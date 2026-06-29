# ============================================================
# OFL — Daily database backup script
# ============================================================
# Uses Django's `manage.py dumpdata` to export the production
# PostgreSQL database (hosted on Render) into a timestamped JSON
# file under  c:\Mana_system2\backups\ .
#
# JSON dumps are portable: they can be re-loaded into ANY new
# Django/PostgreSQL install via `python manage.py loaddata
# <file>` — even if the host platform (Render, Fly.io, etc.)
# changes in the future. This is the same export format Django
# itself uses for fixtures.
#
# Setup (one time):
#   1. Copy scripts\backup_config.ps1.example
#         → scripts\backup_config.ps1
#   2. Edit backup_config.ps1 and paste your EXTERNAL DATABASE
#      URL between the quotes.
#   3. Run this script once manually to confirm it works:
#         powershell -ExecutionPolicy Bypass -File scripts\backup_db.ps1
#   4. Schedule it daily via Windows Task Scheduler (see README
#      below).
# ============================================================

$ErrorActionPreference = "Stop"

# --- Paths ---
$ProjectRoot = "C:\Mana_system2"
$ConfigFile  = Join-Path $ProjectRoot "scripts\backup_config.ps1"
$BackupDir   = Join-Path $ProjectRoot "backups"
$PythonExe   = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$ManagePy    = Join-Path $ProjectRoot "manage.py"

# --- Load DATABASE_URL from the gitignored config file ---
if (-not (Test-Path $ConfigFile)) {
    Write-Error "Config file not found: $ConfigFile`nCopy backup_config.ps1.example → backup_config.ps1 and fill in your DATABASE_URL."
    exit 1
}
. $ConfigFile

if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
    Write-Error "DATABASE_URL is empty. Edit $ConfigFile and paste your External Database URL from Render."
    exit 1
}

# --- Ensure backup directory exists ---
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

# --- Build timestamped filename ---
$Timestamp  = Get-Date -Format "yyyy-MM-dd_HHmm"
$BackupFile = Join-Path $BackupDir "backup-$Timestamp.json"

Write-Host "[backup_db] Dumping production database -> $BackupFile"

# --- Run Django dumpdata via the helper script ---
# We call scripts/_dump.py instead of `manage.py dumpdata`
# directly so we can disable server-side cursors at runtime
# (Render's pooled connection drops cursors mid-fetch, which
# breaks plain dumpdata with: "cursor _django_curs_..._sync_X
# does not exist"). The helper excludes contenttypes and
# auth.permission so restores don't conflict with the auto-
# generated entries Django creates during migrate.
& $PythonExe (Join-Path $ProjectRoot "scripts\_dump.py") $BackupFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "[backup_db] dumpdata failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

$Size = (Get-Item $BackupFile).Length / 1KB
Write-Host ("[backup_db] OK - wrote {0:N1} KB" -f $Size)

# --- Retention: keep last 30 days only ---
$Cutoff = (Get-Date).AddDays(-30)
Get-ChildItem -Path $BackupDir -Filter "backup-*.json" `
  | Where-Object { $_.LastWriteTime -lt $Cutoff } `
  | ForEach-Object {
      Write-Host "[backup_db] Removing old backup: $($_.Name)"
      Remove-Item $_.FullName -Force
  }

Write-Host "[backup_db] Done."
