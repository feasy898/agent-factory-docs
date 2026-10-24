#!/bin/bash
# retry_watch.sh — 看守 solve_retry：无运行中 mcode 且 affected job 有未完成时自动重启。
# 覆盖配额熔断（QUOTA_HIT 退出）与异常退出；每次重启前确认配额已恢复。
CM=/home/pan-ding/campaign-mcode
LOG=$CM/logs/retry_watch.log
affected_remaining() {
  python3 - << 'PY'
import json, os
n = 0
for w, arm, job, snip in json.load(open('/tmp/affected_jobs.json')):
    if not os.path.exists(f"/home/pan-ding/campaign-mcode/{w}/runs/{arm}/{job}/work/.done"):
        n += 1
print(n)
PY
}
echo "[$(date '+%F %T')] retry watcher start" >> "$LOG"
while true; do
  rem=$(affected_remaining)
  [ "$rem" = "0" ] && { echo "[$(date '+%F %T')] all affected jobs done, exit" >> "$LOG"; break; }
  running=$(ps aux | grep -c "[m]code exec")
  if [ "$running" -gt 0 ]; then
    sleep 300; continue
  fi
  echo "[$(date '+%F %T')] remaining=$rem, no mcode running -> relaunch" >> "$LOG"
  rm -f "$CM/QUOTA"
  bash "$CM/scripts/solve_retry.sh" 12 >> "$CM/logs/retry-solve.out" 2>&1
  if [ -f "$CM/QUOTA" ]; then
    echo "[$(date '+%F %T')] quota blocked, sleep 600" >> "$LOG"
    sleep 600
  else
    echo "[$(date '+%F %T')] round finished, checking" >> "$LOG"
    sleep 60
  fi
done
