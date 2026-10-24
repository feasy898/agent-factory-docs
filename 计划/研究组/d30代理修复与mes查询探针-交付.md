# D-30 docker 代理修复 + MES 查询级探针 · 交付（2026-10-22 下午，修理组子代理 step-5-preview 载体）

> 两件互不依赖的小事：①D-30 本机 docker pull 通道修复（债册 D-30，中）——**补丁已就位，dockerd 重启未执行（"半应用"态，命令与回滚已交付，见 §1.5）**；②MES 轻量查询级探针（mes500 报告 §4 C 组缺口 1，④组遗留项）——**已交付、四类失败演练全过、keepalive 已换新码在役**。
> **纪律事故如实自首（本节作业的方法性错误，已由主代理归档并增设纪律）**：§1.3 的 A/B 实证用了"起第二 dockerd"的验证法，14:27:53 拆掉真 `docker0` 桥，本机判分停摆 17 分钟——事故全记录《事故-20261022-docker0桥被拆-本机判分停摆17分钟.md》，主代理已增设 AGENT.md 硬纪律 8（禁第二 dockerd）/9（docker0 桥判活+禁直接 restart docker）。**该验证方法自 15:4x 起被禁**；本文保留其产出数据（代理端点有效性的证据仍成立），同时完整披露方法代价。其余纪律遵守：gov 零接触；密钥零明文（口令只经 0600 文件管道）；MES 演练不污染生产告警文件（ALARMS_LOG/KLOG/mes_event 打桩重定向）。

---

## 1. D-30 本机 docker pull 通道修复

### 1.1 死因定位（全部实测）

| 探项 | 实测 | 结论 |
|---|---|---|
| drop-in 现值 | `/etc/systemd/system/docker.service.d/proxy.conf`：`HTTP_PROXY=HTTPS_PROXY=http://127.0.0.1:7890`（10-20 05:20 起） | 死端点写入处 |
| 本机 mihomo 监听 | pid 2000426（10-21 00:48 起）只听 `100.64.0.8:7890`（`ss -tlnp` 实证）；`curl -x http://127.0.0.1:7890 https://registry-1.docker.io/v2/` → rc=7 连接拒绝 | 回环口无人监听 |
| 生产 daemon 实况 | `docker info`：HTTP/HTTPS Proxy=`http://127.0.0.1:7890`，Live Restore=false；dockerd pid 1336735 active | 死代理正挂在生产 daemon 上 |
| 代理端点可用性 | `curl -x http://100.64.0.8:7890 https://registry-1.docker.io/v2/` → **401**（auth challenge，正常可达）；token 5.56s / manifest 1.98s / blob 307→CDN | 100.64.0.8:7890 通道活 |

即 D-30 登记的死因坐实：**drop-in 两行代理指向 127.0.0.1:7890，而 mihomo 只绑 tailnet 接口 100.64.0.8:7890**；任何 `docker pull` 走 daemon 代理必然 proxyconnect 拒连（daocloud mirror EOF 是同一死代理的另一种表象；现 daemon.json 无 registry-mirrors，拉取直连 registry-1.docker.io 经代理）。

### 1.2 补丁（已应用，对运行中 daemon 惰性无害）

`/etc/systemd/system/docker.service.d/proxy.conf` 两行代理改指 `http://100.64.0.8:7890`（NO_PROXY 三行不动）；原件备份同目录 `proxy.conf.bak-deadend-127-20261022`；`systemctl daemon-reload` 已执行。diff 存档：`工具状态备份/d30-docker-proxy-20261022/proxy.conf.diff`。

```
-Environment="HTTP_PROXY=http://127.0.0.1:7890"
-Environment="HTTPS_PROXY=http://127.0.0.1:7890"
+Environment="HTTP_PROXY=http://100.64.0.8:7890"
+Environment="HTTPS_PROXY=http://100.64.0.8:7890"
```

应用后即时复验：`systemctl is-active docker`=active、`docker info` 仍显示旧代理值（符合预期——drop-in 只在 daemon 启动时读取，**修复要生效需重启 dockerd**，见 §1.5）。

### 1.3 A/B 实证（**方法已被禁，数据仍有效——方法代价见本条末**）

