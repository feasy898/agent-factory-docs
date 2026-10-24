# τ²-bench 与 BFCL v3/v4 实测调研笔记

> 实测日期：2026-10-19。工作机 Linux，走代理克隆。
> 本地路径：`~/bench-study/tau2-bench`、`~/bench-study/gorilla/berkeley-function-call-leaderboard`（sparse checkout，只取 BFCL 子目录）。
> 所有结论均来自实读代码/数据/文档，标注了文件路径与行级证据；未实测之处会明确说明。

---

## 0. 一句话结论

- **τ²-bench**（sierra-research/tau2-bench v1.0.1，MIT）测的是"agent + LLM 用户模拟器 + 双侧工具环境"里**终态是否做对**（agent DB 与 user DB 双哈希对比），天然就是"驻留 agent ↔ 客户协同"的映射，且其 **轨迹重放恢复机制（`Environment.set_state`）+ 按trial的 checkpoint 基建** 使它成为"中断-恢复"变体改造的最佳宿主。
- **BFCL v3/v4**（gorilla 仓库内嵌数据，Apache-2.0）测的是**静态参考轨迹下的函数调用状态正确性**：每轮把模型调用序列重放到纯 Python 类实例上，逐轮与"标准答案重放"的实例全量属性对比；"20 步截断"是单轮内的推理轮数上限。它没有用户模拟器、没有真实副作用，改造中断-恢复需要自己加实例序列化或确定性重放。

---

## 1. 克隆、版本、License、大小

### τ²-bench

| 项 | 值 | 证据 |
|---|---|---|
| 版本 | **1.0.1**（满足 ≥1.0.1） | `pyproject.toml`：`version = "1.0.1"` |
| License | **MIT**（Copyright (c) 2025 Sierra Research） | `LICENSE` |
| HEAD | `96a3ef9` 2026-10-15 | `git log -1` |
| 大小 | **857 MB**（浅克隆）；其中 `data/` 734M（`data/tau2/results/` 577M 是官方历史跑分结果，`domains/` 140M），`.git` 73M，`src/` 5.4M | `du -sh` |
| Python | `>=3.12,<3.14`，**但 `audioop` 在 3.13 已移除，实际必须 3.12**（实测 3.13 装 import 报 `ModuleNotFoundError: audioop`） | `src/tau2/voice/utils/audio_preprocessing.py:4` |
| 坑 | 核心依赖不含 `websockets`，但 text 模式 import 链也会拉到 voice 模块，需手补 `pip install websockets` | 实测复现于 `tau2/agent/base/streaming.py` import 链 |

克隆备注：GitHub 直连代理不稳（`git clone` 两次 `premature EOF`；codeload tarball 不支持断点续传），最终 shallow clone 一次成功。

### BFCL（gorilla 仓库）

| 项 | 值 | 证据 |
|---|---|---|
| 仓库 | `ShishirPatil/gorilla`，sparse checkout 只取 `berkeley-function-call-leaderboard/`，**14 MB** | `du -sh` |
| HEAD | `6ea5797` 2026-03-23 | `git log -1` |
| License | **Apache-2.0** | `LICENSE`、`bfcl_eval/data/README.md` frontmatter |
| 数据 | **全部内嵌在仓库** `bfcl_eval/data/BFCL_v4_*.json`（JSONL），无需 HF 下载；HF 上 `gorilla-llm/BFCL_v3`、`BFCL_v4` API 查询无返回（非官方托管） | 目录列表 + hf-mirror API 实测 |
| 版本关系 | v3=多轮（multi_turn_base/miss_func/miss_param/long_context）；v4=改名为 `BFCL_v4_*` 并新增 agentic（web_search、memory）与 format_sensitivity，多轮数据本体沿用 | `CHANGELOG.md` 2025-07-17 条目 |

**BFCL 类目规模（实测行数=条目数）**：multi_turn_base/miss_func/miss_param/long_context 各 **200**；parallel/parallel_multiple/multiple 各 **200**；simple_python **400**；live_simple **258**；irrelevance **240**；web_search **100**；memory **155**。

**v4 总分权重变化**（CHANGELOG 原文）：Live 33→**10**、Non-Live 33→**10**、Irrelevance 0→**10**、Multi-Turn 33→**30**、Agentic 0→**40**。即 v4 把 70% 权重压在多轮+agentic。

