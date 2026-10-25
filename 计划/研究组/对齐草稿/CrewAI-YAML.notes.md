# CrewAI-YAML · AFB DSL 翻译记录

- 目标：**CrewAI 的 YAML 装配方式**（`agents.yaml` + `tasks.yaml` 声明角色/目标/背景故事与任务期望、分配；`Process=sequential|hierarchical`）
- 输入卡片：`计划/研究组/对齐机制卡/CrewAI-YAML.md`（六节齐全；INDEX 第 28 行登记「成 / 4604 字 / 正常」）
- 语法依据：`计划/研究组/DSL-语法提案-B.md`（AFB 正本骨架：七段 + 六正交构造）+ `计划/研究组/DSL-语法择优-裁决-20261024.md` §二-1（`meta.topology_selector` 编译期语义）、§二-2（`escape.kind` 七类闭环词表）
- 语法参照样例：ask 里写的 `.../crates/af-dsl/testdata/sample1-6.yaml` **不存在**；实为 `sample1.yaml`…`sample6.yaml` 六个单文件（M1 已解析通过的 golden 种子，见 `crates/af-dsl/tests/parse_test.rs:28-33`）
- 交付物：本文件 + 同目录 `CrewAI-YAML.yaml`
- 日期：2026-10-24

> 声明：本文件是**草稿记录**，不构成验收结论；最终通过与否由编译器裁定。
> 工作区零改动：af 仓只被**只读**引用；校验在 `~/.cache/afb-sandbox`（af-wt-phase2-dsl 的裁剪副本，含临时测试 `draft_check.rs`）与 `~/.cache/cel-crewai`（cel 沙盒的私有副本）里跑。

---

## 一、机制 → 语法映射表（逐条对应卡片⑥）

### ⑥(a) 可映射为「标准拓扑 + 组件」的 13 条

