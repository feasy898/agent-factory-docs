# 2026 · V100 sm_70 推理引擎全矩阵 + 本地模型选型

- **调研人**：本地模型选型调研子代理
- **调研日期**：2026-10-21
- **基准机器**：`anolis-gpu-01`，2× Tesla V100S-PCIE-32GB（CC 7.0 / sm_70）
- **基准负载**：af-bench harness（SWE-bench Verified / Terminal-Bench / InjecAgent / τ²-bench），每题约 10 轮工具调用，需要稳定 tool calling、跨轮不崩、能改代码、能读长日志；本地臂定位是"零 API 额度的量产臂"
- **现役模型**：`qwen3-coder-30b:latest` = Qwen3-Coder-30B-A3B-Instruct-Q4_K_M（18.56 GB，ollama 0.40.6 / llamacpp runner），实测 decode **135.7 tok/s**、prompt **149.1 tok/s**（num_ctx 8192）、加载 10.5 s
- **纪律**：本报告只写有来源的事实；来源分为「官方自报 / 官方文档 / 第三方复现 / 本机实测」四类，逐条标注。找不到的写「未找到公开证据」。**本轮未下载任何模型权重**，因此所有 tok/s 数字除"本机实测"外均为第三方复现或厂商自报。

---

## 0. 一句话结论

**在 2×V100S-32GB 上，现役 ollama/llama.cpp 仍是最优引擎**（唯一同时满足"支持新架构 + 支持双卡 + 免折腾 + 已有实测基线"的选项）；**候选模型里只有 `Qwen3-Coder-Next (80B-A3B, Q4_K_M 48.4 GB)` 同时满足"64 GB 显存装得下"和"解题率显著更高"**，但它的解码速度**不会**比现役 30B-A3B 快（两者激活参数都是 ~3B，带宽账一样），价值是**能力**不是**速度**。核心假设是"对了一半"：MoE-vs-稠密的带宽机制成立且已被数据证实（稠密 27B 在 V100 上确实慢 3-4 倍），但"80B-A3B 比 30B-A3B 更快"不成立。

---

## 1. 本机环境实测（2026-10-21，命令与输出见各条）

| 项 | 实测值 | 命令 |
|---|---|---|
| GPU | 2× Tesla V100S-PCIE-32GB，各 32768 MiB | `nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv` |
| 驱动 / 驱动可支持的最高 CUDA | 570.133.20 / **CUDA 12.8** | `nvidia-smi`（头部 "NVIDIA-SMI 570.133.20 … CUDA Version: 12.8"） |
| **GPU 互连拓扑** | GPU0↔GPU1 = **PHB**（经 PCIe Host Bridge），**无 NVLink** | `nvidia-smi topo -m` |
| **P2P 直访** | GPU0→GPU1 **OK**，GPU1→GPU0 **OK**（PCIe P2P 可用） | `nvidia-smi topo -p2p r` / `-p2p w` |
| CPU / 内存 | 16 vCPU / 125 GB（available 107 GB） | `nproc` / `free -g` |
| glibc / gcc | glibc **2.38** / gcc 12.3.0（libstdc++ 含 GLIBCXX_3.4.30） | `ldd --version` / `gcc --version` / `strings libstdc++.so.6` |
| Python | 系统 python3.11；**另有 /usr/bin/python3.12**（pip 26.2.1）；**无 uv** | `python3 --version` / `python3.12 -m pip --version` / `which uv` |
| CUDA 工具链 | `/usr/local/cuda-12.6`，nvcc **12.6.68** + 头文件齐全；**`lib64/` 只有 `libnvptxcompiler_static.a`，没有 libcudart / libcudadevrt** | `ls /usr/local/cuda-12.6/lib64` |
| ollama | **0.40.6**，`/api/version` = `{"version":"0.40.6"}` | `curl -s http://127.0.0.1:11434/api/version` |
| 现役模型元数据 | `qwen3-coder-30b:latest`，18,556,689,690 B，family `qwen3moe`，30.5B params，ctx 262144，runner `llamacpp`，capabilities `[tools, completion]` | `curl -s http://127.0.0.1:11434/api/tags` |

**两个此前未被记录、但直接影响部署的事实：**

1. **CUDA 工具链是"半套"**：有 nvcc 和头文件，但没有 `libcudart.so` / `libcudadevrt.a`。实测 `nvcc -arch=sm_70 -o p p.cu` 链接失败：`/usr/bin/ld: cannot find -lcudadevrt` / `cannot find -lcudart_static`。**结论：现在无法在 anolis 上从源码编译带 CUDA 的 llama.cpp**，必须先补装完整 CUDA Toolkit（`cuda-toolkit-12-6` 完整包）或不依赖 cudart 的构建方式。
2. **P2P 是通的**：PHB 拓扑不等于不能 P2P。`nvidia-smi topo -p2p r` 两向都 OK，所以 llama.cpp 的 `--split-mode layer` 双卡切分可以走 GPU 间 P2P，不必经主机内存往返；这比 NVLink 慢一个量级，但层间只传 hidden（Qwen3-Coder-Next hidden=2048，f16 → 每 token 每层边界 4 KB），带宽不是瓶颈。**`--split-mode tensor` 才是真瓶颈**（每次矩阵乘要跨卡归约）。

---

## 2. 引擎全矩阵（2026 · sm_70 / 32 GB V100）

