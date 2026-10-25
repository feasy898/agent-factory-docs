# Agent 定义 DSL 语法规范 v0.1 · 提案 B（编译器简单性 / IR 直映优先）

> 身份：第二阶段 DSL-Compiler 团队 · 语法代理 B（竞争提案，与提案 A 按「对齐覆盖度 + 编译复杂度 + DX」择优合入）。
> 日期：2026-10-24。语言代号：**AFB**（Agent Flow Blueprint）。
> 输入依据：15 张对齐机制卡（`计划/研究组/对齐机制卡/`）、DSL-G0 三框架表达力报告（langgraph/autogen/crewai）、af 四 crate schema（af-graph `model.rs`/`validate.rs`/`predicate.rs`、af-harness `spec.rs`、af-dspy-ir `model.rs`）、poc-cue 装载器错误分类学（`af/poc/poc-cue/verify-load/loader/src/error.rs`）、落地契约 v0、ADR-001/002/007、提案 A（`计划/研究组/DSL-语法提案-A.md`，可引用不必跟随）。
> 本文件为任务书授权的唯一写入文件；未修改任何现有文件，未建任何仓。

---

## 0. 设计立场：四条取舍纪律

提案 A 的立场是对齐覆盖度优先（15 顶层段、9 类节点 kind、选择器与预算/停止/失败各占一段）。**本提案的立场是编译器简单性与 IR 直映优先**：每一个语法构造都必须落在工作区已有的 IR 类型上，或折算成一个可计数的最小扩展；能做成节点上的正交构造字段，就绝不新开顶层段。四条纪律：

| # | 纪律 | 具体含义 | 反证（A 的做法） |
|---|---|---|---|
| **B-R1** | **IR 直映** | 语法段的字段与 af 仓 Rust 结构体一一对应；新增 IR 概念进"改动预算表"（§3.4）逐条记账，宪法 C5「语法可换、IR 慎改」 | A 的 15 段中 `interface`/`selectors`/`failures` 各引入一套自有名词，与 af-graph 的 entry/Edge/ControlledLoop 语义重叠但不同形 |
| **B-R2** | **正交构造优先** | 人工/循环/扇出/路由/逃逸全部是**节点上的构造字段**，与 kind 正交——直接承 af-graph `model.rs:37-51` 注释「人工/循环/map 是节点上的一等构造字段，与 kind 正交」 | A 把 human/loop/map 提为 9 类 kind 之一，把逃逸舱提为独立顶层段 |
| **B-R3** | **控制流三原语** | 一切控制流收敛为：固定边（数据流）/ `route` 构造（多路路由）/ `loop.exit_when`（环出口）。**边上没有 `when` 字段**——路由只有一处语法、一处归一化算法 | A 的边可带 `when` 守卫又有 `selectors`，两套路由机制需要互斥可证性分析（其自述 E2206「可证性由选择器分支分析给出」，实为手工推导） |
| **B-R4** | **一次收齐 + 稳定码** | 校验器一次报完全部违例（承 af-graph `validate.rs:246-279`、af-dspy-ir `validate.rs:13-244`）；错误码四层分类学 E0/E1/E2/E9（承 poc-cue `error.rs:1-11`），E2001–E2007 由 af-graph 图域占用、本方案**不重新分配** | A 亦持此纪律，B 与之相同（此项非分歧点） |

硬边界不退（ADR-001 及使命指令）：

1. **YAML 主干 + CEL 谓词**：一切运行时谓词（停止/门控/路由/环出口/安全点断言）= CEL 表达式，编译期 `Program::compile`、无副作用；Python 不进 L0–L3 任何语法层，只在 L4 逃逸舱（`escape` 构造）且显式记账（ADR-001 §3）。
2. **语言核心零领域名词**：核心七段不出现 git/终端/代码/视频等领域词；领域具体性全部住在包引用里（`pkg.<包>.<名>` 与 `route.<名>@<版本>` 是包产物不是核心词表）。机器检查口径：删掉全部 `pkg.*`/`route.*` 引用后，核心 golden 样例自洽可编译（§4.7 自检含此步）。
3. **类型化受限**：无图灵完备、无副作用、可静态校验。CEL 取**保守子集**：只允许比较、布尔组合、整数算术、`in` 字面量列表，**零函数/方法调用**——该纪律由 cel-parser 0.10.1 的 `ExpressionReferences`（`~/.cargo/registry/src/*/cel-parser-0.10.1/src/references.rs:37-49`，`functions()`/`variables()` 两个集合）做**静态集合包含判定**，不手写解析器（§1.4）。
4. **拒绝式版本信封**：`version: 1` 顶层键；缺键/非整数/非 1 → 整份拒绝、不解析 body（承 af-dspy-ir `Program.version` 与 af-harness `decode_spec` 双先例，`af-harness/src/spec.rs:180-214`）。全文所有结构 `deny_unknown_fields`。

**B 相对 A 的净简化**（一句话动机）：A 用 15 段 + 9 kind 表达同一批机制；B 用 **7 个顶层段 + 6 个正交构造字段**表达，且全部控制流只有一个归一化算法（§1.5），内联体让「悬空循环体 / 未版本化 map 体」两类违例在语法面**不可表示**（§2.3）。

---

## 1. 语法总览

### 1.1 顶层结构树（7 段）

```
AFB 文档（YAML，拒绝式信封；全文 deny_unknown_fields）
├── version: 1          # 信封键：非 1 整份拒绝（E0001/E0002/E0003）；信封未知键 E0004
├── meta                # 身份 + 入口 + 整图 I/O 契约（input/output 折进类型表引用，不新开段）
├── types               # 工件/信封/输入 schema 登记：跨节点契约的类型词典（L1）
├── stores              # 状态槽：类型 + 单写者 + 生命周期 + 有界保留（L0/L1）
├── nodes               # 节点：kind(四型) + uses + emits/writes/reads + context + 六构造字段
├── edges               # 类型化工件边：from.output→to.input + checkpoint（IR 1:1，无 when）
└── policies            # budgets[] + stop[] + failures[] 三账合一（L1 执行契约）
```

节点上的**正交构造字段**（不占顶层段，承 af-graph `model.rs:37-51`）：

```
nodes[].loop    # 受控循环：体（内联 nodes+edges）+ 上限 + 携带 + 安全点 + 出口
nodes[].map     # 扇出：体（内联）+ over（运行时定基数）+ max_fanout
nodes[].human   # 人工工位：station/role/quorum + resume.schema（类型化恢复值）
nodes[].route   # 多路路由：有序 CEL 规则 + 必填 default（编译期归一化为边守卫）
nodes[].escape  # L4 逃逸舱：impl_ref + 记账四字段（ADR-001 §3）
nodes[].ops     # transform 算子弟表：闭环词表 + 参数闭合
```

### 1.2 各段字段速览 + IR 字段映射表

#### `meta` —— 身份与边界契约

| DSL 字段 | 说明 | IR 落点 | 新增/复用 |
|---|---|---|---|
| `name` | ref 名（承 af-harness `is_ref_name`：字母数字 `_.:-`，≤128，`spec.rs:14/294-296`） | `GraphTemplate.name` | 复用 |
| `graph_version` | 图模板版本，一等键（承 af-graph `model.rs:22-23`） | `GraphTemplate.graph_version` | 复用 |
| `entry` | 入口节点 id | `GraphTemplate.entry` | 复用 |
| `input` | 整图输入契约 = `types` 表中的类型名（**不新开 interface 段**） | `InterfaceSpec.input_type` | 新增结构体（3 字段） |
| `output` | `{ref: <类型名>, from: <节点 id>}`——终态工件与唯一发射者（必填 `from`，不做推断） | `InterfaceSpec.output_type/output_from` | 同上 |
| `intent` | 审计/检索用自由文本 | 计划对象元数据 | 复用（`node_exec`/plan 元数据） |

#### `types` —— 类型词典

```yaml
types:
  - name: answer                    # 类型名（doc 唯一）
    schema:                         # JSON Schema 对象（内联，唯一 schema 家）
      type: object
      required: [final, supports]
      properties:
        final: { type: string }
        supports: { type: array, items: { type: string } }
```

- 端口/store 元素类型只能是：`类型名` | `list<类型名>` | `envelope<类型名>` | 内联**原始类型**（`{type: string|integer|boolean|number}`）| 内建 `signal`（零载荷排序令牌）。
- `envelope<T>` 是内建泛型 = `{payload: T, from_node: string, artifact_type: string, step: integer}`——typed handoff 的血缘位（MetaGPT `cause_by` 的对应物、LangGraph G7 缺口的填补）。**它是类型不是边标记**：端口写 `envelope<prd>` 即信封，血缘由运行时包装器填，编译期只核类型。
- 对象 schema 必须住 `types` 表；端口上写内联对象 schema → E1003（一个 schema 一个家，消重争议进 §8 开放问题）。
- IR：`TypeTable = BTreeMap<String, Schema>`（新增，词典而已）。

#### `stores` —— 状态槽（L0 判定对象）

| DSL 字段 | 说明 | IR 落点 |
|---|---|---|
| `name` | 槽名（所在作用域唯一） | `StoreSpec.name` |
| `type` | `message_log` \| `document` \| `collection` \| `kv` \| `vector_index` | `StoreSpec.kind` |
| `item`/`value` | collection/vector_index 的元素类型 / kv 的值类型（`types` 表名） | `StoreSpec.item` |
| `writer` | **唯一写者**：节点 id 或点号路径（经 loop/map 体逐层解析） | `StoreSpec.writer: NodePath` |
| `lifecycle` | `run`（本计划执行）\| `iteration`（每次迭代重建）\| `persistent`（跨执行持久） | `StoreSpec.lifecycle` |
| `retention` | `{max_items}` \| `{max_bytes}` \| `{policy: rolling_window, max_items, keep_system?}`——**至少一个上界**（承 af-graph `CarriedState::is_bounded`，`model.rs:90-95`） | `StoreSpec.retention` |
| `eval_input` | 可选 `true`：本槽存评估 ground truth，读者受限（INV-4 判定对象） | `StoreSpec.eval_input` |

**读权限在消费者侧声明，不在 store 侧**：agent 类节点经 `context.sections`（INV-1），其余节点经 `reads[]`。这是对 LangGraph 少数真声明式机制的继承——G0 报告证实其「节点输入按 schema 的运行时过滤」是源码级真过滤（`DSL-G0-表达力-langgraph.md` §1 attach_node 行），B 把读侧声明留在消费者，store 只保住「单写者」这一条硬约束。`readers` 字段因此被删除（A 有），INV-4 改由引用扫描判定（§5）。

#### `nodes` —— 节点

| DSL 字段 | 说明 | IR 落点 |
|---|---|---|
| `id` | 所在作用域唯一（根图或某个 loop/map 体）——承 af-graph `validate.rs:291-301` | `Node.id` |
| `kind` | **四型**：`task` \| `gate` \| `check` \| `transform`（af-graph `kind` 模块首发四型原样，`model.rs:9-17`）；开放 String——未注册 kind 只进 `unknown_kinds` 诊断集合不拒绝（承 `model.rs:6-8`），但不得携带任何构造字段（E1005） | `Node.kind` |
| `uses` | 组件绑定：`{model?: route 引用, tools?: [pkg 引用], tool?: pkg 引用, unit?: pkg 判定单元引用, memory?: [引用]}`——**LLM/工具/评估器的分野在 uses 不在 kind**（IR 直映：`node_exec.components`，落地契约 §7.1） | `NodeExec.components` + `AgentSpec` |
| `emits` | `{端口: 类型}` 输出端口契约（L1） | `artifact_contract`（`node_exec`，落地契约 §7.1） |
| `writes` | 可写 store 名（INV-2 判定对象） | `StoreSpec.writer` 交叉核对 |
| `reads` | 直读 store 名（仅非 LLM 节点；LLM 节点声明即 E2303） | `NodeExec` 读侧投影 |
| `context` | `{sections: [...]}`——**仅 LLM-bound task 可用**（INV-1 判定对象） | `AgentSpec.context_template` + 组装计划 |
| `ops` | transform 算子弟表（仅 kind=transform） | 组件绑定（内置算子族） |

