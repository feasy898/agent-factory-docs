#!/usr/bin/env python3
"""aggregate.py <results_dir> <arms_csv> <tasks_csv> <reps>
汇总判分结果：每臂通过率（infra 不计分母）、逐题配对矩阵、每臂 vs base 的配对差值。
输出 stdout 报告 + results/summary.json。"""
import json, os, sys

results_dir, arms, tasks, reps = sys.argv[1], sys.argv[2].split(), sys.argv[3].split(), int(sys.argv[4])

def load(arm, task, r):
    p = os.path.join(results_dir, f"{arm}__{task}-r{r}.json")
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p)).get("status")
    except Exception:
        return None

# 每臂统计
arm_stats = {}
for arm in arms:
    pw = fl = infra = missing = 0
    for t in tasks:
        for r in range(1, reps + 1):
            s = load(arm, t, r)
            if s == "pass": pw += 1
            elif s == "fail": fl += 1
            elif s == "infra": infra += 1
            else: missing += 1
    judged = pw + fl
    arm_stats[arm] = {"pass": pw, "fail": fl, "infra": infra, "missing": missing,
                      "judged": judged, "rate": (pw / judged) if judged else None}

# 逐题矩阵（每题每臂取 reps 中最好结果， paired by task）
task_matrix = {}
for t in tasks:
    row = {}
    for arm in arms:
        sts = [load(arm, t, r) for r in range(1, reps + 1)]
        sts = [s for s in sts if s in ("pass", "fail")]
        row[arm] = ("pass" if any(s == "pass" for s in sts) else "fail") if sts else "n/a"
    task_matrix[t] = row

# 配对差值：每个技术在哪些题上 base=fail 且 tech=pass（翻转），base=pass 且 tech=fail（回退）
# 口径：仅在双方都有判分数据的题目上比较（配对集），避免题集不同导致的苹果橘子对比
deltas = {}
base = "base"
for arm in arms:
    if arm == base: continue
    paired_tasks = []
    for t in tasks:
        bs = [load(base, t, r) for r in range(1, reps + 1)]
        as_ = [load(arm, t, r) for r in range(1, reps + 1)]
        bs = [s for s in bs if s in ("pass", "fail")]
        as_ = [s for s in as_ if s in ("pass", "fail")]
        if bs and as_:
            paired_tasks.append(t)
    flips, regress = [], []
    for t in paired_tasks:
        b, a = task_matrix[t].get(base), task_matrix[t].get(arm)
        if b == "fail" and a == "pass": flips.append(t)
        if b == "pass" and a == "fail": regress.append(t)
    bstat, astat = arm_stats[base], arm_stats[arm]
    # 配对集上的通过率（每臂只统计配对题）
    def paired_rate(a):
        pw = fl = 0
        for t in paired_tasks:
            sts = [load(a, t, r) for r in range(1, reps + 1)]
            sts = [s for s in sts if s in ("pass", "fail")]
            if any(s == "pass" for s in sts): pw += 1
            else: fl += 1
        return pw / (pw + fl) if (pw + fl) else None
    br, ar = paired_rate(base), paired_rate(arm)
    # 稳定性口径：两重复均通过才算通过（best-of-2 会掩盖稳定性变化）
    def both_rate(a):
        pw = fl = 0
        for t in paired_tasks:
            sts = [load(a, t, r) for r in range(1, reps + 1)]
            sts = [s for s in sts if s in ("pass", "fail")]
            if len(sts) == reps and all(s == "pass" for s in sts): pw += 1
            elif sts: fl += 1
        return pw / (pw + fl) if (pw + fl) else None
    def stab(a, t):
        sts = [load(a, t, r) for r in range(1, reps + 1)]
        sts = [s for s in sts if s in ("pass", "fail")]
        return sum(1 for s in sts if s == "pass"), len(sts)
    stab_gain = []   # 通过次数增加但 best-of 未翻转的题（稳定性提升）
    for t in paired_tasks:
        bp, bn = stab(base, t); ap, an = stab(arm, t)
        if ap > bp and not (task_matrix[t].get(base) == "fail" and task_matrix[t].get(arm) == "pass"):
            stab_gain.append({"task": t, "base": f"{bp}/{bn}", "tech": f"{ap}/{an}"})
    bbr, abr = both_rate(base), both_rate(arm)
    deltas[arm] = {
        "flips_fail_to_pass": flips, "regress_pass_to_fail": regress,
        "base_rate": bstat["rate"], "tech_rate": astat["rate"],
        "rate_delta_pp": (None if bstat["rate"] is None or astat["rate"] is None
                          else round((astat["rate"] - bstat["rate"]) * 100, 1)),
        "paired_tasks": paired_tasks,
        "paired_base_rate": br, "paired_tech_rate": ar,
        "paired_delta_pp": (None if br is None or ar is None else round((ar - br) * 100, 1)),
        "both_base_rate": bbr, "both_tech_rate": abr,
        "both_delta_pp": (None if bbr is None or abr is None else round((abr - bbr) * 100, 1)),
        "stability_gain": stab_gain,
    }

report = {"arm_stats": arm_stats, "task_matrix": task_matrix, "deltas": deltas}
os.makedirs(results_dir, exist_ok=True)
json.dump(report, open(os.path.join(results_dir, "summary.json"), "w"), ensure_ascii=False, indent=1)

print("=== 每臂通过率（infra/缺失不计分母）===")
for arm in arms:
    s = arm_stats[arm]
    rate = "n/a" if s["rate"] is None else f"{s['rate']*100:.1f}%"
    print(f"{arm:10s} pass={s['pass']:3d} fail={s['fail']:3d} infra={s['infra']:2d} missing={s['missing']:2d}  rate={rate}")
print("\n=== 配对差值（每题取 reps 最好；配对集=双方都有数据的题）===")
for arm, d in deltas.items():
    br = f"{d['paired_base_rate']*100:.1f}%" if d['paired_base_rate'] is not None else "n/a"
    tr = f"{d['paired_tech_rate']*100:.1f}%" if d['paired_tech_rate'] is not None else "n/a"
    bbr = f"{d['both_base_rate']*100:.1f}%" if d['both_base_rate'] is not None else "n/a"
    abr = f"{d['both_tech_rate']*100:.1f}%" if d['both_tech_rate'] is not None else "n/a"
    print(f"{arm:32s} paired(n={len(d['paired_tasks'])}) base={br} tech={tr} delta={d['paired_delta_pp']}pp  both-pass base={bbr} tech={abr} delta={d['both_delta_pp']}pp  flips={d['flips_fail_to_pass']}  regress={d['regress_pass_to_fail']}  stab_gain={[g['task'] for g in d['stability_gain']]}")
print("\n=== 逐题矩阵 ===")
hdr = "task".ljust(32) + "".join(a.rjust(10) for a in arms)
print(hdr)
for t in tasks:
    print(t.ljust(32) + "".join(str(task_matrix[t][a]).rjust(10) for a in arms))
