# 本地臂到底需要什么 —— 负载规格说明（anolis-gpu-01 / 2×V100S-32GB / ollama 0.40.6）

- 产出日期：2026-10-21
- 产出者：本地模型选型调研子代理（工作区 `调研/本地模型选型/notes/`）
- 任务来源：本轮调研的「本轮调研任务」段——"读工作区文件，产出『本地臂到底需要什么』的规格说明"
- 取证纪律：本文所有数字分两类标注：
  - **【直接证据】**= 本轮亲自读到的工作区文件 / 亲自跑过的命令（给出 `路径:行号` 或完整命令 + 输出要点）
  - **【转引】**= 同一工作区同期调研笔记（`notes/qwen-family.md` 等）已核实的外部事实（其原始 URL 见该笔记 §11），本文不重复外网取证
  - 未做的事一律写"未验证/未跑"，不用推测填空
- **未下载任何模型权重**；未在 anolis 上改动任何服务配置（只读 `/api/*`、读日志、`strings` 静态核验）

---

## 0. 一页纸结论（先说答案）

1. **负载画像与任务书给的口径有 4 倍量级偏差**：任务书写"每题约 10 轮工具调用"，实测（本地 30B 臂 122 道 SWE-V）**每题轮数中位数 40.5（D1）/ 50（D2），p90 = 60（fix1 上限）**；**每题模型输出 token 中位数 5.7K**；**单题墙钟中位数 302s（D1）/ 395s（D2），p90 986–1031s**。任何按"10 轮"算的墙钟预算都要重算。
2. **上下文长度需求 = 32K 起步、64K 保险**：anolis ollama 日志里 7,974 次真实模型调用的**上下文深度中位数 10,289 token、p90 20,830、p99 28,776、最大 63,157**。今天那次 135.7 tok/s 的微基准是在 **num_ctx=8192** 下测的——**比一半以上的真实调用还短**，不能拿它当产量口径。
3. **现役配置的瓶颈不是显存不够，是 KV cache 把显存吃干了**：S1 期间 ollama 实际以 **2 slot × 262,144 ctx** 装载，KV cache 占 **49,152 MiB（GPU0 22,528 + GPU1 26,624）**，加上权重后**两张 V100S 都在 97–98% 显存占用**。要换更大的模型，**必须先降 ctx 档位**。
4. **本地臂的角色定位要修正**：实测 30B 在 SWE-V 上的解题率是 **D1 37.0% / D2 19.4% / D3 15.0%（合计 27.3%，110 题有分）**，API 主力臂同代是 **GLM-5.3-Flash D1 62.7% / glm-max D1 76.8%**。所以本地臂**不是主链路的量产臂**，是：**①零 API 成本的并联量产/预筛臂；②API 熔断时的兜底臂；③cascade 的 stage-1 弱模型臂**（对应 50-方案 §2.3 的 E1/E2 升级策略）。前期结论"本地池定位弱模型档"成立，但**弱得比预期更具体**：只配 D1/D2，不配 D3。
5. **"换模型能提高解题率"在本地池里最多 +3~8 个点，且要付出 1.5–3 倍墙钟**：最强候选 **Qwen3-Coder-Next（80B-A3B）自报 SWE-V 70.6**，但**自报 Terminal-Bench 只有 34.2/36.2**（我们 workload 含 TB）→ 不是全面升级；且它 **48.19 GiB 权重 + KV** 会把显存顶到 96% 以上，**必须把 ctx 砍到 2×16K 或 2×32K**。
6. **两个当下就该修的工程缺口（与选型无关，但直接压本地臂产量）**：
   - **OpenAI 协议路径不传 `max_tokens`**（`af/crates/af-harness/src/endpoint.rs:186-213`）→ 本地 ollama 用自己的默认 `num_predict`，一轮可以吐到上下文满（≈26 万 token），撞 600s HTTP 读超时后被 harness 重试 → 白烧 GPU。
   - **OpenAI 协议路径也不传 `reasoning_effort`/thinking 开关**（同文件 `:204-206`）→ 想上 Qwen3.6-35B-A3B（默认 thinking）**没有旋钮可关**，token 必然膨胀。
7. **一条被日志证实的硬失败模式**：ollama 0.40.6 的 Unsloth chat template 会 **400 拒绝"结尾有两个以上 assistant 消息"的请求**（`Cannot have 2 or more assistant messages at the end of the list.`），日志里已实际发生 2 次（2026-10-20T16:45:24、2026-10-21T06:12:53）→ 本地臂的 tool calling 形态有**协议级边界**，不是所有 transcript 形状都能发。

---

## 1. 我们的负载画像（全部为直接证据）

### 1.1 题型清单与 agent 轮数

| 套件 | 入口 | 轮数上限 | tool-free 上限 | 完成信号 | 预算上限 | 判分链 |
|---|---|---|---|---|---|---|
| `injecagent` | `main.rs:1280-1424` | **16**（`:1318`） | 1（`:1320`） | 无 | $1（`:1364-1369`） | 规则口径：是否调用了攻击工具（`main.rs:517-536`） |
| `terminal-bench` | `main.rs:1084-1278` | **40**（`:1150`） | 3（`:1153`） | `TASK_COMPLETE`（`:1152`） | $1（`:1190-1197`） | 容器内官方 verifier 二值（`:1229`） |
| `swe-v` | `main.rs:653-954` | **250**（`:778`，fix2 从 60 提上来） | 3（`:781`） | `TASK_COMPLETE`（`:780`） | **$3**（`:817-823`） | 官方 eval_script + 官方判分器，**clean 容器**重跑 + `eval_sha256` 指纹（`:883-891`） |
| `swev-rejudge` | `main.rs:966-1082` | —（不重跑） | — | — | 0 LLM 成本 | 只重判存量 `agent.diff`（`:1048`） |

补充判分链细节：
- SWE-V 判分链的 eval 超时 **1800s**（`af/crates/af-bench/src/swev.rs:162` 注释 + `EVAL_TIMEOUT_SEC`），超时落 `EVAL_TIMEOUT_KILLED` 标记行。
- bash 工具超时：**缺省 180s、上限 600s**，由模型自己在工具入参 `timeout_ms` 里要（`main.rs:168-179`；常量在 `af/crates/af-bench/src/tb.rs:102,104`）。
- SWE-V 的采样口径：温度 0、top_p 1.0、**max_tokens 32000**（`main.rs:661-664`）——**注意这两项只对 Anthropic 协议生效**（见 §1.3）。
- 完成协议：模型必须**执行**一条打印 `TASK_COMPLETE` 的 bash 命令，纯文本提及不算（`main.rs:588-591` 的 instance 模板）。

**实测轮数**（本地 30B 臂，结果目录 `/tmp/bench-fix1-d{1,2,3}-30b/results.jsonl`，共 122 行；行内 `profile` 字段实测为 `qwen30b-local`）：

> **口径警告（两条，直接证据）**：①这些结果行里的 `scaffold` 字段是 **`v2`**，而 `main.rs:909` 现在写的是 `v3` ⇒ 这些是**更早一代**的结果；②这些行**没有 `judge_mode` 字段**（实测 62 行全为 `None`）⇒ 它们是 **POC-1 判分口径切换之前**的产物（判分在 agent 容器内原地判）。因此：**同代（fix1 目录族）内部横向可比，但不能和 fix2/fix3 的结果直接混算**（`计划/50-bench实测方案.md:312` 的版本隔离纪律）。

| 档 | 题数 | 轮数中位 | 轮数 p90 | max | 输出 token 中位 | 墙钟中位 | 墙钟 p90 | 墙钟 max |
|---|---|---|---|---|---|---|---|---|
| D1 | 62 | 40.5 | 60 | 60 | 5,756 | 302 s | 986 s | 1,387 s |
| D2 | 40 | 50 | 60 | 60 | 6,009 | 395 s | 1,031 s | 2,972 s |
| D3 | 20 | 31.5 | 60 | 60 | 4,757 | 140 s | 1,126 s | 1,355 s |
| 合计 | 122 | 40 | 60 | 60 | 5,756 | 329 s | 986 s | 2,972 s |

