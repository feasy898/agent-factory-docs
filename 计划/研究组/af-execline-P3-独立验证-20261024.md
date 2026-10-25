# af-execline P3（判分链搬运）独立验证报告

> 身份：独立验证者（与 P3 实现者无涉），2026-10-24。
> 对象：`/home/pan-ding/workspace/af-wt-phase2-execline/`（HEAD = `4cba6cb`，
> 分支 `phase2-execline`），验收面 = `crates/af-execline/`。
> 纪律：只读 + 实跑；未改任何代码/文档（本报告除外）；未写
> `计划/变更日志.md`；未跑 workspace 全量测试；构建目录 `CARGO_TARGET_DIR=~/afbuild-phase2v`。
> 开工 `df -h /`：27G 可用（95% 已用）→ 收尾 25G 可用。过程中 `/tmp` 写入触发
> 磁盘配额（EDQUOT os error 122），改用 `~/afbuild-phase2v` 热缓存后完成全部构建。

---

## 0. 结论

**PASS**（附 3 条不影响验收的 notes，见 §5）。

必做检查 1–4 全部实跑通过；P3 交付物与 RESULT-P3.md 声明逐条核对一致；
判分独立性三组守卫经 11 个变异体实证非空转（变异测试全杀）。

---

## 1. 实跑测试（任务书必做项 1）

### 1.1 验收命令原文

```
cd /home/pan-ding/workspace/af-wt-phase2-execline && CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline
```

输出（`test result` 行全量）：

```
     Running unittests src/lib.rs
test result: ok. 14 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
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
test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.04s
   Doc-tests af_execline
test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```

**exit 0；14+8+9+15+12+4+7 = 69 passed / 0 failed / 2 ignored**
（lib 14 / lifecycle 8 / p1_comparison 9 / p1_suite 15 / p2_bridge 12+1ig /
p3_judge 4+1ig / p3_verify 7 / doc 0）。与 RESULT-P3.md §4 表格声称的
"69 passed / 0 failed" 逐项相符。

### 1.2 `--ignored`（真 venv fixture / 真 docker 冒烟）——环境允许，已实跑

```
cd /home/pan-ding/workspace/af-wt-phase2-execline && CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-execline -- --ignored
```

关键输出：

```
     Running tests/p2_bridge.rs
test smoke_real_local_docker_via_bridge ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 12 filtered out; finished in 0.05s
     Running tests/p3_judge.rs
test real_judge_fixture_trio_resolved ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4 filtered out; finished in 2.05s
```

**exit 0。** `real_judge_fixture_trio_resolved`（`#[ignore]`，p3_judge.rs:298-343）
在真 `swev-venv` + 现产 `swev-judge.py` 下通过：现产指纹过锚、双判分
`resolved` false→true 翻转实测（2.05s；RESULT-P3 声称 2.0s，相符）。
本机 docker 守护进程在位，故 P2 的 `#[ignore]` 真 docker 冒烟亦通过。

**独立复核（不借被测代码路径，直接驱动真判分器）**——用假代理阻断网络实跑
fixture 三件套，确认判定值确出自 judge stdout 且全程零出网：

```
cd /home/pan-ding/workspace/agent黑灯工厂
env https_proxy=http://127.0.0.1:9 http_proxy=http://127.0.0.1:9 \
    HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 \
    /home/pan-ding/swev-venv/bin/python tools/swev-judge.py <fx>/task.json <fx>/eval.log <fx>/agent.diff
# → {"resolved": false, "log_parsed": true, "f2p_success": 0, "f2p_failure": 1, ...}   exit=0
# eval-ok.log → {"resolved": true,  "log_parsed": true, "f2p_success": 1, ...}        exit=0
```

`sha256sum tools/swev-judge.py` = `a292547f3bfce825b0b44997fd5cc145a5aa7ee89d8533729716c0275950617c`，
与 `judge.rs:47` 的 `production()` 锚字面一致（现产指纹复测通过）。

