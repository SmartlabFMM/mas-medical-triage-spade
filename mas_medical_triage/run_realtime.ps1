# run_realtime.ps1 - Lance le systeme MAS en mode temps reel
# Usage : .\run_realtime.ps1

$ErrorActionPreference = "Stop"
$projectPath = (Resolve-Path ".").Path
$pythonExe = Join-Path $projectPath ".venv311\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "Python venv introuvable: $pythonExe" -ForegroundColor Red
    Write-Host "Installe d'abord l'env: python -m venv .venv311 ; .\.venv311\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  TriageMed AI - Mode Temps Reel (Clean Start)" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# 1) Nettoie les anciens process python lies a CE projet (API + main.py)
$old = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
    $_.CommandLine -and
    $_.CommandLine.Contains($projectPath) -and
    ($_.CommandLine -match "api\\app\.py" -or $_.CommandLine -match "main\.py")
}

if ($old) {
    Write-Host "  Arret des anciens process projet..." -ForegroundColor Yellow
    $old | ForEach-Object {
        try {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
            Write-Host ("    - stopped PID {0}" -f $_.ProcessId) -ForegroundColor DarkYellow
        } catch {
            Write-Host ("    - impossible d'arreter PID {0}: {1}" -f $_.ProcessId, $_.Exception.Message) -ForegroundColor Red
        }
    }
}

# 2) Verifie ejabberd
$ejabberd = docker ps --filter "name=ejabberd" --format "{{.Status}}" 2>$null
if (-not $ejabberd) {
    Write-Host "  Demarrage ejabberd..." -ForegroundColor Yellow
    docker start ejabberd | Out-Null
    Start-Sleep -Seconds 3
} else {
    Write-Host "  ejabberd : $ejabberd" -ForegroundColor Green
}

# 3) Lance l'API Flask dans un nouveau terminal (port 5000)
Write-Host ""
Write-Host "  Lancement de l'API Flask (port 5000)..." -ForegroundColor Yellow
$apiCmd = @"
Set-Location '$projectPath'
`$env:PYTHONPATH='.'
`$env:PYTHONUTF8='1'
& '$pythonExe' api/app.py
"@
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $apiCmd) -WindowStyle Normal | Out-Null

# 4) Attend que /health reponde
Write-Host "  Attente de l'API /health..." -ForegroundColor Yellow
$apiReady = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" -Method Get -TimeoutSec 2
        if ($health.status -eq "ok") {
            $apiReady = $true
            break
        }
    } catch {}
    Start-Sleep -Milliseconds 500
}

if ($apiReady) {
    Write-Host "  API OK sur http://127.0.0.1:5000" -ForegroundColor Green
} else {
    Write-Host "  API non disponible sur /health (verifie la fenetre API)." -ForegroundColor Red
}

# 5) Lance les agents SPADE en temps reel dans un nouveau terminal
Write-Host ""
Write-Host "  Lancement des Agents SPADE (Mode Temps Reel)..." -ForegroundColor Yellow
$spadeCmd = @"
Set-Location '$projectPath'
`$env:PYTHONPATH='.'
`$env:PYTHONUTF8='1'
& '$pythonExe' main.py --realtime
"@
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $spadeCmd) -WindowStyle Normal | Out-Null

Write-Host ""
Write-Host "  OK: API + SPADE demarres." -ForegroundColor Green
Write-Host "  Interface front: cd interface ; npm install ; npm run dev" -ForegroundColor Cyan
Write-Host ""
