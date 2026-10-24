<!-- TARGET: AutoGen（v0.4+ autogen-agentchat）的声明式 Team 配置（可序列化为 JSON）：RoundRobinGroupChat / SelectorGroupChat / MagenticOne 等团队拓扑、termination conditions、participant agent 声明 -->

## ① 核心机制

AutoGen v0.4 把多智能体系统从"脚本化对话"重构为**事件驱动参与者 + 消息主题 + 声明式团队拓扑**三层结构：Runtime 承载 Topic/AgentId 负责发布与订阅，Agent 是纯粹的消息处理器（system prompt + ModelClient + tools + memory + 私有状态），而 Team 是驱动引擎——它持续从共享消息流中决定"下一个发言者"，把装配好的上下文交给该参与者，接收其产出的消息后循环，直到终止条件判定停止。其核心洞见是：**"谁与谁连接"被抽象成"选择策略"而非消息连线**，因此拓扑（RoundRobin / Selector / MagenticOne / Swarm / Graph）、终止判据（termination conditions）、参与者能力（模型/工具/记忆）三者都是可独立声明、可序列化（`Team.to_config()` → dict）的数据对象，使多智能体编排从硬编码脚本变成可持久化、可复现、可复用的资产。

## ② 组件清单

| 组件 | 类型 | 职责 |
|---|---|---|
| AssistantAgent / UserProxyAgent / CodeExecutorAgent / SocietyOfMindAgent | 参与者节点 | 各自执行单元；前者通用 LLM 参与者，后两者分别承担人在回路与代码执行回传 |
| Team（BaseGroupChat） | 编排器 | 持有 group_chat 与发言者选择策略，产出 stop_reason |
| RoundRobinGroupChat | 拓扑 | 固定轮转，严格一人一句 |
| SelectorGroupChat | 拓扑 | 由模型（可选自定义 selector_func）根据消息上下文选择下一发言者 |
| MagenticOneGroupChat | 拓扑 | 编排器 + 工作者 + 账本 + 停滞检测 + 重规划 |
| Swarm | 拓扑 | 工具调用触发 handoff 的交接式协作 |
| GraphFlow / DiGraphBuilder | 拓扑（实验性） | 有向图 + 条件激活边 |
| TerminationCondition 家族 | 停止谓词 | 订阅消息流，命中即终止团队 |
| Message 类型 | 通信单元 | Text / UserInput / FunctionCall / FunctionExecutionResult / Handoff / Stop |
| Memory | 上下文源 | ListMemory、MemoStore、ChromaDBMemory |
| Tool | 动作端口 | FunctionTool、CodeExecutorTool |
| Runtime / Topic / AgentId | 通信层 | 发布订阅与参与者寻址 |
| TeamState / AgentState | 状态 | `save_state()` / `load_state()` 可快照恢复 |

## ③ 数据与上下文流

- **Team 是唯一的上下文装配者**：每回合从团队消息缓冲区取共享消息流，按参与者描述与 system prompt 组装模型上下文，并附上工具 schema。
- **两条并行上下文线**：团队共享消息流（公开）+ 每个 Agent 的私有 memory（仅自己检索并注入）。可见性由订阅关系决定，而非由图连线决定。
- **消息单向广播**：Agent 只向 Topic publish，不直接调用他人；"下一个发言者"的裁决权在 Team，或委托给模型/selector_func。
- **工件交接**：代码执行结果、文件路径、结构化负载均以消息体在流中移交；MagenticOne 的 task ledger / progress ledger 属编排器私有结构化状态，跨回合更新且不混入普通消息历史。
- **状态位置**：Team 持消息缓冲与各参与者状态，`save_state()` 输出可 JSON 化 dict（消息、agent state、ledger）；`to_config()` 只暴露静态声明，不含运行态。

## ④ 失败处理与停止条件

