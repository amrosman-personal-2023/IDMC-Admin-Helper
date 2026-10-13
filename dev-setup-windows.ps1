#Requires -Version 5.1
<#
.SYNOPSIS
    IDMC Vendor Portal — Local Dev Setup (Windows)

.DESCRIPTION
    Configures everything needed to run the portal locally on Windows:
      - Generates secrets (.env.local)
      - Creates local-data directories for staging and logs
      - Creates Python virtual environments for both services
      - Installs all dependencies
      - Runs Alembic migrations against SQLite (no external DB needed)
      - Seeds the first admin account
      - Prints the three commands to start the stack

    Database: SQLite (no PostgreSQL needed for local dev)
    Portal:   Vite dev server (no nginx needed)

.EXAMPLE
    .\dev-setup-windows.ps1
    .\dev-setup-windows.ps1 -AdminPassword "MySecret123!"
    .\dev-setup-windows.ps1 -AdminUsername "myadmin" -AdminPassword "MySecret123!"
#>
[CmdletBinding()]
param(
    [string]$AdminUsername = "sysadmin",
    [string]$AdminPassword = "changeme!"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Colour helpers ────────────────────────────────────────────────────────────
function Info   { param($m) Write-Host "[INFO]  $m" -ForegroundColor Cyan }
function Ok     { param($m) Write-Host "[ OK ]  $m" -ForegroundColor Green }
function Warn   { param($m) Write-Host "[WARN]  $m" -ForegroundColor Yellow }
function Header { param($m) Write-Host "`n══ $m ══" -ForegroundColor Cyan }
function Manual { param($m) Write-Host "[TODO]  $m" -ForegroundColor Yellow }
function Fatal  { param($m) Write-Host "[FAIL]  $m" -ForegroundColor Red; exit 1 }

# ── Project root ──────────────────────────────────────────────────────────────
$Project = Split-Path -Parent $MyInvocation.MyCommand.Definition

Header "IDMC Vendor Portal — Windows Dev Setup"
Info "Project root: $Project"

# =============================================================================
# 1. Prerequisite checks
# =============================================================================
Header "Checking prerequisites"

# Python 3.9+ (3.12 preferred; 3.9 is the minimum the deps support)
$PythonExe = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match '(\d+)\.(\d+)') {
            $maj = [int]$Matches[1]; $min = [int]$Matches[2]
            if ($maj -eq 3 -and $min -ge 9) { $PythonExe = $candidate; break }
        }
    } catch {}
}
if (-not $PythonExe) {
    Fatal "Python 3.9+ not found. Download from https://www.python.org/downloads/"
}
$PyVer = (& $PythonExe --version 2>&1).ToString()
Ok "Python: $PyVer ($PythonExe)"
if ($PyVer -notmatch '3\.12') { Warn "Python 3.12 is recommended; found $PyVer. Download from https://www.python.org/downloads/" }

# Node 20+
try {
    $nodeVer = & node --version 2>&1
    $nodeMaj = [int]($nodeVer -replace 'v(\d+).*','$1')
    if ($nodeMaj -lt 20) { Fatal "Node.js 20+ required (found $nodeVer). Download from https://nodejs.org/" }
    Ok "Node: $nodeVer  npm: $(npm --version)"
} catch {
    Fatal "Node.js not found. Download from https://nodejs.org/"
}

# =============================================================================
# 2. Generate secrets
# =============================================================================
Header "Generating secrets"

$EnvFile = Join-Path $Project ".env.local"

$PemDir   = Join-Path $Project "local-data"
$PrivPem  = Join-Path $PemDir "jwt_private.pem"
$PubPem   = Join-Path $PemDir "jwt_public.pem"

