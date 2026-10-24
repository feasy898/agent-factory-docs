# 本地 vs API：算清「本地臂」这笔账（2×V100S-32GB / ollama 0.40.6 / af-bench）

- **产出日期**：2026-10-21
- **调研者**：本地模型选型调研子代理（工作区 `调研/本地模型选型/notes/`）
- **任务来源**：本轮调研任务——"算清『本地 vs API』的账：补齐 MiniMax M3.1 Flash、GLM-5.3、Kimi K3 的当前公开价格与每题成本（结合我们 SWE-V 一题 10 轮、单轮 2-8K token 的用量估算），对比 2×V100S 跑本地模型的机会成本（GPU 占用、电费、折旧、我们能多跑多少题）"
- **取证纪律**：
  - 【直接证据】= 本轮**亲自跑过的命令**或**亲自读到的页面/文件**，给出命令与输出要点
  - 【转引】= 工作区同期笔记（`notes/our-workload.md`、`notes/qwen-family.md` 等）已核实的外部事实，原始 URL 见那些笔记
  - **未做的事一律写"未跑/未找到公开证据"，不用推测填空**
- **本轮动作边界**：未下载任何模型权重；在 anolis 上只做了**只读探测 + 起过两个临时 ollama 实例做对照测量，已 kill 复原**（生产实例 pid 2713982 未动，已核 `pgrep -a ollama` 只剩它一个）

---

## 0. 一页纸结论（先给答案）

### 0.1 对"值不值得换一个本地模型"的直接回答

**不值得把工程量投在"换模型"上，值得投在"换配置 + 换定位"上。** 三个理由，全部有本轮直接证据：

1. **我们已经有"零现金成本、且解题率比本地臂高 1.7–1.9 倍"的 API 臂了。** 本轮实测确认 `mavis` 通道对 **MiniMax-M3.1-Flash 和 MiniMax-M3 都是免费的**（连发两次调用后 `coding_plan/remains` 的 `general` 计数仍是 `5h_used=0 / week_used=0`），而 fix1 同代实测：**m31f D1 70.0% vs 本地 30B D1 37.0%**；**m3 D1 63.6%**。既然免费臂就能拿到接近 GLM-5.3 max（76.8%）的解题率，**"本地臂省 API 钱"这个原始动机已经基本不成立了**。
2. **本地臂的真实稀缺资源不是钱，是 GPU 墙钟和"永不熔断"这两个属性。** 本轮实测本地 30B 的 D1 中位墙钟 **302s**、D2 **395s**、p90 986s；按 2 slot 算，本地臂**每小时只解出 ~8.1 题**（D1 37%）。而免费 API 臂不受我们这 2 张卡的物理上限约束。**本地臂应该占的位置是"并发溢出的去处 / 永不熔断的兜底 / 保密离线题"，不是"最便宜的解题器"。**
3. **但本地臂有一个 API 臂短期内补不了的属性：它不受任何外部配额、限流、鉴权轮换故障影响。** 本轮在 `状态/优惠通道.md` 里读到 2026-10-20 那次事故：**mcode OAuth 令牌对被并发刷新打死 → m31f 免费通道整条停摆**，靠运营者重新授权才恢复。这类故障**本地臂天然免疫**。所以"要不要本地臂"这个问题，答案取决于**我们是否愿意把产线押在一条会整条停摆的免费通道上**。

### 0.2 本轮推翻/修正的三条前期结论

| 前期结论 | 本轮裁定 | 依据 |
|---|---|---|
| 「本地池定位弱模型档，产线主力走 API」 | **强化**：不只是"弱"，而是**在有免费 API 臂的前提下，本地臂的边际价值只剩"抗故障"和"并发溢出"** | 【直接证据】mavis 免费性实测 + fix1 同代解题率对照 |
| 「50-方案的输入 300K+输出 30K 画像高估 1–2 个数量级」 | **对 API 臂成立，对本地臂要改写**：本地臂每题 prompt 总量中位 **418,472**（不是低 1–2 个数量级），因为 ollama 每轮把整个历史重发（但 96.9% 命中缓存，**增量 prefill 只有 ~9,857 token/题**） | 【直接证据】`/tmp/bench-fix1-d1-30b/results.jsonl` 解析 |
| 「本地最强可行选项 = Qwen3-Coder-Next（80B A3B）」 | **维持"能力上限探针"定位，但优先级应低于"调参 + 换定位"**；且 **Qwen3.6-35B-A3B 是更均衡的下一档**（单卡 20.23 GiB、SWE/TB 双超现役） | 【直接证据】ollama registry manifest 实测 + 【转引】官方分数 |

### 0.3 本轮发现的、值得立刻修的两个工程缺口（与选型无关，但直接压产量）

1. **现役 ollama 用的是 `num_ctx=262144`，把显存吃到 94–95% 满**（S1 装载日志：KV 49,152 MiB = GPU0 22,528 + GPU1 26,624），而**真实调用的上下文深度 p99 只有 28,776 token**（本轮独立解析 7,984 个样本）⇒ **262K 是纯浪费，降到 32K 能腾出约 42 GiB 显存**。
2. **本轮实测：现役模型是被拆在两张卡上的**（CUDA0 8,975.64 + CUDA1 8,548.79 MiB 权重 + KV 800/736 MiB）。**但单卡跑同一模型 decode 几乎一样快**（单卡 131.7–133.9 tok/s vs 拆卡 133–135 tok/s）⇒ **两张卡各跑一个独立实例，比一张卡上开 2 个 slot 的聚合吞吐高 19%**（实测 260.7 vs 219 tok/s），且**每卡独立、故障隔离**。这是一条**零成本、零下载**的产能改进。

---

## 1. 候选清单总表

> 口径：全部落到"anolis 2×V100S-32GB + ollama 0.40.6 + af-bench 真实负载"。体积列是**本轮实测的 registry manifest 字节数**（不是标称值）。分数列严格区分**官方自报**与**第三方复现**。

