# 模型情报调研：按任务难度选模型 + token 预算数据底座

- **查询日期**：2026-10-19（所有数据均为当日查询）
- **用途**：为 agent 黑灯工厂的"harness 必须超过的基础表现"基线、模型采购与弱强路由提供数据支撑
- **数据来源约定**：每个数字后括注来源 URL。未经本人复现的第三方数字均标注"转引"。查不到的如实标注"未查到"。
- **重要口径说明**：
  - Artificial Analysis（下称 AA）当前 Intelligence Index 版本为 **v4.3.2**（10 项基准合成，含 Terminal-Bench 4.0、SciCode、HLE、AA-LCR 等），**已无独立的"Coding Index"单列分数**，编码能力以 Terminal-Bench 4.0 / SciCode 等并入主指数（来源：https://artificialanalysis.ai/evaluations/artificial-analysis-intelligence-index ）。
  - AA 价格除特别注明外为 **blended 价**（7:2:1 缓存命中:输入:输出 加权，$/1M tokens）。
  - 同一模型在不同 AA 页面（模型页 vs 厂商页 vs 对比页）可能对应**不同指数版本**，出现分数不一致时两条都记录并标注。

---

## 一、Artificial Analysis 基线分（2026-10-19 查询）

### 1.1 中国厂商模型（开放权重为主）

| 模型 | AA Intelligence Index | 价格（$/1M） | 速度 | 上下文 | 备注/来源 |
|---|---|---|---|---|---|
| **GLM-5.3 (max)** | **45**（厂商页） | blended $0.90 | 77 t/s | 1M | 开放权重；AA 厂商页 https://artificialanalysis.ai/providers/zai |
| **GLM-5.3-Flash** | **42** | blended **$0.10** | 69 t/s | 1M | 同上；旗舰 1/10 价 |
| GLM-5.2 (max) | 34 | blended $0.90 | 86 t/s | 1M | 同上 |
| GLM-5 (Reasoning) | 28（v4.3.2，#25/121） | $1.00 入 / $3.20 出，缓存 8 折，blended $0.66 | 78.7 t/s | 200k | 744B/40B MoE，MIT；已标 deprecated；模型页 https://artificialanalysis.ai/models/glm-5 |
| **Kimi K3 (Max)** | **44**（模型页 #5/121）；上市报道 57（不同指数版本，两条并存） | **$3.00 入 / $15.00 出**，缓存命中 9 折，blended $2.31 | **42.1 t/s**（偏慢，#69/79） | 1M | 2.8T/104B MoE；Kimi K3 License；模型页 https://artificialanalysis.ai/models/kimi-k3 ；上市分 https://www.linkedin.com/pulse/kimi-k3-launches-57-artificial-analysis-intelligence-clwlc |
| Kimi K2.7-Code | 未查到 AA 单页分 | OR: $0.671/$3.35 | — | 262k | OpenRouter 挂牌 https://openrouter.ai/moonshotai/kimi-k2.7-code |
| **MiniMax-M3** | **29** | **$0.30 入 / $1.20 出**，blended $0.22 | ~110–122.7 t/s（同价位快） | 1M | 对比页 https://artificialanalysis.ai/models/comparisons/kimi-k3-vs-minimax-m3 ；Terminal-Bench 4.0 仅 2%、SciCode 47%（同页） |
| **Step 5 Preview** | **44**（与 Kimi K3 max 同档） | blended $0.54；约 **$0.71/task**（≈Kimi K3 的 1/2.8） | 91–93 t/s | 1M | 600B/27B MoE，开放权重；厂商页 https://artificialanalysis.ai/providers/stepfun ；https://x.com/ArtificialAnlys/status/2102213621963243704 （转引） |
| Step 3.7 Flash | 19 | blended $0.18 | 212–224 t/s | 256k | 同上厂商页 |
| Step 3.5 Flash | 17 | blended $0.06 | 130–144 t/s | 256k | 同上厂商页 |
| **DeepSeek V4.1 Flash (max)** | **45**（AA 模型总览页 open-weights 前三）/ **39**（厂商页表，版本差异两条并存） | blended $0.27 | 176 t/s | 1M | 厂商页 https://artificialanalysis.ai/providers/deepseek ；总览页 https://artificialanalysis.ai |
| DeepSeek V4 Pro 0813 (max) | 36 | blended $0.67 | 79 t/s | 1.05M | 同上 |
| **DeepSeek V3.2 (Reasoning)** | 21（v4.3.2 估算）；另有第三方转引"66、开源第 2"（新指数版本，未经 AA 页面直接确认） | $0.28 入 / $0.42 出，blended $0.108 | 112 t/s | 128k | 685B/37B，MIT；对比页 https://artificialanalysis.ai/models/comparisons/deepseek-v3-2-reasoning-vs-qwen3-coder-480b-a35b-instruct ；"66"转引自 https://www.linkedin.com/pulse/deepseek-v32-2-most-intelligent-open-weights-model-qnwoc |
| DeepSeek R1（R 系） | AA 现行页**已无 R 系条目**（推理线由 V3.2/V4.x Reasoning 承担） | — | — | — | 厂商页说明 https://artificialanalysis.ai/providers/deepseek |
| **Qwen3.8 Max (0902)** | **45**（阿里系最高） | ~$1.2/task blended | 38 t/s | 984k | 创作者页 https://artificialanalysis.ai/models/creators/alibaba |
| Qwen3.8-Flash-Next | 40 | blended $0.1 | 52 t/s | 256k | 同上 |
| Qwen3.6 Plus | 27 | blended $0.4 | 56 t/s | 1M | 同上 |
| **Qwen3-Coder 480B A35B** | **12** | $0.30 入 / $1.80 出 | —（另处 112 t/s） | 262k | 非推理；Apache 2.0；对比页见 DeepSeek V3.2 行；SciCode 46%、HLE 5% |
| Qwen3-Coder 30B A3B | 10 | blended $0.2 | 158 t/s | 262k | 同上创作者页 |
| Qwen3-Coder Next (80B A3B) | 9 | blended $0.4 | 94 t/s | 256k | 同上；自报 SWE-V 70.6%（见第四节） |

