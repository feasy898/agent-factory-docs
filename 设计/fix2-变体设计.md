# 设计 · fix2 变体设计（S1 研究循环第一个 harness 变体）

> **结果代号：fix1 → fix2**（§9.3 结果版本隔离）。af main = 794fcaa + bfad8f3（两批，CI 七门全绿）。
> 日期：2026-10-20。输入：kimi code 研究、codex/claude code 研究（运营者会话子代理报告）、
> [harness差异解剖](harness差异解剖.md)（研究③）、[harness-对齐审计](harness-对齐审计.md)（研究①）、
> [失败轨迹分析](失败轨迹分析.md)（研究②）。**参数类改动以研究①为唯一裁决源（§9.7 对齐纪律），本文件不自设参数。**

---

## 0. TL;DR

fix2 = **协议修复（研究③ B1-B6）+ 参数对齐（研究① §6.A）+ 轨迹机制（研究② 建议1/2/3/5）**。
判分链语义未动（红线）；k=1 保持；不动的：TB 线参数（审计 §6.C 为建议级）、命令超时 180s/截断 12KB（审计 D10 判"基本对齐，中性"）。

---

## 1. 借鉴清单（来源 × 去处 × 失败模式 × 语义标记）

| # | 改动 | 来源 | 对应失败模式（S0 D 类 / S1 轨迹类） | 语义变更 |
|---|---|---|---|---|
| C1 | 完成判定改"工具输出首行=信号词"（提交式完成，叙述提及不再触发） | 研究③ B1（mini has_finished）；kimi/codex 研究（提交动态与硬协议佐证） | S0 D1 零补丁完成、D3 早停；S1：误触发风险路径 | **是（fix2 主变更）** |
| C2 | system 缩为一行角色；纪律/工作流/提交协议改 instance 模板随每题重发；含测试先行引导与 Core Judgment 两句 | 研究③ B4/B5（mini instance_template + mcode Core Judgment） | S0 D2 越权改测试、D6 交付物缺失、长对话遗忘 | **是** |
| C3 | 无工具轮教学反馈（第一轮即纠偏，不再静默数满 tool_free 倒计时） | 研究③ B3②（mini FormatError 教学）；codex 研究（loop 管控） | S0 D3；S1 摩擦点 1 | **是** |
| C4 | finish_reason=length/max_tokens 截断专项反馈 + **空轮不计 tool_free 计数** | 研究③ B8；**研究② 建议2**（61 空轮、m31f-14096 被误杀实证） | S1 摩擦点 3、机制性误杀 | **是** |
| C5 | 超时/桥接失败带内教学反馈（不死文案）；exit=N 移至输出末行（首行让位完成判定）；修字面 `\n` 疵点；截断附换窄命令指引 | 研究③ B3①/B6（mini timeout_template + observation_template） | S1 摩擦点 8；有效步数缩水 | **是** |
| C6 | 容器环境变量卫生（PAGER=cat 等 6 项，TB/SWE-V 两 setup 同步） | 研究③ B6（mini env 块） | 分页器挂死/进度条噪音暗坑 | **是** |
| C7 | bash 工具描述补防错条款（新 shell/非交互/超时/exit 行位置） | mcode 研究（工具描述即防错）；差异解剖 §1.1 | S0 零补丁嫌疑（目录矛盾类） | **是** |
| C8 | 收尾机制：剩 ~10% 轮 gentle、剩 ~4% 轮 strong 轮次预算提醒（各恰一次） | **研究② 建议1**（19/60 max_turns 例补丁已过判分仍在验证） | S1 B1 类 19 例、摩擦点 1 | **是** |
| C9 | 反考古护栏：git 考古/全盘搜索模式命中即注入护栏 | **研究② 建议5**（51/145 run、单例烧 10-20 轮） | S1 D-考古类 | **是** |
| C10 | instance 两条禁令：不写 changelog/docs；无网不重试下载 | **研究② 建议3**（73/145 run 文档吸附、59 run 无网试探） | S1 摩擦点 2/5 | **是** |
| P1 | max_turns 60 → 250 | **研究① §6.A.1**（D1 主因：60=标准 24%） | S1 max_turns 86 行 | **是（参数对齐）** |
| P2 | 成本上限 $1 → $3 | **研究① §6.A.2**（D2） | budget_exhausted 长题 | **是（参数对齐）** |
| P3 | temperature 0.0 / top_p 1.0 显式 | **研究① §6.A.4**（D6：复现性，cal2 逐题翻转 16-20%） | 方差与格式失败率 | **是（参数对齐）** |
| P4 | max_tokens 8192 → 显式 32000 | **研究① §6.A.3**（D3；Vals"highest possible"；GLM-5.2 卡片 64000 取保守档） | S1 47 轮 finish=max_tokens | **是（参数对齐）** |
| P5 | 去 hints_text 注入 | **研究① D4/§6.A.5**（反向虚高：标准只给 problem_statement） | 榜单可比性 | **是（对齐）** |
| P6 | 关 gate 反馈重试（attempt 恒 1；gate 只记账） | **研究① D5/§6.A.6**（反向虚高：免费 repair 轮） | pass@1 口径纯化 | **是（对齐）** |
| P7 | eval 超时 1200 → 1800s | **研究① D9/§6.A.8**（慢测试误杀） | 判分假阴性风险面 | **是（对齐）** |
| N1 | 结果行 scaffold v2 → v3 + reasoning_tier 声明（保持 Off） | 研究① §6.A.7（档位必须声明；Off = mini 默认） | 口径自述 | 记录字段 |
| N2 | TB 套件系统提示同步提交式完成协议 | C1 的必然联动（harness 语义变了，提示不跟则 TB 全灭） | — | **是（TB）** |