# Detect stale .env.local that has inline JWT keys (old broken format)
if (Test-Path $EnvFile) {
    $envLines = Get-Content $EnvFile
    $privLine = $envLines | Where-Object { $_ -match '^JWT_SIGNING_KEY=' }
    $oldFormat = $privLine -and ($privLine -notmatch 'JWT_SIGNING_KEY_FILE') -and ($privLine -match '^JWT_SIGNING_KEY=[A-Za-z0-9+/]')
    $missingPem = (-not (Test-Path $PrivPem)) -or (-not (Test-Path $PubPem))
    if ($oldFormat -or $missingPem) {
        Warn ".env.local has inline keys or PEM files are missing — regenerating secrets."
        Remove-Item $EnvFile -Force
    } else {
        Warn ".env.local already exists — skipping secret generation."
        Warn "Delete $EnvFile and re-run to regenerate all secrets."
    }
}

if (-not (Test-Path $EnvFile)) {
    Info "Generating RSA key pair (4096-bit) for JWT signing..."

    # Use .NET RSA — no OpenSSL required on Windows
    $rsa = [System.Security.Cryptography.RSA]::Create(4096)

    # Export private key as PKCS#8 PEM — write real newlines to a file
    $privBytes = $rsa.ExportPkcs8PrivateKey()
    $privB64   = [Convert]::ToBase64String($privBytes)
    $privLines = @("-----BEGIN PRIVATE KEY-----")
    for ($i = 0; $i -lt $privB64.Length; $i += 64) {
        $privLines += $privB64.Substring($i, [Math]::Min(64, $privB64.Length - $i))
    }
    $privLines += "-----END PRIVATE KEY-----"
    Set-Content -Path $PrivPem -Value ($privLines -join "`n") -Encoding ASCII -NoNewline
    Add-Content -Path $PrivPem -Value "" # trailing newline

    # Export public key as SubjectPublicKeyInfo PEM
    $pubBytes  = $rsa.ExportSubjectPublicKeyInfo()
    $pubB64    = [Convert]::ToBase64String($pubBytes)
    $pubLines  = @("-----BEGIN PUBLIC KEY-----")
    for ($i = 0; $i -lt $pubB64.Length; $i += 64) {
        $pubLines += $pubB64.Substring($i, [Math]::Min(64, $pubB64.Length - $i))
    }
    $pubLines += "-----END PUBLIC KEY-----"
    Set-Content -Path $PubPem -Value ($pubLines -join "`n") -Encoding ASCII -NoNewline
    Add-Content -Path $PubPem -Value ""

    $rsa.Dispose()
    Ok "PEM key files written to $PemDir\"

    # Generate hex secrets using .NET CSPRNG
    function New-HexSecret { param([int]$Bytes)
        $buf = [byte[]]::new($Bytes)
        [System.Security.Cryptography.RandomNumberGenerator]::Fill($buf)
        -join ($buf | ForEach-Object { $_.ToString("x2") })
    }

    $AdminApiKey          = New-HexSecret 32
    $AdminSessionSecret   = New-HexSecret 32
    $UploadTokenSecret    = New-HexSecret 32
    $LocalLogPaths        = Join-Path $Project "local-data\log_paths.local.yaml"

    # JWT keys are stored as file paths — Load-Env.ps1 reads actual PEM content
    # at runtime so python-jose receives a proper multiline PEM string.
    $envContent = @"
# IDMC Vendor Portal — local dev environment
# Generated by dev-setup-windows.ps1 — do not commit this file

# ── Database (SQLite for local dev) ──────────────────────────────────────────
DB_URL=sqlite+aiosqlite:///./dev.db

# ── JWT key paths (loaded as PEM content by Load-Env.ps1) ────────────────────
JWT_SIGNING_KEY_FILE=$PrivPem
JWT_PUBLIC_KEY_FILE=$PubPem

# ── Auth Service ──────────────────────────────────────────────────────────────
ADMIN_API_KEY=$AdminApiKey
ADMIN_SESSION_SECRET=$AdminSessionSecret
ENROLLMENT_LINK_BASE_URL=http://localhost:5173/enroll

# ── Backend API ───────────────────────────────────────────────────────────────
AUTH_SERVICE_URL=http://127.0.0.1:8001
IDMC_STAGING_ROOT=$Project\local-data\staging
ALLOWED_PATHS_CONFIG=$Project\backend-api\config\paths.yaml
OPERATIONS_CONFIG=$Project\backend-api\config\operations.yaml
LOG_PATHS_CONFIG=$LocalLogPaths
UPLOAD_TOKEN_SECRET=$UploadTokenSecret
LLM_SETTINGS_PATH=$Project\local-data\llm-settings.enc

# ── LLM (set your API key here or via Admin Console after first boot) ─────────
LLM_PROVIDER=anthropic
LLM_API_KEY=
LLM_MODEL=claude-opus-4-8
LLM_MAX_CONTEXT_TOKENS=80000
"@
    Set-Content -Path $EnvFile -Value $envContent -Encoding UTF8
    Ok "Secrets written to $EnvFile"
}

