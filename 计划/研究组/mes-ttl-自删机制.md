# MES 遗留数据"连续 7 天无人调用即自动删除"机制 · 设计与交付（2026-10-22，修理组子代理 step-5 载体）

> 运营者决策单（2026-10-22 14:2x 主代理派发）：为**本机旧锚点 ClickHouse**（http://127.0.0.1:5221，
> 26.7.34.3，库 `af_mes` + 库 `mes`）的遗留数据做"连续 7 天无人调用即自动删除"机制。
> **af_mes.mes_event（现役活账本）绝对不动，永久豁免；gov 零接触；密钥零明文。**
> 结论：**机制已落成并全流程演练通过；当前处于"只观测不删"的观察期（arming 未放置）。**

---

## 1. 对象与豁免

| 类 | 对象 | 现状（2026-10-22 实测） | 删除粒度 |
|---|---|---|---|
| A | `mes.events_mt` | 1,020,000 行 / 14.99 MiB | 整表（归档后 DROP TABLE） |
| A | `mes.bench_events` | 1,000,000 行 / 11.16 MiB | 整表 |
| A | `mes.events_repl` | 1,016,045 行 / 13.68 MiB | 整表 |
| A | `mes.agg_hourly` | 3,222 行 / 50.00 KiB | 整表 |
| A | `mes.hourly_agg` | 3,222 行 / 1.55 MiB | 整表 |
| B | `af_mes.mes_line_hour` 的第一代陈旧行 | 全表 73 行，其中 **4 个陈旧键**：`bench@1970-01-01`、`bench@2026-10-20 04:00`、`bench-trial@1970-01-01`、`bench-trial@2026-10-20 04:00`（与现役 mes_event 对不上；mingda 侧该表已随迁移干净重建，此仅指锚点存量） | 行集（仅当整表连续 7 天无查询才删其中陈旧行；表仍在用就一行不删） |
| 豁免 | `af_mes.mes_event` | 9,611 行，现役活账本（MES 迁 mingda 后本锚点为只读回滚锚） | **永久豁免，任何模式/arming 下零动作** |
| 豁免 | `af_mes.mes_line_hour_mv` | 现役物化视图（mes_event→mes_line_hour 聚合链） | 永久豁免（删之断现役管道） |

对象清单是**白名单制**（内置默认清单，`--objects-file` 可覆盖但拒绝包含豁免 id）；不在清单内的表
（含全部 system.*、af_mes 其余表）永不进入候选。豁免清单硬编码于执行器，objects 文件无法覆盖。

## 2. 判定式一：调用探测（"某对象最近 7 天是否被查询过"）

数据源 = `system.query_log`（config.xml 已开，14 天 TTL，flush 7.5s；**10-22 MES 500 修复重启后
才开始有记录**，最早一条 2026-10-22 09:30:14——这决定了首上线前 7 天必然只观测，见 §4）。

对每个对象（db.table），一条 query_log 行计为"访问"当且仅当满足其一（**两路覆盖**）：

1. **tables 数组**含 `"<db>.<table>"`（解析级，覆盖 SELECT/INSERT/DROP/ALTER/OPTIMIZE 等）；
2. **query 文本**含限定名 `<db>.<table>`（词边界，防 `events_mt__ttl_verify` 之类前缀误配）；
3. **query 文本**含裸表名 `<table>` 且 `current_database = <db>`；
4. **query 文本**含 `SHOW TABLES FROM <db>` / `USE <db>`（数据库级内省，**保守计为对该库全部对象的访问**——曾实测到 12:56:16 一条 `SHOW TABLES FROM mes` 把 5 张遗留表全部标记为已访问，符合设计）。

`last_accessed_at` = 保留期内命中行的最大 `event_time`；"7 天无调用" = 最近 7 天窗口内无命中行。

**工具自身不自我续命**：执行器所有查询带 `User-Agent: mes-ttl-sweep/1.0`，探测时整体排除。
附加规则（实测发现的 CH 行为）：ClickHouse 对 HTTP INSERT 会在服务端把查询重写为
`INSERT INTO db.tbl (col, ...) FORMAT <fmt>` 并以**空 UA** 单独记入 query_log（与原查询两条并存、
不共享 query_id；且原查询的 tables 数组**不含** MV 目标、重写条目才含——是原查询的超集）。
归属规则：**同一秒内存在带工具 UA 的 INSERT 原查询、且其 tables 数组是重写条目 tables 的
子集时，该重写条目归工具身份一并排除**。不能用集合相等（MV 场景失效），更不能一刀切排除
重写条目——生产上 MV 目标表（mes_line_hour）的"被写入"信号只存在于重写条目，误排除会漏判
真实访问（演练中实证过这两种错法）。

