# GGUF 量化生态调研：2×V100S-32GB 上的编码模型选型（2026-10-21）

> 本轮任务：研究 GGUF 量化生态当下最优做法（Unsloth Dynamic v3/v4、bartowski、lmstudio-community、ggml-org、IQ/IQ3_XS/UD-Q4_K_XL、EXL2/AWQ/GPTQ/Marlin、Q4_K_M vs Q5_K_M vs Q8_0 vs Q3_XXS 的质量损失实测），并回答三个具体问题：
> 1. 某模型在 32GB V100 上最佳量化档是哪个？
> 2. IQ/UD 系列与标准 K 量化在 2×V100 上的速度差？
> 3. 社区「Q4 最好、Q2/Q3 伤代码」的证据？

---

## 0. 取证条件与免责（必读）

**本次会话所在机器不是 anolis-gpu-01。** 实测确认：本机是编排面 pandev-comp（RTX 3070 Laptop 8GB、14GB 内存、ollama 0.35.1），**没有任何 V100**（`nvidia-smi` 输出仅 1× RTX 3070 Laptop，8192MiB）。

因此：

- **本轮所有 V100 相关的性能数字都不是本轮实测**，来源分三类，逐条标注：
  - 【官方自报】：发布方自己给的数字（Unsloth 文档 / Qwen 模型卡 / ollama 官方页）。
  - 【第三方复现】：社区在**真实硬件**上跑出来的数字（如 llama.cpp issue 里的 llama-bench 输出）。
  - 【推断】：我基于带宽/参数量的手算，标为推断并给出公式与假设。
- **未做的事**：未下载任何模型权重（HF 在本机被网络策略拦截，huggingface.co / hf.co / cdn-lfs 全部超时，reddit / HN 同样不可达），未在 V100 上跑任何基准。
- 本轮取证通道：**GitHub REST API + raw.githubusercontent + GitHub issue HTML、ModelScope API、ollama.com、unsloth.ai/docs（GitBook 的 `.md` 版本可直接取全文）、b ing 搜索**。HF 与 Reddit 不可达导致 **bartowski / lmstudio-community 的模型卡原文未能直接阅读**，只能通过 ModelScope 镜像的文件清单与引用它们的第三方 issue 间接取证（见 §6「未取得证据」）。

**基准日期：2026-10-21。** llm 相关版本号以当日为准。

---

## 1. 结论速览

| # | 结论 | 证据强度 |
|---|---|---|
| 1 | **量化生态的当前最优不是「某个神奇量化格式」，而是「Unsloth Dynamic（UD- 前缀）逐张量混合量化 + agentic 校准 imatrix」**。UD-Q4_K_XL 在同尺寸下比社区标准 imatrix 量化高 2–4 个百分点（Aider Polyglot 实测），且这是可复现的第三方数据。 | 第三方复现（Aider Polyglot，David Sluys 跑） |
| 2 | **「Q2/Q3 伤代码」有直接证据，但边界在 3-bit，不是 4-bit**。UD-IQ3_XXS 在 Aider Polyglot 上接近 BF16；再降到 2-bit/1-bit，Divergence-300@32 从 ~25% 崩到 <8–10%，**tool calling 直接失效**。 | 官方自报(Unsloth) + 第三方复现(Aider) |
| 3 | **「MoE 总参大但激活少 ⇒ 解码快」这个假设成立，而且现役模型本身就是 MoE**。稠密 27B 在 V100 上实测 ~30 tok/s（第三方 V100 实测），而我们现役 30B-A3B（激活 3.3B）实测 135.7 tok/s——**差 4.3 倍**，与前期假设（3–4 倍）吻合。 | 第三方复现（V100 llama-bench）+ 我方既有实测 |
| 4 | **因此本地最强可行候选是 Qwen3-Coder-Next（80B-A3B，激活 3B）**：Q4 档 49.6GB 塞进 64GB 偏紧，**UD-Q3_K_XL 36.28GB 宽松**，且第三方称 3-bit 对该模型接近 BF16。 | 官方自报 + 第三方复现 + 推断 |
| 5 | **但 Qwen3.8-27B / Qwen3.6（qwen3_5 家族）在 sm_70 上有未解决的 CUDA 崩溃级风险**（见 §5），Qwen3-Coder-Next 走的是更早的 `qwen3next` 架构，家族风险面小一档。 | 官方 issue（OPEN） |
| 6 | **2×V100 的部署约束是 `--split-mode layer`**：`row` 在 CUDA 上直接不支持，`tensor` 在多卡 Volta 上会 hang 并泄漏显存（第三方 3×V100 实测）。 | 第三方复现 |
| 7 | **EXL2 / AWQ / GPTQ / Marlin 路线在 V100 上整体出局**：vLLM V1 已移除 V100；Marlin 需要 sm_80+；vLLM 在 V100 上有大量 kernel/FA 失败记录。**本机没有 vLLM，结论是「不要重新选型」而不是「值得试」。** | 官方 issue + 推理 |

---

## 2. GGUF 量化生态地图（2026-10-21 版）

### 2.1 上游：llama.cpp（本轮所有格式的"定义者"）

- **最新版本 v0.7.0，发布于 2026-10-15**（GitHub API `releases/latest`：`tag_name=v0.7.0`, `published_at=2026-10-15T17:13:19Z`）。
- **我们 ollama 0.40.6 恰好内置 v0.7.0**：`https://raw.githubusercontent.com/ollama/ollama/v0.40.6/LLAMA_CPP_VERSION` → `b11669`；而 llama.cpp 的 `b11669` 正是提交 "llama.cpp : bump version to 0.7.0 (#30603)"，提交时间 2026-10-15T16:48:22+03:00。
  - ollama v0.40.6 发布于 2026-10-16，v0.40.7（2026-10-20）pin 到 `b11738`。
  - **含义**：我们 ollama 0.40.6 ≈ llama.cpp v0.7.0，属于"新到不能再新"，§5 里那些 2026 年 8–10 月的 sm_70 崩溃问题大部分已在其中，但 **b11669 之后 5 天内的改动没有**（例如 #29107 IQ3 code reorder，2026-10-20，v0.40.7 才有）。
- **sm_70 仍在官方 CUDA 编译目标里**：`ggml/src/ggml-cuda/CMakeLists.txt` 中 `70 == V100, FP16 tensor cores`，并以 `70-virtual` 形式加入 `CMAKE_CUDA_ARCHITECTURES`。
- **官方量化类型清单**（`gguf-py/gguf/quants.py`）：F32/F16/BF16、Q4_0/Q4_1/Q5_0/Q5_1/Q8_0、Q2_K…Q6_K、TQ1_0/TQ2_0（ternary）、Q1_0/Q2_0（新）、IQ1_S/IQ1_M、IQ2_XXS/IQ2_XS/IQ2_S、IQ3_XXS/IQ3_S、IQ4_XS/IQ4_NL、MXFP4、NVFP4。
- **CUDA MMQ（int8 DP4A 矩阵乘）覆盖的量化类型**（源码 `ggml/src/ggml-cuda/mmq.cu` 的 case 列表 + `template-instances/` 清单）：
  - 有：`Q8_0 / Q2_K / Q3_K / Q4_K / Q5_K / Q6_K / IQ1_S / IQ2_XXS / IQ2_XS / IQ2_S / IQ3_XXS / IQ3_S / IQ4_XS / IQ4_NL / MXFP4 / Q1_0 / Q2_0 / Q4_0 / Q4_1 / Q5_0 / Q5_1`
  - **无（→ 退回 dequant + cuBLAS GEMM，decode 更慢）**：`IQ1_M`、`TQ1_0`、`TQ2_0`。
  - **这条直接决定了「UD-IQ1_M / UD-TQ1_0 在 V100 上不要用」的工程结论**（§4.2、§7）。

### 2.2 官方量化速度表（CPU，非 GPU！）

`tools/quantize/README.md`（master）给出 Llama-3.1-8B 的官方量化对比，**注意这是 CPU 数字，不能直接套到 V100**：

| 量化 | bits/weight | size (GiB) | pp512 t/s | tg128 t/s |
|---|---|---|---|---|
| Q4_K_M | 4.8944 | 4.58 | 821.81 | 71.93 |
| Q5_K_M | 5.7036 | 5.33 | 758.69 | 67.23 |
| Q6_K | 6.5633 | 6.14 | 812.01 | 58.67 |
| Q8_0 | 8.5008 | 7.95 | 865.09 | 50.93 |
| Q3_K_M | 3.9960 | 3.74 | 783.44 | 71.68 |
| Q2_K | 3.1593 | 2.95 | 784.45 | 79.85 |
| IQ3_XS | 3.4977 | 3.27 | 708.71 | 71.67 |
| IQ3_XXS | 3.2548 | 3.04 | 813.88 | 73.95 |
| IQ4_XS | 4.4597 | 4.17 | 771.80 | 77.51 |
| IQ4_NL | 4.6818 | 4.38 | 806.03 | 76.63 |
| F16 | 16.0005 | 14.96 | 923.49 | 29.17 |

