# af-compiler G2b 独立验证报告（stage3 绑定 + stage4 计划 + CLI）

- 验证对象：`/home/pan-ding/workspace/af-wt-phase2-dsl`（分支 `phase2-g2b`，HEAD `e85bfdb`，基线 `824c4b2`）
- 验证范围：`crates/af-compiler/`（`src/components.rs`、`src/bind.rs`、`src/plan.rs`、`src/bin/af-compiler-plan.rs`、`RESULT-G2b.md`、`af/packages/` 三份 `components.json`）
- 验证方式：只读 + 实跑。**未修改任何代码或文档**（唯一例外是本报告文件）；未写 `计划/变更日志.md`（已核对该文件未被本工作树提交过）；构建目录仅 `~/afbuild-phase2v`，未触其他工作树。
- 磁盘纪律：开工 `df -h /` 243G 可用；收工 242G 可用。
- 验证日期：2026-10-24

---

## 结论：**有条件通过**

功能与语义核心全部实跑通过；未通过项集中在**卫生/文档面**，无功能性缺陷。逐项见下。

| # | 必做检查 | 结论 | 关键证据 |
|---|---|---|---|
| 1 | `cargo test -p af-compiler` 核对 53/53 | **通过** | 53 passed / 0 failed，rc=0，逐二进制计数合计 53 |
| 2 | 绑定语义 fail-loud 真实性（E9001/E9002/E9003 探针） | **通过** | 自构 6 个探针全部实跑命中目标码，stdout 恒 0 字节 |
| 3 | 计划确定性 + 内容寻址 + 篡改敏感 | **通过** | 双跑逐位一致；单字符篡改后 dsl_digest/plan_id 变；registry_digest 独立重算一致 |
| 4 | 逃逸注入逐字一致 | **通过** | 6 条 EscapeSpec 五字段全对；无逃逸样例计划 0 条逃逸 |
| 5a | 落地契约 §7.1 一致性（≥10 项） | **有条件通过** | 13 项逐字相符、11 条偏差与文档声明相符；**另有 3 项偏差未列入偏差表** |
| 5b | golden 21 零回归 | **通过** | 21/21 逐字节独立复核 |
| 5c | clippy / fmt | **clippy 通过；fmt 未通过** | clippy 仅 1 条基线既有警告（"零新警告"属实）；`cargo fmt --check` rc=1，去重后 117 处，其中 49 处出自 G2b |

---

## 1. 全量测试：53/53 实跑通过

命令（完整输出落盘，非 `tail` 抽样）：

```
$ cd /home/pan-ding/workspace/af-wt-phase2-dsl
$ CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-compiler > /tmp/g2b_full_test.log 2>&1
rc=0
```

逐二进制计数（`grep "test result"` 求和）：

| 测试目标 | 通过 |
|---|---|
| unittests src/lib.rs | 0 |
| unittests src/bin/af-compiler-plan.rs | 0 |
| unittests src/bin/af-compiler-snapshot.rs | 0 |
| tests/bind_test.rs | 17 |
| tests/golden_test.rs | 11 |
| tests/inline_body_test.rs | 4 |
| tests/ir_schema_test.rs | 8 |
| tests/lower_error_test.rs | 2 |
| tests/plan_test.rs | 7 |
| tests/route_guard_test.rs | 4 |
| Doc-tests af_compiler | 0 |
| **合计** | **53** |

`grep -c FAILED` = **0**。

与 RESULT-G2b 声称完全吻合：新增 bind 17 + plan 7 = 24 例；53 − 24 = **29 例为 G2a/G3 既有**（golden 11 + inline_body 4 + ir_schema 8 + lower_error 2 + route_guard 4 = 29），即 G2a 存量零回归在同一命令内成立。

附带非干扰验证：

```
$ CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-dsl
rc=0   test result: ok. 244 passed; 0 failed
```

与 RESULT-G2b 声称的 244 一致。

---

