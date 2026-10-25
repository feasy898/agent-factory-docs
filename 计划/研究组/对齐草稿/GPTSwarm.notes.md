# GPTSwarm → AFB 草稿翻译记录

- **目标**：GPTSwarm（Zhuge et al. 2024；agent = 可优化的计算图/蜂群）
- **草稿**：`计划/研究组/对齐草稿/GPTSwarm.yaml`
- **依据（本次实读）**：
  - 卡片：`计划/研究组/对齐机制卡/INDEX.md`（第 21 行 → 第 8 张卡 `GPTSwarm.md`）、`计划/研究组/对齐机制卡/GPTSwarm.md`（①–⑥ 全节）
  - 语法正本：`计划/研究组/DSL-语法提案-B.md` §1（七段字段表 + 六构造）、§2（正交性表）、§4 样例 2（MetaGPT）/样例 3（Debate）
  - 裁决：`计划/研究组/DSL-语法择优-裁决-20261024.md` §二-1（`meta.topology_selector` 编译期语义）、§二-2（`escape.kind` 七类词表）
  - 参照样例与实装：`af-wt-phase2-dsl/crates/af-dsl/testdata/sample1..6.yaml`（M1 golden）、`af-wt-phase2-dsl/crates/af-dsl/src/model.rs`（M1 serde AST）、`.../src/validate/refs.rs`、`.../src/validate/inv2.rs`、`.../src/shape.rs`、`.../src/envelope.rs`
- **结论**：草稿 0 个语法构造靠编造——所有落点都在提案 B §1 的既有字段面内；卡片 ⑥(b) 的 6 项定义性机制全部走 `escape` 构造 + 七类词表记账。

---

## 1. 机制 → 语法映射表（逐条对应卡 ⑥(a)，8/8 落位）

| # | 卡片 ⑥(a) 机制（原文要点） | AFB 落点 | 语法构造 | 草稿中的具体位置 |
|---|---|---|---|---|
| a1 | 「agent = 图」→ 顶层是 Graph/Topology 对象，边必须是一等声明式数据流依赖，不是隐式顺序列表 | 顶层 `nodes` + `edges` 两段；边 = 四字段类型化工件边 | `nodes`/`edges` | `search.loop.body.nodes`（13 个体节点）+ `search.loop.body.edges`（17 条体边）；根 `edges: []`（入口即唯一图） |
| a2 | ReAct 单节点自循环 → 带条件的自环节点 / DSL 原生 loop 结构 | 两层 `loop`：搜索外环 + 反思修订内环 | `loop`（体/max_iterations/carried/safety_points/exit_when/on_exhausted） | `search`（max_iterations 40、exit_when 预算 9/10）；`revise`（max_iterations 3、exit_when `attempt.passed == true`） |
| a3 | Plan→Execute→Review 流水线 → 三节点链式拓扑，工件交接 = 类型化消息端口 | `planner → dispatch → execute_map → reviewer` 链；工件走类型化端口（`envelope<plan>` 带血缘） | `emits`/`consumes`/`edges` + `envelope<T>` | `planner.emits {plan: "envelope<plan>", steps: "list<step_spec>"}`；边 `planner.plan → reviewer.plan` |
| a4 | Generate→Critique→Revise 反思 → 带反馈边的 cycle 拓扑 | `revise` 环体：`regenerate → critique → verdict_gate → regenerate`（回边 + 安全点门控） | `loop` + `route` + 反馈边 | `search.loop.body.nodes[revise]`；回边 `verdict_gate.opinion → regenerate.feedback`；`verdict_gate` 是 `kind: gate` 安全点 |
| a5 | 多智能体辩论/投票 → fan-out 并行分支 + fan-in 汇聚节点 | 扇出 = `map`（运行时定基数、实例间无横向边 → 互不可见）；扇入 = `aggregate` transform 的 `tally`/`select_best` | `map` + `ops`(tally/select_best) | `execute_map.map.over: dispatch.worklist`（`map` 体 3 节点、2 边）；`aggregate.ops` 两条 |
| a6 | 工具调用 → `tool` 节点类型 + 参数 schema + 失败返回类型 | `task` + `uses.tool` 绑定；请求/回执各一个登记类型 | `uses.tool` + `types` | `tool_exec`（`uses: {tool: pkg.swarmkit.tools@1}`），`action_request`（请求参数）/ `observation{ok,output}`（失败返回类型） |
| a7 | 记忆/scratchpad → 显式 context 节点，通过边接到需要它的节点 | 显式 `memory` 节点 + 边 `memory.mem → reviewer.mem`（非全局 store 隐式注入） | `nodes` + `edges` + `context.sections(from: edge)` | `memory`（task/cheap 模型，`emits {mem: step_result}`）；边 `memory.mem → reviewer.mem` |
| a8 | 条件路由 → 条件边（DSL 需支持按节点输出选择下游） | `route` 构造（有序 CEL 规则 + 必填 default），归一化为边守卫 | `route` | `reviewer.route`（不过→revise / default→aggregate）；`verdict_gate.route`（不过→regenerate / default→exit） |

