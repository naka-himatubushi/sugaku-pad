# 端末内実現性スパイク 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Goodnotes AI for Math クローンを「完全 on-device ネイティブ iPad アプリ」で作れるか、3 つの技術スパイク（OCR / 計算 / 端末内LLM）で go/no-go をデータ判定する。

**Architecture:** SwiftUI + PencilKit のアプリ土台を作り、(C) Foundation Models 可用性、(A) 端末内 LaTeX-OCR 精度、(B) 端末内 SymPy 計算 + FM 説明 を順に検証。各スパイクは合否基準を持ち、全て満たせば Solve スライス本実装の計画へ進む。

**Tech Stack:** Swift / SwiftUI / PencilKit / CoreML or MLX-Swift / FoundationModels / Python(pix2tex, SymPy, coremltools) / Python-Apple-support

> **元 spec:** `docs/superpowers/specs/2026-06-13-goodnotes-math-ai-clone-design.md`
> **注:** これは検証計画。Solve スライス本体の実装計画は、本計画完了後にスパイク結果を反映して別途作成する。

---

## ファイル構成（本計画で作成/変更）

- `MathAI.xcodeproj`（Xcode プロジェクト一式）— アプリ土台
- `MathAI/MathAIApp.swift` — アプリエントリ
- `MathAI/Spikes/FoundationModelAvailabilityView.swift` — Spike C
- `MathAI/Spikes/OcrSpikeView.swift` — Spike A（端末内 OCR 実行・表示）
- `MathAI/Spikes/ComputeSpikeView.swift` — Spike B（端末内 SymPy 実行・表示）
- `spikes/ocr/eval_pix2tex.py` — Spike A（Mac 上での OCR 精度ハーネス）
- `spikes/ocr/dataset/` — 評価用画像 + 正解 LaTeX
- `spikes/compute/solver.py` — Spike B（SymPy ソルバ。後で本実装の SolveEngine に発展）
- `spikes/compute/test_solver.py` — solver のユニットテスト
- `spikes/compute/eval_fm_vs_sympy.py` — Spike B（FM単体 vs SymPy 比較ハーネス）
- `docs/superpowers/spikes/SPIKE_RESULTS.md` — go/no-go 判定レポート

---

## Task 1: アプリ土台 + 実機デプロイ（toolchain と配布の検証）

手書きアプリはシミュレータで検証できないため、最初に「無料署名で実機にデプロイできる」ことを確認する。これ自体が spec §9 のリスク検証。

**Files:**
- Create: `MathAI.xcodeproj`, `MathAI/MathAIApp.swift`, `MathAI/ContentView.swift`

- [ ] **Step 1: Xcode で App プロジェクトを作成**

Xcode → File → New → Project → iOS → App。
- Product Name: `MathAI`
- Interface: SwiftUI / Language: Swift
- 保存先: `~/sandbox/math-ai-ipad/`
- Signing → Team: 自分の Personal Team（無料 Apple ID）、"Automatically manage signing" ON

- [ ] **Step 2: PencilKit が使える最小 UI を書く**

`MathAI/ContentView.swift`:
```swift
import SwiftUI
import PencilKit

struct ContentView: View {
    @State private var canvas = PKCanvasView()
    var body: some View {
        VStack {
            Text("MathAI — 土台確認").font(.headline)
            CanvasRepresentable(canvas: $canvas)
                .border(.gray)
        }
    }
}

struct CanvasRepresentable: UIViewRepresentable {
    @Binding var canvas: PKCanvasView
    func makeUIView(context: Context) -> PKCanvasView {
        canvas.drawingPolicy = .anyInput
        canvas.tool = PKInkingTool(.pen, color: .black, width: 3)
        return canvas
    }
    func updateUIView(_ uiView: PKCanvasView, context: Context) {}
}
```

- [ ] **Step 3: 実機にビルド & 実行**

Run（対象: USB か Wi-Fi 接続した自分の iPad）。
Expected: iPad 上でアプリが起動し、Apple Pencil で黒い線が書ける。

