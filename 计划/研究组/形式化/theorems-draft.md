# 定理陈述库草稿（FV-0.3 · 任务包 P2-Q02 · ADR-011）

- 版本：草稿 v0（2026-10-24，定理陈述抽取战役交付）
- 地位：**只译不证**。本文件是正本语义的定理陈述翻译（陈述库），不含任何证明；证明是后续战役（FV-0.4+）的义务。每条陈述逐字锚定正本原文（文件+行号+摘录），行号全部来自本战役实读（Read/sed/grep），无编造。
- 配套报告：同目录 `extraction-report.md`（抽取统计 / 正本歧义清单 / 审计高危提示）。

## 0. 正本与路径别名

| 别名 | 全路径 | 用途 |
|---|---|---|
| 【提案B】 | `/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/DSL-语法提案-B.md` | §5 四条 L0 不变量判定规则（:1341-1554）等 |
| 【规范】 | `/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-compiler/docs/执行语义规范-v0.md` | loop/map/route/边投递/重试补偿操作语义（全文 99 行） |
| 【矩阵】 | `/home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-compiler/docs/保证边界矩阵.md` | 三档保证分类 + TCB + 诚实边界（全文 60 行） |
| 【G1裁决】 | `/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/G1-放行裁决-20261024.md` | goto:exit 语义裁决（:18）等 |
| 【state】 | `/home/pan-ding/workspace/af-wt-phase2-execline/crates/af-workorder/src/state.rs` | 订单状态机（127 行） |
| 【order】 | `/home/pan-ding/workspace/af-wt-phase2-execline/crates/af-workorder/src/order.rs` | 迁移统一入口 + 门控 |

正本定位说明（如实）：
- 【规范】与【矩阵】在 `af-wt-phase2-execline` 工作树**不存在**（`ls /home/pan-ding/workspace/af-wt-phase2-execline/crates/af-compiler/docs/` → `No such file or directory`），按任务包预案改读 `af-wt-phase2-dsl` 工作树（任务包正本 2/3 预授权的 fallback）。
- 【state】在两个工作树各有一份，本战役实跑 `diff /home/pan-ding/workspace/af-wt-phase2-execline/crates/af-workorder/src/state.rs /home/pan-ding/workspace/af-wt-phase2-dsl/crates/af-workorder/src/state.rs` → 输出 `IDENTICAL`（逐字节相同），以下行号对两份均有效。

## 0.1 三档分类与第四档预留位

【矩阵】:9-13 定义三档保证：**静态可证明**（编译期确定性算法判定，违例拒绝编译+稳定错误码）/ **运行时可强制**（执行面机制强制，违例类型化上报）/ **依赖可信组件**（组件按声明行事，组件进 TCB）。【矩阵】:15：「一条保证可拆多层……拆层标注是本文的核心诚实手段」。

本库为**第四档·机器验证**预留分类位（ADR-011 义务）：每条陈述带「矩阵档位」（现状三档标注）与「第四档预留」两个字段。第四档的占位定义（待后续 ADR 裁决）：**由证明工具（Verus/Kani/Rocq）在声明的义务范围内给出机器可检查证据，将原档的证据形态升级为证明工件**；原三档标注不被第四档替换——机器验证是叠加证据，不推翻原档的机制定位。凡陈述落在 TCB 内（如装配忠实性、包装忠实性），第四档只能对 TCB 成员的实现代码建模验证，不能消除 TCB 本身——此类条目的「第四档预留」字段明确写出可验证面与不可验证面。

## 0.2 条目格式与统计

每条：编号 / 方向（soundness=违例必拒；completeness=合法必过；property=性质）/ 自然语言陈述 / 锚定原文（文件:行号 + 逐字摘录）/ 建议证明工具（Verus/Kani/Rocq）/ 矩阵档位 / 第四档预留 / UNCERTAIN（无则写「无」）。

总数 **57 条**：A 组 INV 16 · B 组构造语义 23 · C 组确定性 9 · D 组状态机 9。UNCERTAIN 8 条（14.0%）：A-04、B-02、B-04、B-06、B-11、B-13、B-18、C-08。

---

# A 组 · INV 组（四条 L0 不变量，每条 soundness + completeness 两方向）

## A-01 · INV-1 soundness——section 来源可解析
- **方向**：soundness（违例必拒）
- **陈述**：任何文档若存在某 LLM-bound task 节点的某 section 来源不可解析（`input.fields` ∉ `meta.input` schema、`arg.name` ∉ 所在体形参表、`edge.port` ∉ 本节点入边端口集、`store` 名经作用域链不可解析、`template_ref` 形状非法五者任一），则编译被拒绝，且 Report 含稳定码 E2301。
- **锚定原文**：
  - 【提案B】:1347：「每个 section 的来源可解析（`input.fields` ∈ `meta.input` schema、`arg.name` ∈ 所在体形参表、`edge.port` ∈ 本节点入边端口集、`store` 名经作用域链可解析、`template_ref` 形状合法）」
  - 【提案B】:1380：「`E2301 context_source_unresolvable: node 'solver' section[1] field 'requirement' not in meta.input schema (t)`」
  - 【提案B】:1570：「E2301 上下文来源不可解析」
- **建议证明工具**：Kani——对 af-dsl `validate/inv1` 判定函数建 harness：非确定构造含不可解析来源的 AST，断言 Report 含 E2301。
- **矩阵档位**：静态可证明·声明面（【矩阵】:21「**静态可证明（声明面）**：E2301 来源可解析……编译期全判」）。
- **第四档预留**：可全判位——判定函数为纯函数，Kani harness 即第四档证据。
- **UNCERTAIN**：无。

## A-02 · INV-1 soundness——配额为正
- **方向**：soundness
- **陈述**：任何文档若存在某 LLM-bound 节点的某 section `quota_tokens ≤ 0`（或缺失），则编译被拒绝且 Report 含 E2302。
- **锚定原文**：
  - 【提案B】:1347：「每段 `quota_tokens` 为正」
  - 【提案B】:1570：「E2302 配额非正」
  - 【矩阵】:21：「E2302 配额非正」
- **建议证明工具**：Kani（同 A-01 harness 家族，逐码断言）。
- **矩阵档位**：静态可证明（【矩阵】:21）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## A-03 · INV-1 soundness——LLM 节点禁直读 store
- **方向**：soundness
- **陈述**：任何文档若存在 LLM-bound 节点声明 `reads`，则编译被拒绝且 Report 含 E2303；store 内容只能经 `context.sections` 进入 agent 上下文。
- **锚定原文**：
  - 【提案B】:1347（句末）：「LLM-bound 节点不得声明 `reads`」
  - 【提案B】:1381：「`E2303 agent_direct_store_read: LLM-bound node 'solver' declares reads ['trajectory']（store 只能经 context.sections 进入 agent 上下文）`」
  - 【提案B】:114（`reads` 字段行）：「直读 store 名（仅非 LLM 节点；LLM 节点声明即 E2303）」
  - 【提案B】:101：「**读权限在消费者侧声明，不在 store 侧**：agent 类节点经 `context.sections`（INV-1），其余节点经 `reads[]`」
- **建议证明工具**：Kani。
- **矩阵档位**：静态可证明（【矩阵】:21「E2303 LLM 节点直读 store」）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## A-04 · INV-1 soundness——入边端口被 section 引用（未引用方向）
- **方向**：soundness
- **陈述**：任何文档若存在 LLM-bound task 节点的某个入边端口未被任何 section 引用，则编译被拒绝且 Report 含 E2304。
- **锚定原文**：
  - 【提案B】:1347：「每个入边端口恰被一个 section 引用」
  - 【提案B】:1570：「E2304 入边端口未被 section 引用」
  - 【提案B】:1349：「**检查**：引用闭包扫描 + 入边端口覆盖核对 + 配额正数核对」
- **建议证明工具**：Kani。
- **矩阵档位**：静态可证明（【矩阵】:21「E2304 入边端口恰被一节引用」）。
- **第四档预留**：可全判位（就本条已陈述方向）。
- **UNCERTAIN**：**是**——「恰被一个」的**被多引方向**（同端口被 ≥2 个 section 引用）：规则文字【提案B】:1347 覆盖两个方向，但 §6 码表（:1570）与违规样例（:1351-1381）只定义「未被引用」方向的码位与消息，被多引方向报不报错、报哪个码，正本未定。本条只陈述已定方向，多引方向待规范勘误（见报告歧义清单 #1）。

## A-05 · INV-1 判定对象范围（范围定理）
- **方向**：property（范围界定）
- **陈述**：E2304 的判定对象 = LLM-bound task 节点；非 LLM 节点（含 kind:check + uses.unit 判定单元）即使带 `context` 且入边端口未被 section 引用，也不得触发 E2304（其段级核对 E2301/E2302/E2401-E2403 仍照常适用于已声明的 context）。
- **锚定原文**：
  - 【提案B】:1347（全句主语）：「**规则**：LLM-bound task 节点的上下文 = 且仅 = 其 `context.sections` 声明的来源（无隐式注入）；……每个入边端口恰被一个 section 引用；LLM-bound 节点不得声明 `reads`」（后续分句继承「LLM-bound task 节点」主语）
  - 【提案B】:113（`context` 字段行）：「`{sections: [...]}`——**仅 LLM-bound task 可用**（INV-1 判定对象）」
  - 【提案B】:111（`uses` 字段行）：「**LLM/工具/评估器的分野在 uses 不在 kind**」
  - 背景（非正本，裁定先例）：`计划/研究组/E2304-作用域复核-20261024.md` §1-§3——af-dsl 曾按「LLM-bound ∪ 带 context」判定（过宽），phase2-dsl-fix1 已收窄为 `if llm_bound`。
- **建议证明工具**：Kani——存在性 harness：非 LLM 节点带 context + 入边端口未被引用 ⇒ Report 不含 E2304。
- **矩阵档位**：静态可证明（【矩阵】:21）。
- **第四档预留**：可全判位；此条把「判定对象范围」本身立为定理，防实现再漂移（E2304 类风险的定理面收口）。
- **UNCERTAIN**：无（「LLM-bound」操作定义依 :111 分野在 uses——task + `uses.model` 在场；E1005 落地后应保持该定义）。

