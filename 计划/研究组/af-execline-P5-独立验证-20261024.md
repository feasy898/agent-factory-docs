# af-execline P5（订单生命周期接线 + TB 单元）独立验证报告

> 身份：独立验证者（与 P5 实现者无涉），2026-10-24。
> 对象：`/home/pan-ding/workspace/af-wt-phase2-execline/crates/af-execline/`
> （HEAD = `1830371`，分支 `phase2-execline-p5` 快进落地，工作树干净），验收面 =
> `FileRecordSink`/`allocate_attempt_dir`/`driver.execute` 接线/`TbEnv::verify`/
> `TbExecuteUnit`、`tests/{p5_wiring,p5_tb}.rs`、`RESULT-P5.md`。
> 纪律：只读 + 实跑；未改任何代码/文档（本报告除外）；未写
> `计划/变更日志.md`；未跑真容器、真模型（两条既有 `#[ignore]` 未执行）；
> 构建目录 `CARGO_TARGET_DIR=~/afbuild-phase2v`。开工 `df -h /`：22G 可用
> （96% 已用）→ 收尾 21G 可用（>15G 线）。

---

## 0. 结论

**PASS**（附 5 条不影响验收的 notes，见 §6）。

任务书必做检查 1–5 全部实跑/实查通过：95 passed / 0 failed / 2 ignored 基线
复现（P5 新增 12 例 = p5_wiring 4 + p5_tb 8，与 RESULT-P5 §2 声称一致）；
p5_wiring 全生命周期测试真驱动 af-engine 子进程（`EngineClient` 为具体类型、
`Command::new(&bin).spawn()` 进程协议，无桩可注）走完 8 op 入账，MES 四类恰
各一真实断言，同 order_id 二次 drive `replayed=true` 且单元不重跑、行不重落；
R8 不对称（swev 递增不覆写 vs TB `remove_dir_all`）由
`attempt_layout_asymmetry_regression_r8` 双向钉死，D-20 序号递增逻辑与
af-bench 原文逐行一致；TB 原样差异与 af-bench `run_tb` 原文完成 10 处对照
（`TB_SYSTEM_PROMPT` diff rc=0 逐字节一致，三行键集机械比对一致）；测试无
空断言/无 stub 残留；RESULT-P5.md 各条可实跑声明核对一致（clippy/fmt 实跑
复核通过；`cargo deny` 我未跑，见 §5）。

---

## 1. 实跑测试（任务书必做项 1）

### 1.1 验收命令原文

```
cd /home/pan-ding/workspace/af-wt-phase2-execline && CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline
```

exit 0。`test result` 行全量（第二次完整捕获；首次同命令 exit 0，仅 tail 截断
前面靶，故复跑一次取全量）：

```
     Running unittests src/lib.rs
test result: ok. 18 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
     Running tests/lifecycle.rs
test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s
     Running tests/p1_comparison.rs
test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
     Running tests/p1_suite.rs
test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
     Running tests/p2_bridge.rs
test result: ok. 12 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out; finished in 0.01s
     Running tests/p3_judge.rs
test result: ok. 4 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out; finished in 0.01s
     Running tests/p3_verify.rs
test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.05s
     Running tests/p4_unit.rs
test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s
     Running tests/p5_tb.rs
test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
     Running tests/p5_wiring.rs
test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s
   Doc-tests af_execline
test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```

**18+8+9+15+12+4+7+10+8+4 = 95 passed / 0 failed / 2 ignored**——P4 基线
83 + P5 新增 12 = 95，逐项复现。P5 两个靶的用例名（防张冠李戴）：

- p5_tb 8 例：`tb_row_key_sets_and_note_truncation` /
  `tb_task_load_failure_is_setup_failed_row` / `tb_setup_failure_row` /
  `tb_bash_tool_has_no_guards` / `tb_run_failure_row_and_container_cleanup` /
  `tb_full_flow_row_launch_shape_and_verify_chain` /
  `tb_verify_reward_zero_is_failure_not_infra` /
  `tb_verify_missing_reward_is_infra_row`。
- p5_wiring 4 例：`file_record_sink_append_flush_and_reopen_append` /
  `attempt_layout_asymmetry_regression_r8` /
  `full_lifecycle_with_swev_unit_ledger_mes_rows_and_trio` /
  `second_drive_replays_real_unit_without_rerun_or_duplicate_rows`。

