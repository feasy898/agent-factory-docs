# 复核档案 #1：GLM-4.7-Flash（智谱 30B-A3B, MIT）—— 独立复核

- 复核日期：**2026-10-21**
- 复核对象（原调研的「复核对象」栏三个）：
  1. **GLM-4.7-Flash**（智谱，30B-A3B，MIT）—— 主对象
  2. **GLM-4.7-Flash-Coder**（whitecircle 社区 SFT）
  3. **Ling-3.0-flash-REAP288-71B-A5B**（社区压缩探针）
- 被复核的原结论：`调研/本地模型选型/notes/china-vendors.md`（第 26/29/42/43/45/114-140/147-153/196-211/293 行等）
- 复核者立场：**只做核查，不改写原结论**。查不到的一律写「无法核实」。

---

## 0. 复核结论速览

| 维度 | 原结论 | 复核判定 |
|---|---|---|
| 官方仓库/参数/许可/ctx | 30B-A3B、MIT、ctx 200K、Q4_K_M 18.31GB | ✅ **属实**，且可补更硬的数字：GGUF `general.architecture = deepseek2`、`print_info: model params = 29.94 B`、47 层、64 专家选 4 + 1 共享、q_lora 768 / kv_lora 512、`context_length = 202752` |
| GGUF 存在性与下载量 | ggml-org 官方 GGUF + unsloth 全量化档 | ✅ 属实。**ggml-org/GLM-4.7-Flash-GGUF 下载 29,839**（lastMod 2026-01-23）；unsloth/GLM-4.7-Flash-GGUF 下载 230,934（lastMod 2026-02-12） |
| V100 上能不能跑 | 「能跑，且第二卡照旧空转」 | ✅ **能跑**（有第三方在 Tesla V100-SXM2-32GB 上真跑起来过），⚠️ 但「同构、第二卡空转」的显存账算错了（见 §4.3）、**必须 `-fa off`**，且 198K 上下文在单卡上装不下 |
| 速度证据 | 「V100 上 decode 约 80–120 tok/s」（推断，中置信度） | ⚠️ **无任何 V100 tok/s 实测**；最接近的同代证据是 RTX 3090 修好 FA 后 **tg128 = 108.10 tok/s**。V100 预期应下调到 **80–110 tok/s**，**大概率慢于现役 135.7 tok/s** |
| 质量证据 | 「官方 SWE-V 59.2 / τ²-Bench 79.5」 | ✅ 数字属实（官方自报），❗ **零第三方独立复现**；AA 的 Index 15 是 `intelligenceIndexIsEstimated = true`（估计值，非实测）；swe-rebench 榜单上 GLM-4.7 Flash 的 model 列是 **N/A** |
| 「思考关不掉」 | 「它是 reasoning 模型且思考关不掉（HF 讨论 #56）」 | ❌ **错的**。官方 chat template 里就有 `enable_thinking` 开关，官方文档明确 GLM-4.7 series 可 `"thinking": {"type": "disabled"}`；模型卡反而说多轮 agentic 任务**应开启** Preserved Thinking |
| 「MLA → KV 极小 → 198K 在 32GB 卡可行」 | 高置信推断 I3 | ❌ **错的**。V100 实测日志：llama.cpp 对该模型 **K 与 V 都存 f16**，= **99.9 KiB/token**；198K 需 **~19.3 GiB** KV，与 19GB 权重叠加后单卡 32GB 装不下 |

**总判定：模型本身是真实、可用、值得装的（MIT + 官方 GGUF + 官方模板 + 已有 MTP 支持），但原结论对它最关键的两条推断（思考关不掉 / KV 极小）方向反了，而且「V100 上与现役同速」这一立论基础站不住 —— 现有证据指向它比现役略慢。**

---

## 1. 本轮实际跑过的核查（可复核）

| # | 命令 | 目的 | 结果 |
|---|---|---|---|
| C1 | `getent hosts anolis-gpu-01` / `ping -c1 anolis-gpu-01` | 能否在目标机实测 | **失败**（exit 2，DNS 解析不了）。本会话主机是 `pandev-comp`（`nvidia-smi` → RTX 3070 Laptop 8192 MiB） |
| C2 | `curl https://hf-mirror.com/api/models/zai-org/GLM-4.7-Flash` | 官方仓库元数据 | downloads **1,085,125**、likes 1,880、lastMod 2026-01-29、tags 含 `license:mit`、`glm4_moe_lite` |
| C3 | `curl https://hf-mirror.com/zai-org/GLM-4.7-Flash/raw/main/config.json` | 参数真值 | 见 §3.1 |
| C4 | `curl -r 0-40000000 <ggml-org GGUF>` + `gguf` python 解析（`pip install --break-system-packages gguf`） | **读 GGUF 元数据**（不下载权重，只读头部 40MB 后即删） | 见 §3.2，架构 = `deepseek2` |
| C5 | `curl https://hf-mirror.com/api/models/unsloth/GLM-4.7-Flash-GGUF/tree/main?recursive=1` | 各量化真值体积 | Q4_K_M **18,312,339,808 B = 18.31 GB**、Q8_0 31.84 GB、MXFP4_MOE 16.97 GB |
| C6 | `curl https://hf-mirror.com/api/models/ggml-org/GLM-4.7-Flash-GGUF/tree/main?recursive=1` | 官方 GGUF 真值体积 | `GLM-4.7-Flash-Q4_K.gguf` **18,244,193,920 B = 18.24 GB**（注意 file_type=15 = Q4_K_M） |
| C7 | `curl -H "Accept: application/vnd.docker.distribution.manifest.v2+json" https://registry.ollama.ai/v2/library/glm-4.7-flash/manifests/q4_K_M` | ollama tag 真实 blob | **19,019,269,280 B = 19.02 GB**；q8_0 = 31.84 GB |
| C8 | `curl https://ollama.com/library/glm-4.7-flash`（剥标签） | ollama 卡片原文 | 「requires Ollama 0.14.3 which is currently in pre-release」、三个 tag 全 198K context、「4 months ago」 |
| C9 | `curl https://ollama.com/library/glm-4.7` | 「大版已下架」核查 | 原文：**「glm-4.7 was retired on July 15, 2026. No models have been pushed.」** → 原结论属实 |
| C10 | `curl https://hf-mirror.com/api/models/zai-org/GLM-4.7-Flash/discussions/{47,48,56,66,69,71,75,46,...}` | 逐条拉社区讨论原文 | 见 §6、§7 |
| C11 | `curl https://raw.githubusercontent.com/ggml-org/llama.cpp/master/{src/llama-arch.cpp,src/models/deepseek2.cpp,ggml/src/ggml-cuda/fattn.cu,ggml/src/ggml-cuda/CMakeLists.txt}` | 引擎支持度 / sm_70 编译 | 见 §4 |
| C12 | `curl https://api.github.com/search/issues?q=GLM-4.7-Flash+repo:ggml-org/llama.cpp` + `curl https://github.com/ggml-org/llama.cpp/issues/18948`（HTML） | V100 上的真实案例 | 见 §5.1（**决定性证据**） |
| C13 | `curl https://artificialanalysis.ai/models/glm-4-7-flash`（1.6MB HTML，内嵌 JSON） | 第三方分数与速度 | 见 §6.2 |
| C14 | `curl https://swe-rebench.com/`（7.8MB HTML） | 第三方 agentic 榜单 | 见 §6.3 |
| C15 | `curl https://hf-mirror.com/whitecircle/GLM-4.7-Flash-Coder/raw/main/README.md` | SFT 自测数字 | 见 §7.1 |
| C16 | `curl https://raw.githubusercontent.com/ggml-org/llama.cpp/master/models/templates/GLM-4.7-Flash.jinja` | 官方模板的思考开关 | 见 §4.4 |
| C17 | `curl https://hf-mirror.com/api/models/unsloth/Qwen3-Coder-Next-GGUF/tree/main?recursive=1` | 「80B-A3B Q4 ≈45GB」核查 | IQ4_NL **45.13 GB**、Q4_1 合计 50.05 GB、Q5_K_M 56.86 GB、Q6_K **65.61 GB（>64GB，装不下）** |
| C18 | `curl https://api.github.com/repos/ggml-org/llama.cpp/issues/18102`（搜索结果正文） | 80B-A3B 在 llama.cpp 上的真实速度 | 见 §8 |
| C19 | `curl https://api.github.com/repos/ollama/ollama/releases?per_page=20` | ollama 0.40.6 时间 | v0.40.6 发布于 **2026-10-16** → 满足「≥0.14.3」 |
| C20 | `ollama list` / `df -h` | 本机是否已有可用权重 | 只有 qwen3:4b / qwen3:8b；**未下载任何 GLM 权重**（遵守「不下载模型权重」） |

