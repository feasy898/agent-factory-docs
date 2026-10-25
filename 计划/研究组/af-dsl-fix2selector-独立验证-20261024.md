# fix2（三守卫+勘误）与 selector 组件（registry+packages）独立验证报告

- 验证者：独立测试代理（与实现者无涉，只读+实跑，未改任何代码/文档）
- 对象：`/home/pan-ding/workspace/af-wt-phase2-dsl`，分支 `phase2-dsl-int`，HEAD `8fed107`（merge: fix2+selector 汇流；父提交 `01ae160` 勘误、`9f8719e` 三守卫实装）
- 基线：phase2-dsl-int @`8fed107`（任务给定）
- 日期：2026-10-24
- 资源纪律：开工 `df -h /` → `/dev/nvme0n1p2 468G 198G 246G 45% /`（246G 可用）；构建 `CARGO_TARGET_DIR=~/afbuild-phase2v`；未触其他工作树；`git status --short` 空（仓库零改动，佐证见 §7）

## 0. 结论三态

| 项 | 判定 | 依据 |
|---|---|---|
| **fix2 三守卫（E2002/E2004/E2322）** | **通过（PASS）** | 自构 24 例全新形态违规/正例实跑，码精确；正例零误伤（§2） |
| **selector registry 安全性** | **通过（PASS）** | 空 registry 反例复现（3/6/3/3 条 E2001）；manifest 静态拒绝 10 例；注入面无隐式放行（§3） |
| **文档勘误（执行语义规范 3 处 + E2210→E1002）** | **通过（PASS）** | 三处高报已改且与实装逐条对上；E2210 确不在 af-dsl 码表、escape 四字段缺一实为 E1002（§4） |
| **golden 17 未被新守卫拒绝** | **通过（PASS）** | `g3_golden_corpus_byte_exact` 绿；另用 CLI 独立复核 17/17 逐字节相等（§5） |
| **270 测试基线** | **通过（PASS）** | 实跑 270 passed / 0 failed / 0 ignored（§1） |
| **clippy / fmt** | **通过（PASS，附存量债说明）** | clippy 1 条存量 doc 警告（未触碰文件）；四个新文件 fmt 全 clean，fmt 差异全在未触碰的存量文件（§5） |

**总判定：通过（无阻塞缺陷，无必须修复项）。** 附 3 条非阻塞观察（§6）。

---

## 1. 实跑测试基线（核对 270）

**命令**（在 `/home/pan-ding/workspace/af-wt-phase2-dsl` 下）：

```
CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-dsl -p af-compiler
```

**输出**（exit=0）：

```
TOTAL: passed=270 failed=0 ignored=0
```

逐二进制明细（`grep -E "^     Running|^test result"` 配对）：

| 二进制 | passed | | 二进制 | passed |
|---|---|---|---|---|
| af_compiler（lib 单测） | 0 | | af_dsl cel_test | 10 |
| af_compiler_snapshot（bin 单测） | 0 | | af_dsl envelope_test | 11 |
| af-compiler golden_test | **8** | | af_dsl inv1_test | 37 |
| af-compiler inline_body_test | 4 | | af_dsl inv2_test | 9 |
| af-compiler ir_schema_test | 8 | | af_dsl inv3_test | 10 |
| af-compiler lower_error_test | 2 | | af_dsl inv4_test | 12 |
| af-compiler route_guard_test | 4 | | **af_dsl loop_guard_test（fix2 新增）** | **18** |
| af_dsl（lib 单测） | 0 | | af_dsl m4_test | 15 |
| | | | af_dsl parse_test | 37 |
| | | | af_dsl refs_test | 37 |
| | | | **af_dsl registry_test（selector 新增）** | **20** |
| | | | af_dsl route_test | 18 |
| | | | af_dsl selector_test | 10 |
| | | | Doc-tests af_compiler / af_dsl | 0 / 0 |

- af-compiler 小计 **26**（8+4+8+2+4）+ af-dsl 小计 **244**（10+11+37+9+10+12+18+15+37+37+20+18+10）= **270**，与给定基线一致。
- 附：`CARGO_TARGET_DIR=~/afbuild-phase2v cargo check --workspace` → `Finished dev profile`（全 workspace 通过，其余 crate 未受影响）。

