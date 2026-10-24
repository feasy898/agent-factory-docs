# anolis 自有 ClickHouse 实例退役 · 交付（2026-10-22，修理组子代理 step-5-preview 载体）

> 任务：删除 anolis 上那套自有 ClickHouse 实例（`~/ch-mes/`，pid 50003 附近），连带清理保活机制，
> 确保删后无人反复拉起、看板不报假警。运营者决策：删掉更好（MES 主链已于 10-22 迁 mingda-website）。
> 结论：**核查两项全过、归档双侧 sha256 一致、守活摘除、进程/端口清零、软删可回滚、收尾四项复验全绿。**

---

## 1. 删除前核查（任务书要求，任何一条不满足即停手）

### 核查1：无生产写入方 —— 通过

| 证据 | 读数 |
|---|---|
| `af_mes.mes_event` 总行数 | **1 行**（count()=1，sum(quantity)=1，uniqExact(event_id)=1） |
| 唯一一行内容 | `occurred_at=2026-10-21 17:58:00.000`，`kind=repair_probe`，`event_id=repair-anolis-chmes-probe-1`——即 10-21 修理组拉起该实例时的自产探针，**此后零写入** |
| 全厂 tools/ 代码 | `grep -rn "5221\|5222\|ch-mes" tools/*.py tools/*.sh`：命中处全部为注释/文档串（bench-mes/sched/mcode-dispatch/keepalive 四件的 MES 迁移说明），**无任何写入方指向 anolis**；poc-mes 脚本（af/poc/poc-mes/scripts/）打的是本机 127.0.0.1:5221/5222，与 anolis 无关 |
| anolis 本机脚本 | `grep -rn --exclude-dir=ch-mes "5221\|5222" ~/bin ~/.local/bin ~/mcode-swev ~/*.sh ~/*.py`：仅 `~/.local/bin/uv`（ELF 二进制，字节巧合命中，非脚本） |
| anolis cron | `/etc/crontab`（仅注释）、`/etc/cron.d/`（仅 0hourly 标准件）、用户 crontab（仅 ch-mes 守活自身，见 §2）——**无写入方** |
| anolis systemd | `systemctl list-unit-files` 与 `/etc/systemd/system/`+`/usr/lib/systemd/system/` 文件级 grep：**无 ch-mes/clickhouse/guard 任何单元**（在役 timer 仅 sysstat/bao-*/egress-bao/opch-ws-gc/dnf-makecache，与守活注释自述一致） |
| 网络面 | config.xml `<listen_host>127.0.0.1</listen_host>`——**只听回环，远程根本写不进来**；anolis 全 /proc 扫描无任何进程 cmdline 含 5221/5222 |
| 查询留痕 | 该实例未开 query_log（config 无该节），静默证据以 mes_event 冻结计数 + guard.log 连续 ok 行为准 |

### 核查2：守活装置定位 —— 通过

| 装置 | 位置与内容 |
|---|---|
| **用户级 crontab**（主保活） | `*/5 * * * * $HOME/ch-mes/guard.sh >> $HOME/ch-mes/guard.log 2>&1`（pan-ding 用户 crontab，条目带注释头 `# ch-mes-guard: ...保底守卫（补丁② R2；D-27 基建连续性...）`）；每 5 分钟 ping `http://127.0.0.1:5221/ping`，失败且扫 /proc 无 clickhouse server 进程时执行 `~/ch-mes/start.sh`（3 次尝试后 30min 退避，状态落 `~/ch-mes/guard-state.json`，日志 `~/ch-mes/guard.log` 5MB 截尾） |
| **CH 内置 watchdog**（进程形态） | pid 49996 `ClickHouseWatch`（`/proc/49996/exe` → ch-mes/bin/clickhouse，PPid=1），server 退出时随之退出——非独立保活，无 cron/systemd 依赖 |
| **本机 keepalive 判活对象** | `tools/factory-keepalive.py` 的 ch-mes-local 探活**打的是 mingda 100.64.0.2:15221**（MES 迁后已改指）；anolis ch-mes 仅在其注释中出现（"另有 guard.sh+用户级 crontab 保底……非产线告警面"），**不在判活/告警集合内** |
| **watch/看板** | `tools/factory-watch.py` 与 `状态/看板/{index.html,data.json}` 对 ch-mes/5221/ClickHouse **零引用**——删后不会产生假警 |

---

## 2. 执行记录（先归档后删，可回滚）

### 归档（先）

