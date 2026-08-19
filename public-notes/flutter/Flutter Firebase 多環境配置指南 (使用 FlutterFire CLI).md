Flutter app 不同環境搭配不同 Firebase Project 設定
===

我們的情境是想要 Production (Release), Development (Debug) 搭配不同的 Firebase project

## 第一步：安裝和設定 FlutterFire CLI

### 1.1 安裝 FlutterFire CLI
```bash
# 安裝 FlutterFire CLI
dart pub global activate flutterfire_cli

# 驗證安裝
flutterfire --version
```

### 1.2 登入 Firebase
```bash
# 登入你的 Google 帳號
firebase login

# 或者如果已經安裝 Firebase CLI
flutterfire login
```

## 第二步：移除現有 Firebase 配置

### 2.1 移除現有檔案
刪除以下檔案（如果存在）：
- `android/app/google-services.json`
- `ios/Runner/GoogleService-Info.plist`
- `lib/firebase_options.dart`
- `firebase.json`

### 2.2 移除 iOS Xcode 中的 Firebase 配置
1. 開啟 `ios/Runner.xcodeproj`
2. 刪除 `GoogleService-Info.plist`（如果存在）

## 第三步：建立多環境 Firebase 配置

### 3.1 為 Development 環境配置
```bash
# 配置 development 環境
flutterfire configure \
  --project=yourapp-dev \
  --out=lib/firebase_options_dev.dart \
  --ios-bundle-id=com.yourapp.dev \
  --android-package-name=com.yourapp.dev \
  --ios-out=ios/config/Dev/GoogleService-Info.plist \
  --android-out=android/app/config/dev/google-services.json
```

### 3.2 為 Production 環境配置
```bash
# 配置 production 環境
flutterfire configure \
  --project=yourapp-prod \
  --out=lib/firebase_options_prod.dart \
  --ios-bundle-id=com.yourapp \
  --android-package-name=com.yourapp \
  --ios-out=ios/config/Prod/GoogleService-Info.plist \
  --android-out=android/app/prod/google-services.json
```

### 3.3 驗證產生的檔案
執行完成後，你應該會看到：
```text
lib/
├── firebase_options_dev.dart
├── firebase_options_prod.dart
android/app/config/
├── dev/google-services.json      ← development 環境
├── prod/google-services.json    ← production 環境
ios/config/
├── Dev/GoogleService-Info.plist  ← development 環境
├── Prod/GoogleService-Info.plist ← production 環境
```

## 第四步：建立環境配置管理

根據環境來初始化 FirebaseAPp

> 這邊的 Environment 非 dart 內建的 class 這邊只是舉例，可以依照需求實做判斷環境的方式

```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:gobbleverse/firebase_options_dev.dart' as firebase_dev;
import 'package:gobbleverse/firebase_options_prod.dart' as firebase_prod;

Future<void> _setupFirebase() async {
  final currentPlatform = switch (Environment.current) {
    Environment.development =>
      firebase_dev.DefaultFirebaseOptions.currentPlatform,
    Environment.production =>
      firebase_prod.DefaultFirebaseOptions.currentPlatform,
  };

  await Firebase.initializeApp(
    options: currentPlatform,
  );
}
```

## 第五步：調整 firebase.json 設定

把 android, iOS 裡面的 fileOout 都改到指向同一個地方，然後我們會利用 pre build 的方式動態複製對應的檔案到該位置

``` json
flutter": {
  "platforms": {
    "android": {
      "buildConfigurations": {
        "src/debug": {
          ...
          "fileOutput": "android/app/google-services.json"
        },
        "src/release": {
          ...
          "fileOutput": "android/app/google-services.json"
        }
      }
    },
    "ios": {
      "buildConfigurations": {
        "Debug": {
          ...
          "fileOutput": "ios/Runner/GoogleService-Info.plist"
        },
        "Release": {
          ...
          "fileOutput": "ios/Runner/GoogleService-Info.plist"
        }
      }
    },
```

## 第五步：Android 配置調整

