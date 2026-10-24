# 外部项目研究 · openJiuwen（openjiuwen-A）

> 研究日期：2026-10-19 · 评审员立场：默认拒绝（有效证据充分时可大胆）· 我们的底座：自研 Rust 内核 + 13 抽象 + 13 机制 + 四层形态（L1 内核 / L2 适配 / L3 配方 / L4 运营），设计依据《产品设计_拍板版.md》§1-2 及全文。

---

## 一、定位与结论（TL;DR）

**项目真实存在，且是一个大型多模块开源生态。** GitHub 组织 `openJiuwen-ai`（blog: https://www.openjiuwen.com，China，创建于 2026-02-26，24 个公开仓库，731 followers）。搜索变体实测：直接搜 `jiuwen` 即命中该组织（88 个仓库结果）；拼写变体 openjiuwen / open-jiuwen / OpenJiuWen / jiuwen / 九问 / 久闻 中，真实命中的是 **openJiuwen-ai** 组织及其 `openjiuwen` PyPI 包；其余拼写（九问、久闻、open-jiuwen）未发现对应项目。组织背后是华为（agent-core、agent-dx 等源码文件头版权均标注 "Copyright (c) Huawei Technologies Co., Ltd."，如 `openjiuwen/core/graph/graph.py:2`、`openjiuwen/harness/security/permission_engine/core.py:1`、A4P `src/a4p/__init__.py` 无标注但仓库同属该组织）。

**一句话定位**：openJiuwen 是一个"Agent 开发→运行→部署→分发"全链路平台生态（ agent SDK + 可视化工作室 + 分布式运行时 + 推理/路由/记忆等中间件 + 技能市场 + 若干终端应用），许可证全部 Apache-2.0，语言以 Python/Java 为主、两个系统级组件为 Rust（model-router、agent-dx）。

**结论：不引入（作为内核）；局部设计参考 + 两个 Rust 组件列入观望。** 它与我们重叠的部分（任务图、会话/检查点、trace、评估、权限、技能）是"Agent 框架"品类（LangGraph/Dify/LiteLLM 同类），不是"工厂内核"品类；我们 26 件内核预算里最独特的机制（CONWIP 投放闸、CSP 抽样、升迁梯、金标注入、副作用网关幂等+fencing、可组合 Meter、通用日历、JIT 护栏）在 openJiuwen 中**一个都不存在**，因此不存在"某子系统整体用它搭"的证据基础。其两个 Rust 组件（model-router 路由内核、agent-dx 分布式执行底座）与我方语言基线一致、架构思想值得抄，但均处骨架期（13★/3★，README 自述大量 stub），结论为观望、暂不引入。详见第四、五节。

---

## 二、项目概览与完整模块清单（24 个仓库）

数据来源：2026-10-19 GitHub API `orgs/openJiuwen-ai/repos`（stars/forks/语言/最近推送）与各仓库 README/源码（本地解包后阅读）。按与内核相关度排序：

### 第一梯队（平台主干）

1. **agent-core（openjiuwen，Python，451★/127 fork，2026-10-19 推送，PyPI 版本 0.1.19）**——生态的 SDK 内核：Agent 创建、工作流编排、LLM 调用、工具调用、可观测、状态保存与断点恢复。包内含 `core`（single_agent/workflow/graph/session/security/sys_operation/retrieval/memory/context_engine）、`harness`（DeepAgents 编码 agent 框架：rails/权限引擎/subagents/task_loop）、`agent_teams`（多 agent 团队，含 HumanAgentInbox 人在环）、`agent_evolving`（自演进训练评估框架）、`rsi`（递归自我改进：artifact RSI 程序搜索 + harness RSI）、`symphony`（能力图谱/评估套件）、`extensions`（OTel tracer/存储/检查点/sandbox provider/A2A）。成熟度证据：1447 个测试文件（`find tests -name 'test_*.py' | wc -l` = 1447，本机实测）、PyPI 49 个发版（0.0.37→0.1.19.post2，2026-10-14 最新，pypi.org/pypi/openjiuwen/json）、Python 3.11-3.13。是全生态中唯一天然具备"内核"地位的仓库，但仍是 Python。

