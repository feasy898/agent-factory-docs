# MetaGPT · AFB 翻译记录（notes）

- 目标：MetaGPT（Hong et al. 2023，软件公司 SOP 多角色流水线）
- 草稿：`计划/研究组/对齐草稿/MetaGPT.yaml`
- 信源（全部读过）：
  - `计划/研究组/对齐机制卡/INDEX.md`（定位第 6 张卡 = MetaGPT.md，4224 字，标注「流水线+结构化工件交接」）
  - `计划/研究组/对齐机制卡/MetaGPT.md`（六节全文，重点 ⑥）
  - `计划/研究组/DSL-语法提案-B.md`（§1 七段+六构造 / §2 正交性 / §4 样例 2 MetaGPT / §5 四条不变量 / §6 码表）
  - `计划/研究组/DSL-语法择优-裁决-20261024.md` §二（`meta.topology_selector` 编译期语义；`escape.kind` 七类词表）
  - 语法参照：`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/testdata/sample1.yaml`（golden 种子）
  - 解析器事实：`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/src/model.rs`（M1 AST：`EscapeDecl{kind?,impl_ref,reason,owner,share_budget_pct}`、`Meta.topology_selector`、`LoopDecl.safety_points` 必填、`EmitSpec` 自定义反序列化）、`src/validate/{refs,inv2}.rs`（E2001–E2331 判定规则）、`crates/af-dsl/RESULT-M1.md`（23 码位与偏差表）

---

## 一、机制 → 语法映射表（逐条对应卡⑥(a)，共 12 项）

| # | 卡⑥(a) 机制 | AFB 落点（草稿中的具体位置） | 判定 |
|---|---|---|---|
| a1 | 有向流水线拓扑 + 结构化工件交接 | `nodes`（pm/architect/planner/build/semantic_verdict/terminate）+ `edges` 13 条类型化工件边；静态 SOP 流水线，非 ReAct 式单节点环 | 完整表达 |
| a2 | 角色 = 带输出类型声明的 actor 节点 | 每个角色一个 `kind: task` 节点 + `uses.model`；输出端口类型化：`pm.emits{prd: envelope<prd>}`、`architect.emits{design: envelope<design>}`、`planner.emits{tasks: list<task_item>}`、`qa.emits{report: qa_report, cases: list<test_case>}` | 完整表达 |
| a3 | 结构化工件 = 端口类型化 payload，schema 即接口契约 | `types` 表 16 个类型（prd/design/task_item/code_file/test_case/qa_report/exec_report/…）+ `emits`/`consumes` 双端类型；每条边编译期类型相等核对（M1 E2201）+ 运行期 schema 校验（补 LangGraph G3 缺口） | 完整表达 |
| a4 | SOP 图 = 静态拓扑 + 边工件类型 + **节点优先级顺序** | 前两项 = `edges` + 端口类型；**「节点优先级顺序」在 AFB v0.1 无字段**（见 §四 语法不确定点 1），用静态边序 + `meta.topology_selector` 的候选图切换近似 | **部分表达**（子项缺失） |
| a5 | `cause_by` = 工件血缘/溯源元数据 | 端口类型即信封：`envelope<prd>` / `envelope<design>`（血缘由运行时填 `from_node/artifact_type/step`）；`envelope<T>` 是类型不是边标记（B §1.2） | 完整表达 |
| a6 | pub/sub 消息通道 = 异步总线 + 主题订阅 + 角色级 inbox 隔离 | 角色级 inbox 隔离 = 每角色一个 `message_log` 槽（`pm_memory`/`architect_memory`/`planner_memory`/`engineer_memory`/`qa_memory`，各单写者）；**主题订阅与运行时收件人 = 逃逸舱**（`watch_match`/`pick_recipients`），静态边只是其编译期近似 | **部分表达**（触发/收件人转逃逸） |
| a7 | TaskFinished = 声明式终态信号 | `terminate.emits{done: signal}`（内建 `signal` 零载荷端口类型）+ `meta.output{ref: signal, from: terminate}`；配套 `policies.stop` 兜底 | 完整表达 |
| a8 | 角色记忆 = 按因果链过滤的滚动上下文 | 滚动上下文 = 每角色 `message_log` 槽 + `context.sections` 的 `{from: store, policy: latest_k, args:{k}}`；**「按 cause_by 因果链过滤」= 逃逸舱**（`scope_inbox`，运行时上下文自改写） | **部分表达**（因果链过滤转逃逸） |
| a9 | 模板化生成 = schema 约束的结构化输出 | `context.sections` 的 `{from: template, template_ref: pkg.sweng.*_system}` + `types` 表 schema 约束 + `policies.failures[schema_invalid]`（不合约 → 同节点重试 + `format_reminder` 回灌） | 完整表达 |
| a10 | QA 回环 = 带反馈边的拓扑 | `build` 受控循环：体 = engineer → run_code → parse_exec_log → role_retry → apply → qa；`qa.route{rules:[{when: "qa.passed == false", goto: engineer}], default: exit}`；`max_iterations: 3`、`carried` 有界携带、`safety_points:[{node: qa, kind: check}]`、`exit_when: "attempt.passed == true"`、`on_exhausted: fail` | 完整表达 |
| a11 | 工作区文件 = 外部工件存储（跨角色共享） | `stores.repo`（`collection` of `code_file`，`writer: build.apply` 点号路径单写者，INV-2），`apply` transform 的 `merge` op 末端落点为该槽 | 完整表达 |
| a12 | 状态序列化 = 检查点/恢复机制 | `edges[].checkpoint: true`（architect→planner、planner→build、build→semantic_verdict 三条边），快照语义由 af-plan 承载 | 完整表达 |

