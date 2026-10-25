# Agensh-DeLM → AFB DSL 翻译记录

- 目标：Agensh（arXiv:2609.26781，微软研究院，1→1024 自组织 harness）+ DeLM（arXiv:2606.10662，斯坦福，共享上下文 𝒞 + 任务队列 𝒯 取代主 agent）双目标合一。
- 卡片：`计划/研究组/对齐机制卡/Agensh-DeLM.md`（2026-10-24 重写版，双目标均经检索核实）。
- 语法正本：《DSL-语法提案-B》（AFB v0.1）+《DSL-语法择优-裁决-20261024》§二（`meta.topology_selector` 编译期语义、`escape.kind` 七类词表）。
- 草稿：`计划/研究组/对齐草稿/Agensh-DeLM.yaml`（version:1 信封 + 七段）。
- 编译器实现参照：`af-wt-phase2-dsl/crates/af-dsl`（M1：信封 + 七段解析 + 引用闭包 + INV-2）。

---

## 一、机制 → 语法映射表（逐条对应卡 ⑥(a)）

| # | 卡 ⑥(a) 机制 | AFL 语法落点 | 草稿中的具体位置 | 保真度说明 |
|---|---|---|---|---|
| 1 | worker 池（同构、仅 ID 不同），并发异步 | `map` 构造：`over` 运行时定基数 + `max_fanout` 封顶 + 隐式 `item` | `workers.map`：`over: boot.roster`、`max_fanout: 1024`；`slot` 节点 `consumes: {item: worker_id}` 显式收隐式入边并 `emits: {who: worker_id}` | 基数由 `boot` 逃逸在运行时产出（阶梯激活），故 `over` 指向节点端口而非 `input` 字段；实例间无横向边（局部工作区互不可见） |
| 2 | 单 worker 五步合作循环（gather→claim→act→verify→merge） | `loop` 构造：内联体五节点链 + `max_iterations` + `exit_when` + `on_exhausted` | `cycle.loop`：体节点 `board_read→msg_pump→guard_pump→gather→claim→lease_guard→negotiate→act→verify→fail_scan→session→merge` + `wrap`（收束子图）；`max_iterations: 24`、`exit_when: "attempt.passed == true"`、`on_exhausted: continue` | 五步被拆成可判定的节点：`gather`=上下文装配、`claim`=认领、`act`=干活、`verify`+`fail_scan`=验证、`session`+`merge`=合并进展；`verify`/`fail_scan` 内部化为「验收 + 未解 fail 扫描」两步验证面 |
| 3 | 条目类型（OBSERVED/FACT/FAIL/CLAIM/PATCH_SUMMARY；100/300 字上限） | `types` 段 schema（字段级 `maxLength`）；血缘用 `envelope<T>` | `types.board_entry`（`entry_type` + `body.maxLength: 300`）、`types.queue_entry`（subject/detail/status/owner/scope）、`types.progress_report`（body/rationale/evidence = PATCH_SUMMARY 三元组） | ①条目类型是**运行时取值**（`entry_type` 字段），AFB 无枚举型 schema 落点；②100/300 分档无法按 `entry_type` 条件化（见 §三-4） |
| 4 | 共享上下文 / 黑板（append-only，全员可查、读取面裁剪） | `stores`（`message_log`）；多写者按写者拆槽 + 读侧内建交错合并 | `stores.board`（`message_log`，`item: board_entry`，`retention.max_items: 2000`），单写者 `board_publish` | **动态 N 的「每实例各写一格、全体互见」在 v0.1 语法未定义** → 本稿用「根级单写者汇聚」近似（`workers` 的 `entries` 出边 → `board_publish`），代价是同一 map 轮内 worker 看不到彼此新条目（该缺口由逃逸 `board_read` 在宿主侧补） |
| 5 | 共享 workspace（proposed/ongoing/completed，PR 合入 main，Git 冲突检测）+ 交付判据（compile.sh → ./executable） | `stores`（`collection`, `lifecycle: persistent`）+ `task(uses.tool)` 节点 + `gate`/`check` | `stores.workspace`（persistent，单写者 `workspace_publish`）；`workspace_publish`（`uses.tool: pkg.agensh.workspace_commit@1`）；`session` 逃逸节点做分支/PR 状态机；交付判据落 `submit_gate`（`assert: "inputs.chosen.evidence != ''"`）+ `verify`（`uses.unit: pkg.agensh.acceptance_gate@1`） | Git 语义（三态/冲突检测/重试）本身无标准拓扑落点，落到 `policies.failures[].class: tool_error` + `route: same_node` + `feedback: conflict_resolution`；PR 状态机在 `session` 逃逸内 |
| 6 | 验证步（对照子任务验收判据，不过即修）；【D】判据取自原任务 | 体内 `check`/`gate` + `route` 回 `act` | `verify`（check，unit）+ `fail_scan`（check，unit）；`verify.route` / `fail_scan.route` 的 rule `passed == false → goto: act`；`verify.context.sections` 直读 `from: input, fields: [acceptance]`（不经子任务摘要） | 「判据取自原任务」由 `from: input` 直读保证；**注意**：check 节点带 `context` 在 M1 可解析，但 INV-1 语义规定 context 仅 LLM-bound task 可用（M2 判定，见 §三-3） |
| 7 | 合并冲突重试（纳入同伴进展→解决→再合并） | `policies.failures[].class: tool_error` + `route`/`retry`/`feedback` | `policies.failures` 第一条：`tool_error` / `route: same_node` / `feedback: conflict_resolution` / `retry: {max: 3, backoff_ms: 2000}` | Git 语义上的重试回路，非拓扑回边；AFB 的回边只有 `route`（本稿用于验收打回），冲突重试落在失败账 |
| 8 | 6h 墙钟预算 + T+6h 全员强制终止 | `policies.budgets`（`dimension: clock_ms`）+ `policies.stop[]` | `budgets: wall_clock / clock_ms / scope: plan / cap: 21600000`；`stop: {when: "budget.clock_ms_spent >= budget.clock_ms_cap", outcome: failed}` | 「全体强制终止」= plan 级 stop；`clock_ms` 是提案 B 已列维度 |
| 9 | T−45/T−5 收束（停止派新特性、合并就绪工作） | `route` 的预算 CEL + 收束子图（声明式近似）；分钟级提醒注入 → 逃逸 | `gather.route`：rule `budget.clock_ms_spent >= budget.clock_ms_cap * 7 / 8 → goto: wrap`（6h 的 7/8 = T−45min）；`wrap` 节点产出 `patch` 汇入 `session→merge`（合并就绪工作） | T−5min 一级与「分钟级提醒注入本体」无法声明式表达 → 逃逸 `guard_pump`（`runtime_context_mutation`） |
| 10 | board_read 最近 2000 条 / board_grep 全史布尔检索 / board_unfold 展开 | `context.sections` 的 `from: store` 策略：`latest_k{k}` / `retrieve{component,k}`；detail 独立工件 | `gather`：`{from: store, store: board, policy: latest_k, args: {k: 2000}}` 与 `{policy: retrieve, component: pkg.agensh.board_grep@1, args: {k: 32}}`；`fail_scan`：`{policy: retrieve, component: pkg.agensh.fail_index@1, args: {k: 64}}`；`board_entry.detail_ref` 承载长文 | `board_unfold`（按条目展开 detail）与【D】的增量游标无静态落点 → 逃逸 `board_read` |
| 11 | worker 协议提示词（全局同模板、仅 ID 异）；底层 harness 选择 | `context.sections` 的 `template` + `vars`；`uses.model` 的 `route.<名>@<版本>` | `gather`/`act`/`merge`/`wrap`：`{from: template, template_ref: pkg.agensh.*_protocol, vars: {worker_id: arg.worker_id}}`；`uses: {model: route.main@1}`（主循环）/ `route.cheap@1`（合并、入队、收束） | 「仅 ID 不同」= 同一 `template_ref` + 唯一变量；harness（Claude Code/Copilot/Codex）的差异落在包内，`route.*` 只表达模型档位 |
| 12 | 【D】任务队列 𝒯（open/claimed/done + owner 全员可见；first-claim-wins） | `stores`（collection，条目含 status/owner）+ `route`；原子性 → 逃逸 | `stores.task_queue`（单写者 `queue_publish`）；`lease_guard`（gate，`assert: "inputs.lease.status == 'claimed'"`）`route` 未抢到 → `negotiate`；`queue_publish` 把 `intake` 的种子与 worker 的 `claims` 合并入槽 | 判定可静态写，**原子抢注不可** → 逃逸 `claim`（`env_adapter`）；`status`/`owner` 的实时可见性因此依赖宿主队列（见 §三-8） |
| 13 | 【D】独立提交判据 ReadyToSubmit（证据覆盖全部需求才提交）；先结束者的任务由下个运行者接管 | `check` + `loop.exit_when`；`on_exhausted: continue` | `cycle.exit_when: "attempt.passed == true"`（attempt = 体内最近验证面 `fail_scan.passed`）；`on_exhausted: continue`；`submit_gate`（gate）作最终交付门禁 | 「证据覆盖全部需求」= 外部判定单元 `pkg.agensh.acceptance_gate@1` + `ReadyToSubmit` 语义近似；接管语义用 `on_exhausted: continue` 近似（AFB 无「他人已结束→任务转移」原语） |

