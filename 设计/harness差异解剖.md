# 设计 · harness 差异解剖（mcode / mini-swe-agent / zcode / af-harness）

> **使命**：搞清楚"商业/标杆 harness 为什么强"，产出我们可借鉴的具体差异清单，并回答"我们与 mini-swe-agent 的差距主要在协议设计还是参数"。
> **日期**：2026-10-20。**方法**：mcode 经 ssh anolis 只读实读 npm 包（0.6.5，未运行，未取任何密钥）；mini-swe-agent 经 GitHub 源码与官方博客一手取证；zcode 取本会话可观察事实 + bundled-skills 样本；af-harness/af-bench 读源码（swev scaffold v2）。与 [harness横评与配置建议](外部项目研究/harness横评与配置建议.md) 互补：那篇管"选型与强制拓扑"，本篇管"提示/协议/上下文/停止的工程细节与通过率"。

---

## 0. TL;DR

1. mini-swe-agent 用**一行 system prompt**在 SWE-bench Verified 拿到 65%（o3，发布时）→ **>74%**（当前 README，bash-only 榜），成本 $0.46-0.72/题。它赢的不是提示词，是**四件协议工程**：恰好一个可解析动作的硬格式 + 三类带内故障恢复 + "完成=提交命令的输出首行 token"的因果判定 + 大有效步数（250 步上限 / ~50 步饱和 / $3 成本上限）。
2. mcode（MiniMax Code 0.6.5）代表商业 CLI 的做法：~12KB 分层 system、Claude Code 同款工具族（read/edit/grep/glob/bash/task/todowrite）带重防错描述、95% 窗口自动压缩（结构化 5 节续接摘要）、16 类错误分类学 + 退避重试。**它的 agent 面纪律与开源 Claude Code 形态高度同构**——商业差距更多在模型与执行质量，不在秘密提示。
3. 我们的 swev scaffold v2（S0 0/5）**参数并不紧（60 轮 ≥ mini 饱和点 50 步），紧的是协议**：完成信号是"文本子串"（无动作、无工件、任何轮可误触发）、无带内故障恢复、纪律放 system 不放 instance。S0 实证 agent 5-13 轮自愿收工、token 比画像低 1-2 个数量级——失败是"提前停"，不是"资源不够"。
4. **判断：差距主要在协议设计**。协议修复的直接预期是把 S0 的 D1/D2/D3 类失败（每模型 1/5）救回，即 0/5 → 1-2/5；要接近 mini 的 74% 还需模型分档 + cascade（E1），harness 协议只能把"自家造成的损失"清零。

---

## 1. 四方事实卡（一手取证）

### 1.1 mcode（@minimax-ai/code 0.6.5，anolis ~/.npm-global/lib/node_modules/）

**提示结构**（assets/agents/ 下 hbs 模板按 feature 条件编译）：
- `_v2/coding/SYSTEM.md.hbs`（~12KB）分五层：`# Harness`（工具优先级、权限语义、并行/串行规则、最高信号先行、不引入泄密代码）→ `# Core Judgment`（角色定位；"做用户实际要求的事，不悄悄扩大缩小或重塑任务"；"歧义时先完成所有不依赖答案的部分"；"复杂任务先定 scope/deliverable/validation 再拆解"）→ `# Memory`（高信号记忆纪律，no-op 优先）→ `# Communication & Delivery`（preamble 消息规范含 8 条示例、final response 必须自包含、验证后才宣布完成）→ Shell/Git 约束。
- `_v2/` 有独立子代理角色：`worker` / `explore`（只读，副作用即 `ROLE_MISMATCH`）/ `verifier`（怀疑主义、不信任生产者声明、发现按严重度报告）。**子代理有 Deliverable Gate：任务越权时立即返回 `ROLE_MISMATCH` 并推荐改派**——用协议而不是劝说防跑偏。
- `work/SYSTEM.md.hbs` 有 **Artifact Completion Contract**：先写验收清单→先交付主件再做附带改进→"功能正确优先，视觉可接受即停，最多两轮渲染检查"。

