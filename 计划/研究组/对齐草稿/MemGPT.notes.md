# MemGPT → AFB DSL 翻译记录

- 目标：**MemGPT**（中断驱动式分层记忆 / LLM 操作系统，Packer et al. 2023，arXiv:2310.08560；后产品化为 Letta）
- 输入卡片：`计划/研究组/对齐机制卡/MemGPT.md`（六节齐全，3703 字；INDEX 第 18 行登记「成 / 3703 字 / 正常 / 未动用 Mem0 备选」）
- 语法依据：`计划/研究组/DSL-语法提案-B.md`（AFB 正本骨架，§1 七段字段表 + §1.3 六构造 + §2 正交性 + §4 样例 2/3 精读）+ `计划/研究组/DSL-语法择优-裁决-20261024.md` §二-1（`meta.topology_selector` 编译期语义）、§二-2（`escape.kind` 七类闭环词表）
- 语法参照样例：`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/testdata/` 下的 `sample1.yaml`…`sample6.yaml` 六个单文件（M1 已解析通过的 golden 种子）；**ask 里写的 `sample1-6.yaml` 合并文件不存在**（已核实该目录内容）
- 编译器参照：`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl/src/model.rs`（七段 serde AST，含裁决吸收的 `meta.topology_selector` 与 `escape.kind` 枚举）、`validate/`（M1 引用闭包 + INV-2）
- 交付物：本文件 + 同目录 `MemGPT.yaml`
- 日期：2026-10-24

> 声明：本文件是**草稿记录**，不构成验收结论；最终通过与否由编译器裁定。未改动工作区内任何现有文件；两处临时校验沙盒建在本机 `/home/pan-ding/.cache/`（`afb-memgpt-cel` = cel-interpreter 保守子集沙盒；`afb-memgpt-check/struct_check.py` = 结构自检脚本）与 `/tmp/afb-reflexion-check`（**他人已建**的 af-dsl 前端调用壳，本稿只读复用其已编译二进制，未改其源码）。

---

## 一、机制 → 语法映射表（逐条对应卡片⑥）

### ⑥(a) 可映射为「标准拓扑 + 组件」的机制（7 条，全部落标准语法，零逃逸）

