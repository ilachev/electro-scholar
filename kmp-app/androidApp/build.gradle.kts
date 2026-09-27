import org.jetbrains.kotlin.gradle.dsl.JvmTarget

val appVersion = providers.fileContents(
    rootProject.layout.projectDirectory.file("../version.txt")
).asText.map(String::trim)

fun semVerToVersionCode(version: String): Int {
    val match = requireNotNull(Regex("""^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$""").matchEntire(version)) {
        "version.txt must contain a SemVer value, got '$version'"
    }
    val (major, minor, patch) = match.destructured
    require(major.toInt() <= 2_000 && minor.toInt() <= 999 && patch.toInt() <= 999) {
        "Version '$version' cannot be represented as an Android versionCode"
    }
    return major.toInt() * 1_000_000 + minor.toInt() * 1_000 + patch.toInt()
}

val resolvedAppVersion = appVersion.get()

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.compose.compiler)
}

dependencies {
    implementation(project(":shared"))
    implementation(libs.androidx.activity.compose)
}

android {
    namespace = "io.github.ilachev.electroscholar"
    compileSdk = libs.versions.android.compileSdk.get().toInt()

    defaultConfig {
        applicationId = "io.github.ilachev.electroscholar"
        minSdk = libs.versions.android.minSdk.get().toInt()
        targetSdk = libs.versions.android.targetSdk.get().toInt()
        versionCode = semVerToVersionCode(resolvedAppVersion)
        versionName = resolvedAppVersion
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

kotlin {
    compilerOptions {
        jvmTarget = JvmTarget.JVM_11
    }
}
