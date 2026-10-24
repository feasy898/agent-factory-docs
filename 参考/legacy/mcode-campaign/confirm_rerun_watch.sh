#!/bin/bash
# confirm_rerun_watch.sh — 复测假失败自愈（配额安全版）：重跑写临时日志，成功才替换主日志。
# 不清 .done；重跑覆盖 work 目录，判分读最终态。配额熔断时主日志不动（下轮继续重试）。
CM=/home/pan-ding/campaign-mcode
LOG=$CM/logs/confirm_rerun_watch.log
MODEL="minimax/MiniMax-M3.1-Flash-Preview"
export PATH="$HOME/.npm-global/bin:$PATH"
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }
say "confirm rerun watcher start (quota-safe)"
while true; do
  mapfile -t jobs < <(python3 - << 'PY'
import os, re, glob, time
runfail = re.compile(r"mcode exec (failed|cancelled)")
quota = re.compile(r"Token Plan 用量上限|insufficient_balance")
now = time.time()
for log in glob.glob("/home/pan-ding/campaign-mcode/confirm-*/logs/*/*.mcode.log"):
    try:
        if now - os.path.getmtime(log) < 180: continue
        txt = open(log, errors="replace").read()
    except Exception: continue
    if runfail.search(txt) and not quota.search(txt):
        m = re.match(r".*/confirm-([a-z-]+)/logs/([^/]+)/(.+)\.mcode\.log", log)
        if m: print(f"{m.group(1)}\t{m.group(2)}\t{m.group(3)}")
PY
)
  if [ "${#jobs[@]}" -gt 0 ]; then
    say "found ${#jobs[@]} failed jobs"
    for entry in "${jobs[@]}"; do
      IFS=$'\t' read -r w arm job <<< "$entry"
      d="$CM/confirm-$w/runs/$arm/$job"
      main="$CM/confirm-$w/logs/$arm/$job.mcode.log"
      tmp="$main.rerun"
      [ -f "$d/prompt.txt" ] || continue
      ok=0
      for attempt in 1 2; do
        timeout -k 60 1800 mcode exec --cwd "$d/work" --model "$MODEL" --permission full --timeout 25m "$(cat "$d/prompt.txt")" > "$tmp" 2>&1
        if grep -qi "Token Plan 用量上限|insufficient_balance" "$tmp"; then
          say "quota-blocked $w/$arm/$job (attempt $attempt), keep old log"
          rm -f "$tmp"; break
        fi
        if grep -qE "mcode exec (failed|cancelled)" "$tmp"; then
          say "still-failing $w/$arm/$job (attempt $attempt)"
          sleep 10; continue
        fi
        mv "$tmp" "$main"; ok=1
        say "rerun-ok $w/$arm/$job (attempt $attempt)"
        break
      done
      rm -f "$tmp" 2>/dev/null
    done
  fi
  sleep 900
done
