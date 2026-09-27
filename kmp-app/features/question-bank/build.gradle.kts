import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.gradle.api.tasks.testing.Test

plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.android.multiplatform.library)
    alias(libs.plugins.compose.multiplatform)
    alias(libs.plugins.compose.compiler)
    alias(libs.plugins.sqldelight)
}

kotlin {
    jvm()

    android {
        namespace = "io.github.ilachev.electroscholar.feature.questionbank"
        compileSdk = libs.versions.android.compileSdk.get().toInt()
        minSdk = libs.versions.android.minSdk.get().toInt()

        compilerOptions {
            jvmTarget = JvmTarget.JVM_11
        }
        androidResources {
            enable = true
        }
    }

    listOf(
        iosArm64(),
        iosSimulatorArm64(),
    ).forEach { iosTarget ->
        iosTarget.binaries.framework {
            baseName = "QuestionBankFeature"
            isStatic = true
        }
    }

    jvmToolchain(21)

    sourceSets {
        commonMain.dependencies {
            implementation(libs.compose.runtime)
            implementation(libs.compose.foundation)
            implementation(libs.compose.material3)
            implementation(libs.compose.material.icons.core)
            implementation(libs.compose.ui)
            implementation(libs.compose.components.resources)
            implementation(libs.sqldelight.runtime)
            implementation(libs.coroutines.core)
        }
        commonTest.dependencies {
            implementation(kotlin("test"))
        }
        androidMain.dependencies {
            implementation(libs.androidx.activity.compose)
            implementation(libs.sqldelight.android.driver)
        }
        jvmMain.dependencies {
            implementation(libs.sqldelight.sqlite.driver)
        }
        jvmTest.dependencies {
            implementation(libs.coroutines.test)
        }
        iosMain.dependencies {
            implementation(libs.sqldelight.native.driver)
        }
    }
}

sqldelight {
    databases {
        create("QuestionBankDatabase") {
            packageName.set("io.github.ilachev.electroscholar.feature.questionbank.data")
        }
    }
}

compose.resources {
    publicResClass = true
    packageOfResClass = "io.github.ilachev.electroscholar.feature.questionbank.resources"
}

val testHome = layout.buildDirectory.dir("test-user-home")
tasks.withType<Test>().configureEach {
    systemProperty("user.home", testHome.get().asFile.absolutePath)
}
