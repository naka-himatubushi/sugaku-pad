# スパイク結果（途中経過）

最終更新: 2026-06-13
関連: `docs/superpowers/plans/2026-06-13-on-device-feasibility-spikes.md`

進行中。Mac 上で自律検証できる部分を先行実施。実機（iPad + Xcode）が要る部分は筆者待ち。

---

## Spike A — 端末内 LaTeX-OCR（Mac ベースライン: 実施済 / 実機: 未）

- ツール: `pix2tex`（LaTeX-OCR, 重み 97MB）, 評価ハーネス `spikes/ocr/eval_pix2tex.py`
- データ: 印刷体レンダリング 12 問（代数+三角）。`spikes/ocr/gen_synthetic.py` で生成
- 結果（**印刷体**・意味ベース正規化後）:
  - exact-match = **58.3% (7/12)**
  - char-level similarity 平均 = **87.9%**
- 誤読の傾向: 関数語 "sin" の誤認識（複数）、単独文字（a→Ω）、入れ子分数（tan=sin/cos）の文字化け
- 注意: 合成画像は matplotlib フォントで pix2tex の学習元（実 LaTeX）と分布差あり。誤読の一部はその差由来の可能性。
- **end-to-end 求解一致（OCR出力→latex_input→SolveEngine）= 6/7 (85.7%)**（`spikes/ocr/eval_solve_from_predictions.py`）
  - exact-match 58% に対し end-to-end 86% → **latex_input 層が OCR の表記揺れ（2X/x^{2}/\\frac/\\,）を吸収**。失敗は x→π の本物の誤読 1 件のみ
- **暫定示唆**: 文字列一致が低くても「解ければよい」観点では印刷体で 86%。**確認カード（人が修正してから解く）UX があれば実用域に届きうる**。実機手書きの実測が本ゲート。
- **CoreML 変換 probe（Mac, Xcode 不要）= ✅ エンコーダ変換成功**（`spikes/ocr/try_coreml.py`）
  - `torch.jit.trace`→coremltools は失敗（動的パディングで `TypeError`）
  - **`torch.export` + `run_decompositions({})` → coremltools で pix2tex エンコーダの Core ML 変換に成功**。`pix2tex_encoder.mlpackage`(25MB) をロード&推論 OK、出力 `(1,505,256)` の画像特徴を生成
  - **Spike A の結論（更新）**: 端末内 OCR の最難関 ViT エンコーダは Core ML 化可能と実証。**残課題は自己回帰デコーダ**（x_transformers のループ）→ (a) デコーダも変換 (b) エンコーダ特徴を使い Swift で decode ループ実装、のいずれか。手書きOCRが整うまでは手入力＋確認カードで Solve 成立可能
- **未（実機ゲート）**: デコーダ処理の実装 → 実 Pencil 手書きでの正答率測定
- ⚠️ **venv 破損→再構築済**: python@3.13 削除で壊れた venv を python@3.12 で再作成（pix2tex+coremltools9.0+torch2.12）。旧 `brew install`(mas/xcodegen) の cleanup が python@3.13 を削除 → `.venv`(torch/pix2tex) 死亡。**ライブ OCR 再実行には venv 再構築が必要**（`brew install python@3.13` → venv → `pip install pix2tex`）。end-to-end 評価は captured_predictions.json で torch 無しに再現可能

## Spike B — 端末内 計算（コア実装: 実施済 / 埋め込み・FM比較: 未）

- **`mathai/` パッケージ**（アプリ本体の計算コア、純 SymPy・端末内埋め込み前提）：**テスト 20件 PASS**
  - `mathai/solver.py`（SolveEngine）: 線形・二次（因数分解手順）・式評価・三角（評価/恒等式/方程式分類）・非対応判定。暗黙乗算で "2x+3=7" も解釈
  - `mathai/latex_input.py`（LaTeX入力層）: OCR 出力 LaTeX → SymPy 数式へ変換（\\frac/\\sqrt/^{}/三角/暗黙乗算/大文字小文字）
  - `solve_latex()` で OCR→求解を一気通貫
- `spikes/compute/eval_fm_vs_sympy.py`：SymPy 正解生成 OK。FM 回答記入→採点の枠組み完成
- **未（実機ゲート）**: ① iOS への Python+SymPy 埋め込み（Python-Apple-support）成否 ② 実機 FM 単体の正答率測定（`fm_answers.json` 記入→`score`）

## Spike C — Foundation Models 可用性（未: 実機必須）

- **未**: 手持ち iPad が iOS26 / Apple Intelligence 対応か、`SystemLanguageModel.availability` を実機で確認

---

## 筆者側の必須アクション（自律不可）

1. **Xcode を App Store からインストール**（現状 Command Line Tools のみ。Swift/iOS は一切ビルド不可）
2. 実機 iPad を用意し、無料 Apple ID で署名・信頼設定
3. 実機での手書きデータ収集（Spike A 本ゲート）、FM 動作確認（Spike C）

## 総合判定

**保留**（Mac 側の頭脳検証は前進。実機ゲート A/B/C 完了後に GO/条件付きGO/NO-GO を確定する）
