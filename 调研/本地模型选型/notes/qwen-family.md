# Qwen 系 2025–2026 编码/推理模型全景 · 2×V100S-32GB 本地选型调研

- **调研日期**：2026-10-21
- **调研人**：本地模型选型子代理（Qwen 全家族专项）
- **基线机器**：anolis-gpu-01 = 2× Tesla V100S-**PCIE**-32GB，CC 7.0（sm_70），driver 570.133.22→实测 `570.133.20`，nvidia-smi 报 CUDA 12.8 runtime；125GB RAM；ollama **0.40.6**（`/data/models/bin/ollama`，runner 库在 `/data/models/lib/ollama/`，CUDA 后端 `cuda_v12/libggml-cuda.so`）；无独立 llama-cli / llama-server / vLLM / SGLang。
- **现役模型**：`qwen3-coder-30b` = Qwen3-Coder-30B-A3B-Instruct-Q4_K_M（ollama model layer **18.557 GB**），实测 decode 135.7 tok/s、prompt 149.1 tok/s（num_ctx 8192、2 slot）。
- **本轮交付定位**：本报告是**Qwen 家族全景 + 官方规格核对**专项，兄弟报告 `v100-speed-data.md`（V100 吞吐数据库）与 `chinese-community.md`（中文社区实测）已覆盖速度实测与社区口碑，本报告**不重复**，只做交叉引用 + 补齐它们没做的家族穷举与官方分数核验。

---

## 0. 一句话结论（先给答案）

1. **Qwen3-Coder-Next 确实存在且可本地化**，规格为 **80B 总参 / 3B 激活**（`qwen3_next` 架构，48 层 = 12×(3×Gated DeltaNet + 1×Gated Attention)，512 专家取 10），官方**自带 GGUF**（`Qwen/Qwen3-Coder-Next-GGUF`），**Q4_K_M 官方分片实测合计 48.41 GB**，ollama 的 `qwen3-coder-next:q4_K_M` 是 **51.74 GB**。双卡 64GB（实测可用 64988 MiB）**放得下**，双卡各约 24.1 GiB（25.87 GB），余 ~7.6 GiB/卡给 KV + buffer。
2. **但它不是我们 workload 的最优解**：官方 **Terminal-Bench 2.0 = 34.2 / 36.2**（Terminus2-xml / -json），**明显低于 Qwen3.6-35B-A3B 的 51.5**。我们的 af-bench 含 Terminal-Bench，所以"Coder-Next 更强"只在 SWE-bench 维度成立、在 Terminal-Bench 维度**是倒退**。
3. **Qwen3.8 家族里没有 30B 级、更小激活的本地候选**：Qwen3.8 官方只开源了 **27B（稠密）** 与 **Flash-Next（125B+51B n-gram，装不下）** 与 **2.4T-A95B（装不下）**。**Qwen3.7 只以 API 形态存在（Qwen3.7-Plus, 397B/17B 激活），没有开放权重**。**"Qwen3-Coder-30B-Thinking" 这个型号不存在**（30B 的 thinking 兄弟是通用模型 `Qwen3-30B-A3B-Thinking-2507`，不是 Coder）。
4. **若要在 32GB 卡上找一个"比现役强、激活更少"的 Qwen**，唯一答案是 **Qwen3.6-35B-A3B（35B 总参 / 3B 激活，22.62 GB）**——它**单卡就装得下**（余 ~10 GiB 给 KV），官方 SWE-V **73.4** / TB2 **51.5** / SWE-Pro **49.5** 全面高于现役；但它属于 `qwen3_5_moe` 家族，**在 sm_70 上有一个至今未修的上游崩溃 issue**（见 §5.1），且默认 thinking 会烧 token。
5. **待验证的核心假设：成立。** 「大总参小激活 MoE 在 V100 上比稠密 27B 快」在带宽账上被独立确认：稠密 27.78B @Q4 每 token 要读 ~16.9 GB，30B-A3B 每 token 只读 ~2.3 GB，**差 7.3×**；第三方 V100 实测也显示稠密 27B 约 **30–33 tok/s** vs MoE 30B-A3B **133–136 tok/s**，**约 4.1×**。反面也成立：**80B 级 MoE 的 Q4 不是 45GB 而是 48.4–51.7 GB**（前期文档低估 7–15%），但双卡放得下。
6. **--n-cpu-moe CPU 专家卸载在 V100 上不可作为主路径**：PCIe 实测 **Gen3 x16**（≈15.75 GB/s 理论），Coder-Next 每 token 需搬运的激活专家权重约 0.92 GB ⇒ **天花板 ≤17 tok/s**，比全 GPU 慢 8–10×。它只是"塞进单卡"的应急手段。

---

## 1. 家族全景：官方到底发布了什么（穷举结果）

### 1.1 穷举方法

直接调 HuggingFace 官方 API 拉取 `author=Qwen` 的**全部 469 个 repo**（`https://huggingface.co/api/models?author=Qwen&limit=1000`），再逐个拉 `config.json` 读架构与规格，最后按 `pipeline_tag` / `model_type` / 命名筛出编码与推理线。命令与输出留档：

```bash
export HTTPS_PROXY=http://100.64.0.8:7890   # 本机 mihomo 出口（直连 HF 被 DNS 分流劫持，见 §9 通道说明）
curl -sS "https://huggingface.co/api/models?author=Qwen&limit=1000&sort=lastModified&direction=-1" -o /tmp/qwen_models.json
# → total 469
```

### 1.2 结论：Qwen 系 2025-2026 的"编码/推理开放权重"全集

