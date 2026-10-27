# 红队第 3 波（W3）全程记录

- 日期：2026-10-27（候选投喂 → 裁判裁定 → 五域修复 → 全域合龙批九门终跑，全程当日完成）
- 波次对象：第二阶段交付全景 + W1/W2 修复面自身（af 仓 @438fa6d + phase2-redteam-fixes 全域修复面 + 工作区文书）——判分链真值面/形式验证载体/中立性门解析/退役观察期自动化/文档口径七向审计
- 修复执行：红队修复员（glm5.3）——五域修复员按域分苗（af-dsl/af-compiler/af-execline/af-order/misc，各自域分支）；全域合龙批由红队修复员按序 --no-ff 合入五域分支并终跑九门
- 本记录路径（返回路径确认）：/home/pan-ding/workspace/agent黑灯工厂/计划/研究组/红队收口/wave3-记录.md
- 硬线核验：ci/run.sh 九门全绿——修复员亲跑 exit 0（step1-8 PASS + step9 ADVISORY-PASS）：①af-dsl 域复跑（step8 中立性门 13 判据全绿，R8 新判据首跑 PASS，证据入档 9e8008a）②**全域合龙批终跑（2026-10-27，全域修复员 32 条 W3 修复全部同树合验——step1 K5 判分链 lint PASS（W3-C-34 judge.rs 导入链六锚 da945f50/W3-C-06 rubric e8b67eb6 两锚换版裁决登记后逐位对锚）、step8 中立性门 13 判据全过（R8 解析对账 PASS「原始 FAILED 行=解析键=cargo 汇总=23、未归类=0」、I1/I2/I3 集合精确相等 @23、S1 词表 reflexkit 勘误后 18 豁免/0 白名单外/0 漂移）；9a Rocq 10/10 + 9a-2 定理清单对账 21 条定理名逐位一致+陈述块 SHA-256 一致（57f6393869e9…，W3-C-29 新增判据）、9b Kani 32 verified/0 failures；证据入档 239f16a）**
- 本记录口径：裁定分布按裁判最终裁定清单计（43 候选 = real 32 + overturn 0 + not 10 + handled 1 闭合）；席/候选明细以裁定书所引 sources 为准（可机算面），未下发编号如实注记不臆测——本节 §一 席-项归类按各修复项自证域归属归纳（裁判 sources 编号未随修复材料下发，per-seat 编号以裁判侧正本为准）
- **漏检根因存档**：逐条「根因/本应拦在/改进」分析=后台产物另档（whys artifact，**按波次覆盖**、不保证跨波留存）——本记录不内联其内容；波次收官如需留存须随波次另档拷贝，勿依赖覆盖前的后台产物

## 一、12 席清单

| # | 席（source 前缀） | 焦点 | real 裁定项（按修复清单域归属归纳） |
|---|---|---|---|
| 1 | `plan` | 计划/承诺对照席（总计划 §0/§2/§6 × 交付实况 × 退役观察期口径） | 5 条：W3-C-02、W3-C-03、W3-C-04、W3-C-05、W3-C-43 |
| 2 | `evidence` | 证据指针核验席（远端仓状态/密钥终扫计数 × 实跑复算） | 2 条：W3-C-33、W3-C-40 |
| 3 | `a1chain` | A1 验收链对账席（交付文对照口径残留） | 1 条：W3-C-41 |
| 4 | `cross` | 跨文书一致性席（pid 换装台账/ADR 枚举跨文书同步） | 2 条：W3-C-12、W3-C-32 |
| 5 | `docs` | 状态/活文档席（组件状态枚举与登记面自不闭合） | 1 条：W3-C-42 |
| 6 | `dsl` | af-dsl 语义面席（E 码迁移/human 嵌套门/内建端口声明/E0004 注记/inline_prims/map from_body） | 6 条：W3-C-15、W3-C-16、W3-C-17、W3-C-18、W3-C-19、W3-C-20 |
| 7 | `compiler` | af-compiler 席（对齐计划快照重生成） | 1 条：W3-C-21 |
| 8 | `execline` | af-execline 执行面席（预算巨帽/--unit 路由矩阵/B-02 载体口径/判分链真值入锚） | 4 条：W3-C-23、W3-C-24、W3-C-31、W3-C-34 |
| 9 | `order` | af-order 门面席（共享 target 跨树假绿/文书码位） | 2 条：W3-C-25、W3-C-26 |
| 10 | `fv` | 形式验证席（B-16 E2102 半边内核证据/定理清单对账） | 2 条：W3-C-28、W3-C-29 |
| 11 | `adv` | 对抗/可作弊面席（中立性词表词形/门解析扩面 R8） | 2 条：W3-C-35、W3-C-38 |
| 12 | `ops` | 运维/退役面席（pyc 影子/观察期自动复核/判据①订单核验/期满终局） | 4 条：W3-C-06、W3-C-11、W3-C-13、W3-C-14 |

十二席产出候选合计 **43 条**。其中 32 条 real-defect 裁定全部修复（fixed=true，逐条见 §四）；其余 **11 条非 real 候选**（10 not-defect + 1 handled）的个体编号未随修复材料下发——按编号连续性可辨未入任何 real 裁定的编号（W3-C-01/07/08/09/10/22/27/30/36/37/39 及 handled 1 条），非 real 个体与缺口号的关系以裁判侧裁定正本为准，本记录不臆测。

## 二、候选与裁定分布

- 候选总量：**43 条**（十二席产出）
- 裁定分布（按实际 verdict 计）：**real-defect = 32 / overturn = 0 / not-defect = 10 / handled = 1**（32+0+10+1=43 闭合）
- real 32 的构成：代码/仓内缺陷 13 条（af-dsl 6 / af-compiler 1 / af-execline 4 / af-order 2）+ 形式验证与门面缺陷 6 条（fv 2 / adv 2 / compiler 快照 1 + execline 判分锚计入上列）+ 工作区文书/口径缺陷 9 条（plan 5 / evidence 2 / a1chain 1 / cross 2 / docs 1）+ 运维自动化缺陷 4 条（ops 4）
- 修复结果：**32/32 全部修复**（fixed=true，逐条见 §四）——代码缺陷走 TDD（先红后绿）+ 九门全绿硬线；形式验证载体按裁决补内核证据或对账判据；文书缺陷原地勘误并留勘误注记；观察期自动化按 fixHint 落判定核心+期满终局+真机留痕
- 多源并案：本波无多源并案记录（每项 real 裁定对应单一缺陷面）

## 三、修复载体

