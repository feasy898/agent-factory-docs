# Multi-Agent Debate → AFB 草稿 · 翻译记录

- 目标：`Multi-Agent Debate`（对齐机制卡 `计划/研究组/对齐机制卡/Multi-Agent-Debate.md`，2854 字，六节齐全）
- 草稿：`计划/研究组/对齐草稿/Multi-Agent-Debate.yaml`（AFB v0.1，version 信封 + 七段）
- 语法正本：`计划/研究组/DSL-语法提案-B.md`（§1 七段字段表/六构造、§2 正交性、§4 样例 2/3 精读）
- 裁决补充：`计划/研究组/DSL-语法择优-裁决-20261024.md` §二-1（`meta.topology_selector` 编译期语义）、§二-2（`escape.kind` 七类闭环词表）
- 参照 golden：`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/testdata/sample1.yaml … sample6.yaml`
  **注**：任务书给的路径 `testdata/sample1-6.yaml` 实际不存在；仓库里是 `sample1.yaml`~`sample6.yaml` 六个文件（本目标的 golden 是 `sample3.yaml` = `debate_kv`，已通读，见 `/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/testdata/sample3.yaml:1-155`）。
- 基线关系：本稿以提案 B §4.3 样例 3（`debate_kv`）为底座，**在其上扩展**：检索证据链、可见性矩阵、运行期权重、运行期拓扑变异、多级回退链、裁决自由文本解析，并补齐 10 个 `escape` 逃逸节点。

---

## 1. 机制 → 语法映射表（逐条对应卡 ⑥(a)）

| 卡⑥(a) 条目 | 机制（卡原文） | AFB 落点（节点/构造/字段） | 表达强度 |
|---|---|---|---|
| a1 | 扇出—广播—扇入的轮次循环 = N 辩手并行出解 → 全连接广播同伴解 → 局部状态更新 → 轮控制器迭代 K 次 | `map` 构造 `rounds.debate_map`（`over: input.personas`，运行时定基数、实例间无横向边 ⇒ 同轮互不可见）→ 轮控制器 = `loop` 构造 `rounds`（`max_iterations: 4` = K 轮上限）；扇入 = `rounds.tally`（`ops: tally`）+ 轮外 `vote` | **近似**：扇出/扇入/轮控为原生构造；「全连接广播」DSL 无原语，用「共享 store + 读侧 `retrieve` 段」近似（见 §4 不确定点 2） |
| a2 | 角色多样性 = 同构节点模板 + Persona 参数化分支 | `map` 体内单一模板节点 `rounds.debate_map.debater` + `context.sections[template].vars: {persona: arg.item}`（`arg.item` = map 隐式形参） | 原生 |
| a3 | 多数票聚合 = fan-in 统计节点 | `vote`（`kind: transform`，`ops: tally{by: claim}` + `select_best{by: confidence_milli, prefer: max}`）+ 轮内 `rounds.tally` | 原生（`ops` 闭环词表） |
| a4 | LLM 裁决 = Judge 节点读取 transcript 工件输出终值 | `adjudicate`（`kind: task`, `uses: {model: route.judge@1}`，`context.sections` 含 `{from: store, store: transcript, policy: full}` → 读完整黑板；`{from: input, fields: [question, mode]}` 支持对抗式裁判） | 原生 |
| a5 | 共享黑板交接 = transcript 作为追加式共享工件，轮间持久 | `stores.transcript`（`type: collection`, `item: turn_record`, `writer: rounds.collector`, `lifecycle: run`, `retention: {max_items: 128}`）+ `loop.carried` 登记 → 轮间携带；单写者 = `rounds.collector`（INV-2） | 原生 |
| a6 | 匿名与随机排序 = 消息变换算子（去元数据 + shuffle） | `rounds.broadcast`（`kind: transform`）：`anonymize{drop: [persona]}` → `shuffle_seeded{seed_ref: input.question}` → `truncate{max_tokens_each: 200}`，末端落点 = store `peer_board` | 原生（`shuffle_seeded` 带种子 ⇒ 可复现，与论文的不可复现随机之差见 ⑥b-2） |
| a7 | 局部信念覆盖写 = 每代理 memory write 策略 | `rounds.debate_map.debater.uses.memory: [pkg.debatekit.belief@1]`（逐轮覆盖写的私有信念） | **近似**：per-instance 私有状态不能建成 store（map 体多写者 = E2312），只能落 `uses.memory` 组件绑定；「自解」无 section 来源（见 §4 不确定点 1） |
| a8 | 检索 = 工具节点挂载，证据注入上下文 | `retrieve`（`kind: task`, `uses: {tool: pkg.debatekit.search@1}`）→ `evidence_arbiter`（写 `stores.evidence`）→ 辩手 `context.sections` 含 `{from: store, store: evidence, policy: full}` | 原生（写权限仲裁部分转 ⑥b-8 逃逸） |
| a9 | 上下文装配 = 问题 + 证据 + 他人解 + 自解 | `debater.context.sections` 六段：`template`(角色) / `input`(问题) / `store evidence`(证据) / `store peer_board`(他人解，`policy: retrieve`, `component: pkg.debatekit.per_peer_view@1`, `args: {k: 8}`) / `store visibility_matrix`(可见性策略) / `edge prompt`(运行期拼装的个性化提示)；自解经 `uses.memory` | 原生（自解一项近似，见 a7） |

