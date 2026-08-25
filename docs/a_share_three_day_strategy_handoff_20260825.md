# A股三日短线策略研究交接（截至 Campaign298）

当前已完成到 Campaign298，持续研究目标仍为 active。最新因子 `alpha158_volume_coefficient_of_variation_20d = VSTD20 / VMA20` 通过覆盖和 150/150 唯一性门；2021–2023 的 Rank IC 2/3 为正、归一化收益 3/3 为正、10bp 2/3 为正，但最差归一化回撤 -50.39%、复合 20bp 收益 -1.51%，开发幸存者仍为 0。2024–2025 未打开，当前没有可部署的新策略。

权威交接请从 [Campaign298 交接文档](a_share_three_day_strategy_handoff_20260825_campaign298.md) 开始；终态报告为 [Campaign298 终端报告](a_share_three_day_walkforward_campaign_298_terminal_report.md)，最新状态为 `a_share_three_day_iteration_status_20260825_campaign298_terminal.json`，最新重复控制库政策为 `a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v428_20260825.json`。

历史完整定义/数值比较器库更新为 `170/151`。Campaign298 只因覆盖和唯一性通过而追加，追加不代表开发幸存或投资价值；不得反向、改变二十日窗口、单独测试 VSTD/VMA、加 epsilon/log/裁剪/阈值或与旧因子组合救援。

Candidate49 仍是唯一活动前瞻候选，账本保持 0/0。2026-08-25 只读 plan 已失败关闭，未运行且不得同日重试。历史结果不得生成当前评分、选股、仓位或订单。本地 Campaign298 证据位于 `.local-research/campaign_298/`，受忽略规则保护，不要移动、清理或强制提交。

复核：

```bash
python -m scripts.a_share_three_day_walkforward_campaign298 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign298.py
```

下一步 Campaign299 只能先冻结新的有限、机制独立、零网络离线概念目录，并继续以 `170/151` 库做值前重叠检查；不得围绕 Campaign298 的成交量变异系数、方向、窗口或变换做邻域搜索。本交接是研究记录，不构成投资建议。
