#!/usr/bin/env python3
"""独占层分析 v4：history 反序后过滤 0B 空步骤与 RootFS.Layers 对齐（计数校验）。"""
import json, re, subprocess

OUT = "/home/pan-ding/workspace/agent黑灯工厂/状态观测/anolis-gc-20261023"
d = json.load(open(f"{OUT}/lists-data-v2.json"))
pool, keep, cand = d["pool"], set(d["keep"]), d["cand"]
A_ids, dangling = set(d["A_ids"]), set(d["dangling_inuse"])

def ssh(args, timeout=300):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "anolis"] + args,
                       capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    if r.returncode != 0: raise RuntimeError(r.stderr[-300:])
    return r.stdout

all_ids = sorted({v[0] for v in pool.values()} | A_ids | dangling)
out = ssh(["docker", "image", "inspect"] + all_ids + ["--format", '"{{.Id}} {{range .RootFS.Layers}}{{.}} {{end}}"'])
obj_layers = {}
for line in out.splitlines():
    p = line.split()
    if len(p) < 2: continue
    obj_layers[p[0].replace("sha256:", "")[:12]] = p[1:]

def parse_size(s):
    m = re.match(r"([\d.]+)\s*([kMGT]?B)", s.strip())
    if not m: return 0.0
    return float(m.group(1)) * {"B":1e-9,"kB":1e-6,"KB":1e-6,"MB":1e-3,"GB":1.0,"TB":1e3}[m.group(2)]

hist5 = {}
for line in open(f"{OUT}/hist-raw.tsv"):
    if "\t" not in line: continue
    iid, s = line.split("\t", 1)
    hist5[iid.strip().replace("sha256:", "")] = [x for x in s.split(",") if x.strip()]

layer_size, ok_cnt, bad = {}, 0, []
for iid, layers in obj_layers.items():
    hs_all = hist5.get(iid[:5], [])
    hs = [x for x in hs_all if parse_size(x) > 0]      # 去 0B 空步骤
    if len(hs) == len(layers):
        ok_cnt += 1
        for dd, s in zip(layers, hs):
            v = parse_size(s)
            if dd not in layer_size or v > layer_size[dd]: layer_size[dd] = v
    else:
        bad.append((iid, len(layers), len(hs_all), len(hs)))
print(f"对齐成功 {ok_cnt}/{len(obj_layers)}；失败样例: {bad[:5]}")

keep_objs = {pool[n][0] for n in keep} | A_ids | dangling
protected = set()
for o in keep_objs: protected.update(obj_layers.get(o, []))
free = {}
for n in cand:
    for dd in obj_layers.get(pool[n][0], []):
        if dd not in protected: free.setdefault(dd, []).append(n)
est = sum(layer_size.get(dd, 0.0) for dd in free)
per = {n: 0.0 for n in cand}
for dd, ns in free.items():
    sz = layer_size.get(dd, 0.0)
    if len(ns) == 1: per[ns[0]] += sz
    else:
        for n in ns: per[n] += sz / len(ns)
print(f"可释放 diff 层 {len(free)} 个；删集 {len(cand)} 张独占层估算合计: {est:.1f} GB")
print("删序（预估独占降序）:")
for n in sorted(cand, key=lambda x: -per[x]):
    print(f"  {per[n]:6.2f}GB est  {pool[n][1]:>7}  {n}")
json.dump({"per": per, "est": est, "order": sorted(cand, key=lambda x: -per[x]), "aligned": ok_cnt},
          open(f"{OUT}/layer-est.json", "w"), ensure_ascii=False, indent=1)
