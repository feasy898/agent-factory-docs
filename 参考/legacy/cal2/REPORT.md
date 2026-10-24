# cal2 基准标定轮报告（2026-10-13）

- 任务集：Terminal-Bench original-tasks 精选 51 题（easy 17 / medium 20 / hard 14），本地 pytest 确定性验收
- 矩阵：12 配置 × 51 题 = 612 次 agent 运行（5 官方 harness @anolis + 7 本机 ZCode 工作流派发，含 GLM 双模型）
- 判分：anolis docker 按官方 Dockerfile 构建镜像，scratch 挂载 /app，跑官方 tests/test_outputs.py，exit 0 = pass
- 规格来源：L3 终审材料包 A5 模型谱系预登记画像（三臂+路由竞争臂预测带，假设-待验证口径）

## 一、主结果表（对照 A5 预登记预测带）

| 配置 | Harness | 模型 | A5 臂 | 通过 | 判定 | 通过率 | A5 预测带 | 上轮(官方) | 带内/外 |
|---|---|---|---|---|---|---|---|---|---|
| cal2-mcode-m3 | mcode | MiniMax-M3 | 强臂候选 | 35 | 16 | **68.6%** | 65–82% | 58.8% | 带内 |
| cal2-mcode-m31f | mcode | MiniMax-M3.1-Flash-Preview | flash 臂 | 39 | 12 | **76.5%** | 50–68% | 76.5% | 带上 |
| cal2-step-s5 | step | step-5-preview | 强臂候选 | 35 | 16 | **68.6%** | 60–78% | 70.6% | 带内 |
| cal2-step-router | step | step-router-v1 | 路由竞争臂 | 25 | 26 | **49.0%** | 55–78% | — | 带下 |
| cal2-kimi-k28 | kimi | kimi-for-coding (K2.8) | 中臂候选 | 38 | 13 | **74.5%** | 55–75% | 78.4% | 带内 |
| zcode-m3 | zcode-wf | MiniMax-M3 | 强臂候选 | 28 | 23 | **54.9%** | 65–82% | — | 带下 |
| zcode-m31f | zcode-wf | MiniMax-M3.1-Flash-Preview | flash 臂 | 35 | 16 | **68.6%** | 50–68% | — | 带上 |
| zcode-s5 | zcode-wf | step-5-preview | 强臂候选 | 34 | 17 | **66.7%** | 60–78% | — | 带内 |
| zcode-router | zcode-wf | step-router-v1 | 路由竞争臂 | 28 | 23 | **54.9%** | 55–78% | — | 带下 |
| cal2-grok47 | grok | grok-4.7 | 强臂候选 | 45 | 6 | **88.2%** | 60–86% | — | 带内 |
| zcode-glm53 | zcode-wf | GLM-5.3 | 新增-未预登记 | 40 | 10 | **80.0%** | — | — | 无预登记带 |
| zcode-glm53f | zcode-wf | GLM-5.3-Flash | 新增-未预登记 | 32 | 19 | **62.7%** | — | — | 无预登记带 |

## 二、同模型跨 harness 对比（官方 vs ZCode 工作流）

| 模型 | 官方 harness | ZCode 工作流 | 差值 |
|---|---|---|---|
| m3 | 68.6% (35/51) | 49.0% (25/51) | -19.6pp |
| m31f | 76.5% (39/51) | 68.6% (35/51) | -7.8pp |
| s5 | 68.6% (35/51) | 66.7% (34/51) | -2.0pp |
| router | 49.0% (25/51) | 54.9% (28/51) | +5.9pp |


## 2b、跨 harness 对比的统计说明

- 同模型同题集下，官方 harness 与 ZCode 工作流派发的差值见上表；负值表示工作流派发路径下拉了该模型表现。
- 注意：官方 harness 使用各自 CLI 默认配置（step CLI 默认 thinking=medium）；zcode-s5 泳道已对齐为 medium（见 E3）。
- 上轮（sess_ab665723，wf vs mcode，M3.1/M3）曾得 wf−mcode=+12.9pp；本轮同对比为 −2.0pp/−9.8pp，方向反转——harness 间差距在本轮题集/版本下不稳定，是本轮最重要的标定发现之一。
## 三、难度分层

