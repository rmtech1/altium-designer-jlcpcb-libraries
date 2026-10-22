<#
.SYNOPSIS
  Registers a daily Windows scheduled task that keeps the JLCPCB database current.

.DESCRIPTION
  Runs `python -m jlc_altium update` every day. Upstream data is rebuilt daily
  around 06:00 UTC; the download is skipped when nothing changed, so a daily
  run is cheap. Output is appended to library\update.log.

  The update works while Altium is open: if Altium holds the database file,
  the new data is written into it in a single transaction instead.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install-scheduled-task.ps1
  powershell -ExecutionPolicy Bypass -File scripts\install-scheduled-task.ps1 -At 08:15
  powershell -ExecutionPolicy Bypass -File scripts\install-scheduled-task.ps1 -Remove
#>
param(
    [string]$At = "07:45",
    [string]$TaskName = "JLCPCB Altium Library Update",
    [string]$Python = "",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed '$TaskName'."
    return
}

$repo = Split-Path -Parent $PSScriptRoot
$python = $Python
if (-not $python) { $python = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $python) { throw "python not found on PATH. Install Python 3.11+ from python.org first, or pass -Python." }

$log = Join-Path $repo "library\update.log"
$cmd = "/c `"`"$python`" -m jlc_altium update >> `"$log`" 2>&1`""
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmd -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $At
# Run at the next opportunity if the PC was off at the scheduled time.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Downloads the latest JLCPCB parts data and rebuilds the Altium database library." -Force | Out-Null
Write-Host "Registered '$TaskName' daily at $At. Log: $log"
Write-Host "Run it now with: Start-ScheduledTask -TaskName '$TaskName'"
