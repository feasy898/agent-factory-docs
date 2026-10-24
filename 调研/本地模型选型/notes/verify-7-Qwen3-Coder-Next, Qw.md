# 复核 · 第 7 名 · Qwen3-Coder-Next / Qwen3.6-35B-A3B / Qwen3.8-27B

- 复核日期：**2026-10-21**（本文件所有抓取/读取/SSH 核验均在该日完成）
- 复核对象：`Qwen3-Coder-Next`（主）、`Qwen3.6-35B-A3B`、`Qwen3.8-27B`（对照）
- 被复核的原始档案：`调研/本地模型选型/notes/english-community.md`（2026-10-21 出具）
- 基准机器（全程以此为准）：**anolis-gpu-01 = 2× Tesla V100S-PCIE-32GB（sm_70 / CC 7.0，无 NVLink，PCIE），driver 570.133.20，CUDA 12.6 工具链，125 GB 内存，ollama 0.40.6**
- 现役：`qwen3-coder-30b` = Qwen3-Coder-30B-A3B-Instruct-Q4_K_M（18.5 GB / 30.5B 总参 / 3.3B 激活 / 262144 ctx）
- 本轮**未下载任何权重、未跑任何推理**；只做只读核验（HF API、GitHub raw/HTML、arXiv HTML、ollama registry、HN Algolia API、SSH 到 anolis 读文件与日志）

---

## 0. 复核结论速览

| 原结论要点 | 复核判定 |
|---|---|
| 官方仓库/参数/激活/context/体积/许可/下载量 | ✅ **全部属实**（逐项从 HF API + config.json + GGUF 分片直读复算） |
| 「80B-A3B 解码速度与现役同量级（90–140 t/s）」 | ❌ **推翻**。无任何证据支撑，且被两类第三方数据反驳；预期应为**比现役慢 2–4 倍**（30–60 t/s，推断值） |
| 「混合线性注意力打断前缀缓存复用 → 每轮工具调用重算全对话」 | ⚠️ **过度泛化**。原始证据讲的是**落盘 slot save/restore**；上游已修（#25913 已 MERGED），进程内 warm-slot 复用有第三方实测有效 |
| 「上游未修的 FA GEMM NaN race，Volta 会中招，必须 q4_0 KV 规避」 | ❌ **推翻**。该 kernel 是 P100 fork 私有文件（上游 404），修复已在 fork PR #4；且其 commit message 写明受影响路径是 **pre-Volta**，V100 不在内 |
| 「现役单卡 32GB 装不下 262K KV → 只能 num_ctx 8192；Coder-Next 首次让本地跑满 262K」 | ❌ **推翻**。本机 ollama 日志实测：现役在 n_ctx=262144 下 49/49 层全 GPU offload，KV 拆两卡后仍剩 5784 MiB |
| 「70.6% SWE-V 是厂商自报、官方榜 0 命中」 | ✅ 属实，**但不完整**（漏了厂商自报表的基线复现、漏了 TB 2.0 的 25.8–36.2 区间、漏了现役在官方榜的三个条目） |
| 「AA II 对非 reasoning 模型系统性低估，不应据此排序」 | ⚠️ 未经证实的辩解。同一张表里**现役 30B 得 10 分 > Coder-Next 9 分** |
| 「Qwen3-Coder-Next 是唯一更值得上的候选」 | ❌ **不成立**（能力未获第三方独立复现，速度预期被推翻，长上下文优势不存在） |

**净结论：原报告的一手事实（体积/架构/榜单/社区引文）质量很高，但核心推理链「MoE 又快又强 → 换 80B-A3B 买能力不买速度」在我能查到的证据下站不住。按现有证据，Qwen3-Coder-Next 在我们机器上更可能是「墙钟更贵、解题率未证」，不是「更值得上」。**

---

## 1. 一手事实核查（逐项复算）

### 1.1 模型本体（HF API 直读）

命令：`curl -s https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next`（HTTP 200，18811 B）
另：`curl -s https://hf-mirror.com/Qwen/Qwen3-Coder-Next/raw/main/config.json`（HTTP 200，1178 B）

| 项 | 实测值 | 原报告 | 判定 |
|---|---|---|---|
| 模型 ID / 架构 | `Qwen3-Coder-Next` / `Qwen3NextForCausalLM` / model_type `qwen3_next` | 同 | ✅ |
| 总参（BF16） | **79,674,391,296**（safetensors.parameters.BF16） | 79.7B | ✅ |
| 激活参 | 3B（512 专家 top-10 + 1 shared expert） | 同 | ✅ |
| 层数 / 混合布局 | `num_hidden_layers=48`，`full_attention_interval=4` → 12 层全注意力 + 36 层 Gated DeltaNet | 48=36+12 | ✅（推导自 config，README 原文「12 * (3 * (Gated DeltaNet -> MoE) -> 1 * (Gated Attention -> MoE))」一致） |
| 专家 | `num_experts=512`, `num_experts_per_tok=10`, `shared_expert_intermediate_size=512`, `moe_intermediate_size=512` | 同 | ✅ |
| 注意力 | `num_attention_heads=16`, `num_key_value_heads=2`, `head_dim=256`, `partial_rotary_factor=0.25` | 同 | ✅ |
| 线性注意力 | `linear_num_key_heads=16`, `linear_num_value_heads=32`, `linear_value_head_dim=128`, `linear_conv_kernel_dim=4` | 未列 | ➕ 补充 |
| context | `max_position_embeddings=262144` | 256K | ✅ |
| 许可 | `license:apache-2.0`（cardData.license + tags） | Apache-2.0 | ✅ |
| 下载量 / 点赞 | **522,825** / 1,703 | 未列 | ➕ |
| 创建 / 最后更新 | 2026-01-30 / 2026-02-03 | 未列 | ➕ |
| thinking | 官方 README：「supports only non-thinking mode」 | 非 reasoning | ✅ |

### 1.2 GGUF 体积（分片逐个列出后求和）

