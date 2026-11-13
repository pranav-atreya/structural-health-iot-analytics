<#
.SYNOPSIS
    Initialises local configuration (.env, secrets.h) and Python dependencies
    for the Structural Health IoT Analytics project.
#>
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " STRUCTURAL HEALTH IoT ANALYTICS — WORKSPACE SETUP" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Create .env from .env.example if missing
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[OK] Created .env from .env.example" -ForegroundColor Green
} else {
    Write-Host "[INFO] .env already exists (preserved)" -ForegroundColor Yellow
}

# 2. Detect active LAN IPv4 address for ESP32 MQTT configuration (prioritise Wi-Fi, exclude virtual adapters)
$LanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.InterfaceAlias -match '^(Wi-Fi|WLAN)$' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -First 1 -ExpandProperty IPAddress)

if (-not $LanIp) {
    $LanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.InterfaceAlias -notmatch 'vEthernet|WSL|Docker|Loopback|VirtualBox|VMware' -and $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -ne '192.168.56.1' } |
        Select-Object -First 1 -ExpandProperty IPAddress)
}

if (-not $LanIp) {
    $LanIp = "192.168.1.100"
}

Write-Host "[INFO] Detected Laptop LAN IPv4 Address: $LanIp" -ForegroundColor Cyan

# 3. Create firmware/structural_health_monitor/secrets.h if missing
$SecretsExample = Join-Path $RepoRoot "firmware\structural_health_monitor\secrets.example.h"
$SecretsTarget  = Join-Path $RepoRoot "firmware\structural_health_monitor\secrets.h"

if (-not (Test-Path $SecretsTarget)) {
    $Content = Get-Content $SecretsExample -Raw
    $Content = $Content -replace '"192\.168\.1\.100"', "`"$LanIp`""
    Set-Content -Path $SecretsTarget -Value $Content -Encoding UTF8
    Write-Host "[OK] Created firmware\structural_health_monitor\secrets.h with MQTT_BROKER_HOST=$LanIp" -ForegroundColor Green
    Write-Host "     -> IMPORTANT: Edit secrets.h to enter your WIFI_SSID and WIFI_PASSWORD before flashing!" -ForegroundColor Yellow
} else {
    Write-Host "[INFO] firmware\structural_health_monitor\secrets.h already exists (preserved)" -ForegroundColor Yellow
}

# 4. Install Python requirements
Write-Host "`n[STEP] Verifying Python packages from requirements.txt..." -ForegroundColor Cyan
python -m pip install -r requirements.txt

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " SETUP COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Edit firmware\structural_health_monitor\secrets.h with your Wi-Fi SSID & password."
Write-Host "     (Confirm MQTT_BROKER_HOST is set to '$LanIp')"
Write-Host "  2. Start the Docker stack:   .\scripts\start_stack.ps1"
Write-Host "  3. Run unit & ML tests:      python -m pytest tests/"
