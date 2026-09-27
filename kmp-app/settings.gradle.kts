pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "electro-scholar"
include(":shared")
include(":features:question-bank")
include(":androidApp")
include(":desktopApp")
