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

## Cloud backup (GitHub Actions — runs even when your PC is off)

Local Task Scheduler only fires when this PC is on. To guarantee a daily dump even when the laptop is closed, a **separate private repo** runs the workflow on GitHub's own servers every day at 02:00 Asia/Manila and commits the dump there.

Why a separate repo: this `mana_system2` repo is public, so committing user data into it would leak passwords/phone numbers/balances. The dedicated backup repo is private and holds only the dumps.

### One-time setup

1. **Create the private companion repo** on GitHub:
   - Name: `mana_system2_backup`
   - Visibility: **Private**
   - Do NOT initialize with a README (we already have one locally).

2. **Push the local backup-repo folder** (already prepared at `c:\Mana_system2_backup\`):

   ```powershell
   cd C:\Mana_system2_backup
   git remote add origin https://github.com/vainglory0601-arch/mana_system2_backup.git
   git push -u origin main
   ```

3. **Add the DATABASE_URL secret** to the backup repo:
   GitHub → `mana_system2_backup` Settings → *Secrets and variables* → **Actions** → *New repository secret*
   - Name: `DATABASE_URL`
   - Value: the **External Database URL** from Render.

4. **Run the workflow once** to verify:
   GitHub → `mana_system2_backup` → *Actions* tab → *Daily DB Backup* → *Run workflow* → main → green tick → a new `backups/backup-…json` appears in the repo.

### Pulling cloud backups down to this PC

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sync_backups.ps1
```

This clones (first run) or pulls the private backup repo into `%LOCALAPPDATA%\OFL-Backup-Cache\` and copies any new dump files into `c:\Mana_system2\backups\`. Run it any time, or schedule it daily in Task Scheduler.

## What's in git vs. not in git

| File | In git? |
|---|---|
| `scripts/backup_db.ps1` | yes |
| `scripts/restore_db.ps1` | yes |
| `scripts/backup_config.ps1.example` | yes |
| `scripts/backup_config.ps1` | **NO** (has password) |
| `backups/*.json` | **NO** (has user data) |
