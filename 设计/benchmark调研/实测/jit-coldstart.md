# JIT 冷启动组件可克隆性实测：GEPA 与 Agent Workflow Memory (AWM)

- 实测日期：2026-10-19
- 实测机：本机 Linux（Debian，Python 3.14.4），外网走代理 `socks5h://100.64.0.3:1080`，pip 走清华镜像
- 克隆位置：`~/bench-study/gepa`、`~/bench-study/agent-workflow-memory`
- 结论先行：**GEPA 可直接作为工厂 JIT 编译器的优化内核**（零硬依赖、单文件接入点、原生"只出配方提案"）；**AWM 不宜作依赖引入**（非包、绑定 Mind2Web/WebArena schema），但其"归纳 prompt + 在线循环"模式值得抄。

---

## 1. 克隆与体量

### GEPA（gepa-ai/gepa）
| 项 | 值 |
|---|---|
| commit | `f1cfdee2856e9dc4b5b4dc5cc2e391d0aa20d819`（2026-10-12，main HEAD，与 GitHub API 核对一致）|
| License | MIT（`LICENSE`："Copyright © 2025 Lakshya A Agrawal"）|
| 体量 | depth-1 克隆 73MB（含 .git 27MB），工作树 46MB，608 个受控文件 |
| 热度 | 7058 stars（API 实测）|
| PyPI | `gepa==0.1.4`，wheel 仅 **290KB**；清华镜像可拉，秒级 |
| 依赖 | **pyproject `dependencies = []`（零硬依赖）**；extras `[full]` 才要 litellm<1.92、tqdm、cloudpickle、datasets、mlflow、wandb、pandas、pyarrow、pydantic、tiktoken；`Requires-Python >=3.10,<3.15` |
| 代码量 | wheel 内 91 个 .py，**23,729 行** |

证据摘录（pyproject.toml）：
```toml
[project]
name="gepa"
version="0.1.4"
description = "A framework for optimizing textual system components (AI prompts, code snippets, etc.) using LLM-based reflection and Pareto-efficient evolutionary search."
dependencies = []
```

### AWM（zorazrw/agent-workflow-memory）
| 项 | 值 |
|---|---|
| commit | `8c0ff8cd11d648c8fceb99e4e42f37e3b75381b1`（2025-12-22 "fix typo in readme"）|
| License | Apache-2.0 |
| 体量 | 55 个受控文件，11MB；Python 代码约 **4,428 行** |
| PyPI | **无包**（清华镜像 404），只能源码 vendored |
| 依赖 | mind2web 子目录：tqdm/numpy/openai/backoff==2.2.1/tiktoken/lxml==4.9.3/matplotlib（7 个）；webarena 子目录：browsergym-core/experiments、openai>=1.35.4,<1.36、langchain 0.2 系、tiktoken、huggingface_hub 等（约 14 个，版本钉死较紧）。注意 `lxml==4.9.3` 在 Python 3.14 下大概率装不上 |

安装实测：`pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple gepa` 在 venv 中秒装成功（系统 Python 是 PEP 668 管控，需 venv）。代理下 git clone 很慢（约 37KB/s），gepa 仓库因文档图片达 ~120MB，git 协议耗时约 15 分钟；AWM 11MB 约 4 分钟。

---

## 2. GEPA 实质解读（读 wheel 内源码 = GitHub HEAD 同版本 0.1.4）

### 2.1 输入接口到底是什么

GEPA 的顶层入口 `gepa.optimize`（`gepa/api.py:46`）：

```python
def optimize(
    seed_candidate: dict[str, str],                                   # 配方：{组件名: 文本}
    trainset: list[DataInst] | DataLoader[DataId, DataInst],          # 优化集
    valset: list[DataInst] | DataLoader[DataId, DataInst] | None,     # 评估集（可选）
    adapter: GEPAAdapter[DataInst, Trajectory, RolloutOutput] | None = None,
    task_lm: str | ChatCompletionCallable | None = None,              # 执行侧模型（可传 callable）
    reflection_lm: LanguageModel | str | None = None,                 # 反思侧模型（可传 callable）
    candidate_selection_strategy = "pareto",   # pareto / current_best / epsilon_greedy / top_k_pareto
    frontier_type: FrontierType = "instance",  # instance / objective / hybrid / cartesian
    module_selector = "round_robin",           # 每轮选哪些组件改
    max_metric_calls: int | None = None,       # 预算按"评估次数"计
    acceptance_criterion = "strict_improvement",
    ...
) -> GEPAResult
```

