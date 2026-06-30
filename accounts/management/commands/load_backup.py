"""One-time data import. Runs when data_backup.json is present in the project root."""
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Flush database and load data_backup.json if the file exists"

    def handle(self, *args, **options):
        # accounts/management/commands/ → 3 levels up = project root /workspace
        backup_path = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data_backup.json")
        )

        if not os.path.exists(backup_path):
            self.stdout.write("data_backup.json not found — skipping.")
            return

        self.stdout.write("Flushing existing data...")
        call_command("flush", "--noinput", verbosity=0)

        self.stdout.write("Loading data_backup.json into database...")
        call_command("loaddata", backup_path, verbosity=1)
        self.stdout.write("Data import complete.")
