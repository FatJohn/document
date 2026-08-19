# Flutter Android compile toolchain 版本相容性

每次升級 Flutter 專案的 Android compile toolchain，都要在 Gradle、AGP、Kotlin、JDK 這四個東西之間抓交集，版本一個沒對上就是滿滿的紅字。這篇把我查過的版本搭配關係整理起來，每次要升級的時候可以參考。

---

## 目前建議的版本組合（2026-03）

先講結論，目前 Flutter 專案用這組是最穩的：

| 套件   | 建議版本 | 說明                                                           |
| ------ | -------- | -------------------------------------------------------------- |
| AGP    | 8.10.0   | Flutter 完整支援的最新 AGP 8.x 穩定版                          |
| Gradle | 8.13     | 搭配 AGP 8.10 的最新穩定 Gradle                                |
| Kotlin | 2.2.x    | 搭配 AGP 8.10 的穩定選擇；2.3.0 可用但 R8 完整支援需 AGP 8.13+ |
| JDK    | 17       | AGP 8.x 的標準要求，穩定且 CI 廣泛支援                         |

如果需要 Kotlin 2.3 的 R8 完整支援，可以考慮把 AGP 升到 8.13+（需 Gradle 8.13）。

---

## 這些版本到底怎麼互卡的

Android compile toolchain 裡，這幾個套件的版本是環環相扣的。單看兩兩對照表很容易忽略整體搭配，所以先搞清楚底層到上層的決定依賴關係會比較好做決定。

### 依賴方向

```text
Flutter SDK
  * 決定最低 Kotlin 版本
  * 決定最低 Gradle 版本（透過內建的 Gradle wrapper）

AGP (Android Gradle Plugin)
  * 決定最低 Gradle 版本
  * 決定最低 Kotlin 版本
  * 決定最低 JDK 版本

Kotlin (KGP)
  * 決定可用的 Gradle 版本範圍（有上限與下限）

Gradle
  * 決定可用的 JDK 版本範圍（有上限與下限）
```

重點是：**Gradle 版本是整條鏈的交集中心**。AGP 卡 Gradle 的下限，Kotlin 卡 Gradle 的上限，最終選的 Gradle 版本必須同時滿足兩邊。JDK 則由 Gradle 版本決定支援範圍。

### 升級的時候版本怎麼選

不管從哪個版本開始動，最終都要回到同一個問題：找出所有套件的交集。以下提供兩條常見的查找路徑。

#### 路徑 A：想升級 AGP

> 情境：AGP 要從 8.7 升到 8.10

**Step 1 : 查 AGP 對 Gradle 的最低要求**

翻「AGP <-> Gradle 版本對照表」：AGP 8.10 需要 Gradle >= 8.11.1。

**Step 2 : 查 AGP 對 Kotlin 的最低要求**

翻「AGP <-> Kotlin 最低版本需求表」：AGP 8.10 需要 Kotlin >= 2.0.0。

**Step 3 : 用 Step 1 的 Gradle 版本，反查 Kotlin 上限**

翻「Kotlin <-> Gradle 版本對照表」，看哪些 Kotlin 版本吃得下 Gradle 8.11+：
- Kotlin 2.1.0 支援 Gradle 最高 8.11 -- 剛好壓線
- Kotlin 2.1.20 支援 Gradle 最高 8.12 -- 可以

所以 Kotlin 至少要 2.1.0 以上才能搭 Gradle 8.11。結合 Step 2 的下限（>= 2.0.0），**實際下限是 2.1.0**。

**Step 4 : 查 Flutter SDK 對 Kotlin 的要求**

Flutter 3.29+ 要求 Kotlin >= 2.0.0，不會進一步限縮。

**Step 5 : 用最終的 Gradle 版本，查 JDK 支援範圍**

翻「Gradle JDK 相容性」：Gradle 8.11 支援 JDK 8-23，AGP 8.x 要求 JDK >= 17。取交集：**JDK 17-23**。

**最終結果**

| 套件   | 可用範圍     | 建議選擇             |
| ------ | ------------ | -------------------- |
| AGP    | 8.10（目標） | 8.10.0               |
| Gradle | >= 8.11.1    | 8.13（取最新穩定版） |
| Kotlin | >= 2.1.0     | 2.2.x（穩定版）      |
| JDK    | 17 - 23      | 17（穩定且廣泛支援） |

#### 路徑 B：想升級 Kotlin

> 情境：Kotlin 要從 1.9.20 升到 2.1.0

**Step 1 : 查 Kotlin 對 Gradle 的版本範圍**

翻「Kotlin <-> Gradle 版本對照表」：Kotlin 2.1.0 支援 Gradle 7.6.3 - 8.11。**Gradle 不能超過 8.11。**

**Step 2 : 用 Gradle 上限，反查可用的 AGP 最高版本**