## A-06 · INV-1 completeness——合法必过
- **方向**：completeness
- **陈述**：任何文档若满足 INV-1 全部子句（每个 LLM-bound 节点的 section 来源全可解析、每段配额为正、无 LLM 节点声明 reads、每个 LLM-bound 节点入边端口恰被一节引用），则编译不得因 INV-1 相关码（E2301/E2302/E2303/E2304）拒绝。
- **锚定原文**：
  - 【提案B】:1349：「**检查**：引用闭包扫描 + 入边端口覆盖核对 + 配额正数核对」
  - 【提案B】:1343：「判定位置：af-dsl 前端静态 pass（ADR-002 crate 职责）。每条给：规则 → 静态检查 → 一个违规样例 → 错误码。全部一次收齐。」
- **建议证明工具**：Kani——满足前提的 AST ⇒ 断言 Report 中 E2301-E2304 缺席。
- **矩阵档位**：静态可证明（【矩阵】:21）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## A-07 · INV-2 soundness——写者集合恰一
- **方向**：soundness
- **陈述**：任何文档若存在某 store 的写者集合（全部节点 `writes[]` 点号路径解析后，与 `store.writer` 声明交叉核对）基数 ≠ 1，或 ≠ 声明的 writer，则编译被拒绝且 Report 含 E2311。
- **锚定原文**：
  - 【提案B】:1385：「每个 store 恰有一个写者——`store.writer` 声明与全部节点 `writes[]` 引用（点号路径解析后）交叉核对，写者集合势 = 1 且等于声明值」
  - 【矩阵】:22：「E2311 多写者/写者集合不符」
  - 【提案B】:1570：「E2311 多写者」
  - 【提案B】:1387：「**检查**：写者闭包扫描 + map 体作用域禁写 + carried 覆盖核对」
- **建议证明工具**：Kani（对 inv2 判定函数 harness：构造多写者 AST ⇒ 断言 E2311；G1 裁决 :12 记载「验证者曾以 19 个自构样例独立实证」INV-2 三码，harness 化即第四档化）。
- **矩阵档位**：静态可证明（【矩阵】:22「**静态可证明**：E2311 多写者/写者集合不符、E2312 map 体写体外 store……编译期判定」）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## A-08 · INV-2 soundness——map 体禁写体外 store
- **方向**：soundness
- **陈述**：任何文档若存在 map 体节点写入本 map 体外声明的 store，则编译被拒绝且 Report 含 E2312（N 并行实例将并发写；合法形态是 N 实例 = N 写者，即 map 体节点只能写本体内声明的 store）。
- **锚定原文**：
  - 【提案B】:1385：「map 体节点只能写本体内声明的 store（N 实例 = N 写者）」
  - 【提案B】:1445：「`E2312 map_shared_store_write: node 'debater' inside map body writes store 'transcript' declared outside（N 并行实例将并发写；改由汇聚节点单写——见样例 3 collector）`」
- **建议证明工具**：Kani（违规样例 :1391-1442 的 AST 形态即反例模板）。
- **矩阵档位**：静态可证明（【矩阵】:22）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## A-09 · INV-2 soundness——carried 覆盖
- **方向**：soundness
- **陈述**：任何文档若 loop 的 `carried[]` 未覆盖「体内（含嵌套体）写入的、体外声明的全部 store」，则编译被拒绝且 Report 含 E2211；反向（completeness）：carried 覆盖核对通过 ⇒ 不因 E2211 拒。
- **锚定原文**：
  - 【提案B】:1385（句末）：「loop 的 `carried` 必须覆盖「体内（含嵌套体）写入的、体外声明的全部 store」」
  - 【提案B】:1569：「E2211 carried 未覆盖跨作用域写入」
  - 【规范】:27：「未列入 `carried[]` 而被体内写入的体外 store 不存在（E2211 编译期已排除）——运行时无需防御」
- **建议证明工具**：Kani。
- **矩阵档位**：静态可证明（【矩阵】:32 loop 有界性行内 carried 至少一上界为静态面；E2211 归【提案B】:1569 契约段）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## A-10 · INV-2 completeness + 性质引理——单写者 ⇒ 无并发写冲突
- **方向**：completeness + property
- **陈述**：①（completeness）写者闭包核对通过 ⇒ 每个 store 的写者集合恰为声明 writer 单点，编译不因 E2311/E2312 拒。②（性质引理）静态单写者成立且运行时执行面按 writer 路由写请求的条件下，任意 store 无并发写冲突——性质（无并发写冲突）由机制（单写者）在 v0.1 兑现。
- **锚定原文**：
  - 【矩阵】:22：「**性质/机制分层**（ADR-010 §4）：保证的性质=「无并发写冲突」；v0.1 的机制=「单写者」（集中式形态的最简可判定形式）」「运行时无强制需求（静态已排除多写者；执行面按 writer 路由写请求是顺从而非强制）」
  - 【矩阵】:50（TCB 绑定组件行）：「写冲突由 INV-2 静态排除 + 执行面按 writer 路由兜底」
  - 【提案B】:1385。
- **建议证明工具**：Rocq——抽象写事件模型上证「写者单点 ⇒ 任意两写事件同 store 者同源（可排序）」；静态面（①）用 Kani。
- **矩阵档位**：静态可证明（机制面）；性质面由机制面 + 执行面顺从合成。
- **第四档预留**：①可全判位；②引理可全判（Rocq 对抽象模型），但「执行面按 writer 路由」前提在执行面 TCB（【矩阵】:49）——引理以该前提为显式假设。
- **UNCERTAIN**：无（机制多元/声明式原子合并协议是 v0.2 议题，【矩阵】:22 明文；届时引理需重立）。

## A-11 · INV-3 soundness——直接自验证必拒
- **方向**：soundness
- **陈述**：任何文档若存在验证面节点（kind ∈ {check, gate} ∪ human 标记节点）的一条入边，其生产者是该节点自己，则编译被拒绝且 Report 含 E2321（产出即验收 = 自验证，禁止）。
- **锚定原文**：
  - 【提案B】:1450：「验证节点的任一条入边的生产者不得是它自己（产出即验收 = 自验证）」
  - 【提案B】:1491：「`E2321 self_verification: verifier node 'solver' consumes port 'patch' produced by itself（生成与验证必须不同节点）`」
  - 【提案B】:1450（验证面定义）：「验证面 = kind ∈ {check, gate} ∪ human 标记节点（check/gate 另内建 `passed: boolean` 端口）」
- **建议证明工具**：Kani（违规样例 :1456-1488 的 solver→solver 自环即反例模板）。
- **矩阵档位**：静态可证明·直接自环面（【矩阵】:23「**静态可证明（直接自环面）**：E2321 验证面节点……任一入边的生产者是它自己」）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## A-12 · INV-3 范围边界——间接自验证不查（诚实边界定理）
- **方向**：property（范围声明）
- **陈述**：INV-3 的判定范围 = 直接自环；间接自验证（验证节点经中间节点消费自己产出的数据流可达形态，如 A 产出→B 验证→A 又消费 B 的结论）**不在 v0.1 判定范围**——含间接自验证形态的合法文档编译通过，不算漏判。此为正本登记的已知缺口，非已保证项。
- **锚定原文**：
  - 【提案B】:1609（§8-4）：「**验证分离的深度**：INV-3 只查直接自环（验证节点消费自己产的端口）。间接自验证（check → transform → check）未查——完全判定需要数据流可达性分析」
  - 【矩阵】:23：「**诚实边界**：间接自验证（A 产出→B 验证→A 又消费 B 的结论改写产出）v0.1 **不查**——提案 §8-4 开放问题，标注为已知缺口而非已保证」
  - 【矩阵】:55（诚实边界 1）：「**间接自验证不查**（INV-3）：v0.1 只判直接自环；A→B→A 的间接自验证是已知缺口（提案 §8-4）」
- **建议证明工具**：无判定义务（范围陈述非判定定理）；若未来升级为判定，需数据流可达性分析（Rocq 建模可达关系可选）。
- **矩阵档位**：诚实边界登记项（非保证）。
- **第四档预留**：预留但**不可立即全判**——先决条件是规范层面先裁决间接自验证是否入判定范围（v0.2 议题）。
- **UNCERTAIN**：无（边界本身是正本明文；「未来是否收窄」是开放问题，不影响本条陈述内容）。

## A-13 · INV-3 completeness + 安全点白名单
- **方向**：completeness + soundness（安全点面）
- **陈述**：①（completeness）无直接自环的文档不得因 E2321 拒。②（soundness）任何文档若 loop 的 `safety_points` 存在节点（点号路径解析后）kind ∉ {check, gate, human}，则编译被拒绝且 Report 含 E2322。
- **锚定原文**：
  - 【提案B】:1450（句末）：「loop 的 `safety_points` 每个节点（点号路径解析后）必须是验证面节点」
  - 【提案B】:1452：「**检查**：验证面节点入边生产者身份核对 + 安全点 kind 白名单（承 af-graph `SafetyPointKind` 三值，`validate.rs:453-457`）」
  - 【提案B】:1446：「`E2322 safety_point_not_verifier: safety point 'debater' kind 'task' not in {check, gate, human}`」
  - 【提案B】:1570：「E2322 安全点非验证面」
- **建议证明工具**：Kani。
- **矩阵档位**：静态可证明（【矩阵】:23 直接自环面 + 【矩阵】:32 loop 有界性行「safety_points 缺失拒绝编译」）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无（E2322 的章节归属文本交叉见报告歧义清单 #3；语义本身无歧义）。

