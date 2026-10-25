# AFlow · AFB 翻译记录（对齐草稿）

- 目标：**AFlow**（Zhang et al. 2024，工作流自动搜索：代码表示 + MCTS）
- 交付草稿：`计划/研究组/对齐草稿/AFlow.yaml`
- 依据（本次实读）：
  - `计划/研究组/对齐机制卡/AFlow.md`（六节全文，重点 ⑥(a)/⑥(b)）
  - `计划/研究组/对齐机制卡/INDEX.md`（第 24 行：AFlow 卡片成，字数 3351，置信正常）
  - `计划/研究组/DSL-语法提案-B.md`（§1 七段 + 六构造、§2 正交性、§4 样例 2/3/4、§5 四条 L0、§7 分级）
  - `计划/研究组/DSL-语法择优-裁决-20261024.md` §二（`meta.topology_selector` 编译期语义、`escape.kind` 七类词表）
  - `计划/研究组/对齐机制卡/AFlow.md` ⑥(a) 7 条 / ⑥(b) 6 条
- 语法参照：`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/testdata/sample4.yaml`（golden 种子，AFlow 同面）与 `crates/af-dsl/src/model.rs`（M1 已实现的 AST 形状，含 `EscapeKind` 七类枚举）
- **结论口径**：本文件是**草稿的翻译记录**，不是验收结论；最终通过与否由编译器/评审裁定。

---

## 0. 草稿形状一览

| 项 | 值 |
|---|---|
| 顶层段 | `version / meta / types / stores / nodes / edges / policies`（七段齐全，与 golden 样例顶层键集一致） |
| 节点总数 | 12（含体内）：根图 4（`loader / search / best / materialize`）+ 搜索环体 9 + map 体 1（`exec_one`） |
| 构造用量 | `loop`×1（`search`）、`map`×1（`exec_map`）、`route`×0、`human`×0、`ops`×3 节点（`select`/`scoreboard`/`best`）、`escape`×6 |
| store | 4（`task_set` / `answers_ref` / `codes` / `tree`） |
| 逃逸构造 | 6（`search.mcts` / `search.register` / `search.opguard` / `search.exec_map.exec_one` / `search.cost_probe` / `materialize`） |
| 逃逸预算占比合计 | **95%**（20+25+10+25+10+5）——如实体记账，见 §4 语法不确定点⑩ |

---

## 1. 机制 → 语法映射表（逐条对应卡⑥(a)）

| # | 卡⑥(a) 机制 | 语法落点（草稿内定位） | 判定 |
|---|---|---|---|
| a1 | 工作流 = 有向无环拓扑；节点 = 算子实例；边 = 数据依赖 | `nodes[]` + `edges[]`（根图 3 条边 + 环体 9 条边，端口四字段 `from/output/to/input`） | **完全表达**（静态部分） |
| a2 | Model / CustomizedModel / Toolkit / Agent 四类算子 → 组件目录枚举、类型受白名单约束 | 语义分野落在 `uses` 而非 `kind`：`uses.model`（`mutator`，Model/CustomizedModel 算子）、`uses.tool`（`loader`，Toolkit 算子）、`uses.unit`（`assess`，评估单元）；Agent 算子（角色画像 + 输出格式 + 内部对话历史）= `mutator` 的 `context.sections`（`template` 段=role/profile，`edge` 段=输出格式与输入工件）+ 节点内运行期对话历史 | **完全表达**（本配方可见算子）；候选工作流**内部**的算子实例在运行期生成 → 落 `escape`（见 b1/b3/b6） |
| a3 | 节点间结构化工件交接 + 共享上下文写入 | 类型化端口（`consumes`/`emits` + `types` 表 10 型）、工件边逐边类型核对、共享上下文 = `stores`（`codes` 存候选代码、`tree` 存质量/成本分账） | **完全表达**；血缘位不用 `envelope<T>`（理由见 §4 ⑤） |
| a4 | Agent 节点内部多轮对话 + 格式/反思子步骤 → 单节点内 agent-in-loop + 可插拔节点内策略 | `mutator`（LLM-bound task）：多轮对话/可插拔策略 = `AgentSpec` 运行期（`uses.model: route.main@1` 模型路由 + 组件契约）；格式与角色 = `context.sections`（`template`/`edge` 投影）；反思子步骤 = `pkg.aflowkit.mutator_system` 模板内的结构化输出契约 | **部分表达**：节点内多轮=运行期能力，AFB v0.1 无显式语法位（见 §4 ③） |
| a5 | 任务质量指标（pass@1/accuracy/F1）+ token 成本计量 → 评估组件（注册 metric 与 cost 回调） | 质量指标 = `assess`（`kind: check` + `uses.unit: pkg.aflowkit.evaluate@1`，外部判定单元，装载期 E9003 核类别）；成本计量 = **逃逸** `search.cost_probe`（`runtime_context_mutation`），因成本分依赖运行期调用日志 | **部分表达**（指标=表达；成本=逃逸） |
| a6 | 迭代轮数 / 每轮样本任务数 / 质量阈值 → 预算配置项 + 停止条件 | 轮数 = `loop.max_iterations: 20` + `budgets[iter_turns]`；样本任务数 = `budgets[sample_calls]（scope: map:search.exec_map, dimension: model_calls）`；停止 = `loop.exit_when` + `policies.stop`；**质量阈值**：AFB 无 quality 维度、CEL 位置词表不含 store/嵌套节点端口 → 阈值落在评估单元契约，停止面用 `attempt.passed` 表达 | **部分表达**（阈值落点见 §4 ②） |
| a7 | 搜索结束导出最优工作流 → 编译/物化产物（最终可执行流水线） | 选择最优 = `best`（`select_best` by `quality_milli`）+ `meta.output{ref: pipeline_bundle, from: materialize}`；**物化为可独立运行流水线** = 逃逸 `materialize`（`program_synthesis`，装载体是 Python 代码） | **部分表达**（选最优=表达；物化=逃逸） |

