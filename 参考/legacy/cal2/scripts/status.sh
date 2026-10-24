#!/bin/bash
# status.sh — one-shot status of the whole cal2 round (anolis lanes + local lanes + disk + quota)
set -uo pipefail
ROOT=/home/pan-ding/workspace/临时工作区/temp1
CAL=$ROOT/cal2
echo "===== $(date -Is) ====="
echo "--- anolis official lanes ---"
ssh -o ConnectTimeout=8 -o BatchMode=yes anolis '
for cfg in cal2-mcode-m3 cal2-mcode-m31f cal2-step-s5 cal2-step-router cal2-kimi-k28; do
  d=/home/pan-ding/bench/results/$cfg
  n=$(ls $d/*.json 2>/dev/null | wc -l)
  p=$(grep -l "\"pass\"" $d/*.json 2>/dev/null | wc -l)
  f=$(grep -l "\"fail\"" $d/*.json 2>/dev/null | wc -l)
  i=$(grep -l "\"infra\"" $d/*.json 2>/dev/null | wc -l)
  alive=$(pgrep -f "lane.sh $cfg " >/dev/null 2>&1 && echo RUN || echo DEAD)
  echo "$cfg: $alive done=$n pass=$p fail=$f infra=$i"
done
echo "quota_marker=$(ls /home/pan-ding/bench/QUOTA* 2>/dev/null | wc -l) disk=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)G"
echo "supervisor=$(pgrep -f supervisor_cal2 >/dev/null && echo RUN || echo DEAD)"
' 2>/dev/null
echo "--- local workflow lanes (agent file activity) ---"
cd "$CAL/runs"
for cfg in zcode-m3 zcode-m31f zcode-s5 zcode-router; do
  n=$(find $cfg -type f -mmin -12 2>/dev/null | wc -l)
  tot=$(find $cfg -type f 2>/dev/null | wc -l)
  echo "$cfg: $n files active in last 12m / $tot total"
done
echo "--- local judged so far ---"
for cfg in zcode-m3 zcode-m31f zcode-s5 zcode-router; do
  echo "$cfg: $(ls $CAL/results/$cfg/*.json 2>/dev/null | wc -l) judged"
done
