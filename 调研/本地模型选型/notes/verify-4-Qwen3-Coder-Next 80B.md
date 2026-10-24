# 复核档案 #4：Qwen3-Coder-Next 80B-A3B（复核对象：UD-Q3_K_XL / UD-Q4_K_XL）

> 复核日期：2026-10-21
> 复核对象：Qwen3-Coder-Next 80B-A3B（架构 `qwen3next`）
> 被复核的原结论：`调研/本地模型选型/notes/quant-ecosystem.md`（第 306/319-332/400/411 行等）
> 复核机器：**不是 anolis-gpu-01**。本会话机 = `PanDeveopComp`，`nvidia-smi` 仅 1× RTX 3070 Laptop 8GB、`ollama 0.35.1`、14GB 内存。**本轮所有 V100 数字都不是本轮实测**，全部来自一手源码 / GGUF 文件头 / 第三方 issue 记录。

---

## 0. 复核结论速览

| # | 原结论的断言 | 复核结果 | 证据强度 |
|---|---|---|---|
| 1 | 官方仓库存在，80B-A3B，激活 ~2.1B，ctx 262144，Apache-2.0 | **部分正确，需修正「激活 2.1B」** | 官方一手（config.json + README） |
| 2 | GGUF 生态齐备，UD-Q3_K_XL 36.28GB / UD-Q4_K_XL 49.61GB | **正确**，且本轮直接用 HTTP Range 拉 GGUF 文件头逐张量验证 | 一手（GGUF 二进制头） |
| 3 | **「激活 2.1B ⇒ 每 token 读 ~1.3GB ⇒ decode 不应慢于现役 30B-A3B」** | **❌ 错。实测每 token 读 2.90GB（Q3_K_XL）/ 3.23GB（Q4_K_XL），是现役 30B-A3B（1.92GB）的 1.5–1.7 倍。decode 必然慢于现役，不是「同量级」** | 一手（GGUF 张量表逐张量求和） |
| 4 | 「80–150 tok/s（推断）」 | **❌ 区间需下修到 45–90 tok/s**，且推断链条本身有错 | 推断（已重算）+ 第三方实测换卡佐证 |
| 5 | **Qwen3-Coder-Next 架构比 qwen3_5 老，sm_70 风险面小** | **❌ 错。两者共用同一个 `llm_build_delta_net_base` 与同一套 GDN CUDA kernel，sm_70 风险面同样大** | 一手（llama.cpp 源码） |
| 6 | 45GB Q4 双卡 64GB 装不下 → 需 `--n-cpu-moe` | **部分正确但结论方向错**：Q3_K_XL 33.75GiB 双卡 layer-split 后**每卡只占 16.5GiB，余 15.3GiB**，根本不需要 CPU 卸载。真正的问题不是「装不下」而是「每 token 读的字节太多」 | 一手（GGUF 逐层字节分布） |
| 7 | 官方 SWE-V 70.6 / TB2.0 36.2 / Aider 66.2 | **数字正确**，但**全部是作者自报**（官方 benchmark 图 + Unsloth 文档转引同一张表），**无第三方独立复现 agentic 分数** | 官方一手 + 第三方（仅量化档对比） |
| 8 | 「Qwen3.8-27B 只适合做离线参照」 | **维持**（且比原文理由更强：它与 Qwen3-Coder-Next 共用 GDN kernel） | 一手 |
| 9 | 「ollama 没有暴露关闭 CUDA graphs 的开关，#29255 无法规避」 | **❌ 前提错误**。`llm/llama_server.go:476` 是 `cmd.Env = os.Environ()`，子进程**完整继承父环境**，`GGML_CUDA_DISABLE_GRAPHS=1` 可直接透传 | 一手源码 |

**总判定：修正（不是确认）。** 原结论把这个模型列为 P1「首选、decode 不牺牲、80–150 tok/s」，三项核心卖点里有两项（速度不牺牲、sm_70 风险小）经一手证据检验为假。它仍可能是**能力最强**的本地候选，但在我们这套 2×V100S 上**不可能比现役 30B-A3B 快**，而我们的工作负载里「单题墙钟时间同样重要」。

---

## 1. 模型真实状态核查

### 1.1 官方仓库与元数据（一手确认）

ModelScope API：`https://www.modelscope.cn/api/v1/models/Qwen/Qwen3-Coder-Next`

```
Name = Qwen3-Coder-Next
License = apache-2.0
Architectures = ['Qwen3NextForCausalLM']
Downloads = 49381          (ModelScope 镜像口径)
CreatedTime = 1769782698  → 2026-01-30
```

官方 `config.json`（`https://www.modelscope.cn/models/Qwen/Qwen3-Coder-Next/resolve/master/config.json`）关键字段：

```json
"architectures": ["Qwen3NextForCausalLM"],
"model_type": "qwen3_next",
"num_hidden_layers": 48,  "full_attention_interval": 4,
"hidden_size": 2048,  "num_attention_heads": 16,  "num_key_value_heads": 2,
"head_dim": 256,  "partial_rotary_factor": 0.25,
"num_experts": 512,  "num_experts_per_tok": 10,
"moe_intermediate_size": 512,  "shared_expert_intermediate_size": 512,
"linear_num_key_heads": 16, "linear_key_head_dim": 128,
"linear_num_value_heads": 32, "linear_value_head_dim": 128,
"linear_conv_kernel_dim": 4,
"max_position_embeddings": 262144,
"torch_dtype": "bfloat16"
```

→ **48 层 = 12 全注意力 + 36 GDN**（`full_attention_interval=4`），**512 专家 top-10**，与原结论一致。

官方 README（`.../resolve/master/README.md`）明确写：

> - Number of Parameters: 80B in total and **3B activated**
> - Number of Parameters (Non-Embedding): 79B
> - Hybrid Layout: 12 \* (3 \* (Gated DeltaNet -> MoE) -> 1 \* (Gated Attention -> MoE))
> - Context Length: 262,144 natively
> - **This model supports only non-thinking mode** and does not generate `<think></think>` blocks
> - 推荐采样：`temperature=1.0, top_p=0.95, top_k=40`
> - 部署要求：`sglang>=v0.5.8` / `vllm>=v0.15.0`（**两者都不支持 V100**，见 §3）

**修正 1：激活参数不是 2.1B，是 3B。**
原结论（`quant-ecosystem.md:306`）写「激活 ~2.1B」，并在 `:329` 给出手算：
> `48 层 × (10 专家 × 3 × 512 × 2048) ≈ 1.51B + 共享专家 0.15B + 注意力/嵌入 0.45B ≈ ~2.1B`

这个手算漏了 **36 个 GDN 层的 SSM 投影**。逐层核对 GGUF 张量（见 §2.2），36 个 GDN 层各带 `attn_qkv [2048,8192]` + `attn_gate [2048,4096]` + `ssm_out [4096,2048]`，全注意力层带 `attn_q [2048,8192]` + `attn_k/v [2048,512]` + `attn_output [4096,2048]`。**官方自报 3B 是对的，原结论的 2.1B 是漏算。**

这个误差的**方向性后果**在原结论里是致命的：它把"每 token 读多少字节"算小了 1.5 倍，直接导致"decode 不应慢于现役"的乐观判断（§2.3 详述）。

### 1.2 许可证与下载量

| 项 | 值 | 来源 |
|---|---|---|
| 许可证 | apache-2.0 | ModelScope API + GGUF 头 `general.license` |
| 官方仓库下载量 | **522,825**（likes 1,703），lastModified 2026-02-03 | `https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next`（HF 直连被拦，镜像可达） |
| Unsloth GGUF 下载量 | **146,567**（likes 889），lastModified 2026-03-06 | `https://hf-mirror.com/api/models/unsloth/Qwen3-Coder-Next-GGUF` |
| ollama 官方档 | `qwen3-coder-next:q4_K_M` (52GB) / `:q8_0` (85GB) | `https://ollama.com/library/qwen3-coder-next/tags`；registry manifest 实测 q4_K_M layer size = 51,741,599,936 B |
| ollama manifest 元数据 | `model_family=qwen3next`, `renderer=qwen3-coder`, `parser=qwen3-coder`, `model_type=79.7B`, `requires=0.15.5` | `https://registry.ollama.ai/v2/library/qwen3-coder-next/manifests/q4_K_M` |
| GGUF 架构键 | `general.architecture = qwen3next` | GGUF 文件头（§2.2） |

