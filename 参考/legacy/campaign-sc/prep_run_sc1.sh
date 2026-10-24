#!/bin/bash
# prep_run_sc1.sh — SC1：gen_prompts 后为四条工具臂生成工件（带门禁）。
set -uo pipefail
SC=/home/pan-ding/campaign-sc
ROOT=$SC/sc1
LOG=$SC/logs/prep-sc1.log
echo "[$(date '+%F %T')] prep start" >> "$LOG"
fail=0
for arm in g1f g2f g3f g7f; do
  for d in "$ROOT/runs/$arm"/*/work; do
    [ -d "$d" ] || continue
    out=$(python3 "$SC/scripts/prep_sc1.py" "$d" "$arm" 2>&1)
    rc=$?
    if [ $rc -ne 0 ]; then
      fail=$((fail+1))
      touch "$d/.prep_failed"
      echo "[$(date '+%F %T')] PREP_GATE_FAIL $arm $d rc=$rc: $(echo "$out" | tail -1)" >> "$LOG"
    fi
  done
  echo "[$(date '+%F %T')] arm $arm prep done (cumulative fails=$fail)" >> "$LOG"
done
echo "[$(date '+%F %T')] prep complete, fails=$fail" >> "$LOG"
echo "prep fails: $fail (details in $LOG)"
