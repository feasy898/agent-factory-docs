#!/bin/bash
# agent_kimi.sh <model> <scratch> <prompt_file>
set -uo pipefail
MODEL="$1"; SCRATCH="$2"; PROMPT="$3"
export PATH="$HOME/.kimi-code/bin:$PATH"
cd "$SCRATCH" || exit 1
OUT=$(mktemp)
kimi -p "$(cat "$PROMPT")" -m "$MODEL" > "$OUT" 2>&1
rc=$?
cat "$OUT"
if grep -q "usage limit\|rate limit\|quota" "$OUT"; then
  touch "/home/pan-ding/bench/QUOTA_kimi-k28"
  rc=42
fi
rm -f "$OUT"
exit $rc
