# DSL-G0 表达力评估：LangGraph StateGraph

> 任务：G0 自研必要性验证之一。对三篇代表性论文（ReAct / MetaGPT / AFlow），尝试用 LangGraph StateGraph（当前 1.x，2026-10 查证官方文档与源码）写出尽量完整的描述，按四维度判定表达力。
> 结论先行：**12 格中 0 格无条件"完整表达"，2 格场景限定下完整，其余 10 格均落在"需胶水代码"档；缺口集中在 L1 契约层与 L0 不变量层——恰是我们四层 DSL 的价值区。LangGraph 可作 L3 执行内核候选，不可作 DSL 本体。**
> 身份：DSL-Compiler 团队对齐代理（探针分支）｜日期：2026-10-24｜本文件为任务书授权的唯一写入文件。

---

## 0. 方法与口径

- **查证来源**（均为 2026-10-24 实际抓取）：
  - 图 API：docs.langchain.com/oss/python/langgraph/graph-api.md、use-graph-api.md
  - 运行时：docs.langchain.com/oss/python/langgraph/pregel.md
  - 容错：docs.langchain.com/oss/python/langgraph/fault-tolerance.md（注明多数节点级特性要求 `langgraph>=1.2`）
  - 子图：docs.langchain.com/oss/python/langgraph/use-subgraphs.md
  - 中断：docs.langchain.com/oss/python/langgraph/interrupts.md
  - 错误页：…/errors/INVALID_CONCURRENT_GRAPH_UPDATE、…/errors/GRAPH_RECURSION_LIMIT
  - 源码：github.com/langchain-ai/langgraph `libs/langgraph/langgraph/graph/state.py`（`attach_node`）、`channels/last_value.py`
  - 版本口径：docs.langchain.com/oss/python/releases/langgraph-v1（create_react_agent 弃用）；docs.langchain.com/oss/python/langchain/middleware/overview
- **判档三档**：完整表达 / 需胶水代码（注明量与脏度）/ 不可表达。"胶水代码"= 图模型之外的节点函数内逻辑、包装器、外层 Python 循环；框架不感知、不校验、不保证。
- **不确定的一律标"待验证"**，不猜 API。
- 本环境未安装 langgraph 实测（任务书允许文档法）；代码为按文档写出的描述性代码，**未运行**。

## 1. LangGraph StateGraph 核心模型（判定的事实基础）