**小计**：12 项全部有落点——完整表达 9 项（a1、a2、a3、a5、a7、a9、a10、a11、a12），部分表达 3 项（a4 的「节点优先级顺序」子项、a6、a8），部分表达的残余全部落在卡⑥(b) 的逃逸清单里，不新造语法。

**卡④/⑤ 的补充落点**：失败处理 = `policies.failures` 九类词表中的 6 类（schema_invalid / tool_error / environment_failure / gate_refused / timeout / budget_exhausted）；停止条件 = `policies.stop`（`steps.turns` 步数上限 + 预算上限兜底，因为论文明确「未给出通用 max_round」）；预算 = `policies.budgets`（cents/tokens_total/turns，含 `scope: loop:build`）。

---

## 二、逃逸清单（卡⑥(b) 共 9 项，逐项一个 `escape` 节点 + 七类词表记账）

| 卡⑥(b) | 机制 | 草稿节点 | `escape.kind`（七类词表） | 记账理由（`reason` 摘要） | share_budget_pct |
|---|---|---|---|---|---|
| b-1 | 运行时由 Action 依赖元数据推导/改写 SOP 图 | `sop_rewrite` | `meta_loop` | 拓扑并非只写一次（`required_previous` 可改流程），静态图声明无法保真 → 运行时图重写；`meta.topology_selector` 是编译期语义，只能覆盖预声明候选图 | 15 |
| b-2 | `_watch` 订阅 + cause_by 链触发的激活语义 | `watch_match` | `runtime_context_mutation` | 角色由「消息类型是否命中订阅表」决定是否响应，而非静态边唤醒；激活判定在运行时求值 | 15 |
| b-3 | 运行时决定消息收件人（定向 send_to / 广播 / all_agents） | `pick_recipients` | `meta_loop` | 边在运行时才产生（等价于运行时改图）；静态边只能近似其存在性，不能近似目标集合 | 10 |
| b-4 | 代码生成与执行副作用（RunCode 真跑、写工作区） | `run_code` | `env_adapter` | 有状态环境契约：核心只允许调用包内注册的动作面；任意代码执行与副作用经逃逸并版本化登记 | 25 |
| b-5 | 运行错误文本回灌 prompt（stderr/测试输出） | `parse_exec_log` | `free_text_parser` | stderr 是自由文本，需解析为结构化失败项（`failure_item`）后才能回灌；自由文本双向解析不进核心 | 10 |
| b-6 | LLM 判定的语义终止（QA 通过/不通过是模型判断） | `semantic_verdict` | `llm_predicate` | 语义判定谓词不能落 CEL；类型化的确定性判定已在 `qa`（`kind: check` + `uses.unit`）落点，此节点只承接 LLM 语义判定 | 15 |
| b-7 | 双层上下文可见性（角色私有记忆 + 环境全局池） | `scope_inbox` | `runtime_context_mutation` | 作用域化上下文装配（按 cause_by 链过滤）在运行时完成；`context.sections` 只能表达来源与配额 | 15 |
| b-8 | 用户通道与人工介入（send_to_user / 中断续跑） | `user_channel` | `env_adapter`（**借用，见 §四 语法不确定点 3**） | 交互式会话挂起与跨进程中断续跑属有状态环境契约；词表无「人工介入」类 | 10 |
| b-9 | 异常与重试策略内嵌于角色循环（重试次数/回灌策略由用户代码决定） | `role_retry` | `runtime_context_mutation` | 静态 `failures` 预算只给兜底，不覆盖运行时策略改写 | 10 |