**额外映射（卡片 ③ 数据流里出现、⑥ 未单列但本稿用到）**

| 机制 | 语法落点 | 位置 |
|---|---|---|
| 协作信息「共享介质而非点对点边」（全员共享 + 读取面裁剪） | 三个根级 store + 根级单写者汇聚（`queue_publish`/`board_publish`/`workspace_publish`） | 根级节点区 |
| 消息投递双轨（频道批量 / 私信 mid-turn） | 无静态落点 → 逃逸 `msg_pump` | `cycle` 体内 |
| 五步循环内的「同伴进展消息 + 累积发现」输入面 | `gather.context.sections`：`from: edge`（findings/peer_msg/nudge）+ `from: store`（board/workspace/task_queue） | `gather` |
| DeLM 增量读（只读自上次读取以来的新增） | 无静态落点 → 逃逸 `board_read` | `cycle` 体内 |

---

## 二、逃逸清单（`escape` 构造 + 七类词表记账）

| 逃逸节点 | `escape.kind`（七类词表） | `impl_ref` | 机制 | 为什么标准拓扑/组件表达不了 |
|---|---|---|---|---|
| `boot` | `env_adapter` | `packages/agensh@1.0.0/hatches/activation_roster.py` | 阶梯激活（首小时 1/30s、此后 1/3s）+ worker ID 分配 | 激活节奏是基础设施编排的时间表，`map` 只有 `over`/`max_fanout`，无「激活日程」字段；名单基数运行时定 |
| `board_read` | `runtime_context_mutation` | `packages/agensh@1.0.0/hatches/board_reader.py` | board_read（最新 2000 条）/ board_grep（全史布尔）/ board_unfold（展开 detail）+【D】增量游标 | 游标是「按 agent 记忆的运行时读位置」，`latest_k{k}` 只是近似；全史检索与按条目展开也无 component 落点 |
| `msg_pump` | `runtime_context_mutation` | `packages/agensh@1.0.0/hatches/message_pump.py` | 消息投递双轨：频道消息每轮首投、私信每次基础设施工具调用后 mid-turn 注入 | 「按运行时事件改写 worker 上下文」不是数据边；`context.sections` 只在装配期求值，无法表达 mid-turn 注入 |
| `guard_pump` | `runtime_context_mutation` | `packages/agensh@1.0.0/hatches/idle_guard.py` | idle 10 分钟催工 prompt + T−45/T−5 提醒注入 | 同上：停滞/预算提醒是运行时事件触发的提示注入 |
| `claim` | `env_adapter` | `packages/agensh@1.0.0/hatches/atomic_claim.py` | 【D】first-claim-wins 原子认领 + apply 守卫式复制（拒绝覆盖无法解释的本地改动） | CAS 式条件写入是有副作用原语；CEL 保守子集零副作用，`gate` 只能判定不能抢注 |
| `negotiate` | `llm_predicate` | `packages/agensh@1.0.0/hatches/claim_negotiation.py` | CLAIM 冲突的同伴协商（「谁做/怎么分叉」语义裁决） | 裁决是语义级而非谓词级，保守 CEL 子集写不出 |
| `session` | `env_adapter` | `packages/agensh@1.0.0/hatches/workspace_session.py` | 外部有状态会话：Gitea 分支/PR 状态与合并冲突检测、Mattermost DM 历史、事件路由器重启恢复 | 跨执行的有状态服务契约与恢复语义无静态表达位 |
| `fail_watch` | `llm_predicate` | `packages/agensh@1.0.0/hatches/fail_lifecycle.py` | 【D】fail 条目全局开放语义（「保持 open 直到被新条目或修复子任务处理」） | 跨实例条件联动、无静态边可达；「提交前读上下文解决相关 fail」已用 `fail_scan`（check + `retrieve`）静态近似，全局生命周期部分不可 |

