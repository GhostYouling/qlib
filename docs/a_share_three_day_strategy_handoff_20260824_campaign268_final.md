# A 股三日短线策略研究交接：Campaign268 最终版

最新权威状态为 `docs/a_share_three_day_iteration_status_20260824_campaign268_option_source_terminal.json`（SHA-256 `3cd69e7b432465301a0168da8c27a3e3ccfcb8262b830e09a548492b460c992e`），权威台账为 `data/experiments/short_horizon/historical_walkforward/campaign_268/research_attempt_ledger_v1.json`（SHA-256 `9c266aade2156383257fda3bee7f518849bb27149f582242a61488e1eb6b0d47`，链尖 `876860a51cb90bb50b52eccc9e7a53704330641364b3acb4a7a549e7ecc8b7db`）。

Campaign268 已在值前终止 Campaign157 c157_04 发行人级期权隐含偏度/期限结构路线。当前授权和已审官方元数据无法同时闭合覆盖 A 股合格分母的直接个股期权、每日点时合约及调整历史、收盘已知买卖报价质量、标的/利率/股息或持有成本、定价反解规则、曲面构建和 2019–2023 完整覆盖。这是来源合同拒绝，不是因子预测失败。

有限目录共 7 条路线且全部值前拒绝：完整个股期权曲面、Tushare `opt_daily` 加 `opt_basic`、ETF 期权映射成分股、股指期权映射成分股、收盘/结算价单独反解隐波、当前产品/合约名单回填，以及行权价/Delta/期限/流动性/子集/模型搜索。不得先看稀疏期权值再选标的、行权价或期限，也不得把 ETF/指数共同状态重贴为个股信息。

Tushare `opt_daily` 要求 2000 积分但字段只有 OHLC、结算、成交量/额与持仓；`opt_basic` 要求 5000 积分，超过当前 3000 积分边界，并且公开合同没有证明每日不可变历史修订档案。本轮未请求升级或接口行。上交所/深交所本轮审阅的产品是少数 ETF 期权，中金所是指数期权，均不能直接形成全市场发行人横截面。

最终会计为 20 次尝试，其中 7 次值前科学路线、13 次完整保留的基础设施失败；累计历史研究尝试 2,701，收益读取开发试验 315。完整定义/合格数值比较器保持 `162/143`；本轮选中因子、公式、方向、快照、来源请求、开发试验与 2024–2025 压力试验均为 0。

本轮只读仓库元数据和官方公开文档；只核验 `.env` 中 Token 非空且文件私有、Git 忽略，未读取凭据值或摘要、未创建 provider client、未请求来源行、未读取期权/候选/比较/证券价格/收益值。Campaign265 不变：v420 不存在，接受来源清单不存在，零收益审计仍因 `source_acceptance_manifest_absent_or_unsafe` 关闭。Candidate49 仍是唯一前瞻候选，信号/执行账本保持 0/0；禁止回填、Candidate50、当前评分、选股、仓位和订单。

实际 Git 仓库为 `/Volumes/DIsk/Disk-Coding/qlib`，分支为 `faet/local-test`；`/Users/niyufei/Coding/qlib` 不是 Git 工作树。持续目标保持 `active`。Campaign157 的有限跨资产目录现已穷尽：c157_01 仍由 Campaign265 独立冻结，c157_02/c157_03/c157_04 已来源合同终止，c157_05/c157_06 已是终止组合。下一轮 Campaign269 只允许从仓库元数据出发做全新的有限概念级离线侦察，排除终止因子重组、Campaign265 修改和 Candidate49 变更。
