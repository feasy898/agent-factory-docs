# 任务1 · 三机现状盘点 · 跨腿汇总报告（汇总人-GLM-5.3）

- **对象**：tailnet `edgenet` 三台机器 anolis-gpu-01（100.64.0.7）/ governance-machine（100.64.0.6，下文部分引文称 srv-1）/ hk-gateway（100.64.0.3）
- **输入**：三条模型族腿各自的总报告（每条腿内部均为"双人独立盘点 + 合并员仲裁"）：
  - [S] `step-router-v1/总报告.md`
  - [M] `MiniMax-M3.1-Flash/总报告.md`
  - [G] `GLM-5.3-Flash/总报告.md`
- **对照方案**：`/home/pan-ding/workspace/agent协作平面/agent协作体系.txt`（HarnessOS 方案）
- **汇总人复核**：[R] 2026-10-05T06:18–06:30 UTC（≈14:18–14:30 CST），从 pandev-comp（100.64.0.8）对三机做**只读** SSH 复核（全部命令与原始输出存 `/tmp/synth-t1/*.out`）。三腿盘点窗口为当日 04:40–05:30 UTC，本次复核紧随其后约 45–110 分钟。
- **标注规则**：三腿原文的【单方记录，未核实】【已仲裁】【已核实-单方】等证据强度标注一律保留、不升格；[R] 开头的条目为汇总人本次新实测，属新证据而非对腿报告的"核实升格"。[S] 的 anolis 部分仅有 A/B 双报告、未经合并仲裁（[S] 自述），其独有事实按未仲裁口径引用。

---

## 1. 执行摘要（只看这一页的 owner 必读 12 条）

1. **盘点前提修正**：governance-machine=治理面、anolis-gpu=开发机、hk-gateway=网关的"三机分工"**是任务设定而非方案原文**——[M] 已 grep 方案全文（机器名/内网 IP/公网 IP/srv-1 全部零命中），采信；三机角色实测与该设定吻合（见 §4 矩阵）。
2. **三机骨架真实在产**：gov=治理面（CloudCrane/jiuwen_glue 栈：15 容器 + 6 自建服务 + PG 治理库）、anolis=执行面（**已在产而非待开发**：jiuwenswarm+harness+PM/patrol 循环，GPU1 47% 被语音业务占）、hk=纯网络网关（agent 设施 0/15 项）。
3. **方案与实机的核心偏差**：§9.5 `harnessos/` 目录树三机零命中；实机以另一套 CloudCrane 命名体系承载同构治理语义（[G] 定性为"双实现风险，需 owner 架构级裁定"）。方案四大件（Jev 独立判别服务 / Memory 向量库 / OwnerGate 实体 / 生产 MQ 承载）**三机全部未建**。
4. **⚠️ 盘点窗口之后、本次复核之前（≈05:56–05:58 UTC）已发生一轮人工修复**，三腿报告描述的是修复前状态：(a) hk 的 gost 从 `*:1080`（公网无鉴权）重绑为 `100.64.0.3:1080`（仅 tailnet）+ 新增 logrotate 配置（[R] 单元文件 mtime 05:56:54、重启 05:56:55、logrotate 05:58:07 实测）；(b) gov 公网 22/8300/8310/8787 已被云安全组全部闭合（IPv4/IPv6 双栈，公网仅剩 80/443——[M] 盘点窗口内实测过公网 22 OPEN）。执行者未查明（三腿按铁律只读，不会是盘点腿；疑似 owner 看到首批发现后处置）。
5. **最大安全事件的终值**：hk gost 无鉴权 SOCKS5 滥用累计外部连接 **895,866 条**（占 95.9%，[R] 全文件统计），日志膨胀至 370.8MB / 约 125 万行；TOP 单一外部 IP 112,590 次。量级排序：[M]（05:13 时 449,632 条、外部 ~91.5%、"分钟级加速"——**方向与量级正确且最终被低估近 3 倍**）> [G]（约 8 万次——**低估约一个数量级**，但其 65→97M 是较早期快照，方向一致）> [S]（88MB——**完全漏掉滥用事实**）。
6. **hk 成功登录排查已完成**（[G] 的头号遗留项，[R] 本次完成）：Accepted 全量 174 次、**全部 publickey、零次密码成功**——无被爆破攻破的证据；但外部 IP `60.188.237.31` 的 10 次 publickey root 登录（10-01~10-02）与 `42.194.143.17` 的 1 次（10-05 03:45:12，本次开机后 19 秒）**三腿均未记录过**，是否 owner 本人需 owner 确认。
7. **anolis 凭据破口终裁**：git remote 明文 token **7 处**（[G] 数对、[M] 漏 6 处）：chenmai8 六仓 github（同一用户名 `feasy898`，大概率同一 PAT 复用）+ qw-arena2 一处 cnb——实际只需轮换 **2 个 token** 即可清零 7 处（[R] 逐仓 masked 复核确认）。
8. **patrol 跨机之谜解开**（[M]/[G] 都标记为"待解释"的时间吻合）：anolis patrol 的用例 PAT-01 本义就是"**回归套件可启动（ssh srv-1 权威副本）**"，`role-run.sh:57` 实测 `WS_SSH_TARGET=root@100.64.0.6`——patrol 每 2h（`17 */2`）经 SSH 在 gov 上驱动权威回归套件，gov 的 12:17 基线不是"手动跑"而是这一机制（[R] 证实）。
9. **gov 仍在恶化**：[R] 实测 load 15.60/8 核、ClickHouse 552%（高于三腿观测的 453–513%）、auto-router 崩溃计数 28,054（三腿 27,195→27,211，仍在涨）、planner LLM 通道故障从 401 降档演变为 **502 Bad Gateway**（[R] 14:05/14:16 CST 两条日志）。
10. **三台安全底盘同构性缺陷**：均无 fail2ban、均无主机防火墙（INPUT 全 ACCEPT）、均无 SWAP、gov/hk 的 SSH 均 root+password 开（gov 另有 root 7 把公钥、hk 6 把）；tailnet 网络 ACL 现为**全 mesh**（10-05 起新策略：网络全通 + Tailscale SSH 按 user 分层，策略文件自认"一把被盗的节点密钥=立即 root，无第二道门"——[R] 读到 policy.hujson 全文）。
11. **仍需 owner 处置的高危项**（未修复）：anolis 公网 22 爆破仍在进行（[R] 实测 24h journal 口径 22,496 条失败口令，≈[M] 的 70,600 条 audit 记录换算口径）；anolis `/data` 84%；gov factory-board 8300 对**任意 tailnet 节点无鉴权全量可读**（[R] 从非 gov 节点 GET `/api/state` 得 200 + 334,097 字节）且服务仍绑 0.0.0.0；部署双源漂移的运维窗 SYSTEM-GUIDE 记载 **≤2026-10-05（今天）到期**未闭环。
12. **三腿质量画像**（供后续任务路由参考）：[M] 最完整、事实密度最高（但也有漏计：chenmai8 token ×6、Temporal 第二 namespace、gov 僵尸进程父进程）；[G] 深度最好、多个独家高危发现（7 token、PM 空转热循环、8300 公网可达、exit node 零使用、双实现风险定性），但量级估算偶有失准（gost ~8 万次、hk github 25s 稳态）；[S] 覆盖面最浅（漏 gost 滥用、gov 过载、anolis 深层），其 anolis A/B 未合并仲裁，但贡献了 planner 停摆时间点（10-02 20:24Z，[R] 已证实）与 headscale 双用户线索。

---

## 2. 跨腿一致结论清单（至少两条腿独立得出；标注一致腿）

> 加 [R✓] 的表示本次汇总人复核进一步证实；[R+] 表示本次复核补充了新细节。

