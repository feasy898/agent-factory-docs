#!/bin/bash
# remote_judge2.sh — 修复版判分器（v2）。
# v1 的假失败根因：基于 ghcr.io/laude-institute/t-bench/ubuntu-24-04 的任务镜像里没有 pip
# （`No module named pip`），构建期三种 pip 安装方式全部失败且被 `|| true` 吞掉，探针据此
# 把该题所有 run 判成 infra/pytest_missing（实测 9 题 × 全臂 = 判分数据整片作废）。
# v2 的修法：
#   (1) 构建注入先装 python3-pip（走阿里云 apt 源），再删 EXTERNALLY-MANAGED 解除 PEP668，
#       最后 pip 装 pytest，仍失败则退回 apt 装 python3-pytest；
#   (2) 探针改为"按判分时的同一套安装序列试装后再验"，不再要求镜像预置 pytest；
#   (3) 判分容器内的安装序列同步补上 apt 兜底与解除 PEP668。
# 用法与 v1 完全一致：remote_judge2.sh <campaign_dir> <task> <run_tag> ...
set -uo pipefail
CAMP="$1"; TASK="$2"; shift 2
GRADING_HOME="/home/pan-ding/bench/.grading-b6a766c909"
TASKS_HOME="/home/pan-ding/bench/tasks"
TASK_DIR="$TASKS_HOME/$TASK"
LOG="$CAMP/logs/judge-$TASK.log"
mkdir -p "$CAMP/results" "$CAMP/logs"
img_tag="tbtask-$TASK"

judge_one() {
  local tag="$1" arm="${1%%__*}" rest="${1#*__}"
  local scratch="$CAMP/runs/$arm/$rest/work"
  local out="$CAMP/results/$tag.json"
  if [ ! -d "$scratch" ]; then echo "{\"status\":\"infra\",\"reason\":\"no_scratch\",\"tag\":\"$tag\"}" > "$out"; return; fi
  local tdir; tdir=$(mktemp -d /tmp/tbcamp.XXXXXX)
  cp -r "$GRADING_HOME/$TASK/." "$tdir/" 2>/dev/null
  cp "$tdir/test.py" "$scratch/" 2>/dev/null || true
  local res; res=$(mktemp /tmp/tbcamprun.XXXXXX)
  # 假失败防护 1：探针按判分同序列试装 pytest，仍不可用才算环境缺陷
  local probe; probe=$(mktemp /tmp/tbcprobe.XXXXXX)
  docker run --rm --entrypoint bash "$img_tag:latest" -lc 'rm -f /usr/lib/python3*/EXTERNALLY-MANAGED 2>/dev/null; PY=$(command -v python3 || command -v python); export PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ PIP_TRUSTED_HOST=mirrors.aliyun.com PIP_BREAK_SYSTEM_PACKAGES=1; ($PY -c "import pytest" >/dev/null 2>&1) || pip3 install --break-system-packages -q pytest==8.4.1 setuptools >/dev/null 2>&1 || $PY -m pip install --break-system-packages -q pytest==8.4.1 setuptools >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq --no-install-recommends python3-pytest python3-setuptools >/dev/null 2>&1) || true; python3 -c "import pytest" >/dev/null 2>&1 && echo PYTEST_OK || echo PYTEST_MISSING' > "$probe" 2>&1
  if ! grep -q PYTEST_OK "$probe"; then
    echo "[judge2] PYTEST_MISSING $img_tag tag=$tag -> infra" >> "$LOG"
    echo "{\"status\":\"infra\",\"reason\":\"pytest_missing\",\"tag\":\"$tag\"}" > "$out"
    rm -f "$probe"; return
  fi
  rm -f "$probe"
  timeout -k 30 900 docker run --sig-proxy=false --rm \
    -v "$(realpath "$scratch")":/app -v "$tdir":/tests:ro -e TEST_DIR=/tests -w /app \
    "$img_tag:latest" \
    bash -lc 'PY=$(command -v python3 || command -v python); export PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ PIP_TRUSTED_HOST=mirrors.aliyun.com PIP_BREAK_SYSTEM_PACKAGES=1; rm -f /usr/lib/python3*/EXTERNALLY-MANAGED 2>/dev/null || true; ($PY -c "import pytest, setuptools" 2>/dev/null || pip3 install --break-system-packages -q pytest==8.4.1 setuptools 2>/dev/null || $PY -m pip install --break-system-packages -q pytest==8.4.1 setuptools 2>/dev/null || (apt-get update -qq && apt-get install -y -qq --no-install-recommends python3-pytest python3-setuptools 2>/dev/null) || true); git config --global --add safe.directory "*" 2>/dev/null || true; $PY -m pytest $TEST_DIR/test_outputs.py -rA 2>/dev/null || $PY -m pytest /tests -rA' \
    > "$res" 2>&1
  local rc=$?
  tail -60 "$res" >> "$LOG"
  # 假失败防护 2：输出里出现环境类错误（判分环境自身）→ infra；agent 自身的 ImportError 属真实失败
  if [ $rc -ne 0 ] && grep -qE "No module named pytest|externally-managed|ERROR: collection|ERROR collecting|InterpreterNotFound|No such file or directory: /tests" "$res"; then
    echo "[judge2] ENV_ERROR tag=$tag rc=$rc -> infra" >> "$LOG"
    echo "{\"status\":\"infra\",\"reason\":\"env_error\",\"tag\":\"$tag\"}" > "$out"
    rm -rf "$tdir" "$res"; return
  fi
  if [ $rc -eq 0 ]; then echo "{\"status\":\"pass\",\"tag\":\"$tag\"}" > "$out"
  elif [ $rc -eq 124 ]; then echo "{\"status\":\"infra\",\"reason\":\"test_timeout\",\"tag\":\"$tag\"}" > "$out"
  else echo "{\"status\":\"fail\",\"tag\":\"$tag\"}" > "$out"; fi
  rm -rf "$tdir" "$res"
}

