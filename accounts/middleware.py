from django.contrib.auth import logout, get_user_model
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.conf import settings
from django.utils.cache import patch_vary_headers


# ---------------------------------------------------------------------------
# Portal Session Middleware
# Gives each portal its own session cookie so staff / user / admin can all
# stay logged in simultaneously in the same browser.
# ---------------------------------------------------------------------------

PORTAL_COOKIE_MAP = {
    '/staff':   'staff_sessionid',
    '/control': 'staff_sessionid',
    '/view':    'staff_sessionid',
    '/admin':   'admin_sessionid',
}


def _portal_cookie_name(path):
    for prefix, name in PORTAL_COOKIE_MAP.items():
        if path.startswith(prefix):
            return name
    return settings.SESSION_COOKIE_NAME   # default 'sessionid' for user portal


class PortalSessionMiddleware(SessionMiddleware):
    """
    Drop-in replacement for SessionMiddleware.
    Uses a different cookie name per portal so that user / staff / admin
    sessions are completely independent within the same browser.
    """

    def process_request(self, request):
        cookie_name = _portal_cookie_name(request.path_info)
        session_key = request.COOKIES.get(cookie_name)
        request.session = self.SessionStore(session_key)
        # Store for use in process_response
        request._portal_session_cookie = cookie_name

    def process_response(self, request, response):
        cookie_name = getattr(request, '_portal_session_cookie',
                              settings.SESSION_COOKIE_NAME)
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty    = request.session.is_empty()
        except AttributeError:
            return response

        # Delete cookie when session becomes empty
        if cookie_name in request.COOKIES and empty:
            response.delete_cookie(
                cookie_name,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            patch_vary_headers(response, ('Cookie',))
        else:
            if accessed:
                patch_vary_headers(response, ('Cookie',))
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if response.status_code != 500:
                    try:
                        request.session.save()
                    except Exception:
                        pass
                    response.set_cookie(
                        cookie_name,
                        request.session.session_key,
                        max_age=request.session.get_expiry_age(),
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or request.is_secure(),
                        httponly=settings.SESSION_COOKIE_HTTPONLY,
                        samesite=settings.SESSION_COOKIE_SAMESITE,
                    )
        return response


class CheckUserActiveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Case 1: user is authenticated but is_active=False (shouldn't happen with
        # modern Django backends, but keep as safety net)
        if hasattr(request, 'user') and request.user.is_authenticated and not request.user.is_active:
            logout(request)
            return redirect(reverse('login') + '?suspended=1')

        # Case 2: Django's ModelBackend already returned None for inactive users,
        # so request.user is AnonymousUser but the session still holds a user_id.
        # Detect this and redirect with the suspended alert.
        if not request.user.is_authenticated:
            user_id = request.session.get('_auth_user_id')
            if user_id:
                User = get_user_model()
                try:
                    user = User.objects.get(pk=user_id)
                    if not user.is_active:
                        request.session.flush()
                        return redirect(reverse('login') + '?suspended=1')
                except User.DoesNotExist:
                    pass

        return self.get_response(request)