**GGUF 确实存在且被广泛使用**（14.6 万次下载 + ollama 官方收录），不是冷门模型。

### 1.3 官方 benchmark 数字（作者自报，图表一手读取）

下载官方 benchmark 图 `https://qianwen-res.oss-accelerate-overseas.aliyuncs.com/Qwen3-Coder-Next/benchmarks.png`（4862×2136 PNG，本轮直接读图）：

| Benchmark | **Qwen3-Coder-Next (80B)** | DeepSeek-V3.2 (671B) | GLM-4.7 (358B) | MiniMax M2.1 (229B) |
|---|---|---|---|---|
| SWE-Bench Verified (w/ SWE-Agent) | **70.6** | 70.2 | 74.2 | 74.8 |
| SWE-Bench Multilingual (w/ SWE-Agent) | **62.8** | 62.3 | 63.7 | 66.2 |
| SWE-Bench Pro (w/ SWE-Agent) | **44.3** | 40.9 | 40.6 | 34.6 |
| Terminal-Bench 2.0 (w/ Terminus-2 json) | **36.2** | 39.3 | 37.1 | 32.6 |
| Aider | **66.2** | 69.9 | 52.1 | 61.0 |

与 Unsloth 文档（`https://unsloth.ai/docs/models/qwen3-coder-next.md`）里的表格**逐格一致**，确认 Unsloth 转引的就是这张官方表。

**注意：TB2.0 36.2 低于 DeepSeek-V3.2 的 39.3 和 GLM-4.7 的 37.1。** 我们的工作负载里有 Terminal-Bench，这是**唯一与现役同量纲的 agentic 分数**，作者自报 36.2 并不突出。

---

## 2. 速度证据核查（本次复核最关键的推翻）

### 2.1 本轮新方法：不靠手算，直接读 GGUF 文件头逐张量求和

原结论的"每 token 读 ~1.3GB"是手算的。我用 HTTP Range 请求只拉 GGUF **文件头**（不下载权重），解析出全部 843 个张量的 name / dims / quant type / offset，再按 `ggml/src/ggml-common.h` 的**真实 block 字节数**逐张量求和：

```bash
# 取 UD-Q3_K_XL 的前 40MB（GGUF 头 + 张量表，足够）
curl -sL -r 0-40000000 \
  "https://www.modelscope.cn/models/unsloth/Qwen3-Coder-Next-GGUF/resolve/master/Qwen3-Coder-Next-UD-Q3_K_XL.gguf" -o hdr.bin
# 解析：GGUF v3, n_tensors=843, n_kv=52
```

GGUF 头实测 KV（节选）：`general.architecture=qwen3next` / `qwen3next.block_count=48` / `context_length=262144` / `expert_count=512` / `expert_used_count=10` / `expert_feed_forward_length=512` / `full_attention_interval=4` / `general.size_label=512x2.5B`。

**这份文件头的自证价值**：`general.size_label = "512x2.5B"` —— Unsloth 自己标的 "512 专家 × 2.5B 激活"，与官方 README 的 "3B activated" 同量级，**再次否证原结论的 2.1B**。

### 2.2 逐张量字节分解（UD-Q3_K_XL，全部一手）

```
EXPERT(routed)    77,309,411,328 params   33663.5 MB  [IQ3_XXS, IQ4_XS, Q5_K]
attn(q/k/v/gate/out) 1,233,229,824 params   1298.0 MB  [F32, NVFP4, Q8_0]
token_embd           311,164,928 params    330.6 MB  [Q8_0]
ssm_out              301,989,888 params    320.9 MB  [Q8_0]
output_head          311,164,928 params    255.3 MB  [Q6_K]
router                50,331,648 params    201.3 MB  [F32]
shared_expert        150,994,944 params    158.9 MB  [NVFP4, Q8_0]
ssm_other              5,905,152 params      6.8 MB  [F32, Q3_K]
norms/other              198,656 params      0.8 MB  [F32]
文件总字节 = 36.24 GB (33.75 GiB)  ← 与 ModelScope 标称 36.28GB 吻合（0.1% 误差）
```

**decode 时每 token 实际要读的字节**（routed 专家只读 top-10/512，其余全读）：

| 组成 | UD-Q3_K_XL | UD-Q4_K_XL | UD-IQ3_XXS | UD-IQ3_S | UD-Q2_K_XL | ollama 官方 Q4_K_M |
|---|---|---|---|---|---|---|
| dense(attn+ssm+shexp+router) | 1986.6 MB | 1987.3 MB | 1592.5 MB | 1592.5 MB | 1422.0 MB | 1174.4 MB |
| experts (top10/512) | 657.5 MB | 916.3 MB | 530.8 MB | 554.4 MB | 487.2 MB | 979.1 MB |
| output_head | 255.3 MB | 330.6 MB | 255.3 MB | 255.3 MB | 175.0 MB | 255.3 MB |
| **每 token 合计** | **2899 MB** | **3234 MB** | **2378 MB** | **2402 MB** | **2084 MB** | **2409 MB** |

**对照：现役 Qwen3-Coder-30B-A3B-Instruct（同一方法实测）**

| | UD-Q4_K_XL | Q4_K_M（= 现役 ollama 档 18.5GB） |
|---|---|---|
| dense | 594.5 MB | 567.3 MB |
| experts (top8/128) | 1039.7 MB | 1097.1 MB |
| output_head | 255.3 MB | 255.3 MB |
| **每 token 合计** | **1889 MB** | **1920 MB** |

### 2.2b 新发现（可操作）：**ollama 官方档的每 token 字节数，比 Unsloth「3-bit 档」还少 17%**

把 ollama 官方 `qwen3-coder-next:q4_K_M`（51.74 GB）的张量表也解出来对比：

| 组成 | ollama 官方 Q4_K_M | Unsloth UD-Q3_K_XL | Unsloth UD-Q4_K_XL |
|---|---|---|---|
| dense(attn+ssm+shexp+router) | **1174.4 MB**（Q4_K/Q6_K） | 1986.6 MB（**Q8_0**） | 1987.3 MB（**Q8_0**） |
| experts (top10/512) | 979.1 MB | 657.5 MB | 916.3 MB |
| output_head | 255.3 MB | 255.3 MB | 330.6 MB |
| **每 token 合计** | **2409 MB** | **2899 MB** | **3234 MB** |
| 文件大小 | 48.18 GiB | 33.75 GiB | 46.16 GiB |

**机理**：Unsloth 的动态量化把 `attn_*` / `ssm_out` / `shared_expert` 留在 **Q8_0**（Unsloth 自己的文档就说过 "Quantizing any attn_* is especially sensitive for hybrid architectures, and so leaving them in higher precision works well"——**质量上正确，但在带宽受限的 decode 场景下是代价**）。ollama 官方档把这些压到 Q4_K/Q6_K，dense 部分因此少读 **812 MB/token**。

**结论（对选型有直接影响）**：
- Unsloth UD-Q3_K_XL 的**文件**比 ollama 官方 Q4_K_M 小 30%，但**每 token 读得反而多 20%**。
- 在**带宽受限的 decode** 场景（我们的 af-bench 就是），应当**优先选每 token 字节数少的档，而不是文件小的档**。
- **ollama 官方 `qwen3-coder-next:q4_K_M`（48.18 GiB）双卡 layer-split 后每卡约 23 GiB，余 9 GiB——放得下，且每 token 2.41GB 优于所有 Unsloth UD 档**（UD-IQ3_XXS 2.38GB 略优，UD-IQ3_S 2.40GB 相当）。
- **这条必须实测验证**：本轮只验证了字节数，没有验证 ollama 官方档的**输出质量**（它没有 imatrix 校准），质量可能低于 UD 档。**不可仅凭带宽结论直接换档。**