翻「AGP <-> Gradle 版本對照表」，找 Gradle <= 8.11 能撐住的 AGP：
- AGP 8.10 需要 Gradle >= 8.11.1 -- 8.11 不夠，不行
- AGP 8.9 需要 Gradle >= 8.11.1 -- 一樣不夠
- AGP 8.8 需要 Gradle >= 8.10.2 -- 可以

所以搭 Kotlin 2.1.0 的話，AGP 最高只能用到 8.8。想用 AGP 8.10 就得改用 Kotlin 2.1.20+（支援 Gradle 最高 8.12）。

**Step 3 : 確認 AGP 對 Kotlin 的最低要求**

翻「AGP <-> Kotlin 最低版本需求表」：AGP 8.8 需要 Kotlin >= 1.9.20 -- Kotlin 2.1.0 沒問題。

**Step 4 : 確認 JDK**

Gradle 8.11 支援 JDK 8-23，AGP 8.x 要求 JDK >= 17，取交集：**JDK 17-23**。

**最終結果**

| 套件   | 可用範圍      | 建議選擇                     |
| ------ | ------------- | ---------------------------- |
| Kotlin | 2.1.0（目標） | 2.1.0                        |
| Gradle | 7.6.3 - 8.11  | 8.11（取上限以支援最新 AGP） |
| AGP    | <= 8.8        | 8.8（Gradle 8.11 下的最新）  |
| JDK    | 17 - 23       | 17                           |

### 快速檢查清單

拿到一組版本後，跑這四個檢查就知道能不能用：

1. AGP 版本 => Gradle 版本 >= AGP 要求的最低版本？
2. AGP 版本 => Kotlin 版本 >= AGP 要求的最低版本？
3. Kotlin 版本 => Gradle 版本在 KGP 支援的範圍內（注意上限）？
4. Gradle 版本 => JDK 版本在 Gradle 支援的範圍內，且 >= AGP 要求的最低 JDK？

四項全過就沒問題。

---

## 各套件版本對照表

以下是各對照表的詳細數據，上面查版本的時候翻這裡。

---

## AGP <-> Gradle 版本對照表

| AGP 版本 | 最低 Gradle 版本 |
| -------- | ---------------- |
| 9.1      | 9.3.1            |
| 9.0      | 9.1.0            |
| 8.13     | 8.13             |
| 8.12     | 8.13             |
| 8.11     | 8.13             |
| 8.10     | 8.11.1           |
| 8.9      | 8.11.1           |
| 8.8      | 8.10.2           |
| 8.7      | 8.9              |
| 8.6      | 8.7              |
| 8.5      | 8.7              |
| 8.4      | 8.6              |
| 8.3      | 8.4              |
| 8.2      | 8.2              |
| 8.1      | 8.0              |
| 8.0      | 8.0              |
| 7.4      | 7.5              |

