"""SolveEngine（SymPy 実装）。

数式文字列を受け取り、SymPy で決定的に解いて「種別・手順・解」を返す。
Spike B の中核であり、将来の本実装 SolveEngine の原型。

公開関数:
    solve_equation(expr: str) -> dict
        expr: "2*x + 3 = 7" のような方程式、または "1/2 + 1/3" のような式
        返り値: {supported: bool, kind: str, steps: list[str], answer: list[str]}
"""
import sympy as sp

x = sp.symbols("x")


def _parse(s: str):
    """文字列を SymPy 式に変換する。x を既定の記号として束縛する。"""
    return sp.sympify(s, locals={"x": x})


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
            is_trig = any(poly.has(f) for f in trig_funcs)

            if is_trig:
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

    except (sp.SympifyError, SyntaxError, TypeError, ValueError, AttributeError):
        return {"supported": False, "kind": "unknown", "steps": [], "answer": []}
