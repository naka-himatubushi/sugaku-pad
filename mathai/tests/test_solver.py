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


def test_answer_latex_renders_as_fraction():
    # 表示用に縦分数の LaTeX を返す
    r = solve_equation("1/2 + 1/3")
    assert r["answer_latex"] == ["\\frac{5}{6}"]


def test_steps_latex_have_label_and_latex():
    r = solve_equation("2x + 3 = 7")
    assert r["steps_latex"]
    assert all("label" in s and "latex" in s for s in r["steps_latex"])


def test_bare_quadratic_expression_is_factored_with_roots():
    # 等号なしの 2 次式は「因数分解 + =0 の根」を返す（そのまま返さない）
    r = solve_equation("2x^2 - 3x - 5")
    assert r["supported"] is True
    assert r["kind"] == "polynomial"
    joined = " ".join(s["latex"] for s in r["steps_latex"])
    assert "-1" in joined and "\\frac{5}{2}" in joined  # 根 x=-1, 5/2 が手順に出る


def test_solutions_are_verified_by_substitution():
    # 検算レイヤー: 解を元の式に代入して成立を確認
    assert solve_equation("2x + 19 = 9")["verified"] is True
    assert solve_equation("x**2 - 5*x + 6 = 0")["verified"] is True
    assert solve_equation("2x^2 - 3x - 5")["verified"] is True       # 多項式（展開一致）
    assert solve_equation("1/2 + 1/3")["verified"] is True            # 数値
    assert solve_equation("2/(x^2-4) - 1/(x^2+2x)")["verified"] is True  # 簡約
