#!/usr/bin/env python3
"""Generate task sets for three skill packages."""
import json, os, textwrap

ROOT = "planning/taskset-redesign/step"

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content.strip() + "\n")

# ============================================================
# meeting-minutes-skill
# ============================================================
MM = os.path.join(ROOT, "meeting-minutes-skill")

# t01 ability/basic — 三节全有 + 元信息
write(f"{MM}/t01/task.json", json.dumps({
    "id": "t01",
    "type": "ability",
    "difficulty": "basic",
    "instruction": "使用 meeting-minutes 技能，对下面的会议转写稿生成三段式纪要（纪要.docx + summary.json）到指定输出目录 <outdir>。",
    "nonce_input": {
        "description": "内嵌转写稿，无外部路径依赖",
        "transcript": "[09:00] 主持人: 大家安静，会议开始\n[09:01] 产品张经理: 经过上周评估，我们决定启动A项目\n[09:02] 研发李工: 同意这个决定，资源我来协调\n[09:03] 测试王主管: 我们需要在本周内完成第一轮用例评审\n[09:04] 产品张经理: 评审由王主管负责，截止到本周五\n[09:05] 运维赵工: 服务器资源紧张，存在延期风险\n[09:06] 研发李工: 如果不提前申请，下周扩容可能来不及\n[09:07] 主持人: 散会"
    },
    "expected": {"决议事项": 2, "待办事项": 2, "风险与关注": 2, "合计": 6},
    "design_note": "强裸模型通过率 ≤55%：必须严格按 SKILL.md §3.2 的 11 关键词分类、§4 的元信息公式与待办表格三列格式执行。裸模型会把‘决定’和‘同意’漏归决议、把‘需要’和‘负责’漏归待办，或把‘风险’和‘延期’归并。"
}, ensure_ascii=False, indent=2))

write(f"{MM}/t01/brief.md", """\
# brief — t01 三节基础分类

**任务摘要**：对一段含决议/待办/风险各至少两行的转写稿生成标准三段式纪要。

**可机判判据（按优先级）**：
- `纪要.docx` 可被 python-docx 打开，且三节标题按顺序出现：`一、决议事项` / `二、待办事项` / `三、风险与关注`
- `summary.json` 四键数值与 docx 实际条数逐项一致且 `合计 = 三者和`
- 待办节为 3 列表格，表头含 `事项` `负责人` `期限`，数据行 = 待办条数
- 每个条目可在 transcript 中逐字溯源（含时间与说话人）
- 元信息行格式：`来源：<文件名> ｜ 解析发言 6 条（决议 2 · 待办 2 · 风险 2）`
""")

write(f"{MM}/t01/rubric.md", """\
# rubric — t01 三节基础分类

| 维度 | 权重 | 0 分（失格） | 6 分（部分） | 10 分（满分） |
|---|---|---|---|---|
| 三节结构与标题 | 20 | 缺节或标题错序 | 标题齐全但顺序错 | 标题齐全、顺序正确、可打开 |
| summary.json 四键一致性 | 20 | 四键不全或数值与文档不一致 | 合计错误或键名偏差 | 四键名精确、数值与文档完全一致 |
| 待办表格 | 20 | 无表格或列数≠3 | 表头不全或数据行≠2 | 表头含 事项/负责人/期限、数据行=2 |
| 逐字溯源 | 25 | 任一条目在 transcript 中找不到出处 | 条目内容改写或合并 | 每条目含【时间 · 说话人】且逐字出现在 transcript |
| 噪声行排除 | 15 | 散会行/寒暄行进入章节 | 少数噪声行混入 | 09:00/09:07 两噪声行完全未混入 |
""")

# t02 ability/basic — 关键词碰撞优先级 + 边界行收录
write(f"{MM}/t02/task.json", json.dumps({
    "id": "t02",
    "type": "ability",
    "difficulty": "basic",
    "instruction": "使用 meeting-minutes 技能，对下面的会议转写稿生成三段式纪要到指定输出目录 <outdir>。重点验证：一行同时命中多类关键词时的归类优先级（决议 > 待办 > 风险），以及含关键词的收尾行必须收录、不含关键词的散会行必须丢弃。",
    "nonce_input": {
        "description": "内嵌转写稿，含关键词碰撞与收尾行",
        "transcript": "[14:00] 主持人: 开始\n[14:01] 项目经理: 升级当天一旦出现延期迹象，立即回滚，这个结论请各位记牢\n[14:02] 开发组长: 需要再压一轮回归\n[14:03] 测试组长: 回归由测试组负责，截止到周三\n[14:04] 主持人: 散会"
    },
    "expected": {"决议事项": 1, "待办事项": 2, "风险与关注": 0, "合计": 3, "collision_line": "14:01 归决议"},
    "design_note": "强裸模型通过率 ≤50%：裸模型会把含‘延期’的行归风险、把‘结论’单独归决议，而 SKILL.md §3.2 规定同行命中多类只归最高优先级（决议 > 待办 > 风险）。"
}, ensure_ascii=False, indent=2))

write(f"{MM}/t02/brief.md", """\
# brief — t02 关键词碰撞与边界行

**任务摘要**：验证一行同时含“延期”和“结论”时归决议，以及含关键词的收尾行收录、散会行丢弃。

**可机判判据**：
- docx 中 `14:01` 条目出现在 `一、决议事项` 节
- `14:04` 散会行不出现在任何节（转录不可溯源）
- 待办表格数据行 = 2（14:02 与 14:03）
""")

write(f"{MM}/t02/rubric.md", """\
# rubric — t02 关键词碰撞与边界行

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 碰撞行优先级 | 35 | 14:01 归风险或待办 | 归决议但理由错误 | 归决议且与 SKILL.md 优先级一致 |
| 收尾行收录 | 20 | 含关键词的 14:01 未收录 | 收录但节错 | 正确收录且内容逐字 |
| 散会行排除 | 15 | 14:04 进入章节 | 14:04 未进入但其他噪声混入 | 14:04 完全未混入 |
| summary 与表格一致 | 20 | summary 数值错误 | 合计错误 | 四键精确、合计=3 |
| 待办条目溯源 | 10 | 任一待办找不到出处 | 内容改写 | 逐字溯源且含负责人/期限 |
""")

# t03 boundary/edge — 空文件与全噪声
write(f"{MM}/t03/task.json", json.dumps({
    "id": "t03",
    "type": "boundary",
    "difficulty": "edge",
    "instruction": "使用 meeting-minutes 技能，对下面的空转写稿（空字符串）生成三段式纪要到指定输出目录 <outdir>。重点验证空文件输入时技能必须合法产出三节皆空的 docx 与 summary 全 0，不报错。",
    "nonce_input": {
        "description": "直接传入空字符串，不依赖任何外部文件",
        "transcript": ""
    },
    "expected": {"决议事项": 0, "待办事项": 0, "风险与关注": 0, "合计": 0, "docx_openable": True},
    "design_note": "强裸模型通过率 ≤35%：裸模型往往在空输入时直接报错或停止，而 SKILL.md:77 明确规定空文件/全噪声输入不报错，必须产出三节皆空且 summary 全 0 的合法 docx。"
}, ensure_ascii=False, indent=2))

write(f"{MM}/t03/brief.md", """\
# brief — t03 空输入边界

**任务摘要**：空转写稿输入，验证三节皆空 + summary 全 0 + docx 可打开。

**可机判判据**：
- `纪要.docx` 存在且可被 python-docx 打开
- 文档包含三个节标题 `一、决议事项` `二、待办事项` `三、风险与关注`
- 三节标题下均无条目
- 待办表格仅含表头行（`事项` `负责人` `期限`）
- `summary.json` 四键数值全为 0 且 `合计 = 0`
""")

write(f"{MM}/t03/rubric.md", """\
# rubric — t03 空输入边界

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 空输入不报错 | 30 | 未产出或非 0 退出 | 产出但结构错误 | 正常退出码 0 且产物齐全 |
| docx 三节标题保留 | 25 | 任意一节标题缺失 | 标题存在但顺序错 | 三节标题齐全、顺序正确 |
| 三节条目全空 | 25 | 任意节出现条目 | 节标题下有空白段落 | 三节标题下无任何条目段落 |
| summary 全 0 | 15 | 四键不全 | 任一键≠0 | 四键全 0 且合计=0 |
| 待办表格结构 | 5 | 无表格 | 列数≠3 | 仅表头行、列数=3 |
""")

