#!/usr/bin/env python3
"""patch5-test-a4l-watch-verify.py — 补丁测试员独立验证套件（补丁 patch-tmpfs-alarm-watch-A4L-R2）。

三属性（安灯语义映射）：
  A 越线拦住=越线亮灯：/tmp < 2662MiB 或 statvfs 盘点失败 → amber A4L:tmp，文案与任务书
    逐字一致、盘点失败/写满两文案同码强制区分；经 build_alarms→log_alarms 既有 30min
    去重链落流水（daemon）/快照（once），与 A4 同权。
  B 正常放行=正常不亮灯：/tmp ≥2662MiB（含边界 =2662 严格小于）零 A4L 报警。
  C 在飞不受影响：不跑真实 --once/常驻（会写生产 latest.json/data.json/watch-state.json
    并与在飞 pid 抢 state）；全扫描桩 + 四件套（LATEST/DASH_DATA/STATE_FILE/ALARMS_LOG）
    重定向沙箱；after 对比在飞 pid 3692358 同 pid 同启动时间、产线 alarms.log/latest.json
    零 A4L（旧码在飞证明）、现役文件 md5 不变。

输出落 /tmp/wtst-verify.out。跑法：python3 补丁/patch5-test-a4l-watch-verify.py >/dev/null 2>&1
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from unittest import mock

WS = "/home/pan-ding/workspace/agent黑灯工厂"
TARGET = f"{WS}/tools/factory-watch.py"
AUTHOR = f"{WS}/补丁/patch5-test-a4l-watch.py"
OUT_PATH = "/tmp/wtst-verify.out"
T = 1792610000.0
WARN_MSG = ("本机 /tmp 可用 {x} MiB<2662MiB（usrquota 校准线，闸线 2252MiB，"
            "低于则 sched/mcode 拦新臂/新判分）")
FAIL_MSG = "/tmp 盘点失败（fail-closed）"
LINES, PASS, FAIL = [], [], []


def say(s=""):
    LINES.append(str(s))


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    say(f"{'PASS' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not cond else ""))


def sh(cmd, timeout=60):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def a4l_of(alarms):
    return [a for a in alarms if a["code"] == "A4L:tmp"]


def stubs(anolis=None):
    return dict(
        arms=[], plan=[],
        sched={"status_file_exists": True, "mtime_stale": False,
               "proc_confirmed_down": False, "alive": False, "running_arms": []},
        anolis=anolis if anolis is not None else {},
        relay={"consecutive_failures": 0, "last_event": "-"},
        state={"alarm_open": {}, "alarm_logged": {}, "sweb_img_hist": []},
        extras=None, archived=None,
    )


# ================= PART 0 before =================
say("=" * 72)
say("PART 0 before：在飞 watch 快照 / 状态观测面 / 现场水位")
say("=" * 72)
rc, o, _ = sh("ps -o pid,lstart,etimes --no-headers -p 3692358")
say(f"在飞 watch: {o.strip()}")
rc, o, _ = sh("md5sum 状态观测/latest.json 状态观测/watch-state.json")
say(f"状态观测 md5(before): {o.strip()}")
rc, n_alm, _ = sh("wc -l < 状态观测/alarms.log")
rc, n_a4l, _ = sh("grep -c A4L 状态观测/alarms.log 状态观测/latest.json ; true")
say(f"alarms.log 行数(before)={n_alm.strip()} A4L 命中={n_a4l.strip().replace(chr(10), ' / ')}")
rc, o, _ = sh("python3 -c \"import os; st=os.statvfs('/tmp'); print(st.f_bavail*st.f_frsize//1048576)\"")
cur_mb = int(o.strip())
say(f"/tmp 现水位: {cur_mb}MiB（≥2662 → 新码现场也应零 A4L）")

# ================= PART 1 作者套件 =================
say("")
say("=" * 72)
say("PART 1 作者套件 补丁/patch5-test-a4l-watch.py")
say("=" * 72)
r = subprocess.run([sys.executable, AUTHOR], capture_output=True, text=True,
                   timeout=120, cwd=WS)
say(f"rc={r.returncode}")
say(r.stdout.strip()[-1500:])
if r.stderr.strip():
    say(f"[stderr尾] {r.stderr.strip()[-300:]}")
n_pass = sum(1 for l in r.stdout.splitlines() if l.startswith("PASS "))
check("PART1 作者套件全过（rc=0 且零 FAIL 且 ALL PASS）",
      r.returncode == 0 and "FAIL " not in r.stdout and "ALL PASS" in r.stdout,
      f"rc={r.returncode} pass_lines={n_pass}")

# ================= PART 2 常量/探针/阈值 =================
say("")
say("=" * 72)
say("PART 2 常量校准链 / probe_local_tmp_mb / 阈值边界")
say("=" * 72)
spec = importlib.util.spec_from_file_location("fw_verify", TARGET)
md = importlib.util.module_from_spec(spec)
spec.loader.exec_module(md)
SB = tempfile.mkdtemp(prefix="wtst-verify-")
md.ALARMS_LOG = f"{SB}/alarms.log"
md.LATEST = f"{SB}/latest.json"
md.DASH_DATA = f"{SB}/data.json"
md.STATE_FILE = f"{SB}/watch-state.json"

check("W1a 常量 A4L_TMP_WARN_MB=2662 / A4L_TMP_GATE_MB=2252",
      md.A4L_TMP_WARN_MB == 2662 and md.A4L_TMP_GATE_MB == 2252,
      f"{md.A4L_TMP_WARN_MB}/{md.A4L_TMP_GATE_MB}")
src = open(TARGET, encoding="utf-8").read()
check("W1b 常量注释含校准链（mes500-根因报告.md:42 / WARN 2662≈sched / 闸线 2252≈sched+mcode CLOSE）",
      "mes500-根因报告.md:42" in src and "2662MiB≈2.6GiB" in src
      and "2252MiB≈2.2GiB" in src and "probe_tmpfs" in src)
check("W1c 模块头部安灯规则 docstring 增 A4L 条目（含盘点失败另文案说明）",
      "amber A4L 本机 /tmp 可用 <2662MiB" in src and "/tmp 盘点失败（fail-closed）" in src[:2000])

st_mb = os.statvfs("/tmp")
expect_mb = st_mb.f_bavail * st_mb.f_frsize // 1048576
mb, fail = md.probe_local_tmp_mb()
check("W2 真实 probe=(MiB, False) 且与 statvfs 同公式同读数", fail is False and mb == expect_mb,
      f"probe={mb} expect={expect_mb}")

with mock.patch.object(md.os, "statvfs", side_effect=OSError(28, "mock")):
    mb2, fail2 = md.probe_local_tmp_mb()
check("W3 statvfs 异常 → (-1, True) 盘点失败=fail-closed", mb2 == -1 and fail2 is True,
      f"{mb2}/{fail2}")

# 阈值矩阵（含现场真实读数=正常放行）
cases = [
    (expect_mb, "现场真实读数"),
    (2662, "=2662 边界"),
    (2661, "2661 边界下"),
    (1000, "1000 深水区"),
]
for val, label in cases:
    with mock.patch.object(md, "probe_local_tmp_mb", lambda v=val: (v, False)):
        al = a4l_of(md.build_alarms(t=T, **stubs()))
    if val < 2662:
        check(f"W4a {label}（{val}MiB<2662）→ 恰 1 条 amber A4L:tmp 文案逐字一致",
              len(al) == 1 and al[0]["level"] == "amber"
              and al[0]["key"] == "A4L:tmp" and al[0]["message"] == WARN_MSG.format(x=val),
              f"msg={al[0]['message'] if al else None}")
    else:
        check(f"W4a {label}（{val}MiB≥2662）→ 零 A4L 报警（正常放行）", al == [], f"al={al}")

with mock.patch.object(md, "probe_local_tmp_mb", lambda: (-1, True)):
    al = a4l_of(md.build_alarms(t=T, **stubs()))
check("W4b 盘点失败 → 同码 A4L:tmp 文案恰为 '/tmp 盘点失败（fail-closed）'（与写满文案强制区分）",
      len(al) == 1 and al[0]["message"] == FAIL_MSG and al[0]["level"] == "amber", f"al={al}")

# A4 与 A4L 同权共存（anolis 分区>85% + 本机 /tmp 低水 → 两条同列）
anolis_hot = {"ok": True, "disk": {"/data": {"use_pct": 90, "used": "9T", "size": "10T", "avail": "1T"}}}
with mock.patch.object(md, "probe_local_tmp_mb", lambda: (1000, False)):
    al2 = md.build_alarms(t=T, **stubs(anolis=anolis_hot))
codes = [a["code"] for a in al2]
check("W4c A4（anolis 盘>85%）与 A4L（/tmp 低水）同权同列（同一 build_alarms 链）",
      "A4" in codes and "A4L:tmp" in codes, f"codes={codes}")

# ================= PART 3 去重链与 one_round 端到端（沙箱四件套） =================
say("")
say("=" * 72)
say("PART 3 log_alarms 30min 去重同款 + one_round once/daemon 端到端（全沙箱）")
say("=" * 72)
st = {"alarm_open": {}, "alarm_logged": {}, "sweb_img_hist": []}
with mock.patch.object(md, "probe_local_tmp_mb", lambda: (1500, False)):
    alarms = md.build_alarms(t=T, **stubs())
md.log_alarms(alarms, st, T)
n1 = len(open(md.ALARMS_LOG).read().strip().splitlines())
md.log_alarms(alarms, st, T + 60)
n2 = len(open(md.ALARMS_LOG).read().strip().splitlines())
md.log_alarms(alarms, st, T + md.DEDUP_WINDOW + 1)
n3 = len(open(md.ALARMS_LOG).read().strip().splitlines())
row = json.loads(open(md.ALARMS_LOG).read().strip().splitlines()[0])
check("W5a 30min 去重：首记 1 行/窗内不重复/窗外复报（1→1→2）", (n1, n2, n3) == (1, 1, 2),
      f"{n1}/{n2}/{n3}")
check("W5b 流水行字段 amber/A4L:tmp/文案/ts/since 齐全",
      row["level"] == "amber" and row["code"] == "A4L:tmp"
      and row["message"] == WARN_MSG.format(x=1500) and row.get("ts") and row.get("since"),
      f"row={row}")
# 同码去重：盘点失败与写满同 key=A4L:tmp，窗内互斥不双报
with mock.patch.object(md, "probe_local_tmp_mb", lambda: (-1, True)):
    alarms_fail = md.build_alarms(t=T + 120, **stubs())
md.log_alarms(alarms_fail, st, T + 120)
n4 = len(open(md.ALARMS_LOG).read().strip().splitlines())
check("W5c 同码去重：窗内另一文案（盘点失败）不双报（仍 2 行）", n4 == 2, f"n={n4}")

# one_round once 模式：进快照、不落流水（清掉 W5 沙箱流水，验证 once 全程不产该文件）
try:
    os.remove(md.ALARMS_LOG)
except FileNotFoundError:
    pass
state = {"line_hist": [], "last_increase": {}, "first_running": {},
         "sweb_img_hist": [], "alarm_open": {}, "alarm_logged": {},
         "proc_miss_streak": 0}
scan_stubs = [
    mock.patch.object(md, "scan_all_arms", lambda state, t: []),
    mock.patch.object(md, "scan_plan_tiers", lambda: {}),
    mock.patch.object(md, "scan_scheduler", lambda state, t: {
        "status_file_exists": True, "mtime_stale": False,
        "proc_confirmed_down": False, "alive": False, "running_arms": []}),
    mock.patch.object(md, "scan_extra_schedulers", lambda t: []),
    mock.patch.object(md, "scan_anolis", lambda state, t: {"ok": False, "disk": {}}),
    mock.patch.object(md, "scan_local_images", lambda state, t: None),
    mock.patch.object(md, "scan_relay", lambda: {"consecutive_failures": 0, "last_event": "-"}),
    mock.patch.object(md, "probe_local_tmp_mb", lambda: (2000, False)),
    mock.patch.object(md, "build_snapshot",
                      lambda *a, **k: {"alarms": a[5], "totals": {"n_total": 0, "rows_10m": 0}}),
]
with contextlib.ExitStack() as stx:
    for s_ in scan_stubs:
        stx.enter_context(s_)
    snap_once = md.one_round(state, "once")
latest = json.load(open(md.LATEST))
dash = json.load(open(md.DASH_DATA))
check("W6a once 模式：A4L 进快照（返回值+沙箱 latest.json+data.json 三处一致）且文案逐字",
      any(a["code"] == "A4L:tmp" for a in snap_once["alarms"])
      and any(a["code"] == "A4L:tmp" for a in latest["alarms"])
      and any(a["code"] == "A4L:tmp" for a in dash["alarms"])
      and latest["alarms"][0]["message"] == WARN_MSG.format(x=2000)
      if latest["alarms"] else False,
      f"snap={[a['code'] for a in snap_once['alarms']]} latest={latest.get('alarms')}")
check("W6b once 模式不落 alarms.log 流水（与 A4 等同权：快照不落账）",
      not os.path.exists(md.ALARMS_LOG), "alarms.log 不应存在")

# daemon 模式：落流水
with contextlib.ExitStack() as stx:
    for s_ in scan_stubs:
        stx.enter_context(s_)
    snap_d = md.one_round(state, "daemon")
lines = [json.loads(l) for l in open(md.ALARMS_LOG).read().strip().splitlines()]
check("W6c daemon 模式：A4L 经真实 build→log 链落沙箱流水 1 行（30min 去重窗口内一次）",
      any(a["code"] == "A4L:tmp" for a in snap_d["alarms"])
      and len(lines) == 1 and lines[0]["code"] == "A4L:tmp"
      and lines[0]["message"] == WARN_MSG.format(x=2000),
      f"lines={lines}")
check("W6d daemon 模式 state 落沙箱（save_state→STATE_FILE，零产线接触）",
      os.path.exists(md.STATE_FILE) and "A4L:tmp" in json.dumps(json.load(open(md.STATE_FILE))),
      "watch-state.json 沙箱应含 A4L:tmp 键")

# ================= PART 4 after =================
say("")
say("=" * 72)
say("PART 4 after：在飞 watch 未动 / 产线面零 A4L / 现役文件未变")
say("=" * 72)
rc, o, _ = sh("ps -o pid,lstart,etimes --no-headers -p 3692358")
say(f"在飞 watch(after): {o.strip()}")
lstart_same = "00:59:18" in o
check("C1 在飞 watch 同 pid 同启动时间（3692358@00:59:18，未重启）",
      rc == 0 and lstart_same, o.strip())
rc, n_alm2, _ = sh("wc -l < 状态观测/alarms.log")
rc, n_a4l2, _ = sh("grep -c A4L 状态观测/alarms.log 状态观测/latest.json ; true")
a4l_lines = [l for l in n_a4l2.strip().splitlines() if l]
say(f"alarms.log 行数(before={n_alm.strip()} → after={n_alm2.strip()}；"
    f"行数增减=在飞 watch 自身 30min 复报节奏，非本测试所致) A4L 命中={a4l_lines}")
check("C2 产线 alarms.log 与 latest.json 零 A4L 行（在飞旧码不产 A4L）",
      len(a4l_lines) == 2 and all(l.endswith(":0") for l in a4l_lines),
      f"A4L 命中={a4l_lines}")
rc, o, _ = sh("md5sum 状态观测/latest.json 状态观测/watch-state.json")
say(f"状态观测 md5(after): {o.strip()}（latest.json/watch-state.json 由在飞 watch 每轮自写，mtime/md5 变化归因其 60s 轮）")
md5_now = sh(f"md5sum {TARGET}")[1].strip()
say(f"现役文件 md5: {md5_now}")
check("C3 现役 tools/factory-watch.py 全程未变（cb315e90…）",
      "cb315e90eb54136ce59a3625ab9552e2" in md5_now, md5_now)

shutil.rmtree(SB, ignore_errors=True)

# ================= 汇总 =================
say("")
say("=" * 72)
n, total = len(PASS), len(PASS) + len(FAIL)
say(f"{'FAILED ' + str(total - n) + ' 项' if FAIL else '零失败'}；通过 {n}/{total}")
for f_ in FAIL:
    say(f"  FAIL: {f_}")
say("VERDICT: " + ("ALL PASS" if not FAIL else "HAS FAILURES"))
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(LINES) + "\n")
sys.exit(1 if FAIL else 0)