---

## 2. 三守卫判定真实性（E2002 / E2004 / E2322）

### 2.1 被测代码落点（只读核对）

- `crates/af-dsl/src/validate/loop_guard.rs:26` — `if decl.max_iterations == 0` → `ErrorCode::ValueOutOfRange`（E2002）
- `crates/af-dsl/src/validate/loop_guard.rs:33` — `if decl.safety_points.is_empty()` → `ErrorCode::EmptyCollection`（E2004）
- `crates/af-dsl/src/validate/loop_guard.rs:40-51` — `for c in decl.carried.iter().flatten()` + `if c.max_items.is_none() && c.max_bytes.is_none()` → E2002
- `crates/af-dsl/src/validate/inv3.rs:23-24` — `is_verifier` = `kind ∈ {check, gate} ∪ human 标记`
- `crates/af-dsl/src/validate/inv3.rs:57-88` — `check_safety_points`：`SafetyPointKind::Check → kind=="check"`、`Gate → kind=="gate"`、`Human → human.is_some()`（三值原样）；不匹配 → `SafetyPointNotVerifier`（E2322）；路径不可解析 `continue`（E2107 域）
- 编排位：`crates/af-dsl/src/validate/mod.rs:80`（`loop_guard::check` 在 refs 之后、inv1 之前），E2322 走 inv3 族
- 类型约束：`crates/af-dsl/src/model.rs:437` `max_iterations: u32`（**无 serde default → 必填**）；`model.rs:465/467` `max_items/max_bytes: Option<usize>`（皆可缺省）；`model.rs:440` `safety_points: Vec<SafetyPointDecl>`（**必填，无 default**）
- 码位登记：`crates/af-dsl/src/error.rs:50`（ValueOutOfRange/E2002）、`error.rs:55`（EmptyCollection/E2004）、`error.rs:128`（SafetyPointNotVerifier/E2322）

### 2.2 自构违规/正例实跑（24 例，全部为仓库夹具未覆盖的新形态）

**方法**：在被测仓库**之外**建独立 harness（`/tmp/afv-harness`，path 依赖 `crates/af-dsl`，`CARGO_TARGET_DIR=/tmp/afv-target`），仓库内 `git status` 全程为空。命令：

```
cd /tmp/afv-harness && CARGO_TARGET_DIR=/tmp/afv-target cargo run --offline --bin afv   # 三守卫 24 例
cd /tmp/afv-harness && CARGO_TARGET_DIR=/tmp/afv-target cargo run --offline --bin edge   # 边界行为 5 例
```

**反例（码精确）**：

| # | 形态（全新，仓库 `loop_guard_test.rs` 18 例均未覆盖） | 实跑码 | 关键输出 |
|---|---|---|---|
| V1 | `max_iterations` 字段整个缺省 | `["E1002"]` | `shape rejected:E1002 missing_field[document]: missing field \`max_iterations\`` |
| V2 | `max_iterations: -1`（负数） | `["E1004"]` | `invalid value: integer \`-1\`, expected u32` |
| V3 | `max_iterations: null` | `["E1003"]` | `invalid type: unit value, expected u32` |
| V4 | `max_iterations: 0.5`（非整数） | `["E1003"]` | `invalid type: floating point \`0.5\`, expected u32` |
| V5 | 安全点 `kind=gate` 指向 **check** 节点（与仓库夹具的 check→gate 反向） | `["E2322"]` | `loop l1 安全点 "c"（kind=gate）指向节点 l1.c（kind="check"，human=false）非对应验证面` |
| V6 | 安全点 `kind=check` 指向 **human 标记**节点 | `["E2322"]` | `…指向节点 l1.h（kind="task"，human=true）非对应验证面` |
| V7 | 安全点 `kind=gate` 指向 **human 标记**节点 | `["E2322"]` | 同上（human=true） |
| V8 | 两个安全点，仅第二个指向 task | `["E2322"]`（恰一个） | `loop l1 安全点 "w"（kind=gate）指向节点 l1.w（kind="task"…）` |
| V9 | 安全点路径**穿嵌套 map 体**（`m.inner_task`）指向 task | `["E2322"]` | `…指向节点 l1.m.inner_task（kind="task"，human=false）` |
| V10 | 安全点指向 **loop 拥有者自身**（出体路径 `l1`） | `["E2107"]` | `loop "l1" 安全点路径 "l1" 从体根逐层解析失败` |
| V11 | **嵌套内层** loop 的 `safety_points: []` | `["E2004"]` | `loop l1.inner 未声明任何安全点（safety_points 为空，拒绝编译）` |
| V12 | `carried` 两项，仅第二项缺上界 | `["E2002"]`（恰一个） | `loop l1 carried 条目 store "t" 无上界（max_items/max_bytes 至少其一）` |
| V13 | `carried` 三项全缺上界 | `["E2002","E2002","E2002"]` | 三条分别定位 `s`/`t`/`u` |
| V14 | 嵌套 loop 三守卫并犯（内层 `max_iterations:0` + 空安全点 + carried 无上界） | `["E2002","E2004","E2002"]` | 首条 `loop l1.inner 的 max_iterations = 0` |
| V15 | `safety_points` 字段整个缺省 | `["E1002"]` | `missing field \`safety_points\`` |
| V16 | 外层合法、**内层** carried 无上界（双 loop 并列） | `["E2002"]` | `loop outer.inl carried 条目 store "s" 无上界` |

