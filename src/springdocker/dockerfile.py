"""
Dockerfile generation: digest tables, options/spec dataclasses, and Jinja rendering.

Static explanation heuristics live in dockerfile_explain.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from jinja2 import Environment, PackageLoader, StrictUndefined

from springdocker.digest_pins import (
    DISTROLESS_BASE_DIGESTS,
    DISTROLESS_JAVA_DIGESTS,
    OS_RUNTIME_IMAGES,
    TEMURIN_JDK_DIGESTS,
    TEMURIN_JRE_DIGESTS,
)
from springdocker.gradle_descriptors import DEFAULT_GRADLE_DESCRIPTOR_FILES
from springdocker.java_features import MIN_JAVA_VERSION, validate_dockerfile_options
from springdocker.runtime_images import SUPPORTED_RUNTIME_IMAGES

# Auto-merged into jlink MUSTHAVE_MODULES when jlink is enabled and Spring Web is detected
# (see project_detect.has_spring_web_dependency and ADR 0007).
JLINK_BASELINE_MODULES: tuple[str, ...] = (
    "java.desktop",
    "java.logging",
    "java.naming",
    "java.management",
)

DEFAULT_JVM_FLAGS: tuple[str, ...] = (
    "-XX:MaxRAMPercentage=75",
    "-XX:+ExitOnOutOfMemoryError",
    "-Djava.io.tmpdir=/tmp",
)

BUILTIN_RECIPES = ("jvm-balanced", "spring-aot", "native-aot")
SPRINGDOCKER_REPO_URL = "https://github.com/mnafshin/springdocker"
NATIVE_AOT_SCAFFOLD_WARNING = (
    "native-aot emits experimental scaffold output only; "
    "springdocker does not ship a production native-image workflow yet "
    "(see docs/native-aot.md)"
)
NATIVE_AOT_DOCKERFILE_SCAFFOLD_COMMENT = (
    "# scaffold: experimental native-image Dockerfile; not a production-ready springdocker workflow"
)

GRADLE_BOOT_JAR_PATH = "build/libs/application.jar"
MAVEN_BOOT_JAR_PATH = "target/application.jar"
LAYER_EXTRACT_DEST = "/layers"
LAYERED_RUNTIME_JAR = "application.jar"
LAYERED_APP_CDS_ARCHIVE = "application.jsa"
LAYERED_APP_CDS_WORKDIR = "/cds-work"
LAYERED_JEP483_AOT_CACHE = "application.aot"


def merge_jlink_must_have_modules(
    curated: tuple[str, ...],
    baseline: tuple[str, ...],
) -> tuple[str, ...]:
    merged = list(curated)
    for module in baseline:
        if module not in merged:
            merged.append(module)
    return tuple(merged)


def _distroless_debian_release_number(java_version: int) -> int:
    """Java 25+ uses distroless debian13; older supported Java versions use debian12."""
    return 13 if java_version >= 25 else 12


def _distroless_debian_release(java_version: int) -> str:
    return f"debian{_distroless_debian_release_number(java_version)}"


def _distroless_java_image(java_version: int) -> str:
    return f"gcr.io/distroless/java{java_version}-{_distroless_debian_release(java_version)}:nonroot"


def _distroless_base_image(java_version: int) -> str:
    return f"gcr.io/distroless/base-{_distroless_debian_release(java_version)}:nonroot"


def _distroless_base_digest(java_version: int) -> str | None:
    return DISTROLESS_BASE_DIGESTS.get(_distroless_debian_release_number(java_version))


@dataclass(frozen=True)
class BuildConfig:
    recipe: str
    use_buildkit_cache: bool
    use_jlink: bool
    use_layered_jar: bool
    enable_appcds: bool
    enable_jep483_aot_cache: bool
    must_have_modules: tuple[str, ...]
    jlink_baseline_modules: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeConfig:
    runtime_image: str
    platform_aware: bool
    non_root: bool
    tuned_jvm_flags: bool
    jvm_flags: tuple[str, ...]
    healthcheck_path: str | None


@dataclass(frozen=True)
class SupplyChainConfig:
    include_oci_labels: bool
    include_stopsignal: bool
    include_embedded_sbom: bool
    include_reproducible_controls: bool
    pin_digests: bool


@dataclass(frozen=True)
class DockerfileSpec:
    build_tool: str
    java_version: int
    build: BuildConfig
    runtime: RuntimeConfig
    supply_chain: SupplyChainConfig
    gradle_descriptor_files: tuple[str, ...] = ()


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
    java_version: int = MIN_JAVA_VERSION
    use_buildkit_cache: bool = True
    use_jlink: bool = True
    non_root: bool = True
    tuned_jvm_flags: bool = True
    must_have_modules: tuple[str, ...] = ()
    jlink_baseline_modules: tuple[str, ...] = JLINK_BASELINE_MODULES
    runtime_image: str = "distroless"
    platform_aware: bool = True
    healthcheck_path: str | None = None
    include_oci_labels: bool = True
    include_stopsignal: bool = True
    include_embedded_sbom: bool = True
    include_reproducible_controls: bool = True
    use_layered_jar: bool = True
    enable_appcds: bool = True
    enable_jep483_aot_cache: bool = False
    jvm_flags: tuple[str, ...] = ()
    pin_digests: bool = True
    gradle_descriptor_files: tuple[str, ...] = ()

    def resolved_jvm_flags(self) -> tuple[str, ...]:
        if self.jvm_flags:
            return self.jvm_flags
        if self.tuned_jvm_flags:
            return DEFAULT_JVM_FLAGS
        return ()

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
                jlink_baseline_modules=self.jlink_baseline_modules,
            ),
            runtime=RuntimeConfig(
                runtime_image=self.runtime_image,
                platform_aware=self.platform_aware,
                non_root=self.non_root,
                tuned_jvm_flags=self.tuned_jvm_flags,
                jvm_flags=self.resolved_jvm_flags(),
                healthcheck_path=self.healthcheck_path,
            ),
            supply_chain=SupplyChainConfig(
                include_oci_labels=self.include_oci_labels,
                include_stopsignal=self.include_stopsignal,
                include_embedded_sbom=self.include_embedded_sbom,
                include_reproducible_controls=self.include_reproducible_controls,
                pin_digests=self.pin_digests,
            ),
            gradle_descriptor_files=self.gradle_descriptor_files,
        )


def _gradle_boot_jar_select_run_lines() -> tuple[str, ...]:
    """Pick the boot JAR (snapshot or release) and copy it to a stable path for later stages."""
    return (
        "RUN set -eux; \\",
        "    boot_jar=$(ls build/libs/*.jar | grep -v -- '-plain.jar$' | head -1); \\",
        '    test -n "$boot_jar"; \\',
        f'    cp "$boot_jar" {GRADLE_BOOT_JAR_PATH}',
    )


def _maven_boot_jar_select_run_lines() -> tuple[str, ...]:
    """Pick the executable boot JAR and copy it to a stable path for later stages."""
    return (
        "RUN set -eux; \\",
        "    boot_jar=$(ls target/*.jar | grep -v -- '-plain.jar$' | head -1); \\",
        '    test -n "$boot_jar"; \\',
        f'    cp "$boot_jar" {MAVEN_BOOT_JAR_PATH}',
    )


def _layered_runtime_workspace_copy_lines(*, source_stage: str = "build", chown_flag: str = "") -> tuple[str, ...]:
    prefix = f"COPY --from={source_stage} {chown_flag}"
    dest = LAYER_EXTRACT_DEST
    return (
        f"{prefix}{dest}/dependencies/ ./",
        f"{prefix}{dest}/spring-boot-loader/ ./",
        f"{prefix}{dest}/snapshot-dependencies/ ./",
        f"{prefix}{dest}/application/ ./",
    )


def _layered_appcds_training_run_lines() -> tuple[str, ...]:
    dest = LAYER_EXTRACT_DEST
    return (
        f"RUN mkdir -p {LAYERED_APP_CDS_WORKDIR} && \\",
        f"    cp -a {dest}/dependencies {dest}/spring-boot-loader {dest}/snapshot-dependencies {LAYERED_APP_CDS_WORKDIR}/ && \\",
        f"    cp -a {dest}/application/. {LAYERED_APP_CDS_WORKDIR}/ && \\",
        f"    cd {LAYERED_APP_CDS_WORKDIR} && \\",
        f"    java -XX:ArchiveClassesAtExit={LAYERED_APP_CDS_ARCHIVE} -Dspring.context.exit=onRefresh "
        f"-jar {LAYERED_RUNTIME_JAR} || true",
    )


def _gradle_descriptor_copy_line(descriptor_files: tuple[str, ...]) -> str:
    files = descriptor_files or DEFAULT_GRADLE_DESCRIPTOR_FILES
    return f"COPY {' '.join(('gradlew', *files))} ./"


def _build_setup(
    build_tool: str,
    recipe: str,
    *,
    gradle_descriptor_files: tuple[str, ...] = (),
) -> tuple[list[str], str, str]:
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
            MAVEN_BOOT_JAR_PATH if recipe != "native-aot" else "target/*",
        )
    build_cmd = "./gradlew --no-daemon bootJar -x test"
    if recipe == "spring-aot":
        build_cmd = "./gradlew --no-daemon processAot bootJar -x test"
    elif recipe == "native-aot":
        build_cmd = "./gradlew --no-daemon nativeCompile -x test"
    return (
        [
            _gradle_descriptor_copy_line(gradle_descriptor_files),
            "COPY gradle ./gradle",
            "RUN chmod +x gradlew",
            "COPY src ./src",
        ],
        build_cmd,
        GRADLE_BOOT_JAR_PATH if recipe != "native-aot" else "build/native/nativeCompile/*",
    )


def _section(*lines: str) -> DockerfileSection:
    return DockerfileSection(lines=tuple(lines))


def _validate_options(options: DockerfileOptions) -> None:
    if options.build_tool not in {"maven", "gradle"}:
        raise ValueError("build tool must be 'maven' or 'gradle'")
    validate_dockerfile_options(options)
    if options.runtime_image not in SUPPORTED_RUNTIME_IMAGES:
        supported = ", ".join(sorted(SUPPORTED_RUNTIME_IMAGES))
        raise ValueError(f"runtime_image must be one of: {supported}")
    if options.recipe not in BUILTIN_RECIPES:
        supported = ", ".join(BUILTIN_RECIPES)
        raise ValueError(f"recipe must be one of: {supported}")
    for flag in options.jvm_flags:
        if not flag.strip():
            raise ValueError("jvm_flags entries must be non-empty")


def _pin_image(tag: str, digest: str | None, *, pin_digests: bool = True) -> str:
    if not pin_digests or digest is None:
        return tag
    return f"{tag}@{digest}"


def _jlink_build_base(spec: DockerfileSpec, default_build_base: str) -> str:
    """Use a musl-linked JDK for jlink when the runtime base is Alpine."""
    if spec.runtime.runtime_image == "alpine":
        return f"eclipse-temurin:{spec.java_version}-jdk-alpine"
    return default_build_base


def _uses_os_runtime(spec: DockerfileSpec) -> bool:
    return spec.runtime.runtime_image in OS_RUNTIME_IMAGES


def _bundles_vendor_jre_on_os_runtime(spec: DockerfileSpec) -> bool:
    return _uses_os_runtime(spec) and not spec.build.use_jlink


def _vendor_jre_image(java_version: int, *, pin_digests: bool = True) -> str:
    return _pin_image(
        f"eclipse-temurin:{java_version}-jre",
        TEMURIN_JRE_DIGESTS.get(java_version),
        pin_digests=pin_digests,
    )


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
        lines.extend(_layered_runtime_workspace_copy_lines(source_stage="build", chown_flag=chown_flag))
        if spec.build.enable_appcds:
            lines.append(
                f"COPY --from=build {chown_flag}{LAYERED_APP_CDS_WORKDIR}/{LAYERED_APP_CDS_ARCHIVE} "
                f"/app/{LAYERED_APP_CDS_ARCHIVE}"
            )
        if spec.build.enable_jep483_aot_cache:
            lines.append(
                f"COPY --from=aot-trainer {chown_flag}/app/{LAYERED_JEP483_AOT_CACHE} /app/{LAYERED_JEP483_AOT_CACHE}"
            )
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
    setup, build_cmd, jar_path = _build_setup(
        spec.build_tool,
        spec.build.recipe,
        gradle_descriptor_files=spec.gradle_descriptor_files,
    )
    build_step = (
        "RUN --mount=type=cache,sharing=locked,target=/root/.m2 " + build_cmd
        if spec.build.use_buildkit_cache and spec.build_tool == "maven"
        else "RUN --mount=type=cache,sharing=locked,target=/root/.gradle " + build_cmd
        if spec.build.use_buildkit_cache and spec.build_tool == "gradle"
        else f"RUN {build_cmd}"
    )

    jvm_args: list[str] = list(spec.runtime.jvm_flags)

    header_lines = [
        "# syntax=docker/dockerfile:1",
        f"# Generated by springdocker — {SPRINGDOCKER_REPO_URL}",
        f"# Java {spec.java_version} | build-tool: {spec.build_tool}",
    ]
    if spec.build.recipe != "jvm-balanced":
        header_lines.append(f"# recipe: {spec.build.recipe}")
    if spec.build.recipe == "native-aot":
        header_lines.append(NATIVE_AOT_DOCKERFILE_SCAFFOLD_COMMENT)
    header_lines.append("")
    sections: list[DockerfileSection] = [_section(*header_lines)]
    if spec.runtime.platform_aware:
        sections.append(_section("ARG TARGETPLATFORM", "ARG BUILDPLATFORM", ""))
    if spec.supply_chain.include_reproducible_controls:
        sections.append(_section("ARG SOURCE_DATE_EPOCH=0", ""))
    if spec.supply_chain.include_oci_labels:
        sections.append(_section('ARG OCI_SOURCE=""', 'ARG OCI_REVISION=""', 'ARG OCI_CREATED=""', ""))
    pin_digests = spec.supply_chain.pin_digests
    build_base = _pin_image(
        f"eclipse-temurin:{spec.java_version}-jdk",
        TEMURIN_JDK_DIGESTS.get(spec.java_version),
        pin_digests=pin_digests,
    )
    if spec.build.recipe == "native-aot":
        build_base = f"ghcr.io/graalvm/native-image-community:{spec.java_version}"
    gradle_boot_jar_select = (
        _gradle_boot_jar_select_run_lines()
        if spec.build_tool == "gradle" and spec.build.recipe != "native-aot"
        else ()
    )
    maven_boot_jar_select = (
        _maven_boot_jar_select_run_lines()
        if spec.build_tool == "maven" and spec.build.recipe != "native-aot"
        else ()
    )
    sections.append(
        _section(
            f"FROM --platform=$BUILDPLATFORM {build_base} AS build",
            "WORKDIR /app",
            *setup,
            build_step,
            *gradle_boot_jar_select,
            *maven_boot_jar_select,
            f"RUN java -Djarmode=tools -jar /app/{jar_path} extract --layers --destination {LAYER_EXTRACT_DEST}"
            if spec.build.use_layered_jar
            else "",
            *_layered_appcds_training_run_lines()
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
            f"FROM --platform=$TARGETPLATFORM {_pin_image(_distroless_base_image(spec.java_version), _distroless_base_digest(spec.java_version), pin_digests=pin_digests)}",
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

    if _bundles_vendor_jre_on_os_runtime(spec):
        sections.append(_section(f"FROM {_vendor_jre_image(spec.java_version, pin_digests=pin_digests)} AS vendor-jre", ""))

    if spec.build.use_jlink:
        must_have = merge_jlink_must_have_modules(
            spec.build.must_have_modules,
            spec.build.jlink_baseline_modules,
        )
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
        pin_digests=pin_digests,
    )
    if spec.build.use_jlink and spec.build.enable_jep483_aot_cache:
        sections.append(
            _section(
                f"FROM --platform=$TARGETPLATFORM {runtime_base} AS aot-trainer",
                "COPY --from=jre-builder /jre/out /opt/java",
                "ENV JAVA_HOME=/opt/java",
                'ENV PATH="${JAVA_HOME}/bin:${PATH}"',
                "WORKDIR /app",
                *_layered_runtime_workspace_copy_lines(source_stage="build"),
                (
                    f"RUN java -XX:AOTCacheOutput=/app/{LAYERED_JEP483_AOT_CACHE} -Dspring.context.exit=onRefresh "
                    f"-jar {LAYERED_RUNTIME_JAR}; \\"
                ),
                f"    test -f /app/{LAYERED_JEP483_AOT_CACHE}",
                "",
            )
        )

    if spec.runtime.runtime_image == "distroless":
        runtime_base = (
            _pin_image(
                _distroless_base_image(spec.java_version),
                _distroless_base_digest(spec.java_version),
                pin_digests=pin_digests,
            )
            if spec.build.use_jlink
            else _pin_image(
                _distroless_java_image(spec.java_version),
                DISTROLESS_JAVA_DIGESTS.get(spec.java_version),
                pin_digests=pin_digests,
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
            distroless_lines.extend(_layered_runtime_workspace_copy_lines(source_stage="build"))
            if spec.build.enable_appcds:
                distroless_lines.append(
                    f"COPY --from=build {LAYERED_APP_CDS_WORKDIR}/{LAYERED_APP_CDS_ARCHIVE} /app/{LAYERED_APP_CDS_ARCHIVE}"
                )
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
    elif spec.runtime.runtime_image == "temurin" and spec.build.use_jlink:
        # jlink ships the runtime; a Temurin JRE base would only add unused layers.
        tag, digest = OS_RUNTIME_IMAGES["debian-slim"]
        sections.append(_compose_os_runtime_section(spec, jar_path, _pin_image(tag, digest, pin_digests=pin_digests)))
    elif spec.runtime.runtime_image in OS_RUNTIME_IMAGES:
        tag, digest = OS_RUNTIME_IMAGES[spec.runtime.runtime_image]
        sections.append(_compose_os_runtime_section(spec, jar_path, _pin_image(tag, digest, pin_digests=pin_digests)))
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
            temurin_lines.extend(_layered_runtime_workspace_copy_lines(source_stage="build", chown_flag=chown_flag))
            if spec.build.enable_appcds:
                temurin_lines.append(
                    f"COPY --from=build {chown_flag}{LAYERED_APP_CDS_WORKDIR}/{LAYERED_APP_CDS_ARCHIVE} "
                    f"/app/{LAYERED_APP_CDS_ARCHIVE}"
                )
            if spec.build.enable_jep483_aot_cache:
                temurin_lines.append(
                    f"COPY --from=aot-trainer {chown_flag}/app/{LAYERED_JEP483_AOT_CACHE} /app/{LAYERED_JEP483_AOT_CACHE}"
                )
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

    if _bundles_vendor_jre_on_os_runtime(spec):
        sections.append(
            _section(
                "COPY --from=vendor-jre /opt/java/openjdk /opt/java",
                "ENV JAVA_HOME=/opt/java",
                'ENV PATH="${JAVA_HOME}/bin:${PATH}"',
            )
        )
    elif spec.build.use_jlink and spec.runtime.runtime_image != "distroless":
        sections.append(
            _section(
                "COPY --from=jre-builder /jre/out /opt/java",
                "ENV JAVA_HOME=/opt/java",
                'ENV PATH="${JAVA_HOME}/bin:${PATH}"',
            )
        )

    if spec.build.use_layered_jar and spec.build.enable_appcds:
        jvm_args.append(f"-XX:SharedArchiveFile={LAYERED_APP_CDS_ARCHIVE}")
    if spec.build.enable_jep483_aot_cache:
        jvm_args.append(f"-XX:AOTCache={LAYERED_JEP483_AOT_CACHE}")
    entrypoint = (
        ["java", *jvm_args, "-jar", LAYERED_RUNTIME_JAR]
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
