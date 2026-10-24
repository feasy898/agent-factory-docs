# 复核·第8名·Qwen3.6-35B-A3B（Qwen/Qwen3.6-35B-A3B）

- 复核日期：2026-10-21
- 复核对象：`Qwen/Qwen3.6-35B-A3B`（35B 总参 / 3B 激活的 MoE，qwen3_5_moe 架构，多模态）
- 被复核的原结论：`调研/本地模型选型/notes/our-workload.md`（2026-10-21 出具）中关于该候选的条目 + `调研/本地模型选型/notes/local-vs-api.md` §2.2
- 取证纪律：
  - **【直证】**= 本轮亲自跑过的命令 / 亲自读过的文件（给命令与输出要点、或 `路径:行号`）
  - **【转引】**= 本轮亲自读到的外部页面/仓库内容（给 URL + 读到的原文要点）
  - **【未核实】**= 本轮查不到、无法验证的项，明确写"无法核实"，不填推测值
- **本轮未下载任何模型权重，未在 anolis 上启动任何新模型，未改动任何服务配置**；只做了只读检查（`curl` registry / ModelScope API、`ssh anolis` 只读 `ls`/`strings`/`nvidia-smi`/`ps`、读 ollama 日志、读 ollama 与 llama.cpp 源码）

---

## 0. 一页纸结论

1. **模型是真的，身份清楚**：`Qwen/Qwen3.6-35B-A3B` 在 ModelScope 上有官方镜像（HF 本轮不可达，`http=000`），`config.json` 直读到 `Qwen3_5MoeForConditionalGeneration` / 40 层 / 256 专家取 8 + 1 shared / hidden 2048 / **full_attention head_dim 256** / `max_position_embeddings 262144` / `mtp_num_hidden_layers 1` / 带 vision tower（27 层、hidden 1152）。许可 **Apache-2.0**。
2. **官方分数直读无误**：SWE-bench Verified **73.4**、Multilingual 67.2、Pro 49.5、**Terminal-Bench 2.0 51.5**（模型卡 HTML 表）。**但这是孤证**：本轮未找到任何第三方对 SWE-V / TB 做过独立复现（找到的第三方数据要么 n=2，要么是衍生版，要么是负面报告）。
3. **能跑，且我们这条路径是最省事的那条**：`ollama 0.40.6` 官方库里就有 `qwen3.6:35b`（库页 7.2M downloads），权重 + projector = **21.07 GiB，单张 V100S-32GB 装得下**；anolis 上 ollama 实际跑的是 **llama-server runner**（`llama-server 0.7.0-dev, commit 620d2225c`），其 `libllama.so.0.7.0` 内含 **51 处 `qwen35moe` 符号** ⇒ 架构 + MTP 图在位。
4. **原结论有一处硬错必须改**：**"harness 的 OpenAI 路径没有 thinking 开关 ⇒ 没有旋钮可关"是错的**。ollama 0.40.6 的 OpenAI 兼容层支持 `reasoning_effort`，其中 `"none"` → `ThinkValue{false}`（`openai/openai.go:585-590`），而 qwen3.5 家族 renderer 读 `think.Bool()` 决定是否出 `<think>`（`model/renderers/qwen35.go:217-219`）⇒ **发 `reasoning_effort:"none"` 就能关掉 thinking**。真正要改的是 harness 侧（`af/crates/af-harness/src/endpoint.rs:365-372` 把 `ReasoningTier::Off` 映射成"不发字段"）。
5. **原结论漏了两条对生产有用的信息**：(a) ollama 的 `qwen3.6:35b` 本身就是 **MTP 构建**（manifest `from` = `35b-a3b-mtp-q4_K_M-20260824`，params `draft_num_predict=2`），且 ollama 0.40.6 的 llama-server runner 会**自动启用 MTP**（`llm/llama_server.go:863-870, 928-934`）⇒ 有机会白捡 1.3–1.5×（需冒烟）；(b) 该模型的 **KV 只有 20 KiB/token**（现役 30B 是 96 KiB/token），同样显存下 ctx 余量高一个量级。
6. **风险要改写口径**：原结论写"同族 sm_70 崩溃 issue #29783 **未修**"——精确说法是：#29783 至今 open，但上游维护者 2026-10-01 评论称**已由 PR #29803 修复**（Volta FA 缺 head 320/256 配置，用 Ampere 配置会共享内存溢出而崩）；**我们 ollama 内置的 llama.cpp fork 是否含该修复，本轮无法核实**（fork 仓库 raw 路径取不到、GitHub API 限流）。而我们的模型 full-attention head_dim **正好是 256**，且 ollama 启动参数是 `--flash-attn auto`（默认走 FA）⇒ **冒烟必测，兜底开关 `OLLAMA_FLASH_ATTENTION=0`**。
7. **速度证据**：最接近的第三方实测是 **98.8 tok/s**（V100-SXM2-32GB、llama.cpp 自编 sm_70、unsloth UD-Q4_K_M、ctx 16384、thinking ON、单流），作者自述 PCIe 约慢 10%。**没有任何人在"2×V100S-PCIe + ollama + 我们的真实 ctx 深度(10–32K) + 我们的 40 轮工具调用形态"下测过它**。我们本轮也**没跑**（不下载权重）。
8. **裁定**：**保留为"最该打榜的一档"，但把它从"能力更强的候选"降级为"能力未知、极可能更快、开关可关的候选"**。它的官方分比现役高是**官方自报**，没有任何独立复现；因此正确姿势是"先花 1 小时冒烟（能不能起、thinking 能不能关、MTP 稳不稳），再用我们自己的 af-bench 打榜"，而不是把 73.4 当既成事实写进决策。