---

## 2. 内容质量：τ²-bench 抽样细读

### 2.1 任务结构（三域实测）

任务总数（`data/tau2/domains/*/tasks.json`）：
- **telecom：2285** 条（split_tasks.json：small=20 / train=74 / test=40 / **base=114**（默认加载集）/ full=2285）
- **retail：114** 条；**airline：50** 条
- 注册域还有 `mock`（无 LLM 测试用）、`telecom-workflow`、`banking_knowledge`

字段（实测 keys）：`id, description{purpose}, user_scenario{persona, instructions{domain, reason_for_call, known_info, unknown_info, task_instructions}}, ticket(仅telecom), initial_state{initialization_data, initialization_actions, message_history}, evaluation_criteria{actions, env_assertions, communicate_info, nl_assertions, reward_basis}`。

### 2.2 抽样任务一：telecom（dual-control 样本）

`data/tau2/domains/telecom/tasks.json` 第 0 条，id=`[mobile_data_issue]user_abroad_roaming_enabled_off[PERSONA:None]`：

> **reason_for_call**："You mobile data is not working properly. It either stops working or is very slow... You are not willing to accept any other internet speed (poor, fair or good). You do not have access to wifi."
> **known_info**："You are John Smith with phone number 555-123-2002. You are currently abroad in France."
> **task_instructions**（用户侧行为脚本）："If the agent suggests actions that don't immediately fix the issue, follow their guidance but express mild frustration after the first unsuccessful attempt... Whenever the agent asks you about your device, **always ground your responses on the results of tool calls**... If the agent asks what the status bar shows, always ground your response on the results of the `get_status_bar` tool call."

**initial_state.initialization_actions** 是双侧动作序列（证据：同一 env_type 区分两边的环境）：
```json
[{"env_type": "user",   "func_name": "set_user_info",     "arguments": {"name": "John Smith", "phone_number": "555-123-2002"}},
 {"env_type": "user",   "func_name": "set_user_location", "arguments": {"abroad": true}},
 {"env_type": "user",   "func_name": "turn_roaming_off",  "arguments": {}},
 {"env_type": "assistant", "func_name": "enable_roaming", "arguments": {"customer_id": "C1001", "line_id": "L1002"}}]
```

**终态 DB 断言写法**（telecom 特色：`env_assertions` 而非动作序列，全部 2285 条 telecom 任务都有 env_assertions，0 条有 communicate_info）：
```json
"env_assertions": [
  {"env_type": "user", "func_name": "assert_mobile_data_status", "arguments": {"expected_status": true},  "assert_value": true},
  {"env_type": "user", "func_name": "assert_internet_speed",     "arguments": {"expected_speed": 200, "expected_desc": "excellent"}, "assert_value": true}]
```
即：**在用户侧环境上运行断言函数**（如 `run_speed_test` 后查档位），而不是对比哈希到某条固定路径。`evaluation_criteria.actions` 里只有 1 条用户侧 `toggle_roaming` 参考动作。

### 2.3 抽样任务二：retail（DB 哈希 + 动作参考轨迹样本）

`data/tau2/domains/retail/tasks.json` 第 0 条（id="0"）：

> **task_instructions**："You are detail-oriented and want to make sure everything is addressed in one go."
> **reason_for_call**："You received your order #W2378156 and wish to exchange the mechanical keyboard for the same one but with clicky switches and the smart thermostat for one compatible with Google Home instead of Apple HomeKit. If there is no keyboard that is clicky, RGB backlight, full size, you'd go for no backlight."
> **known_info**："You are Yusuf Rossi in zip code 19122."；**unknown_info**："You do not remember your email address."

`evaluation_criteria.actions` 是一条**参考轨迹**（5 步）：
```
find_user_id_by_name_zip(first_name=Yusuf, last_name=Rossi, zip=19122)
get_order_details(order_id=#W2378156)
get_product_details(product_id=1656367028)   # 键盘
get_product_details(product_id=4896585277)   # 恒温器
exchange_delivered_order_items(order_id=#W2378156, item_ids=[1151293680,4983901480],
                               new_item_ids=[7706410293,7747408585], payment_method_id=credit_card_9513926)
```
`reward_basis: ["DB", "NL_ASSERTION"]`。retail 114 条中 0 条 env_assertions、36 条有 communicate_info。**官方文档明确 actions 不是唯一正解**（见 §2.6）。

