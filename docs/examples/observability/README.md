# Observability examples

springdocker does not generate app observability wiring. Stubs here:

- [`application.properties`](application.properties) — minimal Actuator/Micrometer setup
- [`service-monitor.yaml`](service-monitor.yaml) — Prometheus Operator scrape of the management port (`8081`)

Recommended stack: Micrometer → Prometheus → Grafana; OpenTelemetry when an OTLP backend exists. Keep benchmark analyze separate from live metrics.
