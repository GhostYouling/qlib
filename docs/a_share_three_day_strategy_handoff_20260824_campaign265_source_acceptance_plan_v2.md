# A 股三日短线因子研究交接（Campaign265 来源计划就绪 v2）

本文件追加修正前一版交接的终态验证会计，不改写其当时证据。前一版 SHA-256 为 `6f2788e964fb8fc2891667019c9def85f99621d8c3f020af31fc48c0b2b7b51a`。

## 有效结论

Campaign265 的 zero-network source-acceptance `plan` 仍为 `ready=true`、实际退出码 0、无 blocker。它冻结 2019-01-02 至 2025-12-31 共 1,699 个接受日，未来精确请求为 1 次 `cb_basic` 加 1,699 次 `cb_daily`，合计 1,700 次；字段、每次 1–1,999 行、1.05 秒最小 provider-entry 间隔、私有 intent/journal、原子 checkpoint/final 和终止不重试语义均不变。

planner 仍没有 credential loader、provider client、网络、写盘、`run` 或确认接口。没有读取/哈希 Token、请求来源、创建来源验收文件、读取来源/候选/比较/价格/收益值。`ready=true` 不授权执行；v418 仅授权 `plan`。

发布统一报告后，旧 adapter 阶段的发布时哈希测试按预期失效；第一次排除又使用了错误的 pytest collection-root 前缀。两条失败已独立保存，旧测试未改。最终当前状态套件为 Black/Ruff 通过、Pytest `47 passed, 1 deselected`，v4–v6 追加链通过。因此有效会计为 Campaign265 15 次尝试：8 次值前科学、7 次基础设施、完整因子尝试 0、收益读取开发试验 0；累计历史尝试 2,619，累计收益读取开发试验 315。

完整定义/数值比较器仍为 `162/143`。Candidate49 仍是唯一前瞻候选，信号/执行账本 0/0 且哈希不变；禁止历史回填、第二候选、当前评分/选股/仓位/订单和投资建议。持续目标 `请持续迭代因子。` 保持 `active`。

## 最新权威断点

- 最新状态：`docs/a_share_three_day_iteration_status_20260824_campaign265_source_acceptance_plan_ready_v2.json`，SHA-256 `38a9e8b3834643db861dedb4b16e9b3d316d117582e166980a27ecf8351cff48`。
- 政策 v418：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v418_20260824.json`，SHA-256 `f1ba460fda8fe9b51388edfb4a2de7c8a7940c0df1650a75e8d142ccef3d36a0`。
- planner：`scripts/a_share_three_day_walkforward_campaign265_source_acceptance_plan.py`，SHA-256 `1702119cc43c58843cc27575a9681214121b45084ccd0ff84489ea362eac7c05`。
- plan 结果：`docs/a_share_three_day_walkforward_campaign_265_source_acceptance_plan_result_20260824.json`，SHA-256 `03c05e8586d97d2c0e2fccb9978ab858a7f99bd77b49d5266a7706383ef2b3a5`。
- 有效验证：`docs/a_share_three_day_walkforward_campaign_265_source_acceptance_plan_validation_v2_20260824.json`，SHA-256 `4925d75621fe0625d9b34a269c2c5867fe15109e1d03a9cbee869b6d344d39bc`。
- 当前状态测试：`tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_source_acceptance_plan_current_state.py`，SHA-256 `6394b75ab008be6ed38a7f933c8cccc6c3af8bdabdcd6da98457def456d90ee1`。
- 本地追加链：`data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v6.json`，SHA-256 `fd015de31865b048f8f199759b4330dbfd3732167f174c6ab79576b865889c36`，链尖 `5fc45efdf39f4cc61a3460bc295547899bf83e492c1ad77f38d0fd681e29a8cc`。
- 两条追加失败：`docs/a_share_three_day_walkforward_campaign_265_post_plan_mutable_report_hash_test_failure_20260824.json` / `docs/a_share_three_day_walkforward_campaign_265_post_plan_pytest_deselect_prefix_failure_20260824.json`。

`data/` 与 `.env` 均保持 Git 忽略；不得强制提交本地台账、统一报告、来源目标或凭据。

## 下一步唯一允许路径

继续 Campaign265，单独设计并冻结 credential-safe 的一次性执行 workflow，但在新政策发布前只做零网络实现和合成测试。workflow 必须绑定现有 plan 最终字节，不得修改日期、字段、调用数、路径、公式或门槛；凭据加载前先独占/fsync 完整 intent/journal，每个请求前后按授权—响应—原子 checkpoint—提交事件推进，任何 inflight/来源/持久化失败均终止且禁止重请求，失败证据必须去敏。

只有未来新政策绑定 workflow/test/freeze 最终哈希、其零网络 plan `ready=true` 且实际退出码 0，并取得明确确认，才可能执行一次来源验收。来源验收成功后仍先过覆盖与 143 项唯一性门，全部通过前禁止价格/收益；2024–2025 仍保持关闭直到 2019–2023 出现非零 survivor。

当前绝不能加载凭据、发 provider 请求、启动 `run`、回填 Candidate49、启动第二前瞻候选、修改冻结门槛或把历史结果当作投资建议。
