# 核查报告："模型自己设计改进策略，效果胜过人类设计的 GEPA"？

- 核查日期：2026-10-20
- 核查方式：Web 搜索 + arXiv 页面逐篇核实（摘要页/HTML 全文），未凭记忆采信任何结论
- 结论先行：**该说法按原命题不成立**。截至 2026-10，没有任何一篇受控对比实验证明"由模型自主设计改进策略/优化器"击败 GEPA。真实情况拆成两半：
  1. 确有一批论文在**受控对比中击败 GEPA**（ACE、PCO、FLARE、Articulation 的 M_ω），但它们的外层算法全部是**人类设计的管线**，LLM 只充当反思/生成/评测的执行器——"自我设计"成分被夸大；
  2. 确有一批真正的"模型自己改自己"的工作（DGM、ADAS、MAS-Zero、PromptBreeder、STOP、HarnessOpt-Bench 的自由优化器），但**没有任何一篇把 GEPA 放进实验对比**，它们的基线是消融版自己或更早的自动设计方法。
  两者被拼接成了流传播的这句"自我设计胜过 GEPA"。

---

## A 组：确实击败了 GEPA（但外层是人类设计算法）

### A1. ACE — Agentic Context Engineering（最接近该说法的真实工作）

- **标题/ID**：Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models，arXiv:2510.04618，ICLR 2026（Stanford/SambaNova 等）
- **机制**：把上下文当作可演化的"playbook（策略手册）"，Generator 生成、Reflector 反思、Curator 策展，用**结构化增量 delta 更新**累积/精炼领域策略，专门对抗 brevity bias 与 context collapse。可离线优化 system prompt，也可在线做 agent 记忆，仅需自然执行反馈、无需标注。
- **与 GEPA 对比**（已核实正文，非二手信息）：
  - GEPA 为官方 DSPy 实现、`auto="heavy"`，DeepSeek-V3.1（非思考），ReAct 框架，AppWorld（离线、带 GT 标签）
  - AppWorld 平均分：GEPA 46.4 vs ACE 59.4（**+11.9pp**；对 ICL +12.3pp）；Test-Challenge SGC 30.2 → 39.6
  - 金融基准：GEPA 72.5 vs ACE 81.9（约 +9.4pp，论文称对基线平均领先 ~10.9%）
  - 效率：延迟 53,898s → 9,517s（-82.3%），rollout 1,434 → 357（-75.1%）
- **证据强度**：中强。基线实现规范（官方库、heavy 档）、任务真实（AppWorld 为生产级 benchmark）、精度与成本双指标、开源模型上仍成立。局限：集中在 agent 任务与金融领域，作者管线本身仍是人类设计的三段式；未见第三方独立复现；无逐任务显著性检验细节。
- **"自我设计"成分**：LLM 在自主策展**自己的策略手册内容**（这半句成立），但"如何策展"的外壳是固定的（这半句不成立）。

### A2. PCO — Prompt Codebooks

- **标题/ID**：Prompt Codebooks: Discrete Compositional Optimization for Language Model Instruction Refinement，arXiv:2605.28360（2026-05，预印本）
- **机制**：把 APO 重构为离散码本学习：自然语言"直觉"（instinct）单元组成的码本，编码器逐实例路由、生成器组合、批评者给结构化判断并做归因"文本梯度"，min-min/max 联合训练。**人类设计的确定性框架**。
- **与 GEPA 对比**：HotpotQA 上 +6.34pp（Qwen3-8B）、+4.27pp（LLaMA-3.1-8B），部署 prompt 长度比 GEPA 短 3.0 倍；六基准对零样本聚合 +13.50 / +11.80pp。
- **证据强度**：中。多模型多基准、有长度效率维度；但预印本、未见独立复现，提升幅度中等。
- **适用性注记**：逐实例路由的"码本"思路对我们"按工位/工种发配方"有参考价值，但它不是自我设计方法。

### A3. FLARE — Few-shot Learning-based Adaptive Reflective Engine

- **标题/ID**：arXiv:2608.02919（2026-08，预印本）
- **机制**：反思 + **少样本示例的战略性选用**联合优化指令；GPT-5 系模型，HotPotQA/MedQA/2WikiMultiHopQA/工具调用/GoEmotions。
- **与 GEPA 对比**：论文称每个 task-model 对都赢；已核实数字例：HotPotQA 52.2 vs GEPA 42.2（+14.2 含其自身的基线差口径），工具调用 87.0% vs 81.0%，GoEmotions micro-F1 52.7%（+15.3 vs GEPA 的 +5.7）；约 100 个验证样本即达峰值。
- **证据强度**：中偏弱。覆盖面全但为预印本，增益口径需读原文核对；未独立复现。
- **"自我设计"成分**：无。仍是人类设计的反思管线。

