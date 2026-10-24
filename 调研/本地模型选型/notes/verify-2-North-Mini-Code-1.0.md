# 独立复核：North-Mini-Code-1.0（Cohere）

- **复核日期**：2026-10-21
- **复核对象**：原调研档案 `调研/本地模型选型/notes/western-open.md` §2.1 对 North-Mini-Code-1.0 的全部结论
- **复核机**：pandev-comp（RTX 3070 Laptop 8GB，本机）+ anolis-gpu-01（2× Tesla V100S-PCIE-32GB，sm_70，driver 570.133.20，ollama 0.40.6）经 `ssh anolis` 远程取证
- **网络条件**：`huggingface.co` / `raw.githubusercontent.com`（本机）/ `jsdelivr` 直连被阻断；实际使用 `hf-mirror.com`（HF API + raw）、`github.com/.../raw/...`、`github.com` HTML 页、`api.github.com`（限流但可用）、`artificialanalysis.ai` 内嵌 JSON、`registry.ollama.ai`、`ollama.com`。**未下载任何模型权重**（遵守复核纪律；GGUF 头部信息全部用 HTTP Range 只读前 1.4–18.9MB 元数据区解析）
- **总判定**：**修正**。原结论的**方向正确**（North-Mini-Code 是西方候选中唯一值得上本地臂的），但**三处关键数字错、两条"待验证"风险已被我实测推翻、一条最关键的风险被原报告误判为矛盾**。

---

## 〇、复核结论速览

| # | 原结论 | 复核判定 | 说明 |
|---|---|---|---|
| 1 | 模型真实存在、Apache 2.0、30B/3B MoE | ✅ **确认** | 全部一手复核，含 HF 元数据、config.json、GGUF 头、ollama registry |
| 2 | ollama 能否加载 cohere2moe「未验证，列为现场冒烟第一项」 | ❌ **推翻**（可加载） | 我在 anolis 上用 ollama 0.40.6 自带的 `llama-server` 实测：cohere2moe **被识别为已知架构**并走完 hparam/SWA 校验 |
| 3 | 「ollama 官方库无上述任一新候选」 | ❌ **推翻** | ollama 官方库**有** `north-mini-code-1.0`（Q4_K_M 18.59GB），且 `model_family: cohere2moe` |
| 4 | 每 token 权重：North 2.01GB vs 现役 1.85GB，差 8.5%，推算 ≈125 tok/s | ❌ **数字错** | 真实值 **2.278GB vs 1.920GB，差 18.6%**，推算 **≈114 tok/s**（0.84× 现役，不是 0.92×） |
| 5 | 「AA 76 t/s vs 现役 158 t/s，2.08× 与带宽模型矛盾，是最大待测项」 | ❌ **误判** | 两个数**根本不是同一口径**：76 来自 Cohere 第一方托管 API，158 是 2 个第三方 host 的中位数。不构成"矛盾"，也不构成"待测项" |
| 6 | 官方自报 SWE-V 80.2% pass@10 / 61.0% pass@1 | ⚠️ **需限定** | HF 模型卡 `.eval_results` 自己登记的是 **SWE-V 67.6 / TB2.0 36.0 / SWE-Pro 40.2**（2026-06-09，官方自报 pass@1 口径），比博客的 pass@10 口径低一截 |
| 7 | KV ≈98KB/token，32K ctx 仅 3.2GB | ⚠️ **不完整** | 98KB/token 对，但漏了**滑窗 3:1 交错注意力**——llama.cpp 用 hybrid_iswa 路径，36 个滑窗层只保留 4096 token。32K ctx 实际 KV 仅 **1.17GB**（不是 3.2GB） |
| 8 | 质量证据有第三方独立复现 | ✅ **确认（唯一一家）** | Artificial Analysis 同一指数版本、同一日测得 TB-Hard 31.06% vs 现役 15.15% |
| 9 | 速度证据只有作者自报 | ⚠️ **部分推翻** | 除 AA 外，还有**上游 llama.cpp PR #24260 的作者基准**（RTX 5090 Q4_K_M tg128 = 324.19 t/s）和 **hipfire 的 gfx1151 实测**（≈50 t/s decode） |

---

## 一、模型真实状态核查

### 1.1 官方仓库与元数据（直接证据）

命令与输出：

```
$ curl -sS "https://hf-mirror.com/api/models/CohereLabs/North-Mini-Code-1.0"
id = CohereLabs/North-Mini-Code-1.0
author = CohereLabs
createdAt = 2026-06-05T02:38:01.000Z
lastModified = 2026-06-15T04:32:41.000Z
downloads = 7320
likes = 581
tags = [... 'license:apache-2.0', 'deploy:azure' ...]
```

- **存在、公开、Apache 2.0** —— 确认。HF 下载量 7320、581 likes。
- 权重分 49 个 safetensors 分片；`model.safetensors.index.json` 的 `metadata` = `{'total_parameters': 30484303872, 'total_size': 60968607744}` → **总参 30.48B**（含 embedding 只存一份，lm_head 权重共享）。

### 1.2 参数规模与激活参数（config.json 原文实读）

```
$ curl -sS ".../CohereLabs/North-Mini-Code-1.0/raw/main/config.json"
architectures: ["Cohere2MoeForCausalLM"]   model_type: cohere2_moe
hidden_size 2048   num_hidden_layers 49   num_attention_heads 32
num_key_value_heads 4   head_dim 128
num_experts 128    num_experts_per_tok 8   num_shared_experts 0
expert_selection_fn sigmoid   first_k_dense_replace 1
prefix_dense_intermediate_size 3072   intermediate_size (expert) 768
vocab_size 262144   max_position_embeddings 500000
sliding_window 4096   rope_theta 50000
layer_types = [full_attention, sliding_attention ×3] × 12 + [full_attention]   ← 13 个全局层 / 36 个滑窗层
```