> 说明：a1「边即上下文可见性」在 AFB 里由 INV-1（`context.sections` 声明式来源 + 无隐式注入）承载——草稿每个 LLM 节点只通过 `sections` 取上下文，未声明的入边端口一律不可见。卡片 ②「节点=无状态 callable」在 DSL 侧对应 `kind` + `uses` 绑定（`task`/`transform`/`gate`/`check`），节点体本身不落在语法层（见 b4）。

## 2. 机制 → 逃逸映射表（逐条对应卡 ⑥(b)，6/6 记账）

| # | 卡片 ⑥(b) 机制 | `escape` 节点 | `escape.kind`（七类词表） | `share_budget_pct` | 为什么 L0–L3 无落点（诚实理由） |
|---|---|---|---|---|---|
| b1 | 运行时生成/改写图结构：拓扑是优化变量本身，需动态图生成 + 图编辑原语 | `graph_edit` | `program_synthesis` | 10 | 静态 DSL 的 `nodes/edges` 是编译期常量；「产出一张新图」在语法层无表达位 → 由包内实现产出 `graph_spec` 并沿边回填到 `planner.spec`（近似） |
| b2 | 奖励驱动的优化控制环：RL/进化搜索（策略、采样、精英集、回退）整体在 DSL 之外 | `optimize` | `meta_loop` | 15 | 搜索策略/精英保留/回退是「图上的元算法」，无节点级或边级落点 → 以「调用外部优化器并把结果作为子图回填」接入 |
| b3 | 外部奖励/评分函数：任意回调挂载点 | `reward` | `llm_predicate` | 8 | 任务成功判据/测试通过率来自 DSL 外的评测器；CEL 保守子集零函数调用（提案 B §1.4），无法挂任意回调 → 逃逸 |
| b4 | 任意 Python 节点体：节点是任意 callable，DSL 只能声明结构不能声明函数体 | `py_node`（置于 `execute_map` 体内，代表候选图里的自定义节点） | `program_synthesis` | 6 | 语言核心零领域名词、无内联代码面（ADR-001 §3 Python 只进 L4）→ 节点体实现住包内 `impl_ref` |
| b5 | 执行期动态并发与拓扑重排：动态 fan-out、节点级超时取消、异步语义 | `dispatch` | `runtime_context_mutation` | 6 | `map` 只能表达静态扇出；超时取消/异步调度属运行期调度语义，语法层无字段 → 逃逸（**词法近似，见 §4-5**） |
| b6 | 图作为值：图可被嵌套、复用、作为另一张图的节点 | `graph_value` | `program_synthesis` | 4 | AFB 无「图」这个一等值类型（`types` 表只登记工件类型）→ 逃逸（**词法近似，见 §4-6**） |

**七类词表记账**（裁决 §二-2）：

| kind | 本配方节点数 | 占比（声明值合计） |
|---|---|---|
| `program_synthesis` | 3（graph_edit / py_node / graph_value） | 20% |
| `meta_loop` | 1（optimize） | 15% |
| `runtime_context_mutation` | 1（dispatch） | 6% |
| `llm_predicate` | 1（reward） | 8% |
| `dynamic_tool_registry` | 0 | — |
| `env_adapter` | 0 | — |
| `free_text_parser` | 0 | — |
| **合计** | **6 个 escape 节点** | **49%** |

