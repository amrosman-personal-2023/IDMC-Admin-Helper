#Requires -Version 5.1
<#
.SYNOPSIS
    IDMC Vendor Portal — Windows Release Script

.DESCRIPTION
    Builds, tests, tags, and optionally pushes all Docker images on Windows.
    Requires Docker Desktop for Windows (with Linux containers mode).

.PARAMETER Tag
    Docker image tag. Default: latest

.PARAMETER Push
    Push images to the registry after building.

.PARAMETER SkipTests
    Skip unit tests (use when CI has already run them).

.PARAMETER Registry
    Container registry prefix, e.g. ghcr.io/your-org

.PARAMETER Env
    Environment name. Uses .env.<Env> file instead of .env.

.EXAMPLE
    .\release.ps1
    .\release.ps1 -Tag v1.3.0
    .\release.ps1 -Tag v1.3.0 -Push -Registry ghcr.io/your-org
    .\release.ps1 -SkipTests -Tag v1.3.0
    .\release.ps1 -Env staging

.NOTES
    Run from an elevated PowerShell prompt or Developer PowerShell.
    Docker Desktop must be running in Linux containers mode.
#>

[CmdletBinding()]
param (
    [string]  $Tag        = "latest",
    [switch]  $Push,
    [switch]  $SkipTests,
    [string]  $Registry   = "",
    [string]  $Env        = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Colour helpers ─────────────────────────────────────────────────────────────
function Write-Info    ($msg) { Write-Host "  [INFO]  $msg" -ForegroundColor Cyan }
function Write-OK      ($msg) { Write-Host "  [OK]    $msg" -ForegroundColor Green }
function Write-Warn    ($msg) { Write-Host "  [WARN]  $msg" -ForegroundColor Yellow }
function Write-Err     ($msg) { Write-Host "  [ERROR] $msg" -ForegroundColor Red }
function Write-Step    ($msg) { Write-Host "`n══ $msg ══" -ForegroundColor White }

# ── Resolve paths ──────────────────────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$EnvFile    = if ($Env) { ".env.$Env" } else { ".env" }
$ComposeFile = "docker-compose.yml"

$Images = @(
    "idmc/auth-service",
    "idmc/backend-api",
    "idmc/portal"
)

# ── Pre-flight checks ──────────────────────────────────────────────────────────
Write-Step "Pre-flight checks"

# Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Err "docker not found. Install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
}

# Docker running
try {
    docker info 2>&1 | Out-Null
} catch {
    Write-Err "Docker is not running. Start Docker Desktop and retry."
    exit 1
}

# Linux containers mode
$dockerInfo = docker info --format "{{.OSType}}" 2>&1
if ($dockerInfo -ne "linux") {
    Write-Err "Docker must be in Linux containers mode. Right-click Docker Desktop tray icon → 'Switch to Linux containers'."
    exit 1
}

# Docker Compose (plugin preferred)
$DC = $null
if (docker compose version 2>&1 | Select-String "Docker Compose") {
    $DC = "docker compose"
} elseif (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    $DC = "docker-compose"
} else {
    Write-Err "Docker Compose not found. It ships with Docker Desktop — ensure it is up to date."
    exit 1
}
Write-Info "Using compose command: $DC"

# .env file
if (-not (Test-Path $EnvFile)) {
    Write-Warn "No $EnvFile found — copying from .env.template."
    Write-Warn "Fill in all secrets before running in production!"
    Copy-Item .env.template $EnvFile
}

# Warn about missing secrets
$RequiredVars = @(
    "POSTGRES_PASSWORD", "JWT_SIGNING_KEY", "JWT_PUBLIC_KEY",
    "ADMIN_API_KEY", "ADMIN_SESSION_SECRET", "UPLOAD_TOKEN_SECRET"
)
foreach ($Var in $RequiredVars) {
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^${Var}=.+" }
    if (-not $line) { Write-Warn "$Var is not set in $EnvFile" }
}

Write-OK "Pre-flight checks passed"