---

## 2. 判分独立性复核（本包核心；任务书必做项 2）

### 2.1 定位与唯一调用点

- `judge.rs` 模块文档（judge.rs:1-20）明示独立性边界 = 子进程边界，判分一切调用收敛到本模块。
- 全 src 内 `judge::invoke` 的调用点只有一个：`suite/swev.rs:294`
  （`grep -rn "invoke(" src/` 实测：除 judge.rs 自身定义外，仅 swev.rs:294 与两处测试）。
- `check_fingerprint` 在 src 内的调用点只有一个：`suite/swev.rs:227`，位于
  capture_diff / eval.sh 写入 / eval 执行 / judge 调用**全部之前**。

### 2.2 指纹门 fail-loud（EX3002）

`judge.rs:56-70`：`sha256(script)` 与锚比对，不匹配 → `JudgeFingerprintMismatch`
（带 script/expected/actual）；脚本不可读（`sha256_hex` 返回 `None`）→ 同一错误码，
`actual` 填 `"脚本不可读（无法验真）"`。**无降级、无跳判、无静默换脚本分支**；
错误码 `EX3002` 定义于 `error.rs:31,47,63,100`（行号与 RESULT-P3 §1 表一致），
文案含 "fail-loud：拒跑、不降级、不跳判、不静默换脚本"（error.rs:99）。
`error.rs:138-155` 的码表锁定测试钉死 `EX3002` / `JUDGE_FINGERPRINT_MISMATCH`。

**伪造/篡改指纹路径的行为测试（存在且已实跑通过）**：

| 测试 | 篡改手法 | 位置 |
|---|---|---|
| `judge_fingerprint_gate_fail_loud_ex3002` | 锚匹配放行；造**改字节**脚本副本 + 锚仍声明原脚本 → EX3002、实测/声明双指纹进文案；脚本**缺席** = 无法验真同样拒跑 | p3_judge.rs:172-221 |
| `verify_fingerprint_gate_blocks_before_any_work` | 篡改脚本字节后走完整 `verify` → EX3002 进 note、**桥零调用**、run 目录三件套零文件 | p3_verify.rs:480-511 |
| `real_judge_fixture_trio_resolved` | 现产脚本指纹与默认锚严丝合缝才继续，否则 `expect` 失败 | p3_judge.rs:311-312 |

### 2.3 argv 契约钉死（改 argv 是否被测试捕获）

`p3_judge.rs:127-164` 三断言：
① 恰五元素 `[python, script, task_json, log, diff]`（判分脚本恰收三个位置参数），
对抗路径（空格/单引号/`;`/`$HOME`/反斜杠）逐字节穿透；
② 子进程原始 environ 与测试进程 `std::env::vars()` **全等**（`assert_eq!` 整体比较，
零豁免项）；
③ 假 python 的父进程 basename 不属于 `bash/sh/ssh/timeout/dash/zsh`。

**变异实证（改 argv 必被抓）**——我在 `/tmp` 沙箱（`/tmp/afmut`，原树 3.9M 副本，
原仓库零改动）对实现做变异后跑测试：

| 变异 | 结果 |
|---|---|
| M2 `invoke` 里 `.arg(log)` 与 `.arg(diff)` 对调 | **杀死**：`judge_invoke_argv_contract_no_env_injection_no_wrapper_shell` + `verify_timeout_marker_before_hash_and_note_stack` |
| M3 `Command` 链插入 `.env("AF_EXTRA_PROBE","1")` | **杀死**：`judge_invoke_argv_contract_no_env_injection_no_wrapper_shell` |
| M4 改走 `bash -c` 字符串拼接（wrapper shell） | **杀死**：`judge_invoke_argv_contract_no_env_injection_no_wrapper_shell` + `verify_judge_failure_paths_match_bench_messages` |

