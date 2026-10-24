<!-- TARGET: CrewAI 的 YAML 装配方式（agents.yaml + tasks.yaml 声明角色/目标/背景故事/任务期望与分配，Process=sequential/hierarchical） -->

## ① 核心机制

CrewAI 解决的是"把一个业务流程拆成若干角色化自治智能体，并让它们以可读、可编排的方式协同交付"的问题。它本身是 Python 编排框架（MIT 开源，crewAIInc/crewAI；无早期同行评审论文，仅有 arXiv 手稿，题录细节存疑），并未发明新推理范式，而是在 ReAct（Thought→Action→Observation）单智能体循环之上补齐了"角色—目标—背景故事"提示模板、任务契约与装配层。执行模型为：Crew 按 Process 选定拓扑 → 逐 Task 推进 → 每个 Task 内由 Agent 以 ReAct 多轮调用工具直到产出满足 expected_output 的结果 → TaskOutput 作为工件在任务间流动（sequential 下自动成为下一 Task 的 context，hierarchical 下由 Manager Agent 读取并裁决委派/验收）→ 各 TaskOutput 汇入 CrewOutput。agents.yaml/tasks.yaml 是声明式装配层：只声明角色三元组与任务契约/归属，crew.py 仅做 YAML→对象绑定并调用 kickoff()，实现"流程声明"与"运行代码"解耦。

## ② 组件清单

| 组件 | 类型 | 职责 |
|---|---|---|
| Crew | 编排容器 | 持有 agents/tasks/process/llm/memory，统一 kickoff 并汇总 CrewOutput |
| Process | 拓扑枚举 | sequential＝有序链＋上下文直连；hierarchical＝Manager 动态委派 |
| Agent | 节点 | role/goal/backstory 三要素＋tools/llm/allow_delegation/max_iter/verbose |
| Task | 节点实例 | description/expected_output/agent/output_json\|output_pydantic/context/human_input |
| AgentExecutor（CrewAgentExecutor） | 循环 | 实现 ReAct 多轮循环、提示拼装、中间步日志 |
| TaskOutput | 工件 | raw/json/pydantic/file_path，任务间交接载体 |
| Context | 边数据流 | 指定的前序 TaskOutput 集合，注入后续提示 |
| Manager Agent | 角色 | hierarchical 下规划、委派、验收；manager_llm/manager_agent 可配 |
| Planner | 前置节点 | planning=True 时由 planning_llm 生成执行计划 |
| Memory | 状态 | short/long/entity/contextual/external(mem0)，Crew 级开关 |
| Tools | 能力 | LangChain 兼容工具、原生搜索/抓取/DB 工具、CodeInterpreterTool、MCP 适配器，支持缓存 |
| LLM | 资源 | crew 默认＋agent 覆盖＋manager_llm/planning_llm/function_calling_llm |
| Guardrail | 校验器 | 结构化输出校验与 LLM 质量门禁 |
| Callbacks | 观测钩子 | task_callback / step_callback |
| Flow | 相邻能力 | @start/@listen/@router 的状态机（与 YAML 装配并存） |
| CLI | 装配入口 | crewai create 生成 YAML 骨架，crewai run 执行 |

## ③ 数据与上下文流

装配期：agents.yaml 每条目→Agent(role, goal, backstory, 可再指定 llm/tools)；tasks.yaml 每条目→Task(description, expected_output, agent:引用 agents.yaml 的键名)，该键引用即完成"任务→角色"分配。运行期，每次 LLM 调用的提示由 system（角色三元组＋任务描述/期望输出＋工具 schema＋规则）与 user（任务输入＋按需检索的记忆）拼装，并追加短期记忆历史与 ReAct 中间步。工件交接：Task 完成后产出 TaskOutput（可写 output_file），作为后续 Task 的 context；普通 Agent 之间互不可见，只能经 delegate_work/ask_question 委派通道交换信息且不共享彼此内部记忆。状态位置：Agent/Task 配置与 task.output 在 Crew 内存；长期记忆落 SQLite＋向量库，tool cache 落盘，Flow 另有 persist_state；Crew 本身无跨进程持久化状态，重跑即失忆（除 memory 外）。可见性：Agent 仅见自身提示＋显式 context＋自检索记忆；hierarchical 的 Manager 可见全部 worker 输出；human_input=True 时外部人类可见该任务草稿并注入反馈。

## ④ 失败处理与停止条件

