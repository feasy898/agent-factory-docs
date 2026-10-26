# 红队第 1 波（W1）全程记录

- 日期：2026-10-26（候选投喂 → 裁判裁定 → 修复收口；14:01 续跑批完成 C-33 完整化与 C-55 补处置；23:05-23:13 复核批完成 C-39 钉子补齐 / C-05 索引行收口 / C-59②判据门测试化 / C-64 聚合排除冒烟档及 7 条在位核验；23:34 全域合龙批终跑九门全绿）；2026-10-27 凌晨（五域分支 --no-ff 合入 phase2-redteam-fixes，合龙九门两处红项修复后终跑九门全绿，证据 5a73ba4）
- 波次对象：第二阶段交付全景（af 仓 @438fa6d + 工作区文书）——承诺面/证据链/语义面/执行面/判分链/运维面六向审计
- 修复执行：红队修复员（glm5.3），工作树 /home/pan-ding/workspace/af-wt-redteam（分支 phase2-redteam-fixes，基于 origin/phase2 @438fa6d；2026-10-27 合入五域分支 phase2-rt-af-execline / phase2-rt-af-order / phase2-rt-af-dsl / phase2-rt-misc / phase2-rt-af-compiler）
- 本记录路径（返回路径确认）：/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/红队收口/wave1-记录.md
- 硬线核验：ci/run.sh 九门全绿——修复员亲跑均 exit 0（step1-8 PASS + step9 ADVISORY-PASS；9b 断言 32 verified/0 failures/32 total）：①08:25 修复批终跑（证据入档 71a09d6）②13:28 复核跑（777672b）③C-33 完整化补丁后终跑（53c2504）④23:34 全域合龙批终跑——W1 修复与全域修复员 W3 域修复（af-dsl/af-compiler）同树合验，step8 中立性门 12 判据全过（证据入档 2d81577）⑤2026-10-27 02:04 五域分支合入后终跑——合龙九门首跑两处红项（clippy useless_format、step3 lifecycle 并发竞态）修复后 exit 0（证据入档 5a73ba4）；step1 含 K5 判分链路径 lint PASS、--self-test 中文语境对抗自检 PASS
- 本记录口径：裁定分布按裁判最终裁定清单计；席/候选明细以裁定书所引 sources 为准（可机算面），未下发编号如实注记不臆测
- **漏检根因存档**：逐条「根因/本应拦在/改进」分析=后台产物另档（whys artifact，**按波次覆盖**、不保证跨波留存）——本记录不内联其内容；波次收官如需留存须随波次另档拷贝，勿依赖覆盖前的后台产物

## 一、12 席清单

| # | 席（source 前缀） | 焦点 | 裁定 sources 引用（编号/条数） |
|---|---|---|---|
| 1 | `plan` | 计划/承诺对照席（总计划 §0/§2/§6 × 交付实况） | 5 条：plan-01、plan-02、plan-03、plan-04、plan-05 |
| 2 | `evidence` | 证据指针核验席（门终裁/变更日志哈希与数字 × git/实盘复算） | 4 条：evidence-01、evidence-02、evidence-03、evidence-05 |
| 3 | `a1chain` | A1 验收链对账席（总账/台账/交付文四方一致性） | 4 条：a1chain-01、a1chain-02、a1chain-04、a1chain-05 |
| 4 | `cross` | 跨文书一致性席（数字/口径跨六文书传播链） | 7 条：cross-01、cross-02、cross-03、cross-04、cross-05、cross-07、cross-08 |
| 5 | `docs` | 状态/活文档席（机器清单/组件状态/总纲/AGENT/质检体系） | 10 条：docs-01、docs-02、docs-03、docs-04、docs-05、docs-06、docs-06b、docs-07、docs-08、docs-09 |
| 6 | `dsl` | af-dsl 语义面席（E 码判定面/词法闸/route/构造组合） | 5 条：dsl-01、dsl-02、dsl-03、dsl-04、dsl-05 |
| 7 | `compiler` | af-compiler 席（bind 去重/is_final/镜像漂移/偏差表） | 4 条：compiler-01、compiler-02、compiler-03、compiler-04 |
| 8 | `execline` | af-execline 执行面席（declare 契约/预算/装订/MES/记录契约/路径安全） | 9 条：execline-01、execline-02、execline-03、execline-04、execline-05、execline-06、execline-07、execline-08、execline-09 |
| 9 | `order` | af-order 门面席（凭证身份面/幂等变体） | 1 条：order-02 |
| 10 | `fv` | 形式验证席（proofs 覆盖率/CI step9 判定强度） | 2 条：fv-01、fv-03 |
| 11 | `adv` | 对抗/可作弊面席（判分链输入钉死/中立性正则/stub 判别/event_id 身份） | 5 条：adv-01、adv-02、adv-03、adv-05、adv-06 |
| 12 | `ops` | 运维/退役面席（TTL 机制/runbook 回滚与判据/巡检口径） | 4 条：ops-01、ops-02、ops-03、ops-04 |

十二席产出候选合计 **69 条**。其中 54 条 real-defect 裁定的 sources 合计 **60 个编号引用**（5 项多源并案：W1-C-06 引 3 源 evidence-01+a1chain-01+cross-02；W1-C-08/C-10/C-14/C-55 各引 2 源——54 候选+6 个并案增量=60）；其余 **15 条非 real 候选**（11 not-defect + 4 handled）的个体编号未随修复材料下发——按编号连续性可辨 5 个未入任何 real 裁定的编号（evidence-04、cross-06、order-01、fv-02、adv-04——cross-04/docs-07 已由 W1-C55 引用），余 10 条以裁判侧裁定正本为准，本记录不臆测。

## 二、候选与裁定分布

- 候选总量：**69 条**（十二席产出）
- 裁定分布（按实际 verdict 计）：**real-defect = 54 / overturn = 0 / not-defect = 11 / handled = 4**（54+0+11+4=69 闭合）
- real 54 的构成：首轮清单 53 条 + 续核增补 W1-C55（G5 门终裁复核时已指出但按「措辞/时点值级」放行未改，裁判终裁为 real-defect 并出 fixHint——首轮 53 清单漏登该条，据裁判最终裁定清单更正）
- 多席并案：5 项裁定为多源吸收（W1-C-06 引 3 源；W1-C-08/C-10/C-14/C-55 各引 2 源，见 §一；并案语义=同一缺陷多席独立命中，修复按并案后缺陷计一次）
- 修复结果：**54/54 全部修复**（fixed=true，逐条见 §四；其中 W1-C55 由修复员续跑批处置、W1-C33 经续跑批完整化），代码缺陷走 TDD（先红后绿）+ 九门全绿硬线，文书缺陷原地勘误并留勘误注记

## 三、修复载体

| 类别 | 位置 |
|---|---|
| 代码/仓内文档（af 仓） | 分支 phase2-redteam-fixes（工作树 ~/workspace/af-wt-redteam），W1 批 **14 个 commit**（与 W2 波 commit 在史上交错，本表只列 W1 批）：23d9d7a（af-dsl 六项+golden 7 份再生）/ ae98366（af-compiler/af-harness 两项）/ ecb5d99（af-execline+af-order 十四项）/ 71b7cef（ci 三项）/ a37453b（ADR+proofs+packages README 多项）/ 2194763（RESULT-G2b 偏差表 #16/#17）/ 71a09d6（九门全绿证据入档）/ 777672b（九门全绿复核证据刷新——修复员 13:28 亲跑 exit 0）/ 53c2504（C-33 完整化+终跑九门证据）/ 49ed877（ADR-011 裁定基数 53→54 更正）/ 7d9e7ae（ADR-011 裁决7 补记 C-33 完整化）/ 5ced300（复核批：C-39 归属钉子补齐+7 条核验）/ e858a3f（复核批：C-05 ADR 索引 005 行取代关系）/ 62287ef（复核批：C-59②判据门测试化+C-64 产线聚合排除冒烟档） |
| 域分支与合龙（af 仓） | 域分支 phase2-rt-af-{execline,order,dsl,misc,compiler} 于 2026-10-27 --no-ff 合入 phase2-redteam-fixes：af-dsl 域 61fa507（C-27 memory 面钉子）+24b2abf（C-28 final_artifact_port EX4006 fail-loud）、af-compiler 域 cb18dca（C-37 顺序对抗钉）随合并提交 d9cf17d/475329f 进入本分支；合龙九门两处红项修复（clippy useless_format + locate 并发竞态）与终跑证据提交 **5a73ba4** |
| 工作区文书（原地勘误） | 计划/{00-总纲,20-质量保证体系,30-遗产处置,技术债登记,变更日志}.md；AGENT.md；计划/研究组/{A1-稳定性验收-终验,G4-门终裁,G5-门终裁,G5-健康度首报,G4-任务中立性机器检查方案,G2G3-放行裁决,G3-全链闸门-L1L4-v2,G4-软件工程包设计,旧bench退役归档-runbook}-*.md；计划/研究组/形式化/{proofs-wave1/确定性组-构造语义-Verus/C组确定性-对应表,FV-1-第一波-裁决-20261025}.md；计划/研究组/红队收口/wave1-记录.md；状态/{机器清单,组件建设状态}.md；tools/mes-ttl-decision-point.py + systemd --user mes-ttl-decision-point.{service,timer}（C-14） |
| 漏检根因（whys） | 后台产物另档（whys artifact，按波次覆盖）——本记录不内联；详见文首存档注记 |
| 硬线核验 | `bash ci/run.sh`（CARGO_TARGET_DIR=~/afbuild-phase2rt）亲跑均 exit 0：step1（fmt+K5 判分链 lint）/step2 clippy/step3 test/step4 cue/step5 scrub/step6 cosign/step7 deny/step8 neutrality 全 PASS + step9 FV ADVISORY-PASS（9b 断言 32 verified/0 failures/32 total）——ci/out/SUMMARY.txt 随 71a09d6/777672b/53c2504/2d81577/5a73ba4 入档 |

