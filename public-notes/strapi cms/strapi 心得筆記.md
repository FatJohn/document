strapi 心得分享
===

[strapi](https://strapi.io/) 是一套 open source headless CMS，因緣際會下我們使用這套來當作 CMS，第一次使用就踩到了一些雷，記錄一下提供有興趣使用的人參考

## 第一個雷

首先第一個雷就是在開發流程上，當你依照文件調整了幾個主要的設定檔案 `admin.ts`, `api.ts`, `database.ts`, `middleware.ts`, `plugin.ts`, `server.ts` 然後把它包成 docker image 放到 container service 如 ECS 跑起來然後給內容建立人員玩了後，運氣好（我現在稱之為運氣好）你會在很初期就發現這個恐怖的雷。

當你使用 Content-Type Builder 建立你要的資料格式並且用 Content Manager 輸入資料時，萬不幸遇到一些錯誤導致 container 重啟後你就會發現你剛剛建立的東西包含 Content type 以及所建立的資料都清空啦～

後來發現了原因

因為使用 Content-Type Builder 去建立自定義的型態的時候，它真正的做動是**新增/修改原始碼**，如果你在本機跑起來去調整 Content-Type 時候，你可以發現 git change，對應的更動就是你剛剛調整的 Content-Type 會建立對應的程式碼，所以為什麼重啟 container 後會一切不見呢？因為最初的 image 裡面並沒有那些變動，所以重啟之後在 Content-Type Builder 就看不到剛剛建立的東西啦～

Content-Type 不見是一件事情，恐怖的是 strapi 啟動時候看起來會依照現在的 Content-Type 去"整理"資料庫，所以既然沒有那些 Content-Type 所以資料庫裡面的東西就會被清掉！！

這真的是太棒了 XD 不知道是哪一個天才這樣設計的，如果玩的是線上資料庫，被這樣應該會有人要去切負謝罪了吧！ XD

## 正確的開發流程(?)

加上 ？ 是因為嚴格上我覺得這不能算正確，只能說是 work around 的流程

同上面說的因為調整 ContentType 其實會更動原始碼，所以開發流程會變的是
1. 開發人員在 local 去建立/調整對應的 Content-Type 後要把 code change 上到 git
2. 再走 CI/CD 流程部屬

這樣才能確保萬不幸 container 重啟後東西不會不見

## 其他可能的開發流程

其他的流程就是不採用 git 這條路

### 流程 1：image 裡面執行的 code 是 mount 外部的 storage

既然會變動原始碼，那就把會變動的原始碼是放在一個不會因為 container 重新啟動而造成原始碼流失的地方

### 流程 2：經常的 snapshot 備份

既然會變動原始碼，那就在每次變動或者頻繁的備份 snapshot image 以及 db


## 第二個雷

說上述流程開發流程可以避免第一個雷，但想起來情境都滿侷限於**單人開發**！

多人開發時候，意思就是多人會變動 Content-Type，不同步變更不同的 Content-Type 時，一旦啟動 local strapi 連上資料庫就有可能造成資料清除，是的！會清除！

即便同一個 Content-Type 兩個人的欄位不同的話也會被清除！因為我就遇到是手邊兩個不同版本的 code 啟動後就讓資料被清除了

總之就是針對 Content-Type 的變動都要十分的小心，主要是有機會造成資料流失

## 其他補充

### 補充 1

strapi 啟動有模式有 production, dev mode，當你用 production mode 啟動的時候，其實 Content Type Builder 的功能是會不見的，只允許人員新增 content

一開始我不懂為什麼會這樣，踩到雷後就知道為什麼了 😅

### 補充 2

在 packages.json 裡面可以發現有 `"upgrade": "npx @strapi/upgrade latest",` 的指令，但如果你在本機執行後，會發現其實 git change 裡面會是空的

目前猜測這個應該是直接更新 build 出來後裡面的 strapi，主要是給正在運行的服務使用（吧？），所以如果開發者要更新版本的話就一樣用 npm update 就好了

### 補充 3

在 Content Type builder 裡面可以調整用戶輸入時候的欄位的名稱，例如通常都用英文名稱來命名欄位，但實際上用戶輸入時希望看到中文，我們可以再 Content Type Builder 調整每個欄位在輸入時候的 Label 就變成中文

**這個會有 Source Chagne！**
**這個會有 Source Chagne！**
**這個會有 Source Chagne！**


## 小結

以上 2 點是要採用 strapi 的 solution 前一定要知道的事情，除了協作時候會很卡是小事，資料不見就事情大條了

然後下面就以使用者、接 API 的開發者來講一下我覺得不太方便的地方

## 使用上不方便之處

### Content-Type Builder 調整欄位順序不方便

Content Type Builder 裡面是可以調整輸入欄位的順序、佔據每一個 row 的百分比。

但問題是那個拖拉順序很奇怪
* 當你輸入項目不是佔據 100% 的話，幾乎無法改變他的輸入順序
* 即便你改了欄位都是 100% ，你把一個欄位拖到一個地方，其他的欄位移動的方式也不一定會如你預期的移動到正下方

所以如果一直搞不定的話，有個蠢但是有效的方式，就是先把欄位移除掉再慢慢依照想要的順序加上去

### 多語系介面支援不友善

原生只開英文，你可以在 app.tsx 把希望支援的語系打開，例如我們當然希望支援繁體中文，打開後你會發現

1. 預設還是改不了，一定要用戶自己登入後再去自己調整語系
2. 翻譯不完全，意思就是切換成中文，畫面上還是有滿多地方是英文的，某種程度可以理解，但奇妙的是我去翻 strapi source code 明明有些地方字串是有翻譯成中文的，但在介面上就是英文
3. 官方文件有說是可以自己家上翻譯的，但問題是介面上的哪一個項目對應到哪一個翻譯的 key 沒有一個很好的對照表，所以即便是要自己翻譯也沒這麼容易，而且也可能遇到 2 的問題，明明有 key 卻不會出現翻譯後的文字

### Content Type Builder 裡面沒有陣列型態支援，一定要用 relation 的方式

舉個例子來說，有一個欄位是喜歡的複數影片連結，在想像中我們可以給他一個陣列裡面就都是字串，很抱歉 strapi 沒有內建支援陣列這種東西，要碼你可以用一個 長字串 的欄位，讓它自己用特定符號來當作分隔，然後前端拿到資料再做處理，要碼你就是要另外建立一個 Type 專門記錄影片，然後建立這兩個 Type 的 relation

有搜尋到有 plugin 可以用，但看起來那個 plugin 僅限於 enumation 型態可以使用

### 建立 A 資料時順便要建立 B 的 relation 的時候不方便

A 裡面有一個欄位關連到 B，所以建立 A 的時候輸入到 B 時就可以透過介面去建立，但如果你沒有先把 A publish 的話，建立 B 完後並不會直接把兩者個關連建立起來，即便 A 是先 Save 也不行，一定要先 publish。

但這樣也不是說沒救，後續再自己去建立關連就好，但就是不方便。

### API 介接不優雅

要接上 starpi 的 API 官方有說到 3 種方式
1. Strapi Client
2. REST API
3. GraphQL API

個人覺得除了 GraphQL API 是"原生"的外，其他的都是在 GraphQL API 基礎上包裝一層，所以我們使用 REST API 介接的時候就會有 API 要給的欄位全部都是由 client 指定的現象

全部由 client 指定我覺得還好，問題是指定的方式有點傷腦筋，舉個例子來說

這邊有 3 個 Type，User 關連到 Article，Article 關連到複數個 ArticleCategory，User 裡面比較特別的是 Avatar 這個欄位是一個 Media，Media 代表就是會有圖片、音樂檔案的類型，是 strapi 內建的

User
| Name    | Type         |
| ------- | ------------ |
| Name    | string       |
| Articls | Article Type |
| Avatar  | Media        |

Article
| Name       | Type     |
| ---------- | -------- |
| Name       | string   |
| Categories | Category |

ArticleCategory
| Name | Type   |
| ---- | ------ |
| Name | string |

這時候你想要一次拉出一個 User 怎麼拉出一個完整的資料呢？
這邊給你個 request url 的範例，其他更詳細的就麻煩自己去看文件了

```
https://localhost:1337/api/artists/{artistId}?&populate[Avatar][fields][0]=url&populate[Article][fields]=*&populate[Article][populate][Categories][fields][0]=name
```

對，就是這麼麻煩
* fields 是用來指定拉取的欄位名稱
* populate 是要拉關連資料時要用的 keyword
* 後面 `[0]` 這種就是第一個欄位，可以多拉幾個欄位就是 `[1] [2]` 以此類推，全拉可以參考上面就用 `*` 代替
* 多層關連就要下對多層的 populate
* Media 也是要使用 populate

我很懷疑如果條件多、欄位多等複雜的條件會不會超過 url 長度限制 XD

我自己接 API 的時候就是生了一段 fetch 的 javascript code 直接在 browser console 測試看看這樣下對不對，有沒有撈出我想要的結果

## 小結 2
上面就是使用上覺得不方便的地方，也許這也是你考慮要不要使用 strapi 的一個參考，身為一個開發者對於 REST API 接的方式真覺得莫名的噁心 XD 噁心但有效這樣？

接下來就提供一些使用上一些技巧吧

## 使用技巧
### `Plugin` strapi-plugin-sso 整合 SSO

strapi 正式支援 SSO 的版本要付費的或雲端的版本才有，但我們使用的是自建的，所以要整合 SSO 的話就要用 [strapi-plugin-sso](https://github.com/yasudacloud/strapi-plugin-sso) 這個 plugin

如果你放在 Container 在跑，前面有加上 Loadbalancer 的話，要記得 proxy 設定要對，不然會有錯誤發生，請參考下面，proxy 的設定的方式在 strapi 5 之後好像有變動，所以現在這樣的設定才對

``` typescript
server.ts

export default ({ env }) => ({
  host: env('HOST', '0.0.0.0'),
  port: env.int('PORT', 3000),
  proxy: {
    koa: true,
  },
  app: {
    keys: env.array('APP_KEYS'),
  },
});

```

### `Plugin` @strapi/provider-upload-aws-s3

strapi 支援把 media 上傳到 S3(或相容) 的地方去，透過的就是 [@strapi/provider-upload-aws-s3](https://github.com/strapi/strapi/tree/93cd7e55a8a06c2a07462d4f075d4292a6559989/packages/providers/upload-aws-s3) 這個套件，這個 github 頁面裡面有把相關要注意的 config 的地方都有補上，包含 S3 要開 CORS 等等

但其中在 middleware 的設定少了一點，這個沒設定對很有可能讓你 strapi 裡面的圖片預覽出不來

github 頁面裡面的 middleware 的設定如下
```
module.exports = [
  // ...
  {
    name: 'strapi::security',
    config: {
      contentSecurityPolicy: {
        useDefaults: true,
        directives: {
          'connect-src': ["'self'", 'https:'],
          'img-src': [
            "'self'",
            'data:',
            'blob:',
            'market-assets.strapi.io',
            'yourBucketName.s3.yourRegion.amazonaws.com',
          ],
          'media-src': [
            "'self'",
            'data:',
            'blob:',
            'market-assets.strapi.io',
            'yourBucketName.s3.yourRegion.amazonaws.com',
          ],
          upgradeInsecureRequests: null,
        },
      },
    },
  },
  // ...
];
```

你可以發現要裡面有 S3 的位置，**但是**如果你的 S3 前面有 CDN 的話，記得也要把 CDN 的位置也補上去，例如 CDN 對應的網址是 `abc.com` 那也要記得把 `abc.com` 補在列表中，否則還是過不了 secirity 的檢查導致預覽無法出現

### 官方文件 AI 可以用

在 strapi 的官網裡面有內建的 AI 功能可以問他問題，基本上都還滿準確的，但最終還是需要以文件為準就是，AI 沒有總是學到最新的資訊。

## 總結

以上就是目前用 strapi 建構了一個 CMS 並且即將上線使用的心得，希望對看的人有所幫助。

你問我下次還會不會用 strapi？我會說... 我們可以先找找其他套 headless CMS 看看有沒有不會遇到上面問題的解決方案 XD

## 未解之謎

看了上述那些雷點，不知道 strapi 的雲端版本的是會怎麼運作不會遇到那些雷的

~~應該不會真的 snapshot backup 吧~~
