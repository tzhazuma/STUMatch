# Android APK 构建报告

> 状态：Android SDK 安装因网络下载超时而未完成，APK 尚未生成。  
> 记录时间：2026-07-08  
> 项目：`UniMatch` / `apps/mobile`

---

## 1. 已完成的移动端工作

- 使用 Expo + React Native + TypeScript 搭建了移动端项目结构。
- 实现了以下页面与功能：
  - 登录 / 注册（`LoginScreen`、`RegisterScreen`）
  - 发现页（`DiscoveryScreen`）
  - 用户详情（`UserDetailScreen`）
  - 个人资料（`ProfileScreen`）
  - 好友（`FriendsScreen`）
  - 聊天（`ChatScreen`）
  - 问卷（`QuestionnaireScreen`）
- 已对接后端 API，与 Web 端共用同一套接口。
- 运行了 `npx tsc --noEmit`，TypeScript 类型检查通过。

---

## 2. APK 编译阻塞原因

当前环境尚未安装 Android SDK，尝试通过 `apps/mobile/scripts/install-android-sdk.sh` 自动安装命令行工具并编译 APK。该脚本需要：

1. 下载 Android SDK Command Line Tools（约 100 MB+）。
2. 使用 `sdkmanager` 下载 `platform-tools`、`build-tools`、Android 平台（API 34）等组件。
3. 编译本地原生依赖（如 `expo-modules-core`）并生成 APK。

由于中国大陆网络下载 Android SDK 命令行工具速度极慢，后台任务在 600 秒超时限制内未能完成下载。因此：

- Android SDK 未成功安装。
- APK 未生成。

---

## 3. 如何在本地继续生成 APK

### 3.1 方式一：使用本仓库脚本（推荐有稳定网络或镜像时）

```bash
cd /path/to/unimatch/apps/mobile
bash scripts/install-android-sdk.sh
```

脚本会：
- 自动检测 `JAVA_HOME`（需要 JDK 17+）。
- 下载 Android SDK 命令行工具到 `~/Android/Sdk`。
- 安装必要的 SDK 组件。
- 设置 `ANDROID_HOME` 与 `ANDROID_SDK_ROOT`。
- 执行 `npx expo run:android --variant release` 生成 APK。

> 提示：如果下载慢，可以先把 `https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip` 手动下载并放到 `~/Android/Sdk` 目录，再运行脚本。

### 3.2 方式二：使用 Expo EAS（不需要本地 Android SDK）

如果你已经在 Expo 账号下配置了项目，可以使用 EAS 云服务构建：

```bash
# 安装 EAS CLI
npm install -g eas-cli

# 登录并配置项目
cd apps/mobile
eas login
eas build:configure

# 构建 Android APK
eas build --platform android --profile preview
```

EAS 会在云端完成构建并返回 APK 下载链接。

### 3.3 方式三：使用 Android Studio

1. 安装 Android Studio。
2. 打开 `apps/mobile/android`（如不存在，先运行 `npx expo prebuild`）。
3. 在 Android Studio 中选择 **Build → Build Bundle(s) / APK(s) → Build APK(s)**。

---

## 4. 环境要求

| 依赖 | 版本要求 |
|------|----------|
| Node.js | 18+ |
| JDK | 17+ |
| Android SDK | API 34（Android 14） |
| Expo CLI | 通过 `npx expo` 使用 |

---

## 5. 下一步建议

1. 在下载速度较快的环境（如境外服务器、校园网）运行安装脚本。
2. 或者优先使用 EAS 云构建，避免本地 Android SDK 环境配置。
3. 生成 APK 后，建议补充 `.github/workflows/mobile-build.yml` 实现 CI 自动构建。

---

## 6. 相关脚本与文件

- `apps/mobile/scripts/install-android-sdk.sh`：Android SDK 安装与 APK 构建脚本。
- `apps/mobile/package.json`：Expo 与 React Native 依赖。
- `apps/mobile/app.json`：Expo 应用配置。

---

> 注意：本报告仅记录当前构建阻塞状态，后续在具备网络条件的环境中可继续完成 APK 编译。
