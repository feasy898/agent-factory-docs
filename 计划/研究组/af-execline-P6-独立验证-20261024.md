# af-execline P6 独立验证报告（薄壳化 + L0/L1 对拍）

> 身份：独立验证者（与 P6 实现者无涉），2026-10-24。只读代码 + 实跑测试，未修改任何
> 代码或文档（本报告除外）。对象工作树 `/home/pan-ding/workspace/af-wt-phase2-p2`，
> 分支 `phase2-execline-p6` @ `5373a55`（基于 P5 完成点 `1830371`）。
> 构建目录：`CARGO_TARGET_DIR=~/afbuild-phase2v`（任务书指定；实现者自评用
> `~/afbuild-phase2b`，两者相互独立）。资源纪律：开工 `df -h /` 20G 可用 → 收尾
> 18G 可用（96%→97%，始终高于 RESULT-P6 自记的 >15G 线）；未跑真容器/真模型/网络；
> 未碰工厂守护进程与 AB 测试线；未写 `计划/变更日志.md`。

## 结论：PASS-with-notes

五项必做检查全部实跑通过（含三项 `#[ignore]` 真跑项中的两项——L0 判分回放与 L1 真判分
链；L2 金丝雀按编排者裁定不在本包执行，仅核钩子在册）。发现 4 条 notes，均不构成对
验收判据的违背，详见 §6。

| # | 必做检查 | 结果 |
|---|---|---|
| 1 | 实跑 `cargo test -p af-execline` / `-p af-bench` | **PASS**（103/0/5 与 3/0，逐二进制计数与 RESULT-P6 §4 全对） |
| 2 | 薄壳化字节契约（六条拒绝路径 + 18 键行模板） | **PASS**（6/6 与 git 历史旧版逐字一致；D7 全等测试真实，见 note-2） |
| 3 | L0 对拍（抽 1 份证据两路重放） | **PASS**（4/4 逐位一致；手动单证据重放亦一致） |
| 4 | L1 对拍（双变体真驱动 + 十维/六维清单） | **PASS**（判分随日志翻转的非旁路证明成立） |
| 5 | 零改动 / sha256 钉死 / RESULT-P6 逐条 / clippy·fmt | **PASS**（af-workorder、af-engine 零字节改动；clippy 0 警告；fmt 零 diff） |

---

## 1. 测试实跑（任务书原文命令）

### 1.1 af-execline

```
cd /home/pan-ding/workspace/af-wt-phase2-p2 && CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline
```

exit 0。逐二进制计数（摘自我实跑的完整日志）：

| 二进制 | passed | failed | ignored |
|---|---|---|---|
| lib (unittests src/lib.rs) | 18 | 0 | 0 |
| lifecycle | 8 | 0 | 0 |
| p1_comparison | 9 | 0 | 0 |
| p1_suite | 15 | 0 | 0 |
| p2_bridge | 12 | 0 | 1 |
| p3_judge | 4 | 0 | 1 |
| p3_verify | 7 | 0 | 0 |
| p4_unit | 10 | 0 | 0 |
| p5_tb | 8 | 0 | 0 |
| p5_wiring | 4 | 0 | 0 |
| p6_shadow | 8 | 0 | 3 |
| doc-tests | 0 | 0 | 0 |
| **合计** | **103** | **0** | **5** |

与任务书要求（103/0/5）及 RESULT-P6 §4 验证记录逐项一致。p6_shadow 二进制实际
`running 11 tests`（8 passed + 3 ignored）：第 11 例 `tb::tests::container_guardrail_
constants_match_calibration` 来自 `#[path]` 编译进来的冻结 `tb.rs` 模块内的 P5 测试，
随单元计入，账面对齐（见 note-4）。

### 1.2 af-bench

```
CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-bench
```

exit 0：**3 passed / 0 failed / 0 ignored**——

```
test tests::args_parse_full_set_and_defaults ... ok
test tests::args_parse_rejects_unknown_and_malformed ... ok
test tests::next_attempt_index_counts_existing_dirs_only ... ok
```

与任务书要求（3/0）及 RESULT-P6 §4 一致（D-20 等价迁移 1 + 参数面回归 2）。

---

## 2. 薄壳化字节契约复核