**评估学留待拍板（未实施）**：测试靶点泄漏档位（研究② 建议6，a/b/c 三档需运营者决策）；预存失败 oracle（建议7，需容器预跑基线设计，留 fix3）；TB 线 max_turns≥200/温度 0.7（审计 §6.C 建议级）；上下文压缩（研究③ B7，250 轮 + 12KB 截断下是否撞窗留 S2 观测）。

## 2. 实施位置

- af-harness `src/run.rs`：C1（settle_turn/matched_signal）、C3/C4（one_turn 注入与计数豁免）、C8（one_turn 收尾提醒，`turn_reminder_threshold`）
- af-harness `src/spec.rs`：StopCondition 语义文档；`src/tests.rs`：48 测试（+4 新增：叙述提及不完成、教学注入计数、截断空轮不计数、收尾提醒恰一次）
- af-bench `src/main.rs`：C2/C10（SWEV_INSTANCE_PROTOCOL）、C9（ARCHAEOLOGY_PATTERNS + bash 闭包）、N1（结果行）、P1-P6（run_swev 参数对齐 + gate 只记账）
- af-bench `src/swev.rs`：P5（prompt 去 hints）、P7（eval 1800s）、C6（env 卫生）
- af-bench `src/tb.rs`：C5（exec 重写 + split_rc）、C6（env 卫生）、C7（bash_tool_decl）、N2（TB 提示）

## 3. 对照重跑协议（只备不发，工厂切换由厂长调度）

**题集（fix1 max_turns 失败题，5 档案 × 4 题 = 20 run，8 道唯一题）**——选取规则：优先 reward=false、优先跨 profile 公共题（同题多档案对照 Δ 最干净）、每档案含 1 道 profile 特有题：

| 档案（--profile） | 题集（--tasks） |
|---|---|
| glm-cp | astropy__astropy-13398, astropy__astropy-13977, astropy__astropy-14369, django__django-10554 |
| glm-cp-max | 同 glm-cp 四题 |
| mavis-m31f | astropy__astropy-13398, astropy__astropy-13977, django__django-10554, django__django-10097 |
| step-5 | astropy__astropy-13398, astropy__astropy-13977, django__django-10554, astropy__astropy-13033 |
| mavis-m3 | astropy__astropy-13398, django__django-10554, django__django-10999, astropy__astropy-14182 |

依据（fix1 快照）：13398/13977/14369/10554 在 ≥4 个档案同为 max_turns 且 reward=false；10097/13033/10999/14182 为对应档案的特有 max_turns 失败。任务包已在 /tmp/swev-s1/（8/8 在）。

**怎么跑（逐档案一条命令；先构建 fix2 二进制）**：

```bash
cd /home/pan-ding/workspace/agent黑灯工厂/af && git pull && cargo build -p af-bench
P=glm-cp; T=astropy__astropy-13398,astropy__astropy-13977,astropy__astropy-14369,django__django-10554
./target/debug/af-bench --suite swe-v --data-root /tmp/swev-s1 --tasks "$T" \
  --profile "$P" --out /tmp/bench-fix2-rerun-$P --host anolis
# P 依次换：glm-cp-max / mavis-m31f / step-5 / mavis-m3（m3 的 T 同 m31f 中其 4 题）
```

**纪律**：
1. 结果目录 `/tmp/bench-fix2-rerun-<profile>/`——**独立目录，绝不与 fix1 各 tier 目录共写**（§9.3 代号隔离）；
2. GLM 并发纪律（§9.6）：glm-cp / glm-cp-max 两档案错峰跑（账户并发上限 ~2-3，重跑期间主代理轻任务计入预算）；
3. m31f 臂待 token-gate 放行后跑；step-5/m3 不受 GLM 预算约束；
4. 判定口径：同题 fix1（max_turns, reward=false）vs fix2 的 status/reward/turns 逐对比较；Δ 归因注记"协议（C1/C2/C8）vs 参数（P1/P2）"时参考研究② §2.2 外推（B1 类预期在 <100 轮内自然收束，若 fix2 在 60-100 轮完成即视为协议+收尾机制生效，非单纯轮次放宽）；
5. 完成后由分析组把 20 对结果并表入画像表（单代内 = fix2 代），fix1 结果保留原位不动作废。

