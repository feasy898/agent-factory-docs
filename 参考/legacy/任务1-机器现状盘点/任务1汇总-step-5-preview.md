# 任务 1 · 三机现状盘点 · 跨腿汇总报告

- **撰写人**：总报告汇总人（step-5-preview）
- **日期**：2026-10-05
- **输入（唯一依据）**：三条模型族腿的总报告全文
  1. `step-router-v1/总报告.md`（下称 **SR**）
  2. `MiniMax-M3.1-Flash/总报告.md`（下称 **MM**）
  3. `GLM-5.3-Flash/总报告.md`（下称 **GLM**）
- **对照方案**：`/home/pan-ding/workspace/agent协作平面/agent协作体系.txt`（HarnessOS，1474 行）
- **本汇总自己的只读复核**（不改远端状态，命令与输出见第 3 章各条与第 8 章附录）：`ssh root@anolis-gpu-01` / `root@governance-machine` / `root@hk-gateway`，全部为 ss / ps / stat / journalctl / df / free / top / nvidia-smi --query-gpu / docker exec headscale nodes list / dnf check-update / systemctl is-active|cat|show / tail / grep 这类只读命令。时间约为 2026-10-05 06:10–06:20 UTC（14:10–14:20 CST），**晚于三条腿各自的盘点窗口**。
- **证据强度纪律**：三腿标注【unconfirmed】【单方记录，未核实】的条目在本汇总中**原样保留该标注，不升格为已核实**。本汇总人只把"我自己跑通的只读命令输出"标为【本汇总复核】。

> ⚠️ **前提校正（三腿中只有一条腿发现并验证）**：把三台机器分工（governance-machine=治理面、anolis-gpu-01=开发机、hk-gateway=公网网关）当作"方案设想"是**任务设定，不是方案原文**。MM 总报告开篇用 `grep -nE "governance-machine|anolis|hk-gateway|100\.64\.0\.|159\.75|srv-?1"` 对方案全文得零命中；**本汇总人独立复现同一 grep（并把 `CloudCrane` 一并纳入），在 1474 行的 `agent协作体系.txt` 上同样零命中**。因此下文凡涉及"机器分工设想"一律标注为【任务设定】；方案的真实约束是 §9.5 目录树 / §9.1 数据存储 / §10 测试门禁 / §5/§6/§8 能力与协议层。

---

## 第 1 章　执行摘要（一个只看这一页的 owner 必须知道的 12 件事）

| # | 必须知道的事实 |
|---|---|
| 1 | **三机分工是任务设定，不是方案原文**：方案文件零命中任何机器名/IP（MM 发现，本汇总人 grep 复现）。所有"与设想差距"的结论都要按这条打折看。 |
| 2 | **只有 governance-machine 真的在承载治理栈**：15 个容器全 Up + 5 个自研 systemd 单元 + PG 治理库 + headscale 控制面；但它跑的是**另一套已落地的 CloudCrane / jiuwen_glue 命名体系**，方案 §9.5 的 `harnessos/` 目录树**三机零命中**（三腿一致）。 |
| 3 | **anolis-gpu-01 不是"待开发的开发机"，而是已投产的 agent 执行面**：jiuwenswarm AgentServer（自 2026-10-02 14:31）+ harness 8/8 模块 + PM/patrol 循环 + 1 个在跑 MCP（8125）+ 遥测；而 GPU 实际被 `/data/xdng` 语音业务占用（GPU1 15516/32768 MiB≈47%、利用率 0%），"开发机"定位与真实负载相反。 |
| 4 | **hk-gateway 的 agent 基础设施确实是零**（15 项核心组件 0/15），但**这符合它作为网络网关的定位**——SR 把它写成"与设想完全脱节"，MM/GLM 明确判断"治理面应落 governance-machine，hk 只承担 exit node + 代理"（硬约束：1.9 GiB / 2 vCPU / 无 SWAP / 无 GPU）。按 MM/GLM 的框架决策，别去给 hk 装治理组件。 |
| 5 | **【进行中】hk-gateway 的公网无鉴权 SOCKS5（gost :1080）正被 ≥6 个境外 IP 大规模滥用**：日志从 97M（MM）→203M（GLM 05:26）→**354M**，前一个实例 2h12m 内消耗 **20min20s CPU、峰值内存 619.1M**，load 一度 3.52（2 vCPU）；tailnet 内合法用户 mingda-website / windev-01 依赖此出口，不能简单封端口。**SR 完全未报此项（覆盖缺口）。** |
| 6 | **【盘点后变化】gost 的公网暴露面已被收窄**：本汇总人复核 `/etc/systemd/system/gost.service` 于 **05:56:54** 被改为 `-L socks5://100.64.0.3:1080`（仅 tailnet 监听），05:56:56 重启，日志停止增长，最后几条客户端为 `100.64.0.2`（合法）。**改动者不见于三腿任何一份报告，本汇总无法认定是谁、为何。** 但 7863 仍绑 `0.0.0.0` 公网可达、`warp-reroute.service` 仍 failed。 |
| 7 | **【进行中】三台机器的公网 22 全在被爆破且全无防护**：anolis 24h `Failed password` **22,722** 条、自 10-02 累计 41,182 条（本汇总人实测；MM 记 33,452，GLM 记 70,600/24h——口径差异见 3.6 条）；hk 约 927–1,000 次/小时、`PermitRootLogin yes` + `PasswordAuthentication yes`；**三台都没装 fail2ban、都没启用主机防火墙、iptables INPUT 策略 ACCEPT、全都没有 SWAP**。 |
| 8 | **governance-machine 的 auto-router 是"功能活着、编排层坏"**：systemd 单元 crash-loop，`NRestarts=27977` 且**仍在增长**（SR 27,195 / MM 27,211 / 本汇总 27,977），根因 `OSError: [Errno 98] Address already in use`；8777 由 **2026-10-03 21:14:07 手工 nohup 的孤儿进程 PID 3522460**（ppid 3522434，本汇总人复核 `ps`）顶着，`/health` 仍 200。 |
| 9 | **回归门禁今天是红的，而且"坏了没人知道"**：`/var/log/factory-tests/baseline-2026-10-05.json` 为 **total 72 / pass 49 / fail 5 / skip 18**（本汇总人读库复核），击穿方案自身"fail 只降不升"铁律；同时回归 fail 告警连续 3 天 `告警未送达 rc=3`、微信 OwnerGate 通道断 4 天。 |
| 10 | **governance-machine 资源已长期过载**：本汇总人实测 `loadavg 14.36 / 13.36 / 13.17`（8 核），`clickhouse` 容器 **492.3% CPU**，`free` 仅 1.7G，**零 SWAP**；anolis 数据盘 `/data` **84%（234G/295G）** 接近写满（三腿一致，本汇总人复核 df）。 |
| 11 | **方案真正要的四大件三机全无**：Jev 独立判别服务、Memory 向量库运行时、OwnerGate 实体、生产 MQ 承载（Temporal 服务端在跑但**零 worker**；Kafka/restate 只有镜像）；另有 `glue.artifact_route` 0 行、MinIO 无 artifact 桶（**该桶清单为 GLM 标注的【A 单方记录，未核实】**）、pgvector 未装、13 个 subagent 未落地。 |
| 12 | **跨机协同只被实证过一条，且方向与设想相反**：唯一实证是 anolis→gov 拉 merger 角色仓并跑通机器门禁（SR/MM/GLM 三腿都写"唯一被实证的跨机协同"）；gov 侧反而看不到 GPU 面（`glue.node` / `node_heartbeat` 各 1 行、回归 L3-08 记"GPU 机从未注册 node"）。好消息：**短时凭据链（OpenBao + vault-broker + anolis 零长期密钥/3 个 renew timer/tmpfs 现拉）是三机落地最好的一块**。 |

**整体健康度（三档分开，不合并总分）**
- **anolis-gpu-01：功能健康、安全不健康、定位偏移。** 执行链路在产，但公网 22 爆破 + 无防护、7 处 git remote 明文 token、`anuser NOPASSWD:ALL` 权限收敛失效、GPU 被业务占用、PM 循环 5 分钟空转掩盖 7 条产品线 103–105h 停滞。
- **governance-machine：基础设施健康、资源与治理面不健康。** 15 容器全 Up、治理数据有真实数据（team_task 38 等），但过载、auto-router 编排层坏、6 张治理表 0 行、通知链断裂。
- **hk-gateway：网络角色成立、安全紧急。** 只有 tailscaled/gost/sing-box/warp-svc 网络层功能；透明分流因 warp-reroute failed 整体不生效、exit node 零流量、开放代理被滥用。

---

## 第 2 章　跨腿一致结论清单

