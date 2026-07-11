$ErrorActionPreference = 'Stop'

$rootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $rootDir

if (-not (Test-Path "frontend/node_modules")) {
    Write-Host "Installing frontend dependencies..."
    Push-Location frontend
    npm install
    Pop-Location
}

$needsBuild = ($env:FORCE_BUILD -eq "1") -or (-not (Test-Path "frontend/out"))
if ($needsBuild) {
    Write-Host "Building frontend static export..."
    Push-Location frontend
    npm run build
    Pop-Location
} else {
    Write-Host "Using existing frontend/out (set FORCE_BUILD=1 to rebuild)."
}

$port = if ($env:PORT) { $env:PORT } else { "8000" }
Write-Host "Starting FastAPI on port $port..."
uv run uvicorn backend.main:app --host 0.0.0.0 --port $port
