# MES 迁移 mingda-website · 交付（2026-10-22 下午，修理组子代理 step-5 载体）

> 任务：MES（ClickHouse 事件库）由 pandev-comp 本机迁至 mingda-website（tailnet 100.64.0.2），
> 本机数据零丢失迁移，写入方全部回指，直接切换+本机旧实例只读 48h 回滚锚。
> 结论：**迁移完成，五项对账逐字一致，双机探针通过，写入方全部回指，既有服务/gov 资产零接触。**
> 唯一事故=巡检侧 13:06 复活 keepalive 与我改码竞态致 6 行落锚点——已追平 Mingda，见 §5。

---

## 1. 部署形态（mingda 侧，本厂自有实例）

| 项 | 值 |
|---|---|
| 位置 | mingda-website（ssh 别名 mingda-bench，100.64.0.2）`/root/ch-mes-factory/`（全新目录，与既有 `~/ch-mes*` 无关，机上原本无此目录） |
| 二进制 | 本机 `~/ch-mes/bin/clickhouse` 原样 scp 传输（769,522,584 B，1m59s），版本 **26.7.34.3 与本机逐字同版**（mingda 出网不通 clickhouse 源，故传二进制不下装；glibc 2.38 前向兼容实测 `clickhouse local --query "SELECT version()"` 通过） |
| 端口 | **15221（HTTP）/ 15222（native）**——迁移前 `ss` 核验全机空闲（在用：22/80/443/8080/8081/3010/55432/8200/8201/9091 等） |
| 监听 | `127.0.0.1`（本机探针）+ `100.64.0.2`（tailnet，写入方走这里）。**不绑 0.0.0.0**——该机公网开 22/80，CH 不暴露公网面 |
| 进程 | server pid 3334225（watchdog 3334214），nohup 常驻，cmdline 带 `--config-file`；**无 systemd 单元**（复刻本机 PPid=1 形态；机器 up 34d，systemd 单元作可选后续，归运营者） |
| 启动 | `/root/ch-mes-factory/start.sh`——复刻本机 MES 500 修复经验的双保险（`cd` 到实例目录 + `--config-file` 显式指定，防 cwd 错致静默走 embedded config）+ /ping 就绪等待 + 防重复启动；就绪判据用带认证的 `SELECT 1`（口令从 0600 的 `.pw` 读，不进 argv 字面量） |

**config.xml（按 7.4G 机器适配，复刻 10-22 MES 500 修复口径）**：`max_server_memory_usage=2147483648`（2GiB 静态）+ `memory_worker_dynamic_hard_limit=0`（关动态塌陷）+ `max_server_memory_usage_to_ram_ratio=0.6` + `mark_cache_size=536870912`（512MiB 降配）+ `query_log`（14 天 TTL，补取证能力）+ timezone Asia/Shanghai。实测四项设置生效（3221225472→2147483648 / 0 / 0.6 / 536870912）。

**users.xml（访问控制）**：default 用户 + **口令字段已设**（openssl rand 生成，明文只存 mingda `/root/ch-mes-factory/.pw` 与 `users.xml`（均 0600）及各消费方 `~/.config/mes-ch/url`（0600）；按密钥纪律**口令值不进任何文档/回报/转录**，此处只登记字段名）。networks 白名单 = `127.0.0.1` / `::1` / `100.64.0.0/10`（tailnet 网段）。实测：无凭据查询 → 401；带凭据 → 正常。

## 2. 数据迁移与对账（零丢失，逐字一致）

1. **写入方静默**（13:02）：kill 主调度器（pid 3866052）+ 实验线调度器（pid 2857945）+ 其在飞臂孤儿（pid 484784，surgical kill，在飞工作流臂 485135/485150 未碰）；keepalive 当时已死于 EDQUOT（12:21），mcode-dispatch 未在跑——写入方全静默后导出，杜绝边写边导漂移。
2. **导出**（13:03）：`SELECT * FROM af_mes.mes_event FORMAT Native`（1,189,021 B）+ 全序 TSV（9,605 行）双格式，落 `~/ch-mes-migration/`（不用 /tmp，遵守分流纪律）。
3. **建 schema**（mingda）：`af_mes` 库 + `mes_event`（MergeTree，DDL 逐字照抄）+ `mes_line_hour`（SummingMergeTree）+ `mes_line_hour_mv`（物化视图，照抄）。
4. **导入**：Native 流 POST 导入（显式列清单）。
5. **五项对账（导入即时，逐字一致）**：

| 项 | 本机（冻结） | mingda | 一致 |
|---|---|---|---|
| 行数 count() | 9605 | 9605 | ✅ |
| sum(quantity) | 2127696368 | 2127696368 | ✅ |
| min(occurred_at) | 2026-10-20 04:13:02.679 | 2026-10-20 04:13:02.679 | ✅ |
| max(occurred_at) | 2027-01-15 08:00:06.000 | 2027-01-15 08:00:06.000 | ✅ |
| uniqExact(event_id) | 8551 | 8551 | ✅ |

