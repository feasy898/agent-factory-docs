#!/usr/bin/env python3
"""regen-index.py — 沙箱工具：为（可能被篡改的）事件流重生索引行+批次 manifest。

用途：注入②/③ 需要构造"记录被篡改但索引/manifest 自洽"的场景，
以隔离出单一致命异常（指纹字段不符 / 判定被伪造成），证明拦它的是哪道门。
重算口径与 obs-checker 读侧一致（events_sha256=整文件字节 sha；merkle=RFC6962 风格）。
"""
import hashlib
import json
import sys


def merkle_root_sorted_hex(hashes):
    def leaf(h):
        return hashlib.sha256(b"\x00" + h.encode("ascii")).digest()

    def node(l, r):
        return hashlib.sha256(b"\x01" + l + r).digest()

    level = [leaf(h) for h in hashes]
    while len(level) > 1:
        nxt = []
        i = 0
        while i < len(level):
            if i + 1 == len(level):
                nxt.append(level[i])
            else:
                nxt.append(node(level[i], level[i + 1]))
            i += 2
        level = nxt
    return level[0].hex()


def main():
    events_path = sys.argv[1]
    index_path = sys.argv[2]
    manifest_path = sys.argv[3]
    data = open(events_path, "rb").read()
    text = data.decode("utf-8", errors="replace")
    raw_lines = text.split("\n")
    trailing = not data.endswith(b"\n")
    if raw_lines and raw_lines[-1] == "":
        raw_lines = raw_lines[:-1]
    torn = 0
    parsed = []
    for i, line in enumerate(raw_lines):
        if line.strip() == "":
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            torn += 1
            if i != len(raw_lines) - 1:
                print(f"ERROR: 第 {i+1} 行坏且不在末尾（不允许的形态）")
                return 2
    if trailing:
        torn += 1
    run_started = parsed[0]["payload"]
    finished = None
    judge = None
    for ev in parsed:
        if ev.get("kind") == "harness.run_finished":
            finished = ev["payload"]
        if ev.get("kind") == "harness.judge":
            judge = ev["payload"]
    run_id = run_started["run_id"]
    row = {
        "run_id": run_id,
        "path": events_path,
        "ts_started": run_started["ts_started"],
        "ts_finished": finished["ts_finished"] if finished else None,
        "status": finished["status"] if finished else "run_failed",
        "event_count": len(parsed),
        "final_seq": parsed[-1]["seq"],
        "events_sha256": hashlib.sha256(data).hexdigest(),
        "torn_lines": torn,
        "fp_image_digest": run_started.get("fp_image_digest"),
    }
    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest = {
        "batch_id": "drill-batch",
        "run_count": 1,
        "run_ids": [run_id],
        "event_count_total": row["event_count"],
        "status_counts": {row["status"]: 1},
        "merkle_root": merkle_root_sorted_hex([row["events_sha256"]]),
        "merkle_algo": "rfc6962-style: leaf=sha256(0x00||ascii(events_sha256)), node=sha256(0x01||l||r), odd-promoted, over lexicographically sorted events_sha256 list",
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print(f"索引行已写: {index_path}")
    print(f"  events_sha256={row['events_sha256'][:16]}… event_count={row['event_count']} final_seq={row['final_seq']} torn={torn}")
    print(f"manifest 已写: merkle_root={manifest['merkle_root'][:16]}…")


if __name__ == "__main__":
    sys.exit(main())
