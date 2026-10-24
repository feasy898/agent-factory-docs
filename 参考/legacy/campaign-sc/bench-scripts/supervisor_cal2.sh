#!/bin/bash
# supervisor_cal2.sh — keep the 5 official lanes alive; stop everything on quota; gentle disk guard.
set -u
B=/home/pan-ding/bench
TARGET=51
declare -A MCFG=(
  [cal2-mcode-m3]="mcode minimax/MiniMax-M3"
  [cal2-mcode-m31f]="mcode minimax/MiniMax-M3.1-Flash-Preview"
  [cal2-step-s5]="step step-5-preview"
  [cal2-step-router]="step step-router-v1"
  [cal2-kimi-k28]="kimi kimi-code/kimi-for-coding"
)
CFGS="cal2-mcode-m3 cal2-mcode-m31f cal2-step-s5 cal2-step-router cal2-kimi-k28"
round=0
while [ $round -lt 40 ]; do
  round=$((round+1))
  echo "[sup] round $round $(date -Is)" >> $B/logs/supervisor-cal2.log
  if [ -f "$B/QUOTA" ]; then
    echo "[sup] QUOTA marker present — stopping all lanes" >> $B/logs/supervisor-cal2.log
    for cfg in $CFGS; do pkill -f "lane.sh $cfg " 2>/dev/null; done
    break
  fi
  avail=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
  if [ "$avail" -lt 5 ]; then
    echo "[sup] disk low ${avail}G, pruning tbtask images" >> $B/logs/supervisor-cal2.log
    docker images --format "{{.Repository}}" | grep '^tbtask-' | xargs -r docker rmi -f >/dev/null 2>&1
  fi
  alldone=1
  for cfg in $CFGS; do
    n=$(ls $B/results/$cfg/*.json 2>/dev/null | wc -l)
    if pgrep -f "lane.sh $cfg " >/dev/null 2>&1; then
      echo "[sup] $cfg running ($n results)" >> $B/logs/supervisor-cal2.log
      alldone=0; continue
    fi
    if [ "$n" -ge "$TARGET" ]; then
      echo "[sup] $cfg complete ($n)" >> $B/logs/supervisor-cal2.log
      continue
    fi
    alldone=0
    set -- ${MCFG[$cfg]}
    h=$1; model=$2
    echo "[sup] relaunching sweep for $cfg ($n results)" >> $B/logs/supervisor-cal2.log
    cd $B && nohup bash scripts/lane.sh $cfg "$h" "$model" "$B/jobs/cal2_tasks.txt" >> $B/logs/lane-$cfg-sweep-r$round.out 2>&1 &
    sleep 30
  done
  [ $alldone -eq 1 ] && { echo "[sup] ALL COMPLETE round $round $(date -Is)" >> $B/logs/supervisor-cal2.log; break; }
  sleep 600
done
echo "[sup] supervisor exit $(date -Is)" >> $B/logs/supervisor-cal2.log
