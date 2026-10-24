# 外部项目研究：PenguinHarness

- **研究对象**：PenguinHarness（变体：PenguinHarness / penguin-harness / penguin harness / penguin_harness 等）
- **结论**：**部分引入**——抄它的评测方法论与基准生命周期设计，不引入其运行时，不整体替换任何子系统。
- **调研日期**：2026-10-19
- **方法说明**：`git clone` 直连 github.com 在本环境被网络阻断（`Failed to connect to github.com port 443`），改经 `raw.githubusercontent.com` / jsDelivr CDN / GitHub API / WebFetch 取得源码树与文件后做代码级+文档级评估。**未运行其任何代码或测试**（环境无 Node 24 与模型密钥，且 ask 允许跑不起来时做代码级+文档级评估）。

---

## 一、项目是什么（身份事实）

**PenguinHarness** = `Prism-Shadow/penguin-harness`，GitHub 2830 stars / 301 forks / 818 commits，Apache-2.0，TypeScript monorepo（pnpm，Node ≥ 24），官网 penguin.ooo。定位一句话：**"Unified and Stable RSI Framework — Automatically improve model × agent harness"**（README.md:5-7）：模型固定不动，进化的是 harness——prompts、Skills、tools、hooks。形态是桌面 App + Web App + CLI + SDK 四件一套，数据全落 `~/.penguin/data` 文件层。

它不是 LLM **安全**评测数据集（ask 中提到的 Penguins 安全数据集方向）。我搜过的变体里没有任何仓库对应该数据集：搜索结果共 12 项（`penguin harness` 查询），主体是 Prism-Shadow 组织生态（penguin-harness 主仓、-community、-benchmark、-plugins、-leaderboard）与衍生（swsgbl/penguin-tui 是 TUI 衍生、Kevinlidk/penguinh-docker 是部署方案、jmicko/penguin_harness 是 0 star 空 Rust 仓、rank-Yu/line-recovery-starter 是"产线质检 agent"起步料）。**Penguins 安全数据集方向：未找到，本报告不涉及。**

它与我们 ask 的相关点在另一半：**它是 LLM/agent 评测 harness**——内置"Evaluation Center"（评估中心）：每个 Project 带 7 个基准（Sec A–E 复刻自 rag-bench-essential、DeepSWE、AutomationBench、Terminal-Bench-Science、Terminal-Bench，加 GDPevo Train/Test，全部以 Harbor 框架在 Docker 里跑，README.md:68），5 个 RSI 算法插件（default/OPRO/APE/ACE/AWM，README.md:60-66），agent 状态版本化快照，每个分数可回溯到产生它的 session。

核心引擎是 `packages/core` 的 `context_engine`（ReAct 循环）+ OmniMessage 协议 + 三接口边界（Human/LLM/Environment），"agent 的整个行为就是可编辑文件"（architecture.en.md:105-115）。

---

## 二、效果证据（成熟度）

