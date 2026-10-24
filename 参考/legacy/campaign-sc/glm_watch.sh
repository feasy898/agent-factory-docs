#!/bin/bash
# glm_watch.sh <wave_root> [par] — GLM 车道看守：把 jobs-glm.txt 里的 job 解完为止（配额熔断自愈）。
# 不负责判分：整波 ALL SOLVED 后由原 sc_watch.sh（m3.1 车道看守）统一判分。
set -uo pipefail
ROOT="$1"; PAR="${2:-3}"
SC=/home/pan-ding/campaign-sc
mkdir -p "$SC/logs"
LOG=$SC/logs/watch-$(basename "$ROOT")-glm.log
say(){ echo "[$(date '+%F %T')] $*" >> "$LOG"; }
say "glm watch start $ROOT par=$PAR"
while true; do
  if [ ! -f "$ROOT/jobs-glm.txt" ]; then say "no jobs-glm.txt — exit"; break; fi
  remain=0
  while IFS= read -r j; do
    [ -z "$j" ] && continue
    [ -f "$ROOT/runs/$j/work/.done" ] || remain=$((remain+1))
  done < "$ROOT/jobs-glm.txt"
  if [ "$remain" -eq 0 ]; then say "GLM LANE SOLVED (0 remaining)"; break; fi
  rm -f "$SC/QUOTA_GLM"
  bash "$SC/scripts/solve_glm.sh" "$ROOT" "$PAR" >> "$SC/logs/$(basename "$ROOT")-solve-glm.out" 2>&1
  if [ -f "$SC/QUOTA_GLM" ]; then
    say "glm quota blocked, sleep 600"
    sleep 600
  else
    say "round returned ($remain remaining before round), sleep 60 then recheck"
    sleep 60
  fi
done
say "GLM_WATCH_DONE $ROOT"
