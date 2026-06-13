"""Web ハーネスの end-to-end スモークテスト（テキスト経路＋画像OCR経路）。

サーバ起動後に実行: .venv/bin/python web/smoke_test.py
"""
import base64
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8077"
IMG = Path(__file__).resolve().parents[1] / "spikes/ocr/dataset/img/q01.png"


def wait_ready(timeout=30):
    for _ in range(timeout * 2):
        try:
            if httpx.get(BASE + "/", timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    assert wait_ready(), "サーバが起動しない"
    print("server up ✓")

    # 1) テキスト経路（二次）
    r = httpx.post(BASE + "/solve", json={"latex": "x^{2} - 5x + 6 = 0"}, timeout=30).json()
    print("text quadratic:", r["kind"], r["answer"])
    assert set(r["answer"]) == {"2", "3"}, r

    # 2) テキスト経路（θ 三角）
    r = httpx.post(BASE + "/solve", json={"latex": "2\\sin\\theta = 1"}, timeout=30).json()
    print("text trig θ:", r["kind"], r["answer"])
    assert set(r["answer"]) == {"pi/6", "5*pi/6"}, r

    # 3) 画像 OCR 経路（合成画像 q01.png = 2x+3=7）— 初回はモデルロードで時間がかかる
    b64 = base64.b64encode(IMG.read_bytes()).decode()
    r = httpx.post(BASE + "/solve", json={"image": b64}, timeout=180).json()
    print("image OCR:", repr(r["latex"]), "→", r["kind"], r["answer"])
    assert r["supported"] and r["answer"] == ["2"], r

    print("\n✅ end-to-end OK: テキスト・θ・画像OCR の3経路すべて求解成功")


if __name__ == "__main__":
    main()
