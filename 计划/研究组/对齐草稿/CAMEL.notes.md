# CAMEL → AFB DSL 翻译记录（草稿）

- 目标：CAMEL（Role-Playing 双代理协作 + Inception Prompting，Li et al. 2023）
- 卡片：`计划/研究组/对齐机制卡/CAMEL.md`（INDEX.md:20 登记为第 7 张卡，3213 字，成）
- 语法正本：`计划/研究组/DSL-语法提案-B.md`（AFB v0.1 骨架）+ `计划/研究组/DSL-语法择优-裁决-20261024.md` §二（`meta.topology_selector` 编译期语义、`escape.kind` 七类词表）
- 草稿：`计划/研究组/对齐草稿/CAMEL.yaml`
- 编译器参照：`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/src/model.rs`（七段 AST，`deny_unknown_fields` 全覆盖）、`src/validate/refs.rs`、`src/validate/inv2.rs`、`src/shape.rs`（闭环词表）
- 计数：**expressible = 9**（卡 ⑥(a) 全部 9 条）、**escapes = 3**（卡 ⑥(b) 中确需逃逸舱的机制数；其中 2 个在本草稿实例化为 `escape` 节点，1 个记账未实例化）

---

## 1. 机制 → 语法映射表

### 1.1 卡 ⑥(a)「可映射为标准拓扑 + 组件的机制」逐条对应（9/9）

| # | 卡片 ⑥(a) 条目（CAMEL.md:51-59） | 本草稿落点 | 节点/字段 | 说明 |
|---|---|---|---|---|
| a-1 | 双角色协作 = 双节点固定拓扑 + 交替消息边（assistant↔user） | 受控循环体内的两个 LLM 节点 + 类型化消息边 | `dialogue.loop.body`：`user_agent`、`assistant_agent`；边 `user_agent.message → assistant_agent.incoming`（`chat_message` typed handoff） | 「固定双节点 + 一条有向消息边」= AFB 的固定边；对话的往复靠循环体每轮重跑 |
| a-2 | 角色扮演人设 = 节点级 system prompt / persona 槽（Role Description） | 两个只读静态工件槽 + store 段注入 + system 模板段 | `stores`: `user_role` / `assistant_role`（`item: role_description` = role_name+profile+chat_example）；context 段 `{from: store, store: user_role, policy: full}`、`{from: template, template_ref: pkg.camelkit.user_system}` | 槽内工件会话内不变（卡③-4「只读静态工件」） |
| a-3 | Inception Prompt = 图前「初始化/编译阶段」的一次性提示生成节点，产出物作为变量注入下游节点 | 根图首节点 + 模板段 + 出边 | 节点 `inception`（`uses.model: route.main@1`，模板段 `pkg.camelkit.inception_prompt` + `input` 段），出边 `inception.draft → role_parser.draft` | 「离线生成」= 根图流水线首段，非循环内 |
| a-4 | 改写后的任务提示 = 全局任务上下文变量，注入全部节点 | 一个全局槽，注入到对话双方的 context | `stores`: `rewritten_task`（`item: task_prompt` = task+assistant_role+user_role 三段式）；双方节点各有一段 `{from: store, store: rewritten_task, policy: full}`；另有一条 typed 边 `role_parser.rewritten_task → dialogue.rewritten_task` 兼作顺序边 | 「注入全部节点」在 AFB 里只能靠 store 段（控制节点 `dialogue` 不能有 context，见 U3） |
| a-5 | Chat Example = 节点级 few-shot 示例槽 | 人设字段 + 独立 few-shot 模板段 | `role_description.chat_example` 字段（由 `role_parser` 填）；模板段 `pkg.camelkit.user_example` / `pkg.camelkit.assistant_example` | 多轮示例本体是自由文本，由 free_text_parser 逃逸舱产出（见 ⑥b-1/⑥b-5） |
| a-6 | 对话历史 = 节点私有 message state，逐轮自动注入 | 两个 `message_log` 槽 + 双方 context 各两段 `latest_k` | `stores`: `user_history`（写者 `dialogue.user_agent`）、`assistant_history`（写者 `dialogue.assistant_agent`）；context 段 `{from: store, store: user_history, policy: latest_k, args: {k: 12}}` + 同款 `assistant_history` | 「双方各自维护一份同源 history」与 INV-2 单写者冲突：拆成「各写各的一份 + 读侧按 step 序交错」（提案 B §1.2 内建合并规则）后既保语义又保单写者 |
| a-7 | 用户方先发 + 交替发言权 = 拓扑起始节点 + 轮次调度参数 | 循环体入口节点 = 用户方 | `dialogue.loop.body.nodes[0] = user_agent`（体入口 = 首元素，§3.2 降维规则）；每轮体序为 用户→助手→门→判定 | 「非对称启动」= 体内第一个节点；「交替」= 每轮体跑一遍（语义前提见 U1） |
| a-8 | 终止 = 语义完成判定 ∧/∨ 轮次/token 上限的组合条件 | 语义判定走 `loop.exit_when`；上限走 `loop.max_iterations` + `policies.stop` + `policies.budgets` | `exit_when: "completion_judge.outcome.completed == true"`；`max_iterations: 12`；`policies.stop`：`steps.iterations >= 12`、`budget.tokens_total_spent >= budget.tokens_total_cap * 9 / 10`；`policies.budgets` 6 条 | 组合被拆到两处构造：语义分支在环出口、硬上限在停止/预算（为什么不用 `route` 见 U2） |
| a-9 | 每角色独立模型绑定 = 节点级 model 绑定；共享任务 = 全局变量/共享 memory scope | 每节点 `uses.model`；共享任务 = 全局 store | `inception` / `user_agent` / `assistant_agent` 各自 `uses: {model: route.main@1}`；共享任务 = `rewritten_task` 槽 | 「同一底座模型」= 同一 route 引用，三处可分绑 |

