# 国内厂商 2026 开源权重编码/推理模型扫描 —— 智谱 / Kimi / DeepSeek / Step / MiniMax / 字节 / 百度 / 腾讯 / 商汤 / 书生 / 百川 /（附）蚂蚁 Ling

- 产出日期：**2026-10-21**
- 调研者：本地模型选型调研子代理（工作区 `调研/本地模型选型/notes/`）
- 基线环境（所有"能不能跑/代价多少"都以此为准）：
  - anolis-gpu-01：2× Tesla **V100S-PCIE-32GB**，CC 7.0（sm_70，无 NVLink），driver 570.133.20，CUDA 12.6 工具链，125 GB 内存
  - 已有：ollama **0.40.6**（自带 llama.cpp runner），**无**独立 llama-cli / llama-server / vLLM / SGLang
  - 现役：`qwen3-coder-30b` = Qwen3-Coder-30B-A3B-Instruct-Q4_K_M（18.5 GB，30.5B 总参 / 3.3B 激活，ctx 262144）
  - 现役实测（沿用本工作区已记录值）：decode **135.7 tok/s**、prompt **149.1 tok/s**（num_ctx 8192）、加载 10.5 s；并发 2 时每请求 109.7 tok/s、合计 ~219 tok/s
- 工作负载：af-bench（SWE-bench Verified / Terminal-Bench / InjecAgent / τ²-bench），每题 ~10 轮工具调用，定位是"零 API 额度的量产臂"，**单题墙钟与吞吐同等重要**。

## 0. 本轮的方法与边界（先把话说死）

| 项 | 事实 |
|---|---|
| 网络 | 本会话所在主机是 **pandev-comp（RTX 3070 Laptop 8GB，`hostname` = PanDeveopComp）**。`ssh anolis-gpu-01` **解析失败**（`Could not resolve hostname`），**本轮没有在 anolis 上跑任何 GPU 测试**，也没有下载任何权重。 |
| HF 访问 | `huggingface.co` 直连超时（DNS 被劫持到 facebook IP 段），但 **`hf-mirror.com` 可用**（HTTP 200），本报告所有 HF 侧的权重体积、config.json、README 均取自 `hf-mirror.com` 的公开 API/原始文件。`raw.githubusercontent.com` 可用（用于查 llama.cpp 源码），`github.com` 页面本身返回 200 但 API 403。 |
| 分数口径 | "官方 agentic 分数"一律是**厂商自报**（模型卡/official 文档/AA 汇总）；"第三方复现"单独标注来源；**推理型模型的 AA 分多为"Estimated"，AA 已注明"independent evaluation forthcoming"**。 |
| 体积换算 | 报告中"B16 权重体积"= HF API `siblings[].size` 对 `*.safetensors` 求和（**直接证据**）；"Q4_K_M 估算"= B16 × **0.30**（我用 3 组已知的真值校准过：Qwen3-Coder-30B-A3B 61.0→18.5 GB = 0.303；GLM-4.7-Flash 59.9→18.31 = 0.306；GLM-4.5-Air 220.9→63.62 = 0.288）。**凡是写"≈"的都是估算**，有真实 GGUF 文件大小的我一律写真值。 |
| 姊妹笔记 | 本工作区已有同批次姊妹笔记 `v100-speed-data.md`（V100 实测吞吐库）、`chinese-community.md`、`qwen-family.md`、`quant-ecosystem.md`。本报告引用它们的实测数字时**明确标注"引自姊妹笔记（非我本轮实测）"**。 |

---

## 1. 一句话结论

**"国内其他厂商"里，2026 年唯一同时满足「开源权重 + 真开源权重可下 GGUF + 激活参数只有 3B（因此在 V100 上和现役同速）+ 官方 agentic 分数高于现役 + 单卡装得下」的模型是 `GLM-4.7-Flash`（智谱，30B-A3B，MIT，Q4_K_M 18.31 GB，官方 SWE-bench Verified 59.2 / τ²-Bench 79.5）。**
其余所有 2026 年的国产大模型（GLM-4.7/5/5.3/5.3-Flash、Kimi K2.5/K2.6/K2.7-Code/K3、DeepSeek V3.2/V4-Flash/V4.1-Flash、Step-3.5/3.7/5、MiniMax M2/M2.5/M2.7/M3、混元 Hy3/Hy4、书生 Intern-S2、百川 M3、ERNIE-4.5-300B）**Q4 权重全部 > 64 GB，一律装不下 2×V100S-32GB**，在 V100 上只能走 CPU 卸载——而 CPU 卸载的实测代价（引自姊妹笔记 `v100-speed-data.md` E20 行）是**掉到个位数 tok/s**，属于"降级方案，不能作主链路"。

**因此对"有没有模型能在相近墙钟成本下比现役解题率高"的回答是：有，且只有一个家族（GLM-4.7-Flash，含其社区 SFT 版），其余全是"更强但装不下"。**

---

## 2. 候选清单总表

> 列含义：**Q4 体积**（GB，有真值写真值，估算写 ≈）｜**GGUF/ollama**（谁提供的、是否官方）｜**官方 agentic 分**（自报）｜**第三方反馈**｜**我们的适配判断**（对 2×V100S-32GB + ollama + af-bench）
> 现役基线：**Qwen3-Coder-30B-A3B-Instruct** — 官方 SWE-bench Verified **51.6**（OpenHands 500 轮）、Terminal-Bench **31.3**、Aider-Polyglot 33.3、BFCL-v3 62.2、TAU-Bench Retail 68.7（引自姊妹笔记 `v100-speed-data.md` §3.1，读自官方模型卡图）；AA Intelligence Index **10**（我本轮直接抓 AA 模型页）；我们实测 135.7 tok/s。

### 2.1 智谱 GLM 系（本次最重要的家族）

