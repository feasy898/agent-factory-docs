#!/bin/bash
# scan_confirm_false_fail.sh — 扫描复测波次的 mcode run 级假失败（锁/取消/配额）。
CM=/home/pan-ding/campaign-mcode
for w in confirm-mem-prompt confirm-mem-tool confirm-mem-mixed; do
  ld="$CM/$w/logs"
  [ -d "$ld" ] || continue
  n=$(grep -rlE "mcode exec (failed|cancelled)" "$ld" --include="*.mcode.log" 2>/dev/null | wc -l)
  db=$(grep -rl "database is locked" "$ld" --include="*.mcode.log" 2>/dev/null | wc -l)
  q=$(grep -rl "Token Plan 用量上限\|insufficient_balance" "$ld" --include="*.mcode.log" 2>/dev/null | wc -l)
  echo "$w: runlevel_fail_logs=$n db_locked=$db quota=$q"
done
