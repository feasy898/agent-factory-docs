#!/usr/bin/env python3
"""层回收分析 v2 终版（2026-10-23）：df -v UNIQUE 盘上权威口径 + SHARED 差额推导删集内共享层。

方法：
  保留 = 现场全部镜像对象 − 删集（含在飞容器镜像强制剔除删集成员）
  层归属 = docker image inspect RootFS.Layers（122/122 与 history 对齐校验过）
  单主独占层盘上尺寸 = docker system df -v UNIQUE SIZE（daemon 层库口径）
  删集内多主层盘上尺寸 = Σ(SHARED_owner − 基座盘上尺寸)（同族纯基座保留镜像参照）
  回收(盘上) = Σ UNIQUE(有效删集) + Σ 删集内共享层
输出：layer-reclaim-final-20261023.json + 控制台报表
"""
import json
import re
from collections import defaultdict

BASE = "/home/pan-ding/workspace/agent黑灯工厂/状态观测/anolis-gc-20261023"
RAW = f"{BASE}/raw-20261023"
GB = 1e9


def sz_gb(s):
    m = re.match(r"([\d.]+)([kMGT]?B)", s)
    return float(m.group(1)) * {"B": 1e-9, "kB": 1e-6, "KB": 1e-6,
                                "MB": 1e-3, "GB": 1.0, "TB": 1e3}[m.group(2)]


tags = [ln.rstrip("\n").split("\t") for ln in open(f"{RAW}/images.txt")
        if "\t" in ln and not ln.startswith("$")]
by_name = {n: (i, s) for n, i, s in tags}
obj_layers, obj_size = {}, {}
for ln in open(f"{RAW}/inspect.tsv"):
    p = ln.rstrip("\n").split("\t")
    if len(p) < 3:
        continue
    iid = p[0].replace("sha256:", "")[:12]
    obj_size[iid] = int(p[1])
    obj_layers[iid] = p[2].split()
owners = defaultdict(set)
for iid, ls in obj_layers.items():
    for dd in ls:
        owners[dd].add(iid)
dfv = {}
sec = None
for ln in open(f"{RAW}/dfv.txt"):
    if ln.startswith("Images space usage"):
        sec = "img"; continue
    if ln.startswith("Container"):
        sec = None; continue
    if sec == "img" and not ln.startswith(("REPOSITORY", "Images")):
        p = ln.split()
        if len(p) >= 8 and re.match(r"^[0-9a-f]{12}$", p[2]):
            dfv[p[2]] = {"repo": p[0], "size": p[-4], "shared": p[-3], "unique": p[-2]}

d = json.load(open(f"{BASE}/lists-data-v2.json"))
cand = list(d["cand"])
ps = [l.rstrip("\n").split("\t") for l in open(f"{RAW}/ps.txt") if "\t" in l]
run_ids = {by_name[p[1]][0] if p[1] in by_name else p[1].replace("sha256:", "")[:12] for p in ps}
eff = [n for n in cand if n in by_name and by_name[n][0] not in run_ids]
blocked = [n for n in cand if n in by_name and by_name[n][0] in run_ids]
cand_ids = {by_name[n][0] for n in eff}
surv = set(obj_layers) - cand_ids
prot = set()
for iid in surv:
    prot.update(obj_layers[iid])

freed_single, freed_multi = defaultdict(set), defaultdict(set)
for iid in cand_ids:
    for dd in obj_layers[iid]:
        if dd in prot:
            continue
        if len(owners[dd]) == 1:
            freed_single[dd].add(iid)
        else:
            freed_multi[dd].add(iid)

# 删集内共享层盘上尺寸：按 owner 组推导（SHARED(owner) − 基座 = 该 owner 全部删集内共享层合计，
# 不能按层重复计）。前提：owner 的幸存者共享层恰为 7 层公共基座（本单已对 15629/16263 逐层核验）。
base_disk = 2.176
group_disk, multi_layer_ids = {}, defaultdict(set)
for dd, ows in freed_multi.items():
    key = tuple(sorted(ows))
    multi_layer_ids[key].add(dd)