# Load .env.local into the current process, then expand PEM file paths
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([^#=][^=]*)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
}
$privFile = [System.Environment]::GetEnvironmentVariable('JWT_SIGNING_KEY_FILE', 'Process')
$pubFile  = [System.Environment]::GetEnvironmentVariable('JWT_PUBLIC_KEY_FILE',  'Process')
if ($privFile -and (Test-Path $privFile)) {
    [System.Environment]::SetEnvironmentVariable('JWT_SIGNING_KEY', (Get-Content $privFile -Raw), 'Process')
}
if ($pubFile -and (Test-Path $pubFile)) {
    [System.Environment]::SetEnvironmentVariable('JWT_PUBLIC_KEY', (Get-Content $pubFile -Raw), 'Process')
}

# =============================================================================
# 3. Create local data directories
# =============================================================================
Header "Creating local data directories"

$Dirs = @(
    "local-data\staging\pm_scripts",
    "local-data\staging\source_files",
    "local-data\staging\target_files",
    "local-data\staging\parameter_files",
    "local-data\scripts",
    "local-data\logs\auth",
    "local-data\logs\api",
    "local-data\logs\agent"
)
foreach ($d in $Dirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Project $d) | Out-Null
}
Ok "Staging and log directories ready under $Project\local-data\"

# Write the local log_paths override
$LocalLogPaths = Join-Path $Project "local-data\log_paths.local.yaml"
if (-not (Test-Path $LocalLogPaths)) {
    $stagingPath = Join-Path $Project "local-data\staging"
    $logAuthPath = Join-Path $Project "local-data\logs\auth"
    $logApiPath  = Join-Path $Project "local-data\logs\api"
    $logAgentPath= Join-Path $Project "local-data\logs\agent"

    $logPathsContent = @"
# Local dev override — generated by dev-setup-windows.ps1
# Points to local-data\ instead of system log directories.
roots:
  - name: staging
    label: "IDMC Staging"
    path: $stagingPath
  - name: auth_logs
    label: "Auth Service Logs"
    path: $logAuthPath
  - name: api_logs
    label: "Backend API Logs"
    path: $logApiPath
  - name: agent_logs
    label: "IDMC Secure Agent Logs"
    path: $logAgentPath
"@
    Set-Content -Path $LocalLogPaths -Value $logPathsContent -Encoding UTF8
    Ok "Local log_paths written to $LocalLogPaths"
}

# =============================================================================
# 4. Auth Service — venv + dependencies + migrations + seed admin
# =============================================================================
Header "Auth Service — Python environment"

$AuthDir = Join-Path $Project "auth-service"
Push-Location $AuthDir

$AuthVenv   = Join-Path $AuthDir ".venv"
$AuthPyExe  = Join-Path $AuthVenv "Scripts\python.exe"
if (Test-Path $AuthPyExe) {
    $vv = (& $AuthPyExe --version 2>&1).ToString()
    if ($vv -match '3\.([89]|1[0-9])') { Ok "venv exists ($vv)" }
    else { Warn "venv Python too old ($vv) — recreating..."; Remove-Item $AuthVenv -Recurse -Force }
}
if (-not (Test-Path $AuthVenv)) {
    Info "Creating virtual environment..."
    & $PythonExe -m venv .venv
    Ok "venv created"
}