**记账统计**：`escape` 节点 8 个（与卡 ⑥(b) 的 8 条一一对应）；词表分布 = `env_adapter` 3（boot / claim / session）、`runtime_context_mutation` 3（board_read / msg_pump / guard_pump）、`llm_predicate` 2（negotiate / fail_watch）；`dynamic_tool_registry` / `program_synthesis` / `meta_loop` / `free_text_parser` 四类本目标未使用。
`share_budget_pct` 单项最高 5%（session），合计 27%。**口径提示**：提案 B §1.3 只说「占比 >30% 警戒是运行期健康度指标」，未定义聚合口径（逐逃逸 vs 合计）；本稿的合计值仅供参考。

---

## 三、语法不确定点（诚实列出，未编造语法）

1. **`arg.worker_id` 的绑定域**。提案 B §1.4 的绑定表只写了 `item`（map 元素，作用域「map 体内」）与 `args`（loop 形参），没有规定**嵌套体内**（map → loop 两层）`arg.<name>` 如何解析。本稿的 `gather`/`act`/`merge`/`wrap` 位于 `workers.map_body` → `cycle.loop_body` 两层之下，用 `arg.worker_id`（`cycle.loop.args` 形参，由 `slot.who` 桥接）而非 `arg.item`。若 M4 判 `arg` 只解析最近一层 loop，则该写法成立；若判定 `arg.item` 才是 map 侧唯一合法名，需把 `slot` 桥接去掉并改回 `arg.item`。**未验证**（M4 未实现 CEL/上下文装配判定）。
2. **check/gate 节点携带 `context.sections`**。提案 B §1.2 写明 `context` 是「仅 LLM-bound task 可用」，而卡 ⑥(a) 明确要求「D 的『验证判据取自原任务』→ check 节点 `context.sections` 直读 `from: input`」。本稿按卡片口径在 `verify`/`fail_scan` 上写了 `context.sections`（M1 解析层接受，见 §五 实证），但 INV-1 在 M2 落地时可能拒。备选方案：把 `acceptance` 改成 `meta.input` 的一部分由判定单元 `pkg.agensh.acceptance_gate@1` 自取。
3. **escape 节点的读能力**。`escape` 节点按提案 B 是「L4 逃逸节点」，没有 `context`，因此在语法层拿不到 `board`/`task_queue`/input，也无法声明 worker 身份（`arg.worker_id` 对 escape 节点同样不可用）。本稿的 `board_read`/`msg_pump`/`guard_pump`/`claim` 依赖宿主运行时上下文提供 worker 身份与输入——**这是语义外的隐含契约**，AFB 语法未提供声明位（已在 `escape.reason` 中写明）。
4. **条目长度分档不可条件化**。JSON Schema 的 `maxLength` 是字段级，不能按 `entry_type` 分 100/300。本稿取 `board_entry.body.maxLength: 300`（覆盖 PATCH_SUMMARY），`progress_report.body.maxLength: 300`，并在 notes 记录 100 字档丢失。
5. **`ops.merge` 的多端口语义**。闭环词表里的 `merge{ports,into}` 未说明 `ports` 是否可多元素、元素类型是否需一致。本稿 `queue_publish` 用 `merge{ports: [seed, claims], into: task_queue}`（两端口同为 `list<queue_entry>`，落点为 store）——形状自洽但**语义未由提案 B 规定**，装载期若核对 ops 输出形状（E9003）可能要求别的写法。
6. **同一消费者同一端口的多条入边**。`verify → act(feedback)` 与 `fail_scan → act(feedback)` 都写 `act` 的 `feedback` 端口（类型同为 `verify_report`）。M1 逐边核对通过，但「两条边喂同一端口」的合并/择一语义提案 B 未定义。
7. **`budget.<dimension>_cap` 的多预算歧义**。本稿 `clock_ms` 只声明一条、`cents` 只声明一条，故 `budget.clock_ms_cap` 无歧义；若后续为同一维度加多条预算，绑定语义未定义。
8. **`status`/`owner` 的实时可见性**。`task_queue` 的写者是根级 `queue_publish`（INV-2 单写者约束下的必然选择），因此「worker A 认领后 worker B 立刻看到 owner 变化」在声明式层不成立；真实原子性在 `claim` 逃逸的宿主队列内，store 侧是**滞后视图**。这是卡 ⑥(b)6「动态 N 多写者」缺口的直接后果，未用语法手段掩盖。
9. **`meta.topology_selector` 未使用**。本目标无「编译期选择不同候选图」的机制（阶梯激活是运行时行为 → 逃逸），故未声明该字段；裁决书 §二-1 的编译期解析语义在此处没有落点。
10. **跨类型引用的 schema 写法**。JSON Schema 的 `$ref` 跨 `types` 表引用在提案 B 未定义，故 `progress_report` 里的工件清单用 `array of string`（路径）而非 `array<workspace_artifact>` 嵌套对象，避免自造引用语法。
11. **`emits: {}` / `carried: []` 的空集合**。二者都被 M1 接受（实证见 §五），但提案 B 正文未规定缺省/空语义是否等价于「不写该端口」。
12. **`select_best` 的 `by: evidence` 比较对象是字符串**。`best` 节点用 `select_best{port: deliveries, by: evidence, prefer: max}` 选最优交付；`evidence` 是自由文本，字典序比较是否符合「证据覆盖度」语义未定义（论文指标是 test-pass rate，非文本比较）。这是近似，不是论文口径。

