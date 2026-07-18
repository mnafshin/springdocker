package io.github.mnafshin.springdocker.gradle;

import io.github.mnafshin.springdocker.maven.PluginDockerfileOptions;
import org.gradle.api.Plugin;
import org.gradle.api.Project;

/**
 * Registers {@code springdocker { }} extension and generate/verify tasks (build.gradle SSOT).
 */
public class SpringdockerPlugin implements Plugin<Project> {

    @Override
    public void apply(Project project) {
        SpringdockerExtension extension = project.getExtensions()
                .create("springdocker", SpringdockerExtension.class);

        extension.getJavaVersion().convention(PluginDockerfileOptions.DEFAULT_JAVA_VERSION);
        extension.getRuntimeImage().convention(PluginDockerfileOptions.DEFAULT_RUNTIME_IMAGE);
        extension.getUseJlink().convention(true);
        extension.getUseLayeredJar().convention(true);
        extension.getNonRoot().convention(true);
        extension.getRecipe().convention(PluginDockerfileOptions.DEFAULT_RECIPE);
        extension.getOutput().convention(PluginDockerfileOptions.DEFAULT_OUTPUT);

        project.getTasks().register("springdockerGenerate", GenerateDockerfileTask.class, task -> {
            task.setGroup("springdocker");
            task.setDescription("Generate Dockerfile from springdocker {} extension (no Python)");
            task.getJavaVersion().set(extension.getJavaVersion());
            task.getRuntimeImage().set(extension.getRuntimeImage());
            task.getUseJlink().set(extension.getUseJlink());
            task.getUseLayeredJar().set(extension.getUseLayeredJar());
            task.getNonRoot().set(extension.getNonRoot());
            task.getRecipe().set(extension.getRecipe());
            task.getOutput().set(extension.getOutput());
            task.getDockerfile().set(
                    extension.getOutput().map(name -> project.getLayout().getProjectDirectory().file(name))
            );
        });

        project.getTasks().register("springdockerVerify", VerifyDockerfileTask.class, task -> {
            task.setGroup("springdocker");
            task.setDescription("Verify Dockerfile matches springdocker {} extension (build.gradle SSOT)");
            task.getJavaVersion().set(extension.getJavaVersion());
            task.getRuntimeImage().set(extension.getRuntimeImage());
            task.getUseJlink().set(extension.getUseJlink());
            task.getUseLayeredJar().set(extension.getUseLayeredJar());
            task.getNonRoot().set(extension.getNonRoot());
            task.getRecipe().set(extension.getRecipe());
            task.getOutput().set(extension.getOutput());
        });
    }
}
