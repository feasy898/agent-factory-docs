# SWE-agent → AFB 草稿 · 翻译记录

- 目标：SWE-agent（Agent-Computer Interface，仓库级软件工程修复，Princeton 2024）
- 卡片来源：`计划/研究组/对齐机制卡/SWE-agent.md`（六节齐全，5918 字）
- 语法依据：《DSL-语法提案-B》（AFB v0.1 正本）§1 / §2 / §4；裁决书 20261024 §二（`meta.topology_selector` 编译期语义、`escape.kind` 七类闭环词表）
- 草稿：`计划/研究组/对齐草稿/SWE-agent.yaml`
- 性质：**草稿是输入不是裁决**。以下映射表是我对卡⑥的翻译预判，最终通过与否由编译器裁定。

---

## 1. 机制 → 语法映射表（逐条对应卡⑥(a) 12 条）

| # | 卡片⑥(a) 机制 | AFB 落点 | 卡片原文要点 |
|---|---|---|---|
| 1 | 单节点 ReAct 循环（Sequential Loop） | `agent_loop` 的 `loop` 构造：体首节点 `agent` 为**唯一 LLM 节点**，无 `map`、无并发分支、无多 agent 分工 | "一轮 = 观察→思考→动作→环境反馈，映射为「单节点循环」；无多 agent 分工、无并发分支" |
| 2 | 受限动作空间 / 工具集 | `agent.uses.tools` 六个 ACI 命令面：`search / open / edit / create / run_test / submit`（各带参数 schema 在包内） | "ACI 暴露的命令集合映射为标准 tool 节点（search / open / edit / create / run-test / submit），每项带参数 schema" |
| 3 | 上下文装配器（Context Assembly） | `agent.context.sections`：① `template`（ACI 系统提示词 `pkg.sweagent.aci_system@1`）② `input`（issue 文本）③ `arg`（环境句柄）④⑤ 两个 `store` 段（`latest_k` 滚动窗口）⑥⑦⑧ 三个 `edge` 段（observation / feedback / hint，均 `optional: true`） | "system prompt + 历史 + 最新 observation 的拼接映射为「固定模板 + 滚动历史窗口」的上下文构造组件" |
| 4 | 记忆 = 对话历史 + 磁盘工件 | 两个 `message_log` 槽 `agent_turns` / `tool_turns`（读侧按 step 内建交错，等价 SWE-agent 的 thought+command ↔ observation 交替）+ 一个 `collection` 槽 `workspace`（工作树 diff 快照 = 磁盘工件） | "映射为「消息列表（memory）」+「工作区/文件工件（artifact store）」两类标准组件，artifact 通过文件系统隐式交接" |
| 5 | 解析器（结构化输出解析） | `format_check`（`kind: check` + `uses.unit: pkg.sweagent.aci_schema@1`）：校验 Thought/Command 结构，产出 `verdict` | "映射为标准「输出解析 / schema 校验」组件，失败产出回灌消息" |
| 6 | 错误回灌与自修正（ReAct 式反馈） | 环内回边 `format_check → agent`（端口 `feedback`）+ `route` 规则 `format_check.passed == false → agent`；并行由 `policies.failures` 的 `class: schema_invalid / route: same_node / feedback: format_reminder` 记账 | "映射为循环内标准 error-feedback 边（环境返回 → 追加 observation → 继续本节点）" |
| 7 | 步数 / 轮次 / 成本上限 | `policies.budgets` 四维：`turns`(loop:agent_loop, 50) / `tokens_total`(plan, 200000) / `cents`(plan, 120) / `clock_ms`(node:agent_loop.env_exec, 60000) | "映射为标准预算组件（max_steps / max_tokens / max_cost / timeout）" |
| 8 | 上下文超限截断 | 静态侧：`store` 段 `policy: latest_k`（滚动历史窗口，k=30）+ `tokens_total` 预算；动态侧（具体裁剪算法）：`runtime_ctx` 逃逸节点 | "映射为标准的 context truncation / 摘要组件（作用于历史消息列表）" |
| 9 | 终止动作 submit | `format_check.verdict.submit == true` → `route` 规则 `goto: exit`（退出环体）+ 环 `exit_when: "format_check.verdict.submit == true"`；`submit` 亦在工具面内 | "映射为标准的「终止/提交动作」+ 终止判据集合" |
| 10 | 评测器 = 标准 evaluate 节点 | `evaluate`（`kind: check` + `uses.unit: pkg.sweagent.swebench_eval@1`）：从 `patch` 工件跑官方测试，产出 `verdict.resolved`（+ fail-to-pass 通过/总数）；金标准存于 `eval_refs` 槽（`eval_input: true`） | "从工件（patch）出发跑官方测试产出 resolved 布尔指标，映射为标准评估/判定组件" |
| 11 | 环境 = 标准 sandbox/executor 组件 | `env_exec`（`kind: task` + `uses.tool: pkg.sweagent.env@1`）：在受限容器内执行命令并捕获 stdout/stderr/返回码 | "命令执行、捕获输出、返回码、diff" |
| 12 | 轨迹记录 | `agent_turns` + `tool_turns`（`message_log`）+ `workspace`（diff 快照序列）三槽即为轨迹记录；`edges[].checkpoint: true` 标在动作边与交付边 | "映射为标准 trajectory/trace 记录组件（供评测与消融分析）" |

