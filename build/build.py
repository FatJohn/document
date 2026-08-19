#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一份 Markdown 投影片原稿轉成單檔 HTML，外加一份逐字稿。

用法：
    python3 build/build.py talks/flutter-cicd/index.md

產出兩個檔：`<原稿>.html`（投影片）與 `<原稿>-script.md`（逐字稿，由 `>` 那些行組成）。
兩個都是產物，不要手改——投影片與講稿共用同一份原稿，就是為了不再手動同步。

原稿格式（工作流程見 repo 根目錄的 README.md）：

    ---
    title: 投影片標題
    eyebrow: 封面上方的小字
    ---

    # 章節名                 → 章節轉場頁
    > 章節說明（一行）

    ## 投影片標題            → 一般投影片
    @ 麵包屑 / 副標
    第一段文字就是 lede。

    > 這行是講者稿，不會進投影片。

    - 條列
    1. 編號步驟

    | 欄 | 位 |
    |---|---|
    | a | b |

    ```kotlin dev-b sm
    // 註解會自動上色
    val x = «重點»
    ```

    ::: compare
    ::: pane dev | 左欄標題
    key :: value
    一般段落。
    :::
    :::

    ::: note 提醒的標題
    內文。
    :::

以 `<` 開頭的區塊原樣輸出，任何 template 沒涵蓋的排版都用它。
"""
import io
import os
import re
import sys

THEME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme.html")


# ---------- inline ----------

def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(t):
    """行內語法：`code`、**strong**、«accent»、\\ 換行。原始 HTML 標籤原樣保留。

    `code` 先抽成佔位符再處理 HTML，否則 `foo/<env>.json` 裡的 <env> 會被當成
    標籤切走，反引號跟著配對錯位。
    """
    keep = []

    def stash(html):
        keep.append(html)
        return "\x01%d\x01" % (len(keep) - 1)

    # `code` 與原始 HTML 標籤都先收起來：前者才不會被當標籤切走，後者則讓
    # **strong** 與 «accent» 可以跨過 <br> 這種標籤配對。
    t = re.sub(r"`([^`]+)`", lambda m: stash("<code>%s</code>" % esc(m.group(1))), t)
    t = re.sub(r"<[^>]+>", lambda m: stash(m.group(0)), t)
    t = esc(t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"«([^»]+)»", r'<span class="acc-t">\1</span>', t)
    t = t.replace("\\\n", "<br>")
    return re.sub(r"\x01(\d+)\x01", lambda m: keep[int(m.group(1))], t)


def code_body(text, lang):
    """程式碼：跳脫、註解上色、«…» 標重點。"""
    out = []
    for line in esc(text).split("\n"):
        line = re.sub(r"«([^»]*)»", r'<span class="a">\1</span>', line)
        marker = "//" if lang in ("kotlin", "kt", "swift", "java", "js", "ts", "dart") else "#"
        # #include / #define 這類 preprocessor 指令不是註解，從它後面才開始找
        start = 0
        if marker == "#":
            m = re.match(r"^\s*#(include|import|define|if|ifdef|else|endif)\b", line)
            if m:
                start = m.end()
        idx = line.find(marker, start)
        if idx >= 0 and '<span class="a">' not in line[idx:]:
            line = line[:idx] + '<span class="c">' + line[idx:] + "</span>"
        out.append(line)
    return "\n".join(out)


# ---------- block ----------

def render_table(lines):
    rows = []
    for ln in lines:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        rows.append(cells)
    head, body = rows[0], rows[2:]          # rows[1] 是分隔線
    out = ["<table>", "<thead>", "<tr>"]
    for c in head:
        cls, c = cell_class(c)
        out.append("<th%s>%s</th>" % (cls, inline(c)))
    out += ["</tr>", "</thead>", "<tbody>"]
    for r in body:
        out.append("<tr>")
        for c in r:
            cls, c = cell_class(c)
            out.append("<td%s>%s</td>" % (cls, inline(c)))
        out.append("</tr>")
    out += ["</tbody>", "</table>"]
    return '<div class="tw">\n%s\n</div>' % "\n".join(out)


def cell_class(c):
    """儲存格開頭的 {m nw} 之類標記轉成 class。"""
    m = re.match(r"^\{([^}]+)\}\s*(.*)$", c)
    return (' class="%s"' % m.group(1), m.group(2)) if m else ("", c)


def parse_blocks(lines):
    """把一段內容切成 HTML 區塊。回傳 list[str]。"""
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue

        # ::: 容器
        if ln.startswith(":::"):
            spec = ln[3:].strip()
            depth, j = 1, i + 1
            while j < n and depth:
                if lines[j].startswith(":::") and lines[j][3:].strip():
                    depth += 1
                elif lines[j].strip() == ":::":
                    depth -= 1
                    if not depth:
                        break
                j += 1
            out.append(render_container(spec, lines[i + 1:j]))
            i = j + 1
            continue

        # 程式碼
        if ln.startswith("```"):
            spec = ln[3:].strip().split()
            lang = spec[0] if spec else ""
            extra = " ".join(spec[1:]) if len(spec) > 1 else ""
            j = i + 1
            while j < n and not lines[j].startswith("```"):
                j += 1
            cls = ("code " + extra).strip()
            body = "\n".join(lines[i + 1:j])
            # pre 內的換行改用 NUL 佔位，build_slide 的縮排就碰不到它；
            # 寫檔前再還原。否則每一行都會多吃 8 個空白，縮排全歪。
            if lang == "mermaid":
                out.append('<div class="diagram">\n<pre class="mermaid">%s</pre>\n</div>'
                           % ("\x00%s\x00" % esc(body)).replace("\n", "\x00"))
            else:
                out.append('<pre class="%s">%s</pre>'
                           % (cls, code_body(body, lang).replace("\n", "\x00")))
            i = j + 1
            continue

        # 表格
        if ln.lstrip().startswith("|"):
            j = i
            while j < n and lines[j].lstrip().startswith("|"):
                j += 1
            out.append(render_table(lines[i:j]))
            i = j
            continue

        # 條列 / 編號
        m_ul = re.match(r"^- (.*)$", ln)
        m_ol = re.match(r"^\d+\. (.*)$", ln)
        if m_ul or m_ol:
            tag, cls = ("ul", "clean") if m_ul else ("ol", "steps")
            pat = r"^- (.*)$" if m_ul else r"^\d+\. (.*)$"
            items, j = [], i
            while j < n:
                m = re.match(pat, lines[j])
                if m:
                    items.append(m.group(1))
                elif lines[j].startswith("  ") and items:
                    items[-1] += " " + lines[j].strip()
                else:
                    break
                j += 1
            out.append("<%s class=\"%s\">\n%s\n</%s>" % (
                tag, cls, "\n".join("  <li>%s</li>" % inline(x) for x in items), tag))
            i = j
            continue

        # 原始 HTML
        if ln.lstrip().startswith("<"):
            j = i
            while j < n and lines[j].strip():
                j += 1
            out.append("\n".join(lines[i:j]))
            i = j
            continue

        # 段落
        j = i
        while j < n and lines[j].strip() and not re.match(r"^(:::|```|\||- |\d+\. |<)", lines[j].lstrip()):
            j += 1
        out.append('<p class="lede wide">%s</p>' % inline(" ".join(x.strip() for x in lines[i:j])))
        i = j
    return out


def render_container(spec, body):
    if spec.startswith("compare"):
        extra = spec[len("compare"):].strip()
        inner = parse_blocks(body)
        return '<div class="compare%s">\n%s\n</div>' % (
            (" " + extra) if extra else "", "\n".join(inner))

    if spec.startswith("pane"):
        rest = spec[len("pane"):].strip()
        tone, _, title = rest.partition("|")
        rows, others = [], []
        for ln in body:
            if " :: " in ln:
                k, _, v = ln.partition(" :: ")
                rows.append('<div class="row"><span class="k">%s</span><span class="v">%s</span></div>'
                            % (inline(k.strip()), inline(v.strip())))
            else:
                others.append(ln)
        blocks = parse_blocks(others)
        blocks = [b.replace('<p class="lede wide">', "<p>") for b in blocks]
        head = "<h3>%s</h3>" % inline(title.strip()) if title.strip() else ""
        return '<div class="pane %s">\n%s\n%s\n%s\n</div>' % (
            tone.strip() or "neutral", head, "\n".join(rows), "\n".join(blocks))

    if spec.startswith("note"):
        title = spec[len("note"):].strip()
        text = " ".join(x.strip() for x in body if x.strip())
        return '<div class="note">\n  <b>%s</b>\n  %s\n</div>' % (inline(title), inline(text))

    if spec.startswith("idshow"):
        lines_out = []
        for ln in body:
            base, _, rest = ln.partition("+")
            suf, _, note = rest.partition("::")
            tone = "dev" if "dev" in note else "prod"
            lines_out.append(
                '<div class="idline small"><span class="idbase">%s</span>'
                '<span class="idsuf %s" data-note="%s">%s</span></div>'
                % (esc(base.strip()), tone, esc(note.split("|")[-1].strip()),
                   esc(suf.strip()) or "&nbsp;&nbsp;&nbsp;"))
        return '<div class="idshow">\n%s\n</div>' % "\n".join(lines_out)

    return "\n".join(body)


# ---------- slides ----------

def build_slide(kind, title, meta, body_lines, chnum=None):
    eyebrow = meta.get("eyebrow", "")
    sec = meta.get("sec", "")
    attr = ' data-sec="%s"' % esc(sec) if sec else ""

    if kind == "cover":
        return ('    <section class="slide cover"%s>\n'
                '      <div class="eyebrow">%s</div>\n'
                '      <h1>%s</h1>\n'
                '      <p class="sub">%s</p>\n'
                '      <div class="byline">\n'
                '        <span class="who">%s</span>\n'
                '        <span class="what">%s</span>\n'
                '      </div>\n    </section>'
                % (attr, inline(eyebrow), inline(title),
                   inline(meta.get("sub", "")), inline(meta.get("who", "")),
                   inline(meta.get("what", ""))))

    if kind == "thanks":
        return ('    <section class="slide thanks"%s>\n      <h1>%s</h1>\n'
                '      <p class="qa">Q &amp; A</p>\n      <p class="sig">%s</p>\n    </section>'
                % (attr, inline(title), inline(meta.get("sig", ""))))

    if kind == "chapter":
        sub = " ".join(x.strip() for x in body_lines if x.strip())
        return ('    <section class="slide chapter"%s>\n'
                '      <div class="chnum">Chapter %02d</div>\n'
                '      <h2>%s</h2>\n      <p class="chsub">%s</p>\n    </section>'
                % (attr, chnum, inline(title), inline(sub)))

    blocks = parse_blocks(body_lines)
    lede = ""
    if blocks and blocks[0].startswith('<p class="lede wide">'):
        lede = "      " + blocks.pop(0).replace('class="lede wide"', 'class="lede"') + "\n"
    cls = "slide tight" if meta.get("tight") else "slide"
    body = "\n".join("        " + b.replace("\n", "\n        ") for b in blocks)
    return ('    <section class="%s"%s>\n      <div class="eyebrow">%s</div>\n'
            '      <h2>%s</h2>\n%s      <div class="body">\n%s\n      </div>\n    </section>'
            % (cls, attr, inline(eyebrow), inline(title), lede, body))


def parse(src):
    lines = src.split("\n")
    front, i = {}, 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            k, _, v = lines[i].partition(":")
            front[k.strip()] = v.strip()
            i += 1
        i += 1

    slides, cur, chnum, sec = [], None, 0, ""
    fenced = False
    for ln in lines[i:]:
        if ln.startswith("```"):
            fenced = not fenced          # 圍籬內的 # 是註解，不是標題
        m1 = None if fenced else re.match(r"^# (.+)$", ln)
        m2 = None if fenced else re.match(r"^## (.+)$", ln)
        if m1 or m2:
            if cur:
                slides.append(cur)
            if m1:
                chnum += 1
                sec = m1.group(1).strip()
                cur = {"kind": "chapter", "title": sec, "meta": {"sec": sec}, "body": [], "notes": [], "chnum": chnum}
            else:
                t = m2.group(1).strip()
                kind = "cover" if t == "@cover" else ("thanks" if t == "@thanks" else "slide")
                cur = {"kind": kind, "title": t, "meta": {"sec": sec}, "body": [], "notes": [], "chnum": chnum}
            continue
        if cur is None:
            continue
        if ln.startswith("@ "):
            cur["meta"]["eyebrow"] = ln[2:].strip()
            continue
        m = re.match(r"^@(\w+):(.*)$", ln)
        if m:
            cur["meta"][m.group(1)] = m.group(2).strip()
            continue
        if ln.startswith(">"):
            cur["notes"].append(ln[1:].strip())        # 講者稿，不進 HTML，只進逐字稿
            continue
        cur["body"].append(ln)
    if cur:
        slides.append(cur)
    return front, slides


def build_script(front, slides):
    """把 `>` 講者稿抽成一份能照著唸的逐字稿。它是產物，不是第二份來源。"""
    out = ["# %s · 講稿" % front.get("title", ""), "",
           "> 由 `python3 build/build.py` 從投影片原稿自動產生，**不要手改**——",
           "> 內容來源是原稿裡 `>` 開頭的行，要改講稿請改原稿再重跑。",
           "",
           "共 %d 張。" % len(slides), ""]
    for i, s in enumerate(slides, 1):
        if s["kind"] == "cover":
            head = "封面：%s" % front.get("title", "")
        elif s["kind"] == "thanks":
            head = "謝謝 / Q&A"
        elif s["kind"] == "chapter":
            head = "章節轉場：%s" % s["title"]
        else:
            head = s["title"]
        out += ["---", "", "## %d · %s" % (i, head)]
        eyebrow = s["meta"].get("eyebrow", "")
        if eyebrow:
            out += ["", "`%s`" % eyebrow]
        notes = list(s.get("notes", []))
        while notes and not notes[-1]:
            notes.pop()
        out += [""] + (notes if notes else ["（這張沒有講稿）"]) + [""]
    return "\n".join(out).rstrip() + "\n"


def main():
    if len(sys.argv) < 2:
        sys.exit("用法：python3 build.py <原稿.md>")
    src_path = sys.argv[1]
    src = io.open(src_path, encoding="utf-8").read()
    front, slides = parse(src)

    for s in slides:
        if s["kind"] == "cover":
            s["title"] = front.get("title", "")
            s["meta"].update({k: front.get(k, "") for k in ("eyebrow", "sub", "who", "what")})
        if s["kind"] == "thanks":
            s["title"] = "謝謝"
            s["meta"]["sig"] = front.get("sig", front.get("who", ""))

    html = "\n\n".join(build_slide(s["kind"], s["title"], s["meta"], s["body"], s.get("chnum"))
                       for s in slides)
    theme = io.open(THEME, encoding="utf-8").read()
    out = (theme.replace("{{TITLE}}", front.get("title", ""))
                .replace("{{COUNT}}", str(len(slides)))
                .replace("{{SLIDES}}", html))
    base = os.path.splitext(src_path)[0]
    dst, script_dst = base + ".html", base + "-script.md"
    io.open(dst, "w", encoding="utf-8").write(out.replace("\x00", "\n"))
    io.open(script_dst, "w", encoding="utf-8").write(build_script(front, slides))
    print("%s → %s（%d 張）＋ %s" % (os.path.basename(src_path), os.path.basename(dst),
                                    len(slides), os.path.basename(script_dst)))


if __name__ == "__main__":
    main()