**工具集与防错**（chunk-2XPMNZVR.js 内 T.Object schema）：read / write / edit / grep / glob / bash / todowrite / task / skill / web_search / memory + 媒体全家桶（图像理解/合成/视频/TTS/音乐）。每个工具有 `executionMode: parallel|sequential` 显式标注。防错条款代表：
- `edit`："old_string 必须与文件精确匹配（含空白缩进），不唯一必须 replace_all，否则失败"。
- `read`："最多 2000 行 + 字节上限；截断时给 next_offset，用同参数续读；不要为确认编辑成功而重读"。
- `grep`："ALWAYS 用本工具搜内容——绝不经 bash 调 grep/rg（会绕过过滤与权限审查）"；`literal=true` 免转义；`output_mode: files_with_matches|content|count`；分页 offset。
- `bash`："每次调用工作目录与 shell 状态不持久，需要换目录就在同一条命令内 cd"；"shell 非交互，无 TTY/stdin，交互式命令先查 --help 的非交互 flag"；timeout 默认 120s 上限 300s、可 run_in_background。

**上下文管理**（compaction，chunk-2XPMNZVR.js `j0` 配置 + chunk-U5SHMJ7Y.js 摘要 prompt）：
- 触发：用量达上下文窗口 95%（`Zan=.95`）。参数：`reserveTokens:16384, keepRecentTokens:20000, minMessagesToCompact:4, contextWindowFallback:128000, safetyMarginTokens:2048`。
- 摘要是**结构化续接摘要**，prompt 全文（固定 5 节）：Task Overview（用户核心请求与成功标准）/ Current State（已完成、改过的文件路径、产出物）/ Important Discoveries（约束、决策及理由、试错及为什么不行）/ Next Steps（具体行动、阻塞、优先级）/ Context to Preserve（用户偏好、承诺）。产出包在 `<summary>` 标签内以 user 消息形式接续历史（`compactionSummary` 角色）。另有 branchSummary 同构。带 PreCompact/PostCompact hooks（trigger + compact_summary）。
- 亦有服务端压缩通道引用（Anthropic `edits: [{type:"compact_20260112"}]`），本地策略为 fallback。

**迭代/停止/重试**：
- 子代理循环：`for turn in 0..maxTurns`，首条消息为 briefing；主循环无固定轮上限（交互面）。
- HTTP 错误分类学 16 类（abort/timeout/rate_limited/tpm_rate_limited/usage_limit/credits_exhausted/auth/bad_request/not_found/content_filter/server_error/overloaded/network/empty_response/unknown/length），重试尊重 retryAfterMs，受 maxRetries 与 maxRetryElapsedMs 双约束，全程 observer 事件可观测。

### 1.2 mini-swe-agent（SWE-agent/mini-swe-agent，Vals.ai 榜单在役 harness 之一，开源标杆）

**代码体量**：agent 类 ~100 行（docs 与官方博客全文引用）。核心循环：

```python
while True:
    try: self.step()                       # query → parse_action → execute → observation
    except NonTerminatingException as e:
        self.add_message("user", str(e))   # 带内恢复：失败变消息，循环继续
    except TerminatingException as e:
        return type(e).__name__, str(e)    # 只有 Submitted / LimitsExceeded 两种终态
```

**输出协议**：system 一行（SWE-bench 配置为 "You are a helpful assistant that can interact with a computer shell to solve programming tasks."）；全部纪律在 instance template（每题作为 user 消息重申）：THOUGHT 段 + 恰好一个动作（v2 默认 native toolcall `bash`，另有 backticks/xml 两个协议变体文件同仓并存——输出协议本身是被消融的对象）；`parse_regex_actions` 要求**恰好 1 个动作**，多了少了都是 `FormatError`。

**带内故障恢复**（这是它的高分机制之一）：
- `FormatError` → `format_error_template` 反馈：不仅报错，还**教学**（给出正确调用示例；`finish_reason=="length"` 时单独模板："你在产生工具调用前被截断，请更简洁"）。
- 命令超时 → `timeout_template`：给出被杀命令原文 + 已有输出 + "请换命令，避免需要交互输入的命令"。
- 连续格式错上限 3 次（`max_consecutive_format_errors`）才以 `RepeatedFormatError` 放弃——模型一般 1 次就学会。

**完成判定**：`has_finished` 检查**命令执行输出**的首行是否为 `MINI_SWE_AGENT_FINAL_OUTPUT` / `COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`。完成必须付出一个"跑 echo"的动作，输出可复核，且协议明说"You CANNOT continue working after submitting"。SWE-bench 配置还要求先 `git diff > patch.txt`（只列源文件）→ 自检 header → 单独命令提交，三步分离。

