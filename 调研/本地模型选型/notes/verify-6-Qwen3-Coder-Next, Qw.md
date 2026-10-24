# 复核·第6名：Qwen3-Coder-Next（Qwen3.6-35B-A3B / Qwen3.6-27B 同批）

- 复核对象：**Qwen3-Coder-Next**（复核对象表里第 1 个），旁带核对 Qwen3.6-35B-A3B / Qwen3.6-27B 的相关断言
- 复核人：独立复核子代理（不修改原结论，只核查）
- 复核日期：2026-10-21
- 被复核原档案：`调研/本地模型选型/notes/v100-speed-data.md`（416 行）
- 复核环境（我自己实际用到的）：
  - 本机 = **pandev-comp 编排面**（RTX 3070 Laptop 8GB，driver 595.99.02，ollama 0.35.1）——**不是** anolis，V100 实测全部通过 `ssh anolis` 完成
  - anolis-gpu-01：2× Tesla V100S-PCIE-32GB，driver 570.133.20，ollama 0.40.6（`/data/models/bin/ollama` 与 `~/.local/bin/ollama` 同版本），现役 `qwen3-coder-30b`（Qwen3-Coder-30B-A3B-Instruct-Q4_K_M，18.5GB）已在盘上
- 网络限制（影响证据可得性，如实记录）：
  - 本机 `huggingface.co` **DNS 被污染**（解析到 Facebook 段 IP，curl/WebFetch 均 connect timeout）；`hf-mirror.com` 本机不通、**anolis 通**；`github.com`/`api.github.com` 本机通但**未认证 API 很快触发限流**（多次 403 rate limit），改从 anolis 出口取；`reddit.com` 本机与 anolis **均超时**；DuckDuckGo/多数 searx 实例超时；**Bing 可连但对我的查询串返回同一批泛化结果（实测无效）**
  - 因此「没有第三方 V100 实测」这一结论的强度受限于可及范围，但我在**能被检索到的主要来源**（HF 全库讨论/文件、GitHub、ollama registry、原始 notes 引用的 5 个第三方源）都查了，均无 Coder-Next 的 V100 tok/s

---

## 0. 复核结论速览（先给结论，再给证据）

| 原结论主张 | 复核判定 | 一句话理由 |
|---|---|---|
| 模型真实存在、80B/3B 激活、48 层混合、512 专家、262144 ctx、Apache-2.0 | ✅ **确认** | 官方仓库、config.json、README 逐项对上（见 §1） |
| 官方自报 SWE-V 70.6 / Pro 44.3 / TB2.0 36.2 / Multilingual 62.8 / Aider 66.2 | ✅ **确认（我独立读图）** | 我自己下载官方 `benchmarks.png` + `swebench_pro.png` 读图复核（见 §4） |
| 「非思考模式，不膨胀 token」 | ✅ **确认** | 官方 README 第 46 行原文："supports only non-thinking mode" |
| Q4_K_M 48.53GB=45.2GiB（unsloth）、52GB（ollama） | ⚠️ **部分修正** | unsloth 单文件 48.53GB/45.20GiB ✅；但 **ollama tag 的 blob 实测 51.74GB=48.19GiB**，每卡权重是 **24.1GiB**（原结论按 22.6GiB 算，偏乐观 1.5GiB/卡） |
| 双卡 64GB 装得下 | ✅ **成立（但余量比原文估计小）** | 权重 24.1GiB/卡 + KV(32K) 0.75GiB + 状态/缓冲 ≈ 26.5–27.5GiB/卡 < 32GiB；**ctx 256K 会溢出**（见 §3.4） |
| V100 上无任何 tok/s 实测；「90–130 tok/s」是推断 | ✅ **确认（我未能补上这条证据）** | 全网可及范围内确实没有 V100/3090/P40/4060Ti 的 Coder-Next 吞吐实测；唯一第三方数字是 RTX 5080+CPU 卸载 40–45 tok/s |
| agentic 分数有第三方独立复现 | ❌ **推翻（不成立）** | SWE-bench 官方榜单 swebench.com **没有任何 Coder-Next 条目**（grep 计数 0）；Terminal-Bench 2.0 榜单页也没有。**70.6 纯属作者自报** |
| 上游 #27366「正好命中我们的架构家族」+「以 stale 关闭」 | ❌ **两处都要改** | 该 issue 的模型是 `bartowski/Qwen3.8-27B-GGUF`（arch `qwen35`），**不是 qwen3next**；关闭原因是 **not_planned**（2026-10-03），不是 stale（见 §5.3） |
| 「Coder-Next 有输出损坏 CUDA bug 的风险」 | ⚠️ **风险对象搞错了，但结论方向对** | 真正踩坑的是 llama.cpp **#19305「Qwen3-Coder-Next Poor Outputs」**（2026-02-03，修于 #19324 key_gdiff）。**ollama 0.40.6 固定 llama.cpp b11669（2026-10-15, v0.7.0）已包含修复** → 我们这条栈上该风险已消除（见 §3.3） |
| 附带结论「现役 18.5GB 模型只落 1 张卡，第 2 张卡全程闲置」 | ❌ **推翻（事实错误）** | ollama 日志 + 我现场 nvidia-smi：双卡都加载了权重、都满负荷。**正确表述是：第 2 张卡在干活，但 layer 切分是串行的，买到容量买不到速度**（见 §6.1，含我的一手实测） |

