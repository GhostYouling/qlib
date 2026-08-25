# A股三日短线因子研究交接文档（Campaign295）

## 当前结论

Campaign295 已完整结束。固定因子 `alpha158_price_volume_directional_confirmation_20d = SUMD20 × (1 + CORD20) / 2` 覆盖充分且通过 147/147 唯一性门，但 2021–2023 三个验证折的 mean Rank IC、标准化收益和 10bp 收益全部为负，幸存者为 0。2024–2025 未打开，当前没有可部署的新策略。

因子仅因通过覆盖和唯一性而追加到未来重复控制库，库由 `166/147` 更新为 `167/148`；新顺序哈希为 `95ba4f3a…f449841` / `b6b8c0e6…6123d9`。该追加不表示开发通过或投资价值。

## 权威入口

- 工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- 分支：`faet/local-test`
- 协议：`docs/a_share_three_day_walkforward_campaign_295_preregistration_20260825.json`
- 最终实现冻结：`docs/a_share_three_day_walkforward_campaign_295_implementation_freeze_v4_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_295_terminal_result_20260825.json`
- 人类可读报告：`docs/a_share_three_day_walkforward_campaign_295_terminal_report.md`
- 最新库政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v425_20260825.json`
- 库顺序重建收据：`docs/a_share_three_day_walkforward_campaign_295_library_order_reconstruction_receipt_20260825.json`
- 最终证据根：`.local-research/campaign_295/alpha158_price_volume_directional_confirmation_20d_v2/`
- 保留的 v1 失败证据：`.local-research/campaign_295/alpha158_price_volume_directional_confirmation_20d_v1/`

## 核心证据

- 有效行 1,001,506/1,001,781，P05 日覆盖约 99.740%，潜在三日 cohort 379。
- 147 个冻结比较器全部通过，最大绝对中位日 Rank 相关 0.330185。
- mean Rank IC：2021 -0.002571、2022 -0.021101、2023 -0.018083。
- 标准化收益：-29.44%、-11.04%、-42.53%；10bp 收益：-3.66%、-2.92%、-6.71%。
- 复合标准化/10bp/20bp 收益：-63.92%/-12.74%/-16.70%；最差标准化回撤 -62.05%。
- 终端台账 13 条；另有 1 条终态后发布失败单独记录。本轮有效总尝试 14 次，开发收益试验 1 次。

## 不可跨越边界

- 禁止反向 Campaign295、改 20 日 horizon、改 `(1+CORD20)/2` 权重、阈值化、筛选或与旧因子组合救援。
- Campaign295 进入 `167/148` 仅用于重复控制，不得当作已验证策略。
- 2024–2025 锁箱不得打开，因为开发幸存者为 0。
- Candidate49 仍是唯一前瞻候选；禁止历史回填、第二前瞻候选和 2026-08-25 同日重试。
- 历史结果不得生成当前评分、选股、仓位或订单。
- 外部 `data` 符号链接及其 Git 删除状态不属于本轮，禁止暂存、恢复或覆盖。

## 下一安全动作

持续目标保持 active。Campaign296 可以在任意时间启动新的有限、零网络、机制独立的值前目录，并必须使用 `167/148` 库做覆盖和有序重复控制。不得围绕 Campaign295 的价格方向、CORD 确认、20 日 horizon、方向或权重做邻域搜索；若没有新的机制独立概念，应记录零路线，而不是消耗更多收益样本。

复核：

```bash
python -m scripts.a_share_three_day_walkforward_campaign295 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign295.py
```
