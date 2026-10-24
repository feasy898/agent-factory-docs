#!/usr/bin/env python3
"""补丁② 单测：keepalive ch-mes-local 探活/去重报警（mock 层）。

边界：mes_event 打桩不真连 CH；ALARMS_LOG 重定向到 /tmp/md-patch2-test/（不污染
状态观测/alarms.log）；对真实本机 CH 只发只读 GET /ping。
运行: python3 补丁/patch2-test-chmes.py   （退出码 0=全过，1=有 FAIL）
"""
import contextlib
import importlib.util
import io
import os
import sys

WS = "/home/pan-ding/workspace/agent黑灯工厂"
TEST_ROOT = "/tmp/md-patch2-test"
os.makedirs(TEST_ROOT, exist_ok=True)

spec = importlib.util.spec_from_file_location(
    "factory_keepalive", f"{WS}/tools/factory-keepalive.py")
fk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fk)

MES_CALLS = []
fk.mes_event = lambda name, kind, _c=MES_CALLS: _c.append((name, kind))
TEST_ALARM = f"{TEST_ROOT}/alarms.log"
fk.ALARMS_LOG = TEST_ALARM
fk.KLOG = f"{TEST_ROOT}/keepalive.log"   # klog 双写（stdout+文件）——文件侧也进沙箱，
#                                          防测试伪造行泄入生产 /tmp/factory-keepalive.log

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append(cond)
    print(f"{'PASS' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail else ""))


# T1 探活：真实本机 CH
ok, detail = fk.check_ch_mes_local(0.0)
check("T1a 真实 CH ping Ok.（存活）", ok is True and detail == "ping Ok.", f"detail={detail}")
check("T1b ch_mes_ping 直返 True", fk.ch_mes_ping() is True)

# T2 探活：死端口（判不准/失联=False，不抛异常）
fk.CH = "http://127.0.0.1:9"
ok, detail = fk.check_ch_mes_local(0.0)
check("T2 死端口=失联（False，不抛）", ok is False and "失败" in detail, f"detail={detail}")
fk.CH = "http://127.0.0.1:5221"

# T3 报警：首失联 → klog+alarms.log+MES 三通道各 ≥1；30min 去重；窗过后再报
class FakeDeb:
    def record(self, *a):
        pass


if os.path.exists(TEST_ALARM):
    os.remove(TEST_ALARM)
fk.last_chmes_alarm = 0.0
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    fk.fix_ch_mes_local(False, 1000000.0, FakeDeb())
out = buf.getvalue()
check("T3a klog ALARM ≥1 行", "ALARM" in out)
check("T3b 报警写明不拉起+人工 Runbook", "不自动重启" in out and "Runbook" in out)
lines = open(TEST_ALARM).read().strip().splitlines()
check("T3c alarms.log ≥1 行（JSON，level=red，code=ch-mes-local）",
      len(lines) == 1 and '"level": "red"' in lines[0] and "ch-mes-local" in lines[0],
      f"lines={len(lines)}")
check("T3d MES kind=ch_mes_down 恰一次", MES_CALLS == [("ch-mes-local", "ch_mes_down")],
      f"mes={MES_CALLS}")
MES_CALLS.clear()
with contextlib.redirect_stdout(io.StringIO()):
    fk.fix_ch_mes_local(False, 1000010.0, FakeDeb())   # 10s 后：去重窗内
check("T3e 30min 去重：不再报警", MES_CALLS == [] and len(open(TEST_ALARM).readlines()) == 1)
MES_CALLS.clear()
with contextlib.redirect_stdout(io.StringIO()) as buf2:
    fk.fix_ch_mes_local(False, 1000000.0 + fk.CHMES_DEDUP_S + 1, FakeDeb())  # 窗过
check("T3f 窗过后再报", MES_CALLS == [("ch-mes-local", "ch_mes_down")]
      and len(open(TEST_ALARM).readlines()) == 2)

# T4 dry-run：只打印不动笔
os.remove(TEST_ALARM)
fk.last_chmes_alarm = 0.0
MES_CALLS.clear()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    fk.fix_ch_mes_local(True, 1000000.0, FakeDeb())
check("T4 dry-run 只打印（无 alarms.log 无 MES）",
      "dry-run" in buf.getvalue() and not os.path.exists(TEST_ALARM) and MES_CALLS == [])

# T5 注册面：TARGETS/CHECKS/FIXES/LAUNCH_PLAN 四处齐
check("T5 ch-mes-local 注册面齐全",
      "ch-mes-local" in fk.TARGETS and "ch-mes-local" in fk.CHECKS
      and "ch-mes-local" in fk.FIXES and any(n == "ch-mes-local" for n, *_ in fk.LAUNCH_PLAN))

print(f"\n{'ALL PASS' if all(RESULTS) else 'HAS FAILURES'} ({sum(RESULTS)}/{len(RESULTS)})")
sys.exit(0 if all(RESULTS) else 1)
