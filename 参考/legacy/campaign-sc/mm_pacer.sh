#!/bin/bash
# mm_pacer.sh — SC3 m31 车道自动配速器（保护 MiniMax 5h 窗口，主会话 confirm 战役优先）。
# 每10分钟看一次账户级近1h燃烧（runtime-state.sqlite 逐轮记账）:
#   burn1h > 20M/h -> 暂停我的 m31 车道（杀 watcher，保底不再消耗）
#   burn1h > 12M/h -> 降到 -P 1
#   否则           -> 保持 -P 2（若不在跑则拉起）
# 注意: 所有 kill 模式只出现在本文件内（不在任何进程 cmdline 里），无自杀风险。
SC=/home/pan-ding/campaign-sc
ROOT=$SC/sc3
LOG=$SC/logs/mm-pacer.log
HIGH=20000000    # 20M/h
MID=12000000     # 12M/h
say(){ echo "[$(date '+%F %T')] $*" >> $LOG; }

burn1h(){
  python3 - <<'EOF'
import sqlite3, time
con = sqlite3.connect("file:/home/pan-ding/.minimax/v2/sqlite/runtime-state.sqlite?mode=ro", uri=True)
t0 = (time.time() - 3600) * 1000
r = con.execute("select coalesce(sum(input_tokens),0)+coalesce(sum(output_tokens),0)+coalesce(sum(reasoning_tokens),0) from local_runtime_token_usage where ts >= ?", (t0,)).fetchone()
print(int(r[0]))
EOF
}

cur_par(){  # 输出当前 m31 watcher 的并发参数
  ps -ef | grep "[s]c3_m31_watch" | grep -oE "par=?[0-9]+| [0-9]+$" | grep -oE "[0-9]+" | head -1
}

lane_alive(){ pgrep -f "[s]c3_m31_watch" >/dev/null; }

stop_lane(){
  pkill -f "[s]c3_m31_watch"; pkill -f "[s]c3_run_m31"
  sleep 1
  # 杀在途 mcode（仅限 sc3 车道工作目录）
  for pid in $(pgrep -f "exec.*campaign-sc/sc3"); do
    grep -q "campaign-sc/sc3" /proc/$pid/cmdline 2>/dev/null && kill -9 $pid 2>/dev/null
  done
}

start_lane(){
  setsid nohup bash $SC/scripts/sc3_m31_watch.sh $ROOT $1 >/dev/null 2>&1 </dev/null &
}

say "pacer start (HIGH=${HIGH} MID=${MID})"
while true; do
  b=$(burn1h)
  p=$(cur_par); p=${p:-0}
  if   [ "$b" -gt "$HIGH" ]; then
    if lane_alive; then stop_lane; say "burn ${b} > HIGH -> 暂停 m31 车道"; fi
  elif [ "$b" -gt "$MID" ]; then
    if [ "$p" != "1" ]; then stop_lane; sleep 2; start_lane 1; say "burn ${b} > MID -> 降 -P 1"; fi
  else
    if ! lane_alive || [ "$p" != "2" ]; then
      if lane_alive; then stop_lane; sleep 2; fi
      start_lane 3; say "burn ${b} 正常 -> 保 -P 2"
    fi
  fi
  sleep 600
done
