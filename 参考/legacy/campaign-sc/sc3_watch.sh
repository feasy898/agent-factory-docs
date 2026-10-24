#!/bin/bash
# sc3_watch.sh <root> <par> — SC3 watcher：跑直到全部 .done，配额自愈，终局判分。
set -uo pipefail
ROOT="$1"; PAR="${2:-2}"
SC="$(dirname "$ROOT")"
say(){ echo "[$(date '+%F %T')] $*" >> "$SC/logs/$(basename "$ROOT").watch.log"; }
say "sc3 watch start $ROOT par=$PAR"
while true; do
  remain=0
  while read -r job; do
    [ -f "$ROOT/runs/$job/work/.done" ] || remain=$((remain+1))
  done < "$ROOT/jobs-sc3.txt"
  [ "$remain" -eq 0 ] && break
  rm -f "$SC/QUOTA_GLM"
  bash "$SC/scripts/sc3_run.sh" "$ROOT" "$PAR" >> "$SC/logs/sc3-run.out" 2>&1
  if [ -f "$SC/QUOTA_GLM.infra127" ]; then say "INFRA127 — 停止"; exit 43; fi
  if [ -f "$SC/QUOTA_GLM" ]; then say "quota blocked, sleep 600"; sleep 600
  else say "round returned ($remain remaining before round), sleep 60"; sleep 60; fi
done
say "ALL SOLVED"
bash "$SC/scripts/sc_judge.sh" "$ROOT" 4 >> "$SC/logs/sc3-judge.out" 2>&1
say "JUDGE_DONE $ROOT"
