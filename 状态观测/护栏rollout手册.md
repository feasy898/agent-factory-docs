# af-bench 容器资源护栏 · 换装（rollout）手册

> 2026-10-21 建立（修理组子代理）。**本手册只写步骤，不执行换装**——执行归主代理/厂长裁决。
> 背景：anolis 10-21 因"测评容器无内存上限 + 无 swap"耗尽假死两次。护栏=af-bench 每个
> docker run 创建点带 `--memory/--pids-limit`（agent 6g/512、TB 2g/256；fix1/fix2 判分
> 在 agent 容器内原地执行，随 6g 封顶）。护栏已按代际移植并构建验证（见 §6），
> **但 af-bench-guardrail（d7f2953f，fix3 代）严禁上任何产线**——它带 fix3 的
> judge_mode=clean 干净判分容器，会污染 fix1/fix2 数据可比性。

## 1. 现状核对：两调度器当前 BIN（/proc/<pid>/environ 法）

两条产线各一个 `python3 tools/factory-sched.py` 实例，凭 environ 区分（缺省=主产线）：

```bash
for p in $(pgrep -f 'tools/factory-sched.py'); do
  echo "== pid=$p cwd=$(readlink /proc/$p/cwd)"
  tr '\0' '\n' < /proc/$p/environ | grep -E '^(BIN|AF_SCHED_GRAPH|AF_SCHED_STATUS|AF_SCHED_LOG)=' \
    || echo "  （无 BIN/AF_SCHED_* → 主产线缺省口径）"
done
```

判读（2026-10-21 18:2x 实测值）：

| 产线 | environ 特征 | BIN 实际路径 | 日志 / 状态 |
|---|---|---|---|
| 主产线（fix1） | 无 BIN/AF_SCHED_*（keepalive spawn 时 strip 掉，恒为缺省） | `/home/pan-ding/workspace/agent黑灯工厂/af/target/debug/af-bench` | `/tmp/factory.log` / `/tmp/factory-status.json` |
| 实验线（fix2） | `AF_SCHED_GRAPH=/tmp/factory2-graph.json`、`AF_SCHED_STATUS=/tmp/factory2-status.json`、`AF_SCHED_LOG=/tmp/factory2.log`、`BIN=…/af/target/debug/af-bench-fix2` | 同左 BIN | `/tmp/factory2.log` / `/tmp/factory2-status.json` |

environ 只给路径，**必须再 sha 一遍文件本体**确认盘上字节：

```bash
B=/home/pan-ding/workspace/agent黑灯工厂/af/target/debug
sha256sum $B/af-bench $B/af-bench-fix1 $B/af-bench-fix2 $B/af-bench-fix1-guardrail $B/af-bench-fix2-guardrail $B/af-bench-guardrail
```

期望（2026-10-21 18:2x 实测）：af-bench 与 af-bench-fix1 均 `ae5eef47…`（fix1 钉死件）、
af-bench-fix2 `b30794b5…`、af-bench-fix1-guardrail `5494a49e…`、af-bench-fix2-guardrail
`d2b36cab…`、af-bench-guardrail `d7f2953f…`（fix3，禁上产线）。

辅助事实：keepalive=`python3 tools/factory-keepalive.py`（pidfile `/tmp/factory-keepalive.pid`，
日志 `/tmp/factory-keepalive.log`，30s 轮poll、状态新鲜度阈值 300s、防抖窗 600s 内最多重启 2 次）；
看护对象名 main-sched / exp-sched。watchdog=`tools/factory-watch.py`，看板=8790 端口
`状态/看板/index.html`。

## 2. 换装步骤（两代际同构；以主产线 fix1 为例，实验线换路径即可）

> 原则：**原子换名（mv rename），禁 `cp` 覆写同 inode**（ETXTBSY/在跑进程映射风险）。
> 护栏主副本 `af-bench-fix{1,2}-guardrail` 始终保留，换入的是它的副本。

1. **前置确认**：§1 的 sha256 全部符合期望；`pgrep -f 'tools/factory-sched.py'` 恰 2 个实例。
2. **记录现状**（供回滚对账）：`tail -1 /tmp/factory-status.json`；两条产线各记一条最新结果行
   （`tail -1 <out目录>/results.jsonl`）。
