"""MathAI Web ハーネス — 手書き/画像/LaTeX を OCR + SymPy で解く end-to-end 実証兼デモ。

ネイティブ iPad 版（`ios/`）の置き換えではない。全パイプライン（手書き→認識→求解→表示）を
初めて通しで動かす検証ハーネスであり、Xcode 導入を待つ間 iPad Safari で使える暫定デモ。

起動: .venv/bin/uvicorn web.server:app --host 0.0.0.0 --port 8000
"""
import base64
import io
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
    if not latex and req.image:
        raw = req.image.split(",", 1)[-1]  # "data:image/png;base64,...." を許容
        image = Image.open(io.BytesIO(base64.b64decode(raw)))
        latex = _get_ocr()(image)
    if not latex:
        return {"latex": "", "supported": False, "kind": "", "steps": [], "answer": []}
    return {"latex": latex, **solve_latex(latex)}
