# DSL-G0 表达力评估：CrewAI YAML 配置（agents.yaml / tasks.yaml / crew 配置）

> 评估者：DSL-Compiler 对齐代理（探针分支）｜日期：2026-10-24
> 方法：未安装框架，全部依据官方文档 docs.crewai.com（检索时文档版本线 **v1.15.30**，2026-10 快照）。
> 每个字段名均出自官方文档页面；文档无示例支撑的推断一律标 **[待验证]**。
> 评估对象是 CrewAI 的**声明式配置面**：classic 项目的 `config/agents.yaml` + `config/tasks.yaml`（`crewai create crew --classic`，官方明确"仍支持、未废弃"），以及新版 JSON-first 格式 `crew.jsonc` + `agents/*.jsonc`（两者声明力基本同构，字段口径一致；下文以 YAML 为主书写，JSONC 差异单独注明）。

---

## 0. 配置面速览（哪些东西能进 YAML，哪些不能）

**能进配置文件（官方文档明确列出）**：

- Agent 级（`docs.crewai.com/en/concepts/agents`）：`role`、`goal`、`backstory`、`llm`、`tools`（按名引用）、`function_calling_llm`、`max_iter`（默认 20）、`max_rpm`、`max_execution_time`（秒）、`verbose`、`allow_delegation`（默认 false）、`step_callback`、`cache`、`system_template`/`prompt_template`/`response_template`、`max_retry_limit`（默认 2）、`respect_context_window`（默认 true）、`multimodal`、`inject_date`/`date_format`、`reasoning`（默认 false）、`max_reasoning_attempts`、`embedder`、`knowledge_sources`、`use_system_prompt`、`memory`。文档口径："agent 配置条目支持任意 public Agent 字段"。
- Task 级（`docs.crewai.com/en/concepts/tasks`）：`description`（必填）、`expected_output`（必填，str）、`name`、`agent`、`tools`、`context`（List[Task 名]）、`async_execution`（默认 false）、`human_input`、`markdown`、`output_file`、`create_directory`、`output_json`、`output_pydantic`、`callback`、`guardrail`（Callable **或字符串**，字符串自动包装成 `LLMGuardrail`）、`guardrails`（列表，优先于 `guardrail`）、`guardrail_max_retries`（默认 3）。`max_retries` 已弃用，改用 `guardrail_max_retries`。JSONC 条目另列 `input_files`、`response_model`、`converter_cls`、`"type": "ConditionalTask"` + `condition`（后四项文档只有字段名、无配置示例，**[待验证]** 具体写法）。
- Crew 级（`docs.crewai.com/en/concepts/crews`）：`agents`、`tasks`、`process`（`sequential` | `hierarchical`，枚举仅此两值）、`manager_llm`（hierarchical 必需）、`manager_agent`、`memory`、`cache`、`max_rpm`、`planning`、`planning_llm`、`embedder`、`output_log_file`、`knowledge_sources`、`checkpoint`、`security_config` 等。JSONC 示例中实际出现的 crew 级配置字段：`name`、`agents`、`tasks`、`process`、`verbose`、`memory`、`inputs`。`planning`/`planning_llm` 文档仅见 Python 构造参数，无配置文件示例 **[待验证]**。

**进不了配置文件（必须 Python）**：

- **Flows 整个编排层**：`@start`/`@listen`/`@router`/`or_`/`and_`/`@persist`/`@human_feedback` 全部是 Python 装饰器。官方 Flows 页明确：flow 的编排逻辑本身永远是代码，配置文件只覆盖 flow 内嵌 crew 的 agents/tasks。
- `ConditionalTask` 的 `condition`：必须是一个接收 `TaskOutput` 返回 bool 的 Python 可调用（`docs.crewai.com/v1.15.30/en/learn/conditional-tasks`），文档无任何声明式条件语法。
- Pydantic schema 类本体：`output_pydantic`/`output_json` 的类型是 `Optional[Type[BaseModel]]`，配置文件里如何引用类无官方示例 **[待验证]**（工具尚有 `"SerperDevTool"` 按名与 `{"python": "module.attribute"}` 两种字符串引用机制，schema 是否同机制文档未写）。
- Memory 的存储配置：`Memory(llm=..., storage="lancedb", ...)` 全是构造参数；配置文件中除 crew 级 `memory: true` 布尔与 `embedder` dict 外无 memory 语法。
- 各种回调（`step_callback`/`task_callback`/`callback`/`before_kickoff_callbacks`）与自定义 evaluator 函数。

