#!/usr/bin/env python3
"""Insert data-benchmark bindings into canonical presentation decks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

DECK_CUSTOMIZATIONS: dict[Path, list[tuple[str, str]]] = {
    REPO / "docs/presentation/docker-steps-evidence.html": [
        (
            "<title>Java Docker Decisions — Evidence from Benchmarks</title>",
            "<title>Docker Steps with Evidence — Why Each Choice Matters</title>",
        ),
        (
            "<h1 class=\"hero-title\">Java Docker<br><em>decisions</em> with evidence</h1>",
            "<h1 class=\"hero-title\">Docker steps<br><em>with evidence</em></h1>",
        ),
        (
            "How to choose build, runtime, and JVM options — and defend each choice with numbers",
            "Why each Dockerfile decision exists — and what you gain from scenarios 01–05",
        ),
        (
            "<p class=\"tiny\" style=\"margin-top: 1.2em;\">Press → · Speaker notes: <kbd>S</kbd></p>",
            "<p class=\"tiny\" style=\"margin-top: 1.2em;\">STEPS &amp; BENEFITS · Press → · Speaker notes: <kbd>S</kbd></p>",
        ),
        (
            '<div class="bar-row"><span class="label">without-jlink</span><div class="bar-wrap"><div class="bar bad" style="width:100%"></div></div><span class="val">144.38 MB</span></div>',
            '<div class="bar-row"><span class="label">without-jlink</span><div class="bar-wrap"><div class="bar bad" data-benchmark-bar="01-custom-jre-jlink/without-jlink-runtime/image_mb_avg" style="width:100%"></div></div><span class="val" data-benchmark="01-custom-jre-jlink/without-jlink-runtime/image_mb_avg">144.38 MB</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">with-jlink</span><div class="bar-wrap"><div class="bar" style="width:70%"></div></div><span class="val">100.40 MB</span></div>',
            '<div class="bar-row"><span class="label">with-jlink</span><div class="bar-wrap"><div class="bar" data-benchmark-bar="01-custom-jre-jlink/with-jlink-runtime/image_mb_avg" style="width:70%"></div></div><span class="val" data-benchmark="01-custom-jre-jlink/with-jlink-runtime/image_mb_avg">100.40 MB</span></div>',
        ),
        (
            '<tr><td>with-jlink</td><td class="good">1,423 ms</td></tr>',
            '<tr><td>with-jlink</td><td class="good"><span data-benchmark="01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms">1,423 ms</span></td></tr>',
        ),
        (
            '<tr><td>without-jlink</td><td>1,446 ms</td></tr>',
            '<tr><td>without-jlink</td><td><span data-benchmark="01-custom-jre-jlink/without-jlink-runtime/startup_avg_ms">1,446 ms</span></td></tr>',
        ),
        (
            '<tr><td>with-aot-cache</td><td class="good">1,429 ms</td><td class="good">1,462 ms</td></tr>',
            '<tr><td>with-aot-cache</td><td class="good"><span data-benchmark="02-jep483-aot-cache/with-aot-cache/startup_avg_ms">1,429 ms</span></td><td class="good"><span data-benchmark="02-jep483-aot-cache/with-aot-cache/startup_p95_ms">1,462 ms</span></td></tr>',
        ),
        (
            '<tr><td>without-aot-cache</td><td>1,509 ms</td><td class="risk">1,730 ms</td></tr>',
            '<tr><td>without-aot-cache</td><td><span data-benchmark="02-jep483-aot-cache/without-aot-cache/startup_avg_ms">1,509 ms</span></td><td class="risk"><span data-benchmark="02-jep483-aot-cache/without-aot-cache/startup_p95_ms">1,730 ms</span></td></tr>',
        ),
        (
            '<tr><td>alpine</td><td class="good">66.08 MB</td><td>2,153 ms</td><td>1,519 ms</td></tr>',
            '<tr><td>alpine</td><td class="good"><span data-benchmark="03-base-image-choice/alpine/image_mb_avg">66.08 MB</span></td><td><span data-benchmark="03-base-image-choice/alpine/build_avg_ms">2,153 ms</span></td><td><span data-benchmark="03-base-image-choice/alpine/startup_avg_ms">1,519 ms</span></td></tr>',
        ),
        (
            '<tr><td>debian-bookworm-slim</td><td>87.64 MB</td><td class="good">1,429 ms</td><td class="good">1,450 ms</td></tr>',
            '<tr><td>debian-bookworm-slim</td><td><span data-benchmark="03-base-image-choice/debian-slim/image_mb_avg">87.64 MB</span></td><td class="good"><span data-benchmark="03-base-image-choice/debian-slim/build_avg_ms">1,429 ms</span></td><td class="good"><span data-benchmark="03-base-image-choice/debian-slim/startup_avg_ms">1,450 ms</span></td></tr>',
        ),
        (
            '<tr><td>temurin-jre</td><td>131.37 MB</td><td class="good">945 ms</td><td>1,451 ms</td></tr>',
            '<tr><td>temurin-jre</td><td><span data-benchmark="03-base-image-choice/temurin/image_mb_avg">131.37 MB</span></td><td class="good"><span data-benchmark="03-base-image-choice/temurin/build_avg_ms">945 ms</span></td><td><span data-benchmark="03-base-image-choice/temurin/startup_avg_ms">1,451 ms</span></td></tr>',
        ),
        (
            '<tr><td>distroless-nonroot</td><td>205.1 MB*</td><td>—</td><td>—</td></tr>',
            '<tr><td>distroless-nonroot</td><td><span data-benchmark="03-base-image-choice/distroless/image_mb_avg">205.1 MB</span></td><td><span data-benchmark="03-base-image-choice/distroless/build_avg_ms">—</span></td><td><span data-benchmark="03-base-image-choice/distroless/startup_avg_ms">—</span></td></tr>',
        ),
        (
            '<div class="bar-row"><span class="label">JVM baseline</span><div class="bar-wrap"><div class="bar bad" style="width:100%"></div></div><span class="val">2,025 ms</span></div>',
            '<div class="bar-row"><span class="label">JVM baseline</span><div class="bar-wrap"><div class="bar bad" data-benchmark-bar="01-custom-jre-jlink/without-jlink-runtime/startup_avg_ms" style="width:100%"></div></div><span class="val" data-benchmark="01-custom-jre-jlink/without-jlink-runtime/startup_avg_ms">2,025 ms</span></div>',
        ),
        (
            '<tr><td>Without CDS archive</td><td>1,450 ms</td></tr>',
            '<tr><td>Without CDS archive</td><td><span data-benchmark="05-appcds/without-appcds/startup_avg_ms">1,450 ms</span></td></tr>',
        ),
        (
            '<tr><td>With AppCDS archive</td><td class="good">1,180 ms</td></tr>',
            '<tr><td>With AppCDS archive</td><td class="good"><span data-benchmark="05-appcds/with-appcds/startup_avg_ms">1,180 ms</span></td></tr>',
        ),
        (
            '<div class="bar-row"><span class="label">debian-slim</span><div class="bar-wrap"><div class="bar" style="width:61%"></div></div><span class="val">87.64 MB</span></div>',
            '<div class="bar-row"><span class="label">debian-slim</span><div class="bar-wrap"><div class="bar" data-benchmark-bar="03-base-image-choice/debian-slim/image_mb_avg" style="width:61%"></div></div><span class="val" data-benchmark="03-base-image-choice/debian-slim/image_mb_avg">87.64 MB</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">alpine + jlink</span><div class="bar-wrap"><div class="bar" style="width:46%"></div></div><span class="val">66.08 MB</span></div>',
            '<div class="bar-row"><span class="label">alpine + jlink</span><div class="bar-wrap"><div class="bar" data-benchmark-bar="03-base-image-choice/alpine/image_mb_avg" style="width:46%"></div></div><span class="val" data-benchmark="03-base-image-choice/alpine/image_mb_avg">66.08 MB</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">with-jlink</span><div class="bar-wrap"><div class="bar warn" style="width:70%"></div></div><span class="val">1,423 ms</span></div>',
            '<div class="bar-row"><span class="label">with-jlink</span><div class="bar-wrap"><div class="bar warn" data-benchmark-bar="01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms" style="width:70%"></div></div><span class="val" data-benchmark="01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms">1,423 ms</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">with AppCDS</span><div class="bar-wrap"><div class="bar" style="width:58%"></div></div><span class="val">1,180 ms</span></div>',
            '<div class="bar-row"><span class="label">with AppCDS</span><div class="bar-wrap"><div class="bar" data-benchmark-bar="05-appcds/with-appcds/startup_avg_ms" style="width:58%"></div></div><span class="val" data-benchmark="05-appcds/with-appcds/startup_avg_ms">1,180 ms</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">with-aot-cache</span><div class="bar-wrap"><div class="bar" style="width:71%"></div></div><span class="val">1,429 ms</span></div>',
            '<div class="bar-row"><span class="label">with-aot-cache</span><div class="bar-wrap"><div class="bar" data-benchmark-bar="02-jep483-aot-cache/with-aot-cache/startup_avg_ms" style="width:71%"></div></div><span class="val" data-benchmark="02-jep483-aot-cache/with-aot-cache/startup_avg_ms">1,429 ms</span></div>',
        )],
    REPO / "docs/presentation/springdocker-features.html": [
        (
            "<title>springdocker — Production Dockerfiles for Spring Boot, Without the Guesswork</title>",
            "<title>springdocker — Features &amp; Workflow</title>",
        ),
        (
            '<h1 class="hero-title">Stop <em>guessing</em>.<br/>Ship the Dockerfile<br/>your Spring Boot app <em>deserves</em>.</h1>',
            '<h1 class="hero-title">springdocker<br/><em>features</em> &amp; workflow</h1>',
        ),
        (
            "An opinionated, explainable, benchmark‑backed Dockerfile generator for the JVM.",
            "Generate, explain, and verify production Spring Boot Dockerfiles — without giving up ownership of the Dockerfile.",
        ),
        (
            '<div class="footer-note">PRESS → TO BEGIN</div>',
            '<div class="footer-note">FEATURES · PRESS →</div>',
        ),
        (
            '<div class="bar-row"><span class="label">without‑jlink</span><div class="bar-wrap"><div class="bar bad" style="width: 100%;"></div></div><span class="val">144.38 MB</span></div>',
            '<div class="bar-row"><span class="label">without‑jlink</span><div class="bar-wrap"><div class="bar bad" data-benchmark-bar="01-custom-jre-jlink/without-jlink-runtime/image_mb_avg" style="width: 100%;"></div></div><span class="val" data-benchmark="01-custom-jre-jlink/without-jlink-runtime/image_mb_avg">144.38 MB</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">temurin‑jre</span><div class="bar-wrap"><div class="bar warn" style="width: 91%;"></div></div><span class="val">131.37 MB</span></div>',
            '<div class="bar-row"><span class="label">temurin‑jre</span><div class="bar-wrap"><div class="bar warn" data-benchmark-bar="03-base-image-choice/temurin/image_mb_avg" style="width: 91%;"></div></div><span class="val" data-benchmark="03-base-image-choice/temurin/image_mb_avg">131.37 MB</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">with‑jlink</span><div class="bar-wrap"><div class="bar" style="width: 70%;"></div></div><span class="val">100.40 MB</span></div>',
            '<div class="bar-row"><span class="label">with‑jlink</span><div class="bar-wrap"><div class="bar" data-benchmark-bar="01-custom-jre-jlink/with-jlink-runtime/image_mb_avg" style="width: 70%;"></div></div><span class="val" data-benchmark="01-custom-jre-jlink/with-jlink-runtime/image_mb_avg">100.40 MB</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">debian‑bookworm‑slim</span><div class="bar-wrap"><div class="bar" style="width: 61%;"></div></div><span class="val">87.64 MB</span></div>',
            '<div class="bar-row"><span class="label">debian‑bookworm‑slim</span><div class="bar-wrap"><div class="bar" data-benchmark-bar="03-base-image-choice/debian-slim/image_mb_avg" style="width: 61%;"></div></div><span class="val" data-benchmark="03-base-image-choice/debian-slim/image_mb_avg">87.64 MB</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">alpine</span><div class="bar-wrap"><div class="bar" style="width: 46%;"></div></div><span class="val">66.08 MB</span></div>',
            '<div class="bar-row"><span class="label">alpine</span><div class="bar-wrap"><div class="bar" data-benchmark-bar="03-base-image-choice/alpine/image_mb_avg" style="width: 46%;"></div></div><span class="val" data-benchmark="03-base-image-choice/alpine/image_mb_avg">66.08 MB</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">JVM baseline</span><div class="bar-wrap"><div class="bar bad" style="width: 100%;"></div></div><span class="val">2,025 ms</span></div>',
            '<div class="bar-row"><span class="label">JVM baseline</span><div class="bar-wrap"><div class="bar bad" data-benchmark-bar="01-custom-jre-jlink/without-jlink-runtime/startup_avg_ms" style="width: 100%;"></div></div><span class="val" data-benchmark="01-custom-jre-jlink/without-jlink-runtime/startup_avg_ms">2,025 ms</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">debian‑bookworm‑slim</span><div class="bar-wrap"><div class="bar warn" style="width: 72%;"></div></div><span class="val">1,450 ms</span></div>',
            '<div class="bar-row"><span class="label">debian‑bookworm‑slim</span><div class="bar-wrap"><div class="bar warn" data-benchmark-bar="03-base-image-choice/debian-slim/startup_avg_ms" style="width: 72%;"></div></div><span class="val" data-benchmark="03-base-image-choice/debian-slim/startup_avg_ms">1,450 ms</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">with‑jlink</span><div class="bar-wrap"><div class="bar" style="width: 70%;"></div></div><span class="val">1,423 ms</span></div>',
            '<div class="bar-row"><span class="label">with‑jlink</span><div class="bar-wrap"><div class="bar" data-benchmark-bar="01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms" style="width: 70%;"></div></div><span class="val" data-benchmark="01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms">1,423 ms</span></div>',
        ),
        (
            '<div class="bar-row"><span class="label">with‑aot (avg)</span><div class="bar-wrap"><div class="bar" style="width: 71%;"></div></div><span class="val">1,429 ms</span></div>',
            '<div class="bar-row"><span class="label">with‑aot (avg)</span><div class="bar-wrap"><div class="bar" data-benchmark-bar="02-jep483-aot-cache/with-aot-cache/startup_avg_ms" style="width: 71%;"></div></div><span class="val" data-benchmark="02-jep483-aot-cache/with-aot-cache/startup_avg_ms">1,429 ms</span></div>',
        ),
    ],
}

def seed_deck(path: Path, replacements: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in replacements:
        if old not in text:
            raise ValueError(f"missing expected fragment in {path}: {old[:80]}...")
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")

def main() -> None:
    for path, replacements in DECK_CUSTOMIZATIONS.items():
        seed_deck(path, replacements)
        print(f"seeded bindings: {path}")

if __name__ == "__main__":
    main()
