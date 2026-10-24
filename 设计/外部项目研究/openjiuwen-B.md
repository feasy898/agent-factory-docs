# openjiuwen 后半模块 · 外部选型评审（B 侧）

> 评审立场：默认拒绝。判据只有一条——**效果证据**。找不到就报未找到，绝不凭印象编造。
> 平行任务：另一代理（A 侧）独立研究同一项目的定位与**前半模块**，本报告不依赖其结论。
> 日期：2026-10-19

---

## 第一节 · 项目定位与模块划分（可复现的排序规则）

### 1.1 找到没有：找到了

GitHub 组织 **`openJiuwen-ai`**（`https://github.com/openJiuwen-ai`）。

定位怎么做的：变体逐个试。`curl 'https://api.github.com/search/repositories?q=jiuwen&sort=stars'` 返回 `total_count: 88`，首位命中 `openJiuwen-ai/jiuwenswarm`（7422★ / 1110 fork / Python / Apache-2.0），由此定位到组织，再 `curl 'https://api.github.com/orgs/openJiuwen-ai/repos?per_page=100&page={1,2,3}'` 拉全量，**共 24 个仓库**（已跑，三页合并去重后 TOTAL=24）。

这是一个**华为系**的 agent 开源社区：多数仓库的 `Cargo.toml`/`package.json` 里 `repository` 指向 `gitcode.com/openJiuwen/...`，发布包走 `openjiuwen-ci.obs.cn-north-4.myhuaweicloud.com`（见 `agentos-enterprise/README.md` 安装段、`agent-dx/Cargo.toml:41-44`）。许可证几乎全 Apache-2.0，法律上无障碍。

### 1.2 排序规则与"后半"切分

按 `created_at` 升序（奠基 → 后来）。24 个仓库切两半，**前半 12 个由 A 侧覆盖，本报告只做后半 12 个**：

| # | 仓库 | created | → |
|---|---|---|---|
| 1–6 | community, deepsearch, agent-protocol, agent-studio, agent-core, docs | 2026-02-26 | **前半（A 侧）** |
| 7 | agent-core-java | 2026-04-09 | 前半（A 侧） |
| 8 | relay | 2026-05-29 | 前半（A 侧） |
| 9 | CareerSim-BDCI26 | 2026-06-01 | 前半（A 侧） |
| 10 | jiuwenswarm | 2026-03-05 | 前半（A 侧） |
| 11 | .github | 2026-03-05 | 前半（A 侧） |
| 12 | agent-tools | 2026-03-05 | 前半（A 侧） |
| **13** | **jiuwensymbiosis** | 2026-06-12 | **后半（本文）** |
| **14** | **agent-memory** | 2026-06-18 | 后半 |
| **15** | **skillhub** | 2026-06-29 | 后半 |
| **16** | **agent-runtime** | 2026-06-29 | 后半 |
| **17** | **agent-runtime-java** | 2026-07-07 | 后半 |
| **18** | **agent-dx** | 2026-08-05 | 后半 |
| **19** | **sciencediscovery** | 2026-08-14 | 后半 |
| **20** | **agent-infer** | 2026-09-07 | 后半 |
| **21** | **agentos-enterprise** | 2026-09-23 | 后半 |
| **22** | **model-router** | 2026-09-24 | 后半 |
| **23** | **iCode** | 2026-09-28 | 后半 |
| **24** | **agent-plugin** | 2026-09-30 | 后半 |

> 排序规则可复现：全部数据来自 `GET /orgs/openJiuwen-ai/repos`（无鉴权）。若 A 侧采用了别的排序（如按 star），切分点会不同——这一点请主代理在合并两份报告时对齐。

### 1.3 组织级成熟度（实测）

| 指标 | 命令 | 结果 |
|---|---|---|
| 近 30 天提交 | `curl 'https://api.github.com/search/commits?q=org:openJiuwen-ai+committer-date:>2026-09-19&per_page=1'` | **2882** |
| 近 90 天提交 | 同上，`>2026-07-21` | **7185** |

**约 96 提交/天。这是真实在运转的工程组织，不是 demo 集合。** 这是本次评审里唯一一条压倒性的正面证据——它不改变任何单模块结论，但它让"代码里写的东西是认真的"这个前提成立。

---

