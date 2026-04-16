# Docker Compose (optional)

Three services: **mcp** (CRM tools over SSE), **agent** (FastAPI), **ui** (Vite dev server, same pattern as langgraph/google_adk).

This mirrors the Kubernetes layout on a single machine. You still need valid Acuvity and LLM credentials.

If you are **new to deploying this app**, run through **[../k8s/README.md](../k8s/README.md)** once on a real cluster first; Compose does not replace that learning path.

For a **full ordered checklist** (including Rancher Desktop, Docker Hub, and Helm), see **[../k8s/README.md](../k8s/README.md)**. Compose is an optional shortcut for developers who prefer one machine without a cluster.

## Quick start

1. Create `deploy/compose/.env` (this path is gitignored) with at least:
   - `ACUVITY_TOKEN`, `APEX_URL`, and the matching LLM key. The app defaults to **OpenRouter** (`LLM_PROVIDER=openrouter` if unset in compose); use **`OPENROUTER_API_KEY`**, or set `LLM_PROVIDER` and `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` instead.
   - `HTTPS_PROXY` and `HTTP_PROXY` built the same way as [../../README.md](../../README.md) for `./src/agent/run_ui.sh`.
   - **`NO_PROXY`** and **`no_proxy`** set to `127.0.0.1,localhost,.svc.cluster.local` when using `HTTPS_PROXY`, so in-cluster or local MCP HTTP clients do not send internal URLs through the external proxy (same idea as the Helm agent pod).
   - `SSL_CERT_FILE` pointing at your Apex CA (for example the same `ca.pem` you fetch for local runs).
2. If TLS to Apex fails inside containers, mount your `ca.pem` and set `SSL_CERT_FILE`, or bake the CA into a custom image.

```bash
cd deploy/compose
docker compose --env-file .env up --build
```

- UI: http://localhost:5174/
- MCP (debug): http://localhost:18000/sse
- Agent (debug): http://localhost:8300/health

The UI sets `BACKEND_URL=http://agent:8000` so Vite proxies `/api` to the agent service (port 8000 inside the compose network).