## A-14 · INV-4 soundness——评估输入对候选必闭
- **方向**：soundness
- **陈述**：任何文档若存在标注 `eval_input: true` 的 store，其读者集合（经 `reads`/`context.sections` 引用它的全部节点，点号路径解析后）中有节点 ∉ {该 store 的 writer, 绑定 `uses.unit` 的 check 节点}，则编译被拒绝且 Report 含 E2331。
- **锚定原文**：
  - 【提案B】:1495：「标注 `eval_input: true` 的 store，其读者（经 `reads`/`context.sections` 引用它的全部节点，点号路径解析）必须 ⊆ {该 store 的 writer, 绑定 `uses.unit` 的 check 节点}」
  - 【提案B】:1554：「`E2331 eval_input_visible: store 'answers_ref' (eval_input) referenced by node 'gen_a' outside {writer 'loader', evaluator nodes}（评估输入对候选不可读）`」
  - 【提案B】:1497：「**检查**：eval_input store 的引用方集合核对 + uses 形状规则（`unit` 仅 check 可用，E1005）」
- **建议证明工具**：Kani（违规样例 :1501-1550 即反例模板；gen_a 兼踩 E2303 的复合样例可用于两码正交性检查）。
- **矩阵档位**：静态可声明·引用扫描（【矩阵】:24「**静态可声明（引用扫描）+ 运行时强制依赖执行面**：E2331 编译期扫描……这只能证明**声明面无违规引用**」）。
- **第四档预留**：声明面可全判位；运行时面见 A-16。
- **UNCERTAIN**：无。

## A-15 · INV-4 completeness——合法必过
- **方向**：completeness
- **陈述**：任何文档若 eval_input store 的全部读者 ⊆ {writer, 绑定 uses.unit 的 check 节点}，则编译不得因 E2331 拒。
- **锚定原文**：
  - 【提案B】:1495（同 A-14 规则句的逆否读法）
  - 【提案B】:1543（违规样例内对照注释）：「`- id: assess`……`# 评估器：唯一合法读者`」（样例中合法读者形态的实物对照）
- **建议证明工具**：Kani。
- **矩阵档位**：静态可声明（【矩阵】:24）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## A-16 · INV-4 分层边界——声明面 vs 运行时拦截
- **方向**：property（分层界定）
- **陈述**：E2331 只覆盖声明面读法（reads/context.sections 引用扫描）；组件实现内嵌绕过（如工具代码里直接读文件系统）超出引用扫描视野，其拦截义务在执行面读权限白名单层——该层当前为占位，故「评估 ground truth 对候选不可读」作为体系保证，其运行时半边 v0 不可立。
- **锚定原文**：
  - 【矩阵】:24：「运行时若组件绕过声明面直读（如工具实现内嵌读文件），由执行面的读权限拦截强制（eval_input 槽的读者白名单在运行时生效）」
  - 【矩阵】:57（诚实边界 3）：「**eval_input 只能拦声明面读法**（INV-4）：组件实现内嵌绕过（如工具代码里直接读文件系统）超出引用扫描视野，依赖执行面的沙箱/权限层（该层当前为占位，见落地契约 §2.3/§5.3）」
  - 【提案B】:1610（§8-5）：「**`eval_input` 的标记责任**：标记靠作者自觉；误标（把普通 store 标 eval_input）只会收紧不会放松，安全性单向」
- **建议证明工具**：当前无可验证面（执行面层占位）；若该层落地为 Rust 实现，Kani 可对其拦截逻辑建 harness——预留。
- **矩阵档位**：静态可声明 + 运行时强制依赖执行面（【矩阵】:24 原档）。
- **第四档预留**：占位层的实现落地是第四档入位前置条件；先决条件在正本已登记为缺口。
- **UNCERTAIN**：无（边界是正本明文；不可立的是运行时半边，本条如实只陈述边界本身）。

---

# B 组 · 构造语义组（loop / map / route / 边投递 / 重试补偿操作语义）

## B-01 · loop 迭代边界（计数器不变量）
- **方向**：property（运行时不变量）
- **陈述**：运行时循环驱动器维护单调递增迭代计数器 `iter`，恒有 `iter ∈ [1, max_iterations]`（`max_iterations > 0` 由编译期保证）；每完成一轮迭代（子图 entry 可达的全部节点终态化）计数器才 +1；`iter` 达 `max_iterations` 且 `exit_when` 未命中 ⇒ 不再开启新一轮，按 `on_exhausted` 收束。
- **锚定原文**：
  - 【规范】:20：「运行时维护单调递增计数器 `iter ∈ [1, max_iterations]`；每完成一轮迭代（子图 entry 可达的全部节点终态化）后计数器 +1。达 `max_iterations` 且 `exit_when` 未命中 → 按 `on_exhausted` 收束」
  - 【规范】:20（前置）：「`max_iterations > 0` 编译期已保证（缺/非正拒绝编译）」
  - 【矩阵】:32：「运行时计数器单调、达上限触发 on_exhausted——由执行面强制」
- **建议证明工具**：Verus（循环驱动器状态机不变量：iter 单调、上界、+1 触发条件）——驱动器实现若为 Rust，Verus 直证；Kani harness 可作备选。
- **矩阵档位**：静态可证明（声明面 max_iterations>0）+ 运行时可强制（计数器，【矩阵】:32）。
- **第四档预留**：运行时半边是第四档主战场——对执行面循环驱动器实现建 Verus 不变量。
- **UNCERTAIN**：无。

## B-02 · on_exhausted 三值收束
- **方向**：property
- **陈述**：迭代预算耗尽且 `exit_when` 未命中时按声明的 `on_exhausted` 收束：`continue` ⇒ 循环节点正常完成、`done: signal` 照常发射；`fail` ⇒ 循环节点终态 `failed`；`keep_best` ⇒ 取已完成的最佳迭代产出为 `done` 产物（IR 只保留枚举位）。
- **锚定原文**：
  - 【规范】:21：「`continue`：循环节点正常完成，`done: signal` 照常发射」
  - 【规范】:22：「`fail`：循环节点终态 `failed`（样例 2/5：QA 不通过耗尽轮次 = 失败；LangGraph `GraphRecursionError` 的声明式对应物）」
  - 【规范】:23：「`keep_best`：取已完成的最佳迭代产出为 `done` 产物（v0【占位】：选择函数由绑定期组件契约定，IR 只保留枚举位）」
- **建议证明工具**：Kani（对驱动器 harness 分支覆盖：三值各引一条执行迹断言终态与产物）。Verus 备选（终态枚举的 case-split）。
- **矩阵档位**：运行时可强制（执行面循环驱动）。
- **第四档预留**：continue/fail 两分支可全判；keep_best 见 UNCERTAIN。
- **UNCERTAIN**：**是**——keep_best 的「最佳」选择函数 v0 占位（【规范】:23【占位】、【规范】:96 未定项 1「`keep_best` 的选择函数……待绑定期组件契约」），其选择性质（最优性、平局裁决）正本未定，本条对 keep_best 只立「枚举位存在 + 产出取自已完成迭代」的弱陈述。

## B-03 · carried 重建——iteration 语义
- **方向**：property
- **陈述**：lifecycle 为 `iteration` 的 carried store，每轮迭代开始时整体重建（清空重置）——任何一轮迭代开始时刻该 store 为空。
- **锚定原文**：
  - 【规范】:24：「每轮迭代开始时」
  - 【规范】:25：「`lifecycle: iteration` 的 store **整体重建**（清空重置）」
- **建议证明工具**：Verus（store 状态不变量）/ Kani 备选。
- **矩阵档位**：运行时可强制（执行面 store 实现，【矩阵】:31 截断执行同层）。
- **第四档预留**：可全判位（对执行面实现建模）。
- **UNCERTAIN**：无。

## B-04 · carried 截断——run/persistent 有界保留
- **方向**：property
- **陈述**：lifecycle 为 `run`/`persistent` 的 carried store 跨迭代保留前序内容，且每轮迭代开始按声明上界截断（滚动窗口）；不变量：任意时刻 store 规模满足 max_items 上界或 max_bytes 上界至少其一（`carried[]` 声明的 store 必须有界由编译期判定）。
- **锚定原文**：
  - 【规范】:24：「`carried[]` 声明的 store 跨迭代携带，**且必须有界**（max_items/max_bytes 至少其一，编译期已判）」
  - 【规范】:26：「`lifecycle: run`/`persistent` 的 store 保留前序内容，按声明的上界截断（滚动窗口：保留最近 max_items 条/预算 max_bytes 内）」
  - 【矩阵】:31：「**store 有界保留**（max_items/max_bytes 至少其一）……E2208 编译期拒绝无上界声明；截断真的发生由执行面强制」
- **建议证明工具**：Verus（容器长度/字节规模不变量）。
- **矩阵档位**：静态可证明（声明存在性，E2208）+ 运行时可强制（截断执行）。
- **第四档预留**：两半皆可建模（编译期 E2208 用 Kani、截断用 Verus）。
- **UNCERTAIN**：**是**——「保留最近 max_items 条」的「最近」判据（追加序？时间戳？）【规范】:26 未明说；按追加序读最自然且与确定性纪律自洽，但需规范勘误钉死（见报告歧义清单 #7）。

## B-05 · 静态排除传递引理——E2211 ⇒ 运行时无未登记体外写
- **方向**：property（编译期到运行时的传递）
- **陈述**：编译期 E2211 通过 ⇒ 运行时不存在「未列入 `carried[]` 而被体内写入的体外 store」形态；运行时对该形态无需防御。前提：编译器正确性（校验器无漏判）——显式 TCB 依赖。
- **锚定原文**：
  - 【规范】:27：「未列入 `carried[]` 而被体内写入的体外 store 不存在（E2211 编译期已排除）——运行时无需防御」
  - 【矩阵】:48（TCB 编译器行）：「被信任什么：静态判定无漏判（校验器正确性）」
- **建议证明工具**：Rocq——以「编译器对 E2211 判定可靠（违例必拒，即 A-09）+ 文档静态通过」为前提，推出运行时 store 集合与声明面一致的引理；Kani 对 A-09 供前提证据。
- **矩阵档位**：静态可证明（经由编译器 TCB 传递）。
- **第四档预留**：引理形式化（Rocq）+ 前提的 Kani 全判 = 完整第四档链；编译器无漏判本身是 TCB 信任（不能被同一验证消除）。
- **UNCERTAIN**：无。