命令：`curl -s "https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next-GGUF/tree/main?recursive=true"`（HTTP 200，32 条）
仓库元数据：downloads **41,833**、likes 298、created 2026-02-02、lastModified 2026-02-04、apache-2.0。

| 量化 | 分片求和 | 原报告 | 判定 |
|---|---|---|---|
| F16 | 49.2+49.3+48.99+11.97 = **159.46 GB** | 159.46 | ✅ |
| Q8_0 | 26.19+26.21+26.05+6.36 = **84.81 GB** | 84.81 | ✅ |
| Q6_K | 20.25+20.25+20.12+4.91 = **65.53 GB** | 65.53 | ✅ |
| Q5_K_M | 17.81+17.48+17.23+4.19 = **56.71 GB** | 56.71 | ✅ |
| Q5_0 | 17.03+16.98+16.87+4.12 = **55.00 GB** | 未列 | ➕ |
| Q4_K_M | 15.52+14.87+14.50+3.51 = **48.40 GB** | 48.40 | ✅ |

Unsloth `unsloth/Qwen3-Coder-Next-GGUF`（同样直读 tree）——原报告只列了 3 个，实际选择面大得多：

| 文件 | GB | 文件 | GB |
|---|---|---|---|
| UD-Q4_K_XL | 49.61 | Q4_K_M | 48.53 |
| UD-Q4_K_M | 49.30 | **Q4_0** | **45.33** |
| UD-Q3_K_M | 35.94 | **IQ4_XS** | **42.68** |
| UD-Q3_K_XL | 36.28 | Q4_K_S | 45.53 |
| UD-Q2_K_XL | 26.76 | MXFP4_MOE | 48.03（Blackwell 专用，Volta 死路） |
| UD-TQ1_0 | 18.94 | UD-IQ1_M | 21.70 |
| UD-IQ2_XXS | 23.31 | UD-IQ3_XXS | 28.48 |

> **对 64 GB 显存的直接含义**：官方 Q4_K_M 48.40 GB + 262K ctx 的 f16 KV（24 KiB/token × 262144 = 6.44 GB）= 54.84 GB，只剩 ~9 GB 给 compute buffer + 激活 + 递归 state（36 层 × 32 头 × 128×128 × 4 B = 75.5 MB/序列）。用 **Unsloth Q4_0 45.33 GB** 或 **IQ4_XS 42.68 GB** 余量立刻宽 3–6 GB。

### 1.3 ollama 库版

- `https://ollama.com/library/qwen3-coder-next`（HTTP 200，80705 B）：tags `latest` / `q4_K_M` = **52 GB · 256K context window**；`q8_0` = 85 GB；页面标 **2.1M Downloads**；明写 “Non-thinking mode only”。
- registry manifest：`curl -sL -H "Accept: application/vnd.docker.distribution.manifest.v2+json" https://registry.ollama.ai/v2/library/qwen3-coder-next/manifests/latest` → model layer **51.74 GB**（digest sha256:30e51a7c…），params layer = `{"temperature":1,"top_k":40,"top_p":0.95}`。→ ollama 版比官方 GGUF 多 3.3 GB，64 GB 显存下更紧。

### 1.4 官方技术报告（一手，厂商自报）

`https://export.arxiv.org/api/query?id_list=2603.00729` → **arXiv:2603.00729v1《Qwen3-Coder-Next Technical Report》, 2026-02-28**（README 里 `@article` 引用一致）。
HTML 全文：`https://arxiv.org/html/2603.00729v1`（HTTP 200，301 KB）。

- **SWE-Bench Verified（Table 3）**：Qwen3-Coder-Next = **70.6**（SWE-Agent）/ **71.1**（miniSWE-Agent）/ **71.3**（OpenHands）。同表基线（Qwen 自己复现的）：Claude-Opus-4.5 78.2/77.8/79.0、Claude-Sonnet-4.5 76.0/68.4/74.6、DeepSeek-V3.2 70.2/67.2/72.6、GLM-4.7 74.2/70.4/70.6、MiniMax-M2.1 74.8/70.4/71.0、Kimi-K2.5 73.2/70.8/–。**max agent turns = 300**。
- **Terminal-Bench 2.0（Table 5）**：**34.2**（Terminus2-xml）/ **36.2**（Terminus2-json）/ **30.9**（ClaudeCode）/ **25.8**（QwenCode）。→ 原报告只写 “TB 2.0 36.2”，**漏掉了 25.8 这个下界**（同一模型不同 scaffold 差 10.4 分，说明该模型的 CLI 题分数对 harness 极敏感）。
- SWE-Bench Pro：**44.3%（826/1865，约 150 agent turns/题）**——该数字在 Figure 1（图片），由 HN 用户 yorwba 复述（HN id=46873700，2026-02-03）。
- **报告里没有任何速度/吞吐数字**：`tokens per second` 出现 **0** 次、`RTX 4090` **0** 次、`A100` **0** 次、`inference cost` **0** 次；只有 `throughput` 2 次（指训练/合成吞吐）。→ **“厂商自报速度”不存在**；原报告也没编造，但也没指出「速度侧只有 ollama/社区/AA 三个外部来源」这一事实。

---

## 2. V100（sm_70）可运行性核查

### 2.1 引擎与版本（本机实测）

```
$ ssh anolis 'ls -la ~/.local/lib/ollama/ | tail -30'
libllama.so.0.7.0 ... libllama-server-impl.so ... llama-quantize ... llama-server
$ ssh anolis '~/.local/bin/ollama --version'   → ollama version is 0.40.6
$ ssh anolis 'strings ~/.local/lib/ollama/libllama.so.0.7.0 | grep -i qwen3'
  %s: detected Ollama-format qwen35 GGUF; applying compatibility fixes
  %s: detected Ollama-format qwen35moe GGUF; applying compatibility fixes
  %s: detected Ollama-format qwen3next GGUF with ssm_dt tensors; applying compatibility fixes
  18llama_model_qwen3moe / 21llama_model_qwen35moe / 21llama_model_qwen3next
  /build/llama-server-cpu/_deps/llama_cpp-src/src/models/qwen3next.cpp
```