### 1.2 海外闭源模型

| 模型 | AA Intelligence Index | blended $/1M | 速度 | 上下文 | 来源 |
|---|---|---|---|---|---|
| **Claude Opus 5.5 (max, w/ fallback)** | **58**（全榜第 1/706） | $5.98（≈$5.98/task） | 97 t/s | 1M | 厂商页 https://artificialanalysis.ai/providers/anthropic |
| Claude Opus 5.5 (xhigh) | 56 | $3.46 | 89 t/s | 1M | 同上 |
| Claude Opus 5.5 (high) | 54 | $1.82 | 83 t/s | 1M | 同上 |
| **Claude Sonnet 5.5 (max)** | **56** | $5.46 | **143 t/s** | 1M | 同上 |
| Claude Sonnet 5.5 (high) | 47 | $0.88 | 110 t/s | 1M | 同上 |
| Claude Opus 5 (max) | 51 | $5.86 | 60 t/s | 1M | 同上 |
| Claude Opus 5 (high) | 48 | $3.61 | 55 t/s | 1M | 同上 |
| Claude Sonnet 5 (high) | 32 | $1.79 | 74 t/s | 1M | 同上（注：有第三方转引 Sonnet 5 = 53 全榜 #5，与 AA 厂商页直接抓取值 32–38 不一致，以直接抓取为准；转引 https://www.linkedin.com/pulse/claude-sonnet-5-achieves-53-artificial-analysis-intelligence-28sbc ） |
| Claude Opus 4.5 (Reasoning) | 29 | 未显示 | 63 t/s | 200k | 同上 |
| Claude 4.5 Sonnet (Reasoning) | 21 | $0.56 | 51 t/s | 1M | 同上 |
| **GPT-5.5 (high)** | **37** | $1.54（blended）；**单价 $5.00 入 / $30.00 出** | 91–98 t/s | 922k–1.05M | 对比页 https://artificialanalysis.ai/models/comparisons/gpt-5-5-high-vs-gemini-3-pro ；厂商表 https://artificialanalysis.ai/providers/openai |
| GPT-5.5 (xhigh) | 38 | $2.63 | 99 t/s | 1.05M | 同上厂商表 |
| GPT-5.6 Sol (max) | 47 | $1.99 | 91 t/s | 1M | 同上 |
| GPT-5.6 Terra (max) | 42 | $1.40 | 136 t/s | 1M | 同上 |
| GPT-5.6 Luna (max) | 37 | $0.18 | 129 t/s | 1M | 同上 |
| GPT-5.3 Codex (xhigh) | 33 | 未显示 | 99 t/s | 400k | 同上 |
| GPT-5.4 (xhigh) | 39 | 未显示 | 99 t/s | 1.05M | 同上 |
| GPT-5.2 (xhigh) | 30 | 未显示 | 78 t/s | 400k | 同上 |
| GPT-5.1 (high) | 25 | 未显示 | 113 t/s | 400k | 同上 |
| GPT-5 (high) | 23 | 未显示 | 104 t/s | 400k | 同上 |
| （更上层）GPT-6 Astra (max) | 53 | $3.26 | 57 t/s | 1M | 同上 |
| （更上层）GPT-6.1 Sol (max) | 52 | $0.72 | 66 t/s | 1M | 同上 |
| **Gemini 4 Argon (high)** | **53**（Google 系最高） | $1.99 | 85 t/s | 1M | 厂商页 https://artificialanalysis.ai/providers/google |
| Gemini 3.8 Flash (high) | 41 | $1.24 | 147 t/s | 1M | 同上 |
| Gemini 3.7 Flash (high) | 39 | $0.93 | 280 t/s | 1M | 同上 |
| Gemini 3.1 Pro Preview | 30 | $1.30–1.31 | 97–139 t/s | 1M | 同上 |
| **Gemini 3 Pro Preview (high)** | **28**（估算） | blended $1.74；**单价 $2.00 入 / $12.00 出** | 未显示 | 1M | 对比页 https://artificialanalysis.ai/models/comparisons/gpt-5-5-high-vs-gemini-3-pro |
| Gemini 3 Flash | 26（估算） | 未显示 | 204 t/s | 1M | 厂商页 |
| Gemini 2.5 Pro | 16 | $0.33 | 113–119 t/s | 1M | 同上 |
| Gemini 2.5 Flash | 13（估算） | 未显示 | 197–212 t/s | 1M | 同上 |