（沙箱基线先复现 69 passed / 0 failed，与原树一致；变异后立即还原，
`diff` 校验沙箱 == 原树。全部变异用 `cargo test --no-fail-fast`，
否则 fail-fast 会在第一个失败 binary 后停跑、少报杀死集——这点我在 M1 上实测复现过。）

### 2.4 『先产哈希后判』顺序断言

`p3_verify.rs:264-312` `verify_timeout_marker_before_hash_and_note_stack`：
eval 退出 124 → 断言 `eval.log` 末尾恰为 `+ fake eval output line\n\nEVAL_TIMEOUT_KILLED 1800\n`
→ **返回的 `eval_sha256` == 对最终日志字节的独立重算**（测试侧自建 sha2 oracle，
不借用被测 `sha256_hex`）。哈希若先于标记写入，两者必失配。

**变异实证**：

| 变异 | 结果 |
|---|---|
| M5 把 `sha256_hex(&log_path)` 提到标记 append **之前**、并删掉标记后的重算 | **杀死**：`verify_timeout_marker_before_hash_and_note_stack` |
| M7 改标记行文本（`EVAL_TIMEOUT_KILLED` → `EVAL_TIMEOUT_KILLED_NOOP`） | **杀死**：同上 |
| M9 `EVAL_TIMEOUT_SEC` 1800 → 900 | **杀死**：同上 |
| M6 丢 `[log_parsed=false] ` 前缀 | **杀死**：`verify_normal_flow_and_log_parsed_prefix_matrix` + 同上 |
| M8 `capture_diff` 超时 60 → 30 | **杀死**：`capture_diff_command_artifact_and_error_contract` |
| M10 `capture_diff` 命令串丢 `diff' ` 后尾随空格 | **杀死**：`capture_diff_command_artifact_and_error_contract` |
| M1 指纹门恒返回 `Ok(())` | **杀死**：`judge_fingerprint_gate_fail_loud_ex3002` + `verify_fingerprint_gate_blocks_before_any_work` |
| M11 篡改 af-bench 源模板（`judge 启动失败` → `judge spawn failed`） | **杀死**：`cmp_p3_judge_templates_against_bench_source`（漂移报警非空转） |

**11/11 全部杀死**，零存活变异体。

### 2.5 判分输入输出接口未动

`verify` 只往 `work_dir` 写三件套（`eval.sh`/`eval.log`/`agent.diff`），
`task_json_path` 原样直通 judge argv（swev.rs:294）；judge 只读三件套、写不回。
判定值只从 judge stdout JSON 取（`resolved` / `log_parsed`，swev.rs:299-305），
Rust 侧无再解释。

---

## 3. 搬运等价（任务书必做项 3；抽查 12 处 ≥ 5）

方法：`diff <(sed -n 'A,Bp' af-bench/src/swev.rs) <(sed -n 'C,Dp' af-execline/src/suite/swev.rs)`。
先确认迁移源一致：本工作树 `crates/af-bench/src/{swev,tb,main}.rs` 与主仓
`af/crates/af-bench/src/` 对应三文件 `diff -q` **IDENTICAL**（RESULT-P3 §1 声称复测通过）。