| 模型 | 发布/更新 | 架构 (model_type) | 总参 / 激活 | ctx | 稠密 or MoE | 官方 agentic 分数 | 官方 GGUF | ollama tag | Q4 体积 |
|---|---|---|---|---|---|---|---|---|---|
| **Qwen3-Coder-30B-A3B-Instruct** | 2025-07-22（卡片 2025-12-03） | `qwen3_moe` | 30.53B / 3.3B | 262144 | MoE 128×8 | SWE-V **51.6**（OpenHands 100 turns，社区引用官方发布值）；Qwen-Code scaffold 口径 **61.4**（本次未定位到可引用的官方原页，标注为转引） | ❌（无官方 GGUF） | `qwen3-coder:30b` | **18.56 GB** |
| Qwen3-30B-A3B-Thinking-2507 | 2025-08-17 | `qwen3_moe` | 30.53B / ~3B | 262144 | MoE 128×8 | 通用推理模型，非 Coder | ❌ | 社区 GGUF | — |
| Qwen3-30B-A3B-Instruct-2507 | 2025-09-17 | `qwen3_moe` | 30.53B / ~3B | 262144 | MoE 128×8 | 通用 | ❌ | 社区 | — |
| Qwen3-VL-30B-A3B-Instruct/Thinking | 2025-11-26 | `qwen3_vl_moe` | ~31.1B / 3B | 262144 | MoE 128×8 | 多模态 | ✅ `Qwen3-VL-30B-A3B-*-GGUF` | `qwen3-vl` | — |
| Qwen3-Omni-30B-A3B-Instruct/Thinking | 2025-09-22 | `qwen3_omni_moe` | ~31.7B | 262144 | MoE | 全模态 | — | `qwen3-omni` | — |
| Qwen3-Next-80B-A3B-Instruct/Thinking | 2025-09-15/17 | `qwen3_next` | 81.33B / 3B | 262144 | MoE 512×10 + 混合注意力 | 通用 | ✅ `Qwen3-Next-80B-A3B-*-GGUF` | `qwen3-next` | — |
| **Qwen3-Coder-Next** | **2026-02-03** | `qwen3_next` | **79.68B / 3B** | 262144 | MoE 512×10 + GDN 混合注意力 | **SWE-V 70.6 / 71.1 / 71.3**；SWE-Multi 62.8；**SWE-Pro 44.3**；**TB2.0 34.2/36.2/30.9/25.8**；Aider 66.2；工具模板泛化 92.7 | ✅ **官方自带** `Qwen/Qwen3-Coder-Next-GGUF` | `qwen3-coder-next:q4_K_M` | **51.74 GB**（官方分片 48.41 GB） |
| Qwen3-Coder-480B-A35B-Instruct | 2025-08-21 | `qwen3_moe` | 480.16B / 35B | 262144 | MoE 160×8 | SWE-V 69.6（500 turns）/ 67.0 | ❌ | `qwen3-coder:480b` | 290 GB（装不下） |
| Qwen3.5-0.8B / 2B / 4B | 2026-03-02 | `qwen3_5` | 0.8 / 2 / 4B | 262144 | **稠密** | — | ❌ | `qwen3.5:0.8b/2b/4b` | 1.32 / 2.68 / 3.32 GB |
| Qwen3.5-9B | 2026-03-02 | `qwen3_5` | 9.65B | 262144 | **稠密** | — | ❌ | `qwen3.5:9b` | 6.55 GB |
| Qwen3.5-27B | 2026-04-24 | `qwen3_5` | 27.78B | 262144 | **稠密** | **SWE-V 72.4 / TB2 41.6 / SWE-Pro 51.2** | ❌ | `qwen3.5:27b` | 17.48 GB |
| **Qwen3.5-35B-A3B** | 2026-04-24 | `qwen3_5_moe` | 35.95B / 3B | 262144 | MoE 256×8+1 | **SWE-V 69.2 / TB2 40.5 / SWE-Pro 44.6** | ❌ | `qwen3.5:35b` | 22.07 GB |
| Qwen3.5-122B-A10B | 2026-04-24 | `qwen3_5_moe` | 125.09B / 10B | 262144 | MoE 256×8+1 | SWE-V 72.0 / TB2 49.4 | ❌ | `qwen3.5:122b` | 81.37 GB（装不下） |
| Qwen3.5-397B-A17B | 2026-04-24 | `qwen3_5_moe` | 403.40B / 17B | 262144 | MoE 512×10 | SWE-V 76.2 / TB2 52.5 | ❌ | — | — |
| **Qwen3.6-27B** | 2026-04-24 | `qwen3_5` | 27.78B | 262144 | **稠密** | **SWE-V 77.2 / TB2 59.3 / SWE-Pro 53.5** | ❌ | `qwen3.6:27b` | 17.77 GB |
| **Qwen3.6-35B-A3B** | 2026-04-24 | `qwen3_5_moe` | 35.95B / 3B | 262144 | MoE 256×8+1 | **SWE-V 73.4 / TB2 51.5 / SWE-Pro 49.5 / SWE-Multi 67.2** | ❌ | `qwen3.6:35b` | **22.62 GB** |
| **Qwen3.8-27B** | 2026-08-14 | `qwen3_5` | 27.78B | 262144 | **稠密** | **TB2.1 73.0 / SWE-Pro 61.7 / NL2Repo 42.3 / DeepSWE1.1 42.2 / QwenSWEBench 79.0 / OSWorld-V 84.3** | ❌ | `qwen3.8:27b` | 17.74 GB |
| Qwen3.8-2.4T-A95B | 2026-08-12 | `qwen3_5_moe` | 2446.18B / 95B | 262144 | MoE 512×10 | — | ❌ | — | — |
| Qwen3.8-Flash-Next | 2026-08-27 | `qwen4_exp` | 125B LLM / 6B 激活 **+ 51B n-gram embedding + 4B MTP** | 262144 | MoE 512×10 + 稀疏 indexer | SWE-Pro 62.5 / DeepSWE 58.7 / SWE-Multi 81.0 / NL2Repo 48.1 / JobBench 55.7 | 社区 | `qwen3.8-flash-next:125b-mlx`（**仅 MLX/macOS，105 GB**） | — |
| Qwen-AgentWorld-35B-A3B | 2026-06-25 | `qwen3_5_moe` | 34.66B / 3B | 262144 | MoE | **世界模型**（环境状态转移预测），非编码模型 | ❌ | — | — |
| **Qwen3.7-Plus** | 仅 API | — | **397B / 17B** | 1M | 闭源 | SWE-Pro 57.6 / TB2.1 64.0 / HLE 34.7 | ❌ **无开放权重** | ❌ | ❌ |
| ~~Qwen3-Coder-30B-Thinking~~ | — | — | — | — | — | **该型号不存在**（官方 HF 目录无此条目） | — | — | — |

**读表要点**

- **Qwen3.5 / 3.6 / 3.8 的 27B 是同一个架构、同一套 text_config**（`qwen3_5_text`，64 层，hidden 5120，inter 17408，24 头/4 KV，vocab 248320，ctx 262144，48 层 linear_attention + 16 层 full_attention），**总参都是 27.78B**。三者是**同一底座的不同后训练版本**，不是新架构。→ 换 3.5→3.6→3.8 拿到的是**分数提升**，不是**架构/速度提升**；速度三者一致（实测见兄弟报告：Qwen3.6-27B 32.9 tok/s、Qwen3.8-27B 33.41 tok/s @V100-PCIE）。
- **Qwen3.5-35B-A3B 与 Qwen3.6-35B-A3B 的 text_config 完全一致**（40 层，hidden 2048，256 专家取 8 + 1 shared，moe_inter 512，30 层 linear_attention + 10 层 full_attention）。**分数差**：3.6 的 SWE-V 73.4 / TB2 51.5 全面高于 3.5 的 69.2 / 40.5。**同尺寸选 3.6。**
- **`Qwen3.8-Flash-Next` 的"125B"只是 LLM 部分**，权重文件合计 180B（125B LLM + 51B n-gram embedding + 4B MTP），且 ollama 官方**只有 MLX 构建**（macOS 专用，105 GB）。在 anolis 上无路可走。
- **`Qwen3.7-Plus` 出现在 Qwen3.8 官方对比表的列头里，但官方 HF 目录中不存在任何 3.7 权重** → **Qwen3.7 是 API-only 型号，不可本地化**。这一点直接回答了任务里的"Qwen3.7"。

### 1.3 官方分数的"可复现性折扣"（重要，影响选型判断）

从 Qwen3.6-35B-A3B 与 Qwen3.5-35B-A3B 官方模型卡的脚注原文（HF README，2026-04-24）：

> SWE-Bench Series: Internal agent scaffold (bash + file-edit tools); temp=1.0, top_p=0.95, **200K context window**.
> Terminal-Bench 2.0: **Harbor/Terminus-2 harness; 3h timeout, 32 CPU/48 GB RAM; temp=1.0, top_p=0.95, top_k=20, max_tokens=80K, 256K ctx; avg of 5 runs.**

以及：

> The model has a default context length of 262,144 tokens. However, because Qwen3.5 leverages extended context for complex tasks, **we advise maintaining a context length of at least 128K tokens to preserve thinking capabilities.**

**我们的实况**：ollama `num_ctx 8192`（2 slot × 8192），V100S 上 64GB 总显存、PCIe Gen3。**官方那些 200K/256K ctx 下的分数，在我们 8K ctx 的 harness 上基本不可复现**；Qwen3.5/3.6/3.8 的 thinking 质量本身依赖长上下文，8K 下 thinking 可能不收敛（兄弟报告 `v100-speed-data.md` §4.2 引 miyagadget 2026-09-04 在 V100-PCIE 上的实测：Qwen3.8 系列 `--reasoning-effort` low/medium/xhigh **三档墙钟完全一样 134–135 s 且"烧满 4096 token 思考预算、从未给出答案"**）。

→ **官方分数的排序可以用来筛"上限"，不能用来排"我们台架上的名次"。** 任何"3.6-35B-A3B 73.4 > Coder-Next 70.6"的结论，必须打折到我们的 8K ctx + ollama 0.40.6 预编译 runner 上重新测。

---

## 2. 重点候选展开分析

### 2.1 【首选探针】Qwen3-Coder-Next（80B-A3B）

**官方规格**（`Qwen/Qwen3-Coder-Next` README + `config.json`，2026-02-03）：

- 架构 `Qwen3NextForCausalLM` / `model_type=qwen3_next`；48 层 = **12 × (3 × (Gated DeltaNet → MoE) + 1 × (Gated Attention → MoE))**
- hidden 2048；Gated Attention 16 Q 头 / 2 KV 头 / head_dim 256；Gated DeltaNet 32 V 头 / 16 QK 头 / head_dim 128
- MoE：**512 专家，取 10**，expert intermediate 512，1 个 shared expert（inter 512）
- ctx **262,144 原生**；**只支持 non-thinking 模式**（不产 `<think>`，`enable_thinking=False` 不再需要）
- 权重 79.68B（由 safetensors 合计 159.36 GB ÷ 2 推得），官方口径"80B 总参 / 3B 激活"
- 采样建议：`temperature=1.0, top_p=0.95, top_k=40`
- **官方自报分数**（技术报告 `qwen3_coder_next_tech_report.pdf`，2026-02-03，Table 3/4/5 + 官方 benchmarks.png）：

| 基准 | Coder-Next | DeepSeek-V3.2 | GLM-4.7 | MiniMax M2.1 |
|---|---|---|---|---|
| SWE-bench Verified (SWE-Agent) | **70.6** | 70.2 | 74.2 | 74.8 |
| SWE-bench Verified (MiniSWE-Agent) | 71.1 | 67.2 | 70.4 | 70.4 |
| SWE-bench Verified (OpenHands) | 71.3 | 72.6 | 70.6 | 71.0 |
| SWE-bench Multilingual (SWE-Agent) | 62.8 | 62.3 | 63.7 | 66.2 |
| SWE-bench Pro (SWE-Agent) | 44.3 | 40.9 | 40.6 | 34.6 |
| **Terminal-Bench 2.0 (Terminus2-json)** | **36.2** | 39.3 | 37.1 | 32.6 |
| Terminal-Bench 2.0 (Terminus2-xml) | 34.2 | 34.8 | 44.9 | – |
| Terminal-Bench 2.0 (ClaudeCode / QwenCode) | 30.9 / 25.8 | – / – | – / 31.5 | 42.7 / 39.3 |
| Aider Polyglot | 66.2 | 69.9 | 52.1 | 61.0 |
| 工具模板泛化（5 个 IDE/CLI 脚手架均值） | **92.7** | 93.7 | 69.9 | 77.3 |

