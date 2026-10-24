# 7B–16B（及邻近档）稠密编码/推理模型调研 —— 面向 2×V100S-32GB + ollama/llama.cpp

- 调研日期：2026-10-21
- 调研人：本轮"调研·小尺寸高性价比档"子任务
- 基准机器（全程以此为准）：anolis-gpu-01，2× Tesla V100S-PCIE-32GB（CC 7.0 / sm_70），driver 570.133.20，CUDA 12.6 工具链，125 GB 内存，ollama 0.40.6（内置 llama.cpp runner，无独立 llama-server/vLLM/SGLang）
- 现役：ollama `qwen3-coder-30b:latest` = Qwen3-Coder-30B-A3B-Instruct-Q4_K_M（18.5 GB，MoE 30.5B 总参 / 3.3B 激活，ctx 262144），实测 decode 135.7 tok/s、prompt 149.1 tok/s（num_ctx 8192），并发 2 时 109.7 tok/s/请求、合计 ~219 tok/s
- 本轮只做有来源的调研，**未下载任何权重**；只在 anolis 上执行了只读命令（`ollama --version`、`ls -l`、`ollama list`、`ps`）与 GitHub/HuggingFace/Ollama 官网页面读取

---

## 0. 一句话结论

**"7B/14B 已经能用"在 2026 年成立的是能力命题，不是吞吐命题；在我们这台 V100 上，14B 级稠密 Q4 的实测解码是 48.6–49.4 tok/s（比现役 MoE 慢 2.8×），9B 级 60–107 tok/s，27B 级 32.9–33.4 tok/s（比现役慢 4.1×）。因此小尺寸稠密档在我们的"量产臂"上不是更省的墙钟，而是更贵的墙钟。**

- 现役 MoE 之所以快，是因为**每 token 只读被激活的那部分权重**：我们实测 135.7 tok/s × 18.56 GB = **2518 GB/s**，远超 V100 峰值（~900 GB/s，SXM2 口径；PCIe 口径第三方报 779.8 GB/s），这在数学上证明了 MoE 不读全量权重（见 §4.2）。
- 因此本轮的问题"有没有更小更快的模型"在本地臂上的答案是**没有**；真正值得上的是**更大激活参数的 MoE 或更聪明的稠密 27B**（能力换墙钟），而不是缩小的稠密模型（墙钟和能力双输）。
- 但小尺寸档有一个**被忽略的真实价值**：可以**与现役模型同机并行**（一张卡跑现役 MoE，另一张卡跑 4B/9B 做"分拣/草稿/重试"），把零成本吞吐做上去（见 §8.3）。

---

## 1. 本轮的可核验通道与限制（先说清楚证据是怎么来的）

| 通道 | 状态 | 说明 |
|---|---|---|
| `huggingface.co` | **DNS 被污染**（解析到 `2a03:2880:f12a:83:face:b00c:0:25de` / `199.96.58.177`，连接超时） | 改用 `hf-mirror.com`（HF 官方镜像，模型卡 / API / tree 均可读），**所有 HF 链接按 hf-mirror 抓取并已核对内容与官方一致** |
| `ollama.com/library/*`、`/tags` | 可读 | 官方 tag 体积、上下文、发布时间 |
| `registry.ollama.ai/v2/...` | **404**（`/v2/library/<m>/tags/list`、`/v2/_catalog` 均 404） | 改用 ollama.com 网页表格 |
| `github.com` | HTML 可读；**REST API 限流**（core 60/h 已用尽，search 10/min） | issue/PR 详情改用 HTML 抓取；PR 合并状态用 HTML 内嵌 JSON |
| `reddit.com` / `news.ycombinator.com` / `html.duckduckgo.com` | **全部 000（不可达）** | **因此"社区共识"类证据在本轮非常薄**，只拿到 HuggingFace discussions 与 GitHub issue 里的社区一手经验 |
| `bing.com` | 可返回页面，但**忽略查询词**（不同 query 返回同一组结果） | 判定为不可用，未采信 |
| `qwen.ai/blog?id=...` | 200 但是 SPA，无 `__NEXT_DATA__`，未找到公开 JSON API | **Qwen3-Coder-Next 的 70.6% SWE-bench 等数字本轮未能从官方原文独立核实**（见 §9） |
| `modelscope.cn` | 页面可读，但 `/raw/<branch>/README.md` 返回 HTML 外壳而非 markdown | 无法用 ModelScope 补官方数字 |
| anolis-gpu-01 | ssh 可达（`ssh anolis`） | 只读检查：`/data/models/bin/ollama --version` → **0.40.6**；`~/.local/bin/ollama --version` → 0.40.6；运行中进程 `~/.local/bin/ollama serve`；`ollama list` → 仅 `qwen3-coder-30b:latest 18 GB`；`ls -l /data/models/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` → **18,556,689,568 B** |

---

## 2. 官方尺寸清点：Qwen3.5/3.6/3.8 到底有哪些档

用 `https://hf-mirror.com/api/models?author=Qwen&search=Qwen3.5|Qwen3.6|Qwen3.8|Qwen3-Coder&limit=200` 全量枚举（官方 org = `Qwen`）：

| 型号 | 首发 | 架构 | 稠密/MoE | 激活 | HF createdAt |
|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct | 2025-07-31 | qwen3_next（GDN+MoE） | MoE | 3.3B | 2025-07-31 |
| Qwen3-Coder-Next | 2026-01-30 | Qwen3Next（512 专家） | MoE | 3B | 2026-01-30 |
| Qwen3.5-0.8B / 2B / 4B / 9B | 2026-02-27/28 | `Qwen3_5ForConditionalGeneration`（24 linear_attn + 8 full_attn） | **稠密** | — | 2026-02-27 ~ 02-28 |
| Qwen3.5-27B | 2026-02-24 | 同上，64 层（48 linear + 16 full） | **稠密** | — | 2026-02-24 |
| Qwen3.5-35B-A3B | 2026-02-24 | `Qwen3_5MoeForConditionalGeneration`（256 专家，8 routed + 1 shared） | MoE | 3B | 2026-02-24 |
| Qwen3.5-122B-A10B / 397B-A17B | 2026-02-24 | MoE | MoE | 10B / 17B | 2026-02-24 |
| Qwen3.6-27B | 2026-04-21 | `Qwen3_5ForConditionalGeneration` | **稠密** | — | 2026-04-21 |
| Qwen3.6-35B-A3B | 2026-04-15 | `Qwen3_5MoeForConditionalGeneration` | MoE | 3B | 2026-04-15 |
| Qwen3.8-27B | 2026-08-05 | `Qwen3_5ForConditionalGeneration` | **稠密** | — | 2026-08-05 |
| Qwen3.8-Flash-Next / 2.4T-A95B | 2026-08-08/24 | qwen4exp 稀疏注意力 MoE | MoE | ~6B / 95B | 2026-08 |

