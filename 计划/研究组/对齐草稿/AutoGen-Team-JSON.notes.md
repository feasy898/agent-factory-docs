# AutoGen-Team-JSON · AFB DSL 翻译记录

- 目标：AutoGen（v0.4+ autogen-agentchat）的声明式 Team 配置（RoundRobinGroupChat / SelectorGroupChat / MagenticOneGroupChat / Swarm / GraphFlow + termination conditions + participant agent 声明）
- 交付草稿：`计划/研究组/对齐草稿/AutoGen-Team-JSON.yaml`
- 语法依据：`计划/研究组/DSL-语法提案-B.md`（AFB v0.1 骨架）+ `计划/研究组/DSL-语法择优-裁决-20261024.md` §二（`meta.topology_selector` 编译期语义 + `escape.kind` 七类词表）
- 需求来源：`计划/研究组/对齐机制卡/AutoGen-Team-JSON.md` ⑥(a) 1–11 / ⑥(b) 1–8
- 参照样例：`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/testdata/sample{1..6}.yaml`（M1 已解析通过的 golden 种子；本机实际是 6 个文件，不是 `sample1-6.yaml` 单文件——任务书给的路径不存在，按目录逐个读）
- 计数：**⑥(a) 可表达 11 项**（其中完全表达 5、近似/部分 6）、**⑥(b) 逃逸 8 项**（对应七类词表全部用到）

---

## 一、机制 → 语法映射表（逐条对应卡 ⑥）

### ⑥(a) 可映射为「标准拓扑 + 组件」的 11 项

