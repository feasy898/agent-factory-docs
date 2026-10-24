# DSL-G0 表达力评估 · AutoGen（0.4+ agentchat，Team JSON 序列化格式）

> 探针分支（对齐组）· 2026-10-24。目的：验证自研 Agent 定义 DSL 的必要性——若现有开源 DSL 能完整表达代表性论文机制，自研复议。
> 依据：AutoGen 官方 stable 文档 + `microsoft/autogen` main 分支源码（autogen-agentchat **0.7.5**，PyPI 2026-10 实查 latest=0.7.5）。所有字段名/API 名均逐条核对，未实测项标"待验证"。本探针未安装框架、未修改 af/ 目录。

---

## 0. 版本口径（先立靶）

| 事项 | 事实 |
|---|---|
| 0.2 | ConversableAgent/GroupChat，纯 Python 命令式构造，无组件级声明式序列化、无 save_state（官方 migration-guide 明确："v0.2 had no built-in way to save and load an agent's state"）。**按任务口径不计入表达力**。 |
| 0.4+ | 重写为 async 事件驱动 Core + AgentChat；官方 migration-guide 列为新能力："a generic component configuration system"、`save_state`/`load_state`。团队/代理的 Component 序列化在 0.4 后期小版本内落地（0.4.7 release note 见 CodeExecutor 序列化；agentchat 组件序列化确切引入小版本**待验证**，0.4.9.2 已有 `dump_component` 泄密修复记录）。 |
| stable=0.7.5 | 本文全部字段以 0.7.5 源码为准。Component JSON 是事实上的 Team 序列化格式（AutoGen Studio 同款）。 |

**Component JSON 骨架**（serialize-components.html，实测于源码 `ComponentBase`）：

```json
{
  "provider": "<类点的路径，如 autogen_agentchat.teams.RoundRobinGroupChat>",
  "component_type": "team | agent | model | termination | tool | memory | ...",
  "version": 1,
  "component_version": 1,
  "description": "...",
  "config": { ...各组件自有 schema... }
}
```

配套 API：`dump_component()` / `load_component()`（`Component[ConfigModel]` 泛型基类）；状态与配置分离——`save_state()`/`load_state()` 只保存消息线程与运行态（TeamState：agent_states、message_thread、current_turn、next_speaker_index，可 JSON 落盘），配置在构造期注入。官方警告：load 会执行代码，"ONLY LOAD COMPONENTS FROM TRUSTED SOURCES"。

---

## 1. 三篇 × 四维度判定矩阵

判定三档：**完整表达** / **胶水代码**（标注多少与多脏）/ **不可表达**。

| 维度 | ReAct（Yao 2022） | MetaGPT（Hong 2023） | AFlow（Zhang 2024） |
|---|---|---|---|
| **1 契约层**（I/O schema、预算、停止、失败重试） | **胶水代码**（少量，~30 行内） | **胶水代码**（重） | **不可表达**（外循环契约）+ 运行内契约胶水 |
| **2 不变量强制**（多写者禁令、生成/验证隔离、评估外置） | **胶水代码**（轻，多数不变量该论文用不到） | **胶水代码**（重） | **胶水代码**（重；变异循环不变量不可表达） |
| **3 上下文组装**（选择性携带、摘要、外置工件） | **完整表达**（该论文需求恰好落在默认行为+声明式截断内） | **胶水代码**（中） | **胶水代码**（中） |
| **4 拓扑与角色** | **完整表达**（单 agent + 工具，天然声明式） | **胶水代码**（流水线骨架完整可声明；typed 产物契约不可表达） | **胶水代码**（重；DAG 骨架可声明，typed 端口/集成聚合/测试回边一半在代码） |

总评：**12 格中 0 格"完整表达"覆盖论文核心机制**；ReAct 两格完整仅因其机制恰为 AutoGen 的默认形态（单 agent 工具循环 + 全历史上下文）；越靠论文的"定义性机制"（typed 契约、不变量、元循环），越塌陷到 Python 代码。

