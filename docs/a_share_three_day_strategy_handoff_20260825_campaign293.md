# A股三日短线因子研究交接文档（Campaign293）

## 当前结论

Campaign293 已完整结束：Alpha158 多 horizon 同行百分位平滑度因子覆盖和 146/146 去重均通过，但三折复合标准化/10bp/20bp 收益为 -30.79%/-5.04%/-9.79%，存活者为 0。该方向已终止，不得反向、改 5/10/20/30/60 horizon、22 家族支持、权重、过滤、阈值或与 Campaign290–292 组合救援。2024–2025 未打开，当前没有可部署的新策略。

因子通过无收益门后按事前规则进入重复控制库，完整定义/数值比较器由 `165/146` 更新为 `166/147`；新顺序 SHA-256 为 `57662d72…ace06f` / `5a771c4f…914c1`。这不是投资价值认证。

## 权威入口

- 工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- 分支：`faet/local-test`
- 协议：`docs/a_share_three_day_walkforward_campaign_293_preregistration_20260825.json`
- 最终实现冻结：`docs/a_share_three_day_walkforward_campaign_293_implementation_freeze_v2_20260825.json`
- 文档化终态：`docs/a_share_three_day_walkforward_campaign_293_terminal_result_20260825.json`
- 人类可读报告：`docs/a_share_three_day_walkforward_campaign_293_terminal_report.md`
- 最新库政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v423_20260825.json`
- 最终本地证据根：`.local-research/campaign_293/alpha158_multi_horizon_peer_rank_smoothness_v2/`
- 保留的 v1 失败证据根：`data/experiments/short_horizon/historical_walkforward/campaign_293/alpha158_multi_horizon_peer_rank_smoothness_v1/`
- 终端校验：`PYTHONPATH=. python -m scripts.a_share_three_day_walkforward_campaign293 verify`

`.local-research/` 与 `data/` 都受 Git 忽略规则保护；Git 文档以 SHA-256 绑定本地候选快照、无收益审计、终端结果和 10 条哈希链运行台账。运行期间 `data` 被外部切换为 `/Volumes/DIsk/Disk-Coding/qlib-data/recovery-worktree` 的符号链接，Git 因而显示既有 tracked data 删除和一个未跟踪 symlink；这些外部变化不属于 Campaign293 提交，禁止暂存、恢复、删除或覆盖。v1/v2 证据都必须保留。

## 核心结果

| 年份 | Rank IC | 标准化收益 | 最大回撤 | 10bp | 20bp |
|---|---:|---:|---:|---:|---:|
| 2021 | -0.00178 | -40.4420% | -60.0292% | -8.0384% | -9.4348% |
| 2022 | +0.00643 | +35.8953% | -32.5529% | +5.5645% | +3.6425% |
| 2023 | +0.00278 | -14.4878% | -67.0045% | -2.1830% | -3.8924% |

问题不是覆盖或重复：有效 1,001,588/1,001,781 行，P05 日覆盖约 99.89%，最大去重相关仅 0.2745。问题是收益不稳健：仅 2022 一折的标准化和成本后收益为正，2021/2023 都为负，且 2021 的整手可负担率不足。不能挑选表现最好的单折。

## 失败记录与复核

- `campaign293_infrastructure_001`：恢复工作树没有复制 Candidate49 忽略账本，且首次只读核查猜错测试文件名；未读研究值，权威账本随后按冻结路径验证为 0/0。
- `campaign293_infrastructure_002`：v1 在完成候选快照和 146/146 去重后，因外部 `data` symlink 的只读权限在发布 no-return audit 时 EPERM；未读任何日线收益。只替换输出根并完整从零重启。
- `campaign293_infrastructure_003`：终态后只读摘要错误访问不存在的 `comparisons` 键；verify 已先通过，修正读取 `results`，未改变终态。
- `campaign293_infrastructure_004`：旧 Campaign292 发布测试错误要求通用交接页永远停在 Campaign292；22 通过、1 失败，随后改为校验其专属交接，由 Campaign293 套件校验最新入口，未读研究值。
- 最终 v2：Python compile、Ruff、7/7 runner 专用测试和 plan 均通过，完整 run 与 verify 通过；存活者 0，锁箱关闭。

## 不可跨越边界

- Candidate49 是唯一活动前瞻候选；禁止历史信号、收益、执行或里程碑回填。
- Candidate49 信号/执行账本仍为 0/0，SHA-256 为 `5193f00d…d3a79` / `d57a3e61…ea4f`。
- Campaign293 的高方向、29 家族、五档 horizon、22 完整家族支持、同行平均并列百分位、相邻差绝对值等权和无拟合口径均已终止；不得反向、调参或组合救援。
- 不得打开 Campaign293 的 2024–2025，不得从历史输出生成当前评分、选股、仓位或订单。
- Candidate49 日常流程仍只能在目标交易日同日 16:30 Asia/Singapore 后先 `plan`，且仅 `ready=true`、退出码 0 时用完全相同参数 `run --confirm-run`。
- v423 是 Campaign293 的重复控制库更新，不是任何缺失来源的采集授权。
- 权威来源仓 `/Volumes/DIsk/Disk-Coding/qlib` 有既存未跟踪 Campaign286 文件；不要纳入本分支或修改。

## 下一安全动作

持续目标保持 active。Campaign294 可以随时做零网络离线值前概念侦察，但必须是新的有限机制，先查 `166/147` 库并冻结公式、方向、过滤、支持、成本、门禁和数据/代码指纹；不得围绕 Campaign293 做方向、horizon、支持、阈值、权重或组合搜索。Candidate49 前瞻轨继续独立观察。
