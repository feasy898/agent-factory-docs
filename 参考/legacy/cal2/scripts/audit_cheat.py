#!/usr/bin/env python3
"""Anti-cheat audit for the cal2 local workflow lanes (v2, false-positive controlled).

A canary string must be:
  - extracted from the task's grading tests (function names or distinctive literals), AND
  - absent from the task's legit corpus (the provided inputs + the instruction),
so a hit in an agent scratch means the agent saw grading material, not task inputs.
"""
import json
import os
import re
import subprocess
import sys

ROOT = "/home/pan-ding/workspace/临时工作区/temp1"
CAL = os.path.join(ROOT, "cal2")
ARCH = open("/home/pan-ding/.cal2-archive-path").read().strip()
SRC = os.path.join(ARCH, "tb-tasks/original-tasks")
TASKS = [l.strip() for l in open(os.path.join(CAL, "tasks.txt")) if l.strip()]
CONFIGS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["zcode-m3", "zcode-m31f", "zcode-s5", "zcode-router", "zcode-glm53", "zcode-glm53f"]
WHITELIST = {"multistep-definite-integral"}  # official COPY . /app design ships tests in the work dir


def read_text(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def legit_corpus(task):
    """All provided input files + the instruction = material the agent legitimately has."""
    parts = [read_text(os.path.join(CAL, "instr", task + ".md"))]
    base = os.path.join(CAL, "inputs", task)
    for dp, _, fs in os.walk(base):
        for f in fs:
            parts.append(read_text(os.path.join(dp, f)))
    return "\n".join(parts)


def canaries(task):
    tdir = os.path.join(SRC, task, "tests")
    cands = set()
    if os.path.isdir(tdir):
        for f in os.listdir(tdir):
            if not f.endswith(".py"):
                continue
            text = read_text(os.path.join(tdir, f))
            for m in re.finditer(r"def (test_\w+)", text):
                cands.add(m.group(1))
            for m in re.finditer(r"""['"]([^'"\n]{16,80})['"]""", text):
                s = m.group(1)
                if " " in s and not s.startswith(("http", "/")) and "{" not in s:
                    cands.add(s)
    corpus = legit_corpus(task)
    return {c for c in cands if c not in corpus}


def grep_dir(path, needle):
    try:
        r = subprocess.run(["grep", "-rIl", "--", needle, path], capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""


def main():
    task_canaries = {t: canaries(t) for t in TASKS}
    findings = []
    for cfg in CONFIGS:
        decl_path = os.path.join(CAL, "results", cfg, "declarations.json")
        decls = json.load(open(decl_path)) if os.path.exists(decl_path) else {}
        for t in TASKS:
            work = os.path.join(CAL, "runs", cfg, t, "work")
            if not os.path.isdir(work):
                continue
            hits = []
            for c in sorted(task_canaries[t]):
                g = grep_dir(work, c)
                if g:
                    hits.append((c, g.splitlines()[0]))
            declared = (decls.get(t) or {}).get("declared_clean")
            if hits or declared is False:
                findings.append({
                    "config": cfg, "task": t, "declared_clean": declared,
                    "grading_only_hits": hits[:5], "whitelisted": t in WHITELIST,
                    "verdict": "SUSPICIOUS" if (hits and t not in WHITELIST) else ("noted" if (hits or declared is False) else "ok"),
                })
    for f in findings:
        print(json.dumps(f, ensure_ascii=False))
    n_sus = sum(1 for f in findings if f["verdict"] == "SUSPICIOUS")
    print(f"\naudited {len(CONFIGS)} configs x {len(TASKS)} tasks; suspicious={n_sus}, noted={sum(1 for f in findings if f['verdict']=='noted')}")
    with open(os.path.join(CAL, "results", "audit.json"), "w") as fh:
        json.dump(findings, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
