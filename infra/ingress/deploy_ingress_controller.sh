#!/bin/bash

set -e

INGRESS_NS="ingress-nginx"

echo "Setting up ingress-nginx controller..."

# ---- Install ingress-nginx controller ----
if kubectl get deployment ingress-nginx-controller -n "$INGRESS_NS" >/dev/null 2>&1; then
  echo "Ingress-nginx controller already exists, skipping installation..."
else
  echo "Installing ingress-nginx controller..."
  
  # Add and update helm repository
  echo "Adding ingress-nginx helm repository..."
  helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
  helm repo update
  
  helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx --create-namespace \
    --set controller.ingressClassResource.name=nginx \
    --set controller.ingressClass=nginx \
    --set controller.service.type=LoadBalancer
fi

echo "Waiting for ingress-nginx controller to be ready..."
kubectl -n "$INGRESS_NS" rollout status deployment/ingress-nginx-controller --timeout=300s

# ---- Print external IP / hostname ----
echo "Fetching ingress external IP/hostname..."
EXT_ADDR=$(kubectl -n "$INGRESS_NS" get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$EXT_ADDR" ]; then
  EXT_ADDR=$(kubectl -n "$INGRESS_NS" get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
fi

echo ""
echo "Ingress controller setup complete!"
echo "External IP/hostname: ${EXT_ADDR:-<not-ready-yet>}"
echo ""
echo "You can now run individual agent ingress deployment scripts."