**计数口径**：卡⑥(a) 7 条中，**3 条完全表达**（a1/a2/a3）、**4 条部分表达**（a4/a5/a6/a7），每条部分表达的残余都指向卡⑥(b) 的逃逸项或 §4 列出的语法缺口 → 报 **expressible = 7**（全部有标准拓扑/组件落点），残余全部记账在逃逸清单（6 条）。

---

## 2. 逃逸清单（卡⑥(b) 逐条 → 七类词表归类）

| # | 卡⑥(b) 机制 | 草稿落点 | `escape.kind`（裁决 §二-2 七类） | 理由（摘要，完整版在 YAML 注释里） |
|---|---|---|---|---|
| b1 | 运行时生成/改写工作流图本身（拓扑非静态声明） | `search.register` | `program_synthesis` | 元智能体产出新 DAG，静态拓扑 DSL 无法表达「合成新图」 |
| b2 | MCTS 是对 DSL 程序本身的元层搜索 | `search.mcts` | `meta_loop` | 标准 DSL 只描述一次执行，无法描述「搜索多个拓扑并按价值选择」 |
| b3 | 节点体是任意 Python 函数体（动态控制流/闭包/局部逻辑） | `search.exec_map.exec_one` + `materialize` | `program_synthesis`（2 处） | 静态拓扑只能给接口签名，无法表达函数体；候选代码的解释执行与最终物化都属代码载荷 |
| b4 | token 与成本计量（运行期遥测 + 对数归一化） | `search.cost_probe` | `runtime_context_mutation` | 成本分依赖运行期调用日志，静态声明无法计算。**词表无 telemetry 类**，暂记此类（见 §4 ①） |
| b5 | 评估闭环回调（价值更新、UCB 计数回灌搜索状态） | `search.mcts`（与 b2 共处一个逃逸） | `meta_loop` | 需要运行时回调与可变状态位，AFB 无可变状态语法 |
| b6 | 代码空间约束的完整性校验（拓扑合法性/算子类型匹配/上下文键约束） | `search.opguard` | `dynamic_tool_registry` | 跨候选、跨运行期的约束需按算子注册表在运行期执行；非法拓扑一律拒绝进入搜索树（卡④-2） |

- 逃逸构造数 = **6**；对应卡⑥(b) 条目数 = **6**（b5 与 b2 共处同一逃逸，b3 拆到 2 处构造）。
- 词表使用分布：`meta_loop`×1、`program_synthesis`×3、`dynamic_tool_registry`×1、`runtime_context_mutation`×1；未用 `dynamic_tool_registry` 之外的 `env_adapter`/`free_text_parser`/`llm_predicate`（AFlow 卡 ⑥b 无对应机制）。
- 记账四字段（`impl_ref` / `reason` / `owner` / `share_budget_pct`）全部齐全（脚本核对 `missing_fields=[]`）。

---

## 3. 卡②/③/④/⑤ 组件与数据流的交叉对照（非⑥，供评审抽查）