| 维度 | 事实 | 证据 |
|---|---|---|
| 流行度 | 2830 stars / 301 forks；npm `@prismshadow/penguin-core` 近月 1069 次下载、`penguin-cli` 767 次 | GitHub API repo 元数据；`api.npmjs.org/downloads/point/last-month`（2026-09-17～10-16） |
| 发版节奏 | 2026-07-19 建仓至今约 3 个月 818 commits，0.1.0→0.2.16 共 16+ 个 release；0.2.6/0.2.7/0.2.8 三天连发，0.2.15/0.2.16 一天连发 | releases 页（v0.2.16 于 10-14，v0.2.15 于 10-13）；npm registry versions |
| 团队 | 组织仓（Prism-Shadow）；README 署名 9 位维护者、两家组织（PrismShadow AI、Qinghe Dynamic），含 Yaowei Zheng（LlamaFactory 作者） | README.md:311-325 |
| License | Apache-2.0（仓库根 LICENSE） | GitHub API license 字段 |
| 能力演示 | ①自进化 demo：决策 agent 同一模型下 84→100 分（README.md:74，附视频）；②产品级基准：数据分析 15 任务 PenguinHarness+DeepSeek V4 Pro 66.67% / $0.55 vs Claude Code+Opus 4.8 53.33% / $38.48（70 倍价差）、Codex 53.33% / $19.41；编程 40 任务×2 run：71.25% / $3.81 vs Claude Code 86.25% / $146.97、Codex 71.25% / $220.08 | packages/landing/src/lib/benchmark-data.ts:30-84；倍数由代码从数据算出（:106-113，"headline claim 由数据构建而非手打，数字刷新时不会漂移"） |
| 方法严谨度 | 基准复刻全部钉 40 位 commit、有 SOURCE.md/selection.json/SELECTION.md 记录选型与校准；重试规则明确"agent 没跑过才重试，Docker 网络失败不算分数" | penguin-harness-benchmark README 规则 5-6 |
| 质量门 | CI 三平台、typecheck+test+coverage（不设阈值）、playwright e2e、changelog 双语强制、插件版本未升 CI 即拒 | .github/CONTRIBUTING.md:148-172 |

**诚实的保留**：①年轻——3 个月，无独立第三方基准验证，benchmark 对比是"产品级对比"（各自带惯用模型，模型列是结果不是常量，benchmark-data.ts:4-9 自述），不是控制变量的 harness 单测；②npm 下载量温和（月千级），实际部署量未知；③单一厂商生态。结论：**作为设计参照物证据充分；作为生产依赖证据不足**。

---

## 三、四问评估（替我们省了什么 / 效果证据 / 引入成本 / 对接与退出）

**Q1 替我们省了什么？** 若照抄其评测方法论，可省掉我们从零推演的几件事：基准的三态生命周期（draft→published/failed + 85 分发布闸 + 校准失败条件，self-improvement.en.md:184-194, :83）、statement/rubric 分离的信息屏障与泄漏检查（:32-46）、scoreboard 记录 schema（运行时标签 = agent×model×thinking_level，只有同标签才可比，:198-206）、候选改动的快照-回滚协议（版本只增不减、 rejected 版本号不复用，agent-optimization/SKILL.md:66-74）、四失败码分类（agent-evaluation/SKILL.md:146-151）。这是**设计期省钱**（数周量级），不是工程期省钱——我们要用 Rust 重写。

**Q2 效果证据？** 见上表。2830 stars/3 个月、16+ 发版、Apache-2.0、可复现的基准数字与自进化 demo，方法论文档（docs/self-improvement）质量高于多数开源项目。但缺第三方审计与大规模部署证据。

**Q3 引入成本？** 作为**参考**：零成本（本文档即产物）。作为**运行时依赖**：不可行——它是一个完整应用（Hono+SQLite server、React SPA、Electron、MMSP 模型网关、自有数据根 `~/.penguin/data`），不是可嵌入的库；且 TypeScript/Node 24 与我们 Rust 内核不同语言。作为**旁路评测服务**（L2 适配器外挂）：技术上可跑 Docker 起服务再把分数搬成我们的 Evaluation 工件，但①多养一个 Node 服务，②它的信息屏障自述"由 Skill 指令和可审计 Trace 强制执行，**不是沙箱**"（self-improvement.en.md:46 WARNING）——对我们安全姿态不够，③退出时我们的工件仍是事实源，但它一改协议我们就得改翻译层。

**Q4 对接四层中哪层 + 退出成本？** 抄设计落在两处：**L3 配方层**（基准生命周期参数、校准与发布策略、抽样率作为 CUE 数据）与 **L1 机制实现参考**（CSP-1 状态机、失败指纹分类、Evaluation 三态语义获得实证参照）。退出成本≈0（不形成依赖）。若走旁路服务则退出成本中等（停服务+翻译层作废，自有工件无损）。

---

## 四、与我们底座的逐项对照

