# ibac-demo on Kubernetes

Helm chart: [charts/ibac-demo](./charts/ibac-demo). Deploys **UI**, **agent**, and **one MCP pod** (`mcp-ibac-local-tools`, CRM tools over **SSE**). Same overall idea as [langgraph](../../../langgraph/README.md) / [google_adk](../../../google_adk/README.md): build images, `helm install`, port-forward UI, then import the Acuvity manifest.

## Contents

| Section | What it is |
|---------|------------|
| [Full procedure: first install](#full-procedure-first-install) | Steps **1 through 8** (do them in order) |
| [After code or image changes](#after-code-or-image-changes) | Rebuild agent image, push, restart pods |
| [Rotate API key](#rotate-openrouter-or-other-api-key-only) | Update a secret without reinstalling everything |
| [Progressive rollout (Apex)](#progressive-rollout-apex) | Optional mental model: local vs Apex vs in-cluster gateway |
| [Cloud-apex dev certificates](#cloud-apex-dev-certificates) | Dev signing pair for gateway installs (not [step 3](#3-apex-tls-bundle-configmap) client CA) |
| [Troubleshooting](#troubleshooting) | Common failures |
| [Reference](#reference) | Docker Hub private repos, Dockerfiles, CA skip, links |
| [MCP layout](#mcp-layout) | How the agent talks to MCP in-cluster |
| [Acuvity manifest](#acuvity-manifest) | `acuctl import` (OpenRouter provider, then app manifest) |
| [Local rehearsal without Kubernetes](#local-rehearsal-without-kubernetes) | Docker Compose |

## Full procedure: first install

Do **steps 1 through 8** below **in order**.

- **Build and push images:** shell working directory **`agents/ibac-demo`** (repo folder that contains `src/` and `Makefile`).
- **`helm` / `kubectl` / install script:** working directory **`agents/ibac-demo/deploy/k8s`** unless a command shows a full path.

There is no separate **`k3s/`** tree: one chart works for **Rancher Desktop**, **k3s**, or any cluster where `kubectl` points. This repo does not install the cluster for you.

### 1. Cluster tools

You need:

- **`kubectl`** talking to your cluster (`kubectl get nodes` shows **Ready**).
- **Helm 3.x** (`helm version`).
- **Docker** and [Docker Hub](https://hub.docker.com/) **`docker login`**. For `docker push`, use a Hub [PAT](https://hub.docker.com/settings/security) with **read and write** (read-only PAT causes `insufficient scopes`).

**Laptop cluster ([Rancher Desktop](https://rancherdesktop.io/)):** Install the app, open **Preferences**, enable **Kubernetes**, wait until it is running. Default context is often **`rancher-desktop`**; confirm with `kubectl get nodes`. The cluster usually **cannot** pull arbitrary local-only image tags; **push to Docker Hub** (or another registry) and set `image.*.repository` in Helm (step 5).

**Remote k3s (or other kube):** Use the **kubeconfig** your team gives you. The **same** Helm commands apply; only the API endpoint (and optional Ingress) differ.

### 2. Build and push images

Use your **Docker Hub username** (Docker ID), not your email, in image names. **Do not commit** real IDs into git.

**Option A - Makefile (recommended)**

From **`agents/ibac-demo`**:

```bash
cd agents/ibac-demo
export DOCKER_HUB_USER=YOUR_DOCKER_ID   # your real Docker Hub username; optional if you pass DOCKER_HUB_USER= on each make line below
docker login   # once per machine if needed
make docker-build
make docker-push
```

Same as `make docker-build DOCKER_HUB_USER=YOUR_DOCKER_ID` if you prefer not to `export`.

Optional: `make helm-lint` validates the chart. Set **`CONTAINER_TAG`** if you do not use `latest`.

**Option B - raw Docker** (same tags as Option A)

```bash
cd agents/ibac-demo

docker build -t YOUR_DOCKER_ID/ibac-demo-agent:latest -f src/agent/Dockerfile src/agent
docker build -t YOUR_DOCKER_ID/ibac-demo-ui:latest -f src/ui/Dockerfile src/ui
docker push YOUR_DOCKER_ID/ibac-demo-agent:latest
docker push YOUR_DOCKER_ID/ibac-demo-ui:latest
```

The **MCP** pod uses the **same** image as the agent (`ibac-demo-agent`). After **agent** or MCP code changes, rebuild and push **that** image and restart **both** `ibac-demo-agent` and `mcp-ibac-local-tools` ([After code or image changes](#after-code-or-image-changes)).

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

The chart defaults to **OpenRouter** (`agent.llmProvider`). For Anthropic or OpenAI instead, set `LLM_PROVIDER` and the matching secret when using [deploy-ibac-demo.sh](./deploy-ibac-demo.sh) or [deploy.sh](./deploy.sh) (same script), or adjust the `helm` flags in step 5.

Unset **`LLM_API_KEY`** in any environment where you intend **`OPENROUTER_API_KEY`** to apply (the app prefers `LLM_API_KEY` when set).

### 5. Install or upgrade Helm release

Replace **`YOUR_DOCKER_ID`** below with the **same** Docker Hub username you used in **step 2** (same value as **`DOCKER_HUB_USER`**).

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
# Same as: ./deploy.sh "${APEX_URL}"   (deploy.sh wraps deploy-ibac-demo.sh; matches langgraph/google_adk naming)
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

After workloads are healthy, import Acuvity YAML into **dev** (`api.acuvity.dev`). Order matters: **OpenRouter provider** first, then **app manifest**.

1. **Subject:** [../config/manifest.yaml](../config/manifest.yaml) uses **`@org=${APP_ORG}`**. **`export APP_ORG=acuvity.ai`** (or your org) before the **`envsubst | acuctl import`** line below, or replace that line with a literal **`@org=acuvity.ai`** and keep using **`- < deploy/config/manifest.yaml`**. Do not commit secrets.

2. **Shell** (example: project **marcus** from URL `https://console.acuvity.dev/apps/marcus/appagents` → path segment **`apps/marcus`**):

```bash
cd agents/ibac-demo

export APP_ORG='acuvity.ai'
export APP_PROJECT_PATH='apps/marcus'   # your slug after /apps/ in the console URL

acuctl import -A https://api.acuvity.dev \
  --namespace "/orgs/${APP_ORG}/${APP_PROJECT_PATH}" \
  - < deploy/config/providers-openrouter.yaml

envsubst < deploy/config/manifest.yaml | acuctl import -A https://api.acuvity.dev \
  --namespace "/orgs/${APP_ORG}/${APP_PROJECT_PATH}" -
```

3. If the app import fails on **`anthropic-api`**, ensure that provider exists in your project (org defaults or a separate provider import).

See **Acuvity manifest** below for multipart vs JSON notes on extractors.

---

## After code or image changes

When you change **Python agent** or **MCP** behavior, rebuild the **agent** image, push, then restart **both** deployments that use it:

```bash
cd agents/ibac-demo
docker build -t YOUR_DOCKER_ID/ibac-demo-agent:latest -f src/agent/Dockerfile src/agent
docker push YOUR_DOCKER_ID/ibac-demo-agent:latest
# Or from agents/ibac-demo, after: export DOCKER_HUB_USER=YOUR_DOCKER_ID
#   make docker-build && make docker-push

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

## Progressive rollout (Apex)

High-level order (details are **steps 1 through 8** above):

1. **App on cluster** - Images on a registry, Helm release healthy, UI via port-forward ([step 7](#7-access-the-ui)). This chart expects **Apex** (`ACUVITY_TOKEN`, `APEX_URL`, proxy on the agent pod). For **no Apex on Kubernetes** you would need a chart change or use [local Compose](../compose/README.md) / local dev without proxy.
2. **With Apex** - **Steps 3 through 5**: CA ConfigMap, secrets, `helm` or `./deploy.sh`.
3. **In-cluster gateway (e.g. cloud-apex)** - Install Acuvity’s gateway per their doc (Helm in the gateway namespace, not this chart). Set **`APEX_URL`** on **ibac-demo** to that gateway’s HTTPS URL. See [Cloud-apex dev certificates](#cloud-apex-dev-certificates) if you need a **dev signing pair** for the gateway itself.

### Cloud-apex dev certificates

This section is **only** for operators who install **cloud-apex** (or another in-cluster Apex gateway) in **development** when enterprise PKI is not used. It is **not** the same file as [step 3](#3-apex-tls-bundle-configmap).

| Files | Purpose |
|-------|---------|
| **`${APEX_URL}/_acuvity/ca.pem`** (step 3) | **Client trust**: the **ibac-demo** agent trusts the Apex HTTPS endpoint. Stored in ConfigMap **`acuvity-ca-bundle`**. |
| **`ca-cert.pem`** + **`ca-key.pem`** (below) | **Signing pair for the gateway** in dev (used by Acuvity’s gateway install, not by the ibac-demo Helm chart). |

From **`agents/ibac-demo/deploy/k8s`** (files land in **`ca/`**, which is [gitignored](../../.gitignore) so **`ca-key.pem` is never committed**):

```bash
mkdir -p ca
curl -fsS -o ./ca/ca-cert.pem \
  https://raw.githubusercontent.com/acuvity/demo-agents/refs/heads/main/certs/ca-cert.pem
curl -fsS -o ./ca/ca-key.pem \
  https://raw.githubusercontent.com/acuvity/demo-agents/refs/heads/main/certs/ca-key.pem
```

**Warnings:** Dev-only material; **do not commit** the private key; not for production. Use Acuvity’s full gateway documentation for **where** these paths are referenced (Helm values, secrets, mounts).

**After the gateway is running:** point **`APEX_URL`** at that gateway’s URL when you [export secrets for Helm](#4-export-secrets-for-helm). You may still need [step 3](#3-apex-tls-bundle-configmap) for **`_acuvity/ca.pem`** on **ibac-demo** pods so the agent trusts that endpoint, depending on your TLS chain.

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

## Reference

**Docker Hub:** Build and push commands are in [**step 2**](#2-build-and-push-images). Use Docker ID in tags and in **`image.agent.repository`** / **`image.ui.repository`** (step 5). Do not put secrets or real IDs in git.

**Private Hub images:** Create a `docker-registry` secret in namespace **`ibac-demo`**, then set [`imagePullSecrets`](./charts/ibac-demo/values.yaml) to that secret’s name.

**Dockerfiles:** Agent (and MCP) [../../src/agent/Dockerfile](../../src/agent/Dockerfile); UI [../../src/ui/Dockerfile](../../src/ui/Dockerfile).

**CA bundle:** Same as **step 3**. Quick test without custom CA: add **`--set agent.acuvityCaBundle.enabled=false`** to Helm (not recommended for production).

**Install and UI URL:** Full **`helm upgrade --install`** and **`./deploy.sh`** examples are in **steps 5 and 7**. Overrides: [example-values.yaml](./example-values.yaml). UI: port-forward **3000:80**, open **http://localhost:3000/** (Vite proxies `/api` via `BACKEND_URL`).

## MCP layout

- **One** MCP server pod exposes **all** CRM tools (same process as local `MCP_SERVER=local` stdio mode).
- The agent uses `LOCAL_MCP_SSE_URL` pointing at `http://mcp-ibac-local-tools.<namespace>.svc.cluster.local:8000/sse` (set automatically by the chart).
- The agent pod sets **`NO_PROXY` / `no_proxy`** for `127.0.0.1`, `localhost`, and **`.svc.cluster.local`** so MCP SSE traffic does not go through **Acuvity `HTTP_PROXY`** (that would cause `httpx.ConnectError` to internal DNS names).

## Acuvity manifest

Files:

- [../config/providers-openrouter.yaml](../config/providers-openrouter.yaml) - **OpenRouter** provider for egress `providers: [openrouter]`. Import **first** with the same **`-A`** and **`--namespace`** as the app.
- [../config/manifest.yaml](../config/manifest.yaml) - **ibac-demo** app (UI, agent, **mcp-servers**; selectors **`type: None`**, listener hosts still match in-cluster DNS when you use Helm).

`subject` is **`@org=${APP_ORG}`** only (expand with **`envsubst`** or edit to a literal org). Listener **hosts** in the manifest align with Helm when you use the cluster: agent **`ibac-demo-agent`**, MCP **`mcp-ibac-local-tools`**, ports **8000** for agent and MCP, **80** for UI ACL.

**Note:** The sample Lua extractors for `POST /send` assume a **JSON** body (`{"message":"..."}`). The interactive UI often sends **multipart/form-data** with a PDF. Adjust extractors for your policy needs or add a JSON-only path if required.

## Local rehearsal without Kubernetes

See [../compose/README.md](../compose/README.md).