- ✅ **原报告的修正成立**：本机确有独立 `llama-server`（原任务前提“没有独立 llama-server 二进制”不成立）。`llama-server --help` 实测含 `--split-mode/--tensor-split/--cpu-moe/--n-cpu-moe/--fit-target/--cache-type-kv/--spec-type {none,draft-simple,draft-eagle3,draft-mtp,draft-dflash,...}`。
- ✅ **架构支持已就位**：ollama 0.40.6（GitHub release 页 datetime=**2026-10-16**，距今 5 天）的 runner 里明确有 `llama_model_qwen3next` 与 `qwen3next.cpp`。
- 上游 llama.cpp 已有 `qwen3next` 模型文件（`src/models/qwen3next.cpp`），非实验分支。

### 2.2 sm_70 硬件路径（上游源码直读）

| 项 | 证据 | 结论 |
|---|---|---|
| CUDA 编译目标含 sm_70 | `ggml/src/ggml-cuda/CMakeLists.txt:44` → `list(APPEND CMAKE_CUDA_ARCHITECTURES 50-virtual 61-virtual 70-virtual)`（CUDA<13 时） | ✅ 支持 |
| CUDA graphs 是否给 V100 | `ggml/src/ggml-cuda/ggml-cuda.cu:4794` → `if (cc < GGML_CUDA_CC_VOLTA) disable_due_to_gpu_arch = true;`，`common.cuh:52` `#define GGML_CUDA_CC_VOLTA 700` | ✅ **V100S (cc=7.0) 不被禁用，白拿 CUDA graphs**（原报告正确） |
| 混合线性注意力（GDN）的 CUDA 快路径 | `ggml/src/ggml-cuda/gated-delta-net-mma.cu:388,404-405`：`ggml_cuda_gdn_mma_launch` 仅在 `H_k==16 && H∈{16,32,48,64} && n_tokens>=64` 且 `cc ∈ {AMPERE_GA10X(8.0), ADA_LOVELACE(8.6), BLACKWELL, DGX_SPARK}` 时启用，否则 `return false` 回落到通用 kernel（`gated_delta_net.cu:357-360`） | 🔴 **原报告完全没提的新硬约束**：V100 上 36 层 GDN 走**无 MMA 的通用 fp32 kernel**；且 `n_tokens>=64` 意味着 hybrid 模型的 MTP/投机解码在 V100 上拿不到该快路径 |
| GDN 通用 kernel 的 decode 开销 | 递归 state 尺寸 = 32 头 × 128×128 × 4 B = 2 MB/层/序列 → 36 层 = 75.5 MB/序列，状态读写流量 ~4 MB/层/token → 理论上限 >10k tok/s | 判定：**不是** decode 的主瓶颈（主瓶颈是 512 专家的小 GEMM，见 §3.2） |

### 2.3 格式死路（在 Volta 上）

| 格式 | 状态 | 证据 |
|---|---|---|
| FP8 | ❌ 死路（Volta 无 FP8 张量核） | `Qwen/Qwen3-Coder-Next-FP8` 确实存在（downloads 1,034,239，F8_E4M3 78,995,521,536 参数 ≈ 79 GB），但即便体积合适也跑不了 |
| MXFP4 / NVFP4 | ❌ 死路（Blackwell sm_100/sm_120） | Unsloth 仓库有 `MXFP4_MOE 48.03 GB`，V100 不可用 |
| BF16 | ❌ 死路（Volta 无 BF16 张量核；llama.cpp 走 f16 模拟，精度/速度双亏） | `torch_dtype=bfloat16` 仅为训练态 |
| INT8 | ⚠️ 降级路线（dp4a，非张量核；sm_61 才有真 DP4A，sm_70 走 sm_61 同级实现） | P100 fork FINDINGS：“The DP4A emulation applies to all of sm_60” |
| **GGUF Q4_K_M / Q4_0 / IQ4_XS** | ✅ **唯一可行路** | llama.cpp/ollama 生态，体积可控 |

### 2.4 已知坑（本次新增/纠正）

1. **前缀缓存：原结论过度泛化 → 需降级**
   - 原始出处是 Kmic-68 fork 的 `p100-docs/FINDINGS.md`（"Serving at long context" 段）：“Restoring a saved slot and resending the original prompt still reprocesses everything, because the saved state includes generated tokens.”——讲的是**落盘 slot save/restore**。
   - 上游对应 issue：**#25913 “server : preserve context checkpoints across slot save/restore”**，状态 **MERGED**（HTML 内 `state":"MERGED"` 可见，2026-08-04 开、8 月内合入）。第三方复现贴（#25913 body 9，Qwen3.8-Flash-Next / Vulkan / Ryzen AI Max+ 395，5,892 token 前缀）给出三行对照：
     - cold 5,892 tok → 19,057 ms
     - after `action=restore` 5,892 tok → 19,238 ms（restore 价值为 0）
     - **in-memory warm slot（不 restore）→ 4 tok → 496 ms** ← 进程内复用是有效的
   - 本机 ollama 0.40.6 runner 二进制里已含 prompt checkpoint 机制：`strings libllama-server-impl.so | grep checkpoint` → `common_prompt_checkpoint::load/update/clear`、`server_context_impl::load_slot_checkpoints`、`slot ... created speculative checkpoint (pos_min=..., n_tokens=...)`。→ 我们的 ollama 路径**不走**落盘 restore。
   - **结论修正**：原报告「换到 Coder-Next 后每轮工具调用都要重算整个对话」**不成立**（至少没有证据支持）。仍**未实测**的是：ollama 0.40.6 对 hybrid 模型在**进程内**是否复用前缀——这一项必须在我们自己的 af-bench 上用 10 轮工具调用实测，不能引第三方结论代替。