kind × uses 的判别表（编译器简单性的关键：**语义分工在绑定侧，kind 保持 af-graph 四型不变**）：

| kind | uses 形态 | 语义 | 编译目标 |
|---|---|---|---|
| `task` | `model` | LLM agent 节点 | `AgentSpec` 四元组（endpoint/context_template/toolset/policy） |
| `task` | `tool` | 工具执行节点 | `node_exec.components.tools` 单项 |
| `task` | 无 uses + `escape` | L4 逃逸节点 | `EscapeSpec` + `node_exec` |
| `task` | `loop`/`map`/`human` 构造 | 控制/人工节点 | `Node.loop_spec/map_spec/human` 原样 |
| `gate` | 无 uses，带 `assert` CEL | 门控（验证面，内建 `passed: boolean` 端口；**出边无隐式守卫**，分支经 `route`） | `Node` + 守卫 |
| `check` | `unit`（外部判定单元） | 验证/评估节点（验证面，内建 `passed` 端口） | `node_exec.unit` |
| `transform` | 无 uses，带 `ops` | 零状态数据算子 | 内置算子组件绑定 |

#### `edges` —— 类型化工件边

```yaml
edges:
  - { from: pm, output: prd, to: architect, input: prd }              # 端口类型 envelope<prd> 即信封
  - { from: agent, output: action, to: tools, input: action, checkpoint: true }
```

四字段 `from/output/to/input` 与 af-graph `Edge`（`model.rs:127-137`）**逐字一致**；唯一扩展是可选 `checkpoint: true`（LangGraph checkpointer 的声明位，快照语义由 af-plan 承载）。**没有 `when` 字段**——条件路由全部走 `route` 构造（B-R3）。边类型核对：生产者端口类型必须存在（E2201）；消费者若声明 `consumes: {端口: 类型}` 则两端必须相等（E2201）；端口名集合 = 消费者的 `inputs.*` CEL 绑定。

#### `policies` —— 三账合一

| 子表 | 字段 | IR 落点 |
|---|---|---|
| `budgets[]` | `{id, dimension, scope, cap}`；dimension ∈ `turns\|model_calls\|tokens_in\|tokens_out\|tokens_total\|tool_calls\|cents\|clock_ms`；scope ∈ `plan\|node:<id>\|loop:<id>\|map:<id>`；cap>0 | `BudgetRef{dimension, per_turn, unit}` 实例集（af-harness `spec.rs:133-138`）+ 计划级 budget 段（落地契约 §5.2）；`cap` 为 `BudgetRef` 新增可选字段 |
| `stop[]` | `{when: CEL, outcome: completed\|failed\|escalated_human}` | `StopCondition` 快路径（completion_signals/tool_free_turn_limit，`spec.rs:120-128`）+ CEL `Predicate` 通道（af-graph `predicate.rs`） |
| `failures[]` | `{class, retry?, route?, feedback?, fallback_route?, terminal?, outcome?}`；class 闭环词表 `transport_transient\|environment_failure\|schema_invalid\|tool_error\|timeout\|gate_refused\|budget_exhausted\|policy_stopped\|unauthorized`（前三类对齐落地契约 §6.2 四分类，后三者对齐 af-harness 终态轴） | `FailureEntry`（新增小结构体）→ `node_exec.retry` |

三表合段的理由（编译器简单性）：三者形状同构（记录表 + CEL 谓词 + 闭环词表）、校验同构（引用闭包扫描）、落点同域（`node_exec.budget/retry` + `StopCondition`）；合成一段少两个 AST 节点、两个校验 pass、两个顶层名字。

#### 节点 `context.sections` —— 上下文装配（INV-1 判定对象）

顺序即拼接顺序；每段 `quota_tokens` 必填（有界上下文）：

| `from` | 字段 | `policy` |
|---|---|---|
| `template` | `template_ref`（包内模板）、`vars?: {名: 字面量或 arg.*/input.* 引用}` | — |
| `input` | `fields[]`（须 ∈ `meta.input` schema） | `project` |
| `arg` | `name`（loop args / map 隐式 `item`）、`fields?` | `project` |
| `edge` | `port`（入边端口名）、`fields?`、`optional?: true` | `project` |
| `store` | `store`、`args?` | `full` \| `latest_k{k,redact?}` \| `retrieve{component,k}` \| `summarize{component}` \| `none` |

**内建合并规则（零字段）**：同一节点上下文中的多个 `message_log` 段按 `step` 序交错合并，其它类型按段声明序拼接。这条内建规则就是 LangGraph `add_messages` reducer 的 B 对应物——**写侧归并改写为读侧交错**（A 需显式 `merge: {by: step_order}` 字段；B 内建，因为交错序只有一种合理语义，不值得一个语法位）。

### 1.3 正交构造字段速览

**`loop`**（承 af-graph `ControlledLoop`，`model.rs:69-78`，三扩展；loop 节点另自带 `done: signal` 端口）：

| 字段 | 说明 |
|---|---|
| `body` | `{nodes: [...], edges: [...]}` **内联体**（entry = nodes 首元素；降维时生成命名子图，见 §3.2） |
| `max_iterations` | 迭代上限 >0（E2002） |
| `carried[]` | `{store, max_items?, max_bytes?}`——**必须覆盖「体内（含嵌套体）节点写入的、声明在体外的全部 store」**（E2211）；至少一个上界（E2002） |
| `safety_points[]` | `{node: <点号路径>, kind: check\|gate\|human}`（承 `SafetyPointKind` 三值原样）；路径从**体根**解析，可穿嵌套体（如 `acquire.admit`） |
| `args?` | `{形参: 节点.端口[.字段] \| input.字段}`——体形参绑定，同时构成隐式依赖边（计 DAG） |
| `exit_when?` | CEL，真则退出 |
| `on_exhausted?` | `continue` \| `fail` \| `keep_best` |

**`map`**（承 af-graph `MapSpec`，`model.rs:116-124`，原样三字段）：`body`（内联）、`over`（`节点.端口` 或 `input.字段`，须解析为 list，E2104）、`max_fanout?`。体经隐式形参 `item` 收元素；节点 emits 的 `from_body` 端口自动包 `list<>`；体内节点可声明 `consumes: {item: <元素类型>}` 收隐式入边；map 节点同样自带 `done: signal` 端口。

**`human`**（承 af-graph `HumanSpec`，`model.rs:55-64`，一扩展）：`{station, role, quorum?, resume: {schema}}`——`resume.schema` 是类型化恢复值（LangGraph `interrupt(response_schema)` 的对应物，G0-langgraph.md §1 interrupt 行）。

**`route`**（B 新增构造，IR 落点 = `Edge.guard`）：`{default: <节点 id 或 exit>, rules: [{when: CEL, goto: <节点 id 或 exit>}]}`。`default` 是必填字段（缺 → E1002，serde 层即拒，不进语义 pass）。语义与归一化算法见 §1.5。

**`escape`**（L4，ADR-001 §3）：`{impl_ref, reason, owner, share_budget_pct}`，四字段缺一 → E2210。`impl_ref` 是包内路径（Python 实现住在包里，不进语法层）；占比 >30% 警戒是运行期健康度指标，编译期只验字段闭合。

**`ops`**（transform 算子弟表，闭环词表）：`project{port,into,fields?}`、`merge{ports,into}`、`slice{port,into,k}`、`anonymize{port,into,drop}`、`shuffle_seeded{port,into,seed_ref}`、`truncate{port,into,max_tokens_each}`、`tally{port,by,into}`、`select_best{port,by,prefer,into}`。管道语义（确定性、无搜索）：按文档序求值；每个 op 的 `port` 必须命名**入边端口、`reads` 中的 store、或前序 op 产生的中间产物**；`into` 命名一个新中间产物，或末端落点 = **emits 端口 / writes 中的 store**（末端落点二选一，E2209）。`shuffle_seeded` 无 `seed_ref` → E2209（可复现纪律：无种子随机不进核心）。**编译期核对 ops 的输入侧形状与参数闭合；输出侧字段映射由组件契约在装载期核对（E9003）**——这是 B 有意划掉的编译器复杂度（§8 开放问题 1）。

### 1.4 CEL 绑定词汇表与保守子集（编译期静态判定）

绑定以结构化值注入（点号 = 成员选择）：

| 绑定 | 字段 | 可见范围 |
|---|---|---|
| `steps` | `turns`、`tool_free`、`tool_calls_last_turn`、`iterations` | 全局 |
| `budget` | `<dimension>_spent` / `<dimension>_cap` | 全局 |
| `last_tool` | `name`、`first_line`、`ok` | 全局 |
| `last_message` | `has_tool_calls` | 全局 |
| `input` | `meta.input` schema 展开 | 全局 |
| `resume` | human 节点 `resume.schema` 展开 | 从当前作用域向外**第一个**带 human 构造的节点 |
| `attempt` | 体内**验证面节点**（check/gate）的内建 `passed` 与显式 emits 端口 | loop 的 `exit_when`（取最近一次验证输出） |
| `item` | map 元素 | map 体内 |
| `inputs` | 本节点入边端口集（gate 的 `assert`、transform 的 ops 参数） | 节点自身 |
| `<节点 id>` | 该节点 emits 端口 + 内建 `passed`（对象端口可继续点字段） | 从当前作用域向外逐层解析，**内层优先**；route 规则的可见范围含节点自身（可写 `qa.passed` 亦可写裸 `passed`） |

**保守子集静态判定**（两条集合包含检查，零手写解析器）：

```rust
// af-dsl::cel（编译期，stage 1）
const OPERATOR_WHITELIST: &[&str] = &[
    "_==_", "_!=_", "_<_", "_<=_", "_>_", "_>=_", "_&&_", "_||_", "!_", "_+_", "_-_", "_*_", "_/_",
    "_%_", "@in",
];
pub struct CelCheck { pub roots: BTreeSet<String>, pub ok: bool }
pub fn check(source: &str, allowed_roots: &BTreeSet<String>) -> Result<CelCheck, Violation> {
    let program = Program::compile(source)                       // 解析失败 → E1051
        .map_err(|e| violation(E1051, e.to_string()))?;          // cel-parser 内部 panic 由 catch_unwind 兜底归一（承 af-graph predicate.rs:12-15 实测注记）
    let refs = program.references();                             // cel-parser references.rs:37-49
    for f in refs.functions() {                                  // 函数/方法调用一律拒绝
        if !OPERATOR_WHITELIST.contains(&f) { return Err(violation(E1052, f)); }
    }
    for v in refs.variables() {                                  // 根绑定必须在位置词表内
        if !allowed_roots.contains(v) { return Err(violation(E2203, v)); }
    }
    Ok(CelCheck { roots: refs.variables().into_iter().map(str::to_owned).collect(), ok: true })
}
```

算子白名单（实测归纳自 cel-parser 0.10.1 的 `functions()` 命名，§4.7 自检含逐算子验证）：`_==_ _!=_ _<_ _<=_ _>_ _>=_ _&&_ _||_ !_ _+_ _-_ _*_ _/_ _%_ @in`。谓词结果非布尔 → E1053（承 af-graph `PredicateError::NotBoolean`，`predicate.rs:27-28`）。

### 1.5 `route` 的归一化算法（互斥性与覆盖性由构造成立）

选择器（A 的做法）需要证明「规则两两不相交且并上 default 覆盖全部出边」——这是个分析问题。B 把路由做成节点构造字段后，归一化是**确定性重写**，无需分析：

```
给定节点 N 的 route：rules r_1..r_n（文档序）+ default d
  1. N 的出边集合 E_out（按 to 分组）
  2. rule i 的守卫：  guard_i  = when_i ∧ ¬(when_1 ∨ … ∨ when_{i-1})
  3. default 的守卫：guard_d  = ¬(when_1 ∨ … ∨ when_n)
  4. 边 N→t 携带的 guard = 命中 t 的**第一条**规则的 guard_i（或 default 的 guard_d）
  5. goto: exit 的分支不产生边
校验（全部静态、一次收齐）：
  E2101  N 存在出边未被任何规则/default 覆盖
  E2102  规则/default 的 goto 不是 N 的出边目标（也不是 exit）
  E2103  同一目标被多条规则命中（后中者不可达——请合并为 `A || B`）
```

