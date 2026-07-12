from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import PaymentMethod
from django.utils.html import format_html

from .models import LoanApplication, LoanConfig, WithdrawalRequest, ContactMessage

User = get_user_model()


@admin.register(LoanConfig)
class LoanConfigAdmin(admin.ModelAdmin):
    list_display = ("interest_rate_monthly", "min_amount", "max_amount", "updated_at")

    def has_add_permission(self, request):
        return not LoanConfig.objects.exists()


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "amount",
        "term_months",
        "monthly_repayment",
        "status",
        "created_at",
        "id_front_preview",
        "id_back_preview",
        "selfie_preview",
        "signature_preview",
    )

    list_filter = ("status", "term_months", "created_at")
    search_fields = ("user__phone", "full_name", "identity_number", "guarantor_contact")

    readonly_fields = (
        "interest_rate_monthly",
        "monthly_repayment",
        "created_at",
        "id_front_preview",
        "id_back_preview",
        "selfie_preview",
        "signature_preview",
    )

    # ---------- PREVIEWS ----------
    def id_front_preview(self, obj):
        if obj.id_front:
            return format_html(
                '<img src="{}" style="height:90px;border-radius:10px;object-fit:cover;" />',
                obj.id_front.url
            )
        return "No ID Front"
    id_front_preview.short_description = "ID Front"

    def id_back_preview(self, obj):
        if obj.id_back:
            return format_html(
                '<img src="{}" style="height:90px;border-radius:10px;object-fit:cover;" />',
                obj.id_back.url
            )
        return "No ID Back"
    id_back_preview.short_description = "ID Back"

    def selfie_preview(self, obj):
        if obj.selfie_with_id:
            return format_html(
                '<img src="{}" style="height:90px;border-radius:10px;object-fit:cover;" />',
                obj.selfie_with_id.url
            )
        return "No Selfie"
    selfie_preview.short_description = "Selfie + ID"

    def signature_preview(self, obj):
        if obj.signature_image:
            return format_html(
                '<img src="{}" style="height:80px;border-radius:8px;object-fit:contain;background:#fff;padding:6px;" />',
                obj.signature_image.url
            )
        return "No signature"
    signature_preview.short_description = "Signature"


from .models import User
from django.utils import timezone

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    filter_horizontal = ("groups", "user_permissions")

    # ✅ SHOW ON LIST PAGE
    list_display = (
        "phone",
        "register_ip",
        "register_country",
        "register_city",
        "account_status",
        "withdraw_otp",
        "balance",
        "is_active",
        "notification_updated_at",
    )

    list_editable = ("account_status", "withdraw_otp")
    list_filter = ("account_status",)

    # ✅ SEARCH phone + ip + country + city
    search_fields = ("phone", "register_ip", "register_country", "register_city")

    # ✅ SHOW ON DETAIL PAGE
    fields = (
        "phone",

        "register_ip",
        "register_country",
        "register_city",
        "register_user_agent",

        "balance",
        "account_status",
        "withdraw_otp",
        "status_message",

        "notification_message",
        "notification_updated_at",

        "success_message",
        "success_message_updated_at",

        "is_active",
        "is_staff",
        "is_view",
        "is_control",
        "groups",
        "user_permissions",
    )

    # ✅ make them readonly so staff/admin can’t accidentally edit
    readonly_fields = (
        "register_ip",
        "register_country",
        "register_city",
        "register_user_agent",
        "notification_updated_at",
        "success_message_updated_at",
    )

    def save_model(self, request, obj, form, change):
        from django.utils import timezone

        # 🔴 Alert message
        if "notification_message" in form.changed_data:
            obj.notification_updated_at = timezone.now()
            obj.notification_is_read = False

        # 🟢 Success message
        if "success_message" in form.changed_data:
            obj.success_message_updated_at = timezone.now()
            obj.success_is_read = False

        super().save_model(request, obj, form, change)
# ✅ ADD THIS (register WithdrawalRequest in Django admin)
@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "currency", "status", "otp_required", "staff_otp", "refunded", "created_at", "updated_at")
    list_filter = ("status", "otp_required", "refunded", "currency")
    search_fields = ("user__phone", "id")
    list_editable = ("status", "otp_required", "staff_otp", "refunded")
    # ... (keep your config)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "subject", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("full_name", "email", "phone", "subject", "message")
    list_editable = ("is_read",)
    readonly_fields = ("user", "full_name", "email", "phone", "subject", "message", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("user", "locked", "wallet_phone", "bank_account", "paypal_email", "updated_at")
    search_fields = ("user__phone", "wallet_phone", "bank_account", "paypal_email")
    list_filter = ("locked",)


from django import forms
from django.db.models import Q
from .models import StaffAccount, StaffActivityLog, StaffLoginEvent


@admin.register(StaffLoginEvent)
class StaffLoginEventAdmin(admin.ModelAdmin):
    """Owner-only, read-only log of which device each staff logged in from."""
    list_display = ("created_at", "username", "new_flag", "device_label", "ip")
    list_filter = ("is_new_device", "created_at")
    search_fields = ("username", "ip", "user_agent", "device_label")
    readonly_fields = [f.name for f in StaffLoginEvent._meta.fields]

    @admin.display(description="Device")
    def new_flag(self, obj):
        return "🆕 NEW DEVICE" if obj.is_new_device else "✓ known"

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class StaffAccountForm(forms.ModelForm):
    """Create/edit a staff login. The password field sets the real login
    password (hashed) and keeps plain_password in sync so the owner can
    read it back."""
    login_password = forms.CharField(
        required=False,
        label="Password",
        help_text="Fill this to set or replace the staff member's login password.",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    class Meta:
        model = StaffAccount
        fields = ("phone", "is_staff", "is_control", "is_view", "is_active")
        labels = {
            "phone": "Username",
            "is_staff": "Staff portal access",
            "is_control": "Control portal access",
            "is_view": "View portal access",
            "is_active": "Active (can log in)",
        }

    def clean(self):
        data = super().clean()
        if not self.instance.pk and not (data.get("login_password") or "").strip():
            raise forms.ValidationError("Password is required when creating a staff account.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if not (user.is_staff or user.is_control or user.is_view):
            user.is_staff = True  # sensible default: staff portal
        pw = (self.cleaned_data.get("login_password") or "").strip()
        if pw:
            user.set_password(pw)
            user.plain_password = pw
        if commit:
            user.save()
        return user


@admin.register(StaffAccount)
class StaffAccountAdmin(admin.ModelAdmin):
    """Owner-only staff login management inside the Loan Admin."""
    form = StaffAccountForm
    list_display = ("phone", "plain_password", "roles", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("phone",)

    def roles(self, obj):
        r = []
        if obj.is_staff:
            r.append("Staff")
        if obj.is_control:
            r.append("Control")
        if obj.is_view:
            r.append("View")
        return ", ".join(r) or "—"

    def get_queryset(self, request):
        # Only manageable staff logins — clients and owner accounts excluded.
        return (
            super().get_queryset(request)
            .filter(Q(is_staff=True) | Q(is_control=True) | Q(is_view=True))
            .filter(is_superuser=False)
        )

    # The whole section exists only for the owner.
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(StaffActivityLog)
class StaffActivityLogAdmin(admin.ModelAdmin):
    """Read-only audit trail — nobody can edit or fake history, not even admins."""
    list_display = ("created_at", "actor_label", "action", "target_label", "old_value", "new_value")
    list_filter = ("action", "created_at")
    search_fields = ("actor_label", "target_label", "old_value", "new_value")
    readonly_fields = [f.name for f in StaffActivityLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