### 1.3 harness 基线结论

- 开放权重天花板已到 **45 分**（GLM-5.3 / DeepSeek V4.1 Flash / Qwen3.8 Max 0902 并列），与 Claude Opus 5.5（58）差约 13 分，与 Sonnet 5.5（56）差约 11 分。
- **性价比拐点非常清晰**：GLM-5.3-Flash 用 **1/9 的价格**拿到旗舰 93% 的智能分（42 vs 45），且独立复现的 SWE-bench Verified 达 92%（见第三节）——这应作为 harness 弱模型档的默认基线。
- Kimi K3 智能分高但 **速度仅 42 t/s**（中位数 77.9），长任务时延成本需计入预算模型。
- 编码子项参考（AA 对比页直接抓取）：Kimi K3 Terminal-Bench 4.0 = 13%、SciCode = 59%；MiniMax-M3 = 2% / 47%；Qwen3-Coder 480B SciCode = 46%、HLE = 5%。GLM-5.3 官方自报 Terminal-Bench 2.1 = 88.2（https://z.ai/blog/glm-5.3 ，自报口径）。

---

## 二、API 官方实际价格核实（以官网/官方文档为准）

### 2.1 智谱 BigModel（https://open.bigmodel.cn/pricing ；页面为 JS 渲染，curl 无法直读，价格经多来源交叉核实，2026-10-19 查询）

| 模型 | 输入 | 缓存命中 | 输出 | 单位 |
|---|---|---|---|---|
| GLM-5.3 | ¥8 | ¥2 | ¥28 | /1M tokens |
| GLM-5.3-Flash（原价） | ¥0.8 | ¥0.115 | ¥2.8 | /1M tokens |
| GLM-5.3-Flash（发布 5 折，**2026-09-09 24:00 已结束**） | ¥0.4 | — | ¥1.4 | /1M tokens |
| GLM-5.3-FlashX | 约旗舰 1/4 | — | 不到旗舰三成（≈200 t/s） | /1M tokens |

- 来源：定价页 https://open.bigmodel.cn/pricing ；交叉核实 https://x.com/linyiq/status/2092745214566023459 （转引）、https://www.datacamp.com/zh/blog/glm-5-3-flash （转引）、官方套餐文档 https://docs.bigmodel.cn/cn/coding-plan/overview 。
- 海外 Z.ai 站 GLM-5.3-Flash：$0.15 入 / $0.50 出（转引同上）。
- 注意：OpenRouter 上 `z-ai/glm-5.3-flash` 挂牌低至 **$0.048/$0.16**、`z-ai/glm-5.3` 低至 **$0.079/$1.4**（第三方供应商价，2026-10-19 查 OpenRouter API `/api/v1/models`），显著低于国内直连，聚合渠道值得纳入比价。