| 模型 | 类型 / 激活 | B16 权重 | Q4 体积 | ctx | GGUF / ollama | 官方 agentic 分（自报） | 第三方反馈 | 我们的适配判断 |
|---|---|---|---|---|---|---|---|---|
| **GLM-4.7-Flash** | MoE **30B / 3B 激活**（47 层，64 专家选 4 + 1 共享，`Glm4MoeLite`，**MLA** q_lora 768 / kv_lora 512） | **59.9 GB**（BF16 GGUF 49.91+10.00） | **18.31**（unsloth Q4_K_M 真值）｜ollama tag **19GB**；Q5_K_M 21.41 / Q8_0 31.84 | **200K**（ollama tag 标 198K） | ✅ **ggml-org/GLM-4.7-Flash-GGUF**（llama.cpp 官方 org，2026-01-23）＋ unsloth 全量化档；✅ ollama 官方 `glm-4.7-flash`（q4_K_M 19GB / q8_0 32GB / bf16 60GB，均 198K） | **SWE-bench Verified 59.2**、**τ²-Bench 79.5**、BrowseComp 42.8、AIME25 91.6、GPQA 75.2、LCB v6 64.0、HLE 14.4（官方模型卡对比表，同时列 Qwen3-30B-A3B-Thinking-2507 = 22.0 / 49.0 与 GPT-OSS-20B = 34.0 / 47.7） | ① HF 讨论 #53："exceptional tool use handling in various typescript cli coders"（正面）；② HF 讨论 #47 llama-bench（build 7822, FA=off）：GLM4.7-Flash Q8_0 tg128 **10.77** vs qwen3moe-30B-A3B Q8_0 **12.95**（-17%），depth 2048 处 **5.28 vs 11.23**（-53%）；③ 讨论 #75：偶发把转义 `\n` 写坏、误删邻近代码且不自知（Q8_0 + llama-server）；④ 讨论 #48：偶发无限重复（另一例归因于 FP8 KV + FlashMLA） | ✅✅ **唯一强推**。与现役**同构**（同 30B-A3B 档、18.3GB 单卡全上卡、第二卡照旧空转），零新增部署风险；官方 SWE-V 59.2 > 现役 51.6，τ²-Bench 79.5 正好命中我们 harness 题型 |
| **GLM-4.7-Flash-Coder**（社区 SFT，whitecircle，base=zai-org/GLM-4.7-Flash，MIT） | 同上 30B-A3B | — | **18.13**（ngquocvinh Q4_K_M 真值） | 同上 | ⚠️ 仅社区量化（ngquocvinh / LakoMoor / ali-sys-1370），**无官方 GGUF** | SWE-rebench-V2（500 Python 题，PI harness）pass@1 **0.3315 → 0.4165**（+25.6%），**轮数 -45%**、每题成本 -14%（作者自测） | whitecircle 自测；作者称"beats Qwen3.5-122B-A10B 与 Devstral-2"、"略超 Ling-2.6-Flash" | ⚠️ **值得试但先不换主线**。轮数 -45% 对我们的"单题墙钟"是直接收益；风险是它只在 PI（bash/read/edit/write）harness 上训过，迁移到 af-bench 未验证 |
| GLM-4.5-Air | MoE 110B / 12B 激活 | 220.9 GB | **63.62**（ggml-org Q4_K_M 真值，单文件） | 128K | ✅ ggml-org / unsloth GGUF | AA Index **11** | — | ❌ **63.62/64 GB 装不下**：KV cache、CUDA context、激活值都没有余量 |
| GLM-4.7（大版） | MoE **358B** / 32B 激活 | **716.7 GB** | ≈215 | 200K | 社区 GGUF（mradermacher/GLM-4.7-REAP-268B-A32B-GGUF 等） | 官方 SWE-V **73.8**、SWE-Multilingual 66.7、**Terminal-Bench 2.0 41%**、τ²-Bench 84.7、LiveCodeBench v6 84.9、HLE 42.8、AA Index **22** | — | ❌ 装不下；**且 ollama 上已于 2026-07-15 retired**（引自姊妹笔记）→ 只能走 API |
| GLM-5 | MoE 754B / 40B 激活 | **1507.7 GB** | ≈450 | 200K | 社区 GGUF | AA Index 28（引自姊妹笔记） | — | ❌ 装不下 |
| GLM-5.3 | MoE 378B（`GlmMoeDsa`） | **755.6 GB** | ≈227 | **1M** | 社区 GGUF | AA Index **45**（开源天花板档） | — | ❌ 装不下 |
| GLM-5.3-Flash | MoE **320B 总参 / 18B 激活**，原生多模态，稀疏+线性混合注意力 | — | **181.36**（ggml-org Q4_K 真值；Q2_K 仍 133.8） | **1M** | ✅ ggml-org/GLM-5.3-Flash-GGUF（2026-10-19，含 MTP 与 mmproj） | 官方："approaching Claude Opus 4.8 on coding and agentic"；AA Index **42**、76.2 t/s | — | ❌ 装不下；且 18B 激活在 V100 上解码是 3B 档的 ~6 倍成本 |

### 2.2 月之暗面 Kimi

| 模型 | 类型 / 激活 | B16 权重 | Q4 体积 | ctx | GGUF | 官方分 | 第三方 | 适配判断 |
|---|---|---|---|---|---|---|---|---|
| Kimi-K2.5 | MoE 298B | **595.2 GB** | ≈179 | — | 社区（QuantPasture / Panchovix 等） | — | — | ❌ |
| Kimi-K2.6 | MoE 298B | **595.2 GB** | ≈179 | 256K | 社区 | AA Index **27**、72.4 t/s | — | ❌ |
| Kimi-K2.7-Code | MoE 298B，coding/agentic 专用 | **595.2 GB** | ≈179 | 256K | 社区 | AA Index **26**、59.3 t/s、$0.54/task | — | ❌ 装不下（ollama 有 `kimi-k2.7-code` tag 但拉不动） |
| Kimi-K3 | MoE（HF 权重 1560.9 GB；AA 口径称 2.8T 总参 / 104B 激活，两者不一致） | 1560.9 GB | ≈470 | 1M | 社区 | AA Index **44**、42.1 t/s | — | ❌ 装不下 |
| **Kimi-Linear-48B-A3B-Instruct** | MoE 49B / **3B 激活**，KDA 混合线性注意力 | **98.2 GB** | ≈29.5 | **1M** | 社区 | AA Index **7**（很弱） | — | ⚠️ 装得下但能力不足（AA 7 < 现役 10） |

### 2.3 DeepSeek

