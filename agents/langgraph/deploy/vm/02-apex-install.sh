#!/usr/bin/env bash
# 02-apex-install.sh — Install the Acuvity Apex agent daemonset into the VM cluster.
#
# Prerequisites:
#   - 01-base-setup.sh completed
#   - An Apex token from the Acuvity console (project: Devyansh)
#   - acuctl binary on PATH (download from Acuvity console or docs)
#
# Usage:
#   APEX_TOKEN=<token> ./02-apex-install.sh
#
# Or run interactively (script will prompt for the token):
#   ./02-apex-install.sh

set -euo pipefail

log()  { echo "[$(date -u +%H:%M:%SZ)] $*"; }
step() { echo; echo "━━━ $* ━━━"; }
die()  { echo "ERROR: $*" >&2; exit 1; }

export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

readonly ACUVITY_API="https://api.acuvity.us"
readonly ACUVITY_NS="/orgs/automated.acuvity.qa/apps/Devyansh"
readonly APEX_NAMESPACE="acuvity"
readonly APEX_HELM_CHART="oci://docker.io/acuvity/apex-agent"

# ---------------------------------------------------------------------------
step "Pre-flight"
# ---------------------------------------------------------------------------
command -v kubectl &>/dev/null || die "kubectl not found. Run 01-base-setup.sh first."
command -v helm    &>/dev/null || die "helm not found. Run 01-base-setup.sh first."
kubectl get nodes &>/dev/null  || die "Cannot reach cluster. Is KUBECONFIG set?"

# ---------------------------------------------------------------------------
step "Apex token"
# ---------------------------------------------------------------------------
if [[ -z "${APEX_TOKEN:-}" ]]; then
  echo
  echo "  Paste your Apex token from the Acuvity console"
  echo "  (Project: Devyansh → Install Agent → copy the token)"
  echo
  read -rsp "  APEX_TOKEN: " APEX_TOKEN
  echo
fi
[[ -n "$APEX_TOKEN" ]] || die "APEX_TOKEN is empty."

# ---------------------------------------------------------------------------
step "acuvity namespace"
# ---------------------------------------------------------------------------
if kubectl get namespace "$APEX_NAMESPACE" &>/dev/null; then
  log "Namespace '$APEX_NAMESPACE' already exists."
else
  kubectl create namespace "$APEX_NAMESPACE"
  log "Namespace '$APEX_NAMESPACE' created."
fi

# ---------------------------------------------------------------------------
step "Install Apex via Helm"
# ---------------------------------------------------------------------------
# The exact chart flags depend on your Acuvity version.
# Adjust --version if the console specifies a pinned version.
helm upgrade apex "$APEX_HELM_CHART" \
  --install \
  --version 1.0.0 \
  --namespace "$APEX_NAMESPACE" \
  --set acuvity.apiEndpoint="$ACUVITY_API" \
  --set acuvity.token="$APEX_TOKEN" \
  --wait \
  --timeout 5m

log "Apex Helm release installed."

# ---------------------------------------------------------------------------
step "Verify Apex daemonset"
# ---------------------------------------------------------------------------
log "Waiting for Apex daemonset rollout..."
kubectl -n "$APEX_NAMESPACE" rollout status ds/apex-apex-agent --timeout=3m

echo
kubectl -n "$APEX_NAMESPACE" get ds,pods -o wide
echo

# ---------------------------------------------------------------------------
step "Apex log check (10 s snapshot)"
# ---------------------------------------------------------------------------
log "Sampling Apex logs — look for 'workloads', 'attached to cgroup', 'attached to netns'..."
echo
# Get the first apex pod
APEX_POD=$(kubectl -n "$APEX_NAMESPACE" get pods -l app.kubernetes.io/name=apex-agent \
  -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || \
  kubectl -n "$APEX_NAMESPACE" get pods --no-headers | head -1 | awk '{print $1}')

kubectl -n "$APEX_NAMESPACE" logs "$APEX_POD" --tail=50 2>/dev/null || \
  kubectl -n "$APEX_NAMESPACE" logs ds/apex-apex-agent --all-containers=true --tail=50

# ---------------------------------------------------------------------------
step "Validate acuctl login (optional)"
# ---------------------------------------------------------------------------
if command -v acuctl &>/dev/null; then
  acuctl login --check -A "$ACUVITY_API" -n "$ACUVITY_NS" \
    && log "acuctl login OK." \
    || log "WARNING: acuctl login check failed — you will need to fix this before importing the manifest."
else
  log "acuctl not found on PATH. Install it from the Acuvity console before running 03-deploy-demo.sh."
fi

# ---------------------------------------------------------------------------
echo
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Phase 2 complete — Apex agent deployed                     ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Next: run  03-deploy-demo.sh  to deploy the LangGraph app  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
