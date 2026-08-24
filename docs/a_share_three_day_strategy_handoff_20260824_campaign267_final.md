# A 股三日短线策略研究交接：Campaign267 最终版

最新权威状态为 `docs/a_share_three_day_iteration_status_20260824_campaign267_credit_spread_source_terminal.json`（SHA-256 `8af1b81a4433fd71d17900ea4623772e3c948ffce3c389d92fcc0d129b86d9bd`），权威台账为 `data/experiments/short_horizon/historical_walkforward/campaign_267/research_attempt_ledger_v1.json`（SHA-256 `3982c1e26415c8805dcbf71afd007f02b7a4aa8763bdef29b5d05b2a1ab042a7`，链尖 `fe246bd88e2bde789be0238af195a78a04edb4a495b282582dfe7b7f71b2d1b4`）。

Campaign267 已在值前终止 Campaign157 c157_02 发行人债券信用利差—股票背离路线。当前授权和已审官方元数据无法同时闭合通用发行人债券清洁收益率、期限匹配基准、首次公开/修订时钟、版本化债券—法律发行人—A 股映射、可选性/优先级/担保/违约处理、多债聚合以及包含无债发行人的 2019–2023 完整分母。这是来源合同拒绝，不是因子预测失败。

有限目录共 7 条路线且全部值前拒绝：精确清洁收益率、OTC 报价代理、债券大宗交易代理、可转债估值/溢价替代、评级类别曲线替代、当前中债估值/存续名单回填，以及稀疏已观测债券上的子集/滞后/聚合/模型搜索。不得先看债券值再选择有数据的发行人，也不得把 Campaign265 的可转债来源族重贴为通用信用利差。

最终会计为 16 次尝试，其中 7 次值前科学路线、9 次完整保留的基础设施失败；累计历史研究尝试 2,681，收益读取开发试验 315。完整定义/合格数值比较器保持 `162/143`；本轮选中因子、公式、方向、快照、来源请求、开发试验与 2024–2025 压力试验均为 0。

本轮只读仓库元数据和官方公开文档；未读取凭据值或摘要、未创建 provider client、未请求来源行、未读取候选/比较/价格/收益值。Campaign265 不变：v420 不存在，接受来源清单不存在，零收益审计仍因 `source_acceptance_manifest_absent_or_unsafe` 关闭。Candidate49 仍是唯一前瞻候选，信号/执行账本保持 0/0；禁止回填、Candidate50、当前评分、选股、仓位和订单。

实际 Git 仓库为 `/Volumes/DIsk/Disk-Coding/qlib`，分支为 `faet/local-test`；`/Users/niyufei/Coding/qlib` 仍不是 Git 工作树。持续目标保持 `active`。下一轮只对 Campaign157 c157_04 期权隐含偏度/期限结构做独立、有限、官方元数据级值前来源审计；若合同不能在读取值前完整闭合，就终止该路线并保留“预测价值未测试”的语义。