## B-06 · 安全点必经
- **方向**：property
- **陈述**：每轮被计入完成的迭代必须经过至少一个安全点节点（check/gate/human）的判定输出；未经任何安全点节点判定输出的轮次不得计入完成——「循环受控」的运行时兑现（静态 DAG 豁免循环体环的代价即安全点必经）。
- **锚定原文**：
  - 【规范】:28：「每轮迭代**必须经过**至少一个安全点节点（check/gate/human）的判定输出，否则该轮不得计入完成——这是「循环受控」的运行时兑现（静态 DAG 豁免循环体的环，代价就是安全点必经）」
  - 【规范】:28（前置）：「`safety_points` 非空编译期已保证」
- **建议证明工具**：Verus（驱动器不变量：iter+1 ⇒ 本轮安全点判定事件存在）。
- **矩阵档位**：静态可证明（safety_points 非空声明面）+ 运行时可强制（必经性）。
- **第四档预留**：运行时半边对驱动器实现建模可全判。
- **UNCERTAIN**：**是**——「判定输出」的端口形态（`passed` 端口？任一 emits 端口？）【规范】:28 未细化；:29 对 exit_when 明说了「`passed`/emits 端口产出」，:28 未同步该措辞（见报告歧义清单 #6）。本条按 :28 原词「判定输出」陈述。

## B-07 · exit_when 求值时机与收束
- **方向**：property
- **陈述**：`exit_when` 的求值时机 = 每轮迭代内验证面节点的 `passed`/emits 端口产出后（`attempt` 绑定取最近一次验证输出）；求值为真 ⇒ 循环立即收束（当轮产出为终产物），不再消耗剩余迭代预算；求值走 CelRef 通道（digest 缓存编译产物）。
- **锚定原文**：
  - 【规范】:29：「求值时机 = 每轮迭代内**验证面节点的 `passed`/emits 端口产出后**（`attempt` 绑定取最近一次验证输出）；求值为真 → 循环立即收束（当轮产出为终产物），不再消耗剩余迭代预算。求值走 CelRef 通道（digest 缓存编译产物）」
- **建议证明工具**：Kani（驱动器 harness：exit_when 命中迹 ⇒ 收束且已消耗迭代数 < max_iterations）。
- **矩阵档位**：v0 约定（【规范】:6 记法「【约定】=v0 取的确定性约定（可裁决变更）」）；机制层运行时可强制。
- **第四档预留**：可全判位；注意【约定】条目可被后续裁决变更——第四档证据须绑定裁决版本。
- **UNCERTAIN**：无。

## B-08 · goto:exit 语义（G1 裁决）
- **方向**：property
- **陈述**：route 的 `goto: exit` 分支不产生任何边；各 exit 分支的联合守卫按文档序析取（`g1 || g2`）暴露给上层——归一化后守卫记在 `IrNode.route_exit_guard`；联合守卫命中 ⇒ 本轮迭代提前收束（当轮产出保留，下轮照常开始），区别于 exit_when 的整个循环收束；循环级终止由 `loop.exit_when`/`policies.stop` 承载——图级归一化与循环级终止分层。`default: exit` 无规则型 exit 守卫时为结构性收束（无出边可走，本轮自然结束）。
- **锚定原文**：
  - 【G1裁决】:18（语义裁决逐字）：「**goto:exit 语义**（草稿批最高优先裁决项）：exit = 本 route 不产生出边 + 各 exit 分支联合守卫（文档序析取）暴露给上层；循环收束由 loop.exit_when / policies.stop 承载。图级归一化与循环级终止分层，批准此读法；提案 B 勘误列入 v0.2 议题（多份草稿的两种读法之歧义就此消除）」
  - 【规范】:30：「体内节点的 route `goto: exit` 分支（归一化后守卫记在 `IrNode.route_exit_guard`，不产边）命中 → **本轮迭代提前收束**（当轮产出保留，下轮照常开始）……`default: exit` 无规则型 exit 守卫时为结构性收束（无出边可走，本轮自然结束；早退语义由 loop 自身的 `exit_when` 承担）」
  - 【规范】:49：「`route_exit_guard` 为真 → 本轮迭代提前收束（§1.5）。多条 exit 规则的联合守卫按文档序析取（`g1 || g2`）」
  - 【提案B】:238：「goto: exit 的分支不产生边」；【提案B】:327：「`goto: exit` 不产生边」
- **建议证明工具**：Rocq（联合守卫析取的命题性质：联合守卫 ≡ ∨i gi，文档序无关析取可结合）+ Kani（lowering 实现的 route_exit_guard 生成 harness）。
- **矩阵档位**：G1 裁决语义（放行裁决，最高语义权威）；【约定】条目。
- **第四档预留**：可全判位——且本条是歧义消解后的钉死条目，第四档证据应引用裁决书行号。
- **UNCERTAIN**：无（两种读法的歧义已由裁决消除，本库一律按裁决读法）。

## B-09 · map 定基数与空扇出
- **方向**：property
- **陈述**：`over` 解析为 list（编译期 E2104 已核类型）；扇出元素数 N 运行时才确定；每元素恰实例化一份子图（实例数 = N），经隐式形参 `item` 收元素；N=0 ⇒ 空扇出，`done` 直接发射且聚合产物为空表。
- **锚定原文**：
  - 【规范】:37：「`over`（`节点.端口` 或 `input.字段`）解析为 list（编译期 E2104 已核类型为 list）；元素数 N **运行时才确定**（对标 Airflow Dynamic Task Mapping）。N=0 → 空扇出，`done` 直接发射（聚合产物为空表）」
  - 【规范】:38：「每个元素实例化一份子图，经隐式形参 `item` 收元素」
  - 【提案B】:1568：「E2104 map.over 非 list」
- **建议证明工具**：Kani（对执行面实例化器 harness：输入 list 长度非确定 ⇒ 实例数相等断言）。
- **矩阵档位**：静态可证明（over 类型）+ 运行时可强制（实例化）。
- **第四档预留**：运行时半边可全判。
- **UNCERTAIN**：无。

## B-10 · map 实例隔离
- **方向**：property
- **陈述**：map 实例间无横向边——静态图不存在实例间边（编译期保证），运行时不得引入实例间通信；实例写共享 store 被 E2312 编译期排除 ⇒ N 实例互不可见（样例 3 的 N 辩手互不可见即本条）。
- **锚定原文**：
  - 【规范】:38：「**实例间无横向边**——静态图就不存在实例间边（编译期保证），运行时不得引入实例间通信；实例写共享 store 被 E2312 编译期排除。样例 3 的 N 辩手互不可见即本条」
  - 【提案B】:1385：「（N 实例 = N 写者）」
- **建议证明工具**：Kani（执行面 harness：断言实例间无共享可变通道；结合 A-08 静态前提 + B-05 传递引理结构）。
- **矩阵档位**：静态可证明（E2312）+ 运行时义务（不引入通信）。
- **第四档预留**：静态半边可全判；「运行时不引入」是对执行面实现的义务性陈述，Verus/Kani 建模其代码可判。
- **UNCERTAIN**：无。

## B-11 · map 并发上限
- **方向**：property
- **陈述**：声明 `max_fanout` 时，任意时刻同时在飞的实例数 ≤ max_fanout（调度级并发控制，落地契约 §3.2 gates/limits 通道）。
- **锚定原文**：
  - 【规范】:39：「`max_fanout` 声明时，同时在飞的实例数 ≤ max_fanout（调度级并发控制，落地契约 §3.2 gates/limits 通道）；未声明 = 执行面默认并发（【占位】默认值待对接会裁决）」
  - 【矩阵】:33：「**map 扇出上限**（max_fanout 可声明）……**静态可声明 + 运行时可强制**：max_fanout 可选；声明后由执行面并发控制强制」
- **建议证明工具**：Verus（并发控制器不变量：in-flight 计数 ≤ 上界）/ Kani 备选。
- **矩阵档位**：静态可声明 + 运行时可强制（【矩阵】:33 原档）。
- **第四档预留**：已声明方向可全判（对执行面并发控制代码建模）。
- **UNCERTAIN**：**是**——未声明 max_fanout 的默认并发值 v0 占位（【规范】:39、【规范】:96），默认路径的上界性质不可立，本条只立已声明方向。

## B-12 · map 聚合完整性
- **方向**：property
- **陈述**：map 节点的 `from_body` 发射端口聚合**全部**实例的同名端口产出，自动包 `list<>`（类型推导规则与 af-dsl 同源）——聚合列表长度 = 产出该端口的实例数，元素与实例产出一一对应。
- **锚定原文**：
  - 【规范】:40：「map 节点的 `from_body` 发射端口（如样例 3 `items: {from_body: debater.position}`）聚合全部实例的同名端口产出，**自动包 `list<>`**（类型推导规则与 af-dsl 同源）」
- **建议证明工具**：Kani（实例化器 + 聚合器联合 harness：N 非确定 ⇒ 聚合长度与元素相等断言）。
- **矩阵档位**：【约定】+ 运行时可强制。
- **第四档预留**：可全判位（同 B-09 harness 家族）。
- **UNCERTAIN**：无（部分实例失败时的聚合范围见 B-13）。

## B-13 · map 聚合序确定性
- **方向**：property
- **陈述**：聚合结果按**实例序**（`over` 的元素下标序）排列，**不是完成序**（完成序不确定，会破坏逐位可复现纪律）；样本内乱序只能由 `shuffle_seeded` 显式引入且必须带 `seed_ref`。
- **锚定原文**：
  - 【规范】:40：「聚合序【约定】：按**实例序**（`over` 的元素下标序）排列——不是完成序（完成序不确定，会破坏逐位可复现纪律；样本内 shuffle 由 `shuffle_seeded` 显式做且必须带 `seed_ref`）」
  - 【提案B】:369：「`shuffle_seeded` 的种子必须来自声明（`seed_ref`），编译期不产随机数」
