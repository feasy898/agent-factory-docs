# af-execline P1 纯函数层吸收独立验证报告（af-bench 吸收 · P1 验证侧）

> 验证者：独立验证代理（P1独立验证者）｜日期：2026-10-24
> 对象：`/home/pan-ding/workspace/af-wt-phase2-execline/crates/af-execline/`（src/ 全部含 suite/ 新模块 + tests/ 全部 + RESULT-P1.md），HEAD `6ee05f8`（分支 phase2-execline）
> 方法：只读代码 + 本会话实跑命令，未修改任何代码与文档（本报告除外）。实现者 RESULT-P1.md 自评仅作声明清单，不构成通过依据；每条结论附命令与证据。
> 实现交付：RED `1111c60` → GREEN `97b7da6` → 文档 `6ee05f8`（`git log --oneline -8` 实测）。

## 0. 资源纪律（ADR-009）

- 开工 `df -h /`：468G 总量、已用 406G、**可用 38G（92%）**——高于 15G 阈值，开工放行。
- 全部构建只落 `CARGO_TARGET_DIR=~/afbuild-phase2v`（新目录，会话后 3.5G）；未碰其他工作树（af-wt-phase2-order / af-wt-phase2-p2 / 主仓 `af/target` 均未触碰）。
- 只跑 `-p af-execline` 测试（任务书原文形式）；另跑 `cargo fmt --check --all`——这是零编译的格式检查（无构建、不占磁盘），用于复核 RESULT §4 同刻度声明，不属"workspace 全量测试"。
- 零容器、零 LLM 网络调用、零凭证消耗（`resolve_key` 测试只用 printf/echo 假命令，见 tests/p1_suite.rs:333-345）。

## 1. 验收测试实跑

命令（任务书原文形式，本会话独立执行）：

```
cd /home/pan-ding/workspace/af-wt-phase2-execline && CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline
```

关键输出（exit 0）：

```
    Finished `test` profile [unoptimized + debuginfo] target(s) in 38.63s
warning: the following packages contain code that will be rejected by a future version of Rust: proc-macro-error2 v2.0.1
     Running unittests src/lib.rs       → running 14 tests → test result: ok. 14 passed; 0 failed
     Running tests/lifecycle.rs         → running  8 tests → test result: ok.  8 passed; 0 failed
     Running tests/p1_comparison.rs     → running  9 tests → test result: ok.  9 passed; 0 failed
     Running tests/p1_suite.rs          → running 15 tests → test result: ok. 15 passed; 0 failed
       Doc-tests af_execline             → running  0 tests → test result: ok.  0 passed; 0 failed
```

**结果：46 通过 / 0 失败（lib 14 + lifecycle 8 + p1_comparison 9 + p1_suite 15 + doc 0）**，与 RESULT-P1.md §4 声明的 "46 passed / 0 failed" 逐项一致。

p1_comparison 9 例中有 1 例是 af-bench 自带的单测随 `#[path]` 编译进本二进制运行：

```
test tb::tests::container_guardrail_constants_match_calibration ... ok   ← 仅存在于 af-bench tb.rs:326-341
```

## 2. 搬运等价性复核

### 2.1 活源对拍（p1_comparison）是否真实有效——三条独立证据

1. **路径指向真实 af-bench 源文件**：tests/p1_comparison.rs:24-30 为
   `#[path = "../../af-bench/src/tb.rs"] mod tb;` / `#[path = "../../af-bench/src/swev.rs"] mod swev;`。
   相对 tests/ 目录解析即 `crates/af-bench/src/{tb,swev}.rs`——实测在位，且含 af-execline 副本没有的生命周期代码（tb.rs:94-297 `TbEnv/ssh/setup/exec/verify/cleanup`）与 `#[cfg(test)] mod tests`（tb.rs:326-341）。
2. **af-bench 原单测在本二进制内运行通过**：运行输出含 `tb::tests::container_guardrail_constants_match_calibration`——该测试只存在于 af-bench tb.rs:334-340，af-execline `suite/tb.rs` 无任何测试模块。若 `#[path]` 指向副本/空文件，此测试不可能出现。**此为活源对拍真实有效的 conclusive 证据**。
3. **af-bench swev.rs 的模块间依赖被满足**：af-bench swev.rs:14 `use crate::tb;` 只在测试 crate 根存在 `mod tb` 时可编译——swev.rs 确实作为本测试 crate 的模块被整体编译（p1_comparison.rs:20-22 注释对此有说明）。