| # | 卡 ⑥(a) 机制 | AFB 落点（节点 / 构造 / 段） | 判定 | 备注与偏差 |
|---|---|---|---|---|
| 1 | RoundRobinGroupChat → 环形拓扑 + 轮转调度器 | `meta.topology_selector.rules[0] → pkg.autogen.team.round_robin@1.0`；候选图配方 = `loop` + `route` 规则 `steps.iterations % N == k`（静态轮转） | 近似（在候选图内） | AFB v0.1 **没有内联多图语法**，本文件 body 只能是 Selector 变体；RoundRobin 的确定轮转退化为「候选图」形式，配方见 §四 |
| 2 | SelectorGroupChat → 路由拓扑（选择策略节点） | `pick_speaker`（task + `uses.model`）→ `selector_override`（`route`：3 条 CEL 规则 + 必填 `default`） | **完全** | 选择结果是**类型化工件** `selector_decision`，路由按字段比较，不靠边守卫（提案 §1.5 单一归一化） |
| 3 | MagenticOneGroupChat → 编排器 + 工作者 + 共享账本 + 重规划转移 | `orchestrate`（编排器）→ `team_ledger`（共享账本，单写者 `ledger_sync`）→ `stall_check`（`kind: check` + `uses.unit` 停滞判定，安全点）→ `stall_flag` → `replanner`（重规划）→ `plan_sync` | **完全**（层级部分） | 「重规划转移」以**数据流**落点（停滞标志进槽，编排器下一回合改计划），避免在循环体内造无界子环；账本的自然语言演化部分转逃逸（⑥b-2） |
| 4 | Swarm → 交接拓扑（handoff 作状态转移边） | 工件 `handoff_request{target,reason}` → `handoff_sync` → `handoff_inbox` → `pick_speaker` 上下文段可见 → `route` 选下一发言者 | 近似 | 「强制转移」未强制：交接单由选择器模型消费后决定下一发言者。严格 Swarm 的确定性交接需要「动态目标边」，AFB v0.1 无此原语（见 §三 U5） |
| 5 | GraphFlow / DiGraphBuilder → 有向图拓扑 + 条件激活边 | 静态边 + `route` 条件边（`selector_override.route`） | 近似 | 条件激活（激活后**新增**边）属运行时改拓扑 → ⑥b-4 逃逸；静态条件边可表达 |
| 6 | TerminationCondition 家族 → 循环守卫谓词（消息/token/超时/文本/来源/handoff/函数调用/外部取消），支持 `\|` `&` 组合 | `policies.stop` 4 条 CEL（`steps.turns`、`budget.tokens_total_*`、`budget.clock_ms_*`、`last_tool.name`）+ `policies.budgets` 3 条 + `term_check`（`kind: check` 安全点）+ `loop.exit_when`；组合语义 = CEL `\|\|` / `&&` | 部分 | 文本命中 / 来源匹配 / handoff 目标 / 外部 `set()` 依赖运行时消息内容与外部事件，CEL 保守子集无字符串函数 → ⑥b-3 逃逸（`term_judge`） |
| 7 | participant agent 声明（角色名、system prompt、description、model client、tools、memory、code executor） | `nodes[]` + `uses{model,tools,memory}` + `context.sections`（template 段=system prompt）+ `user_proxy`（`human` 构造：`station/role/quorum/resume.schema`） | **完全** | 角色 description ≈ template 段 + `selector_decision.reason` 字段；模型客户端类名属组件层（⑥b-8） |
| 8 | FunctionTool / CodeExecutorTool → 动作端口（工具 schema） | `uses.tools: [pkg.autogen.tool.search@1, pkg.autogen.tool.calc@1]`（普通工具）；`code_runner` 逃逸舱（任意代码执行） | 部分 | 任意 Python 与副作用不可静态声明 → ⑥b-5 逃逸 |
| 9 | Memory → 上下文注入 / 检索源 | `uses.memory: [pkg.autogen.mem.list@1]`（组件绑定）+ `context.sections` 的 `store` 段（`full` / `latest_k{k}` / `retrieve{component,k}`） | **完全** | AutoGen 的 ListMemory/MemoStore/ChromaDBMemory 属包组件（`pkg.autogen.mem.*`），不占核心词表 |
| 10 | Message 类型 → 消息类型系统 | `types` 表：`chat_message{speaker,content,kind}`（kind 覆盖 text/function_call/function_result/handoff/stop）、`handoff_request`、`verdict`、`tool_result` 等 | **完全** | `kind` 判别字段承担 AutoGen 的 Message 子类型族（提案无联合类型，用判别字段 + 具名类型近似） |
| 11 | `save_state`/`load_state`、`to_config()` → 状态快照与可序列化声明体 | `edges[].checkpoint: true`（快照声明位，语义由 af-plan 承载）+ 拒绝式信封 `version: 1` + `meta.graph_version` + 全文 `deny_unknown_fields`（= 可序列化声明体本身） | 部分 | `to_config()` 的**自足性**（模型客户端只存类名与数据、行为不可静态校验）→ ⑥b-8 逃逸（`client_registry`） |

### ⑥(b) 需逃逸舱的 8 项（全部落成 `escape` 构造，`kind` 取裁决 §二-2 七类词表）

| # | 卡 ⑥(b) 机制 | 草稿中的逃逸节点 | `escape.kind` | 理由（照卡原文） |
|---|---|---|---|---|
| 1 | selector_func / 自定义选择提示词 | `team_loop.selector_override` | `llm_predicate` | 运行时闭包与自由提示词，静态 DSL 无法表达 |
| 2 | MagenticOne 的 ledger 自然语言演化 | `team_loop.ledger_evolve` | `runtime_context_mutation` | LLM 运行时生成的状态，非静态字段 |
| 3 | 动态终止判据（文本匹配、handoff 目标、外部 `set()`） | `team_loop.term_judge` | `free_text_parser` | 依赖运行时消息内容与外部事件，仅能参数化声明 |
| 4 | 拓扑运行时改写（重规划更换分工、条件激活产生新边） | `team_loop.replanner` | `meta_loop` | 图结构运行时变更，必须逃逸 |
| 5 | 工具内任意 Python 闭包与代码执行副作用（写文件、网络） | `team_loop.code_runner` | `program_synthesis` | 不可静态声明 |
| 6 | provider 侧 token 计费与重试策略 | `team_loop.usage_probe` | `env_adapter` | 外部不可见，需运行时遥测钩子 |
| 7 | 人在回路阻塞输入（UserProxyAgent 等待） | `team_loop.user_wait` | `env_adapter` | 交互式外部事件（阻塞等待 + 超时按错误处理） |
| 8 | `to_config()` 自足性边界（模型客户端仅存类名与数据，行为不可静态校验，卡标注**存疑**） | `client_registry`（图入口，装载期组件注册表） | `dynamic_tool_registry` | 声明可表达、行为需逃逸 |

