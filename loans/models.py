from django.db import models
from django.conf import settings


class LoanApplication(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("need_doc", "Need new document"),
        ("need_otp", "Need new OTP"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=120)
    monthly_income = models.PositiveIntegerField(default=0)
    current_address = models.CharField(max_length=250)

    amount = models.PositiveIntegerField(default=0)
    term_months = models.PositiveSmallIntegerField(default=6)
    purpose = models.CharField(max_length=200, blank=True, default="")

    emergency1_name = models.CharField(max_length=120, blank=True, default="")
    emergency1_contact = models.CharField(max_length=30, blank=True, default="")
    emergency2_name = models.CharField(max_length=120, blank=True, default="")
    emergency2_contact = models.CharField(max_length=30, blank=True, default="")
    emergency3_name = models.CharField(max_length=120, blank=True, default="")
    emergency3_contact = models.CharField(max_length=30, blank=True, default="")

    beneficiary_name = models.CharField(max_length=120, blank=True, default="")
    bank_name = models.CharField(max_length=120, blank=True, default="")
    account_number = models.CharField(max_length=40, blank=True, default="")

    signature_name = models.CharField(max_length=120, blank=True, default="")

    id_front = models.ImageField(upload_to="ids/", null=True, blank=True)
    id_back = models.ImageField(upload_to="ids/", null=True, blank=True)
    selfie_with_id = models.ImageField(upload_to="ids/", null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_note = models.TextField(blank=True, default="")
    approved_amount = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.status}"


class WithdrawalRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("otp_sent", "OTP Sent"),
        ("paid", "Paid"),
        ("rejected", "Rejected"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    admin_note = models.TextField(blank=True, default="")

    otp_code = models.CharField(max_length=10, blank=True, default="")
    otp_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} withdraw {self.amount} {self.status}"
