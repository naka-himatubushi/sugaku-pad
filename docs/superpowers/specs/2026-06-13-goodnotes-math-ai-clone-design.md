# Goodnotes AI for Math クローン — 設計ドキュメント

- 日付: 2026-06-13
- ステータス: 設計承認済み（spec レビュー待ち）
- プロジェクト場所: `~/sandbox/math-ai-ipad/`
- 元アプリ: [Goodnotes AI for Math](https://support.goodnotes.com/hc/en-us/articles/13683534670223-Goodnotes-AI-for-Math) / [技術ブログ](https://www.goodnotes.com/blog/math-ai-that-builds-understanding)

---

## 0. このドキュメントの位置づけ

Goodnotes AI for Math を**スクラッチから・完全 on-device のネイティブ iPad アプリ**として作り直す。
本 spec は全体ではなく **「Solve モードの縦割り1スライス」+ その前提となる技術検証スパイク** を対象とする。Teach Me・グラフ・ノート管理などは後続スライスで別 spec とする。

---

## 1. 背景と目的

### 元アプリの中核機能（コピー対象）
- 手書き数式を**投げ縄（lasso）選択**して認識する
- 認識結果を**確認カード**で見せ、計算前に誤認識を修正できる
- **Solve**（全ステップ提示）と **Teach Me**（概念先行のガイド学習）の2モード
- 計算は本家では Wolfram|Alpha、会話・説明は LLM、という分業

### 本クローンの方針（筆者の選択）
- **新規スクラッチ**（既存 `~/sandbox/math-ocr-mvp/` のコードは流用しない。知見のみ参照）
- **ネイティブ iPad アプリ**（SwiftUI / PencilKit）
- **Solve モードを最初に**作る
- **完全 on-device**（クラウド・Mac backend・tailnet に依存しない＝外出先でも動く）
- 計算エンジンは固定せず、**実機ベンチで「ローカルLLM単体で足りるか／SymPy は必要か」を見極める**
- 配布: **無料 Apple ID で実機**（7日署名、再ビルド前提）

### 制約・前提
- iPad 本体では大型 LLM（qwen3.6:35b / gemma 26B 等）は動かない。よって「ローカル LLM」は**端末内の小型モデル**（Apple Foundation Models / 小型 MLX）を指す。
- Apple Foundation Models は **iOS 26 / Apple Intelligence 対応 iPad** が前提（Spike C で確認）。

---

## 2. スコープ

### 含む（最初のスライス）
手書き → 投げ縄選択 → 認識(手書き→LaTeX) → 確認カード → Solve → ステップ表示 の一気通貫。
初期の数学範囲: **基本代数（一次方程式・二次方程式・因数分解）＋ PreCalc 三角（Unit 6.4〜7.6）**。

### 含まない（後続スライス・別 spec）
- Teach Me モード
- グラフ描画
- ノート/ドキュメント管理・複数ページ・テンプレート
- クラウド同期
- 数学範囲の拡張（微積分など）

---

## 3. アーキテクチャ（全て端末内・ネイティブ）

```
[Apple Pencil 手書き]
      │ strokes
      ▼
 ┌──────────┐   image   ┌──────────────┐  {latex,conf}  ┌──────────────────┐
 │ Canvas/  │ ───────▶ │ Recognition   │ ───────────▶ │ ConfirmationCard │
 │Selection │           │ (端末内OCR)   │              │  (確認・手修正)  │
 └──────────┘           └──────────────┘              └────────┬─────────┘
                                                                │ latex(確定)
                                                                ▼
                                                       ┌──────────────┐ steps ┌─────────────┐
                                                       │ SolveEngine   │──────▶│ Explanation │
                                                       │ (SymPy/端末)  │       │ (FM/端末LLM)│
                                                       └──────────────┘       └──────┬──────┘
                                                                                      ▼
                                                                              ┌─────────────┐
                                                                              │ Render      │
                                                                              │ (iosMath)   │
                                                                              └─────────────┘
```

### 技術選定
| 層 | 技術 | 補足 |
|---|---|---|
| UI | SwiftUI | |
| 手書き/選択 | PencilKit（`PKCanvasView`, 投げ縄選択） | ストローク管理 |
| 認識(OCR) | 端末内 LaTeX-OCR モデル（候補: `LaTeX-OCR(pix2tex)` 系を CoreML か MLX-Swift に変換） | Spike A で確定 |
| 計算 | 埋め込み Python（`Python-Apple-support`）+ **SymPy** | 決定的にステップ生成 |
| 説明 | Apple Foundation Models（端末内 LLM, iOS26） | 自然言語の解説。非対応端末はテンプレ fallback |
| 数式描画 | iosMath / SwiftMath | LaTeX → 数式表示 |
| 保存 | SwiftData かローカルファイル | 単一スライスでは最小限 |

---

## 4. コンポーネント分割（各単一責務・独立テスト可能）

| モジュール | 責務 | インターフェース（概念） | 依存 |
|---|---|---|---|
| `Canvas` | Pencil 入力・ストローク管理 | strokes を提供 | PencilKit |
| `Selection` | 投げ縄で範囲確定→画像化 | `select() -> Image` | Canvas |
| `Recognition` | 画像→LaTeX | `recognize(Image) -> {latex, confidence}` | 端末内OCRモデル |
| `SolveEngine` | LaTeX→解答ステップ | `solve(latex) -> {steps[], answer}` | SymPy |
| `Explanation` | ステップ→自然言語 | `explain(steps) -> text` | Foundation Models |
| `Render` | LaTeX→数式描画 | `render(latex) -> View` | iosMath |
| `ConfirmationCard` | 認識結果の確認/修正 UI | — | Render |

**設計上の要点**: `Recognition` と `SolveEngine` を疎結合（LaTeX 文字列で接続）にしておくことで、計算エンジンを後から差し替え（SymPy ↔ 端末内LLM ↔ ハイブリッド）でき、エンジン見極めの実験がそのまま回せる。

---

## 5. データフロー

1. ユーザーが Apple Pencil で数式を手書き（`Canvas`）
2. 投げ縄で対象を囲む → 選択範囲を画像化（`Selection`）
3. 画像を端末内 OCR にかけ LaTeX + 信頼度を得る（`Recognition`）
4. 確認カードに数式を描画。低信頼度なら強調し、ユーザーが手修正可能（`ConfirmationCard`）
5. 確定 LaTeX を SymPy で解き、ステップと最終解を得る（`SolveEngine`）
6. ステップを自然言語で解説（`Explanation`）
7. ステップ＋解説を数式描画で表示（`Render`）

---

## 6. エラー処理

| 事象 | 振る舞い |
|---|---|
| 認識信頼度が低い | 確認カードで該当箇所を強調し、手動修正を促す |
| SymPy が解けない式 | 「対応範囲外」を明示（曖昧な答えを返さない） |
| Foundation Models 非対応端末 | 説明は決定的なテンプレ文に fallback（計算自体は SymPy で継続） |
| OCR モデルのロード失敗 | エラー表示し、記号パレット等の手入力に退避（Spike A 結果次第） |

---

## 7. 先行スパイク（本実装の前に必須）

完全 on-device（方式 C）は 4 方式中もっとも技術リスクが高い。本実装前に成立可否をデータで確認する。

- **Spike A — 端末内 LaTeX-OCR の精度**
  - 内容: `LaTeX-OCR(pix2tex)` 系を CoreML/MLX-Swift に変換し、**実機 Pencil 入力**で LaTeX 正答率を測定
  - 合否基準: 実 Pencil 入力で LaTeX 正答率 **80% 以上**（暫定閾値）
  - 不合格時: 認識 UX を「修正前提」または記号パレット併用へ設計変更

- **Spike B — 端末内 計算（エンジン見極め）**
  - 内容: ① iOS に SymPy を埋め込めるか（ビルド成立）②Foundation Models **単体**で代表問題を解けるか vs ③SymPy+FM説明、を代表問題セットで正答率比較
  - 目的: 「ローカルLLM単体で足りるか／SymPy は必須か」を**データで**結論づける
  - 既存知見: `math-ocr-mvp` で gemma4 vision OCR は動作したが「JSON 出力が不安定」だった（端末外モデルでの参考値）

- **Spike C — Foundation Models 可用性**
  - 内容: 手持ち iPad が Apple Intelligence（iOS26 / Foundation Models）対応か確認
  - 不合格時: 小型 MLX モデル、またはテンプレ説明に fallback

**ゲート**: Spike A/B/C のいずれかが基準未達なら、方式・スコープを見直してから本実装に進む。

---

## 8. テスト戦略

| 対象 | 方法 |
|---|---|
| `SolveEngine` | 決定的なのでユニットテスト（既知の式→既知のステップ/解） |
| `Recognition` | 固定画像セットでの回帰テスト（正答率を追跡） |
| UI（Canvas/確認/表示） | 実機での手動確認（Pencil 入力はシミュレータ不可） |

---

## 9. 配布・運用

- 無料 Apple ID で実機にサイドロード（署名は 7 日で失効 → 再ビルド前提）
- 完全 on-device のため、外出先・オフラインでも動作する

---

## 10. 正直なリスクと失敗条件

- **最大の不確実性は端末内 手書き数式 OCR の精度**。失敗条件: 実 Pencil 入力で LaTeX 正答率が実用閾値（暫定80%）未満 → 認識 UX を設計変更。
- iOS への **SymPy 埋め込みはビルドが重く**、初回の環境構築に時間がかかる可能性。
- Foundation Models は **対応 iPad / iOS26 前提**。非対応なら fallback。
- ネイティブ Swift は Python 中心の既存ワークフロー／ローカル LLM 自走と相性が変わり、実装支援の進め方を調整する必要がある。

---

## 11. 未確定事項（spec レビューで詰める）

- プロジェクト名（仮: `math-ai-ipad`）
- OCR モデルの最終候補（Spike A で確定）
- 初期問題セットの具体的な内容と件数
- LaTeX 正答率の実用閾値（暫定80%）の妥当性