| 卡⑥(a) | 机制 | AFB 落点 | 说明 |
|---|---|---|---|
| 1 | 中断驱动的单节点 ReAct 式循环 = 节点「思考—调工具—观察」+ scheduler 的 event trigger 入口 | 外层 `session` 受控循环（`max_iterations: 12` = 全局最大步数）+ 内层 `step` 受控循环（`max_iterations: 4` = 步内调用上限 N）；`intake` 取中断事件（`args: { event: intake.event }` 构成隐式依赖边），`agent` = 思考节点，`mem_dispatch` = 工具执行面 | 两级循环分别对应卡④的两条独立上限：「步内最多 N 次函数调用」与「最大步数/总 token 硬超时」。**未用单节点 ReAct 形态**——因为 MemGPT 的每步调用上限是论文级的可调参数（1–4），单节点自环无法把它与全局步数上限分开声明 |
| 2 | 主上下文 / 外部上下文分层（resident tier vs paged-out tier）+ 上下文组装阶段 | 五个 `stores` 按层分族：`core_memory`（kv，run）+ `message_buffer`（message_log，run，rolling_window）= **常驻层**；`archival_memory`（vector_index，persistent）+ `recall_history`（collection，persistent）= **分页层**；组装阶段 = `agent.context.sections` 的 7 段有序装配 | **AFB 无显式 tier 字段**：分层由「哪些槽以 `policy: full` 注入、哪些以 `policy: retrieve` 按需注入」隐式表达（见 §四-2 语法不确定点）。装配顺序照卡片③-2：指令 → 核心记忆 → 缓冲 → 本步中断 → 外部检索 |
| 3 | 自编辑记忆函数 = 带 **write-back 副作用**的记忆写边（append / replace 双算子），区别于普通工具 | 工件 `core_edit`（`mode: append\|replace` + `section` + `content`）= 写边载荷；写者 `host_mem`（`writes: [core_memory, ...]`）；`core_edit.mode` 的闭集即双算子 | 写边的**拓扑与类型**是标准语法（`mem_dispatch` 产出 `edit` 端口 → `host_mem` 消费并落库）。**副作用的运行时判定**（模型自选写什么）归 L4（见 ⑥b-1） |
| 4 | 归档记忆检索、对话召回 = 只读检索边，结果以 observation 回注上下文 | 只读边：`agent.context.sections` 的两条 `policy: retrieve` 段（`archival_memory` k=5 / `recall_history` k=5，`component: pkg.memgpt.similarity@1`）；回注通道：`mem_dispatch` 产 `observation` → `host_mem` 追加进 `message_buffer` → 下一轮 `agent` 以 `policy: full` 读回 | 检索边本身只读（检索方不写被检索槽），符合卡⑥a-4 的「只读」限定。**与论文有一处有意差异**（论文要求模型显式调用 `archival_search`/`conversation_search` 才能检索；本稿让检索结果直接注入上下文）→ 见 §四-3 |
| 5 | 向量库 / 消息库 = 外部 state provider 引用（跨会话持久存储） | `archival_memory`（`type: vector_index`，`lifecycle: persistent`，单写者 `session.step.archive_store`）+ `recall_history`（`type: collection`，`persistent`） | 槽的**声明**是标准语法；**provider 本身**（跨会话存储及其一致性语义）归 L4（见 ⑥b-7） |
| 6 | 每步调用上限、上下文上限 = 运行时守卫（budget guard）属性，可静态声明 | 步内调用上限 = `step.loop.max_iterations: 4`；主上下文上限 = `mem_guard`（kind=gate）`assert: "inputs.report.tokens <= 4000"` + 预算 `ctx_tokens`（`tokens_total`，`scope: node:session.step`，cap 4000）；`safety_points: [{node: mem_guard, kind: gate}]` | 「守卫」用验证面（gate）+ 内建 `passed` 端口承载；`policies.failures` 里 `gate_refused` 承接守卫拒绝（卡④「上下文超预算」） |
| 7 | 消息缓冲窗口 = 环形/滑窗记忆策略，静态可配 | `message_buffer` 的 `retention: { policy: rolling_window, max_items: 20, keep_system: true }` | AFB 的 `rolling_window` 是唯一具名 retention policy，正好对上卡⑥a-7 的「按条数或 token 窗口滚动」 |

**⑥(a) 判定为标准拓扑/组件可表达的机制数 = 7 / 7。**

### ⑥(b) 预计需要 DSL 逃逸舱的机制（7 条，逐条判定）

| 卡⑥(b) | 机制 | 判定 | 落点 / 理由 |
|---|---|---|---|
| 1 | 运行时自改写核心记忆（模型自己重写提示词片段并即时改变后续所有步骤的输入） | **逃逸（已布点）** | `host_mem`（`escape.kind: runtime_context_mutation`）：执行 `core_edit` 的写回副作用并即时改写常驻层。**图结构不变但上下文内容在运行时自生成**——这是本卡最核心的 L4 机制 |
| 2 | 运行时自由选择下一工具（可调用集合与调用序列由模型在运行时决定，不可静态枚举） | **逃逸（已布点）** | `mem_dispatch`（`escape.kind: dynamic_tool_registry`）：运行时函数注册表的分派面，闭合词表 `core_memory_append / core_memory_replace / archival_insert / archival_search / conversation_search` 在其实现内 |
| 3 | 自然语言终止谓词（「直到模型不再发出函数调用」无法用固定步数循环表达） | **逃逸能力已备（主路径未启用）** | 主路径用**结构判据** `exit_when: "last_message.has_tool_calls == false"`（卡④的「模型返回不含函数调用的 assistant 消息 → 本步结束」本身就是结构信号，非自然语言语义判定）；若换成「模型以自然语言自述已完成」的语义终止，则需 `semantic_done`（`escape.kind: llm_predicate`）注入非确定性谓词。该节点已布点在图内但不在关键路径上（启用 = 改一行 `exit_when`） |
| 4 | 动态注入量与预算分配（检索返回条数/长度运行时才确定，主上下文预留多少给外部结果不可静态计算） | **逃逸（已布点）** | `host_mem`（`runtime_context_mutation`）：运行时决定回注量与预算分配，产出 `context_report`（`tokens` / `injected`）供守卫判定 |
| 5 | 语义化分页/驱逐（「先写外部再驱逐主上下文条目」，驱逐条件是语义条件而非静态规则） | **逃逸（已布点）** | `host_mem`（`runtime_context_mutation`）：语义驱逐条件 + 降级裁剪最旧消息（卡④「若模型不驱逐，宿主降级裁剪」） |
| 6 | 任意时刻插入的中断（用户消息可抢占正在进行的生成并改变步边界） | **逃逸（已布点）** | `intake`（`escape.kind: env_adapter`）：宿主事件队列适配器。**静态拓扑只能表达步边界处的取事件**，生成中途的抢占语义只能在该实现内完成 → 见 §四-4 |
| 7 | 跨会话一致性（外部存储写入与后续会话读取的一致性语义超出单次拓扑声明范围） | **逃逸（已布点）** | `archive_store`（`escape.kind: env_adapter`）：跨会话持久外部存储适配器，`archival_memory` 的唯一写者 |

