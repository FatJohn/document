# Flutter 多環境配置完整指南

## 概述

### 什麼是多環境配置

多環境配置讓你能在同一個 App 專案中建立不同的環境版本（如 Development、Staging、Production），每個環境可以有：

- 不同的 **API 端點**
- 不同的 **App 名稱**（例如：「MyApp [DEV]」vs「MyApp」）
- 不同的 **Bundle/Application ID**（可同時安裝在同一裝置）
- 不同的 **App Icon** 和 **Launch Image**
- 不同的 **Firebase 專案配置**
- 不同的 **功能開關**（例如：開發環境顯示除錯工具）

### 為什麼需要多環境

1. **開發與生產環境隔離**：避免測試資料污染正式環境
2. **同時安裝多個版本**：開發人員可在同一裝置安裝 dev 和 prod 版本進行比對
3. **視覺區別**：透過不同的 icon 和 app 名稱快速識別環境
4. **安全性**：正式環境關閉除錯功能和敏感日誌
5. **CI/CD 自動化**：不同 branch 自動建置對應環境

### 本指南涵蓋的配置項目

- Dart Define 配置（環境變數注入）
- Android 多環境配置（Application ID、App Icon、Firebase）
- iOS 多環境配置（Bundle ID、App Icon、Launch Image、Firebase）
- 自動化腳本設計
- CI/CD 整合

---

## 核心機制

### 1. Dart Define 配置 🔷 Flutter 專屬

Flutter 提供 `--dart-define-from-file` 參數，讓你從 JSON 檔案載入環境變數。

#### 使用 `--dart-define-from-file`

建立環境配置檔案：

**`build_config/development.json`**
```json
{
  "ENV": "development",
  "ENABLE_DEVELOPER_LOGGER": true,
  "LOG_LEVEL": "debug",
  "API_BASE_URL": "https://api.example.com/dev",
  "ASSETS_URL": "https://assets.example.com/dev"
}
```

**`build_config/production.json`**
```json
{
  "ENV": "production",
  "ENABLE_DEVELOPER_LOGGER": false,
  "LOG_LEVEL": "info",
  "API_BASE_URL": "https://api.example.com",
  "ASSETS_URL": "https://assets.example.com"
}
```

#### 建置指令

```bash
# Development
flutter run --dart-define-from-file=build_config/development.json

# Production
flutter build apk --dart-define-from-file=build_config/production.json
```

#### 在 Dart 程式碼中讀取環境變數

```dart
class Environment {
  static const String env = String.fromEnvironment('ENV', defaultValue: 'development');
  static const bool enableDevLogger = bool.fromEnvironment('ENABLE_DEVELOPER_LOGGER', defaultValue: false);
  static const String apiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');

  static bool get isDevelopment => env == 'development';
  static bool get isProduction => env == 'production';
}
```

---

### 2. Android 多環境配置

#### 2.1 Application ID Suffix ⭐️ 通用技巧

在 `android/app/build.gradle.kts` 中設定 `applicationIdSuffix`：

```kotlin
android {
    defaultConfig {
        applicationId = "com.example.myapp"
        applicationIdSuffix = ".dev"  // Development: com.example.myapp.dev
    }
}
```

**原理說明**：
- Android 使用 Application ID 識別不同的 App
- 加上 suffix 後，development 和 production 版本視為不同的 App
- 可以同時安裝在同一裝置上

**適用場景**：
- ⭐️ **原生 Android 開發**
- ⭐️ **React Native**
- ⭐️ **Flutter**
- ⭐️ **任何使用 Gradle 建置的 Android 專案**

#### 2.2 App 名稱動態設定 ⭐️ 通用技巧

使用 Gradle 的 `resValue` 機制動態設定 app 名稱：

**`build.gradle.kts`**
```kotlin
android {
    defaultConfig {
        resValue("string", "app_name", "MyApp [DEV]")
    }
}
```

**`AndroidManifest.xml`**
```xml
<application
    android:label="@string/app_name">
</application>
```

**適用場景**：
- ⭐️ **原生 Android 開發**
- ⭐️ **React Native**
- ⭐️ **Flutter**

#### 2.3 App Icon 切換 ⭐️ 通用技巧

使用 Gradle 的 `sourceSets` 機制：

**`build.gradle.kts`**
```kotlin
android {
    sourceSets {
        getByName("main") {
            val envSourceDir = if (isDevelopment()) "src/dev" else "src/prod"
            res.srcDirs("src/main/res", "$envSourceDir/res")
        }
    }
}
```

