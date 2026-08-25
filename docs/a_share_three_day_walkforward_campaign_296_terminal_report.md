# A股三日短线因子 Campaign296 终端报告

## 结论

Campaign296 已完成固定因子 `alpha158_linear_trend_quality_10d = BETA10 × RSQR10` 的覆盖、148 项有序唯一性和三折 2019–2023 walk-forward。高方向的含义是：保留十日标准化收盘价趋势斜率的正负方向，再用同窗口线性拟合优度衰减噪声趋势。没有拟合、训练收益读取、方向搜索、窗口搜索、阈值、筛选或组合。

覆盖和唯一性均通过，但开发结果明确失败：2021/2022/2023 mean Rank IC 分别为 -0.011620、-0.017736、-0.036596，标准化收益分别为 -46.75%、-42.21%、-41.24%，10bp 纸面收益分别为 -9.75%、-5.66%、-6.05%。三折的 Rank IC、spread、标准化收益和成本后收益全部为负，幸存者为 0；2024–2025 锁箱保持关闭，当前不可部署。

因子通过了重复控制门，所以只作为未来重复比较定义追加一次；完整定义/数值比较器库从 `167/148` 变为 `168/149`。追加不表示策略有效，也不允许对 Campaign296 反向、换窗口、替换或重加权 RSQR10、阈值化，或与旧因子组合救援。

## 覆盖与唯一性

- 质量/上市域 1,001,781 行，候选有效 1,001,402 行。
- 日覆盖中位数 100%，P05 约 99.728%，P05 有效股票约 110.3。
- 2019–2023 共 1,147 个会话，潜在三日非重叠 cohort 379 个。
- 148/148 个冻结比较器全部通过；最大绝对中位日 Rank 相关为 0.573464，对应 Campaign295，低于 0.8。
- 唯一性门阶段没有读取日线价格或前向收益；通过后才执行唯一一次三折开发试验。

## 三折开发结果

| 验证年 | cohort | mean Rank IC | top3-bottom3 毛 spread | 标准化收益 | 10bp 收益 | 20bp 收益 |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 74 | -0.011620 | -0.010186 | -46.75% | -9.75% | -10.78% |
| 2022 | 73 | -0.017736 | -0.000532 | -42.21% | -5.66% | -6.53% |
| 2023 | 74 | -0.036596 | -0.004533 | -41.24% | -6.05% | -7.64% |

三折复合标准化收益 -81.92%，10bp -20.02%，20bp -22.98%；中位 mean Rank IC -0.017736，最差标准化回撤 -70.33%。2021/2022 年 10bp board-lot 可负担率 88.18%/88.99%，也低于冻结的 90% 门槛。没有训练收益读取，三个验证折均执行 3 个 signal session 的边界清除，t+1/t+3 保持在同一验证分区。

## 基础设施与会计

值前目录记录 9 个概念。本轮终端哈希链 14 条：9 个概念、4 个基础设施失败、1 个完整因子。四次失败分别是 zsh 标量拆分导致的只读 SHA 核验错误、比较器方向摘要误设为全 higher、当前恢复树的旧 Campaign054 指纹阻止库顺序导入，以及第 148 个比较器的继承辅助函数错误限定 `[0,1]`。前三次发生在 Campaign296 数值读取前，第四次发生在候选与前 147 个比较器读取后、收益读取前；全部失败关闭并保留。

v1 部分产物保持不变；v3 实现仅把 Campaign295 的合法比较器范围显式设为 `[-1,1]`，在独立 v2 根重跑。v2 候选逐分区哈希与 v1 一致。本轮总尝试 14 次，读取收益的开发试验 1 次；累计历史尝试 3,039 次、读取收益的开发试验 327 次。

## Candidate49 独立轨

Candidate49 仍是唯一前瞻候选。2026-08-25 的只读 plan 已以退出码 1 失败关闭，`ready=false`，没有 run 且不得同日重试。没有 provider 请求或历史回填，信号/执行账本仍为 0/0，哈希保持 `5193f00d…d3a79` / `d57a3e61…ea4f`。

## 证据与复核

- 协议：`docs/a_share_three_day_walkforward_campaign_296_preregistration_20260825.json`
- 最终实现冻结：`docs/a_share_three_day_walkforward_campaign_296_implementation_freeze_v3_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_296_terminal_result_20260825.json`
- 最新库政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v426_20260825.json`
- 最终输出：`.local-research/campaign_296/alpha158_linear_trend_quality_10d_v2/`
- 保留的 v1 失败证据：`.local-research/campaign_296/alpha158_linear_trend_quality_10d_v1/`

复核：

```bash
python -m scripts.a_share_three_day_walkforward_campaign296 verify
python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign296.py
```

本报告仅记录历史研究，不构成投资建议。