| 引擎 | Volta/sm_70 真实状态 | 依据（可点开） | 27B 级模型在 32GB V100 上的可行性 | 参考 tok/s |
|---|---|---|---|---|
| **llama.cpp (CUDA)** | **完全支持，且有专用 Volta 路径**。默认 arch 列表含 `70-virtual`（仅 CUDA<13）；有 `VOLTA_MMA_AVAILABLE` 专用宏与 Volta FA 内核；2026-09/10 连续合入 5 个 Volta 修复 | `ggml/src/ggml-cuda/CMakeLists.txt:40-46`；`common.cuh:52,284-291,361-370`；`fattn.cu:223,672`；PR #28887/#28888/#28912/#29232/#29803 | ✅ 唯一全程在用的引擎 | **tg128 = 33.25 tok/s**（Qwen3.8-27B Q4_K_M，1×V100，issue #27366）；**69.36 tok/s**（同模型 + DFlash2 投机解码，PR #28912） |
| **Ollama 0.40.6**（内嵌 llama.cpp b11738） | 支持 `qwen3next` / `qwen35` / `qwen35moe`；能自动识别 MTP draft 头并开启 `EnableMTP`；库里有 `qwen3-coder-next:q4_K_M` | `llm/llama_server.go:877,912-913,936-945`；`llm/llama_server_test.go:2665-2740`；`LLAMA_CPP_VERSION`=b11738 | ✅ 我们的现役路径，零改动 | 实测 **135.7 tok/s**（qwen3-coder-30b） |
| **vLLM upstream** | **半支持，最后一条实用线是 0.19.x**。issue #47019 明确写"vLLM 0.19.x is the last broadly practical vLLM line for Tesla V100 users"；新版本砍掉 Volta 内核，Qwen3.5 加载不了（catch-22，issue #43561 仍 open） | vllm-project/vllm#47019 (2026-06-29) / #43561 (2026-05-25, open) / #38706 / #17541 | ⚠️ 能跑但要钉死版本 + 手动改 fused-MoE 配置 | 8×V100-SXM2 上 **Qwen3.6-35B-A3B：stock 15.6 (C1) / 24.9 (C8) tok/s → 调 BLOCK_SIZE_K 64 后 65.9 / 173.9**（#47019） |
| **1Cat-LLM（1Cat-vLLM 社区分叉）** | **专门为 Volta/SM70 做一等公民优化的 vLLm 分叉**。v1.5.1 (2026-10-03)：Flash-V100 内核、FlashQLA、split-D 注意力；要求 GLIBC≥2.38、GLIBCXX≥3.4.21、Python 3.12、Torch 2.10.0 + CUDA 12.8、SM70；建议驱动 ≥570.124.06 | github.com/1CatAI/1Cat-vLLM（README + v1.5.1 release，main 最后推送 2026-10-21） | ✅ **环境完全对得上**（glibc 2.38 ✓、py3.12 ✓、驱动 570.133.20 ✓、CUDA 12.8 ✓）；但需要另装 uv / Torch 2.10 | 4×V100-SXM2-32GB TP4：QUASAR-27B-NVFP4 + DFlash2 **4K 229.34 / 32K 201.18 / 128K 171.43 / 32K-C4 合计 445.45 tok/s**；Qwen3.8-27B-NVFP4 128K 61.834；+DFlash2 206.06 |
| **SGLang** | ❌ **明确拒绝 sm_70**。`maybe_downgrade_dtype_for_legacy_gpu()`：CC major<8 降 fp16，随后 `if minor < 5: raise RuntimeError("SGLang only supports sm75 and above.")` → V100(7.0) 直接抛错 | `python/sglang/srt/model_executor/model_runner_components/load_model_utils.py:78-90` | ❌ 不可用 | — |
| **TensorRT-LLM** | ❌ **Volta 支持已被删除**。0.14.0 标 deprecated，0.15.0 起 "[BREAKING CHANGE] NVIDIA Volta GPU support is removed in this and future releases"；`supported-hardware.md` 只列 Blackwell/Hopper/Ampere A100 | `docs/source/release-notes.md:759,823`；`docs/source/supported-hardware.md:4-7` | ❌ 不可用（要跑只能钉 0.14.0 之前的旧版，且 0.14.0 也只是 deprecated） | — |
| **TGI** | ❌ **官方支持列表不含 V100**："TGI optimized models are supported on NVIDIA H100, A100, A10G and T4 GPUs with CUDA 12.2+"（T4=Turing sm_75，V100=sm_70 不在其列）；仓库最后推送 2026-03-21，维护活跃度低 | `docs/source/installation_nvidia.md:3` | ❌ 不建议（且 TGI 依赖 FP8/FlashAttention 特性栈） | — |
| **exllamav2** | ⚠️ **未找到公开证据**表明支持 sm_70。`setup.py` 没有显式 arch 列表（走 torch 默认），源码里没找到 min-CC 检查；仓库最后推送 2026-03-04，维护近乎停滞 | 本地 clone `turboderp/exllamav2` 后 grep `compute capability / sm_75 / volta` 无命中 | ❓ 需自行冒烟 | — |
| **exl3 / exllamav3** | ❓ **未找到公开证据**：`github.com/turboderp/exllamav3` 返回 404（仓库不存在或已改名） | `git ls-remote https://github.com/turboderp/exllamav3.git` → "Repository not found" | ❓ | — |
| **LM Studio** | ⚠️ 底层就是 llama.cpp，Volta 能力与 llama.cpp **完全同源**（含同样的 Volta FA 修复）。但它是桌面 GUI 应用，我们这台 headless 机器没有它 | — | ❓ 本机未装，未验证 | — |
| **MLX / mlx-lm** | ❌ 与本机无关：MLX 是 Apple Silicon 专属（Metal） | HF 上 `mlx-community/*` 仓库均为 MLX 权重 | ❌ | — |
| **KTransformers** | ❓ 未验证。Qwen3-Coder-Next 官方卡把它列为支持方之一，但**未找到任何 V100/sm_70 的公开实测** | Qwen/Qwen3-Coder-Next README "For local use, applications such as Ollama, LMStudio, MLX-LM, llama.cpp, and KTransformers have also supported Qwen3" | ❓ | — |
| **其他（MoE-Infer / sgl-kernel / MLC 等）** | ❌/❓ 逐个未验证。已知 MoE-Infer 面向 Hopper/Blackwell 优化 | — | ❌ | — |

### 2.1 llama.cpp 在 Volta 上的四条关键路径（源码级）

| 路径 | Volta 上的状态 | 源码位置 |
|---|---|---|
| **CUDA arch 编译** | `70-virtual` 只在 **CUDA < 13** 时进默认列表：`if (CUDAToolkit_VERSION VERSION_LESS "13") list(APPEND CMAKE_CUDA_ARCHITECTURES 50-virtual 61-virtual 70-virtual) endif()` | `ggml/src/ggml-cuda/CMakeLists.txt:40-46` |
| **FlashAttention** | **有专用 Volta 分支，不是回退**：`volta_mma_available(cc)` 为真时走 Volta MMA 内核；注释"On Volta the GQA optimizations aren't as impactful"（L223）、"On Volta tensor cores are only faster for sufficiently large matrices"（L672-677） | `ggml/src/ggml-cuda/fattn.cu:223-240, 636-677`；`common.cuh:284-291, 361-370` |
| **MMQ（Q4 量化矩阵乘）** | `turing_mma_available` 在 V100 上为假（`highest_compiled_arch(700)=700 < 750`），走 dp4a 路径；`ggml_cuda_should_use_mmq()` 最后一段：`return !fp16_mma_hardware_available(cc) \|\| ne11 < MMQ_DP4A_MAX_BATCH_SIZE(=64)` → **V100 上 MMQ 只在 ne11<64（解码/短批）启用，长 prefill 走 cuBLAS** | `ggml/src/ggml-cuda/mmq.cu:355-424`；`mmq.cuh:8`；`common.cuh:327-330` |
| **混合线性注意力（Gated DeltaNet）** | ⚠️ **Volta 上是最弱的一档**：`gated-delta-net-mma.cu` 整段被 `#if defined(AMPERE_MMA_AVAILABLE)` 包住（V100 拿不到）；`ssm-scan.cu` 的 Mamba-2 SSD 快速路径要求 `cc >= GGML_CUDA_CC_TURING` → V100 落回**串行 scan** | `gated-delta-net-mma.cu:59,121,127,363,403`；`ssm-scan.cu:846-857` |

### 2.2 CUDA 12 vs 13 —— 这是我们最硬的"不可逆红线"

- **官方自报（NVIDIA 一手文档）**：
  - CUDA 13.0 release notes → Deprecations: "**Removed support for Maxwell, Pascal, and Volta GPUs, corresponding to compute capabilities earlier than Turing.**"
  - CUDA 12.8 release notes §1.5.1 "Deprecated Architectures": "Architecture support for Maxwell, Pascal, and Volta is considered feature-complete and will be frozen in an upcoming release."
  - 驱动对照表：CUDA 12.8 GA 要求 Linux 驱动 ≥ **570.26**；CUDA 12.6 Update 3 要求 ≥ 560.35.05
- **交叉验证（llama.cpp 侧独立做了同一件事）**：`ggml/src/ggml-cuda/CMakeLists.txt` 在 `CUDAToolkit_VERSION >= 13` 时把 `50/61/70-virtual` 整段跳过 —— 也就是说**上游已经默认 CUDA 13 装不出 sm_70 的代码**。
- **我们的现状**：`nvidia-smi` 报 CUDA Version 12.8，驱动 570.133.20（>570.26 ✓）。**CUDA 12.6 工具链在 anolis 上仍是 sm_70 可用的最后一档**；一旦把工具链升到 13，就必须锁死 `-DCMAKE_CUDA_ARCHITECTURES=70-virtual` 并接受 nvcc 本身已不支持 sm_70 的事实。
- **推论（推断，非官方）**：CUDA 13 的 nvcc 已不认 `compute_70`，所以 `-DCMAKE_CUDA_ARCHITECTURES=70-virtual` 这条路在 CUDA 13 上也未必成立 —— 我们不应把"升 CUDA 13"列进任何计划。

### 2.3 投机解码（MTP / DFlash2）在 Volta 上的可用性与已知 bug