2. **jiuwenswarm / JiuwenClaw（Python，7422★/1110 fork，2026-10-19 推送，版本 0.1.5）**——旗舰应用：个人"全天候 AI 管家"，经 IM 渠道（飞书/lark-oapi、钉钉、小艺、Web）交互，支持定时任务（heartbeat/cron）、技能自演进（`jiuwenclaw/evolution/`：skill_optimizer/signal_detector）、长期记忆、浏览器自动化。依赖 `openjiwen==0.1.7`（pyproject.toml），是 agent-core 之上的应用层，证明 SDK 可被第三方（社区）用来搭产品。

3. **agent-studio（Java，189★/63 fork，2026-10-16 推送）**——低代码/零代码可视化开发平台：拖拽画布编排工作流、提示词生成/自动优化/多版本对比、技能（模型/插件/记忆）统一管理、在线调试发布。Java 后端 + 前端，对应我们 L3/L4 的"运营者配置面 + 工作台"。

4. **agent-runtime（Python，15★/4 fork，2026-10-19 推送）**——Agent 运行与部署管理平台：REST API 部署/列举/删除/健康检查，三种部署策略（subprocess/docker/k8s），多租户隔离（user_id/space_id），SQLite/MySQL/Redis 底座。对应我们 L2 适配层的"部署运维"关切。

5. **agent-memory（Python，70★/21 fork，2026-10-12 推送，PyPI: JiuwenMemory）**——长期记忆模块：多类型记忆自动抽取（用户画像/语义/情景/变量/摘要）、向量语义检索、AES-GCM 加密、多存储后端（Milvus/ChromaDB/PG/MySQL/GaussDB/SQLite/Redis）、版本化迁移框架、可插拔 MemoryProvider（兼容 Mem0/AgentArts）。

6. **agent-infer（Python，99★/15 fork，2026-10-15 推送，v0.1.0）**——面向 agent 负载的推理框架：vLLM 0.23.0 之上的语义路由器（连续性感知的模型选择）、agent 感知调度、KV cache 池化/迁移插件（含昇腾 NPU 原生）、AgentBench（真实 agent run/trace 回放驱动推理引擎基准）。

7. **model-router（Rust+Python，13★/6 fork，2026-09-24 推送）**——模型路由内核：**核心是 Rust**（Cargo workspace：protocol/state/algorithms/runtime 四层 + PyO3 绑定），决策与执行分离（算法只返回 selected_model_id+reasoning，host 自己调模型，router 不在流量路径上）、算法为纯函数、状态是可丢失的 hint、edge/cloud 双 TOML profile。README 自述："workspace skeleton from the blueprint… Weighted algorithms, remote state gRPC, and the full PyO3 binding are still stubs"——骨架期。

8. **skillhub / openJiuwen Agentic Hub（Python，32★/10 fork，2026-10-10 推送）**——Agent 资产市场：六类资产（Skill/SwarmSkill/plugin/connector/expert/expert group）的发布/版本化/下载，FastAPI+MySQL+前端，CLI `agentichub`（脚手架/校验/打包/发布/安装），可选 ClawHub 兼容 API，有托管版 agentichub.openjiuwen.com。

9. **agent-protocol（C++/Python，115★/44 fork，2026-10-16 推送）**——互操作与授权协议集合：MCP CPP SDK、A2A CPP SDK、A2X agent registry、**A4P**（Agentic Authentication, Authorization, and Audit Protocol，Python SDK：Intent/Operation mandate、ed25519/webauthn 用户签名、授权服务器、SQLite intent token 用量账本）。

10. **deepsearch / openJiuwen Search（Python，129★/30 fork，2026-10-16 推送）**——深度检索与研究引擎集合：DeepSearch（知识增强多步研究、state-space search、段落级引用可溯源、带图图表报告）+ CodeSearch 子项目，面向金融/学术/政策研究报告生产。

### 第二梯队（系统级与分发）

