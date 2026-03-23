#!/usr/bin/env bash
# 01-base-setup.sh — Run this ONCE inside the Ubuntu ARM64 VM after first boot.
#
# What it does:
#   1. Installs base OS packages
#   2. Installs k3s (single-node cluster)
#   3. Configures kubeconfig for the current user
#   4. Installs Helm
#   5. Installs cert-manager (required for Apex CA injection)
#
# Usage (inside the VM):
#   chmod +x 01-base-setup.sh && ./01-base-setup.sh

set -euo pipefail

log()  { echo "[$(date -u +%H:%M:%SZ)] $*"; }
step() { echo; echo "━━━ $* ━━━"; }
die()  { echo "ERROR: $*" >&2; exit 1; }

# Must NOT run as root — we configure kubeconfig for $USER
[[ $EUID -ne 0 ]] || die "Do not run as root. Run as your normal sudo user."

# ---------------------------------------------------------------------------
step "1 — Base packages"
# ---------------------------------------------------------------------------
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  curl git vim ca-certificates jq unzip socat conntrack iptables openssh-server
log "Base packages installed."

# ---------------------------------------------------------------------------
step "2 — Install k3s"
# ---------------------------------------------------------------------------
if command -v k3s &>/dev/null; then
  log "k3s already installed — skipping."
else
  curl -sfL https://get.k3s.io | sh -
  log "k3s installed."
fi

# Wait until the node is Ready
log "Waiting for k3s node to become Ready..."
until sudo k3s kubectl get nodes 2>/dev/null | grep -q " Ready"; do
  sleep 3
done
log "k3s node is Ready."

# ---------------------------------------------------------------------------
step "3 — Configure kubeconfig for $USER"
# ---------------------------------------------------------------------------
mkdir -p "$HOME/.kube"
sudo cp /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
sudo chown "$USER:$USER" "$HOME/.kube/config"
chmod 600 "$HOME/.kube/config"

# Persist across sessions
BASHRC="$HOME/.bashrc"
if ! grep -q "KUBECONFIG" "$BASHRC"; then
  echo 'export KUBECONFIG=$HOME/.kube/config' >> "$BASHRC"
fi
export KUBECONFIG="$HOME/.kube/config"

kubectl get nodes -o wide
log "kubeconfig configured."

# ---------------------------------------------------------------------------
step "4 — Install Helm"
# ---------------------------------------------------------------------------
if command -v helm &>/dev/null; then
  log "Helm already installed — skipping."
else
  curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
  log "Helm installed: $(helm version --short)"
fi

# ---------------------------------------------------------------------------
step "5 — Install cert-manager"
# ---------------------------------------------------------------------------
# Required for Apex's acuvity.ai/inject-custom-ca webhook to issue TLS certs
# into labeled namespaces.

CERT_MANAGER_VERSION="v1.16.3"

if kubectl get namespace cert-manager &>/dev/null; then
  log "cert-manager namespace already exists — skipping install."
else
  log "Installing cert-manager $CERT_MANAGER_VERSION..."
  kubectl apply -f \
    "https://github.com/cert-manager/cert-manager/releases/download/${CERT_MANAGER_VERSION}/cert-manager.yaml"
fi

log "Waiting for cert-manager deployments..."
kubectl -n cert-manager rollout status deploy/cert-manager          --timeout=3m
kubectl -n cert-manager rollout status deploy/cert-manager-cainjector --timeout=3m
kubectl -n cert-manager rollout status deploy/cert-manager-webhook  --timeout=3m
log "cert-manager is ready."

# ---------------------------------------------------------------------------
echo
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Phase 1 complete — base VM ready                           ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Next: run  02-apex-install.sh  to deploy the Apex agent    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
