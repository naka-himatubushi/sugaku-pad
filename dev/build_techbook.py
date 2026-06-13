"""技術書(章データ JSON)を 1 ファイル完結の HTML へ組版する。

ワークフローが書いた各章(html_body + mermaid 図 + 用語)に、開発体制章(正直な設計判断ログ)と
統合用語集を足し、索引・スタイル・オフライン Mermaid を同梱して ios/Resources/techbook.html を生成。
アプリ内 WebView と Mac ブラウザの両方で同じものが読める(完全オフライン)。

実行: .venv/bin/python dev/build_techbook.py  (mermaid.min.js は /tmp/mermaid.min.js を使用)
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = "/private/tmp/claude-501/-Users-nakazawa-pro/ea09cbac-7161-412b-81da-69bb626485bc/tasks/wvj3ugk3f.output"
MERMAID = "/tmp/mermaid.min.js"
OUT = ROOT / "ios" / "Resources" / "techbook.html"
DOCS = ROOT / "docs" / "techbook.html"

# 開発体制・設計判断ログ章(正直に。AI支援と人の判断を区別する)
DEVLOG_HTML = """
<h2>9-1. この本と、開発の進め方について(正直な記録)</h2>
<p>この章は、MathAI を「誰が・どう作ったか」を正直に書き残すためのものです。面談などで実績を語るとき、
盛らずに事実で話せるようにしておくことが、結局いちばん信頼されると考えています。</p>

<h2>9-2. 開発体制 — AI とのペアプログラミング</h2>
<p>MathAI の実装は、<strong>AI(Claude)との協働(ペアプログラミング)</strong>で進めました。
コード(Swift / Python / MLX 連携 / SwiftUI)の多くは AI 支援で書き、私(中沢)は
<strong>研究の方向づけ・技術的な意思決定・徹底した実機検証</strong>を担いました。
「全部を自力で一行ずつ書いた」わけではありません。ここを正直にしておきます。</p>

<table>
<thead><tr><th>役割</th><th>主に AI 支援</th><th>主に私(中沢)が主導</th></tr></thead>
<tbody>
<tr><td>研究テーマの設定</td><td></td><td>「クラウド無しで端末内だけでどこまで作れるか」を定義</td></tr>
<tr><td>技術的意思決定</td><td>選択肢と根拠の提示</td><td>on-device 方針 / モデル選定 / 二層設計の採用 / UX 方針の決定</td></tr>
<tr><td>実装(コード)</td><td>Swift・Python・MLX 連携・SwiftUI の記述</td><td>仕様の指示・レビュー・受け入れ判断</td></tr>
<tr><td>検証・品質</td><td>ベンチ/テストの実行</td><td>毎回 <strong>実機で確認</strong>・不具合を実使用で発見・データで採否を判断</td></tr>
<tr><td>正直さの担保</td><td></td><td>「本命/確実と言うな」「測ってから言え」を徹底</td></tr>
</tbody>
</table>

<h2>9-3. 私が一貫して効かせた強み</h2>
<ul>
<li><strong>実物主義・検証至上</strong>: 仕様書や口頭の「できました」で納得せず、必ず実機(iPad Pro M4)で動かして確かめた。リリース前に実条件で検証する姿勢。</li>
<li><strong>根本原因を追う</strong>: 「なぜ遅い?」「画像が悪いのか AI が弱いのか?」と表層で済ませず、実機の画像を取り出して比較するなどして原因まで掘った(第7章)。</li>
<li><strong>証拠で決める</strong>: 勘ではなくベンチ結果で機種・設計を選んだ(例: 認識モデルを実効ベンチの数値で 2B に決定)。</li>
<li><strong>誇張を嫌う誠実さ</strong>: できないこと(5次方程式の一般解など)を正直に書き、限界を計測して開示した。</li>
<li><strong>AI を道具として的確に方向づける力</strong>: 何を作り・何を検証し・どこで妥協するかを判断し、AI を使って難しい on-device 研究プロダクトを成立させた。</li>
</ul>

