# Harness 选型横评与配置建议书

- **目的**：回答"harness 怎么弄"——工厂内实际工作的 agent 用什么执行外壳、怎么配、个体差异落在哪。本文件是拍板输入，拍板后才进基线。
- **调研日期**：2026-10-19
- **方法**：DSH 深挖（见同目录 [DSH.md](DSH.md)）+ 11 个开源 harness 横评（Codex CLI / Goose / OpenHands / Gemini CLI / opencode / Aider / Claude Code / smolagents / deepagents / pi / Antigravity CLI），全部经 GitHub API 与一手文档取证；默认拒绝姿态；查不到的标"未核实"。
- **调研投入**：两路并行研究代理（合计约 210 万 token、108 次工具调用），主代理复核裁决证据。

---

## 一、裁决建议（一句话）

**harness 自研（af-harness，Rust crate），不引入任何外部 harness 运行时；强制点做进进程拓扑而非配置项；个体差异全部落在四元组+配方 profile（纯数据）；DSH/Codex/Claude Code/OpenHands/pi 共抄 15 件设计。**

理由一句话：横评证实**业界没有任何项目开箱提供"模型调用结构上不可旁路"的强制点**——我们宪法第 1-3 条（网关验预算 / broker 进沙箱 / 副作用网关）在业界无现成实现，唯一可靠路径是把强制做进进程拓扑本身，而这只有自研能做。

---

## 二、评估契约：harness 内核义务 10 条标尺（首次成文，建议固化为准入判据）

| # | 标尺 | 来源 |
|---|---|---|
| 1 | 模型调用可**强制**经我方网关验预算（无法旁路，非"支持配置"） | 宪法 #9 + Meter |
| 2 | 工具调用可强制经进程外 broker 进沙箱 | 抽象 7（Tool/Skill） |
| 3 | 外部副作用可强制经副作用网关 | 宪法 #8 + 机制 7 |
| 4 | trace 一等接口：结构化、版本化、关键事件同步落盘零丢失 | 宪法 #3 |
| 5 | 可注入短期凭证，权限只收紧 | 抽象 4（Credential） |
| 6 | 执行单元生命周期：检查点/暂停恢复/可抢占 | 抽象 1（Run） |
| 7 | fail-closed 失效语义 | 判据：不可旁路测试 |
| 8 | 语言基线 Rust | 实施方案 §二拍板 |
| 9 | 许可证 MIT/Apache 级 + 供应链可审 | deny.toml 纪律 |
| 10 | 可复现：确定性、版本贯穿 | 宪法 #1/#7 |

---

## 三、候选横评总览

| 项目 | 语言 | 许可证 | Stars(10-19) | 1 强制网关 | 2 强制broker | 3 副作用 | 4 trace | 5 凭证 | 6 生命周期 | 7 fail-closed | 8 Rust | 9 许可 | 10 复现 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Codex CLI | **Rust** | Apache-2.0 | 129,902 | ⚠️ | ⚠️ | ⚠️沙箱内可强制 | ✅ | ✅auth.command | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ |
| DSH | TS | MIT | 254,222* | ⚠️组合级 | ⚠️骨架对口 | ❌无对应 | ✅**最强** | ⚠️明文 | ✅检查点fail-closed | ⚠️分治 | ❌ | ✅ | ⚠️ |
| OpenHands SDK | Python+TS | MIT | 91,270/1,274 | ⚠️部署边界 | ⚠️容器边界 | ⚠️部署层 | ✅ | ✅方向 | ✅方向 | ⚠️ | ❌ | ✅ | 未核实 |
| Goose | **Rust** | Apache-2.0 | 55,436 | ⚠️ | ❌ | ❌ | ⚠️ | 未核实 | ⚠️ | ❌ | ✅ | ✅ | ❌ |
| opencode | TS | MIT | 217,334 | ⚠️ | ❌同进程 | ❌ | ✅方向 | ⚠️ | ✅方向 | ⚠️ | ❌ | ✅ | ❌ |
| pi | TS | MIT | 116,361 | ⚠️ | ❌边界外置 | ❌ | ✅契约+一致性测试 | 未核实 | ✅durable | ❌有意fail-open | ❌ | ✅ | ✅Nix钉版 |
| Gemini CLI | TS | Apache-2.0 | 107,454 | ⚠️ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| smolagents | Python | Apache-2.0 | 29,927 | ⚠️ | ⚠️后端可插拔 | ❌ | 未核实 | 未核实 | ⚠️ | ❌ | ❌ | ✅ | ❌ |
| deepagents | Python | MIT | 30,416 | ⚠️ | ⚠️ | ❌ | ⚠️绑LangSmith | 未核实 | ✅LangGraph | ⚠️ | ❌ | ✅ | ⚠️ |
| Aider | Python | Apache-2.0 | 49,636 | ⚠️ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Claude Code | 闭源 | 专有 | — | ⚠️设计最强 | ⚠️hooks协议 | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | 未核实 |