> 标注规则：**三腿**=三条腿独立得出；**两腿**=两条腿独立得出（写明哪两条）。凡本汇总人自己复核过的，标【本汇总复核】。

| # | 一致结论 | 一致腿 |
|---|---|---|
| 1 | 三台盘点机均可 SSH、tailnet `edgenet` 内互 ping 0% 丢包、各自公网出口正常（baidu 均 200） | 三腿 |
| 2 | tailnet `edgenet` 共 **8 节点**；控制面是**自建 headscale v0.29.3 容器，跑在 governance-machine**（SR 称盘点前约 1 小时被重建；GLM 记今天 11:37 hardened recreate）；用户 `edgenet` / `new-member` 存在（本汇总复核 `headscale users list` 证实） | 三腿 |
| 3 | **hk-gateway 与 anolis-gpu-01 之间无法直连**，只能走 DERP(hkg) 中继（157/69–82 ms，`direct connection not established`），是全 tailnet 最差一跳；hk→gov 反而是 direct | MM + GLM（SR 只写"高延迟通"，未提 DERP） |
| 4 | **hk-gateway 的 exit node 名不副实**：广播 `0.0.0.0/0,::/0`、`ip_forward=1`、MASQUERADE 在位，但 `ts-forward` / `ts-postrouting` / FORWARD 计数全 0 → 本次开机以来零 peer 流量经它做出口；gov / anolis 的 `tailscale debug prefs` 也无 exit node 路由 | MM + GLM（SR 未覆盖） |
| 5 | **hk `warp-reroute.service` failed**（`port 7863 not listening - refusing to arm redirect rules`，启动竞态）→ 透明域名分流整体不生效、兜底 `INPUT DROP` 未装、**7863 公网可达** | 三腿（本汇总复核：`systemctl is-active warp-reroute` = failed，`ss` 显示 7863 仍绑 0.0.0.0、Recv-Q=7） |
| 6 | **gov auto-router systemd 单元崩溃循环**（`Errno 98 Address already in use`），8777 被 2026-10-03 21:14 手工 `nohup` 孤儿进程 PID 3522460 顶替、`/health` 200、功能仍通 | 三腿（SR 只报 restart counter；MM/GLM 点名孤儿进程；本汇总复核 PID 3522460 / ppid 3522434 / started Oct 3 21:14:07 / `NRestarts=27977` 且 ActiveState=activating auto-restart） |
| 7 | **gov planner 处于 active running 但 LLM 网关通道降档**：日志"网关不可用，判定挂起""gateway 档 decision HTTP 401 降档"，任务 #26 挂起；SR 另记 `decision_queue` 积压 16 条、#11/#22/#23/#26 超 SLA | 三腿（GLM 13:13:50 复测仍在报） |
| 8 | **Temporal / 消息队列没有真正投产**：gov Temporal 1.28.1 前端 SERVING 但 **零 worker 连接**（established=0、namespace 仅 temporal-system）；anolis Temporal 4 镜像 0 容器、`qw_worker` 进程存活但日志停于 10-02（历史为"模拟提交"试点）；hk 无任何 MQ | 三腿 |
| 9 | **Memory / 向量库、Jev 独立判别服务、OwnerGate 实体，三机均无运行态**：chroma/faiss/milvus/qdrant/pgvector 全盘 0 命中；Jev 只有代码路径（gov `auto_router.py` 33 处命中 + anolis `wake-gate.py` 每 5 分钟实调百炼 `decision-model-preview`）；OwnerGate 只有等价物（gov 微信/challenge 表 0 行/vault-broker，anolis PM agent + `gatekeeper.yaml` status:defined，hk `upload_server.py` 雏形未运行） | 三腿 |
| 10 | **三台都没有 fail2ban、都没有启用主机防火墙、iptables INPUT 策略 ACCEPT**；anolis/gov SELinux Disabled，hk 只有 AppArmor；anolis `fail2ban` 客户端不存在（MM 仲裁"未安装"，本汇总复核 `command -v fail2ban-client` 无输出） | 三腿 |
| 11 | **三台都没有 SWAP**（`swapon --show` 空，本汇总在 gov / anolis 复核为 0 行） | 三腿 |
| 12 | **gov 资源长期过载**：8 核 load 13–19（本汇总实测 `loadavg 14.36/13.36/13.17`），元凶 `company-clickhouse-1` 常驻 460–513% CPU（本汇总实测 492.3%），瞬时 free 低至 159MB（本汇总实测 free 1747MB / 15603MB total） | MM + GLM（SR 未量化负载） |
| 13 | **anolis 数据盘 `/data` 84%（234G/295G）接近饱和**，大户 `night` 99G / `xdng` 58G / `beaneye-datasets` 37G / `hf` 25G；系统盘 98G(62%) | 三腿（本汇总复核 `df -h /data` = 234G/295G 84%） |
| 14 | **回归门禁今天是红的：49 pass / 5 fail / 18 skip（total 72）**，failing `L1-03 L3-05 L4-10 L6-01 L6-09`，锚点 53/4/19 → fail 由 4 升 5，**违反方案 §10.4「fail 只降不升」铁律**；anolis patrol 读到同一组数字（PAT-04 warn） | MM + GLM（SR 记为"65 用例跑通"——见矛盾 D2；本汇总复核 `baseline-2026-10-05.json`：`"total": 72, "pass": 49, "fail": 5, "skip": 18`） |
| 15 | **方案 §9.5 的 `harnessos/` 目录树三机零命中**，实机是另一套命名体系（gov 的 CloudCrane `kernel/`+`jiuwen_glue`，anolis 的 `/opt/gpumachine/`）→ "双实现风险，需 owner 架构级裁定"；gov 侧明说"真相源→实机走 PR 正向通道尚未建立" | 三腿 |
| 16 | **短时凭据链是三机最落实的一块**：gov OpenBao 2.6.2 healthy + vault-broker 8310 + CNB token 经 OpenBao 零落盘；anolis 执行面零长期密钥（`gpumachine-bao-env` oneshot 现拉 tmpfs + 3 个 renew timer + 0600）；**唯一破口是 anolis 7 处 git remote 明文 token** | 三腿 |

---

## 第 3 章　腿间矛盾与可信度判断

> 格式：**矛盾内容 ｜ 各腿说法 ｜ 采信判断与理由**。标【本汇总复核】的是我自己跑的只读命令。

### D1　"三机分工"是方案原文还是任务设定
- **SR**：直接作为"方案设想角色"写进对照表（SR 总报告 §4 开头），并把"hk 15 项核心组件全部未部署"表述为"与设想完全脱节"。
- **MM**：开篇即声明这是**任务设定而非方案原文**，并给出 grep 零命中的证据；据此主张"hk 只应承担 exit node + 代理，治理面应落 governance-machine"。
- **GLM**：混用"方案/任务设想"两说，未做 grep 验证。
- **采信 MM。** 理由：本汇总人独立对 `agent协作体系.txt`（1474 行）执行 `grep -nE "governance-machine|anolis|hk-gateway|100\.64\.0\.|159\.75|srv-?1|CloudCrane"`，**零命中**（连 `CloudCrane` 也不在方案文本内）。结论：凡"机器分工与设想差距"的论断只能当任务设定的对照，不能当方案违约；SR 的"脱节"表述会误导 owner 去给 hk 装治理组件。

### D2　回归门禁的用例数与红绿状态
- **SR**：65 个用例、cron 每日 06:00 自动跑、baseline 已产出 → 结论"跑通 ✅"（SR §3.1.5 / 跑通表 #34）。**未提任何 fail。**
- **MM**：实跑 **72 例 = 49 pass / 5 fail / 18 skip**，与 06:00 定时基线逐字节一致；另有 kernel pytest 184 例全绿；方案 §10 写 76 例；anolis `role.json` 自述 76 例而实测 72 例（差 4 例未归因）。
- **GLM**：gov `tests/cases` **66 个文件**（报告口径 72 用例），今日 12:17 基线 49P/5F/18S 并给出 5 个 fail 明细；anolis `cases/` 70 个 `.sh`（同一口径 72 用例）。
- **采信 MM + GLM。** 理由：本汇总人复核 `/opt/factory-tests/tests/cases/` 文件数 = **66**（`ls | wc -l`），并读 `/var/log/factory-tests/baseline-2026-10-05.json` 得 `"total": 72, "pass": 49, "fail": 5, "skip": 18`、`generated_at: 2026-10-05 06:00:01 +0800`、`host: VM-0-6-opencloudos`。SR 的"65"与"跑通"两处都不成立（既未对上文件数，也漏掉了 5 个 fail）。case 数三套口径（66 文件 / 72 用例 / 76 设计值）留作遗留问题。

