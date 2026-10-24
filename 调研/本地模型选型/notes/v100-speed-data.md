# V100 实测吞吐数据库 & 本地模型选型（2×V100S-32GB）

- 产出日期：2026-10-21
- 调研者：本地模型选型调研子代理（工作区 `调研/本地模型选型/notes/`）
- 基线环境（全部结论以此为准，不套用通用榜单）：
  - anolis-gpu-01：2× Tesla **V100S-PCIE-32GB**，CC 7.0（sm_70，**无 NVLink**），driver 570.133.20，CUDA 12.6 工具链，125 GB 内存
  - 已有：ollama **0.40.6**（自带 llama.cpp runner），**无**独立 llama-cli / llama-server / vLLM / SGLang
  - 现役：`qwen3-coder-30b` = Qwen3-Coder-30B-A3B-Instruct-Q4_K_M（18.5 GB，30.5B 总参 / 3.3B 激活，ctx 262144）
  - 现役实测（本次会话前已测，本轮直接引用）：decode **135.7 tok/s**、prompt **149.1 tok/s**（num_ctx 8192）、加载 10.5 s；并发 2 时每请求 109.7 tok/s、合计约 219 tok/s（`OLLAMA_NUM_PARALLEL=2`）
- 本轮调研方式：**只读网页与元数据**，未下载任何模型权重，未在 anolis 上跑新模型。

---

## 0. 一句话结论

**核心假设只成立一半。**「MoE 解码比同体量稠密快」在 V100 上是**硬事实**（实测 30B-A3B MoE 106–135 tok/s vs 27–32B 稠密 29.9–33.4 tok/s，约 **3.3–4.1×**）；
但「80B-A3B 比 30B-A3B 更快」**不成立**——解码受**激活参数**约束（两者都是 3B 激活），Qwen3-Coder-Next 不会比现役模型快，大概率持平或略慢（512 路专家的散点读比 128 路更吃亏）。
**真正可落地的候选是 Qwen3-Coder-Next（80B-A3B，官方 SWE-bench Verified 70.6%）**：非思考模式（不膨胀 token）、48.5–52 GB 权重正好塞进 2×32GB、速度预期与现役同档。
**同时发现一个零风险的现成收益**：现役 18.5 GB 模型 + num_ctx 8192 时**整模型只落在 1 张 V100S 上**（ollama 官方 FAQ + 我们自己的 ollama 日志双重确认），**第二张 V100S 全程闲置**。

---

## 1. 口径说明（先把话说死，避免表格被误读）

| 术语 | 本报告口径 |
|---|---|
| decode（吐字） | 单请求、单序列、batch=1，每 token 生成速率（tok/s）。**这是决定 agent 单题墙钟的量**。 |
| prefill（读提示） | 提示词读入速率（tok/s）。agent 任务里提示词是"上一轮的输出+工具回显"，量级远小于总吐字。 |
| 上下文深度 | 提示已占多长。**深度越大 decode 越慢**（KV 越大，注意力越贵），所有表都按深度标注。 |
| V100S vs SXM2 | **V100S-PCIE 核心频率 1380 MHz，SXM2 是 1530 MHz**。同卡型 SXM2 实测值搬到我们的 V100S 上要**乘 0.9 左右**（miyagadget 明确给出这条修正）。 |
| 我们的 a6000/3090 等横向卡 | 只做**相对位标尺**用，不作为选型依据。 |

> **重要边界**：下面绝大多数 V100 数据是**单卡**。`--split-mode layer` 切层是**串行**的，双卡只买到容量不买到速度；`--split-mode tensor` 才可能并行（见 §7.1，且上游有未修复的 V100 缺陷）。

---

## 2. 核心对照表：V100 上 Q4_K_M 稠密 14B / 27B / 32B 大致多少 tok/s

### 2.1 直接实测（单卡 V100 32GB，Q4 系量化，短上下文 / depth 0–4K）

| 稠密规模 | 模型 | 量化 | decode tok/s | prefill tok/s | 来源 | 证据类型 |
|---|---|---|---|---|---|---|
| 7–8B | Llama-2-7B | Q4_0 | **129.08**（无 FA）/ **134.76**（FA） | **3042.6** | knightli.com llama.cpp GPU 榜（`llama-bench -m llama-2-7b Q4_0 -p 512 -n 128 -ngl 999 -r 5`） | 第三方复现（llama-bench 原始输出） |
| 7–8B | Llama-2-7B / Mistral-7B / Llama3.1-8B / Qwen2.5-7B | Q4 | 107.5 / 107.3 / 84.1 / 86.0 | — | databasemart「Ollama GPU Benchmark on NVIDIA V100」（Ollama 0.5.11，较旧 llama.cpp） | 第三方复现 |
| 8B | Qwen3 8B | Q4_K | 90.5 @4k / 64.3 @16k / 44.6 @32k | 2756 @4k | hardware-corner RTX A6000 表（**A6000 768 GB/s**，非 V100） | 第三方复现（换卡） |
| **13–14B** | Qwen2.5-14B / deepseek-r1-14B | Q4 | **49.4 / 48.6** | — | databasemart（Ollama 0.5.11） | 第三方复现 |
| 13B | Llama-2-13B | Q4 | 67.5 | — | databasemart（Ollama 0.5.11） | 第三方复现 |
| 14B | Qwen3 14B | Q4_K | 53.8 @4k / 40.7 @16k / 30.8 @32k | 1713 @4k | hardware-corner RTX A6000 表 | 第三方复现（换卡） |
| **27B** | Qwen3.6-27B | **Q4_K_M**（~21 GB） | **32.9**（4 任务均值 33.04/32.76/33.03/32.88） | 206 | miyagadget 2026-07-15（V100-SXM2-32GB，llama.cpp 自编 sm_70，driver 580.159.03，ctx 16384，thinking ON） | 第三方复现 |
| **27B** | Qwen3.8-27B | **UD-Q4_K_XL**（16.34 GiB） | **33.41**（depth 0）/ 32.64 @4k / 30.42 @16k / 27.95 @32k / **15.84 @131k** | 826.0 @depth0 / 511.9 @32k / 236.5 @131k | miyagadget 2026-09-04（V100-**PCIe**-32GB，llama.cpp d230ddd/f9f09f0，`llama-bench -r 3`） | 第三方复现（**与我们的卡型最接近**） |
| 27B | Qwen3.8-27B | Q4_K_M | **30.570**（关投机解码，Q8 KV）→ 41.9（MTP draft 1） | — | dual-v100-llama.cpp 单卡报告（明确写「Tesla V100-PCIE-32GB, SM70, 250W, **无 NVLink 依赖**」） | 第三方复现 |
| 30–31B | Gemma-4-31B | Q4_K_M（20.4 GB） | **29.9** @1k / 29.2 @4k / 28.1 @16k / 27.5 @25k / 26.7 @33k | 496.7 @1k / 600 @4k | DmNep/llm-bench-v100（1×V100-SXM2-32GB，llama.cpp，2026-10-05） | 第三方复现 |
| 32B | Qwen3 32B | Q4_K | 24.6 @4k / 18.3 @16k / 13.5 @32k（**A6000**） | 736.2 @4k | hardware-corner RTX A6000 表 | 第三方复现（换卡） |
| 32B | Qwen3-Coder-32B(Q8_0) | Q8_0（32 GB，`--n-cpu-moe 8`） | 35.7（llama.cpp）/ 45.5（ollama） | 414 / 812 | DmNep/llm-bench-v100 | 第三方复现 |

### 2.2 同一台机器上的 MoE 对照（这是最有说服力的一组）

