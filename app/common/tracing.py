"""Small tracing helper for the shop (used by the :v-trace images, topics 14 and 15).

It is a thin wrapper around OpenTelemetry, which the course explains properly in topics 16-17.

    from common.tracing import setup_tracing, start_span

    app = Flask(__name__)
    setup_tracing(app, "orders")

    with start_span("INSERT orders") as span:
        span.set_attribute("db.system", "postgresql")
        ...

What setup_tracing does:
- creates one span for every request the service receives (for example "POST /orders").
  If the request has a traceparent header, the new span joins that trace (extract).
- sends the spans to Jaeger with OTLP over HTTP, as soon as Jaeger exists
  (TRACES_ENDPOINT, default http://jaeger.monitoring:4318). Every span is recorded (100% sampling),
  unless the caller's traceparent ends with -00.
- writes every log line as one JSON object with the fields time, level, message, service and
  traceparent (the traceparent of the span that is running when the line is written).

Code that calls another service creates a client span and adds the traceparent header (inject):

    from opentelemetry.propagate import inject

    with start_span("POST /pay", kind=SpanKind.CLIENT):
        headers = {}
        inject(headers)
        requests.post(url, json=body, headers=headers)
"""
import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone

from flask import g, request
from opentelemetry import context, propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

__all__ = ["setup_tracing", "start_span", "current_traceparent", "SpanKind"]

SERVICE_NAME = "unknown"
_tracer = trace.get_tracer("shop")
UNTRACED_PATHS = ("/health", "/metrics")


def current_traceparent():
    """The W3C traceparent of the span that is running now, or "" when there is none."""
    ctx = trace.get_current_span().get_span_context()
    if not ctx.is_valid:
        return ""
    return f"00-{ctx.trace_id:032x}-{ctx.span_id:016x}-{int(ctx.trace_flags):02x}"


class JsonFormatter(logging.Formatter):
    def format(self, record):
        line = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": SERVICE_NAME,
            "traceparent": current_traceparent(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            line["request_id"] = request_id
        if record.exc_info:
            line["error"] = self.formatException(record.exc_info)
        return json.dumps(line)


@contextmanager
def start_span(name, kind=SpanKind.INTERNAL):
    """Start a span for the code inside the with block. A span started inside another becomes its child."""
    with _tracer.start_as_current_span(name, kind=kind) as span:
        yield span


def setup_tracing(app, service_name):
    """Turn on tracing and JSON logging for a Flask app."""
    global SERVICE_NAME, _tracer
    SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", service_name)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    # The exporter complains on every batch while Jaeger is not installed yet. Keep the log clean.
    logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3").setLevel(logging.ERROR)

    endpoint = os.environ.get("TRACES_ENDPOINT", "http://jaeger.monitoring:4318").rstrip("/")
    provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))
    provider.add_span_processor(BatchSpanProcessor(
        OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", timeout=3),
        schedule_delay_millis=1000,
    ))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("shop")

    @app.before_request
    def _start_request_span():
        if request.path in UNTRACED_PATHS:
            return
        parent = propagate.extract({k.lower(): v for k, v in request.headers.items()})
        name = f"{request.method} {request.url_rule.rule if request.url_rule else request.path}"
        span = _tracer.start_span(name, context=parent, kind=SpanKind.SERVER)
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.target", request.path)
        g._otel_span = span
        g._otel_token = context.attach(trace.set_span_in_context(span))

    @app.after_request
    def _finish_request_span(response):
        span = g.get("_otel_span")
        if span is not None:
            span.set_attribute("http.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR))
        return response

    @app.teardown_request
    def _end_request_span(exc):
        span = g.pop("_otel_span", None)
        if span is None:
            return
        if exc is not None:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR))
        span.end()
        context.detach(g.pop("_otel_token"))
