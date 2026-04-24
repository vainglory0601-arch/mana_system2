from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from accounts.permissions import block_if_frozen
from .forms import LoanApplicationForm
from .models import LoanApplication, WithdrawalRequest


@login_required
@block_if_frozen
def apply_loan_view(request):
    if request.method == "POST":
        form = LoanApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            app = form.save(commit=False)
            app.user = request.user
            app.save()
            return redirect("/loans/my-loans/")
    else:
        form = LoanApplicationForm()

    return render(request, "loans/apply.html", {"form": form})


@login_required
def my_loans_view(request):
    apps = LoanApplication.objects.filter(user=request.user).order_by("-created_at")
    withdrawals = WithdrawalRequest.objects.filter(user=request.user).order_by("-created_at")
    return render(
        request,
        "loans/my_loans.html",
        {"apps": apps, "withdrawals": withdrawals},
    )


@login_required
@block_if_frozen
def withdraw_view(request, *args, **kwargs):
    error = None
    ok = None

    latest = WithdrawalRequest.objects.filter(user=request.user).order_by("-created_at").first()

    if request.method == "POST":
        action = request.POST.get("action", "")

        # create withdrawal request (OTP NOT available yet)
        if action == "create":
            try:
                amt = int(request.POST.get("amount", "0") or 0)
            except ValueError:
                amt = 0

            if amt <= 0:
                error = "Invalid amount"
            elif amt > request.user.wallet_balance:
                error = "Not enough wallet balance"
            else:
                w = WithdrawalRequest.objects.create(
                    user=request.user,
                    amount=amt,
                    status="pending",
                    otp_code="",
                    otp_verified=False,
                )
                request.user.wallet_balance -= amt
                request.user.save(update_fields=["wallet_balance"])
                ok = "Request submitted. Please wait for admin approval and OTP."
                latest = w

        # verify OTP ONLY after admin approves and sets OTP
        elif action == "verify":
            code = (request.POST.get("otp", "") or "").strip()

            if not latest:
                error = "No withdrawal request found."
            elif latest.status != "otp_sent":
                error = "OTP not available yet. Please wait for admin approval."
            elif latest.otp_verified:
                ok = "OTP already verified."
            elif latest.otp_code == "":
                error = "OTP not set yet."
            elif code != latest.otp_code:
                error = "Wrong OTP code."
            else:
                latest.otp_verified = True
                latest.save(update_fields=["otp_verified"])
                ok = "OTP verified. Admin will process payment."

    return render(
        request,
        "loans/withdraw.html",
        {"error": error, "ok": ok, "latest": latest},
    )
