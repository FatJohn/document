GitHub Action Bot 冷知識
===

## 讓 GitHub Actions Bot 的 Commit 變成 Verified

今天才知道，原來 GitHub Actions 自動 commit 的時候，是可以讓那個 commit 顯示 verified 標籤的。

關鍵就是把 git 的 user email 設成 GitHub Actions bot 專屬的 email：

```bash
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
```

設完之後正常 commit 就好，GitHub 會自動認得這是它家的 bot，直接幫你掛上 verified。

### 建立 PR 也適用

如果你跟我一樣，除了 commit 還需要 action 自動開 PR，一樣可以用這組 email。像我是用 `peter-evans/create-pull-request` 這個 action：

```yaml
- name: Create Pull Request
  uses: peter-evans/create-pull-request@v8
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    committer: github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>
    author: github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>
```

### 那個 `41898282` 是什麼？

這串數字是 GitHub Actions bot 的 user ID。每個 bot 帳號都有自己的 ID，email 格式就是 `{id}+{username}@users.noreply.github.com`。

這個 ID 看起來沒有公開的官方文件記錄，不過可以直接用 GitHub API 查：

```bash
# GitHub Actions bot
curl -s https://api.github.com/users/github-actions%5Bbot%5D | grep -E '"id"|"login"'
# => "login": "github-actions[bot]",
# => "id": 41898282,

# Dependabot 也有自己的
curl -s https://api.github.com/users/dependabot%5Bbot%5D | grep -E '"id"|"login"'
# => "login": "dependabot[bot]",
# => "id": 49699333,
```

所以如果你用的是 Dependabot 或其他 bot，用同樣的方式查一下 ID 就能組出對應的 email。

當啷～ 這...真他喵的是個天才！！🤪
