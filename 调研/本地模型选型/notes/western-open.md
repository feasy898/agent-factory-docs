# 西方开源权重编码/Agentic 模型调研（欧美系，2025–2026）

- **调研日期**：2026-10-21（所有数字均为当日查询）
- **调研人**：本地模型选型调研子代理（"调研·西方开源编码模型"）
- **基准机器**：anolis-gpu-01，2× Tesla V100S-PCIE-32GB（sm_70），CUDA 12.6，ollama 0.40.6（内置 llama.cpp runner），125GB 内存
- **现役模型**：`qwen3-coder-30b` = Qwen3-Coder-30B-A3B-Instruct-Q4_K_M（18.5GB，MoE 30.5B 总参 / 3B 激活，ctx 262144），实测 decode 135.7 tok/s、prompt 149.1 tok/s（num_ctx 8192）
- **本轮问题**：有没有一个西方/欧美系开放权重模型，能在相近或更低的单题墙钟成本下，比现役 qwen3-coder-30b 解题率更高？

> **网络与取证条件（影响证据等级，必须先读）**
> 本次调研机器是 **pandev-comp（RTX 3070 Laptop 8GB）**，**不是 anolis**，因此本轮**没有在任何 V100S 上跑过任何模型**。所有速度数字分两类：官方/第三方自报（标注来源）、以及我基于配置与实测锚点做的**算术推断**（明确标"推断"）。
> 直连 `huggingface.co` / `raw.githubusercontent.com` / `reddit.com` / `mistral.ai` 在本机被阻断；实际使用的取证通道是 `hf-mirror.com`（HF API 与 raw 文件）、`github.com/.../raw/...`、`cdn.jsdelivr.net`、`artificialanalysis.ai`、`ollama.com`、`nvidia.com`。
> GGUF 体积来自 HF API `tree` 端点（lfs.size），**未下载任何权重**；GGUF 架构字符串通过 HTTP Range 只读前 4–16MB 的 **KV 元数据头**解析得到（不读权重张量数据）。

---

## 〇、一句话结论

**有，而且只有一个真正值得上：Cohere 的 `North-Mini-Code-1.0`（30B 总参 / 3B 激活，Apache 2.0）——它的架构与现役 qwen3-coder-30b 几乎同构（128 专家 / 每 token 激活 8 个 / hidden 2048），推理成本几乎不变，但 agentic 分数接近翻倍（AA Terminal-Bench Hard 31.06% vs 现役 15.15%）。**

同期另有两个值得知道的次优解：JetBrains `Mellum2.1-12B-A2.5B`（8.07GB 官方 GGUF，极快，做"分拣/草稿/重试"档）和 NVIDIA `Nemotron-Cascade-2-30B-A3B`（AA τ²-bench 最高，正对我们 harness 题型，但混合 Mamba 架构的每 token 显存流量估算约为现役 2 倍）。

**最重要的一条反直觉发现**：本轮西方最强的两个编码模型 **Devstral 2 (123B) 与 Devstral Small 2 (24B) 都是稠密模型**，在 V100 上属于"能跑但不能用"；西方真正适合我们池子的是**中小规模 MoE**（North-Mini-Code 30B-A3B / Mellum2.1 12B-A2.5B / Nemotron-Cascade-2 30B-A3B）。

---

## 一、候选清单总表

> 列含义：
> - **参数/激活**：总参 / 每 token 激活参（激活参直接决定 decode 时要读多少权重字节 → 决定 V100 上的 tok/s）
> - **Q4 体积**：官方或社区 GGUF 的实际文件大小（HF API lfs.size）
> - **官方 agentic 分数**：厂商模型卡自报（官方自报口径）
> - **第三方**：Artificial Analysis（AA）独立测得的 Intelligence Index 与 Terminal-Bench
> - **我们的适配判断**：以"2×V100S-32GB + ollama/llama.cpp + af-bench agentic harness"为基准

