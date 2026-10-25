# af-compiler G2a 独立验证报告（2026-10-24）

- 验证者：独立测试代理（与 G2a 实现者无涉；只读代码 + 实跑，未修改工作树任何代码/文档；本报告为唯一写入物）
- 验证对象：`/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-compiler/`（src/ + docs/{保证边界矩阵,执行语义规范-v0} + RESULT-G2a.md），锚点 **`2c5a605`**（phase2-compiler 分支）
- 权威输入：任务书（本验证任务）；ADR-010 §2/§5（四一等字段 capability/effect/provenance/trust，经 `计划/变更日志.md` 第 10 行交叉确认）；《DSL-语法提案-B》；《落地契约-v0》；af-dsl 源码（AST 正本）
- 资源纪律：开工 `df -h /` = 剩 19G（盘 96% 满，≥15G 门槛满足）；构建目录 `CARGO_TARGET_DIR=~/afbuild-phase2d`（与实现者同目录规则，未复用其他批目录）；未触碰其他工作树；自构夹具全部落 `/tmp/g2a_inputs/`、探针 crate 落 `/tmp/g2a_probe/`
- 验证后工作树核验：`git status --short` 为空（干净），`git diff 73ccfb2..HEAD -- crates/af-dsl` 为 0 行（af-dsl 源码零改动属实）

## 三态结论：**通过**（附 6 项观察，0 阻断）

G2a 交付面（IR schema v1 + 确定性 lowering + 拒绝式 decode + 快照 CLI + 两份文档）与任务书全部必做检查项符合：23/23 独立复跑全绿、确定性经 4 份输入双跑逐位实证（含中文/特殊字符与对齐草稿）、四一等字段在场且默认值安全、内联体降维等价性经全部 8 个构造亲手比对成立、信封拒绝路径经独立探针逐条复现为真、两文档的三分类标注与引用溯源基本属实（INV-2/INV-4 抽查如实）。观察项见文末：fmt 未净（仓库级既有现象，RESULT 未声明此项）、执行语义规范 §1.1/§1.2/§1.3 与矩阵 L1 loop 行对 af-dsl 静态能力有三处高报（max_iterations>0 / safety_points 非空 / carried 上界均未被 stage 1 强制，已实测反例）、E2210 码位引用不实（实际由 E1002 强制执行）、E9004 为前瞻引用。

---

## 检查 1：全量测试实跑 + CLI 快照 ✅

命令（与任务书指定一致）：

```
cd /home/pan-ding/workspace/af-wt-phase2-dsl
CARGO_TARGET_DIR=~/afbuild-phase2d cargo test -p af-compiler
```

关键输出（五个集成测试二进制 + doc-tests，`grep -cE "^warning|^error"` = 0）：

```
test result: ok. 5 passed; 0 failed   ← golden_test
test result: ok. 4 passed; 0 failed   ← inline_body_test
test result: ok. 8 passed; 0 failed   ← ir_schema_test
test result: ok. 2 passed; 0 failed   ← lower_error_test
test result: ok. 4 passed; 0 failed   ← route_guard_test
test result: ok. 0 passed; 0 failed   ← doc-tests
```

**合计 23 通过 / 0 失败 / 0 警告**，与 RESULT-G2a.md 声明的「23 通过（golden 5 + inline_body 4 + ir_schema 8 + lower_error 2 + route_guard 4）」逐文件一致。

CLI 实跑（对 sample1.yaml 输出 IR JSON）：

```
CARGO_TARGET_DIR=~/afbuild-phase2d cargo run -q -p af-compiler --bin af-compiler-snapshot -- crates/af-dsl/testdata/sample1.yaml
```

exit=0，stdout 4009 字节合法 IR JSON。关键字段核验（`ir_version: 1`；四一等占位在序列化面：`capability_refs: []` / `effect_class: null` / `provenance: null` / `trust: {}`；budgets 按 id 字典序 `["cost_cap","token_cap","turn_cap"]`；stop[0].when 带 `source/roots/digest` 三键）——与 RESULT-G2a.md 第 15 行声明逐项一致。