| 类别 | 位置 |
|---|---|
| 代码/仓内文档（af 仓）· 五域分支 | 域分支 phase2-rt-af-{dsl,compiler,execline,order,misc}：af-dsl 域 98812b7（C-15/16/17/18/19/20 六条）/251e254（C-16/20 E2212/E2213 码位+SYNTAX/提案-B）/f3d9296（C-35 词表 reflexkit+行号漂移）/858da9e（C-28 B-16 E2102 探针）/a076601（C-29 定理清单对账）/967ee5d（C-38 R8 解析扩面）/9e8008a（step8 复跑证据）；af-compiler 域 5a2cf67（C-21 快照重生成+TSV 勘误）/6293e66（C-23 巨帽饱和）；af-execline 域 813b315（C-34 判分链真值入锚）/58c7a1e（C-24 --unit 路由矩阵回归）/e802606（C-31 B-02 部分载体五处同步）；af-order 域 907d470（C-25 target 溯源守卫）/c90e40e（C-25/26 RESULT 入档）/9a262fe（C-26 OR2003 回归锁）；misc 域 088bfc1（C-06 pyc 防再生成不变量）/e1a8937（C-06 在场性门适用分支注记） |
| 全域合龙批（af 仓） | 合并提交 911209c（dsl 域，10 文件含 proofs/kani W3-C28 补证+theorems-manifest.txt）/904b3a7（misc 域）/8a00bba（execline 域，C组表冲突语义合：HEAD 侧 W3-C28 B-16 补证保留+来方 W3-C31 B-02 移入 partial，闭合 40+2+1+3+11=57 机算亲验）/e8f1bbf（compiler 域）/1526768（order 域）；终跑证据 239f16a |
| 工作区文书（原地勘误） | 计划/研究组/{G4-任务中立性机器检查方案,G4-研究报告包设计-v1,G3-全链闸门-L1L4-v2,DSL-G0-必要性报告,密钥终扫-20261024,在飞bench盘点,F-第四单-交付,退役执行记录,旧bench退役归档-runbook,对齐计划快照/（15 份重生成）,形式化/theorems-v1.md,红队收口/wave2-记录.md}-*；计划/{00-总纲→.zcode/plans/plan-session_*.md,变更日志}.md；README.md；AGENT.md；状态/{机器清单,组件建设状态}.md；tools/{bench-retire-obs-review.py,test-bench-retire-obs-review.py,registry-effect-class-audit.py,test-bench-retire-obs-review-criteria.py}；crates/af-order/scripts/（target 守卫三件，随 af-order 域入仓） |
| 硬线核验 | `bash ci/run.sh`（CARGO_TARGET_DIR=~/afbuild-phase2rt）全域合龙批终跑 exit 0：step1（fmt+K5 lint，两锚换版登记后 4 件逐位对锚）/step2 clippy/step3 test（32 条 W3 修复同树）/step4 cue/step5 scrub/step6 cosign/step7 deny/step8 neutrality 13 判据全过（R8 新增）/step9 FV ADVISORY-PASS（9a Rocq 10/10 + 9a-2 定理清单对账 21 条逐位一致+陈述块 SHA-256 57f6393869e9…、9b Kani 32 verified/0 failures）——ci/out/SUMMARY.txt 随 239f16a 入档 |

## 四、修复清单（real 32/32，逐条；非 real 11 条无修复面，个体编号以裁判侧正本为准）

汇总表（id / fixed / commits；工作区原地勘误者 commits 为空；域分支 commit 均经合并提交 911209c/904b3a7/8a00bba/e8f1bbf/1526768 进入 phase2-redteam-fixes）：

| id | fixed | commits |
|---|---|---|
| W3-C-02 | ✅ | —（工作区：README/00-总纲/组件建设状态） |
| W3-C-03 | ✅ | —（工作区：总计划 §2 裁决2；af 侧三件已在分支） |
| W3-C-04 | ✅ | —（工作区：G4-门终裁/G5-门终裁/A1 终验） |
| W3-C-05 | ✅ | 9e8008a |
| W3-C-06 | ✅ | 088bfc1, e1a8937 |
| W3-C-11 | ✅ | —（工作区：tools+退役执行记录） |
| W3-C-12 | ✅ | —（工作区：机器清单/退役执行记录） |
| W3-C-13 | ✅ | —（工作区：tools） |
| W3-C-14 | ✅ | —（工作区：tools+runbook） |
| W3-C-15 | ✅ | 98812b7, f3d9296 |
| W3-C-16 | ✅ | 98812b7, 251e254 |
| W3-C-17 | ✅ | 98812b7 |
| W3-C-18 | ✅ | 98812b7 |
| W3-C-19 | ✅ | 98812b7 |
| W3-C-20 | ✅ | 98812b7, 251e254 |
| W3-C-21 | ✅ | 5a2cf67 |
| W3-C-23 | ✅ | 6293e66 |
| W3-C-24 | ✅ | 58c7a1e |
| W3-C-25 | ✅ | 907d470, c90e40e |
| W3-C-26 | ✅ | 9a262fe, c90e40e |
| W3-C-28 | ✅ | 858da9e |
| W3-C-29 | ✅ | a076601 |
| W3-C-31 | ✅ | e802606 |
| W3-C-32 | ✅ | —（工作区：AGENT.md/组件建设状态） |
| W3-C-33 | ✅ | —（工作区：README/00-总纲/组件建设状态） |
| W3-C-34 | ✅ | 813b315 |
| W3-C-35 | ✅ | f3d9296 |
| W3-C-38 | ✅ | 967ee5d, 9e8008a |
| W3-C-40 | ✅ | —（工作区：DSL-G0/密钥终扫） |
| W3-C-41 | ✅ | —（工作区：退役执行记录/F-第四单） |
| W3-C-42 | ✅ | —（工作区：G3-v2+tools 审计件） |
| W3-C-43 | ✅ | —（工作区：变更日志） |

逐条修复方式（how）：

#### W3-C-02

- **修复**：三处「观察期至 10-28」统一为期满 2026-10-29 01:05:52 并注权威出处：README.md:31、计划/00-总纲.md:21（同线两处：日期+勘误注「原『10-28』系孤立日期，runbook §六-3 权威定义」）、状态/组件建设状态.md:11。fixHint 复核面已做：全工作区 grep「观察期至」——剩余「10-28」字样仅存勘误注引文（变更日志:182 历史 W2-C17 条自述、wave2-记录.md:183 同）不属活性断言；在飞bench盘点-20261024.md:22 短式「观察期至 10-29」日级与权威定义一致、未动。
- **载体**：—（工作区原地勘误）