**GGUF 可得性（本轮直接核实）**：`Qwen/Qwen3-Coder-Next-GGUF` 存在（官方仓库，2026-02-04 更新），分片大小：

| 量化 | 分片 GB | 合计 |
|---|---|---|
| Q4_K_M | 15.525 + 14.872 + 14.503 + 3.511 | **48.41 GB** |
| Q5_K_M | 17.814 + 17.480 + 17.226 + 4.191 | 56.71 GB |
| Q5_0 | 17.027 + 16.980 + 16.869 + 4.119 | 54.99 GB |
| Q6_K | 20.245 + 20.250 + 20.120 + 4.914 | 65.53 GB |
| Q8_0 | 26.190 + 26.213 + 26.047 + 6.362 | 84.81 GB |
| F16 | 49.203 + 49.296 + 48.992 + 11.967 | 159.46 GB |

ollama 侧：`qwen3-coder-next:q4_K_M` = **51.742 GB**（model layer），`q8_0` = **84.813 GB**。
→ **前期文档写的"Q4 约 45GB"低估了 7–15%**；且 **q8_0 在双卡 64GB 上放不下**（84.8/2 = 42.4 GiB/卡 > 31.73 GiB/卡）。

**双卡 64GB 装不装得下（精确账）**：
实测可用显存 `ggml_cuda_init: found 2 CUDA devices (Total VRAM: 64988 MiB)`，每卡 `32494 MiB = 31.73 GiB`。

| 项 | 每卡占用 |
|---|---|
| Q4_K_M 权重（51.742 GB ÷ 2） | **24.65 GiB** |
| CUDA context + 计算 buffer（参考现役实测：164/128 MiB + host buffer） | ≈ 0.4 GiB |
| KV cache（qwen3_next 只有 12 层全注意力，2 KV 头 × 256 head_dim × 2 × f16）@2×8192 | ≈ 0.20 GiB |
| **合计** | **≈ 25.3 GiB / 31.73 GiB** |
| **余量** | **≈ 6.4 GiB/卡** → 可把 num_ctx 提到 32768（2×16K，KV ≈0.8 GiB）仍余 ~5.6 GiB |

**能装下。但代价是什么：**

1. **速度不会变快**。按激活权重流量算：Coder-Next 每 token 需读 ≈ (10/512)×77.3B 专家 + shared 0.15B + 注意力 0.6B + GDN 0.9B + embedding 0.31B ≈ **3.5B 参数 × 0.608 B/param ≈ 2.13 GB/token**；现役 30B-A3B ≈ **2.3 GB/token**。**两者每 token 搬的字节几乎一样** → decode 速度量级相同（现役实测 135.7 tok/s）。**"MoE 一定更快"只在"同总参下比"成立；Coder-Next 比现役的优势是能力不是速度。**
2. **多卡 PHB 惩罚**：实测 `nvidia-smi topo -m` 显示 GPU0↔GPU1 = **PHB**（过 PCIe Host Bridge，V100S-PCIe 无 NVLink），PCIe **Gen 3 x16**。48 层边界 × 2 × 2048 × 2 B ≈ 393 KB/token 跨卡，@135 tok/s ≈ 53 MB/s，相对 15.75 GB/s 可忽略 → **不是瓶颈**。
3. **加载更慢**：现役 10.5 s → 预计 25–35 s（权重大 2.8×）。
4. **磁盘**：51.74 GB 新增；叠加保留现役 18.56 GB = 70.3 GB，按运营口径磁盘可扩容。
5. **Terminal-Bench 是倒退**：官方 34.2/36.2，远低于 3.6-35B-A3B 的 51.5。我们的 af-bench 含 Terminal-Bench ⇒ **整体解题率不一定是净涨**。

**我们的裁定**：**它是"能力上限探针"，不是"换装首选"**。理由：Terminal-Bench 倒退 + non-thinking-only（无 thinking 兜底，但也就没有 thinking token 膨胀，**对量产臂反而是优点**）+ 需重下 51.7 GB。

### 2.2 【性价比首选】Qwen3.6-35B-A3B（35B / 3B 激活）

- 规格：`qwen3_5_moe`，40 层，hidden 2048，**256 专家取 8 + 1 shared**，expert inter 512，30 层 linear_attention + 10 层 full_attention，ctx 262144（官方建议 **≥128K 以保住 thinking 能力**）。
- 官方分数：SWE-V **73.4** / SWE-Multi 67.2 / SWE-Pro 49.5 / **TB2.0 51.5** / NL2Repo 29.4 / LiveCodeBench v6 80.4 / GPQA 86.0。
- ollama `qwen3.6:35b` = **22.62 GB**（model 21.718 + projector 0.903）→ **单张 V100S 就装得下，余 ~9.5 GiB 给 KV/buffer**；两张卡可各跑一个独立实例（无跨卡 PHB 惩罚），或单实例 2 slot。
- **第三方 V100 直接实测（兄弟报告已核，本报告交叉确认）**：**98.8 tok/s**（V100-SXM2-32GB，UD-Q4_K_M ~22 GB，thinking ON，ctx 16384，**llama.cpp 源码自编 sm_70**）→ 搬到 V100S-PCIe 约 89 tok/s。**这条实测同时证明 `qwen3_5_moe` 的 Gated DeltaNet 路径在 sm_70 上是能跑出数的**（见 §5.3 的风险辨析）。
- **致命点**：默认 thinking on 且无 `reasoning_effort` 旋钮（Qwen3.6 卡片只有 `enable_thinking` / `preserve_thinking`），8K ctx 下 thinking 可能不收敛 → 兄弟报告引的 miyagadget V100 实测（同款缺陷在 Qwen3.6-27B 上也出现）。
- **我们的裁定**：**第二轮候选，必须带"关 thinking / 限预算"开关单独打榜**，不能和现役直接换装。

### 2.3 【分数天花板但慢到不可用】Qwen3.6-27B / Qwen3.8-27B / Qwen3.5-27B（稠密 27.78B）

- 三者 **text_config 完全相同**（64 层 dense，48 层 linear_attention + 16 层 full_attention），**总参都是 27.78B**。
- 官方分数阶梯：Qwen3.5-27B（SWE-V 72.4 / TB2 41.6）< Qwen3.6-27B（**77.2 / 59.3**）；Qwen3.8-27B 换用 **Terminal-Bench 2.1** 口径（**73.0**）+ SWE-Pro 61.7 + DeepSWE 42.2 + QwenSWEBench 79.0（**注意：Qwen3.8 起官方不再公布 SWE-bench Verified，只给 SWE-bench Pro**）。
- 速度（兄弟报告实测，本报告复算一致）：Qwen3.6-27B **32.9 tok/s**（V100-SXM2）、Qwen3.8-27B **33.41 tok/s**（**V100-PCIE-32GB**，与我们卡型最接近）、Qwen3.8-27B UD-Q4_K_XL Q8 KV 30.57 → MTP draft 41.9。
- **带宽复算（独立验证"3–4 倍"假设）**：稠密 27.78B @Q4 每 token 读 ≈ 27.78B × 0.608 = **16.9 GB**；30B-A3B 每 token 读 ≈ 3.8B × 0.608 = **2.3 GB** → **7.3× 的字节差**；实测比 135.7 / 33.41 = **4.1×**。**假设成立**（实测比带宽比小，因为稠密大矩阵 GEMV 的带宽利用率更高、MoE 有 gather 开销）。
- **我们的裁定**：**不做**。8K ctx + 33 tok/s + thinking 膨胀 ≈ 单题墙钟是现役的 4–8×，与"量产臂"定位冲突。

### 2.4 【明确排除】