| 机制 | 文档确认的事实 | 对判定的含义 |
|---|---|---|
| 状态定义 | `StateGraph(state_schema)`；键为 TypedDict/dataclass/Pydantic 字段；`Annotated[T, reducer]` 声明归并函数（`operator.add`、`add_messages` 或任意二元函数）；无 reducer 的键默认 `LastValue` 通道（源码 `_get_channel`：`fallback: LastValue = LastValue(annotation)`） | reducer 是声明式的；但它是"多写合法化"机制，不是"多写禁止"机制 |
| 图级 I/O | `StateGraph(OverallState, input_schema=InputState, output_schema=OutputState, context_schema=ContextSchema)`；`compile()` 强制（"You MUST compile your graph"） | 图边界契约可声明；**内部拓扑仍只存在于 Python builder 调用序列中** |
| 节点输入 | 节点函数可声明子集 schema 类型注解；源码 `attach_node`：`input_channels = list(self.builder.schemas[input_schema])`，PregelNode 只订阅这些通道——**注解过滤是运行时真过滤，非文档装饰** | 读侧上下文选择是原生声明式（维度 3 的关键正面证据） |
| 节点输出 | 节点返回部分更新 dict；文档原文："a node *can write to any state channel in the graph state*" | **无写权限模型**（维度 2 的关键反面证据） |
| 校验 | Pydantic 状态校验"only occurs on inputs to the first node in the graph, not on subsequent nodes or outputs" | 节点间流转的结构契约不校验（维度 1 反面证据） |
| 路由 | `add_edge` / `add_conditional_edges(路由函数)` / 节点内 `Command(update=…, goto=…, graph=…, resume=…)` / 动态 fan-out `Send(node, arg)` | 路由逻辑一律是 Python 代码，无声明式谓词 |
| 并发语义 | Pregel superstep：Plan→Execution→Update；同 superstep 并发写非 reducer 键不同值 → `InvalidUpdateError`（错误码 `INVALID_CONCURRENT_GRAPH_UPDATE`；last_value.py 原文 "Can receive only one value per step. Use an Annotated key to handle multiple values."）；superstep 事务性（任一分支异常则全组更新不落） | 并发冲突有运行时保护；**顺序覆盖写永远静默** |
| 预算 | 唯一步数预算：`config={"recursion_limit": N}`（RunnableConfig 字段，默认 25，超限 `GraphRecursionError`）；时间预算 `timeout=`/`TimeoutPolicy(run_timeout=, idle_timeout=)`（仅 async 节点）；**无 token/成本预算 API**（runtime 文档全篇无 budget 概念） | 预算契约只有"步数+时钟"，无"钱" |
| 失败 | `retry_policy=RetryPolicy(max_attempts=3, initial_interval=0.5, backoff_factor=2.0, jitter=True, retry_on=异常类型/谓词)`；`error_handler=(state, error: NodeError) -> Command`（1.2+，可 `goto` 补偿节点）；`set_node_defaults(…)`；fallback 靠 `runtime.execution_info.node_attempt` 手写 | 失败分类=异常分类；无语义失败 taxonomy |
| 隔离 | 子图 `add_node(compiled_subgraph)` 共享同名通道；不同 schema 则节点内 `subgraph.invoke({...})` 手动映射（文档明言用途："keep a private message history for each agent"）；私有通道键可藏于内部 schema；**"Private channels are not redacted when streaming"**（需手动 `output_keys`） | 结构性隔离可行；泄露面需手动关 |
| 人审/暂停 | `interrupt(payload, response_schema=…)`（response_schema 要求 ≥1.2.12，恢复值按 schema 校验）；`compile(interrupt_before=[…], interrupt_after=[…])` 已降级为调试用（官方明言不建议用于 HITL） | 类型化门禁只覆盖"恢复值"，不覆盖 agent 间交接 |
| 拓扑表示 | 官方 API 为命令式 builder（`add_node`/`add_edge`）；无第一方 YAML/JSON 声明式定义；`get_graph()` 仅可视化 | **图不是一阶数据**（维度 4 / AFlow 的核心缺口） |
| 预制件 | `langgraph.prebuilt.create_react_agent` 已弃用 → `langchain.agents.create_agent`（v1.0，middleware 体系：`SummarizationMiddleware`、`HumanInTheLoopMiddleware` 等） | 上下文压缩/调用限额存在，但在 prebuilt agent 层，不在 StateGraph 层 |

---

## 2. 三篇 × 四维度矩阵（总表）

判定：**完**=完整表达；**胶**=需胶水代码（括注量与脏度）；**不**=不可表达。细节证据见 §3–§5。

| 维度 | ReAct (Yao 2022) | MetaGPT (Hong 2023) | AFlow (Zhang 2024) |
|---|---|---|---|
| **D1 契约层**（I/O schema/预算/停止/失败分类重试） | 胶（中）——schema✓、步数✓；token/成本✗；停止条件=路由代码；重试按异常不按语义 | 胶（中重）——schema✓但**节点间更新不校验**（关键缺）；预算✗；SOP 停止trivial | 胶（重）——搜索预算（迭代/评估成本）全在图外 Python；仅 recursion_limit 管单候选执行 |
| **D2 不变量强制**（多写者禁止/生成-验证隔离/评估隔离） | 胶（重）——并发冲突有运行时保护；**写权限不可声明**（"any node can write to any channel"）；顺序覆盖静默 | 胶（重）——读隔离✓（注解过滤，原生）；"QA 不得改 PRD"✗；发布-订阅触发✗需手写条件边 | 胶（重）——评估器与候选的隔离可靠子图边界达成；但"候选不得读 score 通道"无声明式保证 |
| **D3 上下文组装**（全量/选择性/摘要的声明式控制） | 胶（轻）——选择性通道✓声明式（注解过滤）；摘要/压缩✗（SummarizationMiddleware 在 prebuilt 层，StateGraph 需自写节点） | **完（场景限定）**——SOP 恰只需"每角色见指定结构化产物"，通道子集+子图完整覆盖；注：声明粒度=通道集合，无脱敏/配额策略 | **完（场景限定）**——操作符间精确数据流=`Send` 传参+注解过滤，原生；AFlow 无摘要需求 |
| **D4 拓扑与角色**（读写权限/typed handoff） | 胶（轻）——agent↔tools 环✓；单体无 handoff 需求；人审有 `interrupt(response_schema)` | 胶（中）——流水线拓扑✓；typed handoff 只能编码为 state 键更新（`Command.update` 即 dict），信封无独立类型 | 胶（重，含根本性缺失）——拓扑编译期冻结，每候选 rebuild+recompile 可跑通；但**"图作为可被 LLM 产出/变异的一阶数据"无任何原生表示** |