| # | 搬运物 | af-bench 源 | af-execline 落位 | 比对结果 |
|---|---|---|---|---|
| 1 | `capture_diff` 取证命令串（含 `diff' ` 后尾随空格） | swev.rs:103-106 | suite/swev.rs:192-195 | 字面逐字节相同；diff 仅 3 处差异：签名加 `bridge` 参数、`tb_ssh`→`bridge.run`、文档注释 |
| 2 | `capture_diff` 超时 60 / 两错误文案 | swev.rs:107,109,113 | suite/swev.rs:196,198,202 | 相同（`60`、`取 diff 失败: {err}`、`写 agent.diff 失败`） |
| 3 | eval 执行链（`const EVAL_TIMEOUT_SEC: u32 = 1800`、`docker exec -i {} bash -s 2>&1`、`timeout {EVAL_TIMEOUT_SEC} {run_cmd}`、local→`bash -c` / 其余→`ssh -o BatchMode=yes`、stdin=eval.sh、stdout=eval.log、stderr=null） | swev.rs:165-186 | suite/swev.rs:249-273 | 语句相同；差异仅 `bridge`→`bridge_script` 更名与注释换行（RESULT-P3 §3-2 已登记） |
| 4 | 超时标记行（`"\nEVAL_TIMEOUT_KILLED {EVAL_TIMEOUT_SEC}\n"`、append 打开、`st.code() == Some(124)`） | swev.rs:191-200 | suite/swev.rs:277-289 | 逐字节相同 |
| 5 | 哈希时机（注释 + `let eval_sha256 = sha256_hex(&log_path);`） | swev.rs:203-204 | suite/swev.rs:290-291 | 相同 |
| 6 | judge 子进程调用（硬编码 Command + 三个 `.arg`） | swev.rs:205-210 | suite/swev.rs:294 + judge.rs:83-88 | 硬编码字面换 locator 字段；argv 形状不变（§2.3 变异实证） |
| 7 | 判定透传与 note 拼装（`resolved` 取值、`[log_parsed=false] ` 前缀、`eval 超时击杀（已落标记 {EVAL_TIMEOUT_SEC}s）；`、`judge: {}`） | swev.rs:216-231 | suite/swev.rs:299-315 | 逐字节相同 |
| 8 | judge stdout 非 JSON 臂（含 `&text[..text.len().min(200)]`） | swev.rs:234-241 | suite/swev.rs:317-324 | 逐字节相同——**多字节边界 panic 风险原样携带**（见 note N1） |
| 9 | judge 退出非零臂（`judge 退出 {}: {}` + stderr 前 300 chars） | swev.rs:244-255 | suite/swev.rs:327-338 | 逐字节相同 |
| 10 | judge 拉起失败臂（`judge 启动失败: {err}`） | swev.rs:256 | suite/swev.rs:339 | 相同 |
| 11 | `sha256_hex` 实现体（`Sha256::digest` + `{byte:02x}` 拼接） | swev.rs:261-266 | suite/swev.rs:346-351 | 函数体逐字节相同；diff 仅可见性 `fn`→`pub(crate)` + 文档注释 |
| 12 | `production()` 两条硬编码路径 + 现产锚 | swev.rs:205-206 | judge.rs:45-48 | 路径字面相同；锚 `a292547f…0617c` 与本机 `sha256sum` 实测一致（§1.2） |

结论：**搬运等价成立**。全部差异集中在方案登记的三类——签名参数化（bridge/locator）、
`tb_ssh`→`bridge.run`、可见性提升——外加新增的指纹门前置（af-bench 无门，
RESULT-P3 §3-1 已登记为偏差）。`sha256_hex` 未造第二个哈希副本：
全 src 内 `Sha256::digest` 仅 1 处（suite/swev.rs:349），judge.rs:57 复用同一函数。

---

## 4. 测试质量扫描 / RESULT-P3.md 声明核对 / clippy / fmt（任务书必做项 4）

### 4.1 空断言 / 同义反复扫描

对全部 5 个测试文件扫 `assert!(true)` / `assert_eq!(true,true)` / `assert!(false)` /
`assert_eq!(1,1)` / `todo!()` / `unimplemented!()` / `// TODO`：**零命中**
（仅 4 处命中均为文件头文档注释里描述"先红后绿"的文字，非断言）。
`grep -c` 计量：p3_judge 46 处 assert / 5 个 `#[test]`，p3_verify 41 处 assert / 7 个 `#[test]`。

反向实证（比静态扫描更强）：§2.3/§2.4 的 11 个变异体全被杀，说明断言确实在考察行为，
不是同义反复。其中 M11 证明 `cmp_p3_judge_templates_against_bench_source`
的"af-bench 漂移即报警"半边非空转。

