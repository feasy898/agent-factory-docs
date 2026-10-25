# af-execline P2 宿主桥接吸收独立验证报告（af-bench 吸收 · P2 验证侧）

> 验证者：独立验证代理（P2独立验证者）｜日期：2026-10-24
> 对象：`/home/pan-ding/workspace/af-wt-phase2-execline/crates/af-execline/`，HEAD `286cc43`（分支 `phase2-execline`），含 `src/hostbridge.rs`、`src/suite/{tb,swev}.rs`、`tests/{p1_suite,p1_comparison,p2_bridge,lifecycle}.rs`、`RESULT-P1.md`、`RESULT-P2.md`
> 方法：只读代码 + 本会话实跑命令，**未修改任何代码或文档（本报告除外）**；`git status --porcelain` 终核为空。实现者 `RESULT-P2.md` 自评仅作声明清单，不构成通过依据——每条结论附命令与输出证据。
> 实现交付序列（`git log --oneline -6` 实测）：`dd3bc28`（RED）→ `ee0a6e0`（GREEN）→ `584e462`（clippy 重构）→ `286cc43`（RESULT-P2.md）
> **结论：PASS-with-notes**（六项必做检查全部通过；3 条非阻断备注见 §7）

## 0. 资源纪律（ADR-009）

- 开工 `df -h /`：468G 总量、已用 415G、**可用 29G（94%）**——高于 15G 阈值，开工放行。
- 全部构建只落 `CARGO_TARGET_DIR=~/afbuild-phase2v`（会话后 4.6G）；未碰其他工作树（`af-wt-phase2-order` / `af-wt-phase2-p2` / `af-wt-phase2-dsl` / 主仓 `agent黑灯工厂/af` 均未触碰，只读比对）。
- 只跑 `-p af-execline` 测试（任务书原文形式）；另跑 `cargo fmt --check --all` 与 `cargo deny --offline check`——零编译/只读依赖图，用于复核 RESULT-P2.md §4 同刻度声明，不属"workspace 全量测试"。
- 零容器、零 LLM 网络调用、零凭证消耗。`#[ignore]` docker 冒烟**未执行**（资源纪律禁碰 docker）。
- 会话中另建两个一次性 scratch 副本（`/tmp/red-check` 抽 RED 提交 `dd3bc28`、`/tmp/mut-check` 抽 HEAD）用于 RED 复跑与变异测试，构建目录 `~/afbuild-phase2v-red` / `~/afbuild-phase2v-mut` 均已在会话内删除（各 3.1G），不影响目标工作树。

## 1. 验收测试实跑（必做检查 1）

命令（任务书原文形式，本会话独立执行，exit 0）：

```
cd /home/pan-ding/workspace/af-wt-phase2-execline && CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline
```

关键输出：

```
     Running unittests src/lib.rs     → running 14 tests → ok. 14 passed; 0 failed; 0 ignored
     Running tests/lifecycle.rs       → running  8 tests → ok.  8 passed; 0 failed; 0 ignored
     Running tests/p1_comparison.rs   → running  9 tests → ok.  9 passed; 0 failed; 0 ignored
     Running tests/p1_suite.rs        → running 15 tests → ok. 15 passed; 0 failed; 0 ignored
     Running tests/p2_bridge.rs       → running 13 tests → ok. 12 passed; 0 failed; 1 ignored
       Doc-tests af_execline           → running  0 tests → ok.  0 passed; 0 failed; 0 ignored
```

**结果：58 通过 / 0 失败 / 1 ignored**（lib 14 + lifecycle 8 + p1_comparison 9 + p1_suite 15 + p2_bridge 12 + doc 0），与 `RESULT-P2.md` §4 声明的 "58 passed / 0 failed" 逐项一致。

`#[ignore]` docker 冒烟在册状态（实跑输出原文）：

```
test smoke_real_local_docker_via_bridge ... ignored, 真 local docker 冒烟：需本机 docker 守护进程（cargo test -- --ignored 运行）
```

