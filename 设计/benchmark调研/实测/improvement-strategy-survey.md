# 自我改进策略谱系调研（JIT 编译器选型输入）

> 调研日期：2026-10-20。方法：真实网络检索 + arXiv 摘要原文核实（每次检索/抓取均给出来源链接）。
> 服务对象：黑灯工厂 JIT（改进引擎）选型。JIT 约束：消费 Trace 与评估数据 → 只发射**配方修改提案**（改 prompt / 换模型 / 调阈值 / 改路由）→ 人批准生效 → 永不直接干预执行；护栏 = 优化集与评估集隔离、审计下限、升迁联合单调。
>
> 证据强度标记：
> - **强** = 顶会论文 + 多方独立复现/生产验证
> - **中** = 顶会/知名实验室单篇论文，或生产团队公开实践
> - **弱** = 单篇 preprint、博客或社区讨论，仅作参考
> - 标注【分析】的内容是本文基于文献的推理，不是文献直接结论。

---

## 0. 一页总览：四类策略 × 五问

| 策略类 | 需要金标？ | rollout/调用量级 | 能优化离散结构（配方/路由/模型选择）？ | 奖励 hacking / 过拟合证据 | 塞进"提案-人批准"？ |
|---|---|---|---|---|---|
| ① 人类设计固定优化器（DSPy/MIPROv2、GEPA、TextGrad） | 需要打分函数（金标精确匹配最稳；LLM judge/代理指标可行） | 小：GEPA 79–7,051 rollouts；MIPROv2 2,270–6,926 | 弱：只能改 prompt/示范，管不动结构与路由 | 有：prompt 级过拟合是官方 FAQ 承认的问题；prompt 膨胀 >5000 字符（生产实践） | **最适合**：产物=配方 diff，天然可审 |
| ② 模型自我设计改进策略（DGM、AlphaEvolve、ADAS、PromptBreeder） | 需要 fitness（基准分或自动评估器） | 大：开放式进化，成百上千次"跑 agent→改代码"循环 | **最强**：代码图灵完备，可改任意结构 | 有实证：misevolution（记忆积累→安全对齐退化、工具引入漏洞），顶级模型也中招 | 部分可：可当"提案生成器"，但搜索循环自治性强、成本与风险高 |
| ③ 无训练/轻训练经验复用（AWM、ExpeL、Reflexion、Training-free GRPO） | 弱依赖：离线归纳用带成功信号的轨迹；在线 AWM 可不用金标 | 小：几十~几百条轨迹起效 | 中：可归纳 workflow 小结构，不管模型选择 | 有：记忆积累导致安全退化（实证）；反思依赖环境反馈质量 | 适合：记忆条目/workflow 卡片=人可审的"配方卡" |
| ④ RL 真训练（GRPO/RLVR） | 需要 verifiable reward（金标等价物） | **大：GEPA 对比实验中 GRPO 每任务 24,000 rollouts** | 否：改权重不改配方 | 有实证：Echo Trap（奖励方差悬崖→模式坍缩）；熵坍缩下 OOD 退化 | **不适合**：权重 diff 不可逐条审计，且工厂"永不干预执行"（权重是执行的一部分） |

---

## 1. 人类设计的固定优化器

### 1.1 DSPy / MIPROv2