---

## 1. 三篇 × 四维度矩阵

判定三档：**完整表达** / **需胶水代码**（注明多少与多脏） / **不可表达**。

| 论文 \ 维度 | 1. 契约层（schema/预算/停止/失败重试） | 2. 不变量强制（写冲突/隔离/评估外置） | 3. 上下文组装策略 | 4. 拓扑与角色 |
|---|---|---|---|---|
| **ReAct**（思想-行动-观察循环） | **需胶水代码（少量）**：步数/时间/RPM 预算可声明（`max_iter`/`max_execution_time`/`max_rpm`）；但 expected_output 无 schema 强制，失败分类无字段 | **不可表达**（声明式）：预算型不变量由 harness 原生强制，但评估逻辑外部化只有 LLM 字符串 guardrail，无外部校验器声明 | **需胶水代码（中量）**：`respect_context_window` 只有自动截断；观察注入由 harness 内建；`knowledge_sources` 可声明 RAG 注入 | **完整表达**：单体迭代循环是 harness 原生；`reasoning`/`max_reasoning_attempts`/提示三模板可声明 ReAct 式行为 |
| **MetaGPT**（SOP 多角色流水线+结构化产物） | **需胶水代码（中量）**：结构化中间产物需每阶段一个 Pydantic 类（配置文件无 schema 写法示例 [待验证]）；expected_output 纯自然语言 | **不可表达**：顺序流程默认把上一任务输出链入下一任务且无关闭字段（无法做验证者隔离）；多写者冲突无任何字段；评估外置仅 LLM 字符串 | **需胶水代码（大量）**：`context` 只做"整输出拉取"；无摘要、无选择性携带、无字段级绑定 | **完整表达（静态 DAG 部分）**：sequential + `context` 边 + 任务级 `tools` 覆盖 ≈ SOP 流水线静态结构；**QA→工程返工反馈环不可表达** |
| **AFlow**（工作流自动搜索：算子图+评估-变异环） | **不可表达**：搜索循环的终止条件、总体 token 预算（文档仅有事后 `usage_metrics`）、变异算子均无声明处 | **不可表达**：外部评估器（判分脚本/指标）必须写成 Python 函数塞进 guardrail；评估-变异环的全部不变量无从声明 | **不可表达**：AFlow 的变量级类型化数据流绑定，CrewAI 只有整输出 `context`，无对应概念 | **不可表达**（YAML 面）：Process 枚举仅 sequential/hierarchical；条件分支 condition 需 Python；循环边/反馈环/搜索元环全部无原语。注：**固定后的执行图**可用 Python Flows（`@router`/`or_`）表达，但仍不含搜索循环 |

---

## 2. 每格证据

### 2.1 ReAct（Yao et al. 2022）

**[1 契约层｜需胶水代码（少量）]**

可声明部分——agents.yaml（字段全部出自官方 agents/tasks 页）：

```yaml
# config/agents.yaml
react_solver:
  role: "推理执行器"
  goal: "通过多步工具调用与观察迭代回答问题"
  backstory: "谨慎、逐步推理"
  llm: "openai/gpt-4o"
  reasoning: true                  # 显式推理步（官方字段，默认 false）
  max_reasoning_attempts: 3        # 推理尝试上限（默认无限制）
  max_iter: 15                     # 迭代上限（默认 20）——ReAct 步数预算
  max_execution_time: 600          # 秒
  max_rpm: 10
  respect_context_window: true
  allow_delegation: false
  tools: [TavilySearchTool]
```

```yaml
# config/tasks.yaml
solve:
  description: "回答问题并给出每步依据"
  expected_output: "一个明确的最终答案及步骤列表"   # 纯自然语言，无 schema 强制
  agent: react_solver
  guardrail: "输出必须包含'最终答案：'字样与数值结论，否则不合格"  # 字符串→LLMGuardrail
  guardrail_max_retries: 3
```

