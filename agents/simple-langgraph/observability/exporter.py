"""utils/exporter.py - File span exporter for OpenTelemetry."""

import json
from collections.abc import Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class FileSpanExporter(SpanExporter):
    """Export spans to a file."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with open(self.file_path, "a", encoding="utf-8") as span_file:
            for span in spans:
                span_file.write(json.dumps(self._span_to_dict(span)) + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def _span_to_dict(self, span: ReadableSpan) -> dict[str, object]:
        return {
            "name": span.name,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "attributes": (
                dict(span.attributes.items())
                if span.attributes is not None
                else {}
            ),
            "status": span.status.status_code.name,
            "resource": dict(span.resource.attributes),
        }