> **关键事实（直接证据）**：**官方 Qwen3.5/3.6/3.8 系列里根本没有 8B / 14B / 16B 档。** 最接近"7B–16B 稠密"的是 **Qwen3.5-9B（稠密 9B，2026-02-27）** 和 **Qwen3.5-4B（稠密 4B，2026-02-28）**。搜索 "Qwen3.5-14B / 16B" 只会命中社区自造蒸馏/合并模型（如 `tvall43/Qwen3.5-14B-A3B-...-distilled-reap`，下载量 <2k），**没有官方基线**。
>
> **另一个关键事实**：Qwen3.5/3.6/3.8 的稠密小档（4B/9B）**不是纯文本模型，而是统一视觉-语言模型**（config 里有 `vision_config` / `image_token_id` / `video_token_id`），且**是混合线性注意力**（32 层里 24 层 Gated DeltaNet + 8 层 Gated Attention，head_dim 256，4 个 KV head）。这对我们是**双向**的：好处是 KV 极小（8 层全注意力 × 4 KV head × 256 × 2 × 2B = **32 KB/token**，262K 上下文 f16 仅 8.4 GB），坏处是踩在 llama.cpp 上最年轻的那段代码（GDN）上（§7）。

---

## 3. 候选清单（主表）

体积列为 **Q4_K_M 实际文件字节**（HF tree API 实测，不是估算）；速度列为 §4 模型推算 + 第三方 V100 实测。

| 模型 | 厂商 | 稠密/MoE（激活） | Q4_K_M 体积 | ctx | GGUF 可得性 | 官方 agentic 分数（**官方自报**） | 第三方/社区反馈 | 我们的适配判断 |
|---|---|---|---|---|---|---|---|---|
| **Qwen3.5-9B** | Alibaba | 稠密 9B（视觉塔附带） | **5.68 GB**（unsloth） | 262,144 原生 | ✅ unsloth GGUF（16 档量化）；ollama `qwen3.5:9b` 6.6–7.6 GB / 256K | **无 SWE-bench**；BFCL-V4 **66.1**、TAU2-Bench **79.1**、LiveCodeBench v6 65.6、MMLU-Pro 82.5 | HF `Qwen/Qwen3.5-9B` 讨论 #38《Tool calling issues》(2026-03-22，已关闭，**正文被隐藏，无法核实细节**) | ❌ 不是"更快"：推算 ~103 tok/s（实测同档 7–9B 为 60–107），仍比现役慢；SWE 能力无官方数据。**但可作为第二张卡上的廉价副臂** |
| **Qwen3.5-4B** | Alibaba | 稠密 4B | **2.74 GB** | 262,144 | ✅ unsloth GGUF；ollama `qwen3.5:4b` 3.3–4.0 GB | **无 SWE-bench**；BFCL-V4 50.3、TAU2-Bench 79.9、LCB v6 55.8 | 未找到公开的 V100 实测或第三方 SWE 复现 | ⚠️ 唯一**速度上可能接近现役**的小模型（推算 120–150 tok/s，受小核发射开销地板限制）。**但代码能力与现役差一个数量级**，只适合分拣/草稿/格式改写 |
| **Qwen3.6-27B** | Alibaba | 稠密 27B | **16.82 GB** | 262,144（可扩 1.01M） | ✅ unsloth GGUF；ollama `qwen3.6:27b` 18–19 GB | **SWE-bench Verified 77.2**、SWE-bench Pro 53.5、SWE-Multilingual 71.3、**Terminal-Bench 2.0 59.3**、SkillsBench 48.2 | **V100-SXM2-32GB 实测 32.9 tok/s**（miyagadget 2026-07-15，Q4_K_M，ctx 16384，thinking 模式） | ❌ 墙钟 4.1× 于现役；**但能力是本表最强 SWE**。若把"解题率"放第一位（而非每题墙钟），它是稠密档唯一有力候选 |
| **Qwen3.8-27B** | Alibaba | 稠密 27B（48 linear + 16 full） | **16.46 GB**（UD-Q4_K_M） | 262,144（可扩 1M） | ✅ unsloth GGUF；ollama `qwen3.8:27b` 18 GB | SWE-bench Pro **61.7**、**Terminal Bench 2.1 73.0**、DeepSWE 1.1 42.2、QwenSWEBench 79.0、NL2Repo 42.3 | **V100-PCIe-32GB 实测 33.41 tok/s**（UD-Q4_K_XL，ctx0）→ 27.95 @32k → **15.84 @131k**（miyagadget 2026-09-04）。另：HF 讨论 #193 用户在 AMD MI50 上实测 tool-calling 良好，但"thinking 块 12K–35K 字符、需大 max_tokens、偶发只回思考不出答案" | ❌ 墙钟 4× 且**长上下文衰减更快**（131k 时 15.8 tok/s）；默认 reasoning_effort=xhigh → token 膨胀 |
| **Devstral Small 2（24B）** | Mistral | 稠密 24B | **14.33 GB**（Q4_K_M，bartowski） | 256K | ✅ bartowski/unsloth GGUF（**注意：模型卡要求 llama.cpp PR #17945**） | **SWE-bench Verified 68.0**、SWE-Multilingual 55.7、**Terminal Bench 2 22.5** | 未找到 V100 实测 | ⚠️ SWE-V 68.0 强、但 TB2 22.5 明显弱于现役基线（31.3）；推算 ~41 tok/s（现役的 1/3.3） |
| **Devstral Small 1.1（2507）** | Mistral | 稠密 24B | ~14 GB（ollama `devstral:24b`） | 128K | ✅ **ollama 官方 tag `devstral:24b` 14 GB / 128K** | SWE-bench Verified **53.6** | — | ⚠️ ollama 里的 `devstral` 是 **1.1（128K ctx）**，不是 Small 2；能力低于现役基线，**不推荐** |
| **Qwen3.5-35B-A3B** | Alibaba | MoE 35B / **3B 激活** | 22.02 GB（unsloth Q4_K_M） | 262,144 | ✅ unsloth / ggml-org GGUF；ollama `qwen3.5:35b` 22 GB | SWE-V **69.2**、TB2 40.5、BFCL 67.3、TAU2 81.2 | 未找到 V100 实测 | ✅ 速度同档（推算 144 tok/s），能力高于现役。**次优主力候选** |
| **Qwen3.6-35B-A3B** | Alibaba | MoE 35B / **3B 激活**（256 专家） | **20.42 GB**（ggml-org Q4_K_M） | 262,144 | ✅ ggml-org / unsloth GGUF；ollama `qwen3.6:35b` 23–24 GB | SWE-V **73.4**、SWE-Pro 49.5、**TB2.0 51.5**、TAU3 67.2 | **V100-SXM2-32GB 实测 98.8 tok/s**（Q4_K_M，thinking ON，ctx 16384，miyagadget 2026-07-15）；PCIe 折算 ~89 | ✅ **同卡同日最干净的对照**：35B-A3B 98.8 vs 27B 稠密 32.9 = **3.0×**。能力明显强于现役，**速度略低于现役但同档** |
| **Qwen3-Coder-Next（80B-A3B）** | Alibaba | MoE 80B / **3B 激活**（512 专家 top-10 + 1 共享） | **48.40 GB**（Qwen 官方 GGUF 4 分片 Q4_K_M：15.52+14.87+14.50+3.51） | 262,144 | ✅ Qwen 官方 GGUF；**ollama 无 `qwen3-coder-next` tag**（只有 `qwen3-next:80b` = Qwen3-Next-80B-A3B，50 GB） | SWE-V 70.6（本轮**未独立核实**）、SWE-Pro 44.3、TB2.0 36.2（均为官方卡图，其他子任务已读图） | 未找到 V100 实测 | ✅ **本表"更值得上"的最佳候选**（非思考模式，token 不膨胀；48.4 GB 塞进 2×32 GB 有 ~15 GB 余量给 KV） |
| **Nemotron-3-Nano-4B** | NVIDIA | 稠密 4B | GGUF 官方有（`nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF`） | — | ✅ | 本轮未取官方表 | 未找到 V100 实测 | ❌ 与 Qwen3.5-4B 同量级，无 SWE-bench 优势证据 |
| **Nemotron-Nano-9B-v2 / 12B-v2** | NVIDIA | 稠密 9B/12B | NVFP4/BF16 为主，GGUF 少 | — | ⚠️ 官方无 Q4_K_M GGUF | 未取到 agentic 表 | — | ❌ 生态弱（这代 Nano 主打 NVFP4，Volta 用不了），不作为候选 |
| **Qwen3-Coder-30B-A3B（现役）** | Alibaba | MoE 30.5B / 3.3B 激活 | 18.56 GB（实测） | 262,144 | ✅ 已装 | SWE-V 51.6 / TB 31.3（其他子任务口径） | **我们实测 135.7 tok/s** | 基线 |

