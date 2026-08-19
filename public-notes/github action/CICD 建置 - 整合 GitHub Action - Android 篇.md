CICD 建置 - 整合 GitHub Action - Android 篇
===

## 準備 Runner 環境

### 必要
1. 安裝 Android Studio
1. 設定 Android Studio SDK Tools
   - 新增 Android SDK Command-line Tools
   - (如果有) 更新 Android SDK Build-Tools
1. 安裝 [Firebase CLI](https://firebase.google.com/docs/cli?hl=zh-tw#install_the_firebase_cli)
    - `curl -sL firebase.tools | bash`
    - [可選擇] 目前 firebase cli 應該是 x64 的，所以如果可能需要裝 rosetta `softwareupdate --install-rosetta`
1. 增加設定環境變數 (在 mac 上編輯 .zshrc 檔案)
    - 設定 `JAVA_HOME` 路徑與 Android Studio 的 GRADLE_LOCAL_JAVA_HOME 路徑相同
      - `export JAVA_HOME=/Applications/Android\ Studio.app/Contents/jbr/Contents/Home`
        - Android 2022.1.1 之後的路徑
        = Reference: [https://developer.android.com/build/jdks?hl=zh-tw#jdk-config-in-studio](https://developer.android.com/build/jdks?hl=zh-tw#jdk-gradle)
    - 設定 `ANDROID_HOME`
      - `export ANDROID_HOME=~/Library/Android/sdk`
    - 增加 PATH
      - `export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/tools/bin:$ANDROID_HOME/platform-tools`

因為 Android 這邊使用的是 KMP 來開發，所以有額外的東西需要安裝，根據 [Set up an environment](https://www.jetbrains.com/help/kotlin-multiplatform-dev/multiplatform-setup.html#check-your-environment) 有描述，或者可以照文件先安裝 kdoctor (`brew install kdoctor`) 然後執行 kdoctor 來看缺少什麼東西要安裝

基本上就是
- Java
- Android Studio
- XCode
- Android Studio 的 Kotlin Multiplatform plugin
- Cocoapods

> 目前 kdoctor 有 bug ，對於新版的 Android Studio 的偵測支援有問題，就是即便安裝了 Kotlin Multiplatform Plogin 它也無法辨認，已經有人發 PR 修正了，需要等待新版的 kdoctor 釋出

另外使用 KMP 的話跟 Andoid Studio 版本似乎會有衝突造成無法編譯的情況，所以以大運動家為例，就使用 Readme 上面建議的 2024.1.2

### 可選
1. 安裝 bundletoole [可選]
    - 方式 1 : 從 Google 的 repo 下載
      - 下載位置：[bundletool](https://github.com/google/bundletool/releases)
      - 下載後可以把 `bundletool.jar` 放到 `/usr/local/bin/` 下
      - 打開 .zshrc 新增 `alias bundletool="java -jar /usr/local/bin/bundletool.jar"`
        - 或者可以用 CLI : `echo 'alias bundletool="java -jar /usr/local/bin/bundletool.jar"' >> ~/.zshrc`
      - 這樣可以直接在 terminal 中用 `bundletool` 來執行
    - 方式 2 (在 MacOS) : 用 brew 安裝
      - ` brew install bundletool`
      - 安裝後預設就會幫你建立一個 bundletool 的捷徑（位於 `/opt/homebrew/bin`）可以在 terminal 中用 `bundletool` 來執行
      - **注意**
        - 使用此方式會額外下載一個 openJDK
        - 打開捷徑可以看到
          - 會調整執行時候的 `JAVA_HOME` 變數 `export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home}"`
          - 執行 bundletool 是用 `exec "${JAVA_HOME}/bin/java"  -jar` 來去執行，意思 `JAVA_HOME` 這個變數的設定優先順序會改變用來執行這個 bundletool jsr 檔案的 java 版本

## 準備及新增建置時候需要的 secrets 和 variable 到 GitHub 中

要能夠單純化 runner 建置的環境，避免要手動要放置各種檔案到特定位置後才可以建置，所以把必要的檔案、變數、密碼等等都放到 GitHub 當作環境變數，然後在 Flow 執行的過程中能夠動態自動的產生或取得

可以到 repo 的 `Settings` 中，左方的 `Secrets and variables` 點下後選 `Actions` 來管理 secrets 和 variable

> secrets, variable 的名稱均可以自行討論決定

要取得及新增的項目如下
- 建置相關
  - sign 用的 key store (.jks)
  - Module name
  - Google Play Package Name
- 上傳到 Firebase 的
  -  Firebase App Distritution Service Account Json
  -  Firebase 對應的 App ID
-  上傳到 Google Play 的
   - Google Play API Service Account Json
   - Google Play 的 ID
   - Google Play 的 track

> 上述 Firebase 和 Google Play API 的 Service Account JSON 是兩個項目，但其實可以用同一個即可，只要權限設定好即可

下面分別就各項東西怎麼準備說明

### sign 用的 key store (.jks)

參考 [Generate an upload key and keystore](https://developer.android.com/studio/publish/app-signing#generate-key) 建立一個 keystore 檔案(.jks)

> 注意：此檔案不要進版控

#### 新增 Secrets

##### `KEY_STORE_BASE64`

假設匯出的 key store 檔案名稱是 MyKeyStore.jks

使用指令

``` bash
base64 -i MyKeyStore.jks | pbcopy
```

將檔案轉換成 base64 並且複製到記憶體後，貼在該 secrets 的內容

要注意指令最後的換行要移除掉，不然在 CI 轉換成檔案後會不是一個合法的 keystore 檔案，進而導致 build apk fail

##### `KEY_STORE_PASSWORD`

步驟中建立 KeyStore 的密碼輸入進此 secret 

##### `KEY_ALIAS`

步驟中建立 KeyStore 的 Key 的 alias 輸入此 secret 

##### `KEY_PASSWORD`

步驟中建立 KeyStore 的 Key 的密碼輸入於此

> 注意：KeyStore 的密碼 和 KeyStore Key 的密碼要相同，在 [Generate an upload key and keystore](https://developer.android.com/studio/publish/app-signing#generate-key) 裡面有提到有個 Known issue [Error when using different passwords for key and keystore](https://developer.android.com/studio/known-issues#ki-key-keystore-warning)

### Firebase App Distribution Service Account Json

#### 取得步驟

參考這篇的操作 [FIREBASE_TOKEN migration](https://github.com/wzieba/Firebase-Distribution-Github-Action/wiki/FIREBASE_TOKEN-migration)

大致上就是
1. GCP Console
1. 選擇自己的 project （若還沒有 project 則要建立）
1. 點進去之後在左邊切換到 `服務帳戶`
1. 建立或選擇一個 Firebase App Distribution 的 account
1. 點進去 service account 後
1. 切換上方到 `金鑰` 的頁籤
1. 建立一把金鑰，並且保存好建立時候的 json 檔案，該檔案即是 service account json

此 json 檔案僅在建立時候可以下載，請妥善保存

#### 新增 Secrets

##### `FIREBASE_APP_DISTRIBUTION_CREDENTIAL_BASE64`

假設下載的 service account json 檔案名稱叫做 `firebase_credential.json`

使用指令
``` bash
base64 -i firebase_credential.json | pbcopy
```

將檔案轉換成 base64 並且複製到記憶體後，貼在該 secrets 的內容

> 避免直接把 json 文字直接貼到裡面，因為格式問題或者文字問題，可能會造成 GitHub Action 拿到內容存成檔案使用時會有類似 json 格式問題，導致 firebase 指令無法辨認 token 內容進而發生錯誤

### Firebase 對應的 App ID

#### 取得方式

1. 打開 Firebase Console
1. 進入自己的 App 的專案
1. 點開左側功能表的最上方 `專案總攬` 右邊的 `設定 icon` 進入 `專案設定`
1. 下方就可以看到 `您的應用程式`
1. 點選會上傳的應用程式
1. 畫面右邊就會有 `應用程式ID`

#### 新增 Secrets

#####  `FIREBASE_PACK_APP_ID`

把取得得`應用程式ID`貼入 secrets

### Google Play API Service Account Json

#### 取得步驟

參考的操作：[Google Play Credentials (Service Account JSON)](https://docs.apphud.com/docs/google-play-service-credentials)

大致上就是
1. GCP Console
1. 選擇自己的 project （若還沒有 project 則要建立）
1. 點進去之後在左邊切換到 `服務帳戶`
1. 建立或選擇一個 Firebase App Distribution 的 account，建立的時候記得給予的權限要對，請參考上方連結
1. 點進去 service account 後
1. 切換上方到 `金鑰` 的頁籤
1. 建立一把金鑰，並且保存好建立時候的 json 檔案，該檔案即是 service account json

#### 新增 Secrets

##### `GOOGLE_PLAY_API_CRDENTIAL_BASE64`

假設下載的 service account json 檔案名稱叫做 `google_play_credential.json`

使用指令
``` bash
base64 -i google_play_credential.json | pbcopy
```

將檔案轉換成 base64 並且複製到記憶體後，貼在該 secrets 的內容

> 避免直接把 json 文字直接貼到裡面，因為格式問題或者文字問題，可能會造成 GitHub Action 拿到內容存成檔案使用時會有類似 json 格式問題，導致 firebase 指令無法辨認 token 內容進而發生錯誤

### 其他

#### 新增 variables

##### `GOOGLE_PLAY_PACKAGE_NAME`

上傳到 Google Play 對應的 package name

##### `MAIN_PROJECT_MODULE_NAME`

可以使用 `./gradlew project` 列出來，是 android / compose project 的名稱，以大運動家為例是 `composeApp`

##### `FIREBASE_DISTRIBUTION_GROUPS`

請詢問相關人員是屬於哪一個 groups

> 大運動家是 `lab`

## 準備 GitHub Action 要用的 YAML 檔案

### 新增 YAML 檔案

1. 在 repo 的根目錄新增 `.github/workflows` 共 2 個資料夾
2. 在 `.github/workflows` 的資料夾中新增 `{YOUR_WORKFLOW_NAME}.yaml` 檔案

> 要讓 github action 有作用，需要在 default branch 新增這個 yaml 檔案，所以開發測試角度來說可以先建立一個空的，然後再開 branch 去調整

可以根據 [Writing workflows](https://docs.github.com/en/actions/writing-workflows) 來寫 Workflow YAML，這邊提供 Android 的範例，可以再依照需求作調整

### YAML 的內容

這邊以 大運動家 app 使用的 YAML 舉例，說明 YAML 中哪些 step 對於建置 iOS App 時候哪些是必要的，以及額外補充說明一些用 Gtihub action 的心得技巧

``` YAML
name: "Build Android app"

env:
  # The name of the main module repository
  MAIN_PROJECT_MODULE_NAME: ${{vars.MAIN_PROJECT_MODULE_NAME}}

# Allow dory/test-reporter create and upload test results
permissions:
  pull-requests: write
  contents: write
  statuses: write
  checks: write
  actions: write  

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
  lint:
    runs-on: [self-hosted, macOS]
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Lint
        env:
          INCLUDE_IOS: false
        run: ./gradlew lint

      - name: Check and report lint results
        uses: hidakatsuya/action-report-android-lint@v1.2.2
        with:
          result-path: '${{ env.MAIN_PROJECT_MODULE_NAME }}/build/reports/lint-results.xml'
          fail-on-warning: false

  unit-test:
    runs-on: [self-hosted, macOS]
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Unit Test
        env:
          INCLUDE_IOS: false        
        run: ./gradlew test

      - name: Create Test Report
        uses: dorny/test-reporter@v1.9.1
        if: success() || failure()
        with:
          name: Unit Test Results
          path: '${{ env.MAIN_PROJECT_MODULE_NAME }}/build/test-results/testDevDebugUnitTest/**.xml'
          reporter: java-junit
          fail-on-error: false
      
      - name: Upload Test Reports
        uses: actions/upload-artifact@v4
        if: ${{ always() }}
        with:
          name: reports
          path: ${{ env.MAIN_PROJECT_MODULE_NAME }}/build/test-results

  build_and_upload:
    needs: [unit-test, lint]
    runs-on: [self-hosted, macOS]
    env:
      # 對應 build.gradle.kts 中的 signingConfigs 區段的變數名稱
      KEY_STORE_PASSWORD: ${{ secrets.KEY_STORE_PASSWORD }}
      KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
      KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
    steps:
      - name: Checkout code
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
          
          CURRENT_BRANCH=$(git branch -r --contains ${{ github.ref }} | grep -v HEAD | head -n 1 | tr -d ' ' | sed 's/origin\///')
          echo "CURRENT_BRANCH=$CURRENT_BRANCH" >> $GITHUB_ENV

      - name: Grant execute permission for gradlew
        run: chmod +x gradlew

      - name: Create keystore file
        env:
          KEY_STORE_BASE64: ${{ secrets.KEY_STORE_BASE64 }}
        run: |
          # 因為現在 sign 的步驟是寫在 build.gradle.kts 中，所以這邊要先將 keystore 寫入檔案
          # 就不另外用 bundletool 來 sign 了
          KEY_STORE_FILE_PATH=$RUNNER_TEMP/your_keystore.jks
          echo "KEY_STORE_FILE_PATH=$KEY_STORE_FILE_PATH" >> $GITHUB_ENV
          echo -n "$KEY_STORE_BASE64" | base64 --decode -o $KEY_STORE_FILE_PATH

      - name: Build apk release project (APK)
        run: ./gradlew assemblePackRelease

      - name: Build app bundle release (AAB)
        run: ./gradlew bundlePubRelease

      - name: Set build artifacts path to environment variable
        env:
          UPLOAD_KEYSTORE: ${{ secrets.UPLOAD_KEYSTORE }}          
        run: |
          PACK_APK_FILE_PATH=$(ls ${{ env.MAIN_PROJECT_MODULE_NAME }}/build/outputs/apk/pack/release/*.* | head -1 | sed 's/\.[^.]*$/.apk/')
          PUB_AAB_FILE_PATH=$(ls ${{ env.MAIN_PROJECT_MODULE_NAME }}/build/outputs/bundle/pubRelease/*.* | head -1 | sed 's/\.[^.]*$/.aab/')

          echo "PACK_APK_FILE_PATH=$PACK_APK_FILE_PATH" >> $GITHUB_ENV
          echo "PUB_AAB_FILE_PATH=$PUB_AAB_FILE_PATH" >> $GITHUB_ENV
          echo "Pack Apk Path: $PACK_APK_FILE_PATH, Pub Aab Path: $PUB_AAB_FILE_PATH"

      - name: Check if need to upload to Firebase or Google Play
        run: |
          if [ $CURRENT_BRANCH == 'main' ] && echo "$CURRENT_TAG" | grep -Eq "^v[0-9]+\.[0-9]+\.[0-9]+$"; then
            UPLOAD_TO='googleplay'
          elif [ $CURRENT_BRANCH == 'develop' ] && echo "$CURRENT_TAG" | grep -Eq "^dev[0-9]+\.[0-9]+\.[0-9]+$"; then
            UPLOAD_TO='firebase'
          else
            UPLOAD_TO='none'
          fi

          echo "Place to upload: $UPLOAD_TO"
          echo "UPLOAD_TO=$UPLOAD_TO" >> $GITHUB_ENV

      - name: Set Firebase App Distribution Credential
        if: env.UPLOAD_TO == 'firebase' || env.UPLOAD_TO == 'googleplay'
        env:
          FIREBASE_APP_DISTRIBUTION_CREDENTIAL_BASE64: ${{ secrets.FIREBASE_APP_DISTRIBUTION_CREDENTIAL_BASE64 }}
        run: |
          FIREBASE_CREDENTIAL_FILE_PATH=$RUNNER_TEMP/firebase-credential.json
          echo -n "$FIREBASE_APP_DISTRIBUTION_CREDENTIAL_BASE64" | base64 --decode -o $FIREBASE_CREDENTIAL_FILE_PATH
          export GOOGLE_APPLICATION_CREDENTIALS=$FIREBASE_CREDENTIAL_FILE_PATH      
          echo "FIREBASE_CREDENTIAL_FILE_PATH=$FIREBASE_CREDENTIAL_FILE_PATH" >> $GITHUB_ENV      

      - name: Publish APK To Firebase App Distribution
        if: github.env.UPLOAD_TO == 'firebase'
        run: |
          firebase appdistribution:distribute ${{ env.PACK_APK_FILE_PATH }} \
            --app ${{ secrets.FIREBASE_PACK_APP_ID }} \
            --groups "${{ vars.FIREBASE_DISTRIBUTION_GROUPS }}"
  
      - name: Publish To Google Play for Internal Test
        if: env.UPLOAD_TO == 'googleplay'
        uses: r0adkll/upload-google-play@v1.1.3
        with:
          serviceAccountJson: ${{ env.FIREBASE_CREDENTIAL_FILE_PATH }}
          packageName: ${{ vars.GOOGLE_PLAY_PACKAGE_NAME }}
          releaseFiles: ${{ env.PUB_AAB_FILE_PATH }}
          track: internal
```

### 通常在 build Android 時候會用的 actions/setup-java, actions/setup-gradle

如果跑在不是 self host runner 的情況下，在 job 裡面補上 setup-java, setup-gradle 的 step 是必要的，不然建置環境應該是無法建立的

#### actions/setup-java 的設定

distributions 可以的值 : [Supported distributions](https://github.com/actions/setup-java#supported-distributions)

#### Setup JDK
一開始安裝 JDK 的時候是這麼寫的，裡面有 cache 的設定

```yaml
 - name: Set up JDK 17
   uses: actions/setup-java@v4.3.0
   with:
     java-version: '17'
     distribution: 'zulu'
     cache: gradle
```

但發現開啟的話在最後面有個 `Post Set Up JDK` 的步驟會很久，在 GitHub 上面也有被開 Issue [Post Setup JDK 17 takes very long time on local runner](https://github.com/actions/setup-java/issues/683)

解法很簡單就是把 `cache` 拿掉就好了，Issue 裡面有提到可能 Cache 的 Policy 可以調整，這個待有需要時再研究

### Sign app bundle [可選]

根據關分文件的 [Build an app bundle with Gradle](https://developer.android.com/build/building-cmdline) 的建議有 3 個方式

1. 增加 `build.gradle.kts` 檔案的方式在用 gradle 產生 app bundle 的時候就 sign ，這方式也可以搭配 `keystore.properties` 把 keystore 的相關密碼等資訊放在 `keystore.properties` 裡面避免資訊上到版控
   - 寫法可以不搭配 `keystore.properties` 可以在 build.gradle.kts 裡面透過`環境變數`取得
     - 大運動家 採用的方式
2. `jarsigner` 來 sign
3. `bundletool` 來做 sign

看到有些文章會使用 [r0adkll/sign-android-release](https://github.com/r0adkll/sign-android-release) 這個 action 來簡化 sign 的工作，看了一下它的原始碼發現它是用 `apksigner` 去 sign，`apksigner` 是跟著 Android Studio 會有版本問題，所以這個 action 會去找有安裝的最新版本 SDK 裡面的 `apksigner` 來用，但是！！

根據上面 Build an app bunlde with Gradle 的官方文件裡面寫
```
Note: You cannot use apksigner to sign your app bundle.
```

所以看起來是不可以用這個 action 來 sign aab

### 用 hidakatsuya/action-report-android-lint 上傳 lint 報告

用 [hidakatsuya/action-report-android-lint](https://github.com/hidakatsuya/action-report-android-lint) 來產生比較好看的 lint rerport 而不僅把 lint result 上傳到 GitHub Action 中

### asadmansr/android-test-report-action 使用限制

本來產生 unit test report 是採用這套第三方 action [android-test-report-action](https://github.com/asadmansr/android-test-report-action)

但這套只能支援
- Linux os
- 中文支援（非 ascii）有問題
  - 應該是使用的 python 版本過舊

所以在 macos 上面不能使用，所以最後改使用 [dorny/test-reporter](https://github.com/dorny/test-reporter)

### dorny/test-reporter 的使用情況

[test-reporter](https://github.com/dorny/test-reporter)

要打開 github action 的 permission
```yaml
permissions:
  pull-requests: write
  contents: write
  statuses: write
  checks: write
  actions: write
```

原因：["Error: HttpError: Resource not accessible by integration" during build process](https://github.com/dorny/test-reporter/issues/309)

### Firebase CLI

我們是自己使用 Firebase CLI 上傳到 Firebase App Distribution，其中 app id 要給對，請參考上方的取得方式

使用 Firebase CLI 時可以使用多加參數 `--debug` 來看看詳細步驟是錯在那個步驟，可以知道比較清楚的錯誤訊息

#### wzieba/Firebase-Distribution-Github-Action

本來 YAML 是使用 [Firebase App Distribution Github Action](https://github.com/wzieba/Firebase-Distribution-Github-Action?tab=readme-ov-file#firebase-app-distribution-github-action) 來上傳到

但同上非 container 不能執行

#### mapping file

如果 App 有用 [Shrink, obfuscate, and optimize your app](https://developer.android.com/build/shrink-code) 來編譯的話，要記得上傳 mapping file 到 Firebase，可以方便顯示錯誤的地方

[Get readable crash reports in the Crashlytics dashboard](https://firebase.google.com/docs/crashlytics/get-deobfuscated-reports?platform=android) 
裡面也有提到，使用 Crashlytics 的話也要記得開啟上傳 mapping file


### r0adkll/upload-google-play

[r0adkll/upload-google-play](https://github.com/r0adkll/upload-google-play)

裡面必要參數的 service account 的 JSON 有兩種給法，一個是 `serviceAccountJsonPlainText` 另一個是 `serviceAccountJson`
  - 差異：`serviceAccountJsonPlainText` 是直接給 JSON 文字, `serviceAccountJson` 是給 JSON 檔案路徑
  - 使用經驗上用 `serviceAccountJson` 比較方便，給 JSON 文字到變數的時候，可能會遇到 Json 內容有一些被認為不合法字元的情況，看實做如果給 JSON 文字他還是會把他變成一個檔案，因為最終會 export GOOGLE_APPLICATION_CREDENTIALS 到環境變數中，而這個變數的值就是 JSON 檔案的路徑
  - 這個 action 是使用 [@googleapis/androidpublisher](https://www.npmjs.com/package/@googleapis/androidpublisher) 這個 js 版本的 api 套件去上傳，看起來是 Google 官方提供的


## TO-DO


## 參考資料
- [automated-build-android-app-with-github-action](https://github.com/amirisback/automated-build-android-app-with-github-action)
- [Automating Success: GitHub Actions Workflow for Android App Deployment](https://medium.com/@vontonnie/automating-success-github-actions-workflow-for-android-app-deployment-908095d53b97)
- [Sign your app](https://developer.android.com/studio/publish/app-signing)
- [Build your app from the command line](https://developer.android.com/build/building-cmdline)
- [Environment variables](https://developer.android.com/tools/variables?authuser=1)
  - 設定 Runner 環境變數有哪些可以看這篇
- [Android Studio 生成與導入 JKS 金鑰](https://blog.cmrdb.cs.pu.edu.tw/?p=1130)
  - 示範使用 `build.gradle.kts` 與 `keystore.properties` 的方式來建置專案時就簽署
- [Upload apk or bundle to Google Play via command line script](https://stasheq.medium.com/upload-apk-to-google-play-via-command-line-script-d93b0d6a28c5)
- [Distribute Android apps to testers using the Firebase CLI](https://firebase.google.com/docs/app-distribution/android/distribute-cli?apptype=aab)
- [如何自動上傳 apk / aab 到 Google Play Console](https://medium.com/%E4%BF%9D%E7%BE%85%E7%9A%84-flutter-%E9%96%8B%E7%99%BC%E6%8A%80%E5%B7%A7/%E5%A6%82%E4%BD%95%E8%87%AA%E5%8B%95%E4%B8%8A%E5%82%B3-apk-aab-%E5%88%B0-google-play-console-9048251c426b)
  - 這邊展示用 google play api python client 去使用 python 上傳
- lint
  - [Lint](https://developer.android.com/reference/tools/gradle-api/7.3/com/android/build/api/dsl/Lint)
    - 官方文件說明 lint 裡面有哪一些 optino 可以用
  - [Android自定义Lint的二三事儿](https://juejin.cn/post/7130410607534145544)
  - [使用Android Studio Lint静态分析(三)](https://juejin.cn/post/6844903872624853000)
- 可用、參考的一些 Action
  - [gradle GitHub Action](https://github.com/gradle/actions/tree/main)
  - [r0adkll/upload-google-play](https://github.com/r0adkll/upload-google-play)
  - [AKJAW/kotlin-multiplatform-github-actions](https://github.com/AKJAW/kotlin-multiplatform-github-actions)
  - [gradle/setup-gradle](https://github.com/gradle/actions/blob/main/docs/setup-gradle.md)
- 工具
  - [apksigner](https://developer.android.com/tools/apksigner?authuser=1)
  - [KeyStore Explorer](https://keystore-explorer.org/)
  - [使用 Firebase CLI 將 Android 應用程式發布給測試人員](https://firebase.google.com/docs/app-distribution/android/distribute-cli?hl=zh-tw)