| 模型 | 类型 | 量化 | decode tok/s | 来源 |
|---|---|---|---|---|
| **Qwen3-30B-A3B（Thinking）** | MoE 30.5B / 3B 激活 | Q4_K_M（18.6 GB） | **133**（ollama）/ **110**（llama.cpp，q8_0 KV，ctx 131072）@1k；125/99 @4k；105/69.8 @16k；94.8/59 @25k；86.2/50.7 @33k；63.7/32.6 @67k；–/21.5 @115k | DmNep/llm-bench-v100 |
| Qwen3 30B (MoE) | MoE | Q4 | 106.35 @4k，58.64 @256k | hardware-corner V100 实测 |
| Qwen3.6-35B-A3B | MoE 35B / 3B 激活，256 专家（8 routed + 1 shared） | UD-Q4_K_M（~22 GB） | **98.8**（4 任务均值 99.02/98.60/99.14/98.54） | miyagadget 2026-07-15 |
| Qwen3 30B A3B | MoE | Q4_K | 131.2 @4k / 75.4 @16k / 48.1 @32k（**A6000**） | hardware-corner A6000 表 |
| **我们现役 Qwen3-Coder-30B-A3B** | MoE 30.5B / 3.3B 激活 | Q4_K_M（18.5 GB） | **135.7** @num_ctx 8192 | **我们 anolis 实测**（本轮未复测，沿用） |

### 2.3 推导出的"V100 32GB · Q4_K_M 稠密对照表"（本轮调研的主交付物）

| 稠密档 | 权重体积 | **V100 32GB 预期 decode（短上下文）** | 依据 |
|---|---|---|---|
| 7–8B | ~4.5–5 GB | **90–135 tok/s** | 直接实测区间（llama-bench 129–135；旧 ollama 84–107） |
| 13–14B | ~7.5–9 GB | **50–68 tok/s** | 直接实测 48.6–67.5（Ollama 0.5.11/Q4_0）；A6000 Q4_K 53.8 × (900/768) ≈ 63 |
| **27B** | ~16–18 GB | **30–33 tok/s** | 三处独立直接实测（32.9 / 33.41 / 30.57） |
| **30–32B** | ~18–20.5 GB | **27–30 tok/s** | 直接实测 29.9（31B）+ A6000 24.6 × (900/768) ≈ 29 |
| （参考）**30B-A3B MoE** | 18.5 GB | **110–136 tok/s** | 直接实测 133 / 106.35 / 我们 135.7 |

**⇒ 现役 135.7 tok/s 的正确对手是稠密 27B 的 ~33 tok/s，MoE 领先 4.1×；与稠密 14B 的 ~60 tok/s 领先 2.3×。**

---

## 3. 候选清单

| 模型 | 厂商 | 类型 / 激活参数 | Q4 体积 | ctx | GGUF 可得性 | 官方 agentic 分数 | 第三方反馈（V100 上） | 我们的适配判断 |
|---|---|---|---|---|---|---|---|---|
| **Qwen3-Coder-Next** | Alibaba | MoE 80B 总参 / **3B 激活**，512 专家（10 激活 + 1 共享），48 层混合（GatedDeltaNet + Gated Attention），qwen3_next 架构 | **48.53 GB**（unsloth Q4_K_M）｜52 GB（ollama q4_K_M）｜45.13（IQ4_NL）｜42.68（IQ4_XS） | 262,144 原生 | ✅ unsloth / Qwen 官方 GGUF，ollama 官方 tag `qwen3-coder-next:q4_K_M` | **SWE-bench Verified 70.6**（SWE-Agent）、Multilingual 62.8、**SWE-bench Pro 44.3**、**Terminal-Bench 2.0 36.2**、Aider 66.2（官方模型卡图，2026-02） | **未找到公开证据**：本轮没有找到任何 Qwen3-Coder-Next 在 V100 上的 tok/s 实测 | ✅ **首选**。非思考模式（token 不膨胀）、48.5 GB 塞进 2×32GB、解码预期与现役同档 |
| **Qwen3.6-35B-A3B** | Alibaba | MoE 35B / **3B 激活**，256 专家（8 routed + 1 shared），qwen3_5_moe 架构 | ~22 GB（unsloth UD-Q4_K_M）｜**23–24 GB**（ollama `qwen3.6:35b`） | 262,144 原生（可扩到 1.01M） | ✅ ollama `qwen3.6:35b`；unsloth GGUF | **SWE-bench Verified 73.4**、Multilingual 67.2、**SWE-bench Pro 49.5**、**Terminal-Bench 2.0 51.5**、TAU3-Bench 67.2 | ✅ **单卡 V100-SXM2 实测 98.8 tok/s**（Q4_K_M，thinking ON，ctx 16384）→ 搬到 V100S-PCIe 约 **89 tok/s** | ⚠️ **分数最高但墙钟最差**：thinking 模型 + reasoning_effort 默认 xhigh → token 膨胀 ~2×；V100 上有"思考烧完预算不出答案"的实证 |
| Qwen3.6-27B | Alibaba | **稠密 27B**，qwen3_5 架构 | **18–19 GB**（ollama `qwen3.6:27b`） | 262,144 | ✅ ollama + unsloth | **SWE-bench Verified 77.2**（本组最高）、Multilingual 71.3、Pro 53.5、**Terminal-Bench 2.0 59.3** | 27B 稠密在 V100 上 ≈ 33 tok/s（按 Qwen3.6-27B 家族推） | ❌ 墙钟 4.1× + thinking 膨胀 2× ≈ 8×，不适合"量产臂" |
| Qwen3.8-27B | Alibaba | **稠密 27B**，混合线性注意力（64 层里 48 层 GatedDeltaNet、16 层全注意力），qwen35 架构 | **18 GB**（ollama `qwen3.8`）｜16.34 GiB（UD-Q4_K_XL） | 262,144 原生（可扩 1M） | ✅ ollama + unsloth | **Terminal Bench 2.1 = 73.0**、**SWE-bench Pro 61.7**、SWE-MM 38.6、IFBench 79.5、GPQA 89.2 | ✅ **V100-PCIe-32GB 上 llama-bench 实测 33.41 / 27.95 @32k / 15.84 @131k**；另有 2×V100 tensor-split 实测 57.4 tok/s（Q8_0 + MTP3） | ❌ 同上，墙钟不划算；且有 "thinking 永不收敛" 实证 |
| Qwen3.8-Flash-Next | Alibaba | MoE 125B / ~6B 激活，512 专家（10 激活 + 1 共享），48 层 | ~111 GB（UD-Q4_K_XL）｜**105 GB**（ollama） | 262,144 | ✅ | （未在本轮取到官方对比表） | ✅ 4×V100-32GB（NVLink）实测：短提示 **95.0** tok/s、16K 88.2、200K 66.4（专家全驻显存，每卡 24.9 GB）；1×V100+Strata 引擎（Q4_K_M 119 GB，专家走主机内存）**43.5–46.1 tok/s** | ❌ **64 GB 显存装不下**；CPU 卸载后 43–46 tok/s，不到现役一半 |
| Qwen3-Coder-30B-A3B-Instruct | Alibaba | MoE 30.5B / 3.3B 激活，128 专家（8 激活） | 18.5 GB（现役） | 262,144 | ✅ | SWE-bench Verified **51.6**（OpenHands 500 轮）、**Terminal-Bench 31.3**、Aider-Polyglot 33.3、SWE-bench Multilingual 34.7、BFCL-v3 62.2 | ✅ 我们实测 135.7 tok/s；DmNep 同卡 Q4_K_M 实测 110–133 | **现役基线** |
| Qwen3.6-27B-coding / qwen3.6:27b-mtp-q4_K_M | Alibaba | 稠密 27B + 官方 MTP 草稿 | 18–19 GB / 18 GB | 262,144 | ✅ ollama 官方 tag | （本轮未取到独立对比表） | 未找到 V100 实测 | ⚠️ 有 MTP 投机解码版本，理论可 +35% decode（见 §7.2），值得单独测 |
| Qwen3-Next-80B-A3B | Alibaba | MoE 80B / 3B 激活 | 50 GB（ollama `qwen3-next`） | 262,144 | ✅ | （未取到） | 未找到 V100 实测 | ❌ 与 Qwen3-Coder-Next 同架构但非 coder 专用，预期更弱 |

### 3.1 官方分数原始出处（避免转述失真）

- **Qwen3-Coder-Next**（官方模型卡 `benchmarks.png`，我从 `https://qianwen-res.oss-accelerate-overseas.aliyuncs.com/Qwen3-Coder-Next/benchmarks.png` 下载后**直接读图**得到）：
  SWE-Bench Verified **70.6** / DeepSeek-V3.2 70.2 / GLM-4.7 74.2 / MiniMax M2.1 74.8；
  SWE-Bench Multilingual 62.8 / 62.3 / 63.7 / 66.2；
  SWE-Bench Pro 44.3 / 40.9 / 40.6 / 34.6；
  Terminal-Bench 2.0 36.2 / 39.3 / 37.1 / 32.6；Aider 66.2 / 69.9 / 52.1 / 61.0。
