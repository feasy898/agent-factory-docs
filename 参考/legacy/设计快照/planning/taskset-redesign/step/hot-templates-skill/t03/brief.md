# brief — t03 公众号文章全填充

任务摘要：公众号 5 要素，3 卖点全填充，验证三段论冻结开头、thesis_how 三抓手同居、金句共勉、total_filled_from_input=7。

可机判判据：
- structure.json 含 5 个要素，id 顺序为 lead_in, thesis_what, thesis_why, thesis_how, golden_ending
- thesis_what.text 以 一、是什么 开头
- thesis_why.text 以 二、为什么 开头
- thesis_how.text 以 三、怎么办
落到操作层面，给你三个抓手： 开头
- thesis_how 的三行分别为 1. 观察不评判——… 2. 感受需表达——… 3. 请求具体化——…
- golden_ending.text 含 共勉
- total_filled_from_input == 7