---

## 3. ReAct：StateGraph 描述与逐格证据

### 3.0 尽量完整的描述（描述性代码，未运行）

```python
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class ReActState(TypedDict):
    messages: Annotated[list, add_messages]   # 唯一声明式的东西：消息归并 reducer
    step_count: int                            # 步数要自己数——框架只有 recursion_limit

MAX_STEPS = 10

def agent_node(state: ReActState) -> dict:                 # 思想+行动
    resp = llm.bind_tools(TOOLS).invoke(state["messages"])
    return {"messages": [resp], "step_count": state["step_count"] + 1}

def tool_node(state: ReActState) -> dict:                  # 观察
    results = execute_tool_calls(state["messages"][-1])
    return {"messages": results}

def route(state: ReActState):                              # 停止条件=Python 函数
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END

g = StateGraph(ReActState)
g.add_node("agent", agent_node)   # retry_policy=RetryPolicy(...) 可挂，见 3.1
g.add_node("tools", tool_node)
g.add_edge(START, "agent")
g.add_conditional_edges("agent", route, ["tools", END])
g.add_edge("tools", "agent")
app = g.compile()
# 步数预算：config 一部分（默认 25，超限 GraphRecursionError）
app.invoke({"messages": [user_msg], "step_count": 0},
           config={"recursion_limit": 2 * MAX_STEPS})
# 注：等价 prebuilt 为 langchain.agents.create_agent（v1.0 起）；
# langgraph.prebuilt.create_react_agent 已弃用（releases/langgraph-v1）。
```

### 3.1 D1 契约层 —— 判定：需胶水代码（中）

- **I/O schema：✓ 声明式**。`StateGraph(ReActState, input_schema=…, output_schema=…)` 可收窄图边界（graph-api.md）。
- **步数预算：✓**。`recursion_limit`（RunnableConfig，默认 25，`GraphRecursionError`；errors/GRAPH_RECURSION_LIMIT、reference.langchain.com RunnableConfig/recursion_limit）。但这是 superstep 数不是"动作数"，语义错位：一次 fan-out 会多耗配额，需自己换算。
- **token/成本预算：✗ 无 API**。反例：不存在 `budget={"total_tokens": …}` 之类参数——pregel.md（运行时文档）全篇只有步数上限与超时（`TimeoutPolicy(run_timeout=, idle_timeout=)`）。计数只能在节点函数里自管（`step_count` 键即胶水证据）。prebuilt 层的 `ModelCallLimitMiddleware`/`ToolCallLimitMiddleware`（langchain.agents.middleware，middleware/overview 页列出）只覆盖 `create_agent` 内部循环，**不是 StateGraph 图级机制**——名字与覆盖范围待验证（来源含第三方汇总）。
- **停止条件：胶水**。"Final Answer 即停"编码为 `route()` 路由函数——图模型里它是不可省略的 Python 谓词；无声明式 stop-when 谓词。
- **失败分类与重试：半✓**。`RetryPolicy(max_attempts=3, backoff_factor=2.0, retry_on=…)` 可挂 `add_node`（fault-tolerance.md），`retry_on` 是**异常类型/谓词**；"动作非法"这类语义失败不是异常，要么自己 raise 要么在 route 里判——taxonomy 无处声明。`error_handler=(state, error: NodeError) -> Command`（1.2+）能把失败路由到补偿节点，但分类维度仍是异常对象。

### 3.2 D2 不变量强制 —— 判定：需胶水代码（重）

- **多写者禁止：✗（声明式）**。文档原文："a node *can write to any state channel in the graph state*"（use-graph-api.md）。反例：
  ```python
  def tool_node(state: ReActState) -> dict:
      return {"step_count": 999}   # 完全合法：工具节点改写 agent 的计数，无任何声明可拦
  ```
  唯一保护是**同 superstep 并发**写 `LastValue` 键不同值时报 `InvalidUpdateError`（INVALID_CONCURRENT_GRAPH_UPDATE；last_value.py 原文见 §1）；顺序执行中后写静默覆盖。要强制"单写者"只能自写包装器（检查返回 dict 键集 ⊆ 白名单，越权 raise）——纯胶水纪律，框架不保证。