**⑥(a) 判定**：9 条机制全部有标准拓扑/组件落点（其中 a1「全连接广播」、a7「局部信念/自解」为**近似**而非原生，见上表末列与 §4）。

---

## 2. 逃逸清单（卡⑥(b) 9 项 → `escape` 构造 + 七类词表）

七类词表（裁决 §二-2，`af-dsl` `EscapeKind` 实装值域，见 `/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/src/model.rs:551-560`）：
`dynamic_tool_registry | program_synthesis | meta_loop | runtime_context_mutation | env_adapter | free_text_parser | llm_predicate`

| # | 卡⑥(b) 条目 | 逃逸节点（草稿路径） | `escape.kind` | 理由（`escape.reason` 摘要） | `share_budget_pct` |
|---|---|---|---|---|---|
| b1 | 语义级共识判定（LLM 判断是否已达成一致） | `rounds.consensus_pred` | `llm_predicate` | 停机谓词无法静态声明；静态份额阈值只是近似 | 10 |
| b2 | 顺序随机化的不可复现性 | `rounds.peer_order` | `runtime_context_mutation` | AFB 只有**种子化** `shuffle_seeded`（可复现），运行期无种子置换无算子落点 | 10 |
| b3 | 运行时自适应轮数、震荡后改写提示的退火策略 | `rounds.adaptive_rounds` | `meta_loop` | `loop.max_iterations` 是编译期常量，运行期改写调度参数无落点 | 10 |
| b4 | 运行时修改辩论拓扑（代理掉线、临时增反驳者、锦标赛式配对） | `rounds.topology_mutator` | `meta_loop` | `map.over` 只能静态解析到列表，运行期图变异只能逃逸并版本化登记 | 15 |
| b5 | 运行时打分/权重（裁决按可信度加权，权重由 LLM 给出） | `rounds.weighting` | `llm_predicate` | 运行期数值注入核心无通道；权重经端口 `weights` 送到裁决器 | 10 |
| b6 | 针对性点名反驳与个性化提示的运行时拼装 | `rounds.debate_map.prompt_assembler` | `runtime_context_mutation` | `template.vars` 只能参数化静态模板，无法运行期拼装 prompt 程序 | 10 |
| b7 | 「同伴不可见内部 CoT」的逐节点可见性矩阵 | `rounds.visibility` | `runtime_context_mutation` | `context.sections` 只做来源装配，无可见性裁剪声明位 | 10 |
| b8 | 工具结果回灌给同伴的共享工件写入裁决 | `evidence_arbiter` | `runtime_context_mutation` | `stores.writer` 只约束静态写者集合，无运行期回灌范围声明 | 10 |
| b9 | 多级回退链（平票→裁判→截断→中止） | `fallback_chain` | `meta_loop` | 运行期择路非纯静态图；`route` 只能按静态 CEL 分派一次 | 15 |
| ④-补 | 卡④「输出解析失败 → 限次重解析，仍失败则交由裁决器自由文本判定」 | `free_text_verdict` | `free_text_parser` | 裁决器自由文本 → 结构化 winner，核心无自由文本解析算子 | 10 |