**历史覆盖检查（coverage）**：判定"7 天无调用"前，要求 query_log 在**最近 7 天（含今天，服务器
本地日）每天都有至少一条记录**。CH 停机/日志未开的日期不计覆盖——宁可漏判（不删）不可错判。

## 3. 判定式二：陈旧行（对象 B，可复算）

对 agg 表逐 (line_id, hour) 键聚合，与 raw 表同时段聚合做 anti-join：

```sql
SELECT l.line_id, toString(l.hour) AS hour,
       sum(l.event_count) AS event_count, sum(l.quantity_sum) AS quantity_sum,
       max(e.n) AS raw_n
FROM af_mes.mes_line_hour l
LEFT JOIN (
    SELECT line_id, toStartOfHour(occurred_at) AS hour, count() AS n
    FROM af_mes.mes_event GROUP BY line_id, hour
) e ON l.line_id = e.line_id AND l.hour = e.hour
GROUP BY l.line_id, l.hour
```

- `raw_n` 为空（该键在对应时段的现役 raw 中不存在）→ **陈旧，可删**；
- `raw_n` 存在但与 agg 的 `event_count` 不符 → **仅告警**（数据质量信号，不删；生产实测 0 条）；
- `raw_n` 存在且相符 → 健康行，不动。

复算方式：上面 SQL 原样执行即可。删除动作 = `DELETE FROM af_mes.mes_line_hour WHERE (line_id, hour)
IN (...)`（ClickHouse lightweight delete，SummingMergeTree 实测可用，删除后键过滤计数归零）。

## 4. 自 arming 保守判定（双观测）

一个对象只有在**连续两次巡检观测（间隔 ≥24h）都判定"7 天无调用"**时才可删除：

- 每次巡检把判定结果（idle/last_accessed/coverage）追加进状态文件 `工具状态备份/mes-ttl-state.json`；
- 可删条件 = 最近两次观测均 idle **且** 两者时间戳间隔 ≥24h（同一天内跑两次 streak 会到 2 但
  gap≈0，**不可删**——演练实证）；
- 中间任何一次观测判"被访问"，连续计数清零；
- 加上 §2 的 coverage 要求：**首上线后前 7 天 query_log 覆盖不满，全部对象只观测不删**
  （dry-run 语义内置，无需人工干预）。

因此时间线下限：query_log 自 10-22 09:30 起有记录 → 最早 10-29 起 coverage 才可能满足；
再叠双观测 ≥24h → **最早 10-30 前后才可能出现"可删"判定**；且还须 arming 放置（§6）才真删。
本机制不存在"刚上线即删"的路径。

## 5. 执行器

- 路径：`tools/mes-ttl-sweep.py`（Python 3 标准库，无第三方依赖；对 CH 走 HTTP，含 3 次指数退避
  重试——吸收 10-22 MES 500（code 241）历史教训；单实例 flock，防 timer 与手动跑重叠）。
- 模式：`--dry-run`（**默认**，只观测记录）/ `--enforce`（执行态）。
- `--enforce` 仍须 **arming 文件** `工具状态备份/mes-ttl-arming.json` 存在且 `{"armed": true, ...}`
  才真删；否则自动降级干跑并在日志明示。**arming 由主代理在观察期结束后手动放置**（当前未放置）。
- 其他入参：`--ch-url`（默认 http://127.0.0.1:5221，支持 user:pass@ 形式转 Basic，本锚点无鉴权）、
  `--objects-file`、`--state-file`、`--arming-file`、`--archive-root`、`--evidence-file`、`--log-file`
  （生产全部走缺省路径；演练用演练专属路径，与生产状态物理隔离）。