## 第二节 · 后半 12 模块逐个评估（对照 13 抽象 / 13 机制）

### 2.1 agent-dx ★★★★☆ 唯一 Rust 模块，也是后半唯一的工程级候选

**是什么**：Agent Distributed eXecutor，"openJiuwen Agent Runtime 之下的分布式执行底座"（`agent-dx/README.md:9`）。自建 Cargo workspace，`28` 个 crate，Rust 源码 **273,924 行**（`find -name '*.rs' | xargs wc -l`，实测）。

**测得的规模与工程性**：
- `grep -rn '#\[\(tokio::\)\?test\]' --include=*.rs` → **2346** 处；`grep -rn '^def test_\|^    def test_' --include=*.py` → **1230** 处；rs 测试文件 132 个、py 测试文件 146 个。
- 仓库文档自述"404 个静态测试定义 / 528 个"（`docs/testing/test-inventory-and-buildkite-gates.md:19-20`）——**与我的 grep 差一个量级**，应为两套计数口径（门禁注册表 vs 测试函数体）。我如实报告两个数，不替它圆场。
- `grep -rn "todo!()\|unimplemented!()\|TODO: implement" --include=*.rs` → **0**。
- 有分层的 E2E 门禁模型：L0 最小闭环 → Local Standalone → Multi-VM → Full Deployment Acceptance，并明令"不能用 Standalone 通过替代多 VM"（`docs/testing/test-inventory-and-buildkite-gates.md:36-46`）。这种自我约束的测试分级是成熟项目的标志。

**为什么它值得我们看——三处设计与我们直接同构**：

1. **Environment / Runtime 双身份 + 代际 fencing**（`docs/architecture/repository-layout.md:22`）：
   > Environment 是跨节点、暂停恢复和故障接管期间保持不变的**逻辑身份**……Runtime 是 sandboxd 在某个节点创建的一次**物理执行**……二者通过 `RuntimeIdentity { environment_id, runtime_id, ownership_generation }` 绑定，adxlet 只允许当前 generation 的 Runtime 对外提供服务。

   这正是我们 **Run 抽象**（"稳定身份挂在订单上，执行引擎内部编号只是实现细节"）+ **机制7 副作用网关的 fencing 令牌**（"旧节点诈尸"）想要的语义。代码侧对应实现在 `platform/crates/core/src/checkpoint.rs:47-56` 的 `valid_runtime_id()`——runtime_id 的命名格式把 generation 编进了标识本身，旧的 generation 在语法上就匹配不上。

2. **恢复点元数据与存储后端解耦**（`platform/crates/core/src/checkpoint.rs:5-9`）：`CheckpointArtifact { storage, location, size_bytes }` 只存元数据，字节留在后端。对应我们的 **Artifact 内容寻址 + 大载荷外置**（第七节已定）。

3. **检查点的三段式生命周期**（`platform/adxlet/src/checkpoint.rs:176-215`）：`allocate()`（私有本地暂存）→ `retain_staged()` / `publish()`（校验后发布，可回滚上传）→ `materialize()`。并且 `validate_policy()` 显式拒绝"声明了共享存储但节点没配"的请求（`:177-186`）——**声明与现实不符时启动即失败，而不是运行时才发现**。这条纪律值得抄。

**但结论仍是不引入为依赖，三条硬理由**：

- **生命周期模型不同（最致命的一条）**。agent-dx 的 Environment 是**常驻服务**：HTTP/WS/SSH 接入、idle timeout 自动暂停、Gateway 做 Rendezvous Hash 亲和路由（`docs/architecture/repository-layout.md:15-17`）。我们的 Run 是 **WorkOrder 驱动的有界执行**，由投放闸限流、由图引擎调度、由凭证约束预算。把 agent-dx 引进来的实际后果是：我们凭空多出一层 activation / gateway / tenant identity / 长租约，而 §10.4 已经把"通用对话式 agent 平台"列为**明确不做**。用它搭 Run = 为了一个我们不需要的服务语义，吞下 27 万行。
- **运维半径与"部署形态无关"冲突**。硬依赖：常驻 Redis、sandboxd（由 `third_party/sandboxd/source.json` 从 GitCode 钉版本）、组件证书、可达 Gateway。第七节我们已经用 k3s+Karmada+Kueue 覆盖了调度与沙箱。
- **Bus factor = 1**。5 位贡献者，`WenYuLuo` 341 次 / 全仓约 384 次（≈**89%**），star 3，版本号 `v0.1.0rc1`。内核依赖不能由一个人 89% 的单点承担。