| 模型 | 类型 / 激活 | B16 权重 | Q4 体积 | ctx | GGUF | 官方分 | 第三方 | 适配判断 |
|---|---|---|---|---|---|---|---|---|
| DeepSeek-V3.2 | MoE 685B / 37B（61 层，256 专家选 8） | — | ≈205 | 163,840 | 社区 | AA Index **16** | — | ❌ |
| **DeepSeek-V4-Flash** | MoE，256 专家选 6 + 1 共享，`DeepseekV4`，DSA 稀疏注意力（index_topk 512 / num_hash_layers 3 / sliding_window 128），**专家 fp4 + 权重 fp8 分块量化**，MTP | 159.6 GB（**注意**：这是 fp8/fp4 混排后的字节数，不是参数数） | **155.1**（unsloth UD-Q4_K_XL 五个分片真值合计）｜UD-Q3_K_M **129.3**｜UD-IQ1_M **86.9** | **1M** | ✅ unsloth/DeepSeek-V4-Flash-GGUF（全量化档） | AA Index **34**、144.2 t/s、$0.17/task、MIT | — | ❌ **即便压到 IQ1 也要 86.9 GB > 64 GB**，装不下；且 V4 架构在官方 repo 里带**自研 `inference/` kernel**（非 transformers 原生），sm_70 跑它的风险是"未知的未知" |
| DeepSeek-V4.1-Flash | MoE 255B | **510.3 GB** | ≈153 | 1M | ✅ unsloth/DeepSeek-V4.1-Flash-1017-GGUF | AA Index 45（引自姊妹笔记） | — | ❌ |

### 2.4 阶跃星辰 Step

| 模型 | 类型 / 激活 | Q4 体积 | ctx | GGUF | 官方分 | 适配判断 |
|---|---|---|---|---|---|---|
| Step-3.5-Flash | MoE 196B / 11B 激活（45 层，288 专家选 8） | **111.50**（官方 stepfun-ai/Step-3.5-Flash-GGUF-Q4_K_S，12 分片真值） | 262,144 | ✅ **厂商官方 GGUF** | AA Index **17**、129 t/s | ❌ 装不下 |
| Step-3.7-Flash | MoE（Step-3.7） | **111.50**（官方 stepfun-ai/Step-3.7-Flash-GGUF Q4_K_S 三片真值；Q3_K_M 102.5） | 262,144 | ✅ **厂商官方 GGUF**（含 MTP、mmproj、imatrix） | AA Index **19**、**222.8 t/s** | ❌ 装不下 |
| Step-5-Preview | 600B / 27B 激活（AA 口径） | — | 1M | 仅 NVFP4（Blackwell 格式，**V100 不支持**） | AA Index 44（引自姊妹笔记） | ❌ 双重不可行 |

### 2.5 MiniMax

| 模型 | 类型 / 激活 | B16 权重 | Q4 体积 | ctx | GGUF | 官方分 | 适配判断 |
|---|---|---|---|---|---|---|---|
| MiniMax-M2 | MoE 115B / 10B 激活 | — | ≈66 | 196,608 | 社区 | AA Index **19**、63.8 t/s | ❌ 贴边/超 |
| MiniMax-M2.5 | 同族 | — | ≈66 | — | 社区 | — | ❌ |
| MiniMax-M2.7 | MoE 115B / 10B 激活 | **230.1 GB** | ≈69 | 204,800 | 社区（mudler / SickRick / ox-ox） | — | ❌ 装不下 |
| MiniMax-M3 | MoE **427B**（`MiniMaxM3Sparse`，原生多模态） | **854.2 GB** | ≈256 | 1M | 社区 | AA Index **29**、91.6 t/s | ❌ |
| MiniMax-M3.1-Flash | **428B** | — | — | 976K | ❌ **ollama 上只有 `:cloud` tag（纯 API），无本地权重** | $0.15/$0.60 | ❌ 本地不存在 |
| MiniMax-H3 | — | 拉取失败（config.json 404） | — | — | — | — | ❌ 未找到可用证据 |

### 2.6 字节 / 百度 / 腾讯 / 商汤 / 书生 / 百川

| 厂商 | 模型 | 类型 / 激活 | 权重 | GGUF | 官方分 | 适配判断 |
|---|---|---|---|---|---|---|
| **字节** | Seed-Coder-8B（Base/Instruct/Reasoning，MIT，ctx 32K/64K） | 稠密 8B | ~16 GB B16 | ✅ unsloth/Seed-Coder-8B-{Instruct,Reasoning}-GGUF | "SOTA among open-source models of comparable size"（作者自报，图在模型卡 `imgs/seed-coder_intro_performance.png`） | ❌ 8B 稠密，比现役低一个半档 |
| | 其他 | — | — | ❌ 豆包/Seed-Coder 大版本**无开源权重**（HF author ByteDance-Seed 下只有 Seed-Coder-8B、Seed-OSS-36B、BAGEL/Stable-DiffCoder 等研究模型） | — | ❌ |
| **百度** | ERNIE-4.5-21B-A3B(-PT) | MoE 21B / 3B 激活 | **43.7 GB** B16 → ≈13 | ✅ mradermacher/ERNIE-4.5-21B-A3B-PT-GGUF | 卡片主打医疗/多模态 | ⚠️ 装得下，但是 **2025-06 的老模型**，2026 年**没有新的 ERNIE 开源 LLM**（baidu author 下 2026 年只有 OCR/VL/图像） |
| | ERNIE-4.5-300B-A47B | 302B | 603 GB | 社区 | — | ❌ |
| | ERNIE-5 | — | — | — | — | ❌ **未找到任何公开权重证据** |
| **腾讯** | Hunyuan Hy3 | MoE ~300B | **597.6 GB** | — | — | ❌ |
| | Hy4-preview | MoE ~780B | **1560.0 GB** | — | — | ❌ |
| | Hunyuan-A13B-Instruct | MoE 80B / 13B | ~45 GB（推算） | 社区 | — | ⚠️ 装得下但 2025-06 老模型 |
| | Hy-MT2-30B-A3B | MoE 30B / 3B | — | ✅ **厂商官方 GGUF**：Q4_K_M **18.24 GB** / Q8_0 31.99 | — | ❌ **是翻译模型**，与编码无关（体积与 GLM-4.7-Flash 同档，容易误选） |
| **商汤** | — | — | — | — | — | ❌ **未找到公开 LLM 权重证据**（HF author SenseTime 只有检测/分割/3D 模型） |
| **书生/InternLM** | Intern-S2-397B | 403B | **806.9 GB** | 社区 | — | ❌ |
| | Intern-S1 / InternLM3-8B / Intern-Decision-0.8B~4B | 小 | — | 社区 | — | ❌ 太小 |
| **百川** | Baichuan-M2-32B | **稠密 32B**（Qwen2.5-32B 全参微调） | 67.1 GB B16 → ≈20 | ✅ 官方 Baichuan-M2-32B-Q4_K_M-GGUF | — | ❌ **它是医疗模型**（HealthBench 60.1），不是编码模型；且稠密 32B 在 V100 上解码 ~28 tok/s（引自姊妹笔记） |
| | Baichuan-M3-235B | 236B | 471.5 GB | ✅ 官方 GGUF（Q4_K_M） | — | ❌ 装不下 |
| **（附）蚂蚁 Ling** | Ling-2.6-flash | MoE **104B / 7.4B 激活**，混合线性注意力，MIT | 215.0 GB | 社区 | AA Index **10**（= 现役水平）、官方称在 SWE-bench Verified / TAU2-bench / BFCL-V4 上"同级别 SOTA"；4×H20 340 t/s | ❌ Q4 ≈ 64.5 GB，**贴边装不下**（KV 无处安放） |
| | Ling-3.0-flash | MoE 127B / 5B 激活 | 255.0 GB | 社区 | AA Index **20**、316.6 t/s | ❌ |
| | Ling-3.1-flash | MoE 287B | 573.8 GB | 社区 | AA Index **41**、218.5 t/s | ❌ |
| | **Ling-3.0-flash-REAP288-71B-A5B**（社区压缩） | 71B / 5B | — | ✅ 社区 GGUF：**Q4_K_M 44.29 GB**（真值） | — | ⚠️ **装得下**（44.29/64），但 REAP 是社区有损压缩、且 5B 激活解码比现役慢 ~1.5×；可做"上限探针" |

