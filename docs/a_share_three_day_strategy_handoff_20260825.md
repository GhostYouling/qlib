# A股三日短线策略研究交接（截至 Campaign302）

当前策略研究已完成到 Campaign302。完整 Alpha360 + 固定时序 Transformer 的三折零收益设计已成功，第一折也完成固定 5 epoch 训练；但冻结 runner 在读取任何验证收益之前因 `DatetimeIndex.eq()` API 错误终止。该候选既未预测失败，也未验证通过，当前没有可部署的新策略。

权威交接请从 [Campaign302 交接文档](a_share_three_day_strategy_handoff_20260825_campaign302.md) 开始；终止报告为 [Campaign302 终止报告](a_share_three_day_walkforward_campaign_302_terminal_report.md)，最新状态为 `a_share_three_day_iteration_status_20260825_campaign302_terminal.json`，最新重复控制政策为 `a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v432_20260825.json`。

Campaign302 的零收益设计完成 3/3 折，共持久化 54,197,216 字节抽样特征；第一折在 8,369 行上完成训练，2021 Alpha360 验证特征完成流式评分，但分数门禁和分数快照未完成，验证折收益读取为 0。第二、三折模型未训练，2024–2025 未打开。

历史完整定义/数值比较器库保持 `172/153`，顺序摘要保持 `ba884534...af0df1` / `41b42563...0b499d`。Campaign302 没有验证指标或 survivor，因而不得追加定义或比较器，也不得从训练损失推断策略表现。

Candidate49 仍是唯一活动前瞻候选，账本保持 0/0。2026-08-25 只读 plan 已失败关闭，未运行且不得同日重试。Campaign302 不得修改冻结 runner 后沿用同一标识重跑；若恢复，只能建立新的、单独预注册且科学选择完全不变的实现恢复 Campaign，并计作新尝试。

外部 `data` symlink 的既有删除/未跟踪状态不属于本次提交，禁止 stage 或恢复。历史结果不得生成当前评分、选股、仓位或订单。本交接是研究记录，不构成投资建议。

复核：

```bash
cd /Users/niyufei/Coding/qlib/recovery-worktree
python -m pytest -q \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign302.py \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign302_publication.py
```

截至 Campaign302，累计历史研究尝试为 3,119，累计读取收益的开发尝试为 332。若继续研究，只能使用新的预注册实现恢复或真正的新信息通道，不能继续排列组合已终止的日线技术因子。