---

## 2. 逐格证据

### 2.1 ReAct

**D1 契约层 — 胶水代码（轻）**
声明式可得：停止条件全家桶（`conditions/_terminations.py` 逐字段核对）——`MaxMessageTerminationConfig(max_messages, include_agent_event)`、`TextMentionTerminationConfig(text)`（天然表达 "Finish when [Action] contains Finish"）、`TokenUsageTerminationConfig(max_total_token, max_prompt_token, max_completion_token)`、`TimeoutTerminationConfig(timeout_seconds)`、`FunctionCallTerminationConfig(function_name)`（按工具名停，等价于 ReAct 的 Finish 动作哨兵）、`StopMessageTerminationConfig()`，且支持 `|`/`&` 组合成 `OrTerminationCondition`/`AndTerminationCondition`（serialize-components.html 有 dump 实例，可嵌套序列化）。步数预算=团队级 `max_turns`（各 TeamConfig 均有）。
胶水部分：ReAct 的输入契约（任务串）与提示内 "Thought/Action/Observation" 格式只能写进 `system_message` 字符串；失败分类与重试不可声明（见 §3 缺口4）。无需写循环代码——`AssistantAgent` 的工具循环本身就是 ReAct 运行时。
反例（不可声明的部分）：

```python
# ReAct 的格式正确性校验（thought/action 交替、动作名合法性）无声明式挂点，
# 只能子类化 TerminationCondition（Python 代码，非数据）：
class MyFormatGuard(TerminationCondition): ...
```

**D2 不变量 — 胶水代码（轻）**。单 agent 场景无多写者问题；"行动只能经工具协议发生"由模型 function-calling 保证，是运行时行为而非 DSL 条款。`reflect_on_tool_use` + `max_tool_iterations`（AssistantAgentConfig 字段，0.7.5）提供一个固定的工具-反思循环开关，无变体空间。生成/验证隔离该论文不涉及。
**D3 上下文组装 — 完整表达**。ReAct 需要的 scratchpad=全历史，恰是 `AssistantAgent` 默认（`UnboundedChatCompletionContext`）；长观察截断可声明式替换 `model_context` 为 `TokenLimitedChatCompletionContext`（ComponentModel 字段，可 dump）；观察摘要可声明 `tool_call_summary_format`（默认 `"{result}"`，模板串）。
**D4 拓扑与角色 — 完整表达**。`AssistantAgentConfig` 全字段可序列化：`name, model_client, tools, workbench, handoffs, model_context, memory, description, system_message, model_client_stream, reflect_on_tool_use, tool_call_summary_format, max_tool_iterations, metadata, structured_message_factory`。注意 tools 自 v0.5.5 起不再直接序列化，折叠为 `StaticStreamWorkbench` 后经 `workbench` 序列化（源码注释原文："versionchanged:: v0.5.5 Now tools are not serialized, Cause they are part of the workbench"）——`FunctionToolConfig(source_code, global_imports, name, description, has_cancellation_support)` 以函数源码文本嵌入，load 时 `exec`（官方警告）。可声明，但**携带代码体**，见 §3 缺口8。

### 2.2 MetaGPT

**D1 契约层 — 胶水代码（重）**
SOP 中间产物（PRD/设计文档 JSON）本应是 typed 契约。AutoGen 的声明式结构化输出是 `structured_message_factory`（AssistantAgentConfig 字段，源自 `output_content_type`），但源码 docstring 原文（0.7.5，L133-135）：

> "Currently, setting `output_content_type` prevents the agent from being able to call `load_component` and `dum_component` methods for serializable configuration. This will be fixed soon in the future."

