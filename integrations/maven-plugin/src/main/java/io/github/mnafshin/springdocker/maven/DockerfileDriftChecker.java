package io.github.mnafshin.springdocker.maven;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Compares an on-disk Dockerfile to what {@link DockerfileRenderer} would emit for plugin options.
 */
public final class DockerfileDriftChecker {

    private DockerfileDriftChecker() {}

    public static List<String> findDrift(String actualDockerfile, PluginDockerfileOptions options) {
        String expected = DockerfileRenderer.render(options);
        String normalizedActual = normalize(actualDockerfile);
        String normalizedExpected = normalize(expected);
        List<String> issues = new ArrayList<>();
        if (!normalizedActual.equals(normalizedExpected)) {
            issues.add("Dockerfile content does not match plugin configuration (POM SSOT)");
        }

        String runtime = options.runtimeImage().toLowerCase(Locale.ROOT);
        if ("distroless".equals(runtime) && containsHealthcheck(normalizedActual)) {
            issues.add("distroless runtime must not include HEALTHCHECK (no shell)");
        }
        if (options.javaVersion() >= 17
                && !normalizedActual.contains("Java " + options.javaVersion())) {
            issues.add("missing Java " + options.javaVersion() + " marker from plugin javaVersion");
        }
        if (!normalizedActual.contains(options.runtimeImage())
                && !normalizedActual.contains(distrolessHint(options))) {
            // soft signal already covered by full compare; keep list focused
        }
        return issues;
    }

    private static String distrolessHint(PluginDockerfileOptions options) {
        if (!"distroless".equals(options.runtimeImage())) {
            return "";
        }
        return options.useJlink() ? "distroless/base-debian12" : "distroless/java";
    }

    private static boolean containsHealthcheck(String text) {
        return text.lines().anyMatch(line -> line.trim().startsWith("HEALTHCHECK"));
    }

    public static String normalize(String text) {
        return text.replace("\r\n", "\n").strip() + "\n";
    }
}
