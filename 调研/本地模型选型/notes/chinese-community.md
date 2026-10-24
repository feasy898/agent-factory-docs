# 中文社区实测调研：2×V100S-32GB 上的本地模型选型

- 调研日期：**2026-10-21**（所有网页抓取与数据读取均在该日完成；文中"2026-XX-XX"为原文发布日期）
- 调研范围：知乎 / 掘金 / 博客园 / CSDN / 今日头条 / 微信公众号 / 简书 / 什么值得买 / ModelScope / ollama 官方模型库 / llama.cpp 官方源码
- 基准硬件（全程以此为准，不引用通用榜单）：**anolis-gpu-01 = 2× Tesla V100S-PCIE-32GB（sm_70，HBM2 约 900GB/s，driver 570.133.20，CUDA 12.6 工具链）**，125GB 内存，ollama 0.40.6（内置 llama.cpp runner，无独立 llama-cli/llama-server/vLLM/SGLang）。
- 现役模型：ollama `qwen3-coder-30b` = Qwen3-Coder-30B-A3B-Instruct-Q4_K_M（本地 18.5GB；30.5B 总参 / 3.3B 激活；256K ctx）。本次会话 anolis 实测：**decode 135.7 tok/s、prompt 149.1 tok/s（num_ctx 8192）**；并发 2 时每请求 109.7 tok/s、合计约 219 tok/s。
- 工作负载：af-bench 跑 SWE-bench Verified / Terminal-Bench / InjecAgent / τ²-bench 等 agentic 题型，每题约 10 轮工具调用；本地臂定位是"零 API 成本的量产臂"，吞吐与单题墙钟同等重要。

---

## 0. 调研方法与证据分级（请先读这一节）

### 0.1 本次实际可用的信息通道

| 通道 | 状态 | 说明 |
|---|---|---|
| `so.com`（360 搜索） | ✅ 可用 | 本轮主力搜索入口，支持 `site:` 与中文本地化索引 |
| `sogou.com`（搜狗） | ⚠️ 可用但会触发反爬 | 前 3 次查询正常，之后跳 `/antispider/`，仅用于兜底 |
| `cn.bing.com` | ⚠️ 部分失效 | 中文 query 会被"实体化"坍缩（多个不同 Qwen 查询返回同一组结果），只作交叉验证 |
| `m.toutiao.com/i{article_id}/info/` | ✅ 可用（关键通道） | 头条正文 JSON 接口，可拿到含表格的完整正文；web 端是 JS 渲染、抓不到 |
| `ollama.com/library/*/tags` | ✅ 可用 | 官方 tag 体积/上下文的第一手来源 |
| `raw.githubusercontent.com` | ✅ 可用 | 读 llama.cpp master 源码（`common/arg.cpp`、`src/llama-arch.cpp`、`src/llama-model.cpp`） |
| `huggingface.co` / `google.com` / `v2ex.com` | ❌ 不可达 | 本机 DNS 被污染（解析到 Facebook/Twitter 网段），本轮**未能在 HF 读 GGUF 体积**，相关数字只能引 ollama 官方 tag 与社区转述 |
| `modelscope.cn` | ⚠️ 部分可用 | 模型检索 API 可用；**讨论区**未能拿到可引用的帖子，本轮 ModelScope 侧证据为 0 |

### 0.2 证据分级

- **A｜官方自报**：厂商模型卡 / 官方博客 / ollama 官方模型卡与 tag 表。
- **B｜第三方复现**：写明具体硬件、模型、参数、命令与数字，可复算。
- **C｜社区体感/二手转述**：有观点无数字，或数字来自他人转述。
- **D｜疑似 AI 生成/内容农场**：自相矛盾或与官方事实冲突，本报告**不采信其技术数字**，仅作为"社区噪声水平"的记录。

---

## 1. 结论速览（TL;DR）

1. **核心假设「总参大、激活小的 MoE 在 V100 上又快又强」：部分成立，但成立条件极苛刻——必须 100% 权重常驻显存。**
   - 反面硬证据：同一张 RTX 5090D 32GB 上，**稠密** `qwen3.5:27b` 生成 60.91 tok/s（显存 24.5G，GPU 利用率 88%），而 **80B-A3B MoE** `qwen3-coder-next` 只有 **19.54 tok/s**（显存 29G + 内存 22.5G，**GPU 利用率仅 10%–16%**）——52GB 的权重装不进 32GB，被迫 CPU 卸载，直接掉一个数量级。〔B｜集速网 2026-03-11〕
   - 正面条件：Qwen3-Coder-Next 的 Q4_K_M 在 ollama 官方 tag 里是 **52GB**〔A〕，我们 64GB 总显存装得下，但只剩 **12GB** 余量给 KV cache + 双份 CUDA context + 激活值，**容不下一次失败的 split**。

2. **假设「稠密 27B 在 V100 上慢 3–4 倍」：成立，且可能更糟。**
   - 社区在 **V100 32GB 上直接跑过 llama.cpp + 27B 级稠密模型**：Q4_K_M 全量上卡后单流 **14–15 tok/s**，并发 4 总吞吐 **64 tok/s**。〔B｜CSDN 2026-09-19〕
   - 3090（1.79TB/s）上 qwen3.8:27b 在 8K ctx 的解码是 39.6 tok/s（且当时只有 43/64 层在 GPU）〔B｜头条 2026-09-12〕；V100S 带宽只有它的一半（900GB/s），**推断** V100 上 27B 稠密约 20–40 tok/s，即比现役 135.7 tok/s 慢 **3–7 倍**。

3. **对"是否比现役 qwen3-coder-30b 解题率更高"的回答：本轮没有找到能在我们机器上"又快又强"的单一选项，但找到了两个"更强、代价明确"的上位选项和一条被忽视的中间路线。**
   - 能力上位的两个：**Qwen3-Coder-Next 80B-A3B**（官方 SWE-V 70.6 / Terminal-Bench 2.0 36.2）与 **Qwen3.8-27B**（官方 Terminal-Bench 2.1 **73.0** / SWE-bench Pro 61.7 / QwenSWE-Bench 79.0）。
   - **被忽视的中间路线：`glm-4.7-flash`（30B-A3B，19GB Q4_K_M，198K ctx）**——单卡装得下、社区实测 **147.5 tok/s**、官方 SWE-V **59.2** / **τ²-Bench 79.5**（正好命中我们 harness 的题型），且是 2026-02 的新架构，比现役 2025-07 的 Qwen3-Coder-30B 高一个代际。

4. **对我们前期结论的两处修正**（详见 §5.3）：
   - 「Qwen3-Coder-Next Q4 约 45GB」→ **实为 52GB**（ollama 官方 tag），64GB 装下后余量比前期估计更紧，不是"从容"而是"贴边"。
   - 「本地最强可行选项 = Qwen3-Coder-Next」→ **需要降级为"上限探针"**，主力性价比档应改为 19GB 的 `glm-4.7-flash`。

---

## 2. 候选清单总表

> 说明：`Q4体积` 一律取 **ollama 官方 tag 表实测值**（2026-10-21 抓取），因为 HF 在本机不可达；`官方 agentic 分` 一律是**厂商自报**（模型卡里的对比图），不是第三方复现。

