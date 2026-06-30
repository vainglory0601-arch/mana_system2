"""One-time migration: copy all data from Render PostgreSQL into this database."""
import os
from django.db import migrations


RENDER_URL = "postgresql://ofl_postgres_user:XnL9nZiwrE7ugM22osIu4YCz50VdgRrB@dpg-d9155uf7f7vs73d55ji0-a.singapore-postgres.render.com/ofl_postgres"


def restore_from_render(apps, schema_editor):
    import django
    from django.conf import settings

    current_engine = settings.DATABASES["default"]["ENGINE"]
    if "sqlite" in current_engine:
        print("[restore] SQLite detected — skipping Render restore.")
        return

    from django.contrib.auth import get_user_model
    User = get_user_model()
    user_count = User.objects.count()
    if user_count > 2:
        print(f"[restore] {user_count} users already exist — skipping restore.")
        return

    print("[restore] Connecting to Render PostgreSQL...")
    try:
        import psycopg2
        conn = psycopg2.connect(RENDER_URL, connect_timeout=15)
        conn.close()
        print("[restore] Render connection OK.")
    except Exception as e:
        print(f"[restore] Cannot reach Render DB: {e} — skipping.")
        return

    print("[restore] Flushing current database...")
    from django.core.management import call_command
    call_command("flush", "--noinput", verbosity=0)

    print("[restore] Loading data from Render via dumpdata | loaddata...")
    import tempfile, subprocess, sys

    python = sys.executable
    env = os.environ.copy()
    env["DATABASE_URL"] = RENDER_URL

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        tmp_path = tmp.name

    try:
        dump = subprocess.run(
            [python, "manage.py", "dumpdata",
             "--natural-foreign", "--natural-primary",
             "--exclude=contenttypes", "--exclude=auth.permission",
             "--indent=2"],
            capture_output=True, env=env, timeout=120
        )
        if dump.returncode != 0:
            print(f"[restore] dumpdata failed: {dump.stderr.decode('utf-8','ignore')[:300]}")
            return

        with open(tmp_path, "wb") as f:
            f.write(dump.stdout)

        record_count = dump.stdout.count(b'"model"')
        print(f"[restore] Exported {record_count} records from Render.")

        call_command("loaddata", tmp_path, verbosity=1)
        print("[restore] Restore complete!")
    except Exception as e:
        print(f"[restore] Error during restore: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0047_add_contact_message"),
    ]

    operations = [
        migrations.RunPython(restore_from_render, migrations.RunPython.noop),
    ]
