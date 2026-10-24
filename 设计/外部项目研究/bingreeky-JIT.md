# bingreeky/JIT（JIT-Agent）外部选型评审

**评审日期**：2026-10-19
**评审对象**：`https://github.com/bingreeky/JIT`（描述 "JIT-Agent"）+ HF `JIT-Agent/jit-27b`
**结论**：**部分引入** —— 只抄两条设计纪律，零运行时依赖

---

## 0. 名录澄清（防幻觉的关键）

| ask 给的变体 | 实测结果 | 命令 |
|---|---|---|
| `binggreeky/JIT`、`binggreeky` 用户页 | **不存在**（404 / 200 但非该用户） | `curl 'https://api.github.com/users/binggreeky/repos'` → `{"message":"Not Found","status":"404"}` |
| `bingreeky/JIT` | **存在**，559 stars | `curl 'https://api.github.com/search/repositories?q=JIT-Agent'` → 第一条命中 |
| `binggreeky` 用户页 | **存在**，15 个 repo | `curl 'https://api.github.com/users/bingreeky/repos'` → 200 |
| HF `JIT-Agent` | **存在** | `curl 'https://hf-mirror.com/api/models?search=JIT-Agent'` |

**正确账号是 `binggreeky`（e-e-k-y），不是 `binggreeky`。** ask 里的拼写是对的仓库不存在；按拼写直接采信会引入一个不存在的项目。

同账号的相关仓库（属该作者的其他研究线，非本项目）：`AgenTracer`(109★, 失败归因)、`LOPD`(62★)、`MemGen`(427★)、`MaAS`(287★)、`MemEvolve`(281★)、`GMemory`(283★)。

### 取证方式的偏差（如实记录）
- `git clone` **失败**：`fatal: 无法访问 'https://github.com/bingreeky/JIT.git/'：Failed to connect to github.com port 443`。本机对 git 协议端口不通，但 HTTP(S) API 通。
- 改用 `curl codeload.github.com/.../tar.gz/refs/heads/main` 下载源码包（`http=200 size=756725` 首次为截断流，重试三次后完整落地 19.4MB）。
- `/tmp` 磁盘配额已满（`tar: 无法 write: 超出磁盘配额`），故解包到 `~/workspace/ext-research/` 而非 ask 指定的 `/tmp/ext-research/`。
- `arxiv.org` 与 `huggingface.co` 在本机**不可达**（均 `http=000`）；HF 数据经 `hf-mirror.com` 镜像取得，arXiv 论文正文**未读到**。
- GitHub API 匿名配额（60/h）在取证中途耗尽，contributors/commit 明细**未能取到**。

---

## 1. 它是什么（是什么 / JIT 指什么）

**JIT = Just-in-Time（harness evolution），与我们的 JIT 毫无关系——是同名不同物。**

README.md:24-27 的定义：*"JIT-Agent is a compact meta-agent that writes your agent harness on the fly."* 副标题：*Scaling Harness Intelligence via Just-in-Time Harness Evolution*。作者主张：*"Building the scaffold turns out to be a trainable, transferable axis of agent intelligence — orthogonal to scaling the base model."*

机制链条：

1. 给元 agent 一个任务描述、工具注册表、共享运行时协议、以及**若干检索到的先验 harness**；
2. 元 agent **吐出可执行的、任务专属的 Python harness**（"Model-as-a-Harness"），去包裹任意现成 agentic LLM；
3. harness 固定拆成**四个模块** —— `memory` / `planning` / `action` / `tool_policy`，加一个 `prompt.yaml`，共 5 个文件（`jit/README.md` 表格，HF 模型卡同构）；
4. 输出用标签块承载：`<<<PYTHON_MEMORY>>>…<<<END_PYTHON_MEMORY>>>` 等（`jit_meta_agent.py` 与 HF 模型卡逐字一致）；
5. 每个 case 采样 **N=3 个候选**（`--rollouts 3`，温度 **1.0**），从 N 个里挑 1 个真正执行。

三段式流水线（`scripts/run_jit.py`）：

| 阶段 | 代码位置 | 做了什么 |
|---|---|---|
| A 生成 | `run_jit.py:257-269` | `rollouts=3`、`generate_only=True`、**`max_repairs=0`** |
| B 择优 | `run_jit.py:273-300` | judge 或 logprob 排序选 1 |
| C 执行 | `run_jit.py:302-317` | `rollouts=1`、执行选中的那个并计分 |

### 与我们 JIT 编译器、四级漏斗的关系：**零对应**