| 模型 | 厂商 | 架构（总参/激活） | Q4体积(GB) | ctx | GGUF/ollama 可得性 | 官方 agentic 分数（自报） | 第三方反馈（我们能核到的） | 我们的适配判断 |
|---|---|---|---|---|---|---|---|---|
| **Qwen3-Coder-30B-A3B-Instruct**（现役） | 阿里 | MoE 30.5B / 3.3B 激活 | **19**（本地实测 18.5） | 256K 原生（外推 1M） | ✅ `qwen3-coder:30b` | 官方卡未列 SWE-V 数字 | anolis 实测 135.7/149.1 tok/s | 保留为保底档 |
| **Qwen3-Coder-Next** | 阿里 | MoE 80B / 3B 激活（Qwen3-Next-80B-A3B-Base，混合注意力+MoE） | **52**（q4_K_M；q8_0 85） | 256K | ✅ `qwen3-coder-next:latest`（仅 3 个 tag） | **SWE-V 70.6**、SWE-Multilingual 62.8、SWE-Pro 44.3、**Terminal-Bench 2.0 36.2**、Aider 66.2（对比 DeepSeek-V3.2 70.2 / GLM-4.7 74.2 / MiniMax M2.1 74.8） | 32GB 卡上 19.5 tok/s、GPU util 10–16%（集速网）；社区普遍"需双卡 A6000/4090"（简书） | **上限探针**：能力最强但 52/64GB 贴边 + 混合注意力 sm_70 bug 风险 |
| **Qwen3.8-27B** | 阿里 | **稠密 27.78B**，64 层 = 48 层 Gated DeltaNet 线性注意力 + 16 层全注意力 | **18**（q4_K_M）；q8_0 30；mxfp8 32；nvfp4 18；bf16 56 | 256K | ✅ `qwen3.8:27b`（12 个 tag，vision+tools+thinking） | **Terminal-Bench 2.1 = 73.0**、SWE-bench Pro 61.7、NL2Repo 42.3、DeepSWE1.1 42.2、QwenSWE-Bench 79.0、CoWorkBench 70.7、ALE Pass@1 20.4、LCB v6 90.3 | 3090 24G 单卡：8K ctx 解码 39.6 tok/s、196K ctx 降到 13.9 tok/s；且**只有 43/64 层上了 GPU**（头条 2026-09-12） | 能力第一梯队，但**预计比现役慢 3–7 倍**；且默认 thinking on、reasoning_effort 可调（会烧 token） |
| **GLM-4.7-Flash** | 智谱 | **MoE 30B-A3B** | **19**（q4_K_M）；q8_0 32；bf16 60 | 198K | ✅ `glm-4.7-flash`（4 个 tag） | **SWE-V 59.2**、**τ²-Bench 79.5**、AIME25 91.6、GPQA 75.2、LCB v6 64.0、HLE 14.4、BrowseComp 42.8 | 5090D 32G：**147.5 tok/s**、显存 21G、GPU util 83%；3060 6G 笔电：10.8 tok/s、显存 5G+内存 14G、GPU util 20–30% | **首选试水**：单卡装得下、速度快一代际、命中 τ²-bench。风险：2026-02 发布、ollama tag 已 4 个月未更新 |
| **Qwen3.6-35B-A3B** | 阿里 | MoE 35B / A3B | **23–24**（q4_K_M） | 256K | ✅ `qwen3.6:35b-a3b` | 官方 35B-A3B 对比图（本次未逐项读数） | 4090 上总分 0.9125、平均时延 100.35s（博客园 2026-04-27，小样本） | 备选：比现役新、比 27B 稠密快 |
| **Qwen3.6-27B / 27b-coding** | 阿里 | 稠密 27B | 18–19 | 256K | ✅ | 同上 | 4090 上总分 0.90、**平均时延 149.94s、失败率 0.15**（博客园，小样本） | 不建议：同代稠密，速度与现役差距大 |
| **Qwen3.7-35B-A3B** | 阿里 | MoE 35B / A3B | 未找到官方 ollama tag（社区有 GGUF） | 未找到公开证据 | ⚠️ 仅社区量化（如 `aratan/qwen3.7-35b-q4`，描述称 8GB 显存 29 t/s） | 官方对比表里只有闭源 "Qwen3.7-Plus" | 未找到可复核的实测 | 观察，不进候选 |
| **gpt-oss:20b** | OpenAI | MoE 20B | 14 | 128K | ✅ | 官方卡列 SWE-V 34.0（对比 GLM-4.7-Flash 59.2） | 未找到我们硬件上的实测 | 不够强，排除 |
| **gpt-oss:120b** | OpenAI | MoE 120B / 5.1B | **65**（MXFP4） | 128K | ✅ | — | — | **排除**：65GB > 64GB，且 MXFP4 是 Blackwell 格式，V100 不支持 |
| **GLM-5 / GLM-5.3(-Flash)** | 智谱 | 744B / 40B | — | 1M | ❌ ollama 官方库 "No models"（无 GGUF） | — | — | 本地不可行，只能走 API |
| **GLM-4.7**（大版） | 智谱 | 355B 级 | — | — | ❌ **已于 2026-07-15 从 ollama 下架（retired），无 models** | SWE-V 74.2 | — | 本地不可行 |
| **Kimi K2 / K2.5** | 月之暗面 | 1T 级 | — | — | ❌ ollama 官方库无本地 tag | — | — | 本地不可行 |
| **MiniMax M3** | MiniMax | — | — | 1M | ❌ ollama 官方库只有 `:cloud` tag | — | — | 本地不可行 |
| **Qwen3.5:27b** | 阿里 | 稠密 27B | — | 256K | ✅（ollama 72 个 tag） | — | 5090D 32G：60.9 tok/s、显存 24.5G、GPU util 88% | 稠密，V100 上同样会慢；且是更老一代 |

---

## 3. 重点候选展开分析

### 3.1 Qwen3-Coder-Next 80B-A3B —— "能力天花板"，但显存贴边

**直接证据**

| 项 | 数值 | 来源 | 等级 |
|---|---|---|---|
| ollama `qwen3-coder-next:latest` 体积 | **52GB**（Q4_K_M），256K ctx，3 个 tag（latest/q4_K_M/q8_0） | https://ollama.com/library/qwen3-coder-next/tags （2026-10-21 抓取） | A |
| q8_0 体积 | 85GB | 同上 | A |
| 架构 | 基于 Qwen3-Next-80B-A3B-Base，混合注意力 + MoE，80B 总参 / 3B 激活 | ollama 官方模型卡 | A |
| 思考模式 | **Non-thinking mode only**（无 `<think>` 块） | ollama 官方模型卡 | A |
| SWE-bench Verified | **70.6**（对比 DeepSeek-V3.2 70.2 / GLM-4.7 74.2 / MiniMax M2.1 74.8） | ollama 官方模型卡 benchmark 图（https://ollama.com/assets/library/qwen3-coder-next/d978a788-2fa4-44ea-832c-20cd82202a6c） | A |
| Terminal-Bench 2.0 | 36.2 | 同上 | A |
| 32GB 5090D 实测 | 生成 **19.54 tok/s**（全程均值 19.16），显存 29G + 内存 22.5G，**GPU util 10%–16%**，TTFT 15.26s，模型加载 14.39s | https://www.canquick.com/ （集速网，2026-03-11） | B |
| 社区成本判断 | "MoE 是典型的空间换时间……80B 的权重必须全部加载到显存中……为了跑通一个 3B 速度的模型，你需要购买双卡 A6000 或 4090（显存成本 > 5 万），在 ROI 上完全倒挂" | https://www.jianshu.com/p/19d259840e78 （2026-02-05） | C（云厂商软文，观点可信度中等） |
| 发布日期 | 2026-02-04 开源 | 腾讯新闻 https://news.qq.com/rain/a/20260204A00XWI00 | B |