**⑥(b) 判定为需要逃逸舱的机制数 = 7 / 7**（全部布点；其中 3 条共用同一逃逸节点 `host_mem`，故**逃逸节点数 = 5**）。

---

## 二、逃逸清单（escape 构造 + 七类词表记账）

七类词表（裁决 §二-2，承提案 A）：`dynamic_tool_registry` / `program_synthesis` / `meta_loop` / `runtime_context_mutation` / `env_adapter` / `free_text_parser` / `llm_predicate`。

| 节点（路径） | escape.kind（词表内） | impl_ref | owner | share_budget_pct | 对应卡片 | 理由（YAML `reason` 字段摘要） |
|---|---|---|---|---|---|---|
| `session.loop_body.intake` | `env_adapter` | `packages/memgpt@1.0.0/hatches/event_intake.py` | lang-team | 4 | ⑥b-6 | 中断可抢占生成并改变步边界；静态拓扑只表达步边界取事件 |
| `session.loop_body.step.loop_body.mem_dispatch` | `dynamic_tool_registry` | `packages/memgpt@1.0.0/hatches/mem_dispatch.py` | lang-team | 8 | ⑥b-2 | 记忆管理函数的可调用集合与调用序列运行时决定，不可静态枚举 |
| `session.loop_body.step.loop_body.archive_store` | `env_adapter` | `packages/memgpt@1.0.0/hatches/archive_store.py` | lang-team | 5 | ⑥a-5 + ⑥b-7 | 跨会话持久外部存储及其写入-读取一致性语义 |
| `session.loop_body.step.loop_body.host_mem` | `runtime_context_mutation` | `packages/memgpt@1.0.0/hatches/host_mem.py` | lang-team | 9 | ⑥b-1 + ⑥b-4 + ⑥b-5 | 自编辑写回副作用（append/replace 双算子）+ 运行时回注量与预算分配 + 语义化分页/驱逐 |
| `session.loop_body.step.loop_body.semantic_done` | `llm_predicate` | `packages/memgpt@1.0.0/hatches/semantic_done.py` | lang-team | 3 | ⑥b-3 | 自然语言终止谓词；主路径未启用（结构判据已足够） |

- 逃逸舱数（YAML 中 `escape:` 构造数）：**5**
- 逃逸预算占比：**4 + 8 + 5 + 9 + 3 = 29%**，低于 ADR-001 §3 的 **>30% 警戒线**（健康度指标，不触发编译期拒绝）
- 四字段闭合：`impl_ref` / `reason` / `owner` / `share_budget_pct` 全部齐备（E2210 的 serde 前置），并按裁决 §二-2 补 `kind`，取值均在闭环词表内
- **未使用的三类**及理由：`program_synthesis`（无程序合成——MemGPT 不生成/执行代码）、`meta_loop`（无元智能体改图——拓扑是静态的，模型只改记忆不改图）、`free_text_parser`（记忆与响应均按 schema 结构化产出，卡片未列自由文本解析需求）
- 已用四类：`dynamic_tool_registry` ×1、`env_adapter` ×2、`runtime_context_mutation` ×1、`llm_predicate` ×1

