#!/usr/bin/env bash
# Remove a problem created with scripts/break.sh.
# Usage: bash scripts/fix.sh <slow-db|payment-errors>
set -euo pipefail
case "${1:-}" in
  slow-db)
    kubectl -n shop set env deploy/orders SLOW_DB- >/dev/null
    kubectl -n shop rollout status deploy/orders --timeout=180s >/dev/null
    ;;
  payment-errors)
    kubectl -n shop set env deploy/payment PAYMENT_ERROR_RATE=0 >/dev/null
    kubectl -n shop rollout status deploy/payment --timeout=180s >/dev/null
    ;;
  *)
    echo "usage: fix.sh <slow-db|payment-errors>" >&2
    exit 2
    ;;
esac
echo "problem '$1' is removed."
