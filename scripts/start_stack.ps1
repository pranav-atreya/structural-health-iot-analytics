<#
.SYNOPSIS
    Starts the local Docker Compose IoT stack (Mosquitto, InfluxDB 2.x,
    Python MQTT Ingestor, and Grafana) on Windows.
#>
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " STARTING STRUCTURAL HEALTH IoT DOCKER STACK" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[OK] Created .env from .env.example" -ForegroundColor Green
}

Write-Host "[1/4] Validating docker-compose.yml..." -ForegroundColor Cyan
docker compose config -q
if ($LASTEXITCODE -ne 0) {
    throw "docker-compose.yml validation failed."
}

Write-Host "[2/4] Checking Docker Desktop engine..." -ForegroundColor Cyan
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    $DockerDesktopExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $DockerDesktopExe) {
        Write-Host "[INFO] Docker engine is not running yet. Launching Docker Desktop..." -ForegroundColor Yellow
        Start-Process -FilePath $DockerDesktopExe
        $MaxWaitSec = 60
        $Elapsed = 0
        while ($Elapsed -lt $MaxWaitSec) {
            Start-Sleep -Seconds 3
            $Elapsed += 3
            docker info *> $null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[OK] Docker engine is online!" -ForegroundColor Green
                break
            }
            Write-Host "  Waiting for Docker Desktop engine ($Elapsed/$MaxWaitSec s)..." -ForegroundColor DarkGray
        }
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop Linux engine is not running. Please open Docker Desktop and wait for 'Engine running', then re-run .\scripts\start_stack.ps1"
    }
}

Write-Host "[3/4] Building and starting containers..." -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    throw "Failed to start Docker Compose stack."
}

Write-Host "[4/4] Current container status:" -ForegroundColor Cyan
docker compose ps

$LanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.InterfaceAlias -match '^(Wi-Fi|WLAN)$' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -First 1 -ExpandProperty IPAddress)

if (-not $LanIp) {
    $LanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.InterfaceAlias -notmatch 'vEthernet|WSL|Docker|Loopback|VirtualBox|VMware' -and $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -ne '192.168.56.1' } |
        Select-Object -First 1 -ExpandProperty IPAddress)
}

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " STACK ONLINE — ACCESS DETAILS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Grafana Dashboard : http://localhost:3000  (login from .env, default: admin / bridge_grafana_admin)"
Write-Host "  InfluxDB 2.x UI   : http://localhost:8086  (org: pes-iot, bucket: structural_health)"
Write-Host "  MQTT Broker (Host): localhost:1883"
if ($LanIp) {
    Write-Host "  MQTT Broker (LAN) : ${LanIp}:1883  <-- Put '$LanIp' in ESP32 secrets.h MQTT_BROKER_HOST" -ForegroundColor Yellow
}
Write-Host "============================================================" -ForegroundColor Green
