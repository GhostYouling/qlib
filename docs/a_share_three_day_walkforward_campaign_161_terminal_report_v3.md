# Campaign161 债务期限结构因子有效终态报告 v3

科学终态仍未变化：唯一的新定义 `eastmoney_debt_maturity_resilience` 在一次性 2023-Q4 Eastmoney 来源验收中因响应缺少必需 `result` 对象而终止。没有 provider 行、因子值、比较器、日线或 forward return 被读取或保存；2019–2023 下游开发和 2024–2025 均未打开，来源请求不得重试或换字段救援。

本版继续追加发布基础设施会计：两次大范围终态测试补丁因格式化后的上下文不匹配而在零部分写入下失败；拆成精确小补丁后恢复。随后聚焦测试 `13 passed, 1 failed`，唯一失败是终态 v2 对测试文件的旧摘要形成生命周期绑定；有效 v3 不再循环绑定仍在更新的测试，最终测试摘要只由验证回执在测试冻结后记录。

Campaign161 有效会计为 16 次尝试（6 科学、10 基础设施），累计历史尝试 1412，收益读取开发试验仍为 314。定义/数值比较器保持 `158/142`，Candidate49 两本空账本不变，目标继续 active。有效终态记录为 `docs/a_share_three_day_walkforward_campaign_161_terminal_result_v3_20260815.json`（SHA-256 `79714b0ce700d790dd95d439fa427c167b7b91dd1d8cc264e43d548a28e18360`）。
