#!/bin/bash
# confirm_final_chain.sh — 复测收尾：三波判分完成后自动聚合并出确证报告。
CM=/home/pan-ding/campaign-mcode
LOG=$CM/logs/confirm_final_chain.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }
say "confirm final chain start"
while true; do
  if grep -q "ALL CONFIRM WAVES JUDGED" "$CM/logs/confirm_judge_watch.log" 2>/dev/null; then
    say "all judged -> aggregating"
    break
  fi
  sleep 300
done
for w in confirm-mem-prompt confirm-mem-tool confirm-mem-mixed; do
  arms=$(python3 -c "
import json
d=json.load(open('$CM/waves/$w.json'))
print(' '.join(['base']+d['techniques']))")
  tasks=$(python3 -c "
import json
d=json.load(open('$CM/waves/$w.json'))
print(' '.join(d['core_tasks']))")
  python3 "$CM/scripts/aggregate.py" "$CM/$w/results" "$arms" "$tasks" 3 > "$CM/$w/results/confirm-report.txt" 2>&1
  say "$w aggregated"
done
say "CONFIRM_FINAL_READY"
