# 外部项目研究：DeepSeek Harness（DSH）

- **研究对象**：DeepSeek Harness（dsh），`deepseek-ai/deepseek-harness`
- **结论**：**不引入（作为运行时底座）；部分借鉴**——抄四件设计：事件溯源 trace 纪律、副作用前 fail-closed 检查点语义、工具守护管线序列、profile 组合档案模型（以纯数据形态吸收，其 bundle=代码的形态不抄）。
- **调研日期**：2026-10-19
- **方法说明**：经 GitHub API / raw.githubusercontent.com / NVD API / GitHub Advisories API / GitHub Discussions 取证（本环境 git clone github.com 被网络阻断），**未运行其任何代码**。由并行研究代理执行（93 万 token、58 次工具调用），主代理复核关键裁决证据（CVE、逃逸链讨论、checkpoint 语义原文）。

---

## 一、项目是什么（身份事实）

**DSH** 是 DeepSeek AI 于 2026-08-13 以 MIT 协议开源的 agent harness，对标 Claude Code/Codex。GitHub API 实测（2026-10-19）：**254,222 stars / 30,728 forks / 22,395 commits**——两个月增速极端异常，数字以 API 为准记录在案，建议持续复核。当前版本 `0.2.1-rc.2`（2026-10-17），9/24–10/17 约 3.5 周内 10 个版本**全部为 prerelease，无 stable**；README 明告 "THERE WILL BE COMPATIBILITY-BREAKING CHANGES"。

实现：TypeScript monorepo（pnpm 11，Node ≥22.19/24，TS 6），`packages/` 下 **53 个子包**（core、llm、mcp、sandbox、session、telemetry、credentials、guard、host、subprocess、workflow 等），另有 `native/`（Landlock launcher + POSIX flock 原生插件）、`python/`、`vendor/cordis`（框架整体 vendor）。形态：CLI / Web UI / Electron / headless / TS+Python SDK / ACP server。

“一切皆插件”属实且彻底：模型适配器、工具注册表、技能、会话日志、沙箱、存储、调度、UI，**乃至 Agent Loop 本身**都是可替换插件（docs/architecture.md 原文："Every part of the product is a plugin, including the model adapter, the tool registry, the session log, and the agent loop itself. ... no privileged core to patch."）。`core/agent-loop` 只是默认 driver，挂在 `ctx.agentLoop` 服务键上。

特殊信号：`open_issues_count: 0` 且 issues 功能关闭、无 SECURITY.md（根目录只有 SAFETY.md 使用免责）、安全讨论区漏洞上报链接 404。

---

## 二、效果证据（成熟度）

| 维度 | 事实 | 证据 |
|---|---|---|
| 流行度 | 254k stars/30.7k forks（两个月，增速异常待复核） | GitHub API repo 元数据 |
| 发版节奏 | 3.5 周 10 版，全 prerelease；兼容性破坏常态化 | releases API；README 警告原文 |
| License | MIT | GitHub API license 字段 |
| 架构文档质量 | docs/ 成体系（architecture、cordis-primer、capability-seams、tool-execution-pipeline、persistence-catalog、session-format-status 及 subsystems/ 十余篇），宣称与设计多有一手原文支撑 | docs/ 目录直读 |
| 安全成熟度 | **自述未经安全审计**："has not undergone a security audit and must not be treated as secure or production-ready"；"Do not rely on DeepSeek Harness as the sole security control for untrusted workloads" | SAFETY.md 原文 |
| CVE | 已核实 4 个：CVE-2026-82533（**Critical 9.6**，本地控制面认证绕过——只验 Host 头不验连接来源，可调 `commands/execute`，patched 0.1.2-alpha.1）；CVE-2026-101132（loadProfile 路径穿越，LOW，vendor 未回应）；CVE-2026-101131（E2B_API_KEY 信任决策，LOW，vendor 未回应）；CVE-2026-108789（workflow 行为约束被操纵，MEDIUM 5.5，vendor 未回应） | GitHub Advisories API；NVD API |
| 社区安全报告 | 讨论 #8678（2026-10-02，已核实原文）：**"沙箱逃逸+审批绕过"完整链**——沙箱内 agent 读 `$DSH_HOME/.credentials.yaml` 明文浏览器签名密钥 → 离线伪造会话 cookie → 经未设门控制面 RPC 把自己会话设为 `danger-full-access` → 越出 workspace 写，"No human interaction occurring at any point"。仅 2 评论、**无维护者回应**；当前版本是否已修未核实 | discussions/8678 直抓 |

**诚实的保留**：①全部 pre-release，无第三方安全审计，漏洞上报通道事实缺失；②star 增速异常，社区真实采用度无法从 star 推断；③`native/` 实现语言未核实；④文档丰富但挂载期失败语义（fail-open/closed）未在文档规定——未核实。结论：**作为设计参照物证据充分；作为生产底座证据为负**。

