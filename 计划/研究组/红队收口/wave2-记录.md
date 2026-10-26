# 红队第 2 波（W2）全程记录

- 日期：2026-10-26（候选投喂 → 裁判裁定 → 修复收口，全程当日完成）
- 波次对象：第二阶段交付全景 + W1 修复面自身（af 仓 @438fa6d + phase2-redteam-fixes + 工作区文书）——判分链/预算面/身份面/文档口径六向审计
- 修复执行：红队修复员（glm5.3），工作树 /home/pan-ding/workspace/af-wt-redteam（分支 phase2-redteam-fixes，基于 origin/phase2 @438fa6d + W1 修复 11 commit）
- 硬线核验：ci/run.sh 九门全绿——修复员亲跑 exit 0（step1-8 PASS + step9 ADVISORY-PASS；9b 断言 32 verified/0 failures/32 total）；产物入档 commit 641bf64/208906c/033b847/252878c 后终跑
- 本记录路径（返回路径确认）：/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/红队收口/wave2-记录.md
- 本记录口径：裁定分布按实际 verdict 计；席/候选明细以裁定书所引 sources 为准（可机算面），未引用编号如实注记不臆测
- **漏检根因存档**：逐条「根因/本应拦在/改进」分析=后台产物另档（whys artifact，**按波次覆盖**、不保证跨波留存）——本记录不内联其内容；波次收官如需留存须随波次另档拷贝，勿依赖覆盖前的后台产物

## 一、12 席清单

| # | 席（source 前缀） | 焦点 | 裁定 sources 引用（编号/条数） |
|---|---|---|---|
| 1 | `plan` | 计划/承诺对照席（总计划 §0/§2/§6 × 交付实况，含 W1 修复面） | 5 条：plan-01、plan-02、plan-03、plan-04、plan-05 |
| 2 | `evidence` | 证据指针核验席（门终裁/文书数字 × git/实盘复算） | 1 条：evidence-02 |
| 3 | `a1chain` | A1 验收链对账席（总账/台账/交付文/代码四方一致性） | 3 条：a1chain-01、a1chain-04、a1chain-06 |
| 4 | `cross` | 跨文书一致性席（数字/口径跨文书传播链） | 5 条：cross-01、cross-02、cross-03、cross-04、cross-05 |
| 5 | `docs` | 状态/活文档席（AGENT/质检体系/组件状态/总计划/仓内 README/VERSIONS/SYNTAX） | 7 条：docs-01、docs-02、docs-04、docs-05、docs-06、docs-07、docs-08 |
| 6 | `dsl` | af-dsl 语义面席（E 码判定面/词法闸/envelope 整性/is_final 推导） | 3 条：dsl-01、dsl-02、dsl-03 |
| 7 | `compiler` | af-compiler 席（lower is_final/偏差表全量/预算 scope 展开口径） | 3 条：compiler-01、compiler-02、compiler-03 |
| 8 | `execline` | af-execline 执行面席（判定字段/逃逸面/预算双相/深度帽/装订互核/line 接线） | 7 条：execline-01、execline-02、execline-03、execline-05、execline-06、execline-07、execline-08 |
| 9 | `order` | af-order 门面席（graph_version 期待源/show 路径/负帽前置） | 3 条：order-01、order-03、order-04 |
| 10 | `fv` | 形式验证席（proofs 覆盖率披露/Rocq 前提） | 3 条：fv-02、fv-03、fv-04 |
| 11 | `adv` | 对抗/可作弊面席（pyc 影子执行/event_id 跨根相撞/旗标假回显/plan digest/引擎锚） | 5 条：adv-01、adv-02、adv-03、adv-04、adv-05 |
| 12 | `ops` | 运维/退役面席（/tmp 配额/预期灯枚举/取证时序） | 3 条：ops-03、ops-04、ops-05 |

