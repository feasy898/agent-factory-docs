# harness 对齐审计 — SWE-bench Verified 标准测试条件基准

日期：2026-10-20
使命：回答"标准化的 SWE-bench Verified 测试条件到底是什么"，作为自研 af-harness（af-bench swe-v 线）配置的裁决基准。
方法：三线调查——①公开标准（官方源码/文档/榜单方法论，均给来源）；②我方历史前例（参考/legacy 三战役脚本还原）；③af-bench/af-harness 现状（源码原文）。
密钥纪律：本文零密钥明文，端点档案只写引用名。

---

## 0. 结论摘要

1. **公开口径的主轴是 mini-swe-agent**：swebench.com 官方榜单与 Vals.ai 统一 harness 都用它。其 SWE-bench 配置（`src/minisweagent/config/benchmarks/swebench.yaml`）为：**step_limit 250（一步=一次模型调用）、cost_limit $3/题、单 bash 工具、命令超时 60s、输出 >10KB 截断为头 5K+尾 5K、每题 1 次采样（k=1）**；温度在 yaml 中未设（模型默认），采用它的论文口径为 temperature 0.0（OpenAI 系模型 1.0）。
2. **我们 swe-v 现状与该口径的最大偏差是 max_turns=60（模型调用次数）**，仅为 250 的 24%；叠加 $1 成本上限（标准 $3–4）、max_tokens 8192（Vals 口径"开到最高"）。**运营观察到的"大量 max_turns 失败"方向上必然压低通过率，属测试参数失配，在归因 harness 前必须先对齐。**
3. 历史前例（cal2 / mcode-campaign / campaign-sc）全部是**原生 CLI 完整系统提示 + 墙钟硬超时（25–30 分钟）+ k=1 + 官方判分**，与 af-bench 的"自管对话循环 + 60 轮 + $1"是两种形态；与 cal2 可比的条件在 §6.B。
4. 另有两处**反向偏差**（会抬高我们的分数，与榜单不可比）：user message 注入了 `hints_text`（标准三 harness 都只给 problem_statement）；scaffold v2 的 gate 失败反馈重试（attempt≤2，标准无此机制）。

---

## 1. 公开标准口径

### 1.1 mini-swe-agent（swebench.com 官方榜单 / Vals.ai 统一 harness）

来源等级：**官方源码（A）**。以下摘自 SWE-agent/mini-swe-agent 仓库 `src/minisweagent/config/benchmarks/swebench.yaml`（main 分支，2026-10-20 抓取）：

| 参数 | 值 | 备注 |
|---|---|---|
| 步数上限 | `step_limit: 250` | 一步 = 一次模型调用（可含多个 bash 工具调用） |
| 成本上限 | `cost_limit: 3.` | $3/题，超限即停 |
| 系统 prompt | 一行："You are a helpful assistant that can interact with a computer shell to solve programming tasks." | 极简系统提示 |
| 任务 prompt | 长实例模板（~90 行）：PR description 包裹 + 任务指令：只改非测试文件（DO NOT MODIFY tests、pyproject.toml、setup.cfg 等）、推荐工作流（复现脚本→修→验证）、**提交协议**：`git diff > patch.txt` 后必须用原样命令 `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt` 提交，提交后不得再操作 | 输出格式约束：每轮必须含推理文本 + **至少一个** bash 工具调用（原生 tool calling，多调用允许） |
| 命令超时 | `timeout: 60`（秒/命令） | docker 环境，cwd=/testbed |
| 观察截断 | 输出 ≥10000 字符 → 头 5000 + 尾 5000 + 省略提示 | |
| 模型 | 默认 `anthropic/claude-sonnet-4-5-20250929`，`model_kwargs: drop_params, parallel_tool_calls` | **温度未设 = 供应商默认** |
| k 值 | 每题 1 次（preds 已存在即跳过） | |