| 候选 | 排除理由 | 证据 |
|---|---|---|
| **Qwen3.8-Flash-Next** | LLM 125B + 51B n-gram embedding + 4B MTP ⇒ Q4 远超 64GB；ollama 官方**只有 MLX 构建**（macOS 专用）；且 `qwen4exp` 在 sm_70 上有**多卡 layer-split prefill 确定性崩溃** issue | ollama registry：唯一 tag `125b-mlx` = 105 GB；llama.cpp #29562（2026-09-28，closed 但同族） |
| **Qwen3.8-2.4T-A95B** | 2446B 总参 | safetensors 4892 GB |
| **Qwen3.7-Plus** | **仅 API，无开放权重** | Qwen 官方 HF 目录无 3.7 条目；仅出现在 3.8 官方对比表列头 |
| Qwen3-Coder-480B-A35B | 480B，ollama 290 GB | manifest 实测 |
| Qwen3.5-122B-A10B / 397B-A17B | 81.4 GB / 400 GB+ | manifest + safetensors |
| Qwen-AgentWorld-35B-A3B | 世界模型（环境状态转移），不是编码模型 | 卡片"world model inference"表述 |
| **Qwen3.5-0.8B/2B/4B/9B** | 太小，agentic 能力不足（且 9B 是稠密 hybrid） | 官方未给 agentic 分 |
| GPT-OSS-120B MXFP4 | V100 无 MXFP4 | 前序结论，本轮未复核（属非 Qwen 家族） |

---

## 3. 显存/带宽/成本三张账（落到我们的机器）

### 3.1 显存账（双卡 64GB，实测可用 64988 MiB）

| 候选 | 权重 (GiB) | 双卡各占 (GiB) | 每卡余量 (GiB) | 结论 |
|---|---|---|---|---|
| 现役 qwen3-coder:30b | 17.30 | 8.65（实测 8975.64 + 8548.79 MiB） | 23.1 | ✅ 现状 |
| **qwen3.6:35b** | 21.06 | **单卡 21.06** | **10.7** | ✅ **单卡就够** |
| qwen3.6:27b / qwen3.8:27b | 16.55 | 单卡 16.55 | 15.2 | ✅ 显存最宽裕 |
| **qwen3-coder-next:q4_K_M** | 48.19 | **24.10** | **7.6** | ⚠️ 装得下但贴边 |
| qwen3.5:35b | 20.55 | 单卡 20.55 | 11.2 | ✅ |
| qwen3-coder-next:q8_0 | 78.98 | 39.49 | **负** | ❌ 装不下 |
| qwen3.8-flash-next:125b-mlx | 98 | 49（+51B n-gram 未量化更大） | 负 | ❌ |

### 3.2 带宽账（decode 上限，V100S-PCIe 规格 896–900 GB/s）

> **带宽数字的证据等级**：V100S 规格带宽 900 GB/s 是 NVIDIA 规格表数值，本轮**未能在会话内取到官方 datasheet PDF**（`images.nvidia.com` 与 `resources.nvidia.com` 的 PDF 链接均 404/403）。本机**直接实测**到的是：显存最大频率 **1107 MHz**、512-bit GDDR5（`nvidia-smi -q -d CLOCK`），据此推得 896 GB/s。**下表的 decode 上限以此为基准，属"规格推算"而非实测。**

| 模型 | 每 token 读权重 | 带宽天花板 | 实测（V100） |
|---|---|---|---|
| 30B-A3B（现役） | ≈ 2.3 GB | ≈ 390 tok/s | **135.7**（效率 ~35%） |
| Coder-Next 80B-A3B | ≈ 2.13 GB | ≈ 420 tok/s | 未找到 V100 实测 |
| 35B-A3B（3.6/3.5） | ≈ 1.8 GB | ≈ 490 tok/s | **98.8**（SXM2，效率 ~20%） |
| 稠密 27B | ≈ 16.9 GB | ≈ 53 tok/s | **32.9 / 33.41**（效率 ~62%，大 GEMV 带宽利用率更高） |

**结论**：**MoE 在 V100 上的效率只有稠密的 ~1/2，但每 token 字节少 7.3×，净赢 4.1×**。这解释了"MoE 更快"的机制，也说明**MoE 的浪费在 8K ctx、小 batch 下更明显**（gather/scatter 开销占比高）。

### 3.3 CPU 专家卸载（--n-cpu-moe）的代价（正面回答任务里的反面核查）

llama.cpp master `common/arg.cpp:2771`（本轮直接抓取）：

```
{"-ncmoe", "--n-cpu-moe"}, "N",
  "keep the Mixture of Experts (MoE) weights of the first N layers in the CPU"
{"--moe-cache-mib"}, "N",
  "GPU cache size in MiB for the MoE experts kept in the CPU. with multiple GPUs, it is split among them like the layers (--tensor-split)"
```

**机制**：前 N 层的专家权重常驻 CPU，GPU 只留一个 `--moe-cache-mib` 指定的热门专家缓存；每生成一个 token，命中缓存的专家可直接用，未命中的必须**经 PCIe 从主机内存拉取**。

**我们机器上的代价（实测算式）**：
- PCIe 实测：**Generation 3，Link Width 16x** → 理论 15.75 GB/s，实际约 12–14 GB/s。
- Coder-Next 每 token 需从 CPU 搬运的激活专家权重：10/512 × 77.3B = **1.51B 参数 × 0.608 B/param = 0.92 GB**。
- 纯搬运时间 = 0.92 GB ÷ 12 GB/s ≈ **77 ms/token ⇒ 天花板 ≈ 13 tok/s**（乐观 15.75 GB/s ⇒ 58 ms ⇒ 17 tok/s）。
- **即：CPU 卸载把 Coder-Next 从 ~135 tok/s 打到 ≤17 tok/s，慢 8–10×，与现役 135.7 相比是 8× 倒退。**

**裁定**：`--n-cpu-moe` 在这台机器上**不是"塞进单卡"的经济解**，只是极端兜底。若用它把 Coder-Next 压进单张 32GB 卡，墙钟直接不可接受。**更好的做法是双卡分摊（24.1 GiB/卡，余 7.6 GiB）**。

### 3.4 单题墙钟与成本（我们的 workload：每题约 10 轮工具调用）

设一个 SWE/TB 题的 agent 输出总量为 `T` tokens、harness 固定开销 `H` 秒：

| 方案 | decode tok/s | 假设 T=8K | 假设 T=16K | T=16K 且 thinking ×2 |
|---|---|---|---|---|
| 现役 30B-A3B（实测 135.7） | 135.7 | 59 s + H | 118 s + H | 236 s + H |
| Coder-Next（估 100–135） | ~120 | 67 s + H | 133 s + H | （non-thinking，不适用） |
| 35B-A3B（实测 SXM2 98.8 → PCIe ~89） | ~89 | 90 s + H | 180 s + H | **360 s + H** |
| 稠密 27B（实测 33.4） | 33.4 | 240 s + H | 480 s + H | 960 s + H |

**关键洞察**：
1. **Coder-Next 的 non-thinking-only 反而是量产臂的优势** —— 没有 thinking 膨胀，token 可预测；而 3.5/3.6/3.8 默认 thinking + 8K ctx 可能"烧满预算不收敛"（兄弟报告引 miyagadget V100 实测：3 档 reasoning_effort 墙钟全一样 134–135 s 且从不给答案）。
2. **"解题率提升"要用 8K ctx 打折**：官方 SWE-V 差距（Coder-Next 70.6 vs 现役 61.4 转引 / vs 3.6-35B-A3B 73.4）是在 200K–256K ctx + 5 次平均 + 强脚手架下取得的，**我们 8K ctx 上会显著压缩**。真实差距必须靠 af-bench 实测。
3. **本地臂依然追不上 API 主力**：GLM-5.3-Flash SWE-V 92% @ $0.02/task（前序 `model-pricing.md` §4.2 锚点）。Coder-Next 自报 70.6 距其下限仍差 **~21 分**。**本地臂的定位不变：零 API 成本 + 永不熔断的量产臂，不是打主链路。**

---

## 4. llama.cpp / ollama 侧的支持现状（直接证据）

### 4.1 我们的 ollama 0.40.6 runner **已经包含**全部四个新架构

在 anolis 上对 `/data/models/lib/ollama/libllama.so.0` 做 `strings` 核验，出现的架构名：

```
qwen3moe   qwen3next   qwen35   qwen35moe   qwen4exp   qwen3vlmoe   qwen3tts
```

以及 `qwen35.ssm.v_head_reordered` / `qwen35.rope.mrope_interleaved` / `qwen35moe.image_token_id` 等 **hybrid Gated DeltaNet（SSM）专有 KV 名**。

→ **结论**：ollama 0.40.6 的 llama.cpp **认识** `qwen3_next`（Coder-Next）、`qwen35`（3.5/3.6/3.8-27B 稠密）、`qwen35moe`（3.5/3.6-35B-A3B）、`qwen4exp`（3.8-Flash-Next）四种架构。**"支持" ≠ "在 V100 上正确"**，但至少不需要换引擎版本。

（补充事实：现役模型在 anolis 实测 `offloaded 49/49 layers to GPU`、decode 135.7 tok/s ⇒ **该预编译 CUDA 包确实含可用的 sm_70 kernel**，这一点是 A 级自有事实。）

### 4.2 llama.cpp master 源码里的关键分支（本轮直接抓取 raw.githubusercontent.com/ggml-org/llama.cpp/master）