## 四、修复清单（54/54，逐条）

本清单为 2026-10-27 域分支合龙批下发的最终版：id / fixed / commits 与逐条 how 逐字登记；commits 列=该条修复的最终载体（前波载体如 23d9d7a/ae98366/ecb5d99 等在 how 内文如实注明，本轮合入本分支的域提交 61fa507/24b2abf/cb18dca 与合龙证据 2d81577 亦按实际归并计入）；commits 为空=工作区文书原地勘误，无仓内 commit。

汇总表（id / fixed / commits）：

| id | fixed | commits |
|---|---|---|
| W1-C-01 | ✅ | a37453b, 62287ef |
| W1-C-02 | ✅ | a37453b |
| W1-C-03 | ✅ | —（前波 71b7cef 承载，本轮零改动） |
| W1-C-04 | ✅ | a37453b |
| W1-C-05 | ✅ | a37453b, e858a3f |
| W1-C-06 | ✅ | —（工作区原地勘误） |
| W1-C-07 | ✅ | —（工作区原地勘误） |
| W1-C-08 | ✅ | —（工作区原地勘误） |
| W1-C-10 | ✅ | ecb5d99 |
| W1-C-12 | ✅ | —（工作区原地勘误） |
| W1-C-13 | ✅ | —（工作区原地勘误） |
| W1-C-14 | ✅ | —（工作区原地勘误+工具落地） |
| W1-C-15 | ✅ | —（工作区原地勘误） |
| W1-C-16 | ✅ | —（工作区原地勘误） |
| W1-C-22 | ✅ | —（前波 23d9d7a 承载，本轮零改动） |
| W1-C-23 | ✅ | —（前波 23d9d7a 承载，本轮零改动） |
| W1-C-24 | ✅ | —（前波 23d9d7a 承载，本轮零改动） |
| W1-C-25 | ✅ | —（前波 23d9d7a 承载，本轮零改动） |
| W1-C-26 | ✅ | —（前波 23d9d7a 承载，本轮零改动） |
| W1-C-27 | ✅ | 61fa507 |
| W1-C-28 | ✅ | 24b2abf |
| W1-C-29 | ✅ | ae98366, 2d81577 |
| W1-C-30 | ✅ | 2194763 |
| W1-C-31 | ✅ | ecb5d99 |
| W1-C-32 | ✅ | ecb5d99, fa0ec74, 2d81577 |
| W1-C-33 | ✅ | ecb5d99, 53c2504, 2d81577 |
| W1-C-34 | ✅ | ecb5d99, ff68d80, 2d81577 |
| W1-C-35 | ✅ | ecb5d99 |
| W1-C-36 | ✅ | ecb5d99, 2d81577 |
| W1-C-37 | ✅ | ecb5d99, cb18dca |
| W1-C-38 | ✅ | —（前波 ecb5d99 承载，本轮零改动） |
| W1-C-39 | ✅ | ecb5d99, 5ced300, cb18dca |
| W1-C-41 | ✅ | ecb5d99 |
| W1-C-42 | ✅ | —（工作区原地勘误；af 仓披露面随 a37453b） |
| W1-C-44 | ✅ | 71b7cef |
| W1-C-49 | ✅ | —（工作区原地勘误） |
| W1-C-50 | ✅ | —（工作区原地勘误） |
| W1-C-51 | ✅ | —（工作区原地勘误） |
| W1-C-52 | ✅ | —（工作区原地勘误） |
| W1-C-53 | ✅ | —（工作区原地勘误） |
| W1-C-54 | ✅ | —（工作区原地勘误；af/packages README 侧随 a37453b） |
| W1-C-55 | ✅ | —（工作区原地勘误） |
| W1-C-56 | ✅ | —（工作区原地勘误） |
| W1-C-57 | ✅ | —（工作区原地勘误） |
| W1-C-58 | ✅ | —（工作区原地勘误） |
| W1-C-59 | ✅ | ecb5d99, 62287ef |
| W1-C-60 | ✅ | —（前波 71b7cef 承载，本轮零改动） |
| W1-C-61 | ✅ | ecb5d99 |
| W1-C-63 | ✅ | fa0ec74, ecb5d99 |
| W1-C-64 | ✅ | ecb5d99, 62287ef |
| W1-C-65 | ✅ | —（工作区原地勘误；af 仓侧随 a37453b） |
| W1-C-66 | ✅ | —（工作区原地勘误） |
| W1-C-67 | ✅ | —（工作区原地勘误） |
| W1-C-69 | ✅ | —（工作区原地勘误；af 仓侧随 a37453b） |

逐条修复方式（how）：

#### W1-C-01

- **修复**：fixHint 的「有权者写入ADR+同步总计划」路线已落地，无需补适配器。亲读 docs/adr/011-redteam-w1-fixes.md:19-27：裁决1「mcode headless 推迟出第二阶段，总计划 §0/§6 三适配器表述由本 ADR 取代」、裁决2「tb 以库形态吸收，不设门面路由」；亲读总计划 .zcode/plans/plan-session_483404be41dbd275e1ea2a270eeb0600.md:16-17（mcode 行删除线+ADR-011 裁决1 引用、tb 行库形态+裁决2 引用）与 :94（§6 改「实交 swev/graph/report 三单元 + tb 库形态，mcode headless 推迟——ADR-011 裁决 1/2」）；ADR-011 在 docs/adr/README.md 索引在册。亲跑 grep：crates/ 无 headless 命中，af-order/src/exec.rs UnitChoice=swev|report|graph|stub 与裁决2 口径一致。载体 a37453b（ADR-011 创建+索引补登）、62287ef（裁决7 补记）。
- **载体**：`a37453b`, `62287ef`

#### W1-C-02

- **修复**：按 fixHint 首选路线（明确退出+回写，非交付转换器）收口。前批同域修复已随本分支基线（phase2-redteam-fixes）在位，本轮逐面亲验+补齐最后一处残留。①裁决面：ADR-011 裁决 3 正式登记「转换器不在第二阶段交付面、推迟至扩量期」（docs/adr/011-redteam-w1-fixes.md:28-31，提交 a37453b，亲跑 git merge-base --is-ancestor a37453b HEAD 通过）；ADR-005 裁决 3 接入协议冻结头注在位（005-multi-agent-bench.md:3-7）。②回写面（逐一亲读在位）：总计划(.zcode/plans/plan-session_483404be41dbd275e1ea2a270eeb0600.md) §2:38 裁决5 划线+「已被取代（W1-C02/C-05/ADR-011 裁决4/5）」注、§6:94 交付物清单「~~bench→WorkOrder 转换器、MARBLE 改造件~~（推迟至扩量期/随 MARBLE 退出作废）」；00-总纲.md:21 收官状态「转换器明确处置：推迟至第三阶段扩量期」补录。③收口清单：G5-门终裁-20261025.md:29 §四「~~bench→WorkOrder 转换器去留~~（✅ 2026-10-26 红队 W1-C02 补录…）」在位。④本轮补齐的同面残留：总计划 §3:64 W2 分工行仍无处置注列出「MARBLE 工件投递改造 + bench→WorkOrder 转换器」为在飞工作项——按同文件既有注记风格补划线+处置注（仅 C-02/C-05 两项，同行 mcode 项归 W1-C-01 他域未动），并在 计划/变更日志.md 追加 2026-10-27 条登记全链（历史条 :161/:174 不动）。⑤裁判同名命令亲跑（本修复专支 af-wt-rt-af-order/phase2-rt-af-order，HEAD=2d81577）：git grep -il taskbench HEAD 命中 005/011/README 三件（裁判裁定时点 438fa6d 仅 005/README 两件；438fa6d 经 merge-base 验为 HEAD 祖先，即裁判基线严格落后于修复专支）。零代码改动=处置本义（W2 裁决既定「非首单前提、后续扩量」），纯文书修复故未跑测试/九门（按指令归汇总员）；af 仓本轮零新提交=前批修复完备，工作区文书非 git 托管无提交载体。commits 列 a37453b=承载 ADR-011 裁决 3 处置登记的 af 仓提交。
- **载体**：`a37453b`

