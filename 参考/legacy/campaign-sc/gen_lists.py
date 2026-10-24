#!/usr/bin/env python3
"""gen_lists.py <sc_root> — 由 wave json 生成 jobs-driver.txt 与 jobs-sc3.txt。"""
import json, os, sys
root = sys.argv[1]
wave = json.load(open(os.path.join(os.path.dirname(root), "sc3.json"), encoding="utf-8"))
reps = int(wave.get("reps", 3))
driver, alljobs = [], []
for arm in wave["arms"]:
    for t in wave["tasks_by_arm"][arm]:
        for r in range(1, reps + 1):
            alljobs.append("%s/%s-r%d" % (arm, t, r))
            if arm != "p31-skill-library":
                driver.append("%s/%s-r%d" % (arm, t, r))
for fam in wave["p31_families"]:
    for r in range(1, reps + 1):
        driver.append("p31-skill-library/CHAIN-%s-r%d" % (fam, r))
open(os.path.join(root, "jobs-sc3.txt"), "w").write("\n".join(sorted(alljobs)) + "\n")
open(os.path.join(root, "jobs-driver.txt"), "w").write("\n".join(sorted(driver)) + "\n")
print("driver:", len(driver), "real jobs:", len(alljobs))
