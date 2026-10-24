# 资源管理组（研究组④）· 可续用状态账

> 本文件是**账**，不是报告：每个数字带出处与 as-of，下一轮直接接着往下写。
> 记账人：状态记账员（MiniMax-M3.1-Flash-Preview），写作时点 **2026-10-22 05:00 CST**（自测读数 as-of 04:55–04:58）。

## 0. 账本元信息

| 项 | 值 | 出处 |
|---|---|---|
| 工作流 run | `dwfrun-3dc7a361-01b2-4c76-b4ee-19c0c21836f1`（名：**研究组④资源管理组·anolis压载与统一方案**），01:27:50 起、04:54:56 仍 running，本节点（32328）为最后节点 | `~/.zcode/cli/db/db.sqlite` 表 `dwf_run`（`select id,name,status,spent_tokens from dwf_run where id=…` → 46,729,221 tokens） |
| 流程脚本 | `.zcode/workflow-runs/dwfrun-3dc7a361-01b2-4c76-b4ee-19c0c21836f1.mjs`；方法原文 `.zcode/workflow-drafts/研究组4-资源管理组.dwf.ts` | 文件本体 |
| 本轮节点账 | 16 个 ask（15 completed + 本记账节点）+ 6 个 report，node id **32118–32328**（ask 序：32118 资源测绘员 → 32123 红队·盘点核验 → 32144 补丁规划员 → 32159 红队·补丁设计审查 → 32183 补丁修订规划员 → 32196/32231/32255 补丁实施员（①②③） → 32276/32285/32298 补丁测试员（①②③） → 32307 实施员 fix1 → 32311 方案撰写员 v1 → 32315 红队·方案终审 → 32324 方案撰写员 R2 → 32328 本节点） | `dwf_node` 表（`site_id`/`actor_site_id` 映射到 `dwf_actor.name`） |
| 方法（运营者钦定） | ①先用补丁保障 anolis 不因压力 OOM、协调机器压力；②补丁测试有效后形成统一建设方案；③补丁测试用临时阈值/测试模式触发，不真制造资源压力，**MES 自守项真探活真拉起**；④红队审查一律 step-5；⑤红队不通过则先修订再进下一环 | `研究组4-资源管理组.dwf.ts` 头部注释 + 节点 32159/32315 的 system 提示 |
| 授权来源 | `计划/变更日志.md:75`（2026-10-22 01:2x 厂长条）：fix3 路线终审落地，启动**对齐/调优/可观测/资源管理四组**研究工作流，**D-26 归还路径改挂资源管理组** | 文件本体 |
| 承接技术债 | D-26 六面统一治理（`计划/技术债登记.md:33`，**未还**）为主；D-27 跨机 MES 监督（`:34`，未还）、D-24 结果目录 tmpfs（`:31`，未还）、D-17 巡检 cron 生效性（`:24`，未还）、D-30 本机 pull 通道坏（`:36`，未还）、D-34 mcode 判分链（`:42`，注明"该文件现由④资源组在管"） | `计划/技术债登记.md` |
| 红线（全程未越） | gov 生产面/非本厂资产零触碰；补丁只管本厂工作负载，一律 fail-closed、拦新不杀旧；密钥零明文；在飞臂不动；root 仅限 `状态观测/anolis待sudo清单.md` 内事项且留证 | `研究组4-资源管理组.dwf.ts:48`；终审 issue 6 判**无越权**（node 32315） |

### 0.1 记账员本轮自测（2026-10-22 04:55–04:58，全部本节点亲跑）

| 自测项 | 命令 | 输出 | 判读 |
|---|---|---|---|
| 补丁① 作者套件 | `python3 补丁/patch1-test-gate.py` | `ALL PASS (29/29)`，rc=0 | 通过（mock 层，含真实 /proc/meminfo 解析） |
| 补丁② 作者套件 | `python3 补丁/patch2-test-chmes.py` | `ALL PASS (11/11)`，rc=0 | 通过 |
| 补丁③ 作者套件 | `python3 补丁/patch3-test-imggc.py` | `ALL PASS (35/35)`，rc=0 | 通过（**注**：终审复验时为 34/35，T5c 因 mcode 在途为空判 FAIL；本节点复跑时序不同，35/35 全过——T5c 属时序敏感的假阴性，**非** fix1 带来的改善） |
| 补丁存档可重放性 | `patch -p1 -R --dry-run --forward < 补丁/补丁1-*.patch` | rc=0（tools/mcode-dispatch.py + tools/mcode-once-wrapper.sh 均 checking 通过） | 补丁① 可干净重放 |
| 同上（补丁②） | `patch -p1 -R --dry-run --forward < 补丁/补丁2-*.patch` | **rc=1，10 个 hunk 中 4 个 FAILED**（失败于 @@-2,7 / @@-25,6 / @@-74,6 / @@-103,6，即文件头 docstring/常量区） | **补丁②与补丁③改同一文件 `tools/factory-keepalive.py` 且头部 hunk 重叠**（补丁③ 的 @@-33,6 / @@-84,6 / @@-114,6 落在同一区）→ 重放必须按 ②→③ 顺序且头部需手工合并；不可各自独立重放 |
| 同上（补丁③） | `patch -p1 -R --dry-run --forward < 补丁/补丁3-*.patch` | rc=0（tools/factory-keepalive.py + tools/img-gc.py 均 checking 通过） | 补丁③ 与现役文件一致 |
| 现役 keepalive | `ps -o pid,lstart,etime -p 3614522` + `stat tools/factory-keepalive.py` | 3614522 起于 2026-10-21 22:09:34；代码 mtime 2026-10-22 04:25:35 | 现役=**旧代码**，补丁②ch-mes-local 与补丁③gc_watch 未生效 |
| 看护对象数 | `grep "看护" /tmp/factory-keepalive.log` | `常驻启动 pid=3614522 周期 30s 看护 7 对象：main-sched, exp-sched, watch, dash, cb-run, image-feed, mcode-dispatch` | **7 对象（无 ch-mes-local）**＝补丁②第 8 判活对象未上线（与上条互证） |
| 补丁①在役 | `tail -4 /tmp/mcode-dispatch.log` | `[04:55:56] mcode-dispatch 常驻启动 pid=3915427 …` + `[04:55:56] [gate] 资源闸生效: mem≥4.0G disk≥20.0G remote≥4.0G cache=60s hb=600s escalate>1800s halt>86400s` | 补丁①**在役** |
| 告警面新码 | `grep -c "ch-mes-local" 状态观测/alarms.log` / `grep -c "gc-watch" 状态观测/alarms.log` | **0 / 0** | 补丁②③的告警码在生产面**零出现**＝未生效的直接证据（生产 alarms.log 最近 200 行只有 A0/A1/A2/A4/A6/A7） |
| MES 健康 | `curl -s -m 5 http://127.0.0.1:5221/ping`；`ssh anolis 'curl -s -m 5 http://127.0.0.1:5221/ping'` | 两机均 `Ok.` | 任务前提"MES 500"**已过时**（与盘点勘误一致） |
| anolis 守卫在役 | `ssh anolis 'crontab -l; ls -la ~/ch-mes/guard.sh; tail -3 ~/ch-mes/guard.log; ls ~/img-gc-HALT'` | crontab 含 `*/5 * * * * $HOME/ch-mes/guard.sh`；guard.sh `-rwxr-xr-x 5429 10-22 02:59`；guard.log `[04:45:01]/[04:50:01]/[04:55:01] [ok] ping Ok.`；HALT 哨兵不存在 | 补丁② **anolis 侧在役** |
| anolis 水位 | `ssh anolis 'df -P /data'` | `/dev/vdb1 308519744 207522716 85252108 71% /data` | 71%，距 85% 触发线仍有量（方案外推 ~2h 可及，**但触发器未生效**） |
| GC 证据件 | `wc -l 状态观测/img-gc-evidence.jsonl` + 末两行 | 17 行；末行 `{"kind":"plan","ts":"2026-10-22 04:50:17","use_pct":71,"keep_counts":{"A":7,"B":0,"C":100}}` | 执行器可用（plan 链），自动触发器未产生任何 `trigger:true` 行 |
| 本机巡检兜底 | `crontab -l` | 无输出，rc=0（**零条目**） | 与方案 §0 一致：本机 cron 兜底**不存在**（D-17 本机面闭合为否定） |
| 引用行号复核 | `sed -n '997,1005p;1025,1028p;1058,1067p;904,906p' tools/factory-keepalive.py`；`sed -n '445,451p' tools/img-gc.py` | `:997-1005`=self_guard(exit 3 拒双实例)、`:1025-1028`=dry_run 分支在 self_guard 之前 return、`:1058-1067`=finally 删 pidfile、`:904-906`="J3 修复（补丁③R2-fix1）"注释 + 新序 spawn、img-gc `:445-451`=子解析器 `--host` 定义 + host 断言 | 方案 §5 引用的这几处行号**与现役代码逐行相符**（记账员独立复核，非转引） |
| **本轮新增异常** | `ps -eo pid,args \| grep "python3 tools/mcode-dispatch.py"` → **NO mcode-dispatch python process**；`tail -2 /tmp/factory-keepalive.log` → `[04:56:24] [mcode-dispatch] ALARM 600s 内已重启 2 次，超限停止拉起只报警（进程仍死，需人工介入）`；`state.json` 240 键**全 phase=judged** | — | **mcode 派发器当前处于死亡状态**：队列已空（240/240 judged）→ 每次拉起 5s 内"队列跑完退出"→ keepalive 防抖熔断已触发并停止拉起。**这是方案 §4-#2 抖环的升级态**（方案写的是"抖环持续"，实测已到"熔断+需人工介入"），见 §6 P0-2 |

---

## 1. 一屏摘要（下一轮先读这段）

| 环节 | 结论 | 关键数字 | 出处 |
|---|---|---|---|
| 资源风险盘点 | **10 个风险面**成盘（内存/磁盘/容器限额/内存门/本机磁盘/本机 /tmp/tmpfs 类/MES 监督/镜像增长/看护体系横向缺口） | 10 面 | node 32118 |
| 盘点红队核验 | **confirmed**（7 条 issue：1 条引用不存在、2 条数字/章节漂移、1 条"6 个而非 4 个看护对象"勘误、1 条判分容器代际误判、1 条 pid→产线映射未分、1 条如实声明未重跑项） | 7 条 | node 32123 |
| 补丁设计 v1 | 3 个补丁（①mcode 预检闸 ②anolis ch-mes 自守 ③磁盘水位自动 GC 挂钩） | 3 | node 32144 |
| 补丁设计红队审查 | **rejected**，14 条意见（**阻断 5 + 重要 4 + 次要 2 + 未击穿/已核实事实各 1**）→ 全部三条阻断被逐条接受并落到 R2 | 14 条 | node 32159 |
| 补丁 R2 实施 | 3 个补丁已落位工作区（补丁① 另含 `tools/mcode-once-wrapper.sh`） | 3 | node 32196 / 32231 / 32255 |
| 补丁测试 | ①**通过**、②**通过**、③**未过**（J3 实测抓到 spawn argv 缺陷） | 2 过 1 未过 | node 32276 / 32285 / 32298 |
| 补丁③ fix1 | 04:25:35 落盘（argv 改为 `["python3","tools/img-gc.py","apply","--host","anolis"]`，4 处同步），**端到端复验仍缺** | ⚠️ | node 32307 + 方案 §0.1 |
| 方案撰写 v1 | `设计/资源治理统一方案.md`（180 行） | 路径同上 | node 32311 |
| 方案红队终审 | **rejected**，8 条意见（主阻断=补丁→方案迁移路径无资质、6 项纸面闭环风险、keepalive 自举单点、mcode 抖环、journald root 路径假设、gov 判定无越权、MES 止损缺口、引用质量通过） | 8 条 | node 32315 |
| 方案 R2 修订 | 已重写落盘（174 行，§7 逐条映射终审意见）——**但未再经红队复审**（node 32324 之后直接到本记账节点） | ⚠️ 复审缺位 | node 32324 |

**本轮的一句话**：三个补丁**真材且真落地**（①已在线上在役、②的 anolis 侧在役、③的 img-gc 执行器可实跑），但**补丁③的自动触发路径带一个被红队测出、被作者改掉、却还没被端到端复验的缺陷**；方案 v1 因"把未过补丁写成已验证"被终审驳回，R2 已按意见改完但**没人再审一遍**——**下一循环的第一件事是复审 R2，第二件事是 keepalive 原子换血**（现役 7 对象，补丁②③ 的新代码一行都没跑）。

---

## 2. 盘点与红队核验

### 2.1 盘点（node 32118，10 面，节选风险定性）

| # | 面 | 风险定性 | 关键实测（原文摘要） |
|---|---|---|---|
| 1 | anolis 内存 | 中低 | MemTotal 125G / MemAvailable≈118.9G / Swap 32G **used=0 纯缓冲** / swappiness=10；残余：压力未经历真实高峰验证、swap 与镜像同在 /data、绕过 af-bench 直 `docker run` 无闸 |
| 2 | anolis 磁盘（/ 与 /data） | 中 | / 79%、/data 55%；闸只覆盖 /data 一条线、只在派 relay 时拦（不杀在跑臂） |
| 3 | 容器限额（**任务前提已过时，实测证伪**） | 低-中 | 护栏已在役；残余：`--memory` 未显式设 `--memory-swap` |
| 4 | 调度器内存门 | 中低 | 在役但**从未被真实压力验证**（零触发记录）；`:364-366` 记录过"经 ssh 传 awk"引号永闭坑 |
| 5 | 本机磁盘 | 中高 | 78%，余 100G；镜像侧 `docker system df` 报 Images 121/205GB |
| 6 | 本机 /tmp（tmpfs 跑产线数据，D-24 未还） | **高（本轮最高）** | 3.8G/7.5G 已过半；4196 条目 + 1713 陈旧 |
| 7 | tmpfs 类 | 低-中 | anolis /tmp 63G tmpfs 仅用 2.0G；真正吃紧的是本机 7.5G |
| 8 | MES 监督缺口（**任务前提已过时，实测证伪**） | 中 | CH 现在是通的，但"通的全是运气"：两机都靠上一次有人手工起 |
| 9 | 镜像增长 | 中高 | 本机 205GB 镜像 149.1GB 可回收而根分区只余 100G |
| 10 | 看护体系横向缺口 | **高（结构性）** | D-26 定性"全厂缺乏统一的资源管理与回收机制"在实测层面完全成立 |

### 2.2 红队核验（node 32123，**confirmed**，7 条 issue 全接受）