| 项 | 状态 | 证据 |
|---|---|---|
| llama.cpp 侧实现 | ✅ 已合入：`common/speculative.cpp` 的类型表含 `draft-simple / draft-eagle3 / **draft-mtp** / **draft-dflash** / draft-dspark`；CLI 有 `--spec-type` / `--spec-draft-n-max`（默认 3）/ `--spec-draft-n-cpu-moe` 等 | `common/speculative.cpp:75-79`；`tools/server/README.md:249-266` |
| ollama 0.40.6 侧 | ✅ 会自动识别 MTP 头：`hasMTPDraft(f)` → `config.EnableMTP = true` → `draftType = draftTypeMTP`；`hasLegacyQwenMTPDraft` 对 `qwen35`/`qwen35moe` 认 `mtp.fc.weight` / `mtp.layers.0.attn_q.weight` | `llm/llama_server.go:936-945`；`llm/llama_server_test.go:2665-2745` |
| **DFlash2 在 V100 上实测可用** | ✅ 第三方复现：`incoai/Qwen3.8-27B-DFlash2-Q4_K_M` + `Unsloth-Qwen3.8-27B-UD-Q4_K_XL`，`--spec-draft-n-max 7`，V100 上 `predicted_per_second` **54.52 → 69.36**（合入 SM70 的 MMVQ/MMQ crossover 调优后，+27%） | llama.cpp PR #28912（2026-09-21 merged），作者 cyyself，附 V100 实测 gist |
| MTP 在 CUDA 上的收益 | 1Cat-LLM 在 4×V100 TP4 上：Qwen3.6-35B-A3B NVFP4 无 MTP 116.99 → +MTP4 **174.76 tok/s（1.49×）**；Qwen3.8 Flash-Next-NVFP4 80.732 → +MTP4 **138.26** | 1Cat-LLM README（引其 PR #270 / #389） |
| ⚠️ **`--split-mode tensor` + 多卡 Volta = 已知挂死** | issue #27366（2026-08-19，2026-10-03 以 stale 关闭）：3×V100-SXM2-32GB 上跑 `bartowski/Qwen3.8-27B-GGUF`（arch `qwen35`）——`-sm row` 直接报 `device CUDA1 does not support split buffers`（CUDA 后端没实现 `ggml_backend_split_buffer_type`，只有 SYCL 有）；**`-sm tensor` 在 llama-bench 里跑完后触发 `GGML_ASSERT(meta_buf_ctx->bufs[i]) failed`，在 llama-cli 里则挂死 7 分钟且双卡各占 8286 MiB 不释放**；`-sm layer` 正常 | llama.cpp#27366 全文 |
| ⚠️ **qwen35 架构的活跃 bug（2026-10 仍在）** | #30906（**2026-10-21 当天，open**）："CPU backend produces garbage for the qwen35 hybrid family (24 Gated DeltaNet + 4 gated full-attention layers)"，同二进制同 GGUF 的 Vulkan 后端正常；#29172（open）CUDA 在深 KV 位置 decode+prefill 崩塌（sm_120 上 ~5.5× tg、~21× pp @ d154855）；#27090（open）~520K prefill + YaRN rope-scale 4 静默崩溃；#29092（open，ROCm）fused GDN 状态跨请求串台；#27109（closed）4-bit KV 让 qwen35 prefill 塌到 ~34 t/s | llama.cpp issues，链接见正文 |
| ⚠️ **Volta 专有的历史坑（已修）** | #25835 VRAM 泄漏（CUDA Graphs on V100，#25749 引入）；#26044 sm_70 上 Qwen3-Embedding-8B 返回全 NaN embedding（CPU 正确）；#29255 sm_70 layer-split + 大 prefill + 部分前缀复用触发概率性 `invalid argument` kernel launch 错误 | llama.cpp issues |
| **好消息** | 上列 5 个 Volta 修复（#28887 稀疏 FA、#28888 lightning_indexer cuBLAS、#28912 MMQ crossover、#29232 FA Volta 修复、#29803 修 2 个坏掉的 Volta FA case）全部在 2026-09-14 ~ 2026-10-01 合入，**我们装的 ollama 0.40.6 固定 llama.cpp b11738（2026-10-20）已全部包含** | ollama `LLAMA_CPP_VERSION`=b11738；PR 日期见上 |

### 2.4 `--n-cpu-moe`（CPU 专家卸载）在 V100 上可行吗、代价多大

- **能力存在**：`--n-cpu-moe N`（把前 N 层的 MoE 专家权重留在 CPU）、`--cpu-moe`（全部专家留 CPU）、`--n-cpu-ffn N`（稠密 FFN 留 CPU）、`--moe-cache-mib N`（给 CPU 侧专家做 GPU 缓存，多卡时按 `--tensor-split` 分摊）—— 全部在 `common/arg.cpp:2760-2800` 与 `tools/server/README.md:82-84`。
- **代价（推断，基于带宽模型）**：把专家放 CPU 后，**每个解码 token 的活跃专家权重要走 PCIe（~16-32 GB/s）而不是 HBM2（~900 GB/s）**，单 token 延迟会增加一个数量级以上；`--moe-cache-mib` 只能缓存"少量"专家（3B 激活 → 10/512 专家），命中率低时收益有限。
- **判断（推断）**：**对我们不划算**。Qwen3-Coder-Next Q4_K_M = 48.40 GB，64 GB 显存本来就装得下；用 CPU 卸载换显存会直接违反"每 token 成本"这个核心指标。`--n-cpu-moe` 的正确用途是"装不下时的降级方案"，不是"提速手段"。
- **反面证据**：Qwen3-Coder-Next 官方卡自己写 "If you encounter out-of-memory (OOM) issues, consider reducing the context length to a shorter value, such as 32,768" —— 官方的降级手段是**降上下文**，不是 CPU 卸载。

### 2.5 1Cat-LLM 值不值得上（这是本轮唯一有分量的"新引擎"）

- **它是什么**：`github.com/1CatAI/1Cat-vLLM`（正在改名 1Cat-LLM），"V100 / SM70-focused vLLM engineering fork"，README 开头即 "Make Volta Fast Again"。
- **环境匹配度（我们实测 vs 它要求）**：GLIBC ≥2.38 → 我们 **2.38 ✓（贴线）**；GLIBCXX ≥3.4.21 → 我们 **3.4.30 ✓**；Python 3.12 → 我们 **有 python3.12 ✓**；CUDA 12.8 → 我们 **驱动支持 12.8 ✓**；驱动 ≥570.124.06 → 我们 **570.133.20 ✓**；SM70 → ✓。**唯一缺的是 `uv`（可直接装）和 Torch 2.10 + CUDA 12.8 runtime（需装，~2.5 GB）。**
- **它比 upstream vLLM 强在哪**：长上下文注意力有效算力 **17.92 → 47.1 → ~60.8 → ~71 TFLOP/s**（TP4/TP2/TP1 本地 head 布局分别 71.111 / 70.221 / 69.982 TFLOP/s，单卡 V100-SXM2-32GB 的算子级测量）。这正是 upstream vLLM 在 V100 上的短板（#47019 里 stock fused-MoE 只有 15.6 tok/s）。
- **它的硬限制**：
  1. 官方发布的所有模型级数字都是 **4×V100 TP4**，我们是 **2 卡**；TP2 只有一个**算子级** TFLOP/s 数字，**没有 2 卡整模型 tok/s**。按 4 卡→2 卡保守折半，Qwen3.8-27B-NVFP4 128K 的 61.8 tok/s → ~30 tok/s 量级，**低于我们现役的 135.7**。
  2. 发布 wheel 是 `1cat_vllm-1.5.1-cp312-cp312-linux_x86_64.whl`，README 自述 "**It has not passed the manylinux container gate**"（安装摩擦），且需要 CUDA Toolkit 做 TileLang JIT。
  3. **GGUF 支持只在 main 分支（2026-10-05 之后），不在 v1.5.1 wheel 里** —— 意味着要用 GGUF 必须自己从源码构建。
  4. 依赖链是 Torch 2.10.0 + CUDA 12.8，而 **CUDA 12.8 正是 NVIDIA 明文"Volta support feature-complete and will be frozen"的最后一档**。
  5. 社区分叉，单点维护；README 自述 "The rename is planned"，正在改名中。

