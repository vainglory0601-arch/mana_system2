"""Watchdog: report sensitive client-account changes to the owner's Telegram.

Hooks Django model signals on User, so EVERY code path that changes a
client's status, balance, or notification is caught — staff dashboard,
control panel, admin, future views — nothing can bypass it.

Watched:
  - account_status        (STATUS)
  - balance               (BALANCE, shows +added / -deducted)
  - notification_message  (NOTIFICATION)
  - success_message       (SUCCESS_MSG)
  - client deletion       (DELETE)

Each change writes a permanent StaffActivityLog row, and — when done by a
staff account (or from outside a web request) — sends a Telegram alert.
Changes clients make to their own account (e.g. their balance dropping when
they request a withdrawal) are logged to the database but not alerted.
"""
import hashlib
import html
import logging
import threading
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .current_actor import get_current_actor
from .telegram_alert import send_alert

log = logging.getLogger(__name__)

# Tracks user ids currently mid-deletion, so cascade-deleted loans stay quiet.
_del_local = threading.local()


def _mark_user_deleting(uid, on):
    ids = getattr(_del_local, "ids", None)
    if ids is None:
        ids = set()
        _del_local.ids = ids
    (ids.add if on else ids.discard)(uid)


def _user_is_deleting(uid) -> bool:
    return uid in getattr(_del_local, "ids", ())

WATCH_TZ = ZoneInfo(getattr(settings, "TELEGRAM_ALERT_TZ", "Asia/Bangkok"))


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v if v not in (None, "") else "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _money(v: Decimal) -> str:
    return f"{v:,.2f}"


def _client_label(user) -> str:
    """'Maribeth Lapay (09455202508)' — name from their latest loan application."""
    name = ""
    try:
        name = (
            user.loan_applications.order_by("-created_at")
            .values_list("full_name", flat=True)
            .first()
        ) or ""
    except Exception:
        pass
    return f"{name} ({user.phone})" if name else str(user.phone)


def _client_name(user) -> str:
    try:
        return (
            user.loan_applications.order_by("-created_at")
            .values_list("full_name", flat=True)
            .first()
        ) or ""
    except Exception:
        return ""


# A distinct work-themed emoji badge per staff name (Telegram can't colour text).
_NAME_DOTS = [
    "💼", "📊", "📈", "💰", "🏦", "💳", "🧾", "💵", "🪙", "💎",
    "🏆", "🎯", "⭐", "🔥", "⚡", "💡", "🔑", "🔒", "⚙️", "🛠️",
    "🧰", "📦", "📋", "📝", "🖊️", "📌", "📎", "🗂️", "🖥️", "💻",
    "📱", "📞", "✉️", "📅", "🏷️", "🚀", "🧠", "👑", "🎖️", "🥇",
]


def _dot(name: str) -> str:
    h = int(hashlib.md5((name or "").encode("utf-8")).hexdigest(), 16)
    return _NAME_DOTS[h % len(_NAME_DOTS)]


def _emit(user, actor, change_lines):
    """Send one 'STAFF UPDATE' card to the topic. change_lines already formatted."""
    if not change_lines:
        return
    phone = getattr(user, "phone", str(user.pk))
    name = _client_name(user)
    staff = actor.phone if actor is not None else "SYSTEM"
    dot = _dot(str(staff))
    lines = [
        f"🔔 <b>STAFF UPDATE — {dot} {html.escape(str(staff))}</b>",
        "━━━━━━━━━━━━━━",
        f"📞 <b>Client:</b> <b>{html.escape(phone)}</b>" + (f" — {html.escape(name)}" if name else ""),
        f"🕒 {_now_str()}",
        "",
    ] + change_lines
    send_alert("\n".join(lines))


def _actor_label(actor) -> str:
    if actor is None:
        return "SYSTEM (no web login)"
    role = "staff" if (actor.is_staff or actor.is_superuser) else "client"
    return f"{actor.phone} ({role})"


def _now_str() -> str:
    return timezone.now().astimezone(WATCH_TZ).strftime("%d %b %Y, %I:%M %p")


def _short(text: str, limit: int = 300) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _get_user_model():
    from django.contrib.auth import get_user_model
    return get_user_model()


