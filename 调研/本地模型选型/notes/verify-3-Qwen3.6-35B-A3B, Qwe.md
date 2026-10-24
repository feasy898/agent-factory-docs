# 复核档案：Qwen3.6-35B-A3B（第 3 名候选 / 复核对象首位）

- 复核员：独立复核子代理（Qwen3.6-35B-A3B, Qwe）
- 复核日期：2026-10-21
- 复核对象：**Qwen3.6-35B-A3B**（对比基线：Qwen3-Coder-Next、Qwen3.8-27B、现役 qwen3-coder-30b）
- 复核依据材料：本次会话的「原调研摘要」+ 同工作区 `调研/本地模型选型/notes/eval-landscape.md`（前一轮产出的被复核结论）
- **总判定：原结论的「方向」成立、但支撑数字大多不可比；「首选」结论成立，但成立的理由要换掉，并且必须带上一个此前缺失的缓解手段。**

---

## 0. 本轮的方法与可达性（先说清楚哪些是我查到的、哪些查不到）

**可达并已实际抓取的一手来源：**

| 来源 | 我实际跑的命令 / 动作 | 结果 |
|---|---|---|
| ollama registry | `curl https://registry.ollama.ai/v2/library/qwen3.6/manifests/<tag>`（33 个 tag 逐个） | 拿到每层字节数、runner、format、来源 build |
| ollama blob | `curl -r 0-16000000 <blob-url>` **HTTP Range 只取 GGUF 头**，自写 GGUF v3 解析器 | 拿到 1194 个 tensor 的 name/dims/type/offset |
| HF（经 hf-mirror） | `curl https://hf-mirror.com/api/models/...`、 `/raw/main/config.json`、 `/raw/main/README.md` | 下载量、likes、config、模型卡全文 |
| github.com | issue 网页 HTML 解析（`react-app.embeddedData`）+ GitHub REST（撞限后改网页） | 逐条读 issue 正文与评论 |
| artificialanalysis.ai | `/models/<slug>` 逐模型页解析 RSC payload | **第三方独立评测数据**（见 §4） |
| www.swebench.com | 解析内嵌 `<script id="leaderboard-data">`（2,362,382 B，5 个榜） | 官方榜全部 323 条记录 |
| scaleapi.github.io/SWE-bench_Pro-os/ | 抓页面 | SWE-bench Pro 公开榜 |
| miyagadget.page | 抓 2026-07-15 / 2026-09-04 两篇原文 | **V100 实测原始数据** |
| arxiv.org/abs/2603.00729 | 抓摘要 | 确认是 Qwen3-Coder-Next Technical Report |
| docs.ollama.com/gpu、/api/chat、/capabilities/thinking | 抓页面 | ollama 对 V100 的官方支持、think 参数语义 |

**本环境不可达（因此相关结论一律标「无法核实」）：** `huggingface.co` 直连（curl 25s 超时，**但 hf-mirror.com 可达，所有 HF 数据经镜像取得**）、`google.com`、`news.ycombinator.com`、`reddit.com`。GitHub REST API 未认证配额 60/h，**本轮多次撞限**（故部分 issue 正文改用网页 HTML 解析）。

**我明确没有做的事：**
- **没有下载任何模型权重**（GGUF 只用 Range 请求读了 <20 MB 的头部）。
- **没有在任何机器上跑过该模型**，没有跑 llama-bench，没有做冒烟。**下面所有 tok/s 都不是我实测的。**
- 本机（复核员机器）不是 anolis，没有 V100。

---

## 1. 模型真实状态（一手核实，非转述）

### 1.1 官方仓库与许可证

| 项 | 值 | 出处 |
|---|---|---|
| 官方 HF 仓库 | `Qwen/Qwen3.6-35B-A3B` | hf-mirror `/api/models/Qwen/Qwen3.6-35B-A3B` |
| 下载量 / likes | **3,641,803 / 3,012** | 同上 |
| 创建 / 最后更新 | 2026-04-15 / 2026-04-24 | 同上 |
| 许可证 | **Apache-2.0** | README frontmatter `license: apache-2.0` + cardData `license: apache-2.0` + ollama license blob 全文（Apache 2.0 原文）+ AA `licenseName: "Apache 2.0"` |
| gated | false | HF API |
| model_type / architectures | `qwen3_5_moe` / `Qwen3_5MoeForConditionalGeneration` | config.json |

### 1.2 参数与架构（config.json + 官方 README，两处一致）

```
num_hidden_layers            40
layer_types                  {linear_attention: 30, full_attention: 10}
full_attention_interval      4
num_experts                  256
num_experts_per_tok          8
shared_expert_intermediate_size  512
moe_intermediate_size        512
hidden_size                  2048
num_attention_heads          16
num_key_value_heads          2
head_dim                     256
partial_rotary_factor        0.25
max_position_embeddings      262144
mtp_num_hidden_layers        1
dtype / mamba_ssm_dtype      bfloat16 / float32
vocab_size                   248320
```

官方 README「Model Overview」原文：
- "Number of Parameters: **35B in total and 3B activated**"
- "Hidden Layout: **10 × (3 × (Gated DeltaNet → MoE) → 1 × (Gated Attention → MoE))**"
- "Number of Experts: 256 / Number of Activated Experts: **8 Routed + 1 Shared**"
- "**MTP: trained with multi-steps**"
- "Context Length: **262,144 natively and extensible up to 1,010,000 tokens**"
- "Type: Causal Language Model **with Vision Encoder**"