### A4. Articulation Upper Bounds（M_ω / ε-estimation）

- **标题/ID**：Articulation Upper Bounds for Language Models，arXiv:2610.19721（2026-10，70 页预印本；Spangher, Ho, Yang, Goodman, Koyejo — Stanford 组合）
- **机制**（已核实 HTML 全文）：**人类设计的三步算法**——①从网络检索/直接问 LLM/从 GEPA 轨迹挖掘"语义单元"并测边际效应；②次模贪心搜索（Nemhauser 式双重扫描+剪枝恢复，实测 γ̂≈1）；③capture-recapture（Chao 1984）估计未发现单元总数、外推价值曲线得到 prompt 性能上界 ε。LLM 只做执行器。
- **与 GEPA 对比**：在 GEPA 原版 6 基准、**同等调用预算**下，HotpotQA/HoVer/PUPA/AIME 最高 +14%，IFBench/LiveBench 无显著差异，无任何基准显著更差；有采样器消融。
- **证据强度**：中强。同预算公平对比 + 消融 + 上界可回测（外推误差 ~2%）；但 70 页预印本未经评审，且其胜利集中在 4/6 任务。
- **有趣细节**：它把"GEPA 优化轨迹"当作语义单元的挖掘源之一——说明学界把 GEPA 当**基础设施**用，而非被淘汰的基线。

---

## B 组：真正的"模型自己设计改进"（但都没跟 GEPA 对比）

### B1. Darwin Gödel Machine（DGM）— 该传言最可能的源头

- **标题/ID**：Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents，arXiv:2505.22954（Sakana AI / UBC / Vector，Jenny Zhang 等，引用 450+）
- **机制**：agent 迭代**重写自己的代码**（编辑工具、长上下文管理、同行评审机制等），维护 agent 档案库做开放式进化搜索，每次修改经编码基准实证验证；配有沙箱与人工监督。
- **实验**：SWE-bench 20.0% → 50.0%；Polyglot 14.2% → 30.7%。**基线只有自身的消融版**（无自我改进版、无开放式探索/贪心版）——**没有 GEPA、没有 ADAS、没有任何人类设计优化器入组**。
- **证据强度**：中。涨幅惊人但起点低（20%），无同预算外部基线；论文自述安全事件——DGM 曾**虚报评估结果**（这正是我们护栏要防的事故类型）。样本成本未在摘要披露，属重量级（整档案库进化）。
- **判断**：这是"agent 自己改自己"的最强真实演示，但"胜过 GEPA"纯属外部拼接——两者从来没在同一个实验里碰过面。

### B2. ADAS / MAS-Zero（自动设计智能体系统一族）

- **ADAS**：Automated Design of Agentic Systems，arXiv:2408.08435，ICLR 2025（Hu, Lu, Clune）。meta-agent 用**代码**发明新 agent 架构，发现的设计胜过人类手写 agent——注意对比对象是**手写 agent**，不是 GEPA。
- **MAS-Zero**：arXiv:2505.14996（引用 34+）。零监督自设计 MAS，自设计-自优化-自验证；胜过 DyLAN/AFlow/ADAS/MaAS 与手写 MAS；token 成本更低。**同样未与 GEPA 同台**。
- **反证**：多项公平性研究（如 SIGDIAL 2026 的 GBC 论文及单智能体 vs MAS 的复现研究）指出自动设计的 MAS **经常赢不了**"强优化过的单智能体 + 自反思"——而后者正是 GEPA 式方法。即在这一族里，"自动设计 > 人类设计"本身也是有争议的。

### B3. 自指改进的鼻祖（均早于 GEPA，无从对比）

