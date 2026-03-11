#!/bin/bash

set -e

# ---- Usage function ----
usage() {
  echo "Usage: $0 --name <ingress-name> --namespace <namespace> --host <hostname> --service <service-name> [--port <port>]"
  echo ""
  echo "Required parameters:"
  echo "  --name       Ingress resource name"  
  echo "  --namespace  Target namespace"
  echo "  --host       Hostname for ingress rule"
  echo "  --service    Backend service name"
  echo ""
  echo "Optional parameters:"
  echo "  --port       Service port (default: 80)"
  echo ""
  echo "Example:"
  echo "  $0 --name google-adk-demo --namespace google-adk-demo --host google-adk-demo.local --service google-adk-demo-ui-svc"
  exit 1
}

# ---- Default values ----
PORT="80"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INGRESS_NS="ingress-nginx"

# ---- Parse arguments ----
while [[ $# -gt 0 ]]; do
  case $1 in
    --name)
      INGRESS_NAME="$2"
      shift 2
      ;;
    --namespace)
      NAMESPACE="$2" 
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --service)
      SERVICE_NAME="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown parameter: $1"
      usage
      ;;
  esac
done

# ---- Validate required parameters ----
if [[ -z "$INGRESS_NAME" || -z "$NAMESPACE" || -z "$HOST" || -z "$SERVICE_NAME" ]]; then
  echo "ERROR: Missing required parameters"
  echo ""
  usage
fi

echo "Deploying ingress for $INGRESS_NAME..."
echo "  Namespace: $NAMESPACE"
echo "  Host: $HOST" 
echo "  Service: $SERVICE_NAME:$PORT"
echo ""

# ---- Pre-check: ensure target namespace exists ----
if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  echo "ERROR: Namespace '$NAMESPACE' does not exist."
  echo "Please deploy the application first."
  exit 1
fi

echo "Namespace '$NAMESPACE' exists. Proceeding with ingress setup..."

# ---- Check if ingress controller exists ----
if ! kubectl get deployment ingress-nginx-controller -n "$INGRESS_NS" >/dev/null 2>&1; then
  echo "ERROR: Ingress-nginx controller not found."
  echo "Please run 'deploy_ingress_controller.sh' first."
  exit 1
fi

# ---- Apply Ingress using template ----
echo "Applying ingress configuration..."
export INGRESS_NAME NAMESPACE HOST SERVICE_NAME PORT
envsubst < "$SCRIPT_DIR/ingress-template.yaml" | kubectl apply -f -

# ---- Print connection info ----
echo ""
echo "Ingress '$INGRESS_NAME' deployed successfully!"
echo ""
echo "Add this to your /etc/hosts file:"
EXT_ADDR=$(kubectl -n "$INGRESS_NS" get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$EXT_ADDR" ]; then
  EXT_ADDR=$(kubectl -n "$INGRESS_NS" get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
fi

echo "${EXT_ADDR:-<INGRESS_IP>} $HOST"
echo ""
echo "Then access your application at: http://$HOST"