- **勘误 1**：keepalive 看护对象实为 **6 个不是 4 个**（`tools/factory-keepalive.py` docstring `:7-27`）；盘点只 grep 了其中四个名。结论"不含跨机 ch-mes"不受影响——全文件 grep `ch-mes|clickhouse` 仅 `:76` 的 CH 写端点常量。**（本轮记账员实测现役为 7 对象，见 §0.1；对象数随补丁②上线将变 8——账要跟着改）**
- **勘误 2**：**"GC 手册（状态观测/）"是不存在的引用**（`ls 状态观测/` 只有 alarms.log / anolis待sudo清单.md / latest.json / watch-state.json / watchdog.pid / 业务目的章程.md / 巡检日志.md / 护栏rollout手册.md；`find -iname '*GC*'` 无命中）——任务描述里"GC 手册 状态观测/护栏rollout手册.md"是两个名字的误并。**该勘误后来直接塑造了补丁③的第一交付物（把 10-22 手工流程固化成 `tools/img-gc.py` + 首次出现的 GC 手册）。**
- **勘误 3/4/5/6**：手册章节号小误（swap 交互说明在 §1 行 41-43）、"判分容器 4g/256 未实测"对 fix1/fix2 代际不适用（判分在 agent 容器内原地执行随 6g 封顶，4g/256 是 fix3 独有、其不存在正是期望态）、调度器 pid→产线映射未区分（`/proc/2857945/environ` = `AF_SCHED_GRAPH=/tmp/factory2-graph.json` + `BIN=af-bench-fix2` = 实验线）、一组时钟差数值漂移（MemAvailable 124193540 vs 124650492 kB、load 2.92 vs 0.44 等，**非矛盾**）。
- **勘误 7（如实声明）**：本次未重跑——本机 `du -x /` 与 `~/明细`、anolis 二级 du、205GB 镜像体积的 du 独立核对（`/var/lib/docker` root-only，Permission denied，与盘点所述一致）。
- **红队实测坐实的关键事实（构成后续一切的地基）**：内存门在役（`factory-sched.py:66/353-379/402-415`，两调度器进程均晚于文件 mtime）；容器限额真实在役（`sha256sum af/target/debug/af-bench` = `5494a49e…` = 手册换装目标值 + `strings` 计数 + `docker inspect` 得 mem=6442450944 pids=512 memswap=12884901888）；两机 CH /ping 均 Ok.；D-27 监督缺口属实（本机 keepalive 不含 ch-mes 目标、anolis crontab 空、`~/ch-mes/start.sh` 注释自认"重启机器后需手工再跑"）；**任务前提的"护栏二进制未换生产位"与"ClickHouse 500"两条经实测证伪，盘点的修正是对的**。

### 2.3 补丁设计的红队审查（node 32159，**rejected**，14 条）与 R2 的逐条回应

阻断级 5 条（全部被接受并改写）：
1. **补丁③执行通道未定义** → 可能误删本机 120 张在役 feed 镜像且 D-30 未还无法重拉 → R2 改为一律经 `ssh anolis docker …` + `--host` 强断言。
2. **补丁③保留集③取数源错误**（`/tmp/factory-graph.json` 节点 `state` 字段实测 115 个全 None）→ R2 改取 `/tmp/factory-status.json` + `/tmp/factory2-status.json` 的 `state=="running"`，图只取 `params`。
3. **补丁③保留集②镜像名解析错**（实例→镜像名不是字符串替换，实测 `swebench/sweb.eval.x86_64.pydata_1776_xarray-2905:latest`）→ R2 改读 task json 的 `image` 字段，禁 tid 直接替换。
4. **补丁②影响面错判**（anolis ch-mes **无任何在仓消费者**，5221 写入方全在本机；"失联=入库积压"因果链不成立）→ R2 如实降级 anolis guard 为"D-27 基建保底 + D-26 前过渡件"，论证重心移到本机 MES 探活。
5. **补丁②验证②测不到 guard 且与 CH 内置 watcher 抢起**（watcher pid 49996 是 server 50003 的父进程）→ 验证协议改杀双进程，guard 增"ping 失败但 clickhouse 进程在→记 unhealthy 不盲重启"分支。

重要级 4 条：①静默停摆无告警（拦新不杀旧退化成拦新且无声）→ 加 1800s 升级三通道 + 86400s 停取等人工；②删集无正向白名单 → 加 `^swebench/sweb\.eval\.x86_64\.[a-z0-9_-]+_1776_.+:latest$`；③TOCTOU → 三重重算；④gc_watch 必须严格非阻塞（否则 7 个看护对象集体失明）→ spawn 即返回。
次要级 2 条：①exit 3 同码不同义（once 闸闭改 exit 4）、背景数漂移（36 prepare_failed 非 46）、容器计数门首期删除；②引用漂移（TARGETS 在 `:754-755` 非 `:727-728`）。
**未被击穿的维度（红队实测确认）**：误杀在飞（预检在 `run_one` 开头、`prepare`（含 `rm -rf workdir`）之前，在飞 solve 不经预检）、gov（三补丁只读或只碰本厂资产）、OOM 自己、root（全程用户态）、MES 故障雪崩（CH 写失败均实测非致命）。

---

## 3. 补丁台账（路径 / 语义 / 测试证据 / 记账员判定）

### 3.1 补丁① mcode-dispatch 资源闸 ✅**在役**

- **路径**：`/home/pan-ding/workspace/agent黑灯工厂/补丁/补丁1-mcode-dispatch-资源闸-R2.patch`（456 行，md5 `d9410a10c5a68f2b40f35b06034ceb65`）；另含新增文件 `tools/mcode-once-wrapper.sh`（patch 内 `@@ -0,0 +1,36 @@`）。已原子落位于 `tools/mcode-dispatch.py`（现役 mtime 2026-10-22 02:37:25）。
- **语义（拦新不杀旧 + fail-closed）**：worker 取任务前 probe 三条件，60s 缓存、阈值/时限全部 `MCODE_GATE_*` / `MCODE_DEFER_*` env 可覆盖 —— ① 本机 `/proc/meminfo` MemAvailable < 4GiB（本地解析，绝不把 awk 经 ssh 传远端）；② 本机 docker data root 分区可用 < 20GiB 或判不准；③ anolis `/data/bench/mcode-swev` 可用 < 4G 或 ssh 不可达/判不准（把原 `disk_ok` 的"判不准不拦"升级为 fail-closed）。唯一放行例外=本机内存读数异常（记日志放行，单题 25m/30m 双超时兜底）。闸闭→任务永不出队、在飞 solve 自然收尾；推迟不写 phase、不调 `_note_failure`（不烧 attempts）；每 600s 刷 heartbeat 让 keepalive 看到"活的、在推迟的"。升级：连续推迟 >1800s 触发一次 klog ALARM + MES `kind=mcode_defer_stalled`（直 INSERT，写失败不致命）+ `deferred.log`；>86400s 停取新任务等人工（心跳照刷）；`defer-state.json` 持久化续时。exit 语义：run 双实例守卫 exit 3 不变；新增 `gate-check` 子命令闸闭 exit 4；wrapper 闸闭 exit 4；once 本体不拦人工补跑（横幅 + 落 deferred.log）。
- **测试证据（node 32276，passed=true）**：真进程 `gate-check` 矩阵（mem/disk/remote 三条各自 exit 4；PATH 注入 exit-7 假 ssh 模拟 tailnet 闪断→fail-closed exit 4）→ 默认阈值 `GATE OPEN` exit 0 → S5 动态测试 11/11（闸开取出任务、在飞中途探针转不可达仍自然跑完、闭闸期任务不出队 `calls=1, unfinished=1`、心跳 mtime 前进、`attempts={}` 零烧、state.json 零变化、解除后 `escalated/halted/defer_since` 复位）→ S4A/S4B/S4C/S4D/S4E/S4F 升级链（真实 MES 直 INSERT，计数 0→1，回读 `event_id: mcode-dispatch-mcode_defer_stalled-1792611829-3864359`；重启接续 4/4；闸开复位 5/5；CH 指死端口时写失败不致命 4/4；halt 4/4 + 新进程接续 3/3）→ 终态生产无损（pid 3711801 全程存活推进、`/tmp/mcode-dispatch` 恢复原 3 文件）。
- **记账员判定**：**在役**。本轮独立佐证 = 启动行 `[gate] 资源闸生效 …`（04:25:54/04:28:24/04:45:55/04:48:26/04:55:56）；作者套件本节点复跑 29/29 rc=0。
- **未实测边界（作者自陈）**：probe_mem 读数异常放行分支在本机不可真实制造（仅 mock 覆盖）；1800s/86400s 按允许压为 3s/2s 验证，真实时长未等；keepalive"死后拉起"链路未测（不可杀真进程），只验了判据输入。

### 3.2 补丁② anolis ch-mes 守卫 + 本机 MES 探活 🟡**半在役**（anolis 侧在役 / keepalive 侧未生效）

- **路径**：`/home/pan-ding/workspace/agent黑灯工厂/补丁/补丁2-anolis-ch-mes-guard-本机MES探活-R2.patch`（285 行，md5 `7f9f30bbf24891c2522e6f7231a315b7`）；补丁内含新增文件 `b/补丁/anolis-ch-mes-guard.sh`（= 工作区 `补丁/anolis-ch-mes-guard.sh`，5429 字节，755，**已部署到 anolis `~/ch-mes/guard.sh`**）。
- **语义**：两层。①**本机告警面**（`tools/factory-keepalive.py` 新增第 8 判活对象 `ch-mes-local`）：判据 `GET http://127.0.0.1:5221/ping` 返回 `Ok.`；失联=**只报警不拉起**（本机无 `~/ch-mes/start.sh`，实测不存在）→ klog + `状态观测/alarms.log` JSON 行（`level=red, code=ch-mes-local`）+ MES `kind=ch_mes_down`（写失败不致命）；30min 去重用 keepalive 侧自有键 `last_chmes_alarm`（watch 的 `alarm_logged` 在 watch 进程内不可共享）——**告警主通道是文件，CH 挂时照样可报**。②**anolis 保底面**（`~/ch-mes/guard.sh` + pan-ding 用户级 crontab `*/5`）：ping Ok→记 ok；ping 失败→纯 bash 扫 `/proc`（cmdline 同含 `clickhouse` 与 `server --config-file`，`case` 匹配使检索词不进任何子进程 argv）→ 进程在（watcher 49996/server 50003）记 unhealthy **不执行 start.sh**（防抢跑双起）；进程不在→`still_down<3` 执行 start.sh 后 8s 复探记 restored/restart_failed；≥3 进入 30min 退避（`guard-state.json` backoff-until）；guard.log 超 5MB 截尾保留 1MB。**定位如实降级**：anolis guard = D-27 基建保底 + D-26 前过渡件（anolis 失联 ≠ 本机入库积压）；边界=只管拉起进程不管数据修复。
- **测试证据（node 32285，passed=true）**：本机层 12/12（真 urllib /ping→`(True,'ping Ok.')`、注册面四处齐、`one_round(dry=True)` 真环 8 对象齐跑、dry 无副作用、ch-mes-local 豁免通用失联处置行）；真拉起报警 5 项（klog ALARM 行、沙箱 alarms.log `{"level":"red","code":"ch-mes-local",…}`、MES 计数 0→1、CH 回读 `event_id: factory-keepalive-ch-mes-local-ch_mes_down-1792612545-3878292`、30min 去重窗内不重复）；**悖论面 6/6**（CH 指死端口 127.0.0.1:1：文件主通道照常、MES 写失败不致命、计数不变）；anolis 面：G0 部署核验（md5 `bad0ae70…` 与补丁文件逐字一致、755、cron 在跑、findmnt `/dev/vda3 ext4` 非 tmpfs）、start.sh 幂等真跑、G1 ok 分支、G2 unhealthy 分支（假 ping + 进程在场 → 不拉起，server 进程集合不变）、**G2b 防自匹配**（bash -x trace 中携带检索词的外部命令行 = 0 条）、G3 状态机 9 分支全过（pid 命名空间 + 沙箱 CH_DIR + 桩 start.sh：轮转 5500011B→1048827B、restart/ok/still_down 1→2→3/backoff-enter/backoff-skip/复位）；生产无损（keepalive 3614522 全程未重启、alarms.log 零测试行、sandbox 与桩已清）。
- **记账员判定**：**anolis 侧 ✅在役**（本轮实测 crontab `*/5` 在载、guard.log 04:45/04:50/04:55 三连 `[ok]`）；**本机 ch-mes-local 🟡代码在盘未生效**（现役 keepalive 为旧代码、看护 7 对象、alarms.log 中 `ch-mes-local` 计数 = 0）。作者套件本节点复跑 11/11 rc=0。
- **未实测边界（作者自陈）**：本机真实 CH 停机下的端到端告警未做（不可停生产 MES）；klog/alarms.log 写入验在沙箱路径上；新代码 30s 常驻真实轮未激活；去重窗"过期后再报"仅作者 mock 覆盖。

### 3.3 补丁③ anolis 镜像回收 gc_watch ⚠️**执行器可用 / 触发器修复后未端到端复验**

