# 多 Agent 协同 Harness 调研报告

**面向**：『agent 黑灯工厂』——无人值守的全自动多 agent 产线
**日期**：2026-10-21
**前提**：（1）单体 agent harness 已优化到极限，本报告不涉及单体提示词/工具优化；（2）任务规模天然超出单 agent 能力极限（上下文窗口、连续工作时长、并行度）。
**任务类型**：A）大型项目开发（多模块软件工程、长周期、可并行、需全局一致性）；B）评测驱动的系统优化（假设→实验→测评→迭代的研究循环）。
**核心问题**：单 agent 已到极限的前提下，多 agent 协作『应该』是什么样？哪些协作机制有真实、可检验的价值？

> 说明：本机所有克隆与中间材料均已删除，**报告中全部链接为唯一溯源手段**，均保留为可点击的原文链接。厂内文件（40-计划、50-方案、fix1 代、af 内核等）以文字引用保留，非外部链接。

---

## 1. 执行摘要

### 1.1 推荐基线 harness（一句话）

**以确定性代码化编排运行时为执行底座（S2），入口用三查门控决定『要不要多 agent、并行多大』（S1），全局叠加三闸验证层 v1 最小集（S5：确定性 watchdog 独占合并权 + /goal 会话门 + 合并点冻结上下文评审），任务 B 默认引擎为同预算采样-投票 + 倒 U 停机闸（S8，兼全厂强制基线臂），长时程任务落在跨会话黑板续跑协议上（S6：init.sh + passes 清单 + watchdog 外部核验 + git 检查点 + epoch fencing）；开发类任务经门控路由——map 形进确定性分片-隔离-依赖序集成（S4），可分解非 map 形进双账本星形编排（S3，前置单 agent 地板校验），写耦合走 S3 的单写者降级分支，三查判不通过降级单 agent 长时程跑在 S6 上。**

### 1.2 入选策略清单（9 条：5 推荐 + 4 条件）