| 卡节 | 机制 | 草稿落点 |
|---|---|---|
| ② | 算子库（白名单） | `escape` `search.opguard`（`dynamic_tool_registry`）+ `pkg.aflowkit.*` 组件引用（白名单在包里，核心零领域名词） |
| ② | Model / CustomizedModel / Toolkit / Agent 算子 | `uses.model` / `uses.tool(s)` / LLM-bound task + `context.sections` |
| ② | 工作流代码工件 | `code_artifact`（`code_ref`/`parent_ref`/`op_signature`/`source`），存 `codes` 槽 |
| ② | MCTS 控制器 / 元智能体 | `search.mcts`（逃逸）/ `search.mutator`（DSL-native LLM 节点） |
| ② | 任务集与验证集 | `task_set`（题面）/ `answers_ref`（参考答案，`eval_input: true`） |
| ② | 评估器 | `assess`（`kind: check` + `uses.unit`） |
| ② | 最佳工作流导出 | `best` + `materialize` + `meta.output` |
| ③ | 任务实例进入 DAG、按拓扑序流动、输出写入共享上下文供下游按键读取 | `edges`（逐边类型核对）+ `stores`（`tree`/`codes` 单写者）+ `context.sections` 的 `edge`/`store` 投影 |
| ③ | Agent 节点 scratchpad 为节点私有、不跨节点共享 | 每节点独立 `context.sections`（无跨节点共享段）；scratchpad = `AgentSpec` 运行期（无语法位） |
| ③ | 元智能体看到父代码 + 评估反馈 + 变异指令，看不到真实答案 | `mutator` 的 sections：`edge(branch: parent_code_ref/instruction)` + `store(tree: 反馈)` + `store(codes: 父代码)`；`answers_ref` 为 `eval_input: true`，读者仅 `loader`（写者）与 `assess`（check） |
| ③ | 搜索状态挂在 MCTS 树节点上、分支互不可见 | `tree` 槽（`search.scoreboard` 单写）+ 逃逸内部分支隔离；访问计数/UCB 计数在逃逸内维护（见 §4 ⑥） |
| ④-1 | 候选代码语法错误/导入不到算子/抛异常 → 判无效丢弃、重新生成 | `failures[].class: schema_invalid`（`route: same_node` + `feedback: format_reminder` + retry 2）+ `opguard` 拒绝非法候选 |
| ④-2 | 代码空间约束过滤非法拓扑 | `search.opguard`（逃逸，`dynamic_tool_registry`） |
| ④-3 | 单样本失败计入质量分、不中止整轮 | `eval_result.task_results[].ok` + `failures[].class: tool_error`（`route: next_iteration`） |
| ④-4 | 迭代预算耗尽即停 | `loop.max_iterations: 20` + `exit_when` 预算线 + `policies.stop` |
| ④-5 | 早停（目标质量分/成本上限提前终止）**论文中存在性存疑** | 按「存疑项不写死」处理：只保留预算驱动的出口 + `attempt.passed`（评估器判定「达阈值」）——阈值判定权在评估单元契约内 |
| ④-6 | 终止判据 = 树中价值最高者，不依赖人工筛选 | `best`（`select_best` by `quality_milli`） |
| ⑤ | 四层预算 | `max_iterations` + `budgets[iter_turns]`（轮数）；`budgets[sample_calls]`（每候选样本任务数）；`budgets[eval_tokens]`/`[cost_cap]`（token/成本上限） |
| ⑤ | 打分：质量均值 + 成本对数归一化惩罚，UCB 合并质量/成本/探索 | 质量均值 = 评估单元；成本归一化 = `cost_probe` 逃逸；UCB 合并 = `mcts` 逃逸（DSL 侧 `select` 只到价值最大，见 §4 ⑦） |
| ⑤ | 基准 HumanEval/MBPP/GSM8K/HotpotQA | 落在 `pkg.aflowkit.evaluate@1` 与 `metric` 输入字段（领域细节住包里，核心零领域名词） |
| ⑤ | 报告结论（+4.98% / token 成本 −52.8%，卡片标注存疑） | **不写入语法**（结论数字非机制；卡片自标存疑） |

---

## 4. 语法不确定点（诚实列出，不掩盖）