即：**结构化输出与序列化互斥是官方承认的现状**（`_to_config` 里却序列化了 `structured_message_factory`，与 docstring 矛盾——实际行为**待验证**）。且 schema 本体是 Python pydantic 类引用（`output_content_type: type[BaseModel]`），JSON 里至多存 format_string 与字段名推断（`_from_config` 重建 `ContentModel`），**类型保真度待验证**。
下游消费同样断链：PM 的 PRD JSON 到架构师处按"全线程文本"广播，无"取上一节点输出某字段绑定到我输入参数"的声明。预算/停止可声明（同 ReAct D1），但 MetaGPT 需要的"产物不合法则打回"分类重试无载体。
**D2 不变量 — 胶水代码（重）**。共享状态=广播消息线程，人人可追加（swarm.html："all agents share the same message context"；graph-flow.html："By default, all messages are sent to all agents in the graph"）——没有可声明"只有 PM 能写 PRD 段"的载体，因为根本没有 typed 共享状态存储。轮转制（RoundRobin 顺序）意外地近似了"单写者"纪律，但那是调度副作用，不是可声明不变量。生成/验证隔离可部分声明：`MessageFilterAgent`（可序列化，`component_provider_override = "autogen_agentchat.agents.MessageFilterAgent"`）包裹任意 agent，`MessageFilterConfig(per_source=[PerSourceFilter(source, position: "first"|"last"|None, count)])` 只做读侧按源包含式过滤，**无 exclude、无内容类型粒度、无字段粒度**。QA 想只看最终代码不看工程师自辩：若二者在同一条消息里，不可分。
**D3 上下文组装 — 胶水代码（中）**。可声明：每 agent 独立 `model_context`（`BufferedChatCompletionContext(buffer_size)` / `TokenLimitedChatCompletionContext(token_limit)`）、独立 `memory` 列表（ListMemory/ChromaDBVectorMemory/RedisMemory/Mem0Memory 均为 Component，官方给出 ChromaDB 的 JSON 实例，`update_context` 把检索结果注入为 SystemMessage）、`MessageFilterAgent` 按源过滤。不可声明：LLM 历史摘要压缩（无任何构造）、外置工件引用（消息内联全文，无 artifact 指针/pinning）、过滤规则的语义化描述（只有 first/last/count 三个旋钮）。
**D4 拓扑与角色 — 胶水代码（骨架完整/契约断裂）**。PM→架构师→工程师→QA 线性链声明式完整：`GraphFlow`（`GraphFlowConfig(name, description, participants, termination_condition, max_turns, graph: DiGraph)`，`component_provider_override = "autogen_agentchat.teams.GraphFlow"`）或 `RoundRobinGroupChat`（Config：`name, description, participants, termination_condition, max_turns, emit_team_events`）。角色=可序列化的 `name/description/system_message` 三元组。断裂处：MetaGPT 的发布-订阅环境（角色按消息类型订阅）、typed 产物契约、角色读写权限均无载体。Swarm 的 `Handoff(BaseModel): target/description/name/message`（name 默认 `transfer_to_<target>`）全部可序列化进 AssistantAgent config，但 handoff 是**模型自由决策**（tool-call 触发），不是 SOP 规定的确定性流转；0.7.5 的 Handoff **没有 condition 字段**（那是后继项目 Microsoft Agent Framework 的特性，勿混淆）。

### 2.3 AFlow

