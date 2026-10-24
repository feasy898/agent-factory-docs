#!/bin/bash
# push_local.sh <config> — push every local scratch for the config to anolis in one rsync pass.
set -u
CFG="$1"
CAL=/home/pan-ding/workspace/临时工作区/temp1/cal2
B=/home/pan-ding/bench
ssh -o BatchMode=yes anolis "rm -rf $B/runs/$CFG-* ; mkdir -p $B/runs"
rsync -a --exclude '.tmp' --exclude 'node_modules' --delete \
  --include '*/' --include 'work/***' --exclude '*' \
  "$CAL/runs/$CFG/" "anolis:$B/runs/$CFG/"
n=$(ssh anolis "ls -d $B/runs/$CFG-*/work 2>/dev/null | wc -l")
echo "pushed configs=$n"