佐证与口径补充：
- 采用 mini-swe-agent 复现 SWE-V 的论文明确写"temperature 0.0, maximum step limit of 250, maximum cost of $3 per issue, one patch per issue"（OpenAI 模型用 1.0）。来源：arXiv:2511.13646（社区转引官方超参，B+）。
- Vals.ai（榜单发布者）方法论页：全模型统一 mini-swe-agent、单 bash 工具、"providers' default configurations except the max token limit, which is always set to the highest value possible"、Docker 隔离、官方单测判分；未公布温度与 k（页面未列）。来源：https://www.vals.ai/benchmarks/swebench （榜单发布者官方，A-；该榜 2026-09-01 起已归档）。
- swebench.com 官方榜：mini-swe-agent 为默认提交 harness，各厂以此为标准口径提交（如 Claude Opus 4.5 high 76.80%）。来源：https://www.swebench.com （A-）。

### 1.2 SWE-agent 官方默认（v1.x）

来源等级：**官方源码（A）**（`sweagent/agent/models.py`、`config/default.yaml`，main 分支）：

| 参数 | 值 |
|---|---|
| 温度 | `temperature: float = 0.0` |
| top_p | `top_p: float | None = 1.0` |
| 单题成本上限 | `per_instance_cost_limit` 默认 **3.0**（$3/题） |
| 步数上限 | v1.x AgentConfig **无 step_limit 字段**（靠成本上限与 submit 收束；老版本/社区常用 100 步、$2 档，见 config 文档与教程） |
| 观察 | `max_observation_length: 100_000` 字符 |
| 工具 | bash + 工具 bundle（edit_anthropic filemap、review_on_submit），系统提示一行，实例模板含"只改非测试文件、测试已被我改好"的标准文案 |

### 1.3 OpenHands

来源等级：官方评测代码 + 官方 issue（B+，当前版本可能有变）：

| 参数 | 值 | 来源 |
|---|---|---|
| 迭代上限 | `max_iterations = 100`（SWE-bench eval harness 默认） | OpenHands 仓库 evaluation/benchmarks/swe_bench（issue #9730、#2140 日志实证） |
| 单题预算 | `max_budget_per_task=4`（$4） | 同上（issue #2651） |
| 温度 / top_p | 0.0 / 1.0 | SWE-bench Live 论文（arXiv:2505.23419，官方协作口径："maximum of 60 iterations, temperature 0.0, top-p 1.0"——注意该新基准用 60 迭代，OpenHands 自家 SWE-bench 经典口径 100） |
| 提示结构 | CodeAct agent：长系统提示 + bash/IPython/编辑工具 | 官方仓库 |

### 1.4 各厂官方 SWE-bench Verified 提交口径

| 厂/模型 | 声明的 harness | 分数 | 参数细目 | 来源等级 |
|---|---|---|---|---|
| Zhipu GLM-4.6 | mini-SWE-agent（swebench.com 榜单提交） | 55.4%（$0.10/run） | mini 默认（§1.1） | 榜单（A-） |
| Zhipu GLM-5 | 榜单：mini-SWE-agent（"GLM 5 high"，2026-02-17 提交，$0.53/run）；技术报告另报 77.8%（harness 未公开细节） | 72.8%（榜）/ 77.8%（报告） | 榜单=mini 默认 + thinking high；报告口径**不可得** | 榜单（A-）+ 官方博客（B+） |
| Moonshot Kimi K2 | 内部 agentic scaffold（bash/editor 工具，**单次尝试、无 test-time compute**）；榜单另有 "Kimi K2 OpenHands" 65.40 | 65.8% pass@1 | 温度等采样细目在 tech report PDF（arXiv:2507.20534）正文，**未逐页核验=部分不可得**；K2.5 官方 README 默认 temperature=1.0 / top_p=0.95 | 官方 README（B+） |
| MiniMax M2 | 技术报告：**R2E-Gym scaffold on top of OpenHands**；榜单：mini-SWE-agent（61.00，$0.43）；M2.1：67.0（mini-swe-agent）/ 74.0（Claude Code）；M2.5：80.2% | 见左 | R2E-Gym/OpenHands 臂的迭代上限与温度官方 README 未列，**不可得** | 官方 README + 榜单（B+/A-） |

