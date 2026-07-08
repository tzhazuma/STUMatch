#!/usr/bin/env bash
# Build UniMatch Android APK locally (macOS/Linux)
# Assumes JDK 17 and Android SDK (with NDK r26b) are already installed.

set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MOBILE_DIR="$PROJECT_ROOT/apps/mobile"

# Avoid stale local proxy settings that break downloads/unpacking.
unset all_proxy http_proxy https_proxy ALL_PROXY HTTP_PROXY HTTPS_PROXY 2>/dev/null || true

# Prefer JDK 17 for Android Gradle compatibility
if [ -d /opt/homebrew/opt/openjdk@17 ]; then
  export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
elif [ -d /usr/local/opt/openjdk@17 ]; then
  export JAVA_HOME=/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
elif [ -n "$JAVA_HOME" ] && [[ "$JAVA_HOME" == *"jdk-17"* ]]; then
  : # keep existing JDK 17
else
  echo "Warning: JAVA_HOME does not point to JDK 17. Android Gradle may fail."
fi

if [ -z "$ANDROID_HOME" ]; then
  if [ -d "$HOME/Library/Android/sdk" ]; then
    export ANDROID_HOME="$HOME/Library/Android/sdk"
  elif [ -d "$HOME/Android/Sdk" ]; then
    export ANDROID_HOME="$HOME/Android/Sdk"
  else
    echo "Error: ANDROID_HOME not set and no default Android SDK found."
    exit 1
  fi
fi
export ANDROID_SDK_ROOT="$ANDROID_HOME"

echo "Java: $(java -version 2>&1 | head -n 1)"
echo "ANDROID_HOME: $ANDROID_HOME"

cd "$MOBILE_DIR"

echo "Installing npm dependencies..."
npm install

echo "Running Expo prebuild..."
npx expo prebuild --platform android

echo "Applying Gradle compatibility fixes..."
# 1. Force Kotlin Gradle plugin version to match Compose compiler (1.9.25).
if ! grep -q 'org.jetbrains.kotlin:kotlin-gradle-plugin:\${rootProject.ext.kotlinVersion}' android/build.gradle; then
  sed -i.bak "s|classpath('org.jetbrains.kotlin:kotlin-gradle-plugin')|classpath(\"org.jetbrains.kotlin:kotlin-gradle-plugin:\${rootProject.ext.kotlinVersion}\")|" android/build.gradle
fi
# 2. Ensure Kotlin version property is set in gradle.properties.
if ! grep -q '^android.kotlinVersion=' android/gradle.properties; then
  echo "" >> android/gradle.properties
  echo "android.kotlinVersion=1.9.25" >> android/gradle.properties
fi

echo "Building release APK..."
cd android
./gradlew --no-daemon assembleRelease

APK_PATH="$MOBILE_DIR/android/app/build/outputs/apk/release/app-release.apk"
if [ -f "$APK_PATH" ]; then
  mkdir -p "$MOBILE_DIR/dist-mobile"
  cp "$APK_PATH" "$MOBILE_DIR/dist-mobile/unimatch-release.apk"
  echo ""
  echo "APK build succeeded!"
  echo "  APK: $APK_PATH"
  echo "  Copy: $MOBILE_DIR/dist-mobile/unimatch-release.apk"
else
  echo "APK build failed: $APK_PATH not found"
  exit 1
fi
