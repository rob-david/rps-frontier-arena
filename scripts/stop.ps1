$pattern = 'uvicorn(\.exe)?\s+backend\.main:app'
$processes = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and $_.CommandLine -match $pattern
}

if (-not $processes) {
    Write-Host "No running uvicorn backend.main:app process found."
    exit 0
}

foreach ($process in $processes) {
    Stop-Process -Id $process.ProcessId -Force
    Write-Host "Stopped process $($process.ProcessId)."
}
