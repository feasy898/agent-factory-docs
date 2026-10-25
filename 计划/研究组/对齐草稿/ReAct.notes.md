# ReAct → AFB 草稿翻译记录

- 目标：**ReAct**（Reasoning + Acting 交错循环，Yao et al. 2022）
- 交付：`对齐草稿/ReAct.yaml`（AFB 草稿，`version: 1` 信封 + 七段）
- 依据来源（本记录的全部结论都基于下列文件的实读/实跑）：
  - `计划/研究组/对齐机制卡/INDEX.md`（第 14 行确认目标卡片为 `ReAct.md`，成，3069 字）
  - `计划/研究组/对齐机制卡/ReAct.md`（六节全文，重点 ⑥(a) 8 条 / ⑥(b) 8 条）
  - `计划/研究组/DSL-语法提案-B.md`（§1 七段字段表 + 六构造、§1.4 CEL 保守子集、§1.5 route 归一化、§2 正交性、§4 样例 1/2/3、§5 四条 L0 不变量、§7 分级表第 1 行「ReAct = 优雅，残余 L4：⑥b 1/2/8」）
  - `计划/研究组/DSL-语法择优-裁决-20261024.md` §二（① `meta.topology_selector` 编译期解析语义、② `escape.kind` 七类闭环词表）
  - `af-wt-phase2-dsl/crates/af-dsl/testdata/sample1.yaml`（M1 已解析通过的 golden 种子 —— 注意任务书写的 `sample1-6.yaml` 实际不存在，仓内为 `sample1.yaml`…`sample6.yaml` 六个文件）
  - `af-wt-phase2-dsl/crates/af-dsl/src/model.rs`（M1 真实 serde AST：字段闭包、`escape.kind` 词表枚举、`emits` 的 `from_body` 语义）
- 定位：本文件是**草稿翻译记录**，不是验收裁决。草稿按卡片⑥(a)用标准拓扑/组件表达，⑥(b) 用 `escape` 构造 + 七类词表逐条记账；论文定义性机制无法在 L0–L3 落点的一律走逃逸，**没有编造语法**。

---

## 1. 草稿形态一句话

单根图、一个受控循环节点 `react_loop`（内含 10 个体节点、15 条体边、2 条分支 route）：

```
registry(escape) ─→ reasoner(LLM,唯一写者) ─→ compose(escape) ─→ parse(escape) ─┬─→ judge(escape) ─→ action_valid(gate) ─┬─→ env(escape) ─┬─→ reasoner(观察回边)
                                                                                      │                                 │              └─→ beliefs(escape) ─→ assembler(escape) ─→ reasoner
                                                                                      └───────────────────────────────→ action_valid                                    └─→ recovery(escape) ─→ reasoner(hint)
```

- 根图 `edges: []`：交错循环整体在循环体内（与 golden `sample1.yaml` 的「单节点、工具回灌在节点运行时内」不同——卡片⑥(a)-1 明确要求「工具节点回边」，故本稿把工具/环境节点显式化，代价是拓扑更展开）。
- `meta.output: {ref: answer, from: react_loop}`，答案由体内 `judge.answer` 经 `emits.from_body` 转发。

---

## 2. 机制 → 语法映射表（逐条对应卡片⑥(a) 1–8）