注册处 `tests/p2_bridge.rs:391-392`（`#[ignore = "真 local docker 冒烟：需本机 docker 守护进程（cargo test -- --ignored 运行）"]`），函数体 `:393-435` 设计为"无 docker / 无 busybox 镜像则打印说明后跳过，不拉镜像、不触网，不假绿不误红"。**本任务未执行该 ignore 用例**（禁碰 docker），其运行判据留给具备 docker 的宿主——与 `RESULT-P2.md` §3-4 的偏差登记一致。

## 2. 桥接收敛复核（必做检查 2）

### 2.1 两处 ssh 模板确实收敛为一

af-bench 存在**两个**语义同构的宿主命令执行函数：

| af-bench 源 | 函数 | 包裹模板 |
|---|---|---|
| `crates/af-bench/src/tb.rs:42-64` | `fn ssh(...)` | `tb.rs:43` `format!("timeout {timeout_sec} bash -c {}", shell_quote(script))`（`shell_quote` 定义在 `tb.rs:66-68`） |
| `crates/af-bench/src/swev.rs:268-293` | `fn tb_ssh(...)` | `swev.rs:269-271` `format!("timeout {timeout_sec} bash -c '{}'", script.replace('\'', "'\\''"))`（内联转义，无函数） |

两者模板**产出逐字节相等**已实测证实。我把两处 `format!` 块逐字复制进独立小程序（`/tmp/p2v-bench/src/main.rs`，rustc 实跑，同输入 `script = "echo \"it's\" >&2"`、`timeout_sec = 180`）：

```
@@bench_wrap_tb@@   |timeout 180 bash -c 'echo "it'\''s" >&2'|  len=40
@@bench_wrap_swev@@ |timeout 180 bash -c 'echo "it'\''s" >&2'|  len=40
WRAP_EQUAL=true
```

af-execline 侧只剩**一个**桥接站点，无残留：

```
$ grep -rn 'Command::new("ssh")\|fn tb_ssh\|fn ssh(' src/ tests/
src/hostbridge.rs:41:            Command::new("ssh")
$ grep -rn 'timeout {timeout_sec}' src/
src/hostbridge.rs:37:        let quoted = format!("timeout {timeout_sec} bash -c {}", shell_quote(script));
```

即 `src/hostbridge.rs:35-59` 的 `impl HostBridge for SshBridge` 是唯一收敛点（`tb.rs:42-64` 的 `ssh` 并入 trait 更名 `run`，函数体逐语句一致，`shell_quote` 改调 P1 已迁副本 `crate::suite::tb::shell_quote`）。`SshBridge` 与 af-bench `ssh()` 的差异仅为 doc 注释与 `shell_quote` 的来源模块，无语义差异。

`shell_quote` / `split_rc` / `tail` 三个随迁函数体与 af-bench 逐字节一致（`diff` 唯一差异是 `pub` 可见性关键字，这是 P1 已登记的可见性提升）：

```
$ diff <(sed -n '/^pub fn shell_quote/,/^}/p' src/suite/tb.rs) <(sed -n '/^fn shell_quote/,/^}/p' ../af-bench/src/tb.rs)
1c1
< pub fn shell_quote(text: &str) -> String {      ---  > fn shell_quote(text: &str) -> String {
（split_rc、tail 同款：仅 fn 行的 pub 差异）
```

### 2.2 黄金命令串测试是否真实断言逐字节相等——是，且黄金值本身与 af-bench `format!` 块逐字节相等

`tests/p2_bridge.rs` 的黄金断言形态是**整个三元组的全等**，不是 `contains` 抽检：

- `p2_bridge.rs:131-134` `assert_eq!(calls[1], ("anolis".to_string(), SWEV_RUN_ANOLIS.to_string(), 120))`
- `p2_bridge.rs:166` `assert_eq!(run, SWEV_RUN_LOCAL)`
- `p2_bridge.rs:233` `assert_eq!(calls[0], ("anolis".to_string(), TB_BUILD.to_string(), 1800))`
- `p2_bridge.rs:250` `assert_eq!(calls[2], ("anolis".to_string(), TB_RUN.to_string(), 60))`
- `p2_bridge.rs:302-310` `assert_eq!(calls[0], ("anolis".to_string(), "docker exec ... ; echo __AF_RC=$?".to_string(), 180))`
- `p2_bridge.rs:257-264` cleanup 三元组全等