6. **字节级佐证**：两侧全序 TSV（ORDER BY 全列）导出 md5 均为 `a7ecab5ecc92b4e78cd59df575e47e94`——**逐字节相同**。
7. **收尾集合证明**（静默行追平后）：本机现存 9,611 行（9,605 + §5 的 6 行竞态行）经 `comm` 按 C  locale 全集比对，**本机→mingda 缺失行数 = 0**（本机是 mingda 的严格子集）；切窗后新事件 175 行（探针/调度节点/keepalive 记账）只在 mingda。切窗前总量（occurred_at<13:00）两侧均 9,598 / 2127696361 / 8544。

## 3. 写入方回指清单（4 文件，改前备份）

备份：`工具状态备份/{bench-mes,factory-sched,mcode-dispatch,factory-keepalive}.py.pre-mes-mingda-20261022`。

| 文件 | 改点 | 新语义 |
|---|---|---|
| tools/bench-mes.py | CH 常量 + ch_query 认证头 + `--ch` 兼容 | 地址解析：env `MES_CH_URL` > 0600 文件 `~/.config/mes-ch/url` > 缺省 `http://100.64.0.2:15221`（缺文件且无 env → 无凭据 401 显性失败，**不静默回落旧锚点**） |
| tools/factory-sched.py | CH 常量 + ch_insert 认证头 | 同上 |
| tools/mcode-dispatch.py | CH 常量 + mes_event 认证头 | 同上 |
| tools/factory-keepalive.py | CH 常量 + mes_event/ch_mes_ping 认证头 + 探活目标与告警文案 | **ch-mes-local 探活改指 mingda:15221**（读点回指；本机锚点不在此探活范围）；失联告警文案改为"恢复=人工跑 mingda:/root/ch-mes-factory/start.sh" |

共性：`_mes_conn()` 助手（urllib 不解析 URL 内嵌凭据，故拆 user:pass 转 Basic 头）；四文件 py_compile 过；本机 cred 文件 `~/.config/mes-ch/url`（0600）已建。

**调度栈重启**：两调度器 13:06:45 由 keepalive（巡检侧复活）以新码拉起，重启后 failed=0、done=91、running=7（13:20 时点），断点续跑正常（factory.log/factory2.log 实证）；keepalive 13:15:50 换新码常驻（pid 553898），未扰动在飞的两调度器与工作流臂。

## 4. 验收（双机探针 + 查询级）

- **本机探针**：`bench-mes.py` 实跑一条识别性 results（`zz-mes-migration-probe-pandev`）→ 入 MES 6 行，回读 6 行全对（tokens_input/output/cache_read/turns/wall_ms/reward）。
- **anolis 探针**：经 cred 文件 curl INSERT `zz-mes-migration-probe-anolis-1` → 回读 occurred_at/kind/quantity 全对（anolis 侧只新增一个 0600 cred 文件，其余零写入）。
- **查询级探活**：keepalive 新码 `ch_mes_ping()` → True（打的就是 mingda:15221）；mingda query_log 有 INSERT/SELECT 逐条记录（取证能力在位）。
- **系统错误**：mingda system.errors 仅 4 条且全部是我方迁移/调试自产（WRONG_PASSWORD×1=无凭据测试、SYNTAX_ERROR/UNKNOWN_DATABASE=HTTP 多语句不支持的一次失败、UNKNOWN_IDENTIFIER=query_log 列名笔误），零生产错误。

## 5. 事故与偏差（如实登记）

1. **keepalive 竞态（唯一事故，已闭环）**：13:06:45 巡检侧（主代理手工复活，见巡检日志 13:1x 条）拉起的 keepalive 与我 keepalive.py 改码**竞态**——它加载了旧码（CH=127.0.0.1:5221），向**锚点**写了 6 行 keepalive 记账（13:06:46-13:07:46）；但它同时拉起的两调度器已加载新码，正确写 mingda。处置：13:15:48 kill 旧 keepalive → 13:15:50 新码常驻（pid 553898）；6 行竞态行已按 event_id 去重检查后**追平导入 mingda**（导入前核验 mingda 已有 0 行同 event_id）。教训：改码前应先确认守护层静止——本次 keepalive 12:21 已死，我按其"死亡态"规划，未防其被外部复活。**影响面**：锚点多 6 行新数据（违背"不写新数据"意图约 7 分钟），零丢失（已追平），零错误记账。
2. **mcode-dispatch 崩溃一次**：同一竞态窗内它被旧 keepalive 以"改码中间态"文件拉起（`_mes_conn` 先引用后定义）即崩，30s 后被 keepalive 以修复后文件重拉成功——无数据影响，已自愈。
3. **本地 MV 陈旧行（迁前已存在，未传播）**：锚点 `af_mes.mes_line_hour` 含第一代存量陈旧行（bench/bench-trial @1970-01-01 与 @10-20 04:00，与现役 mes_event 不符——现役该小时只有 bench-void 1524/60074142）。mingda MV 由导入数据干净重建，与 raw 逐字相符（04:00 小时 MV=raw：1524/60074142 ✅）。即：**账本（mes_event）零丢失，MV 差异是本地陈旧、非迁移损失**。