### 1.2 卡 ② 组件清单（11 行）落点

| 组件 | 落点 |
|---|---|
| Inception Prompt（元提示） | 节点 `inception` + 模板段 `pkg.camelkit.inception_prompt` |
| Assistant Role Agent | 体内 `assistant_agent`（`uses.model`） |
| User Role Agent | 体内 `user_agent`（`uses.model`） |
| Role Description（角色名+Profile+Chat Example） | 类型 `role_description` + 槽 `assistant_role`/`user_role` |
| Task Prompt（三段式） | 类型 `task_prompt` + 槽 `rewritten_task` |
| Chat Example | `role_description.chat_example` + `pkg.camelkit.*_example` 模板段 |
| Message History | 槽 `user_history`/`assistant_history`（`message_log`） |
| Communication Channel（交替消息边、用户方先发） | 体内类型化边 + 体入口 = `user_agent` |
| Completion Judge | 体内 `completion_judge`（`escape.kind: llm_predicate`） |
| Token / Turn Budget | `policies.budgets`（6 条，含 `tokens_out` 的单次回复上限）+ `policies.stop` |
| Agent Society / Role-Playing Web | **无固定拓扑落点** → ⑥b-3 逃逸记账（`runtime_context_mutation`），本配方未实例化 |

### 1.3 卡 ③ 数据与上下文流（6 条）落点

| # | 卡片 ③ | 落点 |
|---|---|---|
| ③-1 | 生成期：任务描述 → 一次 Inception 调用 → 两份 Role Description + 改写 Task Prompt | `inception`（只读 `input.task_description`）→ 边 → `role_parser` → 三槽三端口 |
| ③-2 | 装配期：system = 角色提示 + 任务提示；Chat Example 常驻不衰减 | 每方 context 段序：system 模板 → 示例模板 → 自己的人设槽 → 改写任务槽 → 原始 input → 两段历史槽 |
| ③-3 | 对话期：读 system + 完整历史（含对方最新一条），产一条消息追加 | 消息经边 typed handoff（对方最新一条）+ 两个 message_log 槽（完整历史，`latest_k 12` 截窗） |
| ③-4 | 状态归属：角色/任务只读静态工件；历史为节点私有运行态 | 三个工件槽 `lifecycle: run` + 写入点唯一（`role_parser`）；历史槽写者是两个 agent 自身 |
| ③-5 | 可见性：对方角色描述是否可见（论文未明确，存疑） | 本稿选择「各看各的」：每方只读自己的 role 槽（见 U8，存疑点） |
| ③-6 | 交接物：除消息外无结构化工件交接；最终产物沉淀在对话内容 | 唯一的结构化工件 = `dialogue_outcome`（判定节点产出）；最终方案文本由 `dialogue_outcome.final_message` 承载 |