**裁定：设计抄件，零依赖。**

### 2.2 model-router ★★★★☆ 抽象对了，代码是骨架

Rust + PyO3（maturin）双形态，`46` 个 `.rs` / `41` 个 `.py`。

**它自己承认是骨架**（`model-router/README.md:19`）：
> "This repository is the workspace skeleton from the blueprint: layout, contracts, assembly, and one runnable ReAct path are in place. **Weighted algorithms, remote state gRPC, and the full PyO3 binding are still stubs.**"

4 位贡献者共 34 次提交，**0 个 release**，1 个 open issue。README 里的 Quick start 甚至指向作者本机的 `rust_demo_mod_04` 环境变量（`:96-98`）——这是能看见的"未脱离个人机器"痕迹。

**值得抄的两条**：
- **`route → host 自行执行 → report 反馈` 的三段式契约**（`README.md:13-15`、`:36-38`）：路由**不进数据面**，算法只返回 `selected_model_id` + `reasoning`，模型调用由宿主发起。这条边界防止了"网关成为单点与延迟源"。
- **"state 是 hint，丢失只降级为冷路由，不失败请求"**（`README.md:45-46`）：远端 state 超时返回空视图而非报错。**这是一个可直接搬走的失败语义**，对应我们"安灯保留给真正的异常，队列慢就放慢投放"（机制1）的同一种品味。

**为什么不引入**：它选模型，但我们的难点不是"选哪个模型"而是**"每个供给还剩多少额度"**——那是我们 Meter（机制8，可声明、可组合取 min/max）的活，model-router 完全不碰这块。且第七节模型网关已定 Bifrost。**裁定：观望（抄契约，不接依赖）。**

### 2.3 agent-memory（JiuwenMemory）★★★☆☆ 成熟度可以，架构与我们打架

实测：**70★ / 9 位贡献者 / 5 个 release（最新 v0.2.0, 2026-09-21）/ 103 个 open issue**。**已上 PyPI**：`https://pypi.org/pypi/JiuwenMemory/json` → version 0.2.0、6 个发行版、`requires_python >=3.11`、依赖 `cryptography>=42, numpy>=1.24, openai>=1.0, jieba>=0.42, pyyaml>=6.0`，可选 extras 拉到 `pymilvus / elasticsearch / redis / asyncpg / FlagEmbedding / torch>=2.0 / transformers / spacy`。

**能力是真的**：L0–L3 四层记忆、睡眠期三段整合（浅睡筛 → REM 抽取分类 → 深睡去重与冲突消解）、MemoryTurbo（先写缓存、后台异步抽取）、图记忆、`MemUpdateChecker` 用 LLM 判 ADD/DELETE。

**但它与我们宪法正面冲突，这是决定性的**：

- 它的核心操作是 **LLM 驱动的可变更新**（ADD/DELETE/UPDATE 指令）。我们的宪法第 1 条是"agent 之间只传工件引用，不传消息"，抽象 2 是"一切产出都是不可变的内容寻址块"。**把一个语义是"就地改写"的组件接进内容寻址的工厂，等于在不可变地基上开一个可变洞**，而且这个洞开在"记忆"这个最容易被误当成事实源的位置。
- 它的抽取路径**每次对话都调大模型**。这在我们的账本里是一笔**每轮固定发生的、配方里没申报的税**——机制9「通用日历」和宪法第 9 条都要求预算计量维度可声明，而这里的开销既不在 Run 的凭证预算里，也不在图引擎的节点声明里，会变成"影子成本"。影子价格我们只在机制12 里用来给运营者做采购决策，不是用来藏开销的。
- 记忆在我们的 13 抽象里**只是扩展抽象 10（Resident Agent）的附属层**，而 D5 已明确"扩展抽象按需排后"，一期 M1–M5 不含它。

**裁定：观望。** 二期 Resident Agent 上线时，若要接，它的 `MemoryProvider` 接口 + FastAPI REST 天然适合做 **L2 适配器**，但必须满足两条接入前置：①全部 LLM 抽取调用走我们的凭证与 Meter；②记忆的每次变更物化为工件（版本化），而不是原地改写。这两条做不到就不接。