---

## 三、拓扑与关键取舍（一图）

```
session (loop, max_iterations=12, exit_when=budget.cents 90%, on_exhausted=continue)
 ├─ carried: inbox, core_memory, message_buffer, recall_history, archival_memory
 └─ body:
     intake (L4 env_adapter; writes inbox)  ──event──▶ step
     step (loop, max_iterations=4, args{event: intake.event},
           exit_when=last_message.has_tool_calls==false, on_exhausted=continue,
           carried: core_memory, message_buffer, recall_history, archival_memory)
      └─ body:
          agent (LLM route.main@1; ctx: 指令→核心记忆→缓冲→本步中断→归档检索→会话召回)
            ├─reply──▶ host_mem (L4 runtime_context_mutation; writes core_memory/message_buffer/recall_history)
            ├─reply──▶ semantic_done (L4 llm_predicate; 不在关键路径)
            └─plans─▶ mem_dispatch (L4 dynamic_tool_registry; reads core_memory/archival/recall)
                        ├─observation─▶ host_mem   （函数响应回灌 → 追加进 message_buffer → 下轮 agent 读到）
                        ├─edit───────▶ host_mem   （core_memory_append/replace 写回）
                        └─archive───▶ archive_store (L4 env_adapter; writes archival_memory) ─archived─▶ host_mem
          host_mem ──report──▶ mem_guard (gate; assert tokens<=4000; safety point)
```

- **反馈回路**：`agent` → `mem_dispatch` → `host_mem`（把 observation 追加进 `message_buffer`）→ 下一轮迭代 `agent` 以 `policy: full` 读回缓冲 → 看到函数响应。这条回路**不经图边回边**（AFB 的受控循环按迭代重入体首节点），语义等价于论文的「结果以 function response 追加回上下文」。
- **常驻层 vs 分页层**：`core_memory` + `message_buffer` 以 `policy: full` 全量注入主上下文；`archival_memory` + `recall_history` 以 `policy: retrieve` 按需 top-k 注入。

---

## 四、语法不确定点（诚实列出，不编造语法）