---

## 2. 官方事实（逐条落地）

### 2.1 仓库、许可、参数

`zai-org/GLM-4.7-Flash`（HF，MIT，downloads 1,085,125，likes 1,880，lastMod **2026-01-29**，`model_type = glm4_moe_lite`）。

`config.json` 真值（C3）：

```
architectures = Glm4MoeLiteForCausalLM   hidden_size = 2048     intermediate_size = 10240
num_hidden_layers = 47   n_routed_experts = 64   num_experts_per_tok = 4   n_shared_experts = 1
first_k_dense_replace = 1   moe_intermediate_size = 1536   routed_scaling_factor = 1.8
norm_topk_prob = true   topk_method = noaux_tc
num_attention_heads = 20   num_key_value_heads = 20   partial_rotary_factor = 1.0
q_lora_rank = 768   kv_lora_rank = 512   qk_nope_head_dim = 192   qk_rope_head_dim = 64   v_head_dim = 256
max_position_embeddings = 202752   rope_theta = 1000000   dtype = bfloat16
num_nextn_predict_layers = 1     ← MTP 头（HF 权重里有，官方 GGUF 里没有）
```

**激活参数我按 config 复算 ≈ 3.6–3.9B**（每层：4 个路由专家 4×9.44M + 1 个共享专家 9.44M + MLA 注意力 21.8M ≈ 68.9M，×47 层 ≈ 3.24B + embedding/head 0.63B）——**官方口径「A3B」略低于实际激活量**，这对「与现役同速」的推断有影响（见 §5.3）。

第三方独立佐证：llama.cpp 在 V100 上加载该模型时打印 `print_info: model params = 29.94 B`（issue #18948 日志原文）→ **29.94B 总参**成立。

### 2.2 上下文长度

- `config.json`: `max_position_embeddings = 202752`
- GGUF: `deepseek2.context_length = 202752`，`n_ctx_orig_yarn = 202752`
- ollama tag 页面标 **198K**
- AA 页标 200k

→ 原结论「ctx 200K / ollama tag 198K」**属实**。

### 2.3 量化体积真值

| 来源 | 文件 | 字节 | GB |
|---|---|---|---|
| unsloth/GLM-4.7-Flash-GGUF | GLM-4.7-Flash-Q4_K_M.gguf | 18,312,339,808 | **18.31** |
| unsloth | GLM-4.7-Flash-Q5_K_M.gguf | 21,408,850,272 | 21.41 |
| unsloth | GLM-4.7-Flash-Q8_0.gguf | 31,842,799,968 | 31.84 |
| unsloth | GLM-4.7-Flash-MXFP4_MOE.gguf | 16,968,499,296 | 16.97（**V100 上是死路**） |
| ggml-org（llama.cpp 官方 org） | GLM-4.7-Flash-Q4_K.gguf | 18,244,193,920 | **18.24**（file_type=15 → 实为 Q4_K_M） |
| ggml-org | GLM-4.7-Flash-Q8_0.gguf | 31,842,799,232 | 31.84 |
| ollama tag | q4_K_M blob | 19,019,269,280 | **19.02** |
| ollama tag | q8_0 blob | 31,843,415,200 | 31.84 |
| ngquocvinh（Coder SFT） | GLM-4.7-Flash-Coder-Q4_K_M.gguf | 18,132,722,464 | 18.13 |
| unsloth | GLM-4.7-Flash-REAP-23B-A3B-Q4_K_M.gguf | 14,113,838,816 | 14.11 |
| jacek2024 | GLM-4.7-Flash-MTP-Q8_0.gguf | 33,201,195,456 | 33.20（+ MTP 层） |

→ 原结论「Q4_K_M 18.31GB / ollama 19GB / q8_0 32 / bf16 60」**基本属实**；需要修正两点：① ollama 的 q4_K_M 实际是 **19.02 GB**（不是 18.31），与 unsloth/ggml-org 都不同，来源未明（未在 ollama 仓库找到说明）——**不影响装得下的判断**；② ggml-org 那个文件名写 `Q4_K` 但 file_type=15（Q4_K_M），命名与内容不一致，别当成两种不同量化。

### 2.4 GGUF 架构真值（这一条原结论没写，但很关键）

我下载 ggml-org 的 GGUF 前 40 MB（仅头部，随即删除）用 `gguf` 库解出 47 个 KV：

```
general.architecture = deepseek2          ← 不是 "glm4moe"、也不是 "glm4-moe-lite"
general.name = GLM 4.7 Flash   general.license = mit   general.size_label = 64x2.6B
general.file_type = 15  (Q4_K_M)
deepseek2.block_count = 47      deepseek2.context_length = 202752
deepseek2.embedding_length = 2048   deepseek2.feed_forward_length = 10240
deepseek2.attention.head_count = 20   head_count_kv = 1
deepseek2.attention.q_lora_rank = 768  kv_lora_rank = 512
deepseek2.attention.key_length = 576    value_length = 512
deepseek2.attention.key_length_mla = 256  value_length_mla = 256
deepseek2.expert_count = 64  expert_used_count = 4  expert_shared_count = 1
deepseek2.leading_dense_block_count = 1  expert_feed_forward_length = 1536
deepseek2.expert_weights_scale = 1.8  expert_weights_norm = true
deepseek2.rope.dimension_count = 64   rope.freq_base = 1e6
tokenizer.ggml.pre = glm4    tokenizer.chat_template = [gMASK]<sop>…（见 §4.4）
```

张量名只有 `blk.0 … blk.46`（47 块，**没有 blk.47 = MTP 层**）→ **官方 GGUF 不含 MTP 头**；MTP 版在第三方 `jacek2024/GLM-4.7-Flash-MTP-GGUF`。

**这一点直接推翻「llama.cpp 侧要用专门的 glm4-moe-lite 架构」的说法**：llama.cpp master 的 `src/models/` 目录里**没有** `glm4-moe-lite.cpp`（有 `glm4-moe.cpp` / `glm-dsa.cpp` / `glm5-next.cpp`），PR #25564（作者自建 `src/models/glm4-moe-lite.cpp`）**closed 未合并**；官方走的是 `LLM_ARCH_DEEPSEEK2`（`src/llama-arch.cpp:84`）。而 `src/models/deepseek2.cpp:168` 有 `GGML_ASSERT(hparams.is_mla() && "GLM4 MTP requires MLA")` —— 说明 **MTP 是在 deepseek2 架构内实现的**（PR #24868，**已合并 2026-08-03**，`llama_model_deepseek2::graph_mtp`）。

---

## 3. V100（sm_70）上到底能不能跑

### 3.1 结论