### 2.4 skillhub ★★☆☆☆ 分发市场，不是信任边界

32★ / 19 位贡献者（`yy7918` 164 次）/ **0 个 release、0 个 tag** / 15 open issue。技术栈：Python ≥3.11.4 + FastAPI/SQLAlchemy、React 18 + Vite + MUI，**必需 MySQL + 必需 S3 兼容存储（MinIO 或华为 OBS）+ 外部 Auth 服务**（`skillhub/README.md:56-61`）。功能是六类资产（Skill/SwarmSkill/plugin/connector/expert/expert group）的市场，含 CLI `agentichub`、Web UI、ClawHub 兼容。

**为什么不能拿它当我们的 Skill 信任根**：我 `grep -rn "signature\|sha256\|verify\|digest" --include=*.py -il skillhub/marketplace/`，返回的 8 个文件**全部落在 `recommender/` 与 `skill_review/`**，唯一的完整性字段是 `recommender/offline/package_sync/db.py:28` 的 `artifact_sha256: str | None`——**可空**，且用途是离线推荐管道的索引同步，不是装载期强制校验。

我们的宪法要求"Skill 装载时验签**不可跳过**"。一个把完整性字段定义为 optional 的分发市场，恰恰证明它假设的信任模型是"我信我自己的源站"，而我们的信任模型是"签名可离线验证、不信任分发通道"。**两者不可互换。**

> **诚实声明**：`skillhub/cli/`（`agentichub` 的 install/validate 路径）我**没能检查**——shell 在本次评估末尾因 `/tmp` tmpfs 写满（ENOSPC，fork 失败）而完全失效，上述负面结论的检索范围仅限 `marketplace/`。

**裁定：不引入。** 资产分发是运营层的事，且三个外部必需依赖与我们的"适配器只翻译不决策"边界无关。

### 2.5 agent-runtime ★★☆☆☆ 把"agent 是长驻服务"写死了

15★ / 13 位贡献者 / **1 个 release（v0.1.0, 2026-06-29）** / 38 open issue。Python ≥3.11.4 + uv + FastAPI。三种部署策略 `subprocess` / `docker` / `k8s`，多租户注入 `user_id`/`space_id`，标准端点 `/query` `/health` /`reset_conversation`（`agent-runtime/README.md:1-50`）。

**为什么对我们无用**：它的整个存在理由是"把 agent 统一部署成服务"。而部署形态在我们宪法第 5 条里是**运营者配置，不是内核立场**；一个把部署形态固化进产品抽象的组件，引入即违反三无关里的"部署形态无关"。技术上 subprocess/docker/k8s 三件套与 k3s 零增量。

**裁定：不引入。**

### 2.6 agent-runtime-java ★☆☆☆☆ 同构的 Java 副本

33★。Spring Boot HTTP ingress + 进程内 A2A（Agent Card / JSON-RPC / TaskStore），模块分层 `spec → adapters → app`（`agent-runtime-java/README.md:1-40`）。与 2.5 同构的 Java 实现，语言直接冲撞 D5 的"自研内核全部 Rust"基线。**裁定：不引入。**

### 2.7 agentos-enterprise ★★☆☆☆ 纯部署编排，且专有化

19★ / 17 位贡献者 / 0 release。内容是 **24 个 md + 21 个 sh**，几乎没有代码。用 git submodule 聚合 agent-runtime + jiuwenswarm + Conch 沙箱 + A2X registry，`deploy/agentos.sh` 编排 moosefs/jiuwenbox/agent-runtime/agent-gateway/jiuwenswarm 五个模块。要求 **openEuler 22.03/24.03 LTS、MooseFS 4.59.2、etcd、bwrap/iptables/fuse3**（`agentos-enterprise/README.md:30-40`）。

**为什么对我们无用**：① submodule 把整条依赖链钉死在 openJiuwen 自家组件上，我们要的是内核无关的适配器；② 它把"某一种部署形态"写成了产品的一部分——在我们这里，部署形态是 L4 运营者配置，抄进 L1 就是特化。**裁定：不引入。**

### 2.8 iCode ★★★★☆ 大而成熟的编码 agent TUI——抄形态，不接依赖

