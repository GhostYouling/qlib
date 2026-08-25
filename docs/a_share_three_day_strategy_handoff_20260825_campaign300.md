# A股三日短线因子研究交接（Campaign300）

## 当前结论

持续迭代目标仍为 active。Campaign300 的固定高方向因子为：

`alpha158_conditional_return_magnitude_asymmetry_20d = (SUMP20/CNTP20)/((SUMP20/CNTP20)+(SUMN20/CNTN20))`

它通过覆盖和 152/152 唯一性门，但 2021–2023 的 Rank IC 三折全负；复合归一化收益 -31.12%，复合 10bp -4.36%，复合 20bp -8.76%，最差归一化回撤 -39.41%，且 2021 年整手可负担率只有 87.33%。冻结合取门槛判定 survivor=0。2024–2025 未打开，当前没有新可部署策略；不得事后反向、换窗口或变换公式救援。

## 权威入口

- 最新状态：`docs/a_share_three_day_iteration_status_20260825_campaign300_terminal.json`
- 最新重复控制政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v430_20260825.json`
- 终态结果：`docs/a_share_three_day_walkforward_campaign_300_terminal_result_20260825.json`
- 终端报告：`docs/a_share_three_day_walkforward_campaign_300_terminal_report.md`
- 运行器：`scripts/a_share_three_day_walkforward_campaign300.py`
- 本地不可变输出：`.local-research/campaign_300/alpha158_conditional_return_magnitude_asymmetry_20d_v1/`

完整定义/数值比较器库已因覆盖和 152 项唯一性通过而追加到 `172/153`；摘要分别为 `ba884534...af0df1` 与 `41b42563...0b499d`。追加仅用于未来重复控制，不代表预测有效或可交易。

## 不可变边界

- 不得反向、改 20 日窗口、改写条件幅度公式、增加 epsilon/log/绝对值/裁剪/阈值/过滤，或与旧因子、模型组合救援 Campaign300。
- 不得打开 Campaign300 的 2024–2025；只有未来完整冻结的新 campaign 产生非零开发 survivor 才能一次性打开，并标记为历史已暴露的准样本外。
- Candidate49 仍是唯一前瞻候选；账本保持 0/0，禁止历史回填、第二前瞻候选、2026-08-25 同日重试、实盘下单或绕过失败退出码。
- 历史结果不得生成当前评分、选股、仓位、订单或投资建议；历史报告必须继续提示当前上市快照造成的存活偏差。
- `data` 是指向 `/Volumes/DIsk/Disk-Coding/qlib-data/recovery-worktree` 的外部 symlink。工作树中既有与本研究无关的追踪删除和 `?? data`，不得 stage、恢复、删除或改写它们。

## 环境与复核

本轮只做零网络离线研究。`/Users/niyufei/Coding/qlib/.env` 与 recovery worktree 的 `.env` 均不存在；这不影响历史研究。未来 Candidate49 合法新交易日流程若需 provider，必须恢复私密、Git-ignored 的 `.env` 并只验证 `TUSHARE_TOKEN` 非空，绝不打印或哈希秘密。

```bash
cd /Users/niyufei/Coding/qlib/recovery-worktree
python -m scripts.a_share_three_day_walkforward_campaign300 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign300.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign300_publication.py
```

## 下一步

Campaign301 可以在任何时间从 `172/153` 库开始新的零网络值前概念审计。它必须是机制独立的单公式/单方向有限尝试，并在任何候选、比较器或收益值前冻结公式、方向、参数、过滤、子集、组合、模型、成本、门禁和代码/数据指纹。不得围绕 Campaign300 的条件涨跌幅强度比做反向、邻域、变换或窗口搜索。