**能跑，唯一可行路是 llama.cpp + GGUF（ollama 内置的 llama.cpp runner 即走这条路）。** 但有三个必须先知道的坑（§3.3）。

### 3.2 引擎与版本

- **llama.cpp 架构支持**：GGUF 标 `deepseek2` → `LLM_ARCH_DEEPSEEK2`（`src/llama-arch.cpp:84`），`src/models/deepseek2.cpp` 实现 MLA + 64 专家 top-4 + 共享专家 + `leading_dense_block_count=1`。**架构支持已 GA**：ggml-org 官方 GGUF 早在 **2026-01-23** 就发布了（下载 29,839），而模型发布是 2026-01-23 前后。
- **sm_70 编译支持**：`ggml/src/ggml-cuda/CMakeLists.txt` 中 `if (CUDAToolkit_VERSION VERSION_LESS "13") list(APPEND CMAKE_CUDA_ARCHITECTURES 50-virtual 61-virtual 70-virtual)` → **CUDA 12.6 默认就编 sm_70 的 PTX**。第三方在 V100 上跑的实测 build 打印 `CUDA : ARCHS = 500,610,700,750,800,860,890`，含 700 ✓。
- **FlashAttention 在 Volta 上有专门分支**：`ggml/src/ggml-cuda/fattn.cu:224` 有 `if (cc == GGML_CUDA_CC_VOLTA) { … }` 的 GQA 优化分支，`common.cuh:285` 定义 `VOLTA_MMA_AVAILABLE`。所以 **FA 在 sm_70 上是支持的**（但 2026-01 前后对 MLA 路径有 bug，见 §3.3）。
- **CUDA graphs 在这个架构上被关掉**：V100 实测日志原文 `ggml_cuda_graph_set_enabled: disabling CUDA graphs due to GPU architecture` → decode 少拿 5–15% 的调度红利。

### 3.3 三个必知坑

**坑 1（最贵）：FA 路径曾把算子甩回 CPU。**
llama.cpp issue **#18948**「Eval bug: CPU usage is abnormally high when using the CUDA backend to infer GLM-4.7-Flash」——**这个 issue 就是在 Tesla V100-SXM2-32GB（CC 7.0）上开的**，`-ngl 99 -fa on -m GLM-4.7-Flash-UD-Q5_K_XL.gguf`。日志显示 48/48 层已 offload 到 CUDA0（`CUDA0 model buffer size = 20383.21 MiB`），但 CPU 占用异常高、prefill/decode 极慢。评论里的自测：
- 「`-fa off` 快约 3 倍」；
- 「RTX 6000 Pro 上 `-fa off` 150–160 TPS，`-fa on` 只有 60」；
- 「RTX 3090 上 Q4_K_M 头几百 token >110 t/s，6000 token 后掉到 ~20 t/s，新会话也恢复不了；单核 CPU 100%」。
→ 修复路径：PR #18953 + 后续 FA 相关 commit（`b70d251076ac7c3ac1cd5d39dbb167f6ff3b6880`），线程最后确认「now working」。
**运维含义：上机必须显式 `-fa off`（或确认所用 llama.cpp 版本已含该修复），否则会看到「GPU 在跑但 CPU 打满」的假象。**

**坑 2：工具调用解析失败（HTTP 500）。**
llama.cpp issue **#20650**（RTX A5000, CC 8.6, llama.cpp 8382, `GLM-4.7-Flash-Q6_K.gguf`）：`Failed to parse input at pos 1225: <tool_call>read_file_diff_md</tool_call>` → agent 循环直接 500。issue 里 Qwen3.5-35B 也有同样问题 ⇒ 这是 **llama-server 对 GLM 系 tool_call 格式的解析健壮性问题**，与我们的 af-bench（每题 ~10 轮工具调用）**直接相关**。目前仍 **open**。

社区补充（HF 讨论 #66）：用 `IQ4_NL` 量化时「tool usage was broken / tool calls were torn apart」，换 MXFP4_MOE 才消失；另一人用 unsloth `UD_Q4_K_XL` + 定制 chat template + `flash-attn on` + `kv-unified` + `cache-type-k/v q4_0` + ngram-mod 投机解码才把工具调用跑顺。
→ **运维含义：量化档位与 chat template 要一起选，不能随手拿 Q4_K_M 就上。**

**坑 3：官方模板自己还有未修 bug。**
llama.cpp issue **#30313**（2026-10-10，master `23b0202a1`，**仍 open**）：`test-chat --template GLM` 跑 `models/templates/GLM-4.7-Flash.jinja` 时断言失败（"throw path should produce std::runtime_error"）。虽然只是测试断言，但它证明**官方模板路径在 2026-10 仍在调整**。

### 3.4 哪些格式在 Volta 上是死路（针对本模型）

| 路线 | V100 可行？ | 依据 |
|---|---|---|
| GGUF Q4_K_M / Q5_K_M（llama.cpp） | ✅ **唯一推荐** | §3.1–3.3 + §5.1 |
| GGUF MXFP4_MOE（unsloth 16.97GB） | ❌ 不推荐 | MXFP4 是 Blackwell(sm_100/sm_120) 特性；Volta 上只能按低精度反量化模拟，无收益 |
| 官方 FP8 量化版（`Geodd/GLM-4.7-Flash-FP8`） | ❌ | HF 讨论 #60 原文自述「optimized for NVIDIA GPU generations: FP8 (**Hopper-class**)」 |
| 官方 W8A16 版（`Geodd/GLM-4.7-Flash-W8A16`） | ❌ 实际不可用 | 标称 Ampere 级；且 vLLM V1 要求 CC≥8.0（我们 CC=7.0），SGLang 快路径要 sm_80+ |
| vLLM / SGLang | ❌ | 官方 README 明说「vLLM and SGLang only support GLM-4.7-Flash on their **main branches**」；V100 被 vLLM V1 移除。且社区反馈 vLLM/SGLang 在该模型上「generates garbage」（HF #43） |
| llama.cpp + `--n-cpu-moe` | ⚠️ 降级 | 存在该开关，但 TG 性能是已知痛点（llama.cpp #20596「ggml-cpu: improve --n-cpu-moe TG performance」**至今 open**） |

### 3.5 显存账（**原结论这里算错了**）

原结论 I3：「MLA 让 GLM-4.7-Flash 的 KV cache 极小 → 198K 上下文在 32GB 卡上可行」——**与实测日志矛盾**。

V100 实测日志原文（C12）：
```
llama_kv_cache: CUDA0 KV buffer size = 399.50 MiB ( 4096 cells, 47 layers, 1/1 seqs),
                K (f16): 211.50 MiB, V (f16): 188.00 MiB
```
→ **K 与 V 都按 f16 存**（K=576 维、V=512 维），合计 **2176 B/token/层 × 47 层 = 99.9 KiB/token**（=102,272 B/token）。

| ctx | KV 显存 | + Q4 权重 19.0GB | + compute/CUDA 缓冲 | 单卡 32GB 装得下？ |
|---|---|---|---|---|
| 8,192（现役 num_ctx） | 0.78 GB | 19.8 | ~21.2 | ✅ 宽裕 |
| 32,768 | 3.13 GB | 22.1 | ~23.5 | ✅ 舒服（**建议档位**） |
| 64,000 | 6.25 GB | 25.3 | ~26.7 | ✅ 勉强 |
| 131,072 | 12.8 GB | 31.8 | ~33.2 | ❌ 超 |
| 202,752 | 19.8 GB | 38.8 | ~40 | ❌ 远超 |