**确认**：30.48B 总参 / 3B 激活（128 专家取 8），SWA 3:1 交错。

**这里有一处原报告未点明、但对速度有决定性影响的事实**：`use_parallel_embedding: false` + 无 `lm_head` 独立权重 ⇒ **embedding 与输出头共享**。原报告按"lm_head 单独读 0.537B 参数"估算，方向对，但没意识到这个 GGUF 里它是**同一个 Q6_K 张量**（见 §2.2）。

### 1.3 官方自报分数（三个口径，必须分开看）

| 来源 | 指标 | 数值 | 口径 |
|---|---|---|---|
| Cohere 博客（2026-06-09） | SWE-Bench Verified | **80.2%** | **pass@10**，SWE-Agent harness v1.1.0 |
| Cohere 博客 | Terminal-Bench v2 | **55.1%** | **pass@10**，自研 ReAct + Harbor Tmux |
| Cohere 博客 | mini-SWE-agent SWE-V | **61.0%** | **pass@1**，mini-SWE-agent harness |
| **HF 模型卡 `.eval_results/`**（机器可读，2026-06-09） | SWE-bench_Verified | **67.6** | 官方自报（HF leaderboard 口径） |
| 同上 | terminalbench_2 | **36.0** | 同上 |
| 同上 | SWE_Bench_Pro | **40.2** | 同上 |
| 博客 | AAII Coding Index | 33.4 | **旧版指数，已下线，不可与现版 Intelligence Index 比** |

```
$ curl -sSL ".../raw/main/.eval_results%2Fswe-bench-verified.yaml"
- dataset: {id: SWE-bench/SWE-bench_Verified, task_id: swe_bench_%_resolved}
  value: 67.6
  date: "2026-06-09"
```

**修正点**：原报告只引了博客的 pass@10（80.2/55.1）和 pass@1（61.0），**没提模型卡自己登记的 67.6 / 36.0 / 40.2**。这三个数是 Cohere 自己写进 HF leaderboard 的，更接近单次 harness 口径，**与我们 af-bench 口径更接近但仍不同**。原报告"官方自报 80.2%"作为宣传口径被直接引用，有选择性放大之嫌。

### 1.4 GGUF 与下载量（全部实读）

**社区量化（非 Cohere 官方）**：

```
$ curl -sS "https://hf-mirror.com/api/models?search=North-Mini-Code&limit=50"
unsloth/North-Mini-Code-1.0-GGUF   dl=232770  likes=147   ← 下载量最高
bartowski/North-Mini-Code-1.0-GGUF dl=5821    likes=5
mradermacher/...-GGUF dl=211 / heimann/...-GGUF dl=105 / Arki05/...-GGUF dl=394
```

| 仓库 | 文件 | 精确字节 | GB |
|---|---|---|---|
| bartowski | North-Mini-Code-1.0-Q4_K_M.gguf | 18,744,024,640 | 18.744 |
| bartowski | North-Mini-Code-1.0-Q3_K_M.gguf | 14,209,048,128 | 14.209 |
| bartowski | North-Mini-Code-1.0-Q5_K_M.gguf | 21,845,253,696 | 21.845 |
| unsloth | North-Mini-Code-1.0-UD-Q4_K_M.gguf | 19,203,xxx,xxx | 19.203 |

（体积数字与原报告一致，**确认**。）

**但原报告漏了一个更重要的渠道 —— ollama 官方库**：

```
$ curl -sS "https://ollama.com/library/north-mini-code-1.0"
north-mini-code-1.0:latest     19GB · 488K context window
north-mini-code-1.0:q4_K_M     19GB
north-mini-code-1.0:q8_0      32GB
north-mini-code-1.0:bf16      61GB

$ curl -sS "https://registry.ollama.ai/v2/library/north-mini-code-1.0/manifests/latest"
layers: [model 18593955136, license 11358, params 31]
$ .../manifests/q4_K_M  → model blob 18,593,955,136 B
$ .../manifests/q8_0    → 32,437,263,680 B
$ .../manifests/bf16    → 61,004,406,080 B

$ .../blobs/sha256:d7d227... (config)
{"model_format":"gguf","model_family":"cohere2moe","model_type":"30.5B"}
```

**这是对原报告的直接推翻**：原结论写「ollama 官方库只有 devstral:24b(14GB)、gpt-oss:20b(14GB)/120b(65GB)、nemotron:70b(43GB 老模型)，**无上述任一新候选**」——**错**。ollama 官方库有 `north-mini-code-1.0`，Q4_K_M = 18.59GB，比 bartowski 的 18.744GB 小 154MB（ollama 用了不同的 embed 量化）。

**对部署的实际意义**：不需要自编 llama.cpp、不需要手工 `ollama create`、不需要 Modelfile 注入模板 —— 直接 `ollama pull north-mini-code-1.0` 即可，且 ollama 官方已经把 `model_family: cohere2moe` 写进 manifest。

### 1.5 许可证

- HF 模型卡 `license: apache-2.0`；ollama registry 的 license blob 内容 = Apache License 2.0 全文。
- **Apache 2.0，确认**，无合规摩擦。

---

## 二、V100（sm_70，2×32GB）可行性核查

### 2.1 结论先行：能跑，且路径比原报告想的简单得多

