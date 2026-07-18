# springdocker Maven Plugin (Java builder)

Pure-Java **builder plugin**. **POM `<configuration>` is SSOT** ([ADR 0010](../../docs/adr/0010-pom-gradle-ssot-java-builder.md)).

- Does **not** require Python, `pipx`, or `uv`
- Does **not** read `.springdocker.toml` for generate/verify
- Benchmarks and advanced toolkit stay on the [Python CLI](../../cli/README.md)

## Configuration schema (v1)

| Parameter | Property | Type | Default | Effect |
|---|---|---|---|---|
| `javaVersion` | `springdocker.javaVersion` | int | `17` | JDK major used in build/runtime image tags (`>= 17`) |
| `runtimeImage` | `springdocker.runtimeImage` | enum | `distroless` | Runtime base: `distroless`, `debian-slim`, `alpine`, `ubuntu`, `temurin` |
| `useJlink` | `springdocker.useJlink` | boolean | `true` | Custom jlink runtime stage (ignored when `runtimeImage=temurin` fat JRE path may still apply) |
| `useLayeredJar` | `springdocker.useLayeredJar` | boolean | `true` | Spring Boot layered JAR extraction |
| `nonRoot` | `springdocker.nonRoot` | boolean | `true` | Run as non-root USER where the base supports it |
| `recipe` | `springdocker.recipe` | enum | `jvm-balanced` | `jvm-balanced` or `spring-aot` (`native-aot` is **CLI-only**) |
| `output` | `springdocker.output` | string | `Dockerfile.generated` | Output Dockerfile path relative to project basedir |
| `skip` | `springdocker.skip` | boolean | `false` | Skip Mojo execution |

### Explicitly out of plugin config

Benchmarks, configure wizard, full CLI profile matrix (`production-balanced`, …), digest-pin Renovate workflows, `setup --ci`. Use the Python CLI + `.springdocker.toml` for those.

### Mapping notes (plugin → Dockerfile behavior)

| Plugin option | Dockerfile behavior (subset parity with CLI) |
|---|---|
| `javaVersion` | Selects Temurin JDK/JRE major tags in build (and runtime when applicable) |
| `runtimeImage=distroless` | Distroless nonroot runtime; no Dockerfile `HEALTHCHECK` |
| `runtimeImage=temurin` | Eclipse Temurin JRE runtime; simplest path |
| `runtimeImage=debian-slim\|alpine\|ubuntu` | Slim OS runtime (+ optional jlink when `useJlink=true`) |
| `useJlink=true` | Multi-stage jlink custom JRE (when not using plain temurin fat runtime) |
| `useLayeredJar=true` | `layertools` extract + layered `COPY` |
| `recipe=spring-aot` | Enables Spring AOT processing flags in the build stage |
| `nonRoot=true` | `USER` non-root (or distroless nonroot image) |

**SSOT rule:** generate reads **only** these Mojo parameters / defaults. It never opens `.springdocker.toml`.

Canonical type: `io.github.mnafshin.springdocker.maven.PluginDockerfileOptions`.

## Example

```xml
<plugin>
  <groupId>io.github.mnafshin</groupId>
  <artifactId>springdocker-maven-plugin</artifactId>
  <version>1.3.0-SNAPSHOT</version>
  <configuration>
    <javaVersion>21</javaVersion>
    <runtimeImage>temurin</runtimeImage>
    <useJlink>false</useJlink>
    <useLayeredJar>true</useLayeredJar>
    <nonRoot>true</nonRoot>
    <recipe>jvm-balanced</recipe>
    <output>Dockerfile.generated</output>
  </configuration>
</plugin>
```

## Goals (roadmap)

| Goal | Status |
|---|---|
| `generate` | Implemented (pure Java; no Python) |
| `verify` | Implemented — fails on drift vs POM config |
| `export-config` | Implemented — optional one-way POM → `.springdocker.toml` |

```bash
mvn springdocker:generate
mvn springdocker:verify
mvn springdocker:export-config -Dspringdocker.force=true   # optional CLI bridge
```

Unlike the Python CLI (`verify --check-config-drift` against `.springdocker.toml`), this Mojo checks the Dockerfile against **plugin `<configuration>` only**.

### Optional toml export

`export-config` writes `.springdocker.toml` from plugin options so teams can later adopt the Python CLI. Re-export overwrites only with `-Dspringdocker.force=true`. Plugin configuration remains SSOT for the builder path.

## Develop

```bash
cd integrations/maven-plugin
mvn test
```

Maven Central publishing: see [PUBLISHING.md](PUBLISHING.md) ([#145](https://github.com/mnafshin/springdocker/issues/145)).