2. **NaN race：原结论需推翻**
   - 出处：Kmic-68 fork **PR #4**（`https://github.com/Kmic-68/llama.cpp/pull/4`），commit `8d601afcfc2056d7e8411201fc4b87edc2155d88`，2026-10-08，标题 “cuda: fix race condition in fattn_gemm_softmax causing intermittent NaNs”。patch 原文：
     ```
     Affected: the generic branch of ggml_cuda_flash_attn_ext_gemm (pre-Volta, nkv >= 4096,
     >= 128 query rows, KV type other than q4_0, e.g. f16/q8_0). q4_0 caches go to the fold
     kernels... decode/verify never enter this path.
     Repro (2x P100, -sm tensor, Qwen3.8-27B Q6_K, 13 prompts of 5.8k-7.9k tokens x3 passes):
       f16 KV:  NaN 10/39 -> 0/39; prompts whose logits differ between identical passes 8/13 -> 0/13
       q8_0 KV: NaN  8/39 -> 0/39
     ```
   - **三处错**：①该文件 `ggml/src/ggml-cuda/fattn-gemm.cu` 是 **fork 私有**，上游 master 无此文件（`raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/fattn-gemm.cu` → **HTTP 404**；上游该目录只有 fattn.cu / fattn-tile.cu / fattn-mma-f16.cuh / fattn-vec.cuh / fattn-common.cuh）→ 不是“上游未修的 bug”；②修复**已在 fork PR #4 落地**；③受影响路径写明是 **pre-Volta**，**V100 (sm_70) 不在范围内**，且 decode/verify 不走该路径。
   - fork 自己的 “Known gaps” 也写明：两卡物理部署是 bit-stable，“nothing that ships is affected”。
   - → 原报告的「prone 到未修的 Volta NaN race（必须用 q4_0 KV 规避）」**需推翻**；改为：**若采用 Kmic-68 fork 的 P100 补丁，则 V100 走的是上游 tile/vec 路径，不受此 race 影响**。
3. **上游 hybrid/recurrent 模型的其它已知 issue（本轮扫到的）**
   - #29002（open）“hybrid (LFM2) models: co-batching sequences corrupts the recurrent/short-conv state” → **并发多序列会污染递归 state**。我们 `OLLAMA_NUM_PARALLEL=2`，**并发 2 场景必须单独冒烟**（原报告未提）。
   - #20596（open）`ggml-cpu: improve --n-cpu-moe TG performance` → CPU 专家卸载的 TG 性能是已知痛点。
   - #28241（open）“CUDA illegal memory access with -cmoe on Turing (sm_75)” → `--cpu-moe` 在老卡上有已报 bug（sm_75，非 sm_70，但同代风险）。
   - #19382（closed）Qwen3-Coder-Next produces invalid JSON tool calls；#19305（closed）Poor Outputs；#27727（open）abliterated GGUF garbled output → 工具调用稳定性有历史 issue，需在 af-bench 上专门验 tool-call 解析。
   - #30357（open）server: reasoning/content whitespace 不可往返 → prefix-cache invalid（Qwen3.5+ 模板），对我们 10 轮会话的续接有参考价值。
4. **磁盘**：48.4 GB（官方）/ 51.74 GB（ollama）需要空间；`/data` 现剩 18G，运营者已明确授权扩容 → **不作为淘汰理由**；但需注意 ollama 版比官方版多 3.3 GB 显存占用。

### 2.5 ❌ 一个被原报告说错的“优势”：现役已经能跑满 262K

本机 ollama 服务日志（`/data/models/ollama-serve.log`，2026-10-20 05:29 段）实读：

```
ggml_cuda_init: found 2 CUDA devices (Total VRAM: 64988 MiB):
  Device 0: Tesla V100S-PCIE-32GB, compute capability 7.0, VMM: yes, VRAM: 32494 MiB
  Device 1: Tesla V100S-PCIE-32GB, compute capability 7.0, VMM: yes, VRAM: 32494 MiB
load_tensors: offloaded 49/49 layers to GPU
  CUDA0 model buffer size = 8975.64 MiB
  CUDA1 model buffer size = 8548.79 MiB
llama_context: n_ctx = 262144 ; n_ctx_seq = 262144
llama_kv_cache: CUDA0 KV buffer size = 12800.00 MiB
llama_kv_cache: CUDA1 KV buffer size = 11776.00 MiB
sched_reserve: CUDA0 compute buffer size = 4624.22 MiB
common_params_fit_impl: CUDA0: 32494 total, 26399 used, 5784 free vs. target of 1024
srv load_model: initializing, n_slots = 1, n_ctx_slot = 262144
```

- 96 KiB/token × 262144 = 24.6 GB KV，**被拆到两张卡**（12.8 + 11.8 GiB），模型 17.5 GiB + compute 4.6 GiB 全部在 GPU，**仍剩 5.7 GiB**。
- 日志里同时存在 `n_slots=2, n_ctx_slot=8192`（4 次）与 `n_ctx_slot=262144`（11 次）两组运行 → **num_ctx 8192 是那次 bench 的选择，不是硬件限制**。
- → 原报告「现役单卡 32GB 装不下 262K KV（这正是现役只能用 num_ctx 8192 的原因）」与「Coder-Next 首次让本地跑满 262K 长上下文」**两条都要删**。262K 本身现役就能跑。

---

## 3. 速度证据核查

### 3.1 第三方实测（全部为独立用户，非厂商）

