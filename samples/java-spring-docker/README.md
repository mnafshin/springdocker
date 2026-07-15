# java-spring-docker sample project

This sample Spring Boot 4 / **Java 25** project is the **reference evidence harness** for `springdocker` CLI workflows, benchmarks, and presentation numbers.

It is intentionally ahead of the CLI’s production default: when your service omits `java_version`, springdocker falls back to **Java 17**, and JEP 483 AOT requires **24+**. You do not need to match this sample’s JDK to adopt the CLI — set `java_version` in `.springdocker.toml` to your toolchain.

## Config-first team workflow

This directory includes an exemplar [`.springdocker.toml`](.springdocker.toml) (`production-balanced` profile with explicit `[dockerfile]` keys). Typical team flow:

```bash
cd samples/java-spring-docker
springdocker configure --project-root . --force    # optional: re-run wizard
springdocker dockerfile generate --project-root .
springdocker explain Dockerfile.generated --config-aware --format json
springdocker verify --project-root . --check-config-drift
```

Commit `.springdocker.toml` as strategy; commit or CI-regenerate `Dockerfile.generated` as the build artifact. Full guide: [docs/team-adoption.md](../../docs/team-adoption.md).

Legacy `tools/dockerfile_wizard.py` is retired — use `configure` + `dockerfile generate` instead ([tools/README.md](tools/README.md)).

## Build with Maven

```bash
cd /path/to/your-repo/samples/java-spring-docker
./mvnw -DskipTests package
./mvnw test
```

## Build with Gradle

```bash
cd /path/to/your-repo/samples/java-spring-docker
./gradlew build -x test
./gradlew test
```

## Benchmark docs

- `benchmarks/README.md`
- `benchmarks/common/README.md`
- `example-dockerfiles/recipes/` — versioned `springdocker` recipe preset output (regenerated with `springdocker benchmark generate`)
- `tools/README.md`

## Kubernetes sample

See `k8s/kustomization.yaml` for the sample Deployment/Service overlay used in the Kubernetes support docs.