在 app/build.gradle.kts 加上

```kotlin
// 複製 google-services.json 的 task
tasks.register("copyGoogleServices") {
    doLast {
        val environment = dartEnvironmentVariables["APP_CONFIG_SUFFIX"]
        val sourceDir = when (environment) {
            ".dev" -> "config/dev"
            "" -> "config/prod"
            else -> "config/dev" // 預設使用 dev
        }
        
        val sourceFile = file("$sourceDir/google-services.json")
        val targetFile = file("google-services.json")
        
        if (sourceFile.exists()) {
            sourceFile.copyTo(targetFile, overwrite = true)
            println("Copied google-services.json from $sourceDir to root")
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

這邊就是動態把 andorid 這邊的 google-services.json 複製到 firebase.json 指定的地方，裡面判斷的方式可以依照需求實做，這邊只是一種判斷的方式，重點是要把檔案搬到正確的地方

## 第六步：iOS 配置調整

在 Xcode 中更新 Pre-build Script，加入 Firebase 配置檔案的複製：

```bash
# Type a script or drag a script file from your workspace to insert its path.
function entry_decode() { echo "${*}" | base64 --decode; }

IFS=',' read -r -a define_items <<< "$DART_DEFINES"

result=()
resultIndex=0
firebase_config="Dev/GoogleService-Info.plist"  # 預設使用 Debug (development)

for index in "${!define_items[@]}"
do
    if [ "$(entry_decode "${define_items[$index]}")" == "APP_CONFIG_ENV=development" ]; then
        result[$resultIndex]="APP_CONFIG_SUFFIX=.dev";
        resultIndex=$((resultIndex+1))
        result[$resultIndex]="APP_CONFIG_NAME=[DEV] YourApp";
        resultIndex=$((resultIndex+1))
        firebase_config="Dev/GoogleService-Info.plist"
    fi
    if [ "$(entry_decode "${define_items[$index]}")" == "APP_CONFIG_ENV=production" ]; then
        result[$resultIndex]="APP_CONFIG_SUFFIX=";
        resultIndex=$((resultIndex+1))
        result[$resultIndex]="APP_CONFIG_NAME=YourApp";
        resultIndex=$((resultIndex+1))
        firebase_config="Prod/GoogleService-Info.plist"
    fi
done

printf "%s\n" "${result[@]}"|grep '^APP_CONFIG_' > ${SRCROOT}/Flutter/AppConfig.xcconfig

# 複製對應的 Firebase 配置檔案
cp "${SRCROOT}/config/${firebase_config}" "${SRCROOT}/Runner/GoogleService-Info.plist"
```

## 第七步：更新環境配置檔案

### 7.1 更新 development.json
```json
{
  "APP_CONFIG_ENV": "development"
}
```

### 7.2 更新 production.json
```json
{
  "APP_CONFIG_ENV": "production"
}
```

## 第八步：更新建置指令和 VS Code 配置

### 8.1 建置指令
```bash
# Development (Debug build)
flutter run --dart-define-from-file=development.json // 會用 debug 跑
flutter run --release --dart-define-from-file=development.json
flutter build apk --debug --dart-define-from-file=development.json
flutter build apk --release --dart-define-from-file=development.json
flutter build ios --debug --dart-define-from-file=development.json
flutter build ios --release --dart-define-from-file=development.json
flutter build ipa --release --dart-define-from-file=development.json

# Production (Release build)
flutter run --dart-define-from-file=production.json // 會用 debug 跑
flutter run --release --dart-define-from-file=production.json
flutter build apk --debug --dart-define-from-file=production.json
flutter build apk --release --dart-define-from-file=production.json
flutter build ios --release --dart-define-from-file=production.json
flutter build ios --debug --dart-define-from-file=production.json
flutter build ipa --release --dart-define-from-file=production.json
```

## 故障排除

### 如果 FlutterFire 配置失敗
```bash
# 清理並重新配置
flutter clean
flutterfire configure --project=yourapp-dev --out=lib/firebase_options_dev.dart
```