11. **agent-dx / Agent Distributed eXecutor（Rust，3★/5 fork，2026-10-18 推送，默认分支 master）**——分布式执行底座（Rust workspace：afs/agent/gateway/crates/platform）：Template/AgentBinding 管理、无状态 Activator 按需启动 harness（HTTP/WebSocket/SSH）、分布式调度、隔离执行、流量路由、**检查点恢复**（本地/S3）、GPU/NPU 库存感知、执行后端可替换、独立 sandboxd。生态中第二个 Rust 原生组件。

12. **agentos-enterprise（Shell，19★/4 fork，2026-10-16 推送）**——企业级一体化交付仓：以 git submodule 拼装 agent-runtime + jiuwenswarm + Conch（Agent 沙箱）+ agent-protocol（接入网关），一键构建/部署（moosefs/jiuwenbox/agent-runtime/agent-gateway/jiuwenswarm 五模块），支持 openEuler 22.03/24.03、Ubuntu 22.04/24.04，单机与集群。

13. **agent-core-java（Java，43★/6 fork，2026-10-19 推送）**——agent-core 的 Java 版 SDK；**agent-runtime-java（Java，33★/5 fork，2026-10-19 推送）**——分布式 Agent Runtime 的 Java 实现。双语并行的生态策略。

14. **iCode（Python，358★/62 fork，2026-10-18 推送，PyPI: iCode-TUI）**——终端 TUI 编排工具："iCode is solely a tool for orchestrating agents and workflows"，不自带模型、无遥测。亮点：agent 是配置不是代码（F2）、F12 Trajectory（时间/token 花在哪：模型 vs 工具 vs 等待）、diff/rollback（逐轮回退文件改动）、审批模式、可选 OTel 导出。README 自述 "Work in progress"。

15. **sciencediscovery（TypeScript，168★/32 fork，2026-10-16 推送）**——面向科研的 all-in-one agentic workbench；**jiuwensymbiosis（Python，66★/8 fork，2026-10-16 推送）**——基于 agent-core 的 Physical AI 助手；**relay（TypeScript，5★/2 fork）**——多 agent 协作平台（协作开发/code review/任务管理）；**agent-tools（Python，19★/7 fork）**——Agent 工具生态；**agent-plugin（Python，0★）**——插件（早期）；**CareerSim-BDCI26（Python，7★）**——CCF BDCI 2026 竞赛 agent 生存晋升挑战（社区运营/评测用途）；**docs（32★）**——文档中心；**community（13★）**——社区章程；**.github（4★）**——组织 profile。

**生态总评**：24 仓、双语言（Python/Java 为主 + 2 个 Rust 系统件 + C++ 协议 SDK + TS 前端）、Apache-2.0、发版节奏以天计（多个仓库 2026-10-19 当天有推送）、旗舰应用 7.4k★。作为"Agent 开发平台生态"，成熟度证据充分；作为"生产工厂内核"，缺件严重（见第三节）。

---

## 三、前半部分逐模块深研：对照我们的 13 抽象找重叠与互补

深研对象（按清单前半）：agent-core（重点）、jiuwenswarm、agent-studio、agent-runtime、agent-memory、agent-infer、model-router、skillhub、agent-protocol(A4P)、deepsearch。证据均为本地解包后阅读的 文件:行号。

### 3.1 agent-core —— 与我们重叠最多、也最能看出"品类差异"的仓库

**（a）TaskGraph ↔ 我们的抽象 3**：`core/graph/` 是基于 Pregel 的图引擎（`graph.py:36-48` 引入 `Pregel/PregelBuilder/START/END/MAX_RECURSIVE_LIMIT`；`atomic_node.py:27-46` 定义 AtomicNode，节点执行后 `session.state().commit_cmp()` 做状态提交）。`core/workflow/` 提供组件化工作流（LLMComponent/questioner 等，`workflow.py:155-244`）。**重叠**：声明式图、节点=转换、边=依赖、受控循环（递归上限）、动态跳转——与我们的 TaskGraph 同品类。**差异**：我们的节点四型分类（调模型/人工门/确定性检查/纯数据变换，"确定与不确定成为类型属性"用于关灯统计）他们没有；他们有一等公民程度的"人工反馈"只是 questioner 组件模式（`components/llm/questioner_comp.py:456,713` `_get_latest_human_feedback`），不是带账本/法定人数/超时缺省的人工门节点类型。