- 对象表不存在（已被删/从未建）→ 记 `absent`，不报错、不重删。
- **视图依赖闸**（2026-10-22 15:1x 增补，实测驱动）：CH 允许 DROP MV 的源表/目标表而留下悬空 MV
  （实测两种删法都不报错）。删表前若存在把它当源（FROM）或当目标（TO）的 MV/视图，且该视图
  **不在本运行可删集合**内（不在对象清单，或未达双观测判定），则拒绝删除并记
  `blocked-dependent-view`（fail-closed）。依赖视图若是对象清单成员且同样可删，则各自独立归档
  删除（顺序按清单序，源表先删时悬空窗口仅数秒且无写入方，无害）。视图对象的归档=DDL only
  （SHOW CREATE TABLE 即完整 CREATE MATERIALIZED VIEW，无自有数据），DROP TABLE 对 MV 可用。
  依赖可见性：即使只观测，evidence 的 `extra.dependent_views` 也会记录（不等可删判定），
  供运营者决定是否把依赖视图纳入清单。
- 任何归档/自检失败 → **fail-closed**：记 `error`，不删，半成品归档文件清除。

## 6. 调度：systemd user timer（选型理由与安装状态）

| 项 | 值 |
|---|---|
| 单元 | `~/.config/systemd/user/mes-ttl-sweep.service`（Type=oneshot，ExecStart 带 `--enforce`）+ `mes-ttl-sweep.timer` |
| 日程 | `OnCalendar=*-*-* 04:30:00`，`Persistent=true`（停机错过则开机后补跑一次） |
| 安装状态 | **已 enable+now（2026-10-22 14:5x）**，`systemctl --user list-timers` 在役，下次 2026-10-23 04:30 CST；已手动触发一次验证 wiring（Result=success，journald 全链可见） |
| 日志 | stdout 进 journald（`journalctl --user -u mes-ttl-sweep`），同时落 §7 两个留证文件 |

**选 systemd user timer 而非 cron 的理由**：①本机 pan-ding 的 Linger=yes 已实测，user manager
开机自起，无需 root；②`Persistent=true` 自动补跑停机期间错过的日巡（用户级 cron 无 anacron 不补）；
③日志走 journald，与工作区既有取证习惯一致、失败可见（`systemctl --user is-failed`）；
④不新增 root 面——系统级 timer 需 sudo，且 clickhouse-mes.service 的先例是"写了没装、归运营者"，
本单同样不碰系统面。cron 落选：用户 crontab 无补跑、无统一日志面、多一套账。

## 7. 留证（每次执行）

- 人类可读：`状态观测/mes-ttl-sweep.log`（每次执行一个块：模式/arming 状态 + 逐对象一行）；
- 结构化：`工具状态备份/mes-ttl-sweep-evidence.jsonl`（逐对象一行：对象名/行数/last_accessed/
  idle_7d/coverage/reason/streak/deletable/armed/mode/action/archive 路径/extra）；
- 归档（仅删除动作前）：`工具状态备份/mes-ttl-archive-<YYYYMMDD>/`——
  - 整表：`<table>.sql`（SHOW CREATE TABLE）+ `<table>.native`（全量 Native 二进制）+
    `<table>.meta.json`（行数/字节数/sha256/恢复命令/自检结果）；
  - 行集：`<table>.stale-rows.tsv`（待删行全量）+ `.delete.sql`（精确 DELETE 语句）+ `.keys.json` +
    `.meta.json`；
  - **删前自检**：归档后先把数据回灌进临时表 `<table>__ttl_verify_<tag>` 比对行数，通过才删；
    自检失败/行数漂移 → 放弃本次（fail-closed）。

## 8. 测试证据（2026-10-22，全流程演练 + 生产反证）

演练脚本与全部产物：`工具状态备份/mes-ttl-drill-20261022/`（`run-drill.sh` 可重跑、`drill-output.txt`
全程转录、`evidence.jsonl`、`archive/mes-ttl-archive-20261022/`）。演练对象 = `mes_ttl_drill` 库
同名副本（库名刻意避开 `mes_ttl_test`——开发期诊断查询在 query_log 里提及过后者，会按 §2 规则 2
污染访问判定；该规则本身正确）。行集对象配了对偶 raw 表，含 healthy / 计数不符 / 陈旧三类键。
`min_history_days: 0` 仅为绕过 7 天 coverage（生产清单恒为 7）。

