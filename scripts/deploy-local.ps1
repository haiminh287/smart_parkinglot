<#
.SYNOPSIS
    Deploy local – ghepdoicaulong.shop
    Build FE → Start Docker Compose (prod) → Start Cloudflare Tunnel → Health check

.DESCRIPTION
    Script deploy một lệnh cho Windows.
    Yêu cầu: Node.js, Docker Desktop, cloudflared đã cài và có tunnel config.

.PARAMETER TunnelId
    Cloudflare Tunnel ID (nếu chưa điền vào config.yml, truyền ở đây để tự patch).

.PARAMETER SkipBuild
    Bỏ qua bước build FE (dùng dist/ hiện tại).

.PARAMETER SkipDocker
    Bỏ qua bước khởi động Docker Compose.

.EXAMPLE
    # Deploy đầy đủ – điền tunnel ID
    .\scripts\deploy-local.ps1 -TunnelId "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    # Chỉ build FE
    .\scripts\deploy-local.ps1 -SkipDocker

    # Chỉ start tunnel (FE + Docker đã chạy)
    .\scripts\deploy-local.ps1 -SkipBuild -SkipDocker
#>

[CmdletBinding()]
param(
    [string]$TunnelId = "",
    [switch]$SkipBuild,
    [switch]$SkipDocker
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT    = Split-Path -Parent $PSScriptRoot
$FE_DIR  = Join-Path $ROOT "spotlove-ai"
$BE_DIR  = Join-Path $ROOT "backend-microservices"
$CF_CFG  = Join-Path $ROOT "infra\cloudflare\cloudflared\config.yml"
$LOG_DIR = Join-Path $ROOT "logs"

# ── Helpers ──────────────────────────────────────────────────────────────────
function Write-Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "  OK  $msg" -ForegroundColor Green }
function Write-Fail([string]$msg) { Write-Host "  FAIL $msg" -ForegroundColor Red; exit 1 }
function Write-Info([string]$msg) { Write-Host "  >>  $msg" -ForegroundColor Yellow }

