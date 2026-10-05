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
include(":features:question-review")
include(":androidApp")
include(":desktopApp")
