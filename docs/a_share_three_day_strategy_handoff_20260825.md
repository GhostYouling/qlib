# A股三日短线策略研究交接（截至 Campaign290）

当前已完成到 Campaign290，持续研究目标仍为 active。最新因子 `alpha158_session_median_state_persistence_1d` 通过覆盖和 143/143 去重，但 2021–2023 三折 Rank IC、标准化收益及 10bp/20bp 收益均为负，存活者为 0，2024–2025 没有打开，当前没有可部署的新策略。

权威交接请从 [Campaign290 交接文档](a_share_three_day_strategy_handoff_20260825_campaign290.md) 开始；终态报告为 [Campaign290 终端报告](a_share_three_day_walkforward_campaign_290_terminal_report.md)，最新状态为 `a_share_three_day_iteration_status_20260825_campaign290_terminal.json`，最新重复控制库政策为 `a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v420_20260825.json`。

历史完整定义/数值比较器库现为 `163/144`。Campaign290 因通过无收益门而被保留用于以后防重复，但其收益方向已经科学终止；不得反向、改中位状态、滞后、119 支持或权重进行事后挽救。

Candidate49 仍是唯一活动前瞻候选，信号/执行账本保持 0/0，禁止历史回填和第二个前瞻候选。历史结果不得生成当前评分、选股、仓位或订单。本地研究证据位于 `data/experiments/short_horizon/historical_walkforward/campaign_290/alpha158_session_median_state_persistence_v1/`，受忽略规则保护，不要移动、清理或强制提交。

复核：

```bash
MPLCONFIGDIR=/private/tmp/campaign290-mpl /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m scripts.a_share_three_day_walkforward_campaign290 verify
MPLCONFIGDIR=/private/tmp/campaign290-mpl /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign290.py
```

下一步 Campaign291 只能先冻结新的有限、机制独立、零网络离线概念目录，并以 `163/144` 库做值前重叠检查；不得围绕 Campaign290 调参。本交接是研究记录，不构成投资建议。
