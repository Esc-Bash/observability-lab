# k8s/monitoring

The observability stack of the course, all in the namespace `monitoring`. Every folder
creates the namespace itself (`00-namespace.yaml`), so any of them can be applied first.
Everything is sized for a small lab machine (1 CPU, 6 GB): one replica, small requests,
data kept in the pod (`emptyDir`), so it is lost when a pod restarts.

| Path | What it creates | Image | Course |
|---|---|---|---|
| `prometheus/` | ConfigMap `prometheus-config` (`prometheus.yml`), Deployment + Service `prometheus` :9090 | `prom/prometheus:v3.4.1` (has `promtool`) | topic 08 |
| `node-exporter.yaml` | DaemonSet + Service `node-exporter` :9100 | `prom/node-exporter:v1.9.1` | topic 08 |
| `grafana/` | Deployment + Service `grafana` :3000, login `admin` / `admin`, no data sources | `grafana/grafana:11.6.3` | topic 10 |
| `alertmanager/` | ConfigMap `alertmanager-config` (`alertmanager.yml`, receiver that sends nothing), Deployment + Service `alertmanager` :9093, Deployment + Service `alert-receiver` :8080 | `prom/alertmanager:v0.25.0` (has `amtool`), `python:3.12.11-slim` | topic 11 |
| `loki/` | ConfigMap `loki-config`, Deployment + Service `loki` :3100 (OTLP at `/otlp`, structured metadata on) | `grafana/loki:3.5.1` | topic 13 |
| `alloy/` | ConfigMap `alloy-config`, RBAC, DaemonSet `alloy` (labels `namespace`, `pod`, `container`, `app`) | `grafana/alloy:v1.9.1` | topic 13 |
| `jaeger.yaml` | Deployment + Service `jaeger` :16686 (UI), :4317, :4318 (OTLP), in memory | `jaegertracing/all-in-one:1.70.0` | topic 15 |
| `otel-collector/` | ConfigMap `otel-collector-config` (`config.yaml`), Deployment + Service `otel-collector` :4317, :4318, :8889 | `otel/opentelemetry-collector-contrib:0.128.0` | topic 18 |

The learner applies them as the course says, for example:

```bash
cd /root/observability-shop
kubectl apply -f k8s/monitoring/prometheus/
kubectl -n monitoring rollout status deploy/prometheus
```

Prometheus, Alertmanager and the Collector read their config only at start: after
`kubectl apply` of a ConfigMap, run `kubectl -n monitoring rollout restart deployment/<name>`.
