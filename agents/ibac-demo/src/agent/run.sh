#!/bin/bash
set -e
# APP TOKEN - To create your app token
# 1. Navigate to console.acuvity.ai
# 2. Under access, click on App Tokens
# 3. Create your token
export ACUVITY_TOKEN="${ACUVITY_TOKEN:?ACUVITY_TOKEN is not set}"

# APEX URL - To find your apex url
# 1. Go to - https://console.acuvity.ai/me
# 2. Copy the Apex URL under General
export APEX_URL="${APEX_URL:?APEX_URL is not set}"

if [[ "$APEX_URL" != https://* ]]; then
  echo "Error: APEX_URL must start with https://" >&2
  exit 1
fi

# LLM provider selection: openrouter (default), openai, or anthropic
LLM_PROVIDER="${LLM_PROVIDER:-openrouter}"
export LLM_PROVIDER

if [[ -n "$LLM_API_KEY" ]]; then
  # LLM_API_KEY overrides the provider-specific key for any provider
  export LLM_API_KEY
elif [[ "$LLM_PROVIDER" == "openrouter" ]]; then
  export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:?OPENROUTER_API_KEY is not set (required when LLM_PROVIDER=openrouter)}"
elif [[ "$LLM_PROVIDER" == "openai" ]]; then
  export OPENAI_API_KEY="${OPENAI_API_KEY:?OPENAI_API_KEY is not set (required when LLM_PROVIDER=openai)}"
else
  export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY is not set (required when LLM_PROVIDER=anthropic)}"
fi

# MCP server selection: arcade (default) or local
MCP_SERVER="${MCP_SERVER:-arcade}"
export MCP_SERVER

if [[ "$MCP_SERVER" == "arcade" ]]; then
  export ARCADE_API_KEY="${ARCADE_API_KEY:?ARCADE_API_KEY is not set (required when MCP_SERVER=arcade)}"
  export ARCADE_USER_ID="${ARCADE_USER_ID:?ARCADE_USER_ID is not set (required when MCP_SERVER=arcade)}"
  export ARCADE_MCP_URL="${ARCADE_MCP_URL:?ARCADE_MCP_URL is not set (required when MCP_SERVER=arcade)}"
fi

# Download Apex CA (absolute path so SSL_CERT_FILE stays valid after cd into agent dir).
# https://[APEX_URL]/_acuvity/ca.pem
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
# Skip proxy for in-cluster MCP (K8s) and local SSE (localhost).
export NO_PROXY="127.0.0.1,localhost,.svc.cluster.local"
export no_proxy="$NO_PROXY"

export SSL_CERT_FILE="$CA_PATH"

cd "$SCRIPT_DIR"
RESULTS_FILE="docs/results.md"
uv run python3 main.py 2>&1 | tee "$RESULTS_FILE"

echo ""
echo "Generating demo HTML..."
uv run python3 docs/generate_demo.py
open docs/demo.html
