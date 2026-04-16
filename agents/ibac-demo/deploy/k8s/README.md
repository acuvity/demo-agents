# ibac-demo on Kubernetes

Helm chart: [charts/ibac-demo](./charts/ibac-demo). Follows the same layout as [fast-agent](../../../fast-agent/deploy/k8s): **UI Deployment**, **agent Deployment**, and **one MCP Tool Deployment** (`mcp-ibac-local-tools`) that runs all CRM tools from `tools/mcp_tools.py` over **SSE**. The overall flow matches [langgraph](../../../langgraph/README.md) and [google_adk](../../../google_adk/README.md) (Helm chart, port-forward to the UI Service, then import the Acuvity manifest), with ibac-demo-specific steps for Acuvity secrets, Apex URL, and two images (agent and UI).

## Local Kubernetes: Rancher Desktop and K3s

[Rancher Desktop](https://rancherdesktop.io/) gives you a **single-node Kubernetes cluster on your laptop**. It is a practical stand-in for **K3s**-style development: you do **not** install K3s separately for local work; enable **Kubernetes** in Rancher Desktop preferences and wait until the cluster is running.

1. Install Rancher Desktop and turn **Kubernetes** on (Settings / Preferences).
2. Use the default `kubectl` context (often named **`rancher-desktop`**). Verify with `kubectl get nodes`.
3. Build and **push** images to a registry the cluster can reach (see below). Rancher Desktop’s cluster usually **cannot** use arbitrary local-only image names unless you use image import features or a registry; **Docker Hub under your personal account** is the path most teams use for this demo.

**Remote K3s:** If your colleague provisions a **remote** K3s cluster (for example behind **Rancher Manager**), use the **kubeconfig** they give you instead of Rancher Desktop. The Helm commands below are the same; only the cluster endpoint and optional **Ingress** change.

## Docker Hub (personal account)

You need a [Docker Hub](https://hub.docker.com/) login (`docker login`). Use your **Docker Hub username** (Docker ID), not your email, in image names.

1. From repo root **`agents/ibac-demo`**, replace `YOUR_DOCKER_ID` with your Hub username:

```bash
docker build -t YOUR_DOCKER_ID/ibac-demo-agent:latest -f src/agent/Dockerfile src/agent
docker build -t YOUR_DOCKER_ID/ibac-demo-ui:latest -f src/ui/Dockerfile src/ui
docker push YOUR_DOCKER_ID/ibac-demo-agent:latest
docker push YOUR_DOCKER_ID/ibac-demo-ui:latest
```

2. When you install the chart, set **`image.agent.repository`** and **`image.ui.repository`** to `YOUR_DOCKER_ID/ibac-demo-agent` and `YOUR_DOCKER_ID/ibac-demo-ui` (see **Install**). The MCP pod reuses the **agent** image and tag.

3. If the Hub repos are **private**, create a `docker-registry` secret in namespace `ibac-demo` and set [`imagePullSecrets`](./charts/ibac-demo/values.yaml) in your values to that secret’s name.

You do **not** put your Docker ID into application source code; only into **`docker build` / `docker push` tags** and **Helm values** (or `helm --set`).

## Prerequisites

- Kubernetes cluster and `kubectl` configured (for example **Rancher Desktop** with Kubernetes enabled, or any other cluster)
- [Helm](https://helm.sh/) 3.x
- Container images built and **pushed** to a registry the cluster can pull (see **Docker Hub** above), unless you use advanced local-only image loading
  - **Agent image**: build from [../../src/agent/Dockerfile](../../src/agent/Dockerfile) (also used for the MCP pod with a different command).
  - **UI image**: build from [../../src/ui/Dockerfile](../../src/ui/Dockerfile) (Vite dev server; same layout as langgraph/google_adk).

Example build and push (same as **Docker Hub** section; `YOUR_DOCKER_ID` is your Hub username):

```bash
docker build -t YOUR_DOCKER_ID/ibac-demo-agent:latest -f src/agent/Dockerfile src/agent
docker build -t YOUR_DOCKER_ID/ibac-demo-ui:latest -f src/ui/Dockerfile src/ui
docker push YOUR_DOCKER_ID/ibac-demo-agent:latest
docker push YOUR_DOCKER_ID/ibac-demo-ui:latest
```

## Acuvity CA bundle (recommended)

The agent and UI pods set `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` when `agent.acuvityCaBundle.enabled` is true (default). Create a ConfigMap in the target namespace whose key `ca-bundle.crt` contains the trust material Apex needs (same idea as fast-agent’s `acuvity-ca-bundle`).

Example:

```bash
kubectl -n ibac-demo create configmap acuvity-ca-bundle --from-file=ca-bundle.crt=./ca.pem
```

To skip the mount while testing (not recommended for production), set `agent.acuvityCaBundle.enabled=false` in values.

## Install

The chart defaults to short image names (`ibac-demo-agent`, `ibac-demo-ui`) and **`agent.llmProvider: openrouter`** in [values.yaml](./charts/ibac-demo/values.yaml). For **Docker Hub** (or any remote registry), you **must** set **`image.agent.repository`** and **`image.ui.repository`** to match what you built and pushed.

**OpenRouter (default chart LLM):**

```bash
kubectl create namespace ibac-demo 2>/dev/null || true
helm upgrade --install ibac-demo ./charts/ibac-demo -n ibac-demo \
  --set secrets.acuvity_token="$ACUVITY_TOKEN" \
  --set secrets.anthropic_api_key="" \
  --set secrets.openai_api_key="" \
  --set secrets.openrouter_api_key="$OPENROUTER_API_KEY" \
  --set agent.apexUrl="$APEX_URL" \
  --set agent.llmProvider=openrouter \
  --set image.agent.repository=YOUR_DOCKER_ID/ibac-demo-agent \
  --set image.ui.repository=YOUR_DOCKER_ID/ibac-demo-ui
```

**Anthropic instead:** set `agent.llmProvider=anthropic`, pass `secrets.anthropic_api_key`, and leave other LLM secrets empty if you prefer.

**Helper script:** [deploy-ibac-demo.sh](./deploy-ibac-demo.sh) wires Acuvity and LLM secrets (default provider **openrouter**; override with `LLM_PROVIDER`). Set **`DOCKER_HUB_USER=YOUR_DOCKER_ID`** to add the two image repository `--set` flags automatically, or pass them manually with `helm` as above.

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
