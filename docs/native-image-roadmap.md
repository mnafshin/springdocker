# Native image roadmap

> **NOT IMPLEMENTED YET**
>
> This page is roadmap content and does not describe currently shipped `springdocker` functionality.

`springdocker` does not ship a native-image workflow yet, but the current benchmark structure leaves a clear path for it.

## Feasibility

- Treat native-image as an opt-in optimization strategy.
- Keep the JVM path as the default so the CLI stays predictable.

## Constraints

- GraalVM and native-image tooling must be available in the build environment.
- Reflection-heavy Spring Boot apps need explicit configuration.
- Native builds can be significantly slower than JVM builds.
- Native binaries are platform-specific, so benchmark comparisons must record the target architecture.

## Expected workflow

1. Detect a native-image profile or explicit flag.
2. Generate a native build variant alongside the JVM baseline.
3. Run the existing benchmark pipeline against both outputs.
4. Record startup, image size, and success-rate deltas.

## Benchmark integration

- Reuse the existing `07-native-benchmark` benchmark scenario as the comparison anchor.
- Capture both the native and JVM outputs in the same reporting format.
- Gate native adoption on measured startup and footprint improvements.

## Architectural notes

- Native support should be additive, not a replacement for the current Dockerfile generator.
- Keep the Dockerfile and benchmark layers independent so native experimentation stays isolated.
