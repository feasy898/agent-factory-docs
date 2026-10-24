# 评估器质检方向 benchmark 实测记录（eval-bench）

> **实测人/时间**：benchmark 实测子代理，2026-10-19 深夜
> **实测环境**：本工作机 Linux，外网全部走 `socks5h://100.64.0.3:1080`；HF 走代理**直连可用**（`hf-mirror.com` 反而返回 308 不可用）；pip 走清华镜像。所有数字均为本机实际下载/解密/逐行统计所得，非转抄。
> **落盘位置**：克隆/下载放 `~/bench-study/`（judgebench_hf、JudgeBench/JudgeBench-main、dark-current-v2-review、rewardbench2、hal、longjubai、agent_token_consumption_analysis）。
> **方法纪律**：本文只记录实测到的东西；没测到的（如未实际运行的判题）明确标注"未实测"。

---

## 1. JudgeBench —— 评估器准入考卷（可克隆，已抽样 3 条）

### 1.1 可获得性（实测）
- 官方仓库：**github.com/ScalerLab/JudgeBench**（论文 arXiv:2410.12784，Sijun Tan et al., Princeton 等）。
- **克隆过程如实记录**：`git clone` 经代理 3 次尝试均在 index-pack 阶段断链（`invalid index-pack output`）；改用 `codeload.github.com` tarball 下载也两次超时（7.1MB/180s 后断）。**第三次重试得到部分完整 tar 并解压**，关键目录 `data/`、`README.md` 完整到手；`outputs/` 下的判题示例文件损坏（tar 异常 EOF），**judge 输出格式未能实测**。对"当考卷用"无影响——考卷本体在 `data/`。
- HF 数据集 **ScalerLab/JudgeBench**（gated=False）：`data/` 下两个 jsonl（claude 898.5KB / gpt 1914.2KB），已单独完整下载到 `~/bench-study/judgebench_hf/`，与仓库内 `data/` 同格式。

### 1.2 数据格式（实测自 `data/dataset=judgebench,response_model=gpt-4o-2024-05-13.jsonl`）
每行一个 JSON 对象，字段：`pair_id`（UUID）、`original_id`（源数据集题号）、`source`、`question`、`response_model`、`response_A`、`response_B`、`label`（**客观正确性金标**，取值 `A>B` / `B>A`，无平局、无人类偏好含义）。

- 行数实测：**gpt-4o-2024-05-13 350 对 + claude-3-5-sonnet-20240620 270 对**（README 称 350 unique pairs by GPT-4o / 270 by Claude-3.5-Sonnet，一致）。
- 标签分布实测：gpt 集 A>B=193 / B>A=157；claude 集 A>B=143 / B>A=127（两选项大体均衡，不能靠位置偏置猜）。
- 来源分布实测（gpt 集）：**MMLU-Pro 14 学科 × 11 题 = 154**，**LiveBench-math 56、LiveBench-reasoning 98、LiveCodeBench 42**；claude 集同构（34/51/31）。即知识/推理/数学/代码四域。

### 1.3 抽样 3 条摘录（seed=42 随机抽，节选）
1. `[livecodebench] label=A>B`
   - Q：「网格 H 行 W 列，每格一个小写字母……(题面为 AtCoder 式构造题)」
   - A：`# YOUR CODE HERE def find_snuke_path(H, W, grid): target = "snuke" ...`（沿四方向搜 "snuke" 路径）
   - B：`def find_snuke_positions(H, W, grid): ...`（只找位置不构路径，函数语义已偏）
2. `[livebench-reasoning] label=A>B`
   - Q：「实体正八边形 ABCDEFGH，沿 AF、BE、CH 切三刀，问得到多少个四边形」
   - A：「为确定切片数……让我们系统分析」（推理起点正确）
   - B：「要解决该问题……让我们从分解八边形开始」（同为流畅长推理，结论路径不同）
3. `[mmlu-pro-physics] label=B>A`
   - Q：「蓝色的互补色是 (A)绿 (B)黑 … (J)青，10 选项」
   - A：「要确定互补色需理解色轮……」（开头通顺但选错）
   - B：「要找互补色需用色轮，互补色混合后相互抵消……」（选对）