缺口证据：
- `expected_output` 官方定义就是自然语言字符串（"guides the LLM; it does not enforce a schema"），schema 强制要靠 `output_pydantic`/`output_json`，而二者类型是 `Type[BaseModel]`——类本体必须写在 Python 里，配置文件无引用语法示例 **[待验证]**。
- 失败分类：只有 `max_retry_limit`（agent 级，默认 2，不分类）与 `guardrail_max_retries`（默认 3，仅 guardrail 失败）。没有"哪些错误类重试/哪些直接终止/哪些升级"的声明字段。
- 停止条件：`max_iter`/`max_execution_time`/最终答案之外，无自定义停止谓词的声明语法。
- 无 per-task/per-run token 预算字段；token 用量只有事后 `usage_metrics`。

补齐胶水量：一个 Pydantic 输出类 + （若需要非 LLM 校验）一个 guardrail 函数。脏度低——因为这些胶水是 CrewAI 官方支持的扩展点，不是 hack。

**[2 不变量强制｜不可表达（声明式）]**

- ReAct 本身的不变量主要是"循环在预算内终止"，这由 harness 原生强制（`max_iter` 等），DSL 不必重复声明——这是 CrewAI 表达力得分的地方。
- 但"评估逻辑外部化"不可声明：`guardrail` 只收两种形态——Python 函数 `Callable -> (bool, Any)`，或字符串（由 agent 的 LLM 自己判）。没有"引用外部脚本/HTTP 端点/测试套件"作为校验器的字段。要接外部判分器必须写 Python 函数包一层。

**[3 上下文组装策略｜需胶水代码（中量）]**

- 观察注入与累积由 harness 内建，配置面只有总开关 `respect_context_window`（超窗时自动截断/摘要，官方描述"context window respect"）。没有"对观察做摘要/只保留最近 k 步/丢弃工具原始输出"的声明式策略。
- `knowledge_sources`（agent 级/crew 级）可声明 RAG 注入，这是配置面唯一可声明的上下文来源控制。
- 更精细的控制要走 `system_template`/`prompt_template`/`response_template` 三个模板字段（可声明，但内容是自由文本提示工程，不是上下文策略）。

**[4 拓扑与角色｜完整表达]**

- 单体 ReAct 循环是 CrewAI 的执行内核（LLM 迭代决定工具调用直到最终答案），配置面暴露了循环的全部关键参数：`max_iter`、`reasoning`、`max_reasoning_attempts`、`max_rpm`、`max_execution_time`。
- 角色定义（`role`/`goal`/`backstory`）+ 提示三模板（`system_template`/`prompt_template`/`response_template`）可以声明出显式 "Thought/Action/Observation" 文本协议（若要复刻论文原协议而非 CrewAI 默认的函数调用循环）。
- 角色读写权限：不可声明（无 artifact 级权限字段；只有工具粒度——`tools` 按名列表，间接限定能做什么）。此项在 ReAct 单体场景权重低。

### 2.2 MetaGPT（Hong et al. 2023）

**[1 契约层｜需胶水代码（中量）]**

流水线骨架（字段全部为官方字段）：

```yaml
# config/tasks.yaml
write_prd:                       # PM
  description: "基于需求 {req} 撰写 PRD"
  expected_output: "含功能列表、用户故事与优先级的 PRD 文档"
  agent: pm
  output_file: artifacts/prd.md  # 外置产物到文件（官方字段）
system_design:                   # 架构师
  description: "基于 PRD 产出系统设计与接口定义"
  expected_output: "含模块划分与接口签名的技术方案"
  agent: architect
  context: [write_prd]           # 声明读取上游产物
write_code:                      # 工程师
  description: "依据 PRD 与设计实现代码"
  expected_output: "可运行的代码文件"
  agent: engineer
  context: [write_prd, system_design]
qa_review:                       # QA
  description: "对照 PRD 审查代码"
  expected_output: "问题清单与修改建议"
  agent: qa
  context: [system_design, write_code]
```

- 角色扮演（PM/架构师/工程师/QA 的 SOP 人设）用 `role`/`goal`/`backstory` 表达得很好——这是 CrewAI 的甜点区。
- 结构化中间产物（MetaGPT 的 PRD/Design 等是强 schema 类）：需要每阶段一个 Pydantic 类挂 `output_pydantic`。类本体在 Python；YAML/JSONC 中如何引用无官方示例 **[待验证]**。JSONC 支持字段清单里有 `response_model`/`converter_cls` 字样但零示例 **[待验证]**。
- 预算/重试同 2.1 的缺口（`max_retry_limit` 不分类）。