十二席产出候选合纪 **58 条**。其中 45 条 real-defect 裁定的 sources 合计 **48 个编号引用**（3 项多源并案：W2-C-08 引 2 源 a1chain-01+cross-01；W2-C-11 引 2 源 a1chain-04+cross-02；W2-C-42 引 2 源 fv-02+cross-03——并案语义=同一缺陷多席独立命中，修复按并案后缺陷计一次）；其余 **13 条非 real 候选**（12 not-defect + 1 handled）的个体编号未随修复材料下发——按编号连续性可辨 22 个未入任何 real 裁定 sources 的编号（evidence-01/03/04/05、a1chain-02/03/05、cross-06/07/08、dsl-04/05、compiler-04、execline-04/09、order-02、fv-01、adv-04/06、docs-03、ops-01/02），非 real 个体与该缺口集的关系（缺口含非 real 候选或含空号）以裁判侧裁定正本为准，本记录不臆测。

## 二、候选与裁定分布

- 候选总量：**58 条**（十二席产出）
- 裁定分布（按实际 verdict 计）：**real-defect = 45 / overturn = 0 / not-defect = 12 / handled = 1**（45+0+12+1=58 闭合）
- real 45 的构成：代码/仓内缺陷 19 条（af-dsl 3 / af-compiler 1 / af-execline 7 / af-order 3 / af 仓内文书与索引 5）+ 工作区文书/口径缺陷 26 条（计划承诺面 5 / A1 链 3 / 跨文书 3 / 运维面 3 / 状态与活文档 7 / proofs 与 Rocq 3 / 总计划口径 2）
- 修复结果：**45/45 全部修复**（fixed=true，逐条见 §四），代码缺陷走 TDD（先红后绿）+ 九门全绿硬线，文书缺陷原地勘误并留勘误注记；W2-C01（逃逸舱占比）按可复算口径判定为**未达标**（97/247=39.3%>30%），阈值不弱化、处置待运营者——不以换指标方式过检

## 三、修复载体

| 类别 | 位置 |
|---|---|
| 代码/仓内文档（af 仓） | 分支 phase2-redteam-fixes（工作树 ~/workspace/af-wt-redteam），5 个 commit：ff68d80（af-dsl/compiler/execline 十项：C-23/24/25/26/29/31/33/34/35/36）/ fa0ec74（execline/order 九项：C-30/37/39/40/52/53/54/55/56）/ 641bf64（fmt/clippy/中立性词表收尾）/ 208906c（C-42/43/44 + 词表行号）/ 033b847（C-04 索引清理 + C-27/28/47/48/49/50/51）/ 252878c（ADR-012） |
| 工作区文书（原地勘误） | 计划/研究组/{A1-稳定性验收-终验,G4-门终裁,F-第四单-交付,G3-全链闸门-L1L4-v2,G4-研究报告包设计-v1,G5-健康度首报,退役执行记录,旧bench退役归档-runbook}-*.md；计划/{00-总纲→.zcode/plans/plan-session_*.md,20-质量保证体系,30-遗产处置,技术债登记}.md；AGENT.md；状态/{机器清单,组件建设状态}.md；计划/研究组/红队收口/wave1-记录.md（W1-C42 数字同步） |
| 硬线核验 | `bash ci/run.sh`（CARGO_TARGET_DIR=~/afbuild-phase2rt）终跑 exit 0：step1（fmt+K5 lint）/step2 clippy/step3 test/step4 cue/step5 scrub/step6 cosign/step7 deny/step8 neutrality 全 PASS + step9 FV ADVISORY-PASS（9b 断言 32 verified/0 failures/32 total）——ci/out/SUMMARY.txt 随批入档 |

## 四、修复清单（real 45/45，逐条；非 real 13 条无修复面，个体编号以裁判侧正本为准）

汇总：id / 状态 / commit（工作区原地勘误者 commits 为空）：