**推算（我们自己做，不是社区数字）**

- 显存：64GB − 52GB = **12GB 余量**。这 12GB 要装：两张卡的 CUDA context（各约 0.3–0.5GB，V100 社区经验值）、算子工作区、激活、KV cache。
- KV cache：Qwen3-Next-80B-A3B 的层数/KV 头数配置，本次**未找到公开的精确数字**；按 `2 × 层数 × KV头数 × head_dim × 字节数 × ctx` 公式，8K–32K ctx 大概率在 1–4GB 量级——**8K ctx 可行，32K ctx 需要实测才知道**。
- 速度：若 100% 驻留，每 token 需读取的权重 ≈ 3B 激活专家 + 48 层的 attention/norm 权重，与现役 30B-A3B 同量级 → **推断** 70–120 tok/s，接近现役 135.7。
- 但**只要有 10%–20% 的专家落到 CPU**，按 5090D 上 52GB 装 32GB 的实例（GPU util 掉到 10–16%、速度掉到 19.5 tok/s），**推断** 会直接掉到 20–40 tok/s 的量级。这就是本次调研最重要的悬崖。

**对我们负载的匹配度**
- ✅ 优点：**非思考模式**意味着没有 think 块，token 消耗低、延迟稳定——正好命中我们"量产臂"定位和"完成度纪律"痛点；tool calling 是其训练目标之一（官方称在 Claude Code / Qwen Code / Cline / OpenCode 上开箱可用）。
- ❌ 缺点：52/64GB 贴边，容错为零；`qwen3next` 是**混合线性注意力架构**，与 Qwen3.8 属同一"混合注意力家族"，**我们此前记录的"速度正常但输出损坏"CUDA bug 风险同样适用**（llama.cpp 侧 arch 名为 `qwen3next` / `qwen35` / `qwen35moe`，见 §4.2）。

---

### 3.2 Qwen3.8-27B —— 稠密 27B + 混合线性注意力：能力强，但注定慢

**直接证据**

- **架构（我们此前记录有误，此处更正）**：Qwen3.8-27B 是**稠密 27.78B**，不是 MoE。64 层 = **48 层 Gated DeltaNet 线性注意力 + 16 层全注意力**；只有 1/4 的层存 KV cache，线性注意力只存**固定大小状态（实测约 3.7GB）**，不随文本增长。
  来源：https://www.toutiao.com/article/7681648322662154767/ （2026-09-04，正文经 `m.toutiao.com/i7681648322662154767/info/` 取全文）
- **显存账（双 3090 48G，ollama `qwen3.8:27b-mtp-q8_0`，262K ctx，nvidia-smi 实测）**：
  - Q8 权重 + 4bit KV：权重 29G + KV 4.6G + 固定状态 3.7G = **约 37G，余 11G**
  - Q8 权重 + 8bit KV：约 40.8G，余 7.2G
- **Prefill 速度（双 3090）**：128K（~12.7 万 tok）→ ~176s → **~720 tok/s**；256K（~25.4 万 tok）→ ~516s → **~490 tok/s**（长度翻倍，prefill 速度降 32%）。
- **单卡 3090 24G 实测（llama.cpp，Q4_K_M，c=262144）——本轮最有价值的一组数**：
  命令：`llama-server -m Qwen3.8-27B-UD-Q4_K_M.gguf -c 262144 -ngl 999 -fa on -t 12 -np 1 -b 2048 -ub 2048 -ctk q5_0 -ctv q5_0`
  启动日志：`load_tensors: offloaded 43/64 layers to GPU`（**只有 43/64 层在 GPU**），`n_gpu_layers=43`；显存峰值全程恒定 **23508 / 24576 MiB**（KV 启动时一次性预分配，不会 OOM）。

  | 上下文 tokens | 预填充 tok/s | TTFT | **解码 tok/s** | ms/token |
  |---|---|---|---|---|
  | 8,248 | 1390 | 5.9s | **39.6** | 25.2 |
  | 16,477 | 1350 | 12.2s | 36.8 | 27.1 |
  | 32,746 | 1249 | 26.2s | 31.9 | 31.3 |
  | 49,202 | 1160 | 42.4s | 28.3 | 35.4 |
  | 65,471 | 1087 | 60.2s | 25.3 | 39.5 |
  | 98,383 | 972 | 101.3s | 21.0 | 47.6 |
  | 131,109 | 880 | 149.1s | 18.0 | 55.5 |
  | 163,834 | 805 | 203.7s | 15.7 | 63.7 |
  | 196,559 | 741 | 265.4s | **13.9** | 72.0 |

  来源：https://www.toutiao.com/article/7684310497310589440/ （2026-09-12；表格来自文中截图，已逐格读图）
- 作者结论原话："**最好用 LLama.cpp 来跑，ollama 完全不行**（跑 Agent 任务最好能 256k 上下文）"；"以前 3090 能跑的模型基本没有，qwen3.8:27b 感觉是唯一一个能打的模型"。
- 8G 显存 3070 的反面数据（社区第三方量化 IQ4_XS）：32K ctx/ngl22 → 3.5 tok/s；8K/ngl30 → 4.1；ngl32 → 4.0–4.16；换 IQ2_M → 8.5。作者结论："4 t/s 的生成速度意味着写个 2000 字的长文得干等近十分钟"，"真正要拿它干活（长文、代码、严肃推理）……要么上更大显存的卡，要么老老实实用云端 API"。
  来源：https://deepseek.csdn.net/6a8d0b7e662f9a54cba02c96.html （2026-08-25）
- 官方 benchmark（模型卡图）：Terminal-Bench 2.1 = **73.0**、SWE-bench Pro 61.7、NL2Repo-Bench 42.3、DeepSWE 1.1 42.2、QwenSWE-Bench 79.0、CoWorkBench 70.7、JobBench 33.4、Agents' Last Exam Pass@1 20.4 / Score 42.9、IFBench 79.5、GPQA Diamond 89.2、HLE 30.8、LiveCodeBench v6 90.3。
  来源：https://ollama.com/library/qwen3.8 （benchmark 图 https://ollama.com/assets/library/qwen3.8/2a76d126-0f06-40a0-b1b4-5884fd2dc3c7，2026-10-21 下载读图）
- ollama tag 表：18GB(q4_K_M) / 30GB(q8_0) / **32GB(mxfp8)** / **18GB(nvfp4)** / 56GB(bf16)，全部 256K ctx。**注意：mxfp8 与 nvfp4 是 Blackwell(sm_100/sm_120) 格式，V100 用不了，只能走 q4_K_M / q8_0。**

