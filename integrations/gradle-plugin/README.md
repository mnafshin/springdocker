# springdocker Gradle Plugin

Pure-Java twin of the [Maven builder plugin](../maven-plugin/README.md). **`build.gradle` / `build.gradle.kts` is SSOT** ([ADR 0010](../../docs/adr/0010-pom-gradle-ssot-java-builder.md)).

- No Python / `.springdocker.toml` required for generate/verify
- Same option subset as the Maven plugin
- Reuses `DockerfileRenderer` from the Maven module sources

## Apply

```kotlin
// settings.gradle.kts — until Plugin Portal publish, use includeBuild or mavenLocal
pluginManagement {
    includeBuild("../gradle-plugin") // from a sibling checkout layout, or publishToMavenLocal
}

plugins {
    id("io.github.mnafshin.springdocker") version "1.3.0-SNAPSHOT"
}

springdocker {
    javaVersion.set(21)
    runtimeImage.set("temurin")
    useJlink.set(false)
    useLayeredJar.set(true)
    nonRoot.set(true)
    recipe.set("jvm-balanced")
    output.set("Dockerfile.generated")
}
```

```bash
./gradlew springdockerGenerate
./gradlew springdockerVerify
```

## Develop

```bash
cd integrations/gradle-plugin
gradle test
# or: gradle build
```

Requires a local Gradle distribution (`gradle` on PATH) or the Gradle wrapper (not bundled here yet).
