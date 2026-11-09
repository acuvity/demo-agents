"""Minimal OpenTelemetry setup: export LiteLLM and httpx (A2A) spans over OTLP."""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
from opentelemetry.instrumentation.threading import ThreadingInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from openinference.instrumentation.litellm import LiteLLMInstrumentor


def setup_otel(service_name: str, otel_cfg: dict) -> None:
    """Configure tracing for one agent process if otel.enabled is set."""
    if not otel_cfg.get("enabled"):
        return

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=otel_cfg.get("otlp_endpoint", "http://127.0.0.1:14317"),
                insecure=otel_cfg.get("insecure", True),
            )
        )
    )
    
    trace.set_tracer_provider(provider)

    # httpx covers A2A calls (and propagates trace context between agents).
    HTTPXClientInstrumentor().instrument()
    AioHttpClientInstrumentor().instrument()
    # Threading keeps the trace context across worker threads (LiteLLM / ADK executor).
    ThreadingInstrumentor().instrument()
    GoogleADKInstrumentor().instrument()
    LiteLLMInstrumentor().instrument()



def instrument_app(app) -> None:
    """Server side: extract the caller's traceparent so agent spans join the CLI's trace."""
    StarletteInstrumentor.instrument_app(app)