# t04 boundary/edge — 负责人/期限复杂提取
write(f"{MM}/t04/task.json", json.dumps({
    "id": "t04",
    "type": "boundary",
    "difficulty": "edge",
    "instruction": "使用 meeting-minutes 技能，对下面的会议转写稿生成三段式纪要到指定输出目录 <outdir>。重点验证待办负责人与期限的确定性提取（仅按 extraction-heuristics.md 规则，未命中一律填「待定」）。",
    "nonce_input": {
        "description": "内嵌转写稿，覆盖负责人/期限五条规则",
        "transcript": "[10:00] 主持人: 开始\n[10:01] 行政刘主任: 公告由医务处负责\n[10:02] 项目经理: @张三请跟进供应商合同\n[10:03] 测试钱主任: 负责人是我，本周五之前出结果\n[10:04] 运维赵工: 需要重新提交检测报告\n[10:05] 产品张经理: 5月20日之前必须到港\n[10:06] 研发李工: 截止到下周一提交方案\n[10:07] 主持人: 散会"
    },
    "expected": {
        "待办条数": 6,
        "负责人": ["医务处", "张三", "钱主任", "待定", "待定", "待定"],
        "期限": ["待定", "待定", "周五之前", "待定", "5月20日之前", "下周一"]
    },
    "design_note": "强裸模型通过率 ≤45%：裸模型会把‘@张三’识别为提及而非负责人、把‘负责人是我’留空或写‘我’、把‘本周五之前’写成‘本周五之前’（未剥离前缀），或把‘5月20日之前’写成‘5月20日’（未保留后缀）。"
}, ensure_ascii=False, indent=2))

write(f"{MM}/t04/brief.md", """\
# brief — t04 负责人/期限复杂提取

**任务摘要**：验证 extraction-heuristics.md 的五条负责人规则与七条期限规则，以及“我→说话人”替换和“本周/下周”前缀剥离。

**可机判判据**：
- 待办表格 6 行，负责人列依次为：医务处 / 张三 / 钱主任 / 待定 / 待定 / 待定
- 期限列依次为：待定 / 待定 / 周五之前 / 待定 / 5月20日之前 / 下周一
- 所有值都能在对应 transcript 行中逐字找到（“我”→说话人除外）
""")

write(f"{MM}/t04/rubric.md", """\
# rubric — t04 负责人/期限复杂提取

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 负责人提取 | 35 | 任意负责人错或非待定写“待定” | 2处以内错误 | 六行负责人全部按规则提取 |
| 期限提取 | 35 | 任意期限错 | 2处以内错误 | 六行期限全部按规则提取 |
| 前缀/后缀处理 | 15 | “本周五之前”未剥离 | 仅部分正确 | 全部正确（周五之前/5月20日之前/下周一） |
| “我→说话人”替换 | 10 | 写“我”或留空 | 写说话人但其他错误 | 正确替换为说话人“钱主任” |
| 未命中填待定 | 5 | 编造负责人或日期 | 一处未命中未填待定 | 所有未命中行均为待定 |
""")

# t05 boundary/edge — BOM与格式噪声
write(f"{MM}/t05/task.json", json.dumps({
    "id": "t05",
    "type": "boundary",
    "difficulty": "edge",
    "instruction": "使用 meeting-minutes 技能，对下面的会议转写稿生成三段式纪要到指定输出目录 <outdir>。重点验证 UTF-8 BOM 容忍、中英文冒号混用、说话人含空格、无时间戳但内容含关键词行的噪声排除。",
    "nonce_input": {
        "description": "内嵌转写稿，含 BOM 与格式变体（BOM 以 \\ufeff 前缀表示，不依赖外部文件）",
        "transcript": "\ufeff[09:00] 主持人: 开始\n[09:01] 产品张 经理: 经过讨论，同意采用方案B\n[09:02] 记录: 需要会后整理纪要\n[09:03] 主持人: 今天天气不错\n[09:04] 开发组长: 决定采用方案B\n[09:05] 主持人: 散会"
    },
    "expected": {"决议事项": 2, "待办事项": 1, "风险与关注": 0, "合计": 3},
    "design_note": "强裸模型通过率 ≤40%：裸模型可能因 BOM 导致首行解析失败、把‘产品张 经理’（说话人含空格）解析错、把‘记录:’（无时间戳但含冒号且含关键词）当成有效发言收录。SKILL.md §2 规定正则解析容忍 BOM，无时间戳非空行一律作噪声。"
}, ensure_ascii=False, indent=2))

write(f"{MM}/t05/brief.md", """\
# brief — t05 BOM 与格式噪声边界

**任务摘要**：验证 UTF-8 BOM 容忍、中英文冒号混用、说话人含空格、无时间戳关键词行作噪声。

**可机判判据**：
- `纪要.docx` 可打开，无解析报错
- 条目行数为 3（决议 2、待办 1）
- `09:02` 行（无时间戳但含关键词）不出现在任何节
- `09:03` 行（无关键词）不出现在任何节
- `09:01` 发言人中“张 经理”被保留原样，不被拆分
""")

write(f"{MM}/t05/rubric.md", """\
# rubric — t05 BOM 与格式噪声边界

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| BOM 容忍 | 25 | 首行解析失败导致整体错误 | 首行丢弃但其余正确 | 首行正常解析，BOM 不影响输出 |
| 冒号混用 | 20 | 英文冒号行解析失败 | 中文/英文冒号行部分正确 | 中英文冒号均被正确解析 |
| 说话人含空格 | 15 | 解析为“张”或报错 | 保留但条目格式错 | 保留原样“张 经理” |
| 无时间戳噪声行 | 25 | 09:02 进入章节 | 09:02 未进入但其他噪声混入 | 09:02 与 09:03 均完全未混入 |
| summary 计数 | 15 | 数值错误 | 合计错误 | 决议2/待办1/风险0/合计3 |
""")

# t06 trap/hard — 否定词误导
write(f"{MM}/t06/task.json", json.dumps({
    "id": "t06",
    "type": "trap",
    "difficulty": "hard",
    "instruction": "使用 meeting-minutes 技能，对下面的会议转写稿生成三段式纪要到指定输出目录 <outdir>。特别注意：否定词不影响归类（‘不能延期’照样归风险，‘议定’照样归决议）。",
    "nonce_input": {
        "description": "内嵌转写稿，含否定词陷阱",
        "transcript": "[11:00] 主持人: 开始\n[11:01] 销售陈总: 48小时发货的承诺不能延期，否则赔偿\n[11:02] 研发李工: 这个方案就议定下来，不再修改\n[11:03] 测试王主管: 需要补充边界用例\n[11:04] 主持人: 散会"
    },
    "expected": {"决议事项": 1, "待办事项": 1, "风险与关注": 1, "合计": 3, "trap_notes": ["不能延期→风险", "议定→决议"]},
    "design_note": "强裸模型通过率 ≤30%：裸模型会凭语义把“不能延期”当成“不是延期”而排入决议或丢弃，把“议定”当成普通动词而漏归决议。SKILL.md:45 与 classification-rules.md:34 明确否定词不影响归类。"
}, ensure_ascii=False, indent=2))

write(f"{MM}/t06/brief.md", """\
# brief — t06 否定词陷阱

**任务摘要**：验证否定词不影响归类——“不能延期”归风险，“议定”归决议。

**可机判判据**：
- `11:01` 条目出现在 `三、风险与关注` 节
- `11:02` 条目出现在 `一、决议事项` 节
- `11:03` 条目出现在 `二、待办事项` 节
- summary 为 `决议事项:1, 待办事项:1, 风险与关注:1, 合计:3`
""")

write(f"{MM}/t06/rubric.md", """\
# rubric — t06 否定词陷阱

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 否定词归风险 | 40 | “不能延期”归决议或待办 | 归风险但理由错误 | 正确归风险与关注 |
| 议定归决议 | 30 | “议定”归风险或待办 | 归决议但理由错误 | 正确归决议事项 |
| summary 一致性 | 20 | 数值错误 | 合计错误 | 1/1/1/3 精确 |
| 条目溯源 | 10 | 任一条目错出处 | 内容改写 | 逐字溯源 |
""")

