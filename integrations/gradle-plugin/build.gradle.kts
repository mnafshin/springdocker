plugins {
    `java-gradle-plugin`
    `maven-publish`
}

group = "io.github.mnafshin"
version = "1.3.0-SNAPSHOT"

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

repositories {
    mavenCentral()
}

dependencies {
    compileOnly(gradleApi())
    testImplementation(gradleTestKit())
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
}

tasks.test {
    useJUnitPlatform()
}

// Reuse pure-Java generator core from the Maven plugin module (same package).
sourceSets {
    main {
        java {
            srcDir("../maven-plugin/src/main/java")
            exclude("**/GenerateMojo.java")
            exclude("**/VerifyMojo.java")
            exclude("**/ExportConfigMojo.java")
        }
    }
}

gradlePlugin {
    plugins {
        create("springdocker") {
            id = "io.github.mnafshin.springdocker"
            implementationClass = "io.github.mnafshin.springdocker.gradle.SpringdockerPlugin"
            displayName = "springdocker"
            description = "Generate and verify Spring Boot Dockerfiles from build.gradle (SSOT; no Python)"
        }
    }
}