**資源目錄結構**：
```text
android/app/src/
├── dev/res/
│   └── mipmap-*/
│       ├── ic_launcher.png          # Dev 環境的 icon
│       ├── ic_launcher_foreground.png
│       └── ic_launcher_background.png
└── prod/res/
    └── mipmap-*/
        ├── ic_launcher.png          # Prod 環境的 icon
        ├── ic_launcher_foreground.png
        └── ic_launcher_background.png
```

**優點**：
- Build 時自動選擇對應目錄
- 不需要手動複製檔案
- 資源隔離清晰

**適用場景**：
- ⭐️ **原生 Android 開發**
- ⭐️ **React Native**
- ⭐️ **Flutter**

#### 2.4 Firebase 配置切換 ⭐️ 通用技巧

使用 Gradle Task 在 build 前自動複製對應的 `google-services.json`：

**`build.gradle.kts`**
```kotlin
tasks.register("copyGoogleServices") {
    doLast {
        val sourceDir = if (isDevelopment()) "config/dev" else "config/prod"
        val sourceFile = file("$sourceDir/google-services.json")
        val targetFile = file("google-services.json")

        if (sourceFile.exists()) {
            sourceFile.copyTo(targetFile, overwrite = true)
            println("Copied google-services.json from $sourceDir")
        } else {
            throw GradleException("google-services.json not found in $sourceDir")
        }
    }
}

// 確保在處理 google-services 之前先複製檔案
tasks.whenTaskAdded {
    if (name == "processDebugGoogleServices" || name == "processReleaseGoogleServices") {
        dependsOn("copyGoogleServices")
    }
}
```

**檔案結構**：
```text
android/app/
├── config/
│   ├── dev/google-services.json      # Dev 環境的 Firebase 配置
│   └── prod/google-services.json     # Prod 環境的 Firebase 配置
└── google-services.json              # 動態生成（已加入 .gitignore）
```

**適用場景**：
- ⭐️ **原生 Android 開發**
- ⭐️ **React Native**
- ⭐️ **Flutter**

#### 2.5 讀取 Flutter Dart Define 🔷 Flutter 專屬

Android Gradle 可以讀取 Flutter 傳遞的 `dart-defines` 參數：

**`build.gradle.kts`**
```kotlin
import java.util.Base64

// 定義預設配置（Development 環境）
var dartEnvironmentVariables = mutableMapOf(
    "APP_ENVIRONMENT" to "development",
    "APP_CONFIG_SUFFIX" to ".dev",
    "APP_CONFIG_NAME" to "MyApp [DEV]"
)

// 注入 dart-define 變數
if (project.hasProperty("dart-defines")) {
    val dartDefines = project.property("dart-defines") as String
    dartDefines.split(",").forEach { entry ->
        val decodedEntry = String(Base64.getDecoder().decode(entry))
        val pair = decodedEntry.split("=", limit = 2)
        if (pair.size == 2 && pair[0] == "ENV") {
            when (pair[1]) {
                "development" -> {
                    dartEnvironmentVariables["APP_ENVIRONMENT"] = "development"
                    dartEnvironmentVariables["APP_CONFIG_SUFFIX"] = ".dev"
                    dartEnvironmentVariables["APP_CONFIG_NAME"] = "MyApp [DEV]"
                }
                "production" -> {
                    dartEnvironmentVariables["APP_ENVIRONMENT"] = "production"
                    dartEnvironmentVariables["APP_CONFIG_SUFFIX"] = ""
                    dartEnvironmentVariables["APP_CONFIG_NAME"] = "MyApp"
                }
            }
        }
    }
}

// 環境判斷助手函數
fun isDevelopment(): Boolean {
    return dartEnvironmentVariables["APP_ENVIRONMENT"] == "development"
}

android {
    defaultConfig {
        applicationId = "com.example.myapp"
        applicationIdSuffix = dartEnvironmentVariables["APP_CONFIG_SUFFIX"]
        resValue("string", "app_name", dartEnvironmentVariables["APP_CONFIG_NAME"] ?: "MyApp")
    }

    sourceSets {
        getByName("main") {
            val envSourceDir = if (isDevelopment()) "src/dev" else "src/prod"
            res.srcDirs("src/main/res", "$envSourceDir/res")
        }
    }
}
```

**原理說明**：
- Flutter 在執行 `flutter build` 時會將 `dart-defines` 傳遞給 Gradle
- `dart-defines` 是 Base64 編碼的 key=value 對，以逗號分隔
- Gradle 解碼後根據 `ENV` 值設定對應的配置

---

### 3. iOS 多環境配置

#### 3.1 Bundle ID Suffix ⭐️ 通用技巧

iOS 使用 **xcconfig 檔案** 來設定 Bundle ID suffix。

**`ios/Flutter/Debug.xcconfig`**
```c
#include "AppConfig.xcconfig"
#include "Generated.xcconfig"
```

