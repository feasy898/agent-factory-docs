# openJiuwen（九问）开源项目调研报告

> 调研日期：2026-10-19
> 调研方式：互联网检索 + 源码仓库实地阅读（13 个仓库的完整源码/文档已下载至临时目录逐仓分析，分析后已删除，本报告为唯一留存资料）

---

## 1. 项目概览

### 1.1 openJiuwen 是什么

**openJiuwen（开源九问）** 是华为支持的开源 AI Agent 平台，由华为 2012 实验室九问（Jiuwen）团队联合华为云、小艺（Celia）终端团队共同打造，于 **2025 年 12 月底正式开源**。定位是**生产级、企业级 AI Agent 开发与运行平台**，覆盖 Agent 从开发、调试、部署到运维优化的完整生命周期。官方一句话定位：

> openJiuwen 作为开源 Agent 平台，致力于提供灵活、强大且易用的 AI Agent 开发与运行能力。开发者可快速构建处理各类简单或复杂任务的 AI Agent，实现多 Agent 协同交互，高效开发生产级可靠 AI Agent。

它不是单一框架，而是一个** monorepo 生态 / AgentOS 级别的产品家族**：既提供面向开发者的 Python/Java SDK（对标 LangChain/AutoGen），也提供低码/零码可视化开发平台（对标 Dify/Coze），还提供分布式运行时、记忆系统、协议 SDK、Skill 资产市场，以及多款开箱即用的"深度智能体"应用（对标 OpenClaw/Manus 类产品）。其商用对应版本为华为云 AgentArts（智果）企业智能体平台，形成"商用（AgentArts）+ 开源（openJiuwen）"双轮驱动。

### 1.2 背景与社区信息

| 项目 | 信息 |
|---|---|
| 开源时间 | 2025 年 12 月（2026-08-28 在 828 B2B 企业节正式发布平台版，2026-09 华为全联接大会生态亮相） |
| 主代码托管 | **GitCode：`https://gitcode.com/openJiuwen`**（官方文档中所有链接指向 GitCode） |
| GitHub 镜像/组织 | `https://github.com/openJiuwen-ai`（24 个仓库） |
| Gitee | `openeuler/jiuwen-agentcore`（已标注迁移至 AtomGit：`atomgit.com/openeuler/jiuwen-agentcore`） |
| 官网 | `https://openjiuwen.com`（中国站）/ `openjiuwen.com/en` |
| 文档中心 | `openJiuwen-ai/docs` 仓库 + 各仓库内 docs/ |
| 许可证 | **Apache License 2.0**（源码版权头为 `Copyright (c) Huawei Technologies Co., Ltd.`） |
| 社区治理 | SIG 特别兴趣小组制度、CLA 签署（osInfra）、Conventional Commits、门禁 CI、行为准则；邮件列表运营 |
| 热度（2026-10） | GitHub `jiuwenswarm` 7578 stars；`agent-core` 452 stars；`agent-studio` 189 stars；`sciencediscovery` 172 stars |
| 与大赛关系 | `agent-tools` 仓库内置 "Agent Innovation Challenge（智能体创新挑战赛）" 目录（比赛提交/参考样例）；另有 CCF BDCI 2026 赛题仓库 `CareerSim-BDCI26`（Agent 职场生存与晋升挑战），与华为开发者大赛/竞赛生态直接相关 |

### 1.3 解决什么问题

openJiuwen 官方归纳的痛点与对策：

1. **开发门槛高**：提供零代码（Studio 可视化）、低代码（工作流画布）、高代码（Python/Java SDK）三种开发方式；
2. **单 Agent 能力有限**：多 Agent 协同（Leader/Teammate 蜂群、任务分解、专业分工）+ 分布式部署（跨进程/跨机器）；
3. **执行不可靠、体验易"失忆"**：高可靠执行引擎（断点恢复、状态持久化）+ 长期记忆系统（L0–L3 分层、睡时巩固）；
4. **能力无法沉淀复用**：Agent Skills / Swarm Skills（能力资产化）+ SkillHub 托管分发 + Skill 在线自演进；
5. **生产态管理缺失**：Agent Distributed Runtime（多租户、进程/Docker/K8s 部署、生命周期管控）+ Agent Ops（评测、观测、调优）。

---

## 2. 代码仓库全景（24 个仓库）

openJiuwen 采用**模块化多仓库**设计，各仓库可独立演进、自由组合。按架构分层归类：

