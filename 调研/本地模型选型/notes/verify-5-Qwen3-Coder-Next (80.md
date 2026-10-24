# 复核 · 第 5 名 · Qwen3-Coder-Next (80B-A3B)

- **复核日期**：2026-10-21（本轮所有抓取/读取都在该日完成）
- **被复核的原始档案**：`调研/本地模型选型/notes/engines-volta.md`（2026-10-21 出具，368 行）
- **复核对象**：Qwen3-Coder-Next (80B-A3B)；对照：Qwen3-Coder-30B-A3B-Instruct（现役）、Qwen3.8-27B（已否决组）
- **基准机器（全程以此为准）**：anolis-gpu-01 = 2× Tesla V100S-PCIE-32GB（sm_70 / CC 7.0，无 NVLink，PHB 拓扑），driver 570.133.20，CUDA 12.6 工具链，125 GB 内存，ollama 0.40.6
- **纪律**：只核查不改写原结论；数字追到原始出处；查不到写「无法核实」；**本轮未下载任何模型权重**；本轮**没有任何 anolis 实测**（见 §0.3）

---

## 0. 复核结论速览

### 0.1 总判定

**判定：修正（核心方向正确，但 3 条关键结论的证据等级被高估，1 条事实性错误，另有 2 条对 V100 落地有实质影响的遗漏）。**

原档案的一手事实层（模型规格、GGUF 字节数、官方分数、引擎矩阵、llama.cpp 源码级 Volta 路径、vLLM/SGLang/TRT-LLM/TGI 的官方不支持结论）**我逐条复算，全部属实**，质量很高。原档案最大的问题不在事实层，而在**推断层**：它把三处「无实测支撑的推断」写成了接近结论的语气（速度"必然同档"、CPU 卸载"数量级恶化"、ollama 的开关暴露面"未核实"），而且**漏掉了三条本可查到、且方向相反的关键证据**（第三方 Coder-Next 实测、llama.cpp 上 Coder-Next 专属的崩溃/退化报告、现役 30B 在 SWE-bench 官方榜的第三方基线）。

### 0.2 逐条判定

| # | 原档案结论要点 | 判定 | 依据（我本轮实际读到的） |
|---|---|---|---|
| 1 | 模型真实存在，80B 总参 / 3B 激活，48 层，512 专家取 10 + 1 shared，hidden 2048，ctx 262144，Apache-2.0，仅非思考模式 | ✅ **属实** | HF `Qwen/Qwen3-Coder-Next` config.json + README（§1.1） |
| 2 | 官方 GGUF Q4_K_M = 48.40 GB（4 分片），Q5_K_M 56.71 / Q6_K 65.53 / Q8_0 84.81；ollama 库版 q4_K_M = 52 GB | ✅ **属实（字节数逐个复算）** | HF `?blobs=true`（§1.2） |
| 3 | 官方 SWE-V 70.6/71.1/71.3、SWE-Pro 44.3/37.9、SWE-Multilingual 62.8/56.2/64.3、TB2.0 34.2/36.2/30.9/25.8 | ✅ **属实** | 官方技术报告 PDF，`pdftotext -layout` 抽表（§1.3） |
| 4 | SGLang 对 sm_70 硬抛错、TRT-LLM 0.15.0 移除 Volta、TGI 支持列表无 V100、vLLM 0.19 是 V100 末代且 stock 15.6→65.9 / 24.9→173.9 | ✅ **属实（源码/文档/issue 原文复核）** | §2.2 |
| 5 | llama.cpp b11738 有专用 Volta FA 路径、MMQ 走 dp4a、GDN 的 MMA 路径要 Ampere、SSD 快路径要 Turing、70-virtual 仅 CUDA<13 | ✅ **属实（逐行核对，行号微偏）** | §2.1 |
| 6 | 稠密 27B 在 V100 上 tg128 = 33.25 tok/s（现役的 1/4.1） | ✅ **属实** | llama.cpp#27366 原文（§3.1） |
| 7 | 1Cat-LLM 4×V100 TP4 数字 + 环境要求（GLIBC≥2.38 / py3.12 / Torch 2.10+CUDA12.8 / 驱动≥570.124.06 / wheel 未过 manylinux） | ✅ **属实** | 1Cat-LLM README（§2.3） |
| 8 | **"Coder-Next 与现役速度必然同档（1.82 vs 1.83 GB/token）"** | ⚠️ **降级为未验证推断，且证据方向偏负面** | 原档案自己的 3.52 GB/step 反证 + 我新找到的两组第三方实测（§3.2/§3.3）→ 修正 **C1** |
| 9 | **"Qwen3-Coder-30B-A3B 的官方 SWE-V 文本分：未找到公开证据"** | ❌ **不成立** | SWE-bench 官方榜有 5 条第三方提交：60.4 / 52.2 / 51.6 / 49.67 / 45.0 → 修正 **C2** |
| 10 | **"PR #28912：加 DFlash2 投机解码 54.52 → 69.36 tok/s"** | ❌ **因果写错** | 该 PR 是 MMQ/MMVQ crossover 调优在 DFlash2 **已开启**前提下的前后对比 → 修正 **C3** |
| 11 | **"`--n-cpu-moe` 每 token 延迟会增加一个数量级以上"** | ❌ **过度/错误** | 第三方实测：CPU 卸载是 33.7–40.6 tok/s，比纯 GPU 方案只低不是数量级 → 修正 **C4** |
| 12 | **"ollama 0.40.6 是否暴露 `--split-mode`/`--spec-type`：未核实"** | ✅ **可以关闭**（且有实质结论） | ollama v0.40.6 `llm/llama_server.go` 逐行核对 → 修正 **C5** |
| 13 | "双卡 64GB 装得下 Q4_K_M" | ⚠️ **成立但需加两条限定** | 48.41 GB（45.09 GiB）+ KV 0.79 GB(32K) 可行；但 ollama 库版 52 GB 口径不同，且多卡有专属退化报告 → 修正 **C6 / C7** |
| 14 | "Coder-Next 速度证据只有作者自报，V100 上无任何第三方 tok/s" | ❌ **不完整** | 有第三方 tok/s，但**不在 V100 上**：H200 162→247 tok/s（ecto/tang）、RTX4070+内存卸载 33.7–41.2 tok/s（carteakey）→ 修正 **C1** |
| 15 | "Coder-Next 的 agentic 分数无第三方独立复现" | ✅ **属实** | 官方榜 0 命中；GitHub 全站检索无独立复现 → §4.2 |

### 0.3 本轮**没有**做的事（必须写明）

- **没有 anolis 实测**。本会话所在机器是 `pandev-comp`（RTX 3070 Laptop 8GB，ollama 0.35.1），`ssh anolis-gpu-01` 返回 `Could not resolve hostname`（本机 `/etc/hosts` 只有 127.0.0.1 / PanDeveopComp）。因此原档案 §1 的全部 anolis 实测（nvidia-smi / topo / nvcc 链接失败 / ollama /api/tags）**我无法独立复核**，一律标记为「未复核」。
- **没有下载任何模型权重**，没有跑过任何 Coder-Next 推理。
- **没有**在 2×V100 上测过 Coder-Next 的任何 tok/s —— 目前**全世界都没有公开数据**（见 §3.4）。
- 出口可用性实测：`huggingface.co` 与 `api.github.com`（无 UA 时）在本机不可达；`hf-mirror.com` / `modelscope.cn` / `ollama.com` / `raw.githubusercontent.com` / `github.com` HTML 可达。GitHub REST API 需带 `User-Agent: Mozilla/5.0`，且本轮中段触发过 rate limit。

---

## 1. 一手事实核查

### 1.1 模型本体 —— 全部属实

`curl -s https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next` → `downloads 522825 / likes 1703 / created 2026-01-30 / lastModified 2026-02-03 / tags 含 license:apache-2.0 / gated False`。

`config.json`（我下载后逐字段读）：

```
architectures=["Qwen3NextForCausalLM"]   model_type=qwen3_next
num_hidden_layers=48   hidden_size=2048   full_attention_interval=4
num_experts=512        num_experts_per_tok=10   moe_intermediate_size=512
shared_expert_intermediate_size=512   intermediate_size=5120
num_attention_heads=16 num_key_value_heads=2 head_dim=256
linear_num_key_heads=16 linear_num_value_heads=32 linear_value_head_dim=128
max_position_embeddings=262144  vocab_size=151936  torch_dtype=bfloat16
```

模型卡 README 原文核对：
- `Number of Parameters: 80B in total and 3B activated` / `Non-Embedding: 79B` / `Hidden Dimension: 2048` / `Number of Layers: 48` / `Hybrid Layout: 12 * (3 * (Gated DeltaNet -> MoE) -> 1 * (Gated Attention -> MoE))` / `Number of Experts: 512` / `Number of Activated Experts: 10` / `Number of Shared Experts: 1` / `Context Length: 262,144 natively` —— **与原档案完全一致**。
- `**NOTE: This model supports only non-thinking mode and does not generate \`<think></think>\` blocks in its output.**` —— 确认「仅非思考模式」。
- `**Note: If you encounter out-of-memory (OOM) issues, consider reducing the context length to a shorter value, such as 32,768.**` —— 确认官方降级手段是降 ctx。
- `For local use, applications such as Ollama, LMStudio, MLX-LM, llama.cpp, and KTransformers have also supported Qwen3.` —— 确认官方点名 llama.cpp / Ollama / KTransformers。
- 官方部署章节要求 `sglang>=v0.5.8` / `vllm>=0.15.0`；**模型卡正文没有任何 tok/s 数字**（原档案这一点没说错）。

> **下载量/许可的补充**：官方 GGUF 仓库 `Qwen/Qwen3-Coder-Next-GGUF` 的 `downloads 41833 / likes 298 / lastModified 2026-02-04`；safetensors 仓库 40 个分片；许可证 Apache-2.0（`license` 字段与 `LICENSE` 链接均在模型卡 front-matter）。

### 1.2 体积 —— 逐字节复算，全部属实

`curl -s "https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next-GGUF?blobs=true"`，按分片求和：

| 量化 | 官方分片字节数 | 合计 | 十进制 GB | GiB |
|---|---|---|---|---|
| **Q4_K_M** | 15,524,827,040 + 14,872,168,352 + 14,503,294,496 + 3,510,702,144 | **48,410,992,032** | **48.41 GB** | 45.09 |
| Q5_0 | 17,026,609,056 + 16,979,683,232 + 16,869,201,440 + 4,119,425,088 | 54,994,918,816 | 54.99 | 51.21 |
| **Q5_K_M** | 17,813,589,920 + 17,479,501,728 + 17,226,413,600 + 4,190,867,520 | **56,710,372,768** | **56.71** | 52.82 |
| **Q6_K** | 20,245,400,480 + 20,249,793,440 + 20,119,727,648 + 4,913,543,232 | **65,528,464,800** | **65.53** | 61.03 |
| **Q8_0** | 26,190,321,568 + 26,212,935,584 + 26,047,157,792 + 6,361,641,024 | **84,812,055,968** | **84.81** | 78.99 |
| F16 | 49,202,919,520 + 49,296,066,560 + 48,992,048,768 + 11,967,180,896 | 159,458,215,744 | 159.46 | 148.52 |

- 原档案写的「Q4_K_M 48.40 GB（4 shard：15.52+14.87+14.50+3.51）」**逐位吻合**。
- **显存口径修正（见 C6）**：64 GB 显存实际是 2×32768 MiB = **64 GiB = 68.72 GB**。所以 Q4_K_M 官方版只占 45.09/64 GiB，**余 18.9 GiB**（不是原档案写的 ~12 GB，那是十进制混算）；Q5_K_M 占 52.82 GiB，**理论可行但只剩 11.2 GiB** 给 KV + 双卡计算缓冲；Q6_K 61.03 GiB 也不行。
- ollama 官方库（`ollama.com/library/qwen3-coder-next/tags`）：共 **3 个 tag** —— `latest` = `q4_K_M`（digest `ca06e9e4087c`，**52 GB**，256K ctx）、`q4_K_M`（同 digest，52 GB）、`q8_0`（**85 GB**，放不下）。即**唯一可用 tag 就是 52 GB 的 q4_K_M**。52 GB 是十进制 → 48.4 GiB，余 15.6 GiB。

### 1.3 官方分数 —— 属实（我自己抽表）

来源：`https://raw.githubusercontent.com/QwenLM/Qwen3-Coder/main/qwen3_coder_next_tech_report.pdf`（2,647,221 B，PDF 1.5）→ `pdftotext -layout` → 1451 行文本。

- **Table 3（行 726-740）SWE-Bench Verified**，表头 `Model | Size | SWE-Agent | MiniSWE-Agent | OpenHands`：
  ```
  Claude-Opus-4.5        ?    78.2  77.8  79.0
  Claude-Sonnet-4.5      ?    76.0  68.4  74.6
  DeepSeek-V3.2      671A37   70.2  67.2  72.6
  GLM-4.7            358A32   74.2  70.4  70.6
  MiniMax-M2.1       230A10   74.8  70.4  71.0
  Kimi-K2.5         1000A32   73.2  70.8     –
  Qwen3-Coder-Next     80A3   70.6  71.1  71.3
  ```
  表注：`The maximum number of agent turns was set to 300.`
- **Table 4（行 760-772）SWE-Bench Multilingual / SWE-Bench-Pro**：`Qwen3-Coder-Next 80A3 → 62.8 / 56.2 / 64.3`（多语言），`44.3 / 37.9`（Pro）。
- **Table 5（行 843-858）TerminalBench 2.0**，四列 `Terminus2-xml | Terminus2-json | ClaudeCode | QwenCode`：`Qwen3-Coder-Next 80A3 → 34.2 | 36.2 | 30.9 | 25.8`。
- 正文行 793-794 原话：`it achieves scores of 70.6% with SWE-Agent, 71.1% with MiniSWE-Agent, and 71.3% with OpenHands`。
- 行 716 的 RL 观察：`pushing the average number of agent turns from 50 to 130`（原档案引对了）。
- **技术报告里没有 Qwen3-Coder-30B-A3B 的对照行**（我 grep `30B|30-A3B|Coder-30` → 0 命中）。对照组是 Qwen3-Coder-480B-A35B 与 Qwen3-Next。

> **一个原档案漏掉的重要事实**：Terminal-Bench 2.0 里 Coder-Next 的 34.2 是**四个 harness 里最好的那个**；Claude-Opus-4.5 是 58.4/57.3/53.9/51.7，GLM-4.7 是 44.9/37.1/–/31.5。即 Coder-Next 在 TB2.0 上**明显落后于闭源前沿模型**，原档案在表里列了这些数字但没有在结论里点出「Coder-Next 打不过 Opus-4.5」的含义。

### 1.4 对照组：Qwen3-Coder-30B-A3B-Instruct（现役）—— 规格属实

`config.json`：`architectures=["Qwen3MoeForCausalLM"] / model_type=qwen3_moe / num_hidden_layers=48 / hidden_size=2048 / num_attention_heads=32 / num_key_value_heads=4 / head_dim=128 / num_experts=128 / num_experts_per_tok=8 / moe_intermediate_size=768 / max_position_embeddings=262144 / vocab 151936 / bfloat16`。

- 确认**纯注意力 48 层**（无混合线性注意力），128 专家取 8。→ 原档案「现役走的是成熟 qwen3moe 路径，不是 qwen35/qwen3next 混合路径，Volta 风险最低」**成立**。
- **KV 显存（原档案没算，这里补上，方向对 Coder-Next 有利）**：
  - 现役 30B：`48 层 × 4 KV head × 128 head_dim × 2(K,V) × 2 B(f16) = 98,304 B = **96 KiB/token**`
  - Coder-Next：`12 层 × 2 KV head × 256 head_dim × 2 × 2 B = 24,576 B = **24 KiB/token**`
  - → **Coder-Next 的 KV 只有现役的 1/4**。num_ctx 32K 时：0.79 GB vs 3.14 GB；num_ctx 262K 时：6.44 GB vs 25.2 GB。这是 Coder-Next 在 64 GiB 里能开长上下文的**结构性优势**，原档案只把它当"prefill 更快"的边角项。

### 1.5 对照组：Qwen3.8-27B —— 官方分数属实

`Qwen/Qwen3.8-27B`：`downloads 7,586,857 / likes 18,071 / lastModified 2026-08-14 / apache-2.0 / model_type=qwen3_5 / Qwen3_5ForConditionalGeneration`；`text_config`：hidden 5120、intermediate 17408、full_attention_interval 4、layer_types 以 `linear_attention × 3 → full_attention` 循环（与报告一致）。

模型卡原始表格数值：**Terminal Bench 2.1 (Terminus) 73.0**（行 77）、**SWE-bench Pro 61.7**（行 85）、**QwenSWEBench 79.0**（行 109）、**CoWorkBench 70.7**（行 118）、NL2Repo-Bench / DeepSWE 1.1 也在表内。→ 原档案数字**全部属实**；「官方卡未给 SWE-bench Verified」也属实。

`bartowski/Qwen3.8-27B-GGUF?blobs=true`：Q8_0 29,116,388,960 (29.12 GB)、Q6_K 23.86 GB、Q5_K_M 20.92 GB、Q4_K_L 18.82 GB、Q4_1 17.83 GB（Q4_K_M 排第 11 位未打印，约 17.4 GB）→ 与原档案「Q4_K_M 17.44 GB」一致。

---

## 2. V100（sm_70）上到底能不能跑 —— 核查

### 2.1 llama.cpp 路径 —— 原档案的源码级结论全部成立

我在 `ggml-org/llama.cpp` 的 **`b11738`** 提交上逐文件复核（`raw.githubusercontent.com/ggml-org/llama.cpp/b11738/...`）：

| 原档案说法 | 我核到的行 | 判定 |
|---|---|---|
| `70-virtual` 仅 CUDA<13 进默认 arch 列表 | `ggml/src/ggml-cuda/CMakeLists.txt:43` `if (CUDAToolkit_VERSION VERSION_LESS "13")` → `:44` `list(APPEND CMAKE_CUDA_ARCHITECTURES 50-virtual 61-virtual 70-virtual)` | ✅（原写 40-46，实际 43-44） |
| 有专用 Volta FA 路径、`VOLTA_MMA_AVAILABLE` | `common.cuh:286` `#define VOLTA_MMA_AVAILABLE`；`common.cuh:361` `static bool volta_mma_available(const int cc)`；`fattn.cu:224` `if (cc == GGML_CUDA_CC_VOLTA)`；`fattn.cu:672` `if (volta_mma_available(cc) && ...)` | ✅（原写 fattn.cu:223，实际 224） |
| V100 上 `turing_mma_available` 为假 | `common.cuh:365-366`：`ggml_cuda_highest_compiled_arch(cc) >= GGML_CUDA_CC_TURING(750)`，V100=700 → false | ✅ |
| MMQ 只在 `ne11 < 64` 启用，长 prefill 走 cuBLAS | `mmq.cu:423` `return !fp16_mma_hardware_available(cc) || ne11 < MMQ_DP4A_MAX_BATCH_SIZE;`；`mmq.cuh:8` `#define MMQ_DP4A_MAX_BATCH_SIZE 64` | ✅ |
| GDN 的 MMA 整段要 Ampere | `gated-delta-net-mma.cu:59` `#if defined(AMPERE_MMA_AVAILABLE) || (defined(AMD_WMMA_AVAILABLE) && defined(RDNA3))`，`:121`/`:127`/`:363` 同一条件 | ✅ |
| SSD 快速路径要 cc ≥ Turing | `ssm-scan.cu:855` `&& cc >= GGML_CUDA_CC_TURING` | ✅ |
| 架构支持已 GA | `src/llama-arch.cpp:38` `{ LLM_ARCH_QWEN3NEXT, "qwen3next" }`（`:41` qwen35、`:42` qwen35moe）→ Coder-Next 的 `qwen3_next` 架构在 b11738 有正式注册 | ✅（原档案只说 ollama 支持 qwen3next，没给 llama.cpp 侧的架构注册证据，这里补上） |
| 默认切分是 layer | `common/common.h:490` `enum llama_split_mode split_mode = LLAMA_SPLIT_MODE_LAYER;` | ✅ |

**提交时间核对**：`b11738` = `2026-10-19T15:58:14+02:00`（oid f174553e…）；`b11777` = `2026-10-20T22:09:56+03:00`（oid 839a572a…）。原档案给的两处日期都对。

**5 个 Volta 修复**（我逐个拉了 PR 页面）：#28887 `CUDA: enable sparse FlashAttention on Volta`（CLOSED=已合）、#28888 `CUDA: cuBLAS path for lightning_indexer on Volta`（CLOSED=已合）、#28912 `tune MMVQ to MMQ crossover for SM70 (Volta)`（merged 2026-09-21）、#29232 `Cuda: fix fa Volta issue caused by #28536`（CLOSED）、#29803 `CUDA: fix 2 broken Volta FA cases`（**MERGED**）。全部在 2026-10-01 前合入 → **b11738（2026-10-19）必然包含**。原档案这一条成立。

> **无法核实的细节**：我没有在 ollama v0.40.6 源码里找到 `LLAMA_CPP_VERSION` 常量（`.gitmodules` 与 `llm/llama/CMakeLists.txt` 在 v0.40.6 tag 上均 404），因此**「ollama 0.40.6 内嵌 llama.cpp 恰为 b11738」这一条我无法独立核实**。可核实的替代说法：只要 anolis 上 ollama 0.40.6 的 llama.cpp 不早于 2026-10-01，上面 5 个 Volta 修复就一定在。**在 anolis 上直接跑 `ollama run --verbose qwen3-coder-30b "hi"` 看启动横幅里的 llama.cpp commit 即可闭合**（本轮做不到，见 §0.3）。

### 2.2 其他引擎 —— 原档案结论全部成立

- **SGLang**：`python/sglang/srt/model_executor/model_runner_components/load_model_utils.py` —— 函数 `maybe_downgrade_dtype_for_legacy_gpu` 在 `torch.cuda.get_device_capability()[0] < 8` 时降 fp16，随后 `if torch.cuda.get_device_capability()[1] < 5: raise RuntimeError("SGLang only supports sm75 and above.")`，**raise 在第 91 行**（原档案写 78-90）。V100 = (7,0) → minor 0 < 5 → 直接抛错。**sm_70 是死路，成立。**
- **TensorRT-LLM**：`docs/source/release-notes.md` —— `:736` 是 `## TensorRT-LLM Release 0.15.0`，`:759` = `- [BREAKING CHANGE] NVIDIA Volta GPU support is removed in this and future releases.`；`:810` 是 `## TensorRT-LLM Release 0.14.0`，`:823` = `- NVIDIA Volta GPU support is deprecated and will be removed in a future release.`。**版本归属与行号完全对上，成立。**
- **TGI**：`docs/source/installation_nvidia.md:3` 原文 `TGI optimized models are supported on NVIDIA H100, A100, A10G and T4 GPUs with CUDA 12.2+` —— 无 V100。**成立。**
- **vLLM**：issue #47019（2026-06-29 开，2026-07-01 关，标题 `[Performance]: [Fused MoE] BLOCK_SIZE_K=128 decode default causes large slowdown on Volta/V100`）原文：
  - `The focus is vLLM 0.19, because that is the last broadly practical vLLM line for Tesla V100 users.`
  - 环境 `8x NVIDIA Tesla V100-SXM2-32GB`、Volta/sm_70、CUDA 12.6 source build、cudagraph decode
  - 表格：`Qwen3.6-35B-A3B, C1 → stock ~15.6 tok/s → patched ~65.9 tok/s (~4.2x)`；`C8 aggregate ~24.9 → ~173.9 (~7.0x)`；另附 Gemma-4-26B-A4B 10.9→43.7 / 28.3→155.9
  - 根因：`BLOCK_SIZE_K=128` 在 Volta 上 spill，改 64 消除；A/B 输出 bit-identical
  - **注意**：这是**单个用户在 issue 里自报的实测**（附自己的 repo `KumphanartDansiri/vllm-fp8-w8a16-sm70`），不是 vLLM 官方基准。原档案归为「第三方复现」勉强成立，但应注明「用户自报，未被 maintainer 验证」。
  - issue #43561（2026-05-25 开，**至今 open**）：Qwen3.5 系在 V100 上的 transformers↔vLLM 版本 catch-22，原文 `If you downgrade vLLM to an older version that natively supports V100, it cannot load Qwen3.5 … If you upgrade vLLM, it fails on V100.` **成立。**
  - **原档案漏掉的一条**：Coder-Next 的官方模型卡要求 `vllm>=0.15.0`，而 0.19.x > 0.15.0 —— 所以**「vLLM 在 V100 上跑不了 Coder-Next」并不成立**，至少架构上 vLLM 0.19 支持 `qwen3_next`。原档案 #43561 的 catch-22 是针对 **Qwen3.5（qwen3_5 架构）**的，与 Coder-Next 的 `qwen3_next` 是两回事。原档案把两者混在一处了（§2 表里写「Qwen3.5 加载不了（catch-22）」，但结论栏却用它来否 Coder-Next）→ 修正 **C8**。
- **1Cat-LLM**：README 我逐行核对 —— 标题 `Make Volta Fast Again`；v1.5.1（2026-10-03）；`4× V100-SXM2-32GB / TP4`、QUASAR 27B NVFP4 + DFlash2：`4K 229.34`（对照 103.87，+120.80%）、`32K 201.18`（对照 49.04，+310.24%）、`128K 171.43`、`32K-C4 445.45 aggregate`；Attention 有效算力 `17.92 → 71.111 / 70.221 / 69.982 TFLOP/s`（TP4/TP2/TP1 **单卡算子级**测量）；安装要求 `Linux x86_64 · GLIBC >= 2.38 · GLIBCXX >= 3.4.21` / `Python 3.12` / `PyTorch 2.10.0 + CUDA 12.8` / `CUDA 12.8 Toolkit + C++ compiler + ninja`；`The artifact is 1cat_vllm-1.5.1-cp312-cp312-linux_x86_64.whl. It has not passed the manylinux container gate.`；`tested with driver 580.173.02 and recommends 570.124.06 or newer`。
  - **原档案漏掉的一条**：README 里**没有任何 Coder-Next 的 tok/s**。表里的模型是 Qwen3.6-27B-AWQ、Qwen3.6-35B-A3B、Qwen3.8-27B、Qwen3.8 Flash-Next、DeepSeek-V4-Flash、GLM-5.3-Flash。原档案说「Coder-Next 在 V100 上无第三方 tok/s 复现」**在这份 README 范围内成立**（我复核后仍成立）。
  - 另外 README 头部有一条 16GB 卡的 demo 标题 `4× Tesla V100 16GB · Qwen3.8-27B-NVFP4 + DFlash2 · ≈260 tok/s`，README 自己加了免责 `≈260 tok/s is a real-machine demo headline, not a universal fixed decode rate.`。

### 2.3 格式在 Volta 上的死路 —— 成立

- **FP8 / NVFP4 / MXFP4**：Volta 无 FP8/BF16 张量核、无 FP4 硬件 → 硬件死路，成立。但需注明一个细节（原档案 §5.2 I5 已写对）：1Cat-LLM 的表格里 `DeepSeek-V4-Flash · 8× V100 · TP8 · FP8 dense + MXFP4 experts`，说明 **FP8/MXFP4 在 V100 上是"存储格式 + 软件反量化"，不是硬件加速**。
- **BF16**：V100 无 BF16 张量核（V100S 只有 FP16 张量核）→ BF16 权重在 V100 上要么走软件转换要么不能用，成立。
- **INT8**：走 dp4a 整数通路，非张量核，成立（llama.cpp 侧证据：`mmq.cu:423` 那条 `!fp16_mma_hardware_available(cc)` 分支 + `mmq.cuh:8` 的 64 批量门槛）。
- **GGUF 是不是唯一可行路**：在「必须装得下 + 必须能用现役 ollama 0.40.6」这两个约束下，**是**。理由链我复核成立：权重只能 Q4（Q6_K 61.03 GiB / Q8_0 78.99 GiB 都超 64 GiB；Q5_K_M 52.82 GiB 理论可行但无余量）；引擎只能是 llama.cpp 系（ollama 内嵌 runner）。

### 2.4 架构支持是否已 GA —— 成立且比原档案更强

`llama.cpp` b11738 的 `src/llama-arch.cpp:38` 正式注册 `LLM_ARCH_QWEN3NEXT`；`ollama` v0.40.6 的 `llm/llama_server.go:872` `case "qwen35", "qwen35moe":`（`hasLegacyQwenMTPDraft`），`:907-908` compatClipArches 含 qwen35/qwen35moe。ollama 侧 MTP 识别靠 `hasMTPDraft` → `f.KV().Uint("nextn_predict_layers") > 0`，这对 Coder-Next（qwen3next）同样生效。**架构 GA 成立。**

---

## 3. 速度证据核查 —— 原档案最大的问题在这里

### 3.1 稠密 27B 的对照组（成立）

`llama.cpp#27366`（2026-08-19 开 / 2026-10-03 以 stale 关）原文实测（3× V100-SXM2-32GB，`bartowski/Qwen3.8-27B-GGUF` Q4_K_M，arch `qwen35`，commit 9731ad3f）：

```
$ llama-bench -m ... -dev CUDA1,CUDA2 -sm tensor -ngl 99 -fa on -p 4096 -n 128 -r 2
| qwen35 27B Q4_K - Medium | ... | tensor | 1 | CUDA1 | pp4096 | 730.71 ± 4.18 |
| qwen35 27B Q4_K - Medium | ... | tensor | 1 | CUDA1 | tg128  |  33.25 ± 0.14 |
```
- 单卡参考：`pp4096 774.81 / tg128 33.64`；`-sm layer` 双卡：`pp4096 777.09 / tg128 29.90`。
- `-sm row` → `device CUDA1 does not support split buffers`（CUDA 后端只有 SYCL 实现 `ggml_backend_split_buffer_type`）。
- `-sm tensor` → llama-bench 里 `GGML_ASSERT(meta_buf_ctx->bufs[i]) failed`；llama-cli 里**挂死 7 分钟**，双卡各占 **8286 MiB** 不释放。
→ 原档案引用的数字与结论**全部属实**，「稠密 27B 在 V100 上只有现役 1/4~1/2 速度」**成立**。

**一处因果纠正（C3）**：PR #28912（merged 2026-09-21）原文是 `I got predicted_per_second increased from 54.52 to 69.36 (+27%)`，**这个 +27% 是该 PR 自身（SM70 的 MMQ/MMVQ crossover 调优）在 DFlash2 已开启前提下**的前后对比，不是「加 DFlash2 带来的提升」。原档案 §2.3 与 §4.2 把它写成「加 DFlash2 投机解码 → 54.52→69.36」，因果反了。另外该 PR 自述测量脚本是 `a script generated by AI`（作者自己披露），可作为数字精度打折的理由。

### 3.2 【新证据·关键】唯一一组 Coder-Next 的第三方 decode 实测 —— 在 H200 上，不在 V100 上

原档案写「Coder-Next 在 V100 上的任何第三方 tok/s 复现 → 未找到公开证据」。这句在 V100 范围内**成立**，但**漏掉了唯一存在的第三方 Coder-Next tok/s 实测**：

`ecto/tang` 仓库（一个 Rust 自研引擎，GitHub issues 即其开发日志）：

- **#84（2026-10-20）`tang-llm: Qwen3-Coder-Next (qwen3next) CUDA engine`**：
  > `decode @ 4K ctx | **162 tok/s = 11.9% of speed of light** (3.52 GB a step, 4.8 TB/s)`
  > 硬件 `RunPod H200`；权重 `unsloth UD-Q4_K_XL`；`every routed expert VRAM-resident in its GGUF type; dense weights via the native int8 GEMV`；`The speed is latency-bound: about 25 small launches a layer, and GEMVs at about 600 GB/s`。
- **#97（2026-10-21）`qwen3next 162 → 247 tok/s on H200`**：stage sweep + flash-aa + K-split + Q8X + fast K-quant dot，单流、~1.24k-token prompt、512 输出 token。
- **#77**：CPU 参考实现 + 模型支持矩阵，明确「Qwen3-Next-80B 与 Qwen3-Coder-Next 同架构」。

**这条证据为什么重要**（原档案没算）：
- 官方技术报告**通篇没有任何 tok/s**（我 grep `tok/s|tokens per second|throughput|TTFT|GPU|H100|A100|H200|Volta|V100` 全文 0 命中），所以这是**唯一的第三方速度标尺**。
- **3.52 GB/step 是实测的每 token 权重搬运量**，而原档案用的是「3B 激活 × 0.605 B/参数 = 1.82 GB/token」的算术。两者差 ~1.9 倍。差异来源可解释：该引擎是 **Q4 专家 + int8/Q8 稠密权重**的混合量化，不是纯 Q4_K_M；但无论怎么解释，**「每 token 只搬 1.82 GB」这个前提本身没有实测支撑**。
- **有效带宽对比**：H200 上 162 tok/s × 3.52 GB ≈ 570 GB/s 有效（占 4.8 TB/s 的 11.9%，README 自己说 latency-bound）；而我们现役 30B 是 135.7 tok/s × 1.83 GB ≈ 248 GB/s 有效（占 V100S 900 GB/s 的 27.6%）。**折算成「每 GB/s 有效带宽能产出多少 token」，Coder-Next 在这张卡上只有 30B 的约 1/4。** 不能直接外推（引擎不同、量化不同、卡不同），但它**明确不支持**「两者必然同档」这个原档案的强断言。
- 还有一个结构性的、可解释的怀疑点：Coder-Next 每 token 要做 `48 层 × (10 路由专家 + 1 共享专家) × 3 个矩阵 = 1584 次极小 GEMV` + `36 层 GDN 递归 kernel`；现役 30B 是 `48 × 8 × 3 = 1152` 次纯注意力 GEMV，形态上对 GPU 更友好。ecto/tang 自己说 `about 25 small launches a layer`。**这与同工作区的 `verify-7` 独立得出的「Coder-Next 解码不是显存带宽受限，而是被 kernel 启动开销卡死」结论方向一致** —— 两份复核相互印证。

### 3.3 【新证据·关键】唯一一组 llama.cpp 上 Coder-Next 的成体系第三方实测 —— 在消费级卡上

`carteakey.dev` 博客《Running Qwen3-Coder-Next at 40 t/s on consumer hardware (draft)》（2026-02-18，脚本在 `carteakey/l3ms`）：

- 硬件：`i5-12600K (6P+4E)`、**RTX 4070 12 GB（288 GB/s）**、**64 GB DDR5-6000**、CachyOS / CUDA 13.0；模型 `unsloth/Qwen3-Coder-Next-UD-Q4_K_XL`（~46–47 GB，**大部分专家在系统内存**）。
- 结果：`~40 t/s generation, 510+ t/s prompt processing`；对照同硬件 `GPT-OSS-120B ~25–30 t/s`。
- **`--n-cpu-moe` 家族的实测表**（`pp512` = 512-token prompt，`tg128` = 128 token 生成）：

| 策略 | pp512 (t/s) | tg128 (t/s) |
|---|---|---|
| `N_CPU_MOE=40`（默认） | 451 | **40.6** |
| `--ot .ffn_.*_exps.=CPU`（全专家上 CPU） | 410 | **33.7** |
| `--fit`（128 MiB 余量, 131k ctx） | 476 | 38.2 |
| `--fit`（128 MiB 余量, 64k ctx） | 497 | 39.60 |
| `--fit` + q8_0 KV（64k ctx, 128 MiB） | **511** | 39.93 |
| `--fit` + q8_0 KV（64k ctx, 512 MiB） | 502 | 39.62 |

- ik_llama.cpp 分支（MoE 专用 kernel）：`fused-moe + merge-up-gate` 达 `tg128 41.1 / pp512 215`（prefill 腰斩，RAM 需求 46→73 GB）。
- 作者对行为的定性（对我们的负载直接相关）：
  - `Q3CN is described as "aggressively completing tasks" - great for coding agents`（与我们「模型不努力才是成本瓶颈」的旧结论方向一致）
  - `Q3CN can be verbose and occasionally enters loops with certain agent frameworks. Setting --temp 0 can help`（**跨轮进入循环 —— 正是我们要验的「跨轮不崩」风险**）
  - `Because Q3CN is a non-thinking model, it doesn't waste tokens generating internal <think> blocks`（非思考模式的 token 成本优势，作者也这么认为）

**这条证据为什么重要**：
1. 它是 **llama.cpp 上 Coder-Next 唯一成体系的第三方实测**（6+ 配置、脚本开源），原档案完全没找到。
2. 它**直接回答**了本次待验证假设里"`--n-cpu-moe` 在 V100 上可行吗、代价多大"这个问题 —— 原档案用带宽模型**推断**「数量级恶化」，实测是**只低 1~2 倍，不恶化数量级**（33.7~40.6 vs 纯 GPU 方案 40.6）。原因很直白：CPU 侧还有 DDR5 带宽 + 专家缓存兜着 → **C4**。
3. 它给出一个对 V100 不利的量级提示：即使在 288 GB/s 的 4070 + 内存卸载下，llama.cpp 跑 Coder-Next 也只有 **33.7–41.2 tok/s**。V100 的 900 GB/s 显存带宽是 4070 的 3.1×，而且我们的场景是**整个模型常驻显存**（不像 4070 那样大半在系统内存里），所以 V100 上 Coder-Next 的 llama.cpp 表现**不应该是 33–41 这个量级**；但它同样**不能**支持"和现役 135.7 同档"的乐观预期 —— 真实落点更可能在 **60–130 tok/s** 区间，需要实测。

### 3.4 Coder-Next 在 V100 上到底有没有实测？—— 仍然没有

我把能用的检索面都扫了：
- GitHub issues 全站检索 `"Qwen3-Coder-Next" V100` / `"Qwen3-Coder-Next" tok/s` / `"Qwen3-Coder-Next" SWE-bench` / `"Qwen3-Coder-Next" Terminal-Bench`：命中的都是无关仓库（release-watch、CI 机器人、font issue 之类），**无 V100 复现**。
- GitHub discussions 检索 `"Qwen3-Coder-Next"`：命中有意义的是 `ggml-org/llama.cpp #21886`（见 §5 C7）、`carteakey`（§3.3）、`ml-explore/mlx #4524`、`benbhall`（讲 Qwen 32B，无关）、`VecSzn/PolyStrata #47`（4070 Ti Super，测的是 qwen3-8-flash-next-coder / qwen3-6-35b-a3b，**不是 Coder-Next**）。
- 1Cat-LLM README：模型表里无 Coder-Next。
- `huggingface.co` 本机不可达，只能用 `hf-mirror`；HF 的 discussions/社区帖无法覆盖。

**结论：「Coder-Next 在 V100（或任何 sm_70 / ~900 GB/s 老卡）上的 decode tok/s，公开世界为零」—— 与原档案一致，成立。** 但原档案由此推出「所以两者必然同档（1.82 vs 1.83 GB/token）」，这一步**推不出来**。

### 3.5 对照：现役 30B 在 V100 上的速度 = 原档案的 135.7 tok/s（本轮未复核）

本轮无法 SSH 到 anolis，**135.7 / 149.1 / 109.7 / 10.5s 这些数字我一条都没能独立复现**，只能标记「未复核」。这一点很重要：原档案的整个带宽账（`1.83 GB/token × 900 GB/s → 492 tok/s 理论，实测 135.7 = 27% 效率`）**以及**「33.25 / 135.7 = 1/4.1」这个比值，都挂在这一个未复核的数字上。**在 anolis 上重跑一次现役基线，是所有后续判断的前提。**

---

## 4. 质量证据核查

### 4.1 官方分数 = 作者自报，无第三方独立复现（成立，且我补齐了基线）

- **Coder-Next**：技术报告是唯一来源（§1.3）。SWE-bench **官方榜（`swebench.com`）上 Coder-Next 0 命中**（我抓 2.39 MB 页面并解析出 323 条内嵌记录，`"Coder-Next"` / `"Qwen3-Next-80"` 全部 0 命中）。Terminal-Bench 榜单页（`tbench.ai/leaderboard/terminal-bench/2.0`）里也检索不到 Coder-Next 条目。GitHub 全站检索也未找到任何独立复现 SWE-V / TB2.0 分数的第三方项目。
  → **「70.6–71.3 只有作者自报」成立。** 且比原档案说得更弱：连 Terminal-Bench 榜单都没有它的条目，等于**连 scaffold 都没有第三方跑过**。

- **现役 30B 的基线（C2 的核心修正）**：SWE-bench 官方榜上 `model_display = Qwen3-Coder-30B-A3B-Instruct` 共有 **5 条**第三方提交：

| agent | resolved | date | checked |
|---|---|---|---|
| EntroPO + R2E | **60.4** | 2025-09-01 | `false (See README.md…)` |
| EntroPO + R2E | **52.2** | 2025-09-01 | false |
| OpenHands | **51.6** | 2025-08-05 | False |
| EntroPO + R2E | **49.67** | 2025-09-01 | false |
| EntroPO + R2E | **45.0** | 2025-09-01 | false |

  另有 `Qwen3-Coder-480B-A35B-Instruct` + OpenHands = **69.6**（2025-08-05）、`Qwen3-Coder 480B/A35B Instruct` + mini-SWE-agent = **55.4**（2025-08-02，**checked: True**）。

  → 原档案 §5.3 写「Qwen3-Coder-30B-A3B-Instruct 的官方 SWE-bench Verified 文本分（模型卡只有图片）→ 未找到公开证据」。**"官方模型卡没有文本分"是对的，但"未找到公开证据"是错的**：公开第三方基线是有的（45.0–60.4）。

  **更关键的是可以做同 scaffold 对照**（原档案完全没做这一步）：

  | 模型 | OpenHands scaffold 上的 SWE-V |
  |---|---|
  | Qwen3-Coder-30B-A3B-Instruct（现役） | **51.6**（2025-08-05） |
  | Qwen3-Coder-480B-A35B-Instruct | **69.6**（2025-08-05） |
  | **Qwen3-Coder-Next（技术报告，2026-02）** | **71.3** |

  即：**Coder-Next 用 1/6 的激活参数，逼近了 480B-A35B 的解题率，并比现役 30B 高出约 20 个点**。这是「更强」这一半最有力的一条论据 —— 但两侧 scaffold 版本不同（2025-08 的 OpenHands vs 2026-02 的 OpenHands）、两侧都未被官方 `checked: True` 验证，**仍属「作者自报 vs 第三方自报」的对照，不是第三方复现**。

### 4.2 质量证据评级

- 官方一手：Qwen 技术报告 PDF（我复算，数字全对）——**作者自报**。
- 第三方独立复现 agentic 分数：**无**。
- 社区定性：carteakey 博客说 Q3CN「aggressively completing tasks」（对我们「模型不努力才是瓶颈」的旧结论是支持性 anecdotal），同时警告「occasionally enters loops with certain agent frameworks」（对我们「跨轮不崩」是风险信号）。**两句话方向相反，不能拿来当证据。**

---

## 5. 原结论需要修正的地方（编号 C1–C9）

> **C1（重要）｜「Coder-Next 与现役速度必然同档」是未验证推断，且现有第三方证据偏负面。**
> 原档案 §4.1 的推导链是：`48.40GB/80B = 0.605 B/参数 × 3B 激活 = 1.82 GB/token` vs `18.56/30.5 × 3B = 1.83 GB/token` → 「速度必然同档，不会更快」。
> **问题**：(a) 「3B 激活 ⇒ 每 token 只搬 3B 权重」是**算术模型**，没有任何实测支撑；实测的 Coder-Next 每步搬运量是 **3.52 GB**（ecto/tang#84，H200，Q4专家+int8稠密混合量化），比算术值高 ~1.9×。(b) 唯一存在的第三方 llama.cpp 实测（carteakey，RTX 4070 + 内存卸载）只有 **33.7–41.2 tok/s**。(c) 唯一存在的第三方 Coder-Next 引擎实测（ecto/tang，H200）是 **162→247 tok/s**，按每有效带宽折算比现役 30B 低约 4×，且作者明说 `latency-bound`。
> **修正表述**：「两者每 token 读取量在纯 Q4 算术下接近，因此**不排除**同档；但该结论**没有任何实测支撑**，且现有两个独立第三方数据源都指向 Coder-Next 明显更慢。落地判断必须以冒烟实测为准，**不能**用带宽账替代实测。」

> **C2（重要）｜「现役 30B 的官方 SWE-V 文本分：未找到公开证据」不成立。**
> swebench.com 官方榜有 5 条第三方提交（60.4 / 52.2 / 51.6 / 49.67 / 45.0），另有 480B 的 69.6 / 55.4。原档案 §5.3 与 §6.1 用「现役没有公开分数」来暗示「Coder-Next 的 70.6 是更高的、无法证伪的宣称」，这**削弱了自己论证的严谨性** —— 现役有公开基线，只是分散在第三方提交里。
> **修正表述**：把「现役无基线」改成「现役公开第三方基线 45.0–60.4（EntroPO+R2E / OpenHands），最好一条 60.4；Coder-Next 的 70.6–71.3 为作者自报，两者 scaffold 不同期、不同版本」。同时补上同 scaffold 对照（OpenHands：30B 51.6 → 480B 69.6 → Coder-Next 71.3），这是「更强」这一半最干净的论据。

> **C3（事实性）｜PR #28912 的因果被写反。**
> 原档案写「加 DFlash2 投机解码 54.52→69.36 tok/s（PR #28912，+27%）」。原文是 `I got predicted_per_second increased from 54.52 to 69.36 (+27%)`，这个增量来自**该 PR 自身的 SM70 MMQ/MMVQ crossover 调优**（DFlash2 前后都开着）。另：该 PR 自述测量脚本由 AI 生成。
> **修正表述**：「DFlash2 投机解码 + SM70 MMQ crossover 调优后，V100 上 Qwen3.8-27B 的 `predicted_per_second` 达 69.36（较调优前的 54.52 提升 27%）」。

> **C4（重要）｜「`--n-cpu-moe` 每 token 延迟会增加一个数量级以上」过度且错误。**
> 第三方实测（carteakey，RTX 4070 12GB + DDR5-6000）：`N_CPU_MOE=40` → tg128 40.6 / pp512 451；全专家上 CPU → 33.7 / 410；`--fit` + q8_0 KV → 39.93 / 511。**CPU 卸载相对纯 GPU 方案只低约 1–2 倍，不是数量级**（DDR5 带宽 + 专家缓存兜底）。
> **修正表述**：「CPU 卸载在本场景下是**可用但更慢**的降级手段（实测低 1–2 倍，非数量级），不是『一用就废』。」—— 但这**不改变**原档案的最终建议（我们 64 GiB 装得下，就不该用 CPU 卸载换显存）；改变的是**理由**和**风险量级**。更重要的是：CPU 卸载路径在 Coder-Next + 老架构 GPU 上有**专属崩溃报告**（见 C7），所以"可行"也要打折。

> **C5（重要）｜ollama 的开关暴露面可以关闭，且结论对原档案的两处表述有影响。**
> 我把 ollama v0.40.6 的 `llm/llama_server.go` 逐行读完：
> - **显式传给 llama-server 的参数只有这些**：`--model/--port/--host/--no-webui/--offline`、`-np/--kv-unified/--cache-ram`、`--lora`、`--cache-type-k/--cache-type-v`、`--log-*`、`--embedding`、`--flash-attn`、`--load-mode`、`--mmproj/--no-mmproj-offload`、`--no-jinja/--chat-template`、`--context-shift`、`--keep`、`--spec-type/--spec-draft-n-max/--spec-draft-backend-sampling/--spec-draft-model`、`--image-min-tokens`。
> - **没有** `--tensor-split`、**没有** `--n-cpu-moe/--cpu-moe/--moe-cache-mib/--n-cpu-ffn`、**没有** `--fit`、**没有** `--split-mode`（除 `:676` 在设置了 `MainGPU` 时强制 `--split-mode none`）。
> - **但是**：`llm/llama_server.go:476 cmd.Env = os.Environ()`，ollama 启动 llama-server 子进程时**继承整个环境**；而 llama.cpp 的这些开关全部带 `set_env("LLAMA_ARG_*")`（`arg.cpp`：`LLAMA_ARG_SPLIT_MODE` / `LLAMA_ARG_TENSOR_SPLIT` / `LLAMA_ARG_CPU_MOE` / `LLAMA_ARG_N_CPU_MOE` / `LLAMA_ARG_MOE_CACHE_MIB` / `LLAMA_ARG_N_CPU_FFN`）。
> **修正表述**：(a) 原档案 §6.2「不要用 `--split-mode tensor`（ollama 0.40.x 默认 layer 切分，保持默认）」——**结论对、理由错**：ollama 根本不传 `--split-mode`，是 llama.cpp 的默认 `LLAMA_SPLIT_MODE_LAYER`（`common/common.h:490`）在起作用。(b) 原档案 §2.4 把 `--n-cpu-moe` / `--moe-cache-mib` 当现成手段写，**ollama 下没有对应 CLI**，但**可以用 `LLAMA_ARG_N_CPU_MOE=…` / `LLAMA_ARG_MOE_CACHE_MIB=…` / `LLAMA_ARG_SPLIT_MODE=…` / `LLAMA_ARG_TENSOR_SPLIT=…` 环境变量打开**（源码级结论，**本轮未在 anolis 实测**）。这把「必须先装独立 llama-server」的前提**去掉**了。

> **C6（口径）｜「64 GB 减 48.4 GB 余 ~12 GB」算错了，而且 Q5_K_M 是理论可行的。**
> 2×32768 MiB = **64 GiB = 68.72 GB**。官方 Q4_K_M 48.41 GB = 45.09 GiB → **余 18.9 GiB**（不是 12 GB）。ollama 库版 52 GB = 48.4 GiB → 余 15.6 GiB。**Q5_K_M 56.71 GB = 52.82 GiB → 余 11.2 GiB，理论可行**（KV 32K 只要 0.79 GiB），只是没有余量做双卡计算缓冲。
> **修正表述**：「只能 Q4_K_M，没有降档空间」这个说法方向讲反了 —— Q4 是**最稳**的档，Q5_K_M 是**理论可行但无余量**的档，Q6/Q8 才放不下。

> **C7（重要·原档案漏项）｜两条针对 Coder-Next 本身、且正落在我们负载形态上的 llama.cpp 缺陷报告。**
> 1. **`llama.cpp#28241`（2026-09-02 开，**至今 open**）**：标题 `Eval bug: CUDA "illegal memory access" with -cmoe on Turing (sm_75) at exactly 94 prompt tokens`。模型就是 **`unsloth/Qwen3-Coder-Next-GGUF → Qwen3-Coder-Next-UD-Q4_K_S.gguf`（80B MoE / 3B active / 46,079,830,016 B）**，硬件 `Quadro T2000 4 GB (Turing, sm_75)`，`-cmoe` + `-c 32768` + `-ngl 99` → **prompt 恰好 94 token 时必崩**（93/95 正常；CPU-only build 正常）。作者逐项排除了模型文件/量化/驱动/KV/语言等因素。**这是「CPU 专家卸载路径 × Coder-Next × 老架构 GPU」的直接崩溃证据**，sm_75 比 sm_70 还新一档。原档案 §2.4 回答「`--n-cpu-moe` 可行吗」时**只做了带宽推断，完全没找到这条**。
> 2. **`llama.cpp#28185`（2026-09-01 开，**至今 open**）**：标题 `--tensor-split causes intermittent output degeneration on long-context MoE inference, independent of client`。命令行就是 **`--model Qwen3-Coder-Next-UD-Q4_K_M.gguf --ctx-size 65536 --gpu-layers 999 --split-mode layer --tensor-split 4,1 --n-cpu-moe 34 --flash-attn on --parallel 1`** → 增长型多轮会话里**间歇性输出退化**（重复、机械化输出、单条回复膨胀到 ~14 MB / 15+ 分钟）。作者用最小 Python 脚本（无 tool call、纯多轮文本）也能复现（2 次 1 坏）。并且明确观察：**`MoE experts stay almost entirely on one device regardless of the split ratio tried; only non-MoE tensors seem affected by the split value`**、`--main-gpu` 对不平衡无影响。
> **这条正好命中我们「2×V100 双卡切分 + 每题约 10 轮工具调用 + 跨轮不崩」的场景**，原档案只把 `qwen35` 家族的 #30906（输出损坏）列为风险，**漏掉了这条专指 Coder-Next、专指多卡 tensor-split 的复现**。
> **修正表述**：风险清单要新增两条 Coder-Next 专属项，并把 #28185 的「多卡切分下 MoE 专家几乎不被再平衡」这条观察写进双卡方案的显存账（48.41 GB 到底怎么落到两张 32 GB 卡上，不是显然的 24.2+24.2）。

> **C8（逻辑）｜原档案把「vLLM × Qwen3.5 的 catch-22」误当成「vLLM 跑不了 Coder-Next」。**
> `vllm#43561` 讲的是 **Qwen3.5（`qwen3_5` 架构）** 在 V100 上的 transformers↔vLLM 版本冲突，与 Coder-Next 的 `qwen3_next` 架构无关；而 Coder-Next 官方模型卡明确要求 `vllm>=0.15.0`，**远低于 0.19.x**。原档案 §2 表里在「Qwen3.5 加载不了（catch-22）」和「Coder-Next」之间做了隐式跳转。
> **修正表述**：「vLLM 在 V100 上跑不了 **Qwen3.5 系**」与「vLLM 能不能跑 Coder-Next」是两个问题；后者未被本轮证据否定，但 vLLM 在 V100 上 stock 只有 15.6 tok/s、且要手改 fused-MoE 配置 → 结论（不上 vLLM）不变，**但理由要改**。

> **C9（小）｜Coder-Next 在 Terminal-Bench 2.0 上打不过闭源前沿模型，原档案没点出来。**
> 技术报告 Table 5：Coder-Next `34.2 / 36.2 / 30.9 / 25.8`，Claude-Opus-4.5 `58.4 / 57.3 / 53.9 / 51.7`，GLM-4.7 `44.9 / 37.1 / – / 31.5`，MiniMax-M2.1 `– / 32.6 / 42.7 / 39.3`。原档案在表里抄了这些数字，但 §0/§6 的结论里只强调「非思考模式 → token 成本低」。对我们的 API 主力（MiniMax M3.1 Flash / GLM-5.3 / Kimi K3）而言，**Coder-Next 在终端 agentic 上并不领先**。这条要写进结论：本地臂的价值是**零成本量产**，不是解题率天花板。

---

## 6. 无法核实 / 本轮查不到（不补齐）

| 项 | 状态 |
|---|---|
| Coder-Next 在 2×V100S 上的 decode tok/s | **公开世界为零**，本机也不可达（无 anolis SSH）。需现场冒烟。 |
| Coder-Next 在任何 ~900 GB/s 老卡（3090 / P40 / 4060Ti 16G / A6000）上的第三方 tok/s | **未找到**（GitHub issues/discussions 全站 + 1Cat-LLM README + HF 镜像 + 技术报告全文，均无）。 |
| Coder-Next agentic 分数的**第三方独立复现** | **未找到**。SWE-bench 官方榜 0 命中、TB 榜单 0 命中、GitHub 无独立复现项目。 |
| 「ollama 0.40.6 内嵌 llama.cpp 恰为 b11738」 | **无法核实**（ollama v0.40.6 源码里找不到 `LLAMA_CPP_VERSION`；`.gitmodules` / `llm/llama/CMakeLists.txt` 在该 tag 上 404）。可核实的替代说法：b11738 = 2026-10-19，5 个 Volta 修复均 ≤2026-10-01 → 只要 anolis 上不是更早的 llama.cpp 就在内。 |
| 原档案 §1 的全部 anolis 实测（nvidia-smi / topo / nvcc 链接失败 / ollama /api/tags / 135.7 tok/s） | **未复核**（本会话机器是 pandev-comp，`ssh anolis-gpu-01` → `Could not resolve hostname`）。 |
| exllamav2 / exl3 在 sm_70 的支持声明 | **本轮未查**（原档案已列为未找到，本轮不重复声明）。 |
| `LLAMA_ARG_*` 环境变量在 ollama 0.40.6 运行时确实生效 | **源码级成立，未在 anolis 实测**（`llama_server.go:476 cmd.Env = os.Environ()` + `arg.cpp` 的 `set_env("LLAMA_ARG_*")`）。 |
| Coder-Next 的 MTP 投机解码在 llama.cpp 上是否已修 | **未闭合**：见 §7 的 discussion #21886。 |
| Terminal-Bench 2.0 榜单数据接口 | **未定位到**（`tbench.ai/leaderboard/terminal-bench/2.0` 是前端渲染页，页面文本里只有 Qwen3.8-Max-0902 一个模型名；未能确认榜单全量）。 |

---

## 7. 补充：新发现的、但原档案没写的两条负面信号

1. **llama.cpp discussion #21886「Qwen3-Coder-Next and speculative decoding」**（2026-04-14，作者 digitalscream，1 条回复；回复者 d-shehu 2026-07-17）：
   > 提问者：`spec-type = ngram-mod` + Coder-Next → `load_model: speculative decoding not supported by this context`；`Already verified that it's not the REAM model that's causing it.`
   > 回复者：`I also have a use case for this where I need to run the best model that can fit in 64 GB of VRAM … The model card says MTP is supported but it errors out. I assume it wasn't tested with Qwen 3 Next or Qwen 3 Next Coder?`
   → **这正是我们的场景（"best model that can fit in 64 GB of VRAM"）**，而 Coder-Next 的投机解码在 llama.cpp 上**至少到 2026-07 仍有人报障**。原档案 §2.3 讲 DFlash2 在 V100 上有效（那是在 **Qwen3.8-27B** 上），却直接把这条能力外推给了 Coder-Next。
2. **Coder-Next 在 agentic 场景里"会进循环"的社区报告**（carteakey 博客）：`Q3CN can be verbose and occasionally enters loops with certain agent frameworks. Setting --temp 0 can help for pure coding tasks.` → 我们的负载正是「每题约 10 轮工具调用」，这条要在冒烟里专门测（重复循环 = 直接判失败）。

---

## 8. 给决策者的落地建议（在原档案 §6 施工单上的修正）

原档案的施工单（Step 0 环境冒烟 → Step 1 pull → Step 2 num_ctx 32K / NUM_PARALLEL=1 / 不设 q4_0 KV → Step 3 三关冒烟 → Step 4 af-bench 同题同判）**方向是对的**，我加/改四条：

1. **Step 0 增一条基线复跑**：在 anolis 上重跑现役 30B 的 135.7 tok/s（本轮无法复核），作为一切比值的分母。同时读一下 ollama 启动横幅里的 llama.cpp commit，确认 ≥2026-10-01（闭合 §6 的 "b11738" 疑点）。
2. **Step 3 速度关的门槛要改成"与现役同量级"，而不是原档案自己写的"≥100 tok/s"**。理由：现役实测 135.7，原档案自定 100 的门槛等于允许**比现役慢 26%**，而 C1 指向的可能是慢 2 倍。
   - 建议：**< 60 tok/s → 直接否决 Coder-Next，回退现役 30B**（因为此时单题墙钟成本已明显高于现役，而解题率优势尚未实测）；**60–135 → 值得进 af-bench 同题同判**（用解题率优势抵消墙钟劣势）；**≥135 → 优先上**。
3. **Step 2 加两条**：(a) 明确 `OLLAMA_KV_CACHE_TYPE` 保持 f16（不要 q4_0，原档案这条对）；(b) 若要试 `--n-cpu-moe` 降级，**必须用 `LLAMA_ARG_N_CPU_MOE=…` 环境变量**（ollama 无 CLI，见 C5），且**先不要用**（48.41 GB 装得下，且 C7 的 #28241 显示 `-cmoe` + Coder-Next 在 sm_75 上有必崩 bug）。
4. **Step 3 多轮不崩关要加两个专门用例**：(a) ≥10 轮的 tool calling 循环里检查输出是否进入重复循环（carteakey 报告的社区症状）；(b) 双卡下跑**增长型多轮**（不只是 10 轮独立请求），对照 #28185 的退化场景（长 ctx + 多轮 + layer split）。

**最后一句纪律**：本轮所有「Coder-Next 更快/同档」的表述都应当降级为**待实测假设**。原档案在这一点上把推断写成了结论，这是它最需要修正的地方；而它的一手事实层（体积/架构/官方分数/引擎矩阵/源码级 Volta 路径）经我逐条复算，**全部属实，质量很高**。

---

## 附：本轮实际执行的命令与文件（可复现）

```bash
# 模型与体积
curl -s https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next
curl -s https://hf-mirror.com/Qwen/Qwen3-Coder-Next/raw/main/config.json
curl -s https://hf-mirror.com/Qwen/Qwen3-Coder-Next/raw/main/README.md
curl -s "https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next-GGUF?blobs=true"
curl -s https://ollama.com/library/qwen3-coder-next/tags
curl -s https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-30B-A3B-Instruct ; .../raw/main/config.json
curl -s https://hf-mirror.com/api/models/Qwen/Qwen3.8-27B ; .../raw/main/README.md
curl -s "https://hf-mirror.com/api/models/bartowski/Qwen3.8-27B-GGUF?blobs=true"

# 官方分数
curl -sSL https://raw.githubusercontent.com/QwenLM/Qwen3-Coder/main/qwen3_coder_next_tech_report.pdf -o qcntr.pdf
pdftotext -layout qcntr.pdf qcntr.txt     # 1451 行；sed -n '700,880p' 为 Table 3/4/5

# 引擎与源码
curl -s https://raw.githubusercontent.com/sgl-project/sglang/main/python/sglang/srt/model_executor/model_runner_components/load_model_utils.py
curl -s https://raw.githubusercontent.com/NVIDIA/TensorRT-LLM/main/docs/source/release-notes.md      # :736 / :759 / :810 / :823
curl -s https://raw.githubusercontent.com/huggingface/text-generation-inference/main/docs/source/installation_nvidia.md
curl -s https://raw.githubusercontent.com/1CatAI/1Cat-vLLM/main/README.md
for f in ggml/src/ggml-cuda/{CMakeLists.txt,common.cuh,fattn.cu,mmq.cu,gated-delta-net-mma.cu,ssm-scan.cu} \
         ggml/src/ggml-cuda/mmq.cuh src/llama-arch.cpp common/arg.cpp common/common.h; do
  curl -s "https://raw.githubusercontent.com/ggml-org/llama.cpp/b11738/$f"; done
curl -s https://raw.githubusercontent.com/ollama/ollama/v0.40.6/llm/llama_server.go

# 上游 issue / PR（HTML 或 REST API，API 需带 UA）
https://github.com/ggml-org/llama.cpp/issues/27366 | /issues/28037 | /issues/28241 | /issues/28185
https://github.com/ggml-org/llama.cpp/pull/28912 | /pull/28887 | /pull/28888 | /pull/29232 | /pull/29803
https://github.com/vllm-project/vllm/issues/47019 | /issues/43561
https://github.com/ecto/tang/issues/77 | /issues/84 | /issues/97
https://github.com/ggml-org/llama.cpp/discussions/21886
https://carteakey.dev/blog/optimizing-qwen3-coder-next-local-inference/

# 官方榜单
curl -sL -A "Mozilla/5.0" https://www.swebench.com/        # 2.39 MB，内嵌 323 条记录
curl -sL -A "Mozilla/5.0" https://www.tbench.ai/leaderboard/terminal-bench/2.0
```

**本机环境事实（供他人参考）**：`pandev-comp` = RTX 3070 Laptop 8GB / driver 595.99.02 / ollama 0.35.1（只有 qwen3:4b、qwen3:8b）；`ssh anolis-gpu-01` 不可解析；`huggingface.co` 不可达（用 `hf-mirror.com`），`api.github.com` 需 `User-Agent: Mozilla/5.0` 且会 rate-limit，`github.com` HTML 搜索可用（`/search?q=…&type=issues`，解析 `react-app.embeddedData`）。
