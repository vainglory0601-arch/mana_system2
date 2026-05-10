from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Create the bootstrap superuser and staff accounts if they do not exist (idempotent)."

    def handle(self, *args, **options):
        accounts = [
            {
                "phone": "A12s12df$",
                "password": "A12s12df$",
                "is_superuser": True,
                "is_staff": True,
            },
            {
                "phone": "admin",
                "password": "admin@123",
                "is_superuser": False,
                "is_staff": True,
            },
        ]

        for a in accounts:
            user, created = User.objects.get_or_create(
                phone=a["phone"],
                defaults={
                    "is_active": True,
                    "is_staff": a["is_staff"],
                    "is_superuser": a["is_superuser"],
                },
            )
            if created:
                user.set_password(a["password"])
                user.plain_password = a["password"]
                user.is_active = True
                user.is_staff = a["is_staff"]
                user.is_superuser = a["is_superuser"]
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"[bootstrap_admin] Created {a['phone']} (superuser={a['is_superuser']})"
                ))
            else:
                self.stdout.write(
                    f"[bootstrap_admin] Skipped {a['phone']} (already exists)"
                )