关键认知：**GEPA 不规定 trajectory 的数据结构**。`Trajectory = TypeVar("Trajectory")` 是用户自定义类型，引擎对其完全不解释（`core/adapter.py:117`：*"trajectories: opaque to GEPA (the engine never inspects them)"*）。轨迹只在两个用户实现的函数之间流转：

```python
class GEPAAdapter(Protocol[DataInst, Trajectory, RolloutOutput]):
    def evaluate(self, batch: list[DataInst], candidate: dict[str, str],
                 capture_traces: bool = False) -> EvaluationBatch[Trajectory, RolloutOutput]: ...
    def make_reflective_dataset(self, candidate, eval_batch, components_to_update
                 ) -> Mapping[str, Sequence[Mapping[str, Any]]]: ...
    propose_new_texts: ProposalFn | None = None   # 可选：自定义提案逻辑
```

- `EvaluationBatch`（`core/adapter.py:16`）四字段：`outputs`（不解释）、`scores: list[float]`（**minibatch 用 sum 比大小，全 valset 用 mean 进前沿**）、`trajectories`（给 make_reflective_dataset 用）、`objective_scores: list[dict[str,float]]`（多目标）。
- `make_reflective_dataset` 产出"反思数据集"：`{组件名: [记录, ...]}`，推荐记录 schema `{"Inputs": ..., "Generated Outputs": ..., "Feedback": ...}`——这是轨迹信息进入 LLM 提案的**唯一通道**。
- 最省事的接入路径：`DefaultAdapter`（`adapters/default_adapter/`），其轨迹就是：
```python
class DefaultTrajectory(TypedDict):
    data: DefaultDataInst          # {input, additional_context, answer}
    full_assistant_response: str
    feedback: str
```
且 `DefaultAdapter(model=...)` 接受任意 `messages->str` 的 callable，**不需要 litellm**。

### 2.2 Reflective mutation 怎么调 LLM

`proposer/reflective_mutation/reflective_mutation.py:242 propose()` 单轮流程（源码实读）：

1. `sampling_strategy.sample_tasks(...)`：从 Pareto 前沿选父候选（`ParetoCandidateSelector`）+ 从 trainset 采 minibatch（`EpochShuffledBatchSampler`）；
2. `adapter.evaluate(batch, parent, capture_traces=True)` 拿轨迹；
3. 跳过条件：无轨迹，或全部满分（`skip_perfect_score`）；
4. `module_selector` 选本轮要改的组件（round_robin 轮转 / all 全改）；
5. `adapter.make_reflective_dataset(...)` 把轨迹变成反思数据集；
6. **反思 LLM 调用**：默认实现 `strategies/instruction_proposal.py:InstructionProposalSignature`，模板核心（原文摘录）：

```
I provided an assistant with the following instructions to perform a task for me:
```
<curr_param>
```
The following are examples of ... along with the assistant's response ... and some feedback ...:
```
<side_info>
```
Your task is to write a new instruction for the assistant. ... Provide the new instructions within ``` blocks.
```
反思数据集被渲染成 markdown 塞进 `<side_info>`，LLM 返回新指令文本，从 ``` 围栏中提取（`output_extractor`）。**这一步就是"调 LLM"的全部**：`LanguageModel` 协议只是 `__call__(prompt: str | list[dict]) -> str`（`base.py:28`），传一个函数即可。

7. 新候选在同一 minibatch 上重评，接受准则（`strategies/acceptance.py:50`）：
```python
class StrictImprovementAcceptance:
    def should_accept(self, proposal, state) -> bool:
        old_sum = sum(proposal.subsample_scores_before or [])
        new_sum = sum(proposal.subsample_scores_after or [])
        return new_sum > old_sum
```

