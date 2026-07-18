package io.github.mnafshin.springdocker.maven;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.List;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugin.MojoFailureException;
import org.apache.maven.plugins.annotations.LifecyclePhase;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.project.MavenProject;

/**
 * Generates a Dockerfile from POM plugin configuration (no Python, no toml).
 */
@Mojo(name = "generate", defaultPhase = LifecyclePhase.GENERATE_RESOURCES, requiresProject = true, threadSafe = true)
public class GenerateMojo extends AbstractMojo {

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
            getLog().info("springdocker:generate skipped (springdocker.skip=true)");
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

        File basedir = project.getBasedir();
        File pom = new File(basedir, "pom.xml");
        if (!pom.isFile()) {
            throw new MojoFailureException("pom.xml not found in " + basedir + " (Maven builder expects a Maven project)");
        }

        String dockerfile = DockerfileRenderer.render(options);
        File destination = new File(basedir, options.output());
        try {
            Files.writeString(destination.toPath(), dockerfile, StandardCharsets.UTF_8);
            writeDockerignore(basedir);
        } catch (IOException ex) {
            throw new MojoExecutionException("Failed to write " + destination + ": " + ex.getMessage(), ex);
        }
        getLog().info("Wrote Dockerfile: " + destination.getAbsolutePath());
        getLog().info("Benchmarks and advanced tooling remain on the Python CLI (see docs/adopt.md).");
    }

    private static void writeDockerignore(File basedir) throws IOException {
        File ignore = new File(basedir, ".dockerignore");
        if (ignore.exists()) {
            return;
        }
        List<String> lines = List.of(
                ".git",
                ".gitignore",
                "target",
                ".idea",
                ".vscode",
                ".DS_Store",
                ""
        );
        Files.write(ignore.toPath(), lines, StandardCharsets.UTF_8);
    }
}
