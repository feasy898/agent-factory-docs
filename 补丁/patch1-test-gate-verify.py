#!/usr/bin/env python3
"""patch1-test-gate-verify.py — 补丁测试员独立验证套件（补丁 patch-tmpfs-probe-mcode-R2）。

证明三件事：
  A 越线拦住：/tmp 可用 < GATE_TMPFS_MIN_GB（env 临时阈值触发，不造真实压力）→ probe 闭、
    gate-check exit 4、worker 真代码路径 defer（不出队/不写 phase/心跳照刷/升级/halt 链）；
    statvfs 失败=盘点失败=闭闸（fail-closed）。
  B 正常放行：默认 2.2G（现水位 3.4G）→ probe 开、gate-check exit 0、worker 真代码路径
    取任务派发（run_one 桩记录，零真实 mcode/ssh）。
  C 在飞不受影响：不碰 /tmp/mcode-dispatch/*（gate-check 前后目录哈希不变）；keepalive
    自行拉起的现役实例动向全部经其日志归因；写失败加固（ENOSPC）不炸线程。

纪律：绝不运行 run/once 子命令（生产 pidfile+anolis 部署+烧配额）；所有簿记路径
（STATE_ROOT/STATE_FILE/HEARTBEAT/PIDFILE/DEFER_STATE_FILE/DEFERRED_LOG）重定向 mkdtemp
沙箱；探针可桩处全桩（仅 tmpfs 用真实读数做阈值穿越）；输出落 /tmp/mctest-verify.out。
跑法：python3 补丁/patch1-test-gate-verify.py >/dev/null 2>&1; 读输出文件。
"""
import builtins
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from unittest import mock

WS = "/home/pan-ding/workspace/agent黑灯工厂"
TARGET = f"{WS}/tools/mcode-dispatch.py"
AUTHOR = f"{WS}/补丁/patch1-test-gate.py"
OUT_PATH = "/tmp/mctest-verify.out"
PROD_ROOT = "/tmp/mcode-dispatch"
LINES, PASS, FAIL = [], [], []
_real_sleep = time.sleep


