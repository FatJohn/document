# Flutter CI/CD 最佳實務

本文件整理了 Flutter 專案的 CI/CD 最佳實務，涵蓋 GitHub Actions workflow 設計模式、版本管理策略、build 流程設計等。這些模式大多適用於其他框架的 CI/CD，特別標示的部分則專屬於 Flutter。

---

## 目錄

- [Workflow 架構設計](#workflow-架構設計)
- [版本管理策略](#版本管理策略)
- [Build 流程設計](#build-流程設計)
- [Deployment 策略](#deployment-策略)
- [Self-hosted Runner 最佳實務](#self-hosted-runner-最佳實務)
- [Secrets 管理](#secrets-管理)
- [進階模式](#進階模式)
- [故障排除](#故障排除)

---

## Workflow 架構設計

### 主要 Workflow vs Reusable Workflow 🔶 CI/CD 通用

**問題**：隨著專案複雜度提升，workflow 檔案變得龐大且重複。

**解決方案**：使用 `workflow_call` 將共用邏輯提取為 reusable workflow。

#### 架構設計

**主要 Workflow**（`development.yml`、`production.yml`）：
- 定義觸發條件（push、PR、tag、workflow_dispatch）
- 協調整體流程（test → build → deploy）
- 傳遞參數給 reusable workflows

**Reusable Workflow**（`test.yml`、`build-android.yml`、`build-ios.yml`）：
- 實作具體的建置邏輯
- 可被多個主要 workflow 呼叫
- 提供明確的輸入和輸出

#### 範例：主要 Workflow

```yaml
name: Development CI/CD

on:
  push:
    branches: [staging]
  pull_request:
    branches: [staging]

jobs:
  test:
    uses: ./.github/workflows/test.yml

  build-android:
    needs: [test]
    uses: ./.github/workflows/build-android.yml
    with:
      environment: development
      app_version: ${{ needs.resolve-version.outputs.app_version }}
      build_number: ${{ needs.generate-build-number.outputs.build_number }}
      build_aab: false
    secrets: inherit

  deploy-firebase:
    needs: [build-android]
    uses: ./.github/workflows/deploy-firebase.yml
    with:
      environment: development
      artifact_name: android-development-apk
    secrets: inherit
```

#### 範例：Reusable Workflow

```yaml
name: Test

on:
  workflow_call:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: subosito/flutter-action@v2
      - run: flutter pub get
      - run: flutter test
      - run: flutter analyze
```

#### 優點

1. **程式碼重用**：
   - Development 和 Production 共用相同的 test/build 邏輯
   - 修改一處，所有環境同步更新

2. **可讀性**：
   - 主要 workflow 專注於流程協調
   - Reusable workflow 專注於實作細節

3. **可測試性**：
   - 可以手動觸發 reusable workflow 進行測試
   - 每個 workflow 職責單一，易於除錯

4. **維護性**：
   - 減少重複程式碼
   - 修改邏輯時不易遺漏環境

### 參數傳遞設計 🔶 CI/CD 通用

#### 使用 `with` 傳遞參數

```yaml
jobs:
  build-android:
    uses: ./.github/workflows/build-android.yml
    with:
      environment: development
      app_version: "1.2.3"
      build_number: "2601000015"
      build_aab: false
```

#### Reusable Workflow 定義輸入

```yaml
on:
  workflow_call:
    inputs:
      environment:
        description: "Build environment (production or development)"
        required: true
        type: string
      app_version:
        description: "App version (e.g., 1.2.3)"
        required: true
        type: string
      build_aab:
        description: "Whether to build AAB"
        required: false
        type: boolean
        default: false
```

#### 使用 `outputs` 傳遞結果

**Reusable Workflow 定義輸出**：
```yaml
on:
  workflow_call:
    outputs:
      build_number:
        description: 'Generated build number'
        value: ${{ jobs.generate.outputs.build_number }}

jobs:
  generate:
    outputs:
      build_number: ${{ steps.version.outputs.BUILD_NO }}
    steps:
      - id: version
        run: echo "BUILD_NO=2601000015" >> $GITHUB_OUTPUT
```

**主要 Workflow 使用輸出**：
```yaml
jobs:
  generate-build-number:
    uses: ./.github/workflows/build-number.yml

  build-android:
    needs: [generate-build-number]
    uses: ./.github/workflows/build-android.yml
    with:
      build_number: ${{ needs.generate-build-number.outputs.build_number }}
```

### Secrets 繼承機制 🔶 CI/CD 通用

使用 `secrets: inherit` 將 secrets 傳遞給 reusable workflow：

```yaml
jobs:
  build-android:
    uses: ./.github/workflows/build-android.yml
    secrets: inherit
```

**注意事項**：
- `secrets: inherit` 會傳遞所有 secrets
- Reusable workflow 可以直接使用 `${{ secrets.KEY_STORE_PASSWORD }}`
- 如果只需要傳遞部分 secrets，使用明確的 secrets 參數

### 環境隔離策略

#### Branch-based 環境

- **staging branch** → Development 環境
- **main branch** → Production 環境

```yaml
# development.yml
on:
  push:
    branches: [staging]

# production.yml
on:
  push:
    branches: [main]
```

#### Tag-based Deployment

- **dev*** tag → Development deployment
- **v*** tag → Production deployment

```yaml
# development.yml
on:
  push:
    tags:
      - "dev[0-9]+.[0-9]+.[0-9]+-*"

# production.yml
on:
  push:
    tags:
      - "v[0-9]+.[0-9]+.[0-9]+-*"
```

---

## 版本管理策略

### 語義化版本擴展

**標準語義化版本**：`MAJOR.MINOR.PATCH`

**擴展策略**：使用 **奇偶數 patch** 區分環境

- **Staging**: 奇數 patch（0.7.1, 0.7.3, 0.7.5）
- **Production**: 偶數 patch（0.7.2, 0.7.4, 0.7.6）
- **特例**: patch=0 表示 MINOR 升版的首發版本

#### 規則說明

| pubspec.yaml | Staging | Production CI 轉換 |
|--------------|---------|-------------------|
| 0.7.1        | 0.7.1   | 0.7.2             |
| 0.7.3        | 0.7.3   | 0.7.4             |
| 0.8.0        | 0.8.0   | 0.8.0（不變）      |
| 0.8.2        | ❌ 錯誤  | ❌ 停止 build      |

#### 版本轉換 Script

**`version_for_production.sh`**
```bash
#!/bin/bash

set -e

PUBSPEC_FILE="pubspec.yaml"

# 讀取版本
VERSION_LINE=$(grep -m 1 '^\s*version:' "$PUBSPEC_FILE")
FULL_VERSION="${VERSION_LINE#*version:}"
FULL_VERSION="${FULL_VERSION%%+*}"
FULL_VERSION="${FULL_VERSION//[[:space:]]/}"

IFS='.' read -r MAJOR MINOR PATCH <<< "$FULL_VERSION"

# 驗證並轉換
if [ "$PATCH" -eq 0 ]; then
  # MINOR 升版首發，直接使用
  PROD_VERSION="$MAJOR.$MINOR.0"
elif [ $((PATCH % 2)) -eq 1 ]; then
  # 奇數: +1 變成偶數
  PROD_PATCH=$((PATCH + 1))
  PROD_VERSION="$MAJOR.$MINOR.$PROD_PATCH"
else
  # 偶數（非 0）: 錯誤
  echo "Error: Invalid patch version in pubspec.yaml" >&2
  echo "Current version: $FULL_VERSION (patch=$PATCH)" >&2
  echo "Expected: 0 or odd number" >&2
  exit 1
fi

echo "$PROD_VERSION"
```

#### 在 CI/CD 中使用

```yaml
# production.yml
jobs:
  resolve-version:
    runs-on: ubuntu-latest
    outputs:
      app_version: ${{ steps.version.outputs.APP_VERSION }}
    steps:
      - uses: actions/checkout@v3
      - id: version
        run: |
          APP_VERSION=$(./scripts/version_for_production.sh)
          echo "APP_VERSION=$APP_VERSION" >> $GITHUB_OUTPUT
```

### Build Number 生成

#### YYMMXXXXX 格式設計原理

**格式**：`YYMMXXXXX`
- `YY`: 年份後兩碼（26）
- `MM`: 月份（01）
- `XXXXX`: 當年度的第幾次 build（補零至 5 位）

**範例**：`2601000015`（2026年1月第15次 build）

**優點**：
- 保證跨年遞增（27 > 26）
- 保證跨月遞增（2602 > 2601）
- 支援每年 99999 次 build
- 人類可讀（可以看出 build 的年月）

#### 跨年處理策略

**問題**：GitHub Actions 的 `GITHUB_RUN_NUMBER` 是全域累加，跨年後如何重置為 1？

**解決方案**：使用 **Metadata Branch** 儲存年度偏移量。

**原理**：
```text
yearly_run_number = GITHUB_RUN_NUMBER - offset
```

- **2025 年**：offset = 0，第 100 次 build → yearly_run_number = 100
- **2026 年**：offset = 100，第 101 次 build → yearly_run_number = 1

#### Metadata Branch 設計模式 🔶 CI/CD 通用

**建立 orphan branch 儲存 metadata**：

```bash
git checkout --orphan build-metadata
git rm -rf .
echo '{"production":{},"development":{}}' > build-history.json
git add build-history.json
git commit -m "Initialize build history"
git push origin build-metadata
```

**JSON 結構**：
```json
{
  "production": {
    "2025": 0,
    "2026": 150
  },
  "development": {
    "2025": 0,
    "2026": 200
  }
}
```

**在 CI 中讀取和更新**：

```yaml
jobs:
  generate-build-number:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Generate Build Number
        run: |
          # 切換到 metadata branch
          git fetch origin build-metadata
          git checkout build-metadata

          # 讀取 JSON
          JSON_CONTENT=$(cat build-history.json)
          FULL_YEAR=$(date +"%Y")
          CURRENT_OFFSET=$(echo "$JSON_CONTENT" | jq -r --arg env "production" --arg y "$FULL_YEAR" '.[$env][$y] // empty')

          # 跨年判斷
          if [ -z "$CURRENT_OFFSET" ]; then
            echo "New Year Detected! Initializing offset..."
            NEW_OFFSET=$((GITHUB_RUN_NUMBER - 1))
            NEW_JSON=$(echo "$JSON_CONTENT" | jq -c --arg env "production" --arg y "$FULL_YEAR" --argjson v "$NEW_OFFSET" '.[$env][$y] = $v')
            echo "$NEW_JSON" > build-history.json
            git add build-history.json
            git commit -m "Update production build history for year $FULL_YEAR"
            git push origin build-metadata
            CURRENT_OFFSET=$NEW_OFFSET
          fi

          # 計算 build number
          YEARLY_RUN=$((GITHUB_RUN_NUMBER - CURRENT_OFFSET))
          YY=$(date +"%y")
          MM=$(date +"%m")
          RUN_SUFFIX=$(printf "%05d" $YEARLY_RUN)
          BUILD_NO="${YY}${MM}${RUN_SUFFIX}"

          echo "BUILD_NO=$BUILD_NO" >> $GITHUB_OUTPUT

          # 切回原本的 commit
          git checkout $GITHUB_SHA
```

**優點**：
- 每年自動重置 build number
- Production 和 Development 環境獨立計數
- 保留歷史紀錄，可追溯

**適用場景**：
- 🔶 任何需要跨年重置計數的 CI/CD 系統

### 自動版本提升

#### 問題

每次 release 後，需要手動更新 `pubspec.yaml` 的版本號，容易忘記且繁瑣。

#### 解決方案：自動化 Bump Version

**觸發條件**：當 PR 從 staging 合併到 main 時自動執行。

**`bump-version-after-release.yml`**
```yaml
name: Bump Version After Release

on:
  pull_request:
    types: [closed]
    branches: [main]

jobs:
  bump-version:
    if: |
      github.event.pull_request.merged == true &&
      github.event.pull_request.head.ref == 'staging'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          ref: staging
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Bump version
        id: bump
        run: |
          NEW_VERSION=$(./scripts/bump_version.sh)
          echo "new_version=$NEW_VERSION" >> $GITHUB_OUTPUT

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          commit-message: "chore: bump version to ${{ steps.bump.outputs.new_version }}"
          branch: chore/bump-version-${{ steps.bump.outputs.new_version }}
          title: "chore: bump version to ${{ steps.bump.outputs.new_version }}"
          body: |
            ## 🚀 Version Bump

            此 PR 由 GitHub Actions 自動建立，用於在 release 後更新版本號。

            **變更內容:**
            - 版本從 `${{ steps.prev_version.outputs.prev_version }}` 更新為 `${{ steps.bump.outputs.new_version }}`
          base: staging
```

**`bump_version.sh`**
```bash
#!/bin/bash

set -e

PUBSPEC_FILE="pubspec.yaml"

# 讀取版本
VERSION_LINE=$(grep -m 1 '^\s*version:' "$PUBSPEC_FILE")
FULL_VERSION_WITH_BUILD="${VERSION_LINE#*version:}"
FULL_VERSION_WITH_BUILD="${FULL_VERSION_WITH_BUILD//[[:space:]]/}"

# 分離版本號和 build number
if [[ "$FULL_VERSION_WITH_BUILD" == *"+"* ]]; then
  VERSION_PART="${FULL_VERSION_WITH_BUILD%%+*}"
  BUILD_PART="+${FULL_VERSION_WITH_BUILD#*+}"
else
  VERSION_PART="$FULL_VERSION_WITH_BUILD"
  BUILD_PART=""
fi

IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION_PART"

# 計算新的 patch 版本
if [ $((PATCH % 2)) -eq 0 ]; then
  # 偶數: +1 變成第一個奇數
  NEW_PATCH=$((PATCH + 1))
else
  # 奇數: +2 變成下一個奇數
  NEW_PATCH=$((PATCH + 2))
fi

NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"
NEW_FULL_VERSION="$NEW_VERSION$BUILD_PART"

# 更新 pubspec.yaml
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' "s|^\([ ]*version:[ ]*\).*|\1$NEW_FULL_VERSION|" "$PUBSPEC_FILE"
else
  sed -i "s|^\([ ]*version:[ ]*\).*|\1$NEW_FULL_VERSION|" "$PUBSPEC_FILE"
fi

echo "$NEW_VERSION"
```

#### 流程說明

1. PR 從 staging 合併到 main（表示完成 release）
2. GitHub Actions 自動執行 `bump_version.sh`
3. 版本從 0.7.1 → 0.7.3（跳過偶數）
4. 自動建立 PR 回 staging
5. 開發者 review 並 merge PR
6. 繼續下一輪開發

#### 優點

- 完全自動化，無需人工介入
- 避免忘記更新版本號
- 版本歷史清晰，每個版本都有對應的 commit

---

## Build 流程設計

### 平行化與依賴管理 🔶 CI/CD 通用

#### Job 依賴關係設計

使用 `needs` 定義 job 之間的依賴關係：

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: flutter test

  generate-build-number:
    runs-on: ubuntu-latest
    steps:
      - run: echo "BUILD_NO=2601000015" >> $GITHUB_OUTPUT

  build-android:
    needs: [test, generate-build-number]
    runs-on: ubuntu-latest
    steps:
      - run: flutter build apk

  build-ios:
    needs: [test, generate-build-number]
    runs-on: macos-latest
    steps:
      - run: flutter build ios

  deploy:
    needs: [build-android, build-ios]
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying..."
```

**執行流程**：
```text
    test ──┐
           ├──> build-android ──┐
generate ──┤                     ├──> deploy
           ├──> build-ios ──────┘
```

#### 如何決定哪些 Job 可以平行執行

**可以平行執行**：
- `test` 和 `generate-build-number`（無依賴關係）
- `build-android` 和 `build-ios`（都依賴 test 和 generate，但彼此獨立）

**必須順序執行**：
- `deploy` 必須等待 `build-android` 和 `build-ios` 完成

**優點**：
- 縮短總執行時間
- 資源利用效率高
- 早期發現錯誤（test 失敗會立即停止後續 build）

### 多環境 Build 差異

#### Development: APK only

```yaml
# development.yml
jobs:
  build-android:
    uses: ./.github/workflows/build-android.yml
    with:
      environment: development
      build_aab: false  # 只 build APK
```

**為什麼**：
- Development 用於內部測試，不需要上架 Google Play
- APK 可以直接安裝到裝置，方便快速測試
- AAB 需要透過 Google Play Console 或 bundletool 轉換，增加測試流程複雜度

#### Production: APK + AAB

```yaml
# production.yml
jobs:
  build-android:
    uses: ./.github/workflows/build-android.yml
    with:
      environment: production
      build_aab: true  # 同時 build APK 和 AAB
```

**為什麼**：
- AAB 是 Google Play 上架的標準格式
- APK 可以作為備份或提供給特殊管道分發

#### dSYM 上傳策略

**Development**：僅在 tag-based deployment 時上傳
```yaml
jobs:
  build-ios:
    with:
      upload_dsyms_to_crashlytics: ${{ needs.check-deployment-eligibility.outputs.should_deploy == 'true' }}
```

**Production**：總是上傳
```yaml
jobs:
  build-ios:
    with:
      upload_dsyms_to_crashlytics: true
```

**為什麼**：
- dSYM 用於 crash 報告符號化
- Development 的每次 PR build 不需要上傳（節省時間和儲存空間）
- 只在實際部署的版本上傳 dSYM
- Production 的所有 build 都應該上傳（可能需要追蹤 crash）

---

## Deployment 策略

### Tag-based vs Manual Deployment

#### Tag-based Deployment（推薦）

**設計理念**：
- **Branch Push**: 只執行 test + build，不部署
- **Tag Push**: 執行 test + build + deploy
- **Manual Dispatch**: 開發者手動觸發（可選擇是否部署）

**實作**：

```yaml
# 主要 workflow 觸發條件
on:
  push:
    branches: [staging]
    tags:
      - "dev[0-9]+.[0-9]+.[0-9]+-*"
  workflow_dispatch:
    inputs:
      deploy_firebase:
        description: "部署到 Firebase App Distribution"
        type: boolean
        default: false

jobs:
  check-deployment-eligibility:
    runs-on: ubuntu-latest
    outputs:
      should_deploy: ${{ steps.check.outputs.SHOULD_DEPLOY }}
    steps:
      - id: check
        run: |
          SHOULD_DEPLOY=false

          # Tag-based deployment
          if [ "${{ github.ref_type }}" = "tag" ] && [[ "${{ github.ref_name }}" =~ ^dev[0-9]+\.[0-9]+\.[0-9]+ ]]; then
            if [ "$CURRENT_BRANCH" = "staging" ]; then
              SHOULD_DEPLOY=true
            fi
          fi

          echo "SHOULD_DEPLOY=$SHOULD_DEPLOY" >> $GITHUB_OUTPUT

  deploy-firebase:
    needs: [build-android, check-deployment-eligibility]
    if: needs.check-deployment-eligibility.outputs.should_deploy == 'true' || (github.event_name == 'workflow_dispatch' && inputs.deploy_firebase)
    uses: ./.github/workflows/deploy-firebase.yml
```

**優點**：
- 清楚區分 build 和 deploy
- PR 和 branch push 不會意外觸發部署
- Tag 作為 release 的明確標記
- 方便追蹤哪個 build 被部署了

**如何觸發部署**：

```bash
# Development 部署
git tag dev0.7.1
git push origin dev0.7.1

# Production 部署
git tag v0.7.2
git push origin v0.7.2
```

#### Manual Deployment（緊急使用）

使用 `workflow_dispatch` 手動觸發：

```yaml
on:
  workflow_dispatch:
    inputs:
      deploy_firebase:
        description: "部署到 Firebase App Distribution (Android)"
        type: boolean
        default: false
      deploy_testflight:
        description: "部署到 TestFlight (iOS)"
        type: boolean
        default: false
```

**使用時機**：
- 緊急修復需要立即部署
- Tag push 失敗需要重新部署
- 測試特定的 commit

**操作步驟**：
1. 到 GitHub Actions 頁面
2. 選擇對應的 workflow（Development 或 Production）
3. 點擊 "Run workflow"
4. 選擇 branch
5. 勾選要部署的平台
6. 點擊 "Run workflow"

### 安全性考量 🔶 CI/CD 通用

#### Deployment 權限控制

**問題**：任何人 push tag 都會觸發部署，可能造成誤部署。

**解決方案**：

1. **Branch Protection Rules**：
   - 限制誰可以 push 到 main/staging
   - 要求 PR review
   - 要求 status checks 通過

2. **Tag Protection Rules**（GitHub Enterprise）：
   - 限制誰可以建立 `v*` tag
   - 要求特定權限才能觸發 production deployment

3. **Environment Protection Rules**：
   ```yaml
   jobs:
     deploy:
       environment: production  # 使用 GitHub Environment
   ```
   - 設定 Required reviewers
   - 設定 Wait timer
   - 限制哪些 branch 可以部署

4. **驗證 Branch 和 Tag 匹配**：
   ```yaml
   - name: Check deployment eligibility
     run: |
       if [ "${{ github.ref_type }}" = "tag" ]; then
         CURRENT_BRANCH=$(git branch -r --contains ${{ github.ref }} | grep -v HEAD | head -n 1)
         if [ "$CURRENT_BRANCH" != "origin/main" ]; then
           echo "ERROR: v tag must be on main branch"
           exit 1
         fi
       fi
   ```

### 分發平台整合

#### Firebase App Distribution 🔷 Flutter 專屬

**用途**：分發 Android APK 和 iOS IPA 給內部測試人員。

**設定步驟**：

1. **建立 Firebase 專案**
2. **產生 Service Account 金鑰**：
   - 到 Firebase Console → Project Settings → Service Accounts
   - 產生新的私密金鑰（JSON 檔案）
   - 將 JSON 內容 Base64 編碼並儲存為 GitHub Secret

3. **Workflow 實作**：
   ```yaml
   jobs:
     deploy-firebase:
       runs-on: ubuntu-latest
       steps:
         - name: Download APK
           uses: actions/download-artifact@v3
           with:
             name: android-development-apk

         - name: Set Firebase Credential
           env:
             FIREBASE_CREDENTIAL_BASE64: ${{ secrets.FIREBASE_APP_DISTRIBUTION_CREDENTIAL }}
           run: |
             FIREBASE_CREDENTIAL_FILE=$RUNNER_TEMP/firebase-credential.json
             echo -n "$FIREBASE_CREDENTIAL_BASE64" | base64 --decode -o $FIREBASE_CREDENTIAL_FILE
             echo "GOOGLE_APPLICATION_CREDENTIALS=$FIREBASE_CREDENTIAL_FILE" >> $GITHUB_ENV

         - name: Upload to Firebase App Distribution
           run: |
             firebase appdistribution:distribute "path/to/app.apk" \
               --app "${{ vars.FIREBASE_ANDROID_APP_ID }}" \
               --groups "internal-testers"
   ```

#### TestFlight

**用途**：分發 iOS IPA 給 TestFlight 測試人員。

**設定步驟**：

1. **建立 App Store Connect API Key**：
   - 到 App Store Connect → Users and Access → Keys
   - 建立新的 API Key（權限：App Manager）
   - 下載 `.p8` 檔案

2. **儲存為 GitHub Secrets**：
   - `APP_STORE_CONNECT_API_ISSUER_ID`
   - `APP_STORE_CONNECT_API_KEY_ID`
   - `APP_STORE_CONNECT_API_PRIVATE_KEY`（`.p8` 檔案內容）

3. **Workflow 實作**（使用 Codemagic CLI Tools）：
   ```yaml
   jobs:
     deploy-testflight:
       runs-on: macos-latest
       env:
         APP_STORE_CONNECT_ISSUER_ID: ${{ secrets.APP_STORE_CONNECT_API_ISSUER_ID }}
         APP_STORE_CONNECT_KEY_IDENTIFIER: ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }}
         APP_STORE_CONNECT_PRIVATE_KEY: ${{ secrets.APP_STORE_CONNECT_API_PRIVATE_KEY }}
       steps:
         - name: Install Codemagic CLI Tools
           run: pip3 install codemagic-cli-tools

         - name: Download IPA
           uses: actions/download-artifact@v3
           with:
             name: ios-production-ipa

         - name: Upload to TestFlight
           run: |
             app-store-connect publish \
               --path "path/to/app.ipa" \
               --testflight
   ```

#### Google Play Console

**用途**：上架 Android AAB 到 Google Play。

**設定步驟**：

1. **建立 Service Account**：
   - 到 Google Cloud Console 建立 Service Account
   - 到 Google Play Console 授予權限

2. **Workflow 實作**（使用 Fastlane）：
   ```yaml
   - name: Upload to Google Play
     run: |
       fastlane supply \
         --aab "path/to/app.aab" \
         --track "internal" \
         --json_key "${{ secrets.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON }}"
   ```

---

## Self-hosted Runner 最佳實務 🔶 CI/CD 通用

### macOS Runner 配置

#### 為什麼需要 macOS

- **iOS Build**：只能在 macOS 上執行 Xcode build
- **Code Signing**：iOS code signing 需要 macOS keychain

#### Runner 設定

**安裝 Runner**：
1. 到 GitHub → Settings → Actions → Runners → New self-hosted runner
2. 選擇 macOS
3. 依照指示安裝並啟動 runner

**設定 Runner Labels**：
```yaml
runs-on: [self-hosted, macOS]
```

#### 資源清理策略

**問題**：build 產物累積會佔用大量硬碟空間。

**解決方案**：在 workflow 結束時清理快取。

```yaml
jobs:
  build-ios:
    steps:
      - name: Build iOS
        run: flutter build ios

      - name: Clean up caches
        if: always()  # 即使 build 失敗也要清理
        run: |
          echo "Cleaning up iOS build caches..."
          rm -rf build/
          rm -rf .dart_tool/build/
          rm -rf ios/build/
          rm -rf ios/Pods/
          echo "iOS build cleanup completed."
```

**建議清理的目錄**：
- `build/`（Flutter build 產物）
- `.dart_tool/build/`（Dart build 快取）
- `ios/build/`（Xcode build 產物）
- `ios/Pods/`（CocoaPods 快取）
- `android/build/`（Gradle build 產物）
- `android/.gradle/`（Gradle 快取）

#### Keychain 管理

**問題**：iOS code signing 需要將憑證加入 keychain，但不應影響 macOS 系統的 login keychain。

**解決方案**：使用 Codemagic CLI Tools 建立臨時 keychain。

```yaml
- name: Set up temporary keychain
  run: keychain initialize

- name: Add certificates
  run: keychain add-certificates

- name: Restore the original keychain
  if: always()
  run: keychain use-login
```

**優點**：
- 不污染系統 keychain
- build 結束後自動清理
- 避免憑證衝突

---

## Secrets 管理 🔶 CI/CD 通用

### Android Signing

#### 設定步驟

1. **將 keystore 轉為 Base64**：
   ```bash
   base64 -i your_keystore.jks -o keystore_base64.txt
   ```

2. **儲存為 GitHub Secrets**：
   - `KEY_STORE_BASE64`（keystore 的 Base64 編碼）
   - `KEY_STORE_PASSWORD`
   - `KEY_ALIAS`
   - `KEY_PASSWORD`

3. **在 CI 中動態建立 keystore**：
   ```yaml
   - name: Create keystore file
     env:
       KEY_STORE_BASE64: ${{ secrets.KEY_STORE_BASE64 }}
     run: |
       KEY_STORE_FILE_PATH=$RUNNER_TEMP/your_keystore.jks
       echo "KEY_STORE_FILE_PATH=$KEY_STORE_FILE_PATH" >> $GITHUB_ENV
       echo -n "$KEY_STORE_BASE64" | base64 --decode -o $KEY_STORE_FILE_PATH

   - name: Build APK
     env:
       KEY_STORE_PASSWORD: ${{ secrets.KEY_STORE_PASSWORD }}
       KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
       KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
     run: flutter build apk
   ```

4. **清理 keystore**：
   ```yaml
   - name: Clean up
     if: always()
     run: rm -f $RUNNER_TEMP/your_keystore.jks
   ```

**優點**：
- keystore 不需要存在 repository 中
- 每次 build 動態建立，用完即刪
- 安全性高

### iOS Signing

#### 使用 Codemagic CLI Tools

**設定步驟**：

1. **建立 App Store Connect API Key**（見 [TestFlight](#testflight)）

2. **建立 Distribution Certificate**：
   - 到 Apple Developer → Certificates → Create Certificate
   - 選擇 "iOS Distribution"
   - 下載 `.cer` 檔案
   - 從 Keychain Access 匯出私鑰為 `.p12` 檔案
   - 轉為 Base64：
     ```bash
     base64 -i certificate_private_key.p12 -o cert_key_base64.txt
     ```

3. **儲存為 GitHub Secrets**：
   - `APP_STORE_CONNECT_API_ISSUER_ID`
   - `APP_STORE_CONNECT_API_KEY_ID`
   - `APP_STORE_CONNECT_API_PRIVATE_KEY`
   - `DISTRIBUTION_CERTIFICATE_PRIVATE_KEY_BASE64`

4. **在 CI 中使用**：
   ```yaml
   - name: Create certificate private key file
     run: |
       CERT_KEY_PATH=$RUNNER_TEMP/cert_private_key.pem
       echo "CERT_KEY_PATH=$CERT_KEY_PATH" >> $GITHUB_ENV
       echo "$CERTIFICATE_PRIVATE_KEY" | base64 --decode > $CERT_KEY_PATH

   - name: Fetch code signing files from App Store Connect
     run: |
       app-store-connect fetch-signing-files "$BUNDLE_ID" \
         --platform IOS \
         --type IOS_APP_STORE \
         --certificate-key=@file:$CERT_KEY_PATH \
         --create

   - name: Add certificates to keychain
     run: keychain add-certificates
   ```

**優點**：
- 自動從 App Store Connect 下載 provisioning profile
- 自動管理 keychain
- 不需要手動更新憑證

---

## 進階模式

### Concurrency Control 🔶 CI/CD 通用

#### 取消進行中的 Build

**問題**：開發者快速推送多個 commit，導致多個 build 同時執行。

**解決方案**：使用 `concurrency` 取消舊的 build。

```yaml
concurrency:
  group: development-${{ github.ref }}
  cancel-in-progress: true
```

**說明**：
- `group`: 定義 concurrency group（相同 group 的 workflow 會互相影響）
- `cancel-in-progress`: 當新的 workflow 啟動時，取消進行中的舊 workflow

#### Development vs Production 差異

**Development**：
```yaml
concurrency:
  group: development-${{ github.ref }}
  cancel-in-progress: true  # 取消舊的 build
```

**Production**：
```yaml
concurrency:
  group: production-${{ github.ref }}
  cancel-in-progress: false  # 不取消，確保每個 build 都完成
```

**為什麼**：
- Development 環境變化快，舊的 build 沒有意義
- Production 環境需要穩定，每個 build 都應該完整執行

### Artifact Management 🔶 CI/CD 通用

#### 命名規範

**使用有意義的 artifact 名稱**：

```yaml
- name: Upload Android APK
  uses: actions/upload-artifact@v3
  with:
    name: android-${{ inputs.environment }}-apk
    path: build/app/outputs/flutter-apk/*.apk
```

**命名模式**：
- `android-development-apk`
- `android-production-aab`
- `ios-development-ipa`
- `ios-production-ipa`

**優點**：
- 清楚知道 artifact 的內容和環境
- 避免名稱衝突
- 方便在後續 job 中下載

#### Retention 策略

**設定 artifact 保留天數**：

```yaml
- uses: actions/upload-artifact@v3
  with:
    name: android-development-apk
    retention-days: 7  # 7 天後自動刪除
```

**建議**：
- **Development**: 7 天（頻繁 build，不需要長期保留）
- **Production**: 30-90 天（可能需要回溯測試）
- **Release artifacts**: 永久保留（使用 GitHub Releases）

#### 檔案重新命名

**在上傳前重新命名 artifact**：

```yaml
- name: Rename Android APK
  run: |
    cd build/app/outputs/flutter-apk/
    mv app-release.apk "myapp-${{ env.APP_VERSION }}+${{ env.BUILD_NUMBER }}-${{ env.BRANCH_NAME }}.apk"

- uses: actions/upload-artifact@v3
  with:
    name: android-production-apk
    path: build/app/outputs/flutter-apk/*.apk
```

**範例檔名**：`myapp-1.2.3+2601000015-main.apk`

**優點**：
- 下載後立即知道版本和 build number
- 方便歸檔和管理

---

## 故障排除

### 常見 CI 失敗原因

#### 1. Secrets 未設定或錯誤

**錯誤訊息**：
```text
Error: Unable to locate credentials
```

**解決方法**：
- 檢查 GitHub Settings → Secrets 是否設定正確
- 檢查 Secret 名稱拼寫是否正確
- 檢查 workflow 中的 `secrets` 是否正確引用

#### 2. Build 快取問題

**錯誤訊息**：
```text
Error: Gradle build failed with exit code 1
```

**解決方法**：
- 在 workflow 中加入清理步驟（見 [資源清理策略](#資源清理策略)）
- 手動清理 runner 的快取目錄

#### 3. iOS Code Signing 失敗

**錯誤訊息**：
```text
error: No signing certificate "iOS Distribution" found
```

**解決方法**：
- 檢查 App Store Connect API Key 權限
- 檢查 Distribution Certificate 是否過期
- 檢查 Bundle ID 是否已在 Apple Developer 註冊

#### 4. Tag/Branch 不匹配

**錯誤訊息**：
```text
WARNING: dev tag found on branch 'main' instead of 'staging' - deployment skipped
```

**解決方法**：
- 確認在正確的 branch 上 push tag
- Development tag (`dev*`) 應該在 `staging` branch
- Production tag (`v*`) 應該在 `main` branch

### Debug 技巧

#### 1. 啟用 Debug Logging

```yaml
- name: Debug Info
  run: |
    echo "Event: ${{ github.event_name }}"
    echo "Ref: ${{ github.ref }}"
    echo "Ref Type: ${{ github.ref_type }}"
    echo "Ref Name: ${{ github.ref_name }}"
    echo "Branch: ${{ github.head_ref || github.ref_name }}"
```

#### 2. 上傳 Build Logs

```yaml
- name: Upload Build Logs
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: build-logs
    path: |
      build/
      .dart_tool/
      ios/build/
```

#### 3. Slack 通知

```yaml
- name: Notify Failure
  if: failure()
  run: |
    curl -X POST -H 'Content-type: application/json' \
      --data '{"text":"Build failed: ${{ github.repository }} - ${{ github.ref }}"}' \
      ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Log 分析

**關鍵字**：
- `error:`：錯誤訊息
- `warning:`：警告訊息
- `FAILURE`：build 失敗
- `Exception`：例外狀況

**常見錯誤模式**：

1. **Gradle 錯誤**：
   ```text
   FAILURE: Build failed with an exception.
   ```
   → 檢查 `android/app/build.gradle.kts`

2. **Xcode 錯誤**：
   ```text
   error: Signing for "Runner" requires a development team.
   ```
   → 檢查 code signing 設定

3. **Flutter 錯誤**：
   ```text
   Error: Could not resolve the package 'xxx' in 'file:///...'
   ```
   → 執行 `flutter pub get`

---

## 總結

本文介紹了 Flutter 專案的 CI/CD 最佳實務，涵蓋：

1. **Workflow 架構**：使用 reusable workflow 提高可維護性
2. **版本管理**：奇偶數 patch 策略和自動版本提升
3. **Build Number**：YYMMXXXXX 格式和 metadata branch 模式
4. **Deployment**：Tag-based deployment 和多平台整合
5. **Runner 管理**：Self-hosted runner 配置和資源清理
6. **Secrets 管理**：Android keystore 和 iOS code signing
7. **進階技巧**：Concurrency control 和 artifact management

這些模式大多可應用於其他框架的 CI/CD，特別標示 🔶 的部分為通用技術，🔷 的部分為 Flutter 專屬。

---

## 參考資源

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Reusing Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [Flutter CI/CD](https://docs.flutter.dev/deployment/cd)
- [Codemagic CLI Tools](https://github.com/codemagic-ci-cd/cli-tools)
- [Fastlane for Flutter](https://docs.fastlane.tools/)
