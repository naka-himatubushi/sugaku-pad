"""手書き end-to-end セッションを採点する。

webapp で筆者が問題を順に手書きすると、Mac サーバが web/captures/log.jsonl に
各問の recognize(生 OCR) と solve(求解 latex+answer) を記録する。本スクリプトは
problems.json の期待解と突き合わせ、(1)OCR一致(意味的) (2)end-to-end 求解正答率を出す。

採点の堅牢化:
- recognize → その直後の solve をペアにする（出現順の単純対応はしない）。
- 「解く」二度押し等で連続重複した solve は 1 件に畳む。
- OCR 一致は latex 文字列の素一致ではなく、mathai のパーサ + SymPy で
  「同じ方程式か（解集合が一致する係数まで）」を意味的に判定する（\frac と / 等の表記差を吸収）。

使い方:
  .venv/bin/python spikes/solve/grade_session.py --mark   # 開始前に基準行数を記録
  .venv/bin/python spikes/solve/grade_session.py          # 採点
  .venv/bin/python spikes/solve/grade_session.py --since 40
"""
import argparse
import json
import sys
from pathlib import Path

import sympy as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mathai.latex_input import latex_to_math  # noqa: E402
from sympy.parsing.sympy_parser import (  # noqa: E402
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

HERE = Path(__file__).parent
LOG = HERE.parents[1] / "web" / "captures" / "log.jsonl"
PROBLEMS = HERE / "problems.json"
MARK = HERE / ".session_baseline"
_TX = standard_transformations + (implicit_multiplication_application, convert_xor)
_x = sp.Symbol("x")


def _eq_expr(s: str):
    """方程式文字列 'lhs=rhs' を lhs-rhs の SymPy 式に。'=' 無しはそのまま式扱い。"""
    s = latex_to_math(s)
    if "=" in s:
        lhs, rhs = s.split("=", 1)
        return parse_expr(lhs, transformations=_TX, local_dict={"x": _x}) - parse_expr(
            rhs, transformations=_TX, local_dict={"x": _x})
    return parse_expr(s, transformations=_TX, local_dict={"x": _x})


def same_equation(a: str, b: str) -> bool:
    """2 つの方程式が同値か（差が 0、または非零定数倍で解集合が一致）を意味的に判定。"""
    try:
        ea, eb = _eq_expr(a), _eq_expr(b)
        if sp.simplify(ea - eb) == 0:
            return True
        if eb != 0:
            r = sp.simplify(ea / eb)
            return r.is_number and r != 0
    except Exception:  # noqa: BLE001  パース不能な OCR 出力は不一致扱い
        return False
    return False


def is_recognize(e: dict) -> bool:
    return e.get("source") == "recognize" or e.get("kind") == "recognize"


def is_solve(e: dict) -> bool:
    return not is_recognize(e) and e.get("source") in ("handwriting", "text")


def pair_entries(entries: list[dict]) -> list[dict]:
    """recognize → 直後の solve をペア化。連続重複 solve は畳む。"""
    pairs = []
    pending = None
    i = 0
    while i < len(entries):
        e = entries[i]
        if is_recognize(e):
            pending = e
        elif is_solve(e):
            pairs.append({"recognize": pending, "solve": e})
            pending = None
            while (i + 1 < len(entries) and is_solve(entries[i + 1])
                   and entries[i + 1].get("latex") == e.get("latex")
                   and entries[i + 1].get("answer") == e.get("answer")):
                i += 1  # 二度押しの重複 solve を読み飛ばす
        i += 1
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mark", action="store_true")
    ap.add_argument("--since", type=int, default=None)
    args = ap.parse_args()

    lines = [json.loads(x) for x in LOG.read_text(encoding="utf-8").splitlines() if x.strip()] \
        if LOG.exists() else []
    if args.mark:
        MARK.write_text(str(len(lines)), encoding="utf-8")
        print(f"基準を記録: {len(lines)} 行")
        return

    since = args.since if args.since is not None else (
        int(MARK.read_text()) if MARK.exists() else 0)
    pairs = pair_entries(lines[since:])
    problems = json.loads(PROBLEMS.read_text(encoding="utf-8"))["problems"]

    ocr_ok = e2e_ok = graded = 0
    print(f"{'id':4}{'種類':6}{'問題':18}{'OCR読取':26}{'OCR':5}{'解':5}答え(期待→実際)")
    for i, prob in enumerate(problems):
        if i >= len(pairs):
            print(f"{prob['id']:4}{prob['category']:6}{prob['problem']:18}(未提出)")
            continue
        graded += 1
        rec, sol = pairs[i]["recognize"], pairs[i]["solve"]
        read = (rec or sol).get("latex", "")
        ocr_match = same_equation(read, prob["problem"])
        got, exp = set(sol.get("answer", [])), set(prob["expected"])
        solved = bool(sol.get("supported")) and got == exp
        ocr_ok += ocr_match
        e2e_ok += solved
        print(f"{prob['id']:4}{prob['category']:6}{prob['problem']:18}{read[:24]:26}"
              f"{'✓' if ocr_match else '✗':5}{'✓' if solved else '✗':5}"
              f"{','.join(prob['expected'])} → {','.join(sol.get('answer', [])) or '—'}")

    print(f"\n採点 {graded} 問 / 全 {len(problems)} 問")
    if graded:
        print(f"OCR 一致(意味的): {ocr_ok}/{graded} ({ocr_ok / graded:.0%})")
        print(f"end-to-end 求解正答: {e2e_ok}/{graded} ({e2e_ok / graded:.0%})")
        print("（エンジン単体は事前検証で 16/16。end-to-end の差分は OCR 由来）")


if __name__ == "__main__":
    main()