- **Qwen3-Coder-30B-A3B-Instruct**（官方模型卡 `qwen3-coder-30a3-main.jpg`，我下载后直接读图）：
  Terminal-Bench **31.3**、SWE-bench Verified **51.6**（OpenHands 500 轮）、SWE-bench Live 20.7、Multilingual 34.7、Multi-SWE-bench mini 19.5、Aider-Polyglot 33.3、Spider2 21.4、WebArena 43.5、BFCL-v3 62.2、TAU-Bench Retail 68.7。
  → **前期结论"Qwen3-Coder-Next 自报 SWE-bench Verified 70.6%"已独立核实为真。**
- **Qwen3.6-35B-A3B**（HF 卡内 HTML 表）：SWE-bench Verified **73.4** / Multilingual 67.2 / Pro 49.5 / **Terminal-Bench 2.0 51.5** / TAU3-Bench 67.2。
- **Qwen3.6-27B**（HF 卡内 HTML 表）：SWE-bench Verified **77.2** / Multilingual 71.3 / Pro 53.5 / **Terminal-Bench 2.0 59.3**。
- **Qwen3.8-27B**（HF 卡内 HTML 表）：**Terminal Bench 2.1 73.0** / SWE-bench Pro 61.7 / SWE-MM 38.6 / IFBench 79.5 / GPQA 89.2。

> ⚠️ **口径警告**：以上三张表用的**脚手架不同**（OpenHands vs SWE-Agent vs Claude Code harness；Terminal-Bench 1.0 vs 2.0 vs 2.1），**不能直接横比**。跨表比较只作"量级判断"，最终必须在我们自己的 af-bench 上跑同一口径。

---

## 4. 重点候选展开分析

### 4.1 Qwen3-Coder-Next（80B-A3B）— 唯一"墙钟不涨、解题率大涨"的候选

**架构（官方模型卡原文）**：80B 总参 / 3B 激活，48 层 = 12 × (3 × (Gated DeltaNet → MoE) + 1 × (Gated Attention → MoE))；
Gated Attention 16 个 Q 头 / 2 个 KV 头 / head_dim 256；Gated DeltaNet 32 个 V 头 / 16 个 QK 头 / head_dim 128；
MoE 512 专家、每 token 激活 10 个 + 1 个共享专家、专家中间维 512；上下文 262,144 原生；**只支持 non-thinking 模式**。

**显存账（我们 2×32GB = 64 GB）**：
- 权重：unsloth `Qwen3-Coder-Next-Q4_K_M.gguf` = **48.53 GB**（单文件，HF API `siblings` 带 size 实测）；ollama 官方 `qwen3-coder-next:q4_K_M` 标称 **52 GB**；更小的档位：UD-IQ4_XS 42.68 / IQ4_XS 38.43 / UD-Q4_K_S 45.53 / Q3_K_M 38.32 GB。
- KV：只有 12 层是全注意力 → f16 KV = 12 层 × 2(K,V) × 2 KV 头 × 256 × 2 B = **24,576 B/token（24 KiB/token）**。
  - 8K ctx → 192 MiB；**32K → 768 MiB**；64K → 1536 MiB；128K → 3072 MiB；256K → 6144 MiB（**总量**，layer 切分时每卡减半）。
- **按 GiB 算账（我们的卡是 32 GiB = 32768 MiB）**：
  - unsloth Q4_K_M 48.53 **GB**（十进制）= **45.2 GiB** → layer 切分后每卡 **22.6 GiB 权重**。
    - num_ctx 32768：22.6 + 0.375(KV 半份) + ~1.5~2.0(计算缓冲) + ~0.5(CUDA context) ≈ **25.0~25.5 GiB/卡** → 余量 ~6.5 GiB ✅
    - num_ctx 262144：22.6 + 3.0 + 2.0 + 0.5 ≈ **28.1 GiB/卡** → 余量 ~3.9 GiB，**仍放得下但偏紧** ⚠️
  - ollama 官方 q4_K_M 标称 52 GB = 48.4 GiB → 每卡 24.2 GiB 权重；num_ctx 262144 时 ≈ **29.7 GiB/卡** → 余量仅 ~2.3 GiB，**不推荐 256K**。
  - ⇒ **结论：2×V100S-32GB 装得下 Qwen3-Coder-Next，ctx 建议 32768（余量最大），最多到 131072。**

**速度预期（推断，无直接证据）**：
- 解码受**激活参数**约束：现役 3.3B 激活 → 135.7 tok/s；Coder-Next 3B 激活，激活权重字节数相近 → **理论同档**。
- **但它有 512 路专家 vs 现役 128 路**，每 token 要发起 48 × 11 = **528 次极小的专家矩阵乘**（现役 48 × 9 = 432 次）。llama.cpp 的 MoE 路径在 V100 上本就只有理论带宽的 ~25% 效率（30B-A3B Q4_K_M：活跃权重 ~1.8 GB / 900 GB/s ≈ 500 tok/s 理论，实测 110–135），散点读与小核发射的固定开销占比很高。**专家路数翻 4 倍 ⇒ 我预计 90–130 tok/s，不会超过现役的 135.7。**
- 参考：Qwen3.6-35B-A3B 是 256 专家，实测 98.8 tok/s（V100-SXM2）→ 搬到 V100S-PCIe 约 89 tok/s。512 专家的 Coder-Next 落在同一区间是合理预期。

**风险（按严重度）**：
1. **无任何 V100 实测**。本轮未找到 Qwen3-Coder-Next 在 V100/V100S 上的 tok/s 公开数据。
2. **上游 llama.cpp 在多卡 Volta + 混合 qwen3_5 系架构上有未修复缺陷**：ggml-org/llama.cpp **#27366**（2026-08-19 开，2026-10-03 **以 stale 关闭，等于没修**）——`-sm tensor` 在多卡 Volta 上 `llama-cli` **永久挂死并持有显存**、`llama-bench` 跑完断言；`-sm row` 在 CUDA 上直接不支持（`device CUDA1 does not support split buffers`）；**`-sm layer` 正常**。
   → 我们的应对：**只用 layer 切分**（ollama 默认就是 layer 切分，见 §8）。
3. **V100 FA 崩溃面**：ggml-org/llama.cpp **#28661（仍 open，2026-09-09）**——SM70 上 CUDA FlashAttention 对**非标准 head_dim** 会崩（`fattn-mma-f16.cuh:1945` CUDA error: invalid argument）。Coder-Next 的 head_dim 是 256，属于该 issue 提议的**白名单 {64,128,256}**，理论上安全；但 Qwen3.8-27B（head_dim 256 同理）已有人踩过别的 Volta FA 坑（#28640）。**上线前必须先做 FA 开关的 A/B 冒烟。**
4. **qwen3_5 混合线性注意力在 llama.cpp 上很新**：已有先例——双 V100 实验室为了让 V100 上的 Gated DeltaNet 更快，专门 forward-port 了 **row-per-warp CUDA GATED_DELTA_NET** 内核（+4.24%），并需要把上游 **chain MTP 拒掉**（在 V100 上 `n-max=1` 只有 38.55 tok/s，低于对照 42.74）。
   → 我们 ollama 0.40.6 里 **qwen3_next 已被支持**（我在 anolis 上对 `libllama.so` 做了 strings 核验：存在 `src/models/qwen3next.cpp`、`llama_model_qwen3next` 图类、以及 ollama 兼容层 `"%s: detected qwen3next GGUF with ssm_dt tensors; applying compatibility fixes"`）——但**存在 ≠ 在 V100 上正确**，必须冒烟。

### 4.2 Qwen3.6-35B-A3B（35B-A3B）— 分数更高，但被 thinking 拖累

