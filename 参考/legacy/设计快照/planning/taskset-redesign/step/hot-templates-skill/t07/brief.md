# brief — t07 五卖点截断

任务摘要：小红书 5 条卖点，验证前 3 条进正文、第 4-5 条保序记入 points_unused。

可机判判据：
- structure.json.points_used 为 [写清单,对数据,复盘会]
- structure.json.points_unused 为 [找导师,练表达]
- structure.json.points_input_count == 5
- point_block_1/2/3.text 分别含三条卖点原文
- point_block_4/5 不存在
- 骨架.md 中无第 4/5 条卖点出现在正文