> **健康度诚实标记**：合计 49% > ADR-001 §3 的 30% 警戒线。这不是配方写坏了，而是 GPTSwarm 的**定义性机制**（结构搜索 + 图编辑）本质在 DSL 外（提案 B §7 把它列为「冗长但可行」，残余 L4 = ⑥b 1/2）。编译期只验字段闭合（E2210），占比是运行期健康度指标。三个零记账类别（dynamic_tool_registry / env_adapter / free_text_parser）在本目标无对应机制，不硬凑。

## 3. 六节自检清单

| 自检项 | 结论 | 证据 |
|---|---|---|
| ① 信封 | ✅ `version: 1` 唯一顶层版本键；`meta` 必填六字段齐（name/graph_version/entry/input/output/intent + 可选 topology_selector） | M1 `envelope::check` 通过（E0001–E0004 无触发）；顶层键集 = `edges/meta/nodes/policies/stores/types/version`（与 golden 六样例一致） |
| ② 类型表 | ✅ `types` 登记 11 个类型；端口/store 元素类型全部为「类型名 / list< / envelope< / 内建 signal」四档；22 条边两端端口类型相等（含 map 自动包 `list<>` 的 from_body 推导） | M1 `refs::check` E2205/E2201/E2202 全部 0 违例；`meta.output {ref: decision, from: search}` 由 `search.emits.decision = {from_body: decide.decision}` 发射（E2202 通过） |
| ③ 单写者（INV-2） | ✅ `graph_archive` 声明写者 `search.graph_edit`，实际写者唯一且路径一致；map 体内（worker/tool_exec/py_node）零 store 写入；`search` 环的 `carried` 覆盖体内写的 `graph_archive` | M1 `inv2::check` E2311/E2312/E2211 全部 0 违例 |
| ④ 配额 | ✅ 全部 `context.sections` 段均带正数 `quota_tokens`（共 20 段；无 `policy: none` 变通） | M1 只解析不判正数（E2302 归 M2），逐段目视核对：template 400–600 / input 300 / edge 300–1500 / arg 300 |
| ⑤ 预算 | ✅ 4 条预算：`plan`（cents 5000）、`loop:search`（turns 2000）、`node:search.decide`（model_calls 40）、`map:search.execute_map`（tool_calls 500）；作用域全部可解析（嵌套体节点须写点号路径） | M1 `refs::check` E2207 0 违例；`stop` 2 条（轮数/预算）、`failures` 4 条（tool_error / schema_invalid / gate_refused / budget_exhausted，class 全在闭环词表内） |
| ⑥ 逃逸记账 | ✅ 6 个 escape 节点，四字段 `impl_ref/reason/owner/share_budget_pct` 齐全，`kind` 全部落在七类词表内；分类统计见 §2 | M1 `model::EscapeKind` 枚举值域校验通过（E1004 无触发） |

## 4. 语法不确定点（诚实列出，逐条给出我的处置与待裁决项）

