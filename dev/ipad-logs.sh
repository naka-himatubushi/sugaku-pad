#!/usr/bin/env bash
# Mac から iPad(実機) の MathAI アプリのログをリアルタイム監視する開発ツール。
# os_log(Logger) 出力を sudo なしで拾える(libimobiledevice の idevicesyslog 利用)。
#
# 前提: brew install libimobiledevice / iPad を有線接続し「信頼」済み。
# 使い方:
#   dev/ipad-logs.sh                 # MathAI の全ログを流す
#   dev/ipad-logs.sh MLX-BENCH       # "MLX-BENCH" を含む行だけ(ベンチ結果の回収に)
#   dev/ipad-logs.sh > /tmp/run.log  # ファイルに保存
set -euo pipefail

UDID="$(idevice_id -l | head -1)"
if [ -z "${UDID}" ]; then
  echo "iPad が見つからない。有線接続と『このコンピュータを信頼』を確認。" >&2
  exit 1
fi

PATTERN="${1:-}"
echo "監視中: device=${UDID} process=MathAI ${PATTERN:+filter=$PATTERN}" >&2

if [ -n "${PATTERN}" ]; then
  idevicesyslog -u "${UDID}" -p MathAI | grep --line-buffered -i "${PATTERN}"
else
  idevicesyslog -u "${UDID}" -p MathAI
fi