| # | 步骤 | 结果 |
|---|---|---|
| 1 | Run A 首巡（--dry-run） | 全对象 observe；可删候选 deletable=no（streak=1<2） |
| 2 | Run A2 立即再跑（不时间旅行） | streak=2 但 gap≈0 → **deletable=no（24h 间隔闸实证）** |
| 3 | Run B `--enforce` 但 arming 缺失 | 降级干跑；deletable=yes 仍**零删除**（arming 闸实证） |
| 4 | 放置演练 arming 后 Run C `--enforce` | `events_mt` **归档后 DROP**；`mes_line_hour` 陈旧行 **DELETE**；healthy 行与"计数不符"告警行**原样保留** |
| 5 | 反证对象（`bench_events`，每 20s 被第三方 UA 查询） | 全程 idle=no / streak=0 / deletable=no，**enforce+armed 下仍零动作** |
| 6 | 删除验证 | events_mt 已不存在（system.tables 复核）；陈旧键过滤计数=0；bench_events 行数不变 |
| 7 | 归档可恢复 | events_mt 按 `.sql` 重建 + `.native` 回灌 → 3 行，与归档 **md5 逐字节一致**；陈旧行按 `.tsv` 回插 → 原值复原（4,40 / 6,60 各一行），再按 `.delete.sql` 删回终态 |
| 8 | Run D 终态 dry-run | events_mt=absent；行集 stale_keys=0；反证对象仍 accessed 零动作 |
| 9 | 豁免审计 | `af_mes.mes_event`、`af_mes.mes_line_hour_mv` 每跑都记 `exempt` 零动作（含 enforce+armed 轮） |
| 10 | 视图依赖闸 | Run C：`events_mt`/`mv_tgt`（有依赖 MV `mv_dep`、MV 不在清单）→ **`blocked-dependent-view` 拒绝删除**，表仍在；无依赖的 `hourly_agg` 同轮正常归档+删除。Run E（把 `mv_dep` 纳入扩展清单、其 streak=1）→ 仍拦截；Run E2（`mv_dep` 双观测满足）→ `events_mt`/`mv_tgt`/`mv_dep` **连删成功**，`mv_dep` 按 DDL-only 归档（meta.kind=view） |

**生产反证（四次真实执行：14:55/14:57 timer/15:10/15:19 手动 dry-run）**：5 张遗留表与
`af_mes.mes_line_hour` 均 observe（当日确有真实访问 + coverage 不满）；`af_mes.mes_event` 与 MV
记 exempt。**零删除、零触碰 mes_event**。实情登记：锚点上并无工具轮询 mes_line_hour（只有 MV 写入
与我方探测），它的最后访问是 14:23:54 的 MV 写入；按设计，锚点冻结（13:07:46 后零新写入）满 7 天后
它会进入 idle 候选——这正是对象 B 的预期触发路径，届时仍需 arming 才动手。

**新发现的依赖事实（需运营者/主代理裁决）**：`mes.mv_hourly` 是挂在 `mes.events_mt` 上、写入
`mes.agg_hourly` 的物化视图（第一代遗留，不在运营者对象清单里；query_log 自 10-22 起无它的查询
记录）。按依赖闸语义：**`mes.events_mt` 与 `mes.agg_hourly` 在 `mv_hourly` 纳入对象清单（或明确
接受悬空 MV）之前，即使满足全部判定也不会被删**（evidence 的 dependent_views 字段已每跑记录）。
`mes.bench_events`/`mes.events_repl`/`mes.hourly_agg` 无依赖视图，不受影响。此决策归主代理
（执行者不自行扩权把 mv_hourly 加入删除清单）。

## 9. 回滚方法

**整表（对象 A）**——归档目录内三步（HTTP 即可，无需 clickhouse-client）：

```bash
CH=http://127.0.0.1:5221
# 1) 按归档 DDL 重建（.sql 内容原样 POST）
curl -s -X POST "$CH/?query=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(open(sys.argv[1]).read(),safe=""))' mes-ttl-archive-<日期>/events_mt.sql)" --data-binary ''
# 2) Native 全量回灌
curl -s -X POST "$CH/?query=INSERT%20INTO%20mes.events_mt%20FORMAT%20Native" --data-binary @mes-ttl-archive-<日期>/events_mt.native
# 3) 行数与 meta.json 的 rows 比对（归档时已做过回灌自检，恢复后复核即可）
curl -s "$CH/?query=SELECT%20count()%20FROM%20mes.events_mt"
```

