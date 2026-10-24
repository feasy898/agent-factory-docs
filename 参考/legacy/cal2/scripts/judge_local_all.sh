#!/bin/bash
# judge_local_all.sh <config> — judge every task of a local workflow lane that isn't judged yet.
set -uo pipefail
ROOT=/home/pan-ding/workspace/临时工作区/temp1
CAL=$ROOT/cal2
CONFIG="$1"
LOCALRES="$CAL/results/$CONFIG"
mkdir -p "$LOCALRES"
n=0
while read -r t; do
  [ -z "$t" ] && continue
  if [ -s "$LOCALRES/$t.json" ]; then continue; fi
  # only judge if the agent actually ran (work dir non-empty)
  if [ ! -d "$CAL/runs/$CONFIG/$t/work" ] || [ -z "$(ls -A "$CAL/runs/$CONFIG/$t/work" 2>/dev/null)" ]; then
    echo "{\"status\":\"fail\",\"reason\":\"no_artifacts_produced\"}" > "$LOCALRES/$t.json"
    continue
  fi
  out=$(bash "$CAL/scripts/judge_local.sh" "$CONFIG" "$t" < /dev/null)
  echo "$out" > "$LOCALRES/$t.json"
  echo "$t -> $out"
  n=$((n+1))
done < "$CAL/tasks.txt"
echo "judged $n tasks for $CONFIG"
