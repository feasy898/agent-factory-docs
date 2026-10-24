<!-- TARGET: Agensh（去中心化多智能体协作框架） -->
<!-- ACTUAL: AutoGen（微软 AutoGen 多智能体对话编排框架，取其 Swarm 去中心化交接 + GroupChat 协商机制） -->
<!-- CONFIDENCE: LOW -->

## ① 核心机制
AutoGen 解决的是：把多智能体协作从松散的 prompt 链变成可编程、可终止、可度量的会话程序。核心执行模型是"消息驱动 + 循环"：系统唯一状态是一条追加式 message 列表，每个 Agent =(系统提示词 + 工具集 + 内存态)；GroupChat 由"发言者选择器"决定下一位发言者，形成 star 拓扑的会话循环，直到终止条件命中；Swarm 模式取消中心协调者，控制权经 handoff 工具在 Agent 之间直接转移，是框架中最接近去中心化协作的部分；嵌套对话把子任务放进隔离线程，仅把摘要作为工件回灌父线程；代码执行器把 LLM 产出的代码落地为真实动作并回传结果，闭合"思考—行动—观察"循环。

## ② 组件清单

| 组件 | 类型 | 职责 |
| --- | --- | --- |
| AssistantAgent | 角色/执行体 | LLM 节点：按 system prompt 决策、调用工具、生成回复 |
| UserProxyAgent | 角色/执行体 | 代持执行权或引入人类输入（human_input_mode 三档） |
| GroupChat | 循环 | 多参与者会话容器，承载轮次与共享历史 |
| GroupChatManager | 路由 | 按 speaker_selection_method 选下一发言者（round_robin/random/manual/llm） |
| Swarm + Handoff | 通信 | 无中心交接：以工具调用把控制权直接转给对端 |
| Message | 状态/记忆单元 | 唯一状态载体，追加式，含 role/content/tool_calls |
| TerminationCondition | 停止判据 | 文本/消息数/来源/handoff目标/token/超时/外部信号，可组合 |
| CodeExecutor | 工具 | 执行代码并回传 stdout/stderr，失败文本供模型自修复 |
| Context / SummaryContext | 上下文裁剪 | 截断或摘要历史，抑制 token 膨胀 |
| Cache(DiskCache) | 记忆/缓存 | 缓存模型响应，降成本并支持日志回放 |
| NestedChat | 子流程 | 子线程隔离，结果以摘要消息交回父线程 |
| TokenUsageTracker | 预算计量 | 累计 prompt/completion token，可触发预算型终止 |

## ③ 数据与上下文流
状态唯一且驻留内存：追加式 message 列表（默认不持久化，跨会话需外部存储）。消息构造 = Agent 自身 system prompt + 当前可见的消息窗口 + 工具定义；GroupChat 中全体成员共享同一历史，超长时由 Context 截断或以摘要消息替换，因此"谁看到什么"本质是运行时裁剪结果，而非静态权限。动作回灌：tool_calls 与代码块被转成 tool / role=user 的结果消息追加回同一历史，成为下一轮推理输入。Swarm 交接只是新增一条交接消息，控制权转移而消息共享——去中心化不等于上下文隔离。嵌套对话另起线程：子线程内可见全部子消息，结束时仅产出一条 summary 消息回父线程，细节被丢弃。

## ④ 失败处理与停止条件
- 终止条件以"或"组合，任一命中即结束（文本、消息条数、handoff 目标、token、超时、外部信号）。
- 轮次上限 max_round_limit 与单代理 max_consecutive_auto_reply 双重封顶，防无限对话与自说自话。
- 代码执行异常文本回灌同一 Agent，由模型自行修正后重试；执行器层无独立退避/重试策略（存疑：主要靠模型修复循环兜底）。
- 嵌套线程失败不自动终止父线程，除非显式配置异常传播。
- 人类介入：human_input_mode=ALWAYS 时阻塞等待输入，构成显式挂起/恢复点。
- 无系统级"任务完成度"验收与语义死锁检测，完成与否取决于终止消息；停滞检测属 MagenticOne 扩展能力（存疑：非核心）。

## ⑤ 预算与评估方式
- 预算：轮次（max_round_limit、自回复上限）与 token（TokenUsageTracker + TokenUsageTermination）双重控制。
- 成本：Context 截断与摘要压上下文、Cache 命中免重复计费、模型分级（便宜模型做选择与摘要、昂贵模型做推理）摊薄开销。
- 评估基准：AutoGenBench（多轮对话、工具使用、代码、数学、检索等任务）+ 日志回放式评测，以 ground truth / 人工 / LLM-judge 对比输出。
- 消融：单 Agent vs 群聊、选择策略（轮询 vs LLM/相关度）、摘要与缓存开关、终止条件设置对质量与 token 的影响（存疑：具体分数不复述）。

## ⑥ DSL 表达点清单

**(a) 可映射为"标准拓扑+组件"**
- Agent = 具名角色节点 + 工具集 + 内存态 → AssistantAgent / UserProxyAgent
- 会话拓扑 = star 循环 + 轮次上限 → GroupChat + GroupChatManager
- 轮询路由 = 固定后继节点 → round_robin / random 选择器
- 无中心交接 = 有向交接边 → Swarm / Handoff
- 消息流 = 追加式工件链（message 即一等工件）
- 子流程隔离 + 摘要回填 = 嵌套子图 → NestedChat
- 工具执行 = 工具节点，执行结果作为工件回灌
- 上下文裁剪 = 上下文策略节点 → ChatCompletionContext
- 记忆 = 会话历史 + 可插拔外部记忆接口（核心不含向量库，存疑）
- 停止判据 = 可组合终止条件集合；预算 = token 计量与闸门节点

**(b) 预计需要 DSL 逃逸舱**
1. 运行时动态选路（LLM 现场决定下一发言者）= 运行时改写图结构 → 逃逸舱。
2. 终止条件求值器（多条件短路、动态阈值）→ 逃逸舱，需宿主提供谓词求值。
3. 工具/代码执行的外部副作用、错误语义与重试 → 逃逸舱（执行器插件）。
4. 嵌套对话的动态裁剪与摘要生成 → 逃逸舱（依赖模型调用的上下文变换）。
5. token 计量与预算中断（运行期计数器驱动控制流）→ 逃逸舱。
6. 人类介入的阻塞与恢复（同步 I/O 挂起会话）→ 逃逸舱。
7. 缓存命中语义（影响成本与可复现性，无法静态声明）→ 逃逸舱。
8. 语义级死锁/停滞检测 → 逃逸舱。

映射注记（推断）：Agensh 的真实原语未知，本卡是"AutoGen 抽象 → DSL"的预判。若 Agensh 采用合约/账本/共识式协调，则 (a) 中的"中心协调式 GroupChat"需替换为"合约匹配 + 共享账本状态机"，并新增"共享不可变状态/账本"节点；该差异无法从现有信息判定，标记存疑。