> 初回は iPad の 設定 → 一般 → VPN とデバイス管理 で開発者を信頼する必要がある。

- [ ] **Step 4: コミット**

```bash
cd ~/sandbox/math-ai-ipad
git add -A
git commit -m "feat: MathAI アプリ土台（PencilKit 描画 + 実機署名確認）"
```

**合否ゲート:** 実機で起動・Pencil 描画ができれば PASS。署名/デプロイが不可なら、ここで配布方式（有料 Developer 等）を再検討。

---

## Task 2: Spike C — Foundation Models 可用性（最も安価な検証を先に）

iPad が iOS26 / Apple Intelligence 対応で端末内 LLM を使えるかを確認する。説明文（Explanation）を FM に任せられるかが決まる。

**Files:**
- Create: `MathAI/Spikes/FoundationModelAvailabilityView.swift`
- Modify: `MathAI/ContentView.swift`（Spike 画面への遷移を追加）

- [ ] **Step 1: FM 可用性チェック画面を書く**

`MathAI/Spikes/FoundationModelAvailabilityView.swift`:
```swift
import SwiftUI
import FoundationModels   // 注: iOS26 SDK。未提供なら #if canImport で握り、結果を「非対応」として記録する

struct FoundationModelAvailabilityView: View {
    @State private var status: String = "未確認"
    @State private var sample: String = ""
    var body: some View {
        VStack(spacing: 16) {
            Text("Spike C: Foundation Models").font(.headline)
            Text(status)
            Text(sample).font(.caption).padding()
            Button("確認する") { Task { await check() } }
        }
    }

    func check() async {
        let model = SystemLanguageModel.default
        switch model.availability {
        case .available:
            status = "available ✅"
            do {
                let session = LanguageModelSession()
                let r = try await session.respond(to: "2x + 3 = 7 を解くと x は？数値だけ答えて。")
                sample = "FM 応答: \(r.content)"
            } catch {
                sample = "応答エラー: \(error)"
            }
        case .unavailable(let reason):
            status = "unavailable ❌ (\(String(describing: reason)))"
        @unknown default:
            status = "unknown"
        }
    }
}
```

> **注（正直に）:** `FoundationModels` の API 名（`SystemLanguageModel.default` / `LanguageModelSession.respond`）は iOS26 想定。インストール済み SDK と差異があればコンパイルエラーで判明するので、その時点で実 API に合わせる。`#if canImport(FoundationModels)` で囲み、import 不可なら status="非対応(SDKなし)" を記録する。

- [ ] **Step 2: ContentView から開けるようにする**

`MathAI/ContentView.swift` に `NavigationStack` + `NavigationLink("Spike C", destination: FoundationModelAvailabilityView())` を追加。

- [ ] **Step 3: 実機で実行し結果を記録**

Run → "Spike C" → "確認する"。
Expected: `available ✅` と FM 応答（理想は "2"）が表示される、または `unavailable` 理由が表示される。
結果（available / unavailable・理由・サンプル応答の正否）をメモする（後で SPIKE_RESULTS.md に転記）。

- [ ] **Step 4: コミット**

```bash
git add -A
git commit -m "spike(C): Foundation Models 可用性チェック"
```

**合否ゲート:** `.available` かつ簡単な算術に正答 → 説明 LLM に FM を採用。`unavailable` → 説明はテンプレ文 fallback（計算は SymPy 前提）。

---

## Task 3: Spike A — 端末内 LaTeX-OCR の精度（最大リスク・fail-fast）

手書き数式→LaTeX が端末内で実用精度に達するかを検証する。まず Mac 上で OCR エンジンとして `pix2tex` の素の精度を測り、次に端末内デプロイと実 Pencil 入力での精度を測る。

**Files:**
- Create: `spikes/ocr/eval_pix2tex.py`, `spikes/ocr/dataset/labels.json`, `spikes/ocr/dataset/img/*.png`
- Create: `MathAI/Spikes/OcrSpikeView.swift`

- [ ] **Step 1: 評価データセットを用意（30 問・代数+三角）**