## 2. 绑定语义复核：fail-loud 真实性（自构 6 探针）

`RESULT-G2b.md:53-56` 声称 E9001/E9002/E9003 各有实跑触发。以下探针由我在 `/tmp` 自构（**未改动仓库任何文件**），基数为 `crates/af-dsl/testdata/sample2.yaml`，全部经 CLI 实跑：

```
$ ~/afbuild-phase2v/debug/af-compiler-plan --registry af/packages <probe>.yaml
```

| 探针 | 构造 | 期望 | 实跑结果 | 判定 |
|---|---|---|---|---|
| A | `route.main@1` → `route.doesnotexist@1` | E9001 | rc=1，3 条违例：`E9001 节点 "architect" 引用 "route.doesnotexist@1"：组件 "route.doesnotexist" 未注册（注册表共 7 条声明）`（pm/build.engineer 同） | ✅ |
| B | `route.main@1` → `route.main@2`（该组件仅声明 v1） | E9002 | rc=1，3 条：`E9002 节点 "architect" 引用 "route.main@2"："route.main" 请求版本 "2" 未声明（已声明：["1"]）` | ✅ |
| C | `tools:` 追加 `pkg.sweng.test_unit@1`（unit 类当 tool 用） | E9003 | rc=1，1 条：`E9003 节点 "build.engineer" 引用 "pkg.sweng.test_unit@1"："pkg.sweng.test_unit"@1 注册类别为 Unit，此处按 Tool 引用` | ✅ |
| D | `route.main@1` → `pkg@@route.main@1`（内嵌 `@`） | E9001 | rc=1，3 条：`E9001 … 引用串不可解析（内嵌 '@'——无法对照注册表）` | ✅ |
| E | 未版本化 `route.main` × 自建双版本注册表（v1+v2） | E9002 歧义 | rc=1：`E9002 … 未版本化引用 "route.main" 命中多版本声明 ["1", "2"]（须带 @version 消歧）` | ✅ |
| F | 不给 `--registry`（空注册表） | E9001 fail-closed | rc=1，8 条：`E9001 … 组件 "route.main" 未注册（注册表共 0 条声明）` | ✅ |

所有探针 **rc=1 且 stdout 恒 0 字节**——失败路径不吐残缺计划，`af-compiler-plan.rs:95-101` 的 fail-loud 路径属实。

**一次收齐**（`bind.rs:180-193`）也获实证：探针 A 单次运行点名 3 个节点，探针 E 一次点名 7 条（3×E9002 + 4×E9001 混合码同批输出）。

**对 components.json 的对照真实性**：注册表共 7 条声明，与三份清单逐一相符——根级 `af/packages/components.json`（`route.main@1`、`route.cheap@1`，model_route 类带 endpoint）、`af/packages/sweng/components.json`（`pkg.sweng.locate/view/edit` 三 tool + `pkg.sweng.test_unit` unit）、`af/packages/swarmkit/components.json`（`pkg.swarmkit.tools` tool，external_once）。

负例（承 RESULT-G2b 声称）：

```
$ af-compiler-plan --registry af/packages crates/af-compiler/testdata/src/Voyager.yaml
rc=1  stdout=0 字节
计划生成失败：绑定未过（1 条 E900x 违例）：E9001 节点 "explore.observe" 引用 "pkg.openworld.env@1"：组件 "pkg.openworld.env" 未注册（注册表共 7 条声明）
```

### E9004 保留位说明是否如实：**属实**

- `bind.rs:51-59` 的 `BindCode` 枚举**只有 3 个变体**（RefMissing/VersionMismatch/ClassMismatch），`as_str()` 只产 E9001/E9002/E9003——编译期确无 E9004 生产者。
- 全仓 grep：E9004 仅出现在文档注释（`bind.rs:25,50,165`、`components.rs:184`、`plan.rs:80`）与 `plan_test.rs:84` 的注释，无任何产出逻辑。
- 职责划分与契约一致：`落地契约-v0.md:138` 明写"引用缺失/版本不符/digest 不匹配**一律拒绝启动**"，即执行面装载职责；`registry_digest` 由编译期产出并随 `compiled_from.registry_digest` 携带（`plan.rs:79-82`）。RESULT-G2b 遗留项 1 将核对器归 af-execline，与契约不冲突。