#### W1-C-03

- **修复**：非重修，系复核确认：裁判对着旧基线 438fa6d 裁定；本分支（worktree af-wt-rt-af-dsl，基于 phase2-redteam-fixes）上前波 71b7cef 已落 ci/k5-path-lint.py + ci/scorechain-manifest.txt（判分链 4 件 sha256 冻结锚：judge.rs + reportkit citation/rubric/render，obs-checker/obs.rs 载体经 find 证实不在本仓=0 命中，登记表头注明口径映射），并接入 ci/run.sh:82-84 step1 硬门。本波亲跑：python3 ci/k5-path-lint.py → PASS(4 件逐位对锚) exit 0；负探针（临时仓副本改锚为零）→ exit 1 点名漂移/缺席。
- **载体**：—（前波 71b7cef 承载，本轮零改动）

#### W1-C-04

- **修复**：五条裁定均为对『W1 修复波之前基线』的判定（其引证行号只与修复前状态吻合：graph_unit.rs:472-483 filter_map、ci/run.sh:247-259 无计数断言、report_unit.rs 双锚、RESULT-G2b 15 条、『基线无取消该枚举的ADR』）——专用工作树 /home/pan-ding/workspace/af-wt-rt-misc（分支 phase2-rt-misc，自 phase2-redteam-fixes 落位，先 merge 同步无分歧，HEAD=2d81577）已含前波全部修复。本条取 fixHint 第二路径『由有权者正式修订命令面契约』，已落地：ADR-002:28-32 勘误（2026-10-26，红队 W1-C04）明文修订本文与总计划 §0 的四命令枚举，ADR-011 裁决5（docs/adr/011-redteam-w1-fixes.md:36-40）正式登记『门面命令面=submit/list/show；submit 一命令走通全生命周期（driver 内部驱动 release/start/complete/close），approve/close 不设门面子命令，approve_decision op 归编排侧』。一致性亲核：README.md:30（submit 单一入口+unit 枚举勘误）、cli.rs:1『三个子命令（submit/list/show）』、cli.rs:140 用法错误文案同口径——树内无任何未修订的四命令承诺残留（grep submit/approve/list/close 仅命中修订条文自身）。修复前提『driver 内部调用不能冒充门面子命令』成立且 ADR 如实照此表述，未以内部调用冒充。亲跑回归：cargo test -p af-order 全绿（lib 17✓/cli 8✓/exec_contract 12✓/graph_route 3✓/unit_route 5✓，CARGO_TARGET_DIR=~/afbuild-phase2rt-misc）。基线分支已含修复（a37453b），本轮核验零改动、无新 commit。
- **载体**：`a37453b`

#### W1-C-05

- **修复**：fixHint 三要素逐项亲验在位。①ADR-005 被取代头注：docs/adr/005-multi-agent-bench.md:3-7 状态行「已裁决（2026-10-24）；部分被 ADR-011 取代（2026-10-26）：裁决 1 主选 MARBLE 作废（MARBLE 退出第二阶段，多 agent 走 AFB 原生图）；裁决 3 bench→WorkOrder 转换协议冻结；裁决 2 转入冻结；正文保留裁决时点原貌」。②历史正文原貌保留：亲跑 git diff 438fa6d HEAD -- docs/adr/005-multi-agent-bench.md，差异仅状态行（+4 行头注），依据/裁决正文零改动。③ADR-011/总纲同步：ADR-011 裁决 4（011-redteam-w1-fixes.md:32-35）登记 MARBLE 退出第二阶段、多 agent 走 AFB 原生图（sweng sop_full/reportkit paper_report）；ADR README 索引 005 行取代关系在位（README.md:12「已裁决 2026-10-24；部分取代 2026-10-26」，提交 e858a3f）；00-总纲.md:12 同步（~~五 crate~~→四 crate 勘误 + ~~MARBLE 主选~~已取代注）。④裁判同名命令亲跑（HEAD=2d81577）：git log --oneline --follow -- docs/adr/005-multi-agent-bench.md 返回 a050378（创建）→a37453b（修订）——承诺的「随下次 af 仓提交批入 docs/adr/」已兑现；git show HEAD:docs/adr/005-multi-agent-bench.md 状态行为取代头注（裁判所见 438fa6d 版仍是 MARBLE 原文，因 438fa6d 为修复专支祖先、先于 a37453b）。变更日志 :124 待办条由 :174 登记闭合。纯文书/ADR 面零代码改动，未跑测试/九门（按指令归汇总员）；af 仓本轮零新提交=前批修复完备。commits 列承载修复的两笔提交（均为 HEAD 祖先，亲跑 merge-base 验证）。
- **载体**：`a37453b`, `e858a3f`

#### W1-C-06

- **修复**：前批已把 A1-稳定性验收-终验-20261025.md 表头改为「8 笔成功+7 笔如实失败=15 个订单目录全量」并补 F4a/F4a2/F4a3 行与注记④（该文件:5/:12/:36）。本次 TDD 复核：亲跑逐单解析 af-state/orders 15 个 records.jsonl 末行——verdict=true 共 8（F1/F2/F3a/F3b/F4a/F4a2/F4D/F5c）、失败 7（F3a2 verdict=false + F4B/F4B2/F4C/F5 records 空 + F5b completed/false），与文书完全闭合，总账可机器复算。
- **载体**：—（工作区原地勘误）

#### W1-C-07

- **修复**：前批已改 G4-门终裁-20261025.md:4 为 a837c89 并注明 836fcfdc 系 dwfrun 号误植。亲验：git -C af cat-file -t 836fcfdc → rc=128 fatal；cat-file -t a837c89 → commit，show -s 得「feat(g4收尾): sop_full/no_qa/minimal 三图物化…八门全绿」。
- **载体**：—（工作区原地勘误）

#### W1-C-08

- **修复**：前批已改 G5-门终裁-20261025.md:11 为「98 行」附勘误；亲跑 git show 438fa6d:README.md | wc -l = 98。变更日志:160 11.9行系历史誊抄条（按运行禁写规则保留），勘误由同文件:166「README 119 行虚记…修复员 53/53」条载明，活文档无残留（grep 全工作区核过）。
- **载体**：—（工作区原地勘误）

#### W1-C-10

- **修复**：代码面：graph 结果行已改走 af.plan.record.v1 并落 evidence.run_dir（亲读 crates/af-execline/src/graph_unit.rs:382-395 run_dir=Some(attempt_dir)），新单 L1→L2 父子边闭合。亲跑 cargo test -p af-execline --test graph_unit（28 pass，含 :474-478 断言 evidence.run_dir 指向实际 run 目录）与 --test trace_tree_verify（19 pass，工具 fixture 即 records 行带 evidence.run_dir + runs/<name>/harness.db 布局）。文书面亲读核验：G5-门终裁-20261025.md:13 勘误「F4D 实为 exit=1/findings 2——登记开放项…存量 F4D 的 trace 仍为人工亲读」；A1 终验 MES+trace 判据行同口径「存量 F4D 不得追认为工具核验通过」。本轮未对 F4D 重跑工具（原二进制已不存在，fixHint 亦要求不追认），仅核验勘误在位。
- **载体**：`ecb5d99`

#### W1-C-12

