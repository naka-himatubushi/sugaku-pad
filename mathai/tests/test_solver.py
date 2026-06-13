"""SolveEngine の単体テスト（数式文字列入力）。"""
from mathai.solver import solve_equation


def test_linear_equation():
    r = solve_equation("2*x + 3 = 7")
    assert r["supported"] is True
    assert r["kind"] == "linear"
    assert r["answer"] == ["2"]
    assert len(r["steps"]) >= 2


def test_linear_loose_syntax_without_star():
    # 暗黙乗算: "2x" を "2*x" として解釈できる
    r = solve_equation("2x + 3 = 7")
    assert r["answer"] == ["2"]


def test_linear_steps_show_isolation():
    # ステップに「定数を移項した中間式」が現れる（教育的な手順）
    r = solve_equation("2x + 3 = 7")
    joined = " ".join(r["steps"])
    assert "2*x = 4" in joined


def test_quadratic_two_roots():
    r = solve_equation("x**2 - 5*x + 6 = 0")
    assert r["kind"] == "quadratic"
    assert set(r["answer"]) == {"2", "3"}


def test_quadratic_steps_include_factoring():
    r = solve_equation("x**2 - 5*x + 6 = 0")
    joined = " ".join(r["steps"])
    assert "x - 2" in joined and "x - 3" in joined


def test_expression_without_equals_is_evaluated():
    r = solve_equation("1/2 + 1/3")
    assert r["kind"] == "evaluate"
    assert r["answer"] == ["5/6"]


def test_unsupported_input_is_flagged():
    r = solve_equation("???not math???")
    assert r["supported"] is False
    assert r["answer"] == []


def test_trig_value_is_evaluated():
    r = solve_equation("sin(pi/6)")
    assert r["answer"] == ["1/2"]


def test_trig_identity_simplifies_to_one():
    r = solve_equation("sin(x)**2 + cos(x)**2")
    assert r["answer"] == ["1"]


def test_trig_equation_is_classified_and_solved():
    r = solve_equation("sin(x) = 0")
    assert r["kind"] == "trigonometric"
    assert "0" in r["answer"]


def test_trig_equation_in_theta_is_solved():
    # 変数が θ（x ではない）でも解ける — PreCalc 三角の中心ケース
    r = solve_equation("2*sin(theta) = 1")
    assert r["kind"] == "trigonometric"
    assert set(r["answer"]) == {"pi/6", "5*pi/6"}