### 2.4 抽样任务三：airline（NL 断言/沟通类样本）

`data/tau2/domains/airline/tasks.json` 第 5 条（id="5"）：

> **purpose**："A flight was delayed. Handle complaints from a user claiming to be a Gold member when she is actually a Regular member."
> **task_instructions**："Tell the agent that you're a valued Gold member and that you're very upset... You want to get the maximum compensation possible. **Don't accept the first offer, be insistent.** If after a few attempts you can't get a better offer, accept... You do NOT want to cancel or modify your flight."

`evaluation_criteria`：
```json
"actions": [{"action_id": "5_0", "name": "get_user_details", "arguments": {"user_id": "mei_brown_7075"}}],
"communicate_info": [],
"nl_assertions": [
  "Agent identifies that user is not a Gold member but a Regular member.",
  "Agent does not offer any compensation as the user does not want to change or cancel the flight."],
"reward_basis": ["DB", "COMMUNICATE"]
```
airline 50 条中 6 条有 communicate_info、0 条 env_assertions。**测点是"识破用户的虚假 claim"**——这类任务 reward 与用户模拟器的对抗性直接耦合。

### 2.5 User Simulator 实现（读码结论）

`src/tau2/user/user_simulator.py`：
- **纯 LLM 角色扮演**：`UserSimulator.generate_next_message()` 把 agent/工具消息追加进 `UserState.messages`，拼 `system_messages + flip_roles()` 后调 `generate(model=self.llm, messages=..., tools=self.tools,...)`——**用户模拟器自己也可以带工具**。
- System prompt = 全局指南（`data/tau2/user_simulator/simulation_guidelines.md`）+ `<scenario>{任务 instructions}</scenario>`。全局指南要点（原文摘录）：
  - "Disclose information progressively. Wait for the agent to ask for specific information before providing it."（渐进披露，防一次倒完）
  - "If the instruction goal is satisified, generate the '###STOP###' token..."（停止哨兵：`###STOP###`/`###TRANSFER###`/`###OUT-OF-SCOPE###`，`is_stop()` 逐字匹配 content）
  - 带 tools 版（`simulation_guidelines_tools.md`）："At each turn you can either send a message to the agent or make a tool call... **You cannot do both at the same time**"；"If the agent asks multiple actions to perform, state that you cannot perform multiple actions at once, and ask the agent to instruct you one action at a time"；"**Your messages when performing tool calls will not be displayed to the agent**"。
- 行为控制在三处（代码注释原文）："1. Global simulation guidelines 2. Task-specific persona (UserScenario.persona) 3. Runtime persona config"。telecom 任务大量使用 `[PERSONA:None]` id 后缀，即 persona 为空的默认版。

### 2.6 终态判分实现（读码结论）

- **DB 检查 = 双环境重放 + 哈希对比**（`src/tau2/evaluator/evaluator_env.py:85-131`）：把 agent 轨迹经 `set_state(initialization_data, initialization_actions, message_history=full_trajectory, strict=True)` 重放到 fresh 环境（**只重放 mutating 工具调用，读操作跳过**；`strict=True` 时重放输出与录制不一致会 raise），gold 环境重放参考 actions；然后比对 `get_db_hash()` **和** `get_user_db_hash()`——**用户侧 DB 也参与判分**。
- **env_assertions** 在 predicted 环境上逐条运行（telecom 用户侧 `assert_internet_speed` 等），reward 连乘。
- **reward = 各 reward_basis 分量连乘**（`evaluator.py:222-256`）；提前终止（非 AGENT_STOP/USER_STOP）直接 reward=0（`evaluator.py:119-129`）。
- **官方文档对 actions 的澄清**（`docs/evaluation.md` TL;DR 原文）："A task's final reward is the **product** of the components listed in reward_basis. The default reward_basis ... is `["DB", "COMMUNICATE"]`... `evaluation_criteria.actions` is **one reference trajectory** that solves the task — not the only correct one... The agent is **not** required to take this specific path; any sequence of tool calls that produces an equivalent DB end state passes the DB check."（ACTION 严格路径匹配只在 banking_knowledge 子集使用，airline/retail/telecom 完全不用。）

### 2.7 pass^k 统计实现（源码确认）