| 卡⑥(a) | 机制原文（摘） | AFB 落点（ReAct.yaml 路径） | 说明 |
|---|---|---|---|
| 1 | 单节点循环 + 工具节点回边（policy 自循环，工具结果连回 policy） | `nodes[react_loop].loop.body`（`registry→reasoner→…→env→reasoner` 环）+ 体边 `env --observation--> reasoner` | 环由 `loop` 构造（受控循环）承载，`max_iterations` 给出硬界；工具/环境节点显式化为 `env` 逃逸节点并以「观察」端口回灌 policy |
| 2 | 动作调用 = 工具 schema + 位置参数（`search_entity(entity)`、`click[button]`） | `types[action_call]{tool,args_text,matched}` + `reasoner.uses.tools: [pkg.reactkit.hopqa_api, pkg.reactkit.lookup]` | 动作名 + 位置参数串进 typed 端口；静态工具面用 `uses.tools` 绑定（`uses` 是 LLM/工具分野的落点） |
| 3 | 观察返回 = tool_result 文本注入的「工具→上下文」通道 | `types[observation]{text}` + 体边 `env --observation--> reasoner` + context 段 `{from: edge, port: observation, policy: project}` | 观察是纯文本、不归一化不改写（卡片③）；通道 = 一条类型化边 + 一段 context 引用 |
| 4 | 轨迹 = 追加式工件（append-only transcript），循环体的 message 数组 | `stores[trajectory]{type: message_log, writer: react_loop.reasoner, retention: {max_items: 128}}` | 唯一写者 = policy 节点；观察回灌在节点运行时内串行追加（与 golden `sample1.yaml` 同处理） |
| 5 | 记忆 = 无外部记忆库，上下文窗口即唯一记忆 | `reasoner.context.sections` 中**无** `memory` 组件，只有一条 `{from: store, store: trajectory, policy: latest_k, args: {k: 24}}` | 全图仅两个槽（trajectory / beliefs），其中 beliefs 是⑥(b)-4 的可覆盖断言区而非长期记忆；token 随步数线性膨胀由 `tokens_total` 预算与 `latest_k` 上界体现 |
| 6 | 停止 = 终止动作触发条件出边（finish → 结束节点） | ① `judge.route.rules[0]: {when: "judge.verdict.done == true", goto: exit}`；② `loop.exit_when: "judge.verdict.done == true"`；③ `policies.stop[0]: last_tool.first_line in ['FINISH','FINAL ANSWER'] → completed` | 三层：图内出边终止、循环出口、图级停止哨兵 |
| 7 | 预算 = 循环节点 max_iterations 计数器 | `loop.max_iterations: 12` + `policies.budgets[0] {dimension: turns, scope: loop:react_loop, cap: 12}` | 卡片自标「步数具体数值存疑」，12 沿用 golden `sample1.yaml` 的 turn_cap=12（见 §4-U7） |
| 8 | 角色/提示 = 单一 policy 角色；少样本示例为静态 prompt 常量；「推理先于动作」为边序约束 | ① 全图唯一 LLM 节点 `reasoner`（`uses.model: route.main@1`）；② `{from: template, template_ref: pkg.reactkit.fewshot_react}`（静态常量）；③ 边序 `reasoner→compose→parse→judge→action_valid→env` | 「先推理后动作」由拓扑边序表达，无专用语法位 |

---

## 3. 逃逸清单（卡片⑥(b) 1–8 → 七类词表逐条记账）

卡片⑥(b) 共 8 项，恰好覆盖裁决 §二-2 的七类词表（`runtime_context_mutation` 用两次）：

| 卡⑥(b) | 机制原文（摘） | escape 节点 | `escape.kind` | share_budget_pct | 逃逸理由（为什么 L0–L3 无落点） |
|---|---|---|---|---|---|
| 1 | 动作空间运行时才确定（ALFWorld 词表、WebShop 由页面 DOM 决定的 click 目标） | `registry` | `dynamic_tool_registry` | 5 | `uses.tools` 只能静态声明已知动作面；运行时词表的**解析与注册**无语法位。产出 `action_space` 同时喂 policy（可见动作集）与解析器（匹配校验） |
| 2 | 自由文本双向解析：Action/Thought 由同一段生成文本启发式切分 | `parse` | `free_text_parser` | 8 | 端口是 typed 工件，核心侧只承接「已切好」的动作；启发式切分 + 与运行时词表比对得出 `matched` 必须外置 |
| 3 | 一次生成多段（Thought+Action 同批），需组合式生成 / 生成后再分派 | `compose` | `program_synthesis`（**归类存疑，见 §4-U1**） | 5 | 核心节点「一端口 = 一工件」，无法表达一次生成多产物后再分派；本节点把原始生成文本合成为 `(thought, action_text)` 复合工件 |
| 4 | 思考可被覆盖：模型后续否定先前推理，但不可变工件模型只能追加 | `beliefs` | `runtime_context_mutation` | 3 | 需要一个**可写**的断言/scratchpad 区（覆盖写），而轨迹必须保持只追加（卡片④：错误历史仍可见）。故另立 `beliefs` 槽，由该节点以覆盖写更新 |
| 5 | 语义级终止判据：「我认为已完成」由 LLM 判定后需外部解析 | `judge` | `llm_predicate` | 8 | 静态条件边只能表达 finish 动作串这一机器可见形式；语义级完成判定需 LLM 判定后回传 `completion` 工件。该节点同时透传待执行动作（未完成时继续走动作路径） |
| 6 | 错误恢复策略运行时决定（重试 / 换查询 / 回退），而非预定义 error route | `recovery` | `meta_loop`（**归类存疑，见 §4-U3**） | 5 | `failures.route` 只能给一条固定回退路径；「选哪条恢复路径」是运行时元决策，静态路由无法表达 |
| 7 | 上下文全量回灌与裁剪：轨迹线性增长，需运行时 prompt 组装器（截断/摘要） | `assembler` | `runtime_context_mutation` | 4 | `context` 段的 `latest_k`/`summarize` 只能给固定上界；自适应截断/摘要需运行时组装器。产出 `context_bundle` 注入 policy |
| 8 | 有状态交互环境契约：ALFWorld/WebShop 需 env adapter（状态保持、回合同步、非法动作反馈），非普通无状态工具 | `env` | `env_adapter` | 10 | 有状态环境契约远宽于无状态工具组件；核心侧只能承接一个「已执行动作的结果」端口 |

