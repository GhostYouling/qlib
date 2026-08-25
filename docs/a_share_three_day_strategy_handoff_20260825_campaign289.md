# A股三日短线因子研究交接文档（Campaign289）

## 交接结论

Campaign289 已完整结束：一个固定 8 位随机超平面哈希桶均值模型完成 2019–2023 三折滚动开发，存活者为 0。它出现了弱而一致的正 Rank IC 和两折正标准化收益，但无法覆盖交易成本，且 2022 回撤和整手可负担率失败。2024–2025 没有打开，当前没有可部署的新策略。

持续研究目标保持 active。Campaign289 及其二元中位状态、种子 289、8 个超平面、256 桶、96 名/会话样本、桶均值、回退、成本与门禁均已终止；不得事后调参挽救。下一轮必须从新的有限 Campaign290 概念开始。

## 工作区与权威入口

- 可写 Git 工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- 分支：`faet/local-test`
- Campaign289 协议：`docs/a_share_three_day_walkforward_campaign_289_preregistration_20260825.json`
- 零收益设计：`data/experiments/short_horizon/historical_walkforward/campaign_289/binary_hash_cell_mean_v1/design_evidence.json`
- 原失败根：`data/experiments/short_horizon/historical_walkforward/campaign_289/binary_hash_cell_mean_v1/`
- 恢复 v1 失败根：`data/experiments/short_horizon/historical_walkforward/campaign_289/binary_hash_cell_mean_recovery_v1/`
- 终端输出根：`data/experiments/short_horizon/historical_walkforward/campaign_289/binary_hash_cell_mean_recovery_v2/`
- 终端台账：终端输出根下 `terminal_trial_ledger.json`
- 终端报告：`docs/a_share_three_day_walkforward_campaign_289_terminal_report.md`
- 只读校验器：`scripts/a_share_three_day_walkforward_campaign289_terminal_verify.py`

`data/experiments/` 受忽略规则保护，不随 Git 提交；文档以 SHA-256 绑定本地研究证据。不要清理、移动或重写 Campaign286–289 的输出目录。

## 核心指标

| 年份 | Rank IC | 毛价差 | 标准化收益 | 最大回撤 | 10bp | 20bp | 可负担率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 0.00057 | 0.4966% | 4.5031% | -19.1557% | -1.5611% | -2.9325% | 94.59% |
| 2022 | 0.01122 | 0.0629% | -6.6066% | -36.1281% | -2.4997% | -4.2579% | 89.45% |
| 2023 | 0.00852 | -0.1379% | 13.3526% | -15.6738% | 0.2750% | -1.7267% | 93.69% |

三折复合标准化/10bp/20bp 收益为 `+10.63%/-3.76%/-8.67%`。正 Rank IC 3/3、正标准化收益 2/3，但正 10bp 只有 1/3；最差回撤、20bp 聚合和折 2 可负担率失败，所以必须拒绝。

## 恢复审计

- 原失败：折 1 训练收益读取后、模型拟合前，同行集合绑定不一致。
- 恢复 v1 失败：仍在模型拟合前，不可用连接行 NaN 被严格哈希校验拒绝。
- 恢复 v2：只把已经不可用的整行填为中性 0；可用行和全部科学参数不变，随后完成三折。
- 折 1 训练收益读取共 3 次，其中恢复重读 2 次；两次失败均未读验证收益。
- 终端台账 10 条：7 个事前概念、2 次基础设施失败、1 个模型试验。

## 复核命令

```bash
MPLCONFIGDIR=/private/tmp/campaign289-mpl python -m scripts.a_share_three_day_walkforward_campaign289_terminal_verify verify
MPLCONFIGDIR=/private/tmp/campaign289-mpl python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign289.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign289_recovery.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign289_recovery_v2.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign289_finalize.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign289_terminal_verify.py
```

校验器应返回 `verified_terminal_no_survivor_lockbox_closed`。它同时验证 19 个终端产物、10 条哈希链台账、两次失败、三折验证读取、0 个存活者、锁箱关闭和 Candidate49 空账本。

## 不可跨越的边界

- Candidate49 保持唯一活动前瞻候选；禁止历史信号、收益或执行回填。
- Candidate49 信号/执行账本均为 0 条，SHA-256 为 `5193f00d…d3a79` / `d57a3e61…ea4f`。
- 不得修改或重跑 Campaign289 的二元状态、超平面、位数、种子、样本、支持、回退、目标、成本、阈值或门禁。
- 不得把历史输出直接转成当前评分、选股、仓位或订单，也不得表述为投资建议。
- Candidate49 当日流程仍须目标交易日同日 16:30 Asia/Singapore 后先 `plan`；仅 `ready=true` 且退出码 0 才能以完全相同参数 `run --confirm-run`。本轮在窗口前完成，没有运行网络流程。
- 部分人工 `recorded_at` 元数据晚于实际命令时间；不要用它判断执行顺序。使用 intent/failure 的 UTC 时间、文件 SHA-256、输出根和台账哈希链。

## 下一安全动作

Campaign290 可在任何时间继续零网络离线研究，但必须采用新的、有限且机制独立的概念目录。不得围绕 Campaign289 的 8 位哈希做位数、种子、表数、支持阈值、平滑或成本后修补。Alpha360 只在获得足够授权可写容量后重新评估。Candidate49 继续作为独立前瞻确认层。
