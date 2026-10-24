#!/usr/bin/env python3
"""obs-checker.py — fix4-observability 事件流的确定性校验脚本。

用法（入参兼容四种形态）:
    obs-checker.py <path> [--index <index.jsonl>] [--manifest <manifest.json>] [--quiet]

  a) <path> 含 events.jsonl 的观测 run 目录（$AF_OBS_ROOT/runs/<line>/<arm>/<run_id>/）；
  b) 直接给 events.jsonl 文件路径；
  c) af-bench 的 --out 目录（含 results.jsonl + runs/ legacy 布局）——经 results 行的
     task_id + run_dir 尾段映射到 $AF_OBS_ROOT/runs/*/*/<task_id>-a<N>/events.jsonl；
     setup_failed/无观测流的行按"跳过"计数，不判 fail；
  d) line/arm 级目录（直接子目录各自含 events.jsonl）——多 run 模式，全部 PASS 才 exit 0。
AF_OBS_ROOT 缺省 /home/pan-ding/workspace/agent黑灯工厂/工具状态备份/observability。

校验内容（stdlib only；本地可重算的部分：events_sha256/final_seq/event_count/torn_lines/
索引行全字段/manifest 的 merkle_root 与 event_count_total/status_counts；
fp_* 指纹只做格式校验与索引↔事件互证——它们引用的是外部对象（二进制/镜像/venv），
不在本脚本重算范围）:
  1. events.jsonl 存在且非空；逐行信封 keys 恰为 {ts_ms,seq,level,kind,payload}；
  2. seq 从 0 起严格 +1 单调；level/kind 属词表；kind 与 level 的配对符合约定；
  3. 首行必为 harness.run_started；末行必为 harness.run_finished，或（证据更正流）
     run_finished 之后只允许追加 harness.correction 行且末行是 correction；
  4. 各 kind 的 payload 必备字段与类型逐字段核对（checker 各 SPEC 合计 108 项字段检查：
     RUN_STARTED 32/MODEL 11/TOOL 8/KEY_REFRESH 5/RETRY_EXHAUSTED 7/RESOURCE 4/
     JUDGE 17/RUN_FINISHED 13/TERMINAL 4/CORRECTION 7——勘误史：文档旧口径 100 有误，
     终审 O6 实测 101（2026-10-22）；correction 词表落地后为 108；
     实测两轮真实 run 的事件 payload 字段并集 79——旧文档"93 字段"口径不清，作废；
     model.call.model 为强制保留项，缺失即 fail——红队⑤）；
  5. judge_mode_actual 与 run_started.judge_mode_declared 不等即 fail（红队④）；
  6. 非 run_failed 终态必须有 harness.stop/budget/unauthorized critical 行，
     且 run.finished.status 引用其同值 status（schema 硬性要求）；
  7. resolved 非 null 时 f2p_total 必须为正整数（分母缺失即判分行无效）;
  8. 汇总行与事件流互校（红队③修复）：
     model_calls == turns == Σ事件流 harness.model 行数；
     全部 model 行带 usage 时 tokens_* 必须等于 Σusage（否则 warning）；
     effect_fresh+effect_replays == 非纯函数且非 error 的 tool 行数；
     Σ(model.wall_ms) ≤ wall_ms+5s，单条 model/tool wall_ms ∈ [下界, wall_ms+5s]；
     wall_ms 与 (ts_finished-ts_started) 互校；http_retries ≥ Σ(model.retries)；
  9. harness.resource 至少 1 条（周期+终采，红队⑩①：删光 resource 不可再静默 PASS）；
 10. 索引行（自动定位 root/index/runs-YYYYMM.jsonl）：run_id/path/status/时间戳/指纹互证，
     events_sha256/final_seq/event_count/torn_lines 全部本地重算比对（静默截断/篡改必现形）；
 11. 批次 manifest（自动定位或 --manifest）：merkle_root 重算比对（RFC6962 风格，
     叶=sha256(0x00||ascii(events_sha256))，节点=sha256(0x01||l||r)，奇数末节点提升，
     输入为字典序排序的 events_sha256 列表），且 event_count_total==Σ索引 event_count、
     status_counts 与索引行派生值一致；
 12. 证据更正协议（硬规则 4，终审 O1；流内存在 harness.correction 时启用）：
     每条 correction 的归档文件必须存在且 sha256==payload.archived_sha256，且等于当前
     事件流截到该 correction 行之前的字节 sha（两向比对）；第一条 correction 的归档
     sha 还必须等于索引行 events_sha256（索引钉住归档原字节）；corrections 的 old 值
     必须与归档件（或前一次更正后）的 run_finished 实值一致、new 值必须与当前
     run_finished 实值一致；索引行 event_count/final_seq/torn_lines/status/ts_finished
     全部对归档件重算比对；归档目录名须合 corrections/<run_id>-<ts> 约定。

退出码: 0=全部通过（允许 warning），1=存在任何 fail。
撕裂容忍口径（与写侧一致）：末行无换行或 JSON 解析失败计 torn_lines；中间行坏即 fail。
"""

import argparse
import glob
import hashlib
import json
import os
import re
import sys

DEFAULT_OBS_ROOT = "/home/pan-ding/workspace/agent黑灯工厂/工具状态备份/observability"

ENVELOPE_KEYS = {"ts_ms", "seq", "level", "kind", "payload"}
LEVELS = {"normal", "critical"}
KIND_LEVEL = {
    "harness.run_started": "normal",
    "harness.model": "normal",
    "harness.tool": "normal",
    "harness.key_refresh": "critical",
    "harness.retry_exhausted": "critical",
    "harness.resource": "normal",
    "harness.judge": "critical",
    "harness.run_finished": "normal",
    "harness.stop": "critical",
    "harness.budget": "critical",
    "harness.unauthorized": "critical",
    "harness.correction": "critical",
}
SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
SHA_ALGO_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

STATUS_KIND_TO_LABEL = {
    "completed": "completed",
    "max_turns": "max_turns",
    "tool_free_limit": "tool_free_limit",
    "budget_exhausted": "budget_exhausted",
    "stopped": "stopped",
    "unauthorized": "unauthorized",
}
KIND_FOR_STATUS = {
    "completed": "harness.stop",
    "max_turns": "harness.stop",
    "tool_free_limit": "harness.stop",
    "stopped": "harness.stop",
    "budget_exhausted": "harness.budget",
    "unauthorized": "harness.unauthorized",
}

