# A股三日短线因子研究交接文档（Campaign292）

## 当前结论

Campaign292 已完整结束：Alpha158 同日同行百分位极端度广度因子覆盖和 145/145 去重均通过，但三折 Rank IC 全为负、三折标准化收益全为负，前两折整手可负担率不足，存活者为 0。该方向已终止，不得反向、改百分位映射、119 支持、权重、过滤、阈值或与 Campaign290/291 组合救援。2024–2025 未打开，当前没有可部署的新策略。

因子通过无收益门后按事前规则进入重复控制库，完整定义/数值比较器由 `164/145` 更新为 `165/146`；新顺序 SHA-256 为 `bf2f4640…82c127` / `f9abd865…1a8344`。这不是投资价值认证。

## 权威入口

- 工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- 分支：`faet/local-test`
- 协议：`docs/a_share_three_day_walkforward_campaign_292_preregistration_20260825.json`
- 最终实现冻结：`docs/a_share_three_day_walkforward_campaign_292_implementation_freeze_v4_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_292_terminal_result_20260825.json`
- 人类可读报告：`docs/a_share_three_day_walkforward_campaign_292_terminal_report.md`
- 最新库政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v422_20260825.json`
- 最终本地证据根：`data/experiments/short_horizon/historical_walkforward/campaign_292/alpha158_session_peer_rank_extremity_breadth_v2/`
- 保留的失败证据根：`data/experiments/short_horizon/historical_walkforward/campaign_292/alpha158_session_peer_rank_extremity_breadth_v1/`
- 终端校验：`PYTHONPATH=. python -m scripts.a_share_three_day_walkforward_campaign292 verify`

`data/experiments/` 受忽略规则保护，不随 Git 提交；Git 文档以 SHA-256 绑定本地候选快照、无收益审计、终端结果和 11 条哈希链台账。不要移动、重写或清理 Campaign286–292 的本地证据。工作区卷在终态后只剩约 378 MiB，不要重跑 Campaign292 或复制大型证据到该卷。

## 核心数据

| 年份 | Rank IC | 标准化收益 | 最大回撤 | 10bp | 20bp |
|---|---:|---:|---:|---:|---:|
| 2021 | -0.02717 | -15.2888% | -56.5757% | -3.9543% | -5.6172% |
| 2022 | -0.02328 | -53.5937% | -60.4193% | -8.2515% | -9.3741% |
| 2023 | -0.02946 | -7.2696% | -61.2276% | +0.5350% | -0.9762% |

复合标准化/10bp/20bp 为 -63.55%/-11.41%/-15.30%。覆盖中位数/P05 均为 100%，最大去重相关 0.3793；与 Campaign290/291 的相关分别为 0.3793/0.0205。问题不是覆盖或重复，而是冻结高方向在三日历史验证中的预测关系持续为负，且执行门禁也未通过。

## 失败记录与复核

- `campaign292_infrastructure_001`：第一次运行在折 3 绑定发布前 ENOSPC；两折收益已读，终态未发布，v1 部分输出原样保留。
- `campaign292_infrastructure_002`：v2 元数据 plan 测试误把临时输出根参与冻结校验；9 通过、1 失败，未读研究值。
- `campaign292_infrastructure_003`：直接文件调用无法导入 `scripts`；未读研究值，后续固定使用 `python -m`。
- `campaign292_infrastructure_004`：发布测试错误要求两份历史报告全文一致；12 通过、1 失败，Campaign292 区段实际均存在，未读研究值。
- 最终 v4：Ruff 通过、10/10 runner 专用测试通过、plan `ready=true` 后完整运行，verify 通过；修正后的 runner + 发布套件 13/13 通过。

## 不可跨越边界

- Candidate49 是唯一活动前瞻候选；禁止历史信号、收益、执行或里程碑回填。
- Candidate49 信号/执行账本仍为 0/0，SHA-256 为 `5193f00d…d3a79` / `d57a3e61…ea4f`。
- Campaign292 的高方向、同行平均并列百分位、居中绝对极端度、119 支持、等权和无拟合口径均已终止；不得反向、改阈值、签名或组合救援。
- 不得打开 Campaign292 的 2024–2025，不得从历史输出生成当前评分、选股、仓位或订单。
- Candidate49 日常流程仍只能在目标交易日同日 16:30 Asia/Singapore 后先 `plan`，且仅 `ready=true`、退出码 0 时用完全相同参数 `run --confirm-run`。
- v422 是 Campaign292 的重复控制库更新，不是任何缺失来源的采集授权。
- 权威来源仓 `/Volumes/DIsk/Disk-Coding/qlib` 有既存未跟踪 Campaign286 文件；不要纳入本分支或修改。

## 下一安全动作

持续目标保持 active。Campaign293 可以随时做零网络离线值前概念侦察，但必须是新的有限机制，先查 `165/146` 库并冻结公式、方向、过滤、支持、成本、门禁和数据/代码指纹；不得围绕 Campaign292 做方向、百分位、极端度、阈值、权重或组合搜索。Candidate49 前瞻轨继续独立观察。