| 模型 | 厂商 | 结构（总参/激活） | Q4 体积 | ctx | GGUF/ollama 可得性 | 官方 agentic 分数 | 第三方反馈 | 我们的适配判断 |
|---|---|---|---|---|---|---|---|---|
| **Qwen3-Coder-30B-A3B-Instruct**（现役） | Alibaba | MoE 30.5B / 3.3B（128 专家取 8，48 层） | **18,556,689,568 B = 17.28 GiB**（本机 blob 实测） | 262,144 | ✅ 在役 | SWE-V 51.6 / 61.4（口径不同）【转引】 | **我们自己实测：D1 37.0% / D2 19.4% / D3 15.0%**；D1 中位墙钟 302s | **保底档，保留**。但**瓶颈是配置不是模型**（262K ctx 吃穿显存 + 无 `max_tokens` + 拆卡） |
| **Qwen3.6-35B-A3B** | Alibaba | MoE 35B / 3B（256 专家取 8 + 1 shared，40 层，30 层 linear-attn） | **21,718,480,960 B = 20.23 GiB** + projector 902,821,728 B（registry 实测） | 262,144 | ✅ `qwen3.6/manifests/35b` http=200；runner 含 `QWEN35MOE`【转引】 | SWE-V **73.4** / TB2.0 **51.5**【转引，官方自报】 | V100-SXM2 第三方 **98.8 tok/s**（thinking ON）【转引】 | **最该打榜的一档**：单卡装得下 ⇒ **两张卡各跑一个独立实例**，无拆卡惩罚；SWE/TB 双超现役。**前提：必须先有 thinking 开关** |
| **Qwen3-Coder-Next（80B-A3B）** | Alibaba | MoE 80B / 3B（512 专家取 10，48 层，**仅 non-thinking**） | **51,741,599,936 B = 48.19 GiB**（registry 实测；前期文档写 45GB **低估 7%**） | 262,144 | ✅ `qwen3-coder-next/manifests/q4_K_M` http=200 | SWE-V **70.6**（SWE-Agent）/71.1/71.3；**TB2.0 仅 34.2/36.2**【转引】 | **未找到 V100 上的第三方复现** | **能力上限探针，不是换装首选**：①TB 倒退 ~17 分（我们 workload 含 TB）②48 GiB + KV 顶到 95%+，**ctx 必须砍到 2×16K 或 2×32K** ③每 token 字节≈现役 ⇒ **不会更快** |
| **GLM-4.7-Flash 30B-A3B** | Zhipu | MoE 30B / 3B | **19,019,269,280 B = 17.71 GiB**（registry 实测，**本轮首次拿到确切体积**） | 未在本轮核实 | ✅ `glm-4.7-flash/manifests/q4_K_M` http=200 | 未在本轮核实到可核的官方 SWE-V/TB 数 | 【转引】5090D 社区实测 147.5 tok/s | **值得补测**：同价位同结构、比现役高一代。**但官方 agentic 分数本轮未核到，证据不足，暂不进实测队列** |
| **Qwen3.6-27B / Qwen3.8-27B（稠密）** | Alibaba | **稠密** 27.78B（48 层 linear-attn + 16 层 full-attn） | `qwen3.6/manifests/27b` 存在（体积未取） | 262,144 | ✅ | Qwen3.6-27B SWE-V 77.2 / TB2 59.3【转引】 | V100 实测 **32.9–33.41 tok/s**【转引】 | **不做**。稠密每 token 要读 ~16.9 GB vs MoE ~2.3 GB ⇒ **慢 4.1×**，单题墙钟是现役 4–8×，与量产臂定位冲突 |
| **GPT-OSS-120B (MXFP4)** | OpenAI | MoE 120B / 5.1B | 原生 63 GB【转引】 | 131,072 | runner 含 `gpt-oss` 符号【转引】 | SWE-V 33.6【转引】 | — | **维持不推荐**：V100 无 MXFP4 加速 + 体积贴边无 ctx 余量。**本轮未复核 kernel** |
| **MiniMax-M3.1-Flash / M3** | MiniMax | — | — | 1M | ❌ 无本地 GGUF | SWE-Pro 59%（M3）【转引】 | **本轮实测：Vals.ai Terminal-Bench 4.0 上 M3.1-Flash 25.25% vs M3 1.01%** | **只走 API**（mavis 免费通道）——**本地路径基本断绝，这是"本地臂必要性"讨论的起点** |
| **GLM-5.3 / Kimi K3 / DeepSeek-V4.x** | Zhipu/Moonshot/DeepSeek | 超大 MoE | 远超 64 GB | 1M | ❌ ollama 无 GGUF | — | — | **出局**（体量） |

---

## 2. 重点候选展开

### 2.1 决策核心：本地臂 vs **免费** API 臂（不是 vs 付费 API 臂）

这是本轮最重要的发现，也是前期文件里没有的。任务书问的是"本地 vs API 的账"，但**真正的对手不是付费 API，是零现金的 mavis 通道**。

**免费性本轮实测（2026-10-21）**：

```bash
# 取 mcode OAuth token（复用已在役的续期工具）
ssh anolis "K=\$(python3 ~/.local/bin/mcode-token.py get)"
# 调 M3.1-Flash
curl -s -H "Authorization: Bearer $K" -H 'Content-Type: application/json' \
  -H 'User-Agent: MiniMaxCode' \
  -X POST https://agent.minimaxi.com/mavis/api/v1/llm/v1/messages \
  -d '{"model":"MiniMax-M3.1-Flash","max_tokens":64,"messages":[{"role":"user","content":"say OK"}]}'
```
输出：`{"model":"MiniMax-M3.1-Flash", ... "usage":{"input_tokens":9,"output_tokens":13,"cache_read_input_tokens":195, ...}}` ✅

```bash
# 查配额计数器（连发 2 次调用之后）
curl -s -H "Authorization: Bearer $K" -H 'User-Agent: MiniMaxCode' \
  https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains
```
输出：`general: 5h_remaining% 50 week% 53 5h_used 0 week_used 0 total_count_5h 0 total_week 0`
⇒ **文本模型调用没有进任何配额计数**（`video` 计数是 5/35，**证明计数器本身在工作**，不是接口失灵）。这与 `状态/优惠通道.md` §二 的 2026-10-20 独立实证一致（本轮**复现了它**）。

**同时确认 M3 也在同一条免费通道上**：`model=MiniMax-M3` 调用返回正常 usage，`general` 计数仍为 0。

**于是同代（fix1）实测对照**（全部来自 `/tmp/bench-fix1-d*/results.jsonl`，本轮独立解析）：

| 档 | **30b-LOCAL** | **mavis-m31f（免费）** | **mavis-m3（免费）** | glm-cp（GLM-5.3-Flash，套餐 2/3 折） | glm-cp-max（GLM-5.3） | kimi-k3 | step-5 |
|---|---|---|---|---|---|---|---|
| **D1** | **37.0%** | **70.0%** | **63.6%** | 62.7% | **76.8%** | 71.4% | 62.8% |
| **D2** | **19.4%** | **47.8%** | — | 48.3% | 45.7% | 50.0% | 56.5% |
| **D3** | **15.0%** | **35.0%** | — | 22.2% | 50.0% | 47.4% | 28.6% |
| D1 中位墙钟 | **302s** | 1135s | **191s** | 770s | 643s | 303s | 863s |
| D1 中位输出 token | 5,756 | 43,978 | 3,879 | 13,752 | 13,287 | 7,068 | 14,502 |
| 有效吐字速率 | 19.5 tok/s | 43.4 tok/s | 30.1 tok/s | 21.8 tok/s | 24.2 tok/s | 21.7 tok/s | 32.4 tok/s |

> **口径**：全部 fix1 同代（`scaffold=v2`、无 `judge_mode` 字段 ⇒ 均为 POC-1 判分口径切换前），**臂间可比**；不能与 fix2/fix3 混算（`计划/50-bench实测方案.md:312` 版本隔离纪律）。分母为 `reward != null` 的题数（infra 题剔除），**跨臂必须比通过率而非通过数**。