1. **`escape.kind` 的权威性**：裁决 §二-2 说「作为 B `escape.kind` 的 v0.1 词表」，但提案 B §1.3 的 escape 仍是四字段（`impl_ref/reason/owner/share_budget_pct`，E2210「四字段缺一」）。M1 实装 `model.rs:540-547` 把 `kind` 收为**可选**且值域闭环（`EscapeKind` 七值 snake_case）。处置：草稿把 `kind` 全部显式填写（编译器两版都能过）；若正本坚持四字段，需 v0.1.1 加字段，否则 `kind` 会退化成未知字段（E1001）。
2. **`meta.topology_selector.use` 的词法**：裁决只说「已声明的版本化图/子图名」，未规定包引用形状。本文件内没有「候选图」的声明位（候选图是包产物），我用 `pkg.swarmkit.graph.<name>@<version>` 以与 `pkg.*` 保持一致 —— 但这使 `pkg.*` 出现在第 6 个位置（提案 B §4.7 检查 3 列的五处之外），**零领域名词自检的严格读法下这处需要裁决**。备选写法是裸图名 `plan_execute_review@2.1`。
3. **`topology_selector` 的语义边界**：裁决定义为编译期解析（不进运行时）。草稿据此把 GPTSwarm 的「优化器选出哪张候选图」落在选择器上：**优化器本体仍属 b2 逃逸**，选择器只承担「编译产物采用哪张图」这一位。两者不重叠。
4. **「控制节点入边仅表排序」**：样例 2 的 `planner → build` 边（`build` 无 `consumes`）确立了这条约定，但提案 B §1.2 未明文。草稿的 `reviewer.verdict → revise` 沿用同一约定（反馈值实际由 `revise.loop.args {feedback: "reviewer.verdict"}` 注入体内）。M1 对「目标节点无 consumes」的边跳过类型核对，因此该边不受 E2201 约束 —— 若评审要求控制节点也须声明端口类型，此边需改写。
5. **⑥b-5 → `runtime_context_mutation` 是词法近似**：七类词表没有「动态并发/异步调度」类。`runtime_context_mutation` 字面指「运行期上下文变更」，动态 fan-out/超时取消勉强落在「运行期改变执行结构/调度」一侧。备选 `dynamic_tool_registry`（运行时动态注册组件面）也讲得通，但语义更偏「工具注册」而非「调度」。**取前者，请评审复核**。
6. **⑥b-4 / ⑥b-6 同归 `program_synthesis` 是词法近似**：词表没有「任意节点体」和「图作为值」两类，二者都归到「结构/程序合成」一侧。这是七类词表在 GPTSwarm 上的固有缺口。
7. **⑥b-3 → `llm_predicate` 是词法近似**：词表没有「任意外部回调」类；外部评分函数在语义上最接近「判定逻辑外置」。若评审认为外部评测器应独立成类，需要 v0.1.2 扩词表。
8. **奖励平台期（plateau）早停未用 CEL 表达**：草稿把 `plateau` 建模进 `reward_value` 类型，但 CEL 位置词表（提案 B §1.4）没有「上一轮奖励」绑定，无法在 `exit_when` 里比较平台期。故早停只用「轮数上限 + 预算 9/10」，平台期判定留在 `optimize` 逃逸内部。这是**语义缺口**，已在草稿 intent 与本表登记，非语法缺口。
9. **`map` 体隐式形参 `item`**：`worker` 用 `arg.item`（样例 3 先例）；`py_node` 作为逃逸节点用 `consumes` 端口而非 `arg`。逃逸节点是否享有 map 体隐式形参，语法未定义 —— 草稿回避了该问题（不用 `item`）。
10. **escape 节点写 store**：`graph_edit`（逃逸节点）带 `writes: [graph_archive]`。语法未禁止，但 golden 样例无此先例（样例 4 的 `synth` 只 reads/emits）。若评审要求「store 写者必须是 DSL 内节点」，改为在 `graph_edit` 后加一个 `kind: transform` 归档节点（ops `project` → store），代价是多一个节点、少一处逃逸节点写状态。
11. **单写者写路径的跨体写法**：`store.writer: search.graph_edit`（点号路径穿 loop 体）沿用样例 3（`rounds.collector`）与样例 6（`explore.acquire.curator`）先例，M1 `resolve_root_path` 实跑通过。

## 5. 自检记录（本次实跑；命令与输出照抄）

**检查 1 · 任务指定的 YAML 解析自检**

```
$ cd /home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿
$ python3 -c "import yaml,sys; d=yaml.safe_load(open('GPTSwarm.yaml')); print('PARSE OK'); print('top-keys=', sorted(d.keys()))"
PARSE OK
top-keys= ['edges', 'meta', 'nodes', 'policies', 'stores', 'types', 'version']
```
→ 顶层键集与 golden sample1..6 完全一致（七段无漂移）。

**检查 2 · 真实 M1 前端（信封 + 七段解析 + 引用完整性 + INV-2）**——额外自检，非任务指定项

在 `/tmp/afb-draft-check`（**临时目录，非工作区仓库，未改任何现有文件**）建了一个以 path 依赖引用 `af-wt-phase2-dsl/crates/af-dsl` 的小程序，调用其公开 API `load_str` + `validate`：