### 2.1 六条拒绝路径与旧版逐字对照（旧版 = git 历史 `1830371:crates/af-bench/src/main.rs`）

**(a) 源码级对照。** `git show 1830371:crates/af-bench/src/main.rs` 取旧版（1255 行），
与新壳 `crates/af-bench/src/main.rs`（843 行，RESULT-P6 声明 1255→843，实测相符）比对：

- **parse 函数体**：`diff <(sed -n '92,152p' 旧) <(sed -n '214,274p' 新)` —— 除两处
  文档化抽入口外逐字节一致：
  1. `fn parse()` → `fn parse_from<I: IntoIterator<Item = String>>(it: I)`（main.rs:214，
     注释明示"仅从 `parse()` 抽出可测入口，行为零变化"）；
  2. `let mut it = std::env::args().skip(1);` → `let mut it = it.into_iter();`。
- **未知档案**：旧 main.rs:163-327 的 `profile()` 函数体与 af-execline `src/profile.rs:27-190`
  逐字节一致（`diff` 唯一差异 = `fn profile` → `pub fn profile` 可见性）。

**(b) 二进制级对照（最强证据）。** 新壳构建后与冻结旧二进制双跑六条拒绝路径，
逐字节比对 stdout/stderr 与退出码：

| # | 输入 | 新壳输出 | 与旧版 |
|---|---|---|---|
| 1 | `--suite swe-v --bogus` | `af-bench failed: 未知参数 --bogus` | 逐字一致（rc=1） |
| 2 | `--suite` | `af-bench failed: --suite 缺值` | 逐字一致（rc=1） |
| 3 | `--data-root /d --profile p` | `af-bench failed: 缺 --suite` | 逐字一致（rc=1） |
| 4 | `--suite swe-v --data-root /d --profile p --limit abc` | `af-bench failed: --limit 不是整数` | 逐字一致（rc=1） |
| 5 | `--suite bogus --data-root /d --profile p` | `af-bench failed: 未知套件 bogus（可选 injecagent / terminal-bench / swe-v）` | 与 **git 历史旧版**逐字一致；与冻结旧二进制差一词（见 note-1） |
| 6 | `--suite swe-v --data-root /d --profile nope --tasks t` | `af-bench failed: 未知档案 nope（可选 mavis-m31f / …）` | 逐字一致（rc=1） |

六条路径在源码层的落点：新壳 main.rs:260（未知参数）/ :228（缺值）/ :264（缺必填）/
:239（坏整数）/ :502（未知套件）/ profile.rs:188（未知档案）；旧版对应 main.rs:138 /
:106 / :142 / :117 / :620 / :324。任务书判据是"与旧版逐字对照（从 git 历史取旧
main.rs）"——按此判据 **6/6 一致**。

### 2.2 18 键 results 行与冻结模板全等性测试的真实性

- 冻结模板在册：`tests/fixtures/p6-frozen-bench/main.rs:861-889` 的 `json!({...})` 为
  18 键（suite/task_id/profile/trial/reward/status/scaffold/reasoning_tier/run_dir/
  eval_sha256/gate/attempts/http_retries/turns/model_calls/tokens/agent_wall_ms/
  verifier_note），与测试 oracle `old_template_row`（p6_shadow.rs:277-311）逐键同序；
  模板片段的在册性由 `cmp_p6_row_template_in_frozen_source`（p6_shadow.rs:379-395，
  9 个 needle）钉死。
- D7 判等（p6_shadow.rs:521-557）**不是字符串拼接陷阱**：oracle 是独立构建的
  `json!({...})` Value；断言为 ①`assert_eq!(row_new.as_object().unwrap().len(), 18)` 键数；
  ②`assert_eq!(row_new, oracle)` **Value 结构全等**；③`assert_eq!(serde_json::to_string(&row_new),
  serde_json::to_string(&oracle))` **序列化字节全等**。三层判据均作用在解析后的 JSON
  值与序列化字节上，与拼接字符串无关。
- **note-2（唯一保留）**：`agent_wall_ms` 一字段的判等在构造上空转——oracle 的 wall 值
  取自行本身（p6_shadow.rs:523-528、536、541-548），断言 `Some(agent_wall)==Some(agent_wall)`
  恒真。该豁免在注释中明确披露（"wall 属计时豁免面"），且与 `shadow.rs:210-216`
  `METERING_ROW_FIELDS`（含 agent_wall_ms）口径一致——属如实登记的计量豁免，非隐藏
  陷阱；其余 17 键为真实判死。
