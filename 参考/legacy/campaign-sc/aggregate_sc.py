#!/usr/bin/env python3
"""aggregate_sc.py <wave_root> <wave.json> — SC 波次聚合统计。

口径（与复测战役设计书统一统计协议一致）：
- 每 (arm, task)：reps 通过率 p = pass数/已判rep数；any = 至少1次pass；both = 全部rep都pass。
- pairedΔ = 该技术臂任务集上 mean(p_arm - p_base)（逐题配对，仅统计两臂都已判分的题）
- anyΔ / bothΔ 同理；flips = p_arm > p_base 的题数；regress = p_arm < p_base 的题数。
- 判定：candidate: pairedΔ>=+10pp 且 bothΔ>=0 且 regress<=1；reject: pairedΔ<=-15pp 且 flips=0；其余 neutral。
输出 JSON + 终端表格。
"""
import json
import os
import sys
import collections

root, wave_path = sys.argv[1], sys.argv[2]
wave = json.load(open(wave_path, encoding="utf-8"))
tasks_by_arm = wave["tasks_by_arm"]

res = {}
for f in os.listdir(os.path.join(root, "results")):
    if not f.endswith(".json") or "__" not in f:
        continue
    tag = f[:-5]
    arm, job = tag.split("__", 1)
    task = job.rsplit("-r", 1)[0]
    try:
        status = json.load(open(os.path.join(root, "results", f))).get("status")
    except Exception:
        status = "badjson"
    res[(arm, task, job)] = status

arms = list(wave["arms"])
out = {"wave": wave.get("name"), "arms": {}, "n_results": len(res)}
table = []
for arm in arms:
    tasks = tasks_by_arm[arm]
    rows = []
    for t in tasks:
        for a2 in ("base", arm):
            pass
        def stats(a):
            ss = [res.get((a, t, t + "-r%d" % r)) for r in (1, 2, 3)]
            ss = [s for s in ss if s is not None]
            if not ss:
                return None
            npass = sum(1 for s in ss if s == "pass")
            ninfra = sum(1 for s in ss if s == "infra")
            return {"n": len(ss), "pass": npass, "infra": ninfra,
                    "p": npass / len(ss), "any": npass > 0, "both": npass == len(ss) and len(ss) == 3}
        b, a = stats("base"), stats(arm)
        rows.append({"task": t, "base": b, "arm": a})
    valid = [r for r in rows if r["base"] and r["arm"]]
    n = len(valid)
    pdelta = sum(r["arm"]["p"] - r["base"]["p"] for r in valid) / n if n else None
    anyd = sum(float(r["arm"]["any"]) - float(r["base"]["any"]) for r in valid) / n if n else None
    bothd = sum(float(r["arm"]["both"]) - float(r["base"]["both"]) for r in valid) / n if n else None
    flips = sum(1 for r in valid if r["arm"]["p"] > r["base"]["p"])
    regr = sum(1 for r in valid if r["arm"]["p"] < r["base"]["p"])
    verdict = "insufficient"
    if n >= 6 and pdelta is not None:
        if pdelta >= 0.10 and (bothd or 0) >= 0 and regr <= 1:
            verdict = "candidate"
        elif pdelta <= -0.15 and flips == 0:
            verdict = "reject"
        else:
            verdict = "neutral"
    out["arms"][arm] = {"paired_n": n, "pairedΔ": pdelta, "anyΔ": anyd, "bothΔ": bothd,
                        "flips": flips, "regress": regr, "verdict": verdict, "rows": rows}
    if arm != "base":
        table.append((arm, n, pdelta, anyd, bothd, flips, regr, verdict))

def pct(x):
    return "%+.1fpp" % (x * 100) if x is not None else "  n/a "

print("%-14s %4s %9s %9s %9s %5s %7s %s" % ("arm", "n", "pairedΔ", "anyΔ", "bothΔ", "flip", "regress", "verdict"))
for arm, n, p, a, b, f, r, v in table:
    print("%-14s %4d %9s %9s %9s %5d %7d %s" % (arm, n, pct(p), pct(a), pct(b), f, r, v))

with open(os.path.join(root, "results", "aggregate.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("->", os.path.join(root, "results", "aggregate.json"))
