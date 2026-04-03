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

# LLM provider selection: anthropic (default) or openrouter
LLM_PROVIDER="${LLM_PROVIDER:-anthropic}"
export LLM_PROVIDER

if [[ "$LLM_PROVIDER" == "openrouter" ]]; then
  export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:?OPENROUTER_API_KEY is not set (required when LLM_PROVIDER=openrouter)}"
elif [[ -n "$LLM_API_KEY" ]]; then
  # Custom Anthropic-compatible endpoint - LLM_API_KEY provided directly
  export LLM_API_KEY
else
  export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY is not set (required when LLM_PROVIDER=anthropic, or set LLM_API_KEY for a custom endpoint)}"
fi

# MCP server selection: arcade (default) or local
MCP_SERVER="${MCP_SERVER:-arcade}"
export MCP_SERVER

if [[ "$MCP_SERVER" == "arcade" ]]; then
  export ARCADE_API_KEY="${ARCADE_API_KEY:?ARCADE_API_KEY is not set (required when MCP_SERVER=arcade)}"
  export ARCADE_USER_ID="${ARCADE_USER_ID:?ARCADE_USER_ID is not set (required when MCP_SERVER=arcade)}"
  export ARCADE_MCP_URL="${ARCADE_MCP_URL:?ARCADE_MCP_URL is not set (required when MCP_SERVER=arcade)}"
fi

# Download Apex CA
# https://[APEX_URL]/_acuvity/ca.pem
CA_PATH="$(dirname "$0")/ca.pem"

if [ ! -f "$CA_PATH" ]; then
  curl -s -o "$CA_PATH" "${APEX_URL}/_acuvity/ca.pem"
fi

export HTTPS_PROXY="https://token:${ACUVITY_TOKEN}@${APEX_URL#https://}"
export HTTP_PROXY="https://token:${ACUVITY_TOKEN}@${APEX_URL#https://}"

export SSL_CERT_FILE="$CA_PATH"

uv run python3 main.py
