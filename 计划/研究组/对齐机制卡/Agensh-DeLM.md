<!-- TARGET: Agensh（微软研究院·无中心编排者的自组织多智能体 harness，arXiv:2609.26781，2026-09-22 提交）+ DeLM（共享上下文+任务队列取代主 agent 的去中心化 MAS，arXiv:2606.10662，2026-06-09 提交 / v3 2026-10-04） -->
<!-- VERIFIED: 双目标均经网络检索核实（2026-10-24，重写者=对齐机制卡补写者）；原卡「ACTUAL: AutoGen Swarm / CONFIDENCE: LOW」作废。检索词、命中与未核实项见文末附录。机制断言逐条注论文标识（A=arXiv:2609.26781，D=arXiv:2606.10662），节号以 HTML 版为准 -->

## ① 核心机制

Agensh（A）要解决的问题是：多智能体协作的规模与可信度被**中心编排者**卡死——主 agent 逐个派发、逐个汇总，既是延迟瓶颈又是单点瓶颈。它的做法是把协调者整个删掉，只保留三项**基础设施**与一个**写在提示词里的合作循环协议**：①共享 workspace（Gitea/Git 文件系统，承载 proposed / ongoing / completed 三态工作，私有 checkout+分支开发、PR 并入 main，Git 免费提供变更溯源与文本合并冲突检测）；②消息接口（Mattermost：共享任务频道承载团队公告、私信承载紧急点对点）；③共享上下文（append-only 数据库，存可复用发现与工作意图，**其思想明言采自 DeLM**："The idea is adopted from DeLM"，A §2.2）。每个 worker 是一个普通单 agent harness（Claude Code、Copilot 经轻量适配器接入）的实例，**所有 worker 的提示词除 worker ID 外完全一致**——协议住在提示词而非代码里（A §2.3）。worker 们并发、异步地执行五步合作循环：gather context（读目标、当前状态、同伴进展消息与累积发现）→ claim sub-task（向共享上下文追加一条 CLAIM 宣告认领范围，冲突经私信协商）→ take action（本地用工具干活、经共享上下文报告发现）→ verify results（把本地进展对照子任务的验收判据，修正直到满足）→ merge progress（把进展并入共享 workspace，发布带变更内容、背后想法与验证证据的更新）。子任务的发现与分配没有中心分配者：由 worker 自行提议+认领而自组织。DeLM（D，Stanford 项目页自述；作者 Yuzhen Mao、Jerry Gu、Aadi Chauhan、Qizheng Zhang、Hangoo Kang、Azalia Mirhoseini）是这条线的直接前作：它用**共享上下文 𝒞 + 任务队列 𝒯 取代主 agent**，在既有单 agent harness（Codex / Claude Code / AOrchestra）之上跑 n∈{2,4} 个各持持久会话与工作区的 agent——从队列**异步认领**任务（first-claim-wins、每人至多一个未完成认领）、成果可用即发布紧凑 gist、同伴认领与会话状态全员可见；**无特权规划者、无 plan-closure 步**。两系统同属"去中心化/无中心编排"研究线（Agensh 引 DeLM 为文献 [14]），本卡合并覆盖：Agensh 为主目标、DeLM 差异点随文标注。

## ② 组件清单

> 本节断言来源：A=arXiv:2609.26781（摘要+§2），D=arXiv:2606.10662（摘要+§2、附录 A.1）+ 项目页。带【D】者为 DeLM 特有/原型组件。

