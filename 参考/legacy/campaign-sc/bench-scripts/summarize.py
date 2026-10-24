#!/usr/bin/env python3
"""Summarize bench results into matrix.csv + per-config stats + failure buckets."""
import json, os, sys, csv, collections

BENCH = "/home/pan-ding/bench"
RES = os.path.join(BENCH, "results")
TASKS = os.path.join(BENCH, "tasks")

def task_meta():
    meta = {}
    for t in os.listdir(TASKS):
        yf = os.path.join(TASKS, t, "task.yaml")
        diff, cat = "", ""
        try:
            for line in open(yf, encoding="utf-8", errors="replace"):
                if line.startswith("difficulty:"): diff = line.split(":",1)[1].strip()
                if line.startswith("category:"): cat = line.split(":",1)[1].strip()
        except OSError: pass
        meta[t] = (diff, cat)
    return meta

def main():
    tm = task_meta()
    rows = []
    for config in sorted(os.listdir(RES)):
        cdir = os.path.join(RES, config)
        if not os.path.isdir(cdir): continue
        for f in sorted(os.listdir(cdir)):
            if not f.endswith(".json"): continue
            try: r = json.load(open(os.path.join(cdir, f)))
            except Exception: continue
            task = r.get("task") or f[:-5]
            diff, cat = tm.get(task, ("",""))
            rows.append({
                "config": config, "harness": r.get("harness",""), "model": r.get("model",""),
                "task": task, "status": r.get("status",""), "reason": r.get("reason",""),
                "agent_verdict": r.get("agent_verdict",""), "agent_rc": r.get("agent_rc",""),
                "wall_sec": r.get("wall_sec",""), "difficulty": diff, "category": cat,
            })
    with open(os.path.join(RES, "matrix.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["config"])
        w.writeheader(); w.writerows(rows)
    # stats
    by_cfg = collections.defaultdict(list)
    for r in rows: by_cfg[r["config"]].append(r)
    print(f"{'config':<16} {'pass':>5} {'fail':>5} {'infra':>5} {'timeout':>7} {'harness':>7} {'n':>4}  pass_rate(判责后)")
    for cfg, rs in sorted(by_cfg.items()):
        p = sum(1 for r in rs if r["status"]=="pass")
        fl = sum(1 for r in rs if r["status"]=="fail")
        inf = sum(1 for r in rs if r["status"]=="infra")
        to = sum(1 for r in rs if r["agent_verdict"]=="timeout")
        ha = sum(1 for r in rs if r["agent_verdict"]=="harness")
        n = len(rs); denom = n - inf
        pr = f"{p/denom:.1%}" if denom else "-"
        print(f"{cfg:<16} {p:>5} {fl:>5} {inf:>5} {to:>7} {ha:>7} {n:>4}  {pr}")
    # failure buckets
    print("\n== failure buckets (status=fail) by config ==")
    for cfg, rs in sorted(by_cfg.items()):
        fails = [r["task"] for r in rs if r["status"]=="fail"]
        if fails: print(f"{cfg}: {len(fails)}: {', '.join(fails)}")
    print(f"\ntotal rows: {len(rows)}")

if __name__ == "__main__":
    main()