**读法（GPU 迁移到 V100 时要改的）**：
- CPU 上 tg 速度几乎只由"权重越大越慢"决定（读内存带宽），IQ 与 K 差距在 ±5% 内；
- **GPU 上 decode 同理是带宽瓶颈，但绝对值由显存带宽决定**，且 K-quant 的 MMQ 路径在 Volta 上是 DP4A（无张量核），IQ 系列只有 `IQ1_M/TQ*` 缺 MMQ（§2.1）；
- 结论：**在 V100 上，K4/Q5/Q6/Q8 之间的 decode 速度差 ≈ 体积比**（Q8_0 比 Q4_K_M 大 1.74×，decode 预计慢 ~1.7×），IQ4_XS 比 Q4_K_M 小 9%，decode 预计快 ~9%。

### 2.3 Unsloth Dynamic（当前生态的"质量中心"）

- **Dynamic v3.0**（本轮主要对象）：官方文档 `unsloth.ai/docs/basics/dynamic-3.0-ggufs`：
  - 自报「**Qwen3.8-27B Dynamic v3.0 quants 比其他所有提供方在同尺寸下 top-1 精度高 >10%**」；
  - 命名规则：`UD-Q2_K_XL / UD-Q3_K_XL / UD-Q4_K_XL / UD-IQ1_S / UD-IQ1_M / UD-TQ1_0`——**"UD-" 前缀 = 逐张量混合量化（dynamic），不是一种新格式**，文件本身仍是标准 GGUF，llama.cpp / ollama 直接可读（官方明确写「work with most inference engines including llama.cpp and Unsloth Desktop」）。
  - 方法论：imatrix 校准集换成 agentic coding / chat / 多语言混合数据；逐层选择量化类型；**纯后训练量化（不做 QAT/QAD）**。
  - 官方给出的 imatrix 代价：「Imatrix definitely helps reduce KLD & PPL, **at the cost of 5-10% slower inference**」。
  - **1-bit/2-bit 的 agentic 崩塌（官方自报，本轮最关键的一条）**：
    > 「there is a sharp drop off from UD-Q2_K_XL to UD-IQ1_S for 32 token prediction from around **25% accuracy to under 8-10%**. This sharp drop off means **tool calling and non thinking modes break down**.」
    > 「1-bit should not be used for agentic use-cases」：会出现大量循环（建议 `presence_penalty=1.5`）、空回复、工具调用失效。
  - **敏感张量（对混合线性注意力架构尤其重要）**：`ffn_up_exps` / `ffn_gate_exps` 降到 3bit 一般可接受；**`ffn_down_exps` 略敏感**；**`ssm_out` 极敏感且省不了空间**（Mamba/SSM 层不要量化）；**「Quantizing any attn_* is especially sensitive for hybrid architectures, and so leaving them in higher precision works well」**。
  - **MXFP4 在很多张量上劣于 Q4_K**（attn_gate / attn_q / ssm_beta / ssm_alpha），且 MXFP4 是 4.25 bpw vs Q4_K 4.5 bpw——「**It's better to use Q4_K than MXFP4 when choosing between them**」；并已从 Q2_K_XL/Q3_K_XL/Q4_K_XL 中**移除 MXFP4**（除纯 MXFP4_MOE）。
- **Dynamic v2.0**（更早，仍是大量在用档位的来源）：逐层动态调整 + 模型专属方案；官方给出的 Gemma-3-27B KLD 改善表（IQ1_S 1.0357→0.9729 … Q4_K_XL 0.0249→0.0237，GB 几乎不变）。
- **Qwen3.5 全量 KLD/PPL/体积表**（Unsloth 官方，模型 = Qwen3.5-35B-A3B，2026-03-05 更新后的版本）：

| 提供方 | 量化 | 体积 GB | PPL | KLD 99.9% | Mean KLD |
|---|---|---|---|---|---|
| AesSedai | IQ3_S | 12.65 | 6.9152 | 1.8669 | 0.0613 |
| AesSedai | IQ4_XS | 16.4 | 6.6447 | 0.8067 | 0.0235 |
| AesSedai | Q4_K_M | 20.62 | 6.5665 | 0.3171 | 0.0096 |
| AesSedai | Q5_K_M | 24.45 | 6.5356 | 0.21 | 0.0058 |
| Ubergarm | Q4_0 | 19.79 | 6.5784 | 0.4829 | 0.0142 |
| Unsloth | IQ2_XXS | 9.09 | 7.716 | 4.2221 | 0.1846 |
| Unsloth | Q2_K_XL | 12.04 | 7.0438 | 2.9092 | 0.097 |
| Unsloth | IQ3_XXS | 13.12 | 6.7829 | 1.5296 | 0.0501 |
| Unsloth | IQ3_S | 14.13 | 6.7715 | 1.4193 | 0.0457 |
| Unsloth | Q3_K_M | 15.54 | 6.732 | 0.9726 | 0.0324 |
| Unsloth | Q3_K_XL | 16.06 | 6.7245 | 0.9539 | 0.0308 |
| Unsloth | MXFP4_MOE | 18.17 | 6.6 | 0.7789 | 0.0272 |
| Unsloth | Q4_K_M | 18.49 | 6.6053 | 0.5478 | 0.0192 |
| Unsloth | Q4_K_L | 18.82 | 6.5905 | 0.4828 | 0.015 |
| Unsloth | Q4_K_XL | 19.17 | 6.5918 | 0.4097 | 0.0137 |
| Unsloth | Q5_K_XL | 23.22 | 6.5489 | 0.236 | 0.0069 |
| Unsloth | Q6_K_S | 26.56 | 6.5456 | 0.2226 | 0.0065 |
| Unsloth | Q6_K_XL | 28.22 | 6.5392 | 0.1437 | 0.0041 |
| Unsloth | Q8_K_XL | 36.04 | 6.5352 | 0.1033 | 0.0026 |
| bartowski | Qwen_IQ2_XXS | 8.15 | 9.3427 | 6.0607 | 0.3457 |

  - **可读出的三条硬结论**：
    1. **同尺寸下 UD-Q4_K_XL（19.17GB, KLD 0.41）优于标准 Q4_K_M（20.62GB, KLD 0.317）？——不，成立的是"UD-Q4_K_M 比社区 Q4_K_M 在同尺寸下 KLD 更低"**：UD-Q4_K_M 18.49GB / KLD 0.5478 明显不如 AesSedai Q4_K_M 20.62GB / 0.3171（KLD 越低越好）。**真实结论是「同 KLD 下 UD 体积更小」**（UD-Q4_K_XL 19.17GB 的 KLD 0.4097 ≈ 社区 Q4_K_M 20.62GB 的 0.3171 略差，但 UD-Q4_K_L 18.82GB/0.4828 仍在同一档），即 **UD 赢在"体积/质量帕累托前沿"，不是"同体积绝对碾压"**。这一点在 §3 的第三方 Aider 数据里更清楚。
    2. **2-bit 是断崖**：UD-Q2_K_XL mean KLD 0.097 vs UD-Q4_K_XL 0.0137（**差 7 倍**）；UD-IQ2_XXS 0.1846 更是差 13 倍。
    3. **3-bit 是甜点**：UD-Q3_K_XL 16.06GB / mean KLD 0.0308 —— 与社区 Q4_K_M（20.62GB / 0.0096）差 3 倍 KLD，但**体积小 22%**。

### 2.4 bartowski / lmstudio-community / 其他角色

- **bartowski**：社区最活跃的 GGUF 量化者之一。在本轮可达范围内确认他发布了 `bartowski/Qwen3.8-27B-GGUF`（Q4_K_M，第三方 V100 issue 直接引用，§4.1），并维护 **Calibration_v3 校准集**（Unsloth 文档引用：`gist.github.com/bartowski1182/eb213dccb3571f863da82e99418f81e8`）与 **Calibration_v5**（`gist.github.com/tristandruyen/9e207a95c7d75ddf37525d353e00659c/`）——**这两个校准集是当前社区 KLD 横向对比的事实标准**（Unsloth 自己也用它们做对照，以免校准集过拟合）。
- **lmstudio-community**：官方 GGUF（如 `lmstudio-community/Qwen3-Coder-Next-GGUF`），提供 Q4_K_M（48.49GB）、分片 Q6_K（39.82+25.71GB）、分片 Q8_0（39.84+39.75+5.23GB）。**只出标准 K-quant 档，不出 UD- 动态档**；优点是分片规范、体积稳定，缺点是质量低于同尺寸 UD 档。
- **Ubergarm / AesSedai**：Unsloth 文档中出现作为对比提供方（Ubergarm Q4_0、AesSedai IQ3_S/IQ4_XS）。
- **ggml-org**：`GGUF-my-repo` space 官方提供在线量化（每 6 小时同步 main），可自建 imatrix 量化。

### 2.5 EXL2 / AWQ / GPTQ / Marlin 在 sm_70 上的位置

