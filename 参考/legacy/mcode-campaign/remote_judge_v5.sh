#!/bin/bash
# remote_judge_v4.sh — campaign judge on anolis (v4: v3 + 超时杀容器，根除孤儿)。
# v2 修复：旧版与其他 bench 会话（grok/zcode）共用 tbtask-<task> 镜像名，且旧进程被杀后
# 遗留无 pytest 的镜像，导致判分复用陈旧镜像产出 pytest_missing 假失败。
# v2 改用 tb2-<task> 独占标签；镜像存在但探测缺 pytest 时强制重建。
# v3：判完不删镜像（KEEP_IMAGE=1，默认开），跨波次复用；anolis /data 有 140G 可缓存 ~48 题镜像。
# KEEP_IMAGE=0 时恢复旧行为（判完即删）。
# v4b：timeout 只杀 docker CLI（--sig-proxy=false 不转发信号），挂死的 pytest 容器会成孤儿继续烧 CPU。
# v4 给判分容器命名，timeout 返回后显式 docker kill，确保容器退出（--rm 自动清理）。
# Usage (on anolis): remote_judge_v2.sh <campaign_dir> <task> <run_tag> <run_tag> ...
#   run_tag = <arm>__<task>-r<n>  (scratch at $campaign_dir/runs/<arm>/<task>-r<n>/work)
# Result JSON written to $campaign_dir/results/<run_tag>.json ; exit 0 always (infra recorded in JSON).
set -uo pipefail
CAMP="$1"; TASK="$2"; shift 2
GRADING_HOME="/home/pan-ding/bench/.grading-b6a766c909"
TASKS_HOME="/home/pan-ding/bench/tasks"
TASK_DIR="$TASKS_HOME/$TASK"
LOG="$CAMP/logs/judge-$TASK.log"
mkdir -p "$CAMP/results" "$CAMP/logs"
img_tag="tb2-$TASK"

judge_one() {
  local tag="$1" arm="${1%%__*}" rest="${1#*__}"
  local scratch="$CAMP/runs/$arm/$rest/work"
  local out="$CAMP/results/$tag.json"
  if [ ! -d "$scratch" ]; then echo "{\"status\":\"infra\",\"reason\":\"no_scratch\",\"tag\":\"$tag\"}" > "$out"; return; fi
  local tdir; tdir=$(mktemp -d /tmp/tbcamp.XXXXXX)
  cp -r "$GRADING_HOME/$TASK/." "$tdir/" 2>/dev/null
  cp "$tdir/test.py" "$scratch/" 2>/dev/null || true
  local res; res=$(mktemp /tmp/tbcamprun.XXXXXX)
  # 假失败防护 1：pytest 不可用 → infra（环境缺陷，不是 agent 失败）
  local probe; probe=$(mktemp /tmp/tbcprobe.XXXXXX)
  docker run --rm --entrypoint bash "$img_tag:latest" -lc 'python3 -c "import pytest" >/dev/null 2>&1 && echo PYTEST_OK || echo PYTEST_MISSING' > "$probe" 2>&1
  if ! grep -q PYTEST_OK "$probe"; then
    echo "[judge] PYTEST_MISSING $img_tag tag=$tag -> infra" >> "$LOG"
    echo "{\"status\":\"infra\",\"reason\":\"pytest_missing\",\"tag\":\"$tag\"}" > "$out"
    rm -f "$probe"; return
  fi
  rm -f "$probe"
  local cname="tbj-$$-${tag//[^a-zA-Z0-9]/_}"
  timeout -k 30 900 docker run --name "$cname" --sig-proxy=false --rm \
    -v "$(realpath "$scratch")":/app -v "$tdir":/tests:ro -e TEST_DIR=/tests -w /app \
    "$img_tag:latest" \
    bash -lc 'PY=$(command -v python3 || command -v python); export PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ PIP_TRUSTED_HOST=mirrors.aliyun.com PIP_BREAK_SYSTEM_PACKAGES=1; ($PY -c "import pytest, setuptools" 2>/dev/null || pip3 install --break-system-packages -q pytest==8.4.1 setuptools 2>/dev/null || $PY -m pip install --break-system-packages -q pytest==8.4.1 setuptools 2>/dev/null); git config --global --add safe.directory "*" 2>/dev/null || true; $PY -m pytest $TEST_DIR/test_outputs.py -rA 2>/dev/null || $PY -m pytest /tests -rA' \
    > "$res" 2>&1
  local rc=$?
  # v4: timeout 只杀了 docker CLI；显式杀容器根除孤儿（--rm 下已退出的容器 kill 静默失败）
  docker kill "$cname" >/dev/null 2>&1 || true
  tail -60 "$res" >> "$LOG"
  # 假失败防护 2：输出里出现环境类错误（模块缺失/收集失败）→ infra
  # 仅判分环境自身错误才算 infra：pytest 缺失/PEP668/测试文件收集失败/解释器缺失。
  # agent 自带的 ImportError（如未编译扩展）是真实失败，不得误判为 infra。
  if [ $rc -ne 0 ] && grep -qE "No module named pytest|externally-managed|ERROR: collection|ERROR collecting|InterpreterNotFound|No such file or directory: /tests" "$res"; then
    echo "[judge] ENV_ERROR tag=$tag rc=$rc -> infra" >> "$LOG"
    echo "{\"status\":\"infra\",\"reason\":\"env_error\",\"tag\":\"$tag\"}" > "$out"
    rm -rf "$tdir" "$res"; return
  fi
  if [ $rc -eq 0 ]; then echo "{\"status\":\"pass\",\"tag\":\"$tag\"}" > "$out"
  elif [ $rc -eq 124 ]; then echo "{\"status\":\"infra\",\"reason\":\"test_timeout\",\"tag\":\"$tag\"}" > "$out"
  else echo "{\"status\":\"fail\",\"tag\":\"$tag\"}" > "$out"; fi
  rm -rf "$tdir" "$res"
}

