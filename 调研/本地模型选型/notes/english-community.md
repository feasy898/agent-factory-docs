# 英文社区实测调研：2026 下半年「32GB 卡上能跑的本地 agentic 编程模型」

- 调研日期：**2026-10-21**（本报告所有网页抓取、GitHub 读取、SSH 核验均在该日完成；文中"2026-XX-XX"一律为原文发布日期）
- 基准硬件（全文以此为准，不复述通用榜单）：**anolis-gpu-01 = 2× Tesla V100S-PCIE-32GB（sm_70 / CC 7.0，规格 900 GB/s，HBM2），125 GB 内存，driver 570.133.20，CUDA 12.6 工具链，ollama 0.40.6**
- 现役模型：`qwen3-coder-30b` = Qwen3-Coder-30B-A3B-Instruct-Q4_K_M（本地 18.5 GB；30.5B 总参 / 3.3B 激活；262144 ctx）
- 现役实测（本次会话前序，anolis）：**decode 135.7 tok/s、prompt 149.1 tok/s（num_ctx 8192）**；并发 2 时 109.7 tok/s/请求，合计约 219 tok/s
- 工作负载：af-bench 跑 SWE-bench Verified / Terminal-Bench / InjecAgent / τ²-bench 等 agentic 题型，**每题约 10 轮工具调用**；本地臂 = 零 API 成本量产臂，吞吐与单题墙钟同等重要

> 本报告是"英文社区"专线。与同批次 `chinese-community.md`（中文社区）、`v100-speed-data.md`（V100 速度库）、`engines-volta.md`（引擎矩阵）、`qwen-family.md`（Qwen 系全景）、`small-models.md`（小尺寸档）互补。**本报告独占的材料**：(a) 2026 H2 Hacker News 实测贴语料；(b) GitHub 上唯一一个为 **Tesla P100（sm_60，与我们 V100S 同代 Volta 前瞻）** 做的 llama.cpp 优化 fork（含其全部实测数据、NaN race 缺陷与复现方法）；(c) 本机 ollama 0.40.6 runner 的**源码级/二进制级**核验。

---

## 0. 调研方法与证据分级

### 0.1 本轮实际可用的信息通道（2026-10-21 实测）

| 通道 | 状态 | 说明 / 实测证据 |
|---|---|---|
| `hn.algolia.com/api/v1/*` | ✅ **本轮主力** | HN 全文检索 API（story + comment），带 `numericFilters` 时间窗过滤；本轮用它完成 2026 下半年（9–10 月为主）的帖子与评论级取证 |
| `github.com` + `raw.githubusercontent.com` | ✅ | 读 PR 正文、fork 仓库的 `p100-docs/*.md`、llama.cpp upstream 源码 |
| `hf-mirror.com/api/...` | ✅ | HF 官方 API 镜像，**本轮首次打通**（中文社区轮次记为不可达）；用来核对 GGUF 分片体积、模型 config.json 架构 |
| `artificialanalysis.ai` | ✅（curl + 内置浏览器渲染） | curl 拿得到 862 KB HTML 但榜单是 JS 表格；改用浏览器 `playwright.evaluate` 逐行取出 275 行榜单 |
| `openrouter.ai` / `swebench.com` | ✅ | SWE-bench 官方榜数据以 JSON 内嵌在 HTML 里，本轮已解析出全部 270 条提交记录 |
| `ollama.com/library/*` | ✅ | 官方模型卡 + tag 体积表（架构/上下文/是否 cloud-only 的第一手来源） |
| **`www.reddit.com` / `old.reddit.com`** | ❌ **不可达** | 本机 DNS 被污染（`getent hosts www.reddit.com` → `2001::1`；`huggingface.co` → Facebook 网段 `2a03:2880:...`）。curl 报 `FAIL`；内置浏览器导航后停在 `chrome-error://chromewebdata/`，`document.body.innerText` 长度 0。teddit.io 已不是 Reddit 镜像（现为 AI 可见度追踪 SaaS）；`allorigins` / `codetabs` / `corsproxy` / `thingproxy` 全部失败或要 API key；`libreddit.privacyredirect.com` 301 后无内容。**故本轮 Reddit 侧证据 = 0**，见 §9 |
| `x.com` / Twitter | ❌ | DNS 污染 + 需登录，无可用抓取路径 |
| Discord | ❌ | 需邀请/鉴权，无公开 API |
| `news.ycombinator.com` | ❌（但 `hn.algolia.com` 可用） | HN 正文站不可达，但其官方 API 镜像可达，足够做全文级取证 |
| `lmsys/livebench` | 未取 | 本轮未触达（GitHub API 触发 rate limit 403；HTML 树页未解析）。**未找到可引用的本轮证据** |

### 0.2 证据分级（本报告统一口径）

- **A｜官方自报**：厂商模型卡 / 官方 ollama 库 / 官方 GGUF 文件清单 / AA 官方榜（AA 榜对部分模型是**自己实测**，标 `*` 的是 AA 估算）
- **B｜第三方复现**：写明硬件、模型、量化、命令、参数的实测（**本报告的主力**）
- **C｜社区体感**：有观点无数字，或数字来自他人转述
- **D｜未验证 / 不可达**：明确标注，不补齐

---

## 1. 结论速览（TL;DR）

### 1.1 对核心假设的裁定

> **待验证假设**：「总参很大但激活参数很少的 MoE，可能同时做到比现役更强、比稠密 27B 更快」；「稠密 27B 在 V100 上解码会慢 3–4 倍」

| 子命题 | 裁定 | 决定性证据 |
|---|---|---|
| 稠密 27B 在老卡上比 3B 激活 MoE 慢 3–4 倍 | ✅ **成立，且可能更糟（4–5 倍）** | 2×Tesla P100（sm_60）跑 Qwen3.8-27B Q6_K：stock llama.cpp **17.51 t/s**，优化后 **33.2 t/s**〔B〕。而我们现役 30B-A3B 在 V100S 上是 **135.7 t/s** |
| MoE 比同代稠密模型「更快且更强」 | ✅ **成立**（但**我们已经占了这个便宜**） | PaulKeeble 2026-10-17：「the MOE models with few active parameters are just faster and easier to run… they behave a lot more like their peak size than the active parameter size」〔B/C〕 |
| 「MoE 又快又强」对我们意味着**换到 80B-A3B 就能双赢** | ⚠️ **需要修正** | 现役 qwen3-coder-30b **本身已经是 3.3B 激活的 MoE**。换到 80B-A3B 买到的是**能力**，**不是速度**——两者解码速度在同一量级（每 token 都要读 ~3B 激活权重） |
| 80B 级 MoE 的 Q4 权重（前期估 45 GB）放得下 64 GB 吗 | ✅ **放得下，但余量比预期紧** | 官方 Q4_K_M 实测 **48.40 GB**（4 分片）；ollama 库版 Q4_K_M **52 GB**。64 GB 总显存下余量仅 15.6 GB / 12 GB |
| `--n-cpu-moe`（CPU 专家卸载）在 V100 上可行吗 | 🟡 **技术上可行、代价大、且我们多半不需要** | 唯一直接证据：6 GB 显存笔记本跑 80B-A3B，`--cpu-moe --n-gpu-layers 999 --ctx-size 102400` → **17 t/s @ 100k ctx**〔B〕。对我们 64 GB 全显存的场景，CPU 卸载是主动降级 |

### 1.2 三条最重要的发现

**发现 A（最有用）：英文社区有一个专门为 Tesla P100（sm_60，与 V100S 同代）做的 llama.cpp 优化 fork，公开了完整实测数据。**
`Kmic-68/llama.cpp`（分支 `p100-optimizations`，"llama.cpp for 2x Tesla P100"）用 **2× Tesla P100-PCIE-16GB + Qwen3.8-27B Q6_K** 跑出了完整的 prefill/decode 曲线，并把「老卡（Pascal/Volta）上 llama.cpp 到底怎么才能跑快」写成了 `p100-docs/`（README / QUICKSTART / FINDINGS / CHANGES / THREE-GPU）。**这在我们的语境里价值极高**：它同时给了「稠密 27B 在老卡上的真实速度天花板」和「Volta/Pascal 上会踩的一串坑」（见 §4.2、§4.3）。**并且它暴露了一个 upstream 至今未修的 NaN race（§4.3），直接命中我们前期已知的「速度正常但输出损坏」风险。**

**发现 B（最关键的风控）：`qwen3_5` / `qwen3_next` 混合线性注意力架构在多卡上会**打断前缀缓存复用**，而我们的负载是每题 10 轮工具调用。**
P100 fork 的 FINDINGS 明确写：*"Qwen3.8 has 48 recurrent layers, and a recurrent state can't be rewound. Restoring a saved slot and resending the original prompt still reprocesses everything, because the saved state includes generated tokens."* 其对策是「先 `n_predict:0` 预填并保存 state，再 restore + 原文 + 后缀」——**在满深度时把 259,229 token 的重处理降到 10 token**〔B〕。
**含义**：现役 qwen3-coder-30b 是纯注意力（`qwen3_moe`），KV cache 可正常复用；换到 Qwen3-Coder-Next（`qwen3_next`，36 层递归 + 12 层全注意力）或 Qwen3.8-27B（`qwen3_5`，48 递归 + 16 全注意力）后，**每轮工具调用都要重算整个对话**——单题墙钟会显著变长。这是"解题率更高但墙钟不涨"这个命题**最可能破裂的地方**。

**发现 C（一个被忽略的现成杠杆）：我们的 ollama 0.40.6 **自带一个完整的独立 `llama-server` 二进制**，能力远超 ollama 的 API 暴露面。**
实测路径 `/home/pan-ding/.local/lib/ollama/llama-server`，版本 `0.7.0-dev (build 1, commit 620d2225c)`。它**支持** `--split-mode {none,layer,row,tensor}`、`--tensor-split`、`--cpu-moe` / `--n-cpu-moe N` / `--moe-cache-mib`、`--fit` / `--fit-target MiB0,MiB1` / `--fit-ctx`、`--cache-type-k/v`、`--spec-type draft-mtp` / `--spec-draft-n-max`、`--override-kv`。
**含义**：任务前提里「没有独立 llama-cli / llama-server 二进制」这条**需要修正**——我们不必受 ollama 参数面的限制，可以直接用 llama-server 起服务（llama.cpp OpenAI 兼容端点），从而拿到 `-sm tensor`、`-fa`、`-ctk q4_0`、`--fit-target` 这些 ollama 暴露不了的旋钮。

---

## 2. 候选清单总表

> 体积列全部是**本轮亲自抓取的**官方数字：Qwen 官方 GGUF 仓库 `hf-mirror.com/api/models/Qwen/*/tree/main?recursive=true`、Unsloth 官方 GGUF 仓库、`ollama.com/library/*/tags`。分数列严格区分"厂商自报"与"第三方/官方榜复现"。

