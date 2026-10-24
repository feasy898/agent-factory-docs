#!/bin/bash
# rejudge_tasks.sh <root> <parallel> <judge_script> <task> [task ...]
# 只重判指定题目（默认用 remote_judge2.sh 修复版），复用 root 下已有的 agent 产物，
# 结果写回 <root>/results/。中转目录用 <root>-rejudge，与并行中的常规判分流水线互不干扰。
set -uo pipefail
ROOT="$1"; PAR="$2"; RJ="$3"; shift 3
RCAMP="${ROOT}-rejudge"
export PATH="$HOME/.npm-global/bin:$PATH"
mkdir -p "$ROOT/results" "$RCAMP/runs" "$RCAMP/results" "$RCAMP/logs"
docker run --rm -v "$RCAMP:/cleanup" python:3.11-slim sh -c "rm -rf /cleanup/runs/* /cleanup/results/* 2>/dev/null; true" >/dev/null 2>&1 || true

TASKS="$*"
: > "$ROOT/logs/rejudge_plan.txt"
for t in $TASKS; do
  tags=$(python3 - "$ROOT" "$t" << 'PY'
import os, sys
root, task = sys.argv[1], sys.argv[2]
out = []
for arm in sorted(os.listdir(os.path.join(root, 'runs'))):
    for job in sorted(os.listdir(os.path.join(root, 'runs', arm))):
        if job.rsplit('-r', 1)[0] != task:
            continue
        wd = os.path.join(root, 'runs', arm, job, 'work')
        if os.path.isdir(wd) and os.path.exists(os.path.join(wd, '.done')):
            out.append(f'{arm}__{job}')
print(' '.join(out))
PY
)
  [ -n "$tags" ] || { echo "[rejudge] skip $t (no finished runs)" >&2; continue; }
  echo "$t	$tags" >> "$ROOT/logs/rejudge_plan.txt"
done

judge_task() {
  local root="$1" rcamp="$2" rj="$3"; local line="$4"
  local task="${line%%$'\t'*}"; local tags="${line#*$'\t'}"
  local list; list=$(mktemp)
  for tag in $tags; do
    local arm="${tag%%__*}"; local job="${tag#*__}"
    [ -d "$root/runs/$arm/$job/work" ] && echo "$arm/$job" >> "$list"
  done
  [ -s "$list" ] || { rm -f "$list"; return 0; }
  while read -r d; do
    mkdir -p "$rcamp/runs/$(dirname "$d")"
    rm -rf "$rcamp/runs/$d"
    cp -r "$root/runs/$d" "$rcamp/runs/$d"
  done < "$list"
  rm -f "$list"
  bash "$rj" "$rcamp" "$task" $tags
}
export -f judge_task; export ROOT RCAMP RJ

xargs -P "$PAR" -I{} bash -c 'judge_task "$ROOT" "$RCAMP" "$RJ" "$@"' _ {} < "$ROOT/logs/rejudge_plan.txt"
cp "$RCAMP/results/"*.json "$ROOT/results/" 2>/dev/null
echo "rejudge done: $(ls "$ROOT/results" | wc -l) results in $ROOT"