要点：**三家在官方榜的口径全部收敛到 mini-swe-agent 默认参数**；各家内部报告的高分用的是自家/定制 harness，参数多不完整公开。

### 1.5 Terminal-Bench 4.0 / Harbor（TB 线顺带对齐）

来源等级：官方源码（A）+ 第三方集成文档（B）：

- Harbor 生态的官方 agent **terminus-2**（harbor-framework/terminal-bench-1 仓库 `terminal_bench/agents/terminus_2/terminus_2.py`）：`max_episodes` 默认 None → 代码置 **1,000,000（实际上限不设防）**；`temperature` 默认 **0.7**；任务级超时由各任务 yaml 定义。
- TB 4.0 集成文档（EvalScope）：`max_turns` 默认 None = 用 Harbor agent 默认（即上述"不限"）。
- **官方榜没有统一 max_turns**：Artificial Analysis 用 max_turns 250；GLM-5.2 卡片 TB2.1/Terminus-2 用 max_turns=2000、温度 1.0、max_tokens 64000；Qwen3.6 用 3h 超时。结论：TB 线"标准"= Terminus-2 不设轮限 + 任务级时间上限，各评测方自报轮限（来源：artificialanalysis.ai methodology、huggingface.co/zai-org/GLM-5.2、qwen.ai blog，B）。

---

## 2. 我方历史前例还原（legacy 三战役）

来源：`参考/legacy/{cal2,campaign-sc,mcode-campaign}/` 抢救脚本（本地源码，A）。三战役题集均为 Terminal-Bench 任务（官方 Dockerfile + tests/test_outputs.py，docker 构建、scratch 挂 /app、pytest exit 0 = pass）。

### 2.1 cal2（2026-10-13~17，TB 51 题 × 12 配置；结论 GLM-5.3 80.0%、mcode-m31f 76.5%、M3.1Flash 复现逐题一致率 80.4%）

| 泳道 | 实际命令（脚本原文） | 条件 |
|---|---|---|
| zcode-wf（GLM-5.3 / GLM-5.3-Flash / M3 / M3.1F / s5 / router） | `zcode -p "$(cat prompt.txt)" --cwd scratch --mode yolo --model X`（`bench-scripts/agent_zcode.sh`） | **原生客户端完整系统提示**（未注入自定义 system）；用户消息 = prepare_task.py 的 PREAMBLE（24 行环境说明：/app↔cwd 映射、可用软件、pip 镜像、"约 25 分钟"、DONE 声明）+ 任务指令原文；thinking 档位 zcode provider 默认 high，zcode-s5 泳道**对齐 step CLI 默认 medium 重跑**（incidents E3） |
| mcode（M3 / M3.1-Flash） | `mcode exec --cwd scratch --model X --permission full --timeout 25m "<prompt>"`（`agent_mcode.sh`） | 内部超时 25m + OS `timeout 1500`；原生系统提示 |
| step（s5 / router） | `step -p "<prompt>" --approval-mode auto --model X --append-system-prompt "$GUIDE"`（`agent_step.sh`） | GUIDE=4 句非交互安全指引（rm -rf/git 硬阻断规避）；thinking=medium（CLI 二进制默认档） |
| kimi（K2.8） | `kimi -p "<prompt>" -m kimi-code/kimi-for-coding` | 全默认 |
| grok（4.7） | `grok --cwd scratch --always-approve --max-turns 150 --model X --output-format json --prompt-file` | **唯一显式轮限：150 turn**；墙钟 3750s |

共同条件：**k=1**（每配置每题一跑；无采样重试，只有 infra/额度事件补跑）；**温度未显式设置**（各 CLI 供应商默认）；墙钟超时 1500s（grok 3750s）；判分官方 pytest（后期修复判分链路：5400s 构建超时、pytest 环境自检、root 残留清理，REPORT §十/§十一）。
结论数字口径：GLM-5.3 = 80.0%（40/50，1 题 infra 剔除）；cal2-mcode-m31f = 76.5%（未重判）；M3.1-Flash 复现轮 68.6% 且与原跑逐题一致率 80.4%（REPORT §十二）。

