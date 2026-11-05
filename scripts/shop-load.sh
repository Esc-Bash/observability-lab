#!/usr/bin/env bash
# Send N checkouts to the shop on http://127.0.0.1:8080 (the pf-frontend port-forward).
# Usage: bash scripts/shop-load.sh N
set -u
N="${1:-20}"
URL="${SHOP_URL:-http://127.0.0.1:8080}"
case "$N" in ''|*[!0-9]*) echo "usage: shop-load.sh N (a number)" >&2; exit 2 ;; esac
if ! curl -s --max-time 5 -o /dev/null "$URL/"; then
  echo "The shop does not answer on $URL. Is the port-forward pf-frontend running? (systemctl status pf-frontend)" >&2
  exit 1
fi
products=(p-1001 p-1002 p-1003 p-1004 p-1005)
ok=0; failed=0
for i in $(seq 1 "$N"); do
  p="${products[$((RANDOM % ${#products[@]}))]}"
  code=$(curl -s --max-time 20 -o /dev/null -w '%{http_code}' -X POST -d "product_id=$p" "$URL/checkout")
  if [ "$code" = "200" ]; then ok=$((ok + 1)); else failed=$((failed + 1)); fi
done
echo "sent $N checkouts: $ok OK, $failed failed"
