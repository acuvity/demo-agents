# Docker Compose (optional)

Three services: **mcp** (CRM tools over SSE), **agent** (FastAPI), **ui** (Vite dev server, same pattern as langgraph/google_adk).

This mirrors the Kubernetes layout on a single machine. You still need valid Acuvity and LLM credentials.

## Quick start

1. Create `deploy/compose/.env` (this path is gitignored) with at least:
   - `ACUVITY_TOKEN`, `APEX_URL`, `LLM_PROVIDER`, and the matching LLM key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `OPENROUTER_API_KEY`).
   - `HTTPS_PROXY` and `HTTP_PROXY` built the same way as [../../README.md](../../README.md) for `./src/agent/run_ui.sh`.
   - `SSL_CERT_FILE` pointing at your Apex CA (for example the same `ca.pem` you fetch for local runs).
2. If TLS to Apex fails inside containers, mount your `ca.pem` and set `SSL_CERT_FILE`, or bake the CA into a custom image.

```bash
docker compose --env-file .env up --build
```

- UI: http://localhost:5174/
- MCP (debug): http://localhost:18000/sse
- Agent (debug): http://localhost:8300/health

The UI sets `BACKEND_URL=http://agent:8000` so Vite proxies `/api` to the agent service (port 8000 inside the compose network).
