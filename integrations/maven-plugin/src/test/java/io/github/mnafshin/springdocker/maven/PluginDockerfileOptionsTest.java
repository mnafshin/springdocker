package io.github.mnafshin.springdocker.maven;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class PluginDockerfileOptionsTest {

    @Test
    void defaultsMatchSchema() {
        PluginDockerfileOptions options = PluginDockerfileOptions.defaults();
        assertEquals(17, options.javaVersion());
        assertEquals("distroless", options.runtimeImage());
        assertTrue(options.useJlink());
        assertTrue(options.useLayeredJar());
        assertTrue(options.nonRoot());
        assertEquals("jvm-balanced", options.recipe());
        assertEquals("Dockerfile.generated", options.output());
    }

    @Test
    void rejectsNativeAotRecipe() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new PluginDockerfileOptions(17, "temurin", false, false, true, "native-aot", "Dockerfile")
        );
    }

    @Test
    void rejectsJavaBelow17() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new PluginDockerfileOptions(11, "temurin", false, false, true, "jvm-balanced", "Dockerfile")
        );
    }
}
