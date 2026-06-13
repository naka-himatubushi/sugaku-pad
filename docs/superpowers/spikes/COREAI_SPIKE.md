# Apple Core AI 端末内化スパイク 結果

- 日付: 2026-06-13
- 目的: 手書き数式 OCR を Mac の Ollama から **Core AI で iPad 端末内**に移せるか検証
- 調査対象: [Core AI](https://developer.apple.com/core-ai/) / [apple/coreai-models](https://github.com/apple/coreai-models)

## 結論（証拠ベース）

**現状では「Core AI で端末内 手書き OCR」は実現できない。** 2 つの壁:

1. ⚠️ **ツールチェーン要件**: Core AI の実行・アプリ統合は **macOS / iOS 27.0+ ＋ Xcode 27.0+**（WWDC26 系）が必須。
   - 本機は **macOS 26.5 / Xcode 26.5**（GA）→ Core AI を**ビルド・実行できない**。27 系（ベータ）への更新が前提。
2. ⚠️ **手書き OCR 用のモデルが無い**: `apple/coreai-models` のカタログは
   - テキスト LLM: gemma3（**iOS: No**・macOS のみ）, qwen3, mistral, mixtral, gpt_oss, t5 …
   - 視覚/その他: clip（埋め込み）, yolo（検出）, sam3/efficient-sam（領域）, depth-anything, stable-diffusion/flux2（生成）, whisper（音声）
   - → **画像→数式LaTeX を生成する VLM（OCR向け）は提供されていない**。gemma3 の実行例もテキスト専用（`CoreAILanguageModel` + `LanguageModelSession.respond`）。
   - 自前で qwen2.5-VL 等を experimental エクスポートする道はあるが、重く・27 必須・不確実。

## Core AI の現状の強み（分かったこと）

- 端末内 **テキスト LLM**（HF モデルを `.aimodel` へエクスポート、iOS は 4bit palettization 量子化）。`uv run coreai.llm.export ...` で変換、Swift は FoundationModels 経由で `respond`。
- 画像系は分類/検出/領域/生成/深度が中心で、**生成的 OCR(VLM) は弱い/未提供**。

## 推奨（この project の進め方）

- **OCR は当面ローカル Ollama(qwen2.5-VL) を維持**（実用・高速・手書きに強いと実測済み）。
- **Core AI は将来 R&D**:
  - 27 系が GA したら再評価。
  - まず Core AI を使うなら用途は **OCR ではなく「解説/Teach Me のテキスト LLM 端末内化」**（gemma3/qwen3 をエクスポート）が現実的。
  - 端末内 OCR を Core AI でやるなら qwen-VL 等の custom VLM export を要研究（27＋experimental）。

## 面談での語り方（技術判断の実例）

「最新の Core AI を調査 → 端末内 OCR には(a)27 系要件 (b)ビジョン OCR モデル未提供 という壁を特定。よって OCR はローカル LLM 継続、Core AI は解説 LLM の端末内化候補と位置づけた」= 流行に飛びつかず**証拠で意思決定した**例。