- anolis 侧打包：`tar czf ~/ch-mes-archive-20261022.tar.gz ch-mes/`（含 bin/config.xml/users.xml/start.sh/guard.sh/data/log；数据体积极小=1 行探针）
- 大小 225,634,902 B；**sha256 = `e849796c49ff2365de31fac2f2b1944ca62846a8f91bb21d1fc4868b75eb5c54`**（anolis 与本机双侧一致）
- 耐久位：**本机 `工具状态备份/anolis-ch-archive-20261022.tar.gz`**（scp 传输后复验 sha256 相同）；anolis 侧原件 `~/ch-mes-archive-20261022.tar.gz` 亦留存
- 密钥纪律：归档内 `users.xml` 含 `<password>` 字段（已设值）——**只登记字段名，口令值不进任何文档/回报/转录**；anolis `~/.config/mes-ch/url`（0600）同纪律

### 停（先摘守活，后停进程）

1. **摘守活留证**：原 crontab 整表备份至 anolis `~/crontab.bak-pre-ch-mes-retire-20261022`（diff 证实仅删守活两行：注释行+`*/5` 行），随后 `crontab -l | grep -v ... | crontab -` 清空（原表仅含守活两条）。**先摘 cron 再停进程**——杜绝 5 分钟周期内被 guard.sh 抢跑双起。
2. **停 CH**：14:26:09 `kill -TERM 50003` → **1 秒内退出**（未触发 SIGKILL  escalation）；内置 watchdog 49996 随之退出，双进程清零。

### 删（软删，非硬删）

- `mv ~/ch-mes ~/ch-mes.deleted-20261022/`（735M 全量在位：bin/config.xml/users.xml/start.sh/guard.sh/data/log/tmp/user_files/configs.d）
- cron 已无引用（§2.1）；systemd 无单元（核查2）；crontab 备份件是唯一留存引用（证据用途，有意保留）

---

## 3. 收尾验证（任务书四项）

| # | 项 | 结果 |
|---|---|---|
| ① | anolis `ss -tlnp \| grep 5221` 无监听 | **anolis 无 ss 命令**（如实替代）：`curl http://127.0.0.1:5221/ping` → rc=7 连接拒绝；`/proc/net/tcp`+`/proc/net/tcp6` 按 0x1465/0x1466 解析**零监听**；pgrep clickhouse 零进程。14:30 原 cron 触发点过后复查仍零进程（无复活） |
| ② | crontab -l 与 systemctl list-unit-files 无 guard 引用 | crontab **空**（备份 diff 为证）；list-unit-files 及文件级 grep **无 ch-mes/clickhouse/guard** |
| ③ | 本机 `timeout 120 python3 tools/factory-watch.py --once` 不新增 ch-mes/anolis 告警 | rc=0，**安灯红 0 / 黄 0**，`状态观测/alarms.log` 604→604 行**零新增**（跑前跑后 diff 为空）；报告内 anolis 段健康（/ 80%、/data 80%、ollama ok、镜像 72/120） |
| ④ | MES 主链（mingda 100.64.0.2:15221）探针写入+回读 | `tools/bench-mes.py` 实跑探针（task_id=zz-anolis-ch-retire-probe-20261022）→ **入 MES 6 行**；回读 6 行 occurred_at/kind/quantity 全对（14:27:33，reward=1 等）；mingda 总量 count=9853 持续增长、max(occurred_at) 未动。主链不受本次影响，复验通过 |

**本机锚点未动**（属迁移单的回滚锚，不在本任务范围）：pid 207700 在役，mes_event 冻结 9,611 行。

---

## 4. 回滚（一行命令）

anolis 上执行（归档与软删目录均在，数据=10-21 冻结态）：

```bash
ssh anolis 'mv ~/ch-mes.deleted-20261022 ~/ch-mes && (crontab -l 2>/dev/null; echo "*/5 * * * * \$HOME/ch-mes/guard.sh >> \$HOME/ch-mes/guard.log 2>&1") | crontab - && bash ~/ch-mes/start.sh'
```

说明：三件事一气呵成=软删目录 mv 回原位 + 恢复 cron 守活条目（注释行可选）+ 跑 start.sh 拉起；若需连同注释头一并恢复，原文在 anolis `~/crontab.bak-pre-ch-mes-retire-20261022`。归档件（本机 `工具状态备份/anolis-ch-archive-20261022.tar.gz`，sha256 e849796c…）用于硬删除场景下的整体复原。

## 5. 更新记录

| 时间 | 身份 | 事件 |
|---|---|---|
| 2026-10-22 14:1x-14:3x | 修理组子代理（step-5-preview） | 核查两项（mes_event 1 行探针/全厂无写入方/只听回环；守活=crontab guard.sh+内置 watchdog；本机 keepalive/watch/看板不判活）→ 归档（sha256 双侧一致）→ 摘 cron 守活（备份留证）→ SIGTERM 停 CH（1s 退出）→ 软删 mv → 收尾四项复验全绿（端口/cron/watch --once 零告警/MES 主链探针 6 行回读全对）。零接触：gov、anolis 其他服务、本机锚点实例 |
