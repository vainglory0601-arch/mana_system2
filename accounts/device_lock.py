"""Staff device lock: each staff login is bound to ONE approved browser/device.

A login from any other device is blocked and left pending until the owner
approves it (Loan Admin → Staff accounts → Allow) or removes the account.

Safety:
  - The owner (superuser) is NEVER locked.
  - Disabled unless the master switch (SystemSetting.device_lock_enabled) is ON,
    so deploying this changes nothing until the owner turns it on.
  - A staff's FIRST login while the lock is on simply adopts their current
    device as the approved one — nobody gets kicked out.
"""
import logging
import secrets

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from .telegram_alert import send_owner_dm

log = logging.getLogger(__name__)


def _admin_url(request, url_name, uid) -> str:
    """Absolute (https in prod) admin URL for a per-staff action button."""
    url = request.build_absolute_uri(reverse(url_name, args=[uid]))
    if not settings.DEBUG and url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url

DEVICE_COOKIE = "sdev"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 2  # ~2 years


def _client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    xrip = request.META.get("HTTP_X_REAL_IP")
    if xrip:
        return xrip.strip()
    return (request.META.get("REMOTE_ADDR") or "").strip()


def _device_label(request) -> str:
    ua = (request.META.get("HTTP_USER_AGENT", "") or "").lower()
    if "iphone" in ua:
        os_name = "iPhone"
    elif "ipad" in ua:
        os_name = "iPad"
    elif "android" in ua:
        os_name = "Android"
    elif "windows" in ua:
        os_name = "Windows"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "Mac"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Unknown device"
    if "edg" in ua:
        br = "Edge"
    elif "samsungbrowser" in ua:
        br = "Samsung Internet"
    elif "opr" in ua or "opera" in ua:
        br = "Opera"
    elif "crios" in ua or "chrome" in ua:
        br = "Chrome"
    elif "fxios" in ua or "firefox" in ua:
        br = "Firefox"
    elif "safari" in ua:
        br = "Safari"
    else:
        br = "browser"
    return f"{br} on {os_name}"


def _lock_on() -> bool:
    from .models import SystemSetting
    try:
        return SystemSetting.device_lock_on()
    except Exception:
        return False  # fail open — never lock everyone out on an error


def set_device_cookie(response, token):
    """Attach the device token to the browser so it's recognised next time."""
    from django.conf import settings
    if token:
        response.set_cookie(
            DEVICE_COOKIE, token, max_age=COOKIE_MAX_AGE,
            httponly=True, samesite="Lax", secure=not settings.DEBUG,
        )
    return response


def check_device(request, user):
    """Decide whether this staff may log in from this device.

    Returns (allowed: bool, cookie_token: str|None). If cookie_token is not
    None, the caller must set it on the response so this browser is remembered.
    """
    # Owner is never locked; clients aren't staff logins; respect master switch.
    if user.is_superuser or not (user.is_staff or user.is_control or user.is_view):
        return True, None
    if not _lock_on():
        return True, None

    token = request.COOKIES.get(DEVICE_COOKIE)

    # First device ever -> adopt it as the approved one.
    if not (user.allowed_device or "").strip():
        token = token or secrets.token_hex(16)
        user.allowed_device = token
        user.save(update_fields=["allowed_device"])
        return True, token

    # Known, approved device.
    if token and token == user.allowed_device:
        return True, None

    # New/unknown device -> block and leave pending for the owner.
    new_token = token or secrets.token_hex(16)
    label = _device_label(request)
    ip = _client_ip(request)
    user.pending_device = new_token
    user.pending_device_label = label
    user.pending_device_ip = ip
    user.pending_since = timezone.now()
    user.save(update_fields=[
        "pending_device", "pending_device_label", "pending_device_ip", "pending_since",
    ])

    try:
        buttons = {"inline_keyboard": [
            [
                {"text": "✅ Allow", "callback_data": f"dev:allow:{user.pk}"},
                {"text": "🚫 Reject", "callback_data": f"dev:reject:{user.pk}"},
            ],
            [
                {"text": "🗑 Delete account", "callback_data": f"dev:del:{user.pk}"},
            ],
        ]}
        send_owner_dm(
            "🔐 <b>NEW DEVICE — approval needed</b>\n"
            "━━━━━━━━━━━━━━\n"
            f"👮 Staff: <b>{user.phone}</b>\n"
            f"📱 Device: <b>{label}</b>\n"
            f"🌐 IP: {ip}\n\n"
            "This staff tried to log in from a device you haven't approved — "
            "they're blocked for now.\n"
            "Tap a button below — it works right here, instantly:",
            reply_markup=buttons,
        )
    except Exception as e:
        log.warning("owner DM failed: %s", e)

    return False, new_token
