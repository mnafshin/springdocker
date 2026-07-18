package io.github.mnafshin.springdocker.maven;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugin.MojoFailureException;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.project.MavenProject;

/**
 * Optional bridge: write {@code .springdocker.toml} from plugin configuration (POM → toml only).
 */
@Mojo(name = "export-config", requiresProject = true, threadSafe = true)
public class ExportConfigMojo extends AbstractMojo {

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

    @Parameter(property = "springdocker.configFile", defaultValue = ".springdocker.toml")
    private String configFile;

    @Parameter(property = "springdocker.force", defaultValue = "false")
    private boolean force;

    @Parameter(property = "springdocker.skip", defaultValue = "false")
    private boolean skip;

    @Override
    public void execute() throws MojoExecutionException, MojoFailureException {
        if (skip) {
            getLog().info("springdocker:export-config skipped");
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

        File destination = new File(project.getBasedir(), configFile);
        if (destination.exists() && !force) {
            throw new MojoFailureException(
                    "Config already exists: " + destination + " — re-run with -Dspringdocker.force=true to overwrite"
            );
        }

        try {
            Files.writeString(destination.toPath(), TomlConfigExporter.render(options), StandardCharsets.UTF_8);
        } catch (IOException ex) {
            throw new MojoExecutionException("Failed to write " + destination + ": " + ex.getMessage(), ex);
        }
        getLog().info("Wrote " + destination.getAbsolutePath() + " (one-way export from POM SSOT)");
        getLog().info("Plugin configuration remains the builder SSOT; toml is for Python CLI adoption.");
    }
}
