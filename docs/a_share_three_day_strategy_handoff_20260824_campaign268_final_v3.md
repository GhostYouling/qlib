# A 股三日短线策略研究交接：Campaign268 与 Candidate49 最终版

最新权威状态为 `docs/a_share_three_day_iteration_status_20260824_campaign268_final_candidate49_failed_closed.json`（SHA-256 `f9c57c26aeb6cfca8ff02173a5b4709c5221b610ae66aeaacf1fac6366a2fb6b`）。Campaign268 有效追加台账为 `data/experiments/short_horizon/historical_walkforward/campaign_268/research_attempt_ledger_v3.json`（SHA-256 `1863995fee16d64e28c3e74074395e649a660e24d9a2cdc653ac45e3fda8a1b7`，链尖 `d25e5d155a3e6a8cbb01af1d8492e1ea5b4831409242816502085c6d04581a8e`）。Candidate49 当日失败记录为 `docs/a_share_candidate49_20260824_daily_source_failure_record.json`（SHA-256 `ec99b5af6504b55cac9f0f4b77a32a6052be3e3efec0dbe1bc7a9cd971c354e3`）。所有 v1/v2 状态与台账均保留不改写。

Campaign268 已在值前终止 Campaign157 c157_04 发行人级期权隐含偏度/期限结构路线。当前授权和已审官方元数据无法同时闭合覆盖 A 股合格分母的直接个股期权、每日点时合约及调整历史、收盘已知买卖报价质量、标的/利率/股息或持有成本、定价反解规则、曲面构建和 2019–2023 完整覆盖。这是来源合同拒绝，不是因子预测失败。

有限目录共 7 条路线且全部值前拒绝：完整个股期权曲面、Tushare `opt_daily` 加 `opt_basic`、ETF 期权映射成分股、股指期权映射成分股、收盘/结算价单独反解隐波、当前产品/合约名单回填，以及行权价/Delta/期限/流动性/子集/模型搜索。Tushare `opt_daily` 只给日线市场字段；`opt_basic` 要求 5000 积分并且没有证明每日不可变历史修订档案。ETF/指数期权是篮子或共同状态，不能在结果暴露后重贴成个股信息。

Campaign268 有效会计为 22 次尝试，其中 7 次值前科学路线、15 次基础设施失败；累计历史研究尝试 2,703，收益读取开发试验 315。完整定义/合格数值比较器保持 `162/143`；本轮选中因子、公式、方向、快照、开发试验与 2024–2025 压力试验均为 0。

2026-08-24 的 Candidate49 同日 plan 在 16:30 后以 `ready=true`、退出码 0 通过；完全相同参数的确认运行在 `daily-source-sync` 阶段因 `stock_basic_invalid_ts_code` 失败关闭，退出码 1，provider continuation 为 false。必须保留 `/Volumes/DIsk/qlib-a-share-tushare-daily-2026-08-24`，当天不得重试，也不得再次请求失败响应补细节。信号/执行账本保持 0/0，活动 Baostock 根未修改。

本轮未读取凭据值或摘要、未读取期权/候选/比较/证券价格/收益值。Campaign265 不变：v420 不存在，接受来源清单不存在，零收益审计仍因 `source_acceptance_manifest_absent_or_unsafe` 关闭。禁止 Candidate49 历史回填、Candidate50、当前评分、选股、仓位和订单。

实际 Git 仓库为 `/Volumes/DIsk/Disk-Coding/qlib`，分支为 `faet/local-test`。持续目标保持 `active`。Campaign157 的有限跨资产目录已穷尽；下一轮 Campaign269 只允许从仓库元数据出发做全新的有限概念级离线侦察，排除终止因子重组、Campaign265 修改和 Candidate49 变更。
