"""MLX(mlx-vlm) で qwen2.5-VL を動かし、手書き OCR の warm latency を計測する。

Ollama(warm ~1.8s) との比較用。load 後に 2 回推論し、2回目を warm とみなす。
初回は MLX 形式モデル(~4-5GB)を HuggingFace からDLする。

実行: .venv/bin/python spikes/ocr/bench_mlx.py
"""
import time
from pathlib import Path

from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

MODEL = "mlx-community/Qwen2.5-VL-7B-Instruct-4bit"
IMG = str(Path(__file__).parent / "handwriting_eval/img/h2.png")  # 手書き 2x+19=9
PROMPT = ("Transcribe the handwritten math expression into ONE line of LaTeX. "
          "Output only the LaTeX, no explanation, no dollar signs.")


def _text(out) -> str:
    if isinstance(out, str):
        return out
    return getattr(out, "text", str(out))


def main() -> None:
    t0 = time.time()
    model, processor = load(MODEL)
    config = load_config(MODEL)
    print(f"model load: {time.time() - t0:.1f}s")

    try:
        fmt = apply_chat_template(processor, config, PROMPT, num_images=1)
    except TypeError:
        fmt = apply_chat_template(processor, config, PROMPT)

    for i in range(2):
        t = time.time()
        out = generate(model, processor, fmt, image=IMG, max_tokens=64, verbose=False)
        print(f"run{i} (warm={i == 1}): {time.time() - t:.2f}s  -> {_text(out).strip()[:80]!r}")


if __name__ == "__main__":
    main()