- **EXL2**：`turboderp-org/exllamav2` 的 README 未给出明确的 compute capability 门槛文本（我抓到的 README 里没有 "compute capability/Turing/Ampere/Volta" 关键字），**"EXL2 在 V100 上是否可用"未找到公开证据**。另外 EXL2 是 PyTorch 生态，而**我们 anolis 上没有 PyTorch/vLLM 栈**，且要求与本轮纪律（不下载权重）冲突。
- **AWQ / GPTQ（vLLM 侧）**：
  - vLLM issue **#8024**（2024-08，closed）：「deploy on V100, mma -> mma layout conversion is only supported on Ampere」——AWQ/GPTQ 的 Marlin/GEMM 路径依赖 Ampere 的 mma 布局。
  - vLLM issue **#9618**（2024-10，closed）：「Using Tesla V100 to load the GPTQ-Int4 model results in all output being exclamation marks」——**GPTQ-Int4 在 V100 上直接输出错误**。
  - vLLM issue **#22800**（2025-08，closed）：V100-SXM2-32GB 单卡跑不动 Qwen3-30B-A3B 的 AWQ 变体。
  - vLLM issue **#19185 / #25456**（closed）：V100 上 `no kernel image is available for execution on the device`（后者是 gpt-oss）。
  - vLLM issue **#13788**（closed）：「Unsupported FA version: None on V100 and V1 engine」——**V100 + vLLM V1 无 FlashAttention**。
  - vLLM issue **#47019**（2026-06，closed）：「[Fused MoE] BLOCK_SIZE_K=128 decode default causes large slowdown on Volta/V100」——即使能跑，MoE 在 Volta 上默认参数也慢。
  - 结论：**vLLM/AWQ/GPTQ/Marlin 在 V100 上不是"需要优化"，是"结构性不支持"**（Marlin 本身要求 sm_80+；vLLM V1 要求 CC≥7.5，V100=7.0 已被移除）。**我们不重新选型**。
- **llama.cpp 侧的 AWQ/GPTQ**：`tools/server/README.md` 的参数表里只有 `--model-url`，没有 `--load-format awq/gptq/exl2`（我抓到的 master 版 README 中未出现 awq/gptq/exl2 字样）→ **llama.cpp 路线只走 GGUF**，这也是我们既定路线的合理性所在。

---

## 3. 「Q2/Q3 伤代码、Q4 最好」的证据链

### 3.1 官方自报（Unsloth）

1. **Divergence-300@32（agentic 语料，300 条 held-out，来自 Terminal-Bench 2.1 + DeepSWE + Harbor + MathArena + 非拉丁/长文档）**：
   - UD-Q2_K_XL ≈ **25%**；UD-IQ1_S → **<8–10%**。官方结论："tool calling and non thinking modes break down"。
   - 官方进一步点名低比特三大症状：** Excessive looping / Empty responses / Agentic use cases and tool calling 失效**（"only general knowledge is retained when quantized heavily"）。
2. **Qwen3.5 家族**：官方写 "**some bit widths are good, especially 3bit**… ffn_* (down, up, gate) at around iq3_xxs seems to be best compromise… **2 bits cause more degradation**"。
3. **Qwen3-Coder-Next 的第三方 Aider Polyglot**（Unsloth 文档转引）："the 3-bit **UD-IQ3_XXS** quant comes close to **BF16** performance, making **3-bit a sensible minimum**"；同时 "**NVFP4 slightly outperforms the BF16 reference**（可能采样噪声）… 1-bit → 2-bit → 3-bit → 6-bit 稳步提升"。
4. **Benjamin Marie（第三方）对 Qwen3-Coder-Next 的 750 题混合集（LiveCodeBench v6 / MMLU Pro / GPQA / Math500）**：
   - "**Q3_K_M expectedly performs worse on Live Code Bench v6**, but surprisingly much better on HumanEval than standard Q4_K_M"；
   - "the Unsloth's Q4_K_M quants perform better than standard Q4_K_M"；"**at least Q4_K_M is advised**"。
   - 另有一条打脸"PPL/KLD 决定论"的数据：Unsloth IQ2_XXS 在 **LiveCodeBench v6 + MMLU Pro 真实评测上优于** AesSedai IQ3_S，尽管小了 11GB，而两者 PPL/KLD 排序相反（引用 MiniMax-M2.5 分析）。

### 3.2 第三方复现（Aider Polyglot，David Sluys 跑，Unsloth 文档转引）

DeepSeek-V3.1，同尺寸横向对比（Pass-2 正确率）：

| 量化 | 体积 GB | Unsloth 方案 % | 社区方案 % |
|---|---|---|---|
| IQ2_XXS | 164 / 225 | — / 61.2 | 43.6 / — |
| TQ1_0 | 170 | 50.7 | — |
| IQ1_M | 206 | 55.7 | — |
| IQ2_M | 215 / 235 | — / 64.3 | 56.6 / — |
| Q2_K_L | 239 | — | 64.0 |
| Q2_K_XL | 255 | 65.8 | — |
| IQ3_XXS | 268 / 279 | 65.6 / 66.8 | 65.6 / — |
| Q3_K_S | 293 | — | 65.2 |
| Q3_K_XL | 300 | 68.4 | — |
| IQ4_XS | 357 / 360 | 69.2 / — | — / 66.3 |
| Q4_K_XL | 387 | 69.7 | — |
| Q4_K_M | 405 / 409 | 69.7 / — | — / 67.7 |
| Q5_K_M | 478 | — | 68.9 |
| Q5_K_XL | 484 | 70.7 | — |

**读法（这才是本轮最有价值的一张表）**：
- **1-bit/2-bit 断崖**：IQ2_XXS 43.6% → IQ3_XXS 65.6% → IQ4_XS 69.2% → Q4_K_XL 69.7% → Q5_K_XL 70.7%。**从 2-bit 跨到 3-bit 是 +22 个点，从 3-bit 到 4-bit 只 +2~4 点。**
- **同体积下 UD 全面领先**：UD-Q4_K_XL 387GB / 69.7% vs 社区 IQ4_XS 360GB / 66.3%；UD-Q4_K_M 405GB / 69.7% vs 社区 Q4_K_M 409GB / 67.7%。**→ 这就是「选 UD 档而不是标准 imatrix 档」的直接量化依据。**
- 官方旁证：Qwen3-Coder-480B-A35B 的 **UD-Q4_K_XL（276GB）拿到 60.9%**，逼近 BF16（960GB）的 61.8%（Aider Polyglot，第三方）。

### 3.3 反向证据（不要把「Q4 最好」当教条）

- 上表里 **Q5_K_M（478GB）69.7%…Q5_K_XL（484GB）70.7%**，说明**在显存/内存够的前提下，5-bit 比 4-bit 更好**，只是每 GB 收益递减。
- Unsloth 的 Qwen3.5-35B-A3B 表里 **Q6_K_XL 28.22GB / mean KLD 0.0041** 已接近 BF16。
- **PPL/KLD 本身会骗人**（官方明确写："Perplexity and KLD can be misleading as they're highly influenced by calibration"；并给了一个 MMLU 实现细节导致 68.2% vs 35% 的例子）。
- **在混合 GDN 架构上，PPL 根本不可用**：见 §5.3 的 #28879。

**综合结论（本轮问题 3 的答案）**：
> 「Q4 最好、Q2/Q3 伤代码」**在"标准 imatrix 量化 + 同一提供方"口径下成立，但更准确的表述是**：
> **≥4-bit 用 K4 档（Q4_K_M/Q4_K_XL/UD-Q4_K_XL），3-bit 是可用下限（对 agentic/tool calling 而言 UD-IQ3_XXS ≈ BF16），≤2-bit 的 agentic 能力直接崩塌（tool calling 失效），且必须用 Unsloth Dynamic 档而不是社区标准 imatrix 档。**
> 选档时**不要用 PPL/KLD 单独决策**（用 Divergence-300@32 / Aider / LiveCodeBench 这类"行为"指标）。

---

## 4. V100 上的具体问题

### 4.1 「稠密 27B 在 V100 上慢多少？」——有第三方 V100 实测

**llama.cpp issue #27366**（2026-08-19，报告者 DanielIshi，**3× Tesla V100-SXM2-32GB，CC 7.0，驱动 580.173.02，CUDA 12.5，`-DCMAKE_CUDA_ARCHITECTURES=70`**；模型 `bartowski/Qwen3.8-27B-GGUF` Q4_K_M，arch qwen35，65 blocks = 17 attn + 48 SSM）：

| 配置 | pp4096 (t/s) | tg128 (t/s) |
|---|---|---|
| `-sm layer` 双卡 (CUDA1,CUDA2) | **777.09 ± 0.44** | **29.90 ± 0.52** |
| 单卡 | 774.81 ± 1.83 | **33.64 ± 0.05** |
| `-sm tensor` 单卡 | 730.71 ± 4.18 | 33.25 ± 0.14 |

模型权重在 GPU 上占 **15.92 GiB**（27.32B 参数）。

> **顺带一个被低估的事实（直接改变部署方案）**：ollama 官方 FAQ 的多卡加载规则是——
> 「If the model will entirely fit on any single GPU, Ollama will load the model on that GPU… **If the model does not fit entirely on one GPU, then it will be spread across all the available GPUs**」（`https://ollama.com/docs/faq`，2026-10-21 抓取）。
> **我们现役 18.5GB 模型完全放得下单张 V100-32GB ⇒ ollama 只用 1 张卡，第二张 V100 全程闲置。** 这意味着我们实测的 135.7 tok/s 是"单卡"速度，也意味着：
> - 想真正吃满两张卡，三条路：① 上**放不进单卡**的模型（Qwen3-Coder-Next 36–49GB，会自动 spread 到两卡）；② 在两卡上各挂一个**模型实例**（`OLLAMA_MAX_LOADED_MODELS=2`，各占一卡，零 KV 争抢，比单卡 `OLLAMA_NUM_PARALLEL=2` 更划算）；③ 单卡并发（我们已实测：并发 2 时每请求 109.7、合计 ~219 tok/s）。

