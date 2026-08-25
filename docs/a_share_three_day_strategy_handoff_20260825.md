# A股三日短线策略研究交接（截至 Campaign299）

当前已完成到 Campaign299，持续研究目标仍为 active。最新因子 `alpha158_close_distribution_upper_tail_asymmetry_20d = (2*MA20-QTLU20-QTLD20)/(QTLU20-QTLD20)` 通过覆盖和 151/151 唯一性门，但 2021–2023 的 Rank IC、归一化收益和 10bp 收益全部为负；复合归一化收益 -64.50%、10bp -14.85%、20bp -19.36%，最差归一化回撤 -46.60%，开发幸存者仍为 0。2024–2025 未打开，当前没有可部署的新策略。

权威交接请从 [Campaign299 交接文档](a_share_three_day_strategy_handoff_20260825_campaign299.md) 开始；终态报告为 [Campaign299 终端报告](a_share_three_day_walkforward_campaign_299_terminal_report.md)，最新状态为 `a_share_three_day_iteration_status_20260825_campaign299_terminal.json`，最新重复控制库政策为 `a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v429_20260825.json`。

历史完整定义/数值比较器库更新为 `171/152`。Campaign299 只因覆盖和唯一性通过而追加，追加不代表开发幸存或投资价值；不得根据三折同向负结果反向、改变二十日窗口、重组 MA/QTLU/QTLD、加 epsilon/绝对值/裁剪/阈值或与旧因子组合救援。

Candidate49 仍是唯一活动前瞻候选，账本保持 0/0。2026-08-25 只读 plan 已失败关闭，未运行且不得同日重试。历史结果不得生成当前评分、选股、仓位或订单。本地 Campaign299 证据位于 `.local-research/campaign_299/`，受忽略规则保护，不要移动、清理或强制提交。

复核：

```bash
python -m scripts.a_share_three_day_walkforward_campaign299 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign299.py
```

下一步 Campaign300 只能先冻结新的有限、机制独立、零网络离线概念目录，并继续以 `171/152` 库做值前重叠检查；不得围绕 Campaign299 的收盘分布不对称、方向、窗口或变换做邻域搜索。本交接是研究记录，不构成投资建议。