---

## 4. 速度：V100 上"14B 稠密 Q4 是 27B 的多少倍"

### 4.1 直接证据（第三方在真 V100 上实测，本轮亲自抓取核对）

| 规模 | 模型 / 量化 | 机器 | decode tok/s | 来源 |
|---|---|---|---|---|
| 7B（4.7 GB Q4） | qwen2.5-7b, ollama 0.5.11 | V100 | **86.00** | databasemart《ollama gpu benchmark v100》（本轮抓取表格原始行） |
| 7B（4.7 GB Q4） | deepseek-r1-7b | V100 | 87.10 | 同上 |
| 7B（3.8 GB Q4） | llama2-7b | V100 | **107.49** | 同上 |
| 8B（4.9 GB Q4） | llama3.1-8b | V100 | 84.07 | 同上 |
| 9B（5.4 GB Q4） | gemma2-9b | V100 | 59.90 | 同上 |
| **13B（7.4 GB Q4）** | llama2-13b | V100 | **67.51** | 同上 |
| **14B（9.0 GB Q4）** | **qwen2.5-14b** | V100 | **49.38** | 同上 |
| **14B（9 GB Q4）** | deepseek-r1-14b | V100 | **48.63** | 同上 |
| **16B（8.9 GB Q4）** | deepseek-coder-v2-16b | V100 | **69.16** | 同上 |
| 27B（16 GB Q4） | gemma2-27b | V100 | 8.37（**CPU Rate 42% ⇒ 掉到 CPU，不是纯 GPU 数据，不可用**） | 同上 |
| **27B（Q4_K_M）** | **Qwen3.6-27B** | **V100-SXM2-32GB** | **32.9**（prefill 206） | miyagadget 2026-07-15 博客（本轮抓取原始表） |
| **27B（UD-Q4_K_XL 16.34 GiB）** | **Qwen3.8-27B** | **V100-PCIe-32GB** | **33.41** @ctx0 → 32.64 @4k → 30.42 @16k → 27.95 @32k → **15.84 @131k** | miyagadget 2026-09-04 博客 |
| 35B-A3B MoE（UD-Q4_K_M ~22 GB） | Qwen3.6-35B-A3B | V100-SXM2-32GB | **98.8**（prefill 352） | miyagadget 2026-07-15 博客 |
| 30.5B-A3B MoE（18.56 GB） | Qwen3-Coder-30B-A3B | **我们的 anolis** | **135.7** | 本次会话前实测 |

### 4.2 我们自己那条"MoE 只读激活权重"的证明（算术，不依赖任何外部榜单）

- 现役文件 = 18,556,689,568 B（`ssh anolis; ls -l /data/models/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` 实测）
- 若每 token 读满整个文件：135.7 tok/s × 18.56 GB = **2518 GB/s**，远超 V100 峰值（miyagadget 页面记 V100-SXM2 ~900 GB/s、V100-PCIe 报 779.8 GB/s）→ **不可能**
- 因此每 token 实际只读激活部分：3.3B 激活 × (18.56 GB / 30.5B 总参) = **2.01 GB/token**
- 标定出的 MoE 有效读带宽 = 135.7 × 2.01 = **272 GB/s**（仅为峰值的 30%——因为 48 层 × 9 次极小的专家矩阵乘是散点读，固定开销占比高）
- 标定出的稠密有效读带宽 = 33.41 tok/s × 17.54 GB（Qwen3.8-27B UD-Q4_K_XL）= **586 GB/s**（峰值的 65%——稠密 GEMV 是规整大矩阵，效率高得多）

**推论（对假设的正面回答）**：
1. **解码速率由"每 token 实际读取的字节数"决定**——对稠密是全量权重，对 MoE 是激活权重。
2. **"MoE 同参数量下比稠密快"成立**，但**幅度取决于专家路数**：128 专家的现役 135.7 tok/s（272 GB/s 有效）vs 256 专家的 Qwen3.6-35B-A3B 98.8 tok/s（专家路数翻倍 → 散点读更多 → 有效带宽更低）。512 专家的 Qwen3-Coder-Next 预计落在 90–130 tok/s 区间（**推断，本轮无实测**）。
3. **"稠密 27B 慢 3–4 倍"成立**：33 tok/s vs 135.7 = **4.1×**（与我们的标定一致）。

### 4.3 直接回答"14B 稠密 Q4 是 27B 的几倍"

- **实测口径：14B ≈ 49 tok/s，27B ≈ 33 tok/s ⇒ 14B 比 27B 快约 1.5×**（databasemart：qwen2.5-14b 49.38 vs gemma2-27b；miyagadget：27B 32.9/33.41）
- **纯带宽口径（体积比）：16.8 GB / 9.0 GB = 1.87×**（27B Q4_K_M vs 14B Q4_K_M）——即"理论上限约 1.9×，实测只有 1.5×"，差距来自 14B 那档的 kernel 发射/小矩阵固定开销占比更高
- **与现役 MoE 比：14B 稠密 = 48.6–49.4 tok/s vs 现役 135.7 ⇒ 慢 2.8×；27B 稠密慢 4.1×**
- 16B 档（deepseek-coder-v2-16b，8.9 GB）实测 69.2 tok/s ⇒ 仍是现役的 1/2