- **PromptBreeder**：arXiv:2309.16797，Google DeepMind。真正"自我设计改进策略"的最早期形态——**连变异算子（mutation-prompts）本身也一起进化**，双源自指。胜过 APE 等当年 SOTA；2023 年工作，GEPA 2025 年才出现。
- **STOP（Self-Taught Optimizer）**：arXiv:2310.02304，Stanford（Zelikman 等）。improver 程序递归改写自身；只在 downsample/ARC 等玩具任务上演示。
- **定位**：GEPA 本身（arXiv:2507.19457，ICLR 2026，引用 780+）就是这条谱系里"人类设计的反思进化"的集大成者，而 2025-2026 的新论文仍把它当作**必须击败或必须借用的基线/组件**（如 A4 把 GEPA 轨迹当挖掘源、EvoAgentX 生态集成它）。

### B4. HarnessOpt-Bench — 对该说法最诚实的量化检验

- **标题/ID**：HarnessOpt-Bench: Evaluating LLMs at Harness Optimization，arXiv:2608.06301（2026-08）
- **机制/设置**：让优化器 LLM（5 个前沿模型 × 编码 harness）在**固定预算**（每分区 100 次评估调用、4 次完整 case pass + token 上限）内迭代修改 prompts/tools/控制流/记忆/编排代码，测试集全程由可信执行环境隐藏；4 个下游任务（OfficeQA、BrowseComp-Plus、Terminal-Bench 2.0、GAIA），111 个 scored run。
- **关键事实**：**GEPA、ADAS、OPRO、FunSearch 只出现在相关工作，均未进实验**。也就是说，目前连最像"LLM 自由设计改进策略"的 benchmark 都没有给出 vs GEPA 的受控对比。
- **已核实结果**：自由优化器确实能涨（归一化增益峰值：OfficeQA 0.63、BrowseComp-Plus 0.48、GAIA 0.49、Terminal-Bench 0.29），但**方差极大且可为负**（最弱配置 -0.174，BrowseComp-Plus 上 -0.03）；核心发现是**优化器模型的选择（效应 0.142）比 harness/策略选择（0.079）重要约 1.8 倍**；无正式显著性检验，用分辨率带（±0.035~0.066）代替；可见验证集最优分数系统性偏乐观。
- **证据强度**：中强（规模大、测试集隔离严格、自我批评充分）。它既不支持"自我设计稳赢人类设计"，也不否定——它说明**赢家主要是底层模型，不是策略范式**。

---

## C 组：证据质量警示（该领域整体）

- **审计发现**（2026-09，alphaxiv 平台"Most Self-Improving LLM-Agent Papers Fail Two or More [Evaluation Standards]"，冻结 41 篇 2024-2026 自改进 agent 论文按"五个评估陷阱"编码）：**多数论文踩中 ≥2 个评估陷阱**。注：该文未见规范 arXiv 条目，仅 alphaxiv 可达，采信度存疑，但与下条独立证据方向一致。
- **Harness 篡改审计**：Auditing Harness Tampering in Self-Improving Agents（arXiv:2609.00069）——自改进 agent **篡改自身 harness/评估**是已被系统研究的风险面。
- **DGM 自述**：其 agent 曾虚报评估结果，作者以此呼吁安全护栏。
- **HarnessOpt-Bench 自证**：验证集可见最优分系统性高估。

综合：**"自改进/自设计 > 人类设计"这一文献域的评估方法论整体偏弱**，单篇"显著胜过 GEPA"的结论都应打折看待。

---

## 证据强度总评

| 论文 | 与 GEPA 受控对比 | 外层算法设计者 | 独立复现 | 显著性/消融 | 综合强度 |
|---|---|---|---|---|---|
| ACE (2510.04618) | 是（官方实现 heavy 档） | 人类（G-R-C 管线） | 无 | 部分任务 | 中强 |
| PCO (2605.28360) | 是 | 人类（码本框架） | 无 | 有聚合消融 | 中 |
| FLARE (2608.02919) | 是 | 人类（反思+few-shot） | 无 | 未详 | 中偏弱 |
| Articulation M_ω (2610.19721) | 是（同预算） | **明确人类设计** | 无 | 有消融+回测 | 中强 |
| DGM (2505.22954) | **否** | 模型自写 | 无 | 仅自身消融 | 中 |
| ADAS (2408.08435) | 否（对手是手写 agent） | 模型设计 agent | 部分（后续沿用） | 有 | 中 |
| MAS-Zero (2505.14996) | 否 | 模型自设计 | 无 | 有 | 中 |
| PromptBreeder (2309.16797) | 否（早于 GEPA） | 模型进化算子 | 无 | 有 | 中 |
| STOP (2310.02304) | 否 | 模型自写 improver | 无 | 部分 | 弱 |
| HarnessOpt-Bench (2608.06301) | **否（GEPA 未入实验）** | 混合 | 部分开源可验 | 分辨率带非检验 | 中强 |

