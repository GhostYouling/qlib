# A股三日短线策略研究交接（截至 Campaign300）

当前已完成到 Campaign300，持续研究目标仍为 active。最新因子 `alpha158_conditional_return_magnitude_asymmetry_20d` 通过覆盖和 152/152 唯一性门，但 2021–2023 Rank IC 三折全负；复合归一化收益 -31.12%、10bp -4.36%、20bp -8.76%，最差归一化回撤 -39.41%，且一折整手可负担率低于 90%，开发幸存者为 0。2024–2025 未打开，当前没有可部署的新策略。

权威交接请从 [Campaign300 交接文档](a_share_three_day_strategy_handoff_20260825_campaign300.md) 开始；终态报告为 [Campaign300 终端报告](a_share_three_day_walkforward_campaign_300_terminal_report.md)，最新状态为 `a_share_three_day_iteration_status_20260825_campaign300_terminal.json`，最新重复控制库政策为 `a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v430_20260825.json`。

历史完整定义/数值比较器库更新为 `172/153`。Campaign300 只因覆盖和唯一性通过而追加，追加不代表开发幸存或投资价值；不得根据负结果反向、改变二十日窗口、改写条件幅度公式、加 epsilon/绝对值/裁剪/阈值或与旧因子组合救援。

Candidate49 仍是唯一活动前瞻候选，账本保持 0/0。2026-08-25 只读 plan 已失败关闭，未运行且不得同日重试。历史结果不得生成当前评分、选股、仓位或订单。本地 Campaign300 证据位于 `.local-research/campaign_300/`，受忽略规则保护，不要移动、清理或强制提交。

复核：

```bash
python -m scripts.a_share_three_day_walkforward_campaign300 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign300.py
```

下一步 Campaign301 只能先冻结新的有限、机制独立、零网络离线概念目录，并继续以 `172/153` 库做值前重叠检查；不得围绕 Campaign300 的条件涨跌幅强度比、方向、窗口或变换做邻域搜索。本交接是研究记录，不构成投资建议。