- **建议证明工具**：Rocq（聚合 = 按下标序的 fold，序保持引理）/ Kani（双跑聚合相等 harness）。
- **矩阵档位**：【约定】；确定性纪律的运行时延伸（【矩阵】:41 确定性编译行的执行面对应物）。
- **第四档预留**：可全判位；与 C 组确定性定理共同构成「逐位可复现」链条。
- **UNCERTAIN**：**是**——部分实例失败时是否聚合部分结果，按 failures[] 的 class 处置（【规范】:40 尾句「部分实例失败时是否聚合部分结果：按 failures[] 的 class 处置（§5），`tool_error → next_iteration` 类不中止评估（样例 4）」）；class→outcome 映射是声明式的，故「聚合完整性」在全量成立与部分成立之间的边界取决于声明，本条弱化为「聚合序恒为实例序」+「非中止类实例的产出在聚合中」。

## B-14 · route 互斥性（由构造成立）
- **方向**：property（纯逻辑定理）
- **陈述**：归一化后节点任意两条不同出边的守卫逻辑不相交：对规则 i≠j（含 default 守卫 guard_d = ¬(when_1 ∨ … ∨ when_n)），`guard_i ∧ guard_j ≡ false`——由构造成立（第 i 条显式排除前 i-1 条），无需任何图分析。
- **锚定原文**：
  - 【提案B】:235（算法步 2）：「rule i 的守卫：  guard_i  = when_i ∧ ¬(when_1 ∨ … ∨ when_{i-1})」
  - 【提案B】:236（算法步 3）：「default 的守卫：guard_d  = ¬(when_1 ∨ … ∨ when_n)」
  - 【提案B】:245：「性质：guard_1..guard_n, guard_d 两两不相交（构造性：第 i 条显式排除前 i-1 条）且并集为真（default 取全否）——**多路路由的互斥+覆盖不需要任何图分析**」
  - 【规范】:48：「guard_i 两两不相交（第 i 条显式排除前 i-1 条）」
- **建议证明工具**：Rocq——对规则序列结构归纳的命题逻辑证明（本库最自然的 Rocq 条目）；Verus/Kani 无法优雅处理变长归纳。
- **矩阵档位**：静态可证明·构造性（【矩阵】:34「**静态可证明（构造性）**：§1.5 归一化算法构造性地保证 guard 两两不相交且并集为真……正确性由构造成立，不是分析结果」）。
- **第四档预留**：可全判位——Rocq 证明工件即第四档证据；**本条是全语言唯一条件边产生点的正确性论证（【提案B】:245），列为最高优先验证对象**（见报告高危 #1）。
- **UNCERTAIN**：无。

## B-15 · route 覆盖性（恰一命中）
- **方向**：property
- **陈述**：归一化后全部守卫（含 default）的析取恒真：`guard_1 ∨ … ∨ guard_n ∨ guard_d ≡ true` ⇒ 路由节点每条出边**恰被一个**守卫命中——不存在零投递或双投递；执行面不得再做去重/仲裁逻辑（守卫已互斥，再仲裁是语义重复）。
- **锚定原文**：
  - 【规范】:48：「且与 default 守卫的并集为恒真——**每条出边恰被一个守卫命中**，不存在零投递或双投递。执行面**不得**再做去重/仲裁逻辑（那是语义重复；守卫已互斥）」
  - 【提案B】:245（并集为真半句，同 B-14 引文）
  - 【提案B】:237（算法步 4）：「边 N→t 携带的 guard = 命中 t 的**第一条**规则的 guard_i（或 default 的 guard_d）」
- **建议证明工具**：Rocq（与 B-14 同一归纳：析取恒真 + 两两不交 ⇒ 恰一）。
- **矩阵档位**：静态可证明·构造性（【矩阵】:34）。
- **第四档预留**：可全判位（与 B-14 同一证明工件的两半）。
- **UNCERTAIN**：无。

## B-16 · route 不可达排除（E2103）与 E2101/E2102 静态校验
- **方向**：soundness + completeness
- **陈述**：①（soundness）同一目标被多条规则命中 ⇒ E2103（后中者不可达，须合并为 `A || B`）；存在出边未被任何规则/default 覆盖 ⇒ E2101；规则/default 的 goto 非法 ⇒ E2102。②（completeness）route 校验通过 ⇒ 每条规则的 goto 目标互不相同且全部出边被覆盖。
- **锚定原文**：
  - 【提案B】:240：「E2101  N 存在出边未被任何规则/default 覆盖」
  - 【提案B】:241：「E2102  规则/default 的 goto 不是 N 的出边目标（也不是 exit）」
  - 【提案B】:242：「E2103  同一目标被多条规则命中（后中者不可达——请合并为 `A || B`）」
  - 【提案B】:1568：「E2101 route 出边未全覆盖；E2102 route 目标悬空；E2103 route 规则不可达（同目标重复）」
  - 【G1裁决】:19：「**default 必填 = E1002**（M4 对任务包文面的纠正，比 E2101 系更准确——default 是 route 构造的形状缺失）」
- **建议证明工具**：Kani（af-dsl route 校验函数 harness，route 测试既有 18 例——G1 裁决 :12——harness 化即第四档化）。
- **矩阵档位**：静态可证明（【矩阵】:34 route 行同域）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无（E2102 的措辞含糊处见报告歧义清单 #5，不影响本条码位级陈述）。

## B-17 · 边投递消费者幂等（就绪集不变）
- **方向**：property
- **陈述**：边投递 at-least-once（执行面崩溃恢复后可能重投）；消费者的入边端口消费幂等：同工件重复到达不重复触发节点——节点激活条件 = 全部必需入边就绪，重投不改就绪集（已就绪端口重复投递是幂等操作）。
- **锚定原文**：
  - 【规范】:56：「边投递 **at-least-once**——执行面崩溃恢复后可能重投（MES outbox 先落盘后发送、删前崩溃会再送一次，poc-ledger 8/8 实证跨库窗口；调度级跨宿主并集去重防重复消耗）。消费者的入边端口消费必须**幂等**：同工件重复到达不重复触发节点（节点激活条件 = 全部必需入边就绪，重投不改就绪集）」
  - 【规范】:54：「边 = 工件引用，不是消息队列」
- **建议证明工具**：Kani（执行面调度核心 harness：非确定重投序列 ⇒ 节点触发次数 = 就绪时刻数 ≤ 1 的断言）；就绪集抽象模型亦可用 Rocq（幂等二元关系）。
- **矩阵档位**：运行时可强制（【矩阵】:39 副作用恰好一次行的传输半边 + 消费幂等机制）。
- **第四档预留**：可建模位——对执行面调度实现建模；「传输层 at-least-once」本身是假设不是保证（【矩阵】:59 诚实边界 5），不进入证明义务。
- **UNCERTAIN**：无。

## B-18 · 幂等键唯一性与重放不重做
- **方向**：property
- **陈述**：副作用级幂等键 = `{stable_id}/{node_id}/{unit_id}/{attempt}` 命名式，由声明面机械生成（静态保证唯一性）；重放同键不重做外部操作；`effect_replays/effect_fresh` 分开计数；图级「恰一次投递效果」由此构造达成（at-least-once 传输 + 业务幂等键），不假设传输层任何更强承诺。
- **锚定原文**：
  - 【规范】:57：「**幂等键【强制】**：副作用级幂等键命名式（IntentKey 泛化）：`{stable_id}/{node_id}/{unit_id}/{attempt}`——键由**声明面机械生成**（静态保证唯一性），重放同键不重做外部操作，`effect_replays/effect_fresh` 分开计数（harness 既有语义，落地契约 §6.2 recovery.idempotency_key）。图级「恰一次投递效果」由此构造达成」
  - 【规范】:13（总则 4）：「**副作用恰好一次 = at-least-once 传输 + 业务幂等键**（§4）；不可假设传输层给任何更强承诺——poc-temporal 实证：activity 执行 2 次、扣款恰好 1 次，靠的是幂等键不是引擎」
  - 【矩阵】:39：「**幂等键的唯一性由命名式构造静态保证**；传输层 at-least-once 是假设不是保证」
  - 【矩阵】:59（诚实边界 5）：「**传输层 at-least-once 是边界不是保证**：所有「恰好一次」效果由幂等键构造达成」
- **建议证明工具**：Rocq（命名式单射性引理：键四元组相等 ⇔ 组成部分相等）+ Kani（执行面重放去重 harness）。
- **矩阵档位**：运行时可强制（幂等键机制，【矩阵】:39 原档）。
- **第四档预留**：单射性引理可全判（Rocq）；重放去重对执行面实现建模可判；attempt 分量的生成纪律见 UNCERTAIN。
- **UNCERTAIN**：**是**——唯一性依赖 `attempt` 分量的单调性（重跑不覆写、尝试序号单调递增，【规范】:12 总则 3「尝试序号单调递增（a1/a2/…）」）；总则 3 是声明面纪律，其机制强制在执行面 TCB（【矩阵】:49「幂等键生成与重放去重」被信任）——若执行面重置 attempt 序列则唯一性破坏，此依赖本条显式登记。

## B-19 · guard 假 = 未发生
- **方向**：property
- **陈述**：守卫为假的边不投递——该工件对消费者不可见，语义是「未发生」而非「丢弃」（不产生投递事件、不占用消费者就绪集）。
- **锚定原文**：
  - 【规范】:58：「守卫为假的边不投递（该工件对本消费者不可见——不是丢弃，是未发生）。守卫求值失败的处置：按 `failures[]` 的 class 处置（求值错误归 environment_failure 面，F2）」
- **建议证明工具**：Rocq（投递关系定义上的直接引理）/ Kani 备选。
- **矩阵档位**：【约定】。
- **第四档预留**：可全判位（小定理）。
- **UNCERTAIN**：无（守卫求值**失败**的归类当前按 F2，但【规范】:99 未定项 4 将其列为待定项——失败路径不进本条陈述，见报告歧义清单 #10）。

