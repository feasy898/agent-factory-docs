#!/usr/bin/env python3
"""补丁③ 单测：img-gc.py 闸语义 + keepalive gc_watch 触发/去重（mock 层）。

边界：全部 ssh/docker 走 stub，不碰两机 docker；keepalive 的 latest/alarms/证据
重定向到 /tmp/md-patch3-test/ 沙箱；对 anolis 仅 test1 用真实 ssh 跑只读 plan。
运行: python3 补丁/patch3-test-imggc.py   （退出码 0=全过，1=有 FAIL）
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import time
from unittest import mock

WS = "/home/pan-ding/workspace/agent黑灯工厂"
SB = "/tmp/md-patch3-test"
shutil.rmtree(SB, ignore_errors=True)   # 强制新沙箱（防上轮残留污染去重/迟滞判定）
os.makedirs(SB, exist_ok=True)

spec = importlib.util.spec_from_file_location("img_gc", f"{WS}/tools/img-gc.py")
ig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ig)

spec2 = importlib.util.spec_from_file_location(
    "factory_keepalive", f"{WS}/tools/factory-keepalive.py")
fk = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(fk)

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append(cond)
    print(f"{'PASS' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail else ""))


# ---- T1 host 断言（真实子进程，argparse 后立即拒绝，无任何 docker/ssh）----
r = subprocess.run([sys.executable, f"{WS}/tools/img-gc.py", "plan", "--host", "pandev"],
                   capture_output=True, text=True)
check("T1a --host pandev 被 SystemExit 拒绝", r.returncode != 0 and "anolis" in (r.stderr + r.stdout),
      f"rc={r.returncode}")
r = subprocess.run([sys.executable, f"{WS}/tools/img-gc.py", "apply", "--host", "localhost"],
                   capture_output=True, text=True)
check("T1b --host localhost 被 SystemExit 拒绝", r.returncode != 0)

# ---- T2 任务→镜像名 ----
img, fb = ig.task_image("pydata__xarray-2905")
check("T2a 真实 task json image 字段（非 tid 替换）",
      img == "swebench/sweb.eval.x86_64.pydata_1776_xarray-2905:latest" and fb is False, img)
img, fb = ig.task_image("fakerepo__fake-task-1")
check("T2b 缺 json fallback=_1776_ 拼法+旗标",
      img == "swebench/sweb.eval.x86_64.fakerepo_1776_fake-task-1:latest" and fb is True, img)

# ---- T3 白名单 ----
check("T3a 连字符仓段命中", bool(ig.WHITELIST.match(
    "swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8548:latest")))
check("T3b 非本厂镜像拒之门外",
      not ig.WHITELIST.match("ollama/minimax:latest")
      and not ig.WHITELIST.match("af-factory:latest")
      and not ig.WHITELIST.match("<none>:<none>"))

# ---- T4 集合运算不变量 ----
inv = ["swebench/sweb.eval.x86_64.psf_1776_requests-1724:latest",
       "swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8548:latest",
       "ollama/minimax:latest", "<none>:<none>"]
keep = ["swebench/sweb.eval.x86_64.psf_1776_requests-1724:latest"]
delete, foreign = ig.split_inventory(inv, keep)
check("T4a 删集∩保留集=∅", not (set(delete) & set(keep)))
check("T4b 删集 100% 白名单内", all(ig.WHITELIST.match(i) for i in delete) and
      delete == ["swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8548:latest"])
check("T4c foreign 只计数永不删", foreign == ["<none>:<none>", "ollama/minimax:latest"])

# ---- T5 三源保留集（真实本地数据，只读）----
keep, parts, meta, err = ig.gather_keep()
check("T5a 三源无失败", err is None, f"err={err}")
check("T5b C源含 running relay 镜像", len(parts["C"]) >= 6,
      f"C={len(parts['C'])} A={len(parts['A'])} B={len(parts['B'])}")
# T5c 前置条件入断言（§6.4 缺口 9 修复：终审 34/35 vs 35/35 假阴性根因）——
# 严格 1:1 比对仅在 mcode 在途非空时有意义；在途=0（收官）时 B 源应为空。
_mcodestate = {}
try:
    _mcodestate = json.load(open("/tmp/mcode-dispatch/state.json"))
except Exception:
    pass
_mcode_inflight = sum(1 for _e in _mcodestate.values()
                      if isinstance(_e, dict) and _e.get("phase") not in ("judged",))
check("T5c B源与在途任务一一对应（前置：mcode 在途非空才严格比对；在途=0 收官时 B 应为空）",
      (len(parts["B"]) == 0) if _mcode_inflight == 0 else
      (len(parts["B"]) == len(set(meta.get("B_tids") or []))
       and all(ig.WHITELIST.match(i) for i in parts["B"])),
      f"前置 in-flight={_mcode_inflight} B={len(parts['B'])} "
      f"tids={len(set(meta.get('B_tids') or []))}")

# ---- T6 TOCTOU ancestor / HALT（stub ssh）----
with mock.patch.object(ig, "ssh_docker", lambda *a, **k: (True, "abc123\n", "")):
    check("T6a ancestor 有容器=busy", ig.ancestor_busy("x") is True)
with mock.patch.object(ig, "ssh_docker", lambda *a, **k: (True, "", "")):
    check("T6b ancestor 空=可删", ig.ancestor_busy("x") is False)
with mock.patch.object(ig, "ssh_docker", lambda *a, **k: (False, "", "ssh 闪断")):
    check("T6c ancestor 判不准=拒删（fail-closed）", ig.ancestor_busy("x") is True)


class FakeCP:
    def __init__(self, rc):
        self.returncode = rc


with mock.patch.object(ig, "ssh_run", lambda *a, **k: FakeCP(0)):
    check("T7a HALT 在场=True", ig.halt_present() is True)
with mock.patch.object(ig, "ssh_run", lambda *a, **k: FakeCP(1)):
    check("T7b HALT 不在=False", ig.halt_present() is False)
with mock.patch.object(ig, "ssh_run", lambda *a, **k: (_ for _ in ()).throw(Exception("超时"))):
    check("T7c HALT 判不准=None（拒）", ig.halt_present() is None)

# ---- T8 apply 拒绝/执行路径（全 mock，证据入沙箱）----
ig.EVIDENCE_TMP = f"{SB}/ev.jsonl"
ig.EVIDENCE_DURABLE = f"{SB}/ev-durable.jsonl"
for p in (ig.EVIDENCE_TMP, ig.EVIDENCE_DURABLE):
    if os.path.exists(p):
        os.remove(p)


def fake_ssh_docker_factory(rmi_fail=(), ancestor_busy_imgs=(), prune_fail=False):
    INV = ("swebench/sweb.eval.x86_64.psf_1776_requests-1724:latest\n"
           "swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8548:latest\n"
           "swebench/sweb.eval.x86_64.sympy_1776_sympy-19783:latest\n"
           "swebench/sweb.eval.x86_64.pylint-dev_1776_pylint-4661:latest\n"
           "ollama/minimax:latest\n")

    def fake(args, retries=1, wait=15, timeout=60):
        if args[:1] == ["images"]:
            return True, INV, ""
        if args[:1] == ["ps"]:
            flt = [a for a in args if a.startswith("ancestor=")]
            if not flt:                      # docker ps --format（在飞盘点）
                return True, "swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8548:latest\n", ""
            img = flt[0].split("=", 1)[1]    # docker ps -q --filter ancestor=X
            busy = "sympy" in img or img in ancestor_busy_imgs
            return (True, "abc\n" if busy else "", "")
        if args[:2] == ["rmi"]:
            return (args[1] not in rmi_fail, "", "" if args[1] not in rmi_fail else "used by container")
        if args[:2] == ["builder", "prune"]:
            return (not prune_fail, "3.9GB", "")
        return True, "", ""
    return fake


base_env = {"data_use_pct": lambda: (63, None), "halt_present": lambda: False,
            "gather_keep": lambda: (
                ["swebench/sweb.eval.x86_64.psf_1776_requests-1724:latest",
                 "swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8548:latest"],
                {"A": ["swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8548:latest"],
                 "B": ["swebench/sweb.eval.x86_64.psf_1776_requests-1724:latest"], "C": []},
                {"B_tids": ["psf__requests-1724"], "B_fallback": None,
                 "C_fallback": None, "C_notes": [], "errors": []}, None),
            "acquire_lock": lambda: object()}

# T8a HALT 拒绝
env_a = dict(base_env)
env_a["halt_present"] = lambda: True
with mock.patch.multiple(ig, ssh_docker=fake_ssh_docker_factory(), **env_a):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ig.cmd_apply(None)
    ev = [json.loads(l) for l in open(ig.EVIDENCE_DURABLE)]
    check("T8a HALT 在场 apply 必拒", ev[-1]["ok"] is False and "HALT" in ev[-1]["reason"]
          and "results" not in ev[-1] and "deleted" not in ev[-1])
    os.remove(ig.EVIDENCE_TMP) if os.path.exists(ig.EVIDENCE_TMP) else None
    os.remove(ig.EVIDENCE_DURABLE)

# T8b fail-closed 拒绝
env_b = dict(base_env)
env_b["gather_keep"] = lambda: (None, {"A": [], "B": [], "C": []},
                                {"errors": ["x"]}, "state 读取失败")
with mock.patch.multiple(ig, ssh_docker=fake_ssh_docker_factory(), **env_b):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ig.cmd_apply(None)
    ev = [json.loads(l) for l in open(ig.EVIDENCE_DURABLE)]
    check("T8b 保留集源失败=只出 plan 不 apply", ev[-1]["ok"] is False
          and "fail-closed" in ev[-1]["reason"] and ev[-1]["delete"] == [])
    os.remove(ig.EVIDENCE_TMP) if os.path.exists(ig.EVIDENCE_TMP) else None
    os.remove(ig.EVIDENCE_DURABLE)

# T8c ≥88 停手
env_c = dict(base_env)
env_c["data_use_pct"] = lambda: (90, None)
with mock.patch.multiple(ig, ssh_docker=fake_ssh_docker_factory(), **env_c):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ig.cmd_apply(None)
    ev = [json.loads(l) for l in open(ig.EVIDENCE_DURABLE)]
    check("T8c use_pct 90≥88 停手回报", ev[-1]["ok"] is False and "停手" in ev[-1]["reason"])
    os.remove(ig.EVIDENCE_TMP) if os.path.exists(ig.EVIDENCE_TMP) else None
    os.remove(ig.EVIDENCE_DURABLE)

# T8d 正常路径：TOCTOU 三重 + rmi 失败不重试 + builder prune
calls = []


def counting_ancestor(img):
    calls.append(("ancestor", img))
    return "sympy" in img   # sympy=在飞容器镜像 → ancestor 避让；pylint 可删


env_d = dict(base_env)
env_d["ancestor_busy"] = counting_ancestor
with mock.patch.multiple(ig, ssh_docker=fake_ssh_docker_factory(rmi_fail=("ollama-x",)),
                         **env_d):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ig.cmd_apply(None)
    ev = [json.loads(l) for l in open(ig.EVIDENCE_DURABLE)]
    last = ev[-1]
    check("T8d1 apply 完成 ok=True（sympy ancestor 避让、pylint 删除）",
          last["ok"] is True and last["deleted"] == 1 and last["skipped_ancestor"] == 1
          and sorted(r["status"] for r in last["results"]) ==
          ["deleted", "skipped-ancestor-busy"]
          and last["results"][0]["image"].endswith("pylint-4661:latest"))
    check("T8d2 A源在飞镜像被保留（ancestor 避让）",
          all(r["image"] != "swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8548:latest"
              or r["status"].startswith("skipped") for r in last["results"]))
    check("T8d3 结果状态合法且 rmi 每张至多一次",
          all(r["status"] in ("deleted", "rmi-fail", "skipped-ancestor-busy")
              for r in last["results"]))
    check("T8d4 builder prune 执行", "builder_prune" in last)
    check("T8d5 use_pct_after 回填", last.get("use_pct_after") == 63)

# 证据双写一致性（T8d 留下的）
tmp_lines = open(ig.EVIDENCE_TMP).read()
dur_lines = open(ig.EVIDENCE_DURABLE).read()
check("T8e 双写逐行一致", tmp_lines == dur_lines and len(tmp_lines) > 0)

# ---- T9 keepalive gc_watch：触发/防抖/A9 去重 ----
fk.LATEST_JSON = f"{SB}/latest.json"
fk.GC_EVIDENCE = f"{SB}/evk.jsonl"
fk.GC_EVIDENCE_TMP = f"{SB}/evk-tmp.jsonl"
fk.ALARMS_LOG = f"{SB}/alarms.log"
fk.KLOG = f"{SB}/keepalive.log"   # klog 文件侧进沙箱（防伪造行泄入生产 keepalive 日志）
SPAWNED = []
fk.spawn = lambda name, cmd, logf, extra_env=None, strip_env=(): SPAWNED.append((name, cmd)) or 12345
now = time.time()
json.dump({"anolis": {"disk": {"/data": {"use_pct": 90}}}}, open(fk.LATEST_JSON, "w"))
fk.append_gc_evidence({"kind": "apply", "ts": "x", "epoch": int(now - 7 * 3600),
                       "ok": True, "deleted": 3, "rmi_fail": 0,
                       "use_pct": 88, "use_pct_after": 55})
fk.last_gc_spawn = 0.0
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    fk.gc_watch(dry=False)
# T9a 精确 argv 序断言（J3 回归网：--host 归子解析器，子命令必须在前；
# 旧序「--host anolis apply」100% 死于 argparse rc2 且零证据）
check("T9a ≥85 且 >6h → spawn apply（argv 精确序）",
      len(SPAWNED) == 1 and SPAWNED[0][1] ==
      ["python3", "tools/img-gc.py", "apply", "--host", "anolis"],
      f"spawned={SPAWNED}")
check("T9b A9 报警进 alarms.log（amber）", "gc-watch" in open(fk.ALARMS_LOG).read()
      and '"level": "amber"' in open(fk.ALARMS_LOG).read())
evk = [json.loads(l) for l in open(fk.GC_EVIDENCE)]
check("T9c 去重时间戳记回耐久证据", any(r["kind"] == "gc-alarm-sent" for r in evk))
n_alarms = len(open(fk.ALARMS_LOG).readlines())
# 注意：不清 last_gc_spawn——同窗内防抖应同时压制重复 spawn 与重复报警
with contextlib.redirect_stdout(io.StringIO()):
    fk.gc_watch(dry=False)
check("T9d 30min 去重：不重复报警", len(open(fk.ALARMS_LOG).readlines()) == n_alarms)
check("T9e spawn 防抖（1200s 内不重复 spawn）", len(SPAWNED) == 1)

# use_pct<85 不触发
json.dump({"anolis": {"disk": {"/data": {"use_pct": 62}}}}, open(fk.LATEST_JSON, "w"))
fk.last_gc_spawn = 0.0
SPAWNED.clear()
with contextlib.redirect_stdout(io.StringIO()):
    fk.gc_watch(dry=False)
check("T9f 62%<85 不 spawn", SPAWNED == [])
# 6h 迟滞内不触发
json.dump({"anolis": {"disk": {"/data": {"use_pct": 90}}}}, open(fk.LATEST_JSON, "w"))
fk.append_gc_evidence({"kind": "apply", "ts": "y", "epoch": int(now - 1 * 3600), "ok": True,
                       "deleted": 1, "rmi_fail": 0, "use_pct": 86, "use_pct_after": 80})
fk.last_gc_spawn = 0.0
SPAWNED.clear()
with contextlib.redirect_stdout(io.StringIO()):
    fk.gc_watch(dry=False)
check("T9g 距上次成功GC<6h 不 spawn", SPAWNED == [])
# latest.json 断供（mtime 400s）不触发
os.utime(fk.LATEST_JSON, (now - 400, now - 400))
fk.append_gc_evidence({"kind": "apply", "ts": "z", "epoch": int(now - 9 * 3600), "ok": True,
                       "deleted": 1, "rmi_fail": 0, "use_pct": 86, "use_pct_after": 80})
fk.last_gc_spawn = 0.0
SPAWNED.clear()
with contextlib.redirect_stdout(io.StringIO()):
    fk.gc_watch(dry=False)
check("T9h latest.json 过期（watch 断供）不 spawn", SPAWNED == [])

print(f"\n{'ALL PASS' if all(RESULTS) else 'HAS FAILURES'} ({sum(RESULTS)}/{len(RESULTS)})")
sys.exit(0 if all(RESULTS) else 1)
