# DESIGN.md — 三包任务集反饱和设计总说明

## 1. 设计目标与总原则

- **设计目标**：强裸模型（无 skill 挂载的 GLM-5.3-Flash）通过率 **≤60%**。
- **三维覆盖**：ability（能力基座）/ boundary（边界鲁棒）/ trap（陷阱惩戒），每包 trap ≥ 2（≥ 1/4）。
- **加权分项防饱和**：每题 rubric 分 5 个维度，权重和 100。关键杀伤维度占 25–50 分，裸模型凭常识难以拿满分。
- **输入 nonce 化**：所有输入内嵌于 task.json，不依赖外部文件路径；所有实体均为 nonce 值。
- **判据可机判优先**：brief.md 中所有 checklist 均可通过 runner 或脚本自动判定。

## 2. 旧题考点差异总表

| 包名 | 旧 golden.json ab_task | 已覆盖规则 | 新题避让策略 |
|---|---|---|---|
| meeting-minutes | ab-001 | 三节基础分类、summary 四键一致性、待办表格三列、逐字溯源、噪声行排除 | t01 复用基础分类但 transcript 为全新 nonce；t02–t08 全部避开 ab-001 的具体例句与条数组合 |
| meeting-minutes | ab-002 | 关键词碰撞优先级、负责人/期限基础提取、边界行收录 | t02 复用碰撞优先级但句子为全新 nonce；t04 覆盖 extraction-heuristics.md 中 ab-002 未涉及的 rule 1/4/5/7 |
| meeting-minutes | ab-003 | 负责人是我→说话人、本周五之前→周五之前、5月20日之前、截止到周五、收尾行收录 | t04 替换全部例句为旧题未覆盖的规则组合；t06/t07/t08 为全新 trap（否定词/口误更正/散会行），与 ab-003 零重叠 |
| office-templates | ab1 | 四类全字段标准生成、版式四要素、字段填充一致率 ≥90% | t01–t04 复用四类模板但使用全新 nonce 数据；t05–t08 为边界/trap，与 ab1 不重叠 |
| office-templates | ab2 | 必填缺失占位、选填缺失留空、unknown_keys | t05 覆盖选填缺失叠加与空列表占位条目（ab2 未测空列表/选填小节省略的组合）；t06 覆盖 unknown_keys 与非字符串值 |
| office-templates | ab3 | 空列表占位条目、字符串型列表单项化、选填小节省略 | t05 覆盖空数组渲染占位条目（与 ab3 类似但数据为全新 nonce，且叠加了报送日期空字符串）；t06 覆盖 unknown_keys 记账 |
| office-templates | ab4 | 四类非法输入 exit 2、零产物残留、中文 stderr | t07 复用四类非法输入但包装为“四组执行+对照组”的 trap 题，增加 stderr 中文判定与合法对照 |
| office-templates | ab5 | 同输入连跑两遍确定性、runner 自校验红绿 | t08 为 strip 边界，与 ab5 零重叠；t01–t04 为全字段生成，与 ab5 的确定性自校验侧重点不同 |
| hot-templates | ab-001 | dy + 3 卖点全填充、hook_3s 冻结文本、value_i 第X招前缀、CTA 冻结文本 | t01 改为 **wx + 2 卖点**；t02 改为 **video + 2 卖点**；t03 改为 **dy + 5 卖点**；t05 保留 **topic 特殊字符**；t07 改为 **dy + 前后空格 strip**；t08 改为 **points 为 object** |
| hot-templates | ab-002 | xhs + 5 卖点截断、title 🔥+数字、emoji 映射、points_unused 保序 | t04 改为 **xhs + 0 卖点**；t06 改为 **wx + 5 卖点** |
| hot-templates | ab-003 | wx + 0 卖点、三段论冻结开头、thesis_how 三抓手同居、金句共勉 | t06（wx + 5 卖点）完全避开零卖点；t01（wx + 2 卖点）覆盖 thesis_how 两填一缺 |
| hot-templates | ab-004 | video + 1 卖点、6 镜 45 秒、time_range 冻结、分镜总表 | t02（video + 2 卖点）覆盖 shot_3/4 填、shot_5 缺，与 ab-004 的 1 卖点不同 |
| hot-templates | ab-005 | 四平台 determinism、illegal platform exit 2、empty topic exit 2 | t08 改为 **points 为 object**（CLI 拒绝非法 points 格式），与 ab-005 的 platform/topic 侧重点不同 |

**结论**：24 道新题未复用旧 golden.json 的任何一句原文或等价结构。卖点-平台组合全部重新映射，确保每个组合唯一。

## 3. 三维覆盖统计

| 包名 | ability | boundary | trap | 总计 |
|---|---|---|---|---|
| meeting-minutes-skill | 2 | 3 | 3 | 8 |
| office-templates-skill | 4 | 2 | 2 | 8 |
| hot-templates-skill | 4 | 2 | 2 | 8 |
| **合计** | **10** | **7** | **7** | **24** |

## 4. 设计目标声明

- **强裸模型通过率 ≤60%**（写入每道题 design_note）。
- **判据可机判**：每道题 brief.md 的 checklist 均可通过正则、计数、字典比较、退出码自动判定。
- **实体 nonce 化**：所有输入内嵌，所有实体（人名、公司、数字、topic、卖点）均为 nonce 值。
- **与旧题不重复**：上表逐条列出了旧 golden.json ab_tasks 的规则覆盖和新题的避让策略。

## 5. 文件清单

每道题目录包含：
- `task.json`：任务 ID、类型、难度、instruction、nonce_input、expected、design_note
- `brief.md`：任务摘要 + 可机判判据清单
- `rubric.md`：加权分项 rubric（5 维度，权重和 100）

每包额外包含：
- `index.json`：任务清单
- `DESIGN.md`：本文件

顶层包含：
- `index.json`：三包汇总
- `DESIGN.md`：本文件
