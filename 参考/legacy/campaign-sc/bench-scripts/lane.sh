#!/bin/bash
# lane.sh <config_id> <harness> <model> [tasklist_file]
# Runs tasks sequentially; skips tasks that already have a final result (pass/fail) unless FORCE=1.
set -uo pipefail
BENCH=/home/pan-ding/bench
CONFIG="$1"; HARNESS="$2"; MODEL="$3"
LIST="${4:-$BENCH/jobs/all_tasks.txt}"
LANELOG="$BENCH/logs/lane-$CONFIG.log"
mkdir -p "$BENCH/logs"
echo "[lane $CONFIG] start $(date -Is) harness=$HARNESS model=$MODEL" >> "$LANELOG"
while read -r TASK; do
  [ -z "$TASK" ] && continue
  RES="$BENCH/results/$CONFIG/$TASK.json"
  if [ -f "$RES" ] && [ "${FORCE:-0}" != "1" ]; then
    ST=$(python3 -c "import json;print(json.load(open('$RES')).get('status',''))" 2>/dev/null)
    if [ "$ST" = "pass" ] || [ "$ST" = "fail" ]; then
      echo "[lane $CONFIG] skip $TASK ($ST)" >> "$LANELOG"; continue
    fi
  fi
  echo "[lane $CONFIG] run $TASK $(date -Is)" >> "$LANELOG"
  bash "$BENCH/scripts/run_one.sh" "$CONFIG" "$HARNESS" "$MODEL" "$TASK" >> "$LANELOG" 2>&1
  echo "[lane $CONFIG] done $TASK rc=$? $(date -Is)" >> "$LANELOG"
done < "$LIST"
echo "[lane $CONFIG] ALL DONE $(date -Is)" >> "$LANELOG"
