# harness 自研 Rust 化 · 阻碍分析（2026-10-19）

> 结论：**无阻断项，已开工**（grok h1 实例建 crates/af-harness）。本文是拍板版宪法第 4 条（统一 harness 内核）的实施前核查记录。

## 一、核心顾虑：自研 harness 还能否享受 ZCode 内专属优惠？

**能。优惠载体是 API key/账户订阅，不是客户端指纹。**

证据链：
1. ZCode 的供应商配置（`~/.zcode/v2/provider_config.json`）全部是标准 `api-key` 认证直连各供应商端点（stepfun `step_plan/v1`、kimi `api.kimi.com/coding/v1`、minimax、以及 gov 上 higress 的 100.64.0.6:8080 路由）——ZCode 自己没有做客户端证明（attestation）。
2. 智谱 BigModel Coding Plan 的 key 在 bao（`kv/company/LLM-upstream/Zhipu/zhipu-bigmodel-CodingPlan-1`），**直连实测通过**（2026-10-19：POST open.bigmodel.cn/api/paas/v4/chat/completions，usage 正常计量）。这与业界用法一致（Claude Code/Cline 等第三方客户端用同一 key 即享 Coding Plan 价）。
3. ZCode 侧的 entitlement 缓存（coding-plan-cache.json）只是入口引导，不构成请求级校验。

**因此**：自研 harness 直连同一批 key = 同一价格体系。零迁移成本。
备选过渡路径（记录在案）：harness 可把模型调用委托给 ZCode 工作流子代理（请求仍在 ZCode 运行时内发出）——过渡期内若供应商侧策略变化，随时切回。

## 二、其余核查项

| 核查点 | 结论 |
|---|---|
| 协议面 | 两种协议适配即可覆盖现有供应商：openai-chat-completions（bigmodel/kimi/step）+ anthropic-messages（higress 路由）。均为公开文本协议。 |
| 密钥纪律 | harness 不读密钥库：key 由运营者注入，`key_ref` 引用名进 AgentSpec，明文不进结构体 Debug/日志（对齐 bao 纪律）。 |
| 内核预算 | harness 是宪法第 4 条既有机制的实现，不新增 26 件预算（不触发内核预算测试）。 |
| 工具协议 | 自研窄协议（名称+JSON Schema+副作用分类），副作用一律经 af-effect-gateway——默认拒绝外部依赖纪律下不引 MCP 运行时。 |
| 质量地基 | 今天已全齐：credential/meter/trace/stop/effect-gateway 持久化全绿，612+1 测试，七门。harness 是它们的总装层。 |
| 已知残余风险 | ① 供应商侧若未来加客户端校验则需回退备选路径（监测项）；② GLM CodingPlan 的速率限制形态未实测（首跑时观察）。 |

## 三、开工形态

- grok 实例 h1 建 `crates/af-harness`（四元组 AgentSpec + Run 循环 + 双协议适配器 + 五件内核件总装），质量门照旧（全绿+clippy 零新增+mock 测试+真机冒烟留 examples）。
- 合流后由本机跑真机冒烟（bigmodel CodingPlan key 直连，小额度验证）。