fails = []
warns = []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def is_u64(v):
    return isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 2**64 - 1


def is_u32(v):
    return isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 2**32 - 1


def is_u16(v):
    return isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 65535


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def is_str(v):
    return isinstance(v, str)


def check_fields(where, payload, spec):
    """spec: {field: (checker, required)}；缺失/类型错记 fail；额外键记 warning。
    required 只约束"字段必须出现"；null 是否合法由 checker 自己决定
    （schema 里 X|null 的字段用允许 None 的 checker）。"""
    if not isinstance(payload, dict):
        fail(f"{where}: payload 不是对象")
        return
    for field, (checker, required) in spec.items():
        if field not in payload:
            if required:
                fail(f"{where}: 缺必备字段 {field}")
            continue
        value = payload[field]
        try:
            ok = checker(value)
        except Exception as err:  # noqa: BLE001
            ok = False
            warn(f"{where}: 字段 {field} 类型检查异常 {err}")
        if not ok:
            fail(f"{where}: 字段 {field} = {value!r} 类型/取值不符")
    extras = set(payload) - set(spec)
    extras -= {"phase"}  # resource 事件的已知扩展位
    if extras:
        warn(f"{where}: 出现 schema 外字段（已放行，仅提示）: {sorted(extras)}")


def or_none(checker):
    """显式 nullable 包装：null 合法，非 null 走 checker（checker 各 SPEC 统一用它，
    不再留死代码包装）。"""

    def wrapped(v):
        return v is None or checker(v)

    return wrapped


RUN_STARTED_SPEC = {
    "run_id": (lambda v: is_str(v) and bool(SEGMENT_RE.match(v)) or (is_str(v) and re.match(r"^[A-Za-z0-9._-]{1,64}(-x\d+)$", v) is not None), True),
    "instance_id": (is_str, True),
    "line": (lambda v: is_str(v) and bool(SEGMENT_RE.match(v)) and v not in (".", ".."), True),
    "arm": (lambda v: is_str(v) and bool(SEGMENT_RE.match(v)) and v not in (".", ".."), True),
    "profile": (is_str, True),
    "host": (is_str, True),
    "ts_started": (is_u64, True),
    "model": (lambda v: is_str(v) and v != "", True),
    "base_url": (lambda v: is_str(v) and v.startswith(("http://", "https://")), True),
    "reasoning_tier": (is_str, True),
    "stream": (lambda v: isinstance(v, bool), True),
    "max_tokens": (lambda v: v is None or is_u32(v), True),
    "temperature_milli": (lambda v: v is None or is_int(v), True),
    "top_p_milli": (lambda v: v is None or is_int(v), True),
    "max_turns": (is_u32, True),
    "tool_free_turn_limit": (is_u32, True),
    "completion_signals": (lambda v: isinstance(v, list) and all(is_str(s) and s for s in v), True),
    "per_turn_budget_cents": (is_u64, True),
    "spend_cap_cents": (is_u64, True),
    "tool_spend_cents": (is_u64, True),
    "scaffold": (is_str, True),
    "judge_mode_declared": (lambda v: v in ("clean", "in-place"), True),
    "bench_binary_sha256": (lambda v: is_str(v) and bool(HEX64_RE.match(v)), True),
    "harness_git_rev": (lambda v: is_str(v) and (bool(re.fullmatch(r"[0-9a-f]{40}(-dirty\.\d+)?", v)) or v == "unknown"), True),
    "fp_image_ref": (lambda v: is_str(v) and v != "", True),
    "fp_image_digest": (lambda v: is_str(v) and v != "", True),
    "fp_image_digest_source": (lambda v: v in ("repodigest", "id"), False),
    "fp_task_sha256": (lambda v: is_str(v) and bool(HEX64_RE.match(v)), True),
    "fp_prompt_sha256": (lambda v: is_str(v) and bool(HEX64_RE.match(v)), True),
    "fp_judge_script_sha256": (lambda v: is_str(v) and bool(HEX64_RE.match(v)), True),
    "fp_judge_env_sha256": (lambda v: is_str(v) and bool(HEX64_RE.match(v)), True),
    "swebench_version": (lambda v: is_str(v) and v != "", True),
}

MODEL_SPEC = {
    "run_id": (lambda v: is_str(v) and v != "", True),
    "turn": (is_u32, True),
    "model": (lambda v: is_str(v) and v != "", True),  # 强制保留项（红队⑤）
    "finish": (is_str, True),
    "usage": (
        lambda v: v is None or (
            isinstance(v, dict)
            and is_u64(v.get("input_tokens"))
            and is_u64(v.get("output_tokens"))
            and is_u64(v.get("cache_read_tokens"))
        ),
        False,
    ),
    "wall_ms": (is_u64, True),
    "http_status": (lambda v: v is None or is_u16(v), True),
    "retries": (is_u32, True),
    "retry_after_ms": (lambda v: v is None or is_u64(v), True),
    "backoff_ms": (lambda v: v is None or is_u64(v), True),
    "key_refreshed": (lambda v: isinstance(v, bool), True),
}

TOOL_SPEC = {
    "run_id": (lambda v: is_str(v) and v != "", True),
    "turn": (is_u32, True),
    "tool": (lambda v: is_str(v) and v != "", True),
    "effect": (lambda v: is_str(v) and v != "", True),
    "is_error": (lambda v: isinstance(v, bool), True),
    "error_code": (is_str, True),
    "wall_ms": (is_u64, True),
    "error_head": (lambda v: v is None or is_str(v), True),
}

KEY_REFRESH_SPEC = {
    "run_id": (lambda v: is_str(v) and v != "", True),
    "turn": (is_u32, True),
    "reason": (lambda v: v in ("401", "preemptive"), True),
    "attempt": (lambda v: is_u32(v) and v >= 1, True),
    "ok": (lambda v: isinstance(v, bool), True),
}

RETRY_EXHAUSTED_SPEC = {
    "run_id": (lambda v: is_str(v) and v != "", True),
    "model": (lambda v: is_str(v) and v != "", True),
    "err_class": (lambda v: v in ("transport", "http"), True),
    "http_status": (lambda v: v is None or is_u16(v), True),
    "retries_done": (is_u64, True),
    "retry_after_ms": (lambda v: v is None or is_u64(v), True),
    "backoff_ms": (lambda v: v is None or is_u64(v), True),
}

