# LangGraph-StateGraph → AFB 草稿 · 翻译记录

- 目标：LangGraph StateGraph（`计划/研究组/对齐机制卡/LangGraph-StateGraph.md`）
- 草稿：`计划/研究组/对齐草稿/LangGraph-StateGraph.yaml`
- 语法依据：`计划/研究组/DSL-语法提案-B.md`（AFB v0.1 正本）§1 七段/六构造、§2 正交性、§4 样例 2/3/5
- 裁决依据：`计划/研究组/DSL-语法择优-裁决-20261024.md` §二-1（`meta.topology_selector` 编译期语义）、§二-2（`escape.kind` 七类词表）
- 参照样例：`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/testdata/sample{1..6}.yaml`
  （任务书写的 `sample1-6.yaml` 不存在，实际是 6 个独立文件；样例 5 = `langgraph_subset`，与本目标同源）
- 计数：**可表达 13 条 / 逃逸 11 条**（口径见 §2、§3）
- 草稿形状（实跑统计）：types 9 · stores 4 · 根图 nodes 15（含 loop 体 8 + map 体 1）· 根图 edges 26 · `context.sections` 16 · `route` 3 处共 13 条规则 · escape 11 · budgets 4 · stop 2 · failures 6

---

## 1. 机制 → 语法映射表（卡 ⑥(a) 12 条，逐条对应）

| # | 卡 ⑥(a) 机制 | AFB 落点（草稿中的具体位置） | 备注 / 与提案 B 的对应 |
|---|---|---|---|
| a1 | 节点=函数（读 State 快照 → 返回状态增量） | `nodes[].kind: task/transform`，产出走 `emits` 端口（增量而非全量） | B §1.2 nodes 段；端口类型即增量契约 |
| a2 | 共享 State + reducer 合并（多写者同写如何合并） | `stores` 拆为 4 个**单写者**槽（`supervisor_turns` / `worker_turns` / `findings` / `long_term`）；reducer 的「写侧按 step 归并」改写为**读侧按 step 交错**（supervisor 的 context 中两个 `message_log` 段由内建规则交错） | B §1.2 内建合并规则（明写为 LangGraph `add_messages` 的对应物）+ 样例 5 互译表；**有意的语义改写，非一一对应** |
| a3 | 固定边 / START / END | `edges[]{from,output,to,input}`；START=`meta.entry`；END=`route` 的 `goto: exit` | B §1.2 edges 段（无 `when` 字段，路由只走 `route`） |
| a4 | 条件边（路由函数按 State 返回下一节点） | `route{default, rules[{when:CEL, goto}]}`：supervisor 的 `decision.done`、approve 的 `resume.approved`、runtime_probe 的 `note.kind` 共 3 处 13 条规则 | B §1.3 route + §1.5 单一归一化算法 |
| a5 | 图内循环（ReAct 形态的环） | `orchestrate.loop`：`max_iterations: 25`（= `recursion_limit`）、`exit_when`、`on_exhausted: fail`（= `GraphRecursionError`） | B §1.3 loop 构造 |
| a6 | 多智能体 handoff / supervisor | supervisor 节点（LLM 决策）+ `route` 路由 + `dispatch` 扇出到 worker；handoff=条件边返回下一节点 | a4/a7 的组合 |
| a7 | map-reduce fan-out（`Send`） | **静态子集**：`dispatch.map{over: input.worker_pool}` → `aggregate`（merge）→ `persist`（落 findings 槽） | 运行时动态基数=逃逸 `dynamic_dispatch`（见 §3） |
| a8 | 检查点 / 恢复 / time-travel | `edges[].checkpoint: true`（两条主干边）；恢复入口=循环的 `exit_when`/`on_exhausted` + human 节点的恢复值 | B §1.2 edges（唯一扩展字段，快照语义由 af-plan 承载）；**任意历史点 time-travel 无法声明 → 逃逸 `time_travel`** |
| a9 | `interrupt()` 人在回路 | `approve` 节点的 `human{station, role, quorum, resume.schema}`（类型化恢复值） | B §1.3 human（明写为 `interrupt(response_schema)` 的对应物）；**任意节点内挂起+副作用不回滚 → 逃逸 `suspend_resume`** |
| a10 | 子图嵌套（图中图） | `loop`/`map` 的**内联体**（`body: {nodes, edges}`），降维为版本化子图（B §3.2） | 草稿中 `orchestrate.loop.body` 即嵌入的主图；`dispatch.map.body` 即 worker 子图 |
| a11 | 记忆节点（读写 messages） | `compact`（transform：`reads: [findings]` → 写 `long_term` 槽）+ supervisor 的 `store` 段注入（`latest_k`） | 「记忆 = 状态通道 + 一个函数」的直译 |
| a12 | 预算控制 | `policies.budgets`：`rounds_cap`(turns, `loop:orchestrate`, 25) 对应 `recursion_limit`；`cost_cap`/`token_cap`/`tool_cap` 为 plan 级；另有 `policies.stop` 两条 CEL 兜底 | 卡 ④/⑤：框架无 token 计量 → token 预算只能近似为 plan 级上限 |

