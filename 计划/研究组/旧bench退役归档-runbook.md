# 旧 bench 退役归档 runbook（ADR-008 纪律的操作面）

> 2026-10-25 · G5 前置施工员编制。依据：ADR-008（af 仓 docs/adr/008-bench-retirement.md，
> 已裁决 2026-10-24）+ 在飞bench盘点-20261024.md（§3 前置条件逐条可检验）+
> mes-ttl/anolis-ch 退役单先例。本文是**操作手册**：每步给核对法与命令，
> 执行时逐项打勾登记；未满足的前置条件不跳过、不冒充。
>
> 身份纪律：本 runbook 的执行者是退役施工臂；全程登记 计划/30-遗产处置.md
> 删除记录表 + 计划/变更日志.md + 技术债 D-2/D-3/D-39 销项（ADR-008 §6）。

---

## 〇、终态与纪律（ADR-008 原文要点）

- 终态：唯一下单入口 = af 底座（af-order 门面 → af-engine 门控 → af-execline
  执行 → af-mes 记账）。bench 与业务任务同通道。
- 流程：影子对拍 → 切流（旧脚本停用进观察期，保留一行回滚命令）→ 观察期
  （跨天稳定）→ 归档（tools 脚本移 参考/legacy/bench-infra-retired-2026MMDD/，
  附退役报告）。
- 切流窗口避开每小时 :17 的 cron 巡检；停机顺序按盘点 §4（先 sched 后
  keepalive——keepalive 必须晚于其看护对象停，否则 30s 内复活一切）。

## 一、前置条件核对单（在飞 bench 清单核对法）

逐条可检验（盘点 §3 口径，核对法照抄可重跑）：

| # | 条件 | 核对命令/方法 | 判据 |
|---|---|---|---|
| 1 | 三测试扩量收官（af+mcode 两侧） | ①计划/研究组/三测试终审-20261024.md 出现扩量终读表；②本机 `ps -ef \| grep -E "af-bench\|threetest" \| grep -v grep` 空；③anolis `ssh anolis "docker ps -q \| wc -l"` = 0；④相关 results 目录 `find <results> -name results.jsonl -mmin +360` 全部超 6h | 四项全过 |
| 2 | cb-run 线收官 | `tail -5 /tmp/cb-run.log` 连续 tick `inflight=0 q=0 running=0`；`python3 -c "import json,glob;print(sum(json.load(open(p))['judged'] for p in glob.glob('/tmp/cb-dispatch/*.json')))"` | =120 且空转 |
| 3 | mcode-dispatch 收官 | `cat /tmp/mcode-dispatch/state.json`（无非 judged 项）；`cat /tmp/mcode-dispatch/dispatch.pid` 指向死进程（`ps -p <pid>` 空） | 240/240 已满足（盘点时点） |
| 4 | factory2 实验线收官 | `python3 -c "import json;s=json.load(open('/tmp/factory2-status.json'))['_summary'];print(s)"` | pending=0 且 running=0（已满足） |
| 5 | **主线 12 条 pending 臂处置裁决落地**（卡点） | 满足其一：a) 人工 -r2 补图后 /tmp/factory-status.json `_summary` pending=0；b) 计划/变更日志.md 有「放弃 D1/D3 全量臂」裁决行 + 图归档入 工具状态备份/ | **未满足（见 §五占位登记）** |
| 6 | anolis 资源面达标 | `ssh anolis "docker ps -q \| wc -l"`=0；`ssh anolis "df -h /data"` ≤85% | 0 容器已满足；水位回爬需巡检 |
| 7 | 替代面就绪（af 统一执行面等价能力） | ①af 仓 `ci/run.sh` 八门全绿；②swev-judge.py 判分核 sha256 与冻结锚 `a292547f…0617c` 逐字节一致；③F 线订单 MES 记账与 bench-mes 事件 schema 对齐（F-第四单 A/B 已证：失败路径 CH 3 行读回） | 本批 G5 后八门绿在案；F1-F4 订单链已走通 |
| 8 | 观测承接方案落地 | 本 runbook §三-2（keepalive TARGETS 改写）落码 + 计划/变更日志登记 | 施工项 |
| 9 | 本机回滚锚处置（127.0.0.1:5221 CH） | 计划/变更日志有停机/归档裁决；停后 mingda 探针绿 ≥1 天 | 待运营者裁决（非阻塞） |
| 10 | 双代理冲突面避让 | 切流前查 状态观测/巡检日志.md 最新「双代理」条目 + 向重构线协调留言 | 时点检查 |