# ── Unit tests ─────────────────────────────────────────────────────────────────
if (-not $SkipTests) {
    Write-Step "Running unit tests"

    # auth-service
    Write-Info "auth-service (pytest)"
    Push-Location auth-service
    try {
        if (-not (Test-Path .venv)) {
            python -m venv .venv
            & .\.venv\Scripts\pip install -q -r requirements.txt
        }
        & .\.venv\Scripts\python -m pytest -q --tb=short
        if ($LASTEXITCODE -ne 0) { throw "auth-service tests failed" }
        Write-OK "auth-service tests passed"
    } finally { Pop-Location }

    # backend-api
    Write-Info "backend-api (pytest)"
    Push-Location backend-api
    try {
        if (-not (Test-Path .venv)) {
            python -m venv .venv
            & .\.venv\Scripts\pip install -q -r requirements.txt
            & .\.venv\Scripts\pip install -q anthropic openai google-genai "httpx==0.27.0"
        }
        & .\.venv\Scripts\python -m pytest -q --tb=short
        if ($LASTEXITCODE -ne 0) { throw "backend-api tests failed" }
        Write-OK "backend-api tests passed"
    } finally { Pop-Location }

    # portal-spa
    Write-Info "portal-spa (vitest)"
    Push-Location portal-spa
    try {
        if (-not (Test-Path node_modules)) { npm install --silent }
        npm test
        if ($LASTEXITCODE -ne 0) { throw "portal-spa tests failed" }
        Write-OK "portal-spa tests passed"
    } finally { Pop-Location }
}

# ── Build images ───────────────────────────────────────────────────────────────
Write-Step "Building Docker images  (tag: $Tag)"

$env:TAG = $Tag

# Convert env file to absolute path for Compose
$AbsEnvFile = Resolve-Path $EnvFile

Invoke-Expression "$DC --env-file `"$AbsEnvFile`" -f `"$ComposeFile`" build --parallel"
if ($LASTEXITCODE -ne 0) { Write-Err "Build failed"; exit 1 }

Write-OK "All images built"

# ── Tag images ─────────────────────────────────────────────────────────────────
if ($Tag -ne "latest") {
    Write-Step "Tagging images as $Tag and latest"
    foreach ($Img in $Images) {
        docker tag "${Img}:${Tag}" "${Img}:latest"
        Write-OK "Tagged ${Img}:${Tag}"
    }
}

# ── Registry prefix ────────────────────────────────────────────────────────────
if ($Registry) {
    Write-Step "Tagging images for registry: $Registry"
    foreach ($Img in $Images) {
        $Bare = $Img -replace "^idmc/", ""
        docker tag "${Img}:${Tag}" "${Registry}/${Bare}:${Tag}"
        if ($Tag -ne "latest") {
            docker tag "${Img}:${Tag}" "${Registry}/${Bare}:latest"
        }
        Write-OK "Tagged ${Registry}/${Bare}:${Tag}"
    }
}

# ── Push ───────────────────────────────────────────────────────────────────────
if ($Push) {
    if (-not $Registry) {
        Write-Err "-Push requires -Registry <registry>"
        exit 1
    }
    Write-Step "Pushing images"
    foreach ($Img in $Images) {
        $Bare = $Img -replace "^idmc/", ""
        docker push "${Registry}/${Bare}:${Tag}"
        if ($Tag -ne "latest") { docker push "${Registry}/${Bare}:latest" }
        Write-OK "Pushed ${Registry}/${Bare}:${Tag}"
    }
}

# ── Smoke test ─────────────────────────────────────────────────────────────────
if (-not $SkipTests) {
    Write-Step "Smoke test — spinning up test stack"

    $TestCompose = "docker-compose.test.yml"
    Invoke-Expression "$DC --env-file `"$AbsEnvFile`" -f `"$TestCompose`" up -d"

    Write-Info "Waiting for services to become healthy (up to 60s)…"
    $MaxWait = 60; $Elapsed = 0
    do {
        Start-Sleep 3; $Elapsed += 3; Write-Host "." -NoNewline
        $authHealth = try { Invoke-RestMethod "http://localhost:8001/health" -TimeoutSec 2 } catch { $null }
        $apiHealth  = try { Invoke-RestMethod "http://localhost:8002/health" -TimeoutSec 2 } catch { $null }
    } while (-not ($authHealth -and $apiHealth) -and $Elapsed -lt $MaxWait)
    Write-Host ""

    Invoke-Expression "$DC --env-file `"$AbsEnvFile`" -f `"$TestCompose`" down --volumes --remove-orphans" 2>&1 | Out-Null

    if ($authHealth.status -eq "ok" -and $apiHealth.status -eq "ok") {
        Write-OK "Smoke test passed — all services healthy"
    } else {
        Write-Warn "Smoke test inconclusive. Run: docker compose logs auth-service"
    }
}

# ── Summary ────────────────────────────────────────────────────────────────────
Write-Step "Release complete"
Write-Host ""
Write-Host "  Images built:" -ForegroundColor White
foreach ($Img in $Images) { Write-Host "    ${Img}:${Tag}" }
Write-Host ""
Write-Host "  Deploy to production:" -ForegroundColor White
Write-Host "    `$env:TAG='$Tag'; docker compose --env-file .env up -d"
Write-Host ""
if (-not $Push -and $Registry) {
    Write-Warn "Images were tagged for $Registry but not pushed. Add -Push to push."
}
