"""Orders API of the shop.

POST /orders        create an order, save it in postgres, charge it with payment
GET  /orders/<id>   read one order
GET  /health        returns OK

Runs as one process with the Flask built-in server on port 8000.
"""
import logging
import os

import psycopg2
import requests
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("orders")

PAYMENT_URL = os.environ.get("PAYMENT_URL", "http://payment:8001")
DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "shop")
DB_USER = os.environ.get("DB_USER", "shop")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "shop")
# scripts/break.sh slow-db sets SLOW_DB=1: the SELECT on the orders table then takes about 2 seconds.
DB_DELAY_SECONDS = 2.0 if os.environ.get("SLOW_DB") == "1" else 0.0

app = Flask(__name__)
_table_ready = False


def db():
    """Open a new connection to postgres and create the orders table the first time."""
    global _table_ready
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER,
                            password=DB_PASSWORD, connect_timeout=3)
    conn.autocommit = True
    if not _table_ready:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS orders ("
                " id SERIAL PRIMARY KEY,"
                " product_id TEXT NOT NULL,"
                " amount NUMERIC(10, 2) NOT NULL,"
                " status TEXT NOT NULL,"
                " created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
        _table_ready = True
    return conn


def save_order(product_id, amount):
    """Insert the order, then read it back. Returns the order as a dict."""
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (product_id, amount, status) VALUES (%s, %s, 'new') RETURNING id",
                (product_id, amount),
            )
            order_id = cur.fetchone()[0]
            cur.execute(
                "SELECT id, product_id, amount, status, pg_sleep(%s) FROM orders WHERE id = %s",
                (DB_DELAY_SECONDS, order_id),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return {"id": row[0], "product_id": row[1], "amount": float(row[2]), "status": row[3]}


def set_status(order_id, status):
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
    finally:
        conn.close()


def charge_payment(order_id, amount):
    """Ask the payment service to charge the order. Returns True when it is paid."""
    try:
        resp = requests.post(f"{PAYMENT_URL}/pay", json={"order_id": order_id, "amount": amount}, timeout=5)
    except requests.RequestException as err:
        log.error("payment failed for order %s: %s", order_id, err)
        return False
    if resp.status_code != 200:
        log.error("payment failed for order %s: status %s", order_id, resp.status_code)
        return False
    return True


@app.post("/orders")
def create_order():
    data = request.get_json(silent=True) or {}
    product_id = str(data.get("product_id", "p-1001"))
    amount = float(data.get("amount", 499.0))
    order = save_order(product_id, amount)
    if not charge_payment(order["id"], amount):
        set_status(order["id"], "payment_failed")
        return jsonify({"id": order["id"], "status": "payment_failed"}), 502
    set_status(order["id"], "paid")
    order["status"] = "paid"
    log.info("order %s created for %s, amount %.2f", order["id"], product_id, amount)
    return jsonify(order), 201


@app.get("/orders/<order_id>")
def get_order(order_id):
    if not order_id.isdigit():
        return jsonify({"error": "order not found"}), 404
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, product_id, amount, status FROM orders WHERE id = %s", (order_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return jsonify({"error": "order not found"}), 404
    return jsonify({"id": row[0], "product_id": row[1], "amount": float(row[2]), "status": row[3]})


@app.get("/health")
def health():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