| 模型 | 厂商 | 稠密/MoE（激活） | Q4 体积 | ctx | GGUF | 官方 agentic 分数 | 第三方（AA，2026-10-21） | 我们的适配判断 |
|---|---|---|---|---|---|---|---|---|
| **North-Mini-Code-1.0** | Cohere | MoE 30B / **3B**（128 专家取 8） | **18.74GB**（Q4_K_M，bartowski）/ 19.20GB（UD-Q4_K_M，unsloth） | 500k（HF）/ 256k（AA） | ✅ 社区（bartowski/unsloth） | SWE-Bench V **80.2% pass@10**（SWE-Agent）、**61.0% pass@1**（mini-SWE-agent）；TB v2 **55.1% pass@10** | II **9.91**；**TB-Hard 31.06%**；TB2.1 **35.58%**；τ² 37.4%；GPQA 75.7%；速度 76 t/s | **★ 首选 A/B 替换现役**。激活量同现役 → 推理成本基本不变；分数近 2× |
| **Mellum2.1-12B-A2.5B-Thinking** | JetBrains | MoE 12B / **2.5B**（64 专家取 8） | **8.07GB**（Q4_K_M，**官方**） | 131072 | ✅ **官方发布** | SWE-Bench V **47.0**；TB2.1 **17.4**；SWE-bench Pro 28.0；BFCL v4 62.3（Pi v0.73.1 harness） | AA 无条目（404） | **★ "快档"主力**。8GB → 显存宽裕、速度应为现役 1.2–1.5×；但能力≈9B 级，不如现役 |
| **Nemotron-Cascade-2-30B-A3B** | NVIDIA | MoE 31.6B / **3B**（Mamba-2+MoE 混合，128 专家取 6） | 18.17GB（IQ4_NL）/ ~20GB（Q4_K_M），bartowski | 1M | ✅ 社区（bartowski/mradermacher） | SWE-V(OpenHands) **50.2**；TB 2.0 **21.1**；**τ²-Bench 58.9**；BFCL v4 52.9 | II **11.67**；**τ² 53.2%**（最高）；TB-Hard 21.2%；TB2.1 20.6%；IFBench 80.4% | **★ 次选**。τ²-bench 正是我们题型之一；但混合 Mamba 每 token 显存流量估算约 2× 现役 → 约 60–80 tok/s；官方注明"不支持 OpenCode" |
| **Nemotron 3.5 Bolt 74B-A9B** | NVIDIA | MoE 74B / **9B**（496 专家取 9，LatentMoE，Mamba-2 混合） | **22.02GB**（IQ2_XXS，**官方 GGUF**） | 262144 | ✅ **官方发布**（+1.00GB LiLiCorr 投机解码 drafter） | **Terminal-Bench 2.1 50.98**；MCP-Atlas 52.2；BrowseComp 66.75；PinchBench 87.8 | II **21.41（本轮全部候选最高）**；HLE 24.7%；AA-LCR 69.7%；SciCode 39.7% | **不做量产臂**。2-bit IQ2_XXS + 88 层 + 496 专家 + sm_70 无张量核 → 速度风险最大；要用 DFlash 投机解码必须自编 llama.cpp |
| Nemotron-3-Nano-30B-A3B | NVIDIA | MoE 30B / 3.5B（Mamba-2+MoE 混合，128 专家取 6） | 22.42GB（Q4_K_M，ggml-org） | 262144（可到 1M） | ✅ ggml-org/unsloth | SWE-Bench(OpenHands) 38.8；TB hard 8.5；τ² 49.0；BFCL v4 53.8 | AA 无条目 | 备选（同架构但 agentic 明显弱于 Cascade-2） |
| **Devstral 2 (123B)** | Mistral | **稠密 125B**（88 层，无任何 expert 张量） | Q4 **不存在**；Q2_K 46.59GB（unsloth） | 262144 | ✅ 社区 | SWE-V 72.2%；SWE-Multi 61.3%；TB2 32.6% | II 8.62；TB2.1 30.3% | **淘汰（速度）**。46.6GB/ token → 约 5 tok/s，10 轮 agentic 单题不可接受 |
| **Devstral Small 2 (24B)** | Mistral | **稠密 24B** | 14.33GB（Q4_K_M，unsloth）；ollama 官方 tag 14GB | 262144 | ✅ **ollama 官方** | SWE-V 68.0%；SWE-Multi 55.7%；TB2 22.5% | II 7.54；TB2.1 29.6% | **淘汰（速度）**。14.3GB/token → 约 17 tok/s |
| Devstral Small 1.1 / 2505 / 2507 | Mistral | 稠密 24B | ollama 有 24b-small-2505-q4_K_M | 262144 | ✅ 官方 | 更弱 | — | 淘汰（比 Small 2 老） |
| **Devstral Medium** | Mistral | — | — | 256k | **❌ 无开放权重** | — | II 9.01（估算）、openness 11.1、availability 2 | **淘汰**：AA 模型页**无 "Model weights" 字段**；`mistralai` HF 账号下无此模型 → 属 API-only，不属本地候选 |
| **Granite 4.2 30B** | IBM | **稠密 30B**（64 层，hidden 4096，MLP 32768） | 17.72GB（Q4_K_M，**官方**）/ 20.78GB Q5_K_M | 128k（可扩 512k） | ✅ **官方** | — | II **12.68**；TB2.1 26.6%；GPQA 64.4%；AA-LCR 49%；速度 41 t/s | **淘汰（速度）**。17.7GB/token → 约 14 tok/s |
| Granite 4.1 30B / 4.2 8B / 4.2 3B | IBM | 稠密 | 官方 GGUF 有 | 128k | ✅ | — | II 7.44 / — / — | 淘汰（4.1 分数低；8B/3B 太小） |
| Granite 4.0-H-Small（32B 混合注意力） | IBM | 稠密 32B | 有 | 128k | 部分 | — | — | 淘汰（稠密且旧） |
| gpt-oss-20b | OpenAI | MoE 21B / 3.6B | ollama 官方 14GB（MXFP4） | 131072 | ✅ 官方 | — | II 9.95；速度 254 t/s | 淘汰（见 §5 MXFP4 on V100） |
| gpt-oss-120b | OpenAI | MoE 117B / 5.1B | ollama 官方 **65GB**（MXFP4） | 131072 | ✅ 官方 | — | II 11.60 | 淘汰：65GB > 64GB 总显存；且 MXFP4 在 sm_70 无原生路径 |
| Olmo 3 32B-Think / 3.1 32B-Think | Allen AI | 稠密 32B | 社区 GGUF 有 | 64k | ✅ | — | II 6.47 / **7.12**；**TB-Hard 1.5% / 0%** | 淘汰（稠密 + agentic 几乎为零） |
| Olmo 3 7B / 3.1 7B | Allen AI | 稠密 7B | 有 | 64k | ✅ | — | — | 淘汰（太弱，agentic 训练不足） |
| Tulu 3 / 3.1（8B、70B、405B） | Allen AI | 稠密（Llama-3.1 基座） | bartowski/lmstudio 有 | 8k–128k | ✅ | — | — | 淘汰：通用指令模型，非 agentic 编码后训练；无 SWE/TB 成绩 |
| **SmolLM3 3B** | HuggingFaceTB | 稠密 3B | ggml-org/unsloth 有 | 64k | ✅ | — | AA 无条目 | 淘汰（太小，agentic 不可能） |
| **OpenCodeReasoning-Nemotron 7B/14B/32B/1.1** | NVIDIA | **稠密**（Qwen2.5 基座） | bartowski/unsloth 有 | 32k | ✅ | 纯 code reasoning，非 agentic | — | 淘汰：base/instruct 蒸馏模型，**无 agentic/tool-calling 后训练**，32k ctx 也不够读长日志 |
| **OpenCoder 8B / 1.5B** | Infly | 稠密 8B/1.5B | bartowski/QuantFactory 有 | 32k | ✅ | — | — | 淘汰：2024-2025 通用 code instruct，非 agentic；`inf` 自定义许可（非标准 OSI），对我们有合规摩擦 |
| **Codestral 22B** | Mistral | 稠密 22B | bartowski 等有 | 32k | ✅ | FIM 补全为主 | AA 无条目 | 淘汰：2024-05 发布，专注 fill-in-the-middle，**非 agentic** |
| **CodeGemma 2B / 7B** | Google | 稠密 | mradermacher/PrunaAI 有 | 8k | ✅ | — | — | 淘汰：2024 年，指令/补全模型，非 agentic |
| **StarCoder2 3B/7B/15B** | BigCode | 稠密 base | mradermacher/second-state 有 | 4k–16k | ✅ | — | — | 淘汰：**base 模型**，无 instruct/agentic；ctx 太短 |
| **Arctic** | Snowflake | — | — | — | — | — | — | 淘汰：2025–2026 产线是 embedding（embed-l/m/r2.0）、ExCoT 蒸馏、Arctic-AWM、tilT、Arctic-LSTM 投机解码器，**没有一线 agentic 编码主模型** |
| Meltum / Mellum2（JetBrains） | JetBrains | MoE 12B / 2.5B | 官方 GGUF | 131072 | ✅ | 见上表 Mellum2.1 | — | 见上表 |
| JetBrains 其他（Kexer/KStack/CodeLlama/deepseek-coder 蒸馏） | JetBrains | 稠密 | 少量 | — | 部分 | — | — | 淘汰：2024 年 IDE 补全蒸馏模型 |

---

## 二、重点候选展开分析

### 2.1 ★ North-Mini-Code-1.0（Cohere，2026-06-09 发布）——本轮首选

**架构（直接证据）** —— `CohereLabs/North-Mini-Code-1.0/raw/main/config.json`：
```
architectures: ["Cohere2MoeForCausalLM"], model_type: cohere2_moe
hidden_size 2048, num_hidden_layers 49, num_attention_heads 32, num_key_value_heads 4, head_dim 128
num_experts 128, num_experts_per_tok 8, num_shared_experts 0, expert_selection_fn sigmoid
first_k_dense_replace 1, prefix_dense_intermediate_size 3072, expert intermediate 768
vocab_size 262144, max_position_embeddings 500000, sliding_window 4096, rope_theta 50000
```
GGUF 头实测（Range 只读元数据）：`general.architecture = cohere2moe`，`block_count 49`，`expert_count 128`，`expert_used_count 8`，`vocab_size 262144`，`leading_dense_block_count 1`，`attention.sliding_window_pattern` 为 49 长数组（值 0x01010101 → 3:1 滑窗/全局交错，与官方博客一致）。

**为什么它几乎一定是"同速"的** —— 它与现役 qwen3-coder-30b 形状几乎一致：

| | 现役 Qwen3-Coder-30B-A3B | North-Mini-Code-1.0 |
|---|---|---|
| 架构 | Qwen3MoeForCausalLM（`config.json` 实读） | Cohere2MoeForCausalLM |
| 层数 / hidden | 48 / 2048 | 49 / 2048 |
| 专家数 / 每 token 取几 | 128 / 8 | 128 / 8 |
| expert 中间维 | 768 | 768 |
| 前置稠密层 | 1（intermediate 6144） | 1（3072） |
| vocab / lm_head | 151936（**不绑**） | 262144（**不绑**） |
| 每 token 权重读取量（我算） | ≈ 1.85 GB | ≈ 2.01 GB |

**分数（直接证据）**
- 官方模型卡 + Cohere 博客（`hf-mirror.com/blog/CohereLabs/introducing-north-mini-code`，2026-06-09）：SWE-Bench Verified **80.2% pass@10**（SWE-Agent harness）；**61.0% pass@1**（mini-SWE-agent harness）；Terminal-Bench v2 **55.1% pass@10**；AAII Coding Index **33.4**（该指数版本已下线，见下）。
- 官方强调 **harness 鲁棒性**：训练时混用 SWE-Agent（50% SFT 配比）+ 仅 bash 单工具的 mini-SWE-agent + 细粒度 JSON 工具的 OpenCode（6% 配比）→ 跨 harness 迁移。**这一条对我们 af-bench 自研 harness 极其重要**：它不是过拟合单一 scaffold 的模型。
- AA（第三方，2026-10-21）：Intelligence Index **9.91**（现役 qwen3-coder-30b = 9.59）；**Terminal-Bench Hard 31.06%**（现役 15.15%）；**Terminal-Bench 2.1 35.58%**（本轮所有西方候选里最高，Devstral 2 仅 30.34%）；GPQA 75.66%；τ² 37.43%；IFBench 57.55%；AA-LCR 37.3%。
- 官方无 SWE-bench Verified 的 **pass@1**（80.2% 是 pass@10），**不可直接与单次 harness 结果对比**。