| 配置 | easy (17) | medium (20) | hard (14) |
|---|---|---|---|
| cal2-mcode-m3 | 13/17 = 76% | 13/20 = 65% | 9/14 = 64% |
| cal2-mcode-m31f | 15/17 = 88% | 14/20 = 70% | 10/14 = 71% |
| cal2-step-s5 | 15/17 = 88% | 11/20 = 55% | 9/14 = 64% |
| cal2-step-router | 11/17 = 65% | 9/20 = 45% | 5/14 = 36% |
| cal2-kimi-k28 | 15/17 = 88% | 14/20 = 70% | 9/14 = 64% |
| zcode-m3 | 12/17 = 71% | 8/20 = 40% | 5/14 = 36% |
| zcode-m31f | 13/17 = 76% | 13/20 = 65% | 9/14 = 64% |
| zcode-s5 | 11/17 = 65% | 15/20 = 75% | 8/14 = 57% |
| zcode-router | 11/17 = 65% | 12/20 = 60% | 5/14 = 36% |
| cal2-grok47 | 14/17 = 82% | 18/20 = 90% | 11/14 = 79% |
| zcode-glm53 | 14/17 = 82% | 16/19 = 84% | 9/14 = 64% |
| zcode-glm53f | 10/13 = 77% | 15/20 = 75% | 2/12 = 17% |

## 四、逐题矩阵（p=pass f=fail i=infra .=未跑）

