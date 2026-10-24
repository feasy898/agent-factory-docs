interface Job {
  /** 任务名 */
  task: string;
  /** 该 agent 的独立工作目录（scratch） */
  dir: string;
  /** 任务说明文件（PREAMBLE + 原始任务指令） */
  instr: string;
}

interface TaskOutcome {
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
}

const JOBS: Job[] = [{"task": "aimo-airline-departures", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/aimo-airline-departures/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/aimo-airline-departures.md"}, {"task": "analyze-access-logs", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/analyze-access-logs/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/analyze-access-logs.md"}, {"task": "bank-trans-filter", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/bank-trans-filter/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/bank-trans-filter.md"}, {"task": "count-call-stack", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/count-call-stack/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/count-call-stack.md"}, {"task": "countdown-game", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/countdown-game/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/countdown-game.md"}, {"task": "cpp-compatibility", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/cpp-compatibility/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/cpp-compatibility.md"}, {"task": "flood-monitoring-basic", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/flood-monitoring-basic/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/flood-monitoring-basic.md"}, {"task": "grid-pattern-transform", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/grid-pattern-transform/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/grid-pattern-transform.md"}, {"task": "hello-world", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/hello-world/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/hello-world.md"}, {"task": "ilp-solver", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/ilp-solver/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/ilp-solver.md"}, {"task": "jq-data-processing", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/jq-data-processing/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/jq-data-processing.md"}, {"task": "jsonl-aggregator", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/jsonl-aggregator/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/jsonl-aggregator.md"}, {"task": "mahjong-winninghand", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/mahjong-winninghand/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/mahjong-winninghand.md"}, {"task": "multistep-definite-integral", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/multistep-definite-integral/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/multistep-definite-integral.md"}, {"task": "recover-accuracy-log", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/recover-accuracy-log/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/recover-accuracy-log.md"}, {"task": "recover-obfuscated-files", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/recover-obfuscated-files/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/recover-obfuscated-files.md"}, {"task": "schedule-vacation", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/schedule-vacation/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/schedule-vacation.md"}, {"task": "constraints-scheduling", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/constraints-scheduling/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/constraints-scheduling.md"}, {"task": "db-wal-recovery", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/db-wal-recovery/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/db-wal-recovery.md"}, {"task": "distribution-search", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/distribution-search/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/distribution-search.md"}, {"task": "enemy-grid-escape", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/enemy-grid-escape/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/enemy-grid-escape.md"}, {"task": "gcode-to-text", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/gcode-to-text/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/gcode-to-text.md"}, {"task": "git-leak-recovery", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/git-leak-recovery/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/git-leak-recovery.md"}, {"task": "huarong-dao-solver", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/huarong-dao-solver/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/huarong-dao-solver.md"}, {"task": "largest-eigenval", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/largest-eigenval/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/largest-eigenval.md"}, {"task": "log-summary-date-ranges", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/log-summary-date-ranges/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/log-summary-date-ranges.md"}, {"task": "modernize-scientific-stack", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/modernize-scientific-stack/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/modernize-scientific-stack.md"}, {"task": "openssl-selfsigned-cert", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/openssl-selfsigned-cert/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/openssl-selfsigned-cert.md"}, {"task": "polyglot-c-py", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/polyglot-c-py/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/polyglot-c-py.md"}, {"task": "portfolio-optimization", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/portfolio-optimization/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/portfolio-optimization.md"}, {"task": "puzzle-solver", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/puzzle-solver/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/puzzle-solver.md"}, {"task": "regex-log", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/regex-log/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/regex-log.md"}, {"task": "schemelike-metacircular-eval", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/schemelike-metacircular-eval/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/schemelike-metacircular-eval.md"}, {"task": "solve-maze-challenge", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/solve-maze-challenge/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/solve-maze-challenge.md"}, {"task": "sqlite-db-truncate", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/sqlite-db-truncate/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/sqlite-db-truncate.md"}, {"task": "tree-directory-parser", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/tree-directory-parser/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/tree-directory-parser.md"}, {"task": "vertex-solver", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/vertex-solver/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/vertex-solver.md"}, {"task": "cancel-async-tasks", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/cancel-async-tasks/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/cancel-async-tasks.md"}, {"task": "circuit-fibsqrt", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/circuit-fibsqrt/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/circuit-fibsqrt.md"}, {"task": "feal-differential-cryptanalysis", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/feal-differential-cryptanalysis/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/feal-differential-cryptanalysis.md"}, {"task": "feal-linear-cryptanalysis", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/feal-linear-cryptanalysis/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/feal-linear-cryptanalysis.md"}, {"task": "llm-inference-batching-scheduler", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/llm-inference-batching-scheduler/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/llm-inference-batching-scheduler.md"}, {"task": "model-extraction-relu-logits", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/model-extraction-relu-logits/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/model-extraction-relu-logits.md"}, {"task": "movie-helper", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/movie-helper/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/movie-helper.md"}, {"task": "organization-json-generator", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/organization-json-generator/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/organization-json-generator.md"}, {"task": "password-recovery", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/password-recovery/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/password-recovery.md"}, {"task": "path-tracing-reverse", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/path-tracing-reverse/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/path-tracing-reverse.md"}, {"task": "rare-mineral-allocation", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/rare-mineral-allocation/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/rare-mineral-allocation.md"}, {"task": "regex-chess", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/regex-chess/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/regex-chess.md"}, {"task": "reverse-engineering", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/reverse-engineering/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/reverse-engineering.md"}, {"task": "stable-parallel-kmeans", "dir": "/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-m27hs/stable-parallel-kmeans/work", "instr": "/home/pan-ding/workspace/临时工作区/temp1/cal2/instr/stable-parallel-kmeans.md"}];