---

## 1. 模型真身核查

### 1.1 官方仓库与参数（【直证】+【转引】）

- **HuggingFace 本轮不可达**：`curl -4 -m 25 https://huggingface.co/api/models/Qwen/Qwen3.6-35B-A3B` → `http=000`（连接失败，非 404）；`https://huggingface.co` 与 `https://hf-mirror.com` 同样 `http=000`。**因此 HF 上的下载量、官方是否发 GGUF，本轮无法核实。**
- **ModelScope 官方镜像可读**（`https://www.modelscope.cn/api/v1/models/Qwen/Qwen3.6-35B-A3B` → http=200，`Architectures: ["Qwen3_5MoeForConditionalGeneration"]`，`ChineseName: 千问3.6-35B-A3B`）。
- `config.json` 直读（`https://www.modelscope.cn/api/v1/models/Qwen/Qwen3.6-35B-A3B/repo?Revision=master&FilePath=config.json` → http=200, 3686 B）关键字段：

| 字段 | 值 | 出处 |
|---|---|---|
| `architectures` | `["Qwen3_5MoeForConditionalGeneration"]` | config.json |
| `model_type` | `qwen3_5_moe`（text_config: `qwen3_5_moe_text`） | 同上 |
| `num_hidden_layers` | **40** | 同上 |
| `full_attention_interval` | **4** ⇒ 40 层里 10 层 full attention、30 层 linear attention | 同上 |
| `num_experts` / `num_experts_per_tok` | **256 / 8** | 同上 |
| `shared_expert_intermediate_size` / `moe_intermediate_size` | 512 / 512 | 同上 |
| `hidden_size` | **2048** | 同上 |
| `num_attention_heads` / `num_key_value_heads` / `head_dim` | 16 / **2** / **256** | 同上 |
| `linear_num_key_heads` / `linear_num_value_heads` / `linear_key_head_dim` / `linear_value_head_dim` | 16 / 32 / 128 / 128 | 同上 |
| `max_position_embeddings` | **262144** | 同上 |
| `mtp_num_hidden_layers` | **1**（带 MTP 头） | 同上 |
| `dtype` / `mamba_ssm_dtype` | bfloat16 / float32 | 同上 |
| `vocab_size` | 248320 | 同上 |
| `vision_config` | depth 27、hidden 1152、out_hidden 2048、patch 16 ⇒ **多模态（带 vision tower）** | 同上 |

- 模型卡 README 直读（ModelScope `README.md`，http=200，64550 B）自述：**"35B in total and 3B activated"**、**"Context Length: 262,144 natively and extensible up to 1,010,000 tokens"**、**"MTP: trained with multi-steps"**、Hidden Layout = 10 × (3 × (Gated DeltaNet → MoE) → 1 × (Gated Attention → MoE))。
- 许可：**Apache-2.0**（README front-matter `license: apache-2.0`；ollama registry 的 license layer 同样是 Apache License 2.0 全文，11357 B，【直证】已拉取核读）。

### 1.2 官方 agentic 分数（【转引】模型卡 HTML 表，本轮亲自读到原文）

| 指标 | Qwen3.6-35B-A3B | 同表对照 |
|---|---|---|
| SWE-bench Verified | **73.4** | Qwen3.5-35BA3B 70.0 / Qwen3.5-27B 75.0 / Gemma4-26BA4B 17.4 |
| SWE-bench Multilingual | 67.2 | Qwen3.5-27B 69.3 |
| SWE-bench Pro | 49.5 | Qwen3.5-27B 51.2 |
| **Terminal-Bench 2.0** | **51.5** | Qwen3.5-27B 41.6 / Qwen3.5-35BA3B 40.5 / Gemma4-31B 42.9 |

> ⚠️ **口径警示**：73.4 / 51.5 是**官方自报**，且 **51.5 是 Terminal-Bench 2.0 口径**。现役 `Qwen3-Coder-30B-A3B-Instruct` 的官方卡（本轮读的 ModelScope README，5425 B）**没有 Terminal-Bench 数字、也没有 SWE 表**（表格是图片）⇒ **"SWE 73.4 / TB 51.5 双超现役"缺少同口径对照，本轮无法核实现役的官方 TB 数字**。前期笔记里的现役 SWE-V 61.4 也**本轮未能独立复核**（HF 不可达、blog 是图片表）。

### 1.3 thinking 行为（【转引】模型卡 + 【直证】ollama 源码）

模型卡明确写：

> **"Qwen3.6 does not officially support the soft switch of Qwen3, i.e., `/think` and `/nothink`. Qwen3.6 will think by default before response."**
> 关闭方式 = `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`；另有 `preserve_thinking` 选项（多轮保留思考，官方称"可减少整体 token 消耗、改善 KV cache 利用"）。
> 官方建议：**"maintaining a context length of at least 128K tokens to preserve thinking capabilities"**。

### 1.4 GGUF 与下载量

