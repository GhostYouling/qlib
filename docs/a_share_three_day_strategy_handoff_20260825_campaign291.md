# A股三日短线因子研究交接文档（Campaign291）

## 当前结论

Campaign291 已完整结束：Alpha158 同日中位状态共识强度因子覆盖和 144/144 去重均通过，但只有 1/3 折 Rank IC 为正，三折标准化收益与含成本收益全部为负，存活者为 0。该方向已终止，不得反向、改中位阈值、119 支持、权重、过滤或与 Campaign290 组合进行事后救援。2024–2025 未打开，当前没有可部署的新策略。

因子通过无收益门后按事前规则进入重复控制库，完整定义/数值比较器由 `163/144` 更新为 `164/145`；新顺序 SHA-256 为 `641331e8…bb1e6b1` / `d1dbf29b…8facf61`。这不是投资价值认证。

## 权威入口

- 工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- 分支：`faet/local-test`
- 协议：`docs/a_share_three_day_walkforward_campaign_291_preregistration_20260825.json`
- 实现冻结：`docs/a_share_three_day_walkforward_campaign_291_implementation_freeze_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_291_terminal_result_20260825.json`
- 人类可读报告：`docs/a_share_three_day_walkforward_campaign_291_terminal_report.md`
- 最新库政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v421_20260825.json`
- 本地证据根：`data/experiments/short_horizon/historical_walkforward/campaign_291/alpha158_session_median_state_consensus_strength_v1/`
- 终端校验：`PYTHONPATH=. python -m scripts.a_share_three_day_walkforward_campaign291 verify`

`data/experiments/` 受忽略规则保护，不随 Git 提交；Git 文档以 SHA-256 绑定本地候选快照、无收益审计、终端结果和 8 条哈希链台账。不要移动、重写或清理 Campaign286–291 的本地证据。

## 核心数据

| 年份 | Rank IC | 标准化收益 | 最大回撤 | 10bp | 20bp |
|---|---:|---:|---:|---:|---:|
| 2021 | +0.00464 | -4.1597% | -34.7957% | -1.4817% | -3.4870% |
| 2022 | -0.00702 | -25.1660% | -26.5935% | -5.8689% | -7.1605% |
| 2023 | -0.00045 | -22.0596% | -29.2165% | -4.8913% | -6.7668% |

复合标准化/10bp/20bp 为 -44.10%/-11.80%/-16.46%。覆盖中位数/P05 均为 100%，最大去重相关 0.0551，与 Campaign290 相关 0.0394。结果表明问题不是数据覆盖或重复，而是冻结高方向在三日历史验证中的经济表现不稳定且成本后全面为负。

## 不可跨越边界

- Candidate49 是唯一活动前瞻候选；禁止历史信号、收益、执行或里程碑回填。
- Candidate49 信号/执行账本仍为 0/0，SHA-256 为 `5193f00d…d3a79` / `d57a3e61…ea4f`。
- Campaign291 的高方向、同日绝对共识公式、精确中位状态、119 支持、等权和无拟合口径均已终止；不得反向、改阈值、签名或组合救援。
- 不得打开 Campaign291 的 2024–2025，不得从历史输出生成当前评分、选股、仓位或订单。
- Candidate49 日常流程仍只能在目标交易日同日 16:30 Asia/Singapore 后先 `plan`，且仅 `ready=true`、退出码 0 时用完全相同参数 `run --confirm-run`。
- v421 是 Campaign291 的库更新，不是 Campaign265 缺失的来源采集授权；Campaign265 仍保持关闭。

## 下一安全动作

持续目标保持 active。Campaign292 可以随时做零网络离线值前概念侦察，但必须是新的有限机制，先查 `164/145` 库并冻结公式、方向、过滤、支持、成本、门禁和数据/代码指纹；不得围绕 Campaign291 做方向、状态分箱、阈值、签名或组合搜索。Candidate49 前瞻轨继续独立观察。
