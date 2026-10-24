#!/usr/bin/env python3
"""job_usage.py — 把 mcode 会话的 token 用量映射回战役 job。
用法: python3 job_usage.py <wave_root> [days...]   默认扫描今天+昨天的会话目录。
原理: 每个 job 的 prompt.txt 是 mcode exec 的首条用户消息；按内容前缀匹配会话。
输出: <wave_root>/results/usage.json  {job: {"totalTokens":N,"input":N,"output":N,"calls":N,"wallSec":N}}
"""
import json, os, sys, glob, datetime

root = sys.argv[1]
days = sys.argv[2:] or []
base = os.path.expanduser('~/.minimax/v2/sessions')
if not days:
    today = datetime.date.today()
    days = [(today - datetime.timedelta(days=d)).strftime('%Y/%m/%d') for d in range(0, 3)]

# 1) job -> prompt 指纹（取 prompt 去掉技术块后的任务指令行 + 前 200 字符做包含匹配）
jobs = {}
for pj in glob.glob(os.path.join(root, 'runs', '*', '*', 'prompt.txt')):
    job = os.path.relpath(os.path.dirname(pj), os.path.join(root, 'runs'))
    text = open(pj, encoding='utf-8', errors='replace').read()
    # 任务指令 marker 之后的部分对所有臂相同；臂区分靠技术块首行
    marker = '--- TASK INSTRUCTION (verbatim) ---'
    instr = text.split(marker)[-1].strip()[:300]
    tech = '' if '【' not in text[:2000] else text[:2000].split('【')[1].split('】')[0]
    jobs[job] = (instr, tech)

def norm(s):
    return ' '.join(s.split())

job_fp = {j: (norm(i), norm(t)) for j, (i, t) in jobs.items()}
instr_to_jobs = {}
for j, (i, t) in job_fp.items():
    instr_to_jobs.setdefault(i, []).append((j, t))

usage = {}
for day in days:
    for sd in glob.glob(os.path.join(base, day, '*')):
        mj = os.path.join(sd, 'messages.jsonl')
        if not os.path.isfile(mj):
            continue
        try:
            first_user = None
            tot = {'totalTokens': 0, 'input': 0, 'output': 0, 'calls': 0}
            t0 = t1 = None
            with open(mj, encoding='utf-8', errors='replace') as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    ts = d.get('timestamp') or d.get('createdAtMs')
                    if isinstance(ts, (int, float)):
                        t0 = ts if t0 is None else min(t0, ts)
                        t1 = ts if t1 is None else max(t1, ts)
                    role = d.get('role') or (d.get('message', {}) or {}).get('role')
                    if first_user is None and role == 'user':
                        c = d.get('content') or (d.get('message', {}) or {}).get('content')
                        if isinstance(c, list):
                            c = ' '.join(x.get('text', '') for x in c if isinstance(x, dict))
                        if isinstance(c, str):
                            first_user = norm(c)
                    u = d.get('usage') or (d.get('message', {}) or {}).get('usage')
                    if isinstance(u, dict) and u.get('totalTokens'):
                        tot['totalTokens'] += u['totalTokens']
                        tot['input'] += u.get('input', 0)
                        tot['output'] += u.get('output', 0)
                        tot['calls'] += 1
            if first_user is None or tot['calls'] == 0:
                continue
            # 匹配 job：任务指令前缀包含 + 技术块名包含
            for instr, cands in instr_to_jobs.items():
                if instr[:200] in first_user:
                    for j, t in cands:
                        if (t and t in first_user) or (not t and '【' not in first_user[:2500]):
                            usage[j] = {**tot, 'wallSec': int((t1 - t0) / 1000) if t0 and t1 else None}
                            break
                    break
        except Exception:
            continue

out = os.path.join(root, 'results', 'usage.json')
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(usage, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'mapped {len(usage)}/{len(jobs)} jobs -> {out}')