- **生成者/验证者上下文隔离：✓（结构上）**。`tool_node` 声明子集注解即只见通道子集（源码 `attach_node` 证实运行时过滤）；或把 agent 包成子图私有 messages 历史（use-subgraphs.md）。但这是"结构可达"，不是"权限声明"——无 `allow_read=["messages"]` 之类语法。
- **评估逻辑与被评估对象隔离：✓（结构上）**。ReAct 无内置评估者；可表达为父图中的 evaluator 子图，候选轨迹走 `input_schema` 进、score 出。缓解：流式时私有通道不自动隐藏（"Private channels are not redacted when streaming"），防泄露要手动 `output_keys`——又一个易漏的手工步骤。

### 3.3 D3 上下文组装 —— 判定：需胶水代码（轻）

- **选择性通道：✓ 声明式**。节点签名 `def tool_node(state: ToolInput)` → 只读 `ToolInput` 列出的通道（运行时过滤，源码证实）。这是 LangGraph 少有的真声明式上下文控制。
- **摘要/压缩：✗（StateGraph 层）**。长程 ReAct 需要上下文修剪；`SummarizationMiddleware`（langchain.agents.middleware，官方 middleware/overview）只服务 `create_agent` prebuilt；StateGraph 路线要自写 summarizer 节点+消息改写逻辑——胶水。全量/选择/摘要三态中前两态声明式可达，第三态不可。

### 3.4 D4 拓扑与角色 —— 判定：需胶水代码（轻）

- **拓扑：✓ 完整**。agent→tools→agent 环 + 条件出边是 StateGraph 教科书场景（use-graph-api.md 并行/环示例）。
- **角色读写权限：✗**（同 3.2，ReAct 里 agent/tools 双写 `messages` 即常态多写，靠 `add_messages` reducer 合法化——多写不是被禁止而是被归并）。
- **typed handoff：n/a（单体）**；最近似物是 `interrupt(payload, response_schema=Decision)`——人审恢复值可类型化校验（interrupts.md，≥1.2.12），说明"带 schema 的交接"在恢复值一处有官方支持，但节点间交接无对应物。

---

## 4. MetaGPT：StateGraph 描述与逐格证据

### 4.0 尽量完整的描述

```python
from pydantic import BaseModel

class PRD(BaseModel): ...            # 结构化中间产物
class DesignDoc(BaseModel): ...
class QAReport(BaseModel): ...

class SOPState(TypedDict):
    prd: PRD; design: DesignDoc; code: str; qa: QAReport

# 每个角色声明自己"看得见什么"——读隔离的唯一声明手段
class ArchitectInput(TypedDict):
    prd: PRD                          # 架构师只看 PRD，看不到 PM 的草稿通道（若另设草稿键）

def pm_node(state: dict) -> dict:
    # 结构化产物契约只能靠节点内 LangChain API 强制：
    prd = llm.with_structured_output(PRD).invoke(PROMPT_PM)
    return {"prd": prd}               # 图层不校验这个 update（见 4.1 反例）

def architect_node(state: ArchitectInput) -> dict: ...
def engineer_node(state: EngineerInput) -> dict: ...
def qa_node(state: QAInput) -> dict: ...

g = StateGraph(SOPState)
g.add_node("pm", pm_node)
g.add_node("architect", architect_node)
g.add_node("engineer", engineer_node)
g.add_node("qa", qa_node)
g.add_edge(START, "pm")
g.add_edge("pm", "architect")          # SOP 顺序=静态边
g.add_edge("architect", "engineer")
g.add_edge("engineer", "qa")
g.add_edge("qa", END)
app = g.compile()
```

### 4.1 D1 契约层 —— 判定：需胶水代码（中重）

- **I/O schema：半✓，关键缺**。产物类型可进 state schema（Pydantic 支持），但官方明确："Validation only occurs on inputs to the first node in the graph, not on subsequent nodes or outputs"（use-graph-api.md）。反例：`engineer_node` 返回 `{"design": {"garbage": 1}}` 不会在校验层被拒——MetaGPT 的核心卖点（结构化产物契约）在图层**不可强制**，只能每节点内 `with_structured_output` + 手动重试。这是"契约写在图外"的典型脏胶水。
- **预算：✗**（同 3.1，无 token/成本 API；SOP 规模大，PRD 全文进下游，无预算约束后果比 ReAct 更重）。
- **停止条件：✓（trivial）**。线性 SOP 以静态边+END 表达，无需谓词——这是三篇里唯一不需要停止条件胶水的场景。
- **失败分类与重试：同 3.1**（RetryPolicy 异常级；error_handler 可路由返工节点，勉强映射 MetaGPT 的"QA 打回重做"→ `error_handler` 里 `goto="engineer"` 是一个可行胶水）。

