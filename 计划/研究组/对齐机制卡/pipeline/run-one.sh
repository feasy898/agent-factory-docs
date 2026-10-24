#!/bin/bash
# run-one.sh <slug> — 单张机制卡 headless 跑（样板复刻 tools/mcode-dispatch.py RUN_ONE 段）。
# rc: 0=成功且六节齐全; 3=跑完但卡片无效(空/缺节); 42=配额熔断
set -uo pipefail
ROOT="$HOME/m31f-mechcards"
SLUG="${1:?slug}"
PROMPT="$ROOT/prompts/$SLUG.txt"
CARD="$ROOT/cards/$SLUG.md"
LOG="$ROOT/logs/$SLUG.log"
TMO=900   # 单卡硬上限 15 分钟

valid() {
  local f="$1"
  [ -s "$f" ] || return 1
  [ "$(wc -c <"$f")" -ge 600 ] || return 1
  local m
  for m in "① 核心机制" "② 组件清单" "③ 数据与上下文流" "④ 失败处理与停止条件" "⑤ 预算与评估方式" "⑥ DSL 表达点清单"; do
    grep -q "$m" "$f" || return 1
  done
  return 0
}

export PATH="$HOME/.npm-global/bin:$PATH"
python3 "$HOME/mcode-swev/auth-sync.py" >>"$LOG" 2>&1 || echo "[run-one] auth-sync 失败（继续，用现有凭证）" >>"$LOG"
S=$(date +%s)
timeout -k 60 "$TMO" mcode exec --cwd "$ROOT" --model "minimax/MiniMax-M3.1-Flash" \
  --permission full --timeout 25m "$(cat "$PROMPT")" > "$CARD" 2>>"$LOG"
rc=$?
E=$(date +%s)

if grep -qi "insufficient_balance\|Token Plan 用量上限\|http_code.:402\|error code: 2067" "$CARD" "$LOG"; then
  echo "QUOTA $SLUG" >> "$ROOT/status.tsv"
  echo "R $SLUG 42 $((E-S)) $(wc -c <"$CARD" 2>/dev/null || echo 0)" >> "$ROOT/status.tsv"
  echo "[run-one] $SLUG QUOTA_HIT"; exit 42
fi

if [ "$rc" -eq 0 ] && valid "$CARD"; then
  echo "R $SLUG 0 $((E-S)) $(wc -c <"$CARD")" >> "$ROOT/status.tsv"
  echo "[run-one] $SLUG OK"; exit 0
fi
echo "R $SLUG 3 $((E-S)) $(wc -c <"$CARD" 2>/dev/null || echo 0)" >> "$ROOT/status.tsv"
echo "[run-one] $SLUG INVALID (rc=$rc)"; exit 3