2 个 ignored 均非 P5 新增（在册原位）：`p2_bridge.rs:392` 真 local docker 冒烟、
`p3_judge.rs:299` 真判分 fixture——与 RESULT-P5 §3-7 声明一致，我未执行
（禁跑真容器/真模型）。

真引擎证据：`~/afbuild-phase2v/debug/af-engine`（12,375,128 字节，构建于
Oct 24 15:29，先于本次验证）被 `EngineClient::locate` 直接采用（`bin.is_file()`
即用、不重建）。

---

## 2. 生命周期接线复核（任务书必做项 2）

### 2.1 真引擎子进程——不是进程内调用

- `EngineClient` 是具体类型（`engine.rs:132`），全仓无 trait 对象可注桩；
  `call()` 每次 op `Command::new(&self.bin).stdin/stdout/stderr piped().spawn()`
  （`engine.rs:188-195`），一行请求进 stdin、一行响应出 stdout、进程退出。
- `locate()`（`engine.rs:144-171`）缺失即 `cargo build -p af-engine`，构建失败
  EX1002、构建后仍缺 EX1001——都不静默跳过。
- p5_wiring 用 `engine_client()`（`p5_wiring.rs:58-61`）取真实客户端，并断言
  `driver.engine_bin().ends_with("af-engine")`（`p5_wiring.rs:314`）。

### 2.2 8 op 走完 + MES 四类各一（真实断言）

`full_lifecycle_with_swev_unit_ledger_mes_rows_and_trio`
（`p5_wiring.rs:293-405`）：

- `driver.drive(&unit)`（`driver.rs:362-381`）序列 =
  create_order → bind_line → attach_voucher → release → start → execute →
  complete → close；其中 create_order 为本地记账，其余 7 op + 单工件登记各经
  一次引擎子进程（`attach_artifacts` 逐工件 `client.call`，
  `driver.rs:426-456`）。
- ledger 断言（`p5_wiring.rs:316-340`）：序号 `1..=len` 连续；8 个 op 名逐个
  断言存在且 `ok`；`close` 成功记录唯一。
- MES 断言（`p5_wiring.rs:342-349`）：`kinds` 排序后恰等于
  `["close","complete","release","start"]`（四类恰各一，非"至少"）；所有事件
  `work_order_id == stable_id`。
- 落盘断言：`runs/swev-<task>-<profile>-a1` 目录在盘、三件套
  （eval.log/eval.sh/agent.diff）在其内；`results.jsonl` 恰一行 18 键，
  `run_dir` = 驱动层分配目录、`eval_sha256` 用独立 sha256 oracle
  （`p5_wiring.rs:77-82`，不借用被测实现）重算对账；`records.jsonl` 一行，
  `plan_id=order_id`/`node_id=line_id`/`verdict=true`。
- 零模型零凭证：`runner.launches() == 1`，判分走假 venv + 假 docker
  （PATH 首段注入，`p5_wiring.rs:119-141`），引擎不打桩。

### 2.3 二次 drive 幂等（replayed=true）

`second_drive_replays_real_unit_without_rerun_or_duplicate_rows`
（`p5_wiring.rs:409-477`）：首驱后 `drop(driver)`，同 order_id、同 out_dir 重开
驱动、**同一单元实例**再 drive。断言：`second.replayed == true`；终态仍
Closed；`runner.launches()` 仍 1（单元不重跑）；`docker run` 桥调用仍恰 1 次
（容器不重起）；`second.mes_events.is_empty()` 且 MES 文件仍 4 条；
`close` 成功记录唯一；`replay_skip` 审计行在账；序号仍连续；
`results.jsonl`/`records.jsonl` 仍各 1 行（行不重落）。

代码侧支撑：`execute` 重放路径（`driver.rs:267-277`）在 `done` 命中时直接
返回，**不触** attempt 分配与 `FileRecordSink::open`——"单元不重跑、行不重落"
有实现级保证，不止于测试观察。`replayed` 来自 `replay_hits > 0`
（`driver.rs:376`，`replay_skip` 自增，`driver.rs:419-422`）。

### 2.4 接线落位核对

