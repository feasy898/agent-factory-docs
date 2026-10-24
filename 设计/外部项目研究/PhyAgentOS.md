# 外部项目研究 · PhyAgentOS

> 评审人立场：默认拒绝。结论只认效果证据。
> 评审日期：2026-10-19
> 变体搜索：PhyAgentOS / Phy-Agent-OS / phyagent / Physics+Agent+OS（`curl https://api.github.com/search/repositories`，2026-10-19 执行）

---

## 一、项目身份核验（found = true）

**PhyAgentOS/PhyAgentOS-core** —— 真实存在，已拉到本地逐文件读过。

| 项 | 值 | 来源 |
|---|---|---|
| 仓库 | `github.com/PhyAgentOS/PhyAgentOS-core` | GitHub Search API，`total_count=17`（PhyAgentOS 变体）、`8`（Phy-Agent-OS 变体），主仓两次均排第一 |
| Stars | 2987 | 同上 API 返回 `stargazers_count: 2987` |
| License | MIT | API `licenses[0].spdx_id = MIT`；`pyproject.toml:7` `license = {text = "MIT"}`；`LICENSE` 在树根 |
| 语言 / 规模 | Python，163 个 `.py`，42,701 行（含 tests 37 文件 9,455 行） | `find . -name "*.py" \| xargs wc -l` |
| 最近推送 | 2026-10-18（评估前一天） | API `pushed_at` |
| 发版节奏 | v0.2.2 2026-08-21 → v0.2.3 2026-08-27 → v1.0.0 2026-08-30 → v1.1.0 2026-10-09 | `README.md` News 表 + `CHANGELOG.md` |
| 出处 | 中山大学 HCP Lab + 鹏城实验室 + X-Era Lab；技术报告 arXiv 2607.16636；GOSIM 深圳 2026 Spotlight | `README.md` 结尾、`README.md:335-347` |
| 生态活跃度 | 第三方插件已出现（ReKep 真机、Unitree G1 语音、Franka FR3、XLeRobot 适配器） | GitHub Search 返回，独立作者 repo |

**注**：本次 GitHub API 在后半段触发未鉴权限流（`API rate limit exceeded for 223.198.164.239`），因此 **contributor 数量与 release 列表未取到**；发版信息来自仓库内 `CHANGELOG.md` / `README.md`，stars/license/pushed_at 来自限流前的搜索结果。

**不是幻觉**。但读完代码后必须修正一件事：**它不是"物理具身 agent OS"，它是一个"带机器人执行网关的聊天 agent 框架"。** 下面用它的自述文档证明。

---

## 二、它的 OS 抽象到底是什么（这是本次评估的核心）

问题设定要求评估其"OS 抽象（任务/资源/环境管理）"。答案：**任务抽象薄、资源抽象不存在、环境管理等于"起一个子进程"。**

### 2.1 任务管理：一个全局单例状态机，不是任务图

`docs/en/01-framework-introduction.md:71`：

> Only one AgentTask may be non-terminal globally.

全系统同时只允许**一个**非终态 AgentTask。生命周期是一个线性状态机（同文件 §5）：

```
executing ──► succeeded / failed / awaiting_replan ──► cancelled
```

对比我们的 `TaskGraph` + `CONWIP 投放闸` + 多 worker 产线：**没有任何一处支持"多任务并发编排"**。后台 subagent 也只是把一个 AgentLoop 丢到 asyncio 里，且迭代上限是**写死的常量**：

- `PhyAgentOS/agent/subagent.py:118`：`max_iterations = 15`

这一行恰好会被我们的"默认即数据测试"判据（拍板版 §2.3）当场判死——策略常量在代码里。它同时说明：作者自己也把这件事当"agent 循环"而不是"产线调度"。

### 2.2 资源管理：官方文档明说不做

`docs/en/01-framework-introduction.md:39-41`：

> PAOS does not add a cross-Tool resource lease; the selected endpoint operation's `max_concurrency` decides admission.

`docs/en/01-framework-introduction.md:169-171`：

> Cross-Tool resource leases, implicit Registry downloads, and bundled concrete robot/simulator artifacts are **outside the implemented contract**.