3. **停调度器**：`kill -TERM <主产线调度器 pid>`（pgrep+environ 定位，勿误杀实验线）。
   注意：keepalive 会在 ≤30s 内自动重启它——**这正是步骤 5 的"拉起"，无需手工起**；
   因此步骤 4 的换文件要在 kill 后秒级完成（本地 mv，213MB 副本提前 cp 好）。
4. **换二进制名**：
   ```bash
   cd /home/pan-ding/workspace/agent黑灯工厂/af/target/debug
   cp -p af-bench-fix1-guardrail af-bench.guardrail-new   # 提前备好，kill 后只做 mv
   mv -f af-bench.guardrail-new af-bench                  # 原子 rename
   sha256sum af-bench                                     # 必须=5494a49e…
   ```
5. **keepalive 拉起**：观察 `/tmp/factory-keepalive.log` 出现 `拉起 pid=… cmd=python3 tools/factory-sched.py`（main-sched）。
   如需手工拉起（keepalive 故障时）：先 `pgrep -f 'tools/factory-sched.py'` 确认无残留，再
   `setsid nohup python3 tools/factory-sched.py >> /tmp/factory.log 2>&1 < /dev/null &`。
6. **验证**：见 §3。

**实验线（fix2）差别**：BIN 路径=`af/target/debug/af-bench-fix2`，换入件=af-bench-fix2-guardrail，
换后 sha 必须=`d2b36cab…`；调度器日志=/tmp/factory2.log。**该文件必须始终在场**——
keepalive 的 exp-sched 逻辑：BIN 文件缺失只 ALARM 不拉起（需人工），所以只能 mv 替换不能 rm。

## 3. 换装后验证

1. **调度器健康（内存门日志）**：`tail /tmp/factory.log`（实验线 /tmp/factory2.log）——重启后
   恢复按轮派臂日志、无 traceback。内存门（factory-sched.py，anolis MemAvailable<15G 时
   fail-closed 暂派新臂、恢复自动放行）命中时打 `内存闸暂停派臂：anolis available <n>G < 15G…`；
   **内存充足时无此行属正常**，此行是门工作时的标记而非健康必需。
2. **容器真的带上限**（新派臂的容器，anolis 上执行）：
   ```bash
   # D-37（fix4-container-names 分支，2026-10-22）起 swev agent 容器名带产线实例前缀：
   # afbench-<instance>-swev-<task>-<profile>，instance = --out 目录 sha256 前 8 位。
   # 换装窗前旧二进制仍产旧名 afbench-swev-<task>-<profile>——两种名都可能出现，
   # 按名 inspect 前先 `ssh anolis docker ps --format '{{.Names}}' | grep <task关键词>` 取实际名。
   ssh anolis "docker inspect <实际容器名> --format '{{.HostConfig.Memory}} {{.HostConfig.PidsLimit}}'"
   ```
   期望 swev agent 容器 `6442450944 512`（6g/512）；TB 任务/验证器容器 `2147483648 256`（2g/256）。
   换装前已在跑的旧容器无上限（Memory=0），会自然跑完，属预期——护栏只覆盖新起容器。
3. **代际未被污染（结果行对账）**：新落 results.jsonl 行——
   - 主产线（fix1）：`scaffold=v2`；
   - 实验线（fix2）：`scaffold=v3` 且**无 judge_mode 字段**。
   若实验线出现 `judge_mode=clean` 或每次判分多出一个独立干净判分容器（fix3 特征），
   **说明上错了二进制，立即按 §4 回滚并上报**。

## 4. 回滚步骤

与 §2 同构（停调度器→mv 回旧件→keepalive 拉起→验证）：

- **主产线 fix1**：回滚源=`af/target/debug/af-bench-fix1`（`ae5eef47…`，与换装前 af-bench
  逐字节相同）；或换装前另存副本。`mv -f af-bench-fix1 af-bench` 后 sha 必须=`ae5eef47…`。
