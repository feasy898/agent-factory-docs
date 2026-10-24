#!/usr/bin/env python3
"""层回收分析（2026-10-23）：层归属 → 删集独占层字节，两口径 + df -v 标定。

输入 raw-20261023/{images.txt,inspect.tsv,hist.tsv,ps.txt,dfv.txt,df.txt}
输出 layer-reclaim-20261023.json + 控制台报表。
"""
import json
import re
from collections import defaultdict

BASE = "/home/pan-ding/workspace/agent黑灯工厂/状态观测/anolis-gc-20261023"
RAW = f"{BASE}/raw-20261023"

# ---------- 1. 现场池（fresh） ----------
tags = []           # (name, id12, size_str)
for ln in open(f"{RAW}/images.txt"):
    if "\t" not in ln or ln.startswith("$"):
        continue
    name, iid, sz = ln.rstrip("\n").split("\t")
    tags.append((name, iid, sz))
by_name = {n: (i, s) for n, i, s in tags}
ids12 = sorted({i for _, i, _ in tags})
print(f"[pool] tag 行 {len(tags)}，镜像对象 {len(ids12)}")

# ---------- 2. inspect：对象 → (Size 字节, 层 diff-id 列表[老→新]) ----------
obj_size, obj_layers = {}, {}
for ln in open(f"{RAW}/inspect.tsv"):
    p = ln.rstrip("\n").split("\t")
    if len(p) < 3:
        continue
    iid = p[0].replace("sha256:", "")[:12]
    obj_size[iid] = int(p[1])
    obj_layers[iid] = p[2].split()
assert len(obj_layers) == len(ids12), (len(obj_layers), len(ids12))
print(f"[inspect] {len(obj_layers)} 对象，层总数(展开) {sum(len(v) for v in obj_layers.values())}")

# ---------- 3. history：对象 → 各步 Size（docker 输出新→老） ----------
def parse_size(s):
    m = re.match(r"([\d.]+)\s*([kMGT]?B)", s.strip())
    if not m:
        return 0.0
    return float(m.group(1)) * {"B": 1e-9, "kB": 1e-6, "KB": 1e-6,
                                "MB": 1e-3, "GB": 1.0, "TB": 1e3}[m.group(2)]

hist = {}
for ln in open(f"{RAW}/hist.tsv"):
    if "\t" not in ln:
        continue
    iid, s = ln.split("\t", 1)
    hist[iid.strip()] = [parse_size(x) for x in s.split(",") if x.strip()]

# 层尺寸标注：hist 过滤 0B 后反转（新→老 变 老→新）与 RootFS.Layers 对齐
layer_size = {}       # diff-id -> GB（history 口径）
align_ok, align_bad = 0, []
for iid in ids12:
    layers = obj_layers[iid]
    hs_all = hist.get(iid, [])
    hs = [x for x in hs_all if x > 0]
    if len(hs) == len(layers):
        align_ok += 1
        for dd, v in zip(layers, hs):
            if v > layer_size.get(dd, 0.0):
                layer_size[dd] = v
    else:
        align_bad.append((iid, len(layers), len(hs_all), len(hs)))
print(f"[align] 对齐 {align_ok}/{len(ids12)}；失配 {align_bad[:6]}")
all_layers = sorted({dd for v in obj_layers.values() for dd in v})
sum_hist_distinct = sum(layer_size.get(dd, 0.0) for dd in all_layers)
print(f"[calib] history 口径全池去重层和: {sum_hist_distinct:.1f} GB")

# ---------- 4. df -v 解析（盘上口径标定） ----------
def parse_dfv(path):
    imgs = {}
    sec = None
    for ln in open(path):
        if ln.startswith("Images space usage"):
            sec = "img"; continue
        if ln.startswith("Container"):
            sec = None; continue
        if sec == "img" and not ln.startswith(("REPOSITORY", "Images")):
            p = ln.split()
            # 列: REPO TAG ID CREATED(可变词数) SIZE SHARED UNIQUE CONTAINERS → 从行尾倒数
            if len(p) >= 8 and re.match(r"^[0-9a-f]{12}$", p[2]):
                imgs[p[2]] = {"size": p[-4], "shared": p[-3],
                              "unique": p[-2], "containers": p[-1]}
    return imgs

