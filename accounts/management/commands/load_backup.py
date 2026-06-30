"""One-time data import. Runs only if the database has no users."""
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Load data_backup.json only if database is empty"

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.exists():
            self.stdout.write("Database already has users — skipping backup load.")
            return

        backup_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "data_backup.json")
        backup_path = os.path.normpath(backup_path)

        if not os.path.exists(backup_path):
            self.stdout.write("data_backup.json not found — skipping.")
            return

        self.stdout.write("Loading data_backup.json into database...")
        call_command("loaddata", backup_path, verbosity=1)
        self.stdout.write("Data import complete.")
