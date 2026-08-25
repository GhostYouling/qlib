# A股三日短线策略研究交接（截至 Campaign294）

当前已完成到 Campaign294，持续研究目标仍为 active。最新因子 `alpha158_same_horizon_cross_family_peer_rank_consensus_5h` 覆盖通过，但与 Campaign292 的绝对中位日 Rank 相关高达 0.985178，在无收益门失败；没有读取历史收益或启动开发折，当前没有可部署的新策略。

权威交接请从 [Campaign294 交接文档](a_share_three_day_strategy_handoff_20260825_campaign294.md) 开始；终态报告为 [Campaign294 终端报告](a_share_three_day_walkforward_campaign_294_terminal_report.md)，最新状态为 `a_share_three_day_iteration_status_20260825_campaign294_terminal.json`，最新重复控制库政策为 `a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v424_20260825.json`。

历史完整定义/数值比较器库仍为 `166/147`。Campaign294 因重复门失败未追加；不得反向、换 IQR/MAD/熵、改 horizon/22 家族支持/权重或与 Campaign290–293 组合进行事后挽救。

Candidate49 仍是唯一活动前瞻候选，账本保持 0/0。2026-08-25 只读 plan 已失败关闭，未运行且不得同日重试。历史结果不得生成当前评分、选股、仓位或订单。本地 Campaign294 v1/v2 证据均位于 `.local-research/campaign_294/`，受忽略规则保护，不要移动、清理或强制提交。

复核：

```bash
PYTHONPATH=. python -m scripts.a_share_three_day_walkforward_campaign294 verify
PYTHONPATH=. python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign294.py
```

下一步 Campaign295 只能先冻结新的有限、机制独立、零网络离线概念目录，并继续以 `166/147` 库做值前重叠检查；应避开 Alpha158 同行秩状态簇，不得围绕 Campaign294 调参、改方向或组合救援。本交接是研究记录，不构成投资建议。