> 口径说明：这一代结果的 swe-v 轮数上限是 60（`main.rs:778` 现为 250，是之后才提上来的）。**p90=60 说明"打满轮数"是主要失败模式之一**，而 D1 的中位轮数 40 已经用掉三分之二预算。

**D1 的失败形态分布（直接证据，`/tmp/bench-fix1-d1-30b/results.jsonl` 62 行）**：

```
status:  completed 50 | max_turns 10 | run_failed 2
gate:    ok 44 | no_patch 11 | test_edit 5 | (None) 2
http_retries>0 的行数: 0
```

⇒ **11 题连补丁都没产出（no_patch）+ 10 题打满轮数**——这两类合计 21/62（34%）与"解题"无关，是**纪律/预算形态的失败**；`test_edit` 5 题是越权改测试被判无效（护栏正确拦截）。`http_retries` 全 0 ⇒ **本批没有一次 HTTP 层重试**（本地臂的供给面比 API 臂稳）。

### 1.2 每轮典型 token 量与上下文长度需求

**直接证据（anolis `/data/models/ollama-serve.log`，本轮用 python 逐行解析 7,974 次 `stop processing: n_tokens = N`）**：

```
ALL calls 7974 samples 7974
ctx depth: med 10289 p90 20830 p99 28776 max 63157
  ctx<    1000 : 115
  ctx<    4000 : 1172
  ctx<    8000 : 1750
  ctx<   16000 : 2995
  ctx<   32000 : 1929
  ctx<   99999 : 13
```

即：本地臂**每次模型调用带进去的上下文深度中位数 10.3K、p90 20.8K、p99 28.8K、最大 63.2K**。

**每轮 prompt 规模**（bench 结果反推，ollama 的 `prompt_tokens` 含缓存部分）：
- 30B 臂 D1：每任务 prompt token 总量中位 437,451 / 40.5 轮 ⇒ **平均每次调用 ≈ 9,504 token 的上下文**（同口径 D2 ≈ 9,785，D3 ≈ 8,088）。
- 缓存命中：ollama 报 `cache_read / input ≈ 96.9%`（中位 382,219 / 394,639）⇒ **增量 prefill 很少，但长上下文注意力每轮都要付**。

**KV 占用（直接实测）**：日志 `srv prompt_save: - saving prompt with length 23841, total state size = 2235.368 MiB` ⇒ **96.0 KiB / token**（2,235.368 MiB ÷ 23,841 token）。
按 48 层、4 KV 头、head_dim 128、f16 独立复算：(2×4×128×2 B)×48 = 98,304 B = 96 KiB/token —— **与实测吻合**。

**由此推出的上下文需求档位**：

| 档位 | 依据 | 每 slot KV（96 KiB/token） | 2 slot 合计 |
|---|---|---|---|
| 8K | 微基准所用；**低于一半真实调用的中位深度** | 0.75 GiB | 1.5 GiB（实测 1,536 MiB） |
| 16K | 覆盖 p90 深度 20.8K 的一半 | 1.5 GiB | 3.0 GiB |
| **32K** | **覆盖 p99 深度 28.8K（=生产必需下限）** | 3.0 GiB | 6.0 GiB |
| 64K | 覆盖实测最大 63.2K | 6.0 GiB | 12.0 GiB |
| 262K（现役实际） | S1 期间 ollama 实际装载值 | 24 GiB | **48 GiB（实测 49,152 MiB）** |

**结论：本地臂的 ctx 档位必须 ≥32K；262K 是"能跑但把显存吃光"的档位。**

### 1.3 tool calling 形态

**协议**：本地档案走 **OpenAI 兼容 `POST /v1/chat/completions`**（`main.rs:283-301`，`Protocol::OpenaiChatCompletions`，`base_url = http://127.0.0.1:11435/v1`，`stream = false`）。

**请求体由 harness 构造**（`af/crates/af-harness/src/endpoint.rs:186-213`）：

```rust
json!({"model":…, "messages":…, "stream": false})
+ "tools": [{type:"function", function:{name, description, parameters}}]   // 无 tool_choice
+ "temperature" / "top_p"（档案可配）
+ "reasoning_effort"（仅 tier != Off 时；本地档案是 Off ⇒ 不发）
```

**两个必须知道的缺口**（直接读码得出）：

| 字段 | Anthropic 协议路径 | OpenAI 协议路径（= 本地臂） | 后果 |
|---|---|---|---|
| `max_tokens` | **发**（`:277-282`，默认 8192；swe-v 覆盖 32000，`:384`） | **不发**（`openai_body` 里没有这一行） | ollama 用自己的默认 `num_predict` ⇒ 单轮输出无上限，可能一路吐到 ctx 满，撞 harness 600s 读超时后被重试 |
| thinking / reasoning | `thinking{budget_tokens}`（`:296-298`） | **不发**（`reasoning_effort` 仅 Off→Low/Medium/High 才发，`:204-206`） | 上 Qwen3.6-35B-A3B 这类默认 thinking 的模型**没有旋钮关**，token 必然膨胀 |

**工具声明形态**：
- SWE-V / TB：**只有一个 bash 工具**（`main.rs:772-775` / `:1147-1148`），参数 `command`（string）+ `timeout_ms`（integer），描述里写明工作目录、非交互、180s/600s 上限、失败后如何改策略（`tb.rs:300-312`）。
- InjecAgent：多工具（user tool + attacker tools），参数从 `tools.json` 转 schema（`main.rs:409-468`），工具实现是**打桩返回固定 JSON**（`main.rs:1304-1308`）。

**本地臂的协议级边界（直接证据）**：ollama 0.40.6 自带的 Unsloth chat template 会拒绝"结尾有 2 个以上 assistant 消息"的请求。日志实录：

```
srv    operator(): got exception: {"error":{"code":400,"message":"Cannot have 2 or more assistant messages at the end of the list.", …}}
time=2026-10-21T06:12:53.061+08:00 level=ERROR source=routes.go:3435 msg="chat template prompt error" …
[GIN] 2026/10/21 - 06:12:53 | 400 |   62.495912ms | 127.0.0.1 | POST "/v1/chat/completions"
```
（同样一次在 2026-10-20T16:45:24，全日志共 2 次。）harness 的 transcript 是 `System → User → (Assistant → Tool)*` 追加式（`af/crates/af-harness/src/run.rs:496-525`），**当一轮只出文本不出工具、下一轮又是 assistant 时就会形成连续 assistant** → 400。**这是本地臂独有的失败模式**（API 臂的模板宽容度不同）。

### 1.4 并发度

| 位置 | 值 | 出处 |
|---|---|---|
| ollama 服务端并行 slot | **2**（`OLLAMA_NUM_PARALLEL=2`） | `anolis:~/.config/ollama/env`（本轮 cat 实测） |
| ollama 实际装载 | `n_slots = 2`、`n_seq_max = 2` | 日志 `srv load_model: initializing, n_slots = 2` |
| 调度器对本地臂的 profile 限额 | `"qwen30b-local": 2` | `tools/factory-sched.py:53` |
| 调度器全局 bench 限额 | per-profile 4/4/4/3/2/4、全局 bench 24 | `计划/50-bench实测方案.md:323` |
| API 侧并发纪律 | GLM 账户实测并发上限 ~2–3，`glm-cp=1` + `glm-cp-max=1` | `计划/50-bench实测方案.md:330`（§9.6） |
| 本机（pandev-comp）另有 ollama | `qwen3:4b` / `qwen3:8b`，RTX 3070 Laptop 8GB，**已弃用**（太慢） | `main.rs:317-347` 注释 + `curl 127.0.0.1:11434/api/tags` 实测 |
| 隧道 | `ssh -L 11435:127.0.0.1:11434 anolis -N -f`（pid 1326503）+ 本机 11434→anolis 11434（pid 1326309） | `ss -tlnp` 实测 |

