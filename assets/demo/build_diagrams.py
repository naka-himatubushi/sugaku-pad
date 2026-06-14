"""README 用の「動く図」を生成する。

- pipeline.gif … 仕組み(2 本柱＋二層の信頼性)。手書き→読む→確認→解く+検算→表示を
  トークンが流れて各段が点灯。確認=OCR 誤りを人が、検算=計算ミスを機械が捕まえる、を明示。
- mathai.gif  … 計算コアの振り分け。入力→正規化→種別判定→各種別→解→検算 を、
  実例(一次/二次/連立/不等式)を順に流して経路が光る。

Mermaid の静止図を、読みやすい動的アニメに置き換えるのが目的。
実行: uv run --with pillow --with matplotlib --with numpy python build_diagrams.py
"""
import io
import math
import os
import shutil
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out_diag")

BG = (250, 250, 248)
INK = (28, 28, 32)
GRAY = (150, 154, 160)
ACCENT = (44, 110, 240)
GREEN = (28, 170, 110)
ORANGE = (228, 146, 38)
PURPLE = (132, 104, 216)
NEUT = (92, 98, 110)
DIM_FILL = (246, 247, 249)
DIM_EDGE = (223, 225, 229)
DIM_TEXT = (176, 178, 184)

F = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
FB = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
FPS = 12


def font(bold, size):
    return ImageFont.truetype(FB if bold else F, size)


_mcache = {}


def render_math(expr, fontsize, color="#1c7a4b"):
    key = (expr, fontsize, color)
    if key in _mcache:
        return _mcache[key]
    fig = plt.figure()
    fig.patch.set_alpha(0)
    fig.text(0.5, 0.5, f"${expr}$", fontsize=fontsize, color=color, ha="center", va="center")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, transparent=True, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    buf.seek(0)
    img = Image.open(buf).convert("RGBA")
    _mcache[key] = img
    return img


def fit(img, max_w, max_h):
    s = min(max_w / img.width, max_h / img.height, 1.0)
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS) if s < 1 else img


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def tint(color):
    return tuple(int(c * 0.16 + 255 * 0.84) for c in color)


def draw_node(img, box, lines, active, color):
    d = ImageDraw.Draw(img)
    if active:
        d.rounded_rectangle(box, radius=14, fill=tint(color), outline=color, width=3)
        tcol = INK
    else:
        d.rounded_rectangle(box, radius=14, fill=DIM_FILL, outline=DIM_EDGE, width=2)
        tcol = DIM_TEXT
    cx = (box[0] + box[2]) // 2
    cy = (box[1] + box[3]) // 2
    fs = 20 if len(lines) <= 2 else 17
    lh = fs + 5
    y = cy - (len(lines) - 1) * lh / 2
    for i, ln in enumerate(lines):
        d.text((cx, y), ln, font=font(i == 0, fs), fill=(color if (active and i == 0) else tcol), anchor="mm")
        y += lh


def arrow(img, p0, p1, active):
    d = ImageDraw.Draw(img)
    col = ACCENT if active else (212, 214, 220)
    w = 4 if active else 2
    d.line([p0, p1], fill=col, width=w)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for da in (2.6, -2.6):
        d.line([p1, (p1[0] - 12 * math.cos(ang - da), p1[1] - 12 * math.sin(ang - da))], fill=col, width=w)


def make_gif(frames_dir, out, scale=880):
    pal = out + ".pal.png"
    base = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "f%04d.png")]
    subprocess.run(base + ["-vf", f"scale={scale}:-1:flags=lanczos,palettegen=stats_mode=diff", pal], check=True)
    subprocess.run(base + ["-i", pal, "-lavfi",
                           f"scale={scale}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3", out],
                   check=True)
    os.remove(pal)
    print(out, os.path.getsize(out) // 1024, "KB")


def render(frames_dir, frame_fn, total):
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)
    for i in range(total):
        frame_fn(i / total).convert("RGB").save(os.path.join(frames_dir, f"f{i:04d}.png"))


