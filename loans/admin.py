from django.contrib import admin
from django.utils.crypto import get_random_string

from .models import LoanApplication, WithdrawalRequest


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "amount", "term_months", "status", "created_at")
    list_filter = ("status", "term_months")
    search_fields = ("user__username", "full_name", "account_number", "bank_name")
    list_editable = ("status",)


@admin.action(description="Approve & Generate OTP (6 digits)")
def approve_and_generate_otp(modeladmin, request, queryset):
    for w in queryset:
        # generate 6-digit numeric OTP
        otp = get_random_string(6, allowed_chars="0123456789")
        w.otp_code = otp
        w.status = "otp_sent"
        w.otp_verified = False
        w.admin_note = (w.admin_note or "").strip()
        w.save(update_fields=["otp_code", "status", "otp_verified", "admin_note"])


@admin.action(description="Mark as PAID (only if OTP verified)")
def mark_paid(modeladmin, request, queryset):
    for w in queryset:
        if w.otp_verified:
            w.status = "paid"
            w.save(update_fields=["status"])


@admin.action(description="Reject withdrawal")
def reject_withdrawal(modeladmin, request, queryset):
    queryset.update(status="rejected")


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "status", "otp_verified", "created_at")
    list_filter = ("status", "otp_verified")
    search_fields = ("user__username",)
    fields = ("user", "amount", "status", "otp_code", "otp_verified", "admin_note", "created_at")
    readonly_fields = ("created_at",)
    actions = [approve_and_generate_otp, mark_paid, reject_withdrawal]
