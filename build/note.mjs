#!/usr/bin/env node
// 把 public-notes 的 markdown 原稿轉成可以直接貼進點部落的 HTML。
//
// 用法：
//     node build/note.mjs "public-notes/flutter/某篇.md"      單檔 → 同目錄同名 .html
//     node build/note.mjs --all                              批次轉 public-notes 底下全部
//     node build/note.mjs --all talks                        批次轉指定目錄
//
// 選項：
//     --keep-h1    保留原稿開頭的 h1（預設拿掉，因為點部落自己有標題欄）
//     --stdout     印到 stdout 不寫檔
//
// 產出是「片段」不是完整 HTML 文件：一層 <div class="nb-post"> 包住內容，
// 前面一段 <style>。整份複製貼進點部落的 HTML 編輯區即可。
//
// 為什麼不直接用 VS Code 的 Markdown Preview 匯出（2026-08-19 實測點部落）：
//
//   1. 它匯出的是完整文件，CSS 裡有 `body`、`:root` 與 `@media (prefers-color-scheme)`
//      這些全域選擇器。點部落不 sanitize 貼進去的 HTML，所以那些規則會套到整個頁面上，
//      把站台的字型與底色一起改掉。這裡的 CSS 一律 scope 在 `.nb-post` 底下。
//   2. 點部落自己載了 highlight.js 8.9.1，會在 DOMContentLoaded 掃全頁 `pre code` 重新上色，
//      而它「沒有」yaml、kotlin、dart、gradle——正好是這批筆記最常用的。沒標語言的 block
//      還會被它自動猜（實測把一段目錄樹猜成 coffeescript）。
//      擋掉的方法是讓它的 blockLanguage() 判定為 no-highlight：class 用 `nohighlight`，
//      而且**不能**出現 `language-` 或 `lang-` 開頭的 class——它的偵測正則會咬到，
//      咬到之後若語言它認得（bash、json、xml…）就會把這裡烘好的顏色洗掉重做。
//      語言名改放在 pre 的 data-lang。
//   3. 點部落是固定深色（切到系統淺色模式量過，body 仍是 #333），所以配色直接配深底，
//      不要加 prefers-color-scheme 的分支。
import fs from "node:fs";
import path from "node:path";
import mdit from "markdown-it";
import anchor from "markdown-it-anchor";
import footnote from "markdown-it-footnote";
import tasks from "markdown-it-task-lists";
import Slugger from "github-slugger";
import hljs from "highlight.js";

const WRAP = "nb-post";

// ---------- 樣式 ----------
// 只補點部落沒有、或補了會明顯比較好讀的部分，其餘（字級、行高、標題、表格框線）
// 交給站台自己的 CSS，貼上去才不會跟站台其他頁長得不一樣。
// 站台量到的既有值：pre 背景 #222 / 邊框 #111 / 字 #eee，th 背景 #222，內文字 #bbb，連結 #8CB943。
const CSS = `
.${WRAP} pre { padding: 12px 14px; line-height: 1.55; overflow-x: auto; }
.${WRAP} pre code { background: none; padding: 0; white-space: pre; }
.${WRAP} :not(pre) > code { padding: 1px 5px; border-radius: 3px; }
.${WRAP} blockquote { border-left: 4px solid #555; padding: 6px 0 6px 16px; margin: 16px 0; color: #a6a6a6; }
.${WRAP} blockquote > :last-child { margin-bottom: 0; }
.${WRAP} .nb-table { overflow-x: auto; margin: 16px 0; }
.${WRAP} table { border-collapse: collapse; }
.${WRAP} th, .${WRAP} td { border: 1px solid #111; padding: 6px 10px; }
.${WRAP} img { max-width: 100%; height: auto; }
.${WRAP} hr { border: 0; border-top: 1px solid #4a4a4a; margin: 28px 0; }
.${WRAP} .task-list-item { list-style: none; }
.${WRAP} .task-list-item input { margin: 0 6px 0 -18px; }
.${WRAP} .footnotes { font-size: 0.9em; color: #a6a6a6; }
.${WRAP} .hljs-comment, .${WRAP} .hljs-quote { color: #7f848e; font-style: italic; }
.${WRAP} .hljs-keyword, .${WRAP} .hljs-selector-tag, .${WRAP} .hljs-literal { color: #c678dd; }
.${WRAP} .hljs-string, .${WRAP} .hljs-addition { color: #98c379; }
.${WRAP} .hljs-number, .${WRAP} .hljs-symbol, .${WRAP} .hljs-bullet { color: #d19a66; }
.${WRAP} .hljs-attr, .${WRAP} .hljs-attribute, .${WRAP} .hljs-property { color: #d19a66; }
.${WRAP} .hljs-title, .${WRAP} .hljs-section, .${WRAP} .hljs-function { color: #61afef; }
.${WRAP} .hljs-type, .${WRAP} .hljs-class, .${WRAP} .hljs-built_in { color: #e5c07b; }
.${WRAP} .hljs-variable, .${WRAP} .hljs-template-variable, .${WRAP} .hljs-tag,
.${WRAP} .hljs-name, .${WRAP} .hljs-deletion, .${WRAP} .hljs-regexp { color: #e06c75; }
.${WRAP} .hljs-meta, .${WRAP} .hljs-subst, .${WRAP} .hljs-operator { color: #56b6c2; }
.${WRAP} .hljs-emphasis { font-style: italic; }
.${WRAP} .hljs-strong { font-weight: 700; }
`.trim();