| # | 一致结论 | 一致腿 | 采信状态 |
|---|---|---|---|
| C1 | 三机 tailnet 互通正常（三机互 ping 0% 丢包；hk→anolis 走 DERP(hkg) 中继 ~70–157ms、直连未建立；其余多为直连） | [S][M][G] | [R✓] 本次从 pandev 直连三机 22 均通 |
| C2 | tailnet 控制面 = gov 上自托管 headscale v0.29.3（容器），三腿盘点当日 11:37 CST 被重建（hardened recreate）；tailnet 名 `edgenet` | [S][M][G] | [R+] headscale 现登记 **8 节点**（[G] 盘点时为 7+1 差集）；另存在第二个用户 `new-member`（10-05 03:36:52 UTC 创建，[S] 也记录了它），当前无节点 |
| C3 | 角色实测：gov=治理面成立（15 容器+6 自建服务+PG 治理库+headscale 控制面）；anolis=执行面而非开发机（jiuwenswarm/harness/PM/patrol 在产，GPU1 被 /data/xdng 语音栈 3 进程占 15516MiB≈47%）；hk=纯网络网关（agent 协作设施 0 项在运行） | [M][G]（[S] 隐含一致） | [R✓] GPU0=310MiB/GPU1=15516MiB/利用率 0% 逐字吻合 |
| C4 | 方案 §9.5 `harnessos/` 目录树三机零命中；实机以 CloudCrane（glue/temporal/higress/factory-*）命名体系落地，两套概念需人工映射/架构裁定 | [S][M][G] | — |
| C5 | 方案四大件未建：Jev 独立判别服务（三机均无；生产替代是百炼通用模型 decision-model-preview 与 auto-router 代码路径）、Memory/向量库运行时（三机零向量库）、OwnerGate/HubAgent 实体（三机均无）、生产 MQ（gov Temporal 服务端在但**零 worker**、Kafka 无容器） | [S][M][G] | [R✓] established 到 :7233 仍为 0 |
| C6 | gov 治理数据层真实在产：`team_task` 38（COMPLETED 36/PENDING 1/BLOCKED 1）、`decision_record` 4、`guardrail_run` 12、`signal_inbox` 3、`challenge` 0、`artifact_route` 0 | [M][G]（[S] 给了其中一部分） | [R✓] 精确 count 全部吻合；[R+] 0 行表实测为 **9 张**（[G] 列的 6 张 + `promotion_transition`/`promotion_eval_event`/`capability_metric_event`） |
| C7 | 回归门禁在产且**红**：72 用例口径 = 49 pass / 5 fail / 18 skip，fail 由 4 升至 5，**违反方案 §10.4"fail 只降不升"铁律**；5 fail 明细（auto-router 编排层、微信通道 L3-05、双件齐 7/6、worklog 104h、归档通道 24h 零归档） | [M][G]（[S] 记录了门禁存在与基线产出但未给数字） | [R✓] /var/log/factory-tests 基线产物在 |
| C8 | gov auto-router"功能活着、编排层死"：8777 /health=200（v9.0-tiering），但 systemd 单元崩溃循环（根因 `Errno 98 Address already in use`——10-03 21:14 手工 nohup 孤儿进程 PID 3522460 占住端口顶替） | [S][M][G] | [R✓] PID/启动时间/命令行逐字吻合；[R+] NRestarts 已涨至 28,054（≈每 5–8 秒重启一次） |
| C9 | gov planner 的 LLM 通道故障在产：三腿窗口内为"网关档 decision HTTP 401 降档、任务挂起" | [S][M][G] | [R+] 已演变为 **502 Bad Gateway**（14:05/14:16 CST 两条"cycle 异常"日志）；[S] 独有的 decision_queue 积压 16 条、任务 #11/#22/#23/#26 review 超 SLA 未复核、不矛盾、保留 |
| C10 | anolis 执行面在产：jiuwenswarm-app（10-02 14:31 起，127.0.0.1:18092，/health 426 属纯 WS 正常）、patrol 每 2h、PM wake-gate/pm-loop 每 5min、3 个 OpenBao 续期 timer 在转、harness 8/8 模块导入成功 | [S][M][G] | [R✓] patrol 最新一轮 20261005T061701Z（本次复核期间刚跑） |
| C11 | anolis `/data` 数据盘 84%（234G/295G）接近满；GPU 为 2× Tesla V100S-32GB（sm_70，无 bf16/FA2） | [S][M][G] | [R✓] df 逐字吻合 |
| C12 | hk warp-reroute.service failed（根因链：本次开机 03:44:53 后 sing-box 03:45:10 FATAL bind 7864 地址未就绪→03:45:13 自愈→warp-reroute 恰在坏窗口执行且安全门拒装→failed，systemd 不再重试）→ 透明分流整体不生效 + 7863 公网可达；显式代理 7864 可用且 WARP 路径通 | [S][M][G] | [R✓] warp-reroute 仍 failed；[R✓] 7863 仍绑 0.0.0.0 |
| C13 | 三台均无 fail2ban、无主机防火墙（INPUT policy ACCEPT）、无 SWAP；gov/hk 的 sshd 均 PermitRootLogin yes + PasswordAuthentication yes | [S][M][G] | [R✓] rpm/ufw/sshd -T/swap 全部逐字吻合 |
| C14 | 短时凭据链是落实最好的组件：gov OpenBao 8200（healthy，经 Caddy 仅 tailnet 发布）+ vault-broker 8310 + anolis oneshot 现拉 tmpfs + 3 个 renew timer，执行面零长期密钥 | [S][M][G] | — （但被 anolis 7 处 git remote 明文 token 破口——见 §5 #6） |
| C15 | LLM 唯一入口 Higress 在 gov（tailnet :8080=200 + 公网 `ai.hkmingdajiaoyu.com/v1` 经 Caddy，DNS→159.75.21.149）；anolis 是唯一执行面消费方（MODEL_NAME=step-3.5-flash）；auto-router 8777 做三档 tiering | [S][M][G] | [R✓]（[R+] 159.75.21.149 经 ifconfig.me/api.ipify.org 双通道确认就是 gov 的公网 IPv4——闭掉 [G] 的未决项 #9） |
| C16 | Temporal 三机均未投产：gov 服务端 SERVING（7233/8081）但 worker 未注册（tctl 空/established=0）；anolis 的 qw_worker 进程存活但日志停于 10-02（历史=模拟提交试点）；hk 无 | [S][M][G] | [R✓]；[R+] namespace 实测 2 个（temporal-system + default——[G] 对、[M] 漏了 default，见 §3 D4） |
| C17 | MCP：仅 anolis 1 个在跑（agent-browser :8125，仅 tailnet 可达，健康端点未找到 404）+ 1 个备用未跑（coldstart fs_server.py）；gov/hk 无运行实例 | [S][M][G] | — |
| C18 | Skill 库：anolis 三处载体（.agent-skills 5 + /opt/gpumachine/skills 2 + handover 快照）但运行时未接入（skills_root=""、skill_retrieval disabled）；gov 3 个 workshop-skills 在用、SkillFS 未部署 | [S][M][G] | — |
| C19 | 沙箱：无 gVisor/VM 级隔离；anolis 为一次性容器形态（role-run.sh `docker run --rm role-base:23-ssh`，patrol 实证 materialize_done rc=0）+ CNB 远端适配器代码 | [S][M][G] | — |
| C20 | hk 两条结果回传通道（8090 upload_server.py / 9418 git-daemon）全关未运行；唯一代码资产 /srv/git/ohos-tailscale.git（bare 仓，812K，main@20beb2a）无 remote、外部无法拉取、无备份 | [M][G]（[S] 记录了 upload_server.py 未运行） | — |
| C21 | 遥测链在产：anolis otel-collector（Up 7d）→ gov :4317 → Langfuse/ClickHouse（events_core 40555 行持续增长） | [S][M][G] | — |
| C22 | gov 长期资源过载：8 核 load 13–19，主因 ClickHouse 常驻高 CPU；langfuse-web 内存 ~70% | [M][G]（[S] 漏掉过载） | [R✓] load 15.60、ClickHouse 552%；[R+] 三主因齐了：ClickHouse + console_tui 99.8% + minimax-code 95.9% |
| C23 | agent CLI 三机分化：gov 有（openclaw gateway + minimax-code 实例）；anolis/hk 零 CLI、零配置目录 | [S][M][G] | [R✓]（三方清单合并采信，见 §3 D5） |
| C24 | 待更新积压：gov ~96、anolis ~124–125、hk 123 | [M][G]（[S] 的三组数字均口径偏移，见 §3 D6/D8/D24） | [R✓] 本次复核 gov 97 / anolis 124 / hk 123 |
| C25 | gov 443 TLS 握手失败（回归 L0-12 按 skip 登记）；gov 公网 GitHub/Google 直连不通（境外须走代理，与 SYSTEM-GUIDE 记载一致） | [M][G] | [R✓]（443 本机 curl 000） |
| C26 | gov 部署双源漂移：实机 compose 生效源是 platform.git 克隆，真相源 company-ops 侧；SYSTEM-GUIDE 自述"真相源→实机走 PR 正向通道尚未建立"，且记载运维窗 ≤2026-10-05 | [M][G] | — |

---

## 3. 腿间矛盾与可信度判断（逐条：矛盾内容 | 各腿说法 | 采信判断）

> 每条均注明是否做了 [R] 只读复核及结果。未做复核的按证据强度裁决并说明理由。

### D1 anolis git remote 明文凭据数量：7 处 vs 1 处 —— 采信 [G]，[R] 已逐字证实
- [G]：**7 处**（chenmai8 六仓 github + qw-arena2 cnb），已打码呈现。
- [M]：**1 处**（qw-arena2 的 cnb remote，【已核实-单方】，建议改凭据助手并轮换）。
- [S]：未提及 token 问题（只记了 dubious ownership 仓）。
- **[R] 复核**（`find /opt/gpumachine /home/anuser -maxdepth 5 -name .git` + `git remote -v` masked）：**7 个仓**的 remote URL 内嵌 `用户名:token`——chenmai8 的 具身助餐机器人/repo、可玩的小游戏广告/factory、可玩的小游戏广告/repo、咖啡豆质检/repo、政务AI脱敏网关/repo、短剧多国出海/repo 共 6 个 github 仓（同一用户名 `feasy898`）+ projects/qw-arena2 的 cnb 仓。`git remote -v` 每条 remote 打 fetch/push 两行，共 14 行凭据 URL，与 7 仓自洽。
- **采信**：[G]。[M] 漏计的原因可解释：其枚举只到 projects 顶层仓，chenmai8 内嵌的 `*/repo`、`*/factory` 子目录仓未展开（呼应 D9 的口径差）。**修复含义**：实际泄露面是 **2 个 token**（一个 github PAT 复用于 6 处 + 一个 cnb token），轮换 2 个即可清零 7 处。

### D2 hk gost 滥用规模与"现状"：量级差一个数量级，且事件已被盘后修复截断
- [M]：449,632 条/138MB（05:13）→ 203MB、load 3.52（05:26）、外部 ~91.5%、"分钟级加速、tailnet 合法用户 mingda/windev 依赖此出口不能简单封端口"。
- [G]：gost.log 97M（65→95→97M 实证增长）、TOP8 合计约 8 万次、≥6 个境外 IP。
- [S]：仅记 gost.log 88MB 建议"流量模式分析"——**未发现滥用**（重大遗漏）。
- **[R] 复核**（`ls -lh` + `grep '"client"' | sort | uniq -c`）：日志终值 **370.8MB / 约 125 万行**；全文件 client 统计**外部 895,866 vs tailnet 38,435（95.9% 外部）**；TOP：89.144.8.205×112,590、5.175.171.76×88,139、206.168.190.143×76,811、185.233.200.82×35,739（[M] 观测时 23,744）、45.11.229.37×23,571、合法 mingda（100.64.0.2）×28,430。
- **采信**：[M] 的"进行中且加速"判断正确且终值仍被低估近 3 倍；[G] 的绝对数是较早期快照+口径偏窄（方向对、量级低约一个数量级）；[S] 漏报。
- **重要现状修正**（[R]）：**05:56:55 UTC 有人把 gost 重绑为 `socks5://100.64.0.3:1080`（仅 tailnet）**——`gost.service` 单元文件 mtime 05:56:54.974、ExecMainStartTimestamp 05:56:55、命令行实测 `-L socks5://100.64.0.3:1080`；**05:58:07 新建 `/etc/logrotate.d/gost`**（daily/rotate 14/size 50M/copytruncate）。重绑后日志仍从 203MB 续涨至 370.8MB（在途连接排空），至 06:23:49 后 **30 秒静默采样零增长**——公网滥用通道已被切断。执行者未查明（三腿铁律只读，非盘点腿所为；[M] 末次测量 05:26 仍在恶化，修复发生在其后的 30 分钟窗口内）。
- **残余风险**：①量化损失（是否已产生恶意流量后果/账单——`auth.purevpn.com` 出现 33,351 行等线索在三腿报告里）未做；②tailnet 内合法用户（mingda-website/windev-01）的出口是否仍可用未实测——[R] 从 pandev-comp 探 `100.64.0.3:1080` 为 **closed**（可能因 hk 节点级过滤，也可能重绑后合法用户也受影响——需 owner 确认，[M] 原话"需同步给这两台换出口"）。