**（b）Run ↔ 抽象 1**：`session/checkpointer/checkpointer.py`（in_memory + redis 后端，`extensions/checkpointer/redis`）提供工作流断点恢复；README 宣称 "checkpoint recovery for interrupted workflows"。**重叠**：执行的有界性+暂停恢复。**差异**：没有"领一张短期凭证（工具白名单+多维预算）"的 Run 概念；预算只有迭代次数/`budget_tokens` 之类的软限制（`core/single_agent/agents/react_agent.py:1734,3061`），无可拦截的多维资源预算；没有"可否被抢占/可否恢复"的调度声明。

**（c）Artifact ↔ 抽象 2**：`session/vcs/`（CLAUDE.md 自述："Per-session linear version control… rewind: overwrite… fork: mints a new session_id"；`jsonl_backend.py`/`kv_backend.py`，LogEntry 带 crc32 防撕裂）。**重叠**：版本化、可回滚、可 fork。**差异**：是"会话内线性 VCS"而非"内容寻址的不可变块"——无全局 hash 寻址、无同输入同转换命中缓存、无签名决策记录（人的审批不是一等签名工件）。这是与我们根基性差异最大的一处：他们的工件是会话状态的历史，我们的工件是内容寻址的对象。

**（d）Trace ↔ 抽象 5**：`session/tracer/`（span/decorator/workflow_tracer）+ `extensions/tracer_otel/`（OTel 语义约定、redaction、otel_rail）。**重叠**：结构化事件流、编译器材料。**差异**：无 Merkle 锚定、无签名、无外部见证——"产生记录的 Run 自己事后改不了历史"这一属性他们没有；agent_evolving 的 trajectory（`agent_evolving/trajectory/`）是可离线抽取的规范轨迹模型，方向对（trace 作为语料），但止于"可分析"不到"防篡改"。

**（e）Evaluation ↔ 抽象 6**：`agent_evolving/evaluator/evaluator.py`（BaseEvaluator/DefaultEvaluator=LLM-as-judge/MetricEvaluator 分数聚合，`batch_evaluate` 并行）、`symphony` 的 EvaluationSuite/EvaluationWindow/Evaluator、`core/security/guardrail/`（BaseGuardrail+Backend 两层、prompt injection 检测、RiskLevel）。**重叠**：可复现判定、评估即版本化资产（ evaluator 是工件）。**差异**：输出是分数不是三态——没有"需人工"第三态触发安灯的机制；`agent_teams` 的 `HumanAgentInbox`（`agent_teams/__init__.py`）提供人在环收件箱，是最接近"人工门"的东西，但无任务账本/技能分派/法定人数/超时拒绝缺省。

**（f）Tool/Skill ↔ 抽象 7**：`core/sys_operation/`（sandbox/fs/shell/code 操作 + tool_adapter + registry）、`core/foundation/tool/`、`harness/security/permission_engine/`（`core.py:1-24`：判定管线 = tiered 工具策略 allow/ask/deny ⊕ FileGuard 路径防护 ⊕ NetGuard 网络防护，取最严；审批走 rail，引擎只判权）、`harness/rails/security/`。**重叠**：能力经权限引擎验权后在沙箱执行、Skill 可打包。**差异**：权限是 YAML 分层策略（Claude-Code 风格），不是 biscuit 式可衰减凭证 ∩ cedar 策略；"一次性外部操作走副作用网关（意图记录+撤回窗口+幂等键+fencing 令牌）"未见到对应实现（全仓 grep 无 idempotency key/fencing token 概念）；技能签名装载验签在 skillhub 侧（见 3.8），内核侧未见强制。

**（g）Credential ↔ 抽象 4**：内核无对应物。最近的亲戚是 agent-protocol 的 A4P（见 3.9）——用户签名的 mandate，属于"用户→agent 授权"协议，不是"内核签发短期凭证、派生子 agent 只能收紧"的机制。