| 渠道 | 结果 | 取得方式 |
|---|---|---|
| ollama 官方库 | `qwen3.6:35b` = 23GB–24GB / 256K context / Text+Image / tag id `8a43277aac50`；**库页 qwen3.6 共 7.2M Downloads、35 个 tag** | `curl https://ollama.com/library/qwen3.6/tags` → 解析正文 |
| ollama 其他 tag | `27b`、`27b-coding`、`27b-coding-mtp-q4_K_M`（18GB）、`27b-coding-mxfp8`(MLX)、`27b-coding-nvfp4`(MLX) | 同上 |
| **官方 GGUF** | **未找到**：`https://www.modelscope.cn/api/v1/models/Qwen/Qwen3.6-35B-A3B-GGUF` → `http=404 / record not found` | 【直证】 |
| unsloth GGUF（ModelScope 镜像） | `unsloth/Qwen3.6-35B-A3B-GGUF` 存在（http=200），**Downloads 439,159**（ModelScope 口径＝近 30 天）、license apache-2.0、`BaseModel: Qwen/Qwen3.6-35B-A3B` | 【直证】API |
| unsloth GGUF 文件体积（逐个） | `UD-Q4_K_M` 22,134,528,992 B｜`UD-Q4_K_XL` 22,360,456,160｜`UD-Q4_K_S` 20,893,015,008｜`UD-Q5_K_M` 26,456,194,016｜`Q8_0` 36,903,140,320｜**`MXFP4_MOE` 21,706,144,736**｜`mmproj-F16` 899,283,680 / `mmproj-BF16` 902,822,624 | 【直证】`/repo/files` API，31 个文件 |
| HF 下载量 | **无法核实**（HF 不可达） | — |

### 1.5 ollama registry 体积直读（【直证】）

```
curl -s https://registry.ollama.ai/v2/library/qwen3.6/manifests/35b
→ http=200
{"layers":[
  {"mediaType":"application/vnd.ollama.image.model","size":21718480960,
   "from":"qwen3.6-source:35b-a3b-mtp-q4_K_M-20260824"},
  {"mediaType":"application/vnd.ollama.image.projector","size":902821728, ...},
  {"mediaType":"application/vnd.ollama.image.license","size":11357, ...},
  {"mediaType":"application/vnd.ollama.image.params","size":116, ...}],
 "runner":"llamacpp","format":"gguf"}
```

- config blob（220 B）直读：`{"model_format":"gguf","model_family":"qwen35moe","model_type":"35.5B","file_type":"Q4_K_M","renderer":"qwen3.5","parser":"qwen3.5","requires":"0.30.0"}` ⇒ **ollama 用自研的 qwen3.5 renderer + qwen3.5 工具解析器**。
- params blob（116 B）直读：`{"draft_num_predict":2,"min_p":0,"presence_penalty":1.5,"repeat_penalty":1,"temperature":1,"top_k":20,"top_p":0.95}` ⇒ **draft_num_predict=2（MTP 草稿）**。
- **体积合计**：21,718,480,960 + 902,821,728 = **22,621,302,688 B = 21.07 GiB**（权重 20.23 GiB + 视觉 projector 0.84 GiB）。

---

## 2. 2×V100S-32GB（sm_70）可行性核查

### 2.1 引擎与版本

| 引擎 | 结论 | 证据 |
|---|---|---|
| **ollama 0.40.6（我们已有）** | ✅ 唯一现实路径。实际跑的是 **llama-server runner**：`source=llama_server.go:457 msg="starting llama-server" cmd=".../llama-server --model ... -c 262144 -np 1 --flash-attn auto -b 2048 -ub 2048 --context-shift --keep 4"`（anolis `/data/models/ollama-serve.log`）；`~/.local/lib/ollama/llama-server --version` → **0.7.0-dev (build 1, commit 620d2225c)** | 【直证】anolis 日志 + 进程表 |
| ollama runner 是否认识 qwen35moe | ✅ `strings ~/.local/lib/ollama/libllama.so.0.7.0 \| grep -c qwen35moe` → **51**；含 `src/models/qwen35moe.cpp` 编译路径、`llama_model_qwen35moe5graphE`、`llama_model_qwen35moe9graph_mtpE`、"incomplete qwen35moe MTP expert merge" 等串 | 【直证】anolis |
| sm_70 在这台机上真跑 GPU | ✅ 日志 `ggml_cuda_init: found 2 CUDA devices (Total VRAM: 64988 MiB): Device 0: Tesla V100S-PCIE-32GB, compute capability 7.0` + `load_tensors: offloading 47 repeating layers to GPU`（现役 30B 全量卸载、135.7 tok/s） | 【直证】anolis 日志 |
| llama.cpp 预编译包 | ❌ **不带 sm_70**。第三方实测：官方预编译 `ARCHS = 750,800,860,890,900,1000,1200`，V100 报 `CUDA error: no kernel image is available for execution on the device`；必须自编 `-DCMAKE_CUDA_ARCHITECTURES=70`（且 nvcc 警告 "Support for offline compilation for architectures prior to 'sm_75' will be removed"） | 【转引】miyagadget 2026-07-15 |
| vLLM | ⚠️ 0.19.x 是 V100 最后实用线（issue #47019，closed，2026-06-29；测得 `BLOCK_SIZE_K=128` 在 Volta 上是病态默认值，改 64 后 bit-identical）。社区 fork **1CatAI/1Cat-vLLM**（1366 star，"V100 / SM70-focused vLLM engineering fork"） | 【转引】GitHub |
| SGLang | 官方部署建议 `--tp-size 8`（8 卡），我们 2 卡不现实；且快路径要 sm_80+ | 【转引】模型卡 |

### 2.2 格式在 Volta 上的生死

| 格式 | Volta(sm_70) | 说明 |
|---|---|---|
| Q4_K_M / UD-Q4_K_M（GGUF） | ✅ **唯一现实主力** | 无张量核要求，纯反量化 + F16 计算 |
| BF16 | ⚠️ 可加载但无收益 | Volta 无 BF16 张量核；模型原生 dtype 就是 bfloat16，llama.cpp 会转 F16 |
| FP8 (E4M3) | ❌ 无原生 | sm_89+ 才有；1Cat 只能在 V100 上**软件模拟**（`--kv-cache-dtype fp8` 解析为 E4M3） |
| NVFP4 / MXFP4 | ❌ 无原生加速 | sm_100/sm_120 专属；unsloth 确有 `MXFP4_MOE` GGUF（21.7GB），llama.cpp 可反量化加载但**在 V100 上拿不到任何加速** |
| INT8 / dp4a | ⚠️ 有但非张量核 | 走 dp4a，比 Q4 慢且不省时间 |

