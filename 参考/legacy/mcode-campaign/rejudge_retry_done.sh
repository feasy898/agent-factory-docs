#!/bin/bash
# rejudge_retry_done.sh — 重判"已成功重跑"的 affected job（日志干净者）。
set -uo pipefail
CM=/home/pan-ding/campaign-mcode
python3 - << 'PY' > /tmp/retry_done_plan.txt
import json, os, re, collections
runfail = re.compile(r"mcode exec (failed|cancelled)")
groups = collections.defaultdict(list)
for w, arm, job, snip in json.load(open('/tmp/affected_jobs.json')):
    log = f"/home/pan-ding/campaign-mcode/{w}/logs/{arm}/{job}.mcode.log"
    if not os.path.exists(log):
        continue
    txt = open(log, errors="replace").read()
    if runfail.search(txt) or len(txt) <= 100:
        continue  # 未成功重跑的跳过
    task = job.rsplit('-r', 1)[0]
    groups[(w, task)].append(f'{arm}__{job}')
for (w, task), tags in sorted(groups.items()):
    print(f"{w}\t{task}\t{' '.join(sorted(set(tags)))}")
PY
echo "retry-done rejudge groups: $(wc -l < /tmp/retry_done_plan.txt)"
n=0; total=$(wc -l < /tmp/retry_done_plan.txt)
while IFS=$'\t' read -r w task tags; do
  bash "$CM/scripts/remote_judge_v4.sh" "$CM/${w}-remote" "$task" $tags >> "$CM/logs/rejudge-retry.log" 2>&1
  n=$((n+1)); echo "judged $w/$task ($n/$total)"
done < /tmp/retry_done_plan.txt
echo "retry-done rejudge done"
