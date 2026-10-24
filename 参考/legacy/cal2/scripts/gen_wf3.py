#!/usr/bin/env python3
"""Generate GLM-5.3 / GLM-5.3-Flash workflow scripts (byte-identical asks to the m31f lane)."""
import json
import os

CAL = "/home/pan-ding/workspace/临时工作区/temp1/cal2"
CONFIGS = {
    "zcode-glm53":  ("GLM-5.3",       "account:bigmodel-individual-coding-plan/GLM-5.3"),
    "zcode-glm53f": ("GLM-5.3-Flash", "account:bigmodel-individual-coding-plan/GLM-5.3-Flash"),
}
BATCH = 13
TASKS = [l.strip() for l in open(os.path.join(CAL, "tasks.txt")) if l.strip()]
assert len(TASKS) == 51

TEMPLATE = '''interface Job {{
  /** 任务名 */
  task: string;
  /** 该 agent 的独立工作目录（scratch） */
  dir: string;
  /** 任务说明文件（PREAMBLE + 原始任务指令） */
  instr: string;
}}

interface TaskOutcome {{
  /** 任务名 */
  task: string;
  /** 是否确认完成了任务要求的全部产物 */
  done: boolean;
  /** 一句话：完成了什么，或卡在哪里；如不慎看到目录外内容必须在此声明 */
  summary: string;
  /** 是否从未访问过工作目录之外的任何文件（如实回答，虚假声明按作弊处理） */
  declared_clean: boolean;
  /** 完成度 */
  status: "done" | "partial" | "stuck";
}}

const JOBS: Job[] = {jobs};

artifact.board("progress", {{
  title: "{label} · 解题进度",
  key: "task",
  status: "status",
  columns: ["done", "partial", "stuck"],
  cardTitle: "task",
  detail: [{{ field: "summary", label: "结论" }}, {{ field: "declared_clean", label: "未越界声明" }}],
}});

async function solveBatch(js: Job[]): Promise<TaskOutcome[]> {{
  return Promise.all(
    js.map(async (j) => {{
      try {{
        return await agent(`解题-${{j.task}}`, {{
        system:
          "你是一名严谨的工程师，正在参加 Terminal-Bench 自动评测。这是你个人的独立工作目录，其他任何进程不会碰它。铁律：" +
          "① 只允许在指配给你的工作目录内读写文件；严禁读取、列出或搜索该目录之外的任何路径——包括本工作区内其他任何目录、tests/、test_outputs.py、solution、答案、历史结果或归档；" +
          "② 严禁使用 ssh/scp/rsync 访问其他机器，严禁访问任务说明之外的网络资源（按任务说明使用阿里云 pip 镜像除外）；" +
          "③ 如果任务有无法满足的前提（缺文件、缺网络、缺依赖），尽力用现有手段完成能完成的部分，不要向用户提问，自主决策，并把缺前提的实际情况写进最终 summary；" +
          "④ 如不慎看到任务说明之外的内容，立即停止阅读并在 summary 中如实声明；" +
          "⑤ 完成后逐项核对任务要求的产物路径确实存在后再声明 done。任何查阅答案的作弊行为会使整个评测作废。",
      }}).ask<TaskOutcome>(
        `工作目录（只能在此目录内创建/修改文件）：${{j.dir}}\\n` +
          `第一步：完整阅读 ${{j.instr}}，严格按其中的任务说明完成工作（说明中的 /app 路径对应你的工作目录本身）。\\n` +
          `第二步：自查要求的每个产物是否存在且符合要求。\\n` +
          `最后返回 JSON：task 填 "${{j.task}}"；done 为布尔值；summary 用一句话说明结果或卡点；declared_clean 为布尔值——你是否从未访问过工作目录之外的任何文件；status 按完成度填 done/partial/stuck。`,
      );
      }} catch (e) {{
        return {{ task: j.task, done: false, summary: "agent turn failed: " + String(e).slice(0, 300), declared_clean: true, status: "stuck" }};
      }}
    }}),
  );
}}

const batches: Job[][] = [];
for (let i = 0; i < JOBS.length; i += {batch}) batches.push(JOBS.slice(i, i + {batch}));

phase("第 1 批解题（{label}）");
log(`{label}：共 ${{JOBS.length}} 题，分 ${{batches.length}} 批；第 1 批 ${{batches[0].length}} 题`);
const r1 = await solveBatch(batches[0]);
for (const o of r1) report(o, "progress");

phase("第 2 批解题（{label}）");
log(`{label}：第 2 批 ${{batches[1].length}} 题`);
const r2 = await solveBatch(batches[1]);
for (const o of r2) report(o, "progress");

phase("第 3 批解题（{label}）");
log(`{label}：第 3 批 ${{batches[2].length}} 题`);
const r3 = await solveBatch(batches[2]);
for (const o of r3) report(o, "progress");

phase("第 4 批解题（{label}）");
log(`{label}：第 4 批 ${{batches[3].length}} 题`);
const r4 = await solveBatch(batches[3]);
for (const o of r4) report(o, "progress");

const all = [...r1, ...r2, ...r3, ...r4];
return {{
  conclusion: `{label}：${{all.length}} 题完成派发，${{all.filter((o) => o.done).length}} 题自报完成，${{all.filter((o) => !o.declared_clean).length}} 题有越界声明需审计。`,
  results: all,
}};
'''

for cfg, (label, model) in CONFIGS.items():
    jobs = [
        {
            "task": t,
            "dir": os.path.join(CAL, "runs", cfg, t, "work"),
            "instr": os.path.join(CAL, "instr", t + ".md"),
        }
        for t in TASKS
    ]
    with open(os.path.join(CAL, "jobs", cfg + ".json"), "w", encoding="utf-8") as f:
        json.dump({"config": cfg, "model": model, "jobs": jobs}, f, ensure_ascii=False, indent=1)
    for j in jobs:
        os.makedirs(j["dir"], exist_ok=True)
    script = TEMPLATE.format(jobs=json.dumps(jobs, ensure_ascii=False), batch=BATCH, label=label)
    path = os.path.join(CAL, "scripts", f"wf_{cfg}.ts")
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    print("wrote", path, len(script), "bytes,", len(jobs), "jobs")
print("done")
