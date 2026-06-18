# java-spring-docker sample project

This sample Spring Boot 4 / Java 25 project is used to exercise `springdocker` CLI workflows.

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
- `example-dockerfiles/` — versioned `springdocker` output per benchmark scenario and recipe preset (regenerated with `springdocker benchmark generate`)
- `tools/README.md`

## Kubernetes sample

See `k8s/kustomization.yaml` for the sample Deployment/Service overlay used in the Kubernetes support docs.