性质：guard_1..guard_n, guard_d 两两不相交（构造性：第 i 条显式排除前 i-1 条）且并集为真（default 取全否）——**多路路由的互斥+覆盖不需要任何图分析**。这是 B-R3 的兑现处：删掉边上的 `when` 后，整个语言只有这一处产生条件边，也只有这一处需要正确性论证，而它被归一化算法免费保证。

---

## 2. 正交性论证：删掉每一段，哪个真实机制塌掉

反例全部取自 15 张机制卡的 ⑥(a) 清单与三框架 G0 缺口清单（编号见文末锚点）。

| 段/构造 | 删掉它 → 表达不了的真实机制 | 证据锚点 |
|---|---|---|
| `version` | 无拒绝式信封：CrewAI classic YAML 与 JSONC 双轨、字段漂移与文档空洞（guardrail/schema 零示例）直接重演；装载器无法在解析 body 前拒绝坏版本 | G0-crewai §3-8；ADR-001 裁决 4 |
| `meta` | 无 `graph_version`/`entry`：af-graph 图模板三必填字段无处落；内联体降维时没有可 stamp 的父图版本（§3.2）；配方随产品发行的版本管理无入口 | af-graph `model.rs:22-29` |
| `meta.input`（折进 meta 的 I/O 契约） | 无整图输入契约：`from: input` 段与 `map.over: input.字段` 失去类型源；AutoGen「`inputs:{topic}` 是唯一变量机制且是 kickoff 级常量」的断裂重演 | G0-autogen §2.3 D3；CrewAI 卡 ⑥b |
| `types` | 无类型词典：MetaGPT 的结构化工件契约（PRD/Design/TaskList/CodeFile/TestCase）无处安放；typed handoff 无类型可核；LangGraph G3「节点间更新不校验」、AutoGen 缺口 2「typed 契约断裂」重演 | MetaGPT 卡 ⑥a；G0-langgraph §1 校验行；G0-autogen §3-2 |
| `stores` | 无状态槽：INV-2 失去判定对象——Debate 的共享黑板、MetaGPT 的 repo 所有权、Voyager 的技能库/课程表持久化、MemGPT 的主/外分层、Reflexion 的 episodic buffer 全部不可表达；CrewAI「多写者冲突无任何字段」重演 | Debate/MetaGPT/Voyager/MemGPT/Reflexion 卡 ⑥a；G0-crewai §3-3 |
| `nodes` | 无节点即无拓扑：ReAct 单体、GPTSwarm「agent=图、边必须是一等声明式数据流」、ADAS 的多角色工件交接全部丢失 | ReAct/GPTSwarm/ADAS 卡 ⑥a |
| `edges` | 无工件引用边：MetaGPT SOP 流水线、LangGraph 数据流、CrewAI `context` 拉取、AFlow 算子间数据依赖全部丢失；af-graph `Edge` 语义无处落 | af-graph `model.rs:127-137`；G0-crewai §2.2 |
| `policies.budgets` | 无预算契约：ReAct 三重预算、SWE-agent 四维预算、AFlow 搜索预算、CrewAI「无 token/费用字段、只有事后 usage_metrics」重演；LangGraph G1「pregel.md 全篇无 budget 概念」重演 | G0-langgraph §6-G1；G0-crewai §3-6 |
| `policies.stop` | 无声明式停止：ReAct 的 finish 哨兵、Debate 的一致性早停、AutoGen 可组合 termination 家族失去落点；LangGraph「停止条件=路由代码」重演 | G0-langgraph §3.1；G0-autogen §2.1 |
| `policies.failures` | 无失败分类账：SWE-agent 的格式重述回灌、Reflexion 的重试、MetaGPT 的 QA 打回、AutoGen「失败分类=异常分类、无 taxonomy」重演 | G0-autogen §3-4；G0-langgraph §6-G5 |
| `loop` 构造 | 无环原语：ReAct 自环、Reflexion 双层环、MetaGPT QA 回环、AFlow 搜索环、GPTSwarm 批评-修订环、CrewAI「反馈环不可表达（致命缺口 2）」重演 | G0-crewai §3-2；五张卡 ⑥a |
| `map` 构造 | 无扇出原语：Debate 的 N 辩手并行、AFlow 的候选并行评估、LangGraph `Send` 的静态子集全部丢失 | Debate/AFlow 卡 ⑥a；G0-langgraph §1 Send 行 |
| `human` 构造 | 无人在回路：SWE-agent 人工介入、CrewAI `human_input`、LangGraph `interrupt(response_schema)` 全部丢失 | G0-langgraph §1 interrupt 行；SWE 卡 ⑥b-8 |
| `route` 构造 | 无多路路由：Debate 的多数票/裁决 fallback、AutoGen Selector、CAMEL 的终止组合、LangGraph 条件边全部塌陷为「全连接广播」（AutoGen 默认病：all messages to all agents） | G0-autogen §2.2；G0-langgraph §1 路由行 |
| `escape` 构造 | 无 L4：Voyager 的沙箱任意代码执行、AFlow 的程序合成、MemGPT 的语义驱逐、ADAS 的任意 Python、GPTSwarm 的图编辑算子全部不可表达——注意这不是「更脏」而是**违反 ADR-001 的逃逸舱定位由缺失变成不存在** | 五张卡 ⑥b；ADR-001 §3 |
| `ops`（transform） | 无零状态算子：GPTSwarm「节点=无状态 callable」、Debate 的匿名化/乱序/聚合、AFlow 的 ensemble 全部失去声明位 | GPTSwarm/Debate/AFlow 卡 ⑥a |

---

## 3. 编译管线四阶段类型草图（Rust 结构体级）与确定性要点

阶段划分承 ADR-002（`af-dsl` = 前端 + L0 静态判定；`af-compiler` = 四阶段）。错误流承 poc-cue 四层分类学与 af-dspy-ir 一次收齐范式。

### 3.1 Stage 1 · 校验（`af-dsl::validate`）

```rust
/// 四层错误分类学（承 poc-cue loader/src/error.rs:1-11）
pub enum LoadError {
    Envelope(EnvelopeKind),   // E0001-E0004：缺/坏 version、信封未知键
    Shape(ShapeKind),         // E1001-E1007 + E1051-E1053：serde 形状 + 构造形状 + CEL
    Semantic(SemanticKind),   // E2xxx：引用/值域/重复/非空 + L0 不变量 + 契约
    Deploy(DeployKind),       // E9001-E9004：装载期组件解析（stage 3 产出）
}
/// 一条违例：稳定码 + 精确信息（ADR-007 §3），scope 标明根图或哪层体
pub struct Violation { pub code: ErrorCode, pub scope: String, pub message: String }
/// 报告：全部违例的集合，一次收齐不停第一条（承 af-graph validate.rs:108-125）
pub struct Report { pub violations: Vec<Violation> }
impl Report { pub fn is_ok(&self) -> bool; pub fn only_rule(&self, r: Rule) -> bool; }

/// serde AST：七段 + deny_unknown_fields（阶段 1a：信封 → 1b：形状）
pub struct Document {
    pub version: u32,
    pub meta: Meta,
    pub types: BTreeMap<String, Schema>,      // 类型词典
    pub stores: Vec<StoreDecl>,
    pub nodes: Vec<NodeDecl>,                 // 递归：loop/map 的 body 内嵌
    pub edges: Vec<EdgeDecl>,
    pub policies: Policies,
}

/// 校验顺序固定（保证违例输出确定性）：信封 → 形状 → CEL 编译 → 引用闭包 →
/// L0 不变量（INV-1..4）→ 契约核对 → route 归一化
pub fn validate(doc: &Document) -> Report;
```

### 3.2 Stage 2 · IR（`af-compiler::ir`）——拓扑即 IR

```rust
pub struct IrProgram {
    /// af-graph GraphTemplate 原样：B 的 DSL 拓扑与 IR 拓扑同构（内联体降维为命名子图）
    pub graph: GraphTemplate,
    pub stores: BTreeMap<String, StoreSpec>,      // 新增（L0 核心概念，af 仓无对应物）
    pub agents: BTreeMap<String, AgentSpec>,      // LLM-bound task 节点 → af-harness 四元组
    pub node_exec: BTreeMap<String, NodeExec>,    // 落地契约 §7.1 投影（unit/components/budget/retry）
    pub policies: IrPolicies,                     // BudgetRef 集 + StopCondition + FailureEntry 账
    pub interface: InterfaceSpec,                 // 新增 3 字段
    pub escapes: BTreeMap<String, EscapeSpec>,    // 新增（L4 记账）
}
/// 已编译 CEL：compile 一次 eval 多次（承 af-graph predicate.rs:49-70）
pub struct CelRef { pub source: String, pub roots: BTreeSet<String>, pub digest: String }
```

**内联体降维（确定性命名）**：每个 loop/map 构造生成一个 `SubGraph`，名 = 父路径 + `/` + 构造节点 id（如 `voyager/explore/acquire`）；`graph_version` 一律 stamp 父图版本——**af-graph E2007「map 体未版本化」在 DSL 面因此不可触发**（该码保留给 IR 直写路径）；`entry` = 体 nodes 首元素；嵌套构造递归降维。`route` 归一化为 `Edge.guard`（§1.5 算法），`goto: exit` 不产生边。

### 3.3 Stage 3 · 组件绑定（`af-compiler::bind`）与 Stage 4 · 计划生成（`af-compiler::plan`）

```rust
/// 落地契约 §2.2 组件引用集 + §7.1 node_exec.components 同形
pub struct ComponentBinding {
    pub model_route: Option<Ref>, pub loop_policy: Option<Ref>,
    pub memory: Vec<Ref>, pub tools: Vec<Ref>,
    pub context_compaction: Option<Ref>, pub unit: Option<Ref>,
}
pub struct BindReport {
    pub bindings: BTreeMap<String, ComponentBinding>,
    pub registry_digest: String,                 // 对全部声明文件的摘要（§2.2）
    pub violations: Vec<Violation>,              // E9001 引用缺失 / E9002 版本不符 /
}                                                // E9003 组件类别不符（unit 当 tool 用等）/ E9004 digest 不匹配

/// 落地契约 §7.1：拒绝式信封 {"v":1,"body":...}，deny_unknown_fields
pub struct ExecutablePlan { pub v: u32, pub body: PlanBody }
```

### 3.4 IR 改动预算表（宪法 C5：语法可换、IR 慎改）

| IR 类型 | 改动 | 动用的新码 |
|---|---|---|
| af-graph `Edge` | `guard: Option<CelRef>`、`checkpoint: bool`（2 个可选字段） | E1051/E2203 |
| af-graph `ControlledLoop` | `args: BTreeMap<String, PortRef>`、`exit_when: Option<CelRef>`、`on_exhausted: OnExhausted`、`carried_state: Vec<CarriedState>`（4 项） | E2105/E2002/E2211 |
| af-graph `HumanSpec` | `resume: Option<Schema>`（1 项） | E1003 |
| af-graph `Node` | `escape: Option<EscapeSpec>`（1 项）——**拓扑四字段（id/kind/human/loop/map）零改** | E2210 |
| 新 `StoreSpec` | `{name, kind, item?, writer: NodePath, lifecycle, retention, eval_input}` | E2208/E2311/E2331 |
| 新 `EscapeSpec` | `{impl_ref, reason, owner, share_budget_pct}` | E2210 |
| 新 `InterfaceSpec` | `{input_type, output_type, output_from}` | E2202 |
| 新 `FailureEntry` | `{class, retry?, route?, feedback?, fallback_route?, terminal, outcome}` | E2204 |
| 新 `TypeTable` | `BTreeMap<String, Schema>`（词典） | E2205 |

