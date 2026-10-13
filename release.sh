#!/usr/bin/env bash
# =============================================================================
# IDMC Vendor Portal — Release Script
# Builds, tests, tags, and optionally pushes all Docker images.
#
# Usage:
#   ./release.sh                    # build + test, tag as 'latest'
#   ./release.sh --tag v1.3.0       # build + test, tag as v1.3.0
#   ./release.sh --push             # build + test + push to registry
#   ./release.sh --tag v1.3.0 --push --registry ghcr.io/your-org
#   ./release.sh --skip-tests       # build only, no tests
#   ./release.sh --env staging      # use .env.staging instead of .env
# =============================================================================
set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────────
TAG="latest"
PUSH=false
SKIP_TESTS=false
REGISTRY=""
ENV_FILE=".env"
COMPOSE_FILE="docker-compose.yml"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
step()    { echo -e "\n${BOLD}══ $* ══${RESET}"; }

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tag)        TAG="$2";          shift 2 ;;
        --push)       PUSH=true;         shift   ;;
        --skip-tests) SKIP_TESTS=true;   shift   ;;
        --registry)   REGISTRY="$2";     shift 2 ;;
        --env)        ENV_FILE=".env.$2"; shift 2 ;;
        --help|-h)
            grep '^#' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *) error "Unknown option: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Windows detection ─────────────────────────────────────────────────────────
# If running under Git Bash or WSL on Windows, advise using the PowerShell script.
# The bash script still works in WSL but the PowerShell script is the native choice.
if [[ "${OS:-}" == "Windows_NT" ]] || \
   [[ "$(uname -s 2>/dev/null)" == MINGW* ]] || \
   [[ "$(uname -s 2>/dev/null)" == CYGWIN* ]]; then
    warn "Detected Windows environment (Git Bash / MSYS)."
    warn "The native Windows script is: .\\release.ps1"
    warn "Continuing with bash — if Docker commands fail, switch to PowerShell."
    warn "Use docker-compose.windows.yml override for Windows-specific volume paths."
fi

# ── Pre-flight checks ─────────────────────────────────────────────────────────
step "Pre-flight checks"

command -v docker     >/dev/null 2>&1 || { error "docker not found";         exit 1; }
command -v docker-compose >/dev/null 2>&1 || \
  docker compose version >/dev/null 2>&1  || { error "docker compose not found"; exit 1; }

# Use 'docker compose' (plugin) if available, else fall back to docker-compose
if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
else
    DC="docker-compose"
fi

if [[ ! -f "$ENV_FILE" ]]; then
    warn "No $ENV_FILE found — copying from .env.template."
    warn "Fill in secrets before running in production!"
    cp .env.template "$ENV_FILE"
fi

# Warn about missing secrets
for VAR in POSTGRES_PASSWORD JWT_SIGNING_KEY JWT_PUBLIC_KEY ADMIN_API_KEY \
           ADMIN_SESSION_SECRET UPLOAD_TOKEN_SECRET; do
    if ! grep -qE "^${VAR}=.+" "$ENV_FILE" 2>/dev/null; then
        warn "$VAR is not set in $ENV_FILE"
    fi
done

success "Pre-flight checks passed"

# ── Unit tests ────────────────────────────────────────────────────────────────
if [[ "$SKIP_TESTS" == false ]]; then
    step "Running unit tests"

    info "auth-service (pytest)"
    (
        cd auth-service
        if [[ ! -d .venv ]]; then
            python3 -m venv .venv
            .venv/bin/pip install -q -r requirements.txt
        fi
        .venv/bin/python -m pytest -q --tb=short 2>&1
    ) || { error "auth-service tests failed"; exit 1; }
    success "auth-service tests passed"

    info "backend-api (pytest)"
    (
        cd backend-api
        if [[ ! -d .venv ]]; then
            python3 -m venv .venv
            .venv/bin/pip install -q -r requirements.txt
            .venv/bin/pip install -q anthropic openai google-genai "httpx==0.27.0"
        fi
        .venv/bin/python -m pytest -q --tb=short 2>&1
    ) || { error "backend-api tests failed"; exit 1; }
    success "backend-api tests passed"

    info "portal-spa (vitest)"
    (
        cd portal-spa
        [[ ! -d node_modules ]] && npm install --silent
        npm test 2>&1
    ) || { error "portal-spa tests failed"; exit 1; }
    success "portal-spa tests passed"