### D3　governance-machine 待更新包数量
- **SR**：40+ 个待更包。
- **MM**：**96 个**（已仲裁：A 的 198 是输出行数，B 正确）；`--security` 分类未做。
- **GLM**：**96 个**（一致，未复测）。
- **采信 96。** 理由：本汇总人跑 `dnf -q check-update | awk '{print $1}' | grep -c "."` = **97**（两腿各自内部已仲裁过口径，且与我的实测吻合到 1 个以内）。SR 的 40+ 明显偏低，疑为不同命令口径或截断。

### D4　anolis-gpu-01 待更新 / 安全公告数量
- **SR**：264 行安全公告（含 1 Critical，来自 B 的 `dnf updateinfo list-security | wc -l`）；A 另称 90 security。
- **MM**：仅"≥20 包（清单被 `head -20` 截断）"，并明确**安全更新条数未取到**（`dnf updateinfo list-security` 参数不支持）。
- **GLM**：**125**（已仲裁 D9：A 121、B ~125）。
- **采信 GLM 的 125 作为"待更新包数"口径；SR 的 264/90 是"安全公告行数/per-security 条目"口径，量纲不同，不与 125 直接比较。** 理由：本汇总人实测 `dnf -q check-update | grep -c "^\S"` = **121**，与 GLM 的 121–125 区间吻合。**"含 1 Critical"一条来自 SR 转引，未见其他两腿确认，保留为待复核。**

### D5　anolis-gpu-01 是否有一个在跑的 MCP server（agent-browser :8125）
- **SR**：anolis MCP server ❌ **未发现**（SR §3.2.4 表 / 跑通表 #43）。
- **MM**：anolis MCP server ❌ **未发现**（A §6.1 / B §6.8）；其 anolis 服务清单里完全没有 agent-browser。
- **GLM**：anolis MCP ✅ **1 个在跑**：`agent_browser.server` 绑 100.64.0.7:8125（仅 tailnet），pid 550568 自 Sep30，`ss`+`ps`+`curl` 三重确认；另有 `coldstart/mcp/fs_server.py` 备用未运行。
- **采信 GLM。** 理由：本汇总人复核 `ss -ltnp` 显示 `LISTEN 100.64.0.7:8125 users:(("python",pid=550568,fd=3))`，且 `ps -p 550568` = `anuser /opt/gpumachine/agent-browser/venv/bin/python -m agent_browser.server`（elapsed 4-19:30:31）。**SR/MM 的 anolis 盘点属搜索口径漏检**（很可能只 grep 了 `mcp` 关键词而没看监听端口）。这一条直接影响"方案 MCP Pool 是否 0 落地"的结论：anolis 至少有 1 个 HTTP 形态 MCP 在跑，只是无集中 MCP Pool。

### D6　anolis-gpu-01 SSH 爆破的量级
- **SR**：**未量化**（只写 22 端口对公网开放、无爆破防护）。
- **MM**：全 journal 口径自 10-02 起 **33,452** 次（10-02 5,474 / 10-03 7,447 / 10-04 12,589 / 10-05 7,919），并自注**未完全仲裁 A 的 22,430 与本轮 33,452 的 11,022 差额**；`journalctl -u sshd` 口径只有 979。
- **GLM**：**24h sshd 登录失败审计 70,600 条**（标为本腿合并新增实测）。
- **采信"每日数万次、持续增长"，但三个数字不可互换，引用必须带口径。** 理由：本汇总人实测 ① `journalctl --since "24 hours ago" | grep -c "Failed password"` = **22,722**；② `--since "2026-10-02"` = **41,182**；③ 24h `grep -ciE "Failed password|Invalid user"` = **43,667**。可见 MM 的 33,452 与我的 41,182 同属一个量级（窗口都是"自 10-02"），**GLM 的 70,600 无法用 `Failed password` 口径复现**，应属更宽的行匹配口径。三腿不构成事实冲突，但 GLM 数字引用时须注明是宽口径。

### D7　headscale 在册节点数是 7 还是 8（pandev-comp 是否在册）
- **MM**：`tailscale status` 8 节点 vs headscale 登记 **7 节点**，`pandev-comp`（100.64.0.8）**不在 headscale 中、原因未查**（列为合并员新发现）。
- **GLM**：headscale **8 节点在册**。
- **SR**：只说 tailnet 8 节点、headscale 两用户存在，未给在册节点数。
- **采信 GLM。** 理由：本汇总人 `docker exec company-headscale-1 headscale nodes list` 输出的 IP 列为 `100.64.0.1 .2 .3 .4 .5 .6 .7 .8` **八个齐全**（且 `grep -c "100.64.0.8"` = 1）。MM 的"差集"不成立，其"pandev-comp 不在 headscale"属误判。另我复核 `headscale users list` = `edgenet` + `new-member`（与 SR 一致）。

### D8　hk-gateway → anolis-gpu-01 的链路性质
- **SR**：互通表写"通，95–505 ms（高延迟）"、另处"~105 ms"（引 hk 合并 §2.4）。
- **MM**：**仅 DERP(hkg) 中继，157/77/138 ms，`direct connection not established`**，并判读"本 tailnet 最差一跳，即使启用 exit node，gpu 机到网关也是绕路"。
- **GLM**：ping 108.4/103.5/166 ms 通；`tailscale ping` 经 DERP(hkg) 69–82 ms，direct 未建立。
- **采信 MM + GLM。** 理由：两条腿独立给出"直连未建立 + DERP 中继"的机制性结论，且互相印证；SR 只给了延迟数、漏掉了机制。差异在 105 vs 157 ms 属时点/测法差异，不影响结论。

### D9　tailnet 节点的瞬时状态（hk-gateway / windev-01 / mingda-website）
- **SR**：以 gov 仲裁口径记 **hk-gateway = idle**、windev-01 = active、cloudpc-01/harmony-vm/windev-01 offline 的说法与其他行矛盾（其表把 windev-01 同时写成 offline）。
- **MM**：hk-gateway = **active**；windev-01 offline（引 gov SYSTEM-GUIDE"10-07 销毁"）；mingda-website online。
- **GLM**：hk active；windev-01 / mingda-website 均标注"时变（A/B/复核时不一致）"。
- **判定：这是时点快照差异，不是事实冲突，任何"某节点在线/离线"的结论都不能当稳定事实。** 本汇总人在 06:12 UTC 从 gov 复核 `tailscale status`：`hk-gateway … idle; offers exit node`、`windev-01 … idle`、`mingda-website … -`（在线）、`cloudpc-01 offline 12d`、`harmony-vm offline 25d`。可稳定的只有：**cloudpc-01 离线 ~12 天、harmony-vm 离线 ~25 天且 headscale `Expired=yes`，windev-01 在 online/offline 之间反复漂移。**

### D10　hk-gateway 公网 github / pypi 是否"25s 稳定极慢"
- **MM**：github 与 pypi 均为 `t=25.000x s` 的稳定极慢（同时 baidu 0.65–2.84s），已仲裁"是极慢不是不通"，**根因未定位**。
- **GLM**：github 200（3.5s）"B 的挂起现象不复现【已仲裁】"、cloudflare 200（3.6s）不复现；另测 huggingface.co 直连 200 但 12.0s 极慢。
- **判定：无法裁定时点性差异。** GLM 的复现更快不能排除 MM 时点的拥塞（hk 当时正被滥用压到 load 3.52），MM 的"稳定 25s"也不能证明现在仍如此。可确认的共同结论只有：**hk 到 github/pypi 等站点存在慢或挂起，但非不通；根因三方都未定位。**

### D11　governance-machine 上有几个 agent CLI
- **SR**：只有 **openclaw**（`/usr/bin/openclaw`）。
- **MM**：**4 个**：`openclaw` / `mcode` / `kimi` / `mavis-trash`（均在全局 PATH 首段，已仲裁 A 正确）。
- **GLM**：`openclaw`（gateway 18789 常驻）+ **`minimax-code` ×3 实例**（非 PATH 命令、node 实现，pgrep 实测 3 个 PID）。
- **判定：不可归约，作为口径差异处理。** 三腿一致的是"openclaw gateway 是常驻主通道、zcode/claude/qwen/gemini/codex 等均未装"；不一致在"除 openclaw 外还有几个 agent 工具"（SR 1 个 / MM 4 个 CLI / GLM 1+3 进程）。本汇总未复核 PATH CLI 清单，列为遗留问题；不影响 anolis/hk"零 agent CLI"的结论。

### D12　MinIO 桶清单的证据强度
- **MM**：作为事实写"MinIO **只有 `langfuse` 桶，无 artifact 桶**"。
- **GLM**：同一条事实标注**【A 单方记录，未核实】**（A 探到，B 未探）。
- **SR**：只写 MinIO 容器存在，未列桶。
- **保留 GLM 的未核实标注，不得升格。** 本汇总人未复核（`mc` 不在宿主机 PATH、鉴权未打通，GLM 已记为未覆盖项）。该条支撑"Artifact 存储层未启用"的结论，但单独引用时须带【单方记录，未核实】。