**⑥(a) 覆盖判定：12/12 全部落到标准拓扑/组件。** 关键设计取舍见 §4。

---

## 2. 逃逸清单（卡片⑥(b) 8 条 → 七类词表记账）

草稿共 **4 个 escape 节点**（`escape.kind` 取裁决书 §二-2 的七类闭环词表），覆盖卡片⑥(b) 全部 8 条：

| 卡片⑥(b) # | 机制 | escape 节点 | `escape.kind` | 理由（摘自卡片） |
|---|---|---|---|---|
| 1 | ACI 命令语法与文件编辑的"约定即语义"（行号 + 旧文本 → 新文本 的软对齐编辑原语） | `command_extract` | `free_text_parser` | "其语义既非函数调用也非文件补丁，而是字符串级编辑 + 精确匹配行号/代码片段格式…需要 escape hatch（自定义命令解析/替换层）" |
| 2 | 模型自由文本输出到命令的启发式抽取 | `command_extract`（同一逃逸节点） | `free_text_parser` | "解析规则是模糊的、非确定性的 shell 语法子集 → 运行时动态解析，不可静态声明" |
| 3 | 输出截断与摘要的具体裁剪策略 | `runtime_ctx` | `runtime_context_mutation` | "截断长度、diff 展示格式、噪声过滤规则属于实现级启发式，随仓库与命令类型变化 → DSL 表达不了的运行时策略" |
| 4 | 命令执行的安全沙箱与副作用捕获（权限黑名单、网络/超时控制、工作树快照回滚） | `env_boot` | `env_adapter` | "运行时基础设施，DSL 只能引用而不能声明" |
| 5 | 依赖安装与仓库准备脚本（per-instance setup、pip 安装、测试命令生成） | `env_boot`（同一逃逸节点） | `env_adapter` | "运行时生成的环境脚本，静态拓扑无法穷举" |
| 6 | token 预算到步数的动态换算与上下文压缩策略 | `runtime_ctx`（同一逃逸节点） | `runtime_context_mutation` | "不同版本对超限历史的截断/摘要行为不同 → 运行时启发式" |
| 7 | 自省/反思型提示注入（变体相关，卡片标注**存疑**） | `runtime_ctx`（同一逃逸节点） | `runtime_context_mutation` | "提示内容在运行时动态构造，静态拓扑难表达" |
| 8 | 人工介入（human-in-the-loop）通道 | `human_channel` | `dynamic_tool_registry` | "外部人类在轨迹中途注入消息/操作 → 外部事件驱动的动态入边，需逃逸舱式的可注入钩子" |

**逃逸记账**：4 个逃逸节点 × 四字段齐全（`impl_ref` / `reason` / `owner` / `share_budget_pct`）+ `kind`；`share_budget_pct` 合计 **28%**，未超 ADR-001 §3 的 30% 警戒线（结构自检脚本已断言）。

**逃逸节点与标准的分工**（重要）：卡片⑥(b) 第 1/2/3/6/7 条并非"整条机制不可表达"，而是"**其中的运行时启发式部分**不可声明"。草稿的处理是**双轨**：
- 可声明的部分用标准构造表达（例：历史窗口用 `store` 段 `latest_k`；命令面用 `uses.tools`；沙箱执行用 `uses.tool`）；
- 只有启发式/动态部分进逃逸节点（例：具体裁剪算法、自由文本抽取、事件驱动注入）。

