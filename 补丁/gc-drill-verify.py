#!/usr/bin/env python3
"""gc-drill-verify.py — §6.4 缺口 1：补丁③ gc_watch 真实端到端 spawn 复验（fix1+换血后）。

P0-2/P0-4 零变异 drill 协议（方案 §5 / state §9 先例）：真 keepalive 模块、真 gc_watch()、
真 spawn() 机制（setsid/日志重定向/真实子进程 python3 tools/img-gc.py），仅两处测试包装：
  1. 触发水位用沙箱合成 latest.json（use_pct=86：≥85 触发线、<88 停手线——真实 /data 73%
     本就不该触发，绝不人为改生产 latest.json）；
  2. spawn argv 断言新序后 apply→plan 替换（plan=只读盘点，零 rmi）。
其余全部真实路径：子进程写真实证据件（kind=plan 审计追加，J3 先例）与真实 /tmp/img-gc.log。
keepalive 侧 KLOG/ALARMS_LOG/证据路径重定向沙箱，生产 alarms.log/keepalive.log 零写入。
输出落 /tmp/gcdrill.out。
"""
import importlib.util
import json
import os
import shutil
import sys
import time

WS = "/home/pan-ding/workspace/agent黑灯工厂"
OUT = "/tmp/gcdrill.out"
LINES = []


def say(s=""):
    LINES.append(str(s))
    print(s, flush=True)


spec = importlib.util.spec_from_file_location("fk_drill", f"{WS}/tools/factory-keepalive.py")
md = importlib.util.module_from_spec(spec)
spec.loader.exec_module(md)

SB = "/tmp/gcdrill-sandbox"
shutil.rmtree(SB, ignore_errors=True)
os.makedirs(SB)
# keepalive 侧写路径全部重定向沙箱
md.KLOG = f"{SB}/keepalive.log"
md.ALARMS_LOG = f"{SB}/alarms.log"
md.GC_EVIDENCE = f"{SB}/img-gc-evidence.jsonl"
md.GC_EVIDENCE_TMP = f"{SB}/img-gc-evidence-tmp.jsonl"
shutil.copy(f"{WS}/状态观测/img-gc-evidence.jsonl", md.GC_EVIDENCE)  # 真实历史作迟滞/去重基准
# 触发水位合成：86（≥85 触发、<88 停手线）；mtime 天然新鲜
with open(md.LATEST_JSON, encoding="utf-8") as f:
    real_latest = json.load(f)
syn = json.loads(json.dumps(real_latest))
syn.setdefault("anolis", {}).setdefault("disk", {}).setdefault("/data", {})["use_pct"] = 86
with open(f"{SB}/latest.json", "w", encoding="utf-8") as f:
    json.dump(syn, f, ensure_ascii=False)
md.LATEST_JSON = f"{SB}/latest.json"
md.last_gc_spawn = 0.0  # 防抖复位（新进程语义）

# 生产面 before 基线
def wc(path):
    try:
        return sum(1 for _ in open(path, encoding="utf-8"))
    except OSError:
        return 0

ev_tmp_before = wc("/tmp/img-gc-evidence.jsonl")
ev_dur_before = wc(f"{WS}/状态观测/img-gc-evidence.jsonl")
gclog_before = wc("/tmp/img-gc.log")
say(f"before: /tmp/img-gc-evidence={ev_tmp_before}行 耐久证据={ev_dur_before}行 /tmp/img-gc.log={gclog_before}行")

# 真 spawn 包装：断言新序 argv（P0-4 第 4 条核心）+ apply→plan 零变异替换 + 调真 spawn
real_spawn = md.spawn
proof = {}

def spy_spawn(name, cmd, logfile, extra_env=None, strip_env=()):
    proof["name"], proof["cmd"], proof["logfile"] = name, list(cmd), logfile
    assert name == "gc-watch", name
    assert cmd == ["python3", "tools/img-gc.py", "apply", "--host", "anolis"], f"argv 非新序: {cmd}"
    drill_cmd = ["python3", "tools/img-gc.py", "plan", "--host", "anolis"]  # 零变异
    pid = real_spawn(name, drill_cmd, logfile, extra_env, strip_env)
    proof["pid"] = pid
    return pid

md.spawn = spy_spawn
t0 = time.time()
md.gc_watch()
wall_ms = int((time.time() - t0) * 1000)
say(f"gc_watch() 返回 wall={wall_ms}ms（非阻塞口径应 <<1200s 防抖窗）")
say(f"spawn 捕获: name={proof.get('name')} argv={proof.get('cmd')} logfile={proof.get('logfile')}")
ok_argv = proof.get("cmd") == ["python3", "tools/img-gc.py", "apply", "--host", "anolis"] \
    and proof.get("name") == "gc-watch" and proof.get("logfile") == "/tmp/img-gc.log"

# 等真实子进程退出（setsid 脱离，poll /proc）
pid = proof.get("pid")
deadline = time.time() + 180
while pid and time.time() < deadline and os.path.exists(f"/proc/{pid}"):
    time.sleep(1)
child_gone = (not pid) or (not os.path.exists(f"/proc/{pid}"))
say(f"子进程 pid={pid} 已退出={child_gone}（等待 {int(time.time()-t0)-wall_ms if wall_ms else 0}s+）")

time.sleep(1)
ev_tmp_after = wc("/tmp/img-gc-evidence.jsonl")
ev_dur_after = wc(f"{WS}/状态观测/img-gc-evidence.jsonl")
gclog_after = wc("/tmp/img-gc.log")
say(f"after: /tmp/img-gc-evidence={ev_tmp_after}行 耐久证据={ev_dur_after}行 /tmp/img-gc.log={gclog_after}行")
new_ev = open("/tmp/img-gc-evidence.jsonl", encoding="utf-8").read().splitlines()[ev_tmp_before:]
new_ev_dur = open(f"{WS}/状态观测/img-gc-evidence.jsonl", encoding="utf-8").read().splitlines()[ev_dur_before:]
say(f"新增证据行(现场)={new_ev}")
say(f"新增证据行(耐久)={new_ev_dur}")
new_gclog = open("/tmp/img-gc.log", encoding="utf-8").read().splitlines()[gclog_before:]
argparse_bad = [l for l in new_gclog if "invalid choice" in l or "argparse" in l]
say(f"新日志段={len(new_gclog)}行 argparse 错误行={argparse_bad}")
say(f"新日志段前 12 行预览: {[l[:80] for l in new_gclog[:12]]}")
klog_sbx = open(md.KLOG, encoding="utf-8").read().strip().splitlines()
say(f"沙箱 keepalive.log（gc-watch klog）: {klog_sbx}")

verdict = (ok_argv and child_gone and wall_ms < 2000
           and len(new_ev) == 1 and json.loads(new_ev[0]).get("kind") == "plan"
           and len(new_ev_dur) == 1 and json.loads(new_ev_dur[0]).get("kind") == "plan"
           and not argparse_bad and len(new_gclog) > 0)
say("")
say("DRILL VERDICT: " + ("PASS（真 spawn 机制端到端：新序 argv 断言过 / 零变异 plan 子进程正常退出 / "
                       "双证据件各 +1 行 kind=plan / 新日志段无 argparse rc2）" if verdict else "FAIL"))
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(LINES) + "\n")
shutil.rmtree(SB, ignore_errors=True)
sys.exit(0 if verdict else 1)