### D13　gov load 的主因构成
- **SR**：未量化负载。
- **MM**：load 13–19 的"唯一主因"是 `company-clickhouse-1` 常驻 460–513% CPU；同时单列 `console_tui` 99.8%（自 10-01，累计 5938 分钟，疑似忙循环）。
- **GLM**：clickhouse 453% + **console_tui 99.8% 疑似忙循环**，并把"console_tui + clickhouse"并列为 load 13+ 的原因。
- **采信"ClickHouse 是最大单因"（可佐证），console_tui 一条按【单方/未证实】处理。** 理由：本汇总人 `top -bn1` 实测 `clickho+` = **492.3% CPU**（另有 node 进程 92.3%、python 92.3%），与两腿的 460–513% 吻合；但 top 中 92.3% 的 `python` 进程我无法确认就是 console_tui，故 console_tui 的忙循环判断维持原标注，**ClickHouse 高 CPU 的根因两腿都未查明（疑似 MV 刷新/高频 trace 写入）**。

### D14　hk-gateway 公网滥用是否仍在进行（跨时点）
- **三条腿各自窗口内**都确认"进行中"：MM 🔴 极高项"盘点期间仍有新会话"；GLM"13 分钟 +65MB、load 升至 3.5、外部占比 ~91.5%"；**SR 完全未报 gost 滥用**（只写了 warp-reroute 与 sing-box too many open files）。
- **本汇总人 06:13–06:15 UTC 复核（晚于三腿窗口）**：`/etc/systemd/system/gost.service` mtime = **2026-10-05 05:56:54**，内容为 `ExecStart=/usr/local/bin/gost -L socks5://100.64.0.3:1080`；进程 PID 25418 started 05:56:55；`stat` 显示 `gost.log` 60 秒内字节数不变（370,841,108，最后写入 06:13:46）；`ss` 显示 1080 只绑 `100.64.0.3`；日志最后几条的 client 是 `100.64.0.2`（tailnet 内）。
- **判定：公网暴露面在三腿盘点后已被收窄（约 05:56 由未知操作者完成），但"滥用曾经且正在造成损害"这一事实成立，且未完全收尾。** 证据：上一个实例的 journal 记 `Consumed 20min 20.216s CPU time, 619.1M memory peak`（约 03:44–05:56 的 2h12m 内），`gost.log` 已达 **354M / 1,197,607 行且无 logrotate**，load 现在仍 2.39/2.48/2.70（2 vCPU）；同时 7863 仍绑 `0.0.0.0`、`warp-reroute.service` 仍 failed。**谁改的 unit 不见于任何一腿，我无法认定，也不应猜测。**

### D15　anolis `jiuwenswarm-app` / docker 的 enabled 状态
- **SR**：保留 A/B 分歧未仲裁（docker enabled：disabled vs enabled；jiuwenswarm enabled：disabled vs enabled）。
- **MM**：已仲裁——`jiuwenswarm-app` active running，ActiveEnter 10-02 14:31，`Restart=on-failure`。
- **GLM**：已仲裁，active since 2026-10-02 14:31:31 CST，MainPID=1056349、18092 监听子进程=1056366。
- **采信 MM + GLM。** 本汇总人 `ss -ltnp` 显示 `127.0.0.1:18092 users:(("python3",pid=1056366,fd=13))`，与 GLM 的 PID 完全一致 → jiuwenswarm 确实在跑。SR 的"未仲裁"属其腿内未闭环，不构成跨腿事实冲突。

### D16　hk-gateway 的公网可解析性（MagicDNS）
- **SR**：未提及。
- **MM**：未提及。
- **GLM**：hk 上 MagicDNS 主机名解析不可用（`accept-dns=false` / `CorpDNS=false`，`tailscale dns status` = disabled，按名 ping anolis 失败）【一致】。
- **保留为 GLM 单腿发现**（不与其他两腿冲突，但缺独立印证）。影响：hk 上任何按主机名寻址 tailnet 成员的运维动作都会失败。

---

## 第 4 章　三台机器 × 关键维度现状矩阵

> 每格一句话；证据强度以最弱的那条腿标注为准。

| 维度 | anolis-gpu-01 | governance-machine | hk-gateway |
|---|---|---|---|
| **agent 基础设施落地** | 执行面在产但用另一套命名：`/opt/gpumachine/`（harness 8/8 模块导入成功、roles/planner+patrol、PM 循环、1 个在跑 MCP :8125、契约 `registry.json` 静态件）；`harnessos/` 零命中；Memory 无向量、OwnerGate 无实体、Temporal 无容器 | 治理栈最全：15 容器 + PG `jiuwen_team`（glue 24 表 + 14 视图）+ Higress/auto-router + OpenBao/vault-broker + 回归门禁 + headscale；但 `harnessos/` 零命中，跑的是 CloudCrane/jiuwen_glue；6 张治理表 0 行、pgvector 未装、MCP 无运行实例、Jev 无服务 | 15 项核心组件 0/15：无数据库、无 MQ、无 LLM 网关、无 agent CLI、无 SDK；只有 `/srv/inbox/upload_server.py`（未运行）与 `/srv/git/ohos-tailscale.git` 裸仓两个协作雏形 |
| **在跑服务** | 23 个 systemd running + `jiuwenswarm-app`（18092，10-02 起）+ 4 个无托管的 xdng 循环服务 + 1 个 otel 容器（Up 7 天）+ 4 条 anuser cron（patrol 每 2h、PM 每 5 分钟） | 15 容器全 Up、RestartCount=0，7 个 healthy；5 个自研单元 active（factory-board/planner/vault-broker/peidian-agent/openclaw）+ auto-router **编排层崩溃**；20 条 cron 承载全部自研自动化 | 21 个 running：gost/sing-box/warp-svc/tailscaled/ssh/hk-nat；**warp-reroute failed**；无 docker/k8s/任何中间件 |
| **安全** | 最不健康：公网 22 持续爆破（24h 22,722 条 Failed password，本汇总实测）、无 fail2ban、INPUT ACCEPT、7 处 git remote 明文 token、`anuser NOPASSWD:ALL` + 5 身份可免密进 anuser；root 免密仅依赖 Tailscale SSH（acl 粒度未查） | 免密 sudo 双路径（`lighthouse NOPASSWD:ALL` + root drop-in）、`PermitRootLogin yes` + `PasswordAuthentication yes` + 7 把公钥、无 fail2ban/防火墙、**8300/8310/8787 绑 0.0.0.0 且鉴权状态未知**（本汇总实测三端口确为 0.0.0.0）；正面：vault-broker 非 root + 最小权限、planner 只读+私有 tmpfs | 最紧急：gost 公网无鉴权 SOCKS5 被 ≥6 境外 IP 滥用（354M 日志、峰值 619M 内存，本汇总实测）、22 爆破 ~927–1,000 次/小时、7863 公网可达、成功登录从未排查；正面：AppArmor 134 profiles、NTP、unattended-upgrades 已启用 |
| **资源** | 16 核/125 GiB、无 SWAP；load 低（本汇总实测 0.55）；`/data` **84%（234G/295G）** 接近满；GPU1 被语音业务占 15516/32768 MiB≈47%、利用率 0%，GPU0 310 MiB | 8 核/15 GiB、**无 SWAP**；load 13+（本汇总实测 loadavg 14.36/13.36/13.17、clickhouse 492.3% CPU）、free 仅 1.7G → OOM 风险实在；盘 38% | 2 vCPU/1.9 GiB/无 SWAP/无 GPU；被滥用压到 load 2.4–3.5（本汇总实测 2.39）；盘 30G 但 `/var/log` 已 2.1G、`gost.log` 354M 且无轮转 → 数日内有挤压根分区风险 |
| **网络** | tailnet active；→gov 30 ms 直连、→hk 129 ms、→pandev 44 ms；境外直连不通（google 12s 超时、HF 直连 DNS 污染、走 hf-mirror 200）；本机不承载 PG/Redis/Temporal（都在 gov） | tailnet online + **headscale 控制面所在机**；→三机全通；境外直连全断（GitHub/Google/OpenAI/HF）→ 两个 GitHub remote 的可达性未证实；443 TLS 握手失败 rc=35（MM 单腿，三次一致）；公网 IPv4 159.75.21.149（MM/GLM 均记 gov↔hk 直连走该地址） | tailnet active、offers exit node 但**零 peer 流量**；→anolis 只能走 DERP(hkg)；显式代理 7864 实测通（含 WARP 路径），透明分流因 warp-reroute failed 整体不装；两条回传通道（8090/9418）全关、HMTOKEN 无取值来源 |