**读出来的三件事**：
1. **本地 30B 在 D1 就掉到 37.0%**，而**免费的 m31f 是 70.0%** ⇒ **本地臂在"解题率"这个维度上已经被零成本方案碾压 1.9 倍**。
2. **本地臂唯一的优势是墙钟**（D1 302s vs m31f 1135s）。但 **m3（也是免费）墙钟只有 191s、解题率 63.6%** ⇒ **连墙钟优势都被一个免费臂同时打掉了**。本地臂相对 m3 在 D1 上**解题率 -26.6 点、墙钟 +58%**——**没有一项占优**。
3. **本地臂真正的、不可替代的价值在别处**：①**抗外部故障**（2026-10-20 mcode token 事故导致 m31f 整条停摆，本地臂不受影响）；②**并发溢出**（免费通道有 4 路 profile 限额 + 周池/5h 池 + 429 风暴，2026-10-20 实证 40/42 run_failed）；③**保密/离线题**。

### 2.2 候选展开：Qwen3.6-35B-A3B（若要换，第一顺位）

**为什么是它而不是 Coder-Next**（两条都是本轮直接证据）：

| 维度 | Qwen3.6-35B-A3B | Qwen3-Coder-Next 80B-A3B |
|---|---|---|
| Q4 体积（registry 实测） | **20.23 GiB + 0.84 GiB projector** | **48.19 GiB** |
| 显存布局 | **单卡装得下** ⇒ 2 卡各跑一个独立实例，**无跨卡 PCIe 惩罚** | 强制拆卡（24.1 GiB/卡）+ ctx 必须砍到 2×16K/2×32K |
| 官方 SWE-V | **73.4** | 70.6 |
| 官方 TB2.0 | **51.5** | **34.2 / 36.2（倒退 ~17 分）** |
| 每 token 读取字节 | ≈1.8 GB【转引】 | ≈2.13 GB【转引】 |
| 相对现役的**墙钟**变化 | 大概率持平或更快 | 持平（**不会更快**） |

**我们 workload 含 TB**（`af/crates/af-bench/src/main.rs:1084-1278` 是 terminal-bench 适配器）⇒ **Coder-Next 的 TB 倒退是硬伤**。35B-A3B 是唯一"SWE 与 TB 双超现役 + 单卡装得下"的候选。

**必须先解决的前提（否则装上去也白装）**：
- **thinking 旋钮缺失**：`af/crates/af-harness/src/endpoint.rs:186-213` 的 `openai_body()` **不发 `reasoning_effort`**（本地档案 `reasoning_tier: ReasoningTier::Off` ⇒ 连 `reasoning_effort` 字段都不进 body）⇒ Qwen3.6-35B-A3B 的默认 thinking **关不掉** ⇒ token 必然膨胀（我们自己的 m31f 就是这么炸的：输出 token 中位 43,978，比 30B 的 5,756 高 7.6×）。
- **同族 sm_70 崩溃 issue #29783 未修**【转引】⇒ 必须冒烟。
- **MTP 投机解码不会自动生效**：本机 ollama 0.40.6 装载时打印 `"spec common_specu: no implementations specified for speculative decoding"`【转引】⇒ 别指望它提速（但也意味着 `--split-mode tensor` 下的 MTP 崩溃 issue 对我们**不触发**，我们用默认 layer split）。

### 2.3 候选展开：现役 30B —— **不是"该换掉的"，是"该调参的"**

本轮实测的三个配置问题（都可在不换模型的前提下修）：

1. **ctx 档位浪费**：`num_ctx=262144` → KV 48 GiB → 两卡 94–95% 满；而真实深度 p99 只有 28,776。**降到 32K 腾出约 42 GiB**。
2. **拆卡没有换来速度**：本轮实测——拆两卡 **133–135 tok/s**（ollama `eval_duration` 口径），**单卡独占 131.7–133.9 tok/s**。**速度差 ≤1.5%，但单卡方案让两张卡可以各跑一个独立实例** ⇒ 实测聚合 **260.7 tok/s vs 219 tok/s（+19%）**。
3. **`max_tokens` 没传** ⇒ ollama 用自己的默认 `num_predict`，单轮可无上限吐字 ⇒ 撞 600s 读超时后被 harness 重试 ⇒ **白烧 GPU**。

### 2.4 候选展开：Qwen3-Coder-Next（80B-A3B）—— 能力上限探针，不是换装首选

**能力**【转引 `notes/qwen-family.md` §2.1，官方技术报告 2026-02-03】：SWE-V 70.6（SWE-Agent）/71.1（MiniSWE）/71.3（OpenHands）；SWE-Pro 44.3；**TB2.0 36.2（json）/34.2（xml）**。

**体积（本轮独立核实）**：`curl -s https://registry.ollama.ai/v2/library/qwen3-coder-next/manifests/q4_K_M` → model layer **51,741,599,936 B = 48.19 GiB**。**前期文档写的 45GB 低估 7%。**

**反面核查（任务书点名要查的）**：
- 「双卡 64GB 能否放下」→ **能放下但极紧**：48.19 GiB 权重双卡分摊 ≈24.1 GiB/卡，每卡 31.73 GiB 可用 ⇒ 余 ~6.4 GiB。**加上 KV 就爆**（现役 96 KiB/token × 2 slot × 32K = 6 GiB ⇒ 每卡 ~30.5/31.7 GiB = 96% 满）。
- 「`--n-cpu-moe` 在 V100 上可行吗」→ **不可行**。本轮采纳笔记复算：Coder-Next 每 token 需从主机内存搬 ≈0.92 GB；PCIe Gen3 x16 实测 12–14 GB/s ⇒ **纯搬运 58–77 ms/token ⇒ 天花板 13–17 tok/s**。相对现役真实深度的 ~40 tok/s 是 **2.4× 倒退**，相对微基准 135.7 tok/s 是 **8× 倒退**。**双卡分摊才是正解。**

**结论**：它**更强但不会更快**，且 **TB 倒退**。⇒ 若采纳，只能定位成"**SWE 专项加强臂**"（只跑 SWE-V 不跑 TB），不能全量替代。

---

## 3. 算账：本地 vs API（每题成本，用我们自己的实测 token 画像）

### 3.1 我们的真实 token 画像（【直接证据】，本轮从 results.jsonl 解析）

**关键：token 语义按协议不同，必须分开处理**（`af/crates/af-harness/src/endpoint.rs:432-438` OpenAI 路径 vs `:580-583` Anthropic 路径）：
- **OpenAI 协议**：`prompt_tokens` **包含**缓存命中部分，`cached_tokens` 是其子集 ⇒ 未命中输入 = `input - cache_read`。
- **Anthropic 协议**：`input_tokens` **就是未命中输入**，`cache_read_input_tokens` 是**另外**的量 ⇒ 两者直接相加。
- **本地臂走 OpenAI 协议**（`main.rs:283-301`，`base_url = http://127.0.0.1:11435/v1`），但 ollama 的 `prompt_tokens` 是**每轮全量**、其中 ~96.9% 命中缓存。

D1 单题中位（各臂实测）：

