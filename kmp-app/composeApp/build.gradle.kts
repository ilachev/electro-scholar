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
    from(exportedDatabase.file("question-bank.sqlite")) {
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
        create("QuestionBankDatabase") {
            packageName.set("io.github.ilachev.electroscholar.data")
        }
    }
}

compose.desktop {
    application {
        mainClass = "io.github.ilachev.electroscholar.app.MainKt"

        nativeDistributions {
            targetFormats(TargetFormat.Dmg)
            modules("java.sql")
            packageName = "ElectroScholar"
            packageVersion = "1.0.0"
            description = "Electrical engineering learning and circuit analysis"
            macOS {
                bundleID = "io.github.ilachev.electroscholar"
            }
        }
    }
}