**(a) Gated DeltaNet 的 MMA 快路径在 sm_70 上是关闭的** —— `ggml/src/ggml-cuda/gated-delta-net-mma.cu`：

```c
// Enable only architectures benchmarked for this schedule. MMA support alone does not imply a speedup.
if (!ampere_mma_available(info.cc) ||
    (info.cc != GGML_CUDA_CC_AMPERE_GA10X && info.cc != GGML_CUDA_CC_ADA_LOVELACE &&
     info.cc != GGML_CUDA_CC_BLACKWELL && info.cc != GGML_CUDA_CC_DGX_SPARK)) {
    return gdn_path::ar;
}
```
（`AMPERE_MMA_AVAILABLE` 在 `common.cuh:293` 定义为 `__CUDA_ARCH__ >= GGML_CUDA_CC_AMPERE`。）
→ **Volta 一律走 `gdn_path::ar`（纯 CUDA core 的 FP32 GDN 实现）**，这解释了兄弟报告里 35B-A3B 在 V100 上只有 98.8 tok/s，以及"双 V100 实验室要自己 forward-port row-per-warp GATED_DELTA_NET 内核才 +4.24%"的现象。

**(b) Flash Attention 在 Volta 上有专门分支**（不是禁区）—— `ggml/src/ggml-cuda/fattn.cu:224`：

```c
// On Volta the GQA optimizations aren't as impactful vs. minimizing wasted compute:
if (cc == GGML_CUDA_CC_VOLTA) { ... }
```
→ **修正一个常见误解**：llama.cpp 的 FA **支持 sm_70**（我们现役 serve log 里 `flash_attn = auto`）。

**(c) qwen3_next 家族拿到过 Volta 专项修复** —— llama.cpp **PR #28888**（已合并，2026-09-14）"CUDA: cuBLAS path for lightning_indexer on Volta"。
→ **qwen3_next（Coder-Next）有 Volta 修复先例；qwen3_5 家族没有。**

---

## 5. 风险清单（按严重度）

### 5.1 🔴 `qwen3_5` 家族在 sm_70 上的**未修上游崩溃**

**llama.cpp issue #29783**（2026-10-01 开，**截至 2026-10-21 仍 open**）：
> "CUDA: Qwen3.5-122B-A10B (Gated DeltaNet) crashes at first request on sm_70 — no prefill progress, instant kernel-launch rejection"

- 报告者环境：**6× Tesla V100 32GB (sm_70)**，Windows 11，driver 582.78，CUDA 12.4，**LM Studio 2.47.0（llama.cpp b11189，预编译 CUDA 包）**，`--split-mode layer` 7 路切分
- 现象：模型加载正常，**第一个请求 2 秒内**死于 `CUDA error: invalid argument, current device: 0, in function ggml_cuda_kernel_launch at common.cuh:1707`；ctx 261888 与 65024 **都崩**；两个独立量化源（Q8_0 / UD-Q8_K_XL）**都崩**；FA on/off、graphs on/off **都崩**
- 报告者原话：*"so sm_70 users are currently locked out of the whole Qwen3.5 family, not just one quant"*
- **上游维护者回复**（本轮读到）：*"I don't have Volta hardware to reproduce this… Could you first try an upstream llama.cpp master build instead of the LM Studio b11189 runtime? Then… run test-backend-ops -b CUDA0 on a single V100… and **load a smaller Qwen3.5 model on a single GPU** to rule out the multi-GPU layer split."*

**与兄弟报告实测的交叉辨析（重要）**：兄弟报告 §4.2 记录 **Qwen3.6-35B-A3B 在单张 V100-SXM2 上跑出 98.8 tok/s**（llama.cpp **源码自编 sm_70**）。把两条并起来，崩溃的触发条件更可能是：
1. **预编译 runtime（LM Studio b11189）** 而非源码自编 → 我们 ollama 0.40.6 的 runner **正属于预编译这一类** ⇒ **风险未解除**；
2. **多卡 layer split** ⇒ 单卡跑 35B-A3B（22.6 GB）**可能绕开**；
3. 模型维度相关（122B 的 H=64/V=64 头 vs 35B 的 H=32）⇒ 小模型可能绕开。

**⇒ 风险归因未确定，但对我们而言结论是明确的：Qwen3.5/3.6/3.8 这条线在 ollama 0.40.6 预编译 runner + 2×V100S 上属于"未验证且有明确 open issue 指向"，必须先做冒烟，冒烟不过就直接放弃。**

### 5.2 🟠 "速度正常但输出损坏"的 CUDA bug（前期已知）

混合线性注意力（Gated DeltaNet）在 llama.cpp 上很新。Qwen3.8-27B 官方结构 = **48 层 linear_attention + 16 层 full_attention**（`layer_types` 实证），Qwen3-Coder-Next = **36 层 GDN + 12 层 Gated Attention**。**两者都属于 GDN 家族**，同族风险一致。**必测项**：多轮工具调用后模型输出是否出现乱码/重复/结构破坏。

### 5.3 🟠 Coder-Next 的 Terminal-Bench 倒退（§2.1 已述）

官方 TB2.0 34.2/36.2 vs 3.6-35B-A3B 的 51.5。**我们的 af-bench 含 Terminal-Bench ⇒ 不能只看 SWE-V 就换装。**

### 5.4 🟡 8K ctx 与官方 128K–256K 口径的落差

官方建议 ≥128K 保 thinking；我们是 8192。**这是所有 3.5/3.6/3.8 候选的系统性折扣项**，也是"官方分数不可直接采信"的原因。

### 5.5 🟡 thinking token 膨胀

Qwen3.8 官方：`reasoning_effort` **默认 `xhigh`**（支持 xhigh/medium/low），`preserve_thinking` 默认开，thinking 默认开。兄弟报告引的 V100 实测显示 3 档墙钟无差别且不收敛。**Qwen3.6 卡片未提供 `reasoning_effort` 旋钮**（只有 `enable_thinking` / `preserve_thinking`）⇒ 3.6 的 token 膨胀**没有官方旋钮可压**，只能靠关 thinking。

### 5.6 🟢 低风险项

- 磁盘不是约束（运营口径可扩容）；51.74 GB 与 18.56 GB 并存需 ~70 GB。
- 主机 125 GB RAM 足以 mmap 51.7 GB 权重。
- 加载时长 25–35 s，不影响 bench 吞吐。

---

## 6. 直接证据 vs 推断（分栏）

### 6.1 直接证据（本轮亲自读到 / 跑过，可复现）

