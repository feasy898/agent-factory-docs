#!/usr/bin/env python3
"""patch5-test-a4l-watch.py — 补丁「patch-tmpfs-alarm-watch-A4L-R2」作者套件。

被测对象：tools/factory-watch.py 的 A4L 本机 /tmp 安灯（D-24 / 方案 P1-1）。
纪律：零生产副作用——不跑真实 --once/常驻轮（那会写生产 latest.json/data.json/
watch-state.json 并与在飞 watch pid 抢 state）；anolis/docker/relay 扫描全部打桩；
ALARMS_LOG/LATEST/DASH_DATA/STATE_FILE 重定向 /tmp/a4l-watch-test/ 沙箱。
跑法：python3 补丁/patch5-test-a4l-watch.py   （期望末行 ALL PASS (N/N)，rc=0）
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from unittest import mock

WS = "/home/pan-ding/workspace/agent黑灯工厂"
TARGET = f"{WS}/tools/factory-watch.py"
TEST_ROOT = "/tmp/a4l-watch-test"

spec = importlib.util.spec_from_file_location("fw_under_test", TARGET)
md = importlib.util.module_from_spec(spec)
spec.loader.exec_module(md)

os.makedirs(TEST_ROOT, exist_ok=True)
md.ALARMS_LOG = f"{TEST_ROOT}/alarms.log"
md.LATEST = f"{TEST_ROOT}/latest.json"
md.DASH_DATA = f"{TEST_ROOT}/data.json"
md.STATE_FILE = f"{TEST_ROOT}/watch-state.json"

T = 1792610000.0  # 固定 epoch（since 字段确定性）
WARN_MSG = ("本机 /tmp 可用 {x} MiB<2662MiB（usrquota 校准线，闸线 2252MiB，"
            "低于则 sched/mcode 拦新臂/新判分）")
FAIL_MSG = "/tmp 盘点失败（fail-closed）"

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"{'PASS' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not cond else ""))


def stubs(tmp_probe):
    """build_alarms 最小桩输入：其余环全静默，只有 A4L 由 tmp_probe 驱动。"""
    return dict(
        arms=[], plan=[],
        sched={"status_file_exists": True, "mtime_stale": False,
               "proc_confirmed_down": False, "alive": False, "running_arms": []},
        anolis={}, relay={"consecutive_failures": 0, "last_event": "-"},
        state={"alarm_open": {}, "alarm_logged": {}, "sweb_img_hist": []},
        extras=None, archived=None,
    )


def a4l_of(alarms):
    return [a for a in alarms if a["code"] == "A4L:tmp"]


# ---------- T1 真实 statvfs 读数与 df 互证 ----------
mb, fail = md.probe_local_tmp_mb()
df_kib = int(subprocess.run(["df", "-P", "/tmp"], capture_output=True, text=True)
             .stdout.splitlines()[-1].split()[3])
check("T1 真实读数 (mb, False) 且与 df ±200MiB 互证",
      fail is False and mb > 0 and abs(mb - df_kib // 1024) <= 200,
      f"probe={mb} df={df_kib // 1024} fail={fail}")

# ---------- T2 盘点失败 → (-1, True) ----------
with mock.patch.object(md.os, "statvfs", side_effect=OSError(28, "mock ENOSPC")):
    mb2, fail2 = md.probe_local_tmp_mb()
check("T2 statvfs 异常 → (-1, True) 盘点失败", mb2 == -1 and fail2 is True,
      f"got {mb2}/{fail2}")

# ---------- T3 build_alarms A4L 环：开位/预警/边界/盘点失败文案强制区分 ----------
s = stubs(None)
with mock.patch.object(md, "probe_local_tmp_mb", lambda: (3000, False)):
    al = a4l_of(md.build_alarms(t=T, **s))
check("T3a /tmp 3000MiB≥2662 → 不报", al == [], f"alarms={al}")

with mock.patch.object(md, "probe_local_tmp_mb", lambda: (2000, False)):
    al = a4l_of(md.build_alarms(t=T, **s))
check("T3b 2000MiB → 1 条 amber A4L:tmp 且文案逐字一致",
      len(al) == 1 and al[0]["level"] == "amber"
      and al[0]["message"] == WARN_MSG.format(x=2000),
      f"msg={al[0]['message'] if al else None}")

with mock.patch.object(md, "probe_local_tmp_mb", lambda: (2662, False)):
    al_eq = a4l_of(md.build_alarms(t=T, **s))
with mock.patch.object(md, "probe_local_tmp_mb", lambda: (2661, False)):
    al_lt = a4l_of(md.build_alarms(t=T, **s))
check("T3c 阈值边界：=2662 不报（严格小于），2661 报",
      al_eq == [] and len(al_lt) == 1,
      f"eq={al_eq} lt={len(al_lt)}")

with mock.patch.object(md, "probe_local_tmp_mb", lambda: (-1, True)):
    al = a4l_of(md.build_alarms(t=T, **s))
check("T3d 盘点失败 → 同码 A4L:tmp、文案=盘点失败且与写满文案强制区分",
      len(al) == 1 and al[0]["message"] == FAIL_MSG
      and FAIL_MSG != WARN_MSG.format(x=2000)
      and "MiB" not in al[0]["message"] and "fail-closed" in al[0]["message"],
      f"msg={al[0]['message'] if al else None}")

# ---------- T4 log_alarms 30min 去重同款（沙箱 alarms.log） ----------
try:
    os.remove(md.ALARMS_LOG)
except FileNotFoundError:
    pass
st = {"alarm_open": {}, "alarm_logged": {}, "sweb_img_hist": []}
with mock.patch.object(md, "probe_local_tmp_mb", lambda: (1500, False)):
    alarms = md.build_alarms(t=T, **stubs(None))
md.log_alarms(alarms, st, T)
n1 = len(open(md.ALARMS_LOG).read().strip().splitlines())
md.log_alarms(alarms, st, T + 60)     # 去重窗内
n2 = len(open(md.ALARMS_LOG).read().strip().splitlines())
md.log_alarms(alarms, st, T + md.DEDUP_WINDOW + 1)  # 窗外复报
n3 = len(open(md.ALARMS_LOG).read().strip().splitlines())
row = json.loads(open(md.ALARMS_LOG).read().strip().splitlines()[0])
check("T4a 30min 去重：首记 1 行/窗内不重复/窗外复报（1→1→2）",
      (n1, n2, n3) == (1, 1, 2), f"lines={n1}/{n2}/{n3}")
check("T4b 流水行字段：amber/A4L:tmp/文案/ts/since 齐全",
      row["level"] == "amber" and row["code"] == "A4L:tmp"
      and row["message"] == WARN_MSG.format(x=1500)
      and bool(row.get("ts")) and bool(row.get("since")),
      f"row={row}")

# ---------- T5 one_round 端到端（全扫描桩 + 沙箱四件套，daemon 模式落 alarms.log） ----------
try:
    os.remove(md.ALARMS_LOG)
except FileNotFoundError:
    pass
state = {"line_hist": [], "last_increase": {}, "first_running": {},
         "sweb_img_hist": [], "alarm_open": {}, "alarm_logged": {},
         "proc_miss_streak": 0}
with mock.patch.object(md, "scan_all_arms", lambda state, t: []), \
     mock.patch.object(md, "scan_plan_tiers", lambda: {}), \
     mock.patch.object(md, "scan_scheduler", lambda state, t: {
         "status_file_exists": True, "mtime_stale": False,
         "proc_confirmed_down": False, "alive": False, "running_arms": []}), \
     mock.patch.object(md, "scan_extra_schedulers", lambda t: []), \
     mock.patch.object(md, "scan_anolis", lambda state, t: {"ok": False, "disk": {}}), \
     mock.patch.object(md, "scan_local_images", lambda state, t: None), \
     mock.patch.object(md, "scan_relay", lambda: {"consecutive_failures": 0,
                                                  "last_event": "-"}), \
     mock.patch.object(md, "probe_local_tmp_mb", lambda: (1000, False)), \
     mock.patch.object(md, "build_snapshot",
                       lambda *a, **k: {"alarms": a[5],
                                        "totals": {"n_total": 0, "rows_10m": 0}}):
    snap = md.one_round(state, "daemon")
lines = [json.loads(l) for l in open(md.ALARMS_LOG).read().strip().splitlines()]
check("T5 one_round daemon 模式端到端：A4L 经真实 build→log 链落沙箱流水",
      any(a["code"] == "A4L:tmp" for a in snap["alarms"])
      and len(lines) == 1 and lines[0]["code"] == "A4L:tmp"
      and lines[0]["message"] == WARN_MSG.format(x=1000),
      f"snap_codes={[a['code'] for a in snap['alarms']]} lines={lines}")

# ---------- 汇总 + 沙箱清理 ----------
shutil.rmtree(TEST_ROOT, ignore_errors=True)
n, total = len(PASS), len(PASS) + len(FAIL)
print(f"\n{total - n} FAILED, {n} passed" if FAIL else "")
print(f"ALL PASS ({n}/{total})")
sys.exit(1 if FAIL else 0)
