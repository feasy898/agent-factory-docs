#!/bin/bash
# agent_step.sh <model> <scratch> <prompt_file>  (cal2: + quota detection)
set -uo pipefail
MODEL="$1"; SCRATCH="$2"; PROMPT="$3"
export PATH="$HOME/.stepcode/bin:$PATH"
export STEP_NON_INTERACTIVE_APPROVAL=allow
GUIDE="Environment note: this non-interactive session has no confirmation UI. Commands like rm -rf (recursive-force-remove) and compound destructive git commands are hard-blocked and will TERMINATE your run. Use rm -r without -f, or move files aside with mv instead. Keep each bash call to a single non-destructive-purpose command when it touches rm or git history."
OUT=$(mktemp)
cd "$SCRATCH" && step -p "$(cat "$PROMPT")" --approval-mode auto --model "$MODEL" --append-system-prompt "$GUIDE" > "$OUT" 2>&1
rc=$?
tail -c 4000 "$OUT"
if grep -qi "insufficient_balance\|Token Plan 用量上限\|余额不足\|http_code.:402\| arrears\|error code: 2067\|额度" "$OUT"; then
  touch "/home/pan-ding/bench/QUOTA"
  rm -f "$OUT"; exit 42
fi
rm -f "$OUT"
exit $rc
