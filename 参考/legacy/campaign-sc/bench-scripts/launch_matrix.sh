#!/bin/bash
# launch_matrix.sh — start all lanes in background
set -uo pipefail
BENCH=/home/pan-ding/bench
ls "$BENCH/tasks" | sort > "$BENCH/jobs/all_tasks.txt"
launch() { # config harness model
  nohup bash "$BENCH/scripts/lane.sh" "$1" "$2" "$3" >> "$BENCH/logs/lane-$1.out" 2>&1 &
  echo "lane $1 pid $!"
}
launch zcode-glm53       zcode "account:bigmodel-individual-coding-plan/GLM-5.3"
launch mcode-m3          mcode "minimax/MiniMax-M3"
launch mcode-m31flash    mcode "minimax/MiniMax-M3.1-Flash-Preview"
launch mcode-m27         mcode "minimax/MiniMax-M2.7"
launch kimi-k28          kimi  "kimi-code/kimi-for-coding"
launch kimi-k27hs        kimi  "kimi-code/kimi-for-coding-highspeed"
launch step-step5        step  "step-5-preview"