358★ / 10 位贡献者（`0x7c13` 223 次）/ **5 个 release，最新 v0.30.0 (2026-10-15)** / 13 open issue。`src/` 下 Python **331,141 行**，1392 个测试文件，63 个 docs。README 自标 **"Work in progress. Interfaces, file formats, and defaults still change between releases."**

**为什么不能接为依赖**：它是明确的**编码专用 TUI**——diff 视图、按轮次回滚文件改动、trajectory 时间线。我们的三无关第一条是"任务无关"：把一个为改代码而生的 TUI 接进内核，就是宪法第 2.2 节判据里的"特化"。

**但它有几处通用设计值得抄**（文件路径均为实测）：
- `src/chrys/orchestration/invoker/usage.py` + `src/chrys/orchestration/session_usage.py` + `src/chrys/orchestration/engine/trajectory.py` —— 把 token/时间/并行度**按轮次与节点归集**，正对我们"单位成本沿工件血缘归集"（机制11/12）。抄的是**归集口径**，不是代码。
- `src/chrys/orchestration/workflows/rollback.py` —— 选一轮 → 审阅将被撤销的改动 → 丢弃对话。对应我们的"人改稿=工件 v+1，下游自动用新版"（抽象12/人工工位）与 Delivery 发布投影的回滚。
- `src/chrys/orchestration/sub_agents/kernel_policy.py` 与 `acp_policy.py` —— 子 agent 策略独立成文件，对应我们"派生子 agent 时凭证只能收紧不能放宽"（抽象4）。
- `src/chrys/orchestration/invoker/attempts.py` —— 候选的"失败指纹止损"（机制6）实现参考。

**裁定：部分引入（纯设计抄件，零依赖）。**

### 2.9 sciencediscovery ★★★☆☆ 一座工厂的实例，不是底座——但工作台形态可抄

168★ / 12 位贡献者 / **3 个 release，最新 v0.3.0-rc1 (2026-10-16)** / **117 个 open issue**。TypeScript + Python monorepo。本地优先的科学研究工作台，发行**预编译二进制**（linux x86_64 / aarch64），"Bubblewrap 是唯一的系统依赖"，建在 JiuwenSwarm 之上，agent 读文献 → 写并运行代码于沙箱 → **记录每个结果的来源**（`sciencediscovery/README.md:19-40`）。

**为什么不是底座**：它是"某一座工厂"的具体实例——恰好对应我们 §6 里"用户一号"的形态（研究流水线）。拿它当内核 = 把一种产品形态写进内核，违反任务无关。

**可抄的一处**：它的 **artifact / reviewer / provenance 三面板**（见 README 首图），是 Evaluation 三态 + Human Station + Artifact 血缘三者合流后的**成熟产品形态**。这正是我们 L4 运营者空间里"人工工位"该长成什么样——现在有现成设计可参照，不必凭空画。

**裁定：部分引入（L4 形态参考），零依赖。** 117 个 open issue 说明它仍在施工，形态还在动，抄的时候要抄结构不抄细节。

### 2.10 agent-infer ★★★☆☆ 真本事，但绑死 vLLM + 昇腾

99★ / 8 位贡献者 / 1 个 release（0.2.0, 2026-10-15）/ 27 open issue。三个能力（`agent-infer/README.md:7-18`）：**Semantic Router**（Mixture-of-Models，多轮会话连续性感知以减少破坏性且昂贵的模型切换）、**Agent Cache**（vLLM 插件，管 agentic 负载下的调度与 **Ascend NPU 原生 KV cache** 管理/池化/迁移）、**AgentBench**（agentic 负载下的推理引擎基准，可由真实 agent run 或 trace 数据集重放驱动）。**硬依赖 vLLM 0.23.0 + CUDA/昇腾 GPU**，须装在 vLLM 同一环境。

**为什么不是现在引入**：①它是我们已选的 vLLM **前面的一层插件**，不是替换，接进来要在推理链路上多一个可失败点；②绑昇腾与具体 vLLM 版本，耦合在我们还没定型的 M4 上；③ 99★/8 人/1 release，单点风险高。

**唯一值得单独跟踪的是 AgentBench**——我们机制12「容量测量」和 Trace 重放都缺一个 agentic 负载基准。**裁定：观望。**

