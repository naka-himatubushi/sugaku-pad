# sugaku-pad — 完全オンデバイスの手書き数学ノート

<p align="center">
  <img src="assets/demo/demo.gif" alt="sugaku-pad デモ（再現アニメ）" width="760">
</p>

<p align="center"><sub>⚠️ 上の動画は<b>再現アニメ</b>です（手書き入力と求解結果は実データ／UI 表示はイメージ）。実機録画は別途差し替え予定。</sub></p>

> iPad に手書きした数式を、**クラウドに一切送らず端末の中だけで**「読んで・解いて・検算する」ノートアプリ。
> **読む**＝ローカル Vision LLM（MLX / Qwen2-VL 2B）、**解く**＝端末内の Python + SymPy。**通信ゼロ・データは端末の外に出ない。**

個人の**研究・学習プロジェクト**。テーマは **「ローカル限定の LLM で、手書き数学はどこまでいけるか — 完全オンデバイスで」**。

---

## なぜ作ったか（既存サービスとの違い）

手書き数学アプリ自体は珍しくない。差別化は機能ではなく **「どこで動かすか」** にある——**クラウドに依存せず、iPad 単体・ローカル LLM だけで完結**させた点。

| | クラウド型の既存サービス | **sugaku-pad** |
|---|---|---|
| 認識（読む） | サーバへ送信 | **端末内のローカル VLM（MLX Qwen2-VL 2B）** |
| 求解（解く） | サーバ / API | **端末内の CPython + SymPy** |
| 通信 | ネット必須 | **通信ゼロ・機内モードでも動く** |
| データ | 外部サーバへ送信 | **端末の外に一切出ない（完全プライベート）** |
| コスト | API / サブスク | **API 課金ゼロ** |
| 答えの正しさ | ブラックボックス | **SymPy が解を代入して決定論的に検算（verified）** |

---

## 仕組み（2 本柱 ＋ 二層の信頼性）

設計の肝は **「確率的なローカル LLM 認識」と「決定的な SymPy 計算」を、人の確認カードと検算で橋渡しする二層構造**。

```mermaid
flowchart LR
    A["✍️ 手書き入力<br/>PencilKit（iPad）"] --> B
    B["① 認識（確率的）<br/>ローカル Vision LLM<br/>MLX・Qwen2-VL 2B（端末内）"] --> C
    C["② 確認カード<br/>人がワンタップ修正"] --> D
    D["③ 計算＋検算（決定的）<br/>端末内 SymPy / mathai<br/>解を代入して検証 ✓"] --> E
    E["④ 表示<br/>SwiftMath 数式カード"]

    classDef prob fill:#fff3e0,stroke:#e8a33d,color:#000;
    classDef human fill:#f3f0ff,stroke:#8a6dde,color:#000;
    classDef det fill:#e8f0fe,stroke:#5b8def,color:#000;
    class B prob; class C human; class D det;
```

- **① 認識（確率的）**: ローカル Vision LLM が手書き→LaTeX。完璧でない前提に立つ。
- **② 確認（人）**: 誤認識をワンタップ修正＝“最後の数%”の保険。
- **③ 計算＋検算（決定的）**: SymPy で求解し、**答えを元の式に代入して検証**（`verified`）。間違いは弾ける。

### 計算コア `mathai` の中身

`=` の有無で方程式/式に分け、種別ごとに SymPy で解いて **検算**する。

```mermaid
flowchart TD
    IN["LaTeX 入力<br/>(OCR出力 / テキスト)"] --> NORM["LaTeX入力層<br/>暗黙の掛け算・frac/sqrt/三角<br/>不等号・cases・デリミタ除去"]
    NORM --> RT{"入力の形"}
    RT -->|"複数式<br/>; / 改行 / cases"| SYS["連立<br/>solve→代入で検算"]
    RT -->|"不等号<br/>&lt; &gt; ≤ ≥"| INQ["不等式(一次/二次)<br/>solveset(実数)→点サンプルで検算"]
    RT -->|"単一の等式/式"| Q{"= がある?"}
    Q -->|"あり（方程式）"| EQ{"種別"}
    EQ -->|"1次"| L["線形<br/>移項→両辺を割る"]
    EQ -->|"2次"| QD["二次<br/>有理数解→因数分解 / それ以外→解の公式＋判別式"]
    EQ -->|"三角を含む"| TR["三角<br/>三角方程式として解く"]
    Q -->|"なし（式）"| EX{"形は?"}
    EX -->|"数値"| NU["評価<br/>nsimplify"]
    EX -->|"多項式(2次↑)"| PO["因数分解+=0の根"]
    EX -->|"その他"| SI["簡約<br/>simplify"]
    SYS --> SOL["解 / 結果"]
    INQ --> SOL
    L --> SOL
    QD --> SOL
    TR --> SOL
    NU --> SOL
    PO --> SOL
    SI --> SOL
    SOL --> VF["検算レイヤー<br/>代入 / サンプル点で<br/>SymPy が成立を確認"]
    VF --> OUT(["出力: steps_latex /<br/>answer_latex / verified ✓"])
    classDef det fill:#e8f0fe,stroke:#5b8def,color:#000;
    classDef verify fill:#e3f6e8,stroke:#1aa64b,color:#000;
    class NORM,L,QD,TR,NU,PO,SI,SOL det;
    class VF,OUT verify;
```

