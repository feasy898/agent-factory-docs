#!/usr/bin/env python3
"""变体估算：V1（厂长指示保留集）/ V1a（去 D-33 窄集未重叠 18 张）/ V1b（再去 D1topup）。
并把悬空镜像对象纳入'现存对象'保护集。"""
import json, re, subprocess

OUT = "/home/pan-ding/workspace/agent黑灯工厂/状态观测/anolis-gc-20261023"
d = json.load(open(f"{OUT}/lists-data-v2.json"))
pool, keep, cand = d["pool"], set(d["keep"]), d["cand"]
A_ids, A_names = set(d["A_ids"]), set(d["A_names"])

def ssh(args, timeout=300):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "anolis"] + args,
                       capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    if r.returncode != 0: raise RuntimeError(r.stderr[-300:])
    return r.stdout

# 现存全部镜像对象（含悬空）
dangling = [l.split("|")[0] for l in ssh(["docker", "images", "-f", "dangling=true", "--format", '"{{.ID}}|{{.Size}}"']).splitlines() if l.strip()]
print("悬空对象:", dangling)
all_ids = sorted({v[0] for v in pool.values()} | A_ids | set(dangling))
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
layer_size = {}
for iid, layers in obj_layers.items():
    hs = [x for x in hist5.get(iid[:5], []) if parse_size(x) > 0]
    hs = (hs + ["0B"]*len(layers))[:len(layers)]
    for dd, s in zip(layers, hs):
        v = parse_size(s)
        if dd not in layer_size or v > layer_size[dd]: layer_size[dd] = v
dedup_uncompressed = sum(layer_size.values())
print(f"全池去重未压缩层总量: {dedup_uncompressed:.1f} GB（docker system df 实存 205.1GB → 压缩比 {205.1/dedup_uncompressed:.2f}）")

def estimate(delete_set):
    prot = set()
    for n in keep - set(delete_set): prot.update(obj_layers.get(pool[n][0], []))
    for o in (A_ids | set(dangling)): prot.update(obj_layers.get(o, []))
    free = {}
    for n in delete_set:
        for dd in obj_layers.get(pool[n][0], []):
            if dd not in prot: free.setdefault(dd, []).append(n)
    return sum(layer_size.get(dd, 0.0) for dd in free), len(free)

D33 = set(json.load(open("/tmp/d33-m31f-images.json")).values())
D33_extra = {n for n in D33 if n in pool and n not in cand and n not in A_names}
print(f"\nD-33 窄集在池 {len([n for n in D33 if n in pool])}，其中不在 V1 删集的: {len(D33_extra)}")
for n in sorted(D33_extra): print("   ", pool[n][1], n)

D1TOP_imgs = set()
for t in d["D1TOP"]:
    repo, task = t.replace("swebench/sweb.eval.x86_64.","").replace("_1776_","__").replace(":latest","").split("__",1)
    D1TOP_imgs.add(f"swebench/sweb.eval.x86_64.{repo}_1776_{task}:latest")
D1TOP_extra = {n for n in D1TOP_imgs if n in pool and n not in cand and n not in A_names}
print(f"\nD1topup 在池 {len([n for n in D1TOP_imgs if n in pool])}，其中不在 V1 删集的: {len(D1TOP_extra)}")

V1_set = set(cand)
V1a_set = V1_set | D33_extra
V1b_set = V1a_set | D1TOP_extra
for name, s in (("V1（厂长指示）", V1_set), ("V1a（+去D-33未重叠）", V1a_set), ("V1b（+去D1topup）", V1b_set)):
    est, nf = estimate(s)
    print(f"{name}: 删 {len(s)} 张, 独占层 {est:.1f} GB 未压缩（≈实存 {est*205.1/dedup_uncompressed:.1f} GB）, 释放层 {nf} 个")
