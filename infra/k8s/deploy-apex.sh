#!/bin/bash
#
# Deploy Apex Agent to Kubernetes
#
# Usage:
#   ./deploy-apex.sh [-t TOKEN]
#   
# Or with environment variable:
#   ACUVITY_APP_TOKEN=<token> ./deploy-apex.sh
#
# Options:
#   -t TOKEN      App token for authentication

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APEX_DIR="$SCRIPT_DIR/apex-agent"

# Use prod values file
cp "$APEX_DIR/apex-agent-values-template.yaml" "$APEX_DIR/apex-agent-values.yaml"

# Fixed values
IMAGE_TAG="stable"
HELM_TAG="1.0.0"

while getopts "t:" opt; do
  case $opt in
    t)
      TOKEN=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

# replace the image tag
sed -i.bak "s|tag: \".*\"|tag: \"$IMAGE_TAG\"|" "$APEX_DIR/apex-agent-values.yaml" && rm -f "$APEX_DIR/apex-agent-values.yaml.bak"

# Check for app token from command line or environment variable
if [ -n "$TOKEN" ]; then
  cp "$APEX_DIR/acuvity-apptoken-template.yaml" "$APEX_DIR/acuvity-apptoken.yaml"
  sed -i.bak "s|YOUR_APP_TOKEN_HERE|$TOKEN|" "$APEX_DIR/acuvity-apptoken.yaml" && rm -f "$APEX_DIR/acuvity-apptoken.yaml.bak"
elif [ -n "$APP_TOKEN" ]; then
  cp "$APEX_DIR/acuvity-apptoken-template.yaml" "$APEX_DIR/acuvity-apptoken.yaml"
  sed -i.bak "s|YOUR_APP_TOKEN_HERE|$APP_TOKEN|" "$APEX_DIR/acuvity-apptoken.yaml" && rm -f "$APEX_DIR/acuvity-apptoken.yaml.bak"
fi

[ -f "$APEX_DIR/acuvity-apptoken.yaml" ] || { echo "missing token file."; exit 1; }

echo "----------------------------------------------------"
echo "Removing cert-manager and acuvity namespaces..."
echo "----------------------------------------------------"

kubectl delete namespace cert-manager  || { echo "no cert-manager namespace found"; }
kubectl delete namespace acuvity       || { echo "no acuvity namespace found"; }

echo "----------------------------------------------------"
echo "Creating acuvity namespace..."
echo "----------------------------------------------------"
kubectl apply -f "$APEX_DIR/acuvity-namespace.yaml"

echo "----------------------------------------------------"
echo "Installing cert manager..."
echo "----------------------------------------------------"

helm repo add jetstack https://charts.jetstack.io --force-update
helm install cert-manager jetstack/cert-manager   --namespace cert-manager   --create-namespace   --version v1.15.1   --set crds.enabled=true

echo "----------------------------------------------------"
echo "Creating trust-manager for acuvity namespace..."
echo "----------------------------------------------------"
helm upgrade trust-manager jetstack/trust-manager   --install   --namespace cert-manager   --set app.trust.namespace=acuvity   --wait

kubectl apply -f "$APEX_DIR/cert-manager-resources.yaml"



echo "----------------------------------------------------"
echo "Creating app token secret..."
echo "----------------------------------------------------"
kubectl apply -f "$APEX_DIR/acuvity-apptoken.yaml"

echo "----------------------------------------------------"
echo "Install Apex..."
echo "----------------------------------------------------"
helm upgrade apex oci://docker.io/acuvity/apex-agent --version "$HELM_TAG" --install --create-namespace --namespace acuvity -f "$APEX_DIR/apex-agent-values.yaml"
