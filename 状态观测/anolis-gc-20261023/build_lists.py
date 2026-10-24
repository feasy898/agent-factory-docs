#!/usr/bin/env python3
"""anolis 核对版 GC 清单构建（2026-10-23）。源：A 在飞容器 / B 任务池 / C 10-22 台账。
输出 keep-list.txt + delete-candidates.txt + 分析摘要。只读盘点，不删。"""
import json, re, subprocess, sys

OUT = "/home/pan-ding/workspace/agent黑灯工厂/状态观测/anolis-gc-20261023"
RELAY = "/tmp/longcat-relay"

def ssh(args, timeout=120):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "anolis"] + args,
                       capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"ssh rc={r.returncode}: {r.stderr[-300:]}")
    return r.stdout

# ---------- 池 ----------
pool = {}  # name -> (id, size)
for line in ssh(["docker", "images", "--format", '"{{.ID}}|{{.Repository}}|{{.Tag}}|{{.Size}}"']).splitlines():
    if not line.strip(): continue
    i, repo, tag, size = line.split("|", 3)
    name = f"{repo}:{tag}"
    pool[name] = (i, size)

# ---------- A 在飞容器 ----------
ps_lines = ssh(["docker", "ps", "--format", '"{{.ID}}|{{.Image}}|{{.Names}}"']).splitlines()
A_names, A_ids, A_detail = set(), set(), []
for line in ps_lines:
    if not line.strip(): continue
    cid, img, name = line.split("|", 2)
    iid = ssh(["docker", "inspect", cid, "--format", '"{{.Image}}"']).strip()  # sha256:...
    iid = iid.replace("sha256:", "")[:12]
    A_ids.add(iid)
    A_detail.append((cid[:12], img, name, iid))
    if img in pool: A_names.add(img)
    # 该 ID 的所有 tag 也属在飞镜像
    for n, (pid, _) in pool.items():
        if pid == iid: A_names.add(n)

# ---------- B ----------
def readnames(path, col=0):
    out = []
    for l in open(path):
        l = l.strip()
        if not l: continue
        out.append(l.split()[col])
    return out

B1 = [f"swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest",
      f"swebench/sweb.eval.x86_64.django_1776_django-11095:latest",
      f"swebench/sweb.eval.x86_64.matplotlib_1776_matplotlib-22719:latest",
      f"swebench/sweb.eval.x86_64.pydata_1776_xarray-2905:latest",
      f"swebench/sweb.eval.x86_64.pydata_1776_xarray-4075:latest"]
B2 = set()
for f in ("all120.txt", "recovery-d.txt", "done-recovery.txt"):
    B2.update(readnames(f"{RELAY}/{f}"))
B2_ids = set()  # recovery 带来的镜像（按名）

# 采样聚合 9 题
SAMPLE_TASKS = ["django__django-10999","scikit-learn__scikit-learn-10908","sphinx-doc__sphinx-10435",
                "mwaskom__seaborn-3187","psf__requests-2317","pytest-dev__pytest-7205",
                "sphinx-doc__sphinx-7462","django__django-10097","django__django-14011"]
def task2img(t):
    repo, task = t.split("__", 1)
    return f"swebench/sweb.eval.x86_64.{repo}_1776_{task}:latest"
B3_sample = set(task2img(t) for t in SAMPLE_TASKS)

# D-33：收集各文件任务 ID（排除 m31f-120 全量口径与 arm 级 holes/meta）
d33_sets = {}
import glob
for p in sorted(glob.glob("/tmp/d33-*.json")):
    base = p.split("/")[-1]
    if base in ("d33-m31f-120.json", "d33-aggregate-now.json", "d33-holes.json"):
        continue
    try: d = json.load(open(p))
    except Exception: continue
    ids = set()
    def walk(v):
        if isinstance(v, str) and "__" in v and " " not in v: ids.add(v)
        elif isinstance(v, list):
            for x in v: walk(x)
        elif isinstance(v, dict):
            for k, x in v.items():
                if "__" in k and " " not in k: ids.add(k)
                walk(x)
    walk(d)
    if ids: d33_sets[base] = ids