| id | fixed | commits |
|---|---|---|
| W2-C-01 | ✅ | —（工作区：G5 首报+总计划口径记录） |
| W2-C-02 | ✅ | —（工作区：A1+G4 门终裁） |
| W2-C-03 | ✅ | —（工作区：总计划 A4/W5） |
| W2-C-04 | ✅ | 033b847 |
| W2-C-05 | ✅ | —（工作区：总计划 §6） |
| W2-C-07 | ✅ | —（工作区：G3-v2:17） |
| W2-C-08 | ✅ | —（工作区：A1:12） |
| W2-C-11 | ✅ | —（工作区：A1:15+G4:10/:12） |
| W2-C-13 | ✅ | —（工作区：F-第四单:72） |
| W2-C-18 | ✅ | —（工作区：退役执行记录:132） |
| W2-C-19 | ✅ | —（工作区：退役执行记录:132） |
| W2-C-20 | ✅ | —（工作区：30-遗产处置:22） |
| W2-C-23 | ✅ | ff68d80 |
| W2-C-24 | ✅ | ff68d80 |
| W2-C-25 | ✅ | ff68d80 |
| W2-C-26 | ✅ | ff68d80 |
| W2-C-27 | ✅ | 033b847 |
| W2-C-28 | ✅ | 033b847 |
| W2-C-29 | ✅ | ff68d80 |
| W2-C-30 | ✅ | fa0ec74 |
| W2-C-31 | ✅ | ff68d80 |
| W2-C-33 | ✅ | ff68d80 |
| W2-C-34 | ✅ | ff68d80 |
| W2-C-35 | ✅ | ff68d80 |
| W2-C-36 | ✅ | ff68d80 |
| W2-C-37 | ✅ | fa0ec74 |
| W2-C-39 | ✅ | fa0ec74 |
| W2-C-40 | ✅ | fa0ec74 |
| W2-C-42 | ✅ | 208906c |
| W2-C-43 | ✅ | 208906c |
| W2-C-44 | ✅ | 208906c |
| W2-C-45 | ✅ | —（工作区：AGENT/20/组件状态） |
| W2-C-46 | ✅ | —（工作区：组件建设状态:9） |
| W2-C-47 | ✅ | 033b847 |
| W2-C-48 | ✅ | 033b847 |
| W2-C-49 | ✅ | 033b847 |
| W2-C-50 | ✅ | 033b847 |
| W2-C-51 | ✅ | 033b847 |
| W2-C-52 | ✅ | fa0ec74 |
| W2-C-53 | ✅ | fa0ec74 |
| W2-C-54 | ✅ | fa0ec74 |
| W2-C-55 | ✅ | fa0ec74 |
| W2-C-56 | ✅ | fa0ec74 |
| W2-C-57 | ✅ | —（工作区：技术债 D-2） |
| W2-C-58 | ✅ | —（工作区：G4-研究报告包设计:358/:361） |

逐条修复方式（how）：

#### W2-C-01

- **修复**：G5-健康度首报 §二.1 立可复算口径（逃逸舱占比 = Σ body.escapes ÷ Σ body.node_exec，15 份对齐稿 golden IR 点号路径口径；97/97 逃逸路径命中节点，机核 off_node=0）+ 30% 阈值判定：**97/247=39.3%>30% 未达标**（逐稿 22.2%~72.7%，11/15 稿超线）；候选口径 escapes/(escapes+nodes)=28.2% 不采用（逃逸是节点属性非独立表达点，该分母重复计数）已附理由。总计划 L-G5 行旁登口径定义记录，阈值维持原值不弱化，调阈/收敛属运营者裁决。

#### W2-C-02

- **修复**：A1 判据行 trace 项附 caveat：swev/report 布局工具核验 exit=0；**F4D（graph 布局）af-trace-tree-verify 实为 exit=1/findings 2（L1→L2 records 无 evidence.run_dir、L2 引用 run 未建立）——存量 F4D 仅为人工亲读证据、不得追认工具核验通过**；G4-门终裁:10/:12 同条勘误；W1-C36 起新 graph 单落 evidence.run_dir 可工具核验的说明在案。

#### W2-C-03

- **修复**：总计划 A4 与 W5 R-完成「七门 CI 全绿」→「九门（step1-8 硬门 + step9 FV advisory 非阻塞）」并说明 advisory 属性，与 AGENT.md 硬纪律5/00-总纲 §2.2 同口径。

#### W2-C-04

- **修复**：`git rm -r --cached poc/poc-temporal/rust-sdk-smoke/target`（3,191 文件）执行索引清理；git 对象复算口径 3,191 blob/5,137,623,292B≈4.78GiB（候选 1.6G 为工作树 du 口径失真）登记 30-遗产处置 批6；历史过滤（filter-repo/BFG）明确决定暂不做、需运营者裁决（GitHub 镜像既有 >100M 剥离分工不变）；CI 依赖面（poc-cue/poc-cas）不涉该目录，九门复跑不受影响（亲跑 exit 0）。

