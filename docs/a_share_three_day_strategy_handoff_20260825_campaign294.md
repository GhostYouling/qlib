# A股三日短线因子研究交接文档（Campaign294）

## 当前结论

Campaign294 已在无收益门终止。新因子 `alpha158_same_horizon_cross_family_peer_rank_consensus_5h` 覆盖充分，但与 Campaign292 极端度广度的中位日 Rank 相关为 -0.985178，绝对值超过 0.8；它是反向近重复，不能进入收益验证，也不得反向或换方差统计救援。没有读取历史日线收益，开发折为 0，2024–2025 未打开，当前没有可部署的新策略。

因子没有追加到重复控制库，完整定义/数值比较器保持 `166/147`，顺序 SHA-256 仍为 `57662d72…ace06f` / `5a771c4f…914c1`。

## 权威入口

- 工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- 分支：`faet/local-test`
- 有效协议：`docs/a_share_three_day_walkforward_campaign_294_preregistration_v2_20260825.json`
- 最终实现冻结：`docs/a_share_three_day_walkforward_campaign_294_implementation_freeze_v2_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_294_terminal_result_20260825.json`
- 人类可读报告：`docs/a_share_three_day_walkforward_campaign_294_terminal_report.md`
- 最新库政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v424_20260825.json`
- 最终证据根：`.local-research/campaign_294/alpha158_same_horizon_cross_family_peer_rank_consensus_v2/`
- 保留的 v1 失败证据：`.local-research/campaign_294/alpha158_same_horizon_cross_family_peer_rank_consensus_v1/`

## 核心证据

- 有效行 1,001,589/1,001,781，P05 日覆盖约 99.889%，潜在三日 cohort 379。
- 147 个冻结比较器中按序读取 146 个；前 145 个通过。
- 第 146 个 Campaign292 相关为 -0.985178，绝对门禁失败；第 147 个 Campaign293 未读。
- 日线价格、前向收益、训练收益、开发折和锁箱收益读取均为 0。
- 终端台账 12 条：8 个值前概念、3 个基础设施失败、1 个完整因子。

## Candidate49

2026-08-25 16:30 后的唯一只读 plan 以退出码 1 失败关闭：活动日线状态没有恰好一个来源。`ready=false`，没有 run，不得同日重试。账本仍为 0/0；独立记录是 `docs/a_share_candidate49_20260825_readonly_plan_failure_record.json`。

## 不可跨越边界

- 禁止把 Campaign294 反向、改 IQR/MAD/熵、选 horizon、调 22 家族支持、重加权或与 Campaign290–293 组合。
- Campaign294 不进入 166/147 库；不得把它当作已验证策略。
- Candidate49 仍是唯一前瞻候选，禁止历史回填、第二前瞻候选和同日重试。
- 历史结果不得生成当前评分、选股、仓位或订单。
- 外部 `data` 符号链接及其 Git 删除状态不属于本轮，禁止暂存、恢复或覆盖。

## 下一安全动作

持续目标保持 active。Campaign295 只能从新的有限、机制独立、零网络值前目录开始，并以未变的 `166/147` 库做重复检查；应避开整个 Alpha158 同行秩“状态一致性/极端度/平滑度”簇，而不是继续做统计替换。

复核：

```bash
PYTHONPATH=. python -m scripts.a_share_three_day_walkforward_campaign294 verify
PYTHONPATH=. python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign294.py
```