# t07 trap/hard — 口误更正独立
write(f"{MM}/t07/task.json", json.dumps({
    "id": "t07",
    "type": "trap",
    "difficulty": "hard",
    "instruction": "使用 meeting-minutes 技能，对下面的会议转写稿生成三段式纪要到指定输出目录 <outdir>。特别注意：口误更正行与被更正行各自独立按关键词处理，不做上下文关联。",
    "nonce_input": {
        "description": "内嵌转写稿，含口误更正行（无关键词）与被更正行（含关键词）",
        "transcript": "[15:00] 主持人: 开始\n[15:01] 质检钱主任: 等等，我刚才说错了，我们需要重新提交检测报告\n[15:02] 质检钱主任: 负责人是我，本周五之前出结果\n[15:03] 主持人: 散会"
    },
    "expected": {"决议事项": 0, "待办事项": 1, "风险与关注": 0, "合计": 1, "excluded_line": "15:01"},
    "design_note": "强裸模型通过率 ≤35%：裸模型会尝试把 15:01 和 15:02 语义合并、或把 15:01 的“需要”延伸到 15:02。SKILL.md §3.2 与 classification-rules.md:33 规定口误更正不做上下文关联，更正前后行各自独立按关键词处理。"
}, ensure_ascii=False, indent=2))

write(f"{MM}/t07/brief.md", """\
# brief — t07 口误更正独立处理

**任务摘要**：验证口误更正行（无关键词）与被更正行（含关键词）各自独立处理，不合并。

**可机判判据**：
- `15:01` 行不出现在任何节（转录不可溯源）
- `15:02` 行出现在 `二、待办事项` 节，负责人=`钱主任`，期限=`周五之前`
- summary 为 `待办事项:1, 合计:1`
""")

write(f"{MM}/t07/rubric.md", """\
# rubric — t07 口误更正独立处理

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 口误更正行排除 | 40 | 15:01 进入章节 | 15:01 未进入但内容影响他行 | 15:01 完全未混入 |
| 被更正行独立收录 | 30 | 15:02 未收录 | 收录但负责人/期限错误 | 正确收录且负责人/期限正确 |
| summary 一致性 | 20 | 数值错误 | 合计错误 | 待办1/合计1 |
| 未做语义合并 | 10 | 两行语义合并为一条 | 无合并但多出噪声 | 两行严格独立处理 |
""")

# t08 trap/hard — 收尾行 vs 散会行
write(f"{MM}/t08/task.json", json.dumps({
    "id": "t08",
    "type": "trap",
    "difficulty": "hard",
    "instruction": "使用 meeting-minutes 技能，对下面的会议转写稿生成三段式纪要到指定输出目录 <outdir>。重点验证：只看关键词、不看行位置——含关键词的收尾行照样收录，不含关键词的散会行照样丢弃。",
    "nonce_input": {
        "description": "内嵌转写稿，含多条收尾/散会变体",
        "transcript": "[16:00] 主持人: 开始\n[16:01] 项目经理: 结论：培训未完成的员工一律不许独立上岗。散会\n[16:02] 主持人: 谢谢各位，散会\n[16:03] 运维赵工: 存在延期风险\n[16:04] 主持人: 各位早点休息\n[16:05] 主持人: 散会"
    },
    "expected": {"决议事项": 1, "待办事项": 0, "风险与关注": 1, "合计": 2, "included": ["16:01", "16:03"], "excluded": ["16:02", "16:04", "16:05"]},
    "design_note": "强裸模型通过率 ≤40%：裸模型会把 16:01 因含‘散会’而丢弃、或把 16:02 因礼貌性收尾而收录。SKILL.md §3.2 与 classification-rules.md:31 明确规定只看关键词、不看行位置。"
}, ensure_ascii=False, indent=2))

write(f"{MM}/t08/brief.md", """\
# brief — t08 收尾行 vs 散会行

**任务摘要**：验证只看关键词、不看行位置——含关键词的收尾行收录，不含关键词的散会行丢弃。

**可机判判据**：
- `16:01` 出现在 `一、决议事项` 节（含“结论”）
- `16:03` 出现在 `三、风险与关注` 节（含“风险”）
- `16:02`（散会，无关键词）、`16:04`（无关键词）、`16:05`（散会，无关键词）均不出现在任何节
- summary 为 `决议事项:1, 待办事项:0, 风险与关注:1, 合计:2`
""")

write(f"{MM}/t08/rubric.md", """\
# rubric — t08 收尾行 vs 散会行

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 含关键词收尾行收录 | 30 | 16:01 未收录 | 收录但归错节 | 正确收录且归决议 |
| 不含关键词散会行丢弃 | 30 | 16:02 或 16:05 进入章节 | 部分正确 | 16:02/16:04/16:05 均未混入 |
| 风险行正确收录 | 20 | 16:03 未收录 | 归错节 | 正确归风险 |
| summary 与节空保留 | 15 | 数值错误或删除空节标题 | 合计错误 | 决议1/待办0/风险1/合计2，待办节标题仍在 |
| 条目溯源 | 5 | 错出处 | 内容改写 | 逐字溯源 |
""")

print("meeting-minutes-skill generated.")

# ============================================================
# office-templates-skill
# ============================================================
OF = os.path.join(ROOT, "office-templates-skill")

# t01 ability/basic — 周报全字段
write(f"{OF}/t01/task.json", json.dumps({
    "id": "t01",
    "type": "ability",
    "difficulty": "basic",
    "instruction": "使用 office-templates 技能，对下面的周报数据 JSON 生成 文书.docx 与 fields.json 到指定输出目录 <outdir>。数据字段全部齐全，验证标准全量生成。",
    "nonce_input": {
        "description": "周报全字段 JSON，内嵌",
        "data": {
            "部门": "测试部",
            "填报人": "赵倩",
            "周期": "第40周",
            "本周工作内容": ["完成接口回归测试", "修复P1/P2缺陷12个"],
            "下周工作计划": ["启动性能压测", "输出测试报告"],
            "问题与需协调事项": ["需要运维配合扩容"],
            "报送日期": "2026-10-08"
        }
    },
    "expected": {"filled": 7, "missing_required": [], "title": "测试部工作周报"},
    "design_note": "强裸模型通过率 ≤55%：裸模型往往漏掉基本信息行格式、落款右对齐两字缩进、标题公式精确匹配，或把选填‘问题与需协调事项’误省为不出现。"
}, ensure_ascii=False, indent=2))

write(f"{OF}/t01/brief.md", """\
# brief — t01 周报全字段标准生成

**任务摘要**：周报七字段齐全，验证标题公式、基本信息行、两节必填列表、选填小节、落款。

**可机判判据**：
- `fields.json` 顶层键集合与 SKILL.md §5 一致：`template/title/filled_fields/missing_fields/fields/summary/outputs`
- `summary.filled == 7` 且 `summary.missing_required == []`
- `title == "测试部工作周报"`
- `文书.docx` 标题居中黑体二号；段落顺序：标题→基本信息行→一、本周工作内容→二、下周工作计划→三、问题与需协调事项→报送日期
- 落款行 `报送日期：2026-10-08` 右对齐且右缩进两字
""")

write(f"{OF}/t01/rubric.md", """\
# rubric — t01 周报全字段标准生成

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| fields.json 结构 | 20 | 顶层键不全 | summary 计数与明细不一致 | 顶层键集合精确、filled+missing=total |
| 标题公式 | 20 | 标题非“部门工作周报” | 标题正确但字体/居中错 | `测试部工作周报`、居中、黑体22pt |
| 段落顺序与称谓 | 20 | 段落顺序错 | 基本信息行格式错 | 顺序精确，`填报人：赵倩　　周期：第40周` |
| 列表小节与条目 | 25 | 列表项缺失或编号错 | 编号正确但缩进/字体错 | 一/二/三节头、1．2．条目、仿宋16pt、首行缩进 |
| 落款与版式 | 15 | 落款未右对齐 | 右缩进≠两字 | 右对齐、右缩进≈32pt、标签保留 |
""")

