Flutter 整合 Firebase 小筆記
===

## 前置步驟
去 Firebase console 建立 Firebase Project  （廢話 XD）

## 執行整合 Firebase 初始化步驟的技巧

在建立好的 Firebase project 的頁面中會有針對不同平台開發整合的步驟指示，其中有包含 Flutter 的，所以點 Flutter 來察看安裝指示，接著依照步驟來執行

詳細指令請參照頁面指示，因為有步驟的指令會依照 Firebase 專案不同而不同，下面依照步驟順序來解說一些注意事項

1. 安裝 Firebase CLI (firebase-tools)
    * 不管是 Windows or Mac 建議用 npm 的方式裝好像比較方便
      * Windows 下載 binary 的連結有問題
      * Mac 用 curl 安裝的要你升級，然後就怪怪的
      * 用 npm 安裝的話，上面有建議要透過 nvm 這種 node 環境管理來做會比較好，但如果不是前端開發者或不需要多個 node 版本環境的話，可以去找穩定版的 node 安裝後，再透過教學的 npm 指令安裝即可
    * **注意:** 安裝完記得執行 `firebase login` 登入 firebase 後面的 `flutterfirebase` 才可以正常執行
2. 安裝 flutterfire_cli 這個全域的 dart package，安裝完就可以使用 `flutterfire` 的 CLI
    * **注意:** 安裝後可以看訊息，會跟你說要去設定環境變數 PATH 到一個 pub cache 的路徑，請記得去設定，這樣 `flutterfire` CLI 才可以正確的被找到
    * 這個指令可以在任何地方執行
3.  執行 `flutterfire configure` 的指令初始化 project 中的 firebase 的整合   
    * **注意:** 初始化會問你想要包含哪些作業系統，如果要包含 macos, ios 的話，這指令需要在 mac os 的電腦執行，在 windows 上只會更新非 ios, macos 的檔案
    * **注意:** 執行這個指令請到自己的 flutter project 的目錄下，否則無用

## 安裝完步驟
這邊就沒有在安裝指示中，但編譯的時候就會遇到，所以也需要執行

1. 新增 firebase_core package
2. [`可選`] 最低的 iOS / android SDK 版本要求，所以如果不符的話編譯也會有問題，記得要調整