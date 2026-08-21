# Start the FTA Explainer demo: API on :8000, UI on :5173.
#
# This demo is deliberately the FTA Explainer and not the SIP platform. `/api/fta/query` answers
# from the versioned corpus in apps/fta/corpus.py, so it needs no database, no session and no
# model provider. Everything else on the platform needs Postgres and a signed-in session, which
# is correct for those routes and makes them a poor thing to stand up in front of an audience.
#
# What it shows: a member question in, a sourced answer out, with the tariff figures the FTA
# actually changed and the citation they came from.
param([switch]$ApiOnly)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) { Write-Error "No .venv. Run: python -m venv .venv; .venv\Scripts\pip install -e "".[dev]"""; exit 1 }

Write-Output "Starting API on http://127.0.0.1:8000 ..."
$api = Start-Process -FilePath $py -ArgumentList @(
    "-m", "uvicorn", "services.api.main:app", "--host", "127.0.0.1", "--port", "8000"
) -WorkingDirectory $root -PassThru -NoNewWindow

# Wait for /health rather than sleeping a guessed number of seconds.
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
Write-Output "Try:  http://127.0.0.1:8000/docs"
Write-Output "      http://127.0.0.1:8000/api/fta/query?q=wool"
Write-Output ""

if (-not $ApiOnly) {
    Write-Output "Starting FTA UI on http://127.0.0.1:5173 ..."
    Write-Output "(Ctrl+C stops the UI; the API is stopped after that.)"
    Push-Location (Join-Path $root "apps\fta\ui")
    try { pnpm run dev } finally { Pop-Location }
}

Write-Output "Stopping API (pid $($api.Id))..."
try { $api | Stop-Process -Force } catch { }