## B-20 · envelope 血缘包装
- **方向**：property
- **陈述**：端口类型 `envelope<T>` 的边，运行时包装器填 `from_node/artifact_type/step` 三血缘位；类型在编译期已核（E2201 两端相等），包装忠实性在 TCB——编译期只核类型不验证包装内容。
- **锚定原文**：
  - 【规范】:60：「端口类型 `envelope<T>` 的边，运行时包装器填 `from_node/artifact_type/step` 三血缘位（类型在编译期已核；包装忠实性在 TCB，见保证边界矩阵 L1-typed 工件流）」
  - 【矩阵】:30：「**信封血缘的包装忠实性依赖可信组件（执行时包装器）**：端口类型写 `envelope<T>` 即信封……编译期只核类型不验证包装内容」
- **建议证明工具**：Kani（若包装器实现代码在验证范围内，对其「填值 = 声明面真值」建 harness）；包装忠实性作为体系保证不可机器验证（TCB）。
- **矩阵档位**：静态可证明（类型面）+ 依赖可信组件（包装面，【矩阵】:30 原档拆层）。
- **第四档预留**：类型面可全判（Kani）；包装面只能验证 TCB 成员实现、不能消除信任——第四档字段如实标注。
- **UNCERTAIN**：无。

## B-21 · F3 终态不重试 + 预算 probe 拒绝
- **方向**：property
- **陈述**：①执行终态类失败（F3）不重试：六种 RunStatus 终态已终态；`failures[].terminal: true` 的类直接按 `outcome` 落终态账。②预算耗尽语义：开轮前 probe 拒绝 ⇒ 节点终态 budget_exhausted，不产生第 N+1 次模型调用；已产生消耗保留（拒绝不回滚，af-meter 语义）。③F1 供给瞬态层内退避重试对上层透明，且不消耗图级重试预算。
- **锚定原文**：
  - 【规范】:68：「**F3 执行终态【强制·不重试】**：六种 RunStatus 终态语义已终态，不重试；`failures[].terminal: true` 的类（budget_exhausted 等）直接按 `outcome` 落终态账。预算耗尽语义【强制】：开轮前 probe 拒绝 → 节点终态 budget_exhausted，不产生第 N+1 次模型调用；已产生消耗保留（拒绝不回滚，af-meter 语义）」
  - 【规范】:66：「**F1 供给瞬态【强制·层内透明】**：传输/限流/密钥过期类，harness 层内指数退避重试（HTTP ≤5 次、401 单次重取），对上层透明仅计数。重试不消耗图级重试预算（它们不是节点失败）」
  - 【矩阵】:36：「probe（余额不足不开轮）→ charge（工具后结算）→ 终态 budget_exhausted 不透支不静默」
- **建议证明工具**：Kani（harness 失败处置器：F3 类输入 ⇒ 无重试事件 + 终态账断言）。
- **矩阵档位**：运行时可强制（【矩阵】:36/38）。
- **第四档预留**：可建模位（对 harness 处置逻辑）；「六种 RunStatus」枚举清单在落地契约不在本正本——第四档建模前需先取该清单。
- **UNCERTAIN**：无。

## B-22 · outbox 补偿三崩溃点收敛
- **方向**：property
- **陈述**：跨库/跨服务一致性不假设原子提交；补偿写法 = outbox（本库事务内「业务行+信箱行」→ 对端幂等落回执 → 标 done）⇒ 三个崩溃点（事务后发送前 / 发送后回执前 / 回执后标记前）任一注入崩溃，系统收敛到「账=1、回执=1、真实执行=1」。
- **锚定原文**：
  - 【规范】:71：「跨库/跨服务一致性**不假设原子提交**（poc-ledger：WAL 下跨文件无原子性是硬边界，8/8 分裂实测）——补偿写法 = outbox（本库事务内「业务行+信箱行」→ 对端幂等落回执 → 标 done），三崩溃点注入全部收敛到「账=1、回执=1、真实执行=1」。执行面一切跨账本写遵循此模式；图级补偿动作（撤销已发射工件）v0 不提供（发射即事实，修正走后继工单 supersede——`WorkOrder::successor`，落地契约 §6.2 总则 5）」
  - 【规范】:87（引用表）：「跨库无原子性硬边界（WAL 8/8 分裂）→ outbox 补偿三崩溃点收敛 | poc-ledger `REPORT.md` 裁决一」
- **建议证明工具**：Rocq（崩溃-恢复小步语义上的收敛引理，经典 outbox 形式化）。
- **矩阵档位**：【约定】+ 运行时可强制（【矩阵】:39 援引 poc-ledger 实证）。
- **第四档预留**：可全判位（对抽象 outbox 模型）；「三崩溃点」的具体清单在 poc-ledger `REPORT.md`（本战役未读该文件），第四档建模前需先取。
- **UNCERTAIN**：无（本条按正本结论陈述；崩溃点枚举属后续建模输入）。

## B-23 · 断点续跑安全界
- **方向**：property
- **陈述**：断点续跑前置：递交声明与首启逐项相等才准续跑；余额从落库 current 恢复、不重复扣历史；`Breakpoint::BeforeTurnCommit`（副作用已落、行未提交）是续跑安全界——在该界点恢复不产生重复外部副作用（配合 B-18 幂等键）。
- **锚定原文**：
  - 【规范】:72：「递交声明与首启逐项相等才准续跑（harness check_decl 语义）；余额从落库 current 恢复，不重复扣历史；`Breakpoint::BeforeTurnCommit`（副作用已落、行未提交）是续跑安全界」
- **建议证明工具**：Kani（恢复路径 harness：BeforeTurnCommit 断点注入 ⇒ 恢复后外部副作用计数不变）。
- **矩阵档位**：运行时可强制（【矩阵】:38 失败处置行同域）。
- **第四档预留**：可建模位（对 harness 恢复逻辑）。
- **UNCERTAIN**：无。

---

# C 组 · 确定性组（lower 双跑逐位一致及其分解）

## C-01 · 确定性编译——双跑逐位一致（本组核心定理）
- **方向**：property（对编译器自身）
- **陈述**：同一份 YAML 文档经 af-dsl→af-compiler 管线两次编译，产出的 IR 与计划对象逐字节相同——lower 是输入文档的纯函数（无隐藏状态影响输出）。
- **锚定原文**：
  - 【提案B】:367（句末）：「同一份 YAML 两次编译 → 逐字节相同的 IR 与计划」
  - 【矩阵】:41：「**确定性编译**（同输入两次编译 IR 逐位一致）……全链路 BTreeMap/排序键/无时钟无随机无网络；六 golden 样例逐位断言 ×2 编译。这是**对编译器的测试义务**，不是对外的功能保证」
  - 【G1裁决】:31（G2 判据）：「IR 确定性（两次编译逐位一致）」
- **建议证明工具**：Kani（把编译入口抽为纯函数后建双调用相等 harness）+ golden ×2 断言（既有测试义务的持续兑现）。
- **矩阵档位**：静态可证明·对编译器自身（【矩阵】:41 原档；注意其自我定位是测试义务）。
- **第四档预留**：可全判位——但**口径张力**：【矩阵】:41 说「不是对外的功能保证」，【G1裁决】:31 把 IR 确定性列为 G2 放行判据；第四档入位时需统一口径（见报告歧义清单 #11）。
- **UNCERTAIN**：无（两处正本各自明文，张力在口径不在内容）。

## C-02 · 全链路无 HashMap 参与序列化/迭代序
- **方向**：property（C-01 分解）
- **陈述**：编译管线的 `types/stores/agents/node_exec/escapes` 用 `BTreeMap`；id 集合、CEL 根绑定集合用 `BTreeSet`；无任何 HashMap 参与序列化或迭代顺序 ⇒ 集合遍历序 = 字典序，由内容唯一决定。
- **锚定原文**：
  - 【提案B】:366：「**全链路 BTreeMap/BTreeSet**：`types/stores/agents/node_exec/escapes` 用 `BTreeMap`；id 集合、CEL 根绑定集合用 `BTreeSet`。af-graph 已用 `BTreeMap<String, SubGraph>`（`model.rs:31`）与 `BTreeMap` 邻接表（`validate.rs:312`），B 沿袭——**无任何 HashMap 参与序列化或迭代顺序**」
- **建议证明工具**：Kani（类型级断言 + 两次遍历序相等 harness）；容器字典序性质本身可信于标准库（BTreeMap 结构保证），不必重证。
- **矩阵档位**：静态可证明·对编译器自身（【矩阵】:41 分解项）。
- **第四档预留**：可全判位（工程化：类型检查即可机器断言）。
- **UNCERTAIN**：无。

## C-03 · Vec 输出稳定排序
- **方向**：property（C-01 分解）
- **陈述**：序列化前所有 Vec 输出按稳定键排序：`nodes/edges/stores/policies.*` 按 id 排序；`safety_points` 按路径排序；`carried` 按 store 名排序 ⇒ 输出序列是输入多重集的规范函数（与构建过程顺序无关）。
- **锚定原文**：
  - 【提案B】:367（句首）：「**Vec 输出前按稳定键排序**：`nodes/edges/stores/policies.*` 按 id 排序；`safety_points` 按路径排序；`carried` 按 store 名排序」
- **建议证明工具**：Kani（排序幂等性与置换不变性 harness：任意输入序 ⇒ 输出序相等）。
- **矩阵档位**：静态可证明·对编译器自身（【矩阵】:41 分解项）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## C-04 · route 归一化无搜索、确定性重写
- **方向**：property（C-01 分解）
- **陈述**：route 归一化 = 纯文本重写（规则文档序 + ¬ 前缀展开），不涉及集合枚举或排序策略选择，无搜索、无图分析 ⇒ 归一化输出与（节点 route 规则列表，文档序）一一互定。
- **锚定原文**：
  - 【提案B】:368：「**route 归一化无搜索**：§1.5 是纯文本重写（规则文档序 + ¬ 前缀展开），不涉及集合枚举或排序策略选择」
  - 【提案B】:230：「B 把路由做成节点构造字段后，归一化是**确定性重写**，无需分析」
  - 【规范】:45：「归一化是纯文本重写，无搜索、无图分析（提案 B §1.5）」
  - 【矩阵】:34：「af-dsl `route.rs`（lowering 复用同一函数，无第二实现）」
