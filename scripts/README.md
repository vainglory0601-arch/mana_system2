# Database Backup & Restore

Daily JSON snapshots of the production database (Render PostgreSQL) saved to `c:\Mana_system2\backups\`. Each snapshot is a Django fixture and can be loaded into any fresh Django+PostgreSQL install via `loaddata` — so even if the hosting platform changes, the data is portable.

## First-time setup

1. **Get the External Database URL** from Render dashboard:
   - `ofl-postgres` service → Connect → copy *External Database URL*

2. **Create your local config file** (never committed to git):

   ```powershell
   Copy-Item scripts\backup_config.ps1.example scripts\backup_config.ps1
   notepad scripts\backup_config.ps1
   ```

   Paste the External Database URL between the quotes, save, close.

3. **Run a manual backup to verify it works:**

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\backup_db.ps1
   ```

   Expected output:

   ```
   [backup_db] Dumping production database → ...\backups\backup-2026-05-11_2130.json
   [backup_db] OK — wrote 245.7 KB
   [backup_db] Done.
   ```

4. **Schedule daily backups (Windows Task Scheduler):**

   - Open **Task Scheduler** → Create Task
   - General tab:
     - Name: `OFL Daily DB Backup`
     - Run whether user is logged on or not (check this)
   - Triggers tab → New:
     - Daily, at e.g. `02:00 AM`
   - Actions tab → New:
     - Program/script: `powershell.exe`
     - Add arguments:
       `-ExecutionPolicy Bypass -File "C:\Mana_system2\scripts\backup_db.ps1"`
     - Start in: `C:\Mana_system2`
   - Conditions tab: uncheck "Start only if on AC power" (so it runs on laptop)
   - Save. Test with right-click → Run.

## What gets backed up

Everything in `accounts` + `staffdash` + sessions + admin + auth.User, except:

- `contenttypes` and `auth.permission` (Django auto-generates these on every `migrate`, including them would conflict on restore)

## Restoring from a backup

```powershell
# Most recent backup:
powershell -ExecutionPolicy Bypass -File scripts\restore_db.ps1

# Specific backup:
powershell -ExecutionPolicy Bypass -File scripts\restore_db.ps1 `
  -BackupFile "backups\backup-2026-05-11_2130.json"
```

The script loads into whatever DATABASE_URL points to in `backup_config.ps1`. To restore into a fresh database (e.g. after moving to a new host):

1. Spin up a new Postgres on the new host.
2. Update `DATABASE_URL` in `scripts\backup_config.ps1` to point to it.
3. Run `python manage.py migrate` against the new DB to create the schema.
4. Run `restore_db.ps1`.

## Retention

`backup_db.ps1` keeps the **last 30 days** of dumps and deletes older ones. Adjust the `$Cutoff` line if you want a different window.

## What's in git vs. not in git

| File | In git? |
|---|---|
| `scripts/backup_db.ps1` | yes |
| `scripts/restore_db.ps1` | yes |
| `scripts/backup_config.ps1.example` | yes |
| `scripts/backup_config.ps1` | **NO** (has password) |
| `backups/*.json` | **NO** (has user data) |