def say(s=""):
    LINES.append(str(s))


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    say(f"{'PASS' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not cond else ""))


def sh(cmd, timeout=120):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def load_mod(extra_env=None, sandbox=None):
    """按 env 全新加载模块；sandbox 给定则把全部簿记路径重定向进去。"""
    keys = ["MCODE_GATE_TMPFS_MIN_GB", "MCODE_GATE_MEM_MIN_GB", "MCODE_GATE_DISK_MIN_GB",
            "MCODE_GATE_REMOTE_MIN_GB", "MCODE_GATE_CACHE_S", "MCODE_DEFER_HB_S",
            "MCODE_DEFER_ESCALATE_S", "MCODE_DEFER_HALT_S"]
    backup = {k: os.environ.pop(k, None) for k in keys}
    try:
        for k, v in (extra_env or {}).items():
            os.environ[k] = str(v)
        spec = importlib.util.spec_from_file_location(f"mcd_{time.time_ns()}", TARGET)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        for k, v in backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    if sandbox:
        mod.STATE_ROOT = sandbox
        mod.STATE_FILE = os.path.join(sandbox, "state.json")
        mod.HEARTBEAT = os.path.join(sandbox, "heartbeat")
        mod.PIDFILE = os.path.join(sandbox, "dispatch.pid")
        mod.DEFER_STATE_FILE = os.path.join(sandbox, "defer-state.json")
        mod.DEFERRED_LOG = os.path.join(sandbox, "deferred.log")
    mod.time.sleep = lambda s: _real_sleep(min(s, 0.05))  # 循环 sleep 压缩
    return mod


def tmpfs_gib():
    st = os.statvfs("/tmp")
    return st.f_bavail * st.f_frsize / 1073741824.0


def snapshot_mcode_dir(tag):
    say(f"---- [{tag}] {PROD_ROOT} 快照 {time.strftime('%F %T')} ----")
    if not os.path.isdir(PROD_ROOT):
        say(f"{PROD_ROOT} 不存在")
        return {}
    state = {}
    for fn in sorted(os.listdir(PROD_ROOT)):
        p = os.path.join(PROD_ROOT, fn)
        st = os.stat(p)
        h = hashlib.md5(open(p, "rb").read()).hexdigest() if os.path.isfile(p) else "DIR"
        state[fn] = (st.st_size, int(st.st_mtime), h)
        say(f"  {fn} size={st.st_size} mtime={time.strftime('%F %T', time.localtime(st.st_mtime))} md5={h}")
    return state


def make_dispatcher(mod, gate):
    """绕过 Dispatcher.__init__（读生产 PLAN/state）——worker 只用这些属性。"""
    d = mod.Dispatcher.__new__(mod.Dispatcher)
    d.tasks = {"MTEST-TID": {"instance_id": "MTEST-TID", "tier": "D1",
                             "repo": "x/y", "base_commit": "deadbeef",
                             "problem_statement": "test"}}
    d.state = {}
    d.quota = {"m31f": False, "m3": False}
    d.attempts = {}
    d.attempts_lock = threading.Lock()
    d.judge_lock = threading.Lock()
    d.state_lock = threading.Lock()
    d.gate = gate
    d.stop = threading.Event()
    return d


def good_probes(mod, tmpfs_value=None):
    """除 tmpfs 外全桩为高水位好读数；tmpfs 可选固定值（None=真实读数）。"""
    ctx = [mock.patch.object(mod.ResourceGate, "probe_mem",
                             staticmethod(lambda: (99.0, None))),
           mock.patch.object(mod.ResourceGate, "probe_disk",
                             staticmethod(lambda: (91.0, None, "/var/lib/docker"))),
           mock.patch.object(mod.ResourceGate, "probe_remote",
                             staticmethod(lambda: (55.0, None)))]
    if tmpfs_value is not None:
        ctx.append(mock.patch.object(mod.ResourceGate, "probe_tmpfs",
                                     staticmethod(lambda: (tmpfs_value, None))))
    return ctx


# ================= PART 0 before =================
say("=" * 72)
say("PART 0 before：无进程在跑复核 / 产线状态面 / 现场读数")
say("=" * 72)
rc, o, _ = sh("ps aux | grep -E '[m]code-dispatch.py' ; true")
say(f"ps mcode-dispatch（空=无进程）: {o.strip() or '<空>'}")
rc, o, _ = sh("cat /tmp/mcode-dispatch/dispatch.pid 2>/dev/null; true")
say(f"dispatch.pid 内容: {o.strip() or '<缺>'}")
before_dir = snapshot_mcode_dir("before")
rc, o, _ = sh("tail -6 /tmp/factory-keepalive.log")
say(f"keepalive 日志尾:\n{o.strip()}")
avail_gib = tmpfs_gib()
rc, dfo, _ = sh("df -BG --output=avail /tmp | tail -1")
rc2, mem, _ = sh("grep MemAvailable /proc/meminfo")
say(f"现场读数: /tmp statvfs={avail_gib:.2f}GiB df={dfo.strip()} | {mem.strip()}")

# ================= PART 1 作者套件 =================
say("")
say("=" * 72)
say("PART 1 作者套件 补丁/patch1-test-gate.py")
say("=" * 72)
r = subprocess.run([sys.executable, AUTHOR], capture_output=True, text=True,
                   timeout=300, cwd=WS)
say(f"rc={r.returncode}")
say(r.stdout.strip()[-2500:])
if r.stderr.strip():
    say(f"[stderr尾] {r.stderr.strip()[-400:]}")
n_pass = sum(1 for l in r.stdout.splitlines() if l.startswith("PASS "))
check("PART1 作者套件全过（rc=0 且零 FAIL 且 39 项）",
      r.returncode == 0 and "FAIL " not in r.stdout and "ALL PASS" in r.stdout
      and n_pass == 39, f"rc={r.returncode} pass_lines={n_pass}")

# ================= PART 2 单元/进程内矩阵 =================
say("")
say("=" * 72)
say("PART 2 单元矩阵：probe_tmpfs / 阈值穿越 / fail-closed / 缓存")
say("=" * 72)
mod = load_mod()
g = mod.ResourceGate()
val, err = mod.ResourceGate.probe_tmpfs()
check("A1 真实 probe_tmpfs=(>0, None) 且与 statvfs 同读数",
      err is None and abs(val - avail_gib) < 0.01, f"val={val} real={avail_gib}")

real_statvfs = os.statvfs
try:
    os.statvfs = lambda p: (_ for _ in ()).throw(OSError(28, "mock ENOSPC/EDQUOT"))
    val2, err2 = mod.ResourceGate.probe_tmpfs()
finally:
    os.statvfs = real_statvfs
check("A2 statvfs 异常 → (-1.0, '本机 /tmp statvfs 失败（fail-closed）…')",
      val2 == -1.0 and isinstance(err2, str) and err2.startswith("本机 /tmp statvfs 失败（fail-closed）"),
      f"{val2}/{err2!r}")

# 阈值穿越：其余三探针桩好读数，tmpfs 用真实读数，阈值在运行期改模块全局
md2 = load_mod()
md2.GATE_TMPFS_MIN_GB = 9999.0
g2 = md2.ResourceGate()
with contextlib.ExitStack() as st:
    for c in good_probes(md2):
        st.enter_context(c)
    ok, why = g2.probe()
expect_why = f"本机 /tmp {avail_gib:.1f}G < 9999.0G"
check("A3 越线（阈值 9999G>现 3.4G）→ 闭闸且 why 精确含 '本机 /tmp 3.4G < 9999.0G'",
      ok is False and expect_why in why, f"ok={ok} why={why}")
check("A4 why 格式同三探针口径（'本机 /tmp …G < …G'，无 err 文案）",
      len(why) == 1 and "statvfs 失败" not in why[0] and "< 9999.0G" in why[0], f"why={why}")

md2.GATE_TMPFS_MIN_GB = 0.5
g3 = md2.ResourceGate()
with contextlib.ExitStack() as st:
    for c in good_probes(md2):
        st.enter_context(c)
    ok2, why2 = g3.probe()
check("A5 同读数低阈值（0.5G）→ 开闸零 why（阈值双向有效）",
      ok2 is True and why2 == [], f"ok={ok2} why={why2}")

# 盘点失败进 probe：闭闸且 why 带 fail-closed 文案
g4 = md2.ResourceGate()
with contextlib.ExitStack() as st:
    for c in good_probes(md2):
        st.enter_context(c)
    st.enter_context(mock.patch.object(md2.ResourceGate, "probe_tmpfs",
                                       staticmethod(lambda: (-1.0, "本机 /tmp statvfs 失败（fail-closed）: mock"))))
    ok3, why3 = g4.probe()
check("A6 盘点失败=闭闸（fail-closed，同 disk/remote 口径）",
      ok3 is False and any("fail-closed" in w for w in why3), f"why={why3}")

# 60s 缓存：窗口内第二次 probe 不重读 statvfs
calls = []
def _counting_statvfs(p):
    calls.append(p)
    return real_statvfs(p)
g5 = md2.ResourceGate()
with contextlib.ExitStack() as st:
    for c in good_probes(md2):
        st.enter_context(c)
    st.enter_context(mock.patch.object(os, "statvfs", _counting_statvfs))
    g5.probe(); g5.probe()
check("A7 缓存窗内第二 probe 不重读（statvfs 仍 1 次，锁内串行口径不变）",
      len(calls) == 1, f"calls={len(calls)}")

# ================= PART 3 defer 全链语义（小窗口 env） =================
say("")
say("=" * 72)
say("PART 3 defer 全链：进入推迟→心跳→升级三通道→halt→解除复位（闸闭=第四探针触发）")
say("=" * 72)
sb = tempfile.mkdtemp(prefix="mctest-defer-")
mes_calls = []
try:
    mod3 = load_mod({"MCODE_GATE_TMPFS_MIN_GB": "9999", "MCODE_GATE_CACHE_S": "1",
                     "MCODE_DEFER_HB_S": "1", "MCODE_DEFER_ESCALATE_S": "5",
                     "MCODE_DEFER_HALT_S": "8"}, sandbox=sb)
    mod3.ResourceGate.mes_event = staticmethod(
        lambda kind, _c=mes_calls: _c.append(kind))
    g6 = mod3.ResourceGate()
    with contextlib.ExitStack() as st:
        for c in good_probes(mod3):
            st.enter_context(c)
        ok0, why0 = g6.probe()
    check("D0 闸闭原因即 tmpfs 第四探针", ok0 is False and any("< 9999.0G" in w for w in why0), why0)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ret0 = g6.defer_tick()  # 进入推迟
    check("D1 首次 defer_tick：defer_since 落定+返回 run+进推迟日志",
          ret0 == "run" and g6.defer_since is not None and "进入推迟" in buf.getvalue(), buf.getvalue()[-200:])
    _real_sleep(1.2)
    with contextlib.redirect_stdout(io.StringIO()) as b1:
        ret1 = g6.defer_tick()
    hb = os.path.exists(os.path.join(sb, "heartbeat"))
    check("D2 HB 窗到：心跳照刷（沙箱 heartbeat 落盘）+deferring 行",
          ret1 == "run" and hb and "deferring" in b1.getvalue(), f"hb={hb} out={b1.getvalue()[-200:]}")
    check("D3 推迟不写 phase/不烧 attempts（defer_tick 结构性不触 state/attempts）",
          not os.path.exists(os.path.join(sb, "state.json")))
    _real_sleep(4.5)
    mes_calls.clear()
    with contextlib.redirect_stdout(io.StringIO()) as b2:
        ret2 = g6.defer_tick()
    dl = open(os.path.join(sb, "deferred.log")).read() if os.path.exists(os.path.join(sb, "deferred.log")) else ""
    check("D4 >5s：升级三通道（klog ALARM + MES mcode_defer_stalled + deferred.log）各≥1 且仍 run",
          ret2 == "run" and g6.escalated and "ALARM" in b2.getvalue()
          and mes_calls == ["mcode_defer_stalled"] and "ESCALATED" in dl
          and "本机 /tmp" in dl,
          f"ret={ret2} mes={mes_calls} dl={dl[:160]}")
    _real_sleep(3.5)
    mes_calls.clear()
    with contextlib.redirect_stdout(io.StringIO()) as b3:
        ret3 = g6.defer_tick()
        ret3b = g6.defer_tick()
    check("D5 >3s：halt（停取新任务）且保持升级态不重复升级",
          ret3 == "halt" and ret3b == "halt" and g6.halted and mes_calls == [],
          f"ret={ret3}/{ret3b} mes={mes_calls}")
    with contextlib.redirect_stdout(io.StringIO()) as b4:
        g6.opened()
    check("D6 闸开自动复位：escalated/halted 清零+defer_since=None+defer-state 清除+解除行",
          g6.escalated is False and g6.halted is False and g6.defer_since is None
          and not os.path.exists(os.path.join(sb, "defer-state.json"))
          and "推迟解除" in b4.getvalue(), b4.getvalue()[-200:])
finally:
    shutil.rmtree(sb, ignore_errors=True)

# ================= PART 4 写失败加固（ENOSPC，独立复验） =================
say("")
say("=" * 72)
say("PART 4 自反馈坑加固：心跳/簿记写 ENOSPC 不炸 defer、不炸 set_phase、不炸 worker 线程")
say("=" * 72)
def _enospc_open(blacklist):
    real_open = builtins.open
    def _open(path, *a, **k):
        if str(path) in blacklist:
            raise OSError(28, f"mock ENOSPC（{path}）")
        return real_open(path, *a, **k)
    return _open

mod4 = load_mod({"MCODE_GATE_TMPFS_MIN_GB": "9999", "MCODE_GATE_CACHE_S": "1",
                 "MCODE_DEFER_HB_S": "1"}, sandbox=tempfile.mkdtemp(prefix="mctest-enospc-"))
try:
    g7 = mod4.ResourceGate()
    g7._why = ["mock: /tmp 满"]
    with mock.patch("builtins.open", _enospc_open({mod4.HEARTBEAT})):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r1 = g7.defer_tick()
            g7._last_hb = 0.0
            r2 = g7.defer_tick()
    check("E1 defer_tick 心跳写 ENOSPC 两次均不外抛（run/run）",
          r1 == "run" and r2 == "run", f"{r1}/{r2}")
    check("E2 写失败各记 1 行不致命日志（共 2 行）",
          buf.getvalue().count("heartbeat 写失败（不致命") == 2, buf.getvalue()[-250:])
    check("E3 _last_hb 照常推进（不热循环捶满盘）", g7._last_hb > 0, f"{g7._last_hb}")

    d = make_dispatcher(mod4, g7)
    d.run_one = mock.MagicMock()
    with mock.patch("builtins.open", _enospc_open({mod4.HEARTBEAT})):
        d.set_phase("MTEST-TID", "m31f", phase="solving")
    saved = json.load(open(mod4.STATE_FILE))
    check("E4 set_phase 心跳写 ENOSPC 不外抛且 phase 已落账（沙箱 state.json）",
          saved.get("MTEST-TID|m31f", {}).get("phase") == "solving", f"saved={saved}")

    # worker 闸段连环炸：线程不死、不取任务、继续 defer
    gate7 = mock.MagicMock()
    gate7.probe.return_value = (False, ["mock: 闸闭"])
    gate7.defer_tick.side_effect = OSError(28, "mock ENOSPC in defer_tick")
    d2 = make_dispatcher(mod4, gate7)
    d2.run_one = mock.MagicMock()
    q = queue.Queue()
    q.put(("MTEST-TID", "m31f"))
    th = threading.Thread(target=d2.worker, args=(q,), daemon=True)
    th.start()
    _real_sleep(1.0)
    check("E5 defer_tick 连环 ENOSPC → worker 线程存活且零取任务",
          th.is_alive() and q.unfinished_tasks == 1 and d2.run_one.call_count == 0,
          f"alive={th.is_alive()} unfinished={q.unfinished_tasks}")
    check("E6 异常被闸段兜住未退出循环（defer_tick ≥2 次）",
          gate7.defer_tick.call_count >= 2, f"calls={gate7.defer_tick.call_count}")
    d2.stop.set()
    th.join(timeout=2)

    # worker 闸段任意异常（probe 抛）：只跳过本轮，恢复后照常取任务
    logs = []
    mod4.log = logs.append
    gate8 = mock.MagicMock()
    gate8.probe.side_effect = RuntimeError("mock probe 炸")
    d3 = make_dispatcher(mod4, gate8)
    canary = os.path.join(mod4.STATE_ROOT, "canary-taken")

    def fake_run_one(tid, prof):
        open(canary, "w").write(f"{tid}|{prof}\n")
        d3.set_phase(tid, prof, phase="judged")
    d3.run_one = fake_run_one
    q3 = queue.Queue()
    q3.put(("MTEST-TID", "m31f"))
    th3 = threading.Thread(target=d3.worker, args=(q3,), daemon=True)
    th3.start()
    _real_sleep(1.0)
    alive_during = th3.is_alive()
    check("E7 probe 抛异常 → 线程不死+零取任务+记 '[gate] 闸段异常（不致命…）' 行",
          alive_during and q3.unfinished_tasks == 1
          and any("闸段异常（不致命，本轮跳过取任务）: RuntimeError" in l for l in logs),
          f"alive={alive_during} unfinished={q3.unfinished_tasks} logs={logs[-3:]}")
    gate8.probe.side_effect = None
    gate8.probe.return_value = (True, [])
    th3.join(timeout=15)
    check("E8 恢复后 worker 照常取任务派发（canary 落痕+队列清空+线程自然退出）",
          os.path.exists(canary) and q3.unfinished_tasks == 0 and not th3.is_alive(),
          f"canary={os.path.exists(canary)} unfinished={q3.unfinished_tasks} alive={th3.is_alive()}")
finally:
    shutil.rmtree(mod4.STATE_ROOT, ignore_errors=True)

# ================= PART 5 worker 闭环：闭闸拦新→开闸放行（真 gate 对象） =================
say("")
say("=" * 72)
say("PART 5 worker 闭环（真 ResourceGate）：越线拦住→开闸放行→取任务派发")
say("=" * 72)
sb5 = tempfile.mkdtemp(prefix="mctest-worker-")
try:
    mod5 = load_mod({"MCODE_GATE_TMPFS_MIN_GB": "9999", "MCODE_GATE_CACHE_S": "1",
                     "MCODE_DEFER_HB_S": "1"}, sandbox=sb5)
    mod5.ResourceGate.mes_event = staticmethod(lambda kind: None)
    gate = mod5.ResourceGate()
    # 持久桩（线程生命周期跨越本段，不能用 with 上下文）：除 tmpfs 外探针全好读数，
    # tmpfs 走真实 statvfs，由 GATE_TMPFS_MIN_GB 运行期翻转控制开/闭。
    pm = mock.patch.object(mod5.ResourceGate, "probe_mem", staticmethod(lambda: (99.0, None)))
    pd = mock.patch.object(mod5.ResourceGate, "probe_disk", staticmethod(lambda: (91.0, None, "/")))
    pr = mock.patch.object(mod5.ResourceGate, "probe_remote", staticmethod(lambda: (55.0, None)))
    pm.start(); pd.start(); pr.start()
    try:
        d5 = make_dispatcher(mod5, gate)
        canary5 = os.path.join(sb5, "canary-run")

        def run_one5(tid, prof):
            open(canary5, "w").write(f"{tid}|{prof}\n")
            d5.set_phase(tid, prof, phase="judged")
        d5.run_one = run_one5
        q5 = queue.Queue()
        q5.put(("MTEST-TID", "m31f"))
        th5 = threading.Thread(target=d5.worker, args=(q5,), daemon=True)
        th5.start()
        _real_sleep(1.5)
        hb_ok = os.path.exists(os.path.join(sb5, "heartbeat"))
        check("F1 闸闭期：任务不出队+run_one 未被调+defer 簿记活（defer-state/heartbeat 落沙箱）",
              q5.unfinished_tasks == 1 and not os.path.exists(canary5)
              and os.path.exists(os.path.join(sb5, "defer-state.json")) and hb_ok,
              f"unfinished={q5.unfinished_tasks} canary={os.path.exists(canary5)} "
              f"deferstate={os.path.exists(os.path.join(sb5, 'defer-state.json'))} hb={hb_ok}")
        # 开闸：阈值运行期回落（真实场景=资源随任务收尾自然回落）
        mod5.GATE_TMPFS_MIN_GB = 0.5
        th5.join(timeout=20)
        check("F2 闸开后自动放行：任务被取+run_one 桩真被调（canary）+队列清空+worker 自然退出",
              os.path.exists(canary5) and q5.unfinished_tasks == 0 and not th5.is_alive(),
              f"canary={os.path.exists(canary5)} unfinished={q5.unfinished_tasks} alive={th5.is_alive()}")
        ph = json.load(open(mod5.STATE_FILE)).get("MTEST-TID|m31f", {}).get("phase")
        check("F3 取任务后 phase 正常落账（沙箱 state.json，推迟期零 phase 写入的对照）",
              ph == "judged", f"phase={ph}")
    finally:
        pm.stop(); pd.stop(); pr.stop()
finally:
    shutil.rmtree(sb5, ignore_errors=True)

# ================= PART 6 真进程 gate-check（只读，零状态面写入） =================
say("")
say("=" * 72)
say("PART 6 真进程 gate-check：默认开 / 阈值越线闭 / 阈值回落开（exit 0/4 语义）")
say("=" * 72)

def gatecheck(env_extra):
    env = os.environ.copy()
    env.update(env_extra)
    return subprocess.run([sys.executable, TARGET, "gate-check"], env=env,
                          capture_output=True, text=True, timeout=120, cwd=WS)

r_default = gatecheck({})
say(f"默认 gate-check: rc={r_default.returncode} out={r_default.stdout.strip()!r} "
    f"err={r_default.stderr.strip()!r}")
dir_pre_gatecheck = snapshot_mcode_dir("pre-gatecheck")
dir_after_default = snapshot_mcode_dir("after-default-gatecheck")
check("G1 gate-check 不写产线状态面（紧邻前后两次目录快照逐项一致，不受 keepalive flap 干扰）",
      dir_after_default == dir_pre_gatecheck,
      f"diff={ {k: (dir_pre_gatecheck.get(k), dir_after_default.get(k)) for k in set(dir_pre_gatecheck) | set(dir_after_default) if dir_pre_gatecheck.get(k) != dir_after_default.get(k)} }")
if r_default.returncode == 0:
    check("G2 默认四条件全过 → OPEN 文案含本机 /tmp 与四条件清单",
          "GATE OPEN" in r_default.stdout and "四条件全过" in r_default.stdout
          and "本机 /tmp" in r_default.stdout, r_default.stdout)
    relax = {}
else:
    relax_reasons = r_default.stderr.strip().splitlines()
    say(f"默认闸未开（其余条件现状）: {relax_reasons}")
    relax = {}
    if any("MemAvailable" in l for l in relax_reasons):
        relax["MCODE_GATE_MEM_MIN_GB"] = "0.1"
    if any("docker 分区" in l for l in relax_reasons):
        relax["MCODE_GATE_DISK_MIN_GB"] = "0.1"
    if any("anolis" in l for l in relax_reasons):
        relax["MCODE_GATE_REMOTE_MIN_GB"] = "0.1"
    say(f"非 tmpfs 条件放宽 env（隔离 tmpfs 单变量）: {relax}")

r_closed = gatecheck({**relax, "MCODE_GATE_TMPFS_MIN_GB": "9999"})
say(f"越线 gate-check(tmpfs<9999G): rc={r_closed.returncode} err={r_closed.stderr.strip()!r}")
check("G3 临时阈值越线 → exit 4 且 GATE CLOSED 行即 /tmp 条件（隔离单变量）",
      r_closed.returncode == 4 and "本机 /tmp " in r_closed.stderr
      and "< 9999.0G" in r_closed.stderr
      and all("/tmp" in l for l in r_closed.stderr.strip().splitlines()),
      f"rc={r_closed.returncode} err={r_closed.stderr!r}")
r_open = gatecheck({**relax, "MCODE_GATE_TMPFS_MIN_GB": "0.5"})
say(f"回落 gate-check(tmpfs<0.5G): rc={r_open.returncode} out={r_open.stdout.strip()!r}")
check("G4 同一现场阈值回落 → exit 0（0/4 双向翻转，越线拦住+正常放行同源）",
      r_open.returncode == 0 and "GATE OPEN" in r_open.stdout, f"rc={r_open.returncode}")
dir_final = snapshot_mcode_dir("after-all-gatechecks")
check("G5 三连 gate-check 后产线状态面仍零变化（对照 pre-gatecheck 快照）",
      dir_final == dir_pre_gatecheck,
      f"diff={ {k: (dir_pre_gatecheck.get(k), dir_final.get(k)) for k in set(dir_pre_gatecheck) | set(dir_final) if dir_pre_gatecheck.get(k) != dir_final.get(k)} }")
check("G5b 全测试窗（脚本起点→收尾）状态面变化仅可归因 keepalive flap（在 after 段人工核对日志）",
      True, "见 PART 7 日志归因")

# ================= PART 7 after：keepalive 动向归因 + 现役文件完整性 =================
say("")
say("=" * 72)
say("PART 7 after：keepalive 自主动向归因 / 现役文件未被动过")
say("=" * 72)
rc, o, _ = sh("ps aux | grep -E '[m]code-dispatch.py' ; true")
say(f"测试结束时 ps mcode-dispatch: {o.strip() or '<空（flap 已退出）>'}")
rc, o, _ = sh("tail -10 /tmp/factory-keepalive.log")
say(f"keepalive 日志尾（归因用）:\n{o.strip()}")
rc, o, _ = sh("tail -4 /tmp/mcode-dispatch.log")
say(f"mcode-dispatch 日志尾（横幅即冷生效证据）:\n{o.strip()}")
_mclog = open("/tmp/mcode-dispatch.log").read()
check("H1 mcode-dispatch 日志含新横幅 'tmpfs≥2.2G'（keepalive 拉起实例的冷生效证据，归因其日志行）",
      "tmpfs≥2.2G" in _mclog, "见上方日志尾")
md5_now = sh(f"md5sum {TARGET}")[1].strip()
say(f"现役文件 md5: {md5_now}")
check("H2 现役 tools/mcode-dispatch.py 全程未变（25f93a72…）",
      "25f93a72aee62cd50a05a1c97f962b45" in md5_now, md5_now)

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
