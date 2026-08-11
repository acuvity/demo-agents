"""OpenTelemetry setup and instrumentation for the simple-api agent."""

import json
import logging
import os
from collections.abc import Sequence

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.instrumentation.aiohttp_client import (  # type: ignore[import-untyped]  # pylint: disable=import-error,no-name-in-module
    AioHttpClientInstrumentor,
)
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.langchain import (  # type: ignore[import-untyped]
    LangchainInstrumentor,
)
from opentelemetry.instrumentation.threading import (  # type: ignore[import-untyped]
    ThreadingInstrumentor,
)
from openinference.instrumentation.mcp import MCPInstrumentor

logger = logging.getLogger(__name__)

SERVICE = os.environ.get("OTEL_SERVICE_NAME", "simple-api")


class FileSpanExporter(SpanExporter):
    """Export spans as JSONL to a file."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Write spans to file."""
        with open(self.file_path, "a", encoding="utf-8") as f:
            for span in spans:
                f.write(json.dumps({
                    "name": span.name,
                    "trace_id": format(span.context.trace_id, "032x") if span.context else None,
                    "span_id": format(span.context.span_id, "016x") if span.context else None,
                    "parent_id": format(span.parent.span_id, "016x") if span.parent else None,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "status": span.status.status_code.name,
                    "attributes": dict(span.attributes.items()) if span.attributes else {},
                }) + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


def setup_otel() -> TracerProvider:
    """Configure and return the OpenTelemetry TracerProvider."""
    span_file = os.environ.get("OTEL_SPAN_FILE")
    console_export = os.environ.get("OTEL_CONSOLE_EXPORT", "").lower() in ("1", "true")
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: SERVICE}))
    trace.set_tracer_provider(provider)

    if console_export:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("OTEL: console exporter enabled")

    if span_file:
        provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(span_file)))
        logger.info("OTEL: file exporter enabled: %s", span_file)

    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # pylint: disable=import-outside-toplevel,import-error,no-name-in-module
            OTLPSpanExporter,
        )
        insecure = os.environ.get("OTEL_INSECURE", "true").lower() in ("1", "true")
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=insecure,
        )))
        logger.info("OTEL: OTLP exporter enabled: %s", otlp_endpoint)

    HTTPXClientInstrumentor().instrument()
    AioHttpClientInstrumentor().instrument()
    ThreadingInstrumentor().instrument()
    MCPInstrumentor().instrument()
    LangchainInstrumentor().instrument()

    return provider
