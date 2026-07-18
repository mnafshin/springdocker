package io.github.mnafshin.springdocker.gradle;

import io.github.mnafshin.springdocker.maven.DockerfileRenderer;
import io.github.mnafshin.springdocker.maven.PluginDockerfileOptions;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import javax.inject.Inject;
import org.gradle.api.DefaultTask;
import org.gradle.api.file.DirectoryProperty;
import org.gradle.api.file.ProjectLayout;
import org.gradle.api.provider.Property;
import org.gradle.api.tasks.Input;
import org.gradle.api.tasks.OutputFile;
import org.gradle.api.tasks.TaskAction;

/** Writes a Dockerfile from the {@code springdocker} extension (no Python). */
public abstract class GenerateDockerfileTask extends DefaultTask {

    @Inject
    public GenerateDockerfileTask(ProjectLayout layout) {
        getProjectDirectory().convention(layout.getProjectDirectory());
    }

    @Input
    public abstract Property<Integer> getJavaVersion();

    @Input
    public abstract Property<String> getRuntimeImage();

    @Input
    public abstract Property<Boolean> getUseJlink();

    @Input
    public abstract Property<Boolean> getUseLayeredJar();

    @Input
    public abstract Property<Boolean> getNonRoot();

    @Input
    public abstract Property<String> getRecipe();

    @Input
    public abstract Property<String> getOutput();

    public abstract DirectoryProperty getProjectDirectory();

    @OutputFile
    public abstract org.gradle.api.file.RegularFileProperty getDockerfile();

    @TaskAction
    public void generate() throws IOException {
        PluginDockerfileOptions options = new PluginDockerfileOptions(
                getJavaVersion().get(),
                getRuntimeImage().get(),
                getUseJlink().get(),
                getUseLayeredJar().get(),
                getNonRoot().get(),
                getRecipe().get(),
                getOutput().get()
        );
        Path projectDir = getProjectDirectory().get().getAsFile().toPath();
        Path destination = projectDir.resolve(options.output());
        Files.writeString(destination, DockerfileRenderer.render(options), StandardCharsets.UTF_8);
        Path dockerignore = projectDir.resolve(".dockerignore");
        if (!Files.exists(dockerignore)) {
            Files.write(
                    dockerignore,
                    List.of(".git", ".gradle", "build", ".idea", ".vscode", ".DS_Store", ""),
                    StandardCharsets.UTF_8
            );
        }
        getLogger().lifecycle("Wrote Dockerfile: {}", destination.toAbsolutePath());
        getLogger().lifecycle("Benchmarks remain on the Python CLI.");
    }
}