---

## 四、六节自检清单（逐项）

| 自检项 | 判据来源 | 结果 | 证据 |
|---|---|---|---|
| ① 信封 | 顶层仅 `version` + 六段；`version: 1` 整型；`meta` 五必填 + `output.from` 唯一发射者 | ✅ | M1 `envelope::check` + `refs::check_meta` 通过（`VERSION`=1，`meta.output.from: finalize` 确实发射 `delivery`） |
| ② 类型表 | 所有端口/集合元素类型均登记在 `types`；无内联对象 schema；`meta.input` 引用表内名 | ✅ | E2205（未知类型名）/E1003（内联对象）均未触发；`PortType` 只用 `list<·>`/`envelope<·>`/表内名三种写法 |
| ③ 单写者 | 每 store 恰一写者；`writer` 与 `writes[]` 交叉核对；map 体节点不得写体外 store | ✅ | INV-2 无违例：`board`→`board_publish`、`task_queue`→`queue_publish`、`workspace`→`workspace_publish`；map 体（`slot`/`cycle` 及 `cycle` 全体内节点）`writes` 全空 |
| ④ 配额 | 每个 `context.sections` 条目 `quota_tokens` 必填且为正 | ✅ | M1 serde 层 `quota_tokens: u64` 必填；实测 25 段全部带配额、正整数，合计 24100 tokens（gather 13.0k / act 3.9k / verify 1.8k / intake 1.6k / fail_scan 1.2k / merge 1.5k / 其余较小） |
| ⑤ 预算 | `policies.budgets` 维度∈词表、scope∈{plan, node:, loop:, map:}、`cap>0` | ✅ | E2207 未触发：`plan`×4、`loop:workers.cycle`（该节点确有 loop 构造）、`node:workers.cycle.act`（跨 map→loop 两层路径可解析） |
| ⑥ 逃逸记账 | 每个 `escape` 四字段齐全 + `kind` ∈ 七类闭环词表 | ✅ | E1002/E1004 未触发；8 个逃逸节点全部带 `kind`（env_adapter 3 / runtime_context_mutation 3 / llm_predicate 2） |

