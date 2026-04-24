from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import PaymentMethod
from django.utils.html import format_html

from .models import LoanApplication, LoanConfig, WithdrawalRequest

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

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("user", "locked", "wallet_phone", "bank_account", "paypal_email", "updated_at")
    search_fields = ("user__phone", "wallet_phone", "bank_account", "paypal_email")
    list_filter = ("locked",)    