**`ios/Flutter/Release.xcconfig`**
```c
#include "AppConfig.xcconfig"
#include "Generated.xcconfig"
```

**`ios/Flutter/AppConfig.xcconfig`（動態生成）**
```properties
APP_CONFIG_SUFFIX=.dev
APP_CONFIG_NAME=MyApp [DEV]
APP_CONFIG_ICON_NAME=AppIcon-Dev
APP_CONFIG_LAUNCH_IMAGE=LaunchImage-Dev
```

**`ios/Runner.xcodeproj/project.pbxproj`**
```properties
PRODUCT_BUNDLE_IDENTIFIER = "com.example.myapp$(APP_CONFIG_SUFFIX)";
```

**原理說明**：
- xcconfig 檔案提供 Xcode 建置變數
- 在 Bundle Identifier 中引用 `$(APP_CONFIG_SUFFIX)` 變數
- Development: `com.example.myapp.dev`
- Production: `com.example.myapp`（suffix 為空字串）

**適用場景**：
- ⭐️ **原生 iOS 開發**
- ⭐️ **React Native**
- ⭐️ **Flutter**

#### 3.2 App 名稱動態設定 ⭐️ 通用技巧

在 `Info.plist` 中引用 xcconfig 變數：

**`ios/Runner/Info.plist`**
```xml
<key>CFBundleDisplayName</key>
<string>$(APP_CONFIG_NAME)</string>
```

**`AppConfig.xcconfig`**
```properties
APP_CONFIG_NAME=MyApp [DEV]
```

**適用場景**：
- ⭐️ **原生 iOS 開發**
- ⭐️ **React Native**
- ⭐️ **Flutter**

#### 3.3 App Icon 切換 ⭐️ 通用技巧

在 Xcode 中建立多個 AppIcon Set，透過 xcconfig 變數控制使用哪一個：

**資源目錄結構**：
```text
ios/Runner/Assets.xcassets/
├── AppIcon-Dev.appiconset/          # Dev 環境的 icon
│   ├── Contents.json
│   └── Icon-App-*.png
└── AppIcon-Prod.appiconset/         # Prod 環境的 icon
    ├── Contents.json
    └── Icon-App-*.png
```

**`AppConfig.xcconfig`**
```properties
APP_CONFIG_ICON_NAME=AppIcon-Dev
```

**Xcode 設定**：
在 Xcode 的 Build Settings 中設定：
```properties
ASSETCATALOG_COMPILER_APPICON_NAME = $(APP_CONFIG_ICON_NAME)
```

**適用場景**：
- ⭐️ **原生 iOS 開發**
- ⭐️ **React Native**
- ⭐️ **Flutter**

#### 3.4 Launch Image 切換 ⭐️ 通用技巧

Launch Image 的配置較複雜，因為 `LaunchScreen.storyboard` 無法直接引用環境變數。

**解決方案**：使用 Build Phase Script 動態複製對應的 launch image。

**資源目錄結構**：
```text
ios/Runner/Assets.xcassets/
├── LaunchImage-Dev.imageset/        # Dev 環境的 launch image
│   ├── Contents.json
│   └── *.png
├── LaunchImage-Prod.imageset/       # Prod 環境的 launch image
│   ├── Contents.json
│   └── *.png
└── LaunchImage.imageset/            # 動態生成（已加入 .gitignore）
    └── ...
```

**Build Phase Script**（`scripts/copy_launch_image.sh`）：
```bash
#!/bin/bash

# 讀取 xcconfig 中的 APP_CONFIG_LAUNCH_IMAGE 變數
LAUNCH_IMAGE_NAME="${APP_CONFIG_LAUNCH_IMAGE}"

if [ -z "$LAUNCH_IMAGE_NAME" ]; then
    echo "Error: APP_CONFIG_LAUNCH_IMAGE not set"
    exit 1
fi

# 複製對應的 imageset
SOURCE_DIR="${SRCROOT}/Runner/Assets.xcassets/${LAUNCH_IMAGE_NAME}.imageset"
TARGET_DIR="${SRCROOT}/Runner/Assets.xcassets/LaunchImage.imageset"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: $SOURCE_DIR not found"
    exit 1
fi

rm -rf "$TARGET_DIR"
cp -R "$SOURCE_DIR" "$TARGET_DIR"

echo "Copied launch image from $LAUNCH_IMAGE_NAME to LaunchImage"
```

**Xcode Build Phase 設定**：
1. 在 Xcode 中打開 Runner target 的 Build Phases
2. 新增 "Run Script" phase（必須在 "Run Script (Flutter build)" 之前）
3. 名稱設為 "Copy Launch Image"
4. Script 內容：
   ```bash
   "${SRCROOT}/../scripts/copy_launch_image.sh"
   ```