### 2.3 显存账（我们这台机器的具体数字）

**权重侧（【直证】registry manifest）**：21.07 GiB（权重 20.23 + projector 0.84）⇒ **单张 V100S-32GB 装得下，余 ~10.9 GiB**。

**KV 侧（本轮自行推算，输入全部是上面直读到的官方 config，方法用现役模型反向校验）**：

- 本模型：只有 10 个 full-attention 层有 KV（40 层 ÷ `full_attention_interval=4`），30 个 Gated DeltaNet 层是**循环状态**、不随上下文增长。
  每 token KV = 2(K,V) × 2 KV 头 × head_dim 256 × 2 B(f16) × 10 层 = **20,480 B = 20 KiB/token**
- 现役 30B：2 × 4 × 128 × 2 × 48 = 98,304 B = **96 KiB/token** ⇒ 与前期笔记里 anolis 日志实测的 **96.0 KiB/token**（2,235.368 MiB ÷ 23,841）**吻合** ⇒ 推算方法自洽。

| 档位 | 本模型 KV（20 KiB/tok） | 现役 KV（96 KiB/tok） |
|---|---|---|
| 32K ctx × 2 slot | 1.25 GiB | 6.0 GiB |
| 128K ctx × 2 slot | **5.0 GiB** | 24 GiB |
| 262K ctx × 2 slot | 10.0 GiB | **48 GiB（实测 49,152 MiB）** |

⇒ 官方建议的"ctx ≥128K 保 thinking"在本机上只要 **5 GiB KV**，而现役 262K×2slot 要 48 GiB（把两张卡顶到 94–95%）。**这是本模型相对现役最实在的工程优势，原结论没有量化。**

**第三方交叉验证**：miyagadget 在 V100-SXM2-32GB 上跑 35B-A3B UD-Q4_K_M（~22GB、无视觉塔）峰值显存 **27.0GB @ ctx 16384** ⇒ 与我们"20.2 GiB 权重 + KV/计算缓冲 ≈ 27GB"的自洽推算同一量级。

**并发形态建议**（推断，未实测）：单卡装得下 ⇒ **两张卡各跑一个独立实例**（而不是拆卡），既无 tensor-split 惩罚，也能把 KV 预算翻倍。

### 2.4 已知坑（必须冒烟的清单）

1. **sm_70 + Gated DeltaNet 家族首请求崩溃**：llama.cpp issue **#29783**（open，2026-10-01，"CUDA: Qwen3.5-122B-A10B (Gated DeltaNet) crashes at first request on sm_70"），机型 6×V100 32GB、`--split-mode layer`，现象是"进入 slot 后 2 秒内死掉，prefill 都没开始"。**上游维护者 JohannesGaessler 2026-10-01 回复：已由 PR #29803 修复**（`merged_at 2026-10-01T19:55:41Z`，标题 "CUDA: fix 2 broken Volta FA cases"，内容："Ampere configs are used for head sizes 320 + 256 which uses too much shared memory and thus causes a crash, this PR adds the missing configs"）。
   - **我们的模型 full-attention head_dim = 256 ⇒ 正是被修的那一档。**
   - **我们 ollama 0.40.6 内置的 fork（commit 620d2225c）是否含该修复，本轮无法核实**：ollama/llama.cpp 的 raw 路径（`src/models/qwen35moe.cpp`、`ggml/src/ggml-cuda/fattn.cu`，main/master/该短 SHA 全 404）+ GitHub API 限流（`403 rate limit exceeded`）。
   - **动作**：上线前必须冒烟；兜底是 `OLLAMA_FLASH_ATTENTION=0`（走非 FA 路径，慢但不吃这个 bug）——注意 ollama 启动参数默认是 `--flash-attn auto`（会走 FA）。
2. **MTP/投机解码的已知崩溃面**（环境既有风险）：ollama 0.40.6 的 llama-server runner 会按 `nextn_predict_layers>0` **自动启用 MTP**（`llm/llama_server.go:863-870`、`:928-934`），并传 `--spec-type draft-mtp --spec-draft-n-max <draft_num_predict=2>`（`:829-847`）⇒ 我们的 35B-A3B 一装上就默认带 MTP 跑，而环境笔记里记着 MTP 在 tensor-split 下的崩溃 issue ⇒ **单卡跑（不拆卡）比双卡拆开更安全**。
3. **视觉 projector 吃 0.84 GiB 且关不掉**：ollama 无 vLLM 的 `--language-model-only` 等价开关；我们是纯文本负载 ⇒ 纯浪费 0.84 GiB + 一段 vision graph（次要）。
4. **thinking 造成的 token 膨胀**：默认 thinking ON，且 `presence_penalty 1.5 / top_k 20 / top_p 0.95` 是官方推荐值（ollama params blob 同款）⇒ 若不关，每题输出 token 会像环境里 m31f 那样爆炸（我们自己实测 30B 臂输出中位 5,756 token；m31f 43,978）。
5. **Unsloth 模板 400**：ollama 0.40.6 的模板会拒绝"结尾 ≥2 条 assistant 消息"的请求（前期已实证 2 次）⇒ 35B-A3B 走的是 ollama 自研 qwen3.5 renderer，**该行为是否仍存在本轮未验证**。

