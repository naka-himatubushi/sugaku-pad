"""Spike B: 「ローカルLLM単体で足りるか／SymPy は必要か」をデータで判定するハーネス。

SymPy の解を正解（ground truth）とし、端末内 Foundation Models（FM）単体の解答を採点する。
FM 呼び出しは Mac には無いため、2 モードで運用する:

  python eval_fm_vs_sympy.py generate
      -> 問題セットと SymPy 正解を出力し、fm_answers.json のテンプレを作る
      （中沢さんは実機 MathAI の Spike B 画面で各問を FM に解かせ、回答を記入）

  python eval_fm_vs_sympy.py score
      -> fm_answers.json を読み、FM 単体の正答率を SymPy 正解と突き合わせて集計
"""
import json
import sys
from pathlib import Path

from solver import solve_equation

HERE = Path(__file__).parent
ANSWERS = HERE / "fm_answers.json"

# 代数（線形/二次）+ PreCalc 三角 の代表問題
PROBLEMS = [
    "2*x + 3 = 7",
    "3*x - 9 = 0",
    "x/2 + 1 = 4",
    "x**2 - 5*x + 6 = 0",
    "x**2 - 9 = 0",
    "sin(pi/6)",
    "sin(x)**2 + cos(x)**2",
    "sin(x) = 0",
]


def ground_truth() -> list[dict]:
    rows = []
    for p in PROBLEMS:
        r = solve_equation(p)
        rows.append({"problem": p, "sympy_answer": r["answer"], "kind": r["kind"]})
    return rows


def generate() -> None:
    rows = ground_truth()
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    template = [{"problem": r["problem"], "fm_answer": []} for r in rows]
    ANSWERS.write_text(json.dumps(template, ensure_ascii=False, indent=2))
    print(f"\n{ANSWERS.name} を作成。実機 FM の回答を fm_answer に記入して 'score' を実行。")


def _match(truth: list[str], got: list[str]) -> bool:
    return set(map(str, truth)) == set(map(str, got))


def score() -> int:
    if not ANSWERS.exists():
        print("fm_answers.json が無い。先に 'generate' を実行。")
        return 1
    truth = {r["problem"]: r["sympy_answer"] for r in ground_truth()}
    fm = json.loads(ANSWERS.read_text())
    correct = 0
    for row in fm:
        p = row["problem"]
        ok = _match(truth.get(p, []), row.get("fm_answer", []))
        correct += ok
        print(f"{'OK ' if ok else 'NG '} {p}: fm={row.get('fm_answer')} truth={truth.get(p)}")
    n = len(fm)
    acc = correct / n if n else 0.0
    print(f"\nFM 単体 正答率 = {acc:.1%} ({correct}/{n})")
    print("判定の目安: 高ければ LLM-only も選択肢。低ければ SymPy（決定的計算）が必要。")
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "generate"
    if mode == "generate":
        generate()
        return 0
    if mode == "score":
        return score()
    print("usage: eval_fm_vs_sympy.py [generate|score]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