- 逃逸节点数 = 9，与卡⑥(b) 条目数 1:1 对应；每个 `escape` 四字段齐（`kind` + `impl_ref` + `reason` + `owner` + `share_budget_pct`，M1 `EscapeDecl` 必填四字段 + 裁决吸收的可选 `kind`）。
- 词表使用分布：`meta_loop`×2、`runtime_context_mutation`×3、`env_adapter`×2、`free_text_parser`×1、`llm_predicate`×1；`dynamic_tool_registry`、`program_synthesis` 两类本目标未涉及（MetaGPT 不做运行时工具注册，也不合成程序/拓扑——拓扑合成由 b-1 的 `meta_loop` 承担）。
- 声明占比合计 125%，超过 ADR-001 的 30% 健康度警戒（运行期指标，非编译期门禁）——**这是本目标的诚实边界**：9 项逃逸中有 3 项（b-2、b-3、b-7）是消息总线/运行时路由族机制，其本质是「运行时才确定边」，AFB v0.1 的静态边 + `route` 归一化无法保真。若评审认为该占比不可接受，优先处置项是 b-2/b-3/b-7（合并为一个「消息总线」逃逸舱，或在 v0.2 引入运行时触发器语法），而不是压缩 b-4/b-5/b-6（这三项是论文的硬机制，任何压缩都是失真）。

---

## 三、语法不确定点（诚实列出，未编造语法）

1. **「节点优先级顺序」无落点**：卡⑥(a)-4 要求 SOP 图带「节点优先级顺序」。AFB v0.1 的 `nodes`/`edges` 只有拓扑与类型，没有优先级/轮转次序字段；`meta.topology_selector` 是编译期选择候选图，不是运行时优先级。草稿用**静态边序**近似（PM→架构师→派发→构建的拓扑顺序即轮转顺序）。这是**语法缺口**，不是逃逸——运行时优先级轮转属卡⑥(b)-2（`watch_match`）的语义，已在逃逸侧记账，故未新造 `priority` 字段。
2. **CEL 根绑定的作用域解析未验证**：`semantic_verdict.verdict.needs_human == true` 用了「节点 id → 端口 → 对象字段」三层点号。B §1.4 只明文写到「对象端口可继续点字段」，样例 3 有 `vote.stats.top_count`（节点→端口→字段）两层的实证；三层的可见范围（`route` 规则可见范围含节点自身）依 B §1.4 推导，M4 尚未实现，**未能在编译器侧验证**。若 M4 判 `semantic_verdict.verdict` 不可解析，等价改法：把 `needs_human` 提为 `verdict` 的独立端口（`emits{verdict: verdict, needs_human: boolean}`），CEL 改为 `semantic_verdict.needs_human == true`（两层，已有实证）。
3. **逃逸舱词表缺「人工介入/交互挂起」类**：七类词表（裁决 §二-2）没有对应 `human`/`interrupt` 的类。`user_channel` 借用了 `env_adapter`（有状态环境契约）并在 `reason` 里写明「词表无人工介入类」。备选：`human` 构造（`station/role/quorum/resume.schema`）能承接**类型化恢复值**那一半，但承接不了「角色反应中途向用户提问 + 跨进程中断续跑」，故仍按逃逸记账。→ 建议 v0.2 词表新增 `human_interaction` 类。
4. **`meta.output.ref: signal` 是否被下游接受**：终态产物取内建 `signal`（TaskFinished）是我按卡⑥(a)-7「声明式终态信号」做的判断。M1 的 `PortType` 允许 `signal`（`TypeExpr::Signal`），E2202 判定也通过（`terminate` 确实发射 `done: signal`）；但「整图输出契约是否接受零载荷 signal」在 M1 之后无先例（golden 样例的 `meta.output.ref` 都是对象类型）。若编译器要求终态产物为对象类型，退路是 `meta.output{ref: qa_report, from: build}`（golden 样例 2 同形），并保留 `terminate.emits{done: signal}` 作为 TaskFinished 载体。
5. **`meta.topology_selector` 的候选图不在本文件内**：AFB v0.1 无「候选图声明段」（`subgraphs`/`graphs` 段不存在于七段结构），因此 `use: "pkg.sweng.sop_full@1.0"` 指向的是**包产物**（与 `pkg.*`/`route.*` 同族的引用面），其存在性由装载期（E9001/E9002）核对。本草稿未在核心段声明任何候选图，避免编造语法。选择条件 `input.sop_variant` 是配置项（论文无此字段），只用于覆盖卡⑥(b)-1 的**编译期可表达部分**（论文消融实验里的 SOP 变体：全流程 / 去 QA / 最小集），运行时改写仍在 `sop_rewrite` 逃逸舱。
6. **`ops` 输出侧字段级映射未核对**：B §8 开放问题 1 明说 v0.1 不在编译期核对 transform 输出的字段映射（由装载期组件契约核对，E9003）。草稿里 `apply` 的 `merge` op 与 `qa.emits{cases: list<test_case>}` 的字段级对应关系未经编译器核对。
7. **逃逸节点的角色边界**：`watch_match`/`pick_recipients`/`scope_inbox`/`sop_rewrite` 四个逃逸节点在草稿里是**流水线上的真实节点**（工件经它们流转），而它们的语义（运行时路由/装配）在核心语法里并不存在。这是有意的：把「运行时才确定的部分」显式画进拓扑，而不是让静态边假装它可表达。风险是读者可能误以为静态边 + 这四个节点等价于 MetaGPT 的消息总线——notes 与 `reason` 已注明「静态边只是编译期近似」。
8. **`failures.route: same_node` 在「角色内重试」语义上的落差**：B §1.2 的 `route` 取值域是节点 id 或 `same_node`/`next_iteration` 关键词；卡④说「角色 react 内部捕获异常并重试」（重试发生在角色运行时内，不是图上跳边）。草稿用 `same_node` + `retry{max:2}` 近似；精确语义在 `role_retry` 逃逸舱（b-9）里。

