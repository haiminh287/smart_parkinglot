<#
.SYNOPSIS
    Deploy local – app.ghepdoicaulong.shop (FE subdomain)
    Build FE → Start Docker Compose (prod) → Read Logs → Fix Errors → Start Cloudflare Tunnel → Health check

.DESCRIPTION
    Script deploy một lệnh cho Windows.
    Yêu cầu: Node.js, Docker Desktop, cloudflared đã cài và có tunnel config.

.PARAMETER TunnelId
    Cloudflare Tunnel ID (nếu chưa điền vào config.yml, truyền ở đây để tự patch).

.PARAMETER SkipBuild
    Bỏ qua bước build FE (dùng dist/ hiện tại).

.PARAMETER SkipDocker
    Bỏ qua bước khởi động Docker Compose.

.PARAMETER LogsOnly
    Chỉ đọc Docker logs và báo cáo lỗi, không deploy lại.

.EXAMPLE
    # Deploy đầy đủ – điền tunnel ID
    .\scripts\deploy-local.ps1 -TunnelId "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    # Chỉ build FE
    .\scripts\deploy-local.ps1 -SkipDocker

    # Chỉ start tunnel (FE + Docker đã chạy)
    .\scripts\deploy-local.ps1 -SkipBuild -SkipDocker

    # Chỉ xem Docker logs
    .\scripts\deploy-local.ps1 -LogsOnly
#>

