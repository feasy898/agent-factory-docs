#!/bin/bash
# sc3_run.sh <root> <par> — 一轮 SC3 派发。配额熔断时后续 job 秒退(42)，由 watcher 自愈重拉。
set -uo pipefail
ROOT="$1"; PAR="${2:-2}"
SC="$(dirname "$ROOT")"
LIST="$ROOT/jobs-driver.txt"
[ -f "$LIST" ] || { echo "no jobs-driver.txt"; exit 0; }
command -v ~/.npm-global/bin/zcode >/dev/null 2>&1 || { echo "FATAL_NO_ZCODE"; exit 43; }
xargs -P "$PAR" -I{} python3 "$SC/scripts/sc3_wrap.py" "$ROOT" {} < "$LIST"
