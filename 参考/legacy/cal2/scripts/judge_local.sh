#!/bin/bash
# judge_local.sh <config> <task> — rsync the local workflow scratch to anolis and judge there.
# Usage: judge_local.sh <config> <task>   (config: zcode-m3|zcode-m31f|zcode-s5|zcode-router)
set -uo pipefail
ROOT=/home/pan-ding/workspace/临时工作区/temp1
CAL=$ROOT/cal2
CONFIG="$1"; TASK="$2"
LSRC="$CAL/runs/$CONFIG/$TASK/work"
[ -d "$LSRC" ] || { echo "{\"status\":\"infra\",\"reason\":\"no_local_scratch\"}"; exit 2; }
RJOB="/home/pan-ding/bench/runs/$CONFIG-$TASK"
RSCRATCH="$RJOB/work"
ROUT="/home/pan-ding/bench/results/$CONFIG/$TASK.json"
ssh -o BatchMode=yes -o ConnectTimeout=10 anolis "{ rm -rf $RJOB 2>/dev/null; if [ -d $RJOB ]; then docker run --rm -v /home/pan-ding/bench/runs:/runs python:3.11-slim rm -rf /runs/$CONFIG-$TASK >/dev/null 2>&1; fi; } && mkdir -p $RSCRATCH $(dirname $ROUT)" 2>/dev/null
rsync -a --exclude '.tmp' --exclude 'node_modules' "$LSRC/" "anolis:$RSCRATCH/" 2>/dev/null
ssh -o BatchMode=yes -o ConnectTimeout=10 anolis "bash /home/pan-ding/bench/scripts/judge.sh /home/pan-ding/bench/tasks/$TASK $RSCRATCH $ROUT" 2>/dev/null
ssh -o BatchMode=yes -o ConnectTimeout=10 anolis "cat $ROUT" 2>/dev/null
