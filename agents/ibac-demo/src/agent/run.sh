#!/bin/bash
set -e
# APP TOKEN - To create your app token
# 1. Navigate to console.acuvity.ai
# 2. Under access, click on App Tokens
# 3. Create your token
export APP_TOKEN="${APP_TOKEN:?APP_TOKEN is not set}"

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

# MCP server selection: local (default) or arcade
MCP_SERVER="${MCP_SERVER:-local}"
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

export HTTPS_PROXY="https://ibac-demo~agent:${APP_TOKEN}@${APEX_URL#https://}"
export HTTP_PROXY="https://ibac-demo~agent:${APP_TOKEN}@${APEX_URL#https://}"



export SSL_CERT_FILE="./ca/combined-ca.pem"

cd "$SCRIPT_DIR"
uv run python3 main.py