---

## 第 5 章　高危问题统一清单（三腿合并去重，按紧急度排序）

### A. 正在造成损害（active / ongoing）

| # | 问题 | 范围 | 证据（腿 + 本汇总复核） |
|---|---|---|---|
| A1 | **hk-gateway 公网无鉴权 SOCKS5（gost :1080）被大规模持续滥用**：≥6 个境外 IP、外部占比 ~91.5%、分钟级加速、盘点期间仍新增会话；tailnet 内 `100.64.0.2`（28,370+ 条）与 windev-01（10,002 条）是合法用户，处置需同时给它们换出口 | hk | MM §12 极高项 + §10#29；GLM §8① + 总表 #45【已核实-单方】；本汇总：`gost.log` 354M/1,197,607 行、上一实例 `Consumed 20min20s CPU, 619.1M memory peak`、`ss` 显示公网监听已于 05:56 收窄到 100.64.0.3。**SR 未报此项。** |
| A2 | **anolis-gpu-01 公网 22 持续爆破**：24h `Failed password` 22,722 条、自 10-02 41,182 条，日增；无 fail2ban、无封禁机制、INPUT ACCEPT | anolis | MM §3.1.6 P0（33,452）；GLM §3.2 安全（70,600/24h，宽口径）；本汇总实测 22,722 / 41,182 / 43,667（三口径并列）。SR 未量化 |
| A3 | **hk-gateway 公网 22 持续爆破 + root 口令登录开放**：~927–1,000 次/小时；`PermitRootLogin yes` + `PasswordAuthentication yes` + 6 把公钥 + fail2ban 未装 + 全 ACCEPT | hk | MM §3.3.5；GLM §3.3 安全②（auth.log 11,151 条仍在增长）；SR 仅记"sshd 公网 open" |
| A4 | **hk 7863（sing-box redirect 入站）公网可达**：`warp-reroute.service` failed 导致兜底 `INPUT DROP` 未装；已出现 `too many open files` ×2、Recv-Q 有积压 | hk | 三腿一致；本汇总实测 `ss` = `0.0.0.0:7863`、Recv-Q=7、`warp-reroute` 仍 failed |
| A5 | **governance-machine 资源长期过载**：`loadavg 14.36/13.36/13.17`（8 核）、clickhouse 492.3% CPU、free 1.7G、**零 SWAP** → OOM 与调度饥饿风险实在 | gov | MM §3.2.2；GLM §3.1 基本面；本汇总实测 `/proc/loadavg`、`top -bn1`、`free -m`、`swapon --show` 空 |
| A6 | **gov auto-router 编排层持续崩溃**：`NRestarts=27977` 且仍在涨（SR 27,195 / MM 27,211 / 本汇总 27,977），每次重启需人工干预，并以约每小时数百条污染 journal | gov | 三腿一致；本汇总实测 `systemctl show auto-router` = `NRestarts=27977, ActiveState=activating, SubState=auto-restart, ExecMainStatus=1` |
| A7 | **hk gost.log 无轮转且已 354M**，按当前速率数日内可能挤压根分区（30G 盘，根分区 26% 基线，`/var/log` 已 2.1G） | hk | MM §3.3.5；GLM §3.3 安全①；本汇总实测 `stat` = 370,841,108 字节 |

### B. 会造成损害（隐患 / 未爆，但一旦触发即重大）

| # | 问题 | 范围 | 证据 |
|---|---|---|---|
| B1 | **gov 8300（factory-board）/ 8310（vault-broker）/ 8787 绑 0.0.0.0，主机无入站白名单，鉴权状态未知**——两个是凭据/协作敏感端口，合并员列为最高优先级盲区 | gov | MM §3.2.4/§10.2 盲区#1；GLM §3.1 网络；本汇总实测三端口确为 `0.0.0.0` 监听 |
| B2 | **anolis 7 个 git remote URL 内嵌明文 token**（6×github + 1×cnb，违反 AGENTS.md 红线第 1 条）；**token 是否已失效/已 push/在历史提交中——三腿都没查** | anolis | MM §3.1.6 P0；GLM §3.2 密钥卫生（`qw-arena2` cnb remote 内嵌凭据）；SR §1 #6 |
| B3 | **免密 sudo 提权面**：anolis `anuser ALL=(ALL) NOPASSWD:ALL` + 5 个身份可免密进 anuser（其中 `harmony-host` 所属节点已离线 25 天）；gov `lighthouse NOPASSWD:ALL` + root drop-in；**Tailscale ACL 粒度三腿都没查**（anolis root 免密完全依赖它） | anolis / gov | MM §3.1.6/§3.2.9；GLM §3.1/§3.2 安全；SR §1 #6；ACL 空洞三腿一致列为最大盲区 |
| B4 | **gov 观测与告警链"活着但送不到人"**：微信 OwnerGate 通道最近送达 2026-10-01（断 4 天），回归 fail 告警连续三天 `告警未送达 rc=3`；门禁 fail 由 4 升 5 已 3 天无人处置 | gov | MM §7.4.1/§6.1#13；GLM §3.1 专项⑫⑬；SR §1 #11（口径为"通道部分"） |
| B5 | **anolis 数据盘 `/data` 84%（234G/295G）**接近写满，大户 `night` 99G；无 SWAP 兜底 | anolis | 三腿一致；本汇总实测 `df -h /data` |
| B6 | **治理语义双实现**：`harnessos/` 三机零命中，实机是 CloudCrane/jiuwen_glue 另一套命名 → 需 owner 架构级裁定；同时"真相源→实机走 PR 正向通道尚未建立"（运维窗 ≤2026-10-05 到期仍未闭环）+ github.com 本机不通 + company-ops 双副本漂移 | gov / 全局 | 三腿一致 |
| B7 | **hk 两条结果回传通道全关**：`/srv/inbox/upload_server.py`（无 8090 监听、无 unit、`HMTOKEN` 无取值来源，即使启动也会 fallback 到字面量 "unset"；8090 若补 unit 必须同时加访问控制）与 `git://` 9418（无监听、无 git-daemon）→ 外部无法拉取唯一代码资产 `/srv/git/ohos-tailscale.git`（bare、无 `[remote]`） | hk | MM §3.3.3；GLM §3.3 代码与工作区；SR §3.3.3 |
| B8 | **gov 443 TLS 握手失败（`curl -sk https://127.0.0.1/` → rc=35，三次一致）**，回归 L0-12 已 skip 登记；`Caddyfile` 全文三方都没读到 | gov | MM §2.7/§7.1#31（单腿，未被他腿复核） |
| B9 | **gov compose 引用 `${OTLP_BEARER_TOKEN}` 但未设置**（默认空串）→ OTLP 收端口认证形同虚设 | gov | MM §3.2.3/§7.1#50（单腿） |
| B10 | **治理数据层"表就绪、零行"**：`artifact_route / challenge / message_receipt / rule_violation / promotion_record / capability_version` 6 张表 0 行；MinIO 无 artifact 桶（**【单方记录，未核实】**）；Temporal 零 worker；Kafka 只有空壳目录 | gov | MM §3.2.6；GLM §3.1 专项②⑥；SR §3.1.4 |
| B11 | **anolis 5 个业务服务（8125/9001–9004）无 systemd、无 Restart、无自愈**；PM 循环 5 分钟空转热循环（457 份报告/1272 条判定），**掩盖了 7 条产品线 103–105h 全停滞** | anolis | MM §3.1.3/§3.1.7；GLM §3.2 专项⑬；SR §3.2.2 |

### C. 隐患（中期 / 结构性）

| # | 问题 | 证据 |
|---|---|---|
| C1 | 方案四大件（Jev 独立服务、Memory 向量库、OwnerGate 实体、生产 MQ 承载）三机全无；Jev 只有代码路径（gov `auto_router.py` 33 处命中、anolis `wake-gate.py` 调百炼通用模型），§8.2 的 13–16 个接入位一个未接 | 三腿一致 |
| C2 | 13 个运行时 subagent 未落地；现有"角色"是两套不同语义（gov 仅 merger 瞬态；anolis planner/patrol 是 PM/巡检角色） | 三腿一致 |
| C3 | 回归门禁三套数字并存：方案 §10 写 76、实测 72（gov 66 文件 / anolis 70 文件）、kernel pytest 184；**76 vs 72 差 4 例未归因**；黄金用例本体三腿都没跑（需凭据+LLM 预算） | MM + GLM（SR 记 65）；本汇总实测 gov cases = 66 文件、baseline total = 72 |
| C4 | 安全更新积压：gov 96–97、hk 123–124、anolis 121–125（含 SR 记的 1 Critical 待复核）；三腿都未做 `--security` 分类 | 三腿（口径见矛盾 D3/D4） |
| C5 | 备份从未做恢复演练、备份内容有效性未证实；hk 唯一代码资产无 remote、无备份 | MM + GLM |
| C6 | gov 5 个僵尸进程、`/opt/company/data/kafka`·`restate`·`tb` 无主遗留目录、大量 `.bak`（含凭据备份）、两仓各 20+ 处未提交改动 | MM + GLM |
| C7 | 日志与卫生：gov auto-router 每小时数百条污染 journal；hk `journald.conf` 无 `SystemMaxUse`、`gost.log` 无轮转；anolis journal persistent 1.2G 但有 8 天历史缺口（且观察到矛盾，需重查） | 三腿 |
| C8 | 两条腿都出现"同一时刻数字"（anolis patrol 04:17–04:19Z 与 gov 基线 12:17:02/12:19:38 吻合、PAT-04 note 的 host=VM-0-6-opencloudos），关系未说明 | MM + GLM |