---

## 四、自检记录（本 ask 内实跑）

| # | 检查 | 命令 | 结果 |
|---|---|---|---|
| 1 | YAML 解析（ask 指定） | `python3 -c "import yaml,sys; yaml.safe_load(open('.../MetaGPT.yaml'))"` | **通过**（无异常）；顶层键 = `['edges','meta','nodes','policies','stores','types','version']`，与 golden 种子同构 |
| 2 | 顶层结构抽样 | 同上 + 打印节点/逃逸/槽/边计数 | 节点 11（含 loop 体内 6 个）/ 逃逸 9 / 槽 7 / 边 13 / 类型 16 |
| 3 | **af-dsl 前端实测**（信封 + 形状 + 引用闭包 + INV-2 语义层，M1 全部 23 码位） | 自建校验器 `/home/pan-ding/afbcheck`（用 `~/afbuild-phase2d` 预编译的 `libaf_dsl` rlib 直接 `rustc` 链接，源码在 `/home/pan-ding/afbcheck.rs`，**未改动 af-wt-phase2-dsl 仓任何文件**）<br>`$HOME/afbcheck ".../MetaGPT.yaml"` | `LOAD OK` + `VALIDATE OK: 0 violations (M1 semantic layer)`<br>对照组：同一校验器对 golden `testdata/sample1.yaml`、`sample2.yaml` 同样 0 violations（校验器有判别力的旁证见下） |
| 4 | M2/M4 未实现的规则的近似结构自检（INV-1 入边端口恰被一个 edge section 覆盖 / route 覆盖与互斥 / ops 参数闭合 / carried 覆盖跨作用域写入 / 单写者 / retention 有界 / 预算与失败路由作用域） | `python3 /home/pan-ding/afbcheck.py ".../MetaGPT.yaml"` | `STRUCT OK`（0 问题）；对照组 golden `sample2.yaml` 同样 `STRUCT OK` |
| 5 | CEL 保守子集（真实 cel-interpreter 0.10.0 沙盒：`Program::compile` + `references().functions() ⊆ 算子白名单` + `references().variables() ⊆ 位置词表` + 合成上下文求值为布尔） | 自建沙盒 `/home/pan-ding/celcheck`（`cel-interpreter 0.10.0`，离线构建，未改任何仓文件）<br>输入 = 从草稿递归抽取的 7 条表达式（`when`/`exit_when`）<br>`/home/pan-ding/celcheck-target/debug/celcheck /home/pan-ding/cel_exprs.tsv` | `total=7 fail=0`，7 条逐条 PASS：<br>`input.sop_variant == 'full'` / `input.sop_variant == 'no_qa'` / `qa.passed == false` / `attempt.passed == true` / `semantic_verdict.verdict.needs_human == true` / `steps.turns >= 60` / `budget.cents_spent >= budget.cents_cap` |
| 6 | CEL 校验器判别力（反向对照） | 同上，输入 3 条负例 | `total=3 fail=3`：`size(...)` → 非白名单函数拒；`unknown_root.x == 1` → 未知根绑定制；`steps.turns + 1` → 非布尔拒 |