**正例（不误伤）**：P1 `carried: [{store: s, max_items: 0}]`（`Some(0)` 视为已声明）→ `[]`；P2 `carried: []` → `[]`；P3 `max_iterations: 1` → `[]`；P4 两个合法安全点（gate+check）→ `[]`；P5 穿嵌套 map 体的合法 gate 安全点 → `[]`；P6 嵌套双层 loop 均合法 + 跨层安全点 → `[]`；P7 `max_iterations: 4294967295`（u32::MAX）→ `[]`；P8 `carried: [{store: s, max_bytes: 0}]` → `[]`。**8/8 零误伤。**

**边界行为（另 5 例，`bin edge`）**：

| # | 形态 | 实跑码 | 说明 |
|---|---|---|---|
| E1 | 同作用域重复节点 id `l1`，首声明 loop `max_iterations:0`、次声明 loop 合法 | `["E2003","E2002"]` | 与文档「重复 id 时首声明者胜（E2003 已报），被跳过的节点不再定罪」一致——只报首声明者的 E2002，次声明者的合法 loop 未被定罪也未漏报 |
| E2 | **map 体内**的 loop `max_iterations:0` | `["E2001","E2001","E2002"]` | E2001 系本夹具 `entry: l1` 未随节点迁到 `m.l1`（夹具自身问题）；守卫本身覆盖 map 体循环（`loop m.l1 的 max_iterations = 0`） |
| E3 | 深层嵌套 loop>map>loop，最内层 `safety_points: []` | `["E2004"]` | 定位 `loop outer.mm.deep 未声明任何安全点`；外层跨体合法安全点不误伤 |
| E4 | 空 loop 体（`nodes: []`）+ `max_iterations:0` + 空安全点 | `["E2002","E2004"]` | E1007（空体）未实装如文档所述，空体现由 E2004 事实上挡住 |
| E5 | 全合法 + `exit_when` + `on_exhausted` | `[]` | 不误伤 |

**小结**：16 个反例中 12 个走语义层精确单码/确定码序（E2002×4 形态、E2004×2 形态、E2322×5 形态），4 个（V1/V2/V3/V4/V15 中的形状类）在**装载层**被 `u32`/必填性挡下并给出精确码（E1002/E1003/E1004）——三守卫本身只管 `== 0`，负数/缺省不可能抵达语义层，这不是缺口（形状层先拒），但**意味着「max_iterations 负数/缺省」这一验证诉求实际由 E1002/E1003/E1004 兑现，而非 E2002**。E2322 的三值严格口径（交叉错配亦拒）与 af-graph `validate.rs:453-456` 的 `kind_ok` 判定逐条同构（§4.3 复核）。

---

## 3. registry 安全性（selector 装载组件）

### 3.1 被测代码落点

