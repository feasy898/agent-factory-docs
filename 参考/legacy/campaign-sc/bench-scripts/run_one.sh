#!/bin/bash
# run_one.sh <config_id> <harness> <model> <task_name>
set -uo pipefail
BENCH=/home/pan-ding/bench
CONFIG="$1"; HARNESS="$2"; MODEL="$3"; TASK="$4"
TASK_DIR="$BENCH/tasks/$TASK"
RUN_DIR="$BENCH/runs/$CONFIG/$TASK"
RES_DIR="$BENCH/results/$CONFIG"
mkdir -p "$RUN_DIR" "$RES_DIR"
SCRATCH="$RUN_DIR/scratch"
rm -rf "$SCRATCH"; mkdir -p "$SCRATCH"

if ! python3 "$BENCH/scripts/prepare_task.py" "$TASK_DIR" "$SCRATCH" "$RUN_DIR/prompt.txt" > "$RUN_DIR/prepare.log" 2>&1; then
  echo "{\"status\":\"infra\",\"reason\":\"prepare_failed\",\"task\":\"$TASK\",\"config\":\"$CONFIG\"}" > "$RES_DIR/$TASK.json"
  exit 2
fi

start=$(date +%s)
AGENT_TIMEOUT=1500
[ "$HARNESS" = "grok" ] && AGENT_TIMEOUT=3750
timeout $AGENT_TIMEOUT bash "$BENCH/scripts/agent_$HARNESS.sh" "$MODEL" "$SCRATCH" "$RUN_DIR/prompt.txt" > "$RUN_DIR/agent.log" 2>&1
rc=$?
end=$(date +%s)

if [ $rc -eq 124 ]; then AV=timeout; elif [ $rc -eq 42 ]; then
  echo "{\"status\":\"quota\",\"config\":\"$CONFIG\",\"task\":\"$TASK\"}" >> /home/pan-ding/bench/logs/quota-events.log
  exit 43
elif [ $rc -ne 0 ]; then AV=harness; else AV=ran; fi

bash "$BENCH/scripts/judge.sh" "$TASK_DIR" "$SCRATCH" "$RES_DIR/$TASK.json" > /dev/null 2>&1

python3 - "$RES_DIR/$TASK.json" "$CONFIG" "$HARNESS" "$MODEL" "$TASK" "$rc" "$AV" "$start" "$end" <<'PY'
import json, sys, os
path, config, harness, model, task, rc, av, start, end = sys.argv[1:]
try:
    res = json.load(open(path))
except Exception:
    res = {"status": "infra", "reason": "judge_missing"}
res.update({"config": config, "harness": harness, "model": model, "task": task,
            "agent_rc": int(rc), "agent_verdict": av,
            "wall_sec": int(end) - int(start)})
json.dump(res, open(path, "w"), indent=1)
print(json.dumps(res))
PY