合计：**8 个新增可选字段 + 4 个新小结构体 + 1 张类型表**。af-graph 的 `GraphTemplate/Node/Edge/SubGraph/MapSpec/SafetyPointKind` 与 af-harness 的 `AgentSpec` 四元组全部原样复用——这就是「IR 直映优先」的可审计账单。

### 3.5 确定性编译要点

1. **全链路 BTreeMap/BTreeSet**：`types/stores/agents/node_exec/escapes` 用 `BTreeMap`；id 集合、CEL 根绑定集合用 `BTreeSet`。af-graph 已用 `BTreeMap<String, SubGraph>`（`model.rs:31`）与 `BTreeMap` 邻接表（`validate.rs:312`），B 沿袭——**无任何 HashMap 参与序列化或迭代顺序**。
2. **Vec 输出前按稳定键排序**：`nodes/edges/stores/policies.*` 按 id 排序；`safety_points` 按路径排序；`carried` 按 store 名排序。同一份 YAML 两次编译 → 逐字节相同的 IR 与计划。
3. **route 归一化无搜索**：§1.5 是纯文本重写（规则文档序 + ¬ 前缀展开），不涉及集合枚举或排序策略选择。
4. **编译期无时钟、无随机、无网络**：digest = 规范序列化（键序=字典序）后取 SHA-256；`shuffle_seeded` 的种子必须来自声明（`seed_ref`），编译期不产随机数。
5. **CEL 只编译不求值于编译期**（除可常量折叠的守卫，v0.1 不做折叠）：compile 一次、缓存 `CelRef`；eval 走 af-graph `predicate.rs` 通道（含 cel-parser 畸形串 panic 的 catch_unwind 兜底，`predicate.rs:12-15/45-47`）。
6. **未注册 kind 只进诊断**：`unknown_kinds: BTreeSet<String>` 按字典序去重（承 af-graph `validate.rs:224-232` 的 extension_kinds），不是违例。
7. **降维命名确定性**：子图名由「父路径/构造 id」机械生成，不依赖哈希或计数器状态。

---

## 4. 六个完整 YAML 样例

通用纪律：工具/模板/判定单元一律 `pkg.<包>.<名>` / `route.<名>@<版本>` 引用（领域名词全部住在包里）；CEL 全部保守子集（比较/布尔/整数算术/`in` 字面量，零函数调用）；六个样例的 YAML 与 CEL 均已过实跑自检（§4.7）。

### 4.1 样例 1 · ReAct 单体循环

```yaml
version: 1
meta:
  name: react_mono
  graph_version: "1.0"
  entry: solver
  input: react_input
  output: { ref: answer, from: solver }
  intent: "单 agent 节点：工具回灌在节点运行时内串行落账；语义终止 + 三重预算"

types:
  - name: react_input
    schema:
      type: object
      required: [question]
      properties: { question: { type: string } }
  - name: answer
    schema:
      type: object
      required: [final, supports]
      properties:
        final: { type: string }
        supports: { type: array, items: { type: string } }

stores:
  - name: trajectory
    type: message_log
    writer: solver                 # INV-2：唯一写者；观察回灌由 solver 运行时串行追加
    lifecycle: run
    retention: { max_items: 128 }

nodes:
  - id: solver
    kind: task
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

edges: []                          # 单节点：工具回灌在节点运行时内部完成，不经图边

policies:
  budgets:
    - { id: turn_cap, dimension: turns, scope: node:solver, cap: 12 }
    - { id: token_cap, dimension: tokens_total, scope: node:solver, cap: 60000 }
    - { id: cost_cap, dimension: cents, scope: node:solver, cap: 120 }
  stop:
    - { when: "last_tool.first_line in ['FINISH', 'FINAL ANSWER']", outcome: completed }
    - { when: "steps.tool_free >= 2", outcome: failed }
  failures:
    - class: transport_transient
      retry: { max: 3, backoff_ms: 800 }
    - class: tool_error
      route: same_node
      feedback: error_observation   # "无结果"类观察回灌，节点内继续
    - class: budget_exhausted
      terminal: true
      outcome: failed
```

覆盖要点（ReAct 卡 ⑥a 1-8）：单节点自循环 = 节点运行时环（编译目标 = `AgentSpec` 四元组）；轨迹 = 追加式 `message_log` 槽；停止 = 终止动作 CEL + 无工具轮上限；预算 = turns/tokens/cents 三重。卡 ⑥b 的运行时动作词表、自由文本切分、有状态环境契约 → `escape` 构造（本配方零逃逸）。

### 4.2 样例 2 · MetaGPT 流水线 + typed handoff

```yaml
version: 1
meta:
  name: metagpt_sop
  graph_version: "1.0"
  entry: pm
  input: requirement_input
  output: { ref: qa_report, from: build }
  intent: "SOP 流水线 + 信封血缘；repo 单写者；QA 回环=受控循环，安全点=外部评估"

types:
  - name: requirement_input
    schema:
      type: object
      required: [requirement]
      properties: { requirement: { type: string } }
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

stores:
  - name: tasks_board
    type: collection
    item: task_item
    writer: planner               # 顶层节点的单写者（无点号路径）
    lifecycle: run
    retention: { max_items: 128 }
  - name: repo
    type: collection
    item: code_file
    writer: build.apply           # 点号路径：经 loop 体逐层解析（§1.3）
    lifecycle: run
    retention: { max_items: 256 }

nodes:
  - id: pm
    kind: task
    uses: { model: route.main@1 }
    emits: { prd: "envelope<prd>" }          # 端口类型即信封：血缘由运行时填 from_node/artifact_type/step
    context:
      sections:
        - { from: template, template_ref: pkg.sweng.pm_system, quota_tokens: 500 }
        - { from: input, fields: [requirement], policy: project, quota_tokens: 600 }
  - id: architect
    kind: task
    uses: { model: route.main@1 }
    consumes: { prd: "envelope<prd>" }
    emits: { design: "envelope<design>" }
    context:
      sections:
        - { from: template, template_ref: pkg.sweng.architect_system, quota_tokens: 500 }
        - { from: edge, port: prd, fields: [vision, features], policy: project, quota_tokens: 2000 }
  - id: planner
    kind: task
    uses: { model: route.cheap@1 }
    consumes: { prd: "envelope<prd>", design: "envelope<design>" }
    writes: [tasks_board]
    emits: { tasks: "list<task_item>" }
    context:
      sections:
        - { from: template, template_ref: pkg.sweng.planner_system, quota_tokens: 400 }
        - { from: edge, port: prd, fields: [vision, features], policy: project, quota_tokens: 1500 }
        - { from: edge, port: design, fields: [modules, interfaces], policy: project, quota_tokens: 1500 }
  - id: build
    kind: task
    loop:
      body:
        nodes:
          - id: engineer
            kind: task
            uses: { model: route.main@1, tools: [pkg.sweng.locate, pkg.sweng.view, pkg.sweng.edit] }
            consumes: { feedback: qa_report }
            emits: { files: "list<code_file>" }
            context:
              sections:
                - { from: template, template_ref: pkg.sweng.engineer_system, quota_tokens: 600 }
                - { from: store, store: tasks_board, policy: full, quota_tokens: 1800 }
                - { from: edge, port: feedback, fields: [failures], policy: project, quota_tokens: 800, optional: true }
          - id: apply
            kind: transform
            writes: [repo]
            ops:
              - { op: merge, ports: [files], into: snapshot }
            consumes: { files: "list<code_file>" }
            emits: { snapshot: "list<code_file>" }
          - id: qa
            kind: check                      # 验证面；passed 端口内建
            uses: { unit: pkg.sweng.test_unit@1 }
            consumes: { snapshot: "list<code_file>" }
            emits: { report: qa_report }
            route:                           # QA 打回：不通过 → 回工程师；通过 → 退出本体
              default: exit
              rules:
                - { when: "qa.passed == false", goto: engineer }
        edges:
          - { from: engineer, output: files, to: apply, input: files }
          - { from: apply, output: snapshot, to: qa, input: snapshot }
          - { from: qa, output: report, to: engineer, input: feedback }
      max_iterations: 3
      carried:
        - { store: repo, max_items: 256 }    # 仅登记「体外声明、体内写」的 store
      safety_points:
        - { node: qa, kind: check }          # 每轮必须过外部评估（回环的安全点）
      exit_when: "attempt.passed == true"
      on_exhausted: fail
    emits: { report: { from_body: qa.report } }

edges:
  - { from: pm, output: prd, to: architect, input: prd }
  - { from: pm, output: prd, to: planner, input: prd }
  - { from: architect, output: design, to: planner, input: design }
  - { from: planner, output: tasks, to: build, input: tasks }   # 控制节点入边仅表排序

policies:
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

覆盖要点（MetaGPT 卡 ⑥a 全部）：SOP = 静态边流水线；结构化工件 = typed 端口 + 每边编译期类型核对 + 运行期 schema 校验（补 LangGraph G3）；`cause_by` 血缘 = `envelope<T>` 端口类型；QA 回环 = 受控循环（有界携带 + 验证面安全点）；TaskFinished = `exit_when`；工作区文件 = repo 槽；角色记忆 = store 的按需装配。卡 ⑥b 2/3/6（订阅触发、动态收件人、LLM 语义终止）→ 静态边近似或 L4。

### 4.3 样例 3 · Multi-Agent Debate（写入串行化）

```yaml
version: 1
meta:
  name: debate_kv
  graph_version: "1.0"
  entry: rounds
  input: debate_input
  output: { ref: position, from: finalize }
  intent: "N 辩手 map 并行互不可见；collector 是黑板唯一写者；多数票+裁决 fallback；一致性早停"

types:
  - name: debate_input
    schema:
      type: object
      required: [question, personas]
      properties:
        question: { type: string }
        personas: { type: array, items: { type: string } }
  - name: position
    schema:
      type: object
      required: [persona, claim, confidence_milli]
      properties:
        persona: { type: string }
        claim: { type: string }
        confidence_milli: { type: integer }
  - name: turn_record
    schema:
      type: object
      required: [claim, confidence_milli]
      properties:
        claim: { type: string }
        confidence_milli: { type: integer }
  - name: tally_result
    schema:
      type: object
      required: [answers, top_count, top_share_milli]
      properties:
        answers: { type: integer }
        top_count: { type: integer }
        top_share_milli: { type: integer }

stores:
  - name: transcript
    type: collection
    item: turn_record
    writer: rounds.collector        # INV-2：并行辩手不写黑板；汇聚节点串行写入
    lifecycle: run
    retention: { max_items: 64 }

