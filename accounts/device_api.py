"""Secure server-to-server endpoint for the Telegram bot (Jasmine).

When a staff logs in from a new device, the owner gets a Telegram DM with
Allow / Reject / Delete buttons. Those buttons are handled by the bot, which
calls THIS endpoint to actually perform the action in the database — so the
owner never has to open the admin site.

Auth: a shared secret (settings.DEVICE_ACTION_SECRET) that only the bot knows.
Nothing here trusts the caller's session; it trusts the secret only.
"""
import hmac
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

log = logging.getLogger(__name__)


def _clear_pending(u):
    u.pending_device = ""
    u.pending_device_label = ""
    u.pending_device_ip = ""
    u.pending_since = None


@csrf_exempt
@require_POST
def device_action(request):
    secret = getattr(settings, "DEVICE_ACTION_SECRET", "") or ""
    given = request.POST.get("secret") or request.headers.get("X-Device-Secret", "")
    if not secret or not hmac.compare_digest(str(given), str(secret)):
        return JsonResponse({"ok": False, "message": "unauthorized"}, status=403)

    action = (request.POST.get("action") or "").strip()
    pk = (request.POST.get("pk") or "").strip()

    User = get_user_model()
    u = User.objects.filter(pk=pk).first()
    if not u:
        return JsonResponse({"ok": False, "message": "Staff not found (already removed?)."})

    phone = getattr(u, "phone", str(u.pk))

    if action == "allow":
        if u.pending_device:
            u.allowed_device = u.pending_device
            _clear_pending(u)
            u.save(update_fields=[
                "allowed_device", "pending_device", "pending_device_label",
                "pending_device_ip", "pending_since",
            ])
            return JsonResponse({"ok": True,
                                 "message": f"✅ Device approved for {phone}. They can log in now."})
        return JsonResponse({"ok": True, "message": f"Nothing waiting to approve for {phone}."})

    if action == "reject":
        if u.pending_device:
            _clear_pending(u)
            u.save(update_fields=[
                "pending_device", "pending_device_label",
                "pending_device_ip", "pending_since",
            ])
            return JsonResponse({"ok": True,
                                 "message": f"🚫 Rejected the new device for {phone}. "
                                            "They stay locked to their original device."})
        return JsonResponse({"ok": True, "message": f"Nothing waiting to reject for {phone}."})

    if action == "del":
        try:
            u.delete()
        except Exception as e:  # noqa: BLE001
            log.warning("device_action delete failed: %s", e)
            return JsonResponse({"ok": False, "message": f"Could not delete {phone}."})
        return JsonResponse({"ok": True, "message": f"🗑 Staff account {phone} deleted."})

    return JsonResponse({"ok": False, "message": "Unknown action."})