- **建议证明工具**：Rocq（重写函数的确定性：输入相同 ⇒ 输出相同，且文档序进入输出结构）。Kani 备选（双跑）。
- **矩阵档位**：静态可证明（【矩阵】:34）。
- **第四档预留**：可全判位；「无第二实现」是复用纪律，可由代码审计佐证（本战役未跑代码审计，如实登记）。
- **UNCERTAIN**：无。

## C-05 · 编译期无隐藏输入
- **方向**：property（C-01 分解）
- **陈述**：编译期无时钟、无随机、无网络；digest = 规范序列化（键序=字典序）后取 SHA-256；`shuffle_seeded` 的种子必须来自声明（`seed_ref`）⇒ 编译输出仅依赖文档输入（+ 编译器代码版本）。
- **锚定原文**：
  - 【提案B】:369：「**编译期无时钟、无随机、无网络**：digest = 规范序列化（键序=字典序）后取 SHA-256；`shuffle_seeded` 的种子必须来自声明（`seed_ref`），编译期不产随机数」
- **建议证明工具**：Kani + 工程审计组合——「无隐藏输入」是全程序性质，单 harness 不可完全判定；可验证面 = 编译入口函数签名纯度 + 依赖审计（无 time/rand/net crate 引入编译路径）。如实标注：此条的第四档形态是「审计 + 定点 harness」混合证据。
- **矩阵档位**：静态可证明·对编译器自身（【矩阵】:41 分解项）。
- **第四档预留**：部分可判位（见上）——第四档字段按混合证据形态登记。
- **UNCERTAIN**：无（正本明文；可判定性边界是验证方法论问题，不是文本歧义）。

## C-06 · CEL 编译一次不折叠，运行时同源求值
- **方向**：property
- **陈述**：编译期对 CEL 谓词只 compile 不 eval（v0.1 不做常量折叠），compile 一次缓存 `CelRef`；运行时求值走 CelRef 通道（digest 缓存编译产物，`CelRef.digest` 相同的守卫共享缓存编译产物；panic 兜底）⇒ 同一 CelRef 源的求值结果由运行期输入唯一决定，与编译期无关。
- **锚定原文**：
  - 【提案B】:370：「**CEL 只编译不求值于编译期**（除可常量折叠的守卫，v0.1 不做折叠）：compile 一次、缓存 `CelRef`；eval 走 af-graph `predicate.rs` 通道（含 cel-parser 畸形串 panic 的 catch_unwind 兜底，`predicate.rs:12-15/45-47`）」
  - 【规范】:47：「（同一求值上下文；CelRef.digest 相同的守卫共享缓存编译产物）」
  - 【矩阵】:35：「**CEL 保守子集**……四判全在编译期。**运行时求值通道可信**：执行面按 CelRef.source 重编译求值（digest 缓存），panic 兜底承 af-graph predicate.rs」
- **建议证明工具**：Kani（对 predicate 通道 harness：同 source 双 eval 相等——在相同求值上下文下）。
- **矩阵档位**：静态可证明（四判）+ 运行时通道可信（【矩阵】:35 原档拆层）。
- **第四档预留**：可建模位；若未来引入常量折叠（:370 括号预留），本条需修订后重立。
- **UNCERTAIN**：无（修订触发条件已由正本括号预留明示）。

## C-07 · 降维命名确定性
- **方向**：property（C-01 分解）
- **陈述**：内联体降维的子图名 = 父路径 + `/` + 构造节点 id（如 `voyager/explore/acquire`），机械生成、不依赖哈希或计数器状态；`graph_version` 一律 stamp 父图版本；`entry` = 体 nodes 首元素 ⇒ 命名是文档树的纯函数。
- **锚定原文**：
  - 【提案B】:327：「**内联体降维（确定性命名）**：每个 loop/map 构造生成一个 `SubGraph`，名 = 父路径 + `/` + 构造节点 id（如 `voyager/explore/acquire`）；`graph_version` 一律 stamp 父图版本——**af-graph E2007「map 体未版本化」在 DSL 面因此不可触发**（该码保留给 IR 直写路径）；`entry` = 体 nodes 首元素；嵌套构造递归降维」
  - 【提案B】:372：「**降维命名确定性**：子图名由「父路径/构造 id」机械生成，不依赖哈希或计数器状态」
- **建议证明工具**：Kani（命名函数 harness：嵌套构造随机文档 ⇒ 名字唯一且可从文档树复算）。
- **矩阵档位**：静态可证明（【矩阵】:41 分解项）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无（E2007 在 DSL 面不可触发的推论同 B-05 传递引理结构，前提=降维实现正确）。

## C-08 · 校验顺序固定 ⇒ 违例输出确定性
- **方向**：property
- **陈述**：校验按固定顺序执行：信封 → 形状 → CEL 编译 → 引用闭包 → L0 不变量（INV-1..4）→ 契约核对 → route 归一化，且一次收齐不停第一条 ⇒ Report 的违例集合与生成顺序是输入文档的规范函数（同一文档两次校验产出相同 Report）。
- **锚定原文**：
  - 【提案B】:305-306：「/// 校验顺序固定（保证违例输出确定性）：信封 → 形状 → CEL 编译 → 引用闭包 →\n/// L0 不变量（INV-1..4）→ 契约核对 → route 归一化」
  - 【提案B】:290-291：「/// 报告：全部违例的集合，一次收齐不停第一条（承 af-graph validate.rs:108-125）」「pub struct Report { pub violations: Vec<Violation> }」
  - 【提案B】:1343：「全部一次收齐」
- **建议证明工具**：Kani（双跑 Report 相等 harness，覆盖含多违例文档）。
- **矩阵档位**：静态可证明（【矩阵】:41 同域；一次收齐范式承 af-graph）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：**是**——「违例在 Report 内是否按生成序输出、还是再经稳定排序」正本未明说（:305 只固定**校验**顺序，:290 只说集合一次收齐）；本条按「生成序即输出序」的弱陈述立，强陈述（跨阶段违例的全局排序键）待规范补文（见报告歧义清单 #8）。

## C-09 · 拒绝式信封与 unknown_kinds 诊断
- **方向**：soundness + property
- **陈述**：①（soundness）版本不符或信封未知键 ⇒ 整份拒绝、body 不解析（装载即校验、失败路径点名不静默降级）。②（property）未注册 kind 只进 `unknown_kinds: BTreeSet<String>` 按字典序去重的诊断集合，不是违例、不拒绝编译。
- **锚定原文**：
  - 【矩阵】:42：「**拒绝式信封**（DSL 版本信封 / IR `ir_version` / 计划对象 deny_unknown_fields）……版本不符或未知键整份拒绝、body 不解析；装载即校验、失败路径点名不静默降级」
  - 【提案B】:371：「**未注册 kind 只进诊断**：`unknown_kinds: BTreeSet<String>` 按字典序去重（承 af-graph `validate.rs:224-232` 的 extension_kinds），不是违例」
- **建议证明工具**：Kani（信封 reject harness + unknown_kinds 字典序断言）。
- **矩阵档位**：静态可证明（【矩阵】:42 原档）。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

---

# D 组 · 状态机组（af-workorder 订单状态机）

依据：【state】`af-workorder/src/state.rs` 实际状态机（两工作树 diff 逐字节相同，战役内实跑确认）；门控实现【order】`order.rs`。模块职责分工（【state】:3-5）：「状态机只回答"这条边存不存在"；前置条件门控……在 `crate::order::WorkOrder` 中实现，两者分开：非法转换报 `GateError::IllegalTransition`，门控不满足报 `GateError::PreconditionsNotMet`」。

## D-01 · 跃迁表恰为声明生命周期
- **方向**：property（表完备性）
- **陈述**：`allowed_transitions` 逐状态恰为：Created → {Release, Cancel}；Released → {Start, Cancel}；InProgress → {Complete, Cancel}；Completed → {Close}；Closed → ∅；Cancelled → ∅——此表即全部合法边，不在表内的 (from, to) 组合一律拒绝。
- **锚定原文**：
  - 【state】:58-67：「/// 合法出边。不在表内的 (from, to) 组合一律拒绝。」「`Created => &[Transition::Release, Transition::Cancel]`」「`Released => &[Transition::Start, Transition::Cancel]`」「`InProgress => &[Transition::Complete, Transition::Cancel]`」「`Completed => &[Transition::Close]`」「`Closed | OrderState::Cancelled => &[]`」
  - 【state】:89-108（既有测试 `transition_table_is_exactly_the_asked_lifecycle` 全表断言）
  - 【state】:1：「订单状态机:created → released → in_progress → completed → closed,可 cancelled」
- **建议证明工具**：Verus（表常量与断言的等价——把既有单测升级为 Verus 规约）；Kani 备选。
- **矩阵档位**：（af-workorder 不在【矩阵】三档表内——本组条目按其性质归「静态可证明（代码结构事实）」；订单层保证边界待第四档落地时补入矩阵。）
- **第四档预留**：可全判位（最轻量的一组——表断言的机器化）。
- **UNCERTAIN**：无。

## D-02 · 无非法跃迁
- **方向**：soundness（违例必拒）
- **陈述**：对任意状态 s 与跃迁 t：`s.can_apply(t) = false` ⇒ `transition(t)` 返回 `Err(GateError::IllegalTransition{from: s, to: t.to_state(), allowed})`，且 `self.state` 不变（迁移不落地、履历不追加）。
- **锚定原文**：
  - 【order】:431-440：「/// 通用迁移入口:先查状态机边,再查门控;两条都过才落状态并记履历。」「`if !from.can_apply(t) { return Err(GateError::IllegalTransition { from, to: t.to_state(), allowed: from.allowed_transitions().to_vec(), }); }`」
  - 【state】:69-75（`can_apply` 实现：Cancel 三起点特判 + 表内查含）
  - 【state】:4：「非法转换报 [`crate::error::GateError::IllegalTransition`]