**逃逸计数：10 个 `escape` 构造（10 个节点）**，覆盖 ⑥(b) 全部 9 项 + 卡④ 1 项；用到 5/7 类词表（`meta_loop` 3、`runtime_context_mutation` 4、`llm_predicate` 2、`free_text_parser` 1）；未用到 `dynamic_tool_registry` / `program_synthesis` / `env_adapter`（Debate 无对应机制）。

---

## 3. 逃逸之外仍存在的「表达不到」之处（诚实记账，不藏进语法）

| 机制 | 状态 | 处置 |
|---|---|---|
| 集体错误（全部代理收敛到同一错误）无法自动检出 | 卡④明示「框架内无法自动检出」 | **无语法落点**：草案不做假声明；`policies` 不含对应项，监控告警属运行期职责 |
| 震荡不收敛 | 卡④「轮次上限兜底 + 重复内容检测」 | 轮次上限 = `loop.max_iterations` + `budgets.turns_cap` + `policies.stop`；**重复内容检测**无落点（`ops` 词表无去重算子）→ 未声明 |
| 上下文溢出 → 截断或摘要同伴消息后重入 | 卡④ | 截断 = `truncate` op ✓；**摘要**无算子（`context` 有 `summarize` 视图策略，但无算子级摘要）→ 用 `latest_k`/`retrieve` 窗口近似 |
| 对抗式辩论「偏好真值裁判」 | 卡①变体 | 以 `input.mode` 在图内分流（`vote.route` 规则 `input.mode == 'majority'`）→ **近似**，非编译期择图（见 §4 不确定点 7） |
| 论文的具体评测集/倍数等数字 | 卡⑤自带「存疑」标注 | 未进入 DSL（DSL 无评测集字段），不声明 |

---

## 4. 语法不确定点（诚实列出，未编造语法）

1. **「自解」无 section 来源**：section 来源词表只有 `template | input | arg | edge | store` 五类（提案 B §1.2），没有 `memory`。本稿把「自己上一轮解」落成 `uses.memory: [pkg.debatekit.belief@1]`，其注入由组件契约承担 —— **这是组件面假设，不是语法保证**。
2. **「全连接广播」无原生原语**：DSL 的 `map` 实例间无横向边（互不可见），广播只能靠共享 store + 读侧 `retrieve` 段实现；`peer_board` 的「取最近 k 条 + 按本实例 persona 过滤」由 `component: pkg.debatekit.per_peer_view@1` 实现（组件侧语义，语法不保证）。
3. **escape 节点能否带 `writes`/`consumes`/`reads`**：提案 B §1.3 只写「`task` + 无 uses + `escape` = L4 逃逸节点」，未说明逃逸节点是否可参与数据流。本稿让 `evidence_arbiter`、`rounds.visibility` 作为**唯一写者**写 store，并让逃逸节点互相/向下游送端口。若编译器要求逃逸节点纯记账，则 `evidence`/`visibility_matrix` 的写者需改为非逃逸节点 —— 设计会变。
4. **`exit_when` 能否引用逃逸节点输出**：本稿 `exit_when` 写了 `consensus_pred.verdict.reached == true || adaptive_rounds.advice.stop == true`。提案 §1.4 的节点 id 绑定是否在 `loop.exit_when` 的作用域内可见「loop 体节点 id」未显式说明（样例 3 只用了同体节点 `tally.result`）。若不可见，这两项需改由 `attempt` 绑定或另行设计。
5. **`escape.share_budget_pct` 的口径**：ADR-001 §3 与提案 §8-7 只说「>30% 警戒」而未定义分母。本稿按「每个逃逸节点占其自身执行预算的比例」取 10–15（均 ≤30）；但 10 个节点之和为 110%，若口径是「占全计划预算」则此账不成立 —— 需裁决明确。
6. **`meta.topology_selector`（裁决 §二-1）未被使用**：Debate 的图拓扑是静态的（不需要编译期在多个候选图间择一），故本稿未声明 `topology_selector`。「多数票 vs 对抗式」两套图本可用 selector 择一，本稿改用 `input.mode` 在**同一图内**分流 —— 这是**近似**，若裁决要求以 selector 表达，拓扑要拆成两个版本化子图。
7. **`consumes` 的 `item` 端口**：`map` 体的隐式形参 `item` 在提案 §1.3 有述，但 `consumes: {item: {type: string}}` 的字面形状（内联原始类型作端口类型）在 M1 实现中只对 `consumes` 允许（`emits` 不允许内联，见 `/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/src/model.rs:195-222`）。本稿因此把 `prompt`/`verdict_text`/`confidence_milli` 等标量端口都登记为 `types` 表里的命名类型（`prompt_text`/`verdict_text`/`milli_int`），以保持两端类型字面相等（E2201）。
8. **`free_text_verdict` 的输出类型保证**：把自由文本解析成 `position`（结构化 winner）由组件负责，编译期不核对字段级映射（提案 §8-1：输出侧核对留给 E9003 装载期）。故 `position` 的 `confidence_milli` 由解析器填充是**装载期契约**，非语法保证。
9. **`escape.kind` 在 M1 是可选字段**（`RESULT-M1.md` 偏差 7：裁决晚于样例成文）。本稿一律显式给出 `kind`（未来升必填时本稿无需改动）。

