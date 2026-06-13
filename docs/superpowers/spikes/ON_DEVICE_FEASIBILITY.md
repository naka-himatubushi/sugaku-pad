# オンデバイス（iPad 内推論）実現性 調査

- 日付: 2026-06-13
- 問い: 手書き OCR の vision LLM を **iPad の中で**動かせるか（最終目標＝オンデバイス）

## 結論: ✅ 実現可能（MLX Swift 経由）

- **MLX Swift は iOS/iPadOS で VLM を実行できる**。公式 [mlx-swift-examples](https://github.com/ml-explore/mlx-swift-examples) の **MLXChatExample** が「iOS と macOS で LLM/VLM 対応」と明記し、**`qwen2.5VL:3b` プリセット**を登録（`VLMRegistry.qwen2_5VL3BInstruct4Bit`）。
- VLM 実装が豊富（`MLXVLM/Models`）: **Qwen25VL / Qwen3VL / GlmOcr(OCR特化) / FastVLM / Gemma3 / SmolVLM2** 等 → 端末内 OCR の選択肢が複数ある。
- **Core AI より現実的**: Core AI は iOS27 必須＋OCR向けVLM未提供だったが、**MLX Swift は今の iOS で動き、Qwen2.5-VL 実装がある**。

## モデル footprint + 精度（実測 2026-06-13）

3 候補を実手書き 5 問で横並び比較（詳細 = [OCR_BENCHMARK.md](OCR_BENCHMARK.md)）。

| モデル | params | 実体(Q4) | 手書き精度 | warm | 必要 iPad |
|---|---|---|---|---|---|
| **Qwen2.5-VL 3B** | 3.8B | **3.2GB** | 5/5 | **0.23s** | 8GB でも可（公式 iOS 例もこれ） |
| Gemma 4 E2B | 5.1B | 7.2GB | 5/5 | 2.98s | 16GB 推奨（PLE 活用なら 8GB 余地） |
| Qwen2.5-VL 7B | 7B | 6.0GB(Ollama)/5.3GB(MLX) | 5/5 | 0.26s | 16GB（Pro 系） |

→ **推奨 on-device モデル = Qwen2.5-VL 3B 4bit**：精度は 3 種とも 5/5 で並ぶ中、**最小・最速**で 8GB iPad に最も無理なく載る（公式 iOS 例と同一）。Gemma 4 E2B は精度同等だが Ollama 実測で約 13 倍遅く実体も倍以上 → 16GB 機の精度マージン用に保留。16GB 機なら 7B で精度↑も選択可。

## 実装パス

1. `ios/` アプリに MLX Swift（MLXVLM）を SwiftPM 追加
2. `VLMRegistry.qwen2_5VL3BInstruct4Bit` をロード（初回 HF からDL or 同梱）
3. 手書き画像 → on-device 推論 → LaTeX → 既存の確認カード／mathai 検算へ
4. 参考実装: **MLXChatExample**（そのまま土台にできる）。Xcode 導入済みで着手可。

## 残課題・リスク（正直に）

- **iPad の RAM** 次第で 3B/7B が決まる（要確認）。8GB なら 3B 一択。
- ✅ **3B の認識精度は Mac で検証済（実手書き 5/5、7B と同等）** → 落ちる懸念は払拭。確認カード＋検算で残差は吸収。
- 速度: 上記は Mac（Ollama warm）の数値。**iPad GPU 上の実測はまだ**（MLX Swift 統合後に要計測）。
- VLM on iOS は最先端領域（実例はあるが本番化は native 実装の工数がかかる）。

## 次の一手

1. iPad RAM 確認（3B 既定 / 16GB なら 7B も可）
2. ✅ **Mac で Qwen2.5-VL 3B / Gemma 4 E2B を手書きベンチ済**（[OCR_BENCHMARK.md](OCR_BENCHMARK.md)、3B が最小・最速・5/5 で第一候補）
3. ✅ **ネイティブ統合コード完成・iOS ビルド成功**（`ios/Spikes/MlxOcrBenchView.swift`、`Spike D: MLX ベンチ`）。MLXVLM で `VLMRegistry.qwen2_5VL3BInstruct4Bit` をロードし、ロード時間/cold・warm latency/tokens-s/phys_footprint/残メモリを画面計測。パッケージは `mlx-swift-examples 2.29.1` にピン。
4. ⏳ **iPad 実機で速度・RAM 実測**（中沢さんの手作業: [MLX_ONDEVICE_RUNBOOK.md](MLX_ONDEVICE_RUNBOOK.md) の手順で接続→署名→Run→「ベンチ開始」）。シミュレータでは on-device の数字は取れない。
