"""LaTeX 入力層と end-to-end の solve_latex のテスト。"""
from mathai.latex_input import latex_to_math
from mathai.solver import solve_latex


# --- latex_to_math: 文字列変換の単体 ---

def test_caret_braces():
    assert latex_to_math("x^{2}") == "x^(2)"


def test_frac():
    assert latex_to_math("\\frac{1}{2}") == "((1)/(2))"


def test_sqrt():
    assert latex_to_math("\\sqrt{x+1}") == "sqrt(x+1)"


def test_trig_with_power():
    assert latex_to_math("\\sin^2\\theta") == "(sin(theta))^2"


def test_uppercase_variable_is_lowercased():
    assert latex_to_math("2X+3") == "2x+3"


# --- solve_latex: OCR 出力 LaTeX からの end-to-end ---

def test_solve_latex_linear():
    r = solve_latex("2x + 3 = 7")
    assert r["answer"] == ["2"]


def test_solve_latex_quadratic_with_braces():
    r = solve_latex("x^{2} - 5x + 6 = 0")
    assert set(r["answer"]) == {"2", "3"}


def test_solve_latex_fraction_equation():
    r = solve_latex("\\frac{x}{2} + 1 = 4")
    assert r["answer"] == ["6"]


def test_solve_latex_sqrt_equation():
    r = solve_latex("\\sqrt{x+1} = 3")
    assert r["answer"] == ["8"]


def test_solve_latex_factored_form():
    r = solve_latex("(x+1)(x-2) = 0")
    assert set(r["answer"]) == {"-1", "2"}


def test_solve_latex_trig_identity_expression():
    r = solve_latex("\\sin^2\\theta + \\cos^2\\theta")
    assert r["answer"] == ["1"]


def test_solve_latex_trig_equation_in_theta():
    r = solve_latex("2\\sin\\theta = 1")
    assert r["kind"] == "trigonometric"
    assert set(r["answer"]) == {"pi/6", "5*pi/6"}


def test_strips_inline_math_delimiters():
    # OCR が \( \) や \[ \] で囲んでも素の式に戻す（デリミタごと除去）
    assert latex_to_math(r"\(x+1\)") == "x+1"
    assert latex_to_math(r"\[x^{2}\]") == "x^(2)"


def test_solve_latex_fraction_expression_simplifies():
    # OCR 実例: \(\frac{2}{x^2-4}-\frac{1}{x^2+2x}\) = 1/(x^2-2x)
    import sympy as sp
    r = solve_latex(r"\(\frac{2}{x^2-4}-\frac{1}{x^2+2x}\)")
    assert r["supported"] is True
    x = sp.Symbol("x")
    got = sp.sympify(r["answer"][0], locals={"x": x})
    assert sp.simplify(got - 1 / (x**2 - 2 * x)) == 0