| # | 事实 | 出处（命令 / 文件） |
|---|---|---|
| E1 | Qwen 官方 HF 目录共 **469** 个 repo；**无任何 3.7 权重**；**无 "Qwen3-Coder-30B-Thinking"** | `GET /api/models?author=Qwen&limit=1000` → /tmp/qwen_models.json |
| E2 | Qwen3-Coder-Next 规格：48 层 / hidden 2048 / **512 专家取 10** / 1 shared / ctx 262144 / `qwen3_next` | `GET /Qwen/Qwen3-Coder-Next/raw/main/config.json` |
| E3 | 各模型 safetensors 合计（÷2 得总参）：Coder-Next **79.68B**、30B-A3B 30.53B、3.8-27B 27.78B、3.6-35B-A3B 35.95B、3.8-Flash-Next **180B**、3.8-2.4T-A95B 2446.18B、3.5-122B-A10B 125.09B、3.5-397B-A17B 403.40B、AgentWorld-35B 34.66B | `GET /api/models/{m}?blobs=true` 累加 `.safetensors` size |
| E4 | **3.5/3.6/3.8 的 27B text_config 完全相同**（64 层 / hidden 5120 / inter 17408 / 24-4 头 / vocab 248320 / ctx 262144 / 48 linear + 16 full） | 三份 `config.json` 的 `text_config` 逐字段比对 |
| E5 | **3.5-35B-A3B 与 3.6-35B-A3B text_config 完全相同**（40 层 / 256 专家取 8 / 1 shared / 30 linear + 10 full） | 同上 |
| E6 | 官方 GGUF `Qwen/Qwen3-Coder-Next-GGUF` 分片：Q4_K_M 合计 **48.41 GB**、Q5_K_M 56.71、Q8_0 84.81、F16 159.46 | `GET /api/models/Qwen/Qwen3-Coder-Next-GGUF?blobs=true` |
| E7 | ollama manifest 精确体积：`qwen3-coder-next:q4_K_M` **51.742 GB** / `q8_0` 84.813 GB；`qwen3.6:35b` 22.62；`qwen3.6:27b` 17.77；`qwen3.8:27b` 17.74；`qwen3.5:35b` 22.07；`qwen3-coder:30b` 18.557；`qwen3.8-flash-next:125b-mlx` 105（**仅 MLX**） | `GET https://registry.ollama.ai/v2/library/{m}/manifests/{tag}`（逐 layer size 求和） |
| E8 | Qwen3-Coder-Next 官方分数（SWE-V 70.6/71.1/71.3、SWE-Multi 62.8、SWE-Pro 44.3、**TB2 34.2/36.2/30.9/25.8**、Aider 66.2、工具模板 92.7） | `qwen3_coder_next_tech_report.pdf`（2026-02-03）Table 3/4/5 + `qwenianwen-res.../Qwen3-Coder-Next/benchmarks.png`（图像已读） |
| E9 | Qwen3.6-35B-A3B 官方：SWE-V **73.4** / SWE-Multi 67.2 / SWE-Pro 49.5 / **TB2 51.5**；Qwen3.6-27B：SWE-V **77.2** / TB2 **59.3** / SWE-Pro 53.5；Qwen3.5-35B-A3B：SWE-V 69.2 / TB2 40.5；Qwen3.5-27B：72.4 / 41.6 | HF README 内嵌 HTML 表格，脚本解析（`Qwen/Qwen3.6-35B-A3B` 等） |
| E10 | Qwen3.8-27B 官方：**TB2.1 73.0** / SWE-Pro 61.7 / NL2Repo 42.3 / DeepSWE 42.2 / QwenSWEBench 79.0 / OSWorld-V 84.3；**不公布 SWE-V** | `Qwen/Qwen3.8-27B` README 表格 |
| E11 | Qwen3.8-Flash-Next：125B/6B 激活 **+ 51B n-gram + 4B MTP**；`reasoning_effort` 默认 **xhigh**；`preserve_thinking` 默认开 | `Qwen/Qwen3.8-Flash-Next` README |
| E12 | 官方评测口径：SWE 用 200K ctx；TB2.0 用 Harbor/Terminus-2、3h 超时、32 CPU/48GB RAM、256K ctx、**5 次平均**；Qwen3.5/3.6 建议 **≥128K ctx** 以保 thinking | 同 README 脚注 |
| E13 | **llama.cpp #29783（open，2026-10-01）**：Qwen3.5-122B-A10B（GDN）在 6×V100 sm_70 上**首个请求即**死于 `CUDA error: invalid argument @ ggml_cuda_kernel_launch`；ctx 261888/65024、Q8_0/UD-Q8_K_XL、FA on/off、graphs on/off 全崩；维护者回复要求换 master + 试更小模型单卡 | GitHub issue 页面正文（浏览器读取） |
| E14 | **llama.cpp PR #28888（已合并，2026-09-14）**："CUDA: cuBLAS path for lightning_indexer on Volta" → qwen3_next 家族拿到过 Volta 专项修复 | GitHub PR 页面标题 |
| E15 | llama.cpp GDN 的 MMA 快路径**只对 GA10x/Ada/Blackwell/DGX-Spark 开启**，Volta 一律回退 `gdn_path::ar` | `ggml/src/ggml-cuda/gated-delta-net-mma.cu`（master 原文） |
| E16 | llama.cpp FA **支持 sm_70**（`fattn.cu:224` 有 Volta 专门分支） | `ggml/src/ggml-cuda/fattn.cu`（master 原文） |
| E17 | `--n-cpu-moe N` / `--moe-cache-mib N` 语义 | `common/arg.cpp:2771`、`:2781`（master 原文） |
| E18 | anolis 实测：ollama **0.40.6**；2× V100S-32GB **CC 7.0**、**Total VRAM 64988 MiB**（每卡 32494 MiB）；现役 49/49 层 offload，CUDA0 model 8975.64 MiB / CUDA1 8548.79 MiB，KV 800/736 MiB，`flash_attn = auto` | `ssh anolis`：`/api/version`、`nvidia-smi -q`、`/data/models/ollama-serve.log` |
| E19 | anolis 实测：**PCIe Generation 3，Link Width 16x**；`nvidia-smi topo -m` 显示 **GPU0↔GPU1 = PHB**（无 NVLink） | `ssh anolis`：`nvidia-smi -q -d CLOCK` / `nvidia-smi topo -m` |
| E20 | anolis 实测：ollama runner 的 `libllama.so.0` 含架构名 `qwen3next / qwen35 / qwen35moe / qwen4exp / qwen3moe / qwen3vlmoe`，并含 `qwen35.ssm.v_head_reordered` 等 GDN 专有 KV | `ssh anolis`：`strings libllama.so.0 \| grep -E "^qwen"` |
| E21 | 现役 30B-A3B 官方 SWE-V **51.6（OpenHands 100 turns）** 被社区在官方仓库讨论区引用并追问复现细节 | HF discussions API：`/api/models/Qwen/Qwen3-Coder-30B-A3B-Instruct/discussions/30` |
| E22 | 官方 Qwen3-Coder（480B）SWE-V 图：**69.6%（500 turns）/ 67.0%** | `qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-Coder/swe.jpg`（图像已读） |

### 6.2 推断（本报告的判断，非实测）

| # | 推断 | 依据 | 不确定度 |
|---|---|---|---|
| I1 | Coder-Next 在我们机器上 decode ≈ **100–135 tok/s**（与现役同量级，不更快） | E2 的激活参数配置 + E6 的 Q4 位密度 + E18 的现役带宽效率（~35%） | 中（受 GDN 在 Volta 的 FP32 回退路径影响，可能更低） |
| I2 | Coder-Next Q4_K_M 装双卡后每卡余 **~6.4–7.6 GiB** | E7 体积 ÷ 2 vs E18 的 31.73 GiB/卡，加 KV/buffer 估算 | 低–中（buffer 随 ctx/并发变） |
| I3 | `--n-cpu-moe` 路径天花板 **≤17 tok/s** | E19 的 PCIe Gen3 x16 + E2 的激活专家权重 1.51B×0.608 B/param | 中（取决于 `--moe-cache-mib` 命中率与实际 PCIe 效率） |
| I4 | 稠密 27B 在 V100 上比 30B-A3B 慢 **~4.1×**（实测）/ **~7.3×**（带宽比） | 带宽复算（§3.2）+ 兄弟报告三处独立实测 32.9/33.41/30.57 | 低（实测侧） |
| I5 | Qwen3.5/3.6/3.8 在 ollama 0.40.6 预编译 runner + 2×V100S 上**风险未解除**，需冒烟 | E13 的 open issue + E20 的预编译 runner 同类 + 兄弟报告单卡源码自编 98.8 tok/s 的反证 | 中–高 |
| I6 | 官方分数在 8K ctx 下会**显著压缩**，3.6-35B-A3B vs Coder-Next 的排序可能翻转 | E12（官方 200K/256K 口径）+ E12（≥128K 保 thinking） | 高（必须实测） |
| I7 | Coder-Next 的 non-thinking-only 对量产臂是**净正**（token 可预测、无 thinking 膨胀） | E3/E8（只产 non-thinking） | 中 |
| I8 | V100S-PCIe 相对 V100S-SXM2 带宽/性能差 ≈ -10% | 兄弟报告换算 + PCIe Gen3 实测 vs SXM2 专用通道 | 低–中 |

### 6.3 本轮"未找到公开证据 / 未验证"清单（留白，不得当成已知）

1. **Qwen3-Coder-30B-A3B 官方 SWE-bench Verified = 61.4%** 的**可引用原始页面**：官方博客的分数表是**图片**，HF 卡片与 GitHub README 均无数值表；本轮只拿到 "51.6（OpenHands 100 turns）"（E21 可引）。**61.4 按转引处理。**
2. **Qwen3-Coder-Next 在任何 V100/V100S 上的 decode 实测**：本轮未找到。仅有社区"32GB 卡上 19.5 tok/s、GPU util 10–16%"（兄弟报告 chinese-community §E… 转引集速网）与"需双卡 A6000/4090"的定性反馈。
3. **Qwen3-Coder-Next 官方 GGUF 在 ollama 里体积比官方分片大 3.3 GB 的原因**（51.742 vs 48.411）：未查到 ollama 侧 manifest 元数据说明。推测为 ollama 打包了额外张量或量化版本不同 —— **未验证**。
4. **Qwen3.5/3.6/3.8 的"thinking 预算"参数在 ollama 0.40.6 runner 上是否可用**：ollama 的 Modelfile `PARAMETER` 集合里 `reasoning_effort` / `reasoning_budget` 的透传**未验证**（ollama 只暴露固定参数集；兄弟报告引的 `--reasoning-budget` 是 llama-cli 参数，ollama 侧不可直接设置）。
5. **Qwen3.6-35B-A3B 的官方 SWE-V 73.4 在 8K ctx 下的复现值**：无。
6. **V100S-PCIe 32GB 的官方 datasheet 带宽数字**：本轮取 PDF 失败（404/403），只用本机 `nvidia-smi` 读到的 1107 MHz + 512-bit 推得 896 GB/s。
7. **Qwen3.6-27B / Qwen3.8-27B 在 V100 上的 "MTP 投机解码" 在我们 ollama 0.40.6 上能否开启**：ollama 无该开关，未验证。