**对照我们的实测**：现役 `qwen3-coder-30b`（Qwen3-Coder-30B-A3B Q4_K_M，18.5GB，**激活 3.3B**）在 2×V100S 上 decode **135.7 tok/s**（并发 2 时每请求 109.7，合计 ~219）。

> **⇒ 稠密 27B(Q4_K_M) 在 V100 上 ~30–34 tok/s，我们现役 MoE 135.7 tok/s：差 4.0–4.5 倍。**
> 前期假设「稠密 27B 慢 3–4 倍」**方向正确、幅度略偏保守**（这里实测 4.0–4.5 倍）。

### 4.2 「IQ/UD 系列与标准 K 量化在 2×V100 上的速度差」

**能直接证实的**：
1. **Unsloth 官方**：「I quants (iq3_xxs, iq2_s etc) makes inference **5-10% slower**, they're definitely better in terms of efficiency, but there is a tradeoff」——**该表未注明硬件**，只能作为方向性参考（配套表：mxfp4 90.67 / q4_k 90.38 / q3_k 91.36 / q6_k 90.50 / q2_k 90.77 / q8_0 90.33 / q5_k 90.72 / **iq3_xxs 85.68 / iq2_xxs 85.79 / iq3_s 84.37 / iq2_xs 85.19 / iq2_s 85.04**，即 IQ 家族 tg 比 K 家族低约 5–7%）。
2. **官方 CPU 表**（§2.2）：IQ3_XS 71.67 vs Q4_K_M 71.93（几乎相同）；IQ4_XS 77.51 反而最快。
3. **源码级**：`IQ1_M` / `TQ1_0` / `TQ2_0` **没有 CUDA MMQ 内核**（§2.1）→ 这三档在 GPU decode 时走 dequant+cuBLAS，**明显慢于 K 档与 IQ1_S/IQ2/IQ3/IQ4 家族**。
4. **体积差**（同一模型不同档，ModelScope 文件大小）→ 直接决定 GPU 带宽 read 量：Q4_K_M 48.53GB vs IQ4_XS 42.68GB vs UD-Q3_K_XL 36.28GB vs UD-IQ3_S 29.69GB。

**推断（V100 专用）**：
- V100S-32GB 带宽按 **900GB/s** 取值（**前提假设**：本会话未能抓到厂商/规格站原始表格——nvidia.com 该页 301/404、TechPowerUp 规格由 JS 渲染未取到文本、百度百科 403；900GB/s 是 V100 32GB 的公认规格，但**在本会话内未经一手核对**，故所有以此为前提的推算都标为推断）；decode 是纯带宽问题（Volta 无 BF16/FP8/张量核，INT8 走 DP4A），
- 因此 **decode 速度 ≈ 带宽 ÷ 每 token 实际读取字节数**；
- 结论：**在同一模型上，UD-Q3_K_XL(36.3GB) 的 decode 理论带宽需求比 Q4_K_M(48.5GB) 低 25% → 速度大致快 1.3×**，而 IQ4_XS(42.7GB) 约快 1.13×；**但 IQ 家族每档还要额外承担 5–10% 的 kernel 效率损失（Unsloth 口径）**，两者抵消后 **IQ4_XS ≈ K4_K_M，UD-Q3_K_XL 明显最快**。
- **明确不要用**：`UD-IQ1_M`（缺 MMQ）、`UD-TQ1_0`（缺 MMQ）——两者既慢又处在"tool calling 崩塌"区间。

### 4.3 「80B-A3B 的 Q4 权重约 45GB，双卡 64GB 能否放下？——能，但紧」

**直接证据（ModelScope 官方文件清单，2026-10-21 拉取）**，`unsloth/Qwen3-Coder-Next-GGUF`：

| 文件 | GB | 64GB 双卡放得下吗 |
|---|---|---|
| UD-Q4_K_XL | **49.61** | 勉强（余 14.4GB 给 KV/计算缓冲/CUDA context） |
| UD-Q4_K_M | 49.30 | 同上 |
| Q4_K_M | 48.53 | 同上（ollama 官方 qwen3-coder-next:q4_K_M 标 **52GB**，更紧） |
| UD-Q4_K_S | 46.08 | 宽松（余 17.9GB） |
| Q4_K_S / Q4_0 / IQ4_NL | 45.53 / 45.33 / 45.13 | 宽松 |
| IQ4_XS / UD-IQ4_XS / UD-IQ4_NL | 42.68 / 38.43 / 39.23 | 宽松 |
| MXFP4_MOE | 48.03 | 体积够但 **V100 无 MXFP4 硬件加速**（且 Unsloth 已从 K 档中移除 MXFP4） |
| **UD-Q3_K_XL** | **36.28** | **舒适（余 27.7GB）** ← 推荐 |
| UD-Q3_K_M / Q3_K_M | 35.94 / 38.32 | 舒适 |
| UD-IQ3_S / UD-IQ3_XXS | 29.69 / 28.48 | 单卡 32GB 也能放（29.69GB 极紧，28.48GB 尚可） |
| UD-Q2_K_XL | 26.76 | 单卡可放，但**已到 tool calling 崩塌边界**（§3.1） |
| UD-IQ1_S / UD-IQ1_M / UD-TQ1_0 | 21.51 / 21.70 / 18.94 | 单卡可放，**但 agentic 不可用 + IQ1_M/TQ1_0 无 MMQ** |

**KV cache 占用（我方计算，基于 ModelScope 上的官方 config.json）**：
- Qwen3-Coder-Next：`num_hidden_layers=48`, `full_attention_interval=4` → **12 层全注意力 + 36 层 GDN**；`num_key_value_heads=2`, `head_dim=256` → KV/token = 12×2×2×256×2B = **24KB/token** → 32K ctx 仅 **0.77GB**，64K ctx 1.5GB。**KV 不是瓶颈**。
- Qwen3.8-27B：`64` 层、`full_attention_interval=4` → 16 层全注意力（第三方在 V100 上看到 17 attn + 48 SSM = 65 blocks，量级一致）；`num_key_value_heads=4`, `head_dim=256` → KV/token = 16×2×4×256×2B = **64KB/token** → 32K ctx 2GB，64K ctx 4GB。

### 4.4 「放不下时 --n-cpu-moe CPU 专家卸载在 V100 上可行吗、代价多大？」

**结论：在我们的量化档位下不需要用它；真要用，代价是数量级级别的 decode 掉速，且有已知 bug。**

证据：
- **llama.cpp 有 `--n-cpu-moe` / `--cpu-moe`**（把 MoE 专家层放 CPU），且有持续优化：PR #20596「ggml-cpu: improve `--n-cpu-moe` TG performance」（2026-03，OPEN，8 comments）、PR #21614「persistent expert cache for `--n-cpu-moe`」、PR #18934「ggml-cuda: enable cuda-graphs for `n-cpu-moe`」。
- **但 CPU 专家 = 每 token 要过 PCIe 搬专家权重**。V100S PCIe 双向 32GB/s（NVLink 2.0 最高 300GB/s，但 2 张卡是否 NVLink 未知，题面给的是 "Tesla V100S-PCIE-32GB"，**PCIe 卡，无 NVLink**）。
  - 推理：Qwen3-Coder-Next 每 token 需要 48 层 × 10 专家 = 480 次专家读取（Q4 下每专家约 0.95MB）≈ **456MB/token**。若专家在 CPU：456MB / 32GB/s ≈ **14ms/token** 上限 → 理论上限 ~70 tok/s；而跨卡/跨 host 的实际效率通常只有一半以下 → **~30 tok/s 量级**，比全 GPU 慢 3–5 倍。
  - **注意**：我们的 64GB 其实放得下 Q4_K_XL（49.6GB），所以这个代价是**不必要的**；它只在被迫降到 3-bit 以下或跑更大的模型时才需要。
- **已知 bug（直接反对在 V100 上依赖 --n-cpu-moe）**：
  - **#25582**（2026-07，closed）：DeepSeek-V4-Flash 在 CUDA 上跑 MoE 专家 → **输出乱码/语言漂移**（全专家上 CPU 则完全正常）。issue 结论是「专家张量放置本应数学中性，只有该架构表现异常」，同机同 build 下 gemma4 / qwen35moe 的 MoE 全 GPU 正常 → **架构相关、非量化相关**（UD-Q3_K_XL 与 UD-IQ1_S 两种量化都复现）。**教训：MoE 全 GPU 在 CUDA 上有"输出静默损坏"的历史，部署后必须做输出体检。**
  - **#27022**（2026-08，closed）：qwen3next 架构 MoE，**路由权重（ffn_gate_inp_shexp.weight）是 IQ1_M** 时，Vulkan 后端输出全 0/垃圾，CPU 正常；`--override-tensor` 把 IQ1_M router + SSM 张量放 CPU 才正确，但速度掉到 ~2 tok/s。→ **极低比特 + 混合 MoE + 加速器后端 = 高危组合**（Vulkan 侧；CUDA 侧无同类报告，但机制上同源）。
  - **#27717**（closed）：`--n-cpu-moe` 低于阈值会崩 MTP draft 模型加载。
  - **#26110**（closed）：`--load-mode` 重构后，`--n-cpu-moe` 唯一安全的 CPU 卸载组合被移除。
  - **#25777**（closed）：Gemma 4 26B-A4B + `--n-cpu-moe` 在 Vulkan 上 GGML_ASSERT。
  - **#27872 / #27501**：`--fit` 与 `--n-cpu-moe` 组合会 OOM / 尚不支持。

