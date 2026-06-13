"""エンジン拡張（不等式・連立方程式）のテスト。

不等式: 一次/二次の不等式を実数で解き、サンプル点で検算する。
連立: 複数式（;・改行・LaTeX cases）を解き、代入で検算する。
"""
from mathai.solver import solve_equation, solve_latex


# ---- 不等式 ----
def test_linear_inequality_gt():
    r = solve_equation("2x+3>7")
    assert r["supported"] and r["kind"] == "inequality" and r["verified"]
    assert "2" in r["answer"][0]


def test_linear_inequality_le():
    r = solve_equation("3x-1<=5")
    assert r["supported"] and r["kind"] == "inequality" and r["verified"]
    assert "2" in r["answer"][0]


def test_quadratic_inequality():
    # x^2-4<0 の解は -2<x<2
    r = solve_equation("x^2-4<0")
    assert r["supported"] and r["kind"] == "inequality" and r["verified"]
    ans = r["answer"][0]
    assert "2" in ans


def test_inequality_latex_geq():
    r = solve_latex(r"2x+3\geq 7")
    assert r["supported"] and r["kind"] == "inequality" and r["verified"]


def test_inequality_answer_latex_present():
    r = solve_equation("2x+3>7")
    assert r["answer_latex"] and isinstance(r["answer_latex"][0], str)


# ---- 連立方程式 ----
def test_system_semicolon():
    r = solve_equation("x+y=3; x-y=1")
    assert r["supported"] and r["kind"] == "system" and r["verified"]
    assert r["answer"]  # 解がある


def test_system_solution_values():
    # x+y=3, x-y=1 → x=2, y=1
    r = solve_equation("x+y=3; x-y=1")
    joined = " ".join(r["answer"])
    assert "2" in joined and "1" in joined


def test_system_newline():
    r = solve_equation("2x+y=5\nx-y=1")
    assert r["supported"] and r["kind"] == "system" and r["verified"]


def test_system_latex_cases():
    r = solve_latex(r"\begin{cases} x+y=3 \\ x-y=1 \end{cases}")
    assert r["supported"] and r["kind"] == "system" and r["verified"]


def test_system_no_solution_unsupported():
    # 平行（解なし）: x+y=1, x+y=2 → 解なしは supported=False で返す
    r = solve_equation("x+y=1; x+y=2")
    assert r["supported"] is False