### D3 hk 直连 github/pypi 速度：3.5s vs 稳定 25s —— 采信 [M]，[G] 的 25s 是滥用高峰期的暂态
- [M]：github 200 @3.5s（B 的挂起现象不复现，已仲裁）。
- [G]：github/pypi 均为 `t=25.000x s` 的"稳定极慢"（已仲裁"是极慢不是不通"）。
- **[R] 复核**（`curl -o /dev/null -sS -w "%{http_code} %{time_total}s"`）：github 200 @**3.24s**、pypi 200 @**0.39s**、baidu 200 @0.15s。
- **采信**：[M] 为当前稳态。[G] 的 25s 观测本身不假（两腿员都见到），但其窗口（04:40–05:00 UTC）与滥用高峰把 2 vCPU/网络打满的时段重叠——高峰退去后即恢复。"稳定极慢"的定性不成立，[G] 该项的根因归因（DNS/TLS 未定位）也随之降权。

### D4 gov Temporal namespace 数量：1 个 vs 2 个 —— 采信 [G]，[R] 已证实
- [M]："仅 temporal-system"（其 tctl 输出仅 head 部分）。
- [G]："namespace 2（retention 168h）"。
- **[R] 复核**（`temporal operator namespace list`）：**temporal-system + default，共 2 个**。
- **采信**：[G]。[M] 的输出截断/漏看。双方一致的实质结论（服务端 SERVING 但零 worker、established=0）不受影响——[R] 再次证实 established=0。

### D5 gov agent CLI 清单：三个腿各说一层 —— 三者互不矛盾，合并采信，[R] 已合并证实
- [S]：openclaw（/usr/bin/openclaw）。
- [M]：openclaw gateway（127.0.0.1:18789 常驻）+ **minimax-code ×3 实例在跑**（并强调 minimax-code 非 PATH 命令、node 实现）。
- [G]：4 个 PATH 二进制 openclaw / mcode / kimi / mavis-trash（已仲裁 A 正确）。
- **[R] 复核**（`command -v` + `pgrep`）：全部同时成立——PATH 里 4 个（openclaw=/usr/bin、mcode=/root/.minimax-code/bin、kimi=/root/.kimi-code/bin、mavis-trash=/root/.minimax/bin），进程面 openclaw gateway（node，--max-old-space-size=7801）+ minimax-code ×3（PID 1087344/1150575/1755046，与 [M] 的 pgrep 完全一致）。**mcode 就是 minimax-code 的 CLI 入口**（~/.minimax-code/bin/mcode）——[M] 说"非 PATH 命令"指的是名字不叫 minimax-code。
- **采信**：合并。另 [R] 查明 [G] 标记的 5 个僵尸进程父进程 = minimax-code 实例（PID 1087344，4 个 Z bash + 1 个 Z auto-setup.sh）——成因仍未知，但归属已定。

### D6 gov 待更新数：40+ vs 96 —— 采信 [M][G]，[S] 错误
- [S]："40+ 个待更包"；[M]：96（双方盘点一致）；[G]：96（已仲裁：A 的 198 是输出行数）。
- **[R] 复核**（`dnf -q check-update | awk` 过滤）：**97** 行。
- **采信**：~96–97。[S] 的"40+"口径严重偏小，不采信。

### D7 gov factory-tests 用例文件数：65 vs 66 —— 两者都对（.sh 与目录条目口径）
- [S]："cases/*.sh 共 65 个用例"；[M]："tests/cases 66 文件（报告口径 72 用例）"。
- **[R] 复核**：cases/ 目录 **66 项、其中 *.sh 65 个**。
- **采信**：两数并存、无矛盾；实质口径（72 用例、49/5/18、5 fail）三腿一致。

### D8 anolis 待更新数：90 security/264 行 vs 125 vs 未取到 —— 采信 [M]，[R] 证实
- [S]：A"90 security（1 Critical）" vs B"264 行"（命令口径不同，两数均保留——其 anolis 腿未仲裁）；[M]：125（已仲裁 D9）；[G]：≥20（清单被 head -20 截断，未取到）。
- **[R] 复核**（dnf check-update 过滤计数）：**124**。
- **采信**：[M] 的 ~124–125。[S] 两数是不同口径（security 子集/原始行数），[G] 未测到。

### D9 anolis .git 仓库数：~19–21 vs 50 —— 口径差（枚举深度不同），各有正确场景
- [S]/[M]：19 个（[M] 并集拆解：5 有 remote + 7 本地 + 9 dubious）；[G]：50（已仲裁 B 对、A 的 52 未复现）。
- **[R] 复核**：`/opt/gpumachine` maxdepth 5 = **44**、`/home/anuser` maxdepth 5 = 3、`/root` = 0、`/data` maxdepth 4 = 0 → 合计 ~47（有界计数；[G] 的 50 应为不加 maxdepth 的全盘计数）。
- **采信**：两个口径都对——全盘口径采信 [G]（~50），主仓枚举口径采信 [M]/[S]（~19–21）。**实质影响**：chenmai8 的嵌套子仓正是 [M] 枚举不到而 [G] 找到 6 处 token 的直接原因（呼应 D1）——后续盘点必须做全盘 find。

### D10 anolis docker/jiuwenswarm-app enabled 状态（[S] 腿 A/B 分歧未仲裁）—— [R] 裁决
- [S]：A disabled / B enabled（两项均是分歧项）。
- **[R] 复核**（`systemctl is-enabled`）：**jiuwenswarm-app=enabled、docker=enabled**、containerd=disabled、tailscaled=enabled。
- **采信**：[S] 的 B 盘点员对、A 错。分歧闭掉。

### D11 anolis fail2ban：未安装 vs inactive —— 采信 [M][G]，[R] 证实
- [S]：A"未安装" vs B"inactive"（分歧）；[M][G]：未安装。
- **[R] 复核**：无二进制、rpm 未装。
- **采信**：未安装。[S] 的 B 说法"inactive"不准确。