---

## 7. 对我们的具体建议（落到 anolis-gpu-01）

### 7.1 决策

| 档位 | 模型 | 动作 | 理由 |
|---|---|---|---|
| **P0（能力上限探针）** | `qwen3-coder-next:q4_K_M`（51.74 GB） | **下、双卡、冒烟、进第二轮 af-bench** | 唯一"3B 激活 + 80B 总参"的官方 Coder 型号；官方自带 GGUF；non-thinking 省 token；**但 TB2 倒退，不能直接换装** |
| **P1（性价比档）** | `qwen3.6:35b`（22.62 GB） | **先只拉 1 个到单卡，冒烟后打榜** | 单卡装得下（余 ~10 GiB）；SWE-V 73.4 / TB2 51.5 双高；**同尺寸里最强**；风险是 thinking 膨胀 + sm_70 open issue |
| **P2（探路，不进生产）** | `qwen3.6:27b` / `qwen3.8:27b`（~17.7 GB） | 只在 af-bench 里跑"分数天花板"对照组，不接流量 | 33 tok/s 太快不了；但能标出"我们 8K ctx 下 SWE-V 到底能到多少" |
| **不做** | `qwen3.8-flash-next` / 2.4T / 3.5-122B / 3.5-397B / Qwen3.7-Plus | — | 装不下 / 无权重 / 非本地 |
| **保底不动** | `qwen3-coder:30b`（现役） | 保留，同时留一条 18.56 GB 的回滚路径 | 唯一有本机实测基线（135.7 tok/s）的模型 |

### 7.2 装法（anolis，ollama 0.40.6）

> **前置判断**：如果 P0/P1 的冒烟在 ollama 0.40.6 上过不了（尤其 #29783 那类 kernel-launch 崩溃），**唯一可靠的绕法是自编 llama.cpp**（兄弟报告已记录：双 V100 实验室就是为 V100 forward-port 了 `GATED_DELTA_NET` 内核才拿到 +4.24%）。**建议提前在 anolis 上准备一份源码自编的 `llama-server`（`GGML_CUDA=ON CMAKE_CUDA_ARCHITECTURES=70`）作为备选引擎**，这是引入 Qwen3.5+ 家族的真实门槛，不是可选项。

```bash
# ---- 0) 先看 anolis 当前 ollama 服务与配置（不要动服务，先只读）
ssh anolis
curl -s http://127.0.0.1:11434/api/version          # 期望 0.40.6
cat ~/.config/ollama/env                            # 现状：OLLAMA_NUM_PARALLEL=2
df -h /data                                          # 需为 51.74GB 新模型腾空间（当前 18G 余 + docker 可回收 135G）

# ---- 1) 磁盘（若 /data 不够，先回收 docker）
docker system df                                     # 确认可回收量
# 保留现役 18.56GB 回滚路径 ⇒ 至少再加 ~55GB

# ---- 2) 拉模型（官方 tag；不要用 :q8_0，双卡放不下）
ollama pull qwen3-coder-next:q4_K_M                  # 51.74 GB
ollama pull qwen3.6:35b                              # 22.62 GB（可选）

# ---- 3) Modelfile：显式拉长 ctx、关 flash 以外的隐性开销、锁采样参数
cat > /data/models/Modelfile.coder-next <<'EOF'
FROM qwen3-coder-next:q4_K_M
# 现役是 2 slot × 8192；Coder-Next 每卡余 ~7 GiB，可放宽到 2 × 16384
PARAMETER num_ctx 32768
PARAMETER num_gpu 999
PARAMETER temperature 1.0
PARAMETER top_p 0.95
PARAMETER top_k 40
PARAMETER min_p 0
EOF
ollama create qwen3-coder-next-local -f /data/models/Modelfile.coder-next
```

**要改的配置点清单**：

| 位置 | 改什么 | 为什么 |
|---|---|---|
| `~/.config/ollama/env` | 保持 `OLLAMA_NUM_PARALLEL=2`；**先不要**加 `OLLAMA_FLASH_ATTENTION=0`（llama.cpp 的 `auto` 在 sm_70 上会自动走支持路径，E16） | 盲目关 FA 可能更慢 |
| `~/.config/ollama/env` | 若 P1（35B-A3B）**单卡**跑：设 `CUDA_VISIBLE_DEVICES=0` 起第二个实例，让 GPU1 跑现役 → **两卡各跑一个模型、零跨卡 PHB 惩罚** | 35B-A3B 只有 22.6 GB，单卡够；这是比双卡切分更优的拓扑 |
| Modelfile `num_ctx` | 32768（2×16384）起，**不要**直接上 262144 | 官方建议 ≥128K 保 thinking，但 V100 上 128K KV + prefill 时间不可接受；先量 8K→16K→32K 的墙钟斜率 |
| 采样 | `temp=1.0 / top_p=0.95 / top_k=40 / min_p=0` | **官方指定**（模型卡 "Best Practices"），不要自创 |
| tool calling | 用 `qwen3_coder` XML 工具格式；**必须**在 harness 里用该模型的 `<tool_call>/<function=>/<parameter=>` 原生格式解析，不要用通用 JSON parser | 官方技术报告专门训练了多种工具模板，Qwen3-Coder-Next 在 5 个 IDE/CLI 脚手架上的模板泛化 92.7（E8），用错格式会掉分 |
| 不要开 | `--split-mode tensor` + 投机解码（MTP/DFlash2） | 前期已知 V100 上的崩溃 issue；Coder-Next 本身无 MTP，但 `qwen3.8-flash-next` 有（且 #29562 正是它） |
| 不要用 | `--n-cpu-moe` | §3.3：≤17 tok/s，比现役慢 8× |

### 7.3 冒烟测试清单（**每个新模型必须全过，缺一不进 af-bench**）

1. **加载**：`load_tensors: offloaded <N>/<N> layers to GPU`（**全部层上 GPU**，出现 CPU 回落即视为不可用）——本轮基线：`offloaded 49/49 layers to GPU`。
2. **显存**：`Total VRAM: 64988 MiB`，两卡 model buffer 各自 ≈ 24.1 GiB（Coder-Next）/ ≈ 21 GiB（35B-A3B），**不得 OOM**。
3. **冒烟提示词**：发一次带 `qwen3_coder` 工具 schema 的请求，确认返回**合法 XML 工具调用**（不是 JSON、不是散文）。
4. **多轮不崩**：连打 **10 轮**工具调用（模拟 af-bench 的 ~10 轮），每轮返回都必须是合法工具调用；**任何一轮输出乱码/重复/结构破坏即判定失败**（§5.2 的 GDN 输出损坏风险）。
5. **Terminal-Bench 单题**：`qwen3-coder-next` 官方 TB2 只有 34.2/36.2 ⇒ **必须**用 Terminal-Bench 跑 ≥ 5 题做 A/B，而不是只看 SWE-V。
6. **thinking 行为**（仅 P1 / 3.6-3.8）：确认 `<think>` 块长度可控；**若出现"烧满预算不给答案"**（兄弟报告 miyagadget 现象）则该模型直接判不可用于量产臂。
7. **速度基线**：单请求 decode tok/s 与 prompt tok/s（对标现役 135.7 / 149.1）；**并发 2** 每请求 tok/s 与合计（对标现役 109.7 / 219）。
8. **加载耗时**（对标现役 10.5 s，预期 25–35 s）。

### 7.4 打榜方法（避免再被官方分数误导）

- 固定 **同一批 30–50 题**（SWE-bench Verified / Terminal-Bench 各半），现役与候选**同题同判分**，同 `num_ctx`、同并发度、同 harness。
- 同时记录**两个数**：①解题率；②**单题墙钟**（含 harness 固定开销，不能只算 token 生成时间）。
- 因为候选（Coder-Next）**不产 thinking**、现役也不产 thinking，但 3.6/3.8 **产 thinking** ⇒ 对 3.6/3.8 必须额外报"**关 thinking**"的一组，否则是在比"思考长度"而不是"解题率"。
- 结论口径：只有"**解题率显著提高 且 单题墙钟不显著变长**"才允许换装；本轮估算 Coder-Next 大概率满足第一项、满足第二项（token 可预测），而 3.6-35B-A3B 满足第一项、**第二项存疑**（thinking 膨胀）。

---

## 8. 与我们前期结论的对照（独立验证结果）

