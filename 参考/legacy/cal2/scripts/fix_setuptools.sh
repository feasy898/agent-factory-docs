#!/bin/bash
# fix_setuptools.sh — bake setuptools into base images whose pip deps lack it (judge first-check needs both).
set -uo pipefail
export PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ PIP_TRUSTED_HOST=mirrors.aliyun.com
for img in \
  ghcr.io/laude-institute/t-bench/python-3-13:20250620 \
  ghcr.io/laude-institute/t-bench/python-3-13:latest \
  python:3.13-slim-bookworm ; do
  c="enh-st-$(echo "$img" | tr ':/.' '---')"
  docker rm -f "$c" >/dev/null 2>&1
  echo "[st] fixing $img"
  docker run -d --name "$c" "$img" sleep infinity >/dev/null || { echo "[st] RUN FAIL $img"; continue; }
  docker exec "$c" bash -c 'PY=$(command -v python3 || command -v python); $PY -m pip install -q --break-system-packages setuptools 2>/dev/null || $PY -m pip install -q setuptools || echo "[st] PIP FAIL"'
  if docker exec "$c" bash -c 'PY=$(command -v python3 || command -v python); $PY -c "import pytest, setuptools" 2>/dev/null'; then
    docker commit "$c" "$img" >/dev/null && echo "[st] committed $img"
  else
    echo "[st] VERIFY FAIL $img (not committed)"
  fi
  docker rm -f "$c" >/dev/null
done
echo "[st] ALL DONE"
