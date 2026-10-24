#!/usr/bin/env python3
"""anolis 核对版 GC 清单 v2（B 路线·收缩保留集，2026-10-23 厂长裁决）。
保留源：A 在飞容器（实时）∪ B①T0五件 ∪ B②-D2 在飞波次（driver --tasks 实测）∪
        B②-D1 topup 待补（missing-d1.txt）∪ B③ sample-agg 9 题 ∪ B③ D-33 窄集 36 张。
另做独占层估算（diff-ID  exclusivity + docker history 大小）预测 df 实收与删序。"""
import json, re, subprocess, sys, glob

OUT = "/home/pan-ding/workspace/agent黑灯工厂/状态观测/anolis-gc-20261023"
RUN = "/tmp/af-longcat-run"
RELAY = "/tmp/longcat-relay"

def ssh(args, timeout=180):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "anolis"] + args,
                       capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"ssh rc={r.returncode}: {(r.stderr or '')[-300:]}")
    return r.stdout

def task2img(t):
    repo, task = t.split("__", 1)
    return f"swebench/sweb.eval.x86_64.{repo}_1776_{task}:latest"

# ---------- 池（tag 名→ID,SIZE） ----------
pool = {}
for line in ssh(["docker", "images", "--format", '"{{.ID}}|{{.Repository}}|{{.Tag}}|{{.Size}}"']).splitlines():
    if not line.strip(): continue
    i, repo, tag, size = line.split("|", 3)
    pool[f"{repo}:{tag}"] = (i, size)

# ---------- A：实时在飞容器 ----------
ps_lines = ssh(["docker", "ps", "--format", '"{{.ID}}|{{.Image}}|{{.Names}}"']).splitlines()
A_names, A_ids, A_detail = set(), set(), []
for line in ps_lines:
    if not line.strip(): continue
    cid, img, name = line.split("|", 2)
    iid = ssh(["docker", "inspect", cid, "--format", '"{{.Image}}"']).strip().replace("sha256:", "")[:12]
    A_ids.add(iid); A_detail.append((cid[:12], img, name, iid))
    if img in pool: A_names.add(img)
    for n, (pid, _) in pool.items():
        if pid == iid: A_names.add(n)
# 悬空但在用的镜像 ID（无 tag，docker images 不列）
dangling_inuse = A_ids - {pool[n][0] for n in pool}

# ---------- B 源 ----------
B1 = [f"swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest",
      f"swebench/sweb.eval.x86_64.django_1776_django-11095:latest",
      f"swebench/sweb.eval.x86_64.matplotlib_1776_matplotlib-22719:latest",
      f"swebench/sweb.eval.x86_64.pydata_1776_xarray-2905:latest",
      f"swebench/sweb.eval.x86_64.pydata_1776_xarray-4075:latest"]

# D2 在飞波次：解析本机 af-bench-longcat driver --tasks（多题者即 D2 波）
D2_tasks = set()
for c in glob.glob("/proc/[0-9]*/cmdline"):
    try: argv = open(c, "rb").read().decode("utf-8", "ignore").split("\0")
    except Exception: continue
    if not any("af-bench-longcat" in a for a in argv): continue
    if "--tasks" not in argv: continue
    ti = argv.index("--tasks")
    tasks = [t for t in argv[ti+1].split(",") if t]
    if len(tasks) > 1:  # D2 波为整单；topup 为单题
        D2_tasks.update(tasks)
D2_imgs = {task2img(t) for t in D2_tasks}

# D1 topup 待补（实测 missing-d1.txt）
D1TOP = {l.strip() for l in open(f"{RELAY}/missing-d1.txt") if l.strip()}
D1TOP_imgs = {task2img(t.replace("swebench/sweb.eval.x86_64.", "").replace("_1776_", "__").replace(":latest", "")) for t in D1TOP}

SAMPLE_TASKS = ["django__django-10999","scikit-learn__scikit-learn-10908","sphinx-doc__sphinx-10435",
                "mwaskom__seaborn-3187","psf__requests-2317","pytest-dev__pytest-7205",
                "sphinx-doc__sphinx-7462","django__django-10097","django__django-14011"]
B3_sample = {task2img(t) for t in SAMPLE_TASKS}
D33_narrow = set(json.load(open("/tmp/d33-m31f-images.json")).values())

WHITE = re.compile(r"^swebench/sweb\.eval\.x86_64\.[a-z0-9_-]+_1776_.+:latest$")

keep, keep_src = set(), {}
def add(names, src):
    for n in names:
        if n in pool:
            keep.add(n); keep_src.setdefault(n, set()).add(src)

add(A_names, "A"); add(B1, "B1-T0"); add(D2_imgs, "B2-D2波"); add(D1TOP_imgs, "B2-D1topup")
add(B3_sample, "B3-sample"); add(D33_narrow, "B3-D33窄")
foreign = [n for n in pool if not WHITE.match(n)]
cand = sorted(n for n in pool if n not in keep and WHITE.match(n))

# ---------- 独占层估算 ----------
# 收集全部镜像对象（tag + 悬空在用）的 diff-ID 集
all_ids = sorted({pool[n][0] for n in pool} | dangling_inuse)
inspect_out = ssh(["docker", "image", "inspect"] + all_ids +
                  ["--format", '"{{.Id}} {{range .RootFS.Layers}}{{.}} {{end}}"'], timeout=300)
obj_layers = {}
for line in inspect_out.splitlines():
    p = line.split()
    if len(p) < 2: continue
    obj_layers[p[0].replace("sha256:", "")[:12]] = p[1:]