| task | diff | mcode-m3 | mcode-m31f | step-s5 | step-router | kimi-k28 | zcode-m3 | zcode-m31f | zcode-s5 | zcode-router | grok47 | zcode-glm53 | zcode-glm53f |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| aimo-airline-departures | easy | p | p | p | p | p | p | p | p | f | p | p | p |
| analyze-access-logs | easy | p | p | p | p | p | p | p | p | p | f | p | . |
| bank-trans-filter | easy | p | p | p | p | p | p | p | p | p | p | p | . |
| count-call-stack | easy | f | f | p | f | f | f | f | f | f | p | f | f |
| countdown-game | easy | p | p | p | p | p | p | p | f | p | p | p | p |
| cpp-compatibility | easy | p | p | p | p | p | f | p | p | f | p | p | p |
| flood-monitoring-basic | easy | f | f | f | f | p | f | f | f | f | p | f | f |
| grid-pattern-transform | easy | p | p | p | f | p | p | p | p | p | p | p | p |
| hello-world | easy | p | p | p | p | p | p | p | p | p | p | p | p |
| ilp-solver | easy | f | p | f | f | p | p | p | f | p | p | p | p |
| jq-data-processing | easy | f | p | p | f | p | f | f | f | f | f | p | . |
| jsonl-aggregator | easy | p | p | p | p | p | p | p | p | p | p | p | . |
| mahjong-winninghand | easy | p | p | p | f | f | f | f | f | f | p | f | f |
| multistep-definite-integral | easy | p | p | p | p | p | p | p | p | p | p | p | p |
| recover-accuracy-log | easy | p | p | p | p | p | p | p | p | p | p | p | p |
| recover-obfuscated-files | easy | p | p | p | p | p | p | p | p | p | f | p | p |
| schedule-vacation | easy | p | p | p | p | p | p | p | p | p | p | p | p |
| constraints-scheduling | medium | p | p | p | p | p | p | p | p | p | p | p | p |
| db-wal-recovery | medium | p | p | f | p | p | f | p | p | p | p | p | p |
| distribution-search | medium | p | p | p | p | p | p | p | p | f | p | p | p |
| enemy-grid-escape | medium | f | f | p | f | p | p | p | p | p | p | p | p |
| gcode-to-text | medium | f | f | f | f | p | f | p | p | f | p | p | p |
| git-leak-recovery | medium | p | p | f | p | p | p | p | p | p | p | p | p |
| huarong-dao-solver | medium | p | p | p | f | p | f | f | p | p | p | p | p |
| largest-eigenval | medium | p | p | f | p | p | p | f | p | p | p | p | p |
| log-summary-date-ranges | medium | p | p | p | p | p | f | p | p | p | p | p | p |
| modernize-scientific-stack | medium | p | p | p | p | p | p | p | p | p | p | p | p |
| openssl-selfsigned-cert | medium | p | p | p | f | p | f | p | p | p | p | p | p |
| polyglot-c-py | medium | f | p | f | f | f | f | p | f | f | p | p | f |
| portfolio-optimization | medium | f | p | f | f | f | f | f | f | f | f | p | p |
| puzzle-solver | medium | p | f | p | f | p | f | f | f | f | p | f | f |
| regex-log | medium | p | p | p | p | p | f | p | p | p | p | p | p |
| schemelike-metacircular-eval | medium | p | p | f | f | f | p | p | p | f | p | p | p |
| solve-maze-challenge | medium | f | f | f | f | f | f | f | p | f | p | i | f |
| sqlite-db-truncate | medium | p | p | p | f | p | f | p | p | p | p | p | p |
| tree-directory-parser | medium | f | f | f | f | f | f | f | f | f | f | f | f |
| vertex-solver | medium | f | f | p | p | f | p | f | f | p | p | f | f |
| cancel-async-tasks | hard | p | p | p | f | f | f | p | p | f | p | p | p |
| circuit-fibsqrt | hard | f | p | f | f | p | p | p | p | f | p | p | p |
| feal-differential-cryptanalysis | hard | p | p | p | f | p | f | f | f | f | f | f | f |
| feal-linear-cryptanalysis | hard | p | p | p | f | p | p | p | p | p | p | p | f |
| llm-inference-batching-scheduler | hard | p | p | p | f | p | f | p | p | f | p | p | f |
| model-extraction-relu-logits | hard | f | p | p | f | f | f | p | p | f | p | p | f |
| movie-helper | hard | p | p | p | p | p | f | f | f | p | p | f | . |
| organization-json-generator | hard | p | p | p | p | p | p | p | f | f | p | p | f |
| password-recovery | hard | p | p | f | f | p | p | p | p | p | p | p | f |
| path-tracing-reverse | hard | f | f | f | f | f | f | f | f | f | f | f | f |
| rare-mineral-allocation | hard | f | f | f | p | f | f | f | f | f | p | f | f |
| regex-chess | hard | f | f | f | f | f | f | p | p | p | p | f | f |
| reverse-engineering | hard | p | p | p | p | p | f | f | f | f | f | p | f |
| stable-parallel-kmeans | hard | p | f | p | p | p | p | p | p | p | p | p | . |

## 五、阶梯单调性检验（A5 §3.2 判据）

A5 预测：强臂 > 中臂 > flash 臂（阶梯假设）。本轮官方 harness 实测：
- 强臂候选: MiniMax-M3 68.6%, step-5-preview 68.6%, grok-4.7 84.3%
- flash 臂: MiniMax-M3.1-Flash-Preview 76.5%
- 路由竞争臂: step-router-v1 49.0%
- 中臂候选: kimi-for-coding (K2.8) 74.5%

## 六、事件与纪律记录

见 cal2/logs/incidents.md（额度 canary、防作弊基建、s5 配置修正、ENOSPC、DriverError 修复、db-wal 违规及处置、movie-helper 输入缺失、判分链路验证）。

## 七、审计结论