dfv_raw = open(f"{RAW}/dfv.txt").read()
df_summary = [l for l in dfv_raw.splitlines() if l.startswith("Images ")]
df_total_gb = float(re.search(r"Images\s+\d+\s+\d+\s+([\d.]+)GB", df_summary[0]).group(1)) if df_summary else None
dfv = parse_dfv(f"{RAW}/dfv.txt")
def sz_gb(s):
    m = re.match(r"([\d.]+)([kMGT]?B)", s)
    return float(m.group(1)) * {"B":1e-9,"kB":1e-6,"KB":1e-6,"MB":1e-3,"GB":1,"TB":1e3}[m.group(2)]
print(f"[df] Images 总量 {df_total_gb} GB；df -v 镜像行 {len(dfv)}")
print(f"[df] 摘要行: {df_summary}")

# ---------- 5. 保留/删集（v2 清单 ∪ 在飞容器） ----------
d = json.load(open(f"{BASE}/lists-data-v2.json"))
keep_names, cand_names = set(d["keep"]), list(d["cand"])
ps_lines = [l.rstrip("\n").split("\t") for l in open(f"{RAW}/ps.txt") if "\t" in l]
running_imgs = [p[1] for p in ps_lines]
running_ids = set()
for im in running_imgs:
    if im in by_name:
        running_ids.add(by_name[im][0])
    else:
        running_ids.add(im.replace("sha256:", "")[:12])  # 已是 ID 引用
print(f"[ps] 在飞容器 {len(ps_lines)}: {running_imgs} -> ID {sorted(running_ids)}")

cand_missing = [n for n in cand_names if n not in by_name]
eff_cand = [n for n in cand_names if n in by_name and by_name[n][0] not in running_ids]
blocked = [n for n in cand_names if n in by_name and by_name[n][0] in running_ids]
cand_ids = {by_name[n][0] for n in eff_cand}
keep_ids = ({by_name[n][0] for n in keep_names if n in by_name} | running_ids
            | set(d["A_ids"]) | set(d.get("dangling_inuse", [])))
# 交叉核对：keep ∪ cand 应 ≈ 白名单池；survivor = 现场全部对象 − 删集
survivor_ids = set(ids12) - cand_ids
keep_via_pool = set(ids12) - cand_ids
print(f"[sets] v2: keep {len(keep_names)} cand {len(cand_names)}；现场缺 tag {cand_missing}")
print(f"[sets] 在飞命中删集(剔除): {blocked}；有效删集 {len(eff_cand)} 张")
sym_diff = keep_via_pool ^ (keep_ids & set(ids12))
print(f"[sets] survivor(现场−删集) vs keep∪在飞∪A 差集: {sorted(sym_diff)}")

# ---------- 6. 层归属 ----------
owners = defaultdict(set)
for iid in ids12:
    for dd in obj_layers[iid]:
        owners[dd].add(iid)
prot = set()
for iid in survivor_ids:
    prot.update(obj_layers[iid])
freed = {}   # diff-id -> [cand ids 引用]
for iid in cand_ids:
    for dd in obj_layers[iid]:
        if dd not in prot:
            freed.setdefault(dd, []).append(iid)
print(f"[layers] 全池去重层 {len(all_layers)}；受保护层 {len(prot)}；可释放层 {len(freed)}")

# 口径1：naive（inspect Size 展开和，删集有效张）
cal1 = sum(obj_size[by_name[n][0]] for n in eff_cand) / 1e9
# 口径2：history 压缩口径
cal2_raw = sum(layer_size.get(dd, 0.0) for dd in freed)
# 盘上口径标定：全池 scale
scale_pool = df_total_gb / sum_hist_distinct if sum_hist_distinct else None
# 逐镜像标定：df -v UNIQUE(i) / Σ hist(独占层 of i)（仅独占层>0 的镜像）
ratios = []
for iid, row in dfv.items():
    uniq_i = [dd for dd in obj_layers.get(iid, []) if len(owners.get(dd, set())) == 1]
    sc = sum(layer_size.get(dd, 0.0) for dd in uniq_i)
    ud = sz_gb(row["unique"])
    if sc > 0.3 and ud > 0.3:
        ratios.append((ud / sc, iid, ud, sc))
