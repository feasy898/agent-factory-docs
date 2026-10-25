# ADAS → AFB DSL 翻译记录（草稿）

- 目标：ADAS（Automated Design of Agentic Systems，Hu et al. 2024）
- 草稿：`/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿/ADAS.yaml`
- 输入依据（按序读完）：
  1. `计划/研究组/对齐机制卡/INDEX.md`（第 25 行：ADAS.md 卡片，成，3609 字）
  2. `计划/研究组/对齐机制卡/ADAS.md`（全卡；⑥(a) 8 条 / ⑥(b) 7 条）
  3. `计划/研究组/DSL-语法提案-B.md`（§1 七段字段表 L36–L246、§2 正交性 L249–L271、§4 样例 2/3 L450–L776、§5 不变量 L1341–L1555、§7 分级 L1595）
  4. `计划/研究组/DSL-语法择优-裁决-20261024.md` §二-1（`meta.topology_selector`，L21）、§二-2（`escape.kind` 七类词表，L22）
  5. `af-wt-phase2-dsl/crates/af-dsl/`（M1 已落地：`src/model.rs:27-65` meta+topology_selector、`src/model.rs:538-559` escape.kind 七类枚举、`src/validate/refs.rs` 引用闭包、`src/validate/inv2.rs` INV-2）

> 一句话定性（承提案 B §7 L1595）：ADAS = **必须逃逸舱（大部）**。AFB 能承载的是「MAS 搜索外壳 + 发现物的固定执行图」；meta agent 生成候选程序这件事本身是 LLM 节点（可表达），但候选程序的运行时拓扑、新角色、自举替换、任意 Python、不定形状反馈、可编程选择打分六类机制**在 L0–L3 无落点**，全部走 `escape` 记账。

---

## 1. 机制 → 语法映射表（逐条对应卡 ⑥）

### ⑥(a) 可映射为「标准拓扑 + 组件」的机制（8 条，全部有落点）

| # | 卡片 ⑥(a) 机制 | AFB 落点（草稿中的具体位置） | 说明 / 近似 |
|---|---|---|---|
| a1 | Meta Agent 生成候选 | `mas_loop.loop_body.meta_agent`（`kind: task` + `uses.model: route.main@1`，`emits.candidate: candidate_code`，`writes: [candidates]`） | 单节点 LLM；产出是**源码工件**（`candidate_code` 类型），非自由文本 |
| a2 | MAS 外层迭代 | `mas_loop`（`loop` 构造：`max_iterations: 20` / `carried` 三槽 / `safety_points: [verifier(check), human_stop(human)]` / `exit_when` / `on_exhausted: keep_best`） | 反思-修订回路：生成→执行→验证→反馈回灌→再生成 |
| a3 | 候选代码交接给执行器 | 边 `meta_agent.candidate → role_registry.candidate / candidate_run.candidate`（typed handoff，`envelope` 未用；`candidate_code` 为结构化源码工件） | 工件交接用类型化工件边（提案 B §1.2 `edges` 四字段） |
| a4 | 执行反馈回灌 | 两条通道：① 边 `feedback_parse.note → meta_agent.note` + `context.sections` 的 `from: edge` 段；② `exec_logs` 槽经 `from: store / latest_k` 段进入上下文（历史迭代） | 卡③「反馈以文本块追加进上下文」在此被声明式化为「边端口 + store 视图」 |
| a5 | 任务验证 | `verifier`（`kind: check` + `uses.unit: pkg.adaskit.verifier@1`，内建 `passed` 端口），`reads: [answers_ref]` | 验证器外部化（INV-4）；`verifier2` 是自举阶段的同型节点 |
| a6 | 代码内角色函数 → 多角色 + 工件交接 | **部分**：DSL 面只能承载「发现物的固定执行图」——`candidate_run` 的角色调用关系由生成代码在运行时决定，故该条的实际落点落在 `role_registry` + `candidate_run` 两个逃逸节点上；DSL 侧的「角色间以工件交接」由 `candidate_code → role_table → run_output` 的 typed 端口链表达 | 见 §3 逃逸清单 b1/b2。**这是本目标覆盖度最弱的一格** |
| a7 | 候选与分数留存 | `stores`：`candidates`（源码，单写 `mas_loop.meta_agent`）、`records`（候选↔分数对，单写 `mas_loop.scoreboard`）、`exec_logs`（执行日志，单写 `mas_loop.sandbox_env`）、`boot_records`（自举阶段记分板） | 全部 `lifecycle: run` + 有界 `retention`；单写者经 INV-2 编译期核对 |
| a8 | 跨域迁移（图复用/预置子图挂载） | `meta.topology_selector`（裁决 §二-1）：`rules` 引用已版本化的发现物图 `pkg.adaskit.discovered_maze@1` / `discovered_wordle@1`，`fallback: pkg.adaskit.mas_search@1`；运行期的「图 → 任意代码」实例化落在 `code_compile` 逃逸 | 选择器为**编译期**语义（产物仍是单一确定图）；运行期挂载 = 逃逸 b7 |

