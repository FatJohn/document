CICD 建置 - 建立 GitHub Action Self Host Runner
===

## 將 Runner 註冊到 GitHub

要擁有 Github repo / 組織 權限的人去加入，然後依照 [Adding self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners) 教學去註冊 runner，基本上有 2 種方式
- [Adding a self-hosted runner to a repository](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners#adding-a-self-hosted-runner-to-a-repository)
- [Adding a self-hosted runner to an organization](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners#adding-a-self-hosted-runner-to-an-organization)

> 注意：如果要一台 runner 提供給多個 repo 使用的話，只能使用註冊到 組織 的方式

建立的流程大致上是
1. 在 `~` 建立一個 `action-runner` 的目錄
1. 使用指令下載一包壓縮檔到該目錄
1. 解壓縮該檔案（裡面就是包含 Runner 所需要的 shell script 檔案）
1. 執行註冊到 GitHub 的 script ( 使用 `config.sh`，指令請依照 GitHub 頁面指示，GitHub 頁面會戴上註冊用的 token )
1. 執行啟動 GitHub Runner 指令的 script ( 使用 `run.sh` )

## 註冊 Self Host Runner 過程中注意事項

加入的過程中會問你是否要加入 `Group` 及 `Label`

### Group

主要是要能夠使用 Runner Group 時候使用，可以參考 [Managing access to self-hosted runners using groups](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/managing-access-to-self-hosted-runners-using-groups#changing-the-access-policy-of-a-self-hosted-runner-group) 來建立，所以如果沒有設定的話就留空即可

預設值是 `Default`

### Label

執行建立 Runner 的指令過程中，除了一些會預設給的 label 外，也會問你要不要制訂 custom lable，這個 label 就可以用於在 GitHub Action Flow YAML 裡面的 `runs-on` 來指定要跑得 runner

以 M1 Mac Book Air 來說會有下列預設 label
- `self-hosted`
- `macOS`
- `ARM64`

如果執行指令的時候沒有新增，後面也可以去 GitHub 網站的設定裡面再新增，可以參考 [Using labels with self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/using-labels-with-self-hosted-runners)，所以如果僅有一台 runner 的話可以在 GitHub Action Workflow 的 YAML 檔案中寫 `runs-on: self-hosted` 即可

## 執行 Runner 後檢查

Runner 註冊好後，要去 GitHub 的 Runners 裡面看看 `Status` 是不是有連上，若為 `Offline` 則是尚未連上，可以用 CLI 去 runner 的 `actions-runner` 資料夾裡面執行 `run-helper.sh` 試看看

## 把 GitHub self host runner application 變成 service

註冊的最後一步執行 `./run.sh` 意思就是相依於一個 terminal instance，所以一旦把 terminal 關閉的話 runner 和 GitHub 的連線就會斷掉無法使用，也就是說一旦重新開機的時候就不會自動連上

可以參考 [Configuring the self-hosted runner application as a service](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/configuring-the-self-hosted-runner-application-as-a-service?platform=mac) 這篇改註冊成 service

## 移除 Self host runner

可以參考 [Removing self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/removing-self-hosted-runners)

基本上就是從 GitHub 頁面上面可以在 Runner 的頁面點了 Remove ，如果還可以控制到那台 runner 機器的話，可以依照提供的指令去解除跟 repo / 組織 的綁定，不然也可以強制解除綁定

如果有使用指令解除綁定的話，就可以再次使用指令重新綁定，否則如果要重新綁定的話，可以使用下列的方式暴力但簡單的清除
- 叫出 工作管理員 (Windows) / 活動監視器 (Macos)
- 結束 Gibhub runner 的 task
- 刪除 `actions-runner` 的目錄
  - MacOS 目錄通常位於 `~` 下，Windows 的話通常位於 `C:\` 下