#### W2-C-05

- **修复**：总计划 §6 交付物清单「使命指令 D1–D10」加不可核对标记：原文未归档至工作区（全工作区检索仅命中计划自身引用与门终裁 G0-G5 判据片段），收口审计对该部分只能标「无法核对」、不以推测填充；归档原文/权威链接 + D1-D10→交付证据逐项映射登记为后续认领项。

#### W2-C-07

- **修复**：G3-全链闸门-L1L4-v2:17「根级 components.json（7→44 条）」→「2→44 条（+42）；跨文件总量 7→57」（`git show aff4f1a~1:...` 亲数根级 2 条；同文书:82 与 commit message 的 +42 佐证）；其余总量与分类分布不变。

#### W2-C-08

- **修复**：A1:12 F4a/F4a2/F4a3 行改 astropy-12907 + 「失败路径 MES 修复验证探针」（spec-F4a.json:5/spec-F4a3.json:5 原文在案，验证主线 f7ddaed），与 F3 预算探针、F4C 预算校准三者目的区分；原「django-11099 同题；F4 系预算校准用」与订单目录名/records item_id 均不符已注明。

#### W2-C-11

- **修复**：A1:15 与 G4-门终裁:10/:12 的 F4D「在径 resolved=true」改「在径 verdict=true；独立 resolved=true 系 close 后打捞复现」，显著登记判据② fail（results.jsonl 0 字节 + 非打捞口径证据缺位）与代码事实（graph_unit 在径只产 tester pass 布尔）；禁止以原表述关闭该项。

#### W2-C-13

- **修复**：F-第四单-交付:72 A/B 对照去「唯一变量=修复本身」——实测 F3a2（turns=2/unit_calls=2/quota 3312/228/1024、3 次 bash effect）与 F4a3（turns=0/unit_calls=0/quota 全 0/wall 1402ms）输入参数不同，存在混淆变量；改述「同任务同门控形态、不同预算/调用参数的修复前后对照」，修复有效结论由 CH 0→3 结果差支撑，严格受证需同参数重做。

#### W2-C-18

- **修复**：退役执行记录:132 A4L 灯去「与本批无关」表述：/tmp 实测已低于告警自述 2252MiB 闸线（df 7.5G/6.0G 已用；alarms.log 自 01:36 起全程越线；harness 已实际发生 /tmp 写入配额失败）。**/tmp 头寸纳入观察期硬判据**：清理/提额属主=运营者（usrquota 裁决），清理候选机算在案（du 头部 sk-test 999M/sbkit 993M/sbvenv 875M 等 10-26 评判探针残留，修复员已清 W2 探针项回收约 3.1G），定时动作待立。

#### W2-C-19

- **修复**：A7（sweb.eval 0/120 停滞）补入预期灯枚举——image-feed 已退役、镜像实测 0 张、该灯永不自清；watch 判据更新批须将其改「停止供给」显式状态或禁用。

#### W2-C-20

- **修复**：30-遗产处置:22 取证时序如实：第 1 条（13:34:37）data_dir_present=false、第 2 条（13:35:11）true，34s 差异为取证脚本首发竞态非目录状态变化；禁止把第 2 条在场性倒写为首条结论，附复测方式（重跑 tools/mes-ttl-decision-point.py）。

#### W2-C-23

- **修复**：refs.rs E2202 matched 按端口名去重（emits 显式内建端口与 builtin_ports 同名同型不重复计数——["done","done"] 假拒合法文档）；附带把 EmitSpec 映射形补 PortType `{type: 原始四型}` 一致性（此前 emits 面不收该形而 meta.output.ref 面收，check/gate 显式 passed 声明不可表达）。回归：refs_test 显式 done/passed 同名两例 + 不同名同型仍拒反向例。

#### W2-C-24

- **修复**：cel.rs lex_scan 的 pending_has/ident 跨越 // 行注释存活（`/` 分支不再预清，除号形态在 slash_pending 分支才清）——`has //c\n(x)` 不再绕 E1052；块注释仍拒（文法不收）。回归：cel_test 三种注释隔断形全拦 + 注释文本内 has( 不误伤（W1-C23 口径不回退）。

