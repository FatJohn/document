# document

胖胖（JohnShu）的公開簡報，發佈在 <https://fatjohn.github.io/document/>。

| 路徑 | 內容 |
|---|---|
| `index.html` | 站台索引頁 |
| `flutter-cicd/index.md` | 《Flutter App 的建置與發版流程設計》的**原稿** |
| `flutter-cicd/index.html` | 上面那份的產出（投影片本體，就是網站上看到的那頁） |
| `flutter-cicd/index-script.md` | 上面那份的產出（逐字稿，投影片上不會出現的講者稿） |
| `flutter-cicd/samples/` | 這份簡報提到的 script 與設定檔樣本，去識別化過 |
| `build/build.py` | markdown 原稿 → HTML ＋ 逐字稿的 generator |
| `build/theme.html` | 樣式 template |

## 改簡報

**投影片與講者稿是同一份檔案。** `.md` 原稿裡 `>` 開頭的行是講者稿，只會進逐字稿、不會出現在投影片上。改內容只要改 `.md`，然後重跑：

```bash
python3 build/build.py flutter-cicd/index.md
```

一次產兩個檔：`index.html`（投影片）與 `index-script.md`（逐字稿）。**兩個都是產物，不要手改**，下次 build 會被蓋掉。原稿格式說明在 [`build/build.py`](build/build.py) 的檔頭。

推上 `main` 之後 GitHub Pages 會自動重新發佈，不需要額外動作。

## 怎麼看

單一 HTML、方向鍵翻頁、深淺色跟隨系統。流程圖由 mermaid 在瀏覽器端渲染，需要連得到網路（離線時圖不會出現，其餘內容正常）。只想讀內容的話直接看 `.md` 也行。

改完之後值得順手量一次爆版——這套排版的溢出是靜默的，內容被 `overflow` 吃掉，看起來像正常的頁：

```bash
python3 -m http.server 8899 --directory .
```

開 `http://localhost:8899/flutter-cicd/`，viewport 拉到 1280 以上（窄於 760 會進手機版斷點），在 console 逐張比對 `scrollHeight` 與 `clientHeight`，要求全部零溢出。爆版的修法優先序是**先刪字**，其次在該張加 `tight`，最後才降 code 的字級。

## 內容來源

這份簡報講的是一套實際在跑的 Flutter CI/CD 流程，內容已去識別化：專案代號、bundle id、app 名稱、後端網域與 Firebase 專案都換成了假值。samples 裡的每一支也都在檔頭寫明擷取日期與它跟原檔的差異。