1. **`goto: exit` 的语义边界（继承自 Reflexion 稿的同一疑问）**：提案 B §1.3 只写「`goto: <节点 id 或 exit>`」，未定义 `exit` 是「结束本轮迭代」还是「结束整个循环」。本稿**未使用 `goto: exit`**（改为 `exit_when` + `on_exhausted` 承担终止），因此该不确定性对本稿**不构成风险**——但也意味着本稿无法验证 `exit` 的读法。
2. **AFB 无「记忆层 tier」字段（发现的表达缺口）**：卡⑥a-2 要求「resident tier vs paged-out tier」作为**记忆节点的属性**。AFB 的 `stores` 只有 `type`/`item`/`value`/`writer`/`lifecycle`/`retention`/`eval_input`，**没有 tier / 分层字段**。本稿的近似是：用「`policy: full` 注入 = 常驻层，`policy: retrieve` 注入 = 分页层」这一**读侧约定**隐式表达分层，代价是「哪些槽算常驻」只能由读者从 context 段反推，不能被编译器静态核对。若评审认为分层是机制级必备属性，应在 v0.2 评审考虑给 `stores` 加一个 `tier` 位（承裁决 §四-1 的 G3 翻译痛点证据）。
3. **检索边与论文的显式调用语义有差异（有意为之）**：论文里归档检索/会话召回必须由模型显式发出 `archival_search` / `conversation_search` 函数调用才发生；AFB 的 `policy: retrieve` 段是**声明式自动注入**。本稿**同时**保留了两条路径：`retrieve` 段（自动 top-k 注入，满足卡⑥a-4 的「只读检索边」字面要求）与 `mem_dispatch` 的显式检索函数（满足论文的显式调用语义）。代价：自动注入会**绕过模型的检索决策**，在深度记忆检索基准上会高估表现（与卡片⑤的深度检索基线对比不可直接照搬）。
4. **异步抢占的边界（继承自卡片⑥b-6 的诚实边界）**：`intake` 是**步边界**取事件，不是真正的异步抢占。生成中途的抢占（用户消息插进正在进行的生成、改写步边界）在 AFB 里没有对应原语——`meta` 的 `entry` 是静态的，`loop` 也没有「外部事件打断当前迭代」的语义位。本稿把该语义全部推给 `intake` 的 L4 实现，并在此登记为**未在 L0–L3 表达**的部分。
5. **`gate_refused` 的触发路径未定义**：提案 B 的 `policies.failures.class` 词表含 `gate_refused`，但**未定义「验证面 gate 的 `passed=false` 如何自动升级为 `gate_refused` 失败类」**。本稿的处理是：`mem_guard` 无 `route`（无下游分支），其拒绝通过 `failures[].class: gate_refused / terminal: true / outcome: failed` 兜底。golden `sample2.yaml` 的 `qa` 节点用 `route` 的 `default: exit` 处理不通过路径，本稿因 `mem_guard` 是内层循环的末端（无合法 goto 目标）而未采用该写法 → **需编译器确认失败类与 gate 的挂接方式**。
6. **`escape` 节点携带 `reads`/`writes`/`consumes`/`emits` 是否允许**：提案 B 未明确 L4 节点可否声明 store 读写与工件端口。golden `sample6.yaml` 的 `code_exec`（escape）同时有 `consumes`/`emits`/`writes`，本稿的 `host_mem`（escape）同时有 `consumes`/`reads`/`writes`/`emits`，与 golden 先例同形，但**未在提案正文找到明文授权**。
7. **`node:<id>` 预算作用域对嵌套路径的解析**：`policies.budgets[].scope` 取 `node:session.step`（内层循环节点）。af-dsl M1 的作用域解析（`validate/refs.rs` `resolve_root_path` + `Index::child_node`）**支持点号路径穿 loop/map 体**，实测 0 违例通过；但提案 B §1.2 的 scope 词表只写 `node:<id>`，未说明是否允许嵌套点号路径 → 请编译器确认。
8. **`loop.args` 跨层引用体外的节点**：`step.loop.args: { event: intake.event }` 中 `intake` 是**外层体**的节点、`step` 是外层体的节点（两者同作用域），符合提案 B §1.3「args: `{形参: 节点.端口[.字段] | input.字段}`」的字面要求。已实测 af-dsl M1 解析+校验 0 违例。
9. **`context.sections` 的 `from: arg` 段取整个工件**：本稿用 `{ from: arg, name: event, policy: project, quota_tokens: 400 }` 注入整个 `interrupt_event` 工件（未取子字段）。提案 B §1.2 允许 `arg` 段带 `fields?`，但**未禁止省略 `fields` 而取整体**；本稿按「整体投影」处理。
10. **`meta.topology_selector` 未布点**：MemGPT 的模型配置差异（论文消融：主上下文 2k/4k/8k、每步调用次数、是否开放记忆管理函数、是否开启外部检索）落在**运行时组件与配额**上，不在拓扑上；而选择器是**编译期**语义、候选图须是已声明的版本化图/子图（裁决 §二-1），本 DSL 单文档不支持声明多张候选图，故不布点。
11. **`escape.kind` 在 M1 是可选字段**：`crates/af-dsl/src/model.rs:542` 为 `Option<EscapeKind>`（golden `sample6.yaml` 成文早于裁决故未带 kind）。本稿按裁决 §二-2 **补齐** kind，取值均在闭环词表内。
12. **`semantic_done` 是悬挂工件出口**：该节点产出 `completion_verdict` 但当前无消费者（不在关键路径）。AFB 未定义「可选分支节点」的表达位，也未定义产物是否必须被消费；本稿按「允许存在但不被消费」处理。若编译器要求出口闭合，此节点需改为挂在某条 `route` 上。

---

## 五、自检记录（全部实跑）

### 5.1 必做检查：YAML 解析（ask 指定命令）

