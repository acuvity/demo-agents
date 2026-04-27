# Docker Compose Deployment

Services: `mailpit`, `webhook-receiver`, `mcp`, `mcp-tls`, `agent`, `ui`, `cloud-apex`

---

## Prerequisites

- Docker Desktop / Rancher Desktop running
- `acuctl` installed
- CA cert files in `deploy/compose/ca/` (`ca-cert.pem`, `ca-key.pem`)

---

## Initial Setup (run once)

### 1. Create the combined CA bundle

From the repo root `agents/ibac-demo/`:

```bash
cd src/agent
mkdir -p ca
cp ../deploy/compose/ca/ca-cert.pem ca/ca-cert.pem
cat "$(uv run python3 -c "import certifi; print(certifi.where())")" ca/ca-cert.pem > ca/combined-ca.pem
```

### 2. Create `deploy/compose/.env`

```
APEX_URL=https://cloud-apex:8443
APP_TOKEN=<your app token from console.acuvity.ai>
APEX_API_TOKEN=<same value as APP_TOKEN>
OPENROUTER_API_KEY=<your OpenRouter key>
CA_CERT_PATH=./ca/ca-cert.pem
CA_KEY_PATH=./ca/ca-key.pem
```

Get your `APP_TOKEN` from [console.acuvity.ai](https://console.acuvity.ai) under **Access > App Tokens**.

### 3. Import provider and manifest

From `agents/ibac-demo/`:

```bash
export APP_ORG='acuvity.ai'
export APP_PROJECT='cloud-apex-test'   # your project name

acuctl import -A https://api.acuvity.dev \
  --namespace "/orgs/${APP_ORG}/apps/${APP_PROJECT}" \
  - < deploy/config/providers-openrouter.yaml

acuctl import -A https://api.acuvity.dev \
  --namespace "/orgs/${APP_ORG}/apps/${APP_PROJECT}" \
  - < ibac-manifest.yaml
```

### 4. Start

```bash
cd deploy/compose
docker compose --env-file .env up --build
```

Open **http://localhost:5174** - that's the UI.

---

## After a Code Change

```bash
cd deploy/compose
docker compose --env-file .env up --build
```

---

## After a Manifest Change

Re-run the imports from step 3, then restart:

```bash
docker compose --env-file .env down
docker compose --env-file .env up --build
```

---

## After a Token or URL Change

Update `.env`, then restart:

```bash
docker compose --env-file .env down
docker compose --env-file .env up --build
```

---

## Useful Endpoints

| Service | URL |
|---|---|
| UI | http://localhost:5174 |
| Agent API | http://localhost:8300/health |
| MCP (debug) | http://localhost:18000/sse |
| Mailpit (email UI) | http://localhost:8025 |
| cloud-apex | https://localhost:9443 |
