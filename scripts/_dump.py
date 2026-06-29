"""
Internal helper for backup_db.ps1.

Connects directly to PostgreSQL via psycopg and dumps every
user-app table as a Django-fixture-compatible JSON file —
without going through Django's ORM. That matters because the
local working tree can have model changes (new columns,
unapplied migrations) that don't match the production schema;
Django's `dumpdata` would crash with "column X does not exist"
in that case. Reading the schema straight from the live DB
avoids the whole class of problem.

The output is a single JSON list of {"model": "...", "pk": ...,
"fields": {...}} entries — the same shape `manage.py loaddata`
expects, so a restore is one command later.

Do not call this directly; backup_db.ps1 invokes it.

Usage (internal):
    python scripts/_dump.py <output_file>
"""
from __future__ import annotations

import datetime
import decimal
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 is not installed in the venv. Install with:", file=sys.stderr)
    print("    venv\\Scripts\\pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


# Tables we never want in the dump:
#   - Django internals that get re-created by `migrate`
#     (re-loading them causes pk conflicts on restore)
#   - Session data (transient — re-issued on next login)
SKIP_TABLE_PREFIXES = (
    "django_",
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    "auth_user_groups",
    "auth_user_user_permissions",
)
SKIP_TABLES_EXACT = {
    "django_session",
    "django_admin_log",
    "django_content_type",
    "django_migrations",
}


def table_to_model_label(table_name: str) -> str:
    """
    Map "app_modelname" → "app.ModelName" the way Django fixtures
    expect. Django doesn't expose a perfect reverse, but the
    convention is app_label + "_" + model_name (lowercased).
    We split on the first underscore and reconstruct.
    """
    if "_" not in table_name:
        return table_name
    app, _, model = table_name.partition("_")
    return f"{app}.{model}"


def jsonify(value):
    """psycopg returns datetimes/decimals/uuid; JSON can't take them as-is."""
    if value is None:
        return None
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, datetime.timedelta):
        return value.total_seconds()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (bytes, memoryview)):
        # Binary blobs aren't restorable as JSON; record as base64.
        import base64
        return base64.b64encode(bytes(value)).decode("ascii")
    return value


def dump(database_url: str, output_path: Path) -> None:
    parsed = urlparse(database_url)
    print(f"[_dump] Connecting to {parsed.hostname}/{parsed.path.lstrip('/')}")

    conn = psycopg2.connect(database_url, connect_timeout=30)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 1. List user-app tables.
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type   = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            all_tables = [row["table_name"] for row in cur.fetchall()]

            tables = []
            for t in all_tables:
                if t in SKIP_TABLES_EXACT:
                    continue
                if any(t.startswith(p) for p in SKIP_TABLE_PREFIXES):
                    continue
                tables.append(t)

            print(f"[_dump] Will dump {len(tables)} tables: {', '.join(tables)}")

            # 2. Dump each table.
            fixtures: list[dict] = []
            for table in tables:
                cur.execute(f'SELECT * FROM "{table}"')
                rows = cur.fetchall()
                # Try to detect the primary-key column. Most Django
                # models use 'id'; fall back to the first column.
                pk_col = "id" if rows and "id" in rows[0] else (
                    next(iter(rows[0])) if rows else "id"
                )
                model_label = table_to_model_label(table)
                for row in rows:
                    fields = {k: jsonify(v) for k, v in row.items() if k != pk_col}
                    fixtures.append({
                        "model": model_label,
                        "pk": jsonify(row.get(pk_col)),
                        "fields": fields,
                    })
                print(f"[_dump]   {table}: {len(rows)} rows")

        # 3. Write JSON.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(fixtures, f, ensure_ascii=False, indent=2)

        print(f"[_dump] Wrote {len(fixtures)} total objects -> {output_path}")
    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/_dump.py <output_file>", file=sys.stderr)
        sys.exit(2)

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL is not set in the environment.", file=sys.stderr)
        sys.exit(2)

    output = Path(sys.argv[1])
    dump(database_url, output)


if __name__ == "__main__":
    main()