### 2.3 修正 2（核心）：decode 必然慢于现役，不是「同量级」

原结论（`:332`）写：
> **关键对比**：现役 30B-A3B 激活 3.3B、每 token 读 ~2.0GB，实测 135.7 tok/s。**两者激活量相近 ⇒ 速度相近**

前半句（现役每 token ~2.0GB）**实测正确**（我算得 1.92GB，误差 4%）。但推论错了，因为**「激活参数量相近」≠「每 token 读字节相近」**。真正的差异在于**每 token 必须全读的 dense 部分**：

- 现役 30B-A3B：`qwen3moe` 架构，48 层纯全注意力，无 GDN。dense 只有 attn + router + output。
- Qwen3-Coder-Next：`qwen3next` 架构，**36/48 层是 GDN**。每个 GDN 层额外带 `attn_qkv[2048,8192]` + `attn_gate[2048,4096]` + `ssm_out[4096,2048]`；每个全注意力层额外带 `attn_gate[2048,4096]`。**而且 Unsloth 的动态量化把这些 attn_*/ssm_out 张量留在 Q8_0（8.5 bpw），不是 3-bit。**

结果：**Coder-Next 每 token 读 2.90GB，是现役 1.92GB 的 1.51 倍**（Q4_K_XL 档更差，3.23GB = 1.68 倍）。

按现役实测反推带宽效率：135.7 tok/s × 1.92GB = **260 GB/s**（单卡 V100S-32GB-PCIe，900GB/s 理论值的 **29%**）。
用同一效率外推 Coder-Next（单卡放不下，必须双卡 layer-split，见 §2.4）：

> **UD-Q3_K_XL：双卡 layer-split 后每卡每 token 读 2899/2 ≈ 1450MB，按 260GB/s 有效带宽 ⇒ ≈ 90 tok/s**
> **UD-Q4_K_XL：≈ 1622MB/卡 ⇒ ≈ 80 tok/s**

**修正 3：原结论的「80–150 tok/s」区间，下界偏高。** 按一手字节数重算，双卡下 UD-Q3_K_XL 约 **90 tok/s**（UD-Q4_K_XL 更慢，约 80）；再叠加 §2.5 中 #28185 在 2× 卡上实测到的 45.3–51.0 tok/s 作为下界锚点，综合区间应为 **45–90 tok/s**。也就是说：

- 现役：**135.7 tok/s**（单卡，已实测）
- Coder-Next UD-Q3_K_XL：**≈ 90 tok/s**（双卡，推断）
- **Coder-Next 的单题墙钟时间约为现役的 1.5 倍**（同等 token 数下）

这与原结论「速度不牺牲、80–150 tok/s」**方向相反**。而 §2.4 还会显示：双卡 layer-split 在 Volta 上还要额外承担 PCIe 跨卡传输，进一步压低实际值。

**这个修正直接改变选型结论**：原结论说 Coder-Next「能力高一档、速度不牺牲 ⇒ 值得上」。实际是「能力高一档、速度慢 1.5 倍 ⇒ 只在能力缺口大到能盖过墙钟代价时才值得上」。

### 2.4 修正 4：双卡显存——「装不下」是错的，「放得下但每卡不均衡」才是真的

原结论（`:325`）算「49.6 + 0.8 + ~2 ≈ 52.4GB < 64GB，数学上放得下，但只剩 ~11GB buffer」，并把 Q4 档标为「双卡偏紧」，把 Q3 档标为「宽松」。

我按 GGUF 逐层字节分布算了 layer-split 的实际分配（UD-Q3_K_XL，48 层）：

```
blk.0..blk.45  每层 739.7 MB（blk.3/7/11/.../47 全注意力层略小 732.8 MB）
blk.46         968.8 MB  ← 异常层：attn_qkv/attn_gate/shared_expert 被 Unsloth 量化成 NVFP4
embd/other     585.9 MB

连续 24/24 切分：GPU0 = 17.71 GB (16.49 GiB)   GPU1 = 17.94 GB (16.71 GiB)   不均衡 1.3%
每卡 32GB 剩余：15.51 GiB / 15.29 GiB
```

**修正 5：**
1. **UD-Q3_K_XL 双卡放得非常宽松**（每卡只用 16.5 GiB，剩 15.3 GiB 给 KV + 计算缓冲 + 并发槽）。原结论说「36.28GB 塞 64GB，余 27GB」方向对但算的是两卡合计，掩盖了「layer-split 后每卡各 16.5 GiB」这个关键事实。
2. **Q4_K_XL（49.61GB）双卡是够的**（每卡约 23 GiB，剩 9 GiB），原结论的「偏紧」偏保守但方向对。
3. **原结论说「放不下时用 --n-cpu-moe」——这个前提在本模型上不成立**。Q3_K_XL 双卡 layer-split 每卡余 15.3GiB，根本不需要 CPU 卸载专家。**--n-cpu-moe 的正确用途是「显存不足时的降级手段」，不是本模型的部署方案。**
4. **新发现的不均衡风险**：blk.46 单层 968.8MB（比别层多 229MB），因为 Unsloth 把该层的 `attn_qkv`/`attn_gate`/`ffn_*_shexp` 量化成了 **NVFP4**。**NVFP4 是 Blackwell(sm_100/sm_120) 的原生格式**——见 §3.3，Volta 上没有对应硬件加速路径。

### 2.5 第三方实测 tok/s（哪些是真的，哪些是作者自报）

**明确：没有任何第三方在 V100 / 3090 / P40 / 4060Ti 上测过 Qwen3-Coder-Next。** 我在 llama.cpp issue 搜索了 6 组关键词（`Qwen3-Coder-Next+V100+tg` / `qwen3next+V100` / `Qwen3-Next+V100+bench` / `Qwen3-Coder-Next+4090+tok/s` 等），无一条 V100 速度记录。

**找到的真实第三方 tok/s（都是别的卡，但都指向同一个方向）：**

| 来源 | 硬件 | 模型/档 | 数字 | 状态 |
|---|---|---|---|---|
| llama.cpp **#19480** | AMD Ryzen AI 9 HX PRO 370（纯 CPU，96GB DDR5-5600） | Qwen3-Coder-Next Q4_K_M | **7.74 tok/s**（同机稠密 qwen2.5-coder:32b Q4_K_M 仅 3.54） | CLOSED |
| 同上引 #17936 | AMD EPYC 9454P（纯 CPU） | Qwen3-Next-80B vs Qwen3-MoE-30B | **11.76 vs 63.10 tok/s**（同为 ~3B 激活，**慢 5.4 倍**） | CLOSED |
| llama.cpp **#28185** | 2× RTX 5070 12GB | Qwen3-Coder-Next 80B UD-Q4_K_M，**--n-cpu-moe 38** | **45.3 tok/s**；改 `--override-tensor` 手动均衡 + `--n-cpu-moe 31` 后 **51.0 tok/s** | **OPEN** |
| llama.cpp **#25356** | AMD Strix Halo 8060S iGPU | Qwen3-Coder-Next **UD-Q4_K_XL**（512 experts top-10） | 批量 decode：B=1 **45.4** / B=8 122.5 / B=32 130.9 t/s | — |
| llama.cpp **#19672** | DGX Spark (GB10, sm_121) | Qwen3-Coder-Next UD-Q6_K_XL | llama-bench pp512 298.59 / **tg128 32.53** t/s（但真实推理崩溃，见下） | CLOSED |
| llama.cpp **#19345** | RTX 6000 Blackwell | Qwen3-Coder-Next **官方 Q8_0** | llama.cpp **70–80 tok/s** vs vLLM **120 tok/s** | CLOSED |

