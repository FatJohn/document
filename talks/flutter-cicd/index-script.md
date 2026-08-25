# Flutter App 的建置與發版流程設計 · 講稿

> 由 `python3 build/build.py` 從投影片原稿自動產生，**不要手改**——
> 內容來源是原稿裡 `>` 開頭的行，要改講稿請改原稿再重跑。

共 34 張。

---

## 1 · 封面：Flutter App 的建置與發版流程設計

`Flutter · GitHub Actions · 自架 runner`

今天想跟大家講一次我們這套 Flutter App 的建置跟發版流程。

會想講這個是因為，這條流程平常運作得很安靜——你開 PR、merge、然後某天某個人點幾下，App 就出現在 TestFlight 上了。但只要出一次狀況，例如「建置綠燈可是沒發出去」、「QA 說版號對不上」，不知道裡面怎麼跑的就很難查。

今天分三段：**怎麼發版**、**版號怎麼決定**、**環境怎麼切**。中間隨時可以打斷我問問題。

---

## 2 · 先講一下我是誰

`Intro`

開始之前先簡單自我介紹。

我是胖胖，在 TVBS 的 Lab Team。GitHub bio 我寫的是「打雜的工程獅，最熟的是 C#」——這句是真的，C# 寫最久，WPF、UWP 那個年代都待過，也拿過 Microsoft MVP。

再往前是 Pocket PC 跟 Windows CE，那真的是幾百年前了。中間還玩過 Symbian 上的 Qt、Bada、MRE，還有 Windows Phone——如果你沒聽過 Bada 或 MRE，那很正常，它們早就收了。**其實不只它們，這一串裡的平台現在一個都不剩。**

現在手上是 Flutter，而它在我 profile 上還掛著 beginner。那個我沒改，因為它是真的。今天要講的整套流程，就是這個 beginner 一路撞出來的——等一下講到哪裡你覺得「這樣做很怪」，很有可能你是對的，歡迎當場說。

右邊 QR 連到我的 GitHub 跟點部落，想回頭翻東西可以從那裡進。

---

## 3 · 兩條部署線

`Overview`

先給一張全景圖。

整套流程看起來分支很多，但每一個分歧，最後都能還原成同一個問題：**這是 staging 還是 main**。

**如果今天只記得一件事，就記這張。** `staging` 對應 `CI: Development`，`main` 對應 `CI: Production`；後面先看它們平常怎麼跑，最後才看發版怎麼讓 tag 叫起它們。

---

## 4 · 章節轉場：建置

（這張沒有講稿）

---

## 5 · 平常建置的兩條 CI workflow

`建置 / CI workflow`

現在先看平常實際在跑的兩支 CI：`staging` 對應 `CI: Development`，`main` 對應 `CI: Production`。branch push、PR、手動執行都會進來，先跑測試跟建置。

兩份 CI 的上半段差別只有三個地方：監聽哪個分支、tag 的 glob 長怎樣、還有 production 刻意不中斷正在跑的建置——它 `cancel-in-progress` 是 false，因為一次正式發版跑到一半被新的 push 砍掉，比多跑一次還糟。

下半段是十個 job，兩條線的名字跟順序完全一樣。接著直接沿著 job 圖，看一次 CI run 先後怎麼協作。

---

## 6 · 一次建置跑過的 job

`建置 / 流程`

這是一次建置實際會跑到的 job。

最上面五個是平行起跑的。`ci-scripts` 跑的是 CI 自己那些 shell script 的測試，三十幾秒就完。注意圖上它跟 `gradle-config` 沒有箭頭連進 build：兩個都是獨立健康檢查，不會卡住 runner 去建置；但它們只要有一個紅，整條 run 最後還是紅。

`generate-build-number` 要等閘門的結果，因為它得先知道這次算不算正式建置，才知道要不要動計數器。

再來 Android 跟 iOS 平行建置，最後才是派發那一層——**只有 tag 會走到最下面那格**。

接下來不照 YAML 逐行念，而是沿著這張圖看三類真正決定建置結果的輸入：版號、build number 與環境設定。

---

## 7 · 章節轉場：建置的輸入

（這張沒有講稿）

---

## 8 · 版號：人決定前兩碼，CI 只動 patch

`inputs / resolve-version → build-android · build-ios`

版號的唯一來源是 `pubspec.yaml`。這件事很重要：**CI 對版號不做任何轉換**，dev 跟 prod 讀的是同一個欄位。