**D1 契约层 — 不可表达（外循环）+ 运行内胶水**。AFlow 的核心契约是**评估-变异循环**：工作流种群、验证集得分、变异算子（MCTS/EBFT 风格）、迭代预算。Team JSON 是单实例静态快照，全部 Config 模型中无任何搜索/变异/评分构造；搜索循环只能写成外部 harness 代码驱动 `load_component`（生成变体）→`run()`→打分的胶水管道，变体生成完全脱离声明域。运行内契约（单次工作流的步数/token 预算、字符串哨兵停止）可声明，同 §2.1。
**D2 不变量 — 胶水代码（重）**。"评估逻辑外置"：评估节点可声明为 `CodeExecutorAgent`+可序列化的 CodeExecutor（0.4.7 起执行器组件化），或外部裁判 agent；用 `ExternalTermination`（Config 为空壳，`set()` 由外部代码触发）可从外部停跑——但评估器的接入、得分回写、按分变异全是代码。**变异不变量**（"任何 agent 不得修改工作流图本身"）不可表达：AutoGen 里图与运行时彻底分离是架构事实，却没有可声明的条款；经验池/工作流记忆（AFlow 的 experience）无载体。
**D3 上下文组装 — 胶水代码（中）**。AFlow 每个算子需要"上游特定输出→本算子输入"的精准拼装。可用 `MessageFilterAgent(per_source=[...])` 声明"只看某源最近 N 条"，配合 `GraphFlow` 的 join 语义（边级 `activation_group`+`activation_condition: "all"|"any"`，节点级 `activation`）控制汇合时序。不可声明：字段级绑定、集成算子（ensemble）对 k 份采样的多数票聚合（聚合器要么是 Python callable 边条件、要么是提示词 hack 的 agent 节点）、把工具结果外置为工件再传引用。
**D4 拓扑与角色 — 胶水代码（重）**。能声明的部分相当多：`DiGraphConfig` 直嵌 `GraphFlowConfig.graph`，模型为 `DiGraph(nodes: Dict[str, DiGraphNode(name, edges, activation)], default_start_node)`，边 `DiGraphEdge(target, condition: str|Callable|None, activation_group, activation_condition)`；字符串 condition=子串匹配消息内容；fan-out/fan-in、含安全出口的环（`has_cycles_with_exit()` 校验，文档明示支持 "Loops with safe exit conditions"）均可声明。AFlow 的"代码→测试→(FAIL 回修 / PASS 下游)"回边可以这样声明：

```json
"graph": {
  "nodes": {
    "code_op":   {"name": "code_op", "edges": [{"target": "test_op", "condition": null, "activation_group": "", "activation_condition": "all"}], "activation": "all"},
    "test_op":   {"name": "test_op", "edges": [
        {"target": "fix_op",   "condition": "FAIL", "activation_group": "", "activation_condition": "all"},
        {"target": "ensemble", "condition": "PASS", "activation_group": "", "activation_condition": "all"}], "activation": "all"}
  },
  "default_start_node": "code_op"
}
```

（节点/边字段名逐字取自 `_digraph_group_chat.py`；`condition_function` callable 在 dump 时 `exclude=True`，docstring："they will not be serialized"。）
不能声明的部分恰是 AFlow 的定义性机制：算子=带 typed 输入/输出端口的 LLM 操作（AutoGen 节点=整个 agent，无端口概念）；ensemble 聚合语义；变异算子库与搜索策略（外循环，见 D1/D2）。此外 GraphFlow 官方标注 "experimental, API subject to change"。四类拓扑的分工：RoundRobin=固定 SOP；Selector=LLM 选角（`selector_prompt` 模板 `{roles}/{history}/{participants}` + `max_selector_attempts: 3` 可声明，但动态策略本体是 Python 且被丢弃，见缺口5）；Swarm=模型自由 handoff；GraphFlow=确定性 DAG。**角色读写权限在任何一类中都不可表达**。

代表性 JSON 片段（MetaGPT 流水线单角色，字段全部实测自源码；provider 路径按 `component_provider_override` 惯例，`model_context` 的 provider 串**待验证**）：

```json
{
  "provider": "autogen_agentchat.agents.MessageFilterAgent",
  "component_type": "agent",
  "version": 1, "component_version": 1,
  "config": {
    "name": "qa_filtered",
    "wrapped_agent": {
      "provider": "autogen_agentchat.agents.AssistantAgent",
      "component_type": "agent",
      "version": 1, "component_version": 1,
      "config": {
        "name": "qa",
        "description": "runs tests and reports",
        "system_message": "You are the QA engineer. Run the tests, report failures.",
        "model_client": {
          "provider": "autogen_ext.models.openai.OpenAIChatCompletionClient",
          "component_type": "model",
          "version": 1, "component_version": 1,
          "config": {"model": "gpt-4o", "max_retries": 2}
        },
        "model_context": {
          "provider": "autogen_agentchat.models.BufferedChatCompletionContext",
          "config": {"buffer_size": 10}
        },
        "reflect_on_tool_use": false,
        "tool_call_summary_format": "{result}",
        "max_tool_iterations": 1
      }
    },
    "filter": {"per_source": [
      {"source": "architect", "position": "last", "count": 1},
      {"source": "engineer",  "position": "last", "count": 1}
    ]}
  }
}
```