### 4.2 D2 不变量强制 —— 判定：需胶水代码（重）

- **读隔离（角色只见自己订阅的产物）：✓ 原生**。`ArchitectInput` 注解 → `attach_node` 只订阅 `prd` 通道（源码证实）。对应 MetaGPT 的角色订阅语义，这是三格判定里最强的原生支持。
- **写权限（"QA 不得改 PRD"）：✗**。反例：
  ```python
  def qa_node(state: QAInput) -> dict:
      return {"prd": my_own_prd}    # 合法。LastValue 顺序覆盖，静默通过
  ```
  MetaGPT 论文里角色对产物的所有权是 SOP 定义的一部分；LangGraph 无任何声明式 owner/writer 白名单（"any node can write to any channel"）。只能自写包装器——每角色一个，纯纪律。
- **发布-订阅触发（上游产物变更自动通知订阅角色）：✗**。MetaGPT 环境按消息 tag（cause_by）路由；LangGraph 唯一路由机制是条件边/Command——依赖关系要人工编码成边与谓词，订阅是一等概念的缺失（工程量型缺口，见 G8）。
- **多写者**：消息池语义在 LangGraph 里反而更严（并发冲突报错+事务 superstep），此子项优于原论文实现。

### 4.3 D3 上下文组装 —— 判定：完整表达（场景限定）

SOP 需要的恰好是"每角色看到指定结构化产物的集合"——`input_schema` 注解 + 图级 `input_schema/output_schema` + 私有键（内部 schema）三层原生覆盖；MetaGPT 不需要摘要压缩。限定条件：声明粒度=通道集合，无"脱敏/截断/配额"等视图策略（要就自写节点）；prompt 拼装本身属 L3 实现层，任何图 DSL 相同，不计罚。若未来 SOP 引入长产物摘要需求，此格退化为胶（轻）。

### 4.4 D4 拓扑与角色 —— 判定：需胶水代码（中）

- **拓扑：✓**。PM→架构师→工程师→QA 静态边；返工环用 `add_conditional_edges`。
- **typed handoff：半✓**。`Command(update={"prd": prd_obj}, goto="architect")` 可在节点内同时完成更新+路由（graph-api.md），载荷可为 Pydantic 对象；**但信封无独立类型**——`update` 就是 state 键 dict，"这是一份交接、来自谁、要求什么"没有 schema 位置（MetaGPT 的 Message 有 cause_by/send_to 元数据）。接收方也无法声明"我只接受某类信封"。typed resume 只有 `interrupt(response_schema=)` 一处。
- **角色读写权限：✗**（同 4.2）。

---

## 5. AFlow：StateGraph 描述与逐格证据

### 5.0 尽量完整的描述

AFlow 的结构分两层：**候选工作流**（操作符节点+数据流边）与**搜索元循环**（LLM 变异拓扑→执行→验证集打分→经验驱动扩展）。StateGraph 只能覆盖第一层：

```python
# ── 层1：单个候选工作流（可表达）──────────────────────────
class WFState(TypedDict):
    problem: str
    answers: Annotated[list, operator.add]   # map-reduce 聚合
    scores: Annotated[list, operator.add]

def build_workflow(op_graph: dict) -> StateGraph:
    """op_graph: {"nodes": [("gen1", Ensemble), ...], "edges": [(0,1),...]}
       由自造的拓扑 schema 翻译成 builder 调用——这一层翻译器是自研胶水"""
    g = StateGraph(WFState)
    for i, (name, op) in enumerate(op_graph["nodes"]):
        g.add_node(name, make_op_node(op))                 # make_op_node=操作符→节点函数
    for src, dst in op_graph["edges"]:
        g.add_edge(f"n{src}", f"n{dst}")
    g.add_edge(START, "n0"); g.add_edge(f"n{len(op_graph['nodes'])-1}", END)
    return g

# ── 层2：搜索元循环（LangGraph 之外）────────────────────────
for iteration in range(MAX_ITER):           # 迭代预算：普通 Python
    op_graph = llm_mutate(experience_pool)  # 拓扑变异=LLM 产出自造 JSON → 翻译器
    app = build_workflow(op_graph).compile()  # 每个候选重新 build+compile（拓扑编译期冻结所致）
    traj = app.invoke(batch, config={"recursion_limit": 50})
    score = evaluate_on_validation(traj)      # 评估逻辑天然在图外（结构隔离的来源）
    update_experience(score, traj)
```