#### W2-C-25

- **修复**：envelope.rs 整性判定与 i64 窄化分离——u64>i64::MAX 的 version 归 E0003「整数≠1（越界大整数）」而非 E0002「非整数」（RESULT-M1 码表语义）。回归：envelope_test i64::MAX+1 与 u64::MAX 两形。

#### W2-C-26

- **修复**：af-dsl 新增公开 `derived_emit_type`（Index/emit_type 同规则，防 IR 复制推导器）；lower.rs is_final 对 from_body 端口须推导类型等于 meta.output.ref——非同型 from_body（extra: worker.bad）不再误标终态（执行面 final_artifact_port 取首个 is_final 即选错工件）。回归：plan_test loop collector 双 from_body 探针（final 承位/extra 不承位）。

#### W2-C-27

- **修复**：RESULT-G2b 偏差表补登 #18-#21：node_exec[].context（Vec<SectionSpec>）、node_exec[].consumes（BTreeMap）、artifact_contract[].r#type（Option<String>）、node_exec↔graph.nodes 非 1:1（全点号路径投影 vs 根图节点，装订期按归属核对）；sample2 实证（7 vs 4+subgraphs）。表 17→21 条。

#### W2-C-28

- **修复**：执行语义规范-v0 §6.5 口径修正：仅 `node:<路径>` 投影进 node_exec[].budget；plan/loop/map 作用域条目原留计划级 budget.budgets 段、不生成节点级 BudgetRef（计划面无该类型）；强制由执行面读计划级数组完成（PlanBudgets::of/RingBudgets::of 白名单）；附 paper_report 实例（三条 plan/loop 条目全留计划级、6 条 node_exec budget 全空）。

#### W2-C-29

- **修复**：graph_unit 终态判定改 schema 声明驱动——类型 schema 的布尔属性里 pass 优先、resolved 次取（swebench 口径）；无判定字段 = 产物型终态（产出即合格）；判定字段在场而载荷缺 = None = 不 qualified（禁止缺字段推定成功）。回归：graph_unit 单节点 resolved false/true 两形。

#### W2-C-30

- **修复**：planbind 装订期拒收携带 escape 节点的计划（点名 impl_ref/kind/owner/reason）——fix_swe_task 的 env_boot（executor:builtin/sweng.env_boot@af-execline，sweng 内置表无此实现）不再带到执行相才以错向 EX3001 失败；编译 exit 0 不冒充 E2E 可执行。回归：pkg_sweng_package fix_swe_task 编译产物 bind 拒收例。

#### W2-C-31

- **修复**：双相熔断第二相——graph 节点 commit 后、报告环成员完成后各加一次 budget.gate 三维对账（cents=有效帽 min(spec,plan)/turns/tokens_total in+out+cache_read）；终态超帽不得完工（此前只在起动前 gate，终态超帽照常 check_typed/判定/落行）。回归：graph_unit 单节点 plan token_cap=100 终态 160 tokens 完工前熔断例。

#### W2-C-33

- **修复**：graph_unit http_retries 两路径（AgentRunOutcome/AgentRunFailure）累加入 Drive 账并进 ExecutionFacts→v1 行 usage.http_retries（此前 Ok 路径随 `..` 丢弃、facts 硬编码 0——401 重取不可审计）。回归：graph_unit sop_full retries=7 → v1 行 21（3 节点累账口径）。

#### W2-C-34

- **修复**：materialize_schema 增深度帽 16（与 inline_named_refs 同口径）——深层 list<list<...>> 干净返回 None → 下游 check_typed 按「基名不在 types」转 EX4006，不在契约构造位无界递归/栈溢出。回归：graph_corpus_adv type 族 deep-list-nesting-32 例（期待 EX4006）。

#### W2-C-35

- **修复**：PlanBudgets::of 对 node: turns 条目与 node_exec 投影按 (node_id,dimension) 互核 cap——plan 级声明与投影不一致即拒（手改计划改小声明留大投影 = 静默免帽，执行面消费投影值）。回归：graph_corpus_adv budget 族 node-turns-projection-mismatch 例（期待 EX4005）。