| 模型 | 厂商 | 架构（总参 / 激活） | Q4 体积 (GB) | ctx | GGUF 可得性 | 官方 agentic 分数（自报） | 第三方/榜单反馈（本轮实测证据） | 我们的适配判断 |
|---|---|---|---|---|---|---|---|---|
| **Qwen3-Coder-Next** | Alibaba | MoE `qwen3_next` 80B / **3B**（512 专家 top-10，48 层=36 递归+12 全注意力） | **48.40**（Qwen 官方 Q4_K_M）/ 49.61（Unsloth UD-Q4_K_XL）/ **52**（ollama 库版） | 256K | ✅ 官方 GGUF + ollama + Unsloth | SWE-bench Verified **70.6%**（厂商自报）｜Terminal-Bench 2.0 36.2 | **SWE-bench 官方榜无该模型条目**（0 命中）→ 70.6 不可跨榜比较。社区：7900XTX 24GB 上 39 t/s（genpfault）**同模型另有 10 t/s 的报告**（lnenad）；3090+4090 48GB Q4_0+量化 KV 96k → 1400 pp / 80 tps（redrove）；Spark 25–39 t/s；6GB 显存笔记本 `--cpu-moe` 17 t/s @100k | 🟡 **唯一"能力显著更高"的候选，但 3 个硬伤**：① 48.4 GB 权重 + 262K KV 在 64 GB 上贴边；② 混合线性注意力打断前缀缓存（发现 B）；③ 社区实测速度方差极大（10 → 80 t/s），说明**配置即命运** |
| **Qwen3.8-27B** | Alibaba | **稠密** `qwen3_5` 27B（64 层=48 递归+16 全注意力，MMTP 1 层） | 16.46（Unsloth UD-Q4_K_M）/ 16.06（Q4_0）/ 29.05（Q8_0）；ollama `qwen3.8:27b` **18 GB** | 256K | ✅ Unsloth + ollama | Terminal-Bench 2.1 **73.0**｜SWE-bench Pro 61.7｜QwenSWE-Bench 79.0（均为自报） | AA Intelligence Index **34 (xhigh)** / 28 (medium) / 26 (low) / 20 (non-reasoning) — 全部模型中稠密档最高 | 🟢 能力天花板，但**速度与成本双输**：2×P100 实测 17.5–33.2 t/s（无 MTP），我们 V100S 上推算 30–60 t/s，**比现役慢 2.5–4.5 倍**；且默认 xhigh reasoning 的 token 膨胀，OliveronData：「generates stupid amount of tokens even for the simplest tasks」 |
| **Qwen3.6-35B-A3B** | Alibaba | MoE `qwen3_5_moe` 35B / **3B**（256 专家 top-8，40 层） | 22.13（Unsloth UD-Q4_K_M）/ 21.71（MXFP4_MOE）；ollama `qwen3.6:35b-a3b` **23–24 GB** | 256K | ✅ Unsloth + ollama | AA II **18**（reasoning）/ 15\*（non-reasoning） | 2×V100(48GB) 跑 **Qwen3.6-27B（稠密）Q8_0** → 22 t/s（<65k ctx）/ 13 t/s（近满）〔neutrinobro〕；社区反馈 Qwen3.6 4-bit「kept getting stuck in circles」〔smallerize〕 | 🟡 速度档与现役同级（3B 激活）、能力档低于 Coder-Next，但**同样有混合线性注意力的前缀缓存问题**；thinking token 需控 |
| **GLM-4.7-Flash** | Z.ai | MoE **31.2B / 3B**（MIT 许可） | **19**（ollama Q4_K_M）/ 32（q8_0）/ 60（bf16） | 198K | ✅ ollama 官方 | AA II **14.87**（AA 标为估算）｜自报 SWE-V 59.2、τ²-Bench 79.5 | 社区 action test：**GLM-4.7-Flash-4bit 21/36 (58.3%)**，同测试里 Gemma 4 26B-A4B 31/36、Qwen3.5-9B 30/36〔LeoisNotAI〕；但 ecshafer「glm is the best at coding agentically」；smallerize「at least keeps making progress」 | 🟡 单卡 19 GB、极好部署、速度大概率与现役同级；**但 36 题自测里明显落后**，且比现役晚一代却更弱——**不是升级，是平移** |
| **Gemma 4 26B-A4B** | Google | MoE 26B / 4B | — | 256K | ✅（社区已用） | AA II 17\*（估算） | **LeoisNotAI 自测 31/36 (86.1%)，本轮候选中最高**；Netron 3.5 Bolt 74B-A9B 同为 NVIDIA 开源 MoE（AA II 21） | 🟡 值得进第二轮：4B 激活 → 速度友好；26B Q4 约 15 GB 单卡可放。**社区样本量仅 1** |
| **Qwen3-Coder-30B-A3B-Instruct（现役）** | Alibaba | MoE `qwen3_moe` 30.5B / **3.3B**（128 专家 top-8，48 层纯注意力） | 18.56（Unsloth Q4_K_M）/ 18.5（本地实测） | 262K | ✅ ollama 官方 | — | **SWE-bench 官方榜有 5 条提交，最高 60.4%**（EntroPO+R2E，2025-09-01；OpenHands 51.6%）。AA II 仅 10 | ⬅️ **基准**。纯注意力 ⇒ 前缀缓存正常复用，这是它相对新候选的隐性优势 |
| **Qwen3.8-Flash-Next** | Alibaba | MoE `qwen4_exp` **125B-A6B + 51B engram** | — | 262K | ❌ **本地拿不到**：ollama 库中为 **cloud-only**；`unsloth/Qwen3.8-Flash-Next-GGUF` 只有 `mmproj-*.gguf` 与 `mtp-*.gguf`，**无主权重** | AA II **40**（API 侧） | bitexploder 用 **3-bit XXS 量化在 V100 上跑到 >100 t/s**，DeepSWE 官方 harness + Pi：「neck and neck with Opus 4.7 and Sonnet 5」；woctordho：可在 40 GiB 显存内 LoRA 训练 | 🔵 **观察名单，不在本轮可选项内**。但它是 2026 H2 社区最热的本地模型话题，一旦放出权重就应立刻重评 |
| **Qwen3.5-122B-A10B** | Alibaba | MoE 122B / 10B | — | 262K | ✅ | AA II 16（reasoning）/ 18\* | PaulKeeble：3080 10GB + 32GB RAM 跑「127B MoE coder」→ 40–50 t/s @ 65k ctx，且「a lot more usable than a Quantised Qwen3.8-27B」 | 🔵 太重，64 GB 装不下完整 Q4；只有 `--n-cpu-moe` 路线可跑（17 t/s 量级） |

---

## 3. 2026 下半年英文社区实测贴语料（HN 为主）

> 检索方法：`hn.algolia.com/api/v1/search` + `search_by_date`，`tags=comment|story`，`numericFilters=created_at_i>1759276800`（2025-10-01 起），按硬件/模型关键词交叉检索；命中后用 `/api/v1/items/{id}` 取评论全文与父评论上下文。**所有引用均为本轮亲自读到原文。**

### 3.1 唯一一位明确"为 V100 优化 llama.cpp"的社区作者：bitexploder

这位作者是本轮英文社区最有价值的单一信息源——他**明确以 V100 为目标**做推理优化，并把全部实测贴在 HN 公开。