---

## 第 6 章　跑通 / 跑不通总表（跨腿去重合并）

> 结果符号：✅ 跑通 ｜ ❌ 跑不通/未运行 ｜ ⚠️ 部分/待确认。"出处腿"=给出该结论的腿；标 **★** 的表示本汇总人亲自复核过。

### 6.1 跑通

| # | 对象 | 结果 | 关键口径 | 出处腿 |
|---|---|---|---|---|
| 1 | SSH 登录三机 | ✅ | root 免密（anolis 走 Tailscale SSH，gov/hk root 直登） | 三腿 ★ |
| 2 | 系统与资源基本面 | ✅ | OS/内核/CPU/内存/磁盘/GPU 均核实 | 三腿 ★ |
| 3 | tailnet 控制面 | ✅ | 自建 headscale v0.29.3 容器在 gov，8 节点在册，`edgenet`+`new-member` 两用户 | 三腿 ★ |
| 4 | 三机 tailnet 互 ping | ✅ | 0% 丢包；→gov 30 ms、→hk 108–137 ms、→pandev 44 ms | 三腿 ★ |
| 5 | 三机 SSH 22 互通 | ✅ | gov↔anolis / gov↔hk OPEN | 三腿 |
| 6 | 三机公网出口 | ✅ | baidu 200；**hk 是唯一境外可达的一台**（google/github 200） | 三腿 |
| 7 | 防火墙/iptables 规则可读 | ✅ | 策略已核实（但 INPUT ACCEPT，见高危） | 三腿 ★ |
| 8 | gov 15 个容器 | ✅ | 全 Up、RestartCount=0、7 个 healthy | 三腿 ★ |
| 9 | gov 自研进程服务 | ✅ | factory-board / planner / vault-broker / peidian-agent / openclaw gateway 均有 HTTP 响应 | 三腿 ★ |
| 10 | gov PG 治理库 | ✅ | `jiuwen_team`（glue 24 表 + 14 视图）、team_task 38 / event_log 84 / decision_record 4 | 三腿 |
| 11 | gov OpenBao | ✅ | healthy、initialized、8200 经 Caddy 仅 tailnet 发布 | 三腿 |
| 12 | gov Higress / auto-router 功能 | ✅ | :8080 200；:8777 `/health` 200 v9.0-tiering（**编排层坏，见 6.2**） | 三腿 ★ |
| 13 | gov Temporal 前端 / Langfuse UI / factory-board / vault-broker HTTP | ✅ | 200（`/` 404 仅路径不同，非故障） | 三腿 |
| 14 | gov 观测链 | ✅ | otelcol → Langfuse → ClickHouse 14 张表、`events_core` 40555 行 | MM + GLM |
| 15 | gov 回归门禁可实跑 | ✅（但结果为红） | 72 例 / kernel 184 例均可跑，cron 每日 06:00 | MM + GLM ★ |
| 16 | anolis JiuWenSwarm AgentServer | ✅ | active 自 10-02 14:31，127.0.0.1:18092，`/health` 426（纯 WS，非故障） | 三腿 ★ |
| 17 | anolis harness 模块冒烟 | ✅ | 8/8 模块导入成功（在隔离副本上，原目录未触碰）；eval-gate 108/108 全绿 | MM + GLM |
| 18 | anolis xdng 四推理服务 | ✅ | 9001–9004 健康（9004 是转往 gov Higress 的 shim，`cuda_available:false`） | MM + GLM ★ |
| 19 | anolis 在跑的 MCP server | ✅ | `agent_browser.server` 100.64.0.7:8125（仅 tailnet），pid 550568 | GLM ★（SR/MM 未发现，见 D5） |
| 20 | anolis patrol / PM 循环 | ✅（在跑，但结果红/空转） | patrol 每 2h rc=0；wake-gate / pm-loop 每 5 分钟 | 三腿 |
| 21 | anolis OpenBao 远端消费 | ✅ | 100.64.0.6:8200 OPEN + 3 个 renew timer 在轮转 | 三腿 ★ |
| 22 | anolis → gov 跨机通道 | ✅ | PG 5432 OPEN（双通道：`TEAM_PG_DSN` 直连 + `srv1-gov` SSH 别名）、7233 OPEN、4317 遥测 | 三腿 ★ |
| 23 | 唯一被实证的跨机协同 | ✅ | anolis 克隆 gov merger 角色仓并跑通机器门禁（"机器门禁过 20261002T201713Z"提交） | 三腿 |
| 24 | hk gost / sing-box:7864 / warp-svc | ✅ | 显式代理链路实测通（含 WARP 路径 trace warp=on colo=HKG） | 三腿 ★ |
| 25 | hk exit node 配置层 | ✅（但零使用） | `ip_forward=1`、MASQUERADE 在位、`ExitNodeOption=True`、控制面可见 | MM + GLM |
| 26 | hk 公网出口 | ✅ | baidu/hf/npm/google 200；openai/anthropic/grok 403（链路通缺 key） | 三腿 ★ |
| 27 | 短时凭据纪律 | ✅ | OpenBao 现拉 / argv-free / 0600 / tmpfs 注入；gov CNB token 经 Bao 零落盘 | 三腿 |
| 28 | 时间同步与 journal 滚动 | ✅ | chronyd 正常、三机 journal 正常滚动 | 三腿 ★ |

### 6.2 跑不通 / 坏了 / 没配

