#!/usr/bin/env python3
"""Compare pre/post re-judge verdicts for the cal2 configs whose scratch survived."""
import glob
import json
import os

B = "/home/pan-ding/bench/results"


def tally(d):
    r = {}
    for f in glob.glob(os.path.join(d, "*.json")):
        n = os.path.basename(f)[:-5]
        try:
            r[n] = json.load(open(f)).get("status")
        except Exception:
            pass
    p = sum(1 for v in r.values() if v == "pass")
    fl = sum(1 for v in r.values() if v == "fail")
    i = sum(1 for v in r.values() if v == "infra")
    x = sum(1 for v in r.values() if v == "excluded")
    n = p + fl
    return dict(p=p, f=fl, infra=i, excl=x, rate=(p / n * 100 if n else 0.0))


print(f"{'config':<15}{'OLD (退化镜像)':>22}{'NEW (修复环境)':>22}   delta")
for c in ["cal2-grok47", "zcode-m3", "zcode-m31f", "zcode-s5", "zcode-router"]:
    new = tally(os.path.join(B, c))
    pre = os.path.join(B, c + ".prefix")
    old = tally(pre) if os.path.isdir(pre) else None
    olds = f"{old['p']}/{old['p']+old['f']} = {old['rate']:.1f}%" if old else "—"
    news = f"{new['p']}/{new['p']+new['f']} = {new['rate']:.1f}%"
    d = f"{(new['rate']-old['rate']):+.1f}pp" if old else ""
    print(f"{c:<15}{olds:>22}{news:>22}   {d}  (infra={new['infra']}, excl={new['excl']})")
