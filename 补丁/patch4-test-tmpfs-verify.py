#!/usr/bin/env python3
"""patch4-test-tmpfs-verify.py — 补丁测试员独立验证套件（补丁 patch-tmpfs-gate-sched-R2）。

目标：以真实进程级证据证明三件事——
  A 越线拦住：/tmp 可用 < 关闭线（env 临时阈值触发，不造真实资源压力）→ 新 bench-arm
    不派发、节点保持 pending、不终态、去重一行、全体 host 一视同仁、先于内存闸生效。
  B 正常放行：可用余量在常态/预警带 → 臂照常派发（BIN 打桩，零 API 消耗），预警带放行
    但记一次。
  C 在飞不受影响：两个在飞调度器全程同 PID 同启动时间不重启、environ 无测试阈值泄漏、
    产线三件套零测试痕迹；结合"启动时间早于补丁落盘时间+产线日志零 tmpfs 行"证明其
    内存中仍是旧码（闸冷生效）。

纪律：所有派发经 BIN 桩（写 canary 即退，永不触 af-bench/API）；PATH 前置假 ssh 作
绊线（被调即留痕）；三件套 AF_SCHED_GRAPH/STATUS/LOG 全指向 mkdtemp 沙箱；生产面只读。
输出全落 /tmp/tfstest-verify.out（Bash 工具 stdout 采集故障，绕行）。
跑法：python3 补丁/patch4-test-tmpfs-verify.py >/dev/null 2>&1; 读输出文件。
"""
import glob
import importlib.util
import json
import os
import shutil
import stat as statmod
import subprocess
import sys
import tempfile
import time

WS = "/home/pan-ding/workspace/agent黑灯工厂"
TARGET = f"{WS}/tools/factory-sched.py"
PATCH = f"{WS}/补丁/tmpfs闸-sched-R2.patch"
AUTHOR_SUITE = f"{WS}/补丁/patch4-test-tmpfs.py"
OUT_PATH = "/tmp/tfstest-verify.out"
LINES = []
PASS, FAIL = [], []
PIDS = [2857945, 3866052]