| 硬件 / 模型 / 引擎 | 数字 | 出处（可复核） |
|---|---|---|
| **3× RTX 3090**，Qwen3-Next-80B-A3B **Q6_K 61.20 GiB**，`-ngl 99 -fa 1`，`llama-bench -p 512 -n 512` | **pp512 565.84 t/s，tg512 42.45 t/s** | llama.cpp issue **#17822** body 1（https://github.com/ggml-org/llama.cpp/issues/17822） |
| 1× RTX 3090 24GB（VM 透传），unsloth UD-Q4_K_XL，256k ctx，llama.cpp | **32 t/s** | HN id=47064279（nyrikki, 2026-02-18） |
| 1× RX 7900 XTX 24GB（Vulkan），unsloth UD-Q4_K_XL，ctx 32768 | **~39 t/s @ 60% GPU util** | HN id=46874841（genpfault, 2026-02-03） |
| Framework Desktop（Strix Halo 128GB，ROCm），UD-Q4_K_XL | **eval 200–300 t/s / 输出 35–40 t/s** | HN id=46880395（redwood_, 2026-02-04）；另 36 t/s 见 id=47810502（UncleOxidant, 2026-04-17） |
| 2× DGX Spark，Qwen3 Coder Next | **~35 t/s** | HN id=48146804（rsolva, 2026-05-15） |
| 6 GB 显存笔记本，`--cpu-moe --n-gpu-layers 999 --ctx-size 102400` | **17 t/s @100k** | HN id=46878920（predkambrij, 2026-02-03） |
| M4 Max 128 GB，llama.cpp Q4_0 / MLX 4bit / 自研 Metal | **70.9 / 80.6 / ~120 t/s** | HN id=48508826 + story 48556552（LoganDark, 2026-06-12） |
| 4070 12GB（消费级） | “跑得动，性能不惊艳，比装得下的模型略慢” | HN id=48349115（kethinov, 2026-05-31） |

**对照（稠密 qwen3_5 系，同为 V100）：**
- 2× V100 32GB，Qwen3.6-27B **Q8_0**，`llama-server -c 131072 --tensor-split 0.4,0.6 --batch-size 256 --cont-batching --flash-attn on -ngl 999` → **~22 t/s（ctx<65k）→ ~13 t/s（近满）**｜HN id=48049546（neutrinobro, 2026-05-07）✅ 原报告引用属实
- 1× V100 32GB，Qwen3.6-27B UD-Q4_K_XL + MTP patch（turboquant fork），200k ctx → **45–60 t/s**｜HN id=48549139（henrixd, 2026-06-16）➕ 原报告未收录
- 单 V100，27B 4-bit，DeepSWE 实跑 → **~900 t/s prefill / ~100 t/s decode**（作者自称优化过 llama.cpp）｜HN id=49933921（bitexploder, 2026-10-02）

**本机现役（对照基线）**：ollama 日志实测 `eval time = 15038.44 ms / 2000 tokens → 132.93 t/s`、`1864.49 ms / 256 tokens → 136.77 t/s`、`1803.71 ms / 256 tokens → 141.37 t/s`（num_ctx 8192, n_slots 2）。

### 3.2 关键推论：为什么「同量级」这个假设站不住（这是本次复核的核心）

- Coder-Next 每 token 需读 ≈ 3B 激活参数 × 4 bit ≈ **1.5 GB**（与现役 30B-A3B 的 1.5–2.0 GB 同量级）。
- 但实测有效带宽：
  - 3×3090（合计 ~2.8 TB/s 规格）→ 42.45 t/s × 1.5 GB ≈ **64 GB/s ≈ 峰值的 2%**
  - M4 Max（400 GB/s）→ 70.9 t/s × 1.5 GB ≈ **106 GB/s ≈ 峰值的 26%**
  - Strix Halo（256 GB/s）→ 36 t/s × 1.5 GB ≈ **54 GB/s ≈ 峰值的 21%**
  - 本机现役 2×V100S（1.8 TB/s 规格）→ 135.7 t/s × ~1.9 GB ≈ **258 GB/s ≈ 峰值的 14%**
- → **Coder-Next 的 decode 根本不是显存带宽受限**：它被「512 专家 × 48 层 = 每 token 480 组极小 GEMM + 36 层 GDN 递归 kernel」的指令/启动开销卡死（对比现役 128 专家 top-8 + 纯注意力，kernel 形态友好得多）。**这意味着给更多显存带宽救不了它**，也意味着原报告 I1「预期 90–140 t/s，与现役同量级」是**方向性错误**。
- 同栈第三方测量也支持这一点：Artificial Analysis 用同一套方法测官方 API：
  - **Qwen3 Coder Next：97 t/s**（AA II = 9）
  - **Qwen3 Coder 30B A3B Instruct（现役）：158 t/s**（AA II = 10）
  - Qwen3.6-35B-A3B：134 t/s（AA II = 18）
  - Qwen3.8 27B (Xhigh)：45 t/s（AA II = 34）
  → 在**同一厂商、同一条服务链**上，现役比 Coder-Next **快 1.63 倍**。
- **对本机的合理预期（推断，未实测）**：2×V100S 跑 Coder-Next Q4_K_M → **30–60 t/s**（比现役 135.7 t/s **慢 2–4 倍**）。推导依据：3×3090（1.55× 于我们的总带宽）全驻留仅 42.45 t/s；我们没有比 3×3090 更好的机制，且 V100 还要额外吃 GDN 无 MMA 的代价。**该数字是推断，不是实测，必须在 anolis 上跑一次 `llama-bench -m ...-Q4_K_M.gguf -ngl 999 -ts 1,1` 才能定案。**

### 3.3 「没有 Coder-Next 在 V100/P100 上的任何第三方实测」——**成立**

本轮用 HN Algolia API（story + comment，多组关键词 + 时间窗）检索 `V100 / P100 / Qwen3-Coder-Next / tok/s / llama.cpp` 共 200+ 条；**命中的 V100 条目全部是 qwen3_5 稠密 27B / 35B-A3B，或 Qwen3.8-Flash-Next 3bit，没有一条是 80B-A3B 的 Coder-Next**（sonzohan id=48347653 还写着“我在考虑再买一张 V100 来跑 qwen3-coder-next”）。原报告此处判断正确。

### 3.4 P100 fork 的数字：属实但**不能直接套用到我们**

