# 外部项目评审：agentic-os-org/ANOLISA

> 评审立场：默认拒绝。一切以效果证据为核心。评审日期 2026-10-19。
> 研究对象：ANOLISA（Agentic Nexus Operating Layer & Interface System Architecture）。
> 代码证据：浅克隆（codeload tarball, main 分支）至本地工作副本后逐文件阅读；文末附获取与核验命令。
> 对照基线：`/home/pan-ding/workspace/临时工作区/temp2/产品设计_拍板版.md`（§1-2 已读）。

---

## 一、项目是什么：定位、组件、与 Anolis OS 的真实关系

### 1.1 定位

ANOLISA 是 **面向 AI Agent 负载的"服务器侧操作系统层"**（server-side operating layer），README 自述解决三个实际问题：终端入口、Token 成本、执行环境（README.md:88-92）。它的工作方式是**给已经存在的 Agent 框架加外挂**——保持用户已有的 Shell、Agent 框架和沙箱不变，通过 hook/adapter 接入 Claude Code、Codex、OpenClaw、Qoder、Hermes、Qwen 系等宿主（README.md:94-96，src/tokenless/README.md:20-32，src/aw/README.md:33-46）。

这与我们的底座是**不同范式**：我们是"数据流工厂"（TaskGraph 中间表示 + 工件内容寻址 + 订单驱动）；ANOLISA 是"给单个 agent 会话加 OS 级安全/观测/压缩外挂"。它没有 TaskGraph、没有 Artifact 内容寻址、没有 WorkOrder/SLA、没有 CONWIP 投放闸、没有 CSP 采样、没有三态 Evaluation——这些在我们的 13 抽象/13 机制清单里是主干，在 ANOLISA 里不存在对应物（通读组件清单与源码后的否定性结论）。

### 1.2 组件清单（AGENTS.md:12-27）

| 组件 | 路径 | 技术 | 平台 |
|---|---|---|---|
| cosh-ng（AI 原生终端） | src/cosh-ng/ | Rust | Linux 全功能 / macOS 有限 |
| agent-sec-core（OS 安全内核） | src/agent-sec-core/ | Rust + Python | **仅 Linux** |
| agentsight（eBPF 观测） | src/agentsight/ | Rust（eBPF） | Linux 全功能 / macOS 仅轨迹 |
| tokenless（上下文压缩） | src/tokenless/ | Rust | Linux / macOS（npm 分发二进制） |
| agent-memory | src/agent-memory/ | Rust | **仅 Linux** |
| os-skills（系统/运维技能包） | src/os-skills/ | Python/Shell | 全平台 |
| anolisa（安装 CLI） | distribution/anolisa/ | Rust | Linux + macOS(arm64) |
| SkillFS（FUSE 技能视图） | src/skillfs/ | Rust/FUSE | **仅 Linux** |
| ws-ckpt（btrfs 工作区快照） | src/ws-ckpt/ | Rust + TS | **仅 Linux** |
| ktuner（内核调参引擎） | src/ktuner/ | Rust | **仅 Linux** |
| aw（统一策略配置+本地服务） | src/aw/ | Rust | **仅 Linux** |

### 1.3 与 Anolis OS（龙蜥）的关系——核实结论

**ANOLISA 不是"龙蜥的 agentic OS 发行版"本体，而是把龙蜥/阿里云 Linux 生态当作头号目标平台的上层项目。** 证据：

- `src/agentsight/README.md` 安装一节列 "**Anolis OS / CentOS / RHEL:**" 作为受支持系统（yum/dnf 路径）；
- `src/os-skills/devops/sysom-diagnosis/references/supported-environments.md` 的支持矩阵含 "**Anolis OS 7/8**"；
- RPM 打包是一等公民：`sudo yum install anolisa` / `cosh-ng`（docs/QUICKSTART.md、src/cosh-ng/README.md:38-56），各组件带 `.spec.in` 模板；
- 血统为阿里系：OWASP 映射文档把源码基线钉在 `github.com/alibaba/anolisa` commit `3f4b22e3d645`（docs/user-guide/en/agent-security/owasp-agentic-top10.md:14-16），现组织名 agentic-os-org；
- 安全基线组件封装 `loongshield seharden`（src/agent-sec-core/README.md:38）——龙蜥/龙芯生态安全工具。

