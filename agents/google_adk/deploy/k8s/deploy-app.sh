#!/bin/bash

set -e

NAMESPACE="google-adk-demo"
CHART_DIR="$(cd "$(dirname "$0")/charts/google-adk-demo" && pwd)"

[ "$ANTHROPIC_API_KEY" ] || { echo "ANTHROPIC_API_KEY is not set. Please export it before running this script."; exit 1; }
[ "$BRAVE_API_KEY" ] || { echo "BRAVE_API_KEY is not set. Please export it before running this script."; exit 1; }

echo "Create or ensure the namespace '$NAMESPACE' exists..."
kubectl create namespace "$NAMESPACE" 2>/dev/null || echo "Namespace '$NAMESPACE' already exists."

kubectl label namespace "$NAMESPACE" acuvity.ai/inject-custom-ca=enabled --overwrite


echo "----------------------------------------------------"
echo "Installing Sequential Thinking MCP Server..."
echo "----------------------------------------------------"
helm upgrade mcp-server-sequential-thinking oci://docker.io/acuvity/mcp-server-sequential-thinking \
  --install \
  --namespace "$NAMESPACE" \
  --version 1.0.0

echo "----------------------------------------------------"
echo "Installing Brave Search MCP Server..."
echo "----------------------------------------------------"
helm upgrade mcp-server-brave-search oci://docker.io/acuvity/mcp-server-brave-search \
  --install \
  --namespace "$NAMESPACE" \
  --version 1.0.0 \
  --set-string secrets.BRAVE_API_KEY.value="$BRAVE_API_KEY"

echo "Installing google-adk-demo..."
helm upgrade google-adk-demo "$CHART_DIR" \
  --install \
  --namespace "$NAMESPACE" \
  --set secrets.anthropicApiKey="$ANTHROPIC_API_KEY" \
  --set secrets.braveApiKey="$BRAVE_API_KEY"

echo ""
echo "google-adk-demo deployed successfully."
echo "  Agent: google-adk-demo-svc.${NAMESPACE}.svc.cluster.local:80"
