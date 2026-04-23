# Docker Compose (optional)

Three services: **mcp** (CRM tools over SSE), **agent** (FastAPI), **ui** (Vite dev server, same pattern as langgraph/google_adk).

This mirrors the Kubernetes layout on a single machine. You still need valid Acuvity and LLM credentials.

If you are **new to deploying this app**, run through **[../k8s/README.md](../k8s/README.md)** once on a real cluster first; Compose does not replace that learning path.

For a **full ordered checklist** (including Rancher Desktop, Docker Hub, and Helm), see **[../k8s/README.md](../k8s/README.md)**. Compose is an optional shortcut for developers who prefer one machine without a cluster.

## Quick start

1. Create `deploy/compose/.env` (this path is gitignored) with at least:
   - `ACUVITY_TOKEN`, `APEX_URL`, and the matching LLM key. The app defaults to **OpenRouter** (`LLM_PROVIDER=openrouter` if unset in compose); use **`OPENROUTER_API_KEY`**, or set `LLM_PROVIDER` and `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` instead.
   - Optionally add `HTTP_PROXY` and `HTTPS_PROXY` (e.g. `HTTP_PROXY=https://token:<ACUVITY_TOKEN>@<apex-host>`). If not set, `run_ui.sh` builds them at startup from `ACUVITY_TOKEN` and `APEX_URL`.

2. Place the Apex CA cert at `deploy/compose/ca.pem` (committed to the repo). The agent container mounts it at `/etc/ssl/certs/custom/ca.pem` and `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` point to it automatically.

```bash
cd deploy/compose
docker compose --env-file .env up --build
```

- UI: http://localhost:5174/
- MCP (debug): http://localhost:18000/sse
- Agent (debug): http://localhost:8300/health

The UI sets `BACKEND_URL=http://agent:8000` so Vite proxies `/api` to the agent service (port 8000 inside the compose network).
