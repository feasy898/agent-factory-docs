#!/bin/bash
# launch_cal2.sh — start the 5 official-harness lanes for the cal2 round
set -uo pipefail
BENCH=/home/pan-ding/bench
LIST="$BENCH/jobs/cal2_tasks.txt"
[ -s "$LIST" ] || { echo "missing $LIST"; exit 1; }
launch() { # config harness model
  nohup bash "$BENCH/scripts/lane.sh" "$1" "$2" "$3" "$LIST" >> "$BENCH/logs/lane-$1.out" 2>&1 &
  echo "lane $1 pid $!"
}
launch cal2-mcode-m3    mcode "minimax/MiniMax-M3"
sleep 20
launch cal2-mcode-m31f  mcode "minimax/MiniMax-M3.1-Flash-Preview"
sleep 20
launch cal2-step-s5     step  "step-5-preview"
sleep 20
launch cal2-step-router step  "step-router-v1"
sleep 20
launch cal2-kimi-k28    kimi  "kimi-code/kimi-for-coding"
echo "all cal2 lanes launched $(date -Is)"