| 卡⑥(a) | 机制 | AFB 落点 | 说明 |
|---|---|---|---|
| 1 | **Crew → 工作流图根 / 单次运行上下文** | `meta`（`name`/`graph_version`/`entry`/`input`/`output`）+ 根图 | `meta.input = crew_brief`（= `kickoff(inputs)` 的输入字典），`meta.output = {ref: crew_output, from: crew_report}`（唯一发射者，不推断） |
| 2 | **Agent → 节点模板**（role/goal/backstory/tools 声明式） | 每个 Agent 一个 `kind: task` 节点；角色三元组走 `context.sections` 的 `template` 段 `vars:`（`role`/`goal`/`backstory` 字面量），工具走 `uses.tools` | 例：`researcher`（`vars: {role: "Senior Data Researcher", goal: …, backstory: …}` + `uses.tools: [pkg.crewkit.tool.web_search@1, …]`）、`analyst`、`writer`、`scout`、`manager` |
| 3 | **Task → 节点实例 + I/O 契约**（description=输入提示、expected_output=输出规格、output_pydantic=输出 schema） | 节点 `consumes`/`emits` + `types` 表：`task_output{summary, artifact_ref}`（= expected_output 的自然语言期望 + TaskOutput.file_path）、`crew_output`（= CrewOutput） | 「output_pydantic 是输出 schema」= `types` 表里该任务输出类型的 JSON Schema；`description` = 上下文里的任务提示（`input`/`edge`/`arg` 段投影） |
| 4 | **Process=sequential → 静态线性 DAG，边 = TaskOutput→context** | 根图边链 `intake→dispatch→parallel_scan→merge_findings→researcher→analyst→memory_append→compose→crew_report`；上下文边 `researcher→analyst`、`analyst→compose`（经 `compose.loop.args`） | 每个 TaskOutput 经 `envelope` 语义的**类型化工件边**流动；下游用 `from: edge` 段显式拉取 = 「context 拉取」的声明式化 |
| 5 | **Process=hierarchical → Manager 节点 + 委派边的半静态图** | `manager`（manager_llm 角色，产出 `delegation_plan`）→ `manager_delegate`（**逃逸**，运行时改次序）→ `researcher`；末端 `manager_accept`（验收，可见全部 worker 输出） | 分派由 `dispatch.route` 的 `input.process == 'hierarchical'` 规则触发；Manager 的「验收」面 = `manager_accept`（读 `crew_memory` 全量） |
| 6 | **ReAct 多轮循环 → 节点内迭代执行** | 节点运行时内部（不经图边，承 golden `sample1.yaml` 的 `solver` 先例）；上限用 `policies.budgets` 的 `turns`（`scope: node:researcher` cap 15 = Agent.max_iter、`node:manager` cap 15 = Manager.max_iter、`loop:compose` cap 45） | 「唯一硬性早停是 executor 的 max_iter/超时与 Agent 声明最终答案」→ 预算 + `steps.iterations` 停止条件 |
| 7 | **Context → 边上的数据流绑定** | `edges[].{from,output,to,input}` 四字段 + 消费侧 `from: edge` 段（含 `fields`/`policy`/`optional`） | `researcher` 的 `findings`/`plan`/`delegation` 三个入边端口各由**恰好一个** edge 段引用（INV-1） |
| 8 | **Memory → 状态存储 / 检索作用域声明** | 槽：`research_trace`(message_log, run)、`draft_trace`(message_log, iteration)、`crew_memory`(collection, **persistent**, rolling_window)；检索：`from: store, policy: retrieve, component: pkg.crewkit.mem.similarity@1, args:{k:5}`；组件绑定：`uses.memory: [pkg.crewkit.mem.longterm@1]` | 卡片③「短期记忆+ReAct 中间步 / 长期记忆落 SQLite+向量库 / 重跑即失忆（除 memory 外）」↔ 三条槽的 `lifecycle` 差异；`crew_memory` 持久化 → 跨 kickoff 可见 |
| 9 | **planning → 条件启用的前置规划节点** | `planner`（`uses.model: route.plan@1`，planning_llm）+ `dispatch.route` 的 `input.planning == true` 规则 | 条件启用 = route 分派（不启用时该边守卫为假，规划器不执行） |
| 10 | **guardrail → 节点前后置校验器** | 结构化那一半：`guardrail`（`kind: check`，`uses.unit: pkg.crewkit.guardrail.structural@1`，同时是循环的 `safety_points`）；LLM 质量那一半：`output_judge`（**逃逸**，llm_predicate） | 卡片②把 Guardrail 拆成「结构化输出校验」与「LLM 质量门禁」两件事，前者可静态化、后者不可（见 §二） |
| 11 | **callbacks → step/task 级事件钩子** | **无落点（语法缺口）** | AFB v0.1 没有事件/钩子字段；`context.sections` 只描述上下文装配，无「装配过程钩子」位。卡片未把它列入 ⑥(b)，故**未开逃逸舱**（七类词表也无对应类别），仅登记为 v0.2 待议（见 §四-3） |
| 12 | **tools → 能力绑定表** | `uses.tools: [pkg.crewkit.tool.web_search@1, pkg.crewkit.tool.fetch@1, pkg.crewkit.tool.doc_render@1]`、`uses.tool: pkg.crewkit.kickoff_inputs@1` | 领域名词全在 `pkg.*` 引用里（核心七段零领域名词） |
| 13 | **async_execution → 并发分支** | `parallel_scan`（`kind: task` + `map`，`over: input.parallel_topics`，体内 `scout` 角色节点），`emits: {items: {from_body: scout.finding}}` 自动包 `list<>`；汇合 = `merge_findings`（transform，确定性 merge，不落槽 → 无并发写） | 卡片标「汇合语义存疑」：本稿取「并发实例只产工件、汇合点串行合并」的保守口径（承 golden `sample3.yaml` 的 collector 单写者做法） |

**⑥(a) 判定为标准语法可表达 = 12 / 13**；第 11 条（callbacks）**无语法位**，记为语法缺口（未开逃逸舱，理由见 §二-4）。

### ⑥(b) 卡片列出的 9 条：逐条判定

