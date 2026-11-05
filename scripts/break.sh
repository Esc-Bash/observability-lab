#!/usr/bin/env bash
# Create a problem in the shop on purpose.
# Usage: bash scripts/break.sh <slow-db|payment-errors>
#   slow-db         the database query in the orders API takes about 2 seconds
#   payment-errors  the payment service fails about 30% of requests with 500
# Remove it again with scripts/fix.sh <name>.
set -euo pipefail
case "${1:-}" in
  slow-db)
    kubectl -n shop set env deploy/orders SLOW_DB=1 >/dev/null
    kubectl -n shop rollout status deploy/orders --timeout=180s >/dev/null
    ;;
  payment-errors)
    kubectl -n shop set env deploy/payment PAYMENT_ERROR_RATE=0.3 >/dev/null
    kubectl -n shop rollout status deploy/payment --timeout=180s >/dev/null
    ;;
  *)
    echo "usage: break.sh <slow-db|payment-errors>" >&2
    exit 2
    ;;
esac
echo "problem '$1' is on. Remove it with: bash scripts/fix.sh $1"
