plugins {
    kotlin("multiplatform") version "2.4.20" apply false
    id("org.jetbrains.compose") version "1.12.1" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.4.20" apply false
    id("app.cash.sqldelight") version "2.3.2" apply false
}

allprojects {
    dependencyLocking {
        lockAllConfigurations()
        ignoredDependencies.add("org.jetbrains.compose.desktop:desktop-jvm-*")
        ignoredDependencies.add("org.jetbrains.skiko:skiko-awt-runtime-*")
    }
}