# t02 ability/basic — 请示函全字段
write(f"{OF}/t02/task.json", json.dumps({
    "id": "t02",
    "type": "ability",
    "difficulty": "basic",
    "instruction": "使用 office-templates 技能，对下面的请示函数据 JSON 生成 文书.docx 与 fields.json。验证标题公式、称谓顶格、联系行、两行落款。",
    "nonce_input": {
        "description": "请示函全字段 JSON，内嵌",
        "data": {
            "请示事由": "申请购买测试服务器",
            "主送机关": "信息中心",
            "请示缘由": "现有服务器已满载，无法支撑Q4压测",
            "请示事项": "拟采购2台2U机架式服务器，预算12万元",
            "请示单位": "测试部",
            "联系人": "李工",
            "联系电话": "13800138000",
            "成文日期": "2026-10-08"
        }
    },
    "expected": {"filled": 8, "missing_required": [], "title": "关于申请购买测试服务器的请示"},
    "design_note": "强裸模型通过率 ≤55%：裸模型常把称谓写成缩进、漏掉联系行中两个字段的同行布局、或把落款日期加上‘成文日期：’标签。SKILL.md §6 V3/V5 明确称谓顶格、落款日期行为裸日期。"
}, ensure_ascii=False, indent=2))

write(f"{OF}/t02/brief.md", """\
# brief — t02 请示函全字段标准生成

**任务摘要**：请示函八字段齐全，验证标题、称谓、正文段落、联系行、两行落款。

**可机判判据**：
- `title == "关于申请购买测试服务器的请示"`
- 第二非空段为 `信息中心：`，无首行缩进、全角冒号
- 联系行为 `联系人：李工　　联系电话：13800138000`
- 末两段右对齐：`测试部` 与 `2026-10-08`
- `summary.filled == 8`
""")

write(f"{OF}/t02/rubric.md", """\
# rubric — t02 请示函全字段标准生成

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 标题公式 | 20 | 标题错 | 标题正确但字体/居中错 | `关于…的请示`、居中、黑体22pt |
| 称谓顶格 | 20 | 称谓缩进 | 冒号错或字段值错 | 顶格、`信息中心：` |
| 正文段落 | 20 | 段落顺序错 | 缺少请示缘由或事项 | 缘由+事项两段、仿宋首行缩进 |
| 联系行与落款 | 25 | 联系行格式错 | 落款未右对齐 | 联系行两字段齐全；落款两行右对齐右缩两字 |
| fields.json 自洽 | 15 | filled≠8 或明细错 | missing_required 非空 | 8/8、无缺失、title 与文档一致 |
""")

# t03 ability/basic — 会议通知全字段
write(f"{OF}/t03/task.json", json.dumps({
    "id": "t03",
    "type": "ability",
    "difficulty": "basic",
    "instruction": "使用 office-templates 技能，对下面的会议通知数据 JSON 生成 文书.docx 与 fields.json。验证标题、称谓、会议三要素段落、选填议题/要求、联系行、两行落款。",
    "nonce_input": {
        "description": "会议通知全字段 JSON，内嵌",
        "data": {
            "会议名称": "Q4冲刺启动会",
            "召开单位": "总经理办公室",
            "主送对象": "各部门",
            "会议时间": "2026年10月10日 14:00",
            "会议地点": "总部301会议室",
            "参会人员": "全体中层",
            "会议议题": "Q4目标拆解与资源配置",
            "会议要求": ["请提前准备部门Q4规划", "带笔记本电脑"],
            "联系人": "周秘书",
            "联系电话": "010-88888888",
            "发文日期": "2026-10-08"
        }
    },
    "expected": {"filled": 11, "missing_required": [], "title": "关于召开Q4冲刺启动会的通知"},
    "design_note": "强裸模型通过率 ≤55%：裸模型常把会议要求写成非列表、漏掉会议议题段、或把召开单位/发文日期顺序写反。SKILL.md §6 V6 要求列表用‘1．2．’编号，选填小节存在时保留。"
}, ensure_ascii=False, indent=2))

write(f"{OF}/t03/brief.md", """\
# brief — t03 会议通知全字段标准生成

**任务摘要**：会议通知十一字段齐全，验证标题、称谓、会议三要素、选填议题/要求、联系行、两行落款。

**可机判判据**：
- `title == "关于召开Q4冲刺启动会的通知"`
- 第二非空段为 `各部门：`，顶格
- 包含 `会议时间：` `会议地点：` `参会人员：` 三段
- `会议要求` 为列表小节，条目编号 `1．` `2．`
- 联系行与两行落款（召开单位、发文日期）右对齐
""")

write(f"{OF}/t03/rubric.md", """\
# rubric — t03 会议通知全字段标准生成

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 标题公式 | 15 | 标题错 | 正确但字体/居中错 | `关于召开…的通知`、居中、黑体22pt |
| 称谓顶格 | 15 | 称谓缩进 | 冒号错 | `各部门：` 顶格 |
| 会议三要素段落 | 20 | 缺时间/地点/人员 | 段落存在但顺序错 | 三段齐全、顺序正确 |
| 选填议题与要求 | 20 | 会议要求非列表或议题缺失 | 列表编号错 | 议题段存在；要求节头+1．2．条目 |
| 联系行与落款 | 20 | 联系行缺字段 | 落款未右对齐 | 联系行两字段齐全；落款两行右对齐右缩两字 |
| fields.json 自洽 | 10 | 顶层键或计数错 | missing_required 非空 | 11/11、title 一致 |
""")

# t04 ability/basic — 工作总结全字段
write(f"{OF}/t04/task.json", json.dumps({
    "id": "t04",
    "type": "ability",
    "difficulty": "basic",
    "instruction": "使用 office-templates 技能，对下面的工作总结数据 JSON 生成 文书.docx 与 fields.json。验证标题公式（总结主体+总结时段）、四节列表结构、无称谓、两行落款。",
    "nonce_input": {
        "description": "工作总结全字段 JSON，内嵌",
        "data": {
            "总结主体": "平台部",
            "总结时段": "2026年9月",
            "工作回顾": ["完成评测平台月度巡检", "修复3个历史缺陷"],
            "主要成绩": ["平台可用性达到99.95%", "输出月度巡检报告"],
            "存在问题": ["文档更新不及时"],
            "下一步工作打算": ["制定四季度评测排期", "启动自动化巡检"],
            "成文日期": "2026-10-08"
        }
    },
    "expected": {"filled": 7, "missing_required": [], "title": "平台部2026年9月工作总结"},
    "design_note": "强裸模型通过率 ≤55%：裸模型常把总结主体/总结时段写成带空格的公式、漏掉第四必填节‘下一步工作打算’、或在落款处错误添加标签。工作总结无称谓段是与其他模板的关键区别。"
}, ensure_ascii=False, indent=2))

write(f"{OF}/t04/brief.md", """\
# brief — t04 工作总结全字段标准生成

**任务摘要**：工作总结七字段齐全，验证标题公式、四节结构、无称谓、两行落款。

**可机判判据**：
- `title == "平台部2026年9月工作总结"`
- 段落顺序：标题→一、工作回顾→二、主要成绩→三、存在问题→四、下一步工作打算→落款两行
- 无称谓段（与请示函/会议通知的区别）
- 落款第一行 `平台部` 右对齐，第二行 `2026-10-08` 右对齐且无标签
""")

write(f"{OF}/t04/rubric.md", """\
# rubric — t04 工作总结全字段标准生成

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 标题公式 | 20 | 标题错 | 正确但字体/居中错 | `总结主体总结时段工作总结`、居中、黑体22pt |
| 四节结构 | 25 | 缺节或节名错 | 节名正确但列表格式错 | 一/二/三/四节头、1．2．条目、仿宋首行缩进 |
| 无称谓段 | 15 | 出现称谓段 | 标题后直接节头 | 无任何称谓段落 |
| 落款 | 25 | 落款未右对齐 | 日期带标签 | 两行右对齐、右缩两字、日期裸日期 |
| fields.json 自洽 | 15 | 顶层键或计数错 | missing_required 非空 | 7/7、title 一致 |
""")