**逃逸记账合计**：`share_budget_pct` 逐节点 3–10，合计 **48%**（单节点最高 `env`=10%）。词表覆盖：七类全部用到，无空类、无越界值。
**四字段齐全**：`impl_ref`（包内路径，如 `packages/reactkit@1.0.0/hatches/env_adapter.py`）、`reason`、`owner`（`lang-team`）、`share_budget_pct` —— 四字段缺一即 E2210/serde E1002。

---

## 4. 语法不确定点（诚实列出，均未经编译器裁定）

| # | 不确定点 | 我的处理 | 影响 |
|---|---|---|---|
| U1 | 七类词表中**没有**「一次生成多产物 / 复合发射」这一类；卡片⑥(b)-3 无精确归类 | 归入 `program_synthesis`（生成后再分派最接近「合成」语义） | 归类标签错误不影响行为（kind 目前只记账），但健康度统计会失真 |
| U2 | `escape.kind` 的**语义**未定义：`af-dsl/src/model.rs` 只把它收为 `Option<EscapeKind>` 词表值域（M1 只校验值域），编译器不会因 kind 不同而改变行为 | 按「纯记账标签」使用，并在 reason 中写清机制 | 若将来 kind 要驱动语义，本稿的 8 个归类需重审 |
| U3 | `meta_loop` 一词在提案 A 的语境里更像「元层控制循环」（AFlow 的 MCTS 元循环），与「运行时错误恢复策略选择」不完全同义 | 归入 `meta_loop`，reason 注明是「元决策」而非「元循环」 | 归类近似；若词表严格，应新增一类或归入 `dynamic_tool_registry`（更不贴切） |
| U4 | **双通道风险**：policy 节点声明了 `uses.tools`（⑥a-2 要求），同时图中存在 `parse → judge → action_valid → env` 的显式执行路径 | 按「`uses.tools` = 动作面声明、显式边 = 执行路径」处理 | 若运行期按 `uses.tools` 自动派发，会与显式路径重复执行动作。**须由编译器/运行期裁定** |
| U5 | `policies.stop[0]` 用 `last_tool.first_line`（与 golden `sample1.yaml` 同款），但本稿的执行者是 escape 节点 `env`，「`last_tool` 绑定是否覆盖 escape 节点调用」**未定义** | 保留该条作护栏；语义终止的机器可判定副本已由 `judge.route` + `loop.exit_when` 承担 | 若 `last_tool` 不覆盖 escape 节点，该 stop 条永不触发（不致误判） |
| U6 | `policies.stop[1] {steps.tool_free >= 2}` **不是论文机制** | 保留（与 golden 一致），在 YAML 注释中标为守护性判据 | 忠实性偏差：属草稿新增的宿主级护栏 |
| U7 | `max_iterations: 12` / `turn_cap: 12` 的具体数值 | 沿用 golden `sample1.yaml` | 卡片④自标「步数具体数值存疑」 |
| U8 | **温度 0**（卡片⑤的复现前提）在 AFB 无落点：解码参数属模型 route 配置（`route.main@1`），DSL 无解码参数字段 | 只能靠 `route.main@1` 指向的包内配置承载，草稿不表达 | 论文复现条件在 DSL 面不可见 |
| U9 | `beliefs` 槽的 `lifecycle` 取 `run` 而非 `iteration` | 取 `run` + 有界 `max_items: 8` | 提案 §8-3 说 body 内声明 store 一律 `iteration` 语义；若 `iteration` 会在迭代起始重置，会抹掉上一轮写入的覆盖结果，故取 `run` |
| U10 | 卡片⑥(b)-4 与 ⑥(b)-7 是两处独立机制，却共用 `runtime_context_mutation` 一类 | 拆成两个节点（`beliefs` / `assembler`），保持 1:1 可追溯 | 词表粒度粗于机制粒度 |
| U11 | `meta.topology_selector`（裁决 §二-1）**未使用** | ReAct 单一拓扑，无候选图可切换 | 符合语义（选择器只在多候选图时有用）；若后续要按任务族切图（HotpotQA / ALFWorld / WebShop），此处是插点 |
| U12 | 首轮迭代没有 `observation` 与 `context_bundle` | 两段 context 标 `optional: true` | 依赖提案未明示的「可选入边端口」语义（golden `sample5.yaml` 有同款用法） |
| U13 | `carried` 必须同时登记 `trajectory` 与 `beliefs`（二者皆「体内写、体外声明」） | 双登记 | 提案 §8-3 的窄化（体内声明一律 iteration）导致此绕度 |
| U14 | **INV-1 / INV-3 / INV-4 / route 归一化 / CEL 静态判定属 M2–M4，当前 crate 尚未实现** | 这些规则由我**人工逐条核对**（见 §6），未机器验证 | 机器验证只覆盖 M1（信封 / 七段解析 / 词表 / 引用闭包 / INV-2） |

