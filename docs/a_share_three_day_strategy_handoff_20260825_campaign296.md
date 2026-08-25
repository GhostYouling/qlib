# A股三日短线因子研究交接文档（Campaign296）

## 当前结论

Campaign296 已完整结束。固定因子 `alpha158_linear_trend_quality_10d = BETA10 × RSQR10` 覆盖充分且通过 148/148 唯一性门，但 2021–2023 三个验证折的 mean Rank IC、spread、标准化收益和成本后收益全部为负，幸存者为 0。2024–2025 未打开，当前没有可部署的新策略。

因子仅因通过覆盖和唯一性而追加到未来重复控制库，库由 `167/148` 更新为 `168/149`；新顺序哈希为 `1d618cac…e1bd76d` / `71bb5c75…ecaffcaf`。该追加不表示开发通过或投资价值。

## 权威入口

- 工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- 分支：`faet/local-test`
- 协议：`docs/a_share_three_day_walkforward_campaign_296_preregistration_20260825.json`
- 最终实现冻结：`docs/a_share_three_day_walkforward_campaign_296_implementation_freeze_v3_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_296_terminal_result_20260825.json`
- 人类可读报告：`docs/a_share_three_day_walkforward_campaign_296_terminal_report.md`
- 最新库政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v426_20260825.json`
- 库顺序重建收据：`docs/a_share_three_day_walkforward_campaign_296_library_order_reconstruction_receipt_20260825.json`
- 最终证据根：`.local-research/campaign_296/alpha158_linear_trend_quality_10d_v2/`
- 保留的 v1 失败证据：`.local-research/campaign_296/alpha158_linear_trend_quality_10d_v1/`

## 核心证据

- 有效行 1,001,402/1,001,781，P05 日覆盖约 99.728%，潜在三日 cohort 379。
- 148 个冻结比较器全部通过，最大绝对中位日 Rank 相关 0.573464。
- mean Rank IC：2021 -0.011620、2022 -0.017736、2023 -0.036596。
- 标准化收益：-46.75%、-42.21%、-41.24%；10bp 收益：-9.75%、-5.66%、-6.05%。
- 复合标准化/10bp/20bp 收益：-81.92%/-20.02%/-22.98%；最差标准化回撤 -70.33%。
- 终端台账 14 条：9 个概念、4 个基础设施失败、1 个完整因子；开发收益试验 1 次。

## 不可跨越边界

- 禁止反向 Campaign296、改十日窗口、替换/重加权 RSQR10、阈值化、筛选或与旧因子组合救援。
- Campaign296 进入 `168/149` 仅用于重复控制，不得当作已验证策略。
- 2024–2025 锁箱不得打开，因为开发幸存者为 0。
- Candidate49 仍是唯一前瞻候选；禁止历史回填、第二前瞻候选和 2026-08-25 同日重试。
- 历史结果不得生成当前评分、选股、仓位或订单。
- 外部 `data` 符号链接及其 Git 删除状态不属于本轮，禁止暂存、恢复或覆盖。

## 下一安全动作

持续目标保持 active。Campaign297 可以在任意时间启动新的有限、零网络、机制独立的值前目录，并必须使用 `168/149` 库做覆盖和有序重复控制。不得围绕 Campaign296 的 BETA10、RSQR10、十日窗口、方向或乘法权重做邻域搜索；若没有新的机制独立概念，应记录零路线，而不是消耗更多收益样本。

复核：

```bash
python -m scripts.a_share_three_day_walkforward_campaign296 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign296.py
```