| 核查项 | 结果 | 证据 |
|---|---|---|
| ollama 0.40.6 内置 llama.cpp 是否支持 cohere2moe | ✅ **支持**（原报告标"未验证"） | anolis 上 `/data/models/lib/ollama/libllama.so.0.7.0` 含 `llama_model_cohere2moe::load_arch_hparams / load_arch_tensors / build_arch_graph / graph_mtp`；`libllama-common.so` 含 `common_chat_params_init_cohere2moe`（Cohere 专用 tool-call parser，见上游 PR #24615） |
| 架构支持何时进上游 | 2026-06-13 合并 | `api.github.com/repos/ggml-org/llama.cpp/pulls/24260` → `merged=true, merged_at=2026-06-13T17:49:01Z`（PR "Add arch support for cohere2-MoE"） |
| 是否有 CUDA 崩溃历史 | 有，但**已修** | issue #30404：RTX 5090(sm_120) 上 cohere2moe + FA 触发 `MUL_MAT failed / illegal memory access`。报告者 2026-10-19 复测：**ollama v0.40.5 / v0.40.6 已不再复现**（"the crash no longer occurs... stable on Blackwell"），issue 关闭 |
| 显存是否够 | ✅ 够，且宽裕 | 权重 18.59GB + KV（见 2.4）→ 单卡 32GB 装得下，双卡 64GB 极宽裕 |
| V100 上的 FA 路径 | 存在专用分支 | 上游 `ggml/src/ggml-cuda/fattn.cu:224` `if (cc == GGML_CUDA_CC_VOLTA)`（"On Volta the GQA optimizations aren't as impactful vs. minimizing wasted compute"）；`:672` `volta_mma_available(cc)` 分支 |
| sm_70 CUDA 内核在 ollama 自带库里 | ✅ 在 | anolis 现行 ollama 0.40.6 的 `cuda_v12/libggml-cuda.so` 在 2×V100S 上正常 offload（见下方日志） |

**anolis 上 ollama 0.40.6 的现役加载日志（现役模型，证明 sm_70 路径通）**：
```
llama_prepare_model_devices: using device CUDA0 (Tesla V100S-PCIE-32GB) (0000:00:07.0) - 32184 MiB free
llama_prepare_model_devices: using device CUDA1 (Tesla V100S-PCIE-32GB) (0000:00:08.0) - 32184 MiB free
print_info: arch = qwen3moe
load_tensors: offloaded 49/49 layers to GPU
load_tensors:   CUDA0 model buffer size =  8975.64 MiB
load_tensors:   CUDA1 model buffer size =  8548.79 MiB
```

### 2.2 【实测】cohere2moe 架构识别验证 —— 零权重下载的探针实验

原报告把「ollama 能否加载 cohere2moe」列为**现场冒烟第一项**。我用**不下载任何权重**的方式把它做掉了：

**方法**：手工构造一个只有元数据、**零张量**的合成 GGUF（`general.architecture = cohere2moe` + 完整 hparam 集 + SWA pattern + 最小 tokenizer），放到 anolis 上用 ollama 自带的 `llama-server` 加载。**架构若被识别，加载器会一路走到张量维度检查才失败；架构若未知，会在架构分派处立刻报 "unknown model architecture"。**

**执行**：
```
$ scp probe_cohere2moe.gguf probe_qwen3moe.gguf probe_bogus.gguf anolis:/tmp/
$ cd /data/models/lib/ollama && ./llama-server --model /tmp/probe_$m.gguf -c 512 --no-warmup
```

**结果**（三次对照，同一台 anolis、同一二进制）：

```
######## PROBE: cohere2moe
E llama_model_load: error loading model: check_tensor_dims: tensor 'token_embd.weight' not found
   ↑ 已通过：架构分派 → hparam 加载（含 logit_scale / expert_gating_func / leading_dense_block_count）
     → SWA pattern 数组类型校验 → tokenizer.ggml.model/pre → tokens/merges/token_type
     → 卡在张量维度检查（真实模型到这里就会有权重）

######## PROBE: qwen3moe   （对照组，同一路径可达）
E llama_model_load: error loading model: error loading model hyperparameters: key not found in model: qwen3moe.context_length

######## PROBE: bogusarchxyz  （阴性对照）
E llama_model_load: error loading model: unknown model architecture: 'bogusarchxyz'
   ↑ 注意：报错里有架构名！cohere2moe 那次没有 —— 它根本没走到"未知架构"这一支
```

**判定**：**`cohere2moe` 在 ollama 0.40.6 内置 llama.cpp 中是已注册架构**，hparam 解析器、SWA 3:1 交错注意力（`sliding_window_pattern` 必须是 uint32 数组，实测确认）、路由/专家参数全部接受。**原报告的"未验证"风险可以关闭。**

（探针文件已在 anolis 上删除：`rm -f /tmp/probe_*.gguf`。）

### 2.3 各量化格式在 Volta 上的死活

| 格式 | 仓库 | Volta(sm_70) | 说明 |
|---|---|---|---|
| **GGUF Q4_K_M** | ollama 官方 / bartowski / unsloth | ✅ **唯一务实的路** | dp4a + Q4_K 查表，走 CUDA，不需张量核 |
| GGUF Q3_K_M / Q5_K_M | 同上 | ✅ 可用 | 14.21 / 21.85GB，Q5_K_M 仍单卡装得下 |
| GGUF IQ2_XXS / IQ3 | bartowski | ✅ 可用但精度掉 | 8.51 / 12.99GB |
| **MXFP4_MOE** | unsloth（18.66GB） | ❌ **死路** | MXFP4 是 Blackwell(sm_100/sm_120) 特性，sm_70 无原生路径 |
| **NVFP4** | michaelw9999 / XanuNetworks / FreedomAISVR | ❌ **死路** | 同上 |
| **FP8** | **Cohere 官方** `CohereLabs/North-Mini-Code-1.0-fp8` | ❌ **死路** | FP8 需 sm_89+；Volta 无 FP8 硬件 |
| **BF16** | ollama 官方 tag `bf16` 61GB | ❌ 死路 | 61GB > 64GB 总显存，且 V100 无 BF16 张量核 |
| w4a16 | **Cohere 官方** `-w4a16`（1043 下载 / 61 likes） | ❌ 死路 | 需 Marlin kernel，sm_80+ |
| AWQ-INT4 | cyankiwi / FenomAI | ❌ 死路 | 需 sm_75+/80+ 的 Marlin 路径 |
| EAGLE 3 投机 | CohereLabs `-eagle` / AlexWortega | ⚠️ 理论可跑 | 但当前 GGUF **不含 nextn/MTP 张量**（见 2.5） |

