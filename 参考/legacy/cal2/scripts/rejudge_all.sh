#!/bin/bash
# rejudge_all.sh — re-judge every cal2 config whose scratch survives, under the FIXED base images.
# Old verdicts are kept as <cfg>.prefix/ for before/after comparison.
set -u
B=/home/pan-ding/bench
for CFG in cal2-grok47 zcode-m3 zcode-m31f zcode-s5 zcode-router; do
  RES="$B/results/$CFG"
  if [ -d "$B/results/${CFG}.prefix" ]; then echo "[rej] $CFG already re-judged"; continue; fi
  if [ ! -d "$RES" ]; then mkdir -p "$RES"; fi
  # archive old verdicts (keep the last known state for comparison)
  mkdir -p "$B/results/${CFG}.prefix"
  for f in "$RES"/*.json; do [ -e "$f" ] && mv "$f" "$B/results/${CFG}.prefix/"; done
  echo "[rej] starting $CFG at $(date +%H:%M:%S)"
  bash "$B/scripts/judge_daemon.sh" "$CFG" >> "$B/logs/rejudge-$CFG.log" 2>&1
  echo "[rej] done $CFG remaining=$(ls "$RES"/*.json 2>/dev/null | wc -l) at $(date +%H:%M:%S)"
done
echo "REJUDGE_ALL_DONE $(date +%H:%M:%S)" >> "$B/logs/rejudge_all.log"
