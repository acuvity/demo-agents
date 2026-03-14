"""File-based OpenTelemetry span exporter."""
import json
from typing import Sequence
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace import ReadableSpan


class FileSpanExporter(SpanExporter):
    """Exports OpenTelemetry spans to a JSONL file."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with open(self.file_path, "a", encoding="utf-8") as f:
            for span in spans:
                f.write(json.dumps(self._span_to_dict(span)) + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass

    def _span_to_dict(self, span: ReadableSpan) -> dict:
        return {
            "name": span.name,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "attributes": dict(span.attributes or {}),
            "status": span.status.status_code.name,
            "resource": dict(span.resource.attributes or {}),
        }
