# MathAI — Goodnotes AI for Math クローン（簡易版）

手書き数式を認識して解く、完全 on-device のネイティブ iPad アプリ。
[元アプリ: Goodnotes AI for Math](https://support.goodnotes.com/hc/en-us/articles/13683534670223-Goodnotes-AI-for-Math)

## 現状（2026-06-13）

- ✅ **計算コア `mathai/`** … LaTeX 入力層 + SolveEngine（SymPy）。テスト 21 件 PASS
- ✅ **OCR 検証** … pix2tex 印刷体ベースライン。end-to-end 求解 6/7 (85.7%)。エンコーダ Core ML 変換成功
- ✅ **Web ハーネス `web/`** … 手書き→OCR→確認→求解→ステップ表示を**通しで実行できる実物**（end-to-end テスト緑）。iPad Safari からも使える暫定デモ（ネイティブ版の置き換えではない）
- ⏳ **iOS アプリ `ios/`** … Solve 本フロー（手書きキャンバス→確認カード→Solve→ステップ表示）+ 各 Spike 画面を実装済み。計算は `SolveService`（当面モック→Xcode 後に埋め込み mathai へ）。**実コンパイル/実機は Xcode 待ち**

## いますぐ試す（Xcode 不要）

```bash
python3 -m mathai "2x + 3 = 7"          # Solve をステップ表示
python3 -m mathai "\frac{x}{2} + 1 = 4"  # LaTeX も可
python3 -m mathai                         # 対話モード
python3 -m pytest mathai -q               # テスト
```

## Web ハーネスで手書きから解く（今すぐ・iPad Safari 可）

全パイプライン（手書き→認識→確認→求解→ステップ）を通しで動かす実証兼デモ。ネイティブ版とは別物。
```bash
.venv/bin/uvicorn web.server:app --host 0.0.0.0 --port 8077
#   Mac:  http://localhost:8077
#   iPad（同一LAN）: http://192.168.11.9:8077   # Apple Pencil で手書き→「認識して解く」
.venv/bin/python web/smoke_test.py    # end-to-end テスト（テキスト・θ・画像OCR）
```
（HTTP・LAN 内のみ。完全 on-device のネイティブ版は `ios/`＝Xcode 待ち。）

## iOS アプリ（Xcode 導入後）

```bash
xcodegen generate            # project.yml から MathAI.xcodeproj を生成
open MathAI.xcodeproj         # Xcode で開き、自分の iPad を選んでビルド
```
署名は無料 Apple ID（Personal Team）で可。初回は iPad の「設定 → 一般 → VPN とデバイス管理」で開発者を信頼する。

## 構成

| ディレクトリ | 役割 |
|---|---|
| `mathai/` | 計算コア（Solve の頭脳）。純 SymPy・端末内埋め込み前提 |
| `MathAI/` | iPad アプリ（SwiftUI + PencilKit）。`project.yml` で xcodegen 管理 |
| `spikes/` | 技術検証（OCR 精度・FM比較） |
| `docs/superpowers/` | 設計 spec・実装計画・スパイク結果 |

## 既知の制約

- **Xcode 必須**（現状未インストール）。iOS 側はビルド不可。
- **venv 破損**: pix2tex 用 `.venv` は brew 操作で python@3.13 が消え壊れた。ライブ OCR 再実行は `brew install python@3.13` → venv 再作成 → `pip install pix2tex` で復旧。end-to-end 求解評価は `spikes/ocr/eval_solve_from_predictions.py` で torch 無しに再現可。
- 端末内 OCR（手書き）の実用精度と Foundation Models 可用性は **実機検証が本ゲート**（`docs/superpowers/spikes/SPIKE_RESULTS.md`）。
