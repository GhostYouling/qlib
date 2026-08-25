# A股三日短线因子研究交接（Campaign302）

## 当前结论

Campaign302 已不可变终止，没有形成可部署策略。完整 Alpha360 + 固定时序 Transformer 的零收益设计三折成功，第一折也完成了 8,369 行、5 epoch 的训练，但在读取任何验证收益之前，冻结执行器因 `DatetimeIndex.eq()` 不存在而退出。这个结果只说明实现阶段失败，不能解释为预测失败或预测通过。

历史库保持 `172/153`；2024–2025 没有打开；Candidate49 仍是唯一活动前瞻候选，信号/执行账本均为 0，SHA 分别为 `5193f00d…3a79` 和 `d57a3e61…ea4f`。没有生成当前评分、选股、仓位或订单，也不构成投资建议。

## 本轮策略定义

- 完整 360 维 Alpha360，按固定顺序重塑为 60×6 时序，不做特征子集或缺失指标搜索。
- 8 维、2 头、1 层 Transformer，固定正弦位置编码，AdamW、5 epoch、seed 302、无早停。
- 每个训练信号会话先按哈希固定抽 64 只，至少 50 只通过 270/360 有限特征门槛；中位数/IQR 仅在预选训练样本上拟合。
- 三组 expanding walk-forward：2019–2020→2021、2019–2021→2022、2019–2022→2023；清除 3 个边界信号会话。
- 信号收盘生成，t+1 开盘进入、t+3 收盘退出，Top3；固定成本、整手、参与率、阻塞买卖规则。

## 实际证据

- 零收益设计：3/3 折完成，训练特征持久化 54,197,216 字节。
- 第一折训练：8,369 行、5 epoch；训练损失 `0.208604 → 0.092226`。
- 第一折验证：2021 Alpha360 特征流式评分完成；分数门禁、分数快照和验证指标均未完成。
- 验证收益：0 折读取；第二、三折模型未训练；2024–2025 未打开。
- 终止错误：`AttributeError: 'DatetimeIndex' object has no attribute 'eq'`，冻结位置 `scripts/a_share_three_day_walkforward_campaign302.py:960`，退出码 1。
- 同 Campaign 重试：禁止且未执行；冻结 runner 在失败后保持未修改。

## 权威入口

- 最新状态：`docs/a_share_three_day_iteration_status_20260825_campaign302_terminal.json`
- 预注册：`docs/a_share_three_day_walkforward_campaign_302_preregistration_20260825.json`
- 设计实现冻结：`docs/a_share_three_day_walkforward_campaign_302_design_implementation_freeze_20260825.json`
- 开发执行冻结：`docs/a_share_three_day_walkforward_campaign_302_development_execution_freeze_20260825.json`
- 失败裁定：`docs/a_share_three_day_walkforward_campaign_302_development_failure_adjudication_20260825.json`
- 追加式终态台账：`docs/a_share_three_day_walkforward_campaign_302_terminal_trial_ledger_20260825.json`
- 终态结果：`docs/a_share_three_day_walkforward_campaign_302_terminal_result_20260825.json`
- 数值比较政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v432_20260825.json`
- 终止报告：`docs/a_share_three_day_walkforward_campaign_302_terminal_report.md`

## 本机研究产物

当前机器上的忽略目录 `.local-research/campaign_302/alpha360_streamed_transformer_8d_1l_v1/` 保存三折设计矩阵、第一折模型、训练报告和失败记录。核心指纹已由失败裁定文档绑定；该目录约 52 MiB，受 `.gitignore` 保护，不应强制提交到 Git，也不得作为当前评分或实盘输入。

## 不可变边界

- 不得修改冻结的 Campaign302 runner 后沿用 `campaign_302` 重跑，不得从训练损失推断策略表现。
- 不得声称该候选已预测失败或已验证通过；验证收益没有读取。
- 不得把 Campaign302 追加进完整因子定义或数值比较器，库保持 `172/153`。
- Campaign286–302 的终止记录不得改写或通过结果后调方向、窗口、阈值、特征、模型、成本、seed、组合来救援。
- Candidate49 保持唯一活动前瞻候选；禁止历史回填、第二候选、2026-08-25 同日重试、失败码绕过和实盘下单。
- 历史结果不得生成当前评分、选股、仓位或订单；2024–2025 继续关闭。
- 工作区 `data` 外部链接与既有追踪删除属于用户/外部状态，提交时不得 stage、恢复、删除或改写。

## 复核

```bash
cd /Users/niyufei/Coding/qlib/recovery-worktree
python -m pytest -q \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign302.py \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign302_publication.py
python -m ruff check \
  scripts/a_share_three_day_walkforward_campaign302.py \
  scripts/a_share_three_day_walkforward_campaign302_torch_worker.py \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign302.py \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign302_publication.py
```

## 后续恢复

只有两条合规路径：一是创建新的、单独预注册的实现恢复 Campaign，仅修复 API 兼容问题并保持 Campaign302 所有科学选择完全不变，同时计作新尝试；二是从真正的新信息通道开始。任何恢复都必须先冻结代码/数据/折/成本/门禁，不能先看 Campaign302 验证收益，也不能复用 Campaign302 标识。

截至本交接，累计历史研究尝试为 3,119，累计读取收益的开发尝试为 332；当前研究目标由用户决定是否继续，不因本次实现失败自动转为可交易策略。
