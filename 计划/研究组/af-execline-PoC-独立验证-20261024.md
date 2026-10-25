# af-execline 订单生命周期 PoC 独立验证报告（P2-F01 验证侧）

> 验证者：独立验证代理（af-execline独立验证者）｜日期：2026-10-24
> 对象：`/home/pan-ding/workspace/af-wt-phase2-order/crates/af-execline/`（src/ 全部 7 文件 + tests/lifecycle.rs + RESULT.md）
> 验证时 HEAD：`44b7f17`（分支 phase2-order，工作树 clean——`git status --short` 无输出）
> 方法：只读代码 + 本会话实跑命令，未修改任何代码与文档（本报告除外）。实现代理 RESULT.md 自评仅作声明清单，不构成通过依据；以下每条结论均附命令与证据。

## 0. 资源纪律（ADR-009）

- 开工 `df -h /`：468G 总量，已用 398G，**可用 47G（90%）**——高于 15G 阈值，开工放行。
- 全部构建只落 `CARGO_TARGET_DIR=~/afbuild-phase2`（会话前 7.5G → 会话后 7.7G）；主仓 `af/target` 不存在、未创建、未触碰。
- 除任务书允许的抽查（`-p af-workorder`）外未跑其他 crate 测试，未跑 workspace 全量。

## 1. 验收测试实跑

命令（任务书原文形式，本会话独立执行）：

```
cd /home/pan-ding/workspace/af-wt-phase2-order && CARGO_TARGET_DIR=~/afbuild-phase2 cargo test -p af-execline
```

关键输出：

```
running 14 tests                          ← lib 单测
test result: ok. 14 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
running 8 tests                           ← tests/lifecycle.rs 集成
test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
running 0 tests                           ← doc-tests
test result: ok. 0 passed; 0 failed; ...
```

**结果：22 通过 / 0 失败（lib 14 + integration 8 + doc 0）**，与 RESULT.md §2 声明的 "lib 14 + integration 8 + doc 0" 一致。lib 14 例的模块分布（源码清点：clock 2 + error 2 + engine 2 + ledger 2 + mes 1 + exec 1 + driver 4 = 14）与运行输出逐条对应。

抽查另一 crate（任务书允许范围，用于 §3 的 687 声明核验）：

```
CARGO_TARGET_DIR=~/afbuild-phase2 cargo test -p af-workorder
→ 49+3+4+3+3 = 62 passed / 0 failed（lib + calendar_sla + identity + json_snapshots + lifecycle + doc 0）
```

## 2. 测试质量审查

通读 `tests/lifecycle.rs`（526 行 8 例）与 src 内 7 个 `#[cfg(test)]` 模块（14 例）。

### 2.1 空断言 / 同义反复 / 被注释断言 / 伪负向 搜索

- 被注释的断言：`grep -rn "^\s*//\s*assert" crates/af-execline/` → **无匹配**。
- 空断言：未发现（22 例逐条过目，每例至少一条实质 `assert_eq!`/`assert!` 带失败消息）。
- 同义反复断言：未发现纯自我比较。一处边界观察见 N5。
- 伪负向（只测快乐路径的"负向"）：未发现——四个关键负向用例全部真实驱动引擎或账本并断言了**类型化拒绝形态**（逐一核对见 2.2）。

### 2.2 四个负向用例逐一核对

| 用例 | 是否真驱动引擎 | 断言的拒绝形态 | 判定 |
|---|---|---|---|
| ② 门控拒绝 `release_without_voucher_is_typed_gate_rejection_not_panic`（lifecycle.rs:216-247） | 是。create_order+bind_line 后直接 `driver.release()`，release 是 `engine_step`（driver.rs:190-195）→ 真子进程调 `Op::Release`（af-engine/src/lib.rs:230 → af-workorder order.rs:405-425 门控） | `EngineRejected{op:"release"}` + `EngineRejection::Gate` 且 `missing()==[BudgetVoucherNotIssued]`（类型化清单）、稳定码 `EX1006`、状态停在 `Created`、账本有 `!ok` 行（`error_kind=="gate"`、无快照） | 真负向 |
| ③ close 拒绝 `close_without_qualified_final_artifact_is_rejected`（lifecycle.rs:280-324） | 是。走完 release/start/complete 后无工件 `driver.close()` → `Op::Close`（engine lib.rs:237 → order.rs:425 `NoQualifiedFinalArtifact`） | `missing()==[NoQualifiedFinalArtifact]`、`EX1006`、停在 `Completed`；随后补工件重试 close 放行、`close` 成功记录唯一 | 真负向，且带恢复路径 |
| ④ 幂等重放 `second_drive_replays_without_duplicate_terminal`（lifecycle.rs:329-377） | 是。首驱走通后 drop，**重新 open 同一 out_dir**（ledger 重载恢复，driver.rs:84-129），二次 `drive()` 全流程 | `second.replayed==true`、终态 `Closed` 不变、history 长度不增、`second.mes_events` 为空、账本 `close` 成功记录仍唯一、`replay_skip` 审计行存在、重载后序号 1..N 连续、MES 文件仍恰 4 条 | 真驱动（重放语义经真实进程重启边界） |
| ⑦ ledger 断层 `ledger_seq_gap_is_rejected_as_corrupt`（lifecycle.rs:430-485） | 驱动的是账本校验层（`OrderLedger::load`，ledger.rs:75-124）——本用例的对象是存储损坏而非引擎，层次恰当 | 手造 seq=1,3 账本 → `EX2002` + "序号不连续"；混入异单记录 → `EX2002` + "身份不一致"；另有第 ⑧ 例（lifecycle.rs:490-525）从驱动层 `open` 断异单账本（`EX2002`），覆盖了 load 之上的入口 | 真负向 |

