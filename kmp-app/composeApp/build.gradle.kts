import org.jetbrains.compose.desktop.application.dsl.TargetFormat
import org.gradle.api.tasks.Sync

plugins {
    kotlin("multiplatform")
    id("org.jetbrains.compose")
    id("org.jetbrains.kotlin.plugin.compose")
    id("app.cash.sqldelight")
}

kotlin {
    jvm("desktop")
    jvmToolchain(21)

    sourceSets {
        commonMain.dependencies {
            implementation("org.jetbrains.compose.runtime:runtime:1.12.1")
            implementation("org.jetbrains.compose.foundation:foundation:1.12.1")
            implementation("org.jetbrains.compose.material3:material3:1.9.0")
            implementation("org.jetbrains.compose.ui:ui:1.12.1")
        }
        commonTest.dependencies {
            implementation(kotlin("test"))
        }
        val desktopMain by getting {
            dependencies {
                implementation(compose.desktop.currentOs)
                implementation("app.cash.sqldelight:sqlite-driver:2.3.2")
            }
        }
    }
}

val syncQuestionBank = tasks.register<Sync>("syncQuestionBank") {
    group = "content"
    description = "Copies the latest reverse-engineered SQLite database and images into app resources."
    val exportedDatabase = rootProject.layout.projectDirectory.dir("../analysis/database")
    from(exportedDatabase.file("toe.sqlite")) {
        into("database")
    }
    from(exportedDatabase.dir("images")) {
        include("*.jpg")
        into("images")
    }
    into(layout.projectDirectory.dir("src/desktopMain/resources"))
}

tasks.named("desktopProcessResources") {
    dependsOn(syncQuestionBank)
}

sqldelight {
    databases {
        create("ToeDatabase") {
            packageName.set("ru.toe.data")
        }
    }
}

compose.desktop {
    application {
        mainClass = "ru.toe.app.MainKt"

        nativeDistributions {
            targetFormats(TargetFormat.Dmg)
            modules("java.sql")
            packageName = "TOE"
            packageVersion = "1.0.0"
            description = "Современная версия учебной программы ТЕСТ"
            macOS {
                bundleID = "ru.toe.reborn"
            }
        }
    }
}