**关键观察**：三条的共同点是**两个回答都长、都流畅、都"像对的"**，金标只看客观正确性。这正是考卷的毒性的来源。

### 1.4 它测评估器什么、为什么 GPT-4o 只比随机略好
- **测什么**：judge 在"难问题上成对回答"的二选一**客观正确率**（accuracy over 350/270 对）。论文摘要（arXiv:2410.12784，已抓取原文）原文：「many strong models (e.g., GPT-4o) performing **just slightly better than random guessing**」。
- **为什么难（论文口径 + 数据旁证）**：(1) 流水线刻意从"难数据集"取题，回答错误往往错得很深，表面痕迹少；(2) 金标是客观正确性而非众包偏好，judge 平时对齐的"人类偏好先验"（长=好、流畅=好、自信=好）在这里系统性失灵；(3) 两回答风格对齐（同题、同模型、长度量级相当），style 捷径被削弱；(4) 位置均衡设计堵住位置偏置。→ 对工厂的含义：**这 620 对就是现成的"评估器准入考卷"，judged accuracy 显著高于 50% 且带置信区间才准上岗**（具体跑分本机未实测，需 API 预算）。
- 可改造点：`label` 是 A>B 二值，可直接算 accuracy/Wilson 置信区间；`source` 字段天然支持四域分层报告（与 Dark Current 的"分层看子集"纪律同构）。

---

## 2. Dark Current（LLM Judges Have Dark Current）—— 零假设门仪表（仓库已克隆，声明逐行验证通过）

### 2.1 可获得性（实测）
- 论文：**arXiv:2606.15610**「LLM Judges Have Dark Current: Stratified Null and Utility Tests for LLM Judge Reliability」（v2 改题 A Psychometric Datasheet for LLM-as-a-Judge Evaluation；Usami, Hara, Tsuboi, Matsuda；中部大学；**2026-10-13 已投 TMLR**，README 自述）。
- **不存在名为 "darkcurrent-bench" 的独立 HF 数据集**（HF search "judgebench/darkcurrent" 均无此名条目；GitHub 搜索也无）。**官方代码+数据仓库为 github.com/usamihiroyasu/dark-current-v2-review**（从 arXiv HTML 全文页里挖到的唯一仓库链接），`git clone` 一次成功（19MB）。
- 重要范围限制（README/LICENSE_SCOPE 自述）：**"Raw benchmark text, candidate bodies, raw responses, weights … are excluded"** —— 仓库只有记录与哈希，没有 RewardBench 2 原文。要复跑需自备上游数据。

### 2.2 数据结构（实测）
- `held_source485/`：**records.jsonl 2,910 行 = 485 行 RB2 题材 × (克隆对 1 × 2 准则 + 信号对 2 × 2 准则)**；calls_metadata.jsonl 2,910 行（每对的 A/B 角色 sha256、期望判定 `expected_canonical_choice` 等）；proxy/selected_metadata 各 485 行。
  - 克隆对实测判定分布：**`dc_core_clone` 970 条（485 行 × neutral/strict），canonical 判定全部 `tie`（A=0/B=0）**；信号对 `signal_chosen_vs_rejected` 1,940 条：neutral 下 A=497/B=450/tie=23，strict 下 A=449/B=406/tie=115（tie 变多 → 子集对齐被准则吃掉，与论文 Precise IF 58/154 的"聚合过、子集挂"叙事一致）。
  - 每条 record 字段实测：`config_id`（qwen35-local-q4km-raw，本地 ollama 量化模型）、`served_model: qwen3.5:35b-a3b`、`order`（IDENTICAL/AB/BA 各 970）、`winner`、`usage{prompt_tokens,completion_tokens}`、`latency_seconds`、`request_sha256/raw_response_sha256`、`timestamp_utc`。**审计记录自带 token 用量与耗时**。
- `legacy_v5/analysis/release/public_terminal_records_v5.jsonl`：**1,224 条终态记录**。克隆记录 408 条 = **4 个 (config×criterion) 单元 × 102 行**，实测四个单元的 `canonical_verdict` **全部 = tie，即 4 × (0/102)**，与 README 声明「all four configuration–criterion cells have 0/102 clone preferences」**逐行吻合**。judge_id 实测：`qwen25_32b_awq_remote`、`qwen36_mlx_local` 两个配置。
- 摘录 1 条（held_source485/records.jsonl 首行，节选）：
  `{"call_id":"rb2hold:Factuality:67:dc_core:neutral:IDENTICAL","config_id":"qwen35-local-q4km-raw","pair_type":"dc_core_clone","order":"IDENTICAL","usage":{"completion_tokens":6,"prompt_tokens":1400},"latency_seconds":5.36,"winner":"tie","valid":true}`

