# rubric — t07 五卖点截断

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| points_used 截断 | 35 | points_used 长度!=3 或含第 4/5 条 | 长度=3 但顺序错 | 恰为前 3 条原文 |
| points_unused 保序 | 30 | points_unused 为空或顺序错 | 顺序错但内容对 | 保序且完整为第 4/5 条 |
| points_input_count | 15 | !=5 | 计数逻辑错 | =5 |
| 正文无溢出 | 10 | 第 4/5 条出现在 point_block | 出现在 summary 或 tag | 正文仅含前 3 条 |
| 结构自洽 | 10 | points_used+points_unused 总长!=5 | 部分自洽 | 总计 5 条，无遗漏无溢出 |