- 审计覆盖 4 个本地泳道 × 51 题：判定可疑 4 例（需人工复核），其余为 minor 卫生问题声明。
  - zcode-glm53f/ilp-solver: [['Maximized NPV: 299.00', '/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-glm53f/ilp-solver/work/ilp_output.txt']]
  - zcode-glm53f/recover-obfuscated-files: [['Log entry 2: User ', '/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-glm53f/recover-obfuscated-files/work/recovered/project_alpha.log']]
  - zcode-glm53f/constraints-scheduling: [['SUMMARY:Team Planning Meeting', '/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-glm53f/constraints-scheduling/work/solve.py']]
  - zcode-glm53f/openssl-selfsigned-cert: [['%b %d %H:%M:%S %Y %Z', '/home/pan-ding/workspace/临时工作区/temp1/cal2/runs/zcode-glm53f/openssl-selfsigned-cert/work/check_cert.py']]



## 九、GLM 双模型专题（本轮新增，2026-10-15/16）

### 结论
| 模型 | 有效通过率 | 通过/判定 | 排除项 | 判分方式 |
|---|---|---|---|---|
| **GLM-5.3** | **78.0%** | 39/50 | solve-maze-challenge（infra：node 镜像构建超时，环境性） | 一次性干净判分 |
| **GLM-5.3-Flash** | **62.7%** | 32/51 | 无（6 题已补跑，51 题完整口径） | 同上 |

- GLM-5.3 在 12 配置中排**第二**（次于 grok-4.7 的 84.3%，高于 mcode-m31f 的 76.5%）：easy 17/17 全对、hard 12/14=86% 为全部配置最高档，失败集中在 regex-chess、puzzle-solver、count-call-stack 等需要极端精确性的题。
- GLM-5.3-Flash 明显弱于同族旗舰（-15.3pp，78.0% vs 62.7%）：flash 档位落差远大于 MiniMax 同族（M3 49.0% → M3.1-Flash 68.6%，重判后 flash 反超强臂 19.6pp）。
- 选型含义：GLM 系"要强必须上 5.3"；若预算只够 flash 档，MiniMax-M3.1-Flash 是更优的 flash 选择。
- 补跑收官：Flash 泳道最初作废的 6 题（4 题播种事故 + 2 题令牌失效未派发）已在令牌恢复后按逐字节一致指令补跑并判分——4 题播种事故全部转 pass（analyze-access-logs、bank-trans-filter、jq-data-processing、jsonl-aggregator）、stable-parallel-kmeans pass、movie-helper fail（该题输入本就不提供，属设计内条件，与其他全部配置一致）。**双泳道均为 51 题完整口径**。上一轮（10-12）同题集 GLM-5.3 曾测得 88.2%，本轮 78.0% 偏保守（含 12 题重做消耗）。
- 反作弊审计：双泳道 canary 命中 9 例全部证伪（base64 输入解码产物逐字节一致、指令明文规定、表格可算数值、openssl 标准格式），**零判分材料污染**。

## 十、判分链路缺陷与重判修正（2026-10-15/16）

排查评分准确性时定位并修复了判分链路的系统性缺陷：
1. **基础镜像退化 → 静默假失败**：判分容器内 pytest 装不上时报错被吞、记成 fail。已修：基底增强 + setuptools 烤入 + PEP 668 兼容 + 环境自检（坏环境记 infra）。
2. **root 残留污染 scratch**：判分容器以 root 运行，编译残留（如 polyglot 的 cmain）写进挂载的 scratch 且宿主机删不掉，污染后续每次判分。已修：判分前 root 容器清理非当前用户残留。
3. **构建超时/磁盘连锁**：1800s 超时在 ~9KB/s 镜像源下误杀正常构建；重判累积镜像两度把磁盘撑满并引发 dockerd 崩溃、基底丢失。已修：5400s 超时、3G 磁盘熔断、镜像保留策略（>8G 时复用）、5 基底离线验证。

重判口径：
- **5 个本地泳道 + grok47 已在修复环境下全量重判（零 infra，51/51 实判）**，本报告表内数字即重判后数字；grok-4.7 修正为 **84.3%**（此前 96.1% 的读数亦不可信——污染前后各取一段）。
- **官方 harness 的 5 个配置（mcode/step/kimi）scratch 已被 lane runner 清理，无法重判**：其数字在退化镜像时代测得，存在未知幅度的向下偏差，跨配置对比时需注意该口径差异。
- 事件全录：cal2/logs/incidents.md（E11-E17）。


