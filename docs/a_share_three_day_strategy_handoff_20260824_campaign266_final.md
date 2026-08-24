# A 股三日短线策略研究交接：Campaign266 最终版

最新权威状态为 `docs/a_share_three_day_iteration_status_20260824_campaign266_final_accounting_corrected.json`，权威台账为 `data/experiments/short_horizon/historical_walkforward/campaign_266/research_attempt_ledger_v3.json`。

Campaign266 已在值前终止 ETF 一级市场压力路线。3000 积分内的 `fund_share`、`fund_basic` 和月度 `index_weight` 缺少历史映射版本、首次公开时间、份额企业行动与每日 PCF 语义；精确 ETF 映射、份额规模和沪深 PCF 接口要求 8000 积分；季度持仓要求 5000 积分且频率错误。这是来源合同拒绝，不是预测失败，没有请求 provider、读取值或要求升级积分。

最终有效会计为 17 次尝试，其中 6 次值前科学路线、11 次完整保留的基础设施失败；累计历史研究尝试 2,665，收益读取开发试验 315。完整定义/合格数值比较器保持 `162/143`，选中因子、公式、方向、候选快照、开发试验和 2024–2025 压力试验均为 0。

Campaign265 不变：v420 未发布，接受来源清单不存在，零收益审计仍因 `source_acceptance_manifest_absent_or_unsafe` 关闭，本轮不授权 `.env`、provider client 或来源请求。Candidate49 仍是唯一前瞻候选且账本 0/0；禁止回填、Candidate50、当前评分、选股、仓位或订单。

实际 Git 仓库为 `/Volumes/DIsk/Disk-Coding/qlib`，分支为 `faet/local-test`；`/Users/niyufei/Coding/qlib` 不是 Git 工作树。持续目标保持 `active`。下一轮只对 Campaign157 c157_02 发行人债券信用利差—股票背离做有限、官方元数据级、值前来源审计；不能闭合完整历史与点时合同就终止并转向 c157_04，不得先看稀疏债券值再选样本。
