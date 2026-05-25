# Docker Best Practices Presentation

This directory contains the Reveal.js deck for Java/Spring Dockerfile decision-making and benchmarking.

## Open locally

```bash
cd /path/to/springdocker
python3 -m http.server 8000
```

Open:

- `http://localhost:8000/docs/presentation/index.html` — evidence-based decision deck
- `http://localhost:8000/docs/presentation/docker_optimizations_jug_revealjs_v3.html` — JUG talk (Docker + JVM, ~40 min)
- `http://localhost:8000/docs/presentation/pitch.html` — product pitch deck

## Files

- `index.html`: main slide deck (benchmark scenarios)
- `docker_optimizations_jug_revealjs_v3.html`: JUG conference deck (recommended)
- `docker_optimizations_jug_revealjs_v2.html`: earlier JUG draft (flat slides)
- `pitch.html`: springdocker product pitch
- `newPresentation_idea.html`: alternate Reveal.js deck
- `assets/custom.css`: styling for `index.html`
- `assets/jug-deck.css`: shared styling for JUG v3 deck

## Notes

- Reveal.js is loaded from CDN (no local npm setup required).