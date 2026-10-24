#!/usr/bin/env bash
# ro-mount-check.sh — K3「闸1 verifier 只读挂载」实测（沙箱复刻，2026-10-22）。
# 判据（设计/RSI自我改进方案.md §3 闸1 / §8 K3）：
#   判分链三件（swev-judge.py / obs-checker.py / fingerprints.json 登记表）以只读
#   bind-mount 暴露给补丁流程；工作区写判分路径=拒绝（内核 EROFS），且挂载后字节不变。
# 形态与结论：
#   形态A 生产形态：父（宿主）命名空间 sudo 挂 ro，补丁流程（无 CAP_SYS_ADMIN）写 → EROFS。
#   形态B rootless 形态：unshare -rm 内挂 ro + capsh 降权（模拟无挂载权的补丁流程）→ EROFS。
#   形态B' 边界取证（非期望通过项）：同 unshare 内不降权 → remount rw 成功 = 挂载可被绕过，
#        故生产必须用形态A（或挂载后确保补丁流程无 CAP_SYS_ADMIN）。
# 对照：同一内容无只读挂载时 6 类写全部成功——证明拦截来自只读挂载本身。
set -u
# 位置自适配：可用 RSI_DRILL_ROOT 覆盖；缺省=脚本上级目录（归档包内直接可跑）
ROOT="${RSI_DRILL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CHAIN=$ROOT/chain
REG=$ROOT/registry
LOG=${1:-$ROOT/evidence/ro-mount}
mkdir -p "$LOG"
overall=0

restore_file() {  # 保证对照每个 op 前文件在位（rm/mv 会消耗目标）
  local base="$1" f="$2"
  [ -f "$base/$f" ] && return 0
  cp "$CHAIN/$f" "$base/$f" 2>/dev/null || cp "$REG/fingerprints.json" "$base/$f"
}

write_attempts() {  # $1=基准目录  $2=标签  $3=期望 reject|allow  [$4=capsh降权前缀]
  local base="$1" pre="$2" expect="$3" pfx="${4:-}"
  local rc=0 n_ok=0 n_bad=0 out rc_op
  for f in swev-judge.py obs-checker.py fingerprints.json; do
    for op in append cp rm mv chmod pywrite; do
      [ "$expect" = allow ] && restore_file "$base" "$f"
      out=$(eval "$pfx bash -c \"$(case $op in
          append) echo "echo '# inj4' >> '$base/$f'" ;;
          cp)     echo "cp '$REG/frozen/$f' '$base/$f' 2>/dev/null || cp '$REG/fingerprints.json' '$base/$f'" ;;
          rm)     echo "rm -f '$base/$f'" ;;
          mv)     echo "mv '$base/$f' '$base/$f.x'" ;;
          chmod)  echo "chmod 644 '$base/$f'" ;;
          pywrite) echo "python3 -c \\\"open('$base/$f','a').write('# inj4')\\\"" ;;
        esac)\"" 2>&1)
      rc_op=$?
      echo "[$pre/$f/$op] rc=$rc_op :: $(echo "$out" | head -1)"
      if [ $rc_op -eq 0 ]; then n_ok=$((n_ok+1)); else n_bad=$((n_bad+1)); fi
    done
  done
  echo "[$pre 汇总] 成功=$n_ok 失败=$n_bad"
  if [ "$expect" = reject ]; then [ $n_ok -eq 0 ] || rc=1; else [ $n_bad -eq 0 ] || rc=1; fi
  return $rc
}

echo "===== 形态A：真只读 bind-mount（sudo，父命名空间挂载） ====="
mkdir -p "$ROOT/chain-ro" "$ROOT/registry-ro"
sudo -n mount --bind "$CHAIN" "$ROOT/chain-ro" 2>&1 | tee "$LOG/mountA.log"
sudo -n mount -o remount,ro,bind "$ROOT/chain-ro" 2>&1 | tee -a "$LOG/mountA.log"
sudo -n mount --bind "$REG" "$ROOT/registry-ro" 2>&1 | tee -a "$LOG/mountA.log"
sudo -n mount -o remount,ro,bind "$ROOT/registry-ro" 2>&1 | tee -a "$LOG/mountA.log"
echo "chain-ro OPTIONS=[$(findmnt -no OPTIONS "$ROOT/chain-ro")] registry-ro OPTIONS=[$(findmnt -no OPTIONS "$ROOT/registry-ro")]" | tee "$LOG/mountA-opts.log"
write_attempts "$ROOT/chain-ro" "A-ro-chain" reject 2>&1 | tee "$LOG/writes-A-ro-chain.log"; rcA1=$?
write_attempts "$ROOT/registry-ro" "A-ro-registry" reject 2>&1 | tee "$LOG/writes-A-ro-registry.log"; rcA2=$?
out=$(bash -c "mount -o remount,rw,bind $ROOT/chain-ro" 2>&1); echo "[A-ro-chain/remount-rw-attempt] rc=$? :: $(echo "$out" | head -1)" | tee -a "$LOG/writes-A-ro-chain.log"
echo "---- 挂载后判分链字节完整性（须与冻结件一致）----" | tee "$LOG/integrity-A.log"
sha256sum "$ROOT/chain-ro/swev-judge.py" "$ROOT/chain-ro/obs-checker.py" "$ROOT/registry-ro/fingerprints.json" | tee -a "$LOG/integrity-A.log"
sudo -n umount "$ROOT/chain-ro"; sudo -n umount "$ROOT/registry-ro"
rmdir "$ROOT/chain-ro" "$ROOT/registry-ro"

