 Ingress Deployment

This directory contains modular scripts for deploying ingress configurations for all demo agents.

## Structure

```
infra/
└── ingress/
    ├── deploy_ingress_controller.sh    # Shared ingress-nginx controller setup  
    ├── deploy_agent_ingress.sh         # Common ingress deployment script
    ├── ingress-template.yaml           # Reusable ingress YAML template
    └── README.md                       # This documentation

agents/
├── google_adk/
│   └── deploy/k8s/
│       └── deploy-ingress.sh       # Google ADK demo specific ingress (uses common template)
```

## Common Ingress Template

All agents can use the same ingress pattern through a shared template (`ingress-template.yaml`) and deployment script (`deploy_agent_ingress.sh`).

## Deployment

1. **First, deploy the ingress controller:**
```bash
./deploy_ingress_controller.sh
```

2. **Then deploy specific agent ingresses:**
```bash
# Google ADK Demo  
../../agents/google_adk/deploy/k8s/deploy-ingress.sh
```

## Creating New Agent Ingress

For new agents, create a simple wrapper script that calls the common template:

```bash
#!/bin/bash
set -e

# Configuration for your agent
AGENT_NAME="my-agent-demo"
NAMESPACE="my-agent-demo"  
HOST="my-agent-demo.local"
SERVICE_NAME="my-agent-demo-ui-svc"
PORT="80"

# Deploy using common template
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INGRESS_SCRIPT="$SCRIPT_DIR/../../../../infra/ingress/deploy_agent_ingress.sh"

exec "$INGRESS_SCRIPT" \
  --name "$AGENT_NAME" \
  --namespace "$NAMESPACE" \
  --host "$HOST" \
  --service "$SERVICE_NAME" \
  --port "$PORT"
```

## Host Configuration

After deployment, add these entries to your `/etc/hosts` file:

```
<INGRESS_IP> google-adk-demo.local
```

Replace `<INGRESS_IP>` with the external IP shown in the script output.


## Architecture
- **Google ADK**: Use UI-only ingress with internal agent communication
- **Service Types**: All UIs use ClusterIP services (ingress handles external access)
- **Ingress Controller**: Single nginx-ingress LoadBalancer for all traffic