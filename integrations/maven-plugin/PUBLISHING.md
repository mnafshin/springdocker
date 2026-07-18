# Publishing springdocker-maven-plugin to Maven Central

Tracked by [#145](https://github.com/mnafshin/springdocker/issues/145).

## Coordinates

| Field | Value |
|---|---|
| GroupId | `io.github.mnafshin` |
| ArtifactId | `springdocker-maven-plugin` |
| Packaging | `maven-plugin` |

Versioning is **independent of the PyPI CLI** (plugin `1.3.x` vs CLI `1.2.x` is fine). Document the plugin version in release notes when cutting a GitHub Release.

## Prerequisites

1. Sonatype Central Portal account (or legacy OSSRH) with permission to publish `io.github.mnafshin`
2. GPG key for signing artifacts
3. `~/.m2/settings.xml` server credentials (see below)

## Local dry-run

```bash
cd integrations/maven-plugin
mvn -Pcentral-publish clean verify
# does not deploy; validates javadoc/source jars + GPG config presence when -DskipSigning=false
```

## Deploy (maintainers)

```bash
cd integrations/maven-plugin
mvn -Pcentral-publish clean deploy -DskipTests=false
```

After Central sync (often minutes to hours), consumers use a non-SNAPSHOT version:

```xml
<plugin>
  <groupId>io.github.mnafshin</groupId>
  <artifactId>springdocker-maven-plugin</artifactId>
  <version>1.3.0</version>
</plugin>
```

## settings.xml (example)

```xml
<settings>
  <servers>
    <server>
      <id>central</id>
      <username>${env.CENTRAL_USERNAME}</username>
      <password>${env.CENTRAL_TOKEN}</password>
    </server>
  </servers>
  <profiles>
    <profile>
      <id>gpg</id>
      <properties>
        <gpg.executable>gpg</gpg.executable>
      </properties>
    </profile>
  </profiles>
</settings>
```

## CI

A dedicated GitHub Actions workflow can call `mvn -Pcentral-publish deploy` on tagged releases of the plugin (not every CLI tag). Wire credentials via repository secrets; do not commit tokens.

Until the first Central release, install from this repository:

```bash
cd integrations/maven-plugin && mvn clean install
```
