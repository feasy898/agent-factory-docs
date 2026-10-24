#!/bin/bash
# judge_janitor.sh — 清理超时孤儿判分容器。
# 背景：remote_judge 的 timeout -k 30 900 只杀 docker CLI（--sig-proxy=false），
# pytest 挂死的容器成为孤儿继续运行烧 CPU。判分流每 tag 至多 930s（timeout+kill），
# 故 tb2-* 判分容器存活 >16 分钟必然是孤儿，可安全杀。
# 只动 tb2-* 镜像（本 campaign v3 判分器）；其他会话的 tbtask-* 容器不碰。
for c in $(docker ps -q); do
  img=$(docker inspect "$c" --format "{{.Config.Image}}" 2>/dev/null)
  case "$img" in
    tb2-*) ;;
    *) continue;;
  esac
  cmd=$(docker inspect "$c" --format "{{join .Config.Cmd \" \"}}" 2>/dev/null)
  case "$cmd" in
    bash*PY=*) ;;   # 判分容器（探针是 python3 -c import pytest，不匹配且秒退）
    *) continue;;
  esac
  started=$(docker inspect "$c" --format "{{.State.StartedAt}}" 2>/dev/null)
  age=$(( ( $(date +%s) - $(date -d "$started" +%s) ) / 60 ))
  if [ "$age" -gt 16 ]; then
    echo "[$(date '+%F %T')] killing orphan $c $img age=${age}min"
    docker kill "$c" >/dev/null 2>&1
  fi
done
