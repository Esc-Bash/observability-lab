"""Inventory service of the shop (final project, topic 20).

GET /stock/<product_id>   {"product_id": ..., "in_stock": N}
GET /health               returns OK

The stock lookup must finish within STOCK_SERVICE_TIMEOUT_MS (default 2000).
It takes about 40 ms for p-1003 and about 1 ms for the other products.
"""
import logging
import os
import time

from flask import Flask, jsonify

# Add the log handler to the root logger. No basicConfig: with OpenTelemetry automatic
# instrumentation the root logger may already have a handler, and then basicConfig does nothing.
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.getLogger().addHandler(_handler)
logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger("inventory")

TIMEOUT_MS = int(os.environ.get("STOCK_SERVICE_TIMEOUT_MS", "2000"))

STOCK = {"p-1001": 120, "p-1002": 75, "p-1003": 40, "p-1004": 12, "p-1005": 30}
LOOKUP_MS = {"p-1003": 40}  # the warehouse for p-1003 is slow to answer

app = Flask(__name__)


def lookup_stock(product_id):
    """Ask the warehouse for the stock. Returns None when the lookup times out."""
    took_ms = LOOKUP_MS.get(product_id, 1)
    if took_ms > TIMEOUT_MS:
        time.sleep(TIMEOUT_MS / 1000)
        return None
    time.sleep(took_ms / 1000)
    return STOCK[product_id]


@app.get("/stock/<product_id>")
def get_stock(product_id):
    if product_id not in STOCK:
        return jsonify({"error": "unknown product"}), 404
    in_stock = lookup_stock(product_id)
    if in_stock is None:
        log.error("stock lookup for %s timed out after %s ms", product_id, TIMEOUT_MS)
        return jsonify({"error": "stock lookup timed out"}), 500
    log.info("stock for %s is %s", product_id, in_stock)
    return jsonify({"product_id": product_id, "in_stock": in_stock})


@app.get("/health")
def health():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002, threaded=True)