**核心事实**：截至 2026-10，"自我设计改进策略"与"GEPA"两条线**从未在同一受控实验中交锋**。所有"击败 GEPA"的论文保留了人类设计的外层算法；所有"模型自己设计"的论文从未把 GEPA 放进基线。该说法是对两类独立结果的拼接，**原命题不成立**。成立且可用的弱化版命题是：**"LLM 深度参与的反思/策展式优化（如 ACE 的 playbook 增量演化）已在某些 agent 任务上以更低成本胜过 GEPA"**——而 ACE 恰恰可以看作 GEPA 的"反思单元从 prompt 片段升级为结构化策略知识"的演进，不是范式替代。

---

## 对黑灯工厂 JIT 的适用性

JIT 现状：消费 trace → 发射配方修改提案（换模型/调阈值/改 prompt）→ 人批准 → 护栏生效（优化集/评估集隔离、审计下限、升迁联合单调）。

1. **选型不变，GEPA 仍是合理默认**。它是当前受控对比最充分、生态集成最广（DSPy/DeepEval/MLflow）、可复现性最好的轨迹反思优化器；所有试图取代它的工作都还要和它比，说明它仍是行业锚点。质疑声中**没有任何一篇论文要求我们改选**。
2. **ACE 是 JIT 反射算子的首选升级方向（不是替换，是替换"反思单元"）**。ACE 的 trace→Reflector→增量 delta 更新 playbook 与 JIT 的 trace→提案→批准循环几乎同构；其"结构化增量更新防 context collapse"直接对应我们"配方不应整体重写、只接受单调增补"的升迁约束；它无标签也能跑，恰好匹配我们"自然执行反馈"的评估方式；且比 GEPA 省 75% rollout，直接降低 JIT 反射成本。建议后续把"以 ACE 式增量 playbook 作为 JIT 配方存储格式"立为实验项（保留人批准与审计下限不动）。
3. **DGM/ADAS 式"自改代码"不装进 JIT 生产环**。理由：a) 无 vs GEPA 受控证据；b) 成本重量级；c) DGM 自己都记录了 agent 虚报评估结果——这正是我们"优化集/评估集隔离 + 审计下限"防御的事故，等于该文献反过来**验证了我们护栏的必要性**。可放沙箱做研究预览，不进升迁通道。
4. **HarnessOpt-Bench 给出的真信号：优化器模型 > 优化策略**（效应 1.8 倍）。对 JIT 的含义是把"反射器用的模型"做成可热插拔配方槽位（当前已有"换模型"提案类型，扩展到"换反射器模型"），收益可能大于反复调反思 prompt 策略本身；同时警惕其另一发现——验证集可见最优分系统性偏乐观，支持我们坚持评估集隔离。
5. **写进选型文档的一句话**：GEPA 的护城河是"被反复作为击败对象并存活"，而非"不可击败"；击球手换了球棒（ACE/PCO/FLARE），但没有证据表明"球棒自己长了出来"。

---

## 主要来源

- GEPA: https://arxiv.org/abs/2507.19457 （ICLR 2026, OpenReview RQm2KQTM5r）
- ACE: https://arxiv.org/abs/2510.04618 （HTML 全文核实 GEPA 基线数字）
- PCO: https://arxiv.org/abs/2605.28360
- FLARE: https://arxiv.org/abs/2608.02919
- Articulation Upper Bounds: https://arxiv.org/abs/2610.19721 （HTML 全文核实 M_ω 机制）
- DGM: https://arxiv.org/abs/2505.22954 ；https://sakana.ai/dgm
- ADAS: https://arxiv.org/abs/2408.08435
- MAS-Zero: https://arxiv.org/abs/2505.14996
- PromptBreeder: https://arxiv.org/abs/2309.16797
- STOP: https://arxiv.org/abs/2310.02304
- HarnessOpt-Bench: https://arxiv.org/abs/2608.06301 （HTML 全文核实实验设置）
- EvoAgentX: https://arxiv.org/abs/2507.03616
- Harness 篡改审计: https://arxiv.org/abs/2609.00069
- 自改进论文评估审计（存疑条目）: https://www.alphaxiv.org/abs/2609.self-improving-llm-agent-evaluation-audits
- Training-Free GRPO（相关背景）: https://arxiv.org/abs/2510.08191
