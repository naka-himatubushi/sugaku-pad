"""mathai の CLI デモ — Xcode/iPad 無しで Solve の頭脳を今すぐ試すための入口。

使い方:
    python -m mathai "2x + 3 = 7"
    python -m mathai "\\frac{x}{2} + 1 = 4"
    python -m mathai            # 引数なしで対話モード
"""
import sys

from .solver import solve_latex


def _show(query: str) -> None:
    r = solve_latex(query)
    if not r["supported"]:
        print(f"  ✗ 解けません（対応範囲外）: {query!r}")
        return
    print(f"  種別: {r['kind']}")
    for i, step in enumerate(r["steps"], 1):
        print(f"   {i}. {step}")
    print(f"  答え: {', '.join(r['answer'])}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args:
        _show(" ".join(args))
        return 0
    # 対話モード
    print("mathai Solve デモ（空行 / Ctrl-D で終了）。数式または LaTeX を入力:")
    try:
        while True:
            line = input("> ").strip()
            if not line:
                break
            _show(line)
    except EOFError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
