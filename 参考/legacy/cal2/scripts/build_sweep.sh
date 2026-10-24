#!/bin/bash
# build_sweep.sh — pre-build every cal2 task image once to prove the build path works; rmi after each.
# Same build logic as judge.sh (mirror injection after each FROM). Log: bench/logs/build_sweep.txt
set -u
BENCH=/home/pan-ding/bench
OUT="$BENCH/logs/build_sweep.txt"
: > "$OUT"
ok=0; bad=0
while read -r t; do
  [ -z "$t" ] && continue
  img="tbtask-$t:latest"
  free=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
  if [ "${free:-0}" -lt 2 ]; then echo "ABORT low_disk ${free}G at $t" >> "$OUT"; break; fi
  if docker image inspect "$img" >/dev/null 2>&1; then echo "$t PRESENT" >> "$OUT"; ok=$((ok+1)); continue; fi
  echo "[sweep] building $t $(date +%H:%M:%S)" >> "$OUT"
  bctx=$(mktemp -d /tmp/tbbuild.XXXXXX)
  cp -r "$BENCH/tasks/$t"/. "$bctx"/
  python3 - "$bctx/Dockerfile" << 'PY'
import sys, re
p = sys.argv[1]
text = open(p, encoding="utf-8", errors="replace").read()
inject = (
    "RUN mkdir -p /etc/pip && printf '[global]\\nindex-url=https://mirrors.aliyun.com/pypi/simple/\\n"
    "trusted-host=mirrors.aliyun.com\\n' > /etc/pip/pip.conf || true\n"
    "RUN (sed -i 's|http://archive.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; "
    "s|http://security.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; "
    "s|http://deb.debian.org|https://mirrors.aliyun.com|g' "
    "/etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null || true)\n"
)
lines = text.splitlines(keepends=True)
out = []
for l in lines:
    out.append(l if l.endswith("\n") else l + "\n")
    if re.match(r"(?i)^\s*FROM\s", l):
        out.append(inject)
open(p, "w", encoding="utf-8").write("".join(out))
PY
  if DOCKER_BUILDKIT=0 docker build -t "$img" "$bctx" >> "$OUT" 2>&1; then
    echo "$t BUILD_OK" >> "$OUT"; ok=$((ok+1))
  else
    echo "$t BUILD_FAIL" >> "$OUT"; bad=$((bad+1))
  fi
  rm -rf "$bctx"
  docker rmi "$img" >/dev/null 2>&1 || true
done < "$BENCH/jobs/cal2_tasks.txt"
echo "SWEEP_DONE ok=$ok bad=$bad $(df -h / | tail -1)" >> "$OUT"