**未跑项（如实）**：
- **M2（INV-1 上下文完整性 + `context.sections` 来源可解析 + 配额正数）**：M2 尚未实装，本稿用检查 4 的近似脚本覆盖，但 `input.fields ∈ meta.input schema`、`edge.port` 的字段级 schema 归属等未由编译器核对。
- **M3（INV-3 生成器-验证器分离 / INV-4 评估器外部化）**：未实装。本稿自查：`qa`（`kind: check` + `uses.unit`）的入边生产者是 `apply` 而非自身（不触发 E2321）；`safety_points` 的 `qa` 是验证面（满足 E2322 的 kind 白名单）。本稿无 `eval_input: true` 的槽，故 INV-4 无触发面。
- **M4（route 归一化 + CEL 静态判定 + topology_selector 解析）**：未实装。检查 4/5 是我自建的近似实现，**不能替代编译器裁定**。
- 编译期 IR 降维快照 / 计划对象快照：未跑（按 ADR-007 属 af-dsl/af-compiler 落地时的测试项）。

---

## 五、六节自检清单（逐项）

| 项 | 结论 | 依据 |
|---|---|---|
| 信封 | ✅ `version: 1` 顶层首键；七段齐全（meta/types/stores/nodes/edges/policies + version）；`meta` 含 `name/graph_version/entry/input/output/intent` 与裁决吸收的 `topology_selector` | af-dsl M1 `load_str` 通过（E0001–E0004 未触发） |
| 类型表 | ✅ 16 个类型全部登记于 `types`；端口类型只用 `名 / list<名> / envelope<名> / signal`；无内联对象 schema | M1 `E2205`/`E1003` 未触发 |
| 单写者 | ✅ 7 个槽各一个写者：`planner`(tasks_board)、`build.apply`(repo)、`pm`、`architect`、`planner`、`build.engineer`、`build.qa`；写者路径均为根可解析点号路径；`carried` 覆盖体内写的体外槽（repo/engineer_memory/qa_memory） | M1 `E2311`/`E2211`/`E2001` 未触发 + 检查 4 |
| 配额 | ✅ 每个 `context.sections` 条目都有正整数 `quota_tokens`（含 store 段与 edge 段）；`latest_k` 段均带 `args.k` | 检查 4（配额正数 + latest_k 参数） |
| 预算 | ✅ `policies.budgets` 4 条：cents/tokens_total（plan）、turns（node:pm / node:architect / loop:build），`cap` 均 > 0，作用域均可解析 | M1 `E2207` 未触发 + 检查 4 |
| 逃逸记账 | ✅ 9 个 escape 节点，`kind` 全在七类词表内，`impl_ref/reason/owner/share_budget_pct` 四字段齐全，与卡⑥(b) 1:1 对应 | M1 `E1004`（词表）/`E1002`（字段）未触发；对照 §二 清单 |

---

## 六、一句话结论

MetaGPT 是提案 B §7 分级里的「优雅」目标：SOP 流水线、结构化工件 typed 交接、`cause_by` 血缘、QA 回环、TaskFinished、工作区文件、检查点共 9 项机制有标准语法落点（`nodes/edges/types/stores/loop/route/escape`），另有 3 项（节点优先级顺序、pub/sub 触发与收件人、因果链过滤的上下文作用域）只能部分表达，残余由 9 个 `escape` 逃逸舱按七类词表记账——**其中 b-2/b-3/b-7 三项共享「运行时才确定边」的本质**，是本目标最诚实的边界，也是 v0.2 语法扩展的第一候选。