> **激活口径要写准**：不是「8/256」，而是「**8 个路由专家（top-8）+ 1 个恒定激活的共享专家**」。

### 1.3 GGUF 与量化体积（我自己从字节算的，不是抄标称）

**手法**：对 ollama registry 的 model blob 发 `curl -r 0-16000000`（HTTP 206，只取头），自写 GGUF v3 解析器读出 1194 个 tensor 的 name/dims/type/offset，按 ggml 的 (bytes_per_block, elems_per_block) 表算字节。

`qwen3.6:35b-a3b-q4_K_M` blob（sha256:f5ee307a…，23,938,321,664 B）：

```
TYPE       BYTES            COUNT
Q4_K       13,451,378,688   349
Q6_K        9,490,145,280    94     ← MoE down_exps / shared_expert 用的是 Q6_K
F16           892,497,920   207     ← 视觉塔
F32            92,290,496   544
合计       23,926,312,384  (23.93 GB)  vs 文件 23,938,321,664 B → 差 0.05%（元数据+对齐）
```

GGUF KV 元数据（同一 blob 内解析）：

```
general.architecture        = 'qwen35moe'
general.parameter_count     = 35,951,822,704
general.file_type           = 15  (Q4_K_M)
qwen35moe.block_count       = 40
qwen35moe.context_length    = 262144
qwen35moe.expert_count      = 256
qwen35moe.expert_used_count = 8
qwen35moe.full_attention_interval = 4
qwen35moe.attention.head_count_kv = [0,0,0,2, 0,0,0,2, ...]   ← 只有 10 个全注意力层有 KV
```

**该 blob 内含 20 个 `mtp.*` tensor 和视觉 `v.*` tensor** —— 也就是说 ollama 这个 tag 是「主模型 + MTP 头 + 视觉塔」打包在一起。

**ollama 官方 tag 体积（逐个 manifest 读出）**：

| tag | 总量 | 构成 |
|---|---|---|
| `qwen3.6:35b` = `qwen3.6:35b-a3b` | **22.62 GB (21.07 GiB)** | model 21.72 GB（**block_count 41** = 40 主层 + 1 MTP 层，`nextn_predict_layers=1`）+ **projector 0.90 GB (CLIP F16, 447M)** + license + params |
| `qwen3.6:35b-a3b-q4_K_M` | **23.94 GB (22.28 GiB)** | 单 blob（主模型+MTP+视觉全在里面），1045 个 tensor 分片是 mxfp8/nvfp4 那些 |
| `qwen3.6:35b-a3b-q8_0` | 38.70 GB | model 37.80 + projector 0.90 |
| `qwen3.6:35b-a3b-bf16` | **71.97 GB (67.03 GiB)** | **超过 64GB 显存** |
| `qwen3.6:35b-a3b-mxfp8` | 38.05 GB | 1055 个 tensor 分片 |
| `qwen3.6:35b-a3b-nvfp4` | 23.60 GB | 1055 个 tensor 分片 |
| `qwen3.6:27b` | 17.77 GB (16.55 GiB) | |
| `qwen3-coder-next:q4_K_M` | 51.74 GB (48.19 GiB) | 单 model layer |

**官方 llama.cpp org 的 GGUF**（`ggml-org/Qwen3.6-35B-A3B-GGUF`，hf-mirror 上 **120,849 downloads**，lastModified 2026-10-19）：

```
19.017 GiB   Qwen3.6-35B-A3B-Q4_K_M.gguf     ← 纯文本，无视觉无 MTP
34.369 GiB   Qwen3.6-35B-A3B-Q8_0.gguf
64.612 GiB   Qwen3.6-35B-A3B-BF16.gguf
0.572 GiB    mmproj-Qwen3.6-35B-A3B-Q8_0.gguf
0.987 GiB    mtp-Qwen3.6-35B-A3B-Q4_0.gguf
0.392 GiB    dflash-Qwen3.6-35B-A3B-Q8_0.gguf
```

**其他 GGUF 下载量**（hf-mirror `/api/models?search=Qwen3.6`）：`unsloth/Qwen3.6-35B-A3B-GGUF` 1,263,771；`unsloth/Qwen3.6-35B-A3B-MTP-GGUF` 1,103,419；`bartowski/Qwen_Qwen3.6-35B-A3B-GGUF` 179,994；`nvidia/Qwen3.6-35B-A3B-NVFP4` **4,377,689**（见 §2.2，这是个陷阱）；`Qwen/Qwen3.6-35B-A3B-FP8` 3,478,815。
**ollama 官方 tag 下载量**：`qwen3.6:35b` 页面标 **7.2M Downloads**，Updated 1 week ago。

### 1.4 §1 的修正点