**对"运营者可提供 Anolis OS 环境、OS 层依赖视为已解决"这一前提的含义**：其 Linux-only 重依赖（eBPF、btrfs、FUSE、systemd）在 Anolis 上确实可满足；但这不改变架构范式不匹配的事实（见第四节）。

---

## 二、效果证据：成熟度与实测数字（含其自证的局限）

### 2.1 工程成熟度（GitHub API 实测，2026-10-19）

| 指标 | 数值 | 命令 |
|---|---|---|
| stars / forks | 630 / 149 | `curl -s https://api.github.com/repos/agentic-os-org/ANOLISA` |
| 合并 PR | 3304 | `curl -s 'https://api.github.com/search/issues?q=repo:agentic-os-org/ANOLISA+is:pr+is:merged'` |
| License | Apache-2.0 | 同上（repo metadata） |
| 创建 / 最后 push | 2026-03-30 / 2026-10-19（评审当日） | repo metadata `created_at`/`pushed_at` |
| 语言构成 | Rust ~50MB、TS ~12MB、Python ~7.7MB、C 6MB | `/languages` |
| 发版节奏 | tokenless 已发到 v0.8.7（tags: tokenless/v0.8.0→0.8.7）；stack 版本 1.5（2026-09-24） | `/tags`、CHANGELOG.md:9-22 |
| 开放 issue | 1531 | repo metadata `open_issues_count` |

**测试资产**（本地工作副本 `find` 统计）：agent-sec-core 237 个测试文件、cosh-ng 136、agentsight 74、tokenless 69、skillfs 64、ws-ckpt 9。工程深度真实存在，不是空壳项目。

### 2.2 能力实测数字（README 自述，均可在仓库找到对应模块）

- **tokenless 压缩**（README.md:126-136）：工具响应 -65.8%、工具 schema -47.3%、全链路 -62.9%；ResponseCompressor 46.85µs、SchemaCompressor 11.44µs、全链路 198.91µs；单个编码任务实测省 317K tokens（40.5%，AgentSight 测量）。
- **tokenless 各策略 fixture 级数字**（src/tokenless/README.md:41-51）：JSON 响应压缩 36.3% lossless、TOON 17.0%、RTK 命令重写 60-90%。
- **OWASP Agentic Top 10 覆盖**：7 Full / 3 Partial（docs/user-guide/en/agent-security/owasp-agentic-top10.md:31-44），AARM Registry "Aligned"（README badge / agent-sec-core README.md:12-16）。
- **benchmark 设施**：benchmark/ 目录含 SWEBench、TerminalBench、ClawEval 三个 runner（benchmark/README.md:9-13）——但**仓库内没有公开跑分成绩**，不能当作效果证据引用。

### 2.3 其自证的局限（诚实度是加分项，但直接影响"效果证据充分性"）

- tokenless README 明说：上述数字是"仓库参考 fixture 上的孤立结果，**不是产线区间、也不可叠加**"（src/tokenless/README.md:65-71）；Git diff 压缩"**稳定的整 agent token 节省尚未确立**"（同文件:45）；
- 整会话节省 = 压缩率 × 工具响应占比；其自己的示例：60% 压缩率 × 20% 占比 = **12% 整会话节省**（src/tokenless/README.md:107-116）；
- OWASP 映射明说："source-based architectural **self-assessment**，不是 OWASP 认证，**文档变更时未运行测试**，运行时安全测试与对抗性部署验证未做"（owasp-agentic-top10.md:20-24）。

**证据分级结论**：工程成熟度证据充分（可复验）；端到端效果证据是**组件级 + 自测级**，无第三方复现、无生产区间。作为"机制设计参考与移植来源"够格；作为"效果保证的来源"不够——任何引入都必须在我们自己的负载上复测。

---

## 三、四问评估

### 3.1 替我们省了什么