三碼分別是 MAJOR、MINOR、PATCH，加號後面那個是 build number。要記住的是**分工**：MAJOR 跟 MINOR 是人決定的，你要自己去改 `pubspec.yaml`；**CI 只會動 PATCH**，而且只在 bump 的時候 +1，也只開 PR、不直接 push 到保護分支。

這張表是這一章的地圖，四個數字誰產生的一目了然。等一下講 build number 的時候會回到最後一列。

---

## 9 · build number：年月加當月流水號，九位數

`inputs / generate-build-number → build-android · build-ios`

build number 只有一個硬性要求：單調遞增。剩下都是設計空間。

我們的格式是九位數：年後兩碼、月份、當月流水號。為什麼這樣切？看到號碼就知道大概什麼時候建的，查 log 省一次來回；而且計數器每個月歸零，數字不會無限長大。

為什麼是九位？Android 的 `versionCode` 上限是 21 億，九位數最大 `991299999`，可以用到 2099 年。

下面那張表是重點：**只有真的要發版才動計數器**。PR 驗證跑幾百次都不會影響它，所以計數器上的數字就等於真正發出去的次數。

---

## 10 · 兩種號碼來源長什麼樣

`inputs / generate-build-number 的狀態`

「每個月第幾次」是一個必須跨 build 保存的狀態。CI 是無狀態的，所以這個數字得存在某個地方。

我們存在 repo 自己身上：一個孤兒分支，跟主線程式碼完全隔離，裡面只有這個 JSON。上面那個 `15` 就是 development 環境在 2026 年 7 月已經發了 15 次。

每次遞增就 append 一個 commit，不 amend 也不 force，所以那條歷史本身就是發放紀錄。

PR 那條就簡單了，直接拿 GitHub 給每個 run 的流水號取五位，不碰這個分支。

有人可能會問為什麼不用 Actions 的 cache 或 artifact——因為兩者都會過期，而版號的狀態不能過期。

版本與 build number 都已經就緒；下一個 input 是 `environment`。它不像前兩個只是數字，還必須讓 Flutter、Android 與 iOS 取到同一組設定。

---

## 11 · 同一份 JSON，讓三層設定一起切換

`inputs / build-android · build-ios`

這是兩個 build job 共用的 `environment` input。它不是只要切一個環境變數：Flutter runtime、Android 的資源與 Firebase 設定、iOS 的 xcconfig 與 Firebase 設定都得一起換，否則 app 很容易拿到混搭的一組設定。

所以把決策集中在一個檔案：一個環境一份，放在 `build_config/` 底下。上半段是**值**——app 名稱、icon 名稱、bundle id 後綴；下半段是**路徑**——這個環境的 Firebase 設定在哪、Android 的資源目錄在哪。

標起來的那幾個欄位是等一下會一直出現的，先有印象就好。

重點是下半段：**路徑是設定檔自己講的，不是程式從環境名稱推導的**。所以新增環境時，Android／iOS 的取值程式不用再加 `if/else`；放一份 JSON、把它指到的目錄建出來即可。CI 的分支、憑證與派發目標仍要另外配置，這裡講的是平台取值這一層。

兩個 action 的機制不同：Android 先把 JSON 加工成 `dart-define.json`；iOS 先從它產生 `AppConfig.xcconfig`，之後也用同一份 JSON 做 Flutter build。接下來就從標起來的欄位追下去：先看 `APP_CONFIG_SUFFIX` 怎麼決定身份，再看 Android 與 iOS 怎麼各自消費這些設定。

---

## 12 · dev 跟正式版要能裝在同一台手機上

`build-android · build-ios / app identity`

為什麼 bundle id 要分？很單純：**因為 dev 版跟正式版要能同時裝在同一台手機上。**

對作業系統來說，bundle id 就是 app 的身分證。兩個 app 的 bundle id 一樣，後裝的就會蓋掉先裝的。所以測試版必須有一個不同的 id。

做法不是各寫死一整串，而是一個 base 加一個後綴。development 是 `.dev`，production 是空字串。

後綴就是上一頁那個 `APP_CONFIG_SUFFIX`。兩個平台用同一個名字，但拿到它的路徑完全不同——接下來兩頁分開講。

---

## 13 · Android 怎麼拿到這些值

`build-android / runtime + native settings`

Android 這條路最短，因為 Gradle 解得開 dart-define 的內容。

