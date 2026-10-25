# Voyager → AFB DSL 翻译记录

- 目标：Voyager（Minecraft 开放世界：自动课程 + 可执行代码技能库 + 迭代提示机制，Wang et al. 2023）
- 草稿：`/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿/Voyager.yaml`
- 翻译代理：翻译·Voyager（第二阶段 G3 对齐翻译工作流）
- 日期：2026-10-24

## 0. 输入与依据（本次实际读过的文件）

| 文件 | 用到的部分 |
|---|---|
| `计划/研究组/对齐机制卡/INDEX.md` | 第 3 行指向 `对齐机制卡/Voyager.md`；第 42 行「Voyager 卡内个别实现细节与预算数字带"存疑"标注，翻译 DSL 时按机制层采信、数字层复核」 |
| `计划/研究组/对齐机制卡/Voyager.md` | 全文六节；重点 ⑥(a) 1–8（可映射项）与 ⑥(b) 1–7（逃逸项）、③ 数据流、④ 失败处理 |
| `计划/研究组/DSL-语法提案-B.md` | §1.1 七段结构树、§1.2 字段表、§1.3 六构造、§1.4 CEL 保守子集、§1.5 route 归一化、§2 正交性、§4 样例 2/3/6、§5 INV-1..4、§6 码表 |
| `计划/研究组/DSL-语法择优-裁决-20261024.md` | §二-1 `meta.topology_selector`（编译期解析）、§二-2 `escape.kind` 七类闭环词表（dynamic_tool_registry / program_synthesis / meta_loop / runtime_context_mutation / env_adapter / free_text_parser / llm_predicate） |
| `af-wt-phase2-dsl/crates/af-dsl/testdata/sample1-6.yaml` | M1 已解析通过的 golden 种子（本机实为 `sample1.yaml`…`sample6.yaml` 六个文件，`sample6.yaml` = 提案 B §4.6 的 Voyager 样例） |
| `af-wt-phase2-dsl/crates/af-dsl/src/{model.rs,shape.rs,validate/*}` | 实际 AST 字段与 M1 判定规则（`escape.kind` 已实现为可选闭环枚举，`model.rs:535-561`；M1 覆盖信封+七段+引用闭包+INV-2） |

> 提案 B §4.6 的样例 6 本身就是 Voyager 稿。本草稿**不是复刻它**：在其骨架上补了卡 ⑥(a)-1 的「执行反馈=唯一回流通道」（`exec_log` 槽 + context store 段）、卡 ⑥(a)-7 的环境观察工具节点（`observe`）、卡 ⑥(b)-3/⑥(b)-6 的两个逃逸节点（`raw_action` / `verdict`），并按裁决 §二-2 给全部逃逸节点补 `escape.kind`。两份都过 M1（见 §4）。

## 1. 机制 → 语法映射表（逐条对应卡 ⑥(a)）