---

## 開発背景・設計判断（研究ログ）

「完全オンデバイス」を成立させるために、自分で検証して決めたこと。

- **オンデバイスでモデルを選定（証拠ベース）** — 実機 MLX ベンチで Qwen2-VL **2B / 3B / 7B** を比較。意外にも **3B-4bit は実機で誤読が多く、2B-4bit の方が安定**（精度・RAM ~1.5GB・冷えロードの速さ）。8GB iPad では **2B を採用**（7B は 16GB 機向け）。印刷数式 OCR（pix2tex）は手書きで破綻することも実測。→ [`docs/superpowers/spikes/OCR_BENCHMARK.md`](docs/superpowers/spikes/OCR_BENCHMARK.md)
- **求解は Python 埋め込みで（Swift 再実装ではなく）** — 記号計算は SymPy が圧倒的に堅い。書き直すより **CPython を端末に埋め込み `mathai`/SymPy をそのまま動かす**判断。→ [`docs/superpowers/spikes/ONDEVICE_PYTHON.md`](docs/superpowers/spikes/ONDEVICE_PYTHON.md)
- **信頼性を定量化** — OCR 誤りを安全網がどれだけ止めるか測定。**検算が止めたのは 6%、残り 94% は「確認カード（人の目）」頼み**だった（誤読された式も“その式としては正しく解ける”ため検算を通る）。→ 二層が別目的で必要だと数値で確定。※ 16 問・単一文字の模擬誤り 141 件という**小規模ベンチ**で、実 OCR 誤り分布での再測は今後。→ [`docs/superpowers/spikes/RELIABILITY.md`](docs/superpowers/spikes/RELIABILITY.md)
- **つまずき & デバッグ（実機が教えた罠）** — ①ダークモードで PencilKit の黒インクが白画像化し OCR が破綻 → ライトトレイトで描画して解決。②正方形 1024 リサイズで横長の式が潰れて精度劣化 → アスペクト比保持に。③OCR が桁の間に空白を入れる → 桁間だけ詰める。
- **端末内 AI フレームワークの調査** — Apple Core AI を調べ、現状要件では手書き OCR に不適と判断 → **MLX Swift** を採用。→ [`docs/superpowers/spikes/COREAI_SPIKE.md`](docs/superpowers/spikes/COREAI_SPIKE.md)

> より詳しい技術解説は **アプリ内技術書**（[`docs/techbook.html`](docs/techbook.html)）。低レベル（MLX とは）から Python 埋め込みの決断、設計判断ログまで。

---

## 技術スタック

- **UI**: SwiftUI / PencilKit（手書き）/ SwiftMath（数式描画）
- **読む**: MLX Swift（mlx-swift-examples）＋ Qwen2-VL 2B 4bit
- **解く**: 端末内 CPython（Python-Apple-support 3.13）＋ SymPy（`mathai/`）

## 構成

| ディレクトリ | 役割 |
|---|---|
| `ios/` | **ネイティブ iPad アプリ**（SwiftUI + PencilKit）。端末内 MLX 推論 ＋ 埋め込み Python |
| `mathai/` | **計算コア**（LaTeX 入力層 + SymPy SolveEngine）。テスト付き |
| `spikes/` | OCR・計算エンジンの検証スクリプト（モデル比較／信頼性注入 等） |
| `docs/` | 設計・実装計画・検証結果・技術書 |
| `web/` ・ `webapp/` | 前身の Web 版（FastAPI + Canvas）。ネイティブ版の足場 |

## ステータス

- ✅ **iPad 実機（M4）で** 手書き → オンデバイス OCR（MLX Qwen2-VL 2B）→ 確認 → 端末内 SymPy 求解 → 検算 が動作確認済み
- ✅ 計算コア `mathai` テスト PASS（一次/二次/不等式/連立・検算付き）
- 🔬 ローカル LLM のオンデバイス実機ベンチ・信頼性の定量化を実施（`docs/`）

## 正直な限界

- オンデバイス VLM の認識は完璧ではない（だから確認カードで人が直す設計）。
- 信頼性ベンチは小規模（16 問・模擬誤り）。実 OCR 誤り分布での再測は今後。
- README 冒頭のデモは**再現アニメ**で代用中（実機録画への差し替え予定）。