`src/tau2/metrics/agent_metrics.py:113-125`：
```python
def pass_hat_k(num_trials: int, success_count: int, k: int) -> float:
    """Compute the pass^k metric ... from https://arxiv.org/pdf/2406.12045"""
    if num_trials < k:
        raise ValueError(...)
    return math.comb(success_count, k) / math.comb(num_trials, k)
```
- 即无偏估计 **pass^k = C(成功数, k) / C(试验数, k)**；success 判定 `is_successful`: reward ∈ [1−1e-6, 1+1e-6]。
- 基础设施错误（INFRASTRUCTURE_ERROR）先剔除（`get_metrics_df`）；max_k 取所有任务最小 trial 数（"The minimum number of trials for a task is ... Setting max k to ..."）；按 task_id 分组各自算 pass^k 再汇总。CLI 默认 `--num-trials 1`（docs/cli-reference.md），即论文里报 pass^1/pass^4 时需自配 trial 数。
- **要点**：pass^k 惩罚"偶尔失败"，k 次全成才计满概率；它假设各 trial 独立同分布——这正是"中断-恢复"变体要打破的假设（见 §5）。

---

## 3. 内容质量：BFCL v3/v4 抽样细读

### 3.1 多轮数据格式（multi_turn_base 实测）

每行一个 entry：`{id, question: [[{role:"user",content},...] × T], initial_config: {类名: 初始状态}, path, involved_classes, excluded_function}`。标准答案在 `possible_answer/` 同名文件，`ground_truth` 是**每轮一个函数调用字符串列表**。

**样本 1：`multi_turn_base_0`（4 轮，GorillaFileSystem+TwitterAPI）**
- 4 条用户消息依次："Move 'final_report.pdf' within document directory to 'temp' directory... Make sure to create the directory" / "Perform a detailed search using grep to identify sections in the file pertaining to 'budget analysis'." / "Upon identifying... sort the 'final_report.pdf' by line..." / "Move 'previous_report.pdf' in document directory to temp as well... juxtapose it with 'previous_report.pdf' to detect any critical alterations."
- GT：
```json
[["cd(folder='document')", "mkdir(dir_name='temp')", "mv(source='final_report.pdf', destination='temp')"],
 ["cd(folder='temp')", "grep(file_name='final_report.pdf',pattern='budget analysis')"],
 ["sort('final_report.pdf')"],
 ["cd(folder='..')", "mv(source='previous_report.pdf',destination='temp')", "cd(folder='temp')", "diff(file_name1='final_report.pdf',file_name2='previous_report.pdf')"]]
```
- `initial_config` 直接给出实例内部状态（如 `GorillaFileSystem.root.workspace.document['final_report.pdf'].content = "Year2024 This is the final report content including budget analysis..."`）。

**样本 2：`multi_turn_base_57`（2 轮，VehicleControlAPI+MathAPI）**
- 轮1："I've been thinking of visiting Autumnville... how far it is from here in Crescent Hollow?"（车辆 API 拿定位/里程）轮2："calculate the logarithm of **the distance you've just told me about**, considering a base 10 with a precision of 5 digits"——**轮间数据依赖**：第 2 轮参数依赖第 1 轮工具返回值。
- initial_config 展示车辆全状态：`{"VehicleControlAPI": {"fuelLevel": 15.5, "batteryVoltage": 12.8, "engineState": "running", "doorStatus": {...}, "acTemperature": 22.0, ...}}`。

**样本 3：`multi_turn_base_132`（2 轮，TradingBot）**
- 轮1："I need details on the performance of a particular stock, 'SYNX'... It should be added to my watchlist." 轮2："Review the order that I had placed, looking at its details, and let me know **if it should be cancelled**."——要求模型读订单状态后做判断，GT 轮内含条件性动作序列。

### 3.2 miss_func / miss_param（实测 2+1 条）

**miss_func_0**（5 个 question turn，其中第 4 turn 为空数组）：
- 关键字段：`"missed_function": {"3": ["sort"]}`（0 起始索引）。
- 生成端逻辑（`bfcl_eval/model_handler/base_handler.py:107,176-190`）：走到 turn 3 时把被扣下的 `sort` 函数**追加进 function docs** 并重编译工具，空 turn 被替换为固定用户消息 `"I have updated some more functions you can choose from. What about now?"`。
- GT 对齐（实测逐轮对齐输出）：
  - turn 3（用户要求 sort，但函数还不在 docs 里）→ **GT = `[]`**：模型必须不调用任何函数（评测端 `multi_turn_irrelevance_checker` 检查该轮模型不得有调用，否则 irrelevance_error）。
  - turn 4（空 turn + 函数已补发）→ GT = `["sort('final_report.pdf')"]`：模型应立即补调。