**风险（必须正视）**
1. **它是 thinking 模型**（AA 标 Reasoning=Yes）。推理 token 会拉高单题墙钟——这与我们"每题约 10 轮工具调用、单题墙钟同等重要"的约束直接冲突。
2. **AA 实测速度 76 t/s，而现役 qwen3-coder-30b 在 AA 上是 158 t/s**（同一平台口径），差 2.08×。这个差值与我的带宽模型**矛盾**（两者每 token 权重流量只差 8.5%）。要么 AA 侧服务实现/精度/批处理口径不同，要么该模型在 llama.cpp 上另有性能坑。**这是上生产前必须实测的第一项。**
3. 词表 262144 → lm_head 每 token 要读 0.537B 参数（Q4_K_M 下约 0.32GB），比现役多 70%。
4. 滑窗/全局 3:1 交错注意力 → llama.cpp 侧的注意力内核路径与纯 full-attn 不同，需要冒烟。
5. GGUF 全是社区量化（unsloth/bartowski），**不是官方发布**；且无 Cohere 官方 GGUF。

**许可证**：Apache 2.0（模型卡 `license: apache-2.0`）——无合规摩擦，优于 Mistral 的 "Modified MIT"。

---

### 2.2 ★ JetBrains Mellum2.1-12B-A2.5B-Thinking —— "快档"主力

**直接证据**（`JetBrains/Mellum2.1-12B-A2.5B-Thinking` 模型卡 + 官方 GGUF 仓库）：
- 12B 总参 / 2.5B 激活，64 专家取 8，ctx 131072，Apache 2.0。
- **官方发布 GGUF**：`Mellum2.1-12B-A2.5B-Thinking-Q4_K_M.gguf` = **8.07GB**（同仓还有 MXFP4_MOE 7.03GB / Q6_K 10.88GB / Q8_0 12.93GB / BF16 24.31GB）。这是本轮**唯一有厂商第一方 GGUF 且带完整 agentic 后训练**的西方小模型。
- 官方自报（统一用开源 harness "Pi v0.73.1"，shell + 文件编辑工具，114K ctx，每轮最多 16K token）：

| | Mellum2.1 Thinking | Mellum2 Thinking | Gemma 4 (E4B) | Qwen3.5 (9B) |
|---|---|---|---|---|
| SWE-bench Verified | **47.0** | 2.0 | 23.0 | 50.0 |
| Terminal-Bench 2.1 | **17.4** | 0.6 | 3.4 | 21.7 |
| SWE-bench Pro | **28.0** | 0.0 | 4.0 | 38.0 |
| BFCL v4 | 62.3 | 49.6 | 52.5 | 58.5 |
| GPQA Diamond | 64.6 | 51.0 | 53.1 | 77.8 |
| LiveCodeBench v6 | 82.0 | 69.4 | 69.4 | 75.4 |

- 训练方式（模型卡原文）："trains inside real repositories with a shell and file-editing tools and is rewarded when the tests pass"——真实仓库 RL，这是 agentic 能力的正确来源。
- 注意它与 Qwen3.5-9B 在同一 harness 下基本打平（47.0 vs 50.0），**即 agentic 能力≈9B 级**，低于现役 30B-A3B。

**我们的判断**：它是"更快但更弱"的一档。8.07GB 权重 + 2.5B 激活 → 每 token 权重读取 ≈ 1.5GB（Q4_K_M）→ **推断 ≈ 160–180 tok/s**（现役 135.7），且显存占用只有现役的一半，**双卡可同时驻留现役 + Mellum2.1 两个模型**，或用 Mellum2.1 做高并发重试臂。适合我们前期结论里给本地池规划的"弱模型档（分拣/草稿/工具调用重试）"角色，但**不能**替换现役做主解题。

---

### 2.3 ★ Nemotron-Cascade-2-30B-A3B —— τ²-bench 方向最优

**直接证据**（`nvidia/Nemotron-Cascade-2-30B-A3B` 模型卡）：
- 31.6B 总参 / 3B 激活，从 `Nemotron-3-Nano-30B-A3B-Base` 后训练；thinking 与 instruct 双模式（instruct 模式 = 开头加 `<think></think>`）；支持 1M ctx。
- 官方自报（vs 同表 Nemotron-3-Nano-30B-A3B / Nemotron-3-Super-120B-A12B / Qwen3.5-35B-A3B）：

| | Nano-30B-A3B | Super-120B-A12B | Qwen3.5-35B-A3B | **Cascade-2-30B-A3B** |
|---|---|---|---|---|
| SWE Verified (OpenHands) | 38.8 | 60.5 | 69.2 | **50.2** |
| Terminal Bench 2.0 | 8.5 | 31.0 | 40.5 | **21.1** |
| **τ²-Bench** | 49.0 | 61.2 | 81.2 | **58.9** |
| BFCL v4 | 53.8 | – | 67.3 | 52.9 |
| LiveCodeBench v6 | 68.3 | 78.7 | 74.6 | **87.2**（TIR 88.4） |
| AIME 2025 | 89.1 | 90.2 | 91.9 | 92.4 (98.6 TIR) |

- 关键工程细节：官方 vLLM 启动命令带 `--tool-call-parser qwen3_coder` → **它的工具调用格式与 qwen3-coder 同族**，对我们 harness 的 tool-calling 解析器几乎零改动。
- 官方明确："does not currently support OpenCode; it primarily supports OpenHands"。
- AA（第三方）：II **11.67**、**τ² 53.2%**（本轮所有候选最高，我们 harness 恰好有 τ²-bench）、IFBench 80.4%、GPQA 75.8%、TB-Hard 21.2%、TB2.1 20.6%。

**风险**
1. **架构是 Nemotron-H 混合 Mamba-2 + MoE**（52 层中 23 层 Mamba/MoE + 6 层 attention；128 routed 专家取 6 + 1 shared；`mamba_ssm_cache_dtype: float32`）。SSM 状态每层 = n_groups(8) × d_state(128) × d_inner(5376) = 5.5M float，**fp32 状态下每 token 额外读写约 1.0GB 显存流量**（见 §4 算术）。加上 MoE 专家权重（2.75B 激活 × 4.83bit ≈ 1.66GB）与 Mamba 投影（~0.74B × 4.83bit ≈ 0.45GB），**每 token 总流量 ≈ 3.1GB → 推断约 80 tok/s**，是现役的 ~0.6×。这是"更快但更弱"变体里的"更弱+更慢"，**不是**首选。
2. 社区 GGUF（bartowski）**无官方发布**。
3. thinking 模式 token 膨胀。

---

### 2.4 Nemotron 3.5 Bolt 74B-A9B（NVIDIA，官方 GGUF，22.02GB）——能力上限，但**不做量产臂**

**直接证据**
- 官方卡 `nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF`：
  - 总参 74B / 激活 9B；架构 = **Mamba-2–Transformer hybrid LatentMoE** + C-RADIO v4-H 视觉编码器；精度 = **IQ2（2-bit，量化感知训练 QAT）**，GGUF；ctx 最高 256K；**官方给出 28GB（RTX 32GB+）与 32GB（48GB+）两套 llama.cpp 配方**。
  - 官方 benchmark：**Terminal-Bench 2.1 = 50.98**（对照 Qwen3.6-35B-A3B 44.38、Nemotron 3.5 Lightning 30B-A3B 23.46）；MCP-Atlas 52.20；BrowseComp 66.75；GDPVal-AA-V2 28.47；AA-LCR 64.06；SciCode 41.02；PinchBench 87.82。
  - 官方明说设计目标："designed to run everyday agentic tasks locally"，部署形态就是 llama.cpp。
  - 官方量化说明：专家权重全部 **IQ2-XXS（2.0625 bit/元素）**，Mamba 层保留 NVFP4，embedding/output 层 Q8_0；用 ModelOpt 做 **QAD（量化感知蒸馏）**恢复精度。
- AA（第三方）：Intelligence Index **21.41 —— 本轮全部候选里最高**（vs 现役 9.59、Granite 4.2 12.68、Devstral 2 8.62）；HLE 24.65%；AA-LCR 69.67%；SciCode 39.70%。
- **文件体积（直接证据，HF API tree）**：主 GGUF **22.02GB**；投机解码 drafter `NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-LiLiCorr.gguf` = **1.00GB**。
- **GGUF 头实测**：`general.architecture = nemotron_h_moe`，`block_count 88`，`expert_count 496`，`expert_group_used_count 1`，`expert_shared_count 1`，`moe_latent_size 1024`，`ssm.state_size 128`，`ssm.group_count 8`，`ssm.inner_size 8192`，`context_length 262144`，`general.file_type 19`，`quantization_version 2`。
  - `file_type 19` 对应 `GGML_TYPE_IQ2_XXS`（`ggml/include/ggml.h:406`）。

