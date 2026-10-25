# Agent 定义 DSL 语法规范 v0.1 · 提案 A（对齐覆盖度优先）

> 身份：第二阶段 DSL-Compiler 团队 · 语法代理 A（竞争提案，与提案 B 按「对齐覆盖度 + 编译复杂度 + DX」择优合入）。
> 日期：2026-10-24。语言代号：**AFD**（Agent Flow Definition）。
> 输入依据：15 张对齐机制卡（`计划/研究组/对齐机制卡/`）、DSL-G0 三框架表达力报告（langgraph/autogen/crewai）、af 三 crate schema（af-graph `model.rs`/`validate.rs`、af-harness `spec.rs`、af-dspy-ir `model.rs`）、落地契约 v0、ADR-001/002/007。
> 本文件为任务书授权的唯一写入文件；未修改任何现有代码。

---

## 0. 引言：五层模型与本提案的设计立场

使命指令模型把 agent 定义语言切为五层：

| 层 | 名称 | 内容 |
|---|---|---|
| **L0** | 不变量层 | 四条硬不变量，编译期可判定：**上下文完整性**（生成节点看到的每一段上下文都有声明来源）、**写入串行化**（每个状态槽任一时刻至多一个写者）、**生成器-验证器分离**（验证面不得由被验证的生成者兼任）、**评估器外部化**（打分/裁决逻辑在候选执行体之外，评估输入对候选不可读） |
| **L1** | 契约层 | 类型化工件契约、typed handoff、预算（步数/token/费用/时钟）、停止条件、失败分类与处置 |
| **L2** | 拓扑层 | 图/流水线/环/map 扇出/**拓扑选择器**；选择器必须有 fallback，规范 fallback = **集中式编排 + 验证瓶颈**（一个编排路由点 + 一个 check/evaluator 汇聚收束） |
| **L3** | 实现层 | 组件与领域配置包绑定（模型路由/推理循环/记忆/工具/压缩组件），执行面落地 |
| **L4** | 逃逸层 | 显式逃逸舱（escape_hatches），必须声明 + 记账，健康度占比 >30% 警戒 |

DSL-G0 三报告的结论是三框架 12 格中 0 格无条件完整表达，缺口集中在 L0/L1：写权限（LangGraph G4）、节点间校验（G3）、token/费用预算与声明式停止（G1）、typed handoff 信封（G7）、失败分类（G5）、上下文组装策略（G6）、元循环载体（AutoGen 缺口 1）、循环/反馈边（CrewAI 缺口 2）。**本提案的立场是对齐覆盖度优先**：15 个对齐目标（单体 harness 与多 agent 编排论文/框架）的机制都要能自然、可读地写成 AFD，宁可语法面稍大（15 个顶层段、7 类节点、9 类上下文策略）；每引入一个面，都在 §8 交代代价。硬边界不退：

1. **YAML 主干 + CEL 谓词**（ADR-001）：一切运行时谓词（停止/门控/选择器规则/边守卫）是 CEL 表达式，编译期 compile、无副作用；Python 不进 L0–L3 任何语法层。
2. **语言核心零领域名词**：核心语法段不出现 git/终端/代码/视频等领域词；领域具体性全部在 `packages` 配置包引用（工具/模板/判定单元的 `pkg.*` 名字是包产物，不是核心词表）。机器检查口径：删掉全部 `packages` 引用后，核心 golden 样例自洽可编译。
3. **类型化受限**：无图灵完备、无副作用、可静态校验。CEL 采用**保守子集纪律**——谓词只做比较、布尔组合、整数算术与 `in` 字面量列表成员判断，**零方法调用**；一切聚合（计数、份额、最高分）由 transform 算子预计算成整型绑定（如 `tally.top_share_milli`）后再进谓词。这让谓词可静态检查、跨引擎可移植。
4. **拒绝式版本信封**：`version: 1` 顶层键（承 af-dspy-ir `Program.version` 与 AgentSpec `{"v":1,...}` 纪律）；缺键、非整数、非 1 → 整份拒绝，不解析 body。全文所有结构 `deny_unknown_fields`。

---

## 1. 语法总览

### 1.1 顶层结构树（15 段）

```
AFD 文档（YAML，拒绝式信封）
├── version: 1            # 信封版本；非 1 整份拒绝（E0003）
├── meta                  # 名字/展示名/意图/标签：身份、检索与审计入口
├── packages              # 领域配置包引用表：领域名词的唯一入口（L3）
├── types                 # 工件与信封 schema 登记：跨节点契约的类型词典（L1）
├── interface             # 整图输入/输出契约：外部世界的类型化边界（L1）
├── entry                 # 入口节点 id（承 af-graph GraphTemplate.entry）
├── stores                # 状态槽：类型 + 单写者 + 读者 + 生命周期 + 保留策略（L0/L1）
├── subgraphs             # 版本化子图：复用单元，loop/map 的体（L2）
├── nodes                 # 节点：kind + 组件绑定 + 上下文视图 + 写端口 + loop/map/human 构造（L0–L3）
├── edges                 # 类型化工件边：from.output→to.input + CEL 守卫 + 信封 + 检查点（L1/L2）
├── selectors             # 拓扑选择器：CEL 规则路由，default 必填（L2）
├── budgets               # 多维预算：维度 × 作用域 × 上限（L1）
├── failures              # 失败分类账：类别 → 重试/路由/反馈/降级/终态（L1）
├── stop                  # 停止条件：CEL 谓词 → outcome（L1）
└── escape_hatches        # L4 逃逸舱：显式声明 + 记账字段（L4）
```

### 1.2 各段字段速览

**meta**：`name`（ref 名，同 af-harness `is_ref_name` 纪律：字母数字 `_.:-`，≤128）、`display`、`intent`、`labels[]`。

**packages**：`- ref: <包名>@<版本>`。包内提供：工具 schema、提示模板、判定单元（judge/assess）、检索/摘要组件、逃逸舱实现。核心只存引用，装载期按落地契约 §2.2 校验（引用缺失/版本不符/digest 不匹配 → 拒绝启动）。

**types**：`- name / schema`（JSON Schema 对象）。信封泛型内建 `envelope<T>` = `{payload: T, from_node: string, artifact_type: string, step: integer}`（typed handoff 的血缘位，对应 MetaGPT `cause_by` 与 LangGraph G7 缺口）。

**interface**：`input`（JSON Schema 或 `ref`）、`output`（`ref` 类型 + `from` 发射节点 + `list: true` 可选）。输出类型在全图中必须恰有一个发射者，否则需 `from` 点名（E2202）。

**stores**（每槽）：

| 字段 | 说明 |
|---|---|
| `name` | 槽名（doc 唯一） |
| `type` | `message_log` \| `document` \| `collection` \| `kv` \| `vector_index` |
| `item`/`value` | collection/kv/vector_index 的元素类型 ref |
| `writer` | **唯一写者节点 id**（INV-2 判定对象） |
| `readers[]` | 显式读者集合（INV-4 读权限对象）；缺省=空 |
| `lifecycle` | `run`（本计划执行）\| `iteration`（循环每迭代重建）\| `persistent`（跨执行持久，外部 state provider） |
| `retention` | `{max_items}` \| `{max_bytes}` \| `{policy: rolling_window, max_items, keep_system?}`（有界性承 af-graph `CarriedState.is_bounded` 纪律） |

**subgraphs**（承 af-graph `SubGraph`，扩展两个可选字段）：`name / version / entry / nodes / edges` + **`inputs: [名]`**（体形参）+ **`outputs: {端口: 类型}`**（体输出契约；支持 `{from_arg: <名>}` 直通端口）。版本缺失 = 未审定草稿，被 map/loop 引用时拒绝（承 af-graph E2007 思路）。

**nodes**（每节点）：

| 字段 | 说明 |
|---|---|
| `id` | doc 唯一（含子图内节点——选择器/安全点跨层引用以 doc 唯一 id 寻址） |
| `kind` | `agent` \| `tool` \| `check` \| `gate` \| `transform` \| `evaluator` \| `human` \| `loop` \| `map`（开放 String，承 af-graph 开放 kind；**验证面** = check/gate/human/evaluator，L0 判定用） |
| `uses` | 组件绑定：`model: <route ref>`、`tools: [pkg.*]`、`unit: <pkg 判定单元>`、`tool: <pkg 工具>`、`memory: [...]`（L3） |
| `emits` | `{端口: 类型}`——输出端口契约（L1） |
| `writes[]` | 写端口：本节点可写的 store 名（INV-2 判定对象） |
| `reads[]` | 非生成节点的直读 store 名（transform/check/evaluator 专用；**agent 节点只能经 context 访问 store**——INV-1） |
| `consumes` | `{端口: 类型}`（可省，由入边推导；显式声明时作编译核对） |
| `context` | agent 节点的上下文组装声明（下表）+ `merge: {by: step_order}`（读侧合并声明） |
| `human` | 承 af-graph `HumanSpec`：`station/role/quorum` + **`resume: {schema}`**（类型化恢复值，LangGraph `interrupt(response_schema)` 对应物） |
| `loop` | 受控循环构造（下） |
| `map` | 扇出构造（下） |

**context.sections[]**（顺序即拼接顺序；每段 `quota_tokens` 必填——上下文完整性 = 来源 + 策略 + 配额三要素齐备）：

| 来源 `from` | 字段 | 策略 `policy` |
|---|---|---|
| `template` | `template_ref`（包内模板）、`vars` | — |
| `input` | `fields[]`（整图输入投影） | `project` |
| `arg` | `name`（loop args / map 隐式 `item`） | `project` |
| `edge` | `port`（入边载荷）、`optional: true` | `project` |
| `store` | `store` | `full` \| `latest_k{k}` \| `retrieve{component, k}` \| `summarize{component}` \| `none`（声明"不进上下文、仅经工具可见"） |

**edges**（每条）：`from / output / to / input`（承 af-graph `Edge` 四字段，工件引用语义）+ 可选 `when`（CEL 守卫，绑定见 §1.3）、`handoff: envelope`（载荷包 `envelope<T>`）、`checkpoint: true`（本边之后落状态快照，LangGraph checkpointer 的声明位）、`signal: true`（无载荷纯排序/触发边，output/input 写 `signal`）。

**selectors**（每选择器）：`at`（路由依据节点）、`rules[]`（`when` CEL + `goto` 节点 id 或 `exit`，按序首中）、**`default`（必填）**。规范推荐 default 指向集中编排/裁决节点——使命指令的 fallback=集中式编排+验证瓶颈（缺 default → E2101）。

**nodes[].loop**（承 af-graph `ControlledLoop`，三个扩展）：

| 字段 | 说明 |
|---|---|
| `body` | 体子图名（必须已声明且版本化） |
| `max_iterations` | 迭代上限（>0，防活锁） |
| `carried[]` | 跨迭代携带 store + 上界（`max_items`/`max_bytes` 至少其一——承 `CarriedState.is_bounded`；扩展：多槽列表） |
| `safety_points[]` | `{node, kind}`，kind ∈ check/gate/human/evaluator（承 `SafetyPointKind` + 扩 evaluator；缺安全点 = 拒绝编译，承 E2004） |
| `args` **(新)** | 体形参绑定 `{形参: 节点.端口 | input.字段}`（隐式边，计 DAG 依赖） |
| `exit_when` **(新)** | CEL 谓词，真则带 outcome 退出 |
| `on_exhausted` **(新)** | `continue` \| `fail` \| `keep_best`（迭代耗尽策略） |

循环节点 `emits` 可用 `{from_body: 体节点.端口}` 转发体输出；自带 `signal` 端口 `finished`。

**nodes[].map**（承 af-graph `MapSpec` 原样）：`body`（版本化子图）、`over`（`节点.端口` 或 `input.字段`，必须解析为集合类型，否则 E2102）、`max_fanout`。map 体子图以隐式形参 `item` 收到元素；map 节点输出端口 `items: list<T>`。

**budgets**（每条）：`id / dimension / scope / cap`。dimension ∈ `turns | model_calls | tokens_in | tokens_out | tokens_total | tool_calls | cents | clock_ms`；scope ∈ `plan | node:<id> | loop:<id>`；cap 必须 >0（E2207）。

**failures**（每条，失败分类账）：

```yaml
- class: <类别>                  # 闭环词表，见下
  retry: { max: <u32>, backoff_ms: <u32> }
  route: <node_id | same_node | next_iteration>
  feedback: <error_observation | format_reminder | none>
  fallback_route: <node_id>      # retry 耗尽后的降级路径
  terminal: true | false
  outcome: <completed | failed | escalated_human>
```

class 闭环词表：`transport_transient`（F1 供给瞬态）/ `environment_failure`（F2 环境失败）/ `schema_invalid` / `tool_error` / `timeout` / `gate_refused` / `budget_exhausted` / `policy_stopped` / `unauthorized`（后三者对齐 af-harness `RunStatus` 终态轴；整体对齐落地契约 §6.2 四分类）。未知类或路由目标不存在 → E2204。

**stop**（每条）：`when`（CEL）→ `outcome`（completed/failed/escalated_human）。编译目标：优先映射 af-harness `StopCondition` 快路径（完成信号词/无工具轮上限），其余编译为 CEL 谓词（`Predicate::compile`，af-graph `predicate.rs` 通道）。

**escape_hatches**（每条，L4）：`id / kind / reason / owner / share_budget_pct / impl_ref`。kind 闭环词表首版：`dynamic_tool_registry`（运行时工具注册，ReAct 卡 b-1）/ `program_synthesis`（图/代码合成，GPTSwarm/AFlow 卡 b-1）/ `meta_loop`（搜索/进化元循环）/ `runtime_context_mutation`（运行时上下文自改写，MemGPT 卡 b-1/b-5）/ `env_adapter`（有状态环境契约，ReAct/SWE 卡）/ `free_text_parser`（自由文本双向解析，ReAct 卡 b-2）/ `llm_predicate`（语义判定谓词）。缺任一记账字段 → E2503；`share_budget_pct` 是声明阈值，实占在健康度报表核对（>30% 警戒是运行期指标，编译期只验字段完整）。

**transform 节点**（零状态数据算子，GPTSwarm "节点=无状态 callable" 的声明式对应）：`ops[]` 闭环词表 = `project | merge | slice | anonymize | shuffle_seeded | truncate | tally | select_best`，`args` 传参（`shuffle_seeded` 必须带 `seed_ref`——可复现纪律；无种子随机不在核心）。

### 1.3 CEL 绑定词汇表（编译期核对，未知名 → E2203）

绑定以结构化值注入（点号 = CEL 成员选择），谓词零方法调用：

| 绑定 | 字段 |
|---|---|
| `steps` | `turns`、`tool_free`、`tool_calls_last_turn`、`iterations` |
| `budget` | `<dimension>_spent` / `<dimension>_cap`（如 `cents_spent`/`cents_cap`） |
| `last_tool` | `name`、`first_line`、`ok` |
| `last_message` | `has_tool_calls` |
| `attempt` | `verdict.pass`、`score_milli`、`gate_passed`、`acquired`（体最近一次验证/评分输出） |
| `resume` | human 节点 `resume.schema` 展开（如 `resume.approved`） |
| `input` | 整图输入对象 |
| `tally` / `<节点id>` | 具名 transform 的预计算聚合与选择器 `at` 节点的输出字段（如 `vote.top_count`） |
| `inputs` | gate `assert` 内的命名入边（如 `inputs.report.ok`） |

---

## 2. 五层映射表

| 语法段 / 字段 | 层 | 理由 |
|---|---|---|
| `version`、`meta` | 信封/元（层外） | 拒绝式信封纪律（ADR-001） |
| `packages` | **L3** | 组件与领域包绑定是唯一实现层入口 |
| `types`、`interface`、`edges`（类型核对）、`nodes.emits/consumes` | **L1** | 类型化工件契约；每条边都是一次编译期类型核对 + 运行期 schema 校验（补 LangGraph G3） |
| `stores.type/lifecycle/retention` | **L1** | 状态的类型与资源契约（有界性） |
| `stores.writer/readers`、`nodes.writes/reads` | **L0** | 写入串行化 + 读权限（INV-2/INV-4 判定对象） |
| `nodes.context`（sections+quota） | **L0+L1** | 上下文完整性（INV-1）+ 组装策略契约（补 G6） |
| 验证面 kind（check/gate/human/evaluator）+ `loop.safety_points` | **L0** | 生成器-验证器分离（INV-3） |
| `nodes.loop/map/human`、`subgraphs`、`entry`、`edges`（拓扑）、`selectors` | **L2** | 拓扑层；选择器 default = 集中编排 + 验证瓶颈 fallback |
| `budgets`、`failures`、`stop`、`edges.when/checkpoint` | **L1**（when 兼 L2） | 预算/失败分类/停止三契约（补 G1/G5） |
| `escape_hatches` | **L4** | 唯一逃逸面，显式记账 |
| （IR / 可执行计划对象） | L3 落点 | 编译产物，非语法（落地契约 §7） |

---

## 3. 对齐覆盖对照（15 目标 → 语法要素）

| # | 目标 | 核心机制 → AFD 要素 | 残余逃逸（L4） |
|---|---|---|---|
| 1 | ReAct | 单 agent 节点内运行时环 + `writes` 串行落账 + `stop` CEL + `budgets` 三重 | 动态动作词表、自由文本切分、组合式生成 |
| 2 | Reflexion | 外层 `loop`（体=actor+check+reflector）+ `reflections` 槽单写者 + `retrieve` 注入 + `lifecycle: iteration/run` 分层 | 反思空值守卫、成功后反思变体 |
| 3 | Voyager | 嵌套 `loop`（课程环包习得环）+ `persistent` 技能库 + gate 守门入库 + `retrieve` | 沙箱执行任意代码、软性终止判据 |
| 4 | SWE-agent | `uses.tools`（包内 ACI 面）+ `latest_k`/`tool_output_policy` 窗口化 + `submit` CEL 停止 + 四维预算 + `schema_invalid` 格式重述回灌 | 行级编辑原语、依赖准备脚本、人工介入通道 |
| 5 | MemGPT | 分层 `context.sections`（固定配额）+ 记忆工具绑 `writes`（自编辑=串行写）+ `policy: none`（外部层仅工具可见）+ `tool_calls` 步内上限 + `steps.tool_calls_last_turn == 0` 数值化停 | 语义驱逐分页、异步抢占中断 |
| 6 | MetaGPT | typed 端口 + `handoff: envelope` 血缘 + `repo` 单写者 + QA 回环=受控循环（安全点=evaluator） | `_watch` 订阅触发、动态收件人 |
| 7 | CAMEL | 双 agent 节点 + 模板 `vars` 角色化 + 受控对话环 | —（近乎全覆盖） |
| 8 | GPTSwarm | 显式边=可见性 + 并行分支互不可见 + `transform` 算子 + `selectors` 条件路由 | 图编辑算子 + 奖励搜索（meta_loop） |
| 9 | Agensh/DeLM（低置信卡） | `handoff` 边 + swarm 型图（与 8 同面） | 待补卡后复核 |
| 10 | Multi-Agent Debate | `map` 并行互不可见 + `collector` 黑板唯一写者（**多写者→串行化**）+ `shuffle_seeded` 匿名化 + `selectors` 裁决 fallback + `tally` 早停 | 语义共识判定、运行时改拓扑 |
| 11 | AFlow | 搜索元循环=受控 `loop` + 逃逸 `program_synthesis` + `evaluator` 外部评估 + `experience` 有界携带 + **读权限隔离**（分数/答案对候选不可读） | MCTS 本体、遥测计分 |
| 12 | ADAS | 同 11 面（meta_loop + 版本化子图回填） | 元智能体任意合成 |
| 13 | LangGraph | 通道单写化 + `merge: {by: step_order}` 读合并（替代 reducer）+ `exit_when`（条件边）+ `max_iterations`（recursion_limit）+ `checkpoint: true` + `human.resume`（interrupt） | Send 动态基数、时间旅行 |
| 14 | AutoGen | `stop`/`failures`（termination 家族 `|`/`&` 组合→CEL `||`/`&&`）+ `selectors`（Selector 拓扑）+ 环形/层级图 | selector_func 闭包、ledger 自然语言演化 |
| 15 | CrewAI | 顺序流水线 + `context.sections.from: edge`（context 拉取的类型化版）+ `human`（human_input）+ guardrail=check 节点 | Manager 动态委派、RPM 限流 |

---

## 4. 十个完整样例

通用纪律：工具/模板/判定单元一律 `pkg.<包>.<名>` 引用（领域名词全部住在 `packages`）；CEL 全部为保守子集（比较 + 布尔 + 整数算术 + `in` 字面量）。全部样例已过 YAML 解析自检（§4.11）。

### 4.1 样例 1 · ReAct 单体循环

```yaml
version: 1
meta:
  name: react_mono
  display: "对齐样例 1 · ReAct 单体循环"
  intent: "单 agent 节点：工具回灌经写端口串行落账；语义终止 + 三重预算"

packages:
  - ref: hopqa@1.0.0          # 提供 search/lookup 工具 schema 与少样本模板

types:
  - name: answer
    schema:
      type: object
      required: [final, supports]
      properties:
        final: { type: string }
        supports: { type: array, items: { type: string } }

interface:
  input:
    type: object
    required: [question]
    properties: { question: { type: string } }
  output: { ref: answer, from: solver }

entry: solver

stores:
  - name: trajectory
    type: message_log
    writer: solver             # INV-2：唯一写者；观察回灌由 solver 运行时串行追加
    lifecycle: run
    retention: { max_items: 128 }

nodes:
  - id: solver
    kind: agent
    uses:
      model: route.main@1
      tools: [pkg.hopqa.search, pkg.hopqa.lookup]
    writes: [trajectory]
    emits: { answer: answer }
    context:
      sections:
        - { from: template, template_ref: pkg.hopqa.fewshot, quota_tokens: 900 }
        - { from: input, fields: [question], policy: project, quota_tokens: 200 }
        - { from: store, store: trajectory, policy: full, quota_tokens: 6000 }

edges: []                      # 单节点：工具回灌在节点运行时内部完成，不经图边

budgets:
  - { id: turn_cap, dimension: turns, scope: node:solver, cap: 12 }
  - { id: token_cap, dimension: tokens_total, scope: node:solver, cap: 60000 }
  - { id: cost_cap, dimension: cents, scope: node:solver, cap: 120 }

stop:
  - when: "last_tool.first_line in ['FINISH', 'FINAL ANSWER']"
    outcome: completed
  - when: "steps.tool_free >= 2"
    outcome: failed

failures:
  - class: transport_transient
    retry: { max: 3, backoff_ms: 800 }
  - class: tool_error
    route: same_node
    feedback: error_observation    # "无结果"类观察回灌，节点内继续
  - class: budget_exhausted
    terminal: true
    outcome: failed
```

覆盖要点（对应 ReAct 卡 ⑥a）：单节点自循环=节点运行时环（编译目标=AgentSpec 四元组）；轨迹=追加式 `message_log` 槽；停止=终止动作 CEL + 步上限；预算=`max_iterations` 对应的 turns 计数器。卡 ⑥b 的运行时动作词表/自由文本切分 → `escape_hatches`（本配方未用，见 §8）。

### 4.2 样例 2 · Reflexion 自我反思

```yaml
version: 1
meta:
  name: reflexion
  display: "对齐样例 2 · Reflexion 自我反思"
  intent: "外层尝试环 × 内层执行环；评估外部化；反思节点是记忆唯一写者"

packages:
  - ref: codetask@1.1.0        # 外部判定单元 / 相似检索 / 摘要组件

types:
  - name: attempt_result
    schema:
      type: object
      required: [answer, trajectory_digest]
      properties:
        answer: { type: string }
        trajectory_digest: { type: string }
  - name: reflection_note
    schema:
      type: object
      required: [diagnosis, plan_next]
      properties:
        diagnosis: { type: string }
        plan_next: { type: string }
  - name: verdict_type
    schema:
      type: object
      required: [pass]
      properties: { pass: { type: boolean } }
  - name: attempt_record
    schema:
      type: object
      required: [result, pass]
      properties:
        result: { ref: attempt_result }
        pass: { type: boolean }

interface:
  input:
    type: object
    required: [task]
    properties: { task: { type: string } }
  output: { ref: attempt_result, from: best_selector }

entry: attempts

stores:
  - name: trajectory
    type: message_log
    writer: actor
    lifecycle: iteration       # 每次尝试重建（轨迹不跨尝试）
    retention: { max_items: 96 }
  - name: reflections
    type: collection
    item: reflection_note
    writer: reflector          # INV-2：反思节点唯一写者
    lifecycle: run             # 反思跨尝试累积
    retention: { max_items: 8 }
  - name: attempts_log
    type: collection
    item: attempt_record
    writer: evaluate           # check 写自己的判定记录（不写被验工件）
    lifecycle: run
    retention: { max_items: 8 }

subgraphs:
  - name: attempt_body
    version: "1.0"
    entry: actor
    nodes:
      - id: actor
        kind: agent
        uses: { model: route.main@1, tools: [pkg.codetask.run] }
        writes: [trajectory]
        emits: { result: attempt_result }
        context:
          sections:
            - { from: template, template_ref: pkg.codetask.actor_system, quota_tokens: 500 }
            - { from: input, fields: [task], policy: project, quota_tokens: 300 }
            - { from: store, store: reflections, policy: retrieve, component: pkg.codetask.similarity@1, args: { k: 2 }, quota_tokens: 700 }
            - { from: store, store: trajectory, policy: full, quota_tokens: 5000 }
      - id: evaluate
        kind: check                    # INV-3 验证面 + INV-4 外部判定单元
        uses: { unit: pkg.codetask.judge@1 }
        writes: [attempts_log]
        consumes: { result: attempt_result }
        emits: { verdict: verdict_type }
      - id: reflector
        kind: agent
        uses: { model: route.cheap@1 }
        writes: [reflections]
        emits: { note: reflection_note }
        context:
          sections:
            - { from: template, template_ref: pkg.codetask.reflector_system, quota_tokens: 400 }
            - { from: input, fields: [task], policy: project, quota_tokens: 300 }
            - { from: edge, port: verdict, policy: project, quota_tokens: 100 }
            - { from: store, store: trajectory, policy: summarize, component: pkg.codetask.summarizer@1, quota_tokens: 1200 }
    edges:
      - { from: actor, output: result, to: evaluate, input: result }
      - { from: evaluate, output: verdict, to: reflector, input: verdict, when: "attempt.verdict.pass == false" }

nodes:
  - id: attempts
    kind: loop
    loop:
      body: attempt_body
      max_iterations: 4
      carried:
        - { store: reflections, max_items: 8 }
      safety_points:
        - { node: evaluate, kind: check }
      exit_when: "attempt.verdict.pass == true"
      on_exhausted: keep_best
  - id: best_selector
    kind: transform
    reads: [attempts_log]
    ops: [select_best]
    args: { by: pass, prefer: true }
    emits: { answer: attempt_result }

edges:
  - { from: attempts, output: signal, to: best_selector, input: signal, signal: true }

budgets:
  - { id: attempt_turns, dimension: turns, scope: loop:attempts, cap: 24 }
  - { id: cost_cap, dimension: cents, scope: plan, cap: 240 }

failures:
  - class: transport_transient
    retry: { max: 3, backoff_ms: 800 }
  - class: environment_failure
    retry: { max: 3, backoff_ms: 60000 }
    terminal: true
    outcome: escalated_human
  - class: budget_exhausted
    terminal: true
    outcome: failed
```

覆盖要点（Reflexion 卡 ⑥a 1-9）：双层循环=外层受控环+actor 节点内环；Evaluator=独立 check + 外部单元；Buffer=collection 槽+检索注入；作用域=`iteration` vs `run` 两级 lifecycle；重试=失败外层重启。卡 ⑥b 1/3/6（空值守卫、动态预算分配、异质 Evaluator）→ 逃逸或组件参数。

### 4.3 样例 3 · Voyager 技能库 + 自动课程

```yaml
version: 1
meta:
  name: voyager_curriculum
  display: "对齐样例 3 · Voyager 技能库 + 自动课程"
  intent: "嵌套受控循环：外层课程步（提案→内层习得环）；技能库持久 + 检索注入；守门入库"

packages:
  - ref: openworld@1.0.0       # 环境适配执行器 / 相似检索 / 课程与迭代提示模板

types:
  - name: goal
    schema:
      type: object
      required: [text, difficulty]
      properties:
        text: { type: string }
        difficulty: { type: integer }
  - name: skill_entry
    schema:
      type: object
      required: [name, description, body_ref]
      properties:
        name: { type: string }
        description: { type: string }
        body_ref: { type: string }
  - name: exec_report
    schema:
      type: object
      required: [ok, feedback]
      properties:
        ok: { type: boolean }
        feedback: { type: string }
  - name: self_check
    schema:
      type: object
      required: [pass]
      properties: { pass: { type: boolean } }

interface:
  input:
    type: object
    required: [env_summary]
    properties: { env_summary: { type: string } }
  output: { ref: "list<skill_entry>", from: export_skills }

entry: explore

stores:
  - name: curriculum
    type: collection
    item: goal
    writer: proposer
    lifecycle: run
    retention: { max_items: 64 }
  - name: skill_library
    type: collection
    item: skill_entry
    writer: curator            # INV-2：守门写入（执行成功 ∧ 自检通过才入库）
    lifecycle: persistent      # 跨会话持久
    retention: { max_items: 512 }
  - name: attempt_scratch
    type: message_log
    writer: generator
    lifecycle: iteration
    retention: { max_items: 48 }

subgraphs:
  - name: skill_attempt        # 内层：一次"生成→执行→自检→守门"
    version: "1.0"
    entry: generator
    inputs: [goal_text]
    outputs: { acquired: { from_arg: goal_text_passthrough_ignore } }
    nodes:
      - id: generator
        kind: agent
        uses: { model: route.main@1 }
        writes: [attempt_scratch]
        emits: { draft: skill_entry, check: self_check }
        context:
          sections:
            - { from: template, template_ref: pkg.openworld.iterative_prompt, quota_tokens: 700 }
            - { from: arg, name: goal_text, policy: project, quota_tokens: 200 }
            - { from: store, store: skill_library, policy: retrieve, component: pkg.openworld.similarity@1, args: { k: 3 }, quota_tokens: 1500 }
            - { from: store, store: attempt_scratch, policy: full, quota_tokens: 2500 }
      - id: executor
        kind: tool
        uses: { tool: pkg.openworld.env@1 }
        consumes: { draft: skill_entry }
        emits: { report: exec_report }
      - id: admit
        kind: gate
        consumes: { report: exec_report, check: self_check }
        assert: "inputs.report.ok && inputs.check.pass"
      - id: curator
        kind: transform
        writes: [skill_library]
        ops: [project]
        consumes: { draft: skill_entry }
        emits: { acquired: skill_entry }
    edges:
      - { from: generator, output: draft, to: executor, input: draft }
      - { from: generator, output: check, to: admit, input: check }
      - { from: executor, output: report, to: admit, input: report }
      - { from: admit, output: draft, to: curator, input: draft }
  - name: curriculum_step      # 外层体：提案 → 内层习得环
    version: "1.0"
    entry: proposer
    nodes:
      - id: proposer
        kind: agent
        uses: { model: route.cheap@1 }
        writes: [curriculum]
        emits: { goal: goal }
        context:
          sections:
            - { from: template, template_ref: pkg.openworld.curriculum_prompt, quota_tokens: 500 }
            - { from: input, fields: [env_summary], policy: project, quota_tokens: 400 }
            - { from: store, store: curriculum, policy: latest_k, args: { k: 10 }, quota_tokens: 900 }
      - id: acquire
        kind: loop
        loop:
          body: skill_attempt
          max_iterations: 6
          args: { goal_text: proposer.goal.text }
          carried:
            - { store: skill_library, max_items: 512 }
          safety_points:
            - { node: admit, kind: gate }
          exit_when: "attempt.gate_passed == true"
          on_exhausted: continue    # 本目标轮次耗尽→换下一个课程目标

nodes:
  - id: explore
    kind: loop
    loop:
      body: curriculum_step
      max_iterations: 200
      carried:
        - { store: curriculum, max_items: 64 }
        - { store: skill_library, max_items: 512 }
      safety_points:
        - { node: admit, kind: gate }   # 跨层引用：doc 唯一 id
      exit_when: "budget.cents_spent >= budget.cents_cap * 9 / 10"
      on_exhausted: continue
  - id: export_skills
    kind: transform
    reads: [skill_library]
    ops: [project]
    emits: { skills: "list<skill_entry>" }

edges:
  - { from: explore, output: signal, to: export_skills, input: signal, signal: true }

budgets:
  - { id: cost_cap, dimension: cents, scope: plan, cap: 3000 }
  - { id: token_cap, dimension: tokens_total, scope: plan, cap: 3000000 }

failures:
  - class: tool_error
    route: same_node
    feedback: error_observation    # 异常栈回灌，改写重试
  - class: gate_refused
    route: next_iteration          # 自检不过：不入库，重规划
  - class: budget_exhausted
    terminal: true
    outcome: completed             # 预算到顶=会话收束，导出已习得技能
```

覆盖要点（Voyager 卡 ⑥a 1-8）：双层循环；课程表/技能库=持久 collection；检索注入；固定五段模板（template+arg+retrieve+scratch）；写库条件=gate。卡 ⑥b 1/2/6（任意代码执行、运行时改图、软终止）→ 逃逸。注：`outputs.acquired` 的直通声明此处仅为占位示例，实际产出以 `curator.acquired` 为准（编译器对未使用直通端口告警不计错）。

### 4.4 样例 4 · SWE-agent ACI 约束接口

```yaml
version: 1
meta:
  name: swe_agent_aci
  display: "对齐样例 4 · SWE-agent ACI 约束接口"
  intent: "受限动作面（包内工具）+ 窗口化上下文 + 提交动作终止 + 轮/token/费用/时钟四重预算"

packages:
  - ref: sweng@1.2.0           # ACI 工具面与协议模板（领域具体性住在这里）

types:
  - name: patch_ref
    schema:
      type: object
      required: [artifact_ref]
      properties: { artifact_ref: { type: string } }

interface:
  input:
    type: object
    required: [issue_text, repo_ref]
    properties:
      issue_text: { type: string }
      repo_ref: { type: string }
  output: { ref: patch_ref, from: solver }

entry: solver

stores:
  - name: history
    type: message_log
    writer: solver
    lifecycle: run
    retention: { policy: rolling_window, keep_system: true, max_items: 40 }

nodes:
  - id: solver
    kind: agent
    uses:
      model: route.main@1
      tools: [pkg.sweng.locate, pkg.sweng.view, pkg.sweng.edit, pkg.sweng.run_checks, pkg.sweng.submit]
    writes: [history]
    emits: { patch: patch_ref }
    context:
      sections:
        - { from: template, template_ref: pkg.sweng.aci_protocol, quota_tokens: 1600 }
        - { from: input, fields: [issue_text, repo_ref], policy: project, quota_tokens: 1200 }
        - { from: store, store: history, policy: latest_k, args: { k: 24 }, quota_tokens: 9000 }
      tool_output_policy: { truncate_tail_tokens: 400 }   # 单条观察截断（ACI 裁剪纪律）

edges: []

budgets:
  - { id: turns_cap, dimension: turns, scope: node:solver, cap: 50 }
  - { id: tokens_cap, dimension: tokens_total, scope: node:solver, cap: 400000 }
  - { id: cost_cap, dimension: cents, scope: node:solver, cap: 300 }
  - { id: clock_cap, dimension: clock_ms, scope: node:solver, cap: 1800000 }

stop:
  - when: "last_tool.name == 'pkg.sweng.submit'"
    outcome: completed
  - when: "steps.tool_free >= 3"
    outcome: failed

failures:
  - class: schema_invalid       # ACI 格式违规：不消耗环境执行，格式重述回灌
    route: same_node
    feedback: format_reminder
    retry: { max: 4, backoff_ms: 0 }
  - class: tool_error           # 非零返回/编辑失败：错误文本作为观察回灌
    route: same_node
    feedback: error_observation
  - class: transport_transient
    retry: { max: 5, backoff_ms: 1200 }
  - class: budget_exhausted
    terminal: true
    outcome: failed

escape_hatches: []              # 本配方零逃逸：ACI 全部经包工具声明
```

覆盖要点（SWE-agent 卡 ⑥a 1-12）：受限命令集=包工具；上下文装配=模板+滚动窗；观察截断=`tool_output_policy`；记忆=消息槽+磁盘工件（repo_ref 输入）；步数/token/成本/超时=四维预算；submit=CEL 终止；评测器在配方外（bench 侧外部判定，INV-4 天然满足）。卡 ⑥b 1/2/5/8（软对齐编辑原语、模糊解析、环境准备脚本、人工介入）→ 逃逸/包内实现。

### 4.5 样例 5 · MemGPT 分层记忆

```yaml
version: 1
meta:
  name: memgpt_tiers
  display: "对齐样例 5 · MemGPT 分层记忆"
  intent: "主上下文分区组装（固定配额）+ 记忆自编辑经写端口串行化 + 步内调用上限"

packages:
  - ref: memorykit@1.0.0       # 记忆管理工具 / 归档检索 / 召回 / 系统模板

types:
  - name: reply
    schema:
      type: object
      required: [text]
      properties: { text: { type: string } }

interface:
  input:
    type: object
    required: [user_msg]
    properties: { user_msg: { type: string } }
  output: { ref: reply, from: assistant }

entry: assistant

stores:
  - name: core_memory
    type: kv
    value: string
    writer: assistant           # INV-2：自编辑经 assistant 写端口，宿主串行落账
    lifecycle: run
    retention: { max_bytes: 8192 }
  - name: message_buffer
    type: message_log
    writer: assistant
    lifecycle: run
    retention: { policy: rolling_window, max_items: 16 }   # 宿主兜底驱逐：最旧出局
  - name: archival
    type: vector_index
    item: string
    writer: assistant
    lifecycle: persistent
    retention: { max_items: 10000 }

nodes:
  - id: assistant
    kind: agent
    uses:
      model: route.main@1
      tools:
        - pkg.memorykit.core_append       # 写端口绑定 core_memory
        - pkg.memorykit.core_replace
        - pkg.memorykit.archival_insert
        - pkg.memorykit.archival_search
        - pkg.memorykit.recall
    writes: [core_memory, message_buffer, archival]   # 一节点写多槽合法（每槽仍单写）
    emits: { reply: reply }
    context:                        # 主上下文 = 分区模板，固定额度
      sections:
        - { from: template, template_ref: pkg.memorykit.system, quota_tokens: 400 }
        - { from: store, store: core_memory, policy: full, quota_tokens: 1500 }
        - { from: store, store: message_buffer, policy: latest_k, args: { k: 12 }, quota_tokens: 3000 }
        - { from: store, store: archival, policy: none, quota_tokens: 0 }   # 外部层：仅经检索工具可见

edges: []

budgets:
  - { id: calls_per_step, dimension: tool_calls, scope: node:assistant, cap: 4 }   # 步内调用上限
  - { id: turn_cap, dimension: turns, scope: node:assistant, cap: 40 }
  - { id: cost_cap, dimension: cents, scope: plan, cap: 200 }

stop:
  - when: "steps.tool_calls_last_turn == 0"   # 不再发出函数调用 → 收束作答
    outcome: completed

failures:
  - class: tool_error
    route: same_node
    feedback: error_observation    # 写入超限/检索失败 → 错误回灌自纠
  - class: budget_exhausted
    terminal: true
    outcome: failed

escape_hatches:
  - id: semantic_eviction
    kind: runtime_context_mutation
    reason: "模型驱动的语义分页（先写外部再驱逐主上下文条目）超出声明式保留策略的表达面"
    owner: alignment-team
    share_budget_pct: 5
    impl_ref: packages/memorykit@1.0.0/hatches/semantic_eviction.py
```

覆盖要点（MemGPT 卡 ⑥a 1-7）：中断驱动步循环=节点运行时环；主/外分层=sections 分区配额 + `policy: none`（工具可见性）；自编辑=写端口（append/replace 双算子在包工具内）；环形缓冲=rolling_window；步内上限=`tool_calls` 预算。卡 ⑥b 1/5/6（运行时自改写、语义驱逐、任意时刻抢占）→ 逃逸舱示范。

### 4.6 样例 6 · MetaGPT 流水线 + typed handoff

```yaml
version: 1
meta:
  name: metagpt_sop
  display: "对齐样例 6 · MetaGPT SOP 流水线 + typed handoff"
  intent: "结构化工件契约与信封血缘；repo 单写者；QA 回环=受控循环，安全点=外部评估"

packages:
  - ref: sweng@1.2.0

types:
  - name: prd
    schema:
      type: object
      required: [vision, features]
      properties:
        vision: { type: string }
        features: { type: array, items: { type: string } }
  - name: design
    schema:
      type: object
      required: [modules, interfaces]
      properties:
        modules: { type: array, items: { type: string } }
        interfaces: { type: array, items: { type: string } }
  - name: task_item
    schema:
      type: object
      required: [id, instruction, target]
      properties:
        id: { type: string }
        instruction: { type: string }
        target: { type: string }
  - name: code_file
    schema:
      type: object
      required: [path, content_ref]
      properties:
        path: { type: string }
        content_ref: { type: string }
  - name: qa_report
    schema:
      type: object
      required: [pass, failures]
      properties:
        pass: { type: boolean }
        failures: { type: array, items: { type: string } }

interface:
  input:
    type: object
    required: [requirement]
    properties: { requirement: { type: string } }
  output: { ref: qa_report, from: build }

entry: pm

stores:
  - name: tasks_board
    type: collection
    item: task_item
    writer: planner
    readers: [qa]
    lifecycle: run
    retention: { max_items: 128 }
  - name: repo
    type: collection
    item: code_file
    writer: apply           # INV-2：仓库唯一写者（装配与修补都经它串行落账）
    readers: [qa]           # QA 可读、不可写（E2311 会拒绝任何第二写者）
    lifecycle: run
    retention: { max_items: 256 }

subgraphs:
  - name: qa_loop
    version: "1.0"
    entry: engineer
    nodes:
      - id: engineer
        kind: agent
        uses: { model: route.main@1, tools: [pkg.sweng.locate, pkg.sweng.view, pkg.sweng.edit] }
        emits: { files: "list<code_file>" }
        context:
          sections:
            - { from: template, template_ref: pkg.sweng.engineer_system, quota_tokens: 600 }
            - { from: store, store: tasks_board, policy: full, quota_tokens: 1800 }
            - { from: edge, port: feedback, policy: project, quota_tokens: 800, optional: true }   # QA 打回（首轮缺席）
      - id: apply
        kind: transform
        writes: [repo]
        ops: [merge]
        consumes: { files: "list<code_file>" }
        emits: { snapshot: "list<code_file>" }
      - id: qa
        kind: evaluator          # INV-3 验证面 + INV-4 外部判定单元
        uses: { unit: pkg.sweng.test_unit@1 }
        reads: [repo, tasks_board]
        consumes: { snapshot: "list<code_file>" }
        emits: { report: qa_report }
    edges:
      - { from: engineer, output: files, to: apply, input: files }
      - { from: apply, output: snapshot, to: qa, input: snapshot }
      - { from: qa, output: report, to: engineer, input: feedback, when: "attempt.verdict.pass == false" }   # 回环边在循环体内（DAG 豁免由 loop 构造接管）

nodes:
  - id: pm
    kind: agent
    uses: { model: route.main@1 }
    emits: { prd: prd }
    context:
      sections:
        - { from: template, template_ref: pkg.sweng.pm_system, quota_tokens: 500 }
        - { from: input, fields: [requirement], policy: project, quota_tokens: 600 }
  - id: architect
    kind: agent
    uses: { model: route.main@1 }
    emits: { design: design }
    context:
      sections:
        - { from: template, template_ref: pkg.sweng.architect_system, quota_tokens: 500 }
        - { from: edge, port: prd, policy: project, quota_tokens: 2000 }   # typed handoff：端口类型=prd
  - id: planner
    kind: agent
    uses: { model: route.cheap@1 }
    writes: [tasks_board]
    emits: { tasks: "list<task_item>" }
    context:
      sections:
        - { from: template, template_ref: pkg.sweng.planner_system, quota_tokens: 400 }
        - { from: edge, port: prd, policy: project, quota_tokens: 1500 }
        - { from: edge, port: design, policy: project, quota_tokens: 1500 }
  - id: build
    kind: loop
    loop:
      body: qa_loop
      max_iterations: 3
      carried:
        - { store: repo, max_items: 256 }
      safety_points:
        - { node: qa, kind: evaluator }
      exit_when: "attempt.verdict.pass == true"
      on_exhausted: fail
    emits: { report: { from_body: qa.report } }

edges:
  - { from: pm, output: prd, to: architect, input: prd, handoff: envelope }        # envelope<prd>：带 from_node/artifact_type/step 血缘
  - { from: architect, output: design, to: planner, input: design, handoff: envelope }
  - { from: planner, output: tasks, to: build, input: tasks }

budgets:
  - { id: cost_cap, dimension: cents, scope: plan, cap: 600 }
  - { id: fix_turns, dimension: turns, scope: loop:build, cap: 60 }

failures:
  - class: schema_invalid       # 工件不合 schema：打回生成角色重填
    route: same_node
    feedback: format_reminder
    retry: { max: 2, backoff_ms: 0 }
  - class: environment_failure
    retry: { max: 3, backoff_ms: 60000 }
  - class: budget_exhausted
    terminal: true
    outcome: failed
```

覆盖要点（MetaGPT 卡 ⑥a 全部）：SOP=静态边流水线；结构化工件=typed 端口（每边编译期类型核对 + 运行期 schema 校验，补 LangGraph G3）；`cause_by` 血缘=`handoff: envelope`；QA 回环=受控循环（有界+安全点）；TaskFinished=`exit_when`；工作区文件=repo 槽。卡 ⑥b 2/3/6（订阅触发、动态收件人、LLM 语义终止）→ 静态边近似或逃逸（§8）。

### 4.7 样例 7 · Multi-Agent Debate（多写者→串行化）

```yaml
version: 1
meta:
  name: debate_kv
  display: "对齐样例 7 · Multi-Agent Debate（多写者→串行化示例）"
  intent: "N 辩手 map 并行互不可见；collector 是黑板唯一写者；多数票+裁决 fallback；一致性早停"

packages:
  - ref: debatekit@1.0.0

types:
  - name: position
    schema:
      type: object
      required: [claim]
      properties:
        claim: { type: string }
        confidence_milli: { type: integer }
  - name: turn_record
    schema:
      type: object
      required: [round, anonymous_text]
      properties:
        round: { type: integer }
        anonymous_text: { type: string }
  - name: tally_result
    schema:
      type: object
      required: [answers, top_count, top_share_milli]
      properties:
        answers: { type: integer }
        top_count: { type: integer }
        top_share_milli: { type: integer }

interface:
  input:
    type: object
    required: [question, personas]
    properties:
      question: { type: string }
      personas: { type: array, items: { type: string } }
  output: { ref: position, from: finalize }

entry: rounds

stores:
  - name: transcript
    type: collection
    item: turn_record
    writer: collector         # INV-2：并行辩手不写黑板；汇聚节点串行写入
    readers: [adjudicate]     # 全记录仅裁决可读；辩手只经匿名化视图
    lifecycle: run
    retention: { max_items: 64 }

subgraphs:
  - name: one_turn
    version: "1.0"
    entry: debater
    inputs: [item]
    outputs: { position: position }
    nodes:
      - id: debater
        kind: agent
        uses: { model: route.main@1 }
        emits: { position: position }
        context:
          sections:
            - { from: template, template_ref: pkg.debatekit.system, vars: { persona: arg.item }, quota_tokens: 400 }
            - { from: input, fields: [question], policy: project, quota_tokens: 300 }
            - { from: store, store: transcript, policy: latest_k, args: { k: 8, redact: [holder] }, quota_tokens: 2400 }   # 匿名化同伴消息
  - name: round_body
    version: "1.0"
    entry: debate_map
    nodes:
      - id: debate_map
        kind: map
        map: { over: input.personas, body: one_turn, max_fanout: 5 }   # 并行互不可见：实例间无横向边
        emits: { items: "list<position>" }
      - id: collector
        kind: transform
        writes: [transcript]
        ops: [anonymize, shuffle_seeded, truncate]
        args: { seed_ref: input.question, max_tokens_each: 200 }   # 匿名 + 种子化乱序 + 限长
        consumes: { items: "list<position>" }
        emits: {}
      - id: tally
        kind: transform
        ops: [tally]
        args: { by: claim }
        consumes: { items: "list<position>" }
        emits: { result: tally_result }
      - id: converge_gate
        kind: gate
        consumes: { result: tally_result }
        assert: "inputs.result.top_share_milli >= 0 && inputs.result.top_share_milli <= 1000"
    edges:
      - { from: debate_map, output: items, to: collector, input: items }
      - { from: debate_map, output: items, to: tally, input: items }
      - { from: tally, output: result, to: converge_gate, input: result }

nodes:
  - id: rounds
    kind: loop
    loop:
      body: round_body
      max_iterations: 3       # K 轮上限（收益趋平→3 轮足够）
      carried:
        - { store: transcript, max_items: 64 }
      safety_points:
        - { node: converge_gate, kind: gate }
      exit_when: "tally.top_share_milli >= 700"   # 一致性早停（预计算份额进谓词）
      on_exhausted: continue
    emits: { positions: { from_body: debate_map.items } }
  - id: vote
    kind: transform
    ops: [tally, select_best]
    args: { by: claim }
    consumes: { positions: "list<position>" }
    emits:
      winner: position
      top_count: { type: integer }
      answers: { type: integer }
  - id: adjudicate
    kind: agent
    uses: { model: route.main@1 }
    emits: { winner: position }
    context:
      sections:
        - { from: template, template_ref: pkg.debatekit.judge_system, quota_tokens: 400 }
        - { from: input, fields: [question], policy: project, quota_tokens: 300 }
        - { from: store, store: transcript, policy: full, quota_tokens: 6000 }   # 裁决读全记录
  - id: finalize
    kind: transform
    ops: [project]
    consumes: { winner: position }
    emits: { answer: position }

selectors:
  - id: settle
    at: vote
    default: adjudicate      # 使命指令 fallback：集中裁决（验证瓶颈）
    rules:
      - when: "vote.top_count * 2 > vote.answers"
        goto: finalize       # 明确多数 → 直接定案

edges:
  - { from: rounds, output: positions, to: vote, input: positions }
  - { from: vote, output: winner, to: finalize, input: winner }
  - { from: adjudicate, output: winner, to: finalize, input: winner }   # 与上一条经 selector 分支不相交（E2206 可证性由选择器分支分析给出）

budgets:
  - { id: cost_cap, dimension: cents, scope: plan, cap: 400 }
  - { id: turns_cap, dimension: turns, scope: loop:rounds, cap: 30 }

failures:
  - class: schema_invalid
    retry: { max: 2, backoff_ms: 0 }
    fallback_route: adjudicate      # 限次重解析仍败 → 裁决器自由文本判定
  - class: budget_exhausted
    route: vote                     # 成本超限：中止并返回当前多数
    terminal: true
    outcome: completed
```

覆盖要点（Debate 卡 ⑥a 全部 + ⑥b 2/7/8 的声明式化）：扇出-广播-扇入=map+collector；多写者问题=collector 单写者（对照 §5 INV-2 违规样例）；匿名+乱序=`anonymize/shuffle_seeded`（种子化保可复现）；多数票+裁决=`selectors` fallback；早停=`tally` 预计算 + CEL；写权限仲裁=readers 集合。语义共识判定（⑥b 1）→ `llm_predicate` 逃逸。

### 4.8 样例 8 · GPTSwarm 图算子

```yaml
version: 1
meta:
  name: swarm_operators
  display: "对齐样例 8 · GPTSwarm 图算子"
  intent: "节点=零状态算子、边=可见性来源；并行分支互不可见；批评-修订受控环；结构搜索=元层逃逸"

packages:
  - ref: hopqa@1.0.0

types:
  - name: evidence_bundle
    schema:
      type: object
      required: [passages]
      properties: { passages: { type: array, items: { type: string } } }
  - name: outline
    schema:
      type: object
      required: [points]
      properties: { points: { type: array, items: { type: string } } }
  - name: draft
    schema:
      type: object
      required: [text]
      properties: { text: { type: string } }
  - name: review
    schema:
      type: object
      required: [notes, score_milli]
      properties:
        notes: { type: string }
        score_milli: { type: integer }
  - name: answer
    schema:
      type: object
      required: [text]
      properties: { text: { type: string } }

interface:
  input:
    type: object
    required: [question]
    properties: { question: { type: string } }
  output: { ref: answer, from: merge }

entry: retrieve

nodes:
  - id: retrieve
    kind: tool
    uses: { tool: pkg.hopqa.retrieve@1 }
    emits: { evidence: evidence_bundle }
  - id: plan
    kind: agent
    uses: { model: route.main@1 }
    emits: { outline: outline }
    context:
      sections:
        - { from: template, template_ref: pkg.hopqa.planner_system, quota_tokens: 400 }
        - { from: edge, port: evidence, policy: project, quota_tokens: 2000 }
  - id: gen_a
    kind: agent                 # 同构节点模板 + 参数化分支（角色多样性）
    uses: { model: route.main@1 }
    emits: { draft: draft }
    context:
      sections:
        - { from: template, template_ref: pkg.hopqa.drafter_system, vars: { style: conservative }, quota_tokens: 400 }
        - { from: edge, port: outline, policy: project, quota_tokens: 600 }
        - { from: edge, port: evidence, policy: project, quota_tokens: 1500 }
  - id: gen_b
    kind: agent
    uses: { model: route.main@1 }
    emits: { draft: draft }
    context:
      sections:
        - { from: template, template_ref: pkg.hopqa.drafter_system, vars: { style: divergent }, quota_tokens: 400 }
        - { from: edge, port: outline, policy: project, quota_tokens: 600 }
        - { from: edge, port: evidence, policy: project, quota_tokens: 1500 }
  - id: polish
    kind: loop
    loop:
      body: polish_body
      max_iterations: 3
      args: { draft_a: gen_a.draft, draft_b: gen_b.draft }
      carried: []
      safety_points:
        - { node: score_gate, kind: gate }
      exit_when: "attempt.score_milli >= 700"
      on_exhausted: continue
    emits: { revisions: { from_body: revise.revised } }
  - id: merge
    kind: transform
    ops: [merge, project]
    consumes: { revisions: "list<draft>" }
    emits: { answer: answer }

subgraphs:
  - name: polish_body
    version: "1.0"
    entry: critic
    inputs: [draft_a, draft_b]
    nodes:
      - id: critic
        kind: agent
        uses: { model: route.cheap@1 }
        emits: { review: review }
        context:
          sections:
            - { from: template, template_ref: pkg.hopqa.critic_system, quota_tokens: 400 }
            - { from: arg, name: draft_a, policy: project, quota_tokens: 1500 }
            - { from: arg, name: draft_b, policy: project, quota_tokens: 1500 }
            - { from: edge, port: revised, policy: project, quota_tokens: 2500, optional: true }   # 第二轮起：修订稿
      - id: score_gate
        kind: gate
        consumes: { review: review }
        assert: "attempt.score_milli >= 0 && attempt.score_milli <= 1000"   # 安全点：评分合法性（评分阈值退出在 loop.exit_when）
      - id: revise
        kind: agent
        uses: { model: route.main@1 }
        emits: { revised: "list<draft>" }
        context:
          sections:
            - { from: template, template_ref: pkg.hopqa.reviser_system, quota_tokens: 400 }
            - { from: edge, port: review, policy: project, quota_tokens: 800 }
            - { from: arg, name: draft_a, policy: project, quota_tokens: 1500 }
            - { from: arg, name: draft_b, policy: project, quota_tokens: 1500 }
    edges:
      - { from: critic, output: review, to: score_gate, input: review }
      - { from: score_gate, output: review, to: revise, input: review }

edges:
  - { from: retrieve, output: evidence, to: plan, input: evidence }
  - { from: plan, output: outline, to: gen_a, input: outline }
  - { from: plan, output: outline, to: gen_b, input: outline }
  - { from: polish, output: revisions, to: merge, input: revisions }
  # gen_a/gen_b → polish 经 loop.args 引用（隐式边，计 DAG 依赖）

budgets:
  - { id: cost_cap, dimension: cents, scope: plan, cap: 300 }
  - { id: polish_turns, dimension: turns, scope: loop:polish, cap: 12 }

failures:
  - class: tool_error
    route: same_node
    feedback: error_observation    # 坏节点在拓扑层的修复=换依赖/换实现（包侧）；运行期先回灌
  - class: transport_transient
    retry: { max: 3, backoff_ms: 800 }
  - class: budget_exhausted
    terminal: true
    outcome: failed

escape_hatches:
  - id: structure_optimizer
    kind: meta_loop             # 以图为动作空间的搜索在声明式核心之外
    reason: "GPTSwarm 的图编辑算子 + 奖励驱动搜索属元层；产物须回填为版本化子图方可进核心"
    owner: lang-team
    share_budget_pct: 20
    impl_ref: packages/hopqa@1.0.0/hatches/graph_optimizer.py
```

覆盖要点（GPTSwarm 卡 ⑥a 全部）：agent=图=显式节点/边声明；自环/反馈环=受控循环；并行分支互不可见=无横向边（可见性唯一来源是边）；工具/记忆=节点+槽；条件路由=gate/选择器。卡 ⑥b 1/2/4（图编辑、奖励环、任意节点体）→ `meta_loop`/`program_synthesis` 逃逸示范。

### 4.9 样例 9 · AFlow 带评估反馈环（受控循环示例）

```yaml
version: 1
meta:
  name: aflow_feedback_loop
  display: "对齐样例 9 · AFlow 带评估反馈环（受控循环示例）"
  intent: "搜索元循环=受控循环：变异（逃逸合成）→候选执行→外部评估→经验回灌；参考答案与分数对候选不可读"

packages:
  - ref: searchkit@1.0.0       # 图合成工具 / 外部评估单元 / 语料装载

types:
  - name: problem
    schema:
      type: object
      required: [prompt]
      properties: { prompt: { type: string } }
  - name: candidate
    schema:
      type: object
      required: [ref, parent]
      properties:
        ref: { type: string }      # 版本化子图工件引用
        parent: { type: integer }
  - name: answer
    schema:
      type: object
      required: [text]
      properties: { text: { type: string } }
  - name: score_record
    schema:
      type: object
      required: [candidate, quality_milli, cost_milli]
      properties:
        candidate: { type: integer }
        quality_milli: { type: integer }
        cost_milli: { type: integer }
  - name: outcome_pair
    schema:
      type: object
      required: [answer, origin]
      properties:
        answer: { ref: answer }
        origin: { ref: candidate }

interface:
  input:
    type: object
    required: [problem, validation_set]
    properties:
      problem: { ref: problem }
      validation_set: { type: array, items: { ref: problem } }
  output: { ref: candidate, from: best }

entry: loader

stores:
  - name: experience
    type: collection
    item: score_record
    writer: scoreboard         # INV-2：评估结果由记分板唯一串行写入
    readers: [mutate]          # 变异器可读分数；候选子图不可读（INV-4）
    lifecycle: run
    retention: { max_items: 20 }   # 有界经验池
  - name: answers_ref
    type: collection
    item: answer
    writer: loader
    readers: [assess]          # 参考答案只对评估器可读
    lifecycle: run

subgraphs:
  - name: candidate_run        # 单候选执行：静态算子小图（ensemble + 聚合）
    version: "1.0"
    entry: gen_a
    inputs: [item]
    outputs:
      answer: answer
      origin: { from_arg: item }
    nodes:
      - id: gen_a
        kind: agent
        uses: { model: route.main@1 }
        emits: { draft: answer }
        context:
          sections:
            - { from: template, template_ref: pkg.searchkit.solver_system, quota_tokens: 500 }
            - { from: arg, name: item, policy: project, quota_tokens: 600 }
      - id: gen_b
        kind: agent
        uses: { model: route.alt@1 }
        emits: { draft: answer }
        context:
          sections:
            - { from: template, template_ref: pkg.searchkit.solver_system, vars: { variant: b }, quota_tokens: 500 }
            - { from: arg, name: item, policy: project, quota_tokens: 600 }
      - id: aggregate
        kind: transform
        ops: [tally, select_best]
        args: { by: agreement }
        consumes: { draft_a: answer, draft_b: answer }
        emits: { answer: answer }
    edges:
      - { from: gen_a, output: draft, to: aggregate, input: draft_a }
      - { from: gen_b, output: draft, to: aggregate, input: draft_b }
  - name: search_round
    version: "1.0"
    entry: mutate
    nodes:
      - id: mutate
        kind: agent
        uses: { model: route.main@1, tools: [pkg.searchkit.graph_synth] }
        emits: { candidates: "list<candidate>" }
        context:
          sections:
            - { from: template, template_ref: pkg.searchkit.mutator_system, quota_tokens: 600 }
            - { from: input, fields: [problem], policy: project, quota_tokens: 400 }
            - { from: store, store: experience, policy: latest_k, args: { k: 5 }, quota_tokens: 1200 }
      - id: run
        kind: map
        map: { over: mutate.candidates, body: candidate_run, max_fanout: 2 }
        emits: { items: "list<outcome_pair>" }
      - id: assess
        kind: evaluator          # INV-4：评估器外部化，读参考答案
        uses: { unit: pkg.searchkit.assess@1 }
        reads: [answers_ref]
        consumes: { items: "list<outcome_pair>" }
        emits: { scores: "list<score_record>" }
      - id: scoreboard
        kind: transform
        writes: [experience]
        ops: [project]
        consumes: { scores: "list<score_record>" }
        emits: {}
    edges:
      - { from: run, output: items, to: assess, input: items }
      - { from: assess, output: scores, to: scoreboard, input: scores }

nodes:
  - id: loader
    kind: tool
    uses: { tool: pkg.searchkit.corpus@1 }
    writes: [answers_ref]
    emits: { signal: { type: string } }
  - id: search
    kind: loop
    loop:
      body: search_round
      max_iterations: 20       # MCTS 迭代预算
      carried:
        - { store: experience, max_items: 20 }
      safety_points:
        - { node: assess, kind: evaluator }   # 每轮必须过外部评估（反馈环的安全点）
      exit_when: "budget.cents_spent >= budget.cents_cap * 9 / 10"
      on_exhausted: continue
  - id: best
    kind: transform
    reads: [experience]
    ops: [select_best]
    args: { by: quality_milli }
    emits: { winner: candidate }

edges:
  - { from: loader, output: signal, to: search, input: signal, signal: true }
  - { from: search, output: signal, to: best, input: signal, signal: true }

budgets:
  - { id: cost_cap, dimension: cents, scope: plan, cap: 5000 }
  - { id: eval_tokens, dimension: tokens_total, scope: loop:search, cap: 2000000 }

failures:
  - class: schema_invalid       # 合成产物不合法：候选判无效丢弃，重新生成
    retry: { max: 2, backoff_ms: 0 }
    route: next_iteration
  - class: tool_error           # 单样本执行失败计入质量分，不中止评估
    route: next_iteration
  - class: budget_exhausted
    terminal: true
    outcome: completed          # 跑满预算取最优（AFlow 主设置）

escape_hatches:
  - id: graph_synth
    kind: program_synthesis
    reason: "元智能体产出候选变体：核心只允许对已注册算子集做参数化组变；任意拓扑合成经逃逸并版本化登记后实例化"
    owner: lang-team
    share_budget_pct: 30
    impl_ref: packages/searchkit@1.0.0/hatches/graph_synth.py
```

覆盖要点（AFlow 卡 ⑥a + ⑥b 1/2/5）：工作流=静态算子图；四类算子=agent/tool/transform/evaluator kind；迭代/样本/阈值=预算；搜索终止=受控循环出口；反馈回灌=experience 携带 + mutate 检索；评估隔离=readers 双槽（分数给变异器、答案只给评估器）——**候选读不到任何一者**。MCTS 本体与成本遥测 → 逃逸。

### 4.10 样例 10 · LangGraph 状态图子集互译

互译表（LangGraph → AFD；来源：DSL-G0-表达力-langgraph.md §1）：

| LangGraph | AFD 对应物 | 备注 |
|---|---|---|
| `StateGraph(schema)` | `interface` + `stores` | 状态=显式槽而非隐式通道 |
| `Annotated[list, add_messages]` reducer | 按写者拆槽（每槽单写）+ `context.merge: {by: step_order}` 读合并 | **写合并→读合并**：多写合法化改为主张单写（INV-2 静态判定） |
| Node（普通函数） | kind 化节点（agent/tool/check/transform/human） | |
| `add_conditional_edges(route)` | `loop.exit_when` / `edges.when` / `selectors.rules`（CEL） | 路由谓词从 Python 函数变为可静态校验表达式 |
| `START` / `END` | `entry` / `goto: exit` | |
| `recursion_limit`（默认 25） | `loop.max_iterations` + `budgets.turns` | |
| Checkpointer（按 thread 快照） | `edges.checkpoint: true` | 快照内容/恢复语义由 af-plan 承载（落地契约 §6） |
| `interrupt(response_schema)` | `human` 节点 + `resume.schema` | 类型化恢复值 |
| `Send` 动态扇出 | `map`（静态 `over`，运行时定基数） | 任意动态基数 → L4 |
| 子图 subgraph | `subgraphs`（版本化） | |
| `InvalidUpdateError` 并发写保护 | **编译期 INV-2 直接拒绝多写者** | 从运行期检测提前到编译期 |
| `RetryPolicy` / `error_handler(goto)` | `failures.retry` / `failures.route` | 分类维度从异常类型变为语义类别 |
| super-step 事务性 | 计划对象执行语义（落地契约 §3） | 不在语法层 |

```yaml
version: 1
meta:
  name: langgraph_subset
  display: "对齐样例 10 · LangGraph StateGraph 子集互译"
  intent: "通道单写化+读合并替代 reducer；条件边=CEL 出口；recursion_limit=循环上限；interrupt=人工节点；checkpointer=边检查点"

packages:
  - ref: hopqa@1.0.0

types:
  - name: answer
    schema:
      type: object
      required: [text]
      properties: { text: { type: string } }
  - name: action_call
    schema:
      type: object
      required: [tool, args]
      properties:
        tool: { type: string }
        args: { type: object }
  - name: observation
    schema:
      type: object
      required: [ok, text]
      properties:
        ok: { type: boolean }
        text: { type: string }
  - name: approval
    schema:
      type: object
      required: [approved]
      properties: { approved: { type: boolean } }

interface:
  input:
    type: object
    required: [question]
    properties: { question: { type: string } }
  output: { ref: answer, from: react_ring }

entry: react_ring

stores:
  # LangGraph 单通道 messages + add_messages（多写者）→ 拆两槽单写 + 读侧合并
  - name: agent_turns
    type: message_log
    writer: agent           # 原 agent 节点写 messages
    lifecycle: run
    retention: { max_items: 64 }
  - name: tool_turns
    type: message_log
    writer: tools           # 原 tools 节点写 messages
    lifecycle: run
    retention: { max_items: 64 }

subgraphs:
  - name: react_body
    version: "1.0"
    entry: agent
    nodes:
      - id: agent
        kind: agent
        uses: { model: route.main@1, tools: [pkg.hopqa.search, pkg.hopqa.lookup] }   # bind_tools 对应物
        writes: [agent_turns]
        emits: { answer: answer, action: action_call }
        context:
          sections:
            - { from: template, template_ref: pkg.hopqa.react_system, quota_tokens: 500 }
            - { from: input, fields: [question], policy: project, quota_tokens: 200 }
            - { from: store, store: agent_turns, policy: full, quota_tokens: 3000 }
            - { from: store, store: tool_turns, policy: full, quota_tokens: 3000 }
          merge: { by: step_order }   # 读合并声明：替代 add_messages 写侧归并
      - id: tools
        kind: tool
        uses: { tool: pkg.hopqa.toolbench@1 }
        writes: [tool_turns]
        consumes: { action: action_call }
        emits: { observation: observation }
      - id: format_check
        kind: check          # 本语法新增要求：任何循环必须有验证面安全点（LangGraph 无此要求，属有意分歧）
        consumes: { observation: observation }
        emits: { checked: observation }
      - id: approve
        kind: human
        human: { station: review-desk, role: reviewer, quorum: 1 }
        resume:
          schema:
            type: object
            required: [approved]
            properties: { approved: { type: boolean } }   # interrupt(response_schema) 对应物
        consumes: { answer: answer }
        emits: { decision: approval }
    edges:
      - { from: agent, output: action, to: tools, input: action, checkpoint: true }
      - { from: tools, output: observation, to: format_check, input: observation, checkpoint: true }
      - { from: agent, output: answer, to: approve, input: answer }

selectors:
  - id: after_approve
    at: approve
    default: exit            # END 对应物
    rules:
      - when: "resume.approved == false"
        goto: agent          # 打回：回环体重启（Command(goto=...) 的声明式对应）

nodes:
  - id: react_ring
    kind: loop
    loop:
      body: react_body
      max_iterations: 25     # recursion_limit=25
      carried:
        - { store: agent_turns, max_items: 64 }
        - { store: tool_turns, max_items: 64 }
      safety_points:
        - { node: format_check, kind: check }
      exit_when: "resume.approved == true"
      on_exhausted: fail     # GraphRecursionError 对应物 → 终态 failed
    emits: { answer: { from_body: agent.answer } }

edges: []

budgets:
  - { id: turns_cap, dimension: turns, scope: loop:react_ring, cap: 50 }

failures:
  - class: transport_transient
    retry: { max: 3, backoff_ms: 800 }   # RetryPolicy 对应物（分类维度=语义类别）
  - class: environment_failure
    retry: { max: 3, backoff_ms: 60000 }
  - class: budget_exhausted
    terminal: true
    outcome: failed
```

两处**有意分歧**（写入 §8 取舍）：① reducer 语义改写合并（收益：INV-2 静态化；代价：顺序控制移到视图 `merge`）；② 循环必须带验证面安全点（LangGraph 的环可以裸奔，我们的环必须可验收）。

### 4.11 样例自检记录

10 个样例的 YAML 块已全部通过 `yaml.safe_load` 解析自检（抽取自本文档代码块逐块解析，0 语法错误）；CEL 表达式全部落在保守子集（比较/布尔/整数算术/`in` 字面量列表，零方法调用），与 cel-interpreter 0.10 支持面一致（`af-graph/src/predicate.rs` 通道）。运行时绑定名均在 §1.3 词汇表内。正式的编译器红绿测试（含每条 L0 规则的拒绝用例）按 ADR-007 在 af-dsl 落地时补齐，本文档的判定规则是其规格来源。

---

## 5. 四条 L0 不变量的编译期判定规则草案

判定位置：af-dsl 前端静态 pass（ADR-002 crate 职责："L0 不变量静态判定"）。以下每条给：规则 → 静态检查 → 违规样例 → 预期错误。

### INV-1 上下文完整性

**规则**：agent 节点的上下文 = 且仅 = 其 `context.sections` 声明的来源（+策略+配额）；sections 引用的 store/入边端口/arg/模板必须存在且在本节点可读集合内；模板槽位必须被某个 section 绑定（承 af-harness `placeholders`/`UnknownSlot` 校验语义）。agent 节点不得使用 `reads` 直读。

**检查**：引用闭包扫描（store 名、edge 端口名、arg 名、template_ref）+ store.readers 核对 + 槽位闭合。

违规样例（E2301 + E2303）：

```yaml
stores:
  - { name: reflections, type: collection, item: reflection_note, writer: reflector, readers: [], ... }
nodes:
  - id: actor
    kind: agent
    context:
      sections:
        - { from: store, store: reflexions, policy: retrieve, args: { k: 2 }, quota_tokens: 700 }   # E2301：拼写悬空
```

预期错误风格：
`E2301 dangling_context_source: node 'actor' section[2] references undeclared store 'reflexions'（最近候选 'reflections'）`
若 store 存在但 `readers` 不含该节点：`E2303 context_read_denied: store 'reflections' readers [] does not include node 'actor'`。

### INV-2 写入串行化

**规则**：每个 store 恰有一个写者（`writer` 声明与所有节点 `writes[]` 并集一致且势=1）；map 体子图内节点不得写体外套管 store（N 实例=N 写者）；一节点写多槽合法；循环携带槽的写者也必须唯一。

**检查**：writer 唯一性扫描 + map/loop 体作用域闭包分析。

违规样例（E2311 / E2312）：

```yaml
stores:
  - { name: transcript, type: collection, item: turn_record, writer: collector, ... }
nodes:
  - id: debater            # map 体 one_turn 内
    kind: agent
    writes: [transcript]   # E2312：map 体节点写共享槽
```

预期错误风格：
`E2312 map_shared_store_write: node 'debater' inside map body 'one_turn' writes shared store 'transcript'（N 并行实例将并发写；改由汇聚节点单写——见样例 7 collector）`
顶层双写者：`E2311 multiple_writers: store 'transcript' declares writer 'collector' but node 'debater' also writes it`。

### INV-3 生成器-验证器分离

**规则**：验证面 = kind ∈ {check, gate, human, evaluator}。验证节点不得同时是它所验证工件的产生者（consumes 的端口不得与自身 emits 的端口同源）；循环 `safety_points` 必须落在验证面节点（承 af-graph `SafetyPointKind`，扩展 evaluator）。

**检查**：safety_point kind 白名单；check/evaluator 节点的 consumes-emits 自环检测。

违规样例（E2321 / E2322）：

```yaml
nodes:
  - id: solver
    kind: check
    consumes: { patch: patch_ref }
    emits: { patch: patch_ref, verdict: verdict_type }   # E2321：emits 端口与 consumes 同源（自验证）
loop:                     # 某循环节点携带的构造字段
  safety_points:
    - { node: generator, kind: check }   # E2322：generator 是 agent，不在验证面
```

预期错误风格：
`E2321 self_verification: check node 'solver' emits port 'patch' which it also consumes（生成与验证必须不同节点）`
`E2322 safety_point_not_verifier: safety point 'generator' kind 'agent' not in {check, gate, human, evaluator}`。

### INV-4 评估器外部化

**规则**：评估/判定实现必须绑定外部组件（`uses.unit` 指向 packages 内判定单元），不得出现在候选侧 agent 的 `uses.tools` 中；评估输入槽（参考答案、分数记录）的 `readers` 与候选节点集合的交集必须为空。

**检查**：evaluator/check 的 uses 解析目标类别（组件 class=判定单元）+ store.readers × 候选节点（loop/map 体内在册 agent）求交。

违规样例（E2331 / E2332）：

```yaml
stores:
  - { name: answers_ref, type: collection, item: answer, writer: loader, readers: [assess, gen_a], ... }   # E2331
nodes:
  - id: solver
    kind: agent
    uses:
      tools: [pkg.searchkit.assess]   # E2332：评估器组件进了候选工具集
```

预期错误风格：
`E2331 eval_input_visible_to_candidate: store 'answers_ref' readers include candidate node 'gen_a'`
`E2332 inline_evaluator: agent node 'solver' tool 'pkg.searchkit.assess' resolves to evaluator-class component（评估器必须外置为 evaluator/check 节点）`。

---

## 6. 错误码命名空间草案

沿用 af-graph E2xxx 四位风格与 poc-cue 装载器四层分类学（E0 信封 / E1 形状 / E2 语义 / E9 部署期；ADR-001 §4）。**码随域走、跨 crate 不重号**：E2001–E2007 已由 af-graph 图域占用，本方案只在其相邻段分配新码段。

| 码段 | 域 | 归属 | 首批码 |
|---|---|---|---|
| E0001–E0099 | 信封（版本/信封未知键） | af-dsl | E0001 缺 version；E0002 version 非整数；E0003 version 不识别（非匹配即整份拒绝）；E0004 信封未知键 |
| E1001–E1099 | 形状（serde/deny_unknown_fields 映射） | af-dsl | E1001 未知字段；E1002 缺必填字段；E1003 类型不符；E1004 枚举值非法；E1051 CEL 解析失败（含 cel-parser panic 兜底归一，承 `PredicateError::Compile`） |
| E2001–E2007 | 图域既有 | af-graph | **不重新分配**（悬空引用/值域/重复 id/非空/环/孤立/map 体未版本化） |
| E2101–E2199 | 拓扑扩展域 | af-dsl | E2101 selector 缺 default；E2102 map.over 解析为非集合类型；E2103 loop/map args 引用悬空；E2104 子图端口契约不匹配（inputs/outputs 与引用方不符） |
| E2201–E2299 | 契约域（L1） | af-dsl | E2201 边两端端口类型不匹配；E2202 输出类型多射且未 `from` 点名；E2203 谓词引用未知绑定；E2204 失败类未知/路由目标不存在；E2205 信封 schema 非法；E2206 同端口多入边不可证不相交；E2207 预算 cap 非正/作用域悬空 |
| E2301–E2399 | 不变量域（L0） | af-dsl | E2301 上下文来源未声明；E2302 模板槽位未绑定；E2303 上下文读越权；E2311 多写者；E2312 map 共享槽多写；E2321 自验证；E2322 安全点非验证面；E2331 评估输入对候选可读；E2332 评估器内联 |
| E2401–E2499 | 上下文域 | af-dsl | E2401 视图策略未知；E2402 配额非正（`policy: none` 的 0 除外）；E2403 merge 声明非法/无配额段 |
| E2501–E2599 | 绑定域（L3/L4） | af-dsl | E2501 组件/包引用缺失；E2502 版本不符；E2503 逃逸舱缺记账字段；E2504 impl_ref 不可解析 |
| E9001–E9099 | 部署期 | af-execline / af-plan | E9001 装载期组件解析失败；E9002 digest 不匹配（对齐落地契约 §2.2 拒绝式装载） |

错误消息契约（ADR-007 §3）：稳定码 + 精确信息（码名蛇形 + 位置 + 最近候选/期望集合），格式见 §5 各例。

---

## 7. 与 af-graph / AgentSpec 的复用与扩展关系

### 7.1 直接复用（不改一字段）

| af 资产 | AFD 中的位置 |
|---|---|
| `GraphTemplate.graph_version/name/entry` | 文档版本纪律与 `entry` 段 |
| `Node.kind` 开放 String + 首发四型思路 | kind 开放词表（DSL 注册 agent/evaluator/loop/map 等扩展 kind，不改 schema） |
| `HumanSpec{station, role, quorum}` | human 节点构造字段 |
| `MapSpec{body, over, max_fanout}` | map 构造三字段原样（含"体必须版本化"校验，E2007 承接） |
| `Edge{from, output, to, input}` 四字段工件引用语义 | 边段主干 |
| `SubGraph{graph_version, entry, nodes, edges}` | 子图段主干（版本缺失=草稿不可被引用） |
| `ControlledLoop` 骨架：body/max_iterations/carried 有界/safety_points | loop 构造核心 |
| `SafetyPointKind` | 安全点 kind 白名单（扩展 evaluator 一值） |
| af-graph CEL 通道（`Predicate::compile/eval` + catch_unwind 兜底） | 一切 `when/exit_when/assert/rules` 谓词的编译与求值后端 |
| `AgentSpec` 四元组（EndpointSpec/ContextTemplate/ToolDecl/Policy） | **agent 节点的编译目标**：`uses.model`+`context`+`uses.tools`+`budgets/stop/failures` 四段各自降维到四元组（含 `StopCondition.completion_signals`/`tool_free_turn_limit` 快路径与 `BudgetRef{dimension, per_turn, unit}`） |
| `ToolDecl.effect`（Pure/Persist/ExternalOnce） | 包工具声明的副作用分类（写端口绑定由此推导） |
| af-dspy-ir 拒绝式信封（`version` + deny_unknown_fields + 非匹配即拒） | 文档信封纪律 |

### 7.2 扩展（在既有类型上加可选字段，需新校验码）

| 类型 | 扩展 | 动用的码 |
|---|---|---|
| `Edge` | `when`（CEL 守卫）、`handoff: envelope`、`checkpoint: true`、`signal: true` | E1051/E2201/E2205 |
| `ControlledLoop` | `args`、`exit_when`、`on_exhausted`；`carried_state` 列表化（多槽） | E2103/E2104 |
| `SubGraph` | `inputs[]`、`outputs{}`（含 `from_arg` 直通端口） | E2104 |
| `StopCondition` | CEL 谓词通 道（completion_signals 保留为编译快路径） | E2203 |
| `Policy`/`BudgetRef` | budgets 段 → 多维多作用域 BudgetRef 实例集 | E2207 |

### 7.3 新建（af-dsl 自有类型，IR 第一接口原则下的语法层资产）

文档信封与 meta；`types/interface`（含 `envelope<T>`）；`stores`（writer/readers/lifecycle/retention——L0/L1 的核心新概念，af 仓无对应物）；`context.sections` 视图策略族（补 LangGraph G6）；`selectors`；`failures` 分类账（补 G5）；`escape_hatches` 记账；`packages` 引用表。**原则**：语法可换、IR 慎改（宪法 C5）——本提案全部新概念先在 af-dsl AST 定型，降维进 IR 时与 af-plan 可执行计划对象（落地契约 §7）逐字段对齐。

---

## 8. 已知设计取舍与开放问题

### 8.1 取舍（本提案主动选择并接受代价）

1. **语法面偏大**（15 顶层段、7+2 节点 kind、9 类上下文策略）：覆盖度优先的直接代价。与提案 B 竞争时，判据应是"15 目标的机制落点是否自然可读"而非段数；若 B 能以更小面达到同等覆盖，A 的额外面应砍。
2. **写合并 → 读合并**（LangGraph reducer 分歧）：多写者通道改单写者槽 + `context.merge` 读侧合并。收益：INV-2 从运行期异常（`InvalidUpdateError`）提前为编译期拒绝；代价：消息顺序控制从通道语义移到视图声明，`merge.by` 词表（首版仅 `step_order`）可能不够用。
3. **CEL 保守子集**（零方法调用、聚合预计算）：可静态校验、跨引擎可移植；代价：稍复杂的运行时判定要么进 transform 预计算、要么进 L4（记账）。
4. **循环必须带验证面安全点**：所有环都是受控环（承 af-graph 纪律）；代价：LangGraph 式"裸环"不可写，样例 10 需补一个 format_check。
5. **订阅式触发未进核心**（MetaGPT `_watch`/`cause_by` 激活）：用静态边 + envelope 血缘近似；代价：角色×产物矩阵大时边数增长，声明式订阅是后续可加的表层特性（LangGraph 报告 G8 同判）。
6. **语义终止不进核心**：LLM 判停（"我认为完成了"）只能是 `llm_predicate` 逃逸；可数值化的终止（如 MemGPT"无函数调用即停"）已声明式覆盖。
7. **匿名化乱序必须种子化**（`shuffle_seeded.seed_ref`）：可复现纪律优先；不可复现随机=逃逸。
8. **map 静态有界**：`over` 运行时定基数但拓扑静态；LangGraph `Send` 式任意动态扇出、运行时改拓扑（辩论加减辩手）一律 L4。
9. **check 节点可写自己的判定记录槽**（Reflexion attempts_log）：判定记录是验证面的自然产物，不违反 INV-3（它不写被验工件）；边界在 §5 判定规则中显式化。

### 8.2 开放问题（交提案评审/后续 ADR）

1. `version`（文档信封）与 `graph_version`（图模板）双版本键的绑定关系：编译产物是否要求两者同时递增？
2. 逃逸舱 `share_budget_pct` 的口径：声明值 vs 实测值（健康度报表）谁触发 30% 警戒；编译期是否拒绝 >50% 的配方。
3. `budgets.cents` 的 per-turn 换算与供应商计量差异（落地契约 §5.3 voucher 缺口同源）：预算声明与账本真相的 reconcile 规则。
4. human 节点 `resume` 之外的中断/抢占语义（任意点挂起、副作用不回滚）是否需要独立构造，还是维持"边界处暂停 + L4 抢占"。
5. `context.merge.by` 词表扩充（step_order 之外是否需要 by_priority/by_selection）与配额溢出时的段级淘汰规则。
6. 选择器 default 的"集中式编排+验证瓶颈"是否要固化为一个内建 fallback 模板（golden 提供）而非仅规范推荐。
7. 订阅式触发（5）与动态收件人若进入核心，E21xx 需要新增哪些码。
8. `types` 内联 JSON Schema 与 packages 内 schema 的去重/引用规则（同 schema 双处定义的 digest 一致性）。
9. loop `args` 隐式边与显式边的优先级/冲突裁决。
10. Agensh/DeLM 卡为低置信改写（INDEX.md 备注），其对 handoff/swarm 面的覆盖判断待补卡后复核。

---

## 附：本提案的证据锚点

- 对齐机制卡 15 张：`计划/研究组/对齐机制卡/`（ReAct/Reflexion/Voyager/SWE-agent/MemGPT/MetaGPT/GPTSwarm/AFlow/Multi-Agent-Debate/LangGraph-StateGraph/AutoGen-Team-JSON/CrewAI-YAML/CAMEL/ADAS/Agensh-DeLM）——各卡"⑥ DSL 表达点清单"的 (a) 项即本文 §3/§4 的需求来源，(b) 项即 §8 逃逸归类来源。
- 缺口需求：`DSL-G0-表达力-langgraph.md` §6（G1–G8）、`DSL-G0-表达力-autogen.md` §3（缺口 1–8）、`DSL-G0-表达力-crewai.md` §3（缺口 1–8）。
- 复用 schema：`af/crates/af-graph/src/model.rs`（GraphTemplate/Node/HumanSpec/ControlledLoop/CarriedState/SafetyPoint/MapSpec/Edge/SubGraph）、`af/crates/af-graph/src/validate.rs`（E2001–E2007）、`af/crates/af-graph/src/predicate.rs`（CEL 通道）、`af/crates/af-harness/src/spec.rs`（AgentSpec 四元组/信封/槽位校验）、`af/crates/af-dspy-ir/src/model.rs`（version 信封）。
- 裁决：ADR-001（YAML+CEL+逃逸舱）、ADR-002（crate 划分）、ADR-007（错误码契约与红绿纪律）；落地契约 v0（`计划/研究组/落地契约-v0.md`）§2.2/§5/§6/§7。