# 镜像级构建锁：防止并发判分同一题目时构建上下文互相删除
LOCK="/tmp/.tb2build-$TASK.lock"
exec 8>"$LOCK"
flock 8
# 自愈：镜像已存在但探测缺 pytest（陈旧/他会话构建的镜像）→ 删除重建
if docker image inspect "$img_tag:latest" >/dev/null 2>&1; then
  if ! docker run --rm --entrypoint bash "$img_tag:latest" -lc 'python3 -c "import pytest"' >/dev/null 2>&1; then
    echo "[judge] stale image without pytest, rebuilding $img_tag" >> "$LOG"
    docker rmi "$img_tag:latest" >/dev/null 2>&1 || true
  fi
fi
if ! docker image inspect "$img_tag:latest" >/dev/null 2>&1; then
  echo "[judge] building $img_tag" >> "$LOG"
  bctx=$(mktemp -d /tmp/tbbuild.XXXXXX)
  cp -r "$TASK_DIR"/. "$bctx"/
  python3 - "$bctx/Dockerfile" << 'PY'
import sys, re
p = sys.argv[1]
text = open(p, encoding="utf-8", errors="replace").read()
inject = (
    "RUN mkdir -p /etc/pip && printf '[global]\\nindex-url=https://mirrors.aliyun.com/pypi/simple/\\ntrusted-host=mirrors.aliyun\\n' > /etc/pip/pip.conf || true\n"
    "RUN (sed -i 's|http://archive.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; "
    "s|http://security.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; "
    "s|http://deb.debian.org|https://mirrors.aliyun.com|g' "
    "/etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null || true)\n"
    "RUN (command -v pip3 >/dev/null 2>&1 || apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq python3-pip >/dev/null 2>&1 || python3 -m ensurepip --upgrade >/dev/null 2>&1 || true); (pip3 install --break-system-packages -q pytest==8.4.1 setuptools 2>/dev/null || python3 -m pip install --break-system-packages -q pytest==8.4.1 setuptools 2>/dev/null || pip install -q pytest==8.4.1 setuptools 2>/dev/null || true)\n"
)
lines = text.splitlines(keepends=True)
out = []
for l in lines:
    out.append(l if l.endswith("\n") else l + "\n")
    if re.match(r"(?i)^\s*FROM\s", l):
        out.append(inject)
open(p, "w", encoding="utf-8").write("".join(out))
PY
  if ! DOCKER_BUILDKIT=0 docker build -t "$img_tag:latest" "$bctx" >> "$LOG" 2>&1; then
    for tag in "$@"; do echo "{\"status\":\"infra\",\"reason\":\"build_failed\",\"tag\":\"$tag\"}" > "$CAMP/results/$tag.json"; done
    rm -rf "$bctx"; flock -u 8 2>/dev/null || true; exit 0
  fi
  rm -rf "$bctx"
fi
# v4b: 构建锁只覆盖构建段；判分段（docker run 同一已存在镜像）不持锁，
# 避免多波次判同题时互相阻塞（wave9/11 与 wave7/8/10 共享核心 10 题）。
flock -u 8 2>/dev/null || true

for tag in "$@"; do judge_one "$tag"; done
# v3: 默认保留镜像供后续波次复用；KEEP_IMAGE=0 时删
if [ "${KEEP_IMAGE:-1}" = "0" ]; then docker rmi "$img_tag:latest" >/dev/null 2>&1 || true; fi
flock -u 8 2>/dev/null || true
exit 0