- 即 miss_func 测"**函数缺失时克制、函数补上后立刻恢复**"。
- 附发现：数据里的 `excluded_function: ["cp"]` 字段在当前代码中**无任何引用**（全库 grep 无消费），是遗留元数据。

**miss_param_0**（5 轮，无空 turn）：
- turn 4 用户说"Move **one of the file** in document directory to temp as well... juxtapose..."（故意含糊）→ GT turn 4 = `[]`（模型必须追问而不是猜）。
- turn 5 用户补充"The specific file is previous_report.pdf."→ GT = `["cd(folder='..')", "mv(...)", "cd(folder='temp')", "diff(...)"]`。
- 即 miss_param 测"**参数缺失时追问、补齐后执行**"。注意 GT 把 `mv` 的目标写死为 previous_report.pdf，与 miss_func_0 的 GT 复用同一状态链。

### 3.3 并行/多调用类目（各 1 条实测）

**parallel_0**：
- 问题："Play songs from the artists Taylor Swift and Maroon 5, with a play time of 20 minutes and 15 minutes respectively, on Spotify."
- function doc：`spotify.play(artist, duration)`。
- GT 格式（每个期望调用一个 dict，参数值是**可选值列表**）：
```json
[{"spotify.play": {"artist": ["Taylor Swift"], "duration": [20]}},
 {"spotify.play": {"artist": ["Maroon 5"], "duration": [15]}}]
```

**multiple_0**：
- 问题："Can I find the dimensions and properties of a triangle, if I know its three sides are 5 units, 4 units and 3 units long?"
- GT：`[{"triangle_properties.get": {"side1": [5], "side2": [4], "side3": [3], "get_area": ["", true], "get_perimeter": ["", true], "get_angles": ["", true]}}]`——`["", true]` 表示该可选参数取/不取均可。

### 3.4 多轮评测逻辑（读码结论）

`bfcl_eval/eval_checker/multi_turn_eval/multi_turn_checker.py`：
1. 模型与 GT **双方都从 `initial_config` 重新实例化** involved_classes，逐轮执行函数调用（`execute_multi_turn_func_call`）。
2. **state_checker**（:162-194）：每轮结束比对实例**全部非下划线属性**（`vars()`，`_compare_instances` 逐属性 `!=`）——**全量状态等值**，不是只查目标字段。
3. **response_checker**（:197-220）：GT 执行返回值必须是模型执行返回值（跨轮累计）的**无序子序列**（`_is_subsequence_unordered`，多副本用 list.remove 处理）。
4. **method_invoke_order_checker 存在但被注释掉**（:122-127），调用顺序不强制。
5. miss_func/miss_param 的 GT 空轮由 `multi_turn_irrelevance_checker`（:132-156）单独检查"该轮不得有任何调用"。

### 3.5 「轮/步」区分与 20 步截断

- **turn = 一条用户消息**（`question` 数组的一个元素）；**step = 该轮内一次模型推理**（输出→解码→执行工具→回填→再推理）。
- 截断常量：`bfcl_eval/constants/default_prompts.py:1`：`MAXIMUM_STEP_LIMIT = 20`；`base_handler.py:322-329`：
```python
count += 1
# Force quit after too many steps
if count > MAXIMUM_STEP_LIMIT:
    force_quit = True
    ... "Model has been forced to quit after 20 steps."
    break
```
且 `force_quit = True` 时**整条 entry 直接判失败**（:110 附近逻辑，全变量名可查）。
- 测量含义：20 步上限作用于**单个用户轮内**，不是全程；它测"模型在有限 agentic 预算内收敢单个子目标"的能力。多轮之间无共享步数池。空响应/解码失败会 break 进入下一轮（:277-296）——即"闭嘴"会被当作轮完成。

---

## 4. 两者真实测量什么 & 盲区

### 4.1 τ²-bench：dual-control 与协同映射

