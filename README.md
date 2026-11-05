# observability-lab

Lab files for the **Observability Fundamentals** course.

- `demo/` a small demo app, its load script and a sample exporter
- `app/` the sample shop: `frontend`, `orders`, `payment`, `inventory` (Python, Flask)
- `k8s/shop/` the shop on Kubernetes, `k8s/capstone/` the inventory service of the final project
- `k8s/monitoring/` Prometheus, Grafana, Alertmanager, Loki, Alloy, Jaeger and the OpenTelemetry Collector
- `scripts/` `shop-load.sh` sends checkouts, `break.sh` and `fix.sh` turn a fault on and off

The images are on `ghcr.io/esc-bash/`. The course tells you which file to use in each lesson.
