#!/usr/bin/env bash
# deploy.sh — Deploy the Google ADK demo and its MCP server dependencies to Kubernetes.
#
# Usage:
#   Gateway mode  (LiteLLM calls Acuvity gateway, no transport proxy for LiteLLM):
#     BRAVE_API_KEY=<key> LITELLM_MASTER_KEY=<key> \
#       GATEWAY_URL=<url> GOOGLE_ADK_LITELLM_TOKEN=<token> \
#       [GOOGLE_ADK_AGENT_TOKEN=<token> PROXY_HOST=<host> CA_BUNDLE_PATH=<path>] \
#       [ARCADE_API_KEY=<key>] ./deploy.sh
#
#   Proxy mode  (LiteLLM calls Anthropic via transport proxy):
#     ANTHROPIC_API_KEY=<key> BRAVE_API_KEY=<key> LITELLM_MASTER_KEY=<key> \
#       PROXY_HOST=<host> CA_BUNDLE_PATH=<path/to/ca.pem> \
#       [GOOGLE_ADK_AGENT_TOKEN=<token>] [ARCADE_API_KEY=<key>] ./deploy.sh
#
# Prerequisites: kubectl and helm must be available on PATH and pointing at the target cluster.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
readonly NAMESPACE="google-adk-demo"
readonly CHART_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/charts/google-adk-demo" && pwd)"

readonly MCP_SEQUENTIAL_THINKING_CHART="oci://docker.io/acuvity/mcp-server-sequential-thinking"
readonly MCP_SEQUENTIAL_THINKING_VERSION="1.0.0"

readonly MCP_BRAVE_SEARCH_CHART="oci://docker.io/acuvity/mcp-server-brave-search"
readonly MCP_BRAVE_SEARCH_VERSION="1.0.0"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { echo "[$(date -u +%H:%M:%SZ)] $*"; }
step() { echo; echo "━━━ $* ━━━"; }
die()  { echo "ERROR: $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "'$1' is not installed or not on PATH."
}

require_env() {
  [[ -n "${!1:-}" ]] || die "Required environment variable '$1' is not set."
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
require_cmd kubectl
require_cmd helm
require_env BRAVE_API_KEY
require_env LITELLM_MASTER_KEY
require_env GOOGLE_ADK_LITELLM_TOKEN

# LiteLLM proxy mode (no gateway URL) requires an Anthropic key
if [[ -z "${GATEWAY_URL:-}" ]]; then
  require_env ANTHROPIC_API_KEY
fi

# Proxy mode is active when LiteLLM uses the transport proxy (no GATEWAY_URL)
# or when the agent component token is provided (authenticated proxy for the agent)
PROXY_MODE=false
[[ -z "${GATEWAY_URL:-}" ]] && PROXY_MODE=true
[[ -n "${GOOGLE_ADK_AGENT_TOKEN:-}" ]] && PROXY_MODE=true

if [[ "$PROXY_MODE" == "true" ]]; then
  require_env PROXY_HOST
  require_env CA_BUNDLE_PATH
fi

# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------
step "Namespace"
if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  log "Namespace '$NAMESPACE' already exists."
else
  log "Creating namespace '$NAMESPACE'..."
  kubectl create namespace "$NAMESPACE"
fi

log "Ensuring namespace label 'acuvity.ai/inject-custom-ca=enabled'..."
kubectl label namespace "$NAMESPACE" acuvity.ai/inject-custom-ca=enabled --overwrite

# ---------------------------------------------------------------------------
# MCP: Sequential Thinking
# ---------------------------------------------------------------------------
step "MCP Server — Sequential Thinking"
helm upgrade mcp-server-sequential-thinking "$MCP_SEQUENTIAL_THINKING_CHART" \
  --install \
  --namespace "$NAMESPACE" \
  --version "$MCP_SEQUENTIAL_THINKING_VERSION"
log "mcp-server-sequential-thinking installed."

# ---------------------------------------------------------------------------
# MCP: Brave Search
# ---------------------------------------------------------------------------
step "MCP Server — Brave Search"
helm upgrade mcp-server-brave-search "$MCP_BRAVE_SEARCH_CHART" \
  --install \
  --namespace "$NAMESPACE" \
  --version "$MCP_BRAVE_SEARCH_VERSION" \
  --set-string secrets.BRAVE_API_KEY.value="$BRAVE_API_KEY"
log "mcp-server-brave-search installed."

# ---------------------------------------------------------------------------
# CA Bundle  (only needed in proxy mode)
# ---------------------------------------------------------------------------
if [[ "$PROXY_MODE" == "true" ]]; then
  step "CA Bundle"
  kubectl create configmap apex-ca-bundle \
    --namespace "$NAMESPACE" \
    --from-file=ca-bundle.crt="$CA_BUNDLE_PATH" \
    --dry-run=client -o yaml | kubectl apply --server-side -f -
  log "apex-ca-bundle configmap applied."
fi

# ---------------------------------------------------------------------------
# Google ADK Demo
# ---------------------------------------------------------------------------
step "Google ADK Demo"
HELM_ARGS=(
  --install
  --namespace "$NAMESPACE"
  --set secrets.anthropicApiKey="${ANTHROPIC_API_KEY:-}"
  --set secrets.braveApiKey="$BRAVE_API_KEY"
  --set secrets.arcadeApiKey="${ARCADE_API_KEY:-}"
  --set secrets.agentToken="${GOOGLE_ADK_AGENT_TOKEN:-}"
  --set secrets.litellmToken="${GOOGLE_ADK_LITELLM_TOKEN:-}"
  --set secrets.litellmMasterKey="$LITELLM_MASTER_KEY"
)
[[ -n "${PROXY_HOST:-}" ]]  && HELM_ARGS+=(--set proxy.host="$PROXY_HOST")
[[ -n "${GATEWAY_URL:-}" ]] && HELM_ARGS+=(--set litellm.gateway_url="$GATEWAY_URL")

helm upgrade google-adk-demo "$CHART_DIR" "${HELM_ARGS[@]}"
log "google-adk-demo installed."

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo
echo "╔══════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║  Deployment complete                                                                     ║"
echo "╠══════════════════════════════════════════════════════════════════════════════════════════╣"
echo "║                                                                                          ║"
echo "║  Namespace : $NAMESPACE"
echo "║  Agent     : google-adk-demo-svc.${NAMESPACE}.svc.cluster.local:80"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════╝"