- `crates/af-dsl/src/registry.rs:91` `PackageManifest`（`deny_unknown_fields`）、`:112` `parse`、`:136` `validate`（静态校验）、`:178` `graph_refs`
- `crates/af-dsl/src/registry.rs:195` `Registry`、`:203` `load`（目录扫描+排序+跨包重复）、`:266` `options()`（注入 `ValidateOptions`）
- 注入面唯一消费点：`crates/af-dsl/src/validate/m4.rs:463-489` `selector_candidates`；`is_versioned` 形校验在 `m4.rs:475`，`declared_graphs.contains(name)` 在 `m4.rs:481`
- `crates/af-dsl/src/validate/mod.rs:58` `validate()` 恒传 `ValidateOptions::default()`；`:71` `declared_graphs: BTreeSet<String>`（默认空集）

### 3.2 空 registry 时 4 稿仍被拒（反例复现）

**命令**：

```
cd /tmp/afv-harness && CARGO_TARGET_DIR=/tmp/afv-target cargo run --offline --bin reg
```

草稿取自 `计划/研究组/对齐草稿/{ADAS,AutoGen-Team-JSON,GPTSwarm,MetaGPT}.yaml`（该 4 份**不在** golden 17 语料内——golden 语料是另外 11 份编译干净的草稿）。

| 草稿 | 默认 opts（= 空 registry）codes | E2001 条数 |
|---|---|---|
| ADAS.yaml | `["E2001","E2001","E2001"]` | 3 |
| AutoGen-Team-JSON.yaml | `["E2001","E2001","E2001","E2001","E2001","E2001"]` | 6 |
| GPTSwarm.yaml | `["E2001","E2001","E2001"]` | 3 |
| MetaGPT.yaml | `["E2001","E2001","E2001"]` | 3 |

关键输出（逐条点名候选图，非笼统一码）：

```
topology_selector rules[0].use 候选图 "pkg.adaskit.discovered_maze@1" 未在已声明的版本化图/子图集内
topology_selector fallback 候选图 "pkg.adaskit.mas_search@1" 未在已声明的版本化图/子图集内
```

与 `RESULT-selector.md` ③ 节「注入前 3/6/3/3 条」逐数一致。**反例复现成立。**

**注入 af/packages 后**（同一 harness，`Registry::load(af/packages).options()`）：4 稿 codes 全部 `[]`，E2001 归零；`package_count=4`、`declared_graphs` 14 条。

### 3.3 manifest 静态校验拒绝路径（10 例，超过要求的 ≥3）

| # | 构造 | 实跑结果 |
|---|---|---|
| C1 | 坏 JSON（trailing comma） | `manifest 非法：trailing comma at line 1 column 77` |
| C2a | 顶层未知字段 `extra` | `manifest 非法：unknown field \`extra\`, expected \`package\` or \`graphs\`` |
| C2b | graphs 条目未知字段 `homepage` | `manifest 非法：unknown field \`homepage\`, expected one of \`name\`, \`version\`, \`source\`` |
| C3 | 同清单内重复图名（`pkg.zz.dup@1` 两次） | `manifest 非法：图引用 "pkg.zz.dup@1" 在同清单内重复声明` |
| C4 | 同清单内重复点号分层名（`pkg.zz.a.b@1` 两次） | 同上形态，组合引用判重 |
| C5 | `graphs: []` 空清单 | `manifest 非法：graphs 至少声明一项（manifest 唯一职责 = 声明图）` |
| C6 | 缺 `package` | `manifest 非法：missing field \`package\`` |
| C7 | 顶层是数组而非对象 | `manifest 非法：invalid type: string "graphs", expected a sequence` |
| C8 | 跨包重复引用（两目录、同 `package` 名 + 同 `name@version`） | `图引用 "pkg.samepkg.same@1" 重复声明：/tmp/afv-reg-dup/pa 与 /tmp/afv-reg-dup/pb` |
| C9 | 包目录缺 `manifest.json` | `包目录缺少 manifest.json：/tmp/afv-reg-nomanifest/stray_pkg` |

附：C10 空根（只含 `.gitkeep`/`README.md`）→ `package_count=0`、`declared_empty=true`、`options_declared_empty=true`（fail-closed，非目录条目跳过）。

> 说明：任务书写「坏 toml」，但 manifest 规范选的是 **JSON**（`registry.rs:8-10` 注明 serde_json 已在依赖面内、`af/packages/README.md`「选 JSON」）。故 C1 按坏 JSON 构造；TOML 路径在本实装中不存在，无从验证也不适用。