| 日期 | HN item | 原文要点（逐条引用） |
|---|---|---|
| 2026-10-02 | [49933921](https://news.ycombinator.com/item?id=49933921) | *"For reference I have a single V100 running around **900 t/s prefill and 100 t/s decode** during DeepSWE runs on 27B (4 bit quant)."*；*"I have had Claude optimizing llama.cpp for about a week and am at around **300 t/s decode so far on two ancient V100s @ 64 GB RAM**."*；*"Qwen 27B 3.8 **matched Sonnet 5 in the 17 DeepSWE tasks** I have run so far, solving the exact same 7 it has."* |
| 2026-10-04 | [49955472](https://news.ycombinator.com/item?id=49955472) | *"I am **optimizing for V100**. EOL cards on EOL CUDA… **150-160 t/s on 2 GPU for 27B and 125 t/s on Flash Next**."* |
| 2026-10-04 | [49955352](https://news.ycombinator.com/item?id=49955352) | *"I am benching Flash next on a **3 bit XXS quant**… Using **DeepSWE official harness and Pi** with absolutely zero benchmaxx or harness config… it is **neck and neck with Opus 4.7 and Sonnet 5**."*；*"I am doing this on **$1500 of data center leftover GPUs (V100)**."* |
| 2026-09-24 | [49836303](https://news.ycombinator.com/item?id=49836303) | *"There also exists a **$600-800 GPU that can run Qwen 27B 3.8 @ like 60 t/s**… I have a few V100 GPU running Qwen 27B and they do all the work overnight."* |
| 2026-09-29 | [49900994](https://news.ycombinator.com/item?id=49900994) | *"a **$750 GPU (V100) that can run 4-bit 27B quant at >90 t/s**… I have Qwen Flash Next at **>100 t/s**."* |

**⚠️ 重要折扣（必须写明）**：以上 100/150-160/300 t/s 的数字来自 bitexploder **自己用 Claude 优化过的私有 llama.cpp 分支**，不是 stock llama.cpp 可复现的。而且它们**与带宽算术不自洽**：27B 稠密 Q4 ≈ 16 GB，单卡 900 GB/s 的理论上限约 56 t/s，实测 100 t/s 意味着要么量化更激进、要么模型并非稠密。**因此本报告只把这些数字当作"上界探针"，不作为选型依据。** 选型依据用下一节 P100 fork 的可复现数据。

### 3.2 其他可直接对照我们硬件的社区实测

| 日期 | 作者 / HN item | 硬件 / 配置 | 实测 | 对我们的意义 |
|---|---|---|---|---|
| 2026-05-07 | [neutrinobro](https://news.ycombinator.com/item?id=48049546) | **2× Tesla V100（48 GB 合计）** + 128 GB 内存，Qwen3.6-27B **Q8_0**，`llama-server -m … -c 131072 --tensor-split 0.4,0.6 --batch-size 256 --cont-batching --flash-attn on -ngl 999 --threads 16 --jinja` | **~22 tok/s**（ctx < 65K）→ **~13 tok/s**（ctx 接近满，"lots of swapping to RAM"） | 🔴 **与我们的机器最像的一手数据**：V100 + `--tensor-split` + `--flash-attn on` 确实能跑；但**长上下文掉速到 60%**。同帖主观评价：在 ~70 kloc C++ 代码库上「comparable to claude sonnet 4.6」 |
| 2026-06-15 | [xiaoyu2006](https://news.ycombinator.com/item?id=48537533) | V100 32G **SXM2 转 PCIe**，llama.cpp Q4_K_M Qwen3.6-27B | — | 证明 V100-32G + PCIe 适配这条路社区在走 |
| 2026-06-29 | [georgeven](https://news.ycombinator.com/item?id=48722637) | $1500 主机，**3× V100** | 50 t/s | 3 卡 V100 也就 50 t/s 量级（具体模型未给） |
| 2026-10-13 | [karmakaze](https://news.ycombinator.com/item?id=50080248) | **2× AMD R9700**（32GB×2, RDNA4, 1.79 TB/s） | Qwen3.8-27B **MXFP4 150–250 tok/s** | 稠密 27B 在 2×32GB 高速卡上能到 150–250 t/s；**我们只有 1.8 TB/s 总量（V100S PCIe），且不能跑 MXFP4** → 这是稠密 27B 在我们机器上的**乐观上限** |
| 2026-06-17 | [maldie](https://news.ycombinator.com/item?id=48569943) | RTX 4090，Qwen3.6-27B **Unsloth UD-Q4_K_XL + MTP**，`--spec-type draft-mtp --spec-draft-n-max 3 --fa on -c 75000 -ngl 99` | **115 tok/s**（`--spec-draft-n-max 4` → 125） | 🔵 **MTP 投机解码在 Qwen3.6/3.8 上的实测配方**（这两个模型 config 里都有 `mtp_num_hidden_layers=1`）。同帖警告：**KV cache 量化会让缓存掉回 CPU、性能崩塌** |
| 2026-10-19 | [spottedmarley](https://news.ycombinator.com/item?id=50150828) | 自研 harness，GB10 128GB | Qwen3.5:122b ≈ Sonnet 4.5 编码；**Qwen3.8:27b-gsq-iq3s 优于两者**，~50–60 t/s | 第三方在**自研 harness**（与我们 af-bench 同构）上把 Qwen3.8-27B 排在 Sonnet 4.5 之上。**注意 IQ3_S 这种超低 bit** |
| 2026-10-17 | [PaulKeeble](https://news.ycombinator.com/item?id=50129753) | 3080 10GB + 32GB RAM | 「qwen-next coder」127B MoE → **40–50 t/s @ 65k ctx** | 🔴 **对核心假设最直接的社区表态**：「the MOE models with few active parameters are just faster and easier to run… they behave a lot more like their peak size than the active parameter size」「RAM is going to be the big bottleneck for MOE」 |
| 2026-07-08 | [UncleOxidant](https://news.ycombinator.com/item?id=48834700) | — | *"Qwen3-coder-next is very usable. But **I don't think it's as good as Qwen3.6-27B** (though it does run faster on my hardware)."* | 🔴 **与厂商口径相反的社区判断**：Coder-Next 未必强于同代 27B |
| 2026-05-07 | [smallerize](https://news.ycombinator.com/item?id=48050908) | — | *"The (unsloth dynamic) 4-bit quants of Qwen 3.6 **kept getting stuck in circles**… **GLM 4.7 Flash at least keeps making progress**"* | 🔴 量化 MoE 的"打转不收敛"是社区反复出现的失败模式——**正好命中我们"完成度纪律先于绝对能力"的前期结论** |
| 2026-10-14 | [LeoisNotAI](https://news.ycombinator.com/item?id=50088324) | 自有 laptop action test（36 题） | **Gemma 4 26B-A4B 31/36 (86.1%)** > Qwen3.5-9B 30/36 (83.3%) > **GLM-4.7-Flash-4bit 21/36 (58.3%)** | 唯一一份带数字的"本地小模型 agent 动作测试"横评。**样本量 1，但可用于初筛** |
| 2026-09-30 | [OliveronData](https://news.ycombinator.com/item?id=49910341) | — | *"Qwen 3.8 27b… **generates stupid amount of tokens even for the simplest tasks** and gets feedback from the harness to eventually produce something right."* | 🔴 对我们"每题 10 轮、单题墙钟"的负载是**直接负面证据** |
| 2026-06-15 | [ecshafer](https://news.ycombinator.com/item?id=48544094) | 服务器 + ollama（gemma-4 / glm 4.7 flash / qwen 3.6） | *"**glm is the best at coding agentically**"* | C 级体感，但方向与 LeoisNotAI 相反 → 记为噪声 |

### 3.3 Qwen3-Coder-Next 的 HN 主帖（735 分 / 429 评论）里的速度数字汇总

主帖：`Qwen3-Coder-Next`（2026-02-03，735 分）https://news.ycombinator.com/item?id=46872706。本轮把其中所有带硬件+速度的评论摘出：

| 评论 | 硬件 | 配置 | 实测 |
|---|---|---|---|
| [redrove](https://news.ycombinator.com/item?id=46872706) | **3090 + 4090（48 GB 合计）** | Q4_0 + 量化 KV，96k ctx | **1400 pp / 80 tps** |
| [genpfault](https://news.ycombinator.com/item?id=46872706) | RX 7900 XTX 24GB（Vulkan） | `unsloth/...:UD-Q4_K_XL --fit on --ctx-size 32768` | **~39 tok/s @ 60% GPU util** |
| [lnenad](https://news.ycombinator.com/item?id=46872706) | RX 7900 XTX 24GB | 全显存 + 60 GB 内存 | **~10 tok/s**（同模型同卡，**与上一行差 4 倍**） |
| [predkambrij](https://news.ycombinator.com/item?id=46872706) | 笔记本 6GB 显存 + DDR5 | **`--cpu-moe --n-gpu-layers 999 --ctx-size 102400`** | **17 tok/s @ 100k ctx** |
| [cmrdporcupine](https://news.ycombinator.com/item?id=46872706) | NVIDIA Spark | Q4_K_XL | 25–30 tok/s（one-shot 30–39），200k+ ctx 用 ~50 GB 内存 |
| [redwood_](https://news.ycombinator.com/item?id=46872706) | Framework Desktop 128GB（ROCm） | UD-Q4_K_XL | 35–40 t/s 输出，200–300 t/s eval |
| [Tepix](https://news.ycombinator.com/item?id=46872706) | Strix Halo | Q8_0 | 32 tok/s，128k ctx |
| [dust42](https://news.ycombinator.com/item?id=46872706) | M1 64GB | Q4_K_M llama.cpp | 20 tok/s（MLX 2× 快但 KV 分支有 bug） |
| [Aurornis](https://news.ycombinator.com/item?id=46872706) | — | Q2 / Q4 | *"definitely not at Sonnet 4.5 level… gets stuck in thinking loops"* |
| [Kostic](https://news.ycombinator.com/item?id=46872706) | — | — | *"I would not go below q8 if comparing to sonnet"* |
| [segmondy](https://news.ycombinator.com/item?id=46872706) | — | Q6_K_XL | *"almost on par with the raw weights and should let you have 128k-256k context"* |
| [petya415](https://news.ycombinator.com/item?id=46968836) | **RTX 5090 32GB** + 9950X3D，ollama，kv q8 | 128k ctx，10 个真实编码负载 | 模型 51 GB，**53% CPU / 47% GPU 拆分**，**恒定 12 tok/s**，GPU util 仅 3–4% |

**结论（社区侧）**：Qwen3-Coder-Next 在 24–32 GB 卡上的实测跨度是 **10 → 80 tok/s**，差 8 倍。决定因素不是模型，是**权重是否 100% 常驻显存**。petya415 的 5090 案例（51 GB 塞 32 GB → 强制 CPU 卸载 → 12 tok/s）是反面教材；redrove 的 3090+4090（48 GB 装 48.4 GB 权重）是正面教材。
**对我们的直接含义**：我们的 64 GB 总显存刚好够放 48.4 GB 权重（Qwen 官方 Q4_K_M）+ KV，**前提是全程不上 CPU**；一旦任何一层溢出到 CPU，就会掉进 petya415 那个 12 tok/s 的坑。

### 3.4 其他 2026 H2 相关 HN 条目（摘要）

- [50168132](https://news.ycombinator.com/item?id=50168132) `BigMoeOnEdge`（2026-10-20）：在 llama.cpp 上做"大 MoE 边缘流式"分层。宣称「35B on phone 12GB RAM 10 tok/s decode, 100-300+ prefill; Windows/Mac even more: 25+ tok/s 16 gb RAM」。→ **[C/D] 级**，无第三方复现，但方向与"MoE 权重分层卸载"一致。
- [50034625](https://news.ycombinator.com/item?id=50034625) woctordho（2026-10-10）：**Qwen3.8-Flash-Next = 125B-A6B + 51B engram**，可在 40 GiB 显存内 LoRA 训练、Strix Halo 上 200 t/s 训练速度。→ **这是本轮唯一说清 Flash-Next 参数规模的一手来源**。
- [50089834](https://news.ycombinator.com/item?id=50089834)（2026-10-14）：*"We found 110 reward hacks and grading bugs in Terminal-Bench, DeepSWE, and BFCL"* —— **对我们 harness 判分可信度的重要外部信号**。
- [49766208](https://news.ycombinator.com/item?id=49766208)（2026-09-19）：*"We found defects in 37 of DeepSWE's 113 tasks"* —— 同上。
- [50148629](https://news.ycombinator.com/item?id=50148629) kristopolous（2026-10-19）：*"AA prices are always kind of hand wavy for open models… rent a cheap gpu and run inference yourself"* —— 与我们"本地臂 = 零 API 成本"的定位同构。

---

## 4. 重点候选展开

### 4.1 Qwen3-Coder-Next（80B-A3B）— 唯一"能力显著更高"的候选

**架构（官方 config.json，本轮从 `hf-mirror.com/Qwen/Qwen3-Coder-Next/raw/main/config.json` 直读）**
```
architectures      = ["Qwen3NextForCausalLM"]
model_type         = qwen3_next
num_hidden_layers  = 48          full_attention_interval = 4   → 12 层全注意力 + 36 层线性注意力
hidden_size        = 2048        num_experts = 512, num_experts_per_tok = 10
moe_intermediate_size = 512      shared_expert_intermediate_size = 512
num_attention_heads= 16          num_key_value_heads = 2, head_dim = 256
vocab_size         = 151936      max_position_embeddings = 262144
```
AA 官方模型页：**Total parameters 79.7B / Active parameters 3B** / 256k ctx / **Apache 2.0** / **非 reasoning 模型**（"Reasoning: No"）。

**体积（本轮实测，官方 Qwen GGUF 仓库）**
| 量化 | 体积 | 64 GB 装下后余量 |
|---|---|---|
| **Q4_K_M** | **48.40 GB**（15.52+14.87+14.50+3.51） | **15.60 GB** |
| Q5_K_M | 56.71 GB | 7.29 GB ⚠️ |
| Q6_K | 65.53 GB | ❌ 装不下 |
| Q8_0 | 84.81 GB | ❌ |
| F16 | 159.46 GB | ❌ |
| Unsloth UD-Q4_K_XL | 49.61 GB | 14.39 GB |
| Unsloth MXFP4_MOE | 48.03 GB | 15.97 GB（**但 MXFP4 在 V100 上无原生加速**） |
| ollama 库版 Q4_K_M | 52 GB | 12 GB |
| Unsloth UD-Q2_K_XL | 26.76 GB | 37.24 GB（质量代价大） |
| Unsloth UD-Q3_K_M | 35.94 GB | 28.06 GB |

> **修正前期结论**：前期"Q4 约 45 GB"偏低。官方 Q4_K_M 是 **48.40 GB**；ollama 库版是 **52 GB**。两者都能进 64 GB，但**余量是 12–15.6 GB，不是"从容"**。

**KV cache 账（本轮用 config 算，未实测）**
全注意力层只有 12/48 层，KV heads=2，head_dim=256，f16：
`2 (K,V) × 12 层 × 2 heads × 256 dim × 2 B = 24,576 B/token ≈ 24 KiB/token`
→ **262,144 ctx 全量 KV ≈ 6.3 GB**（q4_0 量化后 ≈ 3.2 GB）。这解释了社区"Reserving it costs nothing until it fills"的说法。
对比现役 qwen3-coder-30b（48 层**全**注意力、32 heads/4 kv heads、head_dim 128）：`2×48×4×128×2 = 98,304 B ≈ 96 KiB/token` → 262k ctx 需 **25.8 GB** KV，**单卡 32 GB 装不下**（这也解释了为什么现役实测用 `num_ctx 8192`）。
🔵 **这是一个被低估的收益：Coder-Next 让我们的 harness 第一次能在本地跑满 262K 长上下文**（"能读长日志"是我们负载的明确需求），而现役在长上下文下会被 KV 挤爆或掉速（neutrinobro 的 22 → 13 t/s 就是这个现象）。

**速度推算（本轮，基于 P100 fork 的可复现数据外推）**
P100 fork 在 2×Tesla P100-16GB（sm_60, 732 GB/s 规格）上跑 **同族** Qwen3.8-27B Q6_K：stock **17.51 t/s** → 优化后 **33.2 t/s**（无 MTP）、**54 t/s**（MTP @2k）、**29–35 t/s**（MTP @260k）。
Coder-Next 每 token 读取量 ≈ 3B 激活 × 4 bit ≈ **1.5 GB**（加稠密部分），vs 稠密 27B Q6_K 的 ≈ 16 GB → **每 token 字节数约为稠密 27B 的 1/8～1/10**。
**推断（未实测）**：2×V100S（合计 1.8 TB/s 规格，sm_70 有真 FP16 张量核）上，Coder-Next Q4_K_M 预期 **90–140 t/s decode**，与现役 135.7 t/s **同量级**。这是"**墙钟不涨、解题率大涨**"在速度侧的成立条件。

**三个硬伤**
1. **前缀缓存被打断（发现 B）**：36 层线性注意力 ⇒ 递归 state 不可回退 ⇒ 我们 10 轮工具调用每轮都要重算全对话。P100 fork 给出的对策是 `n_predict:0` 预填 + save/restore + 原文后缀，**但这要求 harness 侧改造**。
2. **社区速度方差 10–80 t/s**：全在显存 vs 部分卸载的差别；我们只有一次机会做对。
3. **官方榜缺席**：SWE-bench 官方榜**没有** Qwen3-Coder-Next 的条目（本轮解析 270 条提交记录，"Qwen3-Coder-Next" 命中 **0**）。**70.6% 是厂商自报、不可跨榜比较**——而现役模型在同榜有 **60.4%** 的第三方提交。

**社区对「它到底强不强」并不一致**：UncleOxidant 认为"不如 Qwen3.6-27B"，厂商自报 70.6%，AA Intelligence Index 只有 **9**（因为它是非 reasoning 模型，AA v4.3.2 的十项评测里 reasoning 类占大头）。**AA II 对非 reasoning 的编码模型系统性低估**——本轮多个来源都指出这一点（HN 上 *"some benchmarks show Qwen 3.8 27b is at Opus 4.6 levels"* vs *"not smarter than other 27b models"* 的对立）。**我们不应以 AA II 给 Coder-Next 排序。**

### 4.2 GitHub `Kmic-68/llama.cpp` —— 2×Tesla P100 优化 fork（本轮最重要的单一工件）

仓库：https://github.com/Kmic-68/llama.cpp ，分支 `p100-optimizations`，自述 *"llama.cpp for 2x Tesla P100 — A fork of llama.cpp with CUDA work for Pascal (sm_60), which upstream mostly leaves on generic paths."*
文档目录 `p100-docs/`：`README.md` / `QUICKSTART.md` / `FINDINGS.md` / `CHANGES.md` / `BUILD.md` / `THREE-GPU.md`；另有 `OPTLOG.md` 全量尝试记录。

**为什么它对我们价值极高**：P100 = Tesla 代 sm_60，与我们的 V100S = sm_70 同代；同 PCIe、无 NVLink、同一张 llama.cpp 代码。**它把「老卡上 llama.cpp 怎么跑快、哪些坑会炸」写成了可复现的工程文档。**

#### 4.2.1 它的实测成绩（2×Tesla P100-16GB，Qwen3.8-27B Q6_K + q4_0 KV，tensor split）

| 指标 | upstream（fork 基线） | 该 fork |
|---|---|---|
| decode `tg256`（无 MTP） | 17.51 t/s | **33.2 t/s** |
| decode + MTP，2k ctx | — | **54 t/s** |
| decode + MTP，260k ctx | — | **29–35 t/s** |
| prefill `pp2048` @ depth 0 | ~250 t/s | **493 t/s** |
| prefill @ 260k ctx | — | 123 t/s（填充）/ 153 t/s（已载入上下文上提问） |
| perplexity（gate corpus, -c 4096） | — | 2.6101 |
| Q5_K_M + MTP 单请求 | 34–40 t/s | **56–64 t/s** |
| Q5_K_M + MTP 两并发 | 7–8 t/s | 30–38 t/s |

**深度曲线（2k → 260k）**：decode 54 → 55 → 46 → 44 → 38 → 37 → 38 → 32 → 29 → 33 t/s；prefill 454 → 423 → 342 → 257 → 206 → 175 → 156 → 140 → 127 → 123 t/s。填满 260k 上下文约 **25 分钟**。

#### 4.2.2 它的运行命令（QUICKSTART.md 原文，我们可直接照抄改造）

```
GGML_CUDA_P2P=1 GGML_CUDA_GRAPHS_PRE_VOLTA=3 \
LLAMA_SPEC_SAMPLE_TEMP=1.0 LLAMA_SPEC_DRAFT_TOPK=20 \
./build-opt/bin/llama-server \
  -m /path/to/Qwen3.8-27B-Q6_K.gguf \
  -ngl 99 -sm tensor -fa 1 -ctk q4_0 -ctv q4_0 \
  -c 262144 -b 32768 -ub 2048 -np 1 \
  --spec-type draft-mtp --spec-draft-n-max 4 --spec-draft-p-min 0.2 \
  -ngld 99 -ubd 64 -ctkd q4_0 -ctvd q4_0 \
  --jinja --temp 1.0 --top-k 20 --top-p 0.95 --min-p 0.0 \
  --host 0.0.0.0 --port 8080
```

逐条理由（QUICKSTART 原表）：
| flag | 为什么 |
|---|---|
| `-sm tensor` | 把每一层劈到两张卡。"Needed to fit the full context"；**且 "Tensor split requires flash attention"** |
| `-fa 1` | flash attention，tensor split 的前提 |
| `-ctk q4_0 -ctv q4_0` | q4_0 KV cache。"An f16 cache doesn't fit at 262k"（**且见 §4.3 的 NaN race：f16/q8_0 KV 在 pre-Volta 上会出 NaN**） |
| `-c 262144` | 满 ctx，"Reserving it costs nothing until it fills" |
| `-np 1` | 单 slot（每个 slot 都独享一份完整 KV） |
| `-b 32768` | **MTP 在长上下文时必需**；更大的 batch 会让 draft 接受率崩掉 |
| `-ub 2048` | 每 GPU pass 的 token 数；2048 是 262k 下还留 VRAM 余量的最快 prefill |
| `--spec-type draft-mtp --spec-draft-n-max 4 --spec-draft-p-min 0.2` | 用模型自带 MTP 头做投机解码 |
| `-ngld 99 -ubd 64 -ctkd q4_0 -ctvd q4_0` | draft 层放 GPU、独立小 ubatch 与 q4_0 缓存；**不加 `-ubd 64` 会在满 ctx 时 OOM** |
| `--top-p 0.95 --min-p 0.0 --top-k 20` | 模型卡采样；GGUF 不带 min-p，llama.cpp 默认 0.05 会失配 |
| `GGML_CUDA_P2P=1` | 卡间直接拷贝，**不经主机内存** |
| `GGML_CUDA_GRAPHS_PRE_VOLTA=3` | 只给单 token MTP draft 步开 CUDA graphs（全量 `1` 在满 ctx 时 VRAM 不够） |

VRAM 实测（每卡，满 262k ctx）：纯文本 `-ub 2048` → GPU0 余 ~1.7–1.9 GiB；带 vision → ~1.1 GiB。**"VRAM use grows as the context fills, so check it with a full prompt, not a short one."**（→ 冒烟必须用长 prompt 测，不能只用短 prompt）

#### 4.2.3 它的「老卡性能规律」（FINDINGS.md，可直接迁移到 V100S）

- 🔴 **"The decode matvec is bound by global memory instructions, not bandwidth."** —— Volta/Pascal 上 decode 的瓶颈是**全局内存指令数**，不是显存带宽。这解释了为什么「激活重读」比「权重读取」更贵，也是稠密模型在老卡上掉速的结构性原因。
- 🔴 **"The activation, not the weights, is the bottleneck. Every block re-reads the q8_1 activation, so its cost scales with block count."**
- 🔵 **"Achievable bandwidth is ~605 GB/s per card, not the 732 on the spec sheet. Decode reaches ~490 GB/s effective."** → 对我们的 **V100S（规格 900 GB/s）**，可望拿到 **~750–800 GB/s** 可用带宽、decode 有效 ~600–650 GB/s。**这张表可以直接用来做 our 机器的速度上限估算。**
- 🔵 **"Long prefill is bound by power, not instructions."** P100 在 175 W 功耗墙下跑到 ~13 TFLOPS fp16。**V100S 的 300 W 板卡上限更高**，prefill 潜力更好。
- 🔴 **"Alignment is a wall. Every quantized block is 2 mod 4 bytes, so a 4-byte quant word needs two loads."**
- 🔵 **"CUDA graphs work on Pascal. Upstream disables them by architecture. They're +6.7% on the speculative path but −2% on plain decode, so they ship opt-in."**
  - 🟢 **本轮 upstream 源码核验（直接证据）**：`ggml/src/ggml-cuda/ggml-cuda.cu` 中 `if (ggml_cuda_info().devices[cuda_ctx->device].cc < GGML_CUDA_CC_VOLTA) { graph->disable_due_to_gpu_arch = true; }`，且 `common.cuh` 定义 `#define GGML_CUDA_CC_VOLTA 700`。
    → **upstream 只对 cc < 7.0 禁 CUDA graphs。我们的 V100S 是 cc 7.0 ⇒ stock llama.cpp 在我们卡上就默认开 graphs，不需要 P100 fork 那套 `GGML_CUDA_GRAPHS_PRE_VOLTA` 改造。** 这是 P100 数字对我们**偏保守**的一个理由。
- 🔴 **"The fork shipped two data races of its own making for weeks before they were found. Both are fixed, and both passed the full `test-backend-ops` suite the whole time."** FINDINGS 详述：① GEMM attention softmax 写概率时还在读分数，长 prompt 会损坏若干行、fp16 下可 NaN；② **tensor-parallel peer copy 可能在对方 ADD 读走之前覆盖 all-reduce 缓冲区，命中 decode 和 MTP**；"With the race forced, acceptance fell from 79% to 43%." → **「测试全过」不能证明输出正确**。这对我们是硬提醒：af-bench 的判分必须能抓到"输出损坏"，不能只看 harness 跑完。
- 🔴 **"Races need repeated unsynchronised runs, deliberate delay injection, or an in-op self-check."**
- 🔵 **长上下文 checkpoint 技巧**："Checkpoints only help if the next query extends them. Qwen3.8 has 48 recurrent layers, and a recurrent state can't be rewound. Restoring a saved slot and resending the original prompt still reprocesses everything… The recipe: prefill with `"n_predict": 0`, save, then restore and send the same text plus a suffix. At full depth that processed 10 tokens instead of 259,229." → **发现 B 的工程解法**。
- 🔵 **"On the default (non-NCCL) 3-GPU path, nvprof attributes about **57% of prefill time to exchange** at a 16k depth, and 54% at 64k."**（THREE-GPU.md / PR#2）→ 🔴 **多卡 prefill 的卡间交换开销是主导项**。优化后的 fork 用 "Hide the tensor-parallel exchange"（分块重叠）把它压到约 7%（nsys），**"+4.5%" 的分块发送 + 下一层权重反量化填充等待**。
  → 对我们：2×V100S 是 **PCIe**（V100S-PCIE-32GB），**P2P 是否可用必须实测**。P100 fork 用 `GGML_CUDA_P2P=1`；若我们的卡不支持 P2P，交换会走主机内存，prefill 会显著变慢。
  - 另注：FINDINGS 记录 "internal AllReduce on Pascal: **−17%**, it assumes NVLink, and these are PCIe cards" —— **不要指望在 PCIe 卡上开 NCCL/AllReduce**。

### 4.3 🔴 上游至今未修的 Volta/Pascal **NaN race**（本轮新发现，直接命中我们的已知风险）

**出处**：`Kmic-68/llama.cpp` PR #4 *"cuda: barrier before fattn_gemm_softmax reuses its shared reduction s…"*，2026-10-08 提出，2026-10-18 由 fork 维护者合并进 **fork 自己的 `p100-optimizations` 分支**（**未推送到 ggml-org/llama.cpp upstream**，PR 状态为 closed/merged-into-fork，owner 评论 "Great find! will review and merge in some time"）。

**原文要点**：
> *"Affects the **generic flash attention GEMM path on pre-Volta GPUs** with larger contexts. The default **q4_0 path is unaffected**."*
> *"Repro (**2x P100, -sm tensor, Qwen3.8-27B Q6_K**, 13 prompts of 5.8k-7.9k tokens x3 passes, b/ub 512, 8k ctx): **f16 KV: NaN 10/39 → 0/39**; prompts whose logits differ between identical passes **8/13 → 0/13**；**q8_0 KV: NaN 8/39 → 0/39**, differing prompts 0/13."*
> *"Affected: the generic branch of `ggml_cuda_flash_attn_ext_gemm` (**pre-Volta**, **nkv >= 4096**, **>= 128 query rows**, **KV type other than q4_0**, e.g. f16/q8_0). **q4_0 caches go to the fold kernels, which have barriers between every red write and read; decode/verify never enter this path.**"*

**为什么这条对我们至关重要**：
1. 我们是 **sm_70（Volta）**，条件是 "**pre-Volta**"（即 cc < 7.0）——**P100 是 sm_60 属于 pre-Volta，而我们不是**。严格按字面，**该 race 不命中 V100S**。
2. **但是**：`nkv >= 4096` + `>= 128 query rows` + `KV type other than q4_0` 这三个条件是**架构无关**的；"pre-Volta" 只是触发该 generic 分支的条件。**在 sm_70 上该分支是否存在、走不走同一段 kernel，必须在 V100S 上实测确认**——**本轮未做此实测（未找到公开证据）**。
3. **症状完全匹配我们前期的已知风险**："速度正常但输出损坏"。而且它**只在长 prompt（5.8k–7.9k tokens）下出现**——短 prompt 冒烟**测不出来**。
4. **可执行的缓解**：**用 `-ctk q4_0 -ctv q4_0`**（该路径"不受影响"）。这与 P100 fork 的 QUICKSTART 一致（`-ctk q4_0 -ctv q4_0`），也与我们现役模型出乱码的 issue ggml-org/llama.cpp#17067（标题即 *"Garbage output for unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M when providing -dev none"*，本轮读到标题）指向同一类问题。

**同 fork 的 PR #3**（2026-10-05）：*"cuda: fold prefill attention support for KV (q8 fold=1)/(fp16 fold=2)… My setup and some tests on **1x P100**"* —— 同一作者在 P100 上做 KV fold 扩展。**同族工作，值得我们复用其方法论。**

### 4.4 Qwen3.8-27B（稠密 27B）— 能力对照组，不是候选

- **架构**：`qwen3_5`，64 层（`full_attention_interval=4` → 16 层全注意力 + 48 层线性注意力），hidden 5120，24 heads / 4 kv heads，head_dim 256，vocab 248320，262144 ctx，**MTP 1 层**，多模态（`Qwen3_5ForConditionalGeneration`）。
- **体积**：Unsloth Q4_0 16.06 / UD-Q4_K_M 16.46 / UD-Q5_K_M 19.77 / UD-Q6_K 21.98 / Q8_0 29.05 GB；ollama `qwen3.8:27b` **18 GB**。
- **KV**：16 层全注意力 × 4 kv heads × 256 dim × 2(K,V) × 2 B = **64 KiB/token** → 262k ctx ≈ 16.8 GB（f16）。**在 64 GB 上放得下（18 + 16.8 = 35 GB）**。
- **能力**：AA II **34 (xhigh)** —— 全榜稠密档最高。第三方（spottedmarley 自研 harness）：优于 Sonnet 4.5。
- **速度（硬数据）**：2×P100-16GB 上 **17.51 t/s**（stock）→ 33.2 t/s（优化后，无 MTP）→ 54 t/s（+MTP @2k）。
  **我们 V100S 的推算**：规格带宽 900 vs P100 732 GB/s（1.23×），sm_70 有真 FP16 张量核（Pascal 无），可达带宽按 FINDINGS 的 605/732 折算比例（0.83）→ V100S 可用约 750 GB/s/卡 vs P100 605（1.24×）。**推算 2×V100S 上 Qwen3.8-27B Q6_K：stock 约 25–40 t/s，优化后 45–60 t/s，+MTP 可能 60–90 t/s。**
  → 🔴 **仍然比现役 135.7 t/s 慢 1.5–5 倍。** 且它额外要付：xhigh reasoning 的 token 膨胀（OliveronData 的直接抱怨）+ 48 层递归导致的前缀缓存重算。
- **判定**：**不做替换**。它是"稠密 vs MoE"这条假设最好的对照组，也是"能力天花板"参照物。

### 4.5 GLM-4.7-Flash（31.2B / 3B）— 便宜好装，但不是升级

- 体积 19 GB（Q4_K_M）/ 32 GB（q8_0）/ 60 GB（bf16），198K ctx，MIT 许可，**单卡轻松放下**。
- AA II 14.87（AA 标为 estimated）。
- 社区横评里 **21/36 (58.3%)**，是三款里最低的。
- 优点：单卡 19 GB → **可以把第二张 V100S 拿来做别的**（或让我们的双卡做 tensor split 提高 KV 空间）；MIT 许可干净；2026-02 架构，比现役新。
- 判定：**作为"保底备选"而非"升级"**。中文社区轮次把它列为性价比首选，本轮英文社区的横评数据**不支持**把它排在现役之上。

### 4.6 Qwen3.8-Flash-Next（125B-A6B + 51B engram）— 🔵 观察名单

- **本轮核实：本地拿不到权重。** `ollama.com/search?q=flash` 显示 `qwen3.8-flash-next` 带 **cloud** 徽标、无本地尺寸、无 `ollama pull` 的本地 tag；`unsloth/Qwen3.8-Flash-Next-GGUF` 仓库树里**只有** `mmproj-BF16/F16.gguf`（0.9 GB）与 `mtp-Qwen3.8-Flash-Next-Q8_0.gguf`（4.14 GB），**没有主权重**。
- 架构（`qwen4_exp`）：48 层、hidden 2560、**512 专家 top-10**、moe_inter 640、24 heads / 2 kv heads、head_dim 256、vocab 248320、262144 ctx、MTP 1 层、`hc_count=4` / `indexer_budget=2048` 的稀疏注意力 + ngram（`ngram_size=3`）机制。**这是 2026 H2 最新的架构，社区还在踩坑期。**
- 社区热度极高：bitexploder 在 V100 上用 **3-bit XXS** 跑到 **>100 t/s**，DeepSWE 官方 harness + Pi 下「neck and neck with Opus 4.7 and Sonnet 5」；woctordho 证明它能在 40 GiB 显存内 LoRA 训练。
- **判定**：**不可部署**（无权重）。但它满足我们想要的一切（低激活、多专家、老卡快、agentic 强）。**一旦 HF 放出 GGUF，应立即重评**——而且很可能需要在 ollama 之外自己编 llama.cpp（`qwen4_exp` 太新）。

---

## 5. 榜单交叉核对（官方自报 vs 第三方/官方榜复现）

### 5.1 Artificial Analysis Intelligence Index v4.3.2（2026-10-21 抓取 `artificialanalysis.ai/leaderboards/models`）

v4.3.2 合成十项评测：**AA-Briefcase v1.1、GDPval-AA v2.1、AutomationBench-AA、Terminal-Bench 4.0、SciCode、Humanity's Last Exam、GDP.pdf、CritPt、AA-Omniscience、AA-LCR v1.1**（页内说明原文）。Terminal-Bench 4.0 = Laude Institute + Stanford 的 66 题 agentic 终端基准，AA 用 **mini-swe-agent harness** 跑全 66 题、**pass@1 平均 3 次重复**——**与我们的 Terminal-Bench 题型高度对齐**。

| 模型 | AA II | 厂商 | 参数 | ctx | AA 托管侧中位速度 |
|---|---|---|---|---|---|
| Qwen3.8 27B (xhigh) | **34** | Alibaba | 27B | 256k | 45 t/s |
| Qwen3.8 27B (medium / low / non-reasoning) | 28 / 26 / 20 | Alibaba | 27B | 256k | ~45 t/s |
| Qwen3.6 35B A3B | **18** | Alibaba | 35B-A3B | 262k | 134 t/s |
| Qwen3.5 122B A10B | 16 | Alibaba | 122B-A10B | 262k | 130 t/s |
| Gemma 4 26B A4B | 17\* | Google | 26B-A4B | 256k | 69 t/s |
| Gemma 4 31B | 15 | Google | 31B | 256k | 36 t/s |
| gpt-oss-120b (high) | 12 | OpenAI | 120B | 131k | 247 t/s |
| Qwen3 Next 80B A3B | 11\* / 10\* | Alibaba | 80B-A3B | 262k | 154 / 126 t/s |
| **Qwen3 Coder Next** | **9** | Alibaba | 79.7B / 3B active | 256k | 97 t/s |
| Qwen3.8-Flash-Next | 40 | Alibaba | 125B-A6B | 256k | 52 t/s |
| GLM-5.3-Flash | 42 | Z AI | 18B active | 1M | 76 t/s |
| MiniMax-M3.1-Flash | 43 | MiniMax | — | 1M | 105 t/s |

> `*` = AA 自己标注为**估算**（无公开 API 或未跑全量）。
> ⚠️ **AA II 对"非 reasoning 的编码模型"系统性低估**（Qwen3-Coder-Next = 9，但厂商自报 SWE-V 70.6%）。**我们排序不能用 AA II 作为主键。**

### 5.2 SWE-bench 官方榜（swebench.com Verified，本轮解析全部 270 条提交记录）

| 排名位 | 模型 | 提交名 | resolved | 日期 | 开源权重 |
|---|---|---|---|---|---|
| 1 | Claude 4.5 Opus | Sonar Foundation Agent + Claude 4.5 Opus | 79.2 | 2025-12-05 | ✗ |
| 2 | Doubao-Seed-Code | TRAE + Doubao-Seed-Code | 78.8 | 2025-09-28 | ✗ |
| … | GPT-5 | Prometheus-v1.2.1 + GPT-5 | 74.4 | 2025-10-15 | ✗ |
| … | GPT 5.2 Codex | GPT 5.2 Codex | 72.8 | 2026-02-19 | ✗ |
| … | Kimi K2 | Lingxi v1.5 × Kimi K2 | **71.2** | 2025-10-14 | ✅ |
| … | Qwen3-Coder-480B-A35B-Instruct | OpenHands + … | 69.6 | 2025-08-05 | ✅ |
| … | GLM-4.6 | GLM-4.6 | 68.2 | 2025-09-30 | ✅ |
| … | GLM-4.5 | GLM-4.5 | 64.2 | 2025-07-28 | ✅ |
| **…** | **Qwen3-Coder-30B-A3B-Instruct（现役）** | **EntroPO + R2E + Qwen3-Coder-30B-A3B-Instruct** | **60.4** | 2025-09-01 | ✅ |
| … | Qwen3-Coder-30B-A3B-Instruct | EntroPO + R2E（同模型另一配置） | 52.2 | 2025-09-01 | ✅ |
| … | Qwen3-Coder-30B-A3B-Instruct | **OpenHands + Qwen3-Coder-30B-A3B-Instruct** | **51.6** | 2025-08-05 | ✅ |
| … | Qwen3-Coder-30B-A3B-Instruct | EntroPO + R2E | 49.67 / 45.0 | 2025-09-01 | ✅ |
| … | Qwen3-Coder-480B-A35B-Instruct | — | 69.6 | — | ✅ |
| … | DeepSeek V3 0324 | SWE-Exp | 42.0 | 2025-08-06 | ✅ |
| — | **Qwen3-Coder-Next** | — | **官方榜无条目（0 命中）** | — | ✅ |

**这张表的三条读法**：
1. **现役模型有官方榜锚点 60.4%**（第三方 EntroPO+R2E 配置）与 **51.6%**（OpenHands 配置）。这两个数比我们任何"自报"都可用。
2. **Qwen3-Coder-Next 的 70.6% 是厂商自报，官方榜无条目** ⇒ 换装前必须在**我们自己的 af-bench** 上跑一遍同口径对比，否则无法回答"解题率是否更高"。
3. **榜单的 harness 决定绝对值**：同榜里同一模型不同 agent 差 9 个点（60.4 vs 51.6）。我们换模型时，**agent 侧（harness/prompt/工具定义）必须锁死**，否则是自变量污染。

---

## 6. 直接证据 vs 推断（分栏）

### 6.1 直接证据（本轮亲自读到 / 跑到的）

| # | 事实 | 来源 |
|---|---|---|
| E1 | Qwen3-Coder-Next 官方 GGUF 体积：Q4_K_M **48.40 GB** / Q5_K_M 56.71 / Q6_K 65.53 / Q8_0 84.81 / F16 159.46 | `hf-mirror.com/api/models/Qwen/Qwen3-Coder-Next-GGUF/tree/main?recursive=true`（本轮抓取，分片逐个列出） |
| E2 | Qwen3-Coder-Next 架构：qwen3_next，48 层，512 专家 top-10，12 层全注意力，79.7B/3B 激活，256k ctx，Apache-2.0，**非 reasoning** | `hf-mirror.com/Qwen/Qwen3-Coder-Next/raw/main/config.json` + `artificialanalysis.ai/models/qwen3-coder-next` |
| E3 | Qwen3.8-27B：qwen3_5，64 层稠密（16 全注意力 + 48 递归），MTP 1 层，vocab 248320，256k ctx；Unsloth Q4_K_M 16.46 / Q8_0 29.05 GB | HF config + GGUF tree |
| E4 | Qwen3.6-35B-A3B：qwen3_5_moe，40 层，256 专家 top-8，UD-Q4_K_M 22.13 GB | 同上 |
| E5 | **Qwen3.8-Flash-Next 无本地权重**：ollama 库中为 cloud-only；Unsloth GGUF 仓库只有 mmproj + mtp | `ollama.com/search?q=flash` + HF tree |
| E6 | ollama 库体积/ctx：qwen3-coder-next 52/85 GB 256K；qwen3.8:27b 18 GB 256K；qwen3.6:35b-a3b 23–24 GB 256K；glm-4.7-flash 19/32/60 GB 198K | `ollama.com/library/*/tags` + `/tags` 页 |
| E7 | **anolis 的 ollama 0.40.6 自带独立 `llama-server`**：`/home/pan-ding/.local/lib/ollama/llama-server`，`version: 0.7.0-dev (build 1, commit 620d2225c)`；支持 `--cpu-moe` / `--n-cpu-moe N` / `--moe-cache-mib` / `--split-mode {none,layer,row,tensor}` / `--tensor-split` / `--fit` + `--fit-target MiB0,MiB1` + `--fit-ctx` / `--cache-type-k/v` / `--spec-type draft-mtp` + `--spec-draft-n-max` / `--override-kv` | `ssh anolis` 实测 `--version` 与 `--help` 原文输出 |
| E8 | **upstream llama.cpp 只对 cc < 7.0 禁 CUDA graphs**；`common.cuh` 定义 `GGML_CUDA_CC_VOLTA 700`；`ggml-cuda.cu` 中 `if (…cc < GGML_CUDA_CC_VOLTA) disable_due_to_gpu_arch = true;` ⇒ **V100S(cc 7.0) 默认开 graphs** | `raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/{common.cuh,ggml-cuda.cu}` |
| E9 | upstream llama.cpp **支持 Volta 的 flash attention**（`fattn.cu` 有 `cc == GGML_CUDA_CC_VOLTA` 分支、`volta_mma_available(cc)`、"On Volta tensor cores are only faster for sufficiently large matrices"） | 同上 `ggml/src/ggml-cuda/fattn.cu` |
| E10 | **2×Tesla P100-16GB + Qwen3.8-27B Q6_K**：stock llama.cpp decode `tg256` **17.51 t/s**；该 fork 优化后 **33.2 t/s**（无 MTP）/ **54 t/s**（MTP @2k）/ **29–35 t/s**（MTP @260k）；prefill `pp2048` 250→**493 t/s**；ppl 2.6101；Q5_K_M+MTP 单请求 34–40→**56–64 t/s** | `github.com/Kmic-68/llama.cpp` 分支 `p100-optimizations`，`p100-docs/README.md` + `QUICKSTART.md` |
| E11 | **P100 fork 的运行命令与逐 flag 理由**（`-sm tensor -fa 1 -ctk q4_0 -ctv q4_0 -c 262144 -b 32768 -ub 2048 -np 1 --spec-type draft-mtp --spec-draft-n-max 4 --spec-draft-p-min 0.2 -ngld 99 -ubd 64` + `GGML_CUDA_P2P=1` + `GGML_CUDA_GRAPHS_PRE_VOLTA=3` + `LLAMA_SPEC_SAMPLE_TEMP=1.0 LLAMA_SPEC_DRAFT_TOPK=20`） | `p100-docs/QUICKSTART.md` |
| E12 | **PR #4：pre-Volta FA GEMM 路径的 NaN race**。复现条件「2x P100, `-sm tensor`, Qwen3.8-27B Q6_K, 13 prompts of 5.8k-7.9k tokens x3, b/ub 512, 8k ctx」：f16 KV **NaN 10/39**、q8_0 KV **8/39**、同 prompt 不同 pass logits 不同 **8/13**；加 `__syncthreads()` 后全 0。**q4_0 路径不受影响**。**未推送到 upstream** | `github.com/Kmic-68/llama.cpp/pull/4` 原文 |
| E13 | P100 fork 的老卡规律：decode matvec **受 global memory 指令数而非带宽限制**；**激活（q8_1）而非权重是瓶颈**；可达带宽 **~605 GB/s/卡**（规格 732），decode 有效 ~490 GB/s；长 prefill **受功耗限制**（~13 TFLOPS fp16 @175 W）；量化块 2 mod 4 字节对齐墙；CUDA graphs 在 Pascal 上被 upstream 按架构禁用（该 fork 自行打开） | `p100-docs/FINDINGS.md` |
| E14 | **多卡 prefill 的卡间交换是主导开销**：3×P100 默认路径 nvprof 归因 **~57%（16k 深度）/ 54%（64k）** 的 prefill 时间花在 exchange；优化后重叠降到 ~7% | `p100-docs/THREE-GPU.md` + PR #2 原文 |
| E15 | 该 fork **自造了两个 data race，数周后才被发现，且全程通过完整 `test-backend-ops` 套件**；其中一个 tensor-parallel peer copy race 命中 decode 与 MTP，强制触发时 **draft 接受率 79% → 43%** | `p100-docs/FINDINGS.md` 原文 |
| E16 | **混合线性注意力的前缀缓存不可回退**："Qwen3.8 has 48 recurrent layers, and a recurrent state can't be rewound. Restoring a saved slot and resending the original prompt still reprocesses everything." 对策 `n_predict:0` 预填 + save/restore + 原文后缀，满深度时 **259,229 token → 10 token** | `p100-docs/FINDINGS.md` 原文 |
| E17 | 2×V100（48 GB 合计）+ 128 GB 内存，Qwen3.6-27B **Q8_0**，`llama-server --tensor-split 0.4,0.6 --flash-attn on -ngl 999 -c 131072`：**~22 tok/s**（<65k ctx）→ **~13 tok/s**（近满，"lots of swapping to RAM"）；主观评价"comparable to claude sonnet 4.6"（~70 kloc C++ 库） | HN [48049546](https://news.ycombinator.com/item?id=48049546)（neutrinobro, 2026-05-07） |
| E18 | bitexploder 明确"为 V100 优化"：单 V100 ~900 t/s prefill / 100 t/s decode（27B 4-bit，DeepSWE）；2×V100@64GB RAM ~300 t/s decode（其私有优化分支）；2026-10-04 口径 2 GPU 27B **150–160 t/s**、Flash Next **125 t/s**；Qwen 27B 3.8 在其 17 道 DeepSWE 任务上"matched Sonnet 5, solving the exact same 7" | HN [49933921](https://news.ycombinator.com/item?id=49933921) / [49955472](https://news.ycombinator.com/item?id=49955472) / [49955352](https://news.ycombinator.com/item?id=49955352) / [49900994](https://news.ycombinator.com/item?id=49900994) |
| E19 | PaulKeeble（2026-10-17）："the MOE models with few active parameters are just faster and easier to run… they behave a lot more like their peak size than the active parameter size"；3080 10GB + 32GB RAM 跑 127B MoE coder → 40–50 t/s @ 65k ctx，"a lot more usable than a Quantised Qwen3.8-27B" | HN [50129753](https://news.ycombinator.com/item?id=50129753) |
| E20 | 2×R9700 → Qwen3.8-27B MXFP4 **150–250 tok/s**（稠密 27B 在 2×32GB 高速卡上的乐观上限） | HN [50080248](https://news.ycombinator.com/item?id=50080248) |
| E21 | RTX 4090 + Qwen3.6-27B UD-Q4_K_XL **MTP**：`--spec-type draft-mtp --spec-draft-n-max 3 --fa on -c 75000` → **115 t/s**（n-max 4 → 125）；**KV cache 量化会导致缓存掉回 CPU 并拖垮性能** | HN [48569943](https://news.ycombinator.com/item?id=48569943) |
| E22 | 自研 harness 横评（36 题）：Gemma 4 26B-A4B **31/36 (86.1%)** > Qwen3.5-9B 30/36 (83.3%) > **GLM-4.7-Flash-4bit 21/36 (58.3%)** | HN [50088324](https://news.ycombinator.com/item?id=50088324) |
| E23 | Qwen3.6 4-bit 量化"kept getting stuck in circles"；GLM 4.7 Flash"至少在推进" | HN [48050908](https://news.ycombinator.com/item?id=48050908) |
| E24 | UncleOxidant：Qwen3-Coder-Next "very usable" 但"**I don't think it's as good as Qwen3.6-27B**（虽然在我的硬件上更快）" | HN [48834700](https://news.ycombinator.com/item?id=48834700) |
| E25 | OliveronData：Qwen3.8-27B"**generates stupid amount of tokens even for the simplest tasks**" | HN [49910341](https://news.ycombinator.com/item?id=49910341) |
| E26 | spottedmarley 自研 harness：Qwen3.5:122b ≈ Sonnet 4.5 编码；Qwen3.8:27b-gsq-iq3s 优于两者，GB10 上 ~50–60 t/s | HN [50150828](https://news.ycombinator.com/item?id=50150828) |
| E27 | Qwen3-Coder-Next 社区速度跨度 10–80 t/s（7900XTX 39 vs 10 t/s；3090+4090 80 tps；Spark 25–39；6GB 显存笔记本 `--cpu-moe` 17 t/s @100k；**RTX 5090 51GB 权重强制 53% CPU 卸载 → 恒定 12 tok/s、GPU util 3–4%**） | HN 主帖 [46872706](https://news.ycombinator.com/item?id=46872706) 各楼 + [46968836](https://news.ycombinator.com/item?id=46968836) |
| E28 | AA Intelligence Index v4.3.2 的十项评测含 **Terminal-Bench 4.0**（66 题，mini-swe-agent harness，pass@1 × 3）；榜上 Qwen3.8 27B(xhigh)=34、Qwen3.6 35B-A3B=18、Qwen3-Coder-Next=9、Qwen3.8-Flash-Next=40 | `artificialanalysis.ai/leaderboards/models` + `/evaluations/terminalbench-4-0`（浏览器渲染后逐行取出 275 行） |
| E29 | **SWE-bench 官方榜（Verified）**：现役 Qwen3-Coder-30B-A3B-Instruct 最高 **60.4%**（EntroPO+R2E）/ 51.6%（OpenHands）；Qwen3-Coder-480B-A35B 69.6%；GLM-4.6 68.2%；Kimi K2 71.2%；**Qwen3-Coder-Next 官方榜 0 命中** | `swebench.com` HTML 内嵌 JSON，本轮解析 270 条提交记录 |
| E30 | 外部对 agentic 基准可信度的质疑：2026-10-14 "We found **110 reward hacks and grading bugs** in Terminal-Bench, DeepSWE, and BFCL"；2026-09-19 "We found defects in **37 of DeepSWE's 113 tasks**" | HN [50089834](https://news.ycombinator.com/item?id=50089834) / [49766208](https://news.ycombinator.com/item?id=49766208) |
| E31 | Qwen3.8-Flash-Next = **125B-A6B + 51B engram**，可在 40 GiB 显存内 LoRA 训练（Strix Halo 200 t/s 训练速度） | HN [50034625](https://news.ycombinator.com/item?id=50034625)（woctordho, 2026-10-10） |
| E32 | 本轮**不可达**通道：reddit.com（DNS 污染 → `2001::1`；curl FAIL；浏览器停在 `chrome-error://`；所有公共代理失败）、x.com、Discord、news.ycombinator.com 正文站 | 本轮 `curl` / `getent hosts` / 浏览器实测 |
| E33 | **前置任务前提需修正**："没有独立 llama-cli / llama-server 二进制"不成立——ollama 0.40.6 自带 `llama-server`（E7） | `ssh anolis` 实测 |
| E34 | `ggml-org/llama.cpp#17067` 标题 = *"Garbage output for unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M when providing -dev none"*（即**我们现役模型**的输出损坏 issue） | `github.com/ggml-org/llama.cpp/issues/17067` 页面标题 |

### 6.2 推断（本报告的判断，**未被直接验证**）

| # | 推断 | 依据 | 风险 |
|---|---|---|---|
| I1 | **Qwen3-Coder-Next Q4_K_M 在 2×V100S 上 decode 约 90–140 t/s，与现役 135.7 t/s 同量级** | 激活 3B → 每 token 读 ~1.5 GB；按 P100 fork 实测的有效带宽折算（490 GB/s / 605 可达 / 16 GB 权重 → 33 t/s 的比例） | 中。**未实测**。P100 fork 的 33.2 t/s 是稠密 27B，不可直接套用到 Coder-Next |
| I2 | **稠密 27B（Qwen3.8-27B）在 2×V100S 上约 25–60 t/s，比现役慢 2.5–5 倍** | E10（2×P100：17.5→33.2 t/s）按带宽比 1.24×、张量核加成上浮 | 中高。**未实测** |
| I3 | **Coder-Next 262K ctx 的 KV 约 6.3 GB（f16）/ 3.2 GB（q4_0）** | 由 config（12 全注意力层 × 2 kv heads × 256 dim）算术推导 | 低（纯算术），但 **linear attention 的递归 state 额外占用未计入** |
| I4 | **换到混合线性注意力模型后，我们 10 轮工具调用的每轮都要重算全对话，单题墙钟显著变长** | E16（P100 fork 对 Qwen3.8-27B 的实测描述） | 中高。**未在 af-bench 上实测**；具体倍数取决于 harness 是否每轮重发全量历史 |
| I5 | **V100S-PCIe 的 P2P 很可能不可用/受限，2 卡 prefill 交换会是显著损耗** | E14（3×P100 交换占 prefill 54–57%）+ P100 fork 必须显式 `GGML_CUDA_P2P=1`；V100S 是 PCIe 型号，无 NVLink | 中。**未实测**。必须在 anolis 上用 `GGML_CUDA_P2P=1` 与 `=0` 对拍 |
| I6 | **V100S 拿到 CUDA graphs 是白送的**（P100 fork 得自己实现） | E8（upstream 只禁 cc<7.0） | 低 |
| I7 | **V100S 可达带宽约 750–800 GB/s/卡，decode 有效 ~600–650 GB/s** | P100 605/732 的比例外推 | 中。**未实测** |
| I8 | **glm-4.7-flash 在我们机器上速度与现役同级但能力更低** | 3B 激活 + 19 GB；E22 的 21/36 | 低 |
| I9 | **Gemma 4 26B-A4B 是被忽略的候选**（4B 激活、26B 总参、约 15 GB Q4、单卡可放、AA II 17\*、社区横评 86.1%） | E22 + AA 榜 | 中。**社区样本量仅 1**，且 Gemma 的 license 与 tool-calling 稳定性需自测 |
| I10 | **P100 fork 的数据对我们偏保守**（我们带宽更高、有真张量核、有 graphs、显存 64GB vs 32GB） | E10 + E8 + E13 | 低 |

### 6.3 明确「未找到公开证据」清单（不补齐）

1. **Reddit（r/LocalLLaMA / r/LocalLLM）2026 H2 帖子**：本轮**完全不可达**（E32）。本次任务点名的 Reddit 侧证据 = 0。
2. **X/Twitter 上 2026-09/10 的 tok/s 实测贴**：不可达。
3. **Discord 社区实测**：不可达。
4. **OpenRouter 社区讨论**：本轮只核到其 API/模型挂牌（价格侧已由中文社区轮次覆盖），**未取到社区讨论**。
5. **lmsys/livebench 2026 H2 榜**：本轮未取到可引用数据（GitHub API 403 + 未解析树页）。
6. **Qwen3-Coder-Next 的第三方 SWE-bench Verified 复现**：官方榜无条目；社区只给 DeepSWE / Terminal-Bench 的轶事比较，**无统一 harness 复现**。
7. **V100S（sm_70）上是否命中 PR #4 的 NaN race**：该 race 条件写的是 "pre-Volta"（cc<7.0），**我们 cc=7.0 严格说不命中**，但架构无关的三个附加条件（nkv≥4096、≥128 query rows、KV≠q4_0）是否在 sm_70 上触发，**本轮未找到公开证据，也未实测**。
8. **2×V100S 的 P2P 可用性**：未找到公开证据，未实测。
9. **Qwen3-Coder-Next 在 V100S 上的任何第三方实测**：**未找到公开证据**（社区全部是 5090/4090/3090/7900XTX/Spark/Strix Halo/M1/PS5）。

---

## 7. 落到我们的机器：把账算清楚

### 7.1 显存账（64 GB 总显存）

| 方案 | 权重 | KV（262k，f16→q4_0） | 合计 | 余量 | 判定 |
|---|---|---|---|---|---|
| 现役 qwen3-coder-30b 单卡 | 18.5 GB | 25.8 GB → 12.9 GB | 44.3 → 31.4 GB | 单卡 **OOM**（262k），故现役实测用 8k ctx | 🔴 长上下文撑不住 |
| 现役 + 8k ctx 单卡 | 18.5 | 0.8 → 0.4 | 19.3 → 18.9 | ~13 GB | ✅ 现状 |
| **Qwen3-Coder-Next Q4_K_M 双卡** | **48.40 GB** | 6.3 → 3.2 GB | 54.7 → 51.6 GB | **9.3 → 12.4 GB** | 🟡 **可行但贴边**；ollama 库版 52 GB 则余 12 → 9.3 GB |
| Qwen3-Coder-Next Q5_K_M 双卡 | 56.71 | 3.2 | 59.9 | 4.1 GB | 🔴 太紧（还剩 compute buffer + 激活） |
| Qwen3-Coder-Next **UD-Q2_K_XL** 双卡 | **26.76 GB** | 3.2 | 30 GB | **34 GB** | 🟢 余量巨大，但 Q2 质量社区反馈差（见 §3.3 Aurornis/Kostic） |
| Qwen3.8-27B Q6_K 双卡 | 21.98 | 16.8 → 8.4 | 38.8 → 30.4 | 25 → 34 GB | 🟢 装得下，但**慢** |
| GLM-4.7-Flash Q4_K_M 单卡 | 19 | （198k ctx，按类似密度估 ~10 GB） | ~29 | ~3 GB | 🟡 单卡勉强；双卡更从容 |
| Qwen3.6-35B-A3B UD-Q4_K_M 双卡 | 22.13 | （40 层，10 全注意力 → ~48 KiB/tok → 262k ≈ 12.6 GB → q4_0 6.3） | 34.7 → 28.4 | 29 → 36 GB | 🟢 最从容 |
| Qwen3.8-Flash-Next | — | — | — | — | ❌ 无权重 |

**结论**：`Qwen3-Coder-Next` 用 **官方 Q4_K_M（48.40 GB）** 装得下，但**必须整卡驻留**（任何一层溢到 CPU 就掉进 petya415 的 12 t/s 坑）。**如果余量太紧，`UD-Q2_K_XL`（26.76 GB）是"宁可低质量也要稳"的备选**——但社区对 Q2 的评价很差（"Q2 is flakey"）。**折中方案：`Qwen3-Coder-Next-UD-Q3_K_M`（35.94 GB）**，余量 ~25 GB，Q3 质量社区争议小于 Q2。

### 7.2 带宽 / 速度账（解码受"每 token 读多少字节"支配）

每 token 读取量 ≈ 激活参数 × 量化位宽（+ 稠密部分）：
- 现役 30B-A3B：3.3B × 4bit ≈ **1.7 GB/token** → 135.7 t/s ⇒ 有效带宽 ≈ **230 GB/s**（**只用了单卡 900 的 1/4！说明现役远未跑满带宽，是被别的因素卡住的**）
- Coder-Next：3B × 4bit ≈ **1.5 GB/token** → 预期与现役同档
- Qwen3.8-27B 稠密：27B × 4bit ≈ **16 GB/token**（Q6_K 约 22 GB）→ 预期 40–60 t/s

🔵 **一个重要推论**：现役 135.7 t/s 只对应 ~230 GB/s 有效带宽，**远低于 V100S 的 900 GB/s 规格**。按 P100 fork 的发现（*"the activation, not the weights, is the bottleneck"*），**现役的 decode 很可能同样被"激活重读 / global memory 指令数"卡住，而不是被权重带宽卡住**。⇒ **Coder-Next（激活 3B、每 token 1.5 GB）很可能拿到与现役相近的 tok/s，但同时因为激活参数少而"更像它的峰值"**（PaulKeeble 的表述）。这是"换 80B-A3B 能拿到能力又不付速度代价"的物理基础。

### 7.3 CPU 专家卸载（`--n-cpu-moe` / `--cpu-moe`）在 V100 上可行吗、代价多大

- **参数确实存在**：我们 ollama 0.40.6 的 `llama-server` 里有 `-cmoe, --cpu-moe`（全部 MoE 权重留 CPU）、`-ncmoe, --n-cpu-moe N`（前 N 层的 MoE 权重留 CPU）、`--moe-cache-mib N`（CPU 侧 MoE 权重的 GPU 缓存大小）。〔E7〕
- **唯一直接实测证据**：predkambrij 在 **6 GB 显存笔记本**上跑 Qwen3-Coder-Next UD-Q4_K_XL，`--cpu-moe --n-gpu-layers 999 --ctx-size 102400` → **17 tok/s @ 100k ctx**。〔E27〕
  - 参照量级：这台机器的 CPU 侧要扛 48 GB 权重搬运；我们 125 GB 内存 + 16 vCPU 条件更好，但 V100S 的 PCIe 是 x16，CPU↔GPU 带宽（~16–25 GB/s）比显存带宽低 **一个数量级**。
  - ⇒ **CPU 专家卸载的 decode 速度天花板大致在 10–30 t/s 量级**，比现役 135.7 t/s 慢 5–10 倍。
- **对我们是否需要**：**不需要。** 64 GB 装得下 48.4 GB 的 Q4_K_M，**全显存驻留**才是正解。`--n-cpu-moe` 是"显存不够时的降级选项"，不是性能选项。
- **但它有一个战术价值**：如果我们想同时在两张卡上跑**两个实例**（一条主力 + 一条对照臂），单实例 48.4 GB 装不下 ⇒ 退而用 **UD-Q2_K_XL（26.76 GB）单卡全显存 + 另一卡跑别的**，比 CPU 卸载好得多。

### 7.4 单题墙钟账（我们每题约 10 轮工具调用）

- **现役**：decode 135.7 t/s、prompt 149.1 t/s @ 8k ctx。10 轮 × (prompt 累积 + 生成) ⇒ 瓶颈在 prompt 重算（若每轮重发全量历史）。
- **Coder-Next**：decode 预期同档（I1）；**但 36 层线性注意力 ⇒ 每轮重算全对话**（I4）。
  - 🔵 **关键缓解**：**它只有 12 层全注意力 ⇒ KV 只有现役的 1/4（24 vs 96 KiB/token）**，所以"重算"的**增量**（KV 读写）比现役便宜；但 **prefill 算力**（36 层递归层的重算）仍是实打实的成本。
  - ⇒ **净效应无法先验判定，必须实测。** 这就是为什么本报告的建议是"**先做单点 A/B，别直接换装**"。

---

## 8. 对我们的具体建议

### 8.1 结论（三句话）

1. **有比现役"更值得上"的候选，但只有一个：Qwen3-Coder-Next（80B-A3B）**——它是唯一同时满足"官方自报解题率明显更高（SWE-V 70.6 vs 现役官方榜 60.4）"+"解码速度与现役同量级（每 token 只读 ~1.5 GB）"+"64 GB 装得下（48.40 GB）"三项的模型。
2. **但"墙钟不涨"这个前提有一个未验证的致命依赖**：`qwen3_next` 的 36 层线性注意力会**打断我们 10 轮工具调用的前缀缓存复用**。这一项不实测清楚，就不能宣称"更值得上"。
3. **"稠密 27B 更强"是真的，"稠密 27B 更快"是假的**——Qwen3.8-27B 在 2×P100 上实测 17.5–33.2 t/s，折算到我们 2×V100S 约 25–60 t/s，**比现役慢 2.5–5 倍**，且额外付 thinking token 膨胀 + 前缀缓存重算。**不要换。**

### 8.2 具体施工单（如果采纳 Qwen3-Coder-Next）

**Step 0 — 先修正一条前置事实（今天就能做）**
我们 ollama 0.40.6 **自带独立 `llama-server`**（`/home/pan-ding/.local/lib/ollama/llama-server`，0.7.0-dev）。**这意味着不需要为了拿 `-sm tensor` / `-fa` / `--fit-target` / `--spec-type draft-mtp` 而去装第二个 llama.cpp。** ollama 的 API 面太窄，**强烈建议本地臂改直连 llama-server 的 OpenAI 兼容端点**（`http://127.0.0.1:8080/v1`），af-bench 侧只需换 base_url。

**Step 1 — 取权重（磁盘不是约束，但注意落盘位置）**
- 选 **Qwen 官方 Q4_K_M（48.40 GB，4 分片）**，不要选 ollama 库版（52 GB，多花 3.6 GB 却不多一分质量）。
- 落盘到 `/data/models/`（当前 /data 剩 18 G，docker 可回收 135 G；按运营者口径可扩容）。**ollama 库的 manifest 方式不便于放 4 分片**，直接用 `llama-server -m` 指向分片目录更简单。
- 若磁盘/余量吃紧，降级档位顺序：`UD-Q4_K_XL (49.61)` → 官方 `Q5_K_M (56.71, 太紧)` → **`UD-Q3_K_M (35.94, 余量 25 GB, 推荐保底档)`** → `UD-Q2_K_XL (26.76, 质量风险高)`。

**Step 2 — 起服务的参数（照 P100 fork 的方法论改写，按我们的 64 GB 调整）**
```
# 冒烟版（先跑通，别一上来就 262k）
GGML_CUDA_P2P=1 \
LLAMA_SPEC_SAMPLE_TEMP=1.0 LLAMA_SPEC_DRAFT_TOPK=20 \
/home/pan-ding/.local/lib/ollama/llama-server \
  -m /data/models/Qwen3-Coder-Next-Q4_K_M-0000{1,2,3,4}-of-00004.gguf \
  -ngl 99 -sm tensor -fa 1 \
  -ctk q4_0 -ctv q4_0 \
  -c 32768 -b 32768 -ub 2048 -np 1 \
  --spec-type draft-mtp --spec-draft-n-max 4 --spec-draft-p-min 0.2 \
  -ngld 99 -ubd 64 -ctkd q4_0 -ctvd q4_0 \
  --jinja --temp 1.0 --top-k 20 --top-p 0.95 --min-p 0.0 \
  --host 127.0.0.1 --port 8080
```
逐条理由（源自 P100 fork QUICKSTART + 本轮 upstream 源码核验）：
| 参数 | 理由 | 证据 |
|---|---|---|
| `-ctk q4_0 -ctv q4_0` | ① q4_0 是唯一**不受** PR#4 NaN race 影响的 KV 类型；② f16 KV 在 262k 装不下；③ maldie 报告"KV 量化会让缓存掉回 CPU 并拖垮性能"——所以 **KV 也要 q4_0，但不能省** | E12 / E11 / E21 |
| `-sm tensor` | 把每层劈到两卡（48.4 GB 需要两卡）；**且 tensor split 要求开 FA** | E11 |
| `-fa 1` | upstream 在 sm_70 上**支持** Volta FA（`fattn.cu` 有 Volta 分支） | E9 |
| **不要** `GGML_CUDA_GRAPHS_PRE_VOLTA` | **upstream 对 cc≥7.0 本来就开 graphs**，V100S 是白送的；那个开关是 P100（sm_60）专用 | E8 |
| `-ub 2048` | 262k 下还留 VRAM 余量的最快 prefill；不够就 1024 → 512（只损失 prefill 速度） | E11 |
| `-b 32768` | MTP 在长上下文必需；batch 过大会让 draft 接受率崩 | E11 |
| `--spec-type draft-mtp --spec-draft-n-max 4 --spec-draft-p-min 0.2` | 用模型自带 MTP 头做投机解码（P100 fork：33.2 → 54 t/s，**+63%**） | E10 / E11 |
| `-ngld 99 -ubd 64 -ctkd q4_0 -ctvd q4_0` | draft 层独立小 ubatch；不加 `-ubd 64` 满 ctx 会 OOM | E11 |
| `--top-p 0.95 --min-p 0.0 --top-k 20` | 模型卡采样；GGUF 不带 min-p，llama.cpp 默认 0.05 会失配 | E11 |
| `GGML_CUDA_P2P=1` | 绕开主机内存的直拷。**必须 A/B 对拍 `=1` 与 `=0`**，因为 V100S 是 PCIe（无 NVLink），P2P 可能不可用 | E14 / I5 |
| `-np 1` | 每个 slot 独享一份完整 KV；我们要并发 2 的话改 `-np 2` 并**重新核算 KV 预算** | E11 |

**Step 3 — 冒烟清单（必须按这个顺序，不许跳）**
1. **单卡先跑**（`-sm none`，只放 1 张卡，用 `UD-Q2_K_XL` 或 1 个分片）——确认 CUDA 真的生效（`nvidia-smi` 看 util>0、显存占用>0）。
2. **输出一致性冒烟**：同一 prompt 跑 3 次，**逐 token 比对 logits/文本**（P100 fork 的 race 只有在重复跑 + 长 prompt 下才暴露）。
3. **长 prompt 冒烟**：**必须用 5.8k–7.9k tokens 以上的 prompt** 跑 3 遍（PR#4 的复现窗口），且 **f16/q8_0 KV 必须专门测一遍**（即使生产用 q4_0，也要知道它会不会炸）。
4. **P2P A/B**：`GGML_CUDA_P2P=1` vs `=0`，比 prefill t/s（2×V100S 交换开销是 3×P100 上 54–57% 的量级）。
5. **满 ctx 显存核对**：用**长 prompt**（不是短 prompt）看 `nvidia-smi` 余量（P100 fork：*"VRAM use grows as the context fills, so check it with a full prompt, not a short one."*）。
6. **工具调用稳定性**：用 af-bench 的真 harness 连打 10 轮，看 tool call 格式与跨轮一致性——**这是我们的核心负载，社区里几乎没人测过这个**。
7. **前缀缓存复现成本实测**（发现 B 的关键实验）：同一会话连续 10 轮，量 prefill token 数。若每轮都重算全量历史 ⇒ **单题墙钟会显著变长**，需要落 P100 fork 的 `n_predict:0` + save/restore 方案，或改用无递归层的模型。

**Step 4 — 判分公平性**
- 换装时**锁死 harness 侧**（prompt、工具定义、轮数上限、上下文裁剪策略），只换模型。SWE-bench 官方榜上同一模型不同 agent 差 9 个点（60.4 vs 51.6），**agent 不锁死就没有可比性**。
- 现役的官方榜锚点是 **60.4%（EntroPO+R2E）** 与 **51.6%（OpenHands）**；Coder-Next 的 70.6% 是厂商自报、**官方榜无条目**。**我们必须在自己的 af-bench 上跑出同口径的数**，否则"更值得上"无法成立。
- 另注：外部已发现 Terminal-Bench / DeepSWE / BFCL 存在 **110 处 reward hack 与判分 bug**（E30）。**我们的判分器需要独立的"输出损坏检测"**（重复采样一致性检查），否则 P100 fork 说的"两个 data race 数周未被发现、且全程通过完整 op 测试套件"这种情况会直接污染我们的结论。

### 8.3 明确不做的三件事（以及为什么）

1. **不换到稠密 27B（Qwen3.8-27B / Qwen3.6-27B）**：2×P100 实测 17.5–33.2 t/s → 我们机器上 25–60 t/s，比现役慢 2.5–5 倍；外加 thinking token 膨胀（OliveronData 实测吐槽）与前缀缓存重算。**它的能力优势（AA II 34）在本地臂上换不回墙钟。**
2. **不碰 GPT-OSS-120B MXFP4**：维持前期结论（V100 不支持 MXFP4），本轮无新增证据支持推翻。
3. **不用 `--n-cpu-moe` 作为常态方案**：唯一实测 17 t/s（6 GB 显存笔记本），代价是 CPU↔GPU 搬运，比现役慢 5–10 倍。**它是"装不下时的降级"，不是性能选项**；我们 64 GB 装得下 Q4_K_M。

### 8.4 观察名单（触发即重评）

| 触发条件 | 动作 |
|---|---|
| **Qwen3.8-Flash-Next（125B-A6B）放出 GGUF 权重** | 🔴 **立即重评**。bitexploder 报告它在 V100 上用 3-bit XXS 跑到 >100 t/s，DeepSWE 官方 harness + Pi 下与 Opus 4.7 / Sonnet 5 打平。3-bit 量化 + 6B 激活 ≈ 47 GB，**正好卡在 64 GB 的甜点上**。注意架构是 `qwen4_exp`（全新），需要足够新的 llama.cpp |
| ollama 升级到支持 `qwen4_exp` 的版本 | 与上同批 |
| upstream 合并 PR#4 的 `__syncthreads()` 修复 | 解除"必须用 q4_0 KV"的自绑（但 q4_0 仍更省显存） |
| af-bench 出现公开的 DeepSWE / Terminal-Bench 复现数据 | 把我们的"解题率"从自测升级为可对标 |
| Gemma 4 26B-A4B 的社区横评样本增加 | 若 LeoisNotAI 的 31/36 被复现，这是"4B 激活 + 26B 总参 + 单卡 15 GB"的极优性价比档，值得进第二轮 |

---

## 9. 本轮"没做到的事"清单（供复盘）

1. **Reddit / X / Discord 全部不可达**（DNS 污染 + 需鉴权 + 公共代理全败）——本任务点名的三大社区源，本轮**只覆盖了 HN + GitHub + 官方库 + 两个官方榜**。若要把 Reddit 补上，需要在**有正常出口的机器**上重跑（可以是我们自己的 anolis？不——anolis 实测同样不可达；需要治理机或换出口）。
2. **lmsys/livebench 未取到**（GitHub API 403 + 未解析树页）。
3. **未在 anolis 上实测任何新模型**（本轮不下载权重，符合任务约束"只读网页与元数据"）。所有速度数字均为第三方数据 + 算术推算。
4. **未验证 V100S 是否命中 PR#4 的 NaN race**、**未验证 2×V100S 的 P2P 可用性**、**未验证前缀缓存重算在 af-bench 10 轮下的实际倍数**——这三条是本报告留下的最重要的三个未决问题，全部需要真机实测。
5. **未评估 `Gemma 4 26B-A4B` 的 GGUF 体积与 ollama 可得性**（本轮只从 AA 榜与社区横评拿到侧面信息）。

---

### 附：本报告引用的关键 URL

- HN Algolia API（本轮主力检索通道）：`https://hn.algolia.com/api/v1/search`、`/search_by_date`、`/items/{id}`
- P100 优化 fork：`https://github.com/Kmic-68/llama.cpp`（分支 `p100-optimizations`）
  - `https://raw.githubusercontent.com/Kmic-68/llama.cpp/p100-optimizations/p100-docs/{README,QUICKSTART,FINDINGS,CHANGES,THREE-GPU}.md`
  - `https://github.com/Kmic-68/llama.cpp/pull/4`（NaN race）、`/pull/2`（3×P100 测量）、`/pull/3`（KV fold）
- llama.cpp upstream 源码：`https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/{common.cuh,ggml-cuda.cu,fattn.cu}`
- HF 官方 API 镜像：`https://hf-mirror.com/api/models/{Qwen/Qwen3-Coder-Next-GGUF,Qwen/Qwen3-Coder-Next,unsloth/*}/tree/main?recursive=true`
- ollama 官方库：`https://ollama.com/library/{qwen3-coder-next,qwen3.8,qwen3.6,glm-4.7-flash}/tags`
- Artificial Analysis：`https://artificialanalysis.ai/leaderboards/models`、`/models/qwen3-coder-next`、`/evaluations/terminalbench-4-0`
- SWE-bench 官方榜：`https://www.swebench.com/`
- 已知 issue：`https://github.com/ggml-org/llama.cpp/issues/17067`（现役模型输出损坏）、PR#2 提到 upstream issue **29466**（三次 server 运行未复现，但"不代表已修"）