| 卡⑥(b) | 机制 | 判定 | 落点 / 理由 |
|---|---|---|---|
| 1 | Manager 运行时动态委派与改写执行次序 | **逃逸（已布点）** | `manager_delegate`（`escape.kind: meta_loop`）：委派边由 LLM 运行期生成，静态 DSL 无法枚举该图（提案 B §1.5 的 route 只能覆盖**已声明**的出边） |
| 2 | ReAct 内循环的终止语义（何时算完成） | **逃逸（已布点，近似）** | `compose.loop_body.completion_decider`（`escape.kind: llm_predicate`）：DSL 只能给 `max_iter` 上限；本稿把「是否真的完成」提到图级，由逃逸节点判定 `done`，未完成则回写作节点继续（**近似**：真判据仍在节点运行时内） |
| 3 | expected_output 的自然语言判据与 LLM-as-judge 门禁 | **逃逸（已布点）** | `compose.loop_body.output_judge`（`escape.kind: llm_predicate`）：满意度无法编码为 DSL 断言，由 LLM 判据给出 `pass`，不通过则打回写作节点 |
| 4 | Memory 的相关性召回与重排 | **逃逸候选（未布点，缺节点宿主）** | 声明面已可表达（`policy: retrieve` + `component:` + `args.k`）；但「重排策略」是运行期检索器内部行为，`context` 装配只由 `sections` 决定，**AFB 没有可承载「上下文钩子」的节点**（同 Reflexion 稿的同类发现）。按裁决 §二-2 归 `runtime_context_mutation`，**不虚构语法位**，只登记候选 |
| 5 | human_input 的阻塞式人机回路 | **可表达，不逃逸（与卡片判定有出入）** | 提案 B §2 明确把「CrewAI `human_input`」列为 `human` 构造的证据锚点（`human{station,role,quorum,resume.schema}` + `route`），且七类逃逸词表里**没有** human/中断这一类。本稿据此用 `human` 构造表达（`compose.loop_body.review`，`resume.schema` = `{approved, comments}`，打回 `route` 回写作节点）。若编译器要求逐条按卡片开舱，需先给词表增类（见 §四-1） |
| 6 | Flow 的 @router 动态分支与 persist_state | **逃逸候选（未布点；persist_state 一半已可表达）** | `persist_state` ≈ `stores` 的 **persistent** 槽（本稿 `crew_memory` 即此形态，可表达）；`@router` 动态分支 = 运行期改图（`meta_loop`），但 Flow 与 YAML crew 是**并存的两套编排模型**（卡片②列 Flow 为「相邻能力」），本图不含 Flow 分支，故无节点宿主 → 登记候选（`meta_loop` + `env_adapter`） |
| 7 | 限流与成本治理（max_rpm、成本早停） | **一半逃逸（已布点）+ 一半标准语法** | 节流：`rate_limit_guard`（`escape.kind: env_adapter`，runtime 资源策略）；成本/时长上限：`policies.budgets`（`cents`/`clock_ms`/`turns`/`tool_calls`）+ `policies.stop`（成本早停、时钟强停）——**注意：CrewAI 原生没有成本早停，这是 AFB 的补强，与原框架有有意差异**（见 §四-6） |
| 8 | YAML extra 字段透传与插件/MCP 工具运行时注册 | **逃逸（已布点）** | `tool_registry`（`escape.kind: dynamic_tool_registry`）：工具集合不可静态封闭枚举，装配期按声明注册运行期工具面（承 AutoGen 稿 `client_registry` 同型） |
| 9 | LiteLLM 层重试/退避/多供应商 fallback | **逃逸（已布点）** | `llm_transport`（`escape.kind: env_adapter`）：位于 DSL 之下的传输层容错；LLM 资源分派（crew 默认 + agent 覆盖 + manager_llm/planning_llm）同在此节点装配 |

**⑥(b) 判定为需要逃逸舱的机制 = 8**（第 1、2、3、4、6、7、8、9 条）；其中 **6 条已落 `escape` 构造**（1、2、3、7、8、9），**2 条为逃逸候选未布点**（4、6，缺节点宿主）；第 5 条（human_input）判定为标准语法可表达，**未开逃逸舱**。

