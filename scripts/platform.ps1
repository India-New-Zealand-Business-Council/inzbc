# Start the whole INZBC platform: Postgres, the API, and the one UI that fronts all four modules.
#
# This supersedes demo.ps1 for showing the system. demo.ps1 stands up the FTA Explainer alone,
# which needs no database and no session -- a deliberate choice when the point was one sourced
# answer. The point here is the opposite: the governed pipeline, the human gates and the audit
# trail are the system, and none of them exist without Postgres behind them.
#
# One UI, not five. apps/sip/ui is the shell; the FTA, Comms and Member screens are mounted into
# it through Vite aliases rather than run as separate servers.
#
# From cmd.exe use scripts\platform.cmd instead: typing a .ps1 path at a cmd prompt returns
# silently, which reads exactly like a script that ran and did nothing.
#
# Open http://localhost:5173, not 127.0.0.1 -- Vite binds localhost and ::1 only.
param(
    [switch]$ApiOnly,
    [switch]$SkipSeed,
    [string]$Container = "inzbc-demo-db",
    # Its own database, not the one bench and test runs share. Those accumulate rows and, more
    # awkwardly, a migration checksum from whenever they were last baselined -- migrate.py then
    # refuses to run against them, correctly, and a demo should not be the thing that discovers
    # it. A fresh name means the first run creates and migrates cleanly.
    [string]$Database = "inzbc_platform"
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv\Scripts\python.exe"
$env:DATABASE_URL = "postgresql://inzbc:inzbc@localhost:5432/$Database"

if (-not (Test-Path $py)) {
    Write-Error "No .venv. Run: python -m venv .venv; .venv\Scripts\pip install -e "".[dev]"""
    exit 1
}

# --- Postgres -------------------------------------------------------------------------------
Write-Output "Starting Postgres ($Container) ..."
# No `2>&1` on a native exe: in PowerShell 5.1 that wraps each stderr line in a
# NativeCommandError and leaves $LASTEXITCODE unreliable even when the command succeeded, which
# made this script report "Postgres did not accept connections" against a healthy database.
docker start $Container *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Could not start container '$Container'. Is Docker Desktop running?"
    exit 1
}

# pg_isready rather than a fixed sleep: the container reports up before Postgres accepts
# connections, and a guessed delay is the difference between a clean start and a confusing crash.
$ready = $false
foreach ($i in 1..30) {
    docker exec $Container pg_isready -U inzbc *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ready) { Write-Error "Postgres did not accept connections"; exit 1 }
Write-Output "Postgres ready."

# --- Schema and migrations ------------------------------------------------------------------
# Both of the next two fail on a second run by design: the database already exists, and the
# baseline is already recorded. $ErrorActionPreference is Stop for this script, and a native
# command writing to stderr trips that even when the situation is entirely normal, so the two
# expected-to-fail calls are wrapped rather than the preference being loosened globally.
try { docker exec $Container psql -U inzbc -d postgres -c "create database $Database" *> $null } catch { }
try { Get-Content (Join-Path $root "database\schema.sql") | docker exec -i $Container psql -U inzbc -d $Database -q *> $null } catch { }

try { & $py (Join-Path $root "scripts\migrate.py") baseline *> $null } catch { }
& $py (Join-Path $root "scripts\migrate.py") up
Write-Output "Schema and migrations applied."

# --- Seed -----------------------------------------------------------------------------------
if (-not $SkipSeed) {
    Write-Output "Seeding demo data ..."
    & $py (Join-Path $root "scripts\seed_demo.py")
}

# --- API ------------------------------------------------------------------------------------
Write-Output "Starting API on http://127.0.0.1:8000 ..."
$api = Start-Process -FilePath $py -ArgumentList @(
    "-m", "uvicorn", "services.api.main:app", "--host", "127.0.0.1", "--port", "8000"
) -WorkingDirectory $root -PassThru -NoNewWindow

$ready = $false
foreach ($i in 1..40) {
    Start-Sleep -Milliseconds 500
    try {
        if ((Invoke-WebRequest "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) {
            $ready = $true; break
        }
    } catch { }
}
if (-not $ready) { Write-Error "API did not become healthy"; $api | Stop-Process -Force; exit 1 }
Write-Output "API healthy."
Write-Output ""
Write-Output "  Platform UI : http://localhost:5173"
Write-Output "  API docs    : http://127.0.0.1:8000/docs"
Write-Output ""

# --- Dev session ----------------------------------------------------------------------------
# Every business route requires a session, so without one the UI shows an error where the run
# status belongs. The browser cannot complete the GitHub handshake locally, so the dev proxy
# carries a real session minted through the same repository the OAuth callback uses.
# seed-owner holds every decision role in the seed, so a walkthrough can reach each screen.
# dev_session.py prints the user, their roles and the cookie on separate lines, so this takes the
# cookie line rather than the whole of stdout.
$sessionOutput = & $py "-m" "scripts.dev_session" "--github-login" "seed-owner" 2>$null
$cookieLine = $sessionOutput | Select-String -Pattern "inzbc_session=" | Select-Object -First 1
if ($LASTEXITCODE -eq 0 -and $cookieLine) {
    $env:INZBC_DEV_SESSION = ($cookieLine -split "inzbc_session=")[-1].Trim()
    Write-Output "Dev session ready (signed in as seed-owner)."
} else {
    Write-Output "No dev session: the UI will render, but authenticated panels will show 'no session'."
}
Write-Output ""

# --- UI -------------------------------------------------------------------------------------
if (-not $ApiOnly) {
    Write-Output "Starting the platform UI on http://localhost:5173 ..."
    Write-Output "(Ctrl+C stops the UI; the API is stopped after that.)"
    Push-Location (Join-Path $root "apps\sip\ui")
    try { pnpm run dev } finally { Pop-Location }
}

Write-Output "Stopping API (pid $($api.Id))..."
try { $api | Stop-Process -Force } catch { }