RESOURCE_SPEC = {
    "run_id": (lambda v: is_str(v) and v != "", True),
    # 红队⑩⑦：写侧 df 瞬故障（已重试 2 次）会落 null——读写契约一致化为
    # "null 合法但必须告警"（在主流程里对 None 记 WARN），其余类型仍 fail。
    "disk_free_bytes": (or_none(is_u64), True),
    "disk_path": (lambda v: is_str(v) and v != "", True),
    "container_mem_peak_kb": (or_none(is_u64), True),
}

JUDGE_SPEC = {
    "run_id": (lambda v: is_str(v) and v != "", True),
    "judge_mode_actual": (lambda v: v in ("clean", "in-place"), True),
    "resolved": (lambda v: v is None or isinstance(v, bool), True),
    "f2p_pass": (lambda v: v is None or is_u32(v), True),
    "f2p_total": (lambda v: v is None or is_u32(v), True),
    "p2p_pass": (lambda v: v is None or is_u32(v), True),
    "p2p_total": (lambda v: v is None or is_u32(v), True),
    "log_parsed": (lambda v: v is None or isinstance(v, bool), True),
    "tests_collected": (lambda v: v is None or is_u32(v), True),
    "env_yml_synthesized": (lambda v: v is None or isinstance(v, bool), True),
    "judge_exit_code": (lambda v: v is None or is_int(v), True),
    "judge_stderr": (lambda v: v is None or is_str(v), True),
    "eval_timeout": (lambda v: isinstance(v, bool), True),
    "eval_sha256": (lambda v: v is None or (is_str(v) and bool(HEX64_RE.match(v))), True),
    "judge_raw": (lambda v: v is None or is_str(v), True),
    "judge_container": (lambda v: v is None or (is_str(v) and v != ""), True),
    "swebench_version": (lambda v: v is None or (is_str(v) and v != ""), True),
}

RUN_FINISHED_SPEC = {
    "run_id": (lambda v: is_str(v) and v != "", True),
    "ts_finished": (is_u64, True),
    "wall_ms": (is_u64, True),
    "turns": (is_u32, True),
    "model_calls": (is_u64, True),
    "tokens_input": (is_u64, True),
    "tokens_output": (is_u64, True),
    "tokens_cache_read": (is_u64, True),
    "http_retries": (is_u32, True),
    "effect_fresh": (is_u64, True),
    "effect_replays": (is_u64, True),
    "status": (lambda v: is_str(v) and v != "", True),
    "stop_reason": (lambda v: is_str(v) and v != "", True),
}

TERMINAL_SPEC = {
    "run_id": (lambda v: is_str(v) and v != "", True),
    "turn": (is_u32, True),
    # status（trace_terminal）/ decision（trace_stop）二选一，shape 在主流程里核对。
    "status": (lambda v: isinstance(v, dict) and is_str(v.get("kind")), False),
    "decision": (lambda v: isinstance(v, dict), False),
}

# 证据更正协议（硬规则 4②，终审 O1 事件化；与写侧 obs.rs::append_correction 同一变更集）。
# 约定：correction 事件只追加在 run_finished 之后；旧值由写侧从当时字节实取；
# archived_* 指向本次更正前的完整原字节归档（checker 两向比对：归档文件 sha 与
# 事件内 sha 一致，且与索引行钉住的 events_sha256 一致——索引行与 manifest 永不改写）。
CORRECTION_SPEC = {
    "run_id": (lambda v: is_str(v) and v != "", True),
    "archived_path": (lambda v: is_str(v) and v != "", True),
    "archived_sha256": (lambda v: is_str(v) and bool(HEX64_RE.match(v)), True),
    "corrections": (
        lambda v: isinstance(v, list)
        and len(v) > 0
        and all(
            isinstance(c, dict)
            and is_str(c.get("field"))
            and c.get("field") != ""
            and "old" in c
            and "new" in c
            for c in v
        ),
        True,
    ),
    "reason": (lambda v: is_str(v) and v != "", True),
    "basis_rev": (lambda v: is_str(v) and v != "", True),
    "operator": (lambda v: is_str(v) and v != "", True),
}


def spec_kind(payload_status):
    if isinstance(payload_status, dict):
        return payload_status.get("kind")
    return None


def merkle_root_sorted_hex(hashes):
    """与写侧 obs.rs::merkle_root_sorted_hex 完全一致的第三方重算口径。"""

    def leaf(h):
        return hashlib.sha256(b"\x00" + h.encode("ascii")).digest()

    def node(l, r):
        return hashlib.sha256(b"\x01" + l + r).digest()

    if not hashes:
        return hashlib.sha256(b"").hexdigest()
    level = [leaf(h) for h in hashes]
    while len(level) > 1:
        nxt = []
        i = 0
        while i < len(level):
            if i + 1 == len(level):
                nxt.append(level[i])  # 奇数末节点提升
            else:
                nxt.append(node(level[i], level[i + 1]))
            i += 2
        level = nxt
    return level[0].hex()


def load_index_rows(root):
    index_dir = os.path.join(root, "index")
    rows = []
    if not os.path.isdir(index_dir):
        return rows
    for name in sorted(os.listdir(index_dir)):
        if name.startswith("runs-") and name.endswith(".jsonl"):
            path = os.path.join(index_dir, name)
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append((name, json.loads(line)))
                    except json.JSONDecodeError:
                        warn(f"索引文件 {name} 有无法解析的行（撕裂），已跳过")
    return rows