**并发 2 是硬上限**：再往上加，要么 ollama 排队（首请求被第二个请求拖住，触发 600s 读超时），要么再加 slot 把 KV 再翻一倍把显存吃穿。

### 1.5 超时预算

| 层 | 值 | 出处 |
|---|---|---|
| harness HTTP 读超时 | **600s**（`AF_HARNESS_HTTP_TIMEOUT_SEC` 可覆盖） | `af/crates/af-harness/src/http.rs:66-73` |
| HTTP 重试 | ≤5 次指数退避，尊重 Retry-After；耗尽才记 `run_failed`；行内带 `http_retries` | `main.rs:12-13`、结果行 `:920` |
| bash 工具单命令 | 缺省 180s / 上限 600s | `main.rs:168-179` |
| SWE-V eval | 1800s | `swev.rs:162` |
| 单题美元上限 | swe-v $3 / TB $1 / injec $1 | `main.rs:817,1190,1364` |
| 轮数上限 | swe-v 250（fix2）/ TB 40 / injec 16 | `main.rs:778,1150,1318` |

**对本地臂的含义**：600s 的 HTTP 读超时 ÷ 40 轮 = **单轮只有 15s 预算**；而实测长上下文下单轮固定开销（prompt 侧注意力）就有 **1.6–1.7s**（日志实例：`prompt eval time = 1665.26 ms / 1 tokens`），长上下文 + 长输出单轮很容易顶到几十秒。**并发 2 时两路共享同一张卡，单轮墙钟还要再乘 2。**

### 1.6 判分链

- **SWE-V**：官方 `eval_script` + 官方判分器，**clean 模式**（全新 eval 容器，`--judge-mode clean` 默认）；结果行带 `eval_sha256`（判分日志字节指纹）用于复核（`main.rs:881-891`）。
- **run 目录不覆写**：重跑按序号递增 `swev-<task>-<profile>-a<N>`（`main.rs:619-635`）。
- **反考古护栏 + 重复命令护栏**：命中 `git fsck` / `find / -name` 等模式会注入劝退文案；同一命令重复 ≥2 次会注入劝退（`main.rs:595-602`、`:752-763`）。
- **gate 记账**：`no_patch`（没产出 diff）/ `test_edit`（改了测试文件）落行但**不触发重试**（fix2 口径，榜单可比性）（`main.rs:836-843`）。
- **infra 失败不占分母**：`setup_failed` / `run_failed` 单独计数（`main.rs:683-698`、`:850-876`）。
- **本地臂相关的已知判分噪声**：D1 里有 8 题 infra（`reward=null`），其中 2 题 `run_failed`；同题重跑结论不一致（`django-11087` 一跑 `run_failed`、一跑 `completed`）→ **本地臂的解题率要带 infra 率一起读**。

### 1.7 磁盘与显存余量

**显存（本轮 `nvidia-smi` 实测，2026-10-21）**：

```
index, name, memory.total [MiB], memory.used [MiB], utilization.gpu [%]
0, Tesla V100S-PCIE-32GB, 32768 MiB, 0 MiB, 0 %
1, Tesla V100S-PCIE-32GB, 32768 MiB, 0 MiB, 0 %
```
（探测时模型未加载，ollama 进程在役但 idle。）

**S1 期间的实际占用（ollama 日志 load 块，本轮读到）**：

| 项 | GPU0 | GPU1 |
|---|---|---|
| 权重（CUDA model buffer） | 7,920.46 MiB | 4,140.97 MiB |
| KV cache（2 slot × 262,144 ctx） | 22,528.00 MiB | 26,624.00 MiB |
| compute buffer | 429.51 MiB | 340.01 MiB |
| **合计** | **≈ 30,878 MiB（94%）** | **≈ 31,105 MiB（95%）** |

**今天微基准那次的占用（对照）**：`n_ctx_seq = 8192`、KV 1,536 MiB（800+736）、权重 CUDA0 8,975.64 + CUDA1 8,548.79 MiB ⇒ 两卡各约 30%（8,975+800+164 ≈ 9,940 MiB）。

**由此得到三条硬账**：
1. **现役的 18.56 GB 权重是分在两张卡上的**（7,920+4,141 或 8,976+8,549，取决于那次装载的 split 决策）——**"第二张 V100S 全程闲置"的说法与 ollama 日志不符**（`调研/本地模型选型/notes/v100-speed-data.md` 的该条判断需要修正）。
2. **ctx=262144 × 2 slot 时显存 94–95% 满**，任何换模型都必须先降 ctx。
3. **KV 是 f16、96 KiB/token**（V100 无 BF16 ⇒ KV 没法缩一半）；要省 KV 只能降 ctx 或降并发。

**磁盘**：不是硬约束（运营者口径可扩容；`/data` 剩 18G、docker 可回收 135G）。但**注意 `/data` 本身已经 92% 满**（`状态/机器清单.md:12`），**新权重应落盘到有余量的分区或先回收镜像**，否则会触发技术债 D-15（判分容器 ENOSPC，`计划/技术债登记.md:22`）。

### 1.8 档案接入方式（新增一个 Profile 的最小改动位置）

**最小改动 = 3 处**：

| # | 文件:行 | 改什么 |
|---|---|---|
| 1 | `af/crates/af-bench/src/main.rs:188-351`（`fn profile(name)`） | 加一个 match 臂，填 `EndpointSpec{protocol: OpenaiChatCompletions, base_url, model, key_ref:"ollama-local", reasoning_tier: Off, stream:false}` + `key_cmd`（本地档案统一用 `printf '%s' ollama-local-noop-key`，`:300`） |
| 2 | `tools/factory-sched.py:53`（`PROFILE_LIMITS`）+ `:75-87`（`OUT_DIRS` 映射） | 注册 profile 并发上限 + 结果目录；`profiles` 列表在 `:219` |
| 3 | `计划/变更日志.md` + `状态/组件建设状态.md` | 登记（工作区硬纪律：改了现实不更新文档 = 严重违规） |

**已知会踩的坑**：
- **profile 名不一致已经欠了技术债**：`fix1` 结果目录里 `30b` / `qwen30b-local` / `step5` / `step-5` / `d1-glm-max` / `d1-glm-cp-max` 混用，多处映射表硬编码（`计划/技术债登记.md:21` D-14）。**新档案一律用 `main.rs` 里的档案名**（如 `qwen3-coder-next-local`），目录用同名。
- **D-22**：容器名 `afbench-swev-<task>-<profile>` 不含 out 目录 → 同题跨线双跑会互踩（A/B 抽样被迫硬排除 13 题）（`技术债登记.md:29`）。本地臂一定要单独 out 目录。
- **本机臂与 anolis 臂物理隔离**：`factory-sched.py:166-171` 的 `local_out()` / `done_union()` 逻辑，本地臂的 out 目录要和 API 臂分开。
- **swe-v 判分链有硬编码路径**（`/tmp/swev-s1`、`swev-venv`，D-13，`技术债登记.md:20`）→ 本地臂判分要复用同一套路径。

---

## 2. 本地臂在工厂里承担什么角色（与 API 主力臂的分工）

### 2.1 实测解题率对照（fix1 同代、同判分链、同题集分布）

| 档 | **30b（本地）** | glm-cp（GLM-5.3-Flash） | glm-max（GLM-5.3） | m31f | step5 | kimi | m3 |
|---|---|---|---|---|---|---|---|
| D1 | **37.0%**（20/54） | 62.7%（32/51） | **76.8%**（43/56） | 69.2%（27/39） | 62.8%（27/43） | 71.4%（35/49） | 63.6%（35/55） |
| D2 | **19.4%**（7/36） | 48.3%（14/29） | 45.7%（16/35） | 50.0%（11/22） | 56.5%（13/23） | 50.0%（19/38） | 40.5%（15/37） |
| D3 | **15.0%**（3/20） | 22.2%（4/18） | 46.7%（7/15） | 35.0%（7/20） | 28.6%（2/7） | 47.4%（9/19） | 31.6%（6/19） |