---

## 二、逃逸清单（escape 构造 + 七类词表记账）

七类词表（裁决 §二-2，承提案 A 的 `escape_hatches.kind`）：`dynamic_tool_registry` / `program_synthesis` / `meta_loop` / `runtime_context_mutation` / `env_adapter` / `free_text_parser` / `llm_predicate`。

| 节点（YAML 路径） | escape.kind | impl_ref | owner | share_budget_pct | 对应卡片 | 理由（YAML `reason` 摘要） |
|---|---|---|---|---|---|---|
| `llm_transport` | `env_adapter` | `packages/crewkit@1.0.0/hatches/llm_transport.py` | lang-team | 5 | ⑥b-9（+ 卡片② LLM 资源） | 传输层重试/退避/多供应商 fallback 在 DSL 之下；LLM 资源分派同处该层 |
| `rate_limit_guard` | `env_adapter` | `packages/crewkit@1.0.0/hatches/rate_limit_guard.py` | lang-team | 5 | ⑥b-7 | max_rpm 节流是运行期资源策略，budgets 只能给上限 |
| `tool_registry` | `dynamic_tool_registry` | `packages/crewkit@1.0.0/hatches/tool_registry.py` | lang-team | 5 | ⑥b-8 | extra 字段透传 + 插件/MCP 运行时注册 → 工具集不可静态封闭 |
| `manager_delegate` | `meta_loop` | `packages/crewkit@1.0.0/hatches/manager_delegate.py` | lang-team | 5 | ⑥b-1 | 委派边与执行次序由 LLM 运行期生成 |
| `compose.loop_body.completion_decider` | `llm_predicate` | `packages/crewkit@1.0.0/hatches/completion_decider.py` | lang-team | 5 | ⑥b-2 | 「是否完成」由 LLM 决定，DSL 只能给 max_iter |
| `compose.loop_body.output_judge` | `llm_predicate` | `packages/crewkit@1.0.0/hatches/output_judge.py` | lang-team | 5 | ⑥b-3 | expected_output 自然语言判据 / LLM-as-judge |

- **逃逸舱数（YAML 中 `escape` 构造数）= 6**；逃逸预算声明值合计 **30%**（每条 5%）。
  - ⚠️ 占比口径未定：提案 B §1.3 / ADR-001 §3 只说「>30% 警戒」，未说清是**单条**还是**合计**口径（与 AutoGen 稿的 U10 同一问题）。本稿合计正好 30%（不越线），单条最大 5%。
- 四字段闭合：`impl_ref` / `reason` / `owner` / `share_budget_pct` 全部齐备（E2210 的 serde 前置），并按裁决 §二-2 补 `kind`，取值全在闭环词表内（未知变体由 serde 拒 → E1004）。
- **未使用的四类及理由**：`program_synthesis`（无程序/图合成：Manager 的动态委派按「运行期改图」归 `meta_loop`）、`runtime_context_mutation`（唯一适配项是 ⑥b-4 的记忆重排，但**无节点宿主**，故未布点）、`free_text_parser`（CrewAI 的任务输出走结构化输出校验，不是自由文本双向解析）、`dynamic_tool_registry` 已用。
- **逃逸候选（未布点）**：⑥b-4 记忆召回重排 → `runtime_context_mutation`；⑥b-6 Flow `@router` → `meta_loop`、Flow `persist_state` 的外部状态部分 → `env_adapter`。

---

## 三、拓扑（一张图）

