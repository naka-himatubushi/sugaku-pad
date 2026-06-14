"""手書き end-to-end ベンチ用の方程式問題セットを作る（正解を SymPy で厳密裏取り）。

筆者が iPad に手書きする「実際にある定番の方程式」を型ごとに収録し、
(1) 期待解を SymPy の独立求解で検証し、(2) 各問を mathai に通して
「OCR が完璧なら mathai が解けるか（エンジン側カバレッジ）」を事前計測する。
→ 本番の手書き採点で「失敗が OCR 由来かエンジン由来か」を切り分けられる。

出力: spikes/solve/problems.json（採点スクリプトが読む）
実行: .venv/bin/python spikes/solve/build_problems.py
"""
import json
import sys
from pathlib import Path

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mathai.solver import solve_latex  # noqa: E402

HERE = Path(__file__).parent
_TX = standard_transformations + (implicit_multiplication_application, convert_xor)
x = sp.Symbol("x")


# (id, 種類, 手書きする式, 期待解のリスト)。期待解は人手で記入し SymPy で検証する。
RAW = [
    ("L1", "一次", "2x+3=7", ["2"]),
    ("L2", "一次", "5x-4=11", ["3"]),
    ("L3", "一次", "3(x-2)=9", ["5"]),
    ("L4", "一次", "7-2x=1", ["3"]),
    ("Q1", "二次", "x^2-5x+6=0", ["2", "3"]),
    ("Q2", "二次", "x^2-4=0", ["-2", "2"]),
    ("Q3", "二次", "2x^2-3x-2=0", ["-1/2", "2"]),
    ("Q4", "二次", "x^2+2x-8=0", ["-4", "2"]),
    ("F1", "分数", "x/2+x/3=5", ["6"]),
    ("F2", "分数", "(x+1)/2=3", ["5"]),
    ("C1", "三次", "x^3-6x^2+11x-6=0", ["1", "2", "3"]),
    ("C2", "三次", "x^3-7x+6=0", ["1", "2", "-3"]),
    ("R1", "根号", "sqrt(x)=3", ["9"]),
    ("R2", "根号", "sqrt(x+1)=2", ["3"]),
    ("M1", "混合", "x^2=2x+3", ["-1", "3"]),
    ("M2", "一次", "4x+1=2x+9", ["4"]),
]


def _expr(side: str):
    return parse_expr(side, transformations=_TX, local_dict={"x": x})


def sympy_truth(problem: str) -> list[str]:
    """問題文を独立に SymPy で解いて実数解の集合（文字列）を返す。"""
    lhs, rhs = problem.split("=")
    sols = sp.solve(sp.Eq(_expr(lhs), _expr(rhs)), x)
    out = []
    for s in sols:
        s = sp.simplify(s)
        if s.is_real is False:  # 複素解は実数ベンチでは除外
            continue
        out.append(str(s))
    return sorted(out)


def verify_expected(problem: str, expected: list[str]) -> bool:
    """期待解が本当に方程式を満たすか（代入して両辺一致）を SymPy で確認。"""
    lhs, rhs = problem.split("=")
    e = _expr(lhs) - _expr(rhs)
    return all(sp.simplify(e.subs(x, sp.sympify(a))) == 0 for a in expected)


def main() -> None:
    rows = []
    print(f"{'id':4}{'種類':6}{'問題':22}{'期待解':14}{'代入検証':8}{'SymPy解':14}{'mathai対応':10}{'mathai解'}")
    for pid, cat, problem, expected in RAW:
        ok = verify_expected(problem, expected)
        truth = sympy_truth(problem)
        m = solve_latex(problem)
        m_ans = sorted(m.get("answer", []))
        rows.append({
            "id": pid, "category": cat, "problem": problem,
            "expected": sorted(expected, key=lambda v: sp.sympify(v)),
            "sympy_truth": truth,
            "mathai_supported": m.get("supported", False),
            "mathai_answer": m_ans,
            "mathai_kind": m.get("kind", ""),
        })
        print(f"{pid:4}{cat:6}{problem:22}{','.join(expected):14}"
              f"{'OK' if ok else 'NG':8}{','.join(truth):14}"
              f"{str(m.get('supported')):10}{','.join(m_ans)}")

    bad = [r["id"] for r in rows if not verify_expected(r["problem"], r["expected"])]
    supported = sum(1 for r in rows if r["mathai_supported"])
    (HERE / "problems.json").write_text(
        json.dumps({"problems": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n問題数: {len(rows)} / 期待解 検証NG: {bad or 'なし'} / "
          f"mathai 事前対応: {supported}/{len(rows)}")
    print(f"→ {HERE / 'problems.json'} に保存")


if __name__ == "__main__":
    main()