---

## 3. 计划确定性独立复核（含篡改实证）

### 3.1 双跑逐位一致

两个输入：**sample2**（`crates/af-dsl/testdata/sample2.yaml`，裸校验链）与 **GPTSwarm**（`crates/af-compiler/testdata/src/GPTSwarm.yaml`，对齐稿，`--registry` 注入链）。

```
$ af-compiler-plan --registry af/packages <yaml> > a.json   # 第一次
$ af-compiler-plan --registry af/packages <yaml> > b.json   # 第二次
$ cmp a.json b.json
```

| 输入 | rc | 字节 | 双跑 `cmp` |
|---|---|---|---|
| sample2 | 0 | 13221 | 逐位一致 |
| GPTSwarm | 0 | 33499 | 逐位一致 |

字节数与 RESULT-G2b 声称的 13221/13595/33499 完全吻合（sample3 另跑 13595 亦一致）。

### 3.2 内容寻址

```
sample2   : plan_id = plan.metagpt_sop@1.0+d8ad1058d270
            dsl_digest       = d8ad1058d27036cf78c136c0872b4ddce05cb2480d3cd12ce83809408afa1e2d
            registry_digest  = 6ec9210b7188df428c7049b553bf4ca9d41aa82fc94eaa838212619b8dea8306
GPTSwarm  : plan_id = plan.gptswarm_candidate_graph@1.0+16f9891c3bef
            dsl_digest       = 16f9891c3bef43e2e9ea81d1d90d20b85fe2858025e03ab4dd175ccfa05de894
            registry_digest  = 6ec9210b…（同上，同注册表根）
```

- `plan_id` = `plan.<图名>@<图版本>+<dsl_digest 前 12 位>`（`plan.rs:349-350`）：两份计划均验证 `plan_id.endswith("+"+dsl_digest[:12])` 为真。
- `digest_of` = `hex(&Sha256::digest(bytes))`（`lower.rs:404-406`），即纯 SHA-256 小写十六进制；dsl_digest/registry_digest 均 64 位 hex。

**`registry_digest` 独立重算（内容寻址硬证据）**——用 Python 复算 `components.rs:272-278` 的规范序列化（7 条声明按 `(name,version)` 字典序、`ComponentDecl` serde 字段序、`Option` 空值显式序列化为 `null`）：

```
computed: 6ec9210b7188df428c7049b553bf4ca9d41aa82fc94eaa838212619b8dea8306
plan    : 6ec9210b7188df428c7049b553bf4ca9d41aa82fc94eaa838212619b8dea8306
MATCH: True
```

（注：首轮复算不符，原因是我的 Python 字典漏了 `EndpointSpec` 的 `max_tokens/temperature_milli/top_p_milli` 三个 `Option` 空位；补齐 serde 字段集后逐位吻合。这一番周折本身佐证 digest 覆盖的是**完整规范序列化**而非源文件字节。）

### 3.3 篡改探针（单字符）

```
$ cp crates/af-dsl/testdata/sample2.yaml /tmp/probe_sample2.yaml
$ sed -i 's/max_items: 128/max_items: 129/' /tmp/probe_sample2.yaml     # 第 59 行，改 1 个字符
$ diff crates/af-dsl/testdata/sample2.yaml /tmp/probe_sample2.yaml
59c59
<     retention: { max_items: 128 }
---
>     retention: { max_items: 129 }

$ af-compiler-plan --registry af/packages /tmp/probe_sample2.yaml
rc=0
篡改后 : plan_id = plan.metagpt_sop@1.0+fe8e7e924662
         dsl_digest = fe8e7e9246627a1533450270e7fda0c858a3ccb759592a260b0705331c7d6fd9
原稿   : plan_id = plan.metagpt_sop@1.0+d8ad1058d270
         dsl_digest = d8ad1058d27036cf78c136c0872b4ddce05cb2480d3cd12ce83809408afa1e2d
```

