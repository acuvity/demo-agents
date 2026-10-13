# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser

COPY --from=builder /app /app

RUN chown -R appuser:appuser /app

USER appuser

ARG AGENT_MODULE
ARG AGENT_PORT
ENV AGENT_MODULE=${AGENT_MODULE} \
    AGENT_PORT=${AGENT_PORT}

EXPOSE ${AGENT_PORT}

CMD uvicorn ${AGENT_MODULE}:a2a_app --host 0.0.0.0 --port ${AGENT_PORT}
