#!/usr/bin/env bash
# deploy.sh — Deploy the A2A multi-agent travel planner to Kubernetes.
#
# Usage:
#   ANTHROPIC_API_KEY=<key> \
#     A2A_TRAVEL_PLANNER_TOKEN=<token> A2A_FLIGHTS_AGENT_TOKEN=<token> \
#     A2A_HOTELS_AGENT_TOKEN=<token> A2A_PRICING_AGENT_TOKEN=<token> \
#     CA_BUNDLE_PATH=<path/to/ca.pem> ./deploy.sh
#
# Prerequisites: kubectl and helm must be available on PATH and pointing at the target cluster.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
readonly NAMESPACE="a2a-multi-agent"
readonly CHART_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/charts/a2a-multi-agent" && pwd)"

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
require_env A2A_TRAVEL_PLANNER_TOKEN
require_env A2A_FLIGHTS_AGENT_TOKEN
require_env A2A_HOTELS_AGENT_TOKEN
require_env A2A_PRICING_AGENT_TOKEN
require_env CA_BUNDLE_PATH

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
# CA Bundle
# ---------------------------------------------------------------------------
step "CA Bundle"
kubectl create configmap apex-ca-bundle \
  --namespace "$NAMESPACE" \
  --from-file=ca-bundle.crt="$CA_BUNDLE_PATH" \
  --dry-run=client -o yaml | kubectl apply -f -
log "apex-ca-bundle configmap applied."

# ---------------------------------------------------------------------------
# A2A Multi-Agent
# ---------------------------------------------------------------------------
step "A2A Multi-Agent"
helm upgrade a2a-multi-agent "$CHART_DIR" \
  --install \
  --namespace "$NAMESPACE" \
  --set secrets.anthropicApiKey="$ANTHROPIC_API_KEY" \
  --set secrets.travelPlannerToken="$A2A_TRAVEL_PLANNER_TOKEN" \
  --set secrets.flightsAgentToken="$A2A_FLIGHTS_AGENT_TOKEN" \
  --set secrets.hotelsAgentToken="$A2A_HOTELS_AGENT_TOKEN" \
  --set secrets.pricingAgentToken="$A2A_PRICING_AGENT_TOKEN"
log "a2a-multi-agent installed."

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo
echo "╔══════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║  Deployment complete                                                                   ║"
echo "╠══════════════════════════════════════════════════════════════════════════════════════════╣"
echo "║                                                                                        ║"
echo "║  Namespace       : $NAMESPACE"
echo "║  Travel Planner  : a2a-travel-planner-svc.${NAMESPACE}.svc.cluster.local:80"
echo "║  Flights Agent   : a2a-flights-agent-svc.${NAMESPACE}.svc.cluster.local:80"
echo "║  Hotels Agent    : a2a-hotels-agent-svc.${NAMESPACE}.svc.cluster.local:80"
echo "║  Pricing Agent   : a2a-pricing-agent-svc.${NAMESPACE}.svc.cluster.local:80"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════╝"
