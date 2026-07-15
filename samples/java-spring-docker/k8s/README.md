# Kubernetes sample (java-spring-docker)

Baseline manifests for the reference sample — springdocker does **not** generate Kubernetes YAML.

| File | Role |
|---|---|
| `deployment.yaml` | App + probes on management port |
| `service.yaml` | Service |
| `kustomization.yaml` | Kustomize entry |

```bash
kubectl apply -k samples/java-spring-docker/k8s
```

Assumptions: HTTP `8080`, management `8081`, readiness `/actuator/health/readiness`, liveness/startup `/actuator/health/liveness`, UID/GID `1001`, writable `/tmp` with read-only root FS.

Customize for non-actuator apps, different ports, or resource limits. Distroless images need these probes — there is no Dockerfile `HEALTHCHECK`.