**修正**：单卡 V100 的现实 ctx 上限是 **32K–64K**，不是 198K。要上 128K+ 必须**两卡都放权重 + KV 分片**（llama.cpp `--split-mode layer`/`row`，或 `-ot` 覆盖），而两卡分片对 MoE 模型的专家路由有额外开销（未验证）。**对 af-bench（每题 ~10 轮、日志很长）32K–64K 很可能不够**，这是原结论完全没提的落地风险。

---

## 4. 「思考关不掉」——原结论最关键的一处错误

**原结论**（china-vendors.md 131 行）：「**它是 reasoning 模型，思考关不掉**：HF 讨论 #56 专门问 how to off Reasoning?，社区只能靠 jinja 模板 `{% set enable_thinking = false %}`」，并据此把它列为「最大风险」。

**核查结果：这句话方向反了。**

1. **官方 chat template 自带思考开关。** 我从 GGUF 元数据里解出官方 `tokenizer.chat_template`，以及 llama.cpp master 的 `models/templates/GLM-4.7-Flash.jinja`（3120 B），两者一致：
   - 第 85 行：`{{- '</think>' if (enable_thinking is defined and not enable_thinking) else '<think>' -}}`
   - 第 52 行：`{%- if ((clear_thinking is defined and not clear_thinking) or loop.index0 > ns.last_user_index) and reasoning_content -%}` → `{{ '<think>' + reasoning_content.strip() + '</think>' }}`
   → `enable_thinking=false` **确实能关思考**；`clear_thinking=false` = **Preserved Thinking**（跨轮保留推理内容）。
2. **官方 API 文档明说可以关。** `docs.z.ai/guides/capabilities/thinking-mode` 原文：「Thinking is activated **by default** in … GLM-4.7 series … **If you want to disable thinking, use the following**: `"thinking": { "type": "disabled" }`」（并注明 GLM-5.3/5.3-Flash 才是 forced thinking、不能关）。
3. **官方模型卡反过来建议「多轮 agentic 任务要开 Preserved Thinking」**：`zai-org/GLM-4.7-Flash/README.md` 第 52 行 —— 「For multi-turn agentic tasks (τ²-Bench and Terminal Bench 2), please turn on **Preserved Thinking mode**」。

**对本地臂的实际含义（这才是真正的墙钟杠杆）**：
- 原结论的「思考关不掉 → 输出 token 多 1.5–2 倍 → 墙钟更差」这条推理链**不成立**；思考是**可配置的旋钮**，不是死路。
- 但风险**方向变了**：官方自己说 agentic 题型**应该**开 preserved thinking（否则跨轮丢推理，质量下降）。我们每题 ~10 轮工具调用，**开思考** → token 多、墙钟长；**关思考** → 可能掉质量。这是一个需要实测选点的**权衡**，不是「只能吃满亏」。
- 落地要求：ollama 0.40.6 的 `Modelfile` 侧要在 `PARAMETER`/template 里注入 `enable_thinking` / `clear_thinking`，而不是接受默认；**af-bench harness 的 tool_result 回填必须带上 `reasoning_content`**，否则 preserved thinking 模式会静默退化。

---

## 5. 速度证据核查

### 5.1 唯一与 V100 直接相关的证据（issue #18948）

| 事实 | 值 | 来源 |
|---|---|---|
| 硬件 | **Tesla V100-SXM2-32GB, compute capability 7.0**（AMD R9 7940H + V100-32G-SXM2，Windows） | #18948 body |
| 模型 | GLM-4.7-Flash UD-Q5_K_XL（20.11 GiB, 5.77 BPW, 29.94B params） | #18948 body |
| 启动参数 | `-ngl 99 -fa on -c 4096 --jinja` | #18948 body |
| 结果 | **模型成功加载并出字**（48/48 层 offload 到 CUDA0，`CUDA0 model buffer size = 20383.21 MiB`），但 CPU 占用异常高、prefill/decode 极慢 | #18948 body + 评论 |
| 修复 | PR #18953 + 后续 FA commit `b70d251…`；评论确认「now working」 | #18948 评论 |
| **tok/s** | **无**（该 issue 只报 CPU 占用与速度异常，未给 tok/s） | — |

→ **能跑，且与我们的卡同型同容量**（V100S-32GB）。但**没有任何人公开过 V100 上 GLM-4.7-Flash 的 tok/s**。

### 5.2 第三方 tok/s 实测汇总（按证据强度排序）

| # | 硬件 | 模型/量化 | 设置 | 数字 | 来源 | 强度 |
|---|---|---|---|---|---|---|
| S1 | **RTX 3090 (CC 8.6)** | GLM-4.7-Flash-UD-Q4_K_XL (16.31 GiB) | llama-bench, `-fa 0 -p 2048` | **pp2048 2588.24 t/s；tg128 108.10 t/s**（另一次 2539.03 / 107.04） | #18948 评论 | 第三方实测（修复后） |
| S2 | RTX 3090 | 同上 | `-fa 1 -ctk f16 -ctv f16` | 表被截断，但同帖描述「FA on 修好后仍明显慢于 FA off」 | #18948 评论 | 第三方实测（部分） |
| S3 | RTX 6000 Pro | 同上 | `-fa off` / `-fa on` | **150–160 t/s（FA off）** / 60（FA on，坏版本） | #18948 评论 | 第三方实测（坏版本期） |
| S4 | RTX A5000 (CC 8.6) | GLM-4.7-Flash-Q6_K + `--n-cpu-moe 5` + `-ot ".ffn_(up)_exps.=CPU"` | llama-server, ctx 70144, FA on, ngram-mod | **prompt 2255 t/s；eval 39.90 t/s**（draft 接受率 0.156） | #20650 日志 | 第三方实测（**带 CPU 卸载**） |
| S5 | 硬件**未标注**（从上下文看是 AMD/Vulkan 老卡） | GLM4.7 Flash **Q8_0** vs qwen3moe-30B-A3B Q8_0 | llama-bench build 7822，**FA=off** | GLM: pp512 102.81 / **tg128 10.77**；d1024 tg 7.29；d2048 tg **5.28**；d8096 tg 2.19 | HF 讨论 #47 | 第三方实测（**不可迁移**） |
| S6 | 同上 | 同上 | **FA=on** | GLM: pp512 86.09 / **tg128 10.97**；d1024 tg 9.76；d2048 tg **8.79**；d8096 tg 5.58 | HF 讨论 #47 | 第三方实测 |
| S7 | 硬件**未标注** | GLM-4.7-Flash-MTP-default-Q8_0 | llama.cpp PR #24868 自测 | baseline **111.32 t/s**；MTP 1 **131.12 t/s（1.18×）**；BF16 baseline 65.70 → 89.90（1.37×） | PR #24868 正文 | 作者自测 |
| S8 | Z.AI 托管 API | GLM-4.7-Flash (Reasoning) | AA 托管 | **medianOutputSpeed 85.52 t/s**，TTFA 24.6 s | AA 页面内嵌 JSON | **第三方托管服务测速（非本地）** |
| S9 | GGUF 存在性 | `zai-org/GLM-4.7-Flash` downloads 1,085,125；`unsloth/...-GGUF` 230,934；`ggml-org/...-GGUF` 29,839 | | | HF API | 间接证据 |

**对原结论的三条修正**：