第一段：解 base64，所有 key 一律進同一個 map。這裡完全不認識環境名稱——不會有 `if (isDevelopment())` 這種東西。

第二段是 bundle id：base 是寫死的，後綴走設定檔。注意取值是經過 `environmentValue()` 這個函式的，不直接讀 map。**為什麼？** 因為直接讀就會寫出 `?: "myapp"` 這種行內預設值，那會把「設定檔漏了一個 key」變成一個看起來很正常的 app 名稱，要出貨之後才發現。包一層就可以在缺值的當下直接炸掉。

第三段是資源目錄。Android 這邊很好，Gradle 支援多來源目錄，把環境的 res 疊進去就好，不用複製任何東西。

---

## 14 · iOS 怎麼拿到這些值

`build-ios / runtime + native settings`

iOS 這條路多一站，因為 Xcode 讀不到 dart-define。

那支 script 把設定檔的值寫成一份 xcconfig。但我上次講的時候發現大家最不清楚的其實是：**那份產出的檔案，到底是怎麼被 build 讀到的？**

就是上面那三步。反過來從 Xcode 那頭看更清楚：Xcode 的專案設定指到 `Debug.xcconfig` 跟 `Release.xcconfig`，這兩份各自只有兩行 `#include`，其中一行 include 的就是 script 產出來的 `AppConfig.xcconfig`。

所以鏈是這樣：**設定檔 → script → AppConfig.xcconfig → 被 Debug/Release include → Xcode 讀到**。中間任何一環沒跑，Xcode 讀到的就是上一次的值。

還有一點：因為 Debug 跟 Release include 的是同一份，所以你本機 run 跟 CI 建置走的是同一組值，不會有「本機看起來對、CI 卻不對」這種事。

---

## 15 · 有些東西沒有變數可用，只能把檔案複製到位

`build-android · build-ios / file placement`

變數能解決的都解決完了，剩下的只能用複製的。

為什麼？因為 Firebase 的 SDK、Xcode 的 storyboard 這些下游工具，**寫死了要讀哪一個路徑的哪一個檔名**，不吃任何變數。所以只能在它們讀之前，把對的那一份複製成那個名字。

表上四列，前三列要複製，最後一列不用——Android 的圖示跟資源可以直接疊目錄，就是上上頁講的 `sourceSets`。iOS 沒有等價的機制。

還有一個容易忘的：前三個的**目標**檔案都要進 `.gitignore`。它們是建置產物。忘了的話就會有人 commit 一份 dev 的 `google-services.json` 上去。

---

## 16 · Android：一個 Gradle task，掛在 plugin 前面

`build-android / Firebase config`

這是 Android 那段複製的完整寫法，一個自己註冊的 task。

有一個細節不能省：**所有路徑都在 configuration 階段解析完**，`doLast` 裡只用已經取好的值。在 `doLast` 裡碰 `project` 或 `file()` 會讓這個 task 跟 configuration cache 不相容。

找不到檔案就 throw，不會靜默跳過。而且錯誤訊息把是哪個欄位指錯了一起寫出來——這是寫的時候多花一分鐘的事，但省下的是別人二十分鐘。

最後用 `whenTaskAdded` 掛在 Google Services plugin 前面，確保 plugin 讀到的是複製後的檔案。

---

## 17 · iOS：一行 cp，加一個掛在 Xcode 上的 build phase

`build-ios / Firebase + launch image`

iOS 這兩段複製發生在不同時機，這點很容易搞混。

Firebase 設定是跑 `generate_app_config.sh` 的時候複製的，跟上一頁那份 xcconfig 一起產。來源由設定檔指定，不存在就 `exit 1`。

啟動圖不一樣，它掛成 Xcode 的 Run Script build phase，**每次 build 都會跑**，讀 xcconfig 的變數決定來源。

為什麼啟動圖要多這一步？因為 storyboard 沒辦法引用 xcconfig 變數，裡面只能寫死一個圖片名稱。所以我們讓它固定引用 `LaunchImage`，在 build 之前把對的那份複製成那個名字。

順帶一提，這不是我們自己想的偏方——iOS 要依環境換 storyboard 裡的素材，社群的標準解就是 build phase script。

---

## 18 · 一支 script 決定 iOS 的四個值

`build-ios / xcconfig`

這四個值不是寫在 script 裡，而是從設定檔逐欄位讀出來的，跟 Android 讀的是同一份。

