"""Frontend of the shop.

GET  /           product page with a checkout button
POST /checkout   places an order with the orders API (form, JSON or empty body)
GET  /health     returns OK
"""
import logging
import os

import requests
from flask import Flask, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("frontend")

ORDERS_URL = os.environ.get("ORDERS_URL", "http://orders:8000")
# Set only in the final project (topic 20): check stock before each checkout.
INVENTORY_URL = os.environ.get("INVENTORY_URL", "")

PRODUCTS = {
    "p-1001": ("Coffee mug", 349.0),
    "p-1002": ("Notebook", 199.0),
    "p-1003": ("Water bottle", 499.0),
    "p-1004": ("Backpack", 1899.0),
    "p-1005": ("Desk lamp", 1299.0),
}

app = Flask(__name__)

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Observability Shop</title>
<style>
body {{ font-family: sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: .6rem 0; display: flex;
        justify-content: space-between; align-items: center; }}
button {{ background: #0b6e4f; color: #fff; border: 0; border-radius: 6px; padding: .5rem 1rem; cursor: pointer; }}
.msg {{ padding: .8rem; border-radius: 6px; background: #eef7f1; }}
.err {{ background: #fdecea; }}
</style></head><body>
<h1>Observability Shop</h1>
{message}
{cards}
</body></html>"""


def page(message=""):
    cards = "".join(
        f'<form class="card" method="post" action="/checkout"><span><b>{name}</b> ({pid})<br>Rs {price:.2f}</span>'
        f'<input type="hidden" name="product_id" value="{pid}"><button type="submit">Checkout</button></form>'
        for pid, (name, price) in PRODUCTS.items()
    )
    return PAGE.format(message=message, cards=cards)


def check_stock(product_id):
    resp = requests.get(f"{INVENTORY_URL}/stock/{product_id}", timeout=5)
    resp.raise_for_status()
    return resp.json().get("in_stock", 0) > 0


@app.get("/")
def home():
    return page()


@app.post("/checkout")
def checkout():
    data = request.get_json(silent=True) or request.form or {}
    product_id = data.get("product_id") or "p-1001"
    if product_id not in PRODUCTS:
        product_id = "p-1001"
    name, amount = PRODUCTS[product_id]
    try:
        if INVENTORY_URL and not check_stock(product_id):
            return page('<p class="msg err">Sorry, this product is out of stock.</p>'), 409
        resp = requests.post(f"{ORDERS_URL}/orders", json={"product_id": product_id, "amount": amount}, timeout=10)
    except requests.RequestException as err:
        log.error("checkout failed for %s: %s", product_id, err)
        return page('<p class="msg err">Checkout failed. Please try again.</p>'), 502
    if resp.status_code != 201:
        log.error("checkout failed for %s: orders returned %s", product_id, resp.status_code)
        return page('<p class="msg err">Checkout failed. Please try again.</p>'), 502
    order = resp.json()
    return page(f'<p class="msg">Thank you! Order {order.get("id")} for {name} is confirmed.</p>')


@app.get("/health")
def health():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
