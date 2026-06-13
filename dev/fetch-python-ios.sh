#!/usr/bin/env bash
# 埋め込み用 CPython（BeeWare Python-Apple-support, iOS 版）を取得・展開する。
# ios/vendor/ は git 管理外なので、クローン後にこれで用意する。
# その後 dev/build-python-payload.sh → xcodegen generate でビルド可能になる。
set -euo pipefail
cd "$(dirname "$0")/.."

VER="3.13-b14"
FILE="Python-3.13-iOS-support.b14.tar.gz"
URL="https://github.com/beeware/Python-Apple-support/releases/download/${VER}/${FILE}"

mkdir -p ios/vendor/python-apple-support
TARBALL="ios/vendor/${FILE}"
if [ ! -f "$TARBALL" ]; then
  echo "DL: $URL"
  curl -sL -o "$TARBALL" "$URL"
fi
tar xzf "$TARBALL" -C ios/vendor/python-apple-support
echo "準備完了: ios/vendor/python-apple-support/Python.xcframework"
echo "次: dev/build-python-payload.sh && xcodegen generate"
