"""mathai — Goodnotes AI for Math クローンの計算コア（Solve 機能の頭脳）。

完全 on-device 構成では、この純 Python パッケージを iOS に埋め込んで使う。
UI（PencilKit）や認識（OCR モデル）から独立した、テスト可能なコア。

公開 API:
    from mathai import latex_to_math, solve_equation, solve_latex, solve_image
"""
from .latex_input import latex_to_math
from .solver import solve_equation, solve_latex

__all__ = ["latex_to_math", "solve_equation", "solve_latex"]