# t05 boundary/edge — 周报选填缺失叠加 + 字符串型列表
write(f"{OF}/t05/task.json", json.dumps({
    "id": "t05",
    "type": "boundary",
    "difficulty": "edge",
    "instruction": "使用 office-templates 技能，对下面的周报数据 JSON 生成 文书.docx 与 fields.json。数据包含：周期为空字符串、本周工作内容为空数组、问题与需协调事项缺失、报送日期为空字符串。验证选填缺失的留空/省略与必填缺失的占位行为。",
    "nonce_input": {
        "description": "周报边界 JSON，内嵌",
        "data": {
            "部门": "测试部",
            "填报人": "赵倩",
            "周期": "",
            "本周工作内容": [],
            "下周工作计划": ["整理缺陷清单并分派责任人"],
            "问题与需协调事项": "",
            "报送日期": ""
        }
    },
    "expected": {"filled": 3, "missing_required": ["部门", "周期", "本周工作内容"], "missing_optional": ["问题与需协调事项", "报送日期"]},
    "design_note": "强裸模型通过率 ≤45%：裸模型会把空数组渲染成无内容小节而不是‘1．____’占位条目、把选填‘问题与需协调事项’写成小节头加空白、或把报送日期留空写成删除整行。SKILL.md §3.2 F1–F4 规定必填空列表→占位条目、选填小节整节省略。"
}, ensure_ascii=False, indent=2))

write(f"{OF}/t05/brief.md", """\
# brief — t05 周报选填缺失叠加

**任务摘要**：验证必填缺失（____ 占位）、选填缺失（留空/省略）、空列表渲染占位条目、字符串型列表单项化。

**可机判判据**：
- 标题为 `____工作周报`（周期必填缺失）
- 一、本周工作内容 节头保留，条目为 `1．____`
- 三、问题与需协调事项 节头完全不出现在 docx
- `报送日期：` 标签保留但值为空
- `summary.missing_required == ["部门","周期","本周工作内容"]`
""")

write(f"{OF}/t05/rubric.md", """\
# rubric — t05 周报选填缺失叠加

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 必填缺失占位 | 30 | 标题未用 ____ 或节头缺失 | 部分占位 | 标题 `____工作周报`、节头保留、`1．____` |
| 选填小节省略 | 25 | “问题与需协调事项”节头出现 | 节头省略但内容残留 | 节头与条目均未出现 |
| 选填文本留空 | 20 | `报送日期：` 整行删除 | 标签删除或值填入占位 | `报送日期：` 标签保留、值为空 |
| fields.json 记账 | 15 | missing_required 或 missing 错 | 计数与明细不一致 | 必填/选填分类精确 |
| 列表字段取值宽容 | 10 | 字符串未单项化或数组处理错 | 部分正确 | 下周工作计划字符串/数组均可正确渲染 |
"""))

# t06 boundary/edge — 请示函必填缺失 + unknown_keys + 空白值
write(f"{OF}/t06/task.json", json.dumps({
    "id": "t06",
    "type": "boundary",
    "difficulty": "edge",
    "instruction": "使用 office-templates 技能，对下面的请示函数据 JSON 生成 文书.docx 与 fields.json。数据包含：主送机关缺失、请示事项为空字符串、联系电话/成文日期选填缺失、含模板外键「备注」。验证必填缺失占位、选填留空、unknown_keys 记账。",
    "nonce_input": {
        "description": "请示函边界 JSON，内嵌",
        "data": {
            "请示事由": "升级开发环境",
            "主送机关": "",
            "请示缘由": "当前环境版本过低，无法支撑新业务上线",
            "请示事项": "",
            "请示单位": "测试部",
            "联系人": "李工",
            "联系电话": "",
            "成文日期": "",
            "备注": "加急"
        }
    },
    "expected": {"filled": 4, "missing_required": ["主送机关", "请示事项"], "missing_optional": ["联系电话", "成文日期"], "unknown_keys": ["备注"]},
    "design_note": "强裸模型通过率 ≤45%：裸模型会把空字符串当成已填充、漏记 unknown_keys、或把‘联系电话：’后面的空白删除成整行消失。SKILL.md §3.2 F1/F2/F6 规定空白字符串为缺失、模板外键按字典序记账。"
}, ensure_ascii=False, indent=2))

write(f"{OF}/t06/brief.md", """\
# brief — t06 请示函必填缺失 + unknown_keys

**任务摘要**：验证必填缺失渲染 `____`、选填缺失留空、unknown_keys 记账。

**可机判判据**：
- 称谓为 `____：`（主送机关必填缺失）
- 请示事项段为 `____`（请示事项空字符串）
- 联系行为 `联系人：李工　　联系电话：`
- 落款一 `测试部` 右对齐，落款二为空段
- `fields.json.summary.unknown_keys == ["备注"]`
- `fields.json.summary.missing_required_names == ["主送机关","请示事项"]`
""")

write(f"{OF}/t06/rubric.md", """\
# rubric — t06 请示函必填缺失 + unknown_keys

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 必填缺失占位 | 30 | 称谓或事项未用 ____ | 一处占位正确 | 称谓 `____：`、事项段 `____` |
| 选填留空 | 25 | 联系电话/成文日期被删除或占位 | 标签保留但格式错 | `联系人：李工　　联系电话：`、落款二空段 |
| unknown_keys 记账 | 20 | unknown_keys 为空或值错 | 键名错或顺序错 | `["备注"]`、字典序 |
| 落款版式 | 15 | 落款未右对齐 | 日期带标签 | 落款一右对齐、落款二空段右对齐 |
| fields.json 自洽 | 10 | filled/missing 计数错 | 明细与计数不一致 | filled=4、missing_required 精确 |
"""))

# t07 trap/hard — 非法输入拒绝
write(f"{OF}/t07/task.json", json.dumps({
    "id": "t07",
    "type": "trap",
    "difficulty": "hard",
    "instruction": "使用 office-templates 技能，对下面四组非法输入分别构造并执行生成命令，记录每组退出码、stderr 与产物残留。对照组使用合法周报数据。判定被测 CLI 契约（SKILL.md §4）是否与参照一致。",
    "nonce_input": {
        "description": "四组非法输入描述 + 一组合法对照数据，内嵌",
        "test_cases": [
            {"id": "invalid_template", "template": "证书", "data_ofn": "合法对照数据见下方", "desc": "模板名不在四类"},
            {"id": "missing_file", "template": "周报", "data_ofn": "/_nonexistent_/data.json", "desc": "数据文件不存在"},
            {"id": "bad_json", "template": "周报", "data_content": "不是JSON", "desc": "JSON 解析失败"},
            {"id": "top_level_array", "template": "周报", "data_content": "[\"数组\",\"非对象\"]", "desc": "顶层非对象"}
        ],
        "control": {
            "template": "周报",
            "data": {
                "部门": "测试部",
                "填报人": "赵倩",
                "周期": "第40周",
                "本周工作内容": ["完成接口回归测试"],
                "下周工作计划": ["整理缺陷清单并分派责任人"],
                "问题与需协调事项": "",
                "报送日期": ""
            }
        }
    },
    "expected": {"每组退出码": 2, "产物残留数": 0, "对照组退出码": 0, "stderr_含中文": True},
    "design_note": "强裸模型通过率 ≤30%：裸模型通常不知道 office-templates 的 CLI 契约，不知道四类非法输入应 exit 2 且零产物残留，甚至会编造错误信息或允许非法模板通过。SKILL.md §4/§7 明确列出四种非法输入与退出码 2。"
}, ensure_ascii=False, indent=2))

write(f"{OF}/t07/brief.md", """\
# brief — t07 非法输入拒绝

**任务摘要**：四组非法输入（模板名非法、数据文件不存在、JSON 解析失败、顶层非对象）各执行一次，对照组执行一次合法输入。

**可机判判据**：
- 四组非法输入的退出码均为 `2`
- 四组输出目录均未创建（`find <outdir> -type f | wc -l` 输出 `0`）
- 对照组退出码为 `0` 且 `outdir` 下恰有 `文书.docx` 与 `fields.json`
- 四组 stderr 均含中文错误提示
""")

write(f"{OF}/t07/rubric.md", """\
# rubric — t07 非法输入拒绝

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 非法模板名 | 25 | exit ≠2 或产生产物 | exit 2 但 stderr 无中文 | exit 2、零产物、中文 stderr |
| 文件不存在 | 25 | exit ≠2 或产生产物 | exit 2 但 outdir 被创建 | exit 2、零产物、中文 stderr |
| JSON 解析失败 | 25 | exit ≠2 或产生产物 | exit 2 但 outdir 被创建 | exit 2、零产物、中文 stderr |
| 顶层非对象 | 15 | exit ≠2 或产生产物 | exit 2 但 outdir 被创建 | exit 2、零产物、中文 stderr |
| 合法对照不受影响 | 10 | 对照组 exit ≠0 | 对照组产物不全 | exit 0、两产物齐全 |
"""))