为避免切断在跑判分容器，实证走了"同配置第二 daemon"：独立 socket `/tmp/dockerd-test.sock`、独立 data-root/exec-root（`/home/pan-ding/dockerd-test-*`，测后已删净）、`--bridge=none`、读同一份 `/etc/docker/daemon.json`，**只差代理端点一项**：

| 运行 | 代理 | 结果 |
|---|---|---|
| Run A（对照，复现 D-30） | `http://127.0.0.1:7890` | `docker pull hello-world` rc=1、0.033s：`proxyconnect tcp: dial tcp 127.0.0.1:7890: connect: connection refused`——**D-30 症状逐字复现** |
| Run B（=新 drop-in 值） | `http://100.64.0.8:7890` | rc=0、**3.28s**：image pulled（digest sha256:11a3eb1597e8…，hello-world:latest 25.9kB）。因两 daemon 共享系统 containerd 镜像库，该件已落在生产镜像库（`docker images hello-world` 可见） |

脚本与原始输出：`工具状态备份/d30-docker-proxy-20261022/{dockerd-ab-test.sh,dockerd-runB.sh,runB-result.txt,runB-pull.out}`。结论：**修复值本身已被真 `docker pull` 实证（3.28s 拉通小镜像）**——注意 Run B 走的是 daemon 自身 HTTP 客户端，与 docker0 桥无关，故该证据不受桥事故影响；缺的只是生产 daemon 的重启生效。

> **⚠️ 方法代价（本单最大偏差，全额披露）**：第二 dockerd 启动时按名接管/重建 `docker0`——`--bridge=none` 只表示"不创建新桥"，**不等于"不碰同名桥"**（dockerd 按名管理网桥，与 data-root/socket 无关）。14:27:53 真桥被拆，真 dockerd 未重启故无人重建，**本机 clean 判分停摆 17 分钟**（观测金丝雀批次二 3 题降级、CI act_runner 一度断链），14:44 由运营者裁决方案②手工重建恢复（docker0 UP+172.17.0.1/16、ip_forward=1、NAT 链完好亲验在役）。主代理已归档事故全记录并增设 **AGENT.md 硬纪律 8（禁在真 dockerd 宿主起第二 dockerd；dockerd 配置验证只准"只读核对+干跑"或"独立 netns"）与硬纪律 9（docker0 桥判活+幂等重建，禁直接 restart docker）**。教训一句版：单宿主多容器判分面上，"起第二个 dockerd 做验证"这种看似隔离的动作会拆真桥；破坏性宿主操作的授权边界必须写在派单里。

### 1.4 已知副作用与边界（如实登记）

1. **docker0 桥事故（最大副作用，已闭环）**：见 §1.3 警告块——第二 dockerd 拆桥致本机判分停摆 17 分钟，14:44 手工重建恢复（主代理亲验 docker0 UP+172.17.0.1/16、ip_forward=1、NAT 链完好；hello-world 容器出网探针通过；金丝雀按降级口径验收）。新纪律 8/9 已立，本单的测试 daemon 残留目录/进程已删净（15:3x 亲验无残留）。
2. 生产镜像库多一个 hello-world:latest（25.9kB，测试件）——重启生效后的净拉实证命令里含 `docker rmi hello-world` 先删再拉。
3. CNB 制品库（docker.cnb.cool）此前不在 NO_PROXY，改后其流量也走 daemon 代理→mihomo（mihomo 规则 GEOIP,CN,DIRECT 应直连，最差经代理仍可用）；local-image-feed 的自有 fast-pull 客户端不走 daemon 代理，不受影响。
4. 100.64.0.8:7890（本机 mihomo）**无鉴权**、只绑 tailnet 接口（非 0.0.0.0）——该风险 10-21 已登记在 `状态观测/anolis待sudo清单.md`（附计划/60 §1.4 滥用前车之鉴），本轮未扩大暴露面，也未新增强鉴权（不属本单范围）。
5. `live-restore` 未启用——启用它可让"daemon 重启不杀容器"，但激活它本身需要一次重启（本轮窗口不存在），列为未来硬化建议，未做。

### 1.5 dockerd 重启：**未执行**（半应用态；受硬纪律 8/9 约束，命令已交付待人工窗口）