def _log_row(actor, target, action, old, new, target_label=None):
    from .models import StaffActivityLog
    try:
        StaffActivityLog.objects.create(
            actor=actor if (actor is not None and actor.pk) else None,
            target=target if (target is not None and target.pk) else None,
            actor_label=_actor_label(actor),
            target_label=target_label if target_label is not None
            else (_client_label(target) if target is not None else ""),
            action=action,
            old_value=str(old or ""),
            new_value=str(new or ""),
        )
    except Exception as e:
        log.warning("StaffActivityLog write failed: %s", e)


def connect_signals():
    User = _get_user_model()

    @receiver(pre_save, sender=User, weak=False)
    def _collect_changes(sender, instance, **kwargs):
        if not instance.pk:
            return
        try:
            old = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            return

        changes = []
        if (old.account_status or "") != (instance.account_status or ""):
            changes.append(("STATUS", old.account_status or "—", instance.account_status or "—"))

        ob, nb = _dec(old.balance), _dec(instance.balance)
        if ob != nb:
            changes.append(("BALANCE", str(ob), str(nb)))

        if (old.notification_message or "").strip() != (instance.notification_message or "").strip():
            changes.append(("NOTIFICATION", old.notification_message, instance.notification_message))

        if (old.success_message or "").strip() != (instance.success_message or "").strip():
            changes.append(("SUCCESS_MSG", old.success_message, instance.success_message))

        if str(old.credit_score) != str(instance.credit_score):
            changes.append(("CREDIT", old.credit_score, instance.credit_score))

        if (old.withdraw_otp or "") != (instance.withdraw_otp or ""):
            changes.append(("OTP", old.withdraw_otp or "—", instance.withdraw_otp or "—"))

        if (old.plain_password or "") != (instance.plain_password or ""):
            changes.append(("PASSWORD", "", instance.plain_password))

        if changes:
            instance._watchdog_changes = changes

    @receiver(post_save, sender=User, weak=False)
    def _report_changes(sender, instance, created, **kwargs):
        changes = getattr(instance, "_watchdog_changes", None)
        if not changes:
            return
        instance._watchdog_changes = None
        actor = get_current_actor()

        for action, old, new in changes:
            _log_row(actor, instance, action, old, new)

        # Client changing their own account (e.g. requesting a withdrawal)
        # is logged above but not alerted — we alert on staff/system actions.
        if actor is not None and actor.pk == instance.pk:
            return

        # Option A: a balance increase that is part of a loan approval is silent.
        approval = getattr(instance, "_approval_credit", False)
        alert = []
        for action, old, new in changes:
            if action == "BALANCE" and approval:
                continue
            if action == "STATUS":
                alert.append(f"✏️ Status changed: <b>{html.escape(str(old))}</b> → <b>{html.escape(str(new))}</b>")
            elif action == "BALANCE":
                ob, nb = _dec(old), _dec(new)
                diff = nb - ob
                sign = "➕ ADDED" if diff > 0 else "➖ DEDUCTED"
                alert.append(
                    f"💰 Balance: <b>{_money(ob)}</b> → <b>{_money(nb)}</b> "
                    f"({sign} <b>{_money(abs(diff))}</b>)"
                )
            elif action == "NOTIFICATION":
                alert.append(f"📢 Notification set: “{html.escape(_short(new))}”")
            elif action == "SUCCESS_MSG":
                alert.append(f"✅ Success message set: “{html.escape(_short(new))}”")
            elif action == "CREDIT":
                alert.append(f"⭐ Credit score: <b>{html.escape(str(old))}</b> → <b>{html.escape(str(new))}</b>")
            elif action == "OTP":
                alert.append(f"🔑 Withdrawal code set: <b>{html.escape(str(new))}</b>")
            elif action == "PASSWORD":
                alert.append(f"🔒 Password changed to: <b>{html.escape(str(new))}</b>")
        _emit(instance, actor, alert)

    @receiver(pre_delete, sender=User, weak=False)
    def _mark_delete(sender, instance, **kwargs):
        _mark_user_deleting(instance.pk, True)

    @receiver(post_delete, sender=User, weak=False)
    def _report_delete(sender, instance, **kwargs):
        try:
            # Only client accounts matter here (not staff logins being managed).
            if instance.is_staff or instance.is_superuser or instance.is_control or instance.is_view:
                return
            actor = get_current_actor()
            detail = f"balance={_dec(instance.balance)}, status={instance.account_status}"
            _log_row(actor, None, "DELETE", detail, "", target_label=_client_label(instance))
            phone = getattr(instance, "phone", str(instance.pk))
            name = _client_name(instance)
            staff = actor.phone if actor is not None else "SYSTEM"
            dot = _dot(str(staff))
            lines = [
                f"🚨 <b>CLIENT DELETED — {dot} {html.escape(str(staff))}</b>",
                "━━━━━━━━━━━━━━",
                f"📞 <b>Client:</b> <b>{html.escape(phone)}</b>" + (f" — {html.escape(name)}" if name else ""),
                f"🕒 {_now_str()}",
                f"💰 <b>Balance at deletion:</b> <b>{_money(_dec(instance.balance))}</b> · Status: <b>{html.escape(str(instance.account_status or ''))}</b>",
            ]
            send_alert("\n".join(lines))
        finally:
            _mark_user_deleting(instance.pk, False)

    # ---- Loans (/staff/loans/) --------------------------------------------
    from .models import LoanApplication, PaymentMethod

    LOAN_WATCH = [
        ("status", "LOAN_STATUS"),
        ("amount", "LOAN_AMOUNT"),
        ("term_months", "LOAN_TERM"),
        ("identity_name", "LOAN_IDNAME"),
        ("identity_number", "LOAN_IDNUM"),
    ]

    @receiver(pre_save, sender=LoanApplication, weak=False)
    def _loan_pre(sender, instance, **kwargs):
        if not instance.pk:
            return
        try:
            old = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            return
        ch = []
        for field, code in LOAN_WATCH:
            ov, nv = getattr(old, field), getattr(instance, field)
            if field == "amount":
                changed = _dec(ov) != _dec(nv)   # compare numerically, not as text
            else:
                changed = str(ov if ov is not None else "") != str(nv if nv is not None else "")
            if changed:
                ch.append((field, code, ov, nv))
        if ch:
            instance._loan_changes = ch

    @receiver(post_save, sender=LoanApplication, weak=False)
    def _loan_post(sender, instance, created, **kwargs):
        ch = getattr(instance, "_loan_changes", None)
        if not ch:
            return
        instance._loan_changes = None
        actor = get_current_actor()
        user = instance.user
        for field, code, ov, nv in ch:
            _log_row(actor, user, code, ov, nv)
        # Client editing their own application is not a staff action — skip alert.
        if actor is not None and actor.pk == user.pk:
            return

        alert = []
        for field, code, ov, nv in ch:
            if field == "status":
                up = str(nv or "").upper()
                if up == "APPROVED":
                    continue  # Option A: approval is silent
                if up == "REJECTED":
                    alert.append(f"❌ Loan #{instance.id} <b>REJECTED</b> (was {html.escape(str(ov))})")
                else:
                    alert.append(f"📋 Loan #{instance.id} status: <b>{html.escape(str(ov))}</b> → <b>{html.escape(str(nv))}</b>")
            elif field == "amount":
                alert.append(f"💵 Loan amount: <b>{html.escape(str(ov))}</b> → <b>{html.escape(str(nv))}</b>")
            elif field == "term_months":
                alert.append(f"📅 Loan term: <b>{html.escape(str(ov))}</b> → <b>{html.escape(str(nv))}</b> months")
            elif field == "identity_name":
                alert.append(f"🪪 ID name: <b>{html.escape(str(ov))}</b> → <b>{html.escape(str(nv))}</b>")
            elif field == "identity_number":
                alert.append(f"🪪 ID number: <b>{html.escape(str(ov))}</b> → <b>{html.escape(str(nv))}</b>")
        _emit(user, actor, alert)

    @receiver(post_delete, sender=LoanApplication, weak=False)
    def _loan_deleted(sender, instance, **kwargs):
        # If the whole client is being deleted, this loan is a cascade victim —
        # the CLIENT DELETED alert covers it, so stay quiet (and don't write a
        # log row referencing a user that's about to vanish).
        if _user_is_deleting(instance.user_id):
            return
        actor = get_current_actor()
        user = instance.user
        _log_row(actor, user, "LOAN_DELETE",
                 f"amount={instance.amount}, status={instance.status}", "",
                 target_label=_client_label(user))
        if actor is not None and actor.pk == instance.user_id:
            return
        _emit(user, actor, [f"🗑 <b>Loan #{instance.id} DELETED</b> (amount {html.escape(str(instance.amount))}, was {html.escape(str(instance.status))})"])

    # ---- Payment methods (Bank/Wallet card) -------------------------------
    PM_FIELDS = ["wallet_name", "wallet_phone", "bank_name", "bank_account", "paypal_email"]

    @receiver(pre_save, sender=PaymentMethod, weak=False)
    def _pm_pre(sender, instance, **kwargs):
        if not instance.pk:
            return
        try:
            old = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            return
        ch = [(f, getattr(old, f), getattr(instance, f))
              for f in PM_FIELDS
              if str(getattr(old, f) or "") != str(getattr(instance, f) or "")]
        if ch:
            instance._pm_changes = ch

    @receiver(post_save, sender=PaymentMethod, weak=False)
    def _pm_post(sender, instance, created, **kwargs):
        ch = getattr(instance, "_pm_changes", None)
        if not ch:
            return
        instance._pm_changes = None
        actor = get_current_actor()
        user = instance.user
        for f, ov, nv in ch:
            _log_row(actor, user, "PAYMENT", f"{f}={ov}", f"{f}={nv}")
        if actor is not None and actor.pk == user.pk:
            return
        details = ", ".join(f"{f.replace('_', ' ')}: <b>{html.escape(str(nv or '—'))}</b>" for f, ov, nv in ch)
        _emit(user, actor, [f"🏦 Bank/Wallet updated → {details}"])