### 2.2 mcode-campaign（TB 任务，M3.1-Flash 技术臂实验）

`solve.sh` / `solve_retry.sh` / `gen_prompts.py`：`mcode exec --permission full --timeout 25m`，OS timeout 1800s；prompt = PREAMBLE +（技术臂提示块）+ 任务指令；**reps=2**（wave.json 默认，方差实验设计，非榜单口径）；run 级失败（exec failed/cancelled）重试最多 3 次（自愈锁错误/超时，非模型失败重采样）；配额 402/2067 熔断全停。

### 2.3 campaign-sc（SC 战役，m3.1flash + GLM-5.3-Flash 车道）

`solve_sc.sh` / `solve_glm.sh`：zcode（`--mode yolo`）/ mcode（`--permission full --timeout 25m`），OS timeout 1800s；**reps=3**（默认）；判分同 `judge.sh`（官方 pytest）；统计按 (arm,task) 的 reps 通过率/any/both（`aggregate_sc.py`）。

**历史条件要点**：原生 CLI 完整系统提示、无显式温度（供应商默认）、无自管对话循环（轮限由 CLI 内部策略 + 墙钟兜底）、k=1（reps 系列为方差实验）、官方容器判分。

---

## 3. 我们现状（af-bench / af-harness 源码原文）

来源：`af/crates/af-bench/src/{main.rs,swev.rs,tb.rs}`、`af/crates/af-harness/src/{spec.rs,run.rs,endpoint.rs,http.rs}`（2026-10-20 工作区源码，A）。

### 3.1 swe-v 生效参数（main.rs `run_swev`）

| 参数 | 现值 | 源码位置 |
|---|---|---|
| max_turns | **60**（1 turn = 1 次模型调用；run.rs L401 `turn_index >= max_turns` 即 `RunStatus::MaxTurns`） | main.rs L624 |
| tool_free_turn_limit | **3**（连续 3 轮无工具调用即停） | main.rs L627 |
| 完成信号 | 助手文本包含 `TASK_COMPLETE` | main.rs L626 |
| 温度 / top_p | `temperature_milli: None, top_p_milli: None` → **请求体不带该字段 = 供应商默认** | 各 profile |
| max_tokens | None → **Anthropic 协议默认 8192**（endpoint.rs L16 `ANTHROPIC_MAX_TOKENS_PLAIN=8192`；spec.rs 注释：2026-10-20 修复前硬编码 1024，"52.7% 运行被截断杀死"） | endpoint.rs |
| reasoning 档位 | 全部 profile `ReasoningTier::Off` → **不发送 thinking / reasoning_effort 字段** | 各 profile |
| 单题预算 | `BudgetBinding::Cents` **100 cents（$1）**，超即 `budget_exhausted` | main.rs L667-671 |
| k 值 / 重试 | 1 次采样 + **scaffold v2 gate 反馈重试（attempt≤2）**：零 diff → 带 `[Harness feedback]` 重入；diff 碰测试文件 → 同。**新对话、同一容器状态**。另有 HTTP 层 429/5xx 指数退避 ≤5 次、401 换钥重试 1 次（http.rs `max_retries: 5`） | main.rs L580-697 |
| 工具集 | **单 bash 工具**：`tb.rs bash_tool_decl`，描述注明每命令 `cd /testbed`；执行 = `docker exec <容器> bash -lc 'cd /testbed && <cmd>'`，**每命令超时 180s**，输出截断 12KB（头 6K+尾 6K），前置 exit 码 | tb.rs L129-151, L238-251 |
| 同命令重复警告 | 6 条历史内重复 ≥2 次的命令，注入 `[harness] You have issued this exact command N times...` | main.rs L592-612 |

### 3.2 scaffold v2 提示原文（main.rs L501，逐字）