表格右邊那欄是「誰在用」——可以看到它們最後接到的都是 Xcode 認得的東西：bundle id、顯示名稱、icon 名稱，還有給前一頁那支複製 script 用的啟動圖名稱。

在 CI 裡它還會多做一件事：把算好的完整 bundle id 寫進 `GITHUB_ENV`，後面抓簽章憑證的步驟會直接用那個值。

最後那個框是這頁的操作判準：**不要把「記得先跑 script」留給人。** `AppConfig.xcconfig` 是產物，如果 build 入口沒有先重產，它就可能沿用上一次的環境。

這個案例的一般本機路徑已由 `Runner` scheme 的 Build Pre-action 自動跑，CI 的 `build-ios` action 也明確跑一次。新增 scheme、改用另一個 target，或多一條建置入口時，要把同一道防線一起接過去。

---

## 19 · 同一件事，Android 原生有現成機制：flavor

`環境 / 對照`

講到這裡，可能有人會想：Android 不是本來就有 flavor 嗎？

對，而且我要先說清楚：**Android 這一側單獨看，flavor 確實比我們現在的做法乾淨。** 前四列它幾乎全包。

但最後一列是重點：flavor 沒有「值帶齊了沒」這個概念。漏設一個值，它就是安靜地拿 `defaultConfig` 的值——正好是我們前面費力氣在擋的那種錯配。

---

## 20 · iOS 沒有 Android flavor 的一對一對應

`環境 / 對照`

iOS 這邊沒有 Android flavor 的一對一對應。Xcode 有 target、scheme 與 build configuration，但沒有一個像 `productFlavors` 那樣一次定義整個 variant matrix 的地方。

換得掉的部分：bundle id、顯示名稱、icon 這些可以由 configuration 指到不同的 xcconfig。切環境的體驗確實會變好。但注意，**值還是走 xcconfig 變數**，跟我們現在一模一樣。

換不掉的部分要先加一個前提：這講的是**單 target** 的情況。Firebase 設定檔還是要一個 build phase script 依環境複製，這是社群通行的做法——但誠實說，**官方文件給的其實不是這條**，官方教的是分多 target，或者 runtime 用 `FirebaseOptions` 自己選。所以是我們選了 script 這條，不是只有這條路。

另外一個代價是：走 scheme 的話，環境清單會散在 `project.pbxproj` 裡面，那是 GUI 產生的檔案，diff 幾乎沒辦法 review。

---

## 21 · 那為什麼這個專案沒走 flavor

`環境 / 取捨`

把兩邊放在一起比。中間那兩列我們是輸的：scheme 的切換體驗比較直觀，一次出多個環境的產物也比較自然。這個案例靠 Runner Pre-action 自動重產 xcconfig，避免把「先跑 script」留給人記。

贏的是漏設定的處理，還有 CI 完全不用動。

所以我的結論是：**不是 flavor 不好，是這個案例在目前的單 target 與共用設定前提下，iOS 那側仍要有 xcconfig 與檔案就位步驟。** 只把 Android 換成 flavor，會讓兩個平台的設定來源分家。若改走多 target 或 runtime `FirebaseOptions`，結論就會不同。

先聲明一下，**這頁是取捨判斷，不是 repo 現況**——我們沒有試過 flavor 版本再回頭比較。真的要重來，值得的時機是「環境長到三個以上，而且需要同一次 CI 產出多個環境的產物」。

---

## 22 · 章節轉場：發版

（這張沒有講稿）

---

## 23 · 什麼時候 CI 真的會 deploy？

`發版 / 派發閘門`

這頁回答一個很常見的疑問：為什麼我推了東西，CI 綠了，但 App 沒更新。

因為**只有 tag 會派發**。推分支、開 PR、手動觸發，這些都只跑測試跟建置。

第一，tag 的格式對不對，正規表達式卡得滿死的。第二，**這個 tag 真的長在那條線上**。所以你在 main 上推一個 `dev1.4.2`，建置會成功，但會跳過派發。

另外被跳過派發的時候，run summary 上會掛一條 warning 說明原因，不會只留一個灰色的 skipped——那個太容易被誤讀成「已經發出去了」。

---

## 24 · 發 dev 與正式版，各按哪幾下

`發版 / 主線`

前面已經看過兩條 CI 的 job；現在只差最後一件事：怎麼讓它真的走到 deploy。

開發版最短：在 staging 跑 `Push Dev Tag`，它 push `dev` tag 後就結束；GitHub 另外起 `CI: Development` 建置與派發。