- **有直接 V100 实测**：**98.8 tok/s**（V100-SXM2-32GB，Q4_K_M ~22 GB，thinking ON，ctx 16384，llama.cpp 自编 sm_70）。搬到 V100S-PCIe（-10%）→ **约 89 tok/s**。
- 官方分：SWE-bench Verified 73.4 / Terminal-Bench 2.0 51.5 —— **Terminal-Bench 上比 Qwen3-Coder-Next 高 15.3 分**（这正是我们 harness 的题型）。
- **致命点（V100 上的实证，不是推测）**：miyagadget 2026-09-04 在 V100-PCIE 上实测 Qwen3.8 系列的 thinking 行为：
  - `--reasoning-effort none` → chat template 直接抛异常（只支持 xhigh/medium/low，**xhigh 是默认**）；
  - low / medium / xhigh **三档墙钟完全一样（134–135 s）**，全都"烧满 4096 token 思考预算、从未给出答案"；
  - 修复是 `--reasoning-budget 1024`（134 s → 39 s）；`--reasoning-budget 0` 行为等同无限（别用）；`-rea off` 反而更慢（78 s，因为答案更长）。
  - 且 Qwen3.6-27B 有**同款缺陷**（数字符数直到超预算）。
- 我们的前提结论说 Qwen3.8 系列默认 reasoning_effort=xhigh、token 消耗约同代 2 倍 —— **已在 V100 上被独立复现**。
- **裁定**：分数上它是最强的"能装进单卡 32 GB 的 MoE"，但 thinking 膨胀 + 可能的"永不收敛"，在 10 轮工具调用的 agent 场景里墙钟不可控。**可作为第二轮候选单独打榜，不作为首发替换。**

### 4.3 Qwen3.6-27B / Qwen3.8-27B（稠密 27B）— 分数天花板，但墙钟 4–8×

- 官方分最高：Qwen3.6-27B SWE-bench Verified **77.2**、Terminal-Bench 2.0 **59.3**；Qwen3.8-27B Terminal Bench 2.1 **73.0**、SWE-bench Pro **61.7**。
- 代价：**V100 上 30–33 tok/s**（三处独立直接实测），是现役的 **1/4.1**；再叠加 thinking 膨胀 ~2× → **实际墙钟 ~8×**。
- 显存反而友好：18 GB（ollama `qwen3.8`）单卡就够，还能留出 ~13 GB 给 KV。
- **裁定**：如果产线目标从"跑得快"改成"解得多、且不介意等 4–8 倍"，Qwen3.6-27B 是分数上的最优解；但按我们"不烧 API 额度的量产臂"定位，**不可用**。
  （附带正面信息：Qwen3.6-27B 与 Qwen3.8-27B 在**双卡 tensor-split** 下有实测提速路径——2×V100 上 Qwen3.8-27B Q8_0 + MTP3 达 **57.4 tok/s**；6×V100-16GB 上 DFlash2 达 218–226 tok/s。**但这是 4–6 卡 + NVLink/SXM2 的结果，迁到我们 2×无 NVLink 的 V100S 要打折，且 §7.1 的 #27366 缺陷就在这条路上。**）

### 4.4 稠密 14B 档（Qwen3 14B / Qwen2.5-14B）— 墙钟友好但分数不够

- V100 上 ~50–68 tok/s（direct databasemart 48.6–67.5；A6000 Q4_K 53.8 → V100 推算 ~63）。**比现役慢 2–2.7×**，不是"更低的单题墙钟"。
- 分数明显低于 30B-A3B 家族。**不满足"更值得上"**。
- 唯一用途：如果某个 harness 子集（如 InjecAgent 工具调用）用 14B 就够，用它换显存/并发。

### 4.5 Qwen3.8-Flash-Next（125B-A6B）— 装不下，且 CPU 卸载代价巨大

- 权重 105 GB（ollama）/ 111 GB（UD-Q4_K_XL）→ **64 GB 显存差 41–47 GB**。
- 即使用 `--n-cpu-moe` 把专家放主机内存：1×V100 上实测 **43.5–46.1 tok/s**（Strata 引擎，Q4_K_M 119 GB，55 GiB 专家常驻内存预算，KV int8，MTP spec 4，ctx 262144）。**不到现役的一半。**
- 4×V100-32GB（NVLink 全互联）专家全驻显存时：短提示 **95.0** tok/s、200K 提示 66.4 tok/s —— 依然不如我们 2 卡的 135.7。
- **裁定：出局。**（唯一理由保留：它是 4 卡+ 的模型，与我们的 2 卡 64 GB 不是一个量级的资产。）

---

## 5. 待验证核心假设的裁定

> 假设原文：「总参很大但激活参数很少的 MoE（80B-A3B）可能同时做到比现役更强、比稠密 27B 更快，因为解码受显存带宽约束、每 token 只需读取被激活的那部分权重；反之稠密 27B 在 V100 上解码会慢 3-4 倍。」

| 子命题 | 裁定 | 直接证据 |
|---|---|---|
| A. 稠密 27B 在 V100 上比 MoE 30B-A3B 慢 3–4× | ✅ **成立** | 27B 稠密 30.57–33.41 tok/s（3 处独立实测）vs 30B-A3B MoE 106–135.7 tok/s → **3.2–4.4×**。且 Qwen3.6-35B-A3B 98.8 vs Qwen3.6-27B 32.9 = **3.0×**（同模型家族同卡同天的对照，最干净） |
| B. 解码受"激活参数"而非"总参数"约束 | ✅ **成立** | Qwen3.6 家族同日同卡：35B/3B 激活 → 98.8 tok/s；27B 稠密 → 32.9 tok/s。DmNep 同卡：30B-A3B(3B 激活) 110–133 vs Gemma4-31B 稠密 29.9 |
| C. 「80B-A3B 比现役 30B-A3B 更快」 | ❌ **不成立** | 两者激活参数都是 3B ⇒ 每 token 读到的权重字节数同量级 ⇒ 理论同速；Coder-Next 另有 **512 路专家**的散点读劣势（vs 现役 128 路），**预期持平或略慢**。⚠️ **C 命题无直接证据**（无任何 Coder-Next 的 V100 实测），本裁定基于 A/B 的机制推断 + 同架构家族的专家路数对照（256 专家的 Qwen3.6-35B-A3B = 98.8 < 128 专家的 Qwen3-30B-A3B = 110–135） |
| D. 「80B-A3B 的 Q4 权重约 45 GB，双卡 64 GB 能否放下」 | ✅ **能放下** | 实测 unsloth Q4_K_M = **48.53 GB 十进制 = 45.2 GiB**（HF API 逐文件 size 求和，非估值），ollama 官方 Q4_K_M 标称 52 GB = 48.4 GiB。layer 切分后每卡 22.6 GiB 权重 + 32K ctx 的 KV（768 MiB 总量 / 384 MiB 每卡）+ 计算缓冲 ~2 GiB ≈ **25.0~25.5 GiB/卡 < 32 GiB** ✅。**注意这不是"磁盘装不下"的问题**（运营者已明确可扩容），而是**64 GB 总显存的分配问题** |
| E. 「放不下时用 `--n-cpu-moe` CPU 专家卸载在 V100 上可行吗、代价多大」 | ❌ **不可行** | 直接实测（同一台 V100 32GB，llama.cpp）：Qwen3-235B-A22B IQ4_XS 全部专家走 CPU（`-cmoe`）→ decode **2.13–3.48 tok/s**；静态 `--n-cpu-moe 88/82/76` → **2.43–4.18 tok/s**。Nemotron 512 专家 `--n-cpu-moe 68` → **10.6–10.7 tok/s**。Qwen3-Coder-30B-A3B **仅 8 层专家走 CPU** → **35.7 tok/s**（vs 同卡全 GPU 的 110 tok/s，**掉 68%**）。<br>**规律：CPU 专家卸载的损失大于按字节的线性损失**，因为 V100 走 PCIe（我们无 NVLink），且 llama.cpp 的 CPU MoE 路径效率极低。**任何需要 CPU 卸载的方案对我们都是降级方案，不能作为主链路** |

**→ 假设的整体结论**：Coder-Next 会**更强**（SWE-bench 51.6→70.6）、**不比现役慢**（激活参数相同），但也**不会更快**。所以"更值得上"的答案是**肯定的**，只是收益来自**解题率**而不是**吞吐**。

---

## 6. 直接证据 vs 推断（分栏）