- **修正 A**：原结论「ollama Q4_K_M 仅 23–24GB」——对 `35b-a3b-q4_K_M`（23.94GB）成立，但**默认 tag `qwen3.6:35b` 实为 22.62 GB (21.07 GiB)**。ollama 页面同时挂 24GB 与 23GB 两个 build（digest 599a7133f2e3 / a7eb95c53bcf），原结论没区分。**纯文本任务应选 `35b`（主模型 21.72GB，视觉塔拆成独立 0.90GB projector 可不加载），比 `35b-a3b-q4_K_M` 省 2.2GB 显存。**
- **修正 B**：原结论把它当纯文本模型——**错。它是 VLM**（Qwen3_5MoeForConditionalGeneration + 27 层 CLIP 视觉塔，out_hidden_size 2048，patch 16×16×2，spatial_merge 2）。对我们纯文本 agentic 任务是纯负担。
- **修正 C**：原结论「激活 3B」——数字对，但表述应为「top-8 路由 + 1 共享，恒定激活」。
- **修正 D**：原结论「262,144（可扩 1.01M）」——✅ 官方原文证实。

---

## 2. 2×V100S-32GB（sm_70）到底能不能跑

### 2.1 引擎：llama.cpp 是唯一可行路

- **ollama 官方支持 V100**。docs.ollama.com/gpu 原文："Ollama supports Nvidia GPUs with compute capability **5.0+** and driver version **550 and newer**. Nvidia GPUs with compute capability 5.0 through 6.2 require driver version **570 or newer**." 支持列表 7.0 档明确含 "NVIDIA TITAN V **V100** Quadro GV100"。我们 V100S = CC 7.0 → 需 driver 550+，现装 570.133.20 → 满足。ollama 官方 tag 的 config blob 里 `requires: "0.30.0"` ≤ 我们的 0.40.6 → **tag 本身不挑版本**。
- **但**：官方预编译 llama.cpp 二进制**不含 sm_70 kernel**。miyagadget 原文："the prebuilt llama.cpp binaries have already dropped support for the V100 (Volta generation) … sm_75 (Turing) and later only; the V100's sm_70 (Volta) isn't included. There's simply no GPU kernel for the V100 baked into the binary." 必须自编 `-DCMAKE_CUDA_ARCHITECTURES=70`。我们用 CUDA 12.6，未踩 CUDA 13 移除 Volta 的坑。
- vLLM / SGLang：按任务书给的硬约束（vLLM V1 要求 CC≥7.5、V100 已被移除；SGLang 快路径要 sm_80+），在 V100 上不是可行路。**本轮未再独立复验这两条。**
- 架构支持已 GA 到可用程度：GGUF 里的 arch 字符串就是 llama.cpp 的 `qwen35moe`，且 `ggml-org` 在 2026-10-19 还在更新该 repo 的量化产物。

### 2.2 格式死路（Volta 硬件约束逐条落到本模型的具体 tag）

| 格式 | 本模型对应产物 | 在 sm_70 上 |
|---|---|---|
| **FP8 / MXFP8** | `35b-a3b-mxfp8` 38.05 GB、`27b-coding-mxfp8` | ☠️ 死路：无 FP8 张量核 |
| **NVFP4 / MXFP4** | `35b-a3b-nvfp4` 23.60 GB、`nvidia/Qwen3.6-35B-A3B-NVFP4`（**437 万下载**） | ☠️ 死路：FP4 是 Blackwell sm_100/sm_120 的东西 |
| **BF16** | `35b-a3b-bf16` **71.97 GB (67.03 GiB)** | ☠️ 双重死路：无 BF16 张量核 **且** 体积超 64GB |
| **Q8_0** | `35b-a3b-q8_0` 38.70 GB / ggml-org 34.369 GiB | ⚠️ 单卡 32GB 装不下；双卡够但 KV 被吃光；且实测比 Q4 慢 ~29% |
| **Q4_K_M** | ggml-org 19.017 GiB（纯文本）/ ollama 21.72 GB（含 MTP） | ✅ **唯一现实可行路** |

> **选型陷阱**：`nvidia/Qwen3.6-35B-A3B-NVFP4` 是本次搜索里下载量最高（437 万）的 Qwen3.6-35B-A3B 产物，**在 V100 上完全用不了**。同理 `Qwen3.6-35B-A3B-FP8`（347 万下载）。选型表必须显式写死「只用 Q4_K_M 家族」。

### 2.3 显存账（我按 GGUF 元数据算的，附口径）

**KV cache（我自己算）**：只有 10 个全注意力层有 KV（`head_count_kv` 每 4 层给一个 2，其余为 0）；K+V × 2 head × 256 dim × 2 B(f16) = 2048 B/层 → ×10 层 = **20 KiB/token**。
- 16K ctx → **320 MiB**；32K → 640 MiB；64K → 1.25 GiB；262K → 5.0 GiB
- 另加 30 个 GDN 线性注意力层的循环态（conv state + SSM state），量级几十 MB/序列

**实测口径（第三方）**：miyagadget 在 V100-SXM2-32GB 上跑 ~22GB 的 Q4_K_M（ctx 16384）→ **峰值显存 27.0 GB**。
即 22GB 权重实际吃 27GB，**约 5GB 被 llama.cpp 的计算缓冲 / CUDA graph / 批缓冲吃掉，不是 KV**。

