# A股三日短线因子 Campaign290 终端报告

## 结论

Campaign290 已完整终止，存活者为 0。固定因子 `alpha158_session_median_state_persistence_1d` 的覆盖与 143 个既有数值因子的去重门禁全部通过，但 2021–2023 三折的 Rank IC、标准化收益和 10bp 收益均为负。它在执行约束上可运行，却没有通过冻结的收益质量门禁，不能部署，也不得事后反向、改状态阈值、换滞后或加权挽救。

2024–2025 锁箱没有打开。Candidate49 仍是唯一前瞻候选，信号/执行账本保持 0/0；本轮没有网络请求、历史回填、第二前瞻候选、当前评分、选股、仓位或订单。

## 因子与审计

因子把每个交易日 158 个 Alpha158 坐标分别按模型支持同行的有限中位数编码为低于、等于或高于，并与同一股票的精确前一接受会话比较。两日均须满足模型支持，至少 119 个坐标可配对；得分为状态相同的比例，方向冻结为越高越好。没有缺口桥接、填充、裁剪、平滑、坐标权重、模型拟合或方向搜索。

- 质量/上市域：1,001,781 行；候选有效 994,235 行。
- 日覆盖中位数 99.9186%，P05 92.9688%，P05 有效股票 109.3。
- 三日非重叠潜在 cohort 378 个，覆盖 2019–2023 五年。
- 143/143 数值去重比较通过；最大绝对中位日 Rank 相关为 0.169688。

因子因覆盖和完整去重通过，被追加到历史完整定义库与未来重复控制比较器中，库由 `162/143` 更新为 `163/144`。这只用于防止后续重复研究，不代表收益有效或可投资。

## 三折结果

| 验证年 | Rank IC | 多空毛价差 | 标准化收益 | 最大回撤 | 10bp | 20bp | 整手可负担率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | -0.00536 | -0.4918% | -25.7894% | -42.4409% | -5.7659% | -7.2625% | 91.40% |
| 2022 | -0.00002 | -0.6682% | -48.7622% | -49.5293% | -8.5740% | -10.4408% | 91.74% |
| 2023 | -0.00314 | +0.1385% | -9.9440% | -23.8767% | -2.3418% | -3.9714% | 94.57% |

三折复合标准化、10bp、20bp 收益分别为 -65.7572%、-15.8631%、-20.2435%。正 Rank IC、正标准化收益、正 10bp 收益均为 0/3；最差标准化回撤 -49.5293%。唯一拒绝分类为 `development_quality_or_aggregate_gate_failed`，存活者为 0。

## 证据与复核

- 协议：`docs/a_share_three_day_walkforward_campaign_290_preregistration_20260825.json`
- 实现冻结：`docs/a_share_three_day_walkforward_campaign_290_implementation_freeze_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_290_terminal_result_20260825.json`
- 本地输出根：`data/experiments/short_horizon/historical_walkforward/campaign_290/alpha158_session_median_state_persistence_v1/`
- 追加式台账：输出根下 `terminal_trial_ledger.json`，9 条，链尖 `ed3704cf…b95c40f`。

复核命令：

```bash
MPLCONFIGDIR=/private/tmp/campaign290-mpl /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m scripts.a_share_three_day_walkforward_campaign290 verify
MPLCONFIGDIR=/private/tmp/campaign290-mpl /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign290.py
```

校验应返回 `verified_campaign290_terminal`、3 个验证折、0 个存活者、9 条台账、2024–2025 关闭和 Candidate49 未改变。本报告仅是历史研究记录，不构成投资建议。
