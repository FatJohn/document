// 擷取自 2026-08-14 的內部版本，已去識別化（bundle id 與 app 名稱都是假值）。
// **這是節錄**：只保留與環境設定有關的段落，plugins / signingConfigs / dependencies
// 都拿掉了。只保證可讀，不保證可直接執行。
//
// 另外刪掉一處：原檔 environmentValue() 的錯誤訊息末段還有一句操作提示，指向一支
// 產生 dart-define.json 的輔助 script——那支不在這批樣本裡，留著會指向不存在的東西。
//
// 原檔：android/app/build.gradle.kts

import java.io.File
import java.util.Base64

// 沒帶 --dart-define-from-file 時的 fallback（等同 development）。
//
// 兩個 ANDROID_* 路徑的**真值**在 build_config/*.json，這裡只是備援。Kotlin DSL 讀不到
// JSON，所以這份複本消不掉——內部版是用一支測試逐 key 比對這兩份，漂移就紅。抄這段的話
// 那支測試要一起抄，不然這裡就是第二個真相來源。
var dartEnvironmentVariables = mutableMapOf(
    "APP_CONFIG_SUFFIX" to ".dev",
    "APP_CONFIG_NAME" to "MyApp [DEV]",
    "ANDROID_FIREBASE_CONFIG_PATH" to "android/app/config/dev/google-services.json",
    "ANDROID_RES_DIR" to "android/app/src/dev/res",
    "NOTIFICATION_CHANNEL_ID" to "default_notification_channel",
    "NOTIFICATION_CHANNEL_NAME" to "Default Notifications",
    "NOTIFICATION_CHANNEL_DESCRIPTION" to "Notification channel for FCM messages [DEV]"
)

// 哪些 key 真的由這次 build 的 dart-define 提供。fallback 的存在讓「設定檔漏了某個
// key」看起來跟「沒帶設定檔」一模一樣，而這兩者的正確行為不同（見 environmentValue）。
val dartDefineKeys = mutableSetOf<String>()

// 注入 dart-define 變數
if (project.hasProperty("dart-defines")) {
    val dartDefines = project.property("dart-defines") as String

    // 所有 dart-define 直接進 map，不只挑 ENV 一個 key：build_config/*.json 說了
    // 這個環境用哪份 Firebase 設定與哪個資源目錄，gradle 照著讀就好。
    dartDefines.split(",").forEach { entry ->
        // 明確指定 UTF-8，不靠 JVM 的預設字元集：進到這份 map 的值不只有這個檔案裡的
        // ASCII 字面值，非 UTF-8 的 JVM 上會解成亂碼。
        val decodedEntry = String(Base64.getDecoder().decode(entry), Charsets.UTF_8)
        val pair = decodedEntry.split("=", limit = 2)
        if (pair.size == 2) {
            dartEnvironmentVariables[pair[0]] = pair[1]
            dartDefineKeys += pair[0]
        }
    }

    // 這裡曾經有一個 `when (ENV)`，用環境名稱決定顯示名稱、bundle id 後綴與通知頻道。
    // 那些值現在都寫在 build_config/<env>.json，通用讀取就拿到了，所以整段移除——
    // gradle 至此完全不認識環境名稱，新增一個環境不必再動這個檔案。
    //
    // 連帶消失的是那個 `when` 的 `else -> throw`（未知 ENV）。它不再需要：gradle 不用
    // ENV 做任何決定，未知的環境名稱對它沒有意義。「這個環境該有的值到底有沒有帶齊」
    // 由下面的 environmentValue() 逐 key 檢查，那比檢查名稱在不在清單裡更準——
    // 名稱對但漏了欄位，才是真正會建出錯東西的情況。

    // 只印跟環境有關的 key。通用讀取之後這份 map 還含十幾個 FLUTTER_* 與其他
    // dart-define，整包印出來反而看不到重點。
    println(
        "App config: " + dartEnvironmentVariables.filterKeys {
            it == "ENV" || it.startsWith("APP_") || it.startsWith("ANDROID_") ||
                it.startsWith("NOTIFICATION_")
        }
    )
}