**行集（对象 B）**：`curl -s -X POST "$CH/?query=INSERT%20INTO%20af_mes.mes_line_hour%20FORMAT%20TSV"
--data-binary @mes-ttl-archive-<日期>/mes_line_hour.stale-rows.tsv`（列序 line_id,hour,event_count,
quantity_sum）。归档目录缺 `meta.json` = 归档未完成，不可用于回滚。

## 10. 已知边界与风险（如实登记）

1. **query_log 只有 10-22 09:30 之后的历史**（MES 500 修复重启后才启用）——覆盖检查由此成为首道
   闸；若 CH 未来长时间停机，停机段不计覆盖，机制自动保守。
2. **文本匹配会把"提及表名的查询"计为访问**（含查 query_log 时 WHERE 里写了表名）——探索行为会
   重置 7 天时钟。这是保守方向的有意设计；需要探这些表时请带工具 UA 或接受时钟重置。
3. **HTTP INSERT 重写条目归属规则**的残余风险：若某客户端的唯一痕迹就是重写形态条目（如原生协议
   带显式列清单的 INSERT）且恰好与工具查询同秒同表集，可能漏判一次访问。本环境写入方全部是
   Python HTTP（原查询+重写两条并存），且双观测+arming 双闸兜底。
4. **锚点 48h 只读回滚窗（至 10-24 下午）**与本机制的关系：机制对 mes_event 只读（陈旧判定式
   必须读现役 raw），永不写/删；对 mes_line_hour 的行删除在观察期+arming 之后才可能发生，
   归档保证可回滚。若锚点在窗口后被整体退役，本机制自然空转（对象 absent），无副作用。
5. **依赖 CH 实例存活**：CH 由 clickhouse-watchdog 裸进程保活（无 systemd 托管，归运营者）；
   CH 不在时本次执行记失败退出（journald 可见），次日补跑（Persistent=true）。
6. **mutation 异步性**：行集删除用 lightweight delete，读取侧即时生效（演练实测删后立即可见归零），
       执行器仍做"键过滤计数 + 陈旧复算"双验证，失败即报 error。
7. **视图依赖闸的取舍**：依赖视图未纳入可删集合时拒绝删表（保守，可能推迟清理）；
       纳入后按清单序删除，源表先删时有数秒悬空窗口（无写入方，无害）。这是"不自行扩权"
       与"不留悬空 MV"之间的折中，决策点已交主代理（§11）。

## 11. 运维清单（给主代理）

- **待裁决项（新）**：`mes.mv_hourly`（挂 events_mt、写 agg_hourly 的第一代 MV）是否纳入对象
  清单。不纳入 → events_mt/agg_hourly 满足判定也会被依赖闸拦下（evidence 每跑记录
  dependent_views）；纳入 → 三者按各自判定独立归档删除（演练已实证连删路径）。
- **观察期结束标志**：`状态观测/mes-ttl-sweep.log` 中目标对象连续两次（间隔≥24h）出现
  `idle7d=yes(...)` 且 `deletable=yes`（最早约 10-29/10-30，前提是期间无新访问）。
- **授权删除**：在观察期满、确认无误后，放置 `工具状态备份/mes-ttl-arming.json`：
  `{"armed": true, "armed_at": "<时间>", "armed_by": "主代理", "note": "<理由>"}`。
  之后最近一次 04:30 的 timer 才会真正归档+删除。
- **日常验证**：`tail -20 状态观测/mes-ttl-sweep.log`；`tail -5 工具状态备份/mes-ttl-sweep-evidence.jsonl`；
  `systemctl --user list-timers mes-ttl-sweep.timer`；`journalctl --user -u mes-ttl-sweep -n 20`。
- **急停**：`systemctl --user disable --now mes-ttl-sweep.timer` + 删除 arming 文件（两者任一
  缺失都不再执行删除；删 arming 后已满足判定的对象也只记录不删）。
- **重放演练**：`bash 工具状态备份/mes-ttl-drill-20261022/run-drill.sh`（幂等，自动重建/清理演练库）。