**`LaunchScreen.storyboard`** 引用通用的 `LaunchImage`：
```xml
<imageView image="LaunchImage" />
```

**適用場景**：
- ⭐️ **原生 iOS 開發**
- ⭐️ **React Native**
- ⭐️ **Flutter**

#### 3.5 Firebase 配置切換 ⭐️ 通用技巧

使用 Script 自動複製對應的 `GoogleService-Info.plist`：

**檔案結構**：
```text
ios/
├── config/
│   ├── Dev/GoogleService-Info.plist      # Dev 環境的 Firebase 配置
│   └── Prod/GoogleService-Info.plist     # Prod 環境的 Firebase 配置
└── Runner/
    └── GoogleService-Info.plist          # 動態生成（已加入 .gitignore）
```

**在生成配置的 script 中處理**（見 3.6）。

**適用場景**：
- ⭐️ **原生 iOS 開發**
- ⭐️ **React Native**
- ⭐️ **Flutter**

#### 3.6 動態生成 xcconfig ⭐️ 通用技巧

建立一個 Shell Script 來動態生成 `AppConfig.xcconfig`，並同時複製 Firebase 配置。

**`scripts/generate_app_config.sh`**
```bash
#!/bin/bash

set -e

ENV_NAME=${1:-development}

# 取得專案根目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 從 project.pbxproj 提取 base bundle identifier
PBXPROJ_PATH="$PROJECT_ROOT/ios/Runner.xcodeproj/project.pbxproj"
BASE_BUNDLE_ID=$(grep -m 1 'PRODUCT_BUNDLE_IDENTIFIER' "$PBXPROJ_PATH" | cut -d'"' -f2 | cut -d'$' -f1)

case "$ENV_NAME" in
    "development")
        APP_CONFIG_SUFFIX=".dev"
        APP_CONFIG_NAME="MyApp [DEV]"
        APP_CONFIG_ICON_NAME="AppIcon-Dev"
        APP_CONFIG_LAUNCH_IMAGE="LaunchImage-Dev"
        firebase_config="Dev/GoogleService-Info.plist"
        ;;
    "production")
        APP_CONFIG_SUFFIX=""
        APP_CONFIG_NAME="MyApp"
        APP_CONFIG_ICON_NAME="AppIcon-Prod"
        APP_CONFIG_LAUNCH_IMAGE="LaunchImage-Prod"
        firebase_config="Prod/GoogleService-Info.plist"
        ;;
    *)
        echo "error: Unknown environment $ENV_NAME" >&2
        exit 1
        ;;
esac

# 計算 Bundle ID
BUNDLE_ID="${BASE_BUNDLE_ID}${APP_CONFIG_SUFFIX}"

# 生成 AppConfig.xcconfig
cat > "$PROJECT_ROOT/ios/Flutter/AppConfig.xcconfig" << EOF
APP_CONFIG_SUFFIX=$APP_CONFIG_SUFFIX
APP_CONFIG_NAME=$APP_CONFIG_NAME
APP_CONFIG_ICON_NAME=$APP_CONFIG_ICON_NAME
APP_CONFIG_LAUNCH_IMAGE=$APP_CONFIG_LAUNCH_IMAGE
EOF

# 複製對應的 Firebase 配置
src_firebase_config="$PROJECT_ROOT/ios/config/$firebase_config"
if [ ! -f "$src_firebase_config" ]; then
    echo "error: Firebase config file not found: $src_firebase_config" >&2
    exit 1
fi
cp "$src_firebase_config" "$PROJECT_ROOT/ios/Runner/GoogleService-Info.plist"

echo "Generated AppConfig.xcconfig for environment: $ENV_NAME"
echo "BUNDLE_ID=$BUNDLE_ID"

# 匯出 BUNDLE_ID 到 CI 環境（如果在 CI 中執行）
if [ -n "$GITHUB_ENV" ]; then
  echo "BUNDLE_ID=$BUNDLE_ID" >> $GITHUB_ENV
fi
```

**使用方式**：
```bash
# Development
./scripts/generate_app_config.sh development

# Production
./scripts/generate_app_config.sh production
```

**為什麼不使用 Xcode Pre-build Action**

很多人會想在 Xcode 的 Build Phases 中加入 Pre-build Action 來執行 `generate_app_config.sh`，但這樣做有幾個問題：

1. **CI/CD 環境不一致**：
   - 在 CI/CD 中通常使用 `flutter build` 指令，而非直接用 Xcode build
   - Pre-build Action 只在透過 Xcode build 時執行
   - CI/CD 需要在 `flutter build` 之前手動執行 script

