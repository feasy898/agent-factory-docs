#!/bin/bash
# sc_watch.sh <wave_root> [par] — SC 波次看守：解题（配额熔断自愈）→ 全部完成 → v5 判分。
set -uo pipefail
ROOT="$1"; PAR="${2:-4}"
SC=/home/pan-ding/campaign-sc
mkdir -p "$SC/logs"
LOG=$SC/logs/watch-$(basename "$ROOT").log
say(){ echo "[$(date '+%F %T')] $*" >> "$LOG"; }
say "watch start $ROOT par=$PAR"
while true; do
  tot=$(find "$ROOT/runs" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | wc -l)
  dn=$(find "$ROOT/runs" -path "*/work/.done" 2>/dev/null | wc -l)
  if [ "$tot" -gt 0 ] && [ "$dn" -ge "$tot" ]; then say "ALL SOLVED ($dn/$tot)"; break; fi
  rm -f "$SC/QUOTA"
  bash "$SC/scripts/solve_sc.sh" "$ROOT" "$PAR" >> "$SC/logs/$(basename "$ROOT")-solve.out" 2>&1
  if [ -f "$SC/QUOTA" ]; then
    say "quota blocked, sleep 600"
    sleep 600
  else
    say "round returned, sleep 60 then recheck"
    sleep 60
  fi
done
say "judging $ROOT"
bash "$SC/scripts/sc_judge.sh" "$ROOT" 4 >> "$SC/logs/$(basename "$ROOT")-judge.out" 2>&1
say "JUDGE_DONE $ROOT"
