# Benchmark 可获得性实测记录

- 实测日期：2026-10-19；机器：本机 Linux；外网走 `socks5h://100.64.0.3:1080`（git/curl 均验证可用），HF 官方站可直连（代理），hf-mirror.com 也可直连。
- 克隆位置：`~/bench-study/`（下表给出各本地路径）。
- 结论速览：9 项中 8 项可拿到数据/代码；唯一完全拿不到的是 GAIA（gated，需 HF 账号接受条款后自动批准）。METR 的"563 条人类基线原始记录"未见独立机器可读发布，但按任务聚合的人类基线数据可直接拿到。

## 总表

| # | 条目 | 数据/代码可得性 | 实测证据 | 本地路径 |
|---|------|----------------|----------|----------|
| 1a | METR HCAST 任务集 | 可得（MIT，任务源码公开；部分资产在 DVC） | `github.com/METR/hcast-public` 克隆成功，含 9+ 任务族（debug_small_libs、esolang、hypothesis_testing、make_web_server、password_check、sentiment_probe、sql_injection、symbolic_regression、sparse_adversarial_perturbations、local_research*），`suite_manifest.yaml` 列 uuid+版本+任务清单 | `~/bench-study/hcast-public` |
| 1b | METR Vivaria | 可得 | `METR/vivaria` 克隆成功；README：基于 METR Task Standard 启动任务环境，`server/` 为 TS+PostgreSQL 服务，用于跑 agent 评测。HCAST 任务符合 Task Standard，可经 vivaria 或 `inspect-metr-task-bridge`(Inspect) 运行 | `~/bench-study/vivaria` |
| 1c | 563 条人类基线 | 部分可得：**原始逐条记录未见独立机器可读发布**；按任务聚合的基线数据已拿到 | HCAST 论文(arXiv:2503.17354)摘要明确"189 tasks, 563 human baselines (1500+ hours)"；论文 HTML 只链 `hcast-public`+`vivaria`，无独立 563 条数据文件。时间针分析仓库 `METR/eval-analysis-public` 内 `reports/time-horizon-{1-0,1-1}/data/raw/runs.jsonl` **直接随 git 提交**（非 DVC），每行含 `human_minutes/human_score/human_source="baseline"` | `~/bench-study/eval-analysis-public` |
| 1d | time-horizon 50% 时长数据机器可读版 | 可得 | runs.jsonl v1.0：41629 行、170 任务、151 个有基线任务，来源 HCAST 22690/RE-Bench 1676/SWAA 17263，34 个模型；v1.1：24008 行、228 任务、162 基线任务、21 模型。50% 时长=logistic 拟合（`src/horizon/`），输入数据即此 jsonl，可自行重算 | 同上 |
| 2 | LHTB 2.0 (Long-Horizon-Terminal-Bench 2.0) | 可得（arXiv 页确实没写，但数据已发布） | 论文 arXiv:2610.14146（77 任务、13 域、90min→3h、每 30min verifier checkpoint、1145 runs/15 模型）。仓库 `zli12321/LHTB`：`tasks/` 46 个原任务 + `tasks-2.0/` 31 个新任务=77；HF 数据集 `IntelligenceLab/Long-Horizon-Terminal-Bench`；Harbor Hub `silrlab/long-horizon-terminal-bench-2.0`。**检查点 verifier 形态**：每任务 `tests/private/{judge.py, dense_reward.py, offcode6_oracle.py, variant.json}`——judge 产出"门控检查 JSON"（gate 失败即停，防中途分作弊），dense_reward.py（stdlib-only）把 judge.log 转为阶梯连续分写入 `/logs/verifier/reward.txt`；`task.toml` 含 `continue_until_timeout=true`+pinned docker sha256；repo 内捆绑改版 Harbor（binary 拒绝回路+verifier 隔离补丁，README 称 17 个满分中 14 个靠偷看 grader，故加了进程冻结） | `~/bench-study/LHTB` |
| 3 | BAGEN | **已实际开源**（2026-05-27 release） | GitHub `mll-lab-nu/BAGEN` 克隆成功（RAGEN/verl 改，40MB）；HF `MLL-Lab/BAGEN`（445 文件，`origin/`+`estimation/`+`manifest.jsonl` 索引）。**rollout-replay 协议有代码**：`scripts/budget-estimation-benchmark/prepare_{swebench,miniswebench}_dialogues.py` 从 origin rollout 构造前缀对话，`run_token_estimation_env.py`/`run_token_estimation_vllm.py` 离线回放前缀让模型估"剩余预算能否完成"（协议：比较前缀已耗 X2+剩余需求 Y2 vs 总量 X3+Y3，输出 `<answer>[est_low,est_high]</answer>` 或 `impossible`）；`estimation/*_pairs.json` 即成对样本。四个 setting：Sokoban/Search-R1/SWE-bench 风格/Warehouse(多资源) | `~/bench-study/BAGEN` |
| 4 | ToolMaze | 可得（代码+数据分离） | GitHub `Zhudongsheng75/ToolMaze` 克隆成功（框架：`toolmaze/core` + `evaluation/core/sandbox.py` 扰动沙箱 + `tools/`272 个插件/4 类 YAML 定义）；**数据在 HF `dongsheng/ToolMaze`**（未 gated）：perturbed_tasks 2000 条(c1-c4 各 500=100 任务×P0-P4)、tasks 400、templates 400，实测计数。**扰动引擎确定性**：实例 JSON 带 `perturbation_mode`(P0-P4)+`perturbation_point`(int)+预计算 perturbation map，sandbox 按 trace 中 `is_perturbed` 标记注入，含 `alternatives.yaml` 备选输出池。**改造为"预算违规注入集"工作量**：中等偏低——注入点/注入时机机制现成，需新增预算记账与违规事件类型（types.py 已有 P0-P4 枚举+可选步骤标记），复用其 execution_trace 推导每步预算，判分侧加预算违规指标；估 1-2 周管道改造+批量重生成 | `~/bench-study/ToolMaze` |
| 5 | TaskBench (microsoft/JARVIS) | 可得 | 稀疏克隆 `taskbench/` 目录：3 个域数据（data_huggingface 7458 行、data_dailylifeapis 4318 行、data_multimedia），每域 `data.json`(JSONL)+`graph_desc.json`+`tool_desc.json`+`user_requests.json`+`alignment_ids.json`。**DAG 格式**：每行 `{id, seed, n_tools, type: single/chain/dag, sampled_nodes:[{task,...}], sampled_links, instruction, tool_steps, tool_nodes:[{task,arguments}], tool_links}`，`graph_desc.json={nodes:[{id,desc}],edges}` 为全局 Tool-Graph。**转工厂 Task Graph 草稿：直接可行**——sampled_nodes/links 本身就是带参数的 DAG，schema 映射+指令字段已在，写个转换脚本即可出草稿 | `~/bench-study/JARVIS/taskbench` |
| 6 | AgentHarm | 可得（上次被拦，本次 hf 官方站走代理实测成功） | `ai-safety-institute/AgentHarm`（注意大小写，旧 id 307 重定向到此）。`benchmark/`6 个 JSON 全部匿名可下：harmful/benign × test_public/validation + chat_public×2。实测下载 2 个文件并抽查：**每集合 176 条**，字段 `{id, id_original, detailed_prompt, hint_included, name, category, prompt, target_functions, grading_function,...}`，带 canary_guid。抽查例：harmful"用 SD 生成政客握手图→AI 视频→发 X 造谣"；benign 同结构改教育视频（互为对照） | `/tmp/agentharm_harmful.json` |
| 7 | GAIA | **匿名不可得，gated:auto** | API 元数据显示 `"gated":"auto"`（登录+接受条款后自动批）。实测匿名 `resolve/main/2023/validation.jsonl` → **HTTP 401**"Access to dataset ... is restricted"；连 README 也要鉴权。hf-mirror 代理同源，无 token 同样拿不到。结论：流程可行但需注册 HF 账号点同意 | 未下载 |
| 8 | MLE-bench | 可得（数据需 Kaggle 账号） | `openai/mle-bench` 克隆成功；README：**75 个 Kaggle 竞赛**（repo 内 `mlebench/competitions/` 84 项含 init/extra），每竞赛自带数据准备+评分脚本；因 Kaggle 不给 held-out test，官方脚本把公开 train 重新切分出私有 test。数据获取：Kaggle API `mlebench prepare --all`（官方称从零约 2 天）或 `--lite` 子集；部分数据走 git-lfs。**GPU 需求**：官方参考硬件 36 vCPU/440GB RAM/**1×24GB A10**，agent 本身不吃训练 GPU | `~/bench-study/mle-bench` |
| 9 | LiveCodeBench | 可得 | HF org `livecodebench/`：code_generation（原版 test.jsonl **9.4GB** 含图片）、**code_generation_lite**（2025-06-05 更新）、execution(-v2)、test_generation、submissions，全部未 gated。**当月新题机制**：lite 版按 release 累积 `test.jsonl…test6.jsonl`，加载脚本 `_VERSIONS_CONFIGS` 定义 release_v1…v6/latest；每题自带 `contest_date`(如 2025-01-04)+`contest_id`(abc387)，"当月新题"=按 contest_date 窗口过滤，新 release 追加文件即可增量评测，无需重下全量 | `/tmp/lcb_t6_head.jsonl` |

## 内容质量印象（顺手抽查）

- **METR runs.jsonl**：字段极规范（task_id/scaffold/tokens_count/score_binarized/human_minutes/human_cost/equal_task_weight），一条记录即一次完整 agent run+对齐的人类基线，直接可做"难度-时长"分析，质量高。
- **AgentHarm**：条目结构工整，harmful/benign 一一对照（同 id_original 成对），grading_function 机器可判，适合直接复用为工具滥用注入模板；公开子集仅 176 条/集合，量不大但每条含多步工具调用链。
- **BAGEN**：rollout 按"模型×128 seeds"成规模存放（gpt5.2/opus4.7/gemini3.1-pro/sonnet4.6/qwen3-235b），warehouse 单文件 40-50MB；estimation 侧除数据外还带任务运行配置（注意内含作者机器路径 /u/ylin30/...，复现时需改路径）。
- **ToolMaze**：单实例 JSON 8KB(c1)~200KB(c4)，期望执行轨迹显式存档，模板→任务→扰动三层生成链完整，工程化程度好；但 repo 本身不含实例，必须另下 HF 包。
- **LHTB 2.0**：任务工程化最重（pinned docker sha256、门控 judge+阶梯奖励、防作弊补丁带事后审计数字），reconstruction.json/gate_report.json 把"重构任务流水线"的中间产物也公开了，值得借鉴。

## 遗留障碍

1. GAIA：需 HF 账号（gated:auto，自动批准），本机无 token，未实测登录后下载。
2. MLE-bench：原始数据要 Kaggle 账号+约 2 天下载，本次只核对了管道与数据形态。
3. HCAST 563 条原始人工记录：论文与仓库均未给出独立机器可读文件；如需逐条数据只能联系 METR 或用 runs.jsonl 的聚合基线近似。
4. LHTB 完整仓库 ~107MB（含大量任务资产），代理下 clone 慢，本次用 `--filter=blob:limit=200k --sparse` 取代码与任务定义；若要跑任务需再拉全量与 docker 镜像。