#### W3-C-03

- **修复**：总计划(.zcode/plans/plan-session_483404be…md)§2裁决2『五新crate含af-plan』划线并补勘误注：实交四crate、ExecutablePlan由af-compiler/src/plan.rs提供、折入经ADR-013追认（含取代范围与v0.2开放议程），原句保留裁决时点原貌——与00-总纲:12已有口径、ADR-013原文三处对齐。分支侧亲验：本支(phase2-rt-af-dsl)docs/adr/013-af-plan-fold-in.md、ADR-README:9取代行、002头注取代注均已随phase2-redteam-fixes合入在位（对照主线worktree af-wt-phase2-execline亲跑grep确认其仍缺三件——属合流即闭合，未直接改动他树防index争用）。
- **载体**：—（工作区原地勘误；af 侧三件已在分支）

#### W3-C-04

- **修复**：三处活性陈旧断言按fixHint统一勘误：G4-门终裁:33『剩余G5+A1尾项待12臂裁决』划线+双点勘误注（G5已六门全绿见G5-门终裁:27；运营者2026-10-26选项B+退役批已执行、现态=切流完成余观察期至2026-10-29 01:05:52复核归档）；G5-门终裁:29收口项表退役项比照前三项划销✅（注明10-26裁决B+退役执行记录-20261026.md、原句系mtime晚于执行仍未随动）；A1终验:43裁定段划线+与同文书:29 W2-C-44勘误判据行口径对齐。python复验：剔除划线与勘误引文后三文书活性残留=0。DSL-G0-必要性报告:36同族变体未动——裁判裁定明确三处活性收口陈述，该文件属历史阶段报告（同变更日志历史行类）。
- **载体**：—（工作区原地勘误）

#### W3-C-05

- **修复**：G4-任务中立性机器检查方案7处『22项』+头注勘误链全篇同步23（:5头注、:22裁决14、:117、:163/:164 I1/I2、:336、:350），:176失败集分解『golden 3』→4（=#23 plan_types_cover_every_port_type_base_name，注明W2-C-53补录归属）；G4-研究报告包设计-v1:360/:363两处同步23；§1.4补R8判据行（W3-C38随批）。正本面亲验：本支ci/neutrality-expected-fail.txt去注释去空行sort -u | wc -l=23；step8门复跑I1/I2/I3『集合精确相等(23项)』PASS实证正本与名单一致。主线worktree同文件22项属未合流面，随本支合流闭合（未动他树）。
- **载体**：`9e8008a`

#### W3-C-06

- **修复**：落位：worktree af-wt-rt-misc（分支 phase2-rt-misc）已存在，按指示 cd 入并 git merge phase2-redteam-fixes 同步前波至 4800a67，其上落两批提交。①亲证缺陷（均本会话亲跑）：find 得 12 份 pyc（11 份 render.cpython-314.pyc 散在 af-wt-calib/contract/exec/exec2/f5/fvint/g4/g5/g5final/phase2-execline/report + 主线 ci/__pycache__/neutrality_scan.cpython-314.pyc 未跟踪件）；python struct '<4sIII' 解包 11 份 pyc 头，内嵌 src_mtime/src_size 与各自 render.py stat 逐项全等=全部 shadow-active；git show 438fa6d 证主线 report_unit.rs 只有 citation/rubric 双指纹（rubric 锚尚为旧值 af63af2c…）、无 render 锚、无 pyc 在场性扫描——裁判指认属实：门只在修复树，主线 report 臂不被挡死。②清理：12 份 pyc 全数删除+空 __pycache__ 目录清除，终扫 af 系全部工作树 pyc/pycache 计数=0。③防再生成不变量（TDD 先红后绿）：再生向量定位=裸跑 rubric_unit.py（无 -B）时第 21 行 import render 落盘 pyc（判分子进程 -B 仅在 report_unit.rs 派生时注入）；新测 rubric_unit_bare_run_without_b_writes_no_bytecode 先红（实跑复现 rc=3、cached_exists=True、pyc 在盘）→ 修复 rubric_unit.py 在 import render 前置 sys.dont_write_bytecode=True → 转绿；pkg_reportkit 17✓（production 锚自检/planted_pyc_shadow/end_to_end 俱在）。④K5 锚纪同步：rubric_unit.py 换版 sha256 2e8ca98f…→e8b67eb6…，report_unit.rs production 锚与 ci/scorechain-manifest.txt（附 W3-C-06 裁决出处登记）双同步，亲跑 python3 ci/k5-path-lint.py=PASS（4 件逐位对锚）；cargo fmt --check 净、clippy 仅依赖项既有提示。⑤真实执行模块验证：真树（非副本）裸跑 rubric_unit.py（显式 env_remove PYTHONDONTWRITEBYTECODE）rc=0、passed=True、tools/ 零字节码在盘。⑥门适用分支写清：check_fingerprints 头注「双指纹门」表述漂移改为「三指纹锚+字节码在场性」并补注适用分支（本门随修复树生效、EX3002 不得归因主线 @438fa6d）——提交 e1a8937。⑦记录修正：红队收口/wave2-记录.md W2-C-50 条「全机唯一在盘 pyc」划改+补「红队 W3-C-06 勘误（2026-10-27）」注记（10 份存量 shadow-active 含 F5c 基准树、主线 06:17:32 再生件=有效影子、ci 未跟踪 pyc 致快照非字节干净、门分支归属澄清、处置与载体）；该文件在 agent黑灯工厂/计划/ 下、经 git rev-parse 证实仓外非 git 仓库，故为工作区编辑无 commit。未跑全量九门（按指令留汇总员统一跑），上述均为定向亲测。
- **载体**：`088bfc1`, `e1a8937`

#### W3-C-11

- **修复**：复核载体 tools/bench-retire-obs-review.py 扩容（该文件与 计划/ 均在 af 仓之外、从未入 git——`git ls-files tools/`=0 亲验，故就地修复无 commit）：①增采 状态观测/alarms.log（read_alarms 取 ts≥起算点全量入台账；A0/A7 登记预期灯只计数；A4L:tmp 按告警文案「可用 N MiB」提取、低于闸线 2252MiB 判负；未知 red/amber 码一律判负）；②增采 /tmp 头寸（tmp_capacity_mib，现值<2252 判负）；③新判据 2b 入判定、期满终局 criteria_unmet 与 verdict 文案；④采样失败面 sampling_failed_faces 汇总（fail-closed 不谎报）。TDD：新测试具 test-bench-retire-obs-review-criteria.py 13 例先红（0/13）后绿（13/13）；同文件 W3-C-14 修复员先批（evaluate() 注入化+期满终局面）全程兼容、其 14 例保持绿（夹具随判据集最小对齐、断言零改动）。真机亲跑留痕：2026-10-27 08:12:15 exit 0，JSONL 第 5 行首记 2b 异常——alarms 起算后 165 条（A0×61/A7×58）、ch-mes-timeout red（20:34:03）点名、A4L 低于闸线 43 条（1522→1779MiB）、/tmp 现值 1775<2252，sampling_failed_faces=[]。口径统一：退役执行记录 :152 核对法「A4L 黄=既有环境灯」以 W3-C11 勘误标记废止（与 :133 W2-C18 硬判据矛盾消除），并追加「观察期自动复核面扩容」登记节（含补做留痕全文）。
- **载体**：—（工作区原地勘误）