### 5.1 D1 契约层 —— 判定：需胶水代码（重）

- **搜索预算：✗**。AFlow 的核心预算是"迭代轮次×每轮验证集调用成本×token"——第一项是外层 `range()`，后两项无任何 API（pregel.md 无 budget 概念）。`recursion_limit` 只管单个候选的单次 invoke。
- **候选执行预算：半✓**（recursion_limit 步数 + TimeoutPolicy 时钟，同 3.1 的语义错位）。
- **停止/收敛条件：✗**。AFlow 的收敛判定（分数 plateau / 轮次上限）在图外 if 语句里。
- **失败分类与重试：同 3.1**；候选执行中途崩溃的记账（trail 记为无效样本）也是外层 try/except。

### 5.2 D2 不变量强制 —— 判定：需胶水代码（重）

- **评估者与被评估隔离：✓（结构上）**。评估函数在图外是天然隔离；若放进父图，可用子图+`input_schema` 保证候选子图拿不到验证集与 score 通道（use-subgraphs.md 的不同-schema 路线）。
- **声明式保证：✗**。"候选工作流禁止读 score 通道"没有声明语法——隔离的正确性依赖构造者纪律（子图边界搭对了才隔离），框架不检查意图。流式泄露（私有通道不 redact）同 3.2。
- **多写者**：AFlow 节点各自写独立输出槽，`Send` fan-out 写聚合键（`operator.add`）是官方 map-reduce 模式——多写归并✓；单写者约束同样不可声明。

### 5.3 D3 上下文组装 —— 判定：完整表达（场景限定）

AFlow 节点间是精确数据流：每个操作符只吃上游指定输出。`Send("op", {"problem": p, "chunk": c})` 逐实例定制状态 + 节点注解过滤通道，两层都是原生 API（graph-api.md Send 节、源码 attach_node）。AFlow 无摘要需求、无全量共享需求——三态中所需的那一态（选择性）完全声明式。这是三篇 12 格中表达力最好的场景。

### 5.4 D4 拓扑与角色 —— 判定：需胶水代码（重，含根本性缺失）

- **运行时拓扑变异：✗（原生）→ 胶水可达但脏**。StateGraph 拓扑编译期冻结："You MUST compile your graph before you can use it"（graph-api.md）；编译后无 add_node/remove_node API（文档与 reference 均无此 API；**待验证**：1.2+ DeltaChannel 是增量通道类型，与动态拓扑无关）。AFlow 每次变异产生新图 → 只能"每候选 rebuild+recompile"（§5.0 层2）。流程能跑通，故不判"不可表达"；但代价是：
  1. **图不是数据**：LLM 不能直接产出/变异 LangGraph 工作流——它产出的是自造 JSON，再经自研翻译器变成 `add_node/add_edge` 调用。这个"拓扑 schema + 翻译器"就是半个任务 DSL，官方无任何第一方表示（无 YAML/JSON 定义；get_graph() 只出可视化）。搜索算法直接操作的数据结构与执行引擎之间隔着自研转换层。
  2. 校验/预算/不变量在翻译层全部重新发明（回到 D1/D2 缺口）。
- **typed handoff：✗ 同 4.4**（Command.update 无信封类型）。
- **角色读写权限：✗ 同 3.2**。

---

## 6. 缺口清单（按严重度排序）