### 2.2 MiniMax（https://platform.minimaxi.com / https://platform.minimax.io ）

| 模型 | 输入 | 缓存 | 输出 | 备注 |
|---|---|---|---|---|
| MiniMax-M3（国内） | ¥2.10 | ¥0.42 | ¥8.40 | /1M tokens |
| MiniMax-M3（国际） | $0.30 | — | $1.20 | 请求 >512K tokens 时价格翻倍 |
| **MiniMax-M3.1-Flash**（2026-10-19 当日正式发布） | **¥1** | ¥0.1（缓存读） | **¥4** | 200+ TPS（P50 170+）；已上线 MiniMax API / M Plan / MiniMax Code |

- 来源：M3 国际价与 AA/OpenRouter 一致（https://openrouter.ai/minimax/minimax-m3 ）；M3.1-Flash 定价见搜狐科技报道 https://m.sohu.com/a/1089825190_122014422 （2026-10-19，转引官方发布）；M Plan https://www.minimax.io/m-plan （订阅制，可配 Claude Code/Codex/Cursor）。
- 国内 M3 定价转引自搜索摘要（标注：未能在官方页面直接核对，采购前应在 platform.minimaxi.com 复核）。

### 2.3 阶跃星辰 StepFun（https://platform.stepfun.com/docs/zh/guides/pricing/details ）

| 模型 | 输入（缓存未命中） | 缓存命中 | 输出 |
|---|---|---|---|
| step-5-preview | $1.00（≈¥7） | $0.10（≈¥0.70；**2026-10-14 起由 ¥0.35 上调至 ¥0.70**） | $2.70（≈¥20） |
| step-3.7-flash | $0.20 | 未查到 | $1.15 |

- 来源：官方定价页（上述 URL）；调价公告 https://platform.stepfun.com/docs/zh/announcements/step-5-preview-price-adjustment （转引）。OpenRouter 同步 $1.0/$2.7 与 $0.2/$1.15（2026-10-19 查 API 实测）。

### 2.4 月之暗面 Kimi（https://platform.moonshot.cn ）

| 模型 | 输入 | 缓存命中 | 输出 |
|---|---|---|---|
| kimi-k3 | ¥20（≈$3） | ¥2 | ¥100（≈$15） |
| kimi-k3-256k | 分档计费（按请求输入 token 总量），**官方单独价目未查到**；第三方 pi.dev/TypingMind 显示 ctx 262k、最大输出 131k | — | — |

- 来源：https://www.moonshot.cn 与 HKET 报道 https://inews.hket.com/article/4162481/ （转引）、知乎汇总（转引）。AA 模型页同样记录 $3/$15、缓存 90% 折扣。
- OpenRouter 上 `moonshotai/kimi-k3` 挂牌出现 $0.239 入 / $11.936 出的第三方促销价与 $2.28/$11.40 的 batch 价（2026-10-19 查 API），说明聚合渠道价差极大。

### 2.5 阿里云百炼（https://help.aliyun.com/zh/model-studio/model-pricing ，华北2/北京地域，2026-10-19 直接抓取）

| 模型 | 输入 | 输出 | 单位 |
|---|---|---|---|
| qwen3.8-max（含思考/非思考，0–1M） | ¥12 | ¥36 | /1M tokens |
| qwen3.8-flash（0–1M） | ¥0.8 | ¥2.7 | /1M tokens |
| **qwen3-coder-flash**（阶梯计价） | ≤32K: ¥1；32–128K: ¥1.5；128–256K: ¥2.5；256K–1M: ¥5 | 对应档 ¥4 / ¥6 / ¥10 / ¥25 | /1M tokens |
| qwen3-vl-plus | ≤32K: ¥1；32–128K: ¥1.5；128–256K: ¥3 | ¥10 / ¥15 / ¥30 | /1M tokens |
| qwen3-coder-plus / qwen3-max | **未查到**——已不在当前价目表（被 qwen3.8 系列替代） | — | — |

- 阶梯规则：按单次请求输入 token 总量定档，整请求按该档单价结算；Batch 半价；上下文缓存仅输入侧折扣，两者不可叠加。海外（新加坡）更贵（coder-flash 国际版 0–32K 约 ¥2.202/¥11.009）。
- OpenRouter 参考：`qwen/qwen3.8-max-0902` $2/$6；`qwen3.8-flash` $0.15/$0.47；`qwen3-coder-flash` $0.195/$0.975；`qwen3-coder-next` $0.12/$0.80（2026-10-19 查 API）。