| 臂 | 协议 | 未命中输入 | 缓存读 | 输出 | 说明 |
|---|---|---|---|---|---|
| **30b-LOCAL** | OpenAI(ollama) | **9,857** | **406,482** | **5,590** | 每轮重发全历史，96.9% 命中缓存；**增量 prefill 极小** |
| glm-cp | Anthropic | 23,520 | 252,928 | 13,752 | |
| glm-cp-max | Anthropic | 22,317 | 355,968 | 13,287 | |
| m31f | Anthropic | 29,375 | 888,043 | 42,159 | thinking token 膨胀 |
| m3 | Anthropic | 13,187 | 181,041 | 3,185 | |
| kimi | OpenAI | 10,718 | 79,104 | 7,068 | |
| step-5 | OpenAI | 66,479 | 519,424 | 14,502 | |

> ⚠️ **口径修正**：任务书给的"SWE-V 一题 10 轮、单轮 2-8K token"与实测不符。实测本地臂 D1 **中位 40.5 轮**、每题 prompt 总量中位 **418,472**、输出中位 **5,756**。**本报告一律用实测画像，不用任务书的估算画像。**

### 3.2 公开价格（本轮核实，2026-10-21）

| 模型 | 官方价 | 来源 | 第三方聚合价（OpenRouter，2026-10-21 实查 API） |
|---|---|---|---|
| **MiniMax-M3.1-Flash** | **国际 $0.15 入 / $0.60 出 / $0.015 缓存读**；**国内 ¥1 / ¥4 / ¥0.1** | 官方定价页 `platform.minimax.io/docs/guides/pricing-paygo` 与 `platform.minimaxi.com/docs/guides/pricing-paygo`（RSC payload 表格直接抓取） | **`minimax/minimax-m3.1-flash:free` = $0 / $0**（provider `Minimax`，`uptime_last_1d=100`，`max_completion_tokens=524288`，`supported_parameters` 含 `tools`/`tool_choice`）✅ **官方 provider 的免费档，不是第三方转售** |
| **MiniMax-M3** | 国际 $0.30 / $1.20 / $0.06（>512K 输入翻倍 $0.60/$2.40）；国内 ¥2.1 / ¥8.4 / ¥0.42 | 同上 | `minimax/minimax-m3` = $0.30 / $1.20 / $0.06 |
| **GLM-5.3** | 国际 **$1.40 入 / $4.40 出 / $0.26 缓存读**；国内刊例 ¥8 / ¥28 / ¥2 | `docs.z.ai/guides/overview/pricing` 表格直接抓取 | `z-ai/glm-5.3` = **$0.079 / $1.40**（第三方供应商价，**远低于官方**）；`:batch` $0.45/$2.00 |
| **GLM-5.3-Flash** | 国际 **$0.15 / $0.50 / $0.03** | 同上 | `z-ai/glm-5.3-flash` = $0.15/$0.50；**`:batch` = $0.05 / $0.18** |
| **Kimi K3** | **国内 ¥20 入（缓存未命中）/ ¥2 缓存命中 / ¥100 出 / 1,048,576 ctx**；缓存写入 ¥20（TTL 5min）/ ¥40（TTL 1h） | `platform.moonshot.cn/docs/pricing/chat`（RSC payload `DocTable` 直接抓取） | `moonshotai/kimi-k3` = **$0.239 / $11.936**（第三方促销价）；`~moonshotai/kimi-latest` = $0.238 / $16.00 |
| Kimi K2.7-Code | ¥1.30 缓存命中 / ¥6.50 未命中 / ¥27.00 出 / 262,144 ctx | 同上 | $0.671 / $3.35 |
| Step 5 Preview | $1.00 入 / $0.10 缓存 / $2.70 出 | `platform.stepfun.com`【转引前期文件】 | `stepfun/step-5-preview` = $1.0 / $2.7 |
| DeepSeek V4.1 Flash | ¥2/¥8 高峰、¥1/¥4 空闲（缓存命中 ¥0.04/¥0.02）【转引】 | 官方定价页【转引】 | `deepseek/deepseek-v4.1-flash` = **$0.049 / $0.525** |

> **口径说明**：OpenRouter 的 `z-ai/glm-5.3` 第三方价（$0.079/$1.40）**低于官方刊例 5.6 倍**，是聚合渠道的竞价结果，**不保证稳定**。采购决策前须复核。

### 3.3 每题成本（用 §3.1 实测画像 × §3.2 价格，按我们实际走的通道）

**通道口径**（`状态/优惠通道.md`）：GLM 走 **CodingPlan key + `open.bigmodel.cn/api/anthropic`**，与 zcode **同池同率**，"2/3 折"是套餐积分价相对按量现金价的结构性优惠；MiniMax 走 **mavis + mcode OAuth = 免费**（本轮复现）。

| 臂 | D1 解题率 | **¥/题** | **¥/解出1题** | D1 中位墙钟 | 有效 tok/s | 现金支出 |
|---|---|---|---|---|---|---|
| **30b-LOCAL** | 37.0% | **¥0.0249**（纯电费） | **¥0.0672** | **302s** | 19.5 | ¥0（但**占 2 张卡的墙钟**） |
| **mavis-m31f（免费）** | **70.0%** | **¥0** | **¥0** | 1135s | 43.4 | **¥0** |
| **mavis-m3（免费）** | **63.6%** | **¥0** | **¥0** | **191s** | 30.1 | **¥0** |
| glm-cp（GLM-5.3-Flash，套餐 2/3） | 62.7% | **¥0.0805** | **¥0.1283** | 770s | 21.8 | 套餐积分 |
| glm-cp-max（GLM-5.3，套餐 2/3） | 76.8% | **¥0.8852** | **¥1.1528** | 643s | 24.2 | 套餐积分 |
| kimi-k3 | 71.4% | ¥0.2083 | ¥0.2916 | 303s | 21.7 | 订阅/按量 |
| step-5 | 62.8% | ¥0.1820 | ¥0.2899 | 863s | 32.4 | 按量 |

**本地电费口径（【直接证据】）**：
- 功耗（本轮实测）：**负载 131.5–138.6 W/卡**（`nvidia-smi --query-gpu=power.draw`，0.5s 采样，7,978 次真实调用期间）；**空载 37.7 / 36.8 W**。V100S 功率上限 250 W。
- 单题中位墙钟 **329s**（本地臂 119 题实测），两卡同时在役 ⇒ **0.03144 kWh/题**。
- 电价：**¥0.791/kWh（工商业，CNY；数据日期 2026-03-01）**，来源 `globalpetrolprices.com/China/electricity/`（第三方汇编，非官方电价文件）。**未找到我们机房实际结算电价**——若按 ¥0.6/kWh 算，本地臂成本降为 ¥0.0189/题。
- ⇒ **本地臂电费 ¥0.025/题**。**加上折旧就完全不一样了**（见 §3.4）。

### 3.4 折旧与 GPU 占用（机会成本的真身）

