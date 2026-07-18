package io.github.mnafshin.springdocker.maven;

import java.util.Locale;
import java.util.Objects;
import java.util.Set;

/**
 * Plugin-native Dockerfile options (POM SSOT). Never loaded from {@code .springdocker.toml}.
 *
 * <p>Schema for milestone issue #141; used by generate/verify/export goals.
 */
public final class PluginDockerfileOptions {

    public static final Set<String> RUNTIME_IMAGES = Set.of(
            "distroless", "debian-slim", "alpine", "ubuntu", "temurin"
    );

    public static final Set<String> RECIPES = Set.of("jvm-balanced", "spring-aot");

    public static final int DEFAULT_JAVA_VERSION = 17;
    public static final String DEFAULT_RUNTIME_IMAGE = "distroless";
    public static final String DEFAULT_RECIPE = "jvm-balanced";
    public static final String DEFAULT_OUTPUT = "Dockerfile.generated";

    private final int javaVersion;
    private final String runtimeImage;
    private final boolean useJlink;
    private final boolean useLayeredJar;
    private final boolean nonRoot;
    private final String recipe;
    private final String output;

    public PluginDockerfileOptions(
            int javaVersion,
            String runtimeImage,
            boolean useJlink,
            boolean useLayeredJar,
            boolean nonRoot,
            String recipe,
            String output
    ) {
        if (javaVersion < 17) {
            throw new IllegalArgumentException("javaVersion must be >= 17 (got " + javaVersion + ")");
        }
        String runtime = normalize(runtimeImage, DEFAULT_RUNTIME_IMAGE).toLowerCase(Locale.ROOT);
        if (!RUNTIME_IMAGES.contains(runtime)) {
            throw new IllegalArgumentException(
                    "runtimeImage must be one of " + RUNTIME_IMAGES + " (got " + runtime + ")"
            );
        }
        String recipeName = normalize(recipe, DEFAULT_RECIPE).toLowerCase(Locale.ROOT);
        if (!RECIPES.contains(recipeName)) {
            throw new IllegalArgumentException(
                    "recipe must be one of " + RECIPES + " (got " + recipeName + "); native-aot is CLI-only"
            );
        }
        this.javaVersion = javaVersion;
        this.runtimeImage = runtime;
        this.useJlink = useJlink;
        this.useLayeredJar = useLayeredJar;
        this.nonRoot = nonRoot;
        this.recipe = recipeName;
        this.output = normalize(output, DEFAULT_OUTPUT);
    }

    public static PluginDockerfileOptions defaults() {
        return new PluginDockerfileOptions(
                DEFAULT_JAVA_VERSION,
                DEFAULT_RUNTIME_IMAGE,
                true,
                true,
                true,
                DEFAULT_RECIPE,
                DEFAULT_OUTPUT
        );
    }

    public int javaVersion() {
        return javaVersion;
    }

    public String runtimeImage() {
        return runtimeImage;
    }

    public boolean useJlink() {
        return useJlink;
    }

    public boolean useLayeredJar() {
        return useLayeredJar;
    }

    public boolean nonRoot() {
        return nonRoot;
    }

    public String recipe() {
        return recipe;
    }

    public String output() {
        return output;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof PluginDockerfileOptions that)) {
            return false;
        }
        return javaVersion == that.javaVersion
                && useJlink == that.useJlink
                && useLayeredJar == that.useLayeredJar
                && nonRoot == that.nonRoot
                && Objects.equals(runtimeImage, that.runtimeImage)
                && Objects.equals(recipe, that.recipe)
                && Objects.equals(output, that.output);
    }

    @Override
    public int hashCode() {
        return Objects.hash(javaVersion, runtimeImage, useJlink, useLayeredJar, nonRoot, recipe, output);
    }

    private static String normalize(String value, String defaultValue) {
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        return value.trim();
    }
}