`spikes/ocr/dataset/labels.json`（画像ファイル名→正解 LaTeX）:
```json
{
  "q01.png": "2x + 3 = 7",
  "q02.png": "x^2 - 5x + 6 = 0",
  "q03.png": "\\frac{1}{2} + \\frac{1}{3}",
  "q04.png": "\\sin^2\\theta + \\cos^2\\theta = 1",
  "q05.png": "\\tan\\theta = \\frac{\\sin\\theta}{\\cos\\theta}"
}
```
画像は iPad で手書き → スクショ → `dataset/img/` に配置（最低 30 件、代数 15 / 三角 15 を目安）。labels.json も 30 件に拡張する。

- [ ] **Step 2: OCR 精度ハーネスを書く（失敗するテスト相当）**

`spikes/ocr/eval_pix2tex.py`:
```python
"""Spike A: pix2tex の手書き数式→LaTeX 精度を測る評価ハーネス。"""
import json, sys
from pathlib import Path
from pix2tex.cli import LatexOCR
from PIL import Image

def normalize(s: str) -> str:
    return s.replace(" ", "").replace("\\left", "").replace("\\right", "")

def main(dataset: Path) -> float:
    labels = json.loads((dataset / "labels.json").read_text())
    model = LatexOCR()
    exact = 0
    for fname, gt in labels.items():
        pred = model(Image.open(dataset / "img" / fname))
        ok = normalize(pred) == normalize(gt)
        exact += ok
        print(f"{fname}: {'OK ' if ok else 'NG '} pred={pred!r} gt={gt!r}")
    acc = exact / len(labels)
    print(f"\nexact-match accuracy = {acc:.1%} ({exact}/{len(labels)})")
    return acc

if __name__ == "__main__":
    acc = main(Path(__file__).parent / "dataset")
    sys.exit(0 if acc >= 0.80 else 1)
```

- [ ] **Step 3: Mac で実行し素の精度を測る**

```bash
cd ~/sandbox/math-ai-ipad
python -m venv .venv && source .venv/bin/activate
pip install "pix2tex[gui]" pillow
python spikes/ocr/eval_pix2tex.py
```
Expected: exact-match accuracy が表示される。≥80% なら端末内化に進む価値あり。<80% なら「修正前提UX/記号パレット併用」へ設計変更（合否ゲート参照）。

- [ ] **Step 4: 端末内モデル化を試す（CoreML 変換を第一候補、MLX-Swift を代替）**

```bash
pip install coremltools torch
# pix2tex の画像エンコーダ+デコーダを torch.jit.trace → coremltools.convert で .mlpackage 化を試みる
```
> **正直に:** pix2tex は encoder-decoder の自己回帰生成で、CoreML への素直な変換が難しい可能性が高い。詰まったら **MLX-Swift で同等モデルを動かす経路**に切り替える（Apple Silicon の iPad で MLX は動作可能）。どちらも不可なら本ゲートを NG とし、TrOCR-math など別モデル、または Spike A 全体を「端末内 OCR は非現実的」と結論づける。
変換できた `.mlpackage`（または MLX 重み）を `MathAI/` に追加。

- [ ] **Step 5: アプリで実 Pencil 入力 → LaTeX を出す画面を書く**

`MathAI/Spikes/OcrSpikeView.swift`（PencilKit の描画を `UIImage` にラスタライズしてモデルへ渡す）:
```swift
import SwiftUI
import PencilKit

struct OcrSpikeView: View {
    @State private var canvas = PKCanvasView()
    @State private var latex = ""
    var body: some View {
        VStack {
            Text("Spike A: 端末内 OCR").font(.headline)
            CanvasRepresentable(canvas: $canvas).border(.gray)
            Button("認識") { latex = recognize(rasterize(canvas)) }
            Text("LaTeX: \(latex)").padding()
        }
    }
    func rasterize(_ c: PKCanvasView) -> UIImage {
        c.drawing.image(from: c.drawing.bounds, scale: 2.0)
    }
    func recognize(_ image: UIImage) -> String {
        // Step 4 で得た CoreML/MLX モデルを呼ぶ。詳細は変換結果の API に合わせる。
        return OcrModel.shared.predict(image)
    }
}
```
（`OcrModel` は Step 4 の成果物に合わせた薄いラッパとして同 Task 内で作成する。）

