# brief — t01 抖音口播全填充

任务摘要：抖音口播 6 要素，3 卖点全填充，验证冻结标记、卖点槽位、filled_from_input。

可机判判据：
- structure.json 含 6 个要素，id 顺序为 hook_3s, pain_point, value_1, value_2, value_3, cta
- hook_3s.text 含 别划走！还在为「通勤时间管理」反复内耗的人
- value_i.text 分别含三条卖点原文且以 第一招： 第二招： 第三招： 开头
- cta.text 含 点赞收藏，评论区扣「1」
- open_placeholders 去重后为 ["可替换为你的原创钩子强句，一句制造好奇或冲突","配套资料/下期选题"]
- 骨架.md 首行 # 抖音口播稿 · 爆款骨架