<h2>9-4. 主要な設計判断ログ(なぜそうしたか)</h2>
<p>面談で深く聞かれたとき<strong>自分の言葉で説明できる</strong>よう、要点を残します。</p>
<ol>
<li><strong>なぜ完全オンデバイスか</strong>: プライバシー(手書きを外に出さない)・オフライン動作・運用コストゼロ。研究としての挑戦価値。</li>
<li><strong>なぜ計算に Python+SymPy を「埋め込んだ」か</strong>: 検証済みの記号計算エンジンをそのまま端末で使うため。Swift で数式処理を再実装するより、信頼できる SymPy を持ち込む方が確実(第3章)。</li>
<li><strong>なぜ認識モデルを 3B → 2B にしたか</strong>: Ollama 上のベンチ(全問正解)は<strong>実機の MLX 4bit の精度を予測できなかった</strong>。実機と同条件で測り直すと 3B は誤読、Qwen2-VL 2B が満点かつ軽量 → データで採用(第2章・第7章)。</li>
<li><strong>なぜ二層(確認カード＋検算)か</strong>: AI の認識は確率的で外す。検算は「計算の正しさ」しか守れず、誤読は<strong>確認カードでしか止まらない</strong>(誤り注入実験で検算は 6% しか救えないと実測。第5章)。</li>
<li><strong>つまずきと対処</strong>: ダークモードで黒インクが白化 → ライト固定で描画。画像の正方形リサイズで認識崩壊 → アスペクト比保持。いずれも実機検証で発見・修正(第7章)。</li>
</ol>

<h2>9-5. 面談での語り方(自分用メモ)</h2>
<blockquote>
<p>「<strong>AI を道具として使いこなし、研究テーマを立て、実機で厳密に検証しながら、誰もやっていない完全オンデバイスの数学アプリを成立させた</strong>。実装は AI 支援だが、設計判断・モデル選定・信頼性の二層設計・つまずきのデバッグはすべて自分が主導し、根拠を数値で持っている。」</p>
</blockquote>
<p>— 全部自力実装と言わない。代わりに、研究判断・検証・意思決定という<strong>本物の強み</strong>と、手元にある実測データ(認識精度・端末内 2.4 秒・検算の寄与 6%/94% など)で語る。</p>
"""


def load_chapters():
    data = json.loads(Path(SRC).read_text())["result"]["chapters"]
    out = []
    for c in data:
        body = c["html_body"]
        if "&lt;" in body[:300] and "<h2" not in body[:300]:  # 二重エスケープなら戻す
            body = html.unescape(body)
        out.append({**c, "html_body": body})
    return out


def insert_diagrams(body: str, diagrams: list[str]) -> str:
    """本文中の [図: …] マーカーを Mermaid 図に順に置換。余りは末尾に。"""
    idx = {"i": 0}

    def repl(_m):
        if idx["i"] < len(diagrams):
            d = diagrams[idx["i"]]
            idx["i"] += 1
            return f'<div class="mermaid">{html.escape(d)}</div>'
        return ""
    body = re.sub(r"\[図[:：][^\]]*\]", repl, body)
    while idx["i"] < len(diagrams):  # マーカーが足りなければ末尾に追加
        body += f'<div class="mermaid">{html.escape(diagrams[idx["i"]])}</div>'
        idx["i"] += 1
    return body


def main():
    chapters = load_chapters()
    # 統合用語集(全章 + 第8章をマージし重複除去)
    terms = {}
    for c in chapters:
        for g in c.get("glossary", []):
            t = g.get("term", "").strip()
            if t and t not in terms:
                terms[t] = g.get("def", "")

    # 表示する章(用語集章は html_body の導入だけ使い、統合用語集を別途生成)
    sections = []
    toc = []
    for n, c in enumerate(chapters, 1):
        sid = f"ch{n}"
        title = c["title"]
        toc.append((sid, title))
        body = insert_diagrams(c["html_body"], c.get("mermaid", []))
        sections.append(f'<section id="{sid}"><a class="top" href="#toc">↑ 目次</a>{body}</section>')

    # 開発体制章
    toc.append(("chdev", "第9章 開発体制・設計判断ログ(正直な記録)"))
    sections.append(f'<section id="chdev"><a class="top" href="#toc">↑ 目次</a>'
                    f'<h2 class="chap">第9章 開発体制・設計判断ログ(正直な記録)</h2>{DEVLOG_HTML}</section>')

    # 統合用語集
    toc.append(("chgloss", "用語集(統合)"))
    dl = "".join(f"<dt>{html.escape(t)}</dt><dd>{html.escape(d)}</dd>" for t, d in sorted(terms.items()))
    sections.append(f'<section id="chgloss"><a class="top" href="#toc">↑ 目次</a>'
                    f'<h2 class="chap">用語集(統合 — {len(terms)} 語)</h2>'
                    f'<p>本書に出てくる専門用語をまとめました。</p><dl class="gloss">{dl}</dl></section>')

    toc_html = "".join(f'<li><a href="#{sid}">{html.escape(t)}</a></li>' for sid, t in toc)
    mermaid_js = Path(MERMAID).read_text()

    css = """