我独立复算了黄金值本身（不依赖实现者自述的推导程序）：把 af-bench `format!` 块逐字复制实跑得基准串，与 `p2_bridge.rs` 黄金常量（按 rustc `\` 连续行折叠规则折叠后）逐字节比对，4/4 全等：

| 黄金常量（测试文件:行号） | 对应 af-bench `format!` 块 | 长度 | 结果 |
|---|---|---|---|
| `SWEV_RUN_ANOLIS`（`tests/p2_bridge.rs:92-98`） | `af-bench/src/swev.rs:77-85` | 354 | **逐字节相等** |
| `SWEV_RUN_LOCAL`（`tests/p2_bridge.rs:102-106`） | `af-bench/src/swev.rs:77-85` + `:63-69`（local 分支 `proxy_env=""`） | 234 | **逐字节相等** |
| `TB_BUILD`（`tests/p2_bridge.rs:201-205`） | `af-bench/src/tb.rs:131-139` | 244 | **逐字节相等** |
| `TB_RUN`（`tests/p2_bridge.rs:208-214`） | `af-bench/src/tb.rs:150-159` | 334 | **逐字节相等** |

交叉校验脚本输出（sha256 前 16 位，两侧一致）：

```
bench_tb_build        sha=19bec4328bfc4975 | tb_setup_cmd0   sha=19bec4328bfc4975 | IDENTICAL
bench_tb_run          sha=c07f5ba9a8813714 | tb_setup_cmd2   sha=c07f5ba9a8813714 | IDENTICAL
bench_tb_exec         sha=9abcc91d7edf68c9 | tb_exec_cmd     sha=9abcc91d7edf68c9 | IDENTICAL
bench_swev_run_anolis sha=757ca4f08e684dea | swev_anolis_cmd1 sha=757ca4f08e684dea | IDENTICAL
bench_swev_run_local  sha=9ce53c7df8f761df | swev_local_cmd1 sha=9ce53c7df8f761df | IDENTICAL
```

其中 `SWEV_RUN_LOCAL` 的 `--pids-limit 512` 后**双空格**原样疵点被如实保留（af-bench `swev.rs:80` 的空 `{proxy_env}` 两侧各留一空格，`\` 折叠后即成双空格），`p2_bridge.rs:100-101` 注释明确登记"迁移不顺手修"——这是搬运忠实度的正向证据，不是缺陷。

## 3. 搬运等价性复核（必做检查 3）

我写了一个**独立探针程序**（`/tmp/p2v-probe`，`path` 依赖真实 `af-execline` crate，自带 `FakeBridge` 记录 `(host, script, timeout_sec)`），对真实实现跑 `swev::setup`（anolis/local）/`TbEnv::setup`/`exec`/`cleanup` 并 dump 实际命令串；再与 §2.2 的 af-bench `format!` 块实跑副本逐字节比对。**12/12 对全部 BYTE-EQUAL**：

```
[BYTE-EQUAL] bench_tb_build     == tb_setup_cmd0     len=244   （tb build，超时 1800）
[BYTE-EQUAL] bench_tb_rm_pre    == tb_setup_cmd1     len=39    （前置 docker rm -f，超时 30）
[BYTE-EQUAL] bench_tb_run       == tb_setup_cmd2     len=334   （tb docker run，超时 60）
[BYTE-EQUAL] bench_tb_cleanup   == tb_cleanup_cmd    len=39    （cleanup，超时 60）
[BYTE-EQUAL] bench_tb_exec      == tb_exec_cmd       len=80    （docker exec + cd 前缀 + ; echo __AF_RC=$?，超时 180）
[BYTE-EQUAL] bench_tb_exec_output == tb_exec_output   len=17   （剥标记行 + exit=0 末行）
[BYTE-EQUAL] bench_tb_timeout_output == tb_exec_timeout_out len=403（超时教学文案 + exit=124）
[BYTE-EQUAL] bench_tb_bridge_err == tb_exec_bridge_err len=200（桥接失败可重试文案 + exit=127）
[BYTE-EQUAL] bench_tb_run_err   == tb_run_err        len=57    （起容器失败文案）
[BYTE-EQUAL] bench_swev_rm_pre  == swev_anolis_cmd0  len=54    （前置 docker rm -f，超时 30）
[BYTE-EQUAL] bench_swev_run_anolis == swev_anolis_cmd1 len=354（anolis 三分支，超时 120）
[BYTE-EQUAL] bench_swev_run_local == swev_local_cmd1 len=234  （local 空代理分支，超时 120）
ALL_PAIRS_EQUAL = True
```

**超时表逐点比对**（7/7 一致）：

| 调用点 | af-bench 源:行号 | af-execline 源:行号 | 值 |
|---|---|---|---|
| `TbEnv::setup` docker build | `tb.rs:140` | `suite/tb.rs:165` | 1800 |
| `TbEnv::setup` 前置 rm | `tb.rs:145` | `suite/tb.rs:170` | 30 |
| `TbEnv::setup` docker run | `tb.rs:160` | `suite/tb.rs:185` | 60 |
| `TbEnv::exec` | `tb.rs:192` | `suite/tb.rs:219` | 180 |
| `TbEnv::cleanup` | `tb.rs:295` | `suite/tb.rs:253` | 60 |
| `swev::setup` 前置 rm | `swev.rs:60` | `suite/swev.rs:138` | 30 |
| `swev::setup` docker run | `swev.rs:86` | `suite/swev.rs:164` | 120 |

**错误文案逐点比对**（7/7 逐字节一致，均经探针实跑验证）：

| 文案 | af-bench 源:行号 | af-execline 源:行号 | 探针实测 |
|---|---|---|---|
| `build {image} 失败: {tail(&log, 800)}` | `tb.rs:143` | `suite/tb.rs:168` | 总长 840，与 af-bench 副本一致 |
| `起容器 {container} 失败: {tail(&log, 400)}` | `tb.rs:163` | `suite/tb.rs:188` | len=57 BYTE-EQUAL |
| `起容器失败: {log.chars().take(400)}`（**头**截断，与 tb 尾截断不同） | `swev.rs:93-96` | `suite/swev.rs:171-174` | 总长 417，与 af-bench 副本一致 |
| 桥接启动失败可重试文案 + `exit=127` | `tb.rs:196` | `suite/tb.rs:223` | len=200 BYTE-EQUAL |
| 外层超时教学文案 + `exit=124` | `tb.rs:203` | `suite/tb.rs:230` | len=403 BYTE-EQUAL |
| 截断标记文案（`bytes elided ... read it in parts.]`） | `tb.rs:210` | `suite/tb.rs:237` | `tb_exec_truncates_at_cap_12000` 全等（6000 + elided 8002 + 5998） |
| 桥 `Err` 原样透传（`Err(err) => Err(err)`） | `swev.rs:97` | `suite/swev.rs:175` | 探针透传文案一致 |

其他等价点：容器名折叠 `instance_id.replace("__", "-")`（`swev.rs:57-58` ↔ `suite/swev.rs:135-136`）、`workdir` `/app` 与 `/testbed`（`tb.rs:169` / `swev.rs:91` ↔ `suite/tb.rs:194` / `suite/swev.rs:169`）、代理三分支 local 空 / anolis 三变量（`swev.rs:63-69` ↔ `suite/swev.rs:141-147`）、CAP 12_000 保头尾各 6_000（`tb.rs:206-215` ↔ `suite/tb.rs:233-242`）均一致。

**接口变化仅为止桥注入的签名扩展**（方案 §2.3 设计要求，非行为变化）：`TbEnv::setup(host, task, profile)` → `setup(bridge, host, task, profile)`；`TbEnv::exec(command)` → `exec(bridge, command)`；`TbEnv::cleanup()` → `cleanup(bridge)`；`swev::setup(host, task, profile)` → `setup(bridge, host, task, profile)`。

## 4. 测试质量（必做检查 4）

### 4.1 空断言 / 同义反复扫描——未发现

```
$ grep -rn 'assert!(true)\|assert!(1 == 1)\|assert_eq!(true, true)\|assert!(!false)\|panic!("unimplemented")' tests/ src/
（无输出）
```

断言密度（`tests/p2_bridge.rs` 498 行）：`assert!` 39 处 + `assert_eq!` 37 处 + 2 处 `panic!`（后者在 `as_err` 辅助函数 `:84-86`，是"期望 Err 实得 Ok"的守卫，非测试体空转）。对比 `p1_suite.rs` 20/51、`p1_comparison.rs` 10/19、`lifecycle.rs` 18/35，密度正常。

### 4.2 p2_bridge 12 测试是否真驱动 bridge（含错误路径）——是，有 RED 复跑与变异测试双重证据

**证据 A：RED 提交复跑**。我用 `git archive dd3bc28` 把 RED 提交抽到 `/tmp/red-check`（只读源仓库，未动工作树），独立构建运行：

```
test result: FAILED. 2 passed; 10 failed; 1 ignored
```

10 个失败全部是 `unimplemented!()` panic，且 panic 位置正是 RED 桩所在行：

```
thread 'ssh_bridge_local_branch_runs_bash_merges_stderr_and_status' panicked at crates/af-execline/src/hostbridge.rs:32:9
thread 'swev_setup_anolis_builds_guardrail_proxy_hygiene_command' panicked at crates/af-execline/src/suite/swev.rs:134:5
thread 'tb_setup_and_cleanup_command_sequence' panicked at crates/af-execline/src/suite/tb.rs:150:9
...（共 10 处，与桩位一一对应）
```

RED 下通过的 2 例恰为 `hostbridge_trait_is_object_safe` 与 `cmp_p2_templates_against_bench_source`——即 `RESULT-P2.md` §4 声明的"过的两项：源文本比对与对象安全，不依赖桩"，**复跑逐字吻合**。这同时证明另外 10 例**确实穿透实现驱动 bridge**，不是自说自话。

**证据 B：变异测试**（在 `/tmp/mut-check` HEAD 副本上做，未碰真实工作树；每轮后还原并复跑确认回绿）：

| # | 变异 | 结果 |
|---|---|---|
| M1 | `swev::setup` 超时 120 → 60 | **被捕获**（`swev_setup_anolis...` FAILED） |
| M2 | `TB_CONTAINER_MEM` `2g` → `4g` | **被捕获**（`tb_setup_and_cleanup...` FAILED） |
| M3 | 桥 stderr 合并分隔符 `'\n'` → `' '` | **被捕获**（`ssh_bridge_local_branch...` FAILED） |
| M4 | swev 错误文案 `起容器失败` → `起容器出错` | **被捕获**（`swev_setup_run_failure...` FAILED） |
| M5 | `shell_quote` 单引号转义整体删除 | **被捕获**（2 例 FAILED） |
| M6 | exec 截断 `CAP` 12_000 → 6_000 | **被捕获**（`tb_exec_truncates_at_cap_12000` FAILED） |
| M7 | ssh 分支删掉 `-o BatchMode=yes` | **未被捕获**（12 passed） |
| M8 | local 分支 `bash` → `sh` | **未被捕获**（12 passed） |

M7 是本次验证最实质的发现：**anolis ssh 分支的 argv 无任何测试覆盖**。`cmp_p2_templates_against_bench_source`（`p2_bridge.rs:448-489`）只断言 af-bench **源文本**含这些模板，不断言 af-execline **实现**的 `Command` argv——M7 改了实现、源文本没动，故测试全绿。`RESULT-P2.md` §3-3 已如实登记此偏差（"anolis ssh 分支无单测……属 L2 对拍面"），但登记理由（"触网"）只解释了为何不真跑 ssh，未点出**命令构造层面**的这一缺口；M8（`bash`→`sh`）同类，不过 local 分支的脚本未用 bashism，实际影响可忽略。

**错误路径覆盖**（问题明确要求"含错误路径"）：4 例专测错误/降级路径，均经 FakeBridge 脚本化响应驱动——
- `swev_setup_run_failure_error_messages`（`:177-196`）：`Ok((false, 500×"x"))` → `chars().take(400)` 头截断断言；`Err("命令桥接启动失败: ...")` → 原样透传断言。
- `tb_setup_failure_error_messages`（`:268-288`）：build 失败 → `tail 800` 尾截断；run 失败 → `tail 400`。
- `tb_exec_bridge_failure_reports_transient_infrastructure`（`:331-341`）：桥 `Err` → 可重试文案 + `exit=127`。
- `tb_exec_timeout_without_marker_teaches_and_exits_124`（`:315-327`）：无 `__AF_RC` 标记 → 教学文案 + `exit=124`。

**测试清单 13 例与 `RESULT-P2.md` §2 表格逐条对应**（12 跑 + 1 ignore），无遗漏、无表格外新增。

### 4.3 两处轻微观测（不构成失败）

1. `swev_setup_anolis_builds_guardrail_proxy_hygiene_command` 的 5 个 `contains` 断言（`p2_bridge.rs:135-155`）在逻辑上已被同测试 `:131-134` 的整串 `assert_eq!` 蕴含——属冗余而非空断言（字符串若变它们确实会红），作用是逐条点名方案 §5-P2 草案条目、失败时定位更准。
2. `hostbridge_trait_is_object_safe`（`:494-498`）的运行时断言只有 `assert_eq!(bridges.len(), 2)`，实质检验在编译期（`Vec<&dyn HostBridge>` 能否成立）；测试注释已自陈此点。

## 5. 声明核对（必做检查 5）

### 5.1 af-bench 零改动——实测为空

```
$ git diff 6ee05f8..HEAD --stat -- crates/af-bench crates/af-workorder crates/af-engine
（空输出）
$ git status --porcelain
（空输出 = 工作树干净）
```

`git ls-files crates/af-bench` 在册 4 文件（`Cargo.toml`、`src/main.rs`、`src/swev.rs`、`src/tb.rs`），全部零改动。`RESULT-P2.md` 头部"af-bench / af-workorder / af-engine 零改动"声明**成立**。

补充支持 `RESULT-P2.md` §4"迁移源一致性"声明：工作树 af-bench 与主仓（`agent黑灯工厂/af`，HEAD `94cd192`，分支 `guardrail-fix2`）逐字节一致——

```
main.rs: IDENTICAL    tb.rs: IDENTICAL    swev.rs: IDENTICAL    Cargo.toml: IDENTICAL
```

故"吸收基准即主仓现行为"成立，等价性对拍有意义。

### 5.2 clippy / fmt / cargo deny 记录——三项均实跑通过

```
$ CARGO_TARGET_DIR=~/afbuild-phase2v cargo clippy -p af-execline --all-targets
    Checking af-execline v0.1.0 (...)
    Finished `dev` profile ... in 0.63s
