# MLX 端末内 OCR ベンチ — 実機 iPad 実行手順

- 日付: 2026-06-13
- 目的: `Spike D: MLX ベンチ` を **実機 iPad** で動かし、速度（ロード/cold/warm latency, tokens/s）と **RAM(phys_footprint)** を実測する
- 前提: Xcode 26.5 インストール済み、無料 Apple ID 署名、iPad（Apple Silicon, 8–16GB）

## なぜ実機が要るか（正直に）

- **シミュレータでは on-device の数字は取れない**。MLX は Metal GPU を使い、メモリ上限(jetsam)も実機固有。シミュレータは Mac の CPU/GPU・メモリを借りるので、iPad の速度・RAM の代理にならない。
- このリポジトリの CLI ビルドは**コンパイル検証用**（API が通るかの確認）。**数字は実機のみ**。

## 中沢さんの手作業（ここだけ手が要る）

1. **iPad を MacBook に有線接続**（または Xcode で Wi-Fi ペアリング）。iPad 側で「このコンピュータを信頼」。
2. Finder/Xcode の `Devices` に iPad が出るのを確認。
3. プロジェクトを Xcode で開く: `open MathAI.xcodeproj`
   - ※ `sudo xcode-select` は不要。Xcode.app の GUI 実行は xcode-select 設定に依存しない。
4. ターゲット `MathAI` → `Signing & Capabilities`:
   - `Automatically manage signing` ON
   - `Team` = 自分の Apple ID（無料）。`Add an Account…` から未登録なら追加。
5. 上部のビルド先（destination）を**接続した iPad** に切替。
6. ⌘R で実行。**初回はビルド後、iPad 側で開発者証明書の信頼が必要**:
   - iPad: 設定 → 一般 → VPN とデバイス管理 → デベロッパApp → 自分の Apple ID を「信頼」。
7. アプリ起動 → 右上 **「検証」→「Spike D: MLX ベンチ」** → **「ベンチ開始（3回）」**。
   - **初回のみ** Qwen2.5-VL 3B(4bit) を HuggingFace から **~3.2GB DL**（Wi-Fi 推奨、数分）。2回目以降はキャッシュ。
8. 画面に出る数字を読み取る:
   - モデルロード秒 / cold latency / warm latency(平均) / 生成 tokens/s
   - RAM(ロード後) / RAM(ピーク) / 残メモリ余裕（= jetsam まで）

## 比較の見方

- Mac(Ollama warm) の実測は **3B=0.23s**（[OCR_BENCHMARK.md](OCR_BENCHMARK.md)）。iPad GPU はこれより遅い見込み → **実機 warm が体感に耐えるか**が判断軸。
- RAM(ピーク) が **残メモリ余裕**を食い潰していないか（8GB 機が要注意）。`os_proc_available_memory` が小さくなりすぎると iOS にアプリを殺される。

## 既知のリスク（測る前に明示）

- **無料署名のメモリ上限**: `Increased Memory Limit` entitlement は無料署名では付けにくい。8GB iPad で 3B がロードできず落ちる可能性 → その場合は 16GB 機 or より小さいモデル(SmolVLM/Qwen2-VL 2B)で再測。
- **無料署名アプリは 7 日で失効** → 再ビルドで延長。
- **初回 DL ~3.2GB**: ストレージとギガに注意。
- mlx-swift / mlx-swift-examples は更新が速い → 本リポジトリは **mlx-swift-examples 2.29.1 にピン**（MLXVLM を含む最後系。main は別リポジトリへ分離済み）。

## 数字が取れたら

- `OCR_BENCHMARK.md` / `ON_DEVICE_FEASIBILITY.md` に **iPad 実機の速度・RAM** を追記し、Mac 実測と並べる。
- warm が実用域なら、次は **Canvas 手書き → MLX OCR → 確認カード → 検算** のフル統合（現状は Spike 単体）。