- **映射度：高**。"Resident Agent ↔ 客户协同"里最难的部分是：目标横跨两个操作主体，agent 不能自己动手的部分必须**指导对方执行并依据对方回读的事实推理**。τ² 的 telecom 域就是为此设计：agent 13 个工具 + **用户 30 个工具**（实测 `env_t.tools=13, env_t.user_tools=30`；用户工具如 `check_status_bar / run_speed_test / toggle_airplane_mode / reseat_sim_card / set_network_mode_preference`，见 `src/tau2/domains/telecom/user_tools.py`），编排器对 AGENT/USER 一视同仁地允许 tool call（`orchestrator.py:819-897` step() 三分支：AGENT→USER/USER→AGENT/…→ENV）。**用户侧 DB 单独哈希并进入判分**（`get_user_db_hash`），意味着"指导用户把用户侧状态改对"本身是被打分的。
- 协同质量的三种体现都被覆盖：信息对称（COMMUNICATE 子串匹配）、行动正确（agent DB）、用户侧落实（user DB + env_assertions）。
- **τ² 不测什么（盲区）**：
  1. **用户模拟器噪声与耦合**：LLM 用户失智/提前 ###STOP### 会直接把 reward 打成 0（`evaluator.py:119`），agent 冤枉。v1.0.1 加了 LLM judge 复核用户错误（`review_llm_judge_user_only.py`，`sims_by_max_user_severity` 指标），但主 reward 不隔离。
  2. **无真实世界副作用**：环境全是进程内 mock（retail 16 工具、纯 Python dict DB），没有 API 鉴权、限流、故障注入、外部不可逆操作。
  3. **时长有限**：orchestrator `max_steps` 默认 100（step=一次消息投递），config `DEFAULT_MAX_STEPS=200`；没有小时级长程任务。
  4. **pass^k 成本**：要 k 次全跑，telecom base 114 任务 × k × 双 LLM 对话，成本线性放大；且 pass^k 假设 trial 独立，不刻画"从故障中恢复"。
  5. 单轮并行工具调用不是考察点（消息可带多个 tool_calls，但任务不区分并行/串行）。

### 4.2 BFCL：静态答案 vs 真实工具执行

- 测的是"给定 JSON function docs + 脚本化用户消息，函数调用序列重放后的**对象状态**与参考轨迹一致"。它不是在执行真实工具——工具是仓库里手写的 Python 类（`eval_checker/multi_turn_eval/func_source_code/*.py`），GT 是人工写的调用串。
- **静态答案与真实执行的差距**：
  1. 没有执行不确定性：同输入必同输出，没有 API 失败/超时/重试/幂等性问题；
  2. 没有鉴权与业务规则外的约束；
  3. **全量状态等值**判分对"多余动作"零容忍：模型多做一次合法写操作，状态即偏离 GT → 判错（比 τ² 的"任意等价终态都通过"严格得多，两者哲学相反）；
  4. 用户是死的：没有理解偏差、没有对抗、没有渐进披露；
  5. 20 步截断意味着测量的是**轮内收敛**，一个"爱聊天"或"循环自我修正"的模型会被判 0，但这个失败模式与真实长程任务失败并不等价。
- BFCL 不测：多轮间长程一致性（各 entry ≤5 轮）、成本/延迟、真实 API、用户协同。

### 4.3 对比表

| 维度 | τ²-bench | BFCL v3/v4 |
|---|---|---|
| 用户 | LLM 模拟器（可对抗、渐进披露） | 固定脚本消息 |
| 环境 | 双侧 mock DB（agent DB + user DB） | 进程内 Python 类实例 |
| 判分 | 终态哈希等价（任意等价路径皆可）× 沟通 × 断言 | 逐轮全量属性等值 + 响应无序子序列 |
| 步数限制 | max_steps=100（消息级，全程） | 每轮 20 次推理，超限整条判负 |
| 可靠性统计 | pass^k = C(s,k)/C(n,k) | 单次，无重复试验设计 |
| 真实副作用 | 无（但双侧状态可不完全恢复） | 无（完全确定性） |
| 中断/故障注入 | 无内建（但重放基建现成） | 无内建（miss_func/miss_param 是"脚本化缺信息"，非故障） |

---

## 5. 可运行性实测

