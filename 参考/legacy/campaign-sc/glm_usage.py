#!/usr/bin/env python3
"""glm_usage.py <wave_root> — token accounting for GLM(zcode) lane jobs.

Maps zcode rollout logs (~/.zcode/cli/rollout/model-io-sess_*.jsonl) back to jobs
by first-prompt fingerprint, sums usage.totalTokens / request counts per job,
writes <root>/results/usage-glm.json.
"""
import glob
import json
import os
import re
import sys

root = sys.argv[1]
runs = os.path.join(root, "runs")

def fingerprint(text):
    t = re.sub(r"\s+", " ", text)[:160]
    return t

jobs = {}
for arm in sorted(os.listdir(runs)):
    ad = os.path.join(runs, arm)
    if not os.path.isdir(ad):
        continue
    for job in sorted(os.listdir(ad)):
        p = os.path.join(ad, job, "prompt.txt")
        if os.path.exists(p):
            jobs[fingerprint(open(p, encoding="utf-8", errors="replace").read())] = "%s/%s" % (arm, job)

usage = {}
mapped = 0
total = 0
for f in glob.glob(os.path.expanduser("~/.zcode/cli/rollout/model-io-sess_*.jsonl")):
    if os.path.getmtime(f) < 1760000000:  # skip ancient
        pass
    fp = None
    toks = 0
    reqs = 0
    try:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                reqs += 1
                if fp is None and '"role":"user"' in line or (fp is None and '"role": "user"' in line):
                    m = re.search(r'"content":\s*(?:\[\{[^]]*?"text":\s*)?"(.*?)"', line)
                    if m:
                        cand = m.group(1).encode().decode("unicode_escape", errors="replace")
                        cand_fp = fingerprint(cand)
                        for jfp in jobs:
                            if jfp[:80] in cand_fp or cand_fp[:80] in jfp:
                                fp = jfp
                                break
                for um in re.finditer(r'"usage":\{"inputTokens":(\d+),"outputTokens":(\d+),"totalTokens":(\d+)', line):
                    toks += int(um.group(3))
    except OSError:
        continue
    if fp and fp in jobs:
        rel = jobs[fp]
        u = usage.setdefault(rel, {"tokens": 0, "requests": 0, "sessions": 0})
        u["tokens"] += toks
        u["requests"] += reqs
        u["sessions"] += 1
        mapped += 1
    total += 1

out = os.path.join(root, "results", "usage-glm.json")
json.dump(usage, open(out, "w"), ensure_ascii=False, indent=1, sort_keys=True)
print("mapped %d sessions (of %d rollout files scanned) -> %s" % (mapped, total, out))

# per-arm medians
import statistics
by_arm = {}
for rel, u in usage.items():
    by_arm.setdefault(rel.split("/")[0], []).append(u["tokens"])
for arm in sorted(by_arm):
    v = by_arm[arm]
    print("%-6s n=%3d  median=%.0f  mean=%.0f  total=%.1fM" % (arm, len(v), statistics.median(v), sum(v)/len(v), sum(v)/1e6))
