# 計算層のオンデバイス化 — 埋め込み Python + SymPy + mathai（Spike E）

- 日付: 2026-06-13
- 問い: 認識(OCR)は MLX で端末内実行できた。**計算層(mathai/SymPy)も iPad 内で動くか？**
- 結論: ✅ **シミュレータ(iOS ランタイム)で動作確認**。実機 framework 化は次段。

## 何をしたか

- BeeWare **Python-Apple-support 3.13** の `Python.xcframework` をアプリに埋め込み。
- バンドル構成: `Resources/python`(PYTHONHOME=標準ライブラリ) / `app`(mathai + bridge.py) / `app_packages`(sympy, mpmath)。
- ObjC ブリッジ `PythonBridge`（C API）で PyConfig 隔離初期化（testbed 準拠: write_bytecode=0 等）→ `bridge.solve_json(latex)` を呼び JSON で受け取る。
- SwiftUI から `PythonBridge.solveJSON()`。Spike E 画面 + 起動時セルフテスト(`PYSOLVE_SELFTEST=1`)。

## 検証結果（シミュレータ self-test、全て verified=true）

| 入力 | kind | 答え |
|---|---|---|
| `2x+3=7` | linear | `2` |
| `x^2-5x+6=0` | quadratic | `2, 3`（因数分解手順付き） |
| `2x+3>7` | inequality | `x > 2` |
| `x+y=3; x-y=1` | system | `x = 2, y = 1` |

→ 一次・二次・**不等式・連立**＋**検算**まで、**端末内 Python で完全動作**。手順(steps_latex)・検算も込みで Mac と同一結果。

## 重要な切り分け（正直に）

- ✅ 検証は **iOS シミュレータ**（Mac の CPU で動く iOS ランタイム）。**実機(arm64)はまだ**。
- ⚠️ **実機の壁 = lib-dynload の framework 化**。iOS 実機は dylib を framework 経由でしか読めず、C 拡張モジュール(.so)を1つずつ署名 framework に包む必要がある（Briefcase が自動化する領域）。シミュレータは .so 直読みが緩いので先に通った。
- → 実機化は「① device スライスの dynload を framework 化 ② 署名 ③ 実機で容量・起動時間計測」が残タスク。SymPy が要る dynload は限定的なので現実的。

## 再現

```bash
dev/fetch-python-ios.sh           # Python.xcframework 取得（ios/vendor は git 管理外）
dev/build-python-payload.sh       # stdlib+sympy+mathai のペイロード生成（ios/python-ios）
xcodegen generate
# シミュレータ self-test:
xcodebuild ... -destination 'generic/platform=iOS Simulator' build
SIMCTL_CHILD_PYSOLVE_SELFTEST=1 xcrun simctl launch --console-pty <udid> com.nakazawa.mathai
```

## 次

- 実機 framework 化（上記の壁）→ iPad で計算層オンデバイス計測。
- `SolveService` を `PythonSolveService`(本ブリッジ) に差し替え → Canvas→MLX OCR→確認カード→**端末内 solve**→手順 の統合（本命の1本化）。
