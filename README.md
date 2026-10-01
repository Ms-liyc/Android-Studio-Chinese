<div align="center">

<img src="docs/images/logo.png" alt="屿宸网络科技工作室" width="480" />

# Android Studio 简体中文语言包

扫描 Android Studio **全量界面词条**，融合 JetBrains 官方中文基线与 Android 专有翻译，一键安装即可将菜单、工具窗口、设置面板、检查描述等切换为简体中文。

✨ **当前版本 1.0.0**

IntelliJ Language Pack · 7600+ 界面资源 · 1460 消息包 · 6140 描述文件 · Android Studio 2024.1 ~ 2026.1

</div>

---

## 项目亮点

| | |
|---|---|
| 🎨 **全量汉化** | 覆盖 IDE 菜单、工具栏、设置、对话框、检查描述、意图动作、文件模板等 7600+ 项界面资源 |
| 🔒 **非侵入式安装** | 标准插件安装，无需管理员权限，不修改 Android Studio 安装目录 |
| 🌏 **设置全覆盖** | 外观、编辑器、构建、Gradle、Android SDK、模拟器等设置面板完整中文化 |
| 📦 **开箱即用** | 安装插件 → 切换语言 → 重启，三步完成汉化 |
| 🪄 **版本兼容** | 兼容 Android Studio 2024.1（241）至 2026.1（262）多个版本 |
| 🖥️ **官方语言切换** | 通过 IDE 内置 Language and Region 设置切换，与 JetBrains 官方语言包机制一致 |
| 📋 **持续维护** | 由 **屿宸网络科技工作室** 维护，欢迎提交 Issue 反馈翻译问题 |

---

<div align="center">

![Version](https://img.shields.io/badge/版本-1.0.0-blue)
![Type](https://img.shields.io/badge/类型-Language%20Pack-green)
![License](https://img.shields.io/badge/许可证-MIT-lightgrey)
![Admin](https://img.shields.io/badge/管理员权限-不需要-green)
![Locale](https://img.shields.io/badge/语言-zh--CN-orange)
![GitHub Stars](https://img.shields.io/github/stars/Ms-liyc/Android-Studio-Chinese?style=social)
![Issues](https://img.shields.io/github/issues/Ms-liyc/Android-Studio-Chinese)

</div>

---

> 本插件仅对 Android Studio 界面进行本地化，不修改 IDE 核心程序与项目代码。

> ⚠️ **注意**：部分第三方插件或硬编码文本可能无法翻译；安装后需**完全重启** Android Studio（非仅重载窗口）才能生效。

---

## 安装方法

### 方式一：从 Release 下载（推荐）

1. 前往 [Releases](https://github.com/Ms-liyc/Android-Studio-Chinese/releases) 下载最新 `.zip` 语言包
2. 打开 Android Studio → **设置** → **插件** → **从磁盘安装插件**
3. 选择下载的 zip 文件，点击 **确定**
4. **重启** Android Studio
5. 打开 **设置 → 外观与行为 → 系统设置 → Language and Region**
6. 将 **Language** 设置为 **Chinese（简体中文）**，再次 **重启**

### 方式二：自行构建

```bash
# 克隆仓库
git clone https://github.com/Ms-liyc/Android-Studio-Chinese.git
cd Android-Studio-Chinese

# 方式 A：简易打包（推荐，仅需 Python 或 JDK）
.\scripts\package.ps1

# 方式 B：Gradle 构建（需要 JDK 21+ 和 Gradle Wrapper）
./gradlew buildPlugin

# 安装 build/distributions/ 下的 zip 文件
```

---

## 使用截图

安装并切换语言后，Android Studio 界面将显示为简体中文，包括：

- 顶部菜单栏（文件、编辑、视图、导航、代码、重构、构建、运行…）
- 左侧项目面板与工具窗口
- 设置对话框全部分类
- Gradle、SDK Manager、AVD Manager 等 Android 工具
- 代码检查与重构提示

---

## 兼容版本

| Android Studio 版本 | 构建号 | 支持状态 |
|---------------------|--------|----------|
| 2024.1.x | 241.x | ✅ 支持 |
| 2024.2.x | 242.x | ✅ 支持 |
| 2024.3.x | 243.x | ✅ 支持 |
| 2025.x | 251.x ~ 253.x | ✅ 支持 |
| 2026.1.x | 261.x ~ 262.x | ✅ 支持 |

---

## 项目结构

```
├── src/main/resources/          # 汉化资源（7600+ 文件）
│   ├── META-INF/plugin.xml      # 插件描述
│   ├── messages/                # 消息包（1450+ .properties）
│   ├── inspectionDescriptions/  # 检查描述
│   ├── intentionDescriptions/   # 意图描述
│   └── fileTemplates/           # 文件模板描述
├── tools/translate_tool.py      # 翻译维护工具链
├── translations/                # 翻译工作目录
├── docs/images/logo.png         # 项目 Logo
└── build.gradle.kts             # 构建配置
```

---

## 贡献翻译

欢迎通过 [GitHub Issues](https://github.com/Ms-liyc/Android-Studio-Chinese/issues) 反馈翻译错误或提交改进建议。

如需参与维护，请参考 `tools/translate_tool.py` 中的翻译工作流：

```powershell
# 提取新版 AS 英文资源
.\scripts\workflow.ps1 extract -StudioPath "C:\Program Files\Android\Android Studio"

# 合并已有翻译
.\scripts\merge-version.ps1 -FromDir translations\en-new -Backup

# 检查进度并构建
.\scripts\workflow.ps1 check
.\scripts\workflow.ps1 build
```

---

## 开发者

<div align="center">

**屿宸网络科技工作室**

YUCHEN NETWORK TECHNOLOGY STUDIO

Android Studio 汉化组

[GitHub](https://github.com/Ms-liyc/Android-Studio-Chinese) · [反馈问题](https://github.com/Ms-liyc/Android-Studio-Chinese/issues)

</div>

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

翻译内容基于 JetBrains 官方中文语言包及社区贡献，仅供学习与交流使用。
