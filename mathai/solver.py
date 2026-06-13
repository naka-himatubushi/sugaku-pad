"""SolveEngine — 数式を SymPy で決定的に解き、種別・手順・解を返す。

Solve 機能の中核。LaTeX（OCR 出力）と「ゆるい数式文字列」の両方を受け付ける。
パースは SymPy の暗黙乗算変換を使い、"2x+3=7" のような人間表記も解釈できる。

公開関数:
    solve_equation(expr: str) -> dict   # "2x + 3 = 7" / "1/2 + 1/3" など
    solve_latex(latex: str) -> dict     # "\\frac{x}{2}+1=4" など（LaTeX）

返り値: {supported: bool, kind: str, steps: list[str], answer: list[str]}
"""
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

from .latex_input import latex_to_math

x = sp.Symbol("x")
_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
# 複数文字の記号は明示束縛して暗黙乗算による分解（theta -> t*h*e*t*a）を防ぐ
_LOCALS = {name: sp.Symbol(name) for name in ("x", "y", "theta", "alpha", "beta")}


def _parse(s: str):
    """ゆるい数式文字列を SymPy 式に変換する（"2x" -> 2*x, "x^2" -> x**2）。"""
    return parse_expr(s, transformations=_TRANSFORMS, local_dict=_LOCALS)


def solve_equation(expr: str) -> dict:
    expr = expr.strip()
    try:
        if "=" in expr:
            lhs_s, rhs_s = expr.split("=", 1)
            lhs, rhs = _parse(lhs_s), _parse(rhs_s)
            sols = sp.solve(sp.Eq(lhs, rhs), x)
            if not sols:
                return {"supported": False, "kind": "equation", "steps": [], "answer": []}

            poly = sp.expand(lhs - rhs)
            steps = [f"方程式: {lhs} = {rhs}"]
            kind = "equation"

            trig_funcs = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc)
            if any(poly.has(f) for f in trig_funcs):
                kind = "trigonometric"
                steps.append("三角方程式として x を解く")
            else:
                try:
                    degree = sp.Poly(poly, x).degree()
                except sp.PolynomialError:
                    degree = None
                if degree == 1:
                    kind = "linear"
                    steps.append(f"整理: {poly} = 0")
                    steps.append("x について解く")
                elif degree == 2:
                    kind = "quadratic"
                    steps.append(f"因数分解: {sp.factor(poly)} = 0")
                    steps.append("各因子をゼロにする x を求める")

            steps.append(f"解: x = {', '.join(str(s) for s in sols)}")
            return {"supported": True, "kind": kind, "steps": steps,
                    "answer": [str(s) for s in sols]}

        # "=" を含まない式は評価する
        val = _parse(expr)
        result = sp.nsimplify(val) if getattr(val, "is_number", False) else sp.simplify(val)
        steps = [f"式: {val}", f"計算: {result}"]
        return {"supported": True, "kind": "evaluate", "steps": steps,
                "answer": [str(result)]}

    except Exception:
        return {"supported": False, "kind": "unknown", "steps": [], "answer": []}


def solve_latex(latex: str) -> dict:
    """LaTeX を受け取り、数式文字列に変換してから解く。"""
    return solve_equation(latex_to_math(latex))