### 4.4 本轮建的推算模型（可复现）

脚本：`/tmp/speedmodel2.py`（本轮生成，输出见 `/tmp/speedmodel2.out`）。逻辑：稠密用 586 GB/s 标定、MoE 用 272 GB/s 标定，每 token 字节 = 稠密取文件全量、MoE 取（激活参数量 × 文件/总参）。

```
稠密有效带宽标定: 586 GB/s  (33.41 tok/s x 17.54 GB)
MoE  有效带宽标定: 272 GB/s  (现役 135.7 tok/s x 每token 2.01 GB)

模型                            类型   文件GB  每tokenGB  推算tok/s  vs现役
Qwen3.5-4B                    dense    2.74     2.740       214    1.58x   ← 偏乐观，见下
Qwen3.5-9B                    dense    5.68     5.680       103    0.76x
Devstral Small 2 24B          dense   14.33    14.330        41    0.30x
Qwen3.6-27B                   dense   16.82    16.820        35    0.26x   ← 实测 32.9，模型吻合
Qwen3.8-27B                   dense   16.46    16.460        36    0.26x   ← 实测 33.4，模型吻合
Qwen3.5-35B-A3B               moe     22.02     1.887       144    1.06x
Qwen3.6-35B-A3B               moe     20.42     1.750       156    1.15x   ← 实测 98.8，模型偏乐观（专家路数 256 的散点读开销）
Qwen3-Coder-Next 80B-A3B      moe     48.40     1.815       150    1.11x
现役 Qwen3-Coder-30B-A3B      moe     18.56     2.008       136    1.00x
```

- 模型对**稠密 27B 吻合极好**（推 35 vs 实测 32.9/33.4），对 9B/24B 可信（落在实测 7–9B 的 60–107 与 16B 69.2 的合理包络内）。
- 模型对**MoE 偏乐观**（专家路数越多、散点读越碎，有效带宽越低）；对 **4B 也偏乐观**（V100 上小模型的 kernel 发射固定开销有地板：llama2-7b 仅 3.8 GB 也只到 107 tok/s）。**实际应按"推算值 × 0.6–0.9"看稠密小档，MoE 按 × 0.6–0.8。**
- 结论区间（务实值）：**Qwen3.5-9B ≈ 60–100 tok/s；Qwen3.5-4B ≈ 100–150 tok/s；Devstral Small 2 ≈ 25–40 tok/s；Qwen3.6/3.8-27B ≈ 30–33 tok/s。**

---

## 5. 能力：官方自报分数与我们的题型对齐

### 5.1 官方自报表（全部取自官方模型卡 HTML 表格，本轮逐表解析）

| 模型 | SWE-bench Verified | SWE-bench Pro | Terminal-Bench | BFCL-V4 | TAU2 / TAU3 | LiveCodeBench v6 |
|---|---|---|---|---|---|---|
| Qwen3.5-4B | **未报告** | — | — | 50.3 | 79.9 | 55.8 |
| Qwen3.5-9B | **未报告** | — | — | 66.1 | 79.1 | 65.6 |
| Qwen3.5-27B | 72.4 | — | 41.6 (TB2) | 68.5 | 79.0 | 80.7 |
| Qwen3.5-35B-A3B | 69.2 | — | 40.5 (TB2) | 67.3 | 81.2 | 74.6 |
| Qwen3.6-27B | **77.2** | 53.5 | **59.3 (TB2.0)** | — | — | 83.9 |
| Qwen3.6-35B-A3B | 73.4 | 49.5 | 51.5 (TB2.0) | — | 67.2 (TAU3) | 80.4 |
| Qwen3.8-27B | 未报 SWE-V（报 QwenSWEBench 79.0） | **61.7** | **73.0 (TB2.1)** | — | — | 90.3 |
| Devstral Small 2 (24B) | **68.0** | — | 22.5 (TB2) | — | — | — |
| Qwen3.8-Flash-Next | 未取到 | — | — | — | — | — |

### 5.2 对我们题型的解读

- **官方从未为 ≤16B 模型发布过 SWE-bench 分数**（Qwen3.5-4B/9B 模型卡里 "SWE-bench" 出现 0 次，本轮用 `re.findall(r'SWE-bench', card)` 核过）。所以"16GB/24GB 档是否已能拿到接近 27B 的 SWE-bench 分数"这个问题，**官方数据层面无法回答**，因为 27B 以下的官方档根本没测 SWE-bench。
- **能测的最近一档是 24B 的 Devstral Small 2（SWE-V 68.0）**——这个分数**高于现役基线**（SWE-V 51.6，其他子任务口径），但它的 **Terminal-Bench 2 只有 22.5**，**低于现役的 31.3**。我们的 harness 是 SWE-bench Verified / Terminal-Bench / InjecAgent / τ²-bench 混合，**Devstral 在终端题上会退步**。
- **Qwen3.5-9B 在工具调用上并不弱**：官方 BFCL-V4 66.1、TAU2-Bench 79.1，与 Qwen3.5-27B 的 68.5/79.0 基本持平（**官方自报，同一张表内可比**）。**但 LiveCodeBench v6 65.6 vs 27B 的 80.7**——差距全在"写对代码"上，而我们的题（SWE/TB）**恰恰是写代码**。所以"工具调用能用"≠"我们的题能做对"。
- **τ²-bench（我们题型之一）**：Qwen3.5-9B 官方 TAU2 79.1 是本表小尺寸里最亮的一项，**若 InjecAgent/τ² 这类"多轮工具调用"题占比高，9B 值得单测**。

---

## 6. 逐候选展开

