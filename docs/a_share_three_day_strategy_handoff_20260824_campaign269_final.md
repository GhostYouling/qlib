# A 股三日短线策略研究交接：Campaign269 最终验证版

最新权威状态为 `docs/a_share_three_day_iteration_status_20260824_campaign269_final_validated.json`（SHA-256 `f77e4128b40c2efdcfd4a97b0b093b51fcf9f621ce5e057457e826980bbc6654`）。Campaign269 当前追加式台账为 `data/experiments/short_horizon/historical_walkforward/campaign_269/research_attempt_ledger_v6.json`（SHA-256 `8dad1656cfdd22a1e8af34112fea1118ae8092790cb1623bd9b042c1177fc41c`，连同 v1–v5 共 17 条，链尖 `5973b1ad6f374f57d8e12df029b0f7f79994ed868f767ea2122cc50acb0fc21d`）。前序 Campaign268 状态、台账及所有终止证据保持不变。

Campaign269 完成了一个有限、零网络、概念级外部信息前沿。目录有 6 条路线：设施极端降水/洪涝、极端冷热、台风风雨、地震地面运动、空气污染应急限产和公共卫生移动限制。唯一保留给下一阶段来源合同的是 `c269_01 issuer_facility_extreme_precipitation_or_flood_exposure`。它要求外部灾害状态通过点时有效的法律实体—子公司—设施历史映射归属到发行人，因此不同于终止的环境会计、处罚、事故披露和市场因子。

`c269_01` 仍然只是概念，不是因子。公式、方向、来源字段、阈值、空间半径和事件窗口均未冻结；没有来源合同、adapter、provider 请求或值读取。仓库当前缺少被接受的 2019–2023 设施主数据、坐标和运营区间、灾害观测版本及修订、空间连接、公开时钟和覆盖全部发行人的零暴露分母。这个结果只说明该路线值得单独审来源合同，不说明数据可用或策略有效。

其余路线处理如下：冷热与台风因会在基础合同前搜索灾害类型、阈值、半径、持续时间和方向而拒绝；地震与空气污染应急限产作为未选中的独立来源延期保留；公共卫生限制因制度样本非平稳且政策与设施映射不可识别而拒绝。若 c269_01 的合同闭合失败，不得转试这些同族变量来救援。

Campaign269 有效会计为 17 次尝试，其中 6 次值前科学路线、11 次基础设施失败；累计历史研究尝试 2,720，累计收益读取开发试验 315。完整定义/数值比较器保持 `162/143`，本轮完整因子、开发试验、survivor 和 2024–2025 压力试验均为 0。前 5 次失败为两次技能输出截断、一次错误 Candidate49 账本路径只读探测、一次宽范围来源盘点截断和一次合并报告长尾读取截断；终态阶段又如实记录补丁上下文失配、非 Git 工作区入口只读检查和过宽合并检索截断。两次跨阶段回归还分别因排除参数形式和 pytest 根目录 node ID 前缀错误命中 4 个旧统一报告哈希节点；非零输出均作废且未读取研究值，只读收集确认正确 node ID 前缀为 `data_collector_tests/` 后已通过。首次混合暂存命令又因 `data/` 忽略规则退出 1，虽部分文件已暂存但没有提交；该失败也保留在台账。

本轮没有读取凭据值或摘要、来源行、候选/比较值、日线价格或 forward return，也没有请求 provider 或 Web。Campaign265 保持原样：v420 不存在、接受来源清单不存在、零收益审计仍由 `source_acceptance_manifest_absent_or_unsafe` 关闭。

Candidate49 仍是唯一前瞻候选。2026-08-24 的同日工作流已在 Campaign268 阶段因 `stock_basic_invalid_ts_code` 失败封口，保留 `/Volumes/DIsk/qlib-a-share-tushare-daily-2026-08-24`，当天不得重试或再次请求失败详情。Campaign269 没有运行 plan/run；信号/执行账本继续为 0/0，SHA-256 分别为 `5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79` 和 `d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f`。

验证结果：Campaign269 聚焦测试 7 项通过；Campaign265–269 与 Candidate49 跨阶段回归 200 项通过，6 个可变统一报告历史哈希节点按设计排除；10 个 Campaign269 JSON 解析、Black、Ruff 和 `git diff --check` 均通过。

下一轮唯一安全工作是 Campaign270：先做 c269_01 的有限零行来源合同可行性审查，并在任何行之前冻结发行人/子公司/设施身份与运营区间、灾害来源及版本修订、公开时钟、空间连接、全发行人零暴露分母、2019–2023 完整覆盖、缺失语义、最终公式、方向、支持门和后续冻结边界。合同不能闭合就值前终止，不得先看值再选灾害类型、阈值、半径、方向或窗口。

实际 Git 仓库为 `/Volumes/DIsk/Disk-Coding/qlib`，分支为 `faet/local-test`。持续目标保持 `active`。历史研究结果不构成投资建议，也不授权 Candidate49 回填、Candidate50、当前评分、选股、仓位或订单。