---

## 3. 候选模型清单

> "Q4 体积"取官方 GGUF 仓库的文件字节数之和（hf-mirror API `?blobs=true`）；"官方 agentic 分数"只填能在**官方一手来源**（模型卡 / 官方技术报告 PDF）里查到的数字。

| 模型 | 厂商 | 稠密/MoE 及激活参数 | Q4 体积 | context | GGUF 可得性 | 官方 agentic 分数 | 第三方反馈（V100 相关） | 我们的适配判断 |
|---|---|---|---|---|---|---|---|---|
| **Qwen3-Coder-Next** | Qwen | **MoE**，80B 总参 / **3B 激活**；hybrid 12×(3×(GatedDeltaNet→MoE)→1×(GatedAttention→MoE))，48 层，512 专家取 10 + 1 shared，hidden 2048 | **Q4_K_M 48.40 GB**（官方 Qwen 仓库 4 shard：15.52+14.87+14.50+3.51）；Q5_K_M 56.71 / Q6_K 65.53 / Q8_0 84.81；**ollama 库版 q4_K_M = 52 GB** | 262,144 原生 | ✅ 官方 `Qwen/Qwen3-Coder-Next-GGUF` + unsloth + bartowski + lmstudio-community | **SWE-bench Verified 70.6（SWE-Agent）/ 71.1（MiniSWE-Agent）/ 71.3（OpenHands）**；SWE-bench Multilingual 62.8/56.2/64.3；**SWE-bench Pro 44.3/37.9**；**Terminal-Bench 2.0：Terminus2-xml 34.2 / Terminus2-json 36.2 / ClaudeCode 30.9 / QwenCode 25.8**；**仅非思考模式** | 1Cat-LLM 实测 **Qwen3.8 Flash-Next-NVFP4 无 MTP 80.732 → +MTP4 138.26 tok/s**（4×V100 TP4，PR #415/#389）——**注意这是 Flash-Next 不是 Coder-Next，Coder-Next 本身在 V100 上无第三方 tok/s 复现** | ⭐ **首选**。装得下（48.4/64 GB）、分数显著高于现役 30B、**且非思考模式 → token 成本低**。风险：速度不比现役快、qwen3next 架构在 Volta 上是"最弱的一档"（GDN 落回串行 scan）、`--split-mode tensor` 必须禁用 |
| **Qwen3-Coder-30B-A3B-Instruct（现役）** | Qwen | MoE 30.5B 总参 / ~3B 激活，`qwen3moe` | 18.56 GB（Q4_K_M，本机在役） | 262,144 | ✅ | 官方模型卡**未给文本版 SWE-bench Verified 表**（只有图片）；未找到可引用的官方文本分数 | 本机实测 decode **135.7**、prompt **149.1**、并发 2 时 109.7/请求、合计 219 | 基准线。**MoE 走的是成熟 `qwen3moe` 路径，不是 qwen3next/qwen35 混合路径，Volta 风险最低** |
| **Qwen3.8-27B** | Qwen | **稠密** 27B；64 层；hidden 5120；**16×(3×(GatedDeltaNet→FFN)→1×(GatedAttention→FFN))**；FFN 中间维 17,408；MTP 多步训练；原生 VLM | bartowski **Q4_K_M 17.44 GB** / Q5_K_M 20.92 / Q6_K 23.86 / Q8_0 29.12 | 262,144 原生，可扩 1M | ✅ bartowski 32 个量化 + unsloth；**ollama 官方库无此模型** | **Terminal Bench 2.1 (Terminus) 73.0**；**SWE-bench Pro 61.7**；NL2Repo-Bench 42.3；DeepSWE 1.1 42.2；QwenSWEBench 79.0；CoWorkBench 70.7；**SWE-bench Verified 官方卡未给** | llama.cpp#27366：**1×V100 tg128 = 33.25 tok/s**、pp4096 730.71；PR #28912：**+DFlash2 投机解码 → 69.36 tok/s**；1Cat-LLM：4×V100 TP4 NVFP4 128K 61.834 / 256K 50.376，+DFlash2 **206.06** | ❌ **不选**。稠密 → 每 token 要读 27B 权重 → 在 V100 上**只有现役的 1/4 ~ 1/2 速度**；且 `qwen35` 混合架构在 Volta 上 GDN 落串行 scan，#30906（今天）还在报 qwen35 输出损坏 |
| **Qwen3.6-35B-A3B** | Qwen | MoE 35B / 3B 激活，`qwen3_5_moe` | 未查（HF 无官方 GGUF） | 262,144 | ⚠️ 未找到官方 GGUF（社区有 `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` 等衍生） | 未找到一手表 | llama.cpp#28037：SM72 上 Q4_K_M 20 GB → decode 20.85 t/s；vLLM#47019：8×V100 stock 15.6 → tuned 65.9 (C1) / 173.9 (C8)；1Cat-LLM：4×V100 TP4 NVFP4 116.99 → +MTP4 174.76 | ❌ 不选：同等 3B 激活 → 解码速度与现役同档，能力未见显著超越 Coder-Next，且无官方 GGUF |
| **incoai/Qwen3.8-27B-DFlash2-GGUF** | 社区（incoai） | 投机解码 draft 模型（DFlash2） | Q4_K_M / Q8_0 / BF16（3 个文件） | — | ✅（仅作 draft） | — | 1Cat-LLM 推荐 DFlash2 draft；llama.cpp PR #28912 在 V100 上实测有效 | ⚠️ **仅在选 Qwen3.8-27B 时才有意义**，而 Qwen3.8-27B 我们不选 → 本轮不用 |
| **GPT-OSS-120B (MXFP4)** | OpenAI | MoE 117B / 5.1B 激活 | MXFP4 约 60+ GB | 131,072 | ✅（但格式问题） | — | — | ❌ **维持前期结论不变**：MXFP4 是 Blackwell(sm_100/sm_120) 的格式，V100 无硬件 FP4；且 117B 权重本身就超 64 GB 显存 |
| **Qwen3-Coder-480B-A35B** | Qwen | MoE 480B / 35B 激活 | — | 262,144 | ❌ 装不下 | SWE-V 70.2（Qwen3-Coder-Next 技术报告里的对照表，转引自该报告） | — | ❌ 装不下（权重 ~250+ GB） |

---

## 4. 重点候选展开

### 4.1 Qwen3-Coder-Next（80B-A3B）—— 本轮唯一"既装得下又更强"的候选

**架构与规格（官方模型卡 + config.json，一手）**
- `Qwen/Qwen3-Coder-Next` config.json：`architectures: ["Qwen3NextForCausalLM"]`，`model_type: "qwen3_next"`，48 层，hidden 2048，num_experts **512**，num_experts_per_tok **10**，moe_intermediate_size 512，shared_expert_intermediate_size 512，full_attention_interval 4（= 12 个全注意力层 / 36 个线性注意力层），head_dim 256，num_key_value_heads 2，max_position_embeddings 262144，vocab 151936
- 模型卡："80B in total and 3B activated"、"79B 非嵌入参数"、"Context Length: 262,144 natively"
- ⚠️ **"This model supports only non-thinking mode and does not generate `` blocks in its output."** → 对我们**极其重要**：我们前期已发现"模型不努力（浅尝辄止、零补丁）"是真正的成本瓶颈，而非 token 绝对量；非思考模式在**架构上**就不可能产生大段思考 token，token 成本天然低。
- 推荐采样：`temperature=1.0, top_p=0.95, top_k=40`（官方 Best Practices）