### 2.11 jiuwensymbiosis ★★☆☆☆ 领域外，但有一处数学有意思

66★。具身智能：身体无关的 `ActionSpec` 动作契约 + 能力门控、动态编排与冲突重规划、"感知即预订 / 移动即失效"的执行记忆、实时跟踪伺服、可达性推理、安全回路、可审计执行（结构化 trace + 存帧 + 回放）。

**为什么对我们无用**：我们的 §10.4「明确不做」第 3 条写的是：不做**执行物理动作的产线**。这是范围判断，不是技术判断，我不为它找补。

**唯一记一笔**：它的"动作契约声明前置条件与效果，序列校验器**只接受前置条件成立的排列**"（README Core Features 末条）是一个干净的规划形式化。如果将来要做受控分支/受控循环的静态校验，这个思路值得回看。**裁定：不引入。**

### 2.12 agent-plugin ★☆☆☆☆ 内容仓，只有一个示例插件

0★ / 1 fork / 92KB。目录里只有 `plugins/example-plugin`（1 skill + 1 tool + 1 rail），外加脚手架模板与工具链脚本。无工程价值。**裁定：不引入。**

---

## 第三节 · 效果证据汇总（全部为本次实测，无一条来自印象）

| 模块 | star | 贡献者（头部占比） | release | open issues | 语言 | 判读 |
|---|---|---|---|---|---|---|
| agent-dx | 3 | 5（WenYuLuo 341/≈384 ≈ 89%） | 1（v0.1.0rc1） | 13 | **Rust** 273,924 行 / 28 crate | 代码最硬，治理最软 |
| model-router | 13 | 4（共 34 次） | **0** | 1 | Rust+PyO3 | 自述骨架 |
| agent-memory | 70 | 9 | 5（v0.2.0, 09-21） | **103** | Python（PyPI 6 个发行版） | 有分发，欠收敛 |
| skillhub | 32 | 19（yy7918 164） | **0** | 15 | Py+React | 无发版纪律 |
| agent-runtime | 15 | 13 | 1（v0.1.0, 06-29） | 38 | Python | 原型期 |
| agent-runtime-java | 33 | — | — | — | Java | 副本 |
| iCode | 358 | 10（0x7c13 223） | **5（v0.30.0, 10-15）** | 13 | Python 331,141 行 | 发版节奏最好 |
| sciencediscovery | 168 | 12 | 3（v0.3.0-rc1） | **117** | TS+Py | 仍在施工 |
| agent-infer | 99 | 8 | 1（0.2.0, 10-15） | 27 | Python（vLLM 插件） | 窄而深 |
| agentos-enterprise | 19 | 17 | 0 | 0 | Shell | 脚本仓 |
| jiuwensymbiosis | 66 | — | — | — | Python | 领域外 |
| agent-plugin | 0 | — | — | — | Python | 空壳 |

许可证：除 `community`/`docs` 为 CC-BY-4.0（在前半）、`CareerSim-BDCI26` 为 MIT（在前半）外，**后半 12 个全部 Apache-2.0**。无 copyleft 障碍。

---

## 第四节 · 引入成本、对接四层、退出成本

### 4.1 按四层定位

| 模块 | 若引入会落在 | 但我们的裁定 |
|---|---|---|
| agent-dx | L1（执行/沙箱/放置） | **不引入**，抄 Environment/Runtime 双身份 + 代际 fencing + CheckpointStore 三段式 |
| model-router | L1（路由） | **不引入**，抄三段式契约与"state 是 hint"的失败语义 |
| agent-memory | L2 适配器 | **观望**，且须满足"LLM 抽取全走 Meter"+"变更物化为工件"两条前置 |
| skillhub | L4 运营 | **不引入**，分发市场不是信任边界 |
| agent-runtime / -java / agentos-enterprise | L4 部署 | **不引入**，把部署形态写死，违反宪法 5 |
| iCode | L4 运营者空间（工作台形态） | **不引入为依赖**，抄 usage/trajectory 归集口径与 rollback 语义 |
| sciencediscovery | L4 运营者空间 | **不引入为依赖**，抄 artifact/reviewer/provenance 三面板 |
| agent-infer | L1/L2 边界（vLLM 前置插件） | **观望**，跟踪 AgentBench |
| jiuwensymbiosis / agent-plugin | — | **不引入** |

