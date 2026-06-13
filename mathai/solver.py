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
import re

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


def _result(supported, kind, struct, answer, answer_latex, verified=False) -> dict:
    return {
        "supported": supported,
        "kind": kind,
        "steps": [f"{s['label']}: {s['plain']}" if s["plain"] else s["label"] for s in struct],
        "steps_latex": [{"label": s["label"], "latex": s["latex"]} for s in struct],
        "answer": answer,
        "answer_latex": answer_latex,
        "verified": verified,  # 解を元の式に代入して成立を確認したか（検算レイヤー）
    }


def _verify_zero(expr, var, sols) -> bool:
    """各解を expr に代入して 0 になるか（=元の式を満たすか）を確認する。"""
    try:
        return bool(sols) and all(sp.simplify(expr.subs(var, s)) == 0 for s in sols)
    except Exception:
        return False


# 不等号（"<=" を "<" より先に判定するため順序が重要）
_INEQ = [("<=", sp.Le), (">=", sp.Ge), ("<", sp.Lt), (">", sp.Gt)]
_OP_LATEX = {"<=": r"\leq", ">=": r"\geq", "<": "<", ">": ">"}
_REL_L = {"<": "<", "<=": r"\leq", ">": ">", ">=": r"\geq"}


def _interval_strings(iv, var) -> tuple[str, str]:
    """1 区間を読みやすい関係式に（trivial な ±∞ 境界は省く）。(plain, latex)。"""
    lo, hi = iv.start, iv.end
    has_lo, has_hi = lo != sp.S.NegativeInfinity, hi != sp.S.Infinity
    lo_op, hi_op = ("<" if iv.left_open else "<="), ("<" if iv.right_open else "<=")
    if has_lo and has_hi:
        return (f"{lo} {lo_op} {var} {hi_op} {hi}",
                f"{sp.latex(lo)} {_REL_L[lo_op]} {sp.latex(var)} {_REL_L[hi_op]} {sp.latex(hi)}")
    if has_lo:
        op = ">" if iv.left_open else ">="
        return f"{var} {op} {lo}", f"{sp.latex(var)} {_REL_L[op]} {sp.latex(lo)}"
    if has_hi:
        return f"{var} {hi_op} {hi}", f"{sp.latex(var)} {_REL_L[hi_op]} {sp.latex(hi)}"
    return "全ての実数", r"\mathbb{R}"


def _ineq_strings(sol_set, var) -> tuple[str, str]:
    """解集合（Interval / Union / 空）を読みやすい (plain, latex) へ整形する。"""
    if sol_set == sp.S.Reals:
        return "全ての実数", r"\mathbb{R}"
    if sol_set == sp.S.EmptySet:
        return "解なし", r"\emptyset"
    if isinstance(sol_set, sp.Interval):
        return _interval_strings(sol_set, var)
    if isinstance(sol_set, sp.Union):
        parts = [_interval_strings(a, var) for a in sol_set.args if isinstance(a, sp.Interval)]
        if parts:
            return " または ".join(p[0] for p in parts), r" \;\lor\; ".join(p[1] for p in parts)
    rel = sol_set.as_relational(var)  # フォールバック
    return str(rel), sp.latex(rel)


def _verify_inequality(rel, var, sol_set) -> bool:
    """サンプル点の「解集合に属するか」と「不等式が成り立つか」が一致するか確認する。"""
    try:
        pts = [sp.Rational(k, 2) for k in range(-21, 22)]  # -10.5〜10.5 を 0.5 刻み
        return all(bool(sol_set.contains(p)) == bool(rel.subs(var, p)) for p in pts)
    except Exception:
        return False


def _solve_inequality(expr: str) -> dict:
    """一次/二次の不等式を実数で解く。解は関係式（例: 2 < x）で返し、サンプル点で検算。"""
    for op, cls in _INEQ:
        if op in expr:
            lhs, rhs = (_parse(s) for s in expr.split(op, 1))
            var = _pick_var(lhs - rhs)
            rel = cls(lhs, rhs)
            sol_set = sp.solve_univariate_inequality(rel, var, relational=False)
            ans_plain, ans_latex = _ineq_strings(sol_set, var)
            struct = [
                _step("不等式", f"{sp.latex(lhs)} {_OP_LATEX[op]} {sp.latex(rhs)}", f"{lhs} {op} {rhs}"),
                _step(f"{var} について解く", ans_latex, ans_plain),
            ]
            verified = _verify_inequality(rel, var, sol_set)
            struct.append(_step("検算（境界の内外で確認）", ans_latex,
                                "内外の点で整合" if verified else "確認できず"))
            return _result(True, "inequality", struct, [ans_plain], [ans_latex], verified)
    return _result(False, "inequality", [], [], [])


def _solve_system(parts: list[str]) -> dict:
    """複数式の連立を解く（一次連立など）。解は代入して全式一致を確認。"""
    eqs = []
    for part in parts:
        if "=" not in part:
            return _result(False, "system", [], [], [])
        lhs_s, rhs_s = part.split("=", 1)
        eqs.append(sp.Eq(_parse(lhs_s), _parse(rhs_s)))
    variables = sorted(set().union(*[e.free_symbols for e in eqs]), key=str)
    sols = sp.solve(eqs, variables, dict=True)
    if not sols:  # 解なし（平行）/不定は未対応として返す
        return _result(False, "system", [], [], [])
    sol = sols[0]
    pairs = [(v, sol[v]) for v in variables if v in sol]
    ans_plain = ", ".join(f"{v} = {val}" for v, val in pairs)
    ans_latex = ", ".join(f"{sp.latex(v)} = {sp.latex(val)}" for v, val in pairs)
    struct = [
        _step("連立方程式", r" \\ ".join(_eq(e.lhs, e.rhs)[0] for e in eqs),
              "; ".join(_eq(e.lhs, e.rhs)[1] for e in eqs)),
        _step("解", ans_latex, ans_plain),
    ]
    verified = bool(pairs) and all(sp.simplify(e.lhs.subs(sol) - e.rhs.subs(sol)) == 0 for e in eqs)
    struct.append(_step("検算（代入して確認）", ans_latex,
                        "全式に代入して一致" if verified else "確認できず"))
    return _result(True, "system", struct, [ans_plain], [ans_latex], verified)


