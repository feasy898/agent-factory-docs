#!/usr/bin/env python3
"""factory-sched.py — 黑灯工厂评测调度器（图结构，MES 记账）。

定位：主代理=下单人（提交/修订战役图），本脚本=工厂执行面——按依赖图并发跑节点，
      每个节点生命周期与结果都入 MES。替代主代理一臂一臂手工拉。

节点类型:
  relay-image {image}              → tools/cnb-relay.py once（幂等；启动前过磁盘闸）
  bench-arm   {profile, tasks, out, host?} → af-bench（断点续跑：只传未完成题；
              host 缺省 anolis，local 时 --host local 本机 docker 直执行；
              同 (tier,profile) 跨主机 done 并集去重，防两主机重复烧 API）
  token-gate  {probe}              → mcode 探活（ok 才放行依赖它的臂）

用法:
  factory-sched.py --init          # 依据样本+既有 results 生成 /tmp/factory-graph.json
  factory-sched.py                 # 常驻调度（每 5s 一轮；图文件热更新，新节点自动接入）
状态: /tmp/factory-status.json；日志 /tmp/factory.log
      （均可用 AF_SCHED_STATUS / AF_SCHED_LOG 覆盖；图 AF_SCHED_GRAPH、二进制 BIN 同理，
      供第二条实验产线并存——两调度器实例各用各的三件套与二进制代）
纪律: 密钥零明文（cnb-relay 内部走 openBao 管道）；失败如实登记不编造；
      全部子进程 stdin=DEVNULL（子进程不得继承调度器 stdin——2026-10-20 教训）。
"""
import argparse
import base64
import glob
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

WS = "/home/pan-ding/workspace/agent黑灯工厂"
AF = f"{WS}/af"
# 四路径参数化（技术债 D-2 部分归还）：环境变量可覆盖，缺省=主产线现值（主产线零影响）。
# 第二条实验产线（如 fix2 对照重跑）用 AF_SCHED_GRAPH/AF_SCHED_STATUS/AF_SCHED_LOG 三件套
# + BIN=独立代际二进制 启动独立调度器实例，与主产线并存（§9.3 结果代际隔离：
# 一个调度器实例只写自己的图/状态/日志/out，二进制代与结果目录代严格配对）。
BIN = os.environ.get("BIN", f"{AF}/target/debug/af-bench")
GRAPH = os.environ.get("AF_SCHED_GRAPH", "/tmp/factory-graph.json")
STATUS = os.environ.get("AF_SCHED_STATUS", "/tmp/factory-status.json")
LOG = os.environ.get("AF_SCHED_LOG", "/tmp/factory.log")


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
# 中继 org 必须全小写（docker 仓库名规范）。Cloudbird-Software 的 org 用小写别名
# cloudbird-software：CNB 注册表/API 大小写不敏感（2026-10-20 probe sn=cnb-hos-1k5c5na5h
# 实证 lowercase crane copy 与 manifest 拉取均通），两 org 独立配额（各 160 核时/月免费）。
# 注意：本常量在调度器进程内——文件改动对运行中的调度器不热生效，下次重启调度器起交替。
RELAY_ORGS = ["zhuzhu-team", "cloudbird-software"]

# per-plan 并发上限（运营者指令：吃满 anolis 65% 空闲核；额度非约束，速率限制试点后调）
PROFILE_LIMITS = {
    "glm-cp": 4, "glm-cp-max": 4, "kimi-k3": 4, "step-5": 3,
    "qwen30b-local": 2, "qwen3-8b-anolis": 2, "mavis-m31f": 4,
}
RELAY_LIMIT = 6
BENCH_LIMIT = 24
# per-host 并发上限（2026-10-20 本机臂接入）：anolis 承载力实测充裕，本机容器内存峰值
# ~889MiB/题、判分 CPU 突发 1-5 核，3 臂是本机稳态上限（后台还驻留 fast-pull/补给循环）。
HOST_LIMITS = {"anolis": 14, "local": 3}
# 磁盘闸：relay 前查 anolis /data 使用率，超线则本轮不启动 relay（防镜像塞满盘）。
DISK_GATE_PCT = 88
# 内存闸：anolis available 内存 <15G 时 fail-closed 暂派新 bench-arm（在跑任务不杀，
# 恢复后自动放行）。2026-10-21 事故口径：测评容器无内存上限+无 swap，整机耗尽假死、
# 运营者硬重启两次——容器上限在 af-bench 侧（--memory/--pids-limit），调度器侧再加
# 一道"机器快死了就别派新臂"的总闸；relay 走磁盘闸（拉镜像吃盘不吃内存），不受本闸管。
MEM_GATE_AVAIL_GIB = 15
# bench-arm 无有效行的连续失败上限：达到即终态 failed（需人工），防死循环烧 API。
FAIL_LIMIT = 3