**为什么它在本轮是"技术上最漂亮、运营上最不合适"的**
- 22.02GB **单张 V100S 32GB 就能装下**（余 ~10GB 给 KV cache）；64GB 双卡更宽裕。**"80B 级 MoE 装不下"这个前提在这里不成立**——NVIDIA 用 2-bit QAT 把它压到了 24GB。
- 但**每 token 要读 9B 激活参数 × 2.0625 bit ≈ 2.32GB 专家权重**（+attention/Mamba），比现役的 1.85GB 只多 25%。带宽不是问题。
- **真正的问题是 2-bit 反量化在 sm_70 上的单位字节成本**。llama.cpp 的 IQ2_XXS 在 CUDA 走 `vec_dot_iq2_xxs_q8_1`（`ggml/src/ggml-cuda/mmvq.cu:56`）——dp4a + 多级查表，**没有张量核**；且 MMVQ 在 Pascal 及更老架构上 batch 上限只有 5（`mmvq.cu:150-175` `get_mmvq_mmid_max_batch_pascal_older`，IQ2_XXS = 5）。加上 88 层 × 9 专家 = 792 次小矩阵乘（kernel launch 开销大）+ Mamba-2 递归扫描延迟 → **推断实测量级 20–40 tok/s**，比现役慢 3–6 倍。（此数值为推断，**未在 V100 实测**。）
- 想吃到官方 DFlash 投机解码（6–7 draft tokens）必须用 `--spec-type draft-dflash --spec-draft-model ...`，**ollama 没有对应开关**（ollama 的 `llm/server.go` 未见该参数）→ 必须自己编译 llama.cpp。
- 官方 28GB 配方本身就假定 `RTX Spark 64GB 或 dGPU 32GB+`、ctx 65536、parallel 1。

**结论**：作为"能力上限探索项"保留（例如在 anolis 上用自编 llama.cpp 跑一次冒烟 + af-bench 试跑），**不作为量产臂**——我们是"不烧 API 额度的量产臂"，吞吐权重极高。

---

### 2.5 Devstral 系：Mistral 的编码主力**全是稠密模型**，在 V100 上不可用

- **Devstral 2 (123B)** —— 直接证据：`config.json` = `architectures: ["Ministral3ForCausalLM"]`，88 层，hidden 12288，96 attn head / 8 KV head，`max_position_embeddings 262144`；**`model.safetensors.index.json` 里 2027 个张量中没有任何 `experts.*` 张量**，只有 `mlp.gate_proj/gate_proj/up_proj/down_proj` → **它是稠密模型**。AA 技术规格页写 "Total parameters 125B"，也未列 Active parameters。→ 结论：**125B 稠密**。
  - 官方分数：SWE-Bench Verified **72.2%**、SWE-Bench Multilingual 61.3%、Terminal-Bench 2 **32.6%**（对照 Qwen3 Coder Plus 69.6% / GLM 4.6 68.0% / DeepSeek v3.2 73.1% / Claude Sonnet 4.5 77.2%）。
  - GGUF：**无 Q4**。unsloth 的 UD-IQ2_XXS 34.40GB / Q2_K 46.59GB / Q2_K_L 46.97GB / Q3_XXS 48.96GB / IQ1_S 28.45GB。
  - → 46.6GB/token，**约 5 tok/s**。即使量化再压到 28.45GB（IQ1_S）也是 9 tok/s 量级。**淘汰**。
- **Devstral Small 2 (24B)** —— 稠密 24B（基座 Mistral-Small-3.1-24B-Base-2503）。官方：SWE-V 68.0%、SWE-Multi 55.7%、TB2 22.5%。GGUF Q4_K_M 14.33GB（ollama 官方 tag `devstral:24b` = 14GB，另有 q8_0 25GB / fp16 47GB）。→ 14.3GB/token，**约 17 tok/s**。**淘汰**。
- **Devstral Medium** —— AA 有模型页（II 9.01 估算、openness 11.1、availability 2），但该页**没有 "Model weights" 字段**，且 `mistralai` 账号下 2026-07-15 之后的新模型列表中**没有 Devstral Medium** → **API-only，非本地候选**。
- **Devstral 3** —— AA slug 404；HF `mistralai` 账号下无此模型 → **不存在（本轮未找到任何公开证据）**。

> 附：Mistral 2026 线上还有 `Mistral-Small-4-119B-2603`（119B，激活 6B？）、`Mistral-Medium-3.5-128B`（稠密 128B）、`Mistral-Large-3-675B`（稠密）、`Ministral-3` 3B/8B/14B（稠密）。AA 侧 Cohere 博客引用 "Mistral Small 4 (119B-A6B)" 且认为它不如 North Mini Code。我们没有对其做 GGUF/速度核查，**列为待办而非结论**。

---

### 2.6 IBM Granite 4.2 30B：分数不错，但**稠密**是致命伤

- 直接证据（`ibm-granite/granite-4.2-30b` 模型卡）："**Decoder-only Dense Transformer (Reasoning)**"，30B，64 层，hidden 4096，GQA 32 head / 8 KV head，SwiGLU MLP hidden 32768，natively 128K（可扩 512K），bfloat16，Apache 2.0，发布 2026-08-25。内置 `<think>...</think>` 推理，支持 full / non-thinking / low-effort 三档。
- **官方 GGUF**：`ibm-granite/granite-4.2-30b-GGUF` —— Q2_K 10.86 / Q3_K_S 12.75 / Q3_K_M 14.13 / Q3_K_L 15.31 / **Q4_K_M 17.72** / Q4_0 16.58 / Q5_K_M 20.78 / Q6_K 24.02 GB。
- AA：II **12.68**（西方稠密里最高）、TB2.1 26.6%、GPQA 64.4%、HLE 11.2%、AA-LCR 49%、GDPVal 575.7、**速度 41 t/s**（同一平台现役 158 t/s）。
- → 17.72GB/token，**约 14 tok/s**。**淘汰（速度）**。另外 Granite 3.x/4.0/4.1 都有官方 GGUF，但 4.1 的 II 只有 7.44。

### 2.7 其余欧美系（Olmo 3 / Tulu 3 / SmolLM3 / OpenCoder / OpenCodeReasoning / Codestral / CodeGemma / StarCoder2 / Arctic）

- **Olmo 3.1-32B-Think**：AA II 7.12，**Terminal-Bench Hard 0%**；Olmo 3-32B-Think：II 6.47，TB-Hard 1.5%。稠密 32B。→ 即使不慢也没有 agentic 能力。
- **Tulu 3 / 3.1**：通用指令模型（Llama-3.1 基座），无 SWE/TB 成绩；稠密。→ 淘汰。
- **SmolLM3 3B**：3B 稠密，Apache 2.0，ggml-org 有官方 GGUF。→ 太小。
- **OpenCodeReasoning-Nemotron (7B/14B/32B/1.1)**：模型卡原文 = "derivative of Qwen2.5-32B-Instruct… a reasoning model post-trained for reasoning for code generation"，ctx **32K**。**这是 base/instruct 蒸馏的 code-reasoning 模型，没有 agentic/tool-calling 后训练**，32K ctx 也不够我们读长日志。→ 淘汰。
- **OpenCoder 8B / 1.5B**：2024-2025 通用 code instruct，许可 `inf` 自定义（非标准 OSI）。→ 淘汰。
- **Codestral 22B**：2024-05，fill-in-the-middle 专用。→ 淘汰。
- **CodeGemma 2B/7B**、**StarCoder2 3B/7B/15B**（base 模型，ctx 4k–16k）：→ 淘汰。
- **Arctic（Snowflake）**：2025–2026 的产线是 embedding 系列、ExCoT 蒸馏、Arctic-AWM 4B/8B/14B、tilT、Arctic-LSTM 投机解码器（针对 gpt-oss-120b/20b、Qwen3-32B、Llama-3.3-70B）。**没有一线 agentic 编码主模型**。→ 淘汰。（附带发现：Snowflake 的 Arctic-LSTM 投机解码器值得在"低层加速"专题单独评估，不属本轮编码模型范围。）
- **"Nemotron Coder"**：在 `nvidia` 账号下 1000 个模型里逐个过滤 `coder/code`，**只找到** OpenCodeReasoning 系列、OpenMath-CodeLlama 系列、NV-EmbedCode、`Kimi-K2.7-Code-NVFP4` 与 `Kimi-K2.7-Code-DFlash`。**不存在官方的 "Nemotron Coder" 开放权重模型**；HF 上 `LLMWildling/NVIDIA-Nemotron-3-Super-135B-A13B-Coder-NVFP4` 等是第三方对**未公开**模型的 NVFP4 转换（且 NVFP4 对 V100 无效）。
  - 附带发现：`nvidia/Kimi-K2.7-Code-DFlash` 说明 **NVIDIA 已发布 DFlash 投机解码 drafter 的独立权重**（对应 llama.cpp 的 `--spec-type draft-dflash`），这对将来任何 NVIDIA 系模型加速都可用。