---

## 三、四问评估（替我们省了什么 / 效果证据 / 引入成本 / 对接与退出）

**Q1 替我们省了什么？** 省的不是代码（TS ≠ Rust 内核），是**三个月设计试错**：(a) 事件溯源 trace 的完整范本——约 60 种事件的 envelope（type/seq/time/data + `ignorable` 标记）、严格 reader（遇未知事件**拒绝重建会话**而非静默丢弃）、`sessionFormatVersion` + 逐级迁移包（v0→v1…v3→v4 全套）+ 每类型 SHA-256 指纹的机器目录；(b) 副作用前 fail-closed 检查点拓扑（见 4.6）；(c) 工具守护管线序列（见 4.2）；(d) profile 组合档案模型（见 4.8）。这是设计期省钱，工程期不省。

**Q2 效果证据？** 宣称几乎都有文档/源码一手支撑："一切皆插件"（architecture.md + core/agent-loop 包）、审批 fail-closed（approval.md："A missing, non-owning, throwing, or non-conforming answerer becomes `unavailable` rather than opening the gate"）、llm/stream 短路拦截（llm-streaming.md）、会话格式四代迁移包齐全。**未被证实的核心宣称**："强制不可绕过"级隔离——插件进程内无隔离、direct 调用面存在、`danger-full-access` 内建、网络出口不管制；#8678 逃逸链无官方反驳。

**Q3 引入成本？** TypeScript/Node 22+/pnpm/TS6——直接撞语言基线（宪法第 8 条标尺）；53 包 monorepo + vendored Cordis + Node 原生插件，供应链面大且全 pre-release；无安全审计、1 Critical + 3 低中 CVE（三家 vendor 未回应）；兼容性破坏常态化 = 深度定制即上跑步机。只抄设计则成本≈零。

**Q4 对接哪层 + 退出成本？** 可对接的是**设计层，不是运行时层**。若强行作运行时：对接点为 profile 组合（裁掉 dsh-base、只装我方 llm 网关适配器 + 我方 sandbox provider + checkpoint policy）；数据层退出成本低（开放版本化 JSONL + 公开迁移包），但我方全部强制逻辑（llm/stream 监听器、guards、provider）绑定 DSH 专有事件词汇与 Cordis seam 契约（53 包 API、`cordis.patch.yml`、PluginEntryId/patchId、schemastery），迁移成本中高。

---

## 四、与我们底座的逐项对照（按 harness 评估契约 10 条标尺）

**4.1 模型调用强制网关（标尺 1）——半合格。** 官方路径收敛于 `ctx.llm` 适配器 seam；`llm/stream` waterfall 明文支持拦截短路（"yield your own chunks to short-circuit"），loop 构造的请求 deep-frozen 且为会话日志纯函数。**但** direct `ctx.llm.stream()` 调用面被文档承认存在，插件进程内运行无隔离墙——强制力是组合级的（我方 profile 只装我方适配器），不是架构级的。除非我方在网关侧持有唯一凭证使绕过=无法调用（外部约束），否则不满足"无法旁路"。

**4.2 工具强制 broker 进沙箱（标尺 2）——骨架对口，强制不足。** 守护管线成熟：`tool/call` 先落盘 → `tools/pre-execute`（权限+沙箱）→ monotonic guards → 执行 → `fs/write-intent` 门 → post-execute。沙箱为**同世界隔离**（bwrap/Landlock、Seatbelt、Windows restricted token），"Silent unconfined passthrough is never legal for a confined policy"。但 `danger-full-access` 是**内建逃生通道**（该模式消费者根本不调用 `ctx.sandbox`），且**网络出口明确不在沙箱策略词汇内**（"Network and process visibility are outside this vocabulary"）。进程外执行靠替换 seam provider（sandbox-ssh 是受支持形态）——改造点清晰，但根本约束同 4.1。

**4.3 副作用网关（标尺 3）——无对应物。** 其"副作用工具"概念止于检查点纪律与幂等键建议，无统一闸门、无撤回窗口、无 fencing 纪元。我们的 af-effect-gateway 在此方向更完整。

**4.4 trace 一等接口（标尺 4）——全场最强，直接可抄。** "Model-visible means logged"；append-only JSONL，存为带校验和的 zstd 连接帧，per-batch fsync，"only a resolved `flush` promises it survives a crash"；版本化 V4 + 逐级迁移 + SHA-256 指纹 + 严格 reader。另有 OTel 通道（自定信号 taxonomy，投递无 at-least-once 保证——未核实）。这是宪法 #3"Trace 是正式接口"的现成实证形态。

**4.5 短期凭证注入（标尺 5）——seam 干净，语义不匹配。** pull 式 per-operation 解析利于轮换；但存储为**明文托管文件**（#8678 逃逸链正是利用此点）、无 TTL、无按工具绑定（"Nothing lets you bind a credential to a specific tool"）、无衰减。与 biscuit"只可收紧"模型不兼容，需自建 provider。

