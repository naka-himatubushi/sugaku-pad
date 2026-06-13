#!/usr/bin/env bash
# 埋め込み Python のバンドル用ペイロードを組み立てる。
#   python/        … PYTHONHOME（標準ライブラリ + シミュレータ用 lib-dynload）
#   app/           … 自前コード（mathai パッケージ）
#   app_packages/  … pip 依存（sympy / mpmath … いずれも純Pythonで版非依存）
# 生成物は大きい(数十MB)ので git 管理せず、本スクリプトで再生成する。
#
# 使い方: dev/build-python-payload.sh
set -euo pipefail
cd "$(dirname "$0")/.."

SUP="ios/vendor/python-apple-support/Python.xcframework"
DEST="ios/python-ios"
PYV="python3.13"
SIM_SLICE="ios-arm64_x86_64-simulator"   # まずシミュレータ(arm64)で実証

rm -rf "$DEST"
mkdir -p "$DEST/python/lib" "$DEST/app" "$DEST/app_packages"

# 1) 標準ライブラリ(純Python, 全スライス共通)
cp -R "$SUP/lib/$PYV" "$DEST/python/lib/$PYV"
# 2) C 拡張(lib-dynload) はスライス別。シミュレータ arm64 を入れる
cp -R "$SUP/$SIM_SLICE/lib-arm64/$PYV/lib-dynload" "$DEST/python/lib/$PYV/lib-dynload"

# 3) 依存(sympy→mpmath)。純Pythonなので Mac の pip で --target でよい
.venv/bin/pip install --quiet --target "$DEST/app_packages" sympy >/dev/null

# 4) 自前パッケージ + Swift から呼ぶ bridge.py
cp -R mathai "$DEST/app/mathai"
cp ios/python_app/*.py "$DEST/app/"

# 5) 軽量化: テスト/キャッシュ/配布メタを削る
find "$DEST" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "$DEST" -type d -name 'tests' -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf "$DEST"/app_packages/*.dist-info 2>/dev/null || true

echo "payload 完成:"
du -sh "$DEST"/python "$DEST"/app_packages "$DEST"/app 2>/dev/null
echo "sympy import 確認(Mac の venv で):"
.venv/bin/python -c "import sys; sys.path.insert(0,'$DEST/app_packages'); sys.path.insert(0,'$DEST/app'); import sympy, mathai.solver as s; print('  sympy', sympy.__version__, '/ solve:', s.solve_latex('2x+3=7')['answer'])"