### 2.5 thinking 开关在 ollama 0.40.6 上的完整链路（【直证】源码，这是原结论错得最关键的一处）

ollama v0.40.6 源码逐跳（全部 raw.githubusercontent 直读）：

1. `openai/openai.go:126` `ReasoningEffort *string \`json:"reasoning_effort,omitempty"\`` ⇒ **OpenAI 兼容请求体接受 `reasoning_effort`**。
2. `openai/openai.go:585-615 ThinkingFromReasoningEffort`：`""` → `nil`（用模型默认）；**`"none"` → `ThinkValue{Value:false}`**；`"minimal"→"low"`；`"xhigh"/"ultra"→"max"`；其余字符串档位若模型声明了具名档则保留，否则回落。
3. `model/renderers/thinking.go:30-45 ResolveThinking`：模型声明了 thinking 描述符时，**bool 值原样透传**（`none` → false 保留）；字符串档位若模型不支持 → 回落 `thinking.Default`；请求未给 → 也回落 Default。
4. 本模型 renderer 声明：`model/renderers/renderer.go:71-72`（family `"qwen3.5"` → `Qwen35Renderer{isThinking: true, emitEmptyThinkOnNoThink: true}`）＋ `model/renderers/qwen35.go:363-367 Thinking()` → `Values {false, true}`、`Default = true`。
5. `model/renderers/qwen35.go:217-219`：`isThinking := r.isThinking; if think != nil && think.Value != nil { isThinking = think.Bool() }`；`types/model/thinking.go` 的 `ThinkValue.Bool()`：**字符串档位一律返回 true**（"named levels request thinking"）。

⇒ **三种请求形态的实际结果**：

| harness 发出 | ollama 解析 | 是否思考 |
|---|---|---|
| 不发该字段（现役 `ReasoningTier::Off`） | `nil` → 回落 Default=true | **开** |
| `"reasoning_effort":"low"/"medium"/"high"`（现役 Low/Medium/High 档） | 字符串档不被 `{false,true}` 支持 → 回落 Default=true（且 `Bool()` 对字符串返回 true） | **开**（不降档） |
| **`"reasoning_effort":"none"`** | `ThinkValue{false}` → 原样透传 → `isThinking=false` | **关** ✔ |

⇒ **harness 侧要改的就一行**：`af/crates/af-harness/src/endpoint.rs:365-372`，把 `ReasoningTier::Off => None` 改成能发出 `"none"`（或给本地档案加一档显式 "none"）。模型卡里的 `chat_template_kwargs:{"enable_thinking":false}` 是 vLLM/SGLang 的玩法，ollama 这条路走 `reasoning_effort` 更直接。

---

## 3. 速度证据（tok/s）

### 3.1 第三方实测（全部本轮亲自读到的原文）

| 来源 | 硬件 | 引擎 / 量化 | decode | 其他 |
|---|---|---|---|---|
| **miyagadget 2026-07-15**（`miyagadget.page/en/blog/2026/07/15/tesla-v100-32gb-qwen36-benchmark-en/`） | **Tesla V100-SXM2-32GB**、driver 580.159.03、CUDA 12.9、Xeon 8260 96 线程 | llama.cpp **自编 sm_70**、unsloth `Qwen3.6-35B-A3B-GGUF:UD-Q4_K_M`（~22GB）、ctx 16384、temp 0、**thinking ON** | **98.8 tok/s**（4 任务：99.02 / 98.60 / 99.14 / 98.54） | prefill 352 tok/s；峰值显存 27.0GB；峰值功耗 206.2W；加载 11.0s |
| 同上（同日同卡对照） | 同上 | Qwen3.6-27B 稠密 Q4_K_M / Q8_0 | 32.9 / 23.4 tok/s | ⇒ MoE 35B-A3B 是稠密 27B 的 **3.0×**（同卡同日，最干净的 MoE-vs-稠密对照） |
| **llama.cpp #28037**（issue，2026-08-30） | **Jetson AGX Xavier（sm_72）**、CUDA 11.4 | Qwen3.6-35B-A3B MoE D=256 GGUF | **20.85 t/s** decode（现"Ampere fallback"路径）；自定义 Volta 配置反而 -5%（19.68） | 作者结论：Volta(m8n8k4) 与 Ampere(m16n8k8) 的 MMA 差距是架构性的，调参补不上 |
| **1CatAI/1Cat-vLLM README**（PR #270） | **4× V100-SXM2-32GB，TP4** | Qwen3.6-35B-A3B **NVFP4**（Volta 无原生 FP4，走 fork 的 Marlin 修） | 116.99 tok/s（无 MTP）→ **174.76 tok/s**（+MTP4，1.49×） | 质量核：GSM8K 122/128、0 invalid；ShareGPT16 120.096 tok/s pure decode |
| **NoRaincheck/coding-agent-evaluations #1**（2026-10-04） | 硬件未注明 | `qwen3.6-35b-a3b-mtp`、pi harness | decode_tps **36.1** | SWE-bench Verified 只跑 **2 题**（50%），n=2 无统计意义 |
| **我们自己的 anolis** | 2×V100S-PCIe-32GB | ollama 0.40.6 / 现役 qwen3-coder-30b | 135.7 tok/s @ num_ctx 8192（真实深度 6–16K 只有 38–40 tok/s） | 参照系；**本轮未跑 Qwen3.6-35B-A3B**（不下载权重） |

### 3.2 速度证据的结论与缺口