这份 JSON 能表达："QA 只带架构师与工程师各最近 1 条消息、窗口 10、模型重试 2 次"。它不能表达："QA 的输入=PRD 的 v2 字段 + 只读权限 + 产物 schema 校验失败自动打回"。

---

## 3. 缺口清单（按严重度降序，各带证据）

1. **元循环（评估-变异/搜索）无声明式载体**。全部 Team/Agent Config 为静态 pydantic 模型；唯一"动态"入口 selector_func/candidate_func/FunctionalTermination/callable 边条件在序列化时全部排除（证据见缺口5）。AFlow 类自进化机制只能写成外部 harness，声明域=0。这是与四层模型 L0（不变量）/元层最大的鸿沟。
2. **typed 契约断裂**：结构化输出与序列化互斥（`_assistant_agent.py` L133-135 原文，实际行为**待验证**）；GraphFlow 边无端口/字段绑定概念（默认全量广播消息，graph-flow.html 原文）；`Handoff.message` 为字符串模板（`base/_handoff.py`，无 schema 字段）。跨角色"产物 schema→下游输入"的 L1 契约在 JSON 里无处安放。
3. **共享状态读写权限不变量不可表达**：无 typed 共享状态存储，唯一共享物是广播消息线程；`MessageFilterAgent` 是读侧包含式过滤（`PerSourceFilter(source, position, count)` 三旋钮），无写侧 ACL、无字段粒度、无 exclude。多写者禁令只能靠调度顺序的副作用近似。
4. **失败分类与策略化重试不可声明**：模型客户端仅有传输层 `max_retries`（`OpenAIClientConfiguration`，转发 AsyncOpenAI）；`reflect_on_tool_use`/`max_tool_iterations` 是固定单一策略；无失败 taxonomy（schema 违例/工具报错/拒答）、无按类重试矩阵、无 fallback 模型链的声明式表达。
5. **所有"策略"扩展点是 Python callable 且序列化即丢失**（官方文档逐条承认）：`selector_func` "is not serializable and will be ignored during serialization and deserialization process"（serialize-components.html）；candidate_func 在 `SelectorGroupChatConfig` 中连字段都没有（源码中被注释掉的是 selector_func，candidate_func 从未出现于 `_to_config`）；`FunctionalTermination` **不是 Component**、无 Config 类（`_terminations.py`）；callable 图边 "will not be serialized"（GraphFlow docstring）；`tool_call_summary_formatter` "**not serializable** ... will be ignored when an agent is loaded from, or exported to, YAML/JSON configuration files"（`_assistant_agent.py` L158-160、L233）。官方解法是"implementing custom workflows and serialization logic"——即承认要自己写胶水。
6. **成本与细粒度资源预算缺失**：`TokenUsageTerminationConfig` 只有 token 三个字段；无 $ 成本预算、无按 agent 的调用次数预算（只有全局 `max_turns`/`max_messages`）、无"暂停-续跑预算"语义（`save_state` 可续，但预算重置语义未定义，**待验证**）。
7. **上下文工程停留在"窗口+过滤+检索"**：无 LLM 摘要压缩构造、`MessageFilterAgent` 无内容类型感知（无法只滤工具事件保文本）、无外置工件引用（消息全内联）。ReAct 之外的一切论文级上下文策略都要胶水。
8. **工具"可序列化"以携带代码体为代价**：`FunctionToolConfig.source_code` 嵌入函数源码，`_from_config` 直接 `exec`（官方安全警告）；意味着声明式 JSON 实际上是代码搬运载体，违背"配置=数据"的理想形态；第三方工具必须实现 Component 协议（v0.5.5 起非 workbench 工具直接不序列化）。