- 冻结件 provenance：三文件 sha256 我独立复算，与 p6_shadow.rs:328-341 钉死值、
  与 `git show 1830371:<file>` 的 blob 三方一致：

```
b857383abdc4e3dfc0262c90ebb9c124ea3a44cb2b069f9175472f2f245981ad  main.rs
f013dd4fee4db48f8410e5f3185baf00a6df62a6f7fe76ddf0963a201754295d  swev.rs
58664cc914e5cd542df43f7f7c3f5bf00b67d527b28e0124e4c9cb0da5962828  tb.rs
```

- 佐证"壳内零行装配"：新壳 `"suite"` 字面装配仅 main.rs:798（injec 一处）；swe-v/TB
  行由 `record.rs:173-207`（18 键）/:312（TB 12 键）/:248、:264、:335、:348（9/11/7/8 键
  失败行）装配，与 RESULT-P6"18/12/9/7/11/8 键全部由 record.rs 装配"相符。

---

## 3. L0 对拍复核（抽 1 份证据，两路判分各重放一次）

**证据选取与对账。** 取 `工具状态备份/shadow-20261024/l0-replay-summary.jsonl` 证据
**a1**（astropy__astropy-12907，eval_sha256 `2c972ea106bc…`，agent_diff_sha256
`2d0b8307d9d191a0…`）。在盘定位：`工具状态备份/observability/bench-obs4-out/runs/
swev-astropy__astropy-12907-mavis-m31f-a1/`——`sha256sum` 复算 eval.log=`2c972ea106bc7419`、
agent.diff=`2d0b8307d9d191a0`，与 summary 逐位对应；task_json `/tmp/swev-s1/
astropy__astropy-12907.json` 在位。

**两路判分（判分脚本 sha256 前 16 位 `a292547f3bfce825` = `JudgeLocator::production()`
锚，judge.rs:47，一致）：**

- 旧路（逐字复刻冻结 swev.rs:205-210 硬编码直调）：
  `/home/pan-ding/swev-venv/bin/python …/tools/swev-judge.py <task_json> <eval.log> <agent.diff>`
- 新路：同 argv（`judge::invoke`，locator 字段即同一硬编码路径，judge.rs:77-89）。

**手动重放结果（a1）：**

```
old rc=0 / new rc=0
stdout 164 字节（去尾 163）：
{"resolved": true, "log_parsed": true, "f2p_success": 2, "f2p_failure": 0, "p2p_success": 13, "p2p_failure": 0, "tests_collected": 15, "swebench_version": "4.1.0"}
sha256(old stdout) == sha256(new stdout) == 5c6b1eec756c33b2f84793177a7d6c7c49c1bd6c53e4a2b0de6caecba39627e1  → STDOUT-BIT-IDENTICAL
```

resolved=true / log_parsed=true，与 summary 声明一致。

**Rust 侧全量重放（任务书同类检查的完整形态）：**

```
CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline --test p6_shadow \
  l0_replay_four_historical_evidences -- --ignored --nocapture
```

```
[L0] astropy__astropy-12907 → old(resolved=Some(true), log_parsed=Some(true)) == new；stdout 163 字节逐位一致   （×4）
test l0_replay_four_historical_evidences ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 10 filtered out; finished in 7.71s
```

**逐位一致声明核对：成立。** 4/4 证据 resolved/log_parsed/stdout 三项全同；历史行交叉
报告（4 行 reward=true）与 summary 一致，且测试按 §4.1 只作报告不判死（p6_shadow.rs:757-775）。
**非旁路依据**：`old_judge_call`（shadow.rs:61-72）与 `judge::invoke` 均真实 spawn 子进程，
判据含 `exit_ok` 两侧断言 + 163 字节真实 judge stdout（含 f2p/p2p 计数）逐位相等——
旁路（罐装判定）无法产出与真实判分输出逐位相同的字节。

---

## 4. L1 对拍复核

### 4.1 双变体是否真驱动（判分随日志翻转的非旁路证明）