| 组件 | 类型 | 职责 |
| --- | --- | --- |
| Worker | 角色/执行体 | 同构单 agent harness 实例（Claude Code/Copilot 经适配器接入，A §2.3）；提示词全局一致仅 worker ID 不同，协议由提示词承载而非硬编码 |
| 合作循环 | 执行模型 | 五步：gather context → claim sub-task → take action → verify results → merge progress；并发、异步、无同步轮（A 摘要） |
| 共享 workspace | 状态/工件库 | Gitea/Git 文件系统：proposed/ongoing/completed 三态；私有分支开发、PR 合入 main；issue 承载工作项（issue #1 即任务）；合并冲突由 Git 检测并暴露给 worker 消解（A §2.2） |
| 消息接口 | 通信 | Mattermost：共享任务频道（公告广播）+ 私信（紧急 1:1）；频道消息在每轮循环开始时投递、私信在每次基础设施工具调用结束后 mid-turn 投递；历史保留、投递异步（A §2.2） |
| 共享上下文 | 状态/记忆 | append-only 类型化条目库：OBSERVED（观察到的行为）/ FACT（已确认事实）/ FAIL（失败进路）/ CLAIM（活跃认领）/ PATCH_SUMMARY（补丁摘要）；条目 100 字上限（PATCH_SUMMARY 300），长文入 `detail` 经 board_unfold 展开；思想采自 DeLM（A §2.2） |
| board_write / board_read / board_grep / board_unfold | 工具 | 共享上下文的读写 API：写入发布；board_read 读最近条目（截断至最新 2000 条）；board_grep 全史布尔关键词检索；board_unfold 展开条目详情（A §2.2） |
| idle detector | 运行时保障 | worker 空闲 10 分钟即发催工 prompt（A 实现节） |
| 事件路由器 | 基础设施 | 事件持久化队列 + 唯一 ID 去重 + 失败退避重投；路由器重启可恢复先前会话（A 实现节） |
| 提醒调度 | 预算护栏 | T−45min 与 T−5min 两级提醒：停止派发新特性、合并就绪工作（A 实现节） |
| 【D】任务队列 𝒯 | 协调原语 | 条目=subject+自由文本 detail；first-claim-wins 独占认领、每 agent 至多一个未完成认领；状态 open/claimed/done+owner 全员可见（D §2） |
| 【D】共享上下文 𝒞（原型） | 状态/记忆 | append-only 可复用发现日志：紧凑 gist+显式 scope+evidence 字段；附件按引用挂载、发布时快照；增量读（"只读自上次读取以来的新增"，OS demand-paging 类比）；expand（按与原任务文件的 diff 查看）/ apply（复制入本地，**拒绝覆盖无法解释的本地改动**）（D §2、附录 A.1） |
| 【D】ReadyToSubmit(D, rᵢ, 𝒞) | 终止判据 | 各 agent 独立判定：证据覆盖全部任务需求即提交自己的完整解（D 算法 1） |
| 【D】会话状态跟踪 | 可见性 | starting/running/ended 框架级状态全员可见；先结束者的任务由下一个仍在运行的 agent 接管（D §2） |

## ③ 数据与上下文流

Agensh 的状态分布在三处，且**全部是共享介质而非点对点边**：workspace 文件（真正的工件）、共享上下文条目（发现的摘要与意图）、消息历史（协调会话）。worker 单轮上下文构造 = 任务目标 + workspace 当前状态 + 同伴进展消息 + 累积发现（五步循环第 1 步的输入面）；写回同样是三条通道：代码/文档进 workspace（分支+PR）、发现进共享上下文（board_write，条目类型即 schema）、协调语义进消息（频道/私信）。条目流转有血缘纪律：CLAIM 先行宣告所有权，FACT 供复用（明确要求**不重推同伴已确认的 FACT、不重试已记录的 FAIL**），PATCH_SUMMARY 携带"变更+动机+验证证据"三元组进 PR 描述。可见性是"全员共享 + 读取面裁剪"：共享上下文全员可查，但 board_read 只回最近 2000 条、全史需 board_grep，因此"谁看到什么"是读取 API 的裁剪结果而非静态权限。消息投递时机双轨：频道消息成批于每轮循环开始时注入，私信在每次基础设施工具调用后 mid-turn 注入——协调信息可以打断工具调用间隙进入上下文。DeLM 的差异：读侧是**增量游标**（每 agent 只收自上次读取以来的新增条目），附件不复制本体而按引用挂载（发布时快照），消费经 expand（diff 视图）/ apply（守卫式复制：与本地无法对账的改动一律拒收）；队列状态机（open→claimed→done+owner）与会话状态（starting/running/ended）本身也是全员可读的共享数据。验证输入取自**原始任务**而非子任务摘要（防验收判据在传递链中漂移），提交前还须读共享上下文并解决与自己相关的已发布 fail 条目。

## ④ 失败处理与停止条件