**不满足项处置纪律**：#5 未裁决则**不得进入切流**（ADR-008 §3-3 明示属运营者
待裁决项、不阻塞退役**准备**，但阻塞切流执行）；#9 非阻塞，随观察期一并处置。

## 二、归档对象清单（ADR-008 §2 退役对象）

| 对象 | 位置 | 形态 | 归档动作 |
|---|---|---|---|
| factory-sched.py | tools/factory-sched.py（主线 main-sched + 实验线 exp-sched 两进程形态） | 常驻调度器（图 /tmp/factory{,2}-graph.json） | §三-1 |
| mcode-dispatch.py | tools/mcode-dispatch.py | 已收官派发器（state 240/240） | §三-1 |
| bench-mes.py | tools/bench-mes.py | MES 记账（含独立 CLI 直跑 + `_mes_conn` 只读查询面——**查询面先于写入面退役**，A/B 对照与审计仍用它） | §三-1（写入面）；查询面保留至观察期末 |
| af-bench 独立 CLI 直跑形态 | af 仓 crates/af-bench（`cargo run -p af-bench -- …` 直跑） | Rust CLI 直跑 bench | §三-3（仓内退役，非文件搬移） |
| MES Python 旁路直 INSERT | bench-mes.py 内 `ch_insert` 直写路径 | 绕 af-mes 的旁路 | §三-4 废除核对 |

**不退役（保留资产，ADR-008 §不退役）**：factory-watch.py（判据更新后转看护
新执行面）、出题三件套管线、swev-judge 判分核（字节冻结，新执行面同契约调用）、
/tmp 工厂运行时件直至观察期结束。

## 三、归档动作（按序执行，每步登记变更日志）

### 0. 切流前快照（证据先于变更）

```bash
TS=$(date +%Y%m%d-%H%M)
mkdir -p 工具状态备份/bench-retire-$TS
cp /tmp/factory-graph.json /tmp/factory-status.json /tmp/factory2-{graph,status}.json \
   /tmp/mcode-dispatch/state.json 工具状态备份/bench-retire-$TS/
ps -eo pid,lstart,args | grep -E "factory-sched|mcode-dispatch|factory-keepalive|factory-watch|cb-run" \
   | grep -v grep > 工具状态备份/bench-retire-$TS/processes-before.txt
```

（12 pending 臂未裁决时**必须先做图原子拷贝**——keepalive graph_guard 会在图
缺失时从备份自动恢复，直接删图会被复活成盲跑态，盘点 §4-3。）

### 1. 停机与文件归档（顺序错序会被 keepalive 复活）

```bash
# ① 派发者先死（防新工作量）：
kill <main-sched-pid> <exp-sched-pid> <cb-run-pid>       # pids 见 processes-before.txt
# ② 确认 running=0 后停 keepalive（必须晚于其看护对象）：
kill $(cat /tmp/factory-keepalive.pid)
# ③ 再停 anolis-proxy-8124（确认 mcode 线不再用后）与 ch-mes-local 锚点
# ④ 观测面最后降级：factory-watch → dash → cron obs-patrol（切流全程保安灯）
# ⑤ 文件归档（观察期满后执行）：
mkdir -p 参考/legacy/bench-infra-retired-2026MMDD
git mv tools/factory-sched.py tools/mcode-dispatch.py 参考/legacy/bench-infra-retired-2026MMDD/  # 或 mv+登记
cp tools/bench-mes.py 参考/legacy/bench-infra-retired-2026MMDD/bench-mes.py.retired  # 查询面观察期内暂留原位
# ⑥ 附退役报告 参考/legacy/bench-infra-retired-2026MMDD/退役报告.md（终值/事件数/回滚法）
```

### 2. keepalive 看护清单改 af 执行面

tools/factory-keepalive.py `TARGETS`（L1235，现 9 对象：main-sched/exp-sched/
watch/dash/cb-run/image-feed/mcode-dispatch/ch-mes-local/anolis-proxy-8124）：

- 观察期形态：TARGETS 收敛为 `["watch", "dash", "af-execline", "mes-ch"]`——
  删除六旧对象，新增 af 执行面判活（af-order/af-execline 进程或最近订单 ledger
  心跳）与 mes-ch 连通探活（mingda 100.64.0.2:15221，复用现有 `_mes_conn`）；