### D12 anolis 本机 factory-tests 是否有 run_all.sh：有 vs 无 —— 两个都对，[G] 表述歧义
- [M]："`factory-tests/tests/run_all.sh` + cases/70 个 .sh 就位"；[G]："本机 factory-tests/ 只有 tests/ 无 run_all.sh（权威执行体在 srv-1）"。
- **[R] 复核**：`/opt/gpumachine/factory-tests/` 下只有 `tests/`；但 **`tests/run_all.sh` 存在**（14659B，10-02）。cases/*.sh 实测 **69**（[M] 70，±1 漂移）。
- **采信**：都对——[G] 指的是顶层无 run_all.sh（歧义），[M] 给的路径本身正确。

### D13 gov sudoers 路径数：单路径 vs 双路径 —— 采信 [G]（更完整），[R] 证实
- [M]：`/etc/sudoers:121` lighthouse NOPASSWD:ALL；[G]：双路径（另有 `/etc/sudoers.d/90-cloud-init-users` root NOPASSWD:ALL）。
- **[R] 复核**：两行都在（:121 + drop-in 第 4 行）。
- **采信**：[G]。两者不矛盾，[M] 少报一条。

### D14 gov 8300/8310 暴露面与鉴权：公网可达 vs 未测 —— [G] 对（针对盘点时点），且已被盘后修复改变
- [G]：绑 0.0.0.0 且公网可达、鉴权状态未知（其最高优先级盲区）；[M]：8300 /api/state=200（334KB，从 gov 本机）未验鉴权、未提公网可达；[S]：未提。
- **[R] 复核**：①绑定仍 0.0.0.0（`ss -tlnp`：8300/8310/8787 三者全绑 0.0.0.0，[G] 对）；②**公网侧现已全部 CLOSED**——从 hk-gateway 与 pandev-comp 两个外部视角探 159.75.21.149 的 22/8300/8310/8787 均闭合，IPv6（2402:4e00:c011:300:…:0）侧同样闭合（仅 80/443 开）——云安全组已被收紧（[M] 盘点窗口内实测过公网 :22 OPEN，说明变更发生在 04:50–06:18 之间，与 hk gost 修复同一时段）；③**tailnet 侧任意节点无鉴权可读**——汇总人从 pandev-comp（非 gov 机器）`GET http://100.64.0.6:8300/api/state` 得 **200 + 334,097 字节**（与 [M] 从 gov 本机读到的 334KB 同源），8310 /healthz=200。
- **采信**：[G] 的"绑 0.0.0.0 + 鉴权未知"正确且读侧已被本次复核证实为无鉴权；"公网可达"在盘点窗口内为真、**现在已闭合**（盘后修复）。风险等级从"公网 P0"降级为"tailnet 内全量无鉴权可读 + 0.0.0.0 绑定隐患（SG 一旦回滚即重暴露）"。写路径鉴权仍未测（不能测——POST 会写状态，保留遗留）。

### D15 159.75.21.149 是否就是 governance-machine：断言 vs 未决 —— 采信 [M]，[R] 闭掉 [G] 的未决项
- [M]：是（Caddyfile L21 注释 + hk→gov direct 端点 159.75.21.149:52486 互证）；[G]：列为未决项 #9（"若不同，PG 在 gov 需重写"）。
- **[R] 复核**：gov 上 `curl -4 ifconfig.me` 与 `api.ipify.org` 均返回 **159.75.21.149**。
- **采信**：[M]。同机。anolis harness config 里的 `srv1=root@159.75.21.149` 指向的就是 gov 的公网入口；公网 :5432 CLOSED（[M] 已实测）——PG 仅 tailnet 内可达。

### D16 glue 表数：24/27/19/24+3 —— 三腿数字完全可调和，[R] 定标
- [M]：gov"24 表+14 视图"（已仲裁）+ anolis 通道实测 19 张（其 X14 自记为待解释差异）；[G]："27 张基表+14 视图=41 关系（glue 38/sem 3）"；[S]："glue 24 + sem 3"。
- **[R] 复核**（information_schema 实测）：**glue BASE TABLE 24 + VIEW 14；sem BASE TABLE 3**——即 glue 基表 24、全库基表 27、含视图 41。
- **采信**：四个数字全部自洽（24=glue 基表；27=+sem；41=+视图；[S] 的 24+3 拆分也对）。**仍未解释的**是 [M] 的 anolis 通道只看到 19 张 glue 表（可见性/查询方式差异，保留遗留）。

### D17 hk SSH 爆破计数与速率 —— 文件口径可互证，[G] 的 927/h 推导不复现
- [M]：auth.log Failed password 11,115/11,151（"增长中"）；[G]：auth.log 本次开机 1128 次/73 分钟≈**927 次/小时** + 文件总量 11,112（判定 A 标签错误）+ journal 226 vs auth.log 1128 未解释。
- **[R] 复核**：auth.log（当前文件）**11,237**、auth.log.1（上一段 38 天开机）**71,221**、`journalctl -b`（本次开机 2h39m）**349 ≈ 132 次/小时**；爆破源仍在轮换（154.219.111.178×730、109.160.32.35×406、64.188.71.209×293、47.96.114.87×121——[M] 标记的 IP 仍在）。
- **采信**：[M] 与 [G] 的数字都对上文件口径（11.1–11.2k ≈ 当期 auth.log 内容），差异在"该文件覆盖多少时间/哪次开机"的解读；[G] 的"927/h"速率推导**未能复现**（本次开机实测 ~132/h），不采信该速率；实质结论（持续爆破+root+password 开+无防护）三腿一致成立。
- **[R] 新答案**（[G] 头号遗留项"成功登录从未被排查"）：**Accepted 全量 174 次、100% publickey、0 次密码成功**。来源：100.64.0.5（windev-01）×73、100.64.0.6（gov）×65、100.64.0.7（anolis）×24、**60.188.237.31×10**（10-01 08:22 ~ 10-02 05:44，publickey root，三腿均无记载）、113.58.30.72×1（与 [M]/[G] 的"9/29 人工登录"吻合）、**42.194.143.17×1**（10-05 03:45:12——本次开机后 19 秒，重启后即登录）。→ 无密码攻破证据；两个陌生 IP 均为 publickey、疑似 owner 的其他工作点，但**需 owner 确认**（见 §7）。

### D18 anolis SSH 爆破量：70,600 vs 33,452 —— 口径互证，[R] 换算吻合
- [M]：24h 审计口径 70,600 条（合并新增实测）；[G]：全 journal 口径 33,452（自 10-02 起累计，内含未仲裁差额 11,022；`-u sshd` 口径仅 979）；[S]：未量化。
- **[R] 复核**（journal 全 units 近 24h）：**22,496** 条 "Failed password for"。
- **采信**：双方都对——auditd 每次失败发多条记录（≈3.1 条/次），70,600 审计记录 ≈ 22.5k journal 行，与本次复核**精确吻合**；[G] 的 33,452 是"自 10-02 累计"（窗口更长）。实质（高强度、日增、无防护）三腿一致。

### D19 auto-router 重启频率表述：每 30.8 秒 vs 每 5–8 秒 —— 采信 [G]（[S] 是算术框架错误）
- [S]：27,195 次 / uptime 836,756 秒 ≈ "每 30.8 秒重启一次"；[G]：NRestarts=27,211、"12:51 时 27,061，20 分钟涨 150 次"≈每 5–8 秒一次、"每 6 秒崩一次污染 journal ~600 条/小时"。
- **[R] 复核**：NRestarts=**28,054**（06:19 UTC，仍在 auto-restart）。从 [G] 的 12:51 CST 采样到 [R] 的 14:19 CST 采样，88 分钟涨 993 次 ≈ **5.3 秒/次**。
- **采信**：[G]（与 [M] 的 crash-loop 记载一致）。[S] 把崩溃次数除以了整段 uptime——崩溃循环始于 10-03 21:14 孤儿进程抢端口之后，不应摊到全程。计数器三腿本身连贯自洽（27,195→27,211→28,054）。

### D20 hk-gateway 的 tailscale 状态：idle vs active —— 瞬时快照差，无需裁决
- [S]（gov 仲裁视角）：idle；[M][G]：active、direct（156.238.240.81:4500 / 159.75.21.149:52486）。
- **采信**：均为瞬时值（tailscale 的 idle/active 反映近端连接活跃度）。hk 在线、跨机 ping 全通、offers exit node 的事实三腿一致。[R] 本次从 pandev 直连 hk 22 亦通。

### D21 [S] 的 anolis planner 停摆时间点（独有事实）—— [R] 证实
- [S]：planner 角色产物最近 2026-10-02T20:24:50Z、之后无运行（[S] 的 anolis 腿 A/B 未仲裁，原标注保留）。
- **[R] 复核**：`ls -t /opt/gpumachine/roles/planner/products/` 最新目录 **20261002T202450Z**——逐字吻合。
- **采信**：[S] 该条采信（已由 [R] 独立证实，但 [S] 报告内的"未仲裁"标注按规则保留原样）。

### D22 [G] 的 exit node"零实际使用"（独家实证）—— 采信（其他腿未测）
- [G]：`ts-forward`/`ts-postrouting`/`FORWARD` 计数全 0 → 本次开机以来零 peer 流量经 hk 出口；[M]：仅记 ExitNodeOption=true、未实测使用；[S]：把"exit node 跨节点验证"列为未覆盖。
- **采信**：[G]（唯一做了实测的腿）。其余腿未测而非矛盾。

### D23 [G] 的"8300/8310 公网可达"（独家发现）与盘点后变化 —— 见 D14
（合并入 D14，不重复。）

### D24 杂项数字口径差（一次性裁决，均有 [R] 复核）
| 项 | 各腿 | [R] 实测 | 采信 |
|---|---|---|---|
| hk 待更新 | [S] 124 / [M][G] 123（[G] 另有实装口径 110） | `apt list --upgradable` = **123** | 123 |
| anolis systemd running 数 | [S] 21 / [M][G] 23（[M] 已仲裁 D15） | **23** | [M][G] |
| hk 磁盘表述 | [S] 29GiB / [M][G] 30G（26%） | 同一物理盘（GiB/GB 计法） | 无矛盾 |
| gov systemd running 数 | 三腿均 26 | 未单独复核（无分歧） | 26 |

### D25 [G] 的"anolis HF 直连 DNS 污染"（独家发现）—— [R] 证实
- [G]：huggingface.co 解析到 Meta/Facebook 的 IPv6（2a03:2880:…），污染 IPv4 还会变；hf-mirror 200 绕行 + 25G 本地缓存。
- **[R] 复核**（anolis 上 `getent hosts huggingface.co`）：**2a03:2880:f10d:83:face:b00c:0:25de**（Facebook 段，"face:b00c"），hf-mirror 200 @1.53s。
- **采信**：[G]。其他腿未测。

### D26 [S] 独有的 gov planner 积压细节 —— 保留（未复核、不矛盾）
- [S]：decision_queue 积压 16 条、任务 #11/#22/#23/#26 review 超 SLA。其他腿只记了任务 #26 挂起。
- **采信**：不矛盾、保留为 [S] 单方记载；[R] 证实了其根源（LLM 通道 401→502）仍在恶化。

### D27 8 节点 vs 7 节点登记差集（[G] 独家发现）—— [R] 复核：现已闭合为 8
- [G]：tailscale status 8 节点 vs headscale 登记 7 节点，pandev-comp（100.64.0.8）不在 headscale（原因未查）；[M]：7 节点与 tailscale status"一一对应"（表述含混）。
- **[R] 复核**（`headscale nodes list --output json`）：当前登记 **8 节点**（ID 1,2,4,5,6,7,8,9——无 ID 3；节点 1/4 已 Expired，对应 cloudpc-01/harmony-vm），全部归属 user edgenet。差集已闭合——第 8 个注册节点的注册时间与身份未逐一定位（headscale JSON 的 hostname 字段未解析出；结合当日 03:36:52 UTC 新建的 `new-member` 用户与 hk bare 仓内的 HARMONY_AGENT_TASK.md"鸿蒙设备任务书+回传通道"，**疑似 owner 正在为新鸿蒙设备做注册准备**——此为假设，未证）。
- **采信**：[G] 的差集在其盘点时点为真；现状差集已闭合（何时/何节点注册的仍为遗留）。

### D28 三机分工是方案原文吗 —— 采信 [M] 的重要修正
- [M]：方案全文 grep 机器名/内网 IP/公网 IP/srv-1 **零命中**，"三机分工是任务设定不是方案原文"；[G] 的 hk 腿 B7 亦把该问题列为未覆盖、[G] 总报告在 4.7 节沿用了【任务设定】标注。
- **采信**：[M]（[G] 一致、[S] 未提）。对报告的影响：本汇总所有"设想 vs 实测"对照的"设想"列均指任务设定，不是方案要求。

---

## 4. 三台机器 × 关键维度现状矩阵（每格一句话）

| 维度 | governance-machine（治理面） | anolis-gpu-01（执行面） | hk-gateway（网关） |
|---|---|---|---|
| **agent 基础设施落地** | CloudCrane/jiuwen_glue 一整套在产：PG 治理库（glue 24 基表+14 视图+sem 3）、OpenBao+vault-broker、Higress+auto-router、Temporal、两套门禁、headscale 控制面——但 §9.5 harnessos/ 零落地，Memory/Jev/OwnerGate/MQ worker/kernel gateway 六大件缺，6→9 张治理表 0 行 | 方案能力的另一套命名落地在 /opt/gpumachine（harness 8 模块+jiuwenswarm+roles+PM/patrol+契约 registry+MCP agent-browser+FS 决策留痕），9 项真在跑；但 harnessos/ 零命中、OwnerGate 无代码、Jev 仅有权重+脚本、Memory 无向量库、真 MQ 无容器 | **0/15 项**：除 tailscaled 提供网络可达性外，无任何 agent 协作组件；仅两处雏形（/srv/git 裸仓 + /srv/inbox 未运行的 upload_server.py） |
| **在跑服务** | 15 容器全 Up（RestartCount=0）+ 6 自建服务全响应（auto-router 功能活编排死）+ 20 条 cron 全部编排在此（回归门禁/计量/监控/通知/备份） | 6 常驻（jiuwenswarm systemd + agent-browser/xdng×4 无 systemd）+ otel 容器 + 4 条 cron（reap/wake-gate/pm-loop/patrol）+ 3 个 Bao 续期 timer | 21 个 running（gost/sing-box/warp-svc/tailscaled/hk-nat + 系统服务）；warp-reroute failed、无任何业务 timer/cron |
| **安全** | fail2ban 无/三防火墙全关/INPUT ACCEPT（靠腾讯云 SG，现仅放 80/443+3478udp）/root+password+7 公钥/lighthouse+root 双 NOPASSWD/8300/8310 绑 0.0.0.0 且 tailnet 内无鉴权可读 | **公网 22 正被持续高强度爆破**（~22.5k 次/24h journal 口径）且无任何防护/anuser NOPASSWD:ALL + 5 身份可进/7 处 git remote 明文 token/INPUT ACCEPT（物理网段可直连 22）/root 免密完全依赖 Tailscale SSH（受 group:trusted 分层保护） | gost 公网滥用已被盘后止血（重绑 tailnet-only）/**22 爆破仍在进行**（~132/h 本次开机）且 root+password 开/7863 公网可达（warp-reroute failed 未修复）/无 fail2ban/防火墙全关（ufw unit active 但策略 inactive）/成功登录排查已清（174 次全 publickey、无密码攻破证据） |
| **资源** | 8 vCPU/15GiB/无 SWAP；**load 13–19 长期过载**（三主因：ClickHouse 454–552%、console_tui 99.8%、minimax-code 95.9%）、瞬时 free 曾低至 159MB、OOM 风险实在；96–97 个包待更新 | 16 vCPU/125GiB/无 SWAP；GPU 2×V100S-32GB 在线但 GPU1 47% 被语音业务占（利用率 0%）；**/data 84% 接近满**；124–125 个包待更新；load 空闲 | 2 vCPU/1.9GiB/无 SWAP/30G 盘（26%）；滥用高峰曾压至 load 3.5，止血后 06:23 实测 load 2.3–2.6 仍偏高；/var/log 2.1G+（gost.log 370.8MB 已有 logrotate 但尚未轮转）；123 个包待更新 |
| **网络** | tailnet 100.64.0.6 + 公网 159.75.21.149（=SRV-1，[R] 已确认同机）+ IPv6 出口可用；公网仅 80/443（8080/8200/4317/5432/7233 等仅 tailnet）；境外直连不通（github/google 等，须走代理） | ens3 192.168.0.95 + tailnet 100.64.0.7；业务端口仅 22 与 8125 对外（8125 仅 tailnet），9001-9004/18092 回环；到 gov 直连 ~31ms；google 直连不通、HF 被 DNS 污染（hf-mirror 绕行 200） | 公网 156.238.240.81（香港）+ tailnet 100.64.0.3；现在无全局 IPv6（仅 link-local——[R] 已闭 [G] 的 IPv6 暴露面遗留项）；到 gov direct ~60ms、**到 anolis 仅 DERP(hkg) 中继 ~70–157ms**；MagicDNS 本机关闭；显式代理 7864 可用、透明分流整体不生效、exit node 广播但零使用 |