#### W3-C-12

- **修复**：亲跑核验：`ps -o pid,ppid,lstart,args -p 2122686`=在役（STARTED=二 10月 27 05:08:37 2026 python3 tools/factory-keepalive.py）、`ps -p 360104`=空。机器清单：现状表 pandev-comp 行改 2122686+勘误注（原格保留 04:4x 快照）、:64 W2-C-46 行内追加记、更新表末尾新增「2026-10-27 05:0x keepalive 受控换装补记」行（SIGTERM 优雅退→setsid nohup 拉起→2122686 在役，观察期锚点随之同步、后续 pid 变动须同步台账）；退役执行记录 :116 行内追记、:130 下增子弹追记（360104 仅存 10-26 01:05:52–10-27 05:08 史值）、:187 行内【追记】。巡检日志:431 原始留痕未动。
- **载体**：—（工作区原地勘误）

#### W3-C-13

- **修复**：同上仓外件就地修复：原 orders_since_start 目录 mtime 口径废除，改 list_order_candidates（全量候选目录）+ verify_orders_records 逐单核订单记录——ledger.jsonl 首条 op=create_order 的 ts_ms 判定核验单创建时间、op=close 且 ok=true 且 state_after=Closed 判终态、mes-events.jsonl kind 集合恰含 release/start/complete/close 判四类跃迁；ledger 不可读=verifiable:false（不凭目录存在记达成）；criterion1=起算后创建订单中存在 Closed+四类跃迁 且 CH af 线行数≥4（入账面保持，None 仍 fail-closed）。测试五例钉死：旧单 mtime 事后刷新不计入（F5c 实证路径复现）、未 Closed 不达成、kind 不齐不达成、零订单不空过、无 ledger 不可达成——先红（orders_verify_fn 缺位 TypeError）后绿。真机跑核：起算后核验单仍零（CH af 线 0 行）→判据①如实未达成，与退役执行记录排期一致。
- **载体**：—（工作区原地勘误）

#### W3-C-14

- **修复**：TDD（先红后绿）：先写 tools/test-bench-retire-obs-review.py（注入时间/采样面）跑出 RED=13 errors（module 无 evaluate）；后在 tools/bench-retire-obs-review.py 实现 evaluate()（纯判定核心：in_window=false 时 kind=…-final 终局记录、verdict 去「观察期内：」前缀、final.criteria_unmet/escalation_required）+ act_on_row()（停表恰一次；未达成才升级）+ stop_obs_timer()（systemctl --user stop+disable bench-retire-obs-review.timer）+ escalate_andon()（状态观测/alarms.log 追加 red 级 OBS-EXPIRE）+ has_final_record()（终局幂等防重跑连刷），main() 重接线→GREEN 14/14（0.002s）。真跑冒烟：`python3 tools/bench-retire-obs-review.py` 落窗口内行 2026-10-27 07:52:46、日报语义原样、timer 仍 active（list-timers NEXT=09:10 未被误停）。runbook §六-3① 同步补「期满自动终局」一句。脚本行文与测试件 py_compile 全过。
- **载体**：—（工作区原地勘误）

#### W3-C-15

- **修复**：check_schema_shape的human遍历由根层for doc.nodes改为walk_nodes深度遍历（与同模块check_vocab同一遍历口径，shape.rs），体内human.resume.schema同门E1003；修正函数doc注记。TDD：parse_test新增nested_human_resume_schema_shapes_are_gated_e1003（loop体标量/无type、map体数字三负例+loop体合法对象正例）先红后绿。亲验testdata全部6处human（含ADAS human_stop/sample5 approve/SWE-agent human_help三个体内嵌套）resume.schema均为object，正例语料零误伤；注释举名因ADAS/SWE属黑名单词改中性表述（中立性纪律）。
- **载体**：`98812b7`, `f3d9296`

#### W3-C-16

- **修复**：采fixHint选项一：construct_conflict迁移至语义段未分配的E2212（E2206在§6表跳空但系A方案自述码不占用），E2209归还提案-B§6既有分派『ops参数不闭合』——RESULT-M1/M2/M3/M4/fix2五处『E2209=ops参数闭合（未实装遗留）』登记就此与实现自然一致化，ops参数闭合落地不再撞码，五份RESULT无需改动。同步面：error.rs码位史注+E2212码、validate/mod.rs注释、tests/construct_conflict_test断言["E2212"]（红）、SYNTAX.md契约面（E2212迁移注+E2213/E1003新规则补登）、ADR-011裁决6原位勘误注（原claim引文保留）、提案-B§6表登记E2212/E2213（契约10→12条、合计54→56、余量6→4，工作区侧）。全仓grep核验剩余E2209均为规范义（ir.rs:374/model.rs:707 ops参数）或勘误引文。
- **载体**：`98812b7`, `251e254`

#### W3-C-17

- **修复**：refs.rs新增check_builtin_port_declarations：内建端口名（loop/map done、check/gate passed）的显式emits声明须与内建固定类型同型（done=signal、passed={type:boolean}），冲突类型或from_body死声明（emit_type内建短路下永不生效）→E1003 fail-loud拒绝，E1003码域定义同步扩展——存活文档的声明面/内建面恒一致，E2202按声明、边核对按emit_type、is_final经derived_emit_type三判定面口径统一。TDD：refs_test三新测（passed:a冲突/done:a冲突/from_body死声明）先红后绿；W2-C23同型去重两正例测不动仍绿（done:signal/passed:{type:boolean}合法保留），全语料grep确认无冲突声明被新门误伤。
- **载体**：`98812b7`

#### W3-C-18

