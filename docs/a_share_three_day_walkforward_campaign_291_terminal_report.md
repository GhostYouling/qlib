# A股三日短线因子 Campaign291 终端报告

## 结论

Campaign291 已完整终止，存活者为 0。固定因子 `alpha158_session_median_state_consensus_strength_1d` 的覆盖与 144 个既有数值因子的去重门禁全部通过，但只有 1/3 验证折 Rank IC 为正，三折标准化收益和 10bp/20bp 收益全部为负。它在执行约束上可运行，却没有通过冻结的收益质量门禁，不能部署，也不得事后反向、改中位状态、支持数、权重、阈值或与 Campaign290 组合挽救。

2024–2025 锁箱没有打开。Candidate49 仍是唯一前瞻候选，信号/执行账本保持 0/0；本轮没有网络请求、历史回填、第二前瞻候选、当前评分、选股、仓位或订单。

## 因子与审计

因子在每个交易日把 158 个 Alpha158 坐标分别按模型支持同行的有限中位数编码为低于、等于或高于。每只股票须满足当日模型支持和至少 119 个有限坐标；得分为“高于数减低于数”的绝对值除以有限状态总数，方向冻结为越高越好。该绝对值不把异质 Alpha158 坐标强行解释成统一看多或看空方向；没有前一日状态、填充、裁剪、平滑、权重、拟合、阈值或方向搜索。

- 质量/上市域：1,001,781 行；候选有效 1,001,737 行。
- 日覆盖中位数和 P05 均为 100%，P05 有效股票 110.3。
- 三日非重叠潜在 cohort 379 个，覆盖 2019–2023 五年。
- 144/144 数值去重比较通过；最大绝对中位日 Rank 相关为 0.055099。
- 与 Campaign290 三态持续度因子的绝对中位日 Rank 相关为 0.039380，证实两者不是近似复制。

因子因覆盖和完整去重通过，被追加到历史完整定义库与未来重复控制比较器中，库由 `163/144` 更新为 `164/145`。这只用于防止后续重复研究，不代表收益有效或可投资。

## 三折结果

| 验证年 | Rank IC | 多空毛价差 | 标准化收益 | 最大回撤 | 10bp | 20bp | 整手可负担率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | +0.00464 | +0.7146% | -4.1597% | -34.7957% | -1.4817% | -3.4870% | 94.59% |
| 2022 | -0.00702 | +0.0390% | -25.1660% | -26.5935% | -5.8689% | -7.1605% | 92.24% |
| 2023 | -0.00045 | -0.1596% | -22.0596% | -29.2165% | -4.8913% | -6.7668% | 91.44% |

三折复合标准化、10bp、20bp 收益分别为 -44.1003%、-11.7997%、-16.4610%。正 Rank IC 为 1/3，正标准化收益和正 10bp 收益均为 0/3；最差标准化回撤 -34.7957%，也低于冻结的 -25% 下限。唯一拒绝分类为 `development_quality_or_aggregate_gate_failed`，存活者为 0。

## 证据与复核

- 协议：`docs/a_share_three_day_walkforward_campaign_291_preregistration_20260825.json`
- 实现冻结：`docs/a_share_three_day_walkforward_campaign_291_implementation_freeze_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_291_terminal_result_20260825.json`
- 本地输出根：`data/experiments/short_horizon/historical_walkforward/campaign_291/alpha158_session_median_state_consensus_strength_v1/`
- 追加式台账：输出根下 `terminal_trial_ledger.json`，8 条，链尖 `d68bc86a…1a299f`。
- 后终态文档基础设施失败另见 `docs/a_share_three_day_walkforward_campaign_291_local_legacy_library_reconstruction_failure_20260825.json`；它没有改变研究结果或台账。

复核命令：

```bash
MPLCONFIGDIR=/private/tmp/campaign291-mpl PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m scripts.a_share_three_day_walkforward_campaign291 verify
MPLCONFIGDIR=/private/tmp/campaign291-mpl PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign291.py
```

校验应返回 `verified_campaign291_terminal`、3 个验证折、0 个存活者、8 条终端试验台账、2024–2025 关闭和 Candidate49 未改变。本报告仅是历史研究记录，不构成投资建议。