2. **環境參數傳遞困難**：
   - Pre-build Action 無法輕易接收外部環境變數
   - 需要額外的機制來告訴 script 要 build 哪個環境

3. **本地開發體驗不一致**：
   - 開發者可能使用 VS Code、Android Studio 或 Xcode
   - 只有 Xcode 會執行 Pre-build Action
   - 其他工具需要手動執行 script

**推薦做法**：
- **本地開發**：開發者在切換環境時手動執行 `./scripts/generate_app_config.sh <environment>`
- **CI/CD**：在 workflow 中明確執行 script，確保環境正確

這樣的設計讓配置流程清晰、可測試、可重用，且不依賴特定的 IDE 或建置工具。

**為什麼不使用 FlutterFire CLI**

FlutterFire CLI 提供 `flutterfire configure` 指令來自動產生 Firebase 配置，但在多環境配置中有以下限制：

1. **不支援動態環境切換**：
   - FlutterFire CLI 需要每次手動執行並選擇 Firebase 專案
   - 無法根據 build 指令自動切換配置

2. **配置重複且難以維護**：
   - 每個環境需要分別執行 `flutterfire configure`
   - 產生的配置檔案分散，不易統一管理

3. **CI/CD 整合複雜**：
   - 需要在 CI 中安裝 FlutterFire CLI
   - 需要處理 Firebase 認證
   - 執行時間較長

4. **Bundle ID 管理困難**：
   - FlutterFire CLI 會修改 Xcode 專案設定
   - 可能與自訂的 Bundle ID suffix 機制衝突

**手動管理的優勢**：
- ✅ 配置檔案版本控制在 `ios/config/` 目錄
- ✅ 透過簡單的 `cp` 指令切換配置
- ✅ 不需要額外的工具或認證
- ✅ CI/CD 執行快速且穩定
- ✅ 完全掌控配置切換邏輯

**適用場景**：
- ⭐️ **原生 iOS 開發**
- ⭐️ **React Native**
- ⭐️ **Flutter**

---

## 實作步驟

### Android 完整設定步驟

#### 步驟 1：建立環境配置檔案

```text
build_config/
├── development.json
└── production.json
```

#### 步驟 2：修改 `build.gradle.kts`

```kotlin
import java.util.Base64

// 定義預設配置
var dartEnvironmentVariables = mutableMapOf(
    "APP_ENVIRONMENT" to "development",
    "APP_CONFIG_SUFFIX" to ".dev",
    "APP_CONFIG_NAME" to "MyApp [DEV]"
)

// 讀取 dart-defines
if (project.hasProperty("dart-defines")) {
    val dartDefines = project.property("dart-defines") as String
    dartDefines.split(",").forEach { entry ->
        val decodedEntry = String(Base64.getDecoder().decode(entry))
        val pair = decodedEntry.split("=", limit = 2)
        if (pair.size == 2 && pair[0] == "ENV") {
            when (pair[1]) {
                "development" -> {
                    dartEnvironmentVariables["APP_ENVIRONMENT"] = "development"
                    dartEnvironmentVariables["APP_CONFIG_SUFFIX"] = ".dev"
                    dartEnvironmentVariables["APP_CONFIG_NAME"] = "MyApp [DEV]"
                }
                "production" -> {
                    dartEnvironmentVariables["APP_ENVIRONMENT"] = "production"
                    dartEnvironmentVariables["APP_CONFIG_SUFFIX"] = ""
                    dartEnvironmentVariables["APP_CONFIG_NAME"] = "MyApp"
                }
            }
        }
    }
}

fun isDevelopment() = dartEnvironmentVariables["APP_ENVIRONMENT"] == "development"

// 複製 Firebase 配置的 Task
tasks.register("copyGoogleServices") {
    doLast {
        val sourceDir = if (isDevelopment()) "config/dev" else "config/prod"
        val sourceFile = file("$sourceDir/google-services.json")
        val targetFile = file("google-services.json")
        sourceFile.copyTo(targetFile, overwrite = true)
    }
}

tasks.whenTaskAdded {
    if (name == "processDebugGoogleServices" || name == "processReleaseGoogleServices") {
        dependsOn("copyGoogleServices")
    }
}

android {
    defaultConfig {
        applicationId = "com.example.myapp"
        applicationIdSuffix = dartEnvironmentVariables["APP_CONFIG_SUFFIX"]
        resValue("string", "app_name", dartEnvironmentVariables["APP_CONFIG_NAME"] ?: "MyApp")
    }

    sourceSets {
        getByName("main") {
            val envSourceDir = if (isDevelopment()) "src/dev" else "src/prod"
            res.srcDirs("src/main/res", "$envSourceDir/res")
        }
    }
}
```