| 维度 | 我们的 JIT 编译器（机制 #13） | bingreeky/JIT |
|---|---|---|
| 优化对象 | **配方参数**（L3，类型化受限 DSL） | **可执行 Python agent 代码** |
| 产出 | 配方修改**提案**，人批准生效 | 直接可执行的 harness |
| 是否干预执行 | **永不**（宪法 #9 显式） | 无此概念——它本身就是执行骨架 |
| 护栏 | 三件套：审计下限 / 优化集与评估集隔离 / 升迁须联合单调 | 见 §3，仅两条泄漏防护，且**无质量下限** |
| 消费的数据 | 产线 **trace** + 评估数据 | benchmark 任务文本（**无 trace 概念**） |
| 触发 | 持续运行的生产反馈 | 每 case 一次性生成 |

四级漏斗（产品设计_拍板版.md:63）的四个台阶——参数化 / 升格机制 / 降配方 / 写手册——在对方项目里**一个都没有对应物**。它不是我们的需求进入工序的候选实现，它是一个研究原型：一个把"agent scaffold 本身"当作可训练轴的学术论点。

> 结论：**同名导致的误判风险**。若日后有人以"JIT 已有成熟开源实现"为由提议替换或对标我们的机制 #13，须以本节为驳斥依据。

---

## 2. 效果证据（本次评审的核心）

### 2.1 模型卡：一个数字都没有

`https://hf-mirror.com/JIT-Agent/jit-27b/raw/main/README.md` 通篇只有：checkpoint 概览、参数表、推荐用法、Intended Use、License。**没有 benchmark 表、没有分数、没有消融**。README 主仓唯一的成绩载体是一张**图片**（`assets/leaderboard.png`）。

### 2.2 唯一可读的成绩（我把图下载下来逐格读了）

`assets/leaderboard.png`（1800×894，500KB），四个基准各一栏。JIT 变体一律是该基准的**最高柱**。摘录增益（同模型内 JIT vs 原生）：

| 基准 | 骨干模型 | JIT | 原生 | Δ |
|---|---|---|---|---|
| **DeepPlanning-Shopping** | DeepSeek V4-Flash | 83.9 | 59.1 | **+24.8** |
| **DeepSearchQA** | Kimi K2.7 Code | 87.8 | 72.4 | **+15.4** |
| **DeepSearchQA** | GPT-5.6 | 88.0 | 76.0 | +12.0 |
| **DeepSearchQA** | Gemini 3.5 Flash | 85.1 | 75.8 | +9.3 |
| AgentIF | GPT-5.6 | 68.0 | 60.1 | +7.9 |
| AgentIF | GLM-5.2 | 69.9 | 63.0 | +6.9 |
| OfficeBench | GLM-5.2 | 68.4 | 63.0 | +5.4 |
| AgentIF | DeepSeek V4-Pro | 63.8 | 58.4 | +5.4 |
| DeepPlanning-Shopping | DeepSeek V4-Pro | 78.2 | 72.8 | +5.4 |
| OfficeBench | Kimi K2.7 Code | 65.8 | 61.0 | +4.8 |
| DeepSearchQA | GLM-5.2 | 93.9 | 89.2 | +4.7 |
| OfficeBench | GPT-5.6 | 65.3 | 60.6 | +4.7 |
| DeepSearchQA | DeepSeek V4-Pro | 78.0 | 72.4 | +5.6 |
| AgentIF | DeepSeek V4-Flash | 61.0 | 56.5 | +4.5 |
| OfficeBench | Gemini 3.5 Flash | 63.4 | 60.6 | +2.8 |
| **DeepPlanning-Shopping** | GLM-5.2 | 83.4 | 82.8 | **+0.6** |
| **OfficeBench** | Qwen3.7 Plus | 61.0 | 60.6 | **+0.4** |

**增益是真的，但有两个必须说清的口子：**

1. **零成本数据。** 全图没有 token 列、没有成本列、没有延迟列。而 JIT 路径的成本是实打实的：跑 3 次 27B 元模型生成（`--rollouts 3 @ T=1.0`），外加择优的一次 judge/logprob 调用。`+0.4` / `+0.6` 这两行在单次评测的噪声范围内，而它们付出的却是 3 倍生成开销 + 一次 54.7GB 模型的驻留。**这张图只证明了"上界"，没证明"性价比"。**
2. **单次实验，无置信区间。** `deepsearchqa` 全量 900 case（`benchmark/registry.py`），其余 100 量级；图中无一给出 seed 数或方差。

### 2.3 成熟度