### 6.1 直接证据（本轮读到/核验过的原始输出）

| # | 结论 | 证据形态 | 出处 |
|---|---|---|---|
| E1 | V100 32GB 上 Q4_K_M 稠密 27B = 30.6–33.4 tok/s decode | llama-bench 输出表 | miyagadget 2026-07-15 / 2026-09-04；dual-v100-llama.cpp 单卡报告 |
| E2 | 同卡 Q4_K_M MoE 30B-A3B = 110–133 tok/s；我们实测 135.7 | 原始 JSON + README 表 | DmNep/llm-bench-v100；我们 anolis 实测 |
| E3 | 同模型家族同卡同日：Qwen3.6-35B-A3B 98.8 vs Qwen3.6-27B 32.9 | 4 任务 × 3 模型均值表 | miyagadget 2026-07-15 |
| E4 | Qwen3-Coder-Next Q4_K_M = 48.53 GB | HF API `siblings[].size` 逐文件求和 | huggingface.co/api/models/unsloth/Qwen3-Coder-Next-GGUF?blobs=true |
| E5 | Qwen3-Coder-Next 官方 SWE-bench Verified 70.6 / TB2.0 36.2 | 官方模型卡图（我读图抄录） | qianwen-res…/Qwen3-Coder-Next/benchmarks.png |
| E6 | 现役 30B-A3B 官方 SWE-bench Verified 51.6 / TB 31.3 | 官方模型卡图（我读图抄录） | qianwen-res…/Qwen3-Coder/qwen3-coder-30a3-main.jpg |
| E7 | V100 上 KV 量化（-ctk/-ctv q8_0）会**静默退回 CPU**、GPU 利用率 0%、10 分钟跑不完 | 指标对照表（GPU util 97–100% vs 0%，功耗 250 W vs 36 W） | miyagadget 2026-09-04 |
| E8 | V100 上 `-fa` 开关无差别（Volta 无 FA2，但 flag 静默通过不报错） | llama-bench A/B（818.70/33.30 vs 821.02/33.44） | 同上 |
| E9 | V100 上 thinking 永不收敛，`--reasoning-budget 1024` 是解药 | 墙钟/正确性表 | 同上 |
| E10 | `--n-cpu-moe` 在 V100 上的实测代价 | 多表（-cmoe / n-cpu-moe 88/82/76 / Nemotron 68） | DmNep/llm-bench-v100 RESULTS-qwen3-235b / RESULTS-moe-cache-fix |
| E11 | 单卡 V100 27B 内存占用：64K 提示 25,143 MiB；255K 提示 25,145 MiB | 峰值显存列 | dual-v100-llama.cpp 单卡报告 |
| E12 | 多卡 Volta + 混合 qwen3.5 架构：`-sm tensor` 挂死、显存泄漏；`-sm row` CUDA 不支持；`-sm layer` 正常 | issue 正文含复现命令 | ggml-org/llama.cpp #27366（2026-08-19 开，2026-10-03 **stale 关闭=未修**） |
| E13 | SM70 上 CUDA FA 对非标准 head_dim 崩溃 | issue 正文 | ggml-org/llama.cpp #28661（**仍 open**） |
| E14 | 我们 ollama 0.40.6 内含 qwen3next 支持 | `strings libllama.so` 命中 `src/models/qwen3next.cpp` / `llama_model_qwen3next` / `qwen3next` 兼容层字符串 | 我在 anolis 上实跑 |
| E15 | **我们现役模型整模型只落在 1 张 V100S 上** | ollama 日志 `load_tensors: offloaded 49/49 layers to GPU` + `llama_kv_cache: size = 1536.00 MiB (8192 cells, 48 layers, 2/2 seqs)` | `/data/models/ollama-serve.log`（我实查） |
| E16 | ollama 的多卡策略：单卡装得下就整卡放（减少 PCIe 传输），装不下才 spread 到所有卡 | 官方 FAQ 原文 | docs.ollama.com/faq |
| E17 | Qwen3.6-35B-A3B 官方 73.4 / TB2.0 51.5；Qwen3.6-27B 官方 77.2 / TB2.0 59.3 | HF 模型卡内 HTML 表 | huggingface.co/Qwen/Qwen3.6-35B-A3B、/Qwen3.6-27B |
| E18 | Qwen3.8-27B 官方 TB2.1 73.0 / SWE-bench Pro 61.7 | 同上 | huggingface.co/Qwen/Qwen3.8-27B |
| E19 | V100 32GB 上 7B Q4_0 = 129.08（无 FA）/ 134.76（FA）tok/s，prefill 3042.6 | llama-bench 榜单原始行 | knightli.com（2026-04-23） |
| E20 | Qwen3-Coder-30B-A3B 官方 30.5B 总参 / 3.3B 激活 / 128 专家 / 8 激活 / 48 层 | 模型卡正文 | huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct |

### 6.2 推断（本报告的判断，非实测）

| # | 推断 | 依据 | 置信度 |
|---|---|---|---|
| I1 | Qwen3-Coder-Next 在 2×V100S 上 decode ≈ 90–130 tok/s（不会超过现役 135.7） | 激活参数相同（3B）+ 专家路数 512 vs 128 的散点读劣势；同族 256 专家的 35B-A3B 实测 98.8 | 中 |
| I2 | 2×V100S 用 `--split-mode layer` 跑 Coder-Next，decode ≈ 单卡水平（容量翻倍、速度不翻倍） | layer 切分串行；且 §7.1 的 #27366 明确 `-sm layer` 才是"正常"的那个 | 中高 |
| I3 | ollama 跑 Coder-Next 时会自动 spread 到两张卡 | E16（FAQ 明文）+ 52 GB > 32 GB 单卡 | 高 |
| I4 | Qwen3.6-35B-A3B 搬到 V100S-PCIe ≈ 89 tok/s | 98.8 × (1380/1530) ≈ 89（miyagadget 自己给的 PCIe 修正 ~10%） | 中高 |
| I5 | "两卡各跑一个独立 ollama 实例" 比 "单卡 OLLAMA_NUM_PARALLEL=2" 聚合吞吐高约 20–25% | 我们自己的数据：单请求 135.7；同卡并发 2 → 每路 109.7、合计 219。拆成两卡各 135.7 → 合计 271 | 中高（基于我们自己的实测外推，未实测双实例） |
| I6 | Coder-Next 在 2×V100S 上 num_ctx 建议 32768（余量 ~6.5 GiB/卡），131072 尚可（余量 ~4 GiB/卡），262144 偏紧（余量 ~2–4 GiB/卡，取决于用 unsloth 45.2 GiB 还是 ollama 48.4 GiB 权重） | 显存账（§4.1，GiB 口径） | 高 |

---

## 7. 反面证据与 V100/Volta 专项风险清单

### 7.1 多卡 Volta 的上游缺陷（**本轮最重要的风险发现**）

- **#27366**（ggml-org/llama.cpp，2026-08-19 开 / 2026-10-03 **以 stale 关闭——等于没修**）：
  - 机型：3× Tesla V100-SXM2-32GB（CC 7.0），GPU1↔GPU2 NVLink、GPU0 走 PCIe
  - 模型：`bartowski/Qwen3.8-27B-GGUF` Q4_K_M（arch `qwen35`，65 blocks，17 attention + 48 SSM 层）← **与我们的 Coder-Next 同属"混合线性注意力 + MoE"家族**
  - `-sm row` → 加载即报 `device CUDA1 does not support split buffers`（CUDA 不支持 row split，CLI help 仍宣称支持）
  - `-sm tensor` → `llama-bench` 跑完断言 `GGML_ASSERT(meta_buf_ctx->bufs[i]) failed`；**`llama-cli` 无输出、无报错、永久挂死并持有 VRAM**
  - `-sm layer` → **works correctly**
  → **我们的硬约束：只走 layer 切分**（ollama 默认就是），不要在 anolis 上手搓 tensor split。
