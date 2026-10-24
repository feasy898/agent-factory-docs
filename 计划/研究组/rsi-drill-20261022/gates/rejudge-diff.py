#!/usr/bin/env python3
"""rejudge-diff.py — 双门数字对账门（闸3 消费侧 / Patch Judge「凭数字不凭故事」沙箱复刻）。

机制：以冻结判分器（registry/frozen/swev-judge.py，生产 venv）对同一 run 的
task.json + eval.log + agent.diff 重判，与事件流 harness.judge 记录值逐字段比对。
判分器被改宽松/记录被伪造成 resolved=true 时，冻结重判给出真实数字 → 对账 FAIL。
"""
import argparse
import json
import subprocess
import sys

VENV_PY = "/home/pan-ding/swev-venv/bin/python"


def run_frozen_judge(judge_py, task, log, diff):
    out = subprocess.run([VENV_PY, judge_py, task, log, diff],
                         capture_output=True, text=True)
    return out


def load_judge_event(events_path):
    with open(events_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            if ev.get("kind") == "harness.judge":
                return ev["payload"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen-judge", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--diff", required=True)
    ap.add_argument("--events", required=True)
    args = ap.parse_args()

    out = run_frozen_judge(args.frozen_judge, args.task, args.log, args.diff)
    print(f"冻结判分器退出码: {out.returncode}")
    print(f"冻结判分器 stdout: {out.stdout.strip()[:400]}")
    if out.stderr.strip():
        print(f"冻结判分器 stderr(尾): {out.stderr.strip()[-200:]}")

    recorded = load_judge_event(args.events)
    if recorded is None:
        print("FAIL: 事件流无 harness.judge 行")
        return 1

    if out.returncode != 0:
        # 判分器本身崩：若记录却声称 resolved 有值 → 记录不可信
        if recorded.get("resolved") is not None:
            print(f"FAIL: 冻结判分器退出 {out.returncode}，但记录声称 resolved={recorded.get('resolved')}")
            return 1
        print("PASS: 判分器崩与记录 resolved=None 一致（judge error 形态）")
        return 0

    try:
        fresh = json.loads(out.stdout.strip())
    except json.JSONDecodeError as err:
        print(f"FAIL: 冻结判分器输出非 JSON: {err}")
        return 1

    bad = []
    pairs = [
        ("resolved", fresh.get("resolved"), recorded.get("resolved")),
        ("f2p_pass", fresh.get("f2p_success"), recorded.get("f2p_pass")),
        ("f2p_total", (fresh.get("f2p_success") or 0) + (fresh.get("f2p_failure") or 0) or None,
         recorded.get("f2p_total")),
        ("p2p_pass", fresh.get("p2p_success"), recorded.get("p2p_pass")),
        ("p2p_total", (fresh.get("p2p_success") or 0) + (fresh.get("p2p_failure") or 0) or None,
         recorded.get("p2p_total")),
        ("tests_collected", fresh.get("tests_collected"), recorded.get("tests_collected")),
        ("log_parsed", fresh.get("log_parsed"), recorded.get("log_parsed")),
    ]
    for name, a, b in pairs:
        ok = a == b
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: 冻结重判={a} vs 事件记录={b}")
        if not ok:
            bad.append(name)

    # judge_raw 原文比对（截断到记录长度内比较前缀）
    raw = recorded.get("judge_raw") or ""
    fresh_text = out.stdout.strip()
    if raw and not fresh_text.startswith(raw.rstrip("\n")[:200]):
        print(f"[FAIL] judge_raw 不一致:\n  记录: {raw[:200]}\n  重判: {fresh_text[:200]}")
        bad.append("judge_raw")

    if bad:
        print(f"RESULT: FAIL — 双门数字对账不一致字段: {bad}（拒收：判定被改/记录被伪造成）")
        return 1
    print("RESULT: PASS — 冻结重判与事件记录逐字段一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