- `driver.execute`：attempt 由 `allocate_attempt_dir` 分配
  （`driver.rs:285-290`），`FileRecordSink::open(&cfg.out_dir)` 传入 ctx
  （`driver.rs:291-304`）；sink 打开失败按单元失败入账（ok=false、幂等键不落、
  EX3001 上抛，`driver.rs:293-304`）。
- `PendingRecordSink` 已不在执行链：仅存于 `exec.rs:144`（其自身单测的
  StubExecuteUnit，不落行）与 `record.rs:45-55` 定义处；driver 只用
  `FileRecordSink`（`driver.rs:291`）。无 P4 占位残留。

---

## 3. R8 不对称与 D-20 证据链（任务书必做项 3）

### 3.1 回归测试钉死（双向）

`attempt_layout_asymmetry_regression_r8`（`p5_wiring.rs:484-517`）：

- swev 臂：预建 `swev-T-P-a1` + 哨兵文件 → 分配得 `swev-T-P-a2`，a1 哨兵
  原样（D-20 绝不覆写）；空根 → `a1`。
- TB 臂：预建 `tb-T-P` + 哨兵 → 分配仍得固定名 `tb-T-P`，哨兵消失、目录本体
  移除（`remove_dir_all`）。
- 双向防"顺手统一"：若把 swev 改成覆写，a1 哨兵断言红；若把 TB 改成递增，
  `assert_eq!(again, tb_dir)` 红。

### 3.2 实现与 af-bench 原文一致性

- `allocate_attempt_dir`（`driver.rs:87-108`）：SwevIncrement →
  `next_attempt_index` + join（`driver.rs:95-98`）；TbOverwrite → 固定名 +
  `let _ = remove_dir_all`（`driver.rs:102-106`，删除失败按 af-bench 原样
  `let _ =` 吞，建目录随后的失败仍会显形）。
- `next_attempt_index`：af-bench `main.rs:594-610` ↔ af-execline
  `suite/mod.rs:37-53`——前缀扫描取 max+1、只读目录不删，逐行一致（含注释
  590-593 ↔ 32-35）。
- TB 覆写层次：af-bench 在 `run_tb` 循环体（`main.rs:1000-1002`，=调用方/
  驱动层），单元只 `create_dir_all`（`main.rs:1002` 后半）；af-execline 同构
  （`tb_unit.rs:157-159` 只建目录）——偏差 §3-2 登记属实。
- D-20 证据链语义保真：`run_dir` 记实际目录、`eval_sha256` 判分时计算
  （`record.rs:187-189`）；run_failed 行也记实际目录（`record.rs:281`）；
  setup_failed 行字段齐备 null（`record.rs:256-258`）。

---

## 4. TB 原样差异对照（任务书必做项 4，≥4 处，列文件:行号）