| # | 对象 | 结果 | 关键口径 | 出处腿 |
|---|---|---|---|---|
| 29 | **hk gost 公网无鉴权 SOCKS5** | ❌ 被滥用（进行中；盘点后公网监听被收窄） | ≥6 境外 IP、354M 日志、峰值 619M 内存 | MM + GLM ★（**SR 未报**） |
| 30 | **hk warp-reroute.service** | ❌ failed | `port 7863 not listening - refusing to arm redirect rules` → 透明分流不生效 + 7863 公网可达 | 三腿 ★ |
| 31 | **hk exit node 实际使用** | ❌ 零 | `ts-forward`/`ts-postrouting`/FORWARD 计数全 0 | MM + GLM |
| 32 | **hk → anolis 直连** | ❌ 仅 DERP(hkg) | `direct connection not established`，69–157 ms | MM + GLM |
| 33 | **hk 两条回传通道（8090 / 9418）** | ❌ 全关 | 无监听、无 unit、HMTOKEN 无取值来源 | MM + GLM |
| 34 | **hk MagicDNS 按名解析** | ❌ 不可用 | `accept-dns=false`、DNS disabled | GLM（单腿） |
| 35 | **gov auto-router 开机自启路径** | ❌ 崩溃循环 | `NRestarts=27977`（仍在涨），8777 靠 10-03 21:14 手工孤儿进程顶替 | 三腿 ★ |
| 36 | **gov 443 TLS** | ❌ `rc=35` 握手失败 | 三次一致，非新增；`Caddyfile` 全文未读到 | MM（单腿） |
| 37 | **gov 8300/8310 鉴权状态** | ⚠️ 未知 | 绑 0.0.0.0、主机无白名单，两腿都未验证（最高优先级盲区） | MM + GLM ★（绑定面实测确认） |
| 38 | **gov OwnerGate 通知链** | ❌ 断 | 微信最近送达 10-01；回归 fail 告警连续 3 天 rc=3 | MM + GLM |
| 39 | **gov 资源余量** | ❌ 不足 | load 13–19、clickhouse 460–513%、零 SWAP、瞬时 free 159MB | MM + GLM ★ |
| 40 | **gov 6 张治理表 / MinIO artifact 桶** | ❌ 0 行 / 无桶 | artifact_route、challenge、message_receipt、rule_violation、promotion_record、capability_version | MM + GLM（桶清单【单方记录，未核实】） |
| 41 | **gov kernel gateway / LiteLLM / Kafka** | ❌ 未部署 / 悬空 | 镜像在、容器不在；`litellm_adapter.py` 悬空；`data/kafka/` 空壳 | MM + GLM |
| 42 | **gov Temporal worker** | ❌ 零 worker | established=0、namespace 仅 temporal-system、compose 自注 "exec-plane workers [待]" | 三腿 |
| 43 | **gov OPA 接流量** | ❌ 容器 healthy 但未接流量 | rego 样例 `W-09 待接线` | MM + GLM |
| 44 | **gov `OTLP_BEARER_TOKEN`** | ❌ 未设置 | compose 引用但默认空串 | MM（单腿） |
| 45 | **gov GitHub/Google/OpenAI/HF 直连** | ❌ 全断 | 两个 GitHub remote 的 `git fetch` 可达性未证实 | MM + GLM |
| 46 | **anolis 公网 22 爆破** | ❌ 持续（无封禁） | 24h 22,722 条 / 自 10-02 41,182 条（本汇总实测） | MM + GLM ★（SR 未量化） |
| 47 | **anolis fail2ban / 防火墙 / sshd 加固** | ❌ 全缺 | 未安装、INPUT ACCEPT、`sshd_config` 去注释后仅 3 行有效 | 三腿 ★ |
| 48 | **anolis 7 处 git remote 明文 token** | ❌ 破口 | 违反 AGENTS.md 红线；有效性未查 | MM + GLM + SR |
| 49 | **anolis `anuser NOPASSWD:ALL`** | ❌ 权限收敛失效 | + 5 个身份可免密进 anuser | 三腿 |
| 50 | **anolis 回归门禁** | ❌ 红 | 72/49/5/18，fail 4→5 击穿"fail 只降不升" | MM + GLM ★（SR 记 65 用例跑通，见 D2） |
| 51 | **anolis PM 循环健康度** | ❌ 空转掩盖停滞 | 5 分钟热循环、7 条产品线 worklog stale 103–105h、dispatch 仅 1 份 | MM + GLM |
| 52 | **anolis HF 直连** | ❌ DNS 污染 | exit=124，已用 hf-mirror 绕行 | MM + GLM |
| 53 | **anolis OwnerGate 实体** | ❌ 无代码无服务 | 仅 handover 文档 + PM agent 替代物 | 三腿 |
| 54 | **anolis 5 个业务服务托管** | ❌ 无 systemd / 无 Restart | 8125/9001–9004 | MM + GLM ★ |
| 55 | **Memory / 向量库（三机）** | ❌ 全无 | chroma/faiss/milvus/qdrant/pgvector 全盘 0 命中；anolis 依赖齐装但 `skill_retrieval disabled` | 三腿 |
| 56 | **Jev 判别服务（三机）** | ❌ 无独立服务 | anolis 只有权重 + 2 脚本；gov 仅 auto-router 内代码路径；hk 无 | 三腿 |
| 57 | **生产 MQ / 沙箱运行态 / agent CLI（三机）** | ❌ 均未投产/未部署/分化 | MQ 见 42；沙箱只有 `docker run --rm` 弱隔离；CLI：gov 有 openclaw(+minimax-code×3)、anolis/hk 零 | 三腿 |
| 58 | **`harnessos/` 目录树（三机）** | ❌ 零命中 | §9.5 结构未建，实机是另一套命名 | 三腿 ★（方案侧 grep 由本汇总复现） |
| 59 | **三机 fail2ban / 主机防火墙 / SWAP** | ❌ 全无 | 三腿一致 | 三腿 ★ |

---

## 第 7 章　遗留问题清单（三腿都没答上来、或互相矛盾的未决项）

**A. 安全类（最高优先）**
1. **tailnet `edgenet` 的 ACL 策略本体**：anolis 的 root 免密完全依赖 Tailscale SSH（`RunSSH: true`、无 authorized_keys），ACL 粒度直接决定谁能变 root——**三腿都把它列为最大空洞，谁都没读 ACL 文件**。
2. **gov 8300 / 8310 的鉴权状态**：两个凭据/协作敏感端口绑 0.0.0.0、主机层 `-P INPUT ACCEPT`、无白名单，两腿都未验证（我只确认了绑定面）。
3. **hk auth.log 里的成功登录从未被任何一方统计**：一台 30 天被爆破、口令开着、6 把公钥的机器，只统计过 `Failed password`；`grep "Accepted"` 是最高优先级补查项。
4. **anolis 7 处泄露 token 的有效性与影响面**：是否已 push、是否在历史提交中、是否已失效——三腿均未查。
5. **gov/hk 的 authorized_keys（7 把 / 6 把）归属与最后使用时间、封禁 IP 原因**：三腿都只计了数量；gov 还有 `VM-0-12-opencloudos` 这台机器的身份未明（MM 列为盲区，且该身份出现在 hk 的 authorized_keys 注释里）。
6. **gov 公网 IPv6 `2402:4e00:c011:300:…` 的实际可达性**：IPv6 无 NAT，若可达安全模型完全不同（MM 盲区，无他腿覆盖）。
7. **hk 是否曾发生入侵/凭据外泄**：gost 被滥用期间有人用它连 `auth.purevpn.com:443`，双方都没统计总量、没查是否已产生凭据外泄或账单损失。

**B. 数据与实现类**
8. **glue 表数 19 vs 24 的差集**：anolis 经自己通道实测 19 张 `glue.*` 表，gov `information_schema` 实测 24 BASE TABLE + 14 VIEW（GLM 自己标为需补测 X14；MM 的内部仲裁落在"24+14"）。同一库两套读数，差集与原因未明。
9. **回归门禁三套数字**：方案 76 / 实测 72 / kernel pytest 184；`role.json` 自述 76 而实测 72 差 4 例；gov `cases/` 66 文件 vs anolis `cases/` 70 文件是否同一权威套件（GLM X15）。
10. **anolis patrol 04:17–04:19Z 与 gov 基线 12:17:02/12:19:38 时刻吻合、PAT-04 note 的 host=VM-0-6-opencloudos**：patrol 是否远程驱动 gov 门禁？12:17 基线的真实触发者是谁（cron 是 06:00，必为手动）？——两腿都提出、都没答。
11. **gov 5 个回归 FAIL 的归属**（L1-03/L3-05/L4-10/L6-01/L6-09）是"已知待办"还是"无人认领的孤儿缺陷"。
12. **ClickHouse 460–513% CPU 的成因**（疑似 MV 刷新或高频 trace 写入，未验证）；以及 `console_tui` 99.8% 是否真是忙循环（本汇总实测到 92.3% 的 `python` 进程但未确认身份）。
13. **gov `Caddyfile` 全文与证书链**：既是 443 TLS 失败的排障入口，也是"哪些域名对外"的唯一权威清单——两腿都没读到。
14. **MinIO 桶清单**：仅 1 个空 `langfuse` 桶为【单方记录，未核实】，需带凭据复核。
15. **Jev 16 个接入位逐位核对、13 个 subagent 逐模块审读、`config/` 六件套（permissions/stop_conditions/owner_gate/jev_thresholds…）与"报告头 `trigger_source`"落实情况**：三腿均未覆盖。
16. **Temporal 端到端闭环**：gov 零 worker + anolis `qw_worker` 空转组合，真实任务派发从未验证。
17. **anolis 黄金用例本体未跑**（需 OpenBao 凭据 + LLM 预算，两腿都因只读/预算未执行）；`check_contracts.py`、`deploy/*/validate.py` 未执行。
18. **gov 双源漂移的实体 diff**：`/opt/company/platform` 5 modified + 16 untracked、company-ops 双副本（10-01 vs 09-26）哪份生效、`/opt/company/ops/notify/` 与 company-ops 的副本漂移。

