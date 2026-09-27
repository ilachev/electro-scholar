import org.jetbrains.compose.desktop.application.dsl.TargetFormat

val appVersion = providers.fileContents(
    rootProject.layout.projectDirectory.file("../version.txt")
).asText.map(String::trim)

plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.compose.multiplatform)
    alias(libs.plugins.compose.compiler)
}

kotlin {
    jvmToolchain(21)
}

dependencies {
    implementation(project(":shared"))
    implementation(compose.desktop.currentOs)
}

compose.desktop {
    application {
        mainClass = "io.github.ilachev.electroscholar.app.MainKt"

        nativeDistributions {
            targetFormats(TargetFormat.Dmg, TargetFormat.Msi, TargetFormat.Deb)
            modules("java.sql")
            packageName = "ElectroScholar"
            packageVersion = appVersion.get()
            description = "Electrical engineering learning and circuit analysis"
            vendor = "ElectroScholar contributors"

            linux {
                packageName = "electro-scholar"
                shortcut = true
                debMaintainer = "ilachev@users.noreply.github.com"
            }

            macOS {
                bundleID = "io.github.ilachev.electroscholar"
            }

            windows {
                menu = true
                shortcut = true
                upgradeUuid = "b2955705-eb57-46c8-a4d3-7168955c1216"
            }
        }
    }
}
