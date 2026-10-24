#!/bin/bash
# sc3_m31_watch.sh <root> <par> — SC3 m3.1 车道 watcher：跑到 jobs-m31.txt 全 done；不判分（GLM watcher 终局统一判）
set -uo pipefail
ROOT="$1"; PAR="${2:-1}"
SC="$(dirname "$ROOT")"
say(){ echo "[$(date '+%F %T')] $*" >> "$SC/logs/sc3-m31.watch.log"; }
say "sc3 m31 watch start $ROOT par=$PAR"
while true; do
  remain=0
  while read -r job; do
    [ -f "$ROOT/runs/$job/work/.done" ] || remain=$((remain+1))
  done < "$ROOT/jobs-m31.txt"
  [ "$remain" -eq 0 ] && break
  rm -f "$SC/QUOTA_M31"
  bash "$SC/scripts/sc3_run_m31.sh" "$ROOT" "$PAR" >> "$SC/logs/sc3-m31-run.out" 2>&1
  if [ -f "$SC/QUOTA_M31.infra127" ]; then say "INFRA127 — 停止"; exit 43; fi
  if [ -f "$SC/QUOTA_M31" ]; then say "m31 quota blocked, sleep 600"; sleep 600
  else say "m31 round returned ($remain remaining before round), sleep 60"; sleep 60; fi
done
say "M31_ALL_DONE $ROOT"