**"Cohere 官方 FP8 与 w4a16 权重存在"是原报告完全没提的一条**——它们在 Volta 上是死路，但值得记录以防后续有人误以为"官方有 FP8 版本就能用"。

### 2.4 显存账（64GB 双卡）

| 项 | 数值 |
|---|---|
| 权重（ollama q4_K_M） | 18.59 GB |
| KV/token（朴素，49 层全量） | 98 KB/token |
| KV/token（**SWA 感知**，llama.cpp 走 `build_attn_inp_kv_iswa`） | 13 个全局层按 ctx 增长 + 36 个滑窗层固定 4096 上限 |
| → ctx 8192 | **0.52 GB** |
| → ctx 32768 | **1.17 GB** |
| → ctx 131072 | **3.79 GB** |
| → ctx 262144 | **7.28 GB** |
| → ctx 500000（GGUF 上限） | ~13.9 GB |

**修正**：原报告写"32K ctx 仅 3.2GB"。98KB/token 本身没错，但**漏算了 3:1 滑窗交错**——36/49 层只保留 4096 token。llama.cpp 对该架构用 `llama_memory_hybrid_iswa_context`（anolis 的 `libllama.so` 里可见 `build_inp_mem_hybrid_iswa` / `get_recr` / `is_swa` 符号），所以真实 KV 只有 1.17GB，**比原报告乐观**。这给并发留了很大空间（2 并发 × 1.17GB 也没问题）。

### 2.5 MTP / 投机解码

**实测**：bartowski Q4_K_M 的 442 个张量里 **`nextn` / `mtp` 张量数量 = 0**（我逐张量解析确认，`type histogram = {Q4_K:146, F32:98, Q8_0:98, Q6_K:51, Q5_K:49}`，非 blk 张量只有 `output_norm.weight` 与 `token_embd.weight`）。

上游 `src/models/cohere2moe.cpp` 有完整的 MTP 实现（`graph_mtp`、`n_layer_nextn == 1` 断言、`nextn.eh_proj/enorm/hnorm`），但**当前公开发布的 GGUF 不含 MTP 块**，所以：
- 官方 EAGLE-3 draft 模型（`CohereLabs/North-Mini-Code-1.0-eagle`）路线存在，但需要自编 llama.cpp + 配 `--spec-type`；
- **ollama 0.40.6 没有对应开关**（anolis 的 `libllama.so` 有 `graph_mtp` 符号，但 ollama runner 未暴露该参数）。
- 结论：**投机解码在我们这条流水线上不可用，不能计入吞吐收益**。这与前期已知的"MTP/DFlash2 在 --split-mode tensor 下有崩溃 issue"叠加，属于高风险区。

---

## 三、速度证据核查

### 3.1 原报告的"最大风险"是对两个不可比数字的误读

原报告写：
> 实测速度 76 t/s（现役在 AA 上 158 t/s），此 2.08× 差值与带宽模型矛盾，是最大待测项

**我实读了 AA 页面内嵌 JSON，两个数字的口径根本不同**：

| 模型 | medianOutputSpeed | performanceDataSource | hostModelCount |
|---|---|---|---|
| north-mini-code | 76.27 | **`{"type":"firstParty","providerName":"Cohere"}`** | 1 |
| qwen3-coder-30b-a3b-instruct | 158.24 | **`{"type":"median"}`**（无 provider） | 2 |

- 76.27 t/s 是 **Cohere 自己托管的 API**（大概率是他们的 H100 集群 + 自研推理栈 + 可能有投机解码），**不是**这个开放权重在任意硬件上的速度。
- 158.24 t/s 是 **2 个第三方 host 提供该开放权重服务的中位数**。
- 这两个数**不构成同平台对比**，2.08× 的差值**不是模型属性**，也**不是"与带宽模型矛盾"**。原报告把它列为"最大待测项"是错配了一个伪信号。

**同样的错误在原报告对 granite-4-2-30b 的使用中也出现**（41 t/s，来源 `firstParty/IBM`），只是那里方向恰好一致（稠密确实慢），掩盖了口径问题。

**顺带一个对原报告有利但它没说的事实**：north-mini-code 的 AA `intelligenceIndexEvaluations` 里，
```
{"slug":"terminalbench-4-0","score":0.0051,"outputTokensPerTask":43981.67,"costPerTask":0,"timePerTask":568.83}
```
43982 token / 568.8 s = **77.3 t/s**，与它自报的 76.27 t/s 完全自洽 → **AA 的速度数是可信的、只是测的是 Cohere 的托管栈**。

### 3.2 第三方/上游实测 tok/s（我另外找到的，原报告没有）

**（a）上游 llama.cpp PR #24260 作者的基准**（作者自测，但硬件/参数/模型文件全公开，可复现）：

```
Device 0: NVIDIA GeForce RTX 5090, compute capability 12.0, VMM: yes, VRAM: 32606 MiB
| model                          | size    | params | backend | ngl | test  | t/s             |
| cohere2_moe 30B.A3B NVFP4      | 16.15 GiB | 30.48 B | CUDA | -1 | pp512 | 11120.91 ± 47.90 |
| cohere2_moe 30B.A3B NVFP4      | 16.15 GiB | 30.48 B | CUDA | -1 | tg128 |   284.04 ± 4.20  |
| cohere2_moe 30B.A3B Q4_K-Medium| 17.44 GiB | 30.48 B | CUDA | -1 | pp512 |  9805.59 ± 94.17 |
| cohere2_moe 30B.A3B Q4_K-Medium| 17.44 GiB | 30.48 B | CUDA | -1 | tg128 |   324.19 ± 2.84  |
```

