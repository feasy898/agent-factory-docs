#!/usr/bin/env python3
"""变体估算 v2：D33_extra/D1TOP_extra 必须排除其他所有保留源成员（防误删在飞波次镜像）。"""
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

dangling = [l.split("|")[0] for l in ssh(["docker", "images", "-f", "dangling=true", "--format", '"{{.ID}}|{{.Size}}"']).splitlines() if l.strip()]
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

def task2img(t):
    repo, task = t.split("__", 1)
    return f"swebench/sweb.eval.x86_64.{repo}_1776_{task}:latest"
D2_imgs = {task2img(t) for t in d["D2_tasks"]}
D1TOP_imgs = {task2img(t.replace("swebench/sweb.eval.x86_64.","").replace("_1776_","__").replace(":latest","")) for t in d["D1TOP"]}
SAMPLE = {"django__django-10999","scikit-learn__scikit-learn-10908","sphinx-doc__sphinx-10435",
          "mwaskom__seaborn-3187","psf__requests-2317","pytest-dev__pytest-7205",
          "sphinx-doc__sphinx-7462","django__django-10097","django__django-14011"}
SAMPLE_imgs = {task2img(t) for t in SAMPLE}
T0 = {"swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest",
      "swebench/sweb.eval.x86_64.django_1776_django-11095:latest",
      "swebench/sweb.eval.x86_64.matplotlib_1776_matplotlib-22719:latest",
      "swebench/sweb.eval.x86_64.pydata_1776_xarray-2905:latest",
      "swebench/sweb.eval.x86_64.pydata_1776_xarray-4075:latest"}
core_keep = D2_imgs | D1TOP_imgs | SAMPLE_imgs | T0 | A_names   # 除 D-33 外的全部保留源
D33 = set(json.load(open("/tmp/d33-m31f-images.json")).values())
D33_extra = {n for n in D33 if n in pool and n not in core_keep}
print(f"核心保留（除D-33）在池: {len([n for n in core_keep if n in pool])}")
print(f"D-33 36 张中与其他保留源不重叠的: {len(D33_extra)}")
for n in sorted(D33_extra): print("   ", pool[n][1], n)

def estimate(delete_set, protect_names):
    prot = set()
    for n in protect_names: prot.update(obj_layers.get(pool[n][0], []))
    for o in (A_ids | set(dangling)): prot.update(obj_layers.get(o, []))
    free = {}
    for n in delete_set:
        for dd in obj_layers.get(pool[n][0], []):
            if dd not in prot: free.setdefault(dd, []).append(n)
    est = sum(layer_size.get(dd, 0.0) for dd in free)
    per = {n: 0.0 for n in delete_set}
    for dd, ns in free.items():
        sz = layer_size.get(dd, 0.0)
        if len(ns) == 1: per[ns[0]] += sz
        else:
            for n in ns: per[n] += sz/len(ns)
    return est, per

V1 = set(cand)
V1a = V1 | D33_extra
prot1 = keep - V1
prot1a = (keep - V1a) | (core_keep & set(pool))   # V1a 下 D-33 不保，但核心保留全保
for name, ds, prot in (("V1（D-33 全保）", V1, prot1), ("V1a（D-33 仅保重叠）", V1a, prot1a)):
    est, per = estimate(ds, prot)
    print(f"{name}: 删 {len(ds)} 张, 独占层估算 {est:.1f} GB（未压缩口径）")
    bad = ds & prot
    print("   误删在保项:", sorted(bad) if bad else "无")
json.dump({"V1a": sorted(V1a), "D33_extra": sorted(D33_extra), "core_keep": sorted(core_keep)},
          open(f"{OUT}/variants2.json", "w"), ensure_ascii=False, indent=1)