# tmpfs 闸阈值（D-24 结果目录 tmpfs，2026-10-22 补丁 R2）：所有 bench-arm 的 out 都落
# 本机 /tmp（tmpfs 7.5G，与产线数据/研究构建产物共居，host 无关——factory/factory2 两图
# 49 个臂节点 out 全部 /tmp/bench-*）。校准依据：10-21 晚 /tmp（tmpfs+usrquota）配额
# 耗尽 EDQUOT(Errno 122)、main-sched 被杀，实测发生于仅余 ~1.7G 时（mes500-根因报告.md:42
# + 对齐组-state.md:252）；本轮 64M-1G 金丝雀臂在余量 3.07G 时全部通过 → 校准
# WARN=2.6GiB / CLOSE=2.2GiB（换算 MiB 向上取整，取保守侧）。env 覆盖单位 MiB（整数），
# 非法值静默回退默认（启动横幅会印出生效值，可发现覆盖没生效）。
def _tmpfs_env_mb(key, default_mb):
    try:
        return max(0, int((os.environ.get(key) or "").strip() or default_mb))
    except ValueError:
        return default_mb

TMPFS_WARN_MB = _tmpfs_env_mb("FACTORY_SCHED_TMPFS_WARN_MB", 2663)  # ≈2.6GiB 预警线
TMPFS_MIN_MB = _tmpfs_env_mb("FACTORY_SCHED_TMPFS_MIN_MB", 2253)    # ≈2.2GiB 关闭线（fail-closed）

SAMPLE = f"{WS}/计划/s1-swev-120.json"

# 既有结果目录（append 续跑，避免重复行；命名不一致故显式映射）
# fix1 = 2026-10-20 harness 根因修复（max_tokens 1024→8192 + tool_free 3 + 完成信号）后的第一代。
# 修复前的 bench-s1-* 目录全部作废（MES line_id=bench-void），不再作为 done 来源。
EXISTING_DIRS = {
    ("D1", "glm-cp"): "/tmp/bench-fix1-d1-glm-cp",
    ("D1", "glm-cp-max"): "/tmp/bench-fix1-d1-glm-max",
    ("D1", "kimi-k3"): "/tmp/bench-fix1-d1-kimi",
    ("D1", "step-5"): "/tmp/bench-fix1-d1-step5",
    ("D1", "qwen30b-local"): "/tmp/bench-fix1-d1-30b",
    ("D1", "mavis-m31f"): "/tmp/bench-fix1-d1-m31f",
    ("D2", "glm-cp"): "/tmp/bench-fix1-d2-glm-cp",
    ("D2", "glm-cp-max"): "/tmp/bench-fix1-d2-glm-max",
    ("D2", "kimi-k3"): "/tmp/bench-fix1-d2-kimi",
    ("D2", "step-5"): "/tmp/bench-fix1-d2-step5",
    ("D2", "qwen30b-local"): "/tmp/bench-fix1-d2-30b",
    ("D2", "mavis-m31f"): "/tmp/bench-fix1-d2-m31f",
    ("D3", "glm-cp"): "/tmp/bench-fix1-d3-glm-cp",
    ("D3", "glm-cp-max"): "/tmp/bench-fix1-d3-glm-max",
    ("D3", "kimi-k3"): "/tmp/bench-fix1-d3-kimi",
    ("D3", "step-5"): "/tmp/bench-fix1-d3-step5",
    ("D3", "qwen30b-local"): "/tmp/bench-fix1-d3-30b",
    ("D3", "mavis-m31f"): "/tmp/bench-fix1-d3-m31f",
}


def log(msg):
    line = f"[{time.strftime('%F %T')}] {msg}"
    # stdout 被重定向到 LOG 本身时只走 stdout，避免文件里同一行出现两遍
    duplicated = False
    try:
        duplicated = os.path.realpath("/proc/self/fd/1") == os.path.realpath(LOG)
    except OSError:
        pass
    print(line, flush=True)
    if not duplicated:
        with open(LOG, "a") as f:
            f.write(line + "\n")


