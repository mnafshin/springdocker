# Presentation decks

Reveal.js slide decks for **springdocker** (product/features) and **Dockerfile engineering** (step-by-step evidence).

These are **maintained project assets**, not throwaway session notes. They support the [secondary conference/evidence audience](../POSITIONING.md#target-audience) described in positioning docs — versioned alongside benchmark CSVs and sample-app evidence.

Policy: [#83](https://github.com/mnafshin/springdocker/issues/83) (ownership & cadence) · [#91](https://github.com/mnafshin/springdocker/issues/91) (commit vs publish).

## Ownership

| Question | Answer |
|---|---|
| **Who owns these files?** | Repository maintainers — same ownership model as `docs/` and the pinned [`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample) benchmarks. |
| **Who may edit?** | Anyone via pull request; reviewers check factual alignment with CLI behavior and benchmark methodology. |
| **Who publishes GitHub Pages?** | A repo admin, optionally — see [Publish policy](#commit-and-publish-policy) below. Not required for CLI users. |
| **Who refreshes benchmark numbers?** | Whoever changes benchmark scenarios or presents with current evidence — typically a maintainer before a talk or after a `--profile full` sample run. |

Slide **content** (wording, structure, new sections) and bound **numbers** (from `data-benchmark` CSVs) both go through normal git review. Do not fork decks outside the repo for “official” talks without merging improvements back.

## Update cadence

| Trigger | Action |
|---|---|
| **Before a conference or meetup talk** | Run `update_presentation_benchmarks.py --check`; refresh with `--profile full` if numbers are stale; commit HTML if bindings changed. |
| **After benchmark scenario or sample-app changes** | Regenerate bindings and commit updated `*.html` in the same PR when feasible. |
| **After CLI/product changes** (configure, verify, profiles, **Java feature matrix**) | Manually update narrative slides in `springdocker-features.html` and techniques/evidence decks; numbers may be unchanged. |
| **Routine maintenance** | No fixed schedule — refresh when presenting or when pinned CI baseline CSVs (`samples/.../results/`) change materially. |
| **Ephemeral helper output** | Regenerate `benchmark-summary.md` locally anytime; never commit (gitignored). |

Stale numbers are acceptable between talks if slides label evidence as sample-specific (see [Notes](#notes)). Before citing absolutes on stage, run a full-profile benchmark on your host or verify `--check` passes.

## Commit and publish policy

Resolved in [#91](https://github.com/mnafshin/springdocker/issues/91).

| Asset | Policy |
|---|---|
| `*.html`, `assets/*.css` | **Committed** — canonical, reviewable talk sources with `data-benchmark` bindings |
| `benchmark-summary.md` | **Gitignored** — local paste helper from `update_presentation_benchmarks.py` |
| Reveal.js / fonts | **CDN only** — not vendored in the repo; no npm build step |
| GitHub Pages | **Optional** — not CI-automated; enable manually if you want a public URL |
| PyPI / release artifacts | **Not included** — decks ship with the git repository, not the CLI package |

**Default:** keep HTML/CSS in the main repository. Talks, benchmark evidence, and presentation numbers stay versioned together; contributors open PRs when slide content or refreshed numbers change.

**Do not** move decks out of the repo or treat them as throwaway generated output — only `benchmark-summary.md` is ephemeral.

### Optional GitHub Pages

The repo includes [`docs/index.html`](../index.html), which redirects to `presentation/java-spring-docker-techniques.html`.

To publish (maintainer, one-time):

1. GitHub → **Settings** → **Pages**
2. **Build and deployment** → Source: **Deploy from a branch**
3. Branch: `main`, folder: **`/docs`**

Result: static hosting for both decks at paths under `/presentation/…`. Reveal.js still loads from the public CDN, so there is no build pipeline to maintain.

For local dry runs or conference Wi‑Fi, prefer `python3 -m http.server` (below) — no hosting setup required.

### What to commit after a benchmark refresh

```bash
python scripts/update_presentation_benchmarks.py
# commit only if HTML changed:
#   docs/presentation/springdocker-features.html
#   docs/presentation/docker-steps-evidence.html
```

Use `--check` in CI or pre-talk prep to detect stale numbers without writing files (see [Refresh benchmark numbers](#refresh-benchmark-numbers-automated)).

## Open locally

```bash
cd /path/to/springdocker
python3 -m http.server 8000
```

Then open:

| Deck | File | Audience |
|---|---|---|
| **Java/Spring Docker techniques** | [`java-spring-docker-techniques.html`](java-spring-docker-techniques.html) | JUG/meetup talks — Dockerfile craft; one impact slide with sample deltas; brief springdocker mention at the end |
| **Features & workflow** | [`springdocker-features.html`](springdocker-features.html) | Teams evaluating the CLI: configure, generate, explain, verify, plugins |
| **Docker steps & evidence** | [`docker-steps-evidence.html`](docker-steps-evidence.html) | Engineers choosing build/runtime/JVM options with benchmark evidence |

## Refresh benchmark numbers (automated)

Presentation decks use `data-benchmark="scenario/variant/metric"` bindings. After a benchmark run, update HTML and markdown in one step:

```bash
export DOCKER_BUILDKIT=1

python scripts/checkout_sample.py
springdocker benchmark generate --project-root samples/java-spring-docker --java-version 25
springdocker benchmark run --project-root samples/java-spring-docker --profile full

python scripts/update_presentation_benchmarks.py
```

This updates:

- `docker-steps-evidence.html` — scenario tables (values + `good`/`warn`/`risk` highlights), bar charts

Benchmark scenario tables use a shared column layout when CSV data exists: **Variant · Image · Build avg · Startup avg · Startup p95**. Cells without measured startup data (e.g. failed runs) show `—`. Standalone bar charts remain on cross-cutting summary slides that have no table.
- `springdocker-features.html` — evidence bar charts in the features deck
- `benchmark-summary.md` — paste-ready markdown tables (gitignored)

Use `--check` to verify deck benchmark values are current without writing files. The `benchmark-updated` HTML comment is refreshed only when values change, so timestamp-only drift does not fail the check.

Use `--profile full` for presentation-grade run counts (10 runs per scenario; 15 for scenario 02). Expect 1–3+ hours depending on host.

Scenario **04 (native)** is not measured by the runner (`--skip-native` by default). The deck binds the JVM comparison row to scenario **01** `without-jlink-runtime`; native-aot table and bar rows stay as published reference values (marked with `*`).

**Cross-cutting bar charts:** Both decks share the same **image-size** ladder (temurin → vendor JRE → jlink → distroless → alpine). Cold-start bars list startup levers across scenarios 01/02/05 — also independent levers, not one Dockerfile.

## Files

- `java-spring-docker-techniques.html` — **recommended for live talks**: multi-stage, layered JAR, jlink, AppCDS, security; wrap-up = impact → cost → bridges (drift → config/generate/verify) → short springdocker close
- `springdocker-features.html` — features & workflow (config-first CLI)
- `docker-steps-evidence.html` — scenarios 01–05 with benefits and **config key → Dockerfile** ON/OFF blocks per decision slide
- `benchmark-summary.md` — generated markdown summary (gitignored)
- `assets/evidence-deck.css` — shared styling for `docker-steps-evidence.html`

## Notes

- Reveal.js loads from CDN (no local npm setup required).
- Numbers are sample evidence from [`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample) (**Spring Boot 4 / Java 25**) — reproduce on your machine before citing absolutes in a live talk.
- **Product vs sample Java:** see [jvm.md](../jvm.md). Scenario index: [benchmarks.md](../benchmarks.md#scenario-index). Team rollout: [adopt.md](../adopt.md).
- After CLI Java-matrix or profile changes, update narrative slides (not only CSV bindings) — see cadence table above.
