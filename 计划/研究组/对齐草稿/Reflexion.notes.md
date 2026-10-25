# Reflexion → AFB DSL 翻译记录

- 目标：**Reflexion**（语言化自我反思 + 情景记忆 Buffer，Shinn et al. 2023）
- 输入卡片：`计划/研究组/对齐机制卡/Reflexion.md`（六节齐全，INDEX 第 2 行登记「成 / 5529 字」）
- 语法依据：`计划/研究组/DSL-语法提案-B.md`（AFB 正本骨架）+ `计划/研究组/DSL-语法择优-裁决-20261024.md` §二（`meta.topology_selector` 编译期语义、`escape.kind` 七类闭环词表）
- 语法参照样例：`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/testdata/sample1.yaml`（M1 已解析通过的 golden 种子；本目录下实为 `sample1.yaml`…`sample6.yaml` 六个单文件，ask 里写的 `sample1-6.yaml` 合并文件不存在）
- 交付物：本文件 + 同目录 `Reflexion.yaml`
- 日期：2026-10-24

> 声明：本文件是**草稿记录**，不构成验收结论；最终通过与否由编译器裁定。未改动任何现有文件；两处临时校验沙盒建在 `/tmp`（`/tmp/afb-reflexion-check` = af-dsl 加载器 + 校验器调用壳；`/tmp/afb-reflexion-cel` = cel-interpreter 保守子集沙盒的私有副本）。

---

## 一、机制 → 语法映射表（逐条对应卡片⑥）

### ⑥(a) 可映射为「标准拓扑 + 组件」的机制（9 条，全部落标准语法，零逃逸）

| 卡⑥(a) | 机制 | AFB 落点 | 说明 |
|---|---|---|---|
| 1 | 主执行环 = Actor 单节点循环（ReAct 拓扑） | `nodes[attempts].loop.body.nodes[actor]`（kind=task，`uses.model` + `uses.tools`） | ReAct 的 Thought→Action→Observation 内层自环落在 **Actor 节点运行时内部**（承 golden `sample1.yaml` 的 `solver` 先例：工具回灌在节点运行时内串行落账，不经图边）；外层受控循环承担「多尝试」 |
| 2 | 工具调用边 = Environment/Tools 组件 | `actor.uses.tools: [pkg.reflexkit.env_exec@1, pkg.reflexkit.search@1]` | Action=工具调用、Observation=返回值回灌同一节点，属标准 tool-call 形态 |
| 3 | Evaluator = 显式评估节点 + 条件边 | `verdict`（kind=check，`uses.unit: pkg.reflexkit.evaluator@1`，`reads: [trajectory]`，`consumes: {answer}`）+ `verdict.route.rules[0]` | 验证面内建 `passed` 端口承载二元/启发式判定；条件边用 `route`（提案 B §1.3，**边无 when**） |
| 4 | Reflector = 显式反思节点（LLM 角色 + 独立 prompt） | `reflect`（kind=task，`uses.model: route.reflect@1`，`template_ref: pkg.reflexkit.reflector_system`，`consumes: {decision}`） | 与 Actor 是**两次独立调用**、不同模型路由与不同模板（卡片③第 6 点） |
| 5 | Episodic Memory Buffer = 记忆组件（store + retrieve） | 写点：`memorize`（kind=transform，`writes: [episodic_buffer]`，`ops: project → into: episodic_buffer`）；槽：`episodic_buffer`（collection / persistent / rolling_window）；读点：`actor.context.sections[0]`（`from: store, policy: retrieve, component: pkg.reflexkit.similarity@1, args: {k: 2}`） | top-k 与相似度度量是组件参数（卡片⑥a-5 原文） |
| 6 | Prompt Assembler / 上下文注入 = 可静态声明的注入边 | `actor.context.sections`（顺序：反思检索 → 任务描述(`arg task`) → 模板(工具说明/输出格式) → 当前轨迹） | 卡片③第 2 点的典型拼装序；段顺序即拼接顺序（提案 B §1.2） |
| 7 | 整条轨迹可见性 = 状态作用域声明 | `trajectory`（`lifecycle: iteration`，单次尝试重建、结束即弃）；`episodic_buffer`（`lifecycle: persistent`，跨尝试跨回合） | 两条槽的生命周期差异即卡片⑥a-7 的「作用域声明」 |
| 8 | 角色划分 = 多角色节点 | 三个角色三套绑定：`actor`(route.main@1) / `verdict`(pkg.reflexkit.evaluator@1) / `reflect`(route.reflect@1) | 语义分工在 `uses` 不在 `kind`（提案 B §1.2 判别表） |
| 9 | 重试 = 外层重启边（重置轨迹 + 注入新反思） | `attempts` 受控循环：`max_iterations: 4` + `carried: [trajectory, episodic_buffer]` + `exit_when: "attempt.passed == true"` + `on_exhausted: fail`；「重置轨迹」由 `trajectory` 的 iteration 生命周期承担，「注入新反思」由下一轮 `actor` 的 retrieve 段承担 | 论文级「actor 尝试 ≤3~4 次」即 `max_iterations`（卡片⑤） |

