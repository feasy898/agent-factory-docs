#!/usr/bin/env python3
"""factory-keepalive.py — 黑灯工厂守护进程的守护（keepalive 常驻，30s 一轮）。

【2026-10-26 §三-2 退役改造（ADR-008，运营者裁决 B·放弃 D1/D3 全量臂并退役）】
旧 bench 链（factory-sched/mcode-dispatch/cb-run/ch-mes-local 锚/anolis-proxy-8124 等）
已退役，本脚本看护清单收敛为观察期 4 对象：

  watch        python3 tools/factory-watch.py（判据不变：进程在+watch-state.json<300s）
  dash         python3 -m http.server 8790（看板，判据=进程在）
  af-execline  af 统一执行面判活（订单驱动非守护）：af-order/af-execline 进程在场
               或 WS/af-state/orders/ 最近订单 ledger 心跳<72h；空闲=amber 报警不拉起
  mes-ch       mingda MES（100.64.0.2:15221）查询级连通探活（原 ch-mes-local 探针
               原样复用，仅更名登记）；失联=四类告警码只报警不拉起

旧 9 对象（main-sched/exp-sched/cb-run/image-feed/mcode-dispatch/ch-mes-local/
anolis-proxy-8124）的判活/拉起函数保留为无引用死码，待观察期满文件归档批
（参考/legacy/）一并清理——见 计划/研究组/退役执行记录-20261026.md。
停机登记：8 对象 MES kind=retired（line_id=bench-retire，2026-10-26 01:03）。

背景（2026-10-21 复盘，技术债 D-3 韧性层）：tailnet 闪断把主/实验线调度器与 cb-run
杀了 50 分钟无人自动拉起（靠人工巡检发现）。下述 9 对象描述为 2026-10-21~10-24
历史形态（退役存档参考，现行看护对象以上表为准）：

  main-sched   python3 tools/factory-sched.py（无 AF_SCHED_*）
               判据=进程在 且 /tmp/factory-status.json mtime<300s；任一失效→杀残进程重启
  exp-sched    同脚本 + env AF_SCHED_GRAPH=/tmp/factory2-graph.json
                          AF_SCHED_STATUS=/tmp/factory2-status.json
                          AF_SCHED_LOG=/tmp/factory2.log
                          BIN=<WS>/af/target/debug/af-bench-fix2
               判据=进程 env 含 AF_SCHED 且 /tmp/factory2-status.json mtime<300s
  watch        python3 tools/factory-watch.py（env AF_WATCH_EXTRA_DIRS=实测现值）
               判据=进程在 且 状态观测/watch-state.json mtime<300s；
               拉起 watchdog 后连带检查看板 http.server 8790（死则一并拉起，绑 127.0.0.1）
  cb-run       python3 tools/cb-run.py run；判据=/tmp/cb-run.pid 指向活着的 cb-run 进程；
               拉起前清陈旧 pidfile（防其单实例守卫拒绝双开误判）
  image-feed   python3 tools/local-image-feed.py；判据=进程在；
               仅当 120 名单尚有缺镜像时才重启（缺=0 为正常完成退出，不重启只记一条）；
               docker 不可读则只报警不动手
  mcode-dispatch python3 tools/mcode-dispatch.py run（官方 harness 对照线，anolis 解题+本机判分）；
               判据=/tmp/mcode-dispatch/dispatch.pid 指向活进程（/proc 扫描兜底）
               且 /tmp/mcode-dispatch/heartbeat mtime<2400s（单题 solve 最长 30min，
               心跳按题相位刷新，阈值须大于单题时长）；QUOTA 熔断完成退出属正常，
               但 keepalive 无法区分熔断与崩溃——重启幂等（state 断点续跑+pidfile 单实例
               守卫拒绝双开），熔断态重启后 worker 立即跳完剩余队列自然退出
  ch-mes-local MES ClickHouse 探活（补丁② R2 + 补丁④查询级，2026-10-22；MES 迁
               mingda-website 后指向 100.64.0.2:15221，本机 127.0.0.1:5221 旧实例只读
               48h 回滚锚不在此探活范围——见 计划/研究组/mes迁移mingda-交付.md）；
               判活=**一条极轻 SELECT 查询级探针**（补丁④：/ping 探不到查询级 500，
               10-21 两次 500 期间探针全程绿灯=mes500 根因报告 §4 C 组缺口 1）；
               失败分四类给不同告警码（conn/auth/query/timeout，见 ch_mes_probe）；
               失联处置=只报警不拉起——mingda 侧已有 systemd 单元 clickhouse-factory.service
               （Restart=always，2026-10-22 14:28 起在役）自动拉起，跨机自动拉起越权仍不做；
               klog + 状态观测/alarms.log 追加（类别码）
               + MES kind=ch_mes_down（写失败不致命），30min 去重用本进程自有状态键
               （watch 的 alarm_logged 在 watch 进程内，不可共享；类别翻转立即重报）。
               告警主通道是文件（klog/alarms.log）：CH 挂时照样可报，不落「用 MES 报
               MES 挂」悖论。anolis 侧 ch-mes 另有 guard.sh+用户级 crontab 保底
               （补丁②，定位=D-27 基建连续性，非产线告警面）。
  anolis-proxy-8124 anolis 8124=d36p-proxy 净化白名单代理（只放行 CONNECT
               agent.minimaxi.com:443 的模型网关，purified/containerized 跑批线共用
               出口；D-43 归还，2026-10-24 入监——曾静默死 13h 引发连锁误诊）。
               判活=ssh 端口探活（明文 GET 拿到任意 HTTP 码即活——本体对非 CONNECT
               一律 403=预期；000/空=死）；ssh 失联=判不准只报警不拉起（拉起也走
               ssh 必失败，30min 去重，klog+alarms.log）；恢复=ssh 调 anolis:~/
               mcode-swev/start-proxy-8124.sh（跑批组拉起方式固化：setsid+nohup+
               日志追加；本体自持 flock 单实例守卫，脚本幂等可重入）；失败上限/
               告警照抄既有对象（防抖 2 次/10min+MES keepalive_restart/suppressed）。
  gc-watch     anolis /data sweb.eval 镜像池 GC 看护（补丁③ R2，2026-10-22；非判活
               对象，是 one_round 内的额外步骤）。只做本地判断：latest.json 的
               anolis.disk['/data'].use_pct ≥85（watch 每轮 ssh 刷新，本地读；文件
               mtime>300s 视为 watch 断供不触发）且距上次成功 GC>6h（读耐久证据
               状态观测/img-gc-evidence.jsonl，不依赖 tmpfs）且距上次 spawn>1200s
               （内存防抖，重启复位由子进程 flock 兜底）→ spawn python3 tools/
               img-gc.py apply --host anolis（子命令在前——argparse 子解析器持
               --host，J3 实测旧序「--host 在前」100% 死于 argparse rc2 且零证据；
               setsid 脱离即返回，flock/ssh/prune 全在
               子进程，子进程 1200s 硬超时自杀）——严格非阻塞，绝不让自己成为 7 个
               看护对象的新单点。≥88% 时 img-gc 自行停手只回报（第二道）。A9：证据
               件有未告警的 apply 结果且距上次报警>30min → alarms.log 记一行
               （code=gc-watch），去重时间戳记回耐久证据件。

正确姿势要点（实测自今日现值，含手工巡检惯例）：
  · 全部 subprocess stdin=DEVNULL（mingda 教训）、cwd=WS、start_new_session（=setsid 脱离）、
    stdout/stderr 追加到各对象既有日志文件（/tmp/factory{,2}.log、/tmp/factory-watch.log、
    /tmp/factory-dash.log、/tmp/cb-run.log、/tmp/local-image-feed.log）。
  · 杀残进程用 /proc 扫描的精确 pid（argv0 basename + environ 判别主/实验线），
    不用 pgrep -f（防自匹配）。杀调度器后按厂内惯例清理其 af-bench/cnb-relay 孤儿
    （ppid==1 且 exe=该调度器 BIN，或 cmdline 含 cnb-relay.py）——防重启后同 --out 重复派发。
  · 防抖：同一对象 10 分钟内最多重启 2 次，超限只报警（本地日志 + MES kind=keepalive_suppressed）。
  · 每次拉起记 /tmp/factory-keepalive.log + MES 事件（kind=keepalive_restart，
    work_order_id=factory-keepalive-<对象>，直 INSERT af_mes.mes_event，写失败不致命）。
  · 刚拉起的对象有 150s 宽限期：宽限内只查进程在场、豁免状态文件新鲜度（旧文件 mtime
    是上一世的，避免刚重启即被判 stale 造成抖环；进程真死仍会触发重启→防抖兜底）。

控制文件韧性层（技术债 D-25，2026-10-21 立项当日归还）：/tmp 图与控制文件曾遭三连删
（factory-graph/factory2-graph/fix2ab-sample，10-21 13:00-14:04，凶手未明），彼时
keepalive 无存在性校验，删后产线盲跑（调度器 load_graph 读失败仅记日志、持旧内存继续
跑）。现每轮巡检最前面先过 graph_guard：两图缺失即从 工具状态备份/ 的最近备份原子
恢复（时间戳滚动件优先、平铺快照兜底；无可用备份只告警不凭空造图），恢复记高亮日志
行 ">>> RESTORED <file> from <backup> <<<" + MES 事件；心跳前再做新鲜滚动备份
backup_graphs（原子拷入 工具状态备份/，带时间戳、每图保留最近 5 份，防备份本身
被删/变旧）。

已知边界（自我认知）：本脚本自身崩溃没有任何进程拉它——单实例守卫 /tmp/factory-keepalive.pid；
自身死亡无法自愈，靠计划内 cron 人工/厂长巡检兜底（巡检 prompt 已存在，发现
/tmp/factory-keepalive.pid 失活即重启本脚本）。密钥零明文：本脚本不读不写任何令牌。

用法:
  factory-keepalive.py                 # 常驻（默认 30s 一轮）
  factory-keepalive.py --once          # 单轮真实巡检+处置
  factory-keepalive.py --dry-run       # 单轮干跑：只打印将执行的判活结论与命令，不动手
  factory-keepalive.py --print-commands  # 打印全部对象的拉起命令/env/日志路径（不动手不判活）
  factory-keepalive.py --interval N    # 自定义轮询秒数
"""
import argparse
import base64
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