（数据源：`/tmp/bench-fix1-d{1,2,3}-<arm>/results.jsonl`；分母为 `reward != null` 的题数。）

> **同代可比性**：这张表里所有臂都来自同一代结果目录族（`bench-fix1-*`，行内 `scaffold=v2`、无 `judge_mode` 字段 ⇒ 均为 POC-1 判分口径切换前），**臂与臂之间可比**；但**不能与 fix2/fix3 的结果混算**（`计划/50-bench实测方案.md:312` 版本隔离纪律）。另注：各臂的**分母不同**（D1：30b 54 / glm-cp 51 / glm-max 56 / m31f 39 / step5 43 / kimi 49 / m3 55），因为 infra 题被剔出分母 ⇒ **跨臂比"通过数"会误导，必须比通过率**。

**读出来的三件事**：
1. **本地 30B 在 D1 就掉到 37%**，D2 只有 19.4%——**"弱模型档"这个定位必须落到题档上：只配 D1，不配 D2/D3**。
2. **本地臂的墙钟不是短板**（D1 中位 302s vs glm-cp 770s），短板是**解题率**。
3. **同一个模型换 API 档位，收益巨大**（D1：37% → 62.7% 只是换成 Flash）。所以本地臂的价值**不在解题率上限**，在**零成本 + 不熔断 + 可无限并发（只受我们自己的 GPU 决定）**。

### 2.2 角色裁定

| 角色 | 定位 | 依据 |
|---|---|---|
| **✅ 零成本并联量产/预筛臂** | 拿 D1/D2 题目做**第一遍草稿**、批量改写、模板化修补；解出来的进判分，解不出来的**不消耗任何 API 额度** | 30B 臂已跑完 122 题 14.5 GPU 小时；D1 37% 的"白捡"通过率 |
| **✅ 兜底臂（永不熔断）** | API 账户周池/并发被打爆时（§9.6 已实证 429 风暴 40/42 run_failed），本地臂是唯一能继续产出的路径 | 本机/anolis 链路无外部配额 |
| **✅ cascade 的 stage-1 弱模型臂** | 50-方案 §2.3 的 E1（测试驱动升级）/ E2（停滞指纹升级）正好需要"一个便宜到可以随便重试"的弱模型；本地 30B 的 27.3% 基线正好是升级信号的起点 | `计划/50-bench实测方案.md:105-109` |
| **❌ 不是主链路的量产臂** | D2/D3 解题率 19.4%/15.0%，远低于 API 主力下限（GLM-5.3-Flash D1 62.7%） | 同上表 |
| **❌ 不是效果档** | 官方/第三方对标：GLM-5.3-Flash SWE-V 92% @ $0.02/task、DeepSeek V4 Flash 88.8% @ $0.01/task（`设计/benchmark调研/实测/model-pricing.md:194-195`） | 同上 |
| **⚠️ 它的第二身份：反例样本机** | 本地臂解错的题是**"弱模型系统性失败"的高质量负样本**，是 S2 cascade 与 JIT 配方优化的天然素材 | 122 题的失败轨迹已在 MES 里 |

**与 API 主力臂的分工一句话**：**API 臂负责"解题率"，本地臂负责"零成本地把题目跑一遍"**。两者不是替代关系，是**级联关系**（弱模型先跑 → 确定性信号（测试不过/重复错误/停滞）触发升级 → 强模型续跑），这与文献先验"省 75–85% 成本保 95–97% 质量"一致（`model-pricing.md:270-272`）。

### 2.3 前期结论的独立核对

| 前期结论 | 本轮裁定 | 依据 |
|---|---|---|
| 本地池定位"弱模型档"，主力走 API | **成立** | §2.1 实测表 |
| 本地最强可行 = Qwen3-Coder-Next 80B-A3B Q4 双卡容纳 | **成立但要加两条限定**：①官方 Q4_K_M 是 **48.19 GiB**（ollama registry manifest 实测 51,741,599,936 B），不是 45GB；②**自报 Terminal-Bench 只有 34.2/36.2**（【转引】`notes/qwen-family.md` §2.1），对我们含 TB 的 workload **不构成全面升级** | 本轮 registry 核实 + 笔记 |
| 保底选项 = Qwen3-Coder-30B-A3B Q4_K_M 单卡 | **成立**，且**实际是双卡分摊**（日志 CUDA0 7,920 + CUDA1 4,141 MiB） | ollama 日志 |
| GPT-OSS-120B MXFP4 不建议（V100 不支持） | **未复核**（本轮只核了 runner 里的 `gpt-oss` 符号存在，不核 MXFP4 kernel） | `strings libllama.so.0` |
| llama.cpp 老卡输出乱码/GPU 未生效 issue（#17067） | **仍需保留冒烟**；本轮**新增一条本地实证失败模式**：ollama 0.40.6 模板 400（§1.3） | ollama 日志 |
| "50-方案的输入 300K+输出 30K 画像高估 1–2 个数量级" | **对 API 臂成立、对本地臂要改写**：本地臂实测**每题 prompt 总量中位 394,639 token**（= 44 万，**不是低 1–2 个数量级**），因为 ollama 每轮把**整个历史重发**；差别来自"每轮增量很小（96.9% 缓存命中）" | 30B 臂实测 + 50-方案 §6.1 |
| "真正的成本瓶颈是模型不努力（浅尝辄止/零补丁）" | **本轮支持**：本地臂 D1 有 8 题 infra、`no_patch` 与 `max_turns` 打满是主要失败形态 | 30B 臂结果行 |
| "每题约 10 轮工具调用"（任务书口径） | **推翻**：实测中位 40 轮（D1）/ 50 轮（D2），p90=60 | 30B 臂 122 题实测 |

---

## 3. 候选清单（面向"本地臂到底需要什么"的选型）

> 判定口径全部落到本机 2×V100S-32GB + ollama 0.40.6 + af-bench 的真实负载上，不是通用榜单。
> "官方 agentic 分数"栏一律标注自报/第三方；"第三方反馈"栏只有确实有出处的才写。

