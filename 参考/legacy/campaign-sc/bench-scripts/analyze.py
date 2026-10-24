#!/usr/bin/env python3
"""Pivot bench results: model × category/difficulty pass rates + per-task matrix."""
import json, os, csv, collections, sys

BENCH = "/home/pan-ding/bench"
RES = os.path.join(BENCH, "results")
TASKS = os.path.join(BENCH, "tasks")

def meta():
    m = {}
    for t in os.listdir(TASKS):
        diff, cat = "", ""
        try:
            for line in open(os.path.join(TASKS, t, "task.yaml"), encoding="utf-8", errors="replace"):
                if line.startswith("difficulty:"): diff = line.split(":",1)[1].strip()
                if line.startswith("category:"): cat = line.split(":",1)[1].strip()
        except OSError: pass
        m[t] = (diff, cat)
    return m

def main():
    tm = meta()
    rows = []
    for cfg in sorted(os.listdir(RES)):
        cdir = os.path.join(RES, cfg)
        if not os.path.isdir(cdir): continue
        for f in os.listdir(cdir):
            if not f.endswith(".json"): continue
            try: d = json.load(open(os.path.join(cdir, f)))
            except Exception: continue
            task = d.get("task", f[:-5])
            diff, cat = tm.get(task, ("", ""))
            rows.append(dict(d, difficulty=diff, category=cat))
    # 1) per-config overall + by difficulty
    cfgs = sorted({r["config"] for r in rows})
    print("== overall ==")
    for c in cfgs:
        rs = [r for r in rows if r["config"] == c]
        p = sum(1 for r in rs if r["status"]=="pass"); n = len(rs)
        inf = sum(1 for r in rs if r["status"]=="infra")
        med = sum(r.get("wall_sec",0) for r in rs if r["status"]=="pass")/max(p,1)
        print(f"{c:<16} n={n:<3} pass={p:<3} ({p/max(n-inf,1):.0%}) infra={inf:<3} pass_med_wall={med:.0f}s")
    print("\n== pass rate by difficulty ==")
    diffs = ["easy","medium","hard"]
    print(f"{'config':<16}" + "".join(f"{d:>10}" for d in diffs))
    for c in cfgs:
        line = f"{c:<16}"
        for d in diffs:
            rs = [r for r in rows if r["config"]==c and r["difficulty"]==d]
            inf = sum(1 for r in rs if r["status"]=="infra")
            p = sum(1 for r in rs if r["status"]=="pass")
            line += f"{(p/max(len(rs)-inf,1)):>10.0%}" if rs else f"{'-':>10}"
        print(line)
    print("\n== pass rate by category ==")
    cats = sorted({r["category"] for r in rows if r["category"]})
    print(f"{'config':<16}" + "".join(f"{cat[:9]:>10}" for cat in cats))
    for c in cfgs:
        line = f"{c:<16}"
        for cat in cats:
            rs = [r for r in rows if r["config"]==c and r["category"]==cat]
            inf = sum(1 for r in rs if r["status"]=="infra")
            p = sum(1 for r in rs if r["status"]=="pass")
            line += f"{(p/max(len(rs)-inf,1)):>10.0%}" if rs else f"{'-':>10}"
        print(line)
    # 2) per-task matrix csv (task × config)
    out = os.path.join(RES, "task_matrix.csv")
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["task","difficulty","category"] + cfgs)
        for t in sorted(tm):
            w.writerow([t, tm[t][0], tm[t][1]] + [
                next((r["status"] for r in rows if r["task"]==t and r["config"]==c), "-") for c in cfgs])
    print(f"\ntask_matrix.csv written ({len(tm)} tasks x {len(cfgs)} configs)")

if __name__ == "__main__":
    main()
