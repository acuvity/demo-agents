from __future__ import annotations

import logging
import socket
import urllib.parse
from typing import Any

from agents import set_tracing_disabled

logger = logging.getLogger("uvicorn.error")

try:
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace import set_tracer_provider

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.threading import ThreadingInstrumentor

    from openinference.instrumentation.mcp import MCPInstrumentor

    OTEL_AVAILABLE = True
    OTEL_IMPORT_ERR_MSG = ""

except ImportError as exc:  # pragma: no cover
    OTEL_AVAILABLE = False
    OTEL_IMPORT_ERR_MSG = str(exc)


class OtelProbeError(RuntimeError):
    pass


def warn(msg: str) -> None:
    logger.warning(msg)


def info(msg: str) -> None:
    logger.info(msg)


def setup_otel(cfg: dict) -> "TracerProvider | None":
    """
    Configure OpenTelemetry from the optional 'otel' section of the config.
    Never raises — failures degrade gracefully.
    """

    if not OTEL_AVAILABLE:
        warn(
            "OpenTelemetry packages are not installed - tracing disabled. "
            f"({OTEL_IMPORT_ERR_MSG})"
        )
        set_tracing_disabled(True)
        return None

    if "otel" not in cfg:
        warn("No 'otel' section found in config - tracing disabled.")
        set_tracing_disabled(True)
        return None

    otel_cfg: dict = cfg["otel"]

    if not otel_cfg.get("enabled", True):
        info("otel: tracing disabled via config")
        set_tracing_disabled(True)
        return None

    service_name: str = otel_cfg.get("service_name", "mcp-agent")
    exporter_type: str = otel_cfg.get("exporter", "console").lower()

    try:
        if exporter_type == "console":
            exporter = ConsoleSpanExporter()

        elif exporter_type == "otlp_http":
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            endpoint = otel_cfg.get("otlp_http", {}).get(
                "endpoint", "http://localhost:4318/v1/traces"
            )
            exporter = OTLPSpanExporter(endpoint=endpoint)
            probe_otlp_http(endpoint)

        elif exporter_type == "otlp_grpc":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            endpoint = otel_cfg.get("otlp_grpc", {}).get(
                "endpoint", "http://localhost:4317"
            )
            exporter = OTLPSpanExporter(endpoint=endpoint)
            probe_otlp_grpc(endpoint)

        else:
            warn(f"Unknown OTEL exporter '{exporter_type}' - tracing disabled")
            set_tracing_disabled(True)
            return None

    except OtelProbeError as exc:
        warn(f"otel: exporter endpoint unreachable - tracing disabled ({exc})")
        set_tracing_disabled(True)
        return None
    except Exception as exc:
        warn(f"otel: exporter creation failed - tracing disabled ({exc})")
        set_tracing_disabled(True)
        return None

    try:
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        provider.add_span_processor(BatchSpanProcessor(exporter))
        set_tracer_provider(provider)

        # Client + background instrumentation
        HTTPXClientInstrumentor().instrument()
        AioHttpClientInstrumentor().instrument()
        ThreadingInstrumentor().instrument()
        MCPInstrumentor().instrument()

        info(f"otel: tracing enabled service='{service_name}' exporter='{exporter_type}'")

        return provider

    except Exception as exc:
        warn(f"otel: initialization failed - tracing disabled ({exc})")
        set_tracing_disabled(True)
        return None


def instrument_fastapi_app(app: Any) -> None:
    """
    Instrument FastAPI so inbound requests create spans and propagate upstream context.
    """
    if not OTEL_AVAILABLE:
        return

    try:
        FastAPIInstrumentor.instrument_app(app)
        info("otel: FastAPI instrumentation enabled")
    except Exception as exc:
        warn(f"otel: FastAPI instrumentation failed ({exc})")


def probe_otlp_http(endpoint: str) -> None:
    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    tcp_probe(host, port)


def probe_otlp_grpc(endpoint: str) -> None:
    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or 4317
    tcp_probe(host, port)


def tcp_probe(host: str, port: int, timeout: float = 3.0) -> None:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as exc:
        raise OtelProbeError(f"TCP connect to {host}:{port} failed: {exc}") from exc