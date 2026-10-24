#!/usr/bin/env python3
"""补丁① R2 资源闸单测（mock 层，验收项 1-3 的进程内验证）。

边界声明：本测试不触碰现役进程/state.json/真实 ssh/MES——
  · mes_event 打桩记录调用，不真连 ClickHouse；
  · DEFER_STATE_FILE / DEFERRED_LOG / HEARTBEAT 重定向到 /tmp/md-gate-test/（补丁自有
    新工件的测试沙箱，现役旧版进程不读不写它们）；
  · 探针 probe_mem/probe_disk/probe_remote/probe_tmpfs 与 ssh 打桩，不发任何网络/
    远端请求（T4 各桩栈统一喂 tmpfs 开闸假读数，测试不依赖当时 /tmp 实际水位）。
2026-10-22 同批扩展（patch-tmpfs-probe-mcode-R2）：T4g/h/i tmpfs 第四探针矩阵、
T5 常量与 env 覆盖、T6 ENOSPC 自反馈坑加固矩阵（心跳写炸不致死线程）。
运行: python3 补丁/patch1-test-gate.py   （退出码 0=全过，1=有 FAIL）
"""
import builtins
import contextlib
import importlib.util
import io
import json
import os
import queue
import subprocess
import sys
import threading
import time
from unittest import mock

WS = "/home/pan-ding/workspace/agent黑灯工厂"
TEST_ROOT = "/tmp/md-gate-test"

spec = importlib.util.spec_from_file_location(
    "mcode_dispatch", f"{WS}/tools/mcode-dispatch.py")
md = importlib.util.module_from_spec(spec)
spec.loader.exec_module(md)

# 沙箱重定向（模块级常量在方法内按调用时全局名解析，打桩生效）
os.makedirs(TEST_ROOT, exist_ok=True)
md.DEFER_STATE_FILE = f"{TEST_ROOT}/defer-state.json"
md.DEFERRED_LOG = f"{TEST_ROOT}/deferred.log"
md.HEARTBEAT = f"{TEST_ROOT}/heartbeat"

real_sleep = time.sleep
md.time.sleep = lambda s: real_sleep(min(s, 0.05))  # worker 循环内的 sleep 压缩到 50ms