# t08 trap/hard — strip 与日期格式边界
write(f"{OF}/t08/task.json", json.dumps({
    "id": "t08",
    "type": "trap",
    "difficulty": "hard",
    "instruction": "使用 office-templates 技能，对下面的周报数据 JSON 生成 文书.docx 与 fields.json。字段值包含前导/尾随空格、日期含前后空格、电话号码含横线。验证入文前 strip、标题公式精确匹配、落款日期裸日期无标签。",
    "nonce_input": {
        "description": "周报 strip 边界 JSON，内嵌",
        "data": {
            "部门": " 测试部 ",
            "填报人": "赵倩 ",
            "周期": " 第40周 ",
            "本周工作内容": ["  完成接口回归测试  "],
            "下周工作计划": ["启动性能压测"],
            "问题与需协调事项": ["需要运维配合扩容"],
            "报送日期": " 2026-10-08 "
        }
    },
    "expected": {"filled": 7, "title": "测试部工作周报", "basic_line": "填报人：赵倩　　周期：第40周", "date_value": "2026-10-08"},
    "design_note": "强裸模型通过率 ≤40%：裸模型会把前后空格原样带入标题（写成 ` 测试部 工作周报`）、把空格带入基本信息行、或在落款日期前后保留空格。SKILL.md §3.2 F5 明确规定入文前 strip。"
}, ensure_ascii=False, indent=2))

write(f"{OF}/t08/brief.md", """\
# brief — t08 strip 与日期格式边界

**任务摘要**：验证字段值入文前 strip、标题公式精确、落款日期裸日期无标签、电话号码含横线原样保留。

**可机判判据**：
- `title == "测试部工作周报"`（前后空格已 trim）
- 基本信息行为 `填报人：赵倩　　周期：第40周`（无首尾空格）
- `本周工作内容` 条目 `1．完成接口回归测试`（无首尾空格）
- 落款行 `报送日期：2026-10-08`（前后空格 trim）
- `fields.json` 中所有 `value` 均为 trim 后的字符串
""")

write(f"{OF}/t08/rubric.md", """\
# rubric — t08 strip 与日期格式边界

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 标题 strip | 25 | 标题含前后空格 | 标题正确但字体/居中错 | `测试部工作周报`、居中、黑体22pt |
| 基本信息行 strip | 20 | `填报人：` 或 `周期：` 值含空格 | 值正确但全角空格错 | `赵倩` 与 `第40周` 无首尾空格 |
| 列表条目 strip | 20 | 条目文本含首尾空格 | 部分正确 | 所有条目文本 trim |
| 落款日期 strip | 20 | 日期前后含空格 | 日期正确但带标签 | `2026-10-08` 裸日期、无标签 |
| fields.json value | 15 | value 含空格 | 部分 trim | 所有 value 均为 trim 后字符串 |
""")

print("office-templates-skill generated.")

# ============================================================
# hot-templates-skill
# ============================================================
HT = os.path.join(ROOT, "hot-templates-skill")

# t01 ability/basic — 抖音口播全填充
write(f"{HT}/t01/task.json", json.dumps({
    "id": "t01",
    "type": "ability",
    "difficulty": "basic",
    "instruction": "使用 hot-templates 技能，生成抖音口播爆款内容骨架（骨架.md + structure.json）到指定输出目录 <outdir>。",
    "nonce_input": {
        "platform": "dy",
        "topic": "通勤时间管理",
        "points": ["前一天晚上定好三件要事", "通勤路上只听行业播客不刷短视频", "到公司先花10分钟写当日清单"]
    },
    "expected": {"要素数": 6, "filled_from_input_topic": ["hook_3s"], "filled_from_input_points": ["value_1","value_2","value_3"], "open_placeholders_total": 2},
    "design_note": "强裸模型通过率 ≤55%：裸模型会把 hook_3s 的冻结文本改写、把 value_i 的‘第一/二/三招：’前缀漏写、或把 CTA 的冻结文本改写成通用祝福。必须逐字节对齐 frozen-tokens.md。"
}, ensure_ascii=False, indent=2))

write(f"{HT}/t01/brief.md", """\
# brief — t01 抖音口播全填充

**任务摘要**：抖音口播 6 要素，3 卖点全填充，验证冻结标记、卖点槽位、filled_from_input。

**可机判判据**：
- `structure.json` 含 6 个要素，id 顺序为 `hook_3s, pain_point, value_1, value_2, value_3, cta`
- `hook_3s.text` 含 `别划走！还在为「通勤时间管理」反复内耗的人`
- `value_i.text` 分别含三条卖点原文且以 `第一招：` `第二招：` `第三招：` 开头
- `cta.text` 含 `点赞收藏，评论区扣「1」`
- `open_placeholders` 去重后为 `["可替换为你的原创钩子强句，一句制造好奇或冲突","配套资料/下期选题"]`
- `骨架.md` 首行 `# 抖音口播稿 · 爆款骨架`
""")

write(f"{HT}/t01/rubric.md", """\
# rubric — t01 抖音口播全填充

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 6 要素结构与顺序 | 20 | 要素数≠6 或顺序错 | 顺序错但要素全 | id 顺序精确为 hook_3s/pain_point/value_1..3/cta |
| hook_3s 冻结文本 | 20 | 无主题代入或改写 | 主题代入但非冻结句 | `别划走！还在为「通勤时间管理」反复内耗的人` |
| value_i 冻结前缀与填充 | 25 | 无‘第X招：’前缀 | 前缀存在但卖点错 | 三槽位均以 `第一/二/三招：` 开头且含原文 |
| cta 冻结文本 | 20 | 无 CTA 冻结句 | 有 CTA 但非冻结句 | `点赞收藏，评论区扣「1」` |
| placeholder 与 filled_from_input | 15 | placeholder_count/text 重计数不一致 | 部分一致 | 自洽且 filled_from_input 含 topic/point#1..3 |
"""))

# t02 ability/basic — 小红书图文全填充
write(f"{HT}/t02/task.json", json.dumps({
    "id": "t02",
    "type": "ability",
    "difficulty": "basic",
    "instruction": "使用 hot-templates 技能，生成小红书图文爆款内容骨架（骨架.md + structure.json）到指定输出目录 <outdir>。",
    "nonce_input": {
        "platform": "xhs",
        "topic": "租房避坑指南",
        "points": ["签约前查房东房产证与身份证一致性", "押金条款写明退还条件与时限", "入住当天拍照录像留档"]
    },
    "expected": {"要素数": 7, "title_含_🔥_与_数字": True, "tag_count_正则": 6, "points_used_len": 3, "points_unused_len": 0},
    "design_note": "强裸模型通过率 ≤55%：裸模型会把 title 写成无 emoji 的普通标题、把 point_block 写成无 emoji 的段落、或把标签组写成少于 3 个。必须严格对齐 xhs.md 的 emoji 映射与标签冻结口径。"
}, ensure_ascii=False, indent=2))

write(f"{HT}/t02/brief.md", """\
# brief — t02 小红书图文全填充

**任务摘要**：小红书 7 要素，3 卖点全填充，验证标题 emoji+数字、emoji 映射、标签组冻结口径。

**可机判判据**：
- `structure.json` 含 7 个要素，id 顺序为 `title, hook_block, point_block_1, point_block_2, point_block_3, summary_block, tag_group`
- `title.text` 含 `🔥` 且含数字 `3`
- `hook_block.text` 以 `✅ 开头钩子` 开头
- `point_block_i.text` 以 `💡 干货N｜<卖点>` 开头
- `summary_block.text` 以 `📌 划重点` 开头
- `tag_group.text` 含 6 个 `#…` 标签（正则 `#[^\s#]+` 计数）
- `tag_group.text` 首标签由主题派生（`clean_tag` 后 = `租房避坑指南`）
""")

write(f"{HT}/t02/rubric.md", """\
# rubric — t02 小红书图文全填充

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 7 要素结构与顺序 | 15 | 要素数≠7 或顺序错 | 顺序错但要素全 | id 顺序精确 |
| title emoji+数字 | 20 | 无 🔥 或无数字 | 数字≠3 | `🔥` 与 `3` 均在 title |
| emoji 映射 | 25 | 任一要素 emoji 错 | 2处以内错 | hook=✅, point=💡, summary=📌, tag=🏷️ |
| 卖点槽位填充 | 20 | 卖点未进 point_block | 部分填充 | 三点原文分别在 point_block_1..3 |
| 标签组冻结口径 | 20 | 标签数≠6 或首标签非主题派生 | 标签数对但首标签错 | 6 标签、首标签 `#租房避坑指南` |
"""))