### 3.4 注入面无隐式放行

**全仓检索**（`grep -rn "declared_graphs\|validate_with" --include=*.rs --include=*.sh --include=*.py`，排除 registry.rs 自身）：`declared_graphs` 的唯一消费点是 `m4.rs:481`；`validate_with` 的仓内调用方只有 `crates/af-dsl/tests/*`；`af-compiler/src/lower.rs` 仅在注释中提到 `topology_selector`（无第二处核对）。**无第二实现、无旁路。**

实跑（默认 opts，每条文档含 `rules[0].use` + `fallback` 两个引用，故期望 `["E2001","E2001"]`）：

| 候选引用 | 默认 opts codes |
|---|---|
| `pkg.adaskit.discovered_maze@1`（**已在 af/packages 声明**） | `["E2001","E2001"]` |
| `pkg.adaskit.mas_search@1`（已声明） | `["E2001","E2001"]` |
| `pkg.nosuchpkg.graph@9` | `["E2001","E2001"]` |
| `pkg.adaskit.discovered_maze`（非版本化形） | `["E2001","E2001"]` |
| `pkg.adaskit.discovered_maze@`（空版本） | `["E2001","E2001"]` |
| `@1`（空名） | `["E2001","E2001"]` |
| `sub.adaskit.discovered_maze@1`（前缀夹带） | `["E2001","E2001"]` |
| `pkg.adaskit.discovered_maze@1 `（尾随空格） | `["E2001","E2001"]` |

**已声明候选在不注入时同样被拒 → 无隐式放行、无默认豁免。** 反向注入后：`pkg.adaskit.discovered_maze@1` → 0 条 E2001；`pkg.nosuchpkg.graph@9` → 1 条（fallback 已声明，仅 use 拒）；`pkg.adaskit.discovered_maze`（非版本化）→ 1 条。注入面是纯放行、按精确串匹配。

### 3.5 af/packages 四示例包实装核对

`adaskit`(3) / `autogen`(5) / `swarmkit`(3) / `sweng`(3) = **14 条**版本化引用，并集恰为：

```
pkg.adaskit.discovered_maze@1, pkg.adaskit.discovered_wordle@1, pkg.adaskit.mas_search@1,
pkg.autogen.team.graph_flow@1.0, pkg.autogen.team.magentic_one@1.0, pkg.autogen.team.round_robin@1.0,
pkg.autogen.team.selector@1.0, pkg.autogen.team.swarm@1.0,
pkg.swarmkit.graph.fanout_vote@1.4, pkg.swarmkit.graph.plan_execute_review@2.1, pkg.swarmkit.graph.react_baseline@1.0,
pkg.sweng.sop_full@1.0, pkg.sweng.sop_minimal@1.0, pkg.sweng.sop_no_qa@1.0
```

与 4 稿 `topology_selector` 的 use+fallback 引用逐字一致（与 `registry_test.rs` 的 `DRAFT_REFS` 闭包一致，本报告独立重算得到同一 14 条集合）。每个 manifest 均通过 `PackageManifest::parse` 静态校验；`source` 均为相对定位串、非空。

---

## 4. 文档勘误核对

### 4.1 执行语义规范 §1.1 / §1.2 / §1.3 三处高报（已改且与实装一致）

文件：`crates/af-compiler/docs/执行语义规范-v0.md`（勘误提交 `01ae160`）。现行文本与实装逐条对照：