ratios.sort()
rs = [r[0] for r in ratios]
med = sorted(rs)[len(rs)//2]
print(f"[scale] 全池 scale={scale_pool:.3f}；逐镜像 unique/hist 中位={med:.3f} "
      f"(n={len(rs)}, min={rs[0]:.3f}, max={rs[-1]:.3f})")
print("[scale] 逐镜像比样例(升序前3+后3):", [(f"{a:.2f}", b) for a, b, _, _ in ratios[:3] + ratios[-3:]])

cal2_disk_pool = cal2_raw * scale_pool
cal2_disk_med = cal2_raw * med

# df -v UNIQUE 交叉验证（删集 Σ UNIQUE = 全池中仅单镜像持有且属删集）
uniq_sum = sum(sz_gb(dfv[by_name[n][0]]["unique"]) for n in eff_cand if by_name[n][0] in dfv)
uniq_from_layers = sum(layer_size.get(dd, 0.0) * med
                       for dd, ows in owners.items() if len(ows) == 1 and next(iter(ows)) in cand_ids)
print(f"[xcheck] df -v 删集 ΣUNIQUE={uniq_sum:.2f}GB；层算独占×med={uniq_from_layers:.2f}GB")
shared_in_d = [dd for dd in freed if len(freed[dd]) > 1]
shared_bytes = sum(layer_size.get(dd, 0.0) for dd in shared_in_d) * med
print(f"[xcheck] 删集内部共享层 {len(shared_in_d)} 个 ≈ {shared_bytes:.2f}GB(med 口径)")

# ---------- 7. 性价比排序（批删归属：独占者全额，删集内共享均摊） ----------
per = {n: 0.0 for n in eff_cand}
for dd, cids in freed.items():
    sz = layer_size.get(dd, 0.0) * med
    if len(cids) == 1:
        per[[n for n in eff_cand if by_name[n][0] == cids[0]][0]] += sz
    else:
        names = [n for n in eff_cand if by_name[n][0] in set(cids)]
        for n in names:
            per[n] += sz / len(names)
order = sorted(eff_cand, key=lambda n: -per[n])
top20 = sum(per[n] for n in order[:20])

print(f"\n===== 结果 =====")
print(f"口径1 naive(Σ inspect Size): {cal1:.1f} GB ({len(eff_cand)} 张)")
print(f"口径2 层感知 history 原始: {cal2_raw:.1f} GB | ×全池scale: {cal2_disk_pool:.1f} GB | ×逐镜像中位: {cal2_disk_med:.1f} GB")
print(f"top20 归属和: {top20:.1f} GB")
print(f"删序（层感知归属降序, med 口径）:")
for n in order:
    print(f"  {per[n]:6.2f}GB  naive={obj_size[by_name[n][0]]/1e9:5.2f}GB  {n}")

json.dump({
    "as_of": "2026-10-23T08:05:41+08:00",
    "cal1_naive_gb": cal1, "cal2_hist_gb": cal2_raw,
    "cal2_disk_poolscale_gb": cal2_disk_pool, "cal2_disk_medscale_gb": cal2_disk_med,
    "scale_pool": scale_pool, "scale_median": med, "scale_n": len(rs),
    "df_total_gb": df_total_gb, "sum_hist_distinct_gb": sum_hist_distinct,
    "uniq_sum_dfv_gb": uniq_sum, "eff_cand": eff_cand, "blocked_running": blocked,
    "cand_missing": cand_missing, "per_gb": per, "order": order, "top20_gb": top20,
    "align_ok": align_ok, "align_bad": align_bad,
    "freed_layers": len(freed), "protected_layers": len(prot),
    "shared_in_delete_layers": len(shared_in_d),
    "shared_in_delete_gb_med": shared_bytes,
    "df_summary": df_summary,
}, open(f"{BASE}/layer-reclaim-20261023.json", "w"), ensure_ascii=False, indent=1)
print(f"\n[written] {BASE}/layer-reclaim-20261023.json")
