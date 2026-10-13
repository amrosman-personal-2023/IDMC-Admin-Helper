# IDMC Vendor Portal — Native Server Setup Guide

**Version 1.4 · June 2026 · Classification: Internal — Restricted**

Run all three tiers directly on the host — no Docker required.
Covers **macOS (Intel + Apple Silicon)**, **Linux (Ubuntu 22.04/24.04)**, and **Windows (Server 2019+ / Windows 11)**.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites by Platform](#2-prerequisites-by-platform)
3. [Directory Layout](#3-directory-layout)
4. [Database Setup](#4-database-setup)
5. [Secret Generation](#5-secret-generation)
6. [Tier 1 — Auth Service](#6-tier-1--auth-service)
7. [Tier 2 — Backend API](#7-tier-2--backend-api)
8. [Tier 3 — Portal SPA + nginx](#8-tier-3--portal-spa--nginx)
9. [First Admin Account](#9-first-admin-account)
10. [Running All Three Tiers](#10-running-all-three-tiers)
11. [Process Management](#11-process-management)
12. [Verifying the Stack](#12-verifying-the-stack)
13. [Environment Variable Reference](#13-environment-variable-reference)
14. [Moved or copied project folder](#14-moved-or-copied-project-folder)

---

## 1. Overview

The three tiers and their default native ports:

| Tier | Directory | Default port | Technology |
|---|---|---|---|
| Auth Service | `auth-service/` | **8001** | Python 3.12 + FastAPI + Uvicorn |
| Backend API | `backend-api/` | **8002** | Python 3.12 + FastAPI + Uvicorn |
| Portal SPA | `portal-spa/` | **80** (prod) / **5173** (dev) | React + Vite → nginx |

nginx acts as a reverse proxy in front of both Python services — the same role it plays inside the Docker `portal` container.

**Network rule:** Auth-service and backend-api must **not** be reachable directly from the internet. Bind them to `127.0.0.1` (loopback) and let nginx proxy the relevant paths. Only nginx (port 80/443) faces the network.

---

## 2. Prerequisites by Platform

### 2.1 macOS

Install [Homebrew](https://brew.sh) if not already present, then:

```bash
# Python 3.12
brew install python@3.12

# Node.js 20 LTS
brew install node@20
echo 'export PATH="/opt/homebrew/opt/node@20/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile

# PostgreSQL 15
brew install postgresql@15
brew services start postgresql@15

# nginx
brew install nginx

# OpenSSL (for secret generation — usually pre-installed via brew)
brew install openssl@3
```

Verify:
```bash
python3.12 --version   # Python 3.12.x
node --version          # v20.x.x
npm --version           # 10.x.x
psql --version          # psql (PostgreSQL) 15.x
nginx -v                # nginx/1.27.x
```

> **Apple Silicon note:** Homebrew installs to `/opt/homebrew/` on M-series Macs. On Intel Macs the prefix is `/usr/local/`. Adjust paths accordingly.

---

### 2.2 Linux (Ubuntu 22.04 / 24.04)

```bash
# System packages
sudo apt-get update
sudo apt-get install -y \
    python3.12 python3.12-venv python3.12-dev \
    python3-pip \
    build-essential libpq-dev \
    curl wget git \
    nginx \
    openssl

# Node.js 20 via NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# PostgreSQL 15
sudo apt-get install -y postgresql-15 postgresql-client-15

# Start PostgreSQL
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

Verify:
```bash
python3.12 --version
node --version
npm --version
psql --version
nginx -v
```

---

### 2.3 Windows (Server 2019+ / Windows 11)

All commands below run in **PowerShell (as Administrator)** unless stated otherwise.

**Python 3.12**
1. Download the installer from https://www.python.org/downloads/ (choose "Windows installer 64-bit")
2. Run it — check **"Add python.exe to PATH"** and **"Install for all users"**
3. Verify: `python --version` → `Python 3.12.x`

**Node.js 20 LTS**
1. Download from https://nodejs.org/en/download (LTS, Windows x64 `.msi`)
2. Run the installer (default options)
3. Verify: `node --version` → `v20.x.x`

**PostgreSQL 15**
1. Download from https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Run the installer — note the password you set for the `postgres` superuser
3. Add `C:\Program Files\PostgreSQL\15\bin` to your PATH:
   ```powershell
   [Environment]::SetEnvironmentVariable(
     "PATH",
     $env:PATH + ";C:\Program Files\PostgreSQL\15\bin",
     "Machine"
   )
   ```
4. Verify: `psql --version`

**nginx for Windows**
1. Download the latest stable nginx for Windows from https://nginx.org/en/download.html
2. Extract to `C:\nginx`
3. Verify: `C:\nginx\nginx.exe -v`

**Visual C++ Build Tools** (required to compile some Python packages):
```powershell
winget install Microsoft.VisualStudio.2022.BuildTools
# During install: select "Desktop development with C++"
```

---

## 3. Directory Layout

Copy the project to a permanent location. The examples below use:

| Platform | Path |
|---|---|
| macOS | `/opt/idmc-portal/` |
| Linux | `/opt/idmc-portal/` |
| Windows | `C:\idmc-portal\` |

```
idmc-portal/
├── auth-service/
├── backend-api/
├── portal-spa/
├── .env                  ← you will create this
├── .env.template
├── docker-compose.yml    ← not used in native mode, kept for reference
└── ...
```

Create the IDMC staging and log directories that the backend-api reads from and writes to:

**macOS / Linux:**
```bash
# Vendor upload staging and trigger scripts
sudo mkdir -p /opt/idmc/staging/{pm_scripts,source_files,target_files,parameter_files}
sudo mkdir -p /opt/idmc/scripts

# Log Analyser browse roots (read-only access by the backend-api)
sudo mkdir -p /var/log/idmc/{auth,api}
sudo mkdir -p /opt/informatica/logs

# Give the user running the services appropriate permissions
sudo chown -R $USER /opt/idmc
chmod -R 750 /opt/idmc
# Log directories: service account writes, backend-api reads
sudo chmod -R 750 /var/log/idmc /opt/informatica/logs
```

**Windows (PowerShell as Administrator):**
```powershell
# Vendor upload staging and trigger scripts
New-Item -ItemType Directory -Force -Path C:\idmc\staging\pm_scripts
New-Item -ItemType Directory -Force -Path C:\idmc\staging\source_files
New-Item -ItemType Directory -Force -Path C:\idmc\staging\target_files
New-Item -ItemType Directory -Force -Path C:\idmc\staging\parameter_files
New-Item -ItemType Directory -Force -Path C:\idmc\scripts

# Log Analyser browse roots
New-Item -ItemType Directory -Force -Path C:\idmc\logs\auth
New-Item -ItemType Directory -Force -Path C:\idmc\logs\api
New-Item -ItemType Directory -Force -Path C:\idmc\logs\agent
```

---

## 4. Database Setup

### 4.1 PostgreSQL (production — all platforms)

**macOS:**
```bash
# Connect as the postgres superuser
psql postgres

# Inside psql:
CREATE USER idmc_portal WITH PASSWORD 'STRONG_PASSWORD_HERE';
CREATE DATABASE idmc_portal OWNER idmc_portal;
\q
```

**Linux:**
```bash
sudo -u postgres psql

# Inside psql:
CREATE USER idmc_portal WITH PASSWORD 'STRONG_PASSWORD_HERE';
CREATE DATABASE idmc_portal OWNER idmc_portal;
\q
```

**Windows (PowerShell):**
```powershell
psql -U postgres -c "CREATE USER idmc_portal WITH PASSWORD 'STRONG_PASSWORD_HERE';"
psql -U postgres -c "CREATE DATABASE idmc_portal OWNER idmc_portal;"
```

The full database URL for PostgreSQL:
```
postgresql+asyncpg://idmc_portal:STRONG_PASSWORD_HERE@127.0.0.1:5432/idmc_portal
```

### 4.2 SQLite (development / single-user only)

No setup needed. Set:
```
DB_URL=sqlite+aiosqlite:///./dev.db
```
in your `.env` and the auth-service will create `dev.db` automatically on first start. **Not suitable for production.**

---

## 5. Secret Generation

All secrets must be generated once per environment and stored in a `.env` file at the project root. **Never commit `.env` to source control.**

### 5.1 macOS / Linux

```bash
cd /opt/idmc-portal

# 1. RSA key pair for JWT signing (RS256, 4096-bit)
openssl genrsa -out jwt_private.pem 4096
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem

# Inline the PEM content (newlines → \n) for use in .env
JWT_SIGNING_KEY=$(awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' jwt_private.pem)
JWT_PUBLIC_KEY=$(awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' jwt_public.pem)

# 2. Random hex secrets
POSTGRES_PASSWORD=$(openssl rand -hex 24)
ADMIN_API_KEY=$(openssl rand -hex 32)
ADMIN_SESSION_SECRET=$(openssl rand -hex 32)
UPLOAD_TOKEN_SECRET=$(openssl rand -hex 32)

# 3. Write .env
cat > .env <<EOF
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
JWT_SIGNING_KEY=${JWT_SIGNING_KEY}
JWT_PUBLIC_KEY=${JWT_PUBLIC_KEY}
ADMIN_API_KEY=${ADMIN_API_KEY}
ADMIN_SESSION_SECRET=${ADMIN_SESSION_SECRET}
UPLOAD_TOKEN_SECRET=${UPLOAD_TOKEN_SECRET}
EOF

echo ".env written. Keep it safe — do not commit to source control."

# Delete raw PEM files from the project root (keep backups elsewhere)
rm jwt_private.pem jwt_public.pem
```

### 5.2 Windows (PowerShell)

```powershell
cd C:\idmc-portal

# The generate-secrets.ps1 script in the project root does all of this:
.\generate-secrets.ps1

# Review the generated .env and fill in PORTAL_BASE_URL and LLM_API_KEY
notepad .env
```

> If `generate-secrets.ps1` is blocked by execution policy:
> ```powershell
> Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
> Unblock-File .\generate-secrets.ps1
> ```

### 5.3 `.env` file structure

The final `.env` must contain these variables (used by all three tiers):

```dotenv
# Database
POSTGRES_PASSWORD=<generated>

# Auth Service
JWT_SIGNING_KEY=<RS256 private key, newlines as \n>
JWT_PUBLIC_KEY=<RS256 public key, newlines as \n>
ADMIN_API_KEY=<hex 32>
ADMIN_SESSION_SECRET=<hex 32>

# Backend API
UPLOAD_TOKEN_SECRET=<hex 32>

# LLM Integration (optional at first boot)
LLM_PROVIDER=anthropic
LLM_API_KEY=
LLM_MODEL=claude-opus-4-8
LLM_MAX_CONTEXT_TOKENS=80000
```

---

## 6. Tier 1 — Auth Service

### 6.1 Create a Python virtual environment

**macOS / Linux:**
```bash
cd /opt/idmc-portal/auth-service
python3.12 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
cd C:\idmc-portal\auth-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 6.2 Install dependencies

The `requirements.txt` covers the core packages. Two additional packages are needed at runtime that are installed separately in the Dockerfile:

**macOS / Linux:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install asyncpg qrcode[pil]
```

**Windows (PowerShell):**
```powershell
pip install --upgrade pip
pip install -r requirements.txt
pip install asyncpg qrcode[pil]
```

> **Why these extras?**
> - `asyncpg` — async PostgreSQL driver required by SQLAlchemy when `DB_URL` starts with `postgresql+asyncpg://`
> - `qrcode[pil]` — generates TOTP enrollment QR codes; requires Pillow as the image backend

### 6.3 Set environment variables

Source your `.env` before starting the service. The auth-service reads these at startup:

| Variable | Required | Description |
|---|---|---|
| `DB_URL` | Yes | Full SQLAlchemy async DB URL |
| `JWT_SIGNING_KEY` | Yes | RS256 private key (PEM, newlines as `\n`) |
| `JWT_PUBLIC_KEY` | Yes | RS256 public key (PEM, newlines as `\n`) |
| `ADMIN_API_KEY` | Yes | Internal API key |
| `ADMIN_SESSION_SECRET` | Yes | Fernet KDF input for TOTP seed encryption |
| `ENROLLMENT_LINK_BASE_URL` | No | Base URL for enrollment links (default: `http://localhost:8000/enroll`) |

**macOS / Linux — load `.env` into the current shell:**
```bash
set -a && source /opt/idmc-portal/.env && set +a

# Then set the DB URL explicitly:
export DB_URL="postgresql+asyncpg://idmc_portal:${POSTGRES_PASSWORD}@127.0.0.1:5432/idmc_portal"
export ENROLLMENT_LINK_BASE_URL="https://your-portal-host.com/enroll"
```

**Windows (PowerShell):**
```powershell
# Load .env into the current session
Get-Content C:\idmc-portal\.env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
}

$env:DB_URL = "postgresql+asyncpg://idmc_portal:$env:POSTGRES_PASSWORD@127.0.0.1:5432/idmc_portal"
$env:ENROLLMENT_LINK_BASE_URL = "https://your-portal-host.com/enroll"
```

### 6.4 Run database migrations

The auth-service uses Alembic to create its schema. Run this once (and again after any upgrade):

**macOS / Linux:**
```bash
cd /opt/idmc-portal/auth-service
source .venv/bin/activate
# DB_URL must be set in your environment (see 6.3)
alembic upgrade head
```

**Windows (PowerShell):**
```powershell
cd C:\idmc-portal\auth-service
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

Expected output: `INFO  [alembic.runtime.migration] Running upgrade  -> 0001, initial schema`

### 6.5 Start the auth service

**macOS / Linux:**
```bash
cd /opt/idmc-portal/auth-service
source .venv/bin/activate
# Bind to loopback — nginx will proxy from outside
uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 2
```

**Windows (PowerShell):**
```powershell
cd C:\idmc-portal\auth-service
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 2
```

Confirm it is running:
```bash
curl http://127.0.0.1:8001/health
# → {"status":"ok"}
```

---

## 7. Tier 2 — Backend API

### 7.1 Create a Python virtual environment

**macOS / Linux:**
```bash
cd /opt/idmc-portal/backend-api
python3.12 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
cd C:\idmc-portal\backend-api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 7.2 Install dependencies

> **Note:** The `backend-api/requirements.txt` in the repository contains a macOS system pip-freeze rather than the project's package list. Install the correct packages directly:

**macOS / Linux:**
```bash
pip install --upgrade pip
pip install \
    "fastapi==0.111.0" \
    "uvicorn[standard]==0.29.0" \
    "httpx==0.27.0" \
    "pyyaml==6.0.1" \
    "python-jose[cryptography]==3.3.0" \
    "cryptography==42.0.7" \
    "anthropic>=0.105" \
    "openai>=2.40" \
    "google-genai>=1.47"
```

**Windows (PowerShell):**
```powershell
pip install --upgrade pip
pip install `
    "fastapi==0.111.0" `
    "uvicorn[standard]==0.29.0" `
    "httpx==0.27.0" `
    "pyyaml==6.0.1" `
    "python-jose[cryptography]==3.3.0" `
    "cryptography==42.0.7" `
    "anthropic>=0.105" `
    "openai>=2.40" `
    "google-genai>=1.47"
```

### 7.3 Prepare config files and directories

The backend-api requires three YAML config files, the staging root, and an LLM settings directory:

**macOS / Linux:**
```bash
# Confirm all three config files exist in the repo
ls /opt/idmc-portal/backend-api/config/paths.yaml       # vendor upload dirs
ls /opt/idmc-portal/backend-api/config/operations.yaml  # trigger scripts
ls /opt/idmc-portal/backend-api/config/log_paths.yaml   # Log Analyser roots

# Create an LLM settings directory
sudo mkdir -p /etc/idmc-portal
sudo chown $USER /etc/idmc-portal
```

**Windows (PowerShell):**
```powershell
# Confirm all three config files exist
Test-Path C:\idmc-portal\backend-api\config\paths.yaml
Test-Path C:\idmc-portal\backend-api\config\operations.yaml
Test-Path C:\idmc-portal\backend-api\config\log_paths.yaml

# LLM settings directory
New-Item -ItemType Directory -Force -Path C:\idmc-portal\llm-settings
```

**About `log_paths.yaml`:** This file controls which directories the Admin Log Analyser can browse. It is separate from `paths.yaml` (vendor upload dirs). Edit it to match the actual log directory paths on your host — the defaults reference `/var/log/idmc/` and `/opt/informatica/logs` (Linux/macOS) or their Windows equivalents. See §7.4 for the `LOG_PATHS_CONFIG` env var that points to this file.

### 7.4 Set environment variables

| Variable | Required | Value |
|---|---|---|
| `AUTH_SERVICE_URL` | Yes | `http://127.0.0.1:8001` |
| `IDMC_STAGING_ROOT` | Yes | `/opt/idmc/staging` (macOS/Linux) or `C:\idmc\staging` (Windows) |
| `ALLOWED_PATHS_CONFIG` | Yes | Path to `paths.yaml` |
| `OPERATIONS_CONFIG` | Yes | Path to `operations.yaml` |
| `LOG_PATHS_CONFIG` | Yes | Path to `log_paths.yaml` |
| `UPLOAD_TOKEN_SECRET` | Yes | From `.env` |
| `ADMIN_SESSION_SECRET` | Yes | From `.env` (same value as auth-service) |
| `LLM_SETTINGS_PATH` | No | Path for encrypted settings file |
| `LLM_PROVIDER` | No | `anthropic` \| `openai` \| `azure_openai` \| `gemini` |
| `LLM_API_KEY` | No | Provider API key (can be set via Admin Console later) |
| `LLM_MODEL` | No | Model identifier |
| `LLM_MAX_CONTEXT_TOKENS` | No | Default: `80000` |

**macOS / Linux:**
```bash
set -a && source /opt/idmc-portal/.env && set +a

export AUTH_SERVICE_URL="http://127.0.0.1:8001"
export IDMC_STAGING_ROOT="/opt/idmc/staging"
export ALLOWED_PATHS_CONFIG="/opt/idmc-portal/backend-api/config/paths.yaml"
export OPERATIONS_CONFIG="/opt/idmc-portal/backend-api/config/operations.yaml"
export LOG_PATHS_CONFIG="/opt/idmc-portal/backend-api/config/log_paths.yaml"
export LLM_SETTINGS_PATH="/etc/idmc-portal/llm-settings.enc"
```

**Windows (PowerShell):**
```powershell
# (load .env as shown in section 6.3)

$env:AUTH_SERVICE_URL       = "http://127.0.0.1:8001"
$env:IDMC_STAGING_ROOT      = "C:\idmc\staging"
$env:ALLOWED_PATHS_CONFIG   = "C:\idmc-portal\backend-api\config\paths.yaml"
$env:OPERATIONS_CONFIG      = "C:\idmc-portal\backend-api\config\operations.yaml"
$env:LOG_PATHS_CONFIG       = "C:\idmc-portal\backend-api\config\log_paths.yaml"
$env:LLM_SETTINGS_PATH      = "C:\idmc-portal\llm-settings\llm-settings.enc"
```

### 7.5 Start the backend API

**macOS / Linux:**
```bash
cd /opt/idmc-portal/backend-api
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8002 --workers 2
```

**Windows (PowerShell):**
```powershell
cd C:\idmc-portal\backend-api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8002 --workers 2
```

Confirm:
```bash
curl http://127.0.0.1:8002/health
# → {"status":"ok"}
```

---

## 8. Tier 3 — Portal SPA + nginx

### 8.1 Build the React SPA

**macOS / Linux:**
```bash
cd /opt/idmc-portal/portal-spa
npm ci
npm run build
# Output is in: portal-spa/dist/
```

**Windows (PowerShell):**
```powershell
cd C:\idmc-portal\portal-spa
npm ci
npm run build
# Output is in: portal-spa\dist\
```

The `dist/` directory contains the compiled static files. This build step only needs to be re-run when portal source code changes.

### 8.2 Configure nginx

nginx needs to:
1. Serve the compiled SPA static files
2. Proxy `/auth/`, `/enroll`, `/admin/auth/`, `/admin/(vendors|devices|…)` → auth-service on port 8001
3. Proxy `/upload/`, `/operations/`, `/portal/`, `/admin/logs/`, `/admin/llm/`, `/admin/extensions` → backend-api on port 8002

The project ships a ready-made `portal-spa/nginx.conf`. Copy and adapt it.

#### macOS (Homebrew nginx)

Homebrew's nginx serves from `/opt/homebrew/var/www` and reads config from `/opt/homebrew/etc/nginx/`.

```bash
# Copy the built SPA into nginx's web root
cp -r /opt/idmc-portal/portal-spa/dist/* /opt/homebrew/var/www/

# Install the nginx config
cp /opt/idmc-portal/portal-spa/nginx.conf \
   /opt/homebrew/etc/nginx/servers/idmc-portal.conf

# Disable the default server block so it doesn't conflict on port 80
# Edit /opt/homebrew/etc/nginx/nginx.conf and remove or comment out:
#   include servers/*;
# then re-add just:
#   include servers/idmc-portal.conf;

# Test and reload
nginx -t
brew services restart nginx
```

#### Linux (system nginx)

```bash
# Copy built SPA
sudo mkdir -p /var/www/idmc-portal
sudo cp -r /opt/idmc-portal/portal-spa/dist/* /var/www/idmc-portal/

# Install config
sudo cp /opt/idmc-portal/portal-spa/nginx.conf \
        /etc/nginx/sites-available/idmc-portal

# Update the root path inside the config to point to /var/www/idmc-portal
sudo sed -i 's|root /usr/share/nginx/html;|root /var/www/idmc-portal;|' \
    /etc/nginx/sites-available/idmc-portal

# Enable the site
sudo ln -sf /etc/nginx/sites-available/idmc-portal \
            /etc/nginx/sites-enabled/idmc-portal

# Disable the default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

#### Windows

```powershell
# Copy built SPA into nginx html directory
$NginxRoot = "C:\nginx"
Copy-Item -Recurse -Force C:\idmc-portal\portal-spa\dist\* "$NginxRoot\html\"

# Replace the default nginx config with the project config
Copy-Item C:\idmc-portal\portal-spa\nginx.conf "$NginxRoot\conf\nginx.conf" -Force

# Edit C:\nginx\conf\nginx.conf:
# - Change:  root /usr/share/nginx/html;
# - To:      root html;       (nginx on Windows uses a relative html/ path)
# - Also remove or replace any Windows-incompatible paths
(Get-Content "$NginxRoot\conf\nginx.conf") `
    -replace 'root /usr/share/nginx/html;', 'root html;' |
    Set-Content "$NginxRoot\conf\nginx.conf"

# Test the config
& "$NginxRoot\nginx.exe" -t

# Start nginx
Start-Process "$NginxRoot\nginx.exe"

# Verify
Invoke-WebRequest http://localhost/ -UseBasicParsing | Select-Object StatusCode
```

> **Windows port 80 conflict:** IIS binds to port 80 by default on Windows Server. Stop it first:
> ```powershell
> Stop-Service W3SVC
> Set-Service W3SVC -StartupType Disabled
> ```

### 8.3 nginx config adjustments for native mode

The shipped `nginx.conf` uses Docker service hostnames (`auth-service`, `backend-api`). For native mode, update the upstream addresses in the config:

| Original (Docker) | Native replacement |
|---|---|
| `proxy_pass http://auth-service:8001;` | `proxy_pass http://127.0.0.1:8001;` |
| `proxy_pass http://backend-api:8002;` | `proxy_pass http://127.0.0.1:8002;` |

**macOS / Linux — sed one-liner:**
```bash
sudo sed -i \
    -e 's|http://auth-service:8001|http://127.0.0.1:8001|g' \
    -e 's|http://backend-api:8002|http://127.0.0.1:8002|g' \
    /etc/nginx/sites-available/idmc-portal   # adjust path for macOS
```

**Windows (PowerShell):**
```powershell
(Get-Content "C:\nginx\conf\nginx.conf") `
    -replace 'http://auth-service:8001', 'http://127.0.0.1:8001' `
    -replace 'http://backend-api:8002',  'http://127.0.0.1:8002' |
    Set-Content "C:\nginx\conf\nginx.conf"
```

Reload nginx after any config change:

| Platform | Command |
|---|---|
| macOS | `brew services restart nginx` |
| Linux | `sudo systemctl reload nginx` |
| Windows | `C:\nginx\nginx.exe -s reload` |

### 8.4 Development mode (optional — skip nginx)

During development you can run the SPA with Vite's dev server instead of building and serving via nginx. Vite's built-in proxy (defined in `vite.config.ts`) forwards API calls to the running Python services.

```bash
cd /opt/idmc-portal/portal-spa   # or C:\idmc-portal\portal-spa
npm run dev
# Vite serves at: http://localhost:5173
```

No nginx needed in dev mode. The SPA hot-reloads on source changes.

---

## 9. First Admin Account

After the auth-service is running and migrations have completed, seed the first admin:

**macOS / Linux:**
```bash
cd /opt/idmc-portal/auth-service
source .venv/bin/activate

# Environment variables must be set (section 6.3)
python seed_admin.py --username sysadmin --password "$(openssl rand -base64 16)"
```

**Windows (PowerShell):**
```powershell
cd C:\idmc-portal\auth-service
.\.venv\Scripts\Activate.ps1

# Environment variables must be set (section 6.3)
python seed_admin.py --username sysadmin --password "InitialP@ss1!"
```

> Record the password securely — it cannot be recovered, only reset by running `seed_admin.py` again with `--password`.

Then log in at `http://localhost/admin/login` (or `http://localhost:5173/admin/login` in dev mode).

---

## 10. Running All Three Tiers

Each tier runs in its own terminal (or background process — see §11). The startup order matters:

```
PostgreSQL (must be up)
    ↓
Tier 1: auth-service (port 8001)
    ↓
Tier 2: backend-api  (port 8002)
    ↓
Tier 3: nginx + SPA  (port 80)
```

### 10.1 Convenience startup script — macOS / Linux

Save as `/opt/idmc-portal/start-native.sh`:

```bash
#!/usr/bin/env bash
set -e

PROJECT=/opt/idmc-portal

# Load secrets
set -a && source "$PROJECT/.env" && set +a

# ── Auth Service ──────────────────────────────────────────────────────────────
export DB_URL="postgresql+asyncpg://idmc_portal:${POSTGRES_PASSWORD}@127.0.0.1:5432/idmc_portal"
export ENROLLMENT_LINK_BASE_URL="http://localhost/enroll"

echo "[1/3] Starting auth-service on 127.0.0.1:8001 ..."
cd "$PROJECT/auth-service"
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 2 &
AUTH_PID=$!
deactivate

# ── Backend API ───────────────────────────────────────────────────────────────
export AUTH_SERVICE_URL="http://127.0.0.1:8001"
export IDMC_STAGING_ROOT="/opt/idmc/staging"
export ALLOWED_PATHS_CONFIG="$PROJECT/backend-api/config/paths.yaml"
export OPERATIONS_CONFIG="$PROJECT/backend-api/config/operations.yaml"
export LOG_PATHS_CONFIG="$PROJECT/backend-api/config/log_paths.yaml"
export LLM_SETTINGS_PATH="/etc/idmc-portal/llm-settings.enc"

echo "[2/3] Starting backend-api on 127.0.0.1:8002 ..."
cd "$PROJECT/backend-api"
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8002 --workers 2 &
API_PID=$!
deactivate

# ── nginx ─────────────────────────────────────────────────────────────────────
echo "[3/3] Reloading nginx ..."
sudo nginx -s reload 2>/dev/null || sudo systemctl reload nginx

echo ""
echo "Stack is up:"
echo "  auth-service  PID $AUTH_PID  → http://127.0.0.1:8001/health"
echo "  backend-api   PID $API_PID   → http://127.0.0.1:8002/health"
echo "  portal        → http://localhost/"
echo ""
echo "Stop with:  kill $AUTH_PID $API_PID && sudo nginx -s stop"
```

```bash
chmod +x /opt/idmc-portal/start-native.sh
/opt/idmc-portal/start-native.sh
```

### 10.2 Convenience startup script — Windows (PowerShell)

Save as `C:\idmc-portal\Start-Native.ps1`:

```powershell
param()
$ErrorActionPreference = "Stop"
$Project = "C:\idmc-portal"

# Load .env
Get-Content "$Project\.env" | ForEach-Object {
    if ($_ -match '^\s*([^#=][^=]*)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
}

# Auth Service
$env:DB_URL = "postgresql+asyncpg://idmc_portal:$env:POSTGRES_PASSWORD@127.0.0.1:5432/idmc_portal"
$env:ENROLLMENT_LINK_BASE_URL = "http://localhost/enroll"
Write-Host "[1/3] Starting auth-service on 127.0.0.1:8001 ..."
Set-Location "$Project\auth-service"
& "$Project\auth-service\.venv\Scripts\alembic.exe" upgrade head
$AuthJob = Start-Process -FilePath "$Project\auth-service\.venv\Scripts\uvicorn.exe" `
    -ArgumentList "app.main:app","--host","127.0.0.1","--port","8001","--workers","2" `
    -PassThru -NoNewWindow

# Backend API
$env:AUTH_SERVICE_URL      = "http://127.0.0.1:8001"
$env:IDMC_STAGING_ROOT     = "C:\idmc\staging"
$env:ALLOWED_PATHS_CONFIG  = "$Project\backend-api\config\paths.yaml"
$env:OPERATIONS_CONFIG     = "$Project\backend-api\config\operations.yaml"
$env:LOG_PATHS_CONFIG      = "$Project\backend-api\config\log_paths.yaml"
$env:LLM_SETTINGS_PATH     = "$Project\llm-settings\llm-settings.enc"
Write-Host "[2/3] Starting backend-api on 127.0.0.1:8002 ..."
$ApiJob = Start-Process -FilePath "$Project\backend-api\.venv\Scripts\uvicorn.exe" `
    -ArgumentList "app.main:app","--host","127.0.0.1","--port","8002","--workers","2" `
    -PassThru -NoNewWindow

# nginx
Write-Host "[3/3] Starting nginx ..."
Start-Process "C:\nginx\nginx.exe" -NoNewWindow

Write-Host ""
Write-Host "Stack is up:"
Write-Host "  auth-service  PID $($AuthJob.Id)  -> http://127.0.0.1:8001/health"
Write-Host "  backend-api   PID $($ApiJob.Id)   -> http://127.0.0.1:8002/health"
Write-Host "  portal        -> http://localhost/"
```

```powershell
.\Start-Native.ps1
```

---

## 11. Process Management

For long-running production deployments, use the platform's native process supervisor instead of background `&` jobs.

### 11.1 Linux — systemd

Create a service file for each tier.

**`/etc/systemd/system/idmc-auth.service`:**
```ini
[Unit]
Description=IDMC Auth Service
After=network.target postgresql.service

[Service]
Type=simple
User=idmc
WorkingDirectory=/opt/idmc-portal/auth-service
EnvironmentFile=/opt/idmc-portal/.env.systemd
ExecStartPre=/opt/idmc-portal/auth-service/.venv/bin/alembic upgrade head
ExecStart=/opt/idmc-portal/auth-service/.venv/bin/uvicorn \
    app.main:app --host 127.0.0.1 --port 8001 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/idmc-api.service`:**
```ini
[Unit]
Description=IDMC Backend API
After=network.target idmc-auth.service

[Service]
Type=simple
User=idmc
WorkingDirectory=/opt/idmc-portal/backend-api
EnvironmentFile=/opt/idmc-portal/.env.systemd
ExecStart=/opt/idmc-portal/backend-api/.venv/bin/uvicorn \
    app.main:app --host 127.0.0.1 --port 8002 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> **`.env.systemd`** must use `KEY=VALUE` format without `export` and with literal PEM newlines escaped as `\n`. systemd reads it natively.

```bash
# Create a restricted service account
sudo useradd -r -s /sbin/nologin idmc
sudo chown -R idmc /opt/idmc /etc/idmc-portal

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now idmc-auth idmc-api nginx

# Check status
sudo systemctl status idmc-auth idmc-api nginx
```

### 11.2 macOS — launchd

Save as `/Library/LaunchDaemons/com.idmc.auth.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>          <string>com.idmc.auth</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/idmc-portal/auth-service/.venv/bin/uvicorn</string>
    <string>app.main:app</string>
    <string>--host</string><string>127.0.0.1</string>
    <string>--port</string> <string>8001</string>
    <string>--workers</string><string>2</string>
  </array>
  <key>WorkingDirectory</key><string>/opt/idmc-portal/auth-service</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>DB_URL</key>             <string>postgresql+asyncpg://idmc_portal:PASS@127.0.0.1:5432/idmc_portal</string>
    <key>JWT_SIGNING_KEY</key>    <string><!-- paste inline PEM --></string>
    <key>JWT_PUBLIC_KEY</key>     <string><!-- paste inline PEM --></string>
    <key>ADMIN_API_KEY</key>      <string><!-- value --></string>
    <key>ADMIN_SESSION_SECRET</key><string><!-- value --></string>
  </dict>
  <key>RunAtLoad</key>    <true/>
  <key>KeepAlive</key>    <true/>
  <key>StandardOutPath</key><string>/var/log/idmc-auth.log</string>
  <key>StandardErrorPath</key><string>/var/log/idmc-auth.log</string>
</dict>
</plist>
```

```bash
sudo launchctl load /Library/LaunchDaemons/com.idmc.auth.plist
sudo launchctl load /Library/LaunchDaemons/com.idmc.api.plist
```

Create a matching `com.idmc.api.plist` for the backend-api (port 8002).

### 11.3 Windows — NSSM (Non-Sucking Service Manager)

[NSSM](https://nssm.cc) wraps any executable as a Windows Service.

```powershell
# Download nssm from https://nssm.cc/download and place nssm.exe in C:\Windows\System32

# Install auth-service as a Windows Service
nssm install IDMC-Auth "C:\idmc-portal\auth-service\.venv\Scripts\uvicorn.exe"
nssm set IDMC-Auth AppParameters "app.main:app --host 127.0.0.1 --port 8001 --workers 2"
nssm set IDMC-Auth AppDirectory  "C:\idmc-portal\auth-service"
nssm set IDMC-Auth AppEnvironmentExtra `
    "DB_URL=postgresql+asyncpg://idmc_portal:PASS@127.0.0.1:5432/idmc_portal" `
    "JWT_SIGNING_KEY=..." `
    "JWT_PUBLIC_KEY=..." `
    "ADMIN_API_KEY=..." `
    "ADMIN_SESSION_SECRET=..."
nssm set IDMC-Auth Start SERVICE_AUTO_START
nssm start IDMC-Auth

# Install backend-api
nssm install IDMC-API "C:\idmc-portal\backend-api\.venv\Scripts\uvicorn.exe"
nssm set IDMC-API AppParameters "app.main:app --host 127.0.0.1 --port 8002 --workers 2"
nssm set IDMC-API AppDirectory  "C:\idmc-portal\backend-api"
nssm set IDMC-API AppEnvironmentExtra `
    "AUTH_SERVICE_URL=http://127.0.0.1:8001" `
    "IDMC_STAGING_ROOT=C:\idmc\staging" `
    "ALLOWED_PATHS_CONFIG=C:\idmc-portal\backend-api\config\paths.yaml" `
    "OPERATIONS_CONFIG=C:\idmc-portal\backend-api\config\operations.yaml" `
    "LOG_PATHS_CONFIG=C:\idmc-portal\backend-api\config\log_paths.yaml" `
    "UPLOAD_TOKEN_SECRET=..." `
    "ADMIN_SESSION_SECRET=..."
nssm set IDMC-API Start SERVICE_AUTO_START
nssm start IDMC-API

# Install nginx as a service
nssm install nginx "C:\nginx\nginx.exe"
nssm set nginx AppDirectory "C:\nginx"
nssm set nginx Start SERVICE_AUTO_START
nssm start nginx
```

Check service status:
```powershell
Get-Service IDMC-Auth, IDMC-API, nginx
```

---

## 12. Verifying the Stack

Once all three tiers are running, run these checks in order:

```bash
# 1. Auth service health
curl http://127.0.0.1:8001/health
# → {"status":"ok"}

# 2. Backend API health
curl http://127.0.0.1:8002/health
# → {"status":"ok"}

# 3. Portal served by nginx
curl http://localhost/
# → HTML page (200 OK)

# 4. nginx proxy to auth (should get 401, not 502)
curl -s -o /dev/null -w "%{http_code}" http://localhost/auth/validate
# → 401  (means nginx reached auth-service and got a real response)

# 5. nginx proxy to backend (should get 401, not 502)
curl -s -o /dev/null -w "%{http_code}" http://localhost/upload/request
# → 401

# 6. Log Analyser roots loaded (should return roots array, not 400/500)
curl -s -o /dev/null -w "%{http_code}" http://localhost/admin/logs/tree
# → 401  (auth required — means the endpoint is reachable and log_paths.yaml was parsed)

# 7. Admin login (browser or curl)
# Navigate to: http://localhost/admin/login
# Then verify Admin Console → Log Analyser → FileTree shows the configured roots
```

If any check returns **502 Bad Gateway**, nginx cannot reach that service — confirm the service is running and its bind address/port matches the nginx `proxy_pass` line.

If check 6 returns **500**, the backend-api likely could not read `log_paths.yaml` — confirm `LOG_PATHS_CONFIG` is set and the file exists at that path.

---

## 13. Environment Variable Reference

Complete list of all environment variables consumed by each service.

### Auth Service

| Variable | Required | Default | Description |
|---|---|---|---|
| `DB_URL` | Yes | `sqlite+aiosqlite:///./dev.db` | SQLAlchemy async database URL |
| `JWT_SIGNING_KEY` | Yes | — | RS256 private key (PEM, `\n`-escaped) |
| `JWT_PUBLIC_KEY` | Yes | — | RS256 public key (PEM, `\n`-escaped) |
| `ADMIN_API_KEY` | Yes | — | Internal API key (hex 32) |
| `ADMIN_SESSION_SECRET` | Yes | — | TOTP seed encryption KDF input (hex 32) |
| `ENROLLMENT_LINK_BASE_URL` | No | `http://localhost:8000/enroll` | Base URL embedded in enrollment QR labels |

### Backend API

| Variable | Required | Default | Description |
|---|---|---|---|
| `AUTH_SERVICE_URL` | Yes | — | `http://127.0.0.1:8001` |
| `IDMC_STAGING_ROOT` | Yes | — | Absolute path to staging root directory |
| `ALLOWED_PATHS_CONFIG` | Yes | — | Absolute path to `paths.yaml` |
| `OPERATIONS_CONFIG` | Yes | — | Absolute path to `operations.yaml` |
| `LOG_PATHS_CONFIG` | Yes | — | Absolute path to `log_paths.yaml` |
| `UPLOAD_TOKEN_SECRET` | Yes | — | HMAC key for upload tokens (hex 32) |
| `ADMIN_SESSION_SECRET` | Yes | — | LLM settings encryption KDF input (must match auth-service) |
| `LLM_SETTINGS_PATH` | No | `/tmp/llm-settings.enc` | Path for encrypted LLM settings file |
| `LLM_PROVIDER` | No | `anthropic` | Seed provider for first boot |
| `LLM_API_KEY` | No | `""` | Seed API key for first boot |
| `LLM_MODEL` | No | `claude-opus-4-8` | Seed model for first boot |
| `LLM_MAX_CONTEXT_TOKENS` | No | `80000` | Seed token limit for first boot |

> **`log_paths.yaml` on Windows:** The default file references Linux paths (`/var/log/idmc/auth` etc.). Update the `path` values to Windows paths, e.g.:
> ```yaml
> roots:
>   - name: staging
>     label: "IDMC Staging"
>     path: C:\idmc\staging
>   - name: auth_logs
>     label: "Auth Service Logs"
>     path: C:\idmc\logs\auth
>   - name: api_logs
>     label: "Backend API Logs"
>     path: C:\idmc\logs\api
>   - name: agent_logs
>     label: "IDMC Secure Agent Logs"
>     path: C:\idmc\logs\agent
> ```

### Portal SPA (build-time only)

The SPA has no runtime environment variables — all API URLs are relative paths proxied by nginx. The `vite.config.ts` proxy settings are used only during `npm run dev`.

---

## 14. Moved or copied project folder

`dev-setup-mac.sh` bakes the **absolute path** of the project root into several generated files at first run:

- `.env.local` — `JWT_SIGNING_KEY_FILE`, `JWT_PUBLIC_KEY_FILE`, `IDMC_STAGING_ROOT`, `ALLOWED_PATHS_CONFIG`, `OPERATIONS_CONFIG`, `LOG_PATHS_CONFIG`, `LLM_SETTINGS_PATH`
- `local-data/log_paths.local.yaml` — all `path:` entries under `roots:`

If you copy, rename, or move the project directory (e.g. duplicating it as a working copy), these files still point at the **old** location and services will fail at startup with errors such as:

```
FATAL: required environment variable 'JWT_SIGNING_KEY' is not set
```

(because `load-env.sh` tries to `cat` a PEM file that no longer exists at the old path).

**Fix:**

1. Delete `.env.local` and re-run `./dev-setup-mac.sh` — it detects the missing file and regenerates everything (including a **new** RSA key pair and secrets) against the current path. This also means any previously-issued JWTs and the admin login are reset — reseed with `seed_admin.py` (§9).
2. If you want to **keep** the existing keys/secrets (e.g. you've already enrolled TOTP devices), hand-edit the absolute paths in `.env.local` and `local-data/log_paths.local.yaml` instead of deleting them, and leave the PEM files under `local-data/` where they are.
3. Also check `auth-service/.venv` and `backend-api/.venv` — if the old project directory itself still exists, Python venvs created with `python -m venv` embed an absolute `home` path in `pyvenv.cfg` and their `bin/python3` symlinks may resolve into the old (and possibly now-deleted) `.venv`. Symptom: `pip`/`python` inside the venv fail with "no such file or directory" even though the venv folder is present. Fix: delete and recreate the venv (`rm -rf .venv && python3.12 -m venv .venv`, then reinstall deps per §6.2 / §7.2).

> **Note on quoting:** if the new project path contains spaces (as in a folder named e.g. `_Small Projects/...`), unquoted `KEY=/path/with spaces/file` lines in `.env.local` will be word-split by `load-env.sh`'s plain `source`/`set -a`, truncating the value at the first space and breaking every downstream path. Quote path values in `.env.local`: `KEY="/path/with spaces/file"`.

---

*End of Native Setup Guide — IDMC Vendor Portal v1.4 — June 2026*
*Platforms: macOS (Intel + Apple Silicon) · Linux (Ubuntu 22.04/24.04) · Windows Server 2019+ / Windows 11*
