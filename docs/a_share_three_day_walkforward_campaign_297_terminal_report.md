# A股三日短线因子 Campaign297 终端报告

## 结论

Campaign297 已完成固定因子 `alpha158_interquantile_envelope_occupancy_20d = (QTLU20 - QTLD20) / (MAX20 - MIN20)` 的覆盖、149 项有序唯一性和三折 2019–2023 walk-forward。高方向表示：过去二十个会话中，收盘价中央 60% 分布宽度相对于同期完整高低价包络越大，因子值越高。没有拟合、训练收益读取、方向搜索、窗口/分位数搜索、epsilon、填充、裁剪、阈值、筛选或组合。

覆盖和唯一性均通过，但开发结果失败：2021/2022/2023 mean Rank IC 分别为 0.015358、-0.015923、-0.003977，标准化收益分别为 -14.66%、-2.91%、-11.90%，10bp 纸面收益分别为 -3.25%、-0.89%、-1.06%。三个 spread、标准化收益和成本后收益全部为负，幸存者为 0；2024–2025 锁箱保持关闭，当前不可部署。

因子通过重复控制门，所以只作为未来重复比较定义追加一次；完整定义/数值比较器库从 `168/149` 变为 `169/150`。追加不表示策略有效，也不允许反向 Campaign297、改变二十日窗口或 20%/80% 分位数、替换包络、加 epsilon/裁剪/阈值，或与旧因子组合救援。

## 覆盖与唯一性

- 质量/上市域 1,001,781 行，候选有效 1,001,507 行。
- 日覆盖中位数 100%，P05 约 99.742%，P05 有效股票约 110.3。
- 2019–2023 共 1,147 个会话，潜在三日非重叠 cohort 379 个。
- 149/149 个冻结比较器全部通过；最大绝对中位日 Rank 相关为 0.086854，对应 `intraday_day_over_day_absolute_return_profile_similarity_238b`，远低于 0.8。
- 唯一性门阶段没有读取日线价格或前向收益；通过后才执行唯一一次三折开发试验。

## 三折开发结果

| 验证年 | cohort | mean Rank IC | top3-bottom3 毛 spread | 标准化收益 | 10bp 收益 | 20bp 收益 |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 74 | 0.015358 | -0.008564 | -14.66% | -3.25% | -4.99% |
| 2022 | 73 | -0.015923 | -0.005296 | -2.91% | -0.89% | -2.81% |
| 2023 | 74 | -0.003977 | -0.001858 | -11.90% | -1.06% | -2.86% |

三折复合标准化收益 -27.00%，10bp -5.12%，20bp -10.29%；中位 mean Rank IC -0.003977，最差标准化回撤 -39.62%。2021/2022 年 10bp board-lot 可负担率 88.74%/85.39%，低于冻结的 90% 门槛。没有训练收益读取，三个验证折均执行 3 个 signal session 的边界清除，t+1/t+3 保持在同一验证分区。

## 基础设施与会计

值前目录记录 9 个概念。本轮终端哈希链 11 条：9 个概念、1 个基础设施失败、1 个完整因子。首次 v1 运行在候选快照写入后、覆盖计算入口处因冻结协议键名与继承辅助函数键名不一致而 `KeyError` 失败关闭；当时没有读取比较器、日线价格或收益。v1 证据原样保留，v2 只冻结了语义等价的覆盖键映射，并写入独立输出根。

本轮总尝试 11 次，读取收益的开发试验 1 次；累计历史尝试 3,050 次、读取收益的开发试验 328 次。v1 和 v2 候选分区哈希一致，说明修复没有改变因子值。

## Candidate49 独立轨

Candidate49 仍是唯一前瞻候选。2026-08-25 的只读 plan 已以退出码 1 失败关闭，`ready=false`，没有 run 且不得同日重试。没有 provider 请求或历史回填，信号/执行账本仍为 0/0，哈希保持 `5193f00d…d3a79` / `d57a3e61…ea4f`。

## 证据与复核

- 协议：`docs/a_share_three_day_walkforward_campaign_297_preregistration_20260825.json`
- 最终实现冻结：`docs/a_share_three_day_walkforward_campaign_297_implementation_freeze_v2_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_297_terminal_result_20260825.json`
- 最新库政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v427_20260825.json`
- 最终输出：`.local-research/campaign_297/alpha158_interquantile_envelope_occupancy_20d_v2/`
- 保留的 v1 失败证据：`.local-research/campaign_297/alpha158_interquantile_envelope_occupancy_20d_v1/`

复核：

```bash
python -m scripts.a_share_three_day_walkforward_campaign297 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign297.py
```

本报告仅记录历史研究，不构成投资建议。
