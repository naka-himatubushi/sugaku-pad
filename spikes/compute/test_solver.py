"""SolveEngine（SymPy 実装）のユニットテスト。

将来の本実装 SolveEngine の仕様をテストで固定する。
インターフェース: solve_equation(expr: str) -> dict
  返り値キー: supported(bool), kind(str), steps(list[str]), answer(list[str])
"""
from solver import solve_equation


def test_linear_equation():
    r = solve_equation("2*x + 3 = 7")
    assert r["supported"] is True
    assert r["kind"] == "linear"
    assert r["answer"] == ["2"]
    assert len(r["steps"]) >= 2


def test_quadratic_two_roots():
    r = solve_equation("x**2 - 5*x + 6 = 0")
    assert r["supported"] is True
    assert r["kind"] == "quadratic"
    assert set(r["answer"]) == {"2", "3"}


def test_quadratic_steps_include_factoring():
    r = solve_equation("x**2 - 5*x + 6 = 0")
    joined = " ".join(r["steps"])
    # 因数分解の形 (x - 2)(x - 3) が手順に現れる
    assert "x - 2" in joined and "x - 3" in joined


def test_expression_without_equals_is_evaluated():
    r = solve_equation("1/2 + 1/3")
    assert r["supported"] is True
    assert r["kind"] == "evaluate"
    assert r["answer"] == ["5/6"]


def test_unsupported_input_is_flagged():
    r = solve_equation("???not math???")
    assert r["supported"] is False
    assert r["answer"] == []


def test_trig_value_is_evaluated():
    r = solve_equation("sin(pi/6)")
    assert r["supported"] is True
    assert r["kind"] == "evaluate"
    assert r["answer"] == ["1/2"]


def test_trig_identity_simplifies_to_one():
    r = solve_equation("sin(x)**2 + cos(x)**2")
    assert r["supported"] is True
    assert r["answer"] == ["1"]


def test_trig_equation_is_classified_and_solved():
    r = solve_equation("sin(x) = 0")
    assert r["supported"] is True
    assert r["kind"] == "trigonometric"
    assert "0" in r["answer"]
