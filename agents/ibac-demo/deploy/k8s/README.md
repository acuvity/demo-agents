# ibac-demo on Kubernetes

Helm chart: [charts/ibac-demo](./charts/ibac-demo). Follows the same layout as [fast-agent](../../../fast-agent/deploy/k8s): **UI Deployment**, **agent Deployment**, and **one MCP Tool Deployment** (`mcp-ibac-local-tools`) that runs all CRM tools from `tools/mcp_tools.py` over **SSE**. The overall flow matches [langgraph](../../../langgraph/README.md) and [google_adk](../../../google_adk/README.md) (Helm chart, port-forward to the UI Service, then import the Acuvity manifest), with ibac-demo-specific steps for Acuvity secrets, Apex URL, and two images (agent and UI).

## Full procedure: first install

Do these steps in order. **Working directories:** run `docker` / `docker build` from **`agents/ibac-demo`**. Run **`helm`** and **`kubectl`** from **`agents/ibac-demo/deploy/k8s`** (or pass absolute paths to the chart).

### 1. Prerequisites

- `kubectl` configured for your cluster (for example **Rancher Desktop** with Kubernetes enabled; `kubectl get nodes` shows **Ready**).
- **Helm 3.x** (`helm version`).
- **Docker** with `docker login` to [Docker Hub](https://hub.docker.com/). For `docker push`, use a [Personal Access Token](https://hub.docker.com/settings/security) with **read and write** scope (a read-only token causes `insufficient scopes`).

### 2. Build and push images

Replace `YOUR_DOCKER_ID` with your Docker Hub username.

```bash
cd agents/ibac-demo

docker build -t YOUR_DOCKER_ID/ibac-demo-agent:latest -f src/agent/Dockerfile src/agent
docker build -t YOUR_DOCKER_ID/ibac-demo-ui:latest -f src/ui/Dockerfile src/ui
docker push YOUR_DOCKER_ID/ibac-demo-agent:latest
docker push YOUR_DOCKER_ID/ibac-demo-ui:latest
```

The **MCP** pod uses the **same** image as the agent (`ibac-demo-agent`). After **agent** code changes, rebuild and push **that** image and restart **both** `ibac-demo-agent` and `mcp-ibac-local-tools`.

### 3. Apex TLS bundle (ConfigMap)

Recommended before install. The chart mounts ConfigMap **`acuvity-ca-bundle`** (key **`ca-bundle.crt`**) when `agent.acuvityCaBundle.enabled` is true (default).

Obtain `ca.pem` once (from repo root **`agents/ibac-demo`**):

```bash
curl -sS -o src/agent/ca.pem "${APEX_URL}/_acuvity/ca.pem"
```

(`APEX_URL` must be your real Apex URL, for example `https://your-tenant.acuvity.dev`.)

Create the namespace and ConfigMap (use an **absolute** path if you are not in `agents/ibac-demo`):

```bash
kubectl create namespace ibac-demo 2>/dev/null || true
kubectl -n ibac-demo create configmap acuvity-ca-bundle \
  --from-file=ca-bundle.crt=./src/agent/ca.pem
```

If you skip the bundle for a quick test only, add **`--set agent.acuvityCaBundle.enabled=false`** to the `helm` command in step 5 (not recommended for production).

### 4. Export secrets for Helm

In the same shell you will use for `helm` (do not commit these):

```bash
export ACUVITY_TOKEN='...'
export APEX_URL='https://your-apex-host'
export OPENROUTER_API_KEY='...'
```

The chart defaults to **OpenRouter** (`agent.llmProvider`). For Anthropic or OpenAI instead, set `LLM_PROVIDER` and the matching secret when using [deploy-ibac-demo.sh](./deploy-ibac-demo.sh), or adjust the `helm` flags in step 5.

Unset **`LLM_API_KEY`** in any environment where you intend **`OPENROUTER_API_KEY`** to apply (the app prefers `LLM_API_KEY` when set).

### 5. Install or upgrade Helm release

```bash
cd agents/ibac-demo/deploy/k8s

helm upgrade --install ibac-demo ./charts/ibac-demo -n ibac-demo \
  --set "secrets.acuvity_token=${ACUVITY_TOKEN}" \
  --set secrets.anthropic_api_key="" \
  --set secrets.openai_api_key="" \
  --set "secrets.openrouter_api_key=${OPENROUTER_API_KEY}" \
  --set "agent.apexUrl=${APEX_URL}" \
  --set agent.llmProvider=openrouter \
  --set image.agent.repository=YOUR_DOCKER_ID/ibac-demo-agent \
  --set image.ui.repository=YOUR_DOCKER_ID/ibac-demo-ui
```

**Alternative:** from `deploy/k8s`, with the same exports:

```bash
export DOCKER_HUB_USER=YOUR_DOCKER_ID
./deploy-ibac-demo.sh "${APEX_URL}"
```

That script sets Acuvity and LLM secrets and, when **`DOCKER_HUB_USER`** is set, adds the two image repository overrides. You must still create the namespace and **acuvity-ca-bundle** ConfigMap yourself if you use the script (same as above).

### 6. Verify workloads

```bash
kubectl -n ibac-demo get pods
```

Wait until **agent**, **ui**, and **mcp-ibac-local-tools** are **Running** and **READY 1/1**.

### 7. Access the UI

Keep this terminal open (**port-forward blocks** until you press Ctrl+C):

```bash
kubectl -n ibac-demo port-forward svc/ibac-demo-ui 3000:80
```

Open **http://localhost:3000/** in your browser.

If the UI shows **Failed to fetch**, the browser never reached the app reliably: confirm port-forward is still running, pods are healthy, then `curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/api/scenarios` (expect **200**).

### 8. Acuvity manifest (policy)

After workloads are healthy, import [../config/manifest.yaml](../config/manifest.yaml) with placeholders updated for your org. See **Acuvity manifest** below for multipart vs JSON notes.

---

## After code or image changes

When you change **Python agent** or **MCP** behavior, rebuild the **agent** image, push, then restart **both** deployments that use it:

```bash
cd agents/ibac-demo
docker build -t YOUR_DOCKER_ID/ibac-demo-agent:latest -f src/agent/Dockerfile src/agent
docker push YOUR_DOCKER_ID/ibac-demo-agent:latest

kubectl -n ibac-demo rollout restart deploy/ibac-demo-agent deploy/mcp-ibac-local-tools
```

If the cluster uses **`latest`** and does not pull a new digest, delete the agent and MCP pods once or bump the image tag in Helm and upgrade.

---

## Rotate OpenRouter (or other) API key only

```bash
export OPENROUTER_API_KEY='sk-or-v1-new-key'

helm upgrade --install ibac-demo ./charts/ibac-demo -n ibac-demo \
  --reuse-values \
  --set "secrets.openrouter_api_key=${OPENROUTER_API_KEY}"

kubectl -n ibac-demo rollout restart deploy/ibac-demo-agent
```

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| **`Failed to fetch`** in the browser | Port-forward still running; `kubectl get pods`; `curl` to `http://127.0.0.1:3000/api/scenarios` |
| **`Agent failed while processing your request.`** | `kubectl -n ibac-demo logs deploy/ibac-demo-agent --tail=150` for the real traceback |
| **`httpx.ConnectError`** to MCP / `*.svc.cluster.local` | Chart sets **`NO_PROXY`** for `.svc.cluster.local` on the agent pod so MCP bypasses Acuvity `HTTP_PROXY`. Re-apply Helm if you are on an old chart. |
| **`TypeError` / `read_timeout_seconds`** on MCP SSE | Fixed in app config (`timeout` / `sse_read_timeout` for `langchain-mcp-adapters` 0.2.x). Rebuild and push the **agent** image, restart agent and MCP pods. |
| **OpenRouter 403** (team, etc.) | Often differs for traffic through Apex vs direct; compare with local `run_ui.sh` (proxy on) vs `uv run server.py` without proxy. |
| **`docker push` insufficient scopes** | New Hub PAT with **write** access; `docker login` again. |

For deep HTTP debugging on the agent, set env **`DEBUG_PROXY_UPSTREAM=1`** or **`DEBUG_ACUVITY_BLOCKS=1`** on the deployment (Helm extra envs or `kubectl set env`) and read pod logs. Do not share logs that contain tokens.

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

## Prerequisites (reference)

- Kubernetes cluster and `kubectl` (for example **Rancher Desktop** with Kubernetes enabled).
- [Helm](https://helm.sh/) 3.x.
- **Agent image**: [../../src/agent/Dockerfile](../../src/agent/Dockerfile) (also used for the MCP pod).
- **UI image**: [../../src/ui/Dockerfile](../../src/ui/Dockerfile).

The **ordered first-run steps** (build, push, ConfigMap, `helm`, port-forward) are in **[Full procedure: first install](#full-procedure-first-install)** at the top of this file.

## Acuvity CA bundle (reference)

Same as **step 3** in [Full procedure](#full-procedure-first-install): ConfigMap **`acuvity-ca-bundle`**, key **`ca-bundle.crt`**, file usually **`src/agent/ca.pem`** (fetch with `curl "${APEX_URL}/_acuvity/ca.pem"` from **`agents/ibac-demo`**). To skip for a quick test, set `agent.acuvityCaBundle.enabled=false`.

## Install and Access (reference)

**Helm `OpenRouter` example, helper script, and Anthropic variant** are spelled out in **steps 5 and 7** of [Full procedure](#full-procedure-first-install). [example-values.yaml](./example-values.yaml) lists common value overrides.

**UI access:** `kubectl -n ibac-demo port-forward svc/ibac-demo-ui 3000:80` then **http://localhost:3000/** (Vite proxies `/api` to the agent Service via `BACKEND_URL`).

## MCP layout

- **One** MCP server pod exposes **all** CRM tools (same process as local `MCP_SERVER=local` stdio mode).
- The agent uses `LOCAL_MCP_SSE_URL` pointing at `http://mcp-ibac-local-tools.<namespace>.svc.cluster.local:8000/sse` (set automatically by the chart).
- The agent pod sets **`NO_PROXY` / `no_proxy`** for `127.0.0.1`, `localhost`, and **`.svc.cluster.local`** so MCP SSE traffic does not go through **Acuvity `HTTP_PROXY`** (that would cause `httpx.ConnectError` to internal DNS names).

## Acuvity manifest

Import [../config/manifest.yaml](../config/manifest.yaml) after you replace placeholders (`label`, `subject`, namespace, app name if needed). Deployment names in the manifest assume Helm release name **`ibac-demo`** in namespace **`ibac-demo`**.

**Note:** The sample Lua extractors for `POST /send` assume a **JSON** body (`{"message":"..."}`). The interactive UI often sends **multipart/form-data** with a PDF. Adjust extractors for your policy needs or add a JSON-only path if required.

## Local rehearsal without Kubernetes

See [../compose/README.md](../compose/README.md).
