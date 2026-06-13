"""OCR の実出力（captured_predictions.json）を mathai に通し、end-to-end 求解率を測る。

pix2tex の生出力は LaTeX 表記の揺れ（2X / x^{2} / \\,）を含むが、
mathai の latex_input 層がそれを吸収して解けるかを評価する。
torch 不要（純 SymPy）なので、システム python でいつでも再現できる。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root
from mathai.solver import solve_latex

DATASET = Path(__file__).parent / "dataset"
PRED_FILE = Path(__file__).parent / "captured_predictions.json"


def main() -> int:
    labels = json.loads((DATASET / "labels.json").read_text())
    preds = json.loads(PRED_FILE.read_text())["predictions"]

    solvable = 0   # 正解側が解ける（solve 対象の）問題数
    matched = 0    # OCR 出力からも同じ解に到達できた数
    for fname, gt in labels.items():
        pred = preds.get(fname, "")
        gt_res = solve_latex(gt)
        if not gt_res["supported"]:
            print(f"{fname}: 解対象外（恒等式/多変数など） gt={gt!r}")
            continue
        solvable += 1
        pred_res = solve_latex(pred)
        ok = pred_res["supported"] and set(pred_res["answer"]) == set(gt_res["answer"])
        matched += ok
        print(f"{fname}: {'解✓' if ok else '解✗'} "
              f"pred_ans={pred_res['answer']} gt_ans={gt_res['answer']} pred={pred!r}")

    print(f"\nend-to-end 求解一致 = {matched}/{solvable} "
          f"({matched / solvable:.1%})  ※印刷体・解ける問題のみ")
    print("示唆: exact-match(58%) より高ければ、latex_input 層が OCR の表記揺れを吸収できている。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