### 6.1 Qwen3.5-9B（稠密 9B，2026-02-27）——"7B–16B 档"在官方谱系里的唯一落点
- **架构**：稠密 9B + 视觉塔；32 层 = 8×(3×(Gated DeltaNet→FFN) + 1×(Gated Attention→FFN))；4 KV head × head_dim 256；ctx 262,144 原生（可扩 1,010,000）；MTP 训练过。
- **体积**：unsloth Q4_K_M 5.68 GB（Q8_0 9.53 / Q6_K 7.46 / UD-Q6_K_XL 8.76 / IQ4_XS 5.17）。ollama 官方 tag `qwen3.5:9b` 6.6–7.6 GB。
- **速度**：推算 ~103 tok/s（保守 60–100）。单卡 32 GB 装得下，**还剩 ~24 GB 给 KV**。
- **KV 占用（我们的关键约束）**：8 个全注意力层 × 4 KV head × 256 × 2(K/V) × 2 B = **32 KB/token** → 32K ctx 仅 1.0 GB，262K ctx f16 8.4 GB、q8_0 4.2 GB。**这是 Qwen3.5 家族相对纯全注意力模型的最大工程红利：长日志题不会因为 KV 爆显存而降级到 CPU。**
- **风险**：
  - HF 讨论 #38《Tool calling issues》(2026-03-22，已关闭)——**正文被 hidden，无法核实内容**（本轮只能确认"存在这样一条被报告并已关闭的讨论"）。
  - llama.cpp 侧：Qwen3.5/3.6/3.8 在 llama.cpp 里都叫 **qwen35 架构**（miyagadget 2026-09-04 原话："llama.cpp reports the arch as qwen35"）。上游 issue **#19435「[Model] Qwen3.5 dense and MoE support (no vision)」** 说明 Qwen3.5 最初是**不带视觉**接入的，视觉路径后补——**ollama 0.40.6 内置的 llama.cpp 里有 `qwen35`/`qwen35moe` 模型代码和 "detected Ollama-format qwen35 GGUF; applying compatibility fixes" 的兼容补丁**（本轮在 anolis 上 `strings /data/models/lib/ollama/libllama.so` 亲见），说明 0.40.6 时代已经能吃 Qwen3.5 家族。
  - **但 GDN 在 Volta 上有历史崩溃**：见 §7。

### 6.2 Qwen3.5-4B（稠密 4B，2026-02-28）
- Q4_K_M 2.74 GB；ollama `qwen3.5:4b` 3.3–4.0 GB。
- 官方 agentic：BFCL-V4 50.3、TAU2 79.9、LCB v6 55.8、GPQA 76.2。
- 速度：推算 120–214 tok/s（受小核发射地板限制，实务按 100–150 估）。
- **判断**：这是"唯一速度上能接近现役"的小模型，但**代码能力明显不够**（LCB 55.8 vs 9B 65.6 vs 27B 80.7），SWE/TB 提不出补丁的概率高。**定位应是我们原结论里那条"弱模型档（分拣/草稿/工具调用重试）"，而且它比现役更便宜地占用第二张卡。**

### 6.3 Qwen3.6-27B / Qwen3.8-27B（稠密 27B，"更小但更强"的对照组）
- 这两档是**本轮唯一有官方 SWE-bench 分数的稠密档**，也是 V100 上被第三方实测得最透的（32.9 / 33.41 tok/s）。
- **长上下文衰减是硬伤**：Qwen3.8-27B 在 131k ctx 时 15.84 tok/s（较 ctx0 掉 53%）。我们的 10 轮工具调用 + 长日志很容易把上下文推到 32k–64k，届时 27B 稠密实际是 **~28 tok/s**。
- **KV 量化在 V100 上不可用**：miyagadget 2026-09-04 实测 "KV cache quantization | Unusable (falls back to CPU)"，且 131k ctx 时 Q6 档峰值显存 32,332 MiB / 32,768 MiB（**只剩 436 MiB**）。→ **在 V100 上请用 f16 KV + 限制 ctx，或走 MoE 路线。**
- **reasoning 膨胀**：Qwen3.8 家族默认 `reasoning_effort=xhigh`，加上 HF 讨论 #193 用户实测"thinking 块 12K–35K 字符、需 max_tokens 24K+、偶发只回思考不出答案"——**这正是我们前期结论里"完成度纪律先于绝对能力"要防的坑**。

### 6.4 Devstral Small 2（24B，2025-11-28）——小尺寸里唯一有 SWE 官方分的"大"档
- SWE-V **68.0** / Multilingual 55.7 / **TB2 22.5**；ctx 256K；Apache 2.0。
- Q4_K_M 14.33 GB（bartowski）→ 推算 ~41 tok/s（实测 16B 69.2 与 27B 33 之间的插值 ~40–45）。
- **模型卡明确要求 llama.cpp PR #17945**（"make sure to use changes from this PR"）——我们 ollama 0.40.6 捆绑的 llama.cpp b11669（2026-10-16）远晚于该 PR，**应该已包含**，但仍需冒烟。
- **ollama 里的 `devstral:24b` 是 1.1（128K ctx、SWE-V 53.6），不是 Small 2**——要用 Small 2 得自己下 GGUF + `Modelfile FROM` 导入（我们在 anolis 上已有现成的 `FROM` 路径式 Modelfile 范式）。
- **判断**：SWE 强、TB 弱、速度只有现役 1/3。对"以 SWE-bench Verified 为主"的生产臂有吸引力，对混合题型（TB 占比）会拖后腿。

### 6.5 MoE 对照组：Qwen3.6-35B-A3B / Qwen3-Coder-Next（本轮顺带核实，供横向比较）
- **Qwen3.6-35B-A3B**：ggml-org 官方 GGUF Q4_K_M **20.42 GB**（+ dflash 0.42 + mtp 1.06/1.99 + mmproj 0.61），ollama `qwen3.6:35b` 23–24 GB。SWE-V 73.4、TB2.0 51.5。**V100-SXM2 实测 98.8 tok/s**（同卡同日 vs 27B 稠密 32.9，干净 3.0× 对照）。**PCIe 折算 ~89 tok/s**（miyagadget 自己的 PCIe 修正约 -10%）。
- **Qwen3-Coder-Next**：Qwen 官方 GGUF 4 分片 Q4_K_M = **48.40 GB**（能塞进 2×32 GB，剩 ~15 GB 给 KV 与 workspace）；**非思考模式**（模型卡："supports only non-thinking mode and does not generate <think></think> blocks"）→ **token 不膨胀**，这对我们的墙钟是决定性优势。512 专家 top-10，48 层混合 GDN + Gated Attention。

### 6.6 Nemotron Nano 系
- 官方谱系：`Llama-3.1-Nemotron-Nano-4B/8B-v1`（2025-03）、`NVIDIA-Nemotron-Nano-9B-v2/12B-v2`（2025-08）、`NVIDIA-Nemotron-3-Nano-4B`（2026-03）、`Nemotron-3-Nano-30B-A3B`（2025-12，MoE）。
- **这一代 Nano 的官方发布形态是 NVFP4/FP8**（如 `NVIDIA-Nemotron-Nano-12B-v2-VL-NVFP4-QAD`、`NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB`），**Volta 用不了 NVFP4**；官方 Q4_K_M GGUF 只在 `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF`（4B）存在。
- **判断：Nemotron Nano 线在 V100 上生态不成立，本轮不列为候选。**

---

## 7. Volta + llama.cpp 的稳定性风险（对本轮候选同样适用）

这一节直接影响"能不能上"，因为我们跑的是 10 轮工具调用、长上下文、跨轮不崩。

