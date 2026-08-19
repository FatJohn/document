CICD 建置 - GitHub Action Workflow 不分平台的心得
===

這邊描述的主要是跟平台無關的一些在 GitHub Action 開發的過程中的心得

## 觸發條件

- `workflow_dispatch` : 能夠被手動觸發要加上這個事件
- `push` : 
  - branchs, tags 是 AND 符合，比對的方式就是 branch 成立 且 tag 成立
  - 可以用 `wildcards` 的表示方式
  - 不支援 `regular expression`
- `pull_request` : 要記得在 typts 條件補上 `synchronixe` ，代表這個 PR 有新的 commit 推上去的時候也會觸發

> 可以看 [Examples of wildcard characters](https://support.microsoft.com/en-us/office/examples-of-wildcard-characters-939e153f-bd30-47e4-a763-61897c87b3f4) 知道 wildcard 的用法

## 多台 Runner 分配工作

- 可以在 YAML 裡面的 `runson` 用同樣的 label 會自動分配，此方式簡單方便
- 可以用使用 runner group，此方式更好的控管、共用

使用 runner gropu 是比較進階的使用場景，可以看 [Managing access to self-hosted runners using groups](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/managing-access-to-self-hosted-runners-using-groups#changing-the-access-policy-of-a-self-hosted-runner-group) 來瞭解

## 全域變數的 env 宣告

YAML 的最上層也可以宣告 `env` 並指定全域的變數，但是 job or step 要使用的時候要用 `${{env.變數名稱}}` 來使用，跟在 step 裡面宣告的時候使用方式不一樣，在 step 裡面宣告的 env 變數直接用 `$變數名稱` 使用即可

## Step 間的傳遞變數

一個 step 中的 env 變數不會延續到下一個 step，要在之後的 step 使用到有兩種方式

1. 把變數書出道 GitHub env 中
2. 做成 step 的 outputs

### 1. 把變數書出道 GitHub env 中

設定到 env 的方式
```bash
echo "{name}={value}" >> "$GITHUB_ENV"
```

要使用 env 的方式
```bash
${{ env.name }}
```

### 2. 做成 step 的 outputs

> 官方文件似乎沒提到 step 使用 outputs 的方式

設定到 outputs 的方式
```bash
echo "{name}={value}" >> "$GITHUB_OUTPUT"
```

要使用 outputs 的方式

首先要在設定 outputs 的 step 或 job 給予 `id`
``` yaml
- name: Expose the artifact path
  id: paths
  run: echo "artifact='app-setup.exe'" >> "$GITHUB_OUTPUT"
```

使用時就可以
``` bash
${{ steps.paths.outputs.artifact }}
```

## Job 間傳遞變數

根據 [Passing information between jobs](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/passing-information-between-jobs) 在 Job 之間也可以使用 output 的方式傳遞

## Step 設定的環境變數是不會往下傳遞的

每一個 step 都可以使用 `env:` 這次在 run 的時候的環境變數，舉例來說

``` YAML
job:
  step1:
    env:
      VAR1='aaa'
    run: |
      VAR2='bbb'
  step2:
```

在 step2 的時候是不能使用 `$VAR1` 及 `$VAR2`，用了也只是一個空的東西，就是沒有定義過，所以要能夠，意思就是每個 step 都要設定一次 env 或者參考上面 `Step 間的傳遞變數`  來傳遞

## 平行執行 Job

可以參考這篇 [Using jobs in a workflow](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/using-jobs-in-a-workflow)，可以在 Job 中用 `need`, `required` 來控制 Job 的執行

## Job 間傳遞 artificat

前面執行的 Job 出來的 artificat 需要透過 上傳 再 下載 才可以給其他的 Job 使用，可以參考 [Storing and sharing data from a workflow](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow)

## GitHub 內建變數的使用

[Accessing contextual information about workflow runs](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/accessing-contextual-information-about-workflow-runs) 有列出內建的一些變數要怎麼使用

就這次使用到的來說說

- `ref_type` : 只會有 `tag` , `branch` 兩種值
- `ref_name` : 會依照觸發的事件而有不同的值
  - push tag 時候是 tag name
  - PR 的時候會是類似 `merged/14` 這種內容
  - push branch 的時候是 branch name

## 取得現在的 branch name 及 tag name

因為我們設計的規則中會需要去判斷現有的 branch name & tag name，所以要取得這 2 個的值，根據上面 `GitHub 內建變數的使用` 中有提到不同的情況下 `ref_name` 的值是不同的，在嘗試過後決定用 2 個 step 去分別就不同的情境去取得對應的值並且設定到 GitHub env 變數中

### 在 ref_type 是 branch 的情況下

因為此時 tag name 一定是空的，所以就保留空值，但 branch name 要依照現在是不是因為 pull request 觸發的而決定要抓 ref_name 還是 head_ref 來當作 branch name

### 在 ref_type 是 tag 的情況下
ref_name 就是 tag name 很單純，但 branch name 就比較複雜要使用 git 加上 grep 指令去抓出來
``` bash
$(git branch -r --contains ${{ github.ref }} | grep -v HEAD | head -n 1 | tr -d ' ' | sed 's/origin\///')
```

## GitHub Hosted Runner 的環境

可以參考 [這邊](https://github.com/actions/runner-images/tree/main/images) ，在 `images` 裡面有不同作業系統，展開作業系統裡可以看到不同名稱的 reedme.md 檔案，裡面有說每個 images 裡面已經預先裝好的環境

## 參考資料
- [act](https://github.com/nektos/act) 
  - 有人開發出可以在 local 測試 GitHub Action 的套件方便開發測試