- **修复**：总账死因已按 ledger 错误码独立映射（fixHint「保留」项核验在位）：亲读 计划/研究组/A1-稳定性验收-终验-20261025.md 总账行——F4B/F4B2 行「死因：EX4006 declare 契约面（红队 W1-C12 勘误——原『图执行器缺失』系从未发射的主单死因错位）」，F4C 行「死于 EX4007 预算熔断：token_cap 累计 514,425 ≥ 帽 400,000（W1-C12 勘误）」，两行均直引 ledger seq6 错误码原文。该文件在工作区文书面（/home/pan-ding/workspace/agent黑灯工厂 非本仓 git 管辖），无仓内 commit；本轮零改动，维持勘误现状。
- **载体**：—（工作区原地勘误）

#### W1-C-13

- **修复**：前批已改 A1:28 为「命令史审计覆盖 10-25 起各单——F1/F2 为 day-1 单，执行长转录已不在盘、不可重验，其入口依据为 MES station_id 账本证据」并带 W1-C13 勘误标记；不再宣称对 F1/F2 已执行命令史审计。MES 侧单一入口账本口径保留。
- **载体**：—（工作区原地勘误）

#### W1-C-14

- **修复**：fixer 可做部分已落地并亲验：①总数勘误——亲读 计划/30-遗产处置.md:22，登记改「合计 3,042,489 行（红队 W1-C14 勘误 2026-10-26：原 3,043,489 系手工加总错 1,000，按 mes-ttl-sweep.log 逐表亲算更正）」；②真实决策定时器与证据输入——亲跑 `systemctl --user list-timers --all` 实证 mes-ttl-decision-point.timer NEXT=2026-10-29 09:00:00（另 mes-ttl-sweep.timer 每日 04:30 照旧），tools/mes-ttl-decision-point.py 在盘（只读取证：5221 监听/pid/五表在场性/观测止点）。残余如实报告：fixHint 的「只读拉起 5221 导出归档 vs 正式放弃整目录归档」二选一是生产数据处置权决断，登记面明文「待编排者裁决（2026-10-28 观察期满前）」「仍待运营者裁决项不变」——不属代码修复员权限，本轮未执行、未代裁；30-遗产处置.md 与 tools/ 均为工作区文件，无仓内 commit。
- **载体**：—（工作区原地勘误+工具落地）

#### W1-C-15

- **修复**：前批已把 runbook §四改为「先还原 工具状态备份/factory-keepalive.py.pre-bench-retire-20261026 再裸 nohup」并记录原一行回滚失效（该备份亲核在位；现行 tools/factory-keepalive.py:1324 TARGETS 仅四对象、备份:1235 为九对象）。本次按 fixHint 补硬回滚演练判据：须 grep 旧 TARGETS 九对象实际恢复且日志出现旧对象拉活行，只看 keepalive 进程起来不算回滚成功。
- **载体**：—（工作区原地勘误）

#### W1-C-16

- **修复**：fixHint「保留修订+白名单过渡限期退出」核验在位：亲读 计划/研究组/旧bench退役归档-runbook.md:113-124——判据①已改按 SQL 语句扫描 `grep -rn 'INSERT INTO af_mes' tools/*.py`（注明原 ch_insert 按函数名对 keepalive mes_event() 结构性失明）、判据③改「业务线零新行+记账面已知白名单枚举」；亲读 计划/技术债登记.md D-45：keepalive 直 INSERT 立案为同族旁路、处置=「通道改造待观察期满 keepalive 退场批」（即 fixHint 的白名单过渡+限期退出）。tools/factory-keepalive.py 通道改造属工作区 ops 面且进程仍在观察期（非 af-execline 文件），本轮不改；工作区文件无仓内 commit。
- **载体**：—（工作区原地勘误）

#### W1-C-22

- **修复**：非重修，系复核确认：前波 23d9d7a 已改 refs.rs check_meta——判定面接 builtin_ports（与 port_exists/emit_type 同源端口模型，refs.rs:77-135），后经红队 W3-C19 演进为「无 emits 的构造/判定节点不得作终态发射者」（refs.rs:102-123，消息如实点名内建端口不构成终态工件，原「无任何 emits 端口」误导性矛盾消除；该裁决登记于 ADR-012）。本波亲跑具名测试：builtin_only_terminal_is_rejected_e2202、builtin_done_port_still_feeds_edges、explicit_builtin_done/passed_declaration_is_not_double_counted、dual_same_type_emit_ports_ambiguate_output、two_distinct_same_type_ports_still_reject_as_e2202 全绿；af-dsl 全套 0 failed。
- **载体**：—（前波 23d9d7a 承载，本轮零改动）

#### W1-C-23

- **修复**：非重修，系复核确认：前波 23d9d7a 已改 cel.rs lex_scan 与 cel-parser 文法同口径跳过 // 行注释（字符串字面量照旧跳过；块注释不跳——文法不收，防深括号绕闸）。本波亲跑具名测试：comments_are_skipped_by_lex_scan、has_macro_across_line_comment_is_still_rejected（注释文本内 has( 不误伤 + 注释不隔断真宏闸）全绿。
- **载体**：—（前波 23d9d7a 承载，本轮零改动）

#### W1-C-24

- **修复**：非重修，系复核确认：前波 23d9d7a 已改 route.rs——default==exit 时 default_guard（¬(when₁∨…∨whenₙ)）并入 exit_guard（:195-204），规则型 exit 保持文档序析取。本波亲跑具名测试：default_exit_produces_negated_disjunction_exit_guard（exit_guard=Some("!((input.x))")）、default_exit_with_exit_rules_joins_disjunction 全绿；route_test 全套 14 例含 a×b 布尔网格析取永真性质测试 0 failed。
- **载体**：—（前波 23d9d7a 承载，本轮零改动）

#### W1-C-25

- **修复**：非重修，系复核确认：前波 23d9d7a 按 fixHint 的 fail-closed 路线落 E2209 ConstructConflict（error.rs:102-107/190 + validate/mod.rs:141）拒绝 loop+map 同节点并存。本波亲跑 construct_conflict_test：loop_plus_map_on_same_node_is_e2209、loop_alone_and_map_alone_still_pass（fixHint 要求的 loop-only/map-only 正例对照）全绿。
- **载体**：—（前波 23d9d7a 承载，本轮零改动）

#### W1-C-26

- **修复**：非重修，系复核确认：前波 23d9d7a 已分叉 E2311 文案（inv2.rs:41-59）——paths.len()>1 → 「写者不唯一」；恰一写者但不匹配 → 「写者与声明不符」。本波亲跑具名测试：sole_writer_mismatch_message_says_mismatch_not_multi（断言含「写者与声明不符」且不含「不唯一」）、multi_writer_message_still_says_not_sole 全绿。
- **载体**：—（前波 23d9d7a 承载，本轮零改动）

#### W1-C-27

- **修复**：前波 ae98366 已按解析结果去重（bind.rs:199-205 dedup_resolved 应用于 tools:223 与 memory:233 两面），但钉子测试只盖 tools 面（fixHint 要求「tools 与 memory 均覆盖」）。本波补 memory 面钉子测试 duplicate_memory_refs_dedup_after_resolution（uses.memory 带/不带版本混写 pkg.crewkit.mem.longterm@1 + pkg.crewkit.mem.longterm → 解析后恰一条且版本化引用）并亲跑绿；af-compiler 全套 12 面 0 failed；cargo fmt --check 归零。commit 61fa507。
- **载体**：`61fa507`

#### W1-C-28

- **修复**：编译面/DSL 面前波已收（23d9d7a E2202 恰一端口匹配 + W2-C26 lower is_final 经 derived_emit_type 同规则推导；本波亲跑 iv48_dual_same_type_output_ports_now_e2202、from_body_port_is_final_requires_derived_type_match 绿），但 fixHint 第二半「final_artifact_port 不得靠 find 吞掉歧义」在前波未落：af-execline graph_unit.rs:1922 仍 .find(|a| a.is_final) 静默取首个。本波 TDD 收口：先在 tests/graph_corpus_adv.rs 加对抗语料 type/dual-final-artifact-ports（output_from 改指 planner+原口置 is_final+追加同型 plan_shadow 口+declare 双键过 envelope 交接门直抵收尾相）→ 守卫前实跑裁定 OK(完成)静默通过（洞，RED）；随后 final_artifact_port 改 collect is_final 端口、>1 即 EX4006 点名端口列表「终态工件不可单义识别，须恰一」→ GREEN；af-execline 全套 23 面 0 failed。commit 24b2abf。
- **载体**：`24b2abf`

#### W1-C-29

