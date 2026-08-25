# A股三日短线因子研究交接文档（Campaign297）

## 当前结论

Campaign297 已完整结束。固定因子 `alpha158_interquantile_envelope_occupancy_20d = (QTLU20 - QTLD20) / (MAX20 - MIN20)` 覆盖充分且通过 149/149 唯一性门，但 2021–2023 三个验证折的 spread、标准化收益和成本后收益全部为负，幸存者为 0。2024–2025 未打开，当前没有可部署的新策略。

因子仅因通过覆盖和唯一性而追加到未来重复控制库，库由 `168/149` 更新为 `169/150`；新顺序哈希为 `b25aef82…5b9fea` / `135dec87…a6508e`。该追加不表示开发通过或投资价值。

## 权威入口

- 工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- 分支：`faet/local-test`
- 协议：`docs/a_share_three_day_walkforward_campaign_297_preregistration_20260825.json`
- 最终实现冻结：`docs/a_share_three_day_walkforward_campaign_297_implementation_freeze_v2_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_297_terminal_result_20260825.json`
- 人类可读报告：`docs/a_share_three_day_walkforward_campaign_297_terminal_report.md`
- 最新库政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v427_20260825.json`
- 库顺序重建收据：`docs/a_share_three_day_walkforward_campaign_297_library_order_reconstruction_receipt_20260825.json`
- 最终证据根：`.local-research/campaign_297/alpha158_interquantile_envelope_occupancy_20d_v2/`
- 保留的 v1 失败证据：`.local-research/campaign_297/alpha158_interquantile_envelope_occupancy_20d_v1/`

## 核心证据

- 有效行 1,001,507/1,001,781，P05 日覆盖约 99.742%，潜在三日 cohort 379。
- 149 个冻结比较器全部通过，最大绝对中位日 Rank 相关 0.086854。
- mean Rank IC：2021 0.015358、2022 -0.015923、2023 -0.003977。
- 标准化收益：-14.66%、-2.91%、-11.90%；10bp 收益：-3.25%、-0.89%、-1.06%。
- 复合标准化/10bp/20bp 收益：-27.00%/-5.12%/-10.29%；最差标准化回撤 -39.62%。
- 终端台账 11 条：9 个概念、1 个基础设施失败、1 个完整因子；开发收益试验 1 次。

## 不可跨越边界

- 禁止反向 Campaign297、改二十日窗口、改 20%/80% 分位数、替换完整包络、加 epsilon/填充/裁剪/阈值/筛选或与旧因子组合救援。
- Campaign297 进入 `169/150` 仅用于重复控制，不得当作已验证策略。
- 2024–2025 锁箱不得打开，因为开发幸存者为 0。
- Candidate49 仍是唯一前瞻候选；禁止历史回填、第二前瞻候选和 2026-08-25 同日重试。
- 历史结果不得生成当前评分、选股、仓位或订单。
- 外部 `data` 符号链接及其 Git 删除状态不属于本轮，禁止暂存、恢复或覆盖。

## 下一安全动作

持续目标保持 active。Campaign298 可以在任意时间启动新的有限、零网络、机制独立的值前目录，并必须使用 `169/150` 库做覆盖和有序重复控制。不得围绕 Campaign297 的二十日包络占用、分位数、方向或标准化方式做邻域搜索；若没有新的机制独立概念，应记录零路线，而不是消耗更多收益样本。

复核：

```bash
python -m scripts.a_share_three_day_walkforward_campaign297 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign297.py
```