**额外可表达 1 条（来自 ⑥(b)）**：

| # | 机制 | AFB 落点 |
|---|---|---|
| b7 | 节点级重试/退避与错误分类 | `policies.failures[]{class, retry{max,backoff_ms}, route, feedback}`：6 个语义类（`transport_transient`/`environment_failure`/`schema_invalid`/`timeout`/`gate_refused`/`budget_exhausted`），分类维度由异常类型改为语义类别 |

> **可表达合计 = 12（⑥a 全覆盖）+ 1（b7）= 13**

---

## 2. 逃逸清单（卡 ⑥(b)，11 条需要逃逸舱）

七类词表取自裁决 §二-2：`dynamic_tool_registry / program_synthesis / meta_loop / runtime_context_mutation / env_adapter / free_text_parser / llm_predicate`。

| 卡 ⑥(b) | 机制 | 草稿中的逃逸节点 | `escape.kind` | 理由（`reason` 摘要） |
|---|---|---|---|---|
| b1 | 运行时动态改写图结构 | `runtime_rewrite` | `meta_loop` | AFB 拓扑必须静态声明，改图只能退化为状态驱动路由 |
| b2 | 动态扇出数量（`Send`） | `dynamic_dispatch` | `meta_loop` | 运行时生成 N 个并行实例，超出静态节点/边数量 |
| b3 | 条件边运行时返回多目标 / 依赖运行期数据决定拓扑 | `llm_route` | `llm_predicate` | 以 LLM 自由文本决定下一节点；AFB `route` 只能是静态可校验 CEL |
| b4 | 真正的 `interrupt` 挂起-恢复（任意节点内挂起、副作用不回滚） | `suspend_resume` | `runtime_context_mutation` | 过程语义无法由「边界处暂停」表达 |
| b5 | 节点内任意 Python 副作用与状态事务 | `side_effects` | `env_adapter` | 框架不提供节点级事务/回滚，DSL 承诺事务性即越界 |
| b6 | 跨线程长期记忆（Store）与任意键值访问 | `thread_store` | `env_adapter` | 跨执行线动态键存取不在单图状态内（静态槽只覆盖类型化部分） |
| b8 | 节点内并发调用 / 流式返回 / async 取消 | `stream_exec` | `env_adapter` | AFB 执行模型为 super-step 级同步，节点内并发需宿主语言支持 |
| b9 | 超级步内并行节点的写冲突消解 | `conflict_merge` | `runtime_context_mutation` | 多写者非确定性合并顺序；AFB 以 INV-2 编译期拒绝，合并语义下沉到逃逸实现 |
| b10 | 子图与父图的状态可见性/隔离边界 | `visibility_scope` | `runtime_context_mutation` | 需通道级可见性字段，AFB 作用域只有「体外声明 + carried 覆盖」 |
| b11 | 时间旅行（回到任意历史检查点并分支） | `time_travel` | `runtime_context_mutation` | 属运行历史操作而非图结构声明 |
| b12 | 跨图/跨运行的编排与调度器语义 | `cross_graph` | `meta_loop` | 超出单图执行模型；`meta.topology_selector` 只做编译期选图 |

**逃逸合计 = 11**，分类分布：`meta_loop` 3 / `runtime_context_mutation` 4 / `env_adapter` 3 / `llm_predicate` 1。
`share_budget_pct` 逐条 10–20（合计 150%），每条 ≤100%，无 >30% 的单条逃逸（ADR-001 §3 警戒线）。