**能省的（机制设计层面，均为我们设计中已声明要做的能力的成熟参考实现）：**

1. **可逆工具输出压缩**（tokenless，Protocol v2）。我们 Meter 管预算，但"花掉之前先减少浪费"这条路径我们只有原则没有设计。ANOLISA 给出一套完整可抄的设计：生命周期四段（BeforeModel schema 处理 / PreTool RTK 重写 / PostTool 路由 / 授权 Retrieve，src/tokenless/README.md:9）、**可逆 stash + `tokenless retrieve HASH` 恢复**（src/tokenless/README.md:48,118）、CJK 感知的归一化 token 估算（src/tokenless/crates/tokenless-protocol/src/lib.rs:13-30，`PROTOCOL_VERSION=2`、`heuristic-v1` 估算器）、以及"候选不更小就原样透传"的保守门限（src/tokenless/README.md:96-100）。这套东西自研需要数周设计+试错，且与内核同为 Rust。
2. **Skill 签名后的漂移重判模式**（Skill Ledger）。我们宪法只写了"Skill 带签名，装载时验签不可跳过"（设计文档 §4 抽象 7）；ANOLISA 多做了我们没写的一环：签名 Skill **内容变更后、再次使用前**报告 `drifted`，重扫把阻塞性发现记为 `deny`（README.md:196-199）；实现为 Ed25519 签名的 append-only 版本链（src/agent-sec-core/agent-sec-cli/src/agent_sec_cli/skill_ledger/core/version_chain.py:1-60，`.skill-meta/versions/v\d{6}.json` + snapshot 结构）。这对我们的 Skill broker 是直接的强化参考。
3. **防护式回滚的 fencing 判定**（ws-ckpt × cosh-ng）。回滚前"在写锁下重算 live diff，generation 或 diff 变化即拒绝"（src/cosh-ng/README.md:305-312）、"`On` 策略无精确 checkpoint 证据即 fail closed"（src/cosh-ng/README.md:292-297）——与我们副作用网关的 fencing 令牌/幂等键同构，可作交叉验证的参考实现。
4. **工具执行的人工批准纪律**。cosh-ng Gateway 代理工具执行、审批卡、`allow_once` 且"**COSH never creates provider `allow_always` rules**"（src/cosh-ng/README.md:305-309）——与我们 Human Station/副作用网关"超时安全缺省是拒绝"同向，细节可参考。

**省不了的（整体性结论）：** 它的 Task/任务模型、观测、沙箱都无法承担我们内核的职责——没有数据流图、没有工件寻址、没有订单/SLA、没有评估三态、没有凭证衰减、没有 trace 防篡改锚定。**不存在"某子系统整体用它搭"的证据支撑**（详见 3.4）。

### 3.2 效果证据（引入决策视角）

- 对"抄 tokenless 压缩机制"：组件级实测数字存在（fixture 65.8%/47.3%/62.9% + 单任务 317K/40.5%），机制可逆、保守门限、纯 Rust；**但整会话效果未经第三方复现，其文档自述区间约 12% 量级**。判定：**值得抄设计，引入前必须在我们工具密集负载（编译/测试/检索占比高）上复测**——我们的工具响应占比大概率高于其示例的 20%，潜在收益更高，但这是推测不是证据。
- 对"抄 Skill Ledger 漂移模式"：实现完整（Ed25519 + 版本链 + 扫描器 + drift/deny 判定 + SkillFS 激活联动），测试伴随（237 个测试文件在 agent-sec-core）；判定：模式级证据充分。
- 对"整体引入任何组件"：效果证据不充分——Linux-only 重依赖（eBPF/btrfs/FUSE/systemd/RPM）直接违反我们"部署形态无关"宪法（设计文档 §2.1）；且范式不匹配（外挂 vs 工厂底座）。

### 3.3 引入成本