- **修复**：error.rs E0004注记由『顶层只认七段 + version』（=8）改为『顶层只认七段：version/meta/types/stores/nodes/edges/policies』（=7），对齐envelope.rs BODY_KEYS(6集合段)+version与SYNTAX.md:11；勘误注记说明原误。纯注记无行为面，envelope/envelope_test零改动全绿。
- **载体**：`98812b7`

#### W3-C-19

- **修复**：lower()在构造Lowering后补meta.output.ref内联原始型入inline_prims（终态发射者ref必为内联原始型——derived passed:boolean与之同型，source处一次登记即闭合该路径），plan.types获得'{type:<prim>}'条目、执行面check_typed基名查询可解析。TDD：plan_test新增builtin_passed_frombody_final_registers_boolean_type_entry（loop体check节点+collector emits final from_body chk.passed+output.ref={type:boolean}）断言①types["boolean"]=={"type":"boolean"}（执行面EX4006查询位）②全计划恰一is_final（final_artifact_port门槛）——编译侧联合钉，先红后绿。17份golden output_type无内联原始型亲验+golden_test全绿=零扰动；执行面af-execline侧属并行修复员域未碰，契约已由①②编码。
- **载体**：`98812b7`

#### W3-C-20

- **修复**：采fixHint『显式拒绝于af-dsl阶段』：check_from_body对map构造的from_body目标端口推导类型为Inline时以新码E2213(map_frombody_inline_type)fail-loud拒绝——list<原始型>不在类型表达式文法（泛型载荷须已登记名/signal），转发端口类型不可表达，禁止再编译出零is_final工件的计划；loop构造不包list<>不受影响。新码经提案-B§6登记（与E2212同批，工作区侧）。TDD：refs_test新增map_frombody_inline_primitive_is_rejected（即裁判探针原形：map over input.items+体内check+final from_body chk.passed+ref={type:boolean}）先红后绿+反向钉loop_frombody_builtin_passed_still_passes零违例（W3-C19路径不误伤）；E2202的undecidable放行面保留给悬空/环域，本形已定罪。
- **载体**：`98812b7`, `251e254`

#### W3-C-21