### 4.2 真实成本（若强行引入 agent-dx，这是账单）

- 语言：**匹配**（Rust，是后半唯一），D5 语言基线无冲突。
- 依赖：常驻 Redis + sandboxd（GitCode 钉版本）+ 组件证书 + 可达 Gateway + Kubernetes 编排。
- 代码面：273,924 行 Rust，28 crate。**全量吞下远超我们的需要**（我们要的是 batch Run 语义，它给的是常驻 Environment 语义）。
- 运维：release 包与 CI 在华为云 OBS + GitCode + Buildkite，不在 GitHub Releases。
- 治理：89% 单一作者、3 star、`0.1.0rc1`。
- **净：为了一个不需要的服务语义，吞下 27 万行 + 一整套分布式基础设施 + 一个 bus factor = 1 的上游。不划算。**

### 4.3 退出成本

**因为本次裁定是「零运行时依赖引入」，退出成本 = 0。** 这正是这个结论最实际的价值：抄走的是设计（写进我们自己的设计文档与 Rust 代码），上游明天改仓库、改许可、甚至消失（3 star 的项目随时可能删库），都不影响我们一行代码。

反过来说：**如果我们采纳了 agent-dx，退出成本将极高**——生命周期模型一旦按它的 Environment 设计，Run 的语义就被绑死在它的协调器语义上，替换等于重写内核。这是不采纳的第二个理由。

---

## 第五节 · 结论与裁决

### 裁决：**部分引入** —— 引入的是设计，不是依赖

**核心理由三句话**：

1. **这个组织是认真的**（96 提交/天，全 Apache-2.0，agent-dx 有 2346 个 Rust 测试函数与 0 个 stub 标记）。所以它值得读。
2. **但后半 12 个模块里没有一个解决我们真正卡住的问题**。我们卡的是：Run 的生命周期与内容寻址、凭证、评估三态、配方与运营者配置、13 个机制的边界。openJiuwen 后半解决的是——把 agent 变成服务、把 agent 资产放进市场、把记忆抽出来、把模型路由一遍、把推理缓存管起来。**这些是好东西，但没有一个是我们的瓶颈。**
3. **最像样的那个（agent-dx）恰好是最不该整体引入的**：它是一个常驻服务执行底座，而我们的 Run 是 WorkOrder 驱动的有界执行；引入即多出一层我们明确不做的 activation/gateway 抽象，且 bus factor = 1。**大胆但诚实的结论是：整体不引入，只抄三处设计。**

### 抄件清单（可直接进我们设计文档，不需要任何代码改动）

| # | 抄什么 | 来自 | 抄进我们的哪一处 |
|---|---|---|---|
| C1 | **逻辑身份 / 物理执行分离 + 代际 fencing**：`RuntimeIdentity{environment_id, runtime_id, ownership_generation}`，旧代际在语法上就匹配不上 | `agent-dx/docs/architecture/repository-layout.md:22`、`platform/crates/core/src/checkpoint.rs:47-56` | **抽象 1（Run）** 与 **机制 7（副作用网关 fencing 令牌）**——把"执行纪元号"从整数升级为"身份命名规则"，让诈尸请求在比对阶段就被拒，而不是在执行阶段被拦 |
| C2 | **恢复点元数据与字节解耦 + 三段式检查点**：`CheckpointArtifact{storage, location, size_bytes}`；`allocate → retain/publish → materialize`；**声明与现实不符时启动即失败** | `platform/crates/core/src/checkpoint.rs:5-9`、`platform/adxlet/src/checkpoint.rs:176-215` | **抽象 2（Artifact）** 大载荷外置；**Trace「宁停勿丢」**的落盘语义 |
| C3 | **决策不进数据面 + state 是可丢的 hint**：`route → host 执行 → report`；远端 state 超时返回空视图而非失败请求 | `model-router/README.md:13-15, 36-38, 45-46` | **计量/路由**的失败语义；同源于机制 1「队列慢就放慢投放，安灯留给真异常」的品味 |
| C4 | **成本按轮次与节点归集** | `iCode/src/chrys/orchestration/invoker/usage.py`、`session_usage.py`、`orchestration/engine/trajectory.py` | **机制 11（观察聚合）/ 机制 12（容量测量）**的归集口径 |
| C5 | **人改=新版本、可回滚**：`workflows/rollback.py` | `iCode/src/chrys/orchestration/workflows/rollback.py` | **抽象 12（Human Station）修订语义** + **抽象 11（Delivery）投影回滚** |
| C6 | **子 agent 策略独立成文件、凭证只收紧** | `iCode/src/chrys/orchestration/sub_agents/kernel_policy.py`、`acp_policy.py` | **抽象 4（Credential）** |
| C7 | **三面板工作台**：artifact / reviewer / provenance | `sciencediscovery/README.md:19` 及首图 | **L4 运营者空间**里"人工工位"的形态参考（抄结构，不抄细节——该仓 117 个 open issue，形态还在动） |
| C8 | **E2E 分级门禁 + 禁止用低层通过替代高层** | `agent-dx/docs/testing/test-inventory-and-buildkite-gates.md:36-46` | 我们自己 M1→M5 的**验收纪律**（"不能用 Standalone 通过替代多 VM"是我们缺的） |

