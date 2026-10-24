#!/bin/bash
# sc_judge.sh <wave_root> [par] — SC 波次逐 job 判分，绕开 judge_all_v5 的 docker stdin bug。
# 直接调 bench/scripts/judge.sh（任务目录 + work 目录 → results/<arm>__<job>.json），幂等可重跑。
set -uo pipefail
ROOT="$1"; PAR="${2:-4}"
mkdir -p "$ROOT/results" "$ROOT/logs"

judge_one() {
  local root="$1" jobrel="$2"
  local work="$root/runs/$jobrel/work"
  local arm="${jobrel%%/*}" job="${jobrel#*/}"
  local tag="${arm}__${job}"
  local task; task=$(echo "$job" | sed 's/-r[0-9]*$//')
  local out="$root/results/$tag.json"
  [ -f "$out" ] && { echo "SKIP $tag"; return 0; }
  [ -f "$work/.done" ] || { echo "NOTDONE $tag"; return 0; }
  bash /home/pan-ding/bench/scripts/judge.sh "/home/pan-ding/bench/tasks/$task" "$work" "$out" >/dev/null 2>&1
  echo "JUDGED $tag $(cat "$out" 2>/dev/null)"
}
export -f judge_one

find "$ROOT/runs" -mindepth 2 -maxdepth 2 -type d | sed "s|$ROOT/runs/||" | sort > "$ROOT/logs/judge_jobs.txt"
xargs -P "$PAR" -I{} bash -c 'judge_one "$@"' _ "$ROOT" {} < "$ROOT/logs/judge_jobs.txt" | tee "$ROOT/logs/judge-sc-last.log" | tail -3
echo "judge-sc done: $(ls "$ROOT/results"/*.json 2>/dev/null | wc -l) results"