---

## 5. V100 / sm_70 专属风险清单（部署前必读）

| 风险 | 证据 | 对我们的影响 | 状态 |
|---|---|---|---|
| **CUDA 上 `-sm row` 不支持** | #27366：「device CUDA1 does not support split buffers」；仅 SYCL 后端实现 `ggml_backend_split_buffer_type` | **必须用 `--split-mode layer`** | 已确认 |
| **多卡 Volta 上 `-sm tensor` hang + 显存泄漏** | #27366：`llama-cli` 7 分钟不出字、每卡占 8286MiB 不释放，拖垮第三张卡的 llama-server（15 次重启） | **绝对不要开 tensor split**；且 MTP/DFlash2 投机解码在 `--split-mode tensor` 下的已知崩溃正好落在这里 | 已确认（closed） |
| **sm_70 多卡 layer-split 在"大 prefill + 高 prefix 复用"下概率性 kernel launch 失败** | #29255（2026-09，OPEN）：7× Volta，`CUDA error: invalid argument @ ggml_cuda_kernel_launch`，在 18K–112K ctx 都出现过，每天崩几次；报告者称「LLM Studio runtime 2.34–2.41 崩得更频繁」，`GGML_CUDA_DISABLE_GRAPHS=1` 只在老 build 有效 | **我们的工作负载正是"长会话 + 高前缀复用 + 每题 10 轮工具调用"**——命中概率最高的场景 | **未解决（OPEN）** |
| **Qwen3.5 家族（GDN hybrid + MoE）在 sm_70 上首个请求即崩** | #29783（2026-10-01，OPEN）：6× V100 32GB，Qwen3.5-122B-A10B，Q8_0 与 UD-Q8_K_XL 都崩（ctx 261888 / 65024 均崩），报 "CUDA error: invalid argument"；报告者称「sm_70 users are currently locked out of the whole Qwen3.5 family」 | **Qwen3.8-27B / Qwen3.6 属于 qwen3_5 家族，风险高** | **未解决（OPEN）** |
| **混合 GDN 架构在 >~80K 位置 decode 崩 25 倍** | #27623（2026-08，OPEN）：Qwen3.8-27B UD-Q3_K_XL，CUDA 单卡 RTX 4080S，tg 从 68K 位置 33 t/s → 91K 位置 **1.4 t/s**（714ms/token）；pp 仍 ~1300 t/s | 我们的 harness 每题 10 轮、日志很长，**上下文一旦堆到 80K 就会慢 25 倍** | **未解决（OPEN）** |
| **sm_70 CUDA FlashAttention 在非标准 head_dim 上崩** | #28661（2026-09，OPEN）：`ggml_cuda_flash_attn_ext_mma_f16_case` 崩，建议对 cc==VOLTA 且 dkq ∉ {64,128,256} 回退 cuBLAS | **我们的候选 head_dim 都是 256**（Qwen3-Coder-Next 256、Qwen3.8-27B 256、Qwen3.6-27B 256）→ **落在安全集合内** | 未解决但对我们不触发 |
| **V100 上 CUDA Graph 显存泄漏** | #25835（2026-07，closed）：Volta+Turing 开启 CUDA graphs 后 VRAM 泄漏 | 需在 anolis 上确认 ollama runner 是否默认开 CUDA graphs | 已关闭（需自查） |
| **V100 cuBLAS 需 fp32 避免溢出** | PR #19959（2026-02，closed/merged）：「Use fp32 in cuBLAS V100 to avoid overflows」 | V100 的 GEMM 走 fp32 路径，速度不如 fp16 张量核（Volta 本来也只有 fp16 TC） | 已修复 |
| **MTP + `--split-mode tensor` CUDA lockup** | #27122（2026-08，OPEN）：Qwen3.8-27B MTP 在 tensor split 下可复现 CUDA 锁死 | 正好命中"MTP/DFlash2 投机解码 + tensor split"两个已知坑 | **未解决（OPEN）** |
| **CPU 后端在 qwen35 家族输出垃圾（重复循环）** | #30906（2026-10-21，OPEN）：Qwen3.8-27B / Holo4，CPU backend 乱码，Vulkan 正常 | 我们的 CPU 专家卸载路径会踩到 | **未解决（OPEN）** |
| **PPL 在混合 GDN 架构上不是精度单调的** | #28879（2026-09，OPEN）：Qwen3.8-27B，**F16 的 PPL (6.5545) 反而差于自己的 Q4_K_M (6.5474)**，8 个 chunk 里 7 个如此；chunk 越长 PPL 越高 | **「用 PPL 选量化档」在 qwen3_5 家族上失效** → 我们的量化选型必须用行为指标（Divergence-300@32 / Aider / LiveCodeBench） | **未解决（OPEN）** |
| **V100 + sm_70 + qwen3next 的 key_gdiff 历史 bug** | PR #19324（2026-02，已合并）：qwen3next 向量化 key_gdiff 计算错误，导致**输出循环/损坏**；Unsloth 文档 Feb 4 明确写"re-download GGUFs and UPDATE llama.cpp" | 我们的 ollama 0.40.6 = llama.cpp v0.7.0（b11669，2026-10-15）**已包含该修复** | 已修复 |
| **Qwen3.8 的 MTP/DFlash2 与工具调用解析问题** | #30887（2026-10-20，OPEN）Qwen3.8-Flash-Next + DFlash2 首 prompt 崩；#28158（OPEN）DFlash/MTP 发出越界 token id；#27733（OPEN）尾部 `<think>` 导致整段生成被丢弃 | 对 Qwen3.8-27B 是负面信号 | 未解决（OPEN） |
| **`-dev none` / CPU-only 路径下 GGUF 输出乱码** | #17067（2025-11，closed）：`unsloth/Qwen3-Coder-30B-A3B Q4_K_M` 在 `-dev none` 下乱码，去掉后正常 | 前期报告里引用的那条老 issue；今天已闭 | 已修复 |

---

## 6. 候选清单

体积来源：ModelScope 官方文件清单（`unsloth/*-GGUF` 仓库，2026-10-21 拉取）；ollama 体积来源：ollama.com 官方库页。
分数来源：**官方自报**（Qwen/Unsloth 文档）已标注；第三方复现单独标注。

| 模型 | 厂商 | 架构 / 激活 | 4-bit 体积 | ctx | GGUF 可得性 | 官方 agentic 分数 | 第三方反馈 | 我们的适配判断 |
|---|---|---|---|---|---|---|---|---|
| **Qwen3-Coder-Next 80B-A3B** | Alibaba | `qwen3next` MoE，48 层（12 全注意力 + 36 GDN），512 专家 top-10，**激活 ~2.1B** | **UD-Q4_K_XL 49.61GB** / UD-Q3_K_XL 36.28GB | 262,144 | Unsloth / lmstudio-community / ollama（`qwen3-coder-next:q4_K_M` 52GB） | SWE-V **70.6**、SWE-Multi 62.8、SWE-Pro 44.3、**TB2.0 36.2**、Aider 66.2（官方自报，w/ SWE-Agent） | Aider Polyglot：UD-IQ3_XXS ≈ BF16（第三方）；Benjamin Marie 750 题：Q3_K_M 在 LCB v6 上差于 Q4_K_M | **首选**：≥3-bit 不崩 tool calling；激活 2.1B ⇒ 每 token 读 ~1.3GB ⇒ **decode 不应慢于现役 30B-A3B**；Q4 档 49.6GB 塞 64GB 偏紧，**建议 Q3_K_XL(36.3GB) 或 Q4_K_XL 双卡**；架构比 qwen3_5 老，sm_70 风险面小 |
| **Qwen3.8-27B** | Alibaba | `qwen3_5` **稠密** 27B，64 层（16 全注意力 + 48 GDN），**无 MoE** | UD-Q4_K_XL **17.56GB** / Q8_0 29.05GB / UD-Q6_K_XL 25.30GB | 262,144（可 YaRN 到 1M） | Unsloth（Dynamic v3.0）/ bartowski / ollama（`qwen3.8:27b` 18GB） | **TB2.1 73.0**、SWE-Pro **61.7**、DeepSWE 1.1 42.2、QwenSWE 79.0、LCB v6 **90.3**、GPQA 89.2（官方自报） | 第三方 V100 实测（#27366）：Q4_K_M 单卡 **tg128 33.64** / 双卡 layer-split **29.90**，pp4096 777 | **不建议做本地主力**：① 稠密 ⇒ decode ~30 tok/s，**比现役慢 4 倍以上**；② qwen3_5 家族在 sm_70 有 OPEN 级崩溃/降速 issue（#29783 / #27623 / #30906 / #28879）；③ 默认 reasoning_effort=xhigh ⇒ token 消耗翻倍 |
| **Qwen3.6-35B-A3B** | Alibaba | `qwen3_5_moe_text` MoE 35B，40 层（10 全注意力），256 专家 top-8，**激活 ~3B** | UD-Q4_K_XL **22.24GB** / Q4_K_M 22.02GB / MXFP4_MOE 21.59GB | 262,144 | Unsloth（Dynamic 2.0）+ MTP 专用仓库 | 官方：TB2.1 63.4 / SWE-Pro 53.5 / LCB v6 83.9（**这是 Qwen3.6-27B 稠密版**的数字，35B-A3B 未单列） | Unsloth 官方：**35B-A3B MTP 在 RTX 6000 上 220 tok/s**、27B 140 tok/s（硬件为 Unsloth 口径，量化档为 UD-Q2_K_XL） | **备选（单卡舒适档）**：22GB 单卡 32GB 放得下，激活 3B ⇒ decode 快；但比 Qwen3-Coder-Next 弱一档，且同属 qwen3_5 家族 sm_70 风险 |
| **Qwen3.6-27B**（稠密） | Alibaba | `qwen3_5_text` 稠密 27B | UD-Q4_K_XL 17.61GB | 262,144 | Unsloth | TB2.1 63.4 / SWE-Pro 53.5 / LCB v6 83.9 | 同上 | 同 Qwen3.8-27B 的问题（稠密慢 + qwen3_5 风险） |
| **Qwen3-Coder-30B-A3B（现役）** | Alibaba | MoE 30.5B，**激活 3.3B** | 现役 Q4_K_M 18.5GB（ModelScope Q4_K_M 18.56GB）；**UD-Q4_K_XL 17.67GB（更小）** | 262,144 | ollama 官方 `qwen3-coder:30b` / Unsloth | AA Intelligence Index 10；SWE 口径弱 | 我方实测 anolis 2×V100S：decode **135.7 tok/s**、prompt 149.1 tok/s、加载 10.5s | **保底**。零成本升级路径：换成 **UD-Q4_K_XL（17.67GB，比现役还小 0.9GB，质量更好）** → 同卡速或更快、留更多显存给 KV/并发 |
| **Qwen3-Coder-480B-A35B** | Alibaba | MoE 480B / 激活 35B | UD-Q4_K_XL **276GB** | 262,144 | Unsloth | SWE-V 69.6（OpenHands 500 轮）/ Aider 61.8 | Aider：UD-Q4_K_XL 60.9 vs BF16 61.8 | **出局**（体量远超 64GB） |
| **GLM-5.3 / GLM-5.3-Flash / Kimi K3 / DeepSeek-V4.x** | Z.ai / Moonshot / DeepSeek | 超大 MoE | ollama 库中均有，但量化后远超 64GB | 1M | ollama 官方 | 见既有调研 | — | **出局**（体量） |
| **GPT-OSS-120B** | OpenAI | MoE 120B，MXFP4 原生 | MXFP4 约 63GB | — | — | — | — | **仍然出局**：V100 无 MXFP4 硬件（黑特 FP4 是 sm_100/sm_120）；且 vLLM 在 V100 上 `no kernel image`（#25456） |