对工厂的意义：**LLM 只在"反思提案"这一处被调用，输出只有组件新文本（配方），永远拿不到执行权**——执行只发生在 `adapter.evaluate` 里，由工厂自己写。这与"JIT 只发射配方修改提案、人批准生效、永不直接干预执行"的设计约束天然吻合。

### 2.3 Pareto frontier 怎么维护

`core/state.py`（`frontier_type="instance"` 默认路径）：

```python
def _update_pareto_front_for_val_id(self, val_id, score, program_idx, ...):
    prev_score = self.pareto_front_valset.get(val_id, float("-inf"))
    if score > prev_score:
        self.pareto_front_valset[val_id] = score
        self.program_at_pareto_front_valset[val_id] = {program_idx}
    elif score == prev_score:
        self.program_at_pareto_front_valset[val_id].add(program_idx)
```

即：**按"单个验证样例"维护前沿**——每个 val 样例记录历史最高分及达到该分的候选集合；任何在"某件事"上最好的候选都留在前沿不死掉（论文动机：避免平均分抹杀偏科解）。0.1.4 还支持 `objective/hybrid/cartesian` 三种多目标前沿（`frontier_type` 状态校验处报错信息可证），多目标时要求 evaluator 提供 `objective_scores`。状态可 `save/load` 断点续跑（`GEPAState.save/load`），每次前沿更新原子写 JSON。

与工厂护栏的映射：
- **优化集/评估集隔离**：GEPA 原生就是 trainset（minibatch 接受判定）与 valset（前沿+选父）双集，隔离是结构性的；
- **审计下限**：可用 `ScoreThresholdStopper`/`NoImprovementStopper` 等停止器 + evaluator 返回分数时叠加下限罚分；
- **升迁联合单调**：strict improvement（minibatch 和严格增）+ 前沿按实例单调不回退；多目标前沿可承载"质量+成本"双指标。升迁（部署）不在 GEPA 语义内——它只产出 `GEPAResult.candidates/val_aggregate_scores/best_idx`，批准权天然留在工厂。

### 2.4 能否直接优化"任意文本配方"？——能，官方通用 API 就是 `optimize_anything`

`gepa/optimize_anything.py`（1701 行）模块 docstring 开头（原文）：
> "``optimize_anything`` — a universal API for optimizing any text parameter. ... If it can be serialized to a string and its quality measured, an LLM can reason about it and propose improvements."

```python
def optimize_anything(
    seed_candidate: str | Candidate | None = None,   # 可以没有种子（seedless 模式）
    *, evaluator: Callable | None = None,            # 返回 score 或 (score, side_info)
    dataset=None, valset=None,
    objective: str | None = None, background: str | None = None,
    config: GEPAConfig | None = None,                # EngineConfig/ReflectionConfig/...
) -> GEPAResult
```

三种模式：单任务搜索（无 dataset）、多任务迁移（只给 dataset）、泛化（dataset+valset）。评估器返回的 `side_info`（ASI）即"文本版梯度"。还内置 `terminal_bench_adapter`（`TerminusAdapter`）：candidate 就是 `{"instruction_prompt": ...}`，`evaluate` 直接 shell 出 `tb run` 跑 Terminal-Bench，轨迹取 episode 的 messages 历史，反思记录为 `{"Message History", "Instruction Prompt", "Feedback"}`——**"优化 agent 的指令配方"已有官方参考实现**。

---

## 3. AWM 实质解读（源码：~/bench-study/agent-workflow-memory）

### 3.1 trace→workflow 归纳算法

核心是**一次 LLM 调用**，没有迭代搜索。`mind2web/offline_induction.py:54 llm_generate()`：

```python
prompt = f"Website: " + ','.join(tags) + '\n'
prompt += format_examples(examples, args.prefix, args.suffix)
prompt = '\n\n'.join([args.INSTRUCTION, args.ONE_SHOT, prompt])
response = client.chat.completions.create(model=args.model_name,
    messages=[{"role": "user", "content": prompt}], temperature=args.temperature, max_tokens=1024)
```