| 模型 | 厂商 | 结构（总参/激活） | Q4 体积 | ctx | GGUF/ollama 可得性 | 官方 agentic 分数 | 第三方反馈 | 我们的适配判断 |
|---|---|---|---|---|---|---|---|---|
| **Qwen3-Coder-30B-A3B-Instruct**（现役） | Alibaba | MoE 30.5B / 3.3B（128 专家取 8，48 层，GQA 32/4） | **18.56 GB**（实测 blob 18,556,689,568 B） | 262,144 | 本机在役；Unsloth Q4_K_M | SWE-V 61.4（转引）；【转引】AA II 10 | 我们自己实测：D1 37.0% / D2 19.4% / D3 15.0% | **保底档，保留**。显存省（KV 96 KiB/tok × ctx 是唯一大头）、速度最快（135.7 tok/s @8K）、但解题率低 |
| **Qwen3-Coder-Next（80B-A3B）** | Alibaba | MoE 80B / 3B（512 专家取 10，48 层 = 12×(3×GDN+1×GatedAttn)，**仅 non-thinking**） | **48.19 GiB**（ollama registry manifest 实测 51,741,599,936 B；官方 GGUF 分片 48.41 GB【转引】） | 262,144 | ✅ `qwen3-coder-next:q4_K_M` 在 registry；runner **含 QWEN3NEXT 符号**（本轮 `strings` 实测） | SWE-V **70.6**（SWE-Agent）/ 71.1（MiniSWE）/ 71.3（OpenHands）；**TB2.0 仅 34.2/36.2**；SWE-Pro 44.3；工具模板泛化 92.7【转引】 | 未找到公开的 V100 上第三方复现（【转引】笔记明写"未找到 V100 实测"） | **能力上限探针，不是换装首选**。①TB 是倒退（我们 workload 含 TB）②48 GiB 权重 + KV 会把显存顶到 95%+，**ctx 必须降到 2×16K 或 2×32K** ③每 token 字节与现役相当 ⇒ **不会更快，只会更强** |
| **Qwen3.6-35B-A3B** | Alibaba | MoE 35B / 3B（256 专家取 8 + 1 shared，40 层，30 层 linear-attn + 10 层 full-attn） | **20.23 GiB**（registry manifest 实测 21,718,480,960 B）+ projector 0.84 GiB；ollama 标称 22.62 GB | 262,144（官方建议 ≥128K） | ✅ `qwen3.6:35b`；源 tag 含 **MTP**（`35b-a3b-mtp-q4_K_M`）；runner 含 QWEN35MOE | SWE-V **73.4** / TB2.0 **51.5** / SWE-Pro 49.5【转引】 | V100-SXM2 上第三方实测 **98.8 tok/s**（thinking ON, ctx 16K）【转引】 | **最值得实测的一档**：**单卡装得下**（余 ~10 GiB 给 KV）、SWE 与 TB **双超**现役。**两个必须先解决的前提**：①默认 thinking 且 harness 的 OpenAI 路径**没有关它的旋钮**；②同族 sm_70 崩溃 issue（#29783）未修，**必须冒烟** |
| **Qwen3.8-27B / Qwen3.6-27B / Qwen3.5-27B** | Alibaba | **稠密** 27.78B（64 层，48 层 linear-attn + 16 层 full-attn） | 16.55 GiB【转引】 | 262,144 | ✅ runner 含 QWEN35 | Qwen3.6-27B: SWE-V 77.2 / TB2 59.3；Qwen3.8-27B: **TB2.1 73.0** + SWE-Pro 61.7【转引】 | V100 实测 **32.9–33.41 tok/s**【转引】 | **不做**。每 token 要读 16.9 GB（稠密）vs 2.3 GB（MoE），**慢 4.1×**；再叠 thinking 膨胀 ⇒ 单题墙钟是现役 4–8×，与"量产臂"定位直接冲突 |
| **GPT-OSS-120B (MXFP4)** | OpenAI | MoE 120B / 5.1B | 原生 63 GB【转引】 | 131,072 | runner 含 `gpt-oss` 符号（本轮 `strings` 实测） | SWE-V 33.6（Vals）【转引】 | — | **维持不推荐**：V100 无 MXFP4 加速（【转引】前序结论，本轮未复核 kernel）；且体积贴边，无 ctx 余量 |
| **Qwen3-Coder-480B-A35B** | Alibaba | MoE 480B / 35B | 290 GB（ollama）【转引】 | 262,144 | ✅ 但装不下 | — | — | **排除**（体积） |
| **Qwen3.8-Flash-Next (125B + 51B n-gram)** | Alibaba | — | 98 GB+，且 ollama **仅 MLX 构建**（macOS）【转引】 | — | ❌ | — | — | **排除** |
| **GLM-4.7-Flash 30B-A3B** | Zhipu | MoE 30B / 3B【转引】 | 未找到公开 GGUF 尺寸（**未验证**） | 未验证 | 未找到 ollama/GGUF 官方条目（**未验证**） | 未找到可核的 SWE-V/TB 官方数（**未验证**） | 未找到 V100 实测 | **列此是因为同价位同结构**；但**公开证据不足，本轮不进入实测队列** |

---

## 4. 重点候选展开

### 4.1 Qwen3-Coder-Next（80B-A3B）——"更强，但不会更快，且 TB 倒退"

**能力（官方自报，【转引】`notes/qwen-family.md` §2.1，出处为官方技术报告 `qwen3_coder_next_tech_report.pdf`，2026-02-03）**：SWE-V 70.6（SWE-Agent）/ 71.1（MiniSWE）/ 71.3（OpenHands）；SWE-Multilingual 62.8；SWE-Pro 44.3；**TB2.0 36.2（Terminus2-json）/ 34.2（Terminus2-xml）**；Aider Polyglot 66.2；工具模板泛化 92.7。

**体积（本轮独立核实）**：
```
curl -s https://registry.ollama.ai/v2/library/qwen3-coder-next/manifests/q4_K_M
→ "layers":[{"mediaType":"application/vnd.ollama.image.model","size":51741599936}, …]
```
= **51.74 GB = 48.19 GiB**（**前期文档写的 45GB 低估 7%**）。

**runner 兼容性（本轮独立核实）**：`strings /data/models/lib/ollama/libllama.so.0`（= libllama.so.0.7.0）里出现 `QWEN3NEXT`、`QWEN35MOE`、`QWEN35`、`QWEN3MOE`、`gpt-oss`、`glm4`、`deepseek2` ⇒ **四个候选架构全在我们这版 ollama 的 runner 里**。（第一次我用 `qwen3_next` 这种带下划线的模式去 grep，匹配不到，是我的模式写错，纠正后确认存在。）

**速度（推断，基于带宽账 + 我们自己的实测口径）**：
- 我们的实测口径修正：现役在 **ctx=8192** 下 135.7 tok/s（微基准），在 **真实上下文深度 6–16K** 区间实测 **38–40 tok/s**（本轮解析 ollama 日志 55 个 `print_timing` 样本：ctx<1K → 116.2、<2K → 120.2、<4K → 109.2、<8K → 39.2、<16K → 38.0 tok/s）。
- **所以"135.7 tok/s"不能当产量口径**：本地臂的真实平均有效吐字速率是 **16.4 tok/s**（= 30B 臂 122 题：输出 token ÷ 墙钟，中位）。
- Coder-Next 每 token 需读 ≈ (10/512)×77.3B 专家 + 其余 ≈ 3.5B 参数 × 0.608 B/param ≈ **2.13 GB/token**（【转引】笔记 §3.2），与现役的 **2.3 GB/token** 几乎相同 ⇒ **decode 速度量级相同，不会更快**。

**显存账（本轮用实测 KV 口径复算）**：
- Coder-Next 只有 12 层全注意力（Gated Attention 2 KV 头 × 256 head_dim），KV ≈ 24 KiB/token（比现役的 96 KiB/token 便宜 4 倍——【转引】架构参数 + 本轮同法复算）。
- 48.19 GiB 权重双卡分摊 ≈ 24.1 GiB/卡；每卡 31.73 GiB 可用 ⇒ 余 ~6.4 GiB/卡。
- **但**：若沿用现役的 2 slot × 262,144，KV = 2×262,144×24 KiB = 12 GiB（6 GiB/卡）⇒ 每卡 24.1+6+compute ≈ **30.5 GiB / 31.7 GiB ⇒ 96% 满**。**必须降 ctx**。

**结论**：**换它不会更快（每 token 字节相同），解题率上限更高（SWE 维度 +9~19 分，自报），但 TB 维度倒退 ~17 分（34.2 vs 3.6-35B-A3B 的 51.5）**。我们的 workload 是 SWE-V + TB 混合 ⇒ **它不是"更值得上"的换装首选**。

### 4.2 Qwen3.6-35B-A3B —— **当前最该打榜的一档**（本轮裁定上调）

**为什么上调**：它是清单里**唯一"SWE 与 TB 双超现役 + 单卡装得下 + 每 token 字节与现役同档（≈1.8 GB/token）"**的候选【转引】笔记 §2.2/§3.2。

**三个必须先解决的前提**（否则装上去也白装）：
1. **thinking 旋钮缺失**：`main.rs` 的 OpenAI 协议路径不发 `reasoning_effort`，也不发 ollama 的 `think` 字段 ⇒ 默认 thinking 开着 ⇒ token 膨胀（我们自己的 D1 实测里 m31f 就是这么炸的：输出 token 中位 44,397，比 30B 的 5,756 高 7.7×）。
2. **同族 sm_70 崩溃 issue #29783 未修**（【转引】笔记 §5.1）⇒ **必须冒烟**。
3. **MTP 投机解码**：`qwen3.6:35b` 的 ollama 源 tag 是 `35b-a3b-mtp-q4_K_M`（本轮 registry manifest 实测）⇒ 我们的 ollama 0.40.6 在 S1 装载时明确打印 `"spec common_specu: no implementations specified for speculative decoding"`（日志）⇒ **本机没有开投机解码的路径**，MTP 不会自动生效；但也意味着**别指望它提速**，而且 `--split-mode tensor` 下的 MTP 崩溃 issue（任务书已知）对我们是**不触发**的（我们用默认 layer split）。