| 卡 ⑥(a) | 机制 | AFB 落点（语法面） | 说明 |
|---|---|---|---|
| 1 | 迭代提示机制 → 单节点自循环（ReAct 型），环境反馈以工具返回通道回灌同一节点上下文 | 内层 `acquire` 受控循环；`generator`（LLM task）+ 反馈槽 `exec_log`（`kv`，`writer: explore.acquire.code_exec`，`retention.max_items: 1`）+ `generator` 的 `{from: store, store: exec_log, policy: full}` context 段 | 卡片强调「回灌同一节点上下文，非多节点流水线、非对话式历史累积」：因此反馈走**状态槽**而非图边/消息累积，槽只保留最近一次执行结果 |
| 2 | 自动课程 → 双层循环；课程表是跨步更新的状态工件 | 外层 `explore` loop（体 = `observe` → `proposer` → `acquire`）+ 内层 `acquire` loop；`curriculum` store（`collection`，`writer: explore.proposer`） | 外层每轮 = 一个课程步；`proposer` 产目标写入课程表，`acquire` 以 `args: {goal_text: proposer.goal.text, world: observe.state}` 绑定（隐式依赖边） |
| 3 | 技能库 → 持久化记忆组件 + 工件库；条目 = 名称/描述/代码 | `stores[].skill_library`：`type: vector_index`、`item: skill_entry`（`name`/`description`/`code`）、`lifecycle: persistent`、`retention.max_items: 512`、`writer: explore.acquire.curator` | 只增不减、跨回合/跨会话可见 |
| 4 | 任务-技能匹配 → 检索式记忆原语（top-k 注入上下文） | `generator` 的 context 段 `{from: store, store: skill_library, policy: retrieve, component: pkg.openworld.similarity@1, args: {k: 3}, quota_tokens: 1500}` | 只注入名称+描述+代码；`k` 取 3（卡 ⑤ 标注 k 值存疑） |
| 5 | 自我验证 → 节点内的判据步骤/守卫（非独立智能体） | `generator` 同一次生成发出 `check: self_check`（`pass`/`reason`）端口 | 符合「不是独立 agent，是同一次生成的固定槽位」；该端口与 `draft` 同源，`admit` gate 用它做门禁（INV-3 不触发：gate 的生产者不是它自己） |
| 6 | 技能入库条件 → 条件边（执行成功 ∧ 自验证通过 → 写库） | `admit`（kind `gate`）：`assert: "inputs.report.ok && inputs.check.pass && inputs.judgement.achieved"`；`route: {default: curator, rules: [{when: "admit.passed == false", goto: exit}]}`；`curator`（transform）单写 `skill_library` | 边无 `when`（B-R3），条件一律走 `route`；入库由 `curator` 的 `project` op 落到 store |
| 7 | 环境交互 → 工具集；代码块调用即工具调用 | `observe` 节点 `uses: {tool: pkg.openworld.env@1}`（环境动作 API 的 L3 组件）；`code_exec` 逃逸实现内部引用同一组件（装载期类别核对 E9003） | DSL 声明面只暴露声明式动作；未声明动作组合走 ⑥(b)-3 的原始通道 |
| 8 | 上下文模板 → 固定槽位提示模板（任务指令/技能代码/执行反馈/自我验证+计划） | `generator` 的 context 段序列：`template: pkg.openworld.iterative_prompt`（含自我验证/计划槽）+ `arg: goal_text`（任务指令）+ `store: skill_library retrieve`（技能代码）+ `store: exec_log`（执行反馈）+ `store: env_state`（世界状态） | 拼接顺序即 section 顺序（提案 B §1.2） |

## 2. 卡 ⑥(b) 逃逸清单（七类词表记账）

| 卡 ⑥(b) | 机制 | 判定 | 落点 / `escape.kind` |
|---|---|---|---|
| 1 | 运行时生成并执行任意 Python 代码 | **需逃逸** | 节点 `code_exec`，`kind: program_synthesis`，`share_budget_pct: 20` |
| 2 | 运行时由 LLM 改写图与工件结构（下一节点运行时才确定） | **近似，无独立逃逸节点** | 「下一步做什么」在草稿里是**数据**（`proposer` 产出 goal → `curriculum` 槽 → 循环下一迭代），拓扑保持静态；纯 node 注入接口未建模（Voyager 论文本身未改拓扑）。运行时工件写入的残余需求并入 `code_exec`（技能代码入库后被检索调用＝运行时可扩展工件面） |
| 3 | 代码与游戏 API 的动态面对接（模型探索出未声明的动作组合） | **需逃逸** | 节点 `raw_action`，`kind: dynamic_tool_registry`，`share_budget_pct: 5` |
| 4 | 向量/嵌入语义检索（top-k 相似度） | **不需逃逸**（卡标注"存疑"，此处判为可表达） | AFB 的 store 类型词表含 `vector_index`，context 段有 `retrieve{component,k}` 策略 → `skill_library: vector_index` + `component: pkg.openworld.similarity@1` |
| 5 | 跨会话持久化状态（技能库/课程表跨 episode） | **不需逃逸** | `stores[].lifecycle: persistent`（技能库）；课程表按卡 ③ 属本计划执行态，用 `lifecycle: run` |
| 6 | 软性/概率性终止判据（环境隐藏状态 + LLM 自验证共同决定） | **需逃逸** | 节点 `verdict`，`kind: llm_predicate`，`share_budget_pct: 5`（CEL 只能表达硬判据，软判据以非确定性守卫注入） |
| 7 | 无固定终点的运行与动态预算注入 | **L1 近似，无逃逸** | `policies.budgets`（scope plan）+ 外层 loop `exit_when: "budget.cents_spent >= budget.cents_cap * 9 / 10"` + `failures[budget_exhausted] → terminal/completed`；DSL 无「运行时注入停止条件」接口，残余缺口记此 |

