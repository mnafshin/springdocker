package io.github.mnafshin.springdocker.maven;

import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class TomlConfigExporterTest {

    @Test
    void exportsMappedSubset() {
        PluginDockerfileOptions options = new PluginDockerfileOptions(
                21, "temurin", false, true, true, "jvm-balanced", "Dockerfile.generated"
        );
        String toml = TomlConfigExporter.render(options);
        assertTrue(toml.contains("java_version = 21"));
        assertTrue(toml.contains("runtime_image = \"temurin\""));
        assertTrue(toml.contains("use_jlink = false"));
        assertTrue(toml.contains("POM SSOT"));
        assertTrue(toml.contains("build_tool = \"maven\""));
    }
}
