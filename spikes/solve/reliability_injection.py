"""信頼性の定量化 — OCR 誤りを注入し、各安全網が何を捕えるかを測る（研究テーマD）。

問い: OCR が間違えたとき、どの層がそれを止めるか？
- 機械の網は2つ: (1)エンジンが式を受け付けない(unsupported) (2)検算(verified=False)
- 人の網は1つ: 確認カード（人が見て直す）。これは自動化できないので、本ベンチは
  「機械の網をすり抜けて *検算も通る別解* になった割合」=**確認カードだけが救える領域**を測る。

方法: 正解16問(problems.json)に現実的な OCR 誤りを注入し、mathai に通して4分類:
  engine_caught : unsupported（アプリは「解けません」と表示＝気づける）
  verify_caught : supported だが verified=False（検算が異常を検知）
  harmless      : verified=True かつ解が元と一致（誤読が偶然 数学を変えなかった）
  SILENT        : verified=True かつ解が元と相違（Q4型。確認カードだけが止められる）

実行: .venv/bin/python spikes/solve/reliability_injection.py
"""
import json
import sys
from pathlib import Path

import sympy as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mathai.solver import solve_latex  # noqa: E402

HERE = Path(__file__).parent
PROBLEMS = HERE / "problems.json"

# 手書きで見間違いやすい数字ペア（双方向）。Q4 の 2→1 もここに含む。
_CONFUSE = {"0": "68", "1": "27", "2": "17", "3": "85", "4": "9",
            "5": "6", "6": "508", "7": "12", "8": "036", "9": "4"}


def perturbations(s: str) -> list[tuple[str, str]]:
    """1 文字だけ変えた現実的な OCR 誤りを列挙（数字の見間違い・符号反転・指数ズレ）。"""
    out = []
    for i, ch in enumerate(s):
        if ch.isdigit():  # 数字の見間違い
            for repl in _CONFUSE.get(ch, ""):
                out.append((f"digit@{i}:{ch}->{repl}", s[:i] + repl + s[i + 1:]))
        if ch in "+-" and i > 0 and s[i - 1] != "=":  # 符号反転（先頭・=直後は除く）
            flip = "-" if ch == "+" else "+"
            out.append((f"sign@{i}:{ch}->{flip}", s[:i] + flip + s[i + 1:]))
    # 指数ズレ: x^2 -> x^3 等（^ の直後の数字を ±1）
    for i, ch in enumerate(s):
        if ch == "^" and i + 1 < len(s) and s[i + 1].isdigit():
            d = int(s[i + 1])
            for nd in {d + 1, max(2, d - 1)} - {d}:
                out.append((f"exp@{i}:{d}->{nd}", s[:i + 1] + str(nd) + s[i + 2:]))
    seen, uniq = set(), []
    for label, p in out:
        if p != s and p not in seen:
            seen.add(p)
            uniq.append((label, p))
    return uniq


def _ans_set(strs: list[str]) -> frozenset:
    vals = set()
    for a in strs:
        try:
            vals.add(sp.nsimplify(sp.sympify(a)))
        except Exception:  # noqa: BLE001
            vals.add(a)
    return frozenset(vals)


def classify(perturbed: str, original_answer: frozenset) -> str:
    try:
        r = solve_latex(perturbed)
    except Exception:  # noqa: BLE001  パース破綻はアプリ側で弾かれる＝気づける
        return "engine_caught"
    if not r.get("supported"):
        return "engine_caught"
    if not r.get("verified"):
        return "verify_caught"
    return "harmless" if _ans_set(r.get("answer", [])) == original_answer else "SILENT"


def main() -> None:
    problems = json.loads(PROBLEMS.read_text(encoding="utf-8"))["problems"]
    counts = {"engine_caught": 0, "verify_caught": 0, "harmless": 0, "SILENT": 0}
    total = 0
    silents = []
    for prob in problems:
        orig = _ans_set(prob["expected"])
        for label, p in perturbations(prob["problem"]):
            cls = classify(p, orig)
            counts[cls] += 1
            total += 1
            if cls == "SILENT":
                r = solve_latex(p)
                silents.append((prob["id"], prob["problem"], p, label,
                                ",".join(prob["expected"]), ",".join(r.get("answer", []))))

    print(f"注入した OCR 誤り: {total} 件（16問×単一文字変異）\n")
    print(f"{'分類':16}{'件数':>6}{'割合':>8}   意味")
    desc = {
        "engine_caught": "アプリが『解けません』と表示＝気づける",
        "verify_caught": "検算が異常を検知＝気づける",
        "harmless": "誤読が解を変えず（無害）",
        "SILENT": "検算も通る別解＝確認カードだけが救える",
    }
    machine = counts["engine_caught"] + counts["verify_caught"]
    for k in ("engine_caught", "verify_caught", "harmless", "SILENT"):
        print(f"{k:16}{counts[k]:>6}{counts[k] / total:>7.0%}   {desc[k]}")
    print(f"\n機械の網が捕捉: {machine}/{total} ({machine / total:.0%})")
    print(f"確認カード必須(SILENT): {counts['SILENT']}/{total} ({counts['SILENT'] / total:.0%})")

    print("\n--- SILENT（確認カードだけが止められる）例 ---")
    for sid, prob, p, label, exp, got in silents[:8]:
        print(f"{sid}: {prob}  --[{label}]-->  {p}   期待{exp} → 別解{got}（検算◯で素通り）")


if __name__ == "__main__":
    main()