#### W2-C-36

- **修复**：graph/report 两单元 BindExpectations.line_id 由 None 改传订单已绑定 line（driver bind_line 先于 execute）——planbind ③ 的 line 复验分支从死代码变为生产接线，携带其他产线 line_id 的手写计划可拒。回归：graph_corpus_adv line 族 carried-line-conflicts-with-order 例（期待 EX4005）。

#### W2-C-37

- **修复**：driver ExecContext.graph_version 期待源由 cfg（cli 每 submit 从当前 plan.json 重读）改订单快照不可变绑定 order.graph_version()——换计划图版本重放时期待(旧) vs 计划(新) 不符即拒（此前自指校验恒真）。残留价值限同次 submit 内 TOCTOU，ADR-011 裁决7「真核对」在生产缝落实。

#### W2-C-39

- **修复**：run_show 位置参数共用 spec::validate_order_id 路径安全门（拒绝对路径/分隔符/`..`/空白，映射 OR1001 用法错误先于任何读取）——此前绝对路径替换 state 根可读出目录外 ledger.jsonl。回归：cli show_rejects_path_unsafe_order_ids 四形 + rogue 对照。

#### W2-C-40

- **修复**：--spend-cap-cents 负/零值 CLI 解析期前置拒（OR1001，先于订单目录/凭证/MES 产生；此前负帽直到 af-harness 凭证签发才拒、污染订单已形成）；max_turns=0 零模型探针语义保留（spec-F4a3 同款）。回归：exec_contract spend_cap_nonpositive_rejected_at_parse 两形 + max_turns=0 正例。

#### W2-C-42

- **修复**：proofs README 57 分母覆盖率按编号机算更正：原「39 有载体 + 15 条(26%)无载体」算术不闭合（39+1+3+1+15=59≠57）且枚举数与声称数不符；更正为 **40 条有内核裁决载体 / 12 条无直接证明载体**（21.1%），旧口径作废；wave1-记录 W1-C42 注记同步。

#### W2-C-43

- **修复**：B-16 从「无载体」移入有内核载体——FV-0.2 27-goto 分配全枚举 Kani harness 3 verified（kani-run.log:1273）已机器穷尽 E2102/E2103 计数语义 + E2101 抑制规则（theorems-v1.md:366 工具栏登记），与已采信的 FV-0.1 route Verus（B-14/B-15/C-04）同构；残余=镜像↔实现对账单测，注明在案。40/12 口径即由此定。

#### W2-C-44

- **修复**：Rocq T05/T06 补零写者前提（T05 soundness 加 `0 < set_card` 假设、T06 completeness 结论加同取域）——CONFLICTS #2/#2b 机器反例：零写者 store 实装不报 E2311 而字面违例谓词 card=0 成真，字面陈述被证伪；与 Kani 侧 cnt≥1 前提同口径（RUNLOG §3），建模说明登记对账关系；v0.2 议程 A-07 修订落地后可撤前提。

#### W2-C-45

- **修复**：AGENT.md 硬纪律5、20-质量保证体系.md L2、组件建设状态.md:39 三处「step1 含 K5」表述改「K5 只在未合流的 phase2-redteam-fixes 分支（ci/k5-path-lint.py + scorechain-manifest.txt），主线 @438fa6d step1 仅 fmt、全树零 K5 工件；合流前不得写作主线门组成」。

#### W2-C-46

- **修复**：组件建设状态.md:9「红队修复批 phase2-redteam-fixes 随后并入」→「待合流/待推送」（merge-base rc=1、ls-remote 无该分支、origin/phase2 仍 438fa6d 实证），实际完成 merge 与 origin 更新后再改表述。

#### W2-C-47

- **修复**：SYNTAX.md 补红队批语义收紧登记（E2209 construct_conflict / E2202 恰一端口+内建端口去重 / CEL // 注释与 has 跨越 / route default:exit 守卫 / E2311 文案分叉），链 ADR-011 裁决6 与 W2 commit；正本回填随 v0.2 议程。

#### W2-C-48

