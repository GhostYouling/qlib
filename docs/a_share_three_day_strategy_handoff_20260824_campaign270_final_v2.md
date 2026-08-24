# A 股三日短线研究交接：Campaign270 最终版 v2

## 最终结论

Campaign270 已完成并终止 `c269_01 issuer_facility_extreme_precipitation_or_flood_exposure` 的来源路线。它只做了零行、零网络来源合同审查，没有进入因子或收益阶段。点时设施主表、点时实体—设施映射、版本化极端降水/洪涝观测、公开/修订时钟、空间连接和全发行人零暴露分母六项合取门全部失败；因此公式、方向、字段、阈值、半径和窗口均未冻结，预测价值没有被测试。

完整定义/数值比较库仍为 `162/143`。Campaign270 最终有效会计为 16 次尝试：6 次值前科学门、10 次基础设施失败、0 个完整因子、0 次收益读取开发试验、0 个 survivor 和 0 次 2024–2025 压力试验。累计历史研究尝试为 2,736，累计收益读取开发试验仍为 315。

## 当前权威链

- 事前合同：`docs/a_share_three_day_walkforward_campaign_270_facility_flood_source_contract_preregistration_20260824.json`，SHA-256 `f5f7c24ffca6aa9e5c4853ff199439721b1a6faf5be056fb4e0ea88d340c3053`。
- 科学终止结果：`docs/a_share_three_day_walkforward_campaign_270_terminal_source_contract_result_20260824.json`，SHA-256 `b78f742a51823dff5829c0dd7b78ec3348b86c87e975ebfe84283632b2219307`。
- 当前有效追加台账：`data/experiments/short_horizon/historical_walkforward/campaign_270/research_attempt_ledger_v6.json`，SHA-256 `d2783a1bdb6575c380a8e772d96b20e6aada70d25225c0d6c8832cc460276ea6`，链头 `f3385ec1ba6c7b2756abf138304d0dfca8271acd95ad45bbc9994232d57da1dd`。
- 当前状态测试：`tests/data_collector_tests/test_a_share_three_day_walkforward_campaign270_final_current_state.py`，SHA-256 `c21ab8254b3c08363aa803ffdf4addeec7fbef2806f92a2ac3db04340b25c56f`。
- 初始终端报告：`docs/a_share_three_day_walkforward_campaign_270_terminal_source_contract_report.md`，SHA-256 `9f5262aab1e29d207a7fc3f8a71e7da26f20d23372b764b84164537190df4f7f`；后续基础设施会计按追加记录进入统一报告和本交接。

`research_attempt_ledger_v5.json` 是明确的无效基础设施证据：它误填了 v4 文件 SHA，在使用前被发现，不能进入有效链。其 SHA-256 为 `38af979e39ca96b54bea518371efeb855377b547785ab91830c894ef006102d5`；绑定失败记录为 `docs/a_share_three_day_walkforward_campaign_270_attempt_ledger_v5_binding_failure_20260824.json`，SHA-256 `5e1a3c34b553cb275a32c7250b70ea31544f4a0becff3412cb0e88649377c1d9`。v6 从真实 v4 直接继续。

## 基础设施失败清单

10 次失败均已记录且未读取研究值：两次技能长段读取截断；`rain` 子串误命中 `train`；猜测 JSON 键得到空投影；报告字面断言导致 6 过 1 败；合并 `jq` 打印完整文档导致输出截断；混合暂存命令因 `/data/` 忽略规则非零退出并部分暂存；跨阶段运行遗漏会话句柄导致不完整输出作废；旧 publication-state 统一报告哈希节点在报告继续追加后失败；无效 v5 前驱文件哈希绑定。

## Candidate49 与凭据边界

Candidate49 仍是唯一前瞻候选。2026-08-24 已因 `stock_basic_invalid_ts_code` 失败封口；保留 `/Volumes/DIsk/qlib-a-share-tushare-daily-2026-08-24`，当天不得重试或重请求失败详情。信号/执行账本保持 0/0，SHA-256 分别为 `5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79` / `d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f`。

`.env` 仅验证为普通文件、0600、Git 忽略、恰好一个非空 `TUSHARE_TOKEN`；没有打印、读取或散列秘密。本轮没有 Web/provider 请求、来源行、候选/比较值、价格/收益、2024–2025、当前评分、选股、仓位或订单。Campaign265 不变，v420 和接受来源清单仍不存在。

## 最终验证

当前状态聚焦测试 4/4 通过；Campaign265–270 与 Candidate49 跨阶段套件 218 项通过，6 个绑定旧统一报告哈希的历史节点精确排除。旧失败命令的非零或不完整输出均未用作通过证据。Black、Ruff、有效 v6 前驱/哈希链校验和 `git diff --check` 通过。

## 下一步

持续目标保持 `active`。Campaign271 可以随时开始一个经济上真正独立、有限且值前冻结的新概念；不必等日线或 16:30。不得用极端冷热、台风、地震、空气污染、公共卫生、洪涝阈值、方向、空间半径或事件窗口救援 Campaign269/270，也不得重组终止因子、回填 Candidate49、启动第二个前瞻候选或把历史结果当作投资建议。