def solve_equation(expr: str) -> dict:
    expr = expr.strip()
    try:
        # 連立: ; か改行で区切られた複数式
        parts = [p.strip() for p in re.split(r"[;\n]", expr) if p.strip()]
        if len(parts) >= 2:
            return _solve_system(parts)
        # 不等式: 不等号を含む単一式
        if any(op in expr for op, _ in _INEQ):
            return _solve_inequality(expr)

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
                    a2, b2, c2 = poly.coeff(var, 2), poly.coeff(var, 1), poly.coeff(var, 0)
                    factored = sp.factor(poly)
                    rational_roots = bool(sols) and all(getattr(s, "is_rational", False) for s in sols)
                    if rational_roots and factored != poly:
                        # 有理数解 → 実際に因数分解できる場合だけ「因数分解」と表示
                        struct.append(_step("因数分解する", f"{sp.latex(factored)} = 0", f"{factored} = 0"))
                        struct.append(_step("各因子を 0 にする",
                                            f"{sp.latex(var)} = {_csv(sols, sp.latex)}",
                                            f"{var} = {_csv(sols, str)}"))
                    else:
                        # 因数分解できない(無理数/複素数解) → 解の公式で解く
                        disc = sp.expand(b2 ** 2 - 4 * a2 * c2)
                        struct.append(_step("解の公式を使う",
                                            r"x = \frac{-b \pm \sqrt{b^{2} - 4ac}}{2a}",
                                            "x = (-b ± √(b²-4ac)) / (2a)"))
                        struct.append(_step("係数を読み取る",
                                            f"a = {sp.latex(a2)},\\quad b = {sp.latex(b2)},\\quad c = {sp.latex(c2)}",
                                            f"a={a2}, b={b2}, c={c2}"))
                        struct.append(_step("判別式を計算",
                                            f"D = b^{{2}} - 4ac = {sp.latex(disc)}",
                                            f"D = b^2-4ac = {disc}"))

            struct.append(_step("解", f"{sp.latex(var)} = {_csv(sols, sp.latex)}",
                                f"{var} = {_csv(sols, str)}"))

            # 検算: 各解を元の式に代入して両辺一致を確認
            verified = _verify_zero(lhs - rhs, var, sols)
            checks = [f"{sp.latex(var)}={sp.latex(s)}:\\ {sp.latex(lhs.subs(var, s))} = {sp.latex(rhs.subs(var, s))}"
                      for s in sols]
            struct.append(_step("検算（代入して確認）", ",\\quad ".join(checks),
                                "代入して両辺一致" if verified else "確認できず"))

            return _result(True, kind, struct, [str(s) for s in sols],
                           [sp.latex(s) for s in sols], verified)

        # "=" を含まない式
        val = _parse(expr)

        # 数値はそのまま計算（例: sin(pi/6)=1/2, 1/2+1/3=5/6）
        if getattr(val, "is_number", False):
            result = sp.nsimplify(val)
            struct = [_step("式", sp.latex(val), str(val)),
                      _step("計算", sp.latex(result), str(result))]
            verified = bool(sp.simplify(val - result) == 0)
            return _result(True, "evaluate", struct, [str(result)], [sp.latex(result)], verified)

        # 1 変数・2 次以上の多項式は因数分解 + =0 の根を出す（例: 2x^2-3x-5）
        var = _pick_var(val)
        try:
            degree = sp.Poly(val, var).degree()
        except sp.PolynomialError:
            degree = None
        if degree is not None and degree >= 2:
            factored = sp.factor(val)
            roots = sp.solve(val, var)
            struct = [
                _step("式", sp.latex(val), str(val)),
                _step("因数分解", sp.latex(factored), str(factored)),
                _step(f"{var} = 0 の解", f"{sp.latex(var)} = {_csv(roots, sp.latex)}",
                      f"{var} = {_csv(roots, str)}"),
            ]
            # 検算: 展開して元の式に戻るか + 各根で 0 になるか
            verified = (sp.expand(factored) - sp.expand(val) == 0) and _verify_zero(val, var, roots)
            struct.append(_step("検算（展開して一致）",
                                f"{sp.latex(sp.expand(factored))} = {sp.latex(sp.expand(val))}",
                                "展開して元の式に一致" if verified else "確認できず"))
            return _result(True, "polynomial", struct, [str(factored)], [sp.latex(factored)], verified)

        # それ以外は簡約（例: 2/(x^2-4)-1/(x^2+2x) → 1/(x(x-2))、恒等式 → 1）
        result = sp.simplify(val)
        struct = [_step("式", sp.latex(val), str(val)),
                  _step("計算", sp.latex(result), str(result))]
        verified = bool(sp.simplify(val - result) == 0)
        return _result(True, "evaluate", struct, [str(result)], [sp.latex(result)], verified)

    except Exception:
        return _result(False, "unknown", [], [], [])


def solve_latex(latex: str) -> dict:
    """LaTeX を受け取り、数式文字列に変換してから解く。"""
    return solve_equation(latex_to_math(latex))