1. **原结论把 S5 当成「社区 llama-bench 显示同档比 Qwen3MoE 慢 17%」并据此推断 V100 速度 —— 三个问题**：
   - ① 该帖**完全没写硬件**（作者还自问「是 llama.cpp 问题、vulkan 后端问题、还是模型架构问题」；回复里另一位 AMD 用户说「vulkan is a joke…如果你卡老只能跑 vulkan，问题就在这」）。**Vulkan+AMD 的数字不能迁移到 CUDA+V100。**
   - ② 测的是 **Q8_0（31.8 GB）**。在小显存卡上 31.8 GB 权重必然大量 CPU 卸载 → 数字被卸载主导。
   - ③ 原结论**只引了 FA=off 行**。同一张表的 FA=on 行：tg128 10.97 vs qwen3moe 13.39（-18%）、d1024 9.76 vs 12.29（-21%）、d2048 **8.79 vs 11.66（-25%）**、d8096 **5.58 vs 8.92（-37%）**。「深度 2K 掉到 1/2」是 FA=off 的极端值（5.28 vs 11.23 = -53%），**开 FA 后是 -25%，不是 -53%**。原结论把最坏情况当成了常态。
2. **原结论的推断 I1「V100 上 decode 约 80–120 tok/s」** —— 应改为：**无实测，只能按同代 3090（108 t/s @ Q4_K_XL）外推到 70–110 t/s**。V100S-32GB 带宽（900 GB/s PCIe）与 3090（936 GB/s）相当，但算力更弱、且 llama.cpp 在该架构**禁用 CUDA graphs** → **合理预期 80–110 tok/s，很可能低于现役 qwen3-coder-30b 的 135.7 tok/s**。**原结论把它当作「与现役同速」的前提，这个前提没有证据支撑。**
3. **AA 的 85.5 tok/s 不能拿来和我们的 135.7 tok/s 比。** AA 的 `medianOutputSpeed = 85.518` 测的是 **Z.AI 托管 API** 的服务端吞吐（含排队/批处理/网络），不是本地解码速度。原结论把两者并置比较是**口径错误**。

### 5.3 物理层面的速度推断（自算，供 anolis 实测验收用）

按 config 复算激活权重（Q4_K_M ≈ 4.8–5.0 bit/权重）：激活 ≈ 3.24B（专家+注意力）+ 0.63B（embedding/head）≈ **3.9B 参数 → 每 token 读 ≈ 2.3 GB**。V100S-32GB 带宽 900 GB/s → 理论上限 ≈ **390 tok/s**；llama.cpp 在 MoE 上的实际效率通常 30–50% → **~120–195 tok/s** 区间的中位偏低值（与 S1 的 3090 实测 108 t/s 一致，因为 3090 上跑的是 16.31 GiB 的 Q4_K_XL）。
现役 qwen3-coder-30b（30.5B/3.3B 激活，18.5 GB）实测 135.7 tok/s —— **两者激活量几乎相同，GLM-4.7-Flash 在 V100 上不应更快**。原结论「同 30B-A3B 档 → 在 V100 上和现役同速」这个推理可以成立（但只是同速，不是更快），而原结论进一步把它当成「换上去不亏」的前提，则需要实测支撑。

---

## 6. 质量证据核查

### 6.1 官方自报（**全部是厂商自报，无第三方复现**）

`zai-org/GLM-4.7-Flash/README.md` 与 ollama 卡片表格（两处一致）：

| Benchmark | GLM-4.7-Flash | Qwen3-30B-A3B-Thinking-2507 | GPT-OSS-20B |
|---|---|---|---|
| AIME 25 | 91.6 | 85.0 | 91.7 |
| GPQA | 75.2 | 73.4 | 71.5 |
| LCB v6 | 64.0 | 66.0 | 61.0 |
| HLE | 14.4 | 9.8 | 10.9 |
| **SWE-bench Verified** | **59.2** | 22.0 | 34.0 |
| **τ²-Bench** | **79.5** | 49.0 | 47.7 |
| BrowseComp | 42.8 | 2.29 | 28.3 |

评测参数（官方原文）：SWE-V / Terminal Bench 用 `temperature 0.7, top_p 1.0, max_new_tokens 16384`；τ²-Bench 用 `temperature 0, max_new_tokens 16384`；默认档 `max new tokens: 131072`。
→ **数字属实**（原结论引用无误）。**注意：对比栏里的基线是 "Qwen3-30B-A3B-Thinking-2507"，不是我们现役的 "Qwen3-Coder-30B-A3B-Instruct"** —— 原结论把 59.2 > 51.6（现役）与官方表直接并列，容易让人误以为是同口径对比。**59.2 vs 51.6 是两个厂商、两套 harness、两套 prompt 的数字，不可直接相减。**（现役 51.6 来自本工作区前期档案 `设计/benchmark调研/实测/model-pricing.md`；本轮**未能**从 Qwen 模型卡/博客独立复核该数字——Qwen 模型卡正文里没有 SWE 数字，博客页是 JS 渲染没抓到。）

### 6.2 第三方：Artificial Analysis

抓取 `https://artificialanalysis.ai/models/glm-4-7-flash`（1.68 MB HTML，内嵌 JSON）：

```
intelligenceIndex = 14.8719733920138   → 页面显示 15
intelligenceIndexIsEstimated = true            ← 关键：指数是「估计值」，AA 未跑独立评测
microevalsEnabled = false
contextWindowTokens = 200000    sizeClass = small    reasoning = yes
price1mInputTokens = 0.07   price1mOutputTokens = 0.40
medianOutputSpeed = 85.5183462997776   medianTimeToFirstAnswerToken = 24.60
omniscienceAccuracy = 0.1615   omniscienceHallucinationRate = 0.939
terminalbenchHard = 0.21969696969697      ← 对我们最有参考价值的第三方 agentic 数
tau2 = 0.988304093567251
lcr = 0.416666666666667      hle = 0.0759962928637627      critpt = 0.00285714285714286
gdpval = null   scicode = null   terminalBench21 = null   terminalBench40 = null
```

- 页面顶部横幅：「This model is deprecated. … Z AI has launched a newer release, GLM-5.」
- 页面说明：「AA Intelligence Index v4.3.2 incorporates 10 evaluations: … Terminal-Bench 4.0, SciCode, … 」「Estimate (**independent evaluation forthcoming**)」
- 智谱官方在 HF 讨论 **#49** 回应 AA-LCR 偏低：「the provider Artificial Analysis used for the benchmark isn't the official one … In our internal local testing, an AA-LCR score of around **45** is considered a reasonable and expected value.」→ AA 的 LCR 41.7% 与智谱内部 ~45 基本吻合，**说明 AA 的部署对该模型是有偏的**。

**判定**：
- AA 的 **Index 15 不可当作第三方复现**（`intelligenceIndexIsEstimated = true`）。原结论虽已注明「Estimated」，但仍在正文把它与「官方 SWE-V 59.2」并列当作「官方 agentic 分高于现役」的支撑 —— **应降级为「厂商/AA 估计值」**。
- 可用的第三方 agentic 数只有 **Terminal-Bench Hard 21.97%**（AA 自测，托管 API 权重）—— 我们的 af-bench 里有 Terminal-Bench，**这个数比 SWE-V 59.2 更有参考价值**，但口径是 TB-Hard 而非 TB2.0。
- AA 的 `tau2 = 98.83%` 与官方 τ²-Bench 79.5 差异极大（harness 不同 + AA 用的是托管 API），**不能拿来互证**。

### 6.3 第三方：SWE-rebench 榜单

`swe-rebench.com`（HTML 解析，118 行表格）：

```
ROW: 52 Z.ai GLM-4.7       Model N/A N/A N/A N/A
ROW: 53 Z.ai GLM-4.7 Flash Model N/A N/A N/A N/A
ROW: 54 Z.ai GLM-5         Model N/A N/A N/A N/A
ROW:111 Qwen Qwen3-Coder-30B-A3B-Instruct Model N/A N/A N/A N/A
ROW:113 Qwen Qwen3-Coder-Next Model N/A N/A N/A N/A
```
（榜单有 "GLM-4.7 Flash (tools)"、"GLM-4.7 Flash, gpt-5.2-codex, GLM-4.7 Flash" 等 agent 组合条目，但 **model-only 一列对 GLM-4.7 Flash 是 N/A**。）