$AuthPip     = Join-Path $AuthVenv "Scripts\pip.exe"
$AuthPython  = Join-Path $AuthVenv "Scripts\python.exe"
$AuthAlembic = Join-Path $AuthVenv "Scripts\alembic.exe"

Info "Installing auth-service dependencies..."
& $AuthPip install --upgrade pip --quiet
& $AuthPip install -r requirements.txt --quiet
& $AuthPip install asyncpg "qrcode[pil]" --quiet
Ok "Auth-service dependencies installed"

Info "Running Alembic migrations (SQLite)..."
$env:DB_URL = "sqlite+aiosqlite:///./dev.db"
& $AuthAlembic upgrade head
Ok "Database schema ready (dev.db)"

Info "Seeding first admin account (username: $AdminUsername)..."
& $AuthPython seed_admin.py --username $AdminUsername --password $AdminPassword

Pop-Location

# =============================================================================
# 5. Backend API — venv + dependencies
# =============================================================================
Header "Backend API — Python environment"

$ApiDir = Join-Path $Project "backend-api"
Push-Location $ApiDir

$ApiVenv   = Join-Path $ApiDir ".venv"
$ApiPyExe  = Join-Path $ApiVenv "Scripts\python.exe"
if (Test-Path $ApiPyExe) {
    $vv = (& $ApiPyExe --version 2>&1).ToString()
    if ($vv -match '3\.([89]|1[0-9])') { Ok "venv exists ($vv)" }
    else { Warn "venv Python too old ($vv) — recreating..."; Remove-Item $ApiVenv -Recurse -Force }
}
if (-not (Test-Path $ApiVenv)) {
    Info "Creating virtual environment..."
    & $PythonExe -m venv .venv
    Ok "venv created"
}

$ApiPip = Join-Path $ApiVenv "Scripts\pip.exe"

Info "Installing backend-api dependencies..."
& $ApiPip install --upgrade pip --quiet
& $ApiPip install `
    "fastapi==0.111.0" `
    "uvicorn[standard]==0.29.0" `
    "httpx==0.27.0" `
    "pyyaml==6.0.1" `
    "python-jose[cryptography]==3.3.0" `
    "cryptography==42.0.7" `
    "anthropic>=0.105" `
    "openai>=2.40" `
    "google-genai>=1.47" `
    --quiet
Ok "Backend-api dependencies installed"

Pop-Location

# =============================================================================
# 6. Portal SPA — npm install
# =============================================================================
Header "Portal SPA — Node dependencies"

$SpaDir = Join-Path $Project "portal-spa"
Push-Location $SpaDir
Info "Running npm ci..."
npm ci --silent
Ok "Node dependencies installed"
Pop-Location

