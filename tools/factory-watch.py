#!/usr/bin/env python3
"""factory-watch.py — 黑灯工厂可观测中心（本机半边）：watchdog 守护 + 安灯分级 + 看板数据源。

定位：只读观测，不启动/不重启任何执行面组件。调度器（factory-sched.py）与 anolis 侧
      由别的角色负责；本脚本负责"看得见"：聚合 bench 结果、探活调度器、巡检 anolis、
      解析中继失败，并按安灯规则产出分级报警。

两种模式:
  factory-watch.py --once   # 单轮扫描，stdout 打印人类可读巡检报告（另刷新 latest.json/data.json）
  factory-watch.py          # 常驻：每 60s 一轮；写 状态观测/latest.json（机器可读全量快照）、
                            #   追加 状态观测/alarms.log（报警流水，同种报警 30 分钟内不重复记）、
                            #   每轮刷新 状态/看板/data.json（看板静态页的数据源）
环境变量:
  AF_WATCH_EXTRA_DIRS       # 逗号分隔的第二产线观测清单（目录 glob=额外面臂 tier=F2；
                            #   .json=额外调度器状态，配对同名 -graph.json 解析臂 out 映射），
                            #   如 "/tmp/bench-fix2-rerun-*,/tmp/factory2-status.json"

安灯规则（level / code / 触发条件，实现见 build_alarms()）:
  red   A0  调度器死/状态停更（状态文件缺失、mtime>300s，或进程连续 2 轮不在）
  red   A1  任一臂末态 run_failed 占比>10%（≥5 题；任务级口径：按 task_id 取
            results.jsonl 末行，重试救回的 attempt 不计——2026-10-22 修，修前
            行级口径把"曾经失败过的尝试"计成"现在仍失败"（实证 D1/D2-step-5
            行级 13/17 → 末态 0，四臂全误报）；与②组 mcode 官方线"78 任务有
            重复行、71 是 None+judged 混合、必须 last-row 口径"同源同坑）
            （归档豁免：results.jsonl mtime>6h 且无关联在跑进程的终态臂跳过不报，
            安灯节汇总一行 [已归档臂]——慢性信号不再每轮复报，归档依据见巡检日志）
  red   A2  任一臂末态零补丁（reward 为 None 且非 run_failed）占比>30%（≥10 题；
            同 A1 任务级口径。不用 gate 判零补丁：实证 gate=no_patch 行里有
            reward=true（启发式误判），reward/status 才是判分事实）
            （同 A1 归档豁免；行级零补丁/gate 拦截降为诊断信息行，不再触发红灯）
  amber A3  某档案 ≥10 题已判分且通过数为 0
  amber A4  anolis 任一巡检分区（/data、/）使用率>85%
  amber A4L 本机 /tmp 可用 <2662MiB（usrquota 校准线 2.6GiB，D-24；statvfs 盘点失败
            同码报「/tmp 盘点失败（fail-closed）」与写满文案强制区分；2252MiB 闸线
            之下 factory-sched/mcode-dispatch 已自动拦新臂/新判分，安灯提前叫人）
  amber A5  factory.log 尾部中继（relay）连续失败 ≥3（中间无一次 ok）
  amber A6  调度器认为 running 的 bench 臂 30 分钟无新 results 行
            （豁免：该臂 out 目录 runs/ 最新子目录 10 分钟内有写入——慢任务
            GLM/kimi 单题 30-60 分钟属正常，results 行只在整题收尾时落盘）
  amber A7  本机 sweb.eval 镜像唯一任务数<120 且连续 2 小时无新增
            （口径与 tools/local-image-feed.py 盘点一致：docker images 里
            swebench/sweb.eval.x86_64.<task> 去重仓库数；anolis 上的 relay
            镜像池另巡检上报，但不参与 A7——2026-10-22 前数的是 anolis 池，
            与 feed 进度无关，实证为误报来源）

容错：bench-fix1-* 目录尚未生成/工厂重启后空目录/结果行有空行或坏 JSON（逐行
      try/except 跳过并计数 n_bad_lines，不整文件失败、不漏坏行之后的所有行——
      2026-10-22 修，实测 D1-mavis-m31f 有 1 行写截断）/anolis ssh 不通/
      调度器从未运行——全部不崩，按 0 或 ok:false 呈现。密钥零明文（本脚本不碰密钥）。
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

WS = "/home/pan-ding/workspace/agent黑灯工厂"
SAMPLE = f"{WS}/计划/s1-swev-120.json"          # D1/D2/D3 分母来源
SCHED_STATUS = "/tmp/factory-status.json"       # 调度器状态（每 5s 刷新）
SCHED_LOG = "/tmp/factory.log"                  # 调度器日志（中继失败解析）
GRAPH = "/tmp/factory-graph.json"               # 调度图（读 bench 臂 out 目录映射）

OBS_DIR = f"{WS}/状态观测"
LATEST = f"{OBS_DIR}/latest.json"
ALARMS_LOG = f"{OBS_DIR}/alarms.log"
STATE_FILE = f"{OBS_DIR}/watch-state.json"
DASH_DIR = f"{WS}/状态/看板"
DASH_DATA = f"{DASH_DIR}/data.json"

INTERVAL = 60                # 常驻轮询周期（s）
DEDUP_WINDOW = 1800          # 同种报警 30 分钟内不重复记（s）
SCHED_STALE_S = 300          # 状态文件 mtime 超此值 → A0
RUNNING_STALL_S = 1800       # running 臂无新结果行 → A6
RUNS_FRESH_S = 600           # runs/ 最新子目录 10 分钟内有写入 → A6 豁免（慢任务在跑）
IMG_STALL_S = 7200           # 镜像数停滞判定窗 → A7
IMAGE_TARGET = 120
ARCHIVE_MATURITY_S = 6 * 3600  # results.jsonl mtime 超此龄且无关联在跑进程 → 臂归档（A1/A2 免报）
RELAY_FAIL_MIN = 3           # 连败阈值 → A5
# A4L 本机 /tmp 安灯线（D-24，patch-tmpfs-alarm-watch-A4L-R2 / 方案 P1-1）：/tmp=
# 7.5G tmpfs+usrquota，与判分结果/任务 json/调度器三件套共居；EDQUOT 实测于仅余
# ~1.7G（mes500-根因报告.md:42）。校准线 2662MiB≈2.6GiB=factory-sched tmpfs 闸 WARN；
# 闸线 2252MiB≈2.2GiB=factory-sched tmpfs_gate / mcode-dispatch probe_tmpfs 的
# CLOSE——低于它自动拦新，安灯负责在闸线之前叫人。
A4L_TMP_WARN_MB = 2662
A4L_TMP_GATE_MB = 2252

PROFILES = ["glm-cp", "glm-cp-max", "kimi-k3", "step-5", "qwen30b-local", "mavis-m31f"]
TIERS = ["D1", "D2", "D3"]
# 与 tools/factory-sched.py EXISTING_DIRS 保持一致（fix1 代目录；bench-s1-* 已作废不扫）
ARMS = {}
for _t in TIERS:
    _lo = _t.lower()
    ARMS[(_t, "glm-cp")] = f"/tmp/bench-fix1-{_lo}-glm-cp"
    ARMS[(_t, "glm-cp-max")] = f"/tmp/bench-fix1-{_lo}-glm-max"
    ARMS[(_t, "kimi-k3")] = f"/tmp/bench-fix1-{_lo}-kimi"
    ARMS[(_t, "step-5")] = f"/tmp/bench-fix1-{_lo}-step5"
    ARMS[(_t, "qwen30b-local")] = f"/tmp/bench-fix1-{_lo}-30b"
    ARMS[(_t, "mavis-m31f")] = f"/tmp/bench-fix1-{_lo}-m31f"

# status 字段里可判定为"零补丁"的取值（判不准的不计入，只按 status/reward 如实统计）
ZERO_PATCH_STATUSES = {"no_patch", "empty_patch", "zero_patch", "no_diff", "patch_empty"}

# ---------- 第二产线（实验线）观测 ----------
# AF_WATCH_EXTRA_DIRS：逗号分隔。含通配符的条目按目录 glob 展开为额外面臂（tier=F2，
# profile=目录名去掉 bench-fix2-rerun- 前缀）；.json 条目视为额外调度器状态文件
# （自动配对同名 -graph.json 以解析运行臂 → out 目录映射与 F2 目标题数）。
# 缺省空 = 只观测主产线（行为与引入前完全一致）。
EXTRA_DIRS_SPEC = os.environ.get("AF_WATCH_EXTRA_DIRS", "")


def parse_extra(spec):
    arm_dirs, statuses = [], []
    for ent in [x.strip() for x in spec.split(",") if x.strip()]:
        if any(c in ent for c in "*?["):
            arm_dirs.extend(sorted(p for p in glob.glob(ent) if os.path.isdir(p)))
        elif ent.endswith(".json"):
            statuses.append(ent)
    return arm_dirs, statuses


EXTRA_ARM_DIRS, EXTRA_STATUS_FILES = parse_extra(EXTRA_DIRS_SPEC)
EXTRA_GRAPHS = {s: s.replace("-status.json", "-graph.json") for s in EXTRA_STATUS_FILES}


def extra_profile(path):
    name = os.path.basename(path)
    return name[len("bench-fix2-rerun-"):] if name.startswith("bench-fix2-rerun-") else name


def now_s():
    return time.strftime("%F %T")


def write_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# ---------- 内部状态（吞吐/停滞判定用，仅常驻模式推进） ----------

def load_state():
    st = load_json(STATE_FILE, {})
    st.setdefault("line_hist", [])       # [[epoch, {dir: 行数}], ...] 保留 40min
    st.setdefault("last_increase", {})   # {dir: epoch} 该目录最近一次行数增长时刻
    st.setdefault("first_running", {})   # {node_id: epoch} 首次见到该节点 running
    st.setdefault("sweb_img_hist", [])   # [[epoch, 本机 sweb.eval 唯一任务数], ...] 保留 ~3h（A7 口径）
    st.pop("img_hist", None)             # 2026-10-22：A7 口径由 anolis SSH 计数改本机 feed 盘点，旧历史作废
    st.setdefault("alarm_open", {})      # {key: epoch} 报警条件首次持续出现时刻
    st.setdefault("alarm_logged", {})    # {key: epoch} 上次写入 alarms.log 时刻
    st.setdefault("proc_miss_streak", 0)
    return st


def save_state(st):
    try:
        write_atomic(STATE_FILE, json.dumps(st, ensure_ascii=False))
    except Exception:
        pass  # 状态写失败不影响观测主流程


def rows_10m(line_hist, path, cur_count, t):
    """最近 ~10 分钟新增行数：取 9-11 分钟前最近的采样做基线；无基线则取最老采样。"""
    base = None
    window = [s for s in line_hist if t - 660 <= s[0] <= t - 480]
    if window:
        base = window[-1]
    elif line_hist:
        base = line_hist[0]
    if base is None:
        return 0
    return max(0, cur_count - base[1].get(path, 0))


def runs_recent_mtime(arm_dir):
    """该臂 out/runs/ 最新子目录的最后活动时刻（epoch）；无 runs/ 或异常返回 None。

    取"最新子目录自身 mtime"与"其内直接文件最大 mtime"的较大者：长生成期
    只追加写单个文件（如 effects.db-wal）时目录 mtime 不动，须看文件级才能
    真实反映"任务还在跑"。
    """
    runs = os.path.join(arm_dir, "runs")
    try:
        subs = [e for e in os.scandir(runs) if e.is_dir()]
        if not subs:
            return None
        newest = max(subs, key=lambda e: e.stat().st_mtime)
        mt = newest.stat().st_mtime
        for f in os.scandir(newest.path):
            try:
                mt = max(mt, f.stat().st_mtime)
            except OSError:
                continue
        return mt
    except OSError:
        return None


# ---------- ① bench 结果聚合 ----------

def scan_arm(path):
    st = {
        "dir": path, "exists": os.path.isdir(path),
        "n_total": 0, "n_reward_true": 0, "n_completed_not_reward": 0,
        "n_run_failed": 0, "n_blocked": 0,
        # 任务级（末行口径，A1/A2 判定用，2026-10-22 修）：按 task_id 取末行
        "n_tasks": 0, "task_run_failed": 0, "task_zero_patch": 0,
        "n_bad_lines": 0,          # 坏行计数（JSON 解析/解码失败，逐行跳过）
        "sum_turns": 0, "n_turns": 0,
        "sum_tin": 0, "sum_tout": 0, "sum_tcache": 0, "n_tokens": 0,
        "sum_wall_ms": 0, "n_wall": 0,
        "judged_tasks": 0, "resolved_tasks": 0,
        "res_mtime": None,          # results.jsonl mtime（epoch）；终态臂归档判定用
    }
    if not st["exists"]:
        return st
    res = os.path.join(path, "results.jsonl")
    try:
        st["res_mtime"] = os.stat(res).st_mtime
    except OSError:
        st["res_mtime"] = None
    last_by_task = {}
    any_reward = set()
    try:
        # 二进制逐行读 + 逐行 try/except：坏行（写截断/编码坏字节）跳过并计数，
        # 不整文件失败、不漏掉坏行之后的所有行（2026-10-22 修；D1-m31f 实测 1 行）
        with open(res, "rb") as f:
            for raw in f:
                try:
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    r = json.loads(line)
                except Exception:
                    st["n_bad_lines"] += 1
                    continue
                if not isinstance(r, dict):
                    continue
                st["n_total"] += 1
                if r.get("reward") is True:
                    st["n_reward_true"] += 1
                status = r.get("status")
                if status == "completed" and r.get("reward") is not True:
                    st["n_completed_not_reward"] += 1
                if status == "run_failed":
                    st["n_run_failed"] += 1
                gate = r.get("gate")
                if (gate is not None and gate != "ok") or \
                   (gate is None and status in ZERO_PATCH_STATUSES):
                    st["n_blocked"] += 1
                turns = r.get("turns")
                if isinstance(turns, (int, float)):
                    st["sum_turns"] += turns
                    st["n_turns"] += 1
                tok = r.get("tokens") if isinstance(r.get("tokens"), dict) else {}
                if tok:
                    st["sum_tin"] += tok.get("input") or 0
                    st["sum_tout"] += tok.get("output") or 0
                    st["sum_tcache"] += tok.get("cache_read") or 0
                    st["n_tokens"] += 1
                wall = r.get("agent_wall_ms")
                if isinstance(wall, (int, float)):
                    st["sum_wall_ms"] += wall
                    st["n_wall"] += 1
                task = r.get("task_id") or r.get("case_id")
                if task:
                    last_by_task[task] = r  # append 语义：后行覆盖前行
                    if r.get("reward") is True:
                        any_reward.add(task)
    except FileNotFoundError:
        st["exists"] = False
        return st
    # 任务级末行口径（A1/A2 判定，2026-10-22 修）：last_by_task 即 append 序末行
    st["n_tasks"] = len(last_by_task)
    st["task_run_failed"] = sum(
        1 for r in last_by_task.values() if r.get("status") == "run_failed")
    # 末态零补丁：判分事实 reward=None（未解决/未判到）且末行非 run_failed。
    # 不用 gate 判零补丁——实证 gate=no_patch 行里有 reward=true（启发式误判）。
    st["task_zero_patch"] = sum(
        1 for r in last_by_task.values()
        if r.get("reward") is None and r.get("status") != "run_failed")
    st["judged_tasks"] = sum(
        1 for r in last_by_task.values()
        if r.get("reward") is not None or r.get("status") not in (None, "run_failed"))
    st["resolved_tasks"] = len(any_reward)
    return st


def scan_all_arms(state, t):
    hist = state["line_hist"]
    spec = [(tier, prof, ARMS[(tier, prof)]) for tier in TIERS for prof in PROFILES]
    spec += [("F2", extra_profile(d), d) for d in EXTRA_ARM_DIRS]
    arms = []
    for tier, prof, path in spec:
        a = scan_arm(path)
        cnt = a["n_total"]
        if a["exists"]:
            prev = hist[-1][1].get(path, 0) if hist else 0
            if cnt > prev:
                state["last_increase"][path] = t
            elif path not in state["last_increase"]:
                state["last_increase"][path] = t
        a["tier"] = tier
        a["profile"] = prof
        a["rows_10m"] = rows_10m(hist, path, cnt, t) if hist else 0
        li = state["last_increase"].get(path)
        a["last_new_row_age_s"] = int(t - li) if li else None
        arms.append(a)
    return arms


def scan_plan_tiers():
    """各难度档题数（分母）。计划文件缺失/坏 → 全 0，不崩。"""
    tiers = {}
    sample = load_json(SAMPLE, None)
    if isinstance(sample, list):
        for it in sample:
            if isinstance(it, dict) and it.get("tier") in TIERS:
                tiers[it["tier"]] = tiers.get(it["tier"], 0) + 1
    for t in TIERS:
        tiers.setdefault(t, 0)
    return tiers


# ---------- ② 调度器活性 ----------

def node_arm_dir(nid):
    base = nid[:-3] if nid.endswith("-w1") else nid
    m = re.match(r"arm-d([123])-(.+)$", base)
    if not m:
        return None
    return ARMS.get(("D" + m.group(1), m.group(2)))


def scan_scheduler(state, t):
    out = {"status_file_exists": os.path.exists(SCHED_STATUS),
           "mtime_age_s": None, "pids": [], "alive": False,
           "summary": None, "running_arms": [], "error": None}
    try:
        out["mtime_age_s"] = int(t - os.stat(SCHED_STATUS).st_mtime)
    except FileNotFoundError:
        pass
    except Exception as e:
        out["error"] = str(e)
    try:
        r = subprocess.run(["pgrep", "-f", "factory-sched.py"],
                           capture_output=True, text=True, timeout=15)
        pids = []
        for x in r.stdout.split():
            try:
                with open(f"/proc/{x}/cmdline", "rb") as f:
                    argv0 = f.read().split(b"\0")[0].decode("utf-8", "replace")
                # 只认 python3 进程本体，排除启动它的 bash 包装命令行
                if os.path.basename(argv0).startswith("python"):
                    pids.append(int(x))
            except Exception:
                continue
        out["pids"] = pids
    except Exception as e:
        out["error"] = out["error"] or str(e)
    proc_up = bool(out["pids"])
    state["proc_miss_streak"] = 0 if proc_up else state.get("proc_miss_streak", 0) + 1
    proc_confirmed_down = state["proc_miss_streak"] >= 2  # 2 轮确认，避免重启窗口误报
    mtime_stale = out["mtime_age_s"] is None or out["mtime_age_s"] > SCHED_STALE_S
    out["alive"] = proc_up and not mtime_stale
    out["proc_confirmed_down"] = proc_confirmed_down
    out["mtime_stale"] = mtime_stale

    stt = load_json(SCHED_STATUS, None)
    if isinstance(stt, dict):
        out["summary"] = stt.get("_summary")
        for nid, n in stt.items():
            if nid == "_summary" or not isinstance(n, dict):
                continue
            if n.get("kind") == "bench-arm" and n.get("state") == "running":
                out["running_arms"].append({"node": nid, "dir": node_arm_dir(nid)})
    return out


def scan_extra_schedulers(t):
    """第二产线调度器（EXTRA_STATUS_FILES）：只读观测——活性看状态文件 mtime，
    运行臂 out 目录从配对 -graph.json 的 params 解析。"""
    out = []
    for sp in EXTRA_STATUS_FILES:
        e = {"status": sp, "exists": os.path.exists(sp), "mtime_age_s": None,
             "summary": None, "running_arms": []}
        try:
            e["mtime_age_s"] = int(t - os.stat(sp).st_mtime)
        except FileNotFoundError:
            pass
        except Exception:
            pass
        gparams = {}
        gp = EXTRA_GRAPHS.get(sp)
        if gp:
            g = load_json(gp, None)
            if isinstance(g, dict):
                gparams = {n.get("id"): n.get("params", {})
                           for n in g.get("nodes", []) if isinstance(n, dict)}
        stt = load_json(sp, None)
        if isinstance(stt, dict):
            e["summary"] = stt.get("_summary")
            for nid, n in stt.items():
                if nid == "_summary" or not isinstance(n, dict):
                    continue
                if n.get("kind") == "bench-arm" and n.get("state") == "running":
                    d = (gparams.get(nid) or {}).get("out") or node_arm_dir(nid)
                    e["running_arms"].append({"node": nid, "dir": d})
        out.append(e)
    return out


def extra_f2_target():
    """F2 实验线目标题数（配对 graph 里 bench-arm tasks 数之和；图缺则按已见目录数×1）。"""
    total = 0
    for sp in EXTRA_STATUS_FILES:
        gp = EXTRA_GRAPHS.get(sp)
        g = load_json(gp, None) if gp else None
        if isinstance(g, dict):
            total += sum(len((n.get("params") or {}).get("tasks", []))
                         for n in g.get("nodes", [])
                         if isinstance(n, dict) and n.get("kind") == "bench-arm")
    return total


# ---------- ③ anolis 巡检 ----------

ANOLIS_CMD = (
    "df -P /data / 2>/dev/null; "
    "echo ---; docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -c 'sweb.eval'; "
    "echo ---; curl -s -m 5 http://127.0.0.1:11434/api/tags 2>/dev/null | head -c 2000; "
    "echo; echo ---; cat /proc/loadavg 2>/dev/null"
)


def scan_anolis(state, t):
    out = {"ok": False, "disk": {}, "sweb_images": None, "image_target": IMAGE_TARGET,
           "ollama": "unknown", "load": None, "error": None}
    try:
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                            "anolis", ANOLIS_CMD],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            out["error"] = (r.stderr or "").strip().splitlines()[-1:] or f"rc={r.returncode}"
            out["error"] = out["error"][0] if out["error"] else f"rc={r.returncode}"
            return out
        parts = [p.strip("\n") for p in r.stdout.split("\n---\n")]
        if len(parts) >= 4:
            for line in parts[0].splitlines():
                f_ = line.split()
                if len(f_) >= 5 and f_[0].startswith("/dev/"):
                    out["disk"][f_[5]] = {"use_pct": int(f_[4].rstrip("%")),
                                          "size": f_[1], "used": f_[2], "avail": f_[3]}
            cnt_s = parts[1].strip().splitlines()[-1].strip() if parts[1].strip() else ""
            out["sweb_images"] = int(cnt_s) if cnt_s.isdigit() else None
            tags = parts[2].strip()
            out["ollama"] = "ok" if '"models"' in tags else "down"
            la = parts[3].strip().split()
            if len(la) >= 3:
                out["load"] = {"m1": float(la[0]), "m5": float(la[1]), "m15": float(la[2])}
            out["ok"] = True
    except Exception as e:
        out["error"] = str(e)
    return out


def scan_local_images(state, t):
    """本机 sweb.eval 镜像唯一任务数（A7 口径，与 tools/local-image-feed.py 盘点一致）。

    数法：docker images 的 Repository 列取 swebench/sweb.eval.x86_64.<task> 前缀的
    去重集合大小——同任务多 tag/重复 tag 不重复计，与 feed"已就位 120/120"同源同口径。
    2026-10-22 前 A7 数的是 anolis SSH 口径（anolis 的 relay 镜像池，67/120 与本机
    feed 进度无关），已实证为误报来源；anolis 池仍巡检上报，但不再参与 A7 停滞判定。
    docker 不可用/超时/非零退出 → None（本轮不判定、不写历史）。
    """
    try:
        r = subprocess.run(["docker", "images", "--format", "{{.Repository}}"],
                           capture_output=True, text=True, timeout=120)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    prefix = "swebench/sweb.eval.x86_64."
    n = len({ln.strip() for ln in r.stdout.splitlines() if ln.strip().startswith(prefix)})
    hist = state["sweb_img_hist"]
    hist.append([t, n])
    state["sweb_img_hist"] = [s for s in hist if t - s[0] <= IMG_STALL_S + 600]
    return n


# ---------- ④ 中继连败解析 ----------

RELAY_END_RE = re.compile(r"\] 结束 (relay-\S+): (ok|FAILED\S*)")


def scan_relay():
    out = {"consecutive_failures": 0, "last_event": None}
    try:
        with open(SCHED_LOG, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 200000))
            tail = f.read().decode("utf-8", "replace")
    except FileNotFoundError:
        out["last_event"] = "factory.log 不存在"
        return out
    except Exception as e:
        out["last_event"] = f"读取失败: {e}"
        return out
    events = [(m.group(1), m.group(2), line.strip())
              for line in tail.splitlines()
              if (m := RELAY_END_RE.search(line))]
    if not events:
        out["last_event"] = "日志尾部暂无 relay 结束事件"
        return out
    cutoff = time.time() - 1800  # 30min 窗：更旧的结局不计入连败（2026-10-21 教训：
    # 图内 relay 清零后不会再有新事件，历史连败尾巴会让 A5 永久常亮 = 告警疲劳）
    for name, verdict, line in reversed(events):  # 从最新往回数连败（尾部连败才触发 A5）
        out["last_event"] = line
        m_ts = re.match(r"\[([\d\-]+ [\d:]+)\]", line)
        if m_ts:
            try:
                if time.mktime(time.strptime(m_ts.group(1), "%Y-%m-%d %H:%M:%S")) < cutoff:
                    break
            except ValueError:
                pass
        if verdict == "ok":
            break
        out["consecutive_failures"] += 1
    return out


# ---------- 安灯 ----------

def bench_proc_dirs():
    """正在运行的 bench 进程涉及的臂 out 目录集合（读 /proc 命令行，零子进程）。

    判据=argv0 basename 含 "bench" 的进程（af-bench/af-bench-fix2）的 --out 实参，
    兼收命令行里任何 /tmp/bench-* 实参。调度器 running_arms 之外的第二判据：
    臂被调度器之外的方式拉起（手工重跑等）也认其在跑，避免误归档灭掉在跑臂的报警。
    """
    dirs = set()
    me = os.getpid()
    try:
        pids = os.listdir("/proc")
    except OSError:
        return dirs
    for pid in pids:
        if not pid.isdigit() or int(pid) == me:
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                toks = [a.decode("utf-8", "replace") for a in f.read().split(b"\0") if a]
        except OSError:
            continue
        if not toks or "bench" not in os.path.basename(toks[0]):
            continue
        for i, a in enumerate(toks):
            if a == "--out" and i + 1 < len(toks):
                dirs.add(toks[i + 1])
            elif a.startswith("/tmp/bench-"):
                dirs.add(a)
    return dirs


def classify_archived(arms, sched, extras, t):
    """终态臂归档：results.jsonl mtime > ARCHIVE_MATURITY_S 且无关联在跑进程的臂，
    A1/A2 慢性灯免报（安灯节汇总一行 [已归档臂]）；有新活动的臂照常报警。

    "关联在跑进程" = 调度器（主产线/实验线）running_arms 指向的 out 目录，或 /proc
    里 bench 进程命令行出现的臂目录，二者取并。无 results.jsonl 的臂不判归档
    （无行即无 A1/A2 可报，且无法主张 6h 停滞）。返回 (archived, active_dirs)。
    """
    active = set()
    for ra in sched.get("running_arms") or []:
        if ra.get("dir"):
            active.add(ra["dir"])
    for e in extras or []:
        for ra in e.get("running_arms") or []:
            if ra.get("dir"):
                active.add(ra["dir"])
    active |= bench_proc_dirs()
    archived = [a for a in arms
                if a.get("res_mtime") is not None
                and t - a["res_mtime"] > ARCHIVE_MATURITY_S
                and a["dir"] not in active]
    return archived, active


def probe_local_tmp_mb():
    """本机 /tmp 可用（MiB）。statvfs 本地读 f_bavail（tmpfs 无 root 保留，与 df 同值）。
    异常 → (-1, True)=盘点失败（fail-closed 口径；与真写满同码 A4L:tmp 但文案强制区分）。"""
    try:
        st = os.statvfs("/tmp")
        return st.f_bavail * st.f_frsize // 1048576, False
    except Exception:
        return -1, True


def build_alarms(arms, sched, anolis, relay, plan, state, t, extras=None, archived=None):
    alarms = []

    def add(level, code, key, message, first_seen):
        alarms.append({"level": level, "code": code, "key": key,
                       "message": message,
                       "since": time.strftime("%F %T", time.localtime(first_seen))})

    # A0 调度器死/状态停更
    if not sched["status_file_exists"]:
        add("red", "A0", "A0", "调度器状态文件缺失（从未运行或已被清理）", t)
    elif sched["mtime_stale"]:
        age = sched["mtime_age_s"]
        add("red", "A0", "A0",
            f"调度器状态停更：factory-status.json 已 {age}s 未刷新（阈值 {SCHED_STALE_S}s）", t)
    elif sched["proc_confirmed_down"]:
        add("red", "A0", "A0", "调度器进程不存在（连续 2 轮 pgrep 无果）", t)

    # A1/A2 按臂（归档的终态臂跳过：results.jsonl mtime>6h 且无关联在跑进程，
    # 慢性红灯不再每轮复报——汇总见安灯节 [已归档臂] 行，归档依据见巡检日志）
    archived_dirs = {a["dir"] for a in (archived or [])}
    for a in arms:
        if a["dir"] in archived_dirs:
            continue
        name = f"{a['tier']}-{a['profile']}"
        # A1/A2 = 任务级末行口径（2026-10-22 修）：按 task_id 取 results.jsonl 末行，
        # 重试救回的 attempt 不计入；行级值降为诊断信息行（render_report [口径明细]），
        # 不再触发红灯。修前误报实证：D1/D2-step-5 行级 run_failed 13/17 → 末态 0，
        # D1/D2-mavis-m31f 行级拦截 27/21 → 末态零补丁 5/1，10%/30% 阈值全不触。
        if a["n_tasks"] >= 5 and a["task_run_failed"] / a["n_tasks"] > 0.10:
            add("red", "A1", f"A1:{name}",
                f"臂 {name}: 末态 run_failed {a['task_run_failed']}/{a['n_tasks']} "
                f"({a['task_run_failed'] * 100 / a['n_tasks']:.0f}%) > 10%"
                f"（任务级末行口径；行级 run_failed={a['n_run_failed']}/{a['n_total']} 为历史尝试）", t)
        if a["n_tasks"] >= 10 and a["task_zero_patch"] / a["n_tasks"] > 0.30:
            add("red", "A2", f"A2:{name}",
                f"臂 {name}: 末态零补丁 {a['task_zero_patch']}/{a['n_tasks']} "
                f"({a['task_zero_patch'] * 100 / a['n_tasks']:.0f}%) > 30%"
                f"（任务级末行口径；行级零补丁/gate拦截={a['n_blocked']}/{a['n_total']} 为历史尝试）", t)

    # A3 按档案聚合：≥10 题已判分且通过 0
    by_prof = {}
    for a in arms:
        p = by_prof.setdefault(a["profile"], {"judged": 0, "resolved": 0})
        p["judged"] += a["judged_tasks"]
        p["resolved"] += a["resolved_tasks"]
    for prof, p in sorted(by_prof.items()):
        if p["judged"] >= 10 and p["resolved"] == 0:
            add("amber", "A3", f"A3:{prof}",
                f"档案 {prof}: 已判分 {p['judged']} 题通过 0", t)

    # A4 anolis 分区
    for mnt, d in sorted((anolis.get("disk") or {}).items()):
        if d["use_pct"] > 85:
            add("amber", "A4", f"A4:{mnt}",
                f"anolis 分区 {mnt} 使用率 {d['use_pct']}%（{d['used']}/{d['size']}）> 85%", t)

    # A4L 本机 /tmp（D-24，patch-tmpfs-alarm-watch-A4L-R2 / 方案 P1-1）：判分 results、
    # swev 任务 json、调度器三件套全落本机 /tmp（tmpfs+usrquota）。<校准线报 amber；
    # 盘点失败同码另文案。30min 去重由 log_alarms 的 alarm_logged 同款承担。
    tmp_mb, tmp_fail = probe_local_tmp_mb()
    if tmp_fail:
        add("amber", "A4L:tmp", "A4L:tmp", "/tmp 盘点失败（fail-closed）", t)
    elif tmp_mb < A4L_TMP_WARN_MB:
        add("amber", "A4L:tmp", "A4L:tmp",
            f"本机 /tmp 可用 {tmp_mb} MiB<{A4L_TMP_WARN_MB}MiB"
            f"（usrquota 校准线，闸线 {A4L_TMP_GATE_MB}MiB，低于则 sched/mcode 拦新臂/新判分）", t)

    # A5 中继连败
    if relay["consecutive_failures"] >= RELAY_FAIL_MIN:
        add("amber", "A5", "A5",
            f"中继连续失败 {relay['consecutive_failures']} 次（≥{RELAY_FAIL_MIN}）无一次 ok；"
            f"最近: {relay['last_event']}", t)

    # A6 running 臂 30 分钟无新结果行（主产线 + 第二产线实验调度器）
    if sched.get("alive"):
        for ra in sched["running_arms"]:
            nid, d = ra["node"], ra["dir"]
            if not d:
                continue
            first = state["first_running"].setdefault(nid, t)
            if t - first < RUNNING_STALL_S:
                continue
            li = state["last_increase"].get(d)
            age = t - li if li else None
            if age is None or age > RUNNING_STALL_S:
                # 慢任务豁免：runs/ 最新子目录 10 分钟内有写入（含其内文件）即视为
                # 活跃——GLM/kimi 单题 30-60 分钟正常，results 行整题收尾才落盘。
                rmt = runs_recent_mtime(d)
                if rmt is not None and t - rmt <= RUNS_FRESH_S:
                    continue
                add("amber", "A6", f"A6:{nid}",
                    f"运行中臂 {nid} 已 {int(age)}s 无新结果行"
                    f"（{d}）" if age is not None else
                    f"运行中臂 {nid} 无新结果行记录（{d}）", t)
    for e in (extras or []):
        for ra in e.get("running_arms", []):
            nid, d = ra["node"], ra["dir"]
            if not d:
                continue
            first = state["first_running"].setdefault(nid, t)
            if t - first < RUNNING_STALL_S:
                continue
            li = state["last_increase"].get(d)
            age = t - li if li else None
            if age is None or age > RUNNING_STALL_S:
                rmt = runs_recent_mtime(d)
                if rmt is not None and t - rmt <= RUNS_FRESH_S:
                    continue
                add("amber", "A6", f"A6:{nid}",
                    f"运行中臂 {nid} 已 {int(age)}s 无新结果行"
                    f"（{d}）" if age is not None else
                    f"运行中臂 {nid} 无新结果行记录（{d}）", t)

    # A7 镜像停滞：2 小时无新增且 <120（本机 feed 盘点口径，见 scan_local_images）
    ih = state["sweb_img_hist"]
    if len(ih) >= 2 and ih[-1][0] - ih[0][0] >= IMG_STALL_S:
        recent = [c for ts, c in ih if t - ts <= IMG_STALL_S]
        if recent and ih[-1][1] < IMAGE_TARGET and max(recent) == min(recent) == ih[-1][1]:
            add("amber", "A7", "A7",
                f"本机 sweb.eval 镜像停滞在 {ih[-1][1]}/{IMAGE_TARGET} 已 2 小时无新增"
                f"（feed 盘点口径：唯一任务数）", t)

    # since 持续性：条件消失即清；持续则沿用首次时刻
    open_keys = {}
    for al in alarms:
        first = state["alarm_open"].get(al["key"], t)
        state["alarm_open"][al["key"]] = first
        al["since"] = time.strftime("%F %T", time.localtime(first))
        open_keys[al["key"]] = True
    for k in list(state["alarm_open"]):
        if k not in open_keys:
            del state["alarm_open"][k]
    order = {"red": 0, "amber": 1}
    alarms.sort(key=lambda x: (order[x["level"]], x["code"], x["key"]))
    return alarms


def log_alarms(alarms, state, t):
    try:
        with open(ALARMS_LOG, "a", encoding="utf-8") as f:
            for al in alarms:
                last = state["alarm_logged"].get(al["key"])
                if last is None or t - last >= DEDUP_WINDOW:
                    f.write(json.dumps({
                        "ts": now_s(), "level": al["level"], "code": al["code"],
                        "message": al["message"], "since": al["since"],
                    }, ensure_ascii=False) + "\n")
                    state["alarm_logged"][al["key"]] = t
    except Exception:
        pass


# ---------- 汇总快照 ----------

def build_snapshot(arms, plan, sched, anolis, relay, alarms, mode, extras=None, archived=None):
    totals = {
        "n_total": sum(a["n_total"] for a in arms),
        "n_reward_true": sum(a["n_reward_true"] for a in arms),
        "n_run_failed": sum(a["n_run_failed"] for a in arms),
        "rows_10m": sum(a["rows_10m"] for a in arms),
        "n_tasks": sum(a["n_tasks"] for a in arms),
        "task_run_failed": sum(a["task_run_failed"] for a in arms),
        "task_zero_patch": sum(a["task_zero_patch"] for a in arms),
        "n_bad_lines": sum(a["n_bad_lines"] for a in arms),
    }
    cost = []
    for prof in PROFILES:
        rows = [a for a in arms if a["profile"] == prof]
        cost.append({
            "profile": prof,
            "runs": sum(a["n_total"] for a in rows),
            "tokens_in": sum(a["sum_tin"] for a in rows),
            "tokens_out": sum(a["sum_tout"] for a in rows),
            "tokens_cache": sum(a["sum_tcache"] for a in rows),
        })
    plan_tiers = dict(plan)
    if EXTRA_ARM_DIRS:
        plan_tiers.setdefault("F2", extra_f2_target())
    return {
        "ts": now_s(),
        "epoch": int(time.time()),
        "generated_by": "tools/factory-watch.py",
        "mode": mode,
        "interval_s": INTERVAL,
        "plan": {"file": SAMPLE, "tiers": plan_tiers},
        "scheduler": {k: v for k, v in sched.items() if k != "summary"} | {"summary": sched.get("summary")},
        "extra_schedulers": extras or [],
        "arms": [{k: a[k] for k in (
            "tier", "profile", "dir", "exists", "n_total", "n_reward_true",
            "n_completed_not_reward", "n_run_failed", "n_blocked",
            "n_tasks", "task_run_failed", "task_zero_patch", "n_bad_lines",
            "judged_tasks", "resolved_tasks", "rows_10m", "last_new_row_age_s",
        )} | {
            "avg_turns": round(a["sum_turns"] / a["n_turns"], 1) if a["n_turns"] else None,
            "avg_tokens_in": int(a["sum_tin"] / a["n_tokens"]) if a["n_tokens"] else None,
            "avg_tokens_out": int(a["sum_tout"] / a["n_tokens"]) if a["n_tokens"] else None,
            "avg_tokens_cache": int(a["sum_tcache"] / a["n_tokens"]) if a["n_tokens"] else None,
            "avg_wall_ms": int(a["sum_wall_ms"] / a["n_wall"]) if a["n_wall"] else None,
        } for a in arms],
        "anolis": anolis,
        "relay": relay,
        "totals": totals,
        "cost": cost,
        "archived_arms": {
            "n": len(archived or []),
            "arms": [f"{a['tier']}-{a['profile']}" for a in (archived or [])],
            "rule": f"results.jsonl mtime>{ARCHIVE_MATURITY_S}s 且无关联在跑进程 → A1/A2 免报",
        },
        "alarms": alarms,
    }


# ---------- 人类可读报告（--once） ----------

def fmt_avg(x, unit=""):
    return "-" if x is None else f"{x}{unit}"


def render_report(s):
    L = []
    L.append("=" * 72)
    L.append(f"黑灯工厂巡检报告  {s['ts']}  （模式 {s['mode']}）")
    L.append("=" * 72)

    sc = s["scheduler"]
    if sc["alive"]:
        sm = sc.get("summary") or {}
        L.append(f"[调度器] 存活 pid={' '.join(map(str, sc['pids'])) or '?'}  "
                 f"状态龄 {sc['mtime_age_s']}s  "
                 f"running={sm.get('running')} done={sm.get('done')} "
                 f"failed={sm.get('failed')} partial={sm.get('partial')} "
                 f"pending={sm.get('pending')}（摘要 ts {sm.get('ts')}）")
    else:
        why = []
        if not sc["status_file_exists"]:
            why.append("状态文件缺失")
        if sc.get("mtime_stale"):
            why.append(f"状态停更 {sc['mtime_age_s']}s")
        if sc.get("proc_confirmed_down"):
            why.append("进程不在")
        L.append(f"[调度器] 失联（{'；'.join(why) or '未知'}）——若修理组正在重启属预期，A0 会持续挂红直至恢复")

    L.append(f"[产线矩阵] 目标分母 D1={s['plan']['tiers']['D1']} "
             f"D2={s['plan']['tiers']['D2']} D3={s['plan']['tiers']['D3']}"
             f"（{os.path.basename(SAMPLE)}）"
             + (f"  F2={s['plan']['tiers'].get('F2', 0)}（实验线 fix2 重跑）"
                if "F2" in s["plan"]["tiers"] else ""))
    L.append(f"  {'档/档案':<18}{'目录':<4}{'总行':>5}{'通过':>5}{'完成未过':>7}"
             f"{'run_fail':>9}{'拦截':>5}{'判分题':>6}{'10min':>6}"
             f"{'avg turns':>10}{'avg wall':>10}")
    for a in s["arms"]:
        L.append(f"  {a['tier']}-{a['profile']:<13}"
                 f"{'有' if a['exists'] else '无':>4}"
                 f"{a['n_total']:>6}{a['n_reward_true']:>6}"
                 f"{a['n_completed_not_reward']:>8}{a['n_run_failed']:>9}"
                 f"{a['n_blocked']:>6}{a['judged_tasks']:>7}{a['rows_10m']:>7}"
                 f"{fmt_avg(a['avg_turns']):>11}{fmt_avg(a['avg_wall_ms'], 'ms'):>12}")
    t = s["totals"]
    L.append(f"  合计: 行 {t['n_total']}，reward=true {t['n_reward_true']}，"
             f"run_failed {t['n_run_failed']}，最近10分钟新增 {t['rows_10m']} 行")

    # 口径明细（2026-10-22 修）：A1/A2 按任务级末行判定；行级=历史 attempt 仅诊断
    data_arms = [a for a in s["arms"]
                 if a["exists"] and (a["n_total"] > 0 or a["n_bad_lines"] > 0)]
    if data_arms:
        L.append("[口径明细] A1/A2=任务级末行（每 task 取 results.jsonl 末行，重试救回不计）；"
                 "行级=历史 attempt，仅诊断不触发安灯")
        for a in data_arms:
            nm = f"{a['tier']}-{a['profile']}"
            bad = f"  坏行 {a['n_bad_lines']}" if a["n_bad_lines"] else ""
            L.append(f"  {nm:<18}唯一题 {a['n_tasks']:>3}  末态 run_failed {a['task_run_failed']:>2}  "
                     f"末态零补丁 {a['task_zero_patch']:>2}  ｜行级 run_failed "
                     f"{a['n_run_failed']}/{a['n_total']}  零补丁/gate "
                     f"{a['n_blocked']}/{a['n_total']}{bad}")

    for e in s.get("extra_schedulers", []):
        if not e["exists"]:
            L.append(f"[实验线调度器] 状态文件缺失（{e['status']}）")
            continue
        sm = e.get("summary") or {}
        fresh = e["mtime_age_s"] is not None and e["mtime_age_s"] <= SCHED_STALE_S
        arms_s = " ".join(f"{ra['node']}→{ra['dir']}" for ra in e["running_arms"]) or "无"
        L.append(f"[实验线调度器] {'存活' if fresh else '停更'} "
                 f"状态龄 {e['mtime_age_s']}s  running={sm.get('running')} "
                 f"done={sm.get('done')} partial={sm.get('partial')} "
                 f"failed={sm.get('failed')} pending={sm.get('pending')}  运行臂: {arms_s}")

    an = s["anolis"]
    if an["ok"]:
        disks = "  ".join(f"{m} {d['use_pct']}%({d['avail']}可用)"
                          for m, d in sorted(an["disk"].items()))
        loc = an.get("local_sweb_images")
        loc_s = (f"本机 {loc}/{an['image_target']}（A7 口径）"
                 if loc is not None else "本机 未知")
        img_s = (f"镜像 anolis {an['sweb_images']}/{an['image_target']}｜{loc_s}")
        ld = an["load"]
        L.append(f"[anolis] {disks}  {img_s}  ollama {an['ollama']}  "
                 f"load {ld['m1']}/{ld['m5']}/{ld['m15']}" if ld else
                 f"[anolis] {disks}  {img_s}  ollama {an['ollama']}  load 未知")
    else:
        L.append(f"[anolis] 巡检失败：{an.get('error') or '未知原因'}"
                 f"（A4 暂不判定；A7 口径=本机 docker feed 盘点，不受 ssh 影响）")

    rl = s["relay"]
    L.append(f"[中继] 连续失败 {rl['consecutive_failures']}（≥{RELAY_FAIL_MIN} 触发 A5）  "
             f"最近事件: {rl['last_event']}")

    al = s["alarms"]
    n_red = sum(1 for x in al if x["level"] == "red")
    n_amb = sum(1 for x in al if x["level"] == "amber")
    L.append(f"[安灯] 红 {n_red} / 黄 {n_amb}")
    if not al:
        L.append("  （无报警）")
    for x in al:
        mark = "红灯" if x["level"] == "red" else "黄灯"
        L.append(f"  [{mark}] {x['code']} since {x['since']}  {x['message']}")

    arc = s.get("archived_arms") or {}
    if arc.get("n"):
        L.append(f"  [已归档臂] {arc['n']} 臂（fix1 终态矩阵，慢性信号已归档见巡检日志）")

    L.append("[成本] 各档案累计（跨三档聚合）")
    L.append(f"  {'档案':<16}{'runs':>6}{'tokens_in':>14}{'tokens_out':>13}{'cache_read':>14}")
    for c in s["cost"]:
        L.append(f"  {c['profile']:<16}{c['runs']:>7}"
                 f"{c['tokens_in']:>15}{c['tokens_out']:>14}{c['tokens_cache']:>15}")
    L.append("=" * 72)
    return "\n".join(L)


# ---------- 主流程 ----------

def one_round(state, mode):
    t = time.time()
    arms = scan_all_arms(state, t)
    plan = scan_plan_tiers()
    sched = scan_scheduler(state, t)
    extras = scan_extra_schedulers(t)
    anolis = scan_anolis(state, t)
    anolis["local_sweb_images"] = scan_local_images(state, t)
    relay = scan_relay()
    archived, _active = classify_archived(arms, sched, extras, t)
    alarms = build_alarms(arms, sched, anolis, relay, plan, state, t, extras, archived)
    snap = build_snapshot(arms, plan, sched, anolis, relay, alarms, mode, extras, archived)

    write_atomic(LATEST, json.dumps(snap, ensure_ascii=False, indent=1))
    write_atomic(DASH_DATA, json.dumps(snap, ensure_ascii=False))
    if mode == "daemon":
        log_alarms(alarms, state, t)
        # 采样历史推进（保留窗）
        state["line_hist"].append([int(t), {a["dir"]: a["n_total"] for a in arms}])
        state["line_hist"] = [s for s in state["line_hist"] if t - s[0] <= 2400]
    save_state(state)
    return snap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="单轮扫描并打印巡检报告")
    args = ap.parse_args()
    os.makedirs(OBS_DIR, exist_ok=True)
    os.makedirs(DASH_DIR, exist_ok=True)
    state = load_state()
    if args.once:
        snap = one_round(state, "once")
        print(render_report(snap))
        return
    write_atomic(f"{OBS_DIR}/watchdog.pid", f"{os.getpid()}\n")
    print(f"[{now_s()}] factory-watch 常驻启动 pid={os.getpid()} 周期 {INTERVAL}s", flush=True)
    while True:
        try:
            snap = one_round(state, "daemon")
            n_red = sum(1 for x in snap["alarms"] if x["level"] == "red")
            n_amb = sum(1 for x in snap["alarms"] if x["level"] == "amber")
            print(f"[{now_s()}] 轮完成: 行 {snap['totals']['n_total']} "
                  f"(+{snap['totals']['rows_10m']}/10min) 安灯 红{n_red} 黄{n_amb}",
                  flush=True)
        except Exception as e:
            print(f"[{now_s()}] 轮异常（不退出）: {e}", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
