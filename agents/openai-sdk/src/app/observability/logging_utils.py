from __future__ import annotations

import logging

from opentelemetry import trace


class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        ctx = span.get_span_context()

        if ctx and ctx.trace_id != 0:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        else:
            record.trace_id = "-"
            record.span_id = "-"

        return True


def configure_logging() -> None:
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"
        if not hasattr(record, "span_id"):
            record.span_id = "-"
        return record

    logging.setLogRecordFactory(record_factory)

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: trace_id=%(trace_id)s span_id=%(span_id)s %(message)s",
    )

    root_logger = logging.getLogger()
    root_logger.addFilter(TraceContextFilter())