另外，工作树 af-bench 三文件与主仓（`agent黑灯工厂/af`，94cd192）逐字节一致（`diff` 空输出），故"旧路基准即主仓行为"的声明成立：

```
$ diff /home/pan-ding/workspace/agent黑灯工厂/af/crates/af-bench/src/main.rs crates/af-bench/src/main.rs → 空
$ diff .../tb.rs   crates/af-bench/src/tb.rs   → 空
$ diff .../swev.rs crates/af-bench/src/swev.rs → 空
```

### 2.2 人工比对：3 个函数（任务书点名要求）+ 全量清单

**抽查函数 1——`diff_touches_tests`**：af-bench `crates/af-bench/src/swev.rs:121-139` ↔ af-execline `crates/af-execline/src/suite/swev.rs:60-78`。
实现：`strip_prefix("diff --git ")` → `split_whitespace().nth(1)` → `trim_start_matches("b/").to_lowercase()` 判定（`contains("test")` 或四类配置后缀）→ 推送**原大小写**的剥前缀路径。`diff` 两段行区：**空**（逐字节一致）。

**抽查函数 2——`load_tb_tasks`**：af-bench `crates/af-bench/src/tb.rs:17-36` ↔ af-execline `crates/af-execline/src/suite/tb.rs:26-45`。
实现：读 `instruction.md` → 校验 `environment/Dockerfile` 与 `tests/test.sh` `is_file()` → 推 `TbTask{task_id, prompt}`；两条报错文案 `"{name} 缺 environment/Dockerfile"` / `"{name} 缺 tests/test.sh"` 一致。`diff`：**空**。

**抽查函数 3——`profile()`**：af-bench `crates/af-bench/src/main.rs:163-327` ↔ af-execline `crates/af-execline/src/profile.rs:27-191`。
165 行档案表，唯一差异是 fn 行 `fn`→`pub fn`；10 档案的 base_url/model/key_ref/reasoning_tier/stream/auth 字面量与未知档案报错模板逐字节相同。`diff`：仅 `1c1`（pub）。

**全量清单复核**（`diff <(sed -n 'A,Bp' 源) <(sed -n 'C,Dp' 目标)` 逐段实测，覆盖 RESULT §1 表全部 18 行 + 2 个随迁单测）：

| # | 搬入物 | af-bench 源 | af-execline 落位 | diff 结果 |
|---|---|---|---|---|
| 1 | `SwevTask`（含 serde default） | swev.rs:16-27 | suite/swev.rs:20-31 | 空 |
| 2 | `SwevTask::prompt` | swev.rs:29-39 | suite/swev.rs:33-43 | 空 |
| 3 | `load_swev_tasks` | swev.rs:41-52 | suite/swev.rs:45-56 | 空 |
| 4 | `diff_touches_tests` | swev.rs:119-139 | suite/swev.rs:58-78 | 空 |
| 5 | `SWEV_SYSTEM_PROMPT` | main.rs:543 | suite/swev.rs:84 | 仅 `pub` |
| 6 | `SWEV_INSTANCE_PROTOCOL` | main.rs:548-566 | suite/swev.rs:90-108 | 仅 `pub` |
| 7 | `ARCHAEOLOGY_PATTERNS` | main.rs:570-577 | suite/swev.rs:113-120 | 仅 `pub` |
| 8 | `TbTask` | tb.rs:12-15 | suite/tb.rs:21-24 | 空 |
| 9 | `load_tb_tasks` | tb.rs:17-36 | suite/tb.rs:26-45 | 空 |
| 10 | `shell_quote` | tb.rs:66-68 | suite/tb.rs:48-50 | 仅 `pub` |
| 11 | `split_rc` | tb.rs:70-92 | suite/tb.rs:52-75 | 仅 `pub`+归属注释 |
| 12 | 护栏常量+校准注释 | tb.rs:101-120 | suite/tb.rs:77-97 | 仅 +1 归属注释行 |
| 13 | `tail` | tb.rs:299-305 | suite/tb.rs:100-106 | 仅 `pub` |
| 14 | `bash_tool_decl` | tb.rs:307-324 | suite/tb.rs:108-126 | 仅 +1 归属注释行 |
| 15 | `Profile` struct | main.rs:158-161 | profile.rs:21-24 | 仅 `pub` |
| 16 | `profile()` | main.rs:163-327 | profile.rs:27-191 | 仅 `pub` |
| 17 | `resolve_key` | main.rs:329-350 | profile.rs:194-215 | 仅 `pub` |
| 18 | `status_label` | main.rs:579-588 | suite/mod.rs:18-27 | 仅 `pub` |
| 19 | `next_attempt_index` | main.rs:590-610 | suite/mod.rs:29-50 | 仅 `pub`+归属注释（4 行 doc 注释原样在册） |
| 20 | 随迁单测 D-20 | main.rs:48-73 | tests/p1_suite.rs:43-69 | 断言全等；差异=归属注释行 + 临时目录前缀 `af-bench-d20-test-`→`af-execline-d20-test-`（p1_suite.rs:47，防撞，文档已声明） |
| 21 | 随迁单测护栏 | tb.rs:330-340 | tests/p1_suite.rs:71-79 | 断言全等；doc 注释 4 行缩为 1 行（见 N2） |

