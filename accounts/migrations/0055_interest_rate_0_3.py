"""Lower the monthly interest rate from 0.5% to 0.3%.

- LoanConfig: default and the stored row move to 0.003 (a row still on 0.005).
- Loans not yet approved (DRAFT / PENDING / REVIEW) are re-priced at 0.3%:
  interest_rate_monthly = 0.003, monthly_repayment = (amount + amount*0.003*term) / term.
- APPROVED and REJECTED loans are never touched: they keep the rate they were
  contracted at.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models

OLD = Decimal("0.005")
NEW = Decimal("0.003")
REPRICE = ("DRAFT", "PENDING", "REVIEW")


def _reprice(apps, rate):
    LoanConfig = apps.get_model("accounts", "LoanConfig")
    LoanApplication = apps.get_model("accounts", "LoanApplication")
    other = OLD if rate == NEW else NEW
    LoanConfig.objects.filter(interest_rate_monthly=other).update(interest_rate_monthly=rate)

    changed = []
    for loan in LoanApplication.objects.filter(status__in=REPRICE).only(
        "id", "amount", "term_months", "interest_rate_monthly", "monthly_repayment"
    ):
        amt = Decimal(str(loan.amount or 0))
        term = int(loan.term_months or 0)
        loan.interest_rate_monthly = rate
        if amt > 0 and term > 0:
            loan.monthly_repayment = ((amt + amt * rate * term) / term).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        changed.append(loan)
    LoanApplication.objects.bulk_update(
        changed, ["interest_rate_monthly", "monthly_repayment"], batch_size=200
    )


def forwards(apps, schema_editor):
    _reprice(apps, NEW)


def backwards(apps, schema_editor):
    _reprice(apps, OLD)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0054_loan_min_50000"),
    ]

    operations = [
        migrations.AlterField(
            model_name="loanconfig",
            name="interest_rate_monthly",
            field=models.DecimalField(decimal_places=6, default=Decimal("0.003000"), max_digits=10),
        ),
        migrations.RunPython(forwards, backwards),
    ]
