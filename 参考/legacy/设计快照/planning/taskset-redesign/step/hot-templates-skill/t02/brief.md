# brief — t02 小红书图文全填充

任务摘要：小红书 7 要素，3 卖点全填充，验证标题 emoji+数字、emoji 映射、标签组冻结口径。

可机判判据：
- structure.json 含 7 个要素，id 顺序为 title, hook_block, point_block_1, point_block_2, point_block_3, summary_block, tag_group
- title.text 含 🔥 且含数字 3
- hook_block.text 以 ✅ 开头钩子 开头
- point_block_i.text 以 💡 干货N｜<卖点> 开头
- summary_block.text 以 📌 划重点 开头
- tag_group.text 含 6 个 #… 标签（正则 #[^\s#]+ 计数）
- tag_group.text 首标签由主题派生（clean_tag 后 = 租房避坑指南）
