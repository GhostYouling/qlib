# A 股三日短线因子研究交接（Campaign265 来源验收计划就绪）

## 当前断点

Campaign265 仍在研究中，持续目标 `请持续迭代因子。` 保持 `active`。冻结候选是 higher `convertible_bond_equity_parity_premium_compression_3s`：同一 exact `CB` 在 `t-3` 与 `t` 两端都活动、有有限 `cb_over_rate` 且 `amount > 0` 时，单债值为 `cb_over_rate(t-3)-cb_over_rate(t)`；同一正股多只合格转债取算术中位数，无合格值保持缺失。

零网络 source-acceptance planner 已完成。唯一 `plan` 返回 `ready=true`、实际退出码 0、单个 JSON、无 blocker。它冻结 2019-01-02 至 2025-12-31 共 1,699 个接受日，未来请求严格为 1 次 `cb_basic` 与逐日 1,699 次 `cb_daily`，总计 1,700 次；每次至少 1 行、严格少于 2,000 行，最小 provider-entry 间隔 1.05 秒。字段、日期、调用顺序、私有路径、intent/journal、原子 checkpoint、精确前缀恢复与终止不重试语义均已固定。

这不是来源验收成功，也不是因子有效或可交易结论。planner 没有读取 `.env`/环境凭据，没有 provider client、传输、写盘、`run` 或确认接口。本轮没有读取/哈希 Token 值，没有 provider 请求、来源行、候选/比较器值、日线价格或 forward return。`ready=true` 只说明离线计划完整，绝不授权执行。

完整定义/数值比较器仍为 `162/143`；Campaign265 完整因子、开发试验、survivor 与 2024–2025 压力试验均为 0。有效会计为 13 次尝试：8 次值前科学尝试、5 次基础设施失败；累计历史尝试 2,617，累计收益读取开发试验 315。Candidate49 仍是唯一前瞻候选，信号/执行账本为 0/0 且哈希不变。

## 权威文件

- 最新状态：`docs/a_share_three_day_iteration_status_20260824_campaign265_source_acceptance_plan_ready.json`，SHA-256 `4b6e942d22cebadebd714b8b7eed0fb7be529ac5f482a158c74be1f2b6a23c0a`。
- plan-only 政策 v418：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v418_20260824.json`，SHA-256 `f1ba460fda8fe9b51388edfb4a2de7c8a7940c0df1650a75e8d142ccef3d36a0`。
- 值前计划合同：`docs/a_share_three_day_walkforward_campaign_265_source_acceptance_preregistration_20260824.json`，SHA-256 `474e5a995703f46005053268bbbd6c1c20835c99233f82e727a24a6085198ffd`。
- planner：`scripts/a_share_three_day_walkforward_campaign265_source_acceptance_plan.py`，SHA-256 `1702119cc43c58843cc27575a9681214121b45084ccd0ff84489ea362eac7c05`。
- planner 测试：`tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_source_acceptance_plan.py`，SHA-256 `a290d89afbb102c945fb3ffd55ddb41c519abaad4e06117eeeeb4ce2c010e00a`。
- 实现冻结：`docs/a_share_three_day_walkforward_campaign_265_source_acceptance_planner_implementation_freeze_20260824.json`，SHA-256 `f6d0083459212661de31623875f280627b3b0dfc4f7868b2dd15198a9aafcd8d`。
- plan 结果：`docs/a_share_three_day_walkforward_campaign_265_source_acceptance_plan_result_20260824.json`，SHA-256 `03c05e8586d97d2c0e2fccb9978ab858a7f99bd77b49d5266a7706383ef2b3a5`。
- 验证：`docs/a_share_three_day_walkforward_campaign_265_source_acceptance_plan_validation_20260824.json`，SHA-256 `188aed7b9434d601b52f4061acf098c7bda5d22c5ee8f89fd2bff366bba09530`。
- 报告：`docs/a_share_three_day_walkforward_campaign_265_source_acceptance_plan_report.md`，SHA-256 `25b3693098ef1c0b4f869e99c325c2a328a8c832df038062da4ee5814c093020`。
- 本地追加链：`data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v4.json`，SHA-256 `706e70dba43e2b236d50ca1edfef35eb7440502a097dba72170551c2c40f999e`，链尖 `472403c6927a6e146fe1922f84ae0d9cb7bb88414a4ba006049620d95495d317`。

`data/` 下的台账、来源目标和统一报告是 Git 忽略的本地证据，不得 `git add -f`。`.env` 是 Git 忽略的 0600 私密文件，绝不提交或披露 Token。

## 下一步唯一允许路径

1. 仍在 Campaign265 内，另行冻结一个 credential-safe 的一次性执行 workflow；不得修改现有 planner、合同、adapter、日期、字段、调用数或路径。
2. workflow 必须在凭据加载前独占创建并 fsync 完整 intent 与 journal；intent 必须嵌入全部 1,699 日期、请求摘要、代码/政策哈希、原子路径和 1,700 次上限。
3. 每次 provider entry 前先 fsync `request_authorized`，响应后原子持久化白名单 checkpoint，再 fsync `checkpoint_committed`。任何已授权但无 checkpoint 的请求、来源失败或证据矛盾都终止且禁止重请求。
4. 失败记录只能保存去敏阶段码与请求序号，不得保存 Token、Token 摘要、原始行、行值、行数或 plaintext provider error。成功必须逐个校验 exact schema、日期、身份、唯一性、1–1,999 行和完整 1,700 请求，并原子发布 final root/manifest。
5. 当前 v418 和最新状态不授权 credential load、provider request、`run` 或确认接口。实现/测试 workflow 后，必须再发布一份绑定其最终字节的新政策；只有届时的零网络 plan `ready=true`、实际退出码 0 与明确确认同时满足，才可执行一次。
6. 来源完整验收后仍先做冻结覆盖和 143 项按序唯一性门；全部通过前禁止价格/收益。2019–2023 只按三组冻结扩展折和三个会话 purge 打开；2024–2025 仍需非零 survivor 后一次性打开。

禁止 Candidate49 历史回填、启动第二前瞻候选、绕过失败、修改公式/方向/滞后/字段/门槛、加入模型或旧因子组合、生成当前评分/选股/仓位/订单或给出投资建议。

## 复验命令

在 `/Volumes/DIsk/Disk-Coding/qlib`：

```bash
/Volumes/DIsk/Coding/anaconda3/bin/python3.12 scripts/a_share_three_day_walkforward_campaign265_source_acceptance_plan.py plan
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m black --check scripts/a_share_three_day_walkforward_campaign265_convertible_premium.py scripts/a_share_three_day_walkforward_campaign265_source_acceptance_plan.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_convertible_premium.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_prevalue_contract.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_adapter_stage.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_source_acceptance_plan.py
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m ruff check scripts/a_share_three_day_walkforward_campaign265_convertible_premium.py scripts/a_share_three_day_walkforward_campaign265_source_acceptance_plan.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_convertible_premium.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_prevalue_contract.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_adapter_stage.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_source_acceptance_plan.py
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_convertible_premium.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_prevalue_contract.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_adapter_stage.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_source_acceptance_plan.py -q
```

发布时为 Black/Ruff 通过、Pytest `42 passed`。代码发布分支仍为 `faet/local-test`；交接前基线提交是 `2929ab2e11ec135afd425e1bb3825179fc0771ce`，本阶段实际提交哈希以远端为准。