- **语言**：Rust 主体，与内核同语言——这是唯一显著的正面因素。
- **依赖**：agent-sec-core 需 bubblewrap+seccomp+root daemon+Python CLI；agentsight 需 eBPF/root/CAP_BPF；ws-ckpt 需 **btrfs**；skillfs 需 **FUSE**；全线需 systemd/RPM（AGENTS.md:24-26 明示五个组件仅 Linux）。每一条都与"本地/云/混合是配置不是架构"冲突。
- **运维面**：多 daemon 模型（agent-sec-daemon root 常驻、cosh-gateway system service、ws-ckpt daemon）；1531 开放 issue 说明上游仍在高速变动，跟随成本高。
- **人力**：若只抄两个机制（tokenless 压缩 + skill 漂移重判），是**读代码+移植+复测**级别的工作量，不是集成运维级别。

### 3.4 对接四层中的哪层 + 退出成本

| 借鉴物 | 对接层 | 退出成本 |
|---|---|---|
| tokenless 可逆压缩机制 | **L2 适配器**（模型调用路径上的压缩 provider，"只翻译不决策"，阈值/开关进 L3 配方参数）或直接作为内核模型网关内的纯函数组件 | 低——纯函数式、可插拔、无外部依赖 |
| Skill Ledger 漂移重判模式 | **L1 内核** Skill broker 验签逻辑增强（装载验签 → 变更重扫 → drifted/deny 再放行） | 低——模式级改动，不引入运行时依赖 |
| ws-ckpt fencing 判定 | 仅作我们 Run 检查点/副作用网关的**设计参考**，不引入组件 | 零 |
| agentsight eBPF 计量 | 不引入内核；其"无 eBPF 模式：扫 JSONL 会话→ATIF v1.7→SQLite"（src/agentsight/README.md:86-88, 480）可作 L2 观测适配器参考 | 零（仅参考） |
| cosh-ng / aw / ktuner / agent-sec-core 整体 | **不引入**（终端优先的交互形态、统一策略服务、内核调参均非我们底座所需） | — |

**退出成本总判**：若按上表窄口径引入，最大沉没成本是 tokenless 压缩的移植+复测工时（数周级）；随时可回退到"不压缩"，无数据锁定（stash 是本地纯数据）。

---

## 四、分项对照：Tool broker / Sandbox / Meter / 进程任务模型

### 4.1 Tool broker（我们的"工具经进程外 broker 验权后沙箱执行"）

ANOLISA 对应物是 cosh-ng Gateway：工具调用经 Gateway 审批后执行，Managed Core 用封闭的 `workspace-write-v1` profile，只暴露 `ask_user_question` 和 `write_file`，每次写都是 Runtime 原生权限决策，Gateway 批准+checkpoint 屏障后才执行；固定工作区文件系统拒绝父目录穿越/绝对路径/symlink 逃逸（src/cosh-ng/README.md:299-304）。**评价**：审批卡的交互形态我们不缺（Human Station）；"写操作集合最小化 + 路径逃逸防护"值得抄进我们的 Sandbox/Tool broker 对接测试。

### 4.2 Sandbox（我们的 Sandbox 抽象）

对应物：agent-sec-core 的 linux-sandbox（bubblewrap+seccomp）+ V2 Policy/Scope/Binding 管理（PAP 状态存 SQLite，root-only 管理，`--policy-admin-uid` 可授权非 root，src/agent-sec-core/README.md:79-85）。策略类型定义清晰：网络 Restricted/Enabled（linux-sandbox/src/policy.rs:24-36）、文件系统 Read/Write/None 三级 + Restricted/Unrestricted/ExternalSandbox 三种沙箱形态（src/policy.rs:50-114）。**评价**：Policy/Scope/Binding 三分作为我们 Sandbox 配置 schema 的参考是合格的；但组件本身（bubblewrap+seccomp+root daemon）引入即违反部署中立，不引入。

### 4.3 Meter（我们的可组合计量）

对应物：agentsight 的 token 计量（eBPF uprobe 截获 SSL 明文 → HF tokenizer 精确计数，src/agentsight/README.md:13,44-47）+ tokenless-stats。**评价**：这是"测量"不是"预算拦截"——我们的 Meter 是声明式额度形状 + 余量信号 + 路由消费（设计文档 §5 机制 8），ANOLISA 给不了拦截语义；反过来它的 eBPF 精确计量可作为我们"供给计量 provider"的极端精确参考，但 root/eBPF 前提与部署中立冲突，仅参考。