结论：**搬运等价性成立**——所有函数体/常量逐字节一致，差异仅限 `pub` 提权（方案要求 P2/P5 复用，函数体不动）、归属注释行、以及临时目录防撞前缀，全部与 RESULT §1"备注"列自述相符。

### 2.3 私有函数（shell_quote / split_rc / tail）黄金值测试是否合理

私有性属实：af-bench tb.rs:66/73/299 三者均为无 `pub` 的模块私有 fn。机制探针（/tmp/p1probe，未碰工作树）复现两条约束：

```
$ rustc --edition 2021 src/pathmod.rs   → error[E0603]: function `shell_quote` is private（#[path] 模块外不可见）
$ rustc --edition 2021 src/incmod.rs    → error[E0753]: expected outer doc comment（include! 吃不下 //! 文件头）
```

黄金值合理性——按 af-bench 原实现（与副本逐字节一致）人工推导三例：

- `shell_quote`（`format!("'{}'", text.replace('\'', "'\\''"))`）：`"ls -la"`→`'ls -la'`；`"it's"`→`'it'\''s'`；`""`→`''`；`"a\nb\tc"`→`'a\nb\tc'`。与 p1_suite.rs:190-193 四例**全符**。
- `split_rc`（`rfind` 标记→行首/行尾定位→只删标记行）：`"plain output\nno marker"`→(原文, None)；`"out\n__AF_RC=0"`→(`"out\n"`, Some(0))；中部例 `"a\n__AF_RC=7\nstderr tail"`→ line_start=2、line_end=11 → `"a\n"+"\nstderr tail"`=(`"a\n\nstderr tail"`, Some(7))。与 p1_suite.rs:172-184 **全符**；RESULT §2 自述"中部标记行初版推导漏了保留的前导换行、实跑纠正后入测"与最终测试内容吻合（前导 `\n` 确在期望值中）。
- `tail`（`len<=cap` 原样 / 否则保末 `cap` **字节**）：`("abc",5)`→`"abc"`；`("abcdefghij",3)`→`"hij"`；`("",3)`→`""`。与 p1_suite.rs:199-201 **全符**。注：按字节切片而非字符——黄金值全为 ASCII，无多字节 panic 风险，且与 af-bench 实现语义相同（非"更正确"的改写）。

结论：三个私有函数以黄金值固化是**当前约束下的合理形态**（机制不可对拍已实证），且黄金值经人工推导与实跑双重核对无误。

## 3. 测试质量审查

通读 tests/p1_suite.rs（15 例）与 tests/p1_comparison.rs（8 例 + af-bench 随入 1 例）。

### 3.1 空断言 / 同义反复 / 被注释断言扫描

| 扫描项 | 命令 | 结果 |
|---|---|---|
| 被注释断言 | `grep -n '// *assert\|// *#\[test\]' p1_suite.rs p1_comparison.rs` | **无匹配** |
| `#[ignore]` | `grep -n '#\[ignore' …` | **无匹配**（无跳过的测试） |
| 空/恒真断言 | `grep -n 'assert!()\|assert!(true)\|assert_eq!(x, x)' …` | **无匹配** |
| 断言密度 | `grep -c assert` | p1_suite 71 处 / p1_comparison 29 处（24 例，均值 ~4 处/例） |