**参数**：`step_limit: 250`（SWE 配置；默认 0=不限）、`cost_limit: $3`、命令 timeout 60s、输出 >10k 字符截为 head 5k + tail 5k + elided 计数 + "换更窄命令"指引、环境变量卫生（`PAGER=cat, MANPAGER=cat, LESS=-R, PIP_PROGRESS_BAR=off, TQDM_DISABLE=1, BASH_ENV=/root/.bashrc`——顺带修了 conda 环境激活）。模型层 10 次指数退避（4s 起，60s 封顶）。

**成绩与消融数据**（公开）：
- README：**>74% SWE-bench Verified**（bash-only 榜；搜索摘要读数 74.40% @ $0.72 / 74.20% @ $0.46）；发布时 o3 约 65%。
- 官方 Roulette 博客（2025-08-19）：**~50 步后性能边际趋零**；成本随步数呈 sigmoid，~30¢/题达峰；每轮随机换模型（提示不变）在 50 题子集上 39 > Sonnet4 33 > GPT-5 32——收益来自模型组合与提交动态，不是提示词改动。
- 与 Agentless（RAG 一次性多补丁挑选）对比明确划界：mini 是纯线性 agent。

### 1.3 zcode（本机在役，可观察事实）

- **系统提示结构**：身份（我是谁/被供电）→ 任务框架（完成、不镀金）→ 纪律（密钥零明文、不越权、commit/push 需请求）→ 工具使用通则（绝对路径、并行独立调用、无 emoji）→ 每工具描述含防错条款。总体与 mcode 的 Harness/Core Judgment 层同构（两者都是 Claude Code 形态的直系后裔）。
- **工具防错样本**：Edit（"必须先 Read 过；old_string 必须精确匹配含缩进；不唯一则失败"）、Read（默认 2000 行、PDF 分页 ≤20 页/请求）、Bash（"cwd 每次重置，用绝对路径；交互式 flag 不支持；gh 做 GitHub 操作"）。防错靠**把失败模式写进描述**而不是事后兜底。
- **子代理机制**：主对话派生子代理（本任务即是），子代理只回文本给协调者；协调者可中途通信。工具面上子代理同样全量可用。mcode 的 task/worker-explore-verifier 角色化是同一机制加"角色门禁"。
- **技能系统**：SKILL.md = frontmatter（name/description/when_to_use 触发工程）+ 正文方法论。样本（bundled-skills/skills/dynamic-workflows）显示其提示工程风格：**表格化决策规则、明写"何时不用"、把判断标准写成一等公民文字**。渐进披露（按需 load）即上下文经济学。
- **上下文压缩**：在役系统含会话压缩与系统提醒注入（本会话可直接观察到 system-reminder 机制与 todo 持久化）；实现细节不在本会话可观察范围，不虚构。

### 1.4 af-harness + af-bench（我们的 swev scaffold v2）

- 提示：`SWEV_SYSTEM_PROMPT` ~120 词 5 条规则（在 /testbed 修 issue；没改文件=失败；禁改测试；先跑测试验证；完成后以 TASK_COMPLETE 结尾且不再调工具）。
- 工具：bash 单工具，声明 2 句描述（含 workdir 前缀语义）。执行：`docker exec bash -lc 'cd /testbed && …'`，180s timeout，输出截断 12k（头尾各半 + 字节数），返回 `exit=N` 前缀。
- 停止：`max_turns 60`；完成=assistant 文本 contains `TASK_COMPLETE`（每轮都查，且**先于** tool_free 检查）；连续 3 轮无工具调用即 ToolFreeLimit 停；预算 100¢。
- 自修复：429/5xx 指数退避 ≤5（尊重 Retry-After）；401 重取密钥重试 1 次；**门禁重试 1 次**（零补丁 / 改测试 → 拼上 harness 反馈重跑，attempt≤2）——v2 新增，思路与 mini 的带内恢复同源，但粒度是"整轮重跑"而非"消息级续跑"。
- 上下文：无压缩、无工具输出分页续读；transcript 全量重发（无 prompt cache 标记）。
- S0 战绩（状态/S0-实测报告.md）：SWE-V ×5 两模型皆 0/5；失败=1 零补丁 + 4 错补丁（M3.1Flash）、1 越权改测试 + 4 错补丁（GLM-5.3）；agent 9-25s、5-13 轮自愿收工，input 4.8k-14.9k tokens。

---

## 2. 差异矩阵

