#!/usr/bin/env bash
# 03-deploy-demo.sh — Clone the repo, deploy the LangGraph demo, and import the Apex manifest.
#
# Prerequisites:
#   - 01-base-setup.sh completed
#   - 02-apex-install.sh completed (Apex daemonset running)
#   - acuctl on PATH and authenticated
#
# Usage:
#   GROQ_API_KEY=<key> BRAVE_API_KEY=<key> ./03-deploy-demo.sh
#
# Or run interactively (script will prompt for missing values):
#   ./03-deploy-demo.sh

set -euo pipefail

log()  { echo "[$(date -u +%H:%M:%SZ)] $*"; }
step() { echo; echo "━━━ $* ━━━"; }
die()  { echo "ERROR: $*" >&2; exit 1; }

export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

readonly REPO_URL="https://github.com/acuvity/demo-agents.git"
readonly REPO_BRANCH="devyansh-test-groq"
readonly REPO_DIR="$HOME/demo-agents"
readonly ACUVITY_API="https://api.acuvity.us"
readonly ACUVITY_NS="/orgs/automated.acuvity.qa/apps/Devyansh"
readonly MANIFEST_PATH="$REPO_DIR/agents/langgraph/deploy/config/manifest.yaml"
readonly DEPLOY_SCRIPT="$REPO_DIR/agents/langgraph/deploy/k8s/deploy.sh"

# ---------------------------------------------------------------------------
step "Pre-flight"
# ---------------------------------------------------------------------------
command -v kubectl &>/dev/null || die "kubectl not found."
command -v helm    &>/dev/null || die "helm not found."
kubectl get nodes &>/dev/null  || die "Cannot reach cluster."

# ---------------------------------------------------------------------------
step "API keys"
# ---------------------------------------------------------------------------
if [[ -z "${GROQ_API_KEY:-}" ]]; then
  read -rsp "  GROQ_API_KEY: " GROQ_API_KEY; echo
fi
if [[ -z "${BRAVE_API_KEY:-}" ]]; then
  read -rsp "  BRAVE_API_KEY: " BRAVE_API_KEY; echo
fi
[[ -n "$GROQ_API_KEY"  ]] || die "GROQ_API_KEY is empty."
[[ -n "$BRAVE_API_KEY" ]] || die "BRAVE_API_KEY is empty."
export GROQ_API_KEY BRAVE_API_KEY

# ---------------------------------------------------------------------------
step "Clone / update repo"
# ---------------------------------------------------------------------------
if [[ -d "$REPO_DIR/.git" ]]; then
  log "Repo already cloned at $REPO_DIR — pulling latest..."
  git -C "$REPO_DIR" pull --ff-only
else
  log "Cloning $REPO_URL (branch: $REPO_BRANCH) into $REPO_DIR..."
  git clone -b "$REPO_BRANCH" "$REPO_URL" "$REPO_DIR"
fi

# ---------------------------------------------------------------------------
step "Deploy LangGraph demo (namespace, MCP servers, Helm chart)"
# ---------------------------------------------------------------------------
chmod +x "$DEPLOY_SCRIPT"
"$DEPLOY_SCRIPT"

# ---------------------------------------------------------------------------
step "Wait for pods to be ready"
# ---------------------------------------------------------------------------
log "Waiting for langgraph-demo rollout..."
kubectl -n langgraph-demo rollout status deploy/langgraph-demo    --timeout=5m
kubectl -n langgraph-demo rollout status deploy/langgraph-demo-ui --timeout=5m
log "Waiting for MCP servers..."
kubectl -n langgraph-demo rollout status deploy/mcp-server-sequential-thinking --timeout=3m || true
kubectl -n langgraph-demo rollout status deploy/mcp-server-brave-search         --timeout=3m || true

echo
kubectl -n langgraph-demo get pods,svc -o wide
echo

# ---------------------------------------------------------------------------
step "Import Apex manifest"
# ---------------------------------------------------------------------------
if command -v acuctl &>/dev/null; then
  log "Checking acuctl login..."
  acuctl login --check -A "$ACUVITY_API" -n "$ACUVITY_NS" \
    || die "acuctl login failed. Authenticate first and re-run."

  log "Importing manifest: $MANIFEST_PATH"
  acuctl import -A "$ACUVITY_API" -n "$ACUVITY_NS" "$MANIFEST_PATH"
  log "Manifest imported."
else
  echo
  echo "  WARNING: acuctl not found — skipping manifest import."
  echo "  Install acuctl, then run manually:"
  echo
  echo "    acuctl import -A $ACUVITY_API -n $ACUVITY_NS \\"
  echo "      $MANIFEST_PATH"
  echo
fi

# ---------------------------------------------------------------------------
step "Smoke test — health endpoint"
# ---------------------------------------------------------------------------
log "Starting port-forward to langgraph-demo-svc on :8300 (5 s)..."
kubectl -n langgraph-demo port-forward svc/langgraph-demo-svc 8300:80 &
PF_PID=$!
sleep 5

if curl -sf http://127.0.0.1:8300/health; then
  echo
  log "Health check PASSED."
else
  log "Health check failed — check pod logs:"
  echo "  kubectl -n langgraph-demo logs deploy/langgraph-demo --tail=50"
fi

kill "$PF_PID" 2>/dev/null || true

# ---------------------------------------------------------------------------
echo
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  Phase 3 complete — LangGraph demo deployed                         ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║                                                                      ║"
echo "║  Backend port-forward:                                               ║"
echo "║    kubectl -n langgraph-demo port-forward svc/langgraph-demo-svc 8300:80"
echo "║    curl http://127.0.0.1:8300/health                                 ║"
echo "║    curl -X POST http://127.0.0.1:8300/send \\                        ║"
echo "║      -H 'Content-Type: application/json' \\                          ║"
echo "║      -d '{\"message\":\"hello\"}'                                      ║"
echo "║                                                                      ║"
echo "║  UI port-forward:                                                    ║"
echo "║    kubectl -n langgraph-demo port-forward svc/langgraph-demo-ui-svc 5174:80"
echo "║    open http://localhost:5174                                         ║"
echo "║                                                                      ║"
echo "║  Watch Apex logs:                                                    ║"
echo "║    kubectl -n acuvity logs -f ds/apex-apex-agent --all-containers    ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