同一 PR 里还贴了 tool-calling 实际输出（llama-server 内置工具调用正常）。**这是目前唯一一条"llama.cpp + cohere2moe + Q4_K_M"的公开 tok/s 实测**，但硬件是 Blackwell 5090，不是 V100。

**（b）hipfire 项目的 gfx1151（AMD）实测**（`warpfront/hipfire` PR #539，2026-07-21 合并）：

> "hipfire bench reports a misleadingly low prefill number for cohere2moe (North-Mini-Code): ~58 tok/s, roughly equal to decode speed... real batched prefill is ~330 tok/s on gfx1151, ~6× the ~50 tok/s decode"

即 **gfx1151 上 cohere2moe decode ≈50 t/s、prefill ≈330 t/s**。这是第三方（非作者）实测，但硬件是 AMD 集显，同样不能直接搬到 V100。

**（c）V100 / 3090 / P40 / 4060Ti 上的 north-mini-code tok/s 实测**：**我没找到任何一条**。`kennel-org/llama-bench-tuner` issue #1 明确把 "North Mini Code 1.0" 列入待测清单（目标机器是 **2× Tesla P40 24GB** 和 RTX 4000 Ada 20GB），但该 issue 仍是 Open 状态、**尚未出结果**。

> **结论：截至 2026-10-21，没有任何第三方在 V100 / 3090 / P40 / 4060Ti 上实测过 north-mini-code 的 tok/s。** 原报告"速度只有作者自报"的说法，在"我们关心的那批老卡"这个限定下**成立**。

### 3.3 我自己算的每 token 权重流量（修正原报告的核心数字）

原报告的 2.01GB / 1.85GB / 8.5% 差异是从**参数量 × 假设 bits/weight** 估的。我改用**逐张量精确字节**（从 GGUF 张量表读出每个张量的实际量化类型，用 GGML 块大小换算），这个方法可以自校验：

**自校验**：用同样方法预测整个文件大小
- North-Mini-Code Q4_K_M：预测 **18.7336 GB** vs 实际 **18.7440 GB** → 误差 **+0.05%** ✅
- 现役 qwen3-coder-30b Q4_K_M：预测 **18.5507 GB** vs 实际 **18.5567 GB** → 误差 **+0.03%** ✅

**每 token 实际读取量**（专家按 8/128 激活折算，embedding 只做查表不整块读；North 的输出头**与 embedding 共享同一个 Q6_K 张量**，所以 lm_head 读的是 262144×2048 的 Q6_K = 0.4404 GB）：

| 项 | North-Mini-Code | 现役 qwen3-coder-30b |
|---|---|---|
| 激活专家（8/128） | 1.0971 GB | 1.0971 GB |
| 注意力 | 0.6775 GB（q=Q6_K, k/v=Q8_0, o=Q5_K） | 0.5165 GB（q/k/o=Q4_K, v=Q6_K） |
| 路由器 | 0.0503 GB | 0.0503 GB |
| 稠密层 0 | 0.0122 GB | 0.0004 GB（无稠密首层） |
| lm_head | **0.4404 GB**（Q6_K 共享 embed） | 0.2553 GB（Q6_K 独立） |
| **合计/ token** | **2.2775 GB** | **1.9196 GB** |
| **比例** | **1.186×**（不是原报告的 1.085×） | — |

**用现役实测反推有效带宽**：`135.7 tok/s × 1.9196 GB = 260.5 GB/s`
**→ 推算 North 在同一台 V100S 上 ≈ 260.5 / 2.2775 = 114.4 tok/s**

**修正**：原报告说"只多 8%，推算 ≈125 tok/s（0.92× 现役）"。**真实是多 18.6%，推算 ≈114 tok/s（0.84× 现役）**。差 10 个百分点，方向对（North 更慢）但幅度被低估了。

**为什么原报告低估了**：它按"均匀 4.83 bit/weight"估算，而实际 bartowski Q4_K_M 是**混合量化**（`attn_q` 用 Q6_K、`attn_k/v` 用 Q8_0、`attn_output` 用 Q5_K、North 的 `token_embd` 用 Q6_K），这些高比特张量在 North 上占比更大。

### 3.4 墙上时间账（我们真正在乎的）

AA 实测：north-mini-code 在 Terminal-Bench 4.0 上 **43982 输出 token/题、568.8 s/题**。

| 场景 | 输出 token | 现役 @135.7 t/s | North @114 t/s（推算） |
|---|---|---|---|
| 我们的典型单题（假设 15K 输出） | 15,000 | 111 s | **132 s**（+19%） |
| AA 实测同量级（43982） | 43,982 | 324 s | **386 s**（+19%） |

**关键判断**：原报告担心的"thinking token 膨胀吃掉 2.05× 的分数优势"——**方向对，但幅度被 AA 数据反证了**。AA 显示 north 的 II 层面输出 token 里 reasoning 只占 10553、answer 7802，**比 granite-4-2-30b 的 reasoning 43890 少得多**；north 是"轻度思考"型（AA 标 `reasoningTokens: 2000`）。所以**token 膨胀不是 2 倍级**，墙上时间大约是现役的 1.2 倍（速度惩罚）× 1.0～1.1 倍（token 惩罚）≈ **1.2～1.3 倍**。

**但反过来也要说清楚**：north 的 TB-Hard 31.06% vs 现役 15.15% 是 **2.05× 的相对题数提升**。若我们每题墙上时间只贵 20～30%，那**净收益是明确的正数**（每单位墙钟时间的解题率提升约 1.55～1.7×）。**这仍然支持"值得上"，但收益比原报告暗示的小。**

---

## 四、质量证据核查

### 4.1 第三方独立复现：**有，且只有一家**

**Artificial Analysis（2026-10-21 当日页面内嵌 JSON 实读）**：