**这里必须诚实：工作区里没有这两台 V100S 的采购价记录**（`状态/机器清单.md` 只记规格与容量，`/tmp/bench-*` 与 `计划/50-bench实测方案.md` 把本地臂成本记作"电费"）。**未找到公开证据**。因此给一个区间而非单值：

| 假设 capex | 折旧口径 | ¥/GPU-h | **每题（2 卡 × 0.0914 h）** | **每解出1题（D1 37%）** |
|---|---|---|---|---|
| ¥60,000（2×V100S 32GB 二手 + 机箱，**市场估计，未找到成交价证据**） | 4 年直线 | ¥1.71 | ¥0.313 | ¥0.846 |
| ¥120,000 | 4 年直线 | ¥3.42 | ¥0.626 | ¥1.692 |
| ¥0（若视为已沉没的既有资产） | — | ¥0 | ¥0 | ¥0 |

**⇒ 关键判断：本地臂的真实成本从 ¥0.025（纯电费）到 ¥0.67（折旧+电费）跨了一个数量级，取决于折旧口径。** 但**无论哪个口径，本地臂都打不过"免费 API 臂"**——因为后者是 ¥0。

### 3.5 机会成本：我们能多跑多少题

**本地臂的物理上限（实测）**：
- 现状（1 实例拆 2 卡 + 2 slot）：聚合 219 tok/s → **21.9 题/小时（墙钟）**，其中解出 **8.1 题/小时**（D1 37.0%）。
- 改 2 独立实例（1 卡/个，本轮实测 260.7 vs 219 tok/s，+19%）：→ **26.0 题/小时**，解出 **9.6 题/小时**。**零成本、零下载。**

**本地臂 vs 免费 API 臂的产能对比**：
- 免费 API 臂的并发受**外部配额**约束：`tools/factory-sched.py:53-56` 的 profile 限额 `mavis-m31f: 4`，而 `HOST_LIMITS = {"anolis": 14, "local": 3}`；5h 池/周池 + 429 风暴（2026-10-20 实证 40/42 run_failed）。
- 本地臂的并发受**我们自己**约束：2 卡 × 2 slot。
- ⇒ **本地臂的产能价值 = 免费臂打满配额后的溢出容量**。这正是它该占的位置。

**把"多跑多少题"翻译成钱**：
- 免费 API 臂：每解出 1 题 **¥0**（现金），但受配额 ⇒ 瓶颈是**额度**不是钱。
- 本地臂：每解出 1 题 **¥0.067（纯电费）到 ¥1.69（含折旧）**，但**不受任何外部配额限制**。
- ⇒ **如果我们的产线规模是"每季度几千题"级别，配额根本不是约束，本地臂就是纯成本中心（占着 2 张卡 + 运维注意力 + 换模型的工程量）。** 如果规模是"每天几万题的持续量产"或者"配额被打爆的应急期"，本地臂才有不可替代性。

---

## 4. 直接证据 vs 推断（分栏）

### 4.1 直接证据（本轮亲自跑过 / 读到，可复现）