---

## 5. 高危问题统一清单（三腿 + [R] 合并去重，按紧急度排序）

> 分级：**A 正在造成损害**（盘点窗口内属实，[R] 注明当前状态）→ **B 会造成损害**（未修复， imminent）→ **C 隐患**。

| # | 级别 | 问题 | 关键事实与当前状态 | 出处 |
|---|---|---|---|---|
| 1 | A→已止血 | **hk gost 无鉴权公网 SOCKS5 被大规模滥用**（三腿记录的最大安全事件） | 终值：外部连接 895,866 条（95.9%）、日志 370.8MB/~125 万行、TOP 外部 IP 112,590 次、滥用期间 load 压至 3.5（2 vCPU）。**05:56:55 UTC 已被重绑 tailnet-only（100.64.0.3:1080）+ logrotate**，06:23:49 后日志零增长。残余：损失量化/恶意流量后果（auth.purevpn.com×33,351 行等）/370MB 日志取证保留/tailnet 合法用户（mingda、windev）出口是否仍可用（[R] 从 pandev 探 100.64.0.3:1080 为 closed，**需确认**） | [M]§1.3/[G]§12；[R] 全文件统计+时间线 |
| 2 | A（仍进行中） | **anolis 公网 22 持续高强度爆破，无任何防护** | 24h journal 口径 22,496 次失败口令（≈[M] 的 70,600 条 audit 记录换算口径）、日增趋势；无 fail2ban、INPUT ACCEPT。**未修复迹象**（[R] 本次未观测到处置） | [M]（合并新增）/[G]；[R] 复测 |
| 3 | A（仍进行中） | **hk 公网 22 持续爆破 + root+password 开** | 本次开机 2h39m journal 口径 349 次（≈132/h）、源 IP 持续轮换（154.219.111.178/109.160.32.35/64.188.71.209/47.96.114.87 等）。成功登录侧已排查：174 次 Accepted 全 publickey、**0 次密码成功**（无被攻破证据，[R] 新答案） | [M]/[G]；[R] Accepted 排查 |
| 4 | A（仍进行中） | **gov 回归门禁红 + 告警链断——"坏了这件事本身送不到人"** | 49/5/18、fail 4→5 违反"只降不升"铁律；微信通道最近送达 10-01（断 4 天）、回归 fail 告警连续 3 天 rc=3 送不出去 | [M]§7.4.1/[G]§3.2.4 |
| 5 | A（仍进行中，在恶化） | **gov 资源过载**：8 核 load 13–19 | [R] 实测 load 15.60、ClickHouse 552%（三腿观测 453–513%，仍在走高）、console_tui 99.8%、minimax-code 95.9%；零 SWAP、瞬时 free 曾 159MB——OOM/雪崩风险实在；成因（ClickHouse MV/写入频率）未定位 | [M]§1/[G]§3.2.2；[R] 复测 |
| 6 | B | **anolis 7 处 git remote 明文 token**（AGENTS.md 红线第 1 条被破） | chenmai8 六仓 github（同一用户名 feasy898，大概率同一 PAT）+ qw-arena2 cnb——轮换 2 个 token 可清零 7 处；token 是否已失效/已 push/在历史提交中**三腿均未查**（需 `git log -p` 全量扫描） | [G]§3.1.6；[R] masked 复核确认 |
| 7 | B | **权限收敛失效**：anolis `anuser NOPASSWD:ALL`（=root）+ 5 身份可免密进 anuser（含 `harmony-host`——所属节点已离线 25 天、归属未审）；gov root+lighthouse 双 NOPASSWD | [M]/[G]；[R] 两机 sudoers 均实测确认 |
| 8 | B | **gov factory-board 8300 对任意 tailnet 节点无鉴权全量可读 + 服务仍绑 0.0.0.0**（vault-broker 8310 同绑定，鉴权状态未验） | [R] 从非 gov 节点 GET /api/state = 200 + 334,097 字节；公网侧已被 SG 闭合（盘后修复），但**任何 SG 回滚即重暴露**；写路径鉴权未测（不能测——POST 会写状态） | [G]§最高盲区；[R] tailnet 视角新证实 |
| 9 | B | **anolis /data 84%（295G 数据盘）** | /data 大户 night 99G、xdng 58G、beaneye-datasets 37G、hf 25G | [S][M][G] 一致；[R] df 复测吻合 |
| 10 | B | **gov auto-router 崩溃循环**（编排层死、孤儿进程 PID 3522460 自 10-03 21:14 顶替、journal ~600 条/小时污染） | [R] NRestarts=28,054（≈5.3 秒/次），8777 /health 仍 200；修复需 kill 孤儿+修 unit（**未执行**——三腿与汇总人均按只读铁律不动） | [S][M][G]；[R] 计数器+PID+启动时间 |
| 11 | B | **hk warp-reroute failed 未修复**：透明分流失效 + 7863 公网可达 + sing-box 2 次 too many open files | [R] 仍 failed、7863 仍绑 0.0.0.0（公网 3/3 OPEN 期间）；根因是竞态（缺 After=/Restart=，安全门本身工作正常） | [S][M][G]；[R] 复测 |
| 12 | B | **gov planner LLM 通道故障在产且在演变**（401 降档→[R] 502 Bad Gateway） | [S] 的 decision_queue=16、任务 #11/#22/#23/#26 review 超 SLA（单方记载，保留）；治理面决策停摆中 | [S][M][G]；[R] 502 新证据 |
| 13 | B | **hk 唯一代码资产无 remote、无备份**：/srv/git/ohos-tailscale.git（bare，812K，main@20beb2a）+ /srv/inbox；两条回传通道（8090/9418）全关且 HMTOKEN 无取值来源 | 磁盘故障即不可恢复 | [M]§3.3/[G]§3.3.3 |
| 14 | B | **SSH 弱配置与跨机公钥网**：gov root+password+7 公钥、hk root+password+6 公钥（含 `zcode-managed-*` 与已离线节点的 `harmony-host`）；tailnet ACL 为全 mesh + accept 式 Tailscale SSH——策略文件自认"一把被盗的节点密钥=立即 root，无第二道门" | [M]/[G]；[R] policy.hujson 全文（10-05 起从 minimal-privilege 回滚为 full-mesh + 按 user 分层 SSH；group:trusted 仅 edgenet@） |
| 15 | B | **gov 8300/8310/8787 的公网暴露史**：SG 收紧前公网可达（[G] 实测、[M] 间接实测过 :22 OPEN）——已闭合，但**收紧动作无留痕/无告知**，易被回滚 | [G]；[R] 双栈双视角验证现已闭合 |
| 16 | C | **anolis PM 空转热循环**：每 5 分钟实调一次百炼、457 份 reports/1272 行判定、连续同判、7 条产品线 worklog 全 stale 103–105h、dispatch 仅 1 份（10-01） | [G]（独家深度发现，[M] 记录了循环在跑但未定性为空转）——掩盖真实停滞+持续烧 LLM 调用 |
| 17 | C | **anolis planner 角色停摆**（10-02 20:24Z 后无运行）+ qw_worker 日志停 10-02 | 执行-规划链条断 3 天；[R] 证实产物时间戳 | [S]（已证实）；[M]（worker 部分） |
| 18 | C | **gov OTLP_BEARER_TOKEN 未设置**（compose L306 引用但未定义、默认空串）→ 遥测接收端疑似无鉴权（tailnet only） | [R] compose L306 逐字确认（在 /opt/company/platform/ops/compose/） | [G]（独家）；[R] 确认 |
| 19 | C | **gov 443 TLS 握手失败 rc=35**（三测一致、非新增）+ **GitHub/Google 直连全断**（两个 GitHub remote 的 git fetch 可行性未证实） | [M]/[G]；[R] 443 本机 curl 000 复测吻合 | [M]/[G] |
| 20 | C | **gov 工作区卫生**：5 僵尸进程（父=minimax-code 1087344，[R] 已查明归属）、两仓各 21 脏文件、company-ops 双副本不同步（且 /opt/company/ops/notify 与 company-ops 侧副本漂移）、大量 .bak（含 auth.env.bak 凭据备份类）、kafka/restate/tb 空遗留目录、宿主残留 temporal-server 进程（Sep28 起，lighthouse 用户） | [M]/[G]；[R] 僵尸父进程+compose 工作目录 |
| 21 | C | **anolis 5 个业务服务无 systemd/无自愈**（agent-browser 8125 + xdng 9001-9004） | [M]/[G] 一致 | [M]/[G] |
| 22 | C | **gov 部署双源漂移 + 运维窗 ≤2026-10-05（今天）到期**：实机 compose 生效源=platform.git 克隆（/opt/company/platform/ops/compose，[R] 已定位），真相源=company-ops 侧；真相源→实机 PR 通道未建立 | [M]/[G]；[R] compose working_dir 实测 | [M]/[G] |
| 23 | C | **待更新积压**：gov 96–97 / anolis 124–125 / hk 123（security 分类均未做） | [R] 三机复测吻合 | [M][G] |
| 24 | C | **hk gost.log 370.8MB 已有 logrotate 配置但从未轮转**（配置 05:58:07 新建）；/var/log 2.1G+ | 首次轮转后可回落；"数日内挤压根分区"的风险已缓解但未消除 | [M]（无轮转→[R] 已有配置） |
| 25 | C | **gov 备份从未做恢复演练**（backup-daily + bao-snapshot 保留 14 份在跑，有效性未证实）；anolis backups/ 内容未盘点 | [M]/[G] | [M]/[G] |
| 26 | C | **anolis HF 直连被 DNS 污染**（解析到 Facebook IPv6 段）——hf-mirror 绕行可用 + 25G 本地缓存，"断 HF"已修正为"仅直连这一条路断" | [G]（独家）；[R] getent 证实 | [G] |
| 27 | C | **gov MinIO 仅有 langfuse 桶（无 artifact 桶）**——"仅 1 个空 langfuse 桶"的"空"仍为 [M]【单方记录，未核实】（桶清单 langfuse-only 已由 [G]+[R] 侧证，内容未验） | [M]/[G] | [M]（标注保留）/[G] |
| 28 | C | **tailnet 离线节点与密钥**：cloudpc-01（12 天 offline、Expired）、harmony-vm（25 天、Expired）、windev-01（SYSTEM-GUIDE 称 10-07 销毁——后天）；headscale 180 天过期策略生效中 | [M]/[G]；[R] 节点列表 1/4 Expired 证实 | [M]/[G] |