```
装配期：llm_transport(L4 env_adapter) → rate_limit_guard(L4 env_adapter) → tool_registry(L4 dynamic_tool_registry) → intake(tool)

dispatch(gate, assert: topic 非空)
  ├─ rule: input.process=='hierarchical' → manager ─delegation→ manager_delegate(L4 meta_loop) ─delegation→ researcher
  ├─ rule: input.planning==true         → planner ─brief→ parallel_scan ; ─plan→ researcher
  └─ default                            → parallel_scan(map over input.parallel_topics; body: scout) ─items→ merge_findings ─findings→ researcher

researcher(角色模板 vars + tools + research_trace + crew_memory 检索)
   └─research→ analyst ─analysis→ memory_append(Crew 级记忆唯一写者)
                          └─(compose.loop.args: research / analysis)→ compose

compose(loop, max_iterations=3, carried: draft_trace, safety_point: guardrail(check),
        exit_when: attempt.passed==true && review.decision.approved==true, on_exhausted: fail)
  body: writer ─draft→ guardrail(check) ─verdict→ completion_decider(L4 llm_predicate) ─completion→ output_judge(L4 llm_predicate) ─judge→ review(human, resume.schema)
        writer ←completion / ←judge / ←decision（三条打回边）；review 拒绝 → writer；guardrail 不过 → 下一轮
  route: default → crew_report ; rule: input.process=='hierarchical' → manager_accept ─draft→ crew_report

crew_report(transform) → meta.output(crew_output)
```

三条路径：
- **sequential**：dispatch(default) → parallel_scan → merge_findings → researcher → analyst → compose → crew_report。
- **sequential + planning**：dispatch(rule2) → planner →（brief 透传）parallel_scan → … → researcher（额外消费 `plan`）。
- **hierarchical**：dispatch(rule1) → manager → manager_delegate → researcher（`findings` 端口缺省、`delegation` 端口在场）→ analyst → compose →（compose.route rule）manager_accept → crew_report。

---

## 四、语法不确定点（诚实列出，不编造语法）