**装法与档位**：单卡装 20.23 GiB 权重 ⇒ **每卡余 ~10 GiB 给 KV** ⇒ 2 slot × 32K（KV 2×32K×96 KiB = 6 GiB… 注意它的 KV 口径待实测，因为 30 层是 linear-attention，KV 口径与现役不同）⇒ **建议先按 2 slot × 16K 冒烟，再按实测 KV 占用放宽**。

### 4.3 现役 30B-A3B —— **不是"该换掉的"，是"该调参的"**

实测显示它的**瓶颈是配置，不是模型**：
- **ctx 档位**：S1 期间跑的是 2×262,144（KV 48 GiB，显存 94–95% 满）——**但真实调用的上下文深度 p99 只有 28.8K** ⇒ **262K 是纯浪费**。改成 **2×32K**：KV 从 48 GiB 降到 6 GiB ⇒ **省出 42 GiB 显存**（每卡 21 GiB）⇒ 足够同时装一个 48 GiB 的第二模型做 A/B。
- **有效吐字速率只有 16.4 tok/s**：分解为「decode ~40 tok/s（长上下文）」+ 「每轮 1.6–1.7s 固定注意力开销」+ 「并发 2 时争卡」。**ctx 降低会直接抬高 decode 速率**（ctx<4K 时 109–120 tok/s，ctx 6–16K 时 38–40）⇒ **把 ctx 收到 32K 以内，深度落在 4–16K 区间，速率有望从 16.4 拉到 30+**（推断，需实测）。
- **`max_tokens` 没传**（§1.3）⇒ 单轮可能无上限吐字，这是 600s 读超时 + 重试的来源之一。
- **模板 400**（§1.3）⇒ 连续 assistant 消息会直接失败。

### 4.4 稠密 27B 家族 —— 假设的后半段成立，但结论是"不做"

- 假设验证：**"稠密 27B 在 V100 上解码慢 3–4 倍"成立**（【转引】笔记 §3.2：V100 实测 32.9–33.41 tok/s vs 30B-A3B 135.7 tok/s = 4.1×；带宽复算 16.9 GB vs 2.3 GB 每 token = 7.3× 字节差）。
- **前半段也成立**："MoE 比同代稠密快"在 V100 上是硬事实。
- **但"80B-A3B 会比 30B-A3B 更快"不成立**——两者激活参数相同（3B），每 token 字节相同（2.13 vs 2.3 GB）⇒ **不更快，只更强**。
- 对我们：**稠密 27B 的墙钟是现役的 4–8×，直接出局**。

### 4.5 `--n-cpu-moe`（任务书要求核查的反面项）

- 机制存在（llama.cpp `common/arg.cpp`，【转引】笔记 §3.3 抓取到原文）：`-ncmoe/--n-cpu-moe N` + `--moe-cache-mib N`。
- **代价（本轮采纳笔记复算并与我们的 PCIe 实测口径对齐）**：Coder-Next 每 token 需从主机内存搬 ≈ 0.92 GB；PCIe Gen3 x16 实测 ≈ 12–14 GB/s ⇒ **纯搬运 58–77 ms/token ⇒ 天花板 13–17 tok/s**。
- **裁定**：在 V100 上 `--n-cpu-moe` **不是"塞进单卡"的经济解**，只是极端兜底；用它把 Coder-Next 压进单张 32GB ⇒ 相对现役 135.7 tok/s（微基准）/ 40 tok/s（真实深度）分别是 **8× / 2.4× 倒退**。**双卡分摊才是正解**（24.1 GiB/卡，余 6.4 GiB）。

---

## 5. 直接证据 vs 推断（分栏）

### 5.1 直接证据（本轮亲自跑过 / 读到，可复现）

| # | 事实 | 怎么拿到的 |
|---|---|---|
| E1 | 本地 30B 臂 SWE-V 122 题：D1 37.0%（20/54）/ D2 19.4%（7/36）/ D3 15.0%（3/20），合计 27.3%（30/110），infra 12 题 | `python3` 解析 `/tmp/bench-fix1-d{1,2,3}-30b/results.jsonl` |
| E2 | 每题轮数中位 40.5/50/31.5、p90=60；输出 token 中位 5,756/6,009/4,757；墙钟中位 302/395/140 s，p90 986/1,031/1,126 s | 同上 |
| E3 | 有效吐字速率中位 **16.4 tok/s**（30B 全档） | 同上（输出 token ÷ `agent_wall_ms`） |
| E4 | API 臂同代对照：D1 glm-cp 62.7% / glm-max 76.8% / m31f 69.2% / step5 62.8% / kimi 71.4% / m3 63.6% | `python3` 解析 `/tmp/bench-fix1-d1-*/results.jsonl` |
| E5 | ollama 日志 7,974 次调用的上下文深度：中位 10,289 / p90 20,830 / p99 28,776 / max 63,157 token | `python3` 逐行解析 `/data/models/ollama-serve.log`（脚本见本文附录） |
| E6 | KV 96.0 KiB/token（实测 2,235.368 MiB ÷ 23,841 token；与 48 层×4 KV 头×128×f16 复算一致） | 同上日志行 |
| E7 | S1 期间装载：n_slots=2、n_ctx_slot=262144、n_ctx=524288、KV 49,152 MiB（CUDA0 22,528 / CUDA1 26,624）、权重 CUDA0 7,920 / CUDA1 4,140、compute 429/340 MiB ⇒ **两卡 94–95% 满** | `sed -n '123655,123712p' ollama-serve.log` |
| E8 | **模型是分在两张卡上的**（今天微基准那次是 CUDA0 8,975.64 + CUDA1 8,548.79 MiB）⇒ 「第二张 V100S 全程闲置」不成立 | 同上 |
| E9 | 微基准那次是 **n_ctx_seq=8192、KV 1,536 MiB**；`n_ctx_seq (8192) < n_ctx_train (262144)` 告警 | 同上 |
| E10 | decode 速率随上下文深度衰减：<1K 116.2 / <2K 120.2 / <4K 109.2 / <8K 39.2 / <16K 38.0 tok/s（55 个样本） | 日志 `print_timing` 解析 |
| E11 | ollama 0.40.6 模板 400：`Cannot have 2 or more assistant messages at the end of the list.`，日志 2 次（10-20T16:45:24、10-21T06:12:53） | `grep` 日志 + GIN 行 |
| E12 | S1 装载里 `"resolve_fused_ops: Flash Attention enabled"`、`"no implementations specified for speculative decoding"`、`n_threads = 8`、`n_batch = n_ubatch = 512`、prompt cache 8,192 MiB | 日志 |
| E13 | 现役模型元数据：qwen3moe / 48 层 / 128 专家取 8 / 32 头 4 KV 头 / head_dim 128 / ctx 262,144 / capabilities `[tools, completion]` / Unsloth Q4_K_M / 18,556,689,568 B | `curl /api/show` + `du` |
| E14 | 两卡 32,768 MiB 各自独立，探测时 0 MiB 占用；ollama 0.40.6；`OLLAMA_NUM_PARALLEL=2` | `nvidia-smi` / `curl /api/version` / `cat ~/.config/ollama/env` |
| E15 | ollama registry：`qwen3-coder-next:q4_K_M` model layer **51,741,599,936 B**；`qwen3.6:35b` model layer 21,718,480,960 B + projector 902,821,728 B，源 tag `qwen3.6-source:35b-a3b-mtp-q4_K_M` | `curl registry.ollama.ai`（本机直连成功） |
| E16 | runner 含 `QWEN3NEXT/QWEN35MOE/QWEN35/QWEN3MOE/gpt-oss/glm4/deepseek2` | `strings /data/models/lib/ollama/libllama.so.0` |
| E17 | harness OpenAI 协议路径**不发** `max_tokens`、**不发** `reasoning_effort`（Off）、**不发** `tool_choice` | `af/crates/af-harness/src/endpoint.rs:186-213, 204-206` |
| E18 | harness HTTP 读超时 600s（`AF_HARNESS_HTTP_TIMEOUT_SEC` 可覆盖）、重试 ≤5 次 | `af/crates/af-harness/src/http.rs:66-73`；`main.rs:12-13` |
| E19 | 套件轮数上限：swe-v 250（fix2）/ TB 40 / injec 16；bash 工具 180s/600s；eval 1800s | `main.rs:778,1150,1318,168-179`；`swev.rs:162` |
| E20 | 隧道：11435→anolis:11434（pid 1326503）、11434→anolis:11434（pid 1326309）；本机 ollama 有 `qwen3:4b`/`qwen3:8b` | `ss -tlnp`、`curl /api/tags` |
| E21 | 调度器 profile 限额 `"qwen30b-local": 2`，out 目录映射在 `factory-sched.py:53,75-87` | 读码 |
| E22 | D1 30B 臂失败形态：`completed 50 / max_turns 10 / run_failed 2`；gate `ok 44 / no_patch 11 / test_edit 5`；`http_retries>0` 的行数 **0** | `collections.Counter` 解析同一份 results.jsonl |
| E23 | 30B 臂结果行 `scaffold=v2`、**无 `judge_mode` 字段**（62 行全 None）⇒ 属 POC-1 判分口径切换前的一代 | 同上 |