# t03 ability/basic — 公众号文章全填充
write(f"{HT}/t03/task.json", json.dumps({
    "id": "t03",
    "type": "ability",
    "difficulty": "basic",
    "instruction": "使用 hot-templates 技能，生成公众号文章爆款内容骨架（骨架.md + structure.json）到指定输出目录 <outdir>。",
    "nonce_input": {
        "platform": "wx",
        "topic": "非暴力沟通",
        "points": ["观察不评判", "感受需表达", "请求具体化"]
    },
    "expected": {"要素数": 5, "total_filled_from_input": 7, "golden_ending_含_共勉": True, "thesis_how_占位数": 0},
    "design_note": "强裸模型通过率 ≤55%：裸模型会把三段论写成无‘一、是什么’前缀的普通段落、漏掉 thesis_how 三抓手的‘N. 卖点——展开’结构、或在金句收尾漏掉‘共勉’。"
}, ensure_ascii=False, indent=2))

write(f"{HT}/t03/brief.md", """\
# brief — t03 公众号文章全填充

**任务摘要**：公众号 5 要素，3 卖点全填充，验证三段论冻结开头、thesis_how 三抓手同居、金句共勉、total_filled_from_input=7。

**可机判判据**：
- `structure.json` 含 5 个要素，id 顺序为 `lead_in, thesis_what, thesis_why, thesis_how, golden_ending`
- `thesis_what.text` 以 `一、是什么` 开头
- `thesis_why.text` 以 `二、为什么` 开头
- `thesis_how.text` 以 `三、怎么办\n落到操作层面，给你三个抓手：` 开头
- `thesis_how` 的三行分别为 `1. 观察不评判——…` `2. 感受需表达——…` `3. 请求具体化——…`
- `golden_ending.text` 含 `共勉`
- `total_filled_from_input == 7`
""")

write(f"{HT}/t03/rubric.md", """\
# rubric — t03 公众号文章全填充

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 5 要素结构与顺序 | 15 | 要素数≠5 或顺序错 | 顺序错但要素全 | id 顺序精确 |
| 三段论冻结开头 | 25 | 任一 thesis 开头非冻结句 | 两个正确 | 三句均以 `一、是什么` `二、为什么` `三、怎么办` 开头 |
| thesis_how 三抓手 | 25 | 三行不存在或格式错 | 两行正确 | 三行 `N. 卖点——【占位:展开…】` 结构齐全 |
| 金句共勉 | 15 | 无共勉 | 有共勉但结构错 | `「…」\\n共勉。` |
| total_filled_from_input | 20 | ≠7 | 计数逻辑错 | 满 3 卖点时 =7 |
"""))

# t04 ability/basic — 短视频分镜表全填充
write(f"{HT}/t04/task.json", json.dumps({
    "id": "t04",
    "type": "ability",
    "difficulty": "basic",
    "instruction": "使用 hot-templates 技能，生成短视频分镜表爆款内容骨架（骨架.md + structure.json）到指定输出目录 <outdir>。",
    "nonce_input": {
        "platform": "video",
        "topic": "居家哑铃入门",
        "points": ["用装满水的矿泉水瓶代替哑铃做划船", "手臂后举练三头", "平板支撑练核心"]
    },
    "expected": {"要素数": 6, "time_ranges": ["00:00-00:03","00:03-00:10","00:10-00:20","00:20-00:30","00:30-00:40","00:40-00:45"], "total_duration": 45, "table_header": "| 序号 | 时间轴 | 画面 | 口播 | 字幕 |"},
    "design_note": "强裸模型通过率 ≤55%：裸模型会把分镜时长配比改错（如 6 镜平均分配）、漏掉分镜总表节、或在 shot_i 名称中写成‘镜头1’而非冻结的‘分镜1（00:00-00:03）’。"
}, ensure_ascii=False, indent=2))

write(f"{HT}/t04/brief.md", """\
# brief — t04 短视频分镜表全填充

**任务摘要**：短视频 6 镜 45 秒，3 卖点全填充，验证时间轴冻结、四列表头、meta 7 键、分镜总表、卖点入 shot_3-5 口播列。

**可机判判据**：
- `structure.json` 含 6 个要素，id 为 `shot_1..shot_6`
- 各要素 `name` 为 `分镜<N>（<起>-<止>）`
- `meta.time_range` 依次为 6 个冻结时间轴
- 各镜 `text` 为一行表格 `| N | 起止 | 画面 | 口播 | 字幕 |`
- `骨架.md` 含 `## 分镜总表（时间轴 00:00-00:45，共 45 秒）`
- shot_3/4/5 口播列分别含三条卖点原文，且以 `第X招，` 开头
""")

write(f"{HT}/t04/rubric.md", """\
# rubric — t04 短视频分镜表全填充

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 6 镜结构与名称 | 20 | 镜数≠6 或名称格式错 | 名称格式错但时长对 | name 冻结为 `分镜<N>（<起>-<止>）` |
| 时间轴冻结 | 25 | 任一镜时间轴错 | 两镜以内错 | 6 个时间轴完全匹配冻结值 |
| 四列表头与行格式 | 20 | 表头列数≠5 或行格式错 | 表头正确但行格式错 | 表头与行均为 `| N | 起止 | 画面 | 口播 | 字幕 |` |
| meta 7 键 | 15 | 任一镜缺少 meta 键 | 3键以内缺失 | 每镜 7 键齐全 |
| 分镜总表 | 10 | 无总表节 | 有总表但时间轴错 | `## 分镜总表（时间轴 00:00-00:45，共 45 秒）` |
| 卖点槽位填充 | 10 | shot_3-5 口播未含卖点 | 部分填充 | 三卖点分别在 shot_3/4/5 口播列且以 `第X招，` 开头 |
"""))

# t05 boundary/edge — 四平台零卖点
write(f"{HT}/t05/task.json", json.dumps({
    "id": "t05",
    "type": "boundary",
    "difficulty": "edge",
    "instruction": "使用 hot-templates 技能，分别对以下四组输入（points=[]）各执行一次生成，产物写入同一输出目录的四个子目录（dy/ xhs/ wx/ video）。重点验证零卖点时各平台占位符的正确落位与 open_placeholders 计数。",
    "nonce_input": {
        "description": "四平台零卖点输入，内嵌。注意一次一跑，共四次执行。",
        "cases": [
            {"platform": "dy", "topic": "居家哑铃入门", "points": []},
            {"platform": "xhs", "topic": "租房避坑指南", "points": []},
            {"platform": "wx", "topic": "非暴力沟通", "points": []},
            {"platform": "video", "topic": "居家哑铃入门", "points": []}
        ]
    },
    "expected": {
        "dy_open": 6,
        "xhs_open": 7,
        "wx_open": 10,
        "video_open": 18,
        "wx_total_filled_from_input": 4,
        "video_shot_3_5_extra_value_count": 6
    },
    "design_note": "强裸模型通过率 ≤40%：裸模型会把零卖点处理成空字符串而不是 `【占位:价值点N】`、漏掉 xhs summary_block 的占位复述、或不知道 wx 的 total_filled_from_input 在零卖点时应为 4。"
}, ensure_ascii=False, indent=2))

write(f"{HT}/t05/brief.md", """\
# brief — t05 四平台零卖点边界

**任务摘要**：四平台各执行一次，points=[]，验证占位符正确落位与 open_placeholders 冻结计数。

**可机判判据**：
- dy：value_1/2/3 均含 `【占位:价值点1/2/3】`，`open_placeholders` 去重后长度=6
- xhs：point_block_1/2/3 均含 `【占位:价值点1/2/3】`，summary_block 复述句也含占位值，`open_placeholders` 长度=7
- wx：thesis_how 三抓手行均为 `N. 【占位:价值点N】——【占位:展开…】`，`open_placeholders` 去重后长度=10，`total_filled_from_input=4`
- video：shot_3/4/5 的口播列与字幕列均含 `价值点2/3`（缺失槽位额外出现），`open_placeholders` 长度=18
""")

