from django.utils.functional import SimpleLazyObject

from .models import loan_limits, loan_rate


def _rate_pct():
    return format((loan_rate() * 100).normalize(), "f")


def loan_rates(request):
    """The monthly interest rate for client pages: `loan_rate` (e.g. 0.005) for calculations and
    `loan_rate_pct` (e.g. "0.5") for text. Lazy, so pages that don't show it run no query."""
    return {
        "loan_rate": SimpleLazyObject(lambda: format(loan_rate().normalize(), "f")),
        "loan_rate_pct": SimpleLazyObject(_rate_pct),
    }


def _peso_short(n):
    """50000 -> "50K", 5000000 -> "5M", 1500000 -> "1.5M"."""
    for size, unit in ((1000000, "M"), (1000, "K")):
        if n >= size:
            return format((n / size).normalize(), "f") + unit
    return format(n.normalize(), "f")


def _limits():
    lo, hi = loan_limits()
    return {
        "min": format(lo.normalize(), "f"), "max": format(hi.normalize(), "f"),   # for JS / attributes
        "min_txt": f"{lo:,.0f}", "max_txt": f"{hi:,.0f}",                         # "50,000"
        "min_short": _peso_short(lo), "max_short": _peso_short(hi),               # "50K"
    }


def loan_amounts(request):
    """Loan amount limits for client pages as `loan_limits.min` / `.max` (numbers),
    `.min_txt` / `.max_txt` ("50,000") and `.min_short` / `.max_short` ("50K"). Lazy, one query."""
    return {"loan_limits": SimpleLazyObject(_limits)}


def staff_counts(request):
    """Pending counts for the staff side menu badges. Lazy: only staff pages that show them query."""
    if not request.path.startswith("/staff/"):
        return {}
    from .models import LoanApplication, WithdrawalRequest
    return {
        "nav_pending_loans": SimpleLazyObject(
            lambda: LoanApplication.objects.filter(status__in=["PENDING", "REVIEW"]).count()),
        "nav_pending_withdrawals": SimpleLazyObject(
            lambda: WithdrawalRequest.objects.filter(status="processing").count()),
    }