| 前期结论（`设计/benchmark调研/实测/model-pricing.md` §4.2 / `计划/50-bench实测方案.md`） | 本轮裁定 | 依据 |
|---|---|---|
| "本地最强可行选项是 Qwen3-Coder-Next（80B A3B，激活约 3B）Q4 量化双卡 64GB 容纳，自报 SWE-bench Verified 70.6%" | **成立，但需加两条限定**：①官方 Q4_K_M 是 **48.41 GB**（官方分片）/ **51.74 GB**（ollama），不是 45GB；②**Terminal-Bench 只有 34.2/36.2，比 Qwen3.6-35B-A3B 的 51.5 还低**，对我们含 TB 的 workload **不构成全面升级** | E6 / E7 / E8 / E9 |
| "保底选项是 Qwen3-Coder-30B-A3B Q4_K_M 单卡" | **成立**（18.56 GB，双卡各 8.65 GiB，余 23 GiB/卡） | E7 / E18 |
| "GPT-OSS-120B MXFP4 明确不建议（V100 不支持 MXFP4）" | 本轮未复核（非 Qwen 家族），不推翻 | — |
| "llama.cpp 在老卡上有输出乱码与 GPU 未生效的 issue（#17067），部署必须先冒烟" | **仍需保留**；本轮**新增**了更具体的同族风险证据（#29783 的 sm_70 GDN kernel-launch 崩溃） | E13 |
| "本地池定位是弱模型档，产线主力走 API" | **维持**。本轮把"更强"的天花板抬到 SWE-V 70.6（Coder-Next 自报）→ 距 GLM-5.3-Flash 的 92% 仍差 ~21 分 | E8 + 前序 §4.2 锚点 |
| "真正的成本瓶颈是'模型不努力'（浅尝辄止、零补丁），完成度纪律先于绝对能力" | **本轮进一步支持**：Coder-Next 官方明确训练了"长程推理、工具使用、**从执行失败中恢复**"与"多轮工具调用格式合规"（技术报告 §3.2.2 / §4.2.4，工具模板泛化 92.7）⇒ 在"改代码 + 多轮不崩"上它比现役更对路 | E8 |
| 待验证假设："总参大但激活少的 MoE 可能同时更强更快；稠密 27B 在 V100 上解码慢 3–4 倍" | **前半成立、后半成立、但"MoE 更快"要限定**：MoE 相对**同代稠密**确实快 4.1×（实测）；但相对**现役 30B-A3B**（也是小激活 MoE），Coder-Next 的每 token 字节相当 ⇒ **不会更快，只会更强** | §3.2 + E2/E6 |
| 待验证假设："80B 级 MoE 的 Q4 权重约 45GB，双卡 64GB 能否放下" | **45GB 低估**；实为 48.41–51.74 GB；**双卡放得下**（每卡余 ~6.4–7.6 GiB） | E6 / E7 / E18 |
| 待验证假设："--n-cpu-moe CPU 专家卸载在 V100 上可行吗、代价多大" | **机制存在**（`--n-cpu-moe` / `--moe-cache-mib`），但**代价 = 每 token 搬 0.92 GB 过 PCIe Gen3 x16 ⇒ 天花板 ≤17 tok/s，比全 GPU 慢 8–10×** ⇒ **不可作为主路径** | E17 / E19 / §3.3 |

---

## 9. 证据通道说明（可复现）

- 本机直连 huggingface.co / github.com / qwen.ai **被 DNS 分流劫持**（`/etc/resolv.conf` 指向本地 dnsmasq"smartnet DNS 分流"，非国内域名被引到已下线的 hk-gateway），`curl` 直连超时、解析到 Facebook 段 IP。
- **可用通道**：`HTTPS_PROXY=http://100.64.0.8:7890`（本机 mihomo，监听 tailnet 地址而非 127.0.0.1）→ 出口 103.17.98.26（香港）。本轮所有 HF / GitHub API / ollama registry 取证均走此通道。
- 浏览器（ZCode IAB）可直连 GitHub（用于读 issue 全文，因 GitHub REST API 对该出口 IP 触发匿名限流）。
- anolis 侧只读取证（未改动服务）：`/api/version`、`nvidia-smi -q`、`nvidia-smi topo -m`、`/data/models/ollama-serve.log`、`strings /data/models/lib/ollama/libllama.so.0`。**未下载任何模型权重**（遵任务约束）。
- 临时材料（tech report PDF、官方分数图）取完即删，未留档在仓库里；需要复现时按 §11 的 URL 重取即可。

---

## 10. 一页纸速查

| 问题 | 答案 |
|---|---|
| Qwen3-Coder-Next 是什么规模？ | 80B 总参 / 3B 激活，`qwen3_next`（48 层 = 12×(3×GDN + 1×Gated Attention)，512 专家取 10），ctx 262144，只 non-thinking |
| 能本地化吗？ | **能**。官方自带 GGUF（Q4_K_M 48.41 GB），ollama `qwen3-coder-next:q4_K_M` 51.74 GB，双卡各 ~24.1 GiB，余 ~6.4 GiB |
| 但它是"更值得上"的吗？ | **SWE 维度是（自报 SWE-V 70.6 vs 现役 51.6–61.4），Terminal-Bench 维度不是（34.2/36.2 vs 3.6-35B-A3B 的 51.5）** ⇒ 进第二轮打榜，不直接换装 |
| Qwen3.8 家族有 30B 级/更小激活的变体吗？ | **没有**。只有 27B 稠密（27.78B，17.74 GB）、Flash-Next（125B+51B n-gram，装不下且 ollama 仅 MLX）、2.4T-A95B。**Qwen3.7-Plus 仅 API，无权重** |
| Qwen3.5/3.6 家族里 30B 级的？ | **Qwen3.5-35B-A3B / Qwen3.6-35B-A3B**（35B/3B，22.6 GB，**单卡装得下**）。分数：3.6 的 SWE-V 73.4 / TB2 51.5 全面强于 3.5（69.2 / 40.5）⇒ 选 3.6。**但有 open 的 sm_70 崩溃 issue #29783，必须先冒烟** |
| "Qwen3-Coder-30B-Thinking"？ | **不存在此型号**。30B 的 thinking 兄弟是通用模型 `Qwen3-30B-A3B-Thinking-2507` |
| MoE 一定更快吗？ | 相对**稠密**快 4.1×（实测 33 → 135 tok/s）；相对**现役小激活 MoE** 不更快（每 token 字节 2.13 vs 2.3 GB），只更强 |
| --n-cpu-moe 可行吗？ | 机制可行，**代价 ≤17 tok/s**（PCIe Gen3 x16，每 token 搬 0.92 GB）⇒ 只作极端兜底 |

---

## 11. 来源清单

- Qwen 官方 HF 组织目录（469 repo）：`https://huggingface.co/api/models?author=Qwen&limit=1000`
- 官方模型卡 / config：`https://huggingface.co/Qwen/{Qwen3-Coder-Next, Qwen3-Coder-Next-GGUF, Qwen3-Coder-30B-A3B-Instruct, Qwen3.8-27B, Qwen3.8-Flash-Next, Qwen3.6-35B-A3B, Qwen3.6-27B, Qwen3.5-35B-A3B, Qwen3.5-27B, Qwen3.5-122B-A10B, Qwen3.5-397B-A17B, Qwen3-Next-80B-A3B-Instruct, Qwen-AgentWorld-35B-A3B, Qwen3-30B-A3B-Thinking-2507}/raw/main/config.json`
- Qwen3-Coder-Next 技术报告（2026-02-03）：`https://raw.githubusercontent.com/QwenLM/Qwen3-Coder/main/qwen3_coder_next_tech_report.pdf`
- 官方分数图：`https://qianwen-res.oss-accelerate-overseas.aliyuncs.com/Qwen3-Coder-Next/{benchmarks.png,swebench_pro.png}`、`https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-Coder/swe.jpg`
- Qwen 官方博客：`https://qwen.ai/blog?id=qwen3-coder-next`（2026/02/03）、`https://qwenlm.github.io/blog/qwen3-coder/`
- ollama 官方库与 registry：`https://ollama.com/library/{qwen3-coder-next,qwen3.5,qwen3.6,qwen3.8,qwen3.8-flash-next,qwen3-coder}`、`https://registry.ollama.ai/v2/library/{lib}/manifests/{tag}`
- HF 讨论（现役模型 SWE-V 复现追问）：`https://huggingface.co/api/models/Qwen/Qwen3-Coder-30B-A3B-Instruct/discussions/30`
- llama.cpp 上游：**issue #29783**（open，sm_70 GDN 崩溃）、**PR #28888**（merged，Volta lightning_indexer）、`ggml/src/ggml-cuda/gated-delta-net-mma.cu`、`ggml/src/ggml-cuda/fattn.cu`、`ggml/src/ggml-cuda/common.cuh`、`common/arg.cpp`
- anolis 自有实测：`/api/version`(=0.40.6)、`nvidia-smi -q -d CLOCK`、`nvidia-smi topo -m`、`/data/models/ollama-serve.log`、`strings libllama.so.0`
- 兄弟报告（交叉引用）：`调研/本地模型选型/notes/v100-speed-data.md`、`调研/本地模型选型/notes/chinese-community.md`