- **修复**：修复已在前波落在本波基线分支上，本波源码+测试双面复核无漂移并亲跑全绿：compiler 镜像补齐长度条款（af-compiler/components.rs:392-398 `e.key_ref.len() > 128` 与非空/字符集/sk- 前缀并列，与 af-harness/spec.rs:294-295 is_ref_name 全条同界）；两侧边界钉在位——compiler 侧 bind_test.rs:589-626 registry_rejects_key_ref_over_128_boundary_same_as_harness（128 过/129 拒+错误点名 key_ref），harness 锚侧 spec.rs:366-378 key_ref_length_boundary_is_128。亲跑（CARGO_TARGET_DIR=~/afbuild-phase2rt-af-compiler）：cargo test -p af-compiler --test bind_test → 19 passed；cargo test -p af-harness --lib key_ref → 2 passed（含 128 界钉）。
- **载体**：`ae98366`, `2d81577`

#### W1-C-30

- **修复**：fixHint 两项偏差已补登于 crates/af-compiler/RESULT-G2b.md（commit 2194763，表 15→17 条）：#16『components.memory 为数组 Vec<String>（草案 §7.1 为单引用串）』注明 uses.memory 声明面为列表形（声明面理由）；#17『loop_policy/context_compaction 恒 null（草案为组件引用串）』注明 v0.1 uses 无该两键声明面、bind.rs 注释自认占位（占位理由）——与 plan.rs:186-193 实现逐字吻合（PlanComponents: model_route Option、loop_policy Option 注释『v0.1 恒 None（uses 无声明面）』、memory: Vec<String>、context_compaction Option 同注释）。摘要行 :113 登记『2026-10-26（红队修复批 W1-C30）偏差表补登 #16/#17……表 15→17 条』满足『出入全集』标准。亲核草案原文（外部文档仓 /home/pan-ding/github-docs-stage/计划/研究组/落地契约-v0.md:404-410）：components 五键确全为引用串且 memory 单值——#16/#17 所述出入属实、登记准确。plan.rs:12 模块表 node_exec 行仍简写『面对齐 §7.1』，但同表已按『见 RESULT-G2b 偏差表』惯例转指权威登记处，fixHint 未要求改 plan.rs，且该文件属并行 af-compiler 修复员域，为防合流冲突不动。无代码面改动，无新 commit。
- **载体**：`2194763`

#### W1-C-31

- **修复**：fixHint 三要素均已在位（commit ecb5d99）并亲验：①graph_unit.rs:557-570 port_contracts 用 .map 收全部 artifact_contract 端口（原 filter_map 丢弃已除，注释明记 C31 死锁机理）；②declare_tool_strict（graph_unit.rs:1395-1483）required=全部端口名、properties/示例/check_typed 仅对有类型端口（:1446-1449 注释『无类型端口=键到位即可，与 commit 相同口径』）；③commit 相（:1261-1280）产出键集恰等全部端口、check_typed 仅 typed——两相键集合一，死锁消除。fixHint 点名的回归载体『向 sop_full 人工加入 shadow 无类型端口』即现成端到端测试 strict_declare_covers_untyped_nonfinal_ports_end_to_end（tests/graph_unit.rs:1809-1868）：注入 {"name":"shadow","is_final":false} 后 drive 全图成功（verdict=true），并断言 API 面 required 含 plan+shadow、properties 仅 plan。亲跑：cargo test -p af-execline --test graph_unit strict_declare_covers_untyped_nonfinal_ports_end_to_end → ok；全套 --test graph_unit → 28 passed/0 failed（CARGO_TARGET_DIR=~/afbuild-phase2rt-misc）。基线分支已含修复，本轮零改动、无新 commit。
- **载体**：`ecb5d99`

#### W1-C-32

- **修复**：死代码期待分支已接线，本波亲验全绿：ExecContext 增 graph_version 字段（exec.rs:40-44）；driver.rs:384-392 传入 Some(self.order.graph_version())（订单快照不可变绑定——W2 后续裁定 cfg 值自指并改良，期待(旧)vs 计划(新) 换版重放即拒）；两生产调用点 graph_unit.rs:201-214 与 suite/report_unit.rs:1364-1372 均把它装进 BindExpectations；planbind.rs:103-118 三面一致性核对（compiled_from vs order 槽 vs 外部期待，漂移报「期待 ≠ 计划（WorkOrder 一次性绑定）」）。钉子测试 tests/graph_unit.rs:1865-1885 graph_version_expectation_mismatch_rejects_binding：漂移期待 Some("9.9") → EX4004/PlanBindMismatch 且 runner.launches() 空+bridge.calls() 空（零节点驱动零容器）、期待一致 Some("1.1") 走通。亲跑 cargo test -p af-execline --test graph_unit → 28 passed。
- **载体**：`ecb5d99`, `fa0ec74`, `2d81577`

#### W1-C-33

- **修复**：环级共享账本+三维熔断已落地并完整化，本波亲验全绿：RingBudgets::of（suite/report_unit.rs:578-645）白名单提取 plan.body.budget——plan 级 cents/tokens_total 带正典 id 门（非 cost_cap/token_cap 即拒）、turns 按 plan/loop:study 作用域强制、强制集外组合 fail-loud 拒收；有效帽 ring_cap_cents = min(spec.spend_cap_cents, plan cost_cap)（report_unit.rs:849-873），reader（:950-952）与每轮 writer（:1106-1108）都拿 ring_remaining 共享余额，ring_gate（:880-905 定义，:913 reader 前、:1029-1034 每轮 writer 前调用）对 cents/turns/tokens_total 三维起动前对账、耗尽拒起下一 launch，turns 单 launch 帽收敛到剩余额度（ring_max_turns :921-928）。钉子测试 tests/pkg_reportkit_ring.rs：:394-409 reader 300¢/writer 298¢ 收敛钉、:782-800 ring_budget_is_shared_across_members_and_circuit_breaks（账本尽→恰 1 launch）、:813+ turns 帽熔断+单 launch 收敛到 min(spec,plan)、token 帽熔断、clock_ms 强制集外拒收。亲跑 cargo test -p af-execline --test pkg_reportkit_ring → 13 passed 1 ignored（忽略项=real_model_ring_smoke_minimal_plan 真模型冒烟需网络密钥，非 C-33 钉）。
- **载体**：`ecb5d99`, `53c2504`, `2d81577`

#### W1-C-34

- **修复**：预算面半开半闭已收口，本波亲验全绿：PlanBudgets::of（graph_unit.rs:1091-1150）按 (scope,dimension) 白名单——plan/cents（正典 id cost_cap）、plan/tokens_total（token_cap）、node:*/turns（要求实际落在某 node_exec 投影、悬空 node: 路径拒收，且声明 cap 与投影 cap 逐项互核——W2-C35 追加）、其余合法但未实现组合一律 ExeclineError::PlanBindMismatch 拒收（error.rs:87/259 钉死 PlanBindMismatch=EX4005），无任何静默 continue。钉子测试 tests/graph_unit.rs:1890-1931 unsupported_budget_dimension_scope_combos_rejected 五组合（plan-clock_ms/plan-model_calls/node-cents/loop-turns/悬空 node:ghost-turns）全断 EX4005+点名强制集文案。亲跑 cargo test -p af-execline --test graph_unit → 28 passed。
- **载体**：`ecb5d99`, `ff68d80`, `2d81577`

#### W1-C-35

- **修复**：已在分支落地（ecb5d99）：亲读 crates/af-execline/src/driver.rs:636-658 emit_mes_if_missing——重放路径按该 op 首次成功账本序号（records().rev().find(op==kind && ok)）重构 event_id（含 instance 判别量），经 MesFileWriter has_event（mes.rs:35-41，load 正本全文对账）查缺，缺则补发、在则幂等跳过；release/start/complete/close 四跃迁重放臂全部接线（driver.rs:313-315/323-325/426-428/436-438），CH 面仍按 event_id 差量去重不双记。亲跑：cargo test -p af-execline --test mes_sink replay_backfills_mes_event_lost_by_first_write_failure → 1 passed（首写失败注入→重放补发断言），全套 mes_sink 12 passed。
- **载体**：`ecb5d99`

#### W1-C-36