- `FIXES`/`CHECKS`/`DRAIN_PROBES` 同步删六旧对象条目，防 NameError；
- 改码后 `python3 -m py_compile tools/factory-keepalive.py` + `--dry` 一轮
  核对判活结论再上岗；变更登记 计划/变更日志.md（ADR-008 §2 原文要求）。

### 3. af-bench 独立 CLI 直跑面退役（仓内动作）

- crates/af-bench 保留为**库**（profile 表/suite 类型被 af-execline 依赖，
  P1 吸收方案），退役的是「独立 CLI 直跑形态」：CLI 入口（main/bin）标记
  `#[deprecated]` 或移除 bin target（以独立批施工裁决为准，本 runbook 只登记
  动作面）；
- 判据：全仓 grep 无 `cargo run -p af-bench` 生产调用路径；F 线订单一律经
  af-order 单一入口（F-首单起已如此，F1-F4a3 八笔在档为证）。

### 4. MES 旁路废除核对

- 旁路 = bench-mes.py `ch_insert` 直 INSERT（盘点 §MES：调度器直写 CH HTTP）；
- 废除判据三面：①tools/ 归档后无活动写入者（`grep -rn ch_insert tools/*.py`
  仅命中归档件）；②af 线 MES 唯一经 af-execline `mes_ch.rs`（CH sink=
  retry_outbox+event_id 对账+差量送批，F-第四单 A/B 实证失败路径 3 行读回）；
  ③mingda CH `af_mes.mes_event` 表在旁路停用后只余 af 线 station_id=
  `af-order-cli` 新事件（SELECT 采样核对）。

## 四、一行回滚命令（ADR-008 §4：切流保留回滚一行）

```bash
cd /home/pan-ding/workspace/agent黑灯工厂 && nohup python3 tools/factory-keepalive.py >> /tmp/factory-keepalive.log 2>&1 & echo $! > /tmp/factory-keepalive.pid
```

（keepalive 单进程即可按 TARGETS 复活 sched/cb-run 全链——这正是停机顺序必须
「keepalive 最后停」的原因；回滚后 5 分钟内 `tail /tmp/factory-keepalive.log`
核对看护轮次与对象活态。观察期内每停一个对象记一条 MES 事件 + 巡检日志行。）

## 五、12 阻塞臂待运营者裁决（占位登记，ADR-008 §3-3）

> **登记身份**：G5 前置施工员代登记占位；**裁决权属运营者**，本 runbook 不预设立场。

| 项 | 内容 |
|---|---|
| 对象 | main-sched 图 12 条 pending 臂：arm-d1-{glm-cp, glm-cp-max, kimi-k3, step-5, qwen30b-local, mavis-m31f} ×6 + arm-d3-同名 ×6 |
| 卡死机理 | deps 挂在 6 个终态 failed relay（scikit-learn-11310/11578/12585、matplotlib-25122、xarray-3677-r2、xarray-4687-r2，rc=1，MES failed 事件 2026-10-23 08:19–08:26 在案）；factory-sched `deps_done` 只认 done/skipped（L367-370）→ failed 依赖永久阻塞，调度器既不派发也不自愈 |
| 证据面 | /tmp/factory-graph.json + /tmp/factory-status.json（deps 实读）；/tmp/factory.log 末派发 2026-10-23 08:32:19 |
| 选项 A | 人工 -r2 补图跑完（先例：2026-10-20 同类处置）→ pending=0 后满足前置 #5-a |
| 选项 B | 运营者裁决放弃：计划/变更日志.md 登记「放弃 D1/D3 全量臂」+ 图归档入 工具状态备份/ → 满足 #5-b，退役锁死 |
| 裁决记录占位 | **【待运营者裁决：____（A/B，日期____）】** |
| 附带裁决（非阻塞，一并请示） | ①本机回滚锚 127.0.0.1:5221 ClickHouse 停机归档（48h 窗已过）；②anolis img-gc HALT 哨兵撤否；③mes-ttl-sweep 10-29 观察期满放行/撤销 |

## 六、完成定义（DoD）

1. §一 十项核对单全部打勾（#5 经裁决落地）；
2. §三 六步动作完成且 工具状态备份/bench-retire-$TS/ 与 参考/legacy/
   bench-infra-retired-2026MMDD/ 在位含退役报告；
3. 观察期跨天稳定（af 线订单照常 Closed+MES 4 行；旧链零复活）；
4. 计划/30-遗产处置.md 删除记录表 + 计划/变更日志.md + 技术债 D-2/D-3/D-39
   销项三处登记齐。