---

## 3. 重点候选展开分析

### 3.1 GLM-4.7-Flash —— 本轮唯一"强推"项

**它为什么是唯一一个"解码成本不涨、解题率涨"的国产模型**

1. **同档位**：30B 总参 / 3B 激活，与现役 Qwen3-Coder-30B-A3B（30.5B / 3.3B）**完全同构**。因此 V100 上的解码成本模型可以整体平移——按姊妹笔记 `v100-speed-data.md` 的实测，30B-A3B MoE Q4_K_M 在 V100S 32GB 上是 **110–136 tok/s**（我们现役 135.7）。
2. **装得下且只占 1 张卡**：Q4_K_M 权重 **18.31 GB**（unsloth 真值；ollama 官方 tag 标 19 GB），单张 32GB 卡放得下，和现役一模一样——**第二张 V100S 继续空转**（这是现役就存在的事实，不是新问题）。
3. **官方分数直接命中我们的题型**：SWE-bench Verified **59.2**（vs 现役官方 51.6，**注意两者脚手架不同**）、**τ²-Bench 79.5**（我们 harness 里有 τ²-bench）、BrowseComp 42.8（工具调用检索）。
4. **AA 综合分**：GLM-4.7-Flash **15** vs 现役 Qwen3-Coder-30B-A3B **10**（我本轮直接抓 AA 模型页文本，Index v4.3.2）。GLM-4.7-Flash 的 AA 分是 "Estimated"，AA 页面自己标了"independent evaluation forthcoming"。
5. **部署面齐全**：llama.cpp 官方 org（ggml-org）已发布 `GLM-4.7-Flash-GGUF`；ollama 官方库有 `glm-4.7-flash`（q4_K_M / q8_0 / bf16 三个 tag，全部 198K 上下文，2.1M 下载，"4 months ago" 更新），ollama 模型卡注明 **"this model requires Ollama 0.14.3 which is currently in pre-release"**——我们 0.40.6 满足。
6. **架构友好度**：GLM-4.7-Flash 用 **MLA**（q_lora_rank 768 / kv_lora_rank 512），KV cache 极小 → 198K 上下文在 32GB 卡上不构成显存压力（对比：GQA 模型的 KV 会随 context 线性膨胀）。

**它可能让我们更慢的三个原因（必须实测，不要假设）**

- **社区 llama-bench 显示它比同档 Qwen3MoE 慢**：HF 讨论 #47（作者 engrtipusultan，llama-bench build 8f91ca54e/7822，FA=off，AMD RX Vega 56 环境）：
  `tg128`：GLM4.7-Flash Q8_0 **10.77** vs qwen3moe-30B-A3B Q8_0 **12.95** vs gpt-oss-20B MXFP4 16.17；
  `tg128 @ d2048`：**5.28** vs **11.23** vs 15.20；`pp512`：102.81 vs 119.46 vs 147.08。
  讨论里回复也指出 Vulkan/ROCm 后端本身很慢、且 llama.cpp 的支持不是智谱官方做的（"llama.cpp support is not added by z.ai"），所以这组数字**只能当作"需要我们自己复测"的信号，不能当作 V100 上的定论**。但**上下文变深时 decode 掉到 1/2 这个形状值得警惕**——我们的 af-bench 每题 10 轮工具调用，上下文会一路涨。
- **它是 reasoning 模型，思考关不掉**：HF 讨论 #56 专门问"how to off Reasoning?"，社区只能靠 jinja 模板 `{% set enable_thinking = false %}`。现役 Qwen3-Coder-30B-A3B-**Instruct** 是 non-thinking。官方评测里 GLM-4.7-Flash 的 SWE-bench Verified 用的是 `temperature 0.7 / top_p 1.0 / max_new_tokens 16384`。**如果它的输出 token 数比现役多 1.5–2 倍，那墙钟就不省了**——这是本轮最大的未验证风险。
- **社区负面反馈**：讨论 #75 报告"即使要求不要动无关代码，仍会破坏转义 `\n`、删掉邻近字符且不自知"；讨论 #48 报告无限重复循环（另一例被归因于 FP8 KV cache + FlashMLA 的数值稳定性）。这两条都直接对应我们 harness 关心的"跨轮不崩"。

### 3.2 GLM-4.7-Flash-Coder（whitecircle 社区 SFT）—— 轮数下降是墙钟的直接杠杆

- **是什么**：`whitecircle/GLM-4.7-Flash-Coder`，MIT，base_model = zai-org/GLM-4.7-Flash，2026-09-12 发布，用 GLM-5.1 做教师、SWE-rebench-V2 成功轨迹做 SFT（框架 Halo 同步开源）。
- **它宣称的结果**（作者自测，PI harness，4 工具 bash/read/edit/write）：SWE-rebench-V2 pass@1 **0.3315 → 0.4165**（+25.6%），**推理 token 中位数 63 → 150（更多）**，但**助手轮数 82.5 → 44（-45%）**，**每题成本 $0.0443 → $0.0382（-14%）**；并行工具调用（一次回复里 2+ 个 read/bash/edit）从 1.6%/0.6%/≈0 涨到 9.7%/7.2%/×90。
- **为什么它对我们特别对口**：我们的痛点之一正是"每题 ~10 轮工具调用、单题墙钟敏感"。**轮数 -45%** 与我们"完成度纪律先于绝对能力"的前期结论同向。官方模型卡的 SFT 配方里 46/177M token 带 loss，工具调用 token 只占 16.1% loss——说明它主要在学"怎么用工具"而不是"怎么说话"。
- **风险**：① 只在 PI harness 上训练/评测，**迁移到 af-bench 未验证**；② 社区量化，无官方 GGUF；③ 它是 base 模型的 SFT，GLM-4.7-Flash 本身的踩坑（#75 破坏代码、#48 重复）**不会因为 SFT 消失**，反而可能因为"更爱并行调用"而放大。