任务书前提"本机 sweb 容器数当前应为 0"**不成立**（当时有 1 个 Up 的 sweb 容器，且现役判定以主代理 14:4x 处置为准：pylint-6386 容器**留自然终态**由臂重试回收、act_runner 容器级重启回桥）。按"不切断现役判分容器"纪律 + 硬纪律 8（宿主级服务重启须显式授权/人工窗口）+ 硬纪律 9（**禁直接 `systemctl restart docker`**，须先过桥判活与幂等重建流程），重启动作挂起，交运营者/主会话择时执行。届时按以下次序（每一项都是硬纪律 9 的判据）：

```bash
# ① 桥判活（缺失先按幂等重建流程处置：核 daemon.json bip/NAT 链/ip_forward → ip link add+地址+up → 容器出网探针）
ip link show docker0 && ip addr show docker0 | grep -q "172.17.0.1/16" && [ "$(sysctl -n net.ipv4.ip_forward)" = 1 ]
# ② 在飞容器清单核对并取得人工窗口（现役已知：afbench-swev-pylint-6386-mavis-m31f 留自然终态、opch-act-runner、af-bench 进程）
docker ps --format '{{.Names}}\t{{.Status}}'
# ③ 原子重启 + 复验（daemon 状态/代理值/容器清单逐项核对）
sudo systemctl restart docker && sleep 3 && systemctl is-active docker \
  && docker info | grep -iE "^ HTTP Proxy|^ HTTPS Proxy" \
  && docker ps -a --format '{{.Names}}\t{{.Status}}'
# ④ 净拉实证（库里已有 25.9kB 测试件，先删再拉）
docker rmi hello-world && docker pull hello-world    # 期望 ~3s 成功
```

**回滚一行**：
```bash
sudo cp -a /etc/systemd/system/docker.service.d/proxy.conf.bak-deadend-127-20261022 /etc/systemd/system/docker.service.d/proxy.conf && sudo systemctl daemon-reload && sudo systemctl restart docker   # 同样受纪律 9：先过桥判活再重启
```

> 现状说明（as-of 15:0x 亲验）：drop-in 已是正确值（`100.64.0.8:7890`）+ 备份在位 + daemon-reload 已做；现役 dockerd 仍是 10-20 07:26 起的老进程、带死端点（`docker pull` 仍报 proxyconnect refused）——即事故归档所称 **D-30"半应用"**态：修复值落盘待换进程，机器下次任何原因重启 dockerd 都会自动带上（但重启本身须走上面的窗口流程）。"通道要活"的硬证据由 §1.3 A/B 实证提供（方法已被禁，数据有效）。

---

## 2. MES 轻量查询级探针（mes500 报告 §4 C 组缺口 1 归还）

### 2.1 实现（tools/factory-keepalive.py 补丁④，改前备份 `工具状态备份/factory-keepalive.py.pre-mes-query-probe-20261022`）

`ch_mes_ping()`（GET /ping 布尔判活）→ **`ch_mes_probe()`**（查询级判活）：

- 探针 SQL（极轻）：`SELECT count() FROM af_mes.mes_event WHERE occurred_at > now() - INTERVAL 1 MINUTE`——occurred_at 是 ORDER BY 首列，分钟级谓词只扫尾部 granule，实测毫秒级返回（live 计数 625-628，30s 一轮零可感负载）。
- 失败四类 → 四个告警码（alarms.log `code` 字段 + klog 文案 + 去重键三位一体）：

| 类别 | 告警码 | 触发形态 | 恢复提示（CHMES_RECOVERY） |
|---|---|---|---|
| conn | `ch-mes-conn-refused` | 连接拒绝（端口失/进程死/tailnet 断） | mingda systemd 单元 clickhouse-factory.service（enabled+Restart=always，14:28 起在役）应自动拉起；持续失联→人工 systemctl start / start.sh，并查 tailnet/端口 |
| auth | `ch-mes-auth` | HTTP 401/403（0600 cred 文件与 mingda .pw 不同步） | 核对 `~/.config/mes-ch/url` 与 `.pw` |
| query | `ch-mes-query` | HTTP 5xx/其他查询错误（**含 mes500 的 MEMORY_LIMIT_EXCEEDED→500 形态**） | 查 mingda system.errors，人工介入 |
| timeout | `ch-mes-timeout` | 超时无响应（3s；挂起/深内存压力/黑洞） | 查负载与连通性，持续按 conn 处置 |