**适配分（我的独立打分）：6.5 / 10**（原结论 7 / 10）
- 加分：模型真身与官方分数全部核实为真；非思考模式对「量产臂」是硬优势；权重确实塞得进 2×V100S。
- 扣分：**质量侧零第三方复现**（70.6 是自报、且用的脚手架与我们 af-bench 不同）；**速度侧零 V100 实测**，我按同族专家数外推得 85–105 tok/s（低于现役 135.7，墙钟要涨 30%–60%）；**上游两个未修的 Volta 坑**（§3.5）正对我们这种 layer-split + 长上下文 + prefix 复用的 agent 用法。

---

## 1. 模型真身核对（这一节全部为「我自己查到的原始出处」）

### 1.1 官方仓库与元数据
`curl https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next`（hf-mirror 是本机 DNS 被污染时的可用镜像；执行于 anolis）：

```
id Qwen/Qwen3-Coder-Next | downloads 522825 | likes 1703 | gated False | pipeline text-generation
tags: transformers, safetensors, qwen3_next, text-generation, conversational, license:apache-2.0, eval-results, ...
lastModified 2026-02-03T16:16:38Z | createdAt 2026-01-30T15:08:18Z
cardData license: apache-2.0
```

→ 模型**真实存在**，**Apache-2.0**（可商用），社区热度在线（52 万次下载）。

### 1.2 config.json（逐字段核对架构）
`curl https://hf-mirror.com/Qwen/Qwen3-Coder-Next/raw/main/config.json`：

```
architectures: Qwen3NextForCausalLM      model_type: qwen3_next
num_hidden_layers: 48        full_attention_interval: 4     → 48/4 = 12 层全注意力，36 层线性注意力
hidden_size: 2048            head_dim: 256     num_attention_heads: 16    num_key_value_heads: 2
num_experts: 512             num_experts_per_tok: 10     shared_expert_intermediate_size: 512
moe_intermediate_size: 512   linear_num_key_heads: 16  linear_num_value_heads: 32
linear_key_head_dim: 128     linear_value_head_dim: 128    linear_conv_kernel_dim: 4
max_position_embeddings: 262144            rope_theta: 5000000   torch_dtype: bfloat16
```

→ 与原结论「48 层混合（GatedDeltaNet + Gated Attention）、512 专家 10 激活 + 1 共享、262144 原生 ctx」**逐项一致**。

**KV 体积复核（我自己算的）**：只有 12 层全注意力，2 个 KV 头，head_dim 256，f16 →
每 token 每层 = K+V = 2×2×256×2 B = 2048 B；12 层 = **24,576 B/token = 24 KiB/token**。
→ 原结论的 24KiB/token **正确**（我独立用 config 数字复算一致）。

### 1.3 权重体积（我逐文件读的 HF tree size，不是估算）
- `unsloth/Qwen3-Coder-Next-GGUF`（downloads 146,567）单文件 `Qwen3-Coder-Next-Q4_K_M.gguf` = **48,528,320,544 B = 48.53GB = 45.20GiB** ✅ 与原结论一致
- 同仓其它档位（我全部列出，可按显存预算选）：UD-IQ4_XS 38.43GB / IQ4_XS 42.68GB / UD-Q4_K_S 45.53GB / **Q4_0 45.33GB** / **UD-IQ1_M 21.70GB** / UD-IQ2_M 24.96GB / Q3_K_M 38.32GB / MXFP4_MOE 48.03GB
- `Qwen/Qwen3-Coder-Next-GGUF`（官方，downloads 41,833）：Q4_K_M 分 4 shard，合计 **48.41GB**（15.52+14.87+14.50+3.51）
- **ollama 官方 tag**（`https://registry.ollama.ai/v2/library/qwen3-coder-next/manifests/q4_K_M`）：
  ```
  model blob 51,741,599,936 B = 51.74GB = 48.19GiB   (digest sha256:30e51a7c…)
  q8_0 blob  84,812,664,640 B = 84.81GB = 78.99GiB   ← 64GB 显存放不下，直接排除
  tags: latest, q4_K_M, q8_0
  ```
  ⚠️ ollama 的 blob 与上面两个公开 Q4_K_M 的 sha256 **都不匹配**（unsloth Q4_K_M = 9e6032d2…，Qwen 官方是分片，unsloth MXFP4 = bf0d98f2…），即 ollama 用的是**自己的再量化版本**，比 unsloth 大 3.2GB。**原结论按「52GB→48.4GiB→每卡 24.2GiB」估算，方向对；我按实测给出每卡 24.1GiB。**

### 1.4 GGUF 可得性与「是不是唯一可行路」
- 官方 README 自己写：**"For local use, applications such as Ollama, LMStudio, MLX-LM, llama.cpp, and KTransformers have also supported"**，并给 SGLang `>=v0.5.8`、vLLM 的 tool parser 脚本 → 引擎面是齐的。
- 原始 FP8 权重也存在（`Qwen/Qwen3-Coder-Next-FP8`，downloads 1,034,239），**但 V100 上是死路**（见 §3.2）。

---

## 2. 引擎与版本：ollama 0.40.6 到底带的是哪个 llama.cpp

这一步是原结论完全没查、但**直接决定「会不会输出损坏」**的关键。