**未用到的三类词表**：`dynamic_tool_registry`（LangGraph 无运行时工具注册表）、`program_synthesis`（无代码合成）、`free_text_parser`（自由文本解析在本目标归入 `llm_predicate` 的路由语义）。

---

## 3. 语法不确定点（诚实列出，请编译器裁定）

1. **端口级多生产者（最需要裁定的一条）**：`hazard_log` 的输入端口 `note` 由 **12 条边**填充（runtime_probe 默认分支 1 条 + 11 条逃逸处理器各 1 条）。AFB 的单写者纪律（INV-2）只约束 **store**，未见「一个输入端口一个生产者」的规则。若 M4 收紧为单生产者，需改为：11 条逃逸处理器各写各的 store（11 个 store），台账节点用 `reads` + `merge` 汇聚。当前草稿选择前者，因为后者的 11 个 store 会淹没图结构。
2. **ops「末端落点二选一」的解读**：本人采用的解读是——每个 op 的 `into` 只落一次；被后续 op 消费的**中间量不得同时声明为 emits 端口**；一条 op 链**恰好一个末端落点**。据此把 `aggregate`/`persist`/`log_turns`/`compact` 拆成 4 个节点（每个 1–3 个 op）。若编译器允许「同一 op 同时落 emits 端口与 store」，这 4 个节点可合并为 1 个（草稿更短）。
3. **`runtime_probe` 是翻译脚手架，不是 LangGraph 机制**：LangGraph 没有「探针」节点。引入它是为了给 11 项运行时语义一个**静态声明入口**（路由 + 逃逸记账），否则这些逃逸节点会成为孤立节点（E2006）。评审若不接受该脚手架，替代方案是把逃逸声明直接挂到语义对应的节点上（如 `dynamic_dispatch` 挂到 `dispatch`），但那样逃逸节点会与业务节点耦合、`kind` 组合合法性存疑。
4. **`meta.topology_selector` 本草稿未使用**：裁决 §二-1 定义其语义为**编译期**在候选图/子图间择一（解析后是单一确定图）。卡 ⑥b-1 的需求是**运行期改写同一张图**，与该构造不同轴，混用会误述语义。故本目标用 `route`（状态驱动路由）+ `escape` 表达改图需求。若评审认为「按输入形状在两种编排拓扑间择一」应显式建模，则应新增候选图并在本文件声明 selector——这属于超出现有机制卡的新增机制，未擅自添加。
5. **`escape.kind` 词表粒度粗**：4 项运行时语义（并行写冲突 / 子图可见性 / 时间旅行 / 任意挂起）没有精确对应类，`runtime_context_mutation` 是就近归类（其中「任意挂起 + 外部输入注入」实为上下文在运行中被改写）。词表若要覆盖 LangGraph 全集，可能需要新增类别——这属 v0.2 语法扩展范畴。
6. **`interrupt` 的语义只到「边界暂停」**：`human.resume.schema` 覆盖了「类型化恢复值」，但「从挂起点续跑且之前的副作用不自动回滚」是过程语义，AFB 无字段承载（已由 `suspend_resume` 逃逸记账，但逃逸舱是 L4 实现位、不是语法语义）。
7. **checkpointer 的粒度近似**：LangGraph 默认每个 super-step 落盘；AFB 只有**边级** `checkpoint: true` 声明位，草稿只在两条主干边标注，无法表达「每步落盘」。
8. **reducer 的写侧归并 → 读侧交错是有意改写**（承 B §1.2 内建规则与样例 5 互译表），不是 LangGraph reducer 的一一对应；代价是「多写者同时写同一通道的合并顺序」语义在 AFB 中不存在（转由 `conflict_merge` 逃逸 + INV-2 编译期拒绝共同承担）。
9. **`thread_id` / 会话标识无语法落点**：AFB 无 thread 概念；已并入 `thread_store` 逃逸的 reason，但严格说它不是「可被 L4 实现补齐」的缺口，而是语法层缺失——此处按逃逸记账是**保守近似**，标注为不确定。
10. **未使用 `envelope<T>`**：该类型是提案 B 为 MetaGPT 式血缘（`cause_by`）引入的，LangGraph 无对应机制，故不用。
11. **`store` 的 `type` 词表只用到 3 个**（`message_log` / `collection`）：LangGraph 的 State 通道无「文档 / 向量索引」的对等物；`long_term` 用 `collection` 承载长期记忆，属近似。

---

## 4. 自检记录（本次实跑，命令与输出）