- **JetBrains 其他**：`CodeLlama-7B-Kexer`、`deepseek-coder-6.7B-kexer`、`Mellum-4b-sft-kotlin` 等均为 2024 年 IDE 补全蒸馏模型。→ 淘汰。**唯一有价值的 JetBrains 资产是 Mellum2.1**（见 2.2）。

---

## 三、"直接证据 vs 推断"分栏

| 结论 | 证据类型 | 具体来源 |
|---|---|---|
| North-Mini-Code = 30B/3B、128 专家取 8、vocab 262144、cohere2moe | **直接证据** | `hf-mirror.com/CohereLabs/North-Mini-Code-1.0/raw/main/config.json`；GGUF 头 Range 解析（`general.architecture=cohere2moe` 等 13 个 KV） |
| North-Mini-Code SWE-V 80.2% pass@10 / 61.0% pass@1 / TB v2 55.1% pass@10 | **直接证据（官方自报）** | `hf-mirror.com/blog/CohereLabs/introducing-north-mini-code`（2026-06-09） |
| North-Mini-Code AA II 9.91、TB-Hard 31.06%、TB2.1 35.58%、76 t/s | **直接证据（第三方）** | `artificialanalysis.ai/models/north-mini-code` 页内嵌 JSON，2026-10-21 抓取 |
| 现役 qwen3-coder-30b 的 AA II 9.59、TB-Hard 15.15% | **直接证据（第三方）** | `artificialanalysis.ai/models/qwen3-coder-30b-a3b-instruct` |
| Devstral 2 = 125B **稠密** | **直接证据** | `model.safetensors.index.json` 中 0 个 expert 张量；`config.json` 无 expert 字段；AA 页 "Total parameters 125B" 且无 Active |
| Nemotron 3.5 Bolt = 74B/9B、IQ2_XXS、22.02GB、TB2.1 50.98 | **直接证据** | NVIDIA 官方模型卡 + HF API tree 体积 + GGUF 头（`nemotron_h_moe` / `moe_latent_size 1024` / `file_type 19`） |
| llama.cpp **支持** `nemotron_h_moe` + `moe_latent_size` | **直接证据** | `src/llama-arch.h:104` `LLM_ARCH_NEMOTRON_H_MOE`；`src/llama-arch.cpp:233` `LLM_KV_MOE_LATENT_SIZE`；`src/llama-arch.cpp:523-524` `LLM_TENSOR_FFN_LATENT_DOWN/UP` |
| IQ2_XXS 在 CUDA 的 MoE 路径可走 GPU（不回落 CPU） | **直接证据** | `ggml/src/ggml-cuda/mmvq.cu:56` `vec_dot_iq2_xxs_q8_1`；`mmvq.cu:150-175` Pascal-or-older 的 MMVQ batch 上限（IQ2_XXS=5） |
| llama.cpp **在 Volta 上有专门 FA 路径** | **直接证据** | `ggml/src/ggml-cuda/fattn.cu:224` `if (cc == GGML_CUDA_CC_VOLTA)`；`common.cuh:52-54` CC 常量 |
| llama.cpp 有 `--n-cpu-moe N`（前 N 层 MoE 权重放 CPU）与 `--moe-cache-mib`（GPU 热缓存） | **直接证据** | `common/arg.cpp:2764-2788` |
| 各候选 GGUF 体积（19.20 / 8.07 / 22.02 / 46.59 / 14.33 / 17.72 / 18.17 …GB） | **直接证据** | HF API `/api/models/{id}/tree/main` 的 `lfs.size` |
| ollama 官方库只有 `devstral:24b`(14GB)、`gpt-oss:20b`(14GB)/`120b`(65GB)、`nemotron:70b`(43GB，老 Llama-3.1-Nemotron) | **直接证据** | `ollama.com/library/{devstral,gpt-oss,nemotron}/tags` 抓取 |
| ollama 0.40.6 发布于 2026-10-17 | **直接证据** | `github.com/ollama/ollama/releases.atom` |
| ollama 0.40.6 内置 llama.cpp 是否支持 `cohere2moe` / `nemotron_h_moe` | **未验证** | ollama 的 `llama/llama.cpp` 是 git submodule，raw 取不到；`github.com/ollama/ollama/raw/.../llama-arch.h` → 404。**必须现场冒烟** |
| V100S 标称显存带宽数值 | **未找到公开证据** | 本次可达的 nvidia.com V100 页与 datasheet PDF URL 均未返回含带宽数字的正文（PDF URL 返回 HTML 404 页）。**下文所有带宽推算一律用我们自己的实测值做锚，不引用标称值** |
| 各候选在 V100S 上的 tok/s 预测 | **推断** | 见 §4；**本轮未在任何 V100 上跑过** |
| `--n-cpu-moe` 的实际吞吐代价 | **推断** | 见 §4.3；未实测 |
| "稠密 27B 在 V100 上比现役慢 3–4 倍" | **推翻（本报告认为被严重低估）** | 见 §4.1：同平台第三方数据 3.9×，按本机实测锚推算约 10× |

---

## 四、对本轮核心假设的验证/推翻

### 4.1 假设 A：「总参很大但激活很少的 MoE 可能同时做到比现役更强、比稠密 27B 更快」

**判定：前半成立且被低估；后半（MoE 总参很大）在本轮西方系里基本不成立。**

**(a) MoE vs 稠密：假设方向对，幅度被低估 2–3 倍。**

第三方同平台口径（Artificial Analysis，同一 index 版本）：
- 现役 Qwen3-Coder-30B-A3B（MoE 30.5B/3B）：**158 t/s**
- IBM Granite 4.2 30B（**稠密 30B**）：**41 t/s** → **3.9×**

按我们自己的实测锚推算（详见 §4.2），差距是 **~10×**：
- 现役每 token 读 ~1.85GB → 135.7 tok/s → **有效带宽 ≈ 251 GB/s**
- Granite 4.2 30B Q4_K_M 17.72GB 全部要读 → **17.72 / 251 → ≈ 14 tok/s**
- Devstral Small 2 24B Q4_K_M 14.33GB → **≈ 17 tok/s**
- Devstral 2 125B Q2_K 46.59GB → **≈ 5 tok/s**

→ 结论：**在 V100 上，"稠密"基本等于"不可用"**，前提是每题 10 轮工具调用、需要读长日志、单题墙钟敏感的 agentic 负载。假设里说的"3-4 倍"应改为"**8–12 倍**"。

**(b) 但「总参很大」这一半不成立。** 本轮西方系最强的编码模型是**稠密**的（Devstral 2 125B、Devstral Small 2 24B、Granite 4.2 30B、Olmo 3 32B、gpt-oss 之外的多数）。真正在 V100 上可用的西方模型，激活参数都在 **2.5B–9B** 这个区间（North-Mini-Code 3B、Mellum2.1 2.5B、Nemotron-Cascade-2 3B、Nemotron-Nano 3.5B、Bolt 9B）。

**(c) 真正提高上限的是"用低比特换激活量"，不是"堆总参"。** NVIDIA Bolt 就是把 74B 总参用 **IQ2（2.0625 bit）+ QAT 蒸馏**压进 22.02GB，从而让 9B 激活在 32GB 卡上跑得动。这条路对我们**可行但不适合作量产臂**（sm_70 无张量核，2-bit 反量化每字节成本高）。