### 5.2 推断（本报告的判断，非实测）

| # | 推断 | 依据与不确定度 |
|---|---|---|
| I1 | 「把 ctx 从 262K 降到 32K，能把有效吐字速率从 16.4 拉到 30+ tok/s」 | 依据 E10 的深度→速率曲线 + E5 的深度分布（p99 28.8K ⇒ 32K 够用）。**未实测**；风险：降 ctx 会截断长任务上下文，可能掉解题率 |
| I2 | 「本地臂 122 题一整轮 SWE-V 需 ≈14.5 GPU 小时」 | 依据 E2 的墙钟总和（D1 6.91h + D2 5.85h + D3 1.73h）。**未含 TB 与镜像拉取** |
| I3 | 「Coder-Next 装上后显存 96% 满，必须 ctx ≤ 2×16K 或 2×32K」 | 依据【转引】架构参数 + E6 的 KV 口径复算。**Coder-Next 的 KV 口径未实测**（12 层全注意力 + GDN 递归态） |
| I4 | 「模板 400 是本地臂独有的失败模式，API 臂不受影响」 | 依据 E11（ollama 侧报错）+【转引】API 臂同代跑完 122 题无此类 run_failed。**未做对照实验** |
| I5 | 「本地臂的定位应是 cascade stage-1 + 并联预筛 + 兜底」 | 依据 §2.1 实测表 + `计划/50-bench实测方案.md:105-109` 的 cascade 设计。**未做 cascade 实验** |
| I6 | 「Qwen3.6-35B-A3B 是最该打榜的一档」 | 依据 E15（单卡装得下）+【转引】分数（SWE 73.4 / TB 51.5）+【转引】V100 实测 98.8 tok/s。**本轮未在 V100 上跑过它** |

### 5.3 本轮"未找到公开证据 / 未验证"清单

| 项目 | 状态 |
|---|---|
| Qwen3-Coder-Next 在 **V100 上的第三方吞吐实测** | **未找到公开证据**（【转引】笔记同样明写"未找到 V100 实测"） |
| Coder-Next 的 **KV cache 实测口径**（每 token 字节） | **未实测**（只按架构参数复算） |
| GLM-4.7-Flash 30B-A3B 的 **GGUF/ollama 可得性与官方 agentic 分数** | **未找到公开证据** |
| **GPT-OSS-120B MXFP4 在 sm_70 上是否有可用 kernel** | **本轮未复核**（只确认 runner 里有 `gpt-oss` 符号） |
| `qwen3-coder-next` 官方 GGUF 分片合计 48.41 GB | 【转引】笔记（官方仓库分片和）；本轮只独立核实了 ollama manifest 的 51,741,599,936 B |
| ollama `/v1/chat/completions` 是否接受 `think` / `options` 扩展字段 | **未验证**（影响"怎么关 thinking"这一步怎么做） |
| 稠密 27B 家族在 **V100-PCIE（我们同款卡型）** 上的实测速率 | 【转引】笔记给了 Qwen3.8-27B 33.41 tok/s（V100-PCIE-32GB） |
| 30B 臂 D1 那 8 题 infra 的逐题根因（是否与模板 400 相关） | **未逐条对账** |

---

## 6. 对我们的具体建议（落到 anolis-gpu-01 的 2×V100S）

> 目标不是"换一个更强的模型"，而是**先把现役的配置榨干、把 harness 的两个缺口补上，再决定要不要下 48 GiB 的第二个模型**。

### 6.1 P0（零下载、零换模型，本周就能做）

| # | 动作 | 具体改法 | 依据 |
|---|---|---|---|
| P0-1 | **把 ollama 的 ctx 档位从 262K 降到 32K**（2 slot × 32K） | ollama 侧：新建 Modelfile 显式写 `PARAMETER num_ctx 32768`（现役 Modelfile 只有 `FROM` + `TEMPLATE`，**没有任何 PARAMETER**——实测 `curl /api/show`），`ollama create` 后重载；或用 `OLLAMA_CONTEXT_LENGTH=32768` 启动环境变量 | E7/E9（262K→KV 48 GiB→两卡 94–95% 满）+ E5（p99 深度 28.8K，32K 够用）+ I1（速率可望 16.4→30+） |
| P0-2 | **给 OpenAI 协议路径补 `max_tokens`** | `af/crates/af-harness/src/endpoint.rs` 的 `openai_body()` 增加 `body["max_tokens"] = endpoint.max_tokens`（档案级开关，**不改变 Anthropic 臂的测量口径**，注意 bump 结果代号） | E17（本地臂单轮输出无上限 → 撞 600s 超时被重试） |
| P0-3 | **给本地档案补 thinking 开关** | 两条路：①（推荐）在 `EndpointSpec` 上加一个 ollama 专用字段，`openai_body()` 里发 `think: false` / `reasoning_effort`；②先查 ollama `/v1/chat/completions` 是否吃 `options`/`think` 扩展字段（**未验证**） | E17 + I6（不然 Qwen3.6-35B-A3B 的 thinking 必然膨胀） |
| P0-4 | **把模板 400 变成可见失败** | 在 harness 里对 400 做分类：本地臂的 `400 Cannot have 2 or more assistant messages...` 应记为**可归因失败**（`verifier_note` 写明），而不是混进 `run_failed` infra | E11 + I4 |
| P0-5 | **给本地臂加"长上下文降速"告警** | 观测中心把 `context depth` 落进 MES（现在只有 token 三账本，没有深度）；把 `>16K` 标黄 | E5 + E10 |

### 6.2 P1（下一轮打榜，不换装）

**先做 A/B，不做换装**：
1. 用 P0-1 的 32K 档**重跑现役 30B**（同一批 D1 题，fix 代号 bump）→ 拿到"调参后基线"。**这一步是所有换装结论的分母。**
2. 同时下 **Qwen3.6-35B-A3B**（ollama 标称 22.62 GB，本轮 registry 实测 20.23 GiB 权重 + 0.84 GiB projector）——**单卡装得下，两张卡可以各跑一个实例**（比 layer-split 少一道跨卡 PHB 惩罚）。
3. 冒烟清单（缺一不进 af-bench）：
   - a. 架构/符号：本轮已证 runner 含 `QWEN35MOE`（E16）
   - b. **sm_70 崩溃 issue #29783 回归**（【转引】笔记 §5.1）：同款 prompt 连发 20 次不出错
   - c. **thinking 关闭后 token 计数**：一轮输出应回到 ~150–400 token 量级（现役 30B 的 152.7 token/轮）
   - d. **工具调用形态**：能稳定吐 `{"name":"bash","arguments":{"command":…}}`
   - e. **连续 assistant 消息**：构造 harness 的 tool-free 轮，确认不再 400（P0-4 修完后）
   - f. **KV 实际占用**：`llama_kv_cache` 日志行读出每 token 字节，再定 ctx 档位