### 3.3 对"80B-A3B MoE 假设"的检验：假设**成立但只在"权重能 100% 常驻显存"时成立**

用本轮拿到的国产模型全集重新检验这个假设：

| 假设 | 检验结论 | 证据 |
|---|---|---|
| "总参大、激活小的 MoE 解码快" | ✅ 成立，且这是 MoE 的物理基础 | 激活 3B 的 MoE（GLM-4.7-Flash / Qwen3-Coder-30B）vs 激活 30B 的 MoE（Step-3.5-Flash 11B、GLM-4.5-Air 12B、GLM-5.3-Flash 18B）：每 token 只需读激活部分权重，V100 的 900 GB/s 带宽下 3B 档实测 110–136 tok/s（姊妹笔记） |
| "80B-A3B 比 30B-A3B 更快" | ❌ **不成立** | 两者激活都是 3B → 每 token 读取量相同 → 速度持平甚至因"专家路数多、散点读更碎"而略慢（姊妹笔记结论一致） |
| "80B 级 MoE 的 Q4 约 45GB，双卡 64GB 装得下" | ❌ **对国产模型普遍不成立** | Q4 真值：Step-3.5-Flash **111.5**、Step-3.7-Flash **111.5**、Kimi K2.5/2.6/2.7-Code ≈179、GLM-4.7 ≈215、DeepSeek-V4-Flash **155.1**、MiniMax-M2.7 ≈69、GLM-4.5-Air **63.62**。**唯一压进 64GB 的"大激活"国产模型是 Ling-3.0-flash-REAP288-71B-A5B（44.29 GB，社区有损压缩）** |
| "放不下时用 `--n-cpu-moe` CPU 专家卸载" | ❌ **在我们的机器上是死路** | 姊妹笔记实测（同机 V100 32GB）：Qwen3-235B-A22B 全专家走 CPU → **2.13–3.48 tok/s**；静态 `--n-cpu-moe 88/82/76` → 2.43–4.18 tok/s；即便只把 **8 层**专家放 CPU（Qwen3-Coder-30B-A3B）→ 35.7 tok/s（-68%）。**我们无 NVLink，PCIe 是瓶颈** |

**所以本轮把假设改写成可执行的版本**：
> 在 2×V100S-32GB 上，能跑且快的只有「**权重 ≤ ~20GB 且激活 ≤ ~3–4B**」这一档（GLM-4.7-Flash / 现役 Qwen3-Coder-30B / Hy-MT2-30B-A3B-翻译模型）。想更强就必须接受"激活参数变大"或"权重压缩"，两者都直接抬高墙钟。

### 3.4 一个容易被忽略的事实：国产阵营的"下一代"全在 300B+ 量级

按本轮直接测到的 B16 权重体积排序（除 GLM-4.7-Flash 外）：

GLM-5 1507.7 GB ≈ Kimi-K3 1560.9 GB ≈ Hy4-preview 1560.0 GB > GLM-4.7 716.7 GB ≈ Intern-S2-397B 806.9 GB ≈ GLM-5.3 755.6 GB ≈ ERNIE-4.5-300B 603.0 GB ≈ Hy3 597.6 GB ≈ Kimi-K2.5/2.6/2.7-Code 595.2 GB ≈ Ling-3.1 573.8 GB ≈ MiniMax-M3 854.2 GB > Baichuan-M3-235B 471.5 GB ≈ Step-3.5/3.7 392 GB > Ling-3.0 255.0 GB > GLM-4.5-Air 220.9 GB ≈ Ling-2.6 215.0 GB > GLM-4.7-Flash **59.9 GB**。

**国产阵营在 2026 年明显向"超大 MoE + 少量激活"演进（GLM-5.3 378B、Kimi-K3 780B+、Hy4 780B、Step-5 600B、MiniMax-M3 427B），这恰恰是 V100 这类 32GB 卡最吃力的形态。** 如果我们的定位是"本地零成本量产臂"，那么**国产模型里"又强又轻"的甜点已经过去了，只剩 GLM-4.7-Flash 这一个 2026 年的 30B-A3B 窗口**（Ling-2.6/3.0 也是 100B+/127B，Q4 都超 64GB）。

---

## 4. 「直接证据」 vs 「推断」分栏

### 4.1 直接证据（本轮亲手抓取，可复现）