**(d) 反驳一个可能的误读**：「激活参数少 = 一定快」只在**权重字节是瓶颈**时成立。若模型用 **Mamba-2/SSM 混合**（Nemotron-H 系），每 token 还要读写 SSM 状态——Nemotron-3-Nano 配置里 `mamba_ssm_cache_dtype: float32`，单层状态 = 8 groups × 128 state × 5376 inner = 5.5M float = 22MB，23 个 Mamba 层 → **每 token 额外约 1.0GB 显存流量**。这让 Nemotron-Cascade-2 的每 token 流量估算（约 3.1GB）**高于**现役（1.85GB）→ 反而更慢。

### 4.2 我们的带宽模型（可复算，推断但基于实测锚）

**锚点（直接证据，来自本次会话给定）**：Qwen3-Coder-30B-A3B-Instruct Q4_K_M，decode **135.7 tok/s**（num_ctx 8192）。
**权重构成（直接证据，Qwen3-Coder-30B-A3B `config.json` 实读）**：48 层 / hidden 2048 / 32 attn head / 4 KV head / head_dim 128 / **128 专家，每 token 取 8** / expert intermediate 768 / 前置稠密层 intermediate 6144 / vocab 151936 / `tie_word_embeddings: false`。

每 token 需要读到的权重参数：
- 路由专家：48 × 8 × 3 × 2048 × 768 = **1.813B**
- 注意力：48 × (2048×4096 + 2×2048×512 + 4096×2048) = **0.906B**
- 稠密 FFN（仅第 0 层）：2048×6144×3 = **0.038B**
- lm_head（不绑 embedding，每 token 读）：151936×2048 = **0.311B**
- 合计 ≈ **3.068B 参数/token**

Q4_K_M 有效位宽取 4.83 bit/weight → **1.852 GB/token**。
→ **有效带宽 = 135.7 tok/s × 1.852 GB ≈ 251 GB/s**（这是本机 llama.cpp + V100S + Q4_K_M MoE 的实测折算常数，后面全部用它推）。

| 候选 | 每 token 权重（我的计算） | 推算 tok/s | 相对现役 |
|---|---|---|---|
| 现役 Qwen3-Coder-30B-A3B Q4_K_M | 3.068B → 1.85GB | **135.7（实测）** | 1.00× |
| **North-Mini-Code-1.0 Q4_K_M** | 49×8×3×2048×768=1.851B + attn 0.925B + dense 0.019B + lm_head 0.537B = 3.332B → 2.01GB | **≈ 125** | 0.92× |
| **Mellum2.1 12B-A2.5B Q4_K_M** | 激活 2.5B（含 lm_head 估计）→ ≈1.5GB | **≈ 165–175** | 1.25× |
| **Nemotron-Cascade-2-30B-A3B** | experts 2.75B + attn 0.14B + mamba 投影 0.74B + **SSM 状态 fp32 1.0GB** → ≈3.1GB | **≈ 80** | 0.59× |
| Nemotron 3.5 Bolt 74B-A9B IQ2_XXS | 专家 9B×2.0625bit = 2.32GB + attn/mamba ≈ 0.2GB + SSM 状态（88 层，含 496 专家，state 更大）≈0.8GB → ≈3.3GB | **≈ 75（若 IQ2 反量化开销与 Q4_K_M 同级）；实测更可能是 20–40** | 0.15–0.55× |
| Granite 4.2 30B Q4_K_M（稠密） | 17.72GB 全部读 | **≈ 14** | 0.10× |
| Devstral Small 2 24B Q4_K_M（稠密） | 14.33GB 全部读 | **≈ 17** | 0.13× |
| Devstral 2 125B Q2_K（稠密） | 46.59GB 全部读 | **≈ 5** | 0.04× |

> 上述 tok/s 全是**推断**。模型间**相对**结论（稠密 ≪ MoE；North-Mini ≈ 现役）比**绝对**值可靠得多。绝对值还受 kernel launch 开销、batch=1 时的小矩阵效率、CPU 辅助线程、CUDA graph 是否生效影响很大。

### 4.3 假设 B：「80B 级 MoE 的 Q4 权重约 45GB，双卡 64GB 能否放下？放不下时 --n-cpu-moe 在 V100 上可行吗、代价多大？」

**(1) 放得下。** 45GB Q4 权重 + KV cache：
- Nemotron-H 家族 KV cache 极小（88 层里只有 6 层是 attention），64K ctx 也很小；纯 attention 家族（如 Qwen3-30B-A3B，48 层全 attention，4 KV head × 128 dim）96KB/token → 64K ctx ≈ 6GB。
- 45 + 6 = 51GB < 64GB → **放得下**。
- 更进一步：NVIDIA 用 IQ2 把 74B 压到 **22.02GB**，**单卡 32GB 就够**（官方给了 "RTX Spark 64GB 或 dGPU 32GB+ / 28GB recipe / 65536 ctx / parallel 1" 的配方）。
- → **「80B MoE 装不下」不是我们这池子的真问题**。真问题是**每 token 激活参数的权重字节数**和**量化格式的反量化开销**。

**(2) `--n-cpu-moe` 的语义与代价（直接证据 + 推断）**
- 语义（`common/arg.cpp:2771`）：`--n-cpu-moe N` = "keep the Mixture of Experts (MoE) weights of the **first N layers** in the CPU"；`--cpu-moe` = 全部 MoE 权重放 CPU；`--n-cpu-ffn` 则是稠密模型的 FFN（arg 文本明确让我们用 `--n-cpu-moe` 处理 MoE 专家）。
- 配套还有 `--moe-cache-mib N`（arg.cpp:2777）："GPU cache size in MiB for the MoE experts kept in the CPU… split among them like the layers (--tensor-split)" → **可以把热专家缓存在显存里**，这让 CPU 卸载从"全 PCIe 流量"变成"命中率决定"。
- 代价（**推断，未实测**）：每 token 这些层的激活专家权重必须走 PCIe。以一个 74B/9B 的模型、IQ2 量化估算，每层激活 9 专家 ≈ 74B/88层/496专家… 换算成字节：单层专家总权重 ≈ 22GB/88 ≈ 250MB，激活 9/496 ≈ 1.8% → 每层每 token ≈ 4.5MB。卸载 4 层 → 18MB/token；按 PCIe 4.0 x16 ≈ 25GB/s 算，约 0.7ms/token（可接受）；卸载 20 层 → 90MB/token → 约 3.6ms/token；再叠加 llama.cpp 的同步开销与 CPU 侧 dequant/GGUF-mmap 页缺失，**卸载 20 层以上基本会掉到 10–30 tok/s**。
- 对 4-bit Q4 的 80B MoE：单层专家 ≈ 45GB/80层 ≈ 560MB，激活比 3/128 → 13MB/token/层，卸载 10 层 = 130MB/token → 5ms/token → 上限约 200 tok/s（但 CPU 侧 dequant 是单线程瓶颈，实际远低于此）。
- **对本轮结论**：**我们不需要 `--n-cpu-moe`**。所有入围候选（19.2 / 8.07 / 22.02 / 18.17 GB）都能整卡放进 32GB V100S；`--n-cpu-moe` 只会作为"显存不够时的兜底"存在。**并且 ollama 并不暴露这个开关**（`llm/server.go` 里没有），要用必须自编 llama.cpp。

### 4.4 假设 C（工程风险）：Qwen3.8-27B 的 `qwen3_5` 混合线性注意力在 llama.cpp 上有"输出损坏"CUDA bug

本轮未复现、也未找到该具体 bug 的公开证据（`github.com/ggml-org/llama.cpp` 的 issue 页面在本机可达但我未定位到对应 issue；`raw.githubusercontent.com` 被阻断）。**但本轮发现一个结构上完全同类的风险源，值得写进风险清单：**

> **llama.cpp 的 `nemotron_h_moe` 走的是和 `qwen3_5` 同一类"混合递归(Mamba/SSM) + MoE + 潜空间投影"图结构**。llama.cpp 侧对应的新张量 `LLM_TENSOR_FFN_LATENT_DOWN/UP` 走 `GGML_OP_MUL_MAT` 且在 buft 探测里被强制标成 `LAYER_REPEATING`（`src/llama-arch.cpp:1102-1104` 注释明确写"latent projections feed ggml_mul_mat, the buft probe must use MUL_MAT to keep them on GPU"）——**这正是"输出损坏 / GPU 未生效"类 bug 的高发位置**。因此：
> - **North-Mini-Code（纯 cohere2moe，无 Mamba、无 latent 投影）风险最低** → 更加支持把它排第一。
> - **Nemotron-Cascade-2 / Nemotron-Nano / Bolt（Mamba 混合 + latent）风险等级与 Qwen3.8 同类** → 部署前必须按前期结论"先冒烟"。

