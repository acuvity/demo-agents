# ibac-demo agent API (FastAPI + LangGraph)
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
 && uv sync --frozen --no-dev

COPY . .

EXPOSE 8000

# PORT defaults to 8000 for Kubernetes; local run_ui.sh still uses 8300 on the host.
CMD ["sh", "-c", "exec uv run uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