| # | 事实 | 取数命令/来源 |
|---|---|---|
| A1 | GLM-4.7-Flash 是 **30B-A3B MoE、MIT、200K ctx、官方 SWE-V 59.2 / τ²-Bench 79.5** | `hf-mirror.com/zai-org/GLM-4.7-Flash/raw/main/README.md`（模型卡表）+ `hf-mirror.com/.../config.json`（`n_routed_experts=64, num_experts_per_tok=4, kv_lora_rank=512, q_lora_rank=768, num_hidden_layers=47`） |
| A2 | GLM-4.7-Flash Q4_K_M = **18.31 GB**、Q5_K_M 21.41、Q8_0 31.84、BF16 59.91 | `hf-mirror.com/api/models/unsloth/GLM-4.7-Flash-GGUF/tree/main?recursive=1` |
| A3 | ollama 官方 `glm-4.7-flash`：q4_K_M **19GB** / q8_0 32GB / bf16 60GB，**198K 上下文**，"Updated 4 months ago"，"requires Ollama 0.14.3" | `ollama.com/library/glm-4.7-flash` 页面文本（已去标签提取） |
| A4 | AA Intelligence Index：GLM-4.7-Flash **15**（85.5 t/s）、Qwen3-Coder-30B-A3B **10**（158.2 t/s）、GLM-4.5-Air 11、GLM-4.7 22、GLM-5.3 45、GLM-5.3-Flash 42、Step-3.5-Flash 17、Step-3.7-Flash 19、Ling-2.6-flash 10、Ling-3.0-flash 20、Ling-3.1-flash 41、DeepSeek-V4-Flash 34、DeepSeek-V3.2 16、MiniMax-M2 19、MiniMax-M3 29、Kimi-K2.6 27、Kimi-K2.7-Code 26、Kimi-Linear-48B-A3B 7 | `curl https://artificialanalysis.ai/models/<slug>` → 去标签后取 "Model summary" 段（Index 版本 v4.3.2） |
| A5 | Q4 真值：GLM-4.5-Air **63.62**（ggml-org）、GLM-5.3-Flash **181.36**（ggml-org）、Step-3.5-Flash **111.50**（厂商官方）、Step-3.7-Flash **111.50**（厂商官方）、DeepSeek-V4-Flash **155.1**（unsloth UD-Q4_K_XL 5 片）、Ling-3.0-flash-REAP288-71B-A5B **44.29**、Hy-MT2-30B-A3B **18.24**（厂商官方）、GLM-4.7-Flash-Coder **18.13** | HF `tree/main?recursive=1` 逐文件 size 求和 |
| A6 | B16 权重体积（HF safetensors 求和）：GLM-4.7 716.7 / GLM-5 1507.7 / GLM-5.3 755.6 / Kimi-K2.5=K2.6=K2.7-Code 595.2 / Kimi-K3 1560.9 / DeepSeek-V4-Flash 159.6 / V4.1-Flash 510.3 / MiniMax-M2.7 230.1 / MiniMax-M3 854.2 / Hy3 597.6 / Hy4 1560.0 / Intern-S2-397B 806.9 / Baichuan-M3 471.5 / ERNIE-4.5-300B 603.0 / ERNIE-4.5-21B-A3B 43.7 / Kimi-Linear 98.2 / Ling-2.6 215.0 / Ling-3.0 255.0 / Ling-3.1 573.8 / GLM-4.5-Air 220.9 / GLM-4.7-Flash 59.9 | HF `api/models/<id>?blobs=true` |
| A7 | **DeepSeek-V4-Flash 即便压到 IQ1 也要 86.9 GB**（UD-IQ1_M 49.97+36.92+0.01）→ 装不下 | 同 A5 |
| A8 | DeepSeek-V4-Flash 架构：256 专家选 6 + 1 共享、`num_hash_layers 3`、`index_topk 512`、`sliding_window 128`、`expert_dtype fp4`、官方 repo 带**自研 `inference/` kernel 目录** | `hf-mirror.com/deepseek-ai/DeepSeek-V4-Flash/raw/main/config.json` + `api/models/...` 文件列表 |
| A9 | GLM-4.7 官方：SWE-V **73.8**、SWE-Multilingual 66.7、**Terminal-Bench 2.0 41%**、τ²-Bench 84.7、LiveCodeBench v6 84.9、HLE 42.8 | `docs.z.ai/guides/llm/glm-4.7.md` 原文 |
| A10 | GLM-5.3-Flash：**320B 总参 / 18B 激活**，稀疏+线性混合注意力，1M ctx，"GLM-5.3-FlashX 200 tokens/s" | `docs.z.ai/guides/vlm/glm-5.3-flash.md` 原文 |
| A11 | 社区 llama-bench：GLM4.7-Flash Q8_0 **tg128 10.77 / d2048 5.28** vs qwen3moe-30B-A3B **12.95 / 11.23** | HF 讨论 `zai-org/GLM-4.7-Flash` #47（作者贴的 llama-bench 原始表） |
| A12 | 社区正面反馈："exceptional tool use handling in various typescript cli coders" | 同上 #53 |
| A13 | 社区负面反馈：破坏转义 `\n`、误删邻近代码（#75）；无限重复（#48） | 同上 #75 / #48 |
| A14 | whitecircle SFT：SWE-rebench-V2 pass@1 **0.3315 → 0.4165**，轮数 82.5 → **44**，每题成本 $0.0443 → **$0.0382** | `hf-mirror.com/whitecircle/GLM-4.7-Flash-Coder/raw/main/README.md` |
| A15 | `minimax-m3.1-flash` 在 ollama 上是 **`:cloud` 纯 API tag，428B 参数**，无本地权重 | `ollama.com/library/minimax-m3.1-flash` |
| A16 | ollama 上 `deepseek-v4-flash` = "No models have been pushed" | `ollama.com/library/deepseek-v4-flash` |
| A17 | 字节 **Seed-Coder-8B 是官方开源权重**（Base/Instruct/Reasoning，MIT，ctx 32K/64K） | `hf-mirror.com/ByteDance-Seed/Seed-Coder-8B-Instruct/raw/main/README.md` |
| A18 | 百川 **Baichuan-M2-32B 是医疗模型**（Qwen2.5-32B 全参微调，HealthBench 60.1） | `hf-mirror.com/baichuan-inc/Baichuan-M2-32B/raw/main/README.md` |
| A19 | 商汤 author 下**只有检测/分割/3D 模型，无 LLM 权重** | `hf-mirror.com/api/models?author=SenseTime` |
| A20 | 百度 2026 年**没有新的 ERNIE 开源 LLM**（只有 OCR/VL/图像） | `hf-mirror.com/api/models?author=baidu`（按 lastModified 排序） |

### 4.2 推断（本轮未实测，属于推理，落地前必须自己验）

| # | 推断 | 依据 | 置信度 |
|---|---|---|---|
| I1 | GLM-4.7-Flash 在我们的 V100S 上 decode 约 **80–120 tok/s**（短上下文），深度 8K+ 可能掉到 60–90 | ① 同 30B-A3B 档实测 110–136（姊妹笔记）② A11 显示它比同档 Qwen3MoE 慢 17%–53% | 中 |
| I2 | 若它的输出 token 数比现役多 1.5–2×，则**单题墙钟可能不降反升** | reasoning 不可关（#56）+ 官方评测 max_new_tokens 16384 vs 现役 non-thinking | 中高（这正是要实测的头号指标） |
| I3 | MLA 让 GLM-4.7-Flash 的 KV cache 极小 → 198K ctx 在 32GB 卡上可行 | config `kv_lora_rank=512`（A1） | 高 |
| I4 | "Q4_K_M ≈ 0.30 × B16" 的换算误差 ±5% | 3 组真值校准（见 §0） | 高 |
| I5 | Ling-3.0-flash-REAP288-71B-A5B（44.29 GB）在 V100 上 decode 约 **70–90 tok/s**（5B 激活） | 激活比 3B 多 1.7×，按 110–136 × 3/5 折算 | 中 |
| I6 | 全部"必须 CPU 卸载"的候选（Step/Kimi/DeepSeek/GLM 大版/MiniMax M2.7）在 V100 上会塌到个位数 tok/s | 姊妹笔记实测（235B 全 CPU → 2.13–3.48 tok/s） | 高（引自姊妹笔记实测） |
| I7 | 32GB 卡上 GLM-4.7-Flash 的 Q8_0（31.84 GB）**放不下**（还要 KV + CUDA context），Q4_K_M 是唯一合理档 | 体积 + KV | 高 |

