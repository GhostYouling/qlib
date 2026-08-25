# A股三日短线策略研究交接（截至 Campaign293）

当前已完成到 Campaign293，持续研究目标仍为 active。最新因子 `alpha158_multi_horizon_peer_rank_smoothness_29g` 通过覆盖和 146/146 去重，但三折复合标准化/10bp/20bp 收益为 -30.79%/-5.04%/-9.79%，存活者为 0，2024–2025 没有打开，当前没有可部署的新策略。

权威交接请从 [Campaign293 交接文档](a_share_three_day_strategy_handoff_20260825_campaign293.md) 开始；终态报告为 [Campaign293 终端报告](a_share_three_day_walkforward_campaign_293_terminal_report.md)，最新状态为 `a_share_three_day_iteration_status_20260825_campaign293_terminal.json`，最新重复控制库政策为 `a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v423_20260825.json`。

历史完整定义/数值比较器库现为 `166/147`。Campaign293 因通过无收益门而被保留用于以后防重复，但其收益方向已经科学终止；不得反向、改 horizon、22 家族支持、权重或与 Campaign290–292 组合进行事后挽救。

Candidate49 仍是唯一活动前瞻候选，信号/执行账本保持 0/0，禁止历史回填和第二个前瞻候选。历史结果不得生成当前评分、选股、仓位或订单。本地研究证据位于 `.local-research/campaign_293/alpha158_multi_horizon_peer_rank_smoothness_v2/`，失败的 v1 输出位于 `data/experiments/short_horizon/historical_walkforward/campaign_293/alpha158_multi_horizon_peer_rank_smoothness_v1/`；两者都受忽略规则保护，不要移动、清理或强制提交。

复核：

```bash
PYTHONPATH=. python -m scripts.a_share_three_day_walkforward_campaign293 verify
PYTHONPATH=. python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign293.py
```

下一步 Campaign294 只能先冻结新的有限、机制独立、零网络离线概念目录，并以 `166/147` 库做值前重叠检查；不得围绕 Campaign293 调参、改方向或组合救援。本交接是研究记录，不构成投资建议。