# 每镜像层大小：history（newest-first）反序对齐 RootFS.Layers
remote = r'''
for id in $(docker images -a -q --no-trunc | sort -u); do
  short=${id:0:12}
  sizes=$(docker history --format '{{.Size}}' "$id" 2>/dev/null | tac | tr '\n' ',')
  echo -e "$short\t$sizes"
done
'''
hist_out = ssh(["bash", "-c", f"'{remote}'"], timeout=600)
layer_size = {}
hist_map = {}
for line in hist_out.splitlines():
    if "\t" not in line: continue
    iid, s = line.split("\t", 1)
    hist_map[iid] = [x.strip() for x in s.split(",") if x.strip()]
def parse_size(s):
    m = re.match(r"([\d.]+)\s*([kMGT]?B)", s)
    if not m: return 0.0
    return float(m.group(1)) * {"B":1e-9,"kB":1e-6,"KB":1e-6,"MB":1e-3,"GB":1.0,"TB":1e3}[m.group(2)]
mismatch = 0
for iid, layers in obj_layers.items():
    hs = hist_map.get(iid, [])
    if len(hs) != len(layers):
        mismatch += 1
        hs = (hs + ["0B"] * len(layers))[:len(layers)] if hs else ["0B"] * len(layers)
    for d, s in zip(layers, hs):
        v = parse_size(s)
        if d not in layer_size or v > layer_size[d]: layer_size[d] = v

keep_objs = {pool[n][0] for n in keep} | {A_ids and i for i in A_ids} | dangling_inuse
# 注意：A_ids 是集合；上面写法取并集
keep_objs = {pool[n][0] for n in keep} | set(A_ids) | set(dangling_inuse)
protected = set()
for o in keep_objs:
    protected.update(obj_layers.get(o, []))
free_layers = {}
for n in cand:
    for d in obj_layers.get(pool[n][0], []):
        if d not in protected:
            free_layers.setdefault(d, []).append(n)
est_total = sum(layer_size.get(d, 0.0) for d in free_layers)
# 每候选的预估独占（该层仅被它一个删除候选引用时全额，否则按 1/N 摊）
per_img = {n: 0.0 for n in cand}
for d, ns in free_layers.items():
    sz = layer_size.get(d, 0.0)
    if len(ns) == 1: per_img[ns[0]] += sz
    else:
        for n in ns: per_img[n] += sz / len(ns)

print("=== 池 ===", len(pool), "tag；白名单内", len([n for n in pool if WHITE.match(n)]))
print("=== A 在飞（实时）===")
for d in A_detail: print("   ", d)
print("    悬空在用:", dangling_inuse)
print("=== B 源 ===")
print("  B1 T0 在池:", len([n for n in B1 if n in pool]), "/5")
print("  D2 波任务:", len(D2_tasks), "→ 在池", len([n for n in D2_imgs if n in pool]))
print("  D1topup(missing-d1):", len(D1TOP), "→ 在池", len([n for n in D1TOP_imgs if n in pool]))
print("  sample-agg 9:", len([n for n in B3_sample if n in pool]), "/9")
print("  D33 窄集 36:", len([n for n in D33_narrow if n in pool]), "/36")
print("=== 保留并集 ===", len(keep), "张")
print("=== foreign（只计数）===")
for n in foreign: print("   ", n, pool[n][1])
print("=== 删集 ===", len(cand), "张；SIZE 列和", round(sum(parse_size(pool[n][1]) for n in cand), 1), "GB")
print("=== 独占层估算 ===", f"{est_total:.1f} GB（history 对齐失配 {mismatch} 个镜像）")
print("=== 删序（预估独占降序）===")
for n in sorted(cand, key=lambda x: -per_img[x]):
    print(f"   {per_img[n]:6.2f}GB  {pool[n][1]:>7}  {n}")
# DRY-RUN
cand_ids = {pool[n][0] for n in cand}
print("=== DRY-RUN ===")
print("  删集 ∩ A名:", sorted(set(cand) & A_names))
print("  删集ID ∩ 在飞ID:", sorted(cand_ids & A_ids))
print("  删集 ∩ 保留:", sorted(set(cand) & keep))
ok = not (set(cand) & A_names) and not (cand_ids & A_ids) and not (set(cand) & keep)
print("  结论:", "PASS" if ok else "FAIL-停步")

json.dump({"pool": pool, "A_names": sorted(A_names), "A_ids": sorted(A_ids),
           "A_detail": A_detail, "dangling_inuse": sorted(dangling_inuse),
           "keep": sorted(keep), "cand": cand, "foreign": foreign,
           "D2_tasks": sorted(D2_tasks), "D1TOP": sorted(D1TOP),
           "per_img_est": per_img, "est_total": est_total},
          open(f"{OUT}/lists-data-v2.json", "w"), ensure_ascii=False, indent=1)
with open(f"{OUT}/keep-list-v2.txt", "w") as f:
    f.write("# keep-list v2（B 路线收缩版）2026-10-23\n")
    for n in sorted(keep): f.write(f"{n}\t{pool[n][1]}\t{'+'.join(sorted(keep_src[n]))}\n")
with open(f"{OUT}/delete-candidates-v2.txt", "w") as f:
    f.write("# delete-candidates v2（B 路线）2026-10-23：名\tSIZE\tID\t预估独占GB\t可删理由\n")
    for n in sorted(cand, key=lambda x: -per_img[x]):
        f.write(f"{n}\t{pool[n][1]}\tID={pool[n][0]}\t{per_img[n]:.2f}\t不在保留源A/B①/B②(D2波+D1topup)/B③；relay2r.sh+recovery-d.txt 可重灌\n")
print("written v2 artifacts")
