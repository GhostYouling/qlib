# Campaign161 债务期限结构因子有效终态报告 v2

Campaign161 的科学结论不变：唯一冻结的 higher 定义 `eastmoney_debt_maturity_resilience` 在一次性 2023-Q4 Eastmoney 来源验收中因响应缺少必需 `result` 对象而终止。没有读取或保存 provider 行、因子值、比较器、日线或 forward return；2019–2023 下游开发和 2024–2025 均未打开，来源请求不得重试或改字段救援。

本版只追加发布验证会计。新终态测试首次 Black 检查退出 1，链式 Ruff/pytest 当时没有运行；机械格式化后 Ruff 通过，Campaign161 公式/来源生命周期/终态聚焦测试共 `14 passed`。该失败记为第 7 次基础设施尝试，因此 Campaign161 有效会计为 13 次尝试（6 科学、7 基础设施），累计历史尝试 1409，收益读取开发试验仍为 314。

定义/数值比较器保持 `158/142`，Candidate49 两本空账本不变，目标继续 active。有效终态记录为 `docs/a_share_three_day_walkforward_campaign_161_terminal_result_v2_20260815.json`（SHA-256 `3682f007b23628ed23f4cbbe9224030956d06c592f4d06e8dcbc2afb7c8f7087`）。
