import org.jetbrains.intellij.platform.gradle.TestFrameworkType

plugins {
    id("org.jetbrains.kotlin.jvm")
    id("org.jetbrains.intellij.platform")
}

group = providers.gradleProperty("group").get()
version = providers.gradleProperty("version").get()

kotlin {
    jvmToolchain(21)
}

intellijPlatform {
    pluginConfiguration {
        id = "com.yuchen.androidstudio.chinese"
        name = "Android Studio 简体中文语言包 / 屿宸汉化组"
        vendor {
            name = "屿宸网络科技工作室"
            url = "https://github.com/Ms-liyc/Android-Studio-Chinese"
        }
        description = """
            Android Studio 简体中文语言包，由屿宸网络科技工作室维护。
            覆盖 IDE 全量界面资源，安装后在 Language and Region 中选择 Chinese 即可使用。
        """.trimIndent()
        changeNotes = """
            1.0.0 - 首发版本，完整汉化 Android Studio 界面
        """.trimIndent()

        ideaVersion {
            sinceBuild = providers.gradleProperty("pluginSinceBuild")
            untilBuild = providers.gradleProperty("pluginUntilBuild")
        }
    }
}

dependencies {
    intellijPlatform {
        androidStudio(providers.gradleProperty("androidStudioVersion"))
        bundledPlugin("org.jetbrains.android")
        testFramework(TestFrameworkType.Platform)
    }
}

tasks {
    buildSearchableOptions {
        enabled = false
    }
}