# ---------------------------------------------------------------------------
# Staff login-device tracking
# ---------------------------------------------------------------------------
def _client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    xrip = request.META.get("HTTP_X_REAL_IP")
    if xrip:
        return xrip.strip()
    return (request.META.get("REMOTE_ADDR") or "").strip()


def _parse_user_agent(ua: str) -> str:
    """'Chrome on Android' style label from a raw User-Agent string."""
    u = (ua or "").lower()
    if "iphone" in u:
        os_name = "iPhone"
    elif "ipad" in u:
        os_name = "iPad"
    elif "android" in u:
        os_name = "Android"
    elif "windows" in u:
        os_name = "Windows"
    elif "mac os" in u or "macintosh" in u:
        os_name = "Mac"
    elif "linux" in u:
        os_name = "Linux"
    else:
        os_name = "Unknown device"

    if "edg" in u:
        browser = "Edge"
    elif "samsungbrowser" in u:
        browser = "Samsung Internet"
    elif "opr" in u or "opera" in u:
        browser = "Opera"
    elif "crios" in u or "chrome" in u:
        browser = "Chrome"
    elif "fxios" in u or "firefox" in u:
        browser = "Firefox"
    elif "safari" in u:
        browser = "Safari"
    else:
        browser = "browser"
    return f"{browser} on {os_name}"


