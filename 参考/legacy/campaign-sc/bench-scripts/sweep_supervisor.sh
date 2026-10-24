#!/bin/bash
# Convergence supervisor: per config, when no lane alive and valid results < 51, launch full-list sweep lane.
set -u
B=/home/pan-ding/bench
TARGET=51
declare -A CFG_H MCFG=(
  [zcode-glm53]="zcode account:bigmodel-individual-coding-plan/GLM-5.3"
  [mcode-m3]="mcode minimax/MiniMax-M3"
  [mcode-m27]="mcode minimax/MiniMax-M2.7"
  [mcode-m31flash]="mcode minimax/MiniMax-M3.1-Flash-Preview"
  [kimi-k28]="kimi kimi-code/kimi-for-coding"
  [step-step5]="step step-5-preview"
)
round=0
while [ $round -lt 12 ]; do
  round=$((round+1))
  echo "[sup] round $round $(date -Is)" >> $B/logs/supervisor.log
  # disk guard
  avail=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
  if [ "$avail" -lt 6 ]; then
    echo "[sup] disk low ${avail}G, pruning tbtask images" >> $B/logs/supervisor.log
    docker images --format "{{.Repository}} {{.Size}}" | awk '$1 ~ /^tbtask-/ && $2 ~ /GB/ {print $1}' | xargs -r docker rmi -f >/dev/null 2>&1
    docker image prune -f >/dev/null 2>&1
  fi
  alldone=1
  for cfg in zcode-glm53 mcode-m3 mcode-m27 mcode-m31flash kimi-k28 step-step5; do
    n=$(ls $B/results/$cfg/*.json 2>/dev/null | wc -l)
    valid=0
    for f in $B/results/$cfg/*.json; do
      [ -f "$f" ] || continue
      python3 -c "import json,sys;json.load(open(sys.argv[1]));sys.exit(0)" "$f" 2>/dev/null && valid=$((valid+1))
    done
    if [ -f "$B/QUOTA_$cfg" ]; then
      echo "[sup] $cfg quota flag present, skipping" >> $B/logs/supervisor.log
      alldone=0; continue
    fi
    if pgrep -f "lane.sh $cfg " >/dev/null 2>&1; then
      echo "[sup] $cfg lane running ($valid valid)" >> $B/logs/supervisor.log
      alldone=0; continue
    fi
    if [ "$valid" -ge "$TARGET" ]; then
      echo "[sup] $cfg complete ($valid)" >> $B/logs/supervisor.log
      continue
    fi
    alldone=0
    set -- ${MCFG[$cfg]}
    h=$1; model=$2
    echo "[sup] launching sweep for $cfg (valid=$valid)" >> $B/logs/supervisor.log
    cd $B && nohup bash scripts/lane.sh $cfg "$h" "$model" >> $B/logs/lane-$cfg-sweep-r$round.out 2>&1 &
    sleep 30
  done
  [ $alldone -eq 1 ] && { echo "[sup] ALL COMPLETE round $round" >> $B/logs/supervisor.log; break; }
  sleep 600
done
echo "[sup] supervisor exit $(date -Is)" >> $B/logs/supervisor.log