### ⑥(b) 预计需要逃逸舱的机制（7 条，逐条判定）

| 卡⑥(b) | 机制 | 判定 | 落点 / 理由 |
|---|---|---|---|
| 1 | 运行时动态决定「是否写记忆 / 写什么」 | **逃逸（已布点）** | `memorize_guard`（kind=task，`escape.kind: runtime_context_mutation`）：运行时判定「反思为空/格式不可解析则跳过」等条件，以 `reflection_entry.writable` 标志回写工件，再由 `route` 决定是否进入静态写入点 `memorize` |
| 2 | 相似度检索 + top-k 选择 | **可表达，不逃逸** | AFB 已有向量检索位：`context.sections` 的 `from: store` + `policy: retrieve` + `component:` + `args: {k: N}`（承 golden `sample6.yaml` 的 `generator` 段）。卡片原文的条件句「若 DSL 不支持向量检索/排序」在 AFB 不成立 |
| 3 | 反思文本的运行时内容影响下一步 prompt 长度与顺序 | **逃逸候选（未布点）** | 部分可表达（retrieve 段的 `quota_tokens` + 组件内截断），但「运行时任意改写 prompt 装配顺序/预算分配」在 AFB **没有节点宿主**：`context` 装配只由 `sections` 声明式决定，没有任何节点能承载「上下文钩子」。按裁决 §二-2 归类为 `runtime_context_mutation`，但本配方**不虚构语法位**，只作逃逸候选登记（详见 §四-3） |
| 4 | 多尝试间的「隐式策略共享」 | **可表达，不逃逸** | 机制上落在 memory 组件：`episodic_buffer`（persistent）+ 外层受控循环 + `actor` 的 retrieve 注入，AFB 有静态声明位 |
| 5 | Buffer 的无界累积与检索成本 | **近似表达（有界化），不逃逸** | AFB 强制 `retention` 至少一个上界（E2208），故论文的「无显式上限、线性增长」被改写为 `rolling_window + max_items: 64 + keep_system: true`。**与论文存在有意的语义差异**（见 §四-6） |
| 6 | Evaluator 的异质性（二元 / 启发式 / LLM-as-judge） | **逃逸（已布点）** | `judge_inject`（kind=task，`escape.kind: llm_predicate`）：`uses.unit` 只覆盖固定类型判定；卡片④要求的「任务层失败 vs 执行错误」区分与运行时打分函数注入由 L4 承载，产出 `reflect_decision` 工件 |
| 7 | 「成功后也反思」等变体（**卡片自标存疑**） | **逃逸能力已备（主路径未启用）** | 论文不同设置不一致，卡片已标存疑。主路径按论文主设置「成功不产生反思」：`verdict.route.default: exit`。启用只需把该 default 改为 `judge_inject`（一行图编辑），L4 判据节点已在图中 |

**⑥(a) 判定为标准语法可表达的机制数 = 9 / 9。**
**⑥(b) 判定为需要逃逸舱的机制数 = 4**（1、3、6、7）；其中 **3 条已落 escape 构造**（1、6 布点；7 布点但主路径未启用），**1 条为逃逸候选未布点**（3，缺节点宿主）；其余 3 条（2、4、5）判定为可表达或近似表达。

---

## 二、逃逸清单（escape 构造 + 七类词表记账）

七类词表（裁决 §二-2，承提案 A）：`dynamic_tool_registry` / `program_synthesis` / `meta_loop` / `runtime_context_mutation` / `env_adapter` / `free_text_parser` / `llm_predicate`。