归纳指令原文（`mind2web/prompt/instruction_abstract.txt`）：
> "Given a list of web navigation tasks, your task is to extract the common workflows to solve these tasks. ... find the repetitive subset of actions across multiple tasks ... Each workflow should have at least two steps. Represent the non-fixed elements (input text, button strings) with descriptive variable names as shown in the example."

后处理 `utils/data.py:filter_workflows()`：按空行切块，截取 `# <website> ... Workflows` 标题之后、剔除含 "delta" 的块——输出就是**纯文本 workflow 库**（每条 = `## 名称` + docstring + 抽象化步骤），例如 `webarena/workflow/shopping.txt` 即成品样例。

**输入 trace 格式**（两条路都汇到同一形态）：
- 离线：标注训练样本 dict，需要 `confirmed_task`（任务句）+ `action_reprs`（逐步动作行，如 `[textbox] Origin City or Airport -> TYPE: Seattle`）+ `domain/subdomain/website` 三级标签；Mind2Web 还需 `data/scores_all_data.pkl` 给候选元素打分。
- 在线（`online_induction.py:18 get_trajectory()`）：读自己跑出来的结果日志，凡 `{"input": [messages], "output": ...}` 的项取一步：`step = {"env": "# " + input 最后一条 user 消息, "action": output}`，再拼成 `env + '\n' + action` 的行序列。
- prompt 拼装（`format_examples`）：`Query #i: <task>` + `Actions and Environments:` + 逐行动作，多任务堆叠。

**输出 workflow 形态**：文本块；使用侧 `workflow/retrieve.py:load_workflows()` 解析 `## 名称`/第二行 docstring/正文，可用 FAISS+OpenAI embeddings 按 `name+docstring` 语义检索 top-k（`--mode semantic`），否则随机取。

### 3.2 离线归纳 vs 在线注入两条路径

`mind2web/pipeline.py`：
- `offline()`：`offline_induction.py`（从 ground-truth 训练样本一次性归纳）→ `run_mind2web.py --workflow_path workflow/<website>.txt`（固定注入评测）。注入方式：`memory.py:get_exemplars()` 把 workflow 文本作为第一条 user 消息放进 prompt，再随机抽 `retrieve_top_k` 条具体 exemplar（1009 条的 `data/memory/exemplars.json`，带 website specifier 过滤）。
- `online()`：按 `induce_steps`（默认 1）分批跑推理 → 每批后用**迄今全部成功结果**重跑 `online_induction.py` 覆盖 workflow 文件 → 继续下一批。即工作流记忆随流式经验滚动增长，冷启动时 workflow 文件为空也能跑（先裸跑再归纳）。

WebArena 侧（`webarena/induce_rule.py`）多一步日志清洗：从 think/action 块中提取、`remove_invalid_steps` 过滤非法动作再归纳。

### 3.3 工程接入评估

- **不可 pip**，只能 vendored。真正需要的只有约 500 行：`offline_induction.py`/`online_induction.py` + `utils/data.py` 的 `format_examples/filter_workflows` + 两个 prompt 文件（`instruction_abstract.txt` 9 行、`one_shot_abstract.txt` 88 行）。
- 代码是研究脚本形态：`input()` 交互选 split、路径硬编码 Mind2Web/WebArena schema、裸 `os.environ["OPENAI_API_KEY"]`。直接 import 会踩坑。
- 改造量估算：工厂 Trace 事件 → `action_reprs` 行格式的转换器约 **50–100 行**（每步一条 `<动作类型> <参数摘要> -> <动作>`，任务句 + 步骤行列表）；三级标签（domain/subdomain/website）需映射为工厂的产线/工序/站点标签。真正要做的工作在"语义"不在"代码"。

---

## 4. 实测运行记录（不调真实 LLM）

脚本存档：`~/bench-study/gepa-mock-example.py`、`~/bench-study/gepa-optimize-anything-mock.py`。