### 2.6 DeepSeek 官方（https://api-docs.deepseek.com/zh-cn/quick_start/pricing ，2026-10-19 直接抓取，**高峰/空闲双轨**）

| 模型 | 缓存命中（高峰/空闲） | 缓存未命中（高峰/空闲） | 输出（高峰/空闲） |
|---|---|---|---|
| deepseek-flash（V4.1-Flash-1017） | ¥0.04 / ¥0.02 | ¥2 / ¥1 | ¥8 / ¥4 |
| deepseek-v4-pro（V4-Pro-0813） | ¥0.30 / ¥0.15 | ¥9 / ¥4.5 | ¥27 / ¥13.5 |

- 高峰 = 周一至周五 9:00–12:00、14:00–18:00（北京时间，节假日除外）；空闲价 = 高峰一半。两模型均 1M 上下文、输出上限 384K。Search/Fetch API ¥5/千次（Harness 端工具调用 2026-11-01 起收费）。来源：官方定价页 + 更新日志 https://api-docs.deepseek.com/zh-cn/updates + V4-Pro 公告 https://api-docs.deepseek.com/zh-cn/news/news260813 。
- **产线含义**：空闲时段（晚间+周末）批量跑任务，成本直接减半——调度器可利用。

### 2.7 海外三巨头（OpenRouter 聚合挂牌价 + 官方口径，2026-10-19 查 OpenRouter API `/api/v1/models` 实测）

| 模型 | 输入 $/1M | 输出 $/1M | Batch 半价 | 备注 |
|---|---|---|---|---|
| Claude Opus 5.5 | $4.00 | $20.00 | 是 | 官方价（AA 记录 Opus 5 时代为 $5/$25） |
| Claude Sonnet 5.5 | $2.00 | $10.00 | 是 | — |
| Claude Opus 5 | $5.00 | $25.00 | 是 | 与 GPT-5.5 输入同价 |
| Claude Opus 4.5 | $5.00 | $25.00 | 是 | ctx 仅 200k |
| Claude Sonnet 5 | $2.00 | $10.00 | 是 | — |
| GPT-5.5 | $5.00 | $30.00 | 是 | pro 版 $30/$180 |
| GPT-5.6 Sol / Terra / Luna | $4/$2/$0.20 | $20/$12/$1.20 | 是 | 同代三档 |
| GPT-5.4 | $2.50 | $15.00 | 是 | mini $0.75/$4.5，nano $0.20/$1.25 |
| GPT-5.3 Codex | $1.75 | $14.00 | — | ctx 400k |
| GPT-5.2 / GPT-5.1 | $1.75/$1.25 | $14/$10 | 是 | — |
| GPT-5（初代） | $1.25（5.1 口径） | $10 | 是 | GPT-5-pro $15/$120 |
| Gemini 3.1 Pro Preview | $2.00 | $12.00 | 是 | — |
| Gemini 3 Pro（Preview） | $2.00 | $12.00 | — | 与 AA 对比页单价一致 |
| Gemini 2.5 Pro | $1.25 | $10.00 | 是 | — |

- 官方一手价交叉验证：GPT-5.5 $5/$30（AA 对比页）、Gemini 3 Pro $2/$12（AA 对比页）、Anthropic 系（AA 厂商页 blended 价反推一致）。

---

## 三、SWE-bench Verified 公开榜（自报 vs 第三方复现）

### 3.1 关键事实：榜单之间绝对值不可互比

- **官方 swebench.com**（自报提交、各用自家 harness）：Claude 4.5 Opus (high) + mini-SWE-agent = **76.80%**（约 $0.75/instance）；GPT-5 + Prometheus-v1.2.1 = 74.40%；Claude 4.5 Opus (medium) mini-SWE = 74.40%；GLM 5 (high) mini-SWE = 72.80%；榜首约 **79.2%**（Sonar Foundation Agent）。来源：https://www.swebench.com （2026-10-19 查询；表格为 JS 渲染，数字来自页面搜索快照与第三方汇总）。
- **Vals.ai 独立榜**（统一 mini-SWE-agent bash-only harness，**2026-09-01 起因饱和归档**）：头部达 93–97%，与官方榜差 15–20 个百分点——**harness 决定绝对值**。来源：https://www.vals.ai/benchmarks/swebench （2026-10-19 直接抓取全表）。

### 3.2 Vals.ai 独立复现表（%resolved / 每条成本，直接抓取节选）