**推论**：
- 选 ggml-org 纯文本 Q4_K_M（19.02 GiB）→ 预计峰值 ~24.5 GB，32GB 卡余 ~7.5 GB。
- 选 ollama `35b` 主 blob（21.72 GB = 20.23 GiB，含 MTP 头）→ 预计峰值 ~26.7 GB，余 ~5 GB。
- 两条路都能单卡 32GB 跑，**都不需要 CPU 卸载** → §2.4 的 #26609（专家卸载崩溃）对我们**不适用**。
- **双卡 split 在 V100 上别碰**（#27366，见下）。

> **修正 E（重要算错）**：原结论「24GB 模型在 32GB 卡上 KV 余量仅约 8GB（16K 上下文即吃满）」——**错**。16K 上下文的 KV 只有 320 MiB；吃显存的是权重 + 计算缓冲。真正「吃满」的原因是 22–24GB 权重本身 + llama.cpp 缓冲。结论（单卡能装）不变，但理由和余量数字都错。

### 2.4 已知坑（逐条读 issue 原文；均为 llama.cpp / ggml-org）

| # | 状态 | 与本模型/我们场景的关系 |
|---|---|---|
| **#25248** | CLOSED（**stale 自动关闭**，非修复） | **「Qwen 3.6 crashes llama-server with prompts more than 132 tokens」**，硬件 **16GB V100**，模型 `unsloth/Qwen3.6-35B-A3B-UD-Q4_K_XL`，CUDA 12.6，llama.cpp b9860。132 token 正常、133 token 崩。**根因不是 Volta，是 build 里带了 `-DGGML_ZENDNN=ON`**；报告者重建去掉 ZenDNN 即正常，并说「加上 ZenDNN 才需要用 `--cpu-moe` 之类参数显式指定 offload 行为」。另一用户 @jhughes2112 报 Qwen3.6 27B/35B 同样「越长越容易 400」。@TheOneWhoWill 在 5070 Ti 上**复现不出来**，误判为 GPU-specific；实际根因是 CPU 侧 ZenDNN。→ **可执行结论：自编 llama.cpp 不要开 ZENDNN；auto-fit 之外显式指定 offload 策略。** |
| **#29255** | **OPEN** | 7× Volta sm_70 layer-split，**"probabilistic CUDA error 'invalid argument' at kernel launch"**，触发条件 = **大 prefill + 部分前缀复用**，原话「during normal long agent sessions (OpenAI-compatible server, one client, very long contexts with heavy prefix reuse) llama-server dies roughly daily — recently ~6 times a day」。跨架构复现（Qwen3.8-Flash-Next、DeepSeek-V4-Flash）。→ **这正是我们 af-bench 的形态**（每题 ~10 轮工具调用、上下文单调增长、前缀高度复用）。**这是本候选在我们机器上最现实的运行时风险**，比原结论担心的「输出损坏」更具体。 |
| **#29783** | **OPEN** | Qwen3.5-122B-A10B（**Gated DeltaNet**）在 **6× V100 32GB 上第一个请求即崩**，ctx 261888/65024 都崩，"CUDA error: invalid argument" at kernel launch，**无任何 prefill 进度**。**同族同架构**（GDN + MoE、256 专家 top-8、KV heads 2 / head_dim 256）。迁移到 35B-A3B 是**推断，非实测**。 |
| **#26609** | **OPEN** | **直接命中本模型**：`Qwen3.6-35B-A3B-UD-Q4_K_M` + **部分专家卸载到 CPU** → 第二个请求必崩 "illegal memory access"，**`-fa off` 才消失**（环境 RTX 5070 12GB，22GB 模型放不下 12GB 显存被迫卸载）。→ **回答待验证假设里那条反面：--n-cpu-moe / 部分专家卸载在 sm_70 上不是可行退路，而是已知崩溃向量。** 好消息是我们 32GB 卡根本不需要卸载。 |
| **#27623** | **OPEN** | Qwen3.8-27B（**同 GDN 混合注意力**）decode 在 KV 位置 >~80K 时**塌约 25 倍**（68K 处 33 t/s → 91K 处 1.4 t/s），prefill 仍 ~1300 t/s。→ 同架构的 Qwen3.6-35B-A3B 有同类风险，需实测。 |
| **#23577** | **OPEN** | 「MTP with Qwen3.6 27B outputs repeated `////` after long session」。我们的 ollama `35b` build **内嵌 MTP 头**（我数到 20 个 `mtp.*` tensor，params 里 `draft_num_predict: 2`）。→ 开 MTP 必须冒烟「长会话重复字符」。另注：@jhughes2112 指出 unsloth 的 MTP GGUF 文件名里**没写 MTP**，容易误认成非 MTP 版。 |
| **#27366** | closed | `-sm tensor` 在**多卡 Volta** 上挂死并泄漏显存；`-sm row` 在 CUDA 不可用。→ 别用双卡 tensor-split。 |
| **#28037** | OPEN | 「Analysis: Volta (SM70/SM72) Flash Attention Optimization Paths」→ V100 的 FA 路径处于「分析中」状态，不是成熟路径。 |
| **#28777** | OPEN | DFlash2 + `--split-mode tensor` 在 sm_70 上 GGML_ASSERT 崩溃。 |

