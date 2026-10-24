#!/usr/bin/env python3
"""fp-reconcile.py — 闸1「verifier 只读挂载+指纹机判」的对账门（沙箱复刻）。

判据（设计/RSI自我改进方案.md §3 闸1 原文）：
  「验收=指纹三件在合入前后逐字节相等，由可观测索引行的 fp_* 字段机器判定」。

本门三方比对（缺一不可）：
  A. 登记表 registry/fingerprints.json（合入前冻结基准）
  B. 事件流 run_started payload 的 fp_* 字段（run 时实采）
  C. 当前判分链实物重算值（sha256 文件字节 / pip freeze 指纹 / docker 镜像 digest）

任一方不一致 → exit 1（拒收+留痕）；三方一致 → exit 0。
重算口径与 af 写侧同源（fix4-observability obs.rs）：
  - judge 脚本：sha256(文件字节)
  - venv：pip freeze --all 输出按行 sort 后 join("\\n")（无尾换行）的 sha256
  - 镜像：docker image inspect RepoDigests[0]
  - bench 二进制：sha256(文件字节)
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def pip_freeze_fp(pybin):
    out = subprocess.run([pybin, "-m", "pip", "freeze", "--all"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None, f"pip freeze 退出 {out.returncode}: {out.stderr[:120]}"
    lines = sorted(out.stdout.splitlines())
    return hashlib.sha256("\n".join(lines).encode()).hexdigest(), f"{len(lines)} lines"


def image_digest(ref):
    out = subprocess.run(
        ["docker", "image", "inspect", ref, "--format", "{{index .RepoDigests 0}}"],
        capture_output=True, text=True)
    if out.returncode != 0:
        return None, f"docker inspect 退出 {out.returncode}: {out.stderr[:120]}"
    return out.stdout.strip(), "repodigest"


def load_event_fp(events_path):
    with open(events_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            if ev.get("kind") == "harness.run_started":
                return ev["payload"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--chain", required=True, help="待对账的判分链目录（含 swev-judge.py/obs-checker.py）")
    ap.add_argument("--events", required=True, help="run 事件流（取 fp_* 记录值）")
    ap.add_argument("--venv-py", default="/home/pan-ding/swev-venv/bin/python")
    args = ap.parse_args()

    reg = json.load(open(args.registry, encoding="utf-8"))
    payload = load_event_fp(args.events)
    if payload is None:
        print("FAIL: 事件流无 harness.run_started 行")
        return 1

    # 待对账项: (名称, 登记表值, 事件记录值, 重算值或None, 重算说明)
    rows = []

    judge_now = sha256_file(f"{args.chain}/swev-judge.py")
    rows.append(("judge_script_sha256",
                 reg["judge_script"]["sha256"],
                 payload.get("fp_judge_script_sha256"),
                 judge_now, "sha256(chain/swev-judge.py)"))

    checker_now = sha256_file(f"{args.chain}/obs-checker.py")
    rows.append(("obs_checker_sha256",
                 reg["obs_checker"]["sha256"],
                 "(登记表专属，事件流无此字段)",
                 checker_now, "sha256(chain/obs-checker.py)"))

    env_now, env_note = pip_freeze_fp(args.venv_py)
    rows.append(("judge_env_sha256",
                 reg["judge_env"]["sha256"],
                 payload.get("fp_judge_env_sha256"),
                 env_now, f"pip-freeze-{env_note}"))

    dig_now, dig_note = image_digest(reg["judge_image"]["ref"])
    rows.append(("image_digest",
                 reg["judge_image"]["digest"],
                 payload.get("fp_image_digest"),
                 dig_now, dig_note))

    bench_now = sha256_file(reg["bench_binary"]["path"])
    rows.append(("bench_binary_sha256",
                 reg["bench_binary"]["sha256"],
                 payload.get("bench_binary_sha256"),
                 bench_now, "sha256(bench 二进制)"))

    task_now = sha256_file(reg["run_sample"]["task_json"])
    rows.append(("task_sha256",
                 reg["run_sample"]["task_sha256"],
                 payload.get("fp_task_sha256"),
                 task_now, "sha256(task.json)"))

    bad = 0
    print("== 闸1 指纹对账（三方：登记表 / 事件流记录 / 实物重算）==")
    for name, reg_v, ev_v, now_v, how in rows:
        checks = [("登记表", reg_v)]
        if ev_v != "(登记表专属，事件流无此字段)":
            checks.append(("事件流", ev_v))
        checks.append(("重算", now_v))
        ok = all(v is not None and v == now_v for _, v in checks)
        status = "PASS" if ok else "FAIL"
        if not ok:
            bad += 1
        print(f"[{status}] {name} ({how})")
        for label, v in checks:
            mark = "==" if (v is not None and v == now_v) else "!="
            print(f"    {label}: {v}  {mark}  重算: {now_v}")
    if bad:
        print(f"RESULT: FAIL — {bad} 项指纹不一致（拒收：判分链被改动或记录被篡改）")
        return 1
    print("RESULT: PASS — 指纹三件+checker+bench+task 六项三方一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