| 规范位置 | 现行表述 | 实装核对（本报告实跑） | 一致？ |
|---|---|---|---|
| §1.1 迭代边界 | 「`max_iterations > 0` 编译期已强制（缺失 → E1002 形状层拒绝；`= 0` → E2002 值域拒绝——fix2/P2-L08 起实装，af-dsl `validate/loop_guard.rs`）」 | `sample6.yaml` 把 `max_iterations: 200` 改 `0` → `E2002: loop explore 的 max_iterations = 0（迭代上限必须 >0）`；删该字段 → `shape rejected:E1002 missing_field: missing field \`max_iterations\`` | ✅ |
| §1.2 carried 重建 | 「每项必须有界（max_items/max_bytes 至少其一——E2002 值域拒绝…承 af-graph `CarriedState::is_bounded` 口径：`Some(0)` 视为已声明上界；与 E2211 覆盖性互补不重复）」 | sample6 删 inner carried 的 `max_items: 512` → `E2002: loop explore.acquire carried 条目 store "skill_library" 无上界`；`max_items: 0` / `max_bytes: 0` 单独声明 → 零违例（`Some(0)` 口径成立） | ✅ |
| §1.3 安全点 | 「非空编译期已强制（缺失 → E1002；为空 → E2004；且每项必须指向验证面节点——E2322，kind 三值…；路径悬空仍归 E2107）」 | 删 safety_points 条目 → `E2004: loop explore.acquire 未声明任何安全点`；把 `admit` 换成 `generator`（task）→ `E2322: …安全点 "generator"（kind=gate）指向节点 explore.acquire.generator（kind="task"…）`；换成 `nope` → `E2107: …安全点路径 "nope" 从体根逐层解析失败`；删整个 `safety_points` 键 → `E1002 missing field \`safety_points\`` | ✅ |
| 头部版本行 | 增补「同日 fix2/P2-L08 勘误——§1.1/§1.2/§1.3 三处『编译期已保证』由 G2a 独立验证实测为高报…」 | 已存在（第 4 行） | ✅ |

另核对 `crates/af-compiler/docs/保证边界矩阵.md` §2 L1 loop 行：已落码「max_iterations 必填（E1002）且 >0（E2002）、carried 每项至少一上界（E2002…）、safety_points 缺失（E1002）/为空（E2004）拒绝且每项指向验证面节点（E2322…；路径悬空归 E2107）」，并注记原高报与 fix2 实装；与本报告 §2 实跑逐条吻合。

**勘误实证命令**（`/tmp/afv-harness/src/bin/errata.rs`）：

```
cd /tmp/afv-harness && CARGO_TARGET_DIR=/tmp/afv-target cargo run --offline --bin errata
# 输出：baseline sample6 codes=[]；四字段各缺一均 E1002；1.1/1.2/1.3 六项全中；ALL ERRATA CHECKS PASSED
```

### 4.2 E2210 → E1002 引用正确性

- **E2210 不在 af-dsl 码表**：`grep -n "E2210\|2210" crates/af-dsl/src/error.rs` 无命中（ErrorCode 枚举无此变体），与勘误注记「E2210 为提案 §6 保留码位」一致。
- **escape 四字段缺一实为 E1002**：`crates/af-dsl/src/model.rs:548-560` `EscapeDecl` 的 `impl_ref`/`reason`/`owner`/`share_budget_pct` 四个必填字段（仅 `kind` 可选），serde `deny_unknown_fields` + 缺字段 → `E1002 missing_field`。本报告对 sample6 的 escape 段逐字段删除实跑：

```
drop escape.impl_ref        -> LOAD_ERR: shape rejected:E1002 missing_field: missing field `impl_ref`
drop escape.reason          -> LOAD_ERR: shape rejected:E1002 missing_field: missing field `reason`
drop escape.owner           -> LOAD_ERR: shape rejected:E1002 missing_field: missing field `owner`
drop escape.share_budget_pct-> LOAD_ERR: shape rejected:E1002 missing_field: missing field `share_budget_pct`
```

- `保证边界矩阵.md:40` 逃逸舱行已改引 E1002 并注明 E2210 系保留码位；`model.rs:548` 自注同述。**引用正确。**

### 4.3 附带交叉核对（af-graph 共享码族）

RESULT-fix2.md 声称 E2002/E2004 与 af-graph 共享码位、E2322 三值承 af-graph `kind_ok` 原样。实读 `crates/af-graph/src/validate.rs`：

- `:405-412` `if lp.max_iterations == 0` → `ErrorCode::ValueOutOfRange`（该枚举 `:63` 映射 `"E2002"`）✅
- `:415-421` `if !lp.carried_state.is_bounded()` → `ValueOutOfRange`（E2002）；`model.rs:92-95` `is_bounded` = `max_items.is_some() || max_bytes.is_some()` ✅（af-dsl `loop_guard.rs:41` 同口径）
- `:427-432` `if lp.safety_points.is_empty()` → `EmptyCollection`（`:65` 映射 `"E2004"`）✅
- `:453-456` `kind_ok = match sp.kind { Check => bn.kind == CHECK, Gate => bn.kind == GATE, Human => bn.human.is_some() }` —— 与 af-dsl `inv3.rs:67-71` 的 match 逐分支同构 ✅