1. ollama v0.40.6 发布于 **2026-10-16**（`api.github.com/repos/ollama/ollama/releases/tags/v0.40.6` → `published_at 2026-10-16T22:00:46Z`）。
2. ollama 用 `LLAMA_CPP_VERSION` 文件固定 llama.cpp 源码：
   `curl https://raw.githubusercontent.com/ollama/ollama/v0.40.6/LLAMA_CPP_VERSION` → **`b11669`**
3. `api.github.com/repos/ggml-org/llama.cpp/commits/b11669` → **commit date 2026-10-15T13:48:22Z，msg "llama.cpp : bump version to 0.7.0 (#30603)"**
4. anolis 上 ollama runner 的动态库确实带 qwen3next 实现：
   ```
   $ strings /data/models/lib/ollama/libllama.so.0.7.0 | grep qwen3next
   _ZN21llama_model_qwen3next17load_arch_hparamsE... / load_arch_tensors / graph / graph_mtp
   qwen3next.attention.head_count_kv
   ```
   → **qwen3next 架构在 ollama 0.40.6 里已完整实现（含 MTP 草稿路径 `graph_mtp`）**，不是「需要 patch 的新架构」。

结论：**我们这套栈（ollama 0.40.6 / llama.cpp b11669 / 2026-10-15）对 Qwen3-Coder-Next 是现成可用的**，不需要自己编 llama.cpp。

---

## 3. V100（sm_70）能不能跑：逐条核查

### 3.1 结论
**能跑，但只有 GGUF 一条路，且必须用 ollama 0.40.6（或 ≥ 2026-02-04 的 llama.cpp）。**

### 3.2 格式死路（V100 硬件事实 + 上游状态）
| 格式 | V100(sm_70) | 结论 |
|---|---|---|
| FP8 | 无 FP8 张量核（Ada/Hopper 起才有） | **死路**：vLLM V1 要求 CC≥8.0/7.5，V100 已被移除；SGLang 快路径要 sm_80+。llama.cpp 虽能反量化 FP8，但 80GB FP8 权重（HF FP8 仓）本身就放不进 64GB |
| NVFP4 / MXFP4 原生算子 | Blackwell(sm_100/sm_120) 专属 | **原生死路**。`unsloth` 有 `Qwen3-Coder-Next-MXFP4_MOE.gguf`(48.03GB)，但 V100 上只能走 ggml 的 dequant→f16 路径（`dequantize_row_mxfp4` 存在于 ollama 的 ggml 里），**我没验证它在 sm_70 上是否真能跑通 → 必须冒烟** |
| BF16 | V100 无 BF16 张量核 | 权重 160GB 放不下；llama.cpp 会转 F16 跑，但不是本场景选项 |
| INT8 | 走 dp4a（CC≥6.1 可用） | 80B INT8 ≈ 80GB → 放不下；只有 4bit 级才可能 |
| **GGUF Q4_K_M** | llama.cpp sm_70 全面支持 | **唯一可行路**：48.19GiB 权重 + 24KiB/token KV，2×32GiB 装得下 |

### 3.3 架构支持是否 GA + 已知坑
- **GA：是**。llama.cpp 从 2025-10 起支持 `qwen3next`，2026 年 1–2 月集中修了一轮（#18792 统一 delta net 处理、#19321 chunking 修复、#19324 key_gdiff 修正、#19375 qwen3next graph 优化、#19365 inplace ops）。我们 pin 的 b11669 全部包含。
- **真正的「输出损坏」坑是 #19305，不是原结论盯着的 #27366**：
  ```
  TITLE: Eval bug: Qwen3-Coder-Next Poor Outputs
  state: closed completed | created 2026-02-03 | closed 2026-02-04
  硬件: DGX Spark (GB10, CC 12.1) | version 7925 (8bece2eb2)
  现象: llama-server 下 Qwen3-Coder-Next 明显输出劣化（误判语法错误、话说到一半自我打断），
        Q4_K_M / Q8_0 / Qwen 官方 GGUF 三份权重都一样；vLLM FP8 与 MLX int4 正常
  修复: PR #19324 "model: (qwen3next) correct vectorized key_gdiff calculation"（2026-02-04 合入）
  ```
  → **这条正好是「速度正常但输出损坏」的同类症状**，但针对的是 Coder-Next 本身。好消息：ollama 0.40.6 pin 的 b11669（2026-10-15）**远晚于该修复**，所以在我们这条栈上**风险已消除**。坏消息：**如果谁为了追新特性自己编了个 2026-02 之前的 llama.cpp，就会踩回去**。
- unsloth 社区还记录了工具调用侧的实操坑（HF discussion #14，2026-02-05）：模型在某些 harness（opencode）下会吐 `"filePath"/home/xxx` 这种坏 JSON；社区指向前端 tool parser / llama.cpp 的 grammar 采样路径。→ **对我们 af-bench 的直接影响：tool call 解析必须实测**（我们本地臂本来就用 ollama 的模板，路径与 opencode 不同）。
- 另一个 unsloth 侧的坑（HF discussion #5，2026-02-19 前后）：**部分 UD/IQ 量化档在 LM Studio 里识别不出架构/context**（被当成非 MoE，context 卡在 2048）。**ollama 侧用官方 q4_K_M 标签，规避了这条**（我们走 ollama 官方 tag，不走 LM Studio）。

