# A股三日短线因子研究交接文档（2026-08-25）

## 交接结论

当前研究轮次 Campaign286 已完成并终止，三组 Alpha158 + LightGBM 配置全部未通过冻结门禁，存活者为 0。2024–2025 锁箱没有打开，当前没有可部署的新策略。本轮代码、冻结记录、失败证据、终态报告和测试已整理在 `faet/local-test` 分支。

## 工作区与权威入口

- 可写恢复工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- 分支：`faet/local-test`
- Campaign286 协议：`docs/a_share_three_day_walkforward_campaign_286_preregistration_20260825.json`
- 终态结果：`docs/a_share_three_day_walkforward_campaign_286_terminal_result_20260825.json`
- 人类可读报告：`docs/a_share_three_day_walkforward_campaign_286_terminal_report.md`
- 最新迭代状态：`docs/a_share_three_day_iteration_status_20260825_campaign286_terminal.json`
- 终态校验器：`scripts/a_share_three_day_walkforward_campaign286_terminal_verify.py`
- 追加式试验台账：`data/experiments/short_horizon/historical_walkforward/campaign_286/walkforward_v1/trial_ledger.json`
- 本地设计快照：`data/experiments/short_horizon/historical_walkforward/campaign_286/alpha158_development_design_recovery_v3/`

`data/experiments/` 下的大型研究产物受仓库忽略规则保护，不随 Git 提交；文档以 SHA-256 绑定这些本地证据。不要移动、重写或清理上述目录。

## 复核命令

在恢复工作区执行：

```bash
MPLCONFIGDIR=/private/tmp/campaign286-mpl /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m scripts.a_share_three_day_walkforward_campaign286_terminal_verify verify
MPLCONFIGDIR=/private/tmp/campaign286-mpl /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign286_terminal_verify.py
```

终态校验应返回 `verified_terminal_no_survivor_lockbox_closed`、16 条记录、3 次收益读取开发试验、9 次模型×折验证读取、0 个存活者。最终化脚本不应重跑；终态文件存在时它会按设计失败关闭。

## 已知恢复历史

原始 `/Volumes/DIsk/Disk-Coding/qlib` 工作树在运行中转为只读，因此本轮在恢复克隆中完成。设计阶段还记录了直接脚本导入失败、缺失本地 Cython 扩展、旧 Campaign054 绝对绑定、67 个零分母会话和原子移动后的路径验证问题；这些都作为追加式基础设施失败保留，没有被改写为科学结果。

开发阶段全部 9 次验证读取和验证快照都已持久化，但原运行器在处理 deep 常数模型的空关联指标时异常退出，导致训练评估指标未持久化。只读最终化器没有重读历史收益，仅用冻结验证证据完成拒绝判定。这是当前证据链的明确局限，不应通过补读来美化。

## 不可跨越的边界

- Candidate49 是唯一活动前瞻候选；禁止历史信号、收益和执行回填。
- Candidate49 的信号与执行账本均为 0 条，SHA-256 分别为 `5193f00d…d3a79` 和 `d57a3e61…ea4f`。
- 不得启动第二个前瞻候选，不得修改 Campaign286 的模型、阈值、搜索空间或终止结论。
- 历史结果不得直接生成当前评分、选股、仓位或订单，也不得表述为投资建议。
- 新的离线研究必须创建新的有限 campaign，事前冻结完整特征库、候选集合、成本、门禁、数据与代码指纹；不得复用 Campaign286 结果做事后挑选。
- Candidate49 日常工作仍遵循交易日同日 16:30 Asia/Singapore 后先 `plan`，仅 `ready=true` 且退出码为 0 时才可用完全相同参数 `run --confirm-run`。

## 下一步建议

Campaign286 已科学终止。若继续长期目标，下一安全动作是创建 Campaign287 的全新有限概念目录，并优先选择与 Alpha158 树模型不同的经济机制或数据生成过程；不要在本轮三个 LightGBM 配置上继续调参。前瞻轨保持 Candidate49 单独观察，和历史滚动研究互不回填。