**推算（我们自己做）**
- 18GB 权重在 V100 32GB 上**可以 100% 驻留**（这比 3090 那次 43/64 层的情况好得多）。
- 但 V100S 带宽 900GB/s ≈ 3090 的一半 → 8K ctx 解码 **推断** 25–40 tok/s；196K ctx **推断** 9–14 tok/s。
- 对比现役 135.7 tok/s：**慢 3.5–5.4 倍**。
- 单题墙钟：af-bench 每题 ~10 轮工具调用，若现役单题输出 5K token，则 qwen3.8 单题生成时间从 ~37s 涨到 ~2–3.5 分钟，再叠加它默认 thinking on（`reasoning_effort` 可调，思考 token 会显著拉长）→ **单题墙钟成本至少翻 4–6 倍**。

**结论**：qwen3.8-27B 在**解题率**上大概率显著优于现役（TB 2.1 73.0 是本轮所有本地候选里最高的 agentic 分），但在**单题墙钟**上明显输。除非我们的瓶颈是"解题率"而不是"时间"，否则它不是现役的直接替代。

---

### 3.3 GLM-4.7-Flash 30B-A3B —— 本轮最值得试的中庸解（前序结论里没有它）

**直接证据**

- ollama 官方模型卡：**"GLM-4.7-Flash is a 30B-A3B MoE model. As the strongest model in the 30B class"**；tag 体积 19GB(q4_K_M) / 32GB(q8_0) / 60GB(bf16)，**198K ctx**；模型卡注明 **"this model requires Ollama 0.14.3 which is currently in pre-release"**（我们 0.40.6 满足）。
  来源：https://ollama.com/library/glm-4.7-flash
- 官方 benchmark（模型卡表格，A 级自报）：

  | Benchmark | GLM-4.7-Flash | Qwen3-30B-A3B-Thinking-2507 | GPT-OSS-20B |
  |---|---|---|---|
  | SWE-bench Verified | **59.2** | 22.0 | 34.0 |
  | **τ²-Bench** | **79.5** | 49.0 | 47.7 |
  | BrowseComp | 42.8 | 2.29 | 28.3 |
  | AIME 25 | 91.6 | 85.0 | 91.7 |
  | GPQA | 75.2 | 73.4 | 71.5 |
  | LCB v6 | 64.0 | 66.0 | 61.0 |
  | HLE | 14.4 | 9.8 | 10.9 |

- 社区实测（集速网 2026-03-11，RTX 5090D 32G，ollama 默认 ctx 4k）：`glm-4.7-flash:latest` 生成 **147.53 tok/s**（全程均值 132.24），**显存 21G**、**没占内存**、GPU util 83%，TTFT 5.75s，模型加载 5.67s。
- 同一台 3060 6G 笔电上：10.84 tok/s，显存 5G + 内存 14G，**GPU util 只有 20%–30%**（这就是"装不下就得靠 CPU"的典型形态）。
- 对比：同一台 5090D 上 `qwen3.5:27b`（稠密）只有 60.91 tok/s —— **同为 30B 级，MoE 快 2.4 倍**，这条数据直接支持"MoE 在解码阶段读得少所以快"的技术直觉。

**推算（我们自己做）**
- 19GB 权重 → **单张 V100S 32GB 就能 100% 驻留**（余 13GB 给 KV+ctx），第二张卡可以留给现役模型做 A/B 对照或跑并发。这比 Qwen3-Coder-Next 的 52/64 贴边稳得多。
- 速度：5090D(1.79TB/s) 上 147.5 tok/s → V100S(900GB/s) **推断** 70–90 tok/s。若是 MoE 且激活 3B，每 token 实际读取的权重远小于 19GB，所以推断区间比"带宽/权重体积"的下界更宽松。
- 相对现役：**可能比 135.7 tok/s 慢一档，但换来的解题率提升是明确的**（SWE-V 59.2 自报、τ²-Bench 79.5 自报；τ²-bench 正好是我们的题型）。

**风险**
- 2026-02 发布，ollama tag 已是"4 个月前"，社区近期复现较少（我们只找到 1 个第三方速度复现 + 若干 CSDN 转载）。
- 智谱同门的 GLM-4.7 大版已于 **2026-07-15 从 ollama 下架**（"glm-4.7 was retired on July 15, 2026 / No models have been pushed"，https://ollama.com/library/glm-4.7）——**Flash 档目前还在，但同门大版被撤，说明智谱在 ollama 上的策略会变**，需留意 4.7-flash 是否也会撤。
- GLM-5 / GLM-5.3 在 ollama **没有 GGUF**，本地路径基本断绝。

---

### 3.4 稠密 27B 家族（Qwen3.5:27b / Qwen3.6-27b / Qwen3.6-27b-coding）

- 集速网实测 `qwen3.5:27b`（5090D 32G）：生成 60.91 tok/s、显存 24.5G、GPU util 88%；**同一张卡上比 30B-A3B 的 glm-4.7-flash 慢 2.4 倍**。
- 博客园"九款本地模型测试"（2026-04-27，RTX 4090 24G + 64GB RAM，全部 Q4_K_M，题量极小：GSM8K 20 / BBH 20 / HumanEval+ 10 / MBPP+ 10，**只能当体感**）：
  - Qwen3.6-27B：逻辑 0.95 / 代码 0.85 / 总分 0.90，**平均时延 149.94s，执行失败率 0.15**
  - Qwen3.6-35B-A3B：总分 0.9125，平均时延 100.35s
  - Qwen3-Coder-Next（Opus4.6 Reasoning Distilled 二次蒸馏版）：代码分 1.00 / 逻辑分 0.60 / 总分 0.80，平均时延 58.25s
  - 值得注意：**MoE 的平均时延明显低于稠密 27B**（100s / 58s vs 150s），这与"解码是访存密集型、MoE 只读激活部分"的机制一致。
  - 来源：https://www.cnblogs.com/Fzeng/p/19938294
- 判断：稠密 27B 这一档在 V100 上不是我们的答案——**它们比现役更慢，且没有 MoE 的速度红利**。列入候选只是为了做对照。

---

### 3.5 明确排除的选项与原因

| 选项 | 排除理由 | 证据 |
|---|---|---|
| gpt-oss:120b | ollama tag **65GB > 64GB**；且是 **MXFP4** 格式，Volta 无原生支持 | https://ollama.com/library/gpt-oss/tags |
| GLM-5 / GLM-5.3(-Flash) | ollama 官方库 **"No models"**（无 GGUF），744B/40B 也不可能在 64GB 跑 | https://ollama.com/library/glm-5 |
| GLM-4.7（大版） | **2026-07-15 已 retired**，ollama 无 models | https://ollama.com/library/glm-4.7 |
| Kimi K2 / K2.5 | ollama 官方库**无本地 tag** | https://ollama.com/library/kimi-k2 、 /kimi-k2.5 |
| MiniMax M3 | ollama 只有 `:cloud` tag | https://ollama.com/library/minimax-m3 |
| qwen3.8:27b-mxfp8 / nvfp4 | Blackwell 格式，sm_70 不支持；只能用 q4_K_M(18GB)/q8_0(30GB) | ollama tag 表 |
| 4090/5090 多卡"堆料" | 社区实测指出：低显存卡必须跨卡搬数据，**PCIe 带宽成瓶颈**，"显存容量 > 显存带宽 > 算力核心数" | 头条 2026-03-01（vLLM 场景，对 llama.cpp layer-split 不完全适用，见 §4.1） |

