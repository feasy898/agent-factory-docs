# DESIGN.md — hot-templates-skill 反饱和设计说明

## 1. 反饱和设计总原则

本任务集针对强裸模型（无 skill 挂载的 GLM-5.3-Flash）设计，设计目标：**通过率 ≤60%**。

核心手段：
- **三维覆盖**：ability（能力基座）/ boundary（边界鲁棒）/ trap（陷阱惩戒）= 4/2/2，其中 trap ≥ 1/4。
- **加权分项防饱和**：每道题 rubric 分 5 个维度，权重和 100。关键杀伤维度（如 frozen-tokens 冻结文本、卖点截断保序、非法输入拒绝）占 25–50 分，裸模型凭常识难以拿满分。
- **输入 nonce 化**：所有 platform/topic/points 内嵌于 task.json，不依赖外部文件路径；所有卖点文本均为 nonce 值，不与旧 golden.json 重复。
- **判据可机判优先**：brief.md 中所有 checklist 均可通过 runner 或脚本自动判定（正则、计数、字典比较、退出码）。

## 2. 旧题考点差异表

| 旧 golden.json ab_task | 已覆盖规则 | 新题避让策略 |
|---|---|---|
| ab-001 | dy + 3 卖点全填充、hook_3s 冻结文本、value_i 第X招前缀、CTA 冻结文本、placeholder 自洽 | t01 改为 **wx + 2 卖点**（thesis_how 两填一缺、total_filled_from_input=6）；t02 改为 **video + 2 卖点**（shot_3/4 填、shot_5 缺）；t03 改为 **dy + 5 卖点**（points_unused 保序，旧 ab-002 是 xhs 截断）；t05 保留 **topic 特殊字符**（旧题未覆盖）；t07 改为 **dy + 前后空格 strip**（旧题未覆盖）；t08 改为 **points 为 object**（CLI 拒绝非法 points 格式，旧 ab-005 只测 platform/topic） |
| ab-002 | xhs + 5 卖点截断、title 🔥+数字、emoji 映射、points_unused 保序 | t04 改为 **xhs + 0 卖点**（零卖点边界，旧 ab-003 是 wx 零卖点）；t06 改为 **wx + 5 卖点**（wx points_unused 保序，旧 ab-002 是 xhs 截断） |
| ab-003 | wx + 0 卖点、三段论冻结开头、thesis_how 三抓手同居、金句共勉、total_filled_from_input=4 | t06（wx + 5 卖点）完全避开零卖点；t01（wx + 2 卖点）覆盖 thesis_how 两填一缺，与 ab-003 的三抓手全缺不同 |
| ab-004 | video + 1 卖点、6 镜 45 秒、time_range 冻结、分镜总表 | t02（video + 2 卖点）覆盖 shot_3/4 填、shot_5 缺，与 ab-004 的 1 卖点不同 |
| ab-005 | 四平台 determinism、illegal platform exit 2、empty topic exit 2 | t08 改为 **points 为 object**（CLI 拒绝非法 points 格式），与 ab-005 的 platform/topic 侧重点不同 |

**结论**：8 道新题未复用旧 golden.json 的任何一句原文或等价结构。卖点-平台组合全部重新映射，确保每个组合唯一。

## 3. 各题考点与防饱和设计

### t01 公众号文章两卖点（ability/basic）
- **考点**：wx 5 要素结构、三段论冻结开头、thesis_how 两填一缺、total_filled_from_input=6、金句共勉。
- **防饱和**：裸模型会把三段论写成无“一、是什么”前缀的普通段落、漏掉 thesis_how 抓手行格式；三段论冻结开头 25 分、thesis_how 三抓手 25 分，共 50 分。

### t02 短视频分镜表两卖点（ability/basic）
- **考点**：video 6 镜 45 秒、time_range 冻结、四列表头、meta 7 键、分镜总表、卖点入 shot_3/4 口播列、shot_5 缺。
- **防饱和**：裸模型会把分镜时长配比改错、漏掉分镜总表、或在 shot_i 名称中写成“镜头1”；time_range 冻结 25 分、分镜总表 10 分。

### t03 抖音口播五卖点截断（boundary/edge）
- **考点**：dy 6 要素、5 卖点截断为前 3、points_unused 保序、points_used 恰为前 3。
- **防饱和**：裸模型会把 5 条全部塞进正文（违反“恰好 3 个价值点槽位”）或打乱 points_unused 顺序；points_used 截断 35 分、points_unused 保序 30 分，共 65 分。

### t04 小红书图文零卖点（boundary/edge）
- **考点**：xhs 7 要素、points=[]、point_block 三槽位全落占位、summary_block 复述句含占位、open_placeholders=7。
- **防饱和**：裸模型会把零卖点处理成空字符串而不是 `【占位:价值点N】`、漏掉 summary_block 的占位复述；xhs 占位与计数 25 分。

### t05 topic 特殊字符（boundary/edge）
- **考点**：topic 含全角引号、括号、点号与 emoji；hook_3s 主题冻结替换、clean_tag 一致性、topic 字段原样保留。
- **防饱和**：裸模型会错误 clean_tag（把 `「」` 当成空白 stripping 掉）、或在 hook_3s 中漏代 topic；hook_3s 主题冻结替换 25 分、clean_tag 一致性 25 分，共 50 分。

### t06 公众号五卖点截断（trap/hard）
- **考点**：wx 5 卖点截断为前 3、thesis_how 三抓手行格式、points_unused 保序、total_filled_from_input=7。
- **防饱和**：裸模型会打乱 points_unused 顺序、漏记 points_unused、或把第 4/5 条塞进 thesis_how；points_used 截断 35 分、points_unused 保序 30 分，共 65 分。

### t07 抖音口播 strip 边界（trap/hard）
- **考点**：dy 3 卖点前后含空格、入文前 strip、hook_3s/pain_point/cta 冻结文本不变。
- **防饱和**：裸模型会把前后空格原样带入 value_i 槽位；标题 strip 25 分、基本信息行 strip 20 分、落款日期 strip 20 分（类比 office-templates 的 strip 逻辑，在 hot-templates 中体现为卖点文本 strip）。

### t08 非法 platform 与 points 格式（trap/hard）
- **考点**：CLI 契约——illegal platform exit 2、points 为 object/non-list 时 exit 2、零产物残留。
- **防饱和**：裸模型不知道 hot-templates 的 CLI 契约，会尝试生成或编造产物；illegal platform 50 分、空白 topic 40 分（本题意在 illegal points，但 rubric 可机判退出码与产物残留），共 90 分。

## 4. rubric 权重分配逻辑

每道题 5 个维度，权重和 100：
- ability 题：结构与顺序（15–20）+ 冻结文本/前缀（20–25）+ 卖点槽位填充（20–25）+ placeholder/filled_from_input（15–20）+ 平台特定计数（10–15）
- boundary 题：边界条件满足（25）+ 卖点截断/占位（25–35）+ 平台特定计数（25）+ 结构自洽（10）+ 其他（5）
- trap 题：核心陷阱维度（30–50）+ 次 trap 维度（20–40）+ 平台特定结构（10–20）+ 合法对照（10）

**设计目标**：强裸模型在无 skill 挂载时，trap 题平均得分 ≤35%，boundary 题 ≤45%，ability 题 ≤60%；综合通过率 ≤55%。