- **路径**：`/home/pan-ding/workspace/agent黑灯工厂/补丁/补丁3-anolis-imggc-gcwatch-R2.patch`（658 行，md5 `819a9ce99d8e78de8081699bb35c2d6c`；文件头已含 **fix1** 说明）；新增文件 `tools/img-gc.py`（mtime 2026-10-22 03:25:33）。
- **语义**：①`tools/img-gc.py`：plan/apply 均须 `--host anolis`（其他值 SystemExit，本机 docker 绝不触碰——本机 120/120 sweb.eval 是本地判分依赖且 D-30 未还），docker 读写全走 `["ssh","-o","ConnectTimeout=10","anolis","docker",…]`；保留集三源并集（A 在飞容器 / B mcode 在途=本机 state.json 相位≠judged → swev-s1 task json `image` 字段，缺失时 fallback `_1776_` 拼法+告警，**禁 tid 直接替换当镜像名** / C 两 status 文件 `state=="running"`，relay 取 `params.image`、bench 取 `params.tasks`；**图只取 params 不读运行态**）；删集=(全量−保留)∩白名单 `^swebench/sweb\.eval\.x86_64\.[a-z0-9_-]+_1776_.+:latest$`（**含连字符勘误版**：派单原版 `[a-z0-9_]+` 对 03:xx 现池仅 22/56 命中，加 `-` 后 56/56，foreign=0）；apply 闸链（任一命中删零张）：HALT 哨兵在场**或判不准**→拒 / 保留集源失败或盘点 2 次重试仍败→fail-closed 只出 plan / 现场复核 `/data` ≥88%→停手只回报（85% 触发线由 keepalive 本地判 latest.json）/ TOCTOU 三重（apply 重取在飞重算、逐候选 `docker ps -q --filter ancestor=` 过滤且判不准按 busy 拒删、rmi 循环内逐张再查后即删）；rmi 失败不重试不 `-f`，记 RMI-FAIL。子进程：flock 单飞（NB，被占静默退出）+1200s SIGALRM 自杀留证据；`docker builder prune -f` 是唯一 Host 级命令；证据 JSONL 双写 `/tmp` + `状态观测/`（耐久件为审计基准）。②`tools/factory-keepalive.py` `one_round` 新增 gc_watch 步骤（**非判活对象**）：纯本地判断（latest.json anolis `/data` use_pct≥85 且 mtime≤300s，否则视为 watch 断供不触发；距上次成功 GC>6h 读耐久证据；spawn 防抖 1200s）→ spawn 即返回、严格非阻塞；A9 告警 30min 去重记回耐久件。
- **测试证据（node 32298，**passed=false**，J3 缺陷）**：缺陷复现——`gc_watch` 的 spawn argv 为旧序 `["python3","tools/img-gc.py","--host","anolis","apply"]`，而 `--host` 定义在 plan/apply 子解析器上（`tools/img-gc.py:445-451`），真 spawn 下 **子进程 100% 死于 argparse rc2**（`img-gc.py: error: argument cmd: invalid choice: 'anolis' (choose from plan, apply)`），**死前零证据、A9 无从告警 ⇒ 自动 GC 触发路径静默失效**；作者单测 T9a 用 spawn 记录器只记 argv 不执行，故漏网。**其余全部实测通过**：作者套件 35/35；A host 红线（`--host pandev`/`localhost`/缺省全拒，本机 sweb.eval 镜像计数全程 =120 零触碰）；B 真实 plan（use_pct=73，保留 A=5/B=2/C=62，删集 32 全白名单内，foreign=0，白名单勘误 66/66 vs 旧版 28/66，B 源 task json 镜像在保留集，ancestor 过滤真测 busy=True/False）；C 硬超时（压 2s → SIGALRM rc=9，证据 `hard-timeout-selfkill`）；D flock 单飞（持锁 12s 期间 apply 静默退出 rc=0，镜像 67→67 零删）；E HALT fail-closed（在场拒 + 判不准拒）；F 停手线（use_pct=90 → 停手只回报，未进删除段）；G 源损坏 fail-closed；**I 真实 apply 全路径**（植连字符 dummy 标签走真实 rmi 路径，真 apply rc=0 耗时 23s，删 8 / rmi-fail 0，/data 77%→71%，镜像 69→61 精确差 8，dummy 残留 0）；J gc_watch（J1 真调用即返回 wall=1ms；J5' A9 失败→red 告警实测；J6' 去重时间戳写回；J7 30min 去重；J8 1200s 防抖；J9 71%<85 不 spawn 不报警）。**顺带实证**：mcode pid 3711801 于 04:18 自然跑完队列退出，keepalive 拉起新实例 pid 3898897，启动横幅即补丁①"[gate] 资源闸生效"——补丁①的"新代码自重启生效 + 断点续跑"在产线得到验证。
- **fix1（node 32307）**：argv 改为 `["python3","tools/img-gc.py","apply","--host","anolis"]`，4 处同步（spawn `:906`、模块 docstring `:42`、gc_watch docstring `:855`、dry-run klog `:896`），04:25:35 落盘。**终审复验**（node 32315 issue 1）：新序 argparse rc=0 / 旧序 rc=2 / fix 后作者套件 T9a 精确 argv 断言 PASS（34/35，唯一 FAIL T5c 为 mcode 在途为空的时序假象）。
- **记账员判定（⚠️ 关键）**：**触发路径仍视同未验证**。理由：(a) 终审实测 `find -newermt "2026-10-22 04:20"` 显示 fix1（04:25:35）之后**无 J3 式真实 spawn 复跑证据**（`/tmp/patch3-r2-tests/out/` 最新为 04:22 的 `j5red_a9.txt`）；(b) 本节点**未复跑** J3 真实端到端 spawn（drill 旗标未落位，`/data` 71% < 85% 不触发）；(c) 本节点复跑作者套件 35/35 rc=0，但 T9a 属"只记 argv 不执行"层级，**不能替代真 spawn**。→ 已列为方案 §5 **P0-4 第 4 条强制验收**（drill 自毁旗标 `状态观测/img-gc-drill.flag` + 零变异 plan spawn + 验三件：新序 argv / 证据行 `kind=plan` 落盘 / `/tmp/img-gc.log` 无 argparse rc2）。执行器侧本轮另有补证：方案撰写员实跑 `python3 tools/img-gc.py plan --host anolis` rc=0（04:50:17，证据件 16→17 行）。

### 3.4 三态总表（记账员口径）

| 补丁 | 组件 | 状态 | 记账员本轮依据 |
|---|---|---|---|
| ① | mcode-dispatch 资源闸 | ✅**在役** | `[gate] 资源闸生效` 启动行（含 04:55:56）；套件 29/29 rc=0 |
| ② | anolis `~/ch-mes/guard.sh` + crontab | ✅**在役** | crontab `*/5` 在载；guard.log 04:45/04:50/04:55 三连 `[ok]` |
| ② | keepalive `ch-mes-local` | 🟡**代码在盘未生效** | 现役 7 对象；alarms.log `ch-mes-local` 计数 0 |
| ③ | `tools/img-gc.py` 执行器 | ✅**在役可用** | plan 实跑 rc=0（04:50:17 证据行）；真实 apply 8 删（node 32298 I 项） |
| ③ | gc_watch 自动触发 | ⚠️**fix1 后无端到端复跑** | 终审 issue 1 + 本节点未复跑 → P0-4 强制补验 |

---

## 4. 方案路径与终审意见

- **路径**：`/home/pan-ding/workspace/agent黑灯工厂/设计/资源治理统一方案.md`（现役 **174 行**，mtime 2026-10-22 04:54:28）。v1 为 180 行（node 32311），R2 重写为现役版本（node 32324）。
- **终审意见（node 32315，红队·方案终审，step-5，未参与本轮环节）＝ `rejected`，8 条**：
  1. **【主阻断·补丁→方案迁移路径】** v1 line 5 以"三补丁已验证"为起点，而补丁③实测记录明确"未过"；且 v1 未披露 J3/fix1 事件、fix 后无 J3 式真实 spawn 复跑证据、P0 验收三条完全不覆盖 gc_watch→spawn→apply 链路——**P0 一旦执行即把未经端到端验证的触发路径投产**。要求：正文补记 J3/fix1 与验证状态；P0 验收增加 gc_watch 端到端验证条。
  2. **【六面闭环】** 矩阵与代码/日志抽查一致，anolis 磁盘/内存/MES 三面近闭环；未闭环面=本机磁盘、本机 local 臂内存、容器历史计量与越限告警、结果目录、本机镜像回收。补法已映射 P1/P2 且诚实标注，但**方案未给时限/责任人 → 纸面闭环风险**；结果目录面建议补归档完整性校验告警。
  3. **【隐藏单点·keepalive 自举】** `factory-keepalive.py:72-74` 自认自身死亡无法自愈、靠巡检 cron 兜底，而 D-17 明确 cron 生效性未证实；方案只写"由巡检 cron 或手工拉起"，未规定"先起新、验 8 对象、后杀旧"的**原子顺序**（且 pidfile 单实例守卫 exit 3 会拒新进程）。
  4. **【隐藏单点·mcode 抖环】** 方案落盘后仍在持续（04:39:22 报 mcode-dispatch DOWN、04:36/04:38 两次"队列跑完退出"），§4-#2 只有二选一选项无时限，告警面被长期占用。
  5. **【隐藏单点·journald root 路径假设】** #3 假设"既有 sudo 留证纪律"本机可行，但 `状态/机器清单.md:42` 记本机 root 项"沙箱无 sudo、待宿主窗口" → 应降格为"待宿主窗口确认"。
  6. **【越权碰 gov】无越权**（唯一 gov 表述=§4 #9"维持现役 gov 网关 方案 B 零操作"，与 `状态观测/anolis待sudo清单.md:91/125` 一致；未发现对 governance-machine/100.64.0.6 的任何操作或申请）。
  7. **【MES 500 根因未明时的止损】止损链完整且逐段复验**：(a) 两机 /ping=Ok.；(b) 检测=ch-mes-local（只报警不拉起、30min 去重、🟡待 P0）+ anolis guard.sh v2（✅在役）；(c) 解耦=告警主通道文件、MES 写失败不致命、丢行接受 → **MES 挂不停产**；(d) 恢复=本机人工 Runbook（实测无 start.sh）、anolis guard 自动拉起。**缺口**：根因未明且 guard 只管拉起不管数据修复 → 建议补"ch_mes_down 触发时先固化 CH 日志/表状态再走 Runbook"+"500 复发 N 次升级 P0 排查"阈值。
  8. **【引用质量·通过项】** 抽查约 30 处 path:line 引用全部与现役代码吻合（`factory-keepalive.py:31-35/72-74/99/103/106/758/802/853-907/942-943`；`factory-sched.py:59-68/113-138/328-415`；`mcode-dispatch.py:119-125/322-442`；`factory-watch.py:25/407/615-617`；`img-gc.py:11-15/39-41/69/80/87`），img-gc 证据件 16 行、末次 apply 04:16:59（77%→71%）与方案相符，keepalive pid 3614522 早于代码 mtime 04:25:35 = 旧代码在役，P0 必要性属实。
- **R2 修订落点（node 32324 + 现役文件 §7 映射表）**：新增 §0.1 三态验证台账 + J3/fix1 事件全文披露；gc_watch 改标 ⚠️"P0 验收通过前视同未验证"；§3.3-a 加 drill 旗标设计（~6 行、零变异 plan spawn）；§5 P0 改**原子替换顺序**（P0-0 人工接力硬前置 → P0-1 `--dry-run` 预检 → P0-2 drill 落位 → P0-3 TERM→等 pidfile 消失→即起新 → P0-4 四条验收，失败回滚一行）；P0-4 第 4 条 = gc_watch 端到端；§4/§5 全部条目加责任人 + 时限 + 到期默认路径；P1-4 归档器补每日完整性巡检 → `alarms.log code=archive-check`；§4-#3 journald 降格"待宿主窗口"；§3.5 补诊断三件（`df -P / /var`、`curl /ping` + `curl "/?query=SELECT 1"`、`/proc` 扫 clickhouse 进程与启动时刻）+ **24h 内失联 ≥2 次 → 登记 P0 级根因排查债**。
- **⚠️ 口径提醒（下一轮必须记得）**：R2 **未经任何红队复审**——node 32324 之后直接进入本记账节点 32328，`dwf_node` 中不存在第二个方案终审节点。因此本 run 的最终结论字段会写"统一建设方案已成稿（**rejected**）"，而磁盘上的文件是**按驳回意见改完但没人再审**的 R2。**"rejected"指 v1，R2 状态=未复审**，两者不可混读。

---

## 5. MES 500 根因排查：**不归本组**（本组交付止血与监督，根因另派）

**结论**：MES 500 根因排查**不属本组本循环**，本组交付的是**止损面**（已在役的 anolis guard + 待生效的本机探活告警 + 事件记账 + 复发升级阈值）；根因取证需要本组**触达不到的权限与面**，应登记 P0 级技术债并请运营者派专门组 + 批宿主窗口。

**依据（逐条可查）**：

| 依据 | 出处 |
|---|---|
| 本组授权范围＝"补丁保障 + 统一建设方案"，方案阶段任务书写明"MES 500 根因未明（方案只给止损与监督，**根因排查待派**）" | `研究组4-资源管理组.dwf.ts`（末段 `notCovered`） |
| 两次 500 发生在**本机** CH（调度器写 127.0.0.1:5221）**非 anolis**；本机 CH 现健康，**根因未定位如实挂账** | `状态观测/巡检日志.md:114`；`巡检日志.md:110`"factory2.log 15:14/16:27 两次 MES 500 未复现（本地 CH 侧，根因未留痕，已恢复）" |
| 根因取证的关键三件（`journalctl -u clickhouse-server` 尾 200 行、数据目录 du、CH 启动时刻）在本机需要 **root**；而本机 root 项状态＝"**沙箱无 sudo、待宿主窗口**"（含 `journal 3.9G 无上限` 未处置项） | `状态/机器清单.md:42`（原文"④根属主遗留项因沙箱无 sudo 全部未动、待宿主窗口：… journal 3.9G 无上限"）；方案 §4-#3 已据此降格 |
| 本机 CH **无启动脚本**（`~/ch-mes/start.sh` 实测不存在）→ 拉起与修复都只能走人工 Runbook | 方案 §3.5 / 终审 issue 7(d) |
| 本组已把"根因债"的触发条件写成可执行阈值：**24h 内失联 ≥2 次 → 直接登记 P0 级根因排查债**（不再走 Runbook 循环重启——guard 只管拉起不管数据修复，若 500 源于数据层损坏则重启无效） | 方案 §3.5 第 3 条 |
| 方案终审对止损链的判定是"完整且逐段复验"，缺口只有"触发时先固化 CH 日志/表状态"与"复发升级阈值"两项 | node 32315 issue 7 |

**本组本轮在 MES 面上已交付的实物**（供下一轮直接引用，不必重做）：anolis `~/ch-mes/guard.sh`（755 + crontab `*/5` + 5 分钟级探活 + 不盲重启 + 30min 退避）**已实证在役**；本机 `ch-mes-local` 探活（只报警不拉起、30min 去重、文件主通道不依赖 CH）**代码在盘、待 keepalive 换血生效**；`kind=ch_mes_down` 事件 + `kind=mcode_defer_stalled` 事件 + `kind=img_gc` 计划中的 MES 接口（方案 P1-3）。
**下一循环的本组动作**：不查 500 根因；只做两件事——①把 §3.5 的诊断三件落进 `ch_mes_down` 触发路径（无 root 三件随事件附件落盘、root 件标"待宿主窗口"）；②盯 **24h 内失联 ≥2 次**阈值，一旦达成即**登记 P0 根因排查债并请运营者派组/批窗口**，同时把债从"挂账"升级为"有主"。

---

## 6. 下一循环动作

### 6.1 P0（今日，**等运营者批窗**——keepalive 重启是唯一能同时激活补丁②③ 的动作）