---

## 4. V100 专项：架构、编译、卸载机制

### 4.1 引擎选型（社区共识，与我们已知一致）

CSDN 2026-09-19《V100部署Qwen 27B：llama.cpp量化调优从4到64 tok/s实战》给出的选型结论（等级 B）：
- **llama.cpp（llama-server）是 V100 跑 27B 级模型"目前最省心、最可能跑出好性能的方案"**。
- vLLM：对 Ampere 及以上做了大量 kernel 优化，Volta 在很多版本直接不在支持列表；SGLang 更激进（设计上假设 Ampere+）；ExLlamaV2 官方要求 Turing 起步，sm_70 不在支持范围；TensorRT-LLM 对老架构支持越来越敷衍。
- 预编译包报 **`no kernel image is available`** —— 因为二进制里没编 sm_70 的 kernel。**必须自己源码编译并显式指定架构**。
- 编译命令（原文给出）：
  ```
  cmake -B build -DGGML_CUDA=ON -DGGML_CUDA_ARCHITECTURES=70 \
        -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF
  cmake --build build --config Release -j $(nproc)
  ```
- 关键启动参数（原文最终配置）：
  ```
  ./llama-server -m qwen-27b-q4_k_m.gguf -c 8192 -ngl 99 \
      --batch-size 512 --ubatch-size 512 -t 8 --mlock --no-mmap \
      --cache-type-k q8_0 --cache-type-v q8_0 --cuda-graph --parallel 4 --port 8080
  ```
- 量化档位表（原文）：Q8_0 28.5GB（32GB 卡勉强）/ Q5_K_M 18.1GB / **Q4_K_M 16.1GB（推荐）** / Q3_K_M 13.5GB / IQ4_XS 14.7GB。
- 原文关键机理（值得抄进我们的设计文档）：
  > "量化最大的收益不是'算得快'，而是'省显存'。省下来的显存让权重全部住进 GPU，避免了跨 PCIe offload，这才是速度提升的根本来源。"
  > "V100 的 Tensor Core 只支持 FP16，不支持 INT8 和 INT4 计算。"
  > "解码阶段本质上是访存密集型任务，瓶颈是'把权重从显存读出来'的速度。"
- 该文给出的**速度阶梯**（单卡 V100 32GB，Qwen 27B Q4_K_M）：transformers FP16 + CPU offload = 4 tok/s → 换 llama.cpp + Q4_K_M + `-ngl 99` 全上卡 = **14–15 tok/s** → 再加 KV q8_0 量化 + 锁页内存等 = 并发 4 时**总吞吐 64 tok/s**，单流稳定 **17–20 tok/s**。

> ⚠️ 注意：ollama 0.40.6 自带的 llama.cpp runner 是**预编译包**。我们现役模型能在 V100 上跑到 135.7 tok/s，说明该预编译包**确实含 sm_70 kernel**（这是我们自己的直接事实，A 级）。但我们**没有独立 llama-server 二进制**，所以 §4.1 的 `--cache-type-k/--cuda-graph/--parallel` 这类精细参数在 ollama 侧**不可直接设置**——这是"要不要额外部署一套源码编译的 llama.cpp"这个决策的真正动因。

### 4.2 多卡与 MoE 卸载机制（llama.cpp 官方源码，2026-10-21 抓取 raw.githubusercontent.com/ggml-org/llama.cpp/master）

| 参数 | 源码位置 | 官方帮助文本（节选） | 含义 |
|---|---|---|---|
| `--split-mode {none,layer,row,tensor}` | `common/arg.cpp:2821-2840` | "**layer (default)**: split layers and KV across GPUs (pipelined)；**tensor**: split weights and KV across GPUs (parallelized, **EXPERIMENTAL**)" | **默认就是 layer 切分**；tensor 模式官方明确标注 EXPERIMENTAL —— 这与我们已知的"MTP/DFlash2 在 `--split-mode tensor` 下会崩"完全吻合，**不要在生产里用 tensor** |
| `--tensor-split N0,N1,...` | `common/arg.cpp:2844+` | 按比例把模型分给各卡 | 双卡均匀用 `1,1` |
| `--cpu-moe` | `common/arg.cpp:2764-2770` | "keep **all** Mixture of Experts (MoE) weights in the CPU" | 全部 MoE 权重留 CPU |
| `--n-cpu-moe N` | `common/arg.cpp:2771-2777` | "keep the Mixture of Experts (MoE) weights of the **first N layers** in the CPU"（env `LLAMA_ARG_N_CPU_MOE`） | **前 N 层**的 MoE 专家留 CPU → 我们的"专家卸载"旋钮 |
| `--moe-cache-mib N` | `common/arg.cpp:2781` | "GPU cache size in MiB for the MoE experts kept in the CPU. **with multiple GPUs, it is split among them like the layers (--tensor-split)**（default: 0, disabled）" | **关键机制**：给留在 CPU 的专家在 GPU 上开一份热点缓存 |
| `--n-cpu-ffn N` | `common/arg.cpp:2791` | "keep the **dense** FFN weights of the first N layers in the CPU（dense models; for MoE expert weights use --n-cpu-moe）" | 稠密模型的对应旋钮 |
| `--spec-draft-n-cpu-moe / --cpu-moe-draft` | `common/arg.cpp:4163-4170` | 投机解码 draft 阶段的对应开关 | MTP/DFlash2 与卸载的交互点 |

**架构支持（同一份源码）**：
- `src/llama-arch.cpp:41-42` → `LLM_ARCH_QWEN35 "qwen35"`、`LLM_ARCH_QWEN35MOE "qwen35moe"`
- `src/llama-arch.cpp:38` → `LLM_ARCH_QWEN3NEXT "qwen3next"`
- `src/llama-model.cpp:333-336` → `llama_model_qwen35` / `llama_model_qwen35moe` 实体类
- ⇒ **Qwen3-Coder-Next（qwen3next）与 Qwen3.8-27B（qwen35）都是"混合线性注意力"家族**，llama.cpp master 均已支持；我们担心的"速度正常但输出损坏"风险**同时覆盖这两个模型**。

**专家命中率的量化证据（很有价值）**：公众号《Qwen3.8-Flash-Next 塞进 12G 显存：决定速度的其实不是量化位数》（AI 智链未来，2026-10-08，**页面明确标注"内容由 AI 生成"，故降级为 D 级，仅取其中可核对的实验结构**）报道了一个 Strata 调度框架的实验：
- Qwen3.8-Flash-Next = **125B A6B**（另带 51B n-gram 与 4B MTP），每层 512 个 routed experts（每 token 选 10）+ 1 shared expert，48 层共 **24,576 个 layer-expert 单元**。
- 12GB 卡（Q2_0）短对话 **94 tok/s**，128K ctx **76 tok/s**（RTX 5070 12GB + 64GB RAM）。
- **同一张 RTX 4090 48GB** 上两个 Q4 量化、限制 GPU 占用相同 → **速度差 1.72 倍**，原因："IQ4_XS 多缓存了 **4,069 个 layer-expert slots**，更多计算留在 GPU 上，CPU miss 更少"；到 256K ctx 差距收窄到约 13%（82.8 vs 73.4 tok/s）。
- 结论（与我们的直觉一致、但表述更精确）：**在 MoE 卸载场景下，决定速度的不是量化位数，而是"专家命中率"**；显存越大 → 热点专家留得越多 → CPU miss 越少。