- [ ] **Step 6: 実機で実 Pencil 入力の精度を測る**

評価セット 30 問を iPad に手書きし、認識結果を labels.json と突き合わせて exact-match を手計算（または簡易ログ）で集計。
Expected: 実 Pencil 入力での正答率を記録。

- [ ] **Step 7: コミット**

```bash
git add -A
git commit -m "spike(A): 端末内 LaTeX-OCR 精度検証（Mac harness + 実機 OCR）"
```

**合否ゲート:** 実 Pencil 入力で exact-match ≥ **80%** → OCR 採用。未満 → 認識 UX を「修正前提」または記号パレット併用に設計変更し、spec を更新。

---

## Task 4: Spike B — 端末内 計算（SymPy 埋め込み + FM単体比較）

「ローカルLLM単体で足りるか／SymPy は必要か」をデータで判定し、SymPy を iOS に埋め込めるか検証する。Part 1 の SymPy ソルバは後で本実装の SolveEngine に発展する。

**Files:**
- Create: `spikes/compute/solver.py`, `spikes/compute/test_solver.py`, `spikes/compute/eval_fm_vs_sympy.py`
- Create: `MathAI/Spikes/ComputeSpikeView.swift`

- [ ] **Step 1: SymPy ソルバの失敗するテストを書く**

`spikes/compute/test_solver.py`:
```python
"""SolveEngine（SymPy 実装）のユニットテスト。"""
from solver import solve_equation

def test_linear():
    r = solve_equation("2*x + 3 = 7")
    assert r["answer"] == ["2"]
    assert len(r["steps"]) >= 1

def test_quadratic():
    r = solve_equation("x**2 - 5*x + 6 = 0")
    assert set(r["answer"]) == {"2", "3"}

def test_unsolvable_marks_unsupported():
    r = solve_equation("???")
    assert r["supported"] is False
```

- [ ] **Step 2: テストを実行して落ちることを確認**

```bash
cd ~/sandbox/math-ai-ipad/spikes/compute
python -m pytest test_solver.py -v
```
Expected: FAIL（`solver` 未実装 / ImportError）。

- [ ] **Step 3: SymPy ソルバを最小実装**

`spikes/compute/solver.py`:
```python
"""LaTeX/プレーン数式を SymPy で解いてステップと解を返す。"""
import sympy as sp

def solve_equation(expr: str) -> dict:
    try:
        lhs, rhs = expr.split("=") if "=" in expr else (expr, "0")
        x = sp.symbols("x")
        eq = sp.Eq(sp.sympify(lhs), sp.sympify(rhs))
        sols = sp.solve(eq, x)
        steps = [f"方程式: {sp.pretty(eq)}", f"x について解く: {sols}"]
        return {"supported": True, "steps": steps,
                "answer": [str(s) for s in sols]}
    except Exception:
        return {"supported": False, "steps": [], "answer": []}
```

- [ ] **Step 4: テストを実行して通ることを確認**

```bash
python -m pytest test_solver.py -v
```
Expected: PASS（3 件）。

- [ ] **Step 5: FM単体 vs SymPy 比較ハーネスを書く**

`spikes/compute/eval_fm_vs_sympy.py`（同じ問題セットで SymPy の正答を基準に、FM 単体の正答率を集計する。FM 呼び出しは Mac の Foundation Models 相当が無いため、Task 2 の実機 FM 応答を手入力するか、ローカル小型 LLM で代用して傾向を見る）:
```python
"""SymPy の解を正解として、LLM 単体解答の正答率を測る。"""
import json
from solver import solve_equation

PROBLEMS = ["2*x + 3 = 7", "x**2 - 5*x + 6 = 0", "3*x - 9 = 0"]

def main():
    rows = []
    for p in PROBLEMS:
        truth = solve_equation(p)["answer"]
        rows.append({"problem": p, "sympy_answer": truth})
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print("→ 各 problem を Task2 の実機 FM に解かせ、上の sympy_answer と一致するか手集計する")

if __name__ == "__main__":
    main()
```
Expected: SymPy の正解一覧が出る。これを基準に FM 単体の正答率を集計し、「LLM単体で実用精度に届くか／SymPy が必要か」を判断する材料にする。

