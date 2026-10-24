# MES ClickHouse @ mingda-website 纳入 systemd 托管 · 交付报告

- 日期：2026-10-22（14:1x–14:5x）
- 身份：修理组子代理（step-5-preview 载体）
- 决策来源：运营者决策"做 systemd"（消除"机器重启即失联"隐患，D-27 同类坑；巡检日志 14:2x 行登记）
- 对象：mingda-website（100.64.0.2，ssh 别名 mingda-bench）`/root/ch-mes-factory/`，CH 26.7.34.3 原生实例，15221(HTTP)/15222(native)

## 1. 勘察结论（单元设计的现实依据）

**进程树真相（关键）**：`clickhouse server` 启动后会自行 re-exec 出**内建 watchdog**（comm=`ClickHouseWatch`，cmdline=`clickhouse-watchdog server --config-file=…`，二进制 `/root/ch-mes-factory/bin/clickhouse` 内含 `CLICKHOUSE_WATCHDOG_ENABLE/RESTART/NO_FORWARD` 字符串），watchdog 再 fork 真正的 server 子进程。切换前形态：

```
nohup(bash 已退出) → 3334214 ClickHouseWatch → 3334225 clickhouse server（持 15221/15222）
```

即 **MainPID 天然是 watchdog，不是 server**；`ch.pid` 里记的是 watchdog pid（start.sh 的 `$!`）。watchdog 语义实测：收到 SIGTERM 会转发给 server 子进程并等其退出，自身以 143（128+SIGTERM）退出；server 子进程被 SIGKILL 时 watchdog 打 `<Fatal> Child process was terminated by signal 9` 后退出，把恢复权交给外部 supervisor。

**启动语义（必须复刻）**：cwd=`/root/ch-mes-factory` + `--config-file=/root/ch-mes-factory/config.xml` 显式指定（start.sh 注释载明的"双保险"：防 cwd 错致 CH 静默走 embedded config——MES 500 根因链一环），argv 另带 `-- --http_port 15221 --tcp_port 15222 --path /root/ch-mes-factory/data`。config.xml 内 path/tmp_path/user_files_path/format_schema_path/logger 全为绝对路径，不依赖 cwd；logger 写 `/root/ch-mes-factory/log/server.{log,err.log}`。

**自启面排查（与任务预判的差异，如实说明）**：任务描述"先从 crontab/自启脚本里摘除 watchdog 条目"。**实测 crontab -l、/etc/cron.d/、/etc/rc.local、/etc/profile.d/ 均无任何 ch-mes/clickhouse 条目**（crontab 仅 qcloud stargate/mem-watch/ssh-blockssh 三条既有业务项）。该 watchdog 是 CH 二进制内建机制而非独立脚本/定时任务，**没有可摘的自启条目**；防双实例的实际手段=切换时直接 TERM 停掉进程树 + start.sh 加警示头（见 §5）。另核验：本机 tools/factory-keepalive.py 对 MES 只探活告警、明确"跨机自动拉起越权"不做，无远端抢起面。

## 2. 交付物

### 2.1 单元文件 /etc/systemd/system/clickhouse-factory.service（全文）