```
You are an autonomous software engineer working inside a Linux container. The repository checkout is at /testbed. Fix the issue described by the user.

Rules:
1. Investigate with the bash tool, then edit files to implement the fix. A run that ends with no code changes is an automatic failure.
2. Never modify test files or test configuration (any path containing 'test', plus conftest.py, tox.ini, pytest.ini, setup.cfg). The grading harness owns the tests and rejects any patch that touches them.
3. Before finishing, run the relevant tests to verify your fix.
4. Keep the change minimal and focused on the issue.
5. When the fix is complete and verified, reply with a short summary that ends with the token TASK_COMPLETE and do not call any more tools.
```

（约 1.1KB / 5 条规则。TB 线系统提示为另一段 4 句短文，main.rs L845。）

### 3.3 用户消息构造（swev.rs L24-35）

```
Repository: {repo}

Issue description:
{problem_statement}

Hints:            ← 仅当数据包 hints_text 非空时追加
{hints_text}
```

### 3.4 判分链（swev.rs）

git diff 取证（`git -c core.fileMode=false diff`）→ 官方 `eval_script` 写入容器执行（**timeout 1200s**）→ 本地 `tools/swev-judge.py`（swebench 4.1 官方解析器）裁决。官方 harness 的 eval 超时默认为 **1800s**（`run_evaluation.py --timeout default=1_800`）。

---

## 4. 对齐表

数值后括号为来源编号（见 §7）。"—"= 不可得/未显式设置。

| 参数 | mini-swe-agent（官方榜/Vals） | SWE-agent v1.x 默认 | OpenHands eval | cal2-zcode | cal2-mcode | af-bench 现状 |
|---|---|---|---|---|---|---|
| 轮/步上限（模型调用） | **250 steps**（1.1①） | 无硬步限（1.2） | 100 iterations（1.3） | CLI 内部策略，无显式（不可得，墙钟兜底） | 同左 + 内部 25m | **60**（3.1） |
| 成本上限/题 | **$3**（1.1①） | $3（1.2） | $4（1.3） | 无（额度熔断除外） | 无 | **$1**（3.1） |
| 温度 | yaml 未设=默认；论文口径 0.0（1.1②） | **0.0**（1.2） | **0.0**（1.3） | 未设=CLI 默认（不可得） | 同左 | 未设=供应商默认（3.1） |
| top_p | — | 1.0（1.2） | 1.0（1.3） | — | — | 未发送 |
| max_tokens | Vals："开到最高"（1.1③） | 供应商默认 | — | CLI 默认（不可得） | 同左 | **8192**（Anthropic 协议默认；10-20 前 1024 事故）（3.1） |
| k（采样次数） | **1**（1.1①） | 1 | 1 | **1** | 1（reps=2 为方差实验，2.2） | 1 + gate 反馈重试≤2（3.1） |
| 系统 prompt | 1 行 + 实例模板 ~90 行（含提交协议）（1.1①） | 1 行 + 实例模板（1.2） | CodeAct 长系统提示（1.3） | **CLI 原生完整系统提示**（2.1） | 同左 | 自定义 5 规则 ~1.1KB（3.2） |
| 输出格式约束 | 每轮≥1 个 bash 调用 + 提交命令（1.1①） | 1 action/轮（default.yaml） | agent 循环 | CLI 原生 | CLI 原生 | TASK_COMPLETE 文本 + 禁再调工具（3.2） |
| 工具集 | 单 bash（1.1①/③） | bash+edit bundle（1.2） | bash+IPython+edit（1.3） | CLI 原生全套 | 同左 | **单 bash**（3.1） |
| 命令超时 | 60s（1.1①） | 默认（不可得，本文档未核） | — | CLI 默认 | CLI 默认 | 180s（3.1） |
| 观察截断 | 10KB（头5K+尾5K）（1.1①） | 100K 字符（1.2） | — | CLI 默认 | CLI 默认 | 12KB（头6K+尾6K）（3.1） |
| 问题输入 | 仅 problem_statement（1.1①） | 仅 problem_statement（1.2） | 仅 problem_statement（1.3） | （TB 任务指令） | 同左 | problem_statement **+ hints_text**（3.3） |
| 失败反馈重试 | 无（格式错误模板除外） | 无 | 无 | 无 | run 级失败重试≤3（非模型失败）（2.2） | **gate 反馈重入≤2**（3.1） |
| 墙钟超时 | 无（步/钱兜底） | 无 | — | **1500s** | **1800s + 内部 25m** | 无全局 agent 墙钟（仅命令 180s + eval 1200s） |
| eval 判分 | 官方 run_evaluation（1800s/题）（1.4①） | 同左 | 同左 | TB：官方 pytest exit 0（2.1） | 同左 | 官方 eval_script + 4.1 解析器，**1200s**（3.4） |
| 判分测试保护 | 官方链路 | 官方链路 | 官方链路 | tests 移出可猜路径 + canary 审计（2.1 E2） | 同左 | diff 碰测试文件 gate（3.1） |