**（h）Trigger/Channel/Resident/Delivery/WorkOrder ↔ 抽象 8-13**：内核均无对应抽象。Trigger 在应用层（jiuwenswarm 的 cron/heartbeat）；Resident Agent 在应用层（JiuwenClaw 常驻+agent-memory 长期记忆）；Delivery 只有 agent-runtime 的部署管理；WorkOrder（SLA/验收协议/变更单/部分交付结算）完全缺失。

**（i）机制层对照（13 机制）**：CONWIP 投放闸、CSP 抽样状态机、升迁/降级引擎+熔断、金标注入器、渐放机制、止损指纹、副作用网关、可组合 Meter、通用日历、分级背压、四级漏斗、决策工件、JIT 护栏——**逐条核查均无对应实现**。最接近的两个：①`agent_evolving` 的 trainer/updater（`updater/single_dim.py|multi_dim.py`）是离线提示词/参数优化器，但它是"训练回路里直接改"，不是我们"JIT 只发射提案、人批准生效、永不干预执行、审计下限+优化集/评估集隔离"的护栏架构；②`rsi/artifact_rsi` 固定依赖 `agentdescent==0.4.6` 做 PUCT 程序搜索（pyproject.toml:37-46 注释说明 vendor 理由）——算法上与我们 JIT 的"消费 trace 提改进"同思想，但无护栏三件套。计量方面：iCode 的 F12 trajectory 展示 token 花费、agent-infer 管 KV cache 调度——是"记账/展示"不是"可声明可组合可拦截的预算"。

**agent-core 小结**：它是一个优秀的 **Agent 框架内核**（图引擎/会话/trace/评估/权限五件套齐全且有 1447 测试文件背书），但它是"把 agent 跑起来"的内核，不是"把工厂管起来"的内核。我们的 13 抽象中它实质性重叠 4 个（TaskGraph/Run 部分/Evaluation/Tool-Skill 部分），互补 2 个（session-vcs 的线性版本控制思想、trajectory 语料模型），其余 7 个抽象与全部 13 机制无对应。**且它是 Python——直接采用即违背我方 D5 拍板的"内核全部 Rust"语言基线。**

### 3.2 jiuwenswarm（JiuwenClaw）—— 应用层参考

常驻个人助手：channel 层四渠道（`jiuwenclaw/channel/`: feishu/dingding/web/xiaoyi）、gateway（cron 定时+heartbeat 唤醒+channel_manager）、evolution（`jiuwenswarm-main/jiuwenclaw/evolution/`: skill_optimizer/signal_detector/skill_call_operator——用户不满或出错时自动精炼技能）。**对我方价值**：①Resident Agent（抽象 10）+ Trigger（抽象 8）的一个真实产品形态参考，证明"常驻 agent+心跳任务+长期记忆"品类成立；②技能自演进的信号检测思路可作我们升迁梯（机制 3）输入信号的参考。**不引入理由**：应用层 Python，与我们 L3/L4 是竞品关系而非组件关系。

### 3.3 agent-studio —— L3/L4 参考

可视化画布+提示词优化+多版本对比+技能管理。对我方"运营者配置模板/开厂向导"（L4）与"工作台"有参考价值（尤其提示词多版本对比测试对应我们评估抽象的产品化）。Java 全栈，运维重（依赖 openEuler 文档站安装），**不引入**。

### 3.4 agent-runtime —— L2 部署参考

FastAPI 包 FastAPI+对话 API（/query /health /reset_conversation），DeploymentManager 三种策略（subprocess/docker/k8s），租户中间件。与我方 L2"适配器（只翻译不决策）"部分重叠但混入了决策（部署策略选择是它的核心逻辑，按我们边界规则 3 这属于该上浮到配方的判断）。**不引入**；其"部署记录+健康检查"模式可作我们 Resident Agent 生命周期租约的对照参考。

### 3.5 agent-memory —— 对 Resident Agent 的互补件