- **建议证明工具**：Verus（状态机经典形态：对全部 (s, t) 组合的 case 断言——状态 6 × 跃迁 5 = 30 例穷举可机器全判）。
- **矩阵档位**：静态可证明（代码结构事实）。
- **第四档预留**：可全判位（穷举域有限，最易闭环）。
- **UNCERTAIN**：无。

## D-03 · 终态吸收
- **方向**：property
- **陈述**：Closed 与 Cancelled 的 `allowed_transitions` 为空表；`is_terminal()` 恰等于 {Closed, Cancelled}；终态上任何 `transition` 调用必被 D-02 拒（IllegalTransition）——终态不可迁出（吸收态）。
- **锚定原文**：
  - 【state】:65：「`Closed | OrderState::Cancelled => &[]`」
  - 【state】:77-79：「`pub fn is_terminal(self) -> bool { matches!(self, OrderState::Closed | OrderState::Cancelled) }`」
  - 【state】:121-125（既有测试 terminal_states）
- **建议证明工具**：Verus。
- **矩阵档位**：静态可证明。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## D-04 · Cancel 窗口
- **方向**：property
- **陈述**：`Transition::Cancel` 仅可自 {Created, Released, InProgress} 施加；在 Completed/Closed/Cancelled 上 `can_apply(Cancel) = false`——完成即不可取消。
- **锚定原文**：
  - 【state】:31-33：「/// created/released/in_progress → cancelled」「`Cancel,`」
  - 【state】:70-73：「// Cancel 的起点是三个状态,单独判断。」「`if t == Transition::Cancel { return matches!(self, Created | Released | InProgress); }`」
  - 【state】:110-118（既有测试 `cancel_allowed_only_before_completion` 六状态断言）
- **建议证明工具**：Verus。
- **矩阵档位**：静态可证明。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## D-05 · from_state 全函数性（Cancel 除外）
- **方向**：property（结构引理）
- **陈述**：对 t ≠ Cancel，`Transition::from_state(t)` 是单值全函数，且 `(from_state(t), to_state(t))` ∈ 合法边集（即 from_state(t) 的 allowed_transitions 含 t）；`from_state(Cancel)` 无单一起点（实现为 `unreachable!`，由 `can_apply` 对 Cancel 的三起点特判补偿）——若未来新增多起点跃迁而沿用 `from_state`，`unreachable!` 会 panic：这是结构债务点，非正确性缺口。
- **锚定原文**：
  - 【state】:36-44：「`pub fn from_state(self) -> OrderState { match self { Transition::Release => OrderState::Created, … Transition::Cancel => unreachable!("Cancel 起点不止一个,由 allowed_transitions 决定"), } }`」
  - 【state】:46-54（`to_state` 全函数五分支）
- **建议证明工具**：Verus（对 t ≠ Cancel 的引理 + to_state 与跃迁表的一致性）；unreachable 分支的排除本身用 Verus `ensures` 前置条件表达。
- **矩阵档位**：静态可证明。
- **第四档预留**：可全判位；审计提示见报告高危 #3。
- **UNCERTAIN**：无。

## D-06 · 状态机/门控双轨分离
- **方向**：property（职责界定）
- **陈述**：状态机层只回答跃迁边存在性；前置条件门控独立核对——Release 门控 = 产线版本已绑定 + 预算凭证已签发（存在且 signed）；Close 门控 = 存在合格终态工件（`is_final && qualified`）；非法转换报 `IllegalTransition`、门控不满足报 `PreconditionsNotMet`（携带类型化 `Vec<Missing>`，缺失清单顺序固定：产线在前、凭证在后），两错误不混淆；两条都过才落状态并记履历。
- **锚定原文**：
  - 【state】:3-5：「状态机只回答"这条边存不存在";前置条件门控(绑定产线版本/预算凭证/合格终态工件)在 [`crate::order::WorkOrder`] 中实现,两者分开:非法转换报 [`crate::error::GateError::IllegalTransition`],门控不满足报 [`crate::error::GateError::PreconditionsNotMet`]」
  - 【order】:431：「/// 通用迁移入口:先查状态机边,再查门控;两条都过才落状态并记履历。」
  - 【order】:441-451（门控核对与 `PreconditionsNotMet` 返回，状态未落地）
  - 【order】:403-404：「/// release 前置:① 已绑定产线版本;② 预算凭证已签发(存在且 signed)。/// 返回缺失清单,顺序固定(产线在前、凭证在后),保证错误可复现、可断言。」
  - 【order】:420-427（`close_missing`：「/// close 前置:存在合格终态工件(is_final && qualified)」）
  - 【order:error.rs】:2：「所以 [`GateError::PreconditionsNotMet`] 携带类型化的 `Vec<Missing>`,而不是一个字符串。」
- **建议证明工具**：Verus（错误类型与核对顺序的规约）+ Kani（缺失清单顺序断言）。
- **矩阵档位**：静态可证明。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## D-07 · 迁移履历完备性
- **方向**：property
- **陈述**：每次成功 `transition` 恰追加一条 `HistoryRecord{from, to}` 且 `to` = 迁移后状态；门控或状态机拒绝时不追加任何记录 ⇒ history 序列是成功迁移序列的忠实记录（长度 = 成功迁移次数；相邻记录链相接：前一条的 to = 后一条的 from）。
- **锚定原文**：
  - 【order】:452-457：「`self.state = t.to_state();`」「`self.history.push(HistoryRecord { from, to: self.state, });`」「`Ok(self.state)`」
  - 【order】:431（「两条都过才落状态并记履历」——拒绝路径 :435/:447 先于 :452 返回）
- **建议证明工具**：Verus（历史不变量：链相接 + 长度对应）。
- **矩阵档位**：静态可证明。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

## D-08 · 状态机幂等性（无自环）与执行单元终态幂等（两层，不合并）
- **方向**：property
- **陈述**：①（订单层）跃迁表中无自环（(s, s) 不是合法边）⇒ 对已处状态 s 重复施加刚成功过的同一 Transition 必被拒——状态机面不存在「重复成功」，重复调用以 IllegalTransition 表达幂等拒绝。②（执行单元层，语义参照）已终态的执行单元重复调用返回同一报告、不再触发模型调用——这是 harness 执行单元语义，不是 WorkOrder 状态机机制；两层「幂等」是不同机制，不可互相推导。
- **锚定原文**：
  - 【state】:59-67（表内逐行核对：无任何 `s => [.. s ..]` 自环分支——D-01 表即证据）
  - 【规范】:11（总则 2）：「**终态即答案**：已终态的执行单元重复调用返回同一报告，不再触发模型调用（harness `run.rs` 既有语义）」
  - 【规范】:12（总则 3）：「**重跑不覆写**：尝试序号单调递增（a1/a2/…），旧目录是复核证据」
- **建议证明工具**：Verus（①：无自环是 D-01 表断言的推论）；②的机制在 harness（本战役未读 run.rs，只立语义引用，不做实现级陈述）。
- **矩阵档位**：①静态可证明；②运行时可强制（harness 既有语义声明）。
- **第四档预留**：①可全判；②需 harness `run.rs` 进入验证范围后另行立条。
- **UNCERTAIN**：无（两层区分本身是本条的目的；②的实现级定理不在本战役范围，如实标注）。

## D-09 · release/close 门控内容的确定性
- **方向**：property
- **陈述**：`release_missing` 返回缺失清单顺序固定（产线在前、凭证在后），保证错误可复现、可断言；`close_missing` 只查「存在 `is_final && qualified` 的工件」；门控失败（清单非空）时返回 `PreconditionsNotMet` 且状态不变。
- **锚定原文**：
  - 【order】:403-418（`release_missing` 全函数：`line.is_none() ⇒ Missing::LineVersionNotBound`；voucher 缺 ⇒ `BudgetVoucherNotIssued`；voucher 未签 ⇒ `BudgetVoucherNotSigned{voucher_id}`）
  - 【order】:404：「/// 返回缺失清单,顺序固定(产线在前、凭证在后),保证错误可复现、可断言。」
  - 【order】:420-427（`close_missing`）
  - 【order】:446-451（清单非空 ⇒ `PreconditionsNotMet`，先于 :452 状态赋值返回）
- **建议证明工具**：Kani（缺失清单内容与顺序的组合断言：给定 (line, voucher) 状态 ⇒ 清单唯一确定）。
- **矩阵档位**：静态可证明。
- **第四档预留**：可全判位。
- **UNCERTAIN**：无。

---

## 附：覆盖核对表（自检）

| 验收项 | 要求 | 实况 |
|---|---|---|
| 总条数 | ≥40 | **57** |
| A 组 INV | ≥5 | 16（四条不变量 × soundness/completeness 两方向齐备：A-01..A-06=INV-1、A-07..A-10=INV-2、A-11..A-13=INV-3、A-14..A-16=INV-4） |
| B 组构造语义 | ≥5 | 23（loop 迭代边界 B-01/B-02、carried B-03..B-05、安全点 B-06、exit B-07/B-08、map B-09..B-13、route 互斥覆盖 B-14..B-16、边投递幂等 B-17..B-20、重试补偿 B-21..B-23） |
| C 组确定性 | ≥5 | 9（核心 C-01 + 分解 C-02..C-09） |
| D 组状态机 | ≥5 | 9（无非法跃迁 D-02、幂等 D-08、表完备 D-01/03/04/05、双轨 D-06、履历 D-07、门控 D-09） |
| 每条锚定原文 | 必须 | 57/57（文件别名+行号+逐字摘录） |
| G1 语义裁决 | 注意 | B-08 全条按裁决读法（【G1裁决】:18），B-14/15/16 与裁决一致 |
| 第四档预留位 | 必须 | 每条含「矩阵档位 + 第四档预留」双字段（§0.1 定义） |
| 只译不证 | 禁止证明 | 全库为陈述 + 建议工具，无证明内容 |
| UNCERTAIN 如实 | 如有 | 8 条（A-04、B-02、B-04、B-06、B-11、B-13、B-18、C-08），逐条写明拿不准的具体方向 |
