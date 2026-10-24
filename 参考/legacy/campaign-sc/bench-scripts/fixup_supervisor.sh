#!/bin/bash
# 修复守护：重跑 8 个 grok harness-bug 题 + 重判 18 个 zcode-router 假失败，带重试
B=/home/pan-ding/bench
LOG=$B/logs/fixup.log
say() { echo "$(date +%H:%M) $*" >> $LOG; }

# 1) grok 8 题：删旧结果 + 重跑（lane.sh 只跳过 pass/fail，所以必须先删）
for t in $(cat $B/jobs/grok8.txt); do rm -f $B/results/cal2-grok47/$t.json; done
say "grok8 results cleared, launching 2 lanes"
for f in /tmp/g8_part_00 /tmp/g8_part_01; do
  setsid bash $B/scripts/lane.sh cal2-grok47 grok grok-4.7 $f < /dev/null >> $B/logs/fixup-g8.out 2>&1 &
  sleep 3
done

# 2) zcode-router 18 题重判（ Judge 路径 runs/<cfg>-<t>/work ）
while read cfg t; do
  [ -f "$B/results/$cfg/$t.json" ] && continue
  say "rejudging $cfg/$t"
  bash $B/scripts/judge.sh $B/tasks/$t $B/runs/$cfg-$t/work $B/results/$cfg/$t.json >> $B/logs/fixup-rz.out 2>&1
done < $B/jobs/rejudge_zcode2.txt

say "fixup supervisor done"