> 这条对我们的直接含义：如果 52GB 的 Qwen3-Coder-Next 在 64GB 上必须动用 `--n-cpu-moe`，**必须同时开 `--moe-cache-mib`**（默认 0 = 禁用！），否则速度会掉到集速网 5090D 那个量级（≈19 tok/s）。

### 4.3 上下文长度的显存账（ollama 实测拟合）

集速网（2026-03-11）在 5090D 32G 上对 ollama 默认 4K ctx 做了实测拟合：
- 线性式：**显存 ≈ 2.79GB（固定开销） + 0.1445 GB/k tokens**（对 qwen3:4b-instruct）
- 实测点：1k→3.0G / 4k→3.6G / 8k→4.1G / 16k→5.4G / 32k→6.7G / 64k→12.3G / 128k→21.4G；作者外推 198k→31.4G（**32GB 卡不够**）。
- 作者结论："以前不知道 ollama 默认启用 4k 上下文，上下文大小对显存和推理速度影响非常大"；"上下文大了之后不仅显存占用多了，推理也慢了"。
- 另一条：**ollama 默认 ctx 是 4096**——这意味着我们如果直接 `ollama run` 不指定 num_ctx，会拿到一个"上下文短、看起来很聪明"的结果，**在 af-bench 上会直接压低解题率**。这一点对我们是硬性配置项。

---

## 5. 直接证据 vs 推断

### 5.1 直接证据（本轮亲自读到，可复现）

| # | 事实 | 来源（URL / 文件） | 等级 |
|---|---|---|---|
| E1 | ollama `qwen3-coder-next` Q4_K_M = **52GB** / q8_0 = 85GB / ctx 256K | https://ollama.com/library/qwen3-coder-next/tags | A |
| E2 | ollama `qwen3-coder:30b` = **19GB**、arch `qwen3moe`、**30.5B 总参 / 3.3B 激活**、256K 原生 ctx（外推 1M） | https://ollama.com/library/qwen3-coder:30b | A |
| E3 | ollama `qwen3.8:27b` Q4_K_M = **18GB**、256K、vision+tools+thinking；另有 mxfp8 32GB / nvfp4 18GB / bf16 56GB | https://ollama.com/library/qwen3.8/tags | A |
| E4 | ollama `glm-4.7-flash` = **19GB**、**198K**、**30B-A3B MoE**；官方 SWE-V **59.2**、**τ²-Bench 79.5** | https://ollama.com/library/glm-4.7-flash | A |
| E5 | ollama `glm-4.7` **2026-07-15 retired**、无 models；`glm-5` / `kimi-k2` / `kimi-k2.5` / `minimax-m3` 无本地 GGUF | https://ollama.com/library/glm-4.7 、 /glm-5 、 /kimi-k2 、 /minimax-m3 | A |
| E6 | ollama `gpt-oss:120b` = **65GB**（MXFP4）、`gpt-oss:20b` = 14GB | https://ollama.com/library/gpt-oss/tags | A |
| E7 | Qwen3-Coder-Next 官方 benchmark：SWE-V 70.6 / SWE-Multilingual 62.8 / SWE-Pro 44.3 / **TB2.0 36.2** / Aider 66.2 | ollama 模型卡 benchmark 图 | A |
| E8 | Qwen3.8-27B 官方 benchmark：TB2.1 **73.0** / SWE-Pro 61.7 / QwenSWE-Bench 79.0 / CoWorkBench 70.7 / ALE Pass@1 20.4 / LCBv6 90.3 | ollama 模型卡 benchmark 图 | A |
| E9 | 集速网（5090D 32G，ollama 默认 4K ctx）：`qwen3.5:27b` **60.91** tok/s（24.5G，GPU 88%）；`qwen3-coder-next` **19.54** tok/s（29G+22.5G 内存，**GPU 10–16%**）；`glm-4.7-flash` **147.53** tok/s（21G，GPU 83%）；`qwen3:4b-instruct` 290.59 tok/s | https://www.canquick.com/ | B |
| E10 | 集速网 ollama 显存拟合：2.79G + 0.1445G/k ctx；ollama 默认 ctx = 4096 | 同上 | B |
| E11 | V100 32GB + llama.cpp + 27B Q4_K_M：全上卡后单流 **14–15 tok/s**，并发 4 总吞吐 **64 tok/s**，单流 17–20 tok/s；初始 FP16 CPU offload 仅 4 tok/s | https://blog.csdn.net/weixin_29047545/article/details/166040492 （2026-09-19） | B |
| E12 | V100 编译要点：`-DGGML_CUDA_ARCHITECTURES=70`；预编译包报 `no kernel image is available`；vLLM/SGLang/ExLlamaV2 不适合 V100 | 同上 | B |
| E13 | 3090 24G 单卡 llama.cpp 跑 qwen3.8:27b：**仅 43/64 层上 GPU**，解码 39.6 tok/s@8K → 13.9 tok/s@196K，prefill 1390→741 tok/s，显存峰值恒定 23508/24576 MiB | https://www.toutiao.com/article/7684310497310589440/ （2026-09-12，表格读图） | B |
| E14 | Qwen3.8-27B 架构：**64 层 = 48 层 Gated DeltaNet 线性注意力 + 16 层全注意力**；线性注意力固定状态 ~3.7G 不随文本增长；双 3090 下 Q8+4bitKV 满 256K 占 37G 余 11G；prefill 128K ~720 tok/s、256K ~490 tok/s | https://www.toutiao.com/article/7681648322662154767/ （2026-09-04） | B |
| E15 | 8G 3070 上 qwen3.8-27b 社区量化：IQ4_XS 4.0–4.16 tok/s / IQ2_M 8.5 tok/s；作者判定"生产请慎入" | https://deepseek.csdn.net/6a8d0b7e662f9a54cba02c96.html （2026-08-25） | B |
| E16 | 4090 上九款本地模型横评：Qwen3.6-27B 总分 0.90 / 时延 149.94s / 失败率 0.15；Qwen3.6-35B-A3B 0.9125 / 100.35s；Qwen3-Coder-Next(蒸馏版) 0.80 / 58.25s | https://www.cnblogs.com/Fzeng/p/19938294 （2026-04-27，题量极小，仅作体感） | B |
| E17 | llama.cpp `--split-mode` 默认 `layer`，`tensor` 标注 **EXPERIMENTAL**；`--n-cpu-moe N` 留前 N 层 MoE 专家在 CPU；**`--moe-cache-mib N` 默认 0（禁用）**，多卡时按 `--tensor-split` 分配 | `common/arg.cpp:2764-2840`（raw.githubusercontent.com，2026-10-21） | A |
| E18 | llama.cpp master 支持 `LLM_ARCH_QWEN35`/`QWEN35MOE`/`QWEN3NEXT` | `src/llama-arch.cpp:38-42`、`src/llama-model.cpp:333-336` | A |
| E19 | 社区判断：Qwen3-Coder-Next 是"空间换时间"，80B 权重必须全进显存，个人/中小企业本地部署是"极差的商业决策" | https://www.jianshu.com/p/19d259840e78 （2026-02-05，云厂商软文，观点） | C |
| E20 | 社区判断：多卡堆料不一定强，低显存卡跨卡搬数据撞 PCIe 瓶颈；"显存容量 > 显存带宽 > 算力核心数" | 头条 2026-03-01（vLLM 场景，**对 llama.cpp layer-split 不完全适用**） | C |