// ---------- markdown ----------

const slugger = new Slugger();

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;");
}

// highlight.js 沒有的語言，對到最接近的一個；對不到就純文字輸出（不猜）。
const ALIAS = { gitignore: "bash", conf: "ini", env: "bash", sh: "bash", zsh: "bash" };

const md = mdit({
  // html:false 是刻意的。這批筆記裡唯一「看起來像 HTML」的是 iOS 篇的
  // <current_directory>，那是佔位符不是標籤；html:true 會讓它變成未知元素、
  // 在頁面上整段消失。改成跳脫顯示才對。
  html: false,
  linkify: true,
  typographer: false,
  breaks: false,
  highlight(code, lang) {
    const key = lang && (hljs.getLanguage(lang) ? lang : ALIAS[lang.toLowerCase()]);
    const body = key
      ? hljs.highlight(code, { language: key, ignoreIllegals: true }).value
      : escapeHtml(code);
    const attr = lang ? ` data-lang="${escapeHtml(lang)}"` : "";
    // 回傳字串以 <pre 開頭時 markdown-it 會原樣輸出，不再自己包一層 pre。
    return `<pre${attr}><code class="nohighlight">${body}</code></pre>`;
  },
})
  .use(footnote)
  .use(tasks, { enabled: false, label: false })
  // 只掛 id，不加 permalink 連結：原稿裡有 [x](#y) 這種內部錨點要能跳，
  // 但把標題整個包成 <a> 會讓它套到站台的連結色（#8CB943），整排標題變綠。
  .use(anchor, { slugify: (s) => slugger.slug(s), tabIndex: false });

// 寬表格在點部落的 730px 內文欄會撐破版面，包一層可橫向捲動的容器。
md.renderer.rules.table_open = () => `<div class="nb-table">\n<table>`;
md.renderer.rules.table_close = () => `</table>\n</div>`;

// ---------- 轉換 ----------

function clean(src) {
  // UTF-8 BOM 會卡在開頭的 `#` 前面，害那行解析不成 h1 而變成內文段落。
  src = src.replace(/^\uFEFF/, "");
  const m = /^---\r?\n([\s\S]*?)\r?\n---\r?\n/.exec(src);
  return m ? src.slice(m[0].length) : src;
}

/** 拿掉開頭那個 h1，回傳 [剩下的 token, 標題文字]。點部落的標題另有欄位，內文再放一次是重複的。 */
function takeTitle(tokens) {
  const i = tokens.findIndex((t) => t.type !== "front_matter");
  if (tokens[i]?.type === "heading_open" && tokens[i].tag === "h1") {
    const title = tokens[i + 1].content;
    tokens.splice(i, 3);
    return title;
  }
  return null;
}

function convert(src, { keepH1 }) {
  slugger.reset();
  const tokens = md.parse(clean(src), {});
  const title = keepH1 ? null : takeTitle(tokens);
  const html = md.renderer.render(tokens, md.options, {});
  const out = `<div class="${WRAP}">\n<style>\n${CSS}\n</style>\n\n${html.trim()}\n</div>\n`;
  return { html: out, title };
}

/** 貼之前值得知道的事：相對路徑的圖片貼過去一定壞，先講。 */
function warnings(html, file) {
  const out = [];
  for (const m of html.matchAll(/<img[^>]+src="([^"]+)"/g)) {
    if (!/^(https?:)?\/\//.test(m[1])) out.push(`圖片是相對路徑，貼上去會壞：${m[1]}`);
  }
  for (const m of html.matchAll(/<a[^>]+href="(?!#|https?:|mailto:)([^"]+)"/g)) {
    out.push(`連結指向本機路徑，貼上去會壞：${m[1]}`);
  }
  return out.map((w) => `  ⚠ ${path.basename(file)}：${w}`);
}

// ---------- CLI ----------

const argv = process.argv.slice(2);
const flags = new Set(argv.filter((a) => a.startsWith("--")));
const args = argv.filter((a) => !a.startsWith("--"));
const keepH1 = flags.has("--keep-h1");
const toStdout = flags.has("--stdout");

function listMarkdown(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return listMarkdown(p);
    return e.isFile() && p.endsWith(".md") ? [p] : [];
  }).sort();
}

function run(file) {
  const src = fs.readFileSync(file, "utf8");
  const { html, title } = convert(src, { keepH1 });
  if (toStdout) {
    process.stdout.write(html);
  } else {
    const dst = file.replace(/\.md$/, ".html");
    fs.writeFileSync(dst, html, "utf8");
    console.log(`${path.basename(file)} → ${path.basename(dst)}`);
  }
  if (title) console.log(`  標題欄可以填：${title}`);
  const w = warnings(html, file);
  if (w.length) console.log(w.join("\n"));
}

if (!args.length && !flags.has("--all")) {
  console.error("用法：node build/note.mjs <原稿.md>｜node build/note.mjs --all [目錄]");
  process.exit(1);
}

const targets = flags.has("--all") ? listMarkdown(args[0] || "public-notes") : args;
for (const f of targets) run(f);