## 检查 2：确定性独立复核 ✅

自选 4 份输入（3 份必需 + 1 份中文/特殊字符自构），CLI **各跑两次**（两次均为独立进程）后 `cmp` 逐位比对：

| 输入 | 来源 | 两次运行结果 |
|---|---|---|
| sample1.yaml | af-dsl testdata（golden） | 4009 字节，逐位一致（sha256 `0a291ee9…`） |
| sample6.yaml | af-dsl testdata（golden，双层嵌套 loop + L4 逃逸） | 13067 字节，逐位一致（`f3f1682e…`） |
| LangGraph-StateGraph.yaml | **对齐草稿**（`计划/研究组/对齐草稿/`，45KB，含嵌套 loop/map、human、checkpoint 边、escape、route） | 45353 字节，逐位一致（`f6662a60…`） |
| special_chars_cn.yaml | **自构**（基于 sample6 注入中文/特殊字符 meta） | 13191 字节，逐位一致（`fa0cee6e…`） |

对齐草稿另跑 Multi-Agent-Debate.yaml（36KB）同样 exit=0——外部草稿可完整过 load+validate+lower 管线。

中文/特殊字符序列化稳定性（自构夹具 `special_chars_cn.yaml`：`meta.intent` 含引号/反斜杠/换行/制表/emoji 🚀🧨/∑∫≠≤/全角（）【】；escape.reason 含 `<>&"'\\「」`；中文 template_ref 与中文 vars 键）：

- 两次运行 `cmp` 逐位一致；追加 **10 次连跑 sha256 全部相同**（10/10 = `fa0cee6e…`）；
- 序列化内容核实：中文/emoji 以原始 UTF-8 落 JSON（非 `\u` 转义），引号/反斜杠/换行按 JSON 规则转义，`python3 json.loads` 往返无损；中文 vars 键（`语言`）在 BTreeMap 序中稳定落位；
- 输入路径无关性：同一文件从工作树路径与 /tmp 路径编译，输出 `diff` 为空。

## 检查 3：IR 完备性 ✅

### 3a. ADR-010 四一等字段（任务书 + 变更日志第 10 行交叉确认四字段 = capability/effect/provenance/trust）

schema 落点（`src/ir.rs`）：`IrNode.capability_refs: BTreeSet<String>`（:117，无 skip——恒序列化）、`ToolSpec.effect_class: Option<EffectClass>`（:407-408，`#[serde(default)]` → null）、`ArtifactSpec.provenance: Option<ProvenanceSpec>`（:438-439，→ null）、`IrBody.trust: BTreeMap<String,String>`（:68，→ `{}`）。

独立核实（不依赖交付方测试，直接解析六样例 CLI 产物 JSON）：四字段在全部六样例逐一在场且**默认值安全**（空集/None/空映射——不授予任何能力、不假设任何副作用、不声明任何血缘、不授予任何信任），合计 40 节点 capability_refs=[]、9 工具 effect_class=null、38 工件 provenance=null、6 样例 trust={}。`effect_class` 词表 Pure/Persist/ExternalOnce（ir.rs:411-420）与 af-harness `ToolDecl.effect`（`af/crates/af-harness/src/spec.rs:36-44`）逐字同源；`capability_refs` 注记的 af-credential Cedar/biscuit 在 `af/crates/af-credential/src/{credential,judge}.rs` 真实存在。

### 3b. 内联体降维等价性（IR 子图节点集 = AST 内联体节点集）

用 Python 独立解析 AST（PyYAML）与 CLI 产物 IR JSON，对**全部 8 个构造**（5 份含构造的样例）逐一人手比对——非仅计数守恒：

