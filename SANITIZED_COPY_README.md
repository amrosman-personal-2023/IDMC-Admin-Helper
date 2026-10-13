# Sanitized copy — no real secrets

This directory is a copy of the parent project with every file that contained
real, generated secret material replaced by a placeholder. It was created on
2026-10-13 for safe sharing / publishing (e.g. before making the repo public,
or before using this folder as a template for a new environment).

Excluded entirely (regenerable, not source):
- `.git/` — git history itself still contains the real secrets; this copy
  does not fix that. If this folder is pushed as a *new* repo, that's fine —
  if it's merged back into the existing git history, the old commits still
  carry the real values.
- `auth-service/.venv/`, `backend-api/.venv/`, `portal-spa/node_modules/` —
  reinstall via `./dev-setup-mac.sh` / `dev-setup-windows.ps1`.
- `auth-service/dev.db` — seeded admin account + TOTP state; removed because
  it's per-install runtime data, not source. Recreate via `alembic upgrade
  head` + `seed_admin.py` (see NATIVE_SETUP.md §9).
- `.DS_Store` files.

Replaced with placeholders (real values existed in the source copy):
| File | What was replaced |
|---|---|
| `jwt_private.pem`, `jwt_public.pem` (root) | Real 4096-bit RSA key pair → placeholder PEM text |
| `auth-service/jwt_private.pem`, `jwt_public.pem` | Same key pair as root → placeholder |
| `local-data/jwt_private.pem`, `jwt_public.pem` | A second, distinct real key pair (the one actually in use for local dev) → placeholder |
| `local-data/llm-settings.enc` | Real Fernet-encrypted LLM settings blob → placeholder text |
| `.env.local` | Real `ADMIN_API_KEY`, `ADMIN_SESSION_SECRET`, `UPLOAD_TOKEN_SECRET` (hex secrets) and absolute filesystem paths (my local username/directory) → placeholders / `<ABSOLUTE_PATH_TO_PROJECT>` |
| `local-data/log_paths.local.yaml` | Absolute filesystem paths → `<ABSOLUTE_PATH_TO_PROJECT>` |

Left as-is (already clean templates, verified to contain no real secrets):
- `.env`, `.env.template` — ship as empty placeholder templates.
- `docker-compose*.yml` — use `${VAR}` interpolation only, no literal secrets.
- All Python/TypeScript source — no hardcoded API keys found (verified by
  pattern scan for `sk-ant-`, `AIza`, `AKIA`, `-----BEGIN ... PRIVATE KEY-----`,
  and generic `key=`/`secret=`/`password=` literals across every tracked file).

**To use this copy:** run `./dev-setup-mac.sh` (or the Windows equivalent) —
it detects there's no valid `.env.local` content and regenerates a fresh RSA
key pair and secrets scoped to wherever this copy lives.

**Still true even with this copy existing:** the *original* project directory
(and its git history, if committed) still has the real secrets. This copy
does not rotate or invalidate them — see DEPLOYMENT.md §22 Security Checklist
for the rotation checklist if that's needed.
