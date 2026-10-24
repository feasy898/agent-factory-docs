#!/bin/bash
# quota_watch.sh — MiniMax 配额监视器：熔断解除后自动重启 wave9/wave11 解题。
# 每 10 分钟一轮：删除 QUOTA 标志 → 对未完成波次跑 solve.sh（跳过 .done）。
# 若配额仍熔断，solve.sh 会快速失败并重新 touch QUOTA，下一轮再试。
CM=/home/pan-ding/campaign-mcode
LOG=$CM/logs/quota_watch.log
wave_incomplete() {
  local w=$1 d=$CM/$1
  local dn tot
  dn=$(find "$d/runs" -name .done 2>/dev/null | wc -l)
  tot=$(find "$d/runs" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | wc -l)
  [ "$tot" -gt 0 ] && [ "$dn" -lt "$tot" ]
}
echo "[$(date '+%F %T')] watcher start" >> "$LOG"
while true; do
  incomplete=""
  for w in wave9 wave11; do wave_incomplete $w && incomplete="$incomplete $w"; done
  [ -z "$incomplete" ] && { echo "[$(date '+%F %T')] all done, exit" >> "$LOG"; break; }
  rm -f "$CM/QUOTA"
  for w in $incomplete; do
    echo "[$(date '+%F %T')] try solve $w" >> "$LOG"
    bash "$CM/scripts/solve.sh" "$w" 10 >> "$CM/logs/$w-solve.out" 2>&1
  done
  if [ -f "$CM/QUOTA" ]; then
    echo "[$(date '+%F %T')] still quota-blocked, sleep 600" >> "$LOG"
  else
    echo "[$(date '+%F %T')] quota OK, checking again soon" >> "$LOG"
  fi
  sleep 600
done