**能力（一手：官方技术报告 PDF `QwenLM/Qwen3-Coder/qwen3_coder_next_tech_report.pdf`）**
- SWE-bench Verified：**70.6 / 71.1 / 71.3**（三个 scaffold），对比 DeepSeek-V3.2(671A37) 70.2/67.2/72.6、GLM-4.7 74.2/70.4/70.6、MiniMax-M2.1 74.8/70.4/71.0、Kimi-K2.5 73.2/70.8（max agent turns = 300）
- SWE-bench Pro 44.3 / 37.9；SWE-bench Multilingual 62.8 / 56.2 / 64.3
- Terminal-Bench 2.0：34.2 / 36.2 / 30.9 / 25.8（四个 harness）
- 报告里还写了一个对我们有意义的观察：RL 训练中 agent 平均轮数从 50 涨到 130 —— **长程 agentic 能力是训出来的**。

**在 2×V100S-32GB 上能不能跑（我们的算账）**
- 权重：Q4_K_M **48.40 GB**（官方 GGUF）/ 52 GB（ollama 库版）。总显存 64 GB → 余 ~12 GB
- KV cache：12 个全注意力层，2 KV head × head_dim 256，f16 → 2×2×256×2 B = 2 KiB /层/token → 12 层 = **24 KiB/token**；Gated DeltaNet 循环状态 = 36 层 × (32 v-head × 128 × 128 × 2 B) = 36 MiB / 序列
  - num_ctx 32,768 → KV ≈ 0.79 GB；65,536 → 1.57 GB；262,144 → 6.3 GB
- 结论：**num_ctx 32K 稳；64K 可试；262K 会很紧（48.4+6.3+计算缓冲 > 64 GB，很可能 OOM）**。官方自己也建议 OOM 时降到 32,768。
- **显存不是淘汰理由**（运营者已明确磁盘可扩、真正约束是 64 GB 显存）；Coder-Next 是少数"刚好装下"的选项。

**速度会不会更快？—— 不会（这是本轮最重要的推翻）**
- 带宽账：Q4_K_M ≈ 0.605 B/参数（48.40 GB / 80B）。每 token 读 3B 激活权重 ≈ **1.82 GB**。V100S-32GB HBM2 带宽 ~900 GB/s → 理论上限 **~495 tok/s**。
- 现役 qwen3-coder-30b：18.56 GB / 30.5B = 0.609 B/参数，3B 激活 → 1.83 GB/token → 理论上限 **~492 tok/s**，实测 135.7 tok/s（**27% 效率**）。
- ⇒ **Coder-Next 与现役的每 token 权重读取量几乎相同（1.82 vs 1.83 GB），速度必然同档，不会更快。** 多出来的 50B 是不激活的专家，只增加装载时间、显存和路由开销（512 专家 top-10）。
- 唯一可能变快/变慢的边际项：① 48 层 vs 48 层（相同）；② 12 个全注意力层（vs 现役 30B-A3B 的 48 个全注意力层）→ **Coder-Next 的注意力层数更少，prefill 更快**；③ `gated-delta-net-mma.cu` 在 Volta 上不可用 → 36 层线性注意力落回串行 scan，**这部分会比 Qwen3-Next 系在 Ampere 上慢**。
- **综合判断：单题墙钟时间与现役"同档 ±20%"，不是"更快"。收益来自解题率。**

### 4.2 Qwen3.8-27B（qwen35 混合稠密）—— 明确不选，但它是"稠密 vs MoE"这条假设的最好的对照组

- **架构**：稠密 27B，64 层，16×(3×(GatedDeltaNet→FFN)→1×(GatedAttention→FFN))，FFN 17,408，hidden 5,120，MTP 多步训练，原生 VLM（image-text-to-text）
- **带宽账**：每 token 读 27B × 0.6 B ≈ **16.2 GB** → 900 GB/s 理论上限 **~55 tok/s**；llama.cpp#27366 实测 **33.25 tok/s**（60% 效率，与模型自洽）→ **相对现役 135.7 tok/s 是 1/4.1**
- 加 DFlash2 投机解码后 **69.36 tok/s**（PR #28912，V100 实测）→ 仍是现役的 1/2
- ⇒ **用户假设中"稠密 27B 在 V100 上解码慢 3-4 倍"被两个独立数据点证实**（33.25 → 1/4.1；69.36 → 1/2.0）
- **架构风险**：`qwen35` 是 2026-08 才进 llama.cpp 的新混合线性注意力架构；#30906（2026-10-21 当天）还在报 CPU 后端输出损坏；#29172 报 CUDA 深 KV 位置崩塌；#29092 报 GDN 状态跨请求串台（ROCm，但状态管理是共性逻辑）；且我们**没有独立 llama-server 二进制**，只能靠 ollama 的内嵌 runner，排查手段更弱
- ⇒ 明确不选

### 4.3 核心假设的验证结论

> 假设原文：「在 2×V100S-32GB 上，『总参很大但激活参数很少的 MoE』（例如 80B-A3B 这类）可能同时做到比现役更强、比稠密 27B 更快，因为解码受显存带宽约束、每 token 只需读取被激活的那部分权重；反之稠密 27B 在 V100 上解码会慢 3-4 倍。」

| 分解 | 结论 | 证据 |
|---|---|---|
| 机制："解码受显存带宽约束，每 token 只读激活权重" | ✅ **成立** | 带宽账自洽：3B 激活 → 1.8 GB/token → 理论 ~490 tok/s，实测 135.7（27% 效率）；27B 稠密 → 16.2 GB/token → 理论 ~55 tok/s，实测 33.25（60% 效率） |
| "稠密 27B 比现役慢 3-4 倍" | ✅ **成立** | llama.cpp#27366（33.25 tok/s，1/4.1）；PR #28912（+DFlash2 后 69.36，1/2.0） |
| "80B-A3B 比现役 30B-A3B 更快" | ❌ **不成立** | 两者激活参数都是 ~3B、每 token 读取量 1.82 vs 1.83 GB → 速度必然同档。**MoE 的"大总参"在解码时是零成本，所以"更强"和"更快"是两个独立轴** |
| "80B-A3B 比现役更强" | ✅ **成立（官方自报）** | SWE-bench Verified 70.6-71.3（Coder-Next）vs 现役 30B-A3B 官方卡未给文本分（前期调研口径 61.6%，转引）；Terminal-Bench 2.0 34.2-36.2 vs Qwen3.8-27B 的 TB2.1 73.0 —— **不同版本号（2.0 vs 2.1）不可直接比** |
| "80B-A3B 的 Q4 权重约 45 GB，双卡 64 GB 能否放下" | ✅ **能放下** | 实测官方 GGUF 字节数：Q4_K_M = **48.40 GB**（不是 45），Q5_K_M 56.71，**Q6_K 65.53 GB 放不下**，Q8_0 84.81 GB 放不下。→ 只能上 Q4_K_M（或 ollama 库版 52 GB 的 q4_K_M） |
| "放不下时 `--n-cpu-moe` CPU 专家卸载在 V100 上可行吗、代价多大" | ⚠️ **可行但极不划算** | 见 §2.4：活跃专家走 PCIe（~16-32 GB/s）而非 HBM2（~900 GB/s），每 token 延迟数量级恶化；`--moe-cache-mib` 命中率低。**正确解法是降 num_ctx 到 32K（官方建议），而不是 CPU 卸载** |

---

## 5. 直接证据 vs 推断（分栏）

### 5.1 直接证据（本轮亲自读到/跑到的）

