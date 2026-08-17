# Campaign161 债务期限结构因子终态报告

Campaign161 已在收益读取前终止，不是因为历史样本不足，而是唯一事前冻结的数据入口没有返回合同要求的 `result` 对象。一次性验收计划先以 `ready=true`、退出码 0 通过；随后固定请求 `RPT_DMSK_FN_BALANCE` 的 2023-12-31 分区，运行以 `response_result_object_missing`、退出码 3 fail-closed。原始响应没有打印或保存，验收意图与失败记录已使任何重试永久失效。

本轮有限目录共 6 项。相关组件均衡、语义族均衡、连续相关度权重、单调样条 GAM 与 PCA/autoencoder 五条组合或模型路线，分别属于 Campaign133、134、144 已终止家族的重参数化或救援，均在读值前关闭。唯一进入来源验收的定义为 higher 因子：

`(LONG_LOAN + BOND_PAYABLE) / (SHORT_LOAN + SHORT_BOND_PAYABLE + NONCURRENT_LIAB_1YEAR + LONG_LOAN + BOND_PAYABLE)`

五个字段必须全部存在、有限且非负，总借款必须严格为正；没有参数、筛选、子集、组合或模型。这个完整定义追加到历史定义库，使定义数从 157 变为 158；由于没有读到来源行、更没有形成数值序列，数值比较器保持 142 项。该终止定义以后只能作为完整、事前冻结的历史特征库成员使用，不能单独重试、换字段或救援。

后续 2019–2023 全量来源、容量、142 项有序唯一性、三折 walk-forward 和收益读取均未获授权；2024–2025 继续关闭。Campaign161 共记 12 次尝试：6 次科学概念和 6 次基础设施失败，累计历史尝试 1408，收益读取开发试验仍为 314。Candidate49 信号与执行账本仍各 0 条且哈希未变；没有当前评分、选股、仓位或订单。本报告不构成投资建议。

权威终态为 `docs/a_share_three_day_walkforward_campaign_161_terminal_result_20260815.json`（SHA-256 `7d0ece85c5abc213a9ecb65c3b281c545ed13450c61aeac7fbd08e2a4b24d8e0`）。持续目标保持 active，下一轮只能从 Campaign162 的有限离线值前审查开始。