def find_manifests(root):
    index_dir = os.path.join(root, "index")
    out = []
    if not os.path.isdir(index_dir):
        return out
    for name in sorted(os.listdir(index_dir)):
        if name.startswith("batch-") and name.endswith(".manifest.json"):
            path = os.path.join(index_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    out.append((name, json.load(fh)))
            except (OSError, json.JSONDecodeError) as err:
                warn(f"批次清单 {name} 读取失败: {err}")
    return out


def resolve_targets(arg):
    """入参兼容四种形态 → [(events.jsonl 绝对路径, run 目录)]（见模块 docstring a-d）。"""
    p = os.path.abspath(arg)
    if os.path.isfile(p):
        return [(p, os.path.dirname(p))]
    if not os.path.isdir(p):
        return []
    if os.path.isfile(os.path.join(p, "events.jsonl")):
        return [(os.path.join(p, "events.jsonl"), p)]
    results = os.path.join(p, "results.jsonl")
    if os.path.isfile(results):
        return targets_from_results(results)
    evs = [
        os.path.join(p, name, "events.jsonl")
        for name in sorted(os.listdir(p))
        if os.path.isfile(os.path.join(p, name, "events.jsonl"))
    ]
    return [(e, os.path.dirname(e)) for e in evs]


def targets_from_results(results_path):
    """af-bench --out 目录：results.jsonl 行的 task_id + run_dir 尾段（…-a<N>）
    映射到 $AF_OBS_ROOT/runs/<line>/<arm>/<task_id>-a<N>/events.jsonl。
    setup_failed（run_dir=null）与找不到观测流的行按"跳过"计数——冒烟批的
    results.jsonl 跨多次调用追加，旧行/无观测行不代表本次失败。"""
    root = os.environ.get("AF_OBS_ROOT") or DEFAULT_OBS_ROOT
    targets = []
    skipped = []
    with open(results_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                skipped.append("<非 JSON 行>")
                continue
            run_dir_field = row.get("run_dir")
            task_id = row.get("task_id")
            if not (isinstance(run_dir_field, str) and run_dir_field) or not task_id:
                skipped.append(str(task_id))
                continue
            base = os.path.basename(run_dir_field.rstrip("/"))
            # legacy 目录名形态：swev-<task_id>-<profile>-a<N>（profile 段可含 '-'）。
            m = re.fullmatch(rf"swev-{re.escape(str(task_id))}-.+-a(\d+)", base)
            if not m:
                skipped.append(base)
                continue
            run_id = f"{task_id}-a{m.group(1)}"
            found = sorted(
                glob.glob(os.path.join(root, "runs", "*", "*", run_id, "events.jsonl"))
            )
            found += sorted(
                glob.glob(os.path.join(root, "runs", "*", "*", run_id + "-x*", "events.jsonl"))
            )
            if not found:
                skipped.append(run_id)
                continue
            for e in found:
                targets.append((e, os.path.dirname(e)))
    if skipped:
        print(
            f"[obs-checker] results.jsonl 里 {len(skipped)} 行无对应观测流（setup_failed/坏行/流缺失，跳过不判 fail）: {skipped[:6]}"
        )
    return targets


def main():
    parser = argparse.ArgumentParser(description="fix4-observability 事件流校验")
    parser.add_argument("run_dir", help="run 目录 / events.jsonl 文件 / --out 目录 / line|arm 级目录")
    parser.add_argument("--index", default=None, help="索引文件路径（缺省自动定位）")
    parser.add_argument("--manifest", default=None, help="批次清单路径（缺省自动定位）")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    targets = resolve_targets(args.run_dir)
    if not targets:
        print(
            f"FAIL: {args.run_dir} 不是可识别的入参（events.jsonl 文件 / 含 events.jsonl 的 run 目录 / af-bench --out 目录 / line|arm 级目录），或事件流不存在"
        )
        return 1
    if len(targets) == 1:
        return check_one(targets[0][0], targets[0][1], args)
    print(f"[obs-checker] 多 run 模式：{len(targets)} 个事件流待检（来源 {args.run_dir}）")
    worst = 0
    passed = 0
    for events_path, run_dir in targets:
        rc = check_one(events_path, run_dir, args)
        worst = max(worst, rc)
        passed += rc == 0
    print(f"[obs-checker] 汇总：{passed}/{len(targets)} PASS")
    return worst


def _torn_count(data):
    """撕裂行计数（与写侧 obs.rs::count_torn_lines 及本脚本主流程同口径）。"""
    torn = 0
    text = data.decode("utf-8", errors="replace")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for line in lines:
        if line.strip() == "":
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            torn += 1
    if data and not data.endswith(b"\n"):
        torn += 1
    return torn


def verify_correction_chain(correction_rows, parsed, data, idx_row, finished, run_id):
    """硬规则 4（终审 O1 事件化）correction 流的读侧校验。

    - 每条 correction：归档文件存在且 sha256 == payload.archived_sha256；
    - 第一条 correction 的归档必须等于索引行 events_sha256（索引行与 manifest 永不
      改写，钉住归档原字节），且归档件末行是 run_finished；其 event_count/
      final_seq/torn_lines/status/ts_finished 全部对归档件重算比对；
    - 链式更正（第 2 条起）的归档件末行必须与当前流里前一条 correction 行的原文
      逐字节一致（归档件=前序状态的真实前驱；写侧每次更正会重写 run_finished
      基线行的值，故归档件与当前流前缀不再逐字节可比，链的正确性由 old/new 链与
      本行原文锚共同保证）；
    - corrections 的 old 值必须与归档件（或前一次更正后）的 run_finished 实值一致、
      new 值链式推进后必须与当前 run_finished 实值一致。"""
    lines = data.decode("utf-8", errors="replace").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    expected = None
    changed_fields = set()
    for k, (ev_idx, payload) in enumerate(correction_rows):
        archived_path = payload.get("archived_path")
        arch_bytes = None
        if is_str(archived_path) and os.path.isfile(archived_path):
            try:
                with open(archived_path, "rb") as fh:
                    arch_bytes = fh.read()
            except OSError as err:
                fail(f"correction[{k}] 归档件 {archived_path} 读取失败: {err}")
        else:
            fail(
                f"correction[{k}] 归档件不存在（硬规则 4①：原字节必须先归档）: {archived_path!r}"
            )
        arch_finished = None
        arch_events = []
        if isinstance(arch_bytes, bytes):
            sha_arch = hashlib.sha256(arch_bytes).hexdigest()
            if sha_arch != payload.get("archived_sha256"):
                fail(
                    f"correction[{k}] 归档件 sha256={sha_arch} ≠ payload.archived_sha256="
                    f"{payload.get('archived_sha256')}"
                )
            parent = os.path.basename(os.path.dirname(archived_path or ""))
            if not re.fullmatch(re.escape(str(run_id)) + r"-\d+(-k\d+)?", parent):
                fail(
                    f"correction[{k}] 归档目录名 {parent!r} 不合 corrections/<run_id>-<ts>[-kN] 约定"
                )
            arch_lines = arch_bytes.decode("utf-8", errors="replace").split("\n")
            if arch_lines and arch_lines[-1] == "":
                arch_lines.pop()
            if k > 0:
                # 链式更正：归档件末行必须与当前流里前一条 correction 行原文逐字节一致
                # （归档件=前序状态的真实前驱；写侧每次更正会重写 run_finished 基线行的值，
                # 故归档件与当前流前缀不再逐字节可比——链的正确性由本行原文锚与
                # old/new 链共同保证）。
                prev_idx = correction_rows[k - 1][0]
                prev_raw = lines[prev_idx] if prev_idx < len(lines) else None
                if not arch_lines or prev_raw is None or arch_lines[-1] != prev_raw:
                    fail(
                        f"correction[{k}] 归档件末行与前一条 correction 行原文不一致"
                        "（归档件不是前序状态的真实前驱）"
                    )
            for line in arch_lines:
                try:
                    arch_events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            # 归档件里的 run_finished 取最后一条（k≥1 的归档件还含前序 correction 行）。
            fin_positions = [
                i for i, e in enumerate(arch_events)
                if isinstance(e, dict) and e.get("kind") == "harness.run_finished"
            ]
            if k == 0:
                # 原始流（更正前）末行必须是 run_finished。
                if not (
                    arch_events
                    and fin_positions
                    and fin_positions[-1] == len(arch_events) - 1
                ):
                    fail(f"correction[{k}] 归档件末行不是 harness.run_finished")
            if fin_positions:
                arch_finished = arch_events[fin_positions[-1]].get("payload") or {}
        if k == 0:
            if isinstance(arch_bytes, bytes):
                if idx_row.get("events_sha256") != hashlib.sha256(arch_bytes).hexdigest():
                    fail(
                        "索引行 events_sha256 ≠ 第一条 correction 归档件 sha256"
                        "（索引/manifest 永不改写，必须钉住归档原字节）"
                    )
                if idx_row.get("event_count") != len(arch_events):
                    fail(
                        f"索引 event_count={idx_row.get('event_count')} ≠ 归档件实算 "
                        f"{len(arch_events)}（索引对归档原字节重算不符）"
                    )
                arch_seqs = [e.get("seq") for e in arch_events if isinstance(e, dict)]
                if idx_row.get("final_seq") != (arch_seqs[-1] if arch_seqs else None):
                    fail(
                        f"索引 final_seq={idx_row.get('final_seq')} ≠ 归档件实算 "
                        f"{arch_seqs[-1] if arch_seqs else None}"
                    )
                if idx_row.get("torn_lines") != _torn_count(arch_bytes):
                    fail(
                        f"索引 torn_lines={idx_row.get('torn_lines')} ≠ 归档件实算 "
                        f"{_torn_count(arch_bytes)}"
                    )
                if isinstance(arch_finished, dict):
                    if idx_row.get("status") != arch_finished.get("status"):
                        fail(
                            f"索引 status={idx_row.get('status')!r} ≠ 归档件 run_finished.status="
                            f"{arch_finished.get('status')!r}"
                        )
                    if idx_row.get("ts_finished") != arch_finished.get("ts_finished"):
                        fail("索引 ts_finished 与归档件 run_finished.ts_finished 不一致")
            expected = dict(arch_finished) if isinstance(arch_finished, dict) else None
        elif expected is not None and isinstance(arch_finished, dict):
            for field, value in expected.items():
                if arch_finished.get(field) != value:
                    fail(
                        f"correction[{k}] 归档件 run_finished.{field}="
                        f"{arch_finished.get(field)!r} ≠ 前序更正后期望 {value!r}"
                        "（链式更正必须逐级一致）"
                    )
        if expected is None and isinstance(finished, dict):
            expected = dict(finished)
        if isinstance(expected, dict):
            for entry in payload.get("corrections") or []:
                if not isinstance(entry, dict) or not is_str(entry.get("field")):
                    continue
                field = entry["field"]
                if field not in expected:
                    fail(f"correction[{k}] 更正目标 {field!r} 不在归档件 run_finished 里")
                elif entry.get("old") != expected[field]:
                    fail(
                        f"correction[{k}] {field} old={entry.get('old')!r} ≠ 归档实值 "
                        f"{expected[field]!r}（旧值必须与被更正前字节一致）"
                    )
                expected[field] = entry.get("new")
                changed_fields.add(field)
    if isinstance(finished, dict):
        for field in sorted(changed_fields):
            if finished.get(field) != expected.get(field):
                fail(
                    f"当前 run_finished.{field}={finished.get(field)!r} ≠ 更正链终值 "
                    f"{expected.get(field)!r}（new 值必须与现值一致）"
                )


def check_one(events_path, run_dir, args):
    fails.clear()
    warns.clear()
    run_dir = os.path.abspath(run_dir)
    if not os.path.isfile(events_path):
        print(f"FAIL: {events_path} 不存在")
        return 1
    with open(events_path, "rb") as fh:
        data = fh.read()
    if not data:
        print("FAIL: events.jsonl 为空")
        return 1

    # ---- 撕裂判定（读侧口径）----
    text = data.decode("utf-8", errors="replace")
    raw_lines = text.split("\n")
    trailing_no_newline = not data.endswith(b"\n")
    if raw_lines and raw_lines[-1] == "":
        raw_lines = raw_lines[:-1]
    torn = 0
    parsed = []
    for idx, line in enumerate(raw_lines):
        if line.strip() == "":
            warn(f"第 {idx + 1} 行为空白行")
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError as err:
            torn += 1
            if idx != len(raw_lines) - 1:
                fail(f"第 {idx + 1} 行 JSON 解析失败且不在末尾（非尾撕裂形态）: {err}")
            else:
                warn(f"末行 JSON 解析失败，计 torn_lines: {err}")
    if trailing_no_newline:
        torn += 1
        warn("末行缺换行符，计 torn_lines")
    if torn:
        warn(f"torn_lines={torn}（>0 必须告警——schema 硬性要求）")

    if not parsed:
        print("FAIL: events.jsonl 没有可解析事件")
        return 1

    # ---- 信封与词表 ----
    for idx, ev in enumerate(parsed):
        where = f"事件[{idx}] seq={ev.get('seq') if isinstance(ev, dict) else '?'}"
        if not isinstance(ev, dict):
            fail(f"{where}: 不是 JSON 对象")
            continue
        keys = set(ev.keys())
        if keys != ENVELOPE_KEYS:
            fail(f"{where}: 信封 keys = {sorted(keys)}，要求恰为 {sorted(ENVELOPE_KEYS)}")
            continue
        if not is_u64(ev["ts_ms"]):
            fail(f"{where}: ts_ms 不是 u64")
        if not isinstance(ev["seq"], int) or isinstance(ev["seq"], bool) or ev["seq"] < 0:
            fail(f"{where}: seq 不是非负整数")
        if ev["level"] not in LEVELS:
            fail(f"{where}: level={ev['level']!r} 不在词表")
        kind = ev["kind"]
        if kind not in KIND_LEVEL:
            fail(f"{where}: kind={kind!r} 不在事件词表")
        elif ev["level"] != KIND_LEVEL[kind]:
            fail(f"{where}: kind={kind} 应为 level={KIND_LEVEL[kind]}，实为 {ev['level']}")
        if not isinstance(ev["payload"], dict):
            fail(f"{where}: payload 不是对象")

    seqs = [ev.get("seq") for ev in parsed if isinstance(ev, dict)]
    for i, s in enumerate(seqs):
        if not isinstance(s, int):
            continue
        if i == 0 and s != 0:
            fail(f"首事件 seq={s}，必须从 0 起")
        elif i > 0 and s != seqs[i - 1] + 1:
            fail(f"seq 不单调：第 {i} 个事件 seq={s}，前一事件 seq={seqs[i - 1]}")

    kinds = [ev.get("kind") for ev in parsed if isinstance(ev, dict)]
    if not kinds or kinds[0] != "harness.run_started":
        fail(f"首行 kind={kinds[0] if kinds else None!r}，必须为 harness.run_started")
    correction_rows = []  # [(事件序号, payload)]，payload 循环里填充
    if "harness.correction" in kinds:
        # 证据更正流（硬规则 4）：correction 只允许追加在 run_finished 之后、连续排到流尾。
        last_fin = max(i for i, k in enumerate(kinds) if k == "harness.run_finished")
        if kinds[-1] != "harness.correction":
            fail(
                f"末行 kind={kinds[-1]!r}：含 correction 的流必须以 correction 行收尾"
                "（run_finished 之后只允许追加 correction）"
            )
        for i in range(last_fin + 1, len(kinds)):
            if kinds[i] != "harness.correction":
                fail(
                    f"事件[{i}] kind={kinds[i]!r}：run_finished 之后只允许 harness.correction"
                    "（硬规则 4：更正只追加在流尾）"
                )
    elif kinds[-1] != "harness.run_finished":
        fail(f"末行 kind={kinds[-1]!r}，必须为 harness.run_finished")

    run_started = parsed[0]["payload"] if kinds and kinds[0] == "harness.run_started" else {}
    run_id = run_started.get("run_id")
    check_fields("run.started", run_started, RUN_STARTED_SPEC)

    # ---- 各 kind payload 逐字段核对 ----
    model_count = 0
    retries_sum = 0
    model_walls = []  # 各 model 行 wall_ms（汇总行互校用）
    model_usage = []  # 各 model 行 usage（None=未报，汇总行 tokens 互校用）
    side_effect_ok_count = 0  # 非纯函数且非 error 的 tool 行（effect_fresh+replays 互校用）
    tool_wall_max = 0
    resource_count = 0
    judge_seen = None
    terminal_rows = []
    finished = None
    for idx, ev in enumerate(parsed):
        kind = ev.get("kind")
        payload = ev.get("payload", {})
        where = f"事件[{idx}] {kind}"
        if not isinstance(payload, dict):
            continue
        if kind != "harness.run_started" and payload.get("run_id") != run_id:
            fail(f"{where}: payload.run_id={payload.get('run_id')!r} 与 run.started 的 {run_id!r} 不一致")
        if kind == "harness.model":
            model_count += 1
            check_fields(where, payload, MODEL_SPEC)
            r = payload.get("retries")
            if isinstance(r, int) and not isinstance(r, bool):
                retries_sum += r
            w = payload.get("wall_ms")
            if is_u64(w):
                if w == 0:
                    fail(f"{where}: model wall_ms=0——真实 HTTP 往返不可能为 0")
                model_walls.append(w)
            model_usage.append(payload.get("usage"))
            m = payload.get("model")
            rs = run_started.get("model")
            if is_str(m) and is_str(rs) and m != rs:
                warn(f"{where}: 实际请求模型 {m!r} 与声明 {rs!r} 不同（同名换模应在此暴露）")
        elif kind == "harness.tool":
            check_fields(where, payload, TOOL_SPEC)
            w = payload.get("wall_ms")
            if is_u64(w):
                tool_wall_max = max(tool_wall_max, w)
            if payload.get("effect") not in (None, "pure") and payload.get("is_error") is False:
                side_effect_ok_count += 1
        elif kind == "harness.key_refresh":
            check_fields(where, payload, KEY_REFRESH_SPEC)
        elif kind == "harness.retry_exhausted":
            check_fields(where, payload, RETRY_EXHAUSTED_SPEC)
            ec = payload.get("err_class")
            hs = payload.get("http_status")
            if ec == "http" and not is_u16(hs):
                fail(f"{where}: err_class=http 但 http_status 缺失")
            if ec == "transport" and hs is not None:
                fail(f"{where}: err_class=transport 但 http_status 非 null")
        elif kind == "harness.resource":
            resource_count += 1
            check_fields(where, payload, RESOURCE_SPEC)
            if payload.get("disk_free_bytes") is None:
                warn(f"{where}: disk_free_bytes=null（写侧 df 已重试 2 次仍失败）")
            if payload.get("container_mem_peak_kb") is None:
                warn(f"{where}: container_mem_peak_kb=null（docker stats 不可用/容器已不在）")
        elif kind == "harness.judge":
            check_fields(where, payload, JUDGE_SPEC)
            judge_seen = payload
            declared = run_started.get("judge_mode_declared")
            actual = payload.get("judge_mode_actual")
            if declared and actual and declared != actual:
                fail(f"判分无效：judge_mode_declared={declared!r} ≠ judge_mode_actual={actual!r}（红队④）")
            if isinstance(payload.get("resolved"), bool):
                total = payload.get("f2p_total")
                if not (is_u32(total) and total > 0):
                    fail(f"{where}: resolved 非 null 但 f2p_total 缺失或为 0（分母缺失判分行无效）")
            if payload.get("eval_timeout") is True and payload.get("eval_sha256") is None:
                fail(f"{where}: eval_timeout=true 但 eval_sha256 为 null（超时标记行应已入哈希）")
        elif kind in ("harness.stop", "harness.budget", "harness.unauthorized"):
            check_fields(where, payload, TERMINAL_SPEC)
            if "status" not in payload and "decision" not in payload:
                fail(f"{where}: 终态行既无 status 也无 decision")
            terminal_rows.append((kind, payload))
        elif kind == "harness.run_finished":
            finished = payload
            check_fields(where, payload, RUN_FINISHED_SPEC)
        elif kind == "harness.correction":
            check_fields(where, payload, CORRECTION_SPEC)
            correction_rows.append((idx, payload))
            # 读侧复验写侧同款约束：更正目标必须是 run_finished 的已存在字段。
            if finished is None:
                fail(f"{where}: 流里还没有 run_finished，无处更正（correction 只能在终态后）")
            else:
                for c in payload.get("corrections") or []:
                    if isinstance(c, dict) and is_str(c.get("field")) and c["field"] not in finished:
                        fail(f"{where}: 更正目标 {c['field']!r} 不在 run_finished payload 里")

    if model_count == 0 and finished is not None and finished.get("status") != "run_failed":
        warn("事件流里没有任何 harness.model 行（非 run_failed 终态）——请确认这是预期")
    # 红队⑩①：resource 事件全缺（采样线程 spawn 失败被静默、或被人为删光）必须现形。
    if finished is not None and resource_count == 0:
        fail("事件流没有任何 harness.resource 行（采样器应至少产出 1 条终采）")

    # ---- run_finished 互校 ----
    if finished is not None:
        status = finished.get("status")
        ts_finished = finished.get("ts_finished") or 0
        wall_ms = finished.get("wall_ms") or 0
        ts_started = run_started.get("ts_started") or 0
        span = ts_finished - ts_started
        if span >= 0 and wall_ms > span + 5_000:
            fail(f"run.finished.wall_ms={wall_ms} 超出 (ts_finished-ts_started)={span}+5s")
        if span >= 0 and span - wall_ms > 60_000:
            warn(f"(ts_finished-ts_started)-wall_ms={span - wall_ms}ms 差距偏大（>60s），请人工确认")
        http_retries = finished.get("http_retries")
        if is_int(http_retries) and retries_sum > http_retries:
            fail(f"各行 model.retries 之和 {retries_sum} > run.finished.http_retries {http_retries}")
        # ---- 红队③修复：汇总行与事件流逐字段互校 ----
        # 1 turn = 1 成功模型调用（drive 每轮恰好一次 complete_once，成功才计 turn 与事件），
        # 故 model_calls 与 turns 都必须等于事件流 harness.model 行数。
        model_calls = finished.get("model_calls")
        if is_int(model_calls) and model_calls != model_count:
            fail(f"run.finished.model_calls={model_calls} ≠ 事件流 harness.model 行数 {model_count}")
        turns = finished.get("turns")
        if is_int(turns) and turns != model_count:
            fail(f"run.finished.turns={turns} ≠ 事件流 harness.model 行数 {model_count}（1 turn=1 模型调用）")
        # tokens 三本账：全部 model 行都带 usage 时必须精确相等；有缺报只告警（流式可能拿不到）。
        wall_ms_v = finished.get("wall_ms") or 0
        if model_usage and all(u is not None for u in model_usage):
            for key, fkey in (
                ("input_tokens", "tokens_input"),
                ("output_tokens", "tokens_output"),
                ("cache_read_tokens", "tokens_cache_read"),
            ):
                total = sum(int(u.get(key) or 0) for u in model_usage)
                if finished.get(fkey) != total:
                    fail(
                        f"run.finished.{fkey}={finished.get(fkey)} ≠ Σmodel.usage.{key}={total}"
                    )
        elif model_count > 0:
            warn("部分 model 行无 usage——tokens_* 无法与事件流精确互校（流式响应常见）")
        # effect 网关：每条成功执行的非纯函数 tool 行恰好计一次 fresh 或 replay。
        eff_f = finished.get("effect_fresh")
        eff_r = finished.get("effect_replays")
        if is_int(eff_f) and is_int(eff_r) and eff_f + eff_r != side_effect_ok_count:
            fail(
                f"effect_fresh({eff_f})+effect_replays({eff_r}) ≠ 非纯函数且非 error 的 tool 行数 {side_effect_ok_count}"
            )
        # 墙钟合理性（红队⑩②）：调用串行，Σ model.wall ≤ run.wall；单条 wall 不得超 run 总墙钟。
        if is_u64(wall_ms_v):
            if sum(model_walls) > wall_ms_v + 5_000:
                fail(f"Σmodel.wall_ms={sum(model_walls)} > run.finished.wall_ms={wall_ms_v}+5s（调用串行，不可能超总墙钟）")
            if tool_wall_max > wall_ms_v + 5_000:
                fail(f"最大 tool.wall_ms={tool_wall_max} > run.finished.wall_ms={wall_ms_v}+5s")
        # 终态行同值引用
        if status == "run_failed":
            if terminal_rows:
                warn("status=run_failed 但存在终态 critical 行——run_failed 是 harness 外失败，通常不应有")
        else:
            expected_kind = KIND_FOR_STATUS.get(status)
            if expected_kind is None:
                fail(f"run.finished.status={status!r} 不在已知终态词表")
            else:
                if not terminal_rows:
                    fail(f"status={status} 但事件流缺少终态 critical 行（{expected_kind}）")
                else:
                    labels = []
                    for kind, payload in terminal_rows:
                        label = STATUS_KIND_TO_LABEL.get(spec_kind(payload.get("status")))
                        labels.append((kind, label))
                    if not any(
                        k == expected_kind and lab == status for k, lab in labels
                    ):
                        fail(
                            f"终态行 {labels} 与 run.finished.status={status!r}（应配 {expected_kind}）不同值"
                        )
            reason = finished.get("stop_reason")
            if is_str(reason):
                try:
                    reason_json = json.loads(reason)
                    if spec_kind(reason_json) != {
                        "completed": "completed",
                        "max_turns": "max_turns",
                        "tool_free_limit": "tool_free_limit",
                        "budget_exhausted": "budget_exhausted",
                        "stopped": "stopped",
                        "unauthorized": "unauthorized",
                    }.get(status):
                        fail(f"stop_reason 的 kind 与 status={status!r} 不一致: {reason[:120]}")
                except json.JSONDecodeError:
                    fail("stop_reason 不是合法 JSON（应为 RunStatus 序列化串）")

    # ---- judge 与 judge_declared 已并上行 ----
    if judge_seen is None and finished is not None and finished.get("status") != "run_failed":
        warn("非 run_failed 终态但没有 harness.judge 行——判分链可能未走通")

    # ---- 索引行比对 ----
    # run_dir = $AF_OBS_ROOT/runs/<line>/<arm>/<run_id> → root 在上四级。
    root = os.path.abspath(os.path.join(run_dir, os.pardir, os.pardir, os.pardir, os.pardir))
    index_rows = []
    if args.index:
        with open(args.index, "r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                # 红队⑩④：与自动定位模式同款撕裂容忍——坏行告警跳过，不 traceback。
                try:
                    index_rows.append((os.path.basename(args.index), json.loads(line)))
                except json.JSONDecodeError as err:
                    warn(f"显式索引 {args.index} 有无法解析的行（撕裂），已跳过: {err}")
    else:
        index_rows = load_index_rows(root)
    idx_row = None
    for name, row in index_rows:
        if row.get("run_id") == run_id:
            idx_row = row
            break
    if idx_row is None:
        fail(f"索引里找不到 run_id={run_id} 的行")
    else:
        required_index = [
            "run_id", "path", "ts_started", "ts_finished", "status",
            "event_count", "final_seq", "events_sha256", "torn_lines", "fp_image_digest",
        ]
        missing = [k for k in required_index if k not in idx_row]
        if missing:
            fail(f"索引行缺字段: {missing}")
        if correction_rows:
            # 证据更正流（硬规则 4）：索引行与 manifest 永不改写，钉住的是归档原字节。
            # sha/count/seq/torn/status/ts_finished 全部转由 verify_correction_chain
            # 对归档件重算比对；当前文件=归档+更正链，整体 sha 不再与索引直接比对。
            verify_correction_chain(correction_rows, parsed, data, idx_row, finished, run_id)
        else:
            actual_sha = hashlib.sha256(data).hexdigest()
            if idx_row.get("events_sha256") != actual_sha:
                fail(
                    f"events_sha256 不一致：索引 {idx_row.get('events_sha256')} ≠ 实算 {actual_sha}"
                    "（文件在索引后被截断/篡改/仍在校验中）"
                )
            if idx_row.get("final_seq") != (seqs[-1] if seqs else None):
                fail(f"索引 final_seq={idx_row.get('final_seq')} ≠ 实算 {seqs[-1] if seqs else None}")
            if idx_row.get("event_count") != len(parsed):
                fail(f"索引 event_count={idx_row.get('event_count')} ≠ 实算 {len(parsed)}")
            if idx_row.get("torn_lines") != torn:
                fail(f"索引 torn_lines={idx_row.get('torn_lines')} ≠ 实算 {torn}")
            if finished is not None and idx_row.get("status") != finished.get("status"):
                fail(
                    f"索引 status={idx_row.get('status')!r} ≠ run.finished.status={finished.get('status')!r}"
                )
            if finished is not None and idx_row.get("ts_finished") != finished.get("ts_finished"):
                fail("索引 ts_finished 与 run.finished.ts_finished 不一致")
        if idx_row.get("path") != events_path:
            fail(f"索引 path={idx_row.get('path')!r} ≠ 实际 {events_path!r}")
        if idx_row.get("ts_started") != run_started.get("ts_started"):
            fail("索引 ts_started 与 run.started.ts_started 不一致")
        if (
            is_str(run_started.get("fp_image_digest"))
            and idx_row.get("fp_image_digest") != run_started.get("fp_image_digest")
        ):
            fail("索引 fp_image_digest 与 run.started.fp_image_digest 不一致")

    # ---- 批次 manifest ----
    manifest = None
    if args.manifest:
        with open(args.manifest, "r", encoding="utf-8") as fh:
            manifest = (os.path.basename(args.manifest), json.load(fh))
    else:
        candidates = [m for m in find_manifests(root) if run_id in (m[1].get("run_ids") or [])]
        manifest = candidates[0] if candidates else None
    if manifest is None:
        warn("未找到包含本 run 的批次 manifest（--manifest 可显式指定）")
    else:
        name, m = manifest
        hashes = {}
        for _, row in index_rows:
            if row.get("run_id") in (m.get("run_ids") or []):
                hashes[row["run_id"]] = row.get("events_sha256")
        missing_runs = [r for r in (m.get("run_ids") or []) if r not in hashes]
        if missing_runs:
            fail(f"manifest {name}: 索引里缺这些 run 的行: {missing_runs[:5]}")
        else:
            recomputed = merkle_root_sorted_hex(
                [hashes[r] for r in sorted(m["run_ids"], key=lambda r: (hashes[r], r))]
            )
            if recomputed != m.get("merkle_root"):
                fail(
                    f"manifest {name}: merkle_root 不一致：清单 {m.get('merkle_root')} ≠ 重算 {recomputed}"
                )
        if m.get("run_count") != len(m.get("run_ids") or []):
            fail(f"manifest {name}: run_count 与 run_ids 长度不一致（计数互证失败）")
        # 红队⑩③：清单计数与索引行互证。
        ec_sum = 0
        status_derived = {}
        for _, row in index_rows:
            if row.get("run_id") in (m.get("run_ids") or []):
                ec_sum += int(row.get("event_count") or 0)
                st = row.get("status")
                if is_str(st):
                    status_derived[st] = status_derived.get(st, 0) + 1
        if m.get("event_count_total") != ec_sum:
            fail(
                f"manifest {name}: event_count_total={m.get('event_count_total')} ≠ Σ索引 event_count={ec_sum}"
            )
        if (m.get("status_counts") or {}) != status_derived:
            fail(
                f"manifest {name}: status_counts={m.get('status_counts')} ≠ 索引派生 {status_derived}"
            )

    # ---- 汇总 ----
    # --quiet 只压 warning 与统计；FAIL 行任何模式都必须落到 stdout（管线据此取失败原因）。
    if not args.quiet:
        for w in warns:
            print(f"WARN: {w}")
    for f_ in fails:
        print(f"FAIL: {f_}")
    if not args.quiet:
        print(
            f"[obs-checker] {run_dir}\n"
            f"  events={len(parsed)} kinds={ {k: kinds.count(k) for k in sorted(set(kinds))} }\n"
            f"  sha256={hashlib.sha256(data).hexdigest()}\n"
            f"  result: {'PASS' if not fails else 'FAIL'} ({len(fails)} fail / {len(warns)} warn)"
        )
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
