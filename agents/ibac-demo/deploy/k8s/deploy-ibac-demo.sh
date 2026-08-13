#!/usr/bin/env bash
set -euo pipefail

# Deploy ibac-demo Helm chart into namespace ibac-demo.
# deploy.sh in this directory is a thin wrapper that execs this script (parity with other demos).
# Usage:
#   export OPENROUTER_API_KEY=...   # default LLM; or ANTHROPIC_API_KEY / OPENAI_API_KEY
#   export ACUVITY_TOKEN=...
#   ./deploy-ibac-demo.sh https://your-apex.example.com
#
# Optional: DOCKER_HUB_USER (Docker Hub username) adds --set for
#   image.agent.repository and image.ui.repository to pull from Hub.
#
# Optional: create ConfigMap acuvity-ca-bundle in the namespace (see README.md)
# before installing, or set agent.acuvityCaBundle.enabled=false in values.

APEX_URL="${1:?Usage: $0 https://your-apex-url}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHART_DIR="${SCRIPT_DIR}/charts/ibac-demo"

[[ -n "${ACUVITY_TOKEN:-}" ]] || { echo "ACUVITY_TOKEN is not set" >&2; exit 1; }
[[ -n "${ANTHROPIC_API_KEY:-}" ]] || [[ -n "${OPENAI_API_KEY:-}" ]] || [[ -n "${OPENROUTER_API_KEY:-}" ]] || {
  echo "Set at least one of ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY" >&2
  exit 1
}

echo "Ensuring namespace ibac-demo exists..."
kubectl create namespace ibac-demo 2>/dev/null || true

helm_image_args=()
if [[ -n "${DOCKER_HUB_USER:-}" ]]; then
  helm_image_args+=(
    --set "image.agent.repository=${DOCKER_HUB_USER}/ibac-demo-agent"
    --set "image.ui.repository=${DOCKER_HUB_USER}/ibac-demo-ui"
  )
fi

helm upgrade --install ibac-demo "${CHART_DIR}" \
  --namespace ibac-demo \
  --set "secrets.acuvity_token=${ACUVITY_TOKEN}" \
  --set "agent.apexUrl=${APEX_URL}" \
  --set "secrets.anthropic_api_key=${ANTHROPIC_API_KEY:-}" \
  --set "secrets.openai_api_key=${OPENAI_API_KEY:-}" \
  --set "secrets.openrouter_api_key=${OPENROUTER_API_KEY:-}" \
  --set "agent.llmProvider=${LLM_PROVIDER:-openrouter}" \
  "${helm_image_args[@]}"

echo "Done. See NOTES from: helm get notes ibac-demo -n ibac-demo"