---

## 5. 差异清单（现状 vs 标准口径，含方向性影响保守估计）

| # | 偏差 | 对照标准 | 方向性影响（保守） |
|---|---|---|---|
| D1 | **max_turns 60** vs 250 步（mini）/100 迭代（OpenHands）/无硬限（SWE-agent、我方 cal2） | §1.1/1.2/1.3 | **显著压低**。每 turn=1 模型调用，60 次对需要装依赖/跑测试的题严重不足；max_turns 失败=该题必挂。这是当前失配的主因，量级至少是被 max_turns 截断题占分母的比例 |
| D2 | **成本上限 $1** vs $3（mini/SWE-agent）/$4（OpenHands） | §1.1-1.3 | 压低。长题在 60 轮内先撞钱墙（budget_exhausted 同样归零）；并发度越低、单题可烧预算越该放宽 |
| D3 | **max_tokens 8192** vs Vals"最高可能" | §1.1③ | 压低。大 diff/长思考被截断 → 格式错误循环 → 烧轮次。10-20 前的 1024 曾致 52.7% 运行截断（spec.rs 注释），属已修 harness 缺陷但证明该参数敏感 |
| D4 | **hints_text 注入** vs 三个标准 harness 均只给 problem_statement | §1.1①/1.2/1.3 | **抬高（虚高）**。官方 hints 是面向解题者的补丁提示，标准口径不含；与榜单对比时我们占了便宜。要可比必须去掉 |
| D5 | **gate 反馈重试 attempt≤2**（新对话+同容器，带失败反馈） | 标准无此机制 | **抬高（虚高）**。相当于免费 repair 轮；榜单口径是单次采样。保留须单列口径（如 SWE-bench 的 batched/repair 类目） |
| D6 | **温度未显式设置** vs 标准口径 0.0（SWE-agent/OpenHands/mini 论文口径） | §1.1② | 中性偏负。供应商默认（GLM/Anthropic 默认通常 1.0）方差大：复现性差（cal2 §十二实测逐题翻转 16-20%），且高温度下工具格式失败率更高 |
| D7 | **reasoning Off（不发 thinking）** vs cal2 原生 CLI（zcode 默认 high thinking）与榜单"GLM 5 **high**"口径 | §1.4/2.1 | 对 thinking 型模型（GLM-5.3 系）**压低**推理深度；与榜单 high 档提交不可比 |
| D8 | **TASK_COMPLETE 文本信号 + 连续 3 无工具轮即停** vs mini 的显式提交命令 | §1.1① | 轻微压低。模型长篇分析（几轮不调工具）会被提前切断；功能上与提交协议近似但语义更脆 |
| D9 | **eval 超时 1200s** vs 官方 1800s | §3.4 | 轻微压低。慢测试套件被误杀成 fail/infra |
| D10 | 单 bash 工具、每命令 180s、12KB 截断 | mini：60s/10KB | 基本对齐（略宽松），中性 |
| D11 | 无全局 agent 墙钟（cal2 有 1500-1800s 硬超时） | §2.1 | 中性偏负：模型挂死时 run 无限等待（infra 风险），对通过率无直接方向性 |
| D12 | 同命令重复警告注入（6 条历史内 ≥2 次） | 标准无 | 轻微正向（对齐我们 60 轮下的防循环），对齐 250 轮后作用减弱 |

