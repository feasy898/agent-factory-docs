#!/usr/bin/env python3
"""sc3_fix_p31base.py — SC3 修正包：
1. sc3.json base 池补 7 道 p31 族题（否则 p31 配对 n=5 insufficient）
2. 重生成 21 个新 base job 目录
3. jobs-m31.txt 追加 21 base + 9 CHAIN；jobs-driver.txt 移除 CHAIN（防双车道重跑）
4. sc3_wrap.py 的 p31_chain 按题分派引擎（7 独有题→mcode，5 与 base 重叠题→zcode，块一致）
5. jobs-sc3.txt 重算（+21）
"""
import json, os, subprocess

SC = "/home/pan-ding/campaign-sc"
ROOT = SC + "/sc3"
UNIQUE = ["feal-linear-cryptanalysis", "feal-differential-cryptanalysis", "regex-log",
          "jq-data-processing", "countdown-game", "huarong-dao-solver", "puzzle-solver"]

# 1) wave json
wp = SC + "/sc3.json"
wave = json.load(open(wp, encoding="utf-8"))
base = wave["tasks_by_arm"]["base"]
added = [t for t in UNIQUE if t not in base]
wave["tasks_by_arm"]["base"] = base + added
json.dump(wave, open(wp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("base pool += %d -> %d tasks" % (len(added), len(wave["tasks_by_arm"]["base"])))

# 2) 新 base job 目录
n = 0
for t in added:
    for r in (1, 2, 3):
        d = os.path.join(ROOT, "runs", "base", "%s-r%d" % (t, r))
        w, pf = os.path.join(d, "work"), os.path.join(d, "prompt.txt")
        if not os.path.isdir(w) or not os.listdir(w):
            os.makedirs(w, exist_ok=True)
            subprocess.run(["python3", "/home/pan-ding/bench/scripts/prepare_task.py",
                            "/home/pan-ding/bench/tasks/" + t, w, pf], capture_output=True)
            n += 1
print("new base job dirs prepared: %d" % n)

# 3) 清单
m31 = [l.strip() for l in open(ROOT + "/jobs-m31.txt") if l.strip()]
for t in added:
    for r in (1, 2, 3):
        j = "base/%s-r%d" % (t, r)
        if j not in m31:
            m31.append(j)
for fam in wave["p31_families"]:
    for r in (1, 2, 3):
        j = "p31-skill-library/CHAIN-%s-r%d" % (fam, r)
        if j not in m31:
            m31.append(j)
open(ROOT + "/jobs-m31.txt", "w").write("\n".join(m31) + "\n")

drv = [l.strip() for l in open(ROOT + "/jobs-driver.txt") if l.strip()]
drv = [j for j in drv if not j.startswith("p31-skill-library/CHAIN-")]
open(ROOT + "/jobs-driver.txt", "w").write("\n".join(drv) + "\n")

alljobs = []
for arm in wave["arms"]:
    for t in wave["tasks_by_arm"][arm]:
        for r in (1, 2, 3):
            alljobs.append("%s/%s-r%d" % (arm, t, r))
open(ROOT + "/jobs-sc3.txt", "w").write("\n".join(sorted(alljobs)) + "\n")
print("jobs-m31: %d, jobs-driver: %d, jobs-sc3(real): %d" % (len(m31), len(drv), len(alljobs)))

# 4) p31_chain 引擎分派补丁
src = open(SC + "/scripts/sc3_wrap.py", encoding="utf-8").read()
if "M31_TASKS" not in src:
    anchor = "def p31_chain(fam, rep):"
    inject = """M31_TASKS = set(%r)

def p31_chain(fam, rep):""" % UNIQUE
    assert anchor in src
    src = src.replace(anchor, inject)
    old_call = """            rc = subprocess.run(["timeout", "-k", "60", str(SOLVE_TO)] + engine_args(prompt, w),
                                stdout=lf, stderr=subprocess.STDOUT).returncode"""
    new_call = """            if t in M31_TASKS:
                if BACKEND != "m31":
                    old = BACKEND; _switch("m31")
                args = engine_args(prompt, w)
                if BACKEND != "m31":
                    _switch(old)
            else:
                if BACKEND != "glm":
                    old = BACKEND; _switch("glm")
                args = engine_args(prompt, w)
                if BACKEND != "glm":
                    _switch(old)
            rc = subprocess.run(["timeout", "-k", "60", str(SOLVE_TO)] + args,
                                stdout=lf, stderr=subprocess.STDOUT).returncode"""
    assert old_call in src
    src = src.replace(old_call, new_call)
    # _switch 帮助函数：改 BACKEND/QUOTA/MODEL/ENGINE 与 engine_args 指向
    helper = '''
def _switch(eng):
    global BACKEND, QUOTA, MODEL, ENGINE, engine_args
    BACKEND = eng
    if eng == "m31":
        QUOTA = os.path.join(SC, "QUOTA_M31")
        MODEL = "minimax/MiniMax-M3.1-Flash-Preview"
        ENGINE = os.path.expanduser("~/.npm-global/bin/mcode")
        def engine_args(prompt, cwd, _e=ENGINE, _m=MODEL):
            return [_e, "exec", "--cwd", cwd, "--model", _m, "--permission", "full", "--timeout", "25m", prompt]
    else:
        QUOTA = os.path.join(SC, "QUOTA_GLM")
        MODEL = "account:bigmodel-individual-coding-plan/GLM-5.3-Flash"
        ENGINE = os.path.expanduser("~/.npm-global/bin/zcode")
        def engine_args(prompt, cwd, _e=ENGINE, _m=MODEL):
            return [_e, "-p", prompt, "--cwd", cwd, "--mode", "yolo", "--model", _m]

'''
    src = src.replace("\ndef run_rollout(", helper + "def run_rollout(")
    open(SC + "/scripts/sc3_wrap.py", "w", encoding="utf-8").write(src)
    print("sc3_wrap.py patched (per-task engine dispatch)")
else:
    print("sc3_wrap.py already patched")
