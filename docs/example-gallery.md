# Example gallery

> **NOT IMPLEMENTED YET**
>
> This page is roadmap content and does not describe currently shipped `springdocker` functionality.

This gallery collects representative generated outputs so you can see the main `springdocker` modes side by side.

## Dockerfile examples

| Example | File | What it shows |
|---|---|---|
| Baseline runtime | `docs/examples/baseline.Dockerfile` | A minimal single-stage runtime for comparison. |
| Jlink runtime | `docs/examples/jlink.Dockerfile` | A multi-stage build with a custom jlink runtime. |
| Layered build | `docs/examples/layered.Dockerfile` | A layered multi-stage build without jlink. |
| Distroless + jlink default | `docs/examples/distroless.Dockerfile` | `jvm-balanced` output: layered JAR, custom jlink runtime, distroless/base-debian13 non-root. |

## Benchmark report example

`docs/examples/benchmark-report.json` shows the JSON shape produced by `springdocker benchmark analyze --format json`.

## Notes

- The Dockerfile samples mirror the generator output used in tests and docs.
- The gallery is intentionally text-first so it stays versionable and easy to review.