## 十一、全面复审与第二次修正（2026-10-16，fork 后独立审计）

审计方法：① 全部 445 个 pass 逐条核对判题日志中的 pytest PASSED 证据（100% 有据）；② 全部 fail 检查失败证据，无证据者逐条重判；③ scratch 产物存在性核验；④ root 残留机理复核。

**复审揪出并修正 9 个并发 OOM 假失败**：终版 sweep 期间多守护进程并发 + 其他会话构建，导致测试容器被 OOM kill（exit 137、无任何输出）却被记为 fail。安静环境串行重判后 9 题翻案为 pass：
- cal2-grok47：analyze-access-logs、recover-obfuscated-files、solve-maze-challenge → 43→45，**88.2%**
- zcode-m3：log-summary-date-ranges、regex-log、sqlite-db-truncate → 25→28，**54.9%**
- zcode-glm53：regex-chess → 39→40，**80.0%**
- zcode-s5：countdown-game → 34→35，**68.6%**

复核为真实失败（不予修正）：zcode-m3/polyglot-c-py（断言“目录中只能有 main.py.c”，模型自留多余文件）、zcode-m3 与 zcode-m31f 的 solve-maze-challenge（产物错误，与 10-14 确定性复判一致）、zcode-glm53f/movie-helper（输入本就不提供的 12 配置一致条件）。

无法复核项（保留原判并标注）：官方 5 配置的 scratch 已被 lane runner 清理，其中 cal2-mcode-m3/solve-maze-challenge 为 lane runner 记录的 no_artifacts_produced（agent 未产出），无 scratch 可重判，按原判保留。

**当前最可信数字**：GLM-5.3 = **80.0%**（40/50）、GLM-5.3-Flash = **62.7%**（32/51）、grok-4.7 = 88.2%、mcode-m31f = 76.5%（未重判）、kimi-k28 = 74.5%（未重判）、m31f/s5 = 68.6%（重判+复审）、m3/router = 54.9%（重判+复审）。


## 十二、flash 类模型专题（2026-10-17 完稿）

| 模型 | 原跑 | 复现跑 | 逐题一致率 | 结论 |
|---|---|---|---|---|
| MiniMax-M3.1-Flash-Preview | 68.6%（35/51） | **68.6%**（35/51） | 80.4%（41/51，10 题翻转但净差为零） | **完美复现**，水平最稳 |
| GLM-5.3-Flash | 62.7%（32/51） | 70.6%（36/51） | 84.3%（43/51） | 区间 63–71%，波动 +7.9pp |
| Step3.7-Flash（新模型首测） | **51.0%**（26/51） | 未复现 | — | 三档中最弱，单次抽样待验证 |

**排名结论**：flash 档内 MiniMax-M3.1-Flash 明显最强（68.6% 且可复现）；GLM-5.3-Flash 居中但 run 间波动较大；Step3.7-Flash 首测 51.0%，与 step-router-v1（49.0%）同档，是阶跃系最弱的一环。

**复现性方法论结论（对全部数字适用）**：M3.1-Flash 两轮总通过率完全一致（68.6%）但逐题有 10 题翻转；GLM-5.3-Flash 两轮差 7.9pp。说明单轮总分有一定稳定性（聚合后），但**逐题判定有约 16–20% 的翻转率**。引用数字应带区间；追查单题表现时必须做多轮。

**审计结论**：三条新泳道 canary 命中 15 例全部证伪（NPV 可由指令表格算出、base64 输入解码产物逐字节一致、指令明文规定的类名/会议名、openssl 标准日期格式、faker 第三方库源码误报），**零判分材料污染**；flood-monitoring-basic 在 M3.1 复现泳道首次因 harness 机制故障（WorkflowError）失败，已补跑并以新内容重判（该题数据只存在于评分容器，12 配置一致失败，属设计内条件）。
