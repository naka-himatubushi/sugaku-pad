r"""LaTeX 入力層 — OCR が出す LaTeX を SymPy が解ける「ゆるい数式文字列」に変換する。

OCR（pix2tex 等）の出力は `2X`, `x^{2}`, `\frac{1}{2}`, `\sin^2\theta` のような LaTeX。
SymPy にそのまま渡せないので、暗黙の掛け算（2x→2*x）や ^ を活かせる形へ正規化する。
依存は SymPy のみ（端末内埋め込みのため antlr/lark 系の重いパーサは使わない）。

公開関数:
    latex_to_math(latex: str) -> str   # 例: "\\sin^2\\theta" -> "(sin(theta))^2"
"""
import re

_TRIG = "sin|cos|tan|cot|sec|csc"

# 意味を持たないスタイル/間隔コマンド
_STYLE_WRAPPERS = r"\\(?:mathrm|mathbf|mathit|boldsymbol|operatorname|text)\s*\{([^{}]*)\}"
_STYLE_TOKENS = [
    r"\left", r"\right", r"\,", r"\;", r"\!", r"\:",
    r"\quad", r"\qquad", r"\displaystyle", r"\scriptstyle", r"\textstyle",
]

# ギリシャ文字・定数・演算子の置換。不等号は長いトークンを先に（\leq を \le より先に）。
_SYMBOLS = {
    r"\leq": "<=", r"\geq": ">=", r"\le": "<=", r"\ge": ">=", r"\lt": "<", r"\gt": ">",
    r"\theta": "theta", r"\pi": "pi", r"\alpha": "alpha", r"\beta": "beta",
    r"\cdot": "*", r"\times": "*", r"\div": "/",
}


def _strip_styling(s: str) -> str:
    s = re.sub(_STYLE_WRAPPERS, r"\1", s)
    for token in _STYLE_TOKENS:
        s = s.replace(token, "")
    return s


def _expand_frac_sqrt(s: str) -> str:
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"((\1)/(\2))", s)
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"sqrt(\1)", s)
    return s


def _caret_braces(s: str) -> str:
    # x^{2} -> x^(2)
    return re.sub(r"\^\s*\{([^{}]*)\}", r"^(\1)", s)


def _expand_trig(s: str) -> str:
    """\\sin^2\\theta -> (sin(theta))^2、\\cos\\theta -> cos(theta)。"""
    pattern = re.compile(
        r"\\(" + _TRIG + r")\s*"           # 関数名
        r"(\^\([^)]*\)|\^[0-9]+)?\s*"       # 任意の冪（数字 or 括弧群のみ。引数を食べない）
        r"(\([^()]*\)|[A-Za-z]+|[0-9]+)"    # 引数（括弧群 or 単一トークン）
    )

    def repl(m: "re.Match") -> str:
        fn, power, arg = m.group(1), m.group(2), m.group(3)
        if not (arg.startswith("(") and arg.endswith(")")):
            arg = f"({arg})"
        base = f"{fn}{arg}"
        if power:
            base = f"({base})^{power[1:]}"  # 先頭の ^ を外して付け直す
        return base

    return pattern.sub(repl, s)


def _cleanup(s: str) -> str:
    s = s.replace("{", "(").replace("}", ")")  # 残った波括弧はグルーピング扱い
    s = s.replace("\\", "")                       # 未知コマンドの backslash 除去
    return s.strip()


def latex_to_math(latex: str) -> str:
    """LaTeX を SymPy 向けのゆるい数式文字列へ変換する。"""
    s = latex.lower()
    for delim in ("\\(", "\\)", "\\[", "\\]", "$$", "$"):  # 数式デリミタ（OCRが付けがち）を除去
        s = s.replace(delim, "")
    # 連立（cases 環境）: 枠を外し、行区切り \\ を連立セパレータ ; に、整列 & を除去
    s = s.replace(r"\begin{cases}", "").replace(r"\end{cases}", "")
    s = s.replace("\\\\", ";").replace("&", "")
    s = _strip_styling(s)
    for token, repl in _SYMBOLS.items():
        s = s.replace(token, repl)
    # caret を先に括弧化（x^{2}→x^(2)）して \frac{..}{x^{2}..} の入れ子波括弧を解消する。
    # これをしないと分母の {2} で _expand_frac_sqrt の [^{}]* が詰まり分数が展開できない。
    s = _caret_braces(s)
    s = _expand_frac_sqrt(s)
    s = _expand_trig(s)
    # OCR が数字の間に空白を入れることがある（"2 7"→27, "2 5 0"→250）。桁間の空白だけ詰める。
    s = re.sub(r"(?<=\d)\s+(?=\d)", "", s)
    s = _cleanup(s)
    return s
