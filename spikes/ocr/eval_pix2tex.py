"""Spike A: pix2tex の数式画像→LaTeX 精度を測る評価ハーネス。

exact-match（正規化後の完全一致）と char-level 類似度を出す。
全予測を表示するので、人手での質的確認もできる。

使い方:
    python gen_synthetic.py      # まず評価画像を生成
    python eval_pix2tex.py       # 精度を測定（戻り値: 80%未満で exit 1）
"""
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image
from pix2tex.cli import LatexOCR

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root を import パスへ
from mathai.solver import solve_latex

DATASET = Path(__file__).parent / "dataset"


def normalize(s: str) -> str:
    """意味の同じ表記を揃える（大文字小文字・スタイル・空白・括弧・コマンド記号）。

    例: '2X+3=7' と '2x + 3 = 7'、'x^{2}' と 'x^2' は一致扱い。
    一方 'sin'→'sip' のような本物の誤読は不一致のまま残す。
    """
    s = s.lower()
    # スタイル/装飾コマンド（意味を持たない）を除去
    for token in ("\\mathrm", "\\boldsymbol", "\\scriptstyle", "\\displaystyle",
                  "\\textstyle", "\\left", "\\right", "\\,", "\\;", "\\!", "\\ ", "~"):
        s = s.replace(token, "")
    # 括弧・空白を除去（^{2} と ^2 を同一視）
    for token in ("{", "}", " "):
        s = s.replace(token, "")
    # 残るコマンド記号（\sin, \cos, \theta, \frac ...）の backslash を除去
    s = s.replace("\\", "")
    return s


def main() -> int:
    labels = json.loads((DATASET / "labels.json").read_text())
    model = LatexOCR()

    exact = 0
    sim_total = 0.0
    solved_ok = 0          # OCR出力をそのまま解いて正解と一致した数（製品観点の指標）
    solvable_gt = 0        # そもそも solve 対象（解ける）正解問題の数
    for fname, gt in labels.items():
        pred = model(Image.open(DATASET / "img" / fname))
        n_pred, n_gt = normalize(pred), normalize(gt)
        ok = n_pred == n_gt
        sim = SequenceMatcher(None, n_pred, n_gt).ratio()
        exact += ok
        sim_total += sim

        gt_res = solve_latex(gt)
        end_to_end = False
        if gt_res["supported"]:
            solvable_gt += 1
            pred_res = solve_latex(pred)
            end_to_end = pred_res["supported"] and set(pred_res["answer"]) == set(gt_res["answer"])
            solved_ok += end_to_end

        mark = "OK " if ok else "NG "
        e2e = "解✓" if end_to_end else ("解✗" if gt_res["supported"] else "解対象外")
        print(f"{fname}: {mark} {e2e} sim={sim:.2f} pred={pred!r} gt={gt!r}")

    n = len(labels)
    acc = exact / n
    print(f"\nexact-match = {acc:.1%} ({exact}/{n})")
    print(f"char-level similarity（平均） = {sim_total / n:.1%}")
    if solvable_gt:
        print(f"end-to-end 求解一致 = {solved_ok / solvable_gt:.1%} ({solved_ok}/{solvable_gt} 解ける問題中)")
    print("注: これは印刷体レンダリングでの数値。実機手書きの本ゲートは別途 iPad で測定する。")
    return 0 if acc >= 0.80 else 1


if __name__ == "__main__":
    sys.exit(main())