warning: the following packages contain code that will be rejected by a future version of Rust: proc-macro-error2 v2.0.1
CLIPPY EXIT: 0
```
af-execline 自身 0 警告；唯一提示为第三方 `proc-macro-error2 v2.0.1` future-incompat（`RESULT-P1.md` §3-5 已登记遗留，非本包新增）。与 `RESULT-P2.md` §4 声明一致。

```
$ CARGO_TARGET_DIR=~/afbuild-phase2v cargo fmt --check --all
FMT_ALL_EXIT: 0
```
零 diff，与 §4 声明的 `cargo fmt --check --all` PASS 一致（我跑了任务书/声明点名的原命令，非更窄替代）。

```
$ CARGO_TARGET_DIR=~/afbuild-phase2v cargo deny --offline check
advisories ok, bans ok, licenses ok, sources ok
DENY_EXIT= 0
```
与 §4 "四类 ok" 一致。

### 5.3 其余声明逐条核对

| `RESULT-P2.md` 声明 | 实跑/实测 | 判定 |
|---|---|---|
| §4 测试 "58 passed / 0 failed" | §1 实测 58/0/1ignored | **一致** |
| §4 RED 基线 "p2_bridge 10 红/2 过/1 ignore"，过的两项为源文本比对与对象安全 | §4.2 证据 A 复跑：2 passed / 10 failed / 1 ignored，过的正是那两项，10 处 panic 对位桩行 | **一致** |
| §4 git 序列 `dd3bc28 → ee0a6e0 → 584e462 → 本文件提交` | `git log --oneline -6` 实测 `286cc43 → 584e462 → ee0a6e0 → dd3bc28`，红→绿成立 | **一致** |
| §4 clippy / fmt / cargo deny | §5.2 三项 exit 0 | **一致** |
| §4 只读约束 af-bench 零改动 | §5.1 `git diff` 空 | **一致** |
| §4 迁移源一致性（与主仓逐字节一致） | §5.1 `cmp` 四文件 IDENTICAL | **一致** |
| 头部"未写 计划/变更日志.md" | `git log --all -- 计划/变更日志.md` 空；工作树无 `计划/` 目录 | **一致** |
| 头部"未碰 P3-P6 内容" | `git diff 6ee05f8..HEAD --stat` 仅 6 文件、全在 `crates/af-execline/`（RESULT-P2.md 108 行 + hostbridge.rs 59 + lib.rs 2 + swev.rs 65 + tb.rs 133 + p2_bridge.rs 498，859 insertions / 6 deletions） | **一致** |
| §2 测试清单 13 例 | §4.2 逐条对应 | **一致** |

## 6. 结论三态

**PASS-with-notes**

六项必做检查全部通过：测试全绿（58/0/1ignored，ignore 冒烟在册未跑）、桥接确已收敛为单一站点且两处 af-bench 模板产出逐字节相等、黄金命令串测试真实断言全等且黄金值本身与 af-bench `format!` 块逐字节相等（4/4）、搬运等价经独立探针对拍 12/12 命令串 + 7/7 超时 + 7/7 错误文案逐字节一致、测试无空断言且 10/12 例经 RED 复跑证明真驱动 bridge（错误路径 4 例齐备）、af-bench 零改动与 clippy/fmt/deny 声明均实测成立。

不定 PASS 而定 PASS-with-notes，原因全部是**非代码性**的观测与一条已登记但可补强的覆盖缺口（§7.1–7.3），不涉及任何搬运不等价或测试造假。

## 7. 遗留 / 备注（非阻断）

1. **anolis ssh 分支 argv 无测试覆盖（可用 M7 实证复现）**。删掉 `src/hostbridge.rs:42-44` 的 `-o BatchMode=yes`，`cargo test -p af-execline` 仍全绿。`RESULT-P2.md` §3-3 已登记该分支无单测，但登记的是"触网不便真跑"，未点明命令构造层可被无痕改动。建议 P3 起在 `cmp_p2_templates_against_bench_source` 之外，补一条对 af-execline 实现 argv 的断言（如经 FakeBridge 捕获 `Command` 构造，或把 ssh 命令构造抽成可测纯函数），成本低、堵住的是"收敛行为被静默改坏"这一类回归。不影响 P2 验收。
2. **`RESULT-P2.md` 头部工作树名与实际不符**。声明写"工作树 `af-wt-phase2-p2`（分支 `phase2-execline-p2`）"，实际验证对象是 `af-wt-phase2-execline` / 分支 `phase2-execline`。工作区里确有一个 `af-wt-phase2-p2`，但它在分支 `phase2-execline-p3`、同为 `286cc43`（内容一致，`af-bench` 两文件 `cmp` IDENTICAL）。属文档笔误，无行为影响。
3. **`RESULT-P2.md` §4 记录的磁盘数与本次实测不符**。声明"开工 `df -h /` → 38G 可用"，我开工实测为 29G 可用（94% 已用）。两者均高于 15G 阈值、不改变放行结论；差异来自测量时点与构建占用。另 §4.3 观测到的两处轻微断言冗余（`p2_bridge.rs:135-155` 的 `contains` 被 `:131-134` 蕴含；`:497` 仅断言 `len()==2`）已在上文说明，不构成缺陷。

---
*本报告由独立验证代理基于只读代码审读与本会话实跑命令生成；除本报告外未修改目标工作树任何文件（`git status --porcelain` 终核为空）。*