- **#28661**（**仍 open**，2026-09-09）：SM70 上 CUDA FA 对非标准 head_dim 崩溃（`CUDA error: invalid argument ... fattn-mma-f16.cuh:1945`）。提议的修复是白名单 {64,128,256}；Coder-Next head_dim=256 在白名单内，但**必须实测**。
- **#26119**（已闭 2026-08-04）：V100 + 投机解码 + 视觉负载下 `cublasSgemm_v2 unsupported parameter` 导致服务端 abort（约 5.5K token 后）。
- **#25835**（已闭）：V100 上开 CUDA Graphs 显存泄漏。
- **#28416**（已闭 2026-09-04）：sm_70 + CUDA 12.9.x 构建在空 32GB 卡上 weight-buffer 分配失败 —— **我们用 CUDA 12.6，躲开了这一条**。
- **#19959**（已闭 2026-02-27）：V100 上 cuBLAS 需用 fp32 避免溢出（env 可覆盖）。
- **#20605**（已闭 2026-03-15）：禁用 PP graph 复用会导致 V100 decode **回退 16%**。
- 另：**V100 无 FP8/BF16/FP4**；**KV 量化在 V100 上静默退回 CPU**（E7）；**`-fa` 是哑开关**（E8）；预编译的 llama.cpp 官方二进制**已经不支持 Volta**，必须自己带 `-DCMAKE_CUDA_ARCHITECTURES=70` 编（miyagadget 明确指出这个 2026 年的坑）。

### 7.2 投机解码在 V100 上的收益（可用但有条件）

来自 dual-v100-llama.cpp 单卡报告（Qwen3.8-27B Q4_K_M，V100-**PCIe**-32GB）：

| MTP draft 长度 | 短上下文 decode |
|---|---|
| 0（关） | 30.570 tok/s |
| **1** | **41.926** |
| 2 | 40.380 |
| 3 | 38.860 |
| 4 | 34.480 |
| 5 | 30.269 |

- Q4/MTP1 相对 Q4/无投机解码 = **+34.96%**。
- KV 档位：Q8_0 41.926 / **Q4_0 42.711**（吞吐与显存最佳，但改变生成轨迹）/ **Q5_0 35.285（SM70 上量化核不划算，别用）**。
- 64,810 token 提示：decode 21.847（Q4 KV）、prefill 471.947、峰值显存 25,143 MiB。
- 255,000 token 提示：decode 12.617、prefill 224.352、峰值 25,145 MiB。
- **上游 chain MTP 在 V100 上反而更慢**（n-max=1 → 38.55，n-max=3 → 33.48，n-max=4 → 30.12），所以只值得用**单步 MTP**。
- ollama 侧：`qwen3.6:27b-mtp-q4_K_M`（18GB）这类**官方带 MTP 草稿的 tag** 存在，是把这条收益吃到手的最短路径（但 ollama 是否启用 MTP 需实测）。

### 7.3 其他风险

- **Volta 时代的 tensor 核只有 fp16/无 bf16**：mmproj 必须用 **F16**（用 BF16 版会出问题，miyagadget 明确点名）。Coder-Next 无视觉，不涉及。
- **显存 NUMA 陷阱**（llama.cpp-v100 文档）：在把显存并入系统内存的机器（如 IBM AC922）上，读模型产生的页缓存可能落进 GPU 显存节点且 CUDA 回收不了 → 表现为"显存不足"；x86 不需要 `numactl`。**我们的 anolis 是普通 x86 + PCIe，风险低**，但 `nvidia-smi` 要持续盯。
- **散热**：V100-PCIe 250 W 峰值实测 269.2 W / 65 °C（无明显降频）；我们的 2 卡机箱散热要复核。

---

## 8. 对我们的具体建议

### 8.1 先做"零风险立刻收益"：把闲置的第二张 V100S 用起来（**建议本周就做**）

**证据链**：现役模型 18.5 GB 单卡装得下 → ollama 按 FAQ 规则"整模型放一张卡" → 我们自己的日志 `load_tensors: offloaded 49/49 layers to GPU` + `llama_kv_cache: size = 1536.00 MiB (8192 cells, ...)` 证实 **num_ctx 8192 下只用了 1 张卡**。

**做法**：
1. 停掉当前单例 ollama（`~/.local/bin/ollama-restart.sh` 已是裸进程托管，重启前先 `pkill af-bench` 确认没有判分容器在用），改成**两个实例**：
   - 实例 A：`CUDA_VISIBLE_DEVICES=0`，端口 11434，`OLLAMA_NUM_PARALLEL=1`
   - 实例 B：`CUDA_VISIBLE_DEVICES=1`，端口 11435（我们已有一条 11435 隧道的历史），`OLLAMA_NUM_PARALLEL=1`
   - 两者都保留 `OLLAMA_FLASH_ATTENTION=1`（V100 上 FA 哑开关，但可省 KV 显存）、`OLLAMA_KV_CACHE_TYPE=f16`（**不要设 q8_0 —— V100 上会静默退回 CPU，E7**）
2. af-bench 侧把"本地臂"从"一个 endpoint 内部并发 2"改成"**两个 endpoint 各跑一路**"。
3. **预期收益（基于我们自己的实测外推）**：单路 135.7 tok/s；现在同卡并发 2 → 每路 109.7、合计 219；改双实例后 → **每路 135.7、合计 ~271（+24% 聚合吞吐）**，且**每题墙钟不变**（甚至因不再互相抢 KV 而略降）。
4. **必须先做的验证**：双实例下各跑一遍 af-bench 的同一题，核对 tool calling 正常、显存不互踩（每卡 18.5+1.5+计算缓冲 ≈ 22 GB / 32 GB，余量充足）。

### 8.2 主线候选：Qwen3-Coder-Next（80B-A3B）— 建议进第二轮实测，**先冒烟再谈换装**

**装法（推荐用 unsloth GGUF 自行起 llama-server，而不是 ollama 的 52 GB tag）**：
- 权重：`unsloth/Qwen3-Coder-Next-GGUF` 的 `Qwen3-Coder-Next-Q4_K_M.gguf`（48.53 GB）。**比 ollama 的 52 GB 少 3.5 GB，能多留 1.75 GB/卡的余量。**
  磁盘：运营者已明确可扩容（/data 剩 18G，docker 可回收 135G）→ 48.5 GB 需要先腾空间（这一步是**磁盘**问题，不是显存问题，不构成淘汰理由）。
- 引擎：我们**目前没有独立 llama-server**。两条路：
  - **路线 A（低风险，先做）**：用 ollama 0.40.6（已验证内含 qwen3_next 支持，E14）。
    - `ollama pull qwen3-coder-next:q4_K_M`（52 GB），用 Modelfile 覆盖 `PARAMETER num_ctx 32768`。
    - ollama 会自动 spread 到两张卡（E16 + I3），layer 切分（官方 FAQ 口径），**避开 #27366 的 tensor-split 雷区**。
    - **必须先核对** ollama 是否真把模型摊到两张卡（`ollama ps` 看 per-GPU 占用 / `nvidia-smi` 看两张卡都有显存），若只落一张必然 OOM。
  - **路线 B（要 MTP/投机解码与 split-mode 控制时才上）**：自编 llama.cpp（`-DCMAKE_CUDA_ARCHITECTURES=70`，CUDA 12.x），或用 **llama.cpp-v100**（`1115714829/llama.cpp-v100`，上游 v0.6.0 / d81235049，2026-10-05 之后，GPL-3.0，发布镜像 `ghcr.io/1115714829/llama.cpp-v100:2.0.1`）。
    - ⚠️ 镜像在 **ghcr.io**，anolis 上 docker.io 不通但 ghcr.io 通不通**未验证**；若不通就用源码编（`cmake -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=70 -DGGML_CUDA_NCCL=ON`，NCCL 是 tensor parallel 才需要，**我们只用 layer 切分可以先不带**）。
- **配置（V100 专项，照抄已验证的别人的结论）**：
  - `num_ctx`：**32768 起**（af-bench 每题 10 轮工具调用，实测 token 量级远低于 300K；不需要 262K）。KV 只需 768 MiB 总量。
  - **不要 KV 量化**（`-ctk/-ctv q8_0` 在 V100 静默退 CPU，E7）；若要省显存，V100 上只有 f16 可用。
  - `-fa` 无所谓（E8）；但**必须做 FA on/off 的输出一致性冒烟**（#28661）。
  - **不要开 thinking**（Coder-Next 本来就只支持 non-thinking，天然规避 Qwen3.8 系的"思考烧满预算"陷阱）。
  - 采样：`temperature=1.0, top_p=0.95, top_k=40`（官方模型卡 Best Practices）。