| # | 动作 | 依据 / 判据 | 记账员补充（as-of 04:57） |
|---|---|---|---|
| **P0-0** | **人工接力硬前置**：执行人全程在终端旁；任何步骤失败立即手工拉起 `cd /home/pan-ding/workspace/agent黑灯工厂 && setsid nohup python3 tools/factory-keepalive.py >> /tmp/factory-keepalive.log 2>&1 < /dev/null &` | 方案 §5 P0-0（本机 crontab 零条目、无 systemd 工厂 timer，cron 兜底实测不存在） | 备份/回滚件已在 `工具状态备份/factory-keepalive.py.pre-patch3-R2` |
| **P0-1** | 干跑预检 `python3 tools/factory-keepalive.py --dry-run`（dry_run 分支在 self_guard 之前 return，旧 pidfile 不受影响） | 方案 §5 P0-1；`factory-keepalive.py:1025-1028` | 需人工核：输出含 8 对象与 ch-mes-local / gc-watch 行 |
| **P0-2** | drill 旗标小改落位（`状态观测/img-gc-drill.flag`，~6 行，原子写入+备份+回滚一行），随本次重启同窗生效 | 方案 §3.3-a / §5 P0-2 | **本轮未落位**——这是补丁③ 端到端复验的前置件 |
| **P0-3** | 原子换血：先 `kill -TERM $(cat /tmp/factory-keepalive.pid)` → 轮询等 pidfile 消失（≤1s，`:1058-1067`）→ **立即**起新（勿在旧进程活时起新，self_guard exit 3 会拒新，`:997-1005`） | 方案 §5 P0-3 | 盲窗 <2s |
| **P0-4** | **四条验收**：① klog 出现"看护 8 对象：… ch-mes-local"（现役行是 7 对象，本轮实测）；② `--dry-run` 复核 ch-mes-local 判活为 `ping Ok.`；③ mcode-dispatch 无新形态异常（空队列退出属裁决 #2，不算本条失败）；④ **gc_watch 端到端**：`touch 状态观测/img-gc-drill.flag` → 等一轮（≤30s + 1200s 防抖窗内）→ 验三件（klog drill spawn 行且 argv 为新序 / `/tmp/img-gc-evidence.jsonl` 与 `状态观测/img-gc-evidence.jsonl` 新增 `kind=plan` 行 / `/tmp/img-gc.log` 有子进程输出且**无 argparse rc2**）。**任一不满足 = P0 验收失败** → 回滚 keepalive 备份件并上报，触发路径继续视同未验证 | 方案 §5 P0-4 | 验收①的判据值要改：现役是"看护 7 对象"，换血后应见 8 对象 |
| **P0-2'** | **mcode 派发器当前已死，需人工处置（记账员本轮新增，见 §0.1）**：`state.json` 240/240 全 judged → 队列空 → 每次拉起 5s 内"队列跑完退出" → keepalive 04:56:24 触发防抖熔断"600s 内已重启 2 次，超限停止拉起只报警（进程仍死，需人工介入）" | 方案 §4-#2（时限 2026-10-23 12:00 前，到期默认路径=按 image-feed 先例给 mcode 判活加"队列空退出=正常完成不重启"分支） | **优先级建议提到 P0 与换血并列**：熔断后 mcode 线**无人自动恢复**，任何补跑/重判任务都会空跑。两条路——①补任务队列（业务解，优选）；②改判活分支（需先确认 state 队列空即判 done 的判据可靠）。**注意**：改判活分支动的是 `tools/mcode-dispatch.py`（补丁① 同文件），与 D-34 登记"该文件现由④资源组在管"不冲突，但需与补丁①语义并读（闸闭时 exit 4 ≠ 队列空） |

### 6.2 P1（本周；责任人=资源组，时限取自方案 §5 表）

| # | 项 | 时限 | 记账员注 |
|---|---|---|---|
| 1 | watch 增本机 `/`、`/tmp` 水位告警（新码 A4L）+ anolis 内存告警码 | 10-24 前 | 本机 `/` 81% 已超 85% 语义线**无人报**（A4 是 anolis-only） |
| 2 | `factory-sched` local 臂准入双条件（/ 可用 ≥15G、MemAvailable ≥4G） | 10-24 前 | local 臂现无任何资源门 |
| 3 | img-gc apply 尾部 MES `image_gc` 事件 | 10-25 前 | 写失败不致命 |
| 4 | `tools/results-archiver.py`（tar+sha256+**每日完整性巡检** → `alarms.log code=archive-check`） | 10-25 前 | 结果目录现全在 tmpfs（D-24），重启即失 |
| 5 | 告警最后一公里：**先提案后落地**，提案=宿主侧厂长 cron 显式消费 alarms.log 或建用户 timer；落地前人工巡检兜底 | 10-26 前提案 | 方案已把 P1-5 的 D-17 核验提前为 P0-0 前置 |
| 6 | journald 500M | **待宿主窗口** | 本机 root 项"沙箱无 sudo"（`状态/机器清单.md:42`）；本组不可执行 |
| 7 | **（记账员新增）方案 R2 交红队复审**（step-5，v1→v2 逐条对照 §7 映射表核销） | 与 P0 同窗或紧随 | R2 目前**无人复审**（见 §4 口径提醒） |
| 8 | **（记账员新增）补丁存档重放性修复**：补丁②③ 同改 `tools/factory-keepalive.py` 且头部 hunk 重叠（§0.1 实测补丁② 反向 dry-run 4/10 hunk FAIL）→ 补一份"②→③ 顺序 + 头部手工合并说明"，或把两补丁合成单一合并补丁 | 下次发布前 | 否则存档不可独立重放 |

### 6.3 P2（下代构建周期，只 commit 不部署）

`af-bench` arm_resource 计量 + D-22 命名；D-15 在跑臂软暂停（同批）；out 根迁 `~/bench-data`（等 §4-#8）；本机镜像一次性 GC（等 §4-#4，需先修 D-30）。

### 6.4 记账员留给下一轮的自测缺口（本轮**未跑**，不得当成已验）

1. **补丁③ gc_watch 真实端到端 spawn**（fix1 后）——P0-4 第 4 条。
2. **补丁②③ 新代码在 keepalive 换血后的真实 30s 常驻轮**（判活对象数应从 7 变 8；alarms.log 应首次出现 `ch-mes-local` / `gc-watch` 码）。
3. **补丁② 去重窗"过期后再报"**（作者 mock 覆盖，真实未再造第 2 行 MES）。
4. **补丁③ 真实 `use_pct ≥ 88%` 现场停手**（`/data` 实际 71–77%，不可人为填满磁盘；此前只以 monkeypatch=90 走真闸链）。
5. **补丁① probe_mem 读数异常放行分支**（本机 `/proc/meminfo` 恒可读，无法真实制造；仅 mock 覆盖）。
6. **补丁① 1800s / 86400s 真实时长**（此前按允许压为 3s/2s）。
7. **补丁① "keepalive 死后拉起 mcode-dispatch"链路**（不可杀真进程，只验了心跳判据）。
8. **方案 R2 的红队复审**（见 6.2-7）。
9. **作者套件 T5c 的时序敏感假阴性**（终审 34/35 vs 本轮 35/35）——建议把 T5c 的前置条件（mcode 在途非空）写进套件断言，避免下一轮再出现"通过/未过"读数漂移。

---

## 7. 诚实边界（记账员本轮跑了什么 / 没跑什么）

**本轮（记账员节点 32328）亲跑并记入 §0.1 的**：三个作者套件（29/29、11/11、35/35，均 rc=0）；三个补丁的 `patch -p1 -R --dry-run` 重放性检查；`ps`/`stat` 现役进程与文件 mtime；`/tmp/mcode-dispatch.log` 与 `/tmp/factory-keepalive.log` 尾行；`状态观测/alarms.log` 新码计数与最近 200 行码分布；`状态观测/img-gc-evidence.jsonl` 行数与末两行；本机 `crontab -l`（零条目）；本机 `curl 127.0.0.1:5221/ping`（Ok.）；`ssh anolis` 读 `/data` 水位、`~/ch-mes/guard.sh` 权限、crontab、guard.log 尾行、`~/img-gc-HALT` 不存在；`state.json` 相位统计（240/240 judged）；`ps` 确认 mcode-dispatch python 进程不存在。
**本轮未跑（明确记为未验）**：任何写操作、任何 docker 删镜像、任何 `img-gc.py apply`、任何 root/sudo 动作、任何 J3 式真实 spawn、任何 `patch -p1` 真实应用（只做 dry-run）、TB 容器 inspect、anolis 内存门压力验证、`/var/lib/docker` du（root-only）、本机 CH 真实停机实验。
**本轮也未做**：未修改任何工作区文件（除新建本状态文件），未动在飞臂/进程，未触碰 gov。

---

## 8. 待决与升级项（需要运营者/厂长裁决，记账员不自行拍板）

| # | 事项 | 现状 | 记账员建议 |
|---|---|---|---|
| 1 | **keepalive 重启窗**（激活补丁②③ 的唯一路径） | 未定 | 今日内定；臂换题间隙执行；执行人终端旁接力（方案 §5 P0-0） |
| 2 | **mcode 派发器已死 + 熔断**（04:56:24） | 需人工 | 与 #1 并列 P0：先补队列，否则任何补跑任务空跑 |
| 3 | **R2 方案复审** | 未排 | 派 step-5 独立终审 v2，核销 §7 映射表 8 条 |
| 4 | **MES 500 根因归属** | 本组结论=不归本组 | 登记 P0 级根因排查债，请运营者派专门组并批本机宿主窗口（root 取证）；本组只保留监督与阈值触发（24h≥2 次） |
| 5 | 本机 journald 500M | 待宿主窗口 | 不执行（仅登记） |
| 6 | 本机镜像 GC 政策 | 等 D-30 | 不执行 |
| 7 | 跨机监督 root vs 用户态 | 已定=用户态 | 维持（guard.sh 已实证） |

**账本纪律提醒（承调优组先例）**：本文件所有数字均带 as-of；引用任何生产读数必须重跑命令取新值，禁止沿用本文件旧值作决策依据（`state.json` 相位、alarms.log 计数、镜像池、磁盘水位在 10-22 仍在变动）。

---

## 9. 追加记录：J3 端到端复验（修理组子代理，2026-10-22 05:05–05:11 CST）

- **结论**：`tools/factory-keepalive.py` 现役工作副本**已含 fix1**（mtime 04:25:35，与补丁③ R2-fix1 落盘时刻一致；spawn argv `:906` 即新序 `["python3","tools/img-gc.py","apply","--host","anolis"]`，4 处同步齐）——**本轮无需再改一行代码**；缺的从来不是修复，是 fix1 之后的端到端复验证据（§3 记账员判定 / 方案 §5 P0-4 第 4 条）。
- **复现（缺陷形态实证）**：旧序 `python3 tools/img-gc.py --host anolis apply` → argparse rc=2 `invalid choice: 'anolis'`（零证据死亡形态复现）；新序 `apply --host anolis --help` → rc=0（`--help` 在 main() 体前退出，无 ssh/docker）。
- **演练（全部零副作用，未执行任何 apply/rmi）**：① `gc_watch` 真调用+合成 latest.json（use_pct=90 新鲜/71/过期/字段缺/防抖窗/6h 迟滞/dry-run 全分支）9/9 PASS，触发态 spawn argv 精确等于新序、wall=41ms；② 经 keepalive 真 `spawn()` 机制零变异 drill（apply→plan 仅存于测试包装层）5/5 PASS：子进程 05:09:44 正常退出、`img-gc-drill.log` 有完整 plan 报告且无 argparse 错、`/tmp`+耐久证据件各新增 1 行 `kind=plan`（use_pct=71，A=6/B=0/C=100）；③ 作者套件 `补丁/patch3-test-imggc.py` 35/35 rc=0（T9a 精确 argv 序断言 PASS）。
- **回归**：py_compile 双文件 rc=0；模块导入后 TARGETS/CHECKS/FIXES=8/8/8 键集一致；`--print-commands` rc=0；在飞 keepalive pid 3614522（旧代码）未动、未重启、未碰 pidfile。
- **现场痕迹（诚实记账）**：证据件 `状态观测/img-gc-evidence.jsonl` +2 行 `kind=plan`（05:06:17、05:09:44，只读盘点的既定审计追加）；`/tmp/factory-keepalive.log` +2 行 gc-watch drill klog；`alarms.log` 曾被演练注入 2 行合成 gc-watch amber（A9 分支被合成证据触发），**已按原样删除还原**（528→526 行，备份 `/tmp/j3-fix-tests/alarms.log.bak-pre-clean`）。
- **证据目录**：`/tmp/j3-fix-tests/`（j3-repro-old-order.out / j3-new-order-help.out / py_compile.out / rehearsal.out / drill_plan_spawn.py + img-gc-drill.log / author-suite.out / alarms.log.bak-pre-clean）。
- **换血条件判断**：J3 触发路径已具备"演练级"验证；但方案 §5 P0-4 第 4 条的**正式验收**仍以换血同窗的 drill 旗标（`状态观测/img-gc-drill.flag`，P0-2 未落位）为准，且换血四前置（P0-0 人工接力 / P0-1 --dry-run / P0-2 旗标 / P0-3 TERM 序列）不在本代理权限——**是否换血由厂长/主代理裁决**。

---

## 10. 第二循环落账（2026-10-22 09:03:50 起，记账时点 12:41–12:46 CST）

> 本节写作时点 **2026-10-22 12:46 CST**（自测读数 as-of 12:43–12:46）。上一循环（§0–§9）保持原样不改，仅在本节做时点校正。
> **本节一句话**：第二循环把"D-24 tmpfs 治理"从纸面做成实物（三道闸落盘 + 一次性清理回血 623MiB）、把 R2 方案的复审缺口补上（**结论仍是 rejected**）、把 P0-4 四条验收跑通（4/4 PASS）——**但验收通过后 8 分钟，看护进程自己被 /tmp EDQUOT 打死了**（12:21:27），三审据此判 confirmed 并把"现役性"打回。**下一循环第一件事是恢复看护，不是别的。**

### 10.0 账本元信息