逃逸记账：`share_budget_pct` 单条最高 15%（`code_runner`），合计 65%；`owner` 统一 `lang-team`；`impl_ref` 全部落在 `packages/autogen@1.0.0/hatches/*.py`（包内路径，不进语法层，承 ADR-001 §3）。

---

## 二、其它关键机制的落点（卡 ①③④⑤）

- **共享消息流（③）**：`team_messages`（`message_log`）——AutoGen 里所有 Agent 都往同一 Topic publish，是典型多写者；AFB 的 INV-2 静态拒绝多写者，故用**单一写者 relay**（`team_loop.relay`）串行落账，参与者只发消息不写槽。这是本稿最关键的一处「翻译即修正」。
- **两条并行上下文线（③）**：公开线 = `team_messages` 槽（经 `context.sections` 的 store 段注入）；私有线 = `uses.memory` 组件绑定（参与者私有的 ListMemory/MemoStore）。可见性由上下文段声明决定，不靠图连线（承提案 §1.2 读权限在消费者侧）。
- **私有结构化状态不进消息历史（③）**：`team_ledger` / `plan_board` / `stall_flag` / `handoff_inbox` 与 `team_messages` 分槽存放。
- **失败处理（④）**：`policies.failures` 五类：`transport_transient`（ModelClient `max_retries`）、`tool_error`（代码异常转错误消息回灌，不崩溃）、`timeout`（UserProxy 阻塞超时按错误处理）、`schema_invalid`、`budget_exhausted`（终端但 `outcome: completed`，跑满预算返回当前最佳）。
- **停止条件（④）**：`policies.stop` 5 条 CEL + `loop.exit_when`（`term_check.termination.terminated == true`）+ `loop.max_iterations: 12` + `on_exhausted: continue`。
- **预算（⑤）**：消息上限 = `turns`（`loop:team_loop`, cap 12）+ `loop.max_iterations`；token = `tokens_total`（plan, cap 400000）；墙钟 = `clock_ms`（plan, cap 600000）；另有 `model_calls`（plan, cap 120）。
- **无静态成本模型（⑤）**：卡明说「花费只能事后统计，DSL 侧无法在声明期预估」→ **本稿不声明 `cents` 预算**，成本观测走 `usage_probe` 逃逸 + `usage_log` 影子账。
- **评估（⑤）**：卡内的 GAIA / WebArena / ALFWorld 数字与消融均标注**存疑**，不进入 DSL（DSL 不承载评测数字）。

---

## 三、语法不确定点（诚实清单）