echo "===== 对照：无只读挂载（可写）时 6 类写应全部成功 ====="
mkdir -p "$ROOT/rw-control"
cp "$CHAIN/swev-judge.py" "$CHAIN/obs-checker.py" "$REG/fingerprints.json" "$ROOT/rw-control/"
write_attempts "$ROOT/rw-control" "A-rw-control" allow 2>&1 | tee "$LOG/writes-A-rw-control.log"; rcCtl=$?
rm -rf "$ROOT/rw-control"

echo "===== 形态B：rootless（unshare -rm 挂 ro + capsh 降权模拟无挂载权补丁流程） ====="
# 源文件置 666：排除权限位干扰，只验挂载拦截
chmod 666 "$CHAIN/swev-judge.py" "$CHAIN/obs-checker.py" "$REG/fingerprints.json"
unshare -rm bash -c "
  set -u
  mkdir -p $ROOT/chain-ro2 $ROOT/registry-ro2
  mount --bind $CHAIN $ROOT/chain-ro2 && mount -o remount,ro,bind $ROOT/chain-ro2
  mount --bind $REG $ROOT/registry-ro2 && mount -o remount,ro,bind $ROOT/registry-ro2
  echo \"[B] chain-ro2 OPTIONS=\$(findmnt -no OPTIONS $ROOT/chain-ro2)\"
  ok=0; bad=0
  for base in $ROOT/chain-ro2 $ROOT/registry-ro2; do
    for f in swev-judge.py obs-checker.py fingerprints.json; do
      for op in append pywrite chmod remount; do
        case \$op in
          append)  CMD=\"echo '# inj4' >> \$base/\$f\" ;;
          pywrite) CMD=\"python3 -c \\\"open('\$base/\$f','a').write('# inj4')\\\"\" ;;
          chmod)   CMD=\"chmod 644 \$base/\$f\" ;;
          remount) CMD=\"mount -o remount,rw,bind \$base\" ;;
        esac
        OUT=\$(capsh --drop=cap_sys_admin -- -c \"\$CMD\" 2>&1); RC=\$?
        echo \"[B-ro/\$(basename \$base)/\$f/\$op] rc=\$RC :: \$(echo \"\$OUT\" | head -1)\"
        if [ \$RC -eq 0 ]; then ok=\$((ok+1)); else bad=\$((bad+1)); fi
      done
    done
  done
  echo \"[B 汇总] 成功=\$ok 失败=\$bad（须全失败）\"
  sha256sum $ROOT/chain-ro2/swev-judge.py $ROOT/chain-ro2/obs-checker.py $ROOT/registry-ro2/fingerprints.json
" 2>&1 | tee "$LOG/writes-B-ro.log"
rcB=$(grep -c "rc=0 " "$LOG/writes-B-ro.log" || true)
chmod 644 "$CHAIN/swev-judge.py" "$CHAIN/obs-checker.py" "$REG/fingerprints.json"

echo "===== 形态B'：边界取证——同 unshare 内不降权（持 CAP_SYS_ADMIN）====="
unshare -rm bash -c "
  set -u
  mkdir -p $ROOT/chain-ro3
  mount --bind $CHAIN $ROOT/chain-ro3 && mount -o remount,ro,bind $ROOT/chain-ro3
  OUT=\$(mount -o remount,rw,bind $ROOT/chain-ro3 2>&1); RC=\$?
  echo \"[B'-boundary/chain-ro3/remount-rw] rc=\$RC :: \$OUT\"
  echo \"remount 后 OPTIONS=\$(findmnt -no OPTIONS $ROOT/chain-ro3)\"
" 2>&1 | tee "$LOG/writes-B-boundary.log"

echo "===== 汇总 ====="
[ $rcA1 -eq 0 ] && [ $rcA2 -eq 0 ] && echo "形态A（生产形态）: PASS — 36 类写尝试全被拒（EROFS）" || { echo "形态A: FAIL"; overall=1; }
[ "$rcB" -eq 0 ] && echo "形态B（rootless+降权）: PASS — 24 类写/remount 尝试全被拒" || { echo "形态B: FAIL — rc=0 行数=$rcB"; overall=1; }
[ $rcCtl -eq 0 ] && echo "对照（无挂载可写）: 符合预期 — 写全部成功，证明拦截来自只读挂载" || { echo "对照异常"; overall=1; }
grep -q "0338566c2f457496037c70f16504b0cfe9f5286c55ee2d67963428b00e7fc16a" "$LOG/integrity-A.log" && echo "完整性: PASS — 判分核挂载后字节与冻结件一致" || { echo "完整性: FAIL"; overall=1; }
grep -q "remount-rw] rc=0" "$LOG/writes-B-boundary.log" && echo "形态B'（边界取证）: 如预期——不降权时可 remount rw 绕过 → 生产必须形态A/确保补丁流程无 CAP_SYS_ADMIN" || echo "形态B': 本次未能复现绕过（环境差异）"
exit $overall