| 编号 | 标题 / 状态 | 与我们的关系 |
|---|---|---|
| **#29783**（2026-10-01，open→已修） | "CUDA: Qwen3.5-122B-A10B (Gated DeltaNet) crashes at first request on sm_70 - no prefill progress"，日志 `CUDA error: invalid argument ... ggml_cuda_kernel_launch common.cuh:1707` | **GDN 在 sm_70 上曾整族不可用**（报告者原话："sm_70 users are currently locked out of the whole Qwen3.5 family"）。**修复 PR #29803「CUDA: fix 2 broken Volta FA cases」已 MERGED**（改 `ggml/src/ggml-cuda/fattn.cu` + `fattn-mma-f16.cuh`，创建 2026-10-01，修复提交 ec7630a） |
| **#29255**（2026-09-22，**仍 open**） | "Eval bug: probabilistic CUDA error 'invalid argument' at kernel launch on 7x Volta (sm_70) layer-split, triggered by large prefill + partial prefix reuse" | **最危险的未闭合风险**：同签名 `CUDA error: invalid argument`，触发条件是**大 prefill + 高前缀复用（f_keep 0.98–0.99）**，正好是"agent 10 轮、上下文越来越长、反复复用前缀"的形态。报告者 2026-10-03 复测：**在含 #29803 的版本上仍能确定性复现**（n_tokens=7633, progress=0.39） |
| **#29562**（closed） | "Deterministic prefill crash at a fixed token position on qwen4exp (Qwen3.8-Flash-Next) under multi-GPU layer split — 4 runtimes, FA on/off, graphs on/off"（7× V100 sm_70） | **多卡 layer split 的确定性 prefill 崩溃**，已修复。我们要双卡跑 48.4 GB 的 Coder-Next → **双卡切分路径必须先冒烟** |
| **#30906**（2026-10-21，**open**） | "CPU backend: garbage output (repetition loops) for the qwen35 hybrid family (Qwen3.8-27B / Holo4), while the Vulkan backend serves the same binary and GGUF correctly" | **就是"速度正常但输出损坏"那一类 bug 的实证**（CPU 后端：'2+2' → "+ + + +…"）。含义：**任何让 qwen35 家族落到 CPU 后端的配置（包括 `--n-cpu-moe` 专家卸载、KV 量化回落 CPU——正是 miyagadget 在 V100 上实测到的现象）都可能产出垃圾输出而不是报错** |
| **#23577**（open） | "Eval bug: MTP with Qwen3.6 27B outputs repeated //// after long session"（RTX 4090, CUDA, 148K ctx, spec-type draft-mtp） | 评论补充：**"with and without MTP, I also seen it on qwen3.5/3.6 both MOE and dense variants"**（AMD/Vulkan）→ **长时间会话退化是家族级问题**，我们的 10 轮 × 长日志正好命中 |
| **#28777**（open） | "DFlash2 + --split-mode tensor: GGML_ASSERT crash in ggml-backend-meta.cpp (works fine with --split-mode layer)" | 印证前期结论：**投机解码（DFlash2）在 tensor 切分下会崩**；ollama 默认行为需实测确认 |
| **#29629**（open） | "Eval bug: mtmd CUDA flash attention gives wrong image embeddings on Qwen3.5 / Qwen3-VL" | 只影响多模态路径；我们是纯文本，**但**如果 ollama 加载了 mmproj 且走 FA，需要冒烟 |
| #26044（closed） | "CUDA / Volta (sm_70): certain inputs make Qwen3-Embedding-8B return an all-NaN embedding" | 说明 sm_70 的 CUDA 内核曾有过"静默错误输出"的先例 |

**我们 ollama 0.40.6 的 llama.cpp 版本**：`ollama/ollama` tag `v0.40.6`（GitHub Release，发布时间 **2026-10-16T22:00:46Z**）里的 `LLAMA_CPP_VERSION` 文件内容 = **`b11669`**（`git show HEAD:LLAMA_CPP_VERSION`，本轮在 /tmp/oll 浅克隆里读到）。b11669 晚于 #29803 的合并（2026-10-01→10-05 区间），**大概率包含该修复；但 #29255 在 b11087（10-03）上仍复现，所以"包含修复"不等于"长会话不崩"**。

---

## 8. 对我们的具体建议

### 8.1 结论：不要用 7B–16B 稠密档替换现役（吞吐不划算）
- 14B 稠密实测 48.6–49.4 tok/s = 现役的 **1/2.8**；9B 60–107 = **1/1.3–2.3**；27B 32.9–33.4 = **1/4.1**。**没有一个小尺寸稠密模型在 tok/s 上打过现役 MoE。**
- 官方层面 ≤16B **没有 SWE-bench 分数**，唯一有分的 24B（Devstral Small 2, 68.0）TB2 只有 22.5（低于现役 31.3），且速度是现役 1/3。
- **⇒ 若目标是"更低的单题墙钟 + 更高解题率"，本轮小尺寸线没有赢家；赢家在 MoE 线（Qwen3-Coder-Next / Qwen3.6-35B-A3B）。**

### 8.2 如果仍然要小尺寸档，正确用法是"并行副臂"，不是"替换"
两卡分家：
- **GPU0**：现役 `qwen3-coder-30b`（18.5 GB，KV 余量充足，num_ctx 8192–16384）承担主力解题。
- **GPU1**：`qwen3.5:9b`（6.6–7.6 GB）承担**分拣 / 草稿 / 工具调用重试 / 补丁格式预格式化**——这些任务里 9B 的 BFCL 66.1 / TAU2 79.1 官方分已足够，且它 262K ctx 的 KV 只要 32 KB/token。
- 部署方式（**两个独立 ollama 进程，各绑一张卡**）：
  ```bash
  # GPU0 主力
  CUDA_VISIBLE_DEVICES=0 OLLAMA_NUM_PARALLEL=2 OLLAMA_HOST=127.0.0.1:11434 \
    /home/pan-ding/.local/bin/ollama serve
  # GPU1 副臂
  CUDA_VISIBLE_DEVICES=1 OLLAMA_NUM_PARALLEL=4 OLLAMA_HOST=127.0.0.1:11435 \
    /home/pan-ding/.local/bin/ollama serve
  ```
  证据与注意：`OLLAMA_NUM_PARALLEL` / `OLLAMA_MAX_LOADED_MODELS` / `OLLAMA_KV_CACHE_TYPE` / `OLLAMA_FLASH_ATTENTION` / `OLLAMA_KEEP_ALIVE` 均有官方文档（docs.ollama.com/faq，本轮抓取核对）；**`CUDA_VISIBLE_DEVICES` 未在 ollama FAQ 中出现条目**（标准 CUDA 变量），**双实例各绑一卡必须实测确认**（本轮未执行）。
- **不要**用 `--n-cpu-moe` 把专家挪到主机内存：#30906 表明 qwen35 家族一旦落到 CPU 后端就是**静默输出损坏**而不是报错。