- **认领冲突**（两个 worker CLAIM 同一范围，A）：无自动仲裁——经私信协商消解；协议把"冲突后怎么办"交给模型判断（语义级，非机制级）。
- **合并冲突**（A）：Git 检测文本冲突、阻塞 PR 合并；worker 纳入同伴最新进展、解决冲突后重新合并（重试回路落在 Git 语义上）。
- **重复劳动**（A/D）：A 靠 CLAIM 条目+不重推 FACT/不重试 FAIL 的提示词纪律；D 靠 peer-status 可见性主动止损（论文实例：发现同伴已认领同一调优方向即终止自己的端口搜索）。
- **失败进路沉淀**（D）：fail 条目不可变，发现缺陷只能**追加**新 fail 条目说明成立条件；fail 保持 open 直到被新条目或修复子任务处理。
- **导入冲突**（D）：apply 拒绝带入无法对账的本地改动，调和责任交给接收 agent。
- **死 worker/僵尸认领**（D）：已结束 owner 的队列条目**不阻塞**他人——需要者本地重建、复用共享文件；"claim 归属保留，但不能挡住必需工作"。A 对 stale claim 的过期/GC **未描述**（未核实）。
- **停滞检测**（A）：worker 空闲 10 分钟触发 idle detector 催工 prompt；T−45/T−5 提醒收束。
- **投递可靠性**（A）：事件持久化队列 + 唯一 ID 去重 + 失败退避重投；路由器重启恢复会话。D 的对应对/wait 为**有界等待**（read --wait 至多 25s，同伴发布或结束即返回）。
- **终止**（A）：墙钟预算 T=t+6h 到点**全体 agent 强制终止**；交付前置判据 = 仓库根 compile.sh 产出 ./executable。D：**论文页未描述全局停止条件**（未核实）——每个 agent 独立经 ReadyToSubmit 判定提交，系统级"何时收摊"未见显式机制。

## ⑤ 预算与评估方式

**Agensh**（A §3）：
- 预算：主预算是**墙钟**（6h/任务）；激活节奏为阶梯式（第一小时每 30s 启 1 个、此后每 3s 启 1 个，以减少范围争用；附录 C）；worker 级 token 上限来自底层 harness（Copilot：输入 272,000 / 输出 128,000）。**token 级成本核算未报告**（HTML v1 未见）。
- 基准：ProgramBench（200 实例：给定参考软件从零重建其行为，断网、6h 预算；论文称其为最具挑战的 agentic 软件工程基准之一），取最难的五个任务：FFmpeg、gromacs、pandoc、PHP-src、ctags。模型 GPT-5.6-sol (high)，底层 harness 为 Copilot。
- 指标与结果：final test-pass rate（官方评测口径的 canonical-kept 通过率）。1→128 agent：平均 19.31%→28.78%（约 +49% 相对提升）；更大组织**更早**到达同等通过率；pandoc 单任务 1→1,024 agent：33.89%→55.06%。worker 轨迹定性分析显示自组织协作随规模涌现并标准化。
- 消融：**HTML v1 未见消融节**（仅 1/8/32/128/1,024 规模实验+定性分析；PDF 是否含额外内容未核实）。

**DeLM**（D §3、§3.5）：
- 基准：Terminal-Bench 4.0、DeepSWE v1.1、SWE-bench Verified（基于 AOrchestra 的 harness + Gemini 3 Flash via OpenRouter）、ProgramBench（Claude Code + Claude Opus 5.5，120 分钟预算）。基线：Codex、Claude Code、各家原生 subagents、AOrchestra。
- 结果：至多 **+17.5 点**精度（对最强基线）、至多 **2.49×** 快于其底层 harness；ProgramBench 至多 **+19.9 点**通过率。时间线解剖（retro-console-soc 任务）：Claude Code 主 agent 73% 时间在等待；DeLM agent 仅 2% 等待、提前 5.5× 完成；n=4 时 7.5 分钟（3.6×）。
- 成本：Cost/Task（总 API 成本）与 Cost/Submission（按 n 摊）；共享上下文完成时平均 **<15K tokens**；读上下文开销占任务成本 1.7–3.7%（Opus 5.5）/ 7.7–17.7%（GPT-6-Astra）。
- 消融（§3.5，n=2 @ TB4.0）：去 early sharing（子任务完成才发布）→ 加速跌至 0.98×/0.93×；去 peer-status（无 owner/会话可见性）→ 减速最狠 0.87×/0.82×、精度 −3.3（Opus）；去共享上下文（改直信）→ 1.09×/1.03×、精度 −3.0（GPT-6-Astra）。结论原文："the speedup of DeLM comes from coordination rather than from parallelism alone"——协调介质（共享上下文+队列）是承重墙，不是并行本身。

## ⑥ DSL 表达点清单

> 语法依据：提案 B（AFB）§1——七段（version/meta/types/stores/nodes/edges/policies）+ 节点正交构造（loop/map/human/route/escape/ops）+ 四型 kind（task/gate/check/transform）+ uses 绑定分野；(b) 逃逸归类对照七类词表（裁决书 §二.2：dynamic_tool_registry / program_synthesis / meta_loop / runtime_context_mutation / env_adapter / free_text_parser / llm_predicate）。

**(a) 可映射为"标准拓扑 + 组件"的机制**