附带负向 ⑥（执行单元失败可重试，lifecycle.rs:382-425）：FailingUnit 真返回 `EX3001`，断言订单停 `InProgress`、`!ok` 的 `attach_artifact` 入账、重试后成功记录唯一——真实。③′ 未签名凭证点名（lifecycle.rs:250-275）：断言 `missing()==[BudgetVoucherNotSigned{voucher_id:"bv-wo-gate-2"}]`——真实（引擎侧 order.rs:412 确有此门）。

### 2.3 测试质量备注（均非阻断）

- **N1（弱断言）**：RESULT.md §2 用例 5 声称"工件文件不重写"，但测试只断言 `artifact_file.is_file()`（lifecycle.rs:374-376），无 mtime/调用计数证明未重写。代码路径上重放早退确实不调 `unit.execute`（driver.rs:208-216 直接从快照重建 `ExecOutput`，note="replay: 工件已登记，未重跑执行单元"），且 MES 空、replay_skip 在账可间接佐证；但"文件未重写"这一句没有直接断言载体。
- **N5（边界观察）**：happy_path 中 `report.order.stable_id() == StableId::generate("wo-happy-1")`（lifecycle.rs:146-150）对 af-workorder 自身近乎同义反复，价值在于钉住"execline 不自搞 ID 方案"的跨 crate 收敛回归——算契约钉，不算伪断言。

## 3. RESULT.md 声明逐条核对

| # | 声明（RESULT.md 位置） | 核对证据 | 结论 |
|---|---|---|---|
| 1 | `work_order_id == stable_id`（§2 用例 1，ADR-004 收敛） | 代码：driver.rs:397-412 `emit_mes` 以 `stable_id` 作 `MesEvent::new` 首参，`af_mes::MesEvent` 首字段即 `work_order_id`（af-mes/src/event.rs:11）；测试：lifecycle.rs:196-201 断言全部事件 `work_order_id == stable_id`；实跑绿 | **属实** |
| 2 | MES 事件恰含 release/start/complete/close 四类（§2 用例 1） | 代码：`MES_TRANSITION_KINDS`（driver.rs:34）且 `emit_mes` 仅在 release/start/complete/close 四个方法调用（driver.rs:192,200,255,262——全文件仅此四处）；测试：lifecycle.rs:190-195 断言排序后恰为 `["close","complete","release","start"]`（4 条各一，不多不少）；实跑绿 | **属实** |
| 3 | ledger 序号连续、可重载（§1/§2） | 代码：序号由账本盖、fsync 后才更新内存（ledger.rs:140-158）；重载校验序号 1 起连续 + 全账本身份一致（ledger.rs:95-122）；测试：lifecycle.rs:159-162（首驱）、367-369（重放后）断言 seqs==1..=N，ledger.rs:207-235 往返单测；实跑绿 | **属实** |
| 4 | workspace 测试 "687 passed / 0 failed，78 target"（§6 step3） | 见下方专项分析 | **可信但无树内产物背书**（N2） |
| 5 | git 先红后绿序列：`4821921` 红 → `d08ec25` 绿 → refactor（§1 表） | `git log` 三笔俱在且顺序相符；RED 提交形态实证：`git grep -c "unimplemented!" 4821921` → driver 10 + engine 2 + exec 1 + ledger 3 + mes 2 = 18 处桩，同时 tests/lifecycle.rs 8 例已全量在场（该提交 11 文件 +1494 行） | **序列属实**；RED 态具体计数（lib 4 failed/6 passed 等）未复跑（需检出旧提交，禁止改动工作树），以提交形态佐证（N3） |
| 6 | "9-op 单行 JSON 协议"（§1） | af-engine/src/lib.rs:166-174 恰 9 个 op（bind_line/attach_voucher/release/start/attach_artifact/complete/close/cancel/approve_decision）；execline 驱动其中 7 个（create_order 是本地构造不调引擎，driver.rs:154-174） | **属实** |
| 7 | 判定走真引擎子进程、不打桩（§1/§2） | engine.rs:183-263 每次 op 拉起 `Command::new(bin)` 子进程一行协议；测试断言 `engine_bin().ends_with("af-engine")`（lifecycle.rs:152-156）；`~/afbuild-phase2/debug/af-engine` 存在（14.1MB，2026-10-24 14:38 构建），本会话 22 例全过即实际走了该二进制 | **属实** |

