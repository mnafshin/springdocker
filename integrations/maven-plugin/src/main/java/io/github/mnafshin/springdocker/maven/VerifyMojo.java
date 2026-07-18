package io.github.mnafshin.springdocker.maven;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugin.MojoFailureException;
import org.apache.maven.plugins.annotations.LifecyclePhase;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.project.MavenProject;

/**
 * Fails the build when the Dockerfile does not match a fresh render from plugin config (POM SSOT).
 */
@Mojo(name = "verify", defaultPhase = LifecyclePhase.VERIFY, requiresProject = true, threadSafe = true)
public class VerifyMojo extends AbstractMojo {

    @Parameter(defaultValue = "${project}", readonly = true, required = true)
    private MavenProject project;

    @Parameter(property = "springdocker.javaVersion", defaultValue = "17")
    private int javaVersion;

    @Parameter(property = "springdocker.runtimeImage", defaultValue = "distroless")
    private String runtimeImage;

    @Parameter(property = "springdocker.useJlink", defaultValue = "true")
    private boolean useJlink;

    @Parameter(property = "springdocker.useLayeredJar", defaultValue = "true")
    private boolean useLayeredJar;

    @Parameter(property = "springdocker.nonRoot", defaultValue = "true")
    private boolean nonRoot;

    @Parameter(property = "springdocker.recipe", defaultValue = "jvm-balanced")
    private String recipe;

    @Parameter(property = "springdocker.output", defaultValue = "Dockerfile.generated")
    private String output;

    @Parameter(property = "springdocker.skip", defaultValue = "false")
    private boolean skip;

    @Override
    public void execute() throws MojoExecutionException, MojoFailureException {
        if (skip) {
            getLog().info("springdocker:verify skipped (springdocker.skip=true)");
            return;
        }

        PluginDockerfileOptions options;
        try {
            options = new PluginDockerfileOptions(
                    javaVersion, runtimeImage, useJlink, useLayeredJar, nonRoot, recipe, output
            );
        } catch (IllegalArgumentException ex) {
            throw new MojoFailureException(ex.getMessage(), ex);
        }

        File dockerfile = new File(project.getBasedir(), options.output());
        if (!dockerfile.isFile()) {
            throw new MojoFailureException(
                    "Missing Dockerfile: " + dockerfile + " — run mvn springdocker:generate first"
            );
        }

        String expected = DockerfileRenderer.render(options);
        String actual;
        try {
            actual = Files.readString(dockerfile.toPath(), StandardCharsets.UTF_8);
        } catch (IOException ex) {
            throw new MojoExecutionException("Failed to read " + dockerfile + ": " + ex.getMessage(), ex);
        }

        if (!normalize(actual).equals(normalize(expected))) {
            throw new MojoFailureException(
                    "Dockerfile drift detected vs plugin configuration (POM SSOT). "
                            + "Re-run mvn springdocker:generate and commit "
                            + options.output()
                            + ". (CLI verify --check-config-drift uses .springdocker.toml instead.)"
            );
        }
        getLog().info("springdocker:verify OK — " + options.output() + " matches plugin configuration");
    }

    static String normalize(String text) {
        return text.replace("\r\n", "\n").strip();
    }
}