| 构造 | 子图名 | 节点集 | 边集 | entry=体首声明 | 版本 stamp |
|---|---|---|---|---|---|
| loop@build（s2） | metagpt_sop/build | == {apply,engineer,qa} | == (3) | engineer ✓ | ✓ |
| loop@rounds（s3） | debate_kv/rounds | == {collector,converge_gate,debate_map,tally} | == (3) | debate_map ✓ | ✓ |
| map@rounds.debate_map（s3） | debate_kv/rounds/debate_map | == {debater} | == (0) | debater ✓ | ✓ |
| loop@search（s4） | aflow_search/search | == {assess,run,scoreboard,synth} | == (3) | synth ✓ | ✓ |
| map@search.run（s4） | aflow_search/search/run | == {aggregate,gen_a,gen_b} | == (2) | gen_a ✓ | ✓ |
| loop@react_ring（s5） | langgraph_subset/react_ring | == {agent,approve,format_check,tools} | == (5) | agent ✓ | ✓ |
| loop@explore（s6） | voyager_curriculum/explore | == {acquire,proposer} | == (0) | proposer ✓ | ✓ |
| loop@explore.acquire（s6） | voyager_curriculum/explore/acquire | == {admit,code_exec,curator,generator} | == (5) | generator ✓ | ✓ |

结论：降维为纯命名空间操作（拓扑零损失），命名规则 `<图名>/<点号路径>`、entry=体 nodes 首元素、graph_version 恒 stamp 父图版本均属实。

## 检查 4：两文档审查

### 4a. 保证边界矩阵——三分类标注与 af-dsl 实际能力

**逐码核对**：矩阵引用的 20 个 E 码中，18 个在 `af-dsl/src/error.rs` 真实存在且在我核对的 validate 模块中实际触发（E2301-E2304/E2401-2403→inv1.rs；E2311/E2312/E2211→inv2.rs；E2321→inv3.rs；E2331→inv4.rs；E2201/E2202/E2205/E2208/E2104→refs.rs；E1051/E1052/E1053/E2203→cel.rs；E2101-E2103→route.rs/m4.rs；E1003→shape.rs；E2003→mod.rs；E2204→m4.rs）。两个例外见观察 4/5。

**INV-2 抽查（矩阵 §1 第 2 行）——如实**：标注「静态可证明：E2311 多写者/写者集合不符、E2312 map 体写体外 store」与 `validate/inv2.rs` 实现逐条对应（:29-39 E2312 in_map 判定；:43-52 E2311 写者势=1 且=声明值）；「运行时无强制需求（静态已排除多写者；执行面按 writer 路由是顺从而非强制）」的分层诚实；性质/机制分层（§4）与 ADR-010 §4 一致。

**INV-4 抽查（矩阵 §1 第 4 行）——「运行时强制依赖执行面」如实标注**：`validate/inv4.rs:44-77` 实现的正是标注所述的「编译期扫描 eval_input: true 的 store 读者 ∉ {writer, kind=check ∧ uses.unit 的节点}」——`is_evaluator()`（:26-28）双条件与矩阵文面逐字一致；矩阵明言这只能证明「声明面无违规引用」，运行时绕过（工具内嵌读文件）由执行面读权限拦截强制，且 §4-3 诚实边界披露「该层当前为占位」——高报为零，分类（静态可声明 + 运行时强制依赖执行面）成立。

**TCB 四行（矩阵 §3）——具体不空泛**：四行各带可核机制锚点（编译器：golden 回归+失败分类账 ADR-007 §4；执行面：装配/probe-charge/迭代计数/幂等键/MES outbox 六具体项；绑定组件：effect_class 真实性+注册表 digest+失约可归因；验证器：E2201 类型核对+INV-3+eval_sha256 位），「被信任什么/不被信任什么（对应防御）」两列均为可检验命题。

### 4b. 执行语义规范-v0——构造覆盖与引用溯源

