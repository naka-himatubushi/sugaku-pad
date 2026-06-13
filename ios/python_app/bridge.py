"""Swift から呼ぶ薄い橋渡し。mathai を JSON 文字列で返すだけ（C API 経由が楽なため）。

ネイティブ側は solve_json(latex) を 1 つ呼べばよい。結果は mathai.solver の dict を
そのまま JSON 化（supported/kind/steps/answer/verified/…）。app/ に置き sys.path に入る。
"""
import json

from mathai.solver import solve_latex


def solve_json(latex: str) -> str:
    try:
        return json.dumps(solve_latex(latex), ensure_ascii=False)
    except Exception as e:  # 念のため: 例外は JSON で返し、ネイティブ側で表示
        return json.dumps({"supported": False, "kind": "error", "error": repr(e),
                           "steps": [], "answer": []}, ensure_ascii=False)