# ---------- MES ----------

def ch_insert(events):
    if not events:
        return
    body = "".join(
        json.dumps({
            "work_order_id": e["work_order_id"],
            "occurred_at": time.strftime("%F %T"),
            "event_id": e["event_id"],
            "line_id": e.get("line_id", "bench"),
            "station_id": e.get("station_id", "factory"),
            "kind": e["kind"],
            "quantity": e.get("quantity", 0),
        }, ensure_ascii=False) + "\n"
        for e in events
    )
    req = urllib.request.Request(
        CH + "/?query=" + urllib.parse.quote(
            "INSERT INTO af_mes.mes_event (work_order_id, occurred_at, event_id, line_id, station_id, kind, quantity) FORMAT JSONEachRow"
        ),
        data=body.encode(), method="POST",
    )
    if CH_AUTH:
        req.add_header("Authorization", CH_AUTH)
    # MES 500 根因修复（2026-10-22 修理组）：CH 在宿主内存压力下间歇 500
    # （服务端 code 241，动态硬限额塌陷）→ 旧逻辑单次失败即静默丢事件。
    # 改为有限重试（2s/8s 退避）；仍失败保留原"不致命"语义但日志带次数。
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                r.read()
            return
        except urllib.error.HTTPError as e:
            last = e
            if e.code < 500 or attempt == 2:
                break
        except urllib.error.URLError as e:
            last = e
            if attempt == 2:
                break
        time.sleep((2, 8)[attempt])
    log(f"MES 写入失败（不致命，已重试 3 次）: {last}")


def node_event(node_id, kind, quantity=0):
    ch_insert([{
        "work_order_id": f"factory-{node_id}",
        "station_id": "factory",
        "line_id": "bench",
        "kind": kind,
        "quantity": quantity,
        "event_id": f"factory-{node_id}-{kind}",
    }])


# ---------- 图生成 ----------

def done_tasks(out_dir):
    """results.jsonl 里已有结论的题（run_failed 算未完成，可重试）。"""
    done = set()
    path = os.path.join(out_dir, "results.jsonl")
    if not os.path.exists(path):
        return done
    for line in open(path, encoding="utf-8"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("status") and r["status"] not in ("run_failed", "setup_failed"):
            done.add(r.get("task_id") or r.get("case_id"))
    return done


def local_out(tier, prof):
    """本机臂 out 目录（与 anolis 臂物理隔离；分析层合并时按 (task,profile) 去重保首个）。"""
    return f"/tmp/bench-fix1-{tier.lower()}-{prof}-local"


def done_union(tier, prof):
    """同 (tier,profile) 的已结论题并集（anolis 目录 + local 目录）。
    两主机各自有同一题的结论即视为完成，臂只跑并集外的题——防两主机重复烧 API。"""
    done = set()
    anolis_dir = EXISTING_DIRS.get((tier, prof))
    if anolis_dir:
        done |= done_tasks(anolis_dir)
    done |= done_tasks(local_out(tier, prof))
    return done


def init_graph():
    sample = json.load(open(SAMPLE))
    tiers = {"D1": [], "D2": [], "D3": []}
    for t in sample:
        tiers[t["tier"]].append(t["instance_id"])

    # 已在 anolis 的镜像 → 不建 relay 节点
    have = set()
    try:
        out = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "anolis",
                              "docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
                             capture_output=True, text=True, timeout=60,
                             stdin=subprocess.DEVNULL).stdout
        for line in out.splitlines():
            if "sweb.eval" in line:
                have.add(line.split(":")[0].split("/")[-1])
    except Exception as e:
        log(f"anolis 镜像盘点失败（按全新处理）: {e}")

    def img_name(inst):
        repo = inst.split("__")[0]
        return f"swebench/sweb.eval.x86_64.{repo.replace('/', '_1776_')}_1776_{inst.split('__')[1]}:latest"

    nodes = []
    relay_ids = {"D1": [], "D2": [], "D3": []}
    for tier, insts in tiers.items():
        for inst in insts:
            img = img_name(inst)
            full = img.split("/")[-1].split(":")[0]
            if full in have:
                continue
            nid = f"relay-{full.split('_1776_')[-1]}"
            nodes.append({"id": nid, "kind": "relay-image", "params": {"image": img}, "deps": []})
            relay_ids[tier].append(nid)

    # mcode 令牌门禁（m31f 臂的公共前置）
    nodes.append({"id": "gate-mcode-token", "kind": "token-gate", "params": {}, "deps": []})

    profiles = ["glm-cp", "glm-cp-max", "kimi-k3", "step-5", "qwen30b-local", "mavis-m31f"]
    for tier, insts in tiers.items():
        avail = [i for i in insts
                 if img_name(i).split("/")[-1].split(":")[0] in have]
        for prof in profiles:
            out_dir = EXISTING_DIRS[(tier, prof)]
            done = done_tasks(out_dir)
            # wave1：镜像已就位、还没跑过的题——不等中继，立即开跑
            w1 = [i for i in avail if i not in done]
            w1_id = f"arm-{tier.lower()}-{prof}-w1"
            if w1:
                deps = ["gate-mcode-token"] if prof == "mavis-m31f" else []
                nodes.append({
                    "id": w1_id, "kind": "bench-arm",
                    "params": {"profile": prof, "tasks": w1, "out": out_dir, "tier": tier},
                    "deps": deps,
                })
            else:
                w1_id = None
            remaining = [i for i in insts if i not in done]
            if not remaining:
                continue
            deps = list(relay_ids[tier])
            if w1_id:
                deps.append(w1_id)  # 全量臂等 wave1 跑完，避免并发写同一 results.jsonl
            if prof == "mavis-m31f":
                deps.append("gate-mcode-token")
            nodes.append({
                "id": f"arm-{tier.lower()}-{prof}",
                "kind": "bench-arm",
                "params": {"profile": prof, "tasks": remaining, "out": out_dir, "tier": tier},
                "deps": deps,
            })
    graph = {"nodes": nodes, "limits": {
        "profile": PROFILE_LIMITS, "relay": RELAY_LIMIT, "bench": BENCH_LIMIT,
    }}
    with open(GRAPH, "w") as f:
        json.dump(graph, f, ensure_ascii=False, indent=1)
    n_relay = sum(1 for n in nodes if n["kind"] == "relay-image")
    n_arm = sum(1 for n in nodes if n["kind"] == "bench-arm")
    log(f"图已生成: {n_relay} relay + {n_arm} bench + 1 gate → {GRAPH}")