*DSH star 增速异常，记录在案待复核。

**排除裁决（一句话各一）**：Gemini CLI——2026-06 已被闭源 Antigravity CLI 取代，生命周期终结；Aider——近 5 个月零提交；Claude Code/Antigravity——闭源专有（仅作架构参照）；Goose——默认 Completely Autonomous + 官方承认"runs with the same permissions as your user account and is not sandboxed at the OS level"，正面撞标尺 2/7；smolagents/deepagents——Python 库形态无强制边界，deepagents 观测绑定商业 LangSmith。

**关键全局结论**：横评中**没有任何候选**在模型调用层面提供开箱即用的结构级不可旁路注入点。最接近的三个位置：(a) Claude Code 企业 managed settings（闭源）；(b) Codex 沙箱强制网络代理（可锁流量，但 `danger-full-access` 可整体旁路）；(c) OpenHands/pi 的 agent-server 独立进程模式（模型调用发生在服务端进程内，若该进程由我方构建部署即构成部署级强制）——**(c) 正是我们自研路线的同构验证**。

---

## 四、最终配置建议：af-harness（自研 Rust 执行器外壳）

### 4.1 形态

新增 `af-harness` crate（Rust），是全厂唯一执行模型调用循环的进程形态；所有"调模型的"图节点共用这一个外壳。它不是框架，是**承载内核义务的薄壳**：loop 逻辑是内核代码（不在插件面开放），插件面只开在 L2 适配器层（契约内插件，沿用设计纪律"只翻译不决策"）。

### 4.2 强制点做进进程拓扑（核心决策）

横评的头号教训：配置项级强制都可被降级（DSH 的 danger-full-access、Codex 的同名开关、Goose 的默认自治）。af-harness 因此把四条强制做进**进程与网络拓扑**，而非 harness 内部开关：

1. **模型调用只存在于 harness server 进程内**；该进程网络出口经部署策略只通我方网关（Bifrost），网关持有唯一上游凭证——绕过网关=无凭证可调（借鉴 OpenHands agent-server 模式 + Codex 网络代理结构 + DSH 4.1 节的"外部约束"启示）。CubeSandbox 的 L7 SNI allow 能力（poc-sandbox 已验）是现成实现件。
2. **工具调用只经 broker → CubeSandbox**；harness 进程自身不注册任何本地工具执行能力（结构上无 `danger-full-access` 等价物——不实现这个词汇）。
3. **外呼只过副作用网关**：工具白名单里凡声明"一次性外部操作"的能力，broker 拒绝直执，只接受经副作用网关签发的执行票。
4. **trace 双轨既定方案**：critical lane af-trace 同步落盘（宁停勿丢），落盘失败=该步不执行（fail-closed，抄 DSH 检查点语义，见下）。

### 4.3 个体差异的承载（回答"我们会有大量自配需求"）

全部走数据，四层落位：

| 需求 | 落位 | 形态 |
|---|---|---|
| 按任务配工具 | 四元组·工具集 + 凭证工具白名单 | CUE 数据 |
| 按任务配上下文 | 四元组·上下文模板 | CUE 数据 |
| 按任务选模型 | 四元组·端点（经 Meter 计量路由） | CUE 数据 |
| 按任务调策略 | 四元组·策略参数 | CUE 数据 |
| **具名档案按任务选择**（用户核心诉求） | **配方 profile** = 四元组集合+工具白名单的具名组合，L3 配方层发行、L4 运营者 fork | CUE 数据，部署期预编译 JSON（既定路线） |
| 真有不同执行循环 | Task Graph 注册新节点类型（宪法内路径，仍挂同一套内核义务） | 内核注册，非第二 harness |
| harness 自身多版本并存 | 渐放机制（机制 5：0% 起点+按评估谓词放量），版本号进 trace | 既定机制 |

**关键边界**：profile 差异只许是数据。DSH 的 profile 里 bundle 是 npm 代码包——那条不抄；我们的配方 DSL 已有纪律（类型化受限、无图灵完备、可静态校验）。

### 4.4 抄设计清单（15 件，零运行时依赖）

