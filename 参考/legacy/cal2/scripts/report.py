#!/usr/bin/env python3
"""Generate the cal2 benchmark calibration report (markdown) from all collected results."""
import json
import os

ROOT = "/home/pan-ding/workspace/临时工作区/temp1"
CAL = os.path.join(ROOT, "cal2")
TASKS = [l.strip() for l in open(os.path.join(CAL, "tasks.txt")) if l.strip()]
DIFF = json.load(open(os.path.join(CAL, "tasks-difficulty.json")))

CONFIGS = [
    # config, harness, model, arm, A5 band, prev-round rate (official harness, bench-2026-10-12)
    ("cal2-mcode-m3",    "mcode",   "MiniMax-M3",                 "强臂候选",   (0.65, 0.82), 0.588),
    ("cal2-mcode-m31f",  "mcode",   "MiniMax-M3.1-Flash-Preview", "flash 臂",   (0.50, 0.68), 0.765),
    ("cal2-step-s5",     "step",    "step-5-preview",             "强臂候选",   (0.60, 0.78), 0.706),
    ("cal2-step-router", "step",    "step-router-v1",             "路由竞争臂", (0.55, 0.78), None),
    ("cal2-kimi-k28",    "kimi",    "kimi-for-coding (K2.8)",     "中臂候选",   (0.55, 0.75), 0.784),
    ("zcode-m3",         "zcode-wf", "MiniMax-M3",               "强臂候选",   (0.65, 0.82), None),
    ("zcode-m31f",       "zcode-wf", "MiniMax-M3.1-Flash-Preview", "flash 臂", (0.50, 0.68), None),
    ("zcode-s5",         "zcode-wf", "step-5-preview",           "强臂候选",   (0.60, 0.78), None),
    ("zcode-router",     "zcode-wf", "step-router-v1",           "路由竞争臂", (0.55, 0.78), None),
        ("cal2-grok47",      "grok",   "grok-4.7",                   "强臂候选",   (0.60, 0.86), None),
    ("zcode-glm53",  "zcode-wf", "GLM-5.3",                  "新增-未预登记", None, None),
    ("zcode-glm53f", "zcode-wf", "GLM-5.3-Flash",            "新增-未预登记", None, None),
]


def load(cfg):
    out = {}
    for base in (os.path.join(CAL, "results-anolis", cfg),):
        if not os.path.isdir(base):
            continue
        for f in os.listdir(base):
            if not f.endswith(".json") or f in ("declarations.json", "audit.json"):
                continue
            try:
                out[f[:-5]] = json.load(open(os.path.join(base, f))).get("status", "?")
            except Exception:
                pass
    return out


