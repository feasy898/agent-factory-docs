#!/bin/bash
# spotcheck.sh — determinism re-judge from existing remote scratches (no local dependency).
set -u
B=/home/pan-ding/bench
mkdir -p /tmp/spotcheck
: > /tmp/spotcheck/summary
for t in hello-world analyze-access-logs count-call-stack tree-directory-parser solve-maze-challenge; do
  s="$B/runs/zcode-m31f-$t/work"
  if [ ! -d "$s" ]; then echo "$t NO_REMOTE_SCRATCH" >> /tmp/spotcheck/summary; continue; fi
  bash "$B/scripts/judge.sh" "$B/tasks/$t" "$s" "/tmp/spotcheck/$t.json" < /dev/null
  echo "$t -> $(cat /tmp/spotcheck/$t.json)" >> /tmp/spotcheck/summary
done
echo SPOTCHECK_DONE >> /tmp/spotcheck/summary