补齐胶水量：4 个 Pydantic 类 + crew.py 里把类挂到各 task；脏度中——是官方路径，但每个契约都要出配置文件进代码，声明面裂成两半。

**[2 不变量强制｜不可表达]**

- **验证者隔离不可表达**：官方 Tasks 页明确顺序流程"output of one task serving as context for the next"是默认行为，文档没有任何字段能关闭"上一任务输出自动进入下一任务"。MetaGPT 式"QA 只看设计稿与代码、不看工程师内心独白"或"工程师不带 QA 结论重写"这类隔离，在配置面无法声明。
- **多写者冲突**：无任何字段声明"哪个 agent/task 拥有哪个 artifact 的写权"。`output_file` 可以让多个 task 指向同一路径，框架不报错也不去重（无冲突检测字段）。
- **评估逻辑外部化**：同 2.1，只有 LLM 字符串 guardrail 或 Python 函数。

**[3 上下文组装策略｜需胶水代码（大量）]**

- `context: [task_a, task_b]` 的语义是"把这几个任务的**完整输出**注入本任务"。没有：字段级绑定（只带 PRD 的功能列表）、选择性携带、摘要压缩、外置工件引用（下游拿到的是上游全文拷贝，不是可寻址的 artifact 引用——尽管 `output_file` 把产物落了盘）。
- Crew 级 `memory: true` 开统一记忆（检索式注入），但它是不受任务声明控制的黑盒，不是显式组装策略。
- `respect_context_window` 只是超窗自动截断开关。
- 要做 MetaGPT 式"订阅特定消息类型"必须靠 Python（自定义 task `callback` 里改写 context，或干脆改用 Flows 手工传参）。

**[4 拓扑与角色｜完整表达（静态 DAG 部分）；返工环不可表达]**

- SOP 流水线的静态部分基本完整：sequential 顺序执行 + `context` 声明非相邻依赖边（官方支持跨任务拉取）+ `async_execution: true` 做有限并行（下游用 context 引用异步任务时会等待）+ 条件跳过（JSONC 的 `"type": "ConditionalTask"`，但 `condition` 必须 Python 函数——条件分支本体仍不可声明）。
- 层级委派：`process: hierarchical` + `manager_llm`/`manager_agent` 提供"经理动态分派+验收"，可作为 SOP 的动态执行变体；但这是运行时自由委派，不是声明的拓扑。
- **缺口（硬伤）**：QA 发现问题→打回工程师重做的**反馈环**不可表达。官方明确 `context` 前向引用被拒绝（JSONC 中"forward references are rejected"），Process 枚举无环原语。QA 任务只能是终点，返工循环必须出配置面（Flows Python 或外层代码重启 crew）。
- 角色读写权限：不可声明（同 2.1）。

### 2.3 AFlow（Zhang et al. 2024）

**[1 契约层｜不可表达]**

AFlow 的对象是"工作流的搜索过程"：初始算子图 + MCTS 变异 + 每轮用外部指标评估 + 预算内终止。对照配置面：

- 节点=LLM 算子（Ensemble/Test/Format 等）：能映射成 task，但 AFlow 节点带**变量级输入签名**（引用上游特定输出变量），`context` 只有整输出，签名无处声明。
- 搜索循环的终止条件（代数/收敛/预算）：无任何字段。Crew 的执行是一次性的（`kickoff` 一次跑完任务列表），没有"迭代整个图"的概念。
- 总体 token/费用预算：无字段（`usage_metrics` 是事后读数；`max_rpm`/`max_iter` 是调用节流不是预算封顶）。

反例（想写而写不出的伪配置——CrewAI 无对应语法）：

```yaml
# 不存在的语法，仅示意 AFlow 需要什么
workflow_search:
  strategy: mcts                    # CrewAI 无此概念
  budget: { total_tokens: 2000000 } # 无此字段
  operators: [ensemble, test]       # 无节点算子抽象
  evaluator: "custom:eval_metric"   # guardrail 无"引用外部可调用配置"语法
  until: { max_iterations: 30 }     # 无搜索级终止声明
```

