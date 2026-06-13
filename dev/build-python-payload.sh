#!/usr/bin/env bash
# 埋め込み Python のうち「自前コード」と「依存パッケージ」だけを用意する。
#   app/           … 自前コード（mathai パッケージ + bridge.py）
#   app_packages/  … pip 依存（sympy / mpmath … 純Pythonで版非依存）
# 標準ライブラリと lib-dynload はビルド時に公式スクリプト install_python が
# xcframework から配置・フレームワーク化するので、ここでは用意しない。
# 生成物は git 管理せず本スクリプトで再生成する。
#
# 使い方: dev/build-python-payload.sh
set -euo pipefail
cd "$(dirname "$0")/.."

DEST="ios/python-ios"
rm -rf "$DEST"
mkdir -p "$DEST/app" "$DEST/app_packages"

# 依存(sympy→mpmath)。純Pythonなので Mac の pip で --target でよい
.venv/bin/pip install --quiet --target "$DEST/app_packages" sympy >/dev/null

# 自前パッケージ + Swift から呼ぶ bridge.py
cp -R mathai "$DEST/app/mathai"
cp ios/python_app/*.py "$DEST/app/"

# 軽量化: テスト/キャッシュ/配布メタを削る
find "$DEST" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "$DEST" -type d -name 'tests' -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf "$DEST"/app_packages/*.dist-info 2>/dev/null || true

echo "payload 完成:"
du -sh "$DEST"/app_packages "$DEST"/app 2>/dev/null
echo "sympy import 確認(Mac の venv で):"
.venv/bin/python -c "import sys; sys.path.insert(0,'$DEST/app_packages'); sys.path.insert(0,'$DEST/app'); import sympy, mathai.solver as s; print('  sympy', sympy.__version__, '/ solve:', s.solve_latex('2x+3=7')['answer'])"