```ini
# MES ClickHouse（本厂自有实例）—— mingda-website @ tailnet 100.64.0.2
# 端口 15221(HTTP)/15222(native)，数据 /root/ch-mes-factory/data（MergeTree 持久化）。
# 2026-10-22 由修理组纳入 systemd 托管（原 nohup 常驻：CH 自带 watchdog pid + server
# 子进程，无自愈重启保障=机器重启即失联，D-27 同类坑）。启动语义逐项复刻
# /root/ch-mes-factory/start.sh：cwd=实例目录 + --config-file 显式指定（防 cwd 错
# 致静默走 embedded config——MES 500 根因链一环）+ --http_port/--tcp_port/--path。
# 注意：clickhouse server 会自行 re-exec 出内建 watchdog（comm=ClickHouseWatch）作为
# 父进程并 fork 真正 server 子进程，故 MainPID=watchdog；server 子进程崩溃由内建
# watchdog 拉起，watchdog 本身死亡由本单元 Restart=always 兜底（双保险）。
# 既有 mingda 网站业务/在役 caddy/11 个 Exited company-* 容器零接触；User=root 保持
# 实例现有属主不变；口令不在本单元出现（users.xml 0600 + healthcheck 从 .pw 读）。
[Unit]
Description=MES ClickHouse factory instance (/root/ch-mes-factory, HTTP 15221 / native 15222)
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/ch-mes-factory
Environment=HOME=/root
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=TZ=Asia/Shanghai
ExecStart=/root/ch-mes-factory/bin/clickhouse server --config-file=/root/ch-mes-factory/config.xml -- --http_port 15221 --tcp_port 15222 --path /root/ch-mes-factory/data
ExecStartPost=/bin/bash /root/ch-mes-factory/healthcheck.sh
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
SuccessExitStatus=143 SIGTERM
RestartSec=5
LimitNOFILE=262144
TimeoutStartSec=180
TimeoutStopSec=120
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

指令逐项理由：

| 指令 | 值 | 理由 |
|---|---|---|
| Type | simple | watchdog 常驻前台不 daemonize（实测 nohup 形态即前台进程，PPid=1）；notify 型无必要 |
| ExecStart | 复刻 start.sh 命令 | cwd 由 WorkingDirectory 负责；`--config-file` 双保险之一保留；argv 与切换前逐字一致 |
| WorkingDirectory | /root/ch-mes-factory | 复刻 start.sh 的 `cd`（双保险之二） |
| User | root | 任务要求+实例现有属主即 root，不改属主 |
| Environment | HOME=/root、PATH=标准集、TZ=Asia/Shanghai | HOME/PATH 取自切换前 watchdog 进程 environ 实测；TZ 对齐 config.xml `<timezone>` |
| ExecStartPost | healthcheck.sh | 等 15222 LISTEN + 认证 /ping=Ok. 才算起成功；失败→unit failed→Restart=always 重试（oneshot 语义由 bash 脚本退出码承载） |
| ExecStop | /bin/kill -TERM $MAINPID | 实测 watchdog 收 TERM 会转发 server 并等其优雅退出；配合默认 KillMode=control-group，即使转发落空剩余进程仍收 TERM，TimeoutStopSec 后兜底 SIGKILL |
| Restart / RestartSec | always / 5 | watchdog 自身死亡（如被 OOM/误杀）由 systemd 兜底；server 子进程崩溃时 watchdog 打 Fatal 退出，同样落到本重启（双保险见 §4 演练） |
| SuccessExitStatus | 143 SIGTERM | 实测发现：watchdog 被 TERM 时以 143 退出，systemd 会记 "Failed with result 'exit-code'"（纯报表噪声，stop/restart 语义未受影响）；加此行后优雅停机不再误报失败 |
| LimitNOFILE | 262144 | CH 官方建议值；切换前实测用量 166 fd，留足余量 |
| TimeoutStartSec | 180 | 覆盖 healthcheck 90s 预算+启动 |
| TimeoutStopSec | 120 | MergeTree 优雅停机（含 query_log flush）足量；实测 2s 内完成 |
| After | network-online.target tailscaled.service | **关键**：15221/15222 绑定 `100.64.0.2`（tailnet IP），开机必须先有 tailscaled，否则 CH 绑定失败退出进重启循环；Wants=network-online 仅为排序提示不强依赖 |

### 2.2 健康检查 /root/ch-mes-factory/healthcheck.sh（全文，0750 root:root）

```bash
#!/usr/bin/env bash
# clickhouse-factory.service 配套健康检查（systemd ExecStartPost，oneshot 语义）。
# 判据（两个都过才算起成功）：
#   ① native 端口 15222 处于 LISTEN；
#   ② 带认证 GET http://127.0.0.1:15221/ping 返回 "Ok."（口令从 0600 的 .pw 读，
#      不落 argv 字面量、不进任何日志/文档——密钥纪律）。
# 超时未过 → 非零退出 → 本 unit 启动失败 → Restart=always 按 RestartSec=5 重试。
# 总预算可用环境变量 CH_HEALTHCHECK_TIMEOUT 覆盖（默认 90s，须 < 单元 TimeoutStartSec=180）。
set -euo pipefail

CH_HOME=/root/ch-mes-factory
HTTP_PORT=15221
NATIVE_PORT=15222
TIMEOUT=${CH_HEALTHCHECK_TIMEOUT:-90}

deadline=$(( $(date +%s) + TIMEOUT ))

# ① 等 native 端口 LISTEN
while true; do
    if ss -tln | awk "{print \$4}" | grep -q ":${NATIVE_PORT}\$"; then
        break
    fi
    if (( $(date +%s) >= deadline )); then
        echo "healthcheck: 端口 ${NATIVE_PORT} 在 ${TIMEOUT}s 内未进入 LISTEN" >&2
        exit 1
    fi
    sleep 1