| 模型 | resolve | $/instance |
|---|---|---|
| Claude Opus 5 | 97.00% | $1.29 |
| DeepSeek V4 Pro 0813 | 96.40% | **$0.10** |
| GPT-5.6 Sol | 96.20% | $1.15 |
| Grok 4.6 | 95.60% | $0.78 |
| GPT-5.6 Terra | 95.40% | $0.40 |
| **GLM 5.3** | **95.40%** | **$0.34** |
| Kimi K3 | 93.40% | $0.76 |
| GPT-5.6 Luna | 93.00% | **$0.04** |
| **GLM 5.3 Flash** | **92.00%** | **$0.02** |
| DeepSeek V4 Flash 0731 | 88.80% | **$0.01** |
| Claude Opus 4.8 | 88.60% | $1.92 |
| Qwen 3.8 27B | 86.00% | $1.08 |
| GLM 5.2 | 82.80% | $0.71 |
| GPT 5.5 | 82.60% | $1.36 |
| Claude Sonnet 5 | 79.60% | $1.49 |
| Gemini 3 Pro (11/25) | 76.40% | $0.77 |
| Kimi K2.7 Code | 78.20% | $0.27 |
| GPT 5.3 Codex | 78.00% | $0.46 |
| Gemini 3 Flash (12/25) | 75.00% | $0.28 |
| MiniMax-M3 | 75.00% | $0.42 |
| Gemini 3.1 Pro Preview | 78.80% | $0.78 |
| Gemini 3.8 Flash | 80.00% | $2.19 |
| GPT 5 | 69.00% | $0.27 |
| Gemini 2.5 Pro | 54.40% | $0.35 |
| GPT OSS 120B | 33.60% | $0.17 |

（完整 88 条见 https://www.vals.ai/benchmarks/swebench ；该页同时公开每条的输入/输出单价，是目前公开 $/task 数据最全的独立来源）

### 3.3 自报 vs 第三方差异（重点条目）

| 模型 | 官方自报 SWE-V | 第三方复现 | 差异说明 |
|---|---|---|---|
| Kimi K3 | 76.8%（官方博客，转引） | SemiAnalysis 独立 70.7%；Vals.ai（mini-SWE）93.4% | 自报高于独立复现约 6 分；Vals 高是 harness 不同 |
| DeepSeek V4 Pro | 80.6%（官方） | Vals 96.4%（mini-SWE） | 同上；另有 DeepSWE 口径 ~8% 的极端争议值（转引，未核实） |
| GLM-5 | 77.8%（开源公告） | Vals: GLM-5 71.4%、GLM-5.3 95.4% | 官方接近 mini-SWE 口径 |
| GLM-5.3 | 84.5%（官方文档，较 5.2 的 77.2% 提升；**该基准是否即 SWE-V 待确认**） | Vals 95.4% | — |
| MiniMax M3 | **未查到官方 SWE-V 自报**（官方博客主打 coding/agentic，见 https://www.minimax.io/blog/minimax-m3 ）；SWE-bench Pro 59%（benchlm.ai，转引） | Vals 75.0% / $0.42 | — |
| Qwen3-Coder-Next | 70.6%（自报） | AA II 仅 9（通用智能弱） | 专用编码模型典型形态：SWE-V 尚可、通用分低 |
| Claude Opus 4.5 | — | 官方榜 76.8%（mini-SWE，$0.75） | 官方榜与 Vals 跨代差异大 |

- **结论（预算建模用）**：不要跨榜比较绝对值；在同一 harness 内（Vals mini-SWE 一览表）做相对排序与 $/task 建模。GLM-5.3-Flash 的 **92% @ $0.02/task** 与 DeepSeek V4 Flash 的 88.8% @ $0.01/task 是目前公开的性价比极值。

---

## 四、采购建议素材：代码产线主力模型（2026 H2）

### 4.1 API 主力候选（按性价比排序，数据均见上文来源）

