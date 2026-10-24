# 状态 · minimax-design 与 LLM 网关（higress）

> **更新纪律**：路由/密钥/域名任何变化 → 更新本文 + 追加更新记录。token 到期前要主动续（海螺 JWT 有 exp）。

## 1. MiniMax Design 是什么

MiniMax（海螺）的**视频/图像生成 API**（hub.minimaxi.com），与文本模型 MiniMax-M3 系无关。这是未来"视频工件"产线可直接调用的生成能力。

## 2. 调用方法（保留资产，勿删）

higress（gov company-higress-1）上有三条 internal ingress 把内网路径代理到 MiniMax Design：

| 路由（内网） | 上游 | 配置文件（gov） |
|---|---|---|
| `/minimax-design/` | hub.minimaxi.com（rewrite /） | /opt/company/data/higress/ingresses/minimax-design-hub.internal.yaml |
| （短版） | 同上 | minimax-design-hub-short.internal.yaml |
| `/minimax-design-cloud/…` | minimax 云端 API | minimax-design-cloud.internal.yaml |

- 认证：ingress annotation `request-header-control-add` 注入海螺 **token**（JWT，含 exp，**到期需更新**——到期日用 `jq` 解 exp 或看 状态 更新记录）与 `device_id`、`version_code`；`request-header-control-update` 覆写 `x-api-key`/`anthropic-version`。
- 配置快照（含活 token，**勿外传**）：本工作区 `参考/higress-minimax-design/`（三条 ingress + mcpbridge-default.yaml，2026-10-19 快照）。
- 调用入口：higress 监听（tailnet `100.64.0.6:8080`；公网 `ai.hkmingdajiaoyu.com` 经 Caddy）。

## 3. 文本模型网关（同一 higress）

路由：llm-auto / main / plan / kimi / step-plan / qwen-u / **minimax**（文本）；插件：ai-proxy / key-auth / model-mapper / ai-statistics。消费方式参考旧平面：anolis 经 :8080 消费（key 经 key-auth；auto-router 8777 曾做三档 tiering，现处崩溃循环，处置见 30-遗产处置 批 3）。

## 4. 与新设计的关系

- Bifrost 是新选型的 LLM 网关（poc-bifrost 实测）；higress 保留价值=①minimax-design 生成 API 通道 ②现役文本网关过渡期可用。两者关系在波次 4 评估（是否并存/收编），**评估前不动 higress**。

## 更新记录

| 日期 | 身份 | 变化 | 验证 |
|---|---|---|---|
| 2026-10-19 | 主代理 | 建档：三条 ingress 定位+快照入 参考/；token 在快照内（exp 见 JWT payload） | ssh gov 实读配置 |