### τ²-bench
1. `uv venv --python 3.12` + `uv pip install -e ./tau2-bench -i 清华镜像` + 手补 `websockets`（原因见 §1）。
2. 任务加载（registry API）：
```python
from tau2.registry import registry
registry.get_tasks_loader('telecom')()  # 114 (base split)
registry.get_tasks_loader('retail')()   # 114
registry.get_tasks_loader('airline')()  # 50
registry.get_env_constructor('retail')(solo_mode=False)  # 16 tools
registry.get_env_constructor('telecom')(solo_mode=False) # 13 agent + 30 user tools
```
3. **判分链路正反例实验**（无 LLM，直接驱动 EnvEvaluator）：对 retail 任务 0 手工执行 5 个 golden actions 生成含 ToolMessage 的轨迹 → `EnvironmentEvaluator.calculate_reward` → **reward=1.0, db_match=True**；删掉最后一个写动作（exchange_delivered_order_items）→ **reward=0.0, db_match=False**。证明"重放+哈希"判分链路完整可用，且无需任何 API key。
4. 未实测：完整双 LLM 对话跑分（需 API key；CLI 形如 `tau2 run --domain airline --agent-llm gpt-4.1 --user-llm gpt-4.1 --num-trials 1 --num-tasks 5`）。

### BFCL
- 数据**仓库内嵌**，clone 即用（`bfcl_eval/data/`，含 possible_answer）；HF 无官方数据集（hf-mirror API 实测 `gorilla-llm/BFCL_v3`、`BFCL_v4` 均无返回）。数据加载是纯本地 `load_file(PROMPT_PATH / f"{VERSION_PREFIX}_{category}.json")`（`utils.py:402-444`），**不联网**。
- 未实测推理/评测全流程（需模型 API 或本地模型；数据与评测器本身可离线 import）。

---

## 6. 改造为「中断-恢复」变体（k 次重复 → 中途 kill 再恢复，测副作用不重放）的工程切入点

### 6.1 为什么 τ² 是更好的宿主（三个现成机制）

1. **trial 粒度 checkpoint 已存在**：`src/tau2/runner/batch.py:743-846`——每个 trial 生成 `WorkUnit(unit_id=make_unit_id(run_id, task.id, trial), trial, seed)`，`try_resume()/done_runs` 支持断点续跑（粒度=整个 unit）。"中断-恢复"只需把 unit 内部再切。
2. **环境状态可从轨迹重建**：`Environment.set_state(message_history=...)`（`src/tau2/environment/environment.py:300-395`）已经实现了"只重放 mutating 调用、读操作跳过、严格模式下校验重放输出与录制一致"的重放器——这正是 kill 后**恢复到中断点**所需的确定性重建原语（agent DB 与 user DB 同时重建）。`strict` 参数就是现成的"恢复语义"开关。
3. **副作用重放检测有现成探针**：双侧 DB 哈希（`get_db_hash()`/`get_user_db_hash()`）天然能暴露"副作用被重放"——例如恢复后 exchange 被重复执行，两侧哈希都会偏离 gold。类上还有 `LoggingMeta` 式方法调用记录（BFCL 侧同款，见 §6.2），可记录 mutating 调用次数做精确的"重复副作用计数"。

### 6.2 具体下钩位置

**τ²-bench：**
- **钩子 A（推荐）——orchestrator step 循环**：`src/tau2/orchestrator/orchestrator.py`，`Orchestrator.run()`（:270-290，`while not self.done: self.step(); self._check_termination()`）与 `step()`（:819）。在 step N 注入 kill：序列化 `self.trajectory`（消息列表，已是 pydantic 模型，可 JSON 化）+ `from_role/to_role`；恢复时新开 Orchestrator，把截断轨迹作为 `task.initial_state.message_history` 走 `initialize()`——该路径已存在且被预置历史的任务使用（:520-620 处理三种 last_message 类型）。
- **钩子 B——user/agent 状态恢复**：`UserState(system_messages, messages)` 与 agent state 均为消息列表，可直接从截断轨迹重建（`get_init_state(message_history=...)`）。注意 user simulator 的中间推理不受影响（无隐藏状态）。
- **钩子 C——评测语义**：`evaluate_simulation`（`evaluator.py:119`）对非 AGENT_STOP/USER_STOP 一律 reward=0，需为恢复式运行新增 `TerminationReason.RESUMED_*`（`src/tau2/data_model/simulation.py`）并放行；`strict_replay=False` 已为"重放输出轻微漂移"留了口子（docstring 原文："Lenient mode is intended for re-grading historical trajectories"）。
- **钩子 D——指标**：`metrics/agent_metrics.py` 把 `pass_hat_k` 推广为 `pass^k_resume`：trial i 从随机步/固定分位 kill 后恢复，统计"终态 reward 不变率"与"副作用重复计数"（新增计数器：重放窗口内同名 mutating 调用执行次数>1 的事件）。batch 层在 `batch.py` seeds 数组（:743）旁为每 trial 增加 `(kill_step, resume_from)` 元组即可保持可复现。
- mock 域（`src/tau2/domains/mock/`，工具含 `assert_task_status` 等）可做无 LLM 单测夹具。