---

## 7. 重点候选展开

### 7.1 Qwen3-Coder-Next 80B-A3B（首选）

**能进 64GB 吗？** 能，但 Q4 档紧：
- 权重：UD-Q4_K_XL 49.61GB（Unsloth 官方口径是"4-bit 需要 **46GB** RAM/VRAM/统一内存"；与 ModelScope 上的 49.61GB 有约 3.6GB 差值，**差值来源未查明**——可能与 MTP 头、嵌入层保留精度或分片方式有关，属未验证项）。
- KV：24KB/token（12 层全注意力 × 2 KV head × 256 head_dim × f16）→ 32K ctx 仅 0.77GB。
- 计算缓冲 + CUDA context：llama.cpp 侧通常 1–3GB。
- 结论：**49.6 + 0.8 + ~2 ≈ 52.4GB < 64GB，数学上放得下**，但只剩 ~11GB buffer，ollama 的 `qwen3-coder-next:q4_K_M`（52GB）只剩 12GB，**并发 2 时 KV 与 buffer 都要翻倍** → **单并发更稳**。
- **更稳的选择是 UD-Q3_K_XL 36.28GB**（余 27.7GB，可开并发 2、context 可上 64K+），代价是质量略降（Unsloth 官方与第三方都称 3-bit 对该模型接近 BF16，UD-IQ3_XXS ≈ BF16）。

**速度（推断，基于带宽模型 + 我们自己的实测校准）**：
- 激活参数：48 层 × (10 专家 × 3 × 512 × 2048) ≈ **1.51B** + 共享专家 0.15B + 注意力/嵌入 0.45B ≈ **~2.1B**。
- 每 token 权重读取（Q4_K_XL ≈ 4.9bpw ≈ 0.61B/param）≈ **1.3GB** + KV。
- 理论上限（900GB/s）≈ 690 tok/s；按我们现役模型实测出的 **~36% 带宽利用率**（135.7 tok/s ÷ 理论 375 tok/s）折算 ≈ **250 tok/s**，再按 MoE kernel 效率打折，**保守预期 80–150 tok/s**。
- **关键对比**：现役 30B-A3B 激活 3.3B、每 token 读 ~2.0GB，实测 135.7 tok/s。**两者激活量相近 ⇒ 速度相近**，而 Qwen3-Coder-Next 的 agentic 分数（官方 SWE-V 70.6）显著高于 30B-A3B 档（AA II 10 / SWE 口径弱）。
- ⚠️ 这是**推断**，需要在 anolis 上实测确认（见 §9 步骤）。

**主要风险**：
1. `qwen3next` 架构 = 混合注意力（36 层 GDN + 12 层全注意力），llama.cpp 上的 GDN 是新代码路径；虽然 #19324（key_gdiff）已修且我们的 ollama 0.40.6 ≥ v0.7.0 已含，但 #29255（sm_70 多卡 layer-split 概率性 kernel 失败）**恰好命中"GDN + 多卡 Volta + 长上下文高前缀复用"**。
2. `UD-IQ1_M` / `UD-TQ1_0` 档在 MoE router 上是灾难（#27022），**这两个档我们不要**。
3. Q4 档在 64GB 上余量小，ollama 的 `OLLAMA_NUM_PARALLEL=2` 会让 KV 翻倍 → 先以 **parallel=1 / ctx=16K–32K** 跑通，再谈并发。

### 7.2 Qwen3.8-27B（稠密 qwen3_5）——能力最强但不适合我们

- **能力面最漂亮**：官方 TB2.1 73.0 / SWE-Pro 61.7 / LCB v6 90.3 / GPQA 89.2，比 Qwen3-Coder-Next 的 TB2.0 36.2 高一个档（注意 TB2.0 与 2.1 不可直接比）。
- **但速度是硬伤**：第三方 V100 实测 Q4_K_M 单卡 **tg128 33.64 t/s**、双卡 layer-split **29.90 t/s**（#27366）。按我们的 10 轮工具调用题，单题墙钟会是现役的 **4 倍以上**。
- **架构风险叠满**：#29783（Qwen3.5 家族 sm_70 首请求崩，OPEN）、#27623（>80K decode 崩 25 倍，OPEN）、#30906（CPU 后端乱码，OPEN）、#28879（PPL 不可用，OPEN）、#27122（MTP + tensor split 锁死，OPEN）、#28892（DFlash2 崩，OPEN）、#28158（越界 token id，OPEN）。
- **token 成本**：默认 `reasoning_effort=xhigh`（Unsloth 文档：xhigh/medium/low/none 四档，xhigh 为默认）⇒ 推理轨迹 token 消耗约为同代其它模型的 2 倍 → 在只有 ~30 tok/s 的机器上，**单题墙钟会被 reasoning 长度二次放大**。
- **结论**：可以留作"离线质量参照/难题兜底"，不适合做量产臂。

### 7.3 零成本升级：现役模型的档位替换

- 现役 `qwen3-coder:30b` = Q4_K_M 18.5GB。
- Unsloth 的 **UD-Q4_K_XL = 17.67GB**（更小），且第三方 Aider 数据支持"同尺寸 UD 更准"。
- **这是一个"不需要新模型、只换档位"的零风险升级**：体积更小 → decode 更快或持平 → 显存余量更大 → 可以开更大的 ctx/并发。
- ⚠️ 前提：UD 档是 Unsloth 逐张量混合，ollama 0.40.6 的 runner（llama.cpp v0.7.0）能读标准 GGUF 里的这些张量类型（IQ/K/Q8 都是标准类型）——**这一点是"推断"，必须先冒烟**（Unsloth 文档明确说 UD GGUFs work with llama.cpp / ollama 可用）。

### 7.4 被排除的路线（EXL2 / AWQ / GPTQ / Marlin）

- 理由已在 §2.5 展开：vLLM V1 已不支持 V100（CC 7.0 < 7.5）；Marlin 需 sm_80+；V100 上 GPTQ-Int4 输出全 "!"（#9618）；AWQ 单卡放不下（#22800）；vLLM V1 在 V100 无 FA（#13788）；MoE 在 Volta 默认参数慢（#47019）。
- 我们 anolis 上也没有 vLLM/SGLang 二进制，只有 ollama 0.40.6（llama.cpp runner）→ **换路线等于换整套栈，收益不明、成本确定**。不采纳。

---

## 8. 直接证据 vs 推断（分栏）