done

# ② 等带认证 /ping=Ok.
while true; do
    resp=$(curl -s --max-time 3 -u "default:$(cat "$CH_HOME/.pw")" \
        "http://127.0.0.1:${HTTP_PORT}/ping" 2>/dev/null || true)
    if [[ "$resp" == "Ok." ]]; then
        echo "healthcheck: ${NATIVE_PORT} LISTEN 且 /ping=Ok. —— clickhouse-factory 就绪"
        exit 0
    fi
    if (( $(date +%s) >= deadline )); then
        echo "healthcheck: /ping 在 ${TIMEOUT}s 内未返回 Ok.（末次响应=${resp:-<空>}）" >&2
        exit 1
    fi
    sleep 1
done
```

密钥纪律：口令只从 0600 的 `/root/ch-mes-factory/.pw` 读取（与 start.sh 同做法）；单元文件、healthcheck、本报告均不含口令明文。

## 3. 切换实录（防双实例）

1. 14:2x 先给 `/root/ch-mes-factory/start.sh` 加警示头（"已由 systemd 接管，勿直接执行"+应急流程），再动进程。
2. `kill -TERM 3334214`（原 nohup watchdog）→ **2 秒内 watchdog 与 server 子进程双双退出**（TERM 转发语义实测确认）；`pgrep -a clickhouse` 空、`ss -tln` 15221/15222 全部释放。
3. `systemctl daemon-reload && systemctl enable --now clickhouse-factory.service` → Created symlink multi-user.target.wants，rc=0。
4. 起后 1 秒 healthcheck 通过（日志：`healthcheck: 15222 LISTEN 且 /ping=Ok.`）。

## 4. 验证证据（五件）

**① systemctl status active + 日志无错**：`Active: active (running)`，`UnitFileState=enabled`，`NRestarts` 随演练递增符合预期；journal 全量 grep error/exception/fail 仅剩 benign 的 "Logging errors to …server.err.log" 行（切换前 13:0x 的认证失败/语法错历史行不属本轮）。

**② 端口由 systemd 托管进程持有**：

```
LISTEN 100.64.0.2:15221 users:(("clickhouse",pid=3386508,…))
LISTEN 100.64.0.2:15222 users:(("clickhouse",pid=3386508,…))
LISTEN 127.0.0.1:15222  users:(("clickhouse",pid=3386508,…))
LISTEN 127.0.0.1:15221  users:(("clickhouse",pid=3386508,…))
```

pid 3386508 位于 `CGroup: /system.slice/clickhouse-factory.service`（MainPID=watchdog 3386495，server 为其子进程）。

**③ systemctl restart 演练**：14:27:08 restart → **~1s 恢复就绪**（远小于 30s 要求）；切换前快照 count=9847 / sum(quantity)=2131877686 / 全序 TSV md5=`3a8621ed6d76ccee0b319c57ad97b712`，切换后逐字一致（期间无新写入）。journal 停/启序列干净（Stopping→Stopped→Starting→healthcheck→Started），无 SIGKILL 残留。修复 SuccessExitStatus 后第二次 restart（14:28:05）停机段不再出现 "Failed with result 'exit-code'"。

**崩溃自愈双演练（Bonus，验证双保险）**：
- SIGKILL server 子进程（3385336）→ 内建 watchdog 打 `<Fatal> Child process was terminated by signal 9` 退出 → systemd Restart=always 接手 → **~7s 恢复**（RestartSec=5+启动~2s），NRestarts=1，数据完好（count 未减，仅正常新增）。
- SIGKILL watchdog（MainPID 3385593）→ 单元级重启 → **~7s 恢复**，NRestarts=2，四端口全部回归。
- 结论：server 死/wathdog 死两条路径都收敛到 systemd 重启，"机器重启即失联"与"进程猝死无人拉"两个坑同时堵死。

**④ 主机重启演练：跳过（如实说明）**。该机承载在役网站业务（mingda-forms 表单接收 tRPC、nginx :80、vault、postgres、node×2、python3、在役 company-caddy-1 容器），`systemctl reboot` 会中断全部既有业务，按任务规则"若重启演练会中断该机既有业务则跳过"——**未执行主机重启**。开机自恢复由单元语义保证：`enabled`（multi-user.target.wants 符号链接已在）+ `After=tailscaled.service`（100.64.0.2 是 tailnet IP，先 tailscaled 后 CH，避免绑定失败空转）+ `Restart=always`（即使开机早期失败也会每 5s 重试至成功）。下次计划内维护窗口可低成本补做（届时既有服务也会重启，无额外代价）。

**⑤ 双机 MES 探针（写入+回读）**：
- 本机 pandev-comp：`systemd-switch-probe-local-20261022T143009`（kind=probe_write）INSERT(JSONEachRow,POST) OK → 回读 7 字段全中；写入后 count=9856。
- anolis：`systemd-switch-probe-anolis-20261022T143021` 同样 INSERT OK → 回读全中。
- 生产写入方 bench-mes.py 用的正是 JSONEachRow POST 同款（探针首版误用 GET 携 VALUES 被 CH 26.7 拒 500，改 POST 即通——非实例回归，生产链路未受影响，期间 count 持续自然增长佐证）。

## 5. 清理与防双实例收尾

- `/root/ch-mes-factory/start.sh`：保留原样+顶部警示块（管理命令走 systemctl；直接跑会与单元抢端口；应急须先 `systemctl stop` 确认端口释放）。`bash -n` 通过。
- 自启面终检：`crontab -l` 无 ch 条目；`/etc/cron.d/`、`/etc/rc.local`、`/etc/profile.d/` 无 ch-mes 引用（本就没有，见 §1）；keepalive 侧只探活告警不拉起。
- `ch.pid` 仍留旧值 3334214（已死），单元不读该文件；start.sh 的防重入守卫对死 pid 会放行——这正是警示头存在的原因，未删除该文件（最小干预）。
- 日志：systemd 下 stdout/stderr 进 journal；config.xml logger 仍写 `/root/ch-mes-factory/log/server.{log,err.log}`；`log/console.log` 不再增长（仅 nohup 时代使用），已说明避免误判。

## 6. 零接触证明

既有服务切换后全部 active：mingda-forms / edgenet-pool / edgenet-broker / nginx / vault / tailscaled / docker；docker 在役 company-caddy-1 Up 4 周未动；Exited 容器 11 个（10 company-*+echo-fixture）原样在场；未新增防火墙规则；未复用未启动任何 gov 容器。mingda 盘 77%（29G 余）不变。

## 7. 恢复/应急命令速查

```bash
# 日常管理
systemctl status clickhouse-factory.service
systemctl restart clickhouse-factory.service
journalctl -u clickhouse-factory.service -f