（注：af-graph 把 kind 错配归 `ValueOutOfRange`/E2002，af-dsl 归 `SafetyPointNotVerifier`/E2322。文档措辞是「kind **三值语义**承 af-graph 原样」，指的是判定口径而非码位，E2322 的码位来源在提案 §6 E23xx 段——两者不矛盾，非缺陷。）

---

## 5. golden 17 / clippy / fmt

### 5.1 golden 17 未被新守卫拒绝（双路独立复核）

**路一（任务点名的 cargo test 段）**：

```
CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-compiler --test golden_test
# running 8 tests ... test result: ok. 8 passed; 0 failed; 0 ignored
# 含：g3_golden_corpus_byte_exact ... ok   （17 份语料重编译与 golden 逐字节相等）
#     six_golden_samples_pass_full_validation ... ok
#     g3_golden_corpus_manifest_closed ... ok
#     g3_golden_tamper_detection ... ok
```

`g3_golden_corpus_byte_exact` 对 `G3_CORPUS`（17 份，`golden_test.rs` 内闭集清单）逐份 `load_str → validate（全量零违例才继续）→ lower → pretty 序列化` 与 `testdata/golden/*.ir.json` 逐字节比对。**17 份全过 = 无一被新守卫拒绝，且 IR 快照零改动。**

**路二（本报告自建 CLI 独立复核，绕开测试 harness）**：

```
cd crates/af-compiler && for f in testdata/src/*.yaml; do
  ~/afbuild-phase2v/debug/af-compiler-snapshot "$f" | printf '%s\n' "$(cat)" | cmp -s - "testdata/golden/$(basename "$f" .yaml).ir.json"
done
# === golden byte-exact: ok=17 bad=0
# === src count: 17, golden count: 17
```

`af-compiler-snapshot` 的装载纪律与 golden 测试同口径（`load → validate（全量零违例）→ lower → pretty + writeln`），退出码非零即拒。**17/17 通过、17/17 逐字节相等、17 份源与 17 份 golden 目录清点一致。** 实现者自报「零拒绝」得到独立确认。

### 5.2 clippy

```
CARGO_TARGET_DIR=~/afbuild-phase2v cargo clippy -p af-dsl -p af-compiler --all-targets
```

→ **1 条警告**，全仓仅此一条：

```
warning: doc list item without indentation
   --> crates/af-compiler/tests/golden_test.rs:256:5
    = note: `#[warn(clippy::doc_lazy_continuation)]` on by default
