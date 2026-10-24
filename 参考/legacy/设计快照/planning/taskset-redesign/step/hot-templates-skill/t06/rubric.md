# rubric — t06 topic 特殊字符边界

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| hook_3s 主题冻结替换 | 25 | 未代入 topic 或删除全角引号 | 代入但 hook 冻结句错 | 「Python 3.12「新特性」与异步编程」 完整保留 |
| clean_tag 一致性 | 25 | tag_group 首标签 clean_tag 错 | clean_tag 正则应用不一致 | Python312新特性与异步编程 |
| topic 字段原样保留 | 20 | topic 被 trim 或改写 | 部分改写 | structure.json.topic 与输入 topic 逐字一致 |
| 卖点填充与计数 | 20 | 卖点错或 points_unused 非空 | 部分正确 | points_used 为三条原文，points_unused 为空 |
| filled_from_input 语义 | 10 | filled_from_input 不含 topic/point#N | 部分正确 | 语义与 frozen-tokens.md 一致 |