1. **GLM-5.3-Flash**（首选）：AA II 42（旗舰 93% 水平）、blended $0.10、1M ctx、开放权重；独立 SWE-V 92% @ $0.02/task。¥0.8/¥2.8 的刊例价在国内一线里最低档。
2. **GLM-5.3 (max)**（复杂任务档）：II 45 并列开源第一、blended $0.90、77 t/s、1M ctx；独立 SWE-V 95.4% @ $0.34。
3. **DeepSeek V4.1 Flash**（夜间批量档）：II 39–45、blended $0.27、176 t/s、1M ctx；空闲时段输出 ¥4/M 全场最低；V4 Flash 0731 独立 SWE-V 88.8% @ $0.01/task。
4. **MiniMax M3.1-Flash**（高速档）：¥1/¥4、200+ TPS、1M ctx；M3 独立 SWE-V 75% 说明其编码能力弱于 GLM/DeepSeek 同价位，适合作弱模型档而非主力。
5. **Step 5 Preview**（agentic 潜力档）：II 44、$1/$2.7、1M ctx、~$0.71/task；600B/27B MoE 开放权重，主打真实 agentic 任务（2026-09 发布，独立编码复现数据尚少）。

### 4.2 本地池 2×V100S-32GB（合计 64GB）能跑什么

- **Qwen3-Coder-30B-A3B 量化版：可行，推荐 Q4_K_M。**
  - Q4_K_M 权重约 **20.5GB**（30.5B 参数 MoE，激活仅 ~3.3B），单卡即可放下，双卡可扩 KV cache/上下文（来源：https://willitrunai.com/models/qwen-3-coder-30b-a3b ；Unsloth GGUF 全系量化 https://huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF ）。
  - Q8_0 约 32GB+，加上 KV cache 在 32GB 单卡上放不下；FP16（~61GB）需双卡且极紧。
  - **V100 架构限制（关键）**：Volta（SM 7.0）**无 BF16、无 FlashAttention**，vLLM 新版支持差；社区路径是 **llama.cpp + GGUF（Q4_K_M/Q5_K_M）**。已有该模型在老卡上输出乱码/GPU 未生效的 issue（https://github.com/ggml-org/llama.cpp/issues/17067 ），部署时需先跑冒烟测试。
  - 能力预期：AA II 仅 10、SWE 类通用智能弱，但 262k ctx + 158 t/s（AA 创作者页），适合做"第一遍草稿/批量重命名/模板化改写"这类低难度任务，不建议承担产线主链路。
- **Qwen3-Coder-Next（80B A3B，激活 ~3B）**：完整版约 46GB 统一内存，Q4 量化后双卡 64GB 可容纳；自报 SWE-V 70.6%，明显强于 30B 版（来源：https://www.morphllm.com/best-open-source-coding-model-2026 、https://huggingface.co/Qwen/Qwen3-Coder-Next ，自报口径）。同样受 V100 无 BF16/FA 限制，须 GGUF 路线，速度预期中等。
- **GPT-OSS-120B**：MXFP4 原生约 63GB，64GB 总显存理论上贴边，但 V100 不支持 MXFP4 加速、需反量化，实际大概率出 OOM 或速度不可用——**不建议**在此池部署。
- 结论语：本地池定位"弱模型档（分拣/草稿/工具调用重试）"，产线主力走 API。本地最强可行选项是 Qwen3-Coder-Next 80B Q4（双卡），保底选项是 Qwen3-Coder-30B-A3B Q4_K_M（单卡）。

### 4.3 成本速算参考（用于 token 预算模块）

- 一次典型 agentic 编码任务（输入 300K tokens + 输出 30K tokens，缓存命中 80% 输入）估算：
  - GLM-5.3-Flash：≈ 240K×¥0.0008 + 60K×¥0.000115×？ —— 刊例原价约 **¥0.28**；促销期约 ¥0.15
  - GLM-5.3：≈ 240K×¥0.008（缓存 ¥0.002）+ 30K×¥0.028 ≈ **¥2.8**（无缓存时 ¥3.2）
  - DeepSeek V4.1 Flash（空闲）：≈ 240K×¥0.00002 + 30K×¥0.004 ≈ **¥0.12**
  - Claude Sonnet 5.5：≈ 240K×$0.002 + 30K×$0.01 ≈ **$0.78**（约 ¥5.6）
  - Claude Opus 5.5：同口径 ≈ $1.56（约 ¥11.2）
  - （以上按 2026-10-19 价目手工计算，缓存折扣按各官网费率；实际以 harness 计量为准）
- Vals.ai 的 $/instance 直接可用作"每任务预算"先验：弱模型档 $0.01–0.05，中档 $0.3–0.8，旗舰档 $1.2–2.0。

---

## 五、强弱协作范式证据（2025–2026 实证，RouteLLM/FrugalGPT 之外）

可操作结论 5 条（每条附来源与数字）：