MES_CALLS = []
md.ResourceGate.mes_event = staticmethod(
    lambda kind, _c=MES_CALLS: _c.append(kind))

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append(cond)
    print(f"{'PASS' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail else ""))


def cleanup():
    for p in (md.DEFER_STATE_FILE, md.DEFERRED_LOG, md.HEARTBEAT):
        try:
            os.remove(p)
        except FileNotFoundError:
            pass


# ---------- T1 闸闭时 worker 不取新任务；在飞 solve 不受影响 ----------
d = md.Dispatcher()
d.run_one = mock.MagicMock()  # 打桩：绝不真实起任务
gate = mock.MagicMock()
gate.probe.return_value = (False, ["mock: 资源闸闭"])
gate.defer_tick.return_value = "run"
d.gate = gate
q = queue.Queue()
q.put(("FAKE-TID-1", "m31f"))
q.put(("FAKE-TID-1", "m3"))
state_snap = json.dumps(d.state, sort_keys=True, ensure_ascii=False)

th = threading.Thread(target=d.worker, args=(q,), daemon=True)
th.start()
real_sleep(1.0)
check("T1a 闸闭时任务不出队（2 项全留队列）", q.unfinished_tasks == 2,
      f"unfinished={q.unfinished_tasks}")
check("T1b 未触发 run_one", d.run_one.call_count == 0,
      f"calls={d.run_one.call_count}")
check("T1c 推迟簿记在走（defer_tick 被调）", gate.defer_tick.call_count >= 1,
      f"calls={gate.defer_tick.call_count}")
check("T1d state.json 零写入（推迟不写 phase）",
      json.dumps(d.state, sort_keys=True, ensure_ascii=False) == state_snap)
check("T1e attempts 零计次（推迟不烧 attempts）", len(d.attempts) == 0)

# 在飞不受影响：run_one 执行中途闸翻转闭合，run_one 必须跑完不被打断
started, done = threading.Event(), threading.Event()
run_calls = []


def fake_inflight(tid, prof):
    run_calls.append(tid)
    started.set()
    real_sleep(1.5)  # 模拟在飞 solve
    done.set()       # solve 收尾动作


d2 = md.Dispatcher()
d2.run_one = fake_inflight
gate2 = mock.MagicMock()
gate2.probe.return_value = (True, [])
d2.gate = gate2
q2 = queue.Queue()
q2.put(("FAKE-TID-2", "m31f"))
th2 = threading.Thread(target=d2.worker, args=(q2,), daemon=True)
th2.start()
started.wait(5)
gate2.probe.return_value = (False, ["mock: 取任务后闸才闭"])  # 在飞期间闭闸
check("T1f 在飞 solve 不被打断（跑完收尾）", done.wait(10))
real_sleep(0.6)
check("T1g 闭闸期间不再取下一任务", len(run_calls) == 1, f"calls={len(run_calls)}")

th.join(timeout=2)   # probe 仍闭 → worker 循环挂着（daemon 线程），不影响断言
th2.join(timeout=2)

# ---------- T2 推迟 31min → 升级三通道各 ≥1 行；同期只升一次 ----------
cleanup()
g = md.ResourceGate()
g._why = ["mock: anolis 不可达（fail-closed）"]
g.defer_since = time.time() - 31 * 60  # 连续推迟 31min
g.escalated = False
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ret = g.defer_tick()
out = buf.getvalue()
check("T2a defer_tick 返回 run（未达 24h）", ret == "run")
check("T2b 通道1 klog ALARM ≥1 行", out.count("ALARM") >= 1)
check("T2c 通道2 MES kind=mcode_defer_stalled", MES_CALLS == ["mcode_defer_stalled"],
      f"mes={MES_CALLS}")
dl = open(md.DEFERRED_LOG).read().strip().splitlines()
check("T2d 通道3 deferred.log ≥1 行 ESCALATED", any("ESCALATED" in l for l in dl),
      f"lines={len(dl)}")
check("T2e escalated 置位", g.escalated is True)
check("T2f defer-state.json 持久化（防重启清零）", os.path.exists(md.DEFER_STATE_FILE))
MES_CALLS.clear()
with contextlib.redirect_stdout(io.StringIO()):
    g.defer_tick()
    g.defer_tick()
check("T2g 同一推迟期只升一次", MES_CALLS == [], f"mes={MES_CALLS}")

# ---------- T3 >24h 停取 + 重启接续 + 解除复位 ----------
MES_CALLS.clear()
g.defer_since = time.time() - 25 * 3600  # 越过 halt 阈值
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ret = g.defer_tick()
check("T3a >24h 返回 halt（停取新任务）", ret == "halt")
check("T3b halt 记 ALARM 行", "ALARM" in buf.getvalue())
MES_CALLS.clear()  # halt 不应重复升级
with contextlib.redirect_stdout(io.StringIO()):
    g.defer_tick()
check("T3c halt 后不重复 MES", MES_CALLS == [])

g2 = md.ResourceGate()  # 模拟重启：新进程从 defer-state.json 接续
check("T3d 重启接续 since（不清零）", g2.defer_since is not None
      and abs(g2.defer_since - (time.time() - 25 * 3600)) < 60)
check("T3e 重启接续 escalated/halted（不重复升级）",
      g2.escalated is True and g2.halted is True)
MES_CALLS.clear()
with contextlib.redirect_stdout(io.StringIO()):
    g2.defer_tick()
check("T3f 重启后同期仍只升一次", MES_CALLS == [])

with contextlib.redirect_stdout(io.StringIO()) as buf3:
    g2.opened()  # 闸开
check("T3g 解除后 escalated/halted 复位",
      g2.escalated is False and g2.halted is False and g2.defer_since is None)
check("T3h defer-state.json 清除", not os.path.exists(md.DEFER_STATE_FILE))
check("T3i 解除记日志（含历时）", "推迟解除" in buf3.getvalue())

# ---------- T4 fail-closed 分支（probe 层）----------
g3 = md.ResourceGate()
with mock.patch.object(md.ResourceGate, "probe_mem",
                       staticmethod(lambda: (-1.0, "mock mem 读数异常"))), \
     mock.patch.object(md.ResourceGate, "probe_disk",
                       staticmethod(lambda: (-1.0, "mock disk statvfs 失败", "/x"))), \
     mock.patch.object(md.ResourceGate, "probe_remote",
                       staticmethod(lambda: (-1.0, "mock anolis 不可达"))), \
     mock.patch.object(md.ResourceGate, "probe_tmpfs",
                       staticmethod(lambda: (3.1, None))):
    ok, why = g3.probe()
check("T4a mem 读数异常=放行（不计入 why）",
      all("mem" not in w for w in why), f"why={why}")
check("T4b disk 判不准=闭闸（fail-closed）", any("disk" in w for w in why))
check("T4c anolis 不可达=闭闸（fail-closed）", ok is False and any("anolis" in w for w in why))

g4 = md.ResourceGate()
with mock.patch.object(md.ResourceGate, "probe_mem",
                       staticmethod(lambda: (8.0, None))), \
     mock.patch.object(md.ResourceGate, "probe_disk",
                       staticmethod(lambda: (91.0, None, "/var/lib/docker"))), \
     mock.patch.object(md.ResourceGate, "probe_remote",
                       staticmethod(lambda: (-1.0, "mock tailnet 闪断"))), \
     mock.patch.object(md.ResourceGate, "probe_tmpfs",
                       staticmethod(lambda: (3.1, None))):
    ok, why = g4.probe()
check("T4d 仅远端闪断即闭闸（三取二不放行）", ok is False and len(why) == 1, f"why={why}")

g5 = md.ResourceGate()
with mock.patch.object(md.ResourceGate, "probe_mem",
                       staticmethod(lambda: (3.0, None))), \
     mock.patch.object(md.ResourceGate, "probe_disk",
                       staticmethod(lambda: (91.0, None, "/var/lib/docker"))), \
     mock.patch.object(md.ResourceGate, "probe_remote",
                       staticmethod(lambda: (55.0, None))), \
     mock.patch.object(md.ResourceGate, "probe_tmpfs",
                       staticmethod(lambda: (3.1, None))):
    ok, why = g5.probe()
check("T4e 内存 <4GiB 即闭闸", ok is False and "MemAvailable" in why[0], f"why={why}")

# ---- tmpfs 第四探针（patch-tmpfs-probe-mcode-R2）：fail-closed / 阈值 / 开闸 ----
g6 = md.ResourceGate()
with mock.patch.object(md.ResourceGate, "probe_mem",
                       staticmethod(lambda: (8.0, None))), \
     mock.patch.object(md.ResourceGate, "probe_disk",
                       staticmethod(lambda: (91.0, None, "/var/lib/docker"))), \
     mock.patch.object(md.ResourceGate, "probe_remote",
                       staticmethod(lambda: (55.0, None))), \
     mock.patch.object(md.ResourceGate, "probe_tmpfs",
                       staticmethod(lambda: (-1.0, "mock /tmp statvfs 失败"))):
    ok, why = g6.probe()
check("T4g /tmp statvfs 失败=盘点失败=闭闸（fail-closed）",
      ok is False and any("statvfs 失败" in w for w in why), f"why={why}")

g7 = md.ResourceGate()
with mock.patch.object(md.ResourceGate, "probe_mem",
                       staticmethod(lambda: (8.0, None))), \
     mock.patch.object(md.ResourceGate, "probe_disk",
                       staticmethod(lambda: (91.0, None, "/var/lib/docker"))), \
     mock.patch.object(md.ResourceGate, "probe_remote",
                       staticmethod(lambda: (55.0, None))), \
     mock.patch.object(md.ResourceGate, "probe_tmpfs",
                       staticmethod(lambda: (1.7, None))):
    ok, why = g7.probe()
check("T4h /tmp 1.7G < 2.2G 闭闸（EDQUOT 校准点之下）",
      ok is False and any("/tmp" in w and "< 2.2G" in w for w in why), f"why={why}")

g8 = md.ResourceGate()
with mock.patch.object(md.ResourceGate, "probe_mem",
                       staticmethod(lambda: (8.0, None))), \
     mock.patch.object(md.ResourceGate, "probe_disk",
                       staticmethod(lambda: (91.0, None, "/var/lib/docker"))), \
     mock.patch.object(md.ResourceGate, "probe_remote",
                       staticmethod(lambda: (55.0, None))), \
     mock.patch.object(md.ResourceGate, "probe_tmpfs",
                       staticmethod(lambda: (3.1, None))):
    ok, why = g8.probe()
check("T4i 四条件全过=开闸（含 tmpfs 3.1G）", ok is True and why == [], f"why={why}")

# disk_ok 升级语义：判不准=不足（原为放行）
d3 = md.Dispatcher()


def ssh_boom(cmd, timeout=60, input_text=None, check_flag=False):
    raise RuntimeError("mock ssh 闪断")


with mock.patch.object(md, "ssh", ssh_boom):
    check("T4f disk_ok 判不准=False（原 True）", d3.disk_ok() is False)

# ---------- T5 tmpfs 阈值常量：默认 2.2G + env 覆盖（子进程验证 import 期读取） ----------
check("T5a GATE_TMPFS_MIN_GB 默认 2.2", md.GATE_TMPFS_MIN_GB == 2.2,
      f"got {md.GATE_TMPFS_MIN_GB}")
_probe_code = (
    "import importlib.util; "
    f"s = importlib.util.spec_from_file_location('m', {f'{WS}/tools/mcode-dispatch.py'!r}); "
    "m = importlib.util.module_from_spec(s); s.loader.exec_module(m); "
    "print(m.GATE_TMPFS_MIN_GB)")
_r = subprocess.run([sys.executable, "-c", _probe_code], capture_output=True, text=True,
                    timeout=60,
                    env={**os.environ, "MCODE_GATE_TMPFS_MIN_GB": "5.5"})
check("T5b env MCODE_GATE_TMPFS_MIN_GB 覆盖生效（子进程 5.5）",
      _r.returncode == 0 and float(_r.stdout.strip()) == 5.5,
      f"rc={_r.returncode} out={_r.stdout.strip()!r} err={_r.stderr[-200:]!r}")

# ---------- T6 ENOSPC 自反馈坑加固矩阵（patch-tmpfs-probe-mcode-R2 ②③） ----------
def _enospc_open_factory(blacklist):
    real_open = builtins.open

    def _open(path, *a, **k):
        if str(path) in blacklist:
            raise OSError(28, f"mock ENOSPC（{path}）")
        return real_open(path, *a, **k)
    return _open

# T6a defer_tick 心跳写炸 → 不致命，推迟照走（返回 run，簿记正常）
cleanup()
g9 = md.ResourceGate()
g9._why = ["mock: /tmp 1.7G < 2.2G"]
with mock.patch("builtins.open", _enospc_open_factory({md.HEARTBEAT})):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ret = g9.defer_tick()          # 第一 tick：defer_since 落定 + 心跳写（炸）
        g9._last_hb = 0.0
        ret2 = g9.defer_tick()         # 第二 tick：心跳写再炸，仍不致命
check("T6a 心跳写 ENOSPC 不炸 defer_tick（两次均 run）",
      ret == "run" and ret2 == "run" and g9.defer_since is not None,
      f"ret={ret}/{ret2}")
check("T6a' 写失败记不致命日志（2 行）",
      buf.getvalue().count("heartbeat 写失败（不致命") == 2,
      f"out={buf.getvalue()[-300:]!r}")

# T6b set_phase 心跳写炸 → 不外抛，phase 已落账（state.json 沙箱验证）
_orig_state_file = md.STATE_FILE
md.STATE_FILE = f"{TEST_ROOT}/state.json"
try:
    d6 = md.Dispatcher()
    d6.state = {}
    with mock.patch("builtins.open", _enospc_open_factory({md.HEARTBEAT})):
        d6.set_phase("ENOSPC-TID", "m31f", phase="solving")
    saved = json.load(open(md.STATE_FILE))
    check("T6b set_phase 心跳写 ENOSPC 不外抛且 phase 已落账",
          saved.get("ENOSPC-TID|m31f", {}).get("phase") == "solving",
          f"saved={saved}")
finally:
    try:
        os.remove(md.STATE_FILE)
    except FileNotFoundError:
        pass
    md.STATE_FILE = _orig_state_file

# T6c worker 闸段抛 ENOSPC → 线程不死、不取任务、继续推迟簿记
d7 = md.Dispatcher()
d7.run_one = mock.MagicMock()
gate7 = mock.MagicMock()
gate7.probe.return_value = (False, ["mock: 资源闸闭"])
gate7.defer_tick.side_effect = OSError(28, "mock ENOSPC in defer_tick")
d7.gate = gate7
q7 = queue.Queue()
q7.put(("FAKE-TID-7", "m31f"))
q7.put(("FAKE-TID-7", "m3"))
th7 = threading.Thread(target=d7.worker, args=(q7,), daemon=True)
th7.start()
real_sleep(1.0)
check("T6c defer_tick 连环炸 worker 仍存活且不取任务",
      th7.is_alive() and q7.unfinished_tasks == 2 and d7.run_one.call_count == 0,
      f"alive={th7.is_alive()} unfinished={q7.unfinished_tasks} "
      f"run_one={d7.run_one.call_count}")
check("T6c' 炸后继续下一轮 defer（≥2 次调用=异常被兜住未退出循环）",
      gate7.defer_tick.call_count >= 2, f"calls={gate7.defer_tick.call_count}")
th7.join(timeout=2)

cleanup()
print(f"\n{'ALL PASS' if all(RESULTS) else 'HAS FAILURES'} "
      f"({sum(RESULTS)}/{len(RESULTS)})")
sys.exit(0 if all(RESULTS) else 1)