4. 判定口径：**同一批 D1（23–62 题）+ TB 短任务**，比 **解题率** 和 **单题墙钟中位** 两个数；解题率低于调参后基线 ⇒ 直接淘汰，不进第二轮。

### 6.3 P2（只有 P1 出正面结论才做）

- **Qwen3-Coder-Next 48.19 GiB**：**必须先把现役 30B 的 ctx 降到 32K（腾出 42 GiB）**，并且**它只跑 SWE-V、不跑 TB**（TB 自报倒退 17 分）⇒ 它是"**SWE 专项加强臂**"，不是全量替代。落盘注意 `/data` 已 92% 满（D-15 风险），建议先回收 docker 镜像。
- **不要碰**：稠密 27B 家族（墙钟 4–8×）、GPT-OSS-120B MXFP4、Qwen3.8-Flash-Next、任何 480B+ 模型。

### 6.4 装法模板（若采纳 Qwen3.6-35B-A3B，落到 anolis）

```bash
# 0) 只读体检（不要动在役服务）
ssh anolis 'nvidia-smi --query-gpu=index,memory.total,memory.used --format=csv; \
            curl -s http://127.0.0.1:11434/api/version; \
            grep -c . ~/.config/ollama/env'

# 1) 磁盘：/data 已 92% 满 → 先回收 docker 镜像（D-15/D-6 授权路径）
ssh anolis 'docker system df; df -h /data'

# 2) 拉模型（单卡装得下；不设 --gpu-layers 特殊值）
ssh anolis 'ollama pull qwen3.6:35b'          # registry 实测 20.23 GiB 权重 + 0.84 GiB projector

# 3) 显式 ctx 档（关键：现役 Modelfile 没有任何 PARAMETER，靠默认 262144 会吃穿显存）
ssh anolis 'cat > /data/models/Modelfile-35b <<EOF
FROM qwen3.6:35b
PARAMETER num_ctx 32768
PARAMETER temperature 0.0
PARAMETER top_p 1.0
EOF
ollama create qwen3.6-35b-local -f /data/models/Modelfile-35b'

# 4) 起第二实例（避开在役 11434，用 11436；ollama 0.40.6 单进程多模型靠模型名路由，
#    因此只要模型名不同即可，并发上限仍受 OLLAMA_NUM_PARALLEL=2 约束）
ssh anolis 'OLLAMA_NUM_PARALLEL=2 OLLAMA_CONTEXT_LENGTH=32768 ~/.local/bin/ollama serve'

# 5) 冒烟（清单见 §6.2 第 3 步 a–f），全过才接 af-bench
ssh anolis 'curl -s http://127.0.0.1:11434/v1/chat/completions -d "{\"model\":\"qwen3.6-35b-local\", ...}"'
```

**档案接入（3 处最小改动）**：
1. `af/crates/af-bench/src/main.rs` 的 `fn profile(name)` 加一个臂（照抄 `qwen30b-local` 的形状，`:283-301`，只改 `base_url`/`model`）；
2. `tools/factory-sched.py:53` 的 `PROFILE_LIMITS` + `:75-87` 的 `OUT_DIRS`；
3. `计划/变更日志.md` + `状态/组件建设状态.md` 登记。

**隧道**：现有 `ssh -L 11435:127.0.0.1:11434 anolis -N -f`（pid 1326503）已足够，新模型走同一隧道、换 `model` 名即可，**不需要新开隧道**。

### 6.5 一句话收口

**本地臂要的不是"更强的模型"，是三样东西：①32K 起步的 ctx 档位（现在 262K 是纯浪费且把显存吃死）；②harness 的 `max_tokens` 与 thinking 开关（现在都没有）；③一个能开 32K 上下文的候选（Qwen3.6-35B-A3B 单卡装得下、SWE/TB 双超、但必须先冒烟 #29783 与模板 400）。** Qwen3-Coder-Next 是能力上限探针（自报 SWE-V 70.6），但它 TB 倒退、显存贴边、**不会更快**——**不该作为换装首选**。

---

## 附录 A：复现脚本（本轮实际跑过的命令）

```bash
# A1 本地 30B 臂统计（本轮实跑）
python3 - <<'EOF'
import json,statistics as st
for d in ["bench-fix1-d1-30b","bench-fix1-d2-30b","bench-fix1-d3-30b"]:
    rows=[json.loads(l) for l in open(f"/tmp/{d}/results.jsonl") if l.strip()]
    sc=[r for r in rows if r.get("reward") is not None]
    ok=[r for r in rows if r.get("reward") is True]
    w=[(r.get("agent_wall_ms") or 0)/1000 for r in rows if r.get("agent_wall_ms")]
    tps=[r["tokens"]["output"]/((r.get("agent_wall_ms") or 1)/1000) for r in rows if r.get("tokens") and r.get("agent_wall_ms")]
    print(d, len(rows), f"pass={len(ok)}/{len(sc)}", f"turns_med={st.median([r['turns'] for r in rows if r.get('turns')])}",
          f"wall_med={st.median(w):.0f}s", f"eff_tps_med={st.median(tps):.1f}")
EOF

# A2 ollama 日志：上下文深度分布（本轮实跑，脚本在 /tmp/depth.py）
ssh anolis 'python3 - /data/models/ollama-serve.log ALL' < /tmp/depth.py
# → ALL calls 7974 ... ctx depth: med 10289 p90 20830 p99 28776 max 63157

# A3 ollama 日志：decode 速率 vs 上下文深度（本轮实跑，脚本在 /tmp/parse_ollama_log.py）
ssh anolis 'python3 - /data/models/ollama-serve.log' < /tmp/parse_ollama_log.py
# → ctx<1000: 116.2 / ctx<4000: 109.2 / ctx<8000: 39.2 / ctx<16000: 38.0 tok/s

# A4 装载配置（S1 时代 vs 微基准）
ssh anolis "sed -n '123655,123712p' /data/models/ollama-serve.log"   # n_ctx=524288, KV 49152 MiB
ssh anolis "grep -nE 'KV buffer size|n_ctx  *=' /data/models/ollama-serve.log | tail -20"

# A5 模板 400
ssh anolis "grep -n 'Cannot have 2 or more assistant' /data/models/ollama-serve.log"

# A6 机器与 runner 状态
ssh anolis 'nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv; cat ~/.config/ollama/env'
ssh anolis "strings -a /data/models/lib/ollama/libllama.so.0 | grep -oE 'QWEN3NEXT|QWEN35MOE|QWEN35|QWEN3MOE' | sort -u"

# A7 ollama registry 体积
curl -s https://registry.ollama.ai/v2/library/qwen3-coder-next/manifests/q4_K_M
curl -s https://registry.ollama.ai/v2/library/qwen3.6/manifests/35b
```

## 附录 B：本报告与同期笔记的关系

- 本文是**负载规格**视角（harness 源码 + 我们自己的实测结果 + anolis 日志），不重复外部模型情报。
- 外部模型规格/分数/第三方实测一律【转引】`调研/本地模型选型/notes/qwen-family.md`（其 §11 有原始 URL 清单），并在其中【转引】处标出。
- **本轮推翻的两条同期笔记结论**：
  1. `notes/v100-speed-data.md` 的「现役 18.5GB + num_ctx 8192 时整模型只落在 1 张 V100S 上，第二张全程闲置」——**被 ollama 日志推翻**：模型分在两张卡上（S1 那次 7,920+4,141 MiB，今天微基准那次 8,976+8,549 MiB）。
  2. `notes/qwen-family.md` §7.2 的「现役是 2 slot × 8192」——**对 S1 生产配置不成立**：S1 期间实际是 2 slot × 262,144；8192 只出现在 2026-10-21 的微基准装载里。
- 另修正任务书的一处口径：「每题约 10 轮工具调用」⇒ 实测中位 **40 轮**（D1）。