| 项 | 值 | 出处 |
|---|---|---|
| 第二循环 run | `dwfrun-abc2de78-f360-459f-9410-f3bc6612ba05`（名：**研究组④资源管理组·第二循环**），09:03:50 起，12:41:41 更新，记账时 status=`running`（本节点 32654 为最后节点，未终） | `~/.zcode/cli/db/db.sqlite` 表 `dwf_run`（`select id,name,status,spent_tokens,time_updated from dwf_run where id like 'dwfrun-abc2de78%'` → running / 101,264,487 tokens / 1792644109030） |
| 流程脚本 | `.zcode/workflow-drafts/研究组4-资源管理组.dwf.ts`（10971B，mtime 09:03）+ 编译快照 `.zcode/workflow-runs/dwfrun-abc2de78-f360-459f-9410-f3bc6612ba05.mjs` | 文件本体 |
| 本循环节点账 | 17 个已完成 ask + 6 个 report + 本记账节点 32654；node id **32467–32654** | `dwf_node` 表 |
| 角色序（ask 序 → actor） | 32467 红队·方案复审(step-5) → 32477 tmp治理设计师 → 32487 红队·tmp设计审查(step-5) → 32491 设计师 R2 修订 → 32505/32522/32532/32537/32542 补丁实施员×5 → 32551/32564/32581/32586/32595 补丁测试员×5 → 32600 补丁测试员（自测缺口）→ 32612 验收执行员 → 32642 红队·三审(step-5) → 32654 状态记账员 | `dwf_node.actor_site_id` 映射 `dwf_actor.name` |
| 模型 | 工作者 GLM-5.3-Flash（`account:bigmodel-individual-coding-plan/GLM-5.3-Flash`）／红队三审全部 `new-provider/step-5-preview`／验收与记账 `minimax/Minimax-M3.1-Flash-Preview` | `dwf_actor.resolved_model` |
| 派单四件事 | A. R2 方案 step-5 复审 v2；B. D-24 tmpfs 治理（/tmp 水位闸 + 产物分流）；C. §6.4 自测缺口中已可执行者；D. P0-4 换血同窗正式验收 + anolis 根分区 80% 定性 | `研究组4-资源管理组.dwf.ts:1-8`（头部注释） |
| 红线执行 | 全程只碰本厂负载、fail-closed 拦新不杀旧、改前备份到 `工具状态备份/`、密钥零明文、未动在飞臂、root 仅只读取证并留证；**未碰 gov**（三审亲验 `grep -i "gov\|governance\|100.64.0.6"` 仅 2 处"方案 B 零操作"表述） | 三审 node 32642 evidence 段 |

### 10.1 记账员本轮自测（12:43–12:46，全部本节点亲跑，非转引）

| 自测项 | 命令 | 输出 | 判读 |
|---|---|---|---|
| **看护现役性（最重要一条）** | `ps -eo pid,lstart,etime,args \| grep -E "[f]actory-keepalive\|[f]actory-sched\|[f]actory-watch\|[m]code-dispatch"` | **无 factory-keepalive 进程**；在跑的只有 factory-sched 2857945（10-21 18:37:32，18:05:38）、factory-sched 3866052（10-22 03:45:14，08:57:57）、factory-watch 3692358（10-22 00:59:18，11:43:53）；mcode-dispatch 无进程 | **看护体系当前为零**（三审 issues[0] 独立复现成立） |
| pidfile / cron 兜底 | `ls -la /tmp/factory-keepalive.pid` → `No such file or directory`；`crontab -l` → **零输出 rc=0** | 无 pidfile、无 cron 兜底 | 与 `factory-keepalive.py:72-74` 自述一致；D-17 本机面仍为否定 |
| **keepalive 死因（逐行读 traceback）** | `tail -60 /tmp/factory-keepalive.log`（全文 1704 行） | 12:21:27 `[graph] 清理旧备份失败 /home/pan-ding/workspace/agent黑灯工厂/工具状态备份/factory2-graph.20261022-112222.json: [Errno 122] Disk quota exceeded` → `[self] 轮异常（不退出）` → **handler 内的 klog 再抛** → `[self] keepalive 退出`；三段 traceback 定位 `:407 prune_graph_backups` / `:148 klog print(line, flush=True)` / `:1064 backup_graphs()` / `:410` / `:1075 main` / `:1090` | **自反馈死锁坐实**：异常处理器内的日志写没有 try 保护 → 二次抛出 → 进程未捕获退出。**这是补丁②硬化了 mcode 心跳写、却漏掉 keepalive 自身 stdout 的直接后果** |
| 本机 /tmp 水位（对补丁阈值） | `df -P / /tmp` → `/dev/nvme0n1p2 490048472 407929532 57152336 88% /`；`tmpfs 7800128 5787624 2012504 75% /tmp`；`findmnt /tmp` → `rw,nosuid,nodev,nr_inodes=1048576,inode64,usrquota` | **/tmp 可用 2012504KiB ≈ 1965MiB**，低于 sched 关闭线 2253MiB **和**预警线 2663MiB | 三保命闸**此刻本应拦新臂**，但 sched/watch 内存中仍是旧码 → 闸未生效（详见 §10.5"现役性推翻"） |
| /tmp 现在谁在吃 | `du -sm --total /tmp/* /tmp/.[a-z]*` → 合计 5657M；前 7 名 `/tmp/afbuild-align2 2423M`、`af-bench-prod-2398779 204M`、`verify4 161M`、`mcode-tune-implementer 104M`、`af-wt-obs2 96M`、`v2 84M`、`bench-fix1-d1-m31f 71M` | 条目数 4051 | **最大单件仍是构建 target 落在 tmpfs**（`afbuild-align2` mtime 12:20:43）＝ §10.3 分流约定**刚落盘就已被违**；`af-bench-prod-2398779`＝清理清单 Tier B 待点头件仍占 204M |
| 作者套件①（补丁①闸，本轮含 tmpfs 探针） | `python3 补丁/patch1-test-gate.py` | `ALL PASS (39/39)` **rc=0** | 通过（29→39 项，新增 T4g/h/i、T5a/b、T6/a'/b/c/c'） |
| 作者套件③（img-gc） | `python3 补丁/patch3-test-imggc.py` | `ALL PASS (35/35)` **rc=0** | 通过（T5c 已按本组建议把"mcode 在途非空"前置条件写进断言，读数不再分裂） |
| 作者套件（watch A4L） | `python3 补丁/patch5-test-a4l-watch.py` | `ALL PASS (9/9)` **rc=0** | 通过 |
| **作者套件④（tmpfs 闸 sched）** | `python3 补丁/patch4-test-tmpfs.py` | **rc=1**，`3 FAILED, 14 passed`：S2a `[gate=False/1964MiB df=1964MiB]`、S6a `[state=pending warns=0 runs=[]]`、S6b `[reliefs=0]`；末行仍无条件打印 **`ALL PASS (14/17)`** | **三保命闸的作者套件非 hermetic**：三项断言耦合 `/tmp` 真实水位，此刻 1964MiB < 关闭线 2253MiB → 闸正确 fail-closed 但断言按"应开闸"写。三审 issues[3] 独立复现成立。**下一轮引用"patch4 套件全过"必须带水位 as-of** |
| 三 tmpfs 补丁存档落位 | `md5sum 补丁/tmpfs闸-*.patch` → `aecc0d2fd771d25f54132c9ac5b1db5d`(90 行) / `0110463e8075a07023f0f62814550a90`(176 行) / `59057adf61741d2c1a98d2b7663cfa1e`(61 行) | 与实施/测试/三审三方报告**逐字一致** | 三个补丁文件均在盘、可比对 |
| 现役三工具落点 | `md5sum tools/factory-sched.py`=47e9991e…（700 行）、`tools/mcode-dispatch.py`=25f93a72…（998 行）、`tools/factory-watch.py`=cb315e90…（947 行）、`tools/factory-keepalive.py`=c53a2669…（drill 旗标已落盘） | 与实施节点报告一致 | 补丁①–④ + drill 旗标五处改动全部在盘 |
| drill 旗标代码落点（亲读） | `sed -n '140,152p;100,112p;880,905p' tools/factory-keepalive.py` | `:107 GC_DRILL_FLAG = {WS}/状态观测/img-gc-drill.flag`；`:148 klog → print(line, flush=True)`（**无 try**，即死因点）；`:883-899` drill 分支（`argv=["python3","tools/img-gc.py","plan","--host","anolis"]` + `os.remove(GC_DRILL_FLAG)` 自毁，1200s 防抖仍适用，dry-run 只打日志） | P0-2 旗标**确已落位**（R2 复审 issues[0] 当时判"从未落盘"是 09:0x 的状态，现已被 12:02 的验收执行员补上） |
| 旗标已自毁 | `ls 状态观测/img-gc-drill.flag` → `No such file or directory` | — | P0-4 第 4 条的"零变异"旁证成立 |
| GC 证据件 | `wc -l 状态观测/img-gc-evidence.jsonl`=23、`/tmp/img-gc-evidence.jsonl`=23、`/tmp/img-gc.log`=34；末行 `{"kind":"plan","ts":"2026-10-22 12:29:20",…,"use_pct":74,…,"foreign":[]}` | 双写一致；21→23 行的两次追加＝11:54 测试员 drill + 12:29 三审 drill | 审计追加链完整可追（12:02:57 验收 drill、12:29:20 三审 drill 均在案） |
| 告警面新码 | `wc -l 状态观测/alarms.log`=587；`grep -c ch-mes-local`=**0**、`grep -c gc-watch`=**1**、`grep -c A4L`=**0** | gc-watch 唯一一条＝05:12:46 amber「anolis /data 镜像GC结果：删 8 张/rmi-fail 0，77%→71%」；A4L=0（watch 仍是旧码）；ch-mes-local=0（CH 健康，预期静默） | 与自测缺口节点口径一致 |
| watch 仍在产线跑 | `stat 状态观测/latest.json / watch-state.json / alarms.log` → 均 **12:43:11** | watch 未死 | 但**已无人监督**（keepalive 亡） |
| mcode 队列 | `python3 -c` 统计 `/tmp/mcode-dispatch/state.json` → `Counter({'judged': 240})`，240 条 | 仍满判收工 | 队列空＝既有 D-34 态，非新故障 |
| 本机根分区（顺带） | `df -P /` → **88%**（used 407929532 / avail 57152336）；`du -sm -x /home/pan-ding/*` → workspace 58279M、afbuild-align2 8958M、afbuild-rt-r1 5267M、zc-ws 5105M、afbuild-rt-c1r1 4948M、afbuild-align-r2 4570M、afbuild-rt-r2 4600M | 与巡检日志 12:0x/12:2x 处置记录（删 `~/af-d20-target` 35G 后回落、现又 88%）同族 | **本机 / 的增长源是 af 构建 target 目录，与 §10.6 anolis / 的定性是两回事**，本组未处置，列 §10.10 待裁决 |
| anolis 根分区（复核 32612 的读数） | `ssh anolis 'date; df -P / /data; du -sm .ollama /opt/gpumachine /srv/bench; docker info --format "{{.DockerRootDir}}"'` | 12:44:16：`/dev/vda3 101985852 77271052 20347148 **80%** /`、`/dev/vdb1 … **74%** /data`；`.ollama 17698M`、`/opt/gpumachine 18222M`、`/srv/bench 2212M`；`DockerRootDir=/data/docker/docker` | 与 node 32612（12:03:43：77,267,072/20,351,128/80%）漂移 ~4MB，**三审（77,254,624）也在同一状态带** → 定性读数可复现 |
| 本节点**未跑** | — | — | `补丁/gc-drill-verify.py`（三审 12:29 已跑并留下 12:29:20 证据行；重跑会再向耐久证据件追加一行，无新信息故不跑）、任何 apply/rmi、任何 root/sudo、任何 patch 真实应用、keepalive 拉起（属需人工接力动作，见 §10.9） |

### 10.2 R2 方案复审 v2 结论（node 32467，红队·方案复审 step-5 新实例，09:03–09:11）

**结论 = `rejected`（8 条）**。这是第二循环的第一条硬事实：**R2 方案至今没有通过独立复审**，且本次复审判的是 v2（R2 修订版），不是 v1。

| # | 等级 | 意见摘要（原文要点，记账员压缩） | 记账员现状判定（as-of 12:46） |
|---|---|---|---|
| 1 | 阻断·主阻断复发 | 方案把 P0-4 第 4 条与 drill 旗标设计写进了文档，但**旗标从未落盘**（`grep -rn "img-gc-drill\|drill" --include=*.py` 只命中两个 .md；`ls 状态观测/img-gc-drill.flag` → 不存在），**而换血已经发生**（pid 3923844 05:12:45、启动行"看护 8 对象…ch-mes-local"）→ 终审最担心的"未经端到端验证的触发路径投产"已成事实 | **已消解**：12:02:32 验收执行员按方案 §5 P0-2 落位旗标（备份 `工具状态备份/factory-keepalive.py.pre-patch3-drill-20261022-120200`），12:02:56 真 keepalive 真 spawn 出新序 argv 的 plan 子进程（§10.5）。**但旗标自毁后代码仍在盘、下次换血继续可用** |
| 2 | 阻断·复发 | §3.5 的止损补强三件（诊断三件 + 24h 失联≥2 次 → 登记 P0 根因债）只写在散文（`:106-109`/`:173`），§5 三张表与 §4 九项裁决清单**无责任人/时限/到期默认路径**；MES 500 根因归属也未进 §4 | **仍成立**：`设计/资源治理统一方案.md` mtime 仍是 **04:54:28**（本循环零改动），三审 12:3x 复验同结论。**部分消解**＝MES 500 根因已由修理组 09:4x 查明修复（`计划/研究组/mes500-根因报告.md`，见 `计划/变更日志.md` 09:4x 行）→ 根因债实际已还，文档未同步 |
| 3 | 重要 | P0-4 第 3 条判据只豁免"空队列退出循环"，**未豁免已升级的熔断形态**（无进程 + 600s 内重启 2 次停止拉起）→ 照方案跑会因与换血无关的既存 D-34 态判失败，**进而触发回滚刚激活的补丁②③** | **仍成立**：12:02:56→12:03:26 换血后同形态复现（`ALARM 600s 内已重启 2 次，超限停止拉起只报警`），验收执行员按方案文字豁免它判 PASS（§10.5）。**这是判据设计缺陷，不是本轮执行缺陷** |
| 4 | 重要·事实错误 | 方案 `:65` 与本文件 §6.4-1 原句"本机 `/` 81% 已超 85% 语义线"——**81% < 85%，算术不成立**；且 A4 的 85% 是 anolis-only（`tools/factory-watch.py:25`） | **仍成立但已过时**：12:43 实测本机 `/` **88%**，是真的越过 85% 了，但越过的是**本机根分区**，而 A4/A4L 仍只看 `/tmp` 与 anolis 分区 → **本机 `/` 至今无任何告警**（alarms.log 无对应码） |
| 5 | 次要·被实测证伪 | 方案 `:63`"`/data` 71%…85% 约 2h 可及"——实测 09:06 为 73%，≈0.47 点/h，85% 约 25h 外 | **仍成立**：12:44 复核 `/data` **74%**（8h 涨 1 点），外推 85% 仍是"十小时量级"，非"小时级" |
| 6 | 次要 | 闭环时限颗粒度不均：P2 全段无日期、§2 表的停手线提案（本机 / 90%、/tmp 85%）未进任何 P 表 | 仍成立 |
| 7 | 如实记录 | 快照漂移（方案 as-of 04:29–04:51，09:0x 实测六面五面朝坏方向移动） | 已漂移更远（12:4x：本机 / 83%→88%、/tmp 61%→75%） |
| 8 | 排除嫌疑 | ①R2 把"先起新验 8 对象后杀旧"改为"TERM→等 pidfile 消失→即起新"是**正当的**（self_guard `:997-1005` 的 `sys.exit(3)` 会拒新进程，红队字面建议不可执行）；②gc_watch 确为非阻塞；③A9 去重与告警路径**已在换血后首轮真实生效**（证据件 `gc-alarm-sent` + `alarms.log:527`） | 全部接受 |