```

`golden_test.rs` 未被 fix2/selector 触碰（fix2 的 `git diff` 只涉及 af-dsl 侧文件与两份 docs；selector 只加 af-dsl 侧 + af/packages）。**零新增警告。**

### 5.3 fmt

对 fix2/selector 触及与新增的源文件逐个 `rustfmt --check --edition 2021`：

| 文件 | 结果 |
|---|---|
| `crates/af-dsl/src/validate/loop_guard.rs`（新） | **CLEAN** |
| `crates/af-dsl/src/validate/inv3.rs` | **CLEAN** |
| `crates/af-dsl/src/registry.rs`（新） | **CLEAN** |
| `crates/af-dsl/tests/loop_guard_test.rs`（新） | **CLEAN** |
| `crates/af-dsl/tests/registry_test.rs`（新） | **CLEAN** |
| `crates/af-dsl/src/error.rs` | **CLEAN** |
| `crates/af-dsl/src/validate/mod.rs` | DIFF 10 hunks |

对 mod.rs 的 10 hunks 逐条定位：**全部落在 `inv1.rs`(1) / `m4.rs`(5) / `mod.rs:154`(1) / `refs.rs`(3)** —— `mod.rs:154` 是 `self.walk(&lp.body.nodes, …)` 的长行拆分，位于 fix2 对该文件的 diff（仅第 1-8 行模块注释、第 13 行 `mod loop_guard;`、第 80 行 `loop_guard::check`）之外，属未触碰的存量行。af-dsl 其余 fmt 差异（`cel.rs`/`model.rs`/`route.rs`/`shape.rs`/各 `tests/*.rs`）同样全在存量文件，四个新文件零差异。**fix2/selector 未新增 fmt 债。**

---

## 6. 观察项（非阻塞，不建议在本任务内改动）

1. **`max_iterations` 负数/缺省不由 E2002 兑现。** `model.rs:437` 是 `u32` 必填，负数和缺省在装载层即被 `E1004`/`E1003`/`E1002` 挡下，`loop_guard.rs:26` 的 `== 0` 永不看到它们。执行语义规范 §1.1 已如实写成「缺失 → E1002；`= 0` → E2002」，故非文档缺陷；但若下游按「E2002 = 迭代上限值域唯一码」做监控聚合，会把负数/缺省类漏在该码之外。属可选的码位归口议题，非正确性问题。
2. **安全点指向 loop 拥有者自身 → E2107 而非 E2322。** V10 实测：路径从体根解析失败（拥有者在体外），归 refs 域。与规范 §1.3「路径悬空仍归 E2107」的表述一致，但「安全点指向一个真实存在、只是出体的节点」这条路径的报错码是 E2107（悬空），信息里不会提示「该节点是 loop 属主」。可读性层面的小瑕疵。
3. **空 loop 体（`nodes: []`）无独立码位。** E4 实测：空体 + `max_iterations:0` + 空安全点 → `["E2002","E2004"]`，E1007 未实装如 `RESULT-fix2.md` §6 所述。规范 §1.3 因此事实上挡住了「空体循环」（无节点可作安全点），语义安全，但若后续要显式区分「空体」与「缺安全点」需落 E1007。

---

## 7. 资源与纪律证据

- `df -h /home/pan-ding`：`/dev/nvme0n1p2 468G 198G 246G 45% /`（开工即查，246G 可用）
- 构建目标目录：`CARGO_TARGET_DIR=~/afbuild-phase2v`（本报告全部 cargo 调用均显式设置）；harness 另用 `/tmp/afv-target`，两者均未写入被测工作树
- 工作树状态：验证全程 `cd /home/pan-ding/workspace/af-wt-phase2-dsl && git status --short` → **空**（HEAD 恒 `8fed107`）；本报告未写入该树任何文件
- 独立 harness 建于 `/tmp/afv-harness`（path 依赖被测 `crates/af-dsl`，`[workspace]` 空表独立成项），4 个 bin：`afv`（三守卫 24 例）、`reg`（registry 10+10+5 例）、`errata`（勘误实证 11 项）、`edge`（边界 5 例）。全部含 `assert!` 断言，退出码均为 0
- 未触 docker / 网络 / 工厂守护进程；未写 `计划/变更日志.md`
- 未修改任何被测代码或文档；唯一写入物为本报告（`计划/研究组/af-dsl-fix2selector-独立验证-20261024.md`）

## 8. 本报告实跑命令索引

| 检查 | 命令 | 结果 |
|---|---|---|
| 270 基线 | `CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-dsl -p af-compiler` | 270 passed / 0 failed |
| workspace 影响 | `CARGO_TARGET_DIR=~/afbuild-phase2v cargo check --workspace` | Finished |
| golden 段 | `CARGO_TARGET_DIR=~/afbuild-phase2v cargo test -p af-compiler --test golden_test` | 8 passed |
| golden CLI 独立复核 | `crates/af-compiler` 下 17 份 `af-compiler-snapshot` + `cmp` 对 golden | ok=17 bad=0 |
| 三守卫 | `cd /tmp/afv-harness && CARGO_TARGET_DIR=/tmp/afv-target cargo run --offline --bin afv` | 24 例全中 |
| 三守卫边界 | `… --bin edge` | 5 例全中 |
| registry | `… --bin reg` | 25 项断言全过 |
| 勘误实证 | `… --bin errata` | 11 项全中 |
| clippy | `CARGO_TARGET_DIR=~/afbuild-phase2v cargo clippy -p af-dsl -p af-compiler --all-targets` | 1 条存量警告 |
| fmt | 逐文件 `rustfmt --check --edition 2021` | 4 个新文件 CLEAN |
