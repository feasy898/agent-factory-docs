#!/usr/bin/env python3
"""scan_glm_429.py <wave_root> — classify each GLM-lane job's log:
clean (no 429) / recovered (429 mid-log but later turns continued) / terminal (log tail ends in failure).
Prints per-arm counts and writes terminal-fail job list to <root>/contaminated-glm.txt
(only jobs whose result is fail/infra AND log ends in a failed state are listed for re-solve).
"""
import os
import re
import sys
import json

root = sys.argv[1]
runs = os.path.join(root, "runs")
logs = os.path.join(root, "logs")
results = os.path.join(root, "results")

BAD = re.compile(r"responseStatus:\s*429|Turn execution failed|rate.limit|RateLimit", re.I)

def classify(logpath):
    try:
        text = open(logpath, encoding="utf-8", errors="replace").read()
    except OSError:
        return "nolog"
    hits = BAD.findall(text)
    if not hits:
        return "clean"
    tail = text[-1500:]
    if BAD.search(tail):
        return "terminal"
    return "recovered"

counts = {}
contaminated = []
for arm in sorted(os.listdir(runs)):
    ad = os.path.join(runs, arm)
    if not os.path.isdir(ad):
        continue
    for job in sorted(os.listdir(ad)):
        rel = "%s/%s" % (arm, job)
        log = os.path.join(logs, rel + ".glm.log")
        if not os.path.exists(log):
            continue  # m3.1 lane job
        c = classify(log)
        tag = "%s__%s" % (arm, job)
        rj = os.path.join(results, tag + ".json")
        status = None
        if os.path.exists(rj):
            try:
                status = json.load(open(rj)).get("status")
            except Exception:
                status = "badjson"
        counts[(arm, c)] = counts.get((arm, c), 0) + 1
        if c == "terminal" and status in ("fail", "infra", None):
            contaminated.append(rel)

for (arm, c), n in sorted(counts.items()):
    print("%-6s %-10s %d" % (arm, c, n))
out = os.path.join(root, "contaminated-glm.txt")
with open(out, "w") as f:
    f.write("\n".join(contaminated) + ("\n" if contaminated else ""))
print("terminal-fail (to re-solve): %d -> %s" % (len(contaminated), out))