---

## 6. 跨腿跑通/跑不通总表（去重合并，标注出处腿；[R✓]=汇总人本次复核证实，[R+]=复核补充了新细节）

### 6.1 跑通（X-01 ~ X-36）

| 编号 | 对象 | 结论 | 出处 |
|---|---|---|---|
| X-01 | tailnet `edgenet` 控制面（gov 上自托管 headscale v0.29.3） | ✅ 可用；8 节点在册（[G] 盘点时 7+1 差集，[R] 现为 8） | [S][M][G]；[R✓] |
| X-02 | 三机 tailnet 互 ping（0% 丢包）+ SSH 22 互通 | ✅（hk→anolis 走 DERP hkg 中继 69–157ms、直连未建立；其余多为直连） | [S][M][G]；[R✓] |
| X-03 | 三机系统基本面（OS/内核/规格/虚拟化/时间同步/journal 滚动） | ✅ 三腿全绿（chronyd Stratum 3–4、journal 正常滚动） | [S][M][G] |
| X-04 | anolis GPU（2× V100S-32GB，驱动 570.133.20/CUDA 12.8） | ✅ 在线（GPU0 310MiB 空闲、GPU1 15516MiB≈47% 被语音栈占、利用率 0%） | [S][M][G]；[R✓] |
| X-05 | anolis → gov：PG 治理库（5432 OPEN + SSH 别名双通道） | ✅（jiuwenswarm 经 TEAM_PG_DSN 直连 + harness pgsem 经 srv1-gov SSH+容器内 psql——双通道并存已仲裁） | [M]；[S][G] |
| X-06 | anolis → gov：OpenBao（:8200 /v1/sys/health 200）+ 3 个续期 timer 在转 | ✅（执行面零长期密钥、tmpfs 注入、0600、argv-free） | [S][M][G] |
| X-07 | anolis → gov：Higress LLM 网关（:8080=200；anolis /v1/models 404=服务可达未带 key） | ✅ 唯一模型入口，step-3.5-flash | [S][M][G] |
| X-08 | anolis → gov：OTLP 遥测（otel Up 7d → 100.64.0.6:4317 → Langfuse/ClickHouse events_core 40555 行） | ✅ 观测链完整 | [S][M][G] |
| X-09 | anolis → gov：**patrol 跨机驱动权威回归套件**（PAT-01"ssh srv-1 权威副本"+ role-run.sh:57 WS_SSH_TARGET=root@100.64.0.6） | ✅ **[R+] 新实证**——gov 12:17 基线之谜解开（patrol 每 2h cron `17 */2` 经 SSH 驱动） | [M][G] 标记的时间吻合 + [R] 脚本证据 |
| X-10 | anolis → gov：merger 角色仓跨机拉取（cluster-smoke origin → gov merger 工作区 + 机器门禁提交） | ✅ [G] 称"唯一被实证的跨机协同"——与 X-09 并列后至少已有两条 | [G] |
| X-11 | gov 15 容器全部 Up、RestartCount=0、7 个 healthy | ✅（headscale 为当日 11:37 重建） | [S][M][G]；[R✓] 计数 15 |
| X-12 | gov 6 个自建进程服务全部有响应（factory-board 8300/planner/vault-broker 8310/peidian-agent 8787/auto-router 8777=200 v9.0-tiering/openclaw 18789） | ✅（auto-router 是孤儿进程承载，编排层坏） | [S][M][G]；[R✓] 8777 /health 200 |
| X-13 | gov 治理数据层真实在产（行数见 §2 C6）+ 决策留痕 append-only + 契约 registry（anolis 侧 registry.json+sha256） | ✅（决策留痕 DDL 拒绝 UPDATE/DELETE 触发器一条仍为 [M]【单方记录，未核实】，标注保留） | [S][M][G]；[R✓] 行数 |
| X-14 | gov 两套门禁可跑：factory-tests 72 例（49/5/18）+ kernel pytest 184 例全绿 | ✅（[R+] 0 行表实测 9 张） | [M][G] |
| X-15 | anolis eval-gate 108/108 全绿 + harness 8/8 模块导入成功（隔离副本复现） | ✅ | [G]（独家实跑） |
| X-16 | anolis jiuwenswarm-app（systemd，10-02 14:31 起，127.0.0.1:18092，WS 426 正常）+ agent-browser MCP（:8125 仅 tailnet）+ xdng 4 服务（9001-9004 回环 200） | ✅ | [S][M][G]；[R✓] enabled |
| X-17 | anolis PM/patrol/reap cron 循环在跑（wake-gate 与 pm-loop 每 5min、patrol 每 2h） | ✅（但 PM 为空转热循环——见 §5 #16） | [S][M][G]；[R+] patrol 最新 06:17Z |
| X-18 | anolis 凭据纪律：3 个 Bao 续期 timer + tmpfs + 0600 + handover/scan_secrets.py 产物在 | ✅（但被 7 处 token 破口抵消——见 §5 #6） | [S][M][G] |
| X-19 | gov 短时凭据链：vault-broker 8310（/healthz 200、vault_audit 35 条）+ OpenBao 2.6.2 healthy + JIT 铸 token/按 accessor 回收脚本 | ✅ 三腿共识"落实最好组件之一" | [S][M][G]；[R✓] 8310=200 |
| X-20 | gov ClickHouse 非空且在写（14 张 Langfuse 表、events_core 40555） | ✅（[M] 仲裁 B 的"空库"作废；同一容器是 load 主因——见 §5 #5） | [M]（仲裁）/[G] |
| X-21 | gov cron 编排 20 条有效（计量/监控/通知/回归门禁/备份） | ✅（已仲裁；CNB token 经 OpenBao 现取零落盘） | [M][G] |
| X-22 | gov 4 个 agent CLI（openclaw/mcode/kimi/mavis-trash）+ openclaw gateway 常驻 + minimax-code ×3 在跑 | ✅（三方清单合并——见 §3 D5） | [S][M][G]；[R✓] 全证实 |
| X-23 | gov→公网（国内）：baidu/npm/pypi 200；Anthropic 403（网络可达）；IPv6 出口可用 | ✅ | [S][M][G] |
| X-24 | anolis→公网：baidu/github/pypi 200 + hf-mirror 200（HF 直连被 DNS 污染但镜像绕行） | ✅ | [M][G]；[R✓] getent+curl |
| X-25 | hk→公网：baidu/google/github/cloudflare/npm/hf 均 200（openai/anthropic/grok 403=链路通缺 key） | ✅（github 实测 3.24s——[M] 口径为当前稳态） | [M][G][S]；[R✓] 复测 |
| X-26 | hk 显式代理 7864 可用（绑 100.64.0.3 仅 tailnet、WARP 路径 trace warp=on colo=HKG；公网侧 closed） | ✅ | [S][M][G]；[R✓] 绑定 |
| X-27 | hk gost 代理功能本身（tailnet 内） | ⚠️ 盘点时 ✅（tailnet 内合法用户 mingda×28,430/windev×10,002 在用）；**重绑后合法用户是否仍可达待确认**（[R] 从 pandev 探 100.64.0.3:1080 为 closed） | [M][G]；[R] 待确认项 |
| X-28 | hk exit node 控制面可见（广播 0.0.0.0/0、ip_forward=1、MASQUERADE 在位、ExitNodeOption=true） | ✅（但实际零使用——见 X-34） | [S][M][G] |
| X-29 | hk bare 仓可读（3 commits、812K、内容 HARMONY_AGENT_TASK.md 等）+ upload_server.py 代码质量良好（与仓库副本 diff=IDENTICAL、防穿越、512MB 上限） | ✅ | [M][G]；[S] 部分 |
| X-30 | gov headscale 管理功能可用（nodes/users list；用户 edgenet + new-member） | ✅ | [S]（用户线索）；[R✓] |
| X-31 | gov 8777 孤儿进程身份与时间戳（PID 3522460、10-03 21:14:07、父子命令实锤） | ✅ 定位完成（谁做的仍是遗留项） | [M][G]；[R✓] lstart 逐字吻合 |
| X-32 | gov 僵尸进程归属 | [R+] 已查明父进程=minimax-code（PID 1087344，4×Z bash + 1×Z auto-setup.sh）；成因未知 | [G]（盲区）→[R] 归属已定 |
| X-33 | gov/zk 外部探测（公网 vantage→159.75.21.149） | [R✓] 公网仅 80/443（443 TLS 握手失败——见 X-40）；22/8300/8310/8787 已闭合（IPv4+IPv6 双栈） | [R] 独家 |
| X-34 | ——（见 6.2 X-52） | | |
| X-35 | gov 443 端口 TCP 层 | ✅ OPEN（但 TLS 握手失败——服务层坏，见 X-40） | [R]；[G]（rc=35） |
| X-36 | 三机无全局 IPv6（hk 仅 link-local——[R] 已闭 [G] 的"IPv6 暴露面"遗留项） | ✅ | [R] 独家 |