---

## 五、实际执行的检查（如实记录）

1. **YAML 解析自检（任务指定）**
   ```
   cd "/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/对齐草稿" && \
   python3 -c "import yaml,sys; yaml.safe_load(open('Agensh-DeLM.yaml')); print('YAML OK')"
   ```
   输出：`YAML OK`（通过）。

2. **AFB 编译器 M1 前端实跑（比任务要求更强的额外检查）**
   为不改动既有仓，在 `/tmp/afb-check` 建了一个只依赖 `af-dsl`（path 依赖 `/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-dsl`）的临时二进制，`CARGO_TARGET_DIR=/tmp/afb-target cargo build --offline` 后运行：
   ```
   /tmp/afb-target/debug/afb-check ".../对齐草稿/Agensh-DeLM.yaml"
   ```
   输出：
   ```
   PARSE OK: name=agentsh_delm_harness root_nodes=10
   VALIDATE OK: no violations
   ```
   （首轮曾报 1 条 `EdgePortTypeMismatch`：`lease_guard` 未发 `lease` 端口却有一条 `lease_guard→act(lease)` 边；已补 `emits: {lease: queue_entry, conflict: queue_entry}` 后复跑通过。）

   覆盖的 M1 判定：信封（E0001-E0004）、serde 形状（E1001-E1004，含 `escape.kind` 七类词表与 `topology_selector` 结构）、引用闭包（E2001/E2104/E2105/E2106/E2107/E2201/E2202/E2204/E2205/E2207/E2208）、INV-2 写入串行化（E2311/E2312/E2211）。

