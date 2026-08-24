# A 股三日短线因子研究交接：Campaign265 v420 发布器计划就绪

## 当前断点

持续目标仍为 active。Campaign265 的冻结因子仍是 higher `convertible_bond_equity_parity_premium_compression_3s`，尚未读取任何真实来源值或收益，不能宣称有效。

新增的 v420 发布器已经完成并验证：

- 协议：`docs/a_share_three_day_walkforward_campaign_265_v420_authorization_publisher_protocol_20260824.json`；
- 实现：`scripts/a_share_three_day_walkforward_campaign265_v420_authorization.py`；
- 测试：`tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_v420_authorization.py`；
- 实现冻结：`docs/a_share_three_day_walkforward_campaign_265_v420_authorization_publisher_implementation_freeze_20260824.json`；
- 计划结果：`docs/a_share_three_day_walkforward_campaign_265_v420_authorization_publisher_plan_result_20260824.json`；
- 验证：`docs/a_share_three_day_walkforward_campaign_265_v420_authorization_publisher_validation_20260824.json`；
- 本地追加链：`data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v15.json`，36 条，链尖 `ce9530315223f3e6a3f4e514002f8087ec3d395658c706467afe72b29ea564dc`。

发布器 `plan` 当前为 `ready=true`、退出码 0、31/31；但 `docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v420_20260824.json` 仍不存在，原工作流的 `future_run_authorized=false`、`run_interface_exposed=false`。

## 续跑顺序

1. 先运行零网络计划：

   ```bash
   /Volumes/DIsk/Coding/anaconda3/bin/python3.12 \
     scripts/a_share_three_day_walkforward_campaign265_v420_authorization.py plan
   ```

   必须同时看到 `ready=true`、退出码 0、31/31 且无 blocker。

2. 只有操作者明确授权时才运行：

   ```bash
   /Volumes/DIsk/Coding/anaconda3/bin/python3.12 \
     scripts/a_share_three_day_walkforward_campaign265_v420_authorization.py \
     publish --confirm-v420-publication
   ```

   该命令只发布 v420，不读取 Token、不创建 provider、不发请求。目标已存在、父级被替换/符号链接或任一冻结字节变化均失败，且不得覆盖或修复旧 v420。

3. 发布成功后重新运行原工作流计划：

   ```bash
   /Volumes/DIsk/Coding/anaconda3/bin/python3.12 \
     scripts/a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py plan
   ```

   只有新的计划仍 `ready=true`、退出码 0、`future_run_authorized=true`，并由操作者再单独明确给出下列命令，才可开始一次性 1,700 调来源采集：

   ```bash
   /Volumes/DIsk/Coding/anaconda3/bin/python3.12 \
     scripts/a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py \
     run --confirm-run
   ```

4. 任一 provider/持久化失败都保留终止证据并禁止重请求。完整来源成功后仍须先过覆盖门和 143 项有序唯一性门；只有 2019–2023 冻结开发 survivor 非零，才能一次性打开 2024–2025。

## 不可越界事项

不得由自动目标替用户发布 v420 或运行 `--confirm-run`；不得回填 Candidate49、启动第二个前瞻候选、修改 Campaign265 公式/门槛、读取未授权价格或收益、生成当前评分/选股/仓位/订单，或把历史结果当作投资建议。