| 分层 | 仓库 | 语言 | Stars | 说明 |
|---|---|---|---|---|
| **DeepAgents（场景智能体）** | `jiuwenswarm` | Python | 7578 | 多智能体协同框架与官方旗舰应用（原 JiuwenClaw，2026-05 v0.2.0 更名），PyPI 包名 `workswarm`，桌面版支持 Windows/macOS/鸿蒙 |
| | `deepsearch` | Python | 129 | 知识增强深度检索与研究引擎（DeepSearch + CodeSearch + search-base 三个子项目），段级引用溯源 |
| | `jiuwensymbiosis` | Python | 67 | Physical AI / 具身智能助手框架（构型无关能力复用与安全控制） |
| | `sciencediscovery` | TypeScript | 172 | 科研一站式 Agentic 工作台（文献阅读→假设→沙箱代码→实验，全程留痕），基于 JiuwenSwarm |
| **SkillHub（技能资产）** | `skillhub` | Python | 32 | Agentic Hub：Skill/SwarmSkill/插件/连接器/专家/专家团六类资产的托管分发平台，兼容 ClawHub 协议，官方托管 agentichub.openjiuwen.com |
| **Agent Studio（可视化开发）** | `agent-studio` | Java+Angular | 189 | 一站式低码/零码 Agent 开发平台：Agent 开发、工作流编排、Prompt 调优、知识库、插件市场、资源管理 |
| **Agent Framework（核心框架）** | `agent-core` | Python | 452 | 核心 Python SDK（PyPI `openjiuwen`，v0.1.19），Agent 编排、运行时、模型、工具、检索、评测、自演进 |
| | `agent-core-java` | Java | 43 | Java 版 SDK（Maven `com.openjiuwen:agent-core-java`），与 Python 能力对齐 |
| | `agent-memory` | Python | 70 | JiuwenMemory 长期记忆系统（PyPI `JiuwenMemory`），L0–L3 分层 + 睡时巩固 + 图谱记忆 |
| **Agent Distributed Runtime（分布式运行时）** | `agent-runtime` | Python | 15 | Agent 服务化运行与部署管理（subprocess/docker/k8s 三种策略，多租户隔离） |
| | `agent-runtime-java` | Java | 33 | Java 版分布式运行时（Spring Boot，Agent Server + Runtime Manager） |
| | `agent-protocol` | C++/Python | 115 | 互操作协议 SDK：MCP C++ SDK、A2A C++ SDK、A2X Registry、A4P 可验证授权 SDK |
| **AgentOS 底座（部分待开源）** | `agentos-enterprise` | Shell | 19 | 多用户 Agent 操作系统：跨系统部署、统一入口 |
| | `agent-infer` | Python | 100 | 基于 vLLM 的 Agentic 推理框架 |
| | `model-router` | Python | 13 | 模型路由内核（按请求选模型，无状态纯函数 + 有界外部状态） |
| | `agent-dx` | Rust | 3 | Agent 分布式执行底座（注册、调用、会话管理开发工具） |
| **工具与外围** | `agent-tools` | Python | 19 | 工具生态：vLLM 亲和调度（KV-Cache 感知路由）、推理路由、比赛样例 |
| | `iCode` | Python | 359 | 轻量级全离线 TUI 开发平台（Agent/工作流工具箱，类 Claude Code 终端形态） |
| | `relay` | TypeScript | 5 | 多 Agent 协作开发平台（协作开发、代码评审、任务管理） |
| | `CareerSim-BDCI26` | Python | 7 | CCF BDCI 2026 赛题：Agent 职场生存与晋升挑战 |
| | `agent-plugin` | Python | 0 | 插件（刚建仓） |
| **社区** | `community` | - | 13 | 治理：章程、CLA、行为准则、安全、发布、SIG 资料 |
| | `docs` | - | 32 | 文档中心（产品简介中英文） |
| | `.github` | - | 4 | 组织 Profile |

> 注：架构图中还有 `agent-gateway`（统一接入网关）与 Agent Ops 平台、Agent System Service（沙箱/Agent POSIX/文件系统/通信总线）标注为"待后期持续开源"（Opening Soon）。

---

## 3. 系统架构

### 3.1 五层能力架构

openJiuwen 采用分层架构，覆盖 AI Agent 从开发、运行到部署运维的完整生命周期（来源：`docs/zh/产品简介.md` 与架构图 `docs/zh/images/architecture.png`）：

```
┌─────────────────────────── DeepAgents ───────────────────────────┐
│   JiuwenSwarm   |   Vibe Agent   |   DeepSearch   |   Others     │
├────────────────────── Agent Core ────────────────────────────────┐
│ ┌─ Agent Framework ────────────────────────────────────────────┐ │   ┌─ Agent-Studio ─┐
│ │ Claw SDK                                                     │ │   │ No-Code/Low-Code│
│ │ Agent Engine: Context Engine | Harness Engine | Coordination │ │   │ Application Space│
│ │              Self Evolving   | Affinity-Scheduler| Team Skills│ │   │ Workflow Canvas │
│ │ Agent Shell:  Privilege Control | Tools Guardrail | Privacy- │ │   │ Resource Mgmt   │
│ │              ware Infer Routing                              │ │   ├─ Agent-Ops ────┤
│ ├─ Agent Distributed Runtime ─────────────────────────────────┤ │   │ Full-chain Tune │
│ │ Agent Service SDK | Discovery & Comm | Multitenancy | Mesh   │ │   │ Assessment&Eval │
│ ├─ Agent System Service ──────────────────────────────────────┤ │   │ Observation     │
│ │ Agent POSIX | System Sandbox | Memory Storage | Agent UI/Web │ │   └────────────────┘
└─┴──────────────────────────────────────────────────────────────┴─┴──────────────────┘
          Models（Pangu/Qwen/DeepSeek/GLM...）  Infrastructure  Hardware/Chipsets
```

五层职责：

1. **DeepAgents**：面向不同场景的复杂智能体，开箱即用——JiuwenSwarm（多 Agent 蜂群）、JiuwenSymbiosis（具身智能）、DeepSearch（深度检索研究）等；
2. **Agent Studio**：一站式开发平台，低码/零代码可视化开发、工作流编排、Prompt 调优、在线调试、资源管理；
3. **Agent Framework**：核心框架与执行引擎（agent-core/-java/-memory），覆盖任务规划、循环执行、工具与技能调用、上下文管理、记忆子系统、多智能体协同、Agent 自演进、算力亲和调度；
4. **Agent Distributed Runtime**：分布式运行时底座，低码/高码两种部署模式，一键发布、多租户隔离、弹性扩缩容、统一注册发现、跨集群互通；
5. **Agent System Service**（AgentOS 底层，逐步开源）：系统级安全隔离沙箱、全局统一记忆持久化、原生 CLI 系统工具、标准化 Agent 文件系统、跨 Agent 通信总线。

架构图中的关键概念（华为自研术语体系）：
- **Claw SDK**：编码智能体底座 SDK（源自 JiuwenClaw/与 OpenClaw 生态呼应）；
- **Context Engine**：上下文引擎；**Harness Engine**：智能体执行骨架（编码场景）；**Coordination Engine**：协同引擎；
- **Self Evolving**：自演进子系统；**Affinity-Scheduler**：算力/KV-Cache 亲和调度；**Team Skills**：团队技能；
- **Agent Shell**：权限控制（Privilege Control）、工具护栏（Tools Guardrail）、隐私感知推理路由（Privacy-ware Infer Routing）；
- **Agent POSIX**：给 Agent 提供类 POSIX 的系统服务抽象。

### 3.2 设计特点

- **双形态统一**：同一套 agent-core 引擎同时支撑"高代码 SDK 开发"与"Studio 低码编排（IR/DSL → 运行时执行）"，Studio 的 `studio-runtime` 服务就是内嵌 agent-runtime 的应用适配层；
- **批流混合图执行**：组件化 + 数据流传递，组件支持 `invoke`（批→批）/ `stream`（批→流）/ `collect`（流→批）/ `transform`（流→流）四种能力类型，图执行器为自研 **Pregel 风格异步并行图引擎**（`openjiuwen/core/graph/pregel` + `stream_actor`）；
- **状态与断点**：会话级状态建模、状态持久化（Checkpointer）、中断恢复、多实例一致性；
- **全链路可观测**：OpenTelemetry（`extensions/tracer_otel`、`harness/observability`），团队级/Agent 级 span 体系。