3. **未执行 / 无法在本轮确认的检查**
   - M2（`context.sections` 语义 + INV-1）、M3（INV-3/INV-4）、M4（route 归一化 + CEL 保守子集静态判定 + `topology_selector`）**均未实现**，因此本稿的 CEL 表达式、`context.sections` 装配、`route` 归一化结果**未经过编译器判定**。
   - 本稿所有 CEL 表达式按提案 B §1.4 的保守子集手写（仅比较/布尔/整数算术/`in`，零函数调用），根绑定取自 §1.4 位置词表（`budget`/`attempt`/`inputs`/`<节点 id>`）；是否全部落在 M4 的 `allowed_roots` 白名单内**未验证**。
   - 未验证 §三 列出的 12 条语法不确定点。

---

## 六、结论与待裁断点（交编译器裁决，草稿不自行裁决）

- 草稿把 **13 条 ⑥(a) 机制全部落到了标准拓扑/组件**（`map`/`loop`/`route`/`stores`/`types`/`check`/`gate`/`transform`/`policies`），把 **8 条 ⑥(b) 机制全部落到了 `escape` 构造**，七类词表逐条记账，无「编造语法」：凡提案 B 未定义的语义（动态 N 多写者槽、激活日程、原子认领、增量游标、mid-turn 注入、跨实例 fail 生命周期、外部有状态会话）一律走逃逸，未自造字段。
- 代价最重的一处是 **共享上下文的「全员互见 + 实时写入」**：INV-2 单写者约束 + 动态 N 写入，使声明式层只能保留滞后视图（§三-8）。这是 v0.2 语法扩展（store 的 per-instance writer 解析规则）的真实压力点，也是裁决书 §四-1 是否为 Agensh/DeLM 开 v0.2 评审的判据之一。
- 建议裁断点：① check/gate 是否允许 `context.sections`（§三-2，直接影响「判据取自原任务」是否可表达）；② 嵌套体内 `arg.<name>` 的绑定域（§三-1）；③ escape 节点是否需要最小读能力声明位（§三-3）。

