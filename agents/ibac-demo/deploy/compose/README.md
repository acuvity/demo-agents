# Docker Compose (optional)

Three services: **mcp** (CRM tools over SSE), **agent** (FastAPI), **ui** (nginx + static build).

This mirrors the Kubernetes layout on a single machine. You still need valid Acuvity and LLM credentials.

## Quick start

1. Copy `.env.template` to `.env` and set variables (same ideas as [../../README.md](../../README.md) for `run_ui.sh`).
2. Set `HTTPS_PROXY` and `HTTP_PROXY` like `run_ui.sh` does from `ACUVITY_TOKEN` and `APEX_URL`.
3. If TLS to Apex fails inside containers, mount your `ca.pem` and set `SSL_CERT_FILE`, or bake the CA into a custom image.

```bash
docker compose --env-file .env up --build
```

- UI: http://localhost:5174/
- MCP (debug): http://localhost:18000/sse
- Agent (debug): http://localhost:8300/health

The UI proxies `/api` to the agent service via the image `nginx.conf` (service name `agent` on port 8000).
