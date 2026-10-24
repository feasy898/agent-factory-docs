#!/usr/bin/env python3
"""path-lint.py — K5「DSL 白名单+路径 lint」门（沙箱复刻）。

判据（设计/RSI自我改进方案.md §8 K5 / §3 闸1 终审 R1）：
  补丁可写范围黑名单 = 判分核三件（swev-judge.py / 判分镜像 / swev-venv）
  + 观测闸自身（obs-checker.py + 写侧 obs.rs）+ 指纹登记表 + 索引/manifest 写侧。
  patch_meta 触碰清单 + 实际 diff 路径双查：命中黑名单即整补丁作废；
  声明清单未覆盖实际 diff 路径（谎报/漏报）同样作废。
"""
import argparse
import json
import re
import sys

# 黑名单（判分链三件 + 观测闸自身 + 登记与索引写侧）。匹配用子串+规范化路径。
BLACKLIST = [
    "tools/swev-judge.py",
    "工具状态备份/observability/obs-checker.py",
    "af/crates/af-bench/src/obs.rs",          # 观测写侧
    "af/crates/af-bench/src/obs/",            # 观测写侧目录形态
    "registry/fingerprints.json",             # 指纹登记表
    "obs-root/index/",                        # 索引/manifest 写侧
    "判分镜像",                                # 镜像 digest 钉定，禁改 tag/digest
    "swev-venv",                              # venv 指纹冻结
]


def norm(p):
    return p.replace("\\", "/").lstrip("./")


def hits_blacklist(path):
    n = norm(path)
    return [b for b in BLACKLIST if b in n or n in b]


def diff_paths(diff_text):
    out = []
    for line in diff_text.splitlines():
        m = re.match(r"diff --git a/(\S+) b/(\S+)", line)
        if m:
            out.append(m.group(2))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", required=True, help="patch_meta.json（含 touched 清单）")
    ap.add_argument("--diff", help="补丁 diff 文件（可选；给了就做谎报/漏报检测）")
    args = ap.parse_args()

    meta = json.load(open(args.meta, encoding="utf-8"))
    touched = [norm(t) for t in meta.get("touched", [])]
    bad = []

    print(f"== 路径 lint：补丁 {meta.get('patch_id', '?')} ==")
    print(f"声明触碰清单（{len(touched)} 项）: {touched}")
    for t in touched:
        h = hits_blacklist(t)
        if h:
            bad.append(f"触碰清单命中黑名单: {t} ← {h}")

    if args.diff:
        actual = [norm(p) for p in diff_paths(open(args.diff, encoding="utf-8").read())]
        print(f"实际 diff 路径（{len(actual)} 项）: {actual}")
        for p in actual:
            h = hits_blacklist(p)
            if h:
                bad.append(f"实际 diff 命中黑名单: {p} ← {h}")
        undeclared = [p for p in actual if p not in touched]
        if undeclared:
            bad.append(f"谎报/漏报触碰清单（实际改了但未声明）: {undeclared}")

    if bad:
        for b in bad:
            print(f"FAIL: {b}")
        print("RESULT: FAIL — 整补丁作废（黑名单路径/谎报触碰清单）")
        return 1
    print("RESULT: PASS — 触碰清单干净且与 diff 一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