所有命令均在本次会话内执行；临时校验工具建在 `/tmp` 与 `~/.cache` 下，**未修改工作区任何既有文件**（含 af-dsl crate）。

| # | 检查 | 命令 | 结果 |
|---|---|---|---|
| 1 | YAML 可解析（任务书指定） | `python3 -c "import yaml; yaml.safe_load(open('.../LangGraph-StateGraph.yaml'))"` | `YAML-PARSE-OK` |
| 2 | af-dsl M1 前端（信封 + 七段解析 + 引用闭包 + INV-2） | 用 `/tmp/afb-draft-check`（path 依赖 `/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl`，调用 `load_str` + `validate`）跑本文件 | `LOAD-OK name=langgraph_stategraph entry=orchestrate` / `VALIDATE-OK 0 violations` |
| 3 | CEL 保守子集（真实 cel-interpreter 0.10.0 沙盒） | `/home/pan-ding/.cache/afb-cel-check/target/debug/afb-cel-check /tmp/exprs_lg.txt`（16 条 when/assert/exit_when 全部抽出） | `---- total=16 fail=0`；每条均过「可解析 / 函数仅白名单算子 / 根绑定在位置词表内 / 求值为布尔」 |
| 4 | M2–M4 结构规则自检（提案 B §5 尚未落地，手写复核） | `python3 /home/pan-ding/.cache/selfcheck_lg.py <yaml>` | `SELFCHECK-OK 0 violations`；`escape 节点数=11 分类分布={'meta_loop': 3, 'runtime_context_mutation': 4, 'env_adapter': 3, 'llm_predicate': 1}` |

### 六节自检清单（逐项）

| 节 | 检查项 | 结论 |
|---|---|---|
| 信封 | `version: 1` 顶层唯一信封键；`meta` 六字段齐全（name/graph_version/entry/input/output/intent）；全文无未知键 | ✅ af-dsl M1 信封层通过（`deny_unknown_fields`） |
| 类型表 | `types` 9 条；全部端口类型与 store 元素类型均已登记（`list<finding>`/`hazard_report`/`envelope` 未用）；`meta.input`=lg_input、`meta.output.from`=finalize 且 finalize 确实发射 `answer` | ✅ E2205 / E2202 通过；自检 T 项 0 违例 |
| 单写者 | 4 个 store 各恰 1 写者（`orchestrate.supervisor` / `orchestrate.log_turns` / `orchestrate.persist` / `orchestrate.compact`）；map 体节点（worker）不写体外槽；`carried` 覆盖体内写入的 4 个 store | ✅ INV-2 通过（E2311/E2312/E2211 均未触发） |
| 配额 | 16 条 `context.sections` 的 `quota_tokens` 全为正；LLM 节点（supervisor/worker/runtime_probe/finalize）均无 `reads`；每个入边端口恰被 1 个 `edge` 段引用 | ✅ 自检 I 项 0 违例（E2301/E2302/E2303/E2304 未触发） |
| 预算 | `budgets` 4 条 cap>0、scope 合法（`loop:orchestrate` 指向真实 loop 构造）；`recursion_limit` 的硬上限=loop `max_iterations: 25` + `rounds_cap`；`stop` 2 条 CEL | ✅ E2207 通过；自检 R/S 项 0 违例 |
| 逃逸记账 | 11 条 `escape`：四字段齐全 + `kind` ∈ 七类词表 + `share_budget_pct` ∈ (0,100]；分类分布可统计 | ✅ 自检 X 项 0 违例 |

### 未跑项（如实）

- **编译器红绿测试**：af-dsl 的 M2（context.sections+INV-1）、M3（INV-3/INV-4）、M4（route 归一化 + CEL 静态判定 + topology_selector）尚未落地，本次用自写脚本 + 真实 cel-interpreter 沙盒**代偿**，不等于官方校验器通过。
- **IR 降维快照 / 计划对象快照**：未跑（`af-compiler` 未实现）。
- **装载期组件解析（E9001–E9004）**：未跑；草稿中的 `pkg.langgraph.*` / `route.*` 引用均为**占位包名**，未在组件注册表中核对存在性。
- **INV-3（自验证）/ INV-4（评估输入可见性）**：M1 未实现，草稿中 `verify` 与其生产者 `aggregate` 为不同节点、`eval_input` 未使用，但未由校验器实证。