- 同义反复：未发现自我比较。p1_comparison 的 `assert_eq!(new, old)` 两侧是**两个独立编译的实现**（af-execline 副本 vs `#[path]` 编译的 af-bench 原文件），非同一表达式。
- 防假绿设计在位：`cmp_diff_touches_tests_battery` 在 15 例全等之外另有 `assert!(!all_hits.is_empty())` 与点名样例 `assert_eq!(…, vec!["tox.ini"])`（p1_comparison.rs:88-97），防"两边同返空"的假绿。
- 源文本比对类测试（profile 表/提示词/模式/标签）以"重建字面量→断言 main.rs 原文含它"实现，差一字节即失配；与活源对拍、黄金值形成三层互证。

### 3.2 搬运清单（RESULT §1）落位抽查

任务书要求抽查 ≥6 项；本次对 §1 表**全部 18 行 + 2 个随迁单测**逐字节复核（见 §2.2 表），全部落在声明行位。计数说明：表实为 **18 行**（任务书表述"19 项"，若把护栏 4 常量拆算则为 21 项——计数口径差异，见 N3，不影响核验结论）。

## 4. 声明核对（RESULT-P1.md §3 五项偏差 + 零改动 + 红绿序）

| 偏差 | 声明要点 | 核验命令/证据 | 判定 |
|---|---|---|---|
| ① af-harness 依赖自 P4 提前至 P1 | P1 目标内 `profile()` 返回 af-harness `EndpointSpec`、`status_label` 收 `&RunStatus`，原样搬要求签名不动 | Cargo.toml:30 `af-harness = { path = "../af-harness" }`（[dependencies]）；profile.rs:15,22 用 `EndpointSpec`；suite/mod.rs:14,18 用 `RunStatus`；方案文件:170 原文"**依赖**：无（仅 serde/serde_json，已有）"确实在册（P1 节） | **如实** |
| ① 附带：无环 | af-execline←af-harness 无环 | `grep -rn "af-execline" crates/af-harness/` → **无命中**；af-harness deps=af-credential/af-effect-gateway/af-meter/af-stop/af-trace/af-workorder/biscuit-auth/rusqlite/ureq | **属实** |
| ② 随迁测试 2 非 3 | 方案记 3 个、实测 2 个 | `grep -c '#\[test\]'` → main.rs **1**、tb.rs **1**、swev.rs **0**；方案文件:59 原文"af-bench 现有 3 个单测（…main.rs:48-73、护栏常量 tb.rs:334-340）"在册（只列了 2 个名字） | **如实** |
| ③ 三私有函数无法活源对拍 | 私有不可见 + include! 吃不下 //! 头（E0753） | /tmp/p1probe 实测 E0603 + E0753（§2.3）；af-bench tb.rs:66/73/299 确为私有 | **如实** |
| ④ `tb::ssh` 对照缺口（P2 范围，存照非偏差） | 本包未搬未测 | af-execline `suite/tb.rs` 无 `ssh`/`TbEnv`（对照 af-bench tb.rs:42-297） | **属实** |
| ⑤ 第三方 future-incompat 提示 | proc-macro-error2 v2.0.1，非本包 lint 警告 | 本会话 `cargo test` 与 `cargo clippy` 输出均复现该 warning；af-execline 自身 0 警告、clippy exit 0 | **如实**（本会话独立复现） |

**af-bench 零改动声明**：

```
$ git diff 44b7f17..HEAD --stat -- crates/af-bench crates/af-workorder crates/af-engine
（空输出）
$ git diff 44b7f17..HEAD --stat
 Cargo.lock | 3 +  crates/af-execline/{Cargo.toml,RESULT-P1.md,src/lib.rs,src/profile.rs,src/suite/mod.rs,src/suite/swev.rs,src/suite/tb.rs,tests/p1_comparison.rs,tests/p1_suite.rs}
```

零改动**属实**：区间内只动 af-execline + Cargo.lock（lock 增量恰为 af-harness/af-stop/sha2 三项，与 Cargo.toml 一致）。

**RED→GREEN 序**：`git log --oneline` 为 `1111c60`(RED) → `97b7da6`(GREEN) → `6ee05f8`(本文档)，红在绿前。RED 提交形态经 `git show 1111c60:crates/af-execline/src/suite/swev.rs` 验证在位：`unimplemented!("P1 RED 桩")` ×3 + 三处"RED 占位"常量注释；profile.rs 同为 `unimplemented!("P1 RED 桩：…")`。RED 态失败计数（0/15、2/9）未复跑——复跑需检出历史提交，与"禁改工作树"冲突，见 N6。

