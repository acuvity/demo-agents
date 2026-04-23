#!/bin/bash
set -e
# Same Acuvity gateway setup as run.sh: validates env, fetches Apex CA, sets proxy + SSL_CERT_FILE.
# Use this to start the chat UI backend so LLM and MCP traffic goes through the gateway.

export ACUVITY_TOKEN="${ACUVITY_TOKEN:?ACUVITY_TOKEN is not set}"
export APEX_URL="${APEX_URL:?APEX_URL is not set}"

if [[ "$APEX_URL" != https://* ]]; then
  echo "Error: APEX_URL must start with https://" >&2
  exit 1
fi

LLM_PROVIDER="${LLM_PROVIDER:-openrouter}"
export LLM_PROVIDER

if [[ -n "$LLM_API_KEY" ]]; then
  export LLM_API_KEY
elif [[ "$LLM_PROVIDER" == "openrouter" ]]; then
  export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:?OPENROUTER_API_KEY is not set (required when LLM_PROVIDER=openrouter)}"
elif [[ "$LLM_PROVIDER" == "openai" ]]; then
  export OPENAI_API_KEY="${OPENAI_API_KEY:?OPENAI_API_KEY is not set (required when LLM_PROVIDER=openai)}"
else
  export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY is not set (required when LLM_PROVIDER=anthropic)}"
fi

MCP_SERVER="${MCP_SERVER:-local}"
export MCP_SERVER

if [[ "$MCP_SERVER" == "arcade" ]]; then
  export ARCADE_API_KEY="${ARCADE_API_KEY:?ARCADE_API_KEY is not set (required when MCP_SERVER=arcade)}"
  export ARCADE_USER_ID="${ARCADE_USER_ID:?ARCADE_USER_ID is not set (required when MCP_SERVER=arcade)}"
  export ARCADE_MCP_URL="${ARCADE_MCP_URL:?ARCADE_MCP_URL is not set (required when MCP_SERVER=arcade)}"
fi

# Absolute path so any relative file references stay valid after we cd into the agent dir.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Build proxy URL from ACUVITY_TOKEN + APEX_URL if not already set (e.g. via docker-compose .env).
if [ -z "${HTTP_PROXY:-}" ]; then
  export HTTPS_PROXY="https://token:${ACUVITY_TOKEN}@${APEX_URL#https://}"
  export HTTP_PROXY="$HTTPS_PROXY"
fi
# Merge with any existing NO_PROXY (e.g. container-internal hostnames set by docker-compose)
_BASE_NO_PROXY="127.0.0.1,localhost,.svc.cluster.local"
_EXISTING_NO_PROXY="${NO_PROXY:-${no_proxy:-}}"
if [[ -n "$_EXISTING_NO_PROXY" ]]; then
  export NO_PROXY="${_EXISTING_NO_PROXY},${_BASE_NO_PROXY}"
else
  export NO_PROXY="$_BASE_NO_PROXY"
fi
export no_proxy="$NO_PROXY"

# If SSL_CERT_FILE is already set (e.g. mounted in Docker Compose / K8s), use it as-is.
# Otherwise fetch the Apex CA cert locally for direct runs.
if [ -z "${SSL_CERT_FILE:-}" ]; then
  CA_PATH="$SCRIPT_DIR/ca.pem"
  if [ ! -f "$CA_PATH" ]; then
    curl -s -o "$CA_PATH" "${APEX_URL}/_acuvity/ca.pem"
  fi
  export SSL_CERT_FILE="$CA_PATH"
  export REQUESTS_CA_BUNDLE="$CA_PATH"
fi

cd "$SCRIPT_DIR"
echo "Starting UI backend on http://0.0.0.0:8300 (Acuvity proxy enabled)"
exec uv run python3 server.py
