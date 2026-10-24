#!/bin/bash
# fix_ubuntu3.sh — restore ubuntu-24-04 judge deps: apt pip (with retries) -> break-system-packages deps.
# Only commits if offline-style verify passes inside the container.
set -uo pipefail
img="ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624"
c="enh-ubuntu-fix3"
docker rm -f "$c" >/dev/null 2>&1
echo "[f3] enhancing $img"
docker run -d --name "$c" "$img" sleep infinity >/dev/null || { echo "[f3] RUN FAIL"; exit 1; }
docker exec "$c" bash -c '
  sed -i "s|http://archive.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g; s|http://security.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g" /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null || true
  mkdir -p /etc/pip && printf "[global]\nindex-url=https://mirrors.aliyun.com/pypi/simple/\ntrusted-host=mirrors.aliyun.com\nbreak-system-packages = true\n" > /etc/pip/pip.conf
  export PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ PIP_TRUSTED_HOST=mirrors.aliyun.com DEBIAN_FRONTEND=noninteractive PIP_BREAK_SYSTEM_PACKAGES=1
  PY=$(command -v python3 || command -v python)
  for i in 1 2 3; do
    apt-get update -qq 2>/dev/null && apt-get install -y -qq python3-pip 2>/dev/null && break
    echo "[f3] apt retry $i"; sleep 5
  done
  if ! $PY -m pip --version >/dev/null 2>&1; then echo "[f3] NO_PIP_AFTER_APT"; exit 1; fi
  for i in 1 2 3; do
    $PY -m pip install -q --break-system-packages pytest==8.4.1 setuptools numpy sympy scipy pillow beautifulsoup4 python-chess pyyaml scikit-learn pulp && break
    echo "[f3] pip retry $i"; sleep 5
  done
  $PY -c "import pytest, setuptools, numpy, sympy, yaml, PIL, chess, sklearn, pulp; print(\"[f3] deps ok\")" || { echo "[f3] VERIFY FAIL"; exit 1; }
'
rc=$?
if [ $rc -eq 0 ]; then
  docker commit "$c" "$img" >/dev/null && echo "[f3] committed"
else
  echo "[f3] NOT COMMITTED (rc=$rc)"
fi
docker rm -f "$c" >/dev/null