### 4.1 `gepa.optimize` + DefaultAdapter + mock 双 LM（PASS）
- `task_lm`：读候选 prompt，含 "ECHO" 才答对；`reflection_lm`：固定回一条改进指令。均纯 Python 函数，无 litellm。
- 结果：`candidates: 2`，`val_aggregate_scores: [0.0, 1.0]`，`best_idx: 1`，反思 LM 调用 1 次，跑满 63 轮迭代（预算 200 metric calls 消耗完）。**框架端到端可启动，优化产生真实分数提升**。
- 副产品验证：第一次跑挂在我 mock 写错（val 集 answer 映射错），GEPA 引擎本身对 minibatch 全满分的候选正确跳过反思（`All subsample scores perfect ... Skipping`），行为符合源码。

### 4.2 `optimize_anything` + mock 反思 LM（PASS）
- 配方 = 一行"调度阈值设为 N"的中文文本，evaluator 吞吐模型最优 70，mock 反思 LM 做 +5 爬山。
- 结果：`val_aggregate_scores: [7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]` **单调爬升**，17 轮收敛，`best_candidate: "调度阈值设为 70"`。候选到达最优后 `New subsample score 10.0 is not better than old score 10.0, skipping`——strict improvement 接受准则工作正常。
- 结论：**"任意文本配方 + 纯函数 evaluator + 可注入 reflection LM"这条链路真实可用**，且全程零第三方依赖。

---

## 5. 冷启动结论

### 5.1 GEPA 第一天没有自产 trace，能否直接消费外部轨迹产出第一批配方提案？

**能，但要把"消费外部轨迹"落成 Replay Adapter，而不是指望 GEPA 直接吃轨迹文件。** 依据与方案：