| 节点 | escape.kind（词表内） | impl_ref | owner | share_budget_pct | 对应卡片 | 理由（落 YAML 的 `reason` 字段） |
|---|---|---|---|---|---|---|
| `attempts.loop_body.judge_inject` | `llm_predicate` | `packages/reflexkit@1.0.0/hatches/judge_inject.py` | lang-team | 15 | ⑥b-6（+ 卡片④ 的失败分层） | 判定单元只支持固定类型判定；「任务层失败 vs 执行错误」的区分与 LLM-as-judge 打分需运行时注入打分函数 |
| `attempts.loop_body.memorize_guard` | `runtime_context_mutation` | `packages/reflexkit@1.0.0/hatches/memorize_guard.py` | lang-team | 10 | ⑥b-1（+ ⑥b-7 的运行时条件） | 「反思为空/格式不可解析则跳过写入」「成功后也反思」等由运行时条件决定，静态路由只能近似 |

- 逃逸舱数（YAML 中的 escape 构造数）：**2**
- 逃逸预算占比：**15% + 10% = 25%**，低于提案 B §1.3 / ADR-001 §3 的 **>30% 警戒线**（健康度指标，不触发编译期拒绝）
- 四字段闭合：`impl_ref` / `reason` / `owner` / `share_budget_pct` 全部齐备（E2210 的 serde 前置），并按裁决补 `kind`
- **未使用的六类**及理由：`dynamic_tool_registry`（工具集固定）、`program_synthesis`（无程序合成）、`meta_loop`（外层循环是静态拓扑，非元智能体改图）、`env_adapter`（环境经 `tools` 声明式接入）、`free_text_parser`（反思文本由 LLM 按 schema 结构化产出，非自由文本解析）、`llm_predicate`/`runtime_context_mutation` 已用

---

## 三、拓扑与关键取舍（一图）

```
attempts (loop, max_iterations=4, exit_when=attempt.passed==true, on_exhausted=fail)
 ├─ args: task ← input.task          carried: trajectory, episodic_buffer
 └─ body:
      actor ──answer──▶ verdict ──verdict──▶ judge_inject ──decision──▶ reflect
      (LLM+tools;                   (check/单元测试;   (L4 llm_predicate;      (LLM 反思节点)
       ctx: 反思检索→任务→模板→轨迹)  route: failed→judge) route: warranted→reflect)
                                                                        │
                                                    reflect ─entry──▶ memorize_guard
                                                    (L4 runtime_context_mutation;
                                                     route: writable→memorize)
                                                                     │
                                                        memorize_guard ─entry──▶ memorize
                                                        (transform: project → episodic_buffer，单写者)
```

- 成功路径：`verdict.route.default: exit` → 本次尝试收束 → `exit_when: attempt.passed == true` → 整条尝试链收束 → `attempts` 以 `from_body: actor.answer` 发射终态工件
- 失败路径：`verdict → judge_inject →(warranted) reflect → memorize_guard →(writable) memorize` → 下一轮迭代（`trajectory` 因 `lifecycle: iteration` 重置，`episodic_buffer` 因 persistent + carried 保留，新的 top-k 反思被检索进下一轮 `actor` 上下文）

---

## 四、语法不确定点（诚实列出，不编造语法）

