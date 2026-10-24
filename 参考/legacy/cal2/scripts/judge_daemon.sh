#!/bin/bash
# judge_daemon.sh — anolis-side judge loop for a local-lane config (scratch must already be pushed).
# Usage: judge_daemon.sh <config>
set -u
CFG="$1"
B=/home/pan-ding/bench
RES="$B/results/$CFG"
LOG="$B/logs/judge-$CFG.log"
# heavy-image tasks (node/compilers, multi-minute builds) go last so the rest finish first
SLOW="solve-maze-challenge modernise modernize-scientific-stack portfolio-optimization rare-mineral-allocation path-tracing-reverse feal-linear-cryptanalysis largest-eigenval"
ORDER=/tmp/judge-order-$CFG.txt
: > "$ORDER"
while read -r t; do [ -z "$t" ] && continue; case " $SLOW " in *" $t "*) ;; *) echo "$t" >> "$ORDER";; esac; done < "$B/jobs/cal2_tasks.txt"
for t in $SLOW; do echo "$t" >> "$ORDER"; done
mkdir -p "$RES"
for r in 1 2; do
  todo=0
  while read -r t; do
    [ -z "$t" ] && continue
    [ -s "$RES/$t.json" ] && continue
    todo=$((todo+1))
    freeg=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
    if [ "${freeg:-0}" -lt 3 ]; then
      echo "PAUSE_LOW_DISK ${freeg}G at $t" >> "$LOG"; sleep 120; continue
    fi
    s="$B/runs/$CFG/$t/work"
    [ -d "$s" ] || s="$B/runs/$CFG/$t/scratch"
    if [ ! -d "$s" ] || [ -z "$(ls -A "$s" 2>/dev/null)" ]; then
      echo "{\"status\":\"fail\",\"reason\":\"no_artifacts_produced\"}" > "$RES/$t.json"
      echo "$t -> no_artifacts" >> "$LOG"; continue
    fi
    # drop root-owned leftovers from earlier judge runs (test containers write build artifacts
    # into the mounted scratch as root; those break re-judging and cannot be removed as $USER)
    docker run --rm -v "$s:/w" python:3.11-slim find /w -mindepth 1 ! -uid "$(id -u)" -delete >/dev/null 2>&1
    bash "$B/scripts/judge.sh" "$B/tasks/$t" "$s" "$RES/$t.json" < /dev/null
    echo "$t -> $(cat "$RES/$t.json" 2>/dev/null)" >> "$LOG"
    docker ps -q --filter "ancestor=tbtask-$t:latest" | xargs -r docker rm -f >/dev/null 2>&1
  done < "$ORDER"
  remaining=$(while read -r t; do [ -z "$t" ] && continue; [ -s "$RES/$t.json" ] || echo x; done < "$ORDER" | wc -l)
  echo "round $r: judged=$todo remaining=$remaining $(date +%H:%M:%S)" >> "$LOG"
  [ "$remaining" -eq 0 ] && break
done
echo "DAEMON_DONE $CFG remaining=$remaining" >> "$LOG"
