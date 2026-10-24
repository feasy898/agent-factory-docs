#!/bin/bash
# confirm_judge_watch.sh — 复测判分看守：某波解题完成后用 judge_all_v5 判分（v5=root拷贝+清理验证+镜像缓存）。
CM=/home/pan-ding/campaign-mcode
LOG=$CM/logs/confirm_judge_watch.log
WAVES="confirm-mem-prompt confirm-mem-tool confirm-mem-mixed"
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }
wave_solve_done() {
  local d="$CM/$1/runs"
  local dn tot
  dn=$(find "$d" -name .done 2>/dev/null | wc -l)
  tot=$(find "$d" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | wc -l)
  [ "$tot" -gt 0 ] && [ "$dn" -ge "$tot" ]
}
say "confirm judge watcher start"
for w in $WAVES; do
  say "waiting for $w solving..."
  while ! wave_solve_done "$w"; do sleep 300; done
  say "$w solving done -> judging"
  bash "$CM/scripts/judge_all_v5.sh" "$w" 4 >> "$CM/logs/$w-judge.out" 2>&1
  say "$w judged: $(ls "$CM/$w/results"/*.json 2>/dev/null | wc -l) results"
done
say "ALL CONFIRM WAVES JUDGED"