#### 步驟 3：建立資源目錄結構

```text
android/app/
├── config/
│   ├── dev/google-services.json
│   └── prod/google-services.json
└── src/
    ├── dev/res/mipmap-*/
    └── prod/res/mipmap-*/
```

#### 步驟 4：更新 `.gitignore`

```gitignore
# Android 動態生成的檔案
android/app/google-services.json
```

#### 步驟 5：驗證配置

```bash
# 測試 Development build
flutter build apk --dart-define-from-file=build_config/development.json

# 檢查生成的 APK Application ID
# 應該是 com.example.myapp.dev
```

---

### iOS 完整設定步驟

#### 步驟 1：建立環境配置檔案

```text
build_config/
├── development.json
└── production.json
```

#### 步驟 2：建立 xcconfig 檔案

**`ios/Flutter/Debug.xcconfig`**
```c
#include "AppConfig.xcconfig"
#include "Generated.xcconfig"
```

**`ios/Flutter/Release.xcconfig`**
```c
#include "AppConfig.xcconfig"
#include "Generated.xcconfig"
```

#### 步驟 3：修改 `project.pbxproj`

在 Xcode 中設定 Bundle Identifier：
```properties
PRODUCT_BUNDLE_IDENTIFIER = "com.example.myapp$(APP_CONFIG_SUFFIX)";
```

或直接編輯 `ios/Runner.xcodeproj/project.pbxproj`：
```properties
PRODUCT_BUNDLE_IDENTIFIER = "com.example.myapp$(APP_CONFIG_SUFFIX)";
```

#### 步驟 4：修改 `Info.plist`

```xml
<key>CFBundleDisplayName</key>
<string>$(APP_CONFIG_NAME)</string>
```

#### 步驟 5：建立資源目錄結構

```text
ios/
├── config/
│   ├── Dev/GoogleService-Info.plist
│   └── Prod/GoogleService-Info.plist
└── Runner/
    └── Assets.xcassets/
        ├── AppIcon-Dev.appiconset/
        ├── AppIcon-Prod.appiconset/
        ├── LaunchImage-Dev.imageset/
        └── LaunchImage-Prod.imageset/
```

#### 步驟 6：建立 `generate_app_config.sh`