- **修复**：ADR-011 头行「53 条 real-defect 裁定」→「54 条」（53 首轮 + 续核增补 W1-C55），与背景段/commit 49ed877 同步；后续基数变更须同查状态行/背景段/提交信息。

#### W2-C-49

- **修复**：af 根 README 布局节「docs/adr/ # ADR-001..010」→「ADR-001..011（011=红队修复批 W1）」，与 docs/adr/README.md 索引及实际 11 份裁决文件一致。

#### W2-C-50

- **修复**：af 根 README af-order 命令面补全枚举 `swev|report|graph|stub` + Auto 缺省规则（三件套在→Swev，缺→Stub 冒烟档），与 exec.rs UnitChoice 实况及 ADR-011 裁决2 对齐。

#### W2-C-51

- **修复**：docs/VERSIONS.md 与 SYNTAX.md 的 farm_anomalies_test 计数 13→14（W1-C28 新增 iv48_同型双端口用例；样本仍 39/39），纯计数漂移校正。

#### W2-C-52

- **修复**：判分目录字节码禁写禁读——三判分/渲染子进程统一 `-B` + PYTHONDONTWRITEBYTECODE（禁写）；check_fingerprints 增 __pycache__/*.pyc 在场性门（禁读兜底：Python 对在场有效 pyc 优先于源文件加载，-B 只禁写不禁读）；存量 pyc 已清（两工作树）。R5 判据基准 render.py 不再可被未锚影子字节码翻转。回归：pkg_reportkit judge_fingerprint_gate_rejects_planted_pyc_shadow。

#### W2-C-53

- **修复**：MES event_id 并入运行实例判别量（订单目录规范路径 sha256 前 16hex，`{stable_id}:{kind}:{seq}:{instance}`）——同 order_id 跨 --state 根不再产生逐字节相同 event_id（CH 按 event_id 去重的差量送批互吞且零告警）；同根重放路径串不变、幂等不破。回归：cli same_order_id_across_state_roots_gets_distinct_event_ids 集成测试。

#### W2-C-54

- **修复**：--max-turns/--spend-cap-cents 接入 graph/report 两臂——graph：default_node_turns=旗标 turns、order_spend_cap_cents=旗标 cents 作订单级总闸（plan 无 cost_cap 时顶上，N 节点收敛到同一总额；plan 有时以 plan 为准）；report：spec.max_turns/spend_cap_cents=旗标（环级总帽，RingBudgets 取 min(spec,plan)）。订单回显自此为真。回归：exec_contract graph_and_report_specs_map_budget_flags。

#### W2-C-55

- **修复**：plan.json 摘要三重钉死——门面 submit 计算（pin_plan_digest，graph/report 档）→ 凭证身份面留档（VoucherRecord.plan_sha256，重放对账不符即 OR2003 同码）→ 单元执行前复核（exec::verify_plan_digest 先于 planbind）。同 graph_version/registry_digest 换 plan.json 放宽预算的路径封死。回归：graph_unit plan_digest_mismatch_rejects_before_binding + voucher plan_digest_is_pinned_and_replay_checked。

#### W2-C-56

- **修复**：af-engine 二进制信任锚——旁车 `<bin>.sha256`（sha256 + 来源 workspace）；locate 四支：验过即用/首用采纳建档/锚不符 `cargo clean -p af-engine` 后从源码重建（硬链接陷阱：debug 与 deps 副本同 inode，只删 bin 会被缓存重新链回污染件，必须 clean -p）/在场不可读拒启动；落锚后终核不过 EX1007。对自由 --target-dir 同锚。回归：engine engine_binary_tamper_is_detected_and_rebuilt（篡改→重建恢复真身+验过即用不再重建）。

#### W2-C-57

- **修复**：技术债登记 D-2 销项语「F1-F5c 八单在档」→「共 15 个订单目录（8 成功+7 如实失败）」；「八 op 生命周期」与订单笔数两个计数维度分别保留（八笔系 runbook:108 的 F1-F4a3 时点数）。

#### W2-C-58

- **修复**：G4-研究报告包设计-v1:358/:361 两处「19 项预期红名单」→「22 项」（姊妹方案已 W1-C67 勘误 19→21→22；行号 :95-121 漂移注明以方案 §1.3 当前版为准），交叉引用闭合。