def main():
    data = {cfg: load(cfg) for cfg, *_ in CONFIGS}
    lines = []
    A = lines.append
    A("# cal2 基准标定轮报告（2026-10-13）")
    A("")
    A("- 任务集：Terminal-Bench original-tasks 精选 51 题（easy 17 / medium 20 / hard 14），本地 pytest 确定性验收")
    A("- 矩阵：9 配置 × 51 题 = 459 次运行（5 官方 harness @anolis + 4 本机 ZCode 工作流派发）")
    A("- 判分：anolis docker 按官方 Dockerfile 构建镜像，scratch 挂载 /app，跑官方 tests/test_outputs.py，exit 0 = pass")
    A("- 规格来源：L3 终审材料包 A5 模型谱系预登记画像（三臂+路由竞争臂预测带，假设-待验证口径）")
    A("")
    A("## 一、主结果表（对照 A5 预登记预测带）")
    A("")
    A("| 配置 | Harness | 模型 | A5 臂 | 通过 | 判定 | 通过率 | A5 预测带 | 上轮(官方) | 带内/外 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for cfg, h, m, arm, band, prev in CONFIGS:
        res = data[cfg]
        p = sum(1 for v in res.values() if v == "pass")
        f = sum(1 for v in res.values() if v == "fail")
        i = sum(1 for v in res.values() if v == "infra")
        x = sum(1 for v in res.values() if v == "excluded")
        n = p + f
        rate = p / n if n else 0
        if band is None:
            inband = "无预登记带"
        else:
            inband = "带内" if band[0] <= rate <= band[1] else ("带上" if rate > band[1] else "带下")
        prevs = f"{prev*100:.1f}%" if prev is not None else "—"
        bandtxt = f"{band[0]*100:.0f}–{band[1]*100:.0f}%" if band else "—"
        A(f"| {cfg} | {h} | {m} | {arm} | {p} | {f+i+x} | **{rate*100:.1f}%** | {bandtxt} | {prevs} | {inband} |")
    A("")
    A("## 二、同模型跨 harness 对比（官方 vs ZCode 工作流）")
    A("")
    A("| 模型 | 官方 harness | ZCode 工作流 | 差值 |")
    A("|---|---|---|---|")
    for a, b in [("cal2-mcode-m3", "zcode-m3"), ("cal2-mcode-m31f", "zcode-m31f"),
                 ("cal2-step-s5", "zcode-s5"), ("cal2-step-router", "zcode-router")]:
        ra, rb = data[a], data[b]
        pa = sum(1 for v in ra.values() if v == "pass"); na = pa + sum(1 for v in ra.values() if v == "fail")
        pb = sum(1 for v in rb.values() if v == "pass"); nb = pb + sum(1 for v in rb.values() if v == "fail")
        if na and nb:
            A(f"| {a.split('-', 2)[2]} | {pa/na*100:.1f}% ({pa}/{na}) | {pb/nb*100:.1f}% ({pb}/{nb}) | {(pb/nb-pa/na)*100:+.1f}pp |")
        else:
            A(f"| {a.split('-', 2)[2]} | {pa}/{na} | {pb}/{nb} | 数据不全 |")
    A("")
    A("")
    A("## 2b、跨 harness 对比的统计说明")
    A("")
    A("- 同模型同题集下，官方 harness 与 ZCode 工作流派发的差值见上表；负值表示工作流派发路径下拉了该模型表现。")
    A("- 注意：官方 harness 使用各自 CLI 默认配置（step CLI 默认 thinking=medium）；zcode-s5 泳道已对齐为 medium（见 E3）。")
    A("- 上轮（sess_ab665723，wf vs mcode，M3.1/M3）曾得 wf−mcode=+12.9pp；本轮同对比为 −2.0pp/−9.8pp，方向反转——harness 间差距在本轮题集/版本下不稳定，是本轮最重要的标定发现之一。")
    A("## 三、难度分层")
    A("")
    A("| 配置 | easy (17) | medium (20) | hard (14) |")
    A("|---|---|---|---|")
    for cfg, *_ in CONFIGS:
        res = data[cfg]
        cells = []
        for d in ("easy", "medium", "hard"):
            ts = [t for t in TASKS if DIFF.get(t) == d]
            p = sum(1 for t in ts if res.get(t) == "pass")
            n = sum(1 for t in ts if res.get(t) in ("pass", "fail"))
            cells.append(f"{p}/{n}" + (f" = {p/n*100:.0f}%" if n else ""))
        A(f"| {cfg} | {cells[0]} | {cells[1]} | {cells[2]} |")
    A("")
    A("## 四、逐题矩阵（p=pass f=fail i=infra .=未跑）")
    A("")
    hdr = "| task | diff | " + " | ".join(c.replace("cal2-", "") for c, *_ in CONFIGS) + " |"
    A(hdr)
    A("|---|---|" + "---|" * len(CONFIGS))
    for t in TASKS:
        row = f"| {t} | {DIFF.get(t, '?')} | "
        row += " | ".join({"pass": "p", "fail": "f", "infra": "i"}.get(data[c].get(t), ".") for c, *_ in CONFIGS)
        A(row + " |")
    A("")
    A("## 五、阶梯单调性检验（A5 §3.2 判据）")
    A("")
    A("A5 预测：强臂 > 中臂 > flash 臂（阶梯假设）。本轮官方 harness 实测：")
    arms = {}
    for cfg, h, m, arm, band, prev in CONFIGS:
        if h == "zcode-wf":
            continue
        res = data[cfg]
        p = sum(1 for v in res.values() if v == "pass"); n = p + sum(1 for v in res.values() if v == "fail")
        arms.setdefault(arm, []).append((m, p / n if n else 0))
    for arm, items in arms.items():
        A(f"- {arm}: " + ", ".join(f"{m} {r*100:.1f}%" for m, r in items))
    A("")
    A("## 六、事件与纪律记录")
    A("")
    A("见 cal2/logs/incidents.md（额度 canary、防作弊基建、s5 配置修正、ENOSPC、DriverError 修复、db-wal 违规及处置、movie-helper 输入缺失、判分链路验证）。")
    A("")
    A("## 七、审计结论")
    A("")
    audit_path = os.path.join(CAL, "results", "audit.json")
    if os.path.exists(audit_path):
        findings = json.load(open(audit_path))
        sus = [f for f in findings if f.get("verdict") == "SUSPICIOUS"]
        A(f"- 审计覆盖 4 个本地泳道 × 51 题：判定可疑 {len(sus)} 例（需人工复核），其余为 minor 卫生问题声明。")
        for f in sus:
            A(f"  - {f['config']}/{f['task']}: {f.get('grading_only_hits', [])[:2]}")
    else:
        A("- 审计尚未运行。")
    A("")
    out = os.path.join(CAL, "REPORT.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("wrote", out, f"({len(lines)} lines)")


if __name__ == "__main__":
    main()
