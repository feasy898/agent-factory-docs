#!/usr/bin/env python3
"""glm_usage_db.py <wave_root> [reset_iso] — GLM lane token accounting via zcode CLI db.

If <root>/contaminated-glm.txt exists and reset_iso is given, for those jobs only
requests with started_at >= reset time are counted (excludes pre-wipe contaminated runs).
"""
import datetime
import json
import os
import sqlite3
import statistics
import sys

root = sys.argv[1].rstrip("/")
reset_ts = 0
if len(sys.argv) > 2:
    dt = datetime.datetime.fromisoformat(sys.argv[2]).astimezone()
    reset_ts = int(dt.timestamp() * 1000)

contaminated = set()
cpath = os.path.join(root, "contaminated-glm.txt")
if os.path.exists(cpath):
    contaminated = {l.strip() for l in open(cpath) if l.strip()}

runs_prefix = root + "/runs/"
con = sqlite3.connect("/home/pan-ding/.zcode/cli/db/db.sqlite", timeout=10)
rows = con.execute(
    """select s.directory, m.started_at, m.provider_total_tokens
       from model_usage m join session s on s.id = m.session_id
       where s.directory like ?""",
    (runs_prefix + "%",),
).fetchall()

usage = {}
skipped = 0
for d, started, tot in rows:
    rel = d[len(runs_prefix):]
    parts = rel.split("/")
    if len(parts) < 2 or not parts[-1].startswith("work"):
        continue
    job = "%s/%s" % (parts[0], parts[1])
    if job in contaminated and (started or 0) < reset_ts:
        skipped += 1
        continue
    u = usage.setdefault(job, {"tokens": 0, "requests": 0})
    u["tokens"] += tot or 0
    u["requests"] += 1

out = os.path.join(root, "results", "usage-glm.json")
json.dump(usage, open(out, "w"), ensure_ascii=False, indent=1, sort_keys=True)
print("mapped %d jobs (skipped %d pre-reset requests) -> %s" % (len(usage), skipped, out))

by_arm = {}
for rel, u in usage.items():
    by_arm.setdefault(rel.split("/")[0], []).append(u["tokens"])
for arm in sorted(by_arm):
    v = sorted(by_arm[arm])
    print("%-6s n=%3d  median=%.2fM  mean=%.2fM  p90=%.2fM  total=%.1fM" % (
        arm, len(v), statistics.median(v) / 1e6, sum(v) / len(v) / 1e6,
        v[int(len(v) * 0.9)] / 1e6, sum(v) / 1e6))