`Kmic-68/llama.cpp`（p100-optimizations 分支）README 原文：“runs at 1.86x upstream's speed (**17.5 -> 32.6 t/s**), and ~3x with the model's built-in MTP head (**~54 t/s**). Prefill runs at ~2x (**250 -> 493 t/s** at short context)”；QUICKSTART 表：MTP 54 t/s @2k → 29–33 t/s @260k；perplexity 2.61。
- ✅ 数字属实（我逐条对过 README/QUICKSTART/FINDINGS/CHANGES）。
- ⚠️ 但它是 **fork、2×P100-16GB(sm_60)、稠密 Qwen3.8-27B**，不是上游、不是 V100、不是 Coder-Next。原报告把它称为“最强证据”，同时又用它推 Coder-Next 的速度——这两件事不能划等号。**它能证明的是「稠密 27B 在老卡上很慢（2×P100 只有 17.5→32.6 t/s）」，恰好支持「MoE 比稠密快」这一半假设。**

---

## 4. 质量证据核查：有没有第三方独立复现？

### 4.1 第三方独立复现 = **没有**

- **SWE-bench 官方榜（Verified）**：抓 `https://www.swebench.com/`（2.39 MB），解析出 **132 条 verified 记录**（日期范围 2023-10-10 … **2025-12-15**）。
  - `"model_display": "…Coder-Next…"` 命中 **0** ✅ 原报告正确。
  - 现役 `Qwen3-Coder-30B-A3B-Instruct`：**60.4**（EntroPO + R2E, 2025-09-01）、**52.2**（EntroPO + R2E）、**51.6**（OpenHands, 2025-08-05）→ 原报告只提了 60.4 与 51.6，漏 52.2。
  - `Qwen3-Coder-480B-A35B-Instruct`：**69.6**（OpenHands, 2025-08-05）✅。
  - ⚠️ 补充事实：该榜最新记录停在 **2025-12-15**，即已 10 个月未更新 → “0 命中”更可能反映**榜单不活跃**，而不是模型没被测过。原报告把它当成“Coder-Next 缺席官方榜”的强证据，需要加上这句限定。
- **无第三方 harness 复现 SWE-bench Verified**：本轮未找到任何非 Qwen 方的 Coder-Next SWE-V 复现。**70.6% 只能算厂商自报。**
- **唯一可用的第三方同口径比较 = Artificial Analysis Intelligence Index v4.3.2**（含 Terminal-Bench 4.0 等 10 项；AA 页面明示 “Evaluation results measured independently by Artificial Analysis”）。逐个模型页实读：
  | 模型 | AA II | 输出速度 | 页面 URL |
  |---|---|---|---|
  | Qwen3 Coder Next | **9**（同类中位数 7） | **97 t/s** | /models/qwen3-coder-next |
  | Qwen3 Coder 30B A3B Instruct（**现役**） | **10**（中位数 6） | **158 t/s** | /models/qwen3-coder-30b-a3b-instruct |
  | Qwen3.6-35B-A3B | **18** | **134 t/s** | /models/qwen3-6-35b-a3b |
  | Qwen3.8 27B (Xhigh) | **34**（中位数 8） | **45 t/s** | /models/qwen3-8-27b |
  - **注意**：同为非 reasoning 的现役 30B（10 分）**高于** Coder-Next（9 分），且快 1.63 倍。原报告只写了 Coder-Next=9、35B-A3B=18、27B=34，**没有写现役的 10 分**——这是最关键的一处遗漏。
  - 原报告“AA II 对非 reasoning 的编码模型系统性低估，我们不应以 AA II 排序”是**未经证实的辩解**：同表里同为非 reasoning 的现役模型得分更高。
  - ❌ **无法核实**：AA 的 Terminal-Bench 4.0 单项分（模型页与 /evaluations/terminalbench-4-0 均为客户端渲染，静态 HTML 里只有模型清单、无分值表；`/api/v2/data/llms/models` 返回 401 需 key）。因此“Qwen3-Coder-Next 的 TB4.0 单项分”本轮**未取到**，不做断言。

### 4.2 社区主观评价：**反对换的证据比原报告收录的多**

- UncleOxidant（HN id=48834700, 2026-07-08）：“Qwen3-coder-next is very usable. But **I don't think it's as good as Qwen3.6-27B** (though it does run faster on my hardware).”（原报告已引）
- **thot_experiment（HN id=47871772, 2026-04-23）**：“**Qwen Coder 30B A3B is far better than Qwen Coder Next imo** … I don't find the 80B to be much better at coding, even in instruct mode, and **the insane speed and low latency of the smaller model is way more useful**. Good one-line completions often happen in 300ms.” ← **原报告漏引**（这条与我们的工作负载最像：10 轮工具调用、单题墙钟敏感）
- **KronisLV（HN id=49359045, 2026-08-19）**：“…the same with **Qwen 3 Coder Next (80B)**, and at least the most recent versions are getting better but still **not quite good enough in real world use cases outside of benchmarks**.” ← **原报告漏引**
- **lambda（HN id=47369087, 2026-03-13）**（Strix Halo 128GB）：“Qwen3-Coder-Next (80B/3B active) feels quite **on speed, though not quite as smart**.” ← **原报告漏引**
- 也有一侧：KronisLV 早期（id=48211279）把 Coder-Next 列为可跑 128GB 机器的推荐；redrove/redwood_ 实测 35–40 t/s 后用于 Claude Code。
- 结论：**社区对「它到底强不强」是分裂的，且针对“换成它”有 3 条明确的反向意见**，原报告只取了 1 条。

---

## 5. 另外两个复核对象（简表）