---

## 4. 核心仓库深度解析

### 4.1 agent-core —— Python 核心 SDK（最重要）

- **定位**：大模型应用 Python SDK，提供高性能 Agent 运行时；PyPI 包 `openjiuwen`，当前版本 0.1.19；Python >=3.11,<3.14。
- **顶层包结构**（`openjiuwen/`，12 个子包）：

| 子包 | 职责 |
|---|---|
| `core/` | 引擎主体：`application`（llm_agent、workflow_agent 两类预置应用）、`context_engine`（上下文引擎：ModelContext/ContextWindow/Token 统计/摘要卸载/多级压缩链）、`controller`（ReAct 等控制器）、`foundation`（LLM 客户端抽象 + Prompt 模板 + Store 抽象 + Tool 体系含 MCP）、`graph`（Pregel 图执行、stream actor、可视化）、`memory`（长期记忆：含 dreaming 睡时巩固）、`multiagent`（TeamRuntime/CommunicableAgent/BaseTeam/预置协作模式）、`workflow`（工作流组件模型）、`session`（会话/中断恢复/流式）、`security`、`kv_cache`、`multitenant`、`sysop`、`retrieval`、`runner`（Runner 统一执行门面） |
| `harness/` | **DeepAgent 深度代理**（编码场景完整闭环）：`create_deep_agent()` 工厂、task_loop（任务循环）、subagents/subagent_runtime（子代理）、rails（三层护栏：上下文处理链/安全/技能演进）、workspace（工作空间沙箱）、tools、skills、security、lsp、cli、moa、observability、goal（目标与评估） |
| `harness_protocol/`、`harness_providers/` | 三方 Harness 接入协议（Session>Turn>Step 层级）与 Provider 适配 |
| `agent_teams/` | **蜂群协作引擎**（JiuwenSwarm 的框架层）：Leader+Teammate 的 TeamAgent、消息总线（inprocess/pyzmq 双传输）、organization（跨团队组织/任务池/专家团队/共享工作空间）、spawn（进程/进程内启动成员）、team_workspace（共享文件/锁/版本）、interaction（@路由/HITL 人机交互）、skill（外部成员 SKILL.md + CLI）、mcp（外部成员 stdio MCP Server）、workflow（**Swarmflow** 编排引擎）、cli（prompt_toolkit+rich TUI）、tiny_agent（极简 Agent）、observability、reliability（主动可靠性） |
| `agent_evolving/` | **自演进/RL 子系统**：Trainer/Evaluator/Optimizer/Updater、Trajectory（OTLP 规范轨迹）、experience（Skill 经验沉淀与治理）、checkpointing、ttse；`agent_rl/`（离线/在线强化学习：Ray、verl 为可选重依赖；在线含 Gateway/judge/调度/训练服务） |
| `symphony/` | 能力资产领域模块：能力指纹（fingerprint）、能力树检索、编排计划（Fast/Beam Planner）、经验沉淀、能力评估 |
| `dev_tools/` | agent_builder、prompt_builder、skill_creator、skill_evaluator、tune |
| `extensions/` | a2a、checkpointer、context_evolver、message_queue、observability（OTel）、store、sys_operation、external_provider、vendor_specific |
| `auto_harness/`、`rsi/` | Auto Harness（评测驱动的 Harness 端到端自优化）等前沿方向 |