**§4 验证记录表其余行**：46/46（§1 复现一致）；clippy 0 警告（§5 复现）；fmt 零 diff（§5 复现，含 `--all`）；迁移源与主仓逐字节一致（§2.1 复现）；资源纪律（§0）。`cargo deny` 四类 ok 一行**本次未跑**（任务书必做项未列，见 N7）。

## 5. 健康度

| 检查 | 命令（本会话实跑） | 输出/退出码 | 结果 |
|---|---|---|---|
| clippy | `CARGO_TARGET_DIR=~/afbuild-phase2v cargo clippy -p af-execline --all-targets` | `Finished dev profile … in 31.95s`；唯一 warning 行=第三方 proc-macro-error2 future-incompat；**exit 0** | **af-execline 自身 0 警告** |
| fmt（crate 级） | `cargo fmt --check -p af-execline` | 无输出，**exit 0** | **通过** |
| fmt（workspace 级，复现 RESULT §4 同刻度声明；零编译格式检查，不涉全量测试） | `cargo fmt --check --all` | 无输出，**exit 0** | **通过** |

## 6. 结论

### **PASS-with-notes**

核心验收全部独立复证：46/46 测试实跑通过（新构建目录 `~/afbuild-phase2v`）；活源对拍真实有效（af-bench 原文件经 `#[path]` 编译，其自带单测在对照二进制内运行通过）；搬运清单 18 行 + 2 随迁单测全部逐字节复核，差异仅限文档已声明的 `pub` 提权/归属注释/防撞前缀；三私有函数黄金值经人工推导+实跑双核对无误；五项偏差逐条与代码、Cargo.toml、方案原文、机制探针对上，无一处夸大；af-bench/af-workorder/af-engine 区间零改动经 git 实证；clippy/fmt 干净。**未发现阻断性问题。**

**问题清单（notes，均非阻断）**：

- **N1** RESULT-P1.md:27 行号笔误：护栏常量行写"注释随迁 tb.rs:73-92"，应为 **tb.rs:101-114**（73-92 是 split_rc）。代码侧归属注释 suite/tb.rs:91 的引用是正确的，仅文档行写错。
- **N2** p1_suite.rs:72 自称"逐字随迁"：护栏单测的 doc 注释由 af-bench tb.rs:330-333 四行缩为一行+归属行（校准推导以交叉引用保留）；**断言体逐字**。属轻度不精确表述，不影响测试效力。
- **N3** 任务书"19 项搬运清单"与 RESULT §1 表实际行数不符：表为 **18 行**（护栏 4 常量合 1 行；拆算则 21 项）。本次按全量 18 行+2 单测复核，超额满足"抽查 ≥6 项"要求。
- **N4** af-stop（dev-dep：`RunStatus::Stopped{decision}` 构造）、sha2（dev-dep：`#[path]` 编译的 af-bench swev.rs 的 `sha256_hex` 需要）未在 §3 偏差清单逐条列名，但在 Cargo.toml:36-44 有注释说明，且方案 §1.2-3（方案文件:51）本就预告吸收需新增 af-credential/af-harness/af-meter/af-stop/sha2。记录性质。
- **N5** 源文本比对类的覆盖边界：`cmp_status_labels_against_bench_source` 只验证六个标签字面量在 main.rs 在册，臂→标签映射由 p1_suite 黄金值锁定；`cmp_profile_table_against_bench_source` 验证字面量出现而不绑定到具体档案臂。两者合并覆盖可接受，且 profile() 整体已由本次逐字节 diff 证明与 main.rs:163-327 全等——源文本测试是冗余保险而非唯一防线。
- **N6** RED 态失败计数（p1_suite 0/15、p1_comparison 2/9）未复跑（复跑需检出历史提交，与禁改工作树冲突）；以 RED 提交的 `unimplemented!()`/占位常量形态 + git 序列佐证。
- **N7** `cargo deny --offline check` 未跑（任务书必做项未列；RESULT §4 的"四类 ok"声明本次未独立复证）。

**已知边界（实现者自报、本次核对底层事实属实，不算新发现）**：`tb::ssh`/`TbEnv` 生命周期、swev setup/verify/sha256_hex、results 行装配属 P2-P5，本包确未搬未测（§4 偏差④已核）；判分三件套契约接口未动。