---

## 5. 与提案 B 样例 1（golden `sample1.yaml`）的有意分歧

| 维度 | golden 样例 1 | 本稿 | 理由 |
|---|---|---|---|
| 拓扑 | 单节点 `solver`，工具回灌在节点运行时内完成，`edges: []` | 显式循环体（10 节点 / 15 边）+ escape 节点 | 卡片⑥(a)-1/6/7 明确要求「工具节点回边」「终止动作出边」「循环节点 max_iterations」，且卡片⑥(b) 八项必须有实体逃逸节点承载 |
| 停止 | 仅 `policies.stop` | 追加 `judge.route → exit` 与 `loop.exit_when` | 「finish → 结束节点」在卡片⑥(a)-6 里是**出边**，只有 route 能表达 |
| 逃逸 | 零逃逸（提案 B §4.1 注「本配方零逃逸」） | 8 个逃逸节点 | 卡片⑥(b) 八项逐条要求记账；提案 B §7 也把 ⑥b 1/2/8 列为 ReAct 的残余 L4 |

---

## 6. 自检记录（实跑，2026-10-24）

### 6.1 YAML 解析（任务书指定的检查）

```
$ cd /home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿
$ python3 -c "import yaml,sys; yaml.safe_load(open('ReAct.yaml'))"
YAML OK
top keys: ['edges', 'meta', 'nodes', 'policies', 'stores', 'types', 'version']
nodes: ['react_loop']
body nodes: ['registry','reasoner','compose','parse','judge','action_valid','env','recovery','beliefs','assembler']
body edges: 15
escapes: [('registry','dynamic_tool_registry',5),('compose','program_synthesis',5),('parse','free_text_parser',8),
           ('judge','llm_predicate',8),('env','env_adapter',10),('recovery','meta_loop',5),
           ('beliefs','runtime_context_mutation',3),('assembler','runtime_context_mutation',4)]
stores: [('trajectory','react_loop.reasoner','run'),('beliefs','react_loop.beliefs','run')]
types: ['react_input','action_space','turn_text','turn_record','action_call','decision','completion','observation','belief_state','context_bundle','hint','answer']
budgets: turn_cap(turns,loop:react_loop,12) / token_cap(tokens_total,loop:react_loop,60000) / cost_cap(cents,plan,120)
stop: last_tool.first_line in ['FINISH','FINAL ANSWER']→completed / steps.tool_free >= 2→failed
failures: ['tool_error','gate_refused','transport_transient','budget_exhausted']
```

（首次写盘时 `beliefs` 逃逸节点的 `reason` 里含未转义的双引号，`yaml.safe_load` 会失败；已改为『』并重跑通过。）

### 6.2 真实编译器前端校验（af-dsl M1：信封 + 七段 serde AST + 词表 + 引用闭包 + INV-2）

链接仓库已构建的 `libaf_dsl.rlib`，跑一个只读小程序（写在 `/tmp`，**未改动仓库任何文件**）：

```
$ rustc --edition 2021 /tmp/afb_check_react.rs \
    --extern af_dsl=/home/pan-ding/workspace/af-wt-phase2-dsl/target/debug/libaf_dsl.rlib \
    -L dependency=/home/pan-ding/workspace/af-wt-phase2-dsl/target/debug/deps -o /dev/shm/afb_check_react

$ cd /home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/testdata
$ /dev/shm/afb_check_react sample1.yaml            # 控制组：golden
PARSE OK: name=react_mono version=1
violations: 0

$ /dev/shm/afb_check_react "/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿/ReAct.yaml"
PARSE OK: name=react_interleaved version=1
violations: 0
```

> 注：`/tmp` 配额已满（tmpfs 7.5G 用 6.0G），链接器在 `/tmp` 输出时报 Bus error，改用 `/dev/shm` 成功。**未运行**：`cargo test -p af-dsl` 全量套件（本次只做了只读链接 + 单文件校验）；M2–M4 的规则（INV-1/3/4、route 归一化、CEL 静态判定）在当前 crate 里不存在，无法机器验证（见 §4-U14）。