**4.6 生命周期：检查点/恢复（标尺 6）——亮点，直接可抄。** 专用 checkpoint 插件在**模型请求前 / 顶层工具（外部副作用）前 / 步边界前**三个屏障同步落盘且 **fail-closed**（"a model adapter or top-level tool body does not run until the durable write succeeds"）；中断的副作用工具恢复为 `TOOL_OUTCOME_UNKNOWN` 且"requires verification or user confirmation"；副作用工具应转发 `exec.callId` 作幂等键（"guarantees durable execution intent, not exactly-once effects"——与我们 af-effect-gateway 幂等键语义合流）。可抢占语义未证实。

**4.7 fail-closed（标尺 7）——分治。** 观察者 fail-open（调度器必须捕获监听器异常继续派发）；决策点可 fail-closed（approval absent/throwing → `unavailable`，`ApprovalPolicy: 'never'` 连后注册 answerer 也无法绕过）。挂载期失败语义未规定。

**4.8 多档案按任务选择（profile 机制）——能力真实，形态不兼容。** profile = `$DSH_HOME/profiles/<name>` 独立目录 + 自己的 bundle 依赖树（pnpm 安装、可 `--save-exact` 锁死）+ `cordis.patch.yml` 补丁层；`dsh --profile <name>` 每次调用选择，`dsh-sdk-minimal` 先例证明可裁至裸核。**这正是用户"多版本按任务选"诉求的现成实现——但差异既有数据也有代码（bundle 是 npm 代码包），与我们"程序性是数据"的宪法冲突；我们只抄"具名档案+按任务选择"的语义，档案内容必须退化为纯数据（CUE 配方 profile）。**

**4.9 语言基线（标尺 8）——❌ TypeScript。** 无可争议的一票否决项。

**4.10 许可证与供应链（标尺 9）——✅ MIT；供应链面大**（53 包 + vendor + 原生插件，1MB pnpm-lock，全 pre-release）。

---

## 五、结论与建议

**裁决：不引入运行时；部分借鉴（抄设计、零运行时依赖）。**

三个一票否决：
1. **语言基线**：TypeScript/Node 全家桶，与"自研内核全部 Rust"拍板正面冲突；
2. **不可旁路性不成立**：进程内插件架构在失控插件面前无法满足宪法"无法绕过"的要求——`danger-full-access` 内建、direct 调用面存在、网络出口不管制；讨论 #8678 的逃逸链（读明文凭证→伪造会话→自设 danger-full-access→绕过审批，全程无人交互）正是这种架构的现实演示；
3. **生产就绪度为负**：官方自述未经安全审计、全 pre-release、破坏性变更常态化、漏洞上报通道缺失、3/4 CVE 厂商未回应。

**抄（进 L1 机制设计与 af-trace/af-harness 规格）：**
1. **事件溯源 trace 纪律**：envelope（type/seq/time/data + `ignorable`）、严格 reader 拒绝未知事件、`sessionFormatVersion` + 逐级迁移包 + SHA-256 schema 指纹机器目录——直接作 af-trace 事件格式的实证参照（docs/persistence-catalog.md、session-format-status.md）。
2. **副作用前 fail-closed 检查点拓扑**：模型请求前/副作用前/步边界前三屏障同步落盘；`TOOL_OUTCOME_UNKNOWN` 恢复语义；`exec.callId` 幂等键转发——与 af-effect-gateway 幂等键设计合流（packages/session/session-checkpoint-policy/README.md）。
3. **工具守护管线序列**：调用先落盘 → pre-execute（权限+沙箱）→ monotonic guards → execute → post-execute（accept/block/replace/add context）→ 冻结结果；审批 absent→unavailable 的 fail-closed（docs/tool-execution-pipeline.md、subsystems/approval.md）。
4. **profile 组合档案模型**：具名档案 + 按调用选择 + 可裁至裸核——以**纯数据形态**吸收为配方 profile（CUE 表达四元组集合与工具白名单），其 bundle=代码包的形态不抄（docs/cli-help.md、packages/boot/app-boot/README.md）。

**不抄 / 不引入**：运行时整体；Cordis 进程内插件框架（我们的插件边界在进程外——broker/沙箱/网关，与 pi 项目"进程内权限不可信"哲学一致）；凭证子系统（明文托管，语义不匹配）；OTel 自定信号 taxonomy（我们走 af-trace critical lane + OTel 非关键 lane 双轨既定方案）。

**风险**：①254k stars 两个月极端异常，复核其真实性；②#8678 修复状态未核实，若引入讨论再起需重估；③Cordis 为 Koishi/Satori 生态同源框架，其事件循环语义深挖不足，抄设计时以 DSH 文档原文为准、以源码复核为加固。