**#19480 是对原结论最有力的反证**（虽然只在 CPU 上）：报告者明确写「the CPU inference path in llama.cpp **isn't taking advantage of the sparse activation pattern** — it appears to be reading far more data than the 3B active params require」，并给出同机对照：同为 ~3B 激活的 Qwen3-Next-80B 比 Qwen3-MoE-30B **慢 5.4 倍**。这说明「激活少 ⇒ decode 快」在 llama.cpp 上**并不自动成立**——MoE 的专家读取有实现层面的开销。

**#28185 更是直接命中我们的部署形态**（2× 卡 + MoE + 专家卸载），且报出了两个我们必须知道的事实：
1. `--n-cpu-moe 38` 时 llama.cpp 的自动切分**极不均衡**（CUDA1 接近满载，CUDA0 只占 ~2GB），必须用 `--override-tensor` 手工把专家层钉到另一张卡；
2. 均衡后从 45.3 提升到 51.0 tok/s（+13%），说明**专家在卡上的分布直接决定吞吐**；
3. **最严重**：用 `--override-tensor` 重新均衡专家后，**输出质量退化**——模型编造不存在的函数名和超出文件长度的行号，21 个"bug"全是同一个模板。该 issue **OPEN**，报告者称 build 10826 上严重形态未复现但仍能测出"自信但错误"的诊断。

**综合裁定：**
- 原结论的「80–150 tok/s」是**纯推断**（原档案 `:372` 自己标注了"纯推断"），区间上界无依据。
- 唯一在 2× 卡上测过本模型的是 #28185：**45.3–51.0 tok/s**（且是 5070 Ti 级卡 + 大量专家在 CPU 上）。作为参照系，这比我重算的 ~90 tok/s 更悲观，故区间下界取 45。
- **修正 6：把「80–150 tok/s」改为「45–90 tok/s（推断，区间上界取 #28185 实测值，下界取本轮带宽重算）」。**

### 2.6 V100 本身的第三方数据（用于交叉校验我们的现役实测）

llama.cpp **#27366**（NOT_PLANNED），3× Tesla V100-SXM2-32GB，CC 7.0，driver 580.173.02，CUDA 12.5，`-DCMAKE_CUDA_ARCHITECTURES=70`：

| 配置 | pp4096 | tg128 |
|---|---|---|
| `-sm layer` 跨 CUDA1,CUDA2 | **777.09 ± 0.44** | **29.90 ± 0.52** |
| 单卡（CUDA0） | 774.81 ± 1.83 | 33.64 ± 0.05 |

这台机器上跑的模型是 `bartowski/Qwen3.8-27B-GGUF` Q4_K_M（**注意：原结论说是「Qwen3.8-27B」，issue 原文是 `Qwen3.8-27B-GGUF` Q4_K_M，arch `qwen35`，65 blocks = 17 attn + 48 SSM**）—— 稠密 27B，**tg128 29.90–33.64**。

这组数字**独立佐证了原结论"稠密模型在 V100 上 ~30 tok/s"这一条**（原结论这部分是对的），但它**测的不是 Qwen3-Coder-Next**，所以不能用来支持 Coder-Next 的任何速度断言。

同一 issue 另记录了对我们部署形态的三个硬事实：
- `-sm row` 在 CUDA 上**直接不支持**：`device CUDA1 does not support split buffers`（`src/llama-model.cpp:999` 抛错，全树只有 SYCL 实现 `ggml_backend_split_buffer_type`）；
- `-sm tensor` 在多卡 Volta 上 **hang 7 分钟**且每卡泄漏 **8286 MiB**；
- **`-sm layer` 正常**。

→ **原结论"2×V100 的部署约束是 --split-mode layer"正确，保留。** 但注意：ollama 0.40.6 的 runner 传的是 `--split-mode none --main-gpu N`（仅在用户显式设 MainGPU 时，见 `llm/llama_server.go:676`），**默认走 llama-server 的自动检测**（`common/arg.cpp:2821-2826` 默认 `layer`）。这条原结论没提，但结论方向一致。

---

## 3. V100（sm_70）上到底能不能跑

### 3.1 引擎与版本

| 项 | 结论 | 证据 |
|---|---|---|
| 推理引擎 | **只有 GGUF + llama.cpp 路线**。vLLM 路线死路 | vLLM 要求 CC≥7.5，V100=7.0 已被移除（原结论已述，方向对） |
| SGLang | **死路** | 官方 README 明确要求 `sglang>=v0.5.8`；SGLang 的 FA3/FlashInfer 需 sm_80+ |
| llama.cpp 版本 | 我们 ollama 0.40.6 = **llama.cpp v0.7.0**（`LLAMA_CPP_VERSION` = `b11669`），2026-10-15 编译 | `https://raw.githubusercontent.com/ollama/ollama/v0.40.6/LLAMA_CPP_VERSION` → `b11669`（本轮实测该 URL 返回 200 + `b11669`） |
| 架构支持 | `qwen3next` 是 llama.cpp **一等架构**：`src/llama-arch.cpp:38` `{ LLM_ARCH_QWEN3NEXT, "qwen3next" }`；转换器 `conversion/__init__.py:258` `"Qwen3NextForCausalLM": "qwen"` | 一手源码 |
| ollama 侧 | ollama 0.40.6 有 `compatmigrate/qwen3next.go`（处理 `.ssm_dt` → `.ssm_dt.bias` 迁移）、`model/renderers/qwen3coder.go`、`model/parsers/qwen3coder.go` | 一手源码 |
| sm_70 编译目标 | **仍在官方 CUDA 目标内**：`ggml/src/ggml-cuda/CMakeLists.txt` 第 44 行 `list(APPEND CMAKE_CUDA_ARCHITECTURES 50-virtual 61-virtual 70-virtual)`（**仅当 CUDA < 13**）；注释 `# 70 == V100, FP16 tensor cores` | 一手源码 |

⚠️ **新增风险（原结论没提）**：`70-virtual` 只在 `CUDAToolkit_VERSION VERSION_LESS "13"` 时加入。我们现在是 CUDA 12.6，安全；但**一旦升到 CUDA 13，sm_70 会从编译目标里消失**（题面已说"CUDA 13 已移除 Volta/sm_70 编译支持，580 系驱动是 Volta 最后期限"）——这两条是**同一个约束的两面**，值得在文档里绑在一起。

### 3.2 架构支持是 GA 的，但"混合注意力"这一族在 sm_70 上是**同一个共享内核**

**修正 7（重要）：原结论「Qwen3-Coder-Next 走的是更早的 qwen3next 架构，家族风险面小」是错的。**

我逐个查了 llama.cpp master 的 `src/models/` 下四个相关架构文件：

```
qwen3next.cpp  : grep -c llm_build_delta_net_base → 1
qwen35.cpp      : grep -c llm_build_delta_net_base → 1
qwen35moe.cpp   : grep -c llm_build_delta_net_base → 1
qwen4exp.cpp    : grep -c llm_build_delta_net_base → 1
```

**四个架构（qwen3next = Qwen3-Coder-Next、qwen35 = Qwen3.8-27B、qwen35moe = Qwen3.6-35B-A3B、qwen4exp = Qwen3.8-Flash-Next）共用同一个 `llm_build_delta_net_base` 图构建基类**，因而共用 `ggml/src/ggml-cuda/gated_delta_net.cu` + `gated-delta-net-mma.cu` 这套 GDN CUDA kernel。

**所以"qwen3next 架构老、风险面小"这个判断不成立**——它和 qwen3_5 家族踩的是同一块 GDN 地板。sm_70 上 GDN 的问题对它们一视同仁。

### 3.3 sm_70 上 GDN 快路径被关掉（性能影响，原结论完全没提）

`ggml/src/ggml-cuda/gated-delta-net-mma.cu:402-407`：