**逃逸账**：3 个逃逸节点，四字段（`impl_ref`/`reason`/`owner`/`share_budget_pct`）齐全，`kind` 取值全部落在裁决 §二-2 的七类闭环词表内（用到的三类：`program_synthesis`、`dynamic_tool_registry`、`llm_predicate`）；`share_budget_pct` 合计 30（20+5+5），压在提案 B §1.3 的 >30% 警戒线下。未用的四类（`meta_loop`/`runtime_context_mutation`/`env_adapter`/`free_text_parser`）在本目标无对应机制，不硬造逃逸节点。

## 3. 语法不确定点（诚实清单）

| # | 不确定点 | 现状处理 | 若裁决改口 |
|---|---|---|---|
| U1 | `escape.kind` 是裁决 §二-2 的新增字段，提案 B §4 样例（= golden `sample6.yaml`）没有 | 采用之（`af-dsl` M1 已实现为可选字段且值域闭环，`model.rs:540-561`） | 若正本回到四字段，删掉三处 `kind:` 即可，其余结构不变 |
| U2 | `code_exec` 与 `raw_action` 在论文里是同一沙箱 API 的两面 | 拆成两个逃逸节点，为按七类词表分别记账（program_synthesis vs dynamic_tool_registry） | 可并入 `code_exec` 的 `reason`，逃逸数由 3 降 2 |
| U3 | 「自验证不通过 → 任务保持不变重规划」（卡 ④-2）的运行时合成语义 | 用 `admit.route` 的 `goto: exit` + `failures[gate_refused].route: next_iteration` 组合表达；正本未定义 `exit` 与 `next_iteration` 的优先级 | 备选：体内加一个 no-op 汇点节点，让失败路径自然结束本轮迭代（`max_iterations` 耗尽才换目标） |
| U4 | `skill_library` 用 `vector_index` 而非 `collection`（golden 用 `collection`） | 选 `vector_index`（语义上技能库是嵌入检索库）；M1 两者都接受 | 若装载期要求统一为 `collection`，改一行即可，`retrieve` 段不变 |
| U5 | 世界状态分槽：INV-2 单写者约束下，程序路径状态（`env_state`）与原始动作路径观察（`action_log`）分成两个槽 | 两个槽都进 `proposer`/`generator` 上下文，代价是提议器要合并两份快照 | 若允许一个世界状态槽，需放宽单写者或引入合并节点 |
| U6 | 预算与循环上限数字（cents 3000 / tokens 3,000,000 / turns 400；外层 200 步、内层 6 次） | 占位值。卡 ⑤ 明确标注论文预算数字"存疑"，INDEX 第 42 行要求「机制层采信、数字层复核」 | 按论文复核后替换数值即可，结构不变 |
| U7 | 嵌套 loop 的预算作用域 | 内层 `acquire` 无法写成 `loop:acquire`：M1 的 scope 解析从根图起（`Index::resolve_root_path`），只能用 `loop.max_iterations` 表达内层尝试次数 | 若 M4 支持嵌套作用域，内层可另立 turns 预算 |
| U8 | `meta.topology_selector`（裁决 §二-1，编译期解析） | 本目标未使用：Voyager 只有单一拓扑 | — |
| U9 | 「环境状态观察」的注入粒度：论文是每步文本快照 | 草稿放在外层课程步首（`observe` 节点）+ 内层每轮读 `env_state` 槽 | 若要求严格每步快照，`observe` 需下沉进内层体（会引入额外写者，需并入 U5 的分槽方案） |
| U10 | L4 逃逸节点直写状态槽（`code_exec` 声明 `writes: [exec_log, env_state]`） | INV-2 只看 DSL 声明的写者集合，静态判定通过 | 若运行时不允许逃逸实现直写槽，需在 `code_exec` 后加 transform 投影节点（多 2 个节点） |
| U11 | `share_budget_pct` 是「每舱占比」还是「全图合计」 | 按合计 30% 处理 | — |
| U12 | 卡 ② 的「自我验证器」是否独立成节点 | 判为独立节点（`verdict`，因它读环境状态而非同一次生成），但卡片未规定节点粒度 | 若判为纯槽位，可删 `verdict`，`admit` 的 assert 退回两条件 |