`cmp_p3_*` 的定位需说准（非缺陷）：它只读 af-bench 源
（`bench_swev_src()`，p3_judge.rs:51-54；实测该函数是文件内唯一的源读取入口，
不读 af-execline 自身实现），因此它是**单向**漂移报警 + 迁移面清单；
af-execline 实现侧的等价由 p3_verify/p3_judge 的行为断言钉死（M6/M8/M9/M10 实证）。

### 4.2 RESULT-P3.md 声明逐条核对

| 声明 | 核对结果 |
|---|---|
| §4 "69 passed / 0 failed" | ✅ 复现一致（14+8+9+15+12+4+7） |
| §4 真 venv fixture "-- --ignored，双判分 2.0s，exit 0" | ✅ exit 0，1 passed，实测 2.05s |
| §1 迁移源"与主仓 swev.rs/tb.rs/main.rs 三文件逐字节一致" | ✅ `diff -q` IDENTICAL ×3 |
| §4 "af-bench / af-workorder / af-engine 零改动"（`git diff 286cc43..HEAD --stat`） | ✅ 输出为空（0 字节），exit 0 |
| §4 RED 基线"435e717 时 p3_judge 3 红/1 过/1 ignore + p3_verify 7 红" | ✅ `git show 435e717` 只增不改（10 文件 +1007 行）；`git show 435e717:crates/af-execline/src/judge.rs` 含 3 处 `unimplemented!()`（44/52/68 行）、`suite/swev.rs` 含 2 处（190/212 行）；现树 `grep -rn "unimplemented!\|todo!()" src/` 零命中。红→绿→重构序列成立（未 checkout，只读 `git show`） |
| §1 `ErrorCode::JudgeFingerprintMismatch` 落位 error.rs:31,47,63,100 | ✅ 四行逐一相符 |
| §2 fixture "两份日志仅差 f2p 的 PASSED/FAILED 一词" | ✅ `diff eval.log eval-ok.log` 仅第 4 行 FAILED↔PASSED |
| §2 fixture task.json "astropy__astropy-12907 裁剪件，f2p/p2p 各一题" | ✅ f2p 1 题 / p2p 1 题；真实 repo/version/base_commit/test_patch |
| §2 fixture "零出网" | ✅ 假代理阻断下判分成功（§1.2 独立实跑） |
| §3-6 "`&text[..text.len().min(200)]` 多字节边界 panic 风险原样携带" | ✅ 属实且已如实登记（af-bench swev.rs:238 ↔ af-execline swev.rs:321） |
| §3-8 "clippy 零新增" | ✅ 见 4.3 |
| §4 "cargo deny --offline check 四类 ok" | ⚠️ **未复跑**（非本次必做项，如实记录为未复核） |
| §1 "未搬 P4-P6 内容" | ✅ `grep -n "judge\|verify\|capture_diff" src/driver.rs` 零命中；`swev::verify` 在 src 内无调用方（仅定义），driver 接线属 P5，与 §1"未搬"清单一致 |

### 4.3 clippy / fmt

```
cd /home/pan-ding/workspace/af-wt-phase2-execline && CARGO_TARGET_DIR=~/afbuild-phase2v cargo clippy -p af-execline --all-targets
warning: the following packages contain code that will be rejected by a future version of Rust: proc-macro-error2 v2.0.1
note: to see what the problems are, use the --future-incompat-report option, or run `cargo report future-incompatibilities --id 1`
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.10s
```

**af-execline 自身 0 警告，exit 0**；唯一提示为第三方 `proc-macro-error2 v2.0.1`
future-incompat（P1 已登记遗留，RESULT-P1.md §3-5），非本包新增——与 §3-8 相符。

```
cd /home/pan-ding/workspace/af-wt-phase2-execline && cargo fmt --check --all
```

**exit 0，零 diff，PASS。**

---

## 5. Notes（不影响验收结论）