**负面检索结果（很重要）**：`qwen35moe + sm_70` 在 llama.cpp issue 全文检索 **0 命中**；`qwen3.6 + V100` 只有 9 条，**其中没有一条是「Qwen3.6 在 V100 上跑通」的正面报告**。
→ 社区在 llama.cpp issue 追踪器里**没有 Qwen3.6-35B-A3B 在 V100 上跑通的公开证据**。正面的只有两处：#25248 报告者确实在 16GB V100 上加载了 Qwen3.6-35B-A3B 并跑到 132 token 才崩；miyagadget 在 V100-SXM2 上跑到 98.8 tok/s。

### 2.5 落在我们机器上的具体跑法（结论，不改原结论）

- **引擎**：llama.cpp 自编，`-DCMAKE_CUDA_ARCHITECTURES=70`，CUDA 12.6，**不要 `-DGGML_ZENDNN=ON`**；或直接用 ollama 0.40.6（官方支持 V100，tag 要求 ≥0.30.0）。**ollama 自带 runner 是否真带 sm_70 kernel，我没能核实**（本机没装 ollama、也不在 anolis 上）→ 这是冒烟第 0 条。
- **权重**：优先 `ggml-org/Qwen3.6-35B-A3B-GGUF/Qwen3.6-35B-A3B-Q4_K_M.gguf`（**19.017 GiB，纯文本**）；要 MTP 投机解码另挂 `mtp-Qwen3.6-35B-A3B-Q4_0.gguf`（0.987 GiB）；**不要**挂 mmproj（纯文本用不上，还占 0.57 GiB）。ollama 侧用 `qwen3.6:35b`（不要用 `35b-a3b-q4_K_M`，前者省 2.2GB）。
- **显存**：单卡 32GB 装 19.02 GiB 权重，峰值预计 ~24.5GB，余 ~7.5GB；ctx 16K–32K 足够 af-bench（KV 320–640 MiB）。**双卡 split 别碰**（#27366）。
- **请求**：`think: false`（或 `think: "low"`）。ollama `/api/chat` 的 `think` 字段语义（docs.ollama.com/api/chat）："true requests thinking, false requests no thinking output, and null uses the model default. String values are model-defined; supported names must match /api/show exactly." 具体支持值与默认值要 `POST /api/show` 读（**我拉不了模型，读不到**）。采样按官方非思考档：`temp=0.7, top_p=0.80, top_k=20, min_p=0.0, presence_penalty=1.5, repetition_penalty=1.0`。
- **冒烟清单（按必测排序）**：① 16K prompt 是否复现 #25248 式崩溃（不带 ZENDNN）；② 30+ 轮长会话 + 重度前缀复用，盯 #29255 的 kernel-launch 崩溃；③ 85K+ 位置 decode 速是否塌（#27623 同架构）；④ 开 MTP 后长会话是否吐重复 `////`（#23577）；⑤ 输出内容正确性（防「速度正常但内容损坏」）。

---

## 3. 速度证据

### 3.1 唯一的第三方 V100 实测（我直接读了原文）

**miyagadget.page, 2026-07-15**《Tesla V100 32GB Local LLM Benchmark: Qwen 3.6 at 98.8 tok/s》

环境（原文表格）：
- GPU **Tesla V100-SXM2-32GB**（Volta, CC 7.0）｜Xeon Platinum 8260
- Driver/CUDA **580.159.03 / 12.9**｜Runtime: **llama.cpp 自编 sm_70**
- Model: `Qwen3.6-35B-A3B-GGUF:UD-Q4_K_M`（~22GB）
- 测量：每任务 2 次热跑取最后一次，temperature=0，**context 16384**，**thinking ON**

结果（原文表格）：

| 任务 | decode tok/s |
|---|---|
| 日文摘要 | 99.02 |
| 代码生成 | 98.60 |
| 数学推理 | 99.14 |
| 长文写作 | 98.54 |
| **平均 decode** | **98.8 tok/s** |
| **平均 prefill** | **352 tok/s** |

同卡同天对照：Qwen3.6-27B Q4_K_M **32.9 tok/s**、Qwen3.6-27B Q8_0 **23.4 tok/s**。
峰值显存 **27.0 GB**、峰值功耗 206.2 W、加载 11.0 s。

作者自己给的 PCIe 修正（原文）："The PCIe version has a slightly lower boost clock (**1380MHz vs. 1530MHz**), so your real-world numbers on a PCIe card could run up to **roughly 10% slower**."

### 3.2 换算到我们机器

**98.8 × 0.9 ≈ 89 tok/s**（用作者自己给的 PCIe 修正系数；我未叠加其他修正因子，因为作者未量化显存带宽差异——SXM2 是 900 GB/s，PCIe 版 V100S 是 900 GB/s 里的 756 GB/s，比例 0.84，若按带宽算应是 ~83 tok/s，**但这是我的推算，不是实测**）。

**关键对比**：

| | 我们的 anolis 实测 | miyagadget V100-SXM2 | 推算到 V100S-PCIe |
|---|---|---|---|
| 现役 qwen3-coder-30b（Qwen3-Coder-30B-A3B，128 专家，qwen3_moe） | **135.7 tok/s**（V100S-PCIe, num_ctx 8192） | — | 135.7（现役基线） |
| Qwen3.6-35B-A3B（256 专家 + 30 层 GDN） | 未测 | 98.8 | **~89** |