---

## 4. 结论：AutoGen 作为 DSL 底座的可行性判断

**判定：不适合作为自研 DSL 的声明式底座；其 Component JSON 是"拓扑快照的序列化格式"，不是"agent 定义 DSL"。**

- **表达力上限**：12 格 0 个"完整表达"覆盖论文核心机制。它声明式覆盖的是四层模型里的 **L2 拓扑**（GraphFlow 的 DAG+条件边+join 语义是开源方案里最完整的片段）和 **L3 实现绑定**（provider 机制指到任意 Python 类），而 **L1 契约**残缺（typed 输出与序列化互斥、无跨角色绑定、无失败重试策略）、**L0 不变量**完全缺位（无读写权限、无隔离条款、无元循环载体）。恰好印证四层切分：AutoGen 只有 L2/L3 有骨架，L0/L1 需要的正是它没有的东西。
- **根因**：Component 序列化的设计目标是"保存/搬运一个 Python 对象图"（AutoGen Studio 的存取），不是"定义可验证的协作契约"。所有判断逻辑被设计为留在 Python 侧（callable），于是序列化格式天然只是静态骨架——这不是实现欠账，是架构取向。
- **可用遗产**：若 G0 后仍要对齐生态，值得抄三样——① `provider`+`config`+`component_type` 的组件指认与版本字段；② 终止条件的可组合（`|`/`&`）+可序列化设计（每个条件一个 Config pydantic）；③ GraphFlow 的 `DiGraphEdge(condition, activation_group, activation_condition)` 图模型与 `MessageFilterAgent` 的读侧视图过滤思路（需升级为带写权限/字段粒度的形态）。
- **与自研的关系**：三篇论文中 ReAct（AutoGen 默认形态）之外，MetaGPT 的 SOP 契约与 AFlow 的元循环正是我们要在 L0/L1/元层自研的差异化能力，且现有方案即便加上胶水也无法"声明式+可校验"地承载——**自研必要性成立，G0 复议不需要**。

### 待验证清单（后续探针可实测）
1. `output_content_type` 在 0.7.5 实际 dump/load 是否失败（docstring 与 `_to_config` 矛盾）。
2. `StructuredMessageFactory` 从 format_string 重建 ContentModel 的类型保真度。
3. `OrTerminationCondition` dump 出的 config 内嵌套键名（文档示例未给全）。
4. agentchat 组件序列化的确切引入小版本（0.4.2–0.4.7 之间）。
5. `save_state` 跨 `load_state` 的预算终止条件重置语义。
6. `model_context`/`memory` 的 provider 字符串标准写法（`autogen_agentchat.models.BufferedChatCompletionContext` 按惯例推断）。

### 证据源清单
- 文档：`microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/` 下 `serialize-components.html`、`tutorial/termination.html`、`tutorial/teams.html`、`tutorial/state.html`、`selector-group-chat.html`、`swarm.html`、`graph-flow.html`、`memory.html`、`migration-guide.html`
- 源码（main=0.7.5）：`autogen_agentchat/agents/_assistant_agent.py`、`agents/_message_filter_agent.py`、`base/_handoff.py`、`conditions/_terminations.py`、`teams/_group_chat/{_round_robin_group_chat,_selector_group_chat,_swarm_group_chat}.py`、`teams/_group_chat/_graph/{_digraph_group_chat,_graph_builder}.py`、`autogen-ext/models/openai/_openai_client.py`、`autogen-core/tools/_function_tool.py`
- 版本：PyPI `autogen-agentchat` latest=0.7.5（2026-10 实查）；GitHub releases 0.4.7/0.4.9.x notes
