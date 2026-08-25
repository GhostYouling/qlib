# A股三日短线策略研究交接（截至 Campaign295）

当前已完成到 Campaign295，持续研究目标仍为 active。最新因子 `alpha158_price_volume_directional_confirmation_20d` 通过覆盖和 147/147 唯一性门，但 2021–2023 三折的 mean Rank IC、标准化收益和 10bp 收益全部为负，开发幸存者为 0；2024–2025 未打开，当前没有可部署的新策略。

权威交接请从 [Campaign295 交接文档](a_share_three_day_strategy_handoff_20260825_campaign295.md) 开始；终态报告为 [Campaign295 终端报告](a_share_three_day_walkforward_campaign_295_terminal_report.md)，最新状态为 `a_share_three_day_iteration_status_20260825_campaign295_terminal.json`，最新重复控制库政策为 `a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v425_20260825.json`。

历史完整定义/数值比较器库更新为 `167/148`。Campaign295 只因覆盖和唯一性通过而追加，追加不代表开发幸存或投资价值；不得反向、改 20 日 horizon、改变 CORD 确认权重、阈值化或与旧因子组合救援。

Candidate49 仍是唯一活动前瞻候选，账本保持 0/0。2026-08-25 只读 plan 已失败关闭，未运行且不得同日重试。历史结果不得生成当前评分、选股、仓位或订单。本地 Campaign295 v1/v2 证据均位于 `.local-research/campaign_295/`，受忽略规则保护，不要移动、清理或强制提交。

复核：

```bash
python -m scripts.a_share_three_day_walkforward_campaign295 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign295.py
```

下一步 Campaign296 只能先冻结新的有限、机制独立、零网络离线概念目录，并继续以 `167/148` 库做值前重叠检查；不得围绕 Campaign295 的价格方向、成交量确认、horizon、方向或权重做邻域搜索。本交接是研究记录，不构成投资建议。
