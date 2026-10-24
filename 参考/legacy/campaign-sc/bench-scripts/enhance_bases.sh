#!/bin/bash
# Enhance t-bench base images: aliyun mirrors + pip.conf + test deps; retag as original.
set -uo pipefail
DEPS="pytest==8.4.1 numpy sympy scipy pillow beautifulsoup4 python-chess pyyaml scikit-learn pulp"
enhance() {
  local img="$1"
  docker image inspect "$img" >/dev/null 2>&1 || { echo "[enh] pulling $img"; docker pull -q "$img" || { echo "[enh] PULL FAIL $img"; return 1; }; }
  local c="enh-$(echo "$img" | tr ':/.' '---')"
  docker rm -f "$c" >/dev/null 2>&1
  echo "[enh] enhancing $img"
  docker run -d --name "$c" "$img" sleep infinity >/dev/null || { echo "[enh] RUN FAIL $img"; return 1; }
  docker exec "$c" bash -c '
    sed -i "s|http://archive.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; s|http://security.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; s|http://deb.debian.org|https://mirrors.aliyun.com|g" /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null || true
    mkdir -p /etc/pip && printf "[global]\nindex-url=https://mirrors.aliyun.com/pypi/simple/\ntrusted-host=mirrors.aliyun.com\n" > /etc/pip/pip.conf
    export PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ PIP_TRUSTED_HOST=mirrors.aliyun.com DEBIAN_FRONTEND=noninteractive
    PY=$(command -v python3 || command -v python)
    if ! $PY -m pip --version >/dev/null 2>&1; then
      apt-get update -qq 2>/dev/null; apt-get install -y -qq python3-pip 2>/dev/null
    fi
    ($PY -m pip install -q '"$DEPS"') || echo "[enh] DEPS PARTIAL"
    $PY -c "import pytest, numpy, sympy, yaml, PIL, chess, sklearn, pulp; print(\"[enh] deps ok\")" || echo "[enh] DEPS VERIFY FAIL"
  '
  docker commit "$c" "$img" >/dev/null && echo "[enh] committed $img"
  docker rm -f "$c" >/dev/null
}
for img in \
  ghcr.io/laude-institute/t-bench/python-3-13:20250620 \
  ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624 \
  ghcr.io/laude-institute/t-bench/python-3-13:latest \
  python:3.11-slim \
  python:3.13-slim-bookworm ; do
  enhance "$img"
done
echo "[enh] ALL DONE"