正式版多一段 review：先開 staging → main PR，merge 後在 main 跑 `Push Production Tag`。它 push `v` tag 後，才由 `CI: Production` 建置與派發。

production tag 後的 bump／sync 是後續自動整理，不是這裡要手動多點的一步。

---

## 25 · 正常發版要手動點的三支入口

`發版 / 手動入口`

正常發版只需要認得這三支手動入口。

`Release Dev` 在 staging 推 `dev` tag，後面真正跑的是 `CI: Development`。Production 則先開 staging → main PR，再在 main 推 `v` tag，後面真正跑的是 `CI: Production`。

hotfix 是另一條情境，不混在正常發版入口；production tag 後的 bump／sync 也是自動接手。Actions 頁面上看到的 release run 跟 CI run 是**前後兩個 workflow run**，靠 tag 串起來。

---

## 26 · 注意：推 tag 不能用 `GITHUB_TOKEN`

`發版 / 注意事項`

這頁不是要展開 GitHub App 怎麼設定，只要記一個操作注意事項。

GitHub 為了避免 workflow 遞迴，內建 `GITHUB_TOKEN` 推出的 ref 不會觸發 workflow。最容易誤判的症狀是：tag 已經在列表上，但 `CI: Development` 或 `CI: Production` 根本沒有新的 run。

所以兩支 Push Tag workflow 用 GitHub App 的短效 installation token。看到 tag 被推上去之後，還要確認對應 CI run 已經起來；這才算發版真的開始。

bump、sync、開 PR 則繼續用 `GITHUB_TOKEN`，因為它們不該再自動喚起下一輪 workflow。

若有人問 token 怎麼拿，兩支 Push Tag workflow 的第一段就是 `actions/create-github-app-token`；但這次不展開 GitHub App 的設定步驟。

---

## 27 · 同版本再發一次，後綴從 -2 開始

`發版 / 重發`

有時候同一個版本要發兩次，例如送審被打回來。

這時候 workflow 會先列出遠端所有符合的 tag，算出這是第幾次發版，再決定 tag 名。第一次是純版號，第二次 `-2`，第三次 `-3`。

**後綴數字對齊「第 N 次」的口語，所以沒有 -1**，這點常有人問。

dev 線直接重跑就好；prod 線會擋下來要你勾一個確認——那道摩擦是刻意的，它要你先想清楚，如果這其實該是一個新版本，那就該 bump 而不是重發。

---

## 28 · 章節轉場：GitHub Actions 補充

（這張沒有講稿）

---

## 29 · 重複的步驟都抽成 composite action

`補充 / 共用步驟`

有人可能會問：兩條 CI 線是不是兩份幾乎一樣的 YAML，改一邊忘記另一邊怎麼辦。

答案是重複的步驟都抽成 composite action 了。兩條線共用同一組 action，**環境差異只用 inputs 表達**。像 `build-android` 收 `environment` 跟 `build_aab`，dev 線傳 false、prod 線傳 true，就這樣而已。

但我想講的其實是下面那個框：**抽出來還有一個不是為了 DRY 的理由。**

這些步驟本來各自是一支 workflow，而 Actions 頁面左邊那排會把所有 workflow 列出來。那排長到你要找「發版要點哪一支」都得先掃一遍。放進 `.github/actions/` 之後它們就不出現在那排了——左邊只剩下真的需要人去點的那幾支。

這是個很小的事，但它每天都在影響你用這個頁面的體驗。

---

## 30 · 用 environment 隔離同名的 variable 與 secret

`補充 / GitHub environment`

前面講的都是建置的差異，來源是 repo 裡的檔案。**派發的差異來源不一樣，是 GitHub 的設定。**

這頁只要記一件事：**同一個變數名，不同 environment 給不同的值。**

看上面那段：兩條線的 deploy job 結構相同，`environment:` 與 artifact 名稱跟著環境換；但變數名完全一樣。GitHub 依 job 上那行 `environment:`，決定給 development 還是 production 那一份。

這樣的好處是：要換測試群組、換 Firebase app，改 GitHub 設定就好，不用動 repo、不用開 PR、不用重新 review。

最後一點是一個坑：**build job 是刻意不掛 `environment:` 的**。掛了的話，environment 的 branch policy 會連 PR build 一起擋掉。

---

## 31 · 讓自動 PR／commit 正確顯示為機器人