> **修正 F（重要）**：原结论「激活参数与现役相同故解码速度同档」——**错**。第三方实测 + 换算后，35B-A3B 在 V100S 上约 **89 tok/s**，**比现役 135.7 慢约 1.5 倍**。同为 3B 激活，但：① 256 专家 vs 现役 128 专家 → 散点读更多；② 30 层 GDN 线性注意力每步还要跑 30 次递归 + 10 次全注意力；③ 现役跑的是 Qwen3-Coder-30B 自己的 qwen3_moe 架构（纯 MoE，无 GDN）。原结论「速度同档」是按「激活参数相同 ⇒ 权重读取字节数同量级」的机制推断，**没有考虑架构差异**，而第三方数据明确否定了「同档」。

### 3.3 速度证据的缺口（明确说「没有」）

- ❌ **没有** 3090 / P40 / 4060Ti 16G/24G 上针对 **Qwen3.6-35B-A3B** 的第三方 tok/s。
- ❌ **没有** **双卡** V100 上 35B-A3B 的任何实测。
- ❌ **没有** 任何 **ollama 0.40.6** 上跑 35B-A3B 的实测。
- ❌ **没有** 35B-A3B 在 >16K 上下文下的速度数据（miyagadget 只到 16K，而 #27623 的塌陷点在 80K+）。
- ⚠️ **必须防止误用**：英文社区笔记里的「134 t/s」是 **Artificial Analysis 记录的 API 服务端输出速度**（AA 自己的基础设施/供应商），**不是本地 GPU 速度**，不能拿来当我们机器的估计。
- ⚠️ 英文社区笔记提到的 Qwen3.6-27B 第三方 V100 实测（neutrinobro，2×V100 48GB，Q8_0，~22 t/s）**是稠密 27B，不是 35B-A3B**，不能混用。

---

## 4. 质量证据：第三方独立复现

### 4.1 有，而且是本轮最重要的新证据

**Artificial Analysis**（第三方独立评测；我 2026-10-21 逐模型页解析 RSC payload）：

| 模型 | AA Intelligence Index | **Terminal-Bench 2.1** | TB 4.0 | TB Hard | avg reasoning tokens | **s / task** |
|---|---|---|---|---|---|---|
| **Qwen3.6 35B A3B (Reasoning)** | **18.23** | **44.94 %** | 0 | 34.85 % | **5395** | **226.5** |
| Qwen3.6 35B A3B (**Non-reasoning**) | 15.23 | 41.57 % | — | 25.76 % | **0** | — |
| Qwen3.5 35B A3B | **19.33** | — | — | 26.52 % | 2000 | — |
| Qwen3.6 27B（稠密同代） | 21.43 | **60.67 %** | 0 | 34.85 % | 5676 | 452.8 |
| Qwen3.8 27B (Reasoning) | **33.68** | **79.78 %** | 5.56 % | — | **2000** | 1172.9 |
| Qwen3.8 27B (non-reasoning) | 20.15 | 49.06 % | 0 | — | 0 | 587.2 |
| Qwen3-Coder-Next | 9.24 | 38.20 % | 0 | 18.18 % | 0 | **150.1** |
| **Qwen3-Coder-30B-A3B-Instruct（现役）** | **9.59** | — | — | 15.15 % | 0 | — |

> AA 的 s/task 是它自己基础设施上的每任务墙钟。**绝对值不能搬到 V100**（我们 decode 比 AA 的托管环境慢一到两个数量级），**同表内的比值可参考**。

**由此得到的独立结论：**

