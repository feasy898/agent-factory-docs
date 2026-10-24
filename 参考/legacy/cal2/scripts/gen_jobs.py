#!/usr/bin/env python3
"""Generate per-config job lists + scratch dirs for the cal2 local workflow lanes."""
import json
import os
import shutil
import sys

ROOT = "/home/pan-ding/workspace/临时工作区/temp1"
CAL = os.path.join(ROOT, "cal2")
CONFIGS = {
    "zcode-m3":     "minimax/MiniMax-M3",
    "zcode-m31f":   "minimax/Minimax-M3.1-Flash-Preview",
    "zcode-s5":     "new-provider/step-5-preview",
    "zcode-router": "new-provider/step-router-v1",
}

tasks = [l.strip() for l in open(os.path.join(ROOT, "bench", "tasks_ordered.txt")) if l.strip()]
assert len(tasks) == 51, len(tasks)

for cfg in CONFIGS:
    jobs = []
    for t in tasks:
        work = os.path.join(CAL, "runs", cfg, t, "work")
        shutil.rmtree(os.path.join(CAL, "runs", cfg, t), ignore_errors=True)
        os.makedirs(os.path.dirname(work), exist_ok=True)
        shutil.copytree(os.path.join(CAL, "inputs", t), work)
        jobs.append({
            "task": t,
            "dir": work,
            "instr": os.path.join(CAL, "instr", t + ".md"),
        })
    with open(os.path.join(CAL, "jobs", cfg + ".json"), "w", encoding="utf-8") as f:
        json.dump({"config": cfg, "model": CONFIGS[cfg], "jobs": jobs}, f, ensure_ascii=False, indent=1)
    print(f"{cfg}: {len(jobs)} jobs, model={CONFIGS[cfg]}")
print("done")