多类型记忆（画像/语义/情景/变量/摘要）自动抽取+AES-GCM 加密+版本化迁移+Mem0 兼容。我们的 Resident Agent（抽象 10）规定"独立记忆层"但未指定实现——**这是全生态中与我方缺口最互补的组件**。但它是 Python、绑定 Milvus/ChromaDB 等重存储，按我方语言基线只能作为 L2 适配器候选或设计参考。70★/21fork/10-12 仍在推送，活跃。

### 3.6 agent-infer —— 对推理层的互补件

vLLM 插件化（KV cache 池化/迁移、昇腾 NPU 原生）+ 语义路由 + AgentBench。我方 §7 选型已定 vLLM 为推理引擎——**agent-infer 是我方推理层最直接的互补候选**（agent 感知调度/前缀缓存正是我们多 agent 并发工厂的刚需），且 AgentBench 的"真实 agent trace 回放驱动基准"与我们"trace 是编译器语料"思想同构。Python、绑 vLLM 0.23.0+CUDA/昇腾硬件，属 L2 适配层候选。99★/15fork，活跃。

### 3.7 model-router —— 唯一"思想可直接抄"的 Rust 件

`crates/protocol|state|algorithms|runtime` 四层 + `crates/py` PyO3 绑定；`runtime/src/router.rs` 的 Router facade（from_config/route/report），`router_provider.rs` 北向契约；算法纯函数（同 (request,ctx) 同决策）、状态是可丢失 hint（远程态超时返回空 view 不失败请求）、router 不在流量路径上（host 自己调模型再 report outcome）。**对我方价值**：①这正是我方 Meter/供给路由（机制 8：路由统一消费"余量"信号）与模型网关（Bifrost）之间缺的那个"纯函数决策核"的形态——决策与执行分离、算法可换、状态可丢，与我方"适配器只翻译不决策"不同，这里是"决策内核纯函数化"，思想值得直接吸收进我方 L2 供给路由的接口设计；②**Rust 原生，与我方语言基线一致**。**否决引入的理由**：README 自述骨架期（weighted 算法/远程状态 gRPC/完整 PyO3 绑定均 stub），13★/6fork，无效果证据；我方若需要，按此契约自研的成本低于收养一个骨架并等它成熟。结论：**观望**（跟踪至算法与远程状态实装）。

### 3.8 skillhub —— Skill 抽象的分发层互补

六类资产（Skill/SwarmSkill/plugin/connector/expert/expert group）发布/版本化/presigned 下载/CLI 一体化，ClawHub 兼容 API，MySQL+FastAPI+前端。我方 Tool/Skill broker（抽象 7）管"验权+沙箱执行+签名装载"，缺"资产市场与版本分发"——skillhub 正好补这一层，且其"资产即版本化发布物"与我方配方库版本化同构。32★/10fork、有托管版。Python 全栈，按边界属 L2/L3 之间；**不引入**（运维一个 MySQL+前端的市场不在我方一期内核预算内），但其"六类资产类型学 + CLI 打包/校验/发布流程"值得抄进我方 Skill broker 的周边设计。

### 3.9 agent-protocol（A4P）—— Credential/决策工件的设计参考

A4P Python SDK：`src/a4p/intent/mandate.py`（IntentMandate/OperationMandate）、`user_signature/ed25519.py|webauthn.py`（用户生物签名授权）、`intent/token.py`+`usage_store.py`（SQLite intent token 用量账本）、授权服务器（`server.py`）+ 用户授权器（`user_authorizer.py`：approve/reject/sign_user_mandate）。**对我方价值**：①"用户签名的 mandate = 可验证的授权边界"正是我方 Credential（抽象 4）与"一切决策皆工件"（宪法 6）要的东西——A4P 的 mandate 结构（意图声明+操作范围+用户签名+用量账本）可直接作为我方 Human Station 决策工件与凭证衰减机制的设计蓝本；②ed25519/webauthn 双签名通道对应我方"人类参与者以角色进入、各带权限"的多参与者模型。Python、早期（无版本号信号）、115★ 主要是 MCP/A2A CPP SDK 的。**不引入，抄设计**。

### 3.10 deepsearch —— L3 配方层参考