## 4. 自检记录（命令与输出，均为本次实跑）

| 检查 | 命令 | 结果 |
|---|---|---|
| ① YAML 可解析（任务指定） | `python3 -c "import yaml,sys; yaml.safe_load(open('.../对齐草稿/Voyager.yaml'))"` | 通过；附加打印：top-keys = `['edges','meta','nodes','policies','stores','types','version']`（七段无漂移），`version` 为 int 1 |
| ② 真实 M1 前端校验（信封+七段+引用闭包+INV-2） | `/tmp/afb-voyager-check/target/debug/afb-check .../Voyager.yaml`（/tmp 离线复制的 `af-dsl` crate 快照，自带 `afb-check` 小程序） | `OK: load + M1 validate clean`（0 违例） |
| ③ CEL 保守子集（编译/算子白名单/根绑定/布尔求值） | `rustc --edition 2021 -L dependency=/tmp/afb-check/target/debug/deps --extern cel_interpreter=.../libcel_interpreter-20c7bddb05aae15c.rlib -o /tmp/afb-cel-check2 /tmp/cel_check.rs` 后 `/tmp/afb-cel-check2 /tmp/voyager_cel.tsv`（用既有 cel-interpreter 0.10 rlib 经 `rustc` 直链编译的独立校验器，不新建 cargo 工程） | `total=5 fail=0`：外层 `exit_when`、内层 `exit_when`、`admit.assert`、`admit.route.rules[0].when`、`policies.stop[0].when` 全 PASS |
| ④ 六节自检（信封/类型表/单写者/配额/预算/逃逸记账 + route 覆盖/safety point/carried 覆盖/INV-1 端口闭合） | `python3 /tmp/voyager_selfcheck.py .../Voyager.yaml`（自写脚本） | `checks=135 FAIL=0  RESULT: PASS` |
| ⑤ 校验器判别力（负例） | 负例 a：`curator` 追加写 `curriculum`；负例 b：`admit.consumes` 删 `judgement` | M1 对 a 报 `StoreMultiWriter`+`CarriedNotCovering`，对 b 报 `EdgePortTypeMismatch`；自写脚本对 a 报同两项 |

**未跑/不可跑（如实）**：
- 编译器 M2–M4（context.sections 语义、route 归一化、CEL 静态判定、topology_selector）尚未落地于 `af-dsl`，故 ③④ 只是等价的独立实现，**不是**编译器裁决；最终通过与否由编译器决定。
- 运行时行为（逃逸舱实现、检索组件、持久化后端）本机无环境，**未运行**。
- ②③④ 的三个工具都在 `/tmp`（`afb-voyager-check`、`afb-cel-check2`、`voyager_selfcheck.py`），**不是交付物**；本任务只交付 `Voyager.yaml` 与本文件两个文件。
- ①②③④ 四项在**最终版文件写定后**已完整重跑一遍（命令与上表一致），结论未变。

## 5. 计数

- 卡 ⑥(a) 可用标准拓扑/组件表达的机制数：**8**（全部 8 项均落在 nodes/edges/stores/构造面上，无一需要逃逸）。
- 需逃逸舱的机制数：**3**（⑥(b)-1 program_synthesis、⑥(b)-3 dynamic_tool_registry、⑥(b)-6 llm_predicate）。
- ⑥(b) 其余 4 项：2 项由标准构造直接表达（⑥b-4 向量检索、⑥b-5 跨会话持久化），2 项为 L1/数据驱动近似（⑥b-2 运行时工件/拓扑、⑥b-7 动态预算与终止）。
