# A 股三日短线研究交接：Campaign270

## 当前结论

Campaign270 已完成。它不是一次收益回测，而是对 Campaign269 唯一保留概念 `c269_01 issuer_facility_extreme_precipitation_or_flood_exposure` 的零行、零网络来源合同审查。六项事前冻结的合取门全部失败，因此该概念已在公式、方向、字段、灾害阈值、空间半径、事件窗口和任何来源行之前终止；预测价值没有被测试。

失败的六项合同分别是：点时设施主表、点时发行人—实体—子公司—设施映射、版本化极端降水/洪涝观测、公开时间与修订链、确定性空间身份与连接、全发行人零暴露分母及后续三日 walk-forward 协议。`scripts/` 中相应天气/洪涝/气象和地理空间/设施 ID 接入均为 0；文档命中只是当前路线或旧来源缺失记录，没有接受清单或适配器。

## 权威文件

- 来源合同事前冻结：`docs/a_share_three_day_walkforward_campaign_270_facility_flood_source_contract_preregistration_20260824.json`，SHA-256 `f5f7c24ffca6aa9e5c4853ff199439721b1a6faf5be056fb4e0ea88d340c3053`。
- 原始终止结果：`docs/a_share_three_day_walkforward_campaign_270_terminal_source_contract_result_20260824.json`，SHA-256 `b78f742a51823dff5829c0dd7b78ec3348b86c87e975ebfe84283632b2219307`。
- 终端验证失败记录：`docs/a_share_three_day_walkforward_campaign_270_terminal_validation_failure_record_20260824.json`，SHA-256 `dc6ba9772d8f0b0c9bfe4acd46512e420af118f784ad1ce927cf43c2e2ce2b1d`。
- 初始/追加台账：`data/experiments/short_horizon/historical_walkforward/campaign_270/research_attempt_ledger_v1.json` / `research_attempt_ledger_v2.json`，SHA-256 分别为 `d5d4a76274df2e443321ee0f6c7ab92e964ba379f4c826252658b714b006bb34` / `1e310a1dfa9e64387fbbc5688d536762fee99daf40b14c595496789fd907967f`；当前链头为 `0c0db3c66ac88810b0d678191de7f852d49a55ae6dbb027b5f91e6cfa05ec14e`。
- 研究报告：`docs/a_share_three_day_walkforward_campaign_270_terminal_source_contract_report.md`，SHA-256 `9f5262aab1e29d207a7fc3f8a71e7da26f20d23372b764b84164537190df4f7f`。
- 聚焦测试：`tests/data_collector_tests/test_a_share_three_day_walkforward_campaign270_terminal.py`，SHA-256 `40cc462ed9563e5a07189b896b5c513a045df0c05e569cd2205435a419c5fc4f`。

## 会计与边界

Campaign270 有效会计为 12 次尝试：6 次值前科学合同门、6 次基础设施失败、0 个完整因子、0 次收益读取开发试验、0 个 survivor、0 次 2024–2025 压力试验。累计历史研究尝试为 2,732，累计收益读取开发试验仍为 315；完整定义/数值比较库保持 `162/143`。

六次基础设施失败全部保留：两次技能合并读取截断、一次 `rain` 子串误命中 `train`、一次猜测 JSON 键的空投影、一次报告字面断言导致的 6 过 1 败，以及一次合并 `jq` 打印完整文档造成的输出截断。所有失败输出均作废，没有读取或改变研究值。

本轮没有读取来源行、候选值、比较值、日线价格、forward return 或 2024–2025 压力收益；没有请求 Web/provider；没有读取或散列 token。`.env` 只验证为普通 0600、Git 忽略、一个非空 `TUSHARE_TOKEN`。Campaign265 不变，v420 和接受来源清单仍不存在。

Candidate49 仍是唯一前瞻候选。2026-08-24 同日来源运行此前已因 `stock_basic_invalid_ts_code` 失败封口，保留 `/Volumes/DIsk/qlib-a-share-tushare-daily-2026-08-24`，当天不得重试或重请求失败详情。信号/执行账本继续为 0/0，SHA-256 分别为 `5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79` / `d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f`。

## 验证结果

Campaign270 聚焦测试 7/7 通过；Campaign265–270 与 Candidate49 跨阶段回归 211 项通过，5 个明确绑定旧统一报告发布哈希的历史节点按设计排除。Black、Ruff、3 个有界 JSON 结构检查和 `git diff --check` 均通过。

## 下一步

持续目标保持 `active`。Campaign271 可以随时做新的零网络历史概念侦察，不必等待日线或 16:30，但必须是一个经济上真正独立、有限且值前冻结的机制。不得用极端冷热、台风、地震、空气污染、公共卫生、洪涝阈值、方向、空间半径或事件窗口救援 Campaign269/270；也不得重组终止因子、启动第二个前瞻候选、回填 Candidate49、生成当前评分/选股/仓位/订单或把历史结果当作投资建议。
