"""One-time data import. Runs when data_backup.json is present in the project root."""
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = "Flush database and load data_backup.json if the file exists"

    def handle(self, *args, **options):
        backup_path = os.path.join(str(settings.BASE_DIR), "data_backup.json")
        print(f"[load_backup] Checking for backup at: {backup_path}")

        if not os.path.exists(backup_path):
            print("[load_backup] data_backup.json NOT FOUND — skipping.")
            return

        print("[load_backup] Found data_backup.json — flushing existing data...")
        call_command("flush", "--noinput", verbosity=0)

        print("[load_backup] Loading data into PostgreSQL...")
        call_command("loaddata", backup_path, verbosity=1)
        print("[load_backup] Data import complete.")