**操作语义段覆盖（任务书点名的五构造全部在册）**：loop §1（1.1 迭代边界/1.2 carried 重建/1.3 安全点/1.4 exit_when/1.5 route 提前收束/1.6 args 隐式依赖）、map §2（2.1 运行时定基数/2.2 实例化隔离/2.3 并发上限/2.4 聚合/2.5 隐式入边）、route §3（3.1 求值时机/3.2 互斥覆盖/3.3 exit 分支/3.4 词汇表）、边投递 §4（4.1 at-least-once/4.2 幂等键/4.3 guard 边/4.4 checkpoint/4.5 envelope 血缘）、重试与补偿 §5（5.1-5.4 F1-F4/5.5 声明式路由/5.6 补偿/5.7 断点续跑）；每段带【强制】/【约定】/【占位】记分。

**引用溯源（逐条实查）**：
- poc-temporal「activity 执行 2 次、扣款恰好 1 次」→ `af/poc/poc-temporal/RESULT.md:15` 原文在场；VERIFY.md 存在；`POC_SUMMARY.md:26` #15 条目同述；
- poc-ledger「WAL 8/8 分裂 + outbox 三崩溃点收敛」→ `af/poc/poc-ledger/REPORT.md:10` 裁决一原文 + :100-105 实测数据在场；
- 落地契约 §5.2（预算 probe/charge/对账五条）、§6.2（F1-F4 + recovery 字段 + 恢复总则五条）、§7.2（Tempo 裁决七条）、§3.2 item 5（fan-out）、§6.3/§7.3（checkpoint/voucher 开放项）→ 均在与规范引文相符的条目实查存在；
- 提案 B §1.5 route 归一化 → af-dsl `src/route.rs` 在场，且 lowering 确为复用（`lower.rs:198` 调 `af_dsl::route::normalize`，无第二实现）；重构形 `!((format_check.passed == false))` 与 route.rs:165-169 公式一致；
- af-meter `budget.rs`、af-harness `run.rs`、af-stop crate 均存在。

## 检查 5：信封拒绝测试真实性 + clippy/fmt

**拒绝路径真实性（独立复现，非照信测试）**：在 /tmp 构建探针 crate（路径依赖 af-compiler/af-dsl，未触工作树），直接调 `decode_ir` 对 13 种输入实跑：

```
valid baseline                => Ok (ir_version=1)
ir_version=2（body 同时篡改）  => Err: IR 信封 ir_version=2 非 1（拒绝式：整份拒绝）   ← 版本先行，body 不解析
missing ir_version            => Err: IR 信封缺 ir_version 键
ir_version="1"（字符串）        => Err: IR 信封 ir_version 非整数
ir_version=1.0（浮点）         => Err: IR 信封 ir_version 非整数
unknown top key               => Err: IR 信封未知顶层键 "extra"
unknown body field            => Err: IR body 形状不符：unknown field `agents_view`…
unknown nested node field     => Err: IR body 形状不符：unknown field `mystery`…（deny_unknown_fields 全层生效）
unknown nested CelRef field   => Err: IR body 形状不符：unknown field `extra`…
invalid JSON / root array / root string => Err: 缺 ir_version 键（退化归并）
body missing                  => Err: IR body 形状不符：缺 body 键
roundtrip equals lowered: true
```

五类拒绝（版本非 1/缺版本/非整数/未知顶层键/未知字段含嵌套）全部真实生效，与 ir_schema_test.rs 的 5 个反例测试主张一致；往返无损成立。

**clippy**：`CARGO_TARGET_DIR=~/afbuild-phase2d cargo clippy -p af-compiler --all-targets` → exit 0，`grep -cE "^warning|^error"` = **0**。✅

**fmt**：`CARGO_TARGET_DIR=~/afbuild-phase2d cargo fmt -p af-compiler -- --check` → **exit 1，55 处 diff**（decode.rs 3、lower.rs 19、五个测试文件 33）。⚠️ 见观察 1。

## 附加核实项

