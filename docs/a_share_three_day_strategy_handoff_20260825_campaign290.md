# A股三日短线因子研究交接文档（Campaign290）

## 当前结论

Campaign290 已完整结束：Alpha158 三态持续度因子覆盖和 143/143 去重均通过，但 2021–2023 三折 Rank IC、标准化收益与含成本收益全面为负，存活者为 0。该方向已终止，不得反向、改分位阈值、滞后、支持数或权重进行事后救援。2024–2025 未打开，当前没有可部署的新策略。

因子通过无收益门后按事前规则进入重复控制库，完整定义/数值比较器由 `162/143` 更新为 `163/144`；新顺序 SHA-256 为 `2d7ae946…faa6c802` / `c026c008…d94bdeff`。这不是投资价值认证。

## 权威入口

- 工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- 分支：`faet/local-test`
- 协议：`docs/a_share_three_day_walkforward_campaign_290_preregistration_20260825.json`
- 实现冻结：`docs/a_share_three_day_walkforward_campaign_290_implementation_freeze_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_290_terminal_result_20260825.json`
- 人类可读报告：`docs/a_share_three_day_walkforward_campaign_290_terminal_report.md`
- 最新库政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v420_20260825.json`
- 本地证据根：`data/experiments/short_horizon/historical_walkforward/campaign_290/alpha158_session_median_state_persistence_v1/`
- 终端校验：`python -m scripts.a_share_three_day_walkforward_campaign290 verify`

`data/experiments/` 受忽略规则保护，不随 Git 提交；Git 文档以 SHA-256 绑定本地候选快照、无收益审计、终端结果和 9 条哈希链台账。不要移动、重写或清理 Campaign286–290 的本地证据。

## 核心数据

| 年份 | Rank IC | 标准化收益 | 最大回撤 | 10bp | 20bp |
|---|---:|---:|---:|---:|---:|
| 2021 | -0.00536 | -25.7894% | -42.4409% | -5.7659% | -7.2625% |
| 2022 | -0.00002 | -48.7622% | -49.5293% | -8.5740% | -10.4408% |
| 2023 | -0.00314 | -9.9440% | -23.8767% | -2.3418% | -3.9714% |

复合标准化/10bp/20bp 为 -65.76%/-15.86%/-20.24%。覆盖中位数/P05 为 99.92%/92.97%，最大去重相关 0.1697。结果表明问题不是数据覆盖或重复，而是冻结方向在历史验证中的经济表现为负。

## 不可跨越边界

- Candidate49 是唯一活动前瞻候选；禁止历史信号、收益、执行或里程碑回填。
- Candidate49 信号/执行账本仍为 0/0，SHA-256 为 `5193f00d…d3a79` / `d57a3e61…ea4f`。
- Campaign290 的高方向、中位三态、1 会话滞后、119 支持、等权和无拟合口径均已终止；任何反向或参数变化必须作为新的机制独立 campaign 事前冻结，且不能表述为 Campaign290 修复。
- 不得打开 Campaign290 的 2024–2025，不得从历史输出生成当前评分、选股、仓位或订单。
- Candidate49 日常流程仍只能在目标交易日同日 16:30 Asia/Singapore 后先 `plan`，且仅 `ready=true`、退出码 0 时用完全相同参数 `run --confirm-run`。
- v420 是 Campaign290 的库更新，不是 Campaign265 缺失的来源采集授权；Campaign265 仍保持关闭。

## 下一安全动作

持续目标保持 active。Campaign291 可以随时做零网络离线值前概念侦察，但必须是新的有限机制，先查 `163/144` 库并冻结公式、方向、过滤、支持、成本、门禁和数据/代码指纹；不得围绕 Campaign290 做方向、状态分箱、滞后或加权搜索。Candidate49 前瞻轨继续独立观察。