1. **`goto: exit` 的语义边界（最高风险）**：提案 B §1.3 只写「`goto: <节点 id 或 exit>`」，未定义 `exit` 是「结束本轮迭代」还是「结束整个循环」。本稿按 golden `sample2.yaml`（`qa` 的 default: exit + `exit_when: attempt.passed == true`）与 `sample6.yaml`（`admit` 的 `goto: exit` 注释「结束本轮」）的用法取**「结束本轮迭代」，整条循环的收束交给 `exit_when`**。若编译器取另一读法，`verdict` / `judge_inject` / `memorize_guard` 三处 default 的行为会变（成功路径与「跳过写入」路径可能提前终止整条尝试链）→ **需编译器裁定**。
2. **逃逸候选 ⑥b-3 无节点宿主（发现的语法缺口）**：「运行时改写 prompt 装配顺序与 token 预算分配」在 AFB 无处安放——`context` 装配只由 `sections` 声明式决定，`escape` 只能挂在节点上，而没有任何节点的语义是「组装下一个节点的上下文」。**未虚构语法**，只登记为逃逸候选（kind=`runtime_context_mutation`）。若编译器认为需要，应在 v0.2 评审补一个「上下文钩子」位（本条属提案 B §四-1 的 G3 翻译痛点证据）。
3. **「工件字段驱动 route」的合法性**：`memorize_guard.route` 用 `memorize_guard.entry.writable == true` 判定，即**用数据字段承载控制流**。字面合法（提案 B §1.4 的 `<节点 id>` 根绑定支持「emits 端口 + 对象端口可继续点字段」，且 `sample2`/`sample3` 已用 `qa.passed`/`vote.stats.top_count` 同形），但把运行时判定编码进工件字段是**语义妥协**，请编译器确认是否接受这种用法（替代方案是给 escape 增加布尔回执端口，但提案 B 未定义该位）。
4. **`attempt` 绑定的「最近一次验证输出」**：提案 B §1.4 规定 `attempt.passed` 取体内验证面节点的最近一次输出。本稿体内只有 `verdict` 一个 check，故 `attempt.passed ≡ verdict.passed`，无歧义；但**多 check 体**下「最近一次」的确定性规则提案未给（本次未触发）。
5. **escape 节点同时带 `reads` / `consumes` / `emits` 是否允许**：提案 B 未明确 L4 节点可否声明 store 读与工件端口。本稿的 `judge_inject` 同时有 `reads: [trajectory]`、`consumes: {verdict}`、`emits: {decision}`。若编译器要求 escape 节点只能有 `impl_ref` 四字段，则该读侧需改为「经工件传递」。
6. **check 节点如何拿到 store 内容**：本稿 `verdict` 用 `reads: [trajectory]`（非 LLM 节点读侧声明，提案 B §1.2「读权限在消费者侧声明」）读轨迹槽，但 `uses.unit` 的判定单元在运行期如何获得该槽内容（是否需要改成 `consumes` 端口）提案未定义。
7. **`message_log` 槽无 `item` 类型**：承 golden `sample1.yaml`，轨迹槽的条目结构由运行时决定（故 `trajectory` 槽不声明 `item`）。
8. **`meta.topology_selector` 未布点**：Reflexion 的两类基准族（代码生成 vs 决策/问答）差异落在 **Evaluator 与工具面（运行时组件）**，不在拓扑；而选择器是**编译期**语义、候选图须是已声明的版本化图/子图（裁决 §二-1）。本文件是单一拓扑，故不布点（若要布，需先声明两张候选图，本 DSL 单文档不支持）。
9. **段顺序 = 拼装序**：卡片③指出「反思置于任务描述之前或之后在论文变体中有差异」。本稿取「反思在前」，属**变体选择**而非论文定论。
10. **`escape.kind` 在 M1 是可选字段**：`crates/af-dsl/src/model.rs:540` 为 `Option<EscapeKind>`（golden `sample6.yaml` 成文早于裁决故未带 kind）。本稿按裁决 §二-2 **补齐** kind，取值均在闭环词表内；未知变体由 serde 拒（E1004）。

---

## 五、自检记录（全部实跑）

### 5.1 必做检查：YAML 解析

```
$ cd /home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿
$ python3 -c "import yaml,sys; d=yaml.safe_load(open('Reflexion.yaml')); print('YAML_OK top-keys=', sorted(d.keys()))"
YAML_OK top-keys= ['edges', 'meta', 'nodes', 'policies', 'stores', 'types', 'version']
```

→ **通过**；七段键集与 golden 样例一致（`version` 首键、无第八段）。

### 5.2 加做检查：真实 af-dsl 编译器前端（M1 解析 + 引用闭包 + INV-2）

用 af 仓的 `af-dsl` crate（`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl`）的公开 API `load_str` + `validate`（`crates/af-dsl/src/lib.rs:26/48`）跑本稿（壳工程建在 `/tmp/afb-reflexion-check`，未改动 af 仓任何文件）：

```
$ /tmp/afb-reflexion-check/target/debug/afb-reflexion-check ".../对齐草稿/Reflexion.yaml"
PARSE_OK name=reflexion_episodic version=1
VALIDATE_OK (0 violations)
```

→ **通过**（0 违例）。覆盖：信封 + 七段 serde 解析（全文 deny_unknown_fields）、类型/节点/store/端口引用闭包（E2001/E2201/E2202/E2205/E2106）、INV-2 写者唯一性与 carried 覆盖（E2311/E2312/E2211）、预算 scope/cap（E2207）、retention 有界（E2208）、失败路由目标（E2204）、词表（E1004）。

