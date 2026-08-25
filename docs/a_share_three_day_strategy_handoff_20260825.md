# A股三日短线策略研究交接（截至 Campaign291）

当前已完成到 Campaign291，持续研究目标仍为 active。最新因子 `alpha158_session_median_state_consensus_strength_1d` 通过覆盖和 144/144 去重，但只有 1/3 折 Rank IC 为正，2021–2023 三折标准化收益及 10bp/20bp 收益均为负，存活者为 0，2024–2025 没有打开，当前没有可部署的新策略。

权威交接请从 [Campaign291 交接文档](a_share_three_day_strategy_handoff_20260825_campaign291.md) 开始；终态报告为 [Campaign291 终端报告](a_share_three_day_walkforward_campaign_291_terminal_report.md)，最新状态为 `a_share_three_day_iteration_status_20260825_campaign291_terminal.json`，最新重复控制库政策为 `a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v421_20260825.json`。

历史完整定义/数值比较器库现为 `164/145`。Campaign291 因通过无收益门而被保留用于以后防重复，但其收益方向已经科学终止；不得反向、改中位状态、119 支持、权重、阈值、签名或与 Campaign290 组合进行事后挽救。

Candidate49 仍是唯一活动前瞻候选，信号/执行账本保持 0/0，禁止历史回填和第二个前瞻候选。历史结果不得生成当前评分、选股、仓位或订单。本地研究证据位于 `data/experiments/short_horizon/historical_walkforward/campaign_291/alpha158_session_median_state_consensus_strength_v1/`，受忽略规则保护，不要移动、清理或强制提交。

复核：

```bash
MPLCONFIGDIR=/private/tmp/campaign291-mpl PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m scripts.a_share_three_day_walkforward_campaign291 verify
MPLCONFIGDIR=/private/tmp/campaign291-mpl PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign291.py
```

下一步 Campaign292 只能先冻结新的有限、机制独立、零网络离线概念目录，并以 `164/145` 库做值前重叠检查；不得围绕 Campaign291 调参、改方向或组合救援。本交接是研究记录，不构成投资建议。
