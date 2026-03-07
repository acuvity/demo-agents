"""Observability package."""
from .exporter import FileSpanExporter
from .otel import setup_otel

__all__ = ["FileSpanExporter", "setup_otel"]