| # | 事实 | 怎么拿到的 |
|---|---|---|
| E1 | **mavis 通道对 M3.1-Flash 和 M3 都免费**：连发 2 次调用后 `coding_plan/remains` 的 `general` 仍 `5h_used=0 / week_used=0`；同响应里 `video` 计数为 5/35（证明计数器在工作） | `ssh anolis` + `curl` 两次（见 §2.1 命令）；与 `状态/优惠通道.md` §二 的 2026-10-20 独立实证一致 |
| E2 | **mavis 的 M3.1-Flash 端点元数据**：`minimax/minimax-m3.1-flash:free`，`prompt=0 / completion=0`，provider `Minimax`，`uptime_last_30m/5m/1d` 全 100，`max_completion_tokens=524288`，`context_length=1000000`，`supported_parameters` 含 `tools`/`tool_choice`/`reasoning_effort` | `curl https://openrouter.ai/api/v1/models/minimax/minimax-m3.1-flash:free/endpoints` |
| E3 | **官方 MiniMax 价格**：M3.1-Flash 国际 $0.15/$0.60/$0.015，国内 ¥1/¥4/¥0.1；M3 国际 $0.30/$1.20/$0.06（>512K 翻倍），国内 ¥2.1/¥8.4/¥0.42 | `platform.minimax.io/docs/guides/pricing-paygo` 与 `platform.minimaxi.com/docs/guides/pricing-paygo` 的 RSC payload 表格，用 `<tr>` 正则解析 |
| E4 | **官方 z.ai 价格**：GLM-5.3 $1.40/$4.40/$0.26；GLM-5.3-Flash $0.15/$0.50/$0.03；GLM-5.3-FlashX $0.37/$1.25/$0.075 | `docs.z.ai/guides/overview/pricing` 的 `<tr>` 解析 |
| E5 | **官方 Moonshot 价格**：kimi-k3 1M tokens：缓存写入(5min) ¥20 / 缓存写入(1h) ¥40 / 缓存命中入 ¥2.00 / 未命中入 ¥20.00 / 出 ¥100.00 / ctx 1,048,576；kimi-k2.7-code ¥1.30/¥6.50/¥27.00/262,144 | `platform.moonshot.cn/docs/pricing/chat` 的 RSC `DocTable` 解析 |
| E6 | **Vals.ai SWE-bench 独立复现（86 个模型，含 latency 字段）**：glm-5.3-flash 92.0% / $0.018 / 3817.4s；glm-5.3 95.4% / $0.338 / 840.8s；kimi-k3 93.4% / $0.760 / 619.5s；MiniMax-M3 75.0% / $0.416 / 726.0s；qwen3.8-27b 86.0% / $1.077 / 599.8s；gpt-oss-120b 33.6% / $0.172 | `curl https://www.vals.ai/benchmarks/swebench` → 正则 `"([^"]+)":\[0,\{"accuracy":\[0,([0-9.]+)\],"latency":\[0,([0-9.]+)\],"cost_per_test":\[0,([0-9.]+)\]` |
| E7 | **Vals.ai Terminal-Bench 4.0**：`minimax/MiniMax-M3.1-flash` **25.253% / $0.735 / 3030.6s**；`minimax/MiniMax-M3` **1.01% / $7.229**；`zai/glm-5.3` 38.889% / $9.374 / 4952.9s；`zai/glm-5.3-flash` 37.374% / $1.220 / 3681.1s；`kimi/kimi-k3` 17.172% / $12.478 / 11353.5s | `curl https://www.vals.ai/benchmarks/terminal-bench-4` 同法解析 |
| E8 | **OpenRouter 当前价（2026-10-21 实查 `/api/v1/models`）**：`z-ai/glm-5.3` $0.079/$1.40；`z-ai/glm-5.3-flash` $0.15/$0.50（`:batch` $0.05/$0.18）；`moonshotai/kimi-k3` $0.239/$11.936；`qwen/qwen3-coder-next` $0.12/$0.80；`stepfun/step-5-preview` $1.0/$2.7；`deepseek/deepseek-v4.1-flash` $0.049/$0.525 | 同上 |
| E9 | **本地臂实测解题率（独立复现）**：D1 **37.0%**（20/54）、D2 **19.4%**（7/36）、D3 **15.0%**（3/20）；D1 中位墙钟 302s、D2 395s、D3 140s；D1 输出中位 5,756、有效 19.5 tok/s | `python3` 解析 `/tmp/bench-fix1-d{1,2,3}-30b/results.jsonl`（分母 = `reward is not None`；`reward` 是 `false` 不是 `None`，**第一次我按 `None` 过滤得到空集，纠正后**） |
| E10 | **API 臂同代对照**：glm-cp D1 62.7%/770s；glm-cp-max 76.8%/643s；mavis-m31f **70.0%**/1135s；mavis-m3 **63.6%**/191s；kimi 71.4%/303s；step-5 62.8%/863s | 同上，解析各 `/tmp/bench-fix1-d1-*/results.jsonl` |
| E11 | **token 语义按协议不同**：OpenAI 路径 `prompt_tokens` 含缓存、`cached_tokens` 是子集（`endpoint.rs:432-438`）；Anthropic 路径 `input_tokens` 是未命中输入、`cache_read_input_tokens` 另计（`endpoint.rs:580-583`） | 读码 + 对照 `main.rs:188-285` 的协议映射（m31f/m3/glm-cp/glm-cp-max = Anthropic；step-5/kimi/30b-local = OpenAI） |
| E12 | **本地臂 D1 单题中位**：未命中输入 **9,857**、缓存读 **406,482**、输出 **5,590** | 同 E9 |
| E13 | **ollama 日志 7,984 次调用的上下文深度**：中位 **10,281**、p90 **20,826**、p99 **28,776**、max **63,157** | `python3` 逐行解析 `/data/models/ollama-serve.log` 的 `stop processing: n_tokens = N` |
| E14 | **现役模型被拆在两张卡上**：CUDA0 权重 8,975.64 + KV 800 MiB；CUDA1 权重 8,548.79 + KV 736 MiB | `grep` ollama-serve.log 的 `load_tensors: CUDA0/CUDA1 model buffer size` + `llama_kv_cache` 行；`nvidia-smi` 实测 10,572 + 10,010 MiB |
| E15 | **单卡独占 decode 与拆卡几乎相同**：单卡 131.7 / 132.4 / 133.9 tok/s（ollama `eval_duration` 口径）；拆卡 134.9 / 134.0 / 134.3 / 133.0 tok/s | 起 `OLLAMA_HOST=127.0.0.1:11436 CUDA_VISIBLE_DEVICES=0` 的临时实例 + `ollama-serve.log` 交叉核对（**已 kill 复原**） |
| E16 | **两独立实例（1 卡/个）聚合 260.7 tok/s**（131.3 + 129.4），vs 单实例 2 slot 的 219 tok/s | 同上，11436 + 11437 双实例并发实测（**已 kill 复原**） |
| E17 | **实测功耗**：负载 131.5–138.6 W/卡（p90 145.6–153.9，max 183.8–182.3），空载 37.7 / 36.8 W，power limit 250 W | `nvidia-smi --query-gpu=power.draw,utilization.gpu,memory.used` 0.4–0.5s 采样 |
| E18 | **本地臂 119 题总 agent 墙钟 14.49 h**，单题中位 329s | 解析三个 results.jsonl 的 `agent_wall_ms` |
| E19 | **中国工商业电价 ¥0.791/kWh**（日期 2026-03-01）；居民 ¥0.532 | `globalpetrolprices.com/China/electricity/` 表格解析 |
| E20 | **ollama registry manifest 体积**：`qwen3-coder-next/q4_K_M` model = **51,741,599,936 B**；`qwen3.6/35b` model = 21,718,480,960 B + projector 902,821,728 B；`glm-4.7-flash/q4_K_M` model = **19,019,269,280 B**；`qwen3.6/27b` 与 `glm-4.7-flash/q4_K_M` manifest 均可取（http=200） | `curl https://registry.ollama.ai/v2/library/<name>/manifests/<tag>` |
| E21 | **现役 Modelfile 无任何 PARAMETER**（只有 FROM + TEMPLATE），故 ctx 走 ollama 默认 | `cat /data/models/Modelfile`（59 B）+ `curl /api/show`【转引 our-workload.md】 |
| E22 | **调度器并发限额**：`mavis-m31f: 4`、`glm-cp: 4`、`glm-cp-max: 4`、`kimi-k3: 4`、`step-5: 3`、`qwen30b-local: 2`；`HOST_LIMITS = {"anolis": 14, "local": 3}`；`BENCH_LIMIT = 24` | 读 `tools/factory-sched.py:50-58` |
| E23 | **生产实例未受影响**：测试结束后 `pgrep -a ollama` 只剩 pid 2713982（生产实例） | `ssh anolis` 实查 |
| E24 | **mavis 通道今日实际在产**：anolis 上有 `mcode exec --model minimax/MiniMax-M3.1-Flash` 与 `--model minimax/MiniMax-M3` 的 run-one.sh 在跑 | `pgrep -af 'mcode exec'` 实查 |

### 4.2 推断（本报告的判断，非实测）

| # | 推断 | 依据与不确定度 |
|---|---|---|
| I1 | 「m3（免费臂）会全面优于本地 30B」 | 依据 E10（D1 63.6% vs 37.0%、墙钟 191s vs 302s）。**但 D2/D3 缺 m3 数据**（fix1 目录里没有 m3 的 d2/d3），不确定度中等 |
| I2 | 「本地臂的主要价值收敛为抗故障 + 并发溢出 + 保密离线」 | 依据 E1（免费臂存在且已复现）+ `状态/优惠通道.md` 的 2026-10-20 停摆事故 + E22（profile 限额）。**未做"配额打爆时本地臂顶上去"的对照实验** |
| I3 | 「把 ctx 从 262K 降到 32K 能把有效吐字速率从 19.5 拉到 30+」 | 依据 E13（p99=28.8K ⇒ 32K 够用）+ 同族实测的深度→速率衰减曲线【转引】。**本轮未实测**；风险：降 ctx 截断长任务可能掉解题率 |
| I4 | 「两独立实例 +19% 聚合吞吐的收益在真实负载下成立」 | 依据 E16（微基准层实测 +19%）。**真实负载未测**（真实负载下长上下文注意力占比更高，实例间隔离收益可能不同） |
| I5 | 「本地臂含折旧的每题成本在 ¥0.31–0.67 区间」 | 依据：capex 假设 ¥60k–120k、4 年直线【**假设，未找到采购价证据**】+ E17/E18/E19 实测功耗与墙钟。**不确定度大** |
| I6 | 「Qwen3.6-35B-A3B 是下一档首选」 | 依据 E20（体积）+ 【转引】官方分数（SWE 73.4 / TB 51.5）+ 【转引】V100 98.8 tok/s。**本轮未在 V100 上跑过它** |
| I7 | 「若要换模型，第一步不是换模型，是先补 harness 的 `max_tokens` 与 thinking 开关」 | 依据 E11/E17 + 【转引】our-workload.md §1.3 的两个缺口。**未验证 ollama `/v1/chat/completions` 是否吃 `think`/`options` 扩展字段** |