| # | 不确定点 | 事实依据 | 本稿取舍 / 备选方案 |
|---|---|---|---|
| U1 | `escape.kind` 在 M1 是**可选**字段 | `crates/af-dsl/src/model.rs:538-547`（`kind: Option<EscapeKind>`；注释写明「样例 B §4 成文先于裁决、未带 kind，故 M1 收为可选、值域已闭环」） | 本稿 8 处逃逸**全部**带 `kind`（裁决要求）；若 M2 收紧为必填，本稿不受影响 |
| U2 | **逃逸节点 + `route` 同节点**的组合合法性未定义 | 提案 §1.2 的 kind×uses 表只写「task + 无 uses + escape → EscapeSpec」；`route` 与 `escape` 同节点在 §1.3 未列先例；M1 结构层允许（`model.rs:136-165` 两者都是可选字段） | 本稿把 `route` 放在 `selector_override`（逃逸节点）上，使「自定义选择闭包」能真正改写路由。**备选**：route 落在 `pick_speaker`（普通 LLM 节点）上，`selector_override` 退化为事后校正——那样 ⑥b-1 的语义会弱化。留待 M4 裁定 |
| U3 | `meta.topology_selector` 的候选图必须是「已声明的版本化图/子图」，但 AFB v0.1 无内联多图语法 | 裁决 §二-1 定义了选择器语义；`model.rs:50-65` 只解析结构不解析候选；提案 §1.2 的 `meta` 无 `graphs` 段 | 本稿候选图一律用**包引用** `pkg.autogen.team.<topology>@1.0`；候选图的声明位置（包内清单）待定。规则 CEL 已过保守子集实跑（§五 检查 3） |
| U4 | **`emits` 端口不支持内联原始类型**（提案 §1.2 允许 `{type: string\|integer\|boolean\|number}`） | M1 `model.rs:195-221`：`EmitSpec` 自定义反序列化对任何 mapping 一律要求「只含 `from_body` 一个键」，其余 mapping 报 `invalid type: emits 端口映射值只允许 {from_body: 节点.端口}`（实测触发，见 §五 检查 2 的首轮失败） | 本稿把布尔/字符串端口改写成**具名对象类型**：`stall_state{stalled,note}`、`termination_state{terminated,reason}`、`ledger_view{text}`。这是 M1 实现与提案 §1.2 的分歧，**建议登记为 M1 偏差**（不影响本稿语义，但影响 CEL 写法：`term_check.termination.terminated` 而非 `term_check.terminated`） |
| U5 | Swarm 的**强制**交接（handoff 目标即下一发言者）与 GraphFlow 的**动态激活边**没有原语 | 提案 §1.5：路由归一化后每条边目标静态可知；`map.over` 只支持静态基数 | 本稿用「交接单工件 + 选择器消费」近似。若要强制交接，需把交接目标做成 `route` 的规则（静态比较交接目标的取值域）——在交接目标取值域有限时可做，取值域开放时只能逃逸 |
| U6 | CEL 位置词表的「节点 id」绑定在 `loop.exit_when` 里能否指向**体内**节点的 emits 端口 | 提案 §1.4：「`<节点 id>` 该节点 emits 端口 + 内建 passed（对象端口可继续点字段）」，可见范围「从当前作用域向外逐层解析，内层优先」；样例 3 先例 `exit_when: "tally.result.top_share_milli >= 700"`（体内节点） | 本稿 `exit_when` 用 `term_check.termination.terminated == true`（体内节点 + 对象字段），与样例 3 同形。M4 的 CEL 静态判定未实跑，只验了保守子集与求值为布尔 |
| U7 | `attempt` 绑定在**多个**验证面节点并存时的可见性 | 提案 §1.4：`attempt` = 「loop 的 `exit_when`（取最近一次验证输出）」 | 本稿体内有两个验证面节点（`stall_check`、`term_check`），为避开歧义**完全不用 `attempt`**，改用节点 id 绑定（U6） |
| U8 | 分支汇聚处「可选端口缺失」的运行期语义 | 提案未定义；本稿 `relay` 的入边来自 4 个不同参与者，均提供 `msg`（无缺失）；但 `code_runner` 的 `msg` 只由 `solver` 提供 | 若选择器直接点名 `code_runner` 而 `solver` 未发言，其 `msg` 入边不触发——本稿靠「代码执行只跟随 solver 的产出」这一编排约定回避，未在语法层解决 |
| U9 | `human` 节点的入边端口是否需要 `context.sections` 覆盖（E2304 适用范围） | 提案 §5 INV-1 只约束「LLM-bound task 节点」；golden 样例 5 的 `approve`（human 节点）有入边 `answer` 端口但无 section，且该样例结构自检通过（提案 §4.7 检查 4） | 本稿 `user_proxy`（human）按样例 5 先例不写 context；若 M2 把 E2304 扩到 human 节点，需补一段 `{from: edge, port: request}` |
| U10 | 逃逸占比口径 | 提案 §8-7：`share_budget_pct` 声明值 vs 实测值谁触发 30% 警戒、是否拒绝 >50% 未定；ADR-001 §3 只说「>30% 警戒是运行期健康度指标」 | 本稿 8 条逃逸分散在流程各段，单条 ≤15%。若按「声明值合计」口径，65% 会触发警戒——**这是本目标最需要评审拍板的口径**（AutoGen 在提案 §7 被评为「优雅」，若按合计口径会被判成高逃逸） |
| U11 | `relay` 的 `turn` 端口与 `team_messages` 落地的字段映射 | 提案 §1.3：ops 的**输出侧**字段映射由组件契约在装载期核对（E9003），编译期不查 | 本稿 `relay` 的 ops 落 `team_messages`，同时 `emits: {turn: chat_message}`（同源转发）；`finalize` 用 `project` 把 `chat_message` 投影成 `team_result{speaker,content}`——两处映射都留到装载期 |
| U12 | `team_loop` 的 `consumes: {ready: signal}`（控制节点的入边） | 提案 §1.2 的 E1006「控制节点污染」列举 `uses/context/writes/reads/escape/ops`，**不含** `consumes/emits`；样例 2 的 `build`（loop 节点）带 `emits` | 本稿 loop 节点带 `consumes`（为让 `client_registry → team_loop` 的边两端类型可核）；若 M2 的 E1006 扩大到 `consumes`，需改用 `signal` 端口的隐式约定 |

