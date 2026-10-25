from django.utils.functional import SimpleLazyObject

from .models import loan_rate


def _rate_pct():
    return format((loan_rate() * 100).normalize(), "f")


def loan_rates(request):
    """The monthly interest rate for client pages: `loan_rate` (e.g. 0.005) for calculations and
    `loan_rate_pct` (e.g. "0.5") for text. Lazy, so pages that don't show it run no query."""
    return {
        "loan_rate": SimpleLazyObject(lambda: format(loan_rate().normalize(), "f")),
        "loan_rate_pct": SimpleLazyObject(_rate_pct),
    }