### 1.4 卡 ④ 失败处理与停止条件（6 条）落点

| # | 卡片 ④ | 落点 |
|---|---|---|
| ④-1 | 语义早停：用户方判定任务达成 → 立即停止 | `loop.exit_when`（判定由 `completion_judge` 逃逸舱给出）+ `on_exhausted: fail` |
| ④-2 | 预算停：单次 max_tokens 或总轮数耗尽 → 强制截断，无降级 | `budgets`（`tokens_out` 按 node 作用域、`turns`/`model_calls` 按 loop 作用域）+ `stop` 的轮次上限 + `on_exhausted: fail`（无降级路径） |
| ④-3 | 人设质量不合格 → 论文依赖人工筛选/重新生成（是否自动重试存疑） | **未自动重生成**（不发明论文未写的行为）；以 `failures.schema_invalid`（retry 2 次 + `route: next_iteration`）兜底；真正的「重新生成」需要给 setup 段套受控循环 + 体内回边（见 U9） |
| ④-4 | 对话跑偏/重复：仅由角色描述与 Chat Example 提供软约束，无自省修复 | 软约束落在 system/示例模板段；无额外检测节点（论文没有） |
| ④-5 | 角色目标冲突：靠角色分工隐式消解，无仲裁 | 无仲裁节点（论文没有）；判定节点只判「是否达成」，不判角色冲突 |
| ④-6 | 模型/API 故障：论文未描述工程级重试与降级（实现层通常重试，存疑） | `failures.transport_transient`（retry 3 次、backoff 800ms）——按实现层惯例补，非论文定义 |

### 1.5 卡 ⑤ 预算与评估方式落点

| 机制 | 落点 |
|---|---|
| 交替双代理 ≈ 单代理 2 倍成本 | `budgets.round_calls`（`model_calls`，`loop:dialogue`，cap 40）+ `round_turns`（`turns`，cap 36，每轮 3 次调用） |
| per-node max_tokens | `budgets.user_msg_tokens` / `assistant_msg_tokens`（`tokens_out`，`node:dialogue.*`，各 cap 2000） |
| 最大轮数上限 | `loop.max_iterations: 12` + `stop: steps.iterations >= 12` |
| 角色描述压缩上下文（communication efficiency 主张） | 三段 `latest_k {k: 12}` 历史窗 + 人设/任务槽各带 `quota_tokens` 上限（合计 17 段配额） |
| 两侧代理可绑同一底座模型 | 三个节点同引 `route.main@1` |
| 社会性评估三维度（cooperation / communication efficiency / role-playing web） | 节点 `social_eval`（`kind: check`，`uses.unit: pkg.camelkit.social_eval@1`，读两段历史 + `dialogue_outcome`），产出类型 `social_scores`（`cooperation_milli` / `efficiency_milli` / `extensibility_milli`）落槽 `eval_scores` |
| 消融对比（完整 Inception vs 仅任务描述 vs 仅角色名） | **本配方不含**：AFB 表达的是单条配方，消融=同一 meta.input 下三份配方实例，属配方工程而非图内机制 |
| 人工评估 / 公开 benchmark | 论文未确证（卡⑤「存疑」），不写入草稿 |

---

## 2. 逃逸清单（七类词表对照）

词表来自裁决 §二-2（`escape.kind` 闭环七类）：`dynamic_tool_registry` / `program_synthesis` / `meta_loop` / `runtime_context_mutation` / `env_adapter` / `free_text_parser` / `llm_predicate`。