---

## 6. 对齐配置建议

### 6.A 与公开榜单可比（mini-swe-agent 口径）

1. **max_turns 60 → 250**（1 turn = 1 模型调用，与 mini step 同义）。
2. **单题成本上限 $1 → $3**（BudgetBinding::Cents 100 → 300；同步 spec per_turn 记账）。
3. **max_tokens 设为各供应商请求上限的最大允许值**（Anthropic 协议显式给大值；不再依赖 8192 协议默认），对齐 Vals"highest possible"。
4. **显式采样参数：temperature=0.0、top_p=1.0**（GLM/Anthropic 端点照发；若某端点不支持 0.0 则记录并保持该供应商默认，声明在结果行）。
5. **用户消息去掉 `Hints:` 段**（swev.rs `prompt()` 不再追加 hints_text）。
6. **关闭 gate 反馈重试（attempt 恒为 1）**，或保留但结果行分列 `pass@1` 与 `pass@1+repair` 两个口径，报告只用前者对榜单。
7. **reasoning 档位显式化**：模拟"GLM 5 high"榜口径 → GLM 系 profile 置 `ReasoningTier::High`；模拟 mini 默认（不发 thinking）→ 保持 Off，但结果行必须声明档位。
8. **eval 超时 1200 → 1800s**（对齐官方 `--timeout` 默认）。
9. 保留单 bash 工具与 diff 判分链（与 mini 语义一致）；建议把系统提示的任务指令部分向 mini 实例模板靠拢（明确"只改非测试文件 + 提交后不得再操作"），把 TASK_COMPLETE 升级为"提交后不得再调工具"的硬语义。

### 6.B 与 cal2 历史可比

1. **换回原生客户端执行面**（zcode `--mode yolo` / mcode `exec --permission full --timeout 25m`）作为 cal2 口径泳道——af-harness 自管循环再怎么调参也不是"原生 CLI 完整系统提示"形态，严格可比只有原生泳道。
2. 若坚持 af-harness 跑 cal2 口径：**thinking=high**（zcode provider 默认；step 系模型对齐 medium，见 cal2 E3）、**墙钟硬超时 1500s/题**（grok 泳道 3750s）、**k=1 且无反馈重试**、温度保持供应商默认（与 cal2 同为"未显式"）、PREAMBLE 式任务包装（环境说明+约 25 分钟+DONE 声明）。
3. 判分沿用官方 pytest exit 0（TB 线 af-bench `verify()` 已同构，注意 cal2 后期三判分缺陷修复：pytest 环境自检、root 残留清理、5400s 构建超时——af-bench 的 root 清理已实现）。

### 6.C TB 线（顺带）

- 现值 max_turns=40 + $1。官方 terminus-2 默认不设轮限（1e6）+ 温度 0.7 + 任务级超时；第三方评测口径 250–2000 turns 不等。建议 **max_turns ≥ 200**（对齐 Artificial Analysis 的 250 档）并把温度显式化（Terminus-2 默认 0.7），成本上限随 §6.A 提到 $3。

---

## 7. 来源清单（等级标注）

