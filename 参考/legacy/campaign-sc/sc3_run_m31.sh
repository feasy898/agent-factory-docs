#!/bin/bash
# sc3_run_m31.sh <root> <par> — SC3 的 m3.1 车道一轮派发（只跑 jobs-m31.txt）
set -uo pipefail
ROOT="$1"; PAR="${2:-1}"
SC="$(dirname "$ROOT")"
LIST="$ROOT/jobs-m31.txt"
[ -f "$LIST" ] || { echo "no jobs-m31.txt"; exit 0; }
export PATH="$HOME/.npm-global/bin:$PATH"
command -v mcode >/dev/null 2>&1 || { echo "FATAL_NO_MCODE"; exit 43; }
export SC3_BACKEND=m31
xargs -P "$PAR" -I{} python3 "$SC/scripts/sc3_wrap.py" "$ROOT" {} < "$LIST"