if (!(Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR | Out-Null }

# ─────────────────────────────────────────────────────────────────────────────
# STEP 0: Validate prerequisites
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Kiem tra prerequisites"

foreach ($cmd in @("node", "npm", "docker", "cloudflared")) {
    if (!(Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Fail "$cmd khong tim thay – vui long cai dat truoc."
    }
}
Write-Ok "node, npm, docker, cloudflared – OK"

$dockerPs = docker ps 2>&1
if ($LASTEXITCODE -ne 0) { Write-Fail "Docker Desktop chua chay. Vui long khoi dong Docker Desktop." }
Write-Ok "Docker daemon – Running"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Patch TunnelId vao config.yml neu duoc truyen
# ─────────────────────────────────────────────────────────────────────────────
if ($TunnelId -ne "") {
    Write-Step "Patch Tunnel ID → config.yml"
    if (!(Test-Path $CF_CFG)) { Write-Fail "Khong tim thay $CF_CFG" }
    $cfg = Get-Content $CF_CFG -Raw
    if ($cfg -match "<TUNNEL_ID_PLACEHOLDER>") {
        $cfg = $cfg -replace "<TUNNEL_ID_PLACEHOLDER>", $TunnelId
        Set-Content -Path $CF_CFG -Value $cfg -Encoding UTF8
        Write-Ok "Da patch Tunnel ID: $TunnelId"
    } else {
        Write-Info "config.yml khong con placeholder – giu nguyen."
    }
}

$cfgContent = Get-Content $CF_CFG -Raw -ErrorAction SilentlyContinue
if ($cfgContent -match "<TUNNEL_ID_PLACEHOLDER>") {
    Write-Fail "config.yml van con <TUNNEL_ID_PLACEHOLDER>. Truyen -TunnelId hoac sua file thu cong."
}
Write-Ok "Cloudflare config.yml – OK"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Build Frontend
# ─────────────────────────────────────────────────────────────────────────────
if (!$SkipBuild) {
    Write-Step "Build Frontend (spotlove-ai)"
    if (!(Test-Path $FE_DIR)) { Write-Fail "Khong tim thay $FE_DIR" }

    if (-not $env:VITE_GATEWAY_SECRET) {
        Write-Info "VITE_GATEWAY_SECRET chua duoc set."
        $secret = Read-Host "Nhap VITE_GATEWAY_SECRET (hoac Enter de bo qua)"
        if ($secret -ne "") { $env:VITE_GATEWAY_SECRET = $secret }
    }

    Push-Location $FE_DIR
    try {
        Write-Info "npm ci..."
        npm ci --silent
        if ($LASTEXITCODE -ne 0) { Write-Fail "npm ci that bai" }

        Write-Info "npm run build (mode=production)..."
        npm run build -- --mode production
        if ($LASTEXITCODE -ne 0) { Write-Fail "npm run build that bai" }

        if (!(Test-Path "dist\index.html")) { Write-Fail "Build xong nhung dist/index.html khong co." }
        Write-Ok "FE build xong → spotlove-ai/dist/"
    } finally {
        Pop-Location
    }
} else {
    Write-Info "SkipBuild – bo qua buoc build FE."
    if (!(Test-Path (Join-Path $FE_DIR "dist\index.html"))) {
        Write-Fail "dist/index.html khong ton tai – can build FE truoc."
    }
    Write-Ok "dist/ san sang."
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Start Docker Compose (prod)
# ─────────────────────────────────────────────────────────────────────────────
if (!$SkipDocker) {
    Write-Step "Start Docker Compose (prod)"
    Push-Location $BE_DIR
    try {
        Write-Info "docker compose up (prod override)..."
        docker compose -f docker-compose.yml -f docker-compose.prod.yml pull --ignore-pull-failures
        docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

        if ($LASTEXITCODE -ne 0) { Write-Fail "docker compose up that bai" }

        Write-Info "Cho services khoi dong (15s)..."
        Start-Sleep -Seconds 15

        docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
        Write-Ok "Docker Compose prod – Running"
    } finally {
        Pop-Location
    }
} else {
    Write-Info "SkipDocker – bo qua buoc Docker Compose."
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Health check HTTP
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Health check local (port 80 + 8000)"

$checks = @(
    @{ url = "http://localhost/nginx-health";    label = "Nginx (port 80)" },
    @{ url = "http://localhost:8000/api/health"; label = "API Gateway (port 8000)" }
)
foreach ($c in $checks) {
    try {
        $resp = Invoke-WebRequest -Uri $c.url -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            Write-Ok "$($c.label) → HTTP $($resp.StatusCode)"
        } else {
            Write-Info "$($c.label) → HTTP $($resp.StatusCode) (warning)"
        }
    } catch {
        Write-Info "$($c.label) → chua phan hoi (co the dang startup)"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Start Cloudflare Tunnel (background)
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Start Cloudflare Tunnel"

$tunnelLog = Join-Path $LOG_DIR "cloudflared-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
Write-Info "Log: $tunnelLog"

$oldProc = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
if ($oldProc) {
    Write-Info "Dung cloudflared cu (PID $($oldProc.Id))..."
    $oldProc | Stop-Process -Force
    Start-Sleep -Seconds 2
}

$proc = Start-Process -FilePath "cloudflared" `
    -ArgumentList "tunnel", "--config", $CF_CFG, "run" `
    -RedirectStandardOutput $tunnelLog `
    -RedirectStandardError  "$tunnelLog.err" `
    -PassThru -WindowStyle Hidden

Write-Info "cloudflared PID: $($proc.Id) – cho 8s..."
Start-Sleep -Seconds 8

if ($proc.HasExited) {
    Write-Host "--- cloudflared stderr ---"
    Get-Content "$tunnelLog.err" -ErrorAction SilentlyContinue | Select-Object -Last 20
    Write-Fail "cloudflared thoat som. Xem log: $tunnelLog.err"
}

Write-Ok "cloudflared dang chay (PID $($proc.Id))"

# ─────────────────────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  DEPLOY LOCAL – DONE" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend  : https://ghepdoicaulong.shop"
Write-Host "  API       : https://api.ghepdoicaulong.shop"
Write-Host "  WebSocket : wss://ws.ghepdoicaulong.shop"
Write-Host ""
Write-Host "  cloudflared PID : $($proc.Id)"
Write-Host "  Log tunnel      : $tunnelLog"
Write-Host "================================================" -ForegroundColor Green
