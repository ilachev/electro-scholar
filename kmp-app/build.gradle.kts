import org.gradle.api.DefaultTask
import org.gradle.api.file.ConfigurableFileCollection
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.tasks.CacheableTask
import org.gradle.api.tasks.IgnoreEmptyDirectories
import org.gradle.api.tasks.InputFiles
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.Internal
import org.gradle.api.tasks.PathSensitive
import org.gradle.api.tasks.PathSensitivity
import org.gradle.api.tasks.TaskAction

plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.multiplatform.library) apply false
    alias(libs.plugins.compose.compiler) apply false
    alias(libs.plugins.compose.multiplatform) apply false
    alias(libs.plugins.kotlin.jvm) apply false
    alias(libs.plugins.kotlin.multiplatform) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.sqldelight) apply false
}

@CacheableTask
abstract class CheckArchitectureTask : DefaultTask() {
    @get:InputFiles
    @get:IgnoreEmptyDirectories
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val commonSources: ConfigurableFileCollection

    @get:InputFiles
    @get:IgnoreEmptyDirectories
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val featureBuildScripts: ConfigurableFileCollection

    @get:Internal
    abstract val rootDirectory: DirectoryProperty

    @TaskAction
    fun checkBoundaries() {
        val root = rootDirectory.get().asFile
        val violations = mutableListOf<String>()
        val nativeImport = Regex("""^import (android\.|java\.|javax\.swing\.|kotlin\.jvm\.|platform\.)""")
        val hostImport = Regex("""^import io\.github\.ilachev\.electroscholar\.app\.""")
        val forbiddenProjectDependency = Regex(
            """project\(\s*[\"']:(?:androidApp|desktopApp|shared|features:)""",
        )

        commonSources.files.sorted().forEach { source ->
            source.readLines().forEachIndexed { index, line ->
                val statement = line.trim()
                if (nativeImport.containsMatchIn(statement) || hostImport.containsMatchIn(statement)) {
                    violations += "${source.relativeTo(root)}:${index + 1}: $statement"
                }
            }
        }
        featureBuildScripts.files.sorted().forEach { script ->
            script.readLines().forEachIndexed { index, line ->
                if (forbiddenProjectDependency.containsMatchIn(line)) {
                    violations += "${script.relativeTo(root)}:${index + 1}: ${line.trim()}"
                }
            }
        }

        check(violations.isEmpty()) {
            "Architecture boundary violations:\n${violations.joinToString("\n")}"
        }
    }
}

@CacheableTask
abstract class CheckVersionConsistencyTask : DefaultTask() {
    @get:InputFile
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val versionFile: RegularFileProperty

    @get:InputFile
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val iosConfig: RegularFileProperty

    @TaskAction
    fun checkVersions() {
        val version = versionFile.get().asFile.readText().trim()
        check(Regex("""^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$""").matches(version)) {
            "version.txt must contain a SemVer value, got '$version'"
        }

        val config = iosConfig.get().asFile.readText()
        val iosVersion = Regex("""(?m)^MARKETING_VERSION\s*=\s*([^\s/]+)""")
            .find(config)
            ?.groupValues
            ?.get(1)
        check(iosVersion == version) {
            "iOS MARKETING_VERSION '$iosVersion' does not match version.txt '$version'"
        }
    }
}

allprojects {
    dependencyLocking {
        lockAllConfigurations()
        ignoredDependencies.add("org.jetbrains.compose.desktop:desktop-jvm-*")
        ignoredDependencies.add("org.jetbrains.skiko:skiko-awt-runtime-*")
    }
}

tasks.register<CheckArchitectureTask>("checkArchitecture") {
    group = "verification"
    description = "Checks platform and vertical-slice dependency boundaries."
    rootDirectory.set(layout.projectDirectory)
    commonSources.from(fileTree(layout.projectDirectory) {
        include("shared/src/commonMain/**/*.kt")
        include("features/*/src/commonMain/**/*.kt")
    })
    featureBuildScripts.from(fileTree(layout.projectDirectory.dir("features")) {
        include("*/build.gradle.kts")
    })
}

tasks.register<CheckVersionConsistencyTask>("checkVersionConsistency") {
    group = "verification"
    description = "Checks that every native host uses the shared application version."
    versionFile.set(layout.projectDirectory.file("../version.txt"))
    iosConfig.set(layout.projectDirectory.file("iosApp/Configuration/Config.xcconfig"))
}
