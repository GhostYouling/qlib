# Campaign161 债务期限结构因子最终有效终态报告

科学终态未变化：`eastmoney_debt_maturity_resilience` 在一次性 2023-Q4 Eastmoney 来源验收中因响应缺少必需 `result` 对象而终止。没有 provider 行、因子值、比较器、日线或 forward return 被读取或保存；2019–2023 下游开发和 2024–2025 均未打开，来源请求不得重试或换字段救援。

最终回归首次命令使用了与实际收集 id 不同的 `tests/` 前缀，并遗漏 Campaign145 已知历史可追加报告绑定节点，因此两项历史生命周期断言运行并失败，其余 `304 passed, 1 skipped`。使用准确的 `data_collector_tests/` node id 后，回归为 `304 passed, 1 skipped, 2 deselected`。该非零退出追加为第 11 次基础设施失败。

Campaign161 最终有效会计为 17 次尝试（6 科学、11 基础设施），累计历史尝试 1413，收益读取开发试验仍为 314。定义/数值比较器保持 `158/142`，Candidate49 两本空账本不变，目标继续 active。有效终态记录为 `docs/a_share_three_day_walkforward_campaign_161_terminal_result_v4_20260815.json`（SHA-256 `4517464eec7d68916c818244262d24bb381f024c9a019697258d3ff69c6b1684`）。