| 维度 | 实测 |
|---|---|
| stars / forks / open issues | 559 / 61 / 3（`curl api.github.com/repos/bingreeky/JIT`） |
| 创建 / 最后推送 | 2026-08-17 / **2026-08-27** → 至评审日**已停更 23 天** |
| 代码量 | 146 个 .py，共 **36,837 行**（jit 2,647 / scripts 8,024 / harness_factory 11,171 / benchmark 14,995） |
| 语法自检 | `python3 -c "compile(...)"` 遍历全部 146 文件 → **0 语法错误**（这是我实跑的唯一检查） |
| 种子 harness | 11 个手写架构（plan_and_execute / flash_searcher / agentfold / resum / hiagent / memobrain / deepagent / gam / roma / aggagent / oagent） |
| 基准 | 7 个，评估器从上游 vendor 而来 |
| 依赖 | `requirements.txt` 75 行：faiss / sentence-transformers / transformers / docx / pptx / pymupdf / pytesseract… |
| License | **代码 MIT**（`LICENSE`；GitHub API 报 `NOASSERTION` 是因为文件末尾附了一段 NOTE） |
| **实际运行** | **未跑**。依赖未装（本机 `import yaml` 即失败），需 conda env + torch + 多个 API key + 约 1GB 数据集 + 54.7GB 模型 TP=4。按 ask「跑不起来就做代码级+文档级评估」处理 |
| contributors | **未取到**（API 配额耗尽；贡献者页抓取失败）。代码内无 author/copyright 头 |
| arXiv 2608.25593 | **未读**（arxiv.org 本机不可达，`http=000`） |

**成熟度定性**：一次性研究发布（single research drop），不是被生产验证过的工程项目。

---

## 3. 引入成本与四层定位

### 3.1 它省我们什么：几乎不省

对照我们的 13 抽象 + 13 机制，逐条查：

