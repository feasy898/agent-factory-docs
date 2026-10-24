#!/bin/bash
# judge_all_v5.sh <root> [parallel] — 用修复版判分器（构建装 pytest + 探测 + 环境误判防护）判全部分 job。
set -uo pipefail
ROOT="$1"; PAR="${2:-4}"
# v5b: ROOT 可能是相对路径（看守传波次名）；docker -v 需要绝对路径，
# 否则 docker 把 "xxx-remote/runs" 当卷名报 invalid characters。
case "$ROOT" in
  /*) ;;
  *)  ROOT="$(cd "$(dirname "$ROOT")" 2>/dev/null && pwd)/$(basename "$ROOT")" ;;
esac
RCAMP="${ROOT}-remote"
export PATH="$HOME/.npm-global/bin:$PATH"
ssh -o BatchMode=yes -o ConnectTimeout=10 localhost true 2>/dev/null || true
# 本脚本就在 anolis 上跑，直接用本地路径
REMOTE_JUDGE=/home/pan-ding/campaign-mcode/scripts/remote_judge_v5.sh
mkdir -p "$ROOT/results" "$RCAMP/runs" "$RCAMP/results" "$RCAMP/logs"
# 用 root 容器清空远程中转目录（docker 判分会产生 root 所有的残留，pan-ding 删不动）
# v5: root 清理 + 验证（旧版静默失败导致孤儿容器重建 __pycache__ → rm 失败 → 嵌套复制 → 判分读到缺文件目录）
for i in 1 2 3; do
  docker run --rm -v "$RCAMP:/cleanup" python:3.11-slim sh -c "rm -rf /cleanup/runs/* /cleanup/results/* 2>/dev/null" >/dev/null 2>&1
  left=$(find "$RCAMP/runs" "$RCAMP/results" -mindepth 1 2>/dev/null | wc -l)
  [ "$left" = "0" ] && break
  echo "WARN: cleanup attempt $i left $left entries, retrying" >&2
  sleep 3
done
[ "$left" = "0" ] || { echo "FATAL: cannot clean $RCAMP" >&2; exit 1; }

# 按 task 聚合全部 (arm,rep) 的 tag，一题一判（每题一次构建）
python3 - "$ROOT" << 'PY' > "$ROOT/logs/judge_plan.txt"
import os, sys, collections
root = sys.argv[1]
by_task = collections.defaultdict(list)
for arm in sorted(os.listdir(os.path.join(root, 'runs'))):
    for job in sorted(os.listdir(os.path.join(root, 'runs', arm))):
        wd = os.path.join(root, 'runs', arm, job, 'work')
        if not os.path.isdir(wd):
            continue
        if not os.path.exists(os.path.join(wd, '.done')):
            continue  # 未完成（配额熔断未跑）的 job 不判——没有 agent 产物
        task = job.rsplit('-r', 1)[0]
        by_task[task].append(f'{arm}__{job}')
for t, tags in by_task.items():
    print(t + '\t' + ' '.join(tags))
PY

judge_task() {
  local root="$1" rcamp="$2" rj="$3"; local line="$4"
  local task="${line%%$'\t'*}"; local tags="${line#*$'\t'}"
  # 推送该题的 scratch
  local list=$(mktemp)
  for tag in $tags; do
    local arm="${tag%%__*}"; local job="${tag#*__}"
    [ -d "$root/runs/$arm/$job/work" ] && echo "$arm/$job" >> "$list"
  done
  [ -s "$list" ] || { rm -f "$list"; return 0; }
  # v5: 用 root 容器拷贝（pan-ding 删不掉 root 所有的 __pycache__ → 旧版 cp 嵌套 → 判分读到陈旧目录）
  docker run -i --rm -v "$rcamp/runs:/dst" -v "$root/runs:/src" python:3.11-slim bash -c '
    while read -r d; do
      rm -rf "/dst/$d"
      mkdir -p "/dst/$(dirname "$d")"
      cp -r "/src/$d" "/dst/$d"
    done < /dev/stdin' < "$list" || { echo "COPY_FAIL $task" >&2; rm -f "$list"; return 1; }
  rm -f "$list"
  bash "$rj" "$rcamp" "$task" $tags
}
export -f judge_task; export ROOT RCAMP REMOTE_JUDGE

cat "$ROOT/logs/judge_plan.txt" | xargs -P "$PAR" -I{} bash -c 'judge_task "$ROOT" "$RCAMP" "$REMOTE_JUDGE" "$@"' _ {}
# 结果回传（本地就是 anolis，直接拷）
cp "$RCAMP/results/"*.json "$ROOT/results/" 2>/dev/null
echo "judge done: $(ls "$ROOT/results" | wc -l) results"