- **修复**：graph 结果行已改走统一行契约，本波亲验全绿：graph_unit.rs:380-432 结果行经 crate::record::swev_v1_row（record.rs:209-245，swev/report 同款投影）落 records.jsonl，ExecutionFacts 携 status/gate/evidence.run_dir(=attempt 目录)/usage 三分账/wall_ms/note（graph nodes/cents/tokens 摘要降入 note），suite/order_id/nodes/cents_used 等契约外键不再出现。钉子测试 tests/graph_unit.rs:437-484：恰一行、12 契约键逐一点名在案、契约外 5 键逐一点名缺席、evidence.run_dir 指向实存目录、usage.quota input=300/output=150/cache_read=30 值级钉死、item_id=TASK。亲跑 cargo test -p af-execline --test graph_unit → 28 passed（含本钉）。注：落地契约-v0.md 不在本工作树（未找到该文件），键集以共享合规投影 record.rs 为正本核对。
- **载体**：`ecb5d99`, `2d81577`

#### W1-C-37

- **修复**：边级重影拒绝已在前波落地（planbind.rs:182-196：BTreeSet<(to,input)> 装订期扫描，重复即 EX4005「边级重影：…多条边命中同一 (to,input) 端口（载荷二义，先拒）」）；本波补齐 fixHint 点名的顺序对抗面——把钉子测试 tests/graph_unit.rs:1933-1970 duplicate_to_input_edges_rejected_at_bind 扩为两序：重影边（不同上游 reviewer.review=不同载荷）push 在后（后边胜面 dup-after）与 insert(0) 在前（前边胜面 dup-before）都必须拒。红绿亲验：临时注释 planbind 边级重影检查块后 cargo test -p af-execline --test graph_unit duplicate_to_input_edges → FAILED（两序皆红，钉子咬合）；git checkout 恢复后全量重跑 → 28 passed 全绿。提交 cb18dca。
- **载体**：`ecb5d99`, `cb18dca`

#### W1-C-38

- **修复**：非重修，系复核确认：前波 ecb5d99 落 planbind.rs:197-231 路径安全门——节点 id（graph+node_exec 两面）与 artifact/consumes 端口名拒 '/'、'\\'、空段/./..（纯点号段）及前导点端口名，词法拒绝覆盖绝对路径与 .. 穿越（join 逃逸仅此两通道）。本波亲跑具名测试 path_unsafe_node_ids_and_ports_rejected_at_bind（slash-id：pl/../../escape、dotdot-id：..、slash-port：pl/an 三例均 PlanBindMismatch 点名「路径分隔符/纯点号段」）绿。
- **载体**：—（前波 ecb5d99 承载，本轮零改动）

#### W1-C-39

- **修复**：归属修正+钉子在位，本波亲验全绿：GraphTask::parse（graph_unit.rs:940-951）str_field 错误文案改为「图输入缺 {name} 字段（执行器容器 setup 硬性必填——起容器需要镜像名；非 swe_task_input schema 必填项）」，不再把执行器自加要求说成 schema 面要求（旧文案「（swe_task_input 面）」已禁）；分层保留——schema 门照放行缺 image 输入、解析门如实拒。钉子测试 tests/graph_unit.rs:2173-2214 image_missing_error_attributes_executor_setup_not_schema_gate：抹去 task.json 的 image 后断 EX3001、文案含「执行器容器 setup 硬性必填」与「非 swe_task_input schema 必填项」、不含旧文案、解析门前 runner.launches() 空+bridge.calls() 空。亲跑 cargo test -p af-execline --test graph_unit → 28 passed（含本钉）。
- **载体**：`ecb5d99`, `5ced300`, `cb18dca`

#### W1-C-41

- **修复**：已在分支落地（ecb5d99）：亲读 crates/af-order/src/voucher.rs:38-40（VoucherRecord.line_id Option 字段，旧行无键=None 不核对=历史盘兼容）、:91-99（盘上 line 与本次 spec.line 不符即 OR2003 fail-loud「产线绑定不可经重放偷改」）；cli.rs:240 凭证/MES/订单三面同值。亲跑：cargo test -p af-order --test cli resubmit_with_different_line_is_rejected → 1 passed（换线重放被拒负例，fixHint 要求的换线负例在位）；全套 af-order cli 8 passed。
- **载体**：`ecb5d99`

#### W1-C-42

- **修复**：本次修复：C组确定性-对应表.md §三.6 原「不在义务清单：B-02/…/B-16..B-23」改为「在义务清单、本批无证明载体」（亲跑 grep -c '^## B-' theorems-v1.md = 23 证实为正式义务），§〇 加 39/57 全库覆盖率披露，§三.6 附 coverage-check 机算块（covered: Kani INV A-01..A-16 + Kani17×11 + FV-0.1×3 + Verus D-01..D-09；uncovered 18 = 部分 C-05/覆盖注记 B-12/仅陈述 B-20（Rocq T10 Admitted 亲核）/受阻 C-06·C-08·C-09/无载体 B 组 12 条）；/tmp/fv_coverage_check.py 对 theorems-v1 条目头做 57=39+18 闭合校验，修前 rc=1（无披露块）修后 rc=0；源裁决亲核（RUNLOG「32 successfully verified harnesses」、RUN-SUMMARY「29 verified, 0 errors」）。FV-1-第一波-裁决 §一 加全库覆盖口径行。
- **载体**：—（工作区原地勘误；af 仓披露面随 a37453b）

#### W1-C-44

- **修复**：fixHint 全部落地（commit 71b7cef）并亲验：ci/run.sh:252-271 抽取 Complete 汇总行后改用『[ -z "$complete" ] 字符串判空』（不再有 grep|tail 管道退出码恒 0 的死告警分支），缺行即 FAIL rc=1；解析并断言 verified=32/failures=0/total=32，任一不符 rc=1（措辞比 fixHint 的 WARN 更严：FAIL）；step9 收尾（ci/run.sh:285-291）fv_advisory 非零 → ADVISORY-WARN——零 harness（输出 No proof harnesses，cargo kani 仍 exit 0）与计数漂移均不得 ADVISORY-PASS。亲验方式：抽出 ci/run.sh:252-271 原样逻辑块（仅去注释行）对 5 份合成日志运行——『32/0/32』→rc=0 过；裁判 drop 变异『26/0/26』→FAIL；『缺 Complete 行』→FAIL；『No proof harnesses…』→FAIL；『31/1/32』→FAIL，5/5 符合（bash /tmp/w1c44-test.sh，pass=5 fail=0）；bash -n ci/run.sh 过。未重跑写入型真 Kani 构建（指令明示九门由汇总员统一跑；本树同状态此前全绿证据见 commit 9666c6c/2d81577：step9 Kani 32 verified/0 failures；/dev/shm/fv0/kani-0.68.0 在场但本轮不触发写型构建）。基线分支已含修复，本轮零改动、无新 commit。
- **载体**：`71b7cef`

#### W1-C-49

- **修复**：前批已在机器清单.md:10 补 10-24 红色事件（巡检日志:418/:421）与清理前后数字。本次按 fixHint「保留最新实测时点」复测刷新：亲跑 df -h / = 92% 用/40G 余（23:0x，已越 tools/local-image-feed.py:29 DISK_PAUSE_PCT=85 闸线），du -sh afbuild-* 实测 top=afbuild-phase2rt 32G/afbuild-w3-order 19G；现状表时点值更新（清理前 122G 缓存/清后 81%/85G/13:3x 84%/23:0x 92% 分列）并按文头更新纪律追加 23:0x 更新记录行。
- **载体**：—（工作区原地勘误）

#### W1-C-50

- **修复**：前批已改机器清单.md:12 anolis 行为「83% 用，48G 余（2026-10-26 08:2x 实测）」附 W1-C50 勘误。亲跑 ssh anolis 'df -h / /data' = /dev/vdb1 295G 232G 48G 83%（/ 98G 76G 19G 81%），与现状表一致，自相矛盾的 10-22/10-23 更新记录注记在位。
- **载体**：—（工作区原地勘误）

#### W1-C-51

- **修复**：前批已按实况改写机器清单.md:14-15 并加勘误。亲跑 tailscale status = 5 节点（.8 pandev-comp/.7 anolis-gpu-01/.6 governance-machine/.2 mingda-website/.1 node|phone-admin|harmonyos|offline 5d），与表一致。本次补修同缺陷在 00-总纲.md §3 的残面：原「离线（cloudpc/harmony-vm/mingda-website）不参与」行改为「cloudpc-01/harmony-vm 已不存在（10-21 headscale 删）+ mingda-website 在役第三执行面/MES 驻点」，指向机器清单 5 节点现状。
- **载体**：—（工作区原地勘误）

#### W1-C-52