```
$ cargo build --offline     # CARGO_TARGET_DIR 默认 /tmp（后续 CEL 检查改到 ~/.cache/afb-cel-target，因 /tmp tmpfs 配额不足）
$ ./target/debug/afb-draft-check "/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿/GPTSwarm.yaml"
PARSE: OK (envelope+shape passed)
VALIDATE: OK (0 violations)
```
同一 checker 跑 golden（非空跑对照）：
```
sample1.yaml: PARSE: OK (envelope+shape passed) VALIDATE: OK (0 violations)
sample2.yaml: PARSE: OK (envelope+shape passed) VALIDATE: OK (0 violations)
sample3.yaml: PARSE: OK (envelope+shape passed) VALIDATE: OK (0 violations)
sample4.yaml: PARSE: OK (envelope+shape passed) VALIDATE: OK (0 violations)
sample5.yaml: PARSE: OK (envelope+shape passed) VALIDATE: OK (0 violations)
sample6.yaml: PARSE: OK (envelope+shape passed) VALIDATE: OK (0 violations)
```

**检查 3 · CEL 保守子集（真实 cel-interpreter 0.10.0）**——额外自检

在 `/tmp/afb-cel-check`（临时目录）复刻提案 B §4.7 的三项判定（`Program::compile` / `references().functions() ⊆ 算子白名单` / `references().variables() ⊆ 位置词表` + 合成绑定上下文求值为布尔）：

```
$ /home/pan-ding/.cache/afb-cel-target/debug/afb-cel-check
PASS route/reviewer: reviewer.verdict.pass == false
PASS route/verdict_gate: verdict_gate.passed == false
PASS assert/verdict_gate: inputs.opinion.pass == true
PASS loop/revise.exit_when: attempt.passed == true
PASS loop/search.exit_when: budget.cents_spent >= budget.cents_cap * 9 / 10
PASS stop/iterations: steps.iterations >= 40
PASS stop/budget: budget.cents_spent >= budget.cents_cap
PASS selector/hard: input.mode == 'hard'
PASS selector/wide: input.mode == 'wide'
REJECTED neg/fn: non-whitelist functions ["size"]
REJECTED neg/root: unknown roots ["unknown_root"]
REJECTED neg/nonbool: steps.turns + 1 -> Int(3)
---- total=12 fail=0
```
9/9 正向表达式通过；3/3 反向对照按预期被拒（证明判定器非全数放行）。

**结构清点**（`python3` 统计草稿本身）
```
types: 11 | stores: 1 | nodes(含嵌套体): 19 | 根节点: ['search']
escape 节点: 6  [(dispatch,runtime_context_mutation,6) (py_node,program_synthesis,6)
                (reward,llm_predicate,8) (optimize,meta_loop,15)
                (graph_edit,program_synthesis,10) (graph_value,program_synthesis,4)]
escape pct 合计: 49 | 边总数: 22（根 0 + 搜索体 17 + map 体 2 + revise 体 3）
budgets: cost_cap/plan, search_turns/loop:search, decide_calls/node:search.decide,
         exec_calls/map:search.execute_map | stop: 2 | failures: 4
```

## 6. 未做 / 未验证项（如实登记）

- **未跑**：`af-compiler` stage 2/3/4（IR 降维、组件绑定、计划生成）——本仓库 af-dsl 处于 M1 模块期（`lib.rs:6-10` 自述），编译期后段不在可用范围。
- **未跑**：INV-1（上下文完整性）/ INV-3（生成器-验证器分离）/ INV-4（评估器外部化）的编译期判定 —— 归 M2/M3（裁决 §四-4 模块切分）。草稿按这些规则**手工对齐**（如 reviewer 的每个入边端口恰被一个 section 引用、`verdict_gate` 的生产者不是它自己、无 `eval_input` store），但**未被机器验证**。
- **未跑**：`route` 归一化（E2101/E2102/E2103）与 `topology_selector` 的编译期解析 —— 归 M4。草稿的两个 `route` 我按 §1.5 算法手算：规则互斥由构造保证、`default` 覆盖剩余、每个 `goto` 都是本节点的出边目标（`reviewer` 的两个出边 = revise/aggregate；`verdict_gate` 的出边 = regenerate，另走 `exit`）。
- **未跑**：CEL 在真实运行时绑定上下文中的求值（M4 的 CEL 通道 + af-graph `predicate.rs`）；本次只在合成上下文里验证了词法与类型。
- **未核实**：卡片本身标注的「论文超参存疑」（具体编辑轮数、基准清单、奖励是 task-level 还是 instance-level）—— 草稿中的 40 轮 / 5000 cents / 3 次修订等数字是**为把机制显式化而设的占位值**，不是论文数值，编译期不校验其与论文一致。