**dsl_digest 与 plan_id 均变**（`d8ad1058d270` → `fe8e7e924662`），而 `registry_digest` 保持 `6ec9210b…` 不变——正确：注册表未动，只 DSL 动了。**同源重跑 digest 不变**由 3.1 的双跑一致覆盖。

---

## 4. 逃逸注入：6 条 EscapeSpec 逐字一致

草稿 `crates/af-compiler/testdata/src/GPTSwarm.yaml` 含 6 处 `escape:` 构造。用脚本逐字段比对草稿 vs 计划 `.body.escapes`：

| 草稿节点 | 计划键 | kind | owner | pct | impl_ref |
|---|---|---|---|---|---|
| dispatch | `search.dispatch` | runtime_context_mutation | lang-team | 6 | `packages/swarmkit@1.0.0/hatches/dispatch.py` |
| py_node | `search.execute_map.py_node` | program_synthesis | lang-team | 6 | `packages/swarmkit@1.0.0/hatches/py_node.py` |
| reward | `search.reward` | llm_predicate | eval-team | 8 | `packages/swarmkit@1.0.0/hatches/reward_fn.py` |
| optimize | `search.optimize` | meta_loop | rl-team | 15 | `packages/swarmkit@1.0.0/hatches/policy_search.py` |
| graph_edit | `search.graph_edit` | program_synthesis | lang-team | 10 | `packages/swarmkit@1.0.0/hatches/graph_edit.py` |
| graph_value | `search.graph_value` | program_synthesis | lang-team | 4 | `packages/swarmkit@1.0.0/hatches/graph_value.py` |

**ALL 6 VERBATIM (kind/impl_ref/reason/owner/share_budget_pct): True**——五个字段全部逐字相同（`reason` 长文案亦逐字比对通过）。计划键 = 节点点号路径，与 `bind.rs:161-169`/`plan.rs:471` 的透传设计一致。

工具节点绑定亦核实：

```
$ jq '.body.node_exec[] | select((.components.tools|length)>0) | {node_id, tools}'
{"node_id":"search.execute_map.tool_exec","tools":[{"reference":"pkg.swarmkit.tools@1","effect_class":"external_once"}]}
```

### 无逃逸样例：不含 EscapeSpec 条目

```
sample2 : escapes_present=true, escapes_value={}, escape_entry_count=0
sample3 : escapes_present=true, escapes_value={}, escape_entry_count=0
GPTSwarm: escapes_present=true, escape_entry_count=6
```

**如实说明（一处需要精确表述的细微差别）**：无逃逸样例的计划中 `escapes` **键仍在场但值为空对象、0 条 EscapeSpec**。这是 schema 自包含性使然（`PlanBody` 恒序列化该字段，`plan.rs:66-67`），不是"残留逃逸数据"。若按"不含任何 EscapeSpec 内容"理解，则**通过**；若按"该块应整体缺席"理解，则**不符**——契约 §7.1 草案本无此块（偏差表 #2），故前者是合理解读。sample1/sample5 因引用未注册组件被 E9001 fail-closed 拒（rc=1，stdout 0 字节），无法产出计划，故未纳入本项。

---

## 5. 与落地契约 §7.1 一致性抽查

对照源：`计划/研究组/落地契约-v0.md:374-432`（§7.1 顶层结构草案）。

### 5.1 逐字相符项（13 项）