- worker 池（同构、仅 ID 不同）→ `map` 构造：`over` 为激活名单（基数运行时定）、`max_fanout` 封顶（如 1024）；worker ID 经隐式 `item` 注入 template vars。实例间无横向边（互不可见的局部工作区），异步并发近似为受控实例并发。
- 单 worker 五步合作循环 → `loop` 构造：body 内联 gather→claim→act→verify→merge 五节点链 + `max_iterations` + `exit_when`（预算 CEL）+ `on_exhausted`。
- 条目类型（OBSERVED/FACT/FAIL/CLAIM/PATCH_SUMMARY；D 的 fact/fail/completion+scope/evidence 字段、100/300/400/800 字上限）→ `types` 段 schema（字段级 maxLength）；条目血缘 → `envelope<T>` 端口类型。
- 共享上下文/黑板 → `stores`（message_log/collection）。**多写者是映射难点**：B 单写者约束下按写者拆槽（每 worker 一槽）+ 读侧多个 message_log 段内建按 step 序交错合并（提案 B §1.2 内建规则；同 §4.5 LangGraph 样例同法）——**静态 N 可行**；动态 N 的"各实例各写一格、全体互见"槽语义提案 B 未定义 → 存疑（见 (b) 6）。
- 共享 workspace → `stores`（collection，`lifecycle: persistent` 承载交付物）+ git 操作 `task(uses.tool)` 节点；交付判据（compile.sh 产出 ./executable）→ `gate` assert 或 `check(uses.unit)`。
- 验证步（对照子任务验收判据，不过即修）→ 体内 `check`/`gate` 节点 + `route` 回 act 节点（QA 打回式回环，同提案 B 样例 2 的 `qa.passed == false → goto engineer`）；D 的"验证判据取自原任务"→ check 节点 `context.sections` 直读 `from: input`（不经子任务摘要，天然满足）。
- 合并冲突重试（纳入同伴进展→解决→再合并）→ `failures[].class: tool_error` + `route`/`retry`/`feedback`。
- 6h 墙钟预算与 T+6h 全员终止 → `policies.budgets`（`dimension: clock_ms`，scope `plan`/`map:workers`）+ `policies.stop[]`（outcome: completed/failed）。
- T−45/T−5 收束（停止派新特性、合并就绪工作）的**声明式近似** → loop `exit_when` 临近预算 CEL（如 `budget.clock_ms_spent >= budget.clock_ms_cap * 3 / 4`）route 到 wrap-up 子图；分钟级提醒**注入**本体见 (b) 5。
- board_read 最近 2000 条 → `context.sections` `from: store, policy: latest_k{k:2000}`；board_grep 全史布尔检索 → `policy: retrieve{component,k}`（L3 检索组件）；board_unfold → detail 独立工件 + 展开工具节点。
- worker 协议提示词（同模板仅 ID 异）→ `template` 段 + `vars: {worker_id: arg.item}`；底层 harness 选择（Claude Code/Copilot/Codex）→ `uses.model` 的 `route.<名>@<版本>` 引用。
- 【D】任务队列 → `stores`（collection，条目含 status/owner 字段）+ `route`（open→认领/已被认领→换件）；first-claim-wins 的**判定**可用 gate 表达，**原子性**不可（见 (b) 3）。
- 【D】独立提交判据（证据覆盖全部需求才提交）→ 各 worker 体内 `check` + loop `exit_when: "attempt.passed == true"`；先结束者任务由下个运行者接管 → `on_exhausted: continue` 语义近似。

**(b) 预计需要 DSL 逃逸舱的机制**（括号=七类词表归类）

1. **CLAIM 冲突的同伴协商消解**（A：私信协商"谁做/怎么分叉"）——语义裁决而非谓词可写 → 逃逸（`llm_predicate`）。
2. **消息投递时机双轨**（A：频道消息每轮首投、私信每次工具调用后 mid-turn 投；共享上下文新条目 mid-turn 前推）——协调信息按运行时事件注入 worker 上下文 → 逃逸（`runtime_context_mutation`）。
3. **first-claim-wins 原子认领与 apply 守卫复制**（D）——CAS/条件写入是有副作用原语，CEL 保守子集零副作用写不出；gate 只能"判定"不能"抢注" → 逃逸，宿主提供有状态队列/合并原语（`env_adapter`）。
4. **增量读游标**（D："只读新增"、demand paging）——游标是按 agent 记忆的运行时读位置；`latest_k` 仅是近似 → 真游标逃逸（`runtime_context_mutation`）。
5. **阶梯激活调度与停滞催工**（A：1/30s→1/3s 启动节奏；10 分钟 idle 探测并发催工 prompt；T−45/T−5 提醒注入）——基础设施编排 + 运行时上下文注入，前者无静态表达（map 无激活日程字段）→ 逃逸（`env_adapter`；催工 prompt 本身归 `runtime_context_mutation`）。
6. **动态 N 的共享账本多写者**——单写者拆槽+读侧交错对静态 N 成立；map 实例数运行时定，"每实例一槽、全员互见"需要 store 声明随 map 体实例化，提案 B §1 未定义该语义 → 存疑，倾向逃逸（`env_adapter`）或 v0.2 语法扩展（store 的 per-instance writer 解析规则）。
7. **外部有状态会话**（A：Gitea 分支/PR 状态、Mattermost DM 历史、事件路由器重启恢复）——跨执行的有状态服务契约与恢复语义 → 逃逸（`env_adapter`）。
8. **fail 条目的全局开放语义**（D："保持 open 直到被新条目或修复子任务处理"）——跨实例条件联动、无静态边可达；提交前"读共享上下文解决相关 fail"可静态近似（check 节点读 store），"保持 open"的全局生命周期不可 → 逃逸（`llm_predicate` + 状态机宿主逻辑）。

