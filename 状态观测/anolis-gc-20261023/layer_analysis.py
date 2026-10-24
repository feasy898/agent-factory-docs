#!/usr/bin/env python3
"""独占层分析 v3：hist key 为 5 位十六进制（远端 sha256: 前缀占位），按前缀匹配。"""
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
print("inspect 对象数:", len(obj_layers), " 平均层数:", sum(len(v) for v in obj_layers.values())/max(1,len(obj_layers)))

def parse_size(s):
    m = re.match(r"([\d.]+)\s*([kMGT]?B)", s.strip())
    if not m: return 0.0
    return float(m.group(1)) * {"B":1e-9,"kB":1e-6,"KB":1e-6,"MB":1e-3,"GB":1.0,"TB":1e3}[m.group(2)]

hist5, mismatch = {}, 0
for line in open(f"{OUT}/hist-raw.tsv"):
    if "\t" not in line: continue
    iid, s = line.split("\t", 1)
    hexid = iid.strip().replace("sha256:", "")
    hist5[hexid] = [x for x in s.split(",") if x.strip()]
assert len(hist5) == len(set(hist5)), "hist 5位前缀碰撞"
layer_size = {}
for iid, layers in obj_layers.items():
    hs = hist5.get(iid[:len(next(iter(hist5)))], [])
    if len(hs) != len(layers):
        mismatch += 1
        hs = (hs + ["0B"] * len(layers))[:len(layers)] if hs else ["0B"] * len(layers)
    for dd, s in zip(layers, hs):
        v = parse_size(s)
        if dd not in layer_size or v > layer_size[dd]: layer_size[dd] = v
print("history 对齐失配:", mismatch, "/", len(obj_layers))

keep_objs = {pool[n][0] for n in keep} | A_ids | dangling
protected = set()
for o in keep_objs: protected.update(obj_layers.get(o, []))
free = {}
for n in cand:
    for dd in obj_layers.get(pool[n][0], []):
        if dd not in protected: free.setdefault(dd, []).append(n)
print("受保护 diff 层数:", len(protected), " 可释放 diff 层数:", len(free))
est = sum(layer_size.get(dd, 0.0) for dd in free)
per = {n: 0.0 for n in cand}
for dd, ns in free.items():
    sz = layer_size.get(dd, 0.0)
    if len(ns) == 1: per[ns[0]] += sz
    else:
        for n in ns: per[n] += sz / len(ns)
print(f"删集 {len(cand)} 张；独占层估算合计: {est:.1f} GB（未压缩口径）")
print("删序（预估独占降序）:")
for n in sorted(cand, key=lambda x: -per[x]):
    print(f"  {per[n]:6.2f}GB est  {pool[n][1]:>7}  {n}")
json.dump({"per": per, "est": est, "order": sorted(cand, key=lambda x: -per[x])},
          open(f"{OUT}/layer-est.json", "w"), ensure_ascii=False, indent=1)
