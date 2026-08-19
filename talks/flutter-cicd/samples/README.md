# samples

《Flutter App 的建置與發版流程設計》這份簡報提到的幾支 script 與設定檔，去識別化之後放在這裡。

**擷取自 2026-08-14 的內部版本。** 專案代號、bundle id、app 名稱、後端網域與 Firebase 專案都換成了假值——`com.example.myapp` / `MyApp` / `example.com`。**只保證可讀，不保證可以直接執行**：路徑、asset 名稱與 Firebase 設定檔都要換成你自己的。

| 檔案 | 對應簡報哪一段 | 這支在做什麼 |
|---|---|---|
| `build_config-development.json` | 環境 / 單一入口 | 一個環境一份的設定檔。上半是值，下半是路徑 |
| `generate_app_config.sh` | 環境 / iOS | 讀設定檔寫出 `AppConfig.xcconfig`，順便把 Firebase plist 複製到位 |
| `runner-build-pre-action.sh` | 環境 / iOS | `Runner` scheme Build Pre-action 的可讀片段；每次 build 先依 `DART_DEFINES` 重產 xcconfig |
| `copy_launch_image.sh` | 環境 / iOS 的複製 | 掛成 Xcode build phase，每次 build 把對應環境的啟動圖複製成固定名稱 |
| `build.gradle.kts` | 環境 / Android | 節錄。dart-define 解析、`environmentValue()` 的 loud fail、`copyGoogleServices` |
| `build-number-action.yml` | 版本 / 狀態放哪 | composite action：孤兒分支上的月計數器，含重試與重算 |

每一支都在檔頭寫了它跟原檔的差異。除了假名替換與加上的解說註解之外，只有兩處刪減：`build.gradle.kts` 拿掉了指向一支未附上的輔助 script 的錯誤訊息末段，`build_config-development.json` 拿掉了一個與本主題無關的第三方登入欄位。`runner-build-pre-action.sh` 原本內嵌在 `.xcscheme` XML，這裡只抽出 shell 內容方便閱讀。

幾個看的時候值得注意的地方：

`generate_app_config.sh` 的 `read_config()` 用 `jq has()` 判斷欄位存不存在，不是判斷值是不是空的——production 的 `APP_CONFIG_SUFFIX` 就是空字串，把空值當缺漏會讓正式版建不起來。

`build.gradle.kts` 檔頭那份 fallback map 是備援，真值在 `build_config/<env>.json`。兩份會漂移，所以內部版有一支測試逐 key 比對它們；抄過去的話那支測試也要一起抄。

`build-number-action.yml` 的重試迴圈裡，push 被拒之後是 **fetch 完重新讀檔重算**，不是沿用上一輪算出的數字——沿用會寫入過期值，發出重複的 build number。那比衝突本身更糟。