- **N1 携带的 panic 风险（已在册）**：`suite/swev.rs:321` 的
  `&text[..text.len().min(200)]` 在 judge stdout 非合法 JSON 且多字节字符恰落在
  200 字节边界时会 panic；af-bench 原版（swev.rs:238）即如此。迁移纪律不顺手修，
  RESULT-P3 §3-6 已登记为后续独立决定。我认可该处理（修了就不是等价迁移），
  但提示 P4+ 若要修，需同时更新 p3_verify.rs:400-401 的行为断言。
- **N2 指纹门的强制力靠约定而非类型**：`lib.rs:47` 把 `judge::invoke`
  以 `judge_invoke` 公开再导出，而 `check_fingerprint` 是独立方法——未来调用方
  （P4/P5）若直呼 `judge_invoke` 而不先过门即可绕过。当前 src 内唯一调用点
  （swev.rs:294）确实先过门（swev.rs:227），且 judge.rs:52-55 模块文档已写明
  "P4 起在单元装载时再调 check_fingerprint()，双重防线"。建议 P4 落实装载期门时
  同步考虑把"不过门不许判分"收到类型/封装里（如返回带门凭证的 wrapper）。
- **N3 指纹门只验脚本字节、不验 python 解释器**：`JudgeLocator` 三字段中
  `python` 与 `script` 都可注入，但 `check_fingerprint` 只哈希 `script`。
  p3_verify.rs:407-408 的注释已如实点明（"指纹门只验脚本"）。venv python 未被
  指纹锚定，属方案 §3.2-2 口径内的既有边界，非本次实现放水。
- **N4 顺序断言的可见边界**：`verify_timeout_marker_before_hash_and_note_stack`
  精确钉死的是"标记先于哈希"与"哈希 == 判分器实际读到的字节"；而"哈希语句先于
  judge 调用语句"这一程序顺序本身不可观测（judge 不改写日志），假想的"先判分后
  哈希"重排仍会通过。可观测契约已满足，记录以备 P4 复核口径。
- **N5 RESULT-P3.md 两处文档性小瑕（非验收项）**：① 文件头写"工作树
  `af-wt-phase2-p2`（分支 `phase2-execline-p3`）"，而本次交付树是
  `af-wt-phase2-execline`（分支 `phase2-execline`，HEAD 4cba6cb）；另有一个独立
  工作树 `af-wt-phase2-p2` 现已在 `phase2-execline-p4`（P4 施工中）。提交图与
  内容对得上，但工作树/分支标识与交付物不符。② §4 记录构建目录
  `~/afbuild-phase2b`，我用的是任务书规定的 `~/afbuild-phase2v`。
- **N6 未复跑项**：`cargo deny --offline check`（RESULT-P3 §4 声称 ok）本次未复跑；
  workspace 全量测试按禁令未跑。除此之外无未实跑项。

---

## 6. 复核方法附注（可复现）

- 变异沙箱：`cp -r crates /tmp/afmut`（3.9M）+ 根 `Cargo.toml`/`Cargo.lock`，
  `CARGO_TARGET_DIR=~/afbuild-phase2v`（热缓存，仅 af-execline 需重编，5.82s）。
  沙箱基线先复现 69 passed / 0 failed，确认与原树等价后才做变异。
- 每个变异施加后立即还原，收尾 `diff` 校验沙箱两个被改文件 == 原树，并通过。
- 全程使用 `cargo test --no-fail-fast`：默认 fail-fast 会在第一个失败 binary 后
  停止后续 binary，导致杀死集少报（M1 上实测复现：首跑只报 p3_judge 一个失败，
  加 `--no-fail-fast` 后才见 p3_verify 的 `verify_fingerprint_gate_blocks_before_any_work`）。
- 原仓库 `git status --porcelain` 开工与收尾均为空，HEAD 恒为 `4cba6cb`——
  验证过程零改动。未写 `计划/变更日志.md`。
