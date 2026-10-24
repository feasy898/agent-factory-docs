#!/bin/bash
# disk_janitor.sh — 复测期间磁盘自持（激进版）：清陈旧遥测 + 1 小时前的任务记录。
# mcode run 上限 25 分钟，1 小时前的记录必然已完成；<5G 时清 3 小时前的 sessions。
while true; do
  rm -rf /home/pan-ding/.minimax/v2/observability/* 2>/dev/null
  find /home/pan-ding/.minimax/background-tasks -mindepth 1 -maxdepth 1 ! -newermt "1 hour ago" -exec rm -rf {} + 2>/dev/null
  avail=$(df -m / | tail -1 | awk "{print \$4}")
  if [ "$avail" -lt 5120 ]; then
    find /home/pan-ding/.minimax/background-tasks -mindepth 1 -maxdepth 1 ! -newermt "3 hours ago" -exec rm -rf {} + 2>/dev/null
    find /home/pan-ding/.minimax/v2/sessions -mindepth 1 -maxdepth 1 -type d ! -newermt "3 hours ago" -exec rm -rf {} + 2>/dev/null
    rm -rf /home/pan-ding/campaign-mcode/confirm-*/logs/*.attempt* 2>/dev/null
  fi
  echo "[$(date '+%F %T')] janitor, / avail=${avail}M" >> /home/pan-ding/campaign-mcode/logs/disk_janitor.log
  sleep 1200
done