这是作者自己在规格文档里画的红线：**跨工具资源租约不属于它的实现契约**。它把并发准入完全下放给机器人 endpoint 自己。对我们的 `Meter 可组合计量` + `分级背压`，这里没有任何可抄的东西——因为它压根没有这一层。

### 2.3 环境管理 = 子进程 + Dora

`PhyAgentOS/skill_runtime/manager.py:426`、`:465` 用 `subprocess.Popen` 拉起 Dora 数据流进程，管理的是"启动/停止/看日志"。没有命名空间、没有 seccomp、没有 cgroup 限额（`docker-compose.yml` 里的 cpus/memory 是**部署级**限额，不是每任务沙箱）。

### 2.4 唯一名副其实的 OS 部分：Delivery / Trigger / Calendar

`PhyAgentOS/channels/` 11 个渠道适配器共 5,944 行（飞书 1008、mochat 896、Telegram 776、Matrix 704、钉钉 479、email 409、Discord 377、企微 353、Slack 280…），`PhyAgentOS/cron/service.py` 400 行，`PhyAgentOS/heartbeat/service.py` 173 行，`PhyAgentOS/bus/queue.py` 44 行（就是两个 `asyncio.Queue`）。

**这是 PhyAgentOS 唯一比"一个 demo"强的部分，也是唯一和我们的 `Delivery / Trigger / Channel` 抽象正面重叠的部分。** 它本体（`pyproject.toml:9`）自述为 `A lightweight personal AI assistant framework`，内核是一个 OpenClaw/CherryBot 血统的个人助理 agent，物理执行是后接的 Gateway。

---

## 三、四个指定问题

### Q1 · 替我们省了什么？

| 我们的关注点 | PhyAgentOS 提供了什么 | 判定 |
|---|---|---|
| **Tool broker** | `PhyAgentOS/agent/tools/registry.py:9` 一个 `dict[str, Tool]` + 一个可选的 `policy.tool_call(name)` 上下文钩子（`:16`、`:54`）；MCP 客户端包装 `PhyAgentOS/agent/tools/mcp.py:13`。**全仓库没有一个工具声明自己的副作用语义**——唯一的近似物是 `PhyAgentOS/forge/interaction/service.py:15-27` 的硬编码 `SAFE_TOOLS` frozenset（12 个名字）和 `:110` 的 `allows()`，即"交互模式下只放行这 12 个工具"。 | **不省，反而更弱。** 我们的 Tool broker 已经要求每个工具声明状态语义（纯函数 / 需先落盘 / 一次性外部操作）。PhyAgentOS 是名单制，不是声明制。 |
| **Sandbox** | 无。`PhyAgentOS/forge/interaction/service.py:277` 直接抛错：`"production isolation adapters are not enabled in this release"`；`docs/interaction/README.md:16-21` 写明默认只接受 `InProcessInteractionDeployment` + `httpx.MockTransport`，"There is deliberately no `private_control_plane=true` production bypass"，且 `:18` "The interaction protocol has no token or HMAC authentication layer"。 | **零。** 连它自己都把沙箱列为未实现。 |
| **Meter** | 无成本记账。全仓库搜 `cost|price|quota|usd|spend` 只命中错误提示文案（`PhyAgentOS/providers/errors.py:33`）和一句文档里提到 `LITELLM_LOCAL_MODEL_COST_MAP`。真正存在的只有**单次 run 的硬闸**：`PhyAgentOS/agent/interaction/runner.py:45` `max_total_tokens: int = 100_000`，以及 `:598-607` 的 `wall_time_s` / `idle_time_s` 预算，写死在 dataclass 默认值里。 | **零。** 我们的 Meter 是"可组合计量 + 声明式预算维度"，它连单一维度的美元计量都没有。 |

**结论：三个指定关注点，一个都没替我们省。** 它最强的一块（渠道矩阵）恰好不是这次要评估的三块。

### Q2 · 效果证据（成熟度）

