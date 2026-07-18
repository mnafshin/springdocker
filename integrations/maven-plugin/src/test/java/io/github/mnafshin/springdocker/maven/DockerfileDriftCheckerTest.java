package io.github.mnafshin.springdocker.maven;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class DockerfileDriftCheckerTest {

    @Test
    void noDriftWhenMatchesRenderer() {
        PluginDockerfileOptions options = PluginDockerfileOptions.defaults();
        String df = DockerfileRenderer.render(options);
        assertTrue(DockerfileDriftChecker.findDrift(df, options).isEmpty());
    }

    @Test
    void detectsManualEdit() {
        PluginDockerfileOptions options = PluginDockerfileOptions.defaults();
        String df = DockerfileRenderer.render(options) + "\n# tampered\n";
        List<String> drift = DockerfileDriftChecker.findDrift(df, options);
        assertFalse(drift.isEmpty());
        assertTrue(drift.get(0).contains("does not match"));
    }
}
