"""SolveEngine — 数式を SymPy で決定的に解き、種別・手順・解を返す。

Solve 機能の中核。LaTeX（OCR 出力）と「ゆるい数式文字列」の両方を受け付ける。
パースは SymPy の暗黙乗算変換を使い、"2x+3=7" のような人間表記も解釈できる。

公開関数:
    solve_equation(expr: str) -> dict
    solve_latex(latex: str) -> dict

返り値:
    supported(bool), kind(str),
    steps(list[str])         … 素テキストの手順（CLI/テスト用）
    steps_latex(list[dict])  … {label, latex} の手順（KaTeX 表示用）
    answer(list[str])        … 素テキストの解
    answer_latex(list[str])  … LaTeX の解（縦分数・上付き指数で表示できる）
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


def _pick_var(expr):
    """解く対象の変数を選ぶ。x を優先、次に theta、無ければ最初の自由変数。"""
    free = expr.free_symbols
    if x in free:
        return x
    theta = sp.Symbol("theta")
    if theta in free:
        return theta
    if free:
        return sorted(free, key=str)[0]
    return x


def _step(label: str, latex: str = "", plain: str = "") -> dict:
    """1 手順を表す中間表現（label + 数式の latex/plain）。"""
    return {"label": label, "latex": latex, "plain": plain}


def _eq(lhs, rhs) -> tuple[str, str]:
    """(latex, plain) を返す等式整形ヘルパー。"""
    return f"{sp.latex(lhs)} = {sp.latex(rhs)}", f"{lhs} = {rhs}"


def _csv(items, fn) -> str:
    return ", ".join(fn(i) for i in items)


def _result(supported, kind, struct, answer, answer_latex) -> dict:
    return {
        "supported": supported,
        "kind": kind,
        "steps": [f"{s['label']}: {s['plain']}" if s["plain"] else s["label"] for s in struct],
        "steps_latex": [{"label": s["label"], "latex": s["latex"]} for s in struct],
        "answer": answer,
        "answer_latex": answer_latex,
    }


def solve_equation(expr: str) -> dict:
    expr = expr.strip()
    try:
        if "=" in expr:
            lhs_s, rhs_s = expr.split("=", 1)
            lhs, rhs = _parse(lhs_s), _parse(rhs_s)
            poly = sp.expand(lhs - rhs)
            var = _pick_var(poly)
            sols = sp.solve(sp.Eq(lhs, rhs), var)
            if not sols:
                return _result(False, "equation", [], [], [])

            eq_latex, eq_plain = _eq(lhs, rhs)
            struct = [_step("方程式", eq_latex, eq_plain)]
            kind = "equation"

            trig_funcs = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc)
            if any(poly.has(f) for f in trig_funcs):
                kind = "trigonometric"
                struct.append(_step(f"三角方程式として {var} を解く"))
            else:
                try:
                    degree = sp.Poly(poly, var).degree()
                except sp.PolynomialError:
                    degree = None
                if degree == 1:
                    kind = "linear"
                    a, c = poly.coeff(var, 1), poly.coeff(var, 0)
                    lt, pl = _eq(a * var, -c)
                    struct.append(_step(f"{var} の項をまとめる", lt, pl))
                    lt2, pl2 = _eq(var, sols[0])
                    struct.append(_step(f"両辺を {a} で割る", lt2, pl2))
                elif degree == 2:
                    kind = "quadratic"
                    factored = sp.factor(poly)
                    struct.append(_step("因数分解", f"{sp.latex(factored)} = 0", f"{factored} = 0"))
                    struct.append(_step("各因子を 0 にする",
                                        f"{sp.latex(var)} = {_csv(sols, sp.latex)}",
                                        f"{var} = {_csv(sols, str)}"))

            struct.append(_step("解", f"{sp.latex(var)} = {_csv(sols, sp.latex)}",
                                f"{var} = {_csv(sols, str)}"))
            return _result(True, kind, struct, [str(s) for s in sols], [sp.latex(s) for s in sols])

        # "=" を含まない式は評価する
        val = _parse(expr)
        result = sp.nsimplify(val) if getattr(val, "is_number", False) else sp.simplify(val)
        struct = [_step("式", sp.latex(val), str(val)),
                  _step("計算", sp.latex(result), str(result))]
        return _result(True, "evaluate", struct, [str(result)], [sp.latex(result)])

    except Exception:
        return _result(False, "unknown", [], [], [])


def solve_latex(latex: str) -> dict:
    """LaTeX を受け取り、数式文字列に変換してから解く。"""
    return solve_equation(latex_to_math(latex))