→ **GLM-4.7-Flash 在 SWE-rebench 上"上榜了但没有 model-only 成绩"**；Qwen3-Coder-30B-A3B-Instruct 与 Qwen3-Coder-Next 同样是 N/A。**这说明 SWE-rebench 榜单本身对本地权重模型覆盖很差**，不能作为本地臂选型的区分依据。原结论没提这一点。

### 6.4 第三方复现的总结论

| 分项 | 有无第三方独立复现 | 证据 |
|---|---|---|
| SWE-bench Verified 59.2 | ❌ **无** | HF #69 只是把官方结果挂到 Hub 的 eval-results 特性（作者是 HF 员工 nielsr，非独立复现）；swe-rebench model 列 N/A |
| τ²-Bench 79.5 | ❌ 无（AA 有个不同 harness 的 98.8%，不可互证） | AA 内嵌 JSON |
| Terminal-Bench | ⚠️ 官方表里**没有** Flash 档的 TB2 数字（原结论已指出 ✓）；AA 给了 TB-Hard 21.97% | AA 内嵌 JSON |
| InjecAgent 类 | ❌ 无 | — |
| 工具调用质量 | ⚠️ 只有**社区轶事**：#53「exceptional tool use handling in various typescript cli coders」（正面）；#66「IQ4_NL 下 tool usage broken / tool calls torn apart」（负面）；#20650 llama-server 解析 500（负面）；#75「破坏转义 `\n`、误删邻近代码」（负面） | HF 讨论 + llama.cpp issue |
| 稳定性负面 | #48 无限重复（其中一例是 vLLM H200 + **FP8 KV + FlashMLA** 组合下必现，与我们无关）；另一例是 ollama+open-webui 用户报告 | HF #48 |

**判定**：原结论「证据强度：官方自报为主、第三方复现薄弱」**属实且应加强**：本轮核查后可以更明确地说 —— **GLM-4.7-Flash 的 agentic 分数目前 0 第三方独立复现；唯一可用的第三方 agentic 数是 AA 的 Terminal-Bench Hard 21.97%。**

---

## 7. 另两个复核对象

### 7.1 GLM-4.7-Flash-Coder（whitecircle 社区 SFT）

- 仓库：`whitecircle/GLM-4.7-Flash-Coder`，MIT，base = `zai-org/GLM-4.7-Flash`，downloads **19,497**，lastMod **2026-09-12**，`library_name: transformers`。
- **无官方 GGUF**；社区量化 `ngquocvinh/GLM-4.7-Flash-Coder-GGUF`（downloads 5,193），**Q4_K_M = 18,132,722,464 B = 18.13 GB**（原结论 ✓ 属实）。该仓库还有 IQ1_M 6.89 / IQ3_M 13.24 / IQ4_XS 16.20 / Q6_K 24.61 / Q8_0 31.84 等档。
- 自测数字（作者 README 原文）：SWE-rebench-V2 pass@1 **0.3315 → 0.4165**（+26% 相对）；**assistant turns 82.5 → 44（-45%）**；**cost/task $0.0443 → $0.0382（-14%）**；「median reasoning tokens per response **63 vs 150**」；并行工具调用占比（2+ read 1.6%→9.7%、2+ bash 0.6%→7.2%、2+ edit 增长约 90×）；训练 16×B300、3 小时、context 75k。
- **口径提醒**：
  - 这是 **SWE-rebench-V2**（nebius 32k 题库，评测只用了 500 道 Python 题），**不是 SWE-bench Verified**，两者不能互比（原结论已正确指出 ✓）。
  - base 0.3315 也是**作者自己**在同 harness 上跑的 → 是**作者自控 A/B**，不是独立复现。
  - 训练/评测**只在 PI harness（bash/read/edit/write 四个工具）**上；我们 af-bench 的工具集不同 → 迁移未验证（原结论已指出 ✓）。
  - 「-45% 轮数」是**墙钟的直接杠杆**，但同时「reasoning token 63 → 150（2.4×）」→ **token 总量未必降**，净墙钟收益需要实测（原结论把它当收益，没提这个反向项 —— **需修正**）。
- 与我们 harness 的匹配度风险：官方 chat template 的工具格式是 `<tool_call>{name}<arg_key>…<arg_value>…</tool_call>`（我从 GGUF 元数据里解出的官方模板原文），而 whitecircle 是在 PI harness 上训的；**PI 的工具名/入参 schema 与我们 af-bench 不同** → 即便权重装上，也必须用我们自己的 tool schema 复测，否则 41.65% 不可迁移。

### 7.2 Ling-3.0-flash-REAP288-71B-A5B（社区压缩探针）

- **仓库名与文件名不一致**：`bloomer010/Ling-3.0-flash-REAP288-**73B**-A5B-GGUF`（仓库名 73B），但里面文件名全是 `Ling-3.0-flash-REAP288-**71B**-A5B-*.gguf`。原结论写「71B-A5B、44.29GB」与**文件名**一致 ✓，但**仓库名**是 73B —— 引用时要注意。
- 该仓库**只有 4 个量化**：`MXFP4 40.98 GB` / `Q2_K 26.83 GB` / `Q3_K_M 34.99 GB` / **`Q4_K_M 44,288,474,560 B = 44.29 GB`**（原结论的 44.29 ✓ 属实）。下载量 1,065（很小）。
- 同族还有 `bloomer010/Ling-3.0-flash-GGUF`（**没有** REAP 版）：Q4_K_M **78.29 GB**、UD-Q4_K_XL 84.72 GB、Q8_0 135.62 GB、IQ1_S 26.69 GB、Q1_0 19.47 GB。
- **V100 判定**：
  - MXFP4 **在 V100 上是死路**（Blackwell 特性），REAP288 的 MXFP4 40.98 GB 这一档**在 V100 上没有意义**；
  - Q4_K_M 44.29 GB **能塞进 2×V100S-64GB 合计显存**，但要给 KV/计算缓冲留 ~19 GB → **ctx 被压到 ~60K 以内**（按 §3.5 的 99.9 KiB/token 量级估，Q4_K_M 44.29GB + KV 6GB + compute ≈ 51GB，余 13GB）；
  - 5B 激活（vs GLM-4.7-Flash 的 3.9B）→ 每 token 多读约 30% 权重；
  - 质量是 **REAP 有损压缩**的结果，无官方分数背书；
  - **结论：原结论把它列为「唯一另装得下且更强的」（AA Index 20 vs 15）——这个"更强"的依据同样只是 AA 的估计分（AA 页面同样把这类模型标为 Estimated），且 A5B 的解码在 V100 上不占优。不构成比 GLM-4.7-Flash 更好的选择。**

---

## 8. 对本次核心假设的判定：「总参很大、激活很少的 MoE 在 V100 上会更快」

**判定：对 30B-A3B 档成立（且只到"同速"），对 80B 级不成立（反而慢 2.5–3 倍）。**