1. **方向被独立证实**。Qwen3.6-35B-A3B 强于 Qwen3-Coder-Next（AA II 18.23 vs 9.24，TB2.1 44.94 % vs 38.20 %），也明显强于现役 30B（AA II 9.59；TB Hard 34.85 % vs 15.15 %）。**「35B-A3B > Coder-Next > 现役」这个排序有第三方背书**，原结论的排序方向站得住。
2. **但非思考模式几乎不损失能力 —— 这是原结论缺失的定量缓解手段**。AA 实测 non-reasoning 变体：II 15.23（-3.0）、TB2.1 41.57 %（-3.4 pt）、**reasoning token = 0**。原结论点名的「最大风险 = token 膨胀」因此有了明确对策：**请求钉 `think: false`**，用 3 分 II 换掉每题 5395 个 reasoning token。
3. **「Qwen3.8 系列 token 消耗是同代 2 倍」这个前提被独立数据推翻**。AA 实测：Qwen3.8-27B (reasoning) **只用 2000 reasoning tokens**，Qwen3.6-35B-A3B **用 5395**——**烧 token 的是 Qwen3.6-35B-A3B 自己**，而 Qwen3.8-27B 拿 TB2.1 79.78 %（vs 44.94 %）、AA II 33.68（vs 18.23），代价是每任务 1172.9 s（vs 226.5 s，5.2 倍）。→ 稠密 27B 的「分数天花板」是真的，但「token 膨胀」这个用来否掉它的理由，方向反了。
4. **Qwen3.6-27B（稠密同代）AA II 21.43 / TB2.1 60.67 % / 452.8 s/task**。原结论「稠密 27B 在 V100 上 33 tok/s，墙钟不可接受」**方向仍对**（33 vs 89 ≈ 2.7 倍），但「分数天花板」要修正为「同代 27B 稠密比 35B-A3B 高 3.2 分 II / 15.7 pt TB2.1，不是 Qwen3.8-27B 独享」。
5. **代际提升没被复现**：厂商表里 Qwen3.6 全面强于 Qwen3.5（TB2.0 51.5 vs 40.5、Pro 49.5 vs 44.6），但 AA 上 **Qwen3.5-35B-A3B (19.33) 略高于 Qwen3.6-35B-A3B (18.23)**。至少说明「3.6 必然强于 3.5」在独立口径下不成立。
6. **Qwen3-Coder-Next 是「墙钟最短的」**（150.1 s/task，且是**非思考模型**，无 token 膨胀）。原结论只说「分数被全面压制」，没提它在墙钟维度反而占优 —— 这在「用墙钟而不是分数做决策」的框架下是一个原结论漏掉的重要事实。
7. **官方榜上查无此模型（两处都查了）**：
   - SWE-bench 官方榜：我解析 `www.swebench.com` 内嵌 `<script id="leaderboard-data">`（2,362,382 B，5 个榜：Multilingual 13 / Test 24 / **Verified 180** / Lite 84 / Multimodal 22 条，合计 323 条），**没有任何 Qwen3.6-35B-A3B 条目**。Verified 榜最新条目 2026-02-26、只有闭源 API；榜上只有我们现役 Qwen3-Coder-30B-A3B-Instruct（OpenHands 51.6、EntroPO+R2E 52.2 / 60.4）。→ **「SWE-bench Verified 73.4」完全无法用官方榜交叉验证。**
   - SWE-bench Pro 官方榜：`scaleapi.github.io/SWE-bench_Pro-os/` 公开榜 7 行（最高 SWE-Agent + claude-4-5-Sonnet **43.72**），**无 Qwen3.6 条目**。该页只写 V1：**1,865 题 / 41 仓**，public set 11 仓，held-out 12 仓，commercial 18 仓，CI 按 **730 题**算。

### 4.2 厂商自报数字的协议（我从官方 README 逐字读到，这是原结论漏掉的关键限定）

官方 README「Benchmark Results」下方的脚注原文：

> - "**SWE-Bench Series: Internal agent scaffold (bash + file-edit tools)**; temp=1.0, top_p=0.95, **200K context window**. **We correct some problematic tasks in the public set of SWE-bench Pro and evaluate all baselines on the refined benchmark.**"
> - "**Terminal-Bench 2.0**: Harbor/Terminus-2 harness; 3h timeout, 32 CPU/48 GB RAM; temp=1.0, top_p=0.95, top_k=20, **max_tokens=80K**, 256K ctx; avg of 5 runs."
> - "NL2Repo: Others are evaluated via **Claude Code** (temp=1.0, top_p=0.95, **max_turns=900**)."
> - "QwenClawBench: An **internal** real-user-distribution Claw agent benchmark (**open-sourcing soon**); temp=0.6, 256K ctx."
> - "QwenWebBench: An **internal** front-end code generation benchmark …"

### 4.3 修正点（继续）

- **修正 G（最重要的一条）**：**「SWE-Pro 49.5 vs 42.7」「TB2.0 51.5 vs 34.2」「SWE-V 73.4 vs 70.6」这三组对比不可比。**
  - 35B-A3B 的 49.5 跑在**厂商自己修正过的题集**（"we correct some problematic tasks … evaluate all baselines on the refined benchmark"）上、用**内部 scaffold**（"Internal agent scaffold"）；
  - Coder-Next 的 42.7 是**公开 SWE-Agent harness** 口径（arXiv 2603.00729 技术报告表格）；
  - 两组数字**不是同一把尺子**。而且 49.5 **高于 SWE-bench Pro 官方公开榜第一名 43.72**，这本身就说明它不是公开榜口径。
  - → 第三方同口径下的真实差距是 **AA TB2.1 44.94 % vs 38.20 %**（6.7 pt），不是「51.5 vs 34.2」（17.3 pt）。**方向不变，幅度被夸大约 2.6 倍。**
- **修正 H**：「SWE-bench Pro V2 642 题 / 11 仓 + HARD-51（判分歧义率 32.4%）」——**我在官方页面上找不到这个口径**。官方页写的是 V1：1,865 题 / 41 仓 / public 11 仓 / CI 按 730 题。**标为无法核实。**
- **修正 I**：「TB 2.1 / 4.0 版本号必须锁死」这条对，但原结论自己也没给出 Qwen3.6 在 TB 2.1/4.0 的官方数——**厂商只在 TB 2.0 上报过**。第三方 AA 的 TB2.1 = 44.94 %、TB4.0 = 0 是目前唯一可用的同代横向数（但注意 Coder-Next 的 TB4.0 也是 0，Qwen3.8-27B 才是 5.56 %，说明 TB4.0 上 0 分可能是「跑不动/没跑完」而非真实 0，**这一栏口径需另查**）。

---

## 5. 逐条裁定原结论

