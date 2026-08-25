# A股三日短线因子研究交接（Campaign301）

## 当前结论

Campaign301 已完成并在值前终止：11 条有限路线中，10 条是已终止 Alpha158/日线 OHLCV 家族的改写或禁止的旧因子组合，Alpha360 则因工作区安全物化空间不足而明确延期。本轮没有选中公式、没有候选快照、没有读取候选/比较器/价格/收益、没有开发回测，也没有打开 2024–2025。

这意味着“继续排列组合现有因子”已不再是有效迭代；继续这样做只会增加多重检验与过拟合。当前历史库仍为 `172/153`，没有新策略可以部署。持续研究目标仍为 active，下一轮必须增加真正新的信息，而不是改写已失败的日线技术指标。

## 权威入口

- 最新状态：`docs/a_share_three_day_iteration_status_20260825_campaign301_prevalue_terminal.json`
- 前沿审计：`docs/a_share_three_day_walkforward_campaign_301_prevalue_frontier_audit_20260825.json`
- 追加式值前台账：`docs/a_share_three_day_walkforward_campaign_301_prevalue_trial_ledger_20260825.json`
- 终态结果：`docs/a_share_three_day_walkforward_campaign_301_terminal_result_20260825.json`
- 最新重复控制政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v431_20260825.json`
- 终端报告：`docs/a_share_three_day_walkforward_campaign_301_terminal_report.md`

## 不可变边界

- Campaign286–300 均不可通过换方向、窗口、变换、阈值、过滤、子集、权重、seed、成本或模型组合救援。
- Campaign301 不追加完整定义或数值比较器；`172/153` 及其顺序摘要必须保持不变。
- Alpha360 只是资源延期，不是科学失败。若以后重启，必须事前冻结完整 360 特征、五年分区、原子存储预算、模型、成本和门禁；不得缩短历史、先看值再选股票或写入未授权外部卷。
- Candidate49 仍是唯一前瞻候选，账本 0/0；禁止历史回填、第二前瞻候选、2026-08-25 同日重试、失败码绕过和实盘下单。
- 历史结果不得生成当前评分、选股、仓位、订单或投资建议；2024–2025 继续关闭。
- `data` 指向 `/Volumes/DIsk/Disk-Coding/qlib-data/recovery-worktree`。现有追踪删除与 `?? data` 属于外部/用户状态，不得 stage、恢复、删除或改写。

## 复核

```bash
cd /Users/niyufei/Coding/qlib/recovery-worktree
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign301_publication.py
python -m ruff check tests/data_collector_tests/test_a_share_three_day_walkforward_campaign301_publication.py scripts/a_share_short_horizon_factor_research.py
```

## 下一步

Campaign302 仅允许从新信息通道或单独冻结的资源安全机制开始。优先方向应是可验证的 point-in-time 事件/基本面/跨资产来源，而不是 Alpha158、日线 K 线、缺口、量价、分位、趋势、成交活跃度或旧终止因子的排列组合。任何新路线都要先冻结有限目录、数据/代码指纹、三组 2019–2023 expanding walk-forward 折、边界清除三信号会话、成本和合取门；只有开发 survivor 非零才可一次性打开 2024–2025，并标注为历史已暴露的准样本外。

本交接是研究与复现说明，不构成投资建议。
