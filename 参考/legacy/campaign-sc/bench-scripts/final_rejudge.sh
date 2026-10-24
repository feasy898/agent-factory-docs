#!/bin/bash
# 最终重判：所有 pytest-missing 假失败（zcode-router 20 + grok47 19 + grok8 infra 2）
B=/home/pan-ding/bench
LOG=$B/logs/final-rejudge.log
say() { echo "$(date +%H:%M) $*" >> $LOG; }
: > $B/jobs/final_rejudge.txt
for cfg in zcode-router cal2-grok47; do
  for f in $B/results/$cfg/*.json; do
    t=$(basename $f .json)
    s=$(python3 -c "import json;print(json.load(open(\"$f\")).get(\"status\"))" 2>/dev/null)
    if [ "$s" = "fail" ] && grep -q "No module named pytest" "$f.log" 2>/dev/null; then
      echo "$cfg $t" >> $B/jobs/final_rejudge.txt
    fi
  done
done
# grok8 的 infra 结果也重判
for t in mahjong-winninghand openssl-selfsigned-cert; do
  s=$(python3 -c "import json;print(json.load(open(\"$B/results/cal2-grok47/$t.json\")).get(\"status\"))" 2>/dev/null)
  [ "$s" = "infra" ] && echo "cal2-grok47 $t" >> $B/jobs/final_rejudge.txt
done
say "total to rejudge: $(wc -l < $B/jobs/final_rejudge.txt)"
split -d -n l/3 $B/jobs/final_rejudge.txt /tmp/fr_part_
for f in /tmp/fr_part_*; do
  setsid bash -c "while read cfg t; do
    rm -f $B/results/\$cfg/\$t.json
    if [ \"\$cfg\" = \"zcode-router\" ]; then W=$B/runs/zcode-router-\$t/work; else W=$B/runs/cal2-grok47/\$t/scratch; fi
    bash $B/scripts/judge.sh $B/tasks/\$t \$W $B/results/\$cfg/\$t.json
  done < $f" < /dev/null >> $B/logs/final-rejudge.out 2>&1 &
  sleep 3
done
say "3 rejudge lanes launched"