1. **逃逸词表无 telemetry 类**：成本计量（b4）在七类里没有对应词，暂记 `runtime_context_mutation`（其语义是「运行期可变状态/上下文改写」，与「只读取量」的遥测不完全同义）。若评审判定不贴切，需 v0.2 增类或并入 `meta_loop`。
2. **「质量阈值」无语法位**（a6 残余）：AFB v0.1 的预算维度词表无 quality 类；CEL 位置词表只含 `steps/budget/last_tool/last_message/input/resume/attempt/item/inputs/<节点id>`，**不含 store、不含嵌套体节点的点号路径**，因此无法写 `tree` 上最大质量分或 `search.best.quality_milli` 形式。本稿把阈值判定放进评估单元契约（`pkg.aflowkit.evaluate@1`，装载期 E9003 核类别），停止面用 `attempt.passed` 表达——**这是语法缺口，不是逃逸**。
3. **「节点内可插拔策略 / 反思子步骤」无字段**（a4 残余）：AFB 把节点内多轮对话与策略交给 `AgentSpec` 运行期四元组（endpoint/context_template/toolset/policy），语法层没有显式声明位；本稿靠 `context.sections` + 模板包承载格式/角色，反思子步骤只能由模板契约约定。
4. **「物化产物」无语法位**（a7 残余）：`meta.output` 只声明终态工件类型与唯一发射者，没有「编译产物 = 可执行流水线」的表达位；物化由 `materialize` 逃逸承担（`program_synthesis`）。
5. **血缘位未用 `envelope<T>`**：端口类型文法只允许一层泛型（`parse_type_payload` 只收名字或 `signal`），`list<envelope<·>>` 非法；本稿的血缘（`code_artifact.parent_ref`）以显式字段承载。**若要 `envelope<T>` 血缘，需把候选列表拆成单件端口或 v0.2 放宽泛型**。
6. **访问计数/UCB 计数无处安放**：卡③ 要求搜索树节点持有访问次数；AFB 的 `tree` 槽只能存可审计的 (代码引用, 质量分, 成本分)，访问计数属可变运行期状态，留在 `meta_loop` 逃逸内。
7. **扩展粒度落差**：论文是「在已有工作流中挑**某个节点**扩展」，本稿 DSL 侧 `select` 只到「候选级价值最大」，节点级扩展在逃逸内完成——已在 `mcts.reason` 里写明。
8. **首轮空选**：`select` 依赖 `tree` 已有记录，第 1 轮无历史分支时退化为空选；初始节点由 `meta_loop` 逃逸负责（DSL 侧无「根节点」语法位）。
9. **候选并行评估的类型限制**：`map.over` 必须是 list；`list<list<·>>` 非法，故每个候选的逐任务明细聚合成**一条** `eval_result` 记录（内含 `task_results[]`），而不是「候选×任务」的二维表。语义等价、类型面受限。
10. **逃逸占比 95% 远超警戒线**：ADR-001 §3 的 30% 警戒与提案 B §8-7「是否编译期拒绝 >50% 配方」均未决。本稿如实记账（AFlow 的定义性机制确实大部分在逃逸里，与提案 B §7 对 AFlow 的分级「必须逃逸舱（部分）」一致），请评审裁定是否需要降占比或开豁免。
11. **未使用 `meta.topology_selector`**：裁决 §二-1 给它的语义是**编译期**决定「编译产物采用哪个候选图」，而 AFlow 的候选选择发生在**运行期**（MCTS 搜索 + 价值择优）。用它表达会误述论文机制，故不用。可考虑用它另立一个「离线预搜后择优编译」的部署变体配方（需评审确认是否属于 AFlow 机制面）。
12. **卡片自带的不确定项**：MCTS 轮数 20（卡④-4 标「具体数值存疑」）、成本归一化公式（卡⑤ 标「具体公式存疑」）、早停是否存在（卡④-5 标「存疑」）——本稿按「机制层采信、数字层标注」处理，未把存疑数字写成硬约束（`max_iterations: 20` 已附注）。
13. **预算作用域的嵌套写法**：提案 B §1.2 只写 `scope ∈ plan|node:<id>|loop:<id>|map:<id>`，未规定嵌套体节点的写法；M1 校验器按根图点号路径解析，**实测必须写 `map:search.exec_map`**（初稿写 `map:exec_map` 被 E2207 拒）。建议正本补一句「嵌套构造用根图点号路径」。

---

## 5. 自检记录（本次实跑）

### 5.1 要求的 YAML 解析自检

```
$ cd /home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿
$ python3 -c "import yaml,sys; yaml.safe_load(open('AFlow.yaml'))"
PARSE_OK
```
（命令无输出即成功；随后脚本化打印得到 `top-keys: ['edges','meta','nodes','policies','stores','types','version']`、`version: 1 (int)`。）

### 5.2 额外自检：AFB 前端真实解析 + 语义校验（af-dsl M1）

用已构建的 `libaf_dsl` 直接跑 `load_str` + `validate`（临时 harness 在 `/tmp`，未改工作区任何文件）：

