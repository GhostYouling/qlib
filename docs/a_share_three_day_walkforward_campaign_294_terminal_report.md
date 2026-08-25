# A股三日短线因子 Campaign294 终端报告

## 结论

Campaign294 已在无收益门终止，未消耗任何开发收益试验。固定因子 `alpha158_same_horizon_cross_family_peer_rank_consensus_5h` 的覆盖门通过，但与 Campaign292 `alpha158_session_peer_rank_extremity_breadth_1d` 的中位日 Rank 相关为 -0.985178，绝对值远高于冻结上限 0.8。语义上它测量同一 horizon 内的跨算子方差，数值上却是 Campaign292 极端度广度的反向近重复；绝对相关门禁正是为了阻止这种换公式、换符号式重复研究。

因此第 146 项失败后按序停止，第 147 项 Campaign293 比较器未读，历史日线价格和前向收益均未读，2019–2023 三折开发没有启动，2024–2025 锁箱没有打开。因子不得反向、改用 IQR/MAD/熵、改变 22 家族支持、选择单一 horizon、重加权或与旧 Alpha158 因子组合救援。完整定义/数值比较器库保持 `166/147` 不变。

## 因子与覆盖

每个会话、每个 Alpha158 horizon 坐标先在有限 model-support 同行中计算升序平均并列秩百分位。对每只股票分别在 5/10/20/30/60 日 horizon 内跨 29 个算子家族计算总体方差；每个 horizon 至少 22 个有限家族，五个 horizon 都须满足。得分为 `1 - 4 × 五个方差的等权均值`，高方向，13 个非 horizon 坐标不参与，没有填充、裁剪、权重、拟合或组合。

- 质量/上市域 1,001,781 行，候选有效 1,001,589 行。
- 日覆盖中位数 100%，P05 约 99.889%，P05 有效股票 110.3。
- 三日非重叠潜在 cohort 379 个，覆盖 2019–2023 五年。
- 146 个已读取比较器中 145 个通过；第 146 个失败，最大绝对相关即 0.985178。
- 与 Campaign290/291 的绝对相关为 0.409107/0.000737；与 Campaign292 为 0.985178。

覆盖充分不等于机制独立。该结果说明“跨算子一致性”和“坐标极端度广度”在当前 Alpha158 数据上几乎形成一对反向排序，不能再用这个方向消耗收益样本。

## 基础设施与会计

值前目录记录 8 个概念。本轮另有 3 个基础设施失败：一次在源仓工作目录导入恢复工作树模块失败；一次初版协议手工转录 Campaign292 数据集 SHA 时被截断，随后以只覆盖该哈希的 v2 协议校正；一次 v1 在 143 项比较后引用错误的 helper 层级，未读收益，随后只修正 `Campaign293.prior` 下的原函数并用独立 v2 根从零重跑。v1 半成品保持不改。

终端哈希链共 12 条：8 个值前概念、3 个基础设施失败、1 个完整因子。Campaign294 有效总尝试 12 次，读取收益的开发试验 0 次；累计历史尝试 3,011 次、读取收益的开发试验仍为 325 次。

## Candidate49 独立轨

2026-08-25 16:30 后执行了一次只读 plan。它以退出码 1 失败关闭，因为活动日线状态没有暴露恰好一个来源；`ready=false`，没有执行 run，也不允许同日重试。没有 provider 请求，信号/执行账本仍为 0/0，哈希保持 `5193f00d…d3a79` / `d57a3e61…ea4f`。

## 证据与复核

- 有效协议校正：`docs/a_share_three_day_walkforward_campaign_294_preregistration_v2_20260825.json`
- 最终实现冻结：`docs/a_share_three_day_walkforward_campaign_294_implementation_freeze_v2_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_294_terminal_result_20260825.json`
- 最终输出：`.local-research/campaign_294/alpha158_same_horizon_cross_family_peer_rank_consensus_v2/`
- v1 失败证据：`.local-research/campaign_294/alpha158_same_horizon_cross_family_peer_rank_consensus_v1/`

复核：

```bash
PYTHONPATH=. python -m scripts.a_share_three_day_walkforward_campaign294 verify
PYTHONPATH=. python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign294.py
```

本报告仅记录历史研究，不构成投资建议。
