#!/usr/bin/env bash
# Source this file to load .env.local into the current shell.
# Usage:  source ./load-env.sh   (or:  . ./load-env.sh)
_LOADER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
_ENV="$_LOADER_DIR/.env.local"
[[ -f "$_ENV" ]] || { echo "No .env.local — run dev-setup-mac.sh first." >&2; return 1; }
set -a
# shellcheck source=/dev/null
source "$_ENV"
set +a
# Expand JWT key file paths into actual PEM content for python-jose
if [[ -n "${JWT_SIGNING_KEY_FILE:-}" && -f "$JWT_SIGNING_KEY_FILE" ]]; then
    JWT_SIGNING_KEY=$(cat "$JWT_SIGNING_KEY_FILE")
    export JWT_SIGNING_KEY
fi
if [[ -n "${JWT_PUBLIC_KEY_FILE:-}" && -f "$JWT_PUBLIC_KEY_FILE" ]]; then
    JWT_PUBLIC_KEY=$(cat "$JWT_PUBLIC_KEY_FILE")
    export JWT_PUBLIC_KEY
fi
echo "Loaded $_ENV"