```
$ rustc --edition 2021 -L <af-wt-phase2-dsl>/target/debug/deps \
    --extern af_dsl=<...>/libaf_dsl-85216d0d9e6f58ff.rlib /tmp/afb_check_aflow.rs -o /tmp/afb_check_aflow
$ /tmp/afb_check_aflow .../对齐草稿/AFlow.yaml
LOAD_OK (envelope + shape parse passed)
VALIDATE_OK (0 violations)
```
> 说明：M1 覆盖信封 + 七段形状 + 引用闭包 + INV-2；**不覆盖** INV-1/INV-3/INV-4/route/CEL（见 `crates/af-dsl/src/lib.rs:7-9`），故这三项由人工核对 + 5.4 的 CEL 沙盒补足。5.2 首轮曾报 1 条 `E2207 BudgetCapOrScopeInvalid`（`scope: map:exec_map` 悬空），已按 §4 ⑬ 改为 `map:search.exec_map` 后复跑通过。

### 5.3 六节自检清单（逐项）

| 项 | 检查内容 | 结果 |
|---|---|---|
| ① 信封 | `version: 1` 为顶层首键、整数非布尔；顶层键集恰为七段、无未知键；M1 `envelope::check` 通过 | ✅ |
| ② 类型表 | `types` 登记 10 型；脚本遍历全部 `consumes`/`emits`/`stores.item` 的类型表达式，未登记类型 **NONE**；端口类型只用 `名 / list<名> / envelope<名> / 内联原始四型 / signal` | ✅ |
| ③ 单写者 | 4 个 store 的声明写者与实际 `writes[]` 交叉核对一致：`task_set`←loader、`answers_ref`←loader、`codes`←search.mutator、`tree`←search.scoreboard；map 体节点无写共享槽；M1 INV-2（E2311/E2312）0 违例 | ✅ |
| ④ 配额 | 全部 `context.sections`（4 段：template/edge/store/store）`quota_tokens` 均为正（600/1200/2400/6000）；INV-1 人工核对：每个入边端口恰被一个 section 引用、LLM 节点无 `reads` | ✅ |
| ⑤ 预算 | 4 条预算 `cap>0`、维度∈词表、作用域合法（`plan` / `loop:search` / `map:search.exec_map`）；M1 E2207 通过；`stop` 1 条 CEL；`failures` 3 条（schema_invalid / tool_error / budget_exhausted） | ✅ |
| ⑥ 逃逸记账 | 6 个 escape 构造：四字段齐全（`missing_fields=[]`）、`kind` 均落在裁决 §二-2 七类词表内（脚本 `in_vocab=True`×6）、`share_budget_pct` 合计 95 | ✅ |

### 5.4 CEL 保守子集实跑（真 cel-interpreter 沙盒）

```
$ /tmp/afb-check/target/debug/afb-check /tmp/aflow_expr.tsv
PASS aflow/loop/exit_when     attempt.passed == true || budget.cents_spent >= budget.cents_cap * 9 / 10
PASS aflow/policies/stop[0]/when  budget.cents_spent >= budget.cents_cap
---- total=2 fail=0
```
> 沙盒为提案 B §4.7 记载的 `/tmp/afb-check`（cel-interpreter 0.10.0），不在工作区仓库内；判据 = 可解析 + 函数白名单 + 根绑定在位置词表 + 求值为布尔。

### 5.5 未跑 / 未验项（如实）

- **编译期红绿测试、IR 降维快照、计划对象快照**：未跑（属 af-dsl/af-compiler 落地范围，提案 B §4.7 已登记为未跑项）。
- **INV-1 / INV-3 / INV-4 的机器判定**：M1 未实现（`lib.rs:8` 列为 M2-M4），本次为**人工核对**，非机器判据。
- **组件装载期核对（E9001–E9004）**：未跑（`pkg.aflowkit.*` / `route.main@1` 等包产物在本工作区不存在，装载期不可验证）。
- **CEL 语义正确性**：只验了「语法合法 + 布尔可求值」，未验业务语义（如 `budget.cents_cap` 是否在运行期真被声明绑定）。

---

## 6. 交付计数（供 `submit_result` 口径）

- `target` = AFlow
- `draft` = `/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿/AFlow.yaml`
- `expressible` = **7**（卡⑥(a) 全部 7 条有标准拓扑/组件落点：3 条完全、4 条部分，残余记入逃逸/语法缺口）
- `escapes` = **6**（卡⑥(b) 全部 6 条，落到 6 个 escape 构造，kind 全部取自裁决 §二-2 七类词表）
- `ok` = true（YAML 解析通过 + af-dsl M1 `load_str`/`validate` 0 违例 + CEL 2/2 过沙盒）