1. 语义澄清：GEPA 引擎的输入是 `(seed_candidate, trainset/valset, adapter)`，轨迹是 adapter 在 `evaluate` 里"生产"给 `make_reflective_dataset` 的中间产物，格式自定义。外部轨迹不能直接喂引擎，但可以喂 adapter。
2. Replay Adapter 方案（预估 **150–300 行**）：`DataInst` = 外部轨迹集的任务实例（或轨迹 id）；`evaluate()` 不跑真实 rollout，按 id 查外部轨迹表，返回该轨迹的成败分数（HAL 轨迹自带评分/成败标签；OpenHands 轨迹选 resolved 子集）+ 把轨迹消息序列包装成 `Trajectory`；`make_reflective_dataset` 把 `messages -> {"Inputs","Generated Outputs","Feedback"}`（Feedback=失败原因/测试结果）。此模式下 `max_metric_calls` 预算极便宜（无真实执行），反思 LM 只对 minibatch 提案。产出即"配方修改提案"（新 instruction/prompt 文本+分数证据），交人工批准。
3. 外部轨迹货源（已核实公开可得）：
   - OpenHands 轨迹：HF `nebius/SWE-rebench-openhands-trajectories`（32,161 条成功轨迹/67,074 次尝试，Qwen3-Coder-480B）；`nvidia/SWE-Hero-openhands-trajectories`（34k）；`nebius/SWE-agent-trajectories`（80k）；SWE-bench 官方 `SWE-smith-trajectories`。
   - HAL（Princeton Holistic Agent Leaderboard，[hal.cs.princeton.edu](https://hal.cs.princeton.edu)）：21,730 条 rollout（9 模型×9 benchmark）全量轨迹可下载，但**加密**，需其 `hal-decrypt.sh` 解密，接入前先验证解密与解析成本。
4. 风险提示：外部轨迹的 agent 框架、动作空间与工厂执行器不同，反思提案可能携带源框架特有套路；建议第一批提案只作"种子配方池"，由工厂评估集跑分后再升迁（这本来就是护栏要求）。
5. 兜底：`optimize_anything` 的 seedless 模式（`seed_candidate=None + objective`）可在零轨迹时让反思 LM 从目标描述直接造第一版配方。

### 5.2 AWM 能否从 Terminal-Bench 任务的 oracle solution 归纳工作流？

**机制上能、语义上打折，不建议作为第一天主路径。**

1. 格式可行性（已核实 TB 任务结构，harbor-framework/terminal-bench `tasks/bun-sourcemap-leak/` 实查）：每个任务 = `instruction.md`（任务句，对应 `confirmed_task`）+ `solution/solve.sh`（oracle 解，bash 脚本，对应 `action_reprs` 的步骤行）+ `tests/`（判分）+ `task.toml`。写一个 `solve.sh + instruction.md -> {confirmed_task, action_reprs}` 转换器约 **50–100 行**，套用 AWM 的归纳 prompt（INSTRUCTION + ONE_SHOT + format_examples），一次 LLM 调用即产出 workflow 文本块。`main` 分支实测 tasks 目录 68 项，量级足够做归纳语料。
2. 语义折扣：AWM 的方法论是"跨任务重复子程序 + think/act 里的策略抽象"；TB oracle solution 是**人写的直线脚本**，没有失败恢复、没有反思步骤、任务间共性弱（装依赖/跑测试这类通用套路抽象出来价值有限）。归纳出的 workflow 预期是宽泛模板，证据强度低于从**带成败标签的自产/外部 agent 轨迹**归纳。论文本身的增益场景是 Mind2Web/WebArena 这类同站点重复 UI 例程。
3. 工程负担：无包、依赖钉死（lxml==4.9.3 在 Python 3.14 编译困难）、研究脚本风格。建议只抄 prompt 与在线循环设计（每 N 个任务用累计成功轨迹重归纳、FAISS 语义检索注入 top-k），实现收敛进工厂自己的 JIT 服务。

### 5.3 一句话对比

- **GEPA = 现成的优化引擎**：零依赖、adapter 单点接入、原生"配方候选+分数"输出、trainset/valset 隔离与单调接受内置、`optimize_anything`/TB adapter 两个官方入口直击工厂需求 → **建议克隆为 JIT 冷启动内核**。
- **AWM = 一份方法论文档**：归纳靠一次 LLM 调用 + 好的 prompt，在线路径靠"边跑边重归纳"；代码不可复用为库 → **建议只移植其 prompt 与在线循环思想**。

## 附：本次实测产物路径
- 克隆：`~/bench-study/gepa`（f1cfdee2）、`~/bench-study/agent-workflow-memory`（8c0ff8cd）
- venv：`~/bench-study/.venv-jit`（gepa==0.1.4）
- mock 脚本：`~/bench-study/gepa-mock-example.py`、`~/bench-study/gepa-optimize-anything-mock.py`
- 关键源码（wheel 内）：`gepa/core/adapter.py`、`gepa/api.py`、`gepa/core/state.py`、`gepa/proposer/reflective_mutation/reflective_mutation.py`、`gepa/strategies/instruction_proposal.py`、`gepa/strategies/acceptance.py`、`gepa/optimize_anything.py`、`gepa/adapters/terminal_bench_adapter/terminal_bench_adapter.py`、`gepa/adapters/default_adapter/default_adapter.py`

## 参考来源
- [zorazrw/agent-workflow-memory](https://github.com/zorazrw/agent-workflow-memory)、[AWM 论文 arXiv:2409.07429](https://arxiv.org/abs/2409.07429)
- [gepa-ai/gepa](https://github.com/gepa-ai/gepa)（PyPI `gepa`，本地 wheel 0.1.4 即 HEAD 同版）
- [HAL 主站](https://hal.cs.princeton.edu)、[princeton-pli/hal-harness](https://github.com/princeton-pli/hal-harness)、[HAL 论文 arXiv:2510.11977](https://arxiv.org/abs/2510.11977)
- [nebius/SWE-rebench-openhands-trajectories](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories)、[nvidia/SWE-Hero-openhands-trajectories](https://huggingface.co/datasets/nvidia/SWE-Hero-openhands-trajectories)、[nebius/SWE-agent-trajectories](https://huggingface.co/datasets/nebius/SWE-agent-trajectories)、[Nebius 博客](https://nebius.com/blog/posts/openhands-trajectories-with-qwen3-coder-480b)
- [harbor-framework/terminal-bench](https://github.com/harbor-framework/terminal-bench)（任务结构经 GitHub contents API 实查）