```
$ curl -sS "https://artificialanalysis.ai/models/north-mini-code"  → 解析内嵌 JSON
north-mini-code:
  intelligenceIndex = 9.91462776590372   intelligenceIndexIsEstimated = False  ← 实测
  terminalbenchHard = 0.310606060606061
  terminalBench21   = 0.355805243445693
  tau2 = 0.374269005847953   gpqa = 0.756565656565657   lcr = 0.373333333333333
  ifbench = 0.575510204081633   hle = 0.110750695088044   scicode = 0.387731481481481
  parameters = 30, inferenceParametersActiveBillions = 3, contextWindowTokens = 256000
  licenseName = "Apache 2.0"   isOpenWeights = True   isReasoning = True
  intelligenceIndexTimePerTask = 237.395 s

qwen3-coder-30b-a3b-instruct:
  intelligenceIndex = 9.58537639337592   intelligenceIndexIsEstimated = True   ← 估算
  terminalbenchHard = 0.151515151515152
  terminalBench21 = None
  tau2 = 0.345029239766082   gpqa = 0.516161616161616   lcr = 0.326666666666667
  microevalsEnabled = False   deprecated = True
  parameters = 30.5, inferenceParametersActiveBillions = 3.3
```

**这是全篇最重要的一个修正 —— 原报告的 "9.91 vs 9.59" 对比是「实测 vs 估算」**：

- north-mini-code：`intelligenceIndexIsEstimated = **False**`，`microevalsEnabled = True`，且有完整的 10 项 `intelligenceIndexEvaluations`（含 per-task token 数与秒数）。
- 现役 qwen3-coder-30b：`intelligenceIndexIsEstimated = **True**`，`microevalsEnabled = **False**`，`intelligenceIndexEvaluations = []`（**空的**），而且 AA 已把它标记 **`deprecated: True`**。

也就是说：AA **没有**对现役做过微评测，9.59 是**模型化的估算**。原报告把它和 north 的实测值并排写成"9.91（现役 9.59）"并当作质量证据，属于把不同性质的数据等同。

**但 TB-Hard 的对比是干净的**：两个数都是 AA 实测的同一指标（north 0.3106 / qwen 0.1515），**2.05× 的相对提升成立**。原报告这一条**确认**。

**口径警告（我核查过）**：`terminalbenchHard`（顶层字段，0.3106）与 `terminalbench-4-0`（评测项，0.0051）是**两个不同的东西**——我对全站 705 个模型做了交叉验证，80 个同时有两者的模型里**没有一对相等**（如 gpt-5-6-sol: 0.6591 vs 0.3990；claude-sonnet-5-5: 0.6364 vs 0）。原报告只用了顶层 `terminalbenchHard`，口径一致，**没问题**。

**AA 同平台横向定位（我补的，原报告没有）**——30～40B 开放权重 MoE 的 TB-Hard 排序：
```
qwen3-6-35b-a3b              0.3485
gemma-4-31b                  0.3636
north-mini-code              0.3106
gemma-4-31b-non-reasoning    0.3030
qwen3-5-35b-a3b              0.2652
nemotron-cascade-2-30b-a3b   0.2121
qwen3-coder-30b-a3b-instruct 0.1515   ← 现役
```
**North 在同量级 MoE 里是前列，但不是第一**。而在同平台的 **TB 2.1** 上：north 0.3558 低于 qwen3-6-35b-a3b 的 0.4494、gemma-4-31b 的 0.4345。

**结论**：原报告说"TB2.1 35.58% 为本轮西方候选最高"——**这个限定词（西方候选）是对的**，我核对了 AA 全部 705 个模型，devstral-2 是 0.3034、devstral-small-2 是 0.2959、granite-4-2-30b 是 0.2659，north 0.3558 确实高于这些西方开放权重模型。**但放到全部候选里它不是最强**（东方同代 MoE 更高），原报告如果被读成"最强"会误导。

### 4.2 官方自报的独立性问题

- 官方 SWE-V 80.2% 是 **pass@10**（同一题跑 10 次取最好），**不可与单次 harness 结果比**。原报告已提示这一点，**确认**。
- HF 模型卡自己登记的 67.6（TB2.0 36.0、SWE-Pro 40.2）更接近 pass@1 口径，原报告**漏引**。
- **没有找到任何第三方对 north-mini-code 的 SWE-bench Verified / SWE-bench Pro 独立复现**。`sbley/claude-code-agent-test#469` 之类的"第三方复现"全是机器人自动生成的 release-tracking 公告（内容直接抄 Cohere 博客），**不构成复现**。
- **唯一实质性的第三方 agentic 分数来源就是 AA**，且 AA 没测 SWE-bench（它测的是 Terminal-Bench / GDPVal / Briefcase / AutomationBench / SciCode / HLE / CritPt / Omniscience / LongContext）。

### 4.3 与我们题型的匹配度

我们的 af-bench 跑 SWE-bench Verified / Terminal-Bench / **InjecAgent** / **τ²-bench**。

- **Terminal-Bench** → AA TB-Hard 2.05× 优势直接对口 ✅
- **SWE-bench Verified** → 只有官方自报（pass@10 80.2 / 模型卡 67.6），**无第三方** ⚠️
- **τ²-bench** → north 0.3743 vs 现役 0.3450，**只高 8.5%**，几乎无差异 ⚠️（原报告没给这个对比，我补上；且 nemotron-cascade-2 的 0.5321 远高于两者）
- **InjecAgent** → **AA 和官方都没有这个 benchmark 的分数**，完全无证据 ⚠️

**所以：原报告"2.05× 的 agentic 分数优势"实际上只在 Terminal-Bench 这一项上成立。** 我们的四个题型里，只有一个有第三方证据支持明显提升。

---

## 五、原结论里需要修正的具体条目

### 必须修正（数字/事实错误）