- **假判分变体**（everywhere）：`CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline
  --test p6_shadow l1_ -- --nocapture` → `l1_fake_runner_chain_vs_frozen_bench_six_dimensions
  ... ok`、`l1_mes_mapping_dimension_via_driver ... ok`（2 passed / 1 ignored）。
- **真判分变体**（`#[ignore]` 真跑）：

```
CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline --test p6_shadow \
  l1_real_judge_old_vs_new_full_verify_chain -- --ignored --nocapture
```

```
[L1-真判分] eval.log:    old=(Some(false), Some("64f2068e3861fdf2…")) new 一致
[L1-真判分] eval-ok.log: old=(Some(true),  Some("35394a7d09d93166…")) new 一致
test l1_real_judge_old_vs_new_full_verify_chain ... ok   （4.12s）
```

- **翻转证明**：测试对同一新路单元代码喂两份仅差 1 处字节的判分日志（fixture
  `p6-shadow/eval.log` 与 `eval-ok.log`，`cmp` 报第 118 字节不同：`FAILED` vs
  `PASSED`），旧路与新路判定分别跟随翻转为 false/true（p6_shadow.rs:602 的
  `[("eval.log", false), ("eval-ok.log", true)]` 双循环，:625 与 :631 两侧各断言）。
  判定随日志内容翻转 ⇒ 判定值确由 judge 子进程产出而非旁路罐装。假判分变体的 D5
  （消费 fake judge stdout）与真判分变体的翻转证明互补，覆盖完整。

### 4.2 十维清单（假判分变体，p6_shadow.rs:399-411 声明 + 逐维断言落点）

| 维 | 内容 | 断言落点 |
|---|---|---|
| D1 | agent.diff 字节（旧 capture_diff vs 新单元落盘） | :447-453 |
| D2 | docker 可见命令族（rm 前置 / run 6g+512 护栏 / capture；容器名一致；旧 1+新 2 次 capture） | :455-478 |
| D3 | eval.sh 字节 = task.eval_script（冻结 write 语义） | :480-485 |
| D4 | eval.log 字节 = 回放 fixture 字节 | :487-493 |
| D5 | resolved 消费（fake judge stdout → 行 reward） | :498 |
| D6 | verifier_note 精确拼装（`judge: {stdout}`，无前缀） | :499-503 |
| D7 | 18 键行 vs 冻结模板 oracle：Value 全等 + 序列化字节全等 | :521-557 |
| D8 | run_id 公式 `{task}-a1` 与 run_dir 命名 | :559-572 |
| D9 | eval_sha256 独立重算对账 | :504-515 |
| D10 | gate 记账（旧路 diff_touches_tests 同 diff 同值） | :517-519 |

### 4.3 六维清单（真判分变体，p6_shadow.rs:633-659）

| 维 | 内容 | 断言落点 |
|---|---|---|
| 1 | resolved（且随日志翻转） | :634 |
| 2 | verifier_note 拼装一致 | :635-639 |
| 3 | eval_sha256 一致（同日志字节） | :640-644 |
| 4 | agent.diff 字节一致 | :645-649 |
| 5 | eval.log 字节一致 | :650-654 |
| 6 | eval.sh = 任务包脚本 | :655-659 |

### 4.4 MES 映射维度（附带核对）

`mes_mapping_table`（shadow.rs:322-365）8 对映射：started↔start / done↔complete /
reward→verdict / tokens_input→usage.quota.input / tokens_output→usage.quota.output /
cache_read→usage.quota.cache_read / turns→usage.turns / wall_ms→wall_ms，由
`l1_mes_mapping_dimension_via_driver`（p6_shadow.rs:860-871）逐条断言；真引擎子进程
驱动（FakeRunner+假 docker+假判分）四类事件对行检查 `check_mes_against_row` 问题清单
为空（:934），`legacy_family_from_row` 各字段与行一致（:938-945）。该测试在我实跑中
通过。

---

## 5. 零改动 / 基准迁移 / RESULT-P6 逐条 / clippy·fmt

### 5.1 af-workorder / af-engine 零改动

```
git diff 1830371..HEAD --stat -- crates/af-workorder crates/af-engine
```