- **af-dsl 源码零改动**：`git diff 73ccfb2..HEAD -- crates/af-dsl` = 0 行；`git diff --stat` 全部改动限于 af-compiler 16 文件 +2528 行（纯新增）。
- **红绿序列**：`git show d4b978f:crates/af-compiler/src/lower.rs` 为 `unimplemented!("G2a RED：lowering 待实现")` 桩；该提交测试函数计数 5+4+8+4=21（lower_error 2 例在 87cab12 补入）——「20 红/1 绿（绿 = 不调 lower 的 full_validation 例）」与 RESULT 声明相符；`git log --oneline 73ccfb2..HEAD` 四提交序列与声明一致。
- **CEL 白名单 15 算子**：`cel.rs:24-26` 实测 15 项，与矩阵 L1「E1052 算子白名单（15 算子）」一致。
- **磁盘纪律**：收工 `df -h /` 剩 19G（开工 19G，构建净增可忽略），未触其他工作树。
- **E1002 强制逃逸四字段实证**：自构缺 `owner`/`share_budget_pct` 的 escape 文档 → `装载拒绝：shape rejected:E1002 missing_field[document]: missing field 'owner'`（exit 1）——「四字段缺一拒绝」的性质成立，但码位是 E1002 而非矩阵所引 E2210（见观察 4）。

## 观察项（均不阻断）

1. **fmt 未净**：af-compiler 55 处、af-dsl 92 处 rustfmt diff（仓库 CI `ci/run.sh:78` 有 fmt 硬门）。RESULT-G2a.md 未声明 fmt 通过（只声明 clippy 0 警告），故不构成不实声明；但按仓库自身门禁标准该 crate 不达标。建议实现者跑一遍 `cargo fmt` 收口（若全仓同状，宜先对齐工具链再统一）。
2. **执行语义规范 §1.1 高报**：「`max_iterations > 0` 编译期已保证（缺/非正拒绝编译）」不实——自构 `max_iterations: 0` 文档实测 exit=0 完整 lowering（u32 必填但无非正检查）。执行面若据此省略自身防护，遇 0 迭代语义未定义。
3. **执行语义规范 §1.2/§1.3 + 矩阵 L1 loop 行高报**：「carried 至少一上界…编译期已判」不实（自构无上界 carried 条目实测编译通过；af-dsl 只查 E2211 覆盖性，`CarriedDecl` 两界字段皆 Optional 且无 is_bounded 检查）；「safety_points 非空编译期已保证」不实（自构 `safety_points: []` 实测编译通过；stage 1 只强制键存在=缺失拒绝）。矩阵该行「必填>0」「至少一上界」「缺失拒绝」三小项中只有「必填/缺失」为真。
4. **E2210 码位引用不实**：矩阵 L1 逃逸舱行引「E2210 四字段缺一拒绝」，但 E2210 不在 af-dsl 码表（af-dsl `model.rs:537` 自注「E2210 语义留待后续模块」）；实际强制在装载层 E1002（已实证）。建议矩阵改引 E1002 或注明 E2210 为保留码位。
5. **E9004 前瞻引用**：矩阵 TCB「绑定组件」行引「注册表 digest 完整（E9004 装载期核对）」，E9001-E9004 均未入码表、注册器不存在（落地契约 §2.3「注册表本体不存在」自证）。属 stage 3 前瞻描述而非当期能力，建议文中标注「G2b 后」以免误读为现有机制。
6. **矩阵 §4-3 引用略偏**：「eval_input…该层当前为占位，见落地契约 §2.3/§5.3」——§2.3 是组件注册表缺口、§5.3 是 voucher 缺口，均非 eval_input 读拦截层专条；诚实边界结论（无运行时读权限层实现）本身成立，引用位置可更准。

## 附：自构夹具与产物（证据留存，均未入工作树）

- `/tmp/g2a_inputs/`：special_chars_cn.yaml（中文/特殊字符）、escape_missing_field.yaml、empty_safety_points.yaml、zero_iter.yaml、unbounded_carried.yaml、六样例 run1/run2 产物
- `/tmp/g2a_probe/`：decode_ir 独立探针 crate（13 例拒绝/接受矩阵）