`補充 / bot 身分`

這是一個讓 GitHub 顯示正確身分的小技巧。

自動 bump／sync 與 hotfix prep 都會開 PR、產生 commit；name 用 `github-actions[bot]` 還不夠，email 的數字也必須是這個 bot 帳號的 user id，搭配 GitHub 的 noreply 網域，GitHub 才能正確歸戶。

兩種寫法都列在上面：自己 `git config` 的話寫那兩行；用 `create-pull-request` 這個 action 的話，直接把 committer 跟 author 指定成同一串。

這幾支只要開 PR，不需要喚起下一輪 CI，所以預設 `GITHUB_TOKEN` 就夠。

---

## 32 · 今天沒講的，都有對應的流程

`收尾 / 邊界`

今天走的是正常發版那一條線，這頁把沒講到的補上，讓「沒提到」不等於「沒有」。

第一列 hotfix、第二列推完 tag 之後的自動同步，這兩個是真的會遇到的。我不打算現在展開，因為你不在那個情境裡聽了也記不住——**知道有這個東西就夠了**。

最後那句話是反過來的提醒：**動了 workflow、script 或環境設定，記得同步更新流程文件。** 不然下一個人會照著舊文件操作。

---

## 33 · 帶走這四件事

`收尾`

如果今天只帶走四件事：

**第一，日常 CI 先建置驗證，發版才派發。** 平常的 CI 只做測試與建置；真正把 CI 帶進 deploy 的，是符合規則的 tag。

**第二，發版路由三者必須配對。** staging 對 `dev` tag 與 staging 專案，main 對 `v` tag 與 prod 專案。tag 有推上去，不代表配錯來源也能發出去。

**第三，版號只有一個來源。** 而且分工要記得：MAJOR 跟 MINOR 是人的事，CI 只動 PATCH，build number 完全不歸人管。

**第四，環境設定只有一個入口，而且必須早期驗證。** 一份 JSON 說值也說路徑；Android 與 iOS 各自轉接，固定檔名的檔案在建置前就位。缺 key、資源或路徑不要等下游工具安靜地拿錯。

iOS 的操作判準也在這裡：**每個 build 入口都要先重產 `AppConfig.xcconfig`。** 這個案例的 Runner Pre-action 與 CI 已自動處理；新增入口時要一起接上，而不是再要求人記一個步驟。

---

## 34 · 謝謝 / Q&A

以上，謝謝大家。有什麼問題嗎？

---

### 可能被問到的問題

**Q：為什麼不用 flavor？** 見 flavor 那三頁。一句話：Android 那側 flavor 確實比較乾淨，但目前單 target 的 iOS 仍要 xcconfig 與檔案就位步驟；只換 Android 會讓兩個平台的設定來源分家。若改走多 target 或 runtime `FirebaseOptions`，要重新評估。

**Q：我可以自己推 tag 嗎？** 技術上可以用 tag ruleset 擋，但更重要的是手推的 tag 不會帶 App 身分，也繞過了 workflow 的版號計算。請走 Actions 介面。

**Q：build number 會不會用完？** 九位數最大 `991299999`，Android 上限 21 億，可以用到 2099 年。

**Q：為什麼我的 PR CI 綠了，發版卻炸掉？** 最常見的是 deploy-only 的路徑 PR 根本不會跑到。這也是為什麼加了 `gradle-config` 這個 job——把「另一個環境的設定」從發版當下提前到 PR 階段驗。

**Q：新增一個環境要多久？** 平台取值這一層只要放一份 `build_config/<env>.json` 與它指到的檔案，不用再加 `if/else`。真正的工作是 Firebase Console、Apple Developer、GitHub Environment、簽章素材與 CI 路由；所以不能把「不用改平台程式」講成「整條發版線不用改」。

**Q：bundle id 的 base 是不是也在設定檔裡？** 不是，這是這套做法唯一的例外——base 那段字串散在 `project.pbxproj`（app target 的 Debug／Release／Profile 各一行）與 `build.gradle.kts` 裡，而 iOS 那支 script 是反過來從 pbxproj 抓的。

所以照抄這套之前，先問對的問題：**不是「有沒有單一來源」，而是先數份數、再問每一份有沒有人釘著。** 後綴那兩份有測試逐 key 比對釘住，是可以接受的工程現實；base 那幾份如果沒人釘，就是等著發生的事故。最小的修法是照著加一條測試比對，不一致就紅。