---

## 5. 六节自检清单（逐项过）

| 检查项 | 结论 | 证据 |
|---|---|---|
| **信封** | 通过 | `version: 1` 为首键；顶层键集恰为七段 `['edges','meta','nodes','policies','stores','types','version']`；无未知键 |
| **类型表** | 通过 | 15 个命名类型全部登记（`debate_input, persona_ref, prompt_text, verdict_text, milli_int, position, turn_record, peer_message, evidence_item, tally_result, consensus_verdict, schedule_hint, visibility_plan, weight_vector, final_answer`）；端口类型无内联对象 schema；真实校验器 E2205/E2201 = 0 违例 |
| **单写者（INV-2）** | 通过 | 4 个 store 各 1 写者：`evidence←evidence_arbiter`、`transcript←rounds.collector`、`peer_board←rounds.broadcast`、`visibility_matrix←rounds.visibility`；map 体（`debater`/`prompt_assembler`）不写任何体外 store（E2312=0）；`loop.carried` 覆盖体内写入的 3 个 store（transcript/peer_board/visibility_matrix，E2211=0）；真实校验器 E2311=0 |
| **配额** | 通过 | 12 段 `context.sections` 全部带 `quota_tokens` 且为正（最小 200，最大 6000）；无 LLM 节点声明 `reads`（E2303=0）；每条入边端口恰被一个 section 引用（`debater.prompt`；`adjudicate.winner/roster/weights`） |
| **预算** | 通过 | `budgets` 3 条：`cents/plan/400`、`turns/loop:rounds/30`、`tokens_total/loop:rounds/600000`，dimension 在 8 值词表、scope 合法（`loop:rounds` 确有 loop 构造）、cap>0（E2207=0）；`stop` 1 条（`steps.turns >= 24`）；`failures` 5 条，class 均在 9 值词表，`fallback_route: free_text_verdict` 与 `route: vote` 均指向已声明节点（E2204=0） |
| **逃逸记账** | 通过 | 10 个 `escape` 构造，四字段（`impl_ref`/`reason`/`owner`/`share_budget_pct`）齐全，`kind` 全在七类闭环词表内（E1002/E1004=0）；每类占比 ≤30（警戒线内） |

---

## 6. 实跑记录（命令与输出）

> 环境说明：本次会话中 Bash 工具在完成 af-dsl 校验后失效（任何命令返回 exit 1 且无输出，含 `echo hello`），后续命令改由 `node_repl` 的 `child_process.execSync` 触发，命令本身与输出如实记录如下。

