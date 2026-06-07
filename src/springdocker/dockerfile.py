"""
Dockerfile generation and explain helpers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from jinja2 import Environment, PackageLoader, StrictUndefined

from springdocker.runtime_images import SUPPORTED_RUNTIME_IMAGES

TEMURIN_JDK_DIGESTS = {
    17: "sha256:b04a8c5d46e210873ffd1af6ad5f4d62c69ed3a6736993556eae60bba1373a23",
    21: "sha256:b9142586f9712700c6c9e07adcedfb18608b1a3a056e4001423a3354adfa9d80",
    25: "sha256:c2b7ea21649875fb9052237ac4e3cd4ef63968a2a389a0a1b1a72a5e53e5c93f",
}
TEMURIN_JRE_DIGESTS = {
    17: "sha256:0d79988c68791ce864fe39d149ab1dc84f680539dca77ee7f6f3b041ad7f2f43",
    21: "sha256:010e0a06bd4e0184dec58626afb3ba727b42c56c91b977e2f0a9e0837e0fa3fb",
    25: "sha256:04262e8782d6b034ee5d7c1c5d4e8938fcf2063a76b4bfcd84e5d994d09c27bc",
}
DISTROLESS_JAVA_DIGESTS = {
    17: "sha256:06484c2a9dcc9070aeafbc0fe752cb9f73bc0cea5c311f6a516e9010061998ad",
    21: "sha256:7e37784d94dccbf5ccb195c73b295f5ad00cd266512dfbac12eb9c3c28f8077d",
}
DISTROLESS_BASE_DIGESTS = {
    12: "sha256:7a75a36f4bec82a7542c64195e402907486f9a4dd2f8797a976aa0cf31cfb470",
}
DEBIAN_BOOKWORM_SLIM_DIGEST = "sha256:d5d3f9c23164ea16f31852f95bd5959aad1c5e854332fe00f7b3a20fcc9f635c"
OS_RUNTIME_IMAGES: dict[str, tuple[str, str | None]] = {
    "debian-slim": ("debian:bookworm-slim", DEBIAN_BOOKWORM_SLIM_DIGEST),
    "ubuntu": ("ubuntu:24.04", None),
    "alpine": ("alpine:3.21", None),
}


def _distroless_debian_release(java_version: int) -> str:
    return "debian13" if java_version >= 25 else "debian12"


def _distroless_java_image(java_version: int) -> str:
    return f"gcr.io/distroless/java{java_version}-{_distroless_debian_release(java_version)}:nonroot"


def _distroless_base_image(java_version: int) -> str:
    release = _distroless_debian_release(java_version)
    return f"gcr.io/distroless/base-{release}:nonroot"


@dataclass(frozen=True)
class BuildConfig:
    recipe: str
    use_buildkit_cache: bool
    use_jlink: bool
    use_layered_jar: bool
    enable_appcds: bool
    enable_jep483_aot_cache: bool
    must_have_modules: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeConfig:
    runtime_image: str
    platform_aware: bool
    non_root: bool
    tuned_jvm_flags: bool
    healthcheck_path: str | None


@dataclass(frozen=True)
class SupplyChainConfig:
    include_oci_labels: bool
    include_stopsignal: bool
    include_embedded_sbom: bool
    include_reproducible_controls: bool


@dataclass(frozen=True)
class DockerfileSpec:
    build_tool: str
    java_version: int
    build: BuildConfig
    runtime: RuntimeConfig
    supply_chain: SupplyChainConfig


@dataclass(frozen=True)
class DockerfileSection:
    lines: tuple[str, ...]


@dataclass(frozen=True)
class DockerfileDocument:
    sections: tuple[DockerfileSection, ...]

    def render(self) -> str:
        lines: list[str] = []
        for section in self.sections:
            lines.extend(section.lines)
        env = Environment(
            loader=PackageLoader("springdocker", "templates"),
            autoescape=False,
            trim_blocks=False,
            lstrip_blocks=False,
            keep_trailing_newline=False,
            undefined=StrictUndefined,
        )
        template = env.get_template("dockerfile.j2")
        return template.render(lines=lines)


@dataclass(frozen=True)
class DockerfileOptions:
    build_tool: str
    recipe: str = "jvm-balanced"
    java_version: int = 25
    use_buildkit_cache: bool = True
    use_jlink: bool = True
    non_root: bool = True
    tuned_jvm_flags: bool = True
    must_have_modules: tuple[str, ...] = ()
    runtime_image: str = "temurin"
    platform_aware: bool = True
    healthcheck_path: str | None = None
    include_oci_labels: bool = True
    include_stopsignal: bool = True
    include_embedded_sbom: bool = True
    include_reproducible_controls: bool = True
    use_layered_jar: bool = True
    enable_appcds: bool = True
    enable_jep483_aot_cache: bool = False

    def to_spec(self) -> DockerfileSpec:
        return DockerfileSpec(
            build_tool=self.build_tool,
            java_version=self.java_version,
            build=BuildConfig(
                recipe=self.recipe,
                use_buildkit_cache=self.use_buildkit_cache,
                use_jlink=self.use_jlink,
                use_layered_jar=self.use_layered_jar,
                enable_appcds=self.enable_appcds,
                enable_jep483_aot_cache=self.enable_jep483_aot_cache,
                must_have_modules=self.must_have_modules,
            ),
            runtime=RuntimeConfig(
                runtime_image=self.runtime_image,
                platform_aware=self.platform_aware,
                non_root=self.non_root,
                tuned_jvm_flags=self.tuned_jvm_flags,
                healthcheck_path=self.healthcheck_path,
            ),
            supply_chain=SupplyChainConfig(
                include_oci_labels=self.include_oci_labels,
                include_stopsignal=self.include_stopsignal,
                include_embedded_sbom=self.include_embedded_sbom,
                include_reproducible_controls=self.include_reproducible_controls,
            ),
        )


def _build_setup(build_tool: str, recipe: str) -> tuple[list[str], str, str]:
    if build_tool == "maven":
        build_cmd = "./mvnw -B -q package -DskipTests"
        if recipe == "spring-aot":
            build_cmd = "./mvnw -B -q -DskipTests package spring-boot:process-aot"
        elif recipe == "native-aot":
            build_cmd = "./mvnw -B -q -Pnative -DskipTests native:compile"
        return (
            [
                "COPY mvnw pom.xml ./",
                "COPY .mvn ./.mvn",
                "RUN chmod +x mvnw",
                "COPY src ./src",
            ],
            build_cmd,
            "target/*.jar" if recipe != "native-aot" else "target/*",
        )
    build_cmd = "./gradlew --no-daemon bootJar -x test"
    if recipe == "spring-aot":
        build_cmd = "./gradlew --no-daemon processAot bootJar -x test"
    elif recipe == "native-aot":
        build_cmd = "./gradlew --no-daemon nativeCompile -x test"
    return (
        [
            "COPY gradlew build.gradle settings.gradle ./",
            "COPY gradle ./gradle",
            "RUN chmod +x gradlew",
            "COPY src ./src",
        ],
        build_cmd,
        "build/libs/*-SNAPSHOT.jar" if recipe != "native-aot" else "build/native/nativeCompile/*",
    )


def _section(*lines: str) -> DockerfileSection:
    return DockerfileSection(lines=tuple(lines))


def _validate_options(options: DockerfileOptions) -> None:
    if options.build_tool not in {"maven", "gradle"}:
        raise ValueError("build tool must be 'maven' or 'gradle'")
    if options.java_version < 17:
        raise ValueError("java version must be >= 17")
    if options.runtime_image not in SUPPORTED_RUNTIME_IMAGES:
        supported = ", ".join(sorted(SUPPORTED_RUNTIME_IMAGES))
        raise ValueError(f"runtime_image must be one of: {supported}")
    if options.runtime_image in {"debian-slim", "ubuntu", "alpine"} and not options.use_jlink:
        raise ValueError(f"runtime_image '{options.runtime_image}' requires use_jlink=True")
    if options.recipe not in {"jvm-balanced", "spring-aot", "native-aot"}:
        raise ValueError("recipe must be one of: jvm-balanced, spring-aot, native-aot")
    if options.enable_jep483_aot_cache and options.java_version < 24:
        raise ValueError("JEP 483 AOT cache requires Java 24 or newer")
    if options.enable_jep483_aot_cache and not options.use_jlink:
        raise ValueError("JEP 483 AOT cache requires use_jlink=True")
    if options.enable_jep483_aot_cache and options.enable_appcds:
        raise ValueError("enable_jep483_aot_cache and enable_appcds are mutually exclusive")


def _pin_image(tag: str, digest: str | None) -> str:
    if digest is None:
        return tag
    return f"{tag}@{digest}"


def _jlink_build_base(spec: DockerfileSpec, default_build_base: str) -> str:
    """Use a musl-linked JDK for jlink when the runtime base is Alpine."""
    if spec.runtime.runtime_image == "alpine":
        return f"eclipse-temurin:{spec.java_version}-jdk-alpine"
    return default_build_base


def _os_runtime_user_setup(runtime_image: str) -> list[str]:
    if runtime_image == "alpine":
        return [
            "RUN apk add --no-cache shadow",
            "RUN addgroup -S -g 1001 javauser && adduser -S -u 1001 -G javauser -H -D javauser",
            "RUN install -d -o 1001 -g 1001 -m 755 /app && install -d -o 1001 -g 1001 -m 1777 /tmp",
        ]
    return [
        "RUN apt-get update && apt-get install -y --no-install-recommends passwd && rm -rf /var/lib/apt/lists/*",
        "RUN groupadd --system --gid 1001 javauser && useradd --system --uid 1001 --gid 1001 --no-create-home --shell /usr/sbin/nologin javauser",
        "RUN install -d -o 1001 -g 1001 -m 755 /app && install -d -o 1001 -g 1001 -m 1777 /tmp",
    ]


def _compose_os_runtime_section(
    spec: DockerfileSpec,
    jar_path: str,
    runtime_base: str,
) -> DockerfileSection:
    chown_flag = "--chown=1001:1001 " if spec.runtime.non_root else ""
    lines = [
        f"FROM --platform=$TARGETPLATFORM {runtime_base}",
        *_os_runtime_user_setup(spec.runtime.runtime_image),
        "WORKDIR /app",
        "VOLUME /tmp",
        "EXPOSE 8080",
        "EXPOSE 8081",
    ]
    if spec.build.use_layered_jar:
        lines.extend(
            [
                f"COPY --from=build {chown_flag}/layers/dependencies/ ./",
                f"COPY --from=build {chown_flag}/layers/spring-boot-loader/ ./",
                f"COPY --from=build {chown_flag}/layers/snapshot-dependencies/ ./",
                f"COPY --from=build {chown_flag}/layers/application/ ./",
            ]
        )
        if spec.build.enable_appcds:
            lines.append(f"COPY --from=build {chown_flag}/layers/app.jsa /app/app.jsa")
        if spec.build.enable_jep483_aot_cache:
            lines.append(f"COPY --from=aot-trainer {chown_flag}/app/app.aot /app/app.aot")
    else:
        lines.append(f"COPY --from=build {chown_flag}/app/{jar_path} app.jar")
    if spec.supply_chain.include_oci_labels:
        lines.extend(
            [
                'LABEL org.opencontainers.image.source="${OCI_SOURCE}" \\',
                '      org.opencontainers.image.revision="${OCI_REVISION}" \\',
                '      org.opencontainers.image.created="${OCI_CREATED}"',
            ]
        )
    if spec.runtime.healthcheck_path:
        lines.append(
            'HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 CMD wget -qO- "http://localhost:8080'
            + spec.runtime.healthcheck_path
            + '" >/dev/null || exit 1'
        )
    if spec.supply_chain.include_embedded_sbom:
        lines.append("COPY --from=build /tmp/sbom/spdx.json /usr/share/sbom/spdx.json")
    if spec.supply_chain.include_reproducible_controls:
        lines.append('ENV SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}"')
    lines.append("")
    return _section(*lines)


def _compose_dockerfile(spec: DockerfileSpec) -> DockerfileDocument:
    setup, build_cmd, jar_path = _build_setup(spec.build_tool, spec.build.recipe)
    build_step = (
        "RUN --mount=type=cache,sharing=locked,target=/root/.m2 " + build_cmd
        if spec.build.use_buildkit_cache and spec.build_tool == "maven"
        else "RUN --mount=type=cache,sharing=locked,target=/root/.gradle " + build_cmd
        if spec.build.use_buildkit_cache and spec.build_tool == "gradle"
        else f"RUN {build_cmd}"
    )

    jvm_args: list[str] = []
    if spec.runtime.tuned_jvm_flags:
        jvm_args.extend(
            [
                "-XX:MaxRAMPercentage=75",
                "-XX:+ExitOnOutOfMemoryError",
                "-Djava.io.tmpdir=/tmp",
            ]
        )

    header_lines = [
        "# syntax=docker/dockerfile:1",
        "# Generated by springdocker",
        f"# Java {spec.java_version} | build-tool: {spec.build_tool}",
    ]
    if spec.build.recipe != "jvm-balanced":
        header_lines.append(f"# recipe: {spec.build.recipe}")
    header_lines.append("")
    sections: list[DockerfileSection] = [_section(*header_lines)]
    if spec.runtime.platform_aware:
        sections.append(_section("ARG TARGETPLATFORM", "ARG BUILDPLATFORM", ""))
    if spec.supply_chain.include_reproducible_controls:
        sections.append(_section("ARG SOURCE_DATE_EPOCH=0", ""))
    if spec.supply_chain.include_oci_labels:
        sections.append(_section('ARG OCI_SOURCE=""', 'ARG OCI_REVISION=""', 'ARG OCI_CREATED=""', ""))
    build_base = _pin_image(f"eclipse-temurin:{spec.java_version}-jdk", TEMURIN_JDK_DIGESTS.get(spec.java_version))
    if spec.build.recipe == "native-aot":
        build_base = f"ghcr.io/graalvm/native-image-community:{spec.java_version}"
    sections.append(
        _section(
            f"FROM --platform=$BUILDPLATFORM {build_base} AS build",
            "WORKDIR /app",
            *setup,
            build_step,
            f"RUN java -Djarmode=layertools -jar /app/{jar_path} extract --destination /layers"
            if spec.build.use_layered_jar
            else "",
            (
                "RUN cd /layers && "
                "java -XX:ArchiveClassesAtExit=/layers/app.jsa -Dspring.context.exit=onRefresh "
                "org.springframework.boot.loader.launch.JarLauncher || true"
            )
            if spec.build.use_layered_jar and spec.build.enable_appcds
            else "",
            (
                "RUN install -d /tmp/sbom && "
                "printf '{\"spdxVersion\":\"SPDX-2.3\",\"name\":\"springdocker-generated-image\"}' > /tmp/sbom/spdx.json"
            )
            if spec.supply_chain.include_embedded_sbom
            else "",
            "",
        )
    )

    if spec.build.recipe == "native-aot":
        native_runtime_lines = [
            f"FROM --platform=$TARGETPLATFORM {_pin_image('gcr.io/distroless/base-debian12:nonroot', DISTROLESS_BASE_DIGESTS.get(12))}",
            "WORKDIR /app",
            "COPY --from=build /app/" + jar_path + " /app/app",
        ]
        if spec.supply_chain.include_oci_labels:
            native_runtime_lines.extend(
                [
                    'LABEL org.opencontainers.image.source="${OCI_SOURCE}" \\',
                    '      org.opencontainers.image.revision="${OCI_REVISION}" \\',
                    '      org.opencontainers.image.created="${OCI_CREATED}"',
                ]
            )
        if spec.supply_chain.include_embedded_sbom:
            native_runtime_lines.append("COPY --from=build /tmp/sbom/spdx.json /usr/share/sbom/spdx.json")
        if spec.supply_chain.include_reproducible_controls:
            native_runtime_lines.append('ENV SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}"')
        if spec.supply_chain.include_stopsignal:
            native_runtime_lines.append("STOPSIGNAL SIGTERM")
        native_runtime_lines.append('ENTRYPOINT ["/app/app"]')
        native_runtime_lines.append("")
        sections.append(_section(*native_runtime_lines))
        return DockerfileDocument(sections=tuple(sections))

    if spec.build.use_jlink:
        # Ensure common modules required by frameworks (e.g., java.beans, java.logging, java.naming) are present
        must_have = list(spec.build.must_have_modules)
        for _m in ("java.desktop", "java.logging", "java.naming"):
            if _m not in must_have:
                must_have.append(_m)
        must_have_csv = ",".join(must_have).replace('"', '\\"')
        jre_build_base = _jlink_build_base(spec, build_base)
        sections.append(
            _section(
                f"FROM --platform=$BUILDPLATFORM {jre_build_base} AS jre-builder",
                "WORKDIR /jre",
                f"COPY --from=build /app/{jar_path} app.jar",
                (
                    f"RUN jdeps --ignore-missing-deps --recursive --multi-release {spec.java_version} "
                    "--print-module-deps app.jar > modules.txt"
                ),
                f'ARG MUSTHAVE_MODULES="{must_have_csv}"',
                "RUN set -eux; \\",
                "    MODULES=$( (tr ',' '\\n' < modules.txt; printf '%s\\n' \"$MUSTHAVE_MODULES\" | tr ',' '\\n') \\",
                "      | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$' | sort -u | paste -sd, -); \\",
                "    jlink --add-modules \"$MODULES\" --strip-debug --no-man-pages --no-header-files --compress=2 --output /jre/out",
                "",
            )
        )

    runtime_base = _pin_image(
        f"eclipse-temurin:{spec.java_version}-jre",
        TEMURIN_JRE_DIGESTS.get(spec.java_version),
    )
    if spec.build.use_jlink and spec.build.enable_jep483_aot_cache:
        sections.append(
            _section(
                f"FROM --platform=$TARGETPLATFORM {runtime_base} AS aot-trainer",
                "COPY --from=jre-builder /jre/out /opt/java",
                "ENV JAVA_HOME=/opt/java",
                'ENV PATH="${JAVA_HOME}/bin:${PATH}"',
                "WORKDIR /app",
                "COPY --from=build /layers/dependencies/ ./",
                "COPY --from=build /layers/spring-boot-loader/ ./",
                "COPY --from=build /layers/snapshot-dependencies/ ./",
                "COPY --from=build /layers/application/ ./",
                (
                    "RUN java -XX:AOTCacheOutput=/app/app.aot -Dspring.context.exit=onRefresh "
                    "org.springframework.boot.loader.launch.JarLauncher; \\"
                ),
                "    test -f /app/app.aot",
                "",
            )
        )

    if spec.runtime.runtime_image == "distroless":
        debian_release = _distroless_debian_release(spec.java_version)
        distroless_base_digest = DISTROLESS_BASE_DIGESTS.get(12) if debian_release == "debian12" else None
        runtime_base = (
            _pin_image(
                _distroless_base_image(spec.java_version),
                distroless_base_digest,
            )
            if spec.build.use_jlink
            else _pin_image(
                _distroless_java_image(spec.java_version),
                DISTROLESS_JAVA_DIGESTS.get(spec.java_version),
            )
        )
        distroless_lines = [
            f"FROM --platform=$TARGETPLATFORM {runtime_base}",
            "WORKDIR /app",
            "VOLUME /tmp",
            "EXPOSE 8080",
            "EXPOSE 8081",
        ]
        if spec.build.use_layered_jar:
            distroless_lines.extend(
                [
                    "COPY --from=build /layers/dependencies/ ./",
                    "COPY --from=build /layers/spring-boot-loader/ ./",
                    "COPY --from=build /layers/snapshot-dependencies/ ./",
                    "COPY --from=build /layers/application/ ./",
                ]
            )
            if spec.build.enable_appcds:
                distroless_lines.append("COPY --from=build /layers/app.jsa /app/app.jsa")
        else:
            distroless_lines.append(f"COPY --from=build /app/{jar_path} app.jar")
        if spec.supply_chain.include_oci_labels:
            distroless_lines.extend(
                [
                    'LABEL org.opencontainers.image.source="${OCI_SOURCE}" \\',
                    '      org.opencontainers.image.revision="${OCI_REVISION}" \\',
                    '      org.opencontainers.image.created="${OCI_CREATED}"',
                ]
            )
        if spec.build.use_jlink:
            distroless_lines.extend(
                [
                    "COPY --from=jre-builder /jre/out /opt/java",
                    "ENV JAVA_HOME=/opt/java",
                    'ENV PATH="${JAVA_HOME}/bin:${PATH}"',
                ]
            )
        if spec.runtime.non_root:
            distroless_lines.append("USER nonroot")
        if spec.supply_chain.include_embedded_sbom:
            distroless_lines.append("COPY --from=build /tmp/sbom/spdx.json /usr/share/sbom/spdx.json")
        if spec.supply_chain.include_reproducible_controls:
            distroless_lines.append('ENV SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}"')
        sections.append(_section(*distroless_lines))
    elif spec.runtime.runtime_image in OS_RUNTIME_IMAGES:
        tag, digest = OS_RUNTIME_IMAGES[spec.runtime.runtime_image]
        sections.append(_compose_os_runtime_section(spec, jar_path, _pin_image(tag, digest)))
    else:
        temurin_lines = [f"FROM --platform=$TARGETPLATFORM {runtime_base}"]
        if spec.runtime.non_root:
            temurin_lines.extend(
                [
                    "RUN groupadd --system --gid 1001 javauser && useradd --system --uid 1001 --gid 1001 --no-create-home --shell /usr/sbin/nologin javauser",
                    "RUN install -d -o 1001 -g 1001 -m 755 /app && install -d -o 1001 -g 1001 -m 1777 /tmp",
                ]
            )
        else:
            temurin_lines.append("RUN install -d -m 755 /app && install -d -m 1777 /tmp")

        temurin_lines.extend(
            [
                "WORKDIR /app",
                "VOLUME /tmp",
                "EXPOSE 8080",
                "EXPOSE 8081",
            ]
        )
        if spec.build.use_layered_jar:
            chown_flag = "--chown=1001:1001 " if spec.runtime.non_root else ""
            temurin_lines.extend(
                [
                    f"COPY --from=build {chown_flag}/layers/dependencies/ ./",
                    f"COPY --from=build {chown_flag}/layers/spring-boot-loader/ ./",
                    f"COPY --from=build {chown_flag}/layers/snapshot-dependencies/ ./",
                    f"COPY --from=build {chown_flag}/layers/application/ ./",
                ]
            )
            if spec.build.enable_appcds:
                temurin_lines.append(f"COPY --from=build {chown_flag}/layers/app.jsa /app/app.jsa")
            if spec.build.enable_jep483_aot_cache:
                temurin_lines.append(f"COPY --from=aot-trainer {chown_flag}/app/app.aot /app/app.aot")
        else:
            temurin_lines.append(f"COPY --from=build {'--chown=1001:1001 ' if spec.runtime.non_root else ''}/app/{jar_path} app.jar")
        if spec.supply_chain.include_oci_labels:
            temurin_lines.extend(
                [
                    'LABEL org.opencontainers.image.source="${OCI_SOURCE}" \\',
                    '      org.opencontainers.image.revision="${OCI_REVISION}" \\',
                    '      org.opencontainers.image.created="${OCI_CREATED}"',
                ]
            )
        if spec.runtime.healthcheck_path:
            temurin_lines.append(
                'HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 CMD wget -qO- "http://localhost:8080'
                + spec.runtime.healthcheck_path
                + '" >/dev/null || exit 1'
            )
        if spec.supply_chain.include_embedded_sbom:
            temurin_lines.append("COPY --from=build /tmp/sbom/spdx.json /usr/share/sbom/spdx.json")
        if spec.supply_chain.include_reproducible_controls:
            temurin_lines.append('ENV SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}"')
        sections.append(_section(*temurin_lines))

    if spec.build.use_jlink and spec.runtime.runtime_image != "distroless":
        sections.append(
            _section(
                "COPY --from=jre-builder /jre/out /opt/java",
                "ENV JAVA_HOME=/opt/java",
                'ENV PATH="${JAVA_HOME}/bin:${PATH}"',
            )
        )

    if spec.build.use_layered_jar and spec.build.enable_appcds:
        jvm_args.append("-XX:SharedArchiveFile=/app/app.jsa")
    if spec.build.enable_jep483_aot_cache:
        jvm_args.append("-XX:AOTCache=/app/app.aot")
    entrypoint = (
        ["java", *jvm_args, "org.springframework.boot.loader.launch.JarLauncher"]
        if spec.build.use_layered_jar
        else ["java", *jvm_args, "-jar", "app.jar"]
    )
    tail_lines: list[str] = []
    if spec.runtime.non_root and spec.runtime.runtime_image != "distroless":
        tail_lines.append("USER 1001")
    if spec.supply_chain.include_stopsignal:
        tail_lines.append("STOPSIGNAL SIGTERM")
    tail_lines.append("ENTRYPOINT [" + ", ".join(f'"{arg}"' for arg in entrypoint) + "]")
    tail_lines.append(
        "# Runtime hardening tip: run with --read-only --cap-drop=ALL --security-opt=no-new-privileges --tmpfs /tmp"
    )
    tail_lines.append("")
    sections.append(_section(*tail_lines))
    return DockerfileDocument(sections=tuple(sections))


def build_dockerfile(options: DockerfileOptions) -> str:
    _validate_options(options)
    return _compose_dockerfile(options.to_spec()).render()


def explain_dockerfile_text(text: str) -> dict[str, object]:
    lines = text.splitlines()
    header_match = re.search(r"# Java (\d+) \| build-tool: (maven|gradle)", text)
    java_version = int(header_match.group(1)) if header_match else None
    build_tool = header_match.group(2) if header_match else None
    if java_version is None:
        image_match = re.search(r"(?im)^\s*FROM\s+[^:\s]+:(\d+)", text)
        if image_match:
            java_version = int(image_match.group(1))
    if build_tool is None:
        lowered = text.lower()
        if "mvnw" in lowered or "maven" in lowered:
            build_tool = "maven"
        elif "gradlew" in lowered or "gradle" in lowered:
            build_tool = "gradle"

    features: list[dict[str, object]] = []
    if sum(1 for line in lines if line.strip().upper().startswith("FROM ")) >= 2:
        features.append(
            {
                "name": "multi-stage build",
                "enabled": True,
                "reason": "Separates the build stage from the runtime stage.",
            }
        )
    if "jdeps" in text and "jlink" in text:
        features.append(
            {
                "name": "jlink runtime",
                "enabled": True,
                "reason": "Builds a smaller custom runtime from the detected module list.",
            }
        )
    if "--mount=type=cache" in text:
        features.append(
            {
                "name": "BuildKit cache",
                "enabled": True,
                "reason": "Caches Maven or Gradle dependencies between builds.",
            }
        )
    if "TARGETPLATFORM" in text and "BUILDPLATFORM" in text:
        features.append(
            {
                "name": "multi-architecture build",
                "enabled": True,
                "reason": "Uses Buildx platform arguments for arm64 and amd64 builds.",
            }
        )
    if "gcr.io/distroless" in text:
        features.append(
            {
                "name": "distroless runtime",
                "enabled": True,
                "reason": "Uses a minimal distroless runtime image.",
            }
        )
    if "debian:bookworm-slim" in text:
        features.append(
            {
                "name": "debian-slim runtime",
                "enabled": True,
                "reason": "Uses a Debian bookworm-slim runtime base image.",
            }
        )
    if re.search(r"(?m)^FROM\s+ubuntu:", text):
        features.append(
            {
                "name": "ubuntu runtime",
                "enabled": True,
                "reason": "Uses an Ubuntu runtime base image.",
            }
        )
    if re.search(r"(?m)^FROM\s+alpine:", text):
        features.append(
            {
                "name": "alpine runtime",
                "enabled": True,
                "reason": "Uses an Alpine runtime base image.",
            }
        )
    if "VOLUME /tmp" in text:
        features.append(
            {
                "name": "read-only filesystem ready",
                "enabled": True,
                "reason": "Keeps /tmp writable when the container root filesystem is read-only.",
            }
        )
    if "USER 1001" in text or "USER nonroot" in text or "gcr.io/distroless" in text:
        features.append(
            {
                "name": "non-root runtime",
                "enabled": True,
                "reason": "Runs the application as an unprivileged container user.",
            }
        )
    if "-XX:MaxRAMPercentage=75" in text:
        features.append(
            {
                "name": "tuned JVM flags",
                "enabled": True,
                "reason": "Applies container-friendly JVM memory and failure defaults.",
            }
        )
    if "jarmode=layertools" in text and "/layers/application/" in text:
        features.append(
            {
                "name": "layered jar",
                "enabled": True,
                "reason": "Extracts Spring Boot layers for better image cache reuse.",
            }
        )

    must_have_match = re.search(r'ARG MUSTHAVE_MODULES="([^"]*)"', text)
    must_have_modules = tuple(
        module for module in (part.strip() for part in (must_have_match.group(1) if must_have_match else "").split(",")) if module
    )
    if must_have_modules:
        features.append(
            {
                "name": "must-have modules",
                "enabled": True,
                "reason": "Includes manually curated modules that jdeps cannot infer reliably.",
            }
        )

    summary_parts = []
    if build_tool and java_version is not None:
        summary_parts.append(f"This {build_tool} Dockerfile targets Java {java_version}.")
    if any(feature["name"] == "multi-stage build" for feature in features):
        summary_parts.append("It uses a multi-stage build to keep the runtime image separate from compilation.")
    if any(feature["name"] == "jlink runtime" for feature in features):
        summary_parts.append("It builds a custom runtime with jlink.")
    if any(feature["name"] == "non-root runtime" for feature in features):
        summary_parts.append("It runs as a non-root user.")
    if any(feature["name"] == "BuildKit cache" for feature in features):
        summary_parts.append("It uses BuildKit cache mounts to speed up repeat builds.")
    if any(feature["name"] == "multi-architecture build" for feature in features):
        summary_parts.append("It is Buildx-friendly for amd64 and arm64 image builds.")
    if any(feature["name"] == "read-only filesystem ready" for feature in features):
        summary_parts.append("It keeps /tmp writable for read-only root filesystem deployments.")
    if any(feature["name"] == "tuned JVM flags" for feature in features):
        summary_parts.append("It applies container-oriented JVM defaults.")
    if must_have_modules:
        summary_parts.append("It adds curated modules for reflection or dynamic-loading edge cases.")

    if not summary_parts:
        summary_parts.append("No recognized springdocker optimizations were detected.")

    notes = [
        "Explanation is based on static text signals in the file.",
        "Some checks are best-effort when Dockerfiles are hand-written.",
    ]
    if "HEALTHCHECK" in text:
        features.append(
            {
                "name": "container healthcheck",
                "enabled": True,
                "reason": "Defines a runtime health probe for orchestrators and local checks.",
            }
        )
    if "STOPSIGNAL SIGTERM" in text:
        features.append(
            {
                "name": "explicit stop signal",
                "enabled": True,
                "reason": "Sets explicit signal semantics for clean shutdown behavior.",
            }
        )
    if "org.opencontainers.image.source" in text:
        features.append(
            {
                "name": "OCI image labels",
                "enabled": True,
                "reason": "Includes standard OCI metadata labels for provenance and traceability.",
            }
        )
    if "/usr/share/sbom/spdx.json" in text:
        features.append(
            {
                "name": "embedded SBOM",
                "enabled": True,
                "reason": "Embeds an SPDX JSON file into the container image filesystem.",
            }
        )
    if "SOURCE_DATE_EPOCH" in text:
        features.append(
            {
                "name": "reproducible build controls",
                "enabled": True,
                "reason": "Uses SOURCE_DATE_EPOCH controls for build reproducibility.",
            }
        )
    if "ArchiveClassesAtExit" in text or "SharedArchiveFile=/app/app.jsa" in text:
        features.append(
            {
                "name": "AppCDS training run",
                "enabled": True,
                "reason": "Builds and uses a CDS archive for faster startup.",
            }
        )
    if "AOTCacheOutput" in text or "AOTCache=" in text:
        features.append(
            {
                "name": "JEP 483 AOT cache",
                "enabled": True,
                "reason": "Trains and loads a JEP 483 ahead-of-time class-loading cache.",
            }
        )
    if "native-image-community" in text or "nativeCompile" in text or "native:compile" in text:
        features.append(
            {
                "name": "native AOT build",
                "enabled": True,
                "reason": "Build stage compiles a GraalVM native image.",
            }
        )
    if "processAot" in text or "spring-boot:process-aot" in text:
        features.append(
            {
                "name": "Spring AOT processing",
                "enabled": True,
                "reason": "Build stage runs Spring AOT processing before packaging.",
            }
        )

    return {
        "source": "Dockerfile",
        "build_tool": build_tool,
        "java_version": java_version,
        "stage_count": sum(1 for line in lines if line.strip().upper().startswith("FROM ")),
        "features": features,
        "summary": " ".join(summary_parts),
        "notes": notes,
    }
