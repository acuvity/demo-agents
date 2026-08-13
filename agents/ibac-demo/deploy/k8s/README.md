# ibac-demo on Kubernetes

Helm chart at `[charts/ibac-demo](./charts/ibac-demo)`. Deploys **UI**, **agent**, and **MCP** pod (`mcp-ibac-local-tools`, CRM tools over SSE).

> **Working directories**
>
> - Build/push commands: run from `**agents/ibac-demo`**
> - Helm/kubectl commands: run from `**agents/ibac-demo/deploy/k8s**`

---

## Prerequisites

- `kubectl` pointing at your cluster (`kubectl get nodes` shows **Ready**)
- Helm 3.x (`helm version`)
- Docker + Docker Hub account with a [PAT](https://hub.docker.com/settings/security) that has **read/write** scope

**Rancher Desktop:** Enable Kubernetes in Preferences, wait until running, confirm with `kubectl get nodes`.

---

## Install (steps 1-8, in order)

### 1. Build and push images

From `**agents/ibac-demo`**:

```bash
export DOCKER_HUB_USER=YOUR_DOCKER_ID
docker login
make docker-build
make docker-push
```

> **Manual alternative:**
>
> ```bash
> docker build -t YOUR_DOCKER_ID/ibac-demo-agent:latest -f src/agent/Dockerfile src/agent
> docker build -t YOUR_DOCKER_ID/ibac-demo-ui:latest    -f src/ui/Dockerfile    src/ui
> docker push YOUR_DOCKER_ID/ibac-demo-agent:latest
> docker push YOUR_DOCKER_ID/ibac-demo-ui:latest
> ```

### 2. Create namespace

```bash
kubectl create namespace ibac-demo 2>/dev/null || true
```

### 3. Apex TLS ConfigMap

From `**agents/ibac-demo**`:

```bash
curl -sS -o src/agent/ca.pem "${APEX_URL}/_acuvity/ca.pem"

kubectl -n ibac-demo create configmap acuvity-ca-bundle \
  --from-file=ca-bundle.crt=./src/agent/ca.pem \
  --dry-run=client -o yaml | kubectl apply -f -
```

> Skip for quick tests only: add `--set agent.acuvityCaBundle.enabled=false` to the helm command in step 5. Not recommended for production.

### 4. Export secrets

```bash
export ACUVITY_TOKEN='...'
export APEX_URL='https://your-apex-host'
export OPENROUTER_API_KEY='...'
```

> Using OpenAI or Anthropic instead? Set `LLM_PROVIDER` and the matching key variable. Unset `LLM_API_KEY` if you intend `OPENROUTER_API_KEY` to take effect (the app prefers `LLM_API_KEY` when set).

### 5. Install with Helm

From `**agents/ibac-demo/deploy/k8s**`:

```bash
cd agents/ibac-demo/deploy/k8s

helm upgrade --install ibac-demo ./charts/ibac-demo -n ibac-demo \
  --set "secrets.acuvity_token=${ACUVITY_TOKEN}" \
  --set secrets.anthropic_api_key="" \
  --set secrets.openai_api_key="" \
  --set "secrets.openrouter_api_key=${OPENROUTER_API_KEY}" \
  --set "agent.apexUrl=${APEX_URL}" \
  --set agent.llmProvider=openrouter \
  --set image.agent.repository=${YOUR_DOCKER_ID}/ibac-demo-agent \
  --set image.ui.repository=YOUR_DOCKER_ID/ibac-demo-ui
```

> **Script alternative** (same exports must be set, namespace + ConfigMap still required from step 2/3):
>
> ```bash
> export DOCKER_HUB_USER=YOUR_DOCKER_ID
> ./deploy-ibac-demo.sh "${APEX_URL}"
> ```

### 6. Verify pods

```bash
kubectl -n ibac-demo get pods
```

Wait until **agent**, **ui**, **mcp-ibac-local-tools**, **mailpit**, and **webhook-receiver** are `Running` and `READY 1/1`.

### 7. Access the UI and demo services

Open a separate terminal for each port-forward (each blocks until Ctrl+C):

```bash
# Demo UI
kubectl -n ibac-demo port-forward svc/ibac-demo-ui 3000:80

# Demo 1 - captured emails
kubectl -n ibac-demo port-forward svc/mailpit 8025:8025

# Demo 2 - captured webhook calls
kubectl -n ibac-demo port-forward svc/webhook-receiver 9000:9000
```


| What                            | URL                                                          |
| ------------------------------- | ------------------------------------------------------------ |
| Demo UI                         | [http://localhost:3000/](http://localhost:3000/)             |
| Captured emails (Demo 1)        | [http://localhost:8025/](http://localhost:8025/)             |
| Captured webhook calls (Demo 2) | [http://localhost:9000/events](http://localhost:9000/events) |


> **Verify UI:** `curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/api/scenarios` should return `200`.

### 8. Import Acuvity manifest

From `**agents/ibac-demo`**:

```bash
export APP_ORG='acuvity.ai'                 # your org
export APP_PROJECT_PATH='apps/marcus'       # path after /apps/ in your console URL

# 1. Import OpenRouter provider first
acuctl import -A https://api.acuvity.dev \
  --namespace "/orgs/${APP_ORG}/${APP_PROJECT_PATH}" \
  - < deploy/config/providers-openrouter.yaml

# 2. Then import the app manifest
envsubst < deploy/config/manifest.yaml | acuctl import -A https://api.acuvity.dev \
  --namespace "/orgs/${APP_ORG}/${APP_PROJECT_PATH}" -
```

> If the app import fails on `anthropic-api`, ensure that provider exists in your project first.

---

## Day 2 operations

For first-time install, follow steps 1-8 above. The sections below cover what to run after that.

### After a code change

**Which image covers which pods:**


| Changed code                                             | Image rebuilt     | Pods to restart                                               |
| -------------------------------------------------------- | ----------------- | ------------------------------------------------------------- |
| `src/agent/` (Python agent, MCP tools, webhook receiver) | `ibac-demo-agent` | `ibac-demo-agent`, `mcp-ibac-local-tools`, `webhook-receiver` |
| `src/ui/` (React frontend)                               | `ibac-demo-ui`    | `ibac-demo-ui`                                                |


From `**agents/ibac-demo`**:

```bash
export DOCKER_HUB_USER=YOUR_DOCKER_ID
make docker-build && make docker-push
```

Then restart the relevant pods. For agent/MCP/backend changes:

```bash
kubectl -n ibac-demo rollout restart deploy/ibac-demo-agent deploy/mcp-ibac-local-tools deploy/webhook-receiver
```

For UI-only changes:

```bash
kubectl -n ibac-demo rollout restart deploy/ibac-demo-ui
```

Watch until all pods are `Running` and `READY 1/1`:

```bash
kubectl -n ibac-demo get pods -w
```

> `**latest` tag caveat:** if the cluster has cached the old digest and does not pull the new one, delete the pod manually (`kubectl -n ibac-demo delete pod <pod-name>`) or bump `CONTAINER_TAG` (e.g. `make docker-build CONTAINER_TAG=v2`) and re-run Helm with `--set image.agent.tag=v2`.

### After a Helm values change only (no code change)

No rebuild needed. Just re-apply Helm with `--reuse-values` and the updated flag:

```bash
cd agents/ibac-demo/deploy/k8s

helm upgrade --install ibac-demo ./charts/ibac-demo -n ibac-demo \
  --reuse-values \
  --set "the.changed.value=new-value"

kubectl -n ibac-demo rollout restart deploy/ibac-demo-agent
```

---

## Rotate an API key

```bash
export OPENROUTER_API_KEY='sk-or-v1-new-key'

helm upgrade --install ibac-demo ./charts/ibac-demo -n ibac-demo \
  --reuse-values \
  --set "secrets.openrouter_api_key=${OPENROUTER_API_KEY}"

kubectl -n ibac-demo rollout restart deploy/ibac-demo-agent
```

---

## Troubleshooting


| Symptom                                                                             | What to check                                                                                                                                                                                                                                                   |
| ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `**Failed to fetch**` in browser                                                    | Port-forward still running; `kubectl get pods`; `curl http://127.0.0.1:3000/api/scenarios`                                                                                                                                                                      |
| `**Agent failed while processing your request.**`                                   | `kubectl -n ibac-demo logs deploy/ibac-demo-agent --tail=150`                                                                                                                                                                                                   |
| `**httpx.ConnectError**` to MCP / `*.svc.cluster.local`                             | Re-apply Helm - chart sets `NO_PROXY` for `.svc.cluster.local`                                                                                                                                                                                                  |
| `**TypeError` / `read_timeout_seconds**` on MCP SSE                                 | Rebuild + push agent image, restart agent and MCP pods                                                                                                                                                                                                          |
| `**Unknown tool: <name>**` from MCP                                                 | Agent and MCP pods are on different image versions. Restart both: `kubectl -n ibac-demo rollout restart deploy/ibac-demo-agent deploy/mcp-ibac-local-tools`                                                                                                     |
| `**NotImplementedError: MultiServerMCPClient cannot be used as a context manager**` | `langchain-mcp-adapters` 0.1.0+ dropped context manager support. Fix `runtime/runtime.py`: replace `async with MultiServerMCPClient(...) as client:` with `client = MultiServerMCPClient(...)` then call `await client.get_tools()` directly. Rebuild and push. |
| **OpenRouter 403**                                                                  | Compare direct vs Apex traffic; check team/key restrictions                                                                                                                                                                                                     |
| `**docker push` insufficient scopes**                                               | Hub PAT needs **write** access; `docker login` again                                                                                                                                                                                                            |


For deep HTTP debugging: set `DEBUG_PROXY_UPSTREAM=1` or `DEBUG_ACUVITY_BLOCKS=1` on the agent deployment and read pod logs. Do not share logs that contain tokens.

---

## Reference


| Topic                            | Details                                                                                                                                                                                            |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Dockerfiles**                  | Agent + MCP: `src/agent/Dockerfile`; UI: `src/ui/Dockerfile`                                                                                                                                       |
| **Helm value overrides**         | See `[example-values.yaml](./example-values.yaml)`                                                                                                                                                 |
| **Private Hub images**           | Create a `docker-registry` secret in `ibac-demo` namespace, set `imagePullSecrets` in values                                                                                                       |
| **MCP layout**                   | Agent connects to `http://mcp-ibac-local-tools.<namespace>.svc.cluster.local:8000/sse` via `LOCAL_MCP_SSE_URL` (set automatically by chart). `NO_PROXY` prevents MCP traffic routing through Apex. |
| **Mailpit**                      | Fake SMTP server for Demo 1. Disable with `--set mailpit.enabled=false`.                                                                                                                           |
| **Webhook receiver**             | HTTP event logger for Demo 2. Disable with `--set webhookReceiver.enabled=false`.                                                                                                                  |
| **Acuvity manifest files**       | `deploy/config/providers-openrouter.yaml` (import first); `deploy/config/manifest.yaml` (app)                                                                                                      |
| **Extractors note**              | Sample Lua extractors assume a JSON body (`{"message":"..."}`). The interactive UI sends multipart/form-data with PDF - adjust extractors for your policy.                                         |
| **Local dev without Kubernetes** | See `[deploy/compose/README.md](../compose/README.md)`                                                                                                                                             |


### In-cluster Apex gateway (advanced)

Only needed if you are installing **cloud-apex** in-cluster. These are dev signing certificates for the **gateway itself** - not the same as the CA bundle in step 3.

From `**agents/ibac-demo/deploy/k8s`**:

```bash
mkdir -p ca
curl -fsS -o ./ca/ca-cert.pem \
  https://raw.githubusercontent.com/acuvity/demo-agents/refs/heads/main/certs/ca-cert.pem
curl -fsS -o ./ca/ca-key.pem \
  https://raw.githubusercontent.com/acuvity/demo-agents/refs/heads/main/certs/ca-key.pem
```

> `ca/` is gitignored. Never commit the private key. Dev only.

After the gateway is running, point `APEX_URL` at its HTTPS URL in step 4. You may still need step 3 (`_acuvity/ca.pem`) so the agent trusts the gateway TLS endpoint.