**DSH 4 件**（详见 [DSH.md](DSH.md) §五）：
1. 事件溯源 trace 纪律：envelope+`ignorable` 标记、严格 reader 拒未知事件、版本化+逐级迁移+SHA-256 指纹目录 → af-trace 事件格式实证参照；
2. 副作用前 fail-closed 检查点三屏障（模型请求前/副作用前/步边界前）+ `TOOL_OUTCOME_UNKNOWN` 恢复 + `exec.callId` 幂等键 → 与 af-effect-gateway 幂等键合流；
3. 工具守护管线序列（先落盘→pre-execute→monotonic guards→execute→post-execute→冻结）+ 审批 absent→unavailable；
4. profile 具名档案语义（以纯数据形态吸收）。

**Codex CLI 6 件**：
5. `auth.command`：外部命令取 bearer token + 定时刷新 → 我方 biscuit 短期凭证注入协议范本；
6. 沙箱强制网络代理（`domains.allow/deny` + admin_url）→ 副作用网关流量层实现模板；
7. execpolicy Starlark 前缀规则 + 规则内嵌用例**载入期自检** → CUE/CEL 规则可测试性参照；
8. MCP `required=true` 初始化失败即拒启 → broker 装载 Skill 的 fail-closed 细节；
9. 管理员锁文件语义（受管配置单文件生效、他处静默无效）→ L4 运营者空间覆盖纪律参照；
10. `shell_environment_policy` 默认剔除 `*KEY*/*SECRET*/*TOKEN*` 环境变量 → 沙箱环境卫生基线。

**Claude Code 3 件**（文档层，不可引入）：
11. 多级 managed settings **合并式**托管（受管项叠加，用户无法本地关闭）；
12. `allowedProviders` 白名单：非白名单 provider 会话**启动即拒绝**；
13. PreToolUse 阻断协议（exit code 2 / JSON `permissionDecision: allow|deny|ask|defer` + `updatedInput` 参数改写）——已是事实标准，**建议 broker 协议兼容该语义**，官方"硬 allow/deny 走 permission 层、hook 是建议层"的分层警告直接写进 broker 规格。

**OpenHands/pi 各 1 件**：
14. OpenHands：agent-server 独立进程边界 + `Local→Docker→Remote` 同代码切换部署形态 → af-harness 部署形态中立（宪法 #5）的实证参照；
15. pi：`pi-telemetry` 的"遥测契约+类型化 schema+参考适配器+**一致性测试**" → af-trace 版本化的验收形态；其 README"进程内权限系统不可信，强制边界放进程外"哲学声明可作内部立项引证。

### 4.5 落地建议（波次插入点）

- **波次 4 增列一项**：af-harness **契约先行**——事件 schema（对齐 af-trace）、义务 checklist（本文件 §二 10 条）、broker 协议对齐 PreToolUse 语义。契约评审通过后再写 loop 本体。
- loop 本体规模预期小：内核义务已由 af-credential/af-meter/af-effect-gateway/af-trace/CubeSandbox 承载，harness 只是把它们缝进一个 ReAct 循环（PenguinHarness 研究显示此类外壳"比我们 L1 薄 8 个抽象"）。
- 同步动作：把 §二 10 条标尺固化为 harness 类组件的准入判据文档（后续任何 harness 候选复用，含"第二运营者"出现时的复检）。

---

## 五、风险与未核实项

1. DSH 254k stars/两个月增速异常，其社区信号不应作为任何裁决依据（本次裁决未依赖它）；
2. DSH 讨论 #8678 逃逸链修复状态未核实；若 DSH 后续修复安全姿态并稳定，可重启评估——但语言基线（标尺 8）不随其演进改变；
3. Codex 企业 Managed Configuration 能否管理员锁死 model provider 未核实（文档需登录）——不影响裁决（我们自研），仅影响抄设计清单第 9 条的参照强度；
4. "注册新节点类型"路径的真实需求目前为零——按 rule of three，第三个独立场景出现前不升格机制；
5. 本建议未覆盖 harness 的 UI/人机交互面（人工工位已有 af-station），工作台与 harness 的接口留待波次 4 契约评审。

## 六、建议落账动作（待 owner 拍板）

1. **拍板项**：af-harness 自研立项（Rust crate，契约先行，波次 4 增列）；
2. **否决日志新增一行**：`2026-10-19 | DSH 运行时 | 进程内插件不满足不可旁路（#8678 逃逸链实证）+ TS 违语言基线 + 未审计全 pre-release | 设计/外部项目研究/DSH.md`；
3. **否决日志新增一行**：`2026-10-19 | 外部 harness 横评（10 项） | 业界无"模型调用结构级不可旁路"现成实现；Codex/Goose 为仅有的 Rust 候选但强制点均为可降级配置 | 设计/外部项目研究/harness横评与配置建议.md`；
4. **设计语料库更新**：15 件抄设计清单按既有"抄设计、零运行时依赖"口径分发到 af-trace / af-effect-gateway / broker / af-harness 规格责任人。