---

## 四、RoundRobin / GraphFlow 等「候选图」配方（因 AFB v0.1 无内联多图语法而未写进本文件）

- **RoundRobin**：`loop` 体 = [participant_i] → relay；路由放在一个无 `uses` 的调度节点上，规则用 `steps.iterations % N == k`（CEL `%` 与比较均在保守子集内），`default` 指向最后一位参与者。无模型选择节点 → 与本文件的 Selector 变体的差别只有「有无 `pick_speaker`」。
- **GraphFlow**：条件激活边 = `route` 规则（`when` 为工件字段比较），静态拓扑 = 普通边；「激活后新增边」只能走 ⑥b-4 逃逸。
- **MagenticOne 专有**：`max_turns / max_stalls / max_round_span` 三个结构化上限 → `loop.max_iterations` + `budgets{turns}` + `stall_flag` 槽的累计；本稿只落了 `max_iterations` 与 `stall_flag`（单标志），**未落 max_stalls 计数**（kv 槽无法自增，需 transform 算子或逃逸）——记为已知缺口。

---

## 五、自检记录（本 ask 内实跑，含命令与输出）

**检查 1 · YAML 解析（任务书指定）**
```
python3 -c "import yaml,sys; yaml.safe_load(open('/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿/AutoGen-Team-JSON.yaml'))"
YAML OK; top keys=['edges', 'meta', 'nodes', 'policies', 'stores', 'types', 'version']
body edges=29 root edges=2
body nodes=22 root nodes=3
escapes=8 ['client_registry', 'ledger_evolve', 'replanner', 'selector_override', 'user_wait', 'code_runner', 'term_judge', 'usage_probe']
types=13 stores=7
```
→ 通过；顶层键集恰为七段（`version` + 六段）。规模：节点 25（根 3 + 体内 22）、边 31（根 2 + 体内 29）、类型 13、槽 7、逃逸 8。