- **修复**：先机算复核缺陷（python 逐份 15 快照：nodes=247、context 0/247、consumes 0/247、artifact_contract.type 0/269 全缺席、registry_digest 15/15=手改值 63c3478e…，与裁定一致），再按 fixHint 用当前编译器全量重跑：在本工作树（af-wt-rt-af-compiler=phase2-redteam-fixes@4800a67+本波修复）构建 af-compiler-plan，对 crates/af-compiler/testdata/src/ 同名 15 稿逐份 `af-compiler-plan --registry af/packages` 重产并覆盖 计划/研究组/对齐计划快照/*.plan.json（非改行）。重产后亲验：context 247/247 在场、consumes 203 节点非空（空者键省略=无入边，plan.rs:167 skip_serializing_if）、artifact_contract.type 240/269（Option None 省略，plan.rs:181-183）——与候选证据期望值逐文件吻合（MetaGPT 17/16/17、ADAS 21/16/20）；registry_digest 15/15 仍 63c3478e（63 条代际不变，TSV PLAN 行登记值维持有效）。对重生成 diff 做全量语义分类机算：除 1782 个三面投影键外，另有本树已合入的 IR 演进事实——5 份 route_exit_guard 全否守卫（23d9d7a af-dsl W1 C-24）、6 份 types+signal 使用面内建条目（e4d67aa W2-C-27，与前者交叠 MetaGPT/CrewAI-YAML）、Multi-Agent-Debate types+string（cfcaaab W3-C20 inline_prims，Debate.yaml:17-22 确用内联原始型）——致 10 份 dsl_digest/plan_id 如实换代，旧 c09249e8 等值属旧代际；此外零漂移。双跑 cmp 15/15 逐字节一致（确定性）。文书同步：ci/neutrality-golden-registry.tsv 头注勘误（原「15 份快照以本树 registry 重跑 cmp 15/15 逐字节全等（plan_id 逐字一致）」「逐位一致性登记」标注为对投影落地后编译器不可复现——快照 mtime 2026-10-25 10:44:50 早于 d34633b 14:51/05546bc 16:54，系旧计划体+手改 digest 行混合体），登记重生成事实并把现行验收判据改为「以本树 af-compiler 重产 cmp 15/15 逐字节全等」；TSV 改后按门脚本原码亲跑 R7 闭集守卫=OK（21 份互为闭集）。G4-任务中立性机器检查方案.md §0-5 裁决8 条、§3.2 裁决8 段（新增 W3-C-21 勘误+重生成段）、§3.3 快照清点行同步勘误并明确旧快照代际退役。注：快照与 G4 方案在黑灯工厂仓（非 git 仓库），仅 af 侧 TSV 可提交
- **载体**：`5a2cf67`

#### W3-C-23

- **修复**：TDD 先红后绿。红：crates/af-execline/tests/pkg_reportkit_ring.rs 新增 ring_plan_giant_cost_cap_saturates_and_reader_does_not_melt_early（ring_task_package_mutated 把真计划 cost_cap 改 2^63 与 u64::MAX 两档，断言满环走通 verdict=true、reader 帽 300、writer 帽 298）——修复前亲跑得红，错误文案逐字复现裁定证据「报告环预算熔断：reader 前环内累计 0¢ ≥ 环级帽 -9223372036854775808¢」。绿：crates/af-execline/src/suite/report_unit.rs:724 `entry.cap as i64` 改 `i64::try_from(entry.cap).unwrap_or(i64::MAX)` 饱和换算（巨帽≈无帽，与图执行器 graph_unit node_spend_cap 的 W2-C-28 同族语义；u64 源经此恒非负，负帽不可能再入场——即「拒绝负帽」；环内剩余额度本就 cap−spent 且 spent≥0，帽饱和后 i64 域算术无回绕面）。复验：该测试文件 16 passed/0 failed/1 ignored（网络冒烟）；af-execline 全 crate cargo test 23 个套件全 0 failed；clippy -p af-execline --all-targets 0 告警；cargo fmt --check 净
- **载体**：`6293e66`

#### W3-C-24

- **修复**：本分支（phase2-rt-af-execline，已先 git merge phase2-redteam-fixes 同步）经合龙已含 W1 修复序——cli.rs run_submit 现为 resolve_unit(:245)→create_dir_all(:267)→issue_or_load(:274)。亲跑分支二进制复验裁判探针：①submit --unit stub+三件套 → OR1001「互斥」且 state 根零文件（连目录都未建）；②同 order_id 改预算 99 合法重放 → 走过凭证签发后死于引擎定位 EX1002（/tmp 无 Cargo.toml 的快速失败缝），非 OR2003——毒化路径已死。按 fixHint 补回归测试（cli.rs unit_matrix_violation_leaves_zero_residue_and_does_not_poison_budget_replay 三段钉死：非法拒绝零残留/重放无 OR2003/盘上凭证 amount=99），TDD 双证：临时变异回旧主线序（三件块挪到 issue_or_load 后）同测试立红「被拒命令零残留 left:4 right:0」，恢复后 af-order lib 19✓ 全绿。commit 58c7a1e。
- **载体**：`58c7a1e`

#### W3-C-25

- **修复**：落位：worktree af-wt-rt-af-order 已存在，cd 进去先 git merge phase2-redteam-fixes（快进 82185c2→4800a67）同步前波。TDD 先红后绿：先写夹具测试 test-af-order-target-guard.sh（26 断言，两假树+假 target 复刻跨树污染）跑红（FAIL 守卫不存在 exit 1），再实现转绿（26/26 PASS）。三件落地于 crates/af-order/scripts/：①af-order-target-guard.sh——check 扫 deps/*.d 的 CARGO_MANIFEST_DIR env-dep（非当前树根/CARGO_HOME registry/rustc sysroot 即外来逐件点名 exit 1）+守卫章判异树（覆盖无 env-dep 行的库产物）+ensure 判脏即清理重建（等价 cargo clean，/、$HOME、当前树、CARGO_HOME 拒清 exit 2）+record 产 fixHint 要求的三要素验收 JSON（CARGO_MANIFEST_DIR 集合/源码 commit/测试名单）并刷新章；②af-order-test.sh 包装——缺省按工作树派生独立 ~/afbuild-<树名>-af-order（不同工作树强制独立 CARGO_TARGET_DIR=治本），显式 target 透传但运行前 ensure 零容忍清线（切换工作树=清理重建，禁止复用共享测试产物），跑完 record 留档（验收记录防把跨树二进制当当前树证据）；③夹具测试入库。真实场景亲跑验证：本树 check 共享 target 外来 0；主线树 af-wt-phase2-execline check 同一 target（只读）点名 6 处跨树污染（含裁判引用的 exec_contract-54695d40cedb3d21.d→af-wt-rt-af-order）exit 1；主线树 dry-run 派生独立 ~/afbuild-af-wt-phase2-execline-af-order 不碰共享目录；包装实跑 CARGO_TARGET_DIR=~/afbuild-phase2rt-af-order 51 例全绿 exit 0，验收记录落 ~/afbuild-phase2rt-af-order/af-order-evidence/af-order-provenance-20261027T000332Z-2355493.json（worktree_root=af-wt-rt-af-order、commit=907d470…、manifest_dirs 全指向本树、51 条测试名单）。边界如实声明：守卫只护 af-order 域验证路径，九门 ci 层集成留给汇总员（RESULT.md §7 已写明集成点）；全量九门未跑（按指令归汇总员）。
- **载体**：`907d470`, `c90e40e`

#### W3-C-26

- **修复**：RED 探针亲跑复现：真二进制正常 submit 落账后把 state/orders/wo-probe-1/voucher.json 改写为 '{ broken json' 再 submit，stderr 逐字「af-order: OR2003: 凭证/密钥失败: 凭证损坏 /tmp/w3c26-probe/state/orders/wo-probe-1/voucher.json: key must be a string at line 1 column 3」——与 RESULT.md:111 的 OR2005 直接矛盾，裁判映射链亲核一致（voucher.rs:188-193 load_record→OrderError::Voucher→error.rs:24 OR2003；state.rs:100-105 load_ledger→OR2005）。修复：RESULT.md:111 OR2005→OR2003 并保留 :109-110 账本损坏=OR2005 的区分（注明 W3-C-26 勘误）；新增回归锁测试 corrupted_voucher_reports_or2003_not_or2005（tests/cli.rs，真二进制断言 OR2003+凭证损坏+点名 voucher.json 路径+不得出现 OR2005），定向跑 1 passed，防文书与代码再漂移。af-order 全包 cargo test -p af-order 51 例全绿（lib18/cli11/exec_contract13/graph_route4/unit_route5），cargo fmt --check 零 diff、clippy -p af-order --all-targets 0 告警。全量九门未跑（按指令归汇总员）。
- **载体**：`9a262fe`, `c90e40e`

#### W3-C-28

- **修复**：采 fixHint 补内核证据路线：proofs/kani新增mirror_normalize_illegal_goto_e2102_exact_count（含非法编码3的符号域4×4×4、assume至少一非法在场），精确断言E2102计数=非法goto恰现次数（soundness+completeness双向）、E2102在场⇒E2101恒0（抑制规则）、任一违例不产边集；合法域27分配harness原样保留。cargo kani亲跑（Kani 0.68.0/nightly-2026-08-21，step9 9b同款环境）：Complete - 4 successfully verified harnesses, 0 failures, 4 total——E2102半边真实内核证据补齐，B-16的covered口径自此成立（无需降级）。lib.rs:89『由pending模块…覆盖』误记勘误（pending.rs grep实证无route探针）；kani-run.log顶部存W3-C28复跑段4 verified、首跑3 verified历史段保留；C组确定性-对应表covered-fv02-goto-enum块与全库覆盖率段、README-形式验证.md、计划/研究组/形式化/theorems-v1.md B-16工具栏（工作区侧）同步勘误+补证注。9b的32计数断言管INV组镜像，本批在proofs/kani（子集外），run.sh无需随动。
- **载体**：`858da9e`

#### W3-C-29

- **修复**：9b的32/0/32计数断言本支已由W1-C44在位（亲读run.sh确认）；本批补9a定理面对账：新增theorems-manifest.txt正本（21条<文件>\t<定理名>+statements-sha256=57f63938…，即各文件^Theorem起至^Proof.前的陈述块按T01..T10序拼接之SHA-256）+run.sh 9a-2（coqc 10/10后①定理名集合逐位②陈述哈希，漂移即9a FAIL并点名须更新清单；仅改证明体Admitted→Qed不触发；头注登记纪律与9b同款、未纳入step9的证明集继续标覆盖外）。亲验三例：正例21名逐位一致+哈希等；负例①整条删除B20定理（裁判实验二复现）→名集合21→20拦下；负例②删除B20前提edge_in_document行→哈希57f63938→802be420拦下（同改动coqc仍PASS=原判据盲区实证，coqc 8.20.1）。
- **载体**：`a076601`

#### W3-C-31

- **修复**：B-02 从 no-carrier 移入部分载体，五处同步修 C组确定性-对应表.md：§〇结论、§〇全库覆盖率行（部分证据 C-05+B-02、无载体 12→11）、§二新增 B-02 行（⚠️部分档：driver_mirror 两条 harness 断言耗尽收束=on_exhausted，lib.rs:286-292/:297-309，kani-suite-final.log:2664/:2870 两条 VERIFIED-SUCCESSFUL+:10338 pass=17 fail=0 亲验 grep；continue/fail 下游语义与 keep_best 选择函数未建 harness——theorems-v1.md:242 自标 UNCERTAIN 只立弱陈述，不升格全证）、§三.6 叙事勘误句、coverage-check 块（partial: C-05 B-02／no-carrier 11 条）。闭合机算亲验：theorems-v1 抽条目头 16/23/9/9=57，B 组 1..23 恰好分派六桶零重复，40+2+1+3+11=57。commit e802606。
- **载体**：`e802606`

#### W3-C-32

- **修复**：亲核裁定事实后改两处（均为黑灯工厂仓文件）：①AGENT.md:45 枚举「ADR-001~012 全集，含 011/012」→「ADR-001~013 全集，含 011-redteam-w1-fixes / 012-redteam-w2-fixes / 013-af-plan-fold-in」，并附分支限定（013 与 VERSIONS 追认文字当前仅未合流工作树可用、主线 438fa6d 止于 010）；②状态/组件建设状态.md:9 的 ADR-013 两载体指针（docs/VERSIONS.md；docs/adr/013-af-plan-fold-in.md）按 K5 同款限定口径改写——明确「ADR-013 正文与 docs/VERSIONS.md 对应追认文字当前仅在未合流的 phase2-redteam-fixes 工作树 ~/workspace/af-wt-redteam 可用（实测 4800a67 docs/adr/ 含 013、adr/README.md:20 在档），主线 438fa6d 实测 git ls-tree docs/adr 止于 010、VERSIONS.md ADR-013 零命中——待合流后再改为主线指针」。核验命令亲跑：git ls-tree --name-only 438fa6d docs/adr/（001-010+README，无 013）、git show 438fa6d:docs/VERSIONS.md | grep -c ADR-013（0）、af-wt-redteam 两文件 grep（README.md:20、VERSIONS.md:13/:62 均在档）。AGENT.md 与组件建设状态.md 均在黑灯工厂仓（非 git 仓库），无可提交面；本条不涉 af 仓文件，故无 af 仓 commit
- **载体**：—（工作区原地勘误）

#### W3-C-33

- **修复**：亲跑 `https_proxy=http://100.64.0.8:7890 git ls-remote --heads https://github.com/Feasy898/agent-factory-docs`（直连 rc=128 连不上，经 mihomo 代理 per 状态/网络与出口.md:59）→ f5a1b1fcc7167680f83c7bcf33a6586aaba8583f refs/heads/main，与裁判一致；推送链对 wave2-记录.md:54/:113 核对（d4be61e→9c29b33→553e580→3ed1576→f5a1b1f）。三处状态入口回写：README.md:31、计划/00-总纲.md:21、状态/组件建设状态.md:12 均补「远端 main=f5a1b1f（2026-10-27 ls-remote 实核，完整推送链）——9c29b33 系中间提交/其中一笔内容增量，非最新备份状态」。
- **载体**：—（工作区原地勘误）

#### W3-C-34

- **修复**：judge.rs 三件修复（fixHint 的 PYTHONPYCACHEPREFIX+/-B/导入链锚三取其三，非再加包装哈希）：①JudgeLocator 增 import_chain 信任锚（ImportAnchor×6=swev-judge.py from-import 实际解析到的 swebench 六件 .py 源：包链 __init__×2+grading.py+constants/__init__.py+test_spec/__init__.py+test_spec.py，sha256 亲测入锚，check_fingerprint 同门 EX3002 fail-loud——改一字节/缺席即拒）；②invoke 子进程统一 -B+PYTHONDONTWRITEBYTECODE=1（禁写含嵌套 python）；③受控全新空 PYTHONPYCACHEPREFIX（读取侧重定向，site-packages 4913 枚在场影子 pyc 整体不可达=纯源执行；缓存目录留 tripwire，真实判分 3 目录实测 0 pyc）。TDD：测试先行红（ImportAnchor 缺位编译红）→绿 5✓，变异（去 -B/env）契约测试立红；真 venv 端到端 --ignored fixture 亲跑 8.99s 过（六锚逐位对机+astropy resolved 随日志翻转）；受影响七套件全绿（p3_verify 7/p4_unit 10/p5_wiring 4/p6_shadow 8/pkg_sweng 37/graph_unit 37/p3_judge 5）。K5 门纪：scorechain-manifest judge.rs 锚换版登记（1e43d658…→da945f50…，裁决出处=W3-C-34），k5-path-lint.py 亲跑 PASS 4 件逐位对锚；clippy/fmt 净。commit 813b315。
- **载体**：`813b315`

#### W3-C-35

- **修复**：ci/neutrality-wordlist.txt:76黑名单词reflectkit→reflexkit（理由列注明W3-C-35勘误+词形错位史），头注两处历史记载以勘误注保留原词形；neutrality_scan.py --self-test增包段词形一致性回归（reflexkit在表+pattern命中pkg.reflexkit.search）；RESULT-G4-收尾.md词表再生成段随勘误同步。亲验闭环：①修复前复现（blacklist含reflectkit/不含reflexkit、findall('pkg.reflexkit.search')=[]、对照组pkg.reactkit.hopqa双命中）；②src放含pkg.reflexkit.search探针→scan exit=1命中[词]reflexkit、清理后exit=0（检测能力端到端恢复）；③step8门复跑S1 PASS（18豁免/0白名单外/0漂移）。随批修两处本批引入面：shape.rs注释去ADAS/SWE黑名单词、白名单terminal条目行号699→710随lower.rs登记块插入漂移修正（同条目587→699修正先例）。
- **载体**：`f3d9296`

#### W3-C-38

- **修复**：neutrality_gate.sh按fixHint双面修复：①parse_keys→parse_log——段头补Doc-tests <crate>（原section残留上一值）、键推导补doc-test行形test <文件> - <名>(line N) … ok|FAILED（键=crate::doctest::<文件>::<名>，去行号防漂移）、ignored显式归类不进集合、其余未知结局计未归类；②新判据R8 fail-loud——原始FAILED行数=解析失败键数=cargo汇总失败数三方相等且未归类行=0，任一破裂门红（头注判据清单/汇总行/方案§1.4表同步R8）。亲验四例：实日志af-dsl解析=汇总=2未归类0（23项名单面不变）；合成doc-test FAILED→键入失败集；实日志副本注入doc-test FAILED→失败键2→3（修复前同注入=0键即裁判实测盲区）；未知结局行(BENCHED)→unclassified=1→R8红路径可触发。step8全门复跑exit 0：13判据全绿含R8首跑PASS（23=23=23、未归类0）。
- **载体**：`967ee5d`, `9e8008a`

#### W3-C-40

- **修复**：按 fixHint 未做 3117→3191 机械替换，先亲跑口径核数：`git -C af ls-tree -r --name-only <c> | grep -c` 八个 commit（438fa6d/a050378/94cd192/aff4f1a/1786623/ec231e3/4d427ed/8aecd84）→ /target/=3191 全同；四目录（target+ci/out+poc-cas-rust/out+poc-dspy/verify-adapter/out）扫描时点提交=3236（ci/out 当期 14；438fa6d 时点 ci/out=28 故 3250）。勘误按口径分列：DSL-G0-必要性报告.md:37 注「3117 系密钥终扫:57 命中表四目录命中数（3072+14+17+14）误作总量，本行清理口径应为 target 单目录 3,191」；密钥终扫-20261024.md:105 注命中数 3117 与 git 全量 3,191（target）/3,236（四目录）分列，均链 30-遗产处置.md:77 实际清理记录（W2-C-04，3,191 blob 出索引）。:57 命中表本体未动（命中数口径正确）。
- **载体**：—（工作区原地勘误）

#### W3-C-41

- **修复**：退役执行记录-20261026.md:56 #7③：引文尾「唯一变量=修复本身」删除，保留 CH 0→3 与 release/start/complete 字段对账证据，改为引用来源 L73 W2-C-13 勘误后的正确口径「同任务同门控形态、不同预算/调用参数的修复前后对照」，并列两单混淆变量实证（F3a2 turns=2/unit_calls=2/3 bash effect vs F4a3 turns=0/unit_calls=0/零 effect）；F-第四单-交付-20261025.md:5 文首同措辞残留清理（同口径+指向 §2 勘误）。:73 原 W2-C-13 勘误书未动（撤回出处）。
- **载体**：—（工作区原地勘误）

#### W3-C-42

- **修复**：亲跑机算复核（aff4f1a 五份 components.json 经 git show 全量遍历、剔除 P2-L11 首批 7 件）：all=57/new=50、class={model_route:5,tool:28,unit:13,memory:4}、28 tool effect_class=external_once 14/persist 8/pure 6，与裁判一致；并实证文书自不闭合（external_once 枚举 13 项漏 pkg.autogen.tool.search≠表头 12、pure 枚举 6≠表头 8）。G3-全链闸门-L1L4-v2-20261024.md:78-83 改为 14/8/6 且枚举与表头改齐（+autogen.tool.search）+勘误注。fixHint 之 registry_decl_test 断言：该测试件位于 af 仓工作树（/home/pan-ding/workspace/af-wt-*/crates/af-compiler/tests/registry_decl_test.rs）——本域指令「不碰 af 仓」，未改；以工作区侧等价防线代之：TDD 新建 tools/registry-effect-class-audit.py（RED=FileNotFoundError→实现→5/5 GREEN；集成跑 `--rev aff4f1a` exit 0 三类数量断言全过），文书勘误注已注明该复核件。
- **载体**：—（工作区原地勘误+审计件）

