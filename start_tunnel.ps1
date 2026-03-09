while ($true) {
    Write-Host "Starting persistent Localtunnel..."
    npx localtunnel --port 8000 --subdomain leadaitrackersales
    Write-Host "Tunnel dropped! Reconnecting in 3 seconds..."
    Start-Sleep -Seconds 3
}