```cpp
// Enable only architectures benchmarked for this schedule. MMA support alone does not imply a speedup.
if (!ampere_mma_available(info.cc) ||
    (info.cc != GGML_CUDA_CC_AMPERE_GA10X && info.cc != GGML_CUDA_CC_ADA_LOVELACE &&
     info.cc != GGML_CUDA_CC_BLACKWELL && info.cc != GGML_CUDA_CC_DGX_SPARK)) {
    return gdn_path::ar;          // ← V100 (cc=700) 走这里
}
```

`ampere_mma_available(cc)` 定义在 `ggml/src/ggml-cuda/common.cuh:369-370`：`cc >= GGML_CUDA_CC_AMPERE`(=800)。

**V100 = cc 700 < 800 ⇒ GDN 的 MMA 融合快路径在 V100 上完全关闭**，退回 `gdn_path::ar`（`gated_delta_net.cu` 的 `launch_gated_delta_net`，用 FP32 标量路径，grid = `(H, n_seqs, ceil(S_v/(4*num_warps)))`，block = `(warp_size, num_warps)`）。

同时 `ggml/src/ggml-cuda/ssm-scan.cu:854-855`：
```cpp
&& GGML_CUDA_CC_IS_NVIDIA(cc)
&& cc >= GGML_CUDA_CC_TURING      // ← V100 (700) < TURING (750)，SSD 快路径也不走
```

**含义（重要且原结论未覆盖）**：Qwen3-Coder-Next 有 **36/48 层是 GDN**，这 36 层的核心计算在 V100 上跑的是**无 MMA 的 FP32 慢路径**。这解释了为什么"激活少 ⇒ 快"在本模型上不成立——**算子本身在 Volta 上就降级了**。这是对 §2.3 结论的**机理层面补强**，也是原结论完全没有识别的独立风险。

**FA（Flash Attention）在 sm_70 上是有的**：`fattn.cu:224` 专门有 `if (cc == GGML_CUDA_CC_VOLTA)` 分支做 GQA 优化调整，`fattn.cu:676` 起用 `volta_mma_available(cc)` 走 Volta MMA 路径。**原结论"llama.cpp 在 V100 上无 FlashAttention"不成立**——有，只是走的是 Volta 专用分支。真正的问题见下。

### 3.4 sm_70 上的 FlashAttention 崩溃风险（head_dim 256 是安全的）

llama.cpp **#28661**（OPEN）：SM70 V100 + CUDA FA + 非标准 head_dim → `CUDA error: invalid argument @ ggml_cuda_flash_attn_ext_mma_f16_case`（`fattn-mma-f16.cuh:1945`）。报告者给的修法是「cc==VOLTA 且 dkq ∉ {64,128,256} 时回退 cuBLAS」。

Qwen3-Coder-Next 的 `head_dim = 256`（config.json + GGUF `qwen3next.attention.key_length/value_length = 256`），**落在安全集合内 → 不触发**。原结论这条判断**正确，保留**。

`fattn.cu:574-620` 的 `K->ne[0]` 白名单确认 256 在列（case 256 要求 `V->ne[0] == K->ne[0]`）。

### 3.5 NVFP4：UD 档里混进了 Blackwell 格式（原结论完全没发现）

**新发现**：UD-Q3_K_XL 和 UD-Q4_K_XL 里各**有 5 个 NVFP4 张量**，全在 blk.46：

```
blk.46.attn_gate.weight      [2048, 4096]  NVFP4
blk.46.attn_qkv.weight       [2048, 8192]  NVFP4
blk.46.ffn_down_shexp.weight [512, 2048]   NVFP4
blk.46.ffn_gate_shexp.weight [2048, 512]   NVFP4
blk.46.ffn_up_shexp.weight   [2048, 512]   NVFP4
```

（对照 blk.45/47 全是 Q8_0/Q5_K/Q4_K/IQ4_XS/IQ3_XXS。）

**NVFP4 是 Blackwell 原生格式**（题面已说"无 FP4/NVFP4，那是 Blackwell sm_100/sm_120 的东西"）。查 llama.cpp 的 CUDA 侧：
- `mmq.cuh:74-77` 显示 MXFP4/NVFP4 **有** MMQ 内核（`mmq-instance-nvfp4.cu` 存在）；
- 但 `mmq.cuh:248-253`：`if (blackwell_mma_available(cc)) {...}` —— **非 Blackwell 走 `ggml_cuda_mmq_get_config_ampere` 通用路径**（`mmq.cuh:255-256`），即 NVFP4 在 Volta 上要**退化成通用 DP4A 路径**，没有原生 FP4 张量核加速；
- `mmq.cuh:127-128` 注释明写 `GGML_CUDA_MMQ_SRAM_LAYOUT_FP4, // MXFP4 and NVFP4 on Blackwell` 与 `GGML_CUDA_MMQ_SRAM_LAYOUT_NVFP4, // Generic NVFP4`——**确实存在 generic 路径**，所以**不会崩，但会慢**。

**修正 8：** 原结论说「MXFP4 在 V100 无硬件加速」是对的，但**没发现 UD 档里真的混进了 NVFP4 张量**。这影响两个判断：
1. UD 档的"动态量化"并非纯 K-quant 家族，blk.46 这一层在 Volta 上要走慢路径；
2. **这正是 #28185 那个"专家分布不均 + 输出退化"bug 的可能相关点**（blk.46 恰好是异常层，968.8MB，NVFP4 密集）。二者是否相关**我无法确认**，但值得在 anolis 冒烟时**单独看 blk.46 的输出**。

### 3.6 sm_70 上的未解决 issue 清单（逐条核实状态）

| Issue | 状态 | 内容 | 对 Coder-Next 的相关性 |
|---|---|---|---|
| **#27366** | NOT_PLANNED | 3×V100：`-sm row` CUDA 不支持；`-sm tensor` hang 7min + 泄漏 8286MiB/卡；`-sm layer` 正常。tg128 单卡 33.64 / 双卡 layer 29.90 | **直接相关**（决定部署参数）。但注意：测的是 Qwen3.8-27B（qwen35 架构），**不是** Coder-Next |
| **#29255** | **OPEN** | 7× Volta，layer-split，大 prefill + 0.98–0.99 前缀复用 → `CUDA error: invalid argument @ ggml_cuda_kernel_launch`。**这正是我们 af-bench 每题 10 轮工具调用、长日志复用的形态**。报者称新 build 连 `GGML_CUDA_DISABLE_GRAPHS=1` 都压不住 | **极高相关**。注意报告者明说"Reproduces across architectures (Qwen3.8-Flash-Next GGUF and DeepSeek-V4-Flash variants)"，**不是模型专属** |
| **#29783** | **OPEN** | 6× V100 32GB，Qwen3.5-122B-A10B（Gated DeltaNet）**首请求即崩**，`CUDA error: invalid argument @ ggml_cuda_kernel_launch`，报者假设"GDN/DeltaNet kernel 的 grid/block 维度超出 sm_70 的 CUDA 限制"。**"sm_70 用户目前被整个 Qwen3.5 家族锁在门外"** | **极高相关**。Qwen3-Coder-Next 同为 GDN 混合架构（36 GDN 层），踩同一块地板（§3.2） |
| **#28185** | **OPEN** | Qwen3-Coder-Next 80B UD-Q4_K_M，2× RTX 5070，**`--tensor-split`/`--override-tensor` 导致输出退化**（编造函数名/行号）；报告者："MoE experts stay almost entirely on one device regardless of the split ratio tried" | **极高相关**（本模型 + 多卡 + 专家分布） |
| **#19672** / **#19705** | CLOSED | Qwen3-Coder-Next **512-expert MoE** 在 CUDA 上 `ggml_mul_mat_id` 断言失败（`ids_to_sorted_host.size() == ne_get_rows`）。llama-bench 通过但真实推理崩。CPU fallback 正常 | 已修（CLOSED），但**说明本模型的 512 专家 CUDA 路径曾经脆弱** |
| **#19794** | OPEN | Qwen3-Coder-Next（Hybrid）**Prompt Cache 强制全量重处理**："invalidated context checkpoint ... lack of cache data (likely due to SWA or hybrid/recurrent memory)" | **高相关**。我们的工作负载是 10 轮工具调用、每轮都追加大量上下文——**前缀缓存被反复作废 = 每轮全量重 prefill = 墙钟时间灾难**。这条原结论**完全没提** |
| **#25913** | CLOSED | `/slots save/restore` 在 hybrid/recurrent 模型上静默丢失全部 prompt 复用 | 相关（已修） |
| **#25582** | NOT_PLANNED | DeepSeek-V4-Flash：MoE 专家层在 CUDA 上输出损坏，**`--n-cpu-moe 999`（专家全在 CPU）输出正确** | 说明 CUDA 专家路径确有输出正确性风险史（但架构不同，非本模型） |
| **#27022** | NOT_PLANNED | Vulkan + qwen3next MoE + **IQ1_M router** → 全 0 / 乱码。**"qwen3next" 架构明确在标题里** | 提示 qwen3next 的 router 张量对极低比特极敏感。**我们不用 IQ1_M，但这条印证了"router 出问题 = 全盘崩溃"** |
| **#27623** | OPEN | Qwen3.8-27B（hybrid GDN）decode 在 >80K 位置**塌陷 25 倍** | 相关（同族架构，长上下文退化） |
| **#28879** | OPEN | hybrid GDN 架构上 **PPL 非精度单调**（F16 比 Q4_K_M 还差），PPL 口径失效 | 相关（**不能用 PPL 选量化档**） |
| **#30906** | — | **CPU 后端**对 qwen35 家族输出乱码（重复循环），**同一二进制 + 同一 GGUF 在 Vulkan 后端正常** | 相关（后端差异） |
| **#19480** | CLOSED | Qwen3-Coder-Next CPU 推理比带宽预期慢 3–4 倍（7.74 tok/s）；同机 Qwen3-MoE-30B 63.10 vs Qwen3-Next-80B 11.76 | **本模型 + 慢 5.4 倍的对照**，佐证 §2.5 |