### 3.4 显存账（我用实测尺寸 + config 复算，给出可执行的 ctx 建议）
```
权重        48.19 GiB  → layer 切分后 24.1 GiB/卡
KV          24 KiB/token（§1.2 复算）→ ctx 32K×1slot 0.75GiB(总) 0.375/卡
                                      → ctx 64K×2slot 3.0GiB(总)  1.5/卡
                                      → ctx 256K×1slot 6.0GiB(总)  3.0/卡
GatedDeltaNet 循环状态 ≈ 36 层 ×(32 V头×128×128×4B) ≈ 72MiB/slot（估算，未实测）
计算缓冲 + CUDA context ≈ 1.5–2.5 GiB/卡（估算）
─────────────────────────────────────────────
ctx 32K  1slot → ≈26.4–27.4 GiB/卡 ✅ 余量 ~5GiB
ctx 64K  2slot → ≈28.2–29.2 GiB/卡 ⚠️ 余量 ~3GiB
ctx 256K 1slot → ≈29.7–30.7 GiB/卡 ⚠️ 极紧
ctx 256K 2slot → ≈32.7GiB/卡      ❌ 超显存 → ollama 会把部分张量留在 CPU
```
**最后一行是必须避开的坑，而且我在现役模型上亲眼见过它发生**：现役 30B-A3B 在 `n_slots=2, n_ctx_slot=262144` 时，ollama 日志显示
```
load_tensors: offloaded 49/49 layers to GPU
load_tensors: CPU_Mapped model buffer size =  166.92 MiB / 157.50 / 216.00 / 108.00 ...（约 26 条，合计 ≈4.8GiB）
load_tensors: CUDA0 model buffer size = 7920.46 MiB ;  CUDA1 = 4140.97 MiB
```
即**同一份 18.5GB 权重有 ~4.8GiB 掉回 CPU mmap**（MoE 专家在 CPU 上算）→ 速度塌陷。
→ **给 Coder-Next 的落地约束：`OLLAMA_NUM_PARALLEL=1~2` + `num_ctx ≤ 65536`，256K 上下文在 V100 上不要开。**

### 3.5 两个原结论没提、但正打在我们脸上的 Volta 上游坑
| issue | 状态 | 内容 | 对我们是否命中 |
|---|---|---|---|
| **#29255** | **open**（2026-09-22 起） | 7× Volta(sm_70) `--split-mode layer` + 大 prefill + prefix 复用时，概率性 `CUDA error: invalid argument`（kernel launch 失败）**每日崩数次**；作者明说「跨架构复现（Qwen3.8-Flash-Next / DeepSeek-V4-Flash 各种量化），应该与模型无关」 | **高**：我们就是 2×V100S + layer 切分 + agent 长上下文反复复用前缀。ollama 的 spread 就是 layer 切分 |
| **#25835** | closed **not_planned**（2026-10-06） | V100×2 上**开启 CUDA Graphs 后显存逐轮泄漏直至 OOM**；规避：`GGML_CUDA_DISABLE_GRAPHS=1`（作者用 Qwen3.6-27B-UD-Q4_K_XL、ctx 236000 复现） | **高**：af-bench 每题 ~10 轮工具调用 = 长会话多轮；我们跑 ollama 0.40.6（含 CUDA graph 支持）若开图则可能慢性 OOM |
| #28661 / #28640 / #29803 | #28640 已修（2026-09-09），#29803 已修（2026-10-01） | SM70 上非标准 head_dim 的 FA 崩溃 / 两个坏 FA case | **低**：Coder-Next head_dim=256、linear head 128 都属「标准 2 的幂」档位；且我们的 b11669 已含修复 |
| #19672 | completed | CUDA `ggml_mul_mat_id` 断言失败（512-expert MoE，GB10） | 中：**512 路专家的 MoE kernel 是踩过雷的**，但已修；建议冒烟时专门看 512 专家路径 |

→ 落地建议（可写进我们自己的冒烟清单）：
1. 跑 Coder-Next 时**默认设 `GGML_CUDA_DISABLE_GRAPHS=1`**（如果 ollama runner 透传该环境变量——我**未验证** ollama 0.40.6 的 runner 是否读这个变量，`libggml-cuda.so` 路径在 anolis 上是 `/data/models/lib/ollama/cuda_v12/libggml-cuda.so`（429MiB），我 grep 过 `GGML_CUDA_DISABLE_GRAPHS` **未命中字符串**，需实测确认）；
2. 冒烟必须包含：长前缀复用 + 多轮（≥10 轮）→ 观察是否触发 #29255 式的 kernel launch 错误；
3. 观察 `nvidia-smi` 显存是否随轮次单调上涨（#25835 特征）。

---

## 4. 质量证据：官方自报 vs 第三方复现

### 4.1 官方自报（我独立读图复核，不是转述）
我把官方图片下载到本地后**自己读图**（`/tmp/cn_bench.png` 4862×2136，切三段读；`/tmp/cn_pro.png` 4420×2373）：

