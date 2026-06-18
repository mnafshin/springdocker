# Presentation decks

Reveal.js slide decks for talks about **springdocker** (product/features) and **Dockerfile engineering** (step-by-step evidence).

## Open locally

```bash
cd /path/to/springdocker
python3 -m http.server 8000
```

Then open:

| Talk | File | Audience |
|---|---|---|
| **1 — springdocker features & workflow** | [`springdocker-features.html`](springdocker-features.html) | Teams evaluating the CLI: generate, explain, verify, plugins |
| **2 — why each step & what you gain** | [`docker-steps-evidence.html`](docker-steps-evidence.html) | Engineers choosing build/runtime/JVM options with benchmark evidence |

## Refresh benchmark numbers (automated)

Presentation decks use `data-benchmark="scenario/variant/metric"` bindings. After a benchmark run, update HTML and markdown in one step:

```bash
export DOCKER_BUILDKIT=1

springdocker benchmark generate --project-root samples/java-spring-docker --java-version 25
springdocker benchmark run --project-root samples/java-spring-docker --profile full

python scripts/update_presentation_benchmarks.py
```

This updates:

- `docker-steps-evidence.html` — scenario tables (values + `good`/`warn`/`risk` highlights), bar charts, cache stats

Benchmark scenario tables use a shared column layout when CSV data exists: **Variant · Image · Build avg · Startup avg · Startup p95**. Cells without measured startup data (e.g. failed runs) show `—`. Standalone bar charts remain on cross-cutting summary slides that have no table.
- `springdocker-features.html` — evidence bar charts in Talk 1
- `benchmark-summary.md` — paste-ready markdown tables (gitignored)

Use `--check` to verify deck benchmark values are current without writing files. The `benchmark-updated` HTML comment is refreshed only when values change, so timestamp-only drift does not fail the check.

Use `--profile full` for presentation-grade run counts (10 runs per scenario; 15 for scenario 04). Expect 1–3+ hours depending on host.

Scenario **07 (native)** is not measured by the runner (`--skip-native` by default). The deck binds the JVM comparison row to scenario **03** `without-jlink-runtime`; native-aot table and bar rows stay as published reference values (marked with `*`).

## Files

- `springdocker-features.html` — Talk 1 (features & workflow)
- `docker-steps-evidence.html` — Talk 2 (scenarios 01–08 with benefits)
- `benchmark-summary.md` — generated markdown summary (gitignored)
- `assets/evidence-deck.css` — shared styling for `docker-steps-evidence.html`

## Notes

- Reveal.js loads from CDN (no local npm setup required).
- Numbers are sample evidence from `samples/java-spring-docker/` — reproduce on your machine before citing absolutes in a live talk.
