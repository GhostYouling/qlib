# A 股三日短线因子研究交接：Campaign265 执行工作流计划就绪

## 交接结论

持续目标 `请持续迭代因子。` 仍为 active。本断点完成当前 Campaign265 的凭据安全来源执行工作流与零网络 `plan`，没有终止持续研究目标，也没有把策略标记为已验证盈利。

策略定义为 `convertible_bond_equity_parity_premium_compression_3s`（higher）：同一 exact `CB` 在 `t-3` 与 `t` 两端必须有有限转股溢价率和严格正成交额，单债取 `cb_over_rate(t-3)-cb_over_rate(t)`，同一正股多债取确定性算术中位数。缺失不置零、不前填、不改窗；公式、方向、过滤、门槛和库顺序均已冻结。

当前加固工作流 `plan` v2 为 `ready=true`、实际退出码 0、34/34 检查通过，目标父级目录树真实且无符号链接。它绑定 1,699 个接受日和精确 1,700 次未来调用，但 v419 revision 2 只授权零网络计划：`future_run_authorized=false`，当前 CLI 不暴露 `run`。没有创建 intent、加载 token、导入/创建 provider、发请求、读取来源/候选/比较/价格/收益值或写来源文件。

## 权威断点

- 最新状态：`docs/a_share_three_day_iteration_status_20260824_campaign265_execution_workflow_plan_ready_v2.json`，SHA-256 `1cf226d8d64520cf1801baa6f0bf1ac96a3adb19f85e3d950e7d19d674a79753`。
- 政策 v419 revision 2：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v419_20260824_execution_path_hardening_v2.json`，SHA-256 `c331d3931893ea183a7d0a750be8f5b136b1e95e5a0e1fc65683e6cf64d5cc2a`。
- 执行协议：`docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_protocol_20260824.json`，SHA-256 `766172caa77a9ffa90867e7299e1ac77816934469b8cafd5f63fd27281d9c04c`。
- 工作流：`scripts/a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py`，SHA-256 `796322ab186c837dc02a5657572a3f936792dc33ffd4c817cfc430c1d7639020`。
- 工作流测试：`tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py`，SHA-256 `b160f11d19e5ab85d2b6f3a523ac450a0be8214014165837591c68de0d1faac9`。
- 实现冻结 v2：`docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_workflow_implementation_freeze_v2_20260824.json`，SHA-256 `27bcadf74f6dcd0abe47e22f7d62eacf7f2e788bb4b4d0286d0b7e63337a267f`。
- plan 结果 v2：`docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_workflow_plan_result_v2_20260824.json`，SHA-256 `9006c35b51912e48cf3ae03a6c581c87da6249119b3ceaeb54b0a8ba998bcd03`。
- 有效验证 v2：`docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_workflow_plan_validation_v2_20260824.json`，SHA-256 `1ac037d922474364d3d39ad2c1592e013a288b7f5fb75d51db792be6257882ee`。
- 本地追加链：`data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v12.json`，SHA-256 `737275543470b1a4a49b87c0fc3499f54e4be8beb05bcaf518308d50bfa10ddb`，31 条，链尖 `ac77d8fa218e43aac718c72195b88e8252aa55813a2c651988241594e3ecc900`。
- 基础设施失败记录：`docs/a_share_three_day_walkforward_campaign_265_execution_workflow_infrastructure_failures_20260824.json`，SHA-256 `86a8a061251d561ab517b848d3e1296230fe736b2b743e76886f35f3d387f1ea`，10 个命令级失败全部保留。

`data/` 和 `.env` 均保持 Git 忽略，不得强制提交；token 值不得打印、哈希、记录或持久化。

## 已验证

- Black 与 Ruff：通过；
- workflow 合成测试：`13 passed`；
- Campaign265 跨阶段套件：`60 passed, 1 deselected`；
- v7–v12 台账链：通过；
- Candidate49 信号/执行账本：0/0，SHA-256 分别为 `5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79` / `d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f`；
- 当前会计：Campaign265 31 次尝试（14 科学、17 基础设施），累计历史尝试 2,635，累计收益读取开发试验 315，完整定义/比较器 `162/143`。

## 断点续跑顺序

1. 只读重验本交接的状态 v2、v419 revision 2、协议、工作流、测试、冻结 v2、plan-result v2 和台账指纹；确认 Candidate49 仍为 0/0，`.env` 只做元数据/赋值存在性检查，不输出或哈希值。
2. 如确需真实来源验收，先事前发布 v420；它必须精确绑定工作流、测试、协议、实现冻结和 plan-result 字节，不得修改日期、字段、1,700 调用、1.05 秒间隔、路径、行门、失败或恢复语义。
3. v420 有效后先重新运行同一参数 `plan`。只有 `ready=true` 且退出码 0，并由操作者明确给出 `--confirm-run`，才可执行一次 `run --confirm-run`。不得重试失败请求或为诊断重请求同一响应。
4. 来源验收完整成功后，仍先跑冻结的覆盖与 143 项有序唯一性门。任一失败即终止本定义，不反向、不改窗、不换字段、不过滤、不组合救援。
5. 只有所有值前门通过，才允许一次 2019–2023 三折开发；只有非零 survivor 才可一次性打开标为历史已暴露准样本外的 2024–2025。历史结果永不直接生成当前评分、选股、仓位或订单。

绝不能回填 Candidate49、启动第二个前瞻候选、绕过退出码、修改冻结门槛、执行实盘订单或把该策略当作投资建议。