```
$ cd /home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿
$ python3 -c "import yaml,sys; yaml.safe_load(open('MemGPT.yaml'))"
（无输出，退出码 0）
```

→ **通过**（YAML 语法合法）。附带确认顶层键集：

```
$ python3 -c "import yaml; d=yaml.safe_load(open('MemGPT.yaml')); print('YAML_OK top-keys=', sorted(d.keys()))"
YAML_OK top-keys= ['edges', 'meta', 'nodes', 'policies', 'stores', 'types', 'version']
```

→ 七段结构无漂移，`version` 为唯一信封键。

### 5.2 加做检查：真实 af-dsl 编译器前端（M1 解析 + 引用闭包 + INV-2）

用 af 仓 `af-dsl` crate 的公开 API `load_str` + `validate`（`crates/af-dsl/src/lib.rs:26` / `:48`）跑本稿（壳工程借用 `/tmp/afb-reflexion-check` 已编译二进制，**未改其源码、未改 af 仓任何文件**）：

```
$ /tmp/afb-reflexion-check/target/debug/afb-reflexion-check ".../对齐草稿/MemGPT.yaml"
PARSE_OK name=memgpt_layered version=1
VALIDATE_OK (0 violations)
```

→ **通过（0 违例）**。覆盖：信封 + 七段 serde 解析（全文 `deny_unknown_fields`）、类型/节点/store/端口引用闭包（E2001/E2201/E2202/E2205/E2104/E2105/E2106/E2107）、INV-2 写者唯一性与 carried 覆盖（E2311/E2312/E2211）、预算 scope/cap（E2207）、retention 有界（E2208）、失败路由目标（E2204）、ops/section 词表（E1004）。

### 5.3 加做检查：CEL 保守子集实跑

沙盒 `/home/pan-ding/.cache/afb-memgpt-cel`（cel-interpreter 0.10.0；绑定根按本稿节点 id 补齐为 `mem_guard`/`agent`/`host_mem`/`mem_dispatch`）：

```
$ /home/pan-ding/.cache/afb-memgpt-cel/target/debug/afb-memgpt-cel /tmp/memgpt_expr.tsv
PASS root.session/loop/exit_when	budget.cents_spent >= budget.cents_cap * 9 / 10
PASS root.session.step/loop/exit_when	last_message.has_tool_calls == false
PASS root.session.step.mem_guard/assert	inputs.report.tokens <= 4000
PASS policies/stop[0]/when	budget.tool_calls_spent >= budget.tool_calls_cap
PASS policies/stop[1]/when	budget.cents_spent >= budget.cents_cap
----
total=5 fail=0
```

→ **通过（5/5）**：全部 CEL 表达式可解析（E1051）、算子全在白名单（E1052）、根绑定在位置词表内（E2203）、求值为布尔（E1053）。本稿全部 CEL 表达式 = 2 条 `exit_when` + 1 条 `assert` + 2 条 `stop.when`（`route` 规则为空——本稿未使用 `route`，故无 route CEL）。

### 5.4 加做检查：结构层自检脚本（提案 B §1/§5 规则口径）

`/home/pan-ding/.cache/afb-memgpt-check/struct_check.py`（独立复核，不依赖 af-dsl 内部实现）：

```
$ python3 /home/pan-ding/.cache/afb-memgpt-check/struct_check.py
escape 节点数 = 5，占比 = 29%
stores = 5，types = 12，节点(含体) = 9
STRUCT_OK 0 violations
```

→ **通过**。脚本逐条核对：类型名全登记（含 `list<>` / `envelope<>` 载荷）、每 store 恰一写者且写者路径可解析、map 体内不写共享槽、retention 有界、carried 覆盖（含嵌套体写入的体外声明槽）、每 section 有正 `quota_tokens`、LLM 节点不声明 `reads`、route 覆盖/互斥（本稿无 route）、预算 cap>0 且 scope 可解析、escape 四字段 + kind 在七类词表 + 占比 ≤30%、边端口存在且两端类型相等。

### 5.5 六节自检清单（逐项过）