- [ ] **Step 6: iOS に Python+SymPy を埋め込めるか検証**

`Python-Apple-support`（BeeWare）を使って CPython + SymPy を iOS アプリにバンドルし、端末上で 1 問解けるか確認する。
```
# 参考手順:
#  1. https://github.com/beeware/Python-Apple-support のリリースから iOS 用 Python.xcframework を取得
#  2. Xcode に xcframework を追加、SymPy(pure python)+mpmath を site-packages に同梱
#  3. PythonKit などで Swift から solve_equation を呼ぶ
```
`MathAI/Spikes/ComputeSpikeView.swift` に「2x+3=7 を解く」ボタンを置き、端末上の SymPy が `x=2` を返すか表示する。
> **正直に:** iOS への Python 埋め込みはビルドが重く、初回構築に時間がかかる。詰まる場合は「SymPy はサーバ無しでは厳しい」と記録し、Spike B の結論として (i) FM 単体精度が十分なら LLM-only、(ii) 不十分なら方式 C の再検討、を SPIKE_RESULTS.md に明記する。

- [ ] **Step 7: 実機で SymPy 実行を確認・コミット**

Run → "Spike B" → 「解く」。Expected: 端末上で `x = 2`。
```bash
git add -A
git commit -m "spike(B): SymPy ソルバ + iOS 埋め込み + FM単体比較"
```

**合否ゲート:** ①SymPy が端末上で解ける かつ ②（FM採用時）FM が SymPy 結果を自然言語で説明できる → 「SymPy計算 + FM説明」を採用。SymPy 埋め込み不可 かつ FM 単体精度が十分 → LLM-only を採用。どちらも不可 → 方式 C 再検討。

---

## Task 5: スパイク結果レポートと go/no-go 判定

3 スパイクの結果を 1 つの判定ドキュメントに集約し、Solve スライス本実装に進むか・方式や spec を見直すかを決める。

**Files:**
- Create: `docs/superpowers/spikes/SPIKE_RESULTS.md`

- [ ] **Step 1: 結果レポートを書く**

`docs/superpowers/spikes/SPIKE_RESULTS.md` に以下を表で記録:
- Spike A: 実 Pencil OCR 正答率（数値）/ 合否 / 採用方針
- Spike B: SymPy 端末実行 可否 / FM単体正答率 / 採用エンジン
- Spike C: FM 可用性 / 説明 LLM 採用方針
- 総合判定: GO（Solve スライス本実装へ）/ 条件付き GO（設計変更点を列挙）/ NO-GO（方式 C 再検討）

- [ ] **Step 2: コミット**

```bash
git add -A
git commit -m "docs: スパイク結果と go/no-go 判定"
```

**合否ゲート:** GO または 条件付き GO の場合のみ、Solve スライス本実装の計画作成に進む。

---

## Self-Review（spec 対応チェック）

- spec §7 Spike A → Task 3 / Spike B → Task 4 / Spike C → Task 2 ✅
- spec §9 配布リスク → Task 1（実機署名確認）✅
- spec §3 計算=SymPy / 説明=FM → Task 4 / Task 2 ✅
- spec §10 リスク（OCR精度・SymPy埋め込み・FM可用性）→ 各 Task に合否ゲートと fallback を明記 ✅
- 本計画は検証スコープに限定。Solve スライス本体（確認カード→Solve→表示の通し実装）は Task 5 の GO 判定後に別計画で作成する（意図的なスコープ分割）。
- プレースホルダ: 不確実な iOS 部分（CoreML 変換・Python 埋め込み・FM API 名）は「断定コード」ではなく「試行＋計測＋判断ゲート」として明示。これは spec の no-overpromising 方針に沿った意図的な書き方。
