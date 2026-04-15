# ibac-demo on Kubernetes

Helm chart: [charts/ibac-demo](./charts/ibac-demo). Follows the same layout as [fast-agent](../../../fast-agent/deploy/k8s): **UI Deployment**, **agent Deployment**, and **one MCP Tool Deployment** (`mcp-ibac-local-tools`) that runs all CRM tools from `tools/local_tools.py` over **SSE**.

## Prerequisites

- Kubernetes cluster and `kubectl` configured
- [Helm](https://helm.sh/) 3.x
- Container images built and pushed (or use `imagePullPolicy: Never` with a local cluster):
  - **Agent image**: build from [../../src/agent/Dockerfile](../../src/agent/Dockerfile) (also used for the MCP pod with a different command).
  - **UI image**: build from [../../src/ui/Dockerfile](../../src/ui/Dockerfile) (Vite dev server; same layout as langgraph/google_adk).

Example build (from repo root `agents/ibac-demo`):

```bash
docker build -t your-registry/ibac-demo-agent:latest -f src/agent/Dockerfile src/agent
docker build -t your-registry/ibac-demo-ui:latest -f src/ui/Dockerfile src/ui
```

## Acuvity CA bundle (recommended)

The agent and UI pods set `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` when `agent.acuvityCaBundle.enabled` is true (default). Create a ConfigMap in the target namespace whose key `ca-bundle.crt` contains the trust material Apex needs (same idea as fast-agent’s `acuvity-ca-bundle`).

Example:

```bash
kubectl -n ibac-demo create configmap acuvity-ca-bundle --from-file=ca-bundle.crt=./ca.pem
```

To skip the mount while testing (not recommended for production), set `agent.acuvityCaBundle.enabled=false` in values.

## Install

Use [deploy-ibac-demo.sh](./deploy-ibac-demo.sh) or Helm directly.

```bash
export ACUVITY_TOKEN=...
export ANTHROPIC_API_KEY=...
./deploy-ibac-demo.sh https://your-apex.example.com
```

Or:

```bash
helm upgrade --install ibac-demo ./charts/ibac-demo -n ibac-demo \
  --set secrets.acuvity_token="$ACUVITY_TOKEN" \
  --set secrets.anthropic_api_key="$ANTHROPIC_API_KEY" \
  --set agent.apexUrl="https://your-apex.example.com" \
  --set image.agent.repository=your-registry/ibac-demo-agent \
  --set image.ui.repository=your-registry/ibac-demo-ui
```

See [example-values.yaml](./example-values.yaml) for common overrides (`LLM_PROVIDER`, model overrides, disabling CA bundle).

## Access

After install, Helm prints port-forward hints. Typically:

```bash
kubectl -n ibac-demo port-forward svc/ibac-demo-ui 3000:80
```

Open http://localhost:3000/ . The UI pod runs Vite; it proxies `/api/*` to the `ibac-demo-agent` Service via `BACKEND_URL`.

## MCP layout

- **One** MCP server pod exposes **all** CRM tools (same process as local `MCP_SERVER=local` stdio mode).
- The agent uses `LOCAL_MCP_SSE_URL` pointing at `http://mcp-ibac-local-tools.<namespace>.svc.cluster.local:8000/sse` (set automatically by the chart).

## Acuvity manifest

Import [../config/manifest.yaml](../config/manifest.yaml) after you replace placeholders (`label`, `subject`, namespace, app name if needed). Deployment names in the manifest assume Helm release name **`ibac-demo`** in namespace **`ibac-demo`**.

**Note:** The sample Lua extractors for `POST /send` assume a **JSON** body (`{"message":"..."}`). The interactive UI often sends **multipart/form-data** with a PDF. Adjust extractors for your policy needs or add a JSON-only path if required.

## Local rehearsal without Kubernetes

See [../compose/README.md](../compose/README.md).