| 卡 ⑥(b) | 机制 | 逃逸类别（七类词表） | 本草稿是否实例化 | 落点 / 理由 |
|---|---|---|---|---|
| ⑥b-1 | Inception 运行时生成人设（角色描述内容不可静态声明，只能「生成并注入自由文本工件」） | `free_text_parser` | ✅ 实例化 | 节点 `role_parser`：`impl_ref: packages/camelkit@1.0.0/hatches/role_parser.py`，`share_budget_pct: 10`。它把 `inception_draft` 的自由文本切成 `role_name/profile/chat_example` 并组装三段式任务提示 |
| ⑥b-2 | 语义化完成判定（「任务已达成」是 LLM 语义判断而非字段匹配） | `llm_predicate` | ✅ 实例化 | 节点 `completion_judge`：`impl_ref: .../completion_judge.py`，`share_budget_pct: 10`。它读 `rewritten_task` + 两段历史，给出 `dialogue_outcome`；环出口 `exit_when` 只消费它的结论 |
| ⑥b-3 | Role-playing web 动态增删参与方（运行时改写图结构） | `runtime_context_mutation` | ❌ 记账未实例化 | 固定两方拓扑里没有「增删参与方」的扩展点；写成图内节点会是一个无消费者、无出边的哑节点（违反 §2 孤立节点/E2006 精神）。本配方为论文核心两方协作，该扩展不进图；启用时必须以逃逸舱形式接管运行时参与方集合 |
| ⑥b-4 | 非对称发言权转交（若轮次控制只支持对称轮转） | —（不需要） | ❌ | AFB 的循环体顺序是静态的：体入口 = `user_agent` 即「用户方先发」，交替由每轮体序决定，不存在「对称轮转」的限制。故无需逃逸，也无需扩展参数 |
| ⑥b-5 | 多轮 Chat Example（若示例槽只支持单轮问答） | `free_text_parser`（与 ⑥b-1 同一舱） | ✅ 合并记账 | 多轮示例本体是自由文本，由 `role_parser` 一并产出并装入 `role_description.chat_example`；注入侧是普通 store 段 + few-shot 模板段，无需第二个逃逸节点 |
| ⑥b-6 | 隐式协作风格约束（「如何配合」的软约束） | —（不需要） | ❌ | 这是纯提示语义，没有声明式对应物，也没有可执行体——AFB 里由 system/示例模板段承载即可，不需要逃逸舱 |
| ⑥b-7 | 每轮双次调用的成本记账（若无 per-node 计费/预算钩子） | —（不需要） | ❌ | AFB 有三级预算作用域：`node:` / `loop:` / `plan`，且维度含 `model_calls`、`cents`、`tokens_out`，足以记账 |

**逃逸账目**：本配方 `escape` 节点数 = 2（`free_text_parser`、`llm_predicate`），四字段齐全（`impl_ref`/`reason`/`owner`/`share_budget_pct`），`share_budget_pct` 合计 20%（< ADR-001 §3 的 30% 警戒线）；按「需逃逸舱的机制」计数 = 3（⑥b-1+⑥b-5 合并计 1、⑥b-2、⑥b-3）。

---

## 3. 语法不确定点（诚实清单）

