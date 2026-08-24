# A 股三日短线因子研究交接（Campaign264）

## 当前结论

Campaign264 已完成并在值前门禁终止。它不是一条新增可交易策略：本轮只读重建冻结库并检查本地 Parquet schema 元数据，七条有限候选路线全部属于旧信息族的统计量、字段、窗口、路径或模型救援，因此选中因子为 0，未冻结公式/方向、未创建候选快照、未读取候选值/比较值/日线价格/forward return，也未运行 2019–2023 开发或 2024–2025 压力试验。

完整历史定义库保持 162 项，未来重复控制的数值比较器保持 143 项。Campaign264 的七次值前科学尝试全部写入追加式哈希链；累计历史研究尝试从 2,597 增至 2,604，累计收益读取开发试验仍为 315。这个负结果防止继续用相同信息换统计量制造“新因子”。

持续目标 `请持续迭代因子。` 仍为 `active`。Campaign265 是下一轮，但只能从真正新的、已接受的点时信息通道，或能在任何值前证明相对完整库独立的机制开始。

## 权威断点

- 最新状态：`docs/a_share_three_day_iteration_status_20260824_campaign264_prevalue_terminal.json`，SHA-256 `0b9c1cfece47523f6c7ece4190d7059ffe9d2bddb5d1b40ad92c69b32c65a45d`。
- 数值比较政策 v415：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v415_20260824.json`，SHA-256 `9af0c77afb9a3f9a1e9434914de8178c57a507f680ea17587a128aebd989b77d`。
- 值前有限路线：`docs/a_share_three_day_walkforward_campaign_264_local_schema_independent_mechanism_frontier_20260824.json`，SHA-256 `4ff4834dd6044d6937f1abde82edbe316351b05dca839b5985597de944199c8b`。
- 终端结果：`docs/a_share_three_day_walkforward_campaign_264_terminal_result_20260824.json`，SHA-256 `c746ac55551bec7eef833ab312d710ee64fa765d7e266397e676bc7a1dec362e`。
- 终端报告：`docs/a_share_three_day_walkforward_campaign_264_terminal_report.md`，SHA-256 `0f7ced26eb814dd5eecd072b73d70739c04fb5392ce4f4c75cfc57ed6974356a`。
- 验证记录：`docs/a_share_three_day_walkforward_campaign_264_terminal_validation_20260824.json`，SHA-256 `52c6c6a14dc82e4b3e897690dbc78a87d55abcfb114edb77336f9cae75ca40df`。
- 本地追加式台账：`data/experiments/short_horizon/historical_walkforward/campaign_264/research_attempt_ledger_v1.json`，SHA-256 `a97c2cfa64f2d86fb40386479ac301d1ad5dfa04e53d3ff54263dfdabbb85bb6`，链尖 `19f0cc33cef72207d8e0c62721b86c5fc8d36d56a024503a76ef240b6359e49d`。

`data/` 下的台账和统一研究报告是本地证据，受仓库忽略规则保护；不要用 `git add -f` 强行提交。旧 Campaign263 状态、旧政策和旧终止记录都不得改写。

## 验证与复现

在权威工作树 `/Volumes/DIsk/Disk-Coding/qlib` 中运行：

```bash
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m black --check tests/data_collector_tests/test_a_share_three_day_walkforward_campaign264_terminal.py
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m ruff check tests/data_collector_tests/test_a_share_three_day_walkforward_campaign264_terminal.py
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest tests/data_collector_tests/test_a_share_three_day_walkforward_campaign264_terminal.py -q
```

发布时结果为 Black 通过、Ruff 通过、Pytest `7 passed`。测试会重建 162 个完整定义和 143 个数值比较器，校验所有权威相对/绝对路径哈希、七项台账链、统一报告单一标题以及 Candidate49 的 0/0 空账本。

## Campaign265 接续规则

1. 先从 v415、最新状态和完整 162/143 冻结库恢复；不要从某个“最佳结果”恢复。
2. 在任何值前写出有限 candidate library，并冻结公式、方向、输入字段、点时/缺失/零值语义、过滤、覆盖门、143 项有序唯一性门、成本、组合/拟合方法和幸存规则。
3. 不得重试、反向、变换、改字段、改窗口、残差化、交互、重加权、建模或组合 Campaign264 的七条路线；旧终止因子只能作为事前冻结的完整重复控制库，不能救援。
4. 只有完整候选通过覆盖和全部 143 项有序数值唯一性门，才可打开 2019–2023 三组冻结扩展训练/验证折；分区边界清除三个信号会话，且 t+1/t+3 必须落在同一分区。
5. 2024–2025 保持关闭；只有开发 survivor 存在且整个有限 campaign 的库、搜索空间、模型、成本、门禁、数据/代码指纹已冻结，才可一次性打开，并标为历史已暴露的准样本外。
6. 每个公式、方向、参数、过滤、子集、模型、成功、失败和基础设施尝试都追加记录，不得只保留最佳结果。历史结果不得生成当前评分、选股、仓位或订单，也不构成投资建议。

## Candidate49 独立前瞻层

Candidate49 仍是唯一前瞻候选；信号账本和执行账本均为 0 条，禁止历史收益、信号或执行回填，也禁止启动 Candidate50。其冻结工作流协议为 `docs/a_share_tushare_candidate49_future_session_workflow_protocol.json`，SHA-256 `6ff5636a3f7ef65e93452098186b3aecf9231d68873ab8a1070afb91d699ef7c`。

发布状态记录于 2026-08-24 11:36:50 Asia/Singapore，早于 16:30，因此未执行 plan/run、未请求 provider/Web，绝对日期 staging root `/Volumes/DIsk/qlib-a-share-tushare-daily-2026-08-24` 不存在。只有目标交易日同日 16:30 后才先运行 `plan`；仅当 `ready=true` 且退出码为 0，才可使用完全相同参数运行 `run --confirm-run`。source gate 失败时必须保留失败记录并禁止同日重试。

当前日线数据根为 `/Volumes/DIsk/Disk-Coding/qlib/data`，分钟数据根为 `/Volumes/DIsk/qlib-a-share-tushare-1m`。仓库 `.env` 是 Git 忽略的 `0600` 普通文件，安全检查只确认存在唯一非空 `TUSHARE_TOKEN` 赋值；不得打印、哈希、提交或写入文档其秘密值。