- **修复**：非重修，系时效性复核确认无需改动：前波 W1 修复批已于 2026-10-26 08:4x 终态刷新该文档（:191 更新记录在案；行 9 五 crate 落成+af-plan 折入+修复批待合流如实注记、行 10 packages 63 条、行 11 执行面、行 12 GitHub、行 13-14 G0-G5+A1、过期 af-wt-phase2-order/phase2-order 指针已删）。本波亲跑时效核对：git ls-remote origin（gitea）refs/heads/phase2 = 438fa6d 且 phase2-redteam-fixes 不在远端（行 9「待合流/待推送」仍准确）；GitHub API /repos/Feasy898/af/branches/phase2 → 51955fb「merge: phase2-g5-final…」2026-10-25T15:42:38Z（行 12 逐字相符）。git ls-remote github 本会话亲跑通（未把更早的 GnuTLS 失败算作通道状态）。
- **载体**：—（工作区原地勘误）

#### W1-C-53

- **修复**：前批已改 AGENT.md:28、计划/20-质量保证体系.md:13、组件建设状态.md:39 为九门（step1-8 硬门+step9 FV advisory）附 W1-C53 勘误（grep 三文件核过）。本次修同文件计数滑误：组件建设状态「G1-G5 六门 + A1」改为「G1-G5 五门 + A1（G0 见上行，阶段门合计 G0-G5 六门）」，与 G5-门终裁 §四「六门=G0-G5」口径闭合；:100/:140 的「CI 六门全绿」为 10-19 时点历史叙述按 fixHint 保留。
- **载体**：—（工作区原地勘误）

#### W1-C-54

- **修复**：前批已改 00-总纲:16 与 G5-健康度首报:73 为「57=G3 时点值；终态 63（+reportkit 6）」双口径。本次机算复核：git show 438fa6d 六个 af/packages/**/components.json 计数 44+2+5+6+1+5=63，与 registry_decl_test 断言一致。af/packages/README 的 57 旧数勘误已在 af 仓 phase2-redteam-fixes 分支:108-111（亲核在位，待合流）——af 仓侧不属 docs 域，未触碰。
- **载体**：—（工作区原地勘误；af/packages README 侧随 a37453b）

#### W1-C-55

- **修复**：前批已把 G5-健康度首报:100 成功格改为「completed+verdict=true ×5（F1/F2/F3b/F4a2/F5c）+ max_turns+verdict=true ×2（F3a/F4a）+ graph ×1（F4D）= 合计 8」，注明原 completed×6 多算的正是 F5b、×3 实为 2。本次以本人 15 目录逐单解析复核该三数（5/2/1）全部成立；并修复该勘误引入的断链引用（:91「A1 注记⑦」实为注记④，已改）。
- **载体**：—（工作区原地勘误）

#### W1-C-56

- **修复**：前批已把 00-总纲:5 头部改为「最后更新：2026-10-26（红队修复批 W1 收口刷新…；正文收官状态 2026-10-25 原貌）」——头部日期随实质更新、正文各事件时点保留，符合 fixHint；与 AGENT.md/README 的 10-26/10-25 标记不再矛盾。
- **载体**：—（工作区原地勘误）

#### W1-C-57

- **修复**：前批已把 00-总纲:87 分工行改为「~~优先 grok（anolis）多实例并发~~（已作废…hk-gateway 出口 2026-10-20 失效…anolis 无可用外网代理，grok 出网需另行裁决）；现役主力 = GLM5.3」，与 AGENT.md 硬纪律 3/10-环境与分工.md 作废注记一致（grep 核过）。
- **载体**：—（工作区原地勘误）

#### W1-C-58

- **修复**：前批已改组件建设状态 §一为「当前基线 CI step3 1260 测试 0 failed，git 438fa6d」，原「174+1、git 60f6861」标注为 10-19 起点值，crate 清单改 22 个。本次机算复核：git ls-tree --name-only 438fa6d:crates | wc -l = 22；step3.log test result 求和 = 1260。00-总纲:25 的 60f6861/174+1 保留为「为起点」叙述（fixHint 允许的历史起点口径）。
- **载体**：—（工作区原地勘误）

#### W1-C-59

- **修复**：①判据面钉死（ecb5d99）：亲读 crates/af-order/src/cli.rs:663-676 pin_task_digest 按 unit 取判据真值源、:270 经 DriverConfig.task_sha256 下传；crates/af-execline/src/exec.rs:88-105 verify_task_digest 摘要不符即 UnitFailed 拒绝执行；swev_unit.rs:165-166 在任务装载后、setup/run 前核对（执行前钉死）。②零测试门（ecb5d99+62287ef）：亲读 crates/af-execline/src/suite/swev.rs:350-380 verdict_from_judge_row——tests_collected=0 时 resolved=true 一律降级 None 不当成功（进入 qualified=verdict==Some(true) 订单 verdict 门，close 门不放行）、false 保持失败、缺字段不触发门。亲跑：cargo test -p af-execline --lib verdict → 5 passed（zero_tests_downgrades_resolved_true_to_not_success 等）、cargo test -p af-order --lib pin_task_digest_reads_criteria_source_per_unit → 1 passed。
- **载体**：`ecb5d99`, `62287ef`

#### W1-C-60

- **修复**：非重修，系复核确认：前波 71b7cef 改 ci/neutrality_scan.py 词边界为 ASCII 口径 (?<![A-Za-z])词(?![A-Za-z])（:87-95 注释登记机制与 \b 含 CJK 的失明根因）并加 --self-test。本波亲跑：python3 ci/neutrality_scan.py --self-test → PASS（中文语境 4 词全命中/ASCII 复合标识符 5 例零误伤）；另做隔离端到端三探针（临时仓副本+最小词表，双扫描根齐备）：①中文紧贴『实现git仓库的patch提取与diff比对』→ exit 1 白名单外命中 4（旧 \b 口径下为 0）；②ASCII 标识符 ErrorCode/digit → exit 0 零命中；③ASCII 相连 agitz/repository.commitment → exit 0 零误伤。正仓全量扫描未跑（属汇总员九门口径，按指令不跑全量门）。
- **载体**：—（前波 71b7cef 承载，本轮零改动）

#### W1-C-61