---

## 附：检索与核实记录（2026-10-24，重写者=对齐机制卡补写者）

**检索过程**（WebSearch + arXiv 原文抓取，命中路径如实）：
1. `Agensh multi-agent framework LLM` —— 无精确命中（工具建议近似名 AgentScope/Agno 等）。
2. `"Agensh" agent` —— **命中**：arXiv:2609.26781 "Agensh: Scaling Organizational Intelligence to 1,024 Agents"。
3. arXiv 摘要页 + HTML v1 全文直接核实：标题、作者（Zhihao Zhan, Ting Song, Li Dong, Shaohan Huang, Jianxun Lian, Yan Xia, Furu Wei）、单位（Microsoft Research，HTML 版署名行）、提交日期 2026-09-22、三项基础设施、五步循环、ProgramBench 全部数字、"The idea is adopted from DeLM"（§2.2）、引文 [14]=DeLM。
4. `DeLM decentralized LLM multi-agent collaboration 2024 2025` —— **命中**：arXiv:2606.10662 "Decentralized Multi-Agent Systems with Shared Context"（v1 2026-06-09 / v3 2026-10-04）+ 项目页 yuzhenmao.github.io/DeLM（自述 Stanford）+ 代码 github.com/yuzhenmao/DeLM、插件 github.com/Decentralized-LM/delm-agent-plugin、HF 轨迹数据集。arXiv 摘要页 + HTML v3 全文 + 项目页三方交叉核实。

**结论**：
- 双目标**均可考**，原『Agensh 或 DeLM』备选条款无需降级处理，按双卡合一覆盖（Agensh 为主目标、DeLM 为直接前作——两者本就同线，Agensh 的共享上下文思想明言采自 DeLM）。
- m3.1f 批产时不识二者的原因：两文分别提交于 2026-09-22 与 2026-06-09，晚于其训练知识截止——非目标不存在，原卡「CONFIDENCE: LOW」与 ACTUAL: AutoGen Swarm 代写作废。
- 窗口偏差如实记录：使命预期 DeLM 属 2024-2025 方向；检索到的精确同名同方向论文为 2026-06 提交。检索窗口内**未发现** 2024-2025 年名为 "DeLM" 的去中心化协作论文；因名称精确匹配（项目名 DeLM）、方向精确匹配（去中心化 LLM 多智能体协作）、且被 Agensh 明引为思想来源，判定为同一目标。

**未核实项**（如实）：
- DeLM 作者单位在 arXiv 摘要页未列出；"Stanford" 取自项目页自述（未从论文 PDF 复核）。
- DeLM 系统级全局停止条件：论文页未描述 → 本卡 ④ 相应条目标注未核实。
- Agensh 消融：HTML v1 无消融节；PDF 与 HTML 的内容差异未核。
- 两文细节节号（A §2.2/§2.3/§3、D §3.5、附录 A.1/C）以 HTML 抓取为准，未逐条对 PDF 页码。
- 模型名（GPT-5.6-sol、Claude Opus 5.5、GPT-6-Astra、Gemini 3 Flash）均为论文原文转述，未独立核实各模型存在性。

**来源**：
- Agensh: https://arxiv.org/abs/2609.26781 （HTML v1: https://arxiv.org/html/2609.26781v1）
- DeLM: https://arxiv.org/abs/2606.10662 （HTML v3: https://arxiv.org/html/2606.10662v3）；项目页 https://yuzhenmao.github.io/DeLM/；代码 https://github.com/yuzhenmao/DeLM