artifact.board("progress", {
  title: "M2.7-Highspeed · 解题进度",
  key: "task",
  status: "status",
  columns: ["done", "partial", "stuck"],
  cardTitle: "task",
  detail: [{ field: "summary", label: "结论" }, { field: "declared_clean", label: "未越界声明" }],
});

async function solveBatch(js: Job[]): Promise<TaskOutcome[]> {
  return Promise.all(
    js.map(async (j) => {
      try {
        return await agent(`解题-${j.task}`, {
        system:
          "你是一名严谨的工程师，正在参加 Terminal-Bench 自动评测。这是你个人的独立工作目录，其他任何进程不会碰它。铁律：" +
          "① 只允许在指配给你的工作目录内读写文件；严禁读取、列出或搜索该目录之外的任何路径——包括本工作区内其他任何目录、tests/、test_outputs.py、solution、答案、历史结果或归档；" +
          "② 严禁使用 ssh/scp/rsync 访问其他机器，严禁访问任务说明之外的网络资源（按任务说明使用阿里云 pip 镜像除外）；" +
          "③ 如果任务有无法满足的前提（缺文件、缺网络、缺依赖），尽力用现有手段完成能完成的部分，不要向用户提问，自主决策，并把缺前提的实际情况写进最终 summary；" +
          "④ 如不慎看到任务说明之外的内容，立即停止阅读并在 summary 中如实声明；" +
          "⑤ 完成后逐项核对任务要求的产物路径确实存在后再声明 done。任何查阅答案的作弊行为会使整个评测作废。",
      }).ask<TaskOutcome>(
        `工作目录（只能在此目录内创建/修改文件）：${j.dir}\n` +
          `第一步：完整阅读 ${j.instr}，严格按其中的任务说明完成工作（说明中的 /app 路径对应你的工作目录本身）。\n` +
          `第二步：自查要求的每个产物是否存在且符合要求。\n` +
          `最后返回 JSON：task 填 "${j.task}"；done 为布尔值；summary 用一句话说明结果或卡点；declared_clean 为布尔值——你是否从未访问过工作目录之外的任何文件；status 按完成度填 done/partial/stuck。`,
      );
      } catch (e) {
        return { task: j.task, done: false, summary: "agent turn failed: " + String(e).slice(0, 300), declared_clean: true, status: "stuck" };
      }
    }),
  );
}

const batches: Job[][] = [];
for (let i = 0; i < JOBS.length; i += 13) batches.push(JOBS.slice(i, i + 13));

phase("第 1 批解题（M2.7-Highspeed）");
log(`M2.7-Highspeed：共 ${JOBS.length} 题，分 ${batches.length} 批；第 1 批 ${batches[0].length} 题`);
const r1 = await solveBatch(batches[0]);
for (const o of r1) report(o, "progress");

phase("第 2 批解题（M2.7-Highspeed）");
log(`M2.7-Highspeed：第 2 批 ${batches[1].length} 题`);
const r2 = await solveBatch(batches[1]);
for (const o of r2) report(o, "progress");

phase("第 3 批解题（M2.7-Highspeed）");
log(`M2.7-Highspeed：第 3 批 ${batches[2].length} 题`);
const r3 = await solveBatch(batches[2]);
for (const o of r3) report(o, "progress");

phase("第 4 批解题（M2.7-Highspeed）");
log(`M2.7-Highspeed：第 4 批 ${batches[3].length} 题`);
const r4 = await solveBatch(batches[3]);
for (const o of r4) report(o, "progress");

const all = [...r1, ...r2, ...r3, ...r4];
return {
  conclusion: `M2.7-Highspeed：${all.length} 题完成派发，${all.filter((o) => o.done).length} 题自报完成，${all.filter((o) => !o.declared_clean).length} 题有越界声明需审计。`,
  results: all,
};