证据：
1. **同档对照（同代、同卡、修复后）**：GLM-4.7-Flash（30B-A3B）Q4_K_XL 在 RTX 3090 上 tg128 = **108.10 t/s**（#18948 评论，llama-bench）。
2. **80B-A3B 对照**：llama.cpp issue **#18102**「ggml-cuda: Delta-Net linear attention for Qwen3-Next」作者自测数据（**至今 open**）：「getting ~**45-55 t/s** on q4/mxfp4 and ~40 t/s bf16 on 80B-A3B (blackwell). **pre-blackwell cards get ~38-40 t/s** from solve_tri improvements (baseline was the original ~20 t/s)」→ 80B-A3B q4 在 8.x/9.x 级卡上就是 **~38–40 t/s**，比 30B-A3B 的 108 t/s **慢约 2.5–3×**。
3. **物理原因**（与"只读激活权重"的朴素直觉相反）：
   - 总参越大 → 单个专家矩阵越小（Qwen3-Coder-Next：512 个专家 × moe_intermediate 512，**每专家是一次极小的 GEMV**），GPU 利用率低、kernel launch 与 gather/scatter 开销占比飙升；
   - 路由本身要算 512 路 gate，`ffn_gate_inp` + 专家 gather/scatter 每层都是额外开销；
   - 权重大（45GB）→ 64GB 里要给 KV 挤 ~19GB → ctx 砍半 → **长上下文场景（我们每题 10 轮）反而更吃亏**；
   - MoE 权重的**访存模式是随机的**（每 token 命中不同专家）→ 带宽利用率低于稠密模型的顺序读取。
4. **「80B 级 MoE 的 Q4 约 45GB，双卡 64GB 能否放下」——能放下，但代价明确**：
   - Qwen3-Coder-Next 真值（C17）：**IQ4_NL = 45.13 GB ✓「约 45GB」属实**；Q4_1 分片合计 50.05 GB；Q5_K_M 56.86 GB；**Q6_K = 65.61 GB（>64GB，装不下）**。
   - 装下 45 GB 之后：留给 KV+计算 ≈ 19 GB → ctx 只有 ~50–60K，且速度只有 ~40 t/s 量级（#18102）→ **单题墙钟会是现役的 3 倍以上**。
   - **更硬的反对理由（不是体积，是正确性）**：Qwen3-Coder-Next 是 `qwen3_next` 混合线性注意力架构，llama.cpp 的 CUDA 侧**至今没有专门的 Delta-Net kernel**（#18102 open）、有「Qwen 3 Next CUDA poor performance」（#17822 open）、以及**输出乱码报告**（#27727，ROCm 下 gibberish，Vulkan 正确但慢 20%）→ 与我们已知的「Qwen3.8 混合线性注意力在 llama.cpp 上输出损坏」是**同一类风险**，且已被第三方复现到 llama.cpp issue 里。
   - → **前期结论「本地最强可行选项是 Qwen3-Coder-Next（80B A3B，Q4 量化双卡 64GB 容纳，自报 SWE-V 70.6%）」只对了「权重装得下」这一件事**；对「能跑对」「跑得快」「值得上」三条都不成立。本轮应把它降级。

---

## 9. 需要修正的原结论（逐条）

| # | 原结论原文（china-vendors.md） | 复核判定 | 修正 |
|---|---|---|---|
| C1 | 「它是 reasoning 模型且**思考关不掉**」（131 行，列为最大风险） | ❌ **错** | 官方 chat template 自带 `enable_thinking` 开关（GGUF 元数据 + llama.cpp 官方模板第 85 行实证）；官方文档明说 GLM-4.7 series 可 `"thinking":{"type":"disabled"}`；模型卡反而说**多轮 agentic 任务应开 Preserved Thinking**（`clear_thinking=false`）。→ 风险应改写为「思考是旋钮，开了省质量/关掉省时间，**必须实测选点**」 |
| C2 | I3「MLA 让 KV cache 极小 → 198K 上下文在 32GB 卡上可行」 | ❌ **错** | V100 实测：llama.cpp 存 K(f16,576)+V(f16,512) × 47 层 = **99.9 KiB/token**；198K → ~19.8 GB KV。**单卡现实上限 32K–64K** |
| C3 | 「社区 llama-bench 显示同档比 Qwen3MoE 慢 17%，且上下文到 2K 深度时 decode 掉到 1/2」 | ⚠️ **需限定** | 该帖**无硬件信息**、AMD/Vulkan、Q8_0；原结论只引 FA=off 行，**FA=on 时 d2048 是 8.79 vs 11.66（-25%），d8096 5.58 vs 8.92**，不是 -53% |
| C4 | I1「在 V100 上 decode 约 80–120 tok/s」（中置信） | ⚠️ **应下调并标注为推断** | 无任何 V100 tok/s 实测；同代 3090 修好后 tg128 = 108.10 t/s；V100 禁 CUDA graphs → 预期 **70–110 t/s，很可能慢于现役 135.7** |
| C5 | 「AA 85.5 tok/s（现役 Qwen3-Coder-30B-A3B 158.2 tok/s）」并列比较 | ❌ **口径错误** | AA 测的是**托管 API** 吞吐（`medianOutputSpeed=85.52`，TTFA 24.6s），不能与本地 decode 速度并列；且 AA 的 **Index 15 是 `intelligenceIndexIsEstimated=true`（估计值）**，不能当「第三方复现的 agentic 分」 |
| C6 | 「官方 SWE-V 59.2 > 现役 51.6」 | ⚠️ **口径需澄清** | 59.2 来自智谱官方表，其对比栏基线是 **Qwen3-30B-A3B-Thinking-2507（22.0）**，**不是**现役 Qwen3-Coder-30B-A3B-Instruct（51.6，来自本工作区前期档案，本轮未独立复核）。两套 harness 不可直接相减 |
| C7 | 「唯一同时满足…官方 agentic 分高于现役」 | ⚠️ **证据不足** | 官方分零第三方复现；swe-rebench 上 GLM-4.7 Flash 的 model 列 **N/A**；唯一可用的第三方 agentic 数是 AA 的 **Terminal-Bench Hard 21.97%** |
| C8 | 「ollama tag 19GB / q8_0 32GB / bf16 60GB，均 198K，2.1M 下载，4 months ago；需 ≥0.14.3」 | ✅ 属实，但数字微调 | 真实 blob：**q4_K_M = 19,019,269,280 B = 19.02 GB**、q8_0 = 31.84 GB；ollama 0.40.6 发布于 2026-10-16，满足要求 ✓ |
| C9 | 「GLM-4.7 大版已于 2026-07-15 在 ollama 下架」 | ✅ **属实（已逐字核实）** | ollama 页面原文：「glm-4.7 was retired on July 15, 2026. No models have been pushed.」 |
| C10 | 「必须同时量每题输出 token 与墙钟，因为它是 reasoning 模型」 | ⚠️ **理由错、动作对** | 理由不是「关不掉思考」，而是「思考开/关是配置项，需要同时量两种设置下的 token 数与墙钟」 |
| C11 | （未提及） | ➕ **补漏 1** | **V100 上有真跑案例**（llama.cpp #18948，Tesla V100-SXM2-32GB，CC 7.0），并暴露了「FA 路径把算子甩回 CPU」的严重坑（`-fa off` 快 3×），这条原结论完全没提 |
| C12 | （未提及） | ➕ **补漏 2** | **工具调用在 llama.cpp 侧有已复现的失败模式**（#20650 HTTP 500 解析 `<tool_call>`；HF #66 IQ4_NL 下 tool call 撕裂；#75 破坏转义字符）——对我们「每题 10 轮工具调用」的题型是**首要风险**，原结论只列了 #48/#75 |
| C13 | （未提及） | ➕ **补漏 3** | **MTP 投机解码已合并进 llama.cpp**（PR #24868, 2026-08-03，`llama_model_deepseek2::graph_mtp`），实测平均 **1.18×**（Q8_0）；官方 GGUF **不含** MTP 层，MTP 版在 `jacek2024/GLM-4.7-Flash-MTP-GGUF` |
| C14 | （未提及） | ➕ **补漏 4** | llama.cpp 已内置官方模板 `models/templates/GLM-4.7-Flash.jinja`；但其 test 有 **open bug（#30313, 2026-10-10）** |
| C15 | （关于 Ling） | ⚠️ 微调 | 仓库名是 `...REAP288-**73B**-A5B-GGUF`（文件名才是 71B）；44.29 GB ✓ 属实；该仓库**只有 4 个量化**（MXFP4 在 V100 上是死路） |
| C16 | （关于 80B） | ❌ **需推翻（针对 Qwen3-Coder-Next）** | 前期结论「Qwen3-Coder-Next 80B-A3B，Q4 量化双卡 64GB 容纳」只对**装得下**成立：IQ4_NL 45.13 GB ✓、但 Q6_K 65.61 GB 就装不下；且 llama.cpp 对其混合线性注意力**至今无 CUDA 专用 kernel**（#18102/#17822 open）、有**输出乱码**复现（#27727）；速度只有 ~38–40 t/s（8.x/9.x 卡），**不是更值得上** |

