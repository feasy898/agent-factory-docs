# af-execline P4（SwevExecuteUnit）独立验证报告

> 身份：独立验证者（与 P4 实现者无涉），2026-10-24。
> 对象：`/home/pan-ding/workspace/af-wt-phase2-execline/`（HEAD = `a88c316`，
> 分支 `phase2-execline`，工作树干净），验收面 = `crates/af-execline/`
> （重点 `src/agent.rs`、`src/suite/swev_unit.rs`、`tests/p4_unit.rs`、
> `RESULT-P4.md`）。
> 纪律：只读 + 实跑；未改任何代码/文档（本报告除外）；未写
> `计划/变更日志.md`；未跑真容器、真模型（p2_bridge 的 `#[ignore]` 真 local
> docker 冒烟因此**未执行**）；构建目录 `CARGO_TARGET_DIR=~/afbuild-phase2v`。
> 开工 `df -h /`：26G 可用（95% 已用）→ 收尾 26G 可用。

---

## 0. 结论

**PASS**（附 5 条不影响验收的 notes，见 §6）。

任务书必做检查 1–5 全部实跑/实查通过：83 通过基线复现（0 failed / 2 ignored）；
FakeRunner 缝与 HostBridge 缝正交且各自可替换；全流程链路真驱动（仅叶端执行器
造假）；v1 行与 `af.plan.record.v1` 契约 status/verdict 两轴对齐；无空断言、
负向路径占比 5/14 严格失败路径（10/14 含非 happy 态与护栏负路径）；两条
`#[ignore]` 在册且均非 P4 新增；RESULT-P4.md 各条声明核对一致（clippy/fmt
实跑复核通过）。

---

## 1. 实跑测试（任务书必做项 1）

### 1.1 验收命令原文

```
cd /home/pan-ding/workspace/af-wt-phase2-execline && CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline
```

`test result` 行全量（exit 0）：

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
   Doc-tests af_execline
test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```

**18+8+9+15+12+4+7+10 = 83 passed / 0 failed / 2 ignored**——RESULT-P4.md §4
声称的 83 通过基线逐项复现（P4 新增 = lib 内 4 例 + p4_unit 10 例 = 14 例，
与 P3 收尾 69 例的差值 14 吻合）。

### 1.2 两条 `#[ignore]` 的实跑处置

- `p2_bridge::smoke_real_local_docker_via_bridge`（真 local docker 冒烟）：
  **未执行**——任务书明令禁止跑真容器。
- `p3_judge::real_judge_fixture_trio_resolved`（真 venv + 现产判分脚本，不涉
  容器/模型/网络）：已实跑，`ok`（2.11s）——在册状态实证非摆设：

```
cd /home/pan-ding/workspace/af-wt-phase2-execline && CARGO_TARGET_DIR=~/afbuild-phase2v \
  cargo test -p af-execline --test p3_judge -- --ignored --exact real_judge_fixture_trio_resolved
test real_judge_fixture_trio_resolved ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4 filtered out; finished in 2.11s
```

---

## 2. FakeRunner 注入缝复核（任务书必做项 2）

### 2.1 模型调用确已隔离在 AgentRunner trait 之后

- trait 面：`src/agent.rs:72-74`——`fn run(&self, launch: AgentLaunch<'_>) ->
  Result<AgentRunOutcome, AgentRunFailure>`，单入口。
- `SwevExecuteUnit` 对模型侧的唯一触碰点是 `swev_unit.rs:199` 的
  `self.runner.run(launch)`；该文件从 af-harness 只 import **规格类型**
  （`AgentSpec/BudgetRef/BudgetUnit/ContextTemplate/Policy/StopCondition/
  ToolDecl`，swev_unit.rs:30-32），无 `Opened`/`Launch`/执行 API——单元内
  不存在第二条模型调用路径。
- 真实现 `HarnessRunner`（agent.rs:84/105）持全部 af-harness 执行材料
  （issue_root 逐题签发、bash 注册胶水、key 紧邻现取 + 401 重取器、
  `Opened::open` + `opened.run(Launch)`、http_retries 双路径累计），与
  FakeRunner 同为 `impl AgentRunner`——**替换点就是 trait 本身**，测试注入
  `FakeRunner`（p4_unit.rs:299-341）返回固定 `RunReport`/结构化失败即证。
- 缝的持有形态为 `Arc<dyn AgentRunner>`（swev_unit.rs:111）而非 `&dyn`：
  af-harness ToolRegistry 钉死 `'static + Send + Sync`（agent.rs:8-11 文档 +
  RESULT-P4.md §3-1 登记）——偏差已如实登记，缝的可注入性不变。

### 2.2 容器编排仍在 HostBridge 之后，两缝正交