- MaxMessageTermination：消息条数上限
- TokenUsageTermination：跨参与者累计 token 超限
- TimeoutTermination：墙钟超时
- TextMentionTermination：命中关键词文本（如 "TERMINATE"）
- SourceMatchTermination：指定来源（如 user proxy）发言
- HandoffTermination：交接给指定 agent
- FunctionCallTermination：调用指定终止函数
- ExternalTermination：外部 `set()` 取消
- 组合语义：`|`（任一）与 `&`（全部满足）；`stop_reason` 返回命中者
- 重试/容错：ModelClient 内置 `max_retries`；代码异常转为错误消息回灌而非崩溃；UserProxyAgent 阻塞等待，超时按错误处理
- MagenticOne：停滞检测判定无进展即触发重规划（重写 plan、更新 ledger 与 notes），stall 累计超 `max_stalls` 终止；编排器判定不可行则宣告失败
- GraphFlow：条件激活可成环，靠条件边与终止/最大步数跳出

## ⑤ 预算与评估方式

- 轮次预算 = MaxMessageTermination；token 预算 = TokenUsageTermination（依赖 provider 返回的 usage 累计）；时间预算 = TimeoutTermination；结构化预算 = MagenticOne 的 max_turns / max_stalls / max_round_span 与各 Agent 的 `max_tokens`
- 无静态成本模型：花费只能事后统计，DSL 侧无法在声明期预估
- 评估：官方主战场为 GAIA（官方报告 pass@1 约 24.7%，随版本与是否含人工协助变化，**存疑**），另涉 WebArena / ALFWorld 等网页与具身环境（**存疑**是否列入主表）；消融集中在 ledger/编排器有无、停滞重规划开关、不同 coder 组合（论文有对比，具体表号记不清，**存疑**）；框架侧提供 AutoGenBench 做跨模型、跨实现的统一 agent 评测

## ⑥ DSL 表达点清单

**(a) 可映射为"标准拓扑 + 组件"**

1. RoundRobinGroupChat → 环形拓扑 + 轮转调度器
2. SelectorGroupChat → 路由拓扑（选择策略节点）
3. MagenticOneGroupChat → 层级拓扑：编排器节点 + 工作者节点 + 共享账本 + 重规划转移
4. Swarm → 交接拓扑（handoff 作状态转移边）
5. GraphFlow/DiGraphBuilder → 有向图拓扑 + 条件激活边
6. TerminationCondition 家族 → 循环守卫谓词（消息/token/超时/文本/来源/handoff/函数调用/外部取消），支持 `|`、`&` 组合
7. participant agent 声明 → 节点角色声明（角色名、system prompt、description、model client、tools、memory、code executor）
8. FunctionTool / CodeExecutorTool → 动作端口（工具 schema）
9. Memory → 上下文注入/检索源
10. Message 类型 → 消息类型系统
11. `save_state`/`load_state`、`to_config()` → 状态快照与可序列化声明体（DSL 序列化目标）

**(b) 预计需要 DSL 逃逸舱**

1. selector_func / 自定义选择提示词 → 运行时闭包与自由提示词，静态 DSL 无法表达
2. MagenticOne 的 ledger 自然语言演化 → LLM 运行时生成的状态，非静态字段
3. 动态终止判据（文本匹配、handoff 目标、外部 set()）→ 依赖运行时消息内容与外部事件，仅能参数化声明
4. 拓扑运行时改写（重规划更换分工、条件激活产生新边）→ 图结构运行时变更，必须逃逸
5. 工具内任意 Python 闭包与代码执行副作用（写文件、网络）→ 不可静态声明
6. provider 侧 token 计费与重试策略 → 外部不可见，需运行时遥测钩子
7. 人在回路阻塞输入（UserProxyAgent 等待）→ 交互式外部事件
8. `to_config()` 的自足性边界（模型客户端仅存类名与数据，行为不可静态校验，**存疑**其是否可完全重建）→ 声明可表达、行为需逃逸
