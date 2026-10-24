#!/usr/bin/env python3
"""patch4-test-tmpfs.py — 补丁「patch-tmpfs-gate-sched-R2」作者套件。

被测对象：tools/factory-sched.py 的 tmpfs 闸（D-24）。
纪律：全部零生产副作用——不 spawn 任何 af-bench/ssh（Popen 打桩即炸）、不写生产
MES（node_event/ch_insert 打桩记录）、--once 横幅测试用沙箱三件套
（AF_SCHED_GRAPH/STATUS/LOG 全指向测试目录，空图零节点零派发）。
跑法：python3 补丁/patch4-test-tmpfs.py   （期望末行 ALL PASS (N/N)，rc=0）
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

WS = "/home/pan-ding/workspace/agent黑灯工厂"
TARGET = f"{WS}/tools/factory-sched.py"
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"{'PASS' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not cond else ""))


def load_mod(extra_env=None):
    """按当前 env + extra_env 全新加载模块（常量在 import 期定型，故每场景重载）。"""
    env_backup = {k: os.environ.pop(k, None) for k in
                  ("FACTORY_SCHED_TMPFS_WARN_MB", "FACTORY_SCHED_TMPFS_MIN_MB")}
    try:
        for k, v in (extra_env or {}).items():
            os.environ[k] = v
        spec = importlib.util.spec_from_file_location("fst_under_test", TARGET)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        for k, v in env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return mod


def fresh_sched(mod):
    """绕过 Sched.__init__（它读生产图）；tmpfs_gate/launch 只用实例属性，__new__ 足够。"""
    return mod.Sched.__new__(mod.Sched)


def arm_node(nid="arm-test", host=None, tasks=("t1",), out=None):
    p = {"profile": "glm-cp", "tasks": list(tasks), "out": out or "/tmp/patch4-test-out", "tier": ""}
    if host is not None:
        p["host"] = host
    return {"id": nid, "kind": "bench-arm", "params": p, "deps": []}


class Rig:
    """launch() 测试台：打桩 log/Popen/node_event/subprocess.run，隔离生产面。
    run 只放行 mem_gate 的只读 meminfo 读取（喂假高水位读数，避免真 ssh anolis）；
    其余任何 run/Popen 一律炸出。"""

    MEMINFO_CMD = ["ssh", "-o", "ConnectTimeout=10", "anolis", "cat", "/proc/meminfo"]

    def __init__(self, mod):
        self.mod = mod
        self.logs = []
        self.popen_calls = []
        self.run_calls = []
        self.events = []
        self._orig = (mod.log, mod.node_event, mod.subprocess.Popen, mod.subprocess.run)
        mod.log = self.logs.append
        mod.node_event = lambda *a, **k: self.events.append((a, k))
        mod.subprocess.Popen = \
            lambda *a, **k: (_ for _ in ()).throw(AssertionError(f"Popen 被调用: {a}"))

        def fake_run(cmd, *a, **k):
            self.run_calls.append(cmd)
            if list(cmd) == self.MEMINFO_CMD:
                class R:  # anolis 内存高水位假读数（MemAvailable 999999999 kB）
                    stdout = "MemTotal: 999999999 kB\nMemAvailable: 999999999 kB\n"
                return R()
            raise AssertionError(f"越权 subprocess.run 被调用: {cmd}")

        mod.subprocess.run = fake_run

    def close(self):
        (self.mod.log, self.mod.node_event,
         self.mod.subprocess.Popen, self.mod.subprocess.run) = self._orig

    def tmp_logs(self):
        return [l for l in self.logs if "tmpfs" in l]


# ---------- S1 阈值常量与 env 覆盖 ----------
m = load_mod()
check("S1a 默认阈值 2663/2253（≈2.6/2.2GiB 向上取整）",
      m.TMPFS_WARN_MB == 2663 and m.TMPFS_MIN_MB == 2253,
      f"got {m.TMPFS_WARN_MB}/{m.TMPFS_MIN_MB}")
m = load_mod({"FACTORY_SCHED_TMPFS_WARN_MB": "3000", "FACTORY_SCHED_TMPFS_MIN_MB": "2500"})
check("S1b env 覆盖生效（MiB）", m.TMPFS_WARN_MB == 3000 and m.TMPFS_MIN_MB == 2500)
m = load_mod({"FACTORY_SCHED_TMPFS_WARN_MB": "abc", "FACTORY_SCHED_TMPFS_MIN_MB": ""})
check("S1c 非法/空 env 回退默认", m.TMPFS_WARN_MB == 2663 and m.TMPFS_MIN_MB == 2253)

# ---------- S2 真实 statvfs 读数与 df 互证（当前 /tmp 高位，应开闸） ----------
m = load_mod()
s = fresh_sched(m)
ok, avail = s.tmpfs_gate()
df_kib = int(subprocess.run(["df", "-P", "/tmp"], capture_output=True, text=True)
             .stdout.splitlines()[-1].split()[3])
df_mib = df_kib // 1024
check("S2a 真实读数开闸且与 df 同量级（±200MiB 容生产写入漂移）",
      ok is True and avail > 0 and abs(avail - df_mib) <= 200,
      f"gate={ok}/{avail}MiB df={df_mib}MiB")

# ---------- S3 盘点失败 fail-closed（-1 口径） ----------
m = load_mod()
real_statvfs = os.statvfs
try:
    def boom(path):
        raise OSError("mock statvfs failure")
    os.statvfs = boom
    s = fresh_sched(m)
    ok, avail = s.tmpfs_gate()
finally:
    os.statvfs = real_statvfs
check("S3 statvfs 异常 → (False, -1) fail-closed", ok is False and avail == -1,
      f"got {ok}/{avail}")

# ---------- S4 关闭线拦全体 host（默认/local/mingda-bench），在跑臂不杀 ----------
for host in (None, "local", "mingda-bench"):
    m = load_mod({"FACTORY_SCHED_TMPFS_MIN_MB": "999999", "FACTORY_SCHED_TMPFS_WARN_MB": "9999999"})
    rig = Rig(m)
    try:
        s = fresh_sched(m)
        s.nodes = {}
        node = arm_node(host=host)
        s.nodes[node["id"]] = {**node, "state": "pending", "note": ""}
        s.launch(node)
        blocked = s.nodes[node["id"]]["state"] == "pending" and not rig.events
        s.launch(node)  # 第二轮：去重，不重复报
        n_lines = sum("暂停派臂" in l for l in rig.tmp_logs())
        check(f"S4 host={host or '缺省(anolis)'} 关闭线拦截+不终态+不派发+去重(1行)",
              blocked and n_lines == 1 and not rig.popen_calls,
              f"state={s.nodes[node['id']]['state']} lines={n_lines}")
    finally:
        rig.close()

# ---------- S5 关闭线文案区分盘点失败 ----------
m = load_mod({"FACTORY_SCHED_TMPFS_MIN_MB": "999999"})
rig = Rig(m)
try:
    s = fresh_sched(m)
    node = arm_node()
    s.nodes = {node["id"]: {**node, "state": "pending", "note": ""}}
    s.launch(node)
    check("S5 拦截行带确定读数（非盘点失败文案）",
          any(f"< 关闭线 999999MiB" in l for l in rig.tmp_logs()))
finally:
    rig.close()

# ---------- S6 预警带：放行 + 去重 + 解除行 ----------
m = load_mod({"FACTORY_SCHED_TMPFS_WARN_MB": "999999"})  # 当前余量必落预警带
rig = Rig(m)
try:
    s = fresh_sched(m)
    out = tempfile.mkdtemp(prefix="patch4-warn-")
    with open(os.path.join(out, "results.jsonl"), "w") as f:
        f.write(json.dumps({"task_id": "t1", "status": "completed"}) + "\n")
    node = arm_node(out=out)  # 任务全结论 → 过闸后走"无需续跑"，不触 Popen
    s.nodes = {node["id"]: {**node, "state": "pending", "note": ""}}
    s.launch(node)
    passed = s.nodes[node["id"]]["state"] == "done" and not rig.popen_calls
    s.launch(node)
    warns = sum("预警" in l for l in rig.tmp_logs())
    check("S6a 预警带放行（到达派发逻辑）+去重(1行)+零越权子进程",
          passed and warns == 1
          and all(list(c) == Rig.MEMINFO_CMD for c in rig.run_calls),
          f"state={s.nodes[node['id']]['state']} warns={warns} runs={rig.run_calls}")
    m.TMPFS_WARN_MB = 1  # 模拟恢复到预警线以上（launch 运行期读模块全局）
    s.nodes[node["id"]].update(state="pending", note="")
    s.launch(node)
    reliefs = sum("解除" in l for l in rig.tmp_logs())
    check("S6b 恢复后补一行解除行", reliefs == 1, f"reliefs={reliefs}")
    shutil.rmtree(out, ignore_errors=True)
finally:
    rig.close()

# ---------- S7 关闭→恢复：解除行只补一次 ----------
m = load_mod({"FACTORY_SCHED_TMPFS_MIN_MB": "999999", "FACTORY_SCHED_TMPFS_WARN_MB": "9999999"})
rig = Rig(m)
try:
    s = fresh_sched(m)
    out = tempfile.mkdtemp(prefix="patch4-close-")
    with open(os.path.join(out, "results.jsonl"), "w") as f:
        f.write(json.dumps({"task_id": "t1", "status": "completed"}) + "\n")
    node = arm_node(out=out)
    s.nodes = {node["id"]: {**node, "state": "pending", "note": ""}}
    s.launch(node)  # 关闭，记 closed
    m.TMPFS_MIN_MB = 1  # 模拟 /tmp 回落恢复
    m.TMPFS_WARN_MB = 1
    s._tmpfs_at = 0  # 跳过 60s 缓存（真实场景即缓存自然过期）
    s.launch(node)
    reliefs = sum("解除" in l for l in rig.tmp_logs())
    reopened = s.nodes[node["id"]]["state"] == "done"
    s._tmpfs_at = 0
    s.launch(node)
    check("S7 关闭→恢复解除行 1 次且恢复派发", reopened and reliefs == 1
          and sum("解除" in l for l in rig.tmp_logs()) == 1)
    shutil.rmtree(out, ignore_errors=True)
finally:
    rig.close()

# ---------- S8 60s 缓存（60s 内第二次不重读 statvfs） ----------
m = load_mod()
calls = []
real_statvfs = os.statvfs
try:
    os.statvfs = lambda p: (calls.append(p), real_statvfs(p))[1]
    s = fresh_sched(m)
    s.tmpfs_gate()
    r1 = s.tmpfs_gate()
finally:
    os.statvfs = real_statvfs
check("S8 缓存窗内 statvfs 只读一次", len(calls) == 1, f"calls={len(calls)}")

# ---------- S9 启动横幅（--once + 沙箱三件套，零生产面） ----------
sb = tempfile.mkdtemp(prefix="patch4-sandbox-")
graph = os.path.join(sb, "g.json")
with open(graph, "w") as f:
    json.dump({"nodes": [], "limits": {}}, f)
base_env = dict(os.environ, AF_SCHED_GRAPH=graph,
                AF_SCHED_STATUS=os.path.join(sb, "st.json"),
                AF_SCHED_LOG=os.path.join(sb, "sched.log"))
r = subprocess.run([sys.executable, f"{WS}/tools/factory-sched.py", "--once"],
                   env=base_env, capture_output=True, text=True, timeout=60, cwd=WS)
banner_ok = r.returncode == 0 and os.path.exists(
    os.path.join(sb, "sched.log"))
line = ""
if banner_ok:
    line = [l for l in open(os.path.join(sb, "sched.log")) if "tmpfs 闸生效" in l]
    line = line[-1].strip() if line else ""
check("S9a 启动横幅印默认阈值（2253/2663）且 --once 干净退出",
      banner_ok and "<2253MiB" in line and "<2663MiB" in line, line)
env2 = dict(base_env, FACTORY_SCHED_TMPFS_WARN_MB="3000", FACTORY_SCHED_TMPFS_MIN_MB="2500")
r2 = subprocess.run([sys.executable, f"{WS}/tools/factory-sched.py", "--once"],
                    env=env2, capture_output=True, text=True, timeout=60, cwd=WS)
line2 = ""
for l in open(os.path.join(sb, "sched.log")):
    if "tmpfs 闸生效" in l:
        line2 = l.strip()
check("S9b 横幅印 env 覆盖后生效值（2500/3000）",
      r2.returncode == 0 and "<2500MiB" in line2 and "<3000MiB" in line2, line2)
shutil.rmtree(sb, ignore_errors=True)

# ---------- S10 存档可重放性（沙箱正放 = 现役文件逐字节一致；回滚 dry-run 响亮通过） ----------
rb = tempfile.mkdtemp(prefix="patch4-replay-")
os.makedirs(os.path.join(rb, "tools"))
shutil.copy(f"{WS}/工具状态备份/factory-sched.py.pre-tmpfs-gate-R2",
            os.path.join(rb, "tools/factory-sched.py"))
p1 = subprocess.run(["patch", "-d", rb, "-p1", "--dry-run"],
                    stdin=open(f"{WS}/补丁/tmpfs闸-sched-R2.patch"), capture_output=True, text=True)
p2 = subprocess.run(["patch", "-d", rb, "-p1"],
                    stdin=open(f"{WS}/补丁/tmpfs闸-sched-R2.patch"), capture_output=True, text=True)
same = open(os.path.join(rb, "tools/factory-sched.py"), "rb").read() == \
    open(f"{WS}/tools/factory-sched.py", "rb").read()
check("S10a 补丁在基线上正放 dry-run+实放均 rc=0 且结果与现役文件逐字节一致",
      p1.returncode == 0 and p2.returncode == 0 and same)
p3 = subprocess.run(["patch", "-p1", "-R", "--dry-run", "--forward"],
                    stdin=open(f"{WS}/补丁/tmpfs闸-sched-R2.patch"), capture_output=True,
                    text=True, cwd=WS)
check("S10b 回滚命令 dry-run（patch -p1 -R --forward）在工作区 rc=0",
      p3.returncode == 0, p3.stdout[-300:] + p3.stderr[-300:])
shutil.rmtree(rb, ignore_errors=True)

# ---------- 汇总 ----------
n, total = len(PASS), len(PASS) + len(FAIL)
print(f"\n{total - n} FAILED, {n} passed" if FAIL else "")
print(f"ALL PASS ({n}/{total})")
sys.exit(1 if FAIL else 0)