**净结论：sm_70 上「能不能跑」= 能跑（llama.cpp + GGUF + `--split-mode layer`），但「跑得稳不稳」= 有一堆 OPEN 级 issue，且其中 #29255 / #29783 的触发条件与我们的工作负载形态高度重合。**

---

## 4. 质量证据核查：有没有第三方独立复现 agentic 分数

**答案：没有。**

| 分数 | 来源性质 | 复核结果 |
|---|---|---|
| SWE-V 70.6 / SWE-Multi 62.8 / SWE-Pro 44.3 / TB2.0 36.2 / Aider 66.2 | **作者自报**（官方 benchmark 图，Unsloth 文档转引同一张表） | 数字准确，但**无第三方复现** |
| Aider Polyglot 上的 GGUF 量化档对比 | 第三方（Unsloth 文档转引「Benchmarks were run by third-party contributors on the Aider Polyglot server」） | **只复现"量化档相对排序"，不复现模型绝对 agentic 能力**。图我拉下来读了：UD-IQ3_XXS ≈ 65%、NVFP4 ≈ 67.3%、UD-Q6_K_XL ≈ 65.4%、UD-Q2_K_XL ≈ 57.3%、API ref (bf16) = 66.2%。**图里没有 UD-Q3_K_XL 这个档**（有 UD-IQ3_XXS、UD-Q6_K_XL、UD-Q2_K_XL、UD-IQ2_XXS、NVFP4、FP8、REAP-60B、REAM-Q4、REAP-48B） |
| Benjamin Marie 750 题混合集（LCB v6 / MMLU Pro / GPQA / Math500） | 第三方 | 是**知识/推理**题，不是 agentic 题。Unsloth 文档转述："Q3_K_M expectedly performs worse on LiveCode Bench v6... It seems to run with the most efficiency, using at least Q4_K_M is advised"。**图像 URL 已 404**（我实测 `https://3215535692-files.gitbook.io/.../HAfMRrrXQAALkQb.png` → 404），无法读原图核对 |
| aider.chat 官方榜单 | — | 我抓了 `https://aider.chat/docs/leaderboards/`（569KB）与 `https://aider.chat/2024/12/21/polyglot.html`（47KB），**grep "Coder-Next" / "Qwen3-Next" / "80B" 全部 0 命中** → 官方 Aider 榜单上**没有本模型条目** |

**与现役模型的直接对比（我们需要的锚点）**：现役 Qwen3-Coder-30B-A3B-Instruct 的官方 SWE-Bench Verified 分数我**没能在本轮拿到数字**（其 ModelScope README 指向 `qwenlm.github.io/blog/qwen3-coder/`，该页的分数是 480B-A35B 的，30B-A3B 的分表在图片里、本轮未取到）。**这是本复核的一个已知缺口**——原结论写「现役 30B-A3B 档（AA II 10 / SWE 口径弱）」，"AA II 10"这个口径我无法追溯来源。

**修正 9：原结论的对比基准「官方 SWE-V 70.6 vs 现役 AA II 10」不成立/不可核实。** 现役模型在同一口径下的官方 SWE-V 分数本轮未取得，无法说清"能力高一档"到底高多少。**在拿到现役的同口径官方分之前，不应声称"显著高于"。**

---

## 5. 对原结论的逐条修正汇总

| 原结论位置 | 原文 | 修正 |
|---|---|---|
| `quant-ecosystem.md:306` | 「激活 ~2.1B」 | **→ 3B**（官方 README + GGUF `general.size_label=512x2.5B`；原手算漏了 36 个 GDN 层的 SSM 投影） |
| `:329` | 「注意力/嵌入 0.45B」 | **→ 漏算严重**，GGUF 实测 dense 部分 1.99GB/token（Q3_K_XL） |
| `:306` / `:332` | 「激活 2.1B ⇒ 每 token 读 ~1.3GB ⇒ decode 不应慢于现役 30B-A3B」 | **→ 推翻**。实测每 token 读 **2.90GB**（Q3_K_XL）/ **3.23GB**（Q4_K_XL），是现役（1.92GB）的 **1.5–1.7 倍**。**decode 必然慢 1.5 倍左右** |
| `:372` / `:400` | 「80–150 tok/s（推断）」 | **→ 45–90 tok/s**。上界取 #28185 实测（2× 卡 + 专家卸载 = 45.3–51.0 tok/s），下界取本轮带宽重算（双卡 layer-split ≈ 90 tok/s） |
| `:322` | 「Qwen3-Coder-Next 走的是更早的 qwen3next 架构，家族风险面小」 | **→ 推翻**。qwen3next / qwen35 / qwen35moe / qwen4exp **共用同一 `llm_build_delta_net_base` 与同一套 GDN CUDA kernel**，sm_70 风险面同样大 |
| `:443`（计划） | 「sm_70 支持 FA」 | **→ 正确**（`fattn.cu:224` 有 Volta 专用分支），但**必须补一条**：sm_70 上 GDN 的 MMA 快路径被关（`gated-delta-net-mma.cu:403`，需 cc≥800），36/48 层的核心算子走 FP32 慢路径 |
| `:325` | 「Q4 档 49.6GB 塞 64GB 偏紧；建议 Q3_K_XL」 | **→ 部分修正**。逐层算：Q3_K_XL 双卡 layer-split 后**每卡各 16.5 GiB，余 15.3 GiB**，很宽松；Q4_K_XL 每卡约 23 GiB，余 9 GiB，也够。**「放不下」不成立** |
| `:266` | 「CPU 专家 456MB/token ⇒ ~30 tok/s」 | **→ 前提不适用**。本模型 Q3_K_XL 双卡后根本不需要 `--n-cpu-moe`；--n-cpu-moe 是显存不足时的降级手段。而且 #28185 证明 CPU 卸载下专家分布极难均衡（需 --override-tensor），而**手动均衡会触发输出退化 bug（OPEN）** |
| `:400` | 「P1（主候选）」 | **→ 降级为 P2 备选**。能力最高是事实，但速度慢 1.5 倍 + sm_70 GDN 风险面未收敛 + #19794 前缀缓存反复作废，**综合看不该作为首个上量对象** |
| `:287` | 「#28661 我们的候选 head_dim 都是 256 → 不触发」 | **→ 正确，保留** |
| `:37`（结论 6） | 「2×V100 部署约束是 --split-mode layer」 | **→ 正确，保留**。补充：ollama 0.40.6 默认走 llama-server 自动检测（默认即 layer），仅在显式设 MainGPU 时才传 `--split-mode none` |
| `:411` | 「下载 URL：ModelScope .../Qwen3-Coder-Next-UD-Q3_K_XL.gguf（36.28GB）」 | **→ 正确，保留**。补充实测：36.28GB = 33.75 GiB |
| — | （原结论未提） | **新增**：`#19794` hybrid 模型 prompt cache 强制全量重处理 —— 与我们 10 轮工具调用的工作负载形态直接冲突 |
| — | （原结论未提） | **新增**：UD 档 blk.46 混入 5 个 **NVFP4** 张量（Blackwell 格式），Volta 上走 generic 慢路径 |
| — | （原结论未提） | **新增**：sm_70 上 GDN MMA 快路径关闭（需 cc≥800），36/48 层核心算子降级 |
| — | （原结论未提） | **新增**：CUDA 12.6 升 CUDA 13 会让 `70-virtual` 从编译目标消失（`CMakeLists.txt:43-45`） |
| 原结论「最大风险」段 | 「我们用 ollama 内置 runner（b11669），**没有暴露关闭 CUDA graphs 的开关**，无法规避」 | **→ 前提错误。** `ollama v0.40.6` 的 `llm/llama_server.go:476` 第一行就是 `cmd.Env = os.Environ()`——**llama-server 子进程完整继承父进程环境变量**。`GGML_CUDA_DISABLE_GRAPHS=1` 只要在启动 ollama 前 export 即可透传。**#29255 的「无法规避」结论不成立**（但 #29255 报告者自己说该开关在较新 build 上"helps on ≤2.33 builds; newer builds have launch paths that bypass it"，所以能否真压住**仍需实测**） |
| — | （原结论未提） | **新增**：**选档应按「每 token 字节数」排，不按文件大小排**。ollama 官方 Q4_K_M 每 token 2.41GB < Unsloth UD-Q3_K_XL 2.90GB（§2.2b）。Unsloth 把 attn_*/ssm_out 留 Q8_0 在带宽受限的 decode 下是劣势 |

