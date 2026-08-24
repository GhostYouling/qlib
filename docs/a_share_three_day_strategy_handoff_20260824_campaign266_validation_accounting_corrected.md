# A 股三日短线策略研究交接：Campaign266 最终会计

## 最新状态

以 `docs/a_share_three_day_iteration_status_20260824_campaign266_validation_accounting_corrected.json` 为最新权威状态。Campaign266 已把 Campaign157 c157_03 ETF 一级市场压力路线在值前终止：这是来源合同不完整，不是预测失败。详细机制、接口字段与六条拒绝路线见 `docs/a_share_three_day_walkforward_campaign_266_etf_primary_market_source_frontier_20260824.json`；初始完整交接保留在 `docs/a_share_three_day_strategy_handoff_20260824_campaign266_etf_source_terminal.md`。

首轮验证中，聚焦测试文件需要 Black 机械格式化。该轮 JSON、Ruff 和 7 项测试虽通过，但整体不作为最终验证；失败已追加到 `data/experiments/short_horizon/historical_walkforward/campaign_266/research_attempt_ledger_v2.json`。最终有效会计为 16 次尝试（6 科学、10 基础设施），累计历史研究尝试 2,664，收益读取开发试验 315。ETF 科学结论和 `162/143` 库不变。

## 操作边界

- 实际 Git 仓库：`/Volumes/DIsk/Disk-Coding/qlib`；分支：`faet/local-test`。
- `/Users/niyufei/Coding/qlib` 不是 Git 工作树，不要从该路径提交或读取权威台账。
- 当前 3000 积分边界不支持 8000 积分的精确 ETF 映射、份额规模和沪深 PCF 接口；不要请求、抽样或建议为本路线升级。
- 不得用 `fund_share`、自由文本 benchmark、月度 `index_weight`、季度持仓或 ETF 二级市场量价拼出历史代理。
- Campaign265 不变：v420 未发布、来源清单不存在、审计 blocker 仍是 `source_acceptance_manifest_absent_or_unsafe`，本轮不授权来源执行。
- Candidate49 仍是唯一前瞻候选且账本 0/0；禁止回填、Candidate50、当前评分、选股、仓位或订单。

## 下一轮

持续目标仍为 `active`。下一轮从 Campaign157 c157_02 发行人债券信用利差—股票背离开始，只允许做一份有限、官方元数据级、值前来源审计。必须在任何行值前证明干净收益/基准曲线、陈旧价格、违约和停牌、同发行人多债聚合、发行人—A 股映射、无债发行人分母、首次公开时点及完整 2019–2023 覆盖。若不能闭合，直接值前终止并转向 c157_04，不得先看稀疏债券值再选样本。
