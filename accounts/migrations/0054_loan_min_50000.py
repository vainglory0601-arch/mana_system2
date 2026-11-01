from decimal import Decimal
from django.db import migrations, models


def lower_minimum(apps, schema_editor):
    """The company minimum loan is now ₱50,000 (was ₱80,000)."""
    LoanConfig = apps.get_model("accounts", "LoanConfig")
    LoanConfig.objects.update(min_amount=Decimal("50000.00"))


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0053_loan_rate_half_percent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="loanconfig",
            name="min_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("50000.00"), max_digits=14),
        ),
        migrations.RunPython(lower_minimum, migrations.RunPython.noop),
    ]