### 6.3 六节自检清单逐项

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | **信封** | ✅ | `version: 1` 顶格；顶层键集恰为七段 `{version, meta, types, stores, nodes, edges, policies}`；无未知顶层键；`meta` 五必填 + `intent` 齐备；`meta.output.from` 必填未做推断。M1 解析通过 |
| 2 | **类型表** | ✅ | 12 个类型全部登记在 `types`；全部端口/store 元素类型均为已登记名（无内联对象 schema、无未登记名）；`meta.input=react_input`、`meta.output.ref=answer`、`stores[beliefs].item=belief_state` 均在表内；`emits.from_body` 路径 `judge.answer` 可解析（E2106） |
| 3 | **单写者** | ✅ | `trajectory` ← `react_loop.reasoner`、`beliefs` ← `react_loop.beliefs`；节点 `writes[]` 与 `stores[].writer` 交叉核对一致，**M1 的 INV-2 检查器判定 0 违例**；无 map 体（无 E2312 风险）；体内写、体外声明的两个 store 均在 `carried` 登记（E2211） |
| 4 | **配额** | ✅ | `context.sections` 8 段 `quota_tokens` 全为正（900/200/4000/400/300/600/3000/200）；LLM 节点 `reasoner` 无 `reads`（E2303 不触发）；4 个入边端口 `action_space/observation/context_bundle/hint` 各被**恰好一个** section 引用（E2304）；section 来源（template/input/store/edge）均可解析（E2301/E2401/E2402） |
| 5 | **预算** | ✅ | `budgets` 三条：`turns/loop:react_loop/12`、`tokens_total/loop:react_loop/60000`、`cents/plan/120`，cap>0、scope 指向存在的 loop/plan（E2207）；`loop.max_iterations=12`；`carried` 覆盖体内写、体外声明的 store（E2211）；`safety_points: [{node: action_valid, kind: gate}]` 指向验证面节点（E2107/E2322）；`on_exhausted: fail`（④：步数到顶截断判失败） |
| 6 | **逃逸记账** | ✅ | 8 个 escape 节点，记账四字段（`impl_ref`/`reason`/`owner`/`share_budget_pct`）**无一缺失**（E2210）；`kind` ∈ 七类闭环词表且七类全覆盖（M1 serde E1004 词表校验通过）；占比 3–10%/节点，合计 48% |

### 6.4 人工逐条核对的 M2–M4 规则（M1 尚未实现，非机器验证）

- **INV-1**：LLM 节点上下文 = 且仅 = 声明的 sections（无隐式注入）✓；入边端口恰一引用 ✓；配额正数 ✓；无 `reads` ✓。
- **INV-2**：`trajectory`/`beliefs` 各一写者 ✓；`carried` 覆盖 ✓。
- **INV-3**：`action_valid`（gate）的入边生产者是 `judge`，非自产 ✓；`safety_points` 指向 gate ∈ {check, gate, human} ✓。
- **INV-4**：本稿无 `eval_input: true` 槽 ✓（不触发 E2331）。
- **route 归一化（E2101/2102/2103）**：`judge` 出边={action_valid}，rule→`exit`（不生成边，合法）、default→`action_valid` ✓ 全覆盖、无重复目标；`action_valid` 出边={env, recovery}，rule→`recovery`、default→`env` ✓。
- **CEL 保守子集**：本稿 5 条 CEL —— `judge.verdict.done == true`（×2）、`inputs.action.matched == true`、`action_valid.passed == false`、`last_tool.first_line in ['FINISH','FINAL ANSWER']`、`steps.tool_free >= 2` —— 只用 `_==_`/`_>=_`/`@in`，零函数调用，根绑定分别为节点 id（`judge`/`action_valid`）、`inputs`、`last_tool`、`steps`，均在位置词表内（节点 id 按作用域解析，`judge` 在循环体内、`exit_when`/route 规则的可见范围承提案 §1.4 与样例 3 `tally.result.…` 先例）。

---

## 7. 计数

- **可由标准拓扑/组件表达（卡⑥(a)）**：**8 / 8**
- **需逃逸舱（卡⑥(b)）**：**8 项**，落在七类词表上（`runtime_context_mutation` 2 项，其余各 1 项）
- 草稿体量：1 个根节点（受控循环）· 10 个体节点 · 15 条体边 · 2 个槽 · 12 个类型 · 3 条预算 · 2 条停止 · 4 条失败分类 · 8 个逃逸节点