---

## 七、修订记录（2026-10-24 · E2304 退回修订）

- **日期**：2026-10-24（失败分类账 #5 终裁 = 退回修订）。
- **依据**：`计划/研究组/E2304-作用域复核-20261024.md`。G3 首轮 E2304×4 中，verify/fail_scan 两条系 af-dsl 实现过宽误报（已由 phase2-dsl-fix1，commit 73ccfb2 收窄至仅 LLM-bound 节点后消除）；余下 intake/wrap 两条系本稿 LLM 节点漏引用入边端口——规范层面真违例，按复核报告 §3.2 方案补 2 段 `context.sections`。
- **两处改动**（各 1 行，均插在既有 input 段之后，与复核报告已验证副本 `~/.cache/afb-g3gate/Agensh-DeLM-rev-验证副本.yaml` 逐字节一致）：
  1. `intake`（Agensh-DeLM.yaml:157）：新增 `- { from: edge, port: roster, policy: project, quota_tokens: 800 }`——roster（boot 阶梯激活名单）是入队提示的素材，语义上就是 prompt 上下文；配额 800 依同稿名单类端口先例（:227 gather 的 peer_msg 800）。
  2. `wrap`（Agensh-DeLM.yaml:346）：新增 `- { from: edge, port: brief, policy: project, quota_tokens: 1200 }`——brief（gather 汇出的收束工作简报，:353 入边）是收束提示的上下文；配额 1200 系建议值（复核报告：闸门只要求为正，作者可调）。
- **复验结果**（本机实跑）：
  - harness：`~/.cache/afb-g3gate/g3gate`（load_str→validate，path 依赖 af-dsl 工作树 @73ccfb2，分支现为 phase2-compiler，path 依赖不受分支名影响）；`CARGO_TARGET_DIR=~/afbuild-phase2d cargo build --release` 复核构建 0.07s 无重编译（二进制与磁盘源码一致）。
  - 修订前基线：`REJECT / VIOLATIONS 2 / E2304×2`（intake.roster、wrap.brief，与复核报告 §4 fix1 列一致）。
  - 修订后：`~/afbuild-phase2d/release/g3gate …/Agensh-DeLM.yaml` → **VERDICT PASS，VIOLATIONS 0**。
  - 同 harness 抽查 2 稿（环境一致性）：ReAct → PASS 0；MetaGPT → REJECT E2001×3——均与复核报告 §4 fix1 重跑表逐条相同。
- **随动计数更正**：§四④「实测 25 段全部带配额」现随本修订为 **27 段、合计 26100 tokens**（24100+800+1200），以本记录为准；§三-2 所记「check 带 context 可能被 INV-1 拒」的不确定点已由 fix1 收窄+复核终裁消解（E2304 仅判 LLM-bound 节点，本稿 verify/fail_scan 两 check 不再触发）。
- **改动面**：仅 `Agensh-DeLM.yaml`（+2 行）与本 notes.md（+本节）；其余 14 稿、分类账、其他文件零改动。