| 我们需要 | 它有吗 |
|---|---|
| Trace 正式接口（Merkle+签名，第一天版本化） | **无**。轨迹只作局部 dict 传给 repair prompt |
| Credential（biscuit 衰减 / 短期签发 / 派生只收紧） | **无**。全仓库无凭证体系，只有 `.env` |
| 副作用网关（幂等键 / fencing / 对账） | **无**。`execute_code` 直接落盘，无幂等无撤回 |
| 预算硬闸 | 仅 `model_call_budget = 3*max_steps`（`meta_agent.py:1239`），单次运行的粗钳，非可声明计量维度 |
| Evaluation 三态（通过/不通过/**需人工**） | **两态**。`_validate_harness` 只返回 `passed: bool`（`meta_agent.py:1283`），**无第三态、无人工工位** |
| WorkOrder / Human Station / Delivery / Channel / Resident | **全无** |
| 投放闸 / CONWIP / CSP / 升迁梯 / 注入器 / 止损指纹 | **全无** |
| 调度 / 日历 / Meter | **全无** |
| JIT 护栏 | 部分（见 §4） |

它省不了我们任何一件已有机制。它唯一与我们的交集是**一个研究问题**："scaffold 本身可否被当作可训练能力轴"。

### 3.2 对接四层 + 退出成本

- **语言**：Python 3.11 + conda。我们基线是 **Rust 内核**（D5 拍板），引入它等于在 L1 旁边多出一整棵 Python 树。
- **最重的一条**：光为了**生成**一个 harness，就要驻留 54.7 GB BF16 的 27B 模型、`TP=4` 起（`serve_meta_model.sh`）。对一个"内核机制"来说这是数量级的资源错配。
- **若强行对接到 L2 适配器**：它是一个 benchmark 运行器（deep research / office / travel），**不是通用 agent 工厂底座**。对接它等于把整个 L1-L3 换成它的评测循环，与三无关全部冲突。
- **退出成本**：若只是抄设计纪律（§4 两条），退出成本 = **0**（不改代码）。若真引入运行时，退出成本高（模型托管、conda 双环境、两个沙箱 Python、Python↔Rust 跨语言调用）。

---

## 4. 逐项裁决

### ✅ 值得抄的（两条，均为设计纪律，零依赖）

**① 泄漏防护的精确表述 —— 直接补我们护栏 #2 的一个洞**

- `jit/selector.py:1-5`（docstring）：*"no benchmark score is available at selection time, and using one would be leakage."*
- `scripts/run_jit.py:311-313`：注释写明 *"Repair a crash, but never 'repair' a harness that merely scored low: that would be optimising against the benchmark."*，并落成 `repair_only_on_error=True`。

这条比我们的措辞更锋利。我们的护栏 #2 写的是"优化集与评估集隔离"，**但没有堵住 JIT 自身修复循环拿评测分当反馈这个口子**——对方把这个具体反模式命名并用一行开关封死了。建议把 `repair_only_on_error`（或其等价语义）直接写进我们机制 #13 的接口契约。

**② best-of-N 前的"免费静态闸"**

`selector.py:73-77`：先按 `n_sub == 5`（五个标签块是否齐全）过一道零成本静态门，再在存活集合里 argmax。对应我们机制 #13 尚缺的**提案合法性预筛**（提案进人工队列前先过配方 schema 的静态校验，失败的直接不进队列，省掉人的注意力）。这条与我们的金标注入器/CSP 配合是干净的。

### ❌ 必须拒绝的（fail-open 三连 + 无复现 + 声明不实）

**① fail-open 与我们的"宁停勿错放"正面冲突**

- `jit/meta_agent.py:1078-1087`：评审专家调用异常 → **计为 pass**（注释自称 *"fail-open"*）。
- `scripts/tools/code_tools.py:150-155`：配置的沙箱解释器不存在 → **静默回退到 `sys.executable`**，也就是带 `.env` 凭证的父进程。
- `code_tools.py:90-96`：`_check_safety` 是一条**子串黑名单**（`DISALLOWED_COMMANDS` 逐条 `pattern.lower() in code_lower`），可被轻易绕过——不是沙箱，是字符串匹配。
- `code_tools.py:180`：`env = os.environ.copy()` —— 所谓沙箱**继承全部凭证**。

我们的宪法要求超时安全缺省是拒绝、副作用须走幂等网关、凭证不可被工具触达。这套东西一条都不满足。

**② 不可复现**

`jit_meta_agent.py:237-240`：`rng = random.Random(seed) if seed else random` —— **默认不设种子**，每个 case、每次 rollout 抽不同的参考 harness。全仓库 grep `random.seed` / `torch.manual_seed` / `np.random.seed` **无任何命中**（只有 `JIT_META_REF_SEED` 这个可选环境变量）。直接违反我们宪法 #7（版本贯穿、事故可按版本定位）与 #1。

**③ README 的"自改进 archive"在代码里不存在**

README.md:36 称 *"revises the harness and updates the archive: harnesses keep improving at test time while the generator itself stays frozen."*
全仓 grep `archive` 的命中只有：README.md:36 本行、`scripts/tools/mm_tools_utils.py` 的 ZIP 解包、`harness_factory/harnesses/oagent/action.py` 的专家产物归档、以及 benchmark 评估器里一个同名的 `.zip` 解析器。
**没有 archive、没有写回、没有闭环学习。** 参考材料来自 `harness_factory/harnesses/` 里 11 个**手写、静态**的种子。README 的这一句是本次评审里最需要警惕的一处：它描述的正是我们护栏三件套想防的东西（无人审批的自修改闭环），而它在对方的实现里并不存在——**不要因为这句话而把它当作"JIT 自改进"的现成实现**。

**④ 生成阶段没有质量下限**

`run_jit.py:265` 在 Phase A 显式设 `max_repairs=0`，注释 *"Generation never executes anything, so repairs are meaningless here."*
后果是：六个专家评审面板（`_review_harness_panel`）与 validate→repair 循环**在发布的 best-of-N 路径上完全不走**。JIT 路径只有"盲生成 3 个 → 挑 1 个 → 跑"。它对"生成质量"没有任何地板，只有"不许用分数选"的天花板。半边护栏。

---

## 5. 最终结论

**部分引入。**

- **引入范围**：仅机制 #13（JIT 编译器）规格文档里的**两条设计纪律**——`repair_only_on_error` 语义的泄漏封堵、以及 best-of-N 前的零成本静态合法性闸。**只改规格文档，不引入任何代码、不引入依赖、不进任何一层。**
- **明确不引入**：整个运行时。四层定位是"**不接 L1、不接 L2、不接 L3、不接 L4**"——它不是我们任何一层的能力承载者，理由见 §3.1（13 机制里 12 项它一项没有）与 §3.2（资源错配两个数量级）。
- **需要记录在案的负面结论**：**它不构成我们机制 #13 的现成实现**。任何人再以"JIT 有 559 星的开源实现"提出对标，应引用 §1 的同名不同物表与 §4③ 的声明不实。名字相同是最容易催生错误引入的巧合。
- **待补的取证缺口**（如需升级结论）：本机不可达 `arxiv.org` 与 `huggingface.co`，论文正文未读、贡献者数未取到、未实跑。若要复现其成绩需约 54.7GB 模型 + TP=4 + 多 API key，**不在本次评审的可行性范围内**。

**对接层**：无。**退出成本**：0。

---

*证据来源：`https://github.com/bingreeky/JIT`（tarball 源码包，146 文件全文阅读关键路径）、HF 镜像 `hf-mirror.com/JIT-Agent/jit-27b`、`assets/leaderboard.png` 图像直读、`产品设计_拍板版.md` §1-2/§三/§五。所有文件行号引用自 `~/workspace/ext-research/JIT-main/` 下的本次解包副本。*
