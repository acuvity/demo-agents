"""OpenTelemetry setup and instrumentation for the Google ADK agent."""

import logging

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.threading import (  # type: ignore[import-untyped]
    ThreadingInstrumentor,
)
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor  # type: ignore[import-untyped]  # pylint: disable=import-error,no-name-in-module
from openinference.instrumentation.mcp import MCPInstrumentor  # type: ignore[import-untyped]  # pylint: disable=import-error
from openinference.instrumentation.google_adk import GoogleADKInstrumentor  # type: ignore[import-untyped]  # pylint: disable=import-error
from openinference.instrumentation.litellm import LiteLLMInstrumentor  # type: ignore[import-untyped]  # pylint: disable=import-error

from config import AgentConfig
from observability.exporter import FileSpanExporter

logger = logging.getLogger(__name__)


def setup_otel(cfg: AgentConfig) -> TracerProvider:
    """Configure and return the OpenTelemetry TracerProvider based on cfg."""
    from opentelemetry.sdk.trace.export import (  # pylint: disable=import-outside-toplevel
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    existing = trace.get_tracer_provider()
    if isinstance(existing, TracerProvider):
        provider = existing
    else:
        underlying = getattr(existing, "_real_provider", None)
        if isinstance(underlying, TracerProvider):
            provider = underlying
        else:
            from opentelemetry.sdk.resources import Resource, SERVICE_NAME  # pylint: disable=import-outside-toplevel

            provider = TracerProvider(
                resource=Resource.create(
                    {SERVICE_NAME: cfg["otel"]["service_name"]}
                )
            )
            trace.set_tracer_provider(provider)

    if cfg["otel"]["enabled"]:
        if cfg["otel"]["console_export"]:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        if not cfg["otel"]["no_file_export"]:
            provider.add_span_processor(
                SimpleSpanProcessor(FileSpanExporter(file_path=cfg["otel"]["file"]))
            )

        otlp_endpoint: str | None = cfg["otel"]["otlp_endpoint"]
        send_spans: bool = cfg["otel"]["send_spans"]
        if otlp_endpoint and send_spans:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # pylint: disable=import-outside-toplevel,import-error,no-name-in-module
                OTLPSpanExporter,
            )

            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=cfg["otel"]["insecure"],
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(
                "OTLP exporter configured: endpoint=%s, insecure=%s",
                otlp_endpoint,
                cfg["otel"]["insecure"],
            )

    HTTPXClientInstrumentor().instrument()
    AioHttpClientInstrumentor().instrument()
    ThreadingInstrumentor().instrument()
    MCPInstrumentor().instrument()
    GoogleADKInstrumentor().instrument()
    LiteLLMInstrumentor().instrument()

    return provider