| 项 | Qwen3.6-35B-A3B | Qwen3.8-27B |
|---|---|---|
| HF 主仓 | `Qwen/Qwen3.6-35B-A3B` 存在，model_type `qwen3_5_moe`，BF16 35,951,822,704 参数，apache-2.0，downloads 3,641,803，likes 3,012，created 2026-04-15 | `Qwen/Qwen3.8-27B` 存在，model_type `qwen3_5`，BF16 27,781,427,952，apache-2.0，downloads 7,586,857，likes 18,071，created 2026-08-05 |
| GGUF | Unsloth UD-Q4_K_M **22.13 GB** ✅ 原报告数值属实；MXFP4_MOE 21.71（Volta 死路）；另有 `35b-a3b-coding` 变体 | Unsloth UD-Q4_K_M **16.46 GB** ✅；**Q4_0 16.06**；Q8_0 29.05；**MTP 头 `MTP/mtp-Qwen3.8-27B-Q4_0.gguf` 1.37 GB**（存在，可作 draft） |
| ollama | `qwen3.6:35b-a3b` 23–24 GB、256K ✅；另有 `35b-a3b-coding` / `…-mtp-q8_0` 等 tag | `qwen3.8:27b` 18 GB、256K ✅；有 `27b-mtp-q8_0` tag |
| AA II / 速度 | 18 / 134 t/s | 34 (Xhigh) / 45 t/s |
| “Coder390” | — | **不是 Qwen 官方模型**：`Coder390` 是社区微调（`nerkyor/Qwen3.8-27B-Coder390-EfficientThink-…`、`huihui-ai/Huihui-Qwen3.8-27B-Coder390-EfficientThink-abliterated-GGUF` 等）。原调研把它当“官方稠密 27B 候选”来用，属定性错误 |
| V100 可跑性 | ✅ GGUF 22 GB，单卡绰绰有余 | ✅ GGUF 16.5 GB；但同为 `qwen3_5` 混合线性注意力 → 同样有 §2.4 的 hybrid 注意事项，且稠密 decode 慢（2×V100 22→13 t/s，见 §3.1） |

---

## 6. 「V100 上到底能不能跑」的落地方案（若仍要试 Coder-Next）

**结论：能跑，且不需要任何 exotic 格式；但按现有证据，它在我们的负载上大概率是净负。**

推荐做法（全部只读/低风险，可立即执行）：

```bash
# 0) 先在 anolis 上确认官方 Q4_K_M 的 4 个分片已下载（不下载权重，先只算账）
#    官方 Q4_K_M = 48.40 GB（4 分片）→ 64 GB 显存余量 ~15.6 GB
#    262K ctx 的 f16 KV = 24 KiB/token × 262144 = 6.44 GB（GDN 递归 state 另加 75.5 MB/序列）
#    若余量太紧 → 改用 Unsloth Q4_0 45.33 GB / IQ4_XS 42.68 GB

# 1) 引擎：直接用本机 ollama 0.40.6（runner 已含 qwen3next 架构），或独立 llama-server
ssh anolis
~/.local/lib/ollama/llama-server --version
#    冒烟（单卡 32GB 装不下 48.4GB → 必须双卡 + --split-mode layer --tensor-split 1,1）
LD_LIBRARY_PATH=$HOME/.local/lib/ollama \
  ~/.local/lib/ollama/llama-server \
    -m /data/models/Qwen3-Coder-Next-Q4_K_M-0000{1,2,3,4}-of-00004.gguf \
    --split-mode layer --tensor-split 1,1 -ngl 999 \
    --cache-type-k q4_0 --cache-type-v q4_0 \      # 省 ~3.2 GB
    --flash-attn on -c 32768 --port 8081
#    ⚠️ 若出现乱码/NaN：换 --flash-attn off 复测（上游 tile/vec 路径），并用 q4_0 KV
#    ⚠️ 并发 2 必须单独测（llama.cpp #29002：hybrid 模型并发会污染递归 state）

# 2) 速度定案（这是我们最缺的一个数）：用 llama-bench 而非服务端
LD_LIBRARY_PATH=$HOME/.local/lib/ollama ~/.local/lib/ollama/llama-bench \
  -m /data/models/Qwen3-Coder-Next-Q4_K_M-00001-of-00004.gguf \
  -ngl 999 -ts 1,1 -p 512 -n 512 -fa 1
#    对照：现役 qwen3-coder-30b 同样命令（预期 ~135 t/s）

# 3) 能力定案：必须在我们自己的 af-bench 上同口径跑 SWE-bench Verified / Terminal-Bench
#    —— 官方榜 0 命中、AA II 9 < 现役 10，没有任何外部数据能替代这一步
```

**决策建议**：
- 若目标是「零 API 成本的量产臂、每题 10 轮工具调用、单题墙钟敏感」→ **优先试 Qwen3.6-35B-A3B（AA II 18，134 t/s，22 GB 单卡绰绰有余，ollama 23–24 GB 库版直接可拉）**，它同时具备「能力分高于现役（18 > 10）+ 速度同档（134 vs 158，差距很小）+ 体积小一半」三个属性。
- Qwen3.8-27B（Xhigh，AA II 34）能力分最高，但输出只有 45 t/s 且 token 消耗 200M（是 Coder-Next 的 6 倍、现役的 ~6 倍）→ 在我们「墙钟=成本」的负载下大概率不划算。
- Qwen3-Coder-Next 若要保留在候选里，**准入条件应改为**：(a) 先在 anolis 实测 V100 上的 tok/s（必须 ≥ 现役的 60% 才继续）；(b) 证明 af-bench 10 轮工具调用的进程内前缀复用有效；(c) 在 af-bench 上跑出高于现役的解题率。三条缺一不可。

---

## 7. 证据索引（本轮实际执行的检查）