d33_union = set().union(*d33_sets.values()) if d33_sets else set()
d33_imgs = set(task2img(t) for t in d33_union)
# 窄读法：仅 images.json 映射（任务镜像名）
d33_narrow = set(json.load(open("/tmp/d33-m31f-images.json")).values())

WHITE = re.compile(r"^swebench/sweb\.eval\.x86_64\.[a-z0-9_-]+_1776_.+:latest$")

keep = set()
keep_src = {}
def add(names, src):
    for n in names:
        if n in pool:
            keep.add(n); keep_src.setdefault(n, set()).add(src)

add(A_names, "A")
add(B1, "B1")
add(B2, "B2")
add(B3_sample, "B3-sample")
add(d33_imgs, "B3-d33-wide")
# add(d33_narrow, "B3-d33-narrow")  # 宽读法已含窄读法

foreign = [n for n in pool if not WHITE.match(n)]
cand = [n for n in pool if n not in keep and WHITE.match(n)]

def gb(s):
    m = re.match(r"([\d.]+)\s*([KMGT]?B)", s)
    if not m: return 0.0
    v = float(m.group(1)); u = m.group(2)
    return v * {"B":1e-9,"KB":1e-6,"MB":1e-3,"GB":1.0,"TB":1e3}[u]

print("=== 池 ===", len(pool), "张, 合计", round(sum(gb(v[1]) for v in pool.values()),1), "GB")
print("=== A 在飞 ===", len(A_detail), "容器")
for d in A_detail: print("   ", d)
print("=== B 源计数 ===")
print("  B1 T0:", len([n for n in B1 if n in pool]), "/", len(B1))
print("  B2 longcat 并集:", len(B2), "名（在池", len([n for n in B2 if n in pool]), "）")
print("  B3 sample-agg 9 题在池:", len([n for n in B3_sample if n in pool]), "/9")
print("  B3 d33 宽并集:", len(d33_union), "任务 →", len([n for n in d33_imgs if n in pool]), "张在池")
print("  d33 窄（images.json）:", len(d33_narrow), "张, 在池", len([n for n in d33_narrow if n in pool]))
for k, v in d33_sets.items(): print(f"    d33[{k}]: {len(v)} 任务")
print("=== 保留并集 ===", len(keep), "张,", round(sum(gb(pool[n][1]) for n in keep),1), "GB")
print("=== foreign（白名单外，只计数）===")
for n in foreign: print("   ", n, pool[n][1])
print("=== 删集候选 ===", len(cand), "张,", round(sum(gb(pool[n][1]) for n in cand),1), "GB")
for n in sorted(cand): print("   ", n, pool[n][1], "ID=" + pool[n][0])

with open(f"{OUT}/keep-list.txt", "w") as f:
    f.write("# keep-list 三源并集 " + "2026-10-23\n")
    for n in sorted(keep):
        f.write(f"{n}\t{pool[n][1]}\t{'+'.join(sorted(keep_src[n]))}\n")
with open(f"{OUT}/delete-candidates.txt", "w") as f:
    f.write("# delete-candidates 池-保留并集∩白名单 2026-10-23\n")
    for n in sorted(cand):
        f.write(f"{n}\t{pool[n][1]}\tID={pool[n][0]}\t不在保留源A/B\n")
# 落盘中间数据供 DRY-RUN
json.dump({"pool": pool, "A_names": sorted(A_names), "A_ids": sorted(A_ids),
           "A_detail": A_detail, "keep": sorted(keep), "cand": sorted(cand),
           "foreign": foreign, "d33_union": sorted(d33_union), "d33_narrow": sorted(d33_narrow),
           "B2": sorted(B2), "B1": B1, "B3_sample": sorted(B3_sample)},
          open(f"{OUT}/lists-data.json", "w"), ensure_ascii=False, indent=1)
print("written:", OUT)
