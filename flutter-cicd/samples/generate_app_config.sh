#!/bin/bash
#
# 擷取自 2026-08-14 的內部版本，已去識別化（bundle id 與 app 名稱都是假值）。
# 只保證可讀，不保證可直接執行。
#
# Generate AppConfig.xcconfig based on environment
# Usage: ./generate_app_config.sh <environment>

set -e

ENV_NAME=${1:-development}

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Extract base bundle identifier from project.pbxproj
# Expected format: PRODUCT_BUNDLE_IDENTIFIER = "com.example.myapp$(APP_CONFIG_SUFFIX)";
PBXPROJ_PATH="$PROJECT_ROOT/ios/Runner.xcodeproj/project.pbxproj"
# Extract the value using cut commands (more robust than sed):
# 1. cut -d'"' -f2: split by double quote, take 2nd field (content inside quotes)
# 2. cut -d'$' -f1: split by dollar sign, take 1st field (base ID before variable)
#
# ⚠️ grep -m 1 只讀第一份。app target 的 Debug／Release／Profile 在 pbxproj 裡各有一行，
# 加上 android/app/build.gradle.kts 那份，base bundle id 一共四份字面值，而且沒有任何
# 機制釘住它們一致。抄這段之前先想好誰來守這四份。
BASE_BUNDLE_ID=$(grep -m 1 'PRODUCT_BUNDLE_IDENTIFIER' "$PBXPROJ_PATH" | cut -d'"' -f2 | cut -d'$' -f1)

# 這支腳本不自己列環境清單：每個環境的值寫在 build_config/<env>.json，與 Android 讀的
# 是同一份檔案（gradle 透過 dart-define 拿到同樣那幾個欄位）。新增一個環境只要放一份設定檔
# 與建出它指到的目錄，不必回來改這裡。
CONFIG_FILE="$PROJECT_ROOT/build_config/${ENV_NAME}.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "error: Config file not found: $CONFIG_FILE" >&2
    echo "       新增環境時放一份 build_config/${ENV_NAME}.json 即可，這支腳本不需要改。" >&2
    exit 1
fi

# 逐個欄位讀，缺了就停。
#
# 用 `has()` 判斷而不是「值是不是空的」：production 的 APP_CONFIG_SUFFIX 就是空字串
# （正式版的 bundle id 沒有後綴），把空值當成缺漏會讓 production 直接建不起來。
# android/app/build.gradle.kts 的 environmentValue(allowBlank) 是同一個考量。
read_config() {
    local key=$1
    if ! jq -e --arg k "$key" 'has($k)' "$CONFIG_FILE" >/dev/null; then
        echo "error: $CONFIG_FILE 沒有 $key 欄位" >&2
        echo "       iOS 的 bundle id 後綴、顯示名稱、app icon 與 launch image 都由設定檔決定；" >&2
        echo "       缺欄位時不會回退到別的環境的值（那正是這個設計要消滅的錯配）。" >&2
        exit 1
    fi
    jq -r --arg k "$key" '.[$k]' "$CONFIG_FILE"
}

APP_CONFIG_SUFFIX=$(read_config APP_CONFIG_SUFFIX)
APP_CONFIG_NAME=$(read_config APP_CONFIG_NAME)
APP_CONFIG_ICON_NAME=$(read_config APP_CONFIG_ICON_NAME)
APP_CONFIG_LAUNCH_IMAGE=$(read_config APP_CONFIG_LAUNCH_IMAGE)
IOS_FIREBASE_CONFIG_PATH=$(read_config IOS_FIREBASE_CONFIG_PATH)

# 這兩個是 asset catalog 裡的名稱，打錯不會讓 build 失敗——Xcode 找不到 icon set 只是
# 少了圖示，copy_launch_image.sh 找不到 imageset 才會擋。所以在這裡先確認它們真的存在，
# 與 gradle 對 ANDROID_RES_DIR 的檢查同一個理由。
ASSETS_DIR="$PROJECT_ROOT/ios/Runner/Assets.xcassets"
for asset in "${APP_CONFIG_ICON_NAME}.appiconset" "${APP_CONFIG_LAUNCH_IMAGE}.imageset"; do
    if [ ! -d "$ASSETS_DIR/$asset" ]; then
        echo "error: Asset not found: ios/Runner/Assets.xcassets/$asset" >&2
        echo "       （來自 $CONFIG_FILE 的 APP_CONFIG_ICON_NAME／APP_CONFIG_LAUNCH_IMAGE）" >&2
        exit 1
    fi
done

# Calculate bundle ID
BUNDLE_ID="${BASE_BUNDLE_ID}${APP_CONFIG_SUFFIX}"

# Generate AppConfig.xcconfig
# 這份是產物，要進 .gitignore。Debug.xcconfig 與 Release.xcconfig 各自 #include 它，
# 所以本機 debug run 與 CI release build 走的是同一組值。
cat > "$PROJECT_ROOT/ios/Flutter/AppConfig.xcconfig" << EOF
APP_CONFIG_SUFFIX=$APP_CONFIG_SUFFIX
APP_CONFIG_NAME=$APP_CONFIG_NAME
APP_CONFIG_ICON_NAME=$APP_CONFIG_ICON_NAME
APP_CONFIG_LAUNCH_IMAGE=$APP_CONFIG_LAUNCH_IMAGE
EOF

# Copy corresponding Firebase config file
#
# 來源由設定檔的 IOS_FIREBASE_CONFIG_PATH 指定（相對 repo 根目錄），與 Android 的
# ANDROID_FIREBASE_CONFIG_PATH 對稱——兩個平台都不從環境名稱推導路徑。
src_firebase_config="$PROJECT_ROOT/$IOS_FIREBASE_CONFIG_PATH"
if [ ! -f "$src_firebase_config" ]; then
    echo "error: Firebase config file not found: $src_firebase_config" >&2
    echo "       （來自 $CONFIG_FILE 的 IOS_FIREBASE_CONFIG_PATH）" >&2
    exit 1
fi
cp "$src_firebase_config" "$PROJECT_ROOT/ios/Runner/GoogleService-Info.plist"

echo "Generated AppConfig.xcconfig for environment: $ENV_NAME"
echo "APP_CONFIG_SUFFIX=$APP_CONFIG_SUFFIX"
echo "APP_CONFIG_NAME=$APP_CONFIG_NAME"
echo "APP_CONFIG_ICON_NAME=$APP_CONFIG_ICON_NAME"
echo "APP_CONFIG_LAUNCH_IMAGE=$APP_CONFIG_LAUNCH_IMAGE"
echo "BUNDLE_ID=$BUNDLE_ID"

# Export BUNDLE_ID to GitHub Actions environment if running in CI
# 後面抓簽章憑證的步驟直接用這個值。
if [ -n "$GITHUB_ENV" ]; then
  printf '%s\n' "BUNDLE_ID=$BUNDLE_ID" >> "$GITHUB_ENV"
fi