**C. 运行与治理类**
19. **gov auto-router 8777 孤儿进程的来龙去脉**：10-03 21:14 执行者是谁、为何杀旧进程 943769、为何不修 unit——两腿列为盲区第 1 项，均未查。
20. **gov 宿主残留的 `temporal-server`（lighthouse 用户，Sep28 起）** 与容器版并存的用途（MM【已核实-单方 B】，他腿未覆盖）。
21. **gov agent CLI 口径不一**（SR 1 个 / MM 4 个 / GLM openclaw + minimax-code×3）——是否同一批进程的不同描述，需一次 PATH 清单核对。
22. **gost unit 在 05:56:54 被改为仅监听 100.64.0.3**：改动者不在三腿任何记录内（需查 shell history / journal / 变更工单才能定性，本汇总不做猜测）；收窄后合法用户 `100.64.0.2` / windev-01 的出口是否仍满足需求也未评估。
23. **hk warp-reroute 是"本次开机才坏"还是长期坏着**（B 记上次成功是 Sep 19 15:28【单方记录，未核实】）；hk `github/pypi` 25s 极慢的根因（MM 记未定位，GLM 复测不复现）；hk MagicDNS 不可用只有单腿印证。
24. **三机之外的 5 个 tailnet 节点**（pandev-comp / mingda-website / windev-01 / cloudpc-01 / harmony-vm）的详细现状与下线原因；windev-01 反复漂移无人跟踪；`100.64.0.2` 两端命名不一致（`mingda-website` vs `edge-server`）的原因。
25. **备份可恢复性**：gov `backup-daily` + `bao-snapshot`（14 份）从未恢复演练；hk `/srv/inbox` 无备份、bare 仓无 remote；anolis `backups/`、`local-plane-backup/` 未盘点。
26. **gov `159.75.21.149` 与 `100.64.0.6` 同一台机**这一事实：MM/GLM 都观察到 gov↔hk 直连走 `159.75.21.149:52486`、GLM 记 `ai.hkmingdajiaoyu.com` 的 A 记录指向它，但 MM 仍把它列为未决项——建议直接以 hostid 核对后关闭（影响"PG 在 gov"与 config 里公网入口的表述）。
27. **`aggregate_only.py:82` 缺 `os.makedirs` 的真 bug**（隔离副本复现 rc=1 / FileNotFoundError）：谁在正常流程里调用它未查，若 CI/巡检依赖它，门禁的"红"可能部分由此造成。
28. **anolis journal 8 天历史缺口**（`--list-boots` 仅 1 boot 却有 10-02 10:32 的条目，合并员看到自相矛盾，需重查）；gov 5 个僵尸进程的父进程。
29. **`159.75.21.149:22 OPEN 但 :5432 CLOSED`、`10.8.0.1:5432 CLOSED`** 等端点结论与"PG 在 gov"的并存解释，以及 `chroma/pgvector` 实际数据是否在 srv-1 PG（两腿均未验证）。

---

## 第 8 章　附录：本汇总人执行的只读复核（命令与原始输出节选）

> 全部为只读操作（ss / ps / stat / journalctl / df / free / top / nvidia-smi --query-gpu / docker exec headscale nodes|users list / dnf check-update / systemctl is-active|cat|show / tail / grep / sleep）。执行时间约 2026-10-05 06:10–06:20 UTC（14:10–14:20 CST）。临时输出存于 `/tmp/synth-t1/`。

| # | 主机 | 命令（节选） | 输出（节选） | 支撑的结论 |
|---|---|---|---|---|
| 1 | 本机 | `grep -nE "governance-machine\|anolis\|hk-gateway\|100\.64\.0\.\|159.75\|srv-?1\|CloudCrane" agent协作体系.txt` | **零命中**（文件 1474 行） | D1：三机分工是任务设定 |
| 2 | anolis | `ss -ltnp \| grep -E "8125\|900[1-4]\|18092"` | `100.64.0.7:8125 users:(("python",pid=550568))`；`127.0.0.1:9001-9004`；`127.0.0.1:18092 users:(("python3",pid=1056366))` | D5 / D15：anolis 确有在跑 MCP；jiuwenswarm PID 与 GLM 一致 |
| 3 | anolis | `ps -o pid,user,etime,args -p 550568` | `anuser 4-19:30:31 /opt/gpumachine/agent-browser/venv/bin/python -m agent_browser.server` | D5 |
| 4 | anolis | `command -v fail2ban-client; systemctl is-active fail2ban` | 无输出 / `inactive` | D15 类：fail2ban 未安装 |
| 5 | anolis | `dnf -q check-update \| grep -c "^\S"` | **121** | D4：待更新包量级 |
| 6 | anolis | `journalctl --since "24 hours ago" \| grep -c "Failed password"` | **22,722** | D6：爆破量级（24h 口径） |
| 7 | anolis | `journalctl --since "2026-10-02" \| grep -c "Failed password"` | **41,182** | D6：爆破量级（自 10-02 口径） |
| 8 | anolis | `journalctl --since "24 hours ago" \| grep -ciE "Failed password\|Invalid user"` | **43,667** | D6：宽口径参照 |
| 9 | anolis | `df -h /data` | `/dev/vdb1 295G 234G 46G 84% /data` | 矩阵/高危 B5 |
| 10 | anolis | `nvidia-smi --query-gpu=index,memory.used --format=csv,noheader` | `0, 310 MiB` / `1, 15516 MiB` | 矩阵：GPU1 占用与两腿一致 |
| 11 | anolis | `cat /proc/loadavg; free -m; swapon --show` | `0.55 0.38 0.17`；`free 35863/128518`；swap 0 行 | 矩阵：anolis 负载低、无 SWAP |
| 12 | gov | `systemctl show auto-router -p NRestarts -p ActiveState -p SubState -p ExecMainStatus` | `NRestarts=27977`；`ActiveState=activating`；`SubState=auto-restart`；`ExecMainStatus=1` | A6：崩溃循环仍在继续 |
| 13 | gov | `ps -o pid,ppid,lstart,args -p 3522460` | `3522460 3522434 Sat Oct 3 21:14:07 2026 python3 /opt/company/ops/auto-router/auto_router.py` | 高危 A6 / D6 一致：孤儿进程顶替 |
| 14 | gov | `docker exec company-headscale-1 headscale nodes list` | IP 列：`100.64.0.1 .2 .3 .4 .5 .6 .7 .8`（8 个齐全，含 .8） | D7：pandev-comp 在册，采信 GLM |
| 15 | gov | `docker exec company-headscale-1 headscale users list` | `edgenet`、`new-member` | 与 SR 一致 |
| 16 | gov | `ls /opt/factory-tests/tests/cases/ \| wc -l` | **66** | D2：文件数 |
| 17 | gov | 读 `/var/log/factory-tests/baseline-2026-10-05.json` | `"total": 72, "pass": 49, "fail": 5, "skip": 18`；`generated_at 2026-10-05 06:00:01 +0800`；`host VM-0-6-opencloudos`；末条 `L6-09 … "result":"fail"` | D2：门禁为红，SR"跑通"不成立 |
| 18 | gov | `dnf -q check-update \| awk '{print $1}' \| grep -c "."` | **97** | D3：采信 96（SR 的 40+ 不成立） |
| 19 | gov | `ss -ltnp \| grep -E "8300\|8310\|8787"` | 三个均 `0.0.0.0` 监听 | 高危 B1：绑定面确认 |
| 20 | gov | `top -bn1` | `clickho+ 492.3% CPU`；另有 node 92.3%、python 92.3% | D13：ClickHouse 是最大单因 |
| 21 | gov | `cat /proc/loadavg; free -m; swapon --show` | `14.36 13.36 13.17`；`free 1747/15603`；swap 0 行 | A5：过载与无 SWAP |
| 22 | gov | `docker ps -q \| wc -l` | **15** | 与三腿一致 |
| 23 | hk | `systemctl is-active warp-reroute.service; ss -ltn \| grep -E "7863\|1080"` | `failed`；`0.0.0.0:7863`（Recv-Q=7）、`100.64.0.3:1080` | A4：7863 仍公网可达 |
| 24 | hk | `ls -lh /var/log/gost.log; wc -l` | `354M` / `1,197,607` 行 | A7 / A1：滥用规模 |
| 25 | hk | `stat -c "%s %y" /var/log/gost.log; sleep 60; stat …` | 两次均 `370841108 2026-10-05 06:13:46`（**60 秒无增长**） | D14：滥用已停止增长 |
| 26 | hk | `systemctl cat gost; systemctl show gost -p ExecMainStartTimestamp; journalctl -u gost \| tail` | unit mtime `2026-10-05 05:56:54`；`ExecStart=/usr/local/bin/gost -L socks5://100.64.0.3:1080`；started `05:56:56`；上一实例 `Consumed 20min 20.216s CPU time, 619.1M memory peak` | D14 / A1：公网暴露在盘点后被收窄 + 资源代价实锤 |
| 27 | hk | `uptime; free -m; uptime -s` | `load average: 2.39, 2.48, 2.70`（2 vCPU）；boot `2026-10-05 03:44:53` | A5/A7 类 |

**未执行/无法执行的事项（如实声明）**：未读取任何密钥/凭据值；未执行任何修复或状态变更；未做跨机端到端调用测试；未验证 gov PATH 上的 agent CLI 清单（D11 留待）；未复核 MinIO 桶清单（`mc` 不可用、鉴权未打通）；hk 的 `warp-cli status` 未跑（需 `--accept-tos`，属写状态，只读铁律禁止）；方案第 0/1/2/3/4/7/11/12 部分无存在基础可核对（沿用 GLM 的说明），未逐项展开。

---

*本汇总仅依据三条腿的总报告全文 + 上表所列本汇总人只读复核撰写；标注【单方记录，未核实】的条目不得作为运维决策的唯一依据。*
