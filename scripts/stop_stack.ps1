<#
.SYNOPSIS
    Stops the local Docker Compose IoT stack while preserving database volumes.
    Pass -PurgeVolumes only if you want to wipe all stored InfluxDB/Grafana data.
#>
param(
    [switch]$PurgeVolumes = $false
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " STOPPING STRUCTURAL HEALTH IoT DOCKER STACK" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if ($PurgeVolumes) {
    Write-Host "[WARNING] Stopping containers and removing persistent volumes (-v)..." -ForegroundColor Red
    docker compose down -v
} else {
    Write-Host "[INFO] Stopping containers (persistent InfluxDB & Grafana volumes preserved)..." -ForegroundColor Yellow
    docker compose down
}

Write-Host "[OK] Stack stopped." -ForegroundColor Green