1. **升级信号不要用模型"自报置信度"，要用探针/困惑度/token 概率。**
   系统综述（arXiv 2603.04445，2026-04）实证：hidden-state 探针与困惑度法显著优于 verbalized confidence（模型口头报告的置信度与正确性一致性差）；小模型在**置信度最高的前 ~20% 查询**上与大模型打平——这 20% 可放心给弱模型。来源：https://arxiv.org/html/2603.04445v2
2. **省多少：75–85% 成本、保 95–97% 质量，是可复现的工程区间。**
   - MixLLM（NAACL 2025，contextual bandit 路由）：**97.25% 的 GPT-4 质量 @ 24.18% 成本**（省 ~75%）。来源：https://arxiv.org/abs/2502.18482
   - R2-Reasoner（GRPO 训练的路由）：**84.46% API 成本节省**且推理精度持平（转引自 2603.04445 综述）。
   - 工程侧经验值（tianpan.co，2025-11）：**~85% 查询路由到便宜模型，保 ~95% 前沿质量**。来源：https://tianpan.co/blog/2025/11/03/llm-routing-model-cascades
3. **生产模板：预路由 → 生成后验证器 → 阈值升级。**便宜模型先跑，输出经分解式校验（schema 校验/单元测试/评分器），低于置信阈值才升级强模型（NeuralTrust 2026 模式描述，https://neuraltrust.ai/blog/llm-model-routing ；agentpatterns.ai 的 Within-Task Model Cascade 同款，https://agentpatterns.ai/loop-engineering/within-task-model-cascade ）。AutoMix（arXiv 2310.12963）证明 few-shot 自验证 + POMDP 元验证器做升级判决，**每单位成本收益（IBC）最高提升 89%**。来源：https://arxiv.org/html/2310.12963v5
4. **代码场景的天然验证器是测试套件——cascade 在有测试的产线上风险最低。**测试可以捕获弱模型失败再升级（业界讨论共识，https://www.linkedin.com/posts/pjlucas_828-is-the-number-i-keep-coming-back-to-activity-7495973514252849152-MPNd ，转引）。CP-Router 用 conformal prediction 在 logits 上判决"普通模型 vs 推理模型"，是无需训练的升级判决替代品（转引自 2603.04445 综述）。
5. **cascade 有结构性安全/质量风险，必须做对抗压测与升级率监控。**arXiv 2605.17288（2026-05）：级联架构对对抗后缀攻击整体脆弱——准确率最高降 **84.6%**、token 成本被抬高 **148.9%**、时延 +108.9%、越狱成功率 +81.4%（弱前置模型更易被攻破）；即使无攻击，cascade 误差也可能严格高于最强单模型；防御手段（困惑度过滤、随机平滑）只有部分效果且误伤良性输入 ~46%。建议：升级判决模块要用校准过的（勿用轻量未校准分类器）、上线前跑对抗压测、生产监控异常升级率。来源：https://arxiv.org/html/2605.17288v1

其他可跟踪资源：Awesome LLM Routing & Cascading 清单 https://github.com/ymoslem/awesome-llm-routing-cascading ；RouterEval 基准（路由器可超过最好单模型——互补性收益，转引自 2603.04445）。

---

## 六、数据缺口（如实登记）

| 项目 | 状态 |
|---|---|
| AA "Coding Index" 独立分数 | **未查到**——v4.3.2 已并入主指数，无单列值 |
| qwen3-coder-plus / qwen3-max 阿里云现价 | **未查到**——已从价目表下线，被 qwen3.8 系列替代 |
| kimi-k3-256k 官方独立价目 | **未查到**——按请求输入量分档计费，官方页未给单价表 |
| MiniMax M3 官方 SWE-bench Verified 自报 | **未查到**（仅 SWE-bench Pro 59%，第三方转引） |
| MiniMax M3 国内价（¥2.1/¥8.4）官方页直接核对 | 未完成——官方页 JS 渲染，数字来自搜索快照转引 |
| GLM-5.3 大模型定价页直接核对 | 未完成——bigmodel.cn 为 SPA，数字来自多来源交叉（x.com 转引 + DataCamp 转引） |
| Step 3.7 Flash 缓存命中价 | **未查到** |
| swebench.com 官方榜完整 JSON | 未能获取（无公开静态 JSON 端点），条目来自页面快照 |
| DeepSeek V3.2 AA 分数 66 之说 | 未在 AA 页面直接确认，仅第三方 LinkedIn 转引，存疑 |

---

*报告生成：ZCode 网络调研，2026-10-19。所有"转引"数字建议在采购决策前于官网二次核对。*