- **有第三方实测**，不是"只有作者自报"：最硬的一条是 miyagadget 的 **98.8 tok/s（V100-SXM2，第三方自建 llama.cpp，原文可核）**。
- **但没有一条与我们的条件等价的**：
  - 他们的卡是 SXM2（1530MHz），我们是 **PCIe（1380MHz）**；作者自己说 PCIe **可能慢 ~10%** ⇒ 折算 **≈89 tok/s**（这是**折算**，不是实测）。
  - 他们的 ctx 是 16384，**我们的真实调用深度中位 10,289 / p90 20,830 / p99 28,776**（前期实测）⇒ **同等深度下的速度没有第三方数据**。现役 30B 在 8192 下 135.7 tok/s、到 6–16K 就掉到 38–40 tok/s，说明**深度对速度的影响远大于模型间差异**。
  - 他们的引擎是**自编 llama.cpp**；我们是 **ollama 自带 runner**（不同构建、不同 FA 路径）。
- ⇒ **"35B-A3B 会比现役快"在本轮仍然没有被证据支持**：98.8（ctx16K、thinking ON、SXM2、自编）vs 我们 135.7（ctx8192、ollama、非 thinking 的 30B）是**不可直接比的两组数**。要下结论只有一条路：在 anolis 上装上、同样 ctx 档、同样 harness 形态实测。

### 3.3 待验证假设（MoE 更快）的裁决

| 假设 | 裁决 | 依据 |
|---|---|---|
| "总参大但激活少的 MoE 比稠密 27B 快" | ✅ **成立** | miyagadget 同卡同日同引擎：35B-A3B 98.8 vs 27B Q4_K_M 32.9 = **3.0×**（第三方案 1Cat：4×V100 TP4 上同族 35B-A3B NVFP4 116.99 vs Qwen3.6-27B-AWQ+MTP4 100.56，同量级） |
| "MoE 比现役 30B-A3B 快" | ⚠️ **未证实** | 同为 3B 激活 ⇒ 每 token 权重字节同量级；MoE 侧还有 256 专家 vs 现役 128 专家的散点读劣势。98.8 vs 135.7 的方向相反，但 ctx/引擎/卡型都不同 ⇒ 不可比 |
| "MoE 相对稠密的优势在 V100 上更大" | ✅ 支持 | llama.cpp #28037：Volta 走 Ampere FA fallback，架构差距拉大 |

---

## 4. 质量证据（是否有第三方独立复现 agentic 分数）

**结论：没有。本轮未找到任何第三方对 Qwen3.6-35B-A3B 复现过 SWE-bench Verified 或 Terminal-Bench。** 找到的第三方材料全部是下面这四类，都不能当作官方分的复现：

| 类型 | 来源 | 内容 | 能否复现官方分 |
|---|---|---|---|
| **负面报告（未解决）** | SWE-agent issue **#1497**（open，2026-08-10）"0% Pass@1 on SWE-Bench Verified using mini-SWE-agent and Qwen3.6-35B-A3B" | H200 + vLLM，ReAct 基线，20/50/100 题子集**全 0**；报告者自述"no clue how to benchmark using mini-SWE-agent"；**评论数 0，无人解答** | ❌ 不能（更像 harness/格式不匹配，但**不能排除模型在弱 harness 下的真实可用性问题**——这恰恰是我们 harness 形态的风险） |
| **微基准（衍生版）** | cnblogs `Fzeng/p/19938294`（2026-04-27） | 4090 上 9 模型横评；参评的是 **Qwen3.6-35B-A3B-Uncensored（衍生版，非官方权重）**；题量 GSM8K 20 + BBH 20 + HumanEval+ 10 + MBPP+ 10；总分 0.9125（并列第 4）、平均时延 100.35s、执行失败率 0.05 | ❌ 不能（非官方权重、非 agentic、样本极小） |
| **小样本 agentic** | NoRaincheck/coding-agent-evaluations #1（2026-10-04） | `qwen3.6-35b-a3b-mtp` 在 leaf/opencode/pi 三个 harness 上跑 SWE-bench Verified，**每个 harness 只有 2 题**，均 50% | ❌ 不能（n=2） |
| **非 agentic 质量核** | 1Cat-vLLM PR #270 | GSM8K **122/128**、0 invalid、0 repetitive（4×V100 TP4 + MTP4） | ❌ 不能（非 agentic） |

⇒ **官方 73.4 / 51.5 目前是孤证**。另外要注意：即便官方分成立，它**仍然低于我们 API 主力臂的前期锚点**（GLM-5.3-Flash SWE-V 92%、DeepSeek V4 Flash 88.8%），所以**换本地模型不改变"本地臂是弱模型档"的定位**——这与前期结论一致。

---

## 5. 对原结论的逐条修正

