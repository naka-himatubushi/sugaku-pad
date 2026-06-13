"""MathAI Web ハーネス — 手書き/画像/LaTeX を OCR + SymPy で解く end-to-end 実証兼デモ。

ネイティブ iPad 版（`ios/`）の置き換えではない。全パイプライン（手書き→認識→求解→表示）を
初めて通しで動かす検証ハーネスであり、Xcode 導入を待つ間 iPad Safari で使える暫定デモ。

起動: .venv/bin/uvicorn web.server:app --host 0.0.0.0 --port 8000
"""
import base64
import datetime
import io
import json
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root → mathai を import
from mathai.solver import solve_latex

app = FastAPI(title="MathAI Web")
_INDEX = Path(__file__).parent / "index.html"
_CAPTURES = Path(__file__).parent / "captures"  # 手書き画像と結果ログの保存先（Claude が把握できるよう）
_CAPTURES.mkdir(exist_ok=True)
_ocr = None  # pix2tex は重いので遅延ロード


def _get_ocr():
    global _ocr
    if _ocr is None:
        from pix2tex.cli import LatexOCR
        _ocr = LatexOCR()
    return _ocr


class SolveRequest(BaseModel):
    latex: str | None = None
    image: str | None = None  # data URL もしくは base64 PNG


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _INDEX.read_text(encoding="utf-8")


@app.post("/solve")
def solve(req: SolveRequest) -> dict:
    latex = (req.latex or "").strip()
    source = "text"
    image_name = None
    if not latex and req.image:
        source = "handwriting"
        data = base64.b64decode(req.image.split(",", 1)[-1])  # data URL を許容
        image_name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".png"
        (_CAPTURES / image_name).write_bytes(data)  # 書いた手書き画像を保存
        latex = _get_ocr()(Image.open(io.BytesIO(data)))

    if latex:
        result = solve_latex(latex)
    else:
        result = {"supported": False, "kind": "", "steps": [], "answer": []}

    _log(source, image_name, latex, result)
    return {"latex": latex, **result}


def _log(source: str, image_name: str | None, latex: str, result: dict) -> None:
    """各リクエストを captures/log.jsonl に記録（Claude が後から把握できるよう）。"""
    entry = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "image": image_name,
        "latex": latex,
        "supported": result["supported"],
        "kind": result["kind"],
        "answer": result["answer"],
    }
    with (_CAPTURES / "log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
