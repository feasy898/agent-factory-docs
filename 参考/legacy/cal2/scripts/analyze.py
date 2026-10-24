#!/usr/bin/env python3
"""Aggregate cal2 results from anolis (official + judged-local lanes) and compare with A5 predictions.

Usage: python3 analyze.py [--pull]
  --pull: rsync the per-config result dirs from anolis into cal2/results-anolis/ first.
"""
import json
import os
import subprocess
import sys

ROOT = "/home/pan-ding/workspace/临时工作区/temp1"
CAL = os.path.join(ROOT, "cal2")
TASKS = [l.strip() for l in open(os.path.join(CAL, "tasks.txt")) if l.strip()]

CONFIGS = [
    # (config, harness, model, arm, A5 predicted pass-rate band, local results dir name)
    ("cal2-mcode-m3",    "mcode",  "MiniMax-M3",                 "强臂候选",   (0.65, 0.82), None),
    ("cal2-mcode-m31f",  "mcode",  "MiniMax-M3.1-Flash-Preview", "flash 臂",   (0.50, 0.68), None),
    ("cal2-step-s5",     "step",   "step-5-preview",             "强臂候选",   (0.60, 0.78), None),
    ("cal2-step-router", "step",   "step-router-v1",             "路由竞争臂", (0.55, 0.78), None),
    ("cal2-kimi-k28",    "kimi",   "kimi-for-coding (K2.8)",     "中臂候选",   (0.55, 0.75), None),
    ("zcode-m3",         "zcode-wf", "MiniMax-M3",               "强臂候选",   (0.65, 0.82), None),
    ("zcode-m31f",       "zcode-wf", "MiniMax-M3.1-Flash-Preview", "flash 臂", (0.50, 0.68), None),
    ("zcode-s5",         "zcode-wf", "step-5-preview",           "强臂候选",   (0.60, 0.78), None),
    ("zcode-router",     "zcode-wf", "step-router-v1",           "路由竞争臂", (0.55, 0.78), None),
    ("cal2-grok47",      "grok",     "grok-4.7",                 "强臂候选",   (0.60, 0.86), None),
    ("zcode-glm53",  "zcode-wf", "GLM-5.3",                  "新增-未预登记", None, None),
    ("zcode-glm53f", "zcode-wf", "GLM-5.3-Flash",            "新增-未预登记", None, None),
    ("zcode-step37f", "zcode-wf", "Step3.7-Flash",           "新增-未预登记", None, None),
    ("zcode-glm53f-r2","zcode-wf", "GLM-5.3-Flash·复现",      "复现验证",     None, None),
    ("zcode-m31f-r2",  "zcode-wf", "M3.1-Flash·复现",         "复现验证",     None, None),
]
PREV = {  # previous round (bench-2026-10-12, sess_aa3db26b) official-harness pass rates
    "cal2-mcode-m3": 0.588, "cal2-mcode-m31f": 0.765, "cal2-step-s5": 0.706,
    "cal2-kimi-k28": 0.784,
}


def pull():
    for cfg, *_x in CONFIGS:
        dst = os.path.join(CAL, "results-anolis", cfg)
        os.makedirs(dst, exist_ok=True)
        subprocess.run(["rsync", "-a", f"anolis:/home/pan-ding/bench/results/{cfg}/", dst + "/"],
                       capture_output=True, timeout=120)


def load(cfg, local_name=None):
    out = {}
    bases = [os.path.join(CAL, "results-anolis", local_name or cfg)]
    for base in bases:
        if not os.path.isdir(base):
            continue
        for f in os.listdir(base):
            if not f.endswith(".json") or f in ("declarations.json", "audit.json"):
                continue
            try:
                d = json.load(open(os.path.join(base, f)))
            except Exception:
                continue
            out[f[:-5]] = d.get("status", "?")
    return out


def main():
    if "--pull" in sys.argv:
        pull()
    print(f"{'config':<18} {'harness':<9} {'pass':>4} {'fail':>4} {'infra':>5} {'excl':>4} {'done':>5} {'rate':>7}  {'A5 band':<10} {'prev':>6}")
    summary = {}
    for cfg, h, model, arm, band, local in CONFIGS:
        res = load(cfg, local)
        npass = sum(1 for v in res.values() if v == "pass")
        nfail = sum(1 for v in res.values() if v == "fail")
        ninfra = sum(1 for v in res.values() if v == "infra")
        nexc = sum(1 for v in res.values() if v == "excluded")
        nquota = sum(1 for v in res.values() if v == "quota")
        done = len(res)
        counted = npass + nfail
        rate = npass / counted if counted else 0.0
        summary[cfg] = dict(pass_=npass, fail=nfail, infra=ninfra, excluded=nexc, quota=nquota, done=done, rate=rate,
                            band=band, prev=PREV.get(cfg))
        print(f"{cfg:<18} {h:<9} {npass:>4} {nfail:>4} {ninfra:>5} {nexc:>4} {done:>5} {rate*100:>6.1f}%  "
              f"{('%d-%d%%' % (band[0]*100, band[1]*100)) if band else '—':<10}  {('%.1f%%' % (PREV[cfg]*100)) if cfg in PREV else '-':>6}")
    with open(os.path.join(CAL, "results", "summary.json"), "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    # per-task matrix
    print("\nper-task (p=pass f=fail i=infra .=not run):")
    hdr = "task".ljust(34) + "".join(c.replace("cal2-", "").ljust(15) for c, *_ in CONFIGS)
    print(hdr)
    loaded = {cfg: load(cfg, local) for cfg, _h, _m, _a, _b, local in CONFIGS}
    for t in TASKS:
        row = t.ljust(34)
        for cfg, *_ in CONFIGS:
            v = loaded[cfg].get(t)
            row += {"pass": "p", "fail": "f", "infra": "i", "quota": "q"}.get(v, ".").ljust(15)
        print(row)



    # difficulty stratification
    try:
        diff = json.load(open(os.path.join(CAL, "tasks-difficulty.json")))
        print("\n--- difficulty stratification (pass/done) ---")
        print(f"{'config':<18} {'easy':>12} {'medium':>12} {'hard':>12}")
        for cfg, h, model, arm, band, local in CONFIGS:
            res = loaded[cfg]
            cells = []
            for d in ("easy", "medium", "hard"):
                ts = [t for t in TASKS if diff.get(t) == d]
                p = sum(1 for t in ts if res.get(t) == "pass")
                n = sum(1 for t in ts if t in res)
                cells.append(f"{p}/{n}" + (f"={p/n*100:.0f}%" if n else ""))
            print(f"{cfg:<18} {cells[0]:>12} {cells[1]:>12} {cells[2]:>12}")
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    main()