| # | 原结论（our-workload.md / local-vs-api.md） | 复核裁定 | 修正后表述 |
|---|---|---|---|
| 1 | "harness 的 OpenAI 协议路径也不传 `reasoning_effort`/thinking 开关 ⇒ **没有旋钮可关**，token 必然膨胀" | ❌ **错（前半对、后半错）** | ollama 0.40.6 的 OpenAI 层**支持** `reasoning_effort`：`"none"` → `ThinkValue{false}`（`openai/openai.go:585-590`）；qwen3.5 家族 renderer 用 `think.Bool()` 决定是否输出 `<think>`（`model/renderers/qwen35.go:217-219`）⇒ **发 `reasoning_effort:"none"` 就能关**。**补充闭环证据**：`model/renderers/thinking.go:30-45 ResolveThinking`（bool 值原样透传；字符串档位若模型不支持则回落到 `thinking.Default`；nil 也回落到 Default=**true**）＋ `types/model/thinking.go` 的 `ThinkValue.Bool()`（字符串档位一律返回 **true**，"named levels request thinking"）⇒ 三种情形逐一坐实：**不发字段 ⇒ thinking 开**；**发 "low"/"medium"/"high" ⇒ 仍是开**（本模型只声明 `{false,true}`，字符串档位不被支持 → 回落 Default=true）；**只有发 "none" ⇒ 关**。**要改的是 harness**：`af/crates/af-harness/src/endpoint.rs:365-372` 把 `ReasoningTier::Off` 映射成"不发字段"，应改成发 `"none"`。**另外**：harness 现有的 Low/Medium/High → `"low"/"medium"/"high"`，而本模型 renderer 的 `Thinking()` 只声明 `{false, true}`（`qwen35.go:363-367`）⇒ 这三档会被解析成**布尔 true（照开 thinking）**，**不产生任何降档效果**；对本模型只有 `"none"` 有效 |
| 2 | "SWE 73.4 / TB 51.5 **双超**现役" | ⚠️ **降级** | 73.4/51.5 是**官方自报**（已直读模型卡核对无误）；但 51.5 是 **Terminal-Bench 2.0** 口径，而现役 30B-A3B 官方卡**没有 TB 数字**（本轮读的卡是图片表，HF 不可达）⇒ **"双超"缺乏同口径对照，本轮无法核实**，应写成"官方自报更高，但无同口径第三方对照" |
| 3 | "单卡 20.2 GiB 装得下（余 ~10 GiB 给 KV）" | ✅ 数字对，但不完整 | 权重 20.23 GiB ✔；**ollama 的 35b tag 还带 0.84 GiB 视觉 projector**（manifest 实测）⇒ 合计 **21.07 GiB**，余 ~10.9 GiB；且**视觉塔在 ollama 里关不掉**（无 `--language-model-only` 等价物），对纯文本负载是纯浪费 |
| 4 | （原结论**完全没提** MTP） | ➕ **补** | ollama 的 `qwen3.6:35b` **本身是 MTP 构建**（manifest `from = 35b-a3b-mtp-q4_K_M-20260824`；params `draft_num_predict=2`），且 ollama 0.40.6 会**自动启用**（`llm/llama_server.go:863-870, 928-934`）⇒ 有机会白捡 1.3–1.5×（第三方 4×V100 上 116.99→174.76）。**我们没跑过**，且环境已记 MTP 崩溃 issue ⇒ 属"必须冒烟"的项 |
| 5 | （原结论**没有量化 KV 优势**） | ➕ **补** | 本模型 KV **20 KiB/token**（10 个 full-attn 层 × 2 头 × 256 × f16），现役 96 KiB/token ⇒ **省 4.8×**；官方建议的 ctx≥128K 只需 5.0 GiB KV（2 slot），而现役 262K×2slot 要 48 GiB。**"两卡各跑一个独立实例、单卡装得下"因此成立** |
| 6 | "同族 sm_70 崩溃 issue（#29783）**未修**，必须冒烟" | ⚠️ **口径要改** | #29783 至今 **open**，但上游维护者 2026-10-01 评论称**已由 PR #29803 修复**（Volta FA 缺 head 320/256 配置）。**我们 ollama 内置的 fork（620d2225c）是否含该修复，本轮无法核实**（fork raw 路径取不到、API 限流）⇒ 表述改为"**上游称已修，我方构建是否含修复未核实**"；因本模型 head_dim=256 且启动带 `--flash-attn auto` ⇒ **冒烟必测，兜底 `OLLAMA_FLASH_ATTENTION=0`** |
| 7 | "V100-SXM2 第三方 98.8 tok/s"（转引 notes/qwen-family.md） | ✅ **数字核实无误**（本轮亲自读了原文） | 98.8 tok/s = 4 任务均值（99.02/98.60/99.14/98.54），V100-SXM2、自编 sm_70 llama.cpp、UD-Q4_K_M、ctx 16384、thinking ON、temp 0。**但作者自述 PCIe 约慢 10%** ⇒ 折算 ≈89 tok/s（折算值，非实测）；且**ctx 16384 ≠ 我们的真实深度 10–32K** |
| 8 | "速度证据为【转引】、本轮未外网复核" | ✅ 本轮已补上外部复核 | 另新增两条第三方：llama.cpp #28037（Jetson Xavier sm_72、**20.85 t/s**、明确说 Volta FA 走 Ampere fallback 且调参无效）与 1Cat-vLLM README（4×V100 TP4、NVFP4 116.99 → +MTP4 174.76、GSM8K 122/128） |
| 9 | "Qwen3.6-35B-A3B 是**最该打榜的一档**" | ✅ **维持** | 理由比原结论更强：单卡装得下（21.07 GiB）+ KV 省 4.8× + thinking 开关**其实有旋钮**（改 harness 一行）+ 第三方 98.8 tok/s。**但必须把"官方 73.4"当待验假设**，用我们自己的 af-bench 打榜再定 |
| 10 | 隐含："本地池是弱模型档、主力走 API" | ✅ **维持** | 即便官方 73.4 成立，仍低于 API 锚点（GLM-5.3-Flash SWE-V 92%）；且本轮补到一条**第三方负面数据**（SWE-agent #1497：mini-SWE-agent 下 0%），提示**弱 harness 形态下本模型可能反而不如现役的非思考 30B**——这正是"先在我们自己的 harness 上测"的理由 |

---

## 6. 本轮未能核实 / 未跑的清单（明确交代）