| # | 不确定点 | 现状与依据 | 若被评审推翻怎么改 |
|---|---|---|---|
| U1 | **循环体的重复语义**：体内回边计数（样例 2 MetaGPT 风格）还是机器重跑体入口（样例 3 Debate 风格） | 本稿按**机器重跑体入口**：体内无回边，每轮 = 用户发言→助手应答→格式门→判定。依据：样例 3（`sample3.yaml`）的体内是 DAG、靠 `max_iterations: 3` 表达 K 轮；`exit_when` 只有在体被重复时才有意义 | 若运行时按「体内回边」计数，则须把「继续本轮」写成体内回边（`outcome_gate → user_agent`），且 `max_iterations` 的含义随之改变，`on_exhausted` 与 `stop` 的轮次口径要重算 |
| U2 | **为什么没用 `route` 构造** | 提案 B §2 的正交性表把「CAMEL 的终止组合」列为 `route` 的落点，但本稿没用。理由：`route` 的 `goto` 词表只有 {节点 id, `exit`}，缺「下一迭代/继续」目标——CAMEL 的终止组合是「完成→退出，否则继续下一轮」，其「继续」分支在无体内回边的读法（U1）下无处可落。故拆成 `exit_when`（语义）+ `stop`/`budgets`（上限）两处 | 若评审要求 route 化：要么给 `route` 增加 `goto: next_iteration`，要么接受体内回边（与 U1 绑定）；两者都会动语法或语义，不宜由本稿单方编造 |
| U3 | **控制节点的入边端口覆盖（INV-1 / E2304，M2 未实现）** | `dialogue` 有入边 `role_parser.rewritten_task → dialogue.rewritten_task`，但控制节点不能带 `context.sections`（E1006「控制节点污染」），所以该端口无 section 可引用。本稿按 golden 样例 2 同形处理（`sample2.yaml` 的 `build` 同样有入边且无 context） | M2 落地 INV-1 时若对控制节点也要求端口覆盖，则应删掉这条入边，改用 `loop.args`（`role_parser.rewritten_task`）承载同一工件——`args` 同样构成隐式依赖边（顺序性等价） |
| U4 | **任务/逃逸节点写 store 的「端口→槽」对应关系无编译器校验** | `role_parser` 同时 `emits` 三端口并 `writes` 三槽，靠同名约定对应（`assistant_role`/`user_role`/`rewritten_task`）。M1 只校验「写者唯一」，不校验写的是什么 | 若将来引入 ops 落地规则，宜拆成 `role_parser`（只 emits）+ 一个 `transform`（`ops: project`，末端落点=store） |
| U5 | **两段 message_log 交错合并的读侧语义** | 双方各读 `user_history` + `assistant_history` 两段，靠提案 B §1.2 的内建规则「按 step 序交错」还原「同源 history」。该内建规则只在提案 §4.7 的样例层面自检过，M2 未实现 | 若 M2/M3 判定交错顺序不符，需改成单槽 + 汇聚写者（Debate 样例的 collector 模式），代价是「交替发言」要额外机制 |
| U6 | **同轮「写后读」可见性** | `user_agent` 写完 `user_history` 后，同轮的 `assistant_agent` 要读到这条最新消息。语法层无「轮内读-写序」保证，这是运行时假设 | 若运行时按「轮末提交」语义，则助手会晚一轮看到对方消息（与论文「含对方最新一条」不符），需改用边 typed handoff 传递最新消息（边已在，但历史视图会滞后一轮） |
| U7 | **助手方上下文轻度冗余** | `assistant_agent` 既从入边端口收 `incoming`（对方最新一条），又从 `user_history`（`latest_k 12`）里看到同一条 | 无需改语法；若要消除，可给历史段用 `slice` 语义（AFB 无此段策略），属未来项 |
| U8 | **对方角色描述是否可见**（卡③-5 明标「存疑」） | 本稿取「各看各的」：每方只读自己的 role 槽 | 若取「互见」，把两个 role 槽都加进双方 context 即可（语法无阻力） |
| U9 | **人设质量不合格的自动重生成**（卡④-3「是否自动重试存疑」） | 本稿**不做**自动重生成（不把论文未写的行为写进 DSL）；用 `failures.schema_invalid` 兜底 | 若要自动重生成：需给 `inception`+`role_parser`+质量门 套一层受控循环，体内加「不合格 → 回 `inception`」的回边（与 U1 的读法绑定，且根图不能有裸环） |
| U10 | **`meta.topology_selector` 未使用** | 裁决 §二-1 吸收的拓扑选择器是**编译期**选图（候选图必须是已声明的版本化图/子图）。CAMEL 核心只有一个固定拓扑；「role-playing web」是运行时参与方变化（=⑥b-3 逃逸），不是编译期图选择。写一个 `topology_selector` 就等于凭空造候选图 | 若要支持「按输入选不同协作规模」，需先声明候选子图，再写 `meta.topology_selector{rules:[{when,use}],fallback}` |
| U11 | **未跑编译器** | 本机未能运行 af-dsl M1 编译器：沙箱拒绝在 `/tmp` 写文件（`echo > /tmp/x` 返回 rc=1），根分区 96% 占用并报「超出磁盘配额」；而按任务约束不得在 af 仓内新增构建产物文件 | 有空位时在 af-wt-phase2-dsl 建一个外部 harness（path 依赖 `af-dsl`）跑 `load_str` + `validate`，可直接给出违例码集 |
| U12 | **CEL 静态判定未实跑** | 提案 §4.7 用的 cel-interpreter 沙盒（`/tmp/afb-check`）在本机不存在；本稿 5 条 CEL 表达式只按 §1.4 的算子白名单与根绑定表人工核对（零函数调用、算子全在白名单、根均为 `inputs`/`steps`/`budget`/节点 id） | 拿到沙盒后逐条过 `Program::compile` + `references()` 即可 |
| U13 | **`escape.kind` 在 M1 是可选字段** | `model.rs:540-547` 把 `kind` 收为 `Option`（因正本六个样例成文早于裁决）；本稿一律显式写 `kind`（`free_text_parser` / `llm_predicate`），值域在七类词表内 | 正本 v0.1 修订把 `kind` 升必填时无需改本稿 |