### 4.1 统一 harness 内核（宪法 4）——同构，且他们走到了"agent=数据文件"

他们的 `context_engine` + 四元组等价物：模型端点（`(provider, model_id)` 对）、上下文（AGENTS.md + Skills）、工具集（7 个内置工具 + broker 外工具）、策略参数（system_config.yaml 的 limits/thinking_level）——"An agent's entire behavior is editable files"（architecture.en.md:110-113）。RSI 进化只改这些文件，`version` 字段随之递增（self-improvement.en.md:216）。与我们的"统一 harness 内核 + 四元组配置"是同一思想；差别在我们的内核还承载凭证/沙箱/副作用网关等 13 抽象，他们的 harness 外壳更薄。**可抄**：agent 状态即文件、版本随每次被接受的优化递增、快照 `snapshots/v<n>.tar.gz` 排除 `.vault.toml`（snapshot-service.ts:1-11, :82-85）——密钥永不进快照这条纪律直接适用于我们的 Artifact/快照设计。

### 4.2 Evaluation 三态（通过/不通过/需人工）——他们没有第三态，但有一条同精神的铁律

他们的评测结果是**两态 + 0-100 分**：`status: ok`（含 0 分——答错也是"被评分的行为"）或 `status: failed`（四种 failure_code：invalid_request / benchmark_invalid / version_changed / evaluation_failed，agent-evaluation/SKILL.md:42, :146-151）。**没有"需人工"第三态**。但两条纪律与我们的第三态同构：①"启动器/Trace 绑定/评分器故障不是被评分行为"（:101）——基础设施失败绝不记 0 分，Harbor 重试规则同样"网络失败不是分数"（benchmark 仓 README 规则 5-6）；②成本只信 Trace 累计值，取不到就 `null`，"缺成本数据不得使分数失效"（:103）。这正是我们第三态要防的"机器判不了/ harness 故障时拿产品出气"。**可抄**：失败码分类法 + "harness 失败 ≠ 产品失败"的记账隔离，作为我们 Evaluation 第三态触发条件的实证细化。

### 4.3 eval-as-产线——他们就是活样板，且纪律极硬

"Self-improvement 循环**不自带运行时**：评估是普通 Session，优化是普通文件编辑，每个结果都是 Project 里的文件"（self-improvement.en.md:5）。评估即产线：Session 是工作单元、scoreboard.yaml 是账本、基准是带 manifest 的版本化产品（`benchmark_config.toml` + CASE 目录 + scoreboard，:136-147）、Harbor Docker trial 是并发上限 4 的工位单元。角色分工（Builder/Evaluator/Optimizer/Target）与信息屏障表（:36-41）：Target 永不见 rubric（rubric 目录根本不进它的 workspace，:61）；Optimizer 只见公开 statement + scoreboard + 关联 Trace，**私评信息一旦进 Optimizer 上下文即回滚候选并按污染停机**（agent-optimization/SKILL.md:43）。服务端只校验形状、永不重算均分（benchmark-service.ts:726-739；agent-optimization/SKILL.md:132 "stored values are authoritative"）。**可抄**：这套"评测即产线 + 信息屏障 + 污染即停 + 账本只追加"整体可以作为我们 eval-as-产线的参照实现；CSP-1 金标的"金标盲评、被评方不可见"由此获得实证设计。

### 4.4 CSP-1 抽样与金标注入——部分同构，但没有 CSP 状态机

他们的多 run 设计（每 case `runs` 次，"用重复 run 区分稳定行为与波动"，agent-optimization/SKILL.md:54）是朴素的方差控制；发布闸固定 85、验收线"均分严格高于 Reference"（:21）是点值比较。**没有**我们的 CSP-1（全检→抽检→缺陷回全检的可配拓扑、抽检下限>零）。金标注入的对应物是 Formal Baseline + 私 rubric（85 分以下也发布，:83）与泄漏检查（:43），位置不同——他们是"每个基准自带私标"，我们是"往任何工作队列按比例埋已知答案考题"。**可抄**：rubric/statement 物理分离 + 埋题前的泄漏检查流程；CSP-1 状态机本身仍用我们自己的（他们的证据不足以替换）。