參考 [3.6 動態生成 xcconfig](#36-動態生成-xcconfig-️-通用技巧)。

#### 步驟 7：建立 `copy_launch_image.sh`

參考 [3.4 Launch Image 切換](#34-launch-image-切換-️-通用技巧)。

#### 步驟 8：新增 Xcode Build Phase

1. 打開 Xcode 專案
2. 選擇 Runner target → Build Phases
3. 點擊 "+" → "New Run Script Phase"
4. 名稱設為 "Copy Launch Image"
5. 將此 phase 拖曳到 "Run Script (Flutter build)" 之前
6. Script 內容：
   ```bash
   "${SRCROOT}/../scripts/copy_launch_image.sh"
   ```

#### 步驟 9：設定 Xcode Build Settings

在 Xcode 的 Build Settings 中搜尋 "ASSETCATALOG_COMPILER_APPICON_NAME"，設定為：
```text
$(APP_CONFIG_ICON_NAME)
```

#### 步驟 10：更新 `.gitignore`

```gitignore
# iOS 動態生成的檔案
ios/Flutter/AppConfig.xcconfig
ios/Runner/GoogleService-Info.plist
ios/Runner/Assets.xcassets/LaunchImage.imageset/
```

#### 步驟 11：驗證配置

```bash
# 測試 Development build
./scripts/generate_app_config.sh development
flutter build ios --dart-define-from-file=build_config/development.json

# 檢查生成的 Bundle ID
# 應該是 com.example.myapp.dev
```

---

### 整合 CI/CD

#### GitHub Actions 範例

```yaml
name: Build and Deploy

on:
  push:
    branches: [main, staging]

jobs:
  build-android:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Flutter
        uses: subosito/flutter-action@v2

      - name: Get dependencies
        run: flutter pub get

      - name: Build APK (Development)
        if: github.ref == 'refs/heads/staging'
        env:
          KEY_STORE_FILE_PATH: ${{ secrets.KEY_STORE_FILE_PATH }}
          KEY_STORE_PASSWORD: ${{ secrets.KEY_STORE_PASSWORD }}
          KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
          KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
        run: |
          flutter build apk \
            --dart-define-from-file=build_config/development.json

      - name: Build AAB (Production)
        if: github.ref == 'refs/heads/main'
        env:
          KEY_STORE_FILE_PATH: ${{ secrets.KEY_STORE_FILE_PATH }}
          KEY_STORE_PASSWORD: ${{ secrets.KEY_STORE_PASSWORD }}
          KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
          KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
        run: |
          flutter build appbundle \
            --dart-define-from-file=build_config/production.json

  build-ios:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Flutter
        uses: subosito/flutter-action@v2

      - name: Get dependencies
        run: flutter pub get

      - name: Generate iOS Config (Development)
        if: github.ref == 'refs/heads/staging'
        run: ./scripts/generate_app_config.sh development

      - name: Generate iOS Config (Production)
        if: github.ref == 'refs/heads/main'
        run: ./scripts/generate_app_config.sh production

      - name: Build IPA
        env:
          ENVIRONMENT: ${{ github.ref == 'refs/heads/main' && 'production' || 'development' }}
        run: |
          flutter build ipa \
            --dart-define-from-file=build_config/$ENVIRONMENT.json
```

#### 注意事項

1. **iOS 必須先執行 `generate_app_config.sh`**
2. **Android 會自動從 dart-defines 判斷環境**
3. **Signing 配置需要設定環境變數或 secrets**
4. **Firebase 配置檔案需要事先準備好並加入版本控制**

---

## 進階技巧

### 自動化腳本設計

#### 從 `project.pbxproj` 提取 Bundle ID

為了避免重複配置，我們從 `project.pbxproj` 動態提取 base Bundle ID：

```bash
PBXPROJ_PATH="$PROJECT_ROOT/ios/Runner.xcodeproj/project.pbxproj"
BASE_BUNDLE_ID=$(grep -m 1 'PRODUCT_BUNDLE_IDENTIFIER' "$PBXPROJ_PATH" | cut -d'"' -f2 | cut -d'$' -f1)
```

**優點**：
- 單一配置來源（`project.pbxproj`）
- Script 自動適應 Bundle ID 變更
- 不需要硬編碼 Bundle ID

#### 錯誤處理最佳實務

```bash
set -e  # 遇到錯誤立即停止

# 檢查檔案是否存在
if [ ! -f "$src_firebase_config" ]; then
    echo "error: Firebase config file not found: $src_firebase_config" >&2
    exit 1
fi

# 檢查參數是否正確
case "$ENV_NAME" in
    "development"|"production")
        ;;
    *)
        echo "error: Unknown environment $ENV_NAME" >&2
        echo "Usage: $0 [development|production]" >&2
        exit 1
        ;;
esac
```

### 避免重複配置

#### 單一配置來源原則

**不好的做法**：
```text
ios/Flutter/
├── AppConfig-dev.xcconfig     # 重複配置
├── AppConfig-prod.xcconfig    # 重複配置
└── AppConfig.xcconfig         # 動態生成
```

**好的做法**：
```text
ios/Flutter/
└── AppConfig.xcconfig         # 唯一配置來源（動態生成）
```

**為什麼移除靜態 xcconfig 檔案**：

1. **配置重複**：
   - 靜態檔案和動態生成的檔案內容重複
   - 修改時需要同時更新多處

2. **容易出錯**：
   - 開發者可能忘記更新靜態檔案
   - 靜態檔案和動態生成的內容可能不一致

3. **混亂的優先順序**：
   - 如果同時存在靜態檔案和動態檔案，Xcode 會優先使用哪一個？
   - 難以預測和除錯

#### 動態生成 vs 靜態檔案

| 特性 | 動態生成 | 靜態檔案 |
|------|----------|----------|
| 配置來源 | script 中的邏輯 | 多個 xcconfig 檔案 |
| 可測試性 | ✅ 可以獨立測試 script | ❌ 需要實際 build |
| 可重用性 | ✅ 可應用於其他專案 | ❌ 需要複製檔案 |
| 錯誤處理 | ✅ Script 可以驗證配置 | ❌ Xcode 錯誤訊息不清楚 |
| CI/CD 整合 | ✅ 明確的執行步驟 | ❌ 依賴檔案是否存在 |

**結論**：使用動態生成 + 單一配置來源，讓配置清晰且易於維護。

---

## 常見問題與陷阱

### FlutterFire CLI 的限制

**問題**：為什麼不推薦使用 FlutterFire CLI 的 `flutterfire configure`？

**原因**：
1. 不支援動態環境切換
2. 配置重複且難以維護
3. CI/CD 整合複雜
4. Bundle ID 管理困難

**推薦做法**：手動管理 Firebase 配置檔案，使用 script 自動複製。

詳見 [3.6 為什麼不使用 FlutterFire CLI](#36-動態生成-xcconfig-️-通用技巧)。

### Xcode Pre-build Action vs 獨立 Script

**問題**：為什麼不在 Xcode Build Phase 中執行 `generate_app_config.sh`？

**原因**：
1. CI/CD 環境不一致（`flutter build` 不會執行 Pre-build Action）
2. 環境參數傳遞困難
3. 本地開發體驗不一致（只有 Xcode 會執行）

**推薦做法**：
- 本地開發：手動執行 script
- CI/CD：在 workflow 中明確執行 script

詳見 [3.6 為什麼不使用 Xcode Pre-build Action](#36-動態生成-xcconfig-️-通用技巧)。

### Build Phase 執行順序

**問題**：Launch Image 的 Copy Script 應該放在哪個 Build Phase？

**答案**：必須在 "Run Script (Flutter build)" **之前**。

**正確順序**：
1. `[CP] Check Pods Manifest.lock`
2. **`Copy Launch Image`** ← 在這裡
3. `Run Script` (Flutter build)
4. `Sources`
5. `Resources`

**原因**：
- Flutter build 會處理 Assets.xcassets
- 如果 LaunchImage.imageset 不存在，build 會失敗
- 因此必須先複製 launch image

### 快取問題處理

**問題**：修改 Launch Image 或 App Icon 後，裝置上顯示的還是舊的圖片。

**原因**：iOS 會快取 launch screen 和 app icon。

**解決方法**：

1. **建立清除快取 script**（`scripts/clear_ios_cache.sh`）：
   ```bash
   #!/bin/bash

   echo "Cleaning iOS build cache..."
   rm -rf build/
   rm -rf ios/build/
   rm -rf ios/Pods/
   rm -rf .dart_tool/build/

   echo "Done! Please:"
   echo "1. Delete the app from your device"
   echo "2. flutter clean"
   echo "3. flutter pub get"
   echo "4. Rebuild the app"
   ```

2. **執行步驟**：
   ```bash
   ./scripts/clear_ios_cache.sh
   flutter clean
   flutter pub get
   # 完全刪除裝置上的 app
   # 重新 build 並安裝
   ```

### 多環境新增

**問題**：如何新增一個新環境（例如 Staging）？

**Android**：
1. 在 `build_config/` 新增 `staging.json`
2. 在 `build.gradle.kts` 的 `when` 區塊新增 staging case
3. 在 `android/app/src/` 新增 `staging/res/` 目錄
4. 在 `android/app/config/` 新增 `staging/google-services.json`

**iOS**：
1. 在 `build_config/` 新增 `staging.json`
2. 在 `generate_app_config.sh` 的 `case` 區塊新增 staging case
3. 在 `Assets.xcassets` 新增 `AppIcon-Staging.appiconset` 和 `LaunchImage-Staging.imageset`
4. 在 `ios/config/` 新增 `Staging/GoogleService-Info.plist`

### 環境參數遺漏

**問題**：忘記執行 `generate_app_config.sh` 會怎樣？

**影響**：
- iOS build 會使用上次生成的配置
- 可能導致環境錯誤（例如想 build prod 但實際使用 dev 配置）

**解決方法**：
- 在 CI/CD workflow 中加入驗證步驟
- 本地開發建立 alias 或 script wrapper

**驗證範例**：
```bash
# 驗證 AppConfig.xcconfig 是否存在且內容正確
if [ ! -f "ios/Flutter/AppConfig.xcconfig" ]; then
    echo "Error: AppConfig.xcconfig not found"
    echo "Please run: ./scripts/generate_app_config.sh <environment>"
    exit 1
fi

# 驗證環境配置是否匹配
EXPECTED_SUFFIX=$([ "$ENVIRONMENT" = "production" ] && echo "" || echo ".dev")
ACTUAL_SUFFIX=$(grep APP_CONFIG_SUFFIX ios/Flutter/AppConfig.xcconfig | cut -d'=' -f2)

if [ "$EXPECTED_SUFFIX" != "$ACTUAL_SUFFIX" ]; then
    echo "Error: Environment mismatch"
    echo "Expected: $ENVIRONMENT (suffix: '$EXPECTED_SUFFIX')"
    echo "Actual: suffix '$ACTUAL_SUFFIX'"
    exit 1
fi
```

---

## 參考資源

- [Flutter dart-define Part 2 - Dev and Prod Package Names and Bundle IDs](https://thiele.dev/blog/flutter-dart-define-part-2-dev-and-prod-package-names-and-bundle-ids/)
- [Effective Dart](https://dart.dev/effective-dart)
- [Flutter Build Modes](https://docs.flutter.dev/testing/build-modes)
- [Android Build Configuration](https://developer.android.com/studio/build)
- [Xcode Build Configuration Files](https://developer.apple.com/documentation/xcode/adding-a-build-configuration-file-to-your-project)