// gradle 刻意不從環境名稱推導路徑。每個環境用哪份 Firebase 設定、哪個資源目錄，都寫在
// build_config/<env>.json 裡由 dart-define 帶進來。
//
// 這裡曾經是 `if (isDevelopment()) "config/dev" else "config/prod"`，語意是「不是
// development 的一律當 production」：即使**正確**新增了 staging（設定檔、兩支腳本全都
// 加了），那個 if/else 不會報錯，而 staging build 會靜默拿到 production 的 Firebase
// 設定與資源——bundle id 是 staging 的，連的專案是正式的。
//
// build_config 裡的路徑相對於 repo 根目錄，而 gradle 的 file(...) 以 android/app 為
// 基準，所以要自己接回根目錄：rootProject 是 android/，它的上一層。
val repoRootDir: File = rootProject.projectDir.parentFile

// 這次 build 是不是帶了某個環境設定檔。
//
// 不能用 project.hasProperty("dart-defines") 判斷：flutter 每次 build 都會傳它自己的
// FLUTTER_*（CHANNEL／VERSION／ENGINE_REVISION…），所以那個 property 永遠都在。
//
// 也不能只看單一 key（這裡曾經只看 ENV）：那個 key 自己缺席時，「設定檔漏了東西」會被
// 誤判成「根本沒帶設定檔」，於是靜默沿用 fallback——正好放掉最該擋的情況。改成看整組
// 環境 key，任何一個出現就代表帶了設定檔，其餘缺的都會被 environmentValue() 抓出來。
val environmentConfigKeys = setOf(
    "ENV",
    "APP_CONFIG_SUFFIX",
    "APP_CONFIG_NAME",
    "ANDROID_FIREBASE_CONFIG_PATH",
    "ANDROID_RES_DIR",
    "NOTIFICATION_CHANNEL_ID",
    "NOTIFICATION_CHANNEL_NAME",
    "NOTIFICATION_CHANNEL_DESCRIPTION"
)
val usesEnvironmentConfig = dartDefineKeys.any { it in environmentConfigKeys }

// 取一個由環境設定檔提供的值。
//
// allowBlank 是為了 production 的 APP_CONFIG_SUFFIX——正式版的 bundle id 沒有後綴，
// 空字串就是它的正確值。把空字串一律當成「沒設定」會讓 production build 直接失敗。
// 空值合法的 key 仍然受「必須由設定檔提供」那條檢查保護，漏寫一樣會被抓到。
fun environmentValue(key: String, allowBlank: Boolean = false): String {
    val value = dartEnvironmentVariables[key]

    // 兩種缺法都要擋，而且第二種才是危險的那個：
    //
    //   * 完全沒有值——檔頭那份 fallback 也被刪了。
    //   * 帶了環境設定檔，但那份設定檔沒有這個 key。此時 map 裡還留著 fallback
    //     （development）的值，用下去就是 staging build 靜默拿到 development 的
    //     Firebase 設定、資源與顯示名稱。所以 fallback 刻意不補單一缺漏的 key。
    val missing = value == null ||
        (!allowBlank && value.isBlank()) ||
        (usesEnvironmentConfig && key !in dartDefineKeys)

    if (missing) {
        throw GradleException(
            """
            Missing $key for this build.

            Every environment states its own values in build_config/<env>.json; gradle does
            not derive anything from the environment name. Add this key to the config file
            you passed (paths are relative to the repository root):

              "APP_CONFIG_SUFFIX": ".dev",
              "APP_CONFIG_NAME": "MyApp [DEV]",
              "ANDROID_FIREBASE_CONFIG_PATH": "android/app/config/dev/google-services.json",
              "ANDROID_RES_DIR": "android/app/src/dev/res",
              "NOTIFICATION_CHANNEL_ID": "default_notification_channel"

            The fallback map at the top of android/app/build.gradle.kts covers only builds
            that pass no environment config at all (plain `flutter build apk` or
            `./gradlew`). It does not fill in a single missing key, because that would mean
            borrowing another environment's values without saying so.
            """.trimIndent()
        )
    }
    return value!!
}

fun environmentPath(key: String): File = File(repoRootDir, environmentValue(key))