DeepResearch 多步多源校验+段落级引用（segment-level provenance）+带图报告。对我方"研究报告产线"（用户一号场景之一）是现成配方参考；其"段落级溯源+置信度"与我方 Trace/Artifact 血缘思想一致但实现为引用标注。Python。**不引入**，列为我们研究产线的对标实现。

---

## 四、四问评估

**① 替我们省了什么？**
- 若整体采用 agent-core：可省"图引擎+会话状态+trace 接线+评估器"的从零编写——但代价是内核语言改为 Python（违背 D5 拍板）、且省下的每一样都要按我方 13 抽象重新对齐（他们的图无节点四型、会话 VCS 非内容寻址、trace 无防篡改、评估无三态），对齐工作量接近重写；更关键的是我方 13 机制在他们那里**一件都没有**，工厂运转规则仍要全自研。净省≈0，净欠（语言基线+抽象对齐+双栈运维）＞0。
- 若只取组件：agent-infer 可省 vLLM agent 化调度的一部分摸索（L2）；agent-memory 可省 Resident Agent 记忆层的设计（L2/参考）；skillhub 可省技能市场从零建（但我们一期不需要市场）；model-router/agent-dx 若成熟可省 Rust 路由核/分布式执行底座——但两者均骨架期，现在接入等于替他们填坑。
- 结论：**没有哪一层可以被它整体替掉**；能替的都是边角，且边角也有更轻的自研路径。

**② 效果证据（成熟度）**：作为 Agent 平台生态，证据充分——jiuwenswarm 7422★/1110 fork；agent-core 451★、1447 测试文件、PyPI 49 个发版且 2026-10-14 仍在发；agent-studio 189★；全生态 Apache-2.0、多仓库日级推送、有托管服务（agentichub.openjiuwen.com）、有企业交付形态（agentos-enterprise 打 submodule 包）。**但作为我方内核的替代件，效果证据为零**：没有任何一个组件解决过"工厂"问题（在制品控制、抽检升迁、副作用对账、预算拦截、配方驱动）。model-router（13★）与 agent-dx（3★）的 Rust 实现虽方向正确，README 自述 stub，无生产部署证据。

**③ 引入成本**：agent-core 引入 = Python 运行时进我方 Rust 内核（FFI 或双进程，trace/凭证/工件全部跨语言边界，宪法 1-3 的可复现性/可分析性保证被边界撕碎）+ 依赖树极重（agentdescent/anthropic/openai/transformers/pymilvus/fastmcp…，pyproject.toml:24-60）。agent-studio = Java+前端+MySQL。skillhub = FastAPI+MySQL+前端。agent-memory/agent-infer = Python+向量库/CUDA。model-router/agent-dx = Rust（语言零成本）但功能骨架期，接入即承担补全责任。运维半径：全生态默认 openEuler/Ubuntu+Docker+K8s，与我方 k3s+Karmada+Kueue 选型部分同构但工具链独立。

**④ 对接四层中哪层 + 退出成本**：
- agent-core → 名义上对接 L1，实则要求 L1 换语言换品类 → **不可对接**（退出成本=内核推倒重来，不可逆）。
- agent-infer / agent-memory → L2 适配层候选（推理/记忆 provider），接口隔离良好，退出成本低（换 provider 即可）。
- skillhub → L2/L3 之间（技能分发），退出成本中（要迁资产库）。
- model-router → 若成熟，对接 L2 供给路由的决策核（Rust crate 直链），退出成本低。
- agent-dx → 若成熟，对接 L1 Sandbox/durable 执行（Rust crate），退出成本中（执行底座替换动筋骨）。
- jiuwenswarm/deepsearch/sciencediscovery/iCode → L3/L4 配方与运营参考，零对接。
- A4P → 纯设计参考（Credential/决策工件蓝本），零对接。

---

## 五、结论与建议动作

**裁决：不引入。**