WS = "/home/pan-ding/workspace/agent黑灯工厂"
PIDFILE = "/tmp/factory-keepalive.pid"
KLOG = "/tmp/factory-keepalive.log"
def _mes_conn(url=None):
    """MES ClickHouse 连接 → (base_url, auth_header)。

    2026-10-22 MES 由 pandev-comp 本机迁至 mingda-website（tailnet 100.64.0.2:15221，
    迁移动机/对账/回滚见 计划/研究组/mes迁移mingda-交付.md；本机 127.0.0.1:5221 旧实例
    保留只读 48h 作回滚锚）。解析顺序：入参 url > 环境变量 MES_CH_URL > 0600 凭据文件
    ~/.config/mes-ch/url > 缺省新 MES 地址。凭据可写 user:pass@host 形式（urllib 不
    解析 URL 内嵌凭据，故在此拆出转 Basic 头）；口令明文按密钥纪律只存 0600 文件，
    不进任何文档/回报。缺文件且无 env 落到无凭据地址→401 显性失败，不静默写旧锚点。
    """
    if url is None:
        url = os.environ.get("MES_CH_URL")
    if not url:
        try:
            with open(os.path.expanduser("~/.config/mes-ch/url"), encoding="utf-8") as f:
                url = f.read().strip()
        except OSError:
            url = "http://100.64.0.2:15221"
    auth = None
    if "@" in url:
        scheme, rest = url.split("://", 1)
        userinfo, hostpart = rest.split("@", 1)
        url = f"{scheme}://{hostpart}"
        auth = "Basic " + base64.b64encode(userinfo.encode()).decode()
    return url, auth


CH, CH_AUTH = _mes_conn()
ALARMS_LOG = f"{WS}/状态观测/alarms.log"   # 与 watch 同一告警文件（补丁②：ch-mes-local 主通道）
CHMES_DEDUP_S = 1800                       # ch-mes-local 失联报警去重窗（同 watch DEDUP_WINDOW）
LATEST_JSON = f"{WS}/状态观测/latest.json"  # watch 产物（anolis.disk['/data'].use_pct 在内）
GC_EVIDENCE = f"{WS}/状态观测/img-gc-evidence.jsonl"   # 耐久证据（补丁③：迟滞+A9 去重源）
GC_EVIDENCE_TMP = "/tmp/img-gc-evidence.jsonl"
GC_TRIGGER_PCT = 85      # /data use_pct 触发线（10-22 台账口径，巡检日志:157）
GC_MIN_INTERVAL = 6 * 3600   # 距上次成功 GC 迟滞
GC_SPAWN_SUPPRESS = 1200     # spawn 防抖（=子进程硬超时上界；重启复位由 flock 兜底）
GC_ALARM_DEDUP_S = 1800      # A9 结果报警去重（记回耐久证据件）
GC_DRILL_FLAG = f"{WS}/状态观测/img-gc-drill.flag"   # P0-2 drill 旗标（自毁；只读 plan 演练通道，方案 §3.3-a/§5）

INTERVAL = 30          # 轮询周期（s）
STALE_S = 300          # 状态/watch-state 文件新鲜度阈值（s）
RESTART_WINDOW = 600   # 防抖窗（s）
RESTART_MAX = 2        # 窗内最多重启次数
GRACE_S = 150          # 刚拉起后的判活宽限（s，豁免文件新鲜度）
HEARTBEAT_EVERY = 20   # 每 N 轮写一行全绿心跳（20×30s=10min）

# ---------- 组合补丁③（T0-5 §8.2）：mcode-dispatch 完成态判断（止抖环）----------
# 状态文件路径可用环境变量指路（MCODE_DISPATCH_STATE），供 §8.2 验收②「副本 state
# 注入假键、不污染真 state」演练；缺省=真 state（现行行为不变）。
MCODE_STATE = os.environ.get("MCODE_DISPATCH_STATE", "/tmp/mcode-dispatch/state.json")
# pending 判据：phase 缺失(None)/solving/collected = 未完成；judged/quota/prepare_failed/error = 终态
MCODE_PENDING_PHASES = (None, "solving", "collected")
MCODE_DRAIN_LOG_S = 3600  # queue_drained 一小时记一条（防刷屏）

# ---------- D-25 控制文件韧性：图存在性校验+自动恢复+滚动备份 ----------
BACKUP_DIR = f"{WS}/工具状态备份"
GRAPH_FILES = [("factory-graph", "/tmp/factory-graph.json"),
               ("factory2-graph", "/tmp/factory2-graph.json")]
BACKUP_KEEP = 5                    # 每图保留最近 N 份时间戳滚动备份
BACKUP_TS = "%Y%m%d-%H%M%S"        # 滚动备份时间戳（定长，字典序=时序）

# 实测现值（2026-10-21 00:4x 逐 /proc 核对），改动需同步更新此处与巡检日志
EXP_ENV = {
    "AF_SCHED_GRAPH": "/tmp/factory2-graph.json",
    "AF_SCHED_STATUS": "/tmp/factory2-status.json",
    "AF_SCHED_LOG": "/tmp/factory2.log",
    "BIN": f"{WS}/af/target/debug/af-bench-fix2",
}
WATCH_ENV = {"AF_WATCH_EXTRA_DIRS": "/tmp/bench-fix2-rerun-*,/tmp/factory2-status.json"}
MAIN_BIN = f"{WS}/af/target/debug/af-bench"
DASH_PORT = "8790"
DASH_DIR = f"{WS}/状态/看板"

last_spawn = {}        # name -> epoch（最近一次本脚本拉起时刻，算宽限期）
last_feed_idle_log = 0.0
last_dispatch_drain_log = 0.0  # mcode-dispatch queue_drained 上次记日志时刻（1h 去重）
last_chmes_alarm = 0.0  # ch-mes-local 上次报警时刻（30min 去重，本进程自有状态键）
last_chmes_alarm_cls = None  # 上次报警的失败类别（类别翻转立即重报，不被去重吞掉）
last_chmes_fail = None      # 最近一次查询探针失败 (cls, detail)（check→fix 传递）
last_gc_spawn = 0.0     # gc-watch 上次 spawn 时刻（1200s 防抖，内存态；重启复位由 flock 兜底）
last_hb_round = -1


def now_s():
    return time.strftime("%F %T")


