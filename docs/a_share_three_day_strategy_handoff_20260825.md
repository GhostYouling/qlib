# A股三日短线策略研究交接（截至 Campaign292）

当前已完成到 Campaign292，持续研究目标仍为 active。最新因子 `alpha158_session_peer_rank_extremity_breadth_1d` 通过覆盖和 145/145 去重，但 2021–2023 三折 Rank IC 与标准化收益均全负，前两折整手可负担率不足，存活者为 0，2024–2025 没有打开，当前没有可部署的新策略。

权威交接请从 [Campaign292 交接文档](a_share_three_day_strategy_handoff_20260825_campaign292.md) 开始；终态报告为 [Campaign292 终端报告](a_share_three_day_walkforward_campaign_292_terminal_report.md)，最新状态为 `a_share_three_day_iteration_status_20260825_campaign292_terminal.json`，最新重复控制库政策为 `a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v422_20260825.json`。

历史完整定义/数值比较器库现为 `165/146`。Campaign292 因通过无收益门而被保留用于以后防重复，但其收益方向已经科学终止；不得反向、改同行百分位、居中极端度、119 支持、权重或与 Campaign290/291 组合进行事后挽救。

Candidate49 仍是唯一活动前瞻候选，信号/执行账本保持 0/0，禁止历史回填和第二个前瞻候选。历史结果不得生成当前评分、选股、仓位或订单。本地研究证据位于 `data/experiments/short_horizon/historical_walkforward/campaign_292/alpha158_session_peer_rank_extremity_breadth_v2/`，失败的 v1 输出也必须保留；两者都受忽略规则保护，不要移动、清理或强制提交。

复核：

```bash
MPLCONFIGDIR=/private/tmp/campaign292-mpl PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m scripts.a_share_three_day_walkforward_campaign292 verify
MPLCONFIGDIR=/private/tmp/campaign292-mpl PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign292.py
```

下一步 Campaign293 只能先冻结新的有限、机制独立、零网络离线概念目录，并以 `165/146` 库做值前重叠检查；不得围绕 Campaign292 调参、改方向或组合救援。本交接是研究记录，不构成投资建议。