| 原结论主张 | 裁定 | 依据 |
|---|---|---|
| 模型真实存在、35B/3B 激活、ctx 262K、Apache-2.0、有官方 GGUF | ✅ **确认** | §1 全部一手核实 |
| ollama Q4_K_M 23–24GB | ⚠️ **修正** | `35b` 实为 22.62GB；`35b-a3b-q4_K_M` 为 23.94GB |
| 纯文本模型 | ❌ **推翻** | 是 VLM（CLIP 视觉塔 + mmproj） |
| 单卡 V100S 装得下 | ✅ **确认**（但余量算错） | 权重 19.02–20.23 GiB，峰值预计 24.5–26.7GB；KV 16K 仅 320MiB |
| 「KV 余量仅约 8GB，16K 即吃满」 | ❌ **推翻** | KV 20 KiB/token；吃显存的是权重 + 计算缓冲（实测 22GB 权重→27GB 峰值） |
| 激活同现役 ⇒ 解码同档 | ❌ **推翻** | 第三方 V100 实测 98.8(SXM2) → ~89 tok/s vs 现役 135.7，**慢约 1.5×** |
| 官方分全面压制 Coder-Next | ⚠️ **方向对、幅度被夸大约 2.6 倍** | 厂商口径不可比（内部 scaffold + 自修正题集）；第三方 AA TB2.1 44.94% vs 38.20% |
| 官方 SWE-V 73.4 | ⚠️ **无法交叉验证** | SWE-bench 官方榜 323 条记录里 **0 条** Qwen3.6-35B-A3B |
| 「最大风险 = token 膨胀，未实测」 | ✅ **确认，且已有缓解手段** | AA 实测 non-reasoning 变体只掉 3.0 分 II / 3.4pt TB2.1，**reasoning token = 0** |
| 「Qwen3.8 系列 xhigh → token 翻倍」 | ❌ **推翻（方向反了）** | AA 实测 Qwen3.8-27B = 2000 tokens，Qwen3.6-35B-A3B = 5395 tokens |
| 「qwen3_5 混合注意力在 sm_70 有 CUDA bug 先例」 | ✅ **确认且更具体** | #25248（V100 上 Qwen3.6-35B-A3B 崩，根因 ZenDNN 非 Volta）、#29255（sm_70 长会话前缀复用天天崩）、#29783（sm_70 GDN 首请求崩）、#27623（同架构 80K+ decode 塌 25×）、#23577（Qwen3.6+MTP 长会话吐 `////`） |
| 首选 Qwen3.6-35B-A3B | ✅ **维持，但理由必须换** | 成立的依据不是「厂商分压制 Coder-Next」，而是「第三方 AA 口径下能力 ≈ 现役 30B 的 2 倍（II 18.23 vs 9.59；TB Hard 34.85% vs 15.15%），且激活参数与现役相同、体积只大 12%」 |
| 「更值得上」成立的条件 | ⚠️ **加前提** | 只有在 **think:false / 低 effort** 且接受 **decode 慢 1.5×** 时成立；think 默认 ON 时，5395 reasoning token 会把墙钟吃掉，墙钟很可能反而更差 |

**净结论**：原结论的**选型结果**我维持（Qwen3.6-35B-A3B 仍是三候选里最值得上本地臂的），但**支撑它的三根柱子都要换**：
1. 分数：改用第三方 AA 同口径（II 18.23 / TB2.1 44.94%），不引用厂商自报；
2. 速度：**承认比现役慢 1.5×**（~89 vs 135.7 tok/s），用 think:false 抵消；
3. 风险：从「可能输出损坏」换成三条**具体的、可冒烟的** sm_70 崩溃路径（#25248 ZenDNN、#29255 长会话前缀复用、#27623 80K+ 塌陷）+ 一条 MTP 专项（#23577）。

---

## 6. 明确「没做到 / 无法核实」的清单

- ❌ 没下载任何模型权重（GGUF 只用 HTTP Range 读头，合计 <20 MB）。
- ❌ 没在任何机器上跑过该模型；没跑 llama-bench；**没做冒烟**。§3 所有 tok/s 均为转引第三方。
- ❌ 复核员本机不是 anolis，没有 V100。
- ❌ huggingface.co 直连、google.com、news.ycombinator.com、reddit.com 在本环境不可达（hf-mirror.com 可达，HF 数据全部经镜像取得）。
- ❌ GitHub REST API 未认证配额 60/h，本轮多次撞限；部分 issue 正文改用 github.com 网页 HTML 解析取得。
- ❌ **ollama 自带 llama.cpp runner 是否包含 sm_70 kernel**——未核实（本机无 ollama、不在 anolis）。这是上机第一步要验的。
- ❌ **Terminal-Bench 2.0/2.1/4.0 官方榜里 Qwen3.6-35B-A3B 的行**——未取到（tbench.ai 数据在 RSC payload 里，本轮未解出）。AA 的 TB2.1 = 44.94% / TB4.0 = 0 是目前唯一的第三方同代横比数。
- ❌ **SWE-bench Pro "V2 642 题 / 11 仓 / HARD-51"**——官方页只有 V1 口径，无法核实。
- ❌ AA 的 TB4.0 = 0 的语义（真 0 分 vs 未完成）——未查证。
- ❌ ollama `qwen3.6:35b` 是否支持 `preserve_thinking`（官方 README 介绍的新选项，声称可降低 token 消耗）——ollama 侧未核实，HF 侧仅在 OpenAI 兼容 API 的 `chat_template_kwargs` 里见到。
