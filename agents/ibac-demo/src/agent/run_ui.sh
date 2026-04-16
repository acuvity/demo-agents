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

MCP_SERVER="${MCP_SERVER:-arcade}"
export MCP_SERVER

if [[ "$MCP_SERVER" == "arcade" ]]; then
  export ARCADE_API_KEY="${ARCADE_API_KEY:?ARCADE_API_KEY is not set (required when MCP_SERVER=arcade)}"
  export ARCADE_USER_ID="${ARCADE_USER_ID:?ARCADE_USER_ID is not set (required when MCP_SERVER=arcade)}"
  export ARCADE_MCP_URL="${ARCADE_MCP_URL:?ARCADE_MCP_URL is not set (required when MCP_SERVER=arcade)}"
fi

# Absolute path so SSL_CERT_FILE stays valid after we cd into the agent dir (relative paths would break).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CA_PATH="$SCRIPT_DIR/ca.pem"
if [ ! -f "$CA_PATH" ]; then
  curl -s -o "$CA_PATH" "${APEX_URL}/_acuvity/ca.pem"
fi

# Percent-encode token in proxy userinfo. Raw tokens with @ : / + etc. break the URL and cause proxy 401.
ACUVITY_TOKEN_PROXY_ESC="$(
python3 <<'PY'
import os, urllib.parse
print(urllib.parse.quote(os.environ["ACUVITY_TOKEN"].strip(), safe=""))
PY
)"
export HTTPS_PROXY="https://token:${ACUVITY_TOKEN_PROXY_ESC}@${APEX_URL#https://}"
export HTTP_PROXY="https://token:${ACUVITY_TOKEN_PROXY_ESC}@${APEX_URL#https://}"
export SSL_CERT_FILE="$CA_PATH"

cd "$SCRIPT_DIR"
echo "Starting UI backend on http://0.0.0.0:8300 (Acuvity proxy enabled)"
uv run python3 server.py