| # | 差异点 | af-bench 原文 | af-execline 落位 | 核对方式 |
|---|---|---|---|---|
| 1 | `TB_SYSTEM_PROMPT` 逐字节 | `main.rs:975` | `suite/tb.rs:105` | `sed` 抽取两侧字面量 `diff` → **rc=0，各 440 字节一致** |
| 2 | verify 容器链九步命令串+超时 | `tb.rs:226-292`（清卷 120→提取 300→建验证器 1800→test.sh 1200→读 reward 30；卷名 `{task}-{container}`；infra 文案 `无 reward.txt；验证器输出:` tail 400） | `suite/tb.rs:266-332` | 逐串阅读比对一致；`p5_tb.rs:434-485` 对 9 次桥调用的脚本原文与超时逐个 `assert_eq!`/`contains` 钉死 |
| 3 | TB 12 键 legacy 行 | `main.rs:1068-1085` | `record.rs:312-331` | 机械抽取键集排序比对一致（suite/task_id/profile/trial/reward/status/http_retries/turns/model_calls/tokens{3}/agent_wall_ms/verifier_note） |
| 4 | TB setup_failed 7 键行 | `main.rs:938-946` | `record.rs:335-345` | 键集机械比对一致；`p5_tb.rs:562-575` 字段级 `json!` 全等 |
| 5 | TB run_failed 8 键行 | `main.rs:1037-1046` | `record.rs:348-365` | 键集机械比对一致；`p5_tb.rs:641-655` 字段级 `json!` 全等（含 `http_retries=4`） |
| 6 | 无采样覆写 | `main.rs:627-632` 注释"只作用于 swe-v 线；TB/竞赛套件不动"+ `main.rs:972` `prof.endpoint.clone()` 原样 | `tb_unit.rs:253-277`（endpoint 克隆即用，无 temperature/top_p/max_tokens 赋值） | `p5_tb.rs:409-416` 断言三者皆 `None`（锚 = `profile.rs:59-71` glm-cp 基底实为 None，非空洞断言） |
| 7 | user_message 裸 prompt | `main.rs:1015` `task.prompt.clone()` | `tb_unit.rs:166` | `p5_tb.rs:402-405` 断言 == `INSTRUCTION`（对照 swev 线 `main.rs:775` 的 instance 模板拼接） |
| 8 | run_id 无 `-a<N>` 后缀 | `main.rs:1013` `task.task_id.clone()` | `tb_unit.rs:164` | `p5_tb.rs:401` 断言 == `TB_TASK`（对照 swev `main.rs:778` 带后缀） |
| 9 | 40 步 / TASK_COMPLETE / 无工具 3 轮 / $1（100/1/100） | `main.rs:981/983-984/1021-1027` | `tb_unit.rs:74-79`（fix2 缺省） | `p5_tb.rs:417-426` 五个数值断言 |
| 10 | bash 工具无护栏 | `main.rs:963-970`（注册处即 `env_for_tool.exec` 直穿；反考古/重复拦截在 swev `main.rs:710-734`） | `tb_unit.rs:281-284`（闭包直穿 `env.exec`） | `p5_tb.rs:681-715` 反向断言：`git fsck --lost-found` 不注入 `[harness]`、同命令第 3 次无 `exact command` 教学包装 |

附带一致项：note 截断 `.chars().take(300)`（`main.rs:945/1045/1084` ↔
`record.rs:27-29` `clip300`，`p5_tb.rs:719-756` 断言 400→300）；
`bash_tool_decl`/`load_tb_tasks`/护栏常量 2g·256 为 P1 已搬（p1_comparison
活源对拍在册，本次复跑全绿）。

---

## 5. 测试质量扫描 + RESULT-P5 声明核对 + clippy/fmt（任务书必做项 5）

### 5.1 测试质量扫描

- 无空断言/无桩残留：`grep "assert!(true\|todo!\|unimplemented!\|dbg!"` 命中
  仅两处文件头 doc 注释（描述 RED 期 `unimplemented!()` 历史），源码零残留。
- 断言强度：TB 三行均字段级 `json!` 全等（非逐字段 contains）；verify 链
  9 次调用脚本原文 + 超时逐个钉死；`eval_sha256` 独立 oracle 重算。
- 确定性：FixedClock；临时目录按 `process::id()` 隔离；PATH 篡改由
  `SPAWN_GUARD` 互斥锁串行并还原（`p5_wiring.rs:37-41,119-141`）。
- 负向覆盖：setup 失败、任务装载失败、runner 失败、infra（无 reward.txt）、
  reward=0 真失败、bash 无护栏——happy/failure 均衡，无"只跑 happy"。
- 可变异抗性：R8 测试双向防统一（§3.1）；`tb_bash_tool_has_no_guards` 对
  "顺手补齐护栏"反向红灯。
- notes（不影响验收）：① p5_tb 直调 `unit.execute`（手搭 ctx），未经驱动
  层全流程 drive TB 单题——驱动层 TB 路径仅由 R8 布局测试覆盖
  （与方案草案 TB 断言面一致，RESULT-P5 §2 亦如此声称）；②
  `full_lifecycle` 未直接计数引擎子进程 spawn 次数，以"终态 Closed 必经
  引擎放行 + engine_bin 路径 + 8 op 全 ok"间接证明（`EngineClient` 无桩可注，
  间接证明在此约束下是强证据）；③ 全生命周期测试对 `results.jsonl` 断言前
  `remove("agent_wall_ms")` 后仅 `< 60_000` 宽松界——合理（墙钟不可精确）。

### 5.2 clippy / fmt（实跑）

```
CARGO_TARGET_DIR=~/afbuild-phase2v cargo clippy -p af-execline --all-targets   # exit 0
cargo fmt --check --all                                                          # exit 0（零 diff）
```

