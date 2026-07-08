# Android APK 构建报告

> 状态：**APK 构建成功**  
> 记录时间：2026-07-09  
> 项目：`UniMatch` / `apps/mobile`

---

## 1. 构建结果

- **APK 文件**：`apps/mobile/android/app/build/outputs/apk/release/app-release.apk`
- **本地副本**：`apps/mobile/dist-mobile/unimatch-release.apk`
- **文件大小**：约 62 MB
- **构建状态**：`BUILD SUCCESSFUL`（Gradle `assembleRelease`）
- **构建时间**：约 2 分 47 秒（缓存后）

---

## 2. 已完成的移动端工作

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
- `npx tsc --noEmit` 类型检查通过。

---

## 3. 关键环境信息

| 依赖 | 版本 / 路径 |
|------|-------------|
| JDK | 17 (`/opt/homebrew/opt/openjdk@17`) |
| Android SDK | `/Users/azuma/Library/Android/sdk` |
| Android Build Tools | 35.0.0 / 34.0.0 |
| Android Platform | API 35 |
| Android NDK | 26.1.10909125 (`android-ndk-r26b`) |
| CMake | 3.22.1 |
| Gradle | 8.10.2 |
| Expo | ~52.0.0 |
| React Native | 0.76.3 |

---

## 4. 构建过程中解决的主要问题

### 4.1 依赖版本对齐

`@expo/vector-icons` 的 `peerDependencies` 中 `expo-font` 为 `*`，导致 npm 安装了最新的 `expo-font@57.0.0`，与 `expo-modules-core@2.2.3` 不兼容，出现 `Plugin [id: 'expo-module-gradle-plugin'] was not found` 错误。

解决方案：在 `apps/mobile/package.json` 中显式锁定 Expo SDK 52 的配套版本：

```json
"expo-font": "~13.0.4",
"expo-asset": "~11.0.5"
```

### 4.2 Kotlin 版本对齐

`expo-modules-core` 自带的 Compose Compiler 插件要求 Kotlin 1.9.25，而 React Native 0.76 默认版本 catalog 使用 Kotlin 1.9.24，导致编译失败。

解决方案：在 `apps/mobile/android/build.gradle` 的 `buildscript` 依赖中显式指定 Kotlin Gradle 插件版本：

```groovy
classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:${rootProject.ext.kotlinVersion}")
```

并在 `gradle.properties` 中设置：

```properties
android.kotlinVersion=1.9.25
```

### 4.3 NDK 下载与安装

项目要求 NDK 26.1.10909125（对应 `android-ndk-r26b`）。由于 Google 官方下载包体积较大（约 939 MB），在 macOS 上通过 `curl -C -` 分段续传完成下载，解压后放到 `ndk/26.1.10909125` 目录，并创建 `source.properties`：

```properties
Pkg.Revision=26.1.10909125
```

### 4.4 网络代理问题

本地环境 `http_proxy`/`https_proxy` 指向一个未运行的本地代理（`127.0.0.1:7890`），导致 Expo prebuild、Gradle wrapper 下载和 npm 安装失败。在相关命令前执行 `unset all_proxy http_proxy https_proxy` 后恢复正常。

---

## 5. 如何重新构建 APK

在已配置好 JDK 17 和 Android SDK 的机器上：

```bash
cd /path/to/unimatch/apps/mobile
unset all_proxy http_proxy https_proxy
npm install
npx expo prebuild --platform android
cd android
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export ANDROID_HOME=/Users/azuma/Library/Android/sdk
./gradlew --no-daemon assembleRelease
```

APK 输出：

```
android/app/build/outputs/apk/release/app-release.apk
```

或使用仓库脚本（已包含 JDK/SKD 自动检测）：

```bash
cd /path/to/unimatch/apps/mobile
bash scripts/install-android-sdk.sh
```

---

## 6. 使用 GitHub Actions / EAS 云构建

- `.github/workflows/android-apk.yml` 已配置，可在仓库启用 GitHub Actions 后自动构建 APK 并推送到 `apk-release` 分支。
- 也可以使用 Expo EAS：安装 `eas-cli` 后运行 `eas build --platform android --profile preview`。

---

## 7. 相关文件

- `apps/mobile/scripts/install-android-sdk.sh`
- `.github/workflows/android-apk.yml`
- `apps/mobile/package.json`
- `apps/mobile/app.json`
- `apps/mobile/android/build.gradle`
- `apps/mobile/android/gradle.properties`

---

> 注意：APK 文件约 62 MB，不适合直接提交到 Git。请使用 GitHub Release 附件或网盘/IM 分发。