| # | 缺口 | 严重度 | 证据（均已在上文出现，此处给锚点） | 根本性/工程量 |
|---|---|---|---|---|
| G1 | **无 token/成本预算与声明式停止条件**。三篇论文的契约层都需要"花多少钱/多少步必须停"；LangGraph 只有 superstep 数（`recursion_limit`，默认 25）与墙钟（`TimeoutPolicy`），二者都非资源语义。`create_agent` 的 call-limit middleware 不在 StateGraph 层（名字待验证） | **高**——契约层地基缺失，任何严肃生产 agent 图都绕不开 | runtime 文档（pregel.md）无 budget 概念；errors/GRAPH_RECURSION_LIMIT；§3.1/§4.1/§5.1 | **根本性**：计费点必须进入执行内核（每次 LLM/工具调用挂钩），节点外包装器数不准并发与 prebuilt 内部调用 |
| G2 | **图不是一阶数据，拓扑编译期冻结**。LLM 产出/变异工作流（AFlow）、把图当配置分发、静态校验拓扑——全无官方表示层；builder 是命令式 Python，compile 强制 | **高**——AFlow 类自改进化、以及我们"配方即数据"的产品形态（底座纪律 §四：配方库随产品发行）直接被卡 | "You MUST compile"（graph-api.md）；无第一方 YAML/JSON（§1 拓扑行）；§5.4 | **根本性**：这不是缺库函数，是缺一个表示层——恰是 DSL 本体 |
| G3 | **节点间状态更新不校验**。Pydantic 校验只在图入口节点生效，"not on subsequent nodes or outputs"——L1 结构化契约（MetaGPT 产物）在图层不可强制 | **高**——契约写在图外=契约不存在；每节点内 `with_structured_output` 是约定不是保证 | use-graph-api.md 校验限制原文；§4.1 反例 | 根本性（校验语义缺位），但可用"节点出口 wrapper 调 pydantic"胶水补救——补救本身是工程量 |
| G4 | **无声明式写权限/单写者不变量**。"any node can write to any state channel"；LastValue 顺序覆盖静默；唯一保护是同 superstep 并发冲突报 `InvalidUpdateError`。生成者/验证者、评估者/被评估者的隔离只能靠子图结构纪律，流式还会泄露私有通道（需手动 `output_keys`） | **高**——L0 不变量层整体缺位；多智能体权限模型（QA 不得改 PRD、候选不得读 score）无处安放 | "any node can write to any channel"原文；last_value.py 错误原文；"Private channels are not redacted when streaming"；§3.2/§4.2 反例 | **根本性**：默认覆盖写是框架哲学（LastValue），叠加权限层与之对抗而非承接 |
| G5 | **失败分类=异常分类**。`RetryPolicy.retry_on` 是异常谓词，`error_handler`（1.2+）路由也基于异常对象；"格式非法/越权/超预算/语义不合格"等论文级失败 taxonomy 无声明位置，只能节点内自编枚举 | **中**——有重试与补偿的机制骨架，缺分类维度 | fault-tolerance.md（RetryPolicy 参数表、NodeError 字段仅 node/error）；§3.1 | 大半工程量（在骨架上叠加分类通道），分类schema本身需要 DSL 层定义——半根本性 |
| G6 | **上下文视图无策略层**。选择性通道✓（注解过滤），但视图策略只有"键集合"一种粒度：无脱敏、无摘要、无配额、无条件裁剪的声明位；摘要机制在 prebuilt 层（SummarizationMiddleware）不通用 | **中**——长程 agent 实际会退化到自写摘要节点 | attach_node 源码（过滤=键集合）；middleware/overview（摘要属 create_agent）；§3.3 | 工程量（可在键集合之上叠视图 DSL）；但"策略进内核 vs 节点胶水"的边界要我们 DSL 裁决 |
| G7 | **typed handoff 无信封类型**。`Command(update=…, goto=…)` 的载荷就是 state 键 dict；无"这是哪类交接/来自哪个角色/接收方声明接受哪类信封"的 schema 位置；typed resume 仅 `interrupt(response_schema=)` 一处 | **中低**——可编码但类型系统不覆盖 agent 间通信 | graph-api.md Command 节；interrupts.md response_schema；§4.4 | 半根本性（需在 state 键之外引入信封类型层=DSL 概念）；纯胶水只能做到"键约定" |
| G8 | **发布-订阅式角色触发缺位**（MetaGPT 订阅 tag 通知）。唯一路由机制是条件边/Command/Send，依赖关系人工编码；工程量随角色×产物矩阵增长 | **低-中**——条件边总能实现，只是脏且不可静态分析 | use-graph-api.md（路由机制清单）；§4.2 | 工程量（声明式依赖触发是 DSL 可加的表层特性） |

**待验证汇总**：① `ModelCallLimitMiddleware`/`ToolCallLimitMiddleware` 的确切名称与是否作用于 StateGraph 图级（来源官方页仅确认 Summarization/HumanInTheLoop 两个名字）；② 编译后是否存在任何官方动态改拓扑 API（当前文档与 reference 未见，按不存在对待）；③ `EphemeralValue` 等内部通道类型是否有用户级 StateGraph 声明语法（源码可见，文档无用户 API）；④ 1.2+ `DeltaChannel`（beta）对并发写语义的影响。