- **必须先做的冒烟（按顺序，每步都有退出条件）**：
  1. **加载冒烟**：能加载、49/48 层全 offload、输出不乱码（前期结论里提到的 llama.cpp 老卡乱码 issue #17067 —— 实际该 issue 是 "Qwen3-Coder-30B-A3B Q4_K_M 在 `-dev none` 下输出乱码"，且**已于 2026-01-20 关闭**；但我们仍要自己验一遍输出可读性）。
  2. **速度冒烟**：单请求 decode 期望落在 **90–130 tok/s**（I1）。**若明显低于 80，说明 512 专家的散点读在 V100 上比预期更糟 → 直接否掉**。
  3. **多卡冒烟**：两张卡都有显存占用；连续跑 3 个不同提示，确认不挂死（#27366 的 `llama-cli` 挂死症状）。
  4. **工具调用冒烟**：用我们 harness 的真实 tool schema 跑一轮，确认 `<function=...>` 格式被正确解析、跨轮不崩。
  5. **长提示冒烟**：灌一段 30–60K 的真实代码/日志，确认 prefill 速率与 KV 占用符合预期（预期 prefill 数百 tok/s 量级）。
- **判定标准（提前定，避免自欺）**：在 af-bench 的同一子集上，**解题率相对现役提升 ≥ 15 个百分点**、且**单题墙钟 ≤ 现役的 1.3×**，才替换现役；否则留作"高分档"备用（API 不稳时手动切）。

### 8.3 第二轮候选：Qwen3.6-35B-A3B（35B-A3B）— 分数最高、必须控 thinking

- 装法最省事：`ollama pull qwen3.6:35b`（**23–24 GB**，单卡 32 GB 装得下，**不需要双卡**）。
- 已有直接证据：**单卡 V100-SXM2 98.8 tok/s**（V100S-PCIe 约 89），prefill 352 tok/s。
- **必须做的额外控制**：
  - 请求里显式关思考或设 `reasoning_budget`（ollama 侧对应 `think` 参数 / `reasoning_effort`），**别用默认 xhigh**——V100 上已实证三档 effort 全都烧满 4096 token 预算且不给答案。
  - 若走 llama-server 路线，用 `--reasoning-budget 1024`（V100 实测的最优点：134 s → 39 s 且答案正确）。
- 判定标准：与现役**同题同口径**比；若解题率提升 ≥ 20 点且墙钟 ≤ 1.6×，可考虑升为"本地主力"。

### 8.4 明确不做的事（以及为什么）

| 候选 | 不做的原因 |
|---|---|
| Qwen3.6-27B / Qwen3.8-27B（稠密） | 墙钟 4.1×（+thinking 膨胀 ≈ 8×），违反"量产臂"定位；分数虽最高但我们买的是吞吐 |
| Qwen3.8-Flash-Next（125B-A6B） | 105–111 GB 权重，64 GB 显存差 41–47 GB；CPU 卸载后实测 43.5–46.1 tok/s，不到现役一半 |
| GPT-OSS-120B MXFP4 | V100 无 MXFP4（硬件不支持），前期结论已确认，本轮维持 |
| 任何依赖 `--split-mode tensor` 的提速方案 | ggml-org/llama.cpp #27366 在多卡 Volta + 混合架构上**挂死且未修复**；要 tensor parallel 必须上 llama.cpp-v100 fork（GPL-3.0，NVLink 优化针对 SXM2 拓扑），在我们 2×V100S-**无 NVLink** 上收益要打折，**不建议现在投入** |
| 在 V100 上开 KV 量化 | 静默退回 CPU，GPU 利用率 0%（E7） |

### 8.5 与我们前期结论的对照（独立验证结果）

| 前期结论（设计/benchmark调研/实测/model-pricing.md §4.2 等） | 本轮独立验证结果 |
|---|---|
| "本地最强可行选项是 Qwen3-Coder-Next（80B A3B，激活约 3B）Q4 量化双卡 64GB 容纳，自报 SWE-bench Verified 70.6%" | ✅ **成立**。70.6 已从官方模型卡图直接核实；Q4_K_M 48.53 GB 确实塞得进 2×32GB（显存账见 §4.1） |
| "保底选项是 Qwen3-Coder-30B-A3B Q4_K_M 单卡" | ✅ **成立且更精确**：ollama 在 18.5 GB + num_ctx 8192 下**只落 1 张卡**（E15），第二张 V100S 闲置 |
| "GPT-OSS-120B MXFP4 明确不建议（V100 不支持 MXFP4）" | ✅ 维持 |
| "V100 无 BF16、无 FlashAttention；llama.cpp 在老卡上有输出乱码与 GPU 未生效的 issue（#17067），部署必须先冒烟" | ✅ 维持，并细化：#17067 实为 "Qwen3-Coder-30B-A3B Q4_K_M 在 `-dev none`（纯 CPU）下输出乱码"，**2026-11-07 开、2026-01-20 已关闭**；"无 FlashAttention"更准确的说法是"**FA2 不支持，`-fa` 是哑开关**"（E8），且 **V100 上 KV 量化会静默退 CPU**（E7，本轮新发现的更危险的一条） |
| "前期已知的坑：Qwen3.8 架构在 llama.cpp 上很新，有过'速度正常但输出损坏'的 CUDA bug；MTP/DFlash2 投机解码在 --split-mode tensor 下有崩溃 issue" | ⚠️ **部分证伪、部分加强**：(a) "MTP/DFlash2 在 split-mode 下崩溃"——在 **llama.cpp-v100 fork** 上 `--split-mode layer` + DFlash2 启动失败**已被修复**（v1.1.1 起），但**上游 llama.cpp 的 tensor split 在多卡 Volta 上仍然是 #27366 未修的挂死**；(b) "输出损坏"——**未找到** Qwen3.8 系在 V100 上"速度正常但输出损坏"的公开 issue；本轮找到的最接近的是 #28661（FA + 非标准 head_dim 崩溃）与 #17067（已闭） |
| "Qwen3.8 系列默认 reasoning_effort=xhigh，token 消耗是同代模型的约 2 倍" | ✅ **在 V100 上被独立复现并强化**：xhigh/medium/low 三档墙钟完全相同（134–135 s）且全都烧满 4096 预算不给答案；`--reasoning-budget 1024` 是解药 |
| "50-方案里'输入 300K+输出 30K/任务'的画像对 SWE/TB 显著高估（实测低 1-2 个数量级）" | ✅ **与文献一致**：Qwen3.8-27B 在 V100 上 131K 提示时 decode 已掉到 15.84 tok/s（深度 0 的 47%）；MoE 30B-A3B 在 67K 时掉到 63.7（ollama）/32.6（llama.cpp）。深度惩罚是实打实的 |

---

## 9. 本轮"未找到公开证据 / 未验证"的项（明确留白，不得当成已知）

1. **Qwen3-Coder-Next 在 V100 / V100S / P40 / A6000 上的任何 tok/s 实测** —— 未找到。相关地，Qwen3-Coder-Next 在**任何**消费级/数据中心卡上的 llama.cpp 吞吐公开贴，本轮也只找到标题级线索（HF 讨论区有 "Check in here for tok/s and benchmarks for local gguf models"，createdAt 2026-02-04），**正文未取到**。
2. **Reddit r/LocalLLaMA 的正文** —— 本环境对 reddit.com 全站被反爬拦截（search.json / .json / HTML 三种方式均返回反爬页，非 404），**只有标题级线索**：
   - "Qwen3.6-MTP-27B on Tesla V100 @ 55 TPS (llama.cpp) — Any way to push this higher without quality loss?"
   - "Tesla V100 16GB local LLMs, single and dual NVLink benchmarks"
   - "Nvidia Tesla P40 performs amazingly well for llama.cpp GGUF!"
   - "r/LocalLLM: NVidia V100 Thoughts"
   → 这些帖子的**内容未验证**，本报告未引用其任何数字。
