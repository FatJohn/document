CICD 建置 - 整合 GitHub Action - iOS 篇
===

## 準備 Runner 環境

1. 取得 Apple Developer Account ([Apple Developer](https://developer.apple.com/account))
1. 安裝 Xcode
1. 安裝 Xcode Command Line Tools
   - `xcode-select --install`
1. 安裝 [Cocoapods](https://cocoapods.org/)
   - `brew install cocoapods`

## 準備及新增建置時候需要的 secrets 和 variable 到 GitHub 中

要能夠單純化 runner 建置的環境，避免要手動要放置各種檔案到特定位置後才可以建置，所以把必要的檔案、變數、密碼等等都放到 GitHub 當作環境變數，然後在 Flow 執行的過程中能夠動態自動的產生或取得

可以到 repo 的 `Settings` 中，左方的 `Secrets and variables` 點下後選 `Actions` 來管理 secrets 和 variable

> secrets, variable 的名稱均可以自行討論決定

要取得及新增的項目如下

1. 建置相關
   - Apple Developer Certificate 檔案 (p12) 及 檔案密碼
   - [不需要了，保留記錄用] Mobile provisioning profile for the app
   - ExportOptions.plist
   - 一個建立建置時使用的 Keychain 的密碼
   - worksapce name
   - app name
   - scheme name   
1. 上傳到 Test flight 的 App Store Connect API 相關
   - App Store Connect API Issuer ID
   - App Store Connvet API Key ID
   - App Store Connect API Private key 檔案 (p8)

下面分別就各項東西怎麼準備說明

### Apple Developer Certificate 檔案 (p12) 及 檔案密碼

#### 取得檔案步驟

匯出步驟
1. 打開 Keychain App
2. 點選左邊 `登入`
3. 切換到 `憑證` 頁簽
4. 找到 `Appple Development` 開頭的憑證
5. 在上麵右鍵點選 `輸出`

會出時會要求你設定密碼，這個密碼就是要使用該檔案的 `檔案密碼` 然後成功會出的 p12 檔案就是 **Apple Developer Certificate 檔案 (p12)**

#### 新增 Secrets

##### `BUILD_CERTIFICATE_BASE64`

假設匯出的憑證 p12 檔案名稱是 Certificates.p12

使用指令

``` bash
base64 -i Certificates.p12 | pbcopy
```

將檔案轉換成 base64 並且複製到記憶體後，貼在該 secrets 的內容

##### `P12_PASSWORD`

將匯出憑證使用的密碼鍵入

### [不需要了，保留記錄用] Mobile provisioning profile for the app

#### 取得方式
- Apple Developer 裡面產生
  - Reference: [Apple Developer — Certificates & Provisioning Profiles](https://kiran-sarella.medium.com/apple-developer-certificates-provisioning-profiles-3fd3467a9c96)
- 從開發者本機取得
  - 路徑是：`~/Library/Developer/Xcode/UserData/Provisioning Profiles`
  - 舊一點版本的 xcode 會放置於：`~/Library/MobileDevice/Provisioning Profiles`

每個 App 會有各自的，所以不同 App 要使用不同的檔案，所以要找取得對的檔案，可以用用文字編輯器打開檔案看裡面的資訊，可以知道哪一個是你要的

上述的方式均可以取得 mobile provision 的檔案，但其實 mobile provision 是有期限的，根據 [Xcode Provisioning Profile Automation for CI](https://www.testdevlab.com/blog/xcode-provisioning-profile-automation-for-ci) 後來 Apple 有出一個可以自動更新 provision profile 的方式，只要在 project 檔案打勾，並且在下指令 archive 的時候補上一個參數即可

> 備註：文章中說的參數是 `-allowProvisioningUpdates` 但文章中的範例有錯誤，這個參數只能下在 archive 的時候，如果下在 exportArchive 的話，CI 執行到最後會出現 export ipa 成功但那個 step 會失敗因為不認得 `-allowProvisioningUpdates` 是什麼

#### 新增 secrets

##### `BUILD_PROVISION_PROFILE_BASE64`

假設 mobileprovision 檔案名稱是 1d0e8da1-9eba-41c7-a308-931ba380c3b0.mobileprovision
``` bash
base64 -i 1d0e8da1-9eba-41c7-a308-931ba380c3b0.mobileprovision | pbcopy
```

將檔案轉換成 base64 並且複製到記憶體後，貼在該 secrets 的內容

### ExportOptions.plist

#### 取得方式

ExportOptions.plist 需要先使用 xcode 產生，可以透過 xcode 執行 archive 然後 distribute，在 distribute 的時候選 `Release Testing` ( 主要是要使用 **ad-hoc** 的方式 ) 去產生 IPA 檔案後，在輸出的目錄就會得到一個 ExportOptions.plist

不同的 scheme 有可能會需要不同的 ExportOptions.plist，因為 bundler id 是不同的，意思就是如果同一個用不同的 scheme 分正式版和開發版，並且裡面的 bundler 是不同的，那就要產生兩份 ExportOptions.plist 使用

#### 新增 secrets

##### `EXPORT_OPTIONS_PLIST`

使用指令
``` bash
base64 -i ExportOptions.plist | pbcopy
```

將檔案轉換成 base64 並且複製到記憶體後，貼在該 secrets 的內容

### 一個建立建置時使用的 Keychain 的密碼

#### 取得方式

自行決定一個強密碼

#### 新增 secrets

##### `KEYCHAIN_PASSWORD`

將密碼鍵入

### 其他

#### 新增 variables

##### `IOS_APP_NAME`

用於 build archive, export ipa 的名稱

#### `IOS_SCHEME_NAME`

建置的時候要使用的 scheme name，僅需名稱不用副檔名

#### `IOS_WORKSPACE_NAME`

建置的時候要使用的 workspace name，僅需名稱不用副檔名

### App Store Connect API 相關

#### 取得方式

可以看 [Generating Tokens for API Requests](https://developer.apple.com/documentation/appstoreconnectapi/generating-tokens-for-api-requests) 以及 [Creating API Keys for App Store Connect API](https://developer.apple.com/documentation/appstoreconnectapi/creating-api-keys-for-app-store-connect-api) 來產生及建立 Apple Store Connect API Key

大致上步驟如下

開啟 [App Store Connect 網站](https://appstoreconnect.apple.com/) 後，點選 `使用者與存取權限`，然後點上方的 `整合` 後就可以看到左邊的一排的功能列出現有 `App Store Connect API` (預設)

- 在畫面上可以看到 **Issuer ID** 下面呈現的一串字串就是 `App Store Connect API Issuer ID`  
- 下方的 API Key 的表格可上就可以看到 **金鑰 ID** 欄位，該欄位所呈現的就是 `App Store Connvet API Key ID`  
- **App Store Connect API Private key 檔案 (p8)** 僅在剛建立 API Key 的最後步驟可以下載，建立之後就無法再次下載，所以請謹慎保存

> Private key 預設的檔名是 `Auth_xxxx.p8` 在上傳到 test flight 的時候要有一模一樣的名稱的檔案存在一些規範中的路徑才可以被找到

#### 新增 secrets

##### `APP_STORE_CONNECT_API_ISSUER_ID`

填入(複製貼上) `App Store Connect API Issuer ID`  的值

#### `APP_STORE_CONNECT_API_KEY_ID`

填入（複製貼上） `App Store Connvet API Key ID`

#### `APP_STORE_CONNECT_API_PRIVATE_KEY`

假設下載的 private key 檔案名稱是 Auth_1234.p8

使用指令

``` bash
base64 -i Auth_1234.p8 | pbcopy
```

將檔案轉換成 base64 並且複製到記憶體後，貼在該 secrets 的內容

## 準備 GitHub Action 要用的 YAML 檔案

### 新增 YAML 檔案

1. 在 repo 的根目錄新增 `.github/workflows` 共 2 個資料夾
2. 在 `.github/workflows` 的資料夾中新增 `{YOUR_WORKFLOW_NAME}.yaml` 檔案

> 要讓 github action 有作用，需要在 default branch 新增這個 yaml 檔案，所以開發測試角度來說可以先建立一個空的，然後再開 branch 去調整

可以根據 [Writing workflows](https://docs.github.com/en/actions/writing-workflows) 來寫 Workflow YAML，這邊提供 iOS 的範例，可以再依照需求作調整

### YAML 的內容

這邊以 大運動家 app 使用的 YAML 舉例，說明 YAML 中哪些 step 對於建置 iOS App 時候哪些是必要的，以及額外補充說明一些用 Gtihub action 的心得技巧

``` YAML
name: "Build iOS app"

on:
  # allow manual trigger
  workflow_dispatch:
  # trigger push to main branch with tag start with "v"
  push:
    branches:
      - main
      - develop
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+*'
      - 'dev[0-9]+.[0-9]+.[0-9]+*'
  # trigger pull request for all branches    
  pull_request:
    types: [opened, synchronize, reopened]
    branches:
      - '*'

jobs:
  build_and_upload:
    runs-on: [self-hosted, macOS]
    steps:
      # this was more debug as was curious what came pre-installed
      # GitHub shares this online, e.g. https://github.com/actions/runner-images/blob/macOS-12/20230224.1/images/macos/macos-12-Readme.md
      - name: Check Xcode version
        run: /usr/bin/xcodebuild -version

      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Get branch name (push branch)
        if: github.ref_type == 'branch'
        run: |
          echo "CURRENT_BRANCH=${{ github.event_name == 'pull_request' && github.head_ref || github.ref_name }}" >> $GITHUB_ENV
          echo "CURRENT_TAG=" >> $GITHUB_ENV

      - name: Get branch name (push tag)
        if: github.ref_type == 'tag'
        run: |
          echo "CURRENT_TAG=${{ github.ref_name }}" >> $GITHUB_ENV
          
          BRANCHES=$(git branch -r --contains ${{ github.ref }} | grep -v HEAD | tr -d ' ' | sed 's/origin\///')
          if echo "$BRANCHES" | grep -q "main"; then
            CURRENT_BRANCH="main"
          else
            CURRENT_BRANCH=$(echo "$BRANCHES" | awk 'NR==1{print $1}')
          fi

          echo "CURRENT_BRANCH=$CURRENT_BRANCH" >> $GITHUB_ENV

      - name: Current branch name and tag name
        env:
          CURRENT_BRANCH: ${{ env.CURRENT_BRANCH }}
          CURRENT_TAG: ${{ env.CURRENT_TAG }}
        run: |
          echo "Current Branch: $CURRENT_BRANCH. Current Tag: $CURRENT_TAG"          

      - name: Install the Apple certificate and provisioning profile
        env:
          BUILD_CERTIFICATE_BASE64: ${{ secrets.BUILD_CERTIFICATE_BASE64 }}
          P12_PASSWORD: ${{ secrets.P12_PASSWORD }}
          KEYCHAIN_PASSWORD: ${{ secrets.KEYCHAIN_PASSWORD }}
        run: |
          # Store original keychain settings
          ORIGINAL_KEYCHAIN=$(security default-keychain -d user | xargs)
          echo "ORIGINAL_KEYCHAIN=$ORIGINAL_KEYCHAIN" >> $GITHUB_ENV
          
          # create variables
          BUILD_CERTIFICATE_PATH=$RUNNER_TEMP/build_certificate.p12
          PP_PATH=$RUNNER_TEMP/build_pp.mobileprovision
          KEYCHAIN_PATH=$RUNNER_TEMP/app-signing.keychain-db

          # import certificate and provisioning profile from secrets
          echo -n "$BUILD_CERTIFICATE_BASE64" | base64 --decode -o $BUILD_CERTIFICATE_PATH

          # create temporary keychain
          security create-keychain -p "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH
          security set-keychain-settings -lut 21600 $KEYCHAIN_PATH
          security unlock-keychain -p "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH

          # import certificate to keychain
          security import $BUILD_CERTIFICATE_PATH -P "$P12_PASSWORD" -A -t cert -f pkcs12 -k $KEYCHAIN_PATH
          security list-keychain -d user -s $KEYCHAIN_PATH

          # 避免彈出 Keychain UI 問你密碼
          security set-key-partition-list -S apple-tool:,apple: -s -k $KEYCHAIN_PASSWORD $KEYCHAIN_PATH

      - name: Create App Store Connect API Key File
        env:
          APP_STORE_CONNECT_API_KEY_ID: ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }}
          APP_STORE_CONNECT_API_PRIVATE_KEY: ${{ secrets.APP_STORE_CONNECT_API_PRIVATE_KEY }}
        run: |
          # 要把 p8 檔案放置於 private_keys 資料夾下，才可以讓 xcodebuild altool 的時候方便使用（不需要特別指定參數）
          APP_STORE_CONNECT_API_PRIVATE_KEY_PATH=./private_keys/AuthKey_$APP_STORE_CONNECT_API_KEY_ID.p8

          # import app store connect api private key from secrets
          mkdir -p private_keys
          echo -n "$APP_STORE_CONNECT_API_PRIVATE_KEY" | base64 --decode -o $APP_STORE_CONNECT_API_PRIVATE_KEY_PATH

          # transform relative path to absolute path
          APP_STORE_CONNECT_API_PRIVATE_KEY_PATH=$(realpath $APP_STORE_CONNECT_API_PRIVATE_KEY_PATH)
          echo "APP_STORE_CONNECT_API_PRIVATE_KEY_PATH=$APP_STORE_CONNECT_API_PRIVATE_KEY_PATH" >> $GITHUB_ENV
      
      - name: Clean Derived Data (before build)
        run: rm -rf ~/Library/Developer/Xcode/DerivedData/*
            
      - name: Build archive
        env:
          IOS_APP_NAME: ${{ vars.IOS_APP_NAME }}
          IOS_SCHEME_NAME_PRODUCTION: ${{ vars.IOS_SCHEME_NAME }}
          IOS_SCHEME_NAME_DEV: ${{ vars.IOS_SCHEME_NAME_DEV }}
          IOS_WORKSPACE_NAME: ${{ vars.IOS_WORKSPACE_NAME }}
          CURRENT_BRANCH: ${{ env.CURRENT_BRANCH }}
          CURRENT_TAG: ${{ env.CURRENT_TAG }}
          APP_STORE_CONNECT_API_KEY_ID: ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }}
          APP_STORE_CONNECT_API_ISSUER_ID: ${{ secrets.APP_STORE_CONNECT_API_ISSUER_ID }}
          APP_STORE_CONNECT_API_PRIVATE_KEY_PATH: ${{ env.APP_STORE_CONNECT_API_PRIVATE_KEY_PATH }}
        run: |
          # setup scheme name
          if [ $CURRENT_BRANCH == 'main' ] && echo "$CURRENT_TAG" | grep -Eq "^v[0-9]+\.[0-9]+\.[0-9]+$"; then
            SCHEME_NAME=$IOS_SCHEME_NAME_PRODUCTION
          else
            SCHEME_NAME=$IOS_SCHEME_NAME_DEV
          fi

          echo "Building $SCHEME_NAME scheme"

          # build archive
          xcodebuild -workspace "$IOS_WORKSPACE_NAME.xcworkspace" \
            -scheme "$SCHEME_NAME" \
            -archivePath $RUNNER_TEMP/$IOS_APP_NAME.xcarchive \
            -sdk iphoneos \
            -configuration Release \
            -allowProvisioningUpdates \
            -authenticationKeyIssuerID "$APP_STORE_CONNECT_API_ISSUER_ID" \
            -authenticationKeyID "$APP_STORE_CONNECT_API_KEY_ID" \
            -authenticationKeyPath "$APP_STORE_CONNECT_API_PRIVATE_KEY_PATH" \
            clean archive || exit 1

      - name: Export ipa
        env:
          IOS_APP_NAME: ${{ vars.IOS_APP_NAME }}
          EXPORT_OPTIONS_PLIST: ${{ secrets.EXPORT_OPTIONS_PLIST }}
          CURRENT_BRANCH: ${{ env.CURRENT_BRANCH }}
          CURRENT_TAG: ${{ env.CURRENT_TAG }}
          APP_STORE_CONNECT_API_KEY_ID: ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }}
          APP_STORE_CONNECT_API_ISSUER_ID: ${{ secrets.APP_STORE_CONNECT_API_ISSUER_ID }}
          APP_STORE_CONNECT_API_PRIVATE_KEY_PATH: ${{ env.APP_STORE_CONNECT_API_PRIVATE_KEY_PATH }}
        run: |
          # setup export options plist
          EXPORT_OPTS_PATH=$RUNNER_TEMP/ExportOptions.plist

          echo -n "$EXPORT_OPTIONS_PLIST" | base64 --decode -o $EXPORT_OPTS_PATH
          
          # export ipa
          xcodebuild -exportArchive \
            -archivePath $RUNNER_TEMP/$IOS_APP_NAME.xcarchive \
            -exportOptionsPlist $EXPORT_OPTS_PATH \
            -exportPath $RUNNER_TEMP/build \
            -allowProvisioningUpdates \
            -authenticationKeyIssuerID "$APP_STORE_CONNECT_API_ISSUER_ID" \
            -authenticationKeyID "$APP_STORE_CONNECT_API_KEY_ID" \
            -authenticationKeyPath "$APP_STORE_CONNECT_API_PRIVATE_KEY_PATH" \

      - name: Upload to TestFlight
        if: github.ref_type == 'tag'
        env:
          APP_STORE_CONNECT_API_KEY_ID: ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }}
          APP_STORE_CONNECT_API_ISSUER_ID: ${{ secrets.APP_STORE_CONNECT_API_ISSUER_ID }}
          CURRENT_BRANCH: ${{ env.CURRENT_BRANCH }}
          CURRENT_TAG: ${{ env.CURRENT_TAG }}
        run: |
          # check if branch name and tag name is what we want
          if [ $CURRENT_BRANCH == 'main' ] && echo "$CURRENT_TAG" | grep -Eq "^v[0-9]+\.[0-9]+\.[0-9]+$"; then
            OK_TO_UPLOAD=true
          elif [ $CURRENT_BRANCH == 'develop' ] && echo "$CURRENT_TAG" | grep -Eq "^dev[0-9]+\.[0-9]+\.[0-9]+$"; then
            OK_TO_UPLOAD=true
          else
            OK_TO_UPLOAD=false
          fi

          if ! $OK_TO_UPLOAD; then
            echo 'Tag name not fits rule'
            exit 1
          fi

          IPA_FILE_PATH=$(find $RUNNER_TEMP/build -name "*.ipa" -print0 | xargs -0 echo | head -n 1)
          echo "IPA file path: $IPA_FILE_PATH"

          xcrun altool --upload-app \
            -t ios \
            --apiKey "$APP_STORE_CONNECT_API_KEY_ID" \
            --apiIssuer "$APP_STORE_CONNECT_API_ISSUER_ID" \
            -f "$IPA_FILE_PATH" || exit 1

      - name: Clean up keychain and provisioning profile
        if: ${{ always() }}
        run: |
          # Clean up keychain
          security delete-keychain $RUNNER_TEMP/app-signing.keychain-db
          # Clean Derived Data
          rm -rf ~/Library/Developer/Xcode/DerivedData/*

      - name: Restore original keychain
        if: always()  # This ensures it runs even if previous steps fail
        env:
          ORIGINAL_KEYCHAIN: ${{ env.ORIGINAL_KEYCHAIN }}
        run: |
          security default-keychain -s "$ORIGINAL_KEYCHAIN"
          security list-keychains -s "$ORIGINAL_KEYCHAIN"
```

### Install the Apple certificate and provisioning profile

這步驟的目的就是把放在 GitHub secrets 中的東西做下列事情
- 把 `secrets.BUILD_CERTIFICATE_BASE64` (開發者憑證內容) 變成實體檔案 (p12)
- 把 `secrets.BUILD_PROVISION_PROFILE_BASE64` (mobileprovision 檔案內容) 變成實體檔案
- 使用 `secrets.KEYCHAIN_PASSWORD` 來建立一個叫 **app-signing** 的 keychain
- 使用 `secrets.P12_PASSWORD` 把開發者憑證檔案匯入到 **app-signing** keychain 中

### Create App Store Connect API Key File
把 App Store Connect API 的 private key (`secrets.APP_STORE_CONNECT_API_PRIVATE_KEY`) 轉化成實體檔案 (p8) 並且放置於 <current_directory>/private_keys 的路徑

此檔案會在 xcbuild archive/exportArchive 使用到，並且於上傳 Testflight 的 xcbuild altool 使用

altool 會自動尋找該檔案，會自動尋找的路徑其中一個地方就是 `<current_directory>/private_keys`，所以這邊放置於此，另外檔案名稱也要注意，要與當初下載時的名稱一樣

> 詳細可以放置位置及工具使用說明請參考下方 `altool 使用指南 1.3` 連結，或者當出現錯誤的時候，錯誤訊息的內容會跟你說可以擺在哪一些路徑中

### Build archive

顧名思義，就是 archive 檔案，這邊的 scheme 是用動態決定的、有的東西是拿 GitHub variable 決定的，但沒有需要可以寫死也可以，這邊會這樣寫是方便如果要直接拿這份 YAML 去改的話，這邊就不用修改，只要在需使用的 repo 上面新增對應的 variable 即可

###  Export ipa

先把放在 GitHub secrets 中的 `secrets.EXPORT_OPTIONS_PLIST` 變成實體檔案，然後再去執行 export 指令

### 在 Build archive 及 Export ipa 步驟的重點
都指定下面四個參數

``` yaml
-allowProvisioningUpdates \
-authenticationKeyIssuerID "$APP_STORE_CONNECT_API_ISSUER_ID" \
-authenticationKeyID "$APP_STORE_CONNECT_API_KEY_ID" \
-authenticationKeyPath "$APP_STORE_CONNECT_API_PRIVATE_KEY_PATH" \
```

讓 xcodebuild 可以與 server 溝通自動做 sign & 取得 mobile provision profile，加上這幾個參數後，CI 機器上面的 XCode 就不需要登入

### Upload to TestFlight

因為 xcbuild exportArchive 的時候只能指定輸出的路徑不能包含檔名，所以不能確定最終的檔名是什麼，看起來是跟 archive 時候使用的 scheme name 一致，所以調整寫法直接用指令去尋找 IPA 檔案並上傳

### 補充：其他 first party 上傳 Test fligh 的方式

1. iTMSTransporter (CLI)
    
    使用 CLI 上傳 IPA 到 testflight 其實還有另外一個是 `iTMSTransporter` / `xcrun iTMSTransporter`

    根據官方文件 [Transporter User Guide 3.3](https://help.apple.com/itc/transporteruserguide/en.lproj/static.html) 中描述，在 xcode 14 之後就沒有內建了需要另外下載
    
    > 但我測試目前使用的 XCode 16 下 xcrun iTMSTransporter 還是可以執行，並且如果直接下 xcrun iTMSTransporter 還可以更新版本

    iTMSTransporter 似乎是比 altool 似乎更早出現的工具，上傳到 test flight 的時候雖然同 altool 一樣會需要把 private key 放到指定的一些目錄，但它有其他參數可以指定 JWT 的路徑，這個 JWT 想當然有包含 private key (p8) 的內容，要組成 JWT 可以參考 [Generating Tokens for API Requests](https://developer.apple.com/documentation/appstoreconnectapi/generating-tokens-for-api-requests)
    
    意思就是可以自己先把 private key 轉換成一個 App Store Connect API 所認得得 JWT 檔案，就不一定要把 private key 擺放在特定位置，但 JWT 必須動態產生，因為 JWT 是需要指定期限會過期

    另外，iTMSTransporter 雖然跟 altool 一樣可以尋找特定一些目錄去找 private keys 檔案 (p8) 來使用，但有遇到 2 個問題
      1. 不會找執行指令路徑下的 `<current_directory>/private_keys`
      2. 用 GitHub Runner 執行的話也即便放到規範的 `~/private_keys` 裡面會找不到，但如果自己直接下指令是正常的

    所以要使用 iTMSTransporter 的話應該要使用 JWT 的方式比較合用

1. XCode (GUI)
1. Transporter App (GUI, Install from App Store)

### Runner Keychain 的特別現象

手動執行完 workflow 後 Keychain 裡面的 `登入` 會消失，這可能會導致後續無法正常 build code，自動執行的話似乎不會遇到這種情況

所以可以看到 step 裡面有 保留 和 恢復 的步驟

## TO-DO
- [ ] `xcrun altool --upload-app` 已經被標示成 deprecated 需要找尋替代指令
  - 可能的替代方案
    - `fast-lane`
    - `xcrun altool --upload-package`
    - `xcrun iTMSTransporter`
    - 使用別人寫好的 [apple-actions](https://github.com/Apple-Actions)

## 參考資料

- [3 ways to install Xcode on macOS [2023]](https://www.andrewhoog.com/post/3-ways-to-install-xcode-on-macos/#2-apple-developer-website)
- [How to build an iOS app archive via command line](https://www.andrewhoog.com/post/how-to-build-an-ios-app-archive-via-command-line/#how-to-build-an-ios-app-archive-via-command-line)
- [How to build an iOS app with GitHub Actions [2023]](https://www.andrewhoog.com/post/how-to-build-an-ios-app-with-github-actions-2023/)
  - 此文件的根據文章
- [[Day:27] GitHub Actions 懶人部署-ios CI 基礎打包](https://ithelp.ithome.com.tw/articles/10251897)
  - 可以參考寫 build number 及有利用別人寫好的幾個 [apple-actions](https://github.com/Apple-Actions)
- [Xcode Provisioning Profile Automation for CI](https://www.testdevlab.com/blog/xcode-provisioning-profile-automation-for-ci)
- [脚本打包所需ExportOptions.plist文件生成](https://juejin.cn/post/6997226858022469639)
- [自动化流程完成 打包 IPA 到 上传 AppStore 之 iOS IPA签名](https://www.cnblogs.com/lesten/p/12695165.html)
  - 裡面有自己去下命令去 sign app 的，不確定為什麼他需要自己去 sign，因為 archive 的命令應該就會 code sign 了
- [一行命令解决 Codesign wants to access key “access” in your keychain](https://juejin.cn/post/6959116895681740837)
- [Distribute apps in Xcode with cloud signing](https://developer.apple.com/videos/play/wwdc2021/10204/?time=1194)

### 上傳 Test Flight 相關
- [上傳建置版本](https://developer.apple.com/tw/help/app-store-connect/manage-builds/upload-builds/)
  - 官方文件，上傳到 Test Fligh 用的指令範例是 `xcrun altool --upload-app`
- [altool 使用指南 1.3](https://help.apple.com/asc/appsaltool/#/)
- [Transporter User Guide 3.3](https://help.apple.com/itc/transporteruserguide/en.lproj/static.html)
  - 現在的版本已經到 3.4.x 了
- [利用 GitHub Actions 與 fastlane 將 iOS APP 發佈到 Apple Store Connect 的 TestFlight](https://medium.com/ddsakura-blog/%E5%88%A9%E7%94%A8-github-actions-%E8%88%87-fastlane-%E5%B0%87-ios-app-%E7%99%BC%E4%BD%88%E5%88%B0-apple-store-connect-%E7%9A%84-testfight-09861cd8c327)
- [Deploy iOS App to TestFlight with GitHub Actions & Fastlane](https://medium.com/swiftable/build-and-deploy-the-app-to-testflight-using-github-actions-with-fastlane-and-app-distribution-ff1786a8bf72)