- 单元经 `self.bridge`（`Arc<dyn HostBridge + Send + Sync>`，
  swev_unit.rs:110）驱动全部容器面：`swev::setup`（docker rm -f 前置 +
  docker run，swev_unit.rs:165-171）、`capture_diff`（swev_unit.rs:227）、
  bash 工具体（swev_unit.rs:387-395）、cleanup（ContainerGuard Drop →
  docker rm -f，swev_unit.rs:449-460）。
- 正交性实证（p4_unit.rs 全流程用例）：同一用例内 `FakeRunner` 与
  `FakeBridge` 分别独立断言——`assert_launch_shape`（经 runner 捕获，19 项）
  与 `assert_bridge_sequence`（经 bridge 留痕，5 次调用逐串）互不依赖；
  `unit_load_fingerprint_gate_fail_loud` 更分别断言"桥零调用"与"runner 零
  调用"（p4_unit.rs:907-908）——任一缝的替换不影响另一缝的行为面。
- **一处缝覆盖缺口（非 P4 引入，如实记）**：verify 的 eval 执行
  （`docker exec -i … bash -s`，stdin 喂 eval.sh）**不经 bridge.run**——
  swev.rs:244-248 明言 HostBridge 三参面表达不了 stdin 文件管道与外层
  stderr 丢弃，直造 `Command::new("bash"/"ssh")`（swev.rs:250-273），与
  af-bench swev.rs:166-186 逐字一致，登记在 RESULT-P3.md §3-2。P4 测试因此
  辅以 PATH 首段假 docker（p4_unit.rs:124-146）驱动该真子进程链。此路径仍
  是"真 bash 子进程 + 假 docker 叶端"，非 mock 到底。

---

## 3. 全流程语义（任务书必做项 3）

### 3.1 链路真驱动，非 mock 到底

`full_flow_trio_rows_and_launch_shape`（p4_unit.rs:651-675）驱动的是
`SwevExecuteUnit::execute` 真实分相机（swev_unit.rs:148-298）：
setup（任务装载=真文件 IO + 容器=fake bridge）→ run（FakeRunner）→ gate
（capture_diff 经 fake bridge）→ verify（**真子进程链**：指纹门 → 取证 →
eval.sh 落盘 → 本机 bash 拉 PATH 首段假 docker 吃 stdin 出日志 →
sha256 真算 → 假 python 判分器**真 `Command` 拉起**回 JSON → note 拼装/
resolved 解读全走 swev.rs:294-330 真代码）→ 双轨行落盘 → cleanup（RAII）。
造假仅限叶端执行器（docker 二进制品、模型端点、判分 venv 回包），阶段机、
行装配、sha256、judge JSON 解读、note 前缀逻辑均为真代码执行。

### 3.2 结果行与 `af.plan.record.v1` 契约两轴对齐

契约定义（`计划/研究组/落地契约-v0.md:59-73`）与实现对照：

| 契约字段 | 契约口径 | 实现 | 对齐证据 |
|---|---|---|---|
| `status` | `completed｜max_turns｜tool_free_limit｜budget_exhausted｜stopped｜unauthorized｜setup_failed｜run_failed`（契约:65） | 六态 ← `suite::status_label`（suite/mod.rs:20-29，逐字对照 main.rs:579-588）+ 失败行 setup_failed/run_failed（record.rs:160/176） | **枚举全覆盖**；legacy 18 键 status 实测 "completed"（p4_unit.rs:516）、v1 status 同源 |
| `verdict` | `true｜false｜null`，null=无判定（契约:66） | `verdict ← reward: Option<bool>`（record.rs:138）；`None → null` | p4_unit.rs:542 实测 `verdict: true`；`failure_rows_key_sets_and_note_truncation` 实测 `reward None → verdict null`（p4_unit.rs:1000/1007） |
| 其余 12 键 | plan_id/node_id/item_id/attempt/host_alias/unit_id/unit_version/evidence{run_dir,evidence_digest}/gate/usage{turns,unit_calls,http_retries,quota}/wall_ms/note | record.rs:121-157，14 键 | p4_unit.rs:528-555 字段级全等断言（14 键齐备） |

另：两轨同源由 `ExecutionFacts` 单源装配（record.rs:85/121），
`agent_wall_ms == wall_ms` 有断言（p4_unit.rs:530）；`ExecOutput.record`
与 v1 行同源有断言（p4_unit.rs:565-567）；gate 三值（ok/no_patch/test_edit）
对应契约"ok｜policy_violation_kind"泛化口径。**两轴对齐成立**。

---

## 4. 测试质量（任务书必做项 4）

### 4.1 空断言扫描

```
grep -rn "assert!(true)\|assert_eq!(1, 1)\|assert!(1 == 1)" tests/ src/
```