# ====================== pipeline.gif ======================
PW, PH = 1000, 430
P_NODES = [
    {"box": [25, 150, 175, 270], "color": NEUT, "lines": ["手書き", "入力"]},
    {"box": [225, 150, 375, 270], "color": ORANGE, "lines": ["① 読む", "確率的", "ローカル VLM"]},
    {"box": [425, 150, 575, 270], "color": PURPLE, "lines": ["② 確認カード", "人が修正"]},
    {"box": [625, 150, 775, 270], "color": ACCENT, "lines": ["③ 解く + 検算", "決定論・SymPy"]},
    {"box": [825, 150, 975, 270], "color": NEUT, "lines": ["④ 表示", "数式カード"]},
]
P_CAP = {2: "誤読（OCR）はここで人が捕まえる", 3: "計算ミスはここで機械が検算で捕まえる"}


def pipeline_frame(t):
    img = Image.new("RGBA", (PW, PH), BG + (255,))
    d = ImageDraw.Draw(img)
    d.text((PW // 2, 44), "仕組み — 2 本柱（確率的に読む ／ 決定論で解く）＋ 二層の信頼性",
           font=font(True, 26), fill=INK, anchor="mm")
    # reveal 進行(前半75%で 5 ノードを点灯、後半hold)
    p = ease(min(1.0, t / 0.78)) * (len(P_NODES) - 1)
    nactive = int(math.floor(p + 0.5)) + 1
    # arrows
    for i in range(len(P_NODES) - 1):
        a = P_NODES[i]["box"]
        b = P_NODES[i + 1]["box"]
        arrow(img, (a[2], 210), (b[0], 210), active=(i + 1) < nactive)
    # nodes
    for i, n in enumerate(P_NODES):
        draw_node(img, n["box"], n["lines"], active=(i < nactive), color=n["color"])
    # token(光る点)
    seg = min(p, len(P_NODES) - 1)
    i0 = int(math.floor(seg))
    f = seg - i0
    x0 = (P_NODES[i0]["box"][0] + P_NODES[i0]["box"][2]) / 2
    x1 = (P_NODES[min(i0 + 1, len(P_NODES) - 1)]["box"][0] + P_NODES[min(i0 + 1, len(P_NODES) - 1)]["box"][2]) / 2
    tx = x0 + (x1 - x0) * f
    if p < len(P_NODES) - 1 - 1e-3:  # 到達後(hold)はトークンを消す
        d.ellipse([tx - 9, 210 - 9, tx + 9, 210 + 9], fill=ACCENT, outline=(255, 255, 255), width=2)
    # captions(二層の要)
    for idx, cap in P_CAP.items():
        if idx < nactive:
            cx = (P_NODES[idx]["box"][0] + P_NODES[idx]["box"][2]) // 2
            col = P_NODES[idx]["color"]
            yy = 300 if idx == 2 else 336
            d.text((cx, yy), cap, font=font(True, 17), fill=col, anchor="mm")
    d.text((PW // 2, 398), "二層の信頼性 ＝ ② 人の確認（読み違いを救う）＋ ③ 機械の検算（計算を保証）。役割が違う。",
           font=font(False, 18), fill=GRAY, anchor="mm")
    return img


# ====================== mathai.gif ======================
MW, MH = 1000, 560
M_NODES = {
    "IN": ([320, 42, 680, 88], NEUT, None),
    "NORM": ([395, 96, 605, 142], ACCENT, ["正規化"]),
    "DEC": ([380, 166, 620, 220], ACCENT, ["種別を判定"]),
    "SYS": ([70, 250, 250, 306], ACCENT, ["連立"]),
    "INQ": ([290, 250, 470, 306], ACCENT, ["不等式"]),
    "EQ": ([510, 250, 690, 306], ACCENT, ["方程式"]),
    "EXPR": ([730, 250, 930, 306], ACCENT, ["式"]),
    "LIN": ([468, 338, 596, 392], ACCENT, ["1次"]),
    "QUA": ([604, 338, 732, 392], ACCENT, ["2次"]),
    "SOL": ([390, 430, 610, 478], ACCENT, ["解"]),
    "VF": ([355, 504, 645, 552], GREEN, ["検算 ✓ → 出力"]),
}
M_EDGES = [("IN", "NORM"), ("NORM", "DEC"), ("DEC", "SYS"), ("DEC", "INQ"), ("DEC", "EQ"),
           ("DEC", "EXPR"), ("EQ", "LIN"), ("EQ", "QUA"), ("SYS", "SOL"), ("INQ", "SOL"),
           ("LIN", "SOL"), ("QUA", "SOL"), ("EXPR", "SOL"), ("SOL", "VF")]
M_EXAMPLES = [
    {"expr": "2x + 3 = 7", "path": ["IN", "NORM", "DEC", "EQ", "LIN", "SOL", "VF"], "ans": r"x = 2"},
    {"expr": "x² − 5x + 6 = 0", "path": ["IN", "NORM", "DEC", "EQ", "QUA", "SOL", "VF"], "ans": r"x = 2,\ 3"},
    {"expr": "x + y = 3 ;  x − y = 1", "path": ["IN", "NORM", "DEC", "SYS", "SOL", "VF"], "ans": r"x = 2,\ y = 1"},
    {"expr": "2x + 3 > 7", "path": ["IN", "NORM", "DEC", "INQ", "SOL", "VF"], "ans": r"x > 2"},
]


def _edge_pts(a, b):
    ba, bb = M_NODES[a][0], M_NODES[b][0]
    return ((ba[0] + ba[2]) / 2, ba[3]), ((bb[0] + bb[2]) / 2, bb[1])


def mathai_frame(t):
    n = len(M_EXAMPLES)
    pos = t * n
    ei = min(int(math.floor(pos)), n - 1)
    lp = pos - ei
    ex = M_EXAMPLES[ei]
    path = ex["path"]
    revealed = path[: max(1, int(math.ceil(ease(min(1.0, lp / 0.6)) * len(path))))]
    active = set(revealed)
    pairs = {(path[i], path[i + 1]) for i in range(len(path) - 1)}

    img = Image.new("RGBA", (MW, MH), BG + (255,))
    d = ImageDraw.Draw(img)
    d.text((MW // 2, 18), "計算コア mathai — 入力を種別ごとに振り分け、解いて必ず検算する",
           font=font(True, 22), fill=INK, anchor="mm")
    # edges
    for a, b in M_EDGES:
        p0, p1 = _edge_pts(a, b)
        arrow(img, p0, p1, active=((a, b) in pairs and a in active and b in active))
    # nodes
    for key, (box, color, lines) in M_NODES.items():
        if key == "IN":
            draw_node(img, box, [ex["expr"]], active=True, color=NEUT)
        else:
            draw_node(img, box, lines, active=(key in active), color=color)
    # 答え(検算が点いたら表示)
    if "VF" in active:
        am = fit(render_math(ex["ans"], 34), 300, 44)
        chip = [665, 430, 960, 478]
        d.rounded_rectangle(chip, radius=12, fill=tint(GREEN), outline=GREEN, width=2)
        img.alpha_composite(am, (chip[0] + (300 - am.width) // 2, 430 + (48 - am.height) // 2))
    # 例インジケータ
    for i in range(n):
        cxx = MW // 2 - (n - 1) * 16 + i * 32
        d.ellipse([cxx - 6, 540, cxx + 6, 552], fill=(ACCENT if i == ei else (210, 212, 218)))
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    render(os.path.join(OUT, "pipe"), pipeline_frame, int(7.0 * FPS))
    make_gif(os.path.join(OUT, "pipe"), os.path.join(HERE, "pipeline.gif"))
    render(os.path.join(OUT, "math"), mathai_frame, int(11.2 * FPS))
    make_gif(os.path.join(OUT, "math"), os.path.join(HERE, "mathai.gif"))


if __name__ == "__main__":
    main()