### 6.2 跑不通 / 坏了 / 未建（X-37 ~ X-70）

| 编号 | 对象 | 结论 | 出处 |
|---|---|---|---|
| X-37 | 方案 §9.5 `harnessos/` 目录树 | ❌ 三机零命中（实机为 CloudCrane 命名体系——需 owner 映射/裁定） | [S][M][G] |
| X-38 | Jev 独立判别服务（§8 的 13/16 个接入位） | ❌ 三机全无服务；生产替代=百炼通用模型 decision-model-preview（anolis wake-gate）+ auto-router 代码路径（gov，33 处命中）；anolis 仅有权重+2 脚本（属 video-capability 产品线） | [S][M][G] |
| X-39 | Memory/向量库运行时 | ❌ 三机零向量库（chroma/faiss/milvus/qdrant/pgvector 全 0；anolis 依赖齐装但 skill_retrieval disabled、promotion 管线 0 行晋升） | [S][M][G] |
| X-40 | gov 443 TLS | ❌ 握手失败（rc=35 三测一致；[R] 复测 000；回归 L0-12 按 skip 登记——非新增故障） | [M][G]；[R✓] |
| X-41 | gov 微信 OwnerGate 通道 | ❌ 最近送达 10-01（断 4 天）；回归 fail 告警 rc=3 连续 3 天送不出去 | [M][G] |
| X-42 | gov planner LLM 通道 | ❌ 401 降档→**[R] 502 Bad Gateway（14:05/14:16 CST）**——治理面决策停摆且在演变 | [S][M][G]；[R] 502 新证据 |
| X-43 | gov auto-router systemd 自启路径 | ❌ 崩溃循环 NRestarts=28,054（[R]；≈5.3 秒/次）——功能活、编排层死 | [S][M][G]；[R✓] |
| X-44 | gov 生产 MQ（Temporal worker） | ❌ established=0（零 worker；namespace 有 temporal-system+default 两个——[R] 定标 [G] 对 [M] 漏）；anolis qw_worker 存活但日志停 10-02（模拟提交试点） | [S][M][G]；[R✓] |
| X-45 | gov 治理表空转 | ❌ 9 张表 0 行（artifact_route/challenge/message_receipt/rule_violation/promotion_record/capability_version + promotion_transition/promotion_eval_event/capability_metric_event——[R] 精确 count 定标 9 张） | [M]（6 张）/[G]（6 张）；[R] 定标 9 |
| X-46 | gov MinIO artifact 桶 | ❌ 仅 langfuse 桶（"空"仍为 [M]【单方记录，未核实】） | [M][G] |
| X-47 | gov kernel gateway / LiteLLM 适配器 / Kafka | ❌ 未部署/悬空/无容器（仅镜像与空目录） | [M][G] |
| X-48 | gov OPA 容器接流量 | ❌ healthy 但未接流量（容器 distroless 无法 exec——[M] 与 [R] 均遇到；headscale 容器同样 distroless，需宿主侧读配置） | [M][G]；[R] 同现象 |
| X-49 | gov OTLP_BEARER_TOKEN | ❌ compose L306 引用但未设置（默认空串） | [G]；[R✓] L306 逐字确认 |
| X-50 | gov skill-sync.sh / SkillFS / agentsight（anolis 侧） | ❌ 缺失/未部署/装了没装完（anolis agentsight/ 仅 TODO-INSTALL.md） | [G][M] |
| X-51 | gov 资源余量 | ❌ load 13–19（[R] 15.60）、ClickHouse 454–552%、console_tui 99.8%、minimax-code 95.9%、零 SWAP、瞬时 free 159MB | [M][G]；[R✓] 更高 |
| X-52 | hk exit node 实际使用 | ❌ 零（ts-forward/ts-postrouting/FORWARD 计数全 0——[G] 独家实证） | [G] |
| X-53 | hk 域名透明分流（AI 站点走 WARP） | ❌ 整体不生效（warp-reroute failed、REDIRECT 未装、三条兜底规则一条未装） | [S][M][G]；[R✓] 仍 failed |
| X-54 | hk 结果回传通道 8090/9418 | ❌ 全关（无监听/无 unit/公网 closed/HMTOKEN 无取值来源） | [M][G]；[S] 部分 |
| X-55 | hk→anolis 直连 | ❌ 仅 DERP(hkg) 中继 ~70–157ms（direct connection not established） | [S][M][G] |
| X-56 | anolis agent CLI（10 个）+ hk agent CLI（9~10 个） | ❌ 全 MISSING（执行主体是服务而非 CLI——三机不互通、不可互相调用） | [S][M][G] |
| X-57 | gov←GPU 机 node 注册 | ❌ glue.node/node_heartbeat 各 1 行（L3-08 记"GPU 机从未注册 node"）——治理面看不到执行面的正式注册 | [G] |
| X-58 | anolis OwnerGate | ❌ 无代码/无服务/无配置（仅 1 篇 handover 文档 + gatekeeper.yaml status:defined 定义卡，建队归 W-12） | [M][G] |
| X-59 | anolis 真消息队列 | ❌ Temporal 4 镜像 0 容器（temporal_open:0） | [M][G] |
| X-60 | anolis 真沙箱运行态 | ❌ 无常驻容器（仅 docker run --rm 弱隔离 + role-base:23-ssh 镜像 0 容器） | [M][G] |
| X-61 | anolis planner 角色运行 | ❌ 产物停在 20261002T202450Z（[S] 独家→[R] 证实） | [S]；[R✓] |
| X-62 | anolis google 直连 | ❌ 12s 超时（[M] 已仲裁 D8）；HF 直连被 DNS 污染（[G]→[R] 证实） | [M][G]；[R✓] |
| X-63 | anolis 5 个业务服务托管 | ❌ 8125/9001-9004 无 systemd/无 Restart/无自愈 | [M][G] |
| X-64 | anolis PM 健康度 | ❌ 空转热循环（457 reports/1272 判定、7 条产品线 worklog 全 stale 103–105h、2 张工单 136.8h/57.2h、dispatch 仅 1 份） | [G]（独家定性） |
| X-65 | anolis /data 空间 | ⚠️ 84%（295G；night 99G/xdng 58G/beaneye-datasets 37G/hf 25G） | [S][M][G]；[R✓] |
| X-66 | 三机 fail2ban / 主机防火墙 / SWAP | ❌ 全无（INPUT 全 ACCEPT；gov/hk SELinux 关或仅 AppArmor；hk ufw unit active 但策略 inactive——[R] 复测澄清：systemd active ≠ 防火墙生效） | [S][M][G]；[R✓] |
| X-67 | gov 96–97/anolis 124–125/hk 123 待更新 | ⚠️ 积压（security 分类未做） | [M][G]；[R✓] 三机复测 |
| X-68 | gov 公网境外直连（GitHub/Google/OpenAI/HF） | ❌ 全断（境外须走代理——与 SYSTEM-GUIDE 记载一致；两个 GitHub remote 的 git fetch 可行性未证实） | [M][G] |
| X-69 | hk LXD | ⚠️ 装了不用（snap 容器在、无实例——lxd list 需交互式未查） | [M][G] |
| X-70 | hk gost 公网暴露（盘点窗口内） | ❌→**已被盘后修复止血**（05:56:55 重绑 tailnet-only；[R] 06:23:49 后日志零增长）——但执行者/合法用户出口/损失量化三项待确认 | [M][G]（滥用属实）+[R]（止血证实） |

