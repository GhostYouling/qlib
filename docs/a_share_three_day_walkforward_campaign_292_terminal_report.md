# A股三日短线因子 Campaign292 终端报告

## 结论

Campaign292 已完整终止，存活者为 0。固定因子 `alpha158_session_peer_rank_extremity_breadth_1d` 的覆盖与 145 个既有数值因子的去重门禁全部通过，但 2021–2023 三折 Rank IC 全为负，三折标准化收益全为负，只有 2023 的 10bp 试验微正，且前两折整手可负担率未达门槛。它不能部署，也不得事后反向、改百分位、119 支持、权重、过滤、阈值或与 Campaign290/291 组合挽救。

2024–2025 锁箱没有打开。Candidate49 仍是唯一前瞻候选，信号/执行账本保持 0/0；本轮没有网络请求、历史回填、第二前瞻候选、当前评分、选股、仓位或订单。

## 因子与审计

每个交易日、每个 Alpha158 坐标都在有限且满足模型支持的同行中使用升序平均并列排名，映射为经验百分位 `u=(rank-0.5)/n`，再变换为居中极端度 `2*abs(u-0.5)`。每只股票须同时满足质量/上市、模型支持和至少 119 个有限坐标；得分是有限坐标极端度的等权平均，方向冻结为越高越好。没有前一日状态、共同经济符号、填充、裁剪、平滑、权重、拟合、阈值、反向或组合搜索。

- 质量/上市域 1,001,781 行，候选有效 1,001,737 行。
- 日覆盖中位数和 P05 均为 100%，P05 有效股票 110.3。
- 三日非重叠潜在 cohort 379 个，覆盖 2019–2023 五年。
- 145/145 数值去重比较通过；最大绝对中位日 Rank 相关为 0.379301。
- 与 Campaign290 持续度因子的相关为 0.379301，与 Campaign291 状态共识因子的相关为 0.020472。

因子因覆盖和完整去重通过，被追加到历史完整定义库与未来重复控制比较器中，库由 `164/145` 更新为 `165/146`。这只用于防止后续重复研究，不代表收益有效或可投资。

## 三折结果

| 验证年 | Rank IC | 多空毛价差 | 标准化收益 | 最大回撤 | 10bp | 20bp | 整手可负担率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | -0.02717 | -0.3956% | -15.2888% | -56.5757% | -3.9543% | -5.6172% | 86.70% |
| 2022 | -0.02328 | -0.9876% | -53.5937% | -60.4193% | -8.2515% | -9.3741% | 89.77% |
| 2023 | -0.02946 | +0.5344% | -7.2696% | -61.2276% | +0.5350% | -0.9762% | 94.04% |

三折复合标准化、10bp、20bp 收益分别为 -63.5465%、-11.4081%、-15.2997%。正 Rank IC 和正标准化收益均为 0/3，正 10bp 收益为 1/3；最差标准化回撤 -61.2276%。拒绝原因为前两折整手可负担率不足及开发质量/聚合门禁失败，存活者为 0。

## 基础设施与会计

终端追加式台账共 11 条：7 个值前概念、3 个运行期基础设施失败、1 个完整因子。第一次完整运行在两折收益已读后因本地卷 ENOSPC 终止，v1 部分证据保持不改；随后只允许公式和门禁完全相同、批量 8192、折间释放内存、独立 v2 输出根的完整重启。另两次失败分别是元数据 plan 测试的输出根绑定错误，以及直接文件调用的 Python import 路径错误；两者都未读取研究值。完整因子只计一个开发试验，但实际验证折收益读取为失败运行 2 折加完整运行 3 折，共 5 次。

终态发布后又记录 1 次文档测试基础设施失败：测试错误要求两份历史报告全文相同，而它们只有 Campaign292 新增区段应保持一致。失败为 12 通过、1 失败，未读取研究值；修正后的 13 项测试全部通过。Campaign292 有效总会计因此为 12 次尝试（7 科学概念、4 基础设施、1 完整因子），终端哈希链仍原样保持 11 条。

## 证据与复核

- 协议：`docs/a_share_three_day_walkforward_campaign_292_preregistration_20260825.json`
- 最终实现冻结：`docs/a_share_three_day_walkforward_campaign_292_implementation_freeze_v4_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_292_terminal_result_20260825.json`
- 最终本地输出根：`data/experiments/short_horizon/historical_walkforward/campaign_292/alpha158_session_peer_rank_extremity_breadth_v2/`
- 保留的失败输出根：`data/experiments/short_horizon/historical_walkforward/campaign_292/alpha158_session_peer_rank_extremity_breadth_v1/`
- 追加式台账：最终输出根下 `terminal_trial_ledger.json`，11 条，链尖 `d50515bb…0e023b52`。

复核命令：

```bash
MPLCONFIGDIR=/private/tmp/campaign292-mpl PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m scripts.a_share_three_day_walkforward_campaign292 verify
MPLCONFIGDIR=/private/tmp/campaign292-mpl PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign292.py
```

校验应返回 `verified_campaign292_terminal`、3 个完整验证折、0 个存活者、11 条终端试验台账、2024–2025 关闭和 Candidate49 未改变。本报告仅是历史研究记录，不构成投资建议。