### 4.4 进程/任务模型（我们的 Run）

对应物：cosh-ng 持久 Task——提交即返回 durable Task ID，Gateway/Runtime 由 system service 持有，退出 shell/断连 SSH 不取消 Task，重连后 `/task list/show` 读持久进度（src/cosh-ng/README.md:281-285）；checkpoint 策略 Auto/On/Off + "无精确证据 fail closed"（:292-297）；Gateway 重启不静默重放 ACP 会话，"suspend or lost 并要求显式 retry"（:285-287）。**评价**：它的 Task 是"终端工作区里的长任务"，我们的 Run 是"领短期凭证、有生命周期四态、可检查点暂停恢复、可被软驱逐"的生产执行单元——粒度与语义都不同；可借鉴的是其**断连不取消 + 不静默重放 + fail-closed checkpoint** 三条纪律，均与我们的设计同向，属交叉验证而非能力替代。

---

## 五、结论

**裁决：部分引入。**

**核心理由**：项目真实存在、工程成熟度充分（630 stars、3304 合并 PR、Apache-2.0、评审当日仍在提交、五组件合计 570+ 测试文件），且与龙蜥生态关系属实（Anolis OS 7/8 是头号支持平台、RPM 一等公民、loongshield 封装、阿里血统）。但其架构是"给既有 agent 框架加 OS 层外挂"（终端优先、Linux-only、eBPF/btrfs/FUSE 重依赖），与我们的数据流工厂底座范式不同，**不存在整体替代我们任何子系统的效果证据**。真正有价值的是两个可直接抄的机制设计：

1. **tokenless 的可逆压缩**（Protocol v2 四段生命周期 + 可逆 stash/retrieve + CJK 感知 token 估算 + 保守门限）——以 L2 压缩适配器形态接入我们的模型调用路径，阈值与开关进 L3 配方；引入前必须在我们工具密集负载上复测（其自述整会话节省约 12% 量级，未叠加、非产线区间）。
2. **Skill Ledger 的漂移重判模式**（Ed25519 签名 + append-only 版本链 + 变更后重扫 drifted/deny 再放行）——补强我们 Skill broker"装载验签"之后的"变更复检"一环，模式级移植，无运行时依赖。

ws-ckpt（btrfs）、agentsight（eBPF/root）、cosh-ng/aw（终端/策略服务形态）**不引入**，仅作设计参考；后者与部署中立宪法冲突。

**建议动作**：① 安排一次 tokenless 压缩机制在我们真实工具负载上的复测实验（L2 适配器 + 配方开关，A/B 对比整会话 token 账单）；② 内核侧把"签名 Skill 变更后重扫再放行"写进 Skill broker 的验签流程设计；③ 其余组件记入参考档案，不跟踪、不集成。

---

## 附：本评审的执行与核验记录

- 项目定位：`curl -s 'https://api.github.com/search/repositories?q=ANOLISA'` → `agentic-os-org/ANOLISA`（注意：组织名是 `agentic-os-org`，ask 中给的 `agentic-os` 组织存在但是另一个组织，其下为 Sec-ConvAgent 等无关项目）。
- 代码获取：`curl -sL https://codeload.github.com/agentic-os-org/ANOLISA/tar.gz/refs/heads/main`（git clone 直连 github.com:443 失败，改走 codeload；/tmp 被其他进程占满且会被清理，工作副本置于 home 目录，评审结束已删除）。
- 元数据/贡献者/tags/releases/合并 PR 数：GitHub REST API（未鉴权）实测，数值见 2.1。
- 测试文件统计：本地工作副本 `find` 计数（口径：`test*.py`/`*_test.py`/`test_*.rs`/`tests/` 下 `.rs`）。
- 未执行：完整构建与测试套件（需 Alinux/RPM/root/eBPF 环境，超出本评审范围；按 ask 要求做代码级+文档级评估，不硬跑）。仓库内 benchmark runner 无公开跑分，未引用为效果证据。