- **工程成熟度：高。** 42.7k 行 Python、37 个测试文件 9,455 行、`ruff` + `compileall` + `pytest` 三件套进 README（`README.md:320-326`）、双语文档、安全归档解包（`PhyAgentOS/skill_runtime/archive.py:20-24` 有 `max_files/max_file_size/max_total_size/max_compression_ratio` 四重限额，`:36-49` 拒绝 `..`/绝对路径/反斜杠/盘符）、崩溃安全的 per-Skill 文件锁（`PhyAgentOS/skill_runtime/locking.py:16`）。
- **能力演示：有，但都是机器人任务的。** LIBERO-10 上 GPT-6+π0.5 报 100%（`README.md:203`），RoboTwin 66-80%。**这些数字衡量的是"机器人能不能抓起杯子"，与"能不能当 Agent 工厂底座"无关**，且 README 自己标注 "Public-leaderboard references may use different protocols"、RoboDojo/RoboTwin 只用 10 个随机任务。属于"单点可达、未复现"的证据强度。
- **文档诚实度：罕见地高，值得肯定。** 作者反复自曝短板：production isolation 未启用、无 HMAC 认证、evidence 是 best-effort（`docs/en/01-framework-introduction.md:105`）、evolution 是 fail-open 且"cannot change execution or verification results"（`:134-135`）。这比很多项目的宣传册可信。
- **无事故运行证据、无生产用户证据**（contributors 数未取到，见第一节）。

### Q3 · 引入成本

- **语言错配（决定性）**：我们是自研 Rust 内核，它是纯 Python 3.11/3.12 异步栈（`pyproject.toml:6` `requires-python = ">=3.11"`）。任何"引入"都等于在 Rust 内核旁边并排放一个 Python 进程树。
- **依赖面大**：主依赖 33 项（`pyproject.toml:16-48`），含 `litellm`、`openai`、`tiktoken`、`mcp`、11 个 IM 渠道 SDK（`dingtalk-stream`/`python-telegram-bot`/`lark-oapi`/`qq-botpy`/`slack-sdk`/`matrix-nio`…）。为评估它而 `pip install -e ".[dev]"` 就拉爆了本机磁盘配额（见第五节），这个依赖面本身就是运维成本信号。
- **外部硬依赖**：物理执行路径需要 Dora CLI 0.4.1（`README.md:221-231`）、Node 20（`Dockerfile` 装 nodejs 20 给 WhatsApp bridge）、独立 Registry（`resourceRegistry.url` 默认指向 `paos-resource-manager.dev.x-era.com`，即 X-Era 自家服务）。**核心仓库不自带任何 Skill/模型/仿真资产**（`README.md:280-283` 自述）。
- **状态模型不合**：SQLite 两份（`.paos/agent_tasks/tasks.sqlite3`、`.paos/evolution/experience.sqlite3`，`docs/en/01-framework-introduction.md:143-151`），全局单任务串行（`:71`）。我们的 Rust 内核是内容寻址 + Merkle + 签名；它是本地文件树 + SQLite。

### Q4 · 对接四层中的哪层 + 退出成本

若强行对接，落点只能是 **L2 适配器**（把它的 Gateway `/tools` 当一个外部机器人供给接进来）——而且只能服务"我们这座工厂恰好有机器人"的场景，直接违反"任务无关"与"第二运营者测试"（拍板版 §2.1/§2.3）。

退出成本：Python 侧无状态可迁（SQLite 私有格式）、协议无认证层不可信、无 Skill 可带走。**退出成本低，但引入收益也是零——这是一笔纯成本交易。**

---

## 四、值得抄的三个设计（如果只看设计，不引代码）

不引项目 ≠ 没有可吸收的东西。以下三条是读代码时确认为**比我们现有设计更精细**的，值得进 L3 配方或作为机制细化：

1. **七种身份不得互相顶替**（`docs/en/01-framework-introduction.md:54-69`）。`task_id` / `binding_id` / `revision_id` / `record_id` / `caller_id` / `invocation_id` / `attempt_id`，文档明写 "They must not be copied into one another or treated as aliases"。这正是我们"agent 之间只传工件引用"（宪法第 1 条）落地时最容易糊掉的地方——建议把这条身份分离规则补进我们的 Artifact/Run 规格。