| # | 清单项 | 检查方式 | 结论 |
|---|---|---|---|
| 1 | **信封** | `version: 1` 为顶层唯一信封键；顶层键集恰为七段（5.1 输出）；af-dsl `envelope::check` 通过（5.2 PARSE_OK） | ✅ |
| 2 | **类型表** | `types` 登记 12 个类型（memgpt_input / reply / interrupt_event / memory_plan / observation / core_edit / archive_write / context_report / completion_verdict / core_record / archival_record / turn_record）；全部 `emits`/`consumes`/`store.item`/`store.value`/`meta.input`/`meta.output.ref` 引用均已登记 → af-dsl E2205 未触发（5.2，0 违例）+ 结构脚本核对（5.4）；对象 schema 只住 `types` 表，端口上无内联对象 schema | ✅ |
| 3 | **单写者（INV-2）** | `core_memory`→`session.step.host_mem`、`message_buffer`→`session.step.host_mem`、`recall_history`→`session.step.host_mem`、`archival_memory`→`session.step.archive_store`、`inbox`→`session.intake`，五条槽各恰一写者且与 `writes[]` 交叉一致；无 map 体（故无并发写）；两级 loop 的 `carried` 均覆盖「体内（含嵌套体）写入的、体外声明的」全部槽 → af-dsl E2311/E2312/E2211 未触发（5.2，0 违例）+ 结构脚本核对（5.4） | ✅ |
| 4 | **配额** | `agent.context.sections` 7 段全部带正 `quota_tokens`（600/100/1200/2500/400/1200/800）；五条槽的 `retention` 均有上界（core_memory 32、message_buffer rolling_window 20+keep_system、archival_memory 4096、recall_history 2048、inbox 64） → E2208 未触发（5.2） | ✅ |
| 5 | **预算** | `policies.budgets` 6 条：`loop:session`(tool_calls 48) / `node:session.step`(tokens_total 4000) / `plan`(turns 96) / `plan`(model_calls 60) / `plan`(tokens_total 240000) / `plan`(cents 600)；scope 均可解析（含嵌套点号路径 `session.step`）→ E2207 未触发（5.2）；`policies.stop` 2 条 CEL 与 2 条 `exit_when` + 1 条 `assert` 已过 CEL 沙盒（5.3） | ✅ |
| 6 | **逃逸记账** | 5 个 `escape` 构造，四字段（impl_ref/reason/owner/share_budget_pct）齐备 + 裁决 §二-2 的 `kind` 在七类闭环词表内；占比 29% < 30% 警戒线；未用三类与理由已列（§二） | ✅ |

### 5.6 未做/无法做的事（如实）

- **未跑** af-dsl 之外的编译器模块（M2 `context.sections` 语义与 INV-1、M3 INV-3+INV-4、M4 route 归一化 + CEL 静态判定 + topology_selector）：这些模块按裁决 §四-4 尚未实现，仓内无可执行件。CEL 我只做了**沙盒级**实跑（5.3），**编译器静态判定未跑**（M4 未实现）。
- **未跑** af-graph 的图域校验（E2005 环 / E2006 孤立节点 / 循环体安全点检查）：`af-graph` crate 未接入本稿的校验路径；我按提案 B §6 的口径人工核对了根图无裸环、根图仅一节点（`session`，entry 指向它）、两级循环体各自带 `safety_points`（`mem_guard` 与跨层路径 `step.mem_guard`），但**未实跑**该 crate 的校验器。
- **未改** `/home/pan-ding/workspace/af-wt-phase2-dsl` 仓内任何文件（只以 path 依赖方式引用其 `af-dsl` crate 做只读校验）；`/home/pan-ding/.cache/afb-memgpt-cel`、`/home/pan-ding/.cache/afb-memgpt-check` 为本机临时沙盒。
- **未做**：把本稿登记进 af-dsl 的 golden testdata（属他人仓的测试资产，不在本任务的两个交付文件范围内）。
- **未做**：与论文的实验复现/数值核对（卡片⑤的「4k 主上下文 ≈ 27k full-context」等结论卡片已自标「数值存疑」，本稿只取其结构不取其数值）。