# 失联自愈（单元 enabled，开机/崩溃均自动拉起；5s 一次重试）
# 手动兜底：
systemctl restart clickhouse-factory.service

# 应急：确认单元已停、端口释放后，才可人工跑旧脚本
systemctl stop clickhouse-factory.service
ss -tln | grep -E ':1522[12]'   # 应无输出
/root/ch-mes-factory/start.sh   # 跑完记得 systemctl start 交还托管

# 数据位置（MergeTree 持久化，勿删）
/root/ch-mes-factory/data/
```

## 8. 遗留与建议（不擅自动手）

- 主机重启演练未做（§4④），建议下次既有业务维护窗口顺带验证并回收本文档该节状态。
- `log/console.log` 成为历史文件，可后续择机归档删除（当前 178B，无紧迫性）。
- healthcheck 的 `/ping` 判据不覆盖"查询级 500"（MES 500 类软故障 ping 仍返回 Ok.）；查询级探针属 D-30 单范围，未越权并入本单元。

## 9. 纪律事故自首：CH default 用户口令泄入子代理转录（待轮换）

勘察第 5 步为确认本机消费方凭据文件格式，`cat ~/.config/mes-ch/url` 将该 URL 内嵌的 default 用户口令明文带入了本子代理转录（0600 文件被整文件打印，2026-09-28 consumer key 先例、10-21 gov 网关口先例同款）。**未写入任何工作区文档/交付物（已 grep 全库 .md 零命中）**，但转录本身按纪律视为已泄。按本工作区先例（"泄入转录→登记待运营者轮换"）**未自行轮换**——轮换需同步 mingda users.xml+`.pw` 与本机/anolis 两处 0600 cred 文件并涉及在飞 bench 写入方，属运营者裁决面。

建议轮换流程（供运营者参考，未执行）：①mingda 生成新口令（`openssl rand -hex 24`）更新 users.xml `<password>`+`.pw`（0600 不变）；②`SYSTEM RELOAD CONFIG` 热加载免重启；③更新本机与 anolis 的 `~/.config/mes-ch/url`（0600）；④双机探针写入+回读验证；⑤旧口令按已泄处理。MES 数据为 bench 遥测，敏感度低，但纪律不因敏感度打折。
