"""Track which logged-in user is performing the current request.

Used by the watchdog (accounts/watchdog.py) to know WHO changed a client's
status / balance / notification, no matter which view did it.
"""
import contextvars

_current_actor = contextvars.ContextVar("current_actor", default=None)


def get_current_actor():
    """The User performing the current request, or None (system/shell)."""
    return _current_actor.get()


class CurrentActorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        actor = user if getattr(user, "is_authenticated", False) else None
        token = _current_actor.set(actor)
        try:
            return self.get_response(request)
        finally:
            _current_actor.reset(token)