clippy 尾输出仅：`warning: the following packages contain code that will be
rejected by a future version of Rust: proc-macro-error2 v2.0.1`——第三方依赖
future-incompat，RESULT-P1 §3-5 已登记，非 P5 新增；af-execline 自身 0 警告。

### 5.3 RESULT-P5.md 声明核对

| 声明 | 核对结果 |
|---|---|
| §2 全套 95 passed / 0 failed / 2 ignored；P5 新增 12 例（4+8） | **一致**（本次实跑逐靶复现） |
| §3-7 无新增 `#[ignore]`；P2 docker 冒烟/P3 判分 fixture 原样在册 | **一致**（两处 `#[ignore]` 均在 p2/p3，非 P5 文件） |
| §4 只读约束 `git diff a88c316..1830371 --stat -- crates/af-bench crates/af-workorder crates/af-engine` 输出 0 字节 | **一致**（实测 0 字节；af-bench 最后触碰 = `725fceb` 护栏提交，早于 P5） |
| §4 git 序列 RED→GREEN→重构→补强→docs | **一致**：`0278c5d`(RED)→`11f78b2`(GREEN)→`c4dfcdf`(重构)→`9e20daa`(补强)→`1830371`(docs) |
| §3-1 DriverConfig 增 `profile`/`attempt_layout` | **属实**（`driver.rs:65-67`） |
| §3-2 TB 覆写在驱动层、单元只建目录 | **属实**（`driver.rs:102-106` ↔ `tb_unit.rs:157-159`） |
| §3-3 TB 无 v1 投影（`record: None`） | **属实**（`tb_unit.rs:237`；`p5_tb.rs:387` 断言 v1 行空） |
| §3-4 TB evidence/outputs 空 | **属实**（`tb_unit.rs:233-238`） |
| §3-5 infra（reward=None）不是 Err | **属实**（`tb_unit.rs:224-239`；`tb_verify_missing_reward_is_infra_row`） |
| §3-8 TB bash 无护栏原样保留 | **属实**（`tb_unit.rs:281-284` + 第 8 例反向断言） |
| §3-10 clippy 零新增 | **一致**（实跑 exit 0，仅第三方提示） |

未能由我复核的声明（如实登记）：RESULT-P5 §4 的 `cargo deny --offline check`
四类 ok——本次任务书未列此项，我未跑；§1"迁移源与主仓 af 逐字节一致"——
本机 `/home/pan-ding/workspace/` 下无主仓 `af`（仅各 `af-wt-*` 工作树），
无法对拍；可佐证的是本工作树 af-bench 自 `725fceb` 后零改动（§上表）。

---

## 6. 遗留 notes（不影响验收结论）

1. p5_tb 未经驱动层全流程 drive（单元直调），TB 的驱动级接线只有 R8 布局
   测试覆盖——若 P6 对拍需要"TB 单题经订单驱动"的证据，属新增测试面。
2. `full_lifecycle` 对引擎子进程为间接证明（无 spawn 计数）；在
   `EngineClient` 不可注桩的约束下结论仍强。
3. `cargo deny` 未由我实跑（任务书未列）。
4. 主仓 `af` 对拍无法在本环境执行（无该目录）。
5. 磁盘 96% 已用（21G 可用）——后续任务包注意构建盘余量。

---

## 7. 复核命令索引（本次实跑）

```
cd /home/pan-ding/workspace/af-wt-phase2-execline && CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline        # exit 0，95/0/2
cd /home/pan-ding/workspace/af-wt-phase2-execline && CARGO_TARGET_DIR=~/afbuild-phase2v cargo clippy -p af-execline --all-targets  # exit 0
cd /home/pan-ding/workspace/af-wt-phase2-execline && cargo fmt --check --all                                            # exit 0
cd /home/pan-ding/workspace/af-wt-phase2-execline && git log --oneline -3                                               # HEAD=1830371
cd /home/pan-ding/workspace/af-wt-phase2-execline && git diff a88c316..1830371 --stat -- crates/af-bench crates/af-workorder crates/af-engine | wc -c   # 0
sed -n '975p' crates/af-bench/src/main.rs ... | diff - <(sed -n '105p' crates/af-execline/src/suite/tb.rs ...)          # rc=0，440B=440B
```

（全文完——独立验证者，2026-10-24）