---

## 五、对我们的具体建议（落到 anolis-gpu-01，2×V100S-32GB）

### 5.1 结论：换掉现役的**唯一推荐**是 North-Mini-Code-1.0

**决策矩阵**

| | 解题率 | 单题墙钟 | 部署风险 | 许可 |
|---|---|---|---|---|
| 现役 qwen3-coder-30b | 基线 | 基线（135.7 t/s） | 已知可用 | Apache 2.0 |
| **North-Mini-Code-1.0** | **AA TB-Hard 15.15% → 31.06%（2.05×）**；AA TB2.1 35.58%（本轮西方最高）；官方 SWE-V 80.2% pass@10 | **推算 ≈125 t/s（0.92×），token 数增加是唯一变量** | 中（社区 GGUF、thinking 模型、词表大） | Apache 2.0 |
| Mellum2.1-12B-A2.5B | 官方 SWE-V 47.0（Pi harness），约 9B 级 | 推算 ≈165–175 t/s | **低**（官方 GGUF 8.07GB、架构简单） | Apache 2.0 |
| Nemotron-Cascade-2-30B-A3B | AA τ² 53.2%（最高）、II 11.67 | 推算 ≈80 t/s（0.59×） | **高**（Mamba 混合 + latent 投影 + 社区 GGUF） | NVIDIA Open Model License |
| Nemotron 3.5 Bolt 74B-A9B | AA II 21.41（最高）、官方 TB2.1 50.98 | 推算 20–40 t/s | **最高**（IQ2_XXS on sm_70 + 需自编 llama.cpp 用 DFlash） | OpenMDW-1.1 |

### 5.2 落地步骤（North-Mini-Code-1.0）

**Step 0 — 先做 20 分钟冒烟（因为 ollama 0.40.6 能否加载 cohere2moe 未验证）**
```bash
# anolis 上确认当前基线
ollama list | grep qwen3-coder-30b
# 下载（走 hf-mirror 或 HF 直连）。两个可选 Q4_K_M（体积均已用 HF API tree 核实）：
#   bartowski/North-Mini-Code-1.0-GGUF  → North-Mini-Code-1.0-Q4_K_M.gguf       18.74GB（标准量化，首选）
#   unsloth/North-Mini-Code-1.0-GGUF    → North-Mini-Code-1.0-UD-Q4_K_M.gguf    19.20GB（unsloth 动态量化，备选）
#   bartowski 另有 Q3_K_M 14.21GB / Q5_K_M 21.85GB
hf download bartowski/North-Mini-Code-1.0-GGUF \
    North-Mini-Code-1.0-Q4_K_M.gguf --local-dir /data/models/nmc
```
```bash
# Modelfile（建议值见下方说明）
cat > /data/models/nmc/Modelfile <<'EOF'
FROM /data/models/nmc/North-Mini-Code-1.0-Q4_K_M.gguf
PARAMETER num_ctx 32768
PARAMETER temperature 1.0
PARAMETER top_p 0.95
PARAMETER num_gpu 999
EOF
ollama create north-mini-code -f /data/models/nmc/Modelfile
ollama show north-mini-code        # 若报错 "unknown model architecture" → 走 Step 0b
```
**Step 0b — 若 ollama 0.40.6 不认 `cohere2moe`（可能性存在，因为 ollama 的 llama.cpp 是 submodule，版本无法离线核实）**
自编 llama.cpp（我们 CUDA 12.6 支持 sm_70，**不要用 CUDA 13**，它已移除 Volta）：
```bash
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=70 -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j 32
```
> 架构说明：把 `CMAKE_CUDA_ARCHITECTURES` 固定成 `70` 而不是 `native`，避免构建期把 sm_70 的 kernel 裁掉。llama.cpp 的 CUDA FA 在 Volta 上有专门分支（`fattn.cu:224`），不需要关 FA。

**Step 1 — 配置改动（相对现役）**

| 项 | 现役 | 建议 | 理由 |
|---|---|---|---|
| `num_ctx` | 8192（实测时）/ 262144（模型上限） | **32768** | North-Mini KV：49 层 × 4 KV head × 128 dim × 2 (K,V) × 2B ≈ 100KB/token → 32K ≈ **3.2GB**；262K 会到 26GB 撑爆单卡 |
| 权重显存 | 18.5GB | 18.74GB | — |
| 显存合计（单卡） | — | ≈22.4GB | V100S 32GB 余 ~9GB，可留给并发 2 路 KV（再 +3.2GB） |
| 双卡分配 | — | **权重全部 GPU0（-ngl 999），GPU1 留给并发臂** | 跨卡切层会把 PCIe 变成瓶颈；MoE 专家切到第二卡是已知慢点 |
| KV 精度 | 默认 f16 | `--cache-type-k q8_0 --cache-type-v q8_0` | KV 砍半 → 32K ctx 只吃 1.6GB，腾出空间跑并发 2 |
| 采样 | — | temperature 1.0 / top_p 0.95 | **官方指定**（Cohere 博客与模型卡一致） |
| thinking | — | **必须显式决定开/关** | 它是 thinking 模型（AA: Reasoning=Yes）；关掉能省 token 但可能掉分，**建议在 af-bench 上 A/B 两档各跑一遍** |
| ollama 并发 | `OLLAMA_NUM_PARALLEL=2` | 保持 2 | 现有基线可比 |

**Step 2 — harness 侧（af-bench）需要改的点**
1. **工具调用格式**：Cohere 的 tool-call 模板与 qwen3-coder 不同源。llama.cpp 侧用 `--jinja` 走模型自带 chat template；ollama 侧用 Modelfile 的 `PARAMETER` + 模型自带 template。**必须先做一次"模型输出 → JSON tool call"的往返验证**。
2. **thinking 块处理**：确认 `<think>...</think>`（或 Cohere 用的标签）在我们解析器里被正确剥离，且**不计入**结果判定，但**计入** token 预算。
3. **token 预算**：前期 50-方案里"输入 300K + 输出 30K/任务"对 SWE/TB 高估了 1–2 个数量级（实测校准）。North-Mini 走 thinking 后输出 token 会上升，**需要重新标定"完成度纪律"阈值**（前期结论：真正的成本瓶颈是"模型不努力"而不是绝对能力）。
4. **长日志读取**：262k ctx 不是重点（我们实测用的是 8192）；重点是 **32K 下的 RULER/长日志**是否仍稳。模型卡称 "ASL" 能力经过训练，但 500K ctx 与我们的用法无关。

**Step 3 — 验收判据（建议写进验收单）**
- 冒烟：连续 10 轮工具调用不崩、tool call JSON 100% 可解析、跨轮不遗忘（我们前期"输出损坏"教训）。
- 吞吐：decode ≥ 110 t/s（我推算 125，允许 -12% 折损）；若 < 80 t/s，优先怀疑大词表 lm_head 与 thinking token，而非模型本身。
- 解题率：af-bench 上 SWE-bench Verified / Terminal-Bench / τ²-bench 三项至少两项 **≥ 现役 × 1.3**（AA 上 TB-Hard 是 2.05×，留 35% 折损余量）。
- 并发：并发 2 时单请求 ≥ 90 t/s（现役并发 2 是 109.7 t/s）。
- 熔断：与 API 主力（MiniMax M3.1 Flash / GLM-5.3 / Kimi K3）的分工不变——**本地臂只做"不烧额度的量产臂"**，GLM-5.3-Flash SWE-V 92% 仍是天花板，本地臂的目标是把**下限**拉上去。

### 5.3 次优建议（并行推进，不互斥）

