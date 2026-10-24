#!/bin/bash
# limbo_fix.sh — 重跑旧看守 bug 遗留的 4 个 limbo job（等配额恢复，配额安全模式）。
CM=/home/pan-ding/campaign-mcode
MODEL="minimax/MiniMax-M3.1-Flash-Preview"
export PATH="$HOME/.npm-global/bin:$PATH"
LOG=$CM/logs/limbo_fix.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }
say "limbo fix start"
# 等配额恢复（QUOTA 文件消失且持续 5 分钟）
while true; do
  if [ ! -f "$CM/QUOTA" ]; then
    sleep 300
    [ ! -f "$CM/QUOTA" ] && break
  fi
  sleep 300
done
say "quota clear, rerunning limbo jobs"
for entry in "p18-mask-separation solve-maze-challenge-r3" "p18-mask-separation stable-parallel-kmeans-r1" "p18-mask-separation stable-parallel-kmeans-r2" "p18-mask-separation stable-parallel-kmeans-r3"; do
  set -- $entry
  arm=$1; job=$2
  d="$CM/confirm-mem-prompt/runs/$arm/$job"
  main="$CM/confirm-mem-prompt/logs/$arm/$job.mcode.log"
  tmp="$main.rerun"
  for attempt in 1 2 3; do
    timeout -k 60 1800 mcode exec --cwd "$d/work" --model "$MODEL" --permission full --timeout 25m "$(cat "$d/prompt.txt")" > "$tmp" 2>&1
    if grep -qi "Token Plan 用量上限|insufficient_balance" "$tmp"; then
      say "quota-blocked $arm/$job (attempt $attempt)"; rm -f "$tmp"; sleep 600; continue
    fi
    if grep -qE "mcode exec (failed|cancelled)" "$tmp"; then
      say "still-failing $arm/$job (attempt $attempt)"; sleep 10; continue
    fi
    mv "$tmp" "$main"; say "limbo-fixed $arm/$job (attempt $attempt)"; break
  done
  rm -f "$tmp" 2>/dev/null
done
say "limbo fix done"