### ⑥(b) 需要逃逸舱的机制（7 条，全部以 `escape` 构造记账）

| # | 卡片 ⑥(b) 机制 | 逃逸节点 | `escape.kind`（七类词表） | 理由（写进 `escape.reason`） |
|---|---|---|---|---|
| b1 | 运行时动态决定拓扑 | `mas_loop.loop_body.candidate_run`、`boot_loop.loop_body.cand_run2` | `program_synthesis` | 候选系统的角色调用关系与控制流写在生成的 Python 里，运行前不可静态枚举为节点/边 |
| b2 | 运行时新增角色 | `mas_loop.loop_body.role_registry` | `dynamic_tool_registry` | 生成的代码可 `def` 出模板预设之外的角色函数与工具，角色集合运行前不可枚举 |
| b3 | 自举（meta agent 被发现物替换） | `root.bootstrap_meta` | `meta_loop` | 拓扑递归替换、可无限嵌套；核心只能承接包内给出的「发现物即新 meta agent」程序 |
| b4 | 任意 Python 能力（import/文件/未登记库） | `mas_loop.loop_body.sandbox_env`、`boot_loop.loop_body.sandbox2` | `env_adapter` | 沙箱进程边界：任意 Python 在包内执行器完成，stdout/stderr/traceback/退出码在边界归一为工件 |
| b5 | 不定形状的反馈与评估 | `mas_loop.loop_body.feedback_parse` | `free_text_parser` | 反馈是 traceback/工具日志/自由文本/数值混合体，固定 schema 覆盖不了；解析在包内完成，核心只收结构化 `feedback_note` |
| b6 | 程序化选择与打分（多次采样/投票/成功率聚合/多任务加权） | `root.selector` | `llm_predicate` | 「各任务多次运行准确率排序」是可编程聚合，难以退化为静态边权与单字段排序 |
| b7 | 编译目标差异（DSL → 任意代码） | `root.code_compile` | `program_synthesis` | 发现物要落成 while/try/递归等嵌套控制流并在新域实例化，DSL 只能表达图 |

> **词表覆盖情况**：七类中用到 6 类（`dynamic_tool_registry` / `program_synthesis` / `meta_loop` / `env_adapter` / `free_text_parser` / `llm_predicate`）；**`runtime_context_mutation` 未使用**，理由：meta agent 的上下文构造（卡③「消息构造」）有静态近似（`context.sections` 的 template/input/edge/store 四类段 + `latest_k` 视图），不必逃逸；真正在运行时改写上下文的部分发生在被逃逸的候选程序内部，已计入 b1/b4。

---

## 2. 逃逸清单（9 个逃逸节点 / 覆盖 7 条卡片项）

| 逃逸节点（草稿路径） | kind | share_budget_pct | 对应卡片项 |
|---|---|---|---|
| `mas_loop.loop_body.role_registry` | `dynamic_tool_registry` | 10 | b2 |
| `mas_loop.loop_body.candidate_run` | `program_synthesis` | 25 | b1 |
| `mas_loop.loop_body.sandbox_env` | `env_adapter` | 15 | b4 |
| `mas_loop.loop_body.feedback_parse` | `free_text_parser` | 8 | b5 |
| `root.selector` | `llm_predicate` | 12 | b6 |
| `root.bootstrap_meta` | `meta_loop` | 10 | b3 |
| `root.code_compile` | `program_synthesis` | 15 | b7 |
| `boot_loop.loop_body.cand_run2` | `program_synthesis` | 20 | b1 的第二实例（自举阶段） |
| `boot_loop.loop_body.sandbox2` | `env_adapter` | 5 | b4 的第二实例（自举阶段） |

记账口径：每条逃逸四字段（`impl_ref`/`reason`/`owner`/`share_budget_pct`）齐全（E2210 口径），`kind` 取自裁决 §二-2 的七类闭环词表。单条占比均 ≤30%（ADR-001 §3 警戒线）。**各条占比之和为 120%**——本稿按「该逃逸面占其所在阶段预算的份额」理解（每条 ≤30% 才有意义），跨阶段求和无意义；见 §4 语法不确定点第 5 条。

