#!/bin/bash
# run-all.sh — 15 目标机制卡批跑驱动：并发≤2；失败重试一次；配额熔断全批停。
set -u
ROOT="$HOME/m31f-mechcards"
SLUGS="react reflexion voyager swe-agent memgpt metagpt camel gptswarm delm mad aflow adas langgraph autogen crewai"
export PATH="$HOME/.npm-global/bin:$PATH"

: > "$ROOT/status.tsv"
: > "$ROOT/batch.log"

have_quota() { grep -q "^QUOTA " "$ROOT/status.tsv" 2>/dev/null; }

ok_of() { # ok_of <slug> -> 最后一次 R 行 rc
  grep "^R $SLUG " "$ROOT/status.tsv" 2>/dev/null | tail -1 | awk '{print $3}'
}

launch() {
  local s="$1"
  echo "[batch] $(date '+%F %T') launch pass=$PASS slug=$s" >> "$ROOT/batch.log"
  ( bash "$ROOT/run-one.sh" "$s" >> "$ROOT/batch.log" 2>&1 ) &
}

PASS=1
for pass in 1 2; do
  PASS=$pass
  for s in $SLUGS; do
    have_quota && break 2
    if [ "$pass" -eq 2 ]; then
      rc=$(ok_of "$s")
      [ "$rc" = "0" ] && continue   # 第一遍已成功，跳过
      echo "[batch] $(date '+%F %T') retry slug=$s (prev rc=$rc)" >> "$ROOT/batch.log"
    fi
    while [ "$(jobs -rp | wc -l)" -ge 2 ]; do wait -n; done
    launch "$s"
    sleep 5   # 错峰，降低同时打认证/网关的概率
  done
  wait
done

echo "[batch] $(date '+%F %T') BATCH_END" >> "$ROOT/batch.log"
echo "== status.tsv =="; cat "$ROOT/status.tsv"
