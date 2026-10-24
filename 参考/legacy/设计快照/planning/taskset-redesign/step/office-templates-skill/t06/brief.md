# brief — t06 请示函必填缺失 + unknown_keys

任务摘要：验证必填缺失渲染 ____、选填缺失留空、unknown_keys 记账。

可机判判据：
- 称谓为 ____：（主送机关必填缺失）
- 请示事项段为 ____（请示事项空字符串）
- 联系行为 联系人：李工　　联系电话：
- 落款一 测试部 右对齐，落款二为空段
- fields.json.summary.unknown_keys == [备注]
- fields.json.summary.missing_required_names == [主送机关,请示事项]