---

## 3. 草稿结构（供快速定位）

```
root: loader → mas_loop → best_pick → selector → bootstrap_meta → boot_loop → final_report → code_compile
mas_loop.body: meta_agent → role_registry → candidate_run → sandbox_env → verifier → feedback_parse → scoreboard → human_stop
               （回边：scoreboard.score → meta_agent.score；feedback_parse.note → meta_agent.note；human_stop.decision → meta_agent.decision）
boot_loop.body: boot_meta_agent → cand_run2 → sandbox2 → verifier2 → scoreboard2
stores: candidates / records / exec_logs / boot_records / answers_ref(eval_input)
```

- 停止/失败（卡④）：`policies.stop`（迭代上限、预算到顶）+ `policies.failures` 五类闭环词表（`schema_invalid` / `tool_error` / `timeout` / `gate_refused` / `budget_exhausted`），`route: next_iteration` 回灌下一迭代（`feedback` 指明回灌哪类工件）。
- 人工终止（卡④-5）：`human_stop`（`human` 构造，`resume.schema` 类型化恢复值 `stop_decision`），并进 `exit_when`。
- 择优而非取最后一版（卡④-6）：`best_pick` 用 `select_best` op 静态排序，`selector` 逃逸做程序化多任务加权排序；`on_exhausted: keep_best` 保证迭代耗尽仍交付历史最佳。
- 预算（卡⑤）：meta 侧 `node:mas_loop.meta_agent` 的 tokens 预算与计划级 cents 分开计（卡⑤「meta 侧与候选侧分开计」的静态近似）。

---

## 4. 语法不确定点 / 诚实标注（逐条）

1. **`ops` 的两段式（中间产物 + store 末端落点）**：`scoreboard` 用 `project verdict → score` 再 `project score → records`，把「记分板既发端口又写槽」表达成两个 op。提案 B §1.3 只说「`into` 命名一个新中间产物，或末端落点 = emits 端口 / writes 中的 store」，**没说最后一个 op 的 `into` 是 store 而前面的 `into` 是中间产物是否合规**。参考样例 3（Debate）里 `into: result` 同时是中间产物又是 emits 端口，本稿沿用该形状。E2209 若收严需复核。
2. **`select_best` 的 `by` 指向 store 内字段**：`best_pick` 的 op `port: records` 指向 `reads` 中的 store，`by: reward_milli` 指向 item 的字段。提案 §1.3 只说 op 的 `port` 可命名「`reads` 中的 store」，未规定 `by` 的字段寻址路径。装载期核对（E9003）时需确认。
3. **`consumes` 声明了但未参与 ops 的端口**：`best_pick` 声明 `consumes: {done: signal}`（控制节点入边）但 op 读的是 store；`final_report` 的 `consumes: {final: ...}` 恰被 op 使用。INV-1 的「入边端口须被 section 引用」只约束 LLM 节点，transform 侧未定义——本稿按「LLM 严格、非 LLM 宽松」处理。
4. **`human` 节点进了搜索循环**：卡④-5 的「人工终止」在语法上只能做成循环体里的一等节点，每轮都要经过；真实语义是「平时不介入、按需终止」。本稿用 `exit_when` 里的 `human_stop.decision.stop == true` 表达终止意图，但**「非阻塞按需介入」这一点语法无落点**，属近似。
5. **`escape.share_budget_pct` 的求和口径**：见 §2 末尾（120%）。ADR-001 §3 只规定单条 >30% 警戒，未规定跨节点求和是否需 ≤100%。
6. **`meta.topology_selector` 的候选图引用形态**：本稿用 `pkg.adaskit.discovered_maze@1`（包产物形态，与 `uses.model` / `template_ref` 一致）。裁决 §二-1 只说「已声明的版本化图/子图」，未规定命名空间前缀；也可能要求图名注册在文档内的 `types`/图清单里——待编译期定。
7. **`loop.args` 值写点号路径**：`boot_loop.args.boot = bootstrap_meta.boot_program`（承提案 B §1.3「`节点.端口[.字段]`」）。该值解析基准是**循环节点所在作用域**（root），故引用 root 节点合法；此为读提案推断，af-dsl 的 `check_arg_ref` 实现（`refs.rs:404-465`）按「同作用域」解析，本稿通过。
8. **逃逸节点不写 `context`**：逃逸节点只带 `consumes`/`reads`/`emits`/`escape`（照 AFlow 样例 4 的 `synth` 形状），不带 `context.sections`——逃逸面不是 LLM-bound 节点，故 INV-1 不适用。
9. **`route` 构造在本稿未被使用**：所有分支（迭代继续/终止、失败回灌）由 `exit_when` + `policies.failures.route` + `on_exhausted` 覆盖；提案 B §1.5 的 route 归一化在 M4 落地后再复核是否需要 `route` 表达「验证通过/不通过」的分叉（当前用 `exit_when` + `gate_refused` 失败类表达）。

