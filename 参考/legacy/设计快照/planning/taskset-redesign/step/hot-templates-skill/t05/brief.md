# brief — t05 四平台零卖点边界

任务摘要：四平台各执行一次，points=[]，验证占位符正确落位与 open_placeholders 冻结计数。

可机判判据：
- dy：value_1/2/3 均含 【占位:价值点1/2/3】，open_placeholders 去重后长度=6
- xhs：point_block_1/2/3 均含 【占位:价值点1/2/3】，summary_block 复述句也含占位值，open_placeholders 长度=7
- wx：thesis_how 三抓手行均为 N. 【占位:价值点N】——【占位:展开...】，open_placeholders 去重后长度=10，total_filled_from_input=4
- video：shot_3/4/5 的口播列与字幕列均含 价值点2/3（缺失槽位额外出现），open_placeholders 长度=18