- 分类实现：urllib 异常族映射——`HTTPError` 401/403→auth、其他→query；`socket.timeout/TimeoutError`（含 URLError.reason 包装）→timeout；`ConnectionRefusedError`（含 URLError.reason）→conn；其余 URLError/未分类异常保守归 conn（方向安全）；2xx 但响应体非纯数字→query。
- 告警通道不变（klog + `状态观测/alarms.log` 文件主通道，CH 挂时照样可报）；MES `kind=ch_mes_down` 不变（**schema 零改动**），类别只在告警文件/klog 区分；30min 去重 + **类别翻转立即重报**（同窗内 conn 翻 query 是质变，不被去重吞）。
- 凭据纪律：连接参数全部走既有 `_mes_conn()`（env `MES_CH_URL` > 0600 `~/.config/mes-ch/url` > 缺省新地址），口令零明文进代码/文档/转录；演练用错凭据是临时构造的假值。
- LAUNCH_PLAN 台账与模块 docstring 同步更新（等价判据命令改为带认证的查询 URL）。

### 2.2 四类失败演练（各一次，生产文件零污染）

演练把 `ALARMS_LOG`/`KLOG` 重定向 /tmp、`mes_event` 打桩，**探针本身打真端点**（真 mingda CH 用于 auth/query，本地套接字用于 conn/timeout），走真实 `fix_ch_mes_local` 告警路径：

| 造失败方式 | 期望→实测 | 告警码核验 |
|---|---|---|
| 错端口 `http://127.0.0.1:15998`（无人监听） | conn→**conn** PASS（`[Errno 111] Connection refused`） | `ch-mes-conn-refused` ✓ |
| 错凭据（真 CH + 临时构造的假 Basic） | auth→**auth** PASS（HTTP 401） | `ch-mes-auth` ✓ |
| 错 SQL（真 CH+真凭据，`SELECT * FROM af_mes.__probe_no_such_table`） | query→**query** PASS（HTTP 404，mingda server.err.log 留 UNKNOWN_TABLE code 60 实证） | `ch-mes-query` ✓ |
| 超时（黑洞套接字：accept 后永不回应，2s） | timeout→**timeout** PASS（`2s 超时无响应`） | `ch-mes-timeout` ✓ |

语义补验（跟跑脚本，`工具状态备份/mes-query-probe-20261022/dedup-retest-output.txt`）：同类(timeout→timeout)去重 PASS(0→0)、类别翻转(timeout→conn)立即重报 PASS(0→1)、dry-run 零写入 PASS(1→1)、新鲜探针 tuple `(True, None, '查询 Ok（近1分钟事件 count=627）')`。

**如实登记**：首个演练脚本自报 "RESULT: HAS FAIL" 系**测试脚本自身两处笔误**（①打印前被结果循环覆写了 `detail` 变量，导致"恢复转绿"行显示上一轮的 timeout 文案；②"同类去重"预期值设错——四类连报后末条告警类别是 timeout，用 query 试"同类"实为翻转，告警正确触发）。生产代码无误，两项均在跟跑脚本中按正确预期复验 ALL PASS。演练脚本与两份输出存档于 `工具状态备份/mes-query-probe-20261022/`。

### 2.3 换码在役 + 恢复转绿

- keepalive 重启（正确姿势：kill 旧 pid 553898 确认退出 → setsid 常驻）：我的实例 pid 636996（14:44:26 起）。**并发事实（如实登记）**：14:45:35 我的实例被同期一姊妹子代理的 keepalive 重启序列终止（与 10-22 13:06 迁移日同型的"改码未先确认守护层静止"竞态，本次无数据面影响）；该姊妹子代理（workflow 子代理）随后两次重启（14:46:31 pid 638896、14:48:56 pid **641328**=现役），并给心跳段加了一处 3 行改进（DRAIN_PROBES：完成态对象如实报 done 不再报 DOWN——与 mes500 §5.1 的 mcode done 判断建议同向）。**我的探针改动与该改进无冲突共存**（现文件=我方版本+该 3 行；pidfile 单实例核对一致）。
- `--dry-run` 判活结论（新码实跑）：`ch-mes-local 存活 查询 Ok（近1分钟事件 count=626）`；其余 7 对象状态与重启前一致（image-feed/mcode-dispatch"失联"=正常完成退出的设计内形态，非回归）。
- **现役实证（15:0x，mingda query_log 亲验）**：现役 keepalive（pid 641328）每 30s 打一条 `SELECT count() FROM af_mes.mes_event WHERE occurred_at > now() - INTERVAL 1 MINUTE`（15:00:59/15:01:29/…/15:03:29 连续 6 条）——查询级探针确已在生产判活链路内跑起来；`/tmp/factory-keepalive.log` 心跳（14:57:58 起）ch-mes-local:ok。
- 生产 `状态观测/alarms.log` 无演练污染（末条仍是 14:26:04 旧码的真实告警，见 §2.4）。

