#!/usr/bin/env bash
# Install Android SDK and build UniMatch release APK (macOS/Linux)
# Run from project root: bash apps/mobile/scripts/install-android-sdk.sh

set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SDK_DIR="$HOME/.android-sdk"
CMDLINE_TOOLS_DIR="$SDK_DIR/cmdline-tools"
LATEST_DIR="$CMDLINE_TOOLS_DIR/latest"
ZIP_URL="https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip"
ZIP_FILE="/tmp/commandlinetools-mac.zip"

# Prefer Java 17 for Android Gradle compatibility
if [ -d /opt/homebrew/opt/openjdk@17 ]; then
  export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
elif [ -d /usr/local/opt/openjdk@17 ]; then
  export JAVA_HOME=/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
fi

echo "Java: $(java -version 2>&1 | head -n 1)"

mkdir -p "$CMDLINE_TOOLS_DIR"

if [ ! -d "$LATEST_DIR" ]; then
  echo "下载 Android SDK 命令行工具..."
  curl -L -o "$ZIP_FILE" "$ZIP_URL"
  unzip -q "$ZIP_FILE" -d "$CMDLINE_TOOLS_DIR"
  mv "$CMDLINE_TOOLS_DIR/cmdline-tools" "$LATEST_DIR"
  rm "$ZIP_FILE"
fi

export ANDROID_HOME="$SDK_DIR"
export PATH="$ANDROID_HOME/platform-tools:$LATEST_DIR/bin:$PATH"

mkdir -p "$HOME/.android"
touch "$HOME/.android/repositories.cfg"

echo "接受许可证并安装 SDK 包..."
yes | sdkmanager --licenses > /dev/null 2>&1 || true
sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0" "ndk;27.0.11718014"

echo "安装 npm 依赖..."
cd "$PROJECT_ROOT/apps/mobile"
npm install

echo "Expo prebuild..."
npx expo prebuild --platform android

echo "构建 release APK..."
cd "$PROJECT_ROOT/apps/mobile/android"
./gradlew assembleRelease

echo "APK 输出路径："
find "$PROJECT_ROOT/apps/mobile/android/app/build/outputs/apk/release" -name "*.apk" -type f
