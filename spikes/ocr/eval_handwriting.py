"""実手書きで qwen2.5-VL の手書き数式 OCR 正答率を測る研究用ベンチ。

中沢さんが webapp で実際に書いた手書き（handwriting_eval/）を正解ラベルと突き合わせ、
(1) 文字一致（正規化後）と (2) end-to-end 求解一致（mathai で解いて同じ答えか）を測る。

使い方: .venv/bin/python spikes/ocr/eval_handwriting.py
"""
import base64
import json
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mathai.solver import solve_latex

HERE = Path(__file__).parent / "handwriting_eval"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.environ.get("OCR_MODEL", "qwen2.5vl:7b")  # OCR_MODEL=gemma4:e2b 等で切替
PROMPT = ("You are a precise math OCR. Transcribe the handwritten math expression into ONE line "
          "of LaTeX. Output ONLY the LaTeX, no explanation, no dollar signs, no code fences.")


def normalize(s: str) -> str:
    s = s.lower()
    for t in ("\\left", "\\right", "\\,", "\\;", "\\!", "\\(", "\\)", "\\[", "\\]", "$", "{", "}", " "):
        s = s.replace(t, "")
    return s.replace("\\", "")


def ocr(image_b64: str) -> str:
    r = httpx.post(f"{OLLAMA}/api/generate",
                   json={"model": MODEL, "prompt": PROMPT, "images": [image_b64],
                         "stream": False, "options": {"temperature": 0}}, timeout=120)
    t = r.json().get("response", "").strip()
    for x in ("```latex", "```", "\\(", "\\)", "\\[", "\\]", "$$"):
        t = t.replace(x, "")
    return t.strip().strip("$").strip()


def main() -> None:
    labels = json.loads((HERE / "labels.json").read_text())["labels"]
    exact = solve_ok = solvable = 0
    for fn, gt in labels.items():
        pred = ocr(base64.b64encode((HERE / "img" / fn).read_bytes()).decode())
        em = normalize(pred) == normalize(gt)
        exact += em
        gtr, pr = solve_latex(gt), solve_latex(pred)
        e2e = False
        if gtr["supported"]:
            solvable += 1
            e2e = pr["supported"] and set(pr["answer"]) == set(gtr["answer"])
            solve_ok += e2e
        print(f"{fn}: {'文字一致' if em else '不一致 '} {'解✓' if e2e else '   '} pred={pred!r} gt={gt!r}")

    n = len(labels)
    print(f"\n文字一致(正規化): {exact}/{n} ({exact / n:.0%})")
    print(f"end-to-end 求解一致: {solve_ok}/{solvable}（解ける問題中）")
    print(f"モデル: {MODEL}（ローカル Ollama）")


if __name__ == "__main__":
    main()
