"""Demo application for topic 03 (metrics, logs and traces).

Paths:
  /         returns OK
  /health   returns OK (not logged, not counted)
  /work     sometimes slow, fails with 500 about 10% of the time
  /metrics  Prometheus metrics

Every request to / or /work gets one trace_id and writes 2 or 3 JSON log lines with it.
"""
import json
import random
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, g, request
from prometheus_client import (
    Counter, Gauge, Histogram, make_wsgi_app, REGISTRY,
    GC_COLLECTOR, PLATFORM_COLLECTOR, PROCESS_COLLECTOR, disable_created_metrics,
)
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import logging

# Keep /metrics short: only the demo metrics.
disable_created_metrics()
for c in (GC_COLLECTOR, PLATFORM_COLLECTOR, PROCESS_COLLECTOR):
    REGISTRY.unregister(c)

# No werkzeug access lines: every log line is one JSON object with a trace_id.
logging.getLogger("werkzeug").setLevel(logging.ERROR)

REQUESTS = Counter("demo_http_requests_total", "Total number of HTTP requests.", ["path", "status"])
DURATION = Histogram("demo_http_request_duration_seconds", "Time taken to handle one request.", ["path"])
IN_PROGRESS = Gauge("demo_in_progress_requests", "Requests being handled right now.")

TRACKED = ("/", "/work")

app = Flask(__name__)


def log(level, message, **fields):
    line = {
        "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "level": level,
        "message": message,
    }
    line.update(fields)
    print(json.dumps(line), flush=True)


@app.before_request
def start():
    if request.path not in TRACKED:
        return
    g.start = time.time()
    g.trace_id = uuid.uuid4().hex
    IN_PROGRESS.inc()
    log("INFO", "request started", path=request.path, status=None, duration_ms=None, trace_id=g.trace_id)


@app.after_request
def finish(response):
    if request.path not in TRACKED or "start" not in g:
        return response
    ms = round((time.time() - g.start) * 1000, 1)
    status = response.status_code
    REQUESTS.labels(request.path, str(status)).inc()
    DURATION.labels(request.path).observe(ms / 1000)
    IN_PROGRESS.dec()
    if status >= 500:
        log("ERROR", "request failed", path=request.path, status=status, duration_ms=ms, trace_id=g.trace_id)
    else:
        log("INFO", "request finished", path=request.path, status=status, duration_ms=ms, trace_id=g.trace_id)
    return response


@app.get("/")
def home():
    return "OK\n"


@app.get("/health")
def health():
    return "OK"


@app.get("/work")
def work():
    # Most requests take 20-150 ms; about 1 in 10 is slow (0.5-1 s).
    delay = random.uniform(0.5, 1.0) if random.random() < 0.1 else random.uniform(0.02, 0.15)
    log("INFO", "doing work", path="/work", status=None, duration_ms=None, trace_id=g.trace_id)
    time.sleep(delay)
    if random.random() < 0.1:
        return "work failed\n", 500
    return "work done\n"


app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