`https://qianwen-res.oss-accelerate-overseas.aliyuncs.com/Qwen3-Coder-Next/benchmarks.png`
图例：**Qwen3-Coder-Next (Ours) / DeepSeek-V3.2 / GLM-4.7 / MiniMax M2.1**
| 分组（脚手架写在图上） | Coder-Next | DS-V3.2 | GLM-4.7 | MiniMax M2.1 |
|---|---|---|---|---|
| SWE-Bench Verified **(w/ SWE-Agent)** | **70.6** | 70.2 | 74.2 | 74.8 |
| SWE-Bench Multilingual (w/ SWE-Agent) | 62.8 | 62.3 | 63.7 | 66.2 |
| SWE-Bench Pro (w/ SWE-Agent) | **44.3** | 40.9 | 40.6 | 34.6 |
| Terminal-Bench 2.0 (w/ Terminus-2 json) | **36.2** | 39.3 | 37.1 | 32.6 |
| Aider | 66.2 | 69.9 | 52.1 | 61.0 |

`swebench_pro.png`（Pareto 图）另证：Coder-Next 落在 **44% 附近、模型规模 ~80B、3B active**，与 44.3 一致。

→ **原结论的这 5 个数字全部核实为真**（我读的是同一张官方图，结论一致）。

### 4.2 第三方独立复现：**没有找到**
- **SWE-bench 官方榜单 swebench.com**：抓了整页（2.39MB，内嵌 JSON 榜单数据），`grep -c -i "coder-next"` = **0**。榜单里只有老的 `Qwen3-Coder-480B-A35B-Instruct`（OpenHands，resolved 69.6）。→ **Coder-Next 没有提交到官方 SWE-bench 榜单**。
- **Terminal-Bench 2.0 榜单**（tbench.ai，145KB）：grep 无 Qwen3-Coder-Next 条目。
- **aider 榜单**（aider.chat/docs/leaderboards/，569KB）：只有 qwen3-235b-a22b / qwen3-32b，无 Coder-Next。
- **HF 讨论区**：官方仓 52 个 discussion 全部扫过标题；`unsloth/Qwen3-Coder-Next-GGUF` 的 #20「Qwen3-Coder-Next GGUF Benchmarks!」是 **量化保真度**评测（LiveCodeBench v6 / MMLU Pro / GPQA / Math500，750 题，Benjamin Marie 做的），**不是 agentic 解题率**；官方仓 #11 的 tok/s 帖也是本模型唯一的速度贴（见 §5）。
- **基准口径警告（与原结论一致且更严重）**：Coder-Next 的 70.6 用 **SWE-Agent**、TB 用 **Terminus-2**；现役 30B-A3B 的 51.6/31.3 用 **OpenHands 500 轮** + **Terminal-Bench 1.0**（我读官方 30B 卡图 `qwen3-coder-30a3-main.jpg` 复核：Terminal-Bench 31.3 / SWE-bench Verified 51.6 w/ OpenHands 500 turns / Multilingual 34.7 / Aider-Polyglot 33.3 ✅ 与原结论一致）。**「70.6 vs 51.6」不是同一把尺子**，跨表只能量级参考。

→ **对决策的含义**：Coder-Next 的解题率优势目前**只有作者自报一个数据点**。原结论把它当「可上线依据」是**过度自信**；必须在 af-bench 上同口径实测才能采信（我们自己的 harness 才是唯一可信尺子）。

---

## 5. 速度证据：第三方实测清单（含「查不到」的部分）

### 5.1 唯一找到的第三方 Coder-Next 吞吐数字（**不是 V100**）
来源：HF discussion `Qwen/Qwen3-Coder-Next` #11（2026-02-04）与 `lmstudio-community/Qwen3-Coder-Next-GGUF` #2（同一人同帖），原文要点：
```
Model: lmstudio-community/Qwen3-Coder-Next-GGUF (Q4_K_M)
Backend: LM Studio 0.4.1 (CUDA 12)
GPU: NVIDIA GeForce RTX 5080 (16GB GDDR7) | CPU: Intel Core Ultra 9 285K | RAM 64GB
Context 60,000 | **Layer Offloading: 35 MoE Layers to CPU** | KV on GPU (Q8_0) | FA ON | Concurrency 10
Single Request: 40–45 tok/s
Concurrent(10): per-request 9–10 tok/s, total ~70 tok/s
```
→ 这条**是 CPU 重卸载下的数字**（48 层里 35 层在 CPU），既不是 V100，也不能用来推 V100 满载速度。

### 5.2 我逐一排查过、**确认没有** Coder-Next 速度数据的来源
- **DmNep/llm-bench-v100**（原结论引用的那个 V100 基准仓，master 分支 README + `results/RESULTS.md` + `results/RESULTS-llamacpp.md` + `results/raw-20261005-1125.json`）：全文 grep `coder-next` = **0 命中**；该仓只有 qwen3-coder-32k(Q8_0) 45.5、qwen3-thinking-128k 等。→ **确认 Coder-Next 在 V100 上没有任何公开实测**。
- **unsloth 官方文档**（`unsloth.ai/docs/models/qwen3-coder-next`，1.42MB）：grep `tok/s`=0、`V100`=0，只有泛化建议「如果量化能完整放进设备，预期 20+ tokens/s」。
- **HF 全库全文检索**：`qwen3-coder-next` × V100 / 3090 / P40 / 4060Ti 四组查询，返回的都是 README 复制粘贴，无吞吐数据。
- **Reddit（LocalLLaMA）**：本机与 anolis **均不可达**（curl 超时）→ 这条渠道本次复核**未覆盖**。
- 其它 V100 类来源（miyagadget 博客、dual-v100-llama.cpp 报告、knightli llama-bench 榜）原结论已列，**均无 Coder-Next 条目**（我未逐篇重查，见 §7 未覆盖项）。