#### W3-C-43

- **修复**：亲核 wave2-记录.md:32-35 终局（候选 56=首轮 58 并案/增补后；real 50/overturn 0/not 5/handled 1；50/50 修复，43 直修+7 域外交接合龙批闭环）与 :369-372 轮次沿革；按 append-only 纪律保留变更日志原 04:4x 首轮快照条原貌，在表格顶部（最新在上）新增 2026-10-27 07:5x 终局补登条：56 候选、50 real、overturn 0、not 5、handled 1、50/50 修复、五域 --no-ff 合入（8cbd79b/1dc8fc9/e312277/76ccdd5/4ed9c04）+九门收口终跑全绿，证据链 wave2-记录.md:32-35/:369-372/§四 终局表。修复后 grep「50 real-defect/56 候选」终局口径已在运营者入口在案。注：工作区非 git 仓（git rev-parse fatal 实证），全部为原地文书/脚本修改，无 commits 可载。
- **载体**：—（工作区原地勘误）

## 五、附记：全域合龙批（2026-10-27）

- **五域分支按序 --no-ff 合入 phase2-redteam-fixes**（af-dsl→misc→af-execline→af-compiler→af-order）：合并提交 911209c/904b3a7/8a00bba/e8f1bbf/1526768；af-execline 域 C组确定性-对应表一处冲突按语义合（红队修复优先）——HEAD 侧 W3-C28 的 B-16 E2102 半边补证（非法编码域探针 4 verified）保留、来方 W3-C31 的 B-02 三值透传弱陈述面自 no-carrier 移入 partial，闭合机算亲验 40 covered（含 B-16）+2 partial（C-05/B-02）+1 admitted（B-20）+3 blocked+11 no-carrier=57、类间无交、并集=全集。
- **K5 判分链锚两笔换版带裁决登记合流**：judge.rs（1e43d658…→da945f50…，W3-C-34 判分面真值入锚：导入链六件 .py 源逐件 sha256 门+子进程 -B/PYTHONDONTWRITEBYTECODE/受控空 PYTHONPYCACHEPREFIX 三道执行面防线）与 rubric_unit.py（2e8ca98f…→e8b67eb6…，W3-C-06 防再生不变量）——k5-path-lint.py 复跑 PASS（4 件逐位对锚）。
- **终局硬线**：全域合龙批终跑 `CARGO_TARGET_DIR=~/afbuild-phase2rt bash ci/run.sh` exit 0——step1-8 全 PASS（step8 中立性门 13 判据全过：C1 对照臂 exit=0、I1/I2/I3 红名单 23 项集合精确相等、R8 解析对账 PASS「原始 FAILED 行=解析键=cargo 汇总=23、未归类=0」、S1 词表 reflexkit 勘误后 18 豁免/0 白名单外/0 漂移、R7 闭集 OK、Z0 沙箱只读）+ step9 ADVISORY-PASS（9a Rocq 10/10 + 9a-2 定理清单对账 21 条定理名逐位一致+陈述块 SHA-256 一致 57f6393869e9…、9b Kani 32 verified/0 failures）；证据入档 239f16a。W3 批 32 条修复在此终态树上全部在位。
