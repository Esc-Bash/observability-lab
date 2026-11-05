#!/usr/bin/env bash
# Send N requests to the demo application on http://127.0.0.1:8000, a mix of / and /work.
# Usage: bash load.sh N        or   curl -fsSL <raw>/demo/load.sh | bash -s -- N
set -u
N="${1:-50}"
URL="${DEMO_URL:-http://127.0.0.1:8000}"
case "$N" in ''|*[!0-9]*) echo "usage: load.sh N (a number)" >&2; exit 2 ;; esac
if ! curl -s --max-time 5 -o /dev/null "$URL/health"; then
  echo "The demo application does not answer on $URL. Is the port-forward demo-app-pf running?" >&2
  exit 1
fi
ok=0; failed=0
for i in $(seq 1 "$N"); do
  if [ $((i % 2)) -eq 0 ]; then path=/work; else path=/; fi
  code=$(curl -s --max-time 10 -o /dev/null -w '%{http_code}' "$URL$path")
  if [ "$code" = "200" ]; then ok=$((ok + 1)); else failed=$((failed + 1)); fi
done
echo "sent $N requests: $ok OK, $failed failed"
