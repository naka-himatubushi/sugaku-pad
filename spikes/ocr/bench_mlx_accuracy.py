"""候補 VLM を MLX(実機と同じ 4bit ランタイム)で手書き OCR 精度測定する。

背景: Ollama ベンチ(3B/7B とも 5/5)は実機 MLX 4bit 3B の精度を予測できなかった
(実機で 2x^2-27x=250 を 2x^2-2x^2=2x^2 と誤読、同じ画像を Mac 7B は正答)。
そこで実機と同条件(mlx-vlm, 4bit)で候補を測り直し、8GB に載る中で最も読めるものを選ぶ。

指標: ①char 一致(正規化後) ②end-to-end 求解一致(mathai で解いて同答)。
実行: .venv/bin/python spikes/ocr/bench_mlx_accuracy.py
"""
import json
import sys
import time
from pathlib import Path

from mlx_vlm import generate, load
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mathai.solver import solve_latex  # noqa: E402

HERE = Path(__file__).parent / "handwriting_eval"
PROMPT = ("You are a precise math OCR. Transcribe the handwritten math expression into ONE line "
          "of LaTeX. Output ONLY the LaTeX, no explanation, no dollar signs, no code fences.")

# 第2ラウンド: 2.29.1 が依存追加なしで載せられる未試験候補 vs 現行ベスト 2B。
# (1回目: 3B-4bit=e2e4/6, 2B-4bit=6/6, SmolVLM=1/6, 3B-8bit=2/6, 7B-4bit=6/6)
MODELS = [
    "mlx-community/Qwen2-VL-2B-Instruct-4bit",           # 現行採用(基準・前回6/6)
    "lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit",  # 最新世代(期待大・~4B)
    "mlx-community/gemma-3-4b-it-qat-4bit",              # Gemma3 4B
    "mlx-community/paligemma-3b-mix-448-8bit",           # PaliGemma(OCR系)
]


def normalize(s: str) -> str:
    s = (s or "").lower()
    for t in ("\\left", "\\right", "\\,", "\\;", "\\!", "\\(", "\\)", "\\[", "\\]",
              "$", "{", "}", " ", "\\cdot", "*"):
        s = s.replace(t, "")
    return s.replace("\\", "")


def _text(out) -> str:
    return out if isinstance(out, str) else getattr(out, "text", str(out))


def _clean(t: str) -> str:
    for x in ("```latex", "```", "\\(", "\\)", "\\[", "\\]", "$$"):
        t = t.replace(x, "")
    return t.strip().strip("$").strip()


def run_model(mid: str, labels: dict) -> None:
    print(f"\n## {mid}", flush=True)
    try:
        model, processor = load(mid)
        config = load_config(mid)
    except Exception as e:  # noqa: BLE001
        print(f"  load 失敗(スキップ): {e}", flush=True)
        return
    char = e2e = solvable = 0
    n = len(labels)
    t0 = time.time()
    for fn, gt in labels.items():
        img = str(HERE / "img" / fn)
        try:
            fmt = apply_chat_template(processor, config, PROMPT, num_images=1)
        except TypeError:
            fmt = apply_chat_template(processor, config, PROMPT)
        try:
            out = generate(model, processor, fmt, image=img, max_tokens=80, verbose=False)
        except Exception as e:  # noqa: BLE001
            print(f"  {fn}: 生成失敗 {e}", flush=True)
            continue
        pred = _clean(_text(out))
        cm = normalize(pred) == normalize(gt)
        char += cm
        gtr, pr = solve_latex(gt), solve_latex(pred)
        ok = False
        if gtr["supported"]:
            solvable += 1
            ok = pr["supported"] and set(pr["answer"]) == set(gtr["answer"])
            e2e += ok
        print(f"  {fn}: {'C' if cm else '.'}{'S' if ok else '.'} gt={gt!r} pred={pred!r}", flush=True)
    print(f"  → char {char}/{n} ({char / n:.0%}) / e2e {e2e}/{solvable} / {time.time() - t0:.0f}s", flush=True)


def main() -> None:
    labels = json.loads((HERE / "labels.json").read_text())["labels"]
    print(f"手書き {len(labels)} 問を MLX 4bit ランタイムで測定", flush=True)
    for m in MODELS:
        run_model(m, labels)


if __name__ == "__main__":
    main()