- **并行跑一个 Mellum2.1-12B-A2.5B（8.07GB 官方 GGUF）常驻**：它 8GB，与 North-Mini 的 19.2GB 可以**同时放进 64GB 显存**（19.2 + 3.2 + 8.1 + KV ≈ 32GB，还剩 32GB 给并发 2 路各自独立的 KV）。定位：**分拣 / 草稿 / 工具调用重试 / 廉价预检**（前期结论给本地池定的"弱模型档"，现在有了具体型号）。它的官方 SWE-V 47.0 已经很接近很多 API 模型，**性价比可能比现役做主臂都高**。
- **Nemotron-Cascade-2-30B-A3B 只在 τ²-bench 是瓶颈时再上**：它是本轮唯一 τ²-bench 显著领先（AA 53.2% vs 现役 34.5%）的候选，且 tool-call parser 与 qwen3-coder 同族。但 Mamba 混合架构在 V100 上有"输出损坏"同类风险，**必须先冒烟再谈上线**。
- **Nemotron 3.5 Bolt 只做"上限探索"**：需要自编 llama.cpp 才能用 DFlash 投机解码（ollama 无 `--spec-type draft-dflash`），且 IQ2_XXS 在 sm_70 上速度存疑。放在优先级最低。
- **明确不再评估**：Granite 4.2 30B、Devstral 2 / Small 2、Olmo 3、gpt-oss-120b、gpt-oss-20b（MXFP4 在 sm_70 无原生路径，llama.cpp 只能反量化）、OpenCoder、OpenCodeReasoning、SmolLM3、Tulu 3、CodeGemma、StarCoder2、Codestral、Arctic。**理由统一：要么稠密（速度）、要么无 agentic 后训练、要么太小太旧、要么无开放权重。**

### 5.4 对前期结论的修正（`设计/benchmark调研/实测/model-pricing.md` §4.2）

| 前期结论 | 本轮判定 |
|---|---|
| "本地池定位=弱模型档（分拣/草稿/工具调用重试），产线主力走 API" | **部分保留，但需要更新**：现在有一个**同速、agentic 分数约 2×** 的西方开放权重模型（North-Mini-Code-1.0），本地池不必只做"弱模型档"。主力走 API 的结论不变（GLM-5.3-Flash SWE-V 92% 仍是天花板）。 |
| "本地最强可行选项 = Qwen3-Coder-Next 80B A3B Q4（双卡），保底 = Qwen3-Coder-30B-A3B Q4_K_M（单卡）" | **需补充一条更优解**：North-Mini-Code-1.0 Q4_K_M 19.20GB，**单卡即可**，激活量与现役相同，AA TB-Hard 2.05×。且它的官方分数（80.2% pass@10 SWE-V）比 Qwen3-Coder-Next 的自报 70.6% 高。**建议把 North-Mini-Code 放进下一轮 bench 实测的候选清单首位。** |
| "GPT-OSS-120B MXFP4 明确不建议（V100 不支持 MXFP4）" | **维持**。补充：gpt-oss-120b 的官方 GGUF 是 **65GB**，已超 64GB 总显存，**双重不可行**。gpt-oss-20b（14GB MXFP4）虽装得下，但 AA II 9.95、agentic 分数无优势，淘汰。 |
| "部署必须先冒烟（llama.cpp 在老卡上有输出乱码/GPU 未生效 issue #17067）" | **维持并强化**。本轮在 llama.cpp 源码里定位到高发区：混合递归（Mamba/SSM）+ MoE + 潜空间投影（`LLM_TENSOR_FFN_LATENT_DOWN/UP`）。**North-Mini-Code（纯 cohere2moe）不涉及这条路径，风险最低——这是把它排第一的额外理由。** |
| "API 对照锚点：GLM-5.3-Flash SWE-V 92% @ $0.02/task" | 维持。**本轮未复核该数字**（不在本轮范围，且 mistral/AA 的部分口径依赖外部页面）。 |

---

## 六、本轮没做/做不到的（明确交代）

1. **没有在 anolis（2×V100S）上跑过任何模型**——本会话的机器是 pandev-comp（RTX 3070 Laptop 8GB），且明确要求不下载权重。§4 的所有 tok/s 都是**基于我们已有实测锚点的算术推断**，不是实测。
2. **没有核实 ollama 0.40.6 内置 llama.cpp 的版本**（其 `llama/llama.cpp` 是 git submodule，raw 路径 404；jsdelivr 缓存版本过旧）。因此"ollama 能否直接加载 `cohere2moe` / `nemotron_h_moe` GGUF"**未验证**。
3. **没有找到 V100S 标称显存带宽的官方原文**（可达的 nvidia.com 页面与 PDF URL 均未返回含该数字的正文）。§4 全部改用我们自己的实测折算常数（251 GB/s）。
4. **没有复现也没有定位到 Qwen3.8 `qwen3_5` "输出损坏" CUDA bug 的具体 issue**（GitHub API 在本机被限流，raw 可用但未定位）。§4.4 是基于源码结构做的**风险类比推断**。
5. **North-Mini-Code 的官方 SWE-bench Verified 只有 pass@10（80.2%），没有 pass@1 的官方数**（61.0% pass@1 是 mini-SWE-agent harness 口径，与我们 af-bench 的口径都不同）。
6. **AA 的 "Coding Index" 33.4**（Cohere 博客引用）对应的是**已下线的旧版 AA 指数**（我们前期记录：现行 v4.3.2 已无独立 Coding Index），**不能与现行 II 直接比较**。本报告统一用现行 II + Terminal-Bench 分项。
7. **没有评估**：Mistral Small 4 119B-A6B、Mistral Medium 3.5 128B、Mistral Large 3 675B、ServiceNow Apriel 1.6-15B、Cohere North Micro Vision、google/gemma-4 系、EXAONE、LiquidAI LFM2.5、Meta Llama 4 —— 这些在 AA 的对比表里出现但不在本轮"西方编码模型"清单内，其中不少也不是编码专精。**未找到公开证据的部分不做推测。**
8. **磁盘约束未作为淘汰理由**（按运营者说明，必要时可扩容）。所有淘汰理由都是**每 token 权重流量 / 激活参数 / 显存占用 / 架构风险**，不是"装不下"。

---

## 附：本次调研用到的可复现命令（全部在本会话执行过）

```bash
# HF 镜像 API：模型检索 / 仓库文件树（体积）/ GGUF 元数据（只读头部 Range 请求）
curl -sL -A "Mozilla/5.0" "https://hf-mirror.com/api/models?search=devstral&limit=30&sort=downloads&direction=-1"
curl -sL -A "Mozilla/5.0" "https://hf-mirror.com/api/models/unsloth/North-Mini-Code-1.0-GGUF/tree/main"
curl -sL -A "Mozilla/5.0" "https://hf-mirror.com/CohereLabs/North-Mini-Code-1.0/raw/main/config.json"
curl -sL -A "Mozilla/5.0" -H "Range: bytes=0-4194303" \
  "https://hf-mirror.com/unsloth/North-Mini-Code-1.0-GGUF/resolve/main/North-Mini-Code-1.0-UD-Q4_K_M.gguf" \
  | python3 ggufhdr.py   # 只解析 KV 元数据，不读权重张量

# 官方模型卡 / 博客
curl -sL -A "Mozilla/5.0" "https://hf-mirror.com/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF/raw/main/README.md"
curl -sL -A "Mozilla/5.0" "https://hf-mirror.com/blog/CohereLabs/introducing-north-mini-code"

# 第三方：Artificial Analysis 指标从页面内嵌 JSON 提取
curl -sL -A "Mozilla/5.0" "https://artificialanalysis.ai/models/north-mini-code"

# 引擎可行性：llama.cpp 源码（github raw 可达，raw.githubusercontent 不可达）
curl -sL -A "Mozilla/5.0" "https://github.com/ggml-org/llama.cpp/raw/refs/heads/master/src/llama-arch.h"
curl -sL -A "Mozilla/5.0" "https://github.com/ggml-org/llama.cpp/raw/refs/heads/master/ggml/src/ggml-cuda/mmvq.cu"
curl -sL -A "Mozilla/5.0" "https://github.com/ggml-org/llama.cpp/raw/refs/heads/master/ggml/src/ggml-cuda/fattn.cu"
curl -sL -A "Mozilla/5.0" "https://github.com/ggml-org/llama.cpp/raw/refs/heads/master/common/arg.cpp"

# Ollama 现状
curl -sL -A "Mozilla/5.0" "https://ollama.com/library/devstral/tags"
curl -sL -A "Mozilla/5.0" "https://github.com/ollama/ollama/releases.atom"
```