核心理由（一段话）：openJiuwen 是一个成熟度证据充分的 **Agent 开发平台生态**（华为背景、Apache-2.0、24 仓、旗舰 7.4k★、内核仓 1447 测试文件+49 个 PyPI 发版），但它属于"把 agent 跑起来"的框架品类，与我方"把工厂管起来"的内核品类只有部分交集——实质性重叠集中在 TaskGraph/会话/trace/评估/权限五件套，且每件的语义都不到我方宪法要求（无内容寻址工件、无防篡改 trace、无三态评估、无可衰减凭证）；我方 26 件内核预算中最独特的 13 个机制（CONWIP/CSP/升迁梯/金标注入/副作用网关/Meter/日历/JIT 护栏…）在它那里一件都不存在，"整体用它搭某子系统"没有证据基础；其主干为 Python/Java，直接采用即违背 D5 拍板的 Rust 内核基线。**不存在引入项，但存在三个值得执行的"抄"与两个"观望"**：

建议动作（按优先级）：
1. **抄设计（零成本，进我方设计语料）**：① A4P 的 mandate 模型（意图+范围+用户 ed25519/webauthn 签名+用量账本）→ 吸收进我方 Credential 与 Human Station 决策工件的接口设计；② model-router 的"决策与执行分离+算法纯函数+状态可丢失"契约 → 吸收进我方 L2 供给路由（Meter 消费余量信号）的接口纪律；③ iCode 的 F12 Trajectory 与 diff/rollback → 我方 L4 工作台"按版本定位事故"的产品化参考；④ session/vcs 的 rewind/fork 语义 → 我方 Run 检查点恢复的对照实现。
2. **观望 2 个 Rust 件（设复查触发条件）**：model-router 待"weighted 算法+远程状态+PyO3 绑定"脱 stub 且出现第三方生产采用证据后复查（对接 L2 路由决策核）；agent-dx 待检查点恢复/sandboxd/Activator 有公开 benchmark 或企业部署案例后复查（对接 L1 Sandbox/durable 执行）。两者成熟前不值得为其填坑。
3. **L2 候选备忘（不排期）**：agent-infer（vLLM agent 化调度/KV 池化，我方推理层互补）、agent-memory（Resident Agent 记忆层互补）——仅当我方相应产线真实需要、且 Rust 侧无等效件时，以适配器形态评估。
4. **配方层对标**：deepsearch（研究报告产线）、jiuwenswarm evolution（技能自演进信号检测）、agent_evolving/rsi（离线优化器形态，注意其无我方 JIT 护栏三件套，勿照抄其"训练回路直接改"）。
5. **否决日志登记**：本次否决"引入 openJiuwen agent-core 作为内核底座"——理由归档为：语言基线冲突 + 13 机制缺失 + 抽象语义不对齐。防止后续重复提案。

---

## 附：证据与方法备注

- 定位方法：GitHub API 无鉴权检索（`curl 'https://api.github.com/search/repositories?q=jiuwen'`，命中组织 openJiuwen-ai；后续 `orgs/openJiuwen-ai/repos` 拉全 24 仓清单；期间 core API 配额 60/h 用尽，改经 codeload tarball 与 raw README 完成，PyPI 信息经 pypi.org/pypi/openjiuwen/json）。变体逐个试的结果：openjiuwen/open-jiuwen/OpenJiuWen/jiuwen/九问/久闻中，仅 openJiuwen-ai 组织与 openjiuwen PyPI 包为真实命中；"九问""久闻"未找到对应开源项目（不构成幻觉引入）。
- 代码证据：本地解包 agent-core、jiuwenswarm、agent-studio、agent-runtime、agent-memory、agent-infer、model-router、skillhub、agent-protocol、deepsearch、agent-dx 共 11 个仓库（浅解包，读完即删）；本报告引用的 文件:行号 均来自这些解包（agent-core 位于 /tmp/ext-research/openjiuwen/agent-core-main，其余位于研究工作区 .ext-tmp/，已按规程清理）。
- 未运行其代码（未跑测试/未部署）：按评审规程"跑不起来就做代码级+文档级评估"执行；成熟度判断依据 stars/forks/发版节奏/测试文件数/README 自述，未验证其运行时行为——此项局限如实声明。
- git clone 直连在本环境失败（github.com:443 连接超时），改用 codeload tarball 等价完成浅克隆。