write(f"{HT}/t05/rubric.md", """\
# rubric — t05 四平台零卖点边界

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| dy 占位与计数 | 25 | value_i 无占位或 open≠6 | 占位存在但计数错 | value_i 三占位 + hook/pain/cta 各一槽位 =6 |
| xhs 占位与计数 | 25 | point_block 无占位或 summary 未复述占位 | 占位存在但 open≠7 | 三干货块+summary+title+hook+tag=7 |
| wx 占位与计数 | 25 | thesis_how 无三占位或 total_filled≠4 | 占位存在但格式错 | 三抓手占位 + lead_in/thesis_what/thesis_why/golden_ending 各一槽位 =10，total_filled=4 |
| video 占位与计数 | 25 | shot_3-5 无额外价值点N或 open≠18 | 占位存在但时长/镜号错 | 每缺一卖点口播+字幕各多一占位，总 open=18 |
"""))

# t06 boundary/edge — topic 特殊字符
write(f"{HT}/t06/task.json", json.dumps({
    "id": "t06",
    "type": "boundary",
    "difficulty": "edge",
    "instruction": "使用 hot-templates 技能，生成抖音口播爆款内容骨架到指定输出目录 <outdir>。topic 含全角引号、括号、点号与 emoji，验证 clean_tag、标题代入、hook_3s 主题替换。",
    "nonce_input": {
        "platform": "dy",
        "topic": "Python 3.12「新特性」与异步编程",
        "points": ["asyncio.TaskGroup", "contextvars跨线程传递", "exception group统一捕获"]
    },
    "expected": {"topic_in_hook": "Python 3.12「新特性」与异步编程", "clean_tag_topic": "Python312新特性与异步编程", "filled_from_input_topic": ["hook_3s"]},
    "design_note": "强裸模型通过率 ≤45%：裸模型会错误 clean_tag（把 `「」` 当成空白 stripping 掉）、或在 hook_3s 中漏代 topic、或在 title/tag_group 中 clean_tag 不一致。frozen-tokens.md 规定 clean_tag 正则 `[\\s#]+` 替换为空。"
}, ensure_ascii=False, indent=2))

write(f"{HT}/t06/brief.md", """\
# brief — t06 topic 特殊字符边界

**任务摘要**：topic 含全角引号、括号、点号与 emoji，验证 clean_tag、主题冻结替换、filled_from_input。

**可机判判据**：
- `hook_3s.text` 含 `别划走！还在为「Python 3.12「新特性」与异步编程」反复内耗的人`
- `structure.json.topic == "Python 3.12「新特性」与异步编程"`
- `tag_group.text` 首标签经 clean_tag 后为 `#Python312新特性与异步编程`
- `points_used` 为三条原文，`points_unused` 为空数组
- `filled_from_input` 中 topic 相关项含原始 topic 字符串
""")

write(f"{HT}/t06/rubric.md", """\
# rubric — t06 topic 特殊字符边界

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| hook_3s 主题冻结替换 | 25 | 未代入 topic 或删除全角引号 | 代入但 hook 冻结句错 | `「Python 3.12「新特性」与异步编程」` 完整保留 |
| clean_tag 一致性 | 25 | tag_group 首标签 clean_tag 错 | clean_tag 正则应用不一致 | `Python312新特性与异步编程` |
| topic 字段原样保留 | 20 | topic 被 trim 或改写 | 部分改写 | `structure.json.topic` 与输入 topic 逐字一致 |
| 卖点填充与计数 | 20 | 卖点错或 points_unused 非空 | 部分正确 | points_used 为三条原文，points_unused 为空 |
| filled_from_input 语义 | 10 | filled_from_input 不含 topic/point#N | 部分正确 | 语义与 frozen-tokens.md 一致 |
"""))

# t07 trap/hard — 五卖点截断
write(f"{HT}/t07/task.json", json.dumps({
    "id": "t07",
    "type": "trap",
    "difficulty": "hard",
    "instruction": "使用 hot-templates 技能，生成小红书图文爆款内容骨架到指定输出目录 <outdir>。points 共 5 条，验证仅前 3 条进正文、第 4-5 条原文完整且保序记入 points_unused。",
    "nonce_input": {
        "platform": "xhs",
        "topic": "职场复盘",
        "points": ["写清单", "对数据", "复盘会", "找导师", "练表达"]
    },
    "expected": {"points_used": ["写清单", "对数据", "复盘会"], "points_unused": ["找导师", "练表达"], "points_input_count": 5, "point_block_4_5_not_in_text": True},
    "design_note": "强裸模型通过率 ≤35%：裸模型会把 5 条卖点全部塞进正文（违反‘恰好 3 个价值点槽位’）、或只截断前 3 条但打乱 points_unused 顺序、或漏记 points_unused。SKILL.md §3.1 明确规定超过 3 条取前 3，第 4 起保序记入 points_unused。"
}, ensure_ascii=False, indent=2))

write(f"{HT}/t07/brief.md", """\
# brief — t07 五卖点截断

**任务摘要**：小红书 5 条卖点，验证前 3 条进正文、第 4-5 条保序记入 points_unused。

**可机判判据**：
- `structure.json.points_used` 为 `["写清单","对数据","复盘会"]`
- `structure.json.points_unused` 为 `["找导师","练表达"]`
- `structure.json.points_input_count == 5`
- `point_block_1/2/3.text` 分别含三条卖点原文
- `point_block_4/5` 不存在
- `骨架.md` 中无第 4/5 条卖点出现在正文
""")

write(f"{HT}/t07/rubric.md", """\
# rubric — t07 五卖点截断

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| points_used 截断 | 35 | points_used 长度≠3 或含第 4/5 条 | 长度=3 但顺序错 | 恰为前 3 条原文 |
| points_unused 保序 | 30 | points_unused 为空或顺序错 | 顺序错但内容对 | 保序且完整为第 4/5 条 |
| points_input_count | 15 | ≠5 | 计数逻辑错 | =5 |
| 正文无溢出 | 10 | 第 4/5 条出现在 point_block | 出现在 summary 或 tag | 正文仅含前 3 条 |
| 结构自洽 | 10 | points_used+points_unused 总长≠5 | 部分自洽 | 总计 5 条，无遗漏无溢出 |
"""))

# t08 trap/hard — 非法 platform 与空白 topic
write(f"{HT}/t08/task.json", json.dumps({
    "id": "t08",
    "type": "trap",
    "difficulty": "hard",
    "instruction": "使用 hot-templates 技能，对下面两组非法输入分别执行一次生成，观察退出码、stderr 与输出目录是否被创建。",
    "nonce_input": {
        "description": "两组非法输入，内嵌",
        "cases": [
            {"platform": "bilibili", "topic": "测试", "points": ["a"]},
            {"platform": "dy", "topic": "  ", "points": ["a"]}
        ]
    },
    "expected": {"每组退出码": 2, "产物残留数": 0, "stderr_含错误标记": True},
    "design_note": "强裸模型通过率 ≤30%：裸模型不知道 hot-templates 的 CLI 契约（仅四 platform 合法、topic strip 后非空），会尝试生成或编造产物。SKILL.md §3.1/§4 明确 illegal platform exit 2、空白 topic exit 2。"
}, ensure_ascii=False, indent=2))

write(f"{HT}/t08/brief.md", """\
# brief — t08 非法 platform 与空白 topic

**任务摘要**：验证非法 platform（bilibili）与空白 topic（strip 后为空）均触发 exit 2 且零产物。

**可机判判据**：
- bilibili 组退出码 = `2`，输出目录未被创建
- 空白 topic 组退出码 = `2`，输出目录未被创建
- 两组 stderr 均含 `[gen.py] 错误：` 或 argparse 英文报错
- 合法对照组（platform=dy, topic=测试, points=["a"]）退出码 = 0 且产物齐全
""")

write(f"{HT}/t08/rubric.md", """\
# rubric — t08 非法 platform 与空白 topic

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 非法 platform | 50 | exit ≠2 或产生产物 | exit 2 但 outdir 被创建 | exit 2、零产物 |
| 空白 topic | 40 | exit ≠2 或产生产物 | exit 2 但 outdir 被创建 | exit 2、零产物 |
| 合法对照不受影响 | 10 | 对照组 exit ≠0 | 产物不全 | exit 0、骨架.md + structure.json 齐全 |
""")

print("hot-templates-skill generated.")
