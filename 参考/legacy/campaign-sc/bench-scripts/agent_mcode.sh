#!/bin/bash
# agent_mcode.sh <model> <scratch> <prompt_file>  (cal2: + quota detection)
set -uo pipefail
MODEL="$1"; SCRATCH="$2"; PROMPT="$3"
export PATH="$HOME/.npm-global/bin:$PATH"
OUT=$(mktemp)
mcode exec --cwd "$SCRATCH" --model "$MODEL" --permission full --timeout 25m "$(cat "$PROMPT")" > "$OUT" 2>&1
rc=$?
tail -c 4000 "$OUT"
if grep -qi "insufficient_balance\|Token Plan 用量上限\|余额不足\|http_code.:402\| arrears\|error code: 2067" "$OUT"; then
  touch "/home/pan-ding/bench/QUOTA"
  rm -f "$OUT"; exit 42
fi
rm -f "$OUT"
exit $rc