nodes:
  - id: rounds
    kind: task
    loop:
      body:
        nodes:
          - id: debate_map
            kind: task
            map:
              over: input.personas            # 运行时定基数；实例间无横向边（互不可见）
              body:
                nodes:
                  - id: debater
                    kind: task
                    uses: { model: route.main@1 }
                    emits: { position: position }
                    context:
                      sections:
                        - { from: template, template_ref: pkg.debatekit.system, vars: { persona: arg.item }, quota_tokens: 400 }
                        - { from: input, fields: [question], policy: project, quota_tokens: 300 }
                        - { from: store, store: transcript, policy: latest_k, args: { k: 8 }, quota_tokens: 2400 }
                edges: []
            emits: { items: { from_body: debater.position } }   # map 的 from_body 自动包 list<>
          - id: collector
            kind: transform
            writes: [transcript]
            ops:
              - { op: anonymize, port: items, drop: [persona], into: anonymous }
              - { op: shuffle_seeded, port: anonymous, seed_ref: input.question, into: shuffled }
              - { op: truncate, port: shuffled, max_tokens_each: 200, into: transcript }   # 末端落点=store
            consumes: { items: "list<position>" }
            emits: {}
          - id: tally
            kind: transform
            ops:
              - { op: tally, port: items, by: claim, into: result }
            consumes: { items: "list<position>" }
            emits: { result: tally_result }
          - id: converge_gate
            kind: gate                      # 安全点：聚合值合法性守卫
            consumes: { result: tally_result }
            assert: "inputs.result.top_share_milli >= 0 && inputs.result.top_share_milli <= 1000"
        edges:
          - { from: debate_map, output: items, to: collector, input: items }
          - { from: debate_map, output: items, to: tally, input: items }
          - { from: tally, output: result, to: converge_gate, input: result }
      max_iterations: 3                    # K 轮上限（收益趋平 → 3 轮足够）
      carried:
        - { store: transcript, max_items: 64 }
      safety_points:
        - { node: converge_gate, kind: gate }
      exit_when: "tally.result.top_share_milli >= 700"   # 一致性早停（预计算份额进谓词）
      on_exhausted: continue
    emits: { positions: { from_body: debate_map.items } }
  - id: vote
    kind: transform
    ops:
      - { op: tally, port: positions, by: claim, into: stats }
      - { op: select_best, port: positions, by: claim, prefer: max, into: winner }
    consumes: { positions: "list<position>" }
    emits:
      stats: tally_result
      winner: position
    route:                                # 明确多数 → 直接定案；否则集中裁决（fallback）
      default: adjudicate
      rules:
        - { when: "vote.stats.top_count * 2 > vote.stats.answers", goto: finalize }
  - id: adjudicate
    kind: task
    uses: { model: route.main@1 }
    consumes: { winner: position }
    emits: { winner: position }
    context:
      sections:
        - { from: template, template_ref: pkg.debatekit.judge_system, quota_tokens: 400 }
        - { from: input, fields: [question], policy: project, quota_tokens: 300 }
        - { from: edge, port: winner, policy: project, quota_tokens: 400 }   # 多数票候选（供裁决参考）
        - { from: store, store: transcript, policy: full, quota_tokens: 6000 }
  - id: finalize
    kind: transform
    ops:
      - { op: project, port: winner, into: answer }
    consumes: { winner: position }
    emits: { answer: position }

edges:
  - { from: rounds, output: positions, to: vote, input: positions }
  - { from: vote, output: winner, to: finalize, input: winner }      # route 规则命中本边
  - { from: vote, output: winner, to: adjudicate, input: winner }    # route default 命中本边
  - { from: adjudicate, output: winner, to: finalize, input: winner }

policies:
  budgets:
    - { id: cost_cap, dimension: cents, scope: plan, cap: 400 }
    - { id: turns_cap, dimension: turns, scope: loop:rounds, cap: 30 }
  failures:
    - class: schema_invalid
      retry: { max: 2, backoff_ms: 0 }
      fallback_route: adjudicate          # 限次重解析仍败 → 裁决器自由文本判定
    - class: gate_refused
      terminal: true                      # 聚合值合法性守卫失败：该轮判失败
      outcome: failed
    - class: budget_exhausted
      route: vote                        # 成本超限：中止并返回当前多数
      terminal: true
      outcome: completed
```

覆盖要点（Debate 卡 ⑥a 全部 + ⑥b 2/7 的声明式化）：扇出-广播-扇入 = map + collector；**多写者问题 = collector 单写者**（对照 §5 INV-2 违规样例）；匿名 + 种子化乱序 = `anonymize`/`shuffle_seeded`（`seed_ref` 保可复现）；多数票 + 裁决 = `route` default；早停 = `tally` 预计算 + CEL。语义共识判定（⑥b 1）、运行时改拓扑（⑥b 4）→ L4。

### 4.4 样例 4 · AFlow 受控循环 + 评估环

```yaml
version: 1
meta:
  name: aflow_search
  graph_version: "1.0"
  entry: loader
  input: search_input
  output: { ref: candidate, from: best }
  intent: "搜索元循环=受控循环：合成（L4）→候选执行→外部评估→经验回灌；答案与分数对候选不可读"

types:
  - name: search_input
    schema:
      type: object
      required: [problem, validation_set]
      properties:
        problem: { type: string }
        validation_set:
          type: array
          items:
            type: object
            required: [prompt]
            properties: { prompt: { type: string } }
  - name: candidate
    schema:
      type: object
      required: [ref, parent]
      properties:
        ref: { type: string }
        parent: { type: integer }
  - name: answer
    schema:
      type: object
      required: [text]
      properties: { text: { type: string } }
  - name: tally_result
    schema:
      type: object
      required: [answers, top_count, top_share_milli]
      properties:
        answers: { type: integer }
        top_count: { type: integer }
        top_share_milli: { type: integer }
  - name: score_record
    schema:
      type: object
      required: [candidate, quality_milli, cost_milli]
      properties:
        candidate: { type: integer }
        quality_milli: { type: integer }
        cost_milli: { type: integer }

stores:
  - name: experience
    type: collection
    item: score_record
    writer: search.scoreboard        # INV-2：评估结果由记分板唯一串行写入
    lifecycle: run
    retention: { max_items: 20 }     # 有界经验池
  - name: answers_ref
    type: collection
    item: answer
    writer: loader
    lifecycle: run
    retention: { max_items: 64 }
    eval_input: true                 # INV-4：参考答案只对评估器可读

nodes:
  - id: loader
    kind: task
    uses: { tool: pkg.searchkit.corpus@1 }
    writes: [answers_ref]
    emits: { done: signal }
  - id: search
    kind: task
    loop:
      body:
        nodes:
          - id: synth
            kind: task
            escape:                     # L4：元智能体产出候选变体（程序合成）
              impl_ref: packages/searchkit@1.0.0/hatches/graph_synth.py
              reason: "元智能体产出候选变体：核心只允许对已注册算子集做参数化组变；任意拓扑合成经逃逸并版本化登记后实例化"
              owner: lang-team
              share_budget_pct: 30
            reads: [experience]         # 变异器可读分数（候选子图不可读——INV-4）
            emits: { candidates: "list<candidate>" }
          - id: run
            kind: task
            map:
              over: synth.candidates
              body:
                nodes:
                  - id: gen_a
                    kind: task
                    uses: { model: route.main@1 }
                    emits: { draft: answer }
                    context:
                      sections:
                        - { from: template, template_ref: pkg.searchkit.solver_system, quota_tokens: 500 }
                        - { from: arg, name: item, policy: project, quota_tokens: 600 }
                  - id: gen_b
                    kind: task
                    uses: { model: route.alt@1 }
                    emits: { draft: answer }
                    context:
                      sections:
                        - { from: template, template_ref: pkg.searchkit.solver_system, vars: { variant: b }, quota_tokens: 500 }
                        - { from: arg, name: item, policy: project, quota_tokens: 600 }
                  - id: aggregate
                    kind: transform
                    consumes: { draft_a: answer, draft_b: answer }
                    ops:
                      - { op: tally, port: draft_a, by: text, into: votes }
                      - { op: select_best, port: draft_b, by: text, prefer: max, into: answer }
                    emits:
                      votes: tally_result
                      answer: answer
                edges:
                  - { from: gen_a, output: draft, to: aggregate, input: draft_a }
                  - { from: gen_b, output: draft, to: aggregate, input: draft_b }
            emits: { items: { from_body: aggregate.answer } }
          - id: assess
            kind: check                  # INV-4：评估器外部化，读参考答案
            uses: { unit: pkg.searchkit.assess@1 }
            reads: [answers_ref]
            consumes: { items: "list<answer>" }
            emits: { scores: "list<score_record>" }
          - id: scoreboard
            kind: transform
            writes: [experience]
            ops:
              - { op: project, port: scores, into: experience }   # 末端落点=store
            consumes: { scores: "list<score_record>" }
            emits: {}
        edges:
          - { from: synth, output: candidates, to: run, input: candidates }
          - { from: run, output: items, to: assess, input: items }
          - { from: assess, output: scores, to: scoreboard, input: scores }
      max_iterations: 20                # MCTS 迭代预算
      carried:
        - { store: experience, max_items: 20 }
      safety_points:
        - { node: assess, kind: check } # 每轮必须过外部评估（反馈环的安全点）
      exit_when: "budget.cents_spent >= budget.cents_cap * 9 / 10"
      on_exhausted: continue
  - id: best
    kind: transform
    reads: [experience]
    ops:
      - { op: select_best, port: experience, by: quality_milli, prefer: max, into: winner }
    emits: { winner: candidate }

edges:
  - { from: loader, output: done, to: search, input: done }
  - { from: search, output: done, to: best, input: done }

policies:
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
```

覆盖要点（AFlow 卡 ⑥a + ⑥b 1/2/5）：工作流 = 静态算子图；四类算子 = task/transform/check/escape 的绑定形态；迭代/样本/阈值 = 预算 + 受控循环出口；反馈回灌 = experience 携带 + synth 检索；**评估隔离 = `eval_input` 标记 + 引用扫描（候选读不到答案；分数只给变异器）**。MCTS 本体与成本遥测 → L4（`escape`）。

### 4.5 样例 5 · LangGraph 状态图子集互译

互译表（来源：`DSL-G0-表达力-langgraph.md` §1 事实行）：

| LangGraph | AFB 对应物 | 备注 |
|---|---|---|
| `StateGraph(schema)` | `meta.input` + `stores` | 状态 = 显式槽而非隐式通道 |
| `Annotated[list, add_messages]` reducer | 按写者拆槽（每槽单写）+ 多 `message_log` 段按 step 序**内建交错** | 写侧归并 → 读侧交错；INV-2 静态化 |
| Node（普通函数） | kind 化节点 + `uses` 绑定 | |
| `add_conditional_edges(route)` | `route` 构造（有序 CEL + 必填 default） | 路由谓词从 Python 函数变为可静态校验表达式 |
| `START` / `END` | `meta.entry` / `goto: exit` | |
| `recursion_limit`（默认 25） | `loop.max_iterations` + `budgets.turns` | |
| Checkpointer（按 thread 快照） | `edges[].checkpoint: true` | 快照/恢复语义由 af-plan 承载（落地契约 §6） |
| `interrupt(response_schema)` | `human` 节点 + `resume.schema` | 类型化恢复值 |
| `Send` 动态扇出 | `map`（静态 `over`，运行时定基数） | 任意动态基数 → L4 |
| 子图 subgraph | loop/map 内联体（降维为版本化子图） | DSL 面无悬空体名 |
| `InvalidUpdateError` 并发写保护 | **编译期 INV-2 直接拒绝多写者** | 从运行期检测提前到编译期 |
| `RetryPolicy` / `error_handler(goto)` | `failures.retry` / `failures.route` | 分类维度从异常类型变为语义类别 |
| super-step 事务性 | 计划对象执行语义（落地契约 §3） | 不在语法层 |

```yaml
version: 1
meta:
  name: langgraph_subset
  graph_version: "1.0"
  entry: react_ring
  input: lg_input
  output: { ref: answer, from: react_ring }
  intent: "通道单写化+读侧交错替代 reducer；条件边=route；recursion_limit=循环上限；interrupt=人工节点；checkpointer=边检查点"

types:
  - name: lg_input
    schema:
      type: object
      required: [question]
      properties: { question: { type: string } }
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

stores:
  # LangGraph 单通道 messages + add_messages（多写者）→ 拆两槽单写 + 读侧交错
  - name: agent_turns
    type: message_log
    writer: react_ring.agent         # 原 agent 节点写 messages
    lifecycle: run
    retention: { max_items: 64 }
  - name: tool_turns
    type: message_log
    writer: react_ring.tools         # 原 tools 节点写 messages
    lifecycle: run
    retention: { max_items: 64 }