---

## 6. 复核方法与未做事项

### 6.1 本轮实际执行的取证

| # | 命令 / 动作 | 结果 |
|---|---|---|
| 1 | `curl https://www.modelscope.cn/api/v1/models/Qwen/Qwen3-Coder-Next` | 官方元数据、License apache-2.0、Downloads 49381 |
| 2 | `curl .../resolve/master/config.json`（Qwen3-Coder-Next / Qwen3.8-27B / Qwen3.8-Flash-Next） | 全部架构参数 |
| 3 | `curl https://hf-mirror.com/api/models/{Qwen/Qwen3-Coder-Next, unsloth/Qwen3-Coder-Next-GGUF}` | 下载量 522,825 / 146,567 |
| 4 | `curl https://registry.ollama.ai/v2/library/qwen3-coder-next/manifests/q4_K_M` | layer size 51,741,599,936 B；manifest config（family/renderer/parser） |
| 5 | `curl -r 0-40000000 <UD-Q3_K_XL.gguf>` + 自写 GGUF 解析器 | 843 张量、52 KV、逐张量字节表、**逐层字节分布** |
| 6 | 同法对 UD-Q4_K_XL / UD-IQ3_XXS / UD-IQ3_S / UD-Q2_K_XL / ollama 官方 Q4_K_M / 现役 30B UD-Q4_K_XL / 现役 30B Q4_K_M | 7 个 GGUF 头的逐张量字节表 |
| 7 | `curl` 拉 llama.cpp master 的 `src/llama-arch.cpp` `src/models/qwen3next.cpp` `src/models/qwen35.cpp` `src/models/qwen35moe.cpp` `src/models/qwen4exp.cpp` `ggml/src/ggml-cuda/{CMakeLists.txt, common.cuh, fattn.cu, mmq.cuh, gated_delta_net.cu, gated-delta-net-mma.cu, ssm-scan.cu, convert.cu}` `ggml/src/ggml-common.h` `common/arg.cpp` | 架构表、GDN kernel 分派、arch 白名单、量化 block 尺寸 |
| 8 | `curl` 拉 ollama v0.40.6 的 `LLAMA_CPP_VERSION` `llm/llama_server.go` `llm/llama_binary.go` `compatmigrate/qwen3next.go` `model/renderers/qwen3coder.go` `model/parsers/qwen3coder.go` `template/index.json` | b11669、split-mode 传参、qwen3next 兼容迁移 |
| 9 | GitHub issue HTML 抓取 + 自写解码器，逐条读正文/评论/状态 | #27366 #29255 #29783 #28185 #19672 #19705 #19480 #18112 #17936 #25356 #19345 #19442 #19794 #25913 #25582 #27022 #27623 #28879 #28661 #30906 |
| 10 | 读官方 benchmark PNG + Unsloth 文档 .md + Unsloth Aider 图（webp→png） | 全部官方分数、Aider 量化档对比图 |
| 11 | `curl https://ollama.com/docs/faq` | 多卡行为原文："If the model will entirely fit on any single GPU, Ollama will load the model on that GPU... If the model does not fit entirely on one GPU, then it will be spread across all the available GPUs" |

### 6.2 本轮**未做**（明确声明，不填猜测）

- **未在 anolis-gpu-01 上跑任何东西**。本会话机是 pandev-comp（RTX 3070 Laptop 8GB）。**所有 V100 数字都是第三方或推断，非本轮实测。**
- **未下载任何模型权重**（只做 HTTP Range 拉文件头，最小 20–40MB）。
- **未复现任何 tok/s 实测**。
- **未取得现役 Qwen3-Coder-30B-A3B-Instruct 的官方 SWE-Bench Verified 分数**（其分数表在博客图片里，本轮未定位到该图）→ §4 的对比缺口。
- **未取得 Benjamin Marie 第三方 750 题图的原图**（URL 404）→ 只采信 Unsloth 的文字转述。
- **未验证 #19794 的前缀缓存问题在 Coder-Next + V100 上的实际影响**（该 issue 用的是 Qwen3-Coder-Next GGUF，CUDA，RTX 3060 8.6 —— 硬件不同）。
- **未验证 blk.46 的 NVFP4 与 #28185 输出退化 bug 是否相关**（纯假设，无证据）。
- **未核实 V100S-32GB-PCIe 的 900GB/s 一手规格**。nvidia.com 数据表 URL 404、TechPowerUp 页面 JS 渲染取不到文本、hf/wikipedia 路径未取到。**900GB/s 仍是沿用原结论的未证前提**，不过本复核的带宽推算用的是**现役模型的实测反推值（260GB/s 有效带宽）**，不依赖 900 这个数，故结论对规格误差不敏感。
- **未验证 ollama 0.40.6 的 runner 在 Coder-Next 上的实际多卡行为**（ollama FAQ 说放不下会 spread，但 FAQ 说的是"load on that GPU / spread across all"，没提 split-mode；实际 llama-server 默认 layer 模式 + #27366 表明 layer 在 Volta 上可用，二者结合推断可行，但**未实测**）。
- **未验证 #29255 在 ollama 内置 runner 上是否真的可规避**（即设了 `GGML_CUDA_DISABLE_GRAPHS=1` 后是否就不崩了）。**但原结论"ollama 没有暴露关闭 CUDA graphs 的开关"这个前提本身是错的**——见 §5 修正 10。

### 6.3 复核的置信度

