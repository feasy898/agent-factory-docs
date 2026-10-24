#!/usr/bin/env python3
"""bench-mes.py — af-bench results.jsonl 入 ClickHouse MES（良率/节拍/成本三账本）。

用法: bench-mes.py <results.jsonl> [--ch http://100.64.0.2:15221]
口径:
  work_order_id = <case_id>-<profile>-<attempt6>（attempt6=对 reward/status/tokens/scaffold
                  做 md5 前 6 位，重跑产生不同 attempt 不互斥）station_id = suite
  line_id = bench（trial=true 时为 bench-trial）
  kind: tokens_input / tokens_output / cache_read / turns / wall_ms / reward(1|0) / infra(1)
  event_id = <work_order_id>-<kind>（同 attempt 幂等去重）
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def _mes_conn(url=None):
    """MES ClickHouse 连接 → (base_url, auth_header)。

    2026-10-22 MES 由 pandev-comp 本机迁至 mingda-website（tailnet 100.64.0.2:15221，
    迁移动机/对账/回滚见 计划/研究组/mes迁移mingda-交付.md；本机 127.0.0.1:5221 旧实例
    保留只读 48h 作回滚锚）。解析顺序：入参 url > 环境变量 MES_CH_URL > 0600 凭据文件
    ~/.config/mes-ch/url > 缺省新 MES 地址。凭据可写 user:pass@host 形式（urllib 不
    解析 URL 内嵌凭据，故在此拆出转 Basic 头）；口令明文按密钥纪律只存 0600 文件，
    不进任何文档/回报。缺文件且无 env 落到无凭据地址→401 显性失败，不静默写旧锚点。
    """
    if url is None:
        url = os.environ.get("MES_CH_URL")
    if not url:
        try:
            with open(os.path.expanduser("~/.config/mes-ch/url"), encoding="utf-8") as f:
                url = f.read().strip()
        except OSError:
            url = "http://100.64.0.2:15221"
    auth = None
    if "@" in url:
        scheme, rest = url.split("://", 1)
        userinfo, hostpart = rest.split("@", 1)
        url = f"{scheme}://{hostpart}"
        auth = "Basic " + base64.b64encode(userinfo.encode()).decode()
    return url, auth


CH, CH_AUTH = _mes_conn()

# MES 500 根因修复（2026-10-22 修理组，见 计划/研究组/mes500-根因报告.md）：
# 本机 CH 在宿主内存压力下会间歇返回 HTTP 500（服务端 code 241
# MEMORY_LIMIT_EXCEEDED，动态硬限额塌陷），旧逻辑单次失败即丢整批事件且无痕。
# 改为有限重试（指数退避 2s/8s）；仍失败则抛出，由调用方记录（不再静默）。
CH_RETRY = 3
CH_BACKOFF = (2, 8)


def ch_query(sql, body=None):
    url = CH + "/?query=" + urllib.parse.quote(sql)
    data = body.encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if CH_AUTH:
        req.add_header("Authorization", CH_AUTH)
    last = None
    for attempt in range(CH_RETRY):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode()
        except urllib.error.HTTPError as e:
            last = e
            # 5xx=服务端可恢复类（内存限额/重启中）；4xx 是请求自身问题，重试无意义
            if e.code < 500 or attempt == CH_RETRY - 1:
                raise
            print(f"ch_query 第 {attempt + 1} 次失败 HTTP {e.code}，{CH_BACKOFF[attempt]}s 后重试",
                  file=sys.stderr)
        except urllib.error.URLError as e:
            last = e
            if attempt == CH_RETRY - 1:
                raise
            print(f"ch_query 第 {attempt + 1} 次失败 {e.reason}，{CH_BACKOFF[attempt]}s 后重试",
                  file=sys.stderr)
        time.sleep(CH_BACKOFF[attempt])
    raise last


def main():
    path = sys.argv[1]
    if "--ch" in sys.argv:
        global CH, CH_AUTH
        CH, CH_AUTH = _mes_conn(sys.argv[sys.argv.index("--ch") + 1])
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    events = []
    for row in rows:
        case = row.get("task_id") or row.get("case_id")
        import hashlib
        attempt = hashlib.md5(json.dumps({
            "r": row.get("reward", row.get("injection_success")),
            "s": row.get("status"),
            "t": row.get("tokens"),
            "sc": row.get("scaffold"),
        }, sort_keys=True).encode()).hexdigest()[:6]
        wo = f"{case}-{row['profile']}-{attempt}"
        suite = row.get("suite", "unknown")
        trial = bool(row.get("trial"))
        base = {
            "work_order_id": wo,
            "occurred_at": time.strftime("%F %T"),
            "line_id": "bench-trial" if trial else "bench",
            "station_id": suite,
        }
        toks = row.get("tokens") or {}
        for kind, qty in [
            ("tokens_input", toks.get("input", 0)),
            ("tokens_output", toks.get("output", 0)),
            ("cache_read", toks.get("cache_read", 0)),
            ("turns", row.get("turns", 0)),
            ("wall_ms", row.get("agent_wall_ms", row.get("wall_ms", 0))),
        ]:
            events.append({**base, "kind": kind, "quantity": int(qty), "event_id": f"{wo}-{kind}"})
        reward = row.get("reward")
        if "reward" not in row:
            pass
        elif reward is None:
            events.append({**base, "kind": "infra", "quantity": 1, "event_id": f"{wo}-infra"})
        else:
            events.append({
                **base,
                "kind": "reward",
                "quantity": 1 if reward else 0,
                "event_id": f"{wo}-reward",
            })
        if "injection_success" in row:
            events.append({
                **base,
                "kind": "injection_success",
                "quantity": 1 if row["injection_success"] else 0,
                "event_id": f"{wo}-injection_success",
            })
    # 幂等：查已存在的 event_id
    ids = ",".join("'" + e["event_id"] + "'" for e in events)
    existing = set()
    if ids:
        out = ch_query(f"SELECT event_id FROM af_mes.mes_event WHERE event_id IN ({ids}) FORMAT TSV")
        existing = {line.strip() for line in out.splitlines() if line.strip()}
    fresh = [e for e in events if e["event_id"] not in existing]
    if not fresh:
        print("全部已存在，0 行新增")
        return
    payload = "\n".join(json.dumps(e, ensure_ascii=False) for e in fresh)
    ch_query("INSERT INTO af_mes.mes_event FORMAT JSONEachRow", payload)
    print(f"入 MES {len(fresh)} 行（跳过重复 {len(events) - len(fresh)}）")


if __name__ == "__main__":
    main()