**记账员口径**：**"rejected" 指的是 R2 方案（v2）本身**，与 §4 首轮终审对 v1 的 rejected 是两次独立判定、结论相同。方案文档现役仍是 04:54:28 的 R2 版，**未被修改、未被销账、未通过复审**。第二轮该组若再派单，第一件事是按这 8 条改文档并送第三次复审（见 §10.9）。

### 10.3 tmpfs 治理交付物台账（node 32477 设计 → 32487 红队 rejected 12 条 → 32491 R2 修订 → 5 个实施 → 5 个测试全过）

**设计审查经过**：`tmp治理设计师` v1（32477）→ 红队·tmp设计审查 **`rejected`，12 条**（4 条重要级直指"保命半边"：①闸只挂 `host=="local"` 而 live 图 49 个臂 out 全在本机 `/tmp`、新图永不出现 local 键 → 闸是空操作；②阈值 1.5G/800M 坐在**实测失败点之下**（对齐组：仅余 1.7G 时 dd 205MB 即 EDQUOT）＝用一个不会触发的线防已发生两次的事故；③mcode 探针与 `/tmp` 写失败构成**自反馈**（心跳写 `:434` 无 try，ENOSPC→worker 线程死→假活→熔断）；④`cp 备份件`式回滚会**静默回退他人并发修改**（`factory-sched.py` 在审查窗内被改 616→640 行））→ 设计师 R2 修订（32491）**12 条逐条亲验后接受**。

| # | 交付物 | 路径 / 落点 | 语义（记账员压缩，细节查 node 32505/32522/32532/32537/32542） | 测试证据 |
|---|---|---|---|---|
| ④-a | **tmpfs 水位闸·调度器** | 存档 `补丁/tmpfs闸-sched-R2.patch`（90 行，md5 `aecc0d2f…`）；落 `tools/factory-sched.py` 640→**700 行**（md5 `47e9991e…`），备份 `工具状态备份/factory-sched.py.pre-tmpfs-gate-R2`；套件 `补丁/patch4-test-tmpfs.py` | 常量 `TMPFS_WARN_MB=2663` / `TMPFS_MIN_MB=2253`（env `FACTORY_SCHED_TMPFS_WARN_MB/MIN_MB`，非法回退默认）；`Sched.tmpfs_gate()` 本机 `os.statvfs("/tmp")` 纯本地读、60s 缓存、异常=**盘点失败即 fail-closed**、拦新不杀旧；挂 `launch()` 的 **bench-arm 全体且不限 host**（依据：49 个 live 臂 out 全在 `/tmp`，`host=="local"` 特判版是空操作）；预警带放行但记一次、`_tmp_logged` 三态去重、恢复补"闸解除"行；启动横幅印生效阈值。**冷生效**：在飞两调度器内存中仍是旧码，重启窗才生效 | node 32551 `passed=true`：**作者套件 17/17** + 测试员自设计套件 `补丁/patch4-test-tmpfs-verify.py` **30/30**（零真实压力，只用 env 临时阈值触发；沙箱 `--once` 真进程：3 种 host 味全拦/不终态/零派发、放行带真派发、BIN 桩 canary、假 ssh 无痕、before-after 三拍在飞 sched PID/启动时间不变、`/tmp/factory*.log` grep `tmpfs`=0 行）。⚠️ **本节点复跑 = 14/17 rc=1**（水位耦合，见 §10.1） |
| ④-b | **tmpfs 探针·mcode 派发器** | 存档 `补丁/tmpfs闸-mcode-R2.patch`（176 行，md5 `0110463e…`）；落 `tools/mcode-dispatch.py` 949→**998 行**（md5 `25f93a72…`），备份 `工具状态备份/mcode-dispatch.py.pre-tmpfs-gate-R2`；**补丁①的作者套件原地扩到 39 项** | 第四探针 `probe_tmpfs()`（`GATE_TMPFS_MIN_GB=2.2`，env `MCODE_GATE_TMPFS_MIN_GB`），异常=盘点失败=闸闭，与既有三探针同口径同权，闸闭走**既有 defer 链零新增逻辑**；**同批硬化 ENOSPC 自反馈坑**：defer_tick 心跳写、set_phase 心跳写包 try/except（"写失败不致命"），worker 闸段外套 try（**线程绝不死**） | node 32564 `passed=true`：**39/39** + 自设计 `补丁/patch1-test-gate-verify.py` **34/34**；真进程 `gate-check` 双向翻转（默认 exit 0 / `MCODE_GATE_TMPFS_MIN_GB=9999` exit 4 恰一行 stderr）；defer 全链 D0–D6 实跑；**冷生效活体证据**：keepalive 11:23 拉起的实例印出 `[gate] 资源闸生效: mem≥4.0G disk≥20.0G remote≥4.0G **tmpfs≥2.2G** cache=60s…`。⚠️ 测试员如实记录的观察项：env 填非浮点会在 import 期崩（同族既有风格，非本补丁回归） |
| ④-c | **本地 /tmp 安灯 A4L** | 存档 `补丁/tmpfs闸-watch-R2.patch`（61 行，md5 `59057adf…`）；落 `tools/factory-watch.py` 916→**947 行**（md5 `cb315e90…`），备份 `工具状态备份/factory-watch.py.pre-A4L-R2`；套件 `补丁/patch5-test-a4l-watch.py` | `A4L_TMP_WARN_MB=2662` / `A4L_TMP_GATE_MB=2252`；`probe_local_tmp_mb()` 异常=(-1,盘点失败)；A4L 块在 A4 环之后，**"盘点失败"与"真写满"同码但文案强制区分**（防运维把读数故障当写满）；30min 去重复用 `log_alarms` 既有链零新代码 | node 32581 `passed=true`：**9/9** + 自设计 `补丁/patch5-test-a4l-watch-verify.py` **22/22**（一次过）；现场 3438MiB ≥ 2662 → 零 A4L；**A4L 计数至今 0，因在飞 watch 仍是旧码（冷生效待重启窗）** |
| ④-d | **产物分流约定** | `设计/分流默认根约定.md`（6538B，md5 `428da38e…`）+ `AGENT.md`（md5 `4cd796b3…`，`:29` 新增硬纪律 7），备份 `工具状态备份/AGENT.md.pre-conv-R2` | **撤回** `~/bench-data/wt` 新根提案（grep 全场零在案＝明示不采纳）；收编四条既成默认根：构建 target→`~/afbuild-<名>`、工作树→`~/workspace/af-wt-<名>`、观测数据→`工具状态备份/observability/`、归档→`~/bench-data`；`/tmp` 白名单=工厂运行时件+在跑臂 out+<50MB 短命件；worktree 分支独占规程（续用至分支收口、腾挪用 `git worktree move`、严禁对已检出分支 add）；**生成层边界如实披露**：在飞 run 的编译快照与机制脚本里的 `/tmp` 默认已烤死不追改，持久修点＝各研究组 `.dwf.ts` 生成段 | node 32586 `passed=true`（文档类验证＝逐条事实核验 + 沙箱 git 实验）：撤回 grep 零命中、worktree 禁令两形态沙箱实测均 fatal 且不建目录、四默认根在役亲验、**四守护进程 before/after 同 PID 同启动时间**、未执行任何 move。如实披露偏差 4 项（md5 因后续节点追加行而变、可观测组-state 行号漂移 213→215、关闭线 2252 vs 实码 2253 差 1MiB、"3 个 /tmp 树"成文时快照现已 5 个且 `af-wt-obs` 转 detached） |
| ④-e | **一次性清理（Tier A 已执行）** | 32 件 mv 入 **`~/bench-data/.trash-tmp-20261022/`**（35 项＝32 件+`MANIFEST.md`，`du -sm`=**623MiB**）；零硬删 | 判据 `mtime≥48h`（`-mtime +1` 口径）+**零 fd** +**零 cwd** +不在证据链；执行时刻重跑三查 **32/32 全过**；`/tmp` 可用 2938→3465MiB（62%→55%）；**Tier B 2 件未动待属主点头**：`/tmp/af-bench-prod-2398779`（**204MiB ELF**，10-21 11:16，零引用零句柄，**本节点 12:43 复核仍在 `/tmp` 顶层第 2 大件**）与 `bgml.html` | node 32595 `passed=true`：桶体检 33 项=32 件+MANIFEST、`/tmp` 同名残留 0、`/proc` 现在时刻复扫 32 件引用=0、四守护进程 before/after 同 PID、留证三件齐（桶内 MANIFEST.md / `状态观测/巡检日志.md:188` / 约定档 §5）。**测试员如实记录的发现**：桶与 `/tmp` **异设备**（bucket_dev=66306 vs tmp_dev=51）→ `mv` 回滚是复制+删源，**可回滚但非瞬时**，且 MANIFEST 未含逐件 sha256 |

**共同的诚实边界（五个实施/测试节点一致自陈，记账员采纳）**：①**三保命闸全部"冷生效"**——文件落盘即可，在飞 sched(2857945/3866052)/watch(3692358)/mcode 内存中仍是旧码，**重启窗未开**；②回滚一律 `patch -p1 -R --forward < 补丁/tmpfs闸-*.patch`（不用 `cp` 覆盖，避免回退他人并发修改），三审亲跑三个补丁 `-R --dry-run` 均 rc=0；③校准阈值（2663/2253 MiB）**明示取代厂长原口径 1.5G/800M**，依据是"EDQUOT 实测失败点 @1.7G"，**最终阈值待运营者批窗时终裁**；④`usrquota` 配额顶精确值**不可得**（本机无 `quota` CLI、无 root），只由金丝雀推得失败带 `f_bavail ∈ (0, ~2.0G]`。

### 10.4 自测缺口：执行与跳过（node 32600，11:45–12:00，补丁测试员）

**执行 6 项**（对照 §6.4 原清单，逐项带判据）：

| # | 原缺口 | 结果 | 关键证据 |
|---|---|---|---|
| 1 | §6.4-1 gc_watch 真实端到端 spawn 复验 | ✅ **PASS**（as-of 11:54） | 真 keepalive 模块 → 真 `gc_watch()` → 真 `spawn()`（setsid/日志重定向）；只两处测试包装：触发水位用沙箱合成 `latest.json use_pct=86`、argv 断言后 apply→plan（只读）。spawn 精确捕获新序 argv、`wall=1ms` 非阻塞、真子进程 pid=404496、沙箱 klog 两行、`/tmp/img-gc.log` 新增 10 行完整 plan（use_pct 73 真实值/删集 31 全白名单/foreign 0）、双证据件各 +1 行 `kind=plan` |
| 2 | §6.4-2 换血后真实 30s 轮判活对象 7→8 | ✅ **PASS**（as-of 11:52） | 05:21:46（第 19 轮）→11:52:25（第 799 轮）共 80 条心跳行，逐行解析对象集合恒为 8 个（含 `ch-mes-local`）、轮间集合不一致=0；模块 `TARGETS/CHECKS/FIXES=8/8/8`。**注**：`gc-watch` 不在判活对象属设计（`factory-keepalive.py:36-48`"非判活对象，one_round 内的额外步骤"） |
| 3 | §6.4-2b `alarms.log` 新码出现 | ✅ **PASS** | `gc-watch` 首现（05:12:46 amber＝换血首轮 A9 对 04:16 既有 apply 结果的**迟发补告警**，配套证据件 `gc-alarm-sent`）→ **A9+30min 去重链在产线真跑**；`ch-mes-local` 0 行＝CH 全程健康属预期静默，探活本体已真实运行 80 轮 |
| 4 | §6.4-7 keepalive 判死→拉起 mcode 链 | ✅ **PASS（后半段）** | 11:53:25 拉起 pid=404166、11:56:55 拉起 pid=406089；每次新实例即印补丁①横幅后按 240/240 judged 断点"队列跑完退出"（累计 96 次）→ **新码自重启生效+断点续跑+单实例守卫反复实证** |
| 5 | §6.4-9 T5c 时序假阴性收口 | ✅ **PASS** | 把"mcode 在途非空才做 1:1 比对、在途=0 时 B 源应为空"编码进 `补丁/patch3-test-imggc.py` 的 T5c，复跑 35/35 rc=0，**下一轮不再出现 34/35 vs 35/35 读数分裂**（本节点复跑 35/35 印证） |
| 6 | 换血后四守护在飞未被触碰（全程校验） | ✅ **PASS** | sched 2857945/3866052、watch 3692358、keepalive 3923844 全程同 PID 同启动时间仅 etimes 增长；零 kill/零重启/零 root/零生产文件写入 |

**跳过 6 项**（每条带原因，逐条抄 node 32600）：

| # | 原缺口 | 跳过原因（原文口径） | 记账员评注 |
|---|---|---|---|
| 7 | §6.4-3 补丁② 去重窗"过期后再报"真实跨窗 | 需真实 CH 失联跨 30min；CH 是生产 MES（`bench-mes` 入库依赖）**不可人为停机**，30min 真实窗内也无自然失联事件 | 不可为，非未做 |
| 8 | §6.4-4 补丁③ 真实 `use_pct≥88%` 现场停手 | 需 `/data` 真涨到 ≥88%（填满磁盘＝破坏性，禁止）或改写生产 `latest.json`（越权）；真 apply（04:16:59, 77%）在 <88 区间按设计正常删除 | 不可为；mock=90 真闸链已过（node 32298 F 项） |
| 9 | §6.4-5 probe_mem 读数异常放行分支 | 需本机 `/proc/meminfo` 不可读＝root 级系统干预；mock 分支作者套件已覆盖 | 不可为 |
| 10 | §6.4-6 1800s/86400s 真实时长 | 需 30min/24h 真实推迟事件自然跨越，时长不可压缩（压缩＝改在飞阈值） | 不可为；3s/2s 压秒演练已过 |
| 11 | §6.4-8 方案 R2 红队复审 | **属独立 step-5 终审角色排期**，本执行节点不可代行 | 角色边界；**但本循环该复审由 32467 独立完成（结论 rejected，见 §10.2）** |
| 12 | §6.4-7 前半段"keepalive 自身死亡→被拉起" | 架构性自认知边界（`:72-74`"本脚本自身崩溃没有任何进程拉它"）+ 验证需杀真 keepalive（违红线④） | 不可为。**⚠️ 现实印证**：12:21:27 keepalive 就是这么死的，且 D-17 兜底不存在（12:43 复核 `crontab -l` 零条目） |

