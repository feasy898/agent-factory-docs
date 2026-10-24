#!/usr/bin/env python3
"""Prepare a scratch dir for one bench run: copy Dockerfile-provisioned files into
/app-relative layout and write the uniform instruction prompt.

Usage: prepare_task.py <task_dir> <scratch_dir> <prompt_out>
"""
import os
import re
import shlex
import shutil
import sys

PREAMBLE = """\
You are solving a Terminal-Bench task. Work entirely inside your current working \
directory. At grading time your working directory will be mounted at /app inside a \
fresh container built from the task's Dockerfile, and the task's pytest suite will \
run there. Paths in the task starting with /app correspond to paths relative to \
your current working directory.

Host environment: Linux x86_64. Available: bash, python3 (with numpy, pandas, \
scikit-learn, sympy, scipy installed), git, jq, gcc, g++, make, openssl, curl. \
PyPI is reachable only via the mirror `pip install -i \
https://mirrors.aliyun.com/pypi/simple/ <pkg>`. GitHub/HuggingFace are NOT \
reachable; tasks must be solved with local files. Do NOT modify anything outside \
your working directory. You have roughly 25 minutes; when done, make sure every \
artifact the task requires exists under the requested paths relative to your \
working directory, then state DONE.

--- TASK INSTRUCTION (verbatim) ---
"""


def parse_copies(dockerfile_path: str):
    """Return list of (src, dst) from COPY/ADD lines. None if unsupported."""
    copies = []
    try:
        text = open(dockerfile_path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        u = line.upper()
        if u.startswith(("COPY", "ADD")):
            if "--from" in line.lower() or u.startswith("ADD"):
                return None
            # strip JSON-array form detection
            if line.split(None, 1)[1].strip().startswith("["):
                return None
            parts = shlex.split(line)
            flags = [p for p in parts if p.startswith("--")]
            args = [p for p in parts[1:] if not p.startswith("--")]
            if len(args) < 2:
                return None
            dest = args[-1]
            if not dest.startswith("/app"):
                return None
            for src in args[:-1]:
                copies.append((src, dest))
    return copies


def copy_into_scratch(task_dir: str, scratch: str, copies):
    for src, dest in copies:
        rel_dest = os.path.relpath(dest, "/app")
        s = os.path.join(task_dir, src)
        d = os.path.join(scratch, rel_dest)
        if not os.path.exists(s):
            # tolerate missing optional sources
            continue
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            os.makedirs(os.path.dirname(d) or ".", exist_ok=True)
            shutil.copy2(s, d)


def main():
    task_dir, scratch, prompt_out = sys.argv[1], sys.argv[2], sys.argv[3]
    copies = parse_copies(os.path.join(task_dir, "Dockerfile"))
    if copies is None:
        print("UNSUPPORTED_DOCKERFILE", file=sys.stderr)
        sys.exit(2)
    os.makedirs(scratch, exist_ok=True)
    copy_into_scratch(task_dir, scratch, copies)
    meta_sys = sys.modules.get("yaml")
    instr = None
    try:
        import yaml
        meta = yaml.safe_load(open(os.path.join(task_dir, "task.yaml"), encoding="utf-8"))
        instr = (meta.get("instruction") or "").strip()
    except Exception:
        pass
    if not instr:
        # crude fallback: strip canary, grab instruction block
        raw = open(os.path.join(task_dir, "task.yaml"), encoding="utf-8").read()
        m = re.search(r"instruction:\s*\|-\n((?:[ \t]+.*\n?)+)", raw)
        if not m:
            print("NO_INSTRUCTION", file=sys.stderr)
            sys.exit(3)
        instr = "\n".join(l.strip() for l in m.group(1).splitlines()).strip()
    with open(prompt_out, "w", encoding="utf-8") as f:
        f.write(PREAMBLE + "\n" + instr + "\n")
    print("OK")


if __name__ == "__main__":
    main()