| 项 | 状态 | 原因 |
|---|---|---|
| HF 官方仓库的下载量、官方是否发布 GGUF | **无法核实** | huggingface.co 本轮 `http=000`（连接失败）；ModelScope 上 `Qwen/Qwen3.6-35B-A3B-GGUF` = 404 |
| 现役 qwen3-coder-30b 的官方 SWE-V / Terminal-Bench 数字 | **无法核实** | ModelScope 卡是图片表；HF 不可达；blog（qwenlm.github.io / qwen.ai）是 SPA 或图片表 |
| ollama 0.40.6 内置 llama.cpp fork 是否含上游 PR #29803 | **无法核实** | ollama/llama.cpp 的 raw 路径（多个候选路径 + 短 SHA 620d2225c）全 404；GitHub API `403 rate limit exceeded` |
| Qwen3.6-35B-A3B 在我们 2×V100S 上的任何实测（tok/s、显存、崩溃与否） | **未跑** | 纪律不下载模型权重 |
| ollama 0.40.6 的 qwen3.5 renderer 在"结尾连续 assistant"时是否仍 400 | **未验证** | 需装模型实测 |
| ollama 的 `/api/show` 对该模型上报的 thinking capability 字段 | **未跑** | 需先 pull 模型 |
| MXFP4 GGUF 在 llama.cpp/V100 上是否能加载并给出什么速度 | **未验证** | 只有文件存在性证据（unsloth 21.7GB MXFP4_MOE） |
| 1Cat-vLLM 的 NVFP4-on-Volta 具体实现（是否纯软件模拟） | 部分核实 | README 自述为 fork 的 Marlin 修；实现细节未逐行读 |

---

## 7. 建议的下一步（不改动原结论，只给复核者的行动建议）

1. **冒烟（约 1 小时，零风险）**：`ollama pull qwen3.6:35b` → 起单卡实例（不拆卡）→ ①能否 load（FA/head_dim 256 会不会崩）②`/v1/chat/completions` 发 `reasoning_effort:"none"` 看 `<think>` 是否消失 ③开/关 MTP 各测一次 tok/s ④`nvidia-smi` 看峰值显存与 KV 实际值。
2. **若冒烟通过**：先改 harness（`endpoint.rs:365-372`：`Off` → 发 `"none"`；并给本地档案一个能表达"none"的档位），再在 af-bench 上用**同一题集**打榜，与现役 30B 臂做同代对照。
3. **若崩**：先 `OLLAMA_FLASH_ATTENTION=0` 排除 FA 路径；仍崩则本模型在 ollama 0.40.6 + sm_70 上不可用，回到"调参换定位"的 P0 路线。
4. **无论如何不要**因为"官方 73.4"就改变"本地臂 = 弱模型档 / 并联量产臂"的定位——本轮未找到任何第三方复现该分数，且找到的第三方 agentic 数据是 n=2 与一份 0% 负面报告。

---

## 8. 本轮取到的来源清单

**可达并已直读**
- `https://registry.ollama.ai/v2/library/qwen3.6/manifests/35b`（http=200）+ 其 config/params/license 三个 blob
- `https://www.modelscope.cn/api/v1/models/Qwen/Qwen3.6-35B-A3B` 及 `repo?FilePath=config.json|README.md|generation_config.json`
- `https://www.modelscope.cn/api/v1/models/unsloth/Qwen3.6-35B-A3B-GGUF` 及 `repo/files`（31 个文件逐个大小）
- `https://ollama.com/library/qwen3.6/tags`（7.2M downloads、tag 体积表）
- ollama v0.40.6 源码（raw.githubusercontent）：`openai/openai.go`、`model/renderers/renderer.go`、`model/renderers/qwen35.go`、`types/model/thinking.go`、`template/template.go`、`server/prompt.go`、`llm/llama_server.go`
- upstream llama.cpp master：`src/models/qwen35moe.cpp`（`full_attention_interval` / 40→LLM_TYPE_35B_A3B）、`ggml/src/ggml-cuda/fattn.cu`（head 320/256 分支、Volta 分支）
- anolis 只读：`/data/models/ollama-serve.log`、`~/.local/lib/ollama/`、`strings` 结果、`nvidia-smi`、`ps`
- 本工作区：`af/crates/af-harness/src/endpoint.rs:187-213, 365-380`、`af/crates/af-harness/src/spec.rs:28-33`

**外部页面（已读原文）**
- `https://miyagadget.page/en/blog/2026/07/15/tesla-v100-32gb-qwen36-benchmark-en/`（98.8 tok/s 全表 + 复现步骤 + 局限声明）
- `https://github.com/ggml-org/llama.cpp/issues/29783` 及其评论（sm_70 崩溃 + "已由 #29803 修复"）
- `https://github.com/ggml-org/llama.cpp/issues/28037`（Volta FA 分析 + Xavier 上 20.85 t/s）
- `https://github.com/ggml-org/llama.cpp/pulls/29803`（修复内容与合并时间）
- `https://github.com/vllm-project/vllm/issues/47019`（0.19.x 是 V100 最后实用线；BLOCK_SIZE_K 64）
- `https://raw.githubusercontent.com/1CatAI/1Cat-vLLM/main/README.md`（Qwen3.6-35B-A3B NVFP4 116.99/174.76 tok/s 等 V100 表）
- `https://github.com/SWE-agent/SWE-agent/issues/1497`（0% Pass@1 负面报告，0 评论）
- `https://github.com/NoRaincheck/coding-agent-evaluations/issues/1`（n=2 agentic + decode_tps）
- `https://www.cnblogs.com/Fzeng/p/19938294`（4090 九模型横评）

**不可达**
- `huggingface.co` / `hf-mirror.com`（http=000）、`ollama/llama.cpp` 的 raw 路径（404）、GitHub API（限流 403）、Bing/DDG 搜索结果页（返回与查询无关的假结果，不采信）