| # | 项 | 契约 | 实跑 |
|---|---|---|---|
| 1 | 拒绝式信封 | `{"v":1,"body":...}` | 顶层键恰 `["v","body"]`，`v=1` |
| 2 | `deny_unknown_fields` 装载纪律 | 信封 + 未知字段拒绝 | plan.rs 22/25 型带该属性（例外为 3 个非序列化型：`PlanPriority`/`PlanError`/`PlanParseError`）；components.rs 3/9（序列化面 `ComponentDecl`/`ComponentsFile`/`EndpointSpec` 全覆盖）。`plan_test.rs::plan_envelope_is_rejecting` 实证四情形（v=2/未知顶层键/缺 v/body 未知字段） |
| 3 | `plan_id` | 本计划标识 | 在场，`plan.<名>@<版本>+<12 位 hex>` |
| 4 | `compiled_from` 三键 | dsl_digest / compiler_version / graph_version | 三键在场（`compiler_version` = `0.1.0`） |
| 5 | `line` 三键 | line_id / line_version / domain_pack_digest | 逐字相符（三值 null） |
| 6 | `order` 11 键 | id/stable_id/run_id/state/graph_version/line/budget_voucher/artifacts/sla/supersedes/history | 逐字相符，键序一致 |
| 7 | `order.sla` | {deadline, priority} | 逐字相符 |
| 8 | `order.state` | `"Created"` | `"Created"` |
| 9 | `graph` 五键 | graph_version/name/entry/nodes/edges/subgraphs | 逐字相符 |
| 10 | `node_exec` 六键 | node_id/unit/components/budget/artifact_contract/retry | 逐字相符 |
| 11 | `node_exec.components` 五键 | model_route/loop_policy/memory/tools/context_compaction | 逐字相符 |
| 12 | `resources` | {gates, limits} | 键相符（恒空，偏差 #4） |
| 13 | `observation` 及 otel/events/mes 子键 | span_tree/ctx_propagation/otel{enabled,endpoint,batch_size}/events{root_env,line,index,manifest}/mes{endpoint_ref,database,line_id,station_id} | **全部逐字相符**，含草案示例值（otel 512、`AF_OBS_ROOT`、`env:MES_CH_URL`/`af_mes`） |

### 5.2 与偏差表声明相符项（11 条全部核对）

RESULT-G2b 偏差表（`RESULT-G2b.md:71-85`）列 11 条，逐条与实跑产物核对：#1 tools 对象数组、#2 增补 stores/types/interface/escapes 四块、#3 budget = IR 三账（budgets/stop/failures）、#4 resources 恒空、#5 observation 草案默认骨架、#6 recovery、#7 retry/qualified_by 恒 null、#8 order 占位、#9 sla.priority 仅 Normal、#10 引用串现实形、#11 plan_id 派生式——均如实。

### 5.3 未列入偏差表的出入（3 项）——本报告的主要文档缺陷

偏差表自称"与落地契约 §7.1 草案的出入"全集，但实跑发现以下差异**未在表中登记**（`grep` 证实 `selector`/`registry_digest`/`provenance` 在偏差表段落均无命中）：

| # | 差异 | 契约 §7.1 | 实现 | 评估 |
|---|---|---|---|---|
| a | `compiled_from` 多第 4 键 | 仅 dsl_digest/compiler_version/graph_version | 增加 `registry_digest` | 有正当理由（§2.2 E9004 携带面），且在结构体清单与 E9004 节有文字说明，但**未入偏差表** |
| b | `node_exec.unit` 缺 `selector` | `{unit_id, unit_version, selector}` | `UnitBinding` 仅 `{unit_id, unit_version}`（`plan.rs:163-167`） | **契约字段缺失**，RESULT-G2b 全文未提及（`selector` 仅以 `topology_selector` 形式出现） |
| c | `node_exec.budget` 形状 | 单对象 `{dimension, unit, per_turn, node_cap}` | 数组 `[{id, dimension, cap}]`（`plan.rs:193-198`，实跑该数组为空） | 形状不符且未登记 |
| d | `artifact_contract[]` 多 `provenance` | {name, is_final, qualified_by} | 增加 `provenance` | 有正当理由（ADR-010），但未入偏差表 |