1. **卡片⑥(b)5（human_input）与提案 B 的冲突**：卡片把 human_input 判为逃逸；提案 B §2 却把「CrewAI `human_input`」列为 `human` 构造的正例，且七类逃逸词表无 human/中断类别。本稿按提案 B 用 `human` 构造表达、**不开逃逸舱**。若编译器以卡片为准，需给 `escape.kind` 增类（词表是裁决 §二-2 定的闭环词表，属 v0.2 议题）。
2. **`meta.topology_selector` 未布点（与 AutoGen 稿的有意分歧）**：裁决 §二-1 说选择器是**编译期**语义、候选图须是已声明的版本化图/子图；而 CrewAI 的 `Process` 是**装配期/运行期**配置（同一份 `agents.yaml`/`tasks.yaml` 在 `process=sequential` 与 `process=hierarchical` 下都合法），且 AFB v0.1 无内联多图语法（无 `graphs:` 段）。本稿改用**运行期 `route`** 承载 Process 分派（`dispatch.route` / `compose.route`）。若评审要求编译期选择，可包化为 `pkg.crewkit.crew.sequential@1.0` / `pkg.crewkit.crew.hierarchical@1.0` 两张候选图并加 `topology_selector`（届时本图的运行期 route 应删除，二者互斥）。
3. **callbacks 无语法位（⑥a-11）**：AFB v0.1 无事件钩子字段，`context.sections` 只描述上下文装配。这是本稿发现的**语法缺口**（提案 B §2 的构造清单里也没有回调位）；建议 v0.2 评审考虑 `hooks[]` 或明确「回调不在 DSL 覆盖范围」。
4. **逃逸节点带 `consumes`/`emits`/`route` 是否允许**：提案 B 未明确 L4 节点可否声明工件端口与路由。本稿的 `manager_delegate`、`completion_decider`、`output_judge` 都带 `consumes`/`emits`，前两者还带 `route`（与同目录 AutoGen 稿 `selector_override` 同型）。若编译器要求逃逸节点只能有四个记账字段，这些节点需改为「经工件传递 + 由静态节点承载路由」。
5. **`gate` 节点带 `emits` 转发工件**：本稿的 `dispatch`（kind=gate）既 `consumes{brief}` 又 `emits{brief}`，把装配输入透传给下游分支。提案未定义 gate 的工件转发语义（gate 内建 `passed` 布尔端口）。
6. **`loop` 构造节点带 `route`**：本稿的 `compose`（loop）带 `route`（hierarchical 时改道到 `manager_accept`）。提案 §6 的 E1006「控制节点污染」禁列是 uses/context/writes/reads/escape/ops，**不含 route**，故按字面合法；但「环结束后的路由」语义提案未写。
7. **逃逸占比口径**（合计 vs 单条，见 §二）与「编译期是否拒绝 >50% 配方」（提案 B §8-7 未决）——同 AutoGen 稿的 U10。
8. **`vars` 的取值域**：提案 §1.2 写 `vars?: {名: 字面量或 arg.*/input.* 引用}`，但 `vars` 值是字符串；`arg.*`/`input.*` 是「字面量字符串」还是「引用表达式」未定义。本稿的 role/goal/backstory 全用**字面量**，不依赖该语义。
9. **`attempt` 绑定的取值**：`compose` 体内只有 `guardrail` 一个验证面节点（check），故 `attempt.passed ≡ guardrail.passed`，无歧义；若日后加入第二个 check，「最近一次」的确定性规则提案未给。
10. **空 `map` 的语义**：`input.parallel_topics` 非必填，未提供时 `parallel_scan` 的扇出基数为 0，提案未定义零实例 map 的行为（是否直接放行 `merge_findings`）。
11. **卡片自标存疑处的建模选择**：卡片④-5（guardrail 不通过是否可继续重试，版本相关）与④-9（Planner 失败是否降级不阻断）均标「存疑」。本稿取：guardrail 不通过 = `gate_refused` 终态失败（终止该 Task，符合卡片④-6「单 Task 抛错终止整次 kickoff」）；Planner 失败 = `environment_failure` 改道 `parallel_scan`（降级为无计划执行）。两者都是**假设**，请评审按目标版本复核。
12. **有意与原框架的差异（语义补强，非翻译）**：`policies.budgets` + `policies.stop` 引入了 CrewAI 原生**没有**的成本早停（卡片⑤「无内建成本早停」）。这是 AFB 的表达力补强，不是 CrewAI 语义，入库前需确认是否允许。
13. **`compose.loop.args` 穿过循环体取上游工件**：`args: {research: researcher.research, analysis: analyst.analysis}` 依赖提案 §1.3「体形参绑定 + 隐式依赖边」；M1 已验引用可解析（E2105 未触发），但**运行期的依赖边语义未由编译器裁决**。
14. **`manager_accept` 与 `crew_report` 同名端口 `draft`**：两端 `emits.draft`/`consumes.draft` 同名同型，两条入边（compose、manager_accept）喂同一端口。M1 的端口类型核对通过；运行期「哪条边生效」由 route 归一化后的守卫决定（hierarchical 时 compose→crew_report 的守卫为假）。若编译器认为同端口多入边需改名，此处需改。

---

## 五、自检记录（本 ask 内实跑，含命令与输出）

### 5.1 必做检查：YAML 解析（任务书指定的那条命令）

```
$ cd /home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿
$ python3 -c "import yaml,sys; d=yaml.safe_load(open('CrewAI-YAML.yaml')); print('YAML_OK top-keys=', sorted(d.keys())); print('nodes=',len(d['nodes']),'edges=',len(d['edges']),'types=',len(d['types']),'stores=',len(d['stores']))"
YAML_OK top-keys= ['edges', 'meta', 'nodes', 'policies', 'stores', 'types', 'version']
nodes= 16 edges= 19 types= 8 stores= 3
```
→ **通过**：顶层键集恰为七段（`version` + 六段），与 golden 样例一致。

### 5.2 加做检查：真实 af-dsl 编译器前端（M1 全量：信封 + 七段形状 + 引用闭包 + INV-2）

沙盒：`~/.cache/afb-sandbox`（af-wt-phase2-dsl 的裁剪副本，仅含 `crates/af-dsl` + 临时测试 `tests/draft_check.rs`，调用 `load_str` + `validate`；**af 仓本身未改动**）。