nodes:
  - id: react_ring
    kind: task
    loop:
      body:
        nodes:
          - id: agent
            kind: task
            uses: { model: route.main@1, tools: [pkg.hopqa.search, pkg.hopqa.lookup] }
            writes: [agent_turns]
            consumes: { checked: observation, decision: approval }
            emits: { answer: answer, action: action_call }
            context:
              sections:
                - { from: template, template_ref: pkg.hopqa.react_system, quota_tokens: 500 }
                - { from: input, fields: [question], policy: project, quota_tokens: 200 }
                - { from: store, store: agent_turns, policy: full, quota_tokens: 3000 }
                - { from: store, store: tool_turns, policy: full, quota_tokens: 3000 }
                # 两个 message_log 段由内建规则按 step 序交错（add_messages 的读侧对应物）
                - { from: edge, port: checked, policy: project, quota_tokens: 400, optional: true }
                - { from: edge, port: decision, fields: [approved], policy: project, quota_tokens: 100, optional: true }
          - id: tools
            kind: task
            uses: { tool: pkg.hopqa.toolbench@1 }
            writes: [tool_turns]
            consumes: { action: action_call }
            emits: { observation: observation }
          - id: format_check
            kind: gate                  # 本语法新增要求：任何循环必须有验证面安全点
            consumes: { observation: observation }
            assert: "inputs.observation.ok == true"
            emits: { checked: observation }     # 通过则前向转发观察
            route:                      # 不合法 → 结束本轮迭代（下轮带失败观察重来）
              default: agent
              rules:
                - { when: "format_check.passed == false", goto: exit }
          - id: approve
            kind: task
            human:
              station: review-desk
              role: reviewer
              quorum: 1
              resume:
                schema:
                  type: object
                  required: [approved]
                  properties: { approved: { type: boolean } }
            consumes: { answer: answer }
            emits: { decision: approval }
            route:                      # 打回：回环体重启（Command(goto=...) 的声明式对应）
              default: exit
              rules:
                - { when: "resume.approved == false", goto: agent }
        edges:
          - { from: agent, output: action, to: tools, input: action, checkpoint: true }
          - { from: tools, output: observation, to: format_check, input: observation, checkpoint: true }
          - { from: format_check, output: checked, to: agent, input: checked }
          - { from: agent, output: answer, to: approve, input: answer }
          - { from: approve, output: decision, to: agent, input: decision }
      max_iterations: 25               # recursion_limit=25
      carried:
        - { store: agent_turns, max_items: 64 }
        - { store: tool_turns, max_items: 64 }
      safety_points:
        - { node: format_check, kind: gate }
      exit_when: "resume.approved == true"
      on_exhausted: fail               # GraphRecursionError 对应物 → 终态 failed
    emits: { answer: { from_body: agent.answer } }

edges: []

policies:
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

两处**有意分歧**（同 A 的判断，理由不同）：① reducer 语义改写成交错（A 需显式 `merge` 字段；B 内建——交错序只有一种合理语义）；② 循环必须带验证面安全点（LangGraph 的环可以裸奔，B 的环必须可验收——`format_check` 是为此补的）。

### 4.6 样例 6 · Voyager（L3/L4 落点标注）

落点标注（Voyager 卡 ⑥ 逐条对层）：

| 机制 | 落点 |
|---|---|
| 迭代提示机制（单节点自循环） | **L2**：`acquire` loop 体内的 generator |
| 自动课程（外层环） | **L2**：`explore` loop + proposer |
| 技能库 / 课程表持久化 | **L0/L1**：`stores`（persistent + 有界 retention） |
| 任务-技能检索（top-k 相似度） | **L3**：`retrieve` 段的 `component: pkg.openworld.similarity@1` |
| 固定五段提示模板 | **L3**：`template` 段的 `pkg.openworld.iterative_prompt` |
| 技能入库守门（执行成功 ∧ 自检通过） | **L0/L2**：`admit` gate + safety point |
| 环境动作 API（craft/place/…） | **L3**：`pkg.openworld.env@1`（沙箱化动作面，非任意代码） |
| **任意 Python 代码生成与执行** | **L4**：`code_exec` escape 节点（impl_ref 进包，逃逸记账） |
| 软性终止判据 / 无固定终点 | **L1**：外层 `exit_when` 走预算（90% 费用即收束）；目标达成的软判定在 generator 的 `self_check` 结构化输出（L3） |

```yaml
version: 1
meta:
  name: voyager_curriculum
  graph_version: "1.0"
  entry: explore
  input: env_input
  output: { ref: "list<skill_entry>", from: export_skills }
  intent: "嵌套受控循环：外层课程步（提案→内层习得环）；技能库持久+检索注入；守门入库；任意代码执行走 L4"

types:
  - name: env_input
    schema:
      type: object
      required: [env_summary]
      properties: { env_summary: { type: string } }
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
  - name: code_artifact
    schema:
      type: object
      required: [source]
      properties: { source: { type: string } }
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

stores:
  - name: curriculum
    type: collection
    item: goal
    writer: explore.proposer
    lifecycle: run
    retention: { max_items: 64 }
  - name: skill_library
    type: collection
    item: skill_entry
    writer: explore.acquire.curator   # INV-2：守门写入（执行成功 ∧ 自检通过才入库）
    lifecycle: persistent             # 跨会话持久
    retention: { max_items: 512 }

nodes:
  - id: explore
    kind: task
    loop:
      body:
        nodes:
          - id: proposer
            kind: task
            uses: { model: route.cheap@1 }
            writes: [curriculum]
            emits: { goal: goal }
            context:
              sections:
                - { from: template, template_ref: pkg.openworld.curriculum_prompt, quota_tokens: 500 }
                - { from: input, fields: [env_summary], policy: project, quota_tokens: 400 }
                - { from: store, store: curriculum, policy: latest_k, args: { k: 10 }, quota_tokens: 900 }
          - id: acquire
            kind: task
            loop:
              args: { goal_text: proposer.goal.text }   # 隐式依赖边：proposer → acquire
              body:
                nodes:
                  - id: generator
                    kind: task
                    uses: { model: route.main@1 }
                    emits: { draft: skill_entry, code: code_artifact, check: self_check }
                    context:
                      sections:
                        - { from: template, template_ref: pkg.openworld.iterative_prompt, quota_tokens: 700 }
                        - { from: arg, name: goal_text, policy: project, quota_tokens: 200 }
                        - { from: store, store: skill_library, policy: retrieve, component: pkg.openworld.similarity@1, args: { k: 3 }, quota_tokens: 1500 }
                  - id: code_exec
                    kind: task
                    escape:                # L4：沙箱解释器执行任意生成代码（Voyager 卡 ⑥b-1）
                      impl_ref: packages/openworld@1.0.0/hatches/code_exec.py
                      reason: "生成器产出的任意 Python 需在沙箱解释器求值；其实现内部引用 L3 组件 pkg.openworld.env@1 提供动作 API（装载期核对类别）"
                      owner: lang-team
                      share_budget_pct: 25
                    consumes: { code: code_artifact }
                    emits: { report: exec_report }
                  - id: admit
                    kind: gate              # 技能写入门禁：执行成功 ∧ 自验证通过
                    consumes: { report: exec_report, check: self_check, draft: skill_entry }
                    assert: "inputs.report.ok && inputs.check.pass"
                    emits: { draft: skill_entry }      # 通过则前向转发工件
                    route:                # 不通过 → 不入库，结束本轮（failures.gate_refused 接下一步）
                      default: curator
                      rules:
                        - { when: "admit.passed == false", goto: exit }
                  - id: curator
                    kind: transform
                    writes: [skill_library]
                    ops:
                      - { op: project, port: draft, into: skill_library }   # 末端落点=store
                    consumes: { draft: skill_entry }
                    emits: {}
                edges:
                  - { from: generator, output: draft, to: admit, input: draft }
                  - { from: generator, output: code, to: code_exec, input: code }
                  - { from: generator, output: check, to: admit, input: check }
                  - { from: code_exec, output: report, to: admit, input: report }
                  - { from: admit, output: draft, to: curator, input: draft }
              max_iterations: 6
              carried:
                - { store: skill_library, max_items: 512 }
              safety_points:
                - { node: admit, kind: gate }
              exit_when: "attempt.passed == true"   # 入库成功 → 本目标收束
              on_exhausted: continue                # 轮次耗尽 → 换下一个课程目标
      max_iterations: 200
      carried:
        - { store: curriculum, max_items: 64 }
        - { store: skill_library, max_items: 512 }
      safety_points:
        - { node: acquire.admit, kind: gate }      # 跨层路径：经嵌套体解析
      exit_when: "budget.cents_spent >= budget.cents_cap * 9 / 10"
      on_exhausted: continue
  - id: export_skills
    kind: transform
    reads: [skill_library]
    ops:
      - { op: project, port: skill_library, into: skills }
    emits: { skills: "list<skill_entry>" }

edges:
  - { from: explore, output: done, to: export_skills, input: done }

policies:
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

覆盖要点：双层循环 = 外层课程环 + 内层习得环；课程表/技能库 = 持久 collection；检索注入 = `retrieve` 段；写库条件 = gate 安全点。卡 ⑥b 1（任意代码执行）→ `code_exec` 逃逸；⑥b 2/6/7（运行时改图、软终止、动态预算）→ L1/L2 近似 + L4。

### 4.7 样例自检记录（实跑，2026-10-24）

**检查 1 · YAML 可解析**（命令：`python3 /tmp/check_b.py`，脚本从本文档抽取全部 ```yaml 块）：

```
yaml blocks total=12 samples(version-first)=6 fragments=6
PASS sample1..6 parse  top-keys=['edges','meta','nodes','policies','stores','types','version']（六个一致）
PASS fragment1..6 parse（§5 违规样例片段）
```

六个样例（`version:` 起头）与六条 §5 违规片段全部通过 `yaml.safe_load`，0 语法错误；六个样例的顶层键集完全一致（七段结构无漂移）。

**检查 2 · CEL 合法（保守子集）**（命令：`/tmp/afb-check/target/debug/afb-check /tmp/expr.tsv`；`/tmp/afb-check` 是离线构建的 cel-interpreter 0.10.0 校验沙盒，属 /tmp 临时文件、非工作区仓库、未改任何现有文件）。16 条表达式（`when`/`exit_when`/`assert` 全部值）逐条过三项判定：

```
PASS s1/policies/stop[0]/when    last_tool.first_line in ['FINISH', 'FINAL ANSWER']
PASS s1/policies/stop[1]/when    steps.tool_free >= 2
PASS s2/.../route/rules[0]/when  qa.passed == false
PASS s2/.../loop/exit_when       attempt.passed == true
PASS s3/.../assert               inputs.result.top_share_milli >= 0 && inputs.result.top_share_milli <= 1000
PASS s3/.../loop/exit_when       tally.result.top_share_milli >= 700
PASS s3/.../route/rules[0]/when  vote.stats.top_count * 2 > vote.stats.answers
PASS s4/.../loop/exit_when       budget.cents_spent >= budget.cents_cap * 9 / 10
PASS s5/.../assert               inputs.observation.ok == true
PASS s5/.../route/rules[0]/when  format_check.passed == false
PASS s5/.../route/rules[0]/when  resume.approved == false
PASS s5/.../loop/exit_when       resume.approved == true
PASS s6/.../assert               inputs.report.ok && inputs.check.pass
PASS s6/.../route/rules[0]/when  admit.passed == false
PASS s6/.../loop/exit_when       attempt.passed == true
PASS s6/.../loop/exit_when       budget.cents_spent >= budget.cents_cap * 9 / 10
---- total=16 fail=0
```

三项判定 = ① `Program::compile` 可解析（E1051 判据）；② `references().functions() ⊆ 算子白名单`（E1052 判据，白名单 `_==_ _!=_ _<_ _<=_ _>_ _>=_ _&&_ _||_ !_ _+_ _-_ _*_ _/_ _%_ @in` 本身由同一沙盒对逐算子表达式实测归纳，含 `in` 在 cel-parser 0.10.1 中登记为 `@in` 而非 `_in_` 的实测修正）；③ `references().variables() ⊆ 位置词表`（节点 id 根按作用域解析，沙盒以允许根建模）且在合成绑定上下文上求值为布尔（E2203/E1053 判据）。反向对照（证明校验器有判别力，非全数放行；命令 `afb-check /tmp/neg.tsv`，3/3 按预期拒）：`size(input.personas) > 0` → 非算子函数 `size` 拒；`unknown_root.x == 1` → 未知根绑定 + 求值 Undeclared reference 拒；`steps.turns + 1` → 非布尔结果拒。

