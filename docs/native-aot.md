# Native AOT (experimental scaffold)

> **Status: Experimental** — not a production native-image workflow.

- `springdocker dockerfile generate --recipe native-aot` writes a GraalVM-oriented Dockerfile scaffold
- Benchmark scenario `04-native-benchmark` uses that scaffold; the runner skips it by default (`--skip-native`)
- Reflection config, build validation, and measured native vs JVM comparisons are **not shipped**

Default path remains the JVM recipes (`jvm-balanced`, `spring-aot`). Track production native-image work in GitHub issues rather than this stub.