## 6. 资源与既有面

- **mingda 磁盘**：部署前 30G 余（76% 用）→ 部署后 **29G 余（77% 用）**，`/root/ch-mes-factory/` 合计 742M（二进制 734MiB + 数据/日志少量）。**高于 25G 停手线**（余量贴近，后续 mingda 布镜像需留意，已报）。
- **既有服务零接触**：未碰 mingda-forms/edgenet-pool/edgenet-broker/hf-sni-router/nginx/vault/postgres/node/python3、在役 caddy 容器、11 个 Exited company-* 容器（含 clickhouse——未复用未启动）；未新增 systemd 单元/防火墙规则；本厂 CH 为独立原生进程。
- **本机锚点**：`~/ch-mes` 实例保持运行（pid 207700，127.0.0.1:5221/5222），**只读 48h 回滚锚**（至 10-24 下午）：无写入方指向它（13:07:46 后零新行，实测冻结 9,611 行）；未设 config 级 readonly——那会阻断回滚写入，"不写新数据"由写入方全回指保证（并用 query_log 可查静默）。
- **范围外遗留（未动，报运营者裁）**：①anolis 自有 CH（pid 50003，af_mes.mes_event 仅 1 行探针、无生产写入方，anolis-ch-mes-guard.sh 保底）——本次未并库；②锚点 `mes.*` 四张遗留表（events_mt 1.02M 行/15MiB、bench_events 1M/11.16MiB、events_repl 1.02M/13.68MiB、agg_hourly/hourly_agg 少量，S0 第一代账本，现无写入方）仍在锚点，未迁。

## 7. 回滚（一行命令）

**写入方回指锚点 + 调度栈重启**（新码读 cred 文件，回滚无需改码）：
```bash
cd /home/pan-ding/workspace/agent黑灯工厂 && echo "http://127.0.0.1:5221" > ~/.config/mes-ch/url && pkill -f "tools/factory-sched.py"; pkill -f "tools/factory-keepalive.py"; sleep 2; setsid nohup python3 tools/factory-keepalive.py >> /tmp/factory-keepalive.out 2>&1 </dev/null & sleep 35; pgrep -af "factory-sched.py|factory-keepalive.py" | grep -v grep
```
** Mingda 期新事件回流锚点**（按需；谓词剔掉已在锚点的 6 行竞态行与未来日期存量行）：
```bash
ssh mingda-bench 'cd /root/ch-mes-factory && ./bin/clickhouse client --host 127.0.0.1 --port 15222 --user default --password "$(cat .pw)" --query "SELECT * FROM af_mes.mes_event WHERE occurred_at > '"'"'2026-10-22 13:07:46'"'"' AND occurred_at < '"'"'2026-10-23'"'"' FORMAT JSONEachRow"' | curl -s --data-binary @- "http://127.0.0.1:5221/?query=INSERT INTO af_mes.mes_event FORMAT JSONEachRow"
```
**停止 mingda 实例**（可选）：`ssh mingda-bench 'kill $(cat /root/ch-mes-factory/ch.pid)'`。
**反向再迁移**：重写 cred 文件为 mingda 地址 + 重启调度栈（一行，同上形态）。

## 8. 验证命令（供巡检/红队）

```bash
# mingda 健康（带认证；口令在 0600 cred 文件，勿落转录）：
curl -s -u "default:$(cat ~/.config/mes-ch/url | sed 's|http://default:||;s|@100.64.0.2:15221||')" "http://100.64.0.2:15221/ping"
# 账目（本机锚点应冻结 9611；mingda 只增不减）：
curl -s "http://127.0.0.1:5221/?query=SELECT count(),sum(quantity),min(occurred_at),max(occurred_at),uniqExact(event_id) FROM af_mes.mes_event FORMAT TSVWithNames"
# 锚点无新写入的静默证据：本机 CH query_log 13:07:46 后无 INSERT
curl -s "http://127.0.0.1:5221/?query=SELECT count() FROM system.query_log WHERE event_time > '2026-10-22 13:07:46' AND query ILIKE '%INSERT%' FORMAT TSV"
```

## 9. 更新记录

| 时间 | 身份 | 事件 |
|---|---|---|
| 2026-10-22 12:5x-13:2x | 修理组子代理（step-5-preview） | 勘察→部署→迁移→对账→回指→重启→双探针→落账，全过程本文档；事故与追平见 §5 |
