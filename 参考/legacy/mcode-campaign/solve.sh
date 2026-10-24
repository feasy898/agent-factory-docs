#!/bin/bash
# solve.sh <root> <parallel> — 并行跑 mcode（m3.1flash），带配额熔断。
# 每 job: runs/<arm>/<task>-r<rep>/，prompt.txt 已由 gen_prompts.py 生成。
set -uo pipefail
ROOT="$1"; PAR="${2:-8}"
MODEL="minimax/MiniMax-M3.1-Flash-Preview"
export PATH="$HOME/.npm-global/bin:$PATH"
QUOTA=/home/pan-ding/campaign-mcode/QUOTA
mkdir -p "$ROOT/logs"
rm -f "$QUOTA"

run_one() {
  local job="$1" root="$2" quota="$3"
  local d="$root/runs/$job"
  local out="$root/logs/$job.mcode.log"
  mkdir -p "$(dirname "$out")"
  [ -f "$d/prompt.txt" ] || { echo "NO_PROMPT $job"; return 0; }
  [ -f "$d/work/.done" ] && { echo "SKIP $job"; return 0; }
  # OS 级硬超时 30m（mcode 自带 timeout 对挂死的 API 调用无效，曾挂死 2 小时）
  timeout -k 60 1800 mcode exec --cwd "$d/work" --model "$MODEL" --permission full --timeout 25m "$(cat "$d/prompt.txt")" > "$out" 2>&1
  local rc=$?
  if grep -qi "insufficient_balance\|Token Plan 用量上限\|http_code.:402\|error code: 2067" "$out"; then
    touch "$quota"; echo "QUOTA $job"; return 42
  fi
  touch "$d/work/.done"
  echo "DONE $job rc=$rc"
}
export -f run_one; export MODEL

find "$ROOT/runs" -mindepth 2 -maxdepth 2 -type d | sed "s|$ROOT/runs/||" | sort > "$ROOT/logs/jobs.txt"
echo "total jobs: $(wc -l < "$ROOT/logs/jobs.txt")"
xargs -P "$PAR" -I{} bash -c 'run_one "$@"' _ {} "$ROOT" "$QUOTA" < "$ROOT/logs/jobs.txt" | tee "$ROOT/logs/solve.log" | tail -5
if [ -f "$QUOTA" ]; then echo "QUOTA_HIT — 停止（剩余 job 未跑）"; exit 42; fi
echo "solve done"