---

## 7. 结论：LangGraph 作为我们 DSL 底座的可行性判断

**总判定：可作执行内核（L3 层），不可作 DSL 本体（L0–L2 层）。G0 自研必要性判定：成立。**

**它给的（值得承接的执行语义）**：Pregel superstep 的事务性（整组更新要么全落要么全不落）、通道+reducer 的声明式归并、并发写冲突的运行时检测（`InvalidUpdateError`）、节点输入按 schema 的运行时过滤、子图边界隔离、`recursion_limit`/`RetryPolicy`/`error_handler`/`interrupt(response_schema)` 这套 1.2+ 容错全家桶——四层模型里 L2 拓扑的执行语义与 L3 的落点，LangGraph 已是当前开源里最完整的。12 格中唯一两格"完整表达"（D3×MetaGPT、D3×AFlow）证明其数据流内核是对的。

**根本性缺口（在 LangGraph 上叠加解决不了或解决得很拧巴的）**：
1. **G1 token/成本预算**——计费点必须进执行内核，包装器层面数不准；
2. **G2 图作为数据**——没有表示层，一切"配置即图/LLM 产图/静态校验图"都要自造 schema+翻译器，而这正是 DSL 本身；
3. **G4 写权限/单写者不变量**——LastValue 默认覆盖写的哲学与"角色所有权"模型对抗，叠加权限层是逆水行舟；
4. **G3/G7 校验与信封的缺位**——契约只在边界一处生效、agent 间通信无类型位，说明 LangGraph 的类型系统只覆盖图的进出口，不覆盖图的内政。

这四项恰好落在我们的 L0（不变量）与 L1（契约）——即任务书四层模型里 LangGraph 完全没有对应概念的两层。G0 判据（"现有 DSL 能完整表达三篇机制则自研复议"）不触发：12 格 0 个无条件完整，10 个需胶水，且最重的三处胶水（预算、图即数据、写权限）都是根本性而非勤奋可解。

**工程量缺口（若以 LangGraph 为内核，由我们的 DSL 在外层补齐即可）**：G5 失败 taxonomy（骨架已有）、G6 视图策略（键过滤已有，叠粒度即可）、G7 信封类型（Command 骨架已有）、G8 声明式依赖触发（条件边可退化为翻译目标）。这些适合作为"DSL 编译到 LangGraph"的翻译目标语义，而不是自研内核的理由。

**对底座路线的直接推论**：① 我们 DSL 的编译目标可以列 LangGraph 为 L4 逃逸层/L3 实现后端候选（其 superstep+通道语义成熟）；② 但 DSL 的 L0/L1（不变量：写权限、单写者、隔离；契约：预算、信封、节点间校验）必须自有表示，无法从 LangGraph 继承；③ G2 说明"图即数据"的表示层（供 AFlow 类搜索与配方分发）是 DSL 的第一交付物，LangGraph 只能当编译靶不能当源表示。

---

## 附：证据来源索引

- 图 API / 状态 / Send / Command / 校验限制：docs.langchain.com/oss/python/langgraph/graph-api.md、use-graph-api.md
- 运行时与通道类型（LastValue/Topic/BinaryOperatorAggregate/DeltaChannel）：…/langgraph/pregel.md
- RetryPolicy / TimeoutPolicy / error_handler / NodeError：…/langgraph/fault-tolerance.md（特性需 langgraph>=1.2）
- 子图隔离与私有历史：…/langgraph/use-subgraphs.md
- interrupt / response_schema / interrupt_before 降级：…/langgraph/interrupts.md
- 错误原文：…/langgraph/errors/INVALID_CONCURRENT_GRAPH_UPDATE、…/errors/GRAPH_RECURSION_LIMIT；reference.langchain.com/python/langchain-core/runnables/config/RunnableConfig/recursion_limit（默认 25）
- 源码：github.com/langchain-ai/langgraph libs/langgraph/langgraph/graph/state.py（attach_node 输入过滤、LastValue fallback）、channels/last_value.py（"Can receive only one value per step…"）
- v1.0 变更（create_react_agent 弃用→langchain.agents.create_agent）：docs.langchain.com/oss/python/releases/langgraph-v1、…/migrate/langgraph-v1
- middleware（SummarizationMiddleware/HumanInTheLoopMiddleware）：docs.langchain.com/oss/python/langchain/middleware/overview