| 维度 | mcode（商业 CLI） | mini-swe-agent（开源标杆） | zcode（本机在役） | af-harness swev v2 |
|---|---|---|---|---|
| **提示结构与字数** | ~12KB 分层 hbs 模板：Harness 纪律→Core Judgment→Memory→Communication→Shell；角色化子代理提示各 ~1-2KB | system **1 行**；全部纪律在 instance（每题重申）：格式协议/边界/工作流/提交三步/示例 | 身份→纪律→工具通则→输出风格；判断标准表格式成文 | 120 词 5 条规则，全部在 system，一次性 |
| **工具集丰富度与防错** | 15+ 工具；每工具 executionMode；描述含失败模式条款（edit 精确匹配/唯一性、read 分页续读、grep 禁经 bash、bash 无状态+非交互+超时语义） | **1 个 bash 工具**；防错不在工具描述，在观察模板（10k 截断+换窄命令指引）、格式教学反馈、timeout 反馈、env 卫生变量 | Read/Edit/Bash/Grep 等核心族，描述含防错条款（同 mcode 形态） | bash 单工具 2 句描述；12k 截断无指引文案；超时返回"桥接失败"无恢复指引 |
| **停止与完成判定** | 交互面无完成信号；子代理 briefing+maxTurns；交付有验收清单契约 | **完成=提交命令输出首行 token**（因果、可复核、提交即终止）；唯一终态 Submitted/LimitsExceeded | 交互循环 | 文本 contains TASK_COMPLETE（任何轮可误触发；无动作无工件）+ tool_free 3 轮 + 60 轮 + 100¢ |
| **上下文管理** | 95% 窗口自动压缩；结构化 5 节续接摘要包 `<summary>`；保留最近 20k tokens；工具输出分页 next_offset | 无压缩；10k 截断 + 线性历史即可支撑 250 步 | 在役含会话压缩 + 技能渐进披露 | 无压缩、无分页；transcript 全量重发无 cache 标记 |
| **输出协议** | 无硬协议（交互面）；子代理 final_text / ROLE_MISMATCH 角色门禁 | **每轮恰好 1 个动作**；违规→FormatError→教学反馈；连续 3 次才放弃 | 无硬协议 | 无格式约束；无工具调用轮静默计入 tool_free 倒计时（不教学） |
| **重试与自修复** | 16 类错误分类学 + retryAfterMs 退避 + 双重上限；任务级无自动重跑 | 模型层 10 次退避；**NonTerminating 全部带内恢复**（格式错/超时/异常都变 user 消息继续跑） | HTTP 退避 + 401 重取 + 门禁重试（与 af 同源思路） | 429/5xx 退避 ≤5 + 401 重取 + **整轮门禁重试 1 次**（零补丁/改测试）——供给面对齐，带内恢复缺失 |
| **体量参照** | ~14MB chunks + 资产 | agent ~100 行 + 配置 YAML | 闭源在役 | af-harness ~919 行 run loop + bench 配方 |

---

## 3. 可借鉴清单（按预期 SWE-V 通过率影响排序）

> 数据锚点：mini-swe-agent 74%+（bash-only 榜）/ 我们 S0 0/5。排序依据：每条直接对应的 S0 失陷模式（D1-D6）+ 公开消融/饱和数据。

**B1. 完成协议改成"可执行提交命令"**（抄 mini-swe-agent `has_finished`）
- 改什么：废掉"assistant 文本 contains TASK_COMPLETE"。改为：agent 必须执行 `echo TASK_COMPLETE`（或 `echo TASK_COMPLETE && cat patch.txt`），harness 在**工具输出首行**匹配 token 才判 Completed。同时删掉"每轮先于 tool_free 的信号检查"，任何中期叙述都不再触发完成。
- 为什么影响大：S0 D1（零补丁完成）/D3（浅尝辄止）的直接机制就是"停止太便宜"。mini 把完成变成一个有代价、有工件、可复核的动作，并配套"提交后不可继续"语义。当前实现还有一条真实风险路径：模型在任何轮的叙述里写了 TASK_COMPLETE 字样（哪怕是"先别发 TASK_COMPLETE"），harness 立即判完成。