### 5.3 加做检查：CEL 保守子集实跑

`/tmp/afb-reflexion-cel`（`/tmp/afb-check` 沙盒的私有副本，绑定根补入本稿的三个节点 id）：

```
$ printf 'r1\tverdict.passed == false\nr2\tjudge_inject.decision.warranted == true\nr3\tmemorize_guard.entry.writable == true\nr4\tattempt.passed == true\ns1\tsteps.iterations >= 4\ns2\tbudget.cents_spent >= budget.cents_cap\n' > /tmp/reflexion_expr.tsv
$ /tmp/afb-reflexion-cel/target/debug/afb-check /tmp/reflexion_expr.tsv
PASS r1	verdict.passed == false
PASS r2	judge_inject.decision.warranted == true
PASS r3	memorize_guard.entry.writable == true
PASS r4	attempt.passed == true
PASS s1	steps.iterations >= 4
PASS s2	budget.cents_spent >= budget.cents_cap
----
total=6 fail=0
```

→ **通过**（6/6：可解析、算子全在白名单、根绑定在位置词表内、求值为布尔）。

### 5.4 六节自检清单（逐项过）

| # | 清单项 | 检查方式 | 结论 |
|---|---|---|---|
| 1 | **信封** | `version: 1` 为首键；顶层键集恰为七段（5.1 输出）；af-dsl `envelope::check` 通过（5.2 PARSE_OK） | ✅ |
| 2 | **类型表** | `types` 登记 5 个类型（`reflexion_input`/`answer`/`verdict_record`/`reflect_decision`/`reflection_entry`）；全部 `emits`/`consumes`/`store.item`/`meta.input`/`meta.output.ref` 引用均已登记 → af-dsl E2205 未触发（5.2，0 违例）；对象 schema 只住 `types` 表，端口无内联对象 | ✅ |
| 3 | **单写者（INV-2）** | `trajectory` 唯一写者 `attempts.actor`；`episodic_buffer` 唯一写者 `attempts.memorize`；无 map 体并发写；外层 loop 的 `carried` 覆盖体内写的两条体外声明槽 → af-dsl INV-2（E2311/E2312/E2211）未触发（5.2，0 违例） | ✅ |
| 4 | **配额** | 每个 `context.sections[]` 均带 `quota_tokens`（actor 4 段 600/400/500/4000；reflect 4 段 600/100/300/4000）；每条 store 的 `retention` 至少一个上界（`trajectory` max_items 128；`episodic_buffer` rolling_window 64 + keep_system） → E2208 未触发（5.2） | ✅ |
| 5 | **预算** | `policies.budgets` 4 条：`loop:attempts`(turns 40) / `node:attempts.reflect`(model_calls 4) / `plan`(cents 300) / `plan`(tokens_total 800000)；scope 均可解析（`node:` 走点号路径 `attempts.reflect`）、cap>0 → E2207 未触发（5.2）；`policies.stop` 2 条 CEL 已过沙盒（5.3） | ✅ |
| 6 | **逃逸记账** | 2 个 escape 构造，四字段（impl_ref/reason/owner/share_budget_pct）齐备 + 裁决 §二-2 的 `kind` 在七类闭环词表内；占比 25% < 30% 警戒线；未用类别与理由已列（§二） | ✅ |

### 5.5 未做/无法做的事（如实）

- **未跑** af-dsl 之外的编译器模块（M2 context.sections 语义、INV-1/M3 INV-3+INV-4、M4 route 归一化与 CEL 静态判定）：这些模块按裁决 §四-4 尚未实现，仓库内无可执行件。route 归一化（§1.5 的 guard 构造）与 CEL 静态判定我只做了**沙盒级**验证（5.3）与**人工**核对（三个 route 节点的出边均被 rule/default 覆盖，E2101/E2102/E2103 不触发；goto 目标均为体内节点或 `exit`）。
- **未改** `/home/pan-ding/workspace/af-wt-phase2-dsl` 仓内任何文件（只以 path 依赖方式引用其 `af-dsl` crate 做只读校验）；`/tmp/afb-reflexion-check`、`/tmp/afb-reflexion-cel` 为临时壳工程。
- **未做**：把本稿登记进 af-dsl 的 golden testdata（属他人仓的测试资产，不在本任务的两个交付文件范围内）。