// 兩個都在 configuration 階段解析：sourceSets 本來就需要，而缺 key 這種錯誤也應該在
// build 開始前就說出來，不是等到複製檔案那一刻。
val androidFirebaseConfig = environmentPath("ANDROID_FIREBASE_CONFIG_PATH")
val androidResDir = environmentPath("ANDROID_RES_DIR")

// 路徑打錯的兩種後果不對稱，所以擋的位置也不同：
//   * google-services.json 不存在 → copyGoogleServices 在 doLast 擋（它是 build 才需要
//     的檔案，configuration 階段擋會讓 ./gradlew tasks 這類唯讀指令也失敗）。
//   * 資源目錄不存在 → AGP 靜默忽略。少了整個環境的圖示與資源，build 照樣成功，跟這裡
//     要消滅的錯配同一個形狀，所以在這裡就擋下來。
if (!androidResDir.isDirectory) {
    throw GradleException(
        """
        ANDROID_RES_DIR does not point at a directory:
          ${androidResDir.relativeTo(repoRootDir)}

        AGP silently ignores a resource directory that does not exist, so a typo here
        costs this environment its icons and resources without failing the build.

        Create it (an empty .gitkeep inside is enough to keep it in version control) or
        fix ANDROID_RES_DIR in build_config/<env>.json.
        """.trimIndent()
    )
}

// 複製這個環境的 google-services.json 的 task
tasks.register("copyGoogleServices") {
    // 路徑在 configuration 階段就取好，doLast 只用取好的值：doLast 裡引用 project 或
    // file(...) 會讓這個 task 與 configuration cache 不相容。
    val sourceFile = androidFirebaseConfig
    val sourcePath = sourceFile.relativeTo(repoRootDir)
    val targetFile = file("google-services.json")

    doLast {
        if (sourceFile.exists()) {
            sourceFile.copyTo(targetFile, overwrite = true)
            println("Copied google-services.json from $sourcePath to android/app/")
        } else {
            // 錯誤訊息指名是哪個欄位指錯了。只說「檔案不存在」，下一個人得先翻 gradle
            // 找出誰在讀它。
            throw GradleException(
                "google-services.json not found: $sourcePath\n" +
                    "(from ANDROID_FIREBASE_CONFIG_PATH in this environment's build_config)"
            )
        }
    }
}

// 確保在處理 google-services 之前先複製檔案
tasks.whenTaskAdded {
    if (name == "processDebugGoogleServices" || name == "processReleaseGoogleServices") {
        dependsOn("copyGoogleServices")
    }
}

android {
    // 設定不同環境的資源目錄。Android 這邊不用複製——Gradle 支援多來源目錄，把環境的
    // res 疊進去就好。iOS 沒有等價機制，所以那邊只能複製檔案。
    sourceSets {
        getByName("main") {
            res.srcDirs("src/main/res", androidResDir)
        }
    }

    defaultConfig {
        applicationId = "com.example.myapp"
        // 一律走 environmentValue()，不直接讀 map：原本的 `?: "myapp"` 這類行內
        // fallback 會把「設定檔漏了這個 key」變成一個看起來很正常的預設值，出貨後才
        // 發現 app 名稱不對。APP_CONFIG_SUFFIX 允許空字串——那是 production 的正確值。
        applicationIdSuffix = environmentValue("APP_CONFIG_SUFFIX", allowBlank = true)
        resValue("string", "app_name", environmentValue("APP_CONFIG_NAME"))
        resValue("string", "fcm_default_channel_id", environmentValue("NOTIFICATION_CHANNEL_ID"))

        buildConfigField("String", "NOTIFICATION_CHANNEL_ID", "\"${environmentValue("NOTIFICATION_CHANNEL_ID")}\"")
        buildConfigField("String", "NOTIFICATION_CHANNEL_NAME", "\"${environmentValue("NOTIFICATION_CHANNEL_NAME")}\"")
        buildConfigField("String", "NOTIFICATION_CHANNEL_DESCRIPTION", "\"${environmentValue("NOTIFICATION_CHANNEL_DESCRIPTION")}\"")
    }
}