## 4. 附节：A/B 读数方法（配对整体位移测量，2026-10-21 定）

对照重跑（§3，最难子集 20 run）回答的是"fix2 能否救回方向性失败"（答案：19/20 不能）；
本附节回答最后一块拼图——**fix2 对整体通过重心的位移**。同题同档案配对，比非配对比较
统计力强得多（消掉题目难度方差）。

### 4.1 数据与配对口径

- 配对单元：(task, profile)。fix1 侧 = `/tmp/bench-fix1-d1-glm-cp/results.jsonl` 与
  `/tmp/bench-fix1-d1-m31f/results.jsonl` 每题**末行**（v2 scaffold，k=1）；
  fix2 侧 = `/tmp/bench-fix2-ab-glm-cp/` 与 `/tmp/bench-fix2-ab-m31f/` 的 results.jsonl
  每题**末行**（v3 scaffold，k=1，attempt 目录唯一化后末行=最终态）。
- 抽样：`random.seed(20261021)`，glm-cp 先抽、m31f 后抽，各 15 题；池 = 该档案 fix1 D1
  已有结论（reward∈{T,F}）的题，排除 ①fix2 对照重跑 8 题（已有 fix2 读数）②主产线在飞同
  (task,profile) 题（容器名 `afbench-swev-<task>-<profile>` 不含 out 目录，同题双跑互踩）。
  骨架落盘 `<fix2-out>/pairing.json`（fix1 对照值已填，fix2_result 由分析组填充）。
- 抽样时刻基线：glm-cp 9 过/6 败；m31f 10 过/5 败（含失败与通过，无偏）。

### 4.2 读数指标

1. **整体通过率位移**：Δ = p2 − p1（同 15 题上 fix2 通过率 − fix1 通过率）。
   n=15 的 95% Wilson 区间半宽在 p≈0.5 时约 ±0.25——**|Δ| < 0.25 的单测量不定案**，
   须与最难子集结论 + 外部锚点（cb+deepseek 69.2%）联读。
2. **翻转矩阵**（配对主指标，信息量在不一致对）：
   翻正 F→T = b，翻负 T→F = c，维持（T→T 与 F→F）不计入检验。净位移 = b − c。
   显著性按 McNemar 精神：k = min(b,c) 对照 Binomial(b+c, 0.5)；
   **b+c < 6 时一律记"样本不足判"**，只陈述方向不做结论。
3. **无效对处理**：run_failed / setup_failed / reward=null（eval 未完成）的 fix2 行记
   reward=null，该对不入矩阵、单独列示；通过率位移按两口径双报：
   保守口径（null 记 0 分，等价"判 0"）与有效对口径（剔除无效对）。两口径结论相反时
   以保守口径示警、以有效对口径解读。
4. **归因注记**（参考 §3 纪律 4 的外推）：翻正且 fix2 turns<60 → 协议效果（C1/C2/C8）；
   翻正且 60≤turns≤250 → 跑道（P1）+协议混合；**翻负（回归）**单独取证——fix1 已过题
   被 fix2 跑挂是协议反伤信号（重点查提交式完成 C1 是否误判收尾、C9 反考古是否误触发），
   逐题附 turns 与 verifier_note。

### 4.3 判读矩阵（预登记，防事后合理化）

| 图景（b/c，n=15） | 判读 |
|---|---|
| b≥6, c≤2 | fix2 整体正位移成立，协议+跑道有效 |
| b≤2, c≥3 | **fix2 存在回归伤害**，优先于任何正读数，需逐题取证 |
| b、c 均 ≥3 且接近 | 方差主导，判分噪声与题目随机性 ~16-20%（cal2 实测）同量级，Δ 不可归因 |
| b+c<6 | 样本不足判，位移未知 |
两档案（glm-cp / m31f）分别出矩阵，不做合并（免费与套餐通道行为不可假设同质）；
若两档案方向一致则并述为"跨档案一致"，仍是定性并述而非合并检验。

## 5. 更新记录

| 日期 | 身份 | 变化 |
|---|---|---|
| 2026-10-20 | fix2 实施子代理 | 建档：借鉴清单（10 语义项 + 7 对齐参数项 + 2 联动）× 失败模式映射、实施位置、对照重跑协议（20 run / 8 题 / 5 档案） |
| 2026-10-21 | fix2 A/B 派发子代理 | 增 §4 附节（A/B 读数方法：配对口径/Wilson/翻转矩阵/判读矩阵预登记）；两 ab 臂（glm-cp、m31f × 15 题）热注入 factory2 图并启动，骨架 pairing.json 落盘 |
