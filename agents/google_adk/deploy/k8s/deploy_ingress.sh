#!/bin/bash

set -e

# ---- Configuration ----
AGENT_NAME="google-adk-demo"
NAMESPACE="google-adk-demo"
HOST="google-adk-demo.local"
SERVICE_NAME="google-adk-demo-ui-svc"
PORT="80"

# ---- Deploy using common ingress template ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INGRESS_SCRIPT="$SCRIPT_DIR/../../../../infra/ingress/deploy_agent_ingress.sh"

echo "Deploying Google ADK Demo ingress using common template..."

exec "$INGRESS_SCRIPT" \
  --name "$AGENT_NAME" \
  --namespace "$NAMESPACE" \
  --host "$HOST" \
  --service "$SERVICE_NAME" \
  --port "$PORT"