---

## 7. 遗留问题清单（三腿未答 + 汇总后仍未闭项的）

> 标注 ★ = [R] 本次已部分闭项；☆ = 仍完全 open；△ = 需 owner 决策/确认（技术手段无法自答）。

1. **△ 盘后修复动作的执行者与授权确认**（05:56–05:58 UTC gost 重绑+logrotate、同期 gov SG 收紧 22/8300/8310/8787、10:51 headscale ACL 策略更新）：是否 owner 本人/其自动化所为？是否留有变更记录？——三腿只读铁律下不可能由盘点腿执行，需 owner 认领并留痕。
2. **△ gost 滥用损失量化与善后**：370.8MB 日志（约 125 万行、外部 895,866 条连接）是否已被用于恶意流量（auth.purevpn.com×33,351 行、google/openai 目标等）/是否产生云账单损失；日志是否需留存取证；`60.188.237.31`（×10 次 publickey root，10-01~10-02）与 `42.194.143.17`（×1，10-05 03:45:12 重启后 19 秒）两个三腿均未记录的外部 IP 是否 owner 本人。
3. **△ tailnet 内合法用户出口是否被修复误伤**：[M] 明确 mingda-website（100.64.0.2，×28,430 次）与 windev-01 依赖 gost 出口；[R] 从 pandev-comp 探 100.64.0.3:1080 为 **closed**（hk 节点级过滤或重绑副作用均有可能）——需 owner 在 mingda/windev 侧实测确认，若断需给这两台换出口方案（[M] 原话）。
4. **anolis 7 处 token 的实际有效性与泄露面**：`git log -p` 全量扫描（是否已 push、是否在历史提交中）、github PAT（feasy898）与 cnb token 的轮换与改用凭据助手——三腿都没做。☆
5. **gov 8300/8310 写路径与凭据调用鉴权**：读侧已证实无鉴权（[R]），POST/凭据调用是否需要鉴权未测（不能测——会写状态）；vault-broker 的 call.ok 调用链是否校验调用者身份。☆
6. **gov ClickHouse 454–552% CPU 成因**（MV 刷新/高频写入未定位——全机 load 主因）、console_tui 99.8% 忙循环的 bug 定位、minimax-code 95.9% 在算什么。☆
7. **gov 5 个回归 FAIL 的根因归属与修复**（L1-03/L3-05/L4-10/L6-01/L6-09——哪些是已知待办、哪些是孤儿缺陷）；修复后微信通道 rc=3 的送达问题。☆
8. **★ 12:17 基线触发者之谜**：[M]/[G] 均标记"cron 为 06:00、12:17 必为手动、谁触发未验证"——[R] 已证实为 anolis patrol 的 PAT-01（每 2h cron `17 */2` 经 SSH 驱动 gov 权威套件）；剩余待验证：06:00 的 cron 定时跑与 patrol 的跨机跑在同一报告目录的产物如何区分/是否重复计费。☆
9. **[M] 的 X14：anolis 通道看到 19 张 glue 表 vs gov 实测 27 基表**的可见性差异原因（pgsem 查询方式/权限/隐藏表）。☆
10. **8777 孤儿进程来龙去脉**：谁在 10-03 21:14 杀了旧进程 943769 并 nohup 顶替、为何不修 unit（[M] 盲区 1——修复方案"kill 3522460+修 unit"三腿与 [R] 均未执行，需 owner 授权）。☆
11. **△ 双实现裁定**：CloudCrane（实机命名）与 HarnessOS（方案 §9.5 命名）两套治理语义的正式映射表/收敛方向——[G] 称"需 owner 架构级裁定"；同时未建成四大件（Jev/Memory/OwnerGate/生产 MQ）是否立项。△
12. **△ 部署双源漂移与运维窗**：SYSTEM-GUIDE 记载运维窗 ≤2026-10-05（**今天**到期）；真相源→实机 PR 正向通道未建立；company-ops 双副本（/opt 停 10-01 vs /root/cnb-staging 停 09-26）哪份生效。△
13. **tailnet 拓扑遗留**：headscale 第 8 个注册节点的身份与时间（[R] 现已 8 节点 vs [G] 盘点时 7——结合 new-member 用户 10-05 03:36 创建与 hk bare 仓 HARMONY_AGENT_TASK.md，**疑似**新鸿蒙设备注册准备中——假设未证）；hk→anolis 的 DERP-only 直连改善（UDP 打洞失败原因）；离线节点处置（cloudpc/harmony Expired 密钥、windev 称 10-07 销毁）。☆
14. **★ gov IPv6 暴露面**：[R] 已闭（仅 80/443 开、22/8300/8310/8787 v6 侧 closed；剩余 3478/udp 未测）。hk 无全局 IPv6（仅 link-local）——[G] 的 IPv6 遗留项基本可闭。☆（3478）
15. **★ hk 成功登录排查**：[R] 已闭主体（174 次全 publickey、0 密码成功）；剩余：60.188.237.31/42.194.143.17 身份确认（见 #2）。btmp.1 139MB 覆盖更早历史未展开。☆
16. **gov 备份有效性**：backup-daily/bao-snapshot 从未恢复演练；anolis backups/、local-plane-backup/ 内容未盘点；hk 无任何备份。☆
17. **anolis /data 治理**：84% 接近满；/data/night 99G 的目录结构与保留策略；7 条产品线 worklog 集体停滞 103–105h 的原因（PM 空转的另一面）。☆
18. **[M] 的【单方记录，未核实】项**（均保留原标注、未升格）：MinIO langfuse 桶"空"、agentic-factory-projects 状态表数字（469/709/233 等）、decision_record DDL 拒绝 UPDATE/DELETE 触发器（需在 gov 查库证实）、warp-reroute 上次成功时间 09-19、v_task_board 任务样例、session-broker provider 接入、anolis 公网出口 IP。☆
19. **[S] 的 anolis A/B 未合并仲裁的历史遗留**：journal 历史缺口矛盾（[G] 亦标"结论存疑需重查"——[S] 的 anolis 腿分歧由本次 [R] 仅裁决了 enabled/fail2ban 两项，其余如 docker/jiuwenswarm 之外的分歧项未逐项复核）。☆
20. **warp-cli 真实连接状态**（需 --accept-tos 写状态，三腿与 [R] 均未测；WARP 在线由 trace 间接证实）、exit node 端到端出口测试（需 tailscale set 状态变更）、7863 的功能级行为（公网打进去会发生什么）。☆
21. **gov zot 内容（repos=0）、Redis keyspace（有密码未读）、Temporal workflow 实例级状态、Higress 路由明细与 consumers、镜像 digest/签名**——深查项，[M]/[S] 的未覆盖清单合并保留。☆
22. **jiuwen-glue README 数字（CI 519 passed）与实测（收集 588 项/2 skip）对不上**、`aggregate_only.py:82` 的 bug（不建目录就写——[R] 未找到 /opt/gpumachine 内调用方，风险降级但未归零）、72 vs 76 用例差的归因（权威 baseline 在 gov 侧可查）。☆

---

## 附：三腿输入报告路径与汇总人复核记录

- [S] `/home/pan-ding/workspace/agent协作平面/协作落实/任务1-机器现状盘点/step-router-v1/总报告.md`
- [M] `/home/pan-ding/workspace/agent协作平面/协作落实/任务1-机器现状盘点/MiniMax-M3.1-Flash/总报告.md`
- [G] `/home/pan-ding/workspace/agent协作平面/协作落实/任务1-机器现状盘点/GLM-5.3-Flash/总报告.md`
- [R] 汇总人只读复核记录：`/tmp/synth-t1/gov*.out`、`/tmp/synth-t1/anolis.out`、`/tmp/synth-t1/hk*.out`（执行时间 2026-10-05T06:18–06:30 UTC；全部命令均为只读——ls/ss/ps/systemctl show/grep/docker exec{psql,headscale list,temporal list}/curl{GET/health}/df/nvidia-smi/getent/dnf check-update/apt list/find/git remote -v{token 已 masked}/ufw status/journalctl 读取；**未修改任何远端状态、未执行任何修复动作**；唯一对外请求为本机对 gov/hk 端口的 TCP/TLS/HTTP GET 探测）。

*汇总完成 ｜ 2026-10-05 ｜ 汇总人-GLM-5.3 ｜ 唯一依据：三份腿总报告 + /tmp/synth-t1/ 下的本次只读复核记录*