```
$ cd /home/pan-ding/.cache/afb-sandbox
$ AFB_DRAFT="/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿/CrewAI-YAML.yaml" \
  CARGO_TARGET_DIR=/home/pan-ding/.cache/afb-target cargo test --offline -p af-dsl --test draft_check -- --nocapture
running 1 test
VIOLATIONS: 0
test draft_check ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s
```
→ **通过（0 违例）**。覆盖：拒绝式信封 E0001–E0004、七段 serde 形状（全文 `deny_unknown_fields`）、引用闭包 E2001/E2201/E2202/E2204/E2205/E2104/E2105/E2106/E2107/E2207/E2208、INV-2 写入串行化 E2311/E2312/E2211、词表 E1004。

### 5.3 加做检查：CEL 保守子集实跑（11 条表达式）

沙盒：`~/.cache/cel-crewai`（`~/.cache/cel-sandbox` 的私有副本；VOCAB 增加本稿的 `completion_decider`/`output_judge`/`review` 三个绑定根，合成上下文补 `input.process/planning/topic`、`inputs.brief.topic`、`attempt.passed=true`、`resume.approved`）。
表达式清单：`~/.cache/crewai_cel.tsv`（2 条 route 规则 + 1 条 gate assert + 1 条 compose.route + 1 条 exit_when + 3 条体内 route + 3 条 policies.stop）。

```
$ cd /home/pan-ding/.cache/cel-crewai
$ CARGO_TARGET_DIR=/home/pan-ding/.cache/cel-target cargo run --offline --quiet -- /home/pan-ding/.cache/crewai_cel.tsv
PASS dispatch.route[0]	input.process == 'hierarchical'
PASS dispatch.route[1]	input.planning == true
PASS dispatch.assert	inputs.brief.topic != ''
PASS compose.route[0]	input.process == 'hierarchical'
PASS compose.exit_when	attempt.passed == true && review.decision.approved == true
PASS compose.body.completion_decider.route[0]	completion_decider.completion.done == false
PASS compose.body.output_judge.route[0]	output_judge.judge.pass == false
PASS compose.body.review.route[0]	resume.approved == false
PASS policies.stop[0]	budget.cents_spent >= budget.cents_cap
PASS policies.stop[1]	budget.clock_ms_spent >= budget.clock_ms_cap
PASS policies.stop[2]	steps.iterations >= 3
----
total=11 fail=0
```
→ **通过（11/11）**：每条过 ① `Program::compile`（E1051 判据）② 算子函数全在保守子集白名单（E1052 判据）③ 根绑定在位置词表内（E2203 判据）④ 合成上下文上求值为布尔（E1053 判据）。

### 5.4 加做检查：六节自检清单（补 M1 未覆盖的 M2/M4 前置条件）

脚本：`~/.cache/autogen_struct_check.py`（AutoGen 稿留下的通用版，本稿只读复用，**未修改**；口径：信封 / 类型表 / 单写者 / 配额+入边端口覆盖 / 预算 / 逃逸记账 / route 覆盖与互斥 / carried 覆盖 / 安全点为验证面）。

```
$ python3 /home/pan-ding/.cache/autogen_struct_check.py ".../对齐草稿/CrewAI-YAML.yaml"
节点 22 个 / 边 354 条 / 逃逸 6 处（share_budget_pct 合计 30%）
  escape llm_transport: kind=env_adapter pct=5
  escape rate_limit_guard: kind=env_adapter pct=5
  escape tool_registry: kind=dynamic_tool_registry pct=5
  escape manager_delegate: kind=meta_loop pct=5
  escape compose.completion_decider: kind=llm_predicate pct=5
  escape compose.output_judge: kind=llm_predicate pct=5
PASS: 六节自检 0 违例
```
→ **通过（0 违例）**。脚本打印的「边 354 条」是它的求和重复计数口径，**实际边数 = 根边 19 + 体内边 10 = 29**；节点 22 = 根 16 + compose 体 5 + parallel_scan 体 1。

逐项对照（任务书要求的六节清单）：

