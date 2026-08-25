# A股三日短线因子研究交接（Campaign298）

## 当前结论

持续迭代目标仍为 active。Campaign298 的固定高方向因子为：

`alpha158_volume_coefficient_of_variation_20d = VSTD20 / VMA20`

它通过覆盖和 150/150 唯一性门，并在 2021–2023 取得 2/3 正 Rank IC、3/3 正归一化收益、2/3 正 10bp 收益；但最差归一化回撤 -50.39%、复合 20bp 收益 -1.51%，所以冻结合取门槛判定 survivor=0。2024–2025 未打开，当前没有新可部署策略。

## 权威入口

- 最新状态：`docs/a_share_three_day_iteration_status_20260825_campaign298_terminal.json`
- 最新重复控制政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v428_20260825.json`
- 终态结果：`docs/a_share_three_day_walkforward_campaign_298_terminal_result_20260825.json`
- 终端报告：`docs/a_share_three_day_walkforward_campaign_298_terminal_report.md`
- 运行器：`scripts/a_share_three_day_walkforward_campaign298.py`
- 本地不可变输出：`.local-research/campaign_298/alpha158_volume_coefficient_of_variation_20d_v1/`

完整定义/数值比较器库已因覆盖和 150 项唯一性通过而追加到 `170/151`；摘要分别为 `2c315c5e...2cb7d64` 与 `c556febf...859aad`。追加仅用于未来重复控制，不代表预测有效或可交易。

## 不可变边界

- 不得反向、改 20 日窗口、单独测试 VSTD/VMA、增加 epsilon/log/裁剪/阈值/过滤，或与价格、旧因子、模型组合救援 Campaign298。
- 不得打开 Campaign298 的 2024–2025；只有未来某个完整冻结 campaign 产生非零开发 survivor 才能一次性打开，并标记为历史已暴露的准样本外。
- Candidate49 仍是唯一前瞻候选；账本保持 0/0，禁止历史回填、第二前瞻候选、2026-08-25 同日重试、实盘下单或绕过失败退出码。
- 历史结果不得生成当前评分、选股、仓位、订单或投资建议；历史报告必须继续提示当前上市快照造成的存活偏差。
- `data` 是指向 `/Volumes/DIsk/Disk-Coding/qlib-data/recovery-worktree` 的外部 symlink。工作树中已有 79 项与本研究无关的追踪删除和 `?? data`，不得 stage、恢复、删除或改写它们。

## 环境与复核

本轮只做零网络离线研究。核查时 `/Users/niyufei/Coding/qlib/.env` 与 recovery worktree 的 `.env` 均不存在；这不影响历史研究，但未来 Candidate49 合法新交易日流程若需 provider，必须先恢复私密、Git-ignored 的 `.env` 并只验证 `TUSHARE_TOKEN` 非空，绝不打印或哈希秘密。

```bash
cd /Users/niyufei/Coding/qlib/recovery-worktree
/Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m scripts.a_share_three_day_walkforward_campaign298 verify
PYTHONPATH=/Users/niyufei/Coding/qlib/recovery-worktree /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign298.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign298_publication.py
```

## 下一步

Campaign299 可以在任何时间从 `170/151` 库开始新的零网络值前概念审计。它必须是机制独立的单公式/单方向有限尝试，并在任何候选、比较器或收益值前冻结公式、方向、参数、过滤、子集、组合、模型、成本、门禁和代码/数据指纹。不得围绕 Campaign298 的成交量变异系数做邻域搜索。
