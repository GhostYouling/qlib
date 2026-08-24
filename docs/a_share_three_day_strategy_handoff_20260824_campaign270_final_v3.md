# A 股三日短线研究交接：Campaign270 最终版 v3

Campaign270 的科学结论与 v2 相同：`c269_01 issuer_facility_extreme_precipitation_or_flood_exposure` 因六项点时来源合同门全部失败，在公式、方向、字段和任何值之前终止；预测价值未测试，完整定义/比较库保持 `162/143`，收益读取开发试验保持 315。

v2 之后新增一次纯基础设施失败：首个暂存秘密扫描错误覆盖整个 Git 索引，命中 8 个既有未修改文件的 token 赋值样例，不能用于判断本轮泄密。命中内容没有打印，`.env` 未暂存。失败已进入 `research_attempt_ledger_v7.json`；当前有效会计为 17 次尝试（6 科学、11 基础设施），累计历史研究尝试 2,737。

当前有效台账为 `data/experiments/short_horizon/historical_walkforward/campaign_270/research_attempt_ledger_v7.json`，SHA-256 `c845e4770db9e7514db0c1f2e54d655d2bb4d5da7b5fa0f7c72d852b87154273`，链头 `408fb6866f553c3df443a8890b4239a14fc1958b062edcf39e1690a7f60267c8`。范围失败记录为 `docs/a_share_three_day_walkforward_campaign_270_repo_wide_secret_scan_scope_failure_20260824.json`，SHA-256 `285cbdd78dec6e2800269e5c815954dcfc72a057e6a95776ecffce1bac31c2b0`。v5 仍是无效且不在链中的保留证据；v6 和更早文件保持不变。

最终验证口径：当前状态聚焦测试 4/4，Campaign265–270 与 Candidate49 跨阶段 218 passed、6 个历史统一报告哈希节点精确排除，Black、Ruff、v7 前驱/链校验和 `git diff --check` 通过。最终秘密检查只扫描 staged diff 的新增行且不回显内容，并单独断言 `.env` 未暂存。

Candidate49 仍是唯一前瞻候选，2026-08-24 的 `stock_basic_invalid_ts_code` 继续封口，信号/执行账本 0/0。没有 provider/Web 请求、来源行、候选/比较值、价格/收益、2024–2025、当前评分、选股、仓位或订单。Campaign265 不变。

持续目标保持 `active`。下一步 Campaign271 只能侦察经济上独立、有限、值前冻结的新概念；不得用相邻灾害、阈值、方向、半径或窗口救援 Campaign269/270，也不得回填 Candidate49、启动第二个前瞻候选或把历史结果当作投资建议。