> 來源: [About Android Gradle plugin](https://developer.android.com/build/releases/about-agp)

---

## Kotlin (KGP) <-> Gradle 版本對照表

| Kotlin 版本 | 最低 Gradle 版本 | 最高 Gradle 版本 |
| ----------- | ---------------- | ---------------- |
| 2.1.20      | 7.6.3            | 8.12             |
| 2.1.0       | 7.6.3            | 8.11             |
| 2.0.21      | 7.5              | 8.10             |
| 2.0.20      | 7.5              | 8.10             |
| 2.0.0       | 7.5              | 8.8              |
| 1.9.20      | 7.5              | 8.5              |
| 1.9.0       | 7.5              | 8.3              |

> Kotlin 2.2+ / 2.3+ 對應的 Gradle 相容範圍請參考 [Kotlin 官方最新文件](https://kotlinlang.org/docs/gradle-configure-project.html#apply-the-plugin)。
>
> 來源: [Configure a Gradle project - Kotlin](https://kotlinlang.org/docs/gradle-configure-project.html#apply-the-plugin)

---

## Kotlin <-> AGP / R8 最低版本需求表

這張表列的是各 Kotlin 版本需要的最低 AGP 版本，主要影響 R8 code shrinking 的正確性。如果專案沒開 R8/ProGuard，編譯可能還是會過，但不保證所有功能正常。

| Kotlin 版本 | 最低 AGP 版本 |
| ----------- | ------------- |
| 2.4         | 9.1.0         |
| 2.3         | 8.13.2        |
| 2.2         | 8.10          |
| 2.1         | 8.6           |
| 2.0         | 8.5           |
| 1.9         | 8.0           |
| 1.8         | 7.4           |

> 來源: [Kotlin support - Android Developers](https://developer.android.com/build/kotlin-support)

---

## AGP <-> Kotlin 最低版本需求表

這張是從 AGP 的角度看，各 AGP 版本要求的最低 Kotlin 版本。

| AGP 版本 | 最低 Kotlin 版本                          |
| -------- | ----------------------------------------- |
| 9.0+     | 2.0.0（且不再使用 kotlin-android plugin） |
| 8.10     | 2.0.0                                     |
| 8.9      | 2.0.0                                     |
| 8.8      | 1.9.20                                    |
| 8.7      | 1.9.20                                    |
| 8.6      | 1.9.20                                    |
| 8.5      | 1.9.20                                    |
| 8.4      | 1.9.20                                    |
| 8.3      | 1.9.0                                     |
| 8.2      | 1.8.20                                    |
| 8.1      | 1.8.20                                    |
| 8.0      | 1.8.20                                    |

> 來源: [Kotlin support - Android Developers](https://developer.android.com/build/kotlin-support)

---

## JDK 版本需求

| AGP 版本 | 最低 JDK 版本 |
| -------- | ------------- |
| 9.x      | 17            |
| 8.x      | 17            |
| 7.x      | 11            |

Gradle 本身的 JDK 相容性：

| Gradle 版本 | 支援 JDK 範圍 |
| ----------- | ------------- |
| 8.10+       | 8 - 23        |
| 8.5 - 8.9   | 8 - 22        |
| 8.0 - 8.4   | 8 - 21        |

> 來源: [Java versions in Android builds](https://developer.android.com/build/jdks)、[Gradle Compatibility Matrix](https://docs.gradle.org/current/userguide/compatibility.html)

---

## Flutter 的部分

- Flutter 3.29+ 要求 Kotlin 2.0.0 以上
- Flutter 3.24+ 要求 Kotlin 1.8.0 以上
- 建議跟著 Flutter stable channel 的預設 Kotlin 版本走

> 來源: [Flutter - Required Kotlin version](https://docs.flutter.dev/release/breaking-changes/kotlin-version)

---

## 補充：AGP 9.0 -- Flutter 還沒準備好

AGP 9.0 在 2026 年 1 月正式出了，改動不小。但截至目前（2026-03），**Flutter 還沒完整支援 AGP 9.0，不建議在 Flutter 專案裡升上去**。

### AGP 9.0 要求的版本

| 套件   | 最低版本 |
| ------ | -------- |
| Gradle | 9.1.0    |
| Kotlin | 2.0.0    |
| JDK    | 17       |

### AGP 9.0 改了什麼

1. **內建 Kotlin 支援（Built-in Kotlin）**：AGP 9.0 預設啟用內建 Kotlin 編譯，不再需要也不能用 `kotlin-android` plugin。原本的 `kotlinOptions` 要改成 `android { kotlin { compilerOptions { ... } } }`。

2. **新版 DSL**：AGP 9.0 只用新版 DSL 介面，舊版 DSL 類型讀不到了。可以暫時在 `gradle.properties` 加 `android.newDsl=false` 撐一下，但這個選項到 AGP 10.0 就會被拔掉。

3. **Gradle 大版本跳躍**：AGP 9.0 要求 Gradle 9.1+，直接跳了一個大版本，其他 Gradle plugin 的相容性可能會炸。

### Flutter 目前的狀況

- 有用到 plugin 的 Flutter 專案跟 AGP 9.0 不相容（[flutter/flutter#181383](https://github.com/flutter/flutter/issues/181383)）
- Flutter 團隊在做 DSL 遷移跟向下相容性驗證（[flutter/flutter#180137](https://github.com/flutter/flutter/issues/175688)）
- 官方遷移文件有了，但明確寫著「手動遷移、尚不支援 plugin」：[Migrating Flutter Android app to AGP 9.0.0](https://docs.flutter.dev/release/breaking-changes/migrate-to-agp-9)

### 要升級嗎？

- 不要！等 Flutter 官方說支援了再升 AGP 9.0
- 如果是沒有用 plugin 的純 Flutter 專案，可以照官方遷移文件試試看，但風險自負

---

## 參考資料

- [About Android Gradle plugin](https://developer.android.com/build/releases/about-agp)
- [Android Gradle plugin release notes](https://developer.android.com/build/releases/gradle-plugin)
- [AGP 9.0 release notes](https://developer.android.com/build/releases/agp-9-0-0-release-notes)
- [Kotlin support - Android Developers](https://developer.android.com/build/kotlin-support)
- [Java versions in Android builds](https://developer.android.com/build/jdks)
- [Configure a Gradle project - Kotlin](https://kotlinlang.org/docs/gradle-configure-project.html)
- [Flutter - Required Kotlin version](https://docs.flutter.dev/release/breaking-changes/kotlin-version)
- [Flutter - Migrating to AGP 9.0.0](https://docs.flutter.dev/release/breaking-changes/migrate-to-agp-9)
- [Gradle Compatibility Matrix](https://docs.gradle.org/current/userguide/compatibility.html)