---

## 10. 未能核实清单（本轮明确查不到，不做推测）

1. **GLM-4.7-Flash 在 V100 上的 tok/s 实测** —— 无（主机 `anolis-gpu-01` DNS 解析失败；本会话主机是 RTX 3070 Laptop 8GB，且不下载权重）。
2. **官方 SWE-bench Verified 59.2 的第三方独立复现** —— 无（swe-rebench model 列 N/A；HF #69 是官方结果的挂载）。
3. **GLM-4.7-Flash 的 Terminal-Bench 2.0 官方分数** —— 官方表里没有；只有 AA 的 TB-Hard 21.97%。
4. **InjecAgent / 提示注入类成绩** —— 无任何公开数据。
5. **HF 讨论 #47 那张 llama-bench 表的硬件** —— 原帖未写，无法补。
6. **ollama 官方 q4_K_M blob 19.02 GB 与 unsloth 18.31 GB 的差异原因** —— 未在 ollama 仓库找到说明。
7. **现役 Qwen3-Coder-30B-A3B-Instruct 的 SWE-V 51.6** —— 本轮未从 Qwen 模型卡/博客独立复核（沿用本工作区前期档案）。

---

## 11. 建议的下一步（如果决定做 af-bench A/B）

按「先便宜后贵」排序，且**每一步都必须在 anolis 上实测**（本轮所有 V100 数字都是推断）：

**Step 0（零成本，先做）**：在 anolis 上装 ollama 0.40.6 已有的 runner 版本，确认 `llama-bench` 不可用时用 `ollama run` 的 `load_duration` / `eval_count` 反算。
**Step 1**：拉 `glm-4.7-flash:q4_K_M`（19.02 GB，单卡可放），**先 `num_ctx 32768`**（KV 3.1 GB），测 decode tok/s、prompt tok/s、加载时间，与现役同口径对比（现役：135.7 / 149.1 / 10.5 s @ num_ctx 8192）。**必须同时用 `-fa off` 与 `-fa on` 各测一遍**（V100 上 FA 历史上会把算子甩回 CPU）。
**Step 2（必须做的对照实验）**：思考开关三档 —— ① `enable_thinking` 默认（开）② `enable_thinking=false`（关）③ `clear_thinking=false`（Preserved Thinking，官方推荐给 agentic 题型）。每档量：**每题输出 token 数、每题墙钟、工具调用解析失败率**。
**Step 3**：工具调用健壮性冒烟（先于任何 benchmark）：用我们 af-bench 真实的 tool schema 跑 20 轮对话，检查：① `<tool_call>` 是否被正确解析 ② 是否有转义字符/误删代码（HF #75）③ 是否有重复循环（#48）④ 跨轮是否丢上下文。
**Step 4**：再考虑 `whitecircle/GLM-4.7-Flash-Coder`（18.13 GB）作为**第二轮**对照 —— 但注意其分数是 SWE-rebench-V2 + PI harness，不可直接迁移；且它 reasoning token 反而更多（63→150 median）。
**Step 5（如果做 MTP）**：需另拉 `jacek2024/GLM-4.7-Flash-MTP-GGUF`（Q8_0 33.2 GB，双卡放不下，Q4 档没有）→ 在我们 32GB 单卡上性价比存疑，**优先级低**。
**回退线**：任何一步出现「工具调用解析失败 > 1%」「墙钟 > 现役 1.3×」「输出损坏」，立即回退现役 `qwen3-coder-30b`。

**验收阈值建议**（与原结论一致，只是把「同速」改成「不慢于 85%」）：解码 ≥ 115 tok/s（现役的 85%）、每题输出 token ≤ 现役 1.2×、af-bench 解题率 ≥ 现役 + 3pt。

---

## 12. 引用清单（本轮实际读到的原始出处）

- HF API/原始文件（经 hf-mirror.com）：`zai-org/GLM-4.7-Flash`（api/models、config.json、README.md）、`zai-org/GLM-4.7-Flash/discussions/{25,29,41,43,46,47,48,49,53,56,60,62,66,69,71,75}`、`ggml-org/GLM-4.7-Flash-GGUF`（api + tree + README）、`unsloth/GLM-4.7-Flash-GGUF`（tree）、`ngquocvinh/GLM-4.7-Flash-Coder-GGUF`（tree）、`whitecircle/GLM-4.7-Flash-Coder`（api + README）、`bloomer010/Ling-3.0-flash-REAP288-73B-A5B-GGUF`（tree）、`bloomer010/Ling-3.0-flash-GGUF`（tree）、`jacek2024/GLM-4.7-Flash-MTP-GGUF`（tree）、`unsloth/Qwen3-Coder-Next-GGUF`（tree）、`Qwen/Qwen3-Coder-Next/config.json`
- ollama：`ollama.com/library/glm-4.7-flash`（+ /tags）、`ollama.com/library/glm-4.7`、`registry.ollama.ai/v2/library/glm-4.7-flash/manifests/{q4_K_M,q8_0}`
- 智谱文档：`docs.z.ai/guides/capabilities/thinking-mode`（原文含「Thinking is activated by default … GLM-4.7 series … `"thinking": { "type": "disabled" }`」）
- llama.cpp 源码（raw.githubusercontent.com/ggml-org/llama.cpp/master）：`src/llama-arch.cpp`（:84 DEEPSEEK2）、`src/models/deepseek2.cpp`（:168 GLM4 MTP assert）、`src/models/models.h`（无 glm4-moe-lite）、`ggml/src/ggml-cuda/fattn.cu`（:224 Volta 分支）、`ggml/src/ggml-cuda/common.cuh`（:285 VOLTA_MMA_AVAILABLE）、`ggml/src/ggml-cuda/CMakeLists.txt`（70-virtual）、`models/templates/GLM-4.7-Flash.jinja`（:85 enable_thinking）
- llama.cpp issues/PR：`#18948`（**V100-SXM2-32GB 实测 + 3090 修好后 tg128=108.10 t/s**）、`#20650`（A5000 上 39.90 t/s + 工具调用 500）、`#18102`（80B-A3B 38–55 t/s）、`#17822`、`#27727`（Qwen3-Next 乱码）、`#24868`（MTP 1.18×，**已合并**）、`#25564`（glm4-moe-lite 独立架构，**未合并**）、`#30313`（官方 GLM 模板 test bug，open）
- 第三方聚合：`artificialanalysis.ai/models/glm-4-7-flash`（内嵌 JSON：index 14.87/estimated、TB-Hard 21.97%、tau2 98.83%、lcr 41.67%、85.52 t/s）、`swe-rebench.com`（GLM-4.7 Flash model 列 N/A）
- 前期档案（引自，非本轮实测）：`调研/本地模型选型/notes/china-vendors.md`、`设计/benchmark调研/实测/model-pricing.md`（现役 SWE-V 51.6）