b/c 属于"声称完备实则不完备"——偏差表作为对接面契约的可审计性因此打折扣。建议补登，不影响运行正确性。

---

## 6. golden 21 零回归独立复核

不依赖 `cargo test`，改用 CLI 独立重编译全部 21 份源并与 golden 逐字节 `cmp`：

```
$ cd /home/pan-ding/workspace/af-wt-phase2-dsl
$ for n in <17 份 G3_CORPUS>; do af-compiler-snapshot <yaml> | cmp - golden/<stem>.ir.json; done
$ for n in ADAS AutoGen-Team-JSON GPTSwarm MetaGPT; do
    af-compiler-snapshot --registry af/packages <yaml> | cmp - golden/<stem>.ir.json; done

=== INDEPENDENT GOLDEN RE-VERIFY: 21/21 byte-exact, 0 failures ===
```

- 17 份裸链（ReAct/Reflexion/Voyager/SWE-agent/MemGPT/CAMEL/Multi-Agent-Debate/AFlow/LangGraph-StateGraph/CrewAI-YAML/Agensh-DeLM + sample1-6）+ 4 份 selector 注入链（ADAS/AutoGen-Team-JSON/GPTSwarm/MetaGPT）= 21，与 `golden_test.rs:218,386` 的两个语料数组一致。
- 与测试内的 11 个 golden 测试（含 2 个篡改检测）互相独立，结论一致。
- **af-dsl 与 golden 零改动**已核实：`git diff 824c4b2..HEAD --stat -- crates/af-dsl crates/af-compiler/testdata` 输出为空。
- G2b 提交范围文件清单（`git diff 824c4b2..HEAD --name-status`）：A `af/packages/components.json`、A `af/packages/swarmkit/components.json`、A `af/packages/sweng/components.json`、A `crates/af-compiler/RESULT-G2b.md`、A `src/bin/af-compiler-plan.rs`、A `src/bind.rs`、A `src/components.rs`、M `src/lib.rs`、M `src/lower.rs`、A `src/plan.rs`、A `tests/bind_test.rs`、A `tests/plan_test.rs`、M `af/packages/README.md`。工作树 `git status --porcelain` 为空（我只在 `/tmp` 落探针）。

---

## 7. clippy / fmt

### clippy：**通过**（"零新警告"属实）

```
$ CARGO_TARGET_DIR=~/afbuild-phase2v cargo clippy -p af-compiler --all-targets
warning: doc list item without indentation
   --> crates/af-compiler/tests/golden_test.rs:256:5
    = help: if this is supposed to be its own paragraph, add a blank line
    = note: `#[warn(clippy::doc_lazy_continuation)]` on by default
