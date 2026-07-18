package io.github.mnafshin.springdocker.maven;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class DockerfileRendererTest {

    @Test
    void rendersTemurinWithoutJlink() {
        PluginDockerfileOptions options = new PluginDockerfileOptions(
                21, "temurin", false, true, true, "jvm-balanced", "Dockerfile.generated"
        );
        String df = DockerfileRenderer.render(options);
        assertTrue(df.contains("eclipse-temurin:21-jdk AS build"));
        assertTrue(df.contains("eclipse-temurin:21-jre AS runtime"));
        assertFalse(df.contains("AS jlink"));
        assertTrue(df.contains("extract --layers"));
        assertTrue(df.contains("HEALTHCHECK"));
        assertTrue(df.contains("POM SSOT"));
    }

    @Test
    void rendersDistrolessWithJlink() {
        PluginDockerfileOptions options = new PluginDockerfileOptions(
                17, "distroless", true, true, true, "jvm-balanced", "Dockerfile.generated"
        );
        String df = DockerfileRenderer.render(options);
        assertTrue(df.contains("AS jlink"));
        assertTrue(df.contains("gcr.io/distroless/base-debian12:nonroot"));
        assertTrue(df.contains("/jre/bin/java"));
        assertFalse(df.contains("HEALTHCHECK"));
    }

    @Test
    void rendersDistrolessJavaImageWithoutJlink() {
        PluginDockerfileOptions options = new PluginDockerfileOptions(
                17, "distroless", false, false, true, "jvm-balanced", "Dockerfile.generated"
        );
        String df = DockerfileRenderer.render(options);
        assertFalse(df.contains("AS jlink"));
        assertTrue(df.contains("gcr.io/distroless/java17-debian12:nonroot"));
        assertTrue(df.contains("app.jar"));
    }

    @Test
    void springAotRecipeAddsProcessAot() {
        PluginDockerfileOptions options = new PluginDockerfileOptions(
                17, "temurin", false, false, true, "spring-aot", "Dockerfile.generated"
        );
        String df = DockerfileRenderer.render(options);
        assertTrue(df.contains("spring-boot:process-aot"));
        assertTrue(df.contains("# recipe: spring-aot"));
    }
}