def connect_login_tracking():
    from .models import StaffLoginEvent

    @receiver(user_logged_in, weak=False)
    def _on_staff_login(sender, request, user, **kwargs):
        # Only staff-type logins matter (skip normal clients).
        if not (
            getattr(user, "is_staff", False)
            or getattr(user, "is_control", False)
            or getattr(user, "is_view", False)
            or getattr(user, "is_superuser", False)
        ):
            return
        try:
            ua = (request.META.get("HTTP_USER_AGENT", "") or "")[:400]
            ip = _client_ip(request)
            key = hashlib.sha256(f"{user.pk}|{ua}".encode()).hexdigest()[:32]

            had_before = StaffLoginEvent.objects.filter(user=user).exists()
            is_new = not StaffLoginEvent.objects.filter(user=user, device_key=key).exists()
            label = _parse_user_agent(ua)

            StaffLoginEvent.objects.create(
                user=user, username=getattr(user, "phone", str(user.pk)),
                ip=ip, user_agent=ua, device_label=label,
                device_key=key, is_new_device=is_new,
            )

            # Alert only when a KNOWN staff account suddenly appears on a NEW
            # device — the classic sign of a shared login. Skip the very first
            # login (setup) and skip the owner.
            if is_new and had_before and not user.is_superuser:
                sname = getattr(user, 'phone', str(user.pk))
                send_alert(
                    "🆕 <b>NEW DEVICE LOGIN</b>\n"
                    f"👮 <b>Staff:</b> {_dot(str(sname))} <b>{html.escape(str(sname))}</b>\n"
                    f"📱 <b>Device:</b> <b>{html.escape(label)}</b>\n"
                    f"🌐 <b>IP:</b> {html.escape(ip or '—')}\n"
                    f"🕒 {_now_str()}\n"
                    "This staff logged in from a device not seen before. "
                    "If it isn't them, their login may be shared."
                )
        except Exception as e:
            log.warning("login tracking failed: %s", e)