def klog(name, msg):
    line = f"[{now_s()}] [{name}] {msg}"
    print(line, flush=True)
    try:
        with open(KLOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


# ---------- MES（直 INSERT，factory-sched ch_insert 同款；失败不致命） ----------

def mes_event(name, kind):
    body = json.dumps({
        "work_order_id": f"factory-keepalive-{name}",
        "occurred_at": now_s(),
        "event_id": f"factory-keepalive-{name}-{kind}-{int(time.time())}-{os.getpid()}",
        "line_id": "keepalive",
        "station_id": name,
        "kind": kind,
        "quantity": 1,
    }, ensure_ascii=False) + "\n"
    req = urllib.request.Request(
        CH + "/?query=" + urllib.parse.quote(
            "INSERT INTO af_mes.mes_event (work_order_id, occurred_at, event_id, "
            "line_id, station_id, kind, quantity) FORMAT JSONEachRow"),
        data=body.encode(), method="POST")
    if CH_AUTH:
        req.add_header("Authorization", CH_AUTH)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
        return True
    except Exception as e:
        klog(name, f"MES 写入失败（不致命）: {e}")
        return False


# ---------- /proc 工具（不使用 pgrep -f，防自匹配） ----------

def scan_pids(match):
    """扫 /proc：argv0 是 python* 且任一后续参数 basename 命中脚本名。match(argv)->bool。"""
    out = []
    me = os.getpid()
    for ent in os.listdir("/proc"):
        if not ent.isdigit() or int(ent) == me:
            continue
        try:
            with open(f"/proc/{ent}/cmdline", "rb") as f:
                argv = [a.decode("utf-8", "replace") for a in f.read().split(b"\0") if a]
        except OSError:
            continue
        if not argv or not os.path.basename(argv[0]).startswith("python"):
            continue
        if match(argv):
            out.append(int(ent))
    return sorted(out)


def pid_argv(pid):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return [a.decode("utf-8", "replace") for a in f.read().split(b"\0") if a]
    except OSError:
        return None


def pid_env(pid):
    env = {}
    try:
        with open(f"/proc/{pid}/environ", "rb") as f:
            for kv in f.read().split(b"\0"):
                if b"=" in kv:
                    k, v = kv.split(b"=", 1)
                    env[k.decode("utf-8", "replace")] = v.decode("utf-8", "replace")
    except OSError:
        pass
    return env


def pid_exe(pid):
    try:
        return os.path.realpath(f"/proc/{pid}/exe")
    except OSError:
        return None


def pid_ppid(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            return int(f.read().rsplit(")", 1)[1].split()[1])
    except (OSError, ValueError, IndexError):
        return None


def sched_pids(which):
    """factory-sched.py 进程，按 environ 分拣主/实验线。which: 'main'|'exp'。"""
    pids = scan_pids(lambda argv: any(os.path.basename(a) == "factory-sched.py" for a in argv[1:]))
    out = []
    for p in pids:
        env = pid_env(p)
        has_af = any(k.startswith("AF_SCHED_") for k in env)
        if which == "exp" and has_af:
            out.append(p)
        elif which == "main" and not has_af:
            out.append(p)
    return out


def file_age(path):
    """文件 mtime 距今秒数；缺失/异常返回 None（视为 stale）。"""
    try:
        return time.time() - os.stat(path).st_mtime
    except OSError:
        return None


def kill_pid(pid, name):
    """精确 pid 杀残进程：SIGTERM → 最多 5s → SIGKILL。"""
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    for _ in range(10):
        if not os.path.exists(f"/proc/{pid}"):
            return
        time.sleep(0.5)
    try:
        os.kill(pid, signal.SIGKILL)
        klog(name, f"SIGKILL 补刀 pid={pid}")
    except ProcessLookupError:
        pass
    time.sleep(0.5)


def reap_orphans(name, bin_path):
    """杀调度器后清理其孤儿（厂内手工重启惯例）：ppid==1 且
    exe==该调度器 BIN，或 cmdline 含 cnb-relay.py。"""
    for ent in os.listdir("/proc"):
        if not ent.isdigit():
            continue
        p = int(ent)
        if pid_ppid(p) != 1:
            continue
        argv = pid_argv(p)
        if not argv or not os.path.basename(argv[0]).startswith("python"):
            continue
        exe = pid_exe(p)
        is_bench_orphan = exe is not None and bin_path and exe == os.path.realpath(bin_path)
        is_relay_orphan = any("cnb-relay.py" in a for a in argv[1:])
        if is_bench_orphan or is_relay_orphan:
            klog(name, f"清理孤儿 pid={p} argv={' '.join(argv[:4])}")
            kill_pid(p, name)


def spawn(name, cmd, logfile, extra_env=None, strip_env=()):
    """正确姿势拉起：stdin=DEVNULL、cwd=WS、setsid 脱离、日志追加。返回 pid 或 None。"""
    env = {k: v for k, v in os.environ.items() if k not in strip_env}
    env.update(extra_env or {})
    env["AF_KEEPALIVE_SPAWN"] = "1"   # 供事后辨认本脚本经手拉起的进程
    try:
        with open(logfile, "ab", 0) as lf:
            proc = subprocess.Popen(
                cmd, cwd=WS, env=env, stdin=subprocess.DEVNULL,
                stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)
        klog(name, f"拉起 pid={proc.pid} cmd={' '.join(cmd)} "
                   f"env+={sorted(extra_env or {})} log={logfile}")
        return proc.pid
    except Exception as e:
        klog(name, f"拉起失败: {e}")
        return None


class Debounce:
    """同对象 10 分钟窗内最多 RESTART_MAX 次重启，超限只报警。"""

    def __init__(self):
        self.hist = {}       # name -> [epoch, ...]
        self.suppressed = {} # name -> epoch（上次"超限报警"记录时刻）

    def allow(self, name, t):
        wins = [x for x in self.hist.get(name, []) if t - x < RESTART_WINDOW]
        self.hist[name] = wins
        if len(wins) >= RESTART_MAX:
            last = self.suppressed.get(name, 0)
            if t - last > RESTART_WINDOW:  # 每窗只报一次
                klog(name, f"ALARM {RESTART_WINDOW}s 内已重启 {len(wins)} 次，超限停止拉起只报警"
                           f"（进程仍死，需人工介入）")
                mes_event(name, "keepalive_suppressed")
                self.suppressed[name] = t
            return False
        return True

    def record(self, name, t):
        self.hist.setdefault(name, []).append(t)


# ---------- 控制文件韧性（D-25） ----------

def _json_ok(path):
    """文件存在且是合法 JSON（备份采纳/恢复候选的准入 sanity gate）。"""
    try:
        with open(path, "rb") as f:
            json.loads(f.read().decode("utf-8", "replace"))
        return True
    except (OSError, ValueError):
        return False


def _atomic_copy(src, dst):
    """原子拷贝：先写 dst 同目录临时名，再 os.replace（=mv）落位。
    图文件可能被调度器并发读写，绝不让半成品出现在目标名上。"""
    tmp = f"{dst}.tmp.{os.getpid()}"
    try:
        with open(src, "rb") as fi, open(tmp, "wb") as fo:
            while True:
                chunk = fi.read(1 << 20)
                if not chunk:
                    break
                fo.write(chunk)
            fo.flush()
            os.fsync(fo.fileno())
        os.replace(tmp, dst)
        return True
    except OSError as e:
        klog("graph", f"原子拷贝失败 {src} → {dst}: {e}")
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False


def _stamped_backups(base):
    """某图的时间戳滚动备份（新→旧）。平铺旧件不归滚动管。"""
    ts_re = re.compile(rf"^{re.escape(base)}\.(\d{{8}}-\d{{6}})\.json$")
    stamped = []
    try:
        for fn in os.listdir(BACKUP_DIR):
            m = ts_re.match(fn)
            if m:
                stamped.append((m.group(1), fn))
    except OSError:
        pass
    stamped.sort(reverse=True)   # 定长时间戳，字典序=时序
    return [os.path.join(BACKUP_DIR, fn) for _, fn in stamped]


def graph_backup_candidates(base):
    """某图在 工具状态备份/ 下的备份候选（新→旧）：
    时间戳滚动件优先，2026-10-21 14:2x 平铺快照兜底。"""
    out = _stamped_backups(base)
    flat = os.path.join(BACKUP_DIR, f"{base}.json")
    if os.path.exists(flat):
        out.append(flat)
    return out


def prune_graph_backups(base):
    """滚动保留最近 BACKUP_KEEP 份时间戳备份（防备份本身堆积/变旧）。"""
    for old in _stamped_backups(base)[BACKUP_KEEP:]:
        try:
            os.unlink(old)
            klog("graph", f"滚动清理旧备份 {os.path.basename(old)}"
                          f"（每图保留最近 {BACKUP_KEEP} 份）")
        except OSError as e:
            klog("graph", f"清理旧备份失败 {old}: {e}")


def backup_graphs():
    """D-25 第二层：心跳前新鲜备份——两图原子拷入 工具状态备份/（时间戳滚动，
    每图保留最近 BACKUP_KEEP 份）。目录本身被删则重建；内容非法 JSON 不采纳。"""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
    except OSError as e:
        klog("graph", f"ALARM 备份目录不可用 {BACKUP_DIR}: {e}")
        return
    ts = time.strftime(BACKUP_TS)
    for base, path in GRAPH_FILES:
        if not os.path.exists(path):
            klog("graph", f"备份跳过：{path} 不存在（交由存在性校验流程处理）")
            continue
        dst = os.path.join(BACKUP_DIR, f"{base}.{ts}.json")
        if not _atomic_copy(path, dst) or not _json_ok(dst):
            klog("graph", f"ALARM 备份未采纳 {path} → {dst}（拷贝失败或内容非法）")
            try:
                os.unlink(dst)
            except OSError:
                pass
            continue
        klog("graph", f"备份 {path} → {os.path.relpath(dst, WS)}"
                      f"（{os.path.getsize(dst)}B）")
        prune_graph_backups(base)


def graph_guard(dry=False):
    """D-25 第一层：控制文件存在性校验+自动恢复。每轮巡检最前面跑，幂等
    （存在即跳过）。缺失→从最近备份（滚动件优先、平铺兜底）原子恢复；
    无可用备份只告警不恢复——绝不凭空造图。返回 (restored, missing)。"""
    restored, missing = [], []
    for base, path in GRAPH_FILES:
        if os.path.exists(path):
            continue
        cands = [p for p in graph_backup_candidates(base)
                 if os.path.exists(p) and _json_ok(p)]
        if not cands:
            klog("graph", f"ALARM 控制文件缺失且无可用备份：{path}"
                          f"（不凭空造图，只记不恢复，需人工介入）")
            missing.append(path)
            continue
        src = cands[0]
        if dry:
            klog("graph", f"[dry-run] {path} 缺失，将从 {src} 恢复（未动手）")
            missing.append(path)
            continue
        if _atomic_copy(src, path):
            klog("graph", f">>> RESTORED {path} from {src} <<<"
                          f"（D-25：控制文件曾被删/丢失，已从最近备份自动恢复）")
            mes_event("graph", "keepalive_graph_restored")
            restored.append(path)
        else:
            klog("graph", f"ALARM 恢复失败 {path} from {src}（需人工介入）")
            missing.append(path)
    return restored, missing


# ---------- 五对象判活（返回 (alive, detail)） ----------

def check_main_sched(t):
    pids = sched_pids("main")
    age = file_age("/tmp/factory-status.json")
    fresh = age is not None and age < STALE_S
    if t - last_spawn.get("main-sched", 0) < GRACE_S:
        return bool(pids), f"grace 宽限内：进程={pids or '无'}（豁免新鲜度）"
    ok = bool(pids) and fresh
    return ok, f"进程={pids or '无'} status_age={int(age) if age is not None else '缺失'}s fresh={fresh}"


def fix_main_sched(dry, t, deb):
    pids = sched_pids("main")
    for p in pids:
        if dry:
            klog("main-sched", f"[dry-run] 将 kill 残进程 pid={p}")
        else:
            klog("main-sched", f"杀残进程 pid={p}（SIGTERM→5s→SIGKILL）")
            kill_pid(p, "main-sched")
    if not dry:
        reap_orphans("main-sched", MAIN_BIN)
    cmd = ["python3", "tools/factory-sched.py"]
    if dry:
        klog("main-sched", f"[dry-run] 将拉起: cwd={WS} cmd={' '.join(cmd)} "
                           f"env-=AF_SCHED_*/BIN（保持缺省=主产线） log=/tmp/factory.log setsid")
        return
    if spawn("main-sched", cmd, "/tmp/factory.log", extra_env={},
             strip_env=("AF_SCHED_GRAPH", "AF_SCHED_STATUS", "AF_SCHED_LOG", "BIN")):
        last_spawn["main-sched"] = t
        deb.record("main-sched", t)
        mes_event("main-sched", "keepalive_restart")


def check_exp_sched(t):
    pids = sched_pids("exp")
    age = file_age(EXP_ENV["AF_SCHED_STATUS"])
    fresh = age is not None and age < STALE_S
    if t - last_spawn.get("exp-sched", 0) < GRACE_S:
        return bool(pids), f"grace 宽限内：进程={pids or '无'}（豁免新鲜度）"
    ok = bool(pids) and fresh
    return ok, f"进程={pids or '无'} factory2_status_age={int(age) if age is not None else '缺失'}s fresh={fresh}"


def fix_exp_sched(dry, t, deb):
    pids = sched_pids("exp")
    for p in pids:
        if dry:
            klog("exp-sched", f"[dry-run] 将 kill 残进程 pid={p}")
        else:
            klog("exp-sched", f"杀残进程 pid={p}（SIGTERM→5s→SIGKILL）")
            kill_pid(p, "exp-sched")
    if not dry:
        reap_orphans("exp-sched", EXP_ENV["BIN"])
    if not os.path.exists(EXP_ENV["BIN"]):
        klog("exp-sched", f"ALARM 二进制缺失 {EXP_ENV['BIN']}，不拉起需人工")
        return
    cmd = ["python3", "tools/factory-sched.py"]
    if dry:
        klog("exp-sched", f"[dry-run] 将拉起: cwd={WS} cmd={' '.join(cmd)} "
                          f"env+={EXP_ENV} log=/tmp/factory2.log setsid")
        return
    if spawn("exp-sched", cmd, "/tmp/factory2.log", extra_env=dict(EXP_ENV)):
        last_spawn["exp-sched"] = t
        deb.record("exp-sched", t)
        mes_event("exp-sched", "keepalive_restart")


def watch_pids():
    return scan_pids(lambda argv: any(os.path.basename(a) == "factory-watch.py" for a in argv[1:]))


def dash_pids():
    return scan_pids(lambda argv: "http.server" in argv and DASH_PORT in argv)


def check_watch(t):
    pids = watch_pids()
    age = file_age(f"{WS}/状态观测/watch-state.json")
    fresh = age is not None and age < STALE_S
    if t - last_spawn.get("watch", 0) < GRACE_S:
        return bool(pids), f"grace 宽限内：进程={pids or '无'}（豁免新鲜度）"
    ok = bool(pids) and fresh
    return ok, f"进程={pids or '无'} watch-state_age={int(age) if age is not None else '缺失'}s fresh={fresh}"


def fix_watch(dry, t, deb):
    for p in watch_pids():
        if dry:
            klog("watch", f"[dry-run] 将 kill 残进程 pid={p}")
        else:
            klog("watch", f"杀残进程 pid={p}")
            kill_pid(p, "watch")
    cmd = ["python3", "tools/factory-watch.py"]
    if dry:
        klog("watch", f"[dry-run] 将拉起: cwd={WS} cmd={' '.join(cmd)} "
                      f"env+={WATCH_ENV} log=/tmp/factory-watch.log setsid")
        return
    if spawn("watch", cmd, "/tmp/factory-watch.log", extra_env=dict(WATCH_ENV)):
        last_spawn["watch"] = t
        deb.record("watch", t)
        mes_event("watch", "keepalive_restart")


def check_dash(t):
    pids = dash_pids()
    return bool(pids), f"看板8790进程={pids or '无'}"


def fix_dash(dry, t, deb):
    dcmd = ["python3", "-m", "http.server", DASH_PORT,
            "--bind", "127.0.0.1", "--directory", DASH_DIR]
    if dry:
        klog("dash", f"[dry-run] 将拉起看板: cmd={' '.join(dcmd)} "
                     f"log=/tmp/factory-dash.log setsid")
        return
    klog("dash", "看板 http.server 8790 不在（watchdog 的连带件），拉起（绑 127.0.0.1）")
    if spawn("dash", dcmd, "/tmp/factory-dash.log"):
        last_spawn["dash"] = t
        deb.record("dash", t)
        mes_event("dash", "keepalive_restart")


def cb_run_match(argv):
    return any(os.path.basename(a) == "cb-run.py" for a in argv[1:]) and \
        (len(argv) >= 3 and argv[-1] == "run")


def check_cb_run(t):
    pid = None
    try:
        with open("/tmp/cb-run.pid") as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        pid = None
    live = False
    if pid and os.path.exists(f"/proc/{pid}"):
        argv = pid_argv(pid) or []
        live = any("cb-run.py" in a for a in argv[1:])
    if not live:
        # pidfile 缺/陈旧时以进程扫描兜底（cb-run 模式=最后一个参数是 run）
        pids = scan_pids(cb_run_match)
        live = bool(pids)
    return live, f"pidfile_pid={pid} 进程在={live}"


def fix_cb_run(dry, t, deb):
    # 清陈旧 pidfile：pid 不在或不是 cb-run 进程才清（防其单实例守卫误拒）
    try:
        old = open("/tmp/cb-run.pid").read().strip()
    except OSError:
        old = None
    stale = True
    if old and old.isdigit() and os.path.exists(f"/proc/{old}"):
        argv = pid_argv(int(old)) or []
        stale = not any("cb-run.py" in a for a in argv[1:])
    if dry:
        klog("cb-run", f"[dry-run] pidfile old={old} stale={stale}"
                       f"{'，将清除陈旧 pidfile' if stale else '，保留'}")
        klog("cb-run", "[dry-run] 将拉起: cwd=WS cmd='python3 tools/cb-run.py run' "
                       "log=/tmp/cb-run.log setsid")
        return
    if stale and old:
        klog("cb-run", f"清陈旧 pidfile（pid={old} 非活 cb-run）")
        try:
            os.remove("/tmp/cb-run.pid")
        except OSError:
            pass
    # 若 pidfile 已丢但残进程在（罕见），精确清残（只匹配 run 模式，不碰 summary/quota 只读调用）
    for p in scan_pids(cb_run_match):
        klog("cb-run", f"杀残进程 pid={p}（pidfile 守卫外残影）")
        kill_pid(p, "cb-run")
    if spawn("cb-run", ["python3", "tools/cb-run.py", "run"], "/tmp/cb-run.log"):
        last_spawn["cb-run"] = t
        deb.record("cb-run", t)
        mes_event("cb-run", "keepalive_restart")


_img_scan_cache = {"ts": 0.0, "missing": None}


def missing_images():
    """与 local-image-feed 同口径数缺镜像；docker 不可读返回 None（判不准不动手）。
    结果缓存 300s（feed 死且已完成时无需每轮都 docker images）。"""
    if time.time() - _img_scan_cache["ts"] < 300:
        return _img_scan_cache["missing"]

    def img_name(inst):
        repo = inst.split("__")[0]
        return f"swebench/sweb.eval.x86_64.{repo.replace('/', '_1776_')}_1776_{inst.split('__')[1]}:latest"
    try:
        want = [img_name(x["instance_id"])
                for x in json.load(open(f"{WS}/计划/s1-swev-120.json", encoding="utf-8"))]
        out = subprocess.run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
                             capture_output=True, text=True, timeout=120,
                             stdin=subprocess.DEVNULL).stdout
        have = {l.strip() for l in out.splitlines() if l.strip()}
        miss = [i for i in want if i not in have]
    except Exception as e:
        klog("image-feed", f"缺镜像盘点失败（只报警不动手）: {e}")
        miss = None
    _img_scan_cache.update(ts=time.time(), missing=miss)
    return miss


def check_image_feed(t):
    pids = scan_pids(lambda argv: any(os.path.basename(a) == "local-image-feed.py" for a in argv[1:]))
    return bool(pids), f"进程={pids or '无'}"


def fix_image_feed(dry, t, deb):
    global last_feed_idle_log
    if dry:
        miss = missing_images()
        if miss is None:
            klog("image-feed", "[dry-run] 缺镜像数判不准（docker 异常）——将只报警不拉起")
        elif miss:
            klog("image-feed", f"[dry-run] 进程不在且缺镜像 {len(miss)} 张——将拉起: "
                               f"cwd=WS cmd='python3 tools/local-image-feed.py' "
                               f"log=/tmp/local-image-feed.log setsid")
        else:
            klog("image-feed", "[dry-run] 进程不在但 120 镜像全就位（正常完成退出）——将不重启只记一条")
        return
    miss = missing_images()
    if miss is None:
        klog("image-feed", "ALARM 进程不在且缺镜像数判不准（docker 异常），需人工")
        return
    if not miss:
        if time.time() - last_feed_idle_log > 3600:  # 一小时记一条，防刷屏
            klog("image-feed", "进程不在但 120 名单镜像全部就位——正常完成退出，不重启")
            last_feed_idle_log = time.time()
        return
    klog("image-feed", f"进程不在且缺镜像 {len(miss)} 张（如 {miss[0]}）→ 拉起")
    if spawn("image-feed", ["python3", "tools/local-image-feed.py"], "/tmp/local-image-feed.log"):
        last_spawn["image-feed"] = t
        deb.record("image-feed", t)
        mes_event("image-feed", "keepalive_restart")


def check_mcode_dispatch(t):
    pid = None
    try:
        with open("/tmp/mcode-dispatch/dispatch.pid") as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        pid = None
    live = False
    if pid and os.path.exists(f"/proc/{pid}"):
        argv = pid_argv(pid) or []
        live = any("mcode-dispatch" in a for a in argv[1:])
    if not live:
        pids = scan_pids(lambda argv: any(os.path.basename(a) == "mcode-dispatch.py"
                                          for a in argv[1:]) and "run" in argv)
        live = bool(pids)
    if not live:
        return False, f"pidfile_pid={pid} 进程在={live}"
    age = file_age("/tmp/mcode-dispatch/heartbeat")
    fresh = age is not None and age < 2400
    if t - last_spawn.get("mcode-dispatch", 0) < GRACE_S:
        return True, f"grace 宽限内：pid={pid}（豁免心跳新鲜度）"
    return fresh, f"pid={pid} heartbeat_age={int(age) if age is not None else '缺失'}s fresh={fresh}"


def mcode_dispatch_drained():
    """mcode-dispatch 完成态判断（T0-5 §8.2）：读 /tmp/mcode-dispatch/state.json，
    pending=[k for k,v in state.items() if v.get('phase') in (None,'solving','collected')]。
    判读口径（fail-closed 方向=不漏拉）：
      - state 读不到/非 JSON → 判不准 → 不走本分支（按现行判活/拉起）；
      - state 空表 → 全 pending → 走现行拉起（新队列方向正确）；
      - pending 非空 → 有未完成 → 走现行判活/拉起；
      - pending 空（全部终态：judged/quota/prepare_failed/error）→ 正常完成退出
        （含放弃与 quota 熔断），**不拉起**——这正是 2026-10-22 满判后 bounce 抖环的根因。
    返回 (drained: bool, detail: str)。"""
    try:
        with open(MCODE_STATE) as f:
            st = json.load(f)
    except (OSError, ValueError) as e:
        return False, f"state 读不到/非法（{type(e).__name__}）→ 判不准，走现行判活"
    if not isinstance(st, dict):
        return False, "state 结构非 dict → 判不准，走现行判活"
    if not st:
        return False, "state 空表 → 全 pending（新队列），走现行拉起"
    pending = [k for k, v in st.items()
               if isinstance(v, dict) and v.get("phase") in MCODE_PENDING_PHASES]
    if pending:
        return False, f"pending={len(pending)}（{pending[:3]}…）→ 有未完成，走现行判活/拉起"
    return True, f"state {len(st)} 键全终态（judged/quota/prepare_failed/error），无 pending"


# 完成态分支登记表（防抖超限态下仍放行完成态判定；非完成态不受影响）
# 2026-10-26 §三-2：mcode-dispatch 随旧链退役移出看护表，本表清空
# （mcode_dispatch_drained 函数保留为死码，随归档批清理）。
DRAIN_PROBES = {}


def fix_mcode_dispatch(dry, t, deb):
    global last_dispatch_drain_log
    # 组合补丁③：完成态分支先行——队列已排空则不拉起（止抖环）。
    drained, why = mcode_dispatch_drained()
    if drained:
        if dry:
            klog("mcode-dispatch", f"[dry-run] {why}——将不拉起（queue_drained：正常完成退出）")
            return
        if t - last_dispatch_drain_log > MCODE_DRAIN_LOG_S:
            klog("mcode-dispatch", f"queue_drained：{why}——正常完成退出，不拉起（止抖环）")
            mes_event("mcode-dispatch", "queue_drained")
            last_dispatch_drain_log = t
        return
    # 非完成态：走现行判活/拉起路径（拉起时记 deb，逻辑与改动前逐字一致）
    # 残进程精确清残（pidfile 失配时），防重启后双实例
    for p in scan_pids(lambda argv: any(os.path.basename(a) == "mcode-dispatch.py"
                                        for a in argv[1:]) and "run" in argv):
        try:
            with open("/tmp/mcode-dispatch/dispatch.pid") as f:
                if f.read().strip() == str(p):
                    continue  # pidfile 一致则交由 spawn 前单实例守卫处理
        except OSError:
            pass
        if dry:
            klog("mcode-dispatch", f"[dry-run] 将 kill 残进程 pid={p}")
        else:
            klog("mcode-dispatch", f"杀残进程 pid={p}")
            kill_pid(p, "mcode-dispatch")
    cmd = ["python3", "tools/mcode-dispatch.py", "run"]
    if dry:
        klog("mcode-dispatch", f"[dry-run] 将拉起: cwd={WS} cmd={' '.join(cmd)} "
                               f"log=/tmp/mcode-dispatch.log setsid")
        return
    if spawn("mcode-dispatch", cmd, "/tmp/mcode-dispatch.log"):
        last_spawn["mcode-dispatch"] = t
        deb.record("mcode-dispatch", t)
        mes_event("mcode-dispatch", "keepalive_restart")


# ---------- ch-mes-local（补丁④：查询级探针，2026-10-22；只报警不拉起） ----------
# 背景：mes500 根因报告（计划/研究组/mes500-根因报告.md §4 C 组缺口 1）——/ping 探不到
# 查询级 500（10-21 两次 500 期间探针全程绿灯）。判活从"进程在场"升级为"真查询"：
# 一条极轻 SELECT（occurred_at 是 ORDER BY 首列，分钟级谓词只扫尾部 granule，
# 毫秒级零重活）。失败分四类给不同告警码（alarms.log code + klog + 去重键）：
#   conn     连接拒绝（端口失/进程死/tailnet 断）
#   auth     HTTP 401/403（凭据缺失/错误——0600 cred 文件与 mingda .pw 不同步）
#   query    HTTP 5xx（CH 查询错误，含 mes500 的 MEMORY_LIMIT_EXCEEDED 形态）
#   timeout  超时无响应（挂起/深内存压力/网络黑洞）
# 告警主通道仍是文件（klog/alarms.log）：CH 挂时照样可报，不落「用 MES 报 MES 挂」
# 悖论；MES kind=ch_mes_down 不变（schema 零改动），类别只在告警文件与 klog 区分。
CHMES_PROBE_SQL = ("SELECT count() FROM af_mes.mes_event "
                   "WHERE occurred_at > now() - INTERVAL 1 MINUTE")
CHMES_PROBE_TIMEOUT = 3      # 秒：正常毫秒级返回；3s 足以区分"慢"与"挂"
CHMES_ALARM_CODES = {"conn": "ch-mes-conn-refused", "auth": "ch-mes-auth",
                     "query": "ch-mes-query", "timeout": "ch-mes-timeout"}
CHMES_RECOVERY = {
    "conn": "恢复=mingda systemd 单元 clickhouse-factory.service（enabled+Restart=always，"
            "2026-10-22 14:28 起在役）应自动拉起；持续失联→人工 ssh mingda-bench "
            "systemctl start clickhouse-factory.service 或跑 /root/ch-mes-factory/start.sh，"
            "并查 tailnet/端口",
    "auth": "恢复=核对 0600 凭据文件 ~/.config/mes-ch/url 与 mingda .pw 是否同步",
    "query": "恢复=查 mingda system.errors（mes500 形态=服务端限额塌陷/查询错误），人工介入",
    "timeout": "恢复=查 mingda 负载与 tailnet 连通性；持续超时按 conn 处置",
}


def ch_mes_probe(timeout=CHMES_PROBE_TIMEOUT, url=None, auth=None, sql=None):
    """查询级探活：GET {url}/?query=<极轻 SELECT>，期待纯数字计数。

    返回 (ok, fail_class, detail)：fail_class ∈ None/'conn'/'auth'/'query'/'timeout'。
    连接参数缺省走 CH/CH_AUTH（=0600 cred 文件/env 解析值，口令不落明文）；入参可
    覆盖——四类失败演练用（错端口/错凭据/错 SQL/黑洞超时）。分类（urllib 异常族）：
      HTTPError 401/403 → auth；其他 HTTP 错误（CH 查询错=500）→ query
      socket.timeout/TimeoutError（含 URLError.reason 包装）→ timeout
      ConnectionRefusedError（含 URLError.reason）→ conn；其他 URLError → conn
    2xx 但响应体非纯数字 → query（服务端回了但不是计数=查询语义异常）。
    """
    url = CH if url is None else url
    auth = CH_AUTH if auth is None else auth
    sql = CHMES_PROBE_SQL if sql is None else sql
    target = f"{url}/?query={urllib.parse.quote(sql)}"
    try:
        req = urllib.request.Request(target)
        if auth:
            req.add_header("Authorization", auth)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace").strip()
            if re.fullmatch(r"\d+", body):
                return True, None, f"查询 Ok（近1分钟事件 count={body}）"
            return False, "query", f"HTTP {r.status} 响应体非计数: {body[:60]!r}"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False, "auth", f"HTTP {e.code}（凭据缺失/错误）"
        return False, "query", f"HTTP {e.code}（CH 查询错误；mes500 同形态）"
    except (socket.timeout, TimeoutError):
        return False, "timeout", f"{timeout}s 超时无响应"
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return False, "timeout", f"{timeout}s 超时（{reason}）"
        if isinstance(reason, ConnectionRefusedError):
            return False, "conn", f"连接拒绝: {reason}"
        return False, "conn", f"连接失败: {reason}"
    except ConnectionRefusedError as e:
        return False, "conn", f"连接拒绝: {e}"
    except Exception as e:            # 未分类连接异常，保守归 conn（方向安全）
        return False, "conn", f"未分类异常: {e!r}"


def check_mes_ch(t):
    """mes-ch（mingda MES 查询级探针，2026-10-26 §三-2 由 ch-mes-local 更名，探针不变）。"""
    global last_chmes_fail
    ok, cls, detail = ch_mes_probe()
    last_chmes_fail = None if ok else (cls, detail)
    return ok, detail


def fix_mes_ch(dry, t, deb):
    """失联处置=只报警不拉起（跨机自动拉起越权，不做；恢复手段见 CHMES_RECOVERY）。
    2026-10-26 §三-2：由 fix_ch_mes_local 更名 mes-ch（探针/告警码/kind 全不变）。
    告警码按失败类别四选一（补丁④）；30min 去重，类别翻转立即重报（同窗内 conn 翻
    query 是质变，不该被去重吞掉）。"""
    global last_chmes_alarm, last_chmes_alarm_cls
    cls, detail = last_chmes_fail or ("conn", "（无分类信息）")
    code = CHMES_ALARM_CODES.get(cls, CHMES_ALARM_CODES["conn"])
    rec = CHMES_RECOVERY.get(cls, CHMES_RECOVERY["conn"])
    if dry:
        klog("mes-ch", f"[dry-run] 查询探针失联（类别={cls} 码={code}：{detail}）"
                       f"——将报警（klog + {ALARMS_LOG} + MES kind=ch_mes_down，"
                       f"{CHMES_DEDUP_S}s 去重），不拉起；{rec}")
        return
    if t - last_chmes_alarm < CHMES_DEDUP_S and cls == last_chmes_alarm_cls:
        return
    last_chmes_alarm, last_chmes_alarm_cls = t, cls
    klog("mes-ch", f"ALARM MES({CH}) 查询探针失联（类别={cls} 码={code}）：{detail}"
                   f"——不自动重启；{rec}；af 线 MES 落账将失败，"
                   f"需人工介入（{CHMES_DEDUP_S}s 内同类别不重复报）")
    try:
        with open(ALARMS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": now_s(), "level": "red", "code": code,
                "message": f"MES({CH}) 查询探针失联（类别={cls}）：{detail}；{rec}",
                "since": time.strftime("%F %T", time.localtime(t)),
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass
    mes_event("mes-ch", "ch_mes_down")


# ---------- anolis-proxy-8124（D-43 归还组，2026-10-24：anolis 8124 净化白名单代理）----------
# 背景：d36p-proxy（anolis 127.0.0.1:8124，只放行 CONNECT agent.minimaxi.com:443，
# mcode-swev purified/containerized 跑批线共用出口）曾静默死 13h 引发连锁误诊。
# 判活=ssh 端口探活：明文 GET，本体对非 CONNECT 一律回 403——拿到任意 3 位 HTTP 码
# 即=端口活；000/空=死。远端命令以 "; true" 收尾屏蔽 curl 退出码，ssh rc 只反映
# 传输层（rc!=0/超时=tailnet 或 anolis 失联=判不准，只报警不拉起——拉起也走 ssh
# 必失败；30min 去重落 klog+alarms.log，文件主通道同 ch-mes-local 取向）。
# 恢复=ssh 调 anolis:~/mcode-swev/start-proxy-8124.sh（跑批组拉起方式固化：
# setsid+nohup+日志追加 d36p-proxy-8124.log；本体自持 flock 单实例守卫
# ~/mcode-swev/d36p-proxy.lock，脚本另有端口幂等防双开，可重入）。
# 防抖/告警照抄既有对象：2 次/600s 窗，超限 keepalive_suppressed；成功拉起记
# last_spawn（GRACE_S 宽限防启动期抖环）+MES keepalive_restart。
PROXY8124_NAME = "anolis-proxy-8124"
PROXY8124_SSH = ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", "anolis"]
PROXY8124_PROBE_CMD = ("curl -sx '' -o /dev/null --max-time 5 -w '%{http_code}' "
                       "http://127.0.0.1:8124/ 2>/dev/null; true")
PROXY8124_START_CMD = "bash ~/mcode-swev/start-proxy-8124.sh"
PROXY8124_REMOTE_LOG = "anolis:~/mcode-swev/d36p-proxy-8124.log"
PROXY8124_SSH_ALARM_DEDUP_S = 1800
last_proxy8124_ssh_alarm = 0.0   # ssh 失联报警去重（本进程自有状态键，同 ch-mes 取向）
last_proxy8124_fail = None       # check→fix 传递 (unreachable: bool, detail)


def proxy8124_probe():
    """ssh 端口探活 → (reachable, alive, detail)。reachable=False=失联判不准。"""
    try:
        r = subprocess.run(PROXY8124_SSH + [PROXY8124_PROBE_CMD],
                           capture_output=True, text=True, timeout=15,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return False, None, "ssh 探活 15s 超时（tailnet/anolis 失联？判不准）"
    if r.returncode != 0:
        return False, None, (f"ssh 失联 rc={r.returncode} "
                             f"{(r.stderr or '').strip()[:60]}（判不准）")
    code = (r.stdout or "").strip()
    if re.fullmatch(r"[1-5]\d\d", code):
        return True, True, f"端口活（明文探测 HTTP {code}，本体拒非 CONNECT=预期）"
    return True, False, f"端口死（curl code={code or '空'}）"


def check_anolis_proxy8124(t):
    global last_proxy8124_fail
    reach, alive, detail = proxy8124_probe()
    last_proxy8124_fail = None if (reach and alive) else (not reach, detail)
    if reach and alive:
        return True, detail
    if t - last_spawn.get(PROXY8124_NAME, 0) < GRACE_S:
        return True, (f"grace 宽限内（拉起后 "
                      f"{int(t - last_spawn.get(PROXY8124_NAME, 0))}s，豁免等启动）"
                      f"probe={detail}")
    return False, detail


def fix_anolis_proxy8124(dry, t, deb):
    global last_proxy8124_ssh_alarm, last_proxy8124_fail
    unreachable, detail = last_proxy8124_fail or (False, "（无分类信息）")
    if unreachable:   # ssh 失联=判不准：只报警不拉起，30min 去重
        if dry:
            klog(PROXY8124_NAME, f"[dry-run] {detail}——将报警不拉起"
                                 f"（{PROXY8124_SSH_ALARM_DEDUP_S}s 去重）")
            return
        if t - last_proxy8124_ssh_alarm > PROXY8124_SSH_ALARM_DEDUP_S:
            last_proxy8124_ssh_alarm = t
            klog(PROXY8124_NAME, f"ALARM ssh 失联判不准（{detail}）——不自动拉起"
                                 f"（拉起也走 ssh 必失败），需人工查 tailnet/anolis"
                                 f"（{PROXY8124_SSH_ALARM_DEDUP_S}s 内不重复报）")
            try:
                with open(ALARMS_LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "ts": now_s(), "level": "red", "code": "anolis-proxy-8124-ssh",
                        "message": f"anolis 8124 代理判活 ssh 失联：{detail}；"
                                   f"不自动拉起（拉起也走 ssh），需人工",
                        "since": time.strftime("%F %T", time.localtime(t)),
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
        return
    if dry:
        klog(PROXY8124_NAME, f"[dry-run] 端口死（{detail}）——将 ssh 调 "
                             f"{PROXY8124_START_CMD} 拉起（log={PROXY8124_REMOTE_LOG}）")
        return
    klog(PROXY8124_NAME, f"端口死 → ssh 拉起（{detail}）")
    try:
        r = subprocess.run(PROXY8124_SSH + [PROXY8124_START_CMD],
                           capture_output=True, text=True, timeout=60,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        deb.record(PROXY8124_NAME, t)
        klog(PROXY8124_NAME, "ALARM ssh 拉起 60s 超时（防抖已计次，需人工查 anolis）")
        return
    out = (r.stdout or "").strip().splitlines()
    err = (r.stderr or "").strip()
    klog(PROXY8124_NAME, f"拉起脚本 rc={r.returncode} {out[-1] if out else '(无输出)'}"
                         f"{(' ' + err[:60]) if err else ''}")
    deb.record(PROXY8124_NAME, t)   # 失败也计次（失败上限照抄既有对象）
    if r.returncode == 0:
        last_spawn[PROXY8124_NAME] = t
        mes_event(PROXY8124_NAME, "keepalive_restart")
    last_proxy8124_fail = None


# ---------- af-execline（2026-10-26 §三-2 退役改造新增：af 统一执行面判活） ----------
# 背景：旧 bench 链退役（ADR-008，runbook §三-2）。af 执行面=订单驱动（af-order submit
# → af-execline 执行 → af-mes 记账），非守护进程——判活取双通道：①/proc 扫描 argv
# basename∈{af-order,af-execline}（释放件与 cargo run 形态同 basename）；②WS/af-state/
# orders/ 最新订单目录 mtime（订单生命周期内落件即心跳）。心跳窗 72h=订单节奏日级+
# 观察期跨天判据 3 天（施工参数，登记 退役执行记录-20261026.md，可调）。
# 失联处置=只报警不拉起（amber 级：订单驱动面空闲≠故障；30min 去重）——klog+
# alarms.log（code=af-execline-idle）+ MES kind=af_plane_idle（写失败不致命）。
AF_EXEC_NAME = "af-execline"
AF_STATE_ORDERS = f"{WS}/af-state/orders"
AF_LEDGER_FRESH_S = 72 * 3600
AF_IDLE_ALARM_DEDUP_S = 1800
last_af_idle_alarm = 0.0


def af_plane_pids():
    """af-order/af-execline 进程扫描（不限 python——释放件是原生二进制）。"""
    out = []
    for ent in os.listdir("/proc"):
        if not ent.isdigit():
            continue
        argv = pid_argv(int(ent))
        if not argv:
            continue
        if os.path.basename(argv[0]) in ("af-order", "af-execline") or \
                any(os.path.basename(a) in ("af-order", "af-execline") for a in argv[1:]):
            out.append(int(ent))
    return sorted(out)


def latest_order_ledger_age():
    """af-state/orders/ 最新订单目录 mtime 距今秒数；目录缺失返回 None。"""
    newest = 0.0
    try:
        for od in os.listdir(AF_STATE_ORDERS):
            try:
                newest = max(newest, os.stat(os.path.join(AF_STATE_ORDERS, od)).st_mtime)
            except OSError:
                continue
    except OSError:
        return None
    return (time.time() - newest) if newest else None


def check_af_execline(t):
    pids = af_plane_pids()
    if pids:
        return True, f"进程={pids}（订单在飞）"
    age = latest_order_ledger_age()
    fresh = age is not None and age < AF_LEDGER_FRESH_S
    if age is None:
        return False, "订单 ledger 目录缺失（af-state/orders/ 不存在）"
    return fresh, f"无进程；订单 ledger 心跳 {int(age)}s 前（窗 {AF_LEDGER_FRESH_S}s）"


def fix_af_execline(dry, t, deb):
    """订单驱动面空闲：只报警不拉起（amber，30min 去重）。恢复=经 af-order 正常下单。"""
    global last_af_idle_alarm
    if dry:
        klog(AF_EXEC_NAME, "[dry-run] af 执行面无进程且订单 ledger 心跳超窗——将报警"
                           f"（amber，{AF_IDLE_ALARM_DEDUP_S}s 去重），不拉起（订单驱动型非守护）")
        return
    if t - last_af_idle_alarm < AF_IDLE_ALARM_DEDUP_S:
        return
    last_af_idle_alarm = t
    klog(AF_EXEC_NAME, "ALARM af 执行面空闲（无 af-order/af-execline 进程且订单 ledger 心跳>"
                       f"{AF_LEDGER_FRESH_S // 3600}h）——不自动拉起（订单驱动型，空闲≠故障）；"
                       "恢复=经 af-order 正常下单（下单即恢复心跳）")
    try:
        with open(ALARMS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": now_s(), "level": "amber", "code": "af-execline-idle",
                "message": "af 执行面空闲：无 af-order/af-execline 进程且订单 ledger 心跳超 "
                           f"{AF_LEDGER_FRESH_S // 3600}h；订单驱动型不自动拉起，恢复=经 af-order 正常下单",
                "since": time.strftime("%F %T", time.localtime(t)),
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass
    mes_event(AF_EXEC_NAME, "af_plane_idle")


# ---------- gc-watch（补丁③ R2：anolis 镜像池 GC 看护，本地判断+spawn 即返回） ----------

def read_gc_evidence():
    """耐久证据末态。容忍缺文件/坏行（无 GC 历史=全 0，方向安全：只多评估一轮）。"""
    last_apply_epoch, last_apply_ok, last_apply_note = 0.0, None, ""
    last_success_epoch, last_alarm_epoch = 0.0, 0.0
    try:
        with open(GC_EVIDENCE, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                ep = r.get("epoch") or 0
                if r.get("kind") == "apply":
                    if ep >= last_apply_epoch:
                        last_apply_epoch, last_apply_ok = ep, bool(r.get("ok"))
                        last_apply_note = (f"删 {r.get('deleted', 0)} 张/rmi-fail "
                                           f"{r.get('rmi_fail', 0)}，/data "
                                           f"{r.get('use_pct')}%→{r.get('use_pct_after')}%"
                                           f"，reason={r.get('reason')}" if not r.get("ok")
                                           else f"删 {r.get('deleted', 0)} 张/rmi-fail "
                                                f"{r.get('rmi_fail', 0)}，/data "
                                                f"{r.get('use_pct')}%→{r.get('use_pct_after')}%")
                    if r.get("ok"):
                        last_success_epoch = max(last_success_epoch, ep)
                elif r.get("kind") == "gc-alarm-sent":
                    last_alarm_epoch = max(last_alarm_epoch, ep)
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return {"last_apply_epoch": last_apply_epoch, "last_apply_ok": last_apply_ok,
            "last_apply_note": last_apply_note, "last_success_epoch": last_success_epoch,
            "last_alarm_epoch": last_alarm_epoch}


def append_gc_evidence(rec):
    """证据双写（tmp 现场 + 耐久）。失败不致命（只影响下轮去重/迟滞精度，方向安全）。"""
    for path in (GC_EVIDENCE_TMP, GC_EVIDENCE):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass


def gc_watch(dry=False):
    """anolis 镜像池 GC 看护（补丁③ R2）。严格非阻塞：本函数只读本地文件做判断，
    需要跑则 spawn tools/img-gc.py apply --host anolis 即返回——flock/ssh/prune 全在
    子进程，绝不阻塞 30s 一轮的主循环（否则 7 个看护对象集体失明）。"""
    global last_gc_spawn
    t = time.time()
    ev = read_gc_evidence()
    # A9：有未告警的 GC 结果 → alarms.log（去重时间戳记回耐久件，30min 窗）
    if ev["last_apply_epoch"] > ev["last_alarm_epoch"] and \
            t - ev["last_alarm_epoch"] > GC_ALARM_DEDUP_S:
        lvl = "amber" if ev["last_apply_ok"] else "red"
        if dry:
            klog("gc-watch", f"[dry-run] 将报警（level={lvl}）：{ev['last_apply_note']}")
        else:
            try:
                with open(ALARMS_LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "ts": now_s(), "level": lvl, "code": "gc-watch",
                        "message": f"anolis /data 镜像GC结果：{ev['last_apply_note']}",
                        "since": time.strftime("%F %T", time.localtime(ev["last_apply_epoch"])),
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            append_gc_evidence({"kind": "gc-alarm-sent", "ts": now_s(),
                                "epoch": int(t), "level": lvl})
            klog("gc-watch", f"GC 结果已入 alarms.log（level={lvl}）：{ev['last_apply_note']}")
    # 触发判断（全部本地读；判不准一律不动）
    if t - last_gc_spawn < GC_SPAWN_SUPPRESS:
        return
    # P0-2 drill 旗标（方案 §3.3-a）：只读演练通道——旗标存在则跳过水位/迟滞判断，
    # spawn 一次 argv=plan（只读不删）的子进程后自毁旗标。1200s 防抖仍适用。
    if os.path.exists(GC_DRILL_FLAG):
        if dry:
            klog("gc-watch", "[dry-run] drill 旗标存在——将 spawn "
                         "tools/img-gc.py plan --host anolis（只读不删；不删旗标）")
            return
        last_gc_spawn = t
        argv = ["python3", "tools/img-gc.py", "plan", "--host", "anolis"]
        klog("gc-watch", f"[drill] 旗标命中 → spawn tools/img-gc.py plan --host anolis"
                         f"（argv={' '.join(argv)}，只读不删；spawn 后旗标自毁）")
        spawn("gc-watch", argv, "/tmp/img-gc.log")
        try:
            os.remove(GC_DRILL_FLAG)
        except OSError:
            pass
        return
    try:
        with open(LATEST_JSON, encoding="utf-8") as f:
            an = (json.load(f).get("anolis") or {})
        pct = (an.get("disk") or {}).get("/data", {}).get("use_pct")
    except Exception:
        return
    age = file_age(LATEST_JSON)
    if pct is None or age is None or age > STALE_S:
        return  # watch 断供/字段缺失：宁可不 GC（fail-safe，不阻塞）
    if pct < GC_TRIGGER_PCT:
        return
    if t - ev["last_success_epoch"] < GC_MIN_INTERVAL:
        return
    if dry:
        klog("gc-watch", f"[dry-run] 将 spawn tools/img-gc.py apply --host anolis"
                         f"（/data {pct}%≥{GC_TRIGGER_PCT}%，距上次成功GC "
                         f"{(t - ev['last_success_epoch']) / 3600:.1f}h）")
        return
    last_gc_spawn = t
    klog("gc-watch", f"触发（/data {pct}%≥{GC_TRIGGER_PCT}%，距上次成功GC "
                     f"{(t - ev['last_success_epoch']) / 3600:.1f}h）→ spawn apply 子进程"
                     f"（非阻塞；≥88% 子进程内自停手只回报）")
    # J3 修复（补丁③R2-fix1）：子命令必须在前——--host 归 apply 子解析器，
    # 旧序「--host anolis apply」100% 死于 argparse rc2 且死前零证据、A9 无从告警。
    spawn("gc-watch", ["python3", "tools/img-gc.py", "apply", "--host", "anolis"],
          "/tmp/img-gc.log")


LAUNCH_PLAN = [
    ("watch", ["python3", "tools/factory-watch.py"], "/tmp/factory-watch.log",
     f"env+={WATCH_ENV}；判据=进程+watch-state.json<300s"),
    ("dash", ["python3", "-m", "http.server", DASH_PORT,
              "--bind", "127.0.0.1", "--directory", DASH_DIR], "/tmp/factory-dash.log",
     "看板：判据=8790 进程在；死则拉起（绑 127.0.0.1）"),
    ("af-execline", ["stat", "-c", "%y", f"{WS}/af-state/orders"], "（不拉起，报警面）",
     "af 统一执行面判活（2026-10-26 §三-2 新增，订单驱动非守护）：判活=af-order/af-execline "
     "进程在场 或 af-state/orders/ 最新订单目录 mtime<72h（cmd 列=心跳等价查看命令）；"
     "空闲=amber 报警不拉起（klog+alarms.log code=af-execline-idle+MES kind=af_plane_idle，"
     "30min 去重）；恢复=经 af-order 正常下单"),
    ("mes-ch", ["curl", "-s", "-m", "5", "-u", "default:<0600凭据文件>",
                "http://100.64.0.2:15221/?query=SELECT%20count()%20FROM%20af_mes.mes_event%20WHERE%20occurred_at%20%3E%20now()%20-%20INTERVAL%201%20MINUTE"],
     str(ALARMS_LOG),
     "mingda MES 查询级连通探活（2026-10-26 §三-2 由 ch-mes-local 更名，探针原样）："
     "判活=极轻 SELECT（/ping 探不到查询级 500=mes500 缺口）；失联=30min 去重报警"
     "（klog+alarms.log 类别码 ch-mes-conn-refused/auth/query/timeout+MES kind=ch_mes_down）；"
     "恢复=mingda systemd 单元 clickhouse-factory.service（Restart=always）自动拉起，持续失联"
     "人工 ssh mingda-bench systemctl start；实现走 urllib（cmd 列的是等价判据命令，"
     "凭据从 0600 文件解析）"),
]


def print_commands():
    print("factory-keepalive 拉起命令台账（均 cwd=WS、stdin=DEVNULL、setsid 脱离、stdout/stderr 追加）：")
    for name, cmd, logf, note in LAUNCH_PLAN:
        print(f"\n[{name}]\n  cmd : {' '.join(cmd)}\n  log : {logf}\n  姿势: {note}")


# 2026-10-26 §三-2 退役改造：旧 9 对象收敛为观察期 4 对象（runbook §三-2）。
# 旧对象的 check/fix 函数保留为无引用死码（见文件头），不在本表=不判活不拉起。
TARGETS = ["watch", "dash", "af-execline", "mes-ch"]


def one_round(dry=False):
    t = time.time()
    deb = one_round.deb
    states = {}
    graph_guard(dry)   # D-25：先保图（存在性校验+自动恢复），再判各对象活
    for name in TARGETS:
        alive, detail = CHECKS[name](t)
        states[name] = (alive, detail)
        if alive:
            continue
        if not dry and not deb.allow(name, t):
            # 防抖超限态：完成态分支仍放行（组合补丁③：queue_drained 不计入防抖，
            # §8.2 验收②③）——让 fix 自己判完成态并直接返回（不拉起、不记 deb）；
            # 非完成态（有 pending）仍受防抖压制不变。
            if name in DRAIN_PROBES:
                drained, _dwhy = DRAIN_PROBES[name]()
                if drained:
                    FIXES[name](dry, t, deb)
            continue  # 防抖超限已报警
        if name not in ("af-execline", "mes-ch"):
            # af-execline/mes-ch 的 fix 自带分支日志（空闲报警/去重报警/恢复指引），
            # 通用「失联 → 处置」行会每轮刷屏，豁免
            klog(name, f"失联 → 处置（{detail}）")
        FIXES[name](dry, t, deb)
    gc_watch(dry)   # 补丁③：anolis 镜像池 GC 看护（纯本地判断+spawn 即返回，非阻塞）
    if dry:
        print(f"--- dry-run 判活结论 {now_s()} ---")
        for name in TARGETS:
            alive, detail = states[name]
            print(f"  {name:<11} {'存活' if alive else '失联'}  {detail}")
    return states


# 让 one_round 携带防抖状态（免全局乱飘）
one_round.deb = Debounce()

CHECKS = {
    "watch": check_watch,
    "dash": check_dash,
    "af-execline": check_af_execline,
    "mes-ch": check_mes_ch,
}
FIXES = {
    "watch": fix_watch,
    "dash": fix_dash,
    "af-execline": fix_af_execline,
    "mes-ch": fix_mes_ch,
}


def self_guard():
    """单实例守卫：pidfile 指向活着的 factory-keepalive 进程即拒绝。"""
    try:
        old = open(PIDFILE).read().strip()
        if old and old.isdigit() and os.path.exists(f"/proc/{old}"):
            argv = pid_argv(int(old)) or []
            if any("factory-keepalive.py" in a for a in argv[1:]):
                print(f"factory-keepalive 已在跑 pid={old}，拒绝双实例", file=sys.stderr)
                sys.exit(3)
        klog("self", f"清陈旧自身 pidfile（pid={old} 失活）")
    except FileNotFoundError:
        pass
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))


def main():
    global INTERVAL
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="单轮干跑，只打印将执行的命令")
    ap.add_argument("--print-commands", action="store_true",
                    help="打印全部对象拉起命令/env/日志路径后退出（不判活不动手）")
    ap.add_argument("--interval", type=int, default=INTERVAL)
    a = ap.parse_args()
    if a.print_commands:
        print_commands()
        return
    INTERVAL = max(5, a.interval)
    if a.dry_run:
        one_round(dry=True)
        return
    self_guard()
    klog("self", f"keepalive 常驻启动 pid={os.getpid()} 周期 {INTERVAL}s "
                 f"看护 {len(TARGETS)} 对象：{', '.join(TARGETS)}")
    stop = {"flag": False}

    def on_term(_sig, _frm):
        stop["flag"] = True
    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)
    rnd = 0
    try:
        while not stop["flag"]:
            rnd += 1
            try:
                states = one_round()
                if rnd - last_hb_round >= HEARTBEAT_EVERY:
                    globals()["last_hb_round"] = rnd
                    backup_graphs()   # D-25：心跳前先做新鲜滚动备份
                    parts = []
                    for name, (ok, detail) in states.items():
                        if ok:
                            parts.append(f"{name}:ok")
                        elif name == "image-feed":
                            parts.append("image-feed:done(正常完成退出,不重启)")
                        elif name in DRAIN_PROBES and DRAIN_PROBES[name]()[0]:
                            # 完成态（队列已排空）：不是 DOWN，如实报 done（防误读为失联）
                            parts.append(f"{name}:done(queue_drained,正常完成退出,不拉起)")
                        else:
                            parts.append(f"{name}:DOWN({detail})")
                    klog("self", f"心跳：第 {rnd} 轮 " + "  ".join(parts))
            except Exception as e:
                klog("self", f"轮异常（不退出）: {e}")
            for _ in range(INTERVAL):
                if stop["flag"]:
                    break
                time.sleep(1)
    finally:
        try:
            if open(PIDFILE).read().strip() == str(os.getpid()):
                os.remove(PIDFILE)
        except OSError:
            pass
        klog("self", "keepalive 退出")


if __name__ == "__main__":
    main()