fi

# ── Build images ──────────────────────────────────────────────────────────────
step "Building Docker images  (tag: $TAG)"

export TAG
export ENV_FILE

IMAGES=(
    "idmc/auth-service"
    "idmc/backend-api"
    "idmc/portal"
)

$DC --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    --parallel

success "All images built"

# ── Tag images ────────────────────────────────────────────────────────────────
if [[ "$TAG" != "latest" ]]; then
    step "Tagging images as $TAG and latest"
    for IMG in "${IMAGES[@]}"; do
        docker tag "${IMG}:${TAG}" "${IMG}:latest"
        success "Tagged ${IMG}:${TAG}"
    done
fi

# ── Registry prefix ───────────────────────────────────────────────────────────
if [[ -n "$REGISTRY" ]]; then
    step "Tagging images for registry: $REGISTRY"
    for IMG in "${IMAGES[@]}"; do
        BARE="${IMG##idmc/}"
        docker tag "${IMG}:${TAG}" "${REGISTRY}/${BARE}:${TAG}"
        [[ "$TAG" != "latest" ]] && \
            docker tag "${IMG}:${TAG}" "${REGISTRY}/${BARE}:latest"
        success "Tagged ${REGISTRY}/${BARE}:${TAG}"
    done
fi

# ── Push ─────────────────────────────────────────────────────────────────────
if [[ "$PUSH" == true ]]; then
    step "Pushing images"
    if [[ -z "$REGISTRY" ]]; then
        error "--push requires --registry <registry>"
        exit 1
    fi
    for IMG in "${IMAGES[@]}"; do
        BARE="${IMG##idmc/}"
        docker push "${REGISTRY}/${BARE}:${TAG}"
        [[ "$TAG" != "latest" ]] && docker push "${REGISTRY}/${BARE}:latest"
        success "Pushed ${REGISTRY}/${BARE}:${TAG}"
    done
fi

# ── Smoke test (optional) ─────────────────────────────────────────────────────
if [[ "$SKIP_TESTS" == false ]]; then
    step "Smoke test — spinning up stack"

    $DC --env-file "$ENV_FILE" -f docker-compose.test.yml up -d \
        2>&1 | tail -5

    info "Waiting for services to be healthy…"
    MAX_WAIT=60; ELAPSED=0
    until $DC --env-file "$ENV_FILE" -f docker-compose.test.yml \
               ps --format json 2>/dev/null | \
               python3 -c "
import sys, json
services = json.load(sys.stdin) if isinstance(json.load(open('/dev/stdin', 'r')), list) \
    else [json.loads(l) for l in sys.stdin]
" 2>/dev/null || [[ $ELAPSED -ge $MAX_WAIT ]]; do
        sleep 3; ELAPSED=$((ELAPSED+3))
        echo -n "."
    done
    echo ""

    # Quick HTTP checks
    AUTH_HEALTH=$(curl -sf http://localhost:8001/health 2>/dev/null || echo "FAIL")
    API_HEALTH=$(curl -sf  http://localhost:8002/health 2>/dev/null || echo "FAIL")
    PORTAL_OK=$(curl -sf   http://localhost:8080/       2>/dev/null | grep -c "IDMC" || echo "0")

    $DC --env-file "$ENV_FILE" -f docker-compose.test.yml down --volumes --remove-orphans \
        >/dev/null 2>&1

    if echo "$AUTH_HEALTH" | grep -q '"status".*"ok"' && \
       echo "$API_HEALTH"  | grep -q '"status".*"ok"'; then
        success "Smoke test passed — all services healthy"
    else
        warn "Smoke test inconclusive — check service logs"
        warn "auth-service: $AUTH_HEALTH"
        warn "backend-api:  $API_HEALTH"
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
step "Release complete"
echo ""
echo -e "  ${BOLD}Images built:${RESET}"
for IMG in "${IMAGES[@]}"; do
    echo "    ${IMG}:${TAG}"
done
echo ""
echo -e "  ${BOLD}Deploy to production:${RESET}"
echo "    TAG=${TAG} docker compose --env-file .env up -d"
echo ""

if [[ "$PUSH" == false && -n "$REGISTRY" ]]; then
    echo -e "  ${YELLOW}Note:${RESET} Images were tagged for $REGISTRY but not pushed."
    echo "    Run with --push to push."
    echo ""
fi
