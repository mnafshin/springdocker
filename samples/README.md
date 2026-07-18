# Reference sample (external)

The full Spring Boot benchmark harness lives in a dedicated repository:

**[`mnafshin/java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample)**

Check it out into this directory (gitignored) before docker-smoke / benchmark workflows:

```bash
python scripts/checkout_sample.py
# → samples/java-spring-docker/
```

Local layout tip: keep a sibling clone at `../java-spring-docker-sample` and the script will symlink it. Override with `JAVA_SPRING_DOCKER_SAMPLE_ROOT`.

Pinned revision: [`scripts/java_spring_docker_sample.manifest.json`](../scripts/java_spring_docker_sample.manifest.json).

Minimal CLI fixtures remain in-repo under `tests/fixtures/` — see [`docs/adr/0004-sample-project-strategy.md`](../docs/adr/0004-sample-project-strategy.md) and [`docs/adr/0009-external-sample-repository.md`](../docs/adr/0009-external-sample-repository.md).