| 断言 | 置信度 | 依据 |
|---|---|---|
| 模型存在、参数、ctx、license、官方分数 | **高** | 官方一手 + GGUF 头双证 |
| GGUF 档位体积、逐张量量化类型 | **高** | 一手二进制解析，与 ModelScope 文件大小吻合 0.1% |
| 每 token 读字节数（2.90 / 3.23 / 1.92 GB） | **高** | 一手逐张量求和，block 尺寸取自 ggml-common.h 静态断言 |
| 推理引擎/版本/架构支持状态 | **高** | 一手源码 |
| sm_70 上 GDN 快路径关闭 | **高** | 一手源码（含 cc 常量与分派条件） |
| sm_70 风险面"qwen3next 不比 qwen3_5 小" | **高** | 一手源码（4 个架构共用同一 base class 与 kernel） |
| issue 状态与触发条件 | **高** | 逐条读原文 + 状态字段 |
| 双卡显存分配（每卡 16.5 GiB / 23 GiB） | **中高** | 逐层字节一手计算；**未实测 llama.cpp 实际切分行为** |
| 45–90 tok/s 区间 | **中** | 区间上界有第三方实测（换卡），下界是带宽推断；**非 V100 实测** |
| "无第三方复现 agentic 分数" | **中高** | 查了 Unsloth 文档、Aider 官网榜单、ModelScope；**HF/Reddit/HN 本机不可达**（hf.co 307 重定向可达但 hf-mirror 的 API 不含榜单数据） |

---

## 7. 给决策者的三条落点

1. **「换模型能提解题率」这个命题本身没被推翻，但「换模型不牺牲速度」被推翻了。** 我们的负载里单题墙钟时间与解题率同等重要，因此正确的问题不是"Coder-Next 强不强"，而是"**强出来的那些分值，值不值多付的 1.5 倍墙钟**"。按官方自报 SWE-V 70.6 vs 现役（口径待补齐），这个账要等现役同口径分出来才算得清。

2. **如果一定要上 Coder-Next，档位选择应按「每 token 字节数」而不是「文件大小」来排**（§2.2b）。Unsloth UD 档把 attn_*/ssm_out 留在 Q8_0，在带宽受限的 decode 下反而吃亏：**ollama 官方 `qwen3-coder-next:q4_K_M`（48.18 GiB）每 token 只读 2.41GB，比「3-bit」的 UD-Q3_K_XL（2.90GB）还少 17%**；UD-IQ3_XXS（2.38GB）与之相当且文件只有 33.75 GiB（双卡每卡 16.5 GiB，最宽松）。**但 ollama 官方档没有 imatrix 校准，输出质量未知——必须实测对比后再定。**

3. **上量前必须在 anolis 做的三件事**（按优先级）：
   - a) **先量现役 30B-A3B 的同口径官方 SWE-V / TB2.0 分数**（补 §4 的缺口），否则无法判断值不值；
   - b) **在 anolis 上实测 Coder-Next 的 decode tok/s**（预期 45–90，双卡 layer-split），并**同时抓 blk.46 的输出**（NVFP4 密集层）；
   - c) **专门测 #19794 的前缀缓存行为**：我们 10 轮工具调用每轮追加大量上下文，若 hybrid 模型的 cache 反复被作废，每轮全量重 prefill 会让墙钟时间再翻倍——**这条比模型强弱更能决定本地臂能不能用**。

---

## 8. 引用来源清单

**一手（官方）**
- `https://www.modelscope.cn/api/v1/models/Qwen/Qwen3-Coder-Next`
- `https://www.modelscope.cn/models/Qwen/Qwen3-Coder-Next/resolve/master/{config.json,README.md}`
- `https://www.modelscope.cn/models/unsloth/Qwen3-Coder-Next-GGUF/resolve/master/README.md`
- `https://www.modelscope.cn/api/v1/models/unsloth/Qwen3-Coder-Next-GGUF/repo/files?Revision=master&Root=`
- GGUF 文件头（HTTP Range）：`unsloth/Qwen3-Coder-Next-GGUF` 的 `UD-Q3_K_XL` / `UD-Q4_K_XL` / `UD-IQ3_XXS` / `UD-IQ3_S` / `UD-Q2_K_XL`；`unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF` 的 `UD-Q4_K_XL` / `Q4_K_M`；`registry.ollama.ai` 的 `qwen3-coder-next:q4_K_M`
- `https://qianwen-res.oss-accelerate-overseas.aliyuncs.com/Qwen3-Coder-Next/benchmarks.png`
- `https://unsloth.ai/docs/models/qwen3-coder-next.md`
- `https://ollama.com/library/qwen3-coder-next{,/tags}`、`https://registry.ollama.ai/v2/library/qwen3-coder-next/manifests/q4_K_M`、`https://ollama.com/docs/faq`
- `https://hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next` 与 `.../unsloth/Qwen3-Coder-Next-GGUF`

**一手（llama.cpp 源码，master，2026-10-21 拉取）**
- `src/llama-arch.cpp:38`、`src/models/qwen3next.cpp`、`src/models/qwen35.cpp`、`src/models/qwen35moe.cpp`、`src/models/qwen4exp.cpp`（四个架构均 `llm_build_delta_net_base`）
- `ggml/src/ggml-cuda/CMakeLists.txt:23-29,42-47`（arch 注释 + `70-virtual` 仅 CUDA<13）
- `ggml/src/ggml-cuda/common.cuh:52-55,160-183,320-375`（CC 常量、`highest_compiled_arch`、`ampere_mma_available`、`volta_mma_available`）
- `ggml/src/ggml-cuda/gated-delta-net-mma.cu:384-445`（GDN 路径分派）、`gated_delta_net.cu:182-215,330-385`（fallback 几何与调用点）
- `ggml/src/ggml-cuda/ssm-scan.cu:849-876`（SSD 路径需 cc≥TURING）
- `ggml/src/ggml-cuda/fattn.cu:180-240,540-700,757-775`（Volta FA 分支、head_dim 白名单、kernel 选择）
- `ggml/src/ggml-cuda/mmq.cuh:66-100,121-160,240-320`（MMQ 类型表、NVFP4 SRAM layout、Blackwell 分支）
- `ggml/src/ggml-cuda/convert.cu:383-421`（NVFP4 dequant）
- `ggml/src/ggml-common.h:89-90,214-227,230-260,320-370,380-460`（QK_K=256、NVFP4 block、各量化 block 字节数 static_assert）
- `common/arg.cpp:2820-2834`（`--split-mode` 默认 layer）、`common/arg.cpp:2771,4170`（`--n-cpu-moe`）
- `tools/quantize/README.md`（官方 CPU 量化速度表）

**一手（ollama v0.40.6 源码）**
- `LLAMA_CPP_VERSION` → `b11669`
- `llm/llama_server.go:426-442,602-680,711-720`（参数暴露面、split-mode 传参）
- `llm/llama_binary.go`、`llm/model_split.go`
- `compatmigrate/qwen3next.go`（qwen3next 的 `.ssm_dt` → `.ssm_dt.bias` 迁移）
- `model/renderers/qwen3coder.go`、`model/parsers/qwen3coder.go`、`template/index.json`

**第三方（llama.cpp issue，逐条读原文/评论/状态）**
#27366(NOT_PLANNED) #29255(OPEN) #29783(OPEN) #28185(OPEN) #19672(CLOSED) #19705(CLOSED) #19480(CLOSED) #18112(CLOSED) #17936(CLOSED) #25356 #19345(CLOSED) #19442(CLOSED) #19794 #25913(CLOSED) #25582(NOT_PLANNED) #27022(NOT_PLANNED) #27623(OPEN) #28879(OPEN) #28661 #30906

**第三方（其他）**
- Aider 官方榜单 `https://aider.chat/docs/leaderboards/` 与 `https://aider.chat/2024/12/21/polyglot.html`（本模型**无条目**）
- Unsloth 转引的 Aider Polyglot 量化档对比图（图内无 UD-Q3_K_XL 档）
- Unsloth 转引的 Benjamin Marie 750 题分析（**原图 URL 已 404**）