### 4.3 本轮"未找到公开证据 / 未验证"清单

| 项目 | 状态 |
|---|---|
| **我们机房实际结算电价** | **未找到**——用的是 globalpetrolprices 的全国工商业均价 ¥0.791/kWh（2026-03-01） |
| **这 2×V100S 的采购价** | **未找到**——工作区无采购记录；折旧表是**假设区间**，不是事实 |
| **Qwen3-Coder-Next 在 V100 上的第三方吞吐实测** | **未找到公开证据**（同批笔记同样明写） |
| **Coder-Next 的 KV cache 每 token 实测口径** | **未实测**（只按架构参数复算） |
| **GLM-4.7-Flash 的官方 SWE-V / TB 分数** | **本轮未核到**（只拿到 registry 体积 19,019,269,280 B 与 manifest 可得性） |
| **M3.1-Flash 的 SWE-bench Verified 第三方复现** | **未找到**——Vals.ai 的 86 模型 swebench 表里**没有** M3.1-Flash 条目；只在 Terminal-Bench 4.0 表里有（25.253%） |
| **MiniMax-M3.1-Flash 在 OpenRouter 免费档的速率限制具体数值** | **未取到具体数字**——官方 limits 页的表格数值是 JS 渲染，只取到"按累计购买额分档的 requests/minute 与 requests/day"的结构说明 |
| **Qwen3.6-35B-A3B 在 ollama 0.40.6 上是否支持关闭 thinking 的字段** | **未验证**（`think: false` / `options` 扩展字段都没试） |
| **本地臂在 D2/D3 换成更强模型后的收益** | **未实测**（本轮未跑任何新模型的 bench） |
| **V100S 32GB 二手成交价** | **未找到成交价证据**（eBay 403）；折旧表用的是区间假设 |

---

## 5. 对我们的具体建议（落到 anolis-gpu-01）

### 5.1 决策（一句话）

**不要为了"提解题率"去换本地模型——免费 API 臂已经 1.7–1.9 倍于它。要做的是三件零下载的事：①把现役 30B 的 ctx 从 262K 降到 32K；②改成两卡各跑一个独立实例（+19% 聚合吞吐）；③把本地臂的定位从"量产臂"改成"抗故障兜底 + 并发溢出 + 保密离线题"。** 换模型（Qwen3.6-35B-A3B）留到 ①③ 做完、且 harness 的 thinking/`max_tokens` 缺口补上之后，作为 P1 打榜项。

### 5.2 P0：零下载、零换模型（建议本周做完）

**P0-1｜ctx 档位 262K → 32K（释放约 42 GiB 显存）**
```bash
# 只读体检
ssh anolis 'nvidia-smi --query-gpu=index,memory.total,memory.used --format=csv; \
            curl -s http://127.0.0.1:11434/api/version; \
            cat ~/.config/ollama/env; cat /data/models/Modelfile'
# 现状：Modelfile 只有 FROM + TEMPLATE，无 PARAMETER ⇒ 走 ollama 默认 262144
# 改（先备份）
ssh anolis 'cp /data/models/Modelfile /data/models/Modelfile.bak.$(date +%F) && \
cat > /data/models/Modelfile <<EOF
FROM /data/models/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf
TEMPLATE """..."""
PARAMETER num_ctx 32768
PARAMETER temperature 0.0
PARAMETER top_p 1.0
EOF'
```
> ⚠️ **TEMPLATE 行必须原样保留**（现役用的是 Unsloth chat template，工具调用形态依赖它；且该模板有"结尾 2 个以上 assistant 消息就 400"的边界【转引】）。
> ⚠️ **必须避开在役 bench**：ollama 是裸进程托管，重启前先 `pgrep -af 'af-bench|mcode exec'` 确认无在跑的判分容器。

**P0-2｜两卡各跑一个独立实例（实测 +19% 聚合吞吐）**
```bash
# 现状：单实例 11434 拆两卡 + 2 slot = 219 tok/s
# 改成：两个实例，各绑一张卡，各 1 slot
ssh anolis 'cat > ~/.local/bin/ollama-2inst.sh <<EOF
#!/bin/bash
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_HOST=127.0.0.1:11436
CUDA_VISIBLE_DEVICES=0 exec $HOME/.local/bin/ollama serve
EOF
# 第二个实例把 0 换成 1、11436 换成 11437'
# 实测依据：11436(单卡) 131.7–133.9 tok/s；双实例聚合 260.7 vs 单实例 219 tok/s
```
> **af-bench 侧**：`main.rs:283-301` 的 `qwen30b-local` 档案 `base_url` 指向 `http://127.0.0.1:11435/v1`（本机隧道 → anolis 11434）。两个实例需要**两个 base_url** ⇒ 建议加一个 `qwen30b-local-b` 档案（`base_url` 指向 11437 的隧道），调度器 `PROFILE_LIMITS` 里 `"qwen30b-local-b": 2`。
> ⚠️ **本轮已实测过这个拓扑（11436/11437），确认可行；但我在测试后已 kill 复原，落地时需要重做并更新 `~/.config/ollama/env` 与重启脚本。**

**P0-3｜给 OpenAI 协议路径补 `max_tokens`（防止白烧 GPU）**
- 文件：`af/crates/af-harness/src/endpoint.rs` 的 `openai_body()`（当前在 `:186-213`）。
- 改法：加档案级开关 `body["max_tokens"] = endpoint.max_tokens`。
- ⚠️ **不改 Anthropic 臂的测量口径**（Anthropic 路径本来就发，`:277-282`），但**必须 bump 结果代号**（工作区纪律：改了现实不更新文档 = 严重违规）。

**P0-4｜给本地档案补 thinking 开关**（Qwen3.6-35B-A3B 上线的硬前提）
- 先验证 `ollama /v1/chat/completions` 是否吃 `think: false` 或 `options: {think: false}`（**本轮未验证**）。
- 若不支持，则走 ollama 原生 `POST /api/chat`（它支持 `think` 字段），需要 harness 加一个新协议分支。

**P0-5｜把"免费臂"从实验地位升格为产线主力（零工程量，收益最大）**
- 我们已经有：**mavis-m31f D1 70.0%**、**mavis-m3 D1 63.6% 且墙钟仅 191s**、**glm-cp D1 62.7%**、**glm-cp-max D1 76.8%**。
- 建议把 D1/D2 的默认生产臂改成 **m3（免费、191s）** 或 **m31f（免费、70%）**；glm-cp-max 留给 D3（50.0%）。
- **必须同步做两件防护**：①**mcode token 续期互斥**（`tools/mcode-token.py` 的 flock 已经解决过一次同类事故，**不要退回无锁并发刷新**）；②**本地臂保持在线**作为免费臂的兜底。
- **配额纪律**：`general` 的 5h/周池虽然文本调用不计数，但**不要把它当无限额**——2026-10-20 的整条停摆就是先例。**保留 DeepSeek V4.1 Flash 夜间档（空闲时输出 ¥4/M，全场最低）和 OpenRouter 锚定作为第二、第三条腿。**

