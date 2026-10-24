#!/usr/bin/env python3
"""sc3_expand_m31.py — 扩充 m31 清单到 6 题×9 臂×3rep=162，并重置其中被 GLM 弄脏的现场。"""
import os, shutil, subprocess

root = "/home/pan-ding/campaign-sc/sc3"
arms = ["base", "p2-mech-chain", "p26-rubric-select", "p27-artifact-vote",
        "p28-supervisor-select", "p37-feedback-retry", "p43-qa-gate",
        "p5-mech-blind-retry", "t2-artifact-gate"]
tasks = ["largest-eigenval", "portfolio-optimization", "enemy-grid-escape",
         "solve-maze-challenge", "schemelike-metacircular-eval",
         "model-extraction-relu-logits"]
jobs = ["%s/%s-r%d" % (a, t, r) for a in arms for t in tasks for r in (1, 2, 3)]
open(os.path.join(root, "jobs-m31.txt"), "w").write("\n".join(jobs) + "\n")

reset = kept = 0
for job in jobs:
    d = os.path.join(root, "runs", job)
    w = os.path.join(d, "work")
    dirty = False
    if os.path.isdir(w):
        files = os.listdir(w)
        dirty = ".done" in files or any(f.startswith(".") and f.endswith("-done") for f in files)
        # rollout 残留也算脏
        dirty = dirty or any(f.startswith("work.r") for f in os.listdir(d))
    if dirty:
        shutil.rmtree(w, ignore_errors=True)
        for f in os.listdir(d):
            if f.startswith("roll") or f == "work.select":
                shutil.rmtree(os.path.join(d, f), ignore_errors=True)
        reset += 1
    if not os.path.isdir(w) or not os.listdir(w):
        os.makedirs(w, exist_ok=True)
        task = job.split("/")[1].rsplit("-r", 1)[0]
        subprocess.run(["python3", "/home/pan-ding/bench/scripts/prepare_task.py",
                        "/home/pan-ding/bench/tasks/" + task, w,
                        os.path.join(d, "prompt.txt")], capture_output=True)
    else:
        kept += 1
print("jobs-m31.txt: %d; reset(dirty): %d; kept-clean: %d" % (len(jobs), reset, kept))
