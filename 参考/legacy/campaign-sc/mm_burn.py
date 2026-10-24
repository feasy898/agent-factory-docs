#!/usr/bin/env python3
"""mm_burn.py [windows...] — MiniMax 账户级用量燃烧曲线。
数据源: ~/.minimax/v2/sqlite/runtime-state.sqlite 的 local_runtime_token_usage（逐轮记账，全账户）。
输出各窗口燃烧量与速率；--detail 按模型分列；--cap 反推：窗口燃烧外推到撞墙的等效值。
"""
import os, sqlite3, sys, time

DB = os.path.expanduser("~/.minimax/v2/sqlite/runtime-state.sqlite")
NOW = time.time() * 1000
con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)

detail = "--detail" in sys.argv
rows = con.execute(
    "select ts, model, input_tokens, output_tokens, reasoning_tokens, cache_read_tokens, cache_write_tokens"
    " from local_runtime_token_usage").fetchall()
tot = lambda r: (r[2] or 0) + (r[3] or 0) + (r[4] or 0)  # 计费近似：in+out+reasoning（cache 折扣另计）

print("total turns on record: %d (库内累计 %.0fM tok)" % (len(rows), sum(tot(r) for r in rows) / 1e6))
for h in (1, 3, 5, 24):
    t0 = NOW - h * 3600 * 1000
    sel = [r for r in rows if (r[0] or 0) >= t0]
    s = sum(tot(r) for r in sel)
    print("近%2dh: %8.1fM tok (%.1fM/h, %d turns)" % (h, s / 1e6, s / 1e6 / h, len(sel)))
    if detail:
        by = {}
        for r in sel:
            by[r[1]] = by.get(r[1], 0) + tot(r)
        for m, v in sorted(by.items(), key=lambda kv: -kv[1]):
            print("    %-46s %8.1fM" % (m, v / 1e6))
