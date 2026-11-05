"""Payment service of the shop.

POST /pay      charge an order: {"order_id": ..., "amount": ...}
GET  /health   returns OK
GET  /metrics  Prometheus metrics of this service

scripts/break.sh payment-errors sets PAYMENT_ERROR_RATE=0.3: about 30% of payments then fail with 500.
"""
import logging
import os
import random
import time

from flask import Flask, g, jsonify, request
from prometheus_client import Counter, Histogram, make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("payment")

ERROR_RATE = float(os.environ.get("PAYMENT_ERROR_RATE", "0"))

PAYMENTS = Counter("payment_requests_total", "Total payment requests handled", ["status"])
LATENCY = Histogram("payment_request_duration_seconds", "Time taken to handle one payment request")

app = Flask(__name__)


@app.before_request
def start_timer():
    g.start = time.time()


@app.after_request
def record_metrics(response):
    if request.path == "/pay":
        PAYMENTS.labels(str(response.status_code)).inc()
        LATENCY.observe(time.time() - g.start)
    return response


@app.post("/pay")
def pay():
    data = request.get_json(silent=True) or {}
    order_id = data.get("order_id")
    amount = data.get("amount", 0)
    time.sleep(random.uniform(0.01, 0.05))  # talking to the bank
    if random.random() < ERROR_RATE:
        log.error("payment for order %s failed: bank declined", order_id)
        return jsonify({"status": "failed", "error": "bank declined"}), 500
    log.info("payment for order %s accepted, amount %s", order_id, amount)
    return jsonify({"status": "paid", "order_id": order_id})


@app.get("/health")
def health():
    return "OK"


app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, threaded=True)