| # | 检查 | 命令 / URL | 结果 |
|---|---|---|---|
| C1 | 模型元数据 | `curl https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next` | 200，522,825 downloads，apache-2.0，qwen3_next |
| C2 | config.json | `curl https://hf-mirror.com/Qwen/Qwen3-Coder-Next/raw/main/config.json` | 48 层/512 专家 top-10/262144 ctx/head_dim 256 |
| C3 | 官方 GGUF 分片体积 | `curl "https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next-GGUF/tree/main?recursive=true"` | 32 条；Q4_K_M=48.40GB 等逐分片求和 |
| C4 | Unsloth GGUF 清单 | `curl "https://hf-mirror.com/api/models/unsloth/Qwen3-Coder-Next-GGUF/tree/main?recursive=true"` | UD-Q4_K_XL 49.61 / Q4_0 45.33 / IQ4_XS 42.68 / UD-TQ1_0 18.94 … |
| C5 | ollama 库页 | `curl https://ollama.com/library/qwen3-coder-next` | 52GB / 256K / 2.1M downloads / non-thinking only |
| C6 | ollama registry manifest | `curl -H "Accept: …v2+json" https://registry.ollama.ai/v2/library/qwen3-coder-next/manifests/latest` | model layer 51.74 GB |
| C7 | 官方技术报告 | `curl "https://export.arxiv.org/api/query?id_list=2603.00729"` + `curl https://arxiv.org/html/2603.00729v1` | SWE-V 70.6/71.1/71.3；TB2.0 34.2/36.2/30.9/25.8；**无任何速度数字** |
| C8 | 上游 CUDA 架构 | `curl …/ggml/src/ggml-cuda/CMakeLists.txt`（L44）、`…/ggml-cuda.cu`（L4794）、`…/common.cuh`（L52） | sm_70 编译目标存在；CUDA graphs 对 cc≥7.0 开启 |
| C9 | GDN MMA 架构门槛 | `curl …/ggml-cuda/gated-delta-net-mma.cu`（L388,404-405）+ `gated_delta_net.cu`（L357-360） | MMA 仅 sm_80/86/120/spark；V100 回落通用 kernel |
| C10 | 上游无 fork 私有文件 | `curl -o /dev/null -w "%{http_code}" …/ggml-cuda/fattn-gemm.cu` | **404**（上游无此文件） |
| C11 | PR#4 原文 | `curl …/patch-diff.githubusercontent.com/raw/Kmic-68/llama.cpp/pull/4.patch` | “pre-Volta … NaN 10/39 -> 0/39 … decode/verify never enter this path” |
| C12 | P100 fork 文档 | `curl …/Kmic-68/llama.cpp/p100-optimizations/{README,FINDINGS,QUICKSTART,CHANGES}.md` | 17.5→32.6 t/s、MTP 54 t/s、prefill 250→493、ppl 2.61；slot restore 段落原文 |
| C13 | 上游 #25913 | `curl -A "Mozilla/5.0" https://github.com/ggml-org/llama.cpp/issues/25913` | 标题“server : preserve context checkpoints across slot save/restore”，`state":"MERGED"`；body 9 给出 warm-slot 4 tok vs cold 5892 tok |
| C14 | SWE-bench 官方榜 | `curl -A "Mozilla/5.0" https://www.swebench.com/` → 解析内嵌 JSON | verified 132 条；Coder-Next 0 命中；30B-A3B 60.4/52.2/51.6；480B 69.6；最新日期 2025-12-15 |
| C15 | AA 三个模型页 | `curl https://artificialanalysis.ai/models/{qwen3-coder-next,qwen3-coder-30b-a3b-instruct,qwen3-6-35b-a3b,qwen3-8-27b}` | II 9/10/18/34；t/s 97/158/134/45；II v4.3.2 含 Terminal-Bench 4.0 |
| C16 | AA TB4.0 单项分 | `curl https://artificialanalysis.ai/evaluations/terminalbench-4-0` + `/api/v2/data/llms/models` | 静态 HTML 无分值（客户端渲染）；API 401 → **无法核实** |
| C17 | HN 全量检索 | `hn.algolia.com/api/v1/search?query=…&tags=comment|story`（多组关键词） | Coder-Next 速度 7 条独立实测；V100 相关 9 条；**无一条是 Coder-Next on V100** |
| C18 | 本机 runner 能力 | `ssh anolis 'strings ~/.local/lib/ollama/libllama.so.0.7.0 \| grep -i qwen3'`；`llama-server --help` | qwen3next 架构在；`--split-mode/--tensor-split/--cpu-moe/--n-cpu-moe/--fit-target/--spec-type draft-mtp` 齐全；`common_prompt_checkpoint` 存在 |
| C19 | 本机运行实况 | `ssh anolis 'grep … /data/models/ollama-serve.log'` | cc 7.0 两卡、49/49 层 offload、n_ctx=262144、KV 12800+11776 MiB、余 5784 MiB；decode 132.9–141.4 t/s |
| C20 | 另两个候选 | `curl https://hf-mirror.com/api/models/{Qwen/Qwen3.6-35B-A3B,Qwen/Qwen3.8-27B}` + ollama 库页 | 参数/许可/下载量/体积如 §5 |

**未执行 / 无法核实的检查（明确列出）**：
- ❌ 未在 anolis 上实际加载 Coder-Next（未下载任何权重）→ **V100 上的 tok/s 至今无实测**，§3.2 的 30–60 t/s 是推断。
- ❌ 未实测 ollama 0.40.6 对 hybrid 模型的**进程内**前缀复用（§2.4-1）。
- ❌ AA Terminal-Bench 4.0 的 Coder-Next 单项分（客户端渲染 / API 401）。
- ❌ 任何第三方的 Coder-Next SWE-bench Verified 复现 —— **检索后确认不存在**（非“没找到”，是“确认没有”）。
- ❌ Reddit / X / Discord 侧证据：本轮未尝试（原报告称 DNS 污染不可达）；不影响上述结论，因为关键数据均可从 HF/GitHub/arXiv/AA/官方榜直接取到。

---

## 8. 一句话结论

**Qwen3-Coder-Next 的「事实层」（架构/体积/榜单/自报分数）原报告核查全部属实；但它的「推理层」有三处必须推翻：① 速度不会与现役同量级，反而大概率慢 2–4 倍（3×3090 全驻留仅 42.45 t/s，AA 同栈 97 vs 158 t/s）；② 「混合线性注意力打断前缀缓存」是落盘 restore 场景的问题、上游已修、进程内复用有第三方实测有效；③ 「Volta NaN race」是 P100 fork 私有 kernel 且只影响 pre-Volta。叠加「现役已经能在 2×V100S 上跑满 262K ctx」这一被误判的「优势」消失、且第三方独立质量复现为零（唯一同口径第三方 AA 上现役 10 分 > Coder-Next 9 分），原结论「Qwen3-Coder-Next 是唯一更值得上的候选」不成立。若要在本地池里换一个，更值得先试的是 **Qwen3.6-35B-A3B（AA II 18、134 t/s、22–24 GB）**。**