- **修复**：fixHint 首选路径『第三指纹锚』已落地（commit ecb5d99）：report_unit.rs:48-53 增 render_sha256 锚（production 缺省=255f68f7…），:78-90 check_fingerprints 循环含三对（citation/rubric/render），不符 EX3002 拒；另有 W2-C52 在场性门拒 __pycache__/*.pyc 影子加载（rubric 动态 import render 的旁路面）。亲验：①盘面对照 sha256sum af/packages/reportkit/{units/citation_unit.py,units/rubric_unit.py,tools/render.py} 三枚哈希与源码锚逐字节相等；②亲跑 cargo test -p af-execline --test pkg_reportkit fingerprint → 3✓（含 judge_fingerprint_gate_rejects_tampered_renderer_with_ex3002：改 render_markdown 函数名的篡件被第三锚拒收 EX3002、judge_fingerprint_gate_rejects_planted_pyc_shadow、篡改 citation 脚本拒收）；③production 锚自检 report_judge_production_anchors_match_files_on_disk → ok；全套 --test pkg_reportkit → 16 passed/0 failed（CARGO_TARGET_DIR=~/afbuild-phase2rt-misc）。fixHint 的『更根本地冻结期望渲染结果』属加码建议（『或』后从句），R5 同源判据基准已被 sha256+pyc 双门钉死，篡改判据必动 render.py 字节即被 EX3002 截获，未再加冻结果面（改判据语义超出本条缺陷面）。基线分支已含修复，本轮零改动、无新 commit。
- **载体**：`ecb5d99`

#### W1-C-63

- **修复**：双保险已在分支落地：①event_id 加实例判别量（fa0ec74 C-53）——亲读 driver.rs:621-627 event_id=「{stable_id}:{kind}:{seq}:{instance}」，instance=订单目录规范路径 sha256 前16hex（driver.rs:174 注释钉死同根重放稳定）；②同 id 异线 fail-loud（ecb5d99）——亲读 crates/af-execline/src/mes_ch.rs:228-266 读侧建 event_id→line_id 映射，同 event_id 异 line_id 即 MesCh 错误拒并（不静默互吞）。亲跑：cargo test -p af-order --test cli same_order_id_across_state_roots_gets_distinct_event_ids → 1 passed（跨 state 根 event_id 不再逐字节相同）；cargo test -p af-execline --test mes_sink ch_sink_same_event_id_different_line_fails_loud → 1 passed。
- **载体**：`fa0ec74`, `ecb5d99`

#### W1-C-64

- **修复**：三面同值+聚合排除已在分支落地：①stub: 前缀（ecb5d99）——亲读 crates/af-order/src/cli.rs:229-240 stub 档在凭证签发前把 spec.line 换成 stub:<line>（凭证/订单绑定/MES 三面同值）；②产线聚合排除（62287ef）——亲读 crates/af-mes/src/schema.rs:60-75 mes_line_hour_mv DDL 增 WHERE line_id NOT LIKE 'stub:%'（含存量部署旧行不改写的运维面注记）。亲跑：cargo test -p af-order --test cli stub_submit_marks_mes_line_with_stub_prefix → 1 passed（MES 事件 line_id 全为 stub:line-poc）；cargo test -p af-mes --lib materialized_view_excludes_stub_smoke_lines_from_production_aggregation → 1 passed。
- **载体**：`ecb5d99`, `62287ef`

#### W1-C-65

- **修复**：五处工作区文书（G3-v2:88/:126、G2G3:41、G4-软工包设计:44、中立性方案:295）前批已带「实为 37 件」内联勘误；本次亲跑 git show aff4f1a:af/packages/components.json 机算闭合正本口径：44 条 = 37 pkg.*（aflowkit2/agensh8/camelkit1/crewkit7/debatekit2/reactkit2/reflexkit3/sweagent10/langgraph1/openworld1，恰 37、无其他前缀）+ 7 route.*。本次补缺：变更日志漏登记勘误，已按活文档纪律追加 23:4x docs 域条目（历史誊抄条 :123 按禁写规则不动）。af/packages/README.md 的 35→37 勘误在 af 仓 redteam-fixes 分支:117-120（亲核在位），af 仓与 commit message 不属 docs 域。
- **载体**：—（工作区原地勘误；af 仓侧随 a37453b）

#### W1-C-66

- **修复**：前批已把 A1:11 结果列改为「F3a 3t 解（max_turns 收束但 verdict=true——意外成功）→F3a2 2t 真失败（verdict=false）」并附勘误，成功计数统一 8。亲读 F3a records.jsonl 末行 status=max_turns/verdict=true、F3a2 verdict=false，与文书一致；G5 首报成功名单同口径。
- **载体**：—（工作区原地勘误）

#### W1-C-67

- **修复**：前批已在 G4-任务中立性机器检查方案.md:4-10 加勘误头（19→21→22 演进）并回填全篇（§1.3:122、I1/I2:157-158、§五:330 等 12 处改 22，「19 项」仅存于勘误头自述）。亲跑 grep -vc '^\s*$\|^#' af-wt-phase2-execline/ci/neutrality-expected-fail.txt = 22，名单与方案一致，名单头部同步纪律在方案:330 复述。
- **载体**：—（工作区原地勘误）

#### W1-C-69

- **修复**：af 仓侧已按 fixHint 例外登记路线落地：phase2-redteam-fixes 分支 af/packages/README.md:24-30 登记「reportkit 组件名段 pkg.report.*（六件亲验）≠目录名 reportkit、与 template_ref pkg.reportkit.* 两段并存为已知例外，消费者按 components.json 实况解析」（af 仓未触碰）。本次补工作区侧同步：G4-施工裁决-20261025.md 裁决 12「组件名段匹配包目录约定不破」处补该已知例外，G4-研究报告包设计-v1.md §2 头加命名段例外登记（声明 pkg.report.*/pkg.reportkit.* 均为终态非笔误、禁止以包目录名推导组件名段）。
- **载体**：—（工作区原地勘误；af 仓侧随 a37453b）

## 五、附记：复核批、全域合龙与域分支合入（2026-10-26 晚 → 10-27 凌晨）

- **复核批（23:05-23:13，3 个 commit）**：5ced300（C-39 归属钉子 TDD 补齐——先红后绿；同轮对 C-29/C-32/C-33/C-34/C-36/C-37 共 7 条核验在位修复并亲跑钉子，除 C-39 外余 6 条钉子测试亲跑全绿）；e858a3f（C-05 ADR README 索引 005 行补取代关系，仅 add 本方文件、未触并行修复员未提交改动）；62287ef（C-59②判据门测试化：verify 判分行口径抽纯函数 verdict_from_judge_row+5 新测试先红后绿；C-64 产线聚合显式排除冒烟档：mes_line_hour_mv DDL 增 WHERE line_id NOT LIKE 'stub:%'，ADR-011 裁决7 补记两处落地）。
- **W3-C19/C-60 临时红的闭合（全域合龙批，cfcaaab/2d81577）**：W1-C-25 与 W1-C-60 两条在复核批时点如实报告的并行 WIP 所致临时红（construct_conflict_test 两条多报 E2202；S1 词表 terminal 541→587 漂移+debate:79 未登记），由红队修复员在全域合龙批收口：construct_conflict_test 两夹具按 W3-C19 迁移补 `emits: { done: signal }`（inv4_test loader 同款先例形态，判据本体 E2209/零违例不变）；词表按漂移修正+debate 条目登记（扫描复跑 18 处全豁免、0 失效）。同批落地全域修复员 W3 域修复（af-dsl C16 大栈线程/C17 E2002 二分/C18 schema 形状门/C19 终态 emits 必填；af-compiler C20 内联原始型规范化+golden 同步），并对域修复做格式（cargo fmt）、clippy（unused_doc_comments）收尾。
- **终局硬线（2026-10-26 23:34）**：全域合龙批终跑 `CARGO_TARGET_DIR=~/afbuild-phase2rt bash ci/run.sh` exit 0——step1-8 全 PASS（step8 中立性门 12 判据全过：C1 对照臂两 crate exit=0、I1/I2/I3 隔离臂失败集与预期红名单 22 项精确相等、S1/R7/Z0 过）+ step9 ADVISORY-PASS（Rocq 10/10、Kani 32 verified/0 failures）；证据入档 2d81577。W1 批 54 条修复在此终态树上全部在位。
- **域分支合入与合龙九门两处红项修复（2026-10-27 凌晨）**：五域分支 phase2-rt-af-{execline,order,misc}（已是指标，`git merge --no-ff` 报「已经是最新的」）与 phase2-rt-af-dsl（61fa507 C-27 memory 面钉子 + 24b2abf C-28 EX4006 fail-loud）、phase2-rt-af-compiler（cb18dca C-37 顺序对抗钉）按序 --no-ff 合入 phase2-redteam-fixes（合并提交 d9cf17d/475329f，零冲突；五支合并后均验证为 HEAD 祖先）。合龙九门首跑 step2/step3 双红，失败即修：①step2 clippy useless_format——af-dsl 合并带入 bind_test.rs:603-644 无参 `format!` 包装，去包装并还原转义双花括号（bind_test 20✓）；②step3 lifecycle 2/6 例 `EngineSpawnFailed` ENOENT——根因为 `EngineClient::locate` 落锚 `std::fs::write` 截断+写非原子，8 线程并发 locate 读写交叠（TDD 红证：并发读者实读 `""` 与 32 字符半行）→ 误判锚不符 → 案例③ `cargo clean -p af-engine` 删 bin 重建 → 他线程定位好正待 spawn 时 bin 被删；standalone 跑又因状态自洽全绿（纯竞态）。修复：locate 全程进程级互斥（重建持锁、等待线程复验后「验过即用」，中毒锁恢复不放大故障）+ 落锚原子化（同目录临时件 + rename）。TDD 先红后绿：新钉 `trust_anchor_write_is_atomic_for_concurrent_readers` 现码实读 `""`/半行红、修复后绿；`concurrent_locate_absent_anchor_never_rebuilds_or_destroys_bin` 钉零重建；W2-C56 篡改捕重建测试安全语义不退化。另：ENOSPC（根盘 100% 写满）致共享 target 内 af-dsl rmeta 损坏（`derived_emit_type` 丢失）——清理陈旧构建目录后强制重建恢复，非代码缺陷。
- **终局硬线（2026-10-27 02:04）**：五域分支合入后终跑 `CARGO_TARGET_DIR=~/afbuild-phase2rt bash ci/run.sh` exit 0——step1-8 全 PASS（step3 含 lifecycle 8✓/p5_wiring 4✓）+ step9 ADVISORY-PASS（Rocq 10/10、Kani 32 verified/0 failures）；证据入档 5a73ba4。W1 批 54 条修复在含域分支的终态树上全部在位。