- **CLI 入口**（pyproject `[project.scripts]`）：`openjiuwen`（harness CLI）、`team-member`、`openjiuwen-team-mcp`、`openjiuwen-rl-service`。
- **官方文档结构**（`docs/zh/2.开发指南/`）：基础功能（接入大模型/LLM 协议收敛/自定义工具）→ 工作流（组件/编排/可视化）→ 智能体（ReActAgent/WorkflowAgent/ContextEvolvingAgent/工具自演进/自定义）→ 多智能体（TeamRuntime/BaseTeam/AgentAsTool/预置协作模式）→ 智能体团队（AgentTeams/Team Organization/团队技能演进）→ 自演进（Agent Skills/Swarm Skills/Skill 在线自演进/Metis 任务记忆）→ 高阶用法（Session 中断恢复/流式/状态、HITL、DeepAgent 强化学习、上下文引擎、记忆引擎、知识检索、Prompt 生成优化、沙箱、安全护栏 Guardrail、MCP 工具、Checkpointer、异步回调、IntelliRouter 智能路由）→ API 文档。
- **examples/**（26 个）：`react_agent`、`workflow_agent`、`multi_agent`、`adaptive_multi_agent_collab`、`agent_evolving`（skill/swarmskill/react 演进 + 评估流水线）、`harness`（DeepAgent+worktree）、`a2a`、`mcp`、`graph_memory`、`permissions`、`security_rail_demo`、`session`、`store`、`retrieval`、`skill_use`、`skill_evaluate`、`context_evolver`、`intelli_router`、`mobile_gui`、`MANGO`、`PerStream`、`jiuwenrl_online`、`rl_calculator`、`rl_nl2sql`、`interact`、`lsp`。

#### Hello World：ReActAgent（官方文档示例，含工具调用与 MCP）

```python
import asyncio, os
from openjiuwen.core.foundation.llm import ModelRequestConfig, ModelClientConfig
from openjiuwen.core.foundation.tool import RestfulApi, RestfulApiCard
from openjiuwen.core.single_agent import AgentCard, ReActAgentConfig, ReActAgent
from openjiuwen.core.runner import Runner

# 1) 模型配置（支持 Pangu/Qwen/DeepSeek 等 OpenAI 兼容 API）
model_config = ModelRequestConfig(model="your-model", temperature=0.8, top_p=0.9)
client_config = ModelClientConfig(client_provider="OpenAI", api_key="sk-xxx",
                                  api_base="https://api.xxx.com", timeout=30)

# 2) 提示词模板
prompt_template = [dict(role="system", content="你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！")]

# 3) 把 REST API 封装成工具（也可用 McpServerConfig 接入 MCP 服务）
weather_card = RestfulApiCard(
    name="WeatherReporter", description="天气查询插件",
    url="https://your-weather-api", method="GET",
    input_params={"type": "object",
                  "properties": {"location": {"type": "string"},
                                 "date": {"type": "string"}},
                  "required": ["location", "date"]})
tool = RestfulApi(card=weather_card)
Runner.resource_mgr.add_tool(tool)

# 4) 创建并运行 ReActAgent
config = ReActAgentConfig(model_config_obj=model_config,
                          model_client_config=client_config,
                          prompt_template=prompt_template)
agent = ReActAgent(card=AgentCard(id="react_agent_1", description="AI助手")).configure(config)
agent.ability_manager.add(tool.card)

result = asyncio.run(agent.invoke({"query": "查询杭州的天气"}))
print(result.get("output"))
```

#### Hello World：Workflow（组件化图编排，README 示例节选）

```python
from openjiuwen.core.workflow import Start, End, LLMComponent, LLMCompConfig, Workflow, WorkflowCard
from openjiuwen.core.runner.runner import Runner

flow = Workflow(card=WorkflowCard(id="generate_text_workflow", name="generate_text", version="1.0",
                                  input_params={"type": "object",
                                                "properties": {"query": {"type": "string"}},
                                                "required": ["query"]}))
start, end = Start(), End({"responseTemplate": "Workflow output text: {{output}}"})
llm = LLMComponent(LLMCompConfig(model_client_config=..., model_config=...,
                                  template_content=[{"role": "user", "content": "{{query}}"}]))
flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
flow.add_workflow_comp("llm", llm, inputs_schema={"query": "${start.query}"})
flow.set_end_comp("end", end, inputs_schema={"output": "${llm.output}"})
flow.add_connection("start", "llm"); flow.add_connection("llm", "end")
Runner.resource_mgr.add_workflow(...)   # 注册后可被 WorkflowAgent 绑定调用
```

#### 多智能体三种预置协作模式（`core/multi_agent`）

| 模式 | 通信方式 | 特点/场景 |
|---|---|---|
| Hierarchical Tools | Agent as Tool（ability_manager 注册子 Agent） | 层次化任务分解，调用关系固定（主管→调研员/分析员→专家） |
| Hierarchical MessageBus | P2P MessageBus | 支持并行调用子 Agent（`max_parallel_sub_agents`），流水线/分布式调度 |
| Handoff | Pub-Sub + 状态机 | Agent 间主动转交任务，支持中断恢复，顺序协作 |

通信模式支持 **P2P（send）**、**Pub-Sub（publish/subscribe，通配符 `*`/`?`）** 及混合。任意 Agent 可通过 `Agent as Tool` 注册为另一个 Agent 的能力，对 LLM 完全透明。

#### 蜂群团队（`agent_teams`，JiuwenSwarm 引擎层）

- `TeamAgentSpec.build()` 是组装 TeamAgent 的唯一公共路径（`agents["leader"]` 必填、`teammate` 可选）；`Runner.run_agent_team[_streaming]()` 运行，支持冷启动/热恢复/会话切换（对象池 + 派发决策 + 并发门禁）；
- 成员可**跨进程/跨机器**（spawn: process/inprocess；messager: inprocess/pyzmq；worktree_remote 跨机器工作树）；
- 组织层（organization）支持跨团队任务池、专家团队（expert_adapters）、汇总团队、共享工作空间；
- 外部 Agent 可通过 **CLI（SKILL_member.md）** 或 **stdio MCP Server** 以"外部成员"身份入队——异构 Agent（如 Claude Code 等）也能加入团队；
- **Swarmflow**：用普通 Python 脚本（`META={...}` + `async def run(args)`，`agent()/parallel()/pipeline()/phase()` 原语）做确定性多阶段编排；带内容寻址 resume journal、token 预算账本（BudgetLedger）、并发治理（三层）、HITL（`human`/`human_session`）、进度事件四层表示（WorkflowRun→Phase→AgentActivity）；
- 可靠性：TeamMonitor 只读监控、OpenTelemetry 团队根 span、主动可靠性框架（健康信号采集+分级处置）。

#### 自演进与强化学习（`agent_evolving`）

- **Agent Skill**：把专业知识/流程/脚本/模板放进含 `SKILL.md` 的标准文件夹，Agent 按描述自动触发（兼容 Anthropic Skills 形态）；`skill-creator` 支持一句话生成；
- **Swarm Skill**：把"多角色协作方式"本身沉淀为资产（可读性/性能/安全三视角评审团队等），`swarmskill-creator` 一句话生成团队；
- **Skill 在线自演进**：`SkillCreateRail` 检测可复用工作流自动提议创建 Skill；`SkillEvolutionRail` + 用户不满/错误信号驱动 Skill 定义迭代（无需训练模型权重）；
- **Auto Harness**：评测驱动端到端优化 Harness 本身；
- **RL**：离线（Ray/verl 可选）与在线（采集 Gateway + judge + 训练调度 + 服务）强化学习，`jiuwenrl_online`、`rl_calculator`、`rl_nl2sql` 提供完整示例；`openjiuwen-rl-service` 独立服务入口；
- **Metis 任务记忆**、经验库（experience 治理：生成→审批→提交→消费反馈）。

### 4.2 agent-core-java —— Java SDK

- Maven 三模块：`core` / `retrieval` / `memory`；Java 17+，`com.openjiuwen:agent-core-java`；
- `core` 包结构（`com.openjiuwen` 下 10 个顶层包）：`core`（application/context/controller/graph[pregel]/memory/multiagent/session/workflow/runner/retrieval/security/sysop/multitenant/kvcache/operator 等，与 Python 对齐）、`harness`（deep_agent/task_loop/subagents/rails/workspace/lsp/security/cli）、`deepagents`、`agentteams`（coordination/factory/interaction/kvcache/messager）、`agentevolving`（agent_rl 离线在线、evaluator、optimizer、trajectory、sharing）、`auto_harness`、`dev_tools`、`extensions`（a2a/checkpointer/context_evolver/message_queue/store/tracerotel）、`spi`（memory/store SPI）；
- **32 个示例**：react_agent（天气助手，Runner.runAgent）、workflow_agent（金融场景）、deep_agent、agent_teams、auto_harness、agent_evolving、context_evolver、graph_memory、multi_agent、a2a、mcp、sandbox、permissions、skill_create/use/evaluate/hot_reload、rl_calculator、rl_nl2sql、jiuwenrl_online、kv-cache-demo、lsp、multi-modal-inference 等；
- 特色：`ReActInterruptResumeExample` 展示中断恢复；存储内置 Milvus/Chroma/PostgreSQL(pgvector)/KV/图数据库。

### 4.3 jiuwenswarm —— 旗舰多 Agent 应用（最热门仓库）

- **定位**：让多 Agent 真正协作起来的终端 Agent 系统，"懂你所想自主演进，蜂群协作完成复杂任务"；面向开发者与团队，自然语言驱动多 Agent 协作、Skill 自演进与工具调用，端到端交付。PyPI `workswarm`；`pip install workswarm` → `jiuwenswarm-init` → `jiuwenswarm-start` → Web UI（localhost:5173）；另有 Windows/macOS 桌面版（含自动更新）与鸿蒙 PC 版、TUI 终端界面。
- **执行模式**：Agent 模式（单 Agent 规划执行，`agent.plan`/`agent.fast`）/ Cluster 集群模式（Leader 编排多专业 Agent，默认）/ Code 模式（代码工作区，diff 展示）；TUI `/mode` 切换子模式（`code.normal`、`code.team`、`team`）。
- **核心能力**（README 能力表）：
  - 多 Agent 协作：Leader 拆解任务、组建团队、多 Agent 专业分工动态协商；
  - 分布式 Swarm：Leader/Teammate 跨进程跨机器部署（底层即 agent-core 的 agent_teams：pyzmq 消息、任务池、共享工作空间）；
  - Swarmflow：Python 脚本确定性多阶段编排（HITL、team token 预算、`/swarmflows` 运行树监控、渐进式工具暴露、AgentGroup 专家 worker）；
  - **Skill 自演进**：自动检测错误信号与用户不满，优化 Skill 定义；
  - Skill Hub 流通：swarmskills.openjiuwen.com 搜索/安装/组合/二创；
  - **Auto Harness**：评测驱动 Harness 自动优化（不训模型权重）;
  - 模型兼容：华为云 MaaS、OpenAI、DeepSeek、DashScope、SiliconFlow、OpenRouter 等 OpenAI 兼容 API + 本地模型；配置 `~/.jiuwenswarm/config/config.yaml` 热加载；
  - 安全：工具执行前审批、文件访问白名单、敏感操作拦截；
- **渠道接入**：小艺、飞书、钉钉、企微、个人微信（国内）；Telegram、Discord、Slack、WhatsApp（国际）；支持群聊 @、数字人（飞书/企微）；
- **记忆**：Memory / Task Memory / Coding Memory 三类文档（对接 JiuwenMemory）；
- **版本节奏**：v0.2.4.beta3（2026-08）聚焦 Agent 实例冷启动时延；近期加入浏览器子 Agent 隔离、多模态会话、Skill-Omni（视觉知识转多模态 Skill）、`/security-review` 等 TUI 命令。

### 4.4 agent-studio —— 低码/零码可视化平台

- **部署形态**：四个服务——`studio-console`（Angular 前端 + Nginx 反代）、`studio-manager`（Java Spring Boot 3.5，管理 Agent/知识库/模型/工具/MCP）、`studio-runtime`（Python，即 agent-runtime 内嵌：Agent/工作流/LLM/MCP/记忆执行与发布调用）、`studio-builder`（Python：NL2、Prompt 生成与优化、模型调测）；
- **技术栈**：后端 Spring Boot 3.5 + MyBatis/Hibernate + Redis(Redisson) + MySQL 8/GaussDB/openGauss + OBS/MinIO + Quartz + JWT/SAML/SSO；前端 Angular 20 + NG-ZORRO + **AntV X6（工作流画布）** + Monaco Editor + ECharts + Tailwind；
- **功能清单**：Agent 开发与测试（插件按需选取、可视化编排、知识库/记忆配置、在线调试发布）、Prompt 工程（一键生成/自动优化/多版本对比测试/版本管理）、工作流可视化编排（拖拽画布、单步调试、实时日志）、资源管理（模型/插件/知识库/记忆统一管理）、知识库 RAG、插件市场、MCP 服务管理（NPX/UVX/SSE/stdio 部署类型）、数据源管理（MySQL 等，配合 NL2SQL）、技能（Skill）管理、API Key、多租户（domain_id/project_id/workspace_id 三级）、审计日志、OpenTelemetry；
- **数据模型**：用户/工作空间/Agent（版本化，IR+DSL 路径）/工作流（版本化、触发器、共享）/会话/知识库/MCP 模板与实例/应用（App 挂 Agent 或 Workflow）/数据源/技能版本/API 密钥，共 20+ 张核心表；
- 一键部署：`cp deploy/.env.template deploy/.env && bash docker/package.sh && bash docker/build.sh && bash deploy/deploy.sh local`。

### 4.5 agent-runtime —— 服务化运行时

- 解决"开发态→生产态"：统一 REST 管理面（部署/查询/删除/健康检查），对话面 `/query`、`/health`、`/reset_conversation`（FastAPI）；
- **三种部署策略**：`subprocess`（默认）/ `docker` / `k8s`（含 kubeconfig、默认部署配置）；
- **多租户**：`user_id`/`space_id` 上下文注入隔离；数据库 SQLite/MySQL/GaussDB/openGauss（`RUNTIME_DB_TYPE` 切换）；
- 应用适配层（applications/）：`workflow_agent`（工作流 IR 执行）、`lowcode_agent`（低码 Agent，配镜像）、`llm_agent`、`a2a_service`、`ir_execution_service`、`versatile_adapter`；
- 模块：service（AgentApp/BaseApp）+ management（DeploymentManager + Deployer）+ server（管理面 REST + 租户中间件）+ foundation（DB/端口/虚拟环境/Docker 工具/日志）+ cli；
- Java 版 `agent-runtime-java`：Spring Boot 实现的分布式运行时（Agent Server + Runtime Manager）。

### 4.6 agent-memory —— JiuwenMemory 长期记忆系统

- **理念**："模型能力决定 Agent 的智力下限，记忆系统决定 Agent 的体验上限"；记忆即"基因片段"的 **AutoGenetic Memory（自主生长记忆）**；
- **L0–L3 分层记忆**：L0 原始消息 → L1 摘要 → L2 结构化记忆（语义/情景/变量）→ L3 用户画像；各层独立持久化；
- **Auto Dreaming（睡时巩固）**：借鉴认知神经科学三阶段（浅睡筛选→REM 提取归类→深睡去重消解）的后台 sweep，断点续扫、忙碌退避；
- **MemoryTurbo**：写入缓存即回（时延降 92%）、后台小模型按话题合并提取、缓存层向量提前检索；
- **Graph Memory**：LLM 抽取实体/关系/Episode，合并去重、BFS 图扩展、三路并行检索 + rerank；
- **冲突检测**：MemUpdateChecker 用 LLM 判 ADD/UPDATE/DELETE，语义校验后执行；
- **存储全栈**：KV（内存/Shelve/DB/Redis）、向量（ChromaDB/Milvus/Elasticsearch/GaussVector）、关系（SQLite/PG/MySQL/GaussDB）、消息、图（Milvus）；版本化迁移框架；文件系统后端（记忆落 markdown + SQLite FTS5）；
- **安全**：AES-256-GCM 透明加密、KV 分布式锁、`scope_id` 多租户隔离；
- **接入**：PyPI `JiuwenMemory`（extras: sqlite/postgres/mysql/gaussdb/redis/chromadb/file-index/server/all）；`memory-server` 一键 REST 服务；`memory-mcp` 一键 MCP 服务（Claude Code/Codex/Cursor 直连）；OpenClaw 生命周期插件（回复前注入、回复后提取）；Plugin/Provider 双维度解耦（MemoryProvider 可换 Mem0/openViking/AgentArts）。
- 使用示例（节选）：`LongTermMemory()` → `register_store(kv, db, vector, embedding)` → `add_messages(UserMessage..., user_id, scope_id, session_id)` → `search_user_mem(query)`，自动产出 `[user_profile]`/`[episodic_memory]` 等记忆并可语义检索。

### 4.7 deepsearch —— 深度检索与研究

- 三个子项目：**DeepSearch**（深度研究引擎：多步多源验证、结构化研究报告、**段级引用溯源**与置信度、规划期自然语言反馈交互）、**CodeSearch**（代码定位 Agent：输入 Issue 描述→输出"看哪些文件哪些行"；Agentic 多轮检索 + 双模型协同控成本；语法感知分块 + 双路稀疏 BM25 + 增量索引；**同一逻辑双引擎实现**——工作流图引擎与纯代码循环引擎，测试锁定字节级一致输出；SDK/CLI/HTTP 服务/容器四种形态）、**openjiuwen-search-base**（共享基座：LLM 客户端/embedding(SQLite 缓存)/Milvus 安全查询/workflow 节点模板/日志脱敏，命名空间隔离多产品共享 Milvus）；
- 已验证模型：Qwen3.7-Max（推荐）、Qwen3.8-Flash、GLM-5.3/5.3-Flash/5.2/5.1/5、DeepSeek V3.2、Kimi-K2.5；
- 典型场景：金融研报（本地投研知识库 + 生成图表报告）、学术/政策研究、复杂决策查询、Bug 定位、大库导航。

### 4.8 agent-protocol —— 互操作协议 SDK（C++ 为主）

| 组件 | 语言 | 能力 |
|---|---|---|
| **MCP C++ SDK** | C++17/CMake | MCP 客户端+服务端，Streamable HTTP 与 stdio 传输，鉴权、Sampling、进度通知、Roots |
| **A2A C++ SDK** | C++17/CMake | Agent2Agent：HTTP+JSON-RPC，Agent Card 发现、消息/任务查询取消、流式事件、请求拦截器、自定义任务存储 |
| **A2X Registry** | Python | Agent 服务注册中心：注册/注销/查询、服务卡片、online/busy/offline 状态、所有权访问控制、Agent Team 短时预订锁；**层次化能力目录 + LLM 语义导航**（自然语言逐层定位服务）、可选向量检索、Web UI |
| **A4P Python SDK** | Python | Agentic 认证授权审计协议：Operation Mandate（操作授权）+ Intent Mandate/Token（意图授权）；Ed25519 签名授权对象、WebAuthn/passkey、参数范围校验、SQLite 原子消费次数限制、prepare/complete 两阶段异步用户确认 |

C++ SDK 选型体现华为在端侧/低资源环境的诉求（鸿蒙/车机/嵌入式 Agent 互操作）。

### 4.9 skillhub —— Agentic Hub 技能资产平台

- 六类资产：**Skill、SwarmSkill、插件、连接器、专家、专家团**；发布/审核/版本/检索/推荐/下载/在线体验/群组授权分发；
- 模块：marketplace（FastAPI+SQLAlchemy）、frontend（React 18+Vite+MUI）、CLI `agentichub`（脚手架/校验/打包/发布/检索/安装/导入，PyPI `openjiuwen-agentichub`）、skill-runner（在线体验沙箱运行时：会话编排、沙箱执行、流式输出）；
- 依赖 MySQL + S3 兼容存储（MinIO/**华为云 OBS**）+ 可配置鉴权服务；Docker Compose 一键部署；**ClawHub 兼容协议**可选启用；官方托管实例 agentichub.openjiuwen.com；
- 治理特性：火爆值热门排序、官方徽标、审核状态机、操作审计、Git 仓库批量导入同步。

### 4.10 其他仓库速览

- **iCode**（359★）：终端 TUI 开发平台（类 Claude Code），"Agent 即配置而非代码"（F2 编辑 instructions/tools/sub-agents/skills/MCP/memory），模型 F4 热切换、Diff 视图、回滚、Trajectory（时间/Token 归因）、工作流逐节点可视化；全离线、数据自持；
- **sciencediscovery**（172★）：科研工作台，基于 JiuwenSwarm；文献→假设→沙箱代码→实验，Reviewer/Provenance 面板全程留痕；单二进制 + Bubblewrap 沙箱，本地运行数据不出机器；
- **agentos-enterprise**：多用户 Agent OS（多系统部署、统一入口）；
- **agent-infer**：vLLM 系 Agentic 推理框架；**model-router**：逐请求模型选择内核；**agent-dx**（Rust）：分布式执行 substrate；
- **agent-tools**：`openJiuwen-vllm-affinity`（KV-Cache 感知亲和调度）、`infer_router`、reward_tool、dev_tools_suite（skills/日志采集解析）+ 比赛样例。

---

## 5. 关键能力清单（对照调研问题）

| 能力域 | openJiuwen 提供 | 落点（仓库/模块） |
|---|---|---|
| Agent 开发框架 | ReActAgent、WorkflowAgent、ContextEvolvingAgent、DeepAgent、自定义 Agent/组件 | agent-core |
| Workflow 编排 | 代码级图编排（Pregel 异步并行、批流混合、断点恢复）+ Studio 拖拽画布 + Swarmflow 多阶段脚本编排 | agent-core/core/workflow、agent-studio、agent_teams/workflow |
| 记忆 | L0–L3 分层、睡时巩固、MemoryTurbo、图谱记忆、冲突检测、多后端、MCP 服务化 | agent-memory、agent-core/core/memory |
| 工具调用 | 本地工具/REST 封装/MCP 客户端服务端/工具审批护栏/白名单 | agent-core/foundation/tool、agent-protocol、harness |
| 多 Agent 协作 | TeamRuntime + P2P/Pub-Sub、Agent as Tool、层次化/Handoff 预置模式、蜂群团队（Leader/Teammate、跨机分布式、外部成员 MCP/CLI 接入）、专家团队 | agent-core/core/multiagent、agent_teams |
| 记忆上下文工程 | ContextEngine（多上下文、窗口裁剪、摘要卸载、六级压缩处理链） | agent-core/context_engine、harness/rails |
| 技能资产化 | Agent Skill/Swarm Skill 标准（SKILL.md）、自演进、Hub 托管分发（兼容 ClawHub） | agent-core、skillhub、swarmskills.openjiuwen.com |
| 自进化 | Prompt/工具/Skill 优化器、经验沉淀、轨迹（OTLP）、离线/在线 RL、Auto Harness | agent-core/agent_evolving、auto_harness |
| 服务化与部署 | subprocess/docker/k8s 部署、多租户、生命周期管理、Java 运行时 | agent-runtime(-java) |
| 互操作协议 | MCP/A2A C++ SDK、A2X 注册发现（LLM 语义导航）、A4P 可验证授权 | agent-protocol |
| 可视化开发 | 零码/低码平台（画布、Prompt 工程、知识库、插件市场、资源管理） | agent-studio |
| 可观测/评测 | OTel 全链路、会话调测、评测体系、Agent Ops（部分待开源） | extensions/tracer_otel、agent_evolving/evaluator |
| 终端/桌面产品 | TUI + 桌面端 + IM 渠道（9 个平台）+ 鸿蒙 | jiuwenswarm、iCode |
| 推理基础设施 | vLLM 亲和调度、模型路由、Agentic 推理框架 | agent-tools、agent-infer、model-router |
| 深度场景智能体 | 蜂群助手、深度检索研究、代码搜索、科研工作台、具身智能 | jiuwenswarm、deepsearch、sciencediscovery、jiuwensymbiosis |

---

## 6. 上手方式汇总

| 形态 | 命令/入口 |
|---|---|
| Python SDK | `pip install -U openjiuwen`（要求 Python 3.11–3.14，推荐 3.11.4） |
| Java SDK | Maven 依赖 `com.openjiuwen:agent-core-java`（Java 17+，源码 `mvn clean install`） |
| JiuwenSwarm | `pip install workswarm` → `jiuwenswarm-init` → `jiuwenswarm-start` → http://localhost:5173 ；桌面版官网下载（Win/macOS/鸿蒙） |
| 记忆服务 | `pip install "JiuwenMemory[server]"` → 配置 `~/.jiuwenmemory/.env` → `memory-server`（REST）或 `memory-mcp`（MCP） |
| Studio 平台 | 克隆 agent-studio → `docker/package.sh`、`build.sh`、`deploy/deploy.sh local`（四服务） |
| Runtime | `bash scripts/run-server.sh`（server/.env 配置 DB/地址） |
| DeepSearch | SDK 安装或 `codesearch index --repo ... && codesearch search --collection ... --query ...` |
| Skill 市场 | 浏览 agentichub.openjiuwen.com 或自建 Docker Compose；CLI `agentichub` |
| harness CLI | `openjiuwen` 命令（agent/prompts/rails/storage/ui 子命令）；`team-member`、`openjiuwen-team-mcp` |

模型接入统一走 `ModelClientConfig(client_provider, api_key, api_base)`，支持华为云 MaaS、Pangu、Qwen、DeepSeek、GLM、Kimi、OpenAI 兼容 API 与本地模型；官方反复强调"本产品仅作为流程编排工具，不包含 AI 模型能力"（欧盟 AI 法案合规免责）。

---

## 7. 典型应用场景

**官方场景（docs/产品简介）**
- ToC：聊天助手、文本生成、智能助手（日程/查询/事务）；
- ToB：金融（多级意图跳转、动态 Agent 调度，高精度低时延）、医疗（病历摘要、影像初筛、诊疗辅助决策）；制造等多行业（828 B2B 企业节宣传：加速制造、医疗、金融行业 Agent 应用）。

**examples 体现的场景**（agent-core 26 例 + Java 32 例）
- 天气助手（ReAct+REST/MCP 工具）、金融 WorkflowAgent、NL2SQL（rl_nl2sql）、代码智能（harness worktree、lsp、沙箱）、多 Agent 协作（团队/层次化/自适应协同）、技能创建与评估、技能热重载（Java）、多模态推理、移动端 GUI Agent（mobile_gui）、强化学习在线服务、具身/物理 AI（jiuwensymbiosis）、科研自动化（sciencediscovery）、深度行业研报（deepsearch）。

**生态应用**
- 小艺 Work 超级智能体（小艺团队 × 九问团队联合打造，via OSCHINA 报道）；
- JiuwenSwarm 接入 9 大 IM 渠道成为个人/团队 Agent 入口；
- ChatBI 等企业平台教程（社区实践：openJiuwen + 华为云 ModelArts Studio 接入 Qwen）。

---

## 8. 与其他 Agent 框架的对比

| 维度 | openJiuwen | LangChain/LangGraph | AutoGen | Dify/Coze |
|---|---|---|---|---|
| 形态 | **全栈平台**（SDK+低码平台+运行时+Ops+资产市场+终端产品） | 代码框架/编排库 | 多 Agent 对话框架 | 低码 SaaS/自托管平台 |
| 语言 | Python + Java + C++（协议）+ Rust/Angular/TS 周边 | Python/JS | Python/.NET | SaaS，少 SDK |
| 工作流引擎 | 自研 Pregel 异步图 + 批流混合组件模型 + Swarmflow；断点恢复 | LangGraph（Pregel 思想同源） | 无强工作流 | 可视化工作流 |
| 多 Agent | 蜂群组织（Leader/Teammate/任务池/共享工作空间/跨机 pyzmq/外部成员 MCP 接入）+ 三种预置模式 | 需自建（LangGraph 平台化收费） | 对话式协作较强 | 偏简单编排 |
| 记忆 | **独立子系统**：L0–L3 分层+Dreaming+图谱+多后端+MCP 服务 | 基础 Memory 类 | 基础 | 内置会话记忆 |
| 自演进 | **独有重点**：Skill/SwarmSkill 自演进、经验沉淀、在线/离线 RL（Ray/verl）、Auto Harness | 无原生 | 无 | 无 |
| 可视化开发 | agent-studio（开源可私有化） | LangSmith/LangGraph Studio（商业） | AutoGen Studio（轻量） | 强项 |
| 生产运行时 | agent-runtime：多租户、3 种部署策略、发布管控（开源） | LangGraph Platform（商业） | 需自建 | 内置（SaaS 为主） |
| 协议生态 | MCP + **A2A C++ SDK + A2X 注册发现 + A4P 授权**（独有） | MCP 为主 | A2A 支持 | 插件/MCP |
| 生态亲和 | 华为系：GaussDB/openGauss、OBS、华为云 MaaS、Pangu、小艺、鸿蒙、昇腾（Affinity-Scheduler/KV-Cache 亲和） | 云中立 | 云中立 | 云中立 |
| 许可/治理 | Apache 2.0，CLA+SIG（类 openEuler 治理） | MIT | MIT/Apache | 部分闭源 SaaS |

**差异点/特色总结**：
1. **"三位一体"最完整**：同时开源"低码平台 + 高码 SDK + 分布式运行时 + 资产市场"，且低码平台与 SDK 共享同一引擎（Studio 的 runtime 就是 agent-runtime 嵌 agent-core），避免 Dify 类平台"低码孤岛"；
2. **能力资产化与自演进**是最大记忆点：Skill/SwarmSkill 把单 Agent 能力和团队协作方式都变成可沉淀、可流通、可自演进的资产，配套 Hub 与在线演进轨道，甚至引入 RL 训练 Agent（国内开源界少见）；
3. **记忆系统独立成库且深度大**：L0–L3 + 睡时巩固 + 图谱记忆，工程化程度高于常见"Memory 类"实现；
4. **协议层下探到 C++**：MCP/A2A C++ SDK + 可验证授权（A4P），瞄准端侧/具身/鸿蒙场景的互操作与安全；
5. **华为全栈亲和**：GaussDB/OBS/MaaS/昇腾亲和调度，但接口保持 OpenAI 兼容，不锁定；
6. **ToC 触达**：桌面版 + 小艺/微信/飞书等 9 渠道 + TUI，是少数"框架+消费级产品"一体的开源项目。

**不足与风险**：
- 项目年轻（2025-12 开源），迭代极快，API 与仓名变动频繁（JiuwenClaw→JiuwenSwarm、studio-service 模块删除重组），兼容性承诺有限（agent-memory 明示 V1→V2 不兼容）；
- 部分"架构图能力"尚未开源（Agent Ops、Agent System Service/Agent POSIX、agent-gateway 标注待开源/Opening Soon），存在"图大于码"的情况；
- 文档以中文为主，英文跟随滞后；主托管在 GitCode，GitHub 为镜像，海外社区参与度有限（Stars 集中于 jiuwenswarm）；
- 贡献门槛：必须签 CLA、禁止合入自己的 PR、门禁流程较重（企业级治理风格）；
- 代码库庞大（24 仓、单仓最大 400MB），初学者认知成本高；jiuwenswarm 处于 beta 阶段。

---

## 9. 结论

openJiuwen 是华为将内部九问 Agent 技术体系（支撑小艺等 ToC 产品）系统化开源的成果，**目标是通过开源构建行业 Agent 生态，与华为云 AgentArts 商用版互补**。它的完成度超出 typical "大厂 KPI 开源"：核心 SDK（agent-core）有真实的图引擎、上下文/记忆/安全护栏、蜂群协作与 RL 自演进代码及大量可运行示例；Studio、Runtime、Memory、DeepSearch、SkillHub、协议 SDK 都是可独立部署的完整产品。对于**需要国产化技术栈、私有化部署、多 Agent 工程化落地、或记忆/自演进等前沿能力**的团队，openJiuwen 是目前中文开源生态中体系最完整的 Agent 平台之一；对于轻量场景，其 jiuwenswarm/iCode 终端产品可直接使用。后续值得跟踪的是 Agent Ops/AgentOS 底座的继续开源进度、API 稳定性承诺，以及 Skill 生态（Swarm Skills Hub）的实际繁荣程度。

---

## 附：调研资料来源

- 本地源码分析（浅下载后已删除）：openJiuwen-ai 组织 13 个仓库（agent-core、agent-core-java、agent-studio、agent-runtime、agent-memory、deepsearch、agent-protocol、skillhub、agent-tools、community、docs、iCode、sciencediscovery）
- GitHub 组织：https://github.com/openJiuwen-ai ；GitCode 主托管：https://gitcode.com/openJiuwen
- 官网：https://openjiuwen.com ；Skill 市场：https://swarmskills.openjiuwen.com / https://agentichub.openjiuwen.com
- 百度百科 openJiuwen 词条；OSCHINA（小艺 Work 与九问团队报道）；凤凰网（828 B2B 企业节发布）；Gitee openEuler/jiuwen-agentcore 建仓 issue（迁移 AtomGit）
- 注：因调研环境网络限制（git 协议阻断、/tmp 磁盘配额），`jiuwenswarm` 仓库源码未能完整下载，该部分结论基于其完整中英 README、官方文档索引及 agent-core 中同源的 agent_teams/swarmflow 引擎源码交叉验证得出，可信度标注为"高（框架层）/中（产品层细节）"。
