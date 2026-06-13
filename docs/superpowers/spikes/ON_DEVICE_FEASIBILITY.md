# オンデバイス（iPad 内推論）実現性 調査

- 日付: 2026-06-13
- 問い: 手書き OCR の vision LLM を **iPad の中で**動かせるか（最終目標＝オンデバイス）

## 結論: ✅ 実現可能（MLX Swift 経由）

- **MLX Swift は iOS/iPadOS で VLM を実行できる**。公式 [mlx-swift-examples](https://github.com/ml-explore/mlx-swift-examples) の **MLXChatExample** が「iOS と macOS で LLM/VLM 対応」と明記し、**`qwen2.5VL:3b` プリセット**を登録（`VLMRegistry.qwen2_5VL3BInstruct4Bit`）。
- VLM 実装が豊富（`MLXVLM/Models`）: **Qwen25VL / Qwen3VL / GlmOcr(OCR特化) / FastVLM / Gemma3 / SmolVLM2** 等 → 端末内 OCR の選択肢が複数ある。
- **Core AI より現実的**: Core AI は iOS27 必須＋OCR向けVLM未提供だったが、**MLX Swift は今の iOS で動き、Qwen2.5-VL 実装がある**。

## モデル footprint（実測 + 見積り）

| モデル | サイズ(4bit) | 必要 iPad |
|---|---|---|
| Qwen2.5-VL **7B** | **5.3GB**（実測） | 16GB（Pro 系） |
| Qwen2.5-VL **3B** | 約 2–2.5GB | 8GB でも可（公式 iOS 例もこれ） |

→ **推奨 on-device モデル = Qwen2.5-VL 3B 4bit**（多くの iPad で動く・公式例と同一）。16GB 機なら 7B で精度↑も選択可。

## 実装パス

1. `ios/` アプリに MLX Swift（MLXVLM）を SwiftPM 追加
2. `VLMRegistry.qwen2_5VL3BInstruct4Bit` をロード（初回 HF からDL or 同梱）
3. 手書き画像 → on-device 推論 → LaTeX → 既存の確認カード／mathai 検算へ
4. 参考実装: **MLXChatExample**（そのまま土台にできる）。Xcode 導入済みで着手可。

## 残課題・リスク（正直に）

- **iPad の RAM** 次第で 3B/7B が決まる（要確認）。
- **3B の認識精度**は 7B（実手書き 5/5）より落ちる可能性 → **端末搭載前に Mac で 3B をベンチ**して見極めるべき。確認カード＋検算で残差は吸収。
- 速度: iPad GPU は MacBook(7B warm 0.29s) より遅い見込み → 3B で実測要。
- VLM on iOS は最先端領域（実例はあるが本番化は native 実装の工数がかかる）。

## 次の一手

1. iPad RAM 確認（3B 既定 / 16GB なら 7B も可）
2. **Mac で Qwen2.5-VL 3B を手書きベンチ**（端末搭載前の精度見極め）
3. ネイティブ統合（MLXChatExample を土台に）
