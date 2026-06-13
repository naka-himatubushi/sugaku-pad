"""Spike A 補助: labels.json の LaTeX を matplotlib mathtext で PNG にレンダリングする。

注意: これは「印刷体（きれいにレンダリングした）数式」であり、実機の手書きではない。
本ゲート（実 Pencil 入力での 80% 精度）には iPad での手書き収集が別途必要。
このスクリプトは OCR パイプライン疎通と pix2tex のベースライン精度測定用。
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent / "dataset"


def render(latex: str, out_path: Path) -> None:
    fig = plt.figure(figsize=(4, 1.2))
    fig.text(0.5, 0.5, f"${latex}$", ha="center", va="center", fontsize=28)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


def main() -> None:
    labels = json.loads((HERE / "labels.json").read_text())
    img_dir = HERE / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    for fname, latex in labels.items():
        render(latex, img_dir / fname)
        print(f"rendered {fname}: {latex}")
    print(f"\n{len(labels)} 枚を {img_dir} に生成")


if __name__ == "__main__":
    main()