1. Agent 循环上限 max_iter（默认约 15）超出即报错终止；max_execution_time 可按时钟强停。
2. 工具异常/超时：把错误文本作为 Observation 回灌，模型可自行改路重试，无统一兜底。
3. LLM 传输层：由底层 LiteLLM 做重试与退避（LLM(max_retries=…)）；max_rpm 限流触发节流或报错。
4. 结构化输出校验失败：Pydantic 错误回灌要求重生成，超过上限抛错（具体重试次数随版本变化，存疑）。
5. Guardrail 不通过抛异常，终止该 Task（是否可继续重试，版本相关，存疑）。
6. 单 Task 抛错通常终止整次 kickoff，无内建"跳过/重跑单任务"语义。
7. human_input 反馈轮次超上限则报错终止。
8. hierarchical：Manager 的 max_iter 封顶；委派失败结果回灌 Manager 由其自行裁决，"判定完成"即停止。
9. Planner 失败一般降级为无计划执行、不阻断主流程（存疑）。
10. 唯一硬性早停是 executor 的 max_iter/超时与 Agent 声明最终答案；无内建成本早停。

## ⑤ 预算与评估方式

控制旋钮：max_iter、max_rpm（Agent/Task/Crew 级）、max_execution_time、max_retry_limit、LLM 级 max_tokens/timeout、tool 缓存、async_execution 并发、human_input 减少自动步数。用量观测：LLM 回调累计 token（crew.usage_metrics、可 reset），LiteLLM 给单价估算，可接 OpenTelemetry tracing 观测逐步调用。评估：框架内核无官方 benchmark/leaderboard；常见工程做法是 pytest＋kickoff_for_each(inputs) 批量回归、按 expected_output 做规则断言、LLM-as-judge 打分、人工评分 CrewOutput。横向参照可用 AgentBench、GAIA、τ-bench、SWE-bench、MultiAgentBench 与"Agent Systems 缩放律"类研究，但 CrewAI 缺少稳定公开的对照分数（存疑）。

## ⑥ DSL 表达点清单

**(a) 可映射为"标准拓扑+组件"**
- Crew → 工作流图根/单次运行上下文；Agent → 节点模板（role/goal/backstory/tools 声明式）；Task → 节点实例＋I/O 契约（description 为输入提示、expected_output 为输出规格、output_pydantic 为输出 schema）。
- Process=sequential → 静态线性 DAG，边＝TaskOutput→context；Process=hierarchical → "Manager 节点＋委派边"的半静态图。
- ReAct 循环 → 节点内迭代执行；Context → 边上的数据流绑定；Memory → 状态存储/检索作用域声明；planning → 条件启用的前置规划节点；guardrail → 节点前后置校验器；callbacks → step/task 级事件钩子；tools → 能力绑定表；async_execution → 并发分支（汇合语义存疑）。

**(b) 预计需要 DSL 逃逸舱**
1. Manager 运行时动态委派与改写执行次序：hierarchical 的边由 LLM 在运行时生成，静态 DSL 无法枚举 → 逃逸舱（动态图边/自适应路由）。
2. ReAct 内循环的终止语义：是否继续调工具由 LLM 决定，DSL 只能给上限（max_iter），无法声明"何时算完成" → 逃逸舱（运行时决策）。
3. expected_output 的自然语言判据与 LLM-as-judge 门禁：满意度无法编码为 DSL 断言 → 逃逸舱（评审器节点）。
4. Memory 的相关性召回与重排：属运行时检索策略，DSL 只能声明启用/作用域/检索源 → 逃逸舱（检索器组件）。
5. human_input 的阻塞式人机回路：外部人类在任务中途注入反馈，是不可静态声明的外部控制流 → 逃逸舱（中断/恢复语义）。
6. Flow 的 @router 动态分支与 persist_state：同生态内并存的动态图与持久化状态 → 逃逸舱（动态图＋外部状态存储）。
7. 限流与成本治理（max_rpm、成本早停）：属运行时资源策略，CrewAI 无原生成本早停 → 逃逸舱（配额/预算守卫）。
8. YAML 允许的 extra 字段透传与插件/MCP 工具运行时注册：字段与工具集合不可静态封闭枚举 → 逃逸舱（开放扩展点）。
9. LiteLLM 层重试/退避/多供应商 fallback：位于 DSL 之下的传输层容错 → 逃逸舱（provider 层）。
