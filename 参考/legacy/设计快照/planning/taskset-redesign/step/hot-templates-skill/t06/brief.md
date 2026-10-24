# brief — t06 topic 特殊字符边界

任务摘要：topic 含全角引号、括号、点号与 emoji，验证 clean_tag、主题冻结替换、filled_from_input。

可机判判据：
- hook_3s.text 含 别划走！还在为「Python 3.12「新特性」与异步编程」反复内耗的人
- structure.json.topic == Python 3.12「新特性」与异步编程
- tag_group.text 首标签经 clean_tag 后为 #Python312新特性与异步编程
- points_used 为三条原文，points_unused 为空数组
- filled_from_input 中 topic 相关项含原始 topic 字符串