| # | 结论 | 类型 | 出处 |
|---|---|---|---|
| D1 | anolis 2×V100S-32GB，驱动 570.133.20，nvidia-smi 报 CUDA 12.8 | **本机实测** | `ssh anolis-gpu-01 'nvidia-smi'` |
| D2 | GPU 间 PHB 拓扑、**无 NVLink**；`topo -p2p r/w` 两向 OK | **本机实测** | `nvidia-smi topo -m` / `-p2p r` / `-p2p w` |
| D3 | anolis CUDA 12.6 工具链**缺 libcudart/libcudadevrt**，CUDA 程序链接失败 | **本机实测** | `nvcc -arch=sm_70 -o p p.cu` → `ld: cannot find -lcudadevrt` |
| D4 | ollama 0.40.6 / `qwen3-coder-30b` 18.56 GB / `qwen3moe` / 30.5B / ctx 262144 / runner llamacpp | **本机实测** | `curl 127.0.0.1:11434/api/version`、`/api/tags` |
| D5 | llama.cpp `70-virtual` 仅在 CUDA<13 时进默认 arch 列表 | **官方源码** | `ggml/src/ggml-cuda/CMakeLists.txt:40-46`（上游 b11777, 2026-10-21） |
| D6 | CUDA 13.0 "Removed support for Maxwell, Pascal, and Volta GPUs"；CUDA 12.8 §1.5.1 Volta feature-complete | **官方文档** | NVIDIA CUDA Toolkit Release Notes（docs.nvidia.com） |
| D7 | llama.cpp 有专用 Volta FA 路径 + `VOLTA_MMA_AVAILABLE`；V100 上 `turing_mma_available=false` | **官方源码** | `common.cuh:284-291,361-370`；`fattn.cu:223,672` |
| D8 | V100 上 MMQ 仅 ne11<64 启用（长 prefill 走 cuBLAS） | **官方源码** | `mmq.cu:355-424`；`mmq.cuh:8` |
| D9 | GDN 的 MMA 路径要求 AMPERE；SSM SSD 快速路径要求 cc≥TURING | **官方源码** | `gated-delta-net-mma.cu:59,363,403`；`ssm-scan.cu:846-857` |
| D10 | `-sm row` 在 CUDA 不可用（只有 SYCL 实现 split buffer）；`-sm tensor` 在多卡 Volta 上 assert/挂死+显存不释放；`-sm layer` 正常 | **第三方复现（上游 issue）** | llama.cpp#27366（2026-08-19） |
| D11 | V100 上 Qwen3.8-27B Q4_K_M：pp4096 730.71 / **tg128 33.25 tok/s** | **第三方复现** | llama.cpp#27366 附 llama-bench 输出 |
| D12 | V100 上 Qwen3.8-27B + DFlash2：`predicted_per_second` 54.52 → **69.36**（+27%） | **第三方复现** | llama.cpp PR #28912（2026-09-21 merged） |
| D13 | 5 个 Volta 修复（#28887/#28888/#28912/#29232/#29803）全部落在 2026-09-14~10-01，ollama 0.40.6 固定 b11738 已包含 | **官方源码 + 官方仓库** | PR 日期 + ollama `LLAMA_CPP_VERSION` |
| D14 | ollama 支持 qwen35/qwen35moe 架构并自动启用 MTP draft | **官方源码** | `llm/llama_server.go:877,912,936-945`；`llama_server_test.go:2665-2745` |
| D15 | SGLang 对 sm_70 直接 `RuntimeError("SGLang only supports sm75 and above.")` | **官方源码** | `sglang/python/sglang/srt/model_executor/model_runner_components/load_model_utils.py:78-90` |
| D16 | TensorRT-LLM 0.15.0 起移除 Volta；0.14.0 deprecated；支持列表无 Volta | **官方文档** | `docs/source/release-notes.md:759,823`；`docs/source/supported-hardware.md:4-7` |
| D17 | TGI 官方支持列表 = H100/A100/A10G/T4，**不含 V100** | **官方文档** | `docs/source/installation_nvidia.md:3` |
| D18 | vLLM 0.19.x 是 V100 最后实用线；stock fused-MoE 15.6→65.9 (C1) / 24.9→173.9 (C8) | **第三方复现（上游 issue）** | vllm#47019（2026-06-29，2026-07-01 closed） |
| D19 | 新版 vLLM 与 Qwen3.5 在 V100 上是 catch-22（issue 仍 open） | **上游 issue（未解决）** | vllm#43561（2026-05-25, open） |
| D20 | 1Cat-LLM v1.5.1 发布于 2026-10-03，4×V100-SXM2-32GB TP4：QUASAR-27B-NVFP4+DFlash2 4K 229.34 / 32K 201.18 / 128K 171.43 / 32K-C4 445.45 tok/s；要求 GLIBC≥2.38、GLIBCXX≥3.4.21、py3.12、Torch 2.10+CUDA 12.8、驱动≥570.124.06；wheel 未过 manylinux 门；GGUF 只在 main | **官方自报（厂商）** | github.com/1CatAI/1Cat-vLLM README + v1.5.1 release |
| D21 | Qwen3-Coder-Next 官方 GGUF 字节数：Q4_K_M 48.40 / Q5_K_M 56.71 / Q6_K 65.53 / Q8_0 84.81 GB；ollama 库版 q4_K_M 52 GB | **官方仓库 + ollama 库** | hf-mirror `?blobs=true`；ollama.com/library/qwen3-coder-next/tags |
| D22 | Qwen3-Coder-Next 规格：80B/3B 激活、48 层、512 专家取 10、hidden 2048、ctx 262144、**仅非思考模式** | **官方模型卡 + config.json** | HF `Qwen/Qwen3-Coder-Next` README / config.json |
| D23 | Qwen3-Coder-Next 官方分数：SWE-V 70.6/71.1/71.3；SWE-Pro 44.3/37.9；TB2.0 34.2/36.2/30.9/25.8 | **官方一手（技术报告 PDF）** | `QwenLM/Qwen3-Coder/main/qwen3_coder_next_tech_report.pdf`（pdftotext 抽取 Table 3/4/5） |
| D24 | Qwen3.8-27B 官方分数：TB2.1 73.0、SWE-Pro 61.7、NL2Repo 42.3、DeepSWE 42.2、QwenSWEBench 79.0、CoWorkBench 70.7；**SWE-bench Verified 官方卡未给** | **官方模型卡** | HF `Qwen/Qwen3.8-27B` README |
| D25 | Qwen3.8-27B GGUF 字节数：Q4_K_M 17.44 / Q5_K_M 20.92 / Q6_K 23.86 / Q8_0 29.12 GB | **官方仓库** | `bartowski/Qwen3.8-27B-GGUF?blobs=true` |
| D26 | `turboderp/exllamav3` 仓库不存在（404） | **实测** | `git ls-remote` → "Repository not found" |
| D27 | 5 个 qwen35/qwen35moe 架构的活跃 bug（#30906 今天、#29172、#27090、#29092、#27109） | **上游 issue** | llama.cpp issue 列表（标题+日期+URL 已抓取；#30906/#29172 正文经 HTML meta 抽取） |

### 5.2 推断（我们根据上面的证据做的外推，未被直接验证）

| # | 推断 | 依据 | 风险 |
|---|---|---|---|
| I1 | Coder-Next 在 2×V100S 上解码速度与现役同档（~100-140 tok/s），不更快 | 带宽账：1.82 vs 1.83 GB/token | 中。**未实测**（本轮不下载权重）。若它实际更慢（如 GDN 串行 scan 拖累），性价比会进一步下降 |
| I2 | Coder-Next Q4_K_M 在 num_ctx 32K 可稳跑，262K 会 OOM | 48.40 GB 权重 + KV 24 KiB/token + 计算缓冲 vs 64 GB | 中。ollama 库版 52 GB 更紧，建议 32K |
| I3 | `--n-cpu-moe` 在 V100 上每 token 延迟数量级恶化 | PCIe ~16-32 GB/s vs HBM2 ~900 GB/s | 中。未实测 |
| I4 | 1Cat-LLM 从 4 卡 TP4 降到我们 2 卡，模型级 tok/s 大致折半（Qwen3.8-27B-NVFP4 128K：61.8 → ~30 量级） | 只有算子级 TP2 数字（70.2 TFLOP/s），无 2 卡整模型数据 | 中高。也可能因 PCIe P2P（PHB）而非 NVLink 而更差 |
| I5 | 1Cat-LLM 用 NVFP4 权重是"存储格式"（V100 无 FP4 硬件，需软件反量化），不是硬件加速 | NVFP4/NVFP4 属 Blackwell；`noctrex/Qwen3-Coder-Next-MXFP4_MOE-GGUF`、`amd/Qwen3-Coder-Next-MXFP4` 命名亦同 | 中。未核对其 kernel 实现路径 |
| I6 | Torch 2.10 + CUDA 12.8 的官方 wheel 是否含 sm_70 SASS | CUDA 12.8 仍支持 sm_70（deprecated 未移除），PyTorch 一般保留 7.0；但 1Cat-LLM 自带 SM70 扩展 | 中。装机前必须先验 |
| I7 | 现役 30B-A3B 的 SWE-bench Verified 官方文本分约 61.6% | 前期调研口径（`设计/benchmark调研/实测/model-pricing.md`），本轮**未能在官方一手来源找到文本表**（模型卡只有图片） | 低（仅用于对照叙述，不作决策依据） |
| I8 | Coder-Next 的 12 个全注意力层（vs 现役 48 层）→ prefill 更快 | 架构差异 | 低。V100 上 FA 走 Volta 分支，与 Ampere 差距约 2×（#28037），收益会被部分抵消 |

