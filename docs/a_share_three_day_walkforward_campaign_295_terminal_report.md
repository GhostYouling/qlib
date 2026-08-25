# A股三日短线因子 Campaign295 终端报告

## 结论

Campaign295 已完成固定因子 `alpha158_price_volume_directional_confirmation_20d` 的覆盖、147 项有序唯一性和三折 2019–2023 walk-forward。因子公式为 `SUMD20 × (1 + CORD20) / 2`，高方向：用 20 日价格涨跌幅度平衡保留方向，再用价格比例与成交量比例的相关性作为 0–1 确认权重。没有拟合、训练收益读取、方向搜索、horizon 搜索、阈值或组合。

覆盖和唯一性均通过，但开发结果明确失败：2021/2022/2023 mean Rank IC 分别为 -0.002571、-0.021101、-0.018083，标准化收益分别为 -29.44%、-11.04%、-42.53%，10bp 纸面收益分别为 -3.66%、-2.92%、-6.71%。三折的 Rank IC、标准化收益和 10bp 收益正折数全部为 0，最差标准化回撤 -62.05%，因此幸存者为 0，2024–2025 锁箱保持关闭，当前不可部署。

因子通过了重复控制门，所以只作为未来重复比较定义追加一次；完整定义/数值比较器库从 `166/147` 变为 `167/148`。追加不表示策略有效，也不允许对 Campaign295 反向、换 horizon、改确认权重、阈值化或与旧因子组合救援。

## 覆盖与唯一性

- 质量/上市域 1,001,781 行，候选有效 1,001,506 行。
- 日覆盖中位数 100%，P05 约 99.740%，P05 有效股票 110。
- 2019–2023 共 1,147 个会话，潜在三日非重叠 cohort 379 个。
- 147/147 个冻结比较器全部通过；最大绝对中位日 Rank 相关为 0.330185，低于 0.8。
- 唯一性门阶段没有读取日线价格或前向收益；通过后才执行唯一一次三折开发试验。

## 三折开发结果

| 验证年 | cohort | mean Rank IC | top3-bottom3 毛 spread | 标准化收益 | 10bp 收益 | 20bp 收益 |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 74 | -0.002571 | -0.009359 | -29.44% | -3.66% | -5.17% |
| 2022 | 73 | -0.021101 | 0.000378 | -11.04% | -2.92% | -4.44% |
| 2023 | 74 | -0.018083 | 0.002855 | -42.53% | -6.71% | -8.08% |

三折复合标准化收益 -63.92%，10bp -12.74%，20bp -16.70%；中位 mean Rank IC -0.018083。2021 年 10bp board-lot 可负担率 87.84%，也低于冻结的 90% 门槛。没有训练收益读取，三个验证折均执行 3 个 signal session 的边界清除，t+1/t+3 保持在同一验证分区。

## 基础设施与会计

值前目录记录 9 个概念。本轮终端哈希链 13 条：9 个概念、3 个终端前基础设施失败、1 个完整因子。三次失败分别是直接脚本入口导入上下文、全局 pytest 入口导入上下文、以及第 144 个比较器前的继承层级引用错误；全部在收益读取前失败关闭。v1 部分产物保留，科学语义不变的 v4 修正后在独立 v2 根重跑。

终态后，本地恢复工作树递归重建旧库顺序又遇到一次旧 Campaign054 指纹失败；它不在已冻结终端台账中，但单独计入基础设施会计。随后从 `/Volumes/DIsk/Disk-Coding/qlib` 只读重建，先验证旧 `166/147` 哈希，再追加 Campaign295 一次。本轮总尝试 14 次，读取收益的开发试验 1 次；累计历史尝试 3,025 次、读取收益的开发试验 326 次。

## Candidate49 独立轨

Candidate49 仍是唯一前瞻候选。2026-08-25 的只读 plan 已以退出码 1 失败关闭，`ready=false`，没有 run 且不得同日重试。没有 provider 请求或历史回填，信号/执行账本仍为 0/0，哈希保持 `5193f00d…d3a79` / `d57a3e61…ea4f`。

## 证据与复核

- 协议：`docs/a_share_three_day_walkforward_campaign_295_preregistration_20260825.json`
- 最终实现冻结：`docs/a_share_three_day_walkforward_campaign_295_implementation_freeze_v4_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_295_terminal_result_20260825.json`
- 最新库政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v425_20260825.json`
- 最终输出：`.local-research/campaign_295/alpha158_price_volume_directional_confirmation_20d_v2/`
- 保留的 v1 失败证据：`.local-research/campaign_295/alpha158_price_volume_directional_confirmation_20d_v1/`

复核：

```bash
python -m scripts.a_share_three_day_walkforward_campaign295 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign295.py
```

本报告仅记录历史研究，不构成投资建议。
