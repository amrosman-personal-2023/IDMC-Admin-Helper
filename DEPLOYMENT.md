# IDMC Vendor Portal — Deployment Guide
**Version 1.4  ·  June 2026  ·  Classification: Internal — Restricted**
**Platforms: Linux (Ubuntu 22.04+) · Windows Server 2019+ · Windows 11 (Docker Desktop)**

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Host Requirements](#3-host-requirements)
4. [Port Reference](#4-port-reference)
5. [Library & Dependency Reference](#5-library--dependency-reference)
6. [First-Time Setup — Linux](#6-first-time-setup--linux)
7. [First-Time Setup — Windows](#7-first-time-setup--windows)
8. [Secret Generation](#8-secret-generation)
9. [Building & Releasing — Linux](#9-building--releasing--linux)
10. [Building & Releasing — Windows](#10-building--releasing--windows)
11. [Production Deployment](#11-production-deployment)
12. [TLS / HTTPS Configuration](#12-tls--https-configuration)
13. [Database Setup](#13-database-setup)
14. [IDMC Directory Structure](#14-idmc-directory-structure)
15. [Log Analyser Directory Configuration](#15-log-analyser-directory-configuration)
16. [LLM Integration Setup](#16-llm-integration-setup)
17. [First-Boot Admin Seeding](#17-first-boot-admin-seeding)
18. [Health Checks & Monitoring](#18-health-checks--monitoring)
19. [Backup & Recovery](#19-backup--recovery)
20. [Scaling](#20-scaling)
21. [Troubleshooting](#21-troubleshooting)
22. [Security Checklist](#22-security-checklist)

---

## 1. Architecture Overview

```
Internet
    │  HTTPS :443
    ▼
┌───────────────────────────────────────┐
│  portal  (nginx + React SPA)          │  Port 80 / 443  — public
│  Docker image: idmc/portal            │
└───────┬──────────────┬────────────────┘
        │              │
        │ :8001         │ :8002
        ▼              ▼
┌──────────────┐  ┌──────────────────────────────┐
│ auth-service │  │ backend-api                  │
│ idmc/auth-   │  │ idmc/backend-api             │
│ service      │  │                              │
│              │  │ • File upload / ops          │
│ • JWT auth   │  │ • Log analyser               │
│ • TOTP       │  │ • LLM proxy (SSE)            │
│ • Admin auth │  │ • Allowed extensions         │
│ • Audit log  │◄─┤ (calls /auth/validate)       │
└──────┬───────┘  └────────────────┬─────────────┘
       │                           │
       ▼                           ▼
┌──────────────┐         ┌─────────────────────┐
│  PostgreSQL  │         │  IDMC Staging Dirs  │
│  port 5432   │         │  /opt/idmc/staging  │
│  (internal)  │         │  (host bind mount)  │
└──────────────┘         └─────────────────────┘
```

All inter-service traffic travels on an isolated Docker bridge network (`internal`).
**Only `portal` (nginx) is reachable from the internet.**

---

## 2. Prerequisites

### Required software — all platforms

| Software | Minimum version | Purpose |
|---|---|---|
| Docker Engine / Docker Desktop | 24.0 / 4.30 | Container runtime |
| Docker Compose | 2.20 plugin or 1.29 standalone | Multi-container orchestration |

### Required software — Linux / macOS

| Software | Minimum version | Purpose |
|---|---|---|
| bash | 4.0+ | `release.sh` script |
| OpenSSL | 1.1.1+ | Secret generation (`generate-secrets.sh`) |
| curl | any | Health checks in release script |

### Required software — Windows

| Software | Minimum version | Notes |
|---|---|---|
| Docker Desktop for Windows | 4.30 | Must run in **Linux containers** mode |
| PowerShell | 5.1 (built-in) or 7.x | `release.ps1` and `generate-secrets.ps1` |
| Windows Subsystem for Linux (WSL 2) | WSL 2 | Strongly recommended — improves Docker performance significantly |

> **Linux containers mode is mandatory.** The application containers are Linux-based.
> To verify: right-click Docker Desktop tray icon — it should say "Switch to Windows containers"
> (meaning Linux containers is currently active).

### Optional — local development / testing (all platforms)

| Software | Minimum version | Purpose |
|---|---|---|
| Python | 3.12 | Running backend tests locally |
| Node.js | 20 LTS | Running frontend tests locally |
| npm | 10 | Frontend package management |

---

### Install on Ubuntu 22.04

```bash
# Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # re-login after this

# Docker Compose plugin
sudo apt-get install docker-compose-plugin

# OpenSSL (usually pre-installed)
sudo apt-get install openssl
```

### Install on macOS

```bash
# Docker Desktop (includes Compose)
brew install --cask docker

# Or standalone Compose
brew install docker-compose
```

### Install on Windows

1. **Enable WSL 2** (run as Administrator):
   ```powershell
   wsl --install
   # Restart when prompted
   wsl --set-default-version 2
   ```

2. **Install Docker Desktop:**
   - Download from https://www.docker.com/products/docker-desktop
   - During setup: check "Use WSL 2 instead of Hyper-V"
   - After install: Settings → General → "Use WSL 2 based engine" ✓

3. **Verify Linux containers mode:**
   ```powershell
   docker info --format "{{.OSType}}"
   # Must output: linux
   ```

4. **Set PowerShell execution policy** (run once as Administrator):
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

5. **Verify:**
   ```powershell
   docker version
   docker compose version
   # Both should return version numbers
   ```

---

## 3. Host Requirements

### Minimum (single host, production)

| Resource | Linux minimum | Linux recommended | Windows minimum | Windows recommended |
|---|---|---|---|---|
| CPU | 2 cores | 4 cores | 4 cores | 6 cores |
| RAM | 4 GB | 8 GB | 8 GB | 16 GB |
| Disk (OS + Docker) | 20 GB | 40 GB | 40 GB | 60 GB |
| Disk (IDMC staging) | 50 GB+ | 100 GB+ | 50 GB+ | 100 GB+ |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS | Windows Server 2019+ or Windows 11 | Windows Server 2022 |

> **Windows RAM note:** Docker Desktop on Windows runs a lightweight Linux VM (WSL 2 or Hyper-V).
> The VM consumes approximately 2–4 GB of RAM overhead on top of the application requirements.
> WSL 2 is more memory-efficient than Hyper-V.

### Windows-specific requirements

| Feature | Requirement |
|---|---|
| Virtualization | Intel VT-x or AMD-V enabled in BIOS/UEFI |
| Hyper-V (fallback) | Enabled in Windows Features (if not using WSL 2) |
| WSL 2 kernel | Windows 10 build 19041+ or Windows Server 2022 |
| File sharing | IDMC staging path added to Docker Desktop → Resources → File Sharing |

### Docker resource limits (set in docker-compose.yml if needed)

```yaml
# Add to any service block:
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
```

Recommended starting limits:

| Service | CPU | Memory |
|---|---|---|
| auth-service | 0.5 | 256 MB |
| backend-api | 1.0 | 512 MB |
| portal (nginx) | 0.25 | 64 MB |
| postgres | 1.0 | 512 MB |

---

## 4. Port Reference

### External (open on firewall / security group)

| Port | Protocol | Service | Notes |
|---|---|---|---|
| 80 | TCP | portal (nginx) | Redirect to 443 in production |
| 443 | TCP | portal (nginx) | HTTPS — primary access point |

### Internal (Docker network only — do NOT expose)

| Port | Service | Callers |
|---|---|---|
| 8001 | auth-service | portal (nginx proxy), backend-api |
| 8002 | backend-api | portal (nginx proxy) |
| 5432 | postgres | auth-service only |

### Firewall rules summary (Ubuntu ufw)

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
# Everything else is blocked by default — Docker manages its own iptables rules
```

> **Important:** Docker bypasses ufw for container-to-container traffic.
> The `internal: true` flag on the `internal` Docker network prevents external
> access even if ufw is misconfigured.

---

## 5. Library & Dependency Reference

### Auth Service (`auth-service/`)

| Library | Version | Purpose |
|---|---|---|
| fastapi | 0.111.0 | HTTP API framework |
| uvicorn[standard] | 0.29.0 | ASGI server (with uvloop + httptools) |
| sqlalchemy | 2.0.30 | Async ORM |
| alembic | 1.13.1 | Database schema migrations |
| psycopg2-binary | 2.9.9 | PostgreSQL driver (sync, for Alembic) |
| asyncpg | latest | PostgreSQL async driver (runtime) |
| aiosqlite | 0.20.0 | SQLite async driver (dev / test) |
| bcrypt | 4.1.3 | Password hashing (Argon2-equivalent strength at rounds=12) |
| cryptography | 42.0.7 | Fernet encryption, RSA key ops |
| python-jose[cryptography] | 3.3.0 | JWT issuance and validation (RS256) |
| pyotp | 2.9.0 | RFC 6238 TOTP generation and verification |
| python-multipart | 0.0.9 | Form data parsing |
| httpx | 0.27.0 | Internal HTTP client (test/lint only in this service) |
| greenlet | 3.0.3 | SQLAlchemy async bridge |

### Backend API (`backend-api/`)

| Library | Version | Purpose |
|---|---|---|
| fastapi | 0.111.0 | HTTP API framework |
| uvicorn[standard] | 0.29.0 | ASGI server |
| httpx | 0.27.0 | Calls auth-service /auth/validate |
| pyyaml | 6.0.1 | Reads paths.yaml, operations.yaml, and log_paths.yaml |
| python-jose[cryptography] | 3.3.0 | JWT validation in upload token signing |
| anthropic | 0.105+ | Anthropic Claude API streaming |
| openai | 2.40+ | OpenAI / Azure OpenAI streaming |
| google-genai | 1.47+ | Google Gemini API streaming |
| cryptography | (via anthropic) | Fernet for LLM settings encryption |

### Portal SPA (`portal-spa/`)

| Library | Version | Purpose |
|---|---|---|
| react | 18.3 | UI framework |
| react-dom | 18.3 | DOM rendering |
| react-router-dom | 6.23 | Client-side routing |
| qrcode | 1.5.4 | Google Authenticator QR code generation |
| vite | 5.2 | Build tool and dev server |
| typescript | 5.4 | Type safety |

### Infrastructure

| Component | Image | Purpose |
|---|---|---|
| nginx | nginx:1.27-alpine | Reverse proxy, SPA server, TLS termination |
| PostgreSQL | postgres:15-alpine | Production database |
| Python | python:3.12-slim | Auth-service and backend-api base |
| Node | node:20-alpine | SPA build stage |

---

## 6. First-Time Setup — Linux

```bash
# 1. Clone / copy the project
cd /opt
sudo mkdir idmc-portal && sudo chown $USER idmc-portal
# (copy project files here)
cd idmc-portal

# 2. Copy the env template
cp .env.template .env

# 3. Generate all secrets (see Section 7)
./release.sh --help   # prints usage

# 4. Fill in .env with generated values

# 5. Create staging and log directories on the host
sudo mkdir -p /opt/idmc/staging/{pm_scripts,source_files,target_files,parameter_files}
sudo mkdir -p /opt/idmc/scripts
sudo mkdir -p /var/log/idmc/{auth,api}
sudo mkdir -p /opt/informatica/logs
sudo chown -R 1000:1000 /opt/idmc /var/log/idmc /opt/informatica/logs   # matches idmc user inside containers

# 6. Run the release build
./release.sh --tag v1.3.0

# 7. Start the stack
TAG=v1.3.0 docker compose --env-file .env up -d

# 8. Seed the first admin account
docker compose exec auth-service python seed_admin.py \
    --username sysadmin --password "$(openssl rand -base64 16)"
```

---

## 7. First-Time Setup — Windows

```powershell
# 1. Open PowerShell as Administrator and navigate to the project folder
cd C:\idmc-portal     # or wherever you placed the project files

# 2. Generate all secrets (writes a .env file with all required values)
.\generate-secrets.ps1
# Edit .env: set PORTAL_BASE_URL and optionally LLM_API_KEY

# 3. Create IDMC staging and log directories on the host
New-Item -ItemType Directory -Force -Path C:\idmc\staging\pm_scripts
New-Item -ItemType Directory -Force -Path C:\idmc\staging\source_files
New-Item -ItemType Directory -Force -Path C:\idmc\staging\target_files
New-Item -ItemType Directory -Force -Path C:\idmc\staging\parameter_files
New-Item -ItemType Directory -Force -Path C:\idmc\scripts
New-Item -ItemType Directory -Force -Path C:\idmc\logs\auth
New-Item -ItemType Directory -Force -Path C:\idmc\logs\api
New-Item -ItemType Directory -Force -Path C:\idmc\logs\agent

# 4. Add C:\idmc to Docker Desktop file sharing
# Docker Desktop → Settings → Resources → File Sharing → Add C:\idmc → Apply & Restart

# 5. Update docker-compose.windows.yml if using host-path bind mounts:
#    volumes:
#      - //c/idmc/staging:/opt/idmc/staging   (forward slashes required)
#      - //c/idmc/scripts:/opt/idmc/scripts

# 6. Build and run (using both base and Windows override)
$env:TAG = 'latest'
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env up -d

# 7. Seed the first admin account
docker compose exec auth-service python seed_admin.py --username sysadmin
```

### Windows path format for Docker volumes

Docker on Windows requires forward slashes and the drive letter in lowercase:

```powershell
# ✓ Correct
//c/idmc/staging:/opt/idmc/staging

# ✗ Wrong — will silently create a named volume instead of binding to host
C:\idmc\staging:/opt/idmc/staging
```

### Windows Defender / antivirus

Docker bind-mounted directories should be excluded from real-time scanning to avoid
performance degradation and potential file lock conflicts during atomic writes:

```powershell
# Run as Administrator
Add-MpPreference -ExclusionPath "C:\idmc"
Add-MpPreference -ExclusionPath "$env:USERPROFILE\.docker"
Add-MpPreference -ExclusionProcess "com.docker.backend.exe"
```

### Windows Firewall

Docker Desktop manages Windows Firewall rules automatically for published ports.
If the portal is not reachable after starting:

```powershell
# Verify the port is listening
netstat -an | findstr ":80"

# Allow manually if needed (run as Administrator)
New-NetFirewallRule -DisplayName "IDMC Portal HTTP"  -Direction Inbound -Protocol TCP -LocalPort 80  -Action Allow
New-NetFirewallRule -DisplayName "IDMC Portal HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

---

## 8. Secret Generation

Run once per environment. **Never reuse secrets between environments.**

### Linux / macOS

```bash
# The generate-secrets.sh script writes a ready-to-use .env file
chmod +x generate-secrets.sh
./generate-secrets.sh > .env
# Then edit .env to set PORTAL_BASE_URL and LLM_API_KEY
```

### Windows (PowerShell — no OpenSSL required)

```powershell
# Uses built-in .NET cryptography (System.Security.Cryptography)
.\generate-secrets.ps1
# Or for a named environment:
.\generate-secrets.ps1 -OutFile .env.staging -Force
```

> **Key sizes:**
> - JWT: 4096-bit RSA (RS256)
> - All hex secrets: 256-bit entropy (openssl rand / .NET CSPRNG)
> - PostgreSQL password: 192-bit entropy

---

## 9. Building & Releasing — Linux

### Quick build (latest tag, no push)

```bash
./release.sh
```

### Versioned release

```bash
./release.sh --tag v1.3.0
```

### Build + test + push to GitHub Container Registry

```bash
./release.sh --tag v1.3.0 --push --registry ghcr.io/your-org
```

### Skip unit tests (CI pre-tested)

```bash
./release.sh --tag v1.3.0 --skip-tests
```

### What the script does

1. Verifies Docker and Compose are installed
2. Warns about missing secrets in `.env`
3. Runs pytest for `auth-service` and `backend-api`
4. Runs vitest for `portal-spa`
5. Builds all three Docker images in parallel (`--parallel`)
6. Tags images with the provided tag and `latest`
7. Optionally retags for a registry and pushes
8. Runs a smoke test: spins up the test compose stack, hits `/health` on both services, tears it down

---

## 10. Building & Releasing — Windows

Use `release.ps1` instead of `release.sh` on Windows.

### Quick build

```powershell
.\release.ps1
```

### Versioned release

```powershell
.\release.ps1 -Tag v1.3.0
```

### Build + test + push to registry

```powershell
.\release.ps1 -Tag v1.3.0 -Push -Registry ghcr.io/your-org
```

### Skip unit tests

```powershell
.\release.ps1 -Tag v1.3.0 -SkipTests
```

### Use environment-specific .env file

```powershell
.\release.ps1 -Env staging   # uses .env.staging
```

### Windows-specific compose command

When deploying on Windows, include the Windows override file to adjust volume paths:

```powershell
$env:TAG = 'v1.3.0'
docker compose `
    -f docker-compose.yml `
    -f docker-compose.windows.yml `
    --env-file .env `
    up -d
```

### Using host-path bind mounts on Windows

If you want the containers to write directly to a Windows host path (e.g. `C:\idmc\staging`):

1. Add `C:\idmc` to Docker Desktop file sharing:
   **Docker Desktop → Settings → Resources → File Sharing → + → C:\idmc → Apply & Restart**

2. Edit `docker-compose.windows.yml` volumes section:
   ```yaml
   backend-api:
     volumes:
       - //c/idmc/staging:/opt/idmc/staging
       - //c/idmc/scripts:/opt/idmc/scripts:ro
       - //c/idmc/logs/auth:/var/log/idmc/auth:ro
       - //c/idmc/logs/api:/var/log/idmc/api:ro
       - //c/idmc/logs/agent:/opt/informatica/logs:ro
       - llm-settings:/etc/idmc-portal
       - ./backend-api/config/paths.yaml:/etc/idmc-portal/paths.yaml:ro
       - ./backend-api/config/operations.yaml:/etc/idmc-portal/operations.yaml:ro
       - ./backend-api/config/log_paths.yaml:/etc/idmc-portal/log_paths.yaml:ro
   ```
   > Note: Use `//c/` (forward slashes, lowercase drive letter) not `C:\`.

### Get help

```powershell
Get-Help .\release.ps1 -Full
.\release.ps1 -?
```

---

## 11. Production Deployment

### Initial start

**Linux / macOS:**
```bash
TAG=v1.3.0 docker compose --env-file .env up -d
```

**Windows (PowerShell):**
```powershell
$env:TAG = 'v1.3.0'
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env up -d
```

### Update to a new version

**Linux / macOS:**
```bash
./release.sh --tag v1.4.0

# Rolling restart (zero downtime if behind a load balancer)
TAG=v1.4.0 docker compose --env-file .env up -d --no-deps auth-service
TAG=v1.4.0 docker compose --env-file .env up -d --no-deps backend-api
TAG=v1.4.0 docker compose --env-file .env up -d --no-deps portal
```

**Windows (PowerShell):**
```powershell
.\release.ps1 -Tag v1.4.0

$env:TAG = 'v1.4.0'
docker compose -f docker-compose.yml -f docker-compose.windows.yml `
    --env-file .env up -d --no-deps auth-service
docker compose -f docker-compose.yml -f docker-compose.windows.yml `
    --env-file .env up -d --no-deps backend-api
docker compose -f docker-compose.yml -f docker-compose.windows.yml `
    --env-file .env up -d --no-deps portal
```

### Stop the stack

**Linux / macOS:**
```bash
docker compose --env-file .env down
# Destroy all data:
docker compose --env-file .env down --volumes
```

**Windows (PowerShell):**
```powershell
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env down
# Destroy all data:
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env down --volumes
```

### View logs

```bash
# Same command on all platforms
docker compose logs -f                  # all services
docker compose logs -f auth-service     # one service
docker compose logs --since 1h portal  # last hour
```

---

## 12. TLS / HTTPS Configuration

### Using Let's Encrypt (Certbot + nginx)

```bash
# On the host (not inside a container)
sudo apt-get install certbot

# Obtain certificate (port 80 must be reachable)
sudo certbot certonly --standalone -d your-portal-host.com

# Certificates are at:
# /etc/letsencrypt/live/your-portal-host.com/fullchain.pem
# /etc/letsencrypt/live/your-portal-host.com/privkey.pem
```

Mount certificates into the portal container and update `nginx.conf`:

```yaml
# docker-compose.yml — portal service
volumes:
  - /etc/letsencrypt:/etc/letsencrypt:ro
ports:
  - "80:80"
  - "443:443"
```

Update `portal-spa/nginx.conf` to add the HTTPS server block:

```nginx
server {
    listen 80;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    ssl_certificate     /etc/letsencrypt/live/your-host/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-host/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:...;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    # ... rest of config as in nginx.conf
}
```

### Certificate auto-renewal

```bash
# Add to crontab
0 3 * * * certbot renew --quiet && docker compose exec portal nginx -s reload
```

---

## 13. Database Setup

### PostgreSQL (production)

The database schema is created automatically by Alembic on first start:

```
auth-service Dockerfile CMD:
  alembic upgrade head && uvicorn ...
```

No manual DDL required. To verify:

```bash
docker compose exec auth-service alembic current
# Should show: head (revision 0001)
```

### Backup

```bash
# Dump
docker compose exec postgres pg_dump \
    -U idmc_portal idmc_portal > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T postgres psql \
    -U idmc_portal idmc_portal < backup_20260603.sql
```

### SQLite (development only)

Set `DB_URL=sqlite+aiosqlite:///./dev.db` in `.env`.
The `dev.db` file is created in the auth-service working directory.

---

## 14. IDMC Directory Structure

The backend-api reads from and writes to directories under `IDMC_STAGING_ROOT`
(default: `/opt/idmc/staging`). This directory must exist on the host and be
mounted into the container.

```
/opt/idmc/
├── staging/
│   ├── pm_scripts/        # Vendor PM script uploads
│   ├── source_files/      # Source data file uploads
│   ├── target_files/      # Target data file uploads (vendor_premium only)
│   └── parameter_files/   # Parameter file uploads
└── scripts/               # Pre-approved trigger scripts (read-only in container)
    ├── daily_load.sh
    └── reload_params.sh
```

### Configuring allowed paths per vendor role

Edit `backend-api/config/paths.yaml`:

```yaml
vendor_standard:
  - pm_scripts
  - source_files
  - parameter_files

vendor_premium:
  - pm_scripts
  - source_files
  - target_files
  - parameter_files
```

### Configuring trigger scripts

Edit `backend-api/config/operations.yaml`:

```yaml
daily_load:
  script: /opt/idmc/scripts/daily_load.sh
  roles:
    - vendor_standard
    - vendor_premium

parameter_reload:
  script: /opt/idmc/scripts/reload_params.sh
  roles:
    - vendor_premium
```

Scripts run in a **clean environment** (only `PATH`, `HOME`, `LANG` passed through).
They must not require access to service secrets.

---

## 15. Log Analyser Directory Configuration

The Log Analyser uses a separate config file — **`backend-api/config/log_paths.yaml`** — that is completely independent of `paths.yaml` (vendor upload directories). Adding a directory here gives the admin the ability to browse and AI-analyse it; it has no effect on what vendors can upload.

### Default configuration

```yaml
roots:
  - name: staging
    label: "IDMC Staging"
    path: /opt/idmc/staging

  - name: agent_logs
    label: "IDMC Secure Agent Logs"
    path: /opt/informatica/logs

  - name: auth_logs
    label: "Auth Service Logs"
    path: /var/log/idmc/auth

  - name: api_logs
    label: "Backend API Logs"
    path: /var/log/idmc/api
```

Each root requires three fields:

| Field | Description |
|---|---|
| `name` | Unique identifier (alphanumeric). Used internally. |
| `label` | Display name shown in the FileTree and sent to the LLM as service context. |
| `path` | Absolute path **inside the container**. Must exist and be readable by the `idmc` user. |

### Adding a new log root

1. Add an entry to `backend-api/config/log_paths.yaml`.
2. Mount the host directory into the `backend-api` container in `docker-compose.yml`:

   ```yaml
   # docker-compose.yml — backend-api volumes
   - /host/path/to/logs:/container/path/to/logs:ro
   ```

3. Restart the backend-api container:

   **Linux / macOS:**
   ```bash
   docker compose up -d --no-deps backend-api
   ```

   **Windows (PowerShell):**
   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.windows.yml `
       --env-file .env up -d --no-deps backend-api
   ```

The new root appears immediately in the Log Analyser FileTree — no code change or image rebuild is required.

### Host directory permissions

The `idmc` user inside the container runs as UID 1000. Log directories should be readable by that UID:

**Linux:**
```bash
sudo chown -R 1000:1000 /var/log/idmc /opt/informatica/logs
sudo chmod -R 750 /var/log/idmc /opt/informatica/logs
```

**Windows:** Add the Docker Desktop service account (or the specific container user) to the ACL of each log directory with Read permission. The directories must be added to Docker Desktop → Settings → Resources → File Sharing before mounting.

### Security note

Paths listed in `log_paths.yaml` are accessible to **admin users only** — the vendor session cookie is never accepted by any log analyser endpoint. The backend enforces that all file paths resolve to within a listed root before reading; traversal attempts return HTTP 400.

---

## 16. LLM Integration Setup

The LLM provider is configured through the Admin Console after deployment.
Optionally seed initial settings via environment variables in `.env`:

```bash
LLM_PROVIDER=anthropic          # anthropic | openai | azure_openai | gemini
LLM_API_KEY=sk-ant-...
LLM_MODEL=claude-opus-4-8
LLM_MAX_CONTEXT_TOKENS=80000
```

### After first boot

```
Admin Console → LLM Settings → set provider + model + API key → Save → Test Connection
```

### Supported providers

| Provider | Env value | Example model | API key source |
|---|---|---|---|
| Anthropic Claude | `anthropic` | `claude-opus-4-8` | console.anthropic.com |
| OpenAI | `openai` | `gpt-4o` | platform.openai.com |
| Azure OpenAI | `azure_openai` | `gpt-4o` | Azure Portal |
| Google Gemini | `gemini` | `gemini-2.0-flash` | aistudio.google.com |

### LLM settings file

Settings are stored encrypted at `LLM_SETTINGS_PATH` (default: `/etc/idmc-portal/llm-settings.enc`).
The encryption key is derived from `ADMIN_SESSION_SECRET` via SHA-256 (Fernet AES-128-CBC + HMAC).

The file is stored in the `llm-settings` Docker volume and persists across container restarts.

---

## 17. First-Boot Admin Seeding

After the stack is running, create the first admin account:

```bash
docker compose exec auth-service python seed_admin.py \
    --username sysadmin \
    --password "$(openssl rand -base64 16)"
```

> Record the generated password securely. It cannot be recovered — only reset
> by running `seed_admin.py` again with a new password (it detects existing accounts).

Then log in at `https://your-host/admin/login`.

---

## 18. Health Checks & Monitoring

### Built-in health endpoints

| Endpoint | Expected response |
|---|---|
| `http://auth-service:8001/health` | `{"status": "ok"}` |
| `http://backend-api:8002/health` | `{"status": "ok"}` |
| `http://localhost/` (nginx) | HTTP 200 |

These are used by Docker's `healthcheck` directives and the release smoke test.

### Check stack health

```bash
docker compose ps         # shows health status
docker compose top        # process list per container
docker stats              # live CPU/memory usage
```

### Recommended monitoring

| Tool | What to monitor |
|---|---|
| Prometheus + Grafana | Container CPU, memory, request rate |
| Loki | Structured JSON logs from both services |
| Uptime Kuma / Pingdom | External HTTPS check on `/` every 60s |
| PostgreSQL exporter | DB connections, query latency, table size |

### Structured log format

Both Python services emit structured JSON to stdout:

```json
{"event": "file_upload", "vendor_id": 3, "filename": "load.py",
 "file_size_bytes": 4096, "timestamp": "2026-06-03T12:00:00"}
```

Collect with `docker compose logs` or a log driver (Loki, Fluentd, CloudWatch).

---

## 19. Backup & Recovery

### What to back up

| Data | Location | Frequency |
|---|---|---|
| PostgreSQL database | `postgres-data` volume | Daily |
| IDMC staging files | `idmc-staging` volume / host path | Per upload or daily |
| LLM settings file | `llm-settings` volume | After any change |
| `.env` secrets file | Host filesystem | After any rotation |

### Automated backup script — Linux

```bash
#!/usr/bin/env bash
BACKUP_DIR=/var/backups/idmc
DATE=$(date +%Y%m%d_%H%M)
mkdir -p "$BACKUP_DIR"

# Database
docker compose exec postgres pg_dump -U idmc_portal idmc_portal \
    | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"

# LLM settings
docker cp idmc-llm-settings:/etc/idmc-portal/llm-settings.enc \
    "$BACKUP_DIR/llm-settings_${DATE}.enc"

# Rotate: keep 7 days
find "$BACKUP_DIR" -mtime +7 -delete
```

Schedule with cron:
```bash
0 2 * * * /opt/idmc-portal/backup.sh >> /var/log/idmc-backup.log 2>&1
```

### Automated backup script — Windows (PowerShell)

```powershell
# backup.ps1
$BackupDir = "C:\Backups\idmc"
$Date      = Get-Date -Format "yyyyMMdd_HHmm"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

# Database
docker compose exec postgres pg_dump -U idmc_portal idmc_portal |
    Set-Content -Path "$BackupDir\db_$Date.sql" -Encoding UTF8

# Compress
Compress-Archive -Path "$BackupDir\db_$Date.sql" `
    -DestinationPath "$BackupDir\db_$Date.sql.zip" -Force
Remove-Item "$BackupDir\db_$Date.sql"

# LLM settings
docker cp "idmc-llm-settings:/etc/idmc-portal/llm-settings.enc" `
    "$BackupDir\llm-settings_$Date.enc"

# Rotate: keep last 7 days
Get-ChildItem $BackupDir | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
    Remove-Item -Force

Write-Host "Backup complete: $BackupDir"
```

Schedule with Windows Task Scheduler (run as Administrator):
```powershell
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NonInteractive -File C:\idmc-portal\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00AM"
Register-ScheduledTask -TaskName "IDMC Backup" -Action $action -Trigger $trigger `
    -RunLevel Highest -Force
```

---

## 20. Scaling

### Horizontal scaling (multiple API replicas)

```yaml
# docker-compose.yml
auth-service:
  deploy:
    replicas: 2

backend-api:
  deploy:
    replicas: 3
```

**Caveat:** The TOTP replay cache (`replay_cache.py`) is in-memory per instance.
With multiple replicas, the same code could theoretically be accepted twice across
different instances. Use Redis for the replay cache before horizontally scaling
the auth-service in production:

```python
# auth-service/app/replay_cache.py — replace in-memory dict with Redis
import redis.asyncio as redis
r = redis.from_url(os.environ["REDIS_URL"])
```

### The portal (nginx) scales to 1

nginx is stateless — a load balancer in front handles multiple instances.
The portal container itself is the load balancer; replicas of it are unnecessary
unless the host itself is behind a CDN or an external load balancer.

---

## 21. Troubleshooting

### `docker compose up --build` fails on `backend-api` — `AttributeError: module 'pkgutil' has no attribute 'ImpImporter'`

As of Oct 2026, `backend-api/requirements.txt` contains only `pip==21.2.4` and `setuptools==58.0.4` (a stale pip-freeze, not the real dependency list — see §5 note). Installing that old pip inside the `python:3.12-slim` base image breaks pip itself, because `pip==21.2.4` depends on `pkgutil.ImpImporter`, which Python 3.12 removed:

```
File ".../pip/_vendor/pkg_resources/__init__.py", line 2164, in <module>
    register_finder(pkgutil.ImpImporter, find_on_path)
AttributeError: module 'pkgutil' has no attribute 'ImpImporter'
```

The build fails before the real packages (`fastapi`, `anthropic`, etc.) ever install. **Workaround until `requirements.txt` is fixed:** either edit `backend-api/requirements.txt` to drop the `pip==`/`setuptools==` pins (let the base image's pip install normally), or skip Docker for local dev entirely and use the native setup (`dev-setup-mac.sh` / `dev-setup-windows.ps1`, see [NATIVE_SETUP.md](NATIVE_SETUP.md)) — it installs the correct package list directly rather than from `requirements.txt`.

### Service fails to start — "FATAL: required environment variable not set"

Check that all required variables are set in `.env`:

```bash
grep "^[A-Z].*=$" .env   # shows variables with empty values
```

### Database connection refused

```bash
docker compose ps postgres   # is it healthy?
docker compose logs postgres  # check for init errors
# Common cause: POSTGRES_PASSWORD not set
```

### `alembic upgrade head` fails on auth-service start

```bash
docker compose exec auth-service alembic history   # show migration state
docker compose exec auth-service alembic current   # show current revision
# If DB is ahead of code: pull the latest image
```

### LLM returns "API key not valid"

1. Go to Admin Console → LLM Settings
2. Re-enter the API key (the field shows `••••` — it must be re-typed to update)
3. Click **Test Connection** — the error message now shows the exact provider error
4. Common cause: the `__keep__` sentinel was saved as the key in an earlier version — fixed in v1.3

### Vendor cannot log in — "Login failed" after entering TOTP

```bash
# Check if the vendor has an enrolled device
docker compose exec auth-service python -c "
import asyncio; from app.database import AsyncSessionLocal
from app.models import Vendor, Device; from sqlalchemy import select
async def check():
    async with AsyncSessionLocal() as db:
        v = (await db.execute(select(Vendor).where(Vendor.username=='username'))).scalar()
        if v:
            d = (await db.execute(select(Device).where(Device.vendor_id==v.id, Device.revoked==False))).scalars().all()
            print(f'vendor id={v.id} active={v.active} devices={len(d)}')
asyncio.run(check())
"
```

If device count is 0: go to Admin Console → Vendors → Re-issue link → have vendor re-scan QR.

### nginx returns 502 Bad Gateway

```bash
docker compose ps         # check auth-service and backend-api are healthy
docker compose logs auth-service --tail 20
docker compose logs backend-api  --tail 20
```

Common causes: service crashed on startup (missing env var), or image not rebuilt after code change.

### LLM streaming hangs / no response in Log Analyser

```bash
# Check backend-api logs during a streaming request
docker compose logs -f backend-api
# Look for "[LLM ERROR]" lines
# Also check: curl -N http://localhost:8002/health  -- should return immediately
```

### Log Analyser FileTree is empty or shows no roots

```bash
# Confirm LOG_PATHS_CONFIG is set and the file exists inside the container
docker compose exec backend-api env | grep LOG_PATHS
docker compose exec backend-api cat /etc/idmc-portal/log_paths.yaml
```

Common causes:
- `LOG_PATHS_CONFIG` env var is missing — add it to `docker-compose.yml` and restart.
- `log_paths.yaml` was not mounted — check the `volumes:` block in `docker-compose.yml`.
- YAML syntax error in `log_paths.yaml` — validate with `python3 -c "import yaml; yaml.safe_load(open('backend-api/config/log_paths.yaml'))"`.

### Log Analyser returns "path is outside all configured log roots"

The path the admin is browsing is not covered by any root in `log_paths.yaml`. Either:
- The path is correct but the root entry is missing — add it to `log_paths.yaml` and remount.
- The host directory was not mounted into the container — add the volume bind in `docker-compose.yml`.

```bash
# Check what is actually mounted at a suspected log path
docker compose exec backend-api ls /var/log/idmc/auth
```

---

### Windows-specific issues

**Docker not starting — "Hardware assisted virtualization and data execution protection must be enabled"**
```powershell
# Enable in BIOS/UEFI: Intel VT-x or AMD-V
# Then enable Hyper-V or WSL 2 from Windows Features:
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
# Or use WSL 2 (preferred):
wsl --install
```

**"docker: error during connect" in PowerShell**
```powershell
# Docker Desktop is not running — start it from the Start Menu
# Or check the system tray for the Docker whale icon
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Start-Sleep 15
docker info
```

**Port 80 already in use on Windows**

IIS or another service is likely bound to port 80:
```powershell
# Find what is using port 80
netstat -ano | findstr ":80 "
# Stop IIS if it is the culprit
Stop-Service W3SVC
Set-Service W3SVC -StartupType Disabled
# Or change the portal to a different port in docker-compose.windows.yml:
#   ports: ["8080:80"]
```

**Volume changes not reflected — files not appearing**

On Windows, bind-mounted directories require the drive to be in Docker Desktop's
File Sharing list. After adding:
```powershell
# Restart Docker Desktop
Stop-Process -Name "Docker Desktop" -Force
Start-Sleep 5
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Start-Sleep 20
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env up -d
```

**Line ending issues — scripts fail inside containers**

Windows text editors may save files with CRLF (`\r\n`). Shell scripts inside Linux
containers require LF (`\n`). Fix:
```powershell
# Convert a specific file (requires Git for Windows)
git config core.autocrlf false
git add --renormalize .

# Or use VS Code: open the file, click "CRLF" in the status bar → select "LF" → save
```

**`release.ps1` is blocked by execution policy**
```powershell
# Allow scripts signed by a trusted publisher or from the local machine:
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# If the file was downloaded from the internet, unblock it:
Unblock-File -Path .\release.ps1
Unblock-File -Path .\generate-secrets.ps1
```

**WSL 2 consuming too much memory**

Docker Desktop uses WSL 2 by default. Limit its memory consumption:
```
# Create or edit: %USERPROFILE%\.wslconfig
[wsl2]
memory=4GB
processors=2
swap=2GB
```
Then restart WSL:
```powershell
wsl --shutdown
# Restart Docker Desktop
```

---

## 22. Security Checklist

Before going live, verify:

**All platforms:**
- [ ] **This repo has no `.gitignore` and, as of Oct 2026, has real secrets committed to git** (checked via `git ls-files`): `jwt_private.pem` / `jwt_public.pem` at repo root and under `auth-service/` (same RSA key pair), `local-data/jwt_private.pem` / `jwt_public.pem` (a second, distinct key pair, currently in active use by local dev), `.env.local` (plaintext `ADMIN_API_KEY`, `ADMIN_SESSION_SECRET`, `UPLOAD_TOKEN_SECRET`), and `local-data/llm-settings.enc` (Fernet-encrypted, not plaintext, but still shouldn't be versioned). No live third-party API key (Anthropic/OpenAI/Gemini) was found hardcoded anywhere in the tracked source — `.env`/`.env.template` are clean placeholder templates, `docker-compose*.yml` correctly use `${VAR}` interpolation, and the only `sk-ant-...` string in the repo is a truncated example in this doc. **Before any further commit or if this repo is ever made public:** add a `.gitignore` (`*.pem`, `.env`, `.env.local`, `local-data/`, `.venv/`, `node_modules/`), and rotate `JWT_SIGNING_KEY`/`JWT_PUBLIC_KEY`, `ADMIN_API_KEY`, `ADMIN_SESSION_SECRET`, and `UPLOAD_TOKEN_SECRET` since the current values are exposed in git history and can't be un-exposed by deleting the files going forward.
- [ ] All secrets in `.env` are generated with `openssl rand` or `generate-secrets.ps1` — no defaults left
- [ ] `.env` is not committed to source control (check `.gitignore`)
- [ ] `POSTGRES_PASSWORD` is at least 48 characters
- [ ] JWT key is 4096-bit RSA
- [ ] Firewall: only ports 80 and 443 open externally
- [ ] TLS is configured; HTTP redirects to HTTPS
- [ ] `HSTS` header is set in nginx (`Strict-Transport-Security`)
- [ ] Admin password changed from default `changeme!`
- [ ] LLM API key is stored only in the encrypted settings file — not in `.env` after first boot
- [ ] `log_paths.yaml` roots do not include sensitive system paths outside of IDMC log directories
- [ ] Log root host directories are mounted **read-only** (`:ro`) in `docker-compose.yml`
- [ ] PostgreSQL is only reachable on the internal Docker network (no `ports:` mapping)
- [ ] Auth-service and backend-api have no `ports:` mapping (internal only)
- [ ] Automated daily database backups are configured and tested
- [ ] Container image updates are scheduled (Dependabot or equivalent)

**Linux:**
- [ ] Docker volumes are on LUKS-encrypted disk or cloud provider encrypted storage
- [ ] Vendor IDMC staging directories have write permission for the `idmc` user only (`chmod 750`)
- [ ] Log files do not contain LLM API keys (`grep -r "sk-ant\|sk-" /var/log`)
- [ ] `release.sh` is executable but not world-writable (`chmod 750 release.sh`)

**Windows:**
- [ ] Docker Desktop is running in **Linux containers** mode (not Windows containers)
- [ ] Docker volumes are on a BitLocker-encrypted drive
- [ ] `C:\idmc` (staging path) ACL: `idmc-portal` service account has Modify; no other standard user has Write
- [ ] `.env` file ACL: only the deployment user and SYSTEM have access
- [ ] Windows Defender exclusions are scoped to `C:\idmc` only — not the entire system
- [ ] PowerShell execution policy is `RemoteSigned` (not `Unrestricted`)
- [ ] `release.ps1` and `generate-secrets.ps1` are unblocked from quarantine (`Unblock-File`)
- [ ] IIS is disabled if port 80/443 is used by the portal
- [ ] WSL 2 memory is capped in `.wslconfig` to prevent runaway consumption

---

*End of Deployment Guide — IDMC Vendor Portal v1.4 — June 2026*
*Platforms: Linux (Ubuntu 22.04+) · Windows Server 2019+ · Windows 11 with Docker Desktop*