### 2.3 对工厂的价值（实测判断）
- 这不是一个"考卷"而是一台**零假设门仪表**：把字节级相同克隆对喂给评估器，任何非 tie 偏好即 dark current > 0。全套审计工程（预注册、哈希链、IDENTICAL/AB/BA 三序、neutral/strict 双准则、克隆门与效用水远分开报告、分单元看子集）可直接照抄成工厂"评估器自检"协议。
- 门槛极低：克隆门只需本地小模型 + 1,400 prompt tokens/条 ×970 对（实测 record 均值量级），单机可日跑。
- 风险：论文是注册报告体例、仓库自称 "Author-review candidate. No release has been authorized"；核心新颖度靠 102/485 两组记录支撑，**复现需自带 RB2 文本**。

---

## 3. RewardBench 2 —— 防刷分轮换题库（HF 直连可下，已读全量）

### 3.1 可获得性（实测）
- **huggingface.co/datasets/allenai/reward-bench-2**（走代理直连），`gated=False, private=False, license=odc-by, arxiv:2506.01937`，单文件 `data/test-00000-of-00001.parquet`（**6,973,189 字节**，经断点续传 3 次下完）。

### 3.2 数据格式（pyarrow 实测全量）
- **1,865 行**。列：`id, prompt, chosen, rejected, num_correct, num_incorrect, total_completions, models, subset, additional_metadata`。
- 每题从 **4 个候选 completion** 里构对：`chosen`/`rejected` 均为单元素列表（从 4 选 1 正确 + 1 错误组成对）；实测 (num_correct, num_incorrect) 组合 **(1,3) 占 1,763/1,865**，其余为 1 correct vs 13~18 incorrect 的长尾（个别题采了更多 completion）。
- subset 分布实测：**Focus 495 / Factuality 475 / Safety 450 / Math 183 / Precise IF 160 / Ties 102**。`models` 列共 **45 个不同生成模型**（top：gpt-4o-2024-08-06 939 次、Llama-3.1-70B 818、jailbreak 724）。
- 摘录 1 条（id=0，节选）：prompt=「Hi do you know how to fix Codeium …[deadline_exceeded]…」，chosen=["Certainly! …"]，rejected=['To resolve the "deadline_exceeded" error …']，`subset=Factuality`，`additional_metadata.correct="ONE", method="natural"`，models=[Qwen2.5-7B, Mistral-7B, Mistral-7B, Llama-3.1-8B]。
- 注意：**Factuality 子集才有 `correct="ONE"` 明确单选金标（475 条）**；Ties 子集金标逻辑是"多正确/全同"（metadata.correct=None），直接当二选一考卷会误用——按 subset 分层接。

---

## 4. HAL 公开日志 —— 止损指纹挖掘语料（已实际下载并解密 1 份）

### 4.1 获取方式（实测）
- 入口 `hal.cs.princeton.edu`（SPA）。**9 个 benchmark 各有页面**（/gaia /swebench_verified_mini /usaco /taubench_airline /assistantbench /corebench_hard /online_mind2web /scicode /scienceagentbench），页内每行 leaderboard 条目带 trace 直链：**`huggingface.co/datasets/agent-evals/hal_traces/resolve/main/<benchmark>_<agent>_<时间戳>_UPLOAD.zip`**。
- `agent-evals/hal_traces` 实测：**381 个加密 zip，共 113.1 GB**；每个 zip 内是单个 `<run>.json.encrypted`。
- **加密与解密（实测成功）**：zip → JSON{salt, encrypted_data} → **PBKDF2-HMAC-SHA256(480k 迭代) 派生 Fernet key，口令硬编码在官方脚本里：`hal1234`**（脚本 `hal.cs.princeton.edu/static/downloads/hal-decrypt.sh`）。官方口径："All agent traces are encrypted to prevent benchmark contamination through automated scraping" —— 实际口令公开，防的是脚本爬虫不是人。
- **本机实测样本**：`corebench_hard_hal_generalist_agent_1747200995_UPLOAD.zip`（945,255 字节，0.95MB）下载 + 解密成功。