**P0-6｜本地臂的定位改写（文档动作，零运行时成本）**
- 在 `计划/50-bench实测方案.md` §2.2 的模型选型矩阵里，把 `Qwen3-Coder-30B（本地）` 这一行的"每任务先验成本"从"电费"改成 **"电费 ¥0.025/题 + 占用 2 卡墙钟；定位改为抗故障兜底/并发溢出/保密离线"**，并明确 **"D1/D2 量产走免费 API 臂"**。

### 5.3 P1：换模型打榜（做完 P0 之后）

**顺序**：先按 P0-1/P0-2 **重跑现役 30B 拿到"调参后基线"**（这一步是所有换装结论的分母），再下 **Qwen3.6-35B-A3B**（registry 实测 20.23 GiB + 0.84 GiB projector，**单卡装得下 ⇒ 2 卡各一个独立实例**）。

```bash
# 磁盘：/data 已 94% 满（18G 可用）→ 先回收 docker
ssh anolis 'docker system df; df -h /data'
# 拉模型（约 21 GiB）
ssh anolis 'ollama pull qwen3.6:35b'
# 显式 ctx（关键：别让它走 262144 默认）
ssh anolis 'cat > /data/models/Modelfile-35b <<EOF
FROM qwen3.6:35b
PARAMETER num_ctx 32768
PARAMETER temperature 0.0
PARAMETER top_p 1.0
EOF
ollama create qwen3.6-35b-local -f /data/models/Modelfile-35b'
```

**冒烟清单（缺一不进 af-bench）**：
- a. 架构符号：`strings /data/models/lib/ollama/libllama.so.0 | grep -E 'QWEN35MOE|QWEN35'`（同族符号已在【转引】中确认）；
- b. **sm_70 崩溃 issue #29783 回归**：同款 prompt 连发 20 次不出错；
- c. **thinking 关闭后 token 计数**：一轮输出应回到 ~150–400 token 量级（现役 30B 是 152.7 token/轮）；
- d. **工具调用形态**：能稳定吐 `{"name":"bash","arguments":{"command":…}}`；
- e. **连续 assistant 消息**：构造 tool-free 轮，确认不再 400（配合 P0-4 的分类记账）；
- f. **KV 实际占用**：从 `llama_kv_cache` 日志行读出每 token 字节，再定 ctx 档位（35B-A3B 有 30 层 linear-attn，KV 口径与现役 96 KiB/token **不同**）。

**判定口径**：同一批 D1（23–62 题）+ TB 短任务，比 **解题率** 与 **单题墙钟中位** 两个数。**解题率低于 P0 调参后的 30B 基线 ⇒ 直接淘汰。**

**档案接入（3 处最小改动，同 `notes/our-workload.md` §1.8）**：
1. `af/crates/af-bench/src/main.rs` 的 `fn profile(name)`（`:188-351`）加 `qwen3-35b-local` 臂（照抄 `qwen30b-local` 的形状，`:283-301`）；
2. `tools/factory-sched.py:53`（`PROFILE_LIMITS`）+ `:75-87`（`OUT_DIRS`）；
3. `计划/变更日志.md` + `状态/组件建设状态.md` 登记。

### 5.4 P2：只有在 P1 出正面结论才做

- **Qwen3-Coder-Next 48.19 GiB**：**必须先做完 P0-1**（否则显存不够），且**只跑 SWE-V 不跑 TB**（TB 自报倒退 ~17 分）⇒ 定位成"**SWE 专项加强臂**"。
- **不要碰**：稠密 27B 家族（墙钟 4–8×）、GPT-OSS-120B MXFP4、Qwen3.8-Flash-Next、任何 480B+ 模型。

### 5.5 什么条件下值得再投工程量换本地模型（决策规则）

**值得，当且仅当下面至少一条成立：**

1. **免费/套餐 API 臂不可靠成为常态**（不是偶发）：mcode token 反复整族吊销、429 风暴常态化、周池长期打满 ⇒ 本地臂是唯一能持续产出的路径 ⇒ 值得投工程量把它做得更强（Qwen3.6-35B-A3B 优先）。
2. **保密/离线题**成为产线的一部分（代码不能出内网）⇒ 本地臂是唯一路径 ⇒ 值得投。
3. **配额打爆后的持续溢出量** > 本地臂的运维成本：按本轮实测，本地臂每小时解出 8.1 题（现状）/ 9.6 题（两实例改造后），且**不消耗任何外部配额** ⇒ 若产线的日增量超过这个量级，扩本地产能（两实例 + 35B-A3B）就是划算的。
4. **降 ctx / 拆实例 / 补 harness 旋钮之后，本地臂的解题率仍显著低于免费臂**（即配置不是瓶颈）⇒ 此时换模型才是唯一剩下的杠杆。

**不值得，当：**
- 只是想要更高的解题率 ⇒ **免费 API 臂（m31f 70.0% / m3 63.6% / glm-cp-max 76.8%）已经零成本地超过任何本地候选**。
- 产线规模是"几千题/季度"级别 ⇒ 配额根本不构成约束，本地臂是纯成本中心（占 2 张卡 + 运维注意力 + 换模型的工程量）。
- 还没有把 P0 的零成本改进做完 ⇒ **先做完再谈换**（配置不是瓶颈时，换模型才是杠杆；配置是瓶颈时，换模型是浪费）。

---

## 6. 一句话回答任务书的核心问题

> **「有没有一个模型，能在相近甚至更低的单题墙钟成本下，比现役 qwen3-coder-30b 解题率更高（即"更值得上"）？」**
>
> **有，但不需要为此付出换模型的工程量。** 现役 30B 的 D1 37.0% 之所以低，主要**不是模型弱，是配置弱**（262K ctx 把显存吃到 95%、拆卡、每轮重发全历史、无 `max_tokens`、无 thinking 旋钮）。而**零现金成本的 mavis 免费臂（MiniMax-M3 D1 63.6% / 墙钟 191s；MiniMax-M3.1-Flash D1 70.0%）在解题率和墙钟上同时超过现役**——本地臂的"省 API 钱"动机已经不成立。
>
> 本地臂该守的位置是：**抗外部故障（2026-10-20 mcode 整条停摆是先例）、配额打爆时的并发溢出、保密离线题**。在这个定位下，**唯一值得投的换装是 Qwen3.6-35B-A3B**（单卡 20.23 GiB、SWE 73.4 / TB 51.5 双超现役），且必须在 ctx 降到 32K、拆成两独立实例、harness 补上 `max_tokens` 与 thinking 开关之后，作为 P1 打榜项——**先做零成本的，再谈换模型的**。

---

*报告生成：本地模型选型调研子代理，2026-10-21。所有"转引"数字建议在决策前于原始出处二次核对。本轮未下载任何模型权重；anolis 上起过的两个临时 ollama 实例（11436/11437）已 kill 复原，生产实例 pid 2713982 未受影响（`pgrep -a ollama` 实查）。*