⑦ 反思提示注入（卡片标注存疑）**未单独建逃逸节点**，并入 `runtime_ctx` 的 reason——因为它与⑥(b) 3/6 是同一运行时组件的不同策略，单独建点会虚增逃逸占比且语义重复。这一点是**我的判断**，若评审要求逐条独立记账，需拆分该节点（会推高逃逸占比）。

---

## 3. 语法不确定点（诚实列出）

| # | 不确定点 | 我的处理 | 影响 |
|---|---|---|---|
| U1 | **`escape.kind` 是裁决书吸收项**，提案 B §4 六个 golden 样例成文早于裁决，样例里的 escape 节点**不带 `kind`**。M1 把 `kind` 收为 `Option`（可缺省）但值域已闭环（`model.rs:540-559`）。 | 本草稿**全部 escape 节点都写了 `kind`**，取七类词表中的四个。 | 若最终规范把 `kind` 改为必填，本稿合规；若允许缺省，本稿仍合规。无风险。 |
| U2 | **`escape` 节点与 `kind: task` 的关系**。提案 B §1.2 的 kind×uses 表说 `task \| 无 uses + escape` = L4 逃逸节点，即逃逸节点应**不带** `uses`。但我的 `command_extract` / `runtime_ctx` / `human_channel` 需要 `consumes` / `emits` / `reads` / `writes` 才能串进拓扑（样例 4 的 `synth` 逃逸节点同样带 `reads` + `emits`，说明"无 uses"不等于"无端口"）。 | 遵循样例 4 形态：逃逸节点有 `kind: task`、**无 `uses`**，但有端口与读写声明。 | 若 M2 的 E1006/E1005 把"逃逸节点必须无 consumes"写死，本稿会被拒。这是本稿最可能被拒的一处。 |
| U3 | **`route` 的 `goto: exit` 语义**。提案 B §1.5 说"goto: exit 的分支不产生边"，但没说 exit 是"退出整个环"还是"退出当前迭代"。我把 `format_check` 的 submit 规则写成 `goto: exit`，同时用环级 `exit_when` 表达同一判据（双重保险），参照样例 2 的 `qa` 节点 `route.default: exit` + 环 `exit_when: attempt.passed == true` 形态。 | 沿用样例 2 形态（route 与 exit_when 并存）。 | 语义解释若不同，只影响"submit 后是否还跑一轮"，不影响静态合法性。 |
| U4 | **`route` 规则的互斥覆盖**。提案 B §1.5 归一化算法要求"规则两两不相交 + default 覆盖全部出边"，但**编译器无法在语法面证明不相交**（§2 明确说"不需要任何图分析"，靠构造保证）。我的 `format_check` 有两条规则（`passed == false → agent` 与 `verdict.submit == true → exit`），语义上可同时为真（格式错但恰含 submit 串）。 | 按文档序写：失败规则在前（先重述），submit 规则在后。若编译器按"第一条命中"归一化（提案 §1.5 第 2 步 `guard_i = when_i ∧ ¬(when_1 ∨ … ∨ when_{i-1})`），则失败优先，语义合理。 | 若 M4 判定两条规则"目标相同/不可达"才会报错；本稿两条目标不同（agent / exit），应可通过。 |
| U5 | **`exit_when` 引用体内节点端口**。提案 B §1.4 的 `attempt` 绑定是"体内验证面节点的 passed 与显式 emits 端口"，样例 3 用 `tally.result.top_share_milli >= 700`（体内 transform 节点 id 根）作 exit_when。我用 `format_check.verdict.submit == true`，属"体内节点 id 根 + 对象端口字段"，与样例 3 同形。 | 采用样例 3 同形写法。 | 若 M4 只允许 `attempt.*` 而不允许体内节点 id 根，需改写为 `attempt.verdict.submit`。**这是我最不确定的一条 CEL 写法。** |
| U6 | **`human` 构造与 `escape` 构造的关系**。卡片⑥(b) 8 把人工介入整体归为逃逸，但提案 B §1.3 的 `human` 构造（`station` / `role` / `quorum` / `resume.schema`）恰好能表达"人工工位 + 类型化恢复值"。 | **双写**：事件驱动的动态注入进逃逸节点 `human_channel`（`dynamic_tool_registry`）；声明式人工工位用标准 `human` 节点 `human_help`（`resume.schema` = `{message, source}`）。二者由 `human_gate`（check + unit）决定走哪条。 | 若评审认为 `human` 构造足以覆盖⑥(b) 8、逃逸节点多余，可删 `human_channel` 只留 `human_help`；反之若认为 `human` 不足以覆盖动态注入，可删 `human_help`。我保留两者以免丢机制。 |
| U7 | **`checkpoint: true` 的位置**。提案 B §1.2 只说它是 LangGraph checkpointer 的声明位、快照语义由 af-plan 承载，没有规定哪些边该标。 | 标在两处：① `agent → format_check`（每轮动作落点，最像 checkpointer 的"步快照"）② `extract_patch → evaluate`（交付判定的恢复点）。 | 纯声明位，标多标少都不影响编译。 |
| U8 | **`select_best` 取最终 patch**。`extract_patch` 用 `select_best{port: workspace, by: seq, prefer: max}` 从 diff 快照序列取末态 diff。语义上正确（末次快照 = 最终工作树），但 `by: seq` 依赖 `patch.seq` 由执行器单调填充——这是我对执行器的一个**未在卡片中写明**的假设。 | 在 `patch` 类型里显式建 `seq: integer` 字段，把假设落到 schema 而不是藏在语义里。 | 若 `seq` 无人填，`select_best` 退化为任意选择。**编译器不会发现此问题**（输出侧字段映射属 E9003 装载期）。 |
| U9 | **失败类与卡片④的对应**。卡片④ 列出 6 类失败（格式违规 / 命令执行失败 / 重复失败 / 补丁自验证失败 / 越权 / 环境异常）+ 4 条终止判据。我把"补丁自验证失败"并入 `tool_error`（模型跑测试看到失败后继续循环，属正常自修正而非失败类），把"重复失败/无进展检测"并入 `budget_exhausted`（卡片明说"无固定重试上限，靠全局步数预算收敛"）。 | 用提案 B 的 9 类闭环词表：`schema_invalid` / `tool_error` / `timeout` / `unauthorized` / `environment_failure` / `budget_exhausted`。 | 词表本身是闭环的，不会因归并而非法；语义保真度的争议在此。 |
| U10 | **`meta.topology_selector` 未使用**。裁决书 §二-1 吸收了它（编译期语义），但卡片⑥(a) 12 条里**没有一条需要"在多个候选图之间选"**——SWE-agent 的变体（不同 ACI 变体 / 不同 prompt 模板）是消融实验维度，不是单次运行的运行时决策。 | 不写 `topology_selector`。若评审希望把"ACI 变体消融"建模为多个版本化候选图 + 编译期选择，需要另出一份变体图（`pkg.sweagent.aci_v2@1` 之类），是**另一个交付物**，不是本稿的缺口。 | 无静态风险，属**范围判断**而非遗漏。 |
| U11 | **`agent` 节点的两个 `latest_k` store 段**。`context.sections` 里 `agent_turns` 与 `tool_turns` 各一段，依赖提案 B §1.2 的**内建**读侧交错合并（"多个 `message_log` 段按 `step` 序交错合并，零字段"）。 | 直接用两个 `message_log` 段，未写任何 merge 字段（照样例 5）。 | 若 M2 实现的交错规则与"assistant/tool 交替"不一致，交错顺序会变，但不影响合法性。 |
| U12 | **`emits` 不接受内联原始类型**（M1 实测：`{type: boolean}` 被拒，E1003）。因此 `human_gate` 的 `ask` 布尔走**具名类型** `human_decision`（对象 `{ask: boolean}`），而非内联 `boolean`。 | 具名类型化，与提案 §1.2 "对象 schema 必须住 `types` 表"一致。 | 无风险（已在 M1 实跑确认）。 |