**检查 3 · 零领域名词**：`pkg.*`/`route.*` 字面量只出现在 `uses`/`template_ref`/`component`/`impl_ref`/`seed_ref` 五处；删光后七段结构、全部 CEL、全部类型名不变，核心 golden 样例自洽。

**检查 4 · 结构自检（按本提案自己的规则）**（命令：`python3 /tmp/struct_check.py`）：一个约 260 行的独立校验脚本（/tmp 临时文件，非工作区仓库），把文档内全部 10 份 YAML 文档（6 样例 + 4 条 §5 违规片段）按 §1/§5/§6 的规则逐条过——kind 四型词表、边端口存在与两端类型相等（含 `from_body` 推导类型与 map 自动包 `list<>`）、route 覆盖/互斥（E2101/E2102/E2103）、LLM 节点入边端口闭合（E2304）与 section 来源可解析（E2301/E2302/E2402）、ops 管道 port/into 可解析（E2209）、store 单写者（E2311）与 writer 路径可解析（E2001）、carried 跨作用域覆盖（E2211）、安全点路径与验证面（E2107/E2322）、map.over 为 list（E2104）、类型名登记（E2205）、retention 有界（E2208）、meta.output 可发射（E2202）、map 体写外槽（E2312）、自验证（E2321）、eval_input 读者集合（E2331）。结果：**6/6 样例 PASS（0 违例）；4 条违规片段各自精确触发其声明的错误码**（inv1→E2301+E2303，inv2→E2312+E2322，inv3→E2321，inv4→E2331[+E2303]，无缺失、无无关码——inv4 的 E2303 已在该片段注释中标注）。该检查在终审中真实抓出并修复了三个样例缺陷：① 样例 4 的 `aggregate` 引用了未在 `types` 登记的 `tally_result`；② 样例 5 的 `format_check→agent` 边把输出端口写成 `observation`（应为转发的 `checked`）；③ 样例 5 的 `approve` route 打回目标 `agent` 缺少对应出边（已补 `decision` 端口、边与 section）。另修复两处片段缺陷：inv2 的安全点路径需穿嵌套体写作 `debate_map.debater`、loop 节点需显式 `emits` 转发。

**未跑项（如实）**：编译器红绿测试（每条 L0 规则的拒绝用例、IR 降维快照、计划对象快照）按 ADR-007 在 af-dsl/af-compiler 落地时补齐——本文档 §5/§6 是其规格来源，当前只有上述语法层自检（YAML 解析 / CEL 合法 / 结构规则）。

---

## 5. 四条 L0 不变量的编译期判定规则

判定位置：af-dsl 前端静态 pass（ADR-002 crate 职责）。每条给：规则 → 静态检查 → 一个违规样例 → 错误码。全部一次收齐。

### INV-1 上下文完整性

**规则**：LLM-bound task 节点的上下文 = 且仅 = 其 `context.sections` 声明的来源（无隐式注入）；每个 section 的来源可解析（`input.fields` ∈ `meta.input` schema、`arg.name` ∈ 所在体形参表、`edge.port` ∈ 本节点入边端口集、`store` 名经作用域链可解析、`template_ref` 形状合法）；每段 `quota_tokens` 为正；每个入边端口恰被一个 section 引用；LLM-bound 节点不得声明 `reads`。

**检查**：引用闭包扫描 + 入边端口覆盖核对 + 配额正数核对。

违规样例（E2301 + E2303；两个码均已实跑确认触发）：

```yaml
version: 1
meta:
  name: inv1_demo
  graph_version: "1.0"
  entry: solver
  input: t
  output: { ref: a, from: solver }
types:
  - { name: t, schema: { type: object, required: [question], properties: { question: { type: string } } } }
  - { name: a, schema: { type: object, required: [text], properties: { text: { type: string } } } }
stores:
  - { name: trajectory, type: message_log, writer: solver, lifecycle: run, retention: { max_items: 64 } }
nodes:
  - id: solver
    kind: task
    uses: { model: route.main@1 }
    writes: [trajectory]
    reads: [trajectory]                     # E2303：LLM 节点直读 store（只能经 section）
    emits: { answer: a }
    context:
      sections:
        - { from: input, fields: [question], policy: project, quota_tokens: 200 }
        - { from: input, fields: [requirement], policy: project, quota_tokens: 200 }  # E2301：meta.input 无此字段
```

预期错误风格：
`E2301 context_source_unresolvable: node 'solver' section[1] field 'requirement' not in meta.input schema (t)`
`E2303 agent_direct_store_read: LLM-bound node 'solver' declares reads ['trajectory']（store 只能经 context.sections 进入 agent 上下文）`

### INV-2 写入串行化

**规则**：每个 store 恰有一个写者——`store.writer` 声明与全部节点 `writes[]` 引用（点号路径解析后）交叉核对，写者集合势 = 1 且等于声明值；map 体节点只能写本体内声明的 store（N 实例 = N 写者）；loop 的 `carried` 必须覆盖「体内（含嵌套体）写入的、体外声明的全部 store」。

**检查**：写者闭包扫描 + map 体作用域禁写 + carried 覆盖核对。

违规样例（E2312 + E2322；片段为可独立解析的完整文档，声明的两个码均已实跑确认触发）：

```yaml
version: 1
meta:
  name: inv2_demo
  graph_version: "1.0"
  entry: rounds
  input: inv2_input
  output: { ref: "list<position>", from: rounds }
types:
  - name: inv2_input
    schema:
      type: object
      required: [personas]
      properties: { personas: { type: array, items: { type: string } } }
  - name: position
    schema:
      type: object
      required: [claim]
      properties: { claim: { type: string } }
  - name: turn_record
    schema:
      type: object
      required: [claim]
      properties: { claim: { type: string } }
stores:
  - { name: transcript, type: collection, item: turn_record, writer: rounds.debate_map.debater,
      lifecycle: run, retention: { max_items: 64 } }
nodes:
  - id: rounds
    kind: task
    loop:
      body:
        nodes:
          - id: debate_map
            kind: task
            map:
              over: input.personas
              body:
                nodes:
                  - id: debater          # map 体节点
                    kind: task
                    uses: { model: route.main@1 }
                    writes: [transcript]  # E2312：map 体节点写共享槽
                    emits: { position: position }
                edges: []
            emits: { items: { from_body: debater.position } }
        edges: []
      max_iterations: 3
      carried: [{ store: transcript, max_items: 64 }]
      safety_points: [{ node: debate_map.debater, kind: gate }]   # E2322：debater 是 task 非验证面
    emits: { items: { from_body: debate_map.items } }
```

预期错误风格：
`E2312 map_shared_store_write: node 'debater' inside map body writes store 'transcript' declared outside（N 并行实例将并发写；改由汇聚节点单写——见样例 3 collector）`
`E2322 safety_point_not_verifier: safety point 'debater' kind 'task' not in {check, gate, human}`

### INV-3 生成器-验证器分离

**规则**：验证面 = kind ∈ {check, gate} ∪ human 标记节点（check/gate 另内建 `passed: boolean` 端口）；验证节点的任一条入边的生产者不得是它自己（产出即验收 = 自验证）；loop 的 `safety_points` 每个节点（点号路径解析后）必须是验证面节点。

**检查**：验证面节点入边生产者身份核对 + 安全点 kind 白名单（承 af-graph `SafetyPointKind` 三值，`validate.rs:453-457`）。

违规样例（E2321；完整可解析文档，实跑确认触发）：

```yaml
version: 1
meta:
  name: inv3_demo
  graph_version: "1.0"
  entry: solver
  input: inv3_input
  output: { ref: verdict_type, from: solver }
types:
  - name: inv3_input
    schema:
      type: object
      required: [task]
      properties: { task: { type: string } }
  - name: patch_ref
    schema:
      type: object
      required: [artifact_ref]
      properties: { artifact_ref: { type: string } }
  - name: verdict_type
    schema:
      type: object
      required: [pass]
      properties: { pass: { type: boolean } }
nodes:
  - id: solver
    kind: check                       # 验证面
    uses: { unit: pkg.sweng.test_unit@1 }
    consumes: { patch: patch_ref }
    emits: { patch: patch_ref, verdict: verdict_type }
edges:
  - { from: solver, output: patch, to: solver, input: patch }   # E2321：自验证（产出自扫）
```

预期错误风格：
`E2321 self_verification: verifier node 'solver' consumes port 'patch' produced by itself（生成与验证必须不同节点）`

### INV-4 评估器外部化

**规则**：评估/判定实现必须外置为 kind=check + `uses.unit` 的节点（组件类别在装载期核对，E9003）；标注 `eval_input: true` 的 store，其读者（经 `reads`/`context.sections` 引用它的全部节点，点号路径解析）必须 ⊆ {该 store 的 writer, 绑定 `uses.unit` 的 check 节点}。

**检查**：eval_input store 的引用方集合核对 + uses 形状规则（`unit` 仅 check 可用，E1005）。

违规样例（E2331；完整可解析文档，实跑确认触发）：

```yaml
version: 1
meta:
  name: inv4_demo
  graph_version: "1.0"
  entry: loader
  input: inv4_input
  output: { ref: answer, from: assess }
types:
  - name: inv4_input
    schema:
      type: object
      required: [corpus]
      properties: { corpus: { type: array, items: { type: string } } }
  - name: answer
    schema:
      type: object
      required: [text]
      properties: { text: { type: string } }
stores:
  - { name: answers_ref, type: collection, item: answer, writer: loader, lifecycle: run,
      retention: { max_items: 64 }, eval_input: true }
nodes:
  - id: loader
    kind: task
    uses: { tool: pkg.searchkit.corpus@1 }
    writes: [answers_ref]
    emits: { done: signal }
  - id: run_map
    kind: task
    map:
      over: input.corpus
      body:
        nodes:
          - id: gen_a                    # 候选执行体（在 map 体内）
            kind: task
            uses: { model: route.main@1 }
            reads: [answers_ref]         # E2331：候选读参考答案（兼踩 E2303：LLM 节点不该用 reads 直读）
            emits: { draft: answer }
        edges: []
    emits: { items: { from_body: gen_a.draft } }
  - id: assess
    kind: check                        # 评估器：唯一合法读者
    uses: { unit: pkg.searchkit.assess@1 }
    reads: [answers_ref]
    consumes: { items: "list<answer>" }
    emits: { scores: answer }
edges:
  - { from: loader, output: done, to: run_map, input: done }
  - { from: run_map, output: items, to: assess, input: items }
```

预期错误风格：
`E2331 eval_input_visible: store 'answers_ref' (eval_input) referenced by node 'gen_a' outside {writer 'loader', evaluator nodes}（评估输入对候选不可读）`

---

## 6. 错误码命名空间与校验规则总数预算

沿用 poc-cue 装载器四层分类学（E0 信封 / E1 形状 / E2 语义 / E9 部署期）与 af-graph E2xxx 四位风格；**码随域走、跨 crate 不重号**：E2001–E2007 已由 af-graph 图域占用（悬空引用/值域/重复 id/非空/环/孤立/map 体未版本化），本方案不重新分配——其中 E2001（悬空引用）、E2002（值域）、E2003（重复 id）、E2004（空集合）由 B 的 DSL 面共享触发；E2005（环）对根图生效（B 的合法环必须显式包进 `loop` 构造，裸环照拒），loop/map 体降维出的循环体子图豁免 DAG 检查（承 af-graph `validate.rs:268`）；E2007（map 体未版本化）在 DSL 面不可触发（内联体降维时自动 stamp 父图版本，§3.2），该码保留给 IR 直写路径；E2006（孤立节点）照常生效。