---

## 4. 自检记录（实跑）

### 4.1 任务指定的检查

命令（原样）：

```
python3 -c "import yaml,sys; yaml.safe_load(open('/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿/CAMEL.yaml'))"
```

结果：通过（无异常）。补充读取并打印了结构：`top keys = ['edges','meta','nodes','policies','stores','types','version']`；nodes = `[inception, role_parser, dialogue, social_eval]`；stores 6 个；types 7 个；root edges 3 条；budgets 6 条；stop 2 条；failures 4 条。

### 4.2 六节自检清单（逐项过）

| 清单项 | 判定依据（本次实跑的检查） | 结果 |
|---|---|---|
| ① 信封 | `version == 1`；顶层键集合恰为七段，无未知顶层键；`meta` 键在 `model.rs:29-40` 允许集内 | ✅ 通过（0 违例） |
| ② 类型表 | 7 个类型名唯一且全部登记；所有端口/`consumes`/`emits`/store `item`/`meta.output.ref` 的类型名可解析；无端口内联对象 schema；所有键在 `model.rs` 键集内 | ✅ 通过（0 违例） |
| ③ 单写者 | 6 个槽逐个核对：声明 writer 可解析且与实际 `writes[]` 写者集合**恰为 1 且相等**；体内写、体外声明的槽全部登记 `carried`；无 map 体共享槽写（E2311/E2312/E2211 口径） | ✅ 通过（0 违例） |
| ④ 配额 | 17 段 `context.sections` 的 `quota_tokens` 全为正整数；`from` 取值全在五来源词表内；LLM 节点的每条入边端口恰被一段 `edge` section 引用（INV-1/E2304 口径） | ✅ 通过（0 违例） |
| ⑤ 预算 | 6 条预算 `cap > 0`；`dimension` 在八值词表内；`scope` 全部可解析（`plan` / `node:dialogue.user_agent` / `node:dialogue.assistant_agent` / `loop:dialogue` 且该节点确有 loop 构造） | ✅ 通过（0 违例） |
| ⑥ 逃逸记账 | 2 个 `escape` 节点：四字段（`impl_ref`/`reason`/`owner`/`share_budget_pct`）齐全、`kind` ∈ 七类词表、`share_budget_pct` 合计 20% < 30% 警戒 | ✅ 通过（0 违例） |

### 4.3 附加检查（同批实跑）

- **拓扑契约**：7 条边（根 3 + 体内 4）端点在其作用域内可解析、生产端口存在、两端端口类型**逐条相等**（含 `from_body` 推导类型）；`meta.output.ref` 由 `meta.output.from` 发射；`meta.entry` 可解析；两个 `safety_points` 路径在体根可解析且是验证面节点（`gate`）→ 0 违例。
- **CEL 保守子集**：5 条表达式（2 个 `assert`、1 个 `exit_when`、2 个 `stop.when`）——零函数调用、算子全部落在白名单符号集、根绑定全部在位置词表内（`inputs`/`steps`/`budget` + 体内节点 id）→ 0 违例。
- **键/枚举白名单比对**：逐字段比对 `af-dsl/src/model.rs` 的 `deny_unknown_fields` 键集与各枚举闭环词表（store type/lifecycle、budget dimension、stop outcome、failure class、escape kind、on_exhausted、safety_point kind、section from）→ 0 违例。

### 4.4 未跑项（如实）

- **af-dsl M1 编译器**（`cargo test -p af-dsl` / `load_str` + `validate`）：**未跑**。原因：本机沙箱拒绝写 `/tmp`（`echo > /tmp/probe` 与 `mkdir -p /tmp/afb-validate` 均返回 rc=1、无输出），根分区已用 96%（`df`）并报「超出磁盘配额」；而按任务约束不得在 af 仓内新增构建产物或 harness 文件。本节 4.2/4.3 的检查是**自建复刻**（按 `model.rs` / `refs.rs` / `inv2.rs` / `shape.rs` 的规则重写），不是编译器实跑结果——两者结论应当一致，但不等同。
- **CEL 实跑**（cel-interpreter 沙盒）：**未跑**，沙盒不存在（见 U12）。
- **IR 降维 / 计划对象快照**：不属于本任务范围。