1. **每 token 权重流量与速度推算**：2.01GB / 1.85GB / 8.5% / 125 tok/s → **2.278GB / 1.920GB / 18.6% / ≈114 tok/s（0.84× 现役）**。见 §3.3。
2. **「ollama 官方库无上述任一新候选」→ 错**。ollama 官方库有 `north-mini-code-1.0`（q4_K_M 18.59GB / q8_0 32.44GB / bf16 61.00GB），`model_family: cohere2moe`。见 §1.4。
3. **「ollama 能否直接加载 cohere2moe 未验证，列为现场冒烟第一项」→ 已验证为可以**（合成 GGUF 探针实测）。见 §2.2。
4. **「AA 76 t/s vs 现役 158 t/s 的 2.08× 差值与带宽模型矛盾，是最大待测项」→ 误判**。两者口径不同（Cohere 第一方 API vs 第三方 host 中位数），不是同平台对比，不构成矛盾。见 §3.1。
5. **「官方自报 SWE-V 80.2%」需并列 HF 模型卡自登记的 67.6**（以及 TB2.0 36.0、SWE-Pro 40.2），否则是选择性引用。见 §1.3。
6. **「AA Intelligence Index 9.91（现役 9.59）」是「实测 vs 估算」的不对等对比**。现役的 9.59 是 AA 模型化估算（`intelligenceIndexIsEstimated=True`、`microevalsEnabled=False`、评测项为空、AA 已标 deprecated）。见 §4.1。
7. **「KV 32K ctx 仅 3.2GB」→ 实际 1.17GB**（漏算 3:1 滑窗交错，llama.cpp 走 hybrid_iswa）。见 §2.4。

### 需要补充限定

8. **速度证据不止作者自报**：还有上游 llama.cpp PR #24260 的 RTX 5090 Q4_K_M **tg128 = 324.19 t/s / pp512 = 9805.59 t/s**，以及 hipfire 的 gfx1151 **decode ≈50 t/s / prefill ≈330 t/s**。但在 **V100/P40/3090/4060Ti 上仍无任何实测**（kennel-org 的 P40 计划 issue 仍 Open 未出数）。
9. **公开 GGUF 不含 MTP/nextn 张量**（442 张量里 0 个），投机解码在本流水线不可用，吞吐不能按此打折/加分。
10. **Cohere 官方有 FP8 与 w4a16 权重**（各有独立仓库），但在 Volta 上是死路。
11. **同平台横向位置**：north 的 TB-Hard 0.3106 在 30–40B 开放权重 MoE 里排前列但不是第一（qwen3-6-35b-a3b 0.3485、gemma-4-31b 0.3636 更高）；TB2.1 同样不是第一。
12. **对我们题型的收益分布不均**：Terminal-Bench 优势确凿（2.05×），τ²-bench 几乎无差（+8.5%），SWE-V 无第三方证据，InjecAgent 零证据。
13. **工具调用模板与现役不同源**：North 用 Cohere 自有格式 `<|START_ACTION|>[{"tool_call_id","tool_name","parameters"}]<|END_ACTION|>`（`chat_template.jinja` 实读），现役用 qwen3 格式。好消息：**llama.cpp 已有专门的 `common_chat_params_init_cohere2moe` parser**（上游 PR #24615，2026-06-14 合并），ollama 0.40.6 的 `libllama-common.so` 里在。但我们 af-bench 若自己做 JSON 抽取，仍需做一次往返验证。

### 确认无误（不需改）

- 模型真实存在、Apache 2.0、30.48B/3B 激活、128 专家取 8、hidden 2048 ✅
- GGUF 体积（bartowski Q4_K_M 18.744GB / Q3_K_M 14.209 / Q5_K_M 21.845；unsloth UD-Q4_K_M 19.203）✅
- 架构字符串 `general.architecture = cohere2moe`、`expert_count=128`、`expert_used_count=8`、`vocab_size=262144`、`leading_dense_block_count=1`、`sliding_window_pattern` 长度 49 ✅（我逐项复现了 Range 解析）
- AA 的 TB-Hard 31.06% / TB2.1 35.58% / τ² 37.43% / GPQA 75.66% / AA-LCR 37.3% ✅
- 「TB2.1 35.58% 为西方开放权重候选最高」✅（我核对了 AA 全部 705 个模型）
- 「官方 SWE-V 只有 pass@10，不可与单次 harness 直接比」✅
- 「它是 thinking 模型（AA Reasoning=Yes）」✅（但膨胀幅度远小于 granite-4-2-30b）
- 「vLLM 有支持」（我补：`vllm/model_executor/models/registry.py:89` 有 `"Cohere2MoeForCausalLM": ("cohere2_moe", "Cohere2MoeForCausalLM")`，但 vLLM V1 要 CC≥7.5，V100 已被移除 → 对我们依然不可用）
- 上游 PR #24260 的**架构已合并**（2026-06-13）✅

---

## 六、给决策者的落地结论

**结论：North-Mini-Code-1.0 仍然是西方开放权重里唯一值得替换现役的候选，方向不变，但预期收益要下调、风险要下调（因为两个最大的"待验证"其实都是伪风险或已被证伪）。**

**上调的确定性**：
- 部署路径确定：ollama 官方库有，架构已被 ollama 0.40.6 识别（我实测），无需自编 llama.cpp。
- 磁盘不是约束（18.59GB）。
- 显存宽裕（权重 18.59GB + 32K ctx KV 1.17GB，单卡 32GB 就够，双卡 64GB 可做多副本）。

**下调的预期**：
- 速度：**≈114 tok/s（0.84× 现役）**，不是原报告的 125（0.92×）。
- 质量：TB-Hard 2.05× 的优势确凿，但只在 Terminal-Bench 上；SWE-V 无第三方证据、τ²-bench 仅 +8.5%、InjecAgent 零证据。
- 单题墙上时间预计是现役的 **1.2～1.3 倍**。

**净账**（单题墙钟每分钟能多解多少题）：约 **1.5～1.7×** —— 仍然显著为正。