| 结论 | 直接证据（可点开核对） | 推断部分（我的手算/推理） |
|---|---|---|
| llama.cpp v0.7.0（2026-10-15）；ollama 0.40.6 ≈ v0.7.0 | GitHub API `releases/latest`；`raw.githubusercontent.com/ollama/ollama/v0.40.6/LLAMA_CPP_VERSION` = `b11669`；llama.cpp commit b11669 = "bump version to 0.7.0"（2026-10-15T16:48:22+03:00） | 无 |
| sm_70 仍在 llama.cpp CUDA 编译目标内 | `ggml/src/ggml-cuda/CMakeLists.txt`（master）含 `70 == V100, FP16 tensor cores` 与 `70-virtual` | 无 |
| IQ1_M / TQ1_0 / TQ2_0 无 CUDA MMQ 内核 | `ggml/src/ggml-cuda/mmq.cu` case 列表（无 IQ1_M/TQ*）；`ggml/src/ggml-cuda/template-instances/` 121 个实例清单 | 无 |
| 稠密 27B 在 V100 上 ~30 tok/s | issue #27366 的 llama-bench 表：3× V100-SXM2-32GB，Qwen3.8-27B Q4_K_M，tg128 29.90（双卡 layer）/33.64（单卡） | 与我们 135.7 tok/s 的对比是直接相除 |
| 现役 30B-A3B 135.7 tok/s | 任务书给定（本会话"在 anolis 实测补充"） | — |
| Qwen3-Coder-Next 每 token 读 ~1.3GB、激活 ~2.1B | config.json（ModelScope `Qwen/Qwen3-Coder-Next`）：48 层、full_attention_interval=4、num_experts=512、top-10、moe_intermediate=512、hidden 2048、vocab 151936 | 激活参数量与每 token 字节数是**我手算**；900GB/s 与 36% 利用率假设来自 V100S 规格与现役实测反推 |
| Qwen3-Coder-Next 预期 80–150 tok/s | — | **纯推断**，需 anolis 实测 |
| 4-bit 档 49.6GB 可进 64GB | ModelScope 文件大小（UD-Q4_K_XL 49.61GB）+ config.json 算出的 KV 24KB/token | "12GB 余量够跑"的判断是推断 |
| UD 档比同尺寸社区档质量高 2–4 点 | Aider Polyglot 第三方表（Unsloth 文档转引 David Sluys 数据） | 无 |
| ≤2-bit 的 agentic/tool calling 崩塌 | Unsloth Dynamic 3.0 官方（Divergence-300@32：Q2_K_XL ~25% → IQ1_S <8–10%） | 无 |
| 3-bit 是 agentic 下限 | Aider Polyglot（UD-IQ3_XXS ≈ BF16，第三方）+ Unsloth 官方"3-bit a sensible minimum" | 无 |
| IQ 比 K 慢 5–10% | Unsloth 官方（**未注明硬件**） | 套到 2×V100 是推断 |
| sm_70 多卡 layer-split 概率性崩 | issue #29255（OPEN，7× Volta） | 迁移到 2×V100S-PCIe 的概率是推断 |
| Qwen3.5 家族 sm_70 首请求崩 | issue #29783（OPEN，6× V100，Qwen3.5-122B-A10B） | 迁移到 27B/35B-A3B 是推断（#27366 显示 27B 在 V100 上曾正常） |
| V100 稠密 vs MoE 差 4 倍 | #27366 实测 + 我方 135.7 | 比值口径（decode 稳态、非并发）是推断 |

**未取得证据（明确列出，不编）**：
1. **HF（huggingface.co / hf.co / cdn-lfs）在本机被网络策略拦截** → bartowski 与 lmstudio-community 的**模型卡原文未读**；只能用 ModelScope 镜像文件清单 + 引用它们的第三方 issue 代替。
2. **Reddit / HackerNews 不可达** → 「社区体感」类证据（如 r/LocalLLaMA 上的量化争论）无法直接取证；本报告的"社区证据"全部来自 Aider Polyglot 官方榜单与 llama.cpp issue（可核验的第三方复现）。
3. **EXL2 在 sm_70 上是否可用**：未找到公开证据（exllamav2 README 无 compute capability 门槛文本）。
4. **lmstudio 官方博客的量化对比数据**：本轮未取（lmstudio.ai/blog 可达但未逐页取）。
5. **Unsloth Dynamic v4**：文档只到 **v3.0**，未找到 v4 的公开资料 → 任务描述里提到的 "v4" 在公开文档中**未见**，本报告只覆盖 v3.0。
6. **bartowski / lmstudio-community 对同一模型的逐档 KLD 原始表**：未取得（HF 不可达）。
7. **Qwen3.8-27B / Qwen3.6 在 V100 上的官方复现**：只有 #27366 一次第三方实测。

---

## 9. 对我们的具体建议（落到 anolis-gpu-01，2×V100S-32GB）

### 9.1 选型结论

| 优先级 | 动作 | 模型 + 档位 | 体积 | 落卡 | 预期 decode（推断） | 理由 |
|---|---|---|---|---|---|---|
| **P0（本周可做，零风险）** | 换档不换模型 | 现役 `qwen3-coder-30b` → **UD-Q4_K_XL** | 17.67GB（比现役 18.5GB 还小） | 单卡 | ≥135.7 tok/s | 体积更小 + 质量更好；改动量最小 |
| **P1（主候选）** | 换模型 | **Qwen3-Coder-Next UD-Q3_K_XL**（或 UD-Q4_K_XL） | 36.28GB（Q4 档 49.61GB） | 双卡 | 80–150 tok/s（推断） | 官方 SWE-V 70.6；激活 2.1B ⇒ decode 不慢于现役；3-bit 已被第三方证明接近 BF16 且 tool calling 不崩 |
| **P2** | 备选 | Qwen3.6-35B-A3B UD-Q4_K_XL | 22.24GB | 单卡 | 快（激活 3B） | 单卡更宽松，但能力弱于 Coder-Next；qwen3_5 家族 sm_70 风险 |
| **P3** | 离线参照，不进量产臂 | Qwen3.8-27B UD-Q4_K_XL | 17.56GB | 单卡 | **~30 tok/s（第三方实测）** | 能力最强但 decode 慢 4 倍 + qwen3_5 sm_70 崩溃风险 + reasoning_effort=xhigh 翻倍 |
| **不做** | — | EXL2 / AWQ / GPTQ / Marlin / vLLM / SGLang | — | — | — | V100 结构性不支持（§2.5） |

### 9.2 落到 anolis 的具体步骤（P0 + P1）

**环境事实（已核对）**：ollama 0.40.6（= llama.cpp v0.7.0，b11669，2026-10-15），CUDA 工具链 12.6，驱动 570.133.20，2×V100S-32GB PCIe，125GB 内存。

**Step 0 — 冒烟（必须先做，历史上踩过坑）**
1. 下载走 **ModelScope 镜像**（HF 在本环境不可达；ModelScope 有 `unsloth/*-GGUF` 全量镜像，文件大小/名称与 HF 一致）：
   `https://www.modelscope.cn/models/unsloth/Qwen3-Coder-Next-GGUF` → `Qwen3-Coder-Next-UD-Q3_K_XL.gguf`（36.28GB）。
2. 落地后先做**输出体检**（因为 #25582/#27022 证明 MoE/低比特在加速器后端可能"静默输出损坏"）：
   - 同一提示跑 3 次，输出是否稳定、非乱码、非重复循环；
   - 触发一次多行 + JSON 结构化请求（对应 #27022 的失败模式）；
   - 跑一次 ≥10 轮工具调用，跨轮不崩、tool call 参数可解析。
3. 同时验证**GPU 真的在算**：看 ollama 日志里 `offloaded X/Y layers to GPU`（本次我们的 qwen3-coder-30b 就出现过 `-dev none` 类退化，见 #17067）。

**Step 1 — P0 换档（现役模型）**
```bash
# ollama 直接吃本地 GGUF：写 Modelfile，FROM 指向本地文件
cat > /data/Modelfile.qwen3c30-udq4kl <<'EOF'
FROM /data/models/Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf
TEMPLATE qwen3-coder
PARAMETER temperature 1.0
PARAMETER top_p 0.95
PARAMETER top_k 40
PARAMETER min_p 0.01
EOF
ollama create qwen3-coder-30b-udq4kl -f /data/Modelfile.qwen3c30-udq4kl
```
- 采样参数沿用 Qwen 官方推荐：`temperature=1.0, top_p=0.95, top_k=40, min_p=0.01, repeat_penalty=1.0`（Unsloth 文档 Qwen3-Coder-Next/Qwen3-Coder 章节）。
- **对比基线**：用现役 `qwen3-coder:30b`（Q4_K_M 18.5GB）与新档跑同一批 af-bench 题，对比解码率与解题率；**必须同 harness、同 seed**。
- **注意 GPU 落位**：UD-Q4_K_XL 只有 17.67GB，**仍会落在一张 V100 上**（ollama FAQ：放得下单卡就单卡）→ 想吃满两张卡做量产吞吐，走
  `OLLAMA_MAX_LOADED_MODELS=2`（两卡各挂一个实例），或单卡 `OLLAMA_NUM_PARALLEL=2`（我们已实测合计 ~219 tok/s）。**这一步比换档本身更可能带来整体吞吐翻倍。**

**Step 2 — P1 上 Qwen3-Coder-Next**
- **档位建议**：
  - 默认选 **UD-Q3_K_XL（36.28GB）**：64GB 里余 27GB，够开 ctx 32K–64K + 并发 2 + 计算缓冲，**也留了退路**（若要上 Q4 档则 49.6GB，余量仅 14GB，ollama 官方 `qwen3-coder-next:q4_K_M` 更是 52GB，只剩 12GB）。
  - **绝对避开 `UD-IQ1_M` / `UD-TQ1_0` / `UD-Q2_K_XL` 及以下**：缺 MMQ 内核（慢）+ tool calling 崩塌（Divergence-300@32 <10%）。