### 5.2 推断（我们自己的推算，标注依据与不确定度）

| # | 推断 | 依据 | 不确定度 |
|---|---|---|---|
| I1 | V100S 上稠密 27B（Q4_K_M）解码约 **15–25 tok/s**（8K ctx，全上卡） | E11 是 Qwen2.5-27B 在 V100 的 14–15 tok/s；qwen3.8-27B 少 KV 但权重读取量相近 | 中（±40%） |
| I2 | V100S 上 Qwen3.8-27B（18GB 全上卡）解码约 **25–40 tok/s@8K、9–14 tok/s@196K** | E13 的 3090 数据（39.6@8K、13.9@196K）按带宽比 0.5 折算；V100 上层数全上 GPU 反而略微优于 E13 的 43/64 层 | 中高 |
| I3 | 相对现役 135.7 tok/s，**稠密 27B 慢 3.5–5.4 倍**，Qwen3.8 单题墙钟涨 4–6 倍 | I2 + 现役实测 | 中 |
| I4 | V100S 上 `glm-4.7-flash`（19GB 全上卡）解码约 **70–90 tok/s** | E9：5090D 147.5 tok/s，V100S 带宽比 0.5；MoE 实际读取量小于 19GB 故不完全线性 | 中高 |
| I5 | Qwen3-Coder-Next 52GB 若 100% 驻留双 V100S → 约 **70–120 tok/s**；若被迫 `--n-cpu-moe` 卸载 → 可能掉到 **20–40 tok/s** | E9（5090D 32G 上 52GB 模型 GPU util 10–16%、19.5 tok/s）+ E17（`--moe-cache-mib` 默认关闭） | **高**（这是本报告最不确定、也最关键的一条） |
| I6 | 52GB 权重在 64GB 上装下后余 12GB，可支撑 **8K–32K ctx**（未实测） | 通用显存公式 + E10 拟合式 | 中高 |
| I7 | "混合线性注意力 + MoE"在 sm_70 上出现"速度正常但输出损坏"的风险，**同时覆盖** Qwen3-Coder-Next(qwen3next) 与 Qwen3.8(qwen35) | E18（两者同属混合注意力家族，llama.cpp 侧独立实现）+ 本工作区已记录的 bug | 中（无公开复现帖） |
| I8 | ollama 0.40.6 的 runner 已含 sm_70 kernel | 现役 qwen3-coder-30b 在 anolis 实测 135.7 tok/s（GPU 生效） | 低（我们自己的事实） |

### 5.3 对我们前期结论的修正（2026-10 前序文件 `设计/benchmark调研/实测/model-pricing.md` §4.2）

| 前期结论 | 本轮核查结果 | 处理 |
|---|---|---|
| 「Qwen3-Coder-Next Q4 量化后双卡 64GB 可容纳（完整版约 46GB）」 | ollama 官方 tag 实为 **52GB**（Q4_K_M），余量仅 12GB | **修正数字**。46GB/45GB 的估计偏低 |
| 「本地最强可行选项是 Qwen3-Coder-Next（80B A3B）」 | 能力上确实最强（SWE-V 70.6 自报），但 52/64GB 贴边 + 混合注意力 sm_70 bug 风险 + 卸载悬崖 | **降级为"上限探针"**，主力性价比档改为 19GB 的 `glm-4.7-flash` |
| 「Qwen3-Coder-30B-A3B Q4_K_M 约 20.5GB」 | ollama 官方 19GB，我们本地 18.5GB | 一致，仅微调 |
| 「Qwen3.8-27B 是稠密 27B，在 V100 上会慢 3–4 倍」 | **成立**（I1–I3），且可能更慢（3.5–5.4×） | 确认，并补上"混合线性注意力、KV 只占 1/4 层"这一关键结构信息 |
| 「Qwen3.8 系列默认 reasoning_effort=xhigh，token 消耗约 2 倍」 | ollama 模型卡确认"Thinking mode is on by default and can be disabled per request；reasoning depth can be tuned with reasoning_effort"；**"默认就是 xhigh" 这一具体取值本次未找到公开证据** | 部分确认（机制在，默认值未证） |
| 「GPT-OSS-120B MXFP4 明确不建议」 | 确认且更严重：ollama tag **65GB > 64GB** | 确认 |

---

## 6. 对我们的具体建议（落到 anolis-gpu-01）

### 6.1 决策

**不替换现役。** 本轮没有任何一个候选能同时满足"解题率更高 + 单题墙钟不增加"。
推荐路径是 **"并行加一档、先做 A/B，再决定是否替换"**：

| 优先级 | 动作 | 候选 | 预期收益 | 风险/代价 |
|---|---|---|---|---|
| **P0** | 装 **`glm-4.7-flash`**（19GB Q4_K_M，**单卡**）做 A/B | 官方 SWE-V 59.2 / τ²-Bench 79.5 自报；推断 70–90 tok/s | 解题率很可能高于现役，且不换架构风险 | 社区复现少（1 个第三方速度点）；同门 GLM-4.7 大版已从 ollama 下架，4.7-flash 未来可能同样撤 |
| **P0** | 装 **`qwen3.8:27b`**（18GB Q4_K_M，单卡）做 A/B | 官方 TB 2.1 **73.0**（本轮本地候选最高） | agentic 能力最强 | **推断慢 3.5–5.4 倍**；默认 thinking on 会烧 token；混合注意力 sm_70 输出损坏风险 |
| **P1** | 把 **`qwen3-coder-next`**（52GB）作为**上限探针**上双卡 | 官方 SWE-V 70.6；非思考模式省 token | 能力天花板 | 52/64GB 贴边；必须 layer split；卸载悬崖；同属混合注意力家族 |
| **P2** | 维持 `qwen3-coder-30b` 作保底 | — | 零成本、零风险 | — |

### 6.2 具体装法与配置改动（anolis，ollama 0.40.6）

**A. GLM-4.7-Flash（P0，单卡）**
```bash
# 只下 19GB 的 Q4_K_M，别碰 bf16(60GB)/q8_0(32GB)
ollama pull glm-4.7-flash:q4_K_M

# 关键：ollama 默认 ctx 只有 4096，必须用 Modelfile 拉长（E10）
mkdir -p ~/ollama-models && cat > ~/ollama-models/glm47flash.Modelfile <<'EOF'
FROM glm-4.7-flash:q4_K_M
PARAMETER num_ctx 32768
PARAMETER temperature 0.6
PARAMETER top_p 0.95
EOF
ollama create glm47flash -f ~/ollama-models/glm47flash.Modelfile

# 起服务时按 2 卡分给 GLM，现役模型仍占 1 卡（19GB < 32GB，余 13GB 给 KV+ctx）
CUDA_VISIBLE_DEVICES=0 OLLAMA_NUM_PARALLEL=2 ollama serve
```
> 说明：`OLLAMA_NUM_PARALLEL=2` 是我们已有的做法（现役并发 2 时每请求 109.7 tok/s、合计 219 tok/s）。**但要注意并发 2 会把 KV cache 需求翻倍**，用 32768 ctx 时单卡余量 13GB 是否够 2 路并发，必须先单路跑通再上并发。

