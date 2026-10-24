#!/usr/bin/env python3
"""split_lanes.py <wave_root> — block-consistent lane split.

Groups jobs by (task, rep) block across arms. A block with any work/.done is
"touched" and stays entirely on the m3.1 lane (model consistency within block:
base-vs-arm paired comparisons must share one model). Fully untouched blocks are
assigned to the GLM lane via <root>/jobs-glm.txt. Idempotent: re-running keeps
prior assignments and adopts still-untouched blocks; solved jobs drop out.
"""
import os
import re
import sys

root = sys.argv[1]
runs = os.path.join(root, "runs")

blocks = {}
for arm in sorted(os.listdir(runs)):
    ad = os.path.join(runs, arm)
    if not os.path.isdir(ad):
        continue
    for jd in sorted(os.listdir(ad)):
        m = re.match(r"^(.*)-r(\d+)$", jd)
        if not m:
            continue
        blocks.setdefault((m.group(1), m.group(2)), []).append("%s/%s" % (arm, jd))

def done(rel):
    return os.path.exists(os.path.join(runs, rel, "work", ".done"))

glm_path = os.path.join(root, "jobs-glm.txt")
glm = set()
if os.path.exists(glm_path):
    glm.update(l.strip() for l in open(glm_path) if l.strip())

n_blocks_glm = 0
for key, jobs in sorted(blocks.items()):
    if any(done(j) for j in jobs):
        continue
    glm.update(jobs)
    n_blocks_glm += 1

glm = {j for j in glm if not done(j)}
with open(glm_path, "w") as f:
    f.write("\n".join(sorted(glm)) + ("\n" if glm else ""))
print("glm lane: %d jobs across %d untouched blocks -> %s" % (len(glm), n_blocks_glm, glm_path))
