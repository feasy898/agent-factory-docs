#!/bin/bash
# rejudge_retry.sh — 精准重判：只判"work 的 .done 比判分结果新"的 affected job
#（即重跑后尚未重判的）。已判过的跳过，避免重复。
set -uo pipefail
CM=/home/pan-ding/campaign-mcode
python3 - << 'PY' > /tmp/rejudge_plan.txt
import json, os, collections
groups = collections.defaultdict(list)
for w, arm, job, snip in json.load(open('/tmp/affected_jobs.json')):
    done = f"/home/pan-ding/campaign-mcode/{w}/runs/{arm}/{job}/work/.done"
    res = f"/home/pan-ding/campaign-mcode/{w}-remote/results/{arm}__{job}.json"
    if not os.path.exists(done):
        continue  # 未重跑完成
    if os.path.exists(res) and os.path.getmtime(res) >= os.path.getmtime(done):
        continue  # 判分结果比 work 新，已重判过
    task = job.rsplit('-r', 1)[0]
    groups[(w, task)].append(f'{arm}__{job}')
for (w, task), tags in sorted(groups.items()):
    print(f"{w}\t{task}\t{' '.join(sorted(set(tags)))}")
PY
echo "precise rejudge groups: $(wc -l < /tmp/rejudge_plan.txt)"
n=0; total=$(wc -l < /tmp/rejudge_plan.txt)
while IFS=$'\t' read -r w task tags; do
  bash "$CM/scripts/remote_judge_v4.sh" "$CM/${w}-remote" "$task" $tags >> "$CM/logs/rejudge-retry.log" 2>&1
  n=$((n+1)); echo "judged $w/$task ($n/$total)"
done < /tmp/rejudge_plan.txt
echo "precise rejudge done"