**B. Qwen3.8-27B（P0，单卡）**
```bash
ollama pull qwen3.8:27b-q4_K_M        # 18GB；不要用 mxfp8/nvfp4（Blackwell 格式，V100 用不了）
cat > ~/ollama-models/qwen38.Modelfile <<'EOF'
FROM qwen3.8:27b-q4_K_M
PARAMETER num_ctx 32768
PARAMETER temperature 0.6
EOF
ollama create qwen38 -f ~/ollama-models/qwen38.Modelfile
```
- **必须显式关思考或降 reasoning_effort**，否则 token 消耗翻倍、单题墙钟直接失控（模型卡：thinking 默认开，可用 `reasoning_effort` 调；我们前期记录的"默认 xhigh"本次未证，但机制成立）。
- 若 ollama 侧遇到长上下文掉速/异常（头条作者原话："最好用 LLama.cpp 来跑，ollama 完全不行"），再上源码编译的 llama.cpp 兜底。

**C. Qwen3-Coder-Next（P1，双卡 52GB）**
```bash
ollama pull qwen3-coder-next:q4_K_M   # 52GB
# 关键：两卡必须都用上，且不要任何 CPU 卸载
CUDA_VISIBLE_DEVICES=0,1 OLLAMA_NUM_PARALLEL=1 ollama serve
```
- 落地前必须确认三件事（**本轮没找到公开证据，只能在 anolis 上实测**）：
  1. ollama 0.40.6 的 runner 对 52GB 模型是否会做 layer split 而不是整体 CPU 卸载；
  2. 是否有非官方的 `qwen3-coder-next` 更小 GGUF（社区量化比官方 Q4_K_M 小）——**HF 本轮不可达，未能核实**；
  3. 若必须卸载，则 `llama.cpp` 侧要**同时**开 `--moe-cache-mib`（默认 0=禁用），否则速度会塌到 ≈19 tok/s 量级（E9）。
- 若走独立 llama.cpp（需源码编译，`-DGGML_CUDA_ARCHITECTURES=70`），参数模板：
  ```
  llama-server -m qwen3-coder-next-q4_k_m.gguf \
      --split-mode layer --tensor-split 1,1 \
      -ngl 99 -c 16384 --batch-size 512 --ubatch-size 512 \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --parallel 1 --host 0.0.0.0 --port 8080
  ```
  （`--split-mode` 必须用 **layer**（llama.cpp 默认值），**不要用 tensor**——官方标 EXPERIMENTAL，且我们已有 MTP/DFlash2 在 tensor 模式下的崩溃 issue。）

### 6.3 冒烟测试清单（每个新模型必须全过，缺一不进 af-bench）

1. **输出完整性**：中文长输出 2000 token 无乱码、无重复、无截断（针对混合线性注意力家族的 qwen3.8 / qwen3-coder-next 必做）。
2. **tool calling 连通**：连续 10 轮工具调用不崩、不丢参数、能正确读回长日志。
3. **显存曲线**：4K → 8K → 16K → 32K 逐档记录 `nvidia-smi` 峰值，确认不会在长上下文处 OOM。
4. **速度衰减曲线**：8K / 32K / 128K 三个点的 decode tok/s（对照 E13 的 3090 曲线形状，看我们是否更平）。
5. **并发**：OLLAMA_NUM_PARALLEL=2 下每请求 tok/s 与合计 tok/s。
6. **同题对跑**：用 af-bench 抽 20 题（SWE-V / Terminal-Bench / τ²-bench 各若干），现役与新模型同题同 harness 对比**解题率**与**单题墙钟**两个轴，缺一不算数。

### 6.4 一句话回答本轮的问题

> 有模型比现役 qwen3-coder-30b 解题率高（`glm-4.7-flash` 单卡 19GB、`qwen3.8:27b` 单卡 18GB、`qwen3-coder-next` 双卡 52GB），但**没有一个能在相近墙钟成本下做到**——因为在 V100 上，解码速度由"权重是否 100% 常驻显存"决定：稠密 27B 要付出 3.5–5.4 倍的解码时间，80B-A3B MoE 只要有专家掉到 CPU 就会塌到 1/5 速度。**最优解不是换模型，而是把"19–20GB 全上卡 + 3B 激活"的 MoE 档位（glm-4.7-flash / qwen3-coder-30b）用足，同时用双卡余量做 A/B 探针。**

---

## 7. 本轮"未找到公开证据"清单（不得用记忆补齐）

1. **没有任何一条"Qwen3-Coder-Next 在 2×V100S-32GB（64GB）上"的社区实测**。中文社区里的 Qwen3-Coder-Next 实测都在 32GB 单卡（→ CPU 卸载）或 48GB 双卡（4090/A6000/5090）上。V100 组合是空白。
2. **`--n-cpu-moe` 在 V100 上量化代价的实测数据**：中文社区里没有针对 V100 的 MoE 专家卸载前后速度对比。公众号那篇 Strata 实验是 12GB 消费卡 + 4090 48GB，且页面标注"内容由 AI 生成"（D 级）。
3. **Qwen3-Coder-Next 的更小 GGUF 社区量化体积**：HF 本轮不可达（DNS 被污染），未能核实是否存在 < 45GB 的社区 Q4/Q3。
4. **Qwen3-Next-80B-A3B 在 256K ctx 下的 KV cache 精确占用**：未找到官方或社区的公开数字（只找到 Qwen3.8-27B 的等价数字）。
5. **Qwen3.8 系列 `reasoning_effort` 的官方默认值是否为 xhigh**：模型卡只说"可用 reasoning_effort 调节"，未给默认值；我们前期结论里的"默认 xhigh"本次**未证**。
6. **ModelScope 讨论区**的可引用帖子：本轮 ModelScope 模型检索 API 可用，但讨论区未拿到可引用内容，该渠道证据计为 0。
7. **小红书 / 微博 / 知乎**的高质量实测：本轮搜索通道未能稳定触达这三个站（360/搜狗索引里命中极少且多为转载），无一手实测可引。
8. **Qwen3.7 开放权重版的官方 ollama tag**：ollama 官方库 `/library/qwen3.7` 返回 404；仅有社区量化（如 `aratan/qwen3.7-35b-q4` 自称 8GB 显存 29 t/s，未能复核）。
9. **Qwen3-Coder-30B-A3B-Instruct 的官方 SWE-bench Verified 数字**：ollama 官方模型卡未列具体分数（本轮未找到该模型的官方 SWE-V），因此"新模型比现役强"缺少现役的同口径官方分作为基线，**必须在 af-bench 上实测对比，不能靠分数推断**。
