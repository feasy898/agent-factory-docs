#!/bin/bash
# rejudge_rest.sh — serial re-judge of the remaining cal2 configs (root-leftover cleanup is in judge_daemon.sh).
set -u
B=/home/pan-ding/bench
for CFG in zcode-m3 zcode-m31f zcode-s5 zcode-router; do
  mkdir -p "$B/results/$CFG"
  echo "[chain] start $CFG $(date +%H:%M:%S)"
  bash "$B/scripts/judge_daemon.sh" "$CFG" >> "$B/logs/final-$CFG.log" 2>&1
  echo "[chain] done $CFG n=$(ls "$B/results/$CFG"/*.json 2>/dev/null | wc -l) $(date +%H:%M:%S)"
done
echo "CHAIN_ALL_DONE $(date +%H:%M:%S)" >> "$B/logs/final-chain.log"
