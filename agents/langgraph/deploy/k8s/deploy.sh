#!/usr/bin/env bash
# deploy.sh — Deploy the Langgraph demo and its MCP server dependencies to Kubernetes.
#
# Usage:
#   ANTHROPIC_API_KEY=<key> BRAVE_API_KEY=<key> ./deploy.sh
#
# Prerequisites: kubectl and helm must be available on PATH and pointing at the target cluster.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
readonly NAMESPACE="langgraph-demo"
readonly CHART_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/charts/langgraph-demo" && pwd)"

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
require_env ANTHROPIC_API_KEY
require_env BRAVE_API_KEY

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
# Langgraph Demo
# ---------------------------------------------------------------------------
step "Langgraph Demo"
helm upgrade langgraph-demo "$CHART_DIR" \
  --install \
  --namespace "$NAMESPACE" \
  --set secrets.anthropicApiKey="$ANTHROPIC_API_KEY" \
  --set secrets.braveApiKey="$BRAVE_API_KEY"
log "langgraph-demo installed."

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo
echo "╔══════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║  Deployment complete                                                                     ║"
echo "╠══════════════════════════════════════════════════════════════════════════════════════════╣"
echo "║                                                                                          ║"
echo "║  Namespace : $NAMESPACE"
echo "║  Agent     : langgraph-demo-svc.${NAMESPACE}.svc.cluster.local:80"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════╝"
