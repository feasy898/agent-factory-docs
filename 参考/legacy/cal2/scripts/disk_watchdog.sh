#!/bin/bash
# Local disk watchdog: log free space; if < 20G, clean stale python temp dirs (>6h) in /tmp.
LOG=/home/pan-ding/workspace/临时工作区/temp1/cal2/logs/disk.log
while true; do
  free=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
  echo "$(date -Is) free=${free}G" >> "$LOG"
  if [ "$free" -lt 20 ]; then
    n=$(find /tmp -maxdepth 1 -name "tmp*" -mmin +360 2>/dev/null | wc -l)
    find /tmp -maxdepth 1 -name "tmp*" -mmin +360 -exec rm -rf {} + 2>/dev/null
    free2=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
    echo "$(date -Is) LOW DISK: cleaned $n stale tmp dirs, free now ${free2}G" >> "$LOG"
  fi
  sleep 300
done
