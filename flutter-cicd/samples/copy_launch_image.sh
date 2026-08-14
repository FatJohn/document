#!/bin/bash
#
# 擷取自 2026-08-14 的內部版本，已去識別化。只保證可讀，不保證可直接執行。
#
# 在 Xcode build 時複製對應環境的 LaunchImage 到通用的 LaunchImage.imageset，
# 這樣 LaunchScreen.storyboard 就能引用到正確的圖片——storyboard 沒辦法引用
# xcconfig 變數，裡面只能寫死一個圖片名稱，所以固定引用 LaunchImage，由這支
# script 在 build 之前把對的那份複製成那個名字。
#
# 掛法：Xcode target 的 Build Phases 加一個 Run Script，放在 Copy Bundle Resources 之前。
# 此 script 依賴 xcconfig 中定義的 APP_CONFIG_LAUNCH_IMAGE 變數。

ASSETS_DIR="${SRCROOT}/Runner/Assets.xcassets"
SOURCE_IMAGESET="${ASSETS_DIR}/${APP_CONFIG_LAUNCH_IMAGE}.imageset"
TARGET_IMAGESET="${ASSETS_DIR}/LaunchImage.imageset"

if [ -z "$APP_CONFIG_LAUNCH_IMAGE" ]; then
  echo "Warning: APP_CONFIG_LAUNCH_IMAGE not set, using LaunchImage-Dev as default"
  SOURCE_IMAGESET="${ASSETS_DIR}/LaunchImage-Dev.imageset"
fi

if [ ! -d "$SOURCE_IMAGESET" ]; then
  echo "Error: Source imageset not found: $SOURCE_IMAGESET"
  exit 1
fi

# 刪除舊的並複製新的
rm -rf "$TARGET_IMAGESET"
cp -R "$SOURCE_IMAGESET" "$TARGET_IMAGESET"

echo "[Xcode Build] Copied launch image: $APP_CONFIG_LAUNCH_IMAGE -> LaunchImage"
