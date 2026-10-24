#!/bin/bash
# fix_ubuntu_base.sh — re-enhance ubuntu-24-04 handling PEP 668 (--break-system-packages).
set -uo pipefail
img="ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624"
c="enh-ubuntu-fix"
docker rm -f "$c" >/dev/null 2>&1
echo "[fix] enhancing $img"
docker run -d --name "$c" "$img" sleep infinity >/dev/null || { echo "[fix] RUN FAIL"; exit 1; }
docker exec "$c" bash -c '
  sed -i "s|http://archive.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; s|http://security.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; s|http://deb.debian.org|https://mirrors.aliyun.com|g" /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null || true
  mkdir -p /etc/pip && printf "[global]\nindex-url=https://mirrors.aliyun.com/pypi/simple/\ntrusted-host=mirrors.aliyun.com\nbreak-system-packages = true\n" > /etc/pip/pip.conf
  export PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ PIP_TRUSTED_HOST=mirrors.aliyun.com DEBIAN_FRONTEND=noninteractive PIP_BREAK_SYSTEM_PACKAGES=1
  PY=$(command -v python3 || command -v python)
  $PY -m pip install -q --break-system-packages pytest==8.4.1 numpy sympy scipy pillow beautifulsoup4 python-chess pyyaml scikit-learn pulp || echo "[fix] DEPS PARTIAL"
  $PY -c "import pytest, numpy, sympy, yaml, PIL, chess, sklearn, pulp; print(\"[fix] deps ok\")" || echo "[fix] DEPS VERIFY FAIL"
'
docker commit "$c" "$img" >/dev/null && echo "[fix] committed"
docker rm -f "$c" >/dev/null