# 镜像级构建锁：防止并发判分同一题目时构建上下文互相删除
LOCK="/tmp/.tbbuild-$2.lock"
exec 8>"$LOCK"
flock 8
if ! docker image inspect "$img_tag:latest" >/dev/null 2>&1; then
  echo "[judge2] building $img_tag" >> "$LOG"
  bctx=$(mktemp -d /tmp/tbbuild.XXXXXX)
  cp -r "$TASK_DIR"/. "$bctx"/
  python3 - "$bctx/Dockerfile" << 'PY'
import sys, re
p = sys.argv[1]
text = open(p, encoding="utf-8", errors="replace").read()
inject = (
    "RUN mkdir -p /etc/pip && printf '[global]\\nindex-url=https://mirrors.aliyun.com/pypi/simple/\\ntrusted-host=mirrors.aliyun.com\\n' > /etc/pip/pip.conf || true\n"
    "RUN (sed -i 's|http://archive.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; "
    "s|http://security.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; "
    "s|http://deb.debian.org|https://mirrors.aliyun.com|g' "
    "/etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null || true)\n"
    "RUN (rm -f /usr/lib/python3*/EXTERNALLY-MANAGED 2>/dev/null; "
    "command -v pip3 >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq --no-install-recommends python3-pip >/dev/null 2>&1) || true; "
    "pip3 install --break-system-packages -q pytest==8.4.1 setuptools >/dev/null 2>&1 || "
    "python3 -m pip install --break-system-packages -q pytest==8.4.1 setuptools >/dev/null 2>&1 || "
    "(apt-get update -qq && apt-get install -y -qq --no-install-recommends python3-pytest python3-setuptools >/dev/null 2>&1) || true)\n"
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
    rm -rf "$bctx"; exit 0
  fi
  rm -rf "$bctx"
fi

for tag in "$@"; do judge_one "$tag"; done
docker rmi "$img_tag:latest" >/dev/null 2>&1 || true
flock -u 8 2>/dev/null || true
exit 0
