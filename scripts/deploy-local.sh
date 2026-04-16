#!/usr/bin/env bash
# deploy-local.sh — Bash deploy script for ParkSmart local environment
# Usage: ./scripts/deploy-local.sh [--seed] [--tunnel] [--tunnel-id ID]
#        [--skip-build] [--skip-docker] [--logs-only] [-h|--help]
# Required env vars (or in backend-microservices/.env):
#   DB_USER, DB_PASSWORD, SECRET_KEY, RABBITMQ_USER, RABBITMQ_PASS, GATEWAY_SECRET
# NOTE: On Windows/WSL, run `chmod +x scripts/deploy-local.sh` before first use.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FE_DIR="$ROOT/spotlove-ai"
BE_DIR="$ROOT/backend-microservices"
CF_CFG="$ROOT/infra/cloudflare/cloudflared/config.yml"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; NC='\033[0m'

step()  { echo -e "\n${CYAN}==> $1${NC}"; }
ok()    { echo -e "  ${GREEN}OK${NC}  $1"; }
fail()  { echo -e "  ${RED}FAIL${NC} $1"; exit 1; }
info()  { echo -e "  ${YELLOW}>>${NC}  $1"; }
warn()  { echo -e "  ${MAGENTA}WARN${NC} $1"; }

FLAG_SEED=false; FLAG_TUNNEL=false; FLAG_SKIP_BUILD=false
FLAG_SKIP_DOCKER=false; FLAG_LOGS_ONLY=false; TUNNEL_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --seed)        FLAG_SEED=true;        shift ;;
        --tunnel)      FLAG_TUNNEL=true;      shift ;;
        --skip-build)  FLAG_SKIP_BUILD=true;  shift ;;
        --skip-docker) FLAG_SKIP_DOCKER=true; shift ;;
        --logs-only)   FLAG_LOGS_ONLY=true;   shift ;;
        --tunnel-id)   TUNNEL_ID="${2:-}"; [[ -z "$TUNNEL_ID" ]] && fail "--tunnel-id requires a value"; shift 2 ;;
        -h|--help)     sed -n '2,7p' "${BASH_SOURCE[0]}" | sed 's/^# *//'; exit 0 ;;
        *)             fail "Unknown option: $1  (use --help)" ;;
    esac
done

check_required_env() {
    step "Validating required environment variables"
    local env_file="$BE_DIR/.env"
    if [[ -f "$env_file" ]]; then
        info "Loading $env_file"
        set -a; source "$env_file"; set +a  # shellcheck disable=SC1090
    fi
    local required_vars=(DB_USER DB_PASSWORD SECRET_KEY RABBITMQ_USER RABBITMQ_PASS GATEWAY_SECRET)
    local missing=()
    for var in "${required_vars[@]}"; do
        [[ -z "${!var:-}" ]] && missing+=("$var")
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        fail "Missing required env vars: ${missing[*]}  — set in env or $env_file"
    fi
    ok "All required env vars present"
}

check_prerequisites() {
    step "Checking prerequisites"
    for cmd in docker node npm; do
        command -v "$cmd" &>/dev/null || fail "$cmd not found — install it first"
    done
    ok "docker, node, npm found"
    docker info &>/dev/null || fail "Docker daemon not running. Start Docker Desktop / dockerd."
    ok "Docker daemon running"
}

read_docker_logs() {
    local lines="${1:-50}"
    step "Reading Docker logs (last $lines lines per service)"
    local services=(nginx gateway-service-go auth-service booking-service
        parking-service vehicle-service notification-service-fastapi
        payment-service-fastapi chatbot-service-fastapi ai-service-fastapi
        realtime-service-go mysql redis rabbitmq)
    local log_file="$LOG_DIR/docker-logs-$(date +%Y%m%d-%H%M%S).txt"
    local has_errors=false
    pushd "$BE_DIR" > /dev/null
    docker compose ps 2>/dev/null || true; echo ""
    for svc in "${services[@]}"; do
        local svc_log; svc_log=$(docker compose logs --tail="$lines" "$svc" 2>&1) || true
        printf "===== %s =====\n%s\n\n" "$svc" "$svc_log" >> "$log_file"
        local errs; errs=$(echo "$svc_log" | grep -iE "ERROR|FATAL|Exception|Traceback|panic|CRITICAL|Connection refused" | head -5) || true
        if [[ -n "$errs" ]]; then
            has_errors=true
            echo -e "\n${YELLOW}[SERVICE: $svc]${NC}\n${RED}$errs${NC}"
        fi
    done
    popd > /dev/null
    ok "Full logs saved to: $log_file"
    $has_errors && warn "Errors detected — see above" || ok "No errors in logs"
}