3. **localscore.ai 的原始榜单数据** —— 站点为 Next.js 前端渲染，直接取 HTML 得到 0 张表；`/api/results` 返回 Forbidden。仅通过 insiderllm 的**转述**拿到 P40 的 LocalScore 行（LLaMA2-7B Q4_0 PP 833/TG 40.9；Qwen2.5-14B Q4_K_M PP 339/TG 15.7）——**二手转述，标为"社区体感"级证据**。
4. **Titan V / Quadro / Tesla M40 在 7B–32B Q4 档的 llama-bench 原始输出** —— 未找到。仅拿到 GPUDojo 的**估算**（P40 8B Q4 ~40–50 t/s 等），标为估算，非实测。
5. **ollama 0.40.6 跑 qwen3_next 在 V100 上的实际行为**（是否 100% offload、是否 100% 正确、实际 tok/s）—— **本轮未跑**（纪律：不下载模型权重）。只做了二进制元数据核验（E14）。
6. **ollama 是否 spread 到多卡的确切触发条件与 `--split-mode` 等价关系** —— FAQ 只说"装不下就 spread 到所有卡"，**没找到官方说明它用哪种切分**；我按"ollama 历来是 layer 切分"推断（I3），**未实测**。
7. **P40 / A6000 / 3090 上 7B–32B 全档位 llama-bench 原始输出** —— 只有 knightli 榜的 **7B Q4_0** 一行（llama-bench 原始格式），以及 hardware-corner 的 A6000 / 3090 汇总表（非 llama-bench 原始格式，来源不透明）。
8. **hw-corner V100 页正文与表格自相矛盾**：正文说 "Qwen3 30B model … 70,000-token context … 12.32 tokens per second"，而其表里 256K ctx 是 58.64 tok/s。**以表格为准并标注该矛盾**。
9. **DmNep 仓库的 `gemma4-32k` 行不可用**：作者自己标注 ollama 报 2.1 GB 显存却跑出 56–61 tok/s（超过 900 GB/s 带宽下的物理上限 44 tok/s），同文件 llama.cpp 只给 29.9 tok/s / 23.7 GB。**本报告采用 llama.cpp 那一行。**

---

## 10. 证据来源清单

| # | 来源 | 日期 | 形态 | 证据类型 |
|---|---|---|---|---|
| S1 | `https://github.com/DmNep/llm-bench-v100`（README + results/RESULTS.md、RESULTS-llamacpp.md、RESULTS-qwen3-235b-2026-10-14.md、RESULTS-moe-cache-fix-2026-10-13.md、RESULTS-orca-q4km-2026-10-16.md） | 2026-10-05 ~ 10-19 | 单卡 V100 32GB 实测仓库（原始 JSON + markdown 表） | 第三方复现（原始数据） |
| S2 | `https://miyagadget.page/en/blog/2026/09/04/tesla-v100-32gb-qwen38-27b-benchmark-en/` | 2026-09-04 | V100-**PCIe**-32GB 上的 llama-bench 表 + KV/FA/thinking A/B | 第三方复现（作者自测日志） |
| S3 | `https://miyagadget.page/en/blog/2026/07/15/tesla-v100-32gb-qwen36-benchmark-en/` | 2026-07-15 | V100-SXM2 上 27B / 35B-A3B 对照 | 第三方复现 |
| S4 | `https://github.com/123123213weqw/dual-v100-llama.cpp`（README + docs/benchmark-single-v100-2026-08-17.zh-CN.md、benchmark-2026-08-16.zh-CN.md、production-2026-08-29.zh-CN.md） | 2026-08 ~ 10 | 单卡/双卡 V100 A/B 报告（MTP/KV/时钟） | 第三方复现（含原始 .out 文件） |
| S5 | `https://github.com/1115714829/llama.cpp-v100`（README + docs/v100/moe-2.0.0.md、27b.md） | 2026-10-12 发布 2.0.0 | V100 专项 llama.cpp fork，4/6 卡 MoE 与稠密实测 | 第三方复现 |
| S6 | `https://knightli.com/en/2026/04/23/llama-cpp-gpu-benchmark-cuda-rocm-vulkan-scoreboard/` | 2026-04-23 | 9 张卡的 llama-bench 榜单（Llama-2-7B Q4_0） | 第三方复现（原始 CSV 字段） |
| S7 | `https://www.hardware-corner.net/guides/tesla-v100-32gb-for-llm/` 与 `.../gpu-llm-benchmarks/rtx-a6000` | 2026 | V100 / A6000 / 3090 / 5090 上下文-吞吐表 | 第三方复现（来源不透明，标为弱一档） |
| S8 | `https://www.databasemart.com/blog/ollama-gpu-benchmark-v100` | — | V100 上 7B–27B Q4 的 Ollama 吞吐 | 第三方复现（Ollama 0.5.11，较旧） |
| S9 | `https://insiderllm.com/guides/used-tesla-p40-local-ai/` | 2026 | P40 数据（转述 LocalScore.ai） | 社区体感（二手） |
| S10 | `https://github.com/gpudojo.com` → `https://gpudojo.com/articles/tesla-p40-best-budget-gpu` | 2026 | P40 tok/s **估算** | 估算（非实测） |
| S11 | HuggingFace 模型卡与 API：`Qwen/Qwen3-Coder-Next`、`Qwen/Qwen3-Coder-30B-A3B-Instruct`、`Qwen/Qwen3.6-35B-A3B`、`Qwen/Qwen3.6-27B`、`Qwen/Qwen3.8-27B`、`unsloth/Qwen3-Coder-Next-GGUF`、`Qwen/Qwen3.8-Flash-Next` | 2026-01 ~ 2026-10 | 官方分数（模型卡图/HTML 表）+ GGUF 文件逐个 size | **官方自报** |
| S12 | `https://ollama.com/library/qwen3-coder-next`、`/qwen3.6`、`/qwen3.8`、`/qwen3.8-flash-next`、`/qwen3-next` | 2026-10 取 | ollama 官方 tag 体积表 | 官方自报 |
| S13 | `https://github.com/ggml-org/llama.cpp/issues/27366`（-sm tensor 在多卡 Volta 挂死）、`/28661`（SM70 FA + 非标准 head_dim 崩溃）、`/26119`、`/25835`、`/28416`、`/19959`、`/20605`、`/17067` | 2025-11 ~ 2026-10 | 上游 issue 正文含复现命令 | 官方仓库（一手） |
| S14 | `https://docs.ollama.com/faq`（多卡加载策略、OLLAMA_* 环境变量） | 2026-10 取 | 官方文档 | 官方自报 |
| S15 | anolis-gpu-01 实查：`/data/models/ollama-serve.log`（`load_tensors: offloaded 49/49 layers to GPU`、KV 规格）、`~/.local/lib/ollama/libllama.so` 的 `strings`（qwen3next / qwen35 / qwen35moe）、`/api/version`=0.40.6 | 2026-10-21 | 我们自己的机器 | **本机实测（E14/E15）** |

---

## 11. 一页纸速查

```
V100 32GB · Q4_K_M · batch=1 · 短上下文 · decode tok/s
  7–8B   ███████████████  90–135
  13–14B ████████         50–68
  27B    █████            30–33     ← 稠密天花板
  30–32B ████             27–30
  30B-A3B MoE █████████████████  110–136   ← 现役，实测 135.7
  35B-A3B MoE ██████████████    98.8
  27B 稠密 + MTP(2×V100,TP) █████████  57.4

候选按"官方分 × V100 可得速度"排序
  Qwen3.6-27B      77.2 SWE-V / 59.3 TB2.0   33 tok/s   墙钟 4.1×+thinking ≈ 8×   ❌
  Qwen3.6-35B-A3B  73.4 / 51.5                89–99      墙钟 ~1.5×+thinking ≈ 3×   ⚠️ 第二轮
  Qwen3-Coder-Next 70.6 / 36.2                90–130*    墙钟 ≈1.0–1.4× 无 thinking  ✅ 首选
  Qwen3.8-27B      (TB2.1 73.0)              30–33      墙钟 4.1×+thinking          ❌
  Qwen3.8-Flash-Nxt125B                       43–46      装不下                    ❌
  现役 30B-A3B     51.6 / 31.3               135.7      基线                      —
  * 推断值，无 V100 直接实测
```