### 2.4 Bonus：一次真实 conn 类失联的实证（14:26）

14:26:04 旧码 keepalive 报警 `MES 失联：/ping 无响应/非 Ok.`，同秒两条 `MES 写入失败（不致命）: Connection refused`——即 10-22 14:26-14:28 mingda CH 有一次真实不可达。查因：**同窗恰是姊妹子代理的 systemd 托管切换**（`clickhouse-factory.service` 14:26:12/14:27:08/14:28:05 三次拉起尝试，14:28:54 起 active，见 状态/机器清单.md 14:3x 行）——计划内切换而非事故。意义：若新码在役，这次会被分类为 **conn（ch-mes-conn-refused）** 并带 systemd 自愈提示，而非旧码的无类别布尔——正是本补丁要补的观测力。mingda 现有 server pid 3386508（14:28:54 起，systemd cgroup 内），数据无损（探针计数持续增长正常）。

---

## 3. 落账清单

| 落点 | 内容 |
|---|---|
| `计划/研究组/d30代理修复与mes查询探针-交付.md` | 本文件 |
| `计划/研究组/事故-20261022-docker0桥被拆-本机判分停摆17分钟.md` | §1.3 方法代价的事故全记录（主代理 15:3x 归档，本文不重复其取证链，只做任务侧交叉引用） |
| `状态观测/巡检日志.md` | 一行（D-30 补丁+A/B 实证+重启挂起+**桥事故交叉披露**；MES 探针交付+演练+换码） |
| `计划/变更日志.md` | 一行（合并登记两件+桥事故纪律化交叉引用） |
| `计划/技术债登记.md` | D-30 行更新（补丁就位、半应用态、restart 待人工窗口——未标全还，如实部分归还）；mes500 C 组缺口 1 随 §2 交付销账 |
| `状态/组件建设状态.md` | 更新记录：14:2x"进行中"行替换为完工行（含桥事故自首） |
| `状态/机器清单.md` | 更新记录一行（本机 docker drop-in 变更+keepalive 探针升级） |
| `工具状态备份/d30-docker-proxy-20261022/` | A/B 脚本、pull 输出、drop-in diff（**方法已被禁，仅存证**） |
| `工具状态备份/mes-query-probe-20261022/` | 演练脚本×2、两份输出 |
| `工具状态备份/factory-keepalive.py.pre-mes-query-probe-20261022` | keepalive 改前备份 |

**未做（交主代理/底座，防越权）**：事故护栏 G2/G3（keepalive/watchdog 桥判活项 + `tools/net-bridge-guard.sh` 幂等重建）已由主代理归口 D-38 系统性建设——本单只改探针、不扩写 keepalive 判活面，避免与 G2 实施方同文件冲突。

## 4. 回滚

- **MES 探针**：`cp -a 工具状态备份/factory-keepalive.py.pre-mes-query-probe-20261022 tools/factory-keepalive.py && pkill -f "tools/factory-keepalive.py"; sleep 2; setsid nohup python3 tools/factory-keepalive.py >> /tmp/factory-keepalive.out 2>&1 </dev/null &`（恢复 /ping 布尔判活；无数据面影响）。
- **D-30**：§1.5 回滚一行（还原 drop-in + daemon-reload + restart docker；restart 同样受硬纪律 9 约束——先桥判活、人工窗口）。

## 5. 更新记录

| 时间 | 身份 | 事件 |
|---|---|---|
| 2026-10-22 14:2x-15:0x | 修理组子代理（step-5-preview 载体） | §1 勘察→补丁→A/B 实证（方法致 docker0 事故，已归档+纪律化）→重启窗口判定（半应用+命令交付）；§2 探针实现→四类演练→语义补验→keepalive 换码在役→dry-run 复验；§3 落账。15:0x 补记：桥事故交叉披露、硬纪律 8/9 对齐、G2/G3 归口 D-38 不越权 |