### 4.2 轨迹字段清单（解密后逐键实测）
顶层 5 键：
- `config`：agent_name、benchmark_name、date、run_id、agent_args（model_name=claude-3-7-sonnet-20250219, budget=4）、**完整 run_command**（`hal-eval --benchmark … -A model_name=… --vm --max_concurrent 1`）。
- `results`：accuracy、written_accuracy、vision_accuracy、successful_tasks[]、failed_tasks[]（本样本 0/45 全失败——BadRequest 引爆，照样全量记录）。
- `total_usage`：**按模型聚合的 prompt_tokens/completion_tokens**（本样本 18,270/6,988）。**无现成 USD 字段，需自乘单价**。
- `raw_logging_results`：**57 条 W&B Weave span**，每条字段实测：`op_name`（全部 `litellm.completion`）、`trace_id/parent_id`（**可重建调用树**）、`started_at/ended_at`（时间戳）、`inputs{model, messages(全文), stop, kwargs}`、`output`（**OpenAI 格式完整回包：choices[].message.content + usage**）、`summary.usage`（每调用 token 数 + `latency_ms` + weave status）、`exception`（类型+消息，本样本 45/57 为 litellm.BadRequestError）、`wb_user_id/project_id`。

### 4.3 规模与"21,730"出处
- **21,730 rollouts 出自 HAL 论文**（arXiv:2510.11977，Kapoor et al.：「conducting **21,730 agent rollouts** across 9 models and 9 benchmarks, at a total compute/API cost of roughly **$40,000**」，搜索核实）。**官网首页现报 "26 597 Rollouts / 9 Benchmarks"**（2026-10 实测，网站已比论文时点增长）。
- **止损指纹挖掘可行性**：高。每次 rollout = 一棵 litellm 调用树，含逐调用 token 数、时延、异常、完整 messages——"花了多少钱、第几步开始空转、哪种异常后还在继续烧"均可直接统计。样本 45/57 调用抛异常仍继续跑，本身就是"亏钱模式"现成案例。限制：(a) 无 USD 字段需配价表；(b) 全库 113.1 GB 加密 zip，全量下需代理+磁盘规划，按 benchmark/agent 选包下载即可；(c) Weave span 的 parent 树要自己重建。

---

## 5. How Do AI Agents Spend Your Money —— 成本指纹语料（格式已实测，mini 包下载中）

### 5.1 获取方式（实测）
- 论文：**arXiv:2604.22750**「How Do AI Agents Spend Your Money? Analyzing and Predicting Token Consumption in Agentic Coding Tasks」（摘要已抓取：**8 个前沿模型 on SWE-bench Verified**；同任务重复运行 token 总量最大差 **30 倍**；更高消耗不等于更高准确率，准确率在中等成本见顶后饱和；Kimi-K2、Claude-Sonnet-4.5 平均比 GPT-5 多烧 **>150 万 tokens**；人类难度标注与真实 token 成本仅弱对齐；自预测相关性最高 **0.39** 且系统性低估）。
- 项目页 `longjubai.github.io/agent_token_consumption`：
  - **代码**：github.com/LongjuBai/agent_token_consumption_analysis（已克隆；**只有分析脚本，无数据**；`dataset/extract_llm_completions_with_stats.py` 泄露原始数据布局：`<model>_maxiter_100_N_v0.31.0-no-hint-…-run_4/llm_completions/<instance_id>/*.json`）。
  - **数据**：**HF `loong0814/openhands_trajectories`**（gated=False）：15 个 tar.gz 共 **41.91 GB** = 9 个模型文件（claude-sonnet-3.7/4/4.5(+new_v2)、gemini-3-pro-preview、gpt-5、gpt-5.2、kimi-k2、qwen3-coder-480b），全量版 2.4–10 GB/个，**`_mini` 精简版 65–98 MB/个**。
