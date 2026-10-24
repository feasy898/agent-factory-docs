#!/bin/bash
# resume_after_anolis_back.sh — run when anolis is reachable again (one-shot recovery for m31f-r2)
set -u
CAL=/home/pan-ding/workspace/临时工作区/temp1/cal2
cd "$CAL" || exit 1
echo "[1] anolis state:"
ssh anolis 'df -h / | tail -1; ls /home/pan-ding/bench/results/zcode-m31f-r2/*.json 2>/dev/null | wc -l; docker ps -q | wc -l' || { echo "ANOLIS_STILL_DOWN"; exit 1; }
echo "[2] disk guard + prune if tight:"
ssh anolis 'a=$(df --output=avail -BG / | tail -1 | tr -dc 0-9); if [ "${a:-0}" -lt 6 ]; then docker image prune -f >/dev/null 2>&1; docker ps -aq --filter status=exited | xargs -r docker rm >/dev/null 2>&1; fi; df -h / | tail -1'
echo "[3] push flood redo content + rejudge flood:"
rsync -a --exclude '.tmp' runs/zcode-m31f-r2/flood-monitoring-basic/work/ anolis:/home/pan-ding/bench/runs/zcode-m31f-r2/flood-monitoring-basic/work/
ssh anolis 's=/home/pan-ding/bench/runs/zcode-m31f-r2/flood-monitoring-basic/work; rm -f /home/pan-ding/bench/results/zcode-m31f-r2/flood-monitoring-basic.json; docker run --rm -v $s:/w python:3.11-slim find /w -mindepth 1 ! -uid $(id -u) -delete >/dev/null 2>&1; bash /home/pan-ding/bench/scripts/judge.sh /home/pan-ding/bench/tasks/flood-monitoring-basic $s /home/pan-ding/bench/results/zcode-m31f-r2/flood-monitoring-basic.json < /dev/null; cat /home/pan-ding/bench/results/zcode-m31f-r2/flood-monitoring-basic.json'
echo "[4] judge remaining tasks (quiet serial):"
ssh anolis 'setsid nohup bash /home/pan-ding/bench/scripts/judge_daemon.sh zcode-m31f-r2 >> /home/pan-ding/bench/logs/final-m31f-r2.log 2>&1 < /dev/null & sleep 3; pgrep -af judge_daemon | grep -v grep | wc -l'
echo "[5] pull all three lanes when daemon finishes, then audit + report"