| 码段 | 域 | 归属 | 码表 |
|---|---|---|---|
| E0001–E0099 | 信封 | af-dsl | E0001 缺 version；E0002 version 非整数；E0003 version 非 1；E0004 信封未知键（**4 条**） |
| E1001–E1099 | 形状 | af-dsl | E1001 未知字段；E1002 缺必填字段；E1003 类型不符；E1004 枚举值非法（以上 4 条由 serde `deny_unknown_fields` 派生，**免费**）；E1005 构造与 kind 组合非法；E1006 控制节点污染（loop/map 节点带 uses/context/writes/reads/escape/ops）；E1007 内联体为空（**3 条手写**） |
| E1051–E1099 | 表达式（E1 子段） | af-dsl | E1051 CEL 解析失败（含 cel-parser panic 兜底归一）；E1052 CEL 非保守子集（非算子函数）；E1053 CEL 谓词非布尔（**3 条**） |
| E2001–E2007 | 图域既有 | af-graph | **不重新分配**（7 条，B 共享其中 4 条） |
| E2101–E2199 | 拓扑扩展 | af-dsl | E2101 route 出边未全覆盖；E2102 route 目标悬空；E2103 route 规则不可达（同目标重复）；E2104 map.over 非 list；E2105 args/over 引用悬空；E2106 emits.from_body 路径悬空；E2107 safety_points 路径悬空（**7 条**） |
| E2201–E2299 | 契约（L1） | af-dsl | E2201 边端口类型不匹配；E2202 meta.output.from 不发射该类型；E2203 CEL 未知根绑定；E2204 失败类未知/路由目标不存在；E2205 未知类型名；E2207 预算 cap 非正/作用域悬空；E2208 store retention 无界；E2209 ops 参数不闭合；E2210 escape 记账缺字段；E2211 carried 未覆盖跨作用域写入（**10 条**） |
| E2301–E2399 | 不变量（L0） | af-dsl | E2301 上下文来源不可解析；E2302 配额非正；E2303 agent 直读 store；E2304 入边端口未被 section 引用；E2311 多写者；E2312 map 共享槽多写；E2321 自验证；E2322 安全点非验证面；E2331 评估输入对候选可读（**9 条**） |
| E2401–E2499 | 上下文 | af-dsl | E2401 store 视图策略未知；E2402 arg 不在所在体形参表；E2403 template vars 引用悬空（**3 条**） |
| E9001–E9099 | 部署期 | af-compiler(stage 3)/执行面 | E9001 组件引用缺失；E9002 版本不符；E9003 组件类别不符（unit 当 tool 用、ops 输出契约不符）；E9004 registry digest 不匹配（**4 条**） |

**总数预算**：手写规则 = 信封 4 + 构造形状 3 + 表达式 3 + 拓扑 7 + 契约 10 + 不变量 9 + 上下文 3 + 部署期 4 = **43 条**；serde 派生 4 条（`deny_unknown_fields` 免费获得）；继承 af-graph 7 条（不新写）。**v0.1 合计 54 条，预算上限 60 条，余量 6 条**留给评审新增（每新增一条须在本文档登记码位与规则，禁止私占空号——承 ADR-007 §3 稳定码契约）。对照：A 的方案未给出总数预算，其码表散见于各段；B 的全部码位集中一表、可逐条审计。

---

## 7. 诚实清单：15 个对齐目标分级

分级口径：**优雅** = 核心机制有直接语法落点、样例即论文机制本身；**冗长但可行** = 能表达但要绕（多层构造/多节点组合/词法变通）；**必须逃逸舱** = 核心机制在 L0–L3 无落点，只能 L4 记账逃逸（ADR-001 §3 语义）。逐条证据 = 各卡 ⑥(a)/(b) + G0 缺口清单。

| # | 目标 | 分级 | 落点与代价 |
|---|---|---|---|
| 1 | ReAct | **优雅** | 单 task + uses.model + 一个 store + stop CEL（样例 1）。残余 L4：运行时动作词表、自由文本切分、有状态环境契约（卡 ⑥b 1/2/8） |
| 2 | Reflexion | **优雅** | 外层 loop（体 = actor + check + reflector）+ reflections 槽单写 + retrieve 注入（与样例 2/4 同面）。残余 L4：空值守卫、异质 evaluator 的函数注入（⑥b 1/6） |
| 3 | Voyager | **冗长但可行** | 双层嵌套 loop + persistent store + gate 守门可表达（样例 6），但 `acquire.admit` 式跨层安全点路径与 persistent+carried 双登记是绕的；任意代码执行必须 L4 |
| 4 | SWE-agent | **优雅** | 包工具面 + latest_k 窗口 + submit 停止 + 四维预算（与样例 1 同面，加 `checkpoint`）。残余 L4：软对齐编辑原语、环境准备脚本、人工介入通道（⑥b 1/5/8） |
| 5 | MemGPT | **冗长但可行** | 分层 sections + 写端口自编辑 + `policy: none` 可表达，但语义驱逐/异步抢占必须 L4；`none` 段配额记 0 是词法变通 |
| 6 | MetaGPT | **优雅** | typed 端口 + `envelope<T>` 血缘 + repo 单写 + QA 回环受控循环（样例 2）。残余 L4/近似：`_watch` 订阅触发、动态收件人（⑥b 2/3）——用静态边 + envelope 近似 |
| 7 | CAMEL | **优雅** | 双 agent + 模板 vars 角色化 + 受控对话环。残余 L4：Inception 运行时生成人设、语义完成判定（⑥b 1/2） |
| 8 | GPTSwarm | **冗长但可行** | 显式边=可见性 + 并行分支互不可见 + transform 算子可表达；图编辑算子与奖励搜索必须 L4（⑥b 1/2） |
| 9 | Agensh/DeLM | **待补卡** | 卡本身低置信（INDEX.md 备注：模型不知原目标、实写 AutoGen Swarm）；按现有内容判与 #8/#14 同面。**补卡前不下结论** |
| 10 | Multi-Agent Debate | **优雅** | map 并行 + collector 单写 + shuffle_seeded + route fallback + tally 早停（样例 3）——本提案的展示样例。残余 L4：语义共识判定、运行时改拓扑（⑥b 1/4） |
| 11 | AFlow | **必须逃逸舱（部分）** | 搜索元循环的**外壳**可用受控 loop + eval_input 隔离表达（样例 4），但 MCTS 本体、程序合成、成本遥测是定义性机制且无 L0–L3 落点（⑥b 1/2/4/5）——诚实的边界 |
| 12 | ADAS | **必须逃逸舱（大部）** | meta agent 的运行时拓扑决定、动态角色、自举替换、任意 Python（⑥b 1/2/3/4）全部越界；DSL 只能承载其「发现物的固定执行图」 |
| 13 | LangGraph 子集 | **优雅** | 通道单写化 + 读侧交错 + route + max_iterations + human.resume + checkpoint（样例 5 + 互译表）。残余 L4：Send 任意动态基数、时间旅行、跨线程 Store |
| 14 | AutoGen | **优雅** | 环形/层级图 + route + stop/failures（termination 家族的 `\|`/`&` 组合 → CEL `\|\|`/`&&`）。残余 L4：selector_func 闭包、ledger 自然语言演化（卡 ⑥b 1/2） |
| 15 | CrewAI | **优雅** | 顺序流水线 + `from: edge` 段（context 拉取的类型化版）+ human（human_input）+ guardrail=gate。残余 L4/近似：Manager 动态委派、RPM 限流（⑥b 1/7）——前者用 route 近似 |

汇总：优雅 9 / 冗长但可行 3（Voyager、MemGPT、GPTSwarm）/ 必须逃逸舱 2（AFlow 部分、ADAS 大部）/ 待补卡 1（Agensh/DeLM）。**与 A 的差别在代价分布而非覆盖面**：A 用 15 段把 #3/#5/#8 从「冗长」压到「可读」，B 接受这三条的绕度，换取 §1.5 的单一归一化算法与 §3.4 的 8 字段 IR 预算——孰优由评审按「编译复杂度权重」裁定。

---

## 8. 开放问题（交评审/后续 ADR）

1. **transform 的输出侧类型核对缺席**：v0.1 只核对 ops 输入侧形状与参数闭合，字段级映射（如 `anonymize` 后 `turn_record` ⊆ `position` 减去 drop 集）由组件契约在装载期核对（E9003）。若要编译期核对，需给每个算子声明输出类型推演规则——预计 +6~8 条校验规则，是否值得由评审定。
2. **无 schema 引用（`$ref`）**：一个已登记类型无法在另一个 schema 内被引用，组合类型只能复制内联（样例 4 的 `validation_set` 元素与 `{prompt}` 形状相同却要重写一遍）。v0.1 用 `types` 表 + 内联原始类型两档；`$ref` 是否进 v0.2 待定。
3. **body 内声明 store 一律 `iteration` 语义**：跨迭代状态必须体外声明 + carried 登记。这比 af-graph `CarriedState` 的原意窄（后者不限声明位置），窄化的收益是 carried 覆盖规则可静态穷尽（E2211）。
4. **验证分离的深度**：INV-3 只查直接自环（验证节点消费自己产的端口）。间接自验证（check → transform → check）未查——完全判定需要数据流可达性分析，与 B-R3 的「控制流单一归一化」精神相抵，留作后续。
5. **`eval_input` 的标记责任**：标记靠作者自觉；误标（把普通 store 标 eval_input）只会收紧不会放松，安全性单向。是否要「writer 是 tool 类节点」的辅助启发式，待定。
6. **`version`（文档信封）与 `graph_version`（图模板）双版本键**：编译产物是否要求两者绑定递增（承 A 的同一开放问题；落地契约 §7.1 `compiled_from.graph_version` 已要求与 WorkOrder 不可变绑定）。
7. **逃逸舱占比口径**：`share_budget_pct` 声明值 vs 实测值谁触发 30% 警戒（ADR-001 §3）；编译期是否拒绝 >50% 的配方。
8. **Agensh/DeLM 卡补写后**，其 handoff/swarm 面覆盖判断需复核（INDEX.md 已标低置信）。

---

## 附：证据锚点

- 裁决：`/home/pan-ding/workspace/af-wt-phase2-order/docs/adr/001-dsl-form.md`（YAML+CEL+逃逸舱+三层错误分类）、`002-crate-layout.md`（af-dsl/af-compiler 职责）、`007-tdd-discipline.md`（稳定错误码契约 E2001/DI1001 风格）。
- 机制卡（15 张，`计划/研究组/对齐机制卡/`）：各卡「⑥ DSL 表达点清单」(a) 为需求来源、(b) 为逃逸归类来源；INDEX.md 记载 Agensh/DeLM 低置信需人工补。
- 缺口需求：`DSL-G0-表达力-langgraph.md` §6（G1–G8，尤其 G4 写权限、G1 预算、G2 图即数据、G3 节点间校验、G7 信封类型）、`DSL-G0-表达力-autogen.md` §3（缺口 1–8，尤其元循环载体、typed 契约断裂）、`DSL-G0-表达力-crewai.md` §3（缺口 1–8，尤其反馈环、不变量层零字段）。
- 复用 schema：`af/crates/af-graph/src/model.rs`（GraphTemplate/Node/HumanSpec/ControlledLoop/CarriedState/SafetyPoint/MapSpec/Edge/SubGraph 与「构造字段与 kind 正交」注释）、`validate.rs`（五规则 + E2001–E2007 + 一次收齐 + extension_kinds 诊断）、`predicate.rs`（CEL compile/eval + catch_unwind 兜底 + NotBoolean）；`af/crates/af-harness/src/spec.rs`（AgentSpec 四元组、拒绝式信封、is_ref_name、StopCondition/BudgetRef、ContextTemplate 槽位校验）；`af/crates/af-dspy-ir/src/model.rs`（version 信封）、`validate.rs`（一次收齐范式）；`af/poc/poc-cue/verify-load/loader/src/error.rs`（E0/E1/E2/E9 四层分类学、稳定码 + kind_name + 精确信息）。
- 编译器约束：`~/.cargo/registry/src/*/cel-parser-0.10.1/src/references.rs`（ExpressionReferences::functions/variables——§1.4 保守子集静态判定的实现基础，白名单经 §4.7 实跑归纳）。
- 竞争提案：`计划/研究组/DSL-语法提案-A.md`（15 段立场；本文 §0 表格与 §7 汇总给出去向差异，不逐条驳）。
