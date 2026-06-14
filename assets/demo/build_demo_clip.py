"""sugaku-pad デモ再現アニメ生成スクリプト。

MathAI のフロー(手書き → オンデバイス OCR → 確認カード → SymPy 求解 → 検算)を
再現したアニメを mp4 / gif に書き出す。

正直さの方針:
- 手書き入力は実データ(web capture の "2x^2-27x=250")。
- 求解の手順・解・検算結果は mathai(SymPy)の実出力。
- UI 表示はアプリの実画面ではなく「再現(イメージ)」。クリップ内にもその旨を明記する。

依存: Pillow / matplotlib(mathtext で数式描画) / numpy。ffmpeg で mp4・gif 化。
実行: uv run --with pillow --with matplotlib --with numpy python build_demo_clip.py
"""
import io
import os
import shutil
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
HANDWRITING = os.path.join(HERE, "handwriting.png")
OUTDIR = os.path.join(HERE, "out")
FRAMES = os.path.join(OUTDIR, "frames")

W, H = 1000, 640
FPS = 20

# 配色
BG = (250, 250, 248)
GRID = (225, 232, 240)
INK = (24, 24, 28)
ACCENT = (44, 110, 240)
GREEN = (28, 170, 110)
GRAY = (140, 144, 150)
CARD = (255, 255, 255)

JP_DIR = "/System/Library/Fonts"
F_W3 = os.path.join(JP_DIR, "ヒラギノ角ゴシック W3.ttc")
F_W6 = os.path.join(JP_DIR, "ヒラギノ角ゴシック W6.ttc")


def font(bold, size):
    return ImageFont.truetype(F_W6 if bold else F_W3, size)


# ---- 数式描画(matplotlib mathtext) ----
_math_cache = {}


def render_math(expr, fontsize=44, color="#18181c"):
    key = (expr, fontsize, color)
    if key in _math_cache:
        return _math_cache[key]
    fig = plt.figure()
    fig.patch.set_alpha(0)
    fig.text(0.5, 0.5, f"${expr}$", fontsize=fontsize, color=color, ha="center", va="center")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=220, transparent=True, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    buf.seek(0)
    img = Image.open(buf).convert("RGBA")
    _math_cache[key] = img
    return img


