#!/bin/bash
# prep_all.sh — prepare inputs + instructions for all 51 tasks (fixed prepare_task.py)
set -uo pipefail
ROOT=/home/pan-ding/workspace/临时工作区/temp1
SRC=$ROOT/tb-tasks/original-tasks
CAL=$ROOT/cal2
fail=0
while read -r t; do
  [ -z "$t" ] && continue
  mkdir -p "$CAL/inputs/$t"
  if ! python3 "$CAL/scripts/prepare_task.py" "$SRC/$t" "$CAL/inputs/$t" "$CAL/instr/$t.md" > "$CAL/logs/prep-$t.log" 2>&1; then
    echo "PREP_FAIL $t: $(tail -1 $CAL/logs/prep-$t.log)"; fail=$((fail+1))
  fi
done < "$ROOT/bench/tasks_ordered.txt"
echo "prep done, failures=$fail"