[CmdletBinding()]
param(
    [string]$TunnelId = "",
    [switch]$SkipBuild,
    [switch]$SkipDocker,
    [switch]$LogsOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT    = Split-Path -Parent $PSScriptRoot
$FE_DIR  = Join-Path $ROOT "spotlove-ai"
$BE_DIR  = Join-Path $ROOT "backend-microservices"
$CF_CFG  = Join-Path $ROOT "infra\cloudflare\cloudflared\config.yml"
$LOG_DIR = Join-Path $ROOT "logs"

# ── Helpers ──────────────────────────────────────────────────────────────────
function Write-Step([string]$msg)  { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)    { Write-Host "  OK  $msg" -ForegroundColor Green }
function Write-Fail([string]$msg)  { Write-Host "  FAIL $msg" -ForegroundColor Red; exit 1 }
function Write-Info([string]$msg)  { Write-Host "  >>  $msg" -ForegroundColor Yellow }
function Write-Warn([string]$msg)  { Write-Host "  WARN $msg" -ForegroundColor Magenta }
function Write-Error2([string]$msg){ Write-Host "  ERR  $msg" -ForegroundColor Red }

if (!(Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR | Out-Null }

# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION: Read docker logs and detect errors
# ─────────────────────────────────────────────────────────────────────────────
function Read-DockerLogs {
    param([string]$ComposeDir, [int]$Lines = 50)

    Write-Step "Kiem tra Docker container status"

    Push-Location $ComposeDir
    try {
        # Get container status
        $psOutput = docker compose -f docker-compose.yml -f docker-compose.prod.yml ps --format json 2>&1
        $allRunning = $true
        $failedContainers = @()

        # Simple ps for display
        docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
        Write-Host ""

        # Get list of containers in unhealthy/exited state
        $psText = docker compose -f docker-compose.yml -f docker-compose.prod.yml ps 2>&1 | Out-String
        $lines2 = $psText -split "`n"
        foreach ($line in $lines2) {
            if ($line -match "(Exit|unhealthy|Error)") {
                $parts = $line -split "\s+"
                if ($parts.Count -gt 0 -and $parts[0] -ne "") {
                    $failedContainers += $parts[0]
                    $allRunning = $false
                }
            }
        }

        if ($allRunning) {
            Write-Ok "Tat ca container dang chay"
        } else {
            Write-Warn "Phat hien container bi loi: $($failedContainers -join ', ')"
        }

        # Read logs of ALL services and report errors
        Write-Step "Doc Docker logs ($Lines dong cuoi moi service)"
        $services = @(
            "nginx", "gateway-service-go", "auth-service", "booking-service",
            "parking-service", "vehicle-service", "notification-service-fastapi",
            "payment-service-fastapi", "chatbot-service-fastapi", "ai-service-fastapi",
            "realtime-service-go", "mysql", "redis", "rabbitmq"
        )

        $logFile = Join-Path $LOG_DIR "docker-logs-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
        $errorSummary = @()

        foreach ($svc in $services) {
            $svcLog = docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=$Lines $svc 2>&1
            if ($LASTEXITCODE -eq 0 -and $svcLog) {
                $logText = $svcLog | Out-String
                Add-Content -Path $logFile -Value "`n===== $svc =====`n$logText"

                # Detect errors
                $errorLines = ($svcLog | Where-Object { $_ -match "(ERROR|FATAL|Exception|Traceback|panic|CRITICAL|Failed|Connection refused|No such file)" })
                if ($errorLines) {
                    $errorSummary += [PSCustomObject]@{
                        Service = $svc
                        Errors  = ($errorLines | Select-Object -First 5) -join "`n"
                    }
                }
            }
        }

        Write-Ok "Full logs saved to: $logFile"

        if ($errorSummary.Count -gt 0) {
            Write-Host "`n===== ERROR SUMMARY =====" -ForegroundColor Red
            foreach ($e in $errorSummary) {
                Write-Host "`n[SERVICE: $($e.Service)]" -ForegroundColor Yellow
                Write-Host $e.Errors -ForegroundColor Red
            }
            Write-Host "========================" -ForegroundColor Red
        } else {
            Write-Ok "Khong phat hien loi nao trong logs"
        }

        return $errorSummary
    } finally {
        Pop-Location
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION: Attempt auto-fix dua tren log errors
# ─────────────────────────────────────────────────────────────────────────────
function Invoke-AutoFix {
    param([array]$ErrorSummary, [string]$ComposeDir)

    if ($ErrorSummary.Count -eq 0) { return }

    Write-Step "Thu tu-fix cac loi pho bien"

    $allErrors = ($ErrorSummary | ForEach-Object { $_.Errors }) -join "`n"

    Push-Location $ComposeDir
    try {
        # Fix 1: MySQL not ready
        if ($allErrors -match "Can't connect to MySQL|Connection refused.*3306|mysql.*not available") {
            Write-Info "MySQL chua san sang – cho 30s va restart services..."
            Start-Sleep -Seconds 30
            docker compose -f docker-compose.yml -f docker-compose.prod.yml restart auth-service booking-service parking-service vehicle-service payment-service-fastapi notification-service-fastapi
            Write-Ok "Da restart services phu thuoc MySQL"
        }

        # Fix 2: Redis not ready
        if ($allErrors -match "Redis.*refused|Connection refused.*6379|redis.*not available") {
            Write-Info "Redis chua san sang – cho 15s va restart gateway..."
            Start-Sleep -Seconds 15
            docker compose -f docker-compose.yml -f docker-compose.prod.yml restart gateway-service-go realtime-service-go
            Write-Ok "Da restart services phu thuoc Redis"
        }

        # Fix 3: RabbitMQ not ready
        if ($allErrors -match "AMQP|rabbitmq|5672.*refused") {
            Write-Info "RabbitMQ chua san sang – cho 20s va restart celery..."
            Start-Sleep -Seconds 20
            docker compose -f docker-compose.yml -f docker-compose.prod.yml restart booking-celery-worker booking-celery-beat notification-service-fastapi
            Write-Ok "Da restart Celery workers"
        }

        # Fix 4: Missing env var / config issue
        if ($allErrors -match "SESSION_COOKIE_DOMAIN is required|ENV=production.*missing|FE_AUTH_CALLBACK_URL must be https") {
            Write-Warn "Gateway thieu env var production – kiem tra docker-compose.prod.yml"
            Write-Info "Chac chan da co: ENV=production, SESSION_COOKIE_DOMAIN, SESSION_COOKIE_SECURE=true, FE_AUTH_CALLBACK_URL"
        }

        # Fix 5: Migration not run
        if ($allErrors -match "no such table|relation.*does not exist|Table.*doesn't exist") {
            Write-Info "Phat hien loi migration – chay migrate..."
            docker compose -f docker-compose.yml -f docker-compose.prod.yml exec auth-service python manage.py migrate --noinput 2>&1 | Write-Host
            docker compose -f docker-compose.yml -f docker-compose.prod.yml exec booking-service python manage.py migrate --noinput 2>&1 | Write-Host
            docker compose -f docker-compose.yml -f docker-compose.prod.yml exec parking-service python manage.py migrate --noinput 2>&1 | Write-Host
            docker compose -f docker-compose.yml -f docker-compose.prod.yml exec vehicle-service python manage.py migrate --noinput 2>&1 | Write-Host
            Write-Ok "Da chay migrations"
        }

        # Fix 6: Port 80 conflict
        if ($allErrors -match "port is already allocated|bind.*80.*already in use") {
            Write-Warn "Port 80 da duoc dung boi process khac"
            $proc80 = netstat -ano | Select-String ":80 " | Select-Object -First 1
            Write-Info "Process dang dung port 80: $proc80"
            Write-Info "Giai phap: Dung IIS/Skype/etc hoac doi nginx sang port 8080"
        }

        # Fix 7: Nginx can't find dist/index.html
        if ($allErrors -match "nginx.*no such file|/usr/share/nginx/html.*not found") {
            Write-Warn "dist/ chua duoc build – rebuild FE..."
        }
    } finally {
        Pop-Location
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# LOGS-ONLY mode
# ─────────────────────────────────────────────────────────────────────────────
if ($LogsOnly) {
    $dockerPs = docker ps 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Fail "Docker Desktop chua chay." }
    $errors = Read-DockerLogs -ComposeDir $BE_DIR -Lines 100
    Invoke-AutoFix -ErrorSummary $errors -ComposeDir $BE_DIR
    exit 0
}

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
    # Replace placeholder OR existing UUID
    $cfg = $cfg -replace "57eb6de9-3ffa-4fe8-bb64-0aa7150f2684", $TunnelId
    $cfg = $cfg -replace "<TUNNEL_ID_PLACEHOLDER>", $TunnelId
    Set-Content -Path $CF_CFG -Value $cfg -Encoding UTF8
    Write-Ok "Da patch Tunnel ID: $TunnelId"
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
        $secret = Read-Host "  Nhap VITE_GATEWAY_SECRET (Enter de bo qua)"
        if ($secret -ne "") { $env:VITE_GATEWAY_SECRET = $secret }
    }

    Push-Location $FE_DIR
    try {
        Write-Info "npm ci..."
        npm ci --silent
        if ($LASTEXITCODE -ne 0) { Write-Fail "npm ci that bai" }

        Write-Info "npm run build (production)..."
        npm run build
        if ($LASTEXITCODE -ne 0) { Write-Fail "npm run build that bai" }

        if (!(Test-Path "dist\index.html")) { Write-Fail "Build xong nhung dist/index.html khong co." }
        $distSize = (Get-ChildItem "dist" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Ok "FE build xong → dist/ ($([math]::Round($distSize,1)) MB)"
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
        Write-Info "docker compose pull (bo qua neu loi)..."
        docker compose -f docker-compose.yml -f docker-compose.prod.yml pull --ignore-pull-failures 2>&1 | Out-Null

        Write-Info "docker compose up -d --build..."
        docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

        if ($LASTEXITCODE -ne 0) { Write-Fail "docker compose up that bai" }

        Write-Info "Cho services khoi dong (20s)..."
        Start-Sleep -Seconds 20

        docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
        Write-Ok "Docker Compose prod – Up"
    } finally {
        Pop-Location
    }

    # ── Đọc logs sau khi services khởi động ──────────────────────────────────
    Write-Info "Cho them 10s roi doc logs..."
    Start-Sleep -Seconds 10
    $logErrors = Read-DockerLogs -ComposeDir $BE_DIR -Lines 30

    # ── Auto-fix nếu phát hiện lỗi ───────────────────────────────────────────
    if ($logErrors.Count -gt 0) {
        Invoke-AutoFix -ErrorSummary $logErrors -ComposeDir $BE_DIR
        Write-Info "Da thu auto-fix – cho 15s roi kiem tra lai..."
        Start-Sleep -Seconds 15
        $logErrors2 = Read-DockerLogs -ComposeDir $BE_DIR -Lines 20
        if ($logErrors2.Count -gt 0) {
            Write-Warn "Van con loi sau khi auto-fix – xem full logs tren. Tiep tuc deploy..."
        } else {
            Write-Ok "Loi da duoc fix!"
        }
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
    @{ url = "http://localhost:8000/api/health"; label = "API Gateway (port 8000)" },
    @{ url = "http://localhost:8001/health/";    label = "Auth Service (port 8001)" },
    @{ url = "http://localhost:8006/health/";    label = "Realtime Service (port 8006)" }
)
foreach ($c in $checks) {
    try {
        $resp = Invoke-WebRequest -Uri $c.url -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        if ($resp.StatusCode -lt 400) {
            Write-Ok "$($c.label) → HTTP $($resp.StatusCode)"
        } else {
            Write-Warn "$($c.label) → HTTP $($resp.StatusCode)"
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
Write-Host "  Frontend  : https://app.ghepdoicaulong.shop"
Write-Host "  API       : https://api.ghepdoicaulong.shop"
Write-Host "  WebSocket : wss://ws.ghepdoicaulong.shop"
Write-Host ""
Write-Host "  cloudflared PID : $($proc.Id)"
Write-Host "  Log tunnel      : $tunnelLog"
Write-Host "  Full logs dir   : $LOG_DIR"
Write-Host ""
Write-Host "  Doc lai logs bat ky luc nao:"
Write-Host "    .\scripts\deploy-local.ps1 -LogsOnly"
Write-Host "================================================" -ForegroundColor Green
