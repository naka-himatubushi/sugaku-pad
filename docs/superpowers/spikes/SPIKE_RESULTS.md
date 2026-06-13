# スパイク結果（途中経過）

最終更新: 2026-06-13
関連: `docs/superpowers/plans/2026-06-13-on-device-feasibility-spikes.md`

進行中。Mac 上で自律検証できる部分を先行実施。実機（iPad + Xcode）が要る部分は中沢さん待ち。

---

## Spike A — 端末内 LaTeX-OCR（Mac ベースライン: 実施済 / 実機: 未）

- ツール: `pix2tex`（LaTeX-OCR, 重み 97MB）, 評価ハーネス `spikes/ocr/eval_pix2tex.py`
- データ: 印刷体レンダリング 12 問（代数+三角）。`spikes/ocr/gen_synthetic.py` で生成
- 結果（**印刷体**・意味ベース正規化後）:
  - exact-match = **58.3% (7/12)**
  - char-level similarity 平均 = **87.9%**
- 誤読の傾向: 関数語 "sin" の誤認識（複数）、単独文字（a→Ω）、入れ子分数（tan=sin/cos）の文字化け
- 注意: 合成画像は matplotlib フォントで pix2tex の学習元（実 LaTeX）と分布差あり。誤読の一部はその差由来の可能性。
- **暫定示唆**: 印刷体でも 58% → 実機手書きはさらに下がる前提。**確認カード（人が修正してから解く）UX が必須**。
- **未（実機ゲート）**: ① pix2tex を CoreML/MLX 化して端末搭載 ② 実 Pencil 手書き 30問で正答率 ≥80% を測定

## Spike B — 端末内 計算（ソルバ: 実施済 / 埋め込み・FM比較: 未）

- `spikes/compute/solver.py`（SymPy SolveEngine 原型）+ `test_solver.py`：**8件 PASS**
  - 対応: 線形・二次（因数分解手順）・式評価・三角（評価/恒等式/方程式分類）・非対応判定
- `spikes/compute/eval_fm_vs_sympy.py`：SymPy 正解生成 OK。FM 回答記入→採点の枠組み完成
- **未（実機ゲート）**: ① iOS への Python+SymPy 埋め込み（Python-Apple-support）成否 ② 実機 FM 単体の正答率測定（`fm_answers.json` 記入→`score`）

## Spike C — Foundation Models 可用性（未: 実機必須）

- **未**: 手持ち iPad が iOS26 / Apple Intelligence 対応か、`SystemLanguageModel.availability` を実機で確認

---

## 中沢さん側の必須アクション（自律不可）

1. **Xcode を App Store からインストール**（現状 Command Line Tools のみ。Swift/iOS は一切ビルド不可）
2. 実機 iPad を用意し、無料 Apple ID で署名・信頼設定
3. 実機での手書きデータ収集（Spike A 本ゲート）、FM 動作確認（Spike C）

## 総合判定

**保留**（Mac 側の頭脳検証は前進。実機ゲート A/B/C 完了後に GO/条件付きGO/NO-GO を確定する）