---

## 5. 未找到公开证据（明确登记，避免被"想当然"填坑）

1. **GLM-4.7-Flash 在 V100（任何型号）上的 tok/s 实测** —— 未找到。本轮唯一社区速度点是 5090D/3060 与一张 AMD llama-bench 表。
2. **GLM-4.7-Flash 的 SWE-bench Verified 第三方独立复现** —— 未找到。已知的第三方只有 whitecircle 的 **SWE-rebench-V2**（不是 SWE-bench Verified，两者不能互比）。
3. **GLM-4.7-Flash 的 Terminal-Bench 分数** —— 官方模型卡对比表里**没有** TB2 数字（只有 SWE-V / τ²-Bench / BrowseComp / AIME / GPQA / LCB v6 / HLE）。GLM-4.7 大版的 TB2 = 41%，Flash 档未知。
4. **GLM-4.7-Flash 的 InjecAgent 类（提示注入 / 越权）成绩** —— 未找到公开数据。官方给的是 BrowseComp 42.8（检索类工具调用）。
5. **DeepSeek-V4-Flash 在 llama.cpp 上的可用性细节**（哪些算子有 sm_70 kernel、DSA 稀疏注意力在 llama.cpp 里的实现状态）—— 未找到明确文档；只确认 unsloth 发了 GGUF。
6. **MiniMax-H3 的参数与权重体积** —— HF `config.json` 404，未取得。
7. **Step-5-Preview 的具体参数量与 Q4 体积** —— 官方只发 NVFP4（Blackwell 格式），其余未取得。
8. **百川 M3-235B 的官方 agentic 分数** —— 未取得（只拿到官方 GGUF 与体积）。
9. **腾讯 Hy3 / Hy4-preview / Hunyuan-A13B 的官方 agentic 分数** —— 未取得。
10. **书生 Intern-S2-397B 的 agentic 分数** —— 未取得。
11. **商汤是否有"不叫 SenseTime author"的 LLM 开源权重** —— 本轮未找到任何公开证据（不能断言不存在，只能说未找到）。
12. **智谱清言**（消费端 App）—— 与 GLM 开源权重无关，登记为"非本轮范围"。

---

## 6. 对我们的具体建议（落到 anolis-gpu-01 的操作手册）

### 6.1 结论性建议

- **主线候选换成 `glm-4.7-flash`（Q4_K_M，单卡）**，与现役做 A/B：它是本轮唯一"官方 agentic 分更高 + 激活参数相同 + 权重体积相同"的国产模型，部署风险与现役等价（同一个 ollama runner、同一张卡、同样 18–19 GB）。
- **不要**把任何 300B+ 的国产模型列入本地方案：它们在 V100 上只能 CPU 卸载，实测会掉到个位数 tok/s（引自姊妹笔记实测），且 GLM-4.7 已被智谱在 ollama 上 retire，说明国产大模型的 ollama 供给策略不稳定。
- **第二张 V100S 继续空转**（现役 18.5 GB 模型本来也只落 1 张卡），不要为了"双卡"去选 45–60 GB 的模型——那会把墙钟打回原形。

### 6.2 具体安装步骤（可直接执行）

```bash
# 0) 前置检查（只读）
#    - 确认 GPU 空闲：nvidia-smi
#    - 确认 ollama 版本：ollama --version   # 需 >= 0.14.3（模型卡要求），我们是 0.40.6
#    - 确认磁盘：df -h /data   # 19GB 权重 + KV 落盘，必要时按运营者授权扩容

# 1) 拉取（不要走 ollama.com 以外的镜像：gguf 已在 ollama registry 里打包好）
ollama pull glm-4.7-flash:q4_K_M     # 19GB，198K ctx

# 2) 起服务（保持与现役一致的并发设置）
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_KEEP_ALIVE=30m
ollama serve

# 3) 冒烟（必做 4 项，缺一不可）
#    3.1 加载与 GPU 生效：ollama ps  → 应显示 100% GPU、18.6/19GB 落在 1 张 V100S
#    3.2 输出不乱码：发一个 200 字的中文+代码混合请求，肉眼检查是否有 mojibake
#        （前期结论提到的 ggml-org/llama.cpp#17067 类问题虽已关闭，但 GLM-4.7-Flash 是新架构，仍须自验）
#    3.3 tool calling：发一个带 tools 的请求，确认模型吐出合法的 tool_call（GLM 4.7 用 glm47 模板）
#    3.4 多轮不崩：连打 3 轮含工具回显的对话，确认不出现无限重复（社区 #48 报告过）

# 4) 速度基线（与现役同口径：num_ctx 8192、单请求）
#    现役记录值：decode 135.7 tok/s、prompt 149.1 tok/s、加载 10.5s
#    → 记录 glm-4.7-flash 的同口径数值；若 decode < 100 tok/s，需要在决策时把墙钟算进去

# 5) af-bench A/B（这是决策依据，不是分数）
#    - 固定同一批题、同一 harness（SWE-bench Verified / Terminal-Bench / InjecAgent / τ²-bench）
#    - 同时记录：解题率、每题输出 token 数、每题墙钟、工具调用轮数
#    - 判据：解题率显著高于现役 且 每题墙钟 ≤ 现役 × 1.1  → 才替换
```

### 6.3 需要改的配置（与现役的差异点）

| 项 | 现役 | glm-4.7-flash | 说明 |
|---|---|---|---|
| 模型名 | `qwen3-coder-30b` | `glm-4.7-flash:q4_K_M` | 换 model 名即可 |
| num_ctx | 8192 | **建议先用 16384 试**（agent 10 轮会涨上下文） | 上下文变深时 decode 会降（社区 #47 d2048 掉一半），需实测后定 |
| KV 量化 | 不要开 | **不要开** | 姊妹笔记实测：V100 上 KV 量化会静默退 CPU；且社区 #48 报告 FP8 KV + FlashMLA 会导致重复循环 |
| flash_attn | 不用 | **不用** | V100 无 FA2，FA 是哑开关 |
| 思考模式 | 无（Instruct 版） | **默认开且难以关** | 需在 af-bench 端解析 `<think>` 段并把它计入 token 预算；尝试 jinja `{% set enable_thinking = false %}`，但官方不支持关思考 |
| 工具模板 | qwen3-coder 模板 | GLM4.7 模板（ollama 自带） | af-bench 的 tool-call 解析器要按 GLM 格式适配（`glm47` parser 的输出形态） |
| 第二张卡 | 空转 | 仍空转 | 两版同构 |