warning: `af-compiler` (test "golden_test") generated 1 warning
Finished `dev` profile ... rc=0
```

仅 1 条警告，位于 `golden_test.rs:256`——该文件已核实与基线 `824c4b2` **逐字节相同**（`cmp` 通过），即 G2a 既有基线警告。**G2b 新增/改动的 6 个源码文件与 2 个测试文件零新警告**，"clippy 零新警告"声称属实。

### fmt：**未通过**

```
$ CARGO_TARGET_DIR=~/afbuild-phase2v cargo fmt -p af-compiler -- --check
rc=1
```

**计数口径说明**：`grep -c "^Diff in"` 得 120 行，但其中 `tests/common/mod.rs:4` 同一处被 4 个测试目标（`mod common;` 被 bind_test/golden_test/inline_body_test/ir_schema_test/plan_test/route_guard_test 各自跟随）重复报告 4 次。**去重后唯一 hunk 数为 117**（`grep "^Diff in" | sort -u | wc -l` = 117）。下表用去重口径。

分文件归因（`cargo fmt --check` 输出 `sed 's/:[0-9]*:$//' | sort | uniq -c`；仓库无 `rustfmt.toml`，edition = 2021）：

| 文件 | 唯一 hunk 数 | G2b 是否改动 | 归属 |
|---|---|---|---|
| `tests/golden_test.rs` | 24 | 否（与基线逐字节相同） | 基线既有 |
| `src/lower.rs` | 20 | 是（+8 行） | 基线既有（见下） |
| `tests/bind_test.rs` | 15 | 新增 | **G2b 新增** |
| `src/plan.rs` | 12 | 新增 | **G2b 新增** |
| `tests/plan_test.rs` | 11 | 新增 | **G2b 新增** |
| `tests/inline_body_test.rs` | 10 | 否 | 基线既有 |
| `tests/route_guard_test.rs` | 8 | 否 | 基线既有 |
| `src/components.rs` | 7 | 新增 | **G2b 新增** |
| `src/decode.rs` | 3 | 否 | 基线既有 |
| `src/bind.rs` | 3 | 新增 | **G2b 新增** |
| `tests/ir_schema_test.rs` | 2 | 否 | 基线既有 |
| `tests/common/mod.rs` | 1 | 否 | 基线既有 |
| `src/lib.rs` | 1 | 是 | **G2b 新增** |
| `src/bin/af-compiler-plan.rs` | 0 | 新增 | 干净 |
| **基线既有小计** | **68** | — | — |
| **G2b 新增小计** | **49** | — | — |
| **合计** | **117** | — | 68+49=117 精确闭合 |

`lower.rs` 归属为"基线既有"的实证：G2b 对其改动仅 8 行（`hex` 加 `pub(crate)` + 新增 `digest_of` 函数），对基线与 HEAD 两份内容分别跑 `rustfmt --edition 2021 --check` 均为 **20 处**——G2b 的增补未引入新 fmt 偏差。

`lib.rs` 归属为"G2b 新增"的实证：该唯一 hunk 在 `lib.rs:22`，是 G2b 新增的 `pub use bind::{...}` 再导出行超宽（`grep -A12 "src/lib.rs:"` 实证）；基线 lib.rs 自身 0 处（其模块子文件的偏差由各子文件自身承载）。

**基线既有 68 处的论证不依赖重跑基线**：`golden_test.rs`/`inline_body_test.rs`/`route_guard_test.rs`/`ir_schema_test.rs`/`common/mod.rs`/`decode.rs` 六个文件 G2b **完全未触碰**，且已用 `git show 824c4b2:<path>` + `cmp` 核实与基线逐字节相同——内容既同，fmt 状态必然相同，故其偏差必为基线既有。

**判定**：
- `cargo fmt --check` 客观上**不干净**（rc=1）。
- 但 **RESULT-G2b.md 全文不含任何 fmt 声称**（`grep -n fmt RESULT-G2b.md` 无命中）——这是**遗漏而非虚假声称**，与 clippy 那条"只声称 clippy"的处理一致。
- 值得记录的是：G2b 自己新增的 49 处占去重总量 117 的 42%，而同期新增的 CLI `af-compiler-plan.rs` 反而是全 crate 唯一 0 处的新文件——说明同一包内卫生执行不一致。

---

## 8. 其他文档准确性发现

**结构体计数错误**：`RESULT-G2b.md:29` 标题为"新增 29 型 + 1 常量 + 1 CLI"，提交信息 `e85bfdb` 同样写"结构体清单 29 型"。但：

- 该标题下的表格实际列出 **38 个具名类型 + 1 个常量**（`PLAN_VERSION`）；
- 实际代码 `src/components.rs` + `src/bind.rs` + `src/plan.rs` 共 **41 个 `pub struct`/`pub enum`**（38 具名 + `OtelSlot`/`EventsSlot`/`MesSlot`，后三者被表格中"（+Otel/Events/Mes 三槽）"括注覆盖）；
- 表格列举与代码**无缺无溢**（`table types missing from code: NONE`），即表格本身准确，错的是标题数字（应为 41，而非 29）。

属计数笔误，不影响代码正确性；但因该数字同时进了提交信息，建议修正以免下游引用。

---

## 9. 总体评价与建议

**立得住的**（全部实跑，非引述）：
1. 53/53 全绿，G2a 存量 29 例与 af-dsl 244 例零回归，golden 21/21 逐字节独立复核通过。
2. E900x fail-loud 真实：6 个自构探针（未注册/错版本/类别不符/坏引用/版本歧义/空注册表）全部命中目标码，一次收齐，stdout 恒 0 字节。
3. 计划双层确定性真实：双跑逐位一致；单字符篡改使 dsl_digest 与 plan_id 变、registry_digest 不变；`registry_digest` 被独立重算逐位复现。
4. 逃逸注入链真实：6 条 EscapeSpec 五字段逐字一致，键为节点点号路径；无逃逸样例 0 条。
5. §7.1 顶层结构 13 项逐字相符，11 条偏差声明与产物相符；拒绝式信封四情形有测试实证。
6. E9004 保留位说明如实（编译期无生产者、执行面核对、契约 §2.2 出处相符）。

**需整改的**（按严重度）：
1. **fmt 不干净**（`cargo fmt --check` rc=1，去重后 117 处：基线既有 68 + G2b 新增 49）。RESULT-G2b 未声称 fmt，故非虚假声称，但卫生未达标；建议 `cargo fmt` 后区分"基线既有 68 处"与"本包新增 49 处"分别处置。
2. **偏差表不完备**：`compiled_from.registry_digest`、`node_exec.unit` 缺 `selector`、`node_exec.budget` 形状、`artifact_contract[].provenance` 四项未登记。其中 `unit.selector` 是契约字段缺失且全文未提，最应补。
3. **结构体计数笔误**：29 型 → 实为 41 型。

**未做/无法验证的**（如实声明）：
- E9004 执行面核对器在 af-execline，不在本包范围，本报告未验证。
- `capability_refs`/`trust`、`context_template`/`policy`、`qualified_by` 静态推导等遗留项（RESULT-G2b 遗留 2/3/4）属 v0.1 无数据源，本报告未验证其"未来兑现"，仅验证其在当前产物中确为空占位。
- 计划 golden 快照入库（遗留 6）未做，RESULT-G2b 明示归 G3，非本包缺陷。

---

## 附：本报告实跑命令索引

| 目的 | 命令 |
|---|---|
| 全量测试 | `CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-compiler` |
| af-dsl 非干扰 | `CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-dsl` |
| 构建 CLI | `CARGO_TARGET_DIR=~/afbuild-phase2v cargo build -p af-compiler --bin af-compiler-plan --bin af-compiler-snapshot` |
| 计划双跑 | `~/afbuild-phase2v/debug/af-compiler-plan --registry af/packages <yaml>` ×2 + `cmp` |
| 绑定探针 | 同上，输入为 `/tmp/probe{A,B,C,D,E}_*.yaml`、`/tmp/probe_reg/` |
| 逃逸比对 | Python 脚本解析 `GPTSwarm.yaml` 的 6 处 `escape:` 块 vs `jq .body.escapes` |
| golden 复核 | `~/afbuild-phase2v/debug/af-compiler-snapshot [--registry af/packages] <yaml> \| cmp - golden/<stem>.ir.json` |
| registry_digest 复算 | Python 重建 7 条声明规范序列化 → SHA-256 |
| clippy | `CARGO_TARGET_DIR=~/afbuild-phase2v cargo clippy -p af-compiler --all-targets` |
| fmt | `CARGO_TARGET_DIR=~/afbuild-phase2v cargo fmt -p af-compiler -- --check`（原始 120 行 → `sort -u` 去重 117 处） |
| fmt 归属 | `grep "^Diff in" \| sed 's/:[0-9]*:$//' \| sort \| uniq -c`；G2b 未触碰文件用 `git show 824c4b2:<path> \| cmp -` 证内容相同 |

报告撰写过程中未修改 `crates/af-compiler/` 与 `af/packages/` 任何文件；所有探针产物均落在 `/tmp`。