| 排名 | 策略 | 任务类型 | 裁决 | 一句话理由 |
|---|---|---|---|---|
| 1 | S8 采样聚合与倒U停机闸 | 两者皆可 | **recommend** | 成本最低、证据最强、是全厂防伪改进的制度性基线：任何复杂协议必须先赢同预算采样-投票，否则判无增量 |
| 2 | S5 三闸生成-验证分离与错误传播治理 | 两者皆可 | **recommend** | 证据链最完整，直击无人值守最危险失败模式（静默坏合并）；验证权收中央不是可选项而是必选项 |
| 3 | S1 入口三查门控与并行度求解 | 两者皆可 | **recommend** | 价值形态是『防损』而非『创造增益』：错误路由一次即按 −70% 区间赔钱（[scaling science](https://arxiv.org/abs/2512.08296)），门控成本近乎为零 |
| 4 | S2 代码化编排运行时 | 两者皆可 | **recommend** | 无人值守的确定性与可恢复性只有代码化编排能满足；v1 优先用厂商 workflow runtime 承载拓扑语义，自建仅限 hub-spoke/WAL/trace 增量 |
| 5 | S6 跨会话黑板续跑与记忆外化 | 两者皆可 | **recommend** | 解决生存问题（会话死亡后不带病接手）；状态外化层进基线，记忆外化层仅对 stateful 跨任务场景开启 |
| 6 | S4 确定性分片-隔离-依赖序集成 | 两者皆可 | **conditional** | 全清单新鲜实证最强（[NP-Bench](https://arxiv.org/abs/2610.07261)：干净集成 1/9→9/9），但仅限门控判 map 形任务 + selector 召回审计达标 |
| 7 | S3 双账本星形编排与单写者降级 | 大型项目开发 | **conditional** | 处于证据最弱区间（90.2% 出自内部 research eval 且同源 caveat 点名编码弱项）；须先过单 agent 地板校验、修正误挂引文 |
| 8 | S7 假设池门控研究环 | 评测驱动优化 | **conditional** | 确定性门（citation 门/三级数据隔离/谱系废黜）立即摘果；六角色环本身必须靠自带的同预算纯采样消融臂证伪后才有资格独立存在 |
| 9 | S9 Harness 自优化双门补丁环 | 评测驱动优化 | **conditional** | 唯一被优化对象=产线自身的策略，风险不对称（修坏自己不知道）；必须排在所有可观测性基建之后、只跑降级版 |

### 1.3 三个关键判断

1. **真正的价值集中在四类：防损（S1 门控避开 −70% 灾难路由）、生存（S2 确定性与 S6 跨会话续跑）、兜底（S5 验证分离防静默坏合并）、下限（S8 同预算采样锁死质量底线）。** 增益型机制（S3 星形、S7 六角色环、S9 自优化）的价值假设均存在被更简单手段解释的高风险，故只给 conditional，并要求其自带的消融/前置条件作为硬门槛。
2. **最强反方证据必须常设**:基座模型解释 41.4% 方差而 scaffold 仅 1.5%（[AI scientists produce results without reasoning scientifically](https://arxiv.org/abs/2604.18805)）；强 prompt 单 agent ≈ 最好的讨论方法（[Rethinking the Bounds](https://arxiv.org/abs/2402.18272)）；六种多 agent 工作流中仅 EvoAgent 稳定胜出（[BenchAgent](https://arxiv.org/abs/2606.05670)）。多 agent 不是默认前提，而是被求解、被证伪的对象。
3. **最大单点风险不是任何机制失效，而是 [MAST](https://arxiv.org/abs/2503.13657) 实测 7 个 SOTA 多 agent 系统失败率 41%–86.7%——选对架构不保证跑通。** 这加重了 S5（验证层）与节点级 trace（可观测性）的权重。

---

## 2. 调研方法与分工

### 2.1 八个调研方向

| # | 方向 | 核心问题 | 代表来源 |
|---|---|---|---|
| 1 | 扩展律与架构选择 | 什么时候该用多 agent？并行度多大？ | [2512.08296](https://arxiv.org/abs/2512.08296)、[2406.07155](https://arxiv.org/abs/2406.07155)、[2606.00655](https://arxiv.org/abs/2606.00655)、[2606.05670](https://arxiv.org/abs/2606.05670) |
| 2 | 星形编排与委派协议 | lead-worker 怎么拆、怎么传、怎么合？ | [Anthropic 多 agent 研究系统](https://www.anthropic.com/research/multi-agent-research-system)、[Magentic-One](https://arxiv.org/abs/2411.04468)、[Cognition Multi-Agents](https://cognition.com/blog/multi-agents-working) |
| 3 | 代码化编排运行时与框架生态 | 拓扑写在 prompt 里还是代码里？恢复语义怎么做？ | [Claude Code workflows](https://code.claude.com/docs/en/workflows)、[Devin dynamic workflows](https://docs.devin.ai/work-with-devin/dynamic-workflows)、[LangGraph](https://github.com/langchain-ai/langgraph)、[AG2](https://github.com/ag2ai/ag2)、[MAF](https://github.com/microsoft/agent-framework)、[ADK](https://github.com/google/adk-python) |
| 4 | 分片-隔离-集成 | 并行写者的冲突面如何结构性消除？ | [Agentic MapReduce](https://devin.ai/blog/agentic-map-reduce)、[NP-Bench](https://arxiv.org/abs/2610.07261)、[AIDev-pop](https://arxiv.org/abs/2607.04697)、[CodeCRDT](https://arxiv.org/abs/2510.18893)、[worktrees](https://code.claude.com/docs/en/worktrees) |
| 5 | 生成-验证分离与错误传播 | 谁验证？验证权放哪？错误怎么不扩散？ | [OpenHands Software Factory](https://docs.openhands.dev/openhands/usage/use-cases/software-factory)、[MAST](https://arxiv.org/abs/2503.13657)、[2408.00989](https://arxiv.org/abs/2408.00989)、[From Spark to Fire](https://arxiv.org/abs/2603.04474) |
| 6 | 跨会话状态与记忆外化 | 会话死了怎么接手？记忆怎么沉淀复用？ | [Anthropic long-running harness](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)、[MemGPT](https://arxiv.org/abs/2310.08560)、[Mem0](https://arxiv.org/abs/2504.19413)、[ACE](https://arxiv.org/abs/2510.04618)、[Context Rot](https://www.trychroma.com/research/context-rot) |
| 7 | 评测驱动研究环 | 假设-实验-测评-迭代的多 agent 形态是什么？ | [AI co-scientist](https://arxiv.org/abs/2502.18864)、[CycleResearcher](https://arxiv.org/abs/2411.00816)、[AI Scientist-v2](https://arxiv.org/abs/2504.08066)、[Coscientist (Nature)](https://www.nature.com/articles/s41586-023-06792-0)、[Agent Laboratory](https://arxiv.org/abs/2501.04227) |
| 8 | 采样聚合与辩论基线 | 最便宜的多 agent 形态收益多大？辩论值不值？ | [Self-Consistency](https://arxiv.org/abs/2203.11171)、[MoA](https://arxiv.org/abs/2406.04692)、[倒U律](https://arxiv.org/abs/2403.02419)、[Statistical Scouting](https://arxiv.org/abs/2605.09618)、[MAD 基准](https://arxiv.org/abs/2311.17371) |

时间覆盖：以 2024–2026 年进展为主（scaling science、NP-Bench、AIDev-pop、BenchAgent、SIMAS、Silo-Bench、AutoSaddler、ACE、long-running harness 等均为 2025–2026 成果），经典奠基（MetaGPT、ChatDev、CAMEL、Self-Consistency、Lost in the Middle、MemGPT、FunSearch、MacNet）全部覆盖。

### 2.2 双模型分工与三层核实链

**调研→换模型核实→裁决抽查**，三层独立视角，任何一层都可以推翻上一层：

1. **第一层·主调研（双模型并行）**：GLM-5.3-Flash 与 MiniMax-M3.1-Flash 各自独立完成八方向调研，产出两份机制谱系（本报告 §3 的两份原始输入）。两份谱系按同一 schema 组织：机制 / how / evidence / limitations。
2. **第二层·交叉核实（换模型评审）**：GLM 草案交 MiniMax 评审、MiniMax 草案交 GLM 评审，逐策略挑错。实际抓出的典型错误：
   - 文件锁出处误挂——MiniMax 评审核实其实出自 [Cline Kanban](https://docs.cline.bot/usage/kanban) 而非 agent-teams 页；
   - [building-effective-agents](https://www.anthropic.com/engineering/building-effective-agents) 页**并无** effort scaling 数字分档（1 agent×3–10 调用等），该先验被降级为待校准；
   - [FastContext](https://arxiv.org/abs/2606.14066) v4 已撤稿（product IP issues、无 PDF），56.2%/46.5% 两数不可得，按撤稿处置；
   - 编排恢复语义被包装为『(prompt, schema, 执行设置) 三元组哈希记账』——裁决核实厂商文档实际语义是『缓存已存结果 + 按启动序重放至首个 prompt 分歧』，属自定义包装、语义等价但须按厂商语义实现。
3. **第三层·独立裁决（Step-5 Preview 抽查）**：裁决者对 9 个策略逐条打开 evidence 链接核对数字（见 §5），再裁两模型评审之间的分歧。典型裁决：
   - 2408.00989 数字之争：MiniMax 评审主张更正为 23.6/46.4/49.8，裁决者独立 curl 核实后**驳回**——原文摘要与 prose 均只有 5.5/10.5/23.7/96.4（MiniMax 的数字实为其 SVG 路径噪声），但采纳其出处更正（2603.04474→2408.00989）；
   - [Manus Wide Research](https://manus.im/blog/manus-wide-research-solve-context-problem) 的『量化切点』被降格为定性描述（原文为『第 8–9 项上下文吃紧、第 9 项起编造』的定性叙述，无 1–5/6–8/≥9 的硬分档表），汇合硬界作为工程设计可辩护但改述。

### 2.3 核实链的战果（为什么三层必要）

本次调研共修正：3 处硬伤（S3 误挂 [2501.06322](https://arxiv.org/abs/2501.06322)——实为综述非 Anthropic 系统 arXiv 版；S4 的 [agentic-map-reduce](https://devin.ai/blog/agentic-map-reduce) 链接 404 失效；S6 的 sleep-time 倍数不在[所引页面](https://www.letta.com/blog/sleep-time-compute)上）；6 处引用更正（NP-Bench/AIDev-pop/CodeCRDT/MAST/2408.00989/AI co-scientist 的编号或出处对调）；以及若干数字口径纠正（AIDev-pop 的 0.5% 是共活对中跨 agent 对占比、4.3% 才是仓库口径）。**全部来源的核实状态逐条记录于 §8 附录。**

---

## 3. 机制谱系全景

按主题归类的机制清单（合并 GLM 与 MiniMax 两份谱系、去重后 20 个主题）。每条：机制要点 → 来源链接 → 局限。

### 3.1 架构选择门控与多 agent 扩展律

**要点**：把『要不要多 agent』做成编排前的显式决策而非默认动作。定量依据：[Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296) 在 260 配置（5 架构 × 6 基准 × 3 模型族，标准化工具/提示/算力）上拟合可预测模型，交叉验证 R²=0.373（能力指标 0.413），87% 留出配置选对最优架构；相对单 agent 变化 +80.8%（可分解金融推理）到 −70.0%（序列规划）；三条规律——能力饱和（单 agent 越强协调收益越递减）、工具密集任务更吃多 agent 开销、无集中式验证的架构传播更多错误。规模维度：[MacNet](https://arxiv.org/abs/2406.07155) 性能随 agent 数 logistic 增长、不规则拓扑优于规则拓扑、可支撑上千 agent；[SIMAS](https://arxiv.org/abs/2606.00655) 证明性能不随 agent 数单调，受协同增益 vs 协调开销权衡支配且要求足够强基座。门控原则原文见 [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)：『能不建 agentic 系统就不建，只在可证明改善结果时加复杂度』。

**局限**：R²=0.373 预测力中等且依赖其基准分布，不可直接外推到产线任务；[MAST](https://arxiv.org/abs/2503.13657) 实测 41%–86.7% 失败率——选对架构不保证跑通；[BenchAgent](https://arxiv.org/abs/2606.05670)（GPT-4.1、十基准、每配置 3302 例×3 轮）六种多 agent 工作流仅 EvoAgent 稳定胜出（79.70% vs 76.65%），真实效应量可能仅个位数 pp；miscoordination/conflict/collusion 三类结构性风险非技术门控可全覆盖（[Multi-Agent Risks from Advanced AI](https://arxiv.org/abs/2502.14143)）。

### 3.2 编排者-执行者双账本层级（星形）

**要点**：lead 垄断分解/分派/汇合/重规划/最终判断，worker 间无横向协议。[Anthropic 多 agent 研究系统](https://www.anthropic.com/research/multi-agent-research-system)：Opus 4 lead + Sonnet 4 workers 比单 agent Opus 4 高 90.2%（内部 research eval）、并行拉起 3–5 个 subagent、复杂查询研究时间最多省 90%、成本约聊天的 15× token、token 用量单独解释 BrowseComp 80% 性能方差；subagent 产物直写文件系统只回传轻引用。[Magentic-One](https://arxiv.org/abs/2411.04468)：task ledger（已核实/待查/待推导/猜测/计划五栏）+ progress ledger（进展/分派/卡死计数）双账本，卡死超阈值→反思→修订计划→重开内层循环；GAIA 38%、WebArena 32.8%、AssistantBench 27.7%，依赖出错后重规划。[Can Small Agents Collaborate](https://arxiv.org/abs/2601.11327)：整体性能主要由 orchestrator 容量驱动、子 agent 开推理收益有限甚至为负——lead 必须用最强模型。

**局限**：90.2% 出自内部 research eval，同页 coding caveat 明言『多数编码任务可并行部分少于研究，且 agent 尚不擅长实时协调委派』——星形的主战场恰在证据点名的弱项区；15× token 且不设预算的更强可能只是更贵；[manager/child 三缺陷](https://cognition.com/blog/multi-agents-working)（过度规定任务、误以为共享状态、跨 agent 回传默认不发生）；[Manus Wide Research](https://manus.im/blog/manus-wide-research-solve-context-problem) 定性描述单上下文第 9 项起进入『格式完美但事实错误』的编造模式——lead 汇合需要硬界。

### 3.3 单写者 + 多智能（single-threaded writes, multiple intelligences）

**要点**：写路径唯一，其他 agent 只贡献智能不产动作。三个已部署分支：干净上下文评审（评审 agent 事前零共享上下文，依据 [Context Rot](https://www.trychroma.com/research/context-rot)；Devin Review 每 PR 约 2 bug、58% 严重）；smart friend（弱主模型把强模型当工具调用，共享主模型完整上下文的 80/20 分叉）；只读侦察 subagent（搜索/调查类，历来最安全）。生产形态：[OpenHands Software Factory](https://docs.openhands.dev/openhands/usage/use-cases/software-factory) 四段式 triage→developer→reviewer→watchdog，reviewer 检出精确 PR head 防移花接木、最小权限（Contents 只读）、watchdog 纯确定性合入。这是对 [Don't Build Multi-Agents](https://cognition.com/blog/dont-build-multi-agents)（两条原则：共享上下文与完整轨迹；动作携带隐含决策）立场的收窄修正而非推翻——parallel-writer swarm 与无结构谈判式 agent 群的警告仍成立。

**局限**：smart friend 在主模型太弱时失效（Cognition 以 SWE 1.5 为例）；评审回传必须由主 agent 用更宽上下文二次过滤否则陷入修复循环；写路径卡死并行度上限；对超大并行写盘任务不适用（需转 3.10 的分片拓扑）。

### 3.4 代码化编排（workflow-as-code）与声明式图运行时

**要点**：拓扑写在确定性脚本里而非 prompt 里。[Claude Code dynamic workflows](https://code.claude.com/docs/en/workflows)：脚本用 agent()/parallel()/pipeline()/phase() 表达分叉汇合、无文件系统/shell 访问权；硬限写死 runtime——默认 16 并发（可 1–256）、单次 parallel/pipeline ≤4096、每 run ≤1000 agent、禁 import()/Date.now()/Math.random()（保重放确定性）、运行中无用户输入；恢复语义为缓存已存结果+按 agent 启动序重放至首个 prompt 分歧（注意：厂商文档无『哈希记账』表述，该词是调研中的自定义包装）；stall 自动重启 ≤5 次；usage-limit 挂起等重置。[Devin dynamic workflows](https://docs.devin.ai/work-with-devin/dynamic-workflows)：每 agent 独立 VM、跨 agent 传代码走 git branch + 结构化输出、失败由脚本决定跳过/默认/重试。框架谱系：[LangGraph](https://github.com/langchain-ai/langgraph)（Pregel 启发，Send/Command/BaseCheckpointSaver 三原语，代码行号已核实 types.py:738/:833、checkpoint base/__init__.py:199）；[AutoGen](https://arxiv.org/abs/2308.08155) conversation programming 是奠基（[仓库已归档](https://github.com/microsoft/autogen)）；[Microsoft Agent Framework](https://github.com/microsoft/agent-framework) 提供 sequential/concurrent/handoff/group 四图模式 + checkpointing + OpenTelemetry；[OpenAI Agents SDK](https://github.com/openai/openai-agents-python) 用 agents/handoffs/guardrails 三原语（Handoff input_filter 裁剪交接上下文）；[Google ADK](https://github.com/google/adk-python) 确定性 workflow agents（Sequential/Parallel/LoopAgent）与 LLM 驱动 AutoFlow 并存；[CrewAI](https://github.com/crewAIInc/crewAI) Flows 用 @start/@listen/@router + Pydantic 结构化状态；[LlamaAgents](https://github.com/run-llama/llama-agents) 步骤即发事件的 async Python 函数、无 DSL。

**局限**：运行中无用户输入，错误规划被确定性放大；prompt 一改下游全重跑的代价；框架生态换代快（AutoGen 归档→MAF、Swarm→Agents SDK、[langgraph-supervisor](https://github.com/langchain-ai/langgraph-supervisor) 官方弃用改推荐工具式 handoff）；[Anthropic 自警](https://www.anthropic.com/engineering/building-effective-agents)：框架抽象层可能遮蔽底层 prompt 使调试变难。

### 3.5 Hub-Spoke 运行时解耦（控制面/执行面分离）

**要点**：hub 常驻守护进程只管会话状态、事件路由、审批与调度（**明确不跑 agent loop**）；spoke 工作进程跑 loop、调工具、流式回传；client（CLI/IDE）平级注册自身能力（VS Code 注册 open-file/reveal-diff，CLI 注册 shell/run-tests），hub 按能力路由。关键性质：client 断开后 spoke 继续执行、其他 client 可中途接管——无人值守跑批前提（[Cline hub-spoke](https://docs.cline.bot/sdk/architecture/hub-spoke)）。[AG2](https://github.com/ag2ai/ag2) v1.0 同构：Hub 拥有 registry/write-ahead log/audit trail，agent 走四类类型化信道（conversation/consulting/discussion/workflow+声明式 TransitionGraph）。[AgentScope](https://github.com/agentscope-ai/agentscope) 走 actor 分布式 + 统一事件总线（架构论文 [2508.16279](https://arxiv.org/abs/2508.16279)），SOP 与 TeamPipeline 为一级特性。

**局限**：hub 是单点，需 WAL/audit 补偿（AG2 自述但无第三方验证）；三者均为新产品/新重构，大规模生产证据少；Cline 官方自限 teams 适用边界——任务可分解、需不同专长、跨 session 恢复、需持久委派记录，简单场景单 agent 更高效（[Multi-Agent Teams](https://docs.cline.bot/sdk/guides/multi-agent-teams)）。

### 3.6 文件黑板与结构化产物通信

**要点**：通信介质不是自由聊天而是结构化产物。奠基：[MetaGPT](https://arxiv.org/abs/2308.00352) 把 SOP 编码进 prompt 序列、装配线分工、结构化文档传递抑制 cascading hallucination（ICLR 2024）；[ChatDev](https://arxiv.org/abs/2307.07924) 用 chat chain 约定『沟通什么』、communicative dehallucination 约定『怎么沟通』（ACL 2024）。现代形态：[Anthropic](https://www.anthropic.com/research/multi-agent-research-system) artifact 直写外部存储只回传轻引用；[Claude Code sub-agents](https://code.claude.com/docs/en/sub-agents) 初始上下文白名单（system prompt + 委派消息 + CLAUDE.md + git 快照，description 合并 >15000 token 告警，完成后返回 agent ID 可 SendMessage 带完整历史续跑）；[Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) 文件系统是终极上下文：压缩可还原（丢内容留 URL/沙箱路径）、todo.md 反复重写对抗 [lost-in-the-middle](https://arxiv.org/abs/2307.03172) 的 U 形偏置、失败轨迹只追加不删（删=抹证据）。

**局限**：[Cognition 反证](https://cognition.com/blog/dont-build-multi-agents)：黑板只解决介质不解决决策一致性——两个并行子 agent 各自写文件照样产生隐含决策冲突（Flappy Bird 反例），必须与写权约束配套；长上下文召回随距离衰减，堆材料本身不是解；结构化产物不能自动防错——[MAST](https://arxiv.org/abs/2503.13657) 最高频失败仍是 FM-1.3 步骤重复（15.7%）与 FM-1.1 不遵守任务需求（11.8%）。

### 3.7 跨会话状态桥接（无人值守续跑）

**要点**：[Anthropic long-running harness](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) 的结论是『compaction isn't sufficient』，跨会话靠文件产物：initializer 产出 init.sh（环境自举+冒烟）、claude-progress.txt（叙事进度）、初始 git 提交、全量 feature 清单 JSON（每项带 passes 位、初值全 failing）；每次会话：读 git log+进度文件恢复→跑 init.sh 冒烟确认没接手坏状态→挑最高优先级 failing feature 推进→每 feature 一 git 提交（提交即检查点）；agent 只许翻 passes 位、禁改测试（JSON 比 Markdown 不易被模型误改）。原文自陈失败模式：『后来的 agent 看到有进展就宣布完工』。配套：[Cline teams](https://docs.cline.bot/sdk/guides/multi-agent-teams) 状态持久化 ~/.cline/data/db/teams.db 随 session 恢复；[sub-agents](https://code.claude.com/docs/en/sub-agents) 的 agent ID + SendMessage 带历史续跑、maxTurns 到顶标 partial 可续。

**局限**：前提是任务可预枚举 feature 清单，探索型不适用；[agent teams 文档](https://code.claude.com/docs/en/agent-teams)自认任务状态可能滞后、无法恢复含运行中队友的会话；passes 位可能被 agent 绕过或误改，需钩子+外部核验方（watchdog）做最后防线；进度文件会膨胀，压缩须守『可还原』底线。

### 3.8 分层记忆外化 + sleep-time compute

**要点**：把『上下文放不下』部分转化为记忆工程。[MemGPT](https://arxiv.org/abs/2310.08560)：窗口=内存、外部存储=磁盘、interrupts 换页；[Letta sleep-time](https://www.letta.com/blog/sleep-time-compute)：记忆编辑职责剥离给后台 agent（[论文 2504.13171](https://arxiv.org/abs/2504.13171)：同精度省约 5× test-time 计算、摊销再降 2.5×、固定预算精度 +13%/18%——**注意：裁决核实这三个数字在 arXiv 论文页而非 Letta 博客页**，且硬前提是有状态跨交互场景）；[Mem0](https://arxiv.org/abs/2504.19413)：抽取-整合-检索+图变体，LOCOMO p95 延迟 −91%、token −90%+、比 OpenAI 记忆方案 +26%、图变体再 +2%；[MIRIX](https://arxiv.org/abs/2507.07957) 六类记忆：ScreenshotVQA +35%、存储 −99.9%、LOCOMO 85.4%；[ACE](https://arxiv.org/abs/2510.04618)：playbook 式『生成-反思-策展』增量更新，防 context collapse 与 brevity bias，agents +10.6%、AppWorld 上小模型追平生产级 agent；[Voyager](https://arxiv.org/abs/2305.16291) 可执行技能库：独特物品 3.3×、里程碑最高 15.3×。

**局限**：sleep-time 在 stateless 场景收益归零；[Context Rot](https://www.trychroma.com/research/context-rot)（18 模型控制实验）表明语义型检索退化远重于词汇匹配、干扰项形态显著影响表现；[Lost in the Middle](https://arxiv.org/abs/2307.03172) U 形偏置对外部化材料同样成立；[2604.18805](https://arxiv.org/abs/2604.18805) 提醒 scaffold 侧只解释 1.5% 方差（基座 41.4%）——记忆/上下文工程的天花板由基座决定。

### 3.9 一任务一环境（worktree / VM / 容器物理隔离）

**要点**：把冲突面从『协调』降为『合并』。[Claude Code worktrees](https://code.claude.com/docs/en/worktrees)：.claude/worktrees/<name>/ 独立 checkout + worktree-<name> 分支，.worktreeinclude 携带 gitignored 配置，子代理 frontmatter isolation: worktree，/batch 拆 5–30 个 worktree 隔离 subagent；[Devin managed](https://cognition.ai/blog/devin-can-now-manage-devins) 每子会话一台完整 VM，独立跑测试验证后才回报；[Cloud sessions](https://www.anthropic.com/news/claude-code-on-the-web)（2026-09 GA）整条会话托管云端隔离沙箱、完成后自动开 PR；[OpenHands](https://docs.openhands.dev/openhands/usage/use-cases/software-factory) 每条 automation 独立 Docker 工作区 + 各自 GitHub token 最小权限。

**局限**：隔离只消文本冲突不消语义冲突——[AIDev-pop](https://arxiv.org/abs/2607.04697)（33,596 agent PR / 2,807 仓库、747 组三方 merge 实跑）：跨 agent 文本冲突率 41.7% vs 同 agent 19.8%、冲突文件 84.4% 为源码、约 42% 结构性；**重要 caveat：跨 agent 共活对仅占共活对的 0.5%、占仓库 4.3%（122/2807），勿高估跨 agent 冲突面**；每环境有重建与合并成本。

### 3.10 Agentic MapReduce 与依赖图调度

**要点**：分片→并行→受控合并三段式，分区必须确定化：planner 只做一次推理、产出确定性 selector（tree-sitter 查询/编译器符号查询/import-call 图遍历/API schema 比对/词法模式），无模型跑遍全仓库（[Agentic MapReduce](https://devin.ai/blog/agentic-map-reduce)；**裁决核实：该链接已 404，机制由 NP-Bench 与 Devin dynamic workflows 双源支撑**）；selector 是可读、可测、可版本控制的产物，召回率=selector 质量。最强实证：[NP-Bench](https://arxiv.org/abs/2610.07261)——按声明作用域划不相交工作集+沿 producer→consumer 依赖图排序合并，干净集成 1/9→9/9、merge 冲突 13→0，**且收益随模型变强不缩水（来自任务分配方式而非模型推理）**；三臂设计（no-coordination/reactive/proactive）证明收益来自 proactive planning。认领与调度：[agent teams](https://code.claude.com/docs/en/agent-teams) 共享任务表+文件锁+mailbox；[Cline Kanban](https://docs.cline.bot/usage/kanban) 一卡一 worktree、依赖链自动启动（文件锁出处在此）。备选介质：[CodeCRDT](https://arxiv.org/abs/2510.18893) 观测驱动共享态，600 试验 100% 收敛零 merge 失败，但最高 39.4% 减速、5–10% 语义冲突率。

**局限**：selector 对反射/DI/动态注册等动态绑定边系统性漏检（枚举覆盖≠必要覆盖）；只适配 map 形任务；[Silo-Bench](https://arxiv.org/abs/2603.01045)（54 配置、1,620 实验）发现 Communication-Reasoning Gap——agent 能自发协调并交换信息、『却系统性无法把分布式状态整合成正确答案』，且协调开销随规模复利直至吃光并行收益——单纯加 agent 数绕不开上下文限制；[agent teams 自认](https://code.claude.com/docs/en/agent-teams)无法恢复含运行中队友的会话。

### 3.11 生成-验证角色分离（评审 / critic / watchdog）

**要点**：生成者与验证者强制分离、上下文零共享。（a）[冻结上下文评审](https://cognition.com/blog/multi-agents-working)：评审 agent 从零读 diff，主 agent 须用更宽上下文二次过滤否则修复循环；（b）[OpenHands Critic](https://docs.openhands.dev/openhands/usage/agent-canvas/critic)：回合末输出成功概率分+问题类别，默认阈值 0.6、≤3 轮退回封顶，第三方 ACP agent 不走此路径；（c）[确定性 watchdog](https://docs.openhands.dev/openhands/usage/use-cases/software-factory)：纯脚本不启任何 agent，仅在验收状态+CI 全绿时合并。理论依据：[LLM 无外部反馈的自纠有时反而更差](https://arxiv.org/abs/2310.01798)——验证必须真正外置；[Anthropic 分类学](https://www.anthropic.com/engineering/building-effective-agents)称 evaluator-optimizer 模式，前提=有明确评估标准。

**局限**：Critic 阈值 0.6/3 轮是默认超参无普适依据；评审噪声制造修复循环是最高频失败模式；[2604.18805](https://arxiv.org/abs/2604.18805)：结果型评测检测不到 68% 轨迹的证据忽略、仅 26% 反驳驱动信念修正——外置评审修不了深层推理缺失，只能兜工程性缺陷。

### 3.12 确定性钩子门控与 /goal

**要点**：把质量门从模型自觉搬到运行时确定性。[OpenHands hooks](https://docs.openhands.dev/openhands/usage/customization/hooks)：按 PreToolUse/PostToolUse/Stop 等注册 shell 脚本，exit 0 放行 / 2 阻断（可输出 deny+reason）/ 其他记错继续；Stop 钩子强制不许结束直到 lint/测试过；async 钩子后台跑不能当门；格式与 Claude Code hooks 兼容。[Claude Code /goal](https://code.claude.com/docs/en/goal)：会话级完成条件环，小而快的评估模型三态判定（未达成/已达成/不可能达成），连续多轮不用工具判无进展即停，四类致命错误清 goal。[agent teams](https://code.claude.com/docs/en/agent-teams) 的 TaskCompleted/TeammateIdle hook 退出码 2 打回。

**局限**：钩子只从工作目录加载不向上搜索；评估模型质量成为新单点（弱评估器→假达成或死循环）；hook 脚本自身无测试、写错会静默放行或误拦——门控代码需与业务代码同库版本管理。

### 3.13 错误传播治理（集中验证 + Challenger/Inspector + 消息谱系）

**要点**：三层治理。（a）架构层：[scaling science](https://arxiv.org/abs/2512.08296) 实证无集中式验证的架构传播更多错误——验证权收中央；（b）角色层：[On the Resilience](https://arxiv.org/abs/2408.00989)（AutoTransform/AutoInject 故障注入，4 任务 6 结构）层级 A→(B↔C) 性能降幅最小 5.5%（对照顺序式 10.5%、全连接 23.7%），Challenger+Inspector 最高挽回 96.4% 故障 agent 错误；（c）消息层：[From Spark to Fire](https://arxiv.org/abs/2603.04474)——单个原子错误种子即可扩散成系统级假共识（cascade amplification/topological sensitivity/consensus inertia 三类脆弱性），genealogy-graph 插件 ≥89% 运行阻止最终感染。干预定量：[MAST](https://arxiv.org/abs/2503.13657) 仅改角色规范 ChatDev +9.4%、加任务目标验证步 +15.6%。级联细节：[Hallucination Cascade](https://arxiv.org/abs/2606.07937)——3-agent 链归一化幻觉分 0.422→0.272（净衰减）但事实准确率 0.789→0.769，压幻觉与保事实有张力。

**局限**：Challenger/Inspector 是纯额外 token 开销；genealogy ≥89% 出自单一论文模拟设置；MAST 的 LLM-as-judge 自动标注（accuracy 0.94/recall 0.77/precision 0.833/κ=0.77，**正文数据、摘要未含**）说明失败检测本身不完美；[2502.14143](https://arxiv.org/abs/2502.14143) 的七类风险因子与 collusion 不是技术门控能全覆盖。

### 3.14 采样-聚合扩展（投票 / MoA / 倒 U 律）

**要点**：最便宜、收益最确定的多 agent 形态：无角色无通信，独立采样后聚合。[Self-Consistency](https://arxiv.org/abs/2203.11171)：GSM8K +17.9%、SVAMP +11.0%、AQuA +12.2%、StrategyQA +6.4%；[MoA](https://arxiv.org/abs/2406.04692)：纯开源 LLM 分层聚合 AlpacaEval 2.0 65.1% vs GPT-4 Omni 57.5%——弱模型协作超单强模型的直接证据；[More Agents](https://arxiv.org/abs/2402.05120)：性能随实例数提升、与复杂方法正交、幅度与任务难度相关。关键扩展律：[Are More LLM Calls All You Need?](https://arxiv.org/abs/2403.02419)——Vote/Filter-Vote 性能随调用数先升后降（更多调用提升简单题、拉低难题），且可从少量样本解析预测最优调用数——**并行度是被求解的量，不是越大越好**。

**局限**：廉价停机信号基本失效——[Statistical Scouting](https://arxiv.org/abs/2605.09618)（每例 960 token 匹配预算）：投票已解释辩论的大部分收益，oracle 逐例路由 +14pp 头部但投票熵只能预测『辩论安全』非『辩论有用』、66% 有益辩论恰发生在投票一致但错误时、自批评探针与『辩论有益』互信息为零；[Not All Flips](https://arxiv.org/abs/2606.00820)：37% 答案翻转无同伴信息也会发生、扣除后 29.3% 采纳同伴含引入新错误；[BenchAgent](https://arxiv.org/abs/2606.05670)：ChatEval 类 4.34× token 仍总体落后。

### 3.15 结构化辩论与裁判（反方证据最密集的一族）

**要点**：独立作答→互读批评→逐轮修订。[Du et al.](https://arxiv.org/abs/2305.14325)（默认 3 agent 2 轮、无裁判、与 zero-shot CoT 正交）；[ChatEval](https://arxiv.org/abs/2308.07201)（同骨干不同 persona 评审团，角色多样性是收益来源——全员同角色退化 53.8 vs 60.0）；[MAD](https://arxiv.org/abs/2305.19118)（裁判+tit-for-tat 治 Degeneration-of-Thought）；谱系上溯 [CAMEL](https://arxiv.org/abs/2303.17760) role-playing。裁判可训练：[2402.06782](https://arxiv.org/abs/2402.06782) 模型裁判准确率 48%→76%、人类裁判 60%→88%，且说服力追踪真相。研究系统变体：[AI co-scientist](https://arxiv.org/abs/2502.18864) 的 Elo 锦标赛成对排序。

**局限**：[Should we be going MAD?](https://arxiv.org/abs/2311.17371)——现有形式辩论不能可靠超过 self-consistency、对超参敏感难优化（且未做同 token 预算对齐）；[Rethinking the Bounds](https://arxiv.org/abs/2402.18272)：强 prompt 单 agent ≈ 最好的讨论方法，讨论只在无 demonstration 时占优；[AgentVerse](https://arxiv.org/abs/2308.10848)：GPT-3.5 下 Group 三任务中两任务输给 Solo、约 10% 错误源自从众（GPT-4 无此现象）；[BenchAgent](https://arxiv.org/abs/2606.05670)：LLM-Debate 1.39× token 总体落后。

### 3.16 类型化信道与通信图剪枝

**要点**：把通信当一等成本治理。[AG2](https://github.com/ag2ai/ag2) 四类类型化信道替代『零通信』禁令；[AgentPrune](https://arxiv.org/abs/2410.02506) 首次定义多 agent 通信冗余问题，对消息传递图 one-shot 剪枝、即插即用——同性能任务成本 $43.7→$5.6、接入现有框架 token −28.1%~72.8%、对两类对抗攻击 +3.5%~10.8%（剪枝同时是安全收益）；[Optima](https://arxiv.org/abs/2410.08115) generate-rank-select-train：Llama 3 8B 最高 2.8× 性能、token <10%。KV-cache 视角来自 [Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)：缓存命中率是生产 agent 首要指标（输入:输出≈100:1，缓存 $0.30 vs 未缓存 $3/MTok 差一个数量级），前缀稳定（禁秒级时间戳）、上下文只追加、显式 cache breakpoint、工具 mask-don't-remove。

**局限**：[Silo-Bench](https://arxiv.org/abs/2603.01045) 反证——就算通信畅通高效，『分布式状态→正确答案』的整合失败仍在推理侧，剪枝治不了；Optima 结果是特定骨干训练后所得，不外推前沿模型；logit 掩码/prefill 非所有供应商可支持（不可用时退化为按阶段固定工具集）。

### 3.17 自动 agent 架构搜索

**要点**：把『协作结构本身』变成搜索空间。[ADAS](https://arxiv.org/abs/2408.08435)：meta agent 在增长的 archive 上迭代编程发明全新 agent、跨域跨模型迁移；[AFlow](https://arxiv.org/abs/2410.10762)：MCTS over 代码 workflow，六基准平均 +5.7%、小模型以 GPT-4o 4.55% 推理成本反超；[MaAS](https://arxiv.org/abs/2502.04180)：agentic supernet 按难度采样架构分布，推理成本仅手工/自动化系统的 $6~45%、性能反超 0.54%~11.82%；[GPTSwarm](https://arxiv.org/abs/2402.16823)（agent 即可优化计算图）、[DyLAN](https://arxiv.org/abs/2310.02170)（Agent Importance Score 动态组队）、[FlowReasoner](https://arxiv.org/abs/2504.15257)（query-level meta-agent 超 o1-mini 达 10.52%）。

**局限**：数字多来自论文自建基准、易过拟合任务分布；搜索本身耗算力；MAST 指出瓶颈在系统设计与任务验证而非拓扑精调——搜索空间选错层就白搜；这些方法优化的以单 agent 工作流为主，跨 agent 并行写的协调问题不在搜索空间内（正交）；MaAS 的对照是手工/自动化系统而非单 agent 基线，不可当产线预期。

### 3.18 评估器在环的进化式程序搜索

**要点**：生成-验证分离的极限形式：LLM 只当变异算子，正确性完全交确定性评估器。[FunSearch](https://deepmind.google/discover/blog/funsearch-making-new-discoveries-in-mathematical-sciences-using-large-language-models/)：cap set 20 年最大增量、evaluator 『守住幻觉与错误想法』；[AlphaEvolve](https://arxiv.org/abs/2506.13131)：4×4 复矩阵乘 48 次标量乘（Strassen 后 56 年首次改进）、数据中心调度、加速支撑自身的 LLM 训练；[OpenEvolve](https://github.com/codelion/openevolve)：开源化（MAP-Elites、默认 5 孤岛、artifact 侧信道、级联评估）；[Darwin Gödel Machine](https://arxiv.org/abs/2505.22954)：同原理改 agent 自身 scaffold，自动发现更好的编辑工具/长上下文管理/同伴评审机制；[MLE-bench + AIRA-Dojo](https://arxiv.org/abs/2507.02554)：Kaggle 奖牌率 39.6%→47.7%、1,000 agent 并行 120 小时。

**局限**：只适用评估器廉价、确定、防作弊的域；评估器成为瓶颈与攻击面（reward hacking 未被系统排查——METR 自注）；meta 循环本身是单线程采样——『多 agent 性』来自孤岛与并行 rollout 而非 agent 间对话，勿误读为对话式协作有效的证据。

### 3.19 评审驱动的研究迭代环（任务 B 的完整形态）

**要点**：共享假设池 + 角色分工 + 生成-评审共演化。[AI co-scientist](https://arxiv.org/abs/2502.18864)：Supervisor + 六角色（Generation/Reflection/Ranking/Evolution/Proximity/Meta-review）+ Elo 成对锦标赛；三落地案例（AML 药物重定位、肝纤维化、AMR 基因转移）。[CycleResearcher](https://arxiv.org/abs/2411.00816)：CycleReviewer 预测论文分数 MAE 比单个人类评审低 26.89%、生成论文模拟评审 5.36（人类 preprint 5.24/accepted 5.69）——评审器变强反哺生成器。[AI Scientist-v2](https://arxiv.org/abs/2504.08066)：experiment manager + 渐进式树搜索 + VLM 反馈，首篇过同行评审的全 AI 论文（注意：模拟评审非真人）。奠基：[Coscientist](https://www.nature.com/articles/s41586-023-06792-0) Planner 四命令动作空间（GOOGLE/PYTHON/DOCUMENTATION/EXPERIMENT）驱动自动化实验；[Robin](https://arxiv.org/abs/2505.13400) 文献 agent+数据分析 agent 闭环（ripasudil→ABCA1 机制实证）；[The AI Scientist](https://arxiv.org/abs/2408.06292) <$15/篇。[Agent Laboratory](https://arxiv.org/abs/2501.04227)：全自主省 84% 成本，但人类每阶段反馈显著提升质量——自主度-质量权衡实测。

**局限**：最强反方 [AI scientists produce results without reasoning scientifically](https://arxiv.org/abs/2604.18805)（8 领域、25,000+ 次运行）：基座解释 41.4% 方差而 scaffold 仅 1.5%；68% 轨迹证据被忽略、仅 26% 反驳驱动信念修正；结果型评测检测不到这些失效、仅靠 scaffold 工程无法修复——研究环的增益大头可能是『更多采样+更贵』而非『更好的科学推理』；假设质量上限由生成模型的假设空间决定，多 agent 分工不改变这个上限。

### 3.20 沙箱评测基建与 harness 自优化闭环

**要点**：任务 B 的地面段。[Terminal-Bench](https://github.com/laude-institute/terminal-bench)：任务=英文指令+验证测试脚本+oracle 解三要素（tb run CLI、经 [Harbor](https://github.com/harbor-framework/harbor) 跑 2.0；Harbor 统一容器化 provider、--n-concurrent 控并发、可产 RL rollouts、直评真实 agent）；[AutoGenBench](https://github.com/microsoft/autogen) 内置重复与隔离控制；AIRA-Dojo 支撑千 agent 并行（见 [2507.02554](https://arxiv.org/abs/2507.02554)）。harness 自优化：[AutoSaddler](https://arxiv.org/abs/2608.23041) 把 harness 改进形式化为离线学习——失败轨迹诊断→结构化补丁（把 harness 当代码）→验证式更新选择，GAIA2/SWE-Bench Pro/TB2.0 +9.0/+9.6/+10.0pp；三消融：deep debugging>浅反思、targeted modification>无约束编辑、generalization-aware selection>轨迹特修。前沿参照：[MiniMax-M2](https://arxiv.org/abs/2605.26494) 的 Forge 支持自演化（自主调试训练 run 并修改自身 scaffold，承担 RL 团队 30–50% 日常迭代）；[METR](https://arxiv.org/abs/2503.14499) 时间视界约每 7 个月翻倍（SWE-bench Verified 约 70 天）——静态 harness 快速过时，这正是自优化要进环的原因。

**局限**：AutoSaddler 是 2026-08 预印本且其基线是它自己的 harness、数字不外推；[CORE-Bench](https://arxiv.org/abs/2409.11363) 最难档最好 agent 仅 21% 复现准确率；[MLAgentBench](https://arxiv.org/abs/2310.03302) 最强 agent 平均 37.5%、训练截止后新建的 Kaggle 挑战低至 0%（污染与泛化威胁评测效度）；[RE-Bench](https://arxiv.org/abs/2411.15114) 时间预算反转：2h 预算 AI 为人类 4×、32h 人类反超 2×——无人值守长跑不会自动赢，harness 要按预算选策略。

---

## 4. 候选策略清单

九个策略，按裁决排名从高到低排列。每个策略给出：机制 / 改进价值假设 / 证据 / 成本 / 风险 / 裁决与排名。实验设计（testDesign）统一整理于 §7。

### S8 采样聚合与倒U停机闸（排名 1 · recommend · 两者皆可）

**机制**：最低成本、收益最确定的多 agent 形态，同时是全厂强制基线——任何更复杂协作协议必须先赢过同预算采样-投票，否则判无增量。拓扑=零通信平坦并行：确定性分派器（纯代码）以 K 个不同假设种子/视角切片把同一优化问题复制给 N 个独立 proposer-verifier 对，多样性靠种子与切片而非讨论；每对在独立环境（worktree/容器，一任务一环境）内跑完『假设→改动→确定性评测』微循环，输出结构化候选。聚合器（代码）按 dev_score 排序，并列时 1 个 consolidator 单次调用去重，禁止语义合并、多案允许并列交付。三层验证：(1) 候选必过确定性评测器；(2) 冻结 holdout + 补丁语义抽检防过拟合判分器；(3) 倒 U 停机闸=解析控制器——≤10% 预算校准采样拟合边际增益曲线，预测边际 <ε 或连续 5 候选不超当前最优即停；停机信号只允许确定性 eval 边际增益，禁一切模型自评信号（[Statistical Scouting](https://arxiv.org/abs/2605.09618) 证明廉价自评信号基本失效）。外推条件修补：倒 U 律原始成立条件是同一 prompt 的 i.i.d. 采样，本策略多样性来自 K 个人工种子，故内置 K 固定、N→∞ 的过采样消融先证倒 U 在本设定下存在，否则停机闸降级为经验规则。研究变体：K=4–6 个完全无通信的独立提议者各拿显式切分的探索视角，聚类器按规范化 mechanism_change 去重、每簇留 top-2、簇数硬上限 3。

**改进价值假设**：相对同预算单 agent 串行 best-of-N：(1) holdout 最优分差 ≤1pp 且墙钟 ≤1/3（并行只换墙钟不换分）；(2) 相对朴素辩论聚合基线 holdout +≥3pp 或同分下 token −30%；(3) 研究变体 distinct hypothesis rate ≥60% 且协调开销 token 占比 ≤15%；(4) 过采样消融中倒 U 曲线可观测——不可观测则停机闸判为无据并登记；(5) 作为全厂基线：任何复杂协议同任务同预算不显著优于本策略即判无增量。

**证据**：
- <https://arxiv.org/abs/2203.11171>（Self-Consistency：GSM8K +17.9%、SVAMP +11.0%、AQuA +12.2%、StrategyQA +6.4%）
- <https://arxiv.org/abs/2402.05120>（More Agents：性能随实例数提升、与复杂方法正交可叠加）
- <https://arxiv.org/abs/2406.04692>（MoA：纯开源 LLM AlpacaEval 2.0 65.1% vs GPT-4 Omni 57.5%）
- <https://arxiv.org/abs/2403.02419>（倒 U 扩展律、解析预测最优调用数——停机闸理论源）
- <https://arxiv.org/abs/2402.18272>（强 prompt 单 agent ≈ 最好讨论方法——辩论臂先验）
- <https://arxiv.org/abs/2605.09618>（Statistical Scouting：廉价信号无法回收 oracle 路由头部、66% 有益辩论在投票一致但错误时）
- <https://arxiv.org/abs/2606.00820>（Not All Flips：37% 翻转无同伴信息也会发生）
- <https://arxiv.org/abs/2606.05670>（BenchAgent：ChatEval 4.34× token 仍落后、LLM-Debate 1.39× token 落后）
- <https://www.trychroma.com/research/context-rot>（每对空白上下文的依据）
- <https://code.claude.com/docs/en/workflows>（哈希记账恢复语义、stall≤5）
- <https://code.claude.com/docs/en/worktrees>（一任务一环境）

**成本**：token≈同预算串行基线（预算对齐是设计约束，不主张 token 增益，主张墙钟与对单点失败的稳健性）；每对独立环境有 1.2–2× overhead；实验占年度包络 5–8%。

**风险**：倒 U 陷阱（难档过量采样反降平均且停机信号基本失效）；相关失败（N 对同犯同一系统性错误——K 种子强制多样性 + diff 相似度 >0.9 判伪多样性告警）；判分器被过拟合（holdout 双门+评测器版本冻结）；弱强混采对抗攻击面（consolidator 只按确定性分数接受弱模型候选）；种子多样性≠i.i.d.（过采样消融内置）；聚类误合并好假设（每簇 top-2）；提议者与评测器同源偏差（模型档位分离）。

**裁决（rank 1）**：唯一同时满足『单 agent 已极限、token 敏感、无人值守』三点的策略。6 条证据全部逐字核实。价值判断：best-of-N+holdout 是真实质量机制而非包装；倒 U 停机闸针对无人值守最贵的失败模式（无限采样烧预算）；[2402.18272](https://arxiv.org/abs/2402.18272) 为否定辩论型聚合提供直接证据，基线不稻草人。改进假设第(1)条诚实不宣称质量增益。唯一保留：墙钟必须按载体分组报告（账户并发争抢污染结论）。

### S5 三闸生成-验证分离与错误传播治理（排名 2 · recommend · 两者皆可）

**机制**：生成者与验证者强制分离、上下文零共享，三层漏斗叠加在生成拓扑之上。**闸 1·冻结上下文评审**：评审 agent 与生成者事前零共享上下文（[Context Rot](https://www.trychroma.com/research/context-rot)），只读产物输出结构化 bug 列表，返回意见由生成侧 lead 用更宽上下文二次过滤（防修复循环）；研究变体三角色花钱闸——Reviewer/Challenger（匹配 [MAST](https://arxiv.org/abs/2503.13657) 14 类失败症状）/Inspector（证据缺口），任一 reject 即 reject（保守偏置），被拦假设事后可行比例 >20% 则降级为『标记不拦』，每假设最多评审 2 轮后强制进评测由评测器裁决。**闸 2·外置 critic 环**：回合末输出成功概率分+问题类别，低于阈值 0.6 退回、≤3 轮封顶（[OpenHands Critic](https://docs.openhands.dev/openhands/usage/agent-canvas/critic)）。**闸 3·确定性 watchdog 终审**：纯脚本不启任何 agent，hooks exit 0/2 语义（[OpenHands hooks](https://docs.openhands.dev/openhands/usage/customization/hooks)）、Stop 钩子强制不许结束直到 lint/测试过、watchdog 独占合并权；/goal 会话级三态判定（[Claude Code /goal](https://code.claude.com/docs/en/goal)）。**门矩阵**：watchdog（结果级）>critic（过程级）>评审（语义级）>goal（会话级），watchdog 红灯任何臂不可覆盖，每门超时动作预定义。**错误传播治理**：验证权收中央（[scaling science](https://arxiv.org/abs/2512.08296) 三规律之一）；层级拓扑最抗故障 + Challenger/Inspector 挽回 96.4%（[2408.00989](https://arxiv.org/abs/2408.00989)，本次裁决逐字核实）；genealogy-graph ≥89% 阻止最终感染（[2603.04474](https://arxiv.org/abs/2603.04474)）。**禁止乘性漏过声明**：三闸读同一批产物、漏过事件相关，不做独立相乘假设——漏过率实证测量，注错集必须同时含机械类与语义类。

**改进价值假设**：相对无独立验收基线（生成者自评自合并）：(1) 注入缺陷集拦截召回率显著更高（Fisher p<0.05；+25pp 为期望值非判据）；(2) 『测试绿但语义错』类合并存活率相对去 watchdog 消融臂降低 ≥30%；(3) 3 轮封顶+类别过滤把 token 增幅控制在 ≤2×；(4) 研究变体：固定 proposer 产出池只换门，评测预算有效利用率 CI 优于无门与自评门中较优者，评审层 token ≤ 所省评测成本 20% 且墙钟 ≤1.15×；(5) 反向测试：每臂注入 5 个门自身失效，静默放行数=0 为上线卡口。

**证据**：
- <https://cognition.com/blog/multi-agents-working>（评审须主 agent 宽上下文过滤；Devin Review 58% 严重率为自报无分母）
- <https://docs.openhands.dev/openhands/usage/use-cases/software-factory>（reviewer exact-head 防移花接木；最小权限；watchdog 纯确定性合入）
- <https://docs.openhands.dev/openhands/usage/agent-canvas/critic>（回合末打分、默认 0.6、≤3 轮）
- <https://docs.openhands.dev/openhands/usage/customization/hooks>（exit 0/2 语义、Stop 强制续跑）
- <https://code.claude.com/docs/en/goal>（三态判定、四类致命错误清 goal）
- <https://code.claude.com/docs/en/agent-teams>（TaskCompleted/TeammateIdle hook 退出码 2；注意此页无文件锁）
- <https://www.anthropic.com/engineering/building-effective-agents>（evaluator-optimizer 前提=有明确评估标准）
- <https://arxiv.org/abs/2310.01798>（无外部反馈的自纠有时反而更差）
- <https://arxiv.org/abs/2512.08296>（无集中式验证的架构传播更多错误）
- <https://arxiv.org/abs/2408.00989>（层级降幅最小 5.5% vs 10.5%/23.7%、Challenger/Inspector 挽回至多 96.4%——裁决逐字核实）
- <https://arxiv.org/abs/2603.04474>（原子错误种子扩散、genealogy-graph ≥89%）
- <https://arxiv.org/abs/2503.13657>（MAST 14 类失败模式与干预数字 +9.4%/+15.6%）
- <https://arxiv.org/abs/2308.07201>（ChatEval：角色多样性是收益来源）
- <https://www.trychroma.com/research/context-rot>（冻结上下文评审依据）
- <https://arxiv.org/abs/2604.18805>（能力边界：外置评审修不了深层推理缺失）
- <https://arxiv.org/abs/2502.14143>（Multi-Agent Risks 结构性风险分类学——注意非 MAST 数字出处）

**成本**：评审+critic 约增 20–40% token（须实测）；watchdog/goal 小模型每轮固定开销但量小；每缺陷单元 ≤3 修复轮；实验占年度包络 6–10%。

**风险**：评审噪声修复循环（最高频失败模式——lead 过滤+硬封顶）；三闸漏过相关非独立（不做乘性声明）；watchdog 对『绿但错』全盲（语义类注错强制入集）；弱评估器新单点；钩子静默放行/误拦（钩子与业务代码同库版本管理+反向测试为上线卡口）；保守偏置拦好假设（事后可行性审计 >20% 触发降级）；门矩阵冲突死锁（超时动作预定义）；异构第三方 agent 不走 critic 路径；能力边界（2604.18805）。

**裁决（rank 2）**：全清单证据链最完整，直击无人值守最危险失败模式：静默坏合并。三层验证全部关键数字逐字核实。验证权收中央+确定性 watchdog 独占合并权不是可选项而是必选项。其对 2408.00989 数字的坚持经裁决者独立 curl 级核实属正确。未逐字核实项：MAST judge 管线 0.94/0.77/0.833/0.77 不在 arXiv 摘要页（正文数据，按正文采信但标注）。

### S1 入口三查门控与并行度求解（排名 3 · recommend · 两者皆可）

**机制**：把『要不要多 agent、并行多大』做成全厂入口的确定性 triage 步，而非任何拓扑的默认前提（两份评审一致指出全部草案默认多 agent 成立、无一带这道门）。三查：(a) **可分解性**——需所有部分共享同一推演上下文的任务判不通过，降级单 agent 长时程（[Anthropic 自认](https://www.anthropic.com/research/multi-agent-research-system)：多数编码任务可并行部分少于研究）；(b) **写独立性**——写集可划成不相交工作集才通过，不通过则路由单写者分支；(c) **可验证性**——无 evaluator 的子任务禁止并行化。产出 gate-report 落盘：路由决定 ∈ {单 agent 长时程 | 星形委派 | 单写者+只读智能 | 分片 map}。定量依据：[scaling science](https://arxiv.org/abs/2512.08296) 87% 留出配置选对最优架构、+80.8%~−70.0% 区间、三规律；[MacNet](https://arxiv.org/abs/2406.07155) logistic 增长；[SIMAS](https://arxiv.org/abs/2606.00655) 非单调。并行度是被求解的量而非常数：初始委派按复杂度分档给先验（**注意：Anthropic building-effective-agents 页经核实并无 effort scaling 数字分档，该先验无出处，已降级为待校准先验而非硬编码**），随后以 ≤10% 预算做校准采样拟合边际增益曲线（倒 U 律，[2403.02419](https://arxiv.org/abs/2403.02419)），预测边际 <ε 即停；所有并发参数由求解器给出，禁止拍定值。门控的可学习版本（MaAS 式）作为日志积累后的扩展项，不在 v1。

**改进价值假设**：相对『无门控、全部任务硬上多 agent』基线：预注册混合任务池上加权验收完成率 +≥10pp；门控拒绝集上被强行多 agent 的对照臂相对被路由臂完成率差 ≥10pp；门控路由与事后穷举最优架构在留出任务上一致率 ≥70%（scaling science 为 87%，产线设定预期更低，此值为工程目标）；并行度求解器给出的 N 与 K-sweep 实测最优 N 偏差 ≤1 档，且同等完成质量下总 token 比固定 K 峰值参数降 ≥30%。

**证据**：
- <https://arxiv.org/abs/2512.08296>（260 配置、R²=0.373/0.413、87%、+80.8%~−70.0%、三规律）
- <https://arxiv.org/abs/2406.07155>（MacNet：logistic 增长、不规则拓扑更优）
- <https://arxiv.org/abs/2606.00655>（SIMAS：性能不随 agent 数单调）
- <https://arxiv.org/abs/2403.02419>（倒 U 扩展律——补引，原草案漏掉）
- <https://www.anthropic.com/engineering/building-effective-agents>（门控原则原文；effort scaling 分档**无出处**已核实）
- <https://www.anthropic.com/research/multi-agent-research-system>（coding caveat——门控 (b) 的动机）
- <https://arxiv.org/abs/2606.05670>（BenchAgent：真实效应量可能仅个位数 pp，功效分析必做）

**成本**：门控本身每任务 1–3 次模型调用+gate-report 落盘，可忽略；校准采样 ≤ 任务预算 10%；求解器为纯代码零模型调用。实验占年度包络 5–8%。

**风险**：R²=0.373 预测力中等且依赖基准分布；门控误分类代价不对称（拒绝侧宁严勿松）；选择偏误（被拒任务必须同池跨臂，否则路由效应与拓扑效应无法分离）；校准采样在超小任务占比过高（设最低预算下限）；MAST 41–86.7% 失败率——选对架构不保证跑通，本策略只承诺路由不承诺执行。

**裁决（rank 3）**：价值形态是『避免损失』而非『创造增益』——−70.0% 序列规划灾难模式（本轮核实）意味着错误路由一次吃掉大量预算。三查设计对应已验证规律（饱和律/单写者原则/集中验证律）。存疑项已记录：effort scaling 分档无出处（裁决打开页面确认），策略已按降级处置正确。70% 一致率设为工程目标而非照搬 87%，诚实。

### S2 代码化编排运行时（排名 4 · recommend · 两者皆可）

**机制**：编排从 prompt 搬进确定性代码，作为全厂所有拓扑的执行底座。拓扑写在脚本里（agent()/parallel()/pipeline()/phase()），中间结果只留脚本变量；脚本无文件系统/shell 访问权。硬限写死 runtime：默认 16 并发（可 1–256）、单次 parallel/pipeline ≤4096、每 run ≤1000 agent、禁 import()/Date.now()/Math.random()、运行中无用户输入（[Claude Code workflows](https://code.claude.com/docs/en/workflows)）。恢复语义：**裁决纠正——厂商实际语义是『缓存已存结果+按 agent 启动序重放至首个 prompt 分歧』，文档无『三元组哈希记账』表述；机制实质成立但进基线时按厂商语义实现，避免自造概念债务**。stall 自动重启 ≤5 次后标 blocked；usage-limit 挂起带确定性上界。控制面/执行面分离（[Cline hub-spoke](https://docs.cline.bot/sdk/architecture/hub-spoke)：hub 不跑 agent loop、client 能力注册、断开后 spoke 继续）；hub 配 WAL+audit trail（[AG2](https://github.com/ag2ai/ag2)）。**状态权威**：文件系统是唯一真源，runtime state 只存引用+内容哈希，恢复时对账、磁盘为准。**控制流归属**：默认转移由脚本决定；重规划是显式节点类型——何时进入由确定性触发器决定，节点内由 LLM 决定内容。通信介质治理：AG2 四类类型化信道 + [AgentPrune](https://arxiv.org/abs/2410.02506) 剪枝（$43.7→$5.6、token −28.1%~72.8%）+ KV-cache 纪律为一级生产指标（[Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)：100:1、缓存/未缓存 10× 价差、前缀稳定、只追加、mask-don't-remove——logit 掩码不可用时退化为按阶段固定工具集）。节点级 trace（每次调用原始 prompt/response 落盘）强制。

**改进价值假设**：对照臂=prompt 驱动星形编排+整图状态快照恢复（最强廉价替代）：注入 5 类故障后自动恢复到与干净跑等价状态成功率 ≥80%，恢复期重复执行 token ≤ 整图快照臂 60%、≤ 整图重跑臂 20%（**80%/60%/20% 为工程目标、无文献先验，显式标注**）；无故障时完成率损失 Δ≤2pp 且编排层 token 占比 ≤5%；接剪枝后同等完成率 token 再降 ≥30%；KV-cache 纪律使输入 token 成本降 ≥50%（供应商支持缓存前提下）。

**证据**：
- <https://code.claude.com/docs/en/workflows>（硬限与恢复语义——裁决逐条确认；恢复表述须按厂商语义校正）
- <https://docs.devin.ai/work-with-devin/dynamic-workflows>（独立 VM、git branch 交接、脚本决定失败处置）
- <https://github.com/langchain-ai/langgraph>（Pregel 式三原语，代码行号已核实）
- <https://github.com/ag2ai/ag2>（Hub registry/WAL/audit；四类类型化信道）
- <https://github.com/microsoft/agent-framework>（四图模式+checkpointing+OpenTelemetry）
- <https://github.com/google/adk-python>（确定性 workflow agents 与 AutoFlow 并存）
- <https://github.com/openai/openai-agents-python>（三原语；Handoff input_filter；Tracing）
- <https://docs.cline.bot/sdk/architecture/hub-spoke>（hub 不跑 loop；断开 spoke 继续）
- <https://github.com/agentscope-ai/agentscope>（actor 分布式+事件总线）
- <https://arxiv.org/abs/2410.02506>（AgentPrune 数字全部逐字确认）
- <https://arxiv.org/abs/2410.08115>（Optima——特定骨干训练后结果，不外推前沿模型）
- <https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus>（KV-cache 各项逐字确认）

**成本**：编排层几乎不加 token；主要成本是工程（自建 runtime 一次性投入）。实验占年度包络 3–5%。

**风险**：确定性换表达力（金丝雀 phase+节点级预算闸）；prompt 一改下游全重跑雪崩（预算闸+dry-run 预估）；框架生态换代（押注维护侧，自建层只依赖三原语级稳定面）；hub 单点（WAL/audit）；抽象遮蔽调试（节点级 trace 强制）；KV-cache 依赖供应商能力（退化路径已定义）；类型化信道治不了 Silo-Bench 推理侧整合失败（跨 agent 整合类问题路由假设池）。

**裁决（rank 4）**：价值不依赖增益假设而依赖无人值守硬约束（确定性重放、故障恢复、挂起有界）。厂商先例全部核实。两点裁决：(1)『哈希记账』是包装性表述，按厂商语义实现；(2) **进基线条件：v1 优先采用厂商 workflow runtime 承载拓扑语义，自建仅限 hub-spoke/audit/WAL/节点 trace 增量——绿色field 重造 Pregel 级 runtime 是纯风险无收益**。KV-cache 纪律是 token 敏感产线的最大单项成本对冲，必须进基线。

### S6 跨会话黑板续跑与记忆外化（排名 5 · recommend · 两者皆可）

**机制**：长周期无人值守层：compaction isn't sufficient（[Anthropic 原话](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)），跨会话靠文件产物。首会话 initializer 产出四件套+初始 git 提交：init.sh、进度叙事文件、feature 清单 JSON（每项带 passes 位、初值全 failing）、验收测试——tests/ 与清单 schema 被钩子保护（exit 2 拦截）。**passes 位外部核验**：passes 是 agent 可写位，原文自陈失败模式『后来的 agent 看到有进展就宣布完工』——指定 watchdog 为外部核验方：每次翻位后由 watchdog 重跑验收命令回写真值，agent 翻位仅是申请；无人复核则记 unverified。每会话固定流程：git log+进度文件恢复→init.sh 冒烟（红则修复或回滚最近绿检查点，禁止带病推进）→挑最高优先级 failing feature→每 feature 一提交。**恢复语义统一表**：冒烟红=回滚到最近绿检查点+副作用纪元封存；子任务卡死=账本重规划续做（不回滚）；冒烟绿但 passes unverified=只信 watchdog 复核。**副作用安全**：检查点带副作用账本，回滚经 effect-gateway/epoch fencing——恢复后旧纪元外部请求 100% 拒绝（UndoBench 实测无 fencing 的回滚在『已提交未确认』阶段成功率掉到 46.7%）。上下文纪律：压缩可还原、todo 反复复述对抗 U 形偏置（[Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)）、失败轨迹只追加、DECISIONS.md append-only。**记忆外化层（知识而非状态）**：[MemGPT](https://arxiv.org/abs/2310.08560) 分层、[Mem0](https://arxiv.org/abs/2504.19413) 抽取-整合-检索、[MIRIX](https://arxiv.org/abs/2507.07957) 六类、[ACE](https://arxiv.org/abs/2510.04618) playbook 增量更新、[sleep-time compute](https://www.letta.com/blog/sleep-time-compute) 后台预计算（**裁决核实：5×/2.5×/+13/18% 三个数字不在所引博客页面上，仅在 arXiv 论文页**，见 §8 核实注记）、[Voyager](https://arxiv.org/abs/2305.16291) 技能库。

**改进价值假设**：基线=公平对话交接对照（同 repo+git log+重读仓库，无清单/冒烟门/记忆库）：≥8 session、注入 3–5 次强杀（进程杀/上下文截断/模型切换三型）的长程任务上：(1) 恢复正确率提升 ≥40pp（基线实测值进报告不预设≈0）；(2) 恢复后重做率 <5%；(3) 坏状态接手本策略=0 且去冒烟门消融臂 >0；(4) 带 epoch fencing 的回滚副作用重放=0、无 fencing 消融臂 >0；(5) 记忆层使后续同类任务 token −30% 或完成率 +10pp（stateful 前提下）；(6) 总 token ≤ 公平基线 80%。

**证据**：
- <https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents>（全套协议逐字确认）
- <https://docs.cline.bot/sdk/guides/multi-agent-teams>（teams.db 随 session 恢复；自认状态滞后）
- <https://docs.cline.bot/sdk/architecture/hub-spoke>（断开 spoke 继续）
- <https://code.claude.com/docs/en/sub-agents>（agent ID+SendMessage 带历史续跑）
- <https://github.com/ag2ai/ag2>（Hub WAL+audit trail）
- <https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus>（压缩可还原、todo 复述、保留失败轨迹）
- <https://arxiv.org/abs/2310.08560>（MemGPT）
- <https://arxiv.org/abs/2504.19413>（Mem0 各数字逐字确认）
- <https://arxiv.org/abs/2507.07957>（MIRIX）
- <https://arxiv.org/abs/2510.04618>（ACE 各数字逐字确认）
- <https://www.letta.com/blog/sleep-time-compute>（**仅确认定性表述与 stateful 前提；5×/2.5×/+13/18% 不在该页**）
- <https://arxiv.org/abs/2305.16291>（Voyager）
- <https://arxiv.org/abs/2307.03172>（Lost in the Middle）
- <https://www.trychroma.com/research/context-rot>（18 模型退化）

**成本**：进度文件与状态位维护 ≈ 每会话 +1–3% token；记忆层后台预计算走离线档、检索时 JIT 加载。实验占年度包络 10–15%（长任务是大头）。

**风险**：前提=任务可预枚举清单（探索型由门控判定）；状态滞后（init.sh 冒烟是唯一可信源）；agent 绕过/误改状态位（钩子硬拦+完整性哈希+两类篡改测试全过为上线前提）；无法恢复含运行中队友的会话（中断点对齐 feature 边界+WIP 提交）；回滚副作用重放（epoch fencing 硬依赖，缺失即禁用自动回滚）；进度文件膨胀；记忆层 stateless 收益归零、受 Context Rot 制约、不修复推理（scaffold 仅解释 1.5% 方差）；hub 单点。

**裁决（rank 5）**：解决生存问题而非优化问题。核心协议全部核实且为厂商原文。关键增量设计——passes 位由 watchdog 外部核验——直接补上 Anthropic 协议自陈的自评漏洞，真实且可测。分层裁决：**状态外化层（黑板+检查点+冒烟门+fencing）= 推荐进基线；记忆外化层=有条件**（收益硬依赖 stateful 场景，sleep-time 倍数不在所引页面、数字来源存疑，进基线前以本厂实测为准）。假设(5)已自带 stateful 限定，诚实。

### S4 确定性分片-隔离-依赖序集成（排名 6 · conditional · 两者皆可）

**机制**：参数化机制（两评审判定原策略 2 与 B4 是同一机制的两次实例化，合并评测成本减半）：分片器+隔离单元+合并器+恢复记账。分片器第一档必须是确定性 selector（tree-sitter/编译器符号/import-call 图/API schema 比对/词法模式），无模型跑遍全仓库，配召回测试；**表述修正：selector 只保证枚举覆盖、不保证必要覆盖——对反射/DI/动态注册等动态绑定边系统性漏检，改述为『枚举器+召回补漏轮』，语义可达调用点单列指标（人工抽样 50 调用点核对）**。隔离执行：每 shard 一个写者+一份完整环境副本（[worktree](https://code.claude.com/docs/en/worktrees) 或独立容器），worker 上下文只装载 shard 作用域+任务卡，完成前必须在自己环境跑 shard 级测试。认领与恢复：共享任务表落盘 JSON，认领=任务卡文件锁（**出处更正：文件锁是 [Cline Kanban](https://docs.cline.bot/usage/kanban) 机制**）带 TTL+心跳，同 shard 重试 ≤5 次标 blocked 不静默丢弃；结论原子写（tmp+rename）。受控合并：按 producer→consumer 依赖图排序，接口/契约类 shard 先行（[NP-Bench](https://arxiv.org/abs/2610.07261) proactive 臂：干净集成 1/9→9/9、merge 冲突 13→0，收益来自任务分配方式而非模型推理——对本厂至关重要：机制收益不依赖基座变强而贬值）。**收敛点裁决**：integrator=确定性 watchdog 外壳：每步合入先跑确定性三件套（回归全集+契约测试+类型检查），仅当验证失败需归因时才升级启动 agent；producer 被退回→其全部下游自动转 blocked。reducer 只消费 schema 校验过的压缩结论做去重/排序/拼装，**明确不做跨片因果推断**（[Silo-Bench](https://arxiv.org/abs/2603.01045)：整合是推理侧瓶颈）——跨片关联问题显式导出为下一轮假设移交假设池。金丝雀门：首批 ≤3 shard 结论过 schema 校验+对拍 ground truth 才放行全量。备选介质不进基线：[CodeCRDT](https://arxiv.org/abs/2510.18893) 仅作对照变体。冲突面诚实口径（[AIDev-pop](https://arxiv.org/abs/2607.04697)）：跨 agent 文本冲突 41.7% vs 19.8%、约 42% 结构性——**但 0.5% 是共活对中跨 agent 对占比、4.3%（122/2807）才是仓库口径（裁决已纠正），勿高估跨 agent 冲突面；本策略价值可能主要来自并行与覆盖而非降冲突**。

**改进价值假设**：按 ground truth 类型分判：(i) 唯一 GT 任务（lint 规则落地、符号重命名、评测配置扫描）：相对朴素并行基线合并冲突数 ≤10%、召回率差 ≤2pp、配置覆盖率 100% 且记录保真率不低于串行；相对单 agent 串行墙钟 ≤1/3（开发）/≤1/5（评测）、token ≤1.3×。(ii) 无唯一解任务（API 迁移、重构）：改用可执行判据（类型检查/测试全绿/行为差分），集成通过率不低于朴素臂。(iii) 整合正确率差 ≤2pp；若落后 >5pp 则裁决『只赢执行不赢结论』。

**证据**：
- <https://devin.ai/blog/agentic-map-reduce>（**裁决核实：HTTP 404 链接失效，检索不到该文；机制改由 NP-Bench 与 Devin dynamic workflows 双源支撑**）
- <https://arxiv.org/abs/2610.07261>（NP-Bench 全部数字逐字确认；**引用更正：原草案把数字挂到 2510.18893，已更正**）
- <https://arxiv.org/abs/2606.14066>（FastContext——**v4 已撤稿（product IP issues、无 PDF）；摘要仅含 resolution +5.5% / token −60%；56.2%/46.5% 不在摘要且全文不可得，按撤稿处置**）
- <https://arxiv.org/abs/2607.04697>（AIDev-pop 逐字确认；0.5%/4.3% 口径已纠正）
- <https://code.claude.com/docs/en/worktrees>（worktree 隔离、.worktreeinclude、/batch）
- <https://docs.cline.bot/usage/kanban>（一卡一 worktree、文件锁认领——出处更正）
- <https://code.claude.com/docs/en/workflows>（stall≤5、恢复语义借用于 shard 重认领）
- <https://arxiv.org/abs/2603.01045>（Silo-Bench：reducer 不做跨片推断的依据）
- <https://arxiv.org/abs/2510.18893>（CodeCRDT 600 试验——**编号更正：原草案与 NP-Bench 编号对调**）
- <https://cognition.ai/blog/devin-can-now-manage-devins>（managed 模式独立 VM、git branch 交接）

**成本**：token≈串行总量×1.1–1.3（估算须实测）；主要成本在评测实例的容器 CPU 与墙钟（非 LLM）；selector 开发是每类任务一次性成本。实验占年度包络 8–12%。

**风险**：selector 召回率上限且动态绑定边漏检（抽样审计+补漏轮+零模型 grep 兜底，grep 是兜底非判据）；只适配 map 形任务；隔离只消文本冲突不消语义冲突（依赖图排序+契约 shard 先行+合入后全局测试兜底）；integrator 升级路径是 agent（升级预算设界）；producer 退回的下游级联作废成本；CodeCRDT 减速与语义冲突实测存在（仅对照）。

**裁决（rank 6 · conditional）**：**条件：(1) 仅接纳经门控判为 map 形的任务，gate-report 为强制前置而非事后归类；(2) selector 召回率必须过抽样审计+补漏轮，未达阈值前分片范围不得扩大。** 价值判断：全清单新鲜实证最强（NP-Bench 逐字核实），收益不依赖基座变强、与能力饱和律兼容；成本结构最优（token 1.1–1.3×，主要成本是容器 CPU）。证据瑕疵记录但不致命：agentic-map-reduce 链接 404；AIDev-pop 的 0.5% 归因错误已要求改正后引用。

### S3 双账本星形编排与单写者降级（排名 7 · conditional · 大型项目开发）

**机制**：门控判『可分解但非 map 形』的开发任务走此拓扑。星形两段式：唯一 lead 垄断分解/分派/汇合/重规划/最终判断，worker 间无横向协议。双账本持久化到仓库文件（[Magentic-One](https://arxiv.org/abs/2411.04468) 语义）：task ledger 五栏（已核实/待查/待推导/猜测/计划）——猜测与已核实分文件存+schema 强制枚举值，已核实栏每条断言可回溯到 commit（防『猜测混入已核实』这一无人值守最隐蔽传播通道）；progress ledger 卡死超阈值由脚本触发重规划节点，LLM 在节点内改计划。**lead 汇合容量硬界**：每批汇合 ≤5 个子任务结论——依据 [Manus Wide Research](https://manus.im/blog/manus-wide-research-solve-context-problem)（**裁决降格：原文为定性描述『第 8–9 项上下文吃紧、第 9 项起编造』，称『量化切点』属夸大；硬界作为工程设计可辩护但应改述**）；超出硬界转 S4 的依赖序汇合。委派契约：worker 初始上下文白名单=system prompt+委派消息（目标/验收命令/禁触文件清单）+仓库约定+git 快照（[Claude Code sub-agents](https://code.claude.com/docs/en/sub-agents)）；显式声明『你与 lead 不共享状态，需要的事实必须自带』（逐条针对 [manager/child 三缺陷](https://cognition.com/blog/multi-agents-working)）；产物直写文件系统只回传 ≤2k token 压缩结论+产物路径；结构化产物按角色协议逐级传递的谱系先例为 [MetaGPT](https://arxiv.org/abs/2308.00352) SOP 与 [ChatDev](https://arxiv.org/abs/2307.07924) communicative dehallucination。**单写者降级分支**：门控 (b) 不通过时——单写者独占所有写操作，其余 agent 只贡献智能：只读侦察 subagent / 冻结上下文评审 / smart-friend（[Cognition 原文](https://cognition.com/blog/dont-build-multi-agents)『writes stay single-threaded』直接支撑）；评审返回的 bug 必须由主 agent 二次过滤。**证据诚实框架**：90.2% 出自内部 research eval，同源 coding caveat 明言『多数编码任务可并行部分少于研究且 agent 尚不擅长实时协调委派』——本策略场景恰在点名弱项区，假设按保守口径设定。[Can Small Agents Collaborate](https://arxiv.org/abs/2601.11327)：orchestrator 容量驱动整体性能——lead 必须用产线最强模型不可降级，worker 可用次强档降成本。

**改进价值假设**：基线=fix1 代已校准单 agent（须先通过与商业 harness 可比的地板校验，禁止在实测 0/5 的地板上比较）：门控判『可分解非 map 形』的自建多模块任务集（12–20 模块、5–8 条跨模块接口契约、含注入语义陷阱）上：(1) 本拓扑（lead 汇合批 ≤5）验收功能完成率不低于校准单 agent（非劣 Δ≥0）且墙钟 ≤1/2、token ≤2×；(2) 相对朴素自由委派基线完成率 +≥10pp 且失败可定位率 ≥80%；(3) 消融臂（去汇合硬界）在 >5/批时出现编造模式征兆；(4) 写耦合子集上单写者降级相对多写者对照集成失败率显著更低（Fisher p<0.05）；(5) 若校准单 agent 完成率 ≥85%（饱和区），主判据自动切换为同完成率下 token ≤1.5×。

**证据**：
- <https://www.anthropic.com/research/multi-agent-research-system>（90.2% 内部 research eval、15× token、coding caveat 逐字确认）
- <https://arxiv.org/abs/2501.06322>（**裁决核实：该编号实为《Multi-Agent Collaboration Mechanisms: A Survey of LLMs》综述，与 Anthropic 系统无关——此引用须删除或更正，90.2%/15× 的出处只保留 Anthropic 博客本身**）
- <https://arxiv.org/abs/2411.04468>（双 ledger、卡死→反思→重规划；GAIA 38% 等）
- <https://cognition.com/blog/multi-agents-working>（manager/child 三缺陷；writes stay single-threaded；Devin Review 2 bug/PR）
- <https://cognition.com/blog/dont-build-multi-agents>（单写者+多脑原则原文、Flappy Bird 反例）
- <https://code.claude.com/docs/en/sub-agents>（初始上下文白名单、SendMessage 续跑）
- <https://manus.im/blog/manus-wide-research-solve-context-problem>（**定性描述，非量化切点**——支持硬界方向）
- <https://arxiv.org/abs/2601.11327>（orchestrator 容量驱动——lead 选型硬前提）
- <https://www.anthropic.com/research/effective-context-engineering-for-ai-agents>（compaction/结构化笔记/多 agent 三类技术；子 agent 回传 1–2k token）
- <https://arxiv.org/abs/2308.00352>（MetaGPT SOP）
- <https://arxiv.org/abs/2307.07924>（ChatDev chat chain / communicative dehallucination）

**成本**：token 按 5–15× 区间记账（**15× 是研究场景外推、两评审均指出对编码无效**），per-subtask 预算写进账本（BrowseComp 上 token 单独解释 80% 方差——不设预算的更强可能只是更贵）；KV-cache 纪律是成本模型最大单项对冲；单写者分支预期 token 1.5–2×。实验占年度包络 10–15%。

**风险**：lead 单点（分解错误被并行放大——三查前置+机械验收+重规划+账本文件/git 恢复）；lead 汇合是瓶颈（context rot+编造阈值+容量驱动三重证据——硬界+分批+溢出转依赖序汇合）；manager/child 三缺陷（委派契约+回传三段式）；成本失控（per-subtask 预算、超限降级单 agent）；弱 lead 收益为负（2601.11327）；单写者分支并行度上限低；**本策略不承诺消除失败（MAST 41–86.7%），承诺失败显性化、可定位、可重规划**。

**裁决（rank 7 · conditional）**：**条件（全部为可执行前置）：(1) 先过 fix1 代单 agent 地板校验，地板不过实验顺延；(2) 主判据受饱和律约束（S0 ≥85% 自动切 token 判据）；(3) 修正引文错误：2501.06322 误挂已确认。** 价值判断：处于证据最弱区间——90.2% 内部 eval 且同源 caveat 点名弱项区；5–15× token 无先验。但应对正确：非劣性假设而非增益假设、per-subtask 预算、lead 选型硬前提、汇合硬界有定性支持。单写者降级分支有 Cognition 原文直接支撑，是写耦合场景最安全形态，值得随门控 (b) 一并进基线。

### S7 假设池门控研究环（排名 8 · conditional · 评测驱动优化）

**机制**：任务 B 的核心多 agent 形态：共享假设池上的角色分工+评审器与生成器共演化。拓扑：1 个 Supervisor 持双账本，管理六类 worker（[AI co-scientist](https://arxiv.org/abs/2502.18864) 角色集：Generation/Reflection/Ranking/Evolution/Proximity/Meta-review）。通信介质=JSON 假设池文件（每条含 id/状态机 proposed→under_review→accepted|rejected/分数/父 id/实验 run id/metrics 摘要），agent 间零自由对话只传工件引用；实验产物直写文件系统。四道门：(1) **入评门**——假设必须挂已跑完的实验 run 且 metrics 过 schema；(2) **citation 门**——Reflection 干净上下文，输出 schema 强制逐条引用 metrics 数值、无引用不得分（直接针对 [2604.18805](https://arxiv.org/abs/2604.18805) 的 68% 轨迹证据被忽略；**裁决更正：原文表述是一般性结论，策略『检测不到 68% 证据忽略』的表述须按原文口径改正**）；(3) **critic 重做环**——评分 <0.6 退回 Evolution、≤3 轮、超限置 rejected；(4) **排序门可降级**——确定性实验分数为主，成对辩论 Elo 只作消融臂（本厂已裁定 9 个 LLM 评审≈2 票信息量）。**与采样策略的账本统一**：同一假设池/同一预算账本，降级路径=连续 2 轮零 accepted 自动转纯采样模式。**数据三级物理隔离**：dev/holdout/confirm 零交集；confirm 只在写基线前跑一次且结果不回流 Proposer。**LLM-judge 变体矛盾修复**：judge 与被优化对象模型隔离+评估器先过准入考卷+judge 版本化；**生成-评审共演化轨道**（[CycleResearcher](https://arxiv.org/abs/2411.00816)：CycleReviewer MAE 比单个人类评审低 26.89%——**裁决注明：『共演化』为推断性表述，原文无此纵向分析**）：judge 不当静态组件，周期性再校准进环。**防自证**：Evaluator 输出目录只读、runtime 签发哈希、三账本独立计量。**无人值守晋级语义**：accepted 产物默认限定在 JIT 可写边界内的配方提案；越界提案终态=挂起队列+安灯+按旧基线继续+可交付部分结果；是否放宽为『confirm 集把关的 DSL 内自动晋级』由运营者裁决、草案不自行豁免。**档案与谱系**：MAP-Elites 式归档（[OpenEvolve](https://github.com/codelion/openevolve)）、5 岛、30% 探索预算；失败签名保留不保留推理链；accepted 假设带父代谱系，坏假设废黜连带废黜全部子代；假设指纹去重不双花预算。

**改进价值假设**：相对单 agent 串行研究环基线（同模型、同评测预算、同被优化对象）：4 个确定性判分的 harness 配方优化任务上『达到目标指标的任务完成率』+≥15pp，且 dev→holdout 复现率 ≤30%、每美元有效改进数 ≥2×；相对朴素多 agent 基线（同六角色但自由聊天）同等完成率下 token ≤1.2×；accepted 假设证据引用率 ≥80%。**可证伪性内置**：同预算纯采样消融臂（无评审环）若与本策略打平，则裁决『价值来自采样而非评审结构』——核心假设被否证并登记负结果；去 citation 门消融打平则砍掉冗余门。

**证据**：
- <https://arxiv.org/abs/2502.18864>（AI co-scientist 六角色+Supervisor 逐字确认；**78.4% GPQA 一致率未在文中核实到，不作为判据**）
- <https://arxiv.org/abs/2604.18805>（基座 41.4% vs scaffold 1.5%、68% 轨迹忽略证据逐字确认；表述口径已更正）
- <https://arxiv.org/abs/2411.04468>（双账本语义）
- <https://www.anthropic.com/research/multi-agent-research-system>（星形委派+压缩回传）
- <https://docs.openhands.dev/openhands/usage/agent-canvas/critic>（阈值重做环）
- <https://docs.openhands.dev/openhands/usage/customization/hooks>（状态机非法迁移阻断）
- <https://arxiv.org/abs/2411.00816>（CycleResearcher 数字逐字确认）
- <https://arxiv.org/abs/2504.08066>（AI Scientist-v2：模拟评审非真人，accepted≠真有效）
- <https://github.com/codelion/openevolve>（MAP-Elites/5 孤岛/级联评估逐条确认）
- <https://www.nature.com/articles/s41586-023-06792-0>（Coscientist 四命令动作空间）
- <https://arxiv.org/abs/2505.13400>（Robin 闭环样例）
- <https://arxiv.org/abs/2501.04227>（Agent Laboratory 自主度-质量权衡实测）
- <https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus>（归档压缩可还原、失败轨迹保留）

**成本**：编排层每假设 6–10 次模型调用；实验执行（bench 臂）占成本大头。**全清单最贵实验：占年度包络 15–20%；降级版 3 任务×3 种子（约减 60%）先行**。

**风险**：评审噪声修复循环（无 citation 意见一律丢弃）；**增益大头可能是更多采样而非更好科学（基座 41.4% vs scaffold 1.5%）——同预算纯采样消融臂内建归因**；模拟评审非真人（终门必须挂确定性 bench 分数）；坏假设 accepted 后被 Evolution 大量繁殖污染池子（状态机+谱系连带废黜+快照回滚+降级纯采样）；judge 被迎合（模型隔离+准入考卷）；Human Station 语义在无人值守下阻塞（挂起+安灯+部分交付）；统计功效（主指标改比值型+配对设计）。

**裁决（rank 8 · conditional）**：**条件：(1) 同预算纯采样消融臂必须与主策略同跑，打平即登记负结果、六角色环降级为归档+状态机工具；(2) 确定性门立即摘果——入评门/citation 门/三级隔离/谱系废黜/confirm 一次成本极低且有 2604.18805 直接支持，应立即并入任务 B 默认环，无需等六角色拓扑结论；(3) 成本封顶先跑降级版。** 价值判断：角色集有强先例，但最强反方同样被核实——六角色结构的边际贡献可能远小于采样量本身，唯一解药是内置消融臂。修歧义得当、统计口径修正接受。

### S9 Harness 自优化双门补丁环（排名 9 · conditional · 评测驱动优化）

**机制**：被优化对象=产线 harness 本身：把研究循环（定位失败点→造 harness 变体→同题对照重跑→验证改进）与 fix<N> 版本隔离制度化为无人值守闭环。双层嵌套：外层=元搜索（离线，在 archive 上以受限 DSL 表示的配方为节点做搜索——**先跑最简单的进化版作对照，因 [AFlow](https://arxiv.org/abs/2410.10762)/[MaAS](https://arxiv.org/abs/2502.04180) 的 MCTS 优势 presuppose 拓扑在搜索空间内，而无人值守安全 DSL 先只含参数层：提示片段/模型路由/工具集/超时重试/并发度/归档参数；拓扑层为 tier-2 需 confirm 把关+安灯**）；内层=每候选配方一次完整评测闭环。上层串行三角色流水线（通信=文件、零对话）：Failure Miner（读失败轨迹、按 MAST 14 类聚类、每类 ≤5 条、干净上下文；MAST-Data 的 LLM-as-judge 标注管线 accuracy 0.94/recall 0.77/precision 0.833/κ=0.77 直接复用——**正文数据，摘要未含，裁决标注未独立核实**；接入既有 otelcol+Langfuse+MES 三账本观测底座而非重造）；Patch Author（把 harness 当代码产结构化补丁 *.patch+patch_meta.json——定向修改而非无约束编辑，[AutoSaddler](https://arxiv.org/abs/2608.23041) 三消融；补丁优先修执行纪律类失败：步骤重复 15.7%/推理-行动失配 13.2%/不遵守任务需求 11.8%）；Patch Judge（只读分数 JSON 不读轨迹——凭数字不凭故事）。下层=沙箱化并行评测执行：**复用 af 内核既有 Run/Artifact/Trace 与调度器，不另起文件锁/队列/原子写记账（重复造轮子）**。验证门控四道：(1) 级联评估——金丝雀 5 题冒烟→120 题子集全套；(2) **双门合入**——目标失败模式任务涨分 AND 泛化留出集（Miner 不可见）掉分 ≤0.5pp 才合入，合入=fix<N+1> bump+git commit 一键回滚，**评测器与判分口径永不进补丁可写范围（verifier 只读挂载）**；(3) confirm 集——只在写基线前跑一次、不回流；(4) Stop 钩子——连续 3 补丁无泛化通过即自动停环+诊断报告。**无人值守晋级**：tier-1 DSL 内补丁由 confirm 把关自动晋级；越界尝试自动拦下+安灯+按旧基线继续；是否放宽『提案人批准』制度由运营者裁决。**harness 过时压力进环**：[METR](https://arxiv.org/abs/2503.14499) 时间视界约每 7 个月翻倍——留出集月度换血、结果不跨代比较。**预算爬坡制**：按每 token 改进斜率决定去留，<5pp@固定预算判失败，≥10pp 只是单篇先验（AutoSaddler +9.0/+9.6/+10.0pp——裁决核实属实且作者为 Microsoft 系；但其基线是它自己的 harness，数字不外推只作同机制先验区间）。

**改进价值假设**：相对静态 harness 基线（fix1 冻结）：5 轮自优化后优化集通过率爬坡曲线斜率显著 >0（bootstrap 95% CI 不含 0），泛化留出集累计 ≥+5pp、confirm 集 ≥+3pp；相对人工驱动研究循环基线：每周可验证 harness 变体数 ≥3× 且回滚率 ≤30%；消融：结构化诊断+验证式选择 vs 随机/无约束补丁臂——增益必须来自诊断结构而非搜索本身（随机补丁臂打平则判『搜索无增量』登记负结果）。**护栏实验**：注入『verifier 被换宽松』的诱导失败，系统不得把『改 verifier』识别为有效补丁（进生产前的强制卡口）。

**证据**：
- <https://arxiv.org/abs/2608.23041>（AutoSaddler 全部数字与三消融逐字确认；作者含 Microsoft 系署名）
- <https://arxiv.org/abs/2503.13657>（MAST 14 模式、MAST-Data、κ=0.88 人工一致性逐字确认）
- <https://arxiv.org/abs/2410.10762>（AFlow +5.7%/4.55% 成本逐字确认——拓扑在空间内才适用）
- <https://arxiv.org/abs/2502.04180>（MaAS 成本与反超区间逐字确认——不可当单 agent 基线预期）
- <https://github.com/codelion/openevolve>（MAP-Elites/级联评估）
- <https://github.com/harbor-framework/harbor>（容器化评测执行）
- <https://github.com/laude-institute/terminal-bench>（任务三要素）
- <https://arxiv.org/abs/2409.11363>（RE-Bench 时间预算反转——增益按预算分层报告的依据）
- <https://arxiv.org/abs/2503.14499>（METR 时间视界——留出集月度轮换依据；**裁决未打开此链接，按策略自带 caveat 处置**）
- <https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents>（harness 缺陷是真实高频失败源的实证）

**成本**：成本主体=验证评测执行：单轮估 0.5–1 亿 token、数小时墙钟、16–24 并发容器——量级估算须实测。**预算可行性（裁决复核算术成立）：5 轮×3 run 全量 ≈ 4.5–9 亿 token，超年度常态包络（250M/月）——必须跑降级版：1 run×3 轮×缩减子集（约 1.5–3 亿，分 2–3 个月摊）**。节流：积累 ≥30 条新失败轨迹才触发一轮。

**风险**：评估器成攻击面（补丁过拟合回归集/刷分——双门+冻结留出+confirm 一次+verifier 只读挂载+反作弊抽检缓解不根除，重大补丁仍走人工抽检）；**正反馈退化环（坏补丁→harness 变笨→更多失败轨迹→误导下轮诊断，无人值守最危险传播路径）——自动 revert+每轮回归集全跑+全轨迹保留+watchdog 安灯**；留出集过时内卷（月度轮换）；时间预算反转（短预算档不启用自优化）；基线天花板不同（爬坡斜率制而非绝对目标）；MCTS 在参数层空间可能无优势（进化版对照先行）；诊断不替代架构改动；无人值守越权改 verifier（DSL 白名单+静态 lint+越界拦截+安灯）。

**裁决（rank 9 · conditional）**：**条件：(1) 时序后置——必须等基线组合（运行时+门控+三闸+采样基线）稳定后再启动，否则正反馈退化环无人兜底；(2) 只跑降级版（全量算术经裁决复核成立，降级不是可选项而是唯一可行形态）；(3) 硬卡口——verifier 只读挂载+『改 verifier』诱导注入演练必须 0 静默放行才上线；(4) 爬坡斜率制接受。** 价值判断：机制有真实先验（AutoSaddler/AFlow/MaAS 均逐字核实），但它是唯一被优化对象=产线自身的策略，风险不对称：修坏了自己不知道。与 S7 的排序理由：S7 的核心任务类型有确定性门可提前摘果，S9 的收益完全依赖地基稳定。

---

## 5. 独立裁决详情（Step-5 Preview）

### 5.1 裁决方法

裁决者独立于两轮主调研与交叉评审，对 9 个策略逐条：打开 evidence 链接核对关键数字是否逐字存在 → 对两模型评审的分歧独立取证 → 给出 verdict（recommend / conditional）、理由、排名。**凡裁决者声明『逐字确认』的数字均为本次会话实际打开原文核对的结果；凡声明『未核实』的项均如实标注，不冒充已核实。**

### 5.2 逐策略裁决记录

| 策略 | verdict | rank | 证据抽查结果（关键项） |
|---|---|---|---|
| S8 采样聚合 | **recommend** | 1 | 6 条全部逐字核实：Self-Consistency 四项增益、倒U律+解析预测、MoA 65.1% vs 57.5%、强 prompt 单 agent≈最佳讨论、Statistical Scouting（oracle +14.0/+13.7pp 但廉价信号仅 +1.3/+1.7pp 且不显著、66%=31/47、self-critique 零互信息）、More Agents |
| S5 三闸 | **recommend** | 2 | 2408.00989（5.5/10.5/23.7/96.4 全部确认，出处更正采纳正确）；2603.04474（≥89% 确认）；2512.08296 确认；Cognition 多 agent 页确认；OpenHands critic 确认（注意类别措辞漂移：『误判完成』vs 原页『likely user follow-up patterns』，机制成立）；/goal 三态确认。**未逐字核实：MAST judge 管线 0.94/0.77/0.833/0.77 不在摘要页（正文数据，采信但标注）** |
| S1 三查门控 | **recommend** | 3 | 2512.08296 全部数字逐字确认（含 −70.0% 的勘误口径）；2403.02419 确认；building-effective-agents 确认门控原则原文、**确认无 effort-scaling 数字分档**；multi-agent-research-system 确认 coding caveat；MacNet、SIMAS 确认 |
| S2 运行时 | **recommend** | 4 | workflows 七项硬限与恢复语义逐条确认，**纠正：恢复表述无『哈希记账』，须按厂商语义实现**；Devin dynamic workflows 确认；AgentPrune 三组数字逐字确认；Manus（100:1、$0.30 vs $3、mask-don't-remove）逐字确认 |
| S6 黑板续跑 | **recommend** | 5 | Anthropic long-running harness 全部逐字确认（含『看到进展就宣布完工』原话）；Mem0、ACE、Context Rot 逐字确认；**letta sleep-time 页仅确认定性表述与 stateful 前提，5×/2.5×/+13/18% 三个数字不在该页——数字来源存疑，以 arXiv 论文页（2504.13171）与本厂实测为准** |
| S4 分片集成 | **conditional** | 6 | NP-Bench 全部逐字确认（1/9→9/9、13→0、收益来自 work allocation）；AIDev-pop 逐字确认，**纠正：0.5% 是共活对中跨 agent 对占比、4.3%（122/2807）才是仓库占比**；CodeCRDT 确认；**devin agentic-map-reduce 链接 404 且检索不到——该出处不可核实，机制改由 NP-Bench+Devin workflows 双源支撑** |
| S3 星形 | **conditional** | 7 | Anthropic 研究系统（90.2%/15×/80% 方差/coding caveat）逐字确认；2601.11327 确认；Cognition 确认；**Manus Wide Research 为定性描述（第 8–9 项吃紧、第 9 项起 fabricated），无量化切点表——策略表述须改述**；**引文错误：2501.06322 实为多 agent 协作机制综述，非 Anthropic 系统 arXiv 版，该引用删除或更正** |
| S7 研究环 | **conditional** | 8 | AI co-scientist 全文确认六角色+Supervisor+Elo（**78.4% GPQA 一致率未核实到，不作判据**）；2604.18805 逐字确认（41.4% vs 1.5%、68%、26%），**『检测不到 68% 证据忽略』系把一般性结论误述为具体数字，须改正**；CycleResearcher 数字逐字确认（**『共演化』为推断性表述，原文无纵向分析**）；OpenEvolve 逐条确认 |
| S9 自优化环 | **conditional** | 9 | AutoSaddler 全部数字与三消融逐字确认（作者含 Microsoft 系署名——机构 caveat 销项）；MAST 14 模式+κ=0.88 逐字确认；AFlow、MaAS 逐字确认。**未核实（厂内数据或未开链接）：TB4.0 70 判分漏洞+16.4% 作弊率、250M token/月包络、METR 7 个月翻倍（2503.14499 未打开）——按策略已自行标注 caveat 处置** |

### 5.3 被拒/降级策略的完整原因

没有任何策略被整体拒绝；4 个 conditional 的降级原因与翻案条件：

1. **S4（条件化）**：机制本身实证最强，条件只是准入纪律——map 形判定必须以 gate-report 为前置、selector 召回审计达标前不得扩围。两处证据瑕疵（404 链接、0.5% 口径）不致命但必须改正后引用。
2. **S3（条件化）**：证据最弱区间（内部 eval+caveat 点名弱项区+token 无先验）+1 处引文硬伤。翻案条件=地板校验通过且非饱和区；其单写者分支不受此影响（有独立原文支撑）。
3. **S7（条件化）**：不是机制错，是归因风险——六角色结构的边际贡献可能被采样量解释（基座 41.4% vs scaffold 1.5%）。其确定性门已立即并入基线；六角色环只买『是否值得独立存在』一张票（G3'' 消融臂以极小增量回答）。
4. **S9（条件化+时序后置）**：唯一被优化对象=产线自身的策略，正反馈退化环在无人值守下无人兜底；全量成本超包络（算术复核成立）。翻案条件=基线稳定+降级版规模+verifier 只读硬卡口 0 静默放行。

### 5.4 裁决总评

> 9 个策略的证据抽查显示：多数关键数字（2512.08296 的 87%/−70%、2408.00989 的 5.5%/96.4%、NP-Bench 的 1/9→9/9、AgentPrune、Mem0、AutoSaddler 等）本轮均被逐字核实，草案整体证据纪律良好；但存在 3 处硬伤——S3 误挂 2501.06322（实为综述）、S4 的 agentic-map-reduce 链接失效、S6 的 sleep-time 倍数不在所引页面——均已记录并要求更正。批判性审视下，真正的价值集中在四类：防损（S1 门控避 −70% 灾难）、生存（S2 确定性与 S6 跨会话）、兜底（S5 验证分离防静默坏合并）、下限（S8 同预算采样锁质量底线）；而增益型机制（S3 星形、S7 六角色环、S9 自优化）的价值假设均存在被更简单手段解释的高风险，故只给 conditional 并要求其自带的消融/前置条件作为硬门槛。最大单点风险不是任何机制失效，而是 MAST 揭示的 41–86.7% 失败率——选对架构不保证跑通，这更加重了 S5 与节点级 trace 的权重。

两轮评审间分歧的裁决汇总：2408.00989 数字之争（驳回 MiniMax 更正、采纳其出处更正）；文件锁出处（采纳 MiniMax：Cline Kanban）；effort scaling 分档无出处（采纳 MiniMax：降级为待校准先验）；Manus 量化切点（采纳裁决：降格为定性描述）；FastContext 撤稿（按撤稿处置，机制谱系中两数标注未核实）。

---

## 6. 推荐基线 Harness

### 6.1 v1 组合

**S1 门控（入口）+ S2 运行时（执行底座）+ S5 三闸（全局验证层，v1 取最小集：确定性 watchdog 独占合并权 + /goal 会话门 + 合并点冻结上下文评审；critic 环与研究变体花钱门列 v1.1）+ S8 采样基线（强制对照臂兼任务 B 默认改进引擎）+ S6 黑板（长时程状态外化层，取 init.sh / features passes+watchdog 核验 / git 检查点 / epoch fencing；记忆外化层仅对 stateful 跨任务复用开启）。**

### 6.2 两大任务类型的路由逻辑

```
任务进入
  │
  ├─ S1 三查门控（可分解性 / 写独立性 / 可验证性）→ gate-report 落盘
  │
  ├─【任务 A · 大型项目开发】
  │    ├─ map 形（lint/重命名/配置扫描/可枚举迁移）→ S4 确定性分片
  │    │    （NP-Bench 证据最强、token 仅 1.1–1.3×）
  │    ├─ 可分解非 map 形 → S3 星形
  │    │    （必须先过 S0 地板校验；完成率 ≥85% 饱和区自动切 token ≤1.5× 判据）
  │    ├─ 写耦合 → S3 单写者降级分支（单写者 + 只读侦察/冻结评审/smart-friend）
  │    └─ 判不通过 → 降级单 agent 长时程，跑在 S6 上
  │
  └─【任务 B · 评测驱动优化】
       ├─ 默认引擎 = S8：best-of-N + holdout 选择 + 倒 U 停机闸
       ├─ 外层套 S7 的确定性门（三级数据隔离 / citation 要求 /
       │   谱系连带废黜 / confirm 只跑一次）——立即采用，不等六角色结论
       └─ 六角色评审环本身：等 G3'' 消融结论再定（打平即降级为归档+状态机工具）
```

**S9 自优化补丁环推迟到第二阶段**（基线稳定 + 降级版规模 1 run×3 轮 + verifier 只读硬卡口）。

### 6.3 组合理由

| 组件 | 承担的角色 | 一句话依据 |
|---|---|---|
| S2 | 无人值守的确定性与可恢复性 | prompt 编排无确定性可言；厂商 workflow runtime 已验证（[workflows](https://code.claude.com/docs/en/workflows)、[Devin](https://docs.devin.ai/work-with-devin/dynamic-workflows)） |
| S1 | 防止 −70% 灾难路由 | 错误路由的代价区间实测（[scaling science](https://arxiv.org/abs/2512.08296)），门控成本近乎为零 |
| S5 | 兜住静默坏合并（无人值守最致命失效） | 三层验证关键数字全部逐字核实（[2408.00989](https://arxiv.org/abs/2408.00989)、[2603.04474](https://arxiv.org/abs/2603.04474)）；无集中验证传播错误是扩展律三规律之一 |
| S8 | 最低成本锁死质量下限 + 全厂防伪基线 | 任何复杂协议先赢同预算采样-投票（[MoA](https://arxiv.org/abs/2406.04692)、[倒U律](https://arxiv.org/abs/2403.02419)） |
| S6 | 长周期任务跨会话生存 | compaction isn't sufficient（[Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)） |
| S4/S3 | 门控路由出的两种开发拓扑 | map 形分片（[NP-Bench](https://arxiv.org/abs/2610.07261)）；非 map 形星形带硬前置（[Anthropic caveat](https://www.anthropic.com/research/multi-agent-research-system)） |
| S7 门 + S9 | 任务 B 的科学纪律与产线自演进 | 确定性门便宜且有直接支持（[2604.18805](https://arxiv.org/abs/2604.18805)）；自演进等地基稳定（[AutoSaddler](https://arxiv.org/abs/2608.23041)） |

### 6.4 落地要点（裁决附加的实现约束）

1. **S2 用厂商语义实现恢复**：v1 优先采用厂商 workflow runtime 承载拓扑语义（Claude Code workflows 或 Devin dynamic workflows 的语义等价物），自建仅限 hub-spoke/WAL/audit/节点 trace 增量；『哈希记账』按厂商实际语义（缓存已存结果+按启动序重放至首个 prompt 分歧）实现，不自造概念。
2. **KV-cache 纪律是最大单项成本对冲**：prompt 前缀稳定（禁秒级时间戳）、上下文只追加、显式 cache breakpoint、工具 mask-don't-remove（logit 掩码不可用时退化为按阶段固定工具集并标注供应商依赖）（[Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)）。
3. **节点级 trace 强制落盘**（每次调用原始 prompt/response）：防框架抽象层遮蔽底层、无人值守出事可定位——MAST 41–86.7% 失败率下这是与 S5 同权重的保险。
4. **引文纪律**：S3 的 2501.06322 误挂引用删除；S4 的 AIDev-pop 0.5%/4.3% 口径改正后引用；S6 的 sleep-time 数字以 arXiv 论文页为准；S7 的 2604.18805 表述按原文口径改正。
5. **effort scaling 分档（简单事实 1 agent / 对比类 2–4 subagent / 复杂 >10）不硬编码**——出处经核实不存在，仅作待校准先验，进基线后以校准采样数据替换。
6. **lead 汇合硬界（≤5/批）作为工程设计保留但改述**——依据是 Manus 的定性描述而非量化切点表。
7. **墙钟指标按载体分组报告**（GLM 臂 vs 免费/本地/夜间档臂），否则账户并发争抢污染结论。
8. **判分器版本冻结 + fix<N> 代号隔离**：评测器与判分口径永不进补丁可写范围；结果不跨代比较。

---

## 7. 下一步并行测试实验设计

统一格式：任务集 → 分组（臂）→ 指标 → 判胜/判停 → L0 与前置 → 成本。所有实验共用纪律：每任务 ≥3 种子、配对统计（McNemar/混合效应）、事先功效分析（BenchAgent 提示真实效应量可能仅个位数 pp）、L0 机制体检 + 首轮标 trial 不进决策、组合态冒烟（单策略结论须在最小组合态上复验 1 任务后才进决策级）、token 记三账本并报占年度包络百分比。

### E1 · S1 三查门控与并行度求解
- **任务集**：预注册混合任务池 14 个（8 开发 + 6 评测优化，三查标签由两名标注者独立给出、分歧仲裁后冻结）。
- **分组**：同池四臂（**含被拒任务，防选择偏误**）：R0 全部硬上多 agent；R1 全部单 agent；R2 门控路由；R3 门控+并行度求解器 vs 固定 K（K∈{2,4,8,16} 子集扫描绘曲线）。
- **指标**：各臂完成率、token、墙钟；门控混淆矩阵（对留出子集事后穷举最优架构）；求解器预测 N vs 扫描最优 N；拒绝率与各查通过率单独报告。
- **判胜/判停**：加权完成率 +≥10pp；拒绝集上被强行臂相对被路由臂差 ≥10pp；路由与穷举最优一致率 ≥70%；N 偏差 ≤1 档且 token −30%。
- **L0**：门控确定性体检（同输入两次产出同 gate-report、schema 校验）。
- **成本**：占年度包络 5–8%，超支先砍种子再砍任务数。

### E2 · S2 代码化编排运行时
- **任务集**：3 个真实长时程任务（每任务 ≥30 次 agent 调用、跨 2–4 小时），每臂注入同一脚本定义的 5 类故障（工具超时、schema 违例、usage limit、输出截断、进程真杀）。
- **分组**：A=prompt 驱动星形+整图快照恢复（最强廉价对照）；B=代码化 runtime 无恢复记账（故障后整图重跑）；C=完整本策略；D=C+类型化信道+AgentPrune 剪枝（通信治理增量）。
- **指标**：故障后自动恢复成功率（对照干净跑 commit 图+测试等价性）；恢复时长、恢复 token、B/C 重复执行比、无人工干预完成任务数、缓存命中率（全臂遥测）、编排层 token 占比；task ledger『猜测混入已核实栏』次数（人工抽 50 条）作二级安全指标。
- **判胜/判停**：恢复成功率 ≥80%、恢复 token ≤ 快照臂 60%/重跑臂 20%（工程目标已标注无文献先验）；**C 若不显著优于 A，结论登记『恢复记账增量不成立』，产线退回快照方案**。
- **L0**：重放确定性体检（同脚本跑两次，第二次零模型调用）+ hook 自检。
- **成本**：占年度包络 3–5%；降级版砍至 2 任务×3 类故障。

### E3 · S3 双账本星形（前置门最致命）
- **前置门**：先跑 fix1 代单 agent 基线并与商业 harness 对齐（50-方案 §9.7 合格判据），地板不过则本实验顺延；多 agent 臂顺手修掉的 harness 缺陷按 §9.3 bump 代号隔离，结果不跨代比较。
- **任务集**：自建多模块任务（12–20 模块、5–8 跨模块契约、注入语义陷阱，登记规格与标注成本）+ SWE-V D2/D3 过滤子集（全量 SWE-V 禁用——gold patch 中位 1 文件/183 字符主要测单点修复）。
- **分组**：五臂同池：S0 校准单 agent；N0 朴素自由委派；G1 本策略全量；G1-abl 去汇合硬界；G2 写耦合子集单写者 vs 多写者对照；D 同预算 best-of-N（强制基线臂）。
- **指标**：功能完成率、回归正确率、墙钟、token 三账本、失败可定位率、编造征兆率（引用不存在实体比例）、跨 agent 集成失败数。
- **判胜/判停**：见 §4 S3 假设栏；S0 ≥85% 饱和区自动切 token ≤1.5× 判据。
- **L0 + 组合态**：机制体检+trial；G1 于运行时+三闸组合态跑 1 任务后再进决策级。
- **成本**：占年度包络 10–15%；降级版 5 任务×2 种子。

### E4 · S4 分片-隔离-集成（两实例并行）
- **开发实例**：6–8 个 map 任务按 GT 类型二分（唯一 GT：lint 落地/重命名；无唯一解：迁移/重构，GT=等价类、判据换可执行三件套），注入跨模块语义陷阱。四臂：S0 串行同预算；N0 朴素并行 swarm；M1 完整本策略；M1-abl 去确定性 selector 改 LLM 定位。
- **评测实例**：真实选型矩阵切片（≈1000+ 配置单元），GT=离线叉积清单+离线标准聚合。三臂 S0/N0/M1 + M2=金丝雀关闭+首 shard 注坏对照（验证金丝雀拦截）。
- **指标**：合并冲突数、干净集成比例、召回率（唯一 GT 类）/可执行判据通过率（无唯一解类）、覆盖率、记录保真率（5% 抽样对拍）、整合正确率、墙钟、token。
- **判胜/判停**：见 §4 S4 假设栏；整合正确率落后 >5pp 裁决『只赢执行不赢结论』。
- **适用性注记**：适用处设采样-投票臂（评测实例复制验证臂），开发实例标注不适用并说明理由（投票是生成端机制，不解决集成调度）。
- **成本**：占年度包络 8–12%（评测实例主导）。

### E5 · S5 三闸（叠加式）
- **任务集**：固定底层生成策略（星形/分片获胜臂）只变验证层。三块：SWE-V D2/D3 过滤子集 + 自建注错集（20 处已知位置缺陷：边界/契约破坏/竞态/半截处理，另加语义类：自洽误读实现、错误但过测的测试）+ 弱可验证类（重构/命名——不进三闸、路由采样-投票+留出集）。
- **分组**：六臂：C0 无门自评自合并；C1 全量三闸；C2 消融（评审共享上下文）；C3 消融（去 watchdog、模型判合并——即『watchdog 外壳 vs agent integrator』收敛点对照）；C4 研究变体（固定 proposer 池只换门）；D 采样-投票同预算（只比质量轴，门控轴单独计量——投票是生成端机制不能行使拦截职能）。
- **指标**：注错存活到合并率（分机械类/语义类报告）、合并后回归失败率、门 precision/recall 对账账本、修复循环轮数、token、墙钟；反向测试 5 注入/臂。
- **判胜/判停**：见 §4 S5 假设栏；**C1 不优于 C3 则登记『确定性终审增量不成立』**。
- **L0**：钩子单测+反向注入演练。
- **成本**：占年度包络 6–10%。

### E6 · S6 黑板续跑
- **任务集**：4 个标称 ≥6 小时长程任务（完整子系统从规格到测试全绿），随机点强杀 3–5 次/任务、覆盖三种死法（进程杀/上下文截断/模型切换）。
- **分组**：六臂：D0 公平对话交接基线（git log+重读仓库，无清单/无冒烟/无记忆）；D1 弱桥接（仅 git 检查点）；D2 完整本策略；D3 消融（去冒烟门）；D4 消融（去记忆层）；D5 消融（去 effect fencing）。
- **指标**：恢复正确率、重做率、坏状态接手数、副作用重放数、单次恢复开销时长（≤总时长 10%）、总 token、记忆复用增量（D2 vs D4 在第 2/3/4 任务上的差）。
- **判胜/判停**：见 §4 S6 假设栏；D2 vs D0 <40pp 则按基线实测值重新归一（基线强则看 D3/D4/D5 消融差），不以绝对值为唯一判据。
- **L0**：钩子自测+epoch fencing 演练（回滚后重放旧纪元请求必须 100% 拒绝）+两类篡改注入演练（passes 位伪造与测试文件改写都要拦截）。
- **成本**：占年度包络 10–15%；降级版 2 任务×2 种子。

### E7 · S7 假设池研究环（全清单最贵，降级版先行）
- **前置**：评估器准入考卷先行（原则 4）+池状态机迁移穷举测试。
- **任务集**：产线现成确定性判分优化任务（档位映射按 50-方案 :81-82 校正：TB 任务属 D3/D4、SWE-V 属 D1/D2）：T1 完成度纪律缺陷率降半；T2 TB 短任务 40 轮不收敛的停止策略；T3 cascade 升级信号配方双目标；T4 s1-swev-120 子集通过率。
- **分组**：五臂×≥5 种子：G1 单 agent 串行环（fix1 校准）；G2 朴素多 agent（同角色自由聊天）；G3 本策略；G3' 去 citation 门；**G3'' 同预算纯采样无评审环（证伪臂，必须同跑）**。臂名不复用策略名（变更日志登记）。
- **判分**：pass^k≥4+误差棒，失败按 MAST 14 类标注；bootstrap 95% CI、主指标比值型（每美元有效改进数）+配对设计。
- **判胜/判停**：见 §4 S7 假设栏；G3'' 打平即否证登记、六角色环降级为归档+状态机工具。
- **成本**：占年度包络 15–20%（最贵）；**降级版 3 任务×3 种子（约减 60%）先行**。

### E8 · S8 采样聚合（全厂基线臂复用）
- **任务集**：6 个优化任务（D1/D2/D3 各 2 个，难度分层按 50-方案 §2.1；任务=优化对象+dev 评测脚本+冻结 holdout 三件套）+研究变体。
- **分组**：3 臂×5 种子（G0 单 agent best-of-N / G1 朴素群聊 / G2 采样投票）+研究变体五臂组（G0–G4：采样+聚类+视角切片，G2–G4 用完全相同 proposer 池与种子只换聚合分派环节——差异只能归因协作机制）。
- **指标**：holdout 最优分、分数-调用数曲线（验证倒 U 被闸住）、墙钟（按载体分组）、token 三账本、候选 diff 多样性、distinct hypothesis rate、协调开销占比。
- **判胜/判停**：见 §4 S8 假设栏；难档若 <串行−2pp，先看曲线平台期区分『停机闸超参需重调』与『机制失败』，前者不判负但记录为超参依赖证据。
- **复用**：本策略臂同时作为星形/分片/研究环各实验的强制基线臂嵌入同任务池，不重复跑。
- **成本**：占年度包络 5–8%。

### E9 · S9 自优化补丁环（第二阶段）
- **前置**：基线组合稳定后启动；DSL 白名单静态 lint 自检+verifier 只读挂载验证+『改 verifier』诱导注入演练 0 静默放行。
- **分组**：四臂×3 独立 run×5 轮（**降级版 1 run×3 轮先行，全量算术超包络已复核**）：G1 静态 fix1 冻结；G2 人工循环基线（现运行形态）；G3 自动化本策略；G3' 消融（随机/无约束补丁，检验『定向修改优于无约束编辑』）。
- **任务三分**：优化集（Miner 可见）/泛化留出（仅 Judge 可见、月度轮换含新题）/冻结回归集（每轮全跑）；判分 pass^k≥4+三账本+误差棒。
- **指标**：优化/留出/confirm 三集通过率轨迹与爬坡斜率、补丁采纳率、每周验证吞吐、回滚率、每采纳补丁 token、失败模式分布随轮迁移。
- **判胜/判停**：见 §4 S9 假设栏；判负条件=留出集较 G1 掉 >1pp 或回滚率 >30%（双门失效证据）。补丁环自身受安灯监视；期间旧代结果按 §9.3 隔离。
- **成本**：降级版约 1.5–3 亿 token 分 2–3 个月摊，并入月度常态化节奏；节流=积累 ≥30 条新失败轨迹才触发一轮。

---

## 8. 附录：全部入选来源链接

核实状态说明：`verified`=原文打开且关键表述核对一致；`corrected`=原引用有出入、已按原文更正后收录；`未核实项`=链接打开但特定数字不在页面/摘要（已在正文标注）。厂内文件（40-计划、50-方案、fix1、af 内核、UndoBench 实测、L0-1 件等）为文字引用，非外部链接。

### 8.1 论文（含基准测评）

- [AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation](https://arxiv.org/abs/2308.08155) — conversation programming 奠基：协作拓扑用代码编排
- [Magentic-One: A Generalist Multi-Agent System](https://arxiv.org/abs/2411.04468) — task/progress 双 ledger、卡死→反思→重规划；GAIA 38%
- [MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework](https://arxiv.org/abs/2308.00352) — SOP 编码进 prompt 序列、结构化产物抑制级联幻觉（ICLR 2024）
- [ChatDev: Communicative Agents for Software Development](https://arxiv.org/abs/2307.07924) — chat chain + communicative dehallucination（ACL 2024）
- [CAMEL: Communicative Agents for "Mind" Exploration](https://arxiv.org/abs/2303.17760) — role-playing + inception prompting 奠基（NeurIPS 2023）
- [AgentScope 1.0: A Developer-Centric Framework](https://arxiv.org/abs/2508.16279) — actor 分布式+统一事件总线架构论文
- [Why Do Multi-Agent LLM Systems Fail? (MAST)](https://arxiv.org/abs/2503.13657) — 14 失败模式 3 大类、7 框架 41–86.7% 失败率、干预 +9.4%/+15.6%、κ=0.88
- [AgentVerse: Facilitating Multi-Agent Collaboration](https://arxiv.org/abs/2308.10848) — Group 两任务输给 Solo、约 10% 从众错误（GPT-4 无）
- [DyLAN: A Dynamic LLM-Powered Agent Network](https://arxiv.org/abs/2310.02170) — Agent Importance Score 动态组队（COLM 2024）
- [Language Agents as Optimizable Graphs (GPTSwarm)](https://arxiv.org/abs/2402.16823) — agent 即可优化计算图（ICML 2024）
- [Scaling Large Language Model-based Multi-Agent Collaboration (MacNet)](https://arxiv.org/abs/2406.07155) — logistic 增长、不规则拓扑更优、上千 agent（ICLR 2025）
- [AFlow: Automating Agentic Workflow Generation](https://arxiv.org/abs/2410.10762) — MCTS over workflow、六基准 +5.7%、小模型 4.55% 成本反超
- [Automated Design of Agentic Systems (ADAS)](https://arxiv.org/abs/2408.08435) — meta agent 编程发明新 agent、跨域迁移
- [Cut the Crap (AgentPrune)](https://arxiv.org/abs/2410.02506) — 通信冗余 one-shot 剪枝：$43.7→$5.6、token −28.1~72.8%、对抗 +3.5~10.8%
- [FlowReasoner: Reinforcing Query-Level Meta-Agents](https://arxiv.org/abs/2504.15257) — 多目标 RL 训练 query-level meta-agent、超 o1-mini 10.52%
- [Should we be going MAD?](https://arxiv.org/abs/2311.17371) — 辩论不能可靠超过 self-consistency、超参敏感（未做同 token 预算对齐）
- [Multi-Agent Architecture Search via Agentic Supernet (MaAS)](https://arxiv.org/abs/2502.04180) — 架构分布按难度采样、成本 $6~45%
- [Optima: Optimizing Effectiveness and Efficiency for LLM-Based MAS](https://arxiv.org/abs/2410.08115) — generate-rank-select-train；Llama3 8B 2.8×、token<10%（特定骨干，corrected）
- [Mixture-of-Agents Enhances LLM Capabilities](https://arxiv.org/abs/2406.04692) — 纯开源 MoA AlpacaEval 2.0 65.1% vs GPT-4 Omni 57.5%
- [MultiAgentBench: Evaluating Collaboration and Competition](https://arxiv.org/abs/2503.01935) — 四种协调拓扑+里程碑 KPI；graph 结构 research 场景最好
- [More Agents Is All You Need](https://arxiv.org/abs/2402.05120) — 纯采样投票随实例数提升、与复杂方法正交（TMLR）
- [Multiagent Debate (Du et al.)](https://arxiv.org/abs/2305.14325) — 3 agent 2 轮、无裁判、与 CoT 正交（corrected：无裁判 agent）
- [Debating with More Persuasive LLMs](https://arxiv.org/abs/2402.06782) — 说服力追踪真相；模型裁判 48%→76%
- [Are More LLM Calls All You Need?](https://arxiv.org/abs/2403.02419) — Vote/Filter-Vote 倒 U 扩展律、解析预测最优调用数
- [Can Small Agents Collaborate to Beat a Single LLM?](https://arxiv.org/abs/2601.11327) — orchestrator 容量驱动、子 agent 推理收益有限/为负
- [Statistical Scouting](https://arxiv.org/abs/2605.09618) — 投票已解释辩论收益、廉价信号失效、66% 有益辩论在投票一致但错误时
- [Not All Flips Are Conformity](https://arxiv.org/abs/2606.00820) — 37% 翻转无同伴信息也发生、完整推理辩论无投票收益多花 57% token
- [BenchAgent: Do More Agents Help?](https://arxiv.org/abs/2606.05670) — 六工作流仅 EvoAgent 胜出；ChatEval 4.34× token 仍落后
- [Multi-Agent Collaboration Mechanisms: A Survey](https://arxiv.org/abs/2501.06322) — 协作机制五维综述（**注意：曾被误挂为 Anthropic 系统 arXiv 版，已纠正**）
- [ChatEval: Better LLM-based Evaluators through Multi-Agent Debate](https://arxiv.org/abs/2308.07201) — persona 评审团、角色多样性是收益来源（53.8 vs 60.0）
- [Self-Consistency Improves CoT Reasoning](https://arxiv.org/abs/2203.11171) — GSM8K +17.9% 等（ICLR 2023，经典奠基）
- [LLMs Cannot Self-Correct Reasoning Yet](https://arxiv.org/abs/2310.01798) — 无外部反馈自纠有时更差（ICLR 2024）
- [AI scientists produce results without reasoning scientifically](https://arxiv.org/abs/2604.18805) — 基座 41.4% vs scaffold 1.5% 方差、68% 轨迹忽略证据
- [MAD: Encouraging Divergent Thinking](https://arxiv.org/abs/2305.19118) — 裁判+tit-for-tat 治思维退化（EMNLP 2024）
- [AI co-scientist](https://arxiv.org/abs/2502.18864) — Supervisor+六角色+Elo 锦标赛（corrected：原 research.google 链接不可达，改论文版）
- [CycleResearcher: Improving Automated Research via Automated Review](https://arxiv.org/abs/2411.00816) — CycleReviewer MAE 低 26.89%（ICLR 2025）
- [The AI Scientist-v2](https://arxiv.org/abs/2504.08066) — 渐进式树搜索+VLM 反馈、首篇过同行评审全 AI 论文
- [Robin: automating scientific discovery](https://arxiv.org/abs/2505.13400) — 文献+数据分析 agent 闭环、ripasudil→ABCA1
- [Agent Laboratory](https://arxiv.org/abs/2501.04227) — 全自主省 84% 成本但人类反馈显著提升质量
- [The AI Scientist](https://arxiv.org/abs/2408.06292) — 全自动科研 <$15/篇、模拟评审近人类
- [AI Research Agents for ML (MLE-bench/AIRA-Dojo)](https://arxiv.org/abs/2507.02554) — 搜索策略形式化、奖牌率 39.6%→47.7%、千 agent 并行 120h（corrected→verified）
- [AlphaEvolve](https://arxiv.org/abs/2506.13131) — 4×4 复矩阵乘 48 次标量乘、56 年来首次改进 Strassen 设定
- [MLAgentBench](https://arxiv.org/abs/2310.03302) — 最强 agent 37.5%、新 Kaggle 挑战低至 0%
- [RE-Bench](https://arxiv.org/abs/2411.15114) — 2h 预算 AI 为人类 4×、32h 人类反超 2×（corrected→verified）
- [CORE-Bench](https://arxiv.org/abs/2409.11363) — 计算复现基准、最难档最好 21%
- [AutoSaddler](https://arxiv.org/abs/2608.23041) — harness 自优化：+9.0/+9.6/+10.0pp、三消融结论
- [Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296) — 260 配置、R²=0.373、87%、+80.8%~−70.0%、三规律
- [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) — 虚拟上下文管理、interrupts 换页
- [Sleep-time Compute](https://arxiv.org/abs/2504.13171) — 同精度 ~5× 省、摊销 2.5×、固定预算 +13/18%（corrected：数字在论文页非 Letta 博客）
- [Measuring AI Ability to Complete Long Software Tasks (METR)](https://arxiv.org/abs/2503.14499) — 时间视界每 7 个月翻倍（v4 2026-07）
- [Mem0: Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413) — LOCOMO p95 −91%、token −90%+、+26%
- [Voyager: Open-Ended Embodied Agent](https://arxiv.org/abs/2305.16291) — 可执行技能库 3.3×/15.3×
- [MIRIX: Multi-Agent Memory System](https://arxiv.org/abs/2507.07957) — 六类记忆、ScreenshotVQA +35%、存储 −99.9%
- [Agentic Context Engineering (ACE)](https://arxiv.org/abs/2510.04618) — playbook 增量更新、agents +10.6%（ICLR 2026）
- [Lost in the Middle](https://arxiv.org/abs/2307.03172) — U 形位置偏置（TACL 2023，经典奠基）
- [Multi-Agent Risks from Advanced AI](https://arxiv.org/abs/2502.14143) — miscoordination/conflict/collusion 三类失效+七类风险因子
- [On the Resilience of LLM-Based Multi-Agent Collaboration with Faulty Agents](https://arxiv.org/abs/2408.00989) — 层级降幅最小 5.5% vs 10.5%/23.7%、Challenger/Inspector 挽回 96.4%
- [Hallucination Cascade](https://arxiv.org/abs/2606.07937) — 级联幻觉 0.422→0.272 但事实 0.789→0.769 的权衡
- [From Spark to Fire](https://arxiv.org/abs/2603.04474) — 原子错误种子扩散、三类脆弱性、genealogy-graph ≥89% 阻止感染
- [CodeCRDT](https://arxiv.org/abs/2510.18893) — 观测驱动协调：100% 收敛零 merge 失败但最高 39.4% 减速
- [AI Agent Pull Requests on GitHub (AIDev-pop)](https://arxiv.org/abs/2607.04697) — 33,596 PR 实证：跨 agent 冲突 41.7% vs 19.8%、0.5%/4.3% 口径
- [NP-Bench and a Scheduling Planner](https://arxiv.org/abs/2610.07261) — 干净集成 1/9→9/9、merge 13→0、收益来自任务分配
- [Scaling Behavior of Single LLM-Driven Multi-Agent Systems (SIMAS)](https://arxiv.org/abs/2606.00655) — 性能不随 agent 数单调、需足够强基座
- [Silo-Bench](https://arxiv.org/abs/2603.01045) — Communication-Reasoning Gap、协调开销随规模复利
- [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) — 自改 scaffold：archive 采样+变体+基准验证
- [The MiniMax-M2 Series](https://arxiv.org/abs/2605.26494) — Forge 自演化：自主调试 run 并修改自身 scaffold
- [Kimi K2](https://arxiv.org/abs/2507.20534) — MuonClip 优化器、15.5T token 零 loss spike
- [MirrorCode](https://arxiv.org/abs/2606.30182) — 只给行为复现整个程序的长程编码基准、最强 56%
- [FastContext](https://arxiv.org/abs/2606.14066) — **v4 已撤稿（product IP issues、无 PDF）；摘要仅 resolution +5.5% / token −60%；按撤稿处置**
- [Coscientist: Autonomous chemical research (Nature 2023)](https://www.nature.com/articles/s41586-023-06792-0) — Planner 四命令动作空间驱动自动化实验（逐字核实）

### 8.2 开源项目

- [LangGraph](https://github.com/langchain-ai/langgraph) — Pregel 式低层编排；Send (types.py:738)、Command (:833)、BaseCheckpointSaver（行号已核实）
- [langgraph-supervisor](https://github.com/langchain-ai/langgraph-supervisor) — 官方弃用声明：改推荐工具式 supervisor 模式
- [Microsoft AutoGen（已归档）](https://github.com/microsoft/autogen) — Project archived；新用户从 MAF 起步；AutoGenBench
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) — sequential/concurrent/handoff/group 四图模式+checkpointing+OpenTelemetry（corrected：MCP 互操作表述出自 AutoGen/SK README 非 MAF 本体）
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) — agents/handoffs/guardrails 三原语；Handoff input_filter (handoffs/__init__.py:158)（corrected：Swarm 取代声明在 openai/swarm README）
- [CrewAI](https://github.com/crewAIInc/crewAI) — Crews+Flows 双抽象、hierarchical process、@start/@listen/@router
- [Google ADK](https://github.com/google/adk-python) — Sequential/Parallel/LoopAgent 确定性 workflow agents + AutoFlow（corrected：LlmAgent 行号更正）
- [AgentScope](https://github.com/agentscope-ai/agentscope) — actor 分布式、SOP/TeamPipeline 一级特性、A2A 协议
- [AG2](https://github.com/ag2ai/ag2) — Hub（registry/WAL/audit trail）+ 四类类型化信道 + TransitionGraph
- [LlamaAgents（原 workflows-py）](https://github.com/run-llama/llama-agents) — 事件驱动编排、纯 Python 无 DSL（corrected：原 URL 301 已改跳转目标）
- [OpenEvolve](https://github.com/codelion/openevolve) — MAP-Elites、5 孤岛、artifact 侧信道、级联评估
- [Terminal-Bench](https://github.com/laude-institute/terminal-bench) — 任务=指令+验证测试+oracle 解三要素、tb run CLI、排行榜 tbench.ai
- [Harbor](https://github.com/harbor-framework/harbor) — 容器化 provider 统一、--n-concurrent、可产 RL rollouts、直评真实 agent

### 8.3 工业实践（厂商工程博客与官方文档）

- [How we built our multi-agent research system（Anthropic）](https://www.anthropic.com/research/multi-agent-research-system) — 90.2% 内部 research eval、15× token、token 解释 80% 方差、coding caveat、effort scaling 叙述（corrected：规范地址；[旧 engineering URL](https://www.anthropic.com/engineering/built-multi-agent-research-system) 301 跳转至此）
- [Building effective agents（Anthropic）](https://www.anthropic.com/engineering/building-effective-agents) — 五种 workflow 模式分类学、『能不建就不建』门控原则、框架抽象层警告（**核实：无 effort scaling 数字分档**）
- [Effective context engineering for AI agents（Anthropic）](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) — attention budget、compaction/结构化笔记/多 agent 三类技术、just-in-time 检索
- [Effective harnesses for long-running agents（Anthropic）](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — init.sh/进度文件/passes JSON/git 检查点、compaction isn't sufficient
- [Claude Code on the web / Cloud sessions（Anthropic）](https://www.anthropic.com/news/claude-code-on-the-web) — 云端隔离沙箱并行会话、2026-09 更名 GA
- [Don't Build Multi-Agents（Cognition, 2025-06-12）](https://cognition.com/blog/dont-build-multi-agents) — 两条原则、Flappy Bird 反例、单线程线性 agent 主张
- [Multi-Agents: What's Actually Working（Cognition, 2026-04-22）](https://cognition.com/blog/multi-agents-working) — 收窄反转：writes stay single-threaded、三分支、manager/child 三缺陷、Devin Review 每 PR 约 2 bug/58% 严重
- [Devin can now Manage Devins（Cognition）](https://cognition.ai/blog/devin-can-now-manage-devins) — 每子会话独立 VM、git branch+结构化输出交接、协调者读子轨迹
- [Agentic MapReduce（Devin）](https://devin.ai/blog/agentic-map-reduce) — 确定性 selector 分片三段式（**裁决核实：链接 404 失效，机制由 NP-Bench+Devin workflows 双源支撑**）
- [Devin Dynamic Workflows（官方文档）](https://docs.devin.ai/work-with-devin/dynamic-workflows) — 确定性脚本编排、独立 VM、恢复记账、失败处置
- [Claude Code: Dynamic workflows](https://code.claude.com/docs/en/workflows) — 硬限（16/256、4096、1000、禁随机/时间）、stall≤5、恢复语义（**无『哈希记账』表述，按厂商语义实现**）
- [Claude Code: Run agents in parallel](https://code.claude.com/docs/en/agents) — 五种并行形态总览
- [Claude Code: Agent teams](https://code.claude.com/docs/en/agent-teams) — 实验特性、共享任务表、mailbox、hook 质量门、已知局限自认（**此页无文件锁**）
- [Claude Code: Worktrees](https://code.claude.com/docs/en/worktrees) — 一会话一 worktree、.worktreeinclude、退出清理规则
- [Claude Code: /goal](https://code.claude.com/docs/en/goal) — 会话级完成条件环、三态判定、四类致命错误清 goal
- [Claude Code: Sub-agents](https://code.claude.com/docs/en/sub-agents) — 上下文白名单、15000 token 告警、agent ID+SendMessage 续跑
- [OpenHands: Software Factory](https://docs.openhands.dev/openhands/usage/use-cases/software-factory) — triage/developer/reviewer/watchdog 四段式、exact-head、最小权限、实跑记录
- [OpenHands: Hooks](https://docs.openhands.dev/openhands/usage/customization/hooks) — exit 0/2 语义、Stop 强制、与 Claude Code hooks 兼容
- [OpenHands: Critic](https://docs.openhands.dev/openhands/usage/agent-canvas/critic) — 回合末打分、0.6/3 轮、ACP 第三方不走 critic
- [Cline: Hub-Spoke Architecture](https://docs.cline.bot/sdk/architecture/hub-spoke) — hub 不跑 loop、client 能力注册、断开 spoke 继续
- [Cline: Multi-Agent Teams](https://docs.cline.bot/sdk/guides/multi-agent-teams) — teams.db 持久化、全量 team_* 工具、适用边界自限
- [Cline: Kanban](https://docs.cline.bot/usage/kanban) — 一卡一 worktree、依赖链、文件锁认领（**文件锁出处在此**）
- [Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) — KV-cache 一等指标（100:1、$0.30 vs $3）、前缀稳定、mask-don't-remove、压缩可还原、失败轨迹保留
- [Wide Research: Beyond the Context Window（Manus）](https://manus.im/blog/manus-wide-research-solve-context-problem) — 单上下文编造模式定性描述、架构切换解法（**定性非量化切点**）
- [Context Rot（Chroma）](https://www.trychroma.com/research/context-rot) — 18 模型控制实验：性能随输入长度不可靠下降、语义检索退化更重
- [Sleep-time Compute / Letta 2.0](https://www.letta.com/blog/sleep-time-compute) — sleep-time agent 双 agent 结构、记忆编辑职责剥离（**5×/2.5×/+13/18% 不在此页，见 arXiv 2504.13171**）
- [FunSearch（DeepMind）](https://deepmind.google/discover/blog/funsearch-making-new-discoveries-in-mathematical-sciences-using-large-language-models/) — LLM+自动 evaluator 配对、cap set 20 年最大增量、进化并行化
- [Measuring AI Ability to Complete Long Tasks（METR 博客）](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/) — 时间视界 logistic 拟合、翻倍约 7 个月（corrected：论文为每对约 8 次、无系统性 reward hacking 排查）

---

*报告完。统计：入选策略 9 条（5 recommend + 4 conditional）、机制谱系主题 20 个、外部来源链接 110+ 条（论文 70 / 开源项目 13 / 工业实践 27，含 1 条撤稿与 2 条失效/降格标注）。*