### 5.3 未找到公开证据（本轮明确查不到，不做补齐）

- **Qwen3-Coder-Next 在 V100 上的任何第三方 tok/s 复现**（1Cat-LLM 的 V100 数字全是 Qwen3.6-35B-A3B / Qwen3.8-27B / Qwen3.8-Flash-Next，**没有 Coder-Next**）。
- **Qwen3-Coder-30B-A3B-Instruct 的官方 SWE-bench Verified 文本分**（模型卡只有图片）。
- **Qwen3.8-27B 的官方 SWE-bench Verified 分**（模型卡给了 SWE-Pro / QwenSWEBench / TB2.1，无 SWE-V）。
- **exllamav2 在 sm_70 上的支持声明与实测**（源码无 min-CC 声明，也无 V100 数据）。
- **exl3 / exllamav3 的当前形态**（`turboderp/exllamav3` 404）。
- **TensorRT-LLM 在 V100 上的任何实测**（且 0.15.0 起官方已移除支持）。
- **TGI 在 V100 上的实测**（官方支持列表不含 V100）。
- **KTransformers 在 V100 上跑 Qwen3-Coder-Next 的任何数据**。
- **LM Studio 在本机 headless 场景的可行性**（本机未装）。
- **2×V100 整模型级的 1Cat-LLM tok/s**（官方只给 4 卡 TP4）。
- **ollama 0.40.6 的内嵌 llama.cpp runner 是否暴露 `--split-mode` / `--spec-type` 等 CLI 开关**（ollama 0.40.x 走的是 `llama-server` 子进程 + 自己的参数映射；本轮**未**逐项核对其暴露面）。

---

## 6. 对我们的具体建议

### 6.1 结论：换模型（Qwen3-Coder-Next），**不换引擎**（继续 ollama/llama.cpp）

**为什么换模型**：在 64 GB 显存里，Qwen3-Coder-Next Q4_K_M（48.40 GB）是**唯一**同时满足"装得下"+"官方 SWE-bench Verified 70.6-71.3、Terminal-Bench 2.0 34.2-36.2"+ 非思考模式（token 成本低）的候选。现役 30B-A3B 官方无 SWE-V 文本分，且 30.5B 总参在能力上明显低于一代。

**为什么不换引擎**：
- vLLM upstream 在 V100 上已到 0.19 末期（#47019 明确"last broadly practical line"），要靠手动改 fused-MoE 配置才能从 15.6 拉到 65.9 tok/s；**即使拉到 65.9 也只有现役 ollama 135.7 的一半**。
- SGLang / TensorRT-LLM / TGI 三家对 sm_70 是**明确不支持**（不是"调参能救"）。
- 1Cat-LLM 是唯一有竞争力的替代，但其发布数字全部基于 **4 卡 TP4**；折算到我们的 2 卡 + PHB PCIe 拓扑（无 NVLink），**大概率打不赢现役 135.7 tok/s**，且要另起 Torch 2.10 + CUDA 12.8 栈。**建议列为"下一轮独立课题"，不阻塞本轮选型。**

### 6.2 落到 anolis 的具体施工单

**Step 0 — 先做环境冒烟（不下载权重，约 15 分钟）**
```bash
# 6.2.1 验证 ollama 的 runner 在 V100 上真走 CUDA（不是 CPU 回退）
ssh anolis-gpu-01 'nvidia-smi --query-compute-apps=pid,used_memory --format=csv; \
                    curl -s -X POST http://127.0.0.1:11434/api/generate -d "{\"model\":\"qwen3-coder-30b\",\"prompt\":\"2+2=?\",\"stream\":false,\"options\":{\"num_predict\":8}}" ' &
# 同时看 GPU 显存占用与 util 是否 > 0
ssh anolis-gpu-01 'nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv'
```
> ⚠️ 前期记录过"llama.cpp 在老卡上有 GPU 未生效的 issue（ggml-org/llama.cpp#17067）"。**任何换模型之前必须先复验 ollama 0.40.6 在 V100S 上 GPU 是真生效的**，否则后面所有 tok/s 都不成立。

**Step 1 — 装模型（走 ollama 官方库最省事）**
```bash
# 官方 Qwen GGUF（48.40 GB，4 shard）与 ollama 库版（52 GB）二选一：
ollama pull qwen3-coder-next:q4_K_M
# 落地路径：/data/models/  或  ~/.ollama/models/  —— 需确认落在 /data（当前 /data 剩 18G、docker 可回收 135G）
df -h /data / ; ollama list
```
> **磁盘**：52 GB + 现有 18.56 GB ≈ 71 GB。/data 剩 18 GB 不够 → 先回收 docker（可回收 135 GB）再拉，**不要**因为磁盘不足就放弃这个候选（运营者已明确可扩容）。

**Step 2 — 配置（这是本轮最需要盯的三处）**
```bash
# 2.1 上下文：必须压到 32K（官方建议，且 48.4GB 权重 + 262K KV 必然 OOM）
#     af-bench 现有实测画像远低于 300K（前期校准：低 1-2 个数量级），32K 足够
# 2.2 并发：现役是 OLLAMA_NUM_PARALLEL=2（并发 2 时 109.7 tok/s/请求）
#     Coder-Next 权重占 48.4/64 GB，KV 余量小 → 先试 OLLAMA_NUM_PARALLEL=1，
#     实测 1 并发的 135 tok/s 基线后再决定是否开 2
# 2.3 显存：OLLAMA_KEEP_ALIVE=30m 以上，避免每题重载（现役加载 10.5s）
cat ~/.config/ollama/env
#   OLLAMA_NUM_PARALLEL=1
#   OLLAMA_KEEP_ALIVE=30m
#   OLLAMA_FLASH_ATTENTION=1
#   （⚠️ 不要设 OLLAMA_KV_CACHE_TYPE=q4_0 —— #27109 实测 4-bit KV 让 qwen35 系 prefill 塌到 ~34 t/s）
```
> ⚠️ **不要用 `--split-mode tensor`**（ollama 0.40.x 默认 layer 切分，保持默认）。#27366 已实证多卡 Volta 上 `-sm tensor` 会挂死 + 双卡各泄漏 8.3 GB。

**Step 3 — 冒烟（三关，缺一不进 bench）**
1. **正确性关**：同一道简单题（如写一个二分查找 + 测试）输出必须语义正确、不能有重复循环。qwen35 系在别的后端出现过"garbage/repetition loops"（#30906），Coder-Next 是 `qwen3next` 架构，同样要验。
2. **多轮不崩关**：连打 10 轮 tool calling（模拟我们一题 10 轮），看是否中途 500 / 静默退出。
3. **速度关**：单请求 decode 要 **≥ 100 tok/s**。若掉到 50-60，说明 GDN 串行 scan 拖累超出预期 → 直接回退现役 30B-A3B，**不要**在 Coder-Next 上继续调优（成本不划算）。

