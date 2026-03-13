#!/bin/bash

# Update and install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt-get install -y gnupg curl apt-transport-https ca-certificates conntrack

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker ${USER}
sudo sysctl net.bridge.bridge-nf-call-iptables=1

# Install K3s
echo "Installing K3s..."
curl -sfL https://get.k3s.io | sh -
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/kubeconfig.yaml
sudo chown $(id -u):$(id -g) ~/.kube/kubeconfig.yaml
export KUBECONFIG=$HOME/.kube/kubeconfig.yaml
echo 'export KUBECONFIG=$HOME/.kube/kubeconfig.yaml' >> ~/.bashrc
kubectl get nodes


# Install Helm
echo "Installing Helm..."
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
helm version