:root{--fg:#1d1d1f;--muted:#6b6b70;--bg:#fbfbfd;--card:#fff;--accent:#0a6cff;--line:#e6e6ea;--code:#f4f4f7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font-family:-apple-system,"Hiragino Sans","Hiragino Kaku Gothic ProN",system-ui,sans-serif;
 line-height:1.85;font-size:17px;-webkit-text-size-adjust:100%}
header.book{background:linear-gradient(135deg,#0a6cff,#5b8def);color:#fff;padding:40px 24px}
header.book h1{margin:0 0 6px;font-size:30px;letter-spacing:.02em}
header.book p{margin:0;opacity:.92}
main{max-width:860px;margin:0 auto;padding:0 20px 80px}
nav#toc{max-width:860px;margin:24px auto;padding:20px 24px;background:var(--card);
 border:1px solid var(--line);border-radius:16px}
nav#toc h2{margin:0 0 10px;font-size:18px}
nav#toc ol{margin:0;padding-left:1.4em} nav#toc li{margin:4px 0}
nav#toc a{color:var(--accent);text-decoration:none}
section{background:var(--card);border:1px solid var(--line);border-radius:16px;
 padding:8px 26px 28px;margin:22px 0;position:relative}
a.top{position:absolute;right:16px;top:14px;font-size:12px;color:var(--muted);text-decoration:none}
h2{font-size:23px;margin:28px 0 12px;padding-top:8px} h2.chap{border-bottom:2px solid var(--accent);padding-bottom:8px}
h3{font-size:19px;margin:22px 0 8px;color:#2b2b30}
p{margin:10px 0} ul,ol{margin:10px 0;padding-left:1.5em} li{margin:5px 0}
strong{color:#0a3a8f}
code{background:var(--code);border-radius:6px;padding:2px 6px;font-size:.9em;
 font-family:ui-monospace,"SF Mono",Menlo,monospace}
pre{background:var(--code);border-radius:12px;padding:14px 16px;overflow:auto}
pre code{background:none;padding:0}
blockquote{margin:14px 0;padding:10px 18px;border-left:4px solid var(--accent);
 background:#f2f7ff;border-radius:0 10px 10px 0;color:#243}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:15px}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
th{background:#f2f5fb}
.mermaid{background:#fff;border:1px dashed var(--line);border-radius:12px;padding:16px;margin:16px 0;text-align:center;overflow:auto}
dl.gloss dt{font-weight:700;color:#0a3a8f;margin-top:12px}
dl.gloss dd{margin:2px 0 0 0;color:#333}
"""

    doc = (
        "<!DOCTYPE html><html lang=\"ja\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>MathAI 技術書</title><style>" + css + "</style></head><body>"
        "<header class=\"book\"><h1>MathAI 技術書</h1>"
        "<p>完全オンデバイス手書き数学アプリ — 設計・実装・研究の記録</p></header>"
        "<nav id=\"toc\"><h2>目次</h2><ol>" + toc_html + "</ol></nav>"
        "<main>" + "".join(sections) + "</main>"
        "<script>" + mermaid_js + "</script>"
        "<script>mermaid.initialize({startOnLoad:true,theme:'neutral',securityLevel:'loose',"
        "flowchart:{useMaxWidth:true,htmlLabels:true}});</script>"
        "</body></html>"
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    DOCS.parent.mkdir(parents=True, exist_ok=True)
    DOCS.write_text(doc, encoding="utf-8")
    print(f"生成: {OUT} ({len(doc)//1024} KB) / 章 {len(toc)} / 用語 {len(terms)}")


if __name__ == "__main__":
    main()