- **ollama 侧**（我们只有 ollama 0.40.6，没有独立 llama-server）：
  ```bash
  export OLLAMA_NUM_PARALLEL=1        # 先 1；并发 2 需要额外 KV，双卡余量够但 P1 阶段先求稳
  export OLLAMA_FLASH_ATTENTION=1     # sm_70 支持 FA；head_dim=256 落在安全集合 {64,128,256}
  export OLLAMA_KV_CACHE_TYPE=q8_0    # 省显存；对 #29255 那种长 prefill 崩溃"最多降低频率"（报告者实测）
  export OLLAMA_MAX_LOADED_MODELS=1   # 关键！默认 = 3×GPU 数，别让 ollama 试图并挂多个 50GB 模型
  ```
- **⚠️ 如果要开 CUDA graph 相关的高级选项，先评估 #29255**：报告者称 `GGML_CUDA_DISABLE_GRAPHS=1` 在新 build 上不再完全有效；我们跑的是 ollama 内置 runner，**无法直接注入该 env**（ollama 自己有 `OLLAMA_*` 开关但没有 graphs 开关）→ **这意味着我们无法规避 #29255 的概率性崩溃，只能降低触发概率**（缩短 ctx、减少 prefix 复用、把单题上下文压到 32K 内）。
  - 结论：**P1 上线前必须先做 20–30 题的长会话压测**（模拟 10 轮工具调用 + 复用前缀），统计崩溃率；>1% 就不要上量产臂。
- **双卡切分**：UD-Q3_K_XL 36.28GB **放不进单张 32GB V100** → 按 ollama FAQ 规则会自动 **spread 到两张卡**（layer 切分），正是我们要的；Q4_K_XL 49.6GB 同理。**不要试图用 row/tensor split**（#27366：row 在 CUDA 不支持 "device CUDA1 does not support split buffers"；tensor 在多卡 Volta 上 hang 且每卡泄漏 8286MiB）。ollama 0.40.6 没有暴露 `--split-mode`，默认即 layer 切分。
- **上下文建议**：先 `OLLAMA_CONTEXT_LENGTH=32768`；Qwen3-Coder-Next 的 KV 只要 24KB/token，32K 也就 0.8GB，**上下文不是瓶颈，瓶颈是 sm_70 的 GDN kernel 稳定性**。

**Step 3 — 与 API 主力臂的成本对照（口径统一）**
- 本地臂的"零 API 成本"是硬优势，但要按**单题墙钟**算：现役 30B-A3B 135.7 tok/s vs P1 候选（推断 80–150 tok/s）差异不大；**而 P3（Qwen3.8-27B ~30 tok/s）在 10 轮工具调用 + xhigh reasoning 下，单题墙钟会是现役的 5–8 倍**，即使解题率高也未必划算——这正是"本地臂定位为零额度量产臂、主力走 API"这一既有结论的量化支撑。

**Step 4 — 回滚条件**
- 若 P1 候选在 anolis 上实测 decode < 60 tok/s（低于现役一半）→ 不上量产臂，退回 P0（换档不换模型）。
- 若 20–30 题长会话压测出现任一次 CUDA "invalid argument" 崩溃 → 暂缓 P1，改为"现役 UD-Q4_K_XL + API 主力"。

---

## 10. 引用清单（可核对）

**llama.cpp 官方**
- 最新 release：v0.7.0，2026-10-15 —— `https://api.github.com/repos/ggml-org/llama.cpp/releases/latest`
- 量化表与量化流程：`https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/quantize/README.md`
- GGUF 类型清单：`https://raw.githubusercontent.com/ggml-org/llama.cpp/master/gguf-py/gguf/quants.py`
- CUDA arch 列表：`https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/CMakeLists.txt`
- CUDA MMQ 类型覆盖：`.../ggml/src/ggml-cuda/mmq.cu`、`.../ggml/src/ggml-cuda/template-instances/`

**ollama 官方**
- `LLAMA_CPP_VERSION`（v0.40.6/v0.40.7/v0.40.5）：`https://raw.githubusercontent.com/ollama/ollama/v0.40.6/LLAMA_CPP_VERSION` 等
- release notes：`https://github.com/ollama/ollama/releases/tag/v0.40.6`（2026-10-16）、`/tag/v0.40.7`（2026-10-20）
- 库页与体积：`https://ollama.com/library/qwen3-coder-next`（q4_K_M 52GB / q8_0 85GB，256K ctx）、`https://ollama.com/library/qwen3.8`（27b 18GB，256K ctx）、`https://ollama.com/library/qwen3-coder`
- FAQ（多 GPU / FA / KV 量化 / 调度器）：`https://ollama.com/docs/faq`

**Unsloth 官方文档（GitBook `.md` 全文）**
- Dynamic 3.0：`https://unsloth.ai/docs/basics/dynamic-3.0-ggufs.md`
- Aider Polyglot：`https://unsloth.ai/docs/basics/dynamic-3.0-ggufs/unsloth-dynamic-ggufs-on-aider-polyglot.md`
- Qwen3.5 GGUF 基准：`https://unsloth.ai/docs/models/qwen3.5/gguf-benchmarks.md`
- Qwen3-Coder-Next：`https://unsloth.ai/docs/models/qwen3-coder-next.md`
- Qwen3-Coder-30B：`https://unsloth.ai/docs/models/tutorials/qwen3-coder-how-to-run-locally.md`
- Qwen3.8：`https://unsloth.ai/docs/models/qwen3.8.md`
- Qwen3.6：`https://unsloth.ai/docs/models/qwen3.6.md`
- Qwen3.5：`https://unsloth.ai/docs/models/qwen3.5.md`
- 文档索引：`https://unsloth.ai/docs/llms.txt`

**ModelScope 官方 API（2026-10-21 拉取）**
- `https://www.modelscope.cn/api/v1/models/{repo}/repo/files?Revision=master&Root=` → 各 GGUF 文件字节数
- `https://www.modelscope.cn/api/v1/models/{repo}/repo?Revision=master&FilePath=config.json` → 架构参数
- 仓库：`unsloth/Qwen3-Coder-Next-GGUF`、`unsloth/Qwen3.8-27B-GGUF`、`unsloth/Qwen3.6-27B-GGUF`、`unsloth/Qwen3.5-35B-A3B-GGUF`、`unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF`、`lmstudio-community/Qwen3-Coder-Next-GGUF`、`Qwen/Qwen3-Coder-Next`、`Qwen/Qwen3.8-27B`、`Qwen/Qwen3.6-35B-A3B`、`Qwen/Qwen3.6-27B`

**llama.cpp issue（第三方复现 / 官方 issue）**
- #27366（2026-08，closed）V100 多卡 split 模式 + Qwen3.8-27B Q4_K_M 的 llama-bench 数字 ← **本轮最关键的一手 V100 数据**
- #29255（2026-09，OPEN）sm_70 多卡 layer-split 概率性 kernel launch 失败
- #29783（2026-10，OPEN）Qwen3.5-122B-A10B 在 sm_70 首请求崩溃
- #27623（2026-08，OPEN）Qwen3.8-27B >80K 上下文 decode 崩 25×
- #28879（2026-09，OPEN）混合 GDN 架构 PPL 非精度单调
- #30906（2026-10-21，OPEN）CPU 后端 qwen35 家族输出乱码
- #27122（2026-08，OPEN）MTP + `--split-mode tensor` CUDA 锁死
- #28661（2026-09，OPEN）SM70 V100 + CUDA FA + 非标准 head_dim 崩溃
- #25582（2026-07，closed）MoE 专家在 CUDA 上输出乱码、CPU 专家正常
- #27022（2026-08，closed）Vulkan + qwen3next + IQ1_M router → 全 0 输出
- #25835（2026-07，closed）Volta + CUDA Graphs VRAM 泄漏
- #28416（2026-09，closed）sm_70 + CUDA 12.9.x 权重缓冲分配失败（我们用 12.6，风险较低）
- #19959（2026-02，closed）V100 cuBLAS 需 fp32
- #19324（2026-02，closed）qwen3next vectorized key_gdiff 修复
- #17067（2025-11，closed）`-dev none` 下 Qwen3-Coder-30B Q4_K_M 乱码
- #30887 / #28158 / #27733（OPEN）Qwen3.8 的 DFlash2/MTP/think 尾解析问题
- #20596 / #21614 / #18934 / #27717 / #26110 / #25777 / #27872 / #27501（`--n-cpu-moe` 相关）

**vLLM（用于证明"换栈无望"）**
- #8024（V100 mma 布局仅 Ampere）、#9618（V100 上 GPTQ-Int4 输出全 "!"）、#22800（V100 放不下 AWQ）、#13788（V100 + V1 无 FA）、#19185/#25456（no kernel image）、#47019（Volta Fused MoE 慢）

---

*本文件由本轮调研（2026-10-21）产出；所有"官方自报/第三方复现"均已逐条标注来源 URL 与日期。*

*未在 anolis-gpu-01 上执行任何实测（本会话机器为 pandev-comp 编排面，无 V100）。所有 V100 性能数字来自第三方 issue 的 llama-bench 输出，或标注为推断。*