**记账员对"6 执行/6 跳过"口径的独立核对**：`node 32600` 的 `executed` 数组 6 条、`skipped` 数组 6 条，与 report 节点 32611 写的"6 项执行/跳过 6 项"一致。三审 issues[6] 称"32600 实跳 4 项、多出的 2 项无对应条目"——**本节点按数组逐条计数为 6 条，不接受该判定**（被指为"多出"的第 5、6 条即上表 #11 `#8` 与 #12 `§6.4-7 前半段`，均有原文条目）。其余三审意见见 §10.7。

### 10.5 P0-4 换血同窗正式验收（node 32612，12:00–12:20，验收执行员）——**4/4 PASS，但现役性已被推翻**

**结论 = `p04_passed: true`（as-of 12:13 CST）**，逐条证据（记账员核对了全部引用的行号与命令形态）：

| 条 | 判据 | 结果 | 证据 |
|---|---|---|---|
| **P0-2（前置）** | drill 旗标落位 | ✅ 已落位 | 落位前亲验 `grep -n "drill" tools/factory-keepalive.py` 零命中、`ls 状态观测/img-gc-drill.flag` 不存在 → 按锚点插入 `:107` 常量 + `:883-899` 分支，`tempfile`+`os.replace` 原子替换，`py_compile` rc=0；备份 `工具状态备份/factory-keepalive.py.pre-patch3-drill-20261022-120200`（sha256 `650d1c1e…`，与改前工作副本同哈希）。**回滚一行**＝cp 备份件 + 重做 P0-3 |
| **P0-3** | 原子换血 | ✅ | 12:02:25 旧 pid 3923844 → `kill -TERM` → `/proc/3923844` 消失=yes → pidfile 消失=yes → 立即 `setsid nohup` 起新 pid **427313**；klog `:1612-1613`「12:02:25 常驻启动 pid=427313 周期 30s 看护 **8 对象**：… ch-mes-local」 |
| **P0-4-①** | 8 对象启动行 | ✅ | 同上 klog `:1612-1613`（本次）与 `:776-777`（05:12 上次换血）；换血后首个 10min 心跳 `:1638`「12:11:26 第 19 轮 … image-feed:done(正常完成退出,不重启) … ch-mes-local:ok」 |
| **P0-4-②** | `--dry-run` 复核 ch-mes-local | ✅ | `python3 tools/factory-keepalive.py --dry-run` → 「ch-mes-local 存活 ping Ok.」；dry-run 在 self_guard 之前 return（`:1026-1028`），pidfile 未被动 |
| **P0-4-③** | mcode-dispatch 无新形态异常 | ✅（**豁免适用，见下**） | `/tmp/mcode-dispatch.log` 形态恒为三行（常驻启动 → `[gate] 资源闸生效…tmpfs≥2.2G…` → 队列跑完退出），全文件 grep `Traceback\|error\|Exception\|exit 4` 零命中；`state.json` 240/240 judged＝队列空属既有裁决 #2 |
| **P0-4-④** | **gc_watch 端到端 drill（三件全中）** | ✅ | 12:02:32 `touch` 旗标 → 12:02:56 klog `:1624-1627`「[drill] 旗标命中 → spawn …（argv=`python3 tools/img-gc.py plan --host anolis`，子命令在前＝**新序**）… 拉起 pid=427877」；双证据件 21→22 行新增 `{"kind":"plan","ts":"2026-10-22 12:02:57",…,"use_pct":73,…,"delete":31,"foreign":[],"fail_closed":null}`；`/tmp/img-gc.log` 14→24 行为完整 plan 报告，**增量段零 argparse rc2**；零变异旁证＝旗标自毁、anolis 镜像池 63 张/115.7GB 前后一致、`/data` 仍 73% |

**⚠️ 记账员必须写下的现役性推翻（三审 issues[0]，本节点独立复现，见 §10.1）**：

- 12:02:25 起役的 pid 427313 **已于 12:21:27 死于 `/tmp` EDQUOT**。traceback 三段：`prune_graph_backups` `:407` → `klog` `:148`（`print` 写 `/tmp/factory-keepalive.log`）抛 `Errno 122` → **异常处理器内 `:410` 的 klog 再抛** → `:1075 main` 的"轮异常（不退出）"处理器里第三次抛 → `:1090` 未捕获退出。
- 机理定性：**补丁②硬化了 mcode-dispatch 的心跳写（ENOSPC 不死线程），却漏掉了 keepalive 自身的日志路径**——supervisor 的 stdout 就重定向在 tmpfs 上，而 `klog` 的 `print` 没有第二层保护。**"保命半边"只保住了被保者，没保住保命者本身。**
- 此刻 `/tmp` 可用 **2012504KiB≈1965MiB**，低于 sched 关闭线 2253MiB 与预警线 2663MiB —— **闸本应正在拦新臂，但三保命闸全部未激活**（sched/watch 在飞进程内存中仍是旧码），而 EDQUOT 已经先一步用实际故障演示了它要防的那件事。
- **因此本节的 P0-4 结论必须读成两句话**：`P0-4 四条判据在 12:13 全部满足（procedurally passed）`；`12:21 起该结论的现役前提不再成立（keepalive 已死，需重做换血窗）`。

### 10.6 anolis 根分区 80% 定性（node 32612，同一节点；本节点 12:44 只读复核）

**结论（原文口径，记账员压缩）**：anolis 根分区 `/` 的 80% **不是本厂产线负载、不是镜像池、不是日志泄漏，而是"静态非产线资产占位 + 平台式 79–80% 常驻"，唯一活增长源是本机交互式 CLI 的 sqlite（与产线无关）**。

| 段 | 内容 | 出处/口径 |
|---|---|---|
| 排除项 | 镜像池在 `/data`（`DockerRootDir=/data/docker/docker`），根分区 `/var/lib` 仅 3.0G；无"已删未释放"幽灵（`du` 与 `df` 差 0.008%、`lsof +L1` 空）；journald 已封顶轮转（`SystemMaxUse=500M` 生效） | node 32612 只读取证；**本节点 12:44 复核 `DockerRootDir=/data/docker/docker`、`/data` 74%、`.ollama 17698M`、`/opt/gpumachine 18222M`、`/srv/bench 2212M` 全部同量级** |
| 占用构成 | `/home/pan-ding 35.6G`（.ollama/models 17.3G **在役** `ollama serve`、.minimax 5.0G、.local/lib 4.9G、workspace 1.7G）｜`/opt 18.4G`（gpumachine 17.8G，cuda 文件 mtime 全 2026-09-30，**属另一项目一次性资产**）｜`/home/anuser 9.0G`｜`/var 4.0G`｜**本厂在 anolis 的实际占用 ≈ 4.6G（ch-mes 735M + /srv/bench 2.2G + workspace 1.7G），占 6%** | 同上 |
| 活增长源 | 5 分钟定标：`df` +736KB/5min ≈ **200MB/天**；分解＝`.minimax` 的 `runtime-state.sqlite`(3.9G)+WAL(106MB) 在写，journal/ollama/srv 全 0 | 同上 |
| **"持续爬升"前提不成立** | 10-21 17:5x 80% → 10-22 04:29 79% → 10-22 12:03/12:44 **80%（余 19.4G）**，19h 净变化≈0（余量反增）＝ 79–80% 平台震荡；旁证 `find /srv -xdev -newermt "2026-10-21 12:00"` 为空＝产线结果目录 24h 零新写 | **本组据此推翻首循环"根分区持续爬升"的素材定性**（§2.1 面 2 与 §8 素材里的"80% 爬升"应改为"平台震荡"） |
| 真问题（风险≠成因） | ①anolis 根分区 `/` **完全在闸外**（磁盘闸与 GC 只覆盖 `/data` 85/88 双线，A4 是 `/data`-only）；②可回收面只剩两块**非产线资产**（`~/.ollama/models` 17.3G 在役、`/opt/gpumachine` 17.8G 属他项目）——按红线未动，交运营者；③按现速率 19.4G 余量约 3–4 个月耗尽，**不构成近期事故风险** | 同上 |

**记账员标注**：本节的取数用了 root（`ssh root@100.64.0.7`），验收执行员声明"仅 状态观测 的只读 du/df/find/docker 查询，均已留证"；本节点 12:44 的复核**未用 root**（`ssh anolis` 免密只读）即取到同量级读数。三审亲验同样只读，并如实标出 `/home/anuser 9.0G` 因权限不可复验。

### 10.7 三审意见（node 32642，红队·三审 step-5 新实例，未参与本循环任何环节，12:20–12:41）

**结论 = `confirmed`（7 条）**。记账员逐条判定：

| # | 等级 | 三审意见 | 记账员判定（as-of 12:46） |
|---|---|---|---|
| 1 | **阻断** | 「P0-4 过」已是过期状态：12:21:27 keepalive 死于 `/tmp` EDQUOT（`prune_graph_backups` 的 klog print → 处理器内 klog 再抛 → 未捕获退出），无进程、无 pidfile、`crontab` 零条目 → 看护体系全亡，仅剩 3 个无人监督的守护进程。tmpfs 补丁硬化了 mcode 心跳却没 harden keepalive 自身日志路径 | **接受，且本节点已独立复现**（§10.1 前两行＋§10.5）。列为 §10.9 第一动作 |
| 2 | 重要 | `/tmp` 已 1969MiB，低于 sched 关闭线 2253 与预警线 2663，**闸却未激活**（sched/watch 仍是旧码），"保命半边"在最需要它的时刻未生效 | **接受**；本节点复核 2012504KiB≈1965MiB，数值同族（1969 vs 1965 为其 12:40 与本节点 12:43 之差） |
| 3 | 重要 | R2 复审第 2 条阻断在盘上未处置：`设计/资源治理统一方案.md` mtime 仍 04:54:28，止损三件仍只在散文，§5 三表/§4 清单无责任人时限，MES 500 根因归属未入 §4；事件上 09:4x 根因已查明修复，**部分消解但文档未同步、R2 驳回未销账、无第二次复审** | **接受**（本节点 `ls -la 设计/资源治理统一方案.md` 复核 mtime＝`Oct 22 04:54`） |
| 4 | 重要 | `补丁/patch4-test-tmpfs.py` **非 hermetic**：12:37 复跑得 **14/17 rc=1**（S2a/S6a/S6b 因真实水位 1972MiB<2253 失败，闸本身正确 fail-closed），而 `:281` 无条件打印「ALL PASS (14/17)」；引用"套件全过"必须带水位 as-of | **接受，且本节点以 `python3 补丁/patch4-test-tmpfs.py` 复现到同一条**（3 FAILED / 14 passed / rc=1，见 §10.1）。**这是本轮唯一被证伪的测试证据口径，账要改写** |
| 5 | 次要 | `补丁/gc-drill-verify.py` 的 verdict 时序不稳：12:29 三审亲跑 rc=1（实质证据全复现：新序 argv、真 spawn pid=484033、双证据件 +1 行 `ts=12:29:20`、img-gc.log 新段 10 行零 argparse rc2），但因未 `wait` 的 setsid 子进程成 zombie、180s 内 `/proc` 仍在而判 FAIL | **接受机理**（本节点**未复跑**，采信其 12:29:20 证据行仍在盘：§10.1 证据件末行实测）；**建议下一循环给脚本补 `waitpid` 或改判据**，否则 P0-4 第 4 条的验收工具本身会时真时假 |
| 6 | 次要 | 记账口径小差：wrapper 写"6 执行/跳过 6"，而 32600 实跳 4 项，多出 2 项无对应条目 | **不接受**（见 §10.4 末段：`skipped` 数组逐条计数为 6，与 report 32611 一致） |
| 7 | 披露 | 三审自身生产写入：重跑 drill 向两个证据件各 +1 行 `kind=plan`（22→23）、`/tmp/img-gc.log` +10 行；零 rmi、零 apply | 接受（**本节点实测两份证据件均 23 行、`/tmp/img-gc.log` 34 行**，与之一致） |

**三审的抽验做法（本节点记其可信度）**：它自述抽了 2 项亲验（`gc-drill-verify.py` 重跑、md5/行号/备份哈希/P0-4 物理证据逐条核），并跑了 4 个套件、3 个 `-R --dry-run`、3 个 `py_compile`、12:4x 的一组现场读数。**本节点对其中可复现的 4 项（keepalive 死亡链、/tmp 水位、patch4 套件 14/17、证据件行数）逐项复现，结论一致；唯一分歧是 issues[6]（计数），已给出反证。**

### 10.8 第二循环后五态总表（记账员口径，as-of 12:46）

| 组件 | 落点 | 状态 | 依据 |
|---|---|---|---|
| 补丁① mcode-dispatch 资源闸（三探针） | `tools/mcode-dispatch.py` | ✅ 在役 | 换血后新实例横幅仍印（11:23 等多次） |
| 补丁① **＋第四探针 tmpfs** | 同上 `:131/:373/:413-419` | 🟡 **代码在盘、冷生效未激活** | 现无 mcode 进程；在飞 sched/watch 同样未重启 |
| 补丁② anolis `~/ch-mes/guard.sh` + crontab | anolis 侧 | ✅ 在役（首循环结论，未变） | — |
| 补丁② keepalive `ch-mes-local` | `tools/factory-keepalive.py` | 🟡 **代码在盘，但看护者已死** | 12:13 曾验 `ping Ok.`；12:21:27 起无人执行该判据 |
| 补丁③ `tools/img-gc.py` 执行器 | 同 | ✅ 在役可用 | 12:02:57 真 plan 出报告 |
| 补丁③ gc_watch 自动触发 | 同 | ✅ **P0-4 第 4 条已正式通过**（12:02:56 drill 新序 argv＋证据双写＋零 argparse rc2） | 但触发者 keepalive 已死 → 现役形态随 §10.5 |
| ④-a sched tmpfs 闸 | `tools/factory-sched.py:78-85/412/453-471` | 🟡 代码在盘、冷生效未激活（**此刻正需要它**） | §10.5 |
| ④-b mcode tmpfs 探针 | `tools/mcode-dispatch.py` | 🟡 同上 | §10.3 |
| ④-c watch A4L | `tools/factory-watch.py:73-79/578/639-648` | 🟡 同上（alarms.log 中 A4L 计数 **0**） | §10.1 |
| ④-d 分流约定 | `设计/分流默认根约定.md` + `AGENT.md:29` | ⚠️ **已成文但当天即被违**（`/tmp/afbuild-align2` 2423M，mtime 12:20:43） | §10.1 `/tmp` 排名 |
| ④-e 一次性清理 Tier A | `~/bench-data/.trash-tmp-20261022/` | ✅ 已执行（623MiB 软删，48h 浸泡后二次确认 `rm` 未执行） | `巡检日志.md:188` |
| ④-e Tier B 2 件 | `/tmp/af-bench-prod-2398779`(204MiB) + `bgml.html` | ⏸ 待属主点头 | §10.10 |
| **keepalive 自身** | `tools/factory-keepalive.py` | 🔴 **死亡（12:21:27 EDQUOT）** | §10.1/§10.5 |