### 3.1 "687 passed" 可信度专项

树内 `ci/out/step3.log`（guardrail-fix2 代际产物，最后入库于 `94cd192`，**早于 af-execline 三笔提交**）：

```
grep -c "test result: ok" ci/out/step3.log        → 75
awk 汇总 passed → 665, failed → 0
grep -c "af_execline\|af-execline" ci/out/step3.log → 0（旧产物不含本 crate）
```

算术自洽：**665 + 22（af-execline lib 14 + integration 8 + doc 0 的 3 个 target 计 22 例）= 687**；75 + 3（本 crate 新增 lib/lifecycle/doc 三 target）= 78。独立抽查：af-execline 22/22 绿、af-workorder 62/62 绿，未见任何失败。

判定：**687 声明可信（量级、算术、抽查三方面吻合）**，但记 **N2**：RESULT.md §6 step3 行表述为 2026-10-24 的 workspace 重跑，而树内归档日志仍是入库前旧产物（665/75），该次 687 运行没有留在树内的产物证据；按任务书本验证未复跑 workspace 全量（资源纪律），以抽查 + 旧日志算术佐证。

## 4. 健康度

| 检查 | 命令（本会话实跑） | 输出/退出码 | 结果 |
|---|---|---|---|
| clippy | `CARGO_TARGET_DIR=~/afbuild-phase2 cargo clippy -p af-execline --all-targets`（ask 所名 `-p af-execline` 的超集，含 lib+tests） | `Finished dev profile ... in 0.34s`，无任何 warning 行，exit 0 | **零警告** |
| fmt | `cargo fmt --check -p af-execline` | 无 diff 输出，exit 0 | **通过** |

（RESULT.md 另声明 workspace 级 `fmt --all` / clippy workspace 全绿——本验证按任务书范围只跑 `-p af-execline`，workspace 级未复跑，见 N4。）

## 5. 结论

### **PASS-with-notes**

核心验收全部独立复证：22/22 测试实跑通过；四个负向用例（门控拒绝/close 拒绝/幂等重放/ledger 断层）均为真实驱动 + 类型化拒绝形态断言，无空断言、无被注释断言、无同义反复伪测试；RESULT.md 四项关键声明（stable_id 收敛 / MES 四类 / ledger 连续可重载 / 引擎子进程不打桩）逐条与代码、测试、实跑对上；clippy/fmt 干净。

**问题清单（notes，均非阻断）**：

- **N1** 「工件文件不重写」声明强于测试断言（仅 `is_file()`，无未重写直接证据；代码路径确无重跑）。
- **N2** 「687 passed/78 target」为 2026-10-24 重跑声明，树内 `ci/out/step3.log` 仍是 af-execline 入库前旧产物（665/75、零次出现本 crate），该次运行无归档证据；算术（665+22、75+3）与抽查全绿使其可信，但证据链缺一环。
- **N3** RED 态失败计数（lib 4 failed/6 passed；integration 8 failed/0 passed）未复跑——复跑需检出历史提交，与"禁改工作树"冲突；以 RED 提交形态（18 处 `unimplemented!()` 桩 + 全量测试在场）佐证。
- **N4** fmt/clippy 的 workspace 级（`--all`）声明未独立复跑（任务书范围限定 `-p af-execline`，该范围全绿）。
- **N5** stable_id 断言属跨 crate 契约钉，对 af-workorder 自身近乎恒真——记录性质，不算缺陷。

**已知边界（沿用实现者 RESULT.md §3/§4 自报，本次核对底层事实属实，不算新发现）**：

- GateRejection 镜像：底层事实已核对——`af-workorder/src/error.rs:51` `MutationForbidden { op: &'static str }` 确为 `&'static str` 借用字段，镜像（engine.rs:32-48）线格式同名同形、`deny_unknown_fields` + 未知变体 fail-loud（engine.rs:314-323 有专测）。
- MES stub 无 outbox / 无 ClickHouse：属实（mes.rs 为纯 JSONL 文件 writer）。
- approve_decision 未纳入：属实——引擎侧存在该 op（af-engine/src/lib.rs:174），execline 驱动层未接入（driver.rs 无对应方法）；cancel 边同样未驱动。

**未做/做不到的检查（如实声明）**：workspace 全量 687 复跑（任务书豁免为抽查）；RED 态计数复跑（禁改工作树）；与 orchestration/ Python 演示链的语义对照（RESULT.md §4 提及、任务书未列入本次必做项）。
