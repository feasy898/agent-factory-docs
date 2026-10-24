# rubric — t07 非法输入拒绝

| 维度 | 权重 | 0 分 | 6 分 | 10 分 |
|---|---|---|---|---|
| 非法模板名 | 25 | exit !=2 或产生产物 | exit 2 但 stderr 无中文 | exit 2、零产物、中文 stderr |
| 文件不存在 | 25 | exit !=2 或产生产物 | exit 2 但 outdir 被创建 | exit 2、零产物、中文 stderr |
| JSON 解析失败 | 25 | exit !=2 或产生产物 | exit 2 但 outdir 被创建 | exit 2、零产物、中文 stderr |
| 顶层非对象 | 15 | exit !=2 或产生产物 | exit 2 但 outdir 被创建 | exit 2、零产物、中文 stderr |
| 合法对照不受影响 | 10 | 对照组 exit !=0 | 对照组产物不全 | exit 0、两产物齐全 |
