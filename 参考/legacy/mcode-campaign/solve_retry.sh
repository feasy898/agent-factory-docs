#!/bin/bash
# solve_retry.sh — 重跑 run 级失败的 job：低并发 + 单 job 最多 3 次尝试（自愈锁错误/超时切断）。
# 配额熔断: 遇到 402/2067 立即停（不标记 .done，不留污染），touch QUOTA。
# 用法: solve_retry.sh <parallel>  （读取 /tmp/affected_jobs.json）
set -uo pipefail
PAR="${1:-12}"
CM=/home/pan-ding/campaign-mcode
MODEL="minimax/MiniMax-M3.1-Flash-Preview"
export PATH="$HOME/.npm-global/bin:$PATH"
AFFECTED=/tmp/affected_jobs.json
QUOTA="$CM/QUOTA"

run_one() {
  local wave="$1" arm="$2" job="$3"
  local d="$CM/$wave/runs/$arm/$job"
  local out="$CM/$wave/logs/$arm/$job.mcode.log"
  mkdir -p "$(dirname "$out")"
  [ -f "$d/prompt.txt" ] || { echo "NO_PROMPT $wave/$arm/$job"; return 0; }
  for attempt in 1 2 3; do
    [ -f "$d/work/.done" ] && { echo "SKIP $wave/$arm/$job"; return 0; }
    timeout -k 60 1800 mcode exec --cwd "$d/work" --model "$MODEL" --permission full --timeout 25m "$(cat "$d/prompt.txt")" > "$out.attempt$attempt" 2>&1
    if grep -qi "insufficient_balance\|Token Plan 用量上限\|http_code.:402\|error code: 2067" "$out.attempt$attempt"; then
      touch "$QUOTA"; echo "QUOTA $wave/$arm/$job"; return 42
    fi
    if grep -qE "mcode exec (failed|cancelled)" "$out.attempt$attempt"; then
      echo "RETRY($attempt) $wave/$arm/$job: $(grep -oE "mcode exec (failed|cancelled).*" "$out.attempt$attempt" | head -1 | cut -c1-70)"
      sleep 5
      continue
    fi
    mv "$out.attempt$attempt" "$out"
    touch "$d/work/.done"
    echo "DONE $wave/$arm/$job (attempt $attempt)"
    return 0
  done
  mv "$out.attempt3" "$out" 2>/dev/null || mv "$out.attempt1" "$out" 2>/dev/null
  touch "$d/work/.done"
  echo "GAVEUP $wave/$arm/$job"
  return 0
}
export -f run_one; export CM MODEL QUOTA

# 只把"主日志仍有 run 级失败/缺失"的 job 加入重跑列表（已完成的不动）
python3 - "$AFFECTED" << 'PY' > /tmp/retry_jobs.txt
import json, sys, os, re
runfail = re.compile(r"mcode exec (failed|cancelled)")
seen = set()
for w, arm, job, snip in json.load(open(sys.argv[1])):
    k = (w, arm, job)
    if k in seen: continue
    seen.add(k)
    log = f"/home/pan-ding/campaign-mcode/{w}/logs/{arm}/{job}.mcode.log"
    clean = False
    if os.path.exists(log):
        try:
            txt = open(log, errors="replace").read()
            clean = (not runfail.search(txt)) and len(txt) > 100
        except Exception:
            clean = False
    if not clean:
        print(f"{w}\t{arm}\t{job}")
PY
echo "retry jobs: $(wc -l < /tmp/retry_jobs.txt)"
while IFS=$'\t' read -r w a j; do rm -f "$CM/$w/runs/$a/$j/work/.done"; done < /tmp/retry_jobs.txt
rm -f "$QUOTA"
cat /tmp/retry_jobs.txt | xargs -P "$PAR" -I{} bash -c 'IFS=$'"'"'\t'"'"' read -r w a j <<< "{}"; run_one "$w" "$a" "$j"' | tee /tmp/retry_solve.log | tail -3
if [ -f "$QUOTA" ]; then echo "QUOTA_HIT — 停止"; exit 42; fi
echo "retry solve done: $(grep -c DONE /tmp/retry_solve.log) done, $(grep -c GAVEUP /tmp/retry_solve.log) gaveup"