**B2. 参数放宽到 mini 口径：预算 100¢→300¢，轮次 60→150-250，并加"最小勘察"软纪律**（抄 mini step_limit/cost_limit + Roulette 博客饱和数据）
- 改什么：`spend_cap_cents/budget` 100→300；`max_turns` 60→200 档；SWEV 提示加 mini 式推荐工作流（定位→复现脚本→修复→验证→边界）。
- 为什么影响大：mini 公开数据表明性能在 ~50 步才饱和、成本在 ~30¢/题达峰；我们 S0 实测 input token 比内部画像低 1-2 个数量级——上限远未触及，是 agent 自愿早停。参数放宽本身不解决早停（需 B1），但 B1 之后没有余量就是新瓶颈。注意 60 轮不是当前绑点（无人打满），改它是给 B1/B3 腾空间。

**B3. 带内故障恢复：NonTerminating 语义 + 格式/超时教学反馈**（抄 mini 三模板 + agent 循环）
- 改什么：① 命令超时/执行异常不再返回"exit=127 桥接失败"这类终端文案，改为 timeout 模板（原命令 + 已得输出 + "避免交互式命令，改用非交互 flag / 重定向"）作为 tool 结果回灌；② 模型轮次无工具调用且无完成意图时，第一轮就注入纠错消息（"你必须调用 bash 工具，示例：{...}"），而不是静默数满 3 轮等 ToolFreeLimit；③ 引入连续 N 次格式错才放弃的计数。
- 为什么影响大：把"必死"变"可恢复"= 有效步数净增；mini 的 FormatError 反馈一般 1 次即教会。这与我们 v2 已有的门禁重试同哲学，但从"整轮重跑"降为"消息级续跑"，便宜一个数量级。

**B4. 提交工件化 + 自检前置**（抄 mini Submission 三步协议）
- 改什么：instance 模板加三步：`git diff -- <只列你改的源文件> > patch.txt` → 自检（只含源文件、header 完整）→ `echo TASK_COMPLETE && cat patch.txt`。保留现有 `diff_touches_tests` 门禁作第二道防线。
- 为什么影响大：S0 D2（越权改测试）在 mini 协议里被"只列源文件"的自检**事前**消化；我们的门禁是事后拦截+整轮重跑（贵一倍）。D2 在 GLM-5.3 上实发 1/5。

**B5. 纪律从 system 挪到 instance，提示包按 mini 骨架重写**（抄 mini instance_template + mcode Core Judgment）
- 改什么：system 保持一行角色；把边界（MODIFY/DO-NOT-MODIFY）、工作流、执行规则（非交互 flag、每命令新子 shell）、正确响应示例、提交协议全部放进随任务重发的 instance 消息；问题陈述用 `<pr_description>` 包裹。吸收 mcode Core Judgment 两句进纪律："做任务实际要求的事，不悄悄扩大/缩小/重塑"；"歧义时先完成所有不依赖答案的部分"。
- 为什么影响大：mini 用一行 system 拿 74% 证明字数不是变量，**纪律随任务重申**才是；一次性 system 在长对话里抗遗忘差。直接压制 D1/D3/D6（交付物清单）。

**B6. 截断与环境卫生物美价廉**（抄 mini observation_template 文案 + env 块）
- 改什么：① 12k 截断附 mini 式指引文案（"输出过长；用 head/tail/sed 选段，或重定向到文件再搜索"）；② docker exec 注入 `PAGER=cat MANPAGER=cat LESS=-R PIP_PROGRESS_BAR=off TQDM_DISABLE=1 NO_COLOR=1`。
- 为什么影响大：单项小，但零风险零成本；分页器挂死与进度条噪音是 SWE 容器高频暗坑（mini 专门为此修了 BASH_ENV/conda 激活）。

**B7. 上下文压缩（B2 落地后的必做项）**（抄 mcode j0 参数 + 5 节摘要 prompt）
- 改什么：用量达窗口 95% 触发；保留最近 ~20k tokens；摘要 prompt 固定五节（任务概览/当前状态/重要发现/下一步/需保留上下文），产出以 `<summary>` user 消息接续。
- 为什么影响大：当前 60 轮配置下非急迫（S0 无人跑满）；一旦采纳 B2 的 200+ 轮，无压缩必撞窗。mini 不需要压缩是因为 10k 截断 + 提交式终局天然限长；我们的任务形态相同，可先靠截断，压缩在 S2 排期。

**B8. finish_reason=length 专项反馈**（抄 mini length 模板）
- 改什么：endpoint 8192 max_tokens 截断且无工具调用时，注入"你被截断，请更简洁并在本轮发出工具调用"反馈。
- 为什么影响大：低频但属于"死态转活态"的同类修复，顺手。