# =============================================================================
# 7. Write the env-loader helper
# =============================================================================
$LoaderPath = Join-Path $Project "Load-Env.ps1"
$loaderContent = @'
# Dot-source this script to load .env.local into the current PowerShell session.
# Usage:  . .\Load-Env.ps1
$EnvFile = Join-Path $PSScriptRoot ".env.local"
if (-not (Test-Path $EnvFile)) {
    Write-Error "No .env.local found — run dev-setup-windows.ps1 first."
    return
}
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([^#=][^=]*)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
}
# Expand JWT key file paths into actual PEM content for python-jose
$privFile = [System.Environment]::GetEnvironmentVariable('JWT_SIGNING_KEY_FILE', 'Process')
$pubFile  = [System.Environment]::GetEnvironmentVariable('JWT_PUBLIC_KEY_FILE',  'Process')
if ($privFile -and (Test-Path $privFile)) {
    [System.Environment]::SetEnvironmentVariable('JWT_SIGNING_KEY', (Get-Content $privFile -Raw), 'Process')
}
if ($pubFile -and (Test-Path $pubFile)) {
    [System.Environment]::SetEnvironmentVariable('JWT_PUBLIC_KEY', (Get-Content $pubFile -Raw), 'Process')
}
Write-Host "Loaded $EnvFile" -ForegroundColor Cyan
'@
Set-Content -Path $LoaderPath -Value $loaderContent -Encoding UTF8

# =============================================================================
# 8. Manual steps the script cannot complete
# =============================================================================
Header "Manual steps required"

Write-Host ""
Manual "IMPORTANT — Change the admin password after first login:"
Write-Host "         The seed admin was created with password: $AdminPassword"
Write-Host "         To reset it, run:"
Write-Host "           cd $AuthDir"
Write-Host "           .\.venv\Scripts\python.exe seed_admin.py --username $AdminUsername --password '<new-password>'"
Write-Host ""
Manual "LLM API key (optional for local dev):"
Write-Host "         To use the Log Analyser AI features, open:"
Write-Host "           $EnvFile"
Write-Host "         Set LLM_API_KEY=<your-key> and LLM_PROVIDER=anthropic (or openai/gemini)"
Write-Host "         Or set it in Admin Console → LLM Settings after starting the stack."
Write-Host ""
Manual "Trigger scripts (operations.yaml):"
Write-Host "         operations.yaml references scripts under /opt/idmc/scripts."
Write-Host "         For local dev, place test scripts (as .bat or .ps1) in:"
Write-Host "           $Project\local-data\scripts\"
Write-Host "         Then update backend-api\config\operations.yaml to point there."
Write-Host "         Note: scripts run inside Python subprocess — use .bat wrappers if needed."
Write-Host ""
Manual "Informatica Secure Agent log paths:"
Write-Host "         log_paths.local.yaml points at local-data\ for dev."
Write-Host "         When connecting to a real IDMC environment, update:"
Write-Host "           $LocalLogPaths"
Write-Host "         to point at actual agent/service log directories."
Write-Host ""
Manual "Portal enrollment base URL:"
Write-Host "         ENROLLMENT_LINK_BASE_URL is set to http://localhost:5173/enroll."
Write-Host "         On a staging or shared server update this in $EnvFile."
Write-Host ""
Manual "Line endings:"
Write-Host "         If any .py or .sh file was saved with CRLF, uvicorn may fail to import it."
Write-Host "         Run:  git config core.autocrlf false  (if using Git)"
Write-Host "         Or open the file in VS Code → click CRLF in the status bar → LF → Save."

# =============================================================================
# 9. Print the three start commands
# =============================================================================
Header "Setup complete — start the stack with these three commands"

$AuthUvicorn = Join-Path $AuthDir ".venv\Scripts\uvicorn.exe"
$ApiUvicorn  = Join-Path $ApiDir  ".venv\Scripts\uvicorn.exe"

Write-Host ""
Write-Host "Open three PowerShell windows and run one command in each:" -ForegroundColor White

Write-Host ""
Write-Host "── Window 1 — Auth Service (port 8001) ─────────────────────────────────────" -ForegroundColor Green
Write-Host "  cd $AuthDir"
Write-Host "  . $LoaderPath"
Write-Host "  `$env:DB_URL = 'sqlite+aiosqlite:///./dev.db'"
Write-Host "  & '$AuthUvicorn' app.main:app --host 127.0.0.1 --port 8001 --reload"

Write-Host ""
Write-Host "── Window 2 — Backend API (port 8002) ──────────────────────────────────────" -ForegroundColor Green
Write-Host "  cd $ApiDir"
Write-Host "  . $LoaderPath"
Write-Host "  & '$ApiUvicorn' app.main:app --host 127.0.0.1 --port 8002 --reload"

Write-Host ""
Write-Host "── Window 3 — Portal SPA (port 5173, Vite dev server) ──────────────────────" -ForegroundColor Green
Write-Host "  cd $SpaDir"
Write-Host "  npm run dev"

Write-Host ""
Write-Host "Then open:       http://localhost:5173" -ForegroundColor White
Write-Host "Admin console:   http://localhost:5173/admin/login" -ForegroundColor White
Write-Host "Admin login:     $AdminUsername / $AdminPassword  <- change this password immediately" -ForegroundColor Yellow
Write-Host ""
Write-Host "Env loader helper:  . $LoaderPath" -ForegroundColor Cyan
Write-Host ""
Ok "All done."
