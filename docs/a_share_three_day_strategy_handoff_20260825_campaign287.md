# A股三日短线因子研究交接文档（Campaign287）

## 交接结论

Campaign287 已完成并按冻结规则终止。本轮只运行了一个完整 Alpha158 会话平衡 MLP：三组验证折的 Rank IC 与 Top3-Bottom3 毛价差均为正，但 2022 验证折标准化最大回撤为 -35.84%，且三折 20bp 试点复合收益为 -6.08%，未通过冻结门禁。因此存活者为 0，2024–2025 锁箱没有打开，当前没有可部署的新策略。

持续研究目标仍为 active。本轮结果不得事后调参挽救；下一轮必须以新的有限 Campaign288 重新事前冻结。

## 工作区与权威入口

- 可写工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- Git 分支：`faet/local-test`
- 前序权威状态：`docs/a_share_three_day_iteration_status_20260825_campaign286_terminal.json`
- Campaign287 协议：`docs/a_share_three_day_walkforward_campaign_287_preregistration_20260825.json`
- 设计实现冻结：`docs/a_share_three_day_walkforward_campaign_287_design_implementation_freeze_20260825.json`
- 开发执行冻结：`docs/a_share_three_day_walkforward_campaign_287_development_execution_freeze_20260825.json`
- 终态结果：`docs/a_share_three_day_walkforward_campaign_287_terminal_result_20260825.json`
- 人类可读报告：`docs/a_share_three_day_walkforward_campaign_287_terminal_report.md`
- 终态校验器：`scripts/a_share_three_day_walkforward_campaign287_terminal_verify.py`
- 追加式试验台账：`data/experiments/short_horizon/historical_walkforward/campaign_287/balanced_mlp_v1/trial_ledger.json`
- 开发报告：`data/experiments/short_horizon/historical_walkforward/campaign_287/balanced_mlp_v1/development_report.json`

`data/experiments/` 下的研究产物受忽略规则保护，不随 Git 提交；仓库文档使用 SHA-256 绑定这些本地证据。不要重写或清理该目录。

## 冻结策略定义

- 特征：完整 158 个 Qlib Alpha158 日频特征，不做子集搜索。
- 预处理：仅用训练折的中位数/IQR，缩放后缺失置零，固定裁剪到 `[-8, 8]`。
- 采样：每个保留训练会话按 `SHA256(287|日期|证券)` 固定选择 96 个名字，训练损失按会话等权。
- 模型：158→32 ReLU→1，固定 weighted Adam、20 轮、一个种子；不做架构、优化器、种子或早停搜索。
- 分区：2019–2020→2021、2019–2021→2022、2019–2022→2023；边界清除 3 个信号会话，t+1/t+3 必须落在同一分区。

## 终态结果

| 验证年 | Mean Rank IC | 毛价差 | 标准化收益 | 最大回撤 | 10bp | 20bp |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 0.0139 | 0.8034% | 44.05% | -22.41% | 2.41% | 0.47% |
| 2022 | 0.0318 | 0.3328% | -18.55% | -35.84% | -5.03% | -6.62% |
| 2023 | 0.0113 | 0.3766% | 17.46% | -14.13% | 1.89% | 0.11% |

三折标准化复合收益为 +37.81%，10bp 复合收益为 -0.90%，20bp 复合收益为 -6.08%。运营门禁通过，但冻结的最差回撤下限和 20bp 成本门禁失败，所以必须拒绝。

## 失败与恢复记录

第一折模型训练后，原冻结运行器在验证分数前置检查中调用了不存在的 `DatetimeIndex.eq`。失败记录被追加保留。恢复脚本只将该 API 调用替换为等价的 `==`，复用第一折模型，没有重训、重读第一折训练收益或补造训练指标；三折验证分数均先落盘，再读取相应验证收益。

本轮台账共 9 条：7 次零收益读取概念尝试、1 次基础设施失败、1 次模型试验。收益读取开发试验为 1 次，模型×折验证读取为 3 次。

## 复核命令

在恢复工作区执行：

```bash
MPLCONFIGDIR=/private/tmp/campaign287-mpl /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m scripts.a_share_three_day_walkforward_campaign287_terminal_verify verify
MPLCONFIGDIR=/private/tmp/campaign287-mpl /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign287.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign287_recovery.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign287_terminal_verify.py
```

校验器应返回 `verified_terminal_no_survivor_lockbox_closed`，并确认 9 条台账记录、7 个概念、1 个基础设施失败、1 个模型试验、3 折验证读取、0 个存活者、第一折训练收益未重读、锁箱关闭和 Candidate49 台账不变。

## 不可跨越的边界

- Candidate49 仍是唯一活动前瞻候选；禁止历史信号、收益或执行回填。
- Candidate49 信号与执行台账均为 0 条，SHA-256 分别为 `5193f00d…d3a79` 和 `d57a3e61…ea4f`。
- 不得修改 Campaign287 的特征、模型、成本、阈值、门禁或终止结论，也不得启动第二个前瞻候选。
- 历史结果不得直接生成当前评分、选股、仓位或订单，不得表述为投资建议。
- 2024–2025 只能在新 campaign 的完整有限候选库、搜索空间、存活规则、组合/拟合方法、成本、门禁以及数据/代码指纹全部冻结后，为整个 campaign 一次性打开；当前仍关闭。
- Candidate49 日常流程仍须在目标交易日同日 16:30 Asia/Singapore 后先运行 `plan`，仅当 `ready=true` 且退出码为 0，才可用完全相同参数执行 `run --confirm-run`。

## 下一安全动作

Campaign288 可以继续零网络离线历史研究，但必须采用新的有限概念目录并完整记录成功与失败，不能围绕 Campaign287 的 32 单元、20 轮、96 样本、裁剪或 2022 失败折做事后微调。Alpha360 路线当前仅因可写磁盘容量不足而延期，不是科学否决；只有获得足够的已授权可写容量后才能重新评估。Candidate49 继续作为独立前瞻确认层。