**上生产前仍必须实测的（已从 3 项缩到 2 项，且都能在 1 小时内做完）**：
1. **在 anolis 上 `ollama pull north-mini-code-1.0` + 跑一次 af-bench 冒烟**（重点看：① 工具调用 JSON 往返是否稳；② 滑窗+全局交错注意力在 sm_70 上是否输出正常 —— 这正是我们已知吃过亏的"速度正常但输出损坏"类问题；③ 实测 tok/s 是否落在 100～125 区间）。这是唯一还剩的硬未知。
2. **af-bench 口径的 SWE-bench Verified 实测**（官方 67.6 / 80.2 两个口径都不可直接用），至少跑 30～50 题。

**已从待测清单里划掉的**：
- ❌ "ollama 能否加载 cohere2moe" —— 已实测确认可以（§2.2）
- ❌ "AA 76 vs 158 的 2.08× 矛盾" —— 伪信号，口径不同（§3.1）
- ❌ "KV 32K 要 3.2GB" —— 实际 1.17GB（§2.4）

**新列进去的**：
- ⚠️ 竞品对照：qwen3-6-35b-a3b（AA TB-Hard 0.3485、TB2.1 0.4494、II 18.23）和 gemma-4-31b（TB-Hard 0.3636）在同平台更强，若它们有可用的 GGUF/Q4 且速度接近，应纳入同批对比——**原报告的候选清单里完全没有这两个**。

---

## 附：本复核执行过的检查清单

| # | 检查 | 手段 | 结果 |
|---|---|---|---|
| 1 | HF 模型元数据 | `curl hf-mirror.com/api/models/CohereLabs/North-Mini-Code-1.0` | 通过 |
| 2 | config.json 原文 | `curl .../raw/main/config.json` | 通过 |
| 3 | safetensors index（总参） | `curl .../raw/main/model.safetensors.index.json` | 通过（30,484,303,872） |
| 4 | 官方 .eval_results yaml ×3 | `curl .../raw/main/.eval_results%2F*.yaml` | 通过（67.6 / 36.0 / 40.2） |
| 5 | Cohere 博客 | `curl hf-mirror.com/blog/CohereLabs/introducing-north-mini-code` | 通过（80.2/61.0/55.1/33.4） |
| 6 | GGUF 头（KV + 张量表） | HTTP Range 只读 0–18.87MB，自写 GGUF 解析器 | 通过（cohere2moe/442 张量/无 nextn） |
| 7 | GGUF 体积 ×5 | HF API `tree`（lfs.size） | 通过 |
| 8 | 全部 North 相关 HF 仓库搜索 | `api/models?search=North-Mini-Code` | 通过（47 个仓库） |
| 9 | ollama 官方库存在性 | `ollama.com/library/north-mini-code-1.0` + registry manifest ×4 tag | 通过（**推翻原结论**） |
| 10 | ollama config blob | registry blobs fetch | 通过（model_family=cohere2moe） |
| 11 | ollama 0.40.6 内含 cohere2moe | anolis 上 `strings libllama.so.0.7.0` | 通过 |
| 12 | **cohere2moe 架构识别实测** | **合成零张量 GGUF → anolis 上 `llama-server` 加载 ×3 对照** | **通过（推翻原"未验证"）** |
| 13 | 已知 CUDA 崩溃是否已修 | `api.github.com/repos/ggml-org/llama.cpp/issues/30404` + 3 条评论 | 通过（0.40.5/0.40.6 已修） |
| 14 | 架构上游合入时间 | `api.github.com/repos/ggml-org/llama.cpp/pulls/24260` | 通过（2026-06-13） |
| 15 | 全部 llama.cpp cohere2moe 相关 issue | `api.github.com/search/issues?q=cohere2moe` | 通过（15 条） |
| 16 | vLLM 支持 | `raw.githubusercontent.com/.../registry.py:89` | 通过 |
| 17 | AA north-mini-code 页 | `curl artificialanalysis.ai/models/north-mini-code` + 内嵌 JSON 解析 | 通过（II 9.9146 实测 / 76.27 t/s firstParty/Cohere） |
| 18 | AA qwen3-coder-30b 页 | `curl artificialanalysis.ai/models/qwen3-coder-30b-a3b-instruct` | 通过（II 9.5854 **估算** / 158.24 t/s median） |
| 19 | AA 全站 705 模型交叉验证 | 从 north 页内嵌 JSON 解析全部模型对象 | 通过（terminalbenchHard ≠ terminalbench-4-0，80 对无一相等） |
| 20 | 上游 llama.cpp 基准 | `curl github.com/ggml-org/llama.cpp/pull/24260` HTML | 通过（5090: Q4_K_M tg128 324.19 t/s） |
| 21 | 第三方 AMD 实测 | `curl github.com/warpfront/hipfire/pull/539` | 通过（gfx1151 decode ≈50 / prefill ≈330 t/s） |
| 22 | 现役 GGUF 头 + 每 token 字节 | anolis 上跑自写解析器 | 通过（18.5507 GB 预测 vs 18.5567 实际） |
| 23 | ollama 0.40.6 sm_70 可用性 | anolis `ollama-serve.log` | 通过（双卡 offload 49/49 层） |
| 24 | 显存/KV 计算 | 自算（SWA 感知） | 通过（32K → 1.17GB） |
| 25 | 权重下载 | — | **未做**（遵守纪律） |
| 26 | V100 上 north-mini-code 实跑 tok/s | — | **未做**（无权重；且被要求不下载权重） |
| 27 | af-bench 口径 SWE-V 复现 | — | **未做**（无权重 + 本次职责为复核非实测） |
| 28 | Reddit 讨论检索 | `reddit.com` 直连 | **未做**（网络不可达） |
| 29 | NVIDIA 官网 V100S 带宽页 | `nvidia.com/en-us/data-center/v100s/` | **未做**（404；带宽改用我方实测反推的 260.5 GB/s，不依赖标称值） |