**① 任务书指定的 YAML 解析自检**
```
cd "/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿" && python3 -c "import yaml,sys; yaml.safe_load(open('Multi-Agent-Debate.yaml'))"
→ YAML_SAFE_LOAD_EXIT=0        （退出码 0，无输出即成功）
```
补充结构统计（同一次运行）：`top keys: ['edges','meta','nodes','policies','stores','types','version']`；节点 21（顶层 8 + loop 体 11 + map 体 2）、types 15、stores 4、escapes 10。

**② 真实 af-dsl 校验器（M1：信封 + 七段 serde + 引用完整性 + INV-2）**
做法：把 `/home/pan-ding/workspace/af-wt-phase2-dsl` 复制到 `/tmp/afdsl-check`（未改动原仓任何文件），在副本里新增一个临时测试 `crates/af-dsl/tests/debate_draft_test.rs`（读本草稿 → `load_str` → `validate` → 断言零违例）。
```
cd /tmp/afdsl-check && CARGO_TARGET_DIR=$HOME/afbuild-phase2d cargo test -p af-dsl --test debate_draft_test -- --nocapture
→ violations = 0
   test debate_draft_zero_violations ... ok
   test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```
（该次运行是在补入 `adjudicate.route` 之后跑的，即当前磁盘上的草稿版本。）

**③ CEL 保守子集实跑（cel-interpreter 0.10.0 沙盒）**
做法：复制提案自带的 `/tmp/afb-check` 沙盒到 `/tmp/afb-check2` 并补进本稿新出现的绑定根（`consensus_pred`/`adaptive_rounds`/`adjudicate` 与 `input.mode`），把草稿里全部 5 条 CEL（1 assert、1 exit_when、2 route.when、1 stop.when）写入 TSV 后实跑（因 /tmp 磁盘配额，编译产物改放 `~/afbuild-afb2`，源码在 `~/tmp-afb-check2`）。
```
$HOME/afbuild-afb2/debug/afb-check /tmp/debate-cel.tsv
PASS draft/assert                   inputs.result.top_share_milli >= 0 && inputs.result.top_share_milli <= 1000
PASS draft/loop_exit_when           tally.result.top_share_milli >= 700 || consensus_pred.verdict.reached == true || adaptive_rounds.advice.stop == true
PASS draft/vote_route_when          input.mode == 'majority' && vote.stats.top_count * 2 > vote.stats.answers
PASS draft/adjudicate_route_when    adjudicate.confidence_milli >= 300
PASS draft/stop_when                steps.turns >= 24
---- total=5 fail=0
```
判定口径 = 提案 §4.7 检查 2 的三项：`Program::compile` 可解析（E1051）、`references().functions() ⊆ 算子白名单`（E1052）、`references().variables() ⊆ 位置词表`（E2203）且求值为布尔（E1053）。

**④ 未跑项（如实）**：M2/M3/M4 的规则（INV-1 上下文完整性、E2301/E2302/E2304、E2401–E2403、INV-3/E2321/E2322、INV-4/E2331、route 归一化 E2101–E2103、E2209 ops 闭合、E2210 逃逸语义、M4 的 CEL 静态判定本体）**尚未由编译器实装**，本稿对应条目只做了人工核对（见 §4、§5），不能声称「编译器已验证」。IR 降维快照、计划对象快照、编译器红绿测试同样未跑。

---

## 7. 交付物与工作区卫生

- 交付：`计划/研究组/对齐草稿/Multi-Agent-Debate.yaml`（AFB 草稿）、本文件（`.notes.md`）。
- 工作区其它文件**未改动**；验证用副本与沙盒全在 `/tmp` 与 `~/tmp-afb-check2`（临时件，非工作区仓库）。
- 唯一需要后续拍板的两件事：§4-3（逃逸节点可否参与数据流/写 store）与 §4-4（`exit_when` 能否引用逃逸节点输出）——这两条一旦裁决为「否」，本稿需相应改写拓扑（不是改记账）。