**A（官方源码，直接抓取原文）**
1. mini-swe-agent `src/minisweagent/config/benchmarks/swebench.yaml`（step_limit 250 / cost_limit 3 / timeout 60 / 提交协议）：https://github.com/SWE-agent/mini-swe-agent
2. mini-swe-agent `src/minisweagent/config/default.yaml`（1 行系统提示、THOUGHT+单命令格式约束）
3. SWE-agent `sweagent/agent/models.py`（temperature 0.0 / top_p 1.0 / per_instance_cost_limit 3.0）与 `config/default.yaml`：https://github.com/SWE-agent/SWE-agent
4. SWE-bench 官方 harness `swebench/harness/run_evaluation.py`（`--timeout` 默认 1800）：https://github.com/SWE-bench/SWE-bench
5. terminus-2 `terminal_bench/agents/terminus_2/terminus_2.py`（max_episodes 默认 None→1e6、temperature 0.7）：https://github.com/harbor-framework/terminal-bench-1
6. 我方源码：`af/crates/af-bench/src/{main.rs,swev.rs,tb.rs}`、`af/crates/af-harness/src/{spec.rs,run.rs,endpoint.rs,http.rs}`；legacy 脚本：`参考/legacy/{cal2,campaign-sc,mcode-campaign}/`（含 REPORT.md、incidents.md）

**A-（榜单发布者官方页）**
7. Vals.ai SWE-bench 方法论（统一 mini-swe-agent、单 bash、max tokens 开到最高、2026-09-01 归档）：https://www.vals.ai/benchmarks/swebench
8. swebench.com 官方榜（mini-swe-agent 为默认提交 harness；GLM-4.6 55.4%、GLM 5 high 72.8%、MiniMax M2 61.0 等）：https://www.swebench.com

**B+（官方报告/README，细节不全）**
9. mini-swe-agent 官方文档（swebench 用法、workers 默认 1、redo 语义）：https://mini-swe-agent.com/latest/usage/swebench/
10. Kimi K2 官方 README（65.8% pass@1、bash/editor、单次尝试、无 test-time compute）与 tech report（arXiv:2507.20534）；K2.5 README（temp=1.0/top_p=0.95 默认）：https://github.com/moonshotai/kimi-k2
11. MiniMax-M2 官方 README（R2E-Gym on OpenHands；榜单 mini-SWE-agent 61.00；M2.1 67.0/74.0；M2.5 80.2%）：https://github.com/MiniMax-AI/MiniMax-M2
12. z.ai GLM 博客与 GLM-5 技术报告转引（77.8%）：https://z.ai/blog/glm-5.1 ；GLM-5.2 卡片（TB2.1 Terminus-2 max_turns=2000、temp 1.0、max_tokens 64000）：https://huggingface.co/zai-org/GLM-5.2

**B（第三方/社区转引，已与官方源码交叉核对）**
13. mini-SWE-agent 复现论文（temp 0.0、250 步、$3、k=1；OpenAI 模型 1.0）：arXiv:2511.13646
14. SWE-bench Live 论文（OpenHands 臂：60 迭代、temp 0.0、top_p 1.0）：arXiv:2505.23419
15. OpenHands eval 默认（max_iterations=100、max_budget_per_task=$4）：https://github.com/OpenHands/OpenHands/issues/9730 、/issues/2140 、/issues/2651
16. EvalScope TB4.0 文档（max_turns 默认 None=Harbor agent 默认）：https://evalscope.readthedocs.io/en/v1.13.0/benchmarks/terminal_bench_v4.html
17. Artificial Analysis 方法论（TB 经 Harbor+Terminus-2、max_turns 250）：https://artificialanalysis.ai/methodology/intelligence-benchmarking

**不可得（明示）**
- GLM-5 技术报告 77.8% 所用内部 harness 的步数/温度/预算细目（报告未公开完整参数；榜单 mini-swe-agent 臂参数即 §1.1）。
- Kimi K2 内部 scaffold 的 SWE-V 采样温度（在 tech report PDF 正文，本次未逐页核验；K2.5 系默认 temp=1.0 可引）。
- MiniMax M2 技术报告所用 R2E-Gym+OpenHands 臂的迭代上限与温度（README 未列）。
- cal2 各闭源 CLI（zcode/mcode/step/kimi）的内部默认轮次上限（脚本未显式设置，实际由 1500–1800s 墙钟兜底）。
- SWE-agent bash 命令默认超时秒数（本次未核到常量定义，不臆断）。