### 明确不做的事

- **不引入 agent-dx 为运行时依赖**（生命周期模型不符 + bus factor 1 + 27 万行）。
- **不引入 skillhub 作为 Skill 信任根**（完整性字段 `artifact_sha256` 可空，装载期无强制验签）。
- **一期不接 agent-memory**（可变语义破坏内容寻址；LLM 抽取是未申报的每轮成本）。
- **不把 agent-runtime / agentos-enterprise 的部署形态抄进 L1**（违反宪法第 5 条）。
- **不碰 jiuwensymbiosis**（我们不做物理产线）。

### 本次评估的边界（如实交代）

**没有跑的检查**：
- ❌ **`cargo check` / `cargo build` 未跑** —— 本机无 Rust 工具链（`rustc --version` → `rustc: 未找到命令`，`cargo --version` 同样）。**agent-dx 是否真能编译，本次未验证**，全部结论为代码级 + 文档级评估（依任务约定"跑不起来就做代码级+文档级评估，不硬跑"）。
- ❌ **Python 测试一个没跑**（无 pytest 环境）。iCode 的 1392 个测试文件、agent-memory 的 103 个 open issue 等均为**静态观测**，非通过结论。
- ❌ **`skillhub/cli/` 未检查** —— shell 在本次评估末尾因 `/tmp` tmpfs 写满（ENOSPC，fork 失败）完全失效。2.4 节的负面结论检索范围仅限 `marketplace/`。

**环境障碍（如实记录）**：
- `/tmp` 为 7.5G tmpfs，已被他人占 6.4G，`pwd` 即报 `超出磁盘配额`。因此克隆改在 `/home/pan-ding/workspace/临时工作区/temp2/.ext-research/`。
- 首次 5 路并行 `git clone` 全部 `Failed to connect to github.com port 443`；改为**串行克隆**后全部成功。
- 评估结束时 shell 失效，**克隆目录未能删除**（任务要求结束删除）。残留路径：`/home/pan-ding/workspace/临时工作区/temp2/.ext-research/`（约 300MB，含 agent-dx / agent-memory / skillhub / model-router / agent-runtime / agent-infer / iCode / agentos-enterprise / sciencediscovery）。另有一个我未克隆的 `ANOLISA/`（160MB）出现在同一目录下，来源不明（可能是并行代理的工作区），**我未删除它**。待 shell 恢复后需人工清理。
- `agent-plugin` / `agent-runtime-java` / `jiuwensymbiosis` 三个仓库**未克隆**（README 经 `raw.githubusercontent.com` 读取），故这三项评估为**文档级**，无代码级证据。

### 给主代理的一句话

**「openjiuwen 后半模块：一个真实在运转的华为系 agent 社区（96 提交/天，Apache-2.0），但它的后半段在做"把 agent 变成商品与服务"（市场/运行时/记忆/路由/缓存），而我们的内核在做"让机制可治理"。交集在设计语言（身份分离、fencing、决策不进数据面、成本归集），不在代码。裁决：部分引入其 8 条设计，零运行时依赖，退出成本 0。」**

---

*本报告的全部数字与代码引用均来自 2026-10-19 本会话内的实测命令（`curl https://api.github.com/...`、`git clone --depth 1`、`wc -l`、`grep -rn`）；未跑的检查已在第五节逐条列明。*
