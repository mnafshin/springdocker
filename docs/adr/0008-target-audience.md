# ADR 0008: Target audience

## Status

Accepted (closes [#87](https://github.com/mnafshin/springdocker/issues/87))

## Context

Review question [#87](https://github.com/mnafshin/springdocker/issues/87) asked whether springdocker is aimed at:

1. Personal research / lab tooling with bleeding-edge defaults
2. Conference / demo toolkit with rich sample assets
3. Production-oriented CLI with LTS-first defaults

That choice affects how Java 25 / Spring Boot 4 in the reference sample is interpreted, and how much
benchmark evidence belongs in the main repository.

## Decision

**Primary audience: teams adopting Spring Boot containerization in production.**

springdocker is a **production-oriented CLI** for Maven/Gradle services that need:

- a real, reviewable Dockerfile in git
- config-first strategy (`.springdocker.toml` SSOT)
- explain / verify workflows in local dev and CI
- generator support from **Java 17+** on the user's project (not tied to the reference sample versions)

**Secondary audience: conference storytelling and evidence-backed demos.**

The repository intentionally keeps presentations and pins a bleeding-edge reference
sample ([`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample) on Spring Boot 4 / Java 25). Those assets support talks and
reproducible evidence — they are **not** the product identity and **not** required for production
adoption.

**Not the primary audience: personal lab-only tooling.**

Research and stress-testing happen via the external sample (benchmark harness, pinned
CI baselines). Users install from PyPI and point the CLI at **their own** Spring Boot project; they
do not need to match Java 25 or Spring Boot 4.

### How this resolves Java version defaults

| Surface | Role |
|---|---|
| User's service + `springdocker init` / `configure` | Production path — **Java 17** floor; undetected fallback **17**; pick profile for **your** stack |
| Feature gates | AppCDS / jlink / layered JAR on **17+**; JEP 483 AOT hard-requires **24+**; `fast-cold-start` remaps to AppCDS on 17–23 |
| [`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample) | Reference / evidence anchor — Java **25** for stress-test + AOT scenario numbers |
| Presentations under `docs/presentation/` | Storytelling — sample evidence (often Java 25), not fleet guarantees |

Bleeding-edge versions in the sample are a **feature for evidence depth**, not a **liability** for
production users. LTS-first rollout is the default CLI path; the sample stays ahead of the curve for
benchmark and talk refresh.

## Consequences

- README and POSITIONING lead with production team adoption; benchmarks and decks are optional.
- PyPI-first distribution ([ADR 0006](0006-pypi-first-distribution.md)) aligns with the primary audience.
- Benchmark/presentation assets remain in the main repo ([ADR 0004](0004-sample-project-strategy.md),
  [#91](https://github.com/mnafshin/springdocker/issues/91)) as secondary-audience support.
- [#69](https://github.com/mnafshin/springdocker/issues/69) (Java 25 / Boot 4 as *user* defaults) is
  addressed by CLI fallback **17** and keeping Java 25 only on the evidence harness.

## References

- [docs/POSITIONING.md](../POSITIONING.md)
- [docs/adopt.md](../adopt.md)
- [#87 Define springdocker target audience](https://github.com/mnafshin/springdocker/issues/87)
