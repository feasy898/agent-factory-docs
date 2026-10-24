#!/bin/bash
# guard.sh — anolis ch-mes(ClickHouse 127.0.0.1:5221) 保底守卫（补丁② R2，2026-10-22）
#
# 定位（如实降级，勿夸大）：技术债 D-27 基建连续性保底 + D-26 统一治理前的过渡件。
#   anolis ch-mes 无跨机监督（~/ch-mes/start.sh 注释自认"重启机器后需手工再跑"），
#   但本机 bench-mes 唯一调用方在本机 sched、只写本机 127.0.0.1:5221——anolis ch-mes
#   失联≠本机入库积压。产线级 MES 告警在本机 factory-keepalive ch-mes-local 探活（同
#   补丁交付）；本件只保 anolis 侧 CH 进程连续性。
# 逻辑（pan-ding 用户级 crontab */5 调用；无 root、无 systemd 单元写入）：
#   ping Ok → 记 ok 行，复位状态退出。
#   ping 失败 → 扫 /proc 找 clickhouse server 进程（cmdline 同时含 'clickhouse' 与
#     'server --config-file'）——纯 bash 内联匹配，grep/awk 子进程 argv 会携带检索词
#     造成自匹配（本机 su/bash 实测踩坑），故只在 tr 后用 case 匹配，检索词不进任何
#     子进程 argv：
#     · 进程在（内置 watcher clickhouse-wat 在场或 server 在场）→ 记 unhealthy 行，
#       不执行 start.sh——防与 watcher 秒级重启窗口抢跑双起（端口绑定失败噪音进 ch.log）；
#     · 进程不在 → still_down<3：执行 ~/ch-mes/start.sh（幂等：自带 ping 预检+setsid），
#       等 8s 再探 ping 记 restored/restart_failed；
#     · still_down≥3 → 进入 30min 退避（backoff-until 记 guard-state.json），退避期内
#       进程不在则只记 backoff-skip——防 crash-loop 无限重试与 ch.log 无上限。
# 状态/日志：~/ch-mes/guard-state.json、~/ch-mes/guard.log（超 5MB 截尾保留尾部 1MB）。
#   ~/ch-mes 落 anolis 根分区 ext4（/dev/vda3，findmnt 实测；anolis 仅 /tmp 是 tmpfs），
#   不受 D-24/D-25 tmpfs 脆弱面影响。
# 边界（如实）：只管"拉起进程"，不管"数据修复"——重启后 /data 若损坏需人工 Runbook。
# 测试覆盖（不碰生产）：MCODE_GUARD_CH_DIR / MCODE_GUARD_PING_URL 环境变量可覆盖，
#   便于在沙箱目录+假端口上演练全状态机（crontab 环境无这些变量=走默认生产值）。
set -u
CH_DIR="${MCODE_GUARD_CH_DIR:-$HOME/ch-mes}"
PING_URL="${MCODE_GUARD_PING_URL:-http://127.0.0.1:5221/ping}"
STATE="$CH_DIR/guard-state.json"
LOG="$CH_DIR/guard.log"
START="$CH_DIR/start.sh"
LOG_MAX=5242880     # guard.log 上限 5MB
LOG_KEEP=1048576    # 截尾保留尾部 1MB
BACKOFF_S=1800      # 退避时长 30min
MAX_TRIES=3         # 连续 still_down 达此数进入退避（周期 5min→30min）

ts() { date '+%F %T'; }
glog() { echo "[$(ts)] [$1] $2" >> "$LOG"; }

# ---- 启动前置 ----
mkdir -p "$CH_DIR" 2>/dev/null
if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG" 2>/dev/null || echo 0)" -gt "$LOG_MAX" ]; then
  tail -c "$LOG_KEEP" "$LOG" > "$LOG.trunc" 2>/dev/null && mv "$LOG.trunc" "$LOG"
fi

still_down=$(sed -n 's/.*"still_down" *: *\([0-9][0-9]*\).*/\1/p' "$STATE" 2>/dev/null)
still_down=${still_down:-0}
backoff_until=$(sed -n 's/.*"backoff_until" *: *\([0-9][0-9]*\).*/\1/p' "$STATE" 2>/dev/null)
backoff_until=${backoff_until:-0}
save_state() {  # $1=still_down  $2=backoff_until(epoch, 0=无)
  printf '{"still_down": %s, "backoff_until": %s, "updated": "%s"}\n' \
    "$1" "$2" "$(ts)" > "$STATE.tmp" 2>/dev/null && mv "$STATE.tmp" "$STATE"
}

ping_ok() { [ "$(curl -s -m 5 "$PING_URL" 2>/dev/null)" = "Ok." ]; }

# ---- 主流程 ----
if ping_ok; then
  glog ok "ping Ok."
  [ "$still_down" -eq 0 ] && [ "$backoff_until" -eq 0 ] || save_state 0 0
  exit 0
fi

# 进程在场检查（见头部注释：纯 bash 匹配防自匹配）
proc_found=""
for p in /proc/[0-9]*; do
  [ "${p#/proc/}" = "$$" ] && continue
  [ -r "$p/cmdline" ] || continue
  { argv=$(tr '\0' ' ' < "$p/cmdline"); } 2>/dev/null || continue  # 进程恰在读取间消亡：静默跳过
  case "$argv" in
    *clickhouse*)
      case "$argv" in
        *"server --config-file"*) proc_found="$proc_found ${p#/proc/}" ;;
      esac ;;
  esac
done

if [ -n "$proc_found" ]; then
  glog unhealthy "ping 失败但 clickhouse 进程在场(${proc_found# })——watcher 域，不执行 start.sh（防抢跑双起）"
  exit 0
fi

now=$(date +%s)
if [ "$backoff_until" -gt "$now" ]; then
  glog backoff-skip "ping 失败且进程不在，退避至 $(date -d @"$backoff_until" '+%F %T')，跳过本轮"
  exit 0
fi

if [ "$still_down" -ge "$MAX_TRIES" ]; then
  until_ts=$((now + BACKOFF_S))
  save_state 0 "$until_ts"
  glog backoff-enter "连续 still_down=$still_down ≥$MAX_TRIES，进入退避至 $(date -d @"$until_ts" '+%F %T')（防 crash-loop）"
  exit 0
fi

still_down=$((still_down + 1))
save_state "$still_down" 0
if [ ! -x "$START" ]; then
  glog restart_failed "ping 失败且进程不在，但 $START 不存在/不可执行——无法拉起，需人工（still_down=$still_down）"
  exit 1
fi
glog restart "ping 失败且进程不在，执行 start.sh（第 $still_down/$MAX_TRIES 次尝试）"
"$START" >> "$LOG" 2>&1
sleep 8   # 等 server 监听；若冷启动更慢，下一轮 cron 的 ok 行兜底
if ping_ok; then
  save_state 0 0
  glog restored "start.sh 后 ping Ok.——恢复（本守卫只管拉起进程，不管数据修复）"
else
  glog restart_failed "start.sh 后 ping 仍失败（still_down=$still_down/$MAX_TRIES）"
fi