输出 **0 字节**（rc=0）——与 RESULT-P6 §4 声明一致。工作树 `git status --porcelain`
干净（无未提交改动）。

全量变更集（`git diff 1830371..HEAD --name-status`，17 项）：M Cargo.lock、M
af-bench/Cargo.toml、M af-bench/src/main.rs、A af-execline/RESULT-P6.md、M
af-execline/src/lib.rs（+`pub mod shadow;`）、A af-execline/src/shadow.rs、A
fixtures/p6-frozen-bench/{main,swev,tb}.rs、A fixtures/p6-shadow/{agent.diff,
eval-ok.log,eval.log,task.json}、M tests/{p1_comparison,p2_bridge,p3_judge}.rs、A
tests/p6_shadow.rs，以及 **R100**（100% 相似纯改名）af-bench/src/{swev,tb}.rs →
tests/fixtures/p6-frozen-bench/{swev,tb}.rs。删除与冻结件入档由 git 识别为改名，
与 RESULT-P6 §1"删除前冻结字节级副本入 fixtures"相符。

### 5.2 对照测试基准等价迁移（sha256 钉死件核对）

`p1_comparison` / `p2_bridge` / `p3_judge` 的 diff 均为**纯基准路径切换**
（`../af-bench/src/*` → `tests/fixtures/p6-frozen-bench/*`，如 p1_comparison.rs:46-52、
:40-44；p2_bridge.rs:437-446；p3_judge.rs:50-55），断言语义零变化。基准等价性由
sha256 三方一致实证：冻结件 == p6_shadow.rs 钉死值 == git `1830371` blob（见 §2.2）。
即"对照面向迁移时点的旧路"（1830371 字节）成立，属如实登记的等价迁移（RESULT-P6 §5-3）。

### 5.3 clippy / fmt / cargo deny

```
CARGO_TARGET_DIR=~/afbuild-phase2v cargo clippy -p af-execline -p af-bench --all-targets
→ 两 crate 0 警告（仅第三方 proc-macro-error2 v2.0.1 future-incompat 提示，P1 已登记遗留）
cargo fmt --check --all          → rc=0，零 diff
CARGO_TARGET_DIR=~/afbuild-phase2v cargo deny --offline check
→ advisories ok, bans ok, licenses ok, sources ok
```

### 5.4 RESULT-P6 声明逐条核对

| 声明（RESULT-P6） | 核对结果 |
|---|---|
| §4 af-execline 103/0/5 逐二进制分解 | 一致（我实跑逐项相同，§1.1） |
| §4 af-bench 3/0 | 一致（§1.2） |
| §4 L0 4/4 逐位一致（8.5s） | 复跑 PASS（7.71s，环境计时差异） |
| §4 L1 真判分 6 维（4.1s）+ 假判分 10 维 | 双 PASS（4.12s / 常规跑） |
| §1 1255 行 → 843 行 | 相符（旧 git 版 1255，新壳 843） |
| §1 六条拒绝路径文案逐字一致 | 相符（§2.1，6/6） |
| §1 swev.rs(293)/tb.rs(341) 删除 + 冻结件入档 | 相符（R100 改名在册，sha256 一致） |
| §1 壳内 `"suite"` 装配仅 injec 一处 | 相符（唯一落点 main.rs:798） |
| §1 18/12/9/7/11/8 键由 record.rs 装配 | 相符（record.rs 各行族构造 + D7 键数断言） |
| §1 增 af-execline、删 sha2 | 相符（Cargo.toml/Cargo.lock diff） |
| §1 D-20 next_attempt_index 壳层分配 | 相符（main.rs:533-537，调用 af_execline::suite 同函数） |
| §1 进度行/汇总行文案同旧 | 相符（旧 main.rs:897/909/1092/1104 == 新 :567/:598/:656/:692；失败臂文案同旧） |
| §3 L2 钩子三件（配置面/两路命令行/#[ignore] 用例） | `l2_canary_hooks_in_place` 在我实跑中通过；默认值/指纹/前置清单要项断言在位 |
| §3 冻结旧路指纹 `7a87876c0a5541c0` | 复测一致（`sha256sum /tmp/threetest-bin/af-bench-g3-frozen` 前 16 位） |
| §4 git 序列 RED→GREEN | 相符：`3b92aee`（shadow.rs 满布 `unimplemented!()` 桩、p6_shadow 10 测试）→ `707b5b0` → `e5f03c8` → `9b7f98f`（RESULT-P6）→ `5373a55`（Cargo.lock） |
| §4 只读约束（af-workorder/af-engine 0 字节） | 相符（§5.1） |
| §4 cargo deny 四类 ok | 复跑一致（§5.3） |
| §4 未写 `计划/变更日志.md` | 相符（`git diff 1830371..HEAD -- 计划/` 空） |
| §2 原始产物归档 5 文件 | 在位；备份 RESULT-P6.md 与仓库版 `diff` 为空（同字节） |
| §5 偏差登记 8 条 | 与代码/测试事实相符（抽查：薄壳单元直调形态、判分指纹门 EX3002 为方案明文机制升级、L0 历史行只报告不判死） |

