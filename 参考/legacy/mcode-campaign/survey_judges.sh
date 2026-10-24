#!/bin/bash
echo "judge_all_v4 procs: $(ps aux | grep -c '[j]udge_all_v4')"
for p in $(ps -ef | grep "[r]emote_judge_v4" | awk '{print $2}'); do
  cmd=$(ps -p $p -o cmd | tail -1)
  w=$(echo "$cmd" | awk '{print $4}' | sed 's|.*/||; s|-remote||')
  t=$(echo "$cmd" | awk '{print $5}')
  c=$(ps --ppid $p -o cmd 2>/dev/null | tail -1 | cut -c1-40)
  echo "$w/$t: $c"
done | sort
