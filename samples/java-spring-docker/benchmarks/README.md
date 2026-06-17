# Benchmark scenarios

Scenario directories under this folder are generated and run by `springdocker benchmark`.

## Regenerate locally

```bash
springdocker benchmark generate --project-root samples/java-spring-docker --java-version 25
```

Run benchmarks (native scaffold skipped by default):

```bash
springdocker benchmark run --project-root samples/java-spring-docker --profile quick
```

## What git tracks vs ignores

| Path | Policy | Why |
|---|---|---|
| `*/variants/**` | Generated — gitignored | Dockerfile variants are reproducible from `springdocker benchmark generate`. |
| `*/results/raw.csv` (except scenario 06) | Generated — gitignored | Run output; regenerate with `benchmark run`. |
| `07-native-benchmark/Dockerfile` | Generated — gitignored | Native scaffold output from the `native-aot` recipe. |
| `07-native-benchmark/README.md` | Generated — gitignored | Scaffold notice written by the generator. |
| `06-base-image-choice/results/raw.csv` | Versioned | Sample input for local analysis examples. |
| `06-base-image-choice/results/baseline.json` | Versioned | CI regression gate baseline. |
| `reference/v1/*` | Versioned | Published reference evidence snapshots. |

Do not commit generated variant Dockerfiles or local run CSVs. CI runs `benchmark generate` and asserts the benchmarks tree stays clean afterward.

See `docs/benchmark-methodology.md` for measurement details and `docs/native-image-roadmap.md` for native scaffold status.