---

## 4. 特别回答：我们与 mini-swe-agent 的差距在"协议设计"还是"参数"？

**判断：主要是协议设计，参数不是主因。** 依据四条：

1. **参数面我们并不紧，且失败模式方向相反。** 若参数是瓶颈，应看到 agent 打满 60 轮 / 预算打满而亡。S0 恰好相反：9-25 秒、5-13 轮自愿收工、input tokens（4.8k-14.9k）比内部画像低 1-2 个数量级；mini 的饱和数据（~50 步、~30¢ 达峰）说明"资源余量"只有配合"必须干够再停"的协议才有意义。我们的 60 轮上限 vs mini 250 上限在当前都远未触及——这不是失分项。唯一真实偏紧的是 100¢ vs $3 成本上限（B2 顺手放宽）。
2. **协议面三个缺陷各自独立制造失败，且与 S0 缺陷一一对应。** ① 完成信号=文本子串（无动作、无工件、可误触发）→ D1/D3；② 无带内恢复（超时=死文案、无工具轮=静默倒计时）→ 有效步数缩水；③ 纪律一次性放 system → 长任务遗忘 → D2/D6。mini 对应的三件：提交命令输出首行判定、NonTerminating 全恢复、纪律随题重申——全是**结构**而非措辞。
3. **公开消融形态佐证"协议 > 提示词"。** mini 官方 Roulette 实验：每轮随机换模型、提示一字不改，成绩反超两个单体模型（39 vs 33/32）——收益来自提交动态与模型组合，说明提示词措辞不是主要变量；而它的性能来自恰好一个可解析动作的硬格式 + 三类恢复模板 + 因果完成判定。它的一行 system 反证提示字数无关。
4. **诚实的预期管理。** S0 n=5、k=1：两模型各 4/5 失败是 D5（错而似真=模型能力真信号），协议修复的直接可回收项是每模型 1/5（D1/D2/D3 类），即 0/5 → 1-2/5 档。74% 还需要模型分档与 cascade（E1）——harness 协议的责任是把"自家造成的损失"清零，并把每分预算转化为有效步数。

---

## 5. 证据来源

| 对象 | 证据 |
|---|---|
| mcode | anolis `~/.npm-global/lib/node_modules/@minimax-ai/code/`：`assets/agents/_default/prompt-base-all.md`（7.2KB）、`_v2/coding/SYSTEM.md.hbs`（12KB）、`_v2/{explore,verifier}.md.hbs`、`_v2/work/SYSTEM.md.hbs`（Artifact Completion Contract）、`chunk-2XPMNZVR.js`（工具 schema/executionMode/compaction 参数 j0/错误分类学）、`chunk-U5SHMJ7Y.js`（5 节续接摘要 prompt `<summary>`）、package.json 0.6.5。全程只读，未取密钥 |
| mini-swe-agent | GitHub 源码（agents/default.py 循环与异常类、models/utils/actions_text.py 恰好一动作解析、config/benchmarks/swebench.yaml 全文、config/default.yaml、README）；swebench.com 官方博客 GPT-5 post（agent 类全文引用 + has_finished）与 Roulette post（~50 步饱和 / ~30¢ 达峰 / 换模型消融）；榜单读数 74.40%@\$0.72（搜索摘要，未直接复核页面，README 宣称 >74% 为准） |
| zcode | 本会话系统提示与工具描述（在役观察）、`/opt/ZCode/resources/glm/packages/bundled-skills/skills/dynamic-workflows/SKILL.md`（提示工程风格样本）、子代理机制（本任务即运行其中） |
| af-harness/af-bench | `af/crates/af-bench/src/main.rs`（SWEV_SYSTEM_PROMPT、60 轮/100¢/门禁重试）、`af/crates/af-bench/src/tb.rs`（bash_tool_decl、exec 180s/12k 截断）、`af/crates/af-harness/src/run.rs`（循环/停止/401 重取）、`af/crates/af-harness/src/endpoint.rs`（8192 max_tokens、无 cache_control）、`状态/S0-实测报告.md`（0/5 与 D1-D6） |

## 更新记录

| 日期 | 身份 | 变化 |
|---|---|---|
| 2026-10-20 | harness 差异研究代理 | 建档：四方事实卡 + 六维差异矩阵 + B1-B8 可借鉴清单 + "协议为主因"判断 |