### 5.5 机制升级一门（方案明文，非偏差）

单元装载期判分指纹门 fail-loud：`JudgeLocator::check_fingerprint`（judge.rs:56-70，
EX3002）经 `SwevUnitSpec::fix2` → `SwevExecuteUnit::new` 在起容器/调模型前执行；
现产脚本指纹 `a292547f3bfce825…` 与锚一致，我实跑的两项 ignore 测试均先过指纹门
（p6_shadow.rs:597-598、:705-706）。

---

## 6. Notes（不影响 PASS 判定）

1. **冻结旧二进制的"未知套件"文案与 git 全史差一词**（外部物件既有属性，非 P6 引入）：
   `/tmp/threetest-bin/af-bench-g3-frozen`（sha256 前 16 位 `7a87876c0a5541c0`，与
   RESULT-P6 §3 登记一致）打印 `…/ swev-rejudge）`，而 git 历史近 20 个提交的 main.rs
   （含 1830371）与新壳均为 `…/ swe-v）`——该冻结二进制构建自历史外的一次实验源。
   任务书判据是"与 git 历史旧 main.rs 逐字对照"，按此 6/6 一致；此差异对 L2 金丝雀
   无操作面影响（金丝雀只传合法 `--suite swe-v`，永不触发该拒绝路径），但若 L2 未来
   以 stderr 拒绝文案为对拍面，需先知悉此件非 1830371 字节的编译产物。
2. **D7 的 `agent_wall_ms` 判等构造性空转**：oracle 的 wall 值取自行本身，断言恒真
   （p6_shadow.rs:523-548）。注释已如实披露为"计时豁免面"，且与 shadow.rs
   `METERING_ROW_FIELDS` 口径一致；其余 17 键为真实判死。属披露充分的豁免，非缺陷，
   但严格说"18 键全等"中有一键是豁免比较而非独立判死。
3. **RESULT-P6 §2"各异 eval.log/agent.diff"措辞不精确**：a3/a4 共用 agent.diff
   （`7f233cc776d064f8…`，summary jsonl 自身即如实记录），4 份证据的独立性体现在
   eval.log 四值各异（ judging 的主输入）。备份 summary 的记录是准确的，文档措辞
   略有夸张。
4. **p6_shadow 二进制 11 例的账目**：8 passed + 3 ignored 中，第 11 例为冻结 tb.rs
   模块内随 `#[path]` 编译的 P5 测试 `tb::tests::container_guardrail_constants_match_
   calibration`；RESULT-P6 §4 的"p6_shadow 8（3 ignored）"按本文件 10 个 `#[test]`
   记账，两者不相悖，仅统计口径需知悉。

## 7. 我未执行/不在本包范围的事项（如实登记）

- **L2 端到端金丝雀真跑**（真容器+真模型）：按编排者裁定不在 P6 范围，我仅核
  `l2_canary_hooks_in_place`（配置面/命令行/前置清单/指纹）通过与 `#[ignore]` 用例
  在册；未批预算/窗口，未拉真容器真模型。
- **原方案 §4.1-L1 真容器镜像复原对拍**：同属 F-首单任务包，未执行。
- 判分 venv/脚本为只读调用（L0/L1 真判分变体）；未修改判分脚本、未跑工厂守护进程、
  未碰 AB 测试线、未写 `计划/变更日志.md`、未改动任何代码或文档（本报告除外）。