2. **"受理 ≠ 完成"，未知副作用永不自动重发**（`:93-99`）。原文："An Action or Session admission response is not completion… PAOS never repeats an unknown admission POST." 代码侧对应 `PhyAgentOS/forge/interaction/service.py:277` 附近的不确定态保留、以及 `runner.py:561` 的 `reconciliation_read_only` 事件、`automatic_resubmit: False`。这是我们"副作用网关幂等"的**更严格版本**：不确定态不是"重试"，而是"保留守卫等待对账"。建议把这条升级写进我们的副作用语义定义。

3. **升迁梯的四态 + 反例退役**（`PhyAgentOS/agent/experience/evolution.py:503-534`、`:390-396`；`PhyAgentOS/config/schema.py:368-370`）。候选状态 `collecting → blocked → promoted | rejected`；晋级门槛是"支持 episode 数 ≥ N"（默认 3，`evolution.py:74-75`）；反例累计到阈值后 lesson 进入 `counterexample`/`retired`（`:390-396`）。另有内容黑名单正则拦"绕过验证/忽略系统指令"（`evolution.py:29-51`，含中英双语）。我们的"升迁梯"目前只有晋级方向，**没有退役/反例方向**——这个缺口是实的。

   另注：`PhyAgentOS/agent/subagent.py:118` 的 `max_iterations = 15` 和 `evolution.py:74` 的阈值默认值，都是"策略常量进代码"的反例，**不要抄这个面**。

---

## 五、我实际跑了什么 / 没跑什么

**跑了**：
- `curl 'https://api.github.com/search/repositories?q=PhyAgentOS&per_page=10'` 等 4 个变体查询（项目定位，命中主仓）。
- 下载并解压全量源码到 `外部项目研究/.tmp-ext/PhyAgentOS-core`（13MB tarball，17MB 解压），逐模块行数统计（`wc -l`），按上表所有结论均引用 `文件:行号`。
- 读：`README.md`、`CHANGELOG.md`、`docs/en/01-framework-introduction.md`（全）、`docs/interaction/README.md`、`pyproject.toml`、`Dockerfile`、`docker-compose.yml`，以及 `agent/tools/{base,registry,mcp,forge_tool_api,spawn}.py`、`agent/{subagent,interaction/runner,experience/{evolution,store}}.py`、`forge/interaction/{service,contracts}.py`、`skill_runtime/{locking,archive,manager}.py`、`verification/contracts.py`、`bus/queue.py`、`cron/types.py`。

**没跑（且如实说明原因）**：
- **测试套件未运行。** 尝试 `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" && pytest`，失败两次且原因都在环境侧，不在项目侧：① 家目录 `/home/pan-ding` 已用 186G，`pip` 报 `OSError: [Errno 122] 超出磁盘配额`；② 系统 `python3` 为 **3.14.4**，项目要求 3.11/3.12；③ 系统 python 无 `pip` 模块（`/home/pan-ding/venvs/ml/bin/python3: No module named pip`）。因此 **"2987 stars 的项目能否在本机跑通"这一条我没有验证过**，本文所有成熟度判断均为**代码级 + 文档级**判断，非运行级。
- **contributors / releases API 未取到**（未鉴权限流）。

---

## 六、裁决

**不引入。**

理由三句话：
1. **功能上不重叠。** 它没有 Sandbox（自述 production isolation 未启用）、没有 Meter（无成本记账，只有单 run 的 token/时长硬闸）、Tool broker 只是一张 dict + 12 项硬编码白名单。任务里点名的三个借鉴对象，一个都不满足。
2. **架构上对立。** 全局单任务串行 + 跨工具资源租约"不在实现契约内"（作者自述），与我们的 TaskGraph/CONWIP/可组合计量处在两个世代。
3. **成本不划算。** 纯 Python 栈对 Rust 内核是零复用（无 FFI 面），33 项主依赖 + Dora CLI + Node 20 + 他家 Registry，换来的是一个机器人任务成功率数字。

**但记一笔"部分引入"：第四节三条设计值得抄进我们的规格**——七种身份分离、"受理≠完成/未知副作用永不自动重发"的更严幂等语义、升迁梯补上反例退役方向。这三条都不需要引入它的代码，是纯设计吸收，落地成本接近零。
