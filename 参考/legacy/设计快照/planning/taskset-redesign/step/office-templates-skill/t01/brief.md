# brief — t01 周报全字段标准生成

任务摘要：周报七字段齐全，验证标题公式、基本信息行、两节必填列表、选填小节、落款。

可机判判据：
- fields.json 顶层键集合与 SKILL.md §5 一致：template/title/filled_fields/missing_fields/fields/summary/outputs
- summary.filled == 7 且 summary.missing_required == []
- title == 测试部工作周报
- 文书.docx 标题居中黑体二号；段落顺序：标题->基本信息行->一、本周工作内容->二、下周工作计划->三、问题与需协调事项->报送日期
- 落款行 报送日期：2026-10-08 右对齐且右缩进两字