---

## 5. 自检记录（全部实跑，命令与输出见下）

| 检查项 | 命令 | 结果 |
|---|---|---|
| YAML 解析（ask 指定） | `python3 -c "import yaml,sys; yaml.safe_load(open('.../ADAS.yaml'))"` | PASS，顶层键集 = `['edges','meta','nodes','policies','stores','types','version']`（七段无漂移） |
| M1 前端真解析 + 语义校验 | `/tmp/afb-harness/target/debug/afb-harness .../ADAS.yaml`（path 依赖 `af-dsl` crate，`cargo build --offline`，`CARGO_TARGET_DIR=/tmp/afb-harness/target`） | `PARSE OK: name=adas_mas_search entry=loader` / `VALIDATE OK: 0 violations`（信封 E0001–E0004、serde 形状、引用闭包 E2xxx、INV-2 全过） |
| 同工具的判别力对照 | 同上跑 `af-wt-phase2-dsl/crates/af-dsl/testdata/sample1..6.yaml` | 6/6 `VALIDATE OK: 0 violations`（与 golden 一致，说明「0 violations」不是空跑） |
| CEL 保守子集（实跑 cel-parser 0.10.1） | `/home/pan-ding/.cache/afb-scratch/cel-target/debug/cel-check < /tmp/cel-check/adas_exprs.tsv`（`Parser::parse` + `references().functions() ⊆ 算子白名单` + 根绑定清单；源码 `/tmp/cel-check/src/main.rs`） | `total=6 fail=0`；根绑定 = `human_stop/scoreboard/scoreboard2/steps/budget/input`，算子仅 `_==_ _||_ _>=_` |
| 六节自检（信封/类型表/单写者/配额/预算/逃逸记账）+ INV-1 式上下文闭合 + INV-3 自验证 + INV-4 eval_input 读者 + 孤立节点 | `python3 /tmp/adas_selfcheck.py` | 「无（十项检查全过）」；逃逸节点 9、七类词表覆盖 6 类、单条占比均 ≤30% |

**未跑 / 未验证项（如实）**：
- 编译器 M2–M4（`context.sections` 语义校验 INV-1、INV-3/INV-4、route 归一化、CEL 静态判定、`topology_selector` 编译期解析）**尚未落地**，本稿对这些部分只做了「按提案 §1/§5 规则人工/脚本核对」，未经过真实编译器判定。
- IR 降维、计划对象生成、组件绑定（`pkg.*` 引用是否存在、类别是否匹配 E9001–E9004）**未验证**（草稿中的包名均为示意）。
- 卡④/⑤ 中标「存疑」的论文细节（迭代上限量级、具体超时/重试策略、基准清单、token 数字）一律按机制层表达，未把存疑数字写进预算 cap 的语义注释之外的地方。
- 环境备注（复现用）：校验用的两个临时工具都不在项目仓内——`/tmp/afb-harness/`（path 依赖 `af-dsl` 的小 harness）与 `/tmp/cel-check/`（cel-parser 0.10.1 检查器）；构建时须设 `TMPDIR` 到非 tmpfs 目录（本机 `/tmp` 为 tmpfs，链接阶段会 Bus error）。项目仓 `af-wt-phase2-dsl` 未被修改（`git status --porcelain` 为空，`Cargo.lock` mtime 仍为 15:54）。

---

## 6. 覆盖度小结

- ⑥(a) 8 条：8 条有落点（a6「代码内角色函数」为**部分落点**，实际依赖 b1/b2 两个逃逸面，见上表）。
- ⑥(b) 7 条：7 条全部以 `escape` 构造 + 七类词表记账（9 个逃逸节点，b1/b4 各两实例）。
- 结论与提案 B §7 L1595 的分级一致：**ADAS = 必须逃逸舱（大部）**；本草稿的贡献是把「MAS 搜索外壳」这一可表达部分做全（迭代、验证、反馈回灌、择优、留痕、人工终止、跨域选择器），把定义性机制全部推到 L4 记账面。