### 5.3 我自己的外推（推理，不是实测，明确标注）
按 config 复算**每 token 需读取的权重字节**：
- Coder-Next：48 层 × (11 专家 × 3 矩阵 × 2048×512) ≈ **1.66B** 专家参数 + 输出头 0.31B ≈ **2.0B 参数/token**
- 现役 30B-A3B：48 层 × (8 专家 × 3 × 2048×768) ≈ **1.81B** + 0.31B ≈ **2.1B 参数/token**
→ **每 token 权重流量两者几乎相同** ⇒ 理论 decode 速度同档。
但**专家路数差 4 倍**（48×11=528 次小矩阵乘 vs 48×8=384 次），小核发射/散点读固定开销更高。同族实测锚点：
```
Qwen3-30B-A3B   128 专家 → DmNep V100-SXM2: 133 tok/s(ollama) / 110(llama.cpp)；我们 anolis: 135.7
Qwen3.6-35B-A3B 256 专家 → miyagadget V100-SXM2: 98.8 tok/s（同一台机器、Q4_K_M、ctx16k、thinking on）
```
→ 按专家数线性外推，**512 专家的 Coder-Next 在 V100S-PCIe 上约 85–100 tok/s**（V100S 比 SXM2 再慢 ~10% ⇒ ~80–95）。
**原结论的「90–130」偏乐观上沿；我认为更可能是 80–100 tok/s。**
→ **决策含义**：解码比现役慢 ~30–40%，而它是非思考模式（token 少）——**净墙钟方向不明**（吐字少 vs 每字更慢相抵）。这必须实测，不能推断。

---

## 6. 我在 anolis 上的一手实测（本次会话新增，用于校验原结论的附带结论）

环境：anolis-gpu-01，2×V100S-32GB，ollama 0.40.6，现役 qwen3-coder-30b（Q4_K_M，18.5GB），`num_ctx 8192`、`num_predict 256`、`temperature 0`、同一提示词。

| # | 配置 | 实测 decode | 备注 |
|---|---|---|---|
| A | **默认实例**（双卡 spread，OLLAMA_NUM_PARALLEL=2）单请求 | **137.30 / 141.93 tok/s**（load 10.0s，prompt 173.9 / 2629.5 tok/s） | 与原结论 135.7 复现一致 ✅ |
| B | `CUDA_VISIBLE_DEVICES=1` 单卡独立实例 | **137.36 / 140.70 tok/s**（load 7.2s） | **与双卡 spread 一模一样** |
| C | `CUDA_VISIBLE_DEVICES=0` 单卡独立实例 | **137.76 / 141.12 tok/s**（load 6.9s） | 同上 |
| D | 默认实例，**2 个并发** | 107.82 + 110.49 = **218.3 tok/s** | 复现原结论的 219 ✅ |
| E | **两个单卡独立实例各 1 个并发** | 131.45 + 131.47 = **262.9 tok/s** | 比 D 高 **+20.4%**（原结论估 +24%/271，略高） |

**A/B/C 的直接推论**（也是对原结论的修正）：
> ollama 0.40.6 会把现役模型 **按层切到两张卡上**（`ollama-serve.log`：`offloaded 49/49 layers to GPU`；`CUDA0 model buffer size = 8975.64 MiB`；`CUDA1 = 8548.79 MiB`；我的实时 `nvidia-smi`：`0, 10314 MiB, 43%` / `1, 9788 MiB, 44%`）——
> **第 2 张卡既不是「闲置」，也不是「加速器」：它在干活，但 layer 切分是串行流水，token 要依次过两张卡，总时间 = 两段之和 ≈ 单卡。**
> 原结论「第二张卡全程闲置 → 拆成两个实例可 +24%」的**结论方向对（我实测 +20.4%），但前提描述错误**，且真实机理是「串行切分不提速、两个独立实例才能吃满两张卡的带宽」。

**对 Coder-Next 的直接含义（新增风险）**：48.19GiB 权重铺在 2×32GiB 上必然是 layer 切分 ⇒ **单 token decode 速度 ≈ 单卡速度**（不会因为占了两张卡就变快），而**单卡还要再跑一遍 512 路专家的小矩阵乘**。这与 §5.3 的外推一致：期望 80–100 tok/s。
另外，Coder-Next 的 layer 切分会踩在 #29255（Volta layer-split 概率性 kernel launch 崩溃，**open**）的路径上。

---

## 7. 逐条判定：原结论哪些对、哪些要改

