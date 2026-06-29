# ============================================================
# OFL — Restore database from a backup JSON
# ============================================================
# WARNING: This loads a backup JSON into the database that
# DATABASE_URL currently points to (per scripts/backup_config.ps1).
# Existing rows with the same primary keys will be overwritten.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\restore_db.ps1
#       -BackupFile "backups\backup-2026-05-11_0930.json"
#
# If -BackupFile is omitted, the most recent backup is used.
# ============================================================

param(
    [string]$BackupFile = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Mana_system2"
$ConfigFile  = Join-Path $ProjectRoot "scripts\backup_config.ps1"
$BackupDir   = Join-Path $ProjectRoot "backups"
$PythonExe   = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$ManagePy    = Join-Path $ProjectRoot "manage.py"

if (-not (Test-Path $ConfigFile)) {
    Write-Error "Config file not found: $ConfigFile"
    exit 1
}
. $ConfigFile

# Pick most recent backup if none specified
if ([string]::IsNullOrWhiteSpace($BackupFile)) {
    $Latest = Get-ChildItem -Path $BackupDir -Filter "backup-*.json" |
              Sort-Object LastWriteTime -Descending |
              Select-Object -First 1
    if (-not $Latest) {
        Write-Error "No backups found in $BackupDir"
        exit 1
    }
    $BackupFile = $Latest.FullName
} elseif (-not (Test-Path $BackupFile)) {
    # Try resolving relative to project root
    $Try = Join-Path $ProjectRoot $BackupFile
    if (Test-Path $Try) { $BackupFile = $Try }
    else { Write-Error "Backup file not found: $BackupFile"; exit 1 }
}

Write-Host "[restore_db] Restoring from: $BackupFile"
Write-Host "[restore_db] Target DATABASE_URL host: $(([uri]$env:DATABASE_URL).Host)"
Write-Host "[restore_db] Press Ctrl+C in the next 5 seconds to abort..."
Start-Sleep -Seconds 5

& $PythonExe $ManagePy loaddata $BackupFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "[restore_db] loaddata failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "[restore_db] Done."