**Step 4 — 用 af-bench 跑同一批题，与现役同题同判**
- 对齐口径：同题、同 harness、同判分脚本（`af-bench --host anolis` 那条线）
- 必记指标：**解题率**（主）、**单题墙钟**（次）、**输出 token 数/题**（次，因为非思考模式应该显著低于同代）
- 我们的前期结论要复验："真正的成本瓶颈是模型不努力（浅尝辄止、零补丁），完成度纪律先于绝对能力" → **Coder-Next 的非思考模式是加分项还是减分项，取决于它是否更愿意把补丁写完**。这必须由 af-bench 实测，不能由榜单推断。

### 6.3 如果 Coder-Next 实测不达标，回退与备选

| 情形 | 动作 |
|---|---|
| 装不下 / 速度 < 100 tok/s / 多轮崩 | 保持现役 qwen3-coder-30b；把预算投到 af-bench 的完成度纪律（前期结论）而不是换模型 |
| 想要更高能力但不想吃 48 GB | 评估 **1Cat-LLM**（本机环境已验证对得上：glibc 2.38 ✓、py3.12 ✓、驱动 570.133.20 ✓、CUDA 12.8 ✓；需装 uv + Torch 2.10 cu128）。**前提**：先验证 (a) Torch 2.10 cu128 wheel 含 sm_70 SASS，(b) 2 卡 TP2 的整模型 tok/s，(c) 1Cat 的 GGUF 支持（只在 main，不在 v1.5.1 wheel） |
| 想要"零风险 + 更高能力" | 放弃本地，转 API 主力（GLM-5.3-Flash / MiniMax M3.1 Flash / Kimi K3）—— 本地臂的定位本就是"不烧额度的量产臂"，不是打主链路 |

### 6.4 明确不做的事

- ❌ **不升 CUDA 到 13**（Volta 官方已移除；且我们驱动 570.133.20 最高到 CUDA 12.8）
- ❌ **不上 vLLM / SGLang / TensorRT-LLM / TGI**（V100 上分别是"末代可用需手调"、"直接拒绝"、"已移除"、"不在支持列表"）
- ❌ **不用 `--n-cpu-moe` 换显存**（每 token 延迟数量级恶化，违反"每 token 成本"核心指标）
- ❌ **不用 `--split-mode tensor`**（#27366 实证挂死 + 显存泄漏）
- ❌ **不选 Qwen3.8-27B**（稠密 → V100 上只有现役 1/4~1/2 速度；`qwen35` 架构 bug 活跃）
- ❌ **不选 GPT-OSS-120B MXFP4**（维持前期结论：V100 无 FP4 硬件；117B 权重也超 64 GB）

---

## 附录 A · 关键 URL 索引

| 主题 | 链接 |
|---|---|
| llama.cpp CUDA arch 列表（sm_70 仅 CUDA<13） | https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-cuda/CMakeLists.txt |
| llama.cpp MMA/Volta 宏 | https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-cuda/common.cuh |
| llama.cpp FA Volta 分支 | https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-cuda/fattn.cu |
| llama.cpp MMQ 决策 | https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-cuda/mmq.cu |
| llama.cpp GDN/SSM 架构门槛 | .../ggml/src/ggml-cuda/gated-delta-net-mma.cu, .../ssm-scan.cu |
| llama.cpp 投机解码类型 | .../common/speculative.cpp |
| llama.cpp CLI（-ncmoe / --moe-cache-mib / --spec-*） | .../common/arg.cpp, .../tools/server/README.md |
| **`-sm tensor` 多卡 Volta 挂死** | https://github.com/ggml-org/llama.cpp/issues/27366 |
| **V100 MMQ/MMVQ crossover（+27% DFlash2）** | https://github.com/ggml-org/llama.cpp/pull/28912 |
| **Volta FA 性能分析（MMA 架构代差）** | https://github.com/ggml-org/llama.cpp/issues/28037 |
| qwen35 输出损坏（2026-10-21） | https://github.com/ggml-org/llama.cpp/issues/30906 |
| qwen35 深 KV 位置 CUDA 崩塌 | https://github.com/ggml-org/llama.cpp/issues/29172 |
| GDN 状态跨请求串台 | https://github.com/ggml-org/llama.cpp/issues/29092 |
| **vLLM 0.19 是 V100 末代 + fused-MoE 调优数据** | https://github.com/vllm-project/vllm/issues/47019 |
| vLLM × V100 × Qwen3.5 catch-22（未解决） | https://github.com/vllm-project/vllm/issues/43561 |
| **SGLang 拒绝 sm_70** | .../sglang/python/sglang/srt/model_executor/model_runner_components/load_model_utils.py |
| **TensorRT-LLM 移除 Volta** | https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/release-notes.md |
| TGI 支持硬件列表 | https://github.com/huggingface/text-generation-inference/blob/main/docs/source/installation_nvidia.md |
| **1Cat-LLM（V100 优先 vLLM 分叉）** | https://github.com/1CatAI/1Cat-vLLM |
| NVIDIA CUDA 13 移除 Volta | https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html |
| Qwen3-Coder-Next 技术报告 PDF | https://github.com/QwenLM/Qwen3-Coder/blob/main/qwen3_coder_next_tech_report.pdf |
| Qwen3-Coder-Next 官方 GGUF | https://huggingface.co/Qwen/Qwen3-Coder-Next-GGUF |
| Qwen3-Coder-Next ollama 库 | https://ollama.com/library/qwen3-coder-next/tags |
| Qwen3.8-27B 官方卡 | https://huggingface.co/Qwen/Qwen3.8-27B |
| DFlash2 draft GGUF | https://huggingface.co/incoai/Qwen3.8-27B-DFlash2-GGUF |

## 附录 B · 本轮做过的检查（命令与结果）

| 检查 | 命令 | 结果 |
|---|---|---|
| anolis GPU/驱动/拓扑 | `ssh anolis-gpu-01 'nvidia-smi; nvidia-smi topo -m; nvidia-smi topo -p2p r'` | 2×V100S-32GB / 570.133.20 / CUDA 12.8 / PHB / P2P OK |
| anolis 工具链 | `ls /usr/local/cuda-12.6/lib64; nvcc --version` | 仅 libnvptxcompiler_static.a；nvcc 12.6.68 |
| CUDA 程序链接 | `nvcc -arch=sm_70 -o p p.cu` | ❌ `cannot find -lcudadevrt / -lcudart_static` |
| anolis 运行时 | `python3 --version; python3.12 -m pip --version; ldd --version; gcc --version; nproc; free -g` | 3.11 / 3.12+pip26.2.1 / glibc 2.38 / gcc 12.3.0 / 16 / 125 GB |
| ollama 状态 | `curl 127.0.0.1:11434/api/version; /api/tags; /api/ps` | 0.40.6；qwen3-coder-30b 18.56 GB；无运行中模型 |
| llama.cpp 上游版本 | `api.github.com/repos/ggml-org/llama.cpp/releases` + `commits` | b11777 (2026-10-21)，commit 339f324 |
| ollama 固定 llama.cpp | `cat LLAMA_CPP_VERSION` (ollama main) | **b11738** |
| ollama 架构支持 | `grep qwen35/qwen3next llm/llama_server.go` | qwen35 / qwen35moe / qwen3next 均支持，MTP 自动识别 |
| SGLang sm_70 门槛 | `grep sm75 python/sglang/srt/model_executor/.../load_model_utils.py` | `RuntimeError("SGLang only supports sm75 and above.")` |
| TRT-LLM Volta 状态 | `grep -i volta docs/source/release-notes.md docs/source/supported-hardware.md` | 0.15.0 移除；列表无 Volta |
| TGI 支持硬件 | `docs/source/installation_nvidia.md` | H100/A100/A10G/T4 |
| exl3 仓库存在性 | `git ls-remote https://github.com/turboderp/exllamav3.git` | Repository not found |
| GGUF 体积 | hf-mirror `?blobs=true` | Coder-Next Q4_K_M 48.40 GB；Qwen3.8-27B Q4_K_M 17.44 GB |
| 官方分数 | 技术报告 PDF `pdftotext -layout` | SWE-V 70.6/71.1/71.3 等 |
