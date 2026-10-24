#!/bin/bash
# confirm_watch.sh — 复测阶段看守：按优先级顺序跑 confirm 波次，-P 12（无锁错误），
# 配额熔断自动等待恢复。全部完成后退出。
CM=/home/pan-ding/campaign-mcode
LOG=$CM/logs/confirm_watch.log
WAVES="confirm-mem-prompt confirm-mem-tool confirm-mem-mixed"
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }
wave_done() {
  local d="$CM/$1/runs"
  local dn tot
  dn=$(find "$d" -name .done 2>/dev/null | wc -l)
  tot=$(find "$d" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | wc -l)
  [ "$tot" -gt 0 ] && [ "$dn" -ge "$tot" ]
}
say "confirm watcher start (waves: $WAVES)"
for w in $WAVES; do
  say "=== $w start ==="
  while true; do
    wave_done "$w" && { say "$w ALL DONE"; break; }
    rm -f "$CM/QUOTA"
    bash "$CM/scripts/solve.sh" "$w" 12 >> "$CM/logs/$w-solve.out" 2>&1
    if [ -f "$CM/QUOTA" ]; then
      say "$w quota blocked, sleep 600"
      sleep 600
    else
      say "$w round finished (solve.sh returned), rechecking"
      sleep 60
    fi
  done
done
say "ALL CONFIRM WAVES SOLVING DONE"