# ---------- 调度 ----------

class Sched:
    def __init__(self):
        self.nodes = {}
        self.order = []
        self.running = {}   # nid -> Popen
        self.started = {}   # nid -> ts
        self.limits = {"profile": PROFILE_LIMITS, "relay": RELAY_LIMIT, "bench": BENCH_LIMIT,
                       "host": HOST_LIMITS}
        self.load_graph(initial=True)

    def load_graph(self, initial=False):
        try:
            graph = json.load(open(GRAPH))
        except Exception as e:
            log(f"图读取失败: {e}")
            return
        # 并发上限热加载（改图文件即生效，无需重启调度器）
        lim = graph.get("limits") or {}
        self.limits = {
            "profile": lim.get("profile", PROFILE_LIMITS),
            "relay": lim.get("relay", RELAY_LIMIT),
            "bench": lim.get("bench", BENCH_LIMIT),
            "host": lim.get("host", HOST_LIMITS),
        }
        for n in graph["nodes"]:
            if n["id"] not in self.nodes:
                self.nodes[n["id"]] = {**n, "state": "pending", "note": ""}
                self.order.append(n["id"])
                if not initial:
                    log(f"新节点接入: {n['id']}")
            else:
                # 热更新定义（deps/params），保留运行状态
                self.nodes[n["id"]]["deps"] = n.get("deps", [])
                self.nodes[n["id"]]["params"] = n.get("params", {})

    def deps_done(self, node):
        return all(self.nodes[d]["state"] in ("done", "skipped")
                   for d in node["deps"] if d in self.nodes)

    def capacity(self, node):
        prof = node["params"].get("profile", "")
        if node["kind"] == "relay-image":
            n_relay = sum(1 for nid in self.running
                          if self.nodes[nid]["kind"] == "relay-image")
            return n_relay < self.limits["relay"]
        # profile 上限按主机各算（anolis 数值不变）：否则 anolis 臂占满共享配额，
        # 本机臂永远饿死——与 per-host 上限的资源语义一致。总量仍由 bench 与 host 上限兜底。
        host = node["params"].get("host", "anolis")
        n_prof = sum(1 for nid in self.running
                     if self.nodes[nid]["params"].get("profile") == prof
                     and self.nodes[nid]["params"].get("host", "anolis") == host)
        n_bench = sum(1 for nid in self.running
                      if self.nodes[nid]["kind"] == "bench-arm")
        n_host = sum(1 for nid in self.running
                     if self.nodes[nid]["kind"] == "bench-arm"
                     and self.nodes[nid]["params"].get("host", "anolis") == host)
        return (n_prof < self.limits["profile"].get(prof, 1)) and (n_bench < self.limits["bench"]) \
            and (n_host < self.limits["host"].get(host, 3))

    def disk_gate(self):
        """磁盘闸：anolis /data 使用率 >88% 时暂停 relay 启动。结果缓存 120s 防 ssh 风暴；
        盘点异常/无读数按 fail-closed 暂停（2026-10-20 22:21 教训：ssh 闪断时旧逻辑放行，
        6 个 relay 齐发后全部死在 ssh load，白拉 1.5GB×N）——ssh 不通时 relay 本身必败，
        闸关闭只是把失败提前到秒级。"""
        now = time.time()
        if now - getattr(self, "_gate_at", 0) < 120:
            return getattr(self, "_gate_ok", True), getattr(self, "_gate_pct", -1)
        self._gate_at = now
        self._gate_ok = False  # fail-closed：只有拿到确定读数且未超线才放行
        self._gate_pct = -1
        try:
            r = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "anolis",
                                "df", "--output=pcent", "/data"],
                               capture_output=True, text=True, timeout=60,
                               stdin=subprocess.DEVNULL)
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip().endswith("%")]
            if lines:
                pct = int(lines[-1].rstrip("%"))
                self._gate_pct = pct
                self._gate_ok = pct <= DISK_GATE_PCT
        except Exception:
            pass
        return self._gate_ok, self._gate_pct

    def mem_gate(self):
        """内存闸：anolis available 内存 <15G 时 fail-closed 暂派新 bench-arm。
        与磁盘闸同构：60s 缓存防 ssh 风暴；ssh 抖动/无读数按 fail-closed 暂停。
        只暂不杀：杀在跑任务=丢在途判分结果，暂停派新让内存随任务结束自然回落。"""
        now = time.time()
        if now - getattr(self, "_mem_at", 0) < 60:
            return getattr(self, "_mem_ok", True), getattr(self, "_mem_avail", -1)
        self._mem_at = now
        self._mem_ok = False  # fail-closed：只有拿到确定读数且高于阈值才放行
        self._mem_avail = -1
        try:
            # 取 /proc/meminfo 全文本地解析（不要把 awk 程序经 ssh 传远端——
            # ssh 会把多参数拼成一条远端 shell 命令，括号触发语法错误，2026-10-21
            # 实测教训：那样内存门会永远 fail-closed，重启调度器后全厂停派）。
            r = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "anolis",
                                "cat", "/proc/meminfo"],
                               capture_output=True, text=True, timeout=60,
                               stdin=subprocess.DEVNULL)
            for line in r.stdout.splitlines():
                if line.startswith("MemAvailable:"):
                    kb = int(line.split()[1])
                    self._mem_avail = kb // 1048576  # kB→GiB（向下取整，同 awk int() 口径）
                    self._mem_ok = self._mem_avail >= MEM_GATE_AVAIL_GIB
                    break
        except Exception:
            pass
        return self._mem_ok, self._mem_avail

    def tmpfs_gate(self):
        """tmpfs 闸：本机 /tmp 可用 <TMPFS_MIN_MB 时 fail-closed 暂派新 bench-arm。
        statvfs 本地读 f_bavail（绝不把盘点经 ssh 传远端）；盘点失败按 -1 口径
        fail-closed（同 disk_gate/mem_gate 的"判不准不放行"）。只拦新不杀旧：在跑臂
        的 out 写入不拦截，暂派让 /tmp 随任务收尾自然回落。<TMPFS_WARN_MB 为预警带：
        放行但记一次（_tmp_logged 去重，恢复≥预警线时补一行解除）。60s 缓存对齐两闸
        节奏。不限 host——所有臂 out 同在本机 /tmp（anolis 臂由 af-bench 在本机落
        results.jsonl），host=="local" 特判版是空操作（mingda-bench 等新 host 键同理
        全过本闸）。"""
        now = time.time()
        if now - getattr(self, "_tmpfs_at", 0) < 60:
            return getattr(self, "_tmpfs_ok", True), getattr(self, "_tmpfs_avail_mb", -1)
        self._tmpfs_at = now
        self._tmpfs_ok = False  # fail-closed：只有拿到确定读数且高于关闭线才放行
        self._tmpfs_avail_mb = -1
        try:
            st = os.statvfs("/tmp")
            self._tmpfs_avail_mb = st.f_bavail * st.f_frsize // 1048576
            self._tmpfs_ok = self._tmpfs_avail_mb >= TMPFS_MIN_MB
        except OSError:
            pass  # 维持 fail-closed 与 -1 口径
        return self._tmpfs_ok, self._tmpfs_avail_mb

    def launch(self, node):
        nid = node["id"]
        if node["kind"] == "relay-image":
            ok, pct = self.disk_gate()
            if not ok:
                if not getattr(self, "_gate_logged", False):
                    why = (f"anolis /data 使用率 {pct}% > {DISK_GATE_PCT}%" if pct >= 0
                           else "anolis /data 盘点失败（ssh 抖动?，fail-closed）")
                    log(f"磁盘闸暂停relay：{why}，本轮不启动 relay")
                    self._gate_logged = True
                return
            if getattr(self, "_gate_logged", False):
                self._gate_logged = False
                log(f"磁盘闸解除：anolis /data 使用率 {pct}%（恢复 relay 启动）")
            org = RELAY_ORGS[len(self.running) % len(RELAY_ORGS)]
            cmd = [sys.executable, f"{WS}/tools/cnb-relay.py", "once",
                   node["params"]["image"], "--org", org]
            cwd = WS
        elif node["kind"] == "bench-arm":
            # tmpfs 闸（D-24）：不限 host——所有臂 out 都落本机 /tmp。低于关闭线（或
            # 盘点失败）本轮不启动新臂；在跑臂不杀，恢复自动放行。
            ok, avail_mb = self.tmpfs_gate()
            if not ok:
                if getattr(self, "_tmp_logged", "") != "closed":
                    why = (f"/tmp 可用 {avail_mb}MiB < 关闭线 {TMPFS_MIN_MB}MiB" if avail_mb >= 0
                           else "/tmp 盘点失败（statvfs 异常，fail-closed）")
                    log(f"tmpfs 闸暂停派臂：{why}，本轮不启动新 bench-arm（在跑任务不杀，恢复自动放行）")
                    self._tmp_logged = "closed"
                return
            if avail_mb < TMPFS_WARN_MB:
                if getattr(self, "_tmp_logged", "") != "warn":
                    log(f"tmpfs 闸预警：/tmp 可用 {avail_mb}MiB < 预警线 {TMPFS_WARN_MB}MiB"
                        f"（继续派臂，逼近 fail-closed）")
                    self._tmp_logged = "warn"
            elif getattr(self, "_tmp_logged", ""):
                log(f"tmpfs 闸解除：/tmp 可用 {avail_mb}MiB ≥ 预警线 {TMPFS_WARN_MB}MiB（恢复常态）")
                self._tmp_logged = ""
            p = node["params"]
            host = p.get("host", "anolis")
            # 内存闸（只作用于 anolis 臂）：available <15G 暂不派新臂；在跑任务不杀，
            # 恢复自动放行。local 臂吃本机内存，由 HOST_LIMITS local=3 另行兜底。
            if host == "anolis":
                ok, avail = self.mem_gate()
                if not ok:
                    if not getattr(self, "_mem_logged", False):
                        why = (f"anolis available {avail}G < {MEM_GATE_AVAIL_GIB}G" if avail >= 0
                               else "anolis 内存盘点失败（ssh 抖动?，fail-closed）")
                        log(f"内存闸暂停派臂：{why}，本轮不启动新臂（在跑任务不杀，恢复自动放行）")
                        self._mem_logged = True
                    return
                if getattr(self, "_mem_logged", False):
                    self._mem_logged = False
                    log(f"内存闸解除：anolis available {avail}G ≥ {MEM_GATE_AVAIL_GIB}G（恢复派臂）")
            done = done_union(p.get("tier", ""), p["profile"]) | done_tasks(p["out"])
            remaining = [t for t in p["tasks"] if t not in done]
            if not remaining:
                self.nodes[nid]["state"] = "done"
                self.nodes[nid]["note"] = "无需续跑（跨主机并集均已结论）"
                node_event(nid, "done", len(p["tasks"]))
                return
            node["assigned"] = remaining  # 实跑口径（并集去重后），finish 按此记账
            cmd = [BIN, "--suite", "swe-v", "--data-root", "/tmp/swev-s1",
                   "--tasks", ",".join(remaining), "--profile", p["profile"],
                   "--out", p["out"], "--host", host]
            cwd = AF
        else:
            return
        try:
            proc = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        except Exception as e:
            if node["kind"] == "bench-arm":
                self.bench_arm_fail(nid, f"启动失败: {e}")
            else:
                self.nodes[nid]["state"] = "failed"
                self.nodes[nid]["note"] = f"启动失败: {e}"
                node_event(nid, "failed")
            return
        self.running[nid] = proc
        self.started[nid] = time.time()
        self.nodes[nid]["state"] = "running"
        node_event(nid, "started")
        log(f"启动 {nid}（{node['kind']} {node['params'].get('profile') or node['params'].get('image', '')}）pid={proc.pid}")

    def bench_arm_fail(self, nid, note):
        """bench-arm 失败（启动异常或整臂零有效行）：不终态，同 partial 的 10 分钟
        重排队机制让限流风暴自愈；连续 FAIL_LIMIT 次仍失败才终态 failed 并标注
        需人工——防死循环烧 API。"""
        node = self.nodes[nid]
        streak = node.get("fail_streak", 0) + 1
        node["fail_streak"] = streak
        if streak >= FAIL_LIMIT:
            node["state"] = "failed"
            node["note"] = f"{note}，连续失败达上限（{streak} 次），需人工"
            node_event(nid, "failed")
        else:
            node["state"] = "partial"
            node["note"] = f"{note}（第 {streak}/{FAIL_LIMIT} 次失败，10 分钟后重排队）"
            node_event(nid, "partial", 0)

    def finish(self, nid, proc):
        node = self.nodes[nid]
        dur = int(time.time() - self.started.get(nid, time.time()))
        rc = proc.returncode
        if node["kind"] == "bench-arm":
            p = node["params"]
            done = done_tasks(p["out"])
            rows = len(done)
            target = len(node.get("assigned") or p["tasks"])
            # MES 增量入账（幂等）。旧逻辑 capture_output 后不看 rc——bench-mes
            # 失败（如 10-21 CH 500）完全静默，账本缺事件无人知；现记录 rc 与 stderr
            # 尾部（MES 500 根因修复，2026-10-22 修理组）。timeout 120→180 容纳
            # bench-mes 内部 3 次重试的退避（30+2+30+8+30=100s 最坏值）。
            res = os.path.join(p["out"], "results.jsonl")
            if os.path.exists(res):
                try:
                    mr = subprocess.run([sys.executable, f"{WS}/tools/bench-mes.py", res],
                                        capture_output=True, timeout=180,
                                        stdin=subprocess.DEVNULL)
                    if mr.returncode != 0:
                        log(f"MES 增量入账失败（bench-mes rc={mr.returncode}，不致命）: "
                            f"{mr.stderr.decode(errors='replace')[-300:]}")
                except subprocess.TimeoutExpired:
                    log("MES 增量入账超时（bench-mes >180s，不致命）")
            if rows >= target and rc == 0:
                node["state"] = "done"
                node["fail_streak"] = 0
                node["note"] = f"{rows}/{target} 完成"
                node_event(nid, "done", dur)
            elif rows > 0:
                node["state"] = "partial"
                node["fail_streak"] = 0
                node["note"] = f"rc={rc} {rows}/{target}（可再调度续跑）"
                node_event(nid, "partial", rows)
            else:
                # 无有效行 ≠ 终态：走 bench_arm_fail 重排队，连续上限后才终态。
                self.bench_arm_fail(nid, f"rc={rc} 无有效行")
            log(f"结束 {nid}: {node['note']}（{dur}s）")
        elif node["kind"] == "relay-image":
            if rc == 0:
                node["state"] = "done"
                node_event(nid, "done", dur)
                log(f"结束 {nid}: ok（{dur}s）")
            else:
                # rc!=0 不一定真失败：cnb-relay 实测把镜像送到 anolis 后 docker load
                # 退出码误报 rc=1（2026-10-20 一天 6 个假 failed 堵死下游臂，手工 -r2
                # 解锁的根因）。以 anolis 实际镜像在场为准：精确名匹配在场即 done，
                # 不在场才 failed；盘点连续两次异常（ssh 抖动）按 failed 保守处理
                # （2026-10-20 22:21 波：闪断窗口单次盘点全失败，22 张已到场镜像被误
                # 终态 failed——所以先重试一次再下结论）。
                present = False
                for attempt in (1, 2):
                    try:
                        out = subprocess.run(
                            ["ssh", "-o", "ConnectTimeout=10", "anolis", "docker",
                             "images", "--format", "{{.Repository}}:{{.Tag}}"],
                            capture_output=True, text=True, timeout=60,
                            stdin=subprocess.DEVNULL).stdout
                        present = node["params"]["image"] in out.splitlines()
                    except Exception as e:
                        log(f"{nid} 镜像盘点失败（第 {attempt}/2 次）: {e}")
                    if present or attempt == 2:
                        break
                    time.sleep(15)
                if present:
                    node["state"] = "done"
                    node["note"] = "rc!=0 但镜像在场"
                    node_event(nid, "done", dur)
                    log(f"结束 {nid}: rc={rc} 但镜像在场，记 done（{dur}s）")
                else:
                    node["state"] = "failed"
                    node["note"] = f"rc={rc}"
                    node_event(nid, "failed")
                    log(f"结束 {nid}: FAILED rc={rc}（{dur}s）")
        self.running.pop(nid, None)
        self.started.pop(nid, None)
        node["finished_ts"] = time.time()

    def probe_token(self):
        """mcode 门禁探活（每轮 <=1 次，失败不打印令牌）。"""
        try:
            r = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "anolis",
                                "python3", "~/.local/bin/mcode-token.py", "verify"],
                               capture_output=True, text=True, timeout=90,
                               stdin=subprocess.DEVNULL)
            return r.returncode == 0
        except Exception:
            return False

    def save_status(self):
        st = {nid: {k: v for k, v in n.items() if k in ("state", "note", "kind")}
              for nid, n in self.nodes.items()}
        st["_summary"] = {
            "running": len(self.running),
            "done": sum(1 for n in self.nodes.values() if n["state"] == "done"),
            "failed": sum(1 for n in self.nodes.values() if n["state"] == "failed"),
            "partial": sum(1 for n in self.nodes.values() if n["state"] == "partial"),
            "pending": sum(1 for n in self.nodes.values() if n["state"] == "pending"),
            "ts": time.strftime("%F %T"),
        }
        with open(STATUS, "w") as f:
            json.dump(st, f, ensure_ascii=False, indent=1)

    def loop(self):
        self.load_graph()
        # 门禁探活限频（60s 一次）
        gate = self.nodes.get("gate-mcode-token")
        if gate and gate["state"] == "pending":
            if time.time() - getattr(self, "_last_probe", 0) > 60:
                self._last_probe = time.time()
                if self.probe_token():
                    gate["state"] = "done"
                    gate["note"] = "mcode 令牌 ok"
                    node_event("gate-mcode-token", "done")
                    log("mcode 令牌门禁: ok，m31f 臂放行")
        # partial 节点 10 分钟后重回 pending（断点续跑由 launch 内结算）
        now = time.time()
        for nid, n in self.nodes.items():
            if n["state"] == "partial" and now - n.get("finished_ts", now) > 600:
                n["state"] = "pending"
                n["note"] = "partial 重回队列"
        # 完成回收
        for nid, proc in list(self.running.items()):
            if proc.poll() is not None:
                self.finish(nid, proc)
        # 启动（按图序，保证先 relay 后 arm）
        for nid in self.order:
            node = self.nodes[nid]
            if node["state"] != "pending":
                continue
            if not self.deps_done(node):
                continue
            if node["kind"] == "token-gate":
                continue
            if not self.capacity(node):
                continue
            self.launch(node)
        self.save_status()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if args.init:
        init_graph()
        return
    sched = Sched()
    log(f"调度器启动（pid {os.getpid()}），图 {GRAPH}")
    log(f"[gate] tmpfs 闸生效: /tmp 关闭线<{TMPFS_MIN_MB}MiB 预警线<{TMPFS_WARN_MB}MiB"
        f"（statvfs f_bavail 本地读，盘点失败 fail-closed 暂派新 bench-arm；"
        f"env FACTORY_SCHED_TMPFS_WARN_MB/FACTORY_SCHED_TMPFS_MIN_MB 可覆盖）")
    while True:
        try:
            sched.loop()
        except Exception as e:
            log(f"调度轮异常（不退出）: {e}")
        if args.once:
            break
        time.sleep(5)


if __name__ == "__main__":
    main()