- **实验线 fix2**：换装前先 `cp -p af-bench-fix2 af-bench-fix2.prev-b30794b5` 留存；回滚=
  `mv -f af-bench-fix2.prev-b30794b5 af-bench-fix2`，sha 必须=`b30794b5…`。
  （也可从 git 代际代码态 2edfdf0 重建，但盘上留存件更快。）
- 回滚后验证同 §3：新起容器 inspect Memory=0/PidsLimit=0（旧二进制无标志）；新结果行
  scaffold 回到该代际口径（fix1=v2 / fix2=v3 无 judge_mode）。

## 5. 哪个代际换哪个文件（对照表）

| 产线 | 代际 | 调度器 BIN 路径（af/target/debug/ 下） | 换装前 sha256 | 换入文件 | 换装后 sha256 | 回滚来源 |
|---|---|---|---|---|---|---|
| 主产线 | fix1 | `af-bench` | `ae5eef47…` | `af-bench-fix1-guardrail` | `5494a49e…` | `af-bench-fix1`（`ae5eef47…`，同字节） |
| 实验线 | fix2 | `af-bench-fix2` | `b30794b5…` | `af-bench-fix2-guardrail` | `d2b36cab…` | 换装前留存副本（`b30794b5…`） |
| —— | fix3 | `af-bench-guardrail` | `d7f2953f…` | **任何产线不得换入**（judge_mode=clean 污染） | —— | —— |

git 出处（均已推 gitea origin）：护栏移植=分支 `guardrail-fix1`（fb76068，CI 产物 d083565）
与 `guardrail-fix2`（725fceb，CI 产物 94cd192），各自基于代际钉死代码态 327ddee / 2edfdf0。
`af-bench-poc`（c62c6ab2）不涉本次换装。

## 6. 冒烟证据与局限（换装前已完成的验证）

- **anolis docker 29.8.1 双冒烟通过**（容器已删净，remaining=0）：
  `--memory 64m --pids-limit 16`：创建+`docker exec echo` 正常，inspect=`Memory=67108864 PidsLimit=16`；
  生产值 `--memory 6g --pids-limit 512`：inspect=`Memory=6442450944 PidsLimit=512`。
  标志形态与二进制实际下发字符串一致（`docker run -d --name <c> --memory <m> --pids-limit <p> …`）。
- **二进制级**：`strings` 确认两个新二进制各含 4 处 `--pids-limit` 创建点（swev agent×1 + TB×3）、
  `verify_clean` 0 命中（无 fix3 干净判分容器）；af-bench 单测含护栏常量测试通过。
- **局限（如实）**：未做完整 bench 运行冒烟（需任务包+档案+凭据，且会起真实任务容器）——
  docker 对参数的接受度由同字符串 docker 级冒烟覆盖；代际钉死字节由构建前后 sha256
  逐字对照覆盖；判分语义未动由代码 diff 审查+CI 七门覆盖。

## 7. 风险与注意

- **keepalive 30s 抢跑窗口**：kill 调度器后若 >30s 才换完文件，keepalive 可能先用旧文件拉起
  （新臂短暂仍是旧二进制，无数据损害，补一次换装即可）。要彻底避免：临时停 keepalive
  （守护动作，需运营者裁决）或采用下面的热插拔变体。
- **热插拔变体（不停调度器）**：直接 `mv` 换名——在跑臂继续用旧 inode 跑完，调度器新派臂
  自动用新二进制；零中断、不触发孤儿清理。代价：无明确切换时点，代际混合窗口更长。
- **孤儿清理**：停调度器→keepalive 重启前会杀 ppid==1 且 exe==对应 BIN 的孤儿 af-bench
  进程——在飞臂会中断（结果按 attempt 序号重跑、不覆写，可接受则按 §2 执行，否则用热插拔）。
- **双实例防线**：任何手工拉起前 `pgrep -f 'tools/factory-sched.py'` 确认存量；主/实验线
  按 §1 environ 区分，勿误停误起。
- **看板/watchdog**：换装后确认 `状态/看板/index.html`（8790）两条产线行恢复、watchdog
  无新红项（F2 行覆盖实验线）。