| # | 原结论（v100-speed-data.md） | 判定 | 修正/依据 |
|---|---|---|---|
| 1 | 官方 SWE-V 70.6 / Pro 44.3 / TB2.0 36.2 / Multilingual 62.8 / Aider 66.2 | **确认** | 我独立下载官方图读图一致（§4.1） |
| 2 | 现役 30B-A3B SWE-V 51.6 / TB 31.3 | **确认** | 官方 30B 卡图读图一致；但 TB 1.0 vs 2.0 不可横比（§4.2） |
| 3 | 非思考模式、token 不膨胀 | **确认** | 官方 README 第 46 行原文 |
| 4 | Q4_K_M 48.53GB/45.2GiB（unsloth）、52GB（ollama） | **修正** | ollama blob 实测 51.74GB/**48.19GiB** → 每卡 **24.1GiB**（原按 22.6GiB 算，偏乐观）；ollama 的 q4_K_M 与公开 unsloth/Qwen 版哈希都不同 |
| 5 | 双卡装得下，ctx 建议 32K，最多 131072 | **修正（收紧）** | 256K×1slot 约 29.7–30.7GiB/卡（极紧）；**256K×2slot 必然溢出**。我另在现役 30B 上实测到「KV 吃紧时 ollama 把 ~4.8GiB 专家张量掉回 CPU」的先例（§3.4）→ 建议 **ctx ≤ 64K，slot ≤ 2** |
| 6 | KV 24KiB/token | **确认** | 我按 config 独立复算一致 |
| 7 | 「V100 上零直接实测，90–130 tok/s 全是推断」 | **确认（本轮仍未补上）** | 我复查 DmNep 仓 0 命中、unsloth 文档无数字、HF 全库检索无数据；唯一第三方数字是 RTX 5080+CPU 卸载 40–45 tok/s。**我把推断区间收窄为 80–100 tok/s**（专家数 512 外推，§5.3） |
| 8 | 「70.6 是作者自报」 | **确认** | 另补：SWE-bench 官方榜单 swebench.com **0 条目**；TB2.0 榜单、aider 榜单亦无 → **无任何第三方独立复现**（这是原结论「证据强度」里最乐观的一环） |
| 9 | 上游 #27366「正好命中我们的架构家族」「以 stale 关闭」 | **修正（两处）** | 关闭原因是 **not_planned**（2026-10-03），不是 stale；报告模型是 `bartowski/Qwen3.8-27B-GGUF`（arch `qwen35`），**不是 qwen3next**；该 issue 证的是「多卡 Volta 上并行切分模式不可用」，反而支持「只用 layer 切分」这条建议 |
| 10 | 「Coder-Next 有 CUDA 输出损坏 bug 风险」（来自提问里的 qwen3_5 家族经验） | **修正（风险对象）** | 针对 Coder-Next 的真实 bug 是 llama.cpp **#19305**（2026-02-03，修于 #19324）；**ollama 0.40.6 pin b11669(2026-10-15) 已含修复** → 我们这条栈上风险消除；真正的残余风险转移到 **#29255（Volta layer-split 崩溃，open）** 与 **#25835（Volta CUDA-graph 显存泄漏，not_planned）** |
| 11 | 附带结论：「现役 18.5GB 模型在 num_ctx 8192 下只落 1 张卡，第 2 张卡全程闲置」 | **推翻（事实错误）** | 日志 + 实时 nvidia-smi 双向证明双卡都在加载与满负荷；正确表述：「双卡都加载，但 layer 切分串行 → 只买容量不买速度」（§6） |
| 12 | 附带结论：「拆两个独立 ollama 实例，聚合 219 → ~271 tok/s（+24%），单题墙钟不变」 | **部分修正** | 我实测：单卡实例各 ~140 tok/s，双实例并发聚合 **262.9** vs spread 双并发 **218.3** = **+20.4%**（原估 +24%/271 略高）；**「单题墙钟不变」成立**（单请求 137–141，与双卡 spread 相同） |
| 13 | 「MoE 在 V100 上比同体量稠密快 3.2–4.4×」 | **本轮未复核** | 不在本次复核对象（属其它模型的横向表），我未逐条重查原引用的 5 个第三方源；仅顺带确认 Coder-Next 的「同档」外推（§5.3）与该结论不冲突 |
| 14 | 「Coder-Next 是唯一墙钟不涨、解题率大涨的候选」 | **降级为『待实测』** | 解题率无第三方复现（§4.2）；速度无 V100 实测、且我外推是**比现役慢 30–40%**（§5.3）。可上线与否取决于 af-bench 同口径实测，**不能仅凭自报表上线** |

---

## 8. 未能核实 / 未覆盖的项（如实列出）

1. **Qwen3-Coder-Next 在 V100 上的真实 tok/s**：本轮**未跑**（48GB 权重未下载，纪律禁止下载权重；且我不接受「推断当实测」）。同族 256 专家的 98.8 tok/s（V100-SXM2）是我唯一的同架构族锚点。
2. **Reddit / LocalLLaMA**：本机与 anolis 均连接超时 → 本轮未覆盖该渠道（可能存在 Coder-Next 的 V100 帖）。
3. **miyagadget 两篇博客、dual-v100-llama.cpp 报告、knightli 榜、hardware-corner A6000 表**：原结论已引用，本轮未逐篇重查原始输出（只确认了 DmNep 仓无 Coder-Next 条目）。
4. **Coder-Next 在 2×V100S 上的显存实测**：未跑（需下权重）。§3.4 是「实测尺寸 + config 复算 + 现役模型行为外推」，其中「计算缓冲 1.5–2.5GiB/卡」「GatedDeltaNet 状态 ≈72MiB/slot」为**估算**。
5. **ollama 0.40.6 的 runner 是否透传 `GGML_CUDA_DISABLE_GRAPHS=1`**：未验证（我在 `libllama.so` 里 grep 该字符串未命中；`libggml-cuda.so` 在 anolis 上位于 `/data/models/lib/ollama/cuda_v12/`，未逐字节查）。
6. **Qwen3.6-35B-A3B / Qwen3.6-27B**：本次复核对象列了这两个，但它们在原档案里只是「同族对照组」。我**只**独立确认了 DmNep/miyagadget 的 35B-A3B=98.8 tok/s 属第三方实测这一事实被原结论正确转述；**这两个模型本身的规格/分数/速度未做逐项复核**（如需，请单独立项）。

---

## 9. 建议的下一步（按性价比排序）

1. **冒烟（1 小时成本，不需要下 48GB 也能做的部分）**：先在 anolis 上用**现役模型**复现我 §6 的 A/B/C/D/E 五组数据，固化成我们自己的「V100 基线脚本」，并把 `#29255`/`#25835` 的规避写进脚本（禁用 CUDA graph、长会话多轮跑）。
2. **下权重冒烟（Coder-Next）**：一次性拉 `qwen3-coder-next:q4_K_M`（48.19GiB，ollama 官方 tag，避开 unsloth 那些「LM Studio 识别不出架构」的 UD 档），跑：① 加载成功且 `offloaded` 行显示双卡切分；② 20 轮工具调用不崩、tool call JSON 不坏（专门验 unsloth 讨论 #14 那个 `"filePath"/home/...` 坏 JSON 症状）；③ 10 轮会话显存不单调上涨；④ 记录 decode tok/s 与 ctx=8192/32768 两档，**用实测替换我 §5.3 的 80–100 推断**。
3. **同口径质量**：只有 af-bench 上跑出 Coder-Next 与现役 30B-A3B 的**同脚手架**解题率与单题墙钟，才能采信「更值得上」；70.6 是 SWE-Agent 口径，与我们的 OpenHands/自研 harness 不可直接换算。
4. **可立即落地的零风险收益**：按 §6，把「双实例（各绑一张卡）」做成我们的默认本地臂形态 → 聚合吞吐 +20.4%、单题墙钟不变（137–141 tok/s 不变）。注意其机理是「layer 切分串行不提速」，不是「第二张卡闲置」。

---

## 10. 引用清单（本次实际访问的原始出处）

**HF / 模型侧**（hf-mirror 镜像，anolis 出口）
- `https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next`（元数据/许可证/下载量）
- `https://hf-mirror.com/Qwen/Qwen3-Coder-Next/raw/main/config.json`（架构参数）
- `https://hf-mirror.com/Qwen/Qwen3-Coder-Next/raw/main/README.md`（非思考模式声明、部署要求、sglang>=0.5.8）
- `https://hf-mirror.com/api/models/{Qwen/Qwen3-Coder-Next,unsloth/Qwen3-Coder-Next-GGUF,Qwen/Qwen3-Coder-Next-GGUF}/tree/main?recursive=1`（逐文件 size/oid）
- `https://hf-mirror.com/api/models/{Qwen/Qwen3-Coder-Next,unsloth/Qwen3-Coder-Next-GGUF,lmstudio-community/Qwen3-Coder-Next-GGUF,bartowski/Qwen_Qwen3-Coder-Next-GGUF}/discussions[/{n}]`（讨论 5/11/13/14/20）
- 官方图：`https://qianwen-res.oss-accelerate-overseas.aliyuncs.com/Qwen3-Coder-Next/benchmarks.png`、`.../swebench_pro.png`
- 现役基线图：`https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-Coder/qwen3-coder-30a3-main.jpg`

**ollama registry / 库页**
- `https://registry.ollama.ai/v2/library/qwen3-coder-next/manifests/{q4_K_M,q8_0}`（blob 尺寸实测）
- `https://ollama.com/library/qwen3-coder-next/tags`（tag 列表：latest / q4_K_M / q8_0）

**GitHub**
- `api.github.com/repos/ollama/ollama/releases/tags/v0.40.6`（published 2026-10-16）
- `raw.githubusercontent.com/ollama/ollama/v0.40.6/LLAMA_CPP_VERSION` → **b11669**
- `api.github.com/repos/ggml-org/llama.cpp/commits/b11669`（2026-10-15, v0.7.0）
- llama.cpp issues：**#19305**（Coder-Next Poor Outputs，closed completed）、**#19324**（key_gdiff 修复）、**#27366**（not_planned）、**#28661/#28640/#29803**（Volta FA）、**#29255**（open，Volta layer-split 崩溃）、**#25835**（not_planned，CUDA graph 显存泄漏）、**#19672**（512-expert MoE CUDA 断言）

**榜单/第三方**
- `https://www.swebench.com/`（官方榜单，coder-next 命中数 0）
- `https://www.tbench.ai/leaderboard/terminal-bench/2.0`、`https://aider.chat/docs/leaderboards/`（均无 Coder-Next 条目）
- `https://raw.githubusercontent.com/DmNep/llm-bench-v100/master/{README.md,results/RESULTS.md,results/RESULTS-llamacpp.md,results/raw-20261005-1125.json}`（coder-next 命中数 0）
- `https://unsloth.ai/docs/models/qwen3-coder-next`（无 tok/s 数字）

**anolis 一手实测**（命令见 §6 表格与正文；脚本 `/tmp/bench.sh`、`/tmp/bench_par.sh`）
- `nvidia-smi --query-gpu=index,memory.used,utilization.gpu,power.draw --format=csv`
- `grep -n "offloaded|CUDA0 model buffer|CUDA1 model buffer|CPU_Mapped|n_ctx_slot" /data/models/ollama-serve.log`
- `POST http://127.0.0.1:{11434,11435,11436}/api/generate`（`num_ctx 8192, num_predict 256, temperature 0`）
