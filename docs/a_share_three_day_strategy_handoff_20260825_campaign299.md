# A股三日短线因子研究交接（Campaign299）

## 当前结论

持续迭代目标仍为 active。Campaign299 的固定高方向因子为：

`alpha158_close_distribution_upper_tail_asymmetry_20d = (2*MA20-QTLU20-QTLD20)/(QTLU20-QTLD20)`

它通过覆盖和 151/151 唯一性门，但 2021–2023 的 Rank IC、归一化收益和 10bp 收益全部为负；复合归一化收益 -64.50%，复合 10bp -14.85%，复合 20bp -19.36%，最差归一化回撤 -46.60%。冻结合取门槛判定 survivor=0。2024–2025 未打开，当前没有新可部署策略；同向负结果不得用于事后反向救援。

## 权威入口

- 最新状态：`docs/a_share_three_day_iteration_status_20260825_campaign299_terminal.json`
- 最新重复控制政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v429_20260825.json`
- 终态结果：`docs/a_share_three_day_walkforward_campaign_299_terminal_result_20260825.json`
- 终端报告：`docs/a_share_three_day_walkforward_campaign_299_terminal_report.md`
- 运行器：`scripts/a_share_three_day_walkforward_campaign299.py`
- 本地不可变输出：`.local-research/campaign_299/alpha158_close_distribution_upper_tail_asymmetry_20d_v1/`

完整定义/数值比较器库已因覆盖和 151 项唯一性通过而追加到 `171/152`；摘要分别为 `b43cca14...e4120e` 与 `f7cf9cf4...1ae14`。追加仅用于未来重复控制，不代表预测有效或可交易。

## 不可变边界

- 不得反向、改 20 日窗口、改变均值/分位数组合、增加 epsilon/log/绝对值/裁剪/阈值/过滤，或与旧因子、模型组合救援 Campaign299。
- 不得打开 Campaign299 的 2024–2025；只有未来完整冻结的新 campaign 产生非零开发 survivor 才能一次性打开，并标记为历史已暴露的准样本外。
- Candidate49 仍是唯一前瞻候选；账本保持 0/0，禁止历史回填、第二前瞻候选、2026-08-25 同日重试、实盘下单或绕过失败退出码。
- 历史结果不得生成当前评分、选股、仓位、订单或投资建议；历史报告必须继续提示当前上市快照造成的存活偏差。
- `data` 是指向 `/Volumes/DIsk/Disk-Coding/qlib-data/recovery-worktree` 的外部 symlink。工作树中已有 79 项与本研究无关的追踪删除和 `?? data`，不得 stage、恢复、删除或改写它们。

## 环境与复核

本轮只做零网络离线研究。此前核查 `/Users/niyufei/Coding/qlib/.env` 与 recovery worktree 的 `.env` 均不存在；这不影响历史研究。未来 Candidate49 合法新交易日流程若需 provider，必须先恢复私密、Git-ignored 的 `.env` 并只验证 `TUSHARE_TOKEN` 非空，绝不打印或哈希秘密。

```bash
cd /Users/niyufei/Coding/qlib/recovery-worktree
python -m scripts.a_share_three_day_walkforward_campaign299 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign299.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign299_publication.py
```

## 下一步

Campaign300 可以在任何时间从 `171/152` 库开始新的零网络值前概念审计。它必须是机制独立的单公式/单方向有限尝试，并在任何候选、比较器或收益值前冻结公式、方向、参数、过滤、子集、组合、模型、成本、门禁和代码/数据指纹。不得围绕 Campaign299 的收盘分布不对称做反向、邻域或窗口搜索。