---

## 4. 关键设计取舍（供评审快速判断）

1. **"单节点循环"的实现层次**：卡片⑥(a) 1 说"单节点循环"，但⑥(a) 5（解析器）、⑥(a) 11（环境）、⑥(a) 10（评测器）都要求独立的**标准组件**。二者不能同时按字面满足。我的取舍：**LLM 节点唯一**（`agent` 是环体里唯一的 `uses.model` 节点），其余节点是非 agent 的标准组件（`check` / `transform` / tool 执行节点 / escape）。这是"单 agent 串行 ReAct 环"的语义，而不是"只有一个节点"的拓扑。如果评审要求严格的单节点（把解析/执行都塞进 agent 运行时），则⑥(a) 5/10/11 就没有落点——我判断当前取舍更忠实于卡片⑥(a) 整体。
2. **环体入口 = `agent`**：提案 B §1.3 规定内联体 `entry = nodes 首元素`，我把 `agent` 放在体节点首位。
3. **格式校验用 `check` 而非 `gate`**：`format_check` 用 `uses.unit`（外部判定单元）而非内建 `assert`，因为 ACI 的命令格式校验是"解析器/schema 校验组件"（卡片⑥(a) 5 明确写"标准「输出解析 / schema 校验」组件"），`check` 语义更贴。`check` 的内建 `passed` 端口正好用于 route 规则。
4. **轨迹双槽而非单槽**：`agent_turns` + `tool_turns` 两个 `message_log`，靠内建交错还原 SWE-agent 的 "assistant(thought+command) / user(observation)" 交替结构——这与样例 5（LangGraph）处理 reducer 多写者同法。
5. **金标准隔离**：`eval_refs` 槽标 `eval_input: true`，只有 `evaluate`（check + unit）读它；`agent` 看不见——对应卡片③"模型看不到 SWE-bench 的参考答案与金标准补丁"。

