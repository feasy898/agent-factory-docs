#!/usr/bin/env python3
"""只读采集：anolis 镜像层证据（2026-10-23 层回收分析用）。

全量只读：df / docker ps / docker images -a / docker image inspect(RootFS.Layers+Size)
/ docker image history(Size 序列) / docker system df + df -v。
产物落 状态观测/anolis-gc-20261023/raw-20261023/：
  df.txt dfv.txt ps.txt images.txt inspect.tsv hist.tsv meta.json
"""
import json
import subprocess
import sys
import time

OUT = "/home/pan-ding/workspace/agent黑灯工厂/状态观测/anolis-gc-20261023/raw-20261023"
PREFIX = ["ssh", "-o", "ConnectTimeout=10", "anolis"]


def ssh(args, timeout=300):
    r = subprocess.run(PREFIX + args, capture_output=True, text=True,
                       timeout=timeout, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"rc={r.returncode} args={args[:4]}... err={r.stderr[-400:]}")
    return r.stdout


def main():
    t0 = time.time()
    meta = {}
    meta["as_of_host"] = ssh(["date", "-Is"]).strip()
    open(f"{OUT}/df.txt", "w").write(
        ssh(["df", "-P", "/data", "/"]) + "\n$ df -P /data /\n")
    open(f"{OUT}/dfv.txt", "w").write(ssh(["docker", "system", "df"], timeout=600)
                                      + "\n$ docker system df -v\n"
                                      + ssh(["docker", "system", "df", "-v"], timeout=600))
    open(f"{OUT}/ps.txt", "w").write(
        "$ docker ps -a --format '{{.ID}}|{{.Image}}|{{.Status}}|{{.Names}}'\n"
        + ssh(["docker", "ps", "-a", "--format",
               '"{{.ID}}|{{.Image}}|{{.Status}}|{{.Names}}"']).replace("|", "\t"))
    images = ssh(["docker", "images", "-a", "--format",
                  '"{{.Repository}}:{{.Tag}}|{{.ID}}|{{.Size}}"']).replace("|", "\t")
    open(f"{OUT}/images.txt", "w").write(
        "$ docker images -a --format '{{.Repository}}:{{.Tag}}|{{.ID}}|{{.Size}}' (| 已转 TSV)\n" + images)

    ids = sorted({ln.split("\t")[1] for ln in images.splitlines() if "\t" in ln})
    meta["image_object_count"] = len(ids)
    # inspect：ID, Size(展开和口径), RootFS.Layers(diff-id, 老在新前)。| 分隔本地转 TSV。
    insp = ssh(["docker", "image", "inspect"] + ids + ["--format",
               '"{{.Id}}|{{.Size}}|{{range .RootFS.Layers}}{{.}} {{end}}"'], timeout=600)
    insp = "\n".join(ln.replace("|", "\t", 2) for ln in insp.splitlines() if ln.strip()) + "\n"
    open(f"{OUT}/inspect.tsv", "w").write(insp)
    n_insp = sum(1 for ln in insp.splitlines() if ln.strip())
    meta["inspect_count"] = n_insp

    # history：每镜像一步 Size（docker 输出新在前）。远端单 ssh 循环，逐镜像 docker history。
    # 内部仅用双引号，整条命令用单引号包裹传输（ssh 朴素拼接远端 shell）。
    cmd = ("for id in " + " ".join(ids) + "; do "
           "printf \"%s\\t\" \"$id\"; "
           "docker image history \"$id\" --format \"{{.Size}}\" 2>/dev/null | paste -sd,; done")
    hist = ssh(["bash", "-c", "'" + cmd + "'"], timeout=900)
    open(f"{OUT}/hist.tsv", "w").write(hist)
    meta["hist_count"] = sum(1 for ln in hist.splitlines() if ln.strip())

    meta["as_of_done"] = time.strftime("%F %T")
    meta["elapsed_s"] = round(time.time() - t0, 1)
    meta["collect_cmd"] = ("ssh anolis: df -P; docker system df[-v]; docker ps -a; "
                           "docker images -a; docker image inspect <all-ids> "
                           "(Id,Size,RootFS.Layers); docker image history <each id> (Size)")
    json.dump(meta, open(f"{OUT}/meta.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
