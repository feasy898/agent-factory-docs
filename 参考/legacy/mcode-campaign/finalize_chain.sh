#!/bin/bash
# finalize_chain.sh — 收尾链：等全部 affected job 重跑完成 → 重判剩余 → 拉取 → 终版聚合。
set -uo pipefail
CM=/home/pan-ding/campaign-mcode
LOG=$CM/logs/finalize_chain.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }
say "finalize chain start"
# 1. 等重跑全部完成（含配额等待）
while true; do
  rem=$(python3 - << 'PY'
import json, os
n = 0
for w, arm, job, snip in json.load(open('/tmp/affected_jobs.json')):
    if not os.path.exists(f"/home/pan-ding/campaign-mcode/{w}/runs/{arm}/{job}/work/.done"):
        n += 1
print(n)
PY
)
  [ "$rem" = "0" ] && { say "all retries done"; break; }
  running=$(ps aux | grep -c "[m]code exec")
  say "remaining=$rem mcode_running=$running"
  [ "$running" -gt 0 ] && sleep 300 && continue
  # 无运行中 job 但仍有剩余 → 可能配额熔断，等看守处理；这里也兜底重启
  if [ -f "$CM/QUOTA" ]; then
    say "quota blocked, waiting for watcher"; sleep 600; continue
  fi
  say "no mcode running and no quota flag -> relaunch retry"
  bash "$CM/scripts/solve_retry.sh" 12 >> "$CM/logs/retry-solve.out" 2>&1
  sleep 120
done
# 2. 重判全部 216 例（幂等：已判过的结果一致）
say "rejudging all 216 affected jobs"
bash "$CM/scripts/rejudge_retry.sh" >> "$CM/logs/rejudge-retry-final.out" 2>&1
say "rejudge done"
# 3. 本地拉取+聚合由 ZCode 侧执行（标记完成）
say "FINALIZE_READY"