def render_text(text, fnt, color):
    """テキストを透明 PNG に描画して返す(行ごとの alpha 合成用)。"""
    tmp = Image.new("RGBA", (4, 4))
    d = ImageDraw.Draw(tmp)
    l, t, r, b = d.textbbox((0, 0), text, font=fnt)
    img = Image.new("RGBA", (r - l + 6, b - t + 6), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((3 - l, 3 - t), text, font=fnt, fill=color)
    return img


def prep_handwriting(target_w):
    """実手書き画像を黒ストローク・透明背景に変換し、指定幅へ縮小。"""
    hw = Image.open(HANDWRITING).convert("RGBA")
    arr = np.array(hw).astype(np.float32)
    lum = arr[..., :3].mean(axis=2)
    alpha = np.clip((235 - lum) / 235 * 255 * 2.2, 0, 255).astype(np.uint8)
    out = np.zeros_like(arr, dtype=np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = INK[0], INK[1], INK[2]
    out[..., 3] = alpha
    img = Image.fromarray(out, "RGBA")
    h = int(target_w * img.height / img.width)
    return img.resize((target_w, h), Image.LANCZOS)


def paste_alpha(base, overlay, pos, alpha=1.0):
    if alpha <= 0:
        return
    if alpha < 1.0:
        a = overlay.split()[3].point(lambda v: int(v * alpha))
        overlay = overlay.copy()
        overlay.putalpha(a)
    base.alpha_composite(overlay, (int(pos[0]), int(pos[1])))


def fit(img, max_w=None, max_h=None):
    """高 dpi 画像を指定枠に収まるよう縮小(拡大はしない=ぼけ防止)。"""
    w, h = img.size
    s = 1.0
    if max_w:
        s = min(s, max_w / w)
    if max_h:
        s = min(s, max_h / h)
    if s < 1.0:
        img = img.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    return img


def ease(t):
    return t * t * (3 - 2 * t)  # smoothstep


HW = prep_handwriting(540)
HW_POS = ((W - HW.width) // 2, 78)


def base_canvas():
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 36):
        d.line([(x, 58), (x, H - 42)], fill=GRID, width=1)
    for y in range(58, H - 42, 36):
        d.line([(0, y), (W, y)], fill=GRID, width=1)
    # 上部バー
    d.rectangle([0, 0, W, 56], fill=(255, 255, 255))
    d.line([(0, 56), (W, 56)], fill=(232, 234, 238), width=2)
    d.ellipse([20, 20, 38, 38], fill=ACCENT)
    d.text((48, 28), "sugaku-pad — 数学パッド", font=font(True, 22), fill=INK, anchor="lm")
    # On-device バッジ
    badge = "● 完全オンデバイス・通信なし"
    bw = d.textlength(badge, font=font(True, 17))
    d.rounded_rectangle([W - bw - 36, 16, W - 16, 42], radius=13, fill=(238, 246, 255))
    d.text((W - 26, 29), badge, font=font(True, 17), fill=ACCENT, anchor="rm")
    # フッタ(正直ラベル)
    foot = "再現アニメ｜手書き入力と求解結果は実データ／UI 表示はイメージ"
    d.text((W // 2, H - 21), foot, font=font(False, 16), fill=GRAY, anchor="mm")
    return img, d


def draw_card(img, box, radius=22, shadow=True):
    x0, y0, x1, y1 = box
    if shadow:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + 8, x1, y1 + 8], radius=radius, fill=(0, 0, 0, 60))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(img).rounded_rectangle(box, radius=radius, fill=CARD, outline=(232, 234, 238), width=2)


def spinner(d, cx, cy, r, t):
    start = (t * 360 * 2) % 360
    d.arc([cx - r, cy - r, cx + r, cy + r], start, start + 270, fill=ACCENT, width=6)


def draw_handwriting(img, reveal=1.0, pencil=False):
    if reveal >= 1.0:
        img.alpha_composite(HW, HW_POS)
    else:
        w = max(1, int(HW.width * reveal))
        img.alpha_composite(HW.crop((0, 0, w, HW.height)), HW_POS)
    if pencil:
        px = HW_POS[0] + int(HW.width * reveal)
        py = HW_POS[1] + HW.height - 18
        ImageDraw.Draw(img).ellipse([px - 7, py - 7, px + 7, py + 7], fill=ACCENT)


def label_chip(img, text, x, y, color):
    d = ImageDraw.Draw(img)
    tw = d.textlength(text, font=font(True, 18))
    # ImageDraw は alpha 塗りを合成せず置換するため、白寄りの淡色ベタを自前で作る
    tint = tuple(int(c * 0.18 + 255 * 0.82) for c in color)
    d.rounded_rectangle([x, y, x + tw + 22, y + 30], radius=11, fill=tint)
    d.text((x + 11, y + 15), text, font=font(True, 18), fill=color, anchor="lm")
    return tw + 22


# 実エンジン出力(2x^2-27x=250) を内容にする
EQ_MATH = render_math(r"2x^2 - 27x = 250", fontsize=58)
ROWS = [
    {"label": "解の公式", "color": ACCENT, "img": render_math(r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}", 40)},
    {"label": "係数", "color": ACCENT, "img": render_text("a = 2 ,  b = −27 ,  c = −250", font(False, 28), INK)},
    {"label": "判別式", "color": ACCENT, "img": render_math(r"D = b^2 - 4ac = 2729", 38)},
    {"label": "解", "color": ACCENT, "img": render_math(r"x = \frac{27 \pm \sqrt{2729}}{4}", 44)},
    {"label": "検算 ✓", "color": GREEN, "img": render_text("代入して両辺一致", font(True, 28), GREEN)},
]


# ---- 各シーン ----
def scene_write(t):
    img, d = base_canvas()
    r = ease(min(1.0, t * 1.15))
    draw_handwriting(img, reveal=r, pencil=r < 1.0)
    d.text((W // 2, H - 70), "① 手書きで数式を書く", font=font(True, 22), fill=GRAY, anchor="mm")
    return img


def scene_recognize(t):
    img, d = base_canvas()
    draw_handwriting(img, 1.0)
    ov = Image.new("RGBA", (W, H), (255, 255, 255, 150))
    img.alpha_composite(ov)
    spinner(ImageDraw.Draw(img), W // 2, H // 2 - 30, 26, t)
    d.text((W // 2, H // 2 + 30), "手書きを認識中…", font=font(True, 30), fill=INK, anchor="mm")
    d.text((W // 2, H // 2 + 70), "オンデバイス VLM（MLX Qwen2-VL 2B）", font=font(False, 20), fill=GRAY, anchor="mm")
    return img


def _card_with_eq(img, slide_y):
    box = [120, slide_y, W - 120, slide_y + 300]
    draw_card(img, box)
    d = ImageDraw.Draw(img)
    d.text((150, slide_y + 34), "認識結果を確認", font=font(True, 24), fill=INK, anchor="lm")
    eq = fit(EQ_MATH, max_w=W - 360, max_h=96)
    paste_alpha(img, eq, ((W - eq.width) // 2, slide_y + 108 - eq.height // 2))
    d.text((W // 2, slide_y + 196), "誤読はここで人が訂正できる（確認カード）", font=font(False, 19), fill=GRAY, anchor="mm")
    d.rounded_rectangle([W // 2 - 74, slide_y + 232, W // 2 + 74, slide_y + 278], radius=16, fill=ACCENT)
    d.text((W // 2, slide_y + 255), "✓ 確認", font=font(True, 22), fill=(255, 255, 255), anchor="mm")


def scene_confirm(t):
    img, _ = base_canvas()
    draw_handwriting(img, 1.0)
    target = 250
    slide = int(H - (H - target) * ease(min(1.0, t * 2.2)))
    _card_with_eq(img, slide)
    return img


def scene_solve_spin(t):
    img, d = base_canvas()
    draw_handwriting(img, 1.0)
    box = [120, 250, W - 120, 550]
    draw_card(img, box)
    spinner(ImageDraw.Draw(img), W // 2, 360, 24, t)
    d.text((W // 2, 420), "計算中…", font=font(True, 28), fill=INK, anchor="mm")
    d.text((W // 2, 458), "端末内 Python + SymPy", font=font(False, 20), fill=GRAY, anchor="mm")
    return img


def scene_result(t):
    img, d = base_canvas()
    draw_handwriting(img, 1.0)
    box = [90, 238, W - 90, 596]
    draw_card(img, box)
    d.text((120, 268), "求解 & 検算（SymPy・決定論）", font=font(True, 23), fill=INK, anchor="lm")
    y0 = 312
    row_h = 54
    for i, row in enumerate(ROWS):
        appear = (t - (0.05 + i * 0.15)) / 0.2
        a = max(0.0, min(1.0, appear))
        if a <= 0:
            continue
        ea = ease(a)
        y = y0 + i * row_h + int((1 - ea) * 14)
        chw = label_chip(img, row["label"], 120, y, row["color"])
        c = fit(row["img"], max_w=600, max_h=44)
        paste_alpha(img, c, (120 + chw + 18, y + 15 - c.height // 2), ea)
    return img


def scene_outro(t):
    img = scene_result(1.0)
    a = ease(min(1.0, t * 1.6))
    img.alpha_composite(Image.new("RGBA", (W, H), (12, 14, 22, int(247 * a))))

    def line(y, text, fnt, col):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((W // 2, y), text, font=fnt, fill=col, anchor="mm")
        paste_alpha(img, layer, (0, 0), a)

    line(H // 2 - 88, "完全オンデバイス・通信ゼロ", font(True, 42), (255, 255, 255))
    line(H // 2 - 32, "読む（ローカル VLM / MLX）→ 確認 → 解く（SymPy）→ 検算 ✓", font(False, 23), (212, 222, 242))
    line(H // 2 + 22, "クラウド型の既存サービスと違い、データは端末の外に出ない", font(False, 21), (150, 200, 255))
    line(H // 2 + 76, "研究テーマ：ローカル限定の LLM で手書き数学はどこまでいけるか", font(False, 21), (150, 200, 255))
    return img


def contrast_box(layer, box, title, body, accent):
    d = ImageDraw.Draw(layer)
    bg = (238, 246, 255) if accent else (244, 245, 247)
    edge = ACCENT if accent else (222, 224, 228)
    d.rounded_rectangle(box, radius=18, fill=bg, outline=edge, width=2)
    cx = (box[0] + box[2]) // 2
    d.text((cx, box[1] + 36), title, font=font(True, 24), fill=(ACCENT if accent else INK), anchor="mm")
    yy = box[1] + 80
    for ln in body:
        d.text((cx, yy), ln, font=font(False, 19), fill=(INK if accent else GRAY), anchor="mm")
        yy += 30


def scene_intro(t):
    img, _ = base_canvas()

    def line(y, text, fnt, col, a):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((W // 2, y), text, font=fnt, fill=col, anchor="mm")
        paste_alpha(img, layer, (0, 0), a)

    line(148, "完全オンデバイスの手書き数学ノート", font(True, 38), INK, ease(min(1.0, t / 0.4)))
    line(200, "読む（ローカル LLM）も 解く（SymPy）も、iPad の中だけ。通信ゼロ。",
         font(False, 21), GRAY, ease(max(0.0, min(1.0, (t - 0.22) / 0.4))))
    pa = ease(max(0.0, min(1.0, (t - 0.45) / 0.4)))
    if pa > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        contrast_box(layer, [100, 300, 470, 472], "クラウド型の既存サービス",
                     ["認識・求解をサーバへ送信", "ネット必須・データが外に出る"], False)
        contrast_box(layer, [530, 300, 900, 472], "sugaku-pad",
                     ["100% オンデバイス", "機内モードでも動く・送信ゼロ"], True)
        ImageDraw.Draw(layer).text((W // 2, 386), "≠", font=font(True, 44), fill=GRAY, anchor="mm")
        paste_alpha(img, layer, (0, 0), pa)
    return img


SCENES = [
    (scene_intro, 2.6),
    (scene_write, 2.2),
    (scene_recognize, 1.0),
    (scene_confirm, 2.0),
    (scene_solve_spin, 0.8),
    (scene_result, 4.2),
    (scene_outro, 2.8),
]


def main():
    if os.path.exists(FRAMES):
        shutil.rmtree(FRAMES)
    os.makedirs(FRAMES, exist_ok=True)
    idx = 0
    keyframes = {}
    for si, (fn, dur) in enumerate(SCENES):
        n = max(1, int(dur * FPS))
        for k in range(n):
            t = k / max(1, n - 1)
            frame = fn(t).convert("RGB")
            frame.save(os.path.join(FRAMES, f"f{idx:04d}.png"))
            idx += 1
        keyframes[fn.__name__] = idx - 1
    print(f"frames: {idx}  keyframes: {keyframes}")

    mp4 = os.path.join(OUTDIR, "demo.mp4")
    gif = os.path.join(OUTDIR, "demo.gif")
    pal = os.path.join(OUTDIR, "palette.png")
    subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(FRAMES, "f%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", "scale=1000:-2", mp4], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", mp4, "-vf", "fps=13,scale=760:-1:flags=lanczos,palettegen=max_colors=128",
                    pal], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", mp4, "-i", pal, "-lavfi",
                    "fps=13,scale=760:-1:flags=lanczos[x];[x][1:v]paletteuse", gif], check=True)
    for f in (mp4, gif):
        print(f, os.path.getsize(f) // 1024, "KB")


if __name__ == "__main__":
    main()