for key in multi_layer_ids:
    vals = {round(sz_gb(dfv[o]["shared"]) - base_disk, 3) for o in key}
    assert len(vals) == 1, (key, vals)
    group_disk[key] = vals.pop()
multi_total = sum(group_disk.values())

uniq = {n: sz_gb(dfv[by_name[n][0]]["unique"]) for n in eff}
# 与层归属集一致性校验
for n in eff:
    i = by_name[n][0]
    n_excl = sum(1 for dd in obj_layers[i] if len(owners[dd]) == 1)
    assert n_excl >= 1 or uniq[n] < 0.01, (n, n_excl, uniq[n])

per = {n: uniq[n] for n in eff}
for key, sz in group_disk.items():
    names = [n for n in eff if by_name[n][0] in set(key)]
    for n in names:
        per[n] += sz / len(names)
order = sorted(eff, key=lambda n: -per[n])
total_uniq = sum(uniq.values())
total = total_uniq + multi_total
naive = sum(obj_size[by_name[n][0]] for n in eff) / GB
top10 = sum(per[n] for n in order[:10])
top20 = sum(per[n] for n in order[:20])
blocked_potential = sum(sz_gb(dfv[by_name[n][0]]["unique"]) for n in blocked)

df_line = [l for l in open(f"{RAW}/df.txt").read().splitlines() if l.startswith("/dev/vdb1")][0].split()
used_g, avail_g = int(df_line[2]) / 1048576, int(df_line[3]) / 1048576
proj_used, proj_avail = used_g - total, avail_g + total

print(f"有效删集 {len(eff)} 张（v2 29 张 − 在飞占用 {len(blocked)} 张）")
print(f"口径1 naive Σ inspect Size : {naive:6.1f} GB")
print(f"口径2 盘上 Σ UNIQUE        : {total_uniq:6.2f} GB")
print(f"      + 删集内共享层({sum(len(v) for v in multi_layer_ids.values())}个/{len(group_disk)}组) : {multi_total:6.2f} GB")
print(f"      = 实际回收预估        : {total:6.2f} GB")
print(f"top10 {top10:.1f} GB / top20 {top20:.1f} GB")
print(f"/data: {used_g:.1f}G used {avail_g:.1f}G avail → 删后 ~{proj_used:.1f}G / avail ~{proj_avail:.1f}G")
print(f"在飞占用候选(暂缓): {blocked}，若届时无容器可另收 ~{blocked_potential:.1f} GB")
print("\n删序（盘上贡献降序；solo=仅删此张回收=UNIQUE）:")
for n in order:
    i = by_name[n][0]
    share = per[n] - uniq[n]
    print(f"  {per[n]:6.2f}GB (solo {uniq[n]:5.2f}" + (f" + 内共享 {share:.2f}" if share > 0.005 else "")
          + f")  naive={obj_size[i]/GB:5.2f}GB  {n}")

json.dump({
    "as_of": "2026-10-23T08:05:41+08:00 (df/dfv) / 08:05:5x (ps)",
    "method": "df -v UNIQUE (daemon disk) + SHARED-base decomposition for D-internal layers",
    "eff_cand": eff, "blocked_running": blocked,
    "cal1_naive_gb": naive, "uniq_sum_gb": total_uniq,
    "multi_layers": {",".join(k): v for k, v in group_disk.items()},
    "multi_total_gb": multi_total, "reclaim_disk_gb": total,
    "top10_gb": top10, "top20_gb": top20, "per_gb": per, "order": order,
    "solo_gb": uniq, "blocked_potential_gb": blocked_potential,
    "data_used_g": used_g, "data_avail_g": avail_g,
    "proj_used_g": proj_used, "proj_avail_g": proj_avail,
}, open(f"{BASE}/layer-reclaim-final-20261023.json", "w"), ensure_ascii=False, indent=1)
print(f"\n[written] {BASE}/layer-reclaim-final-20261023.json")