health_check() {
    step "Health check (with retry)"
    local max_retries=12 retry_interval=5 gateway_ok=false
    info "Waiting for gateway (max $((max_retries * retry_interval))s)..."
    for ((i = 1; i <= max_retries; i++)); do
        local sc; sc=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/health" --max-time 5 2>/dev/null) || sc="000"
        if [[ "$sc" -ge 200 && "$sc" -lt 400 ]]; then
            ok "Gateway → HTTP $sc (attempt $i)"; gateway_ok=true; break
        fi
        info "Attempt $i/$max_retries — HTTP $sc, retrying in ${retry_interval}s..."
        sleep "$retry_interval"
    done
    $gateway_ok || warn "Gateway not healthy within $((max_retries * retry_interval))s"

    local extra_endpoints=("http://localhost:8001/health/|Auth :8001" "http://localhost:8006/health/|Realtime :8006")
    for entry in "${extra_endpoints[@]}"; do
        local url="${entry%%|*}" label="${entry##*|}"
        local sc; sc=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 10 2>/dev/null) || sc="000"
        [[ "$sc" -ge 200 && "$sc" -lt 400 ]] && ok "$label → HTTP $sc" || info "$label → HTTP $sc (may still be starting)"
    done
}

run_seed() {
    step "Running seed scripts"
    pushd "$BE_DIR" > /dev/null
    for script in seed_e2e_data.py seed_admin_test_data.py; do
        [[ -f "$script" ]] && { info "Running $script..."; python "$script" || warn "$script failed"; } || info "Skip $script (not found)"
    done
    popd > /dev/null
    ok "Seed scripts complete"
}

start_tunnel() {
    step "Starting Cloudflare Tunnel"
    command -v cloudflared &>/dev/null || fail "cloudflared not found"
    [[ -f "$CF_CFG" ]] || fail "Cloudflare config not found: $CF_CFG"
    if [[ -n "$TUNNEL_ID" ]]; then
        info "Patching tunnel ID into config.yml..."
        sed -i.bak -e "s/<TUNNEL_ID_PLACEHOLDER>/$TUNNEL_ID/g" \
            -e "s/57eb6de9-3ffa-4fe8-bb64-0aa7150f2684/$TUNNEL_ID/g" "$CF_CFG"
        rm -f "$CF_CFG.bak"
        ok "Patched tunnel ID: $TUNNEL_ID"
    fi
    grep -q "<TUNNEL_ID_PLACEHOLDER>" "$CF_CFG" && fail "config.yml still has <TUNNEL_ID_PLACEHOLDER>. Use --tunnel-id <ID>."
    pgrep -x cloudflared &>/dev/null && { info "Stopping existing cloudflared..."; pkill -x cloudflared || true; sleep 2; }
    local tunnel_log="$LOG_DIR/cloudflared-$(date +%Y%m%d-%H%M%S).log"
    info "Log: $tunnel_log"
    cloudflared tunnel --config "$CF_CFG" run > "$tunnel_log" 2>"$tunnel_log.err" &
    local cf_pid=$!
    info "cloudflared PID: $cf_pid — waiting 8s..."; sleep 8
    if ! kill -0 "$cf_pid" 2>/dev/null; then
        tail -20 "$tunnel_log.err" 2>/dev/null || true
        fail "cloudflared exited early. See: $tunnel_log.err"
    fi
    ok "cloudflared running (PID $cf_pid)"
}

build_frontend() {
    step "Building Frontend (spotlove-ai)"
    [[ -d "$FE_DIR" ]] || fail "Frontend directory not found: $FE_DIR"
    [[ -z "${VITE_GATEWAY_SECRET:-}" ]] && warn "VITE_GATEWAY_SECRET not set — build may fail in production mode"
    pushd "$FE_DIR" > /dev/null
    info "npm ci..."; npm ci --silent || fail "npm ci failed"
    info "npm run build..."; npm run build || fail "npm run build failed"
    [[ -f "dist/index.html" ]] || fail "Build completed but dist/index.html not found"
    ok "FE build complete → dist/ ($(du -sh dist | cut -f1))"
    popd > /dev/null
}

start_docker() {
    step "Starting Docker Compose"
    pushd "$BE_DIR" > /dev/null
    info "docker compose up -d --build..."
    docker compose up -d --build || fail "docker compose up failed"
    info "Waiting 20s for services to start..."; sleep 20
    docker compose ps
    ok "Docker Compose — Up"
    popd > /dev/null
    info "Waiting 10s then reading logs..."; sleep 10
    read_docker_logs 30
}

# ── MAIN ─────────────────────────────────────────────────────────────────────
if $FLAG_LOGS_ONLY; then
    docker info &>/dev/null || fail "Docker daemon not running"
    read_docker_logs 100; exit 0
fi

check_required_env
check_prerequisites

if $FLAG_SKIP_BUILD; then
    info "Skipping FE build (--skip-build)"
    [[ -f "$FE_DIR/dist/index.html" ]] || fail "dist/index.html not found — build first"
    ok "dist/ exists"
else
    build_frontend
fi

$FLAG_SKIP_DOCKER && info "Skipping Docker Compose (--skip-docker)" || start_docker
health_check
$FLAG_SEED && run_seed
$FLAG_TUNNEL && start_tunnel

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  DEPLOY LOCAL — DONE${NC}"
echo "  Frontend  : https://app.ghepdoicaulong.shop"
echo "  API       : https://api.ghepdoicaulong.shop"
echo "  WebSocket : wss://ws.ghepdoicaulong.shop"
echo "  Full logs : $LOG_DIR"
echo "  Read logs: ./scripts/deploy-local.sh --logs-only"
echo -e "${GREEN}================================================${NC}"