| # | 清单项 | 检查方式 | 结论 |
|---|---|---|---|
| 1 | **信封** | `version: 1` 首键；顶层键集恰为七段（5.1）；af-dsl `envelope::check` 通过（5.2 PARSE_OK） | ✅ |
| 2 | **类型表** | `types` 登记 8 个类型（crew_brief / task_output / plan_brief / delegation_plan / judge_verdict / completion_state / review_feedback / crew_output）；全部 `emits`/`consumes`/`store.item`/`meta.input`/`meta.output.ref` 引用已登记 → E2205 未触发（5.2）；对象 schema 只住 `types` 表，端口无内联对象 schema | ✅ |
| 3 | **单写者（INV-2）** | `research_trace`←`researcher`；`draft_trace`←`compose.writer`；`crew_memory`←`memory_append`；无 map 体并发写（`scout` 不写槽）；`compose.carried` 覆盖体内写的体外槽 `draft_trace` → E2311/E2312/E2211 未触发（5.2 + 5.4） | ✅ |
| 4 | **配额** | 每个 `context.sections[]` 都带正数 `quota_tokens`（writer 8 段 600/900/700/200/300/300/4000/600；researcher 7 段 600/300/1200/400/200/4000/600 等）；每条槽 `retention` 至少一个上界（128/128/rolling_window 256+keep_system） → E2208 未触发（5.2） | ✅ |
| 5 | **预算** | `policies.budgets` 8 条，`scope` = plan×4 / `node:researcher` / `node:parallel_scan.scout` / `node:manager` / `loop:compose`，目标均存在且 `loop:compose` 确有 loop 构造；cap 全 >0 → E2207 未触发（5.2）；`policies.stop` 3 条 CEL 已过沙盒（5.3） | ✅ |
| 6 | **逃逸记账** | 6 个 `escape` 构造：四字段（impl_ref/reason/owner/share_budget_pct）齐备 + `kind` 全在七类闭环词表内；逃逸节点不带 `uses`（5.4 脚本查）；声明占比合计 30%、单条 5%（口径问题见 §四-7） | ✅ |

### 5.5 未跑 / 无法做的事（如实）

- **未跑**编译器红绿测试（M1 每条规则的拒绝用例、IR 降维快照、计划对象快照）——按 ADR-007 属 af-dsl/af-compiler 落地时补齐。
- **未跑** M2 / M3 / M4 的正式实现（INV-1 上下文完整性、INV-3 生成器-验证器分离、INV-4 评估器外部化、`route` 归一化算法、CEL 静态判定、`topology_selector` 编译期解析）：**这些模块尚未存在于 af 仓**（`crates/af-dsl/src/validate/` 只有 `inv2.rs`/`refs.rs`/`mod.rs`）。本稿对这些规则只做了**等价的独立自查**（5.4 脚本 + 5.3 沙盒），**不等于编译器裁决**。
- **未生成**编译产物（IR / 计划对象）。
- **未做**：把本稿登记进 af-dsl 的 golden testdata（属他人仓的测试资产，不在本任务的两个交付文件范围内）。
- **未改**任何既有文件：af 仓只读；两个沙盒（`~/.cache/afb-sandbox`、`~/.cache/cel-crewai`）与临时文件（`~/.cache/crewai_cel.tsv`）都在 `~/.cache` 下，与工作区仓库无关。

---

## 六、评审需要拍板的三件事

1. **卡片⑥(b)5（human_input）到底算 `human` 构造还是逃逸舱**（§四-1）：影响逃逸计数（8 ↔ 9）与七类词表是否需要扩类。
2. **`meta.topology_selector` 的定位**（§四-2）：Process 这类「同一份声明、不同装配形态」的枚举，该用编译期选择器（需包化候选图）还是运行期 `route`？本稿选了运行期 route，与 AutoGen 稿的选择相反——两稿口径不统一的话，G3 对照语料会有歧义。
3. **逃逸占比口径**（§四-7）与「卡片标存疑处」的建模取值（§四-11、§四-12）：本稿对 ④-5/④-9 作了假设、对 CrewAI 补了原生没有的成本早停——都需要目标版本复核。
