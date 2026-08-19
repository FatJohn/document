Flutter App 不同環境使用不同 Bundle 及 Application ID 設定
===

這個情境應該滿常見，本來覺得可能會很麻煩，想不到看到 [Flutter dart-define Part 2: Dev and Prod Package Names & Bundle IDs](https://thiele.dev/blog/flutter-dart-define-part-2-dev-and-prod-package-names-and-bundle-ids/) 這篇文章，感覺是用一個比較彈性的方式來做到，但稍微麻煩一些，主要是 iOS 的部分要額外寫 pre-build script

這篇就依照這篇文章的教學拆解步驟來說怎麼玩

## 概述

這邊的環境指的是 Production (Release), Development (Debug) 等等，不同的 Bundle/Application ID 的意思指的是

例如：
- **Development**: `com.yourapp.dev`
- **Staging**: `com.yourapp.staging`
- **Production**: `com.yourapp`

而我們給予環境的變數用的就是建置的時候給予現在是什麼環境，就是使用 flutter build 的 `--dart-define` 或者 `--dart-define-from-file` 的參數在裡面指定環境

例如：
- `flutter build apk --dart-define="APP_CONFIG_ENV=staging"`
- `flutter build apk --dart-define-from-file=development.json`

好，我知道想要怎麼做給予環境變數了，接下來就是每個平台 app 的設定

## 步驟 1 : Android 配置

### 1.1 修改 `android/app/build.gradle`

在檔案開頭加入以下程式碼：

```gradle
// 定義預設配置（Development 環境）
def dartEnvironmentVariables = [
    APP_CONFIG_SUFFIX: '.dev',
    APP_CONFIG_NAME : '[DEV] YourApp'
];

// 注入 dart-define 變數
if (project.hasProperty('dart-defines')) {
    dartEnvironmentVariables = dartEnvironmentVariables + project.property('dart-defines')
        .split(',')
        .collectEntries { entry ->
            def pair = new String(entry.decodeBase64(), 'UTF-8').split('=')
            if (pair.first() == 'APP_CONFIG_ENV') {
                switch (pair.last()) {
                    case 'staging':
                        return [
                            APP_CONFIG_SUFFIX: ".staging",
                            APP_CONFIG_NAME : "[STA] YourApp"
                        ]
                    case 'production':
                        return [
                            APP_CONFIG_SUFFIX: "",
                            APP_CONFIG_NAME : "YourApp"
                        ]
                }
            }
            [(pair.first()): pair.last()]
        }
    println dartEnvironmentVariables
}

android {
    // ... 其他配置
    
    defaultConfig {
        applicationId "com.yourapp"  // 改成你的基礎 package name
        applicationIdSuffix dartEnvironmentVariables.APP_CONFIG_SUFFIX
        resValue "string", "app_name", dartEnvironmentVariables.APP_CONFIG_NAME
        // ... 其他配置
    }
}
```

### 1.2 修改 `android/app/src/main/AndroidManifest.xml`

將 `android:label` 改為動態變數：

```xml
<manifest ...>
    <application
        android:label="@string/app_name"
        ...>
        ...
    </application>
</manifest>
```

## 步驟 2 : iOS 配置

### 2.1 建立預設配置檔案

建立 `ios/Flutter/AppConfig-default.xcconfig`：

```
APP_CONFIG_SUFFIX=.dev
APP_CONFIG_NAME=[DEV] YourApp
```

### 2.2 修改 xcconfig 檔案

在 `ios/Flutter/Debug.xcconfig` 和 `ios/Flutter/Release.xcconfig` 最後加入：

```
#include "AppConfig-default.xcconfig"
#include "AppConfig.xcconfig"
```

### 2.3 修改 project.pbxproj

開啟 `ios/Runner.xcodeproj/project.pbxproj`，搜尋 `PRODUCT_BUNDLE_IDENTIFIER` 並替換為：

```
PRODUCT_BUNDLE_IDENTIFIER = "com.yourapp$(APP_CONFIG_SUFFIX)";
```

**注意**：
- 需要在所有出現的地方都做替換（通常有多個 build configuration）
- RunnerTest 的不需要更換

### 2.4 修改 Info.plist

開啟 `ios/Runner/Info.plist`，找到 `CFBundleDisplayName` 並修改為：

```xml
<key>CFBundleDisplayName</key>
<string>$(APP_CONFIG_NAME)</string>
```

### 2.5 建立 Pre-build Script

1. 用 Xcode 開啟 `ios/Runner.xcodeproj`
2. 選擇 Runner target
3. 點選上牤的 Runner 跳出下拉選單再點選 `Edit Schema` 頁籤
4. 在左側選擇 "Build" → "Pre-actions"
5. 點選 "+" 新增 "New Run Script Action"
6. 確認 "Provide build settings from" 設定為 "Runner"
7. 在 script 區域貼入以下程式碼：

```bash
# Type a script or drag a script file from your workspace to insert its path.
function entry_decode() { echo "${*}" | base64 --decode; }

IFS=',' read -r -a define_items <<< "$DART_DEFINES"

result=()
resultIndex=0

for index in "${!define_items[@]}"
do
    if [ "$(entry_decode "${define_items[$index]}")" == "APP_CONFIG_ENV=staging" ]; then
        result[$resultIndex]="APP_CONFIG_SUFFIX=.staging";
        resultIndex=$((resultIndex+1))
        result[$resultIndex]="APP_CONFIG_NAME=[STA] YourApp";
        resultIndex=$((resultIndex+1))
    fi
    if [ "$(entry_decode "${define_items[$index]}")" == "APP_CONFIG_ENV=production" ]; then
        result[$resultIndex]="APP_CONFIG_SUFFIX=";
        resultIndex=$((resultIndex+1))
        result[$resultIndex]="APP_CONFIG_NAME=YourApp";
        resultIndex=$((resultIndex+1))
    fi
done

printf "%s\n" "${result[@]}"|grep '^APP_CONFIG_' > ${SRCROOT}/Flutter/AppConfig.xcconfig
```

### 2.6 把動態產生的檔案加入 gitignore
建置 iOS 的時候會動態建立 `AppConfig.xcconfig` 可以把這個檔案加入 gitignore

## [可選] 步驟 3 : 修改 Launch.json 方便 Debug

### 3.1 建立 VS Code Launch 配置（建議）

在 `.vscode/launch.json` 中加入不同環境的配置：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Flutter Dev",
            "request": "launch",
            "type": "dart"
        },
        {
            "name": "Flutter Staging",
            "request": "launch",
            "type": "dart",
            "args": [
                "--dart-define=APP_CONFIG_ENV=staging"
            ]
        },
        {
            "name": "Flutter Production",
            "request": "launch",
            "type": "dart",
            "args": [
                "--dart-define=APP_CONFIG_ENV=production"
            ]
        }
    ]
}
```

PS: 如果 dart define 是使用 json 檔案，記得把 args 裡面改成對的

## 步驟 4 : 驗證

### 4.1 檢查 Android
執行不同環境的 build，檢查：
- Package name 是否正確
- App 名稱是否正確
- 可以同時安裝多個版本

### 4.2 檢查 iOS
執行不同環境的 build，檢查：
- Bundle ID 是否正確
- App 名稱是否正確
- 可以同時安裝多個版本

## [可選] 步驟 5 : 補充

### 5.1 不同的 App Icon 

可以為不同環境設定不同的 App Icon：

Android `build.gradle` 中加入：
```gradle
APP_CONFIG_ICON: '@mipmap/ic_launcher_dev'  // 對應到不同的 icon
```

iOS 則在 pre-build script 中加入：
```bash
result[$resultIndex]="APP_CONFIG_ICON=AppIcon-staging";
```

### 5.2 在 dart 裡面存取 dart define 的變數

```dart
const String environment = String.fromEnvironment('APP_CONFIG_ENV', defaultValue: 'development');
```