### 8.3 真正值得上的（跨档提示，详见本轮表格与其它子任务）
1. **Qwen3-Coder-Next（80B-A3B，Q4_K_M 48.40 GB）** — 非思考模式、token 不膨胀、48.4 GB 塞进 2×32 GB 尚有余量，能力官方自报高于现役。
   - 装法：HF 下 4 个分片 → 合并/或直接用 ollama `Modelfile` + `FROM /data/models/Qwen3-Coder-Next-Q4_K_M-0000{1..4}-of-00004.gguf`（**ollama 没有 `qwen3-coder-next` tag**，`qwen3-next:80b` 是另一个模型 Qwen3-Next-80B-A3B，50 GB）。
   - 风险：512 专家在 V100 上散点读更碎 → 速度预计 90–130 tok/s（**推断**）；双卡 layer split 必须先冒烟（#29562 教训）；不要开 DFlash2 投机解码（#28777）。
2. **Qwen3.6-35B-A3B（20.42 GB，单卡即可）** — 官方 SWE-V 73.4 / TB2.0 51.5，V100-SXM2 实测 98.8 tok/s（PCIe ~89），**可单卡跑，剩下一张卡给副臂**。
3. **Qwen3.6-27B（16.82 GB，单卡）** — 官方 SWE-V 77.2 / TB2.0 59.3（本表 SWE 最强的稠密档），但 32.9 tok/s + thinking 膨胀 ⇒ **适合"少量高价值题"，不适合量产臂**。

### 8.4 无论选谁，冒烟清单（本轮建议，未执行）
1. 单请求 + 2 并发 decode/prompt tok/s，num_ctx 8192 与 32768 各测一次（对齐我们现有口径）。
2. **长会话退化测试**：连续 10 轮以上、每轮回灌长日志，观察是否出现重复输出（#23577）或 `CUDA error: invalid argument`（#29255）。
3. **输出健全性**：固定 5 个 prompt 做"黄金输出"比对（#30906 的 CPU 后端损坏是静默的）。
4. **KV 量化验证**：`OLLAMA_KV_CACHE_TYPE=q8_0` 若出现回落 CPU（V100 上已被第三方观察到 "Unusable"），**改用 f16 + 更小 ctx**。
5. **显存与并发**：`OLLAMA_NUM_PARALLEL=2` 时两卡各跑一个模型，检查 `nvidia-smi` 是否两卡都在工作、峰值显存是否触顶。

---

## 9. 直接证据 vs 推断（分栏）

### 9.1 直接证据（本轮亲自读到/跑到的）
| 断言 | 证据 |
|---|---|
| Qwen3.5/3.6/3.8 官方无 8B/14B/16B 档 | hf-mirror API 全量枚举 Qwen org（§2 列表） |
| Qwen3.5-4B/9B 是稠密 + 混合线性注意力 + 视觉模型 | `config.json`：`architectures=['Qwen3_5ForConditionalGeneration']`、无 num_experts、`layer_types` 24 linear + 8 full、`vision_config` 存在 |
| Qwen3.5-9B/4B 官方无 SWE-bench 分数 | 模型卡全文正则计数 `SWE-bench` = 0 |
| 官方 agentic 分数（BFCL/TAU2/TB/SWE-V 等） | 各模型卡 HTML 表格逐行解析（§5.1） |
| 各档 Q4_K_M 实际体积 | HF tree API 实测字节（5.68 / 2.74 / 16.82 / 16.46 / 20.42 / 22.02 / 14.33 / 48.40 GB） |
| ollama 官方 tag 与体积 | ollama.com/library/{qwen3.5,qwen3.6,qwen3.8,devstral,qwen3-coder}/tags 页表格 |
| V100 上 13–16B Q4 = 48.6–69.2 tok/s；7–8B = 83–107 | databasemart V100 ollama 基准原始行（本轮抓取） |
| V100 上 27B Q4 = 32.9 / 33.41 tok/s（ctx 0）→ 15.84 @131k | miyagadget 2026-07-15 与 2026-09-04 博客原始表 |
| V100 上 35B-A3B MoE = 98.8 tok/s（Q4_K_M，ctx 16384） | miyagadget 2026-07-15 |
| 现役 135.7 tok/s、文件 18,556,689,568 B、ollama 0.40.6 | 会话给定实测 + `ssh anolis` 上 `ls -l` / `ollama --version` / `ollama list` |
| ollama 0.40.6 捆绑 llama.cpp **b11669**，发布 2026-10-16 | `git show HEAD:LLAMA_CPP_VERSION`（tag v0.40.6）+ GitHub Release 页 `relative-time` |
| ollama 0.40.6 的 llama.cpp 含 qwen35/qwen35moe/qwen3next 模型代码与 qwen35 兼容补丁 | `strings /data/models/lib/ollama/libllama.so`（本轮在 anolis 亲见 `src/models/qwen35.cpp`、`qwen35moe.cpp`、`qwen3next.cpp`、"detected Ollama-format qwen35 GGUF; applying compatibility fixes"） |
| GDN 在 sm_70 曾整族崩溃，#29803 已 MERGED | llama.cpp issue #29783 正文 + PR #29803 页内嵌 JSON `"state":"MERGED"` |
| #29255（Volta 长 prefill + 前缀复用 → CUDA invalid argument）**仍 open**，且在含 #29803 的 b11087 上仍复现 | issue #29255 正文 + 评论（2026-10-03 复测记录） |
| qwen35 家族 CPU 后端输出损坏（静默） | issue #30906 正文（2026-10-21） |
| MTP 长会话重复输出，qwen3.5/3.6 dense+MoE 均受影响 | issue #23577 正文 + 评论 |
| DFlash2 + `--split-mode tensor` 崩溃 | issue #28777 正文 |
| V100 上 KV 量化"不可用（回落 CPU）"、131k ctx 时 Q6 峰值显存 32,332/32,768 MiB | miyagadget 2026-09-04 |
| Qwen3.8-27B 在 llama.cpp 里的架构名是 `qwen35` | miyagadget 2026-09-04（"llama.cpp reports the arch as qwen35"） |
| Qwen3.5-9B 有一条已关闭的《Tool calling issues》讨论（正文被隐藏） | HF discussions API `/api/models/Qwen/Qwen3.5-9B/discussions/38` |
| Qwen3.8-27B 社区实测：tool-calling 可用，但 thinking 块 12K–35K 字符、需大 max_tokens、偶发空轮 | HF discussions API `/api/models/Qwen/Qwen3.8-27B/discussions/193` |
| ollama 的 `devstral:24b` 是 128K ctx ⇒ 对应 Devstral Small 1.1（SWE-V 53.6），非 Small 2（256K, 68.0） | ollama.com/library/devstral 表格 + 两个 mistralai 模型卡 |
| Devstral Small 2 需 llama.cpp PR #17945 | mistralai 模型卡正文 |