---

## 5. 自检记录（全部实跑，命令与输出见下）

| 检查 | 命令 | 结果 |
|---|---|---|
| YAML 解析 | `python3 -c "import yaml; yaml.safe_load(open('SWE-agent.yaml'))"` | **PASS**（顶层键 `['edges','meta','nodes','policies','stores','types','version']`，七段齐全） |
| M1 静态校验（af-dsl crate 真跑） | 见 §5.1 | **0 violations** |
| CEL 保守子集（cel-parser 0.10.1 真跑） | 见 §5.2 | **7/7 PASS，0 fail** |
| 六节结构自检 | 见 §5.3 | **0 issues** |

### 5.1 M1 静态校验（真实编译器前端）

用 `af-wt-phase2-dsl/crates/af-dsl` 的 `load_str` + `validate` 实跑（非本文档自造规则）：

```
violations = 0
M1 VALIDATE: 0 violations
```

覆盖的 M1 码位：E0001–E0004（信封）、E1001–E1004（形状/词表）、E2001（悬空）、E2003（重复 id）、E2104/E2105/E2106/E2107（拓扑扩展）、E2201（边端口类型）、E2202（output.from 不发射）、E2204（失败类路由）、E2205（未知类型名）、E2207（预算 cap/作用域）、E2208（retention 无界）、E2311（多写者）、E2312（map 共享槽）、E2211（carried 未覆盖）。

**M1 抓出并已修正的一处真实缺陷**（证明该检查有判别力、非全数放行）：
- `emits` 里写内联原始类型 `{type: boolean}` → 报 `E1003 invalid type: emits 端口映射值只允许 {from_body: 节点.端口}`。已改为具名类型 `human_decision`（对象 `{ask: boolean}`）。

**另有一处是我自己脚本的缺陷，不是草稿的缺陷**（如实记录以免误导）：首版自检脚本报"store `agent_turns` 声明写者 `agent_loop.agent` != 实际写者 `agent`"——根因是脚本用**局部 id** 比较而草稿用**从根解析的点号路径**（提案 B §1.3 规定 `writer` 是"节点 id 或点号路径"）。M1 的 `inv2.rs` 正是按点号路径比对（`n.path` vs `declared.path`），对该草稿报 0 违例。脚本已修正为点号路径比较。

### 5.2 CEL 保守子集（cel-parser 0.10.1 实跑）

判定三项：① `Parser::new().parse()` 可编译；② `references().functions() ⊆ 算子白名单`（`_==_ _!=_ _<_ _<=_ _>_ _>=_ _&&_ _||_ !_ _+_ _-_ _*_ _/_ _%_ @in`）；③ `references().variables()` ⊆ 允许根（§1.4 位置词表 + 本稿节点 id 根）。