**检查 2 · af-dsl M1 全量校验（真实编译器前端，非替代检查）**
工作区零改动：把 af-wt-phase2-dsl 仓复制到 `/home/pan-ding/.cache/afb-sandbox`（裁掉其余成员，只留 `crates/af-dsl`），在副本里加一个临时测试 `tests/draft_check.rs`（`load_str` + `validate`，打印全部违例）。命令：
```
AFB_DRAFT=".../AutoGen-Team-JSON.yaml" CARGO_TARGET_DIR=/home/pan-ding/.cache/afb-target \
  cargo test --manifest-path /home/pan-ding/.cache/afb-sandbox/Cargo.toml -p af-dsl --test draft_check -- --nocapture
```
输出：
```
running 1 test
VIOLATIONS: 0
test draft_check ... ok
test result: ok. 1 passed; 0 failed; ...
```
→ 覆盖：拒绝式信封（E0001–E0004）、七段 serde 形状（deny_unknown_fields）、引用闭包（E2001/E2201/E2202/E2204/E2205/E2104/E2105/E2106/E2107/E2207/E2208）、INV-2 写入串行化（E2311/E2312/E2211）。**0 违例**。
（首轮曾因 `emits` 端口写内联原始类型被 E1003 拒绝，见 U4；已按 U4 改为具名类型后通过。）

**检查 3 · CEL 保守子集实跑**
复用提案 §4.7 的离线沙盒（`cel-interpreter 0.10.0`）复制到 `/home/pan-ding/.cache/cel-sandbox`，并把本稿新增的绑定根 `selector_override` / `term_check` 与 `input.topology` 加进合成上下文。命令：
```
cargo run --manifest-path /home/pan-ding/.cache/cel-sandbox/Cargo.toml --offline -- /home/pan-ding/.cache/autogen_cel.tsv
```
输出：`total=14 fail=0`（14 条 = 5 条 topology_selector 规则 + 3 条 route 规则 + 1 条 exit_when + 5 条 policies.stop；每条过 `Program::compile`、算子白名单、位置词表、布尔求值四项）。

**检查 4 · 六节自检（补 M1 未覆盖的 M2/M4 前置条件）**
脚本 `/home/pan-ding/.cache/autogen_struct_check.py`（自写，仿提案 §4.7 检查 4 的规则口径），逐项：信封 / 类型表 / 单写者 / 配额（quota_tokens 正 + LLM 节点入边端口恰被一个 section 引用）/ 预算（cap 正 + scope 合法且目标存在）/ 逃逸记账（四字段 + kind 在七类词表 + 逃逸节点不带 uses）/ route 覆盖与互斥（E2101/E2102/E2103）/ carried 覆盖（E2211）/ 安全点为验证面。输出：
```
节点 25 个 / 逃逸 8 处（share_budget_pct 合计 65%）
PASS: 六节自检 0 违例
```
（脚本打印的「边 644 条」是求和口径的重复计数，实际边数 = 根边 2 + 体内边 29 = 31。）

**未跑项（如实）**
- 编译器红绿测试（M1 每条规则的拒绝用例、IR 降维快照、计划对象快照）——未跑，本次只跑既有 M1 校验器 + 自写结构检查。
- M2/M3/M4 的完整校验（INV-1 正式实现、INV-3 自验证、INV-4 评估隔离、`route` 归一化算法、CEL 静态判定、`topology_selector` 编译期解析）——**未跑**，本稿对这些规则只做了前置自查，不等于通过。
- 编译产物（IR / 计划对象）——未生成。
- CEL 沙盒是 `cel-interpreter 0.10.0`，提案 §4.7 用的是 `cel-interpreter 0.10.0` / `cel-parser 0.10.1`，与提案一致；但**不是**真正编译器内的 `af-dsl::cel` 实现。

---

## 六、评审需要拍板的三件事

1. **U4（`emits` 内联原始类型不支持）**：M1 实现与提案 §1.2 分歧，建议按 M1 现状登记偏差或改实现——影响所有需要布尔/字符串端口的目标。
2. **U10（逃逸占比口径）**：AutoGen 被提案评为「优雅」，但按 `share_budget_pct` 声明值合计口径本稿达 65%；需要明确「合计口径」还是「单条口径」，以及是否拒绝 >50%。
3. **U2 / U3（逃逸节点带 route、多图候选的声明位置）**：决定本目标能否保持「选择策略=路由」这条例外，还是要把 `route` 收回普通节点。