**零命中**（exit 1）。p4_unit.rs 120 处 assert/expect/panic 分布到 10 个
测试（最少 3 处/测试，happy path 主用例经 helper 分摊后含 60+ 字段级断言）；
无"只 unwrap 不断言"的空转测试；`FakeBridge` 遇未预期命令直接
`panic!`（p4_unit.rs:214），回放集闭合。

### 4.2 P4 新增 14 测试的负向路径占比

| 类别 | 测试 | 计数 |
|---|---|---|
| 严格失败路径（Err/拒跑/门） | runner_failure_row_and_container_cleanup、setup_failure_row_with_nulls、unit_load_fingerprint_gate_fail_loud、sink_write_failure_fails_loud、pending_driver_sink_fails_loud | **5/14（36%）** |
| 非 happy 完成态分支 + 失败行字段 | gate_no_patch_on_empty_diff、gate_test_edit_on_test_file_diff、failure_rows_key_sets_and_note_truncation | 3/14 |
| 工具面护栏负路径（经 failing runner 驱动） | bash_tool_guards_archaeology_and_repeats、bash_guard_wrap_semantics、bash_guard_window_slides_after_six | 3/14 |
| 纯函数边界/回退 | attempt_from_dir_follows_next_attempt_naming（非约定命名回退 1）、gate_of_three_branches（含 no_patch 臂） | 2/14 |
| happy path | full_flow_trio_rows_and_launch_shape | 1/14 |

严格失败路径 5/14；含非 happy 态与护栏负路径合计 **10/14（71%）**；唯一
happy path 用例同时断言 19 项 launch 形状 + 5 次桥调用序列 + 三件套字节 +
18/14 键行，深度充分。负向覆盖与 §5 的失败路径语义（run_failed 11 键/
setup_failed 9 键/EX3001/EX3002/cleanup 必达）一一对应，无空转负向。

### 4.3 `#[ignore]` 在册状态

全 crate 共 2 例，**均非 P4 新增**（P4 前已存在；RESULT-P4.md §3-12 如实
声明"无新增 #[ignore] 冒烟"）：

| 测试 | 在册形式 | 实跑处置 |
|---|---|---|
| `p2_bridge::smoke_real_local_docker_via_bridge` | `#[ignore = "真 local docker 冒烟：需本机 docker 守护进程（cargo test -- --ignored 运行）"]`（p2_bridge.rs:392）+ 模块头在册说明（:19）+ 缺席时打印说明跳过不假绿（:390） | 未跑（任务书禁真容器） |
| `p3_judge::real_judge_fixture_trio_resolved` | `#[ignore = "真判分 fixture：需本机 swev-venv 与现产 swev-judge.py（-- --ignored 运行）"]`（p3_judge.rs:299）+ 运行命令文档（:297）+ 缺席显式跳过（:302-303） | 已跑，ok（§1.2） |

---

## 5. RESULT-P4.md 声明核对（任务书必做项 5）

| 声明（RESULT-P4.md） | 独立复核 | 结果 |
|---|---|---|
| §4：83 passed / 0 failed / 2 ignored，各二进制分布 | §1.1 实跑复现，逐项相符 | ✅ |
| §4：RED 时 p4_unit 9 红/1 过（b8c4e44） | 结构复核：`git show b8c4e44:…` 中 agent.rs:89、swev_unit.rs:124/135/145、record.rs:81/97/103/116 共 8 处 `unimplemented!()` 桩；RED 版 p4_unit.rs 恰 10 个 `#[test]`；`PendingRecordSink` 在 RED 即为真代码（`git show b8c4e44:…record.rs`）→ pending_driver_sink 先绿，余 9 红。**RED 态未实跑**（需另建工作树，越权），按结构证据判一致 | ✅（结构一致，未实跑） |
| §4：git 序列 b8c4e44→941c40c→6df0f6b→a88c316 | `git log --oneline 4cba6cb..HEAD` 实测四连，红→绿→重构成立；941c40c 两文件零 `unimplemented!` | ✅ |
| §4：af-bench/af-workorder/af-engine 零改动 | `git diff 4cba6cb..HEAD --stat -- crates/af-bench crates/af-workorder crates/af-engine` 输出为空；`git log 4cba6cb..HEAD -- crates/af-bench` 亦空 | ✅ |
| §4/§1：af-bench 三文件与主仓逐字节一致（开工+收尾双次 diff） | 本次实跑一次：`diff` 主仓 `af/crates/af-bench/src/{swev,tb,main}.rs` vs 工作树，三文件均 IDENTICAL；且 `diff -r` 整个 src 目录 IDENTICAL。辅证：主仓 HEAD `94cd192` 是工作树 HEAD 的祖先（merge-base 实测），af-bench 自 fork 后零提交——字节一致有 git 对象级保证。"双次"为过程声明，我复测一次 | ✅（一次实跑 + git 辅证） |
| §4：clippy exit 0、af-execline 自身 0 警告 | 实跑 `CARGO_TARGET_DIR=~/afbuild-phase2v cargo clippy -p af-execline --all-targets`：exit 0，仅第三方 `proc-macro-error2 v2.0.1` future-incompat 提示（P1 已登记） | ✅ |
| §4：`cargo fmt --check --all` PASS | 实跑 exit 0、零 diff | ✅ |
| §3-1~13 偏差登记 | 抽查全部对得上：Arc 缝（agent.rs:8-11/swev_unit.rs:110-111）、AgentRunFailure 结构化（agent.rs:65-68）、ctx.task_id 补充字段（exec.rs:31）、失败行只落 legacy（swev_unit.rs:313-321 + 测试断言 v1_rows 空）、attempt_from_dir 回退（swev_unit.rs:438-445）、issue_root 逐题签发（agent.rs:106-114）、capture_diff 两次（测试断言桥 5 次调用）、run_failed scaffold 硬编码 v3（record.rs:191）、无新增 #[ignore]（§4.3）、clippy 零新增 | ✅ |
| 头：工作树 `af-wt-phase2-p2`（分支 phase2-execline-p4） | 实际交付工作树为 `af-wt-phase2-execline`（分支 `phase2-execline`）；`af-wt-phase2-p2` 已被 P5 接管（分支 phase2-execline-p5，同停 a88c316）。文档与最终落位名有漂移 | ⚠️ note |

