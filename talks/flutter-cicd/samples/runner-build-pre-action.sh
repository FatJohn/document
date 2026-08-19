#!/bin/bash
#
# 整理自 2026-08-14 內部專案 Runner.xcscheme 的 Build Pre-action，已去識別化。
# 這是貼進 Xcode Scheme Build Pre-actions 的可讀片段，不是獨立執行的安裝腳本。
#
# 目的：AppConfig.xcconfig 是產物，每次 build 都先依目前的 DART_DEFINES 重產，
# 不相信工作目錄裡上一次留下的環境設定。

DEFAULT_ENV="development"
ENV_NAME="$DEFAULT_ENV"

if [[ -n "$DART_DEFINES" ]]; then
  IFS=',' read -r -a define_items <<< "$DART_DEFINES"
  for item in "${define_items[@]}"; do
    decoded_value=$(printf '%s' "$item" | base64 --decode)
    if [[ "$decoded_value" == ENV=* ]]; then
      ENV_NAME="${decoded_value#*=}"
      break
    fi
  done
fi

"${SRCROOT}/../scripts/generate_app_config.sh" "$ENV_NAME"