```
PASS format_check.verdict.submit == true
PASS format_check.passed == false
PASS format_check.verdict.submit == true
PASS human_gate.decision.ask == true
PASS budget.turns_spent >= budget.turns_cap
PASS budget.tokens_total_spent >= budget.tokens_total_cap
PASS budget.cents_spent >= budget.cents_cap
---- total=7 fail=0
```

7 条表达式 = 草稿里全部 `route.rules[].when`（4）+ 环 `exit_when`（1）+ `policies.stop`（3）。零函数调用、零未知根。

### 5.2b 四条 L0 不变量 + route 覆盖的近似自检

M1 尚未实现 INV-1 / INV-3 / INV-4 与 route 归一化（M2/M3/M4），我用独立脚本按提案 B §1.5 / §5 的规则近似核对：

```
INV-1/INV-3/INV-4/route approx check: PASS
```

覆盖：① LLM 节点禁 `reads`（INV-1）；② LLM 节点的 `edge` section 端口集恰等于其入边端口集、且 `consumes` 覆盖全部入边端口（E2304）；③ `check`/`gate`/`human` 节点的入边生产者不得是自身（E2321）；④ `eval_input` 槽的读者必须是 `check`+`unit` 节点（E2331）；⑤ 每个 `route` 的 `goto` 必是本节点出边目标或 `exit`、出边全覆盖、规则目标不重复（E2101/E2102/E2103 近似）。

**这些是近似核对，不等于编译器的 M2/M3/M4 判定。**

### 5.3 六节结构自检（对应任务要求的六项）

```
escapes:
  env_boot: kind=env_adapter pct=6
  command_extract: kind=free_text_parser pct=10
  runtime_ctx: kind=runtime_context_mutation pct=8
  human_channel: kind=dynamic_tool_registry pct=4
escape total pct = 28
types = 13  stores = 4
STRUCT CHECK PASS: 0 issues
```

逐项：

| 自检项 | 判定依据 | 结果 |
|---|---|---|
| **信封** | `version: 1`；顶层键集恰为七段 `edges/meta/nodes/policies/stores/types/version`；M1 E0001–E0004 全过 | PASS |
| **类型表** | 13 个具名类型；端口/槽位引用的类型名全部登记（无悬空）；`signal` 未被误登记为类型；端口无内联对象 schema | PASS |
| **单写者** | 4 个槽各恰一个写者，且与 `store.writer` 点号路径一致：`agent_turns←agent_loop.agent`、`tool_turns←agent_loop.runtime_ctx`、`workspace←agent_loop.env_exec`、`eval_refs←env_boot`；`carried` 覆盖体内写入的三个槽 | PASS |
| **配额** | 每个 `context.sections` 条目 `quota_tokens` 为正整数；`from` 取值在五类来源词表内 | PASS |
| **预算** | 4 条预算：dimension 在 8 类词表内、cap > 0、scope 前缀合法（`loop:` / `plan` / `node:`），M1 E2207 过 | PASS |
| **逃逸记账** | 4 个逃逸节点，四字段（`impl_ref`/`reason`/`owner`/`share_budget_pct`）+ `kind` 齐全，`kind` 全在七类闭环词表内；`share_budget_pct` 合计 28% ≤ 30% 警戒线 | PASS |

**未跑项（如实声明）**：M2/M3/M4 的构造形状校验（E1005 构造×kind 组合、E1007 空体内联体）、CEL 保守子集的**编译器侧**静态判定（M4 才有）、transform 输出侧字段映射（E9003 装载期）——这些模块在本次交付时未实现/未跑。§5.2b 的四条 L0 不变量与 route 覆盖是我按提案 §1.5/§5 规则写的**近似脚本**，不是编译器判定。本稿用 §5.1–5.3 三个独立脚本近似覆盖，但**不能替代**编译器裁定。

---

## 6. 计数

- **expressible = 12**（卡片⑥(a) 全部 12 条落到标准拓扑/组件，无一条需逃逸才能表达）
- **escapes = 4**（草稿中 `escape` 构造节点数；覆盖卡片⑥(b) 全部 8 条机制，映射关系见 §2 表）
- 逃逸占比 `share_budget_pct` 合计 28%
