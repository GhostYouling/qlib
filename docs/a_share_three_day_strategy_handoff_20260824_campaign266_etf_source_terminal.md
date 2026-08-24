# A 股三日短线策略研究交接：Campaign266 ETF 来源值前终止

## 当前结论

持续研究目标仍为 `active`，目标原文是“请持续迭代因子。”本轮已完成一次有效迭代：Campaign157 c157_03 的 ETF 一级市场压力路线在读取任何来源值或收益前被终止。终止原因是当前 3000 积分和点时要求下没有完整来源合同，不是因子回测失败。

当前可用的低积分接口不能安全拼出该机制：`fund_share` 没有首次公开时点和申购/赎回事件拆分，`fund_basic` 只有自由文本基准且没有历史映射版本，`index_weight` 是月度指数权重而不是每日 ETF PCF。精确 ETF 映射、份额规模及沪深每日 PCF 接口要求 8000 积分；季度 `fund_portfolio` 要求 5000 积分且频率错误。因此本轮没有要求升级积分、没有调用 provider，也没有创建一个看似能跑但含未来函数的代理回测。

## 权威入口

- 最新状态：`docs/a_share_three_day_iteration_status_20260824_campaign266_etf_source_terminal.json`
- Campaign266 来源前沿：`docs/a_share_three_day_walkforward_campaign_266_etf_primary_market_source_frontier_20260824.json`
- Campaign266 终止结果：`docs/a_share_three_day_walkforward_campaign_266_terminal_result_20260824.json`
- Campaign266 报告：`docs/a_share_three_day_walkforward_campaign_266_terminal_report.md`
- 追加式台账：`data/experiments/short_horizon/historical_walkforward/campaign_266/research_attempt_ledger_v1.json`
- 冻结历史政策：`docs/a_share_three_day_historical_walkforward_research_policy_20260727.json`
- 当前数值政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v419_20260824_execution_path_hardening_v2.json`
- Campaign265 交接：`docs/a_share_three_day_strategy_handoff_20260824_campaign265_no_return_audit_runner_ready.md`

实际 Git 仓库是 `/Volumes/DIsk/Disk-Coding/qlib`，分支为 `faet/local-test`。`/Users/niyufei/Coding/qlib` 当前只是非 Git 目录，不应作为提交工作树；权威 `data/experiments/...` 台账也位于卷路径仓库内。

## 本轮会计

- 有限路线：6。
- 选中因子、公式、方向、候选快照、完整定义和数值比较器追加：全部 0。
- 开发试验和 2024–2025 压力试验：全部 0。
- Campaign266：15 次尝试，其中 6 次值前科学尝试、9 次已恢复的基础设施失败。
- 累计历史研究尝试：2,663；累计收益读取开发试验：315。
- 完整定义/合格数值比较器：保持 `162/143`。

## Campaign265 不变

Campaign265 的 `convertible_bond_equity_parity_premium_compression_3s` 仍停在来源快照前。`v420` 未发布，接受来源清单不存在，真实零收益审计 `plan` 的唯一 blocker 仍是 `source_acceptance_manifest_absent_or_unsafe`。Campaign266 不授权发布 v420、读取 `.env`、创建 provider client 或发出来源请求。

只有用户未来明确授权 v420 和 Campaign265 来源获取时，才可沿原 Campaign265 交接中的逐步命令继续；不得把“持续迭代”解释为来源执行授权。

## Candidate49 不变

Candidate49 仍是唯一前瞻候选，信号/执行账本为 0/0。禁止历史回填、Candidate50、当前评分、选股、仓位或订单。历史滚动研究和 Candidate49 未来观察继续保持双轨隔离。

## 下一轮安全工作

下一轮可以独立审计 Campaign157 c157_02“发行人债券信用利差—股票背离”的官方来源元数据，仍需在任何行值前冻结有限来源目录、干净收益/基准曲线、陈旧价格、违约、同发行人多债聚合、发行人—A 股映射、完整分母及首次公开时点。若合同不能闭合，就值前终止并转向 c157_04；不得用稀疏已观察债券反向选择样本。

ETF c157_03 只有在新的已授权来源能够事前证明完整 2019–2023 申赎事件、版本化 ETF 映射、每日篮子、首次公开时间、企业行动、重叠分配和全市场分母后才可重开。不得用二级市场量价、当前名单回填、低积分字段拼接、换滞后/窗口/子集/模型或旧因子组合救援。