### 10.9 下一循环动作

#### 10.9.1 P0（**等运营者/厂长批窗；第 1 条是本组唯一能立刻止血的动作**）

| # | 动作 | 判据 / 依据 | 记账员补充（as-of 12:46） |
|---|---|---|---|
| **P0-A** | **恢复看护（人工接力）**：`cd /home/pan-ding/workspace/agent黑灯工厂 && setsid nohup python3 tools/factory-keepalive.py >> /tmp/factory-keepalive.log 2>&1 < /dev/null &`，执行人全程终端旁；pidfile 已不存在故 self_guard 不会拒 | 三审 issues[0]；§10.1 前两行实测（无进程/无 pidfile/`crontab -l` 零条目） | **拉起前必须先看 §10.9.2 的 P0-B**：按现状拉起来，它大概率会在下一轮 `prune_graph_backups` 的 klog 上**再死一次**（/tmp 仍 1965MiB < 关闭线 2253MiB） |
| **P0-B** | **先救 stdout（或先腾 `/tmp`）**：三选一 —— ①把 keepalive 日志目标迁出 tmpfs（`/tmp/factory-keepalive.log` → `~/bench-data/` 或工作区）；②给 `klog()`（`:148`）加 try/except 使日志写失败不再杀进程（最小改动，与补丁②对 mcode 心跳的硬化同款）；③先按 §10.9.2 腾出 `/tmp` ≥2.3G 再拉 | `factory-keepalive.py:148`（`print(line, flush=True)` 无保护，`:410`/`:1075` 两层处理器内再调 klog＝三重放大）；根因是 stdout 重定向在 tmpfs | **记账员建议 ②+③**：②是一行级防御、③解除触发条件；①涉及面更大但一劳永逸。**三选一属需裁决项（见 §10.10-5）** |
| **P0-C** | **三保命闸的激活窗口**：`tools/factory-sched.py`(700 行) / `factory-watch.py`(947 行) 需重启在飞进程才生效；重启需臂换题间隙 + 人工接力先例 | §10.3 四项共同"冷生效"边界；§10.5 现役性 | 当前 `/tmp` 1965MiB **已在关闭线之下** → 一旦激活，新臂将立即被拦（这是设计意图，但会**立刻停派**）。**故重启窗口前必须先 P0-B③ 腾出空间，否则闸一开就把产线停了** |
| **P0-D** | **本机根分区 `/` 88%** 处置口径 | §10.1 本机 df；巡检日志 12:0x/12:2x（删 `~/af-d20-target` 35G 后回落又回 88%） | 本组盘点：`workspace 58.3G`、`afbuild-align2 8.9G`、`afbuild-rt-r1 5.3G`、`zc-ws 5.1G`、`afbuild-rt-c1r1 4.9G`、`afbuild-align-r2/rt-r2 4.6/4.6G`。**归属待运营者确认**（fork 考古重跑资产按零接触纪律不动），见 §10.10-6 |
| **P0-E** | **方案 R2 按三审/R2 复审的 8+3 条改文档并送第三次复审** | §10.2 issues 2/3/4/5/6；§10.7 issues 3 | 改前必读 §10.9.3 的一句话：**"rejected" 指的是 v2，不是 v1**；v1 的 8 条已在 R2 里核销过一轮，别混账 |

#### 10.9.2 P1（本周；责任人＝资源组，时限取自方案 §5 表 + 本组新判）

| # | 项 | 时限 | 记账员注（as-of 12:46） |
|---|---|---|---|
| 1 | **`patch4-test-tmpfs.py` 修汇总文案 + 隔离真实水位**（S2a/S6a/S6b 三项改为"注入水位"而非读真 `/tmp`；`ALL PASS` 只能在零失败时打印） | 下一循环首日 | §10.1/§10.7-4。**这是本轮唯一被证伪的测试口径，不修则下一轮的"套件全过"不可引用** |
| 2 | **`gc-drill-verify.py` 补 `waitpid`（或改 zombie 判据）** | 同上 | §10.7-5：P0-4 第 4 条的验收工具本身时真时假 |
| 3 | watch 增**本机 `/`** 水位告警（新码，与 A4L 同链） | 10-24 前（沿用） | §10.2-4：本机 `/` 已 88%，仍无任何告警码；A4/A4L 只看 anolis 分区与 `/tmp` |
| 4 | `factory-sched` local 臂准入双条件 | 10-24 前（沿用） | 现状未变 |
| 5 | img-gc apply 尾部 MES `image_gc` 事件 | 10-25 前（沿用） | — |
| 6 | `tools/results-archiver.py`（tar+sha256+每日完整性巡检 → `alarms.log code=archive-check`） | 10-25 前（沿用） | **这是 §10.10-1 重迁移的前置件**：不先有归档器与完整性校验，结果目录迁移＝裸奔 |
| 7 | 告警最后一公里（宿主侧 cron 消费 alarms.log 或用户 timer；落地前人工兜底） | 10-26 前提案（沿用） | 本轮新增论据：**keepalive 死后无人拉起、告警也无人消费**，"最后一公里"已从"待提案"升级为"待裁决" |
| 8 | **（新）`/tmp` 分流约定的执行侧落地**：把各研究组 `.dwf.ts` 生成段的 `/tmp` 默认改到 `~/afbuild-*` / `~/workspace/af-wt-*`（§10.3 ④-d 披露的"持久修点"） | 下一循环 | 约定 10:38 落盘，**12:20 就出现 `/tmp/afbuild-align2` 2423M**；且 12:2x 又出现第二套约定 `~/afbuild-shared`（`工具状态备份/构建约定.md`）——**两套约定并存需合并口径** |
| 9 | **（新）keepalive 日志/关键写路径的 EDQUOT 硬化**（P0-B②的正式实施 + 套件） | 与 P0-A 同窗 | 与补丁②对 mcode 心跳的硬化同款模式（写失败不致命），可复用其测试矩阵 |

#### 10.9.3 P2（下代构建周期，只 commit 不部署）

`af-bench` arm_resource 计量 + D-22 命名；D-15 在跑臂软暂停；out 根迁 `~/bench-data`（= §10.10-1）；本机镜像一次性 GC（需先修 D-30）；§10.2-6 的 P2 时限补日期。

### 10.10 需运营者裁决的重迁移项清单（本轮**一项都未执行**，全部登记）

| # | 重迁移项 | 现状实测（as-of 12:43–12:44） | 为什么本组不动 | 裁决需要什么 |
|---|---|---|---|---|
| **1** | **产线 `/tmp/bench-*` 结果目录整体迁出 tmpfs**（D-24 主项，方案 §4-#8 / P2-3） | `ls -d /tmp/bench-*` = **138 个目录**，`du -sm --total` = **1238 MiB**；最大者 `bench-fix1-d1-m31f 72M`、`-step5 60M`、`-glm-cp 52M` | 迁移要停臂或改 symlink，且历史 1.2G 结果需先有归档与校验；本组红线"在飞臂不动" | **前置件**：P1-6 `results-archiver.py` 落地并跑通完整性巡检；**窗口**：臂换题间隙；**顺序**：归档→校验→切 symlink→留旧路径一段观察期 |
| **2** | **`/tmp/af-wt-*` 工作树迁出**（分流约定 §3 的"续用至分支收口"例外到期后的腾挪） | `git -C af worktree list` = **7 条**，其中 **5 条仍注册在 `/tmp`**：`af-wt-align-r2@936fa48`、`af-wt-align2@0dd1a23`、`af-wt-align2-r1@5d9c94d`、`af-wt-obs@d73338e(detached)`、**`af-wt-obs2@59c1d6c` 96M** | 三条分支（`fix4-align-r2`/`fix4-align2`/`fix4-align2-r1`/`fix4-observability`）**正在被在飞 run 使用**；迁移需属主确认空闲＋`git worktree move` | 逐分支**属主确认**；`af-wt-obs` 现为 detached HEAD（`fix4-observability` 已在 obs2 检出），须先定它是否还需要 |
| **3** | **清理清单 Tier B 2 件点头** | `/tmp/af-bench-prod-2398779` = **204MiB 单文件 ELF**，mtime 10-21 11:16，零 fd/零 cwd/全仓零引用（设计＋实施＋测试＋三审四方复核一致）；`bgml.html` 132K | 设计明写"执行时须属主一次点头" | 点头后并入桶 `~/bench-data/.trash-tmp-20261022/`（**注意异设备 mv 是复制+删源，非瞬时**；建议同时补 `sha256`） |
| **4** | **一次性清理桶的 48h 浸泡后 `rm -rf` 二次确认** | 桶内 32 件 + `MANIFEST.md`，`du -sm`=623MiB，落盘 10:48:07 → **浸泡期在 10-24 10:48 后到期** | 协议明文"48h 浸泡后二次确认"；MANIFEST 未含逐件 sha256（测试员如实披露） | 到期后由届时节点执行并巡检留证；建议先补哈希再删 |
| **5** | **keepalive 日志是否迁出 tmpfs**（P0-B 的 ①/②/③ 三选一） | `/tmp/factory-keepalive.log` 现 **1704 行**，`klog` 无 try 保护（`:148`） | 三条路各自越不同边界（迁路径=改运维约定／改码=改生产守护／先腾空间=依赖 P1-8） | 裁决路线；**记账员倾向 ②+③**（见 P0-B） |
| **6** | **本机根分区 `/` 88% 的 af 构建 target 归属** | `~/afbuild-align2 8.9G`、`afbuild-rt-r1 5.3G`、`afbuild-rt-c1r1 4.9G`、`afbuild-align-r2 4.6G`、`afbuild-rt-r2 4.6G`、`workspace 58.3G`；巡检日志 12:0x 已删 `~/af-d20-target` 35G | 巡检日志 12:0x/12:1x 记 `afbuild-rt-r1/c1r1` **疑似 fork 考古重跑资产，按零接触纪律不动** | 确认归属后清理或转正为 `~/afbuild-shared` 口径 |
| **7** | **两套构建约定并存** | `设计/分流默认根约定.md` §1（`~/afbuild-<名>`）vs `工具状态备份/构建约定.md`（全部 worktree 用 `CARGO_TARGET_DIR=~/afbuild-shared`） | 两份文档都是当日产物，合并需运营者定口径 | 合并为单一约定，否则下一轮继续两头写 |
| **8** | **anolis 根分区 80% 的两块非产线资产**（`~/.ollama/models` 17.3G 在役、`/opt/gpumachine` 17.8G 属他项目） | §10.6；本节点 12:44 复核同量级 | 红线："非本厂资产不可触碰" | **本组不动，交运营者**；同时需裁决"anolis 根分区是否补阈值/告警"（当前完全在闸外） |
| **9** | **MES 500 根因债的销账** | 根因已由修理组 09:4x 查明并修复（`计划/研究组/mes500-根因报告.md`，`变更日志.md` 09:4x 两行），但方案 §4 九项清单未收录、本文件 §8-#4 仍挂"待运营者派组批窗口" | 事实已变，账未销 | 运营者确认后可销 §8-#4 并在方案 §4 补行；另 `clickhouse-mes.service`（已写未装）与**MES 可观测基建迁 mingda-website**（巡检日志 11:1x 运营者决策）属跨组条目 |
| **10** | **本机 root 项**（journald 500M、usrquota 配额顶、watcher `exec` 无关项） | 10:1x 巡检记"本机全量免密 sudo 已核，按纪律自限"；`quota`/`repquota` CLI 本机不存在 → **tmpfs 阈值只能静态校准** | 纪律自限 | 若要精确配额顶与 journald 限额，需运营者明确"本组可用 sudo"的边界 |

### 10.11 诚实边界（记账员节点 32654 本轮跑了什么 / 没跑什么）

**本节点亲跑并记入 §10.1 的**（全部只读或工作区内自测）：`ps` 全量进程与启动时间、`/tmp/factory-keepalive.pid` 存废、`crontab -l`、`df -P / /tmp`、`findmnt /tmp`、`du -sm`（`/tmp` 顶层与 `/home/pan-ding/*`）、`ls -d /tmp/bench-*` 与 `git -C af worktree list`、`md5sum`（三 tmpfs 补丁 + 分流约定 + AGENT.md + 三工具 + keepalive）、`wc -l`（两份 GC 证据件 / img-gc.log / alarms.log）、`grep -c`（`ch-mes-local` / `gc-watch` / `A4L`）、`tail -60 /tmp/factory-keepalive.log` 读完整死亡 traceback、`sed -n` 读 keepalive `:100-152/:880-905` 亲验 drill 分支与 klog 实现、`stat` 三个状态件新鲜度、`python3` 统计 `state.json` 相位、**四个作者套件全跑**（39/39、35/35、9/9 rc=0；patch4 **14/17 rc=1**）、`ssh anolis` 只读复核 `df -P / /data` + `du -sm` + `docker info`。

**本节点未跑（明确记为未验）**：`补丁/gc-drill-verify.py`（三审 12:29 已跑，留 12:29:20 证据行）；任何 `img-gc.py apply` / `docker rmi` / `docker prune`；任何 keepalive 拉起、任何在飞进程重启（sched 2857945/3866052、watch 3692358 全程未动）；任何 root/sudo；任何 `patch -p1` 真实应用（三个 tmpfs 补丁的 `-R --dry-run` 由三审跑，本节点未复跑）；`/var/lib/docker` du（root-only）；本机 CH 停机实验；`tools/factory-keepalive.py --dry-run`（**本节点未跑**——12:13 的那一次是验收执行员跑的）。

**本节点未做**：未修改任何工作区文件（除本状态文件 §10 的追加）、未改任何生产配置、未触碰 gov 与非本厂资产、未动 `/tmp` 内任何件（含桶与 Tier B）。

**给下一轮的读法提醒**：本节所有数字带 as-of 12:43–12:46 CST；`/tmp` 水位、`alarms.log` 行数、镜像池、磁盘水位在 10-22 仍在剧烈变动（`/tmp` 今日 57%→88%（被清理）→75%；`/` 83%→88%）。**引用前必须重跑命令取新值，禁止沿用本节旧值作决策依据**（承 §8 账本纪律）。