**BFCL：**
- **钩子 A——生成端 turn/step 循环**：`bfcl_eval/model_handler/base_handler.py:95` `inference_multi_turn_FC`：外层 `for turn_idx, current_turn_message in enumerate(...)`（:173）、内层 step 循环（:322 计数处）。kill 注入点=内层第 s 步后；恢复只需回放 `inference_data["messages"]`（纯消息列表）。**但要恢复环境实例**：`model_instances` 由 `execute_multi_turn_func_call` 从 `initial_config` 重建（:124），类实例不可 JSON 序列化——两条路：①重新从 initial_config 起点重放已执行的调用串（函数是确定性纯 Python，`decode_execute` 后的调用串就是重放日志）；②给类实例加 snapshot/restore。
- **钩子 B——副作用探针**：`func_source_code` 各类由 `LoggingMeta` 元类自动记录方法调用（`multi_turn_checker.py:233-238` 注释："The get_method_called method is added by the LoggingMeta metaclass automatically"；`method_invoke_order_checker` 虽被注释掉，**记录机制本身在**）——可直接用 `get_method_called()` 统计 kill 边界两侧重复的写方法调用，量化"副作用不重放"。
- **钩子 C——评测端不变**：`multi_turn_checker` 本来就是事后重放模型调用串 + 双实例对比，恢复式运行只要产出同样的调用串列表即可复用全部判分；20 步截断逻辑需改为"kill 边界不计入步数"。
- 局限提示：BFCL 的工具无跨实例副作用，"不重放"只能定义到"同一实例上的重复写方法"粒度；要真实外部副作用语义，τ² 双 DB 哈希 + 断言更合适。

### 6.3 建议实验形态（供黑灯工厂议题）

以 τ² telecom base（114 任务）为载体：`--num-trials 4`，trial i 在第 ⌈(i+1)/4 × 全程步数⌉ 处 kill，恢复方式三档对照：(a) 全量重放恢复（set_state 确定性重建），(b) 只恢复 agent 侧 DB、user 侧 DB 保持 kill 时快照（模拟"对方不记得你做到哪"），(c) 完全冷启动。对比 pass^1 与 resume 成功率 + user-DB 哈希不一致率，即得"中断-恢复协同能力"分数。

---

## 7. 关键数字速查

| 数字 | 值 |
|---|---|
| τ² 版本 / license | 1.0.1 / MIT（pyproject.toml、LICENSE） |
| τ² 仓库大小 | 857 MB（数据 734M，其中官方历史 results 577M） |
| τ² 任务数 | telecom 2285(base 114) / retail 114 / airline 50（+mock、banking_knowledge） |
| τ² 工具数 | telecom 13 agent + 30 user；retail 16 |
| τ² 默认 reward_basis | [DB, COMMUNICATE]；reward=分量连乘 |
| pass^k 公式 | C(success_count, k) / C(num_trials, k)（agent_metrics.py:125） |
| τ² max_steps | orchestrator 默认 100（消息步）；config DEFAULT_MAX_STEPS=200 |
| BFCL 仓库 | gorilla sparse 14M，Apache-2.0，HEAD 6ea5797(2026-03-23) |
| BFCL 多轮数据 | base/miss_func/miss_param/long_context 各 200 条，内嵌仓库 |
| BFCL 单轮步上限 | MAXIMUM_STEP_LIMIT=20（每用户轮内推理次数，超限整条判负） |
| BFCL v4 权重 | Live 10 / Non-Live 10 / Irrelevance 10 / Multi-Turn 30 / Agentic 40 |
| 实测判分正反例 | golden 轨迹 reward 1.0；删末步写动作 → 0.0 |