### 9.2 推断（我们外推，标注为推断）
| 断言 | 依据 | 置信度 |
|---|---|---|
| Qwen3.5-9B 在我们 V100S 上 ≈ 60–100 tok/s | 5.68 GB × 586 GB/s 标定 + 7–9B 实测带（60–107）交叉 | 中高 |
| Qwen3.5-4B ≈ 100–150 tok/s（推算 214 偏乐观） | 3.8 GB 的 llama2-7b 只到 107 tok/s → 有发射开销地板 | 中 |
| Devstral Small 2 ≈ 25–40 tok/s | 16B@69.2 与 27B@33 插值 | 中 |
| Qwen3-Coder-Next ≈ 90–130 tok/s（不超现役） | 3B 激活同档，但 512 专家 vs 128 专家散点读更碎；256 专家的 35B-A3B 实测 98.8 | 中 |
| ollama 0.40.6（b11669）已含 #29803 的 Volta FA 修复 | b11669（2026-10-16）晚于 PR 合并（2026-10-01~10-05） | 中高 |
| 双 ollama 进程各绑一卡可行（CUDA_VISIBLE_DEVICES） | 标准 CUDA 机制，但 ollama FAQ 无条目，未实测 | 低-中（需冒烟） |
| 稠密小档的实际 tok/s 落在"推算 × 0.6–0.9" | 实测带宽随模型变小而下降（7B@4.7GB→107 vs 27B@16.8GB→33） | 中 |

### 9.3 本轮"未找到公开证据"清单（不用记忆补齐）
- **Qwen3-Coder-Next 的 SWE-bench Verified 70.6% / SWE-Pro 44.3 / TB2.0 36.2**：qwen.ai 博客是 SPA 且未找到公开 JSON API，Qwen 官方模型卡只有图片（`benchmarks.png`），**本轮未能独立核实**（前期结论里的 70.6% 属"另一子任务读图"口径）。
- **Qwen3-Coder-30B-A3B 的官方 SWE-bench Verified 44.8%**：模型卡无表格，Qwen3-Coder 博客（qwenlm.github.io）正文无该表，**未找到可引用来源**（前期用的 51.6 是第三方 SWE-Agent 口径）。
- **Qwen3.5-9B / 4B 的任何第三方 SWE-bench / Terminal-Bench 复现**：Reddit / HN / DDG 本轮均不可达，HF 讨论里没有，**未找到公开证据**。
- **V100 上 Qwen3.5-9B / 4B / Qwen3.6-27B 的实测 tok/s**：只在 miyagadget 的 27B 与 35B-A3B 上找到；**9B/4B 没有 V100 实测**（只有 databasemart 的 7B/8B/9B/13B/14B/16B 老 llama.cpp/ollama 0.5.11 数据）。
- **Qwen3.6-35B-A3B 在 V100S-PCIe 上的实测**：只有 V100-SXM2 的 98.8，PCIe 折算是按作者自己的 ~-10% 修正推的。
- **Qwen3.5/3.6/3.8 在 ollama 0.40.6 上跑通的公开案例**：未找到（ollama tag 存在 ≠ 0.40.6 能跑；本轮未下载权重，未做端到端验证）。
- **V100S 的官方带宽数值**：nvidia.com 产品页未出现 "900 GB/s" 字串，nvidia PDF 链接 404；本报告用第三方页面记录的 ~900 GB/s（SXM2）/779.8 GB/s（PCIe，miyagadget 自测），并以"每 token 读全量需 2518 GB/s > 峰值"的方式做**与峰值数值无关**的证明。

---

## 10. 引用的关键来源（URL + 日期）

**官方模型卡（经 hf-mirror 读取）**
- `https://huggingface.co/Qwen/Qwen3.5-9B`（createdAt 2026-02-27）｜`/Qwen/Qwen3.5-4B`（2026-02-28）｜`/Qwen/Qwen3.5-27B`（2026-02-24）｜`/Qwen/Qwen3.5-35B-A3B`
- `https://huggingface.co/Qwen/Qwen3.6-27B`（2026-04-21）｜`/Qwen/Qwen3.6-35B-A3B`（2026-04-15）
- `https://huggingface.co/Qwen/Qwen3.8-27B`（2026-08-05）｜`/Qwen/Qwen3-Coder-Next`（2026-01-30）｜`/Qwen/Qwen3-Coder-30B-A3B-Instruct`（2025-07-31）
- `https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512`（2025-11-28）｜`/mistralai/Devstral-Small-2507`（2025-07-07）
- GGUF 体积：`https://huggingface.co/api/models/{unsloth/Qwen3.5-9B-GGUF, unsloth/Qwen3.5-4B-GGUF, unsloth/Qwen3.6-27B-GGUF, unsloth/Qwen3.8-27B-GGUF, ggml-org/Qwen3.6-35B-A3B-GGUF, unsloth/Qwen3.5-35B-A3B-GGUF, bartowski/mistralai_Devstral-Small-2-24B-Instruct-2512-GGUF, Qwen/Qwen3-Coder-Next-GGUF}/tree/main`

**Ollama 官方**
- `https://ollama.com/library/qwen3.5`｜`/qwen3.6`｜`/qwen3.8`｜`/devstral`｜`/qwen3-coder`（+ 各 `/tags` 页）
- `https://github.com/ollama/ollama/releases/tag/v0.40.6`（2026-10-16）；`LLAMA_CPP_VERSION` = b11669
- `https://docs.ollama.com/faq`（OLLAMA_NUM_PARALLEL / OLLAMA_KV_CACHE_TYPE / OLLAMA_MAX_LOADED_MODELS / OLLAMA_FLASH_ATTENTION / OLLAMA_KEEP_ALIVE）

**第三方 V100 实测（本轮亲自抓取核对）**
- `https://www.databasemart.com/blog/ollama-gpu-benchmark-v100`（7B/8B/9B/13B/14B/16B Q4 的 Eval Rate）
- `https://miyagadget.page/en/blog/2026/07/15/tesla-v100-32gb-qwen36-benchmark-en/`（27B 32.9 / 35B-A3B 98.8，V100-SXM2）
- `https://miyagadget.page/en/blog/2026/09/04/tesla-v100-32gb-qwen38-27b-benchmark-en/`（Qwen3.8-27B 33.41→15.84，V100-PCIe，KV 量化不可用）

**llama.cpp issue / PR（本轮抓取正文）**
- #29783（Volta GDN 崩溃）、**#29803（PR，已 MERGED，Volta FA 修复）**、**#29255（Volta 长 prefill + 前缀复用，open）**、#29562（多卡 layer split 确定性崩溃，closed）、**#30906（qwen35 家族 CPU 后端输出损坏，open）**、#23577（MTP 长会话重复输出）、#28777（DFlash2 + split-mode tensor 崩）、#29629（mtmd FA 图像 embedding 错）、#26044（Volta NaN embedding）、#19435（Qwen3.5 dense/MoE 接入，无视觉）

**HuggingFace 社区讨论**
- `Qwen/Qwen3.5-9B` #38《Tool calling issues》（2026-03-22，已关闭，正文隐藏）
- `Qwen/Qwen3.8-27B` #193《Practical experience: Qwen3.8-27B as a tool-using agent…》（2026-09-10，FLvdW，AMD MI50 + llama.cpp + ROCm）