---

## 6. Notes（不影响验收）

1. **工作树命名漂移**（§5 末行）：RESULT-P4.md 头自称 `af-wt-phase2-p2/
   phase2-execline-p4`，实际 HEAD `a88c316` 落在 `af-wt-phase2-execline/
   phase2-execline`；`af-wt-phase2-p2` 已切到 P5 分支（同 commit）。内容
   无影响，交付事实以 git 对象为准。
2. **verify eval 执行不经 HostBridge**（§2.2 末）：P3 已登记偏差
   （RESULT-P3.md §3-2，stdin 管道桥面表达不了），P4 原样继承并用 PATH 假
   docker 驱动。缝覆盖面对"容器编排全经桥"的表述需带此例外阅读。
3. **RED 态 9 红/1 过为结构复核**（§5 第 2 行）：未实跑 RED 提交（跑它需
   另建工作树，越权）；以桩点存在性 + RED 测试集 + PendingRecordSink 先真
   三项证据判一致。
4. **"双次 diff"复测一次**：本次只做了一次 diff（IDENTICAL）；fork 后
   af-bench 零提交（git 实证）使两次 diff 的结论必然相同，"双次"本身无法
   事后区分，按一次实跑 + git 辅证采信。
5. **`attempt` 恒 1 假设**：`attempt_from_dir` 非约定命名回退 1
   （swev_unit.rs:438-445，RESULT-P4 §3-7），驱动层真实 attempt 分配在 P5；
   当前测试面只覆盖到 a1 与回退，a2+ 场景留待 P5 接线后。

---

## 7. 命令索引（本次实跑）

| # | 命令 | 结果 |
|---|---|---|
| 1 | `df -h /`（开工/收尾） | 26G → 26G 可用 |
| 2 | `cd /home/pan-ding/workspace/af-wt-phase2-execline && CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline` | exit 0，83 passed / 0 failed / 2 ignored |
| 3 | 同上（第二次，抓全量 result 行） | 同上 |
| 4 | `… cargo test -p af-execline --test p3_judge -- --ignored --exact real_judge_fixture_trio_resolved` | 1 passed |
| 5 | `… cargo clippy -p af-execline --all-targets` | exit 0，仅第三方 future-incompat |
| 6 | `… cargo fmt --check --all` | exit 0，零 diff |
| 7 | `diff` 主仓 vs 工作树 af-bench src（三文件 + 整目录） | 均 IDENTICAL |
| 8 | `git diff 4cba6cb..HEAD --stat -- crates/af-bench crates/af-workorder crates/af-engine` | 空 |
| 9 | `git log --oneline 4cba6cb..HEAD` / `git worktree list` / `git merge-base HEAD guardrail-fix2` | 四连序列；主仓 HEAD 为祖先 |
| 10 | `git show b8c4e44:…`（agent/swev_unit/record 桩点 + p4_unit 测试集 + PendingRecordSink） | 桩与"9 红/1 过"结构一致 |

未执行（越权/禁止）：修改任何代码或文档（本报告除外）；写
`计划/变更日志.md`；跑 p2_bridge 真 docker 冒烟；跑真模型；跑 workspace
全量测试；另建工作树复跑 RED 提交。