**[2 不变量强制｜不可表达]**

- AFlow 的核心不变量是"候选工作流必须经外部评估器（如代码执行+测试用例）打分后才可进入种群"。CrewAI 配置面能做的最接近的事是字符串 guardrail——那是让执行 agent 的 LLM 自评，恰恰是 AFlow 明确要**避免**的（评估必须独立于生成）。
- 外部评估器只能写成 Python 函数塞进 `guardrail`/`callback`；判分脚本、沙箱执行、指标聚合全部出配置面。
- 生成者/评估者隔离、多写者冲突：同 2.2，零字段。

**[3 上下文组装策略｜不可表达]**

- AFlow 图的边是**带变量的数据流**（`test` 节点消费 `ensemble` 的候选列表变量 + 问题的输入变量）。CrewAI 的 `context` 语义是"把上游任务的整个 TaskOutput 文本注入提示"，没有变量、没有类型、没有部分携带。
- `inputs: {topic: ...}` 模板插值（`{topic}` 占位符）是唯一可声明的变量机制，但它是 kickoff 级常量注入，不是任务间数据流绑定。

**[4 拓扑与角色｜不可表达（YAML 面）]**

- 官方 Processes 页："restricting process values to the defined types (`sequential`, `hierarchical`)"——枚举封死，无自定义 process，无图 DSL。
- 条件分支：`ConditionalTask` 的 `condition` 是 Python 可调用（判定输入是**上一任务**的 TaskOutput）——连分支谓词都不能声明，且只能看上一任务，不能看任意上游。
- 循环/反馈边：无原语（同 2.2 缺口）。
- 并行：`async_execution: true` 可做有限扇出，但扇出后汇合仍靠 context 拉取，无 join 语义声明。
- 缓解事实（记入结论）：**搜索收敛后的那张固定执行图**，用 CrewAI Flows（Python：`@start`/`@listen`/`@router`/`or_`/`and_`）是可表达的，含分支与事件循环；但 Flows 无 YAML，且搜索循环本身（生成-评估-变异新图）在任何 CrewAI 原语之外，需要完全外层的胶水程序。

---

## 3. 缺口清单（按严重度排序）

1. **[致命] 契约层无 schema 强制的声明式表达**。`expected_output` 是自然语言提示（官方原文确认无 schema 强制），真正的 schema 载体 `output_pydantic`/`output_json` 需要 Python 类，配置文件引用语法无官方示例 [待验证]。后果：L1 契约在声明面不可校验，机器可读的输入输出契约整体缺位——这正是我们 L1 层的主菜。
2. **[致命] 拓扑无循环、无反馈边**。`context` 前向引用被拒绝（官方 JSONC 行为），Process 枚举仅两值，条件分支谓词必须 Python。MetaGPT 的 QA 返工环、AFlow 的评估-反馈环均不可表达。反馈环是多 agent 系统的一等公民，缺它 L2 层不及格。
3. **[致命] 不变量层整体缺位**。多写者冲突（无字段）、生成者/验证者上下文隔离（顺序流程默认链入上一任务输出且无关闭开关，官方文档无 opt-out 字段）、评估逻辑外部化（guardrail 只收 Python 函数或 LLM 字符串，无外部校验器引用语法）三项全空。L0 不变量在 CrewAI 里要么由 harness 私有决定（顺序链入），要么不存在。
4. **[严重] 上下文组装只有"整输出拉取"一种原语**。`context` = 上游 TaskOutput 全文注入；无摘要、无选择性携带、无字段级绑定、无外置工件寻址（`output_file` 落盘后下游仍拿全文拷贝）。AFlow 的类型化数据流完全无法落点。`respect_context_window` 的自动截断是黑盒行为不是策略声明。
5. **[严重] 失败分类与重试策略单一**。只有 `max_retry_limit`（agent 级，默认 2，全错误一视同仁）与 `guardrail_max_retries`（默认 3，仅 guardrail 失败）。无错误分类学、无按类重试/升级/熔断的声明。
6. **[中] 预算粒度粗且无总量封顶**。`max_iter`/`max_execution_time`/`max_rpm` 覆盖了次数/时间/速率，但无 token/费用预算字段，用量只有事后 `usage_metrics`。搜索类系统（AFlow）必需的"总预算内探索"无从约束。
7. **[中] 角色读写权限不可声明**。唯一的权限旋钮是 `allow_delegation`（委派开关）与工具列表（agent 级 `tools`、任务级 `tools` 覆盖）——工具粒度只能间接近似"写权限"，无 artifact 级声明。
8. **[中] 声明面双轨且关键写法未定型**。classic YAML 与 JSONC 并存（官方称 YAML 未废弃），但 guardrail/schema/ConditionalTask 在配置文件中的写法零示例；`planning`/`planning_llm`/`memory` 细配置只见 Python。作为底座有字段漂移与文档空洞双重风险。