### 4.5 升迁梯 / JIT 护栏 / 失败指纹——前两项高度同构

accept-only-if-strictly-higher + 不合格即回滚 + 快照先行 + 版本不复用（agent-optimization/SKILL.md:21, :66-74）= 我们升迁梯的"看证据、败自动降"；ACE 的 held-out 测试基准"Reflector 和 Curator 不得接触"（ace SKILL.md:17）与"训练执行永不进 scoreboard"（:93）= 我们 JIT 护栏的"优化集/评估集隔离 + 审计下限"。失败指纹：他们只有引擎级四值 stop_reason（completed/retryable/fatal/aborted，5 次空重试上限，architecture.en.md:168-175），没有我们的失败指纹库+连续同错即止损。**可抄**：优化/评估集隔离的工程做法与"训练轨迹不得冒充矩阵成绩"的记账规则。

### 4.6 我们没有而他们有的（不必抄，列出以示对照）

沙箱插件四种后端（bwrap/dsh/seatbelt/wsl）+ Harbor Docker 评测、OmniMessage/AMSP 流式协议带 UI 部件（A2UI）、HMR 热更新（park→boot→swap）、remote machines over ssh。这些是他们产品形态的一部分，与我们 L1 无对应需求。

---

## 五、结论与建议

**裁决：部分引入。**

**抄（进我们的 L3 配方 + L1 机制设计文档，作为实证参照）：**
1. **基准三态生命周期**：draft/published/failed + 校准（Pilot）+ Formal Baseline + "低于 85 也发布"的发布闸——直接细化我们的 Evaluation 三态与金标冻结流程（self-improvement.en.md:184-194, :83）。
2. **信息屏障与污染停机**：statement/rubric 物理分离、分发前泄漏检查、私评信息进优化器上下文即回滚停机——CSP-1 金标盲评的工程纪律（:36-46；agent-evaluation/SKILL.md:61；agent-optimization/SKILL.md:43）。
3. **评测协议细节**：版本绑定（expected_version 不符即 version_changed）、Trace 绑定（唯一 root Trace 匹配 workspace/agent/provider/model）、四失败码、"基础设施失败不算 0 分"、成本只信 Trace——我们 Evaluation 第三态触发条件与失败指纹的细化输入（agent-evaluation/SKILL.md:59, :95, :101-103, :146-151）。
4. **账本纪律**：scoreboard 只追加、服务端只校验不重算、同标签才可比（agent×model×thinking_level）、被拒候选永不入账本——我们 Delivery/决策工件的记账规则参照（benchmark-service.ts:726-739；self-improvement.en.md:198-206）。
5. **快照纪律**：改前快照、版本只增、rejected 版本号不复用、密钥永不进快照（snapshot-service.ts:1-11；agent-optimization/SKILL.md:66-74）。

**不抄 / 不引入：**
- **不引入运行时、不整体替换任何子系统**：TS/Node 应用而非可嵌入库；其 harness 外壳比我们 L1 薄 8 个抽象；信息屏障自述非沙箱强制，安全姿态不达标。
- **CSP-1 状态机、需人工第三态、升迁梯的完整形态仍用我们自己的**——他们要么没有，要么只有点值比较，证据不足以替换。
- 其基准数据（Sec A–E、GDPevo）可作我们金标库的候选素材调研对象（Apache-2.0 + 钉 commit 复刻方法清晰），但那是数据选型另一题，本报告不背书其内容质量。

**风险**：项目仅 3 个月大、单厂商、无第三方基准审计；其"1/70 成本"是产品级对比非控制变量实验。抄设计时把方法论当假说，用我们自己的 CSP-1 与三态落地验证，而非照单全收。