### 6.4 备选与探针（按优先级）

1. **探针 P1：`whitecircle/GLM-4.7-Flash-Coder`（18.13 GB Q4_K_M，社区 GGUF `ngquocvinh/GLM-4.7-Flash-Coder-GGUF`）**
   - 价值：作者自测**轮数 -45%**、每题成本 -14%、SWE-rebench-V2 pass@1 +25.6% —— 正好打我们的"单题墙钟"痛点。
   - 装法（因为没有 ollama 官方 tag，只能走 GGUF 导入）：
     ```bash
     # 下载 GGUF（走 hf-mirror，实测可达）
     curl -L -o glm47fc.gguf \
       "https://hf-mirror.com/ngquocvinh/GLM-4.7-Flash-Coder-GGUF/resolve/main/GLM-4.7-Flash-Coder-Q4_K_M.gguf"
     ollama create glm47fc -f glm47fc.gguf      # ollama 支持从 GGUF 文件建模型
     ```
   - 注意：下载走 hf-mirror 是本轮实测可达的通道（huggingface.co 直连超时）。
2. **探针 P2：`Ling-3.0-flash-REAP288-71B-A5B` Q4_K_M（44.29 GB，社区）** —— 44.29/64 GB 可双卡放下，AA Index 20（高于现役 10），但 **5B 激活 → 解码慢约 1.7×** 且 REAP 是有损压缩。属于"上限探针"，不是主链路。
3. **降级保底**：保留 `qwen3-coder-30b`（现役）。GLM-4.7-Flash 一旦在 af-bench 上翻车（重复循环 / 工具调用不解析 / 墙钟更慢），立即回退。

### 6.5 一句话给决策者

> 国产阵营在 2026 年整体向 300B–780B 超大 MoE 演进，**这批模型在 2×V100S-32GB 上是"能看不能跑"**（Q4 真值 111–470 GB，而 CPU 卸载实测塌到 2–4 tok/s）。唯一落在"19 GB 单卡、3B 激活、官方 SWE-V 59.2 / τ²-Bench 79.5"的甜点的是 **智谱 GLM-4.7-Flash（MIT）**；它值得一次装机 + af-bench A/B，但**不能只看分数**：必须同时量"每题输出 token 数与墙钟"，因为它是 reasoning 模型、思考关不掉，而现役是 non-thinking。

---

## 7. 引用清单（全部本轮实际访问）

- 模型卡/配置：`hf-mirror.com/zai-org/GLM-4.7-Flash/raw/main/{README.md,config.json}`；`hf-mirror.com/whitecircle/GLM-4.7-Flash-Coder/raw/main/README.md`；`hf-mirror.com/inclusionAI/Ling-2.6-flash/raw/main/README.md`；`hf-mirror.com/ByteDance-Seed/Seed-Coder-8B-Instruct/raw/main/README.md`；`hf-mirror.com/baichuan-inc/Baichuan-M2-32B/raw/main/README.md`；`hf-mirror.com/baidu/ERNIE-4.5-21B-A3B-PT/raw/main/README.md`；`hf-mirror.com/moonshotai/Kimi-Linear-48B-A3B-Instruct/raw/main/README.md`；`hf-mirror.com/deepseek-ai/DeepSeek-V4-Flash/raw/main/config.json`
- 体积：`hf-mirror.com/api/models/<id>/tree/main?recursive=1`（`ggml-org/GLM-5.3-Flash-GGUF`、`ggml-org/GLM-4.5-Air-GGUF`、`stepfun-ai/Step-3.5-Flash-GGUF-Q4_K_S`、`stepfun-ai/Step-3.7-Flash-GGUF`、`unsloth/GLM-4.7-Flash-GGUF`、`unsloth/GLM-4.7-Flash-REAP-23B-A3B-GGUF`、`unsloth/DeepSeek-V4-Flash-GGUF`、`ngquocvinh/GLM-4.7-Flash-Coder-GGUF`、`tencent/Hy-MT2-30B-A3B-GGUF`、`bloomer010/Ling-3.0-flash-REAP288-71B-A5B-GGUF`）；`hf-mirror.com/api/models/<id>?blobs=true`（B16 求和）
- 官方文档：`docs.z.ai/guides/llm/glm-4.7.md`、`docs.z.ai/guides/vlm/glm-5.3-flash.md`、`docs.z.ai/guides/llm/glm-5.3.md`、`docs.z.ai/llms.txt`
- ollama 库：`ollama.com/library/{glm-4.7-flash,minimax-m3.1-flash,deepseek-v4-flash}`
- 第三方分数与速度：`artificialanalysis.ai/models/{glm-4-7-flash,qwen3-coder-30b-a3b-instruct,glm-4-5-air,glm-4-7,glm-5-3,glm-5-3-flash,step-3-5-flash,step-3-7-flash,ling-2-6-flash,ling-3-0-flash,ling-3-1-flash,minimax-m2,minimax-m3,deepseek-v4-flash,deepseek-v3-2,kimi-k2-6,kimi-k2-7-code,kimi-k3,kimi-linear-48b-a3b-instruct}`
- 社区讨论（HF discussions API）：`zai-org/GLM-4.7-Flash` #47（llama-bench 表）、#48（重复循环）、#53（工具调用好评）、#56（关思考）、#75（破坏代码）
- llama.cpp 侧：`raw.githubusercontent.com/ggml-org/llama.cpp/master/src/llama-arch.cpp`（`LLM_ARCH_GLM4_MOE` / `LLM_ARCH_GLM5_NEXT` / `LLM_ARCH_GLM_DSA` 存在）；`hf-mirror.com/ggml-org/GLM-4.7-Flash-GGUF`（llama.cpp 官方 org 发布，2026-01-23）
- 同工作区姊妹笔记（**非本轮实测**）：`调研/本地模型选型/notes/v100-speed-data.md`、`chinese-community.md`、`qwen-family.md`、`quant-ecosystem.md`
