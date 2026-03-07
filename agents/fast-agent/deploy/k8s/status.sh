#!/bin/bash

echo "----------------------------------------------------"
echo "Checking MCP Demo..."
echo "----------------------------------------------------"
echo "----> pods"
kubectl -n mcp-demo get pods
echo "----> config_map"
kubectl -n mcp-demo get cm
echo "----> secrets"
kubectl -n mcp-demo get secrets
echo "----------------------------------------------------"