#!/bin/bash
# rejudge_nested.sh — 重判远程拷贝被污染的 job（嵌套复制 → 判分读到缺文件目录）。
# 每 (wave,task)：root 清理远程 job 目录 → root 拷贝新 scratch → remote_judge_v4 重判。
set -uo pipefail
CM=/home/pan-ding/campaign-mcode
python3 - << 'PY' > /tmp/nested_plan.txt
import json, collections
groups = collections.defaultdict(list)
for w, arm, job in json.load(open('/tmp/nested_jobs.json')):
    task = job.rsplit('-r', 1)[0]
    groups[(w, task)].append(f'{arm}__{job}')
for (w, task), tags in sorted(groups.items()):
    print(f"{w}\t{task}\t{' '.join(sorted(set(tags)))}")
PY
echo "nested rejudge groups: $(wc -l < /tmp/nested_plan.txt)"
n=0; total=$(wc -l < /tmp/nested_plan.txt)
while IFS=$'\t' read -r w task tags; do
  # root 清理+拷贝该题涉及的远程 job 目录（容器内路径 /src=/runs, /dst=/remote runs）
  if ! docker run --rm -v "$CM/$w/runs:/src" -v "$CM/${w}-remote/runs:/dst" python:3.11-slim bash -c "
    for tag in $tags; do
      arm=\${tag%%__*}; job=\${tag#*__}
      rm -rf \"/dst/\$arm/\$job\"
      mkdir -p \"/dst/\$arm\"
      cp -r \"/src/\$arm/\$job\" \"/dst/\$arm/\$job\"
    done" < /dev/null; then
    echo "COPY_FAIL $w/$task"; continue
  fi
  bash "$CM/scripts/remote_judge_v4.sh" "$CM/${w}-remote" "$task" $tags >> "$CM/logs/rejudge-nested.log" 2>&1
  n=$((n+1)); echo "rejudged $w/$task ($n/$total)"
done < /tmp/nested_plan.txt
echo "nested rejudge done"