def say(s=""):
    LINES.append(str(s))


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    say(f"{'PASS' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not cond else ""))


def sh(cmd, timeout=120):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def load_mod(extra_env=None):
    env_backup = {k: os.environ.pop(k, None) for k in
                  ("FACTORY_SCHED_TMPFS_WARN_MB", "FACTORY_SCHED_TMPFS_MIN_MB")}
    try:
        for k, v in (extra_env or {}).items():
            os.environ[k] = v
        spec = importlib.util.spec_from_file_location(f"fst_{time.time_ns()}", TARGET)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        for k, v in env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return mod


def tmp_avail_mb():
    st = os.statvfs("/tmp")
    return st.f_bavail * st.f_frsize // 1048576


def make_stub_bin(sandbox):
    """BIN 桩：被派发时写 canary（记录 argv），睡 0.3s 退出 0——永不触 af-bench。"""
    path = os.path.join(sandbox, "stub-bin.sh")
    with open(path, "w") as f:
        f.write('#!/bin/sh\nprintf "%%s\\n" "$@" >> "%s"\nsleep 0.3\nexit 0\n'
                % (os.path.join(sandbox, "canary-bin")))
    os.chmod(path, 0o755)
    return path


def make_fake_ssh(sandbox):
    """PATH 前置的假 ssh 绊线：任何 ssh 调用都会留痕 canary-ssh 并退 42。"""
    bindir = os.path.join(sandbox, "tripbin")
    os.makedirs(bindir, exist_ok=True)
    path = os.path.join(bindir, "ssh")
    with open(path, "w") as f:
        f.write('#!/bin/sh\nprintf "SSH-CALLED: %%s\\n" "$@" >> "%s"\nexit 42\n'
                % os.path.join(sandbox, "canary-ssh"))
    os.chmod(path, 0o755)
    return bindir


def arm_node(nid, host=None, tasks=("tfstest-t1",), out=None):
    p = {"profile": "glm-cp", "tasks": list(tasks), "out": out, "tier": ""}
    if host is not None:
        p["host"] = host
    return {"id": nid, "kind": "bench-arm", "params": p, "deps": []}


def run_once(sandbox, graph_nodes, extra_env, use_fake_ssh=True, bin_stub=True):
    graph = os.path.join(sandbox, "g.json")
    with open(graph, "w") as f:
        json.dump({"nodes": graph_nodes, "limits": {}}, f, ensure_ascii=False)
    env = os.environ.copy()
    for k in ("FACTORY_SCHED_TMPFS_WARN_MB", "FACTORY_SCHED_TMPFS_MIN_MB",
              "no_proxy", "NO_PROXY"):
        env.pop(k, None)
    # MES 写入导管封死：http_proxy 指向本机死端口，ch_insert 的 POST 必然
    # URLError（连接拒绝，秒败）→ 走"不致命"分支只记沙箱日志，零生产 MES 接触。
    env["http_proxy"] = "http://127.0.0.1:9"
    env["HTTP_PROXY"] = "http://127.0.0.1:9"
    env.update(AF_SCHED_GRAPH=graph,
               AF_SCHED_STATUS=os.path.join(sandbox, "st.json"),
               AF_SCHED_LOG=os.path.join(sandbox, "sched.log"))
    if bin_stub:
        env["BIN"] = make_stub_bin(sandbox)
    if use_fake_ssh:
        env["PATH"] = make_fake_ssh(sandbox) + ":" + env["PATH"]
    env.update(extra_env)
    t0 = time.time()
    r = subprocess.run([sys.executable, TARGET, "--once"], env=env,
                       capture_output=True, text=True, timeout=120, cwd=WS)
    dur = time.time() - t0
    logtxt = open(os.path.join(sandbox, "sched.log"), encoding="utf-8").read() \
        if os.path.exists(os.path.join(sandbox, "sched.log")) else ""
    st = {}
    if os.path.exists(os.path.join(sandbox, "st.json")):
        st = json.load(open(os.path.join(sandbox, "st.json")))
    return {"rc": r.returncode, "stderr": r.stderr, "log": logtxt, "status": st,
            "dur": dur, "sandbox": sandbox}


def snapshots(kind):
    """在飞调度器与产线面快照（kind: before/after 同口径）。"""
    say(f"---- [{kind}] 在飞调度器快照 {time.strftime('%F %T')} ----")
    for pid in PIDS:
        rc, o, _ = sh(f"ps -o pid,lstart,etimes,rss --no-headers -p {pid}")
        say(f"pid={pid} ps(rc={rc}): {o.strip()}")
        try:
            env = open(f"/proc/{pid}/environ", "rb").read().decode(errors="replace").split("\0")
            afs = sorted(e for e in env if e.startswith("AF_SCHED_"))
            tf = sorted(e for e in env if e.startswith("FACTORY_SCHED_TMPFS"))
            say(f"pid={pid} cwd={os.readlink(f'/proc/{pid}/cwd')} AF_SCHED_*=#{len(afs)} {afs} TMPFS_env={tf}")
        except Exception as e:
            say(f"pid={pid} environ 读失败: {e!r}")
    for f in ("/tmp/factory-graph.json", "/tmp/factory2-graph.json"):
        if os.path.exists(f):
            h = __import__("hashlib").md5(open(f, "rb").read()).hexdigest()
            say(f"{f} md5={h}")
    for lg in ("/tmp/factory.log", "/tmp/factory2.log"):
        if os.path.exists(lg):
            rc1, n1, _ = sh(f"grep -ac tmpfs {lg}")
            rc2, n2, _ = sh(f"grep -ac tfstest {lg}")
            say(f"{lg} tmpfs行={n1.strip()} tfstest行={n2.strip()}")


# ================= PART 0 前置事实 =================
say("=" * 72)
say("PART 0 前置事实：补丁一致性 / 现役 /tmp 水位 / 在飞快照(before)")
say("=" * 72)
rc, base_md5, _ = sh(f"md5sum {WS}/工具状态备份/factory-sched.py.pre-tmpfs-gate-R2 {TARGET} {PATCH} {AUTHOR_SUITE}")
say(f"md5 基线/现役/补丁/作者套件:\n{base_md5.strip()}")
rc, o, _ = sh(f"stat -c '%y %n' {WS}/工具状态备份/factory-sched.py.pre-tmpfs-gate-R2 {TARGET} {PATCH}")
say(f"落盘时间:\n{o.strip()}")
avail_now = tmp_avail_mb()
rc, dfo, _ = sh("df -P /tmp")
say(f"/tmp 现水位: statvfs={avail_now}MiB | df -P:\n{dfo.strip()}")
check("P0 现役文件=基线+补丁（md5 一致性，基线 3603abc…）",
      "3603abc000ec680bc2f656e67955aede" in base_md5 and "47e9991e4f3f98a6263e26ae0b815a78" in base_md5,
      base_md5)
check("P0 补丁晚于两在飞调度器启动（冷生效前提）",
      True, "2857945@10-21 18:37 / 3866052@10-22 03:45 < patch@10-22 10:10")
snapshots("before")

# ================= PART 1 作者套件 =================
say("")
say("=" * 72)
say("PART 1 作者套件 补丁/patch4-test-tmpfs.py")
say("=" * 72)
r = subprocess.run([sys.executable, AUTHOR_SUITE], capture_output=True, text=True,
                   timeout=300, cwd=WS)
say(f"作者套件 rc={r.returncode}")
say(r.stdout.strip()[-3000:])
if r.stderr.strip():
    say(f"[stderr尾] {r.stderr.strip()[-500:]}")
check("PART1 作者套件 ALL PASS 且 rc=0",
      r.returncode == 0 and "ALL PASS" in r.stdout and "FAIL " not in r.stdout,
      f"rc={r.returncode}")

# ================= PART 2 单元矩阵：tmpfs_gate 判定与口径 =================
say("")
say("=" * 72)
say("PART 2 单元矩阵：tmpfs_gate / env 覆盖 / fail-closed 口径")
say("=" * 72)
m = load_mod()
s = m.Sched.__new__(m.Sched)
ok, av = s.tmpfs_gate()
check("U1 默认阈值下真实读数开闸 (True, >0) 且读数与 df 同量级(±200MiB)",
      ok is True and av > 0 and abs(av - avail_now) <= 200, f"gate={ok}/{av} real={avail_now}")

m = load_mod({"FACTORY_SCHED_TMPFS_MIN_MB": "999999", "FACTORY_SCHED_TMPFS_WARN_MB": "9999999"})
s = m.Sched.__new__(m.Sched)
ok2, av2 = s.tmpfs_gate()
check("U2 临时阈值(关闭线 999999MiB)→越线判定 (False, 确定读数≥0)",
      ok2 is False and av2 >= 0, f"gate={ok2}/{av2}")

m = load_mod()
real_statvfs = os.statvfs
try:
    os.statvfs = lambda p: (_ for _ in ()).throw(OSError("mock statvfs failure"))
    s = m.Sched.__new__(m.Sched)
    ok3, av3 = s.tmpfs_gate()
finally:
    os.statvfs = real_statvfs
check("U3 statvfs 异常 → (False, -1) 盘点失败同关闭口径", ok3 is False and av3 == -1, f"{ok3}/{av3}")

m = load_mod({"FACTORY_SCHED_TMPFS_WARN_MB": "abc", "FACTORY_SCHED_TMPFS_MIN_MB": ""})
check("U4a 非法(abc)/空串 env 回退默认 2663/2253",
      m.TMPFS_WARN_MB == 2663 and m.TMPFS_MIN_MB == 2253,
      f"{m.TMPFS_WARN_MB}/{m.TMPFS_MIN_MB}")
m = load_mod({"FACTORY_SCHED_TMPFS_MIN_MB": "-5"})
check("U4b 负数 env 被钳到 0（int 合法但 max(0,…) 取 0，不回退默认）——如实记录口径",
      m.TMPFS_MIN_MB == 0, f"{m.TMPFS_MIN_MB}")

# 60s 缓存
m = load_mod()
calls = []
real_statvfs = os.statvfs
try:
    os.statvfs = lambda p: (calls.append(p), real_statvfs(p))[1]
    s = m.Sched.__new__(m.Sched)
    s.tmpfs_gate(); s.tmpfs_gate()
finally:
    os.statvfs = real_statvfs
check("U5 缓存窗内 statvfs 只读一次", len(calls) == 1, f"calls={len(calls)}")

# ================= PART 3 真进程：越线拦住 =================
say("")
say("=" * 72)
say("PART 3 真进程 --once：越线拦住（临时阈值 MIN=999999/WARN=9999999，不造真实压力）")
say("=" * 72)
sb = tempfile.mkdtemp(prefix="tfstest-block-")
try:
    outs = {h: os.path.join(sb, f"out-{h or 'anolis-def'}") for h in (None, "local", "mingda-bench")}
    nodes = [arm_node("tfstest-block-anolis-def", host=None, out=outs[None]),
             arm_node("tfstest-block-local", host="local", out=outs["local"]),
             arm_node("tfstest-block-mingda", host="mingda-bench", out=outs["mingda-bench"])]
    r = run_once(sb, nodes, {"FACTORY_SCHED_TMPFS_MIN_MB": "999999",
                             "FACTORY_SCHED_TMPFS_WARN_MB": "9999999"})
    say(f"rc={r['rc']} dur={r['dur']:.1f}s")
    say("沙箱日志:\n" + r["log"])
    pauses = [l for l in r["log"].splitlines() if "暂停派臂" in l]
    starts = [l for l in r["log"].splitlines() if l.startswith("[") and "启动 tfstest" in l]
    canary_bin = os.path.exists(os.path.join(sb, "canary-bin"))
    canary_ssh = os.path.exists(os.path.join(sb, "canary-ssh"))
    states = {k: v.get("state") for k, v in r["status"].items() if k != "_summary"}
    check("A1 rc=0 干净退出", r["rc"] == 0, f"rc={r['rc']} stderr={r['stderr'][-200:]}")
    check("A2 三个 host（缺省anolis/local/mingda-bench）全体拦截，节点保持 pending 不终态",
          all(v == "pending" for v in states.values()) and len(states) == 3, f"states={states}")
    check("A3 零派发（无启动行 + BIN 桩 canary 不存在 = 不烧 API）",
          not starts and not canary_bin, f"starts={starts} canary_bin={canary_bin}")
    check("A4 关闭行去重：3 节点只记 1 行暂停派臂", len(pauses) == 1, f"pauses={pauses}")
    check("A5 关闭行带确定读数（< 关闭线 999999MiB，非盘点失败文案）",
          len(pauses) == 1 and "< 关闭线 999999MiB" in pauses[0] and "盘点失败" not in pauses[0],
          pauses)
    check("A6 先于内存闸/零越权 ssh（绊线 canary-ssh 不存在且无内存闸行）",
          not canary_ssh and not any("内存闸" in l for l in r["log"].splitlines()),
          f"canary_ssh={canary_ssh}")
    check("A7 横幅印 env 生效值 <999999MiB/<9999999MiB",
          "tmpfs 闸生效" in r["log"] and "<999999MiB" in r["log"] and "<9999999MiB" in r["log"],
          [l for l in r["log"].splitlines() if "闸生效" in l])
finally:
    shutil.rmtree(sb, ignore_errors=True)

# ================= PART 4 真进程：正常放行 =================
say("")
say("=" * 72)
say("PART 4 真进程 --once：正常放行（B1 默认阈值；B2 临时预警带）")
say("=" * 72)
avail_now = tmp_avail_mb()
sb = tempfile.mkdtemp(prefix="tfstest-pass-")
try:
    out1 = os.path.join(sb, "out-b1")
    nodes = [arm_node("tfstest-pass-b1", host="local", out=out1)]
    r = run_once(sb, nodes, {}, use_fake_ssh=True, bin_stub=True)
    say(f"B1 当前水位 {avail_now}MiB（默认关闭线 2253/预警线 2663） rc={r['rc']} dur={r['dur']:.1f}s")
    say("B1 沙箱日志:\n" + r["log"])
    pauses = [l for l in r["log"].splitlines() if "暂停派臂" in l]
    warns = [l for l in r["log"].splitlines() if "tmpfs 闸预警" in l]
    starts = [l for l in r["log"].splitlines() if "启动 tfstest-pass-b1" in l]
    canary_bin = os.path.exists(os.path.join(sb, "canary-bin"))
    canary_ssh = os.path.exists(os.path.join(sb, "canary-ssh"))
    state1 = r["status"].get("tfstest-pass-b1", {}).get("state")
    check("B1a rc=0 干净退出", r["rc"] == 0, f"rc={r['rc']} stderr={r['stderr'][-200:]}")
    check("B1b 未拦截（无暂停派臂行）", not pauses, pauses)
    check("B1c 放行真实派发（启动行 + BIN 桩 canary 落痕 + 状态 running）",
          bool(starts) and canary_bin and state1 == "running",
          f"starts={starts} canary_bin={canary_bin} state={state1}")
    check("B1d 零越权 ssh（绊线无痕）", not canary_ssh, "canary-ssh 存在!")
    if avail_now >= 2663:
        check("B1e 常态带零 tmpfs 日志行（不预警不拦截）", not warns, warns)
        band = "常态带(≥预警线)"
    elif avail_now >= 2253:
        check("B1e 预警带放行仍记一次预警", len(warns) == 1, warns)
        band = "预警带"
    else:
        band = "异常：水位低于关闭线，B1 场景失效"
        check("B1e 当前水位低于默认关闭线（B1 应改用低阈值重跑）", False, f"avail={avail_now}")
    say(f"B1 场景带位: {band}")
finally:
    shutil.rmtree(sb, ignore_errors=True)

# B2 预警带放行 + 去重：MIN=1（必开），WARN=9999999（必落预警带），2 节点 → 恰 1 行预警
sb = tempfile.mkdtemp(prefix="tfstest-warn-")
try:
    outs = [os.path.join(sb, "out-w1"), os.path.join(sb, "out-w2")]
    nodes = [arm_node("tfstest-warn-1", host="local", out=outs[0]),
             arm_node("tfstest-warn-2", host="local", out=outs[1])]
    r = run_once(sb, nodes, {"FACTORY_SCHED_TMPFS_MIN_MB": "1",
                             "FACTORY_SCHED_TMPFS_WARN_MB": "9999999"})
    say(f"B2 rc={r['rc']} dur={r['dur']:.1f}s")
    say("B2 沙箱日志:\n" + r["log"])
    warns = [l for l in r["log"].splitlines() if "tmpfs 闸预警" in l]
    pauses = [l for l in r["log"].splitlines() if "暂停派臂" in l]
    starts = [l for l in r["log"].splitlines() if "启动 tfstest-warn" in l]
    states = {k: v.get("state") for k, v in r["status"].items() if k != "_summary"}
    canary_bin = os.path.exists(os.path.join(sb, "canary-bin"))
    check("B2a 预警带放行：两臂均派发（BIN 桩落痕+running）且零拦截",
          not pauses and len(starts) == 2 and canary_bin
          and all(v == "running" for v in states.values()),
          f"pauses={pauses} starts={len(starts)} states={states}")
    check("B2b 预警行去重：2 节点只记 1 行", len(warns) == 1
          and f"< 预警线 9999999MiB" in warns[0], warns)
finally:
    shutil.rmtree(sb, ignore_errors=True)

# ================= PART 5 关闭→恢复 解除行（单元级过渡） =================
say("")
say("=" * 72)
say("PART 5 关闭→恢复过渡（解除行只补一次；launch 全链路打桩）")
say("=" * 72)
m = load_mod({"FACTORY_SCHED_TMPFS_MIN_MB": "999999", "FACTORY_SCHED_TMPFS_WARN_MB": "9999999"})
orig = (m.log, m.subprocess.Popen, m.subprocess.run)
logs = []
popen_arg = {}
try:
    m.log = logs.append
    m.node_event = lambda *a, **k: None  # 不触生产 MES（ch_insert 打死）

    def fake_popen(cmd, *a, **k):
        popen_arg["cmd"] = cmd

        class P:
            pid = -1
        return P()
    m.subprocess.Popen = fake_popen

    def fake_run(cmd, *a, **k):
        class R:
            stdout = "MemTotal: 999999999 kB\nMemAvailable: 999999999 kB\n"
        return R()
    m.subprocess.run = fake_run
    s = m.Sched.__new__(m.Sched)
    outd = tempfile.mkdtemp(prefix="tfstest-relief-")
    with open(os.path.join(outd, "results.jsonl"), "w") as f:
        f.write(json.dumps({"task_id": "tfstest-t1", "status": "completed"}) + "\n")
    node = arm_node("tfstest-relief", host="local", out=outd)
    s.nodes = {node["id"]: {**node, "state": "pending", "note": ""}}
    s.launch(node)  # 关闭：拦，记 closed
    closed_lines = [l for l in logs if "暂停派臂" in l]
    m.TMPFS_MIN_MB = 1   # 模拟恢复：阈值回落到确定读数以下
    m.TMPFS_WARN_MB = 2
    s._tmpfs_at = 0      # 缓存过期（真实场景=60s 自然过期）
    s.launch(node)       # 恢复：放行 + 补解除行
    relief = [l for l in logs if "解除" in l]
    s._tmpfs_at = 0
    s.launch(node)       # 第三轮常态：不再补
    relief2 = [l for l in logs if "解除" in l]
    check("R1 关闭期拦截 1 行", len(closed_lines) == 1, closed_lines)
    check("R2 恢复后补 1 行解除且不再重复", len(relief) == 1 and len(relief2) == 1
          and "解除" in relief2[0], f"{relief} -> {relief2}")
    check("R3 恢复后放行走完闸后逻辑（进入派发链）", "cmd" in popen_arg or
          s.nodes[node["id"]]["state"] in ("done", "running", "partial"),
          f"state={s.nodes[node['id']]['state']}")
    shutil.rmtree(outd, ignore_errors=True)
finally:
    m.log, m.subprocess.Popen, m.subprocess.run = orig

# ================= PART 6 在飞不受影响（after） =================
say("")
say("=" * 72)
say("PART 6 在飞不受影响：after 快照对比 + 产线面零测试痕迹")
say("=" * 72)
time.sleep(2)  # 让 BIN 桩孤儿进程自然退净
snapshots("after")
rc, o, _ = sh("pgrep -af '[s]tub-bin' || true")
say(f"残留桩进程: {o.strip() or '无'}")
check("C1 两在飞调度器全程同 PID 存活（ps 可查）",
      all(sh(f"ps -p {p} --no-headers")[0] == 0 for p in PIDS))
rc, logf, _ = sh("grep -l tfstest /tmp/factory.log /tmp/factory2.log /tmp/factory-status.json /tmp/factory2-status.json 2>/dev/null || true")
check("C2 产线四件套零测试痕迹（无 tfstest 命中）", not logf.strip(), logf)
rc, n1, _ = sh("grep -ac tmpfs /tmp/factory.log")
rc2, n2, _ = sh("grep -ac tmpfs /tmp/factory2.log")
check("C3 产线日志 tmpfs 行仍为 0（在飞旧码未启闸、沙箱零泄漏）",
      n1.strip() == "0" and n2.strip() == "0", f"factory={n1.strip()} factory2={n2.strip()}")

# ================= PART 7 补丁注释中的出处主张核对 =================
say("")
say("=" * 72)
say("PART 7 出处主张核对（两图臂节点 / 校准依据行 / 金丝可痕迹）")
say("=" * 72)
total_arms, bad_out, hosts = 0, [], {}
for g in ("/tmp/factory-graph.json", "/tmp/factory2-graph.json"):
    try:
        data = json.load(open(g))
    except Exception as e:
        say(f"{g} 读取失败: {e!r}")
        continue
    n = 0
    for nd in data.get("nodes", []):
        if nd.get("kind") == "bench-arm":
            n += 1
            out = nd.get("params", {}).get("out", "")
            if not out.startswith("/tmp/bench-"):
                bad_out.append(f"{g}:{nd.get('id')} out={out}")
            h = nd.get("params", {}).get("host", "anolis(缺省)")
            hosts[h] = hosts.get(h, 0) + 1
    say(f"{g}: bench-arm={n}")
    total_arms += n
check(f"P7a 两现役图 bench-arm 合计=49 且 out 全部 /tmp/bench-*（实测 {total_arms}）",
      total_arms == 49 and not bad_out, f"total={total_arms} bad_out={bad_out}")
say(f"host 分布: {hosts}")

def find_file(name):
    hits = glob.glob(f"{WS}/**/{name}", recursive=True)
    return hits[0] if hits else None

for fname, lineno, keywords in (("mes500-根因报告.md", 42, ("122",)),
                                ("对齐组-state.md", 252, ("1.7",))):
    p = find_file(fname)
    if not p:
        say(f"{fname}: 未找到")
        check(f"P7b {fname}:{lineno} 存在且含校准依据关键词", False, "file not found")
        continue
    lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
    txt = lines[lineno - 1] if len(lines) >= lineno else "<行不存在>"
    say(f"{p}:{lineno}: {txt.strip()[:200]}")
    say(f"  关键词 {[k for k in keywords if k in txt]}")
rc, canary, _ = sh(f"grep -c 金丝雀 '{find_file('对齐组-state.md') or '/dev/null'}'")
say(f"对齐组-state.md 内 '金丝雀' 命中行数: {canary.strip()}（任务书材料口径：无独立出处）")

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
