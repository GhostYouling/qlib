# A股三日短线策略研究交接（截至 Campaign301）

当前已完成到 Campaign301，持续研究目标仍为 active。Campaign301 在任何候选、比较器、价格或收益值之前审计了 11 条剩余 Alpha158/本地日线路线：10 条属于已终止家族的改写或禁止的事后组合，Alpha360 因授权工作区缺少安全原子物化余量而延期。选中因子、开发试验和 2024–2025 压力试验均为 0；当前没有可部署的新策略。

权威交接请从 [Campaign301 交接文档](a_share_three_day_strategy_handoff_20260825_campaign301.md) 开始；终态报告为 [Campaign301 终端报告](a_share_three_day_walkforward_campaign_301_terminal_report.md)，最新状态为 `a_share_three_day_iteration_status_20260825_campaign301_prevalue_terminal.json`，最新重复控制政策为 `a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v431_20260825.json`。

历史完整定义/数值比较器库保持 `172/153`，顺序摘要保持 `ba884534...af0df1` / `41b42563...0b499d`。Campaign301 没有完整因子，因而不得追加定义或比较器。继续排列组合现有 Alpha158、日线 K 线、缺口、量价、分位、趋势、成交活跃度或旧终止因子，不再属于新的机制研究。

Campaign300 的旧索引标题“截至 Campaign300”仍由 [Campaign300 专项交接](a_share_three_day_strategy_handoff_20260825_campaign300.md) 原样保存；其负结果不得反向、改窗或组合救援。Campaign301 是追加终态，不改写 Campaign300。

Candidate49 仍是唯一活动前瞻候选，账本保持 0/0。2026-08-25 只读 plan 已失败关闭，未运行且不得同日重试。历史结果不得生成当前评分、选股、仓位或订单。外部 `data` symlink 的既有删除/未跟踪状态不属于本次提交，禁止 stage 或恢复。

复核：

```bash
cd /Users/niyufei/Coding/qlib/recovery-worktree
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign301_publication.py
```

下一步 Campaign302 只能先冻结新的有限信息通道，或另行冻结资源安全且保持完整语义的机制；不得重开 Campaign301 已关闭路线。Alpha360 保持“资源延期、科学未判定”。本交接是研究记录，不构成投资建议。