- **500 题 × 4 runs 的口径**：目录名实测为 `…-run_1`（流内已见），脚本与 README 指向每模型 4 runs；"500 题"来自论文口径（SWE-bench Verified 500 实例），**mini 包内实例数未清点完（下载未完）**，全量包对应关系未逐包核验——此两点如实标注。

### 5.2 轨迹格式（从下载流中直接抽取首文件实测）
- 布局：`gpt-5_4runs/gpt-5-2025-08-07_maxiter_100_N_v0.62.0-no-hint-run_1/llm_completions/django__django-16263/gpt-5-2025-08-07-1767173201.6350198.json`
- **每个 JSON = 一次 LLM 调用**，字段实测：`messages`（90 条，完整对话含 system）、`response`（choices + **usage：prompt 74,466 / completion 2,069，含 `reasoning_tokens:1600`、`cached_tokens:73216` 明细**）、**`cost: 0.0314045`（litellm 算好的 USD，逐调用）**、`kwargs.tools`（5 个工具定义）、`timestamp`。finish_reason=tool_calls。
- **对工厂的可行性**：这是五件套里**成本指纹最现成的语料**——逐调用 USD cost + cached/reasoning token 拆分 + 工具调用序列 + 4 次重复运行的方差，可直接做"止损指纹"（如：第 N 轮后 cached_tokens 增长但测试不收敛 → 早停）。mini 版一个模型 78.5MB，9 个模型 mini 全收约 650MB，代理可承受。

---

## 6. 横向结论（对工厂评估器质检线的落点）

| 件 | 角色 | 规模（实测） | 直接可用产物 | 主要缺口 |
|---|---|---|---|---|
| JudgeBench | 评估器**准入考卷**（客观正确性金标） | 350+270 对，四域 | jsonl 即考卷；四域分层 | 需 API 跑 judge 得基线；outputs 示例损坏 |
| Dark Current | 评估器**零假设门**（克隆对仪表） | 0/102×4 + 970 克隆对全 tie | 完整审计协议照抄；记录含 usage/latency | 原始 RB2 文本不随仓库发；单 judge 配置 |
| RewardBench 2 | 评估器**防刷分轮换题库** | 1,865 行 6 子集 | 单 parquet 直接加载 | Ties 子集金标逻辑特殊； Factuality 才有单选金标 |
| HAL traces | **止损指纹语料**（agent 全轨迹） | 381 zip / 113.1 GB / 论文 21,730 rollouts ≈ $40K | 逐调用 token+时延+异常+调用树 | 无 USD 需配价；全量大；需解密脚本 |
| openhands_trajectories | **成本指纹语料**（逐调用 USD） | 15 包 41.91 GB（mini 650MB 量级） | cost 字段现成；cached/reasoning 拆分 | mini 实例覆盖未清点；无逐题对错标注需配 SWE-bench 金标 |

**组合建议**：准入用 JudgeBench（考卷）→ 上岗后用 Dark Current 协议做零假设自检（仪表）→ 换题防刷分用 RewardBench 2（题库）→ 语料层用 HAL + openhands_trajectories 挖"亏钱指纹"（多少钱一步、异常后是否继续烧、成本-准确率饱和点）。四者正好构成工厂 Evaluation 三态的"考卷-仪表-语料"闭环。

## 7. 阻塞与未尽事项（如实记录）
1. `git clone` 大仓库经代理频繁断链（JudgeBench 3 败），改 codeload tarball 仍有 2 次超时；**本机代理对 GitHub 大文件约 40KB/s**，RewardBench2 parquet 与 longjubai tar 均靠 `curl -C -` 断点续传完成/进行中。
2. 磁盘配额一度报警（「pwd: 写入错误: 超出磁盘配额」），系多任务并行下载瞬时触顶，后自恢复；`~/.cache` 有 7.4GB 非 本任务缓存未动。
3. JudgeBench `outputs/` 判题示例文件损坏未读；judge 基线跑分（如 GPT-4o 在其上的具体百分数）**本机未实测**，论文只有定性表述。
4. longjubai mini 包完整清点（每 run 实例数、4 runs 是否齐）待下载完成后补；HAL 全量 113.1GB 未下载，仅 0.95MB 样本。
5. "darkcurrent-bench" 独立数据集**不存在**（已搜证），Dark Current 的数据载体即 `usamihiroyasu/dark-current-v2-review` 仓库本体。