---

## 4. 结论：CrewAI 作为自研 DSL 底座的可行性判断

**结论：不可作为底座，G0 自研必要性就 CrewAI 一项而言成立；但 CrewAI 应保留为自研 DSL 的候选编译目标（L3 后端）而非表达力基准。**

- **它真正能完整表达的**只有两块：单体 ReAct 式循环的参数面（harness 原生循环 + 可声明的预算/推理字段），以及静态顺序流水线的角色分工与显式依赖边（MetaGPT 的静态骨架）。这两块恰好是"多 agent 框架的公共下限"，自研 DSL 大概率也会覆盖，不构成采用理由。
- **四层对照**：L0（不变量）= 零字段；L1（契约）= 自然语言期望 + Python 侧 schema，声明面断裂；L2（拓扑）= 仅 DAG 子集（顺序+条件跳过+有限异步并行），无环、无数据流类型；L3（实现）= 最强的一层（这正是它作为执行框架的本职）；L4（逃逸）= 齐全且诚实（回调、自定义函数、Flows 全代码层）。作为"编译目标"它是合格的（声明翻译成它的 agents/tasks/crew 字段即可跑）；作为"底座"（我们的 DSL 语义寄生在它的抽象上）则会被它的 L0/L1/L2 空缺反向锁死。
- **一个明确的反向信号**：CrewAI 自己的演进方向印证了配置面的天花板——一旦要表达图与状态（Flows），官方也放弃了声明式，回退到 Python 装饰器。声明式配置在它内部被定位为"简单场景的脚手架"，不是核心语义载体。我们要做的任务中立 DSL（含不变量与契约为一等公民）与它的定位正交。
- **待验证清单**（若后续进入落地对接需实测）：① `output_pydantic`/`output_json`/`guardrail` 在 YAML/JSONC 中的实际引用语法与是否真能按字符串解析；② JSONC 的 `input_files`/`response_model`/`converter_cls` 语义；③ 顺序流程相邻输出链入是否存在未记载的关闭开关；④ `planning`/`planning_llm` 能否进配置文件。

## 参考页面（官方文档，2026-10-24 检索，文档版本线 v1.15.30）

- https://docs.crewai.com/en/concepts/agents （Agent 字段表、配置条目"支持任意 public Agent 字段"）
- https://docs.crewai.com/en/concepts/tasks （Task 字段表、guardrail 字符串→LLMGuardrail、guardrail_max_retries=3、context 语义与前向引用拒绝、expected_output 无 schema、JSONC 支持 "type": "ConditionalTask"）
- https://docs.crewai.com/en/concepts/crews （Crew 字段表、classic --classic 项目布局）
- https://docs.crewai.com/en/concepts/processes （Process 枚举仅 sequential/hierarchical、manager 委派语义）
- https://docs.crewai.com/v1.15.30/en/learn/hierarchical-process.md （manager_llm/manager_agent、任务动态分配）
- https://docs.crewai.com/v1.15.30/en/learn/conditional-tasks.md （condition 必须 Python 可调用、无声明式语法）
- https://docs.crewai.com/v1.15.30/en/guides/crews/first-crew.md （crew.jsonc + agents/*.jsonc 完整示例、工具按名/custom: 引用、YAML classic 未废弃）
- https://docs.crewai.com/en/concepts/flows （Flows 装饰器全 Python、无 YAML、flow 内嵌 crew）
- https://docs.crewai.com/v1.15.30/en/concepts/memory.md （统一 Memory 构造参数、配置文件无 memory 语法）
- https://docs.crewai.com/v1.15.30/en/concepts/planning.md （planning/planning_llm 仅 Python 示例）