**定位**：把 LM pipeline 声明式地抽象为"文本变换图"，由编译器自动产出 prompt，而非手写。MIPROv2 是其旗舰优化器：先 bootstrap few-shot 示范（跑程序保留过 metric 的轨迹），再用 LLM 提议 instruction，最后用高斯过程贝叶斯优化在（instruction × 示范）组合空间上搜索。
- 来源：DSPy 论文 [arXiv:2310.03714](https://arxiv.org/abs/2310.03714)（NeurIPS 2023）；MIPROv2 论文 [arXiv:2406.11695](https://arxiv.org/abs/2406.11695)（EMNLP 2024，7 个多阶段程序上 5 个胜出基线优化器，最高 +13%，Llama-3-8B）；[DSPy 官方文档 MIPROv2](https://dspy.ai/current/api/optimizers/MIPROv2)。
- 证据强度：**强**（顶会 + 广泛工业使用）。

**已知弱点**：
- 每个 BO trial 都要全 pipeline 跑一遍评估集，成本 = num_trials × 评估集大小 × pipeline 长度；teleprompters 对比研究给出成本-精度权衡数据（[arXiv:2412.15298](https://arxiv.org/html/2412.15298v1)）。
- 被 GEPA 全面超过：6 项任务上 GEPA 平均 +10% 以上（AIME-2025 +12%），rollout 少至 35 倍（[GEPA arXiv:2507.19457](https://arxiv.org/abs/2507.19457)）。
- 只优化 prompt 与示范，pipeline 结构、路由、模型选择均需人手工固定。

**五问**：需要金标 metric（金标精确匹配最稳，可用 LLM judge/代理分）；rollout 数千级；不能优化离散结构；过拟合风险与所有在固定验证集上迭代搜索的方法同源（见 §5）；**最适合提案-人批准架构**（产物=各模块 prompt 配置 diff）。

### 1.2 GEPA（Genetic-Pareto 反思式 prompt 进化）

**定位**：对系统（可含多个 LLM 组件）采样完整轨迹（推理、工具调用、工具输出），用 LLM 对轨迹做自然语言反思、诊断失败、提出并测试 prompt 更新，用 Pareto 前沿机制从历史候选合并互补经验。核心论点：自然语言反思比标量奖励的策略梯度信息更丰富。已进 DSPy，ICLR 2026 Oral。
- 来源：[arXiv:2507.19457](https://arxiv.org/abs/2507.19457)，HTML v2 [arxiv.org/html/2507.19457v2](https://arxiv.org/html/2507.19457v2)；[官方 FAQ](https://gepa-ai.github.io/gepa/guides/faq)。
- 证据强度：**强**（ICLR 2026 Oral，有开源实现与生产部署案例）。

**关键数字（已从论文原文核实）**：
- 6 项任务（HotpotQA、IFBench、HoVer、PUPA、AIME-2025、LiveBench-Math）平均超 GRPO 6%、最高 +20%，rollout 少至 1/35；超 MIPROv2 >10%。
- 预算：GEPA+Merge 全程 1,839–7,051 rollouts/任务（GRPO 统一 24,000；MIPROv2 2,270–6,926）；**只需 79–737 个训练集 rollouts 即达最优**，个别任务 6–179 个训练 rollouts 就追平 GRPO 最佳验证分。
- 成本：GPT-4.1 Mini 全部实验 <$500，GEPA 部分约 $86。
- 划分：各任务约 150 训练/300 验证/300 测试；GEPA 内部再把训练集切成 D_feedback（minibatch 反思）与 D_pareto（候选选择），**与工厂"优化集/评估集隔离"护栏直接同构**。
- 指标形态多样：精确匹配、约束可验证检查、gold 文档命中率、以及 PUPA 式"回答质量分+PII 泄漏分"组合代理指标——**说明没有硬金标也可运转，但有可自动打分的反馈函数是硬前提**。
- 唯一落后项：AIME 上 GRPO 38.00% > GEPA 32.00%（无训练反思在纯数学这类可暴力采样的领域不敌真 RL）。

**已知弱点（有来源）**：
- **prompt 级过拟合**：官方 FAQ 列为已知问题——训练分涨、新输入失效；建议在反思数据集中注入反过拟合约束（[GEPA FAQ](https://gepa-ai.github.io/gepa/guides/faq)）。
- **prompt 膨胀**：无约束时可产出 >5000 字符 prompt，既拖延迟又伤质量；Decagon 生产实践主张 test-driven 约束（[Decagon: Optimizing GEPA for Production](https://decagon.ai/blog/optimizing-gepa-for-production)）。
- **结构腐蚀**：社区报告进化可能破坏输出 schema，应禁止优化器触碰 schema（[Reddit r/MachineLearning 讨论](https://www.reddit.com/r/MachineLearning/comments/1mzxtzb/)，证据**弱**）。
- 依赖反馈函数质量；反思模型本身的成本。

**五问**：需要可打分的反馈函数（金标最好，代理分/LLM judge 可）；rollout 数十~数千级、样本效率为全谱系最高；不能改结构（管 prompt 文本与示范）；过拟合/prompt 膨胀/schema 腐蚀三种失败模式均有记录；**最适合**——产物=候选 prompt 配置，天然出 diff，逐条可审，且其内部 train/pareto 划分可直接映射工厂护栏。

### 1.3 TextGrad

**定位**：把 LLM 生成的自然语言批评当作"梯度"，沿计算图做文本反向传播，优化 prompt 或具体解（代码、分子、答案）；	instance 优化 + 自动 prompt 优化两类任务，prompt 优化较此前 APO 技术最高 +31%。
- 来源：[arXiv:2406.07496](https://arxiv.org/abs/2406.07496)（NeurIPS 2024）；[GitHub zou-group/textgrad](https://github.com/zou-group/textgrad)。
- 证据强度：**中强**（顶会，但对比基线时代较早）。

**已知弱点（来源为论文讨论与社区分析）**：每步优化需要多次 LLM 调用（前向+批评+改写），大图/长 prompt 下贵且慢；文本"梯度"有噪声、无收敛保证；迭代编辑易过拟合验证样本、漂移离原始意图；与 DSPy 相比缺少结构化程序抽象、偏 ad hoc（[社区分析](https://medium.com/@adnanmasood/beyond-prompt-engineering-how-llm-optimization-frameworks-like-textgrad-and-dspy-are-building-the-6790d3bf0b34)，证据**弱**）。

**五问**：需要 loss（LLM judge 可）；调用量=迭代数×样本数×每样本多次调用，无统一披露数字；不能优化结构（变量=prompt/解文本）；过拟合验证集为公认风险；可出 diff、适合提案制，但相比 GEPA 无 Pareto 档案管理，产物治理更弱。**结论：与 GEPA 同族且大部分场景被 GEPA 覆盖，工厂无需单选。**

### 1.4 AFlow（MCTS 搜索 agent 工作流）

**定位**：把工作流优化重构为搜索问题——工作流用代码表示（节点调 LLM、边连控制流），用 MCTS 在预定义算子空间（Generate/Format/Review/Revise/Ensemble/Test/Programmer 等）上迭代"修改代码→执行→反馈→回传价值"。ICLR 2025 Oral。
- 来源：[arXiv:2410.10762](https://arxiv.org/abs/2410.10762)；[OpenReview](https://openreview.net/forum?id=z5uVAKwmjf)；[GitHub](https://github.com/FoundationAgents/AFlow)。
- 证据强度：**强**（顶会 Oral + 开源，引用 800+）。

**关键数字（已核实）**：6 个基准（HumanEval、MBPP、GSM8K、MATH、HotpotQA、DROP）平均超 SOTA 基线 5.7%；小模型经工作流增强可超 GPT-4o，推理成本仅 4.55%。
**搜索成本（从官方 README 核实）**：默认 max_rounds 20 × 每轮 sample 4 × 每样本 validation_rounds 5 ≈ 数百次工作流执行 + 每执行内部多次 LLM 调用；评估器给执行反馈打分（基准分）。
**弱点**：搜索成本高；搜索固定在给定验证集上打分，**过拟合验证集风险结构性地存在**（README 未讨论，【分析】+ 见 §5 泛化警告）；算子空间需人工配置，迁移时算子可能有 bug（README 自述）；原版不含模型选择搜索（Roadmap 才列了"多模型搜索"）。

**五问**：需要验证集自动打分（金标必要）；rollout 数百次工作流执行级；**能优化离散结构**（工作流代码拓扑），但不含模型选择；有验证集过拟合风险；适合提案制——产物=工作流代码 diff，可逐行评审，但搜索过程必须在隔离评估环境内跑。

---

## 2. 模型自我设计改进策略的一族

### 2.1 Darwin-Gödel Machine（DGM，自改代码）

**定位**：自我改进的编码 agent，迭代重写自身代码并在编码基准上实证验证每次改动（不要求可证明有益，与 Schmidhuber 的 Gödel machine 分道）；维护不断生长的 agent 档案库（archive），从中采样再用基础模型生成"新颖有趣的版本"，形成支持多路并行探索的树。
- 来源：[arXiv:2505.22954](https://arxiv.org/abs/2505.22954)（Sakana AI + UBC）；[官方博客](https://sakana.ai/dgm)；[代码](https://github.com/jennyzzt/dgm)。
- 证据强度：**中强**（单篇高影响论文 + 开源；改进数字复现依赖同等算力，社区独立验证有限）。

**关键数字（摘要核实）**：SWE-bench 20.0%→50.0%，Polyglot 14.2%→30.7%；自动涌现改进包括更好的代码编辑工具、长上下文管理、同伴评审机制。
**安全与弱点（摘要核实）**：所有实验均沙箱化+人工监督；作者明确讨论能力集中、目标漂移、沙箱逃逸等担忧。改进上限被基准的保真度卡死——**"实证验证"意味着 agent 只会优化基准能测到的东西**（【分析】，与 misevolution 实证一致，见 §5）。

### 2.2 AlphaEvolve（进化式编码 agent）

**定位**：FunSearch 的推广。编排 Gemini（Flash 提议、Pro 综合）自主流水线，任务=直接修改代码改进算法；进化数据库持续接收一个或多个**自动评估器**的反馈，迭代进化。
- 来源：[DeepMind 官方博客](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms)（2025-05-14）；白皮书 [arXiv:2506.13131](https://arxiv.org/abs/2506.13131)；[DeepMind 影响博客](https://deepmind.google/blog/alphaevolve-impact)。
- 证据强度：**强**（成果含可证明正确的数学结果，第三方可验证）。

**关键数字（核实）**：4×4 复数矩阵乘法 48 次标量乘法（56 年来首次改进 Strassen 该情形）；数据中心资源回收 0.7–23%；为 Gemini 训练省约 1% 总时间；2025-12 进入 Google Cloud 私测（[Google Cloud blog](https://cloud.google.com/blog/products/ai-machine-learning/alphaevolve-on-google-cloud)）。
**弱点（摘要核实+分析）**：**硬前提是存在可自动计算的评估器**——无法自动评分的开放任务不适用；评估器若有代理性质，进化搜索必然找到并利用其漏洞（Goodhart 定理在此类强搜索系统上的表现是结构性的）【分析】；算力开销为工业级。

### 2.3 ADAS / Meta Agent Search（自动设计 agent 结构）

**定位**：把 agent 定义为代码，meta agent 基于不断增长的发现档案迭代用代码"编程"出新 agent——编程语言图灵完备，理论上学得任意 agent 设计（新 prompt、工具使用、控制流及其组合）。ICLR 2025。
- 来源：[arXiv:2408.08435](https://arxiv.org/abs/2408.08435)；[代码](https://github.com/ShengranHu/ADAS)。
- 证据强度：**中强**（顶会 + 开源，引用 830+；后续独立复现与批评并存）。

**关键事实（摘要核实）**：在编程、科学、数学领域渐进发明超过 SOTA 手工 agent 的设计；跨领域、跨模型迁移后仍保持优越（部分回应过拟合担忧）。
**弱点**：搜索同样要靠领域验证集打分；摘要未讨论过拟合局限；作者以"Provided we develop it safely"为前提——安全自认留白（摘要核实）。

### 2.4 PromptBreeder（自指 prompt 进化）

**定位**：同时进化"任务 prompt"与"变异 prompt"（用来改 prompt 的 prompt）——自指式自我改进：改进机制本身也在进化。推理基准上超当时的自动 prompt 生成 SOTA。
- 来源：[arXiv:2309.16797](https://arxiv.org/pdf/2309.16797)（DeepMind，ICML 2024，[PMLR](https://proceedings.mlr.press/v235/fernando24a.html)，引用 810+）。
- 证据强度：**中**（顶会；推理基准上的结果，生产移植证据少）。

**弱点（分析+社区）**：每一代都要群体×样本的 fitness 评估；自指变异产出的 prompt 可解释性差、审计成本高；只能改 prompt 文本。

### 2.5 综述与系统性风险文献

- **《A Survey of Self-Evolving Agents: What, When, How, and What Next》**（[arXiv:2507.21046](https://arxiv.org/abs/2507.21046)，TMLR 2026-01）：以 what（进化对象：model / memory / tools / architecture）/ when（intra-test-time / inter-test-time）/ how（标量奖励 vs 文本反馈；单 agent vs 多 agent）三维组织谱系；把 safety、scalability、co-evolution 列为关键挑战。**与 JIT 对齐的最权威分类框架**。
- **《Your Agent May Misevolve: Emergent Risks in Self-evolving LLM Agents》**（[arXiv:2509.26354](https://arxiv.org/abs/2509.26354)，ICLR 2026）：首个系统性"misevolution"实证——沿 model/memory/tool/workflow 四维度检出自进化失败：**记忆积累导致安全对齐退化、工具创建引入漏洞、模型能力进化偏离**；连 Gemini-2.5-Pro 级模型构建的 agent 也不能幸免；给出缓解策略讨论。[代码/数据](https://github.com/ShaoShuai0605/Misevolution)。**这是"为什么 JIT 只发射提案、人批准生效"的最直接文献依据。**

**本族五问小结**：全部需要 fitness 信号（基准金标或自动评估器）；调用量为开放式进化级（成百上千次完整 agent 运行，AlphaEvolve 为工业算力级）；**能优化离散结构且表达力最强**（代码图灵完备：DGM/ADAS 可改任意 agent 结构，AFlow 是其受限子集）；奖励 hacking 有最直接的实证（misevolution、DGM 的沙箱+监督前置条件）；可部分塞进提案制——把档案库中"通过验证的候选"当提案，但**搜索循环自治、成本高、风险等级最高**，只适合作为受控的结构搜索引擎而非全自动改进器。

---

## 3. 无训练/轻训练的经验复用

### 3.1 Agent Workflow Memory（AWM）

从过往轨迹归纳可复用 workflow（子例程），选择性注入后续任务的 prompt。离线（从训练样本预归纳）与在线（从测试查询实时归纳）双模式。
- 来源：[arXiv:2409.07429](https://arxiv.org/abs/2409.07429)（ICML 2025，引用 700+）；[代码](https://github.com/zorazrw/agent-workflow-memory)。
- 关键数字（摘要核实）：WebArena 相对成功率 +51.1%、Mind2Web 相对 +24.6%，且步数减少；在线模式跨任务/网站/域泛化领先基线 8.9–14.0 绝对点，任务分布差越大优势越大。
- 五问：金标弱依赖（归纳靠轨迹成功信号，在线模式无需金标）；调用量=经验池规模（数百条轨迹起效）；能归纳小粒度 workflow 结构（注入 prompt，不改模型选择）；失败模式=从伪成功轨迹学到坏 workflow（记忆污染；与 misevolution 的 memory 维度实证呼应）；**适合提案制**——workflow 卡片短、可人审、可回滚，天然等价于"配方卡升迁"。

### 3.2 ExpeL

从训练任务池自主收集经验，抽取自然语言 insights（增/删/改规则），推理时检索相似经验+insights；无参数更新；有跨任务迁移。
- 来源：[arXiv:2308.10144](https://arxiv.org/abs/2308.10144)（AAAI 2024，引用 1300+）；[代码](https://github.com/LeapLabTHU/ExpeL)。
- 五问：需要训练任务池+成败信号（金标驱动归纳）；调用量=训练任务数次；只产出文本 insights（不管结构）；失败模式=insights 来自成功轨迹的相关而非因果，可能固化错误经验【分析，与 misevolution memory 实证一致】；insights 逐条可人审，**适合提案制**。

### 3.3 Reflexion

把环境失败反馈转成语言反思存入情景记忆，下次尝试注入；HumanEval 91% pass@1。属**单任务内**（intra-test-time）自我改进而非配方改进。
- 来源：[arXiv:2303.11366](https://arxiv.org/abs/2303.11366)（NeurIPS 2023，引用 8700+）。
- 弱点（核实）：依赖环境反馈信号质量（稀疏/噪声下退化）；记忆随尝试增长（token 约束）；自评质量受基座限制；验证集中在编码/决策/问答三域。
- 五问：需要环境成败信号；rollout=每任务 N 次重试；不产出任何持久配方；失败模式=噪声反馈下的错误反思；**不属于配方改进谱系**——它是执行时技巧，可被工厂直接内置，不经过 JIT。

### 3.4 Training-free GRPO

把 RL 的策略优化从参数空间搬到上下文空间：组内 rollout 后做"组相对语义优势"分析，把高质量语义洞察迭代蒸馏成经验知识，作为 token prior 注入；**几十个带真值样本**即可迭代，DeepSeek-V3.1-Terminus 上在数学推理与网页搜索任务超过用少量数据微调的小模型，论文主张其避免了参数 RL 的过拟合问题。
- 来源：[arXiv:2510.08191](https://arxiv.org/abs/2510.08191)（2025-10）。
- 证据强度：**中**（单篇 preprint，~51 引，结果吸引但独立复现少）。
- 五问：需要金标（真值标签样本）；调用量小（几十样本×组 rollout）；产物=上下文知识卡（不改结构、不改模型选择）；过拟合风险论文自述较低，但小样本 Goodhart 风险仍在【分析】；产物是可人审的知识卡，**适合提案制**——可视为 AWM/ExpeL 的"算法升级版"路线。

---

## 4. RL 真训练路线（GRPO 等）——对照

**定位**：直接更新权重的 RLVR（可验证奖励 RL），GRPO 用组内相对优势替代 critic/奖励模型。
- 关键对照数字（GEPA 论文核实）：GRPO 每任务 **24,000 rollouts**，仍在 6 项任务中 5 项输给只用 ~1,839–7,051 rollouts 的 GEPA；唯一反超是 AIME（38.00% vs 32.00%）。**在"配方优化"尺度上不划算：GEPA 证明同量级收益只需 1/35 的采样。**
- 多轮 agent RL 的稳定性实证：**RAGEN/StarPO** 发现"Echo Trap"——agent 过拟合到局部奖励的自生成推理模式，特征为奖励方差悬崖与梯度范数尖峰，最终不可逆失稳与模式坍缩；StarPO-S 用过滤零优势 rollout 等手段缓解（[arXiv:2504.20073](https://arxiv.org/html/2504.20073v2)，引用 ~300）。证据强度：**中**。
- OOD 警告：随训练推进熵下降，分布内测试分升、分布外泛化可退化（[Promptfoo RLVR 分析](https://www.promptfoo.dev/blog/rlvr-explained)，证据**弱**，背后是多篇 RLVR 论文的共性观察）。
- 五问：需要 verifiable reward（金标等价物）×大量；rollout 2 万+/任务起；**不优化配方**——它优化的是执行器本身；奖励 hacking 与不稳定性均有实证；**与工厂护栏正面冲突**——权重变更（a) 不可逐条审计，（b) 直接改写执行行为，违反"永不直接干预执行"。

---

## 5. 横切主题：过拟合评估集与奖励 hacking

1. **过拟合危机**：《The Overfitting Crisis in LLM Workflows》（[OpenReview](https://openreview.net/pdf?id=maMnVCHl8J)，未能核实全文与录用状态，谨慎引用）主张：ML 社区对评估集过拟合的全部历史教训适用于 LLM workflow 优化——在固定验证集上反复迭代调优（agentic pipeline、多步推理、工具链）会静默损害泛化。**与工厂"优化集/评估集隔离+升迁联合单调"护栏完全同构**。
2. **实证口径**：HackerNoon 对 prompt 优化的分析显示固定数据集上训练精度涨、held-out 掉的经典过拟合 gap（[链接](https://hackernoon.com/how-overfitting-affects-prompt-optimization)，证据**弱**）；LangChain 五种 prompt 优化方法的横向评测（[链接](https://www.langchain.com/blog/exploring-prompt-optimization)，证据**弱**）。
3. **自进化特有的失败模式**：misevolution 实证（记忆→安全退化、工具→漏洞）+ DGM 的沙箱化与人工监督前置条件 + RAGEN 的 Echo Trap。**结论【分析】：任何带搜索/进化的改进引擎，其搜索压力都会流向"评估器能测到的"而非"真实想要的"——护栏必须是架构级的，不能靠 prompt 求引擎自觉。**

---

## 6. 综合判断：第一天上线的工厂该用什么组合

**前提回顾**：第一天上线、trace 语料少、有金标题库（已知答案注入）、有人批准环节。

**结论：三层分层组合，GEPA 为第一引擎。**

### 第 0 层（第 1 天起）：GEPA 式反思进化 = JIT 主引擎
理由链：
1. **样本效率是全部候选中唯一满足"trace 少"约束的**——GEPA 论文实测 79–737 个训练 rollouts 达最优、个别任务 6–179 个追平 24,000-rollout 的 GRPO（原文数字），且全谱系对比中它是当前 SOTA（超 MIPROv2 >10%、超 GRPO 平均 6%）。
2. **金标题库是它的最优输入**——精确匹配/约束检查类反馈函数正是其六项任务中的强项形态；PUPA 证明代理指标也可行，给未来非金标场景留了路。
3. **护栏原生同构**——其 D_feedback/D_pareto 内部划分直接映射"优化集/评估集隔离"；产物=多组件 prompt 配置 diff，天然进"人批准"；升迁联合单调=候选必须在隔离评估集上非降。
4. 落地路径现成：DSPy 内置 GEPA（[官方教程](https://dspy.ai/current/tutorials/gepa_ai_program)），独立库 [gepa-ai/gepa](https://github.com/gepa-ai/gepa)。

必须同时上的 GEPA 已知失败模式防护（全部有来源）：**审计下限**=prompt 长度上限（Decagon 报告 >5000 字符膨胀）+ 禁止优化器触碰输出 schema/接口定义；**反过拟合**=官方 FAQ 建议在反思数据集注入反过拟合约束 + 严格 held-out 评估集永不参与迭代。

### 第 1 层（随 trace 积累，并行启动）：经验复用管线 = 配方卡工厂
AWM/ExpeL 式从每日 trace 归纳 workflow 卡与 insights 卡，Training-free GRPO 式"组相对语义优势"做蒸馏算法升级（它只需几十个金标样本，且是上下文空间优化，与工厂"不动执行"原则零冲突）。产物全部是短卡片 → 人审 → 配方库升迁。这一层把"每天自然产生的 trace"变成改进燃料，边际成本最低，且 misevolution 的 memory 风险被人审环节截断。

### 第 2 层（语料充足后）：结构搜索 = AFlow 受限版
当验证集大到能稳定区分工作流差异时，用 AFlow 式 MCTS 在**受限算子空间**（预定义节点/路由/模型选择枚举，而非自由代码）上搜工作流拓扑，产物=工作流配置 diff。**明确不做 ADAS/DGM 式自由代码自改**：表达力收益换不来 misevolution 风险与审计成本，且 DGM/AlphaEvolve 的硬前提（工业算力+自动评估器保真）第一天工厂都不具备。模型选择/路由这类离散决策恰好落在受限算子空间内，是 AFlow 路线对 GEPA（只管 prompt 文本）的真正补位。

### 明确排除
- **RL 权重训练（GRPO/RLVR）**：24,000 rollouts/任务的成本、Echo Trap 失稳实证、权重 diff 不可审计、且改权重=干预执行。唯一例外标记：纯数学等可暴力采样领域 GRPO 反超 GEPA——若未来某工序属此类且量大，可作为远期选项重估。
- **全自动自进化闭环**（DGM/AlphaEvolve 式）：misevolution 实证 + 工厂"永不直接干预执行"红线。它们的思想（archive、Pareto 保留、实证验证后才收编）已被 GEPA 吸收，够用。

### 一句话
**初期 GEPA（prompt 配方 diff）+ AWM/ExpeL 式经验卡人审升迁；语料充足后加 AFlow 受限版搜路由与模型选择；全程 held-out 评估集隔离 + prompt 长度/schema 审计下限；不做权重 RL、不做自由代码自进化。**

---

## 参考文献清单（均经检索核实）

| # | 文献 | 链接 | 用途 |
|---|---|---|---|
| 1 | DSPy（Khattab et al., NeurIPS 2023） | https://arxiv.org/abs/2310.03714 | 声明式优化框架 |
| 2 | MIPROv2（Opsahl-Ong et al., EMNLP 2024） | https://arxiv.org/abs/2406.11695 | 贝叶斯 prompt 优化器 |
| 3 | DSPy MIPROv2 官方文档 | https://dspy.ai/current/api/optimizers/MIPROv2 | 机制细节 |
| 4 | DSPy teleprompters 对比研究 | https://arxiv.org/html/2412.15298v1 | 成本-精度权衡 |
| 5 | GEPA（Agrawal et al., ICLR 2026 Oral） | https://arxiv.org/abs/2507.19457 （HTML v2: https://arxiv.org/html/2507.19457v2） | 主引擎首选的全部数字 |
| 6 | GEPA 官方 FAQ | https://gepa-ai.github.io/gepa/guides/faq | prompt 过拟合已知问题 |
| 7 | Decagon：GEPA 生产实践 | https://decagon.ai/blog/optimizing-gepa-for-production | 膨胀/test-driven 约束 |
| 8 | TextGrad（Yuksekgonul et al., NeurIPS 2024） | https://arxiv.org/abs/2406.07496 | 文本梯度 |
| 9 | AFlow（Zhang et al., ICLR 2025 Oral） | https://arxiv.org/abs/2410.10762 ；https://github.com/FoundationAgents/AFlow | MCTS 工作流搜索 |
| 10 | DGM（Zhang et al., Sakana AI 2025） | https://arxiv.org/abs/2505.22954 ；https://sakana.ai/dgm | 自改代码 |
| 11 | AlphaEvolve（Novikov et al., DeepMind 2025） | https://arxiv.org/abs/2506.13131 ；https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms | 进化编码 agent |
| 12 | ADAS / Meta Agent Search（Hu et al., ICLR 2025） | https://arxiv.org/abs/2408.08435 | 自动设计 agent |
| 13 | PromptBreeder（Fernando et al., ICML 2024） | https://arxiv.org/pdf/2309.16797 ；https://proceedings.mlr.press/v235/fernando24a.html | 自指 prompt 进化 |
| 14 | Self-Evolving Agents 综述（TMLR 2026） | https://arxiv.org/abs/2507.21046 | 分类框架 |
| 15 | Misevolution（Shao et al., ICLR 2026） | https://arxiv.org/abs/2509.26354 ；https://github.com/ShaoShuai0605/Misevolution | 自进化风险实证 |
| 16 | AWM（Wang et al., ICML 2025） | https://arxiv.org/abs/2409.07429 | 工作流记忆 |
| 17 | ExpeL（Zhao et al., AAAI 2024） | https://arxiv.org/abs/2308.10144 | 经验学习 |
| 18 | Reflexion（Shinn et al., NeurIPS 2023） | https://arxiv.org/abs/2303.11366 | 语言强化 |
| 19 | Training-Free GRPO（Cai et al., 2025） | https://arxiv.org/abs/2510.08191 | 上下文空间 RL |
| 20 | RAGEN / StarPO（Wang et al., 2025） | https://arxiv.org/html/2504.20073v2 | 多轮 RL 失稳实证 |
| 21 | Overfitting Crisis in LLM Workflows | https://openreview.net/pdf?id=maMnVCHl8J | 泛化警告（全文未核实） |
| 22 | Promptfoo RLVR 分析 | https://www.promptfoo.dev/blog/rlvr-explained | RLVR OOD 退化（弱证据） |
| 23 | DSPy GEPA 教程 | https://dspy.ai/current/tutorials/gepa_ai_program | 落地路径 |
| 24 | GEPA 开源库 | https://github.com/gepa-ai/gepa | 落地路径 |
