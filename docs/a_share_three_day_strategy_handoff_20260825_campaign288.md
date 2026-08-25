# A股三日短线因子研究交接文档（Campaign288）

## 交接结论

Campaign288 已完成并按冻结规则终止。本轮只运行了一个完整 Alpha158 会话秩 RBF 随机傅里叶 ridge 模型。三组验证折的平均 Rank IC 均为正，但 Top3-Bottom3 毛收益差、标准化收益和 10bp 试点收益三折全部为负；最差标准化回撤为 -55.24%，20bp 三折复合收益为 -18.42%。存活者为 0，2024–2025 锁箱没有打开，当前没有可部署的新策略。

持续研究目标仍为 active。本轮模型及其秩变换、128 维投影、带宽、种子、ridge 惩罚、成本和门禁均已终止，不得事后调参挽救；下一轮必须从新的有限 Campaign289 概念开始事前冻结。

## 工作区与权威入口

- 可写工作区：`/Users/niyufei/Coding/qlib/recovery-worktree`
- Git 分支：`faet/local-test`
- 前序权威状态：`docs/a_share_three_day_iteration_status_20260825_campaign287_terminal.json`
- Campaign288 协议：`docs/a_share_three_day_walkforward_campaign_288_preregistration_20260825.json`
- 零收益设计证据：`data/experiments/short_horizon/historical_walkforward/campaign_288/ordinal_rff_ridge_v1/design_evidence.json`
- 原失败输出：`data/experiments/short_horizon/historical_walkforward/campaign_288/ordinal_rff_ridge_v1/`
- 恢复后终端输出：`data/experiments/short_horizon/historical_walkforward/campaign_288/ordinal_rff_ridge_recovery_v1/`
- 终态结果：`docs/a_share_three_day_walkforward_campaign_288_terminal_result_20260825.json`
- 人类可读报告：`docs/a_share_three_day_walkforward_campaign_288_terminal_report.md`
- 终态校验器：`scripts/a_share_three_day_walkforward_campaign288_terminal_verify.py`
- 终端追加式试验台账：`data/experiments/short_horizon/historical_walkforward/campaign_288/ordinal_rff_ridge_recovery_v1/terminal_trial_ledger.json`

`data/experiments/` 下的研究产物受忽略规则保护，不随 Git 提交；仓库文档使用 SHA-256 绑定本地证据。不要重写、移动或清理 Campaign286–288 的这些目录。

## 冻结策略定义

- 特征：完整 158 个 Qlib Alpha158 日频特征，不做子集、缺失指示器或方向筛选。
- 输入变换：每个信号会话、每个特征在全部 design model-support 名称内做升序平均秩百分位并减 0.5，非有限值置为中性 0。
- 采样：每个保留训练会话按 `SHA256(288|日期|证券)` 固定选择 96 个名字；有限目标按会话等权。
- 表示：固定 128 维随机傅里叶余弦映射，RBF `gamma=6/158`，随机种子 288；投影中心在零收益阶段冻结。
- 输出：闭式加权 ridge，惩罚 0.001，无截距，只有一个配置。
- 分区：2019–2020→2021、2019–2021→2022、2019–2022→2023；边界清除 3 个信号会话，t+1/t+3 必须落在同一分区。

## 终态结果

| 验证年 | Mean Rank IC | 毛价差 | 标准化收益 | 最大回撤 | 10bp | 20bp | 整手可负担率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 0.00890 | -1.1561% | -41.46% | -55.24% | -5.23% | -6.59% | 83.26% |
| 2022 | 0.01001 | -0.4565% | -13.11% | -28.65% | -3.67% | -5.34% | 89.95% |
| 2023 | 0.01341 | -1.1476% | -33.22% | -40.68% | -6.14% | -7.73% | 90.54% |

三折复合标准化收益为 -66.04%，10bp 为 -14.31%，20bp 为 -18.42%。弱正 IC 没有转化为顶部收益差或成本后收益；回撤、收益差、成本和前两折整手可负担率门禁均失败，必须拒绝。

## 失败与恢复记录

首次开发在折 1 读取训练收益后、模型拟合前失败。原实现先经过市场质量筛选，再重新计算会话秩，改变了预注册要求的 design model-support 同行集合。原 `development_intent.json` 和 `development_failure.json` 均保留未改。

恢复版本先在冻结 design 同行集合上计算秩，再把不变的秩值连接到市场面板。样本键、投影中心、随机映射、模型、成本和门禁未改变。折 1 训练收益为恢复重读一次；失败尝试没有模型拟合或验证收益读取。本轮终端台账共 10 条：8 个零收益概念、1 次基础设施失败、1 个模型试验。

## 复核命令

在恢复工作区执行：

```bash
MPLCONFIGDIR=/private/tmp/campaign288-mpl python -m scripts.a_share_three_day_walkforward_campaign288_terminal_verify verify
MPLCONFIGDIR=/private/tmp/campaign288-mpl python -m pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign288.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign288_recovery.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign288_finalize.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign288_terminal_verify.py
```

校验器应返回 `verified_terminal_no_survivor_lockbox_closed`；测试应为 13 passed。校验内容包括 10 条哈希链台账、8 个概念、1 个基础设施失败、1 个模型试验、3 折验证读取、折 1 一次恢复性训练收益重读、0 个存活者、锁箱关闭和 Candidate49 台账不变。

## 不可跨越的边界

- Candidate49 仍是唯一活动前瞻候选；禁止历史信号、收益或执行回填。
- Candidate49 信号与执行台账均为 0 条，SHA-256 分别为 `5193f00d…d3a79` 和 `d57a3e61…ea4f`。
- 不得修改 Campaign288 的特征、秩变换、投影维度、带宽、种子、惩罚、成本、阈值、门禁或终止结论，也不得启动第二个前瞻候选。
- 历史结果不得直接生成当前评分、选股、仓位或订单，不得表述为投资建议。
- 2024–2025 只能在新 campaign 的完整有限候选库、搜索空间、存活规则、组合/拟合方法、成本、门禁以及数据/代码指纹全部冻结后，为整个 campaign 一次性打开；当前仍关闭。
- Candidate49 日常流程仍须在目标交易日同日 16:30 Asia/Singapore 后先运行 `plan`，仅当 `ready=true` 且退出码为 0，才可用完全相同参数执行 `run --confirm-run`。本轮在 16:30 前完成，未执行 Candidate49 plan/run。

## 下一安全动作

Campaign289 可以继续零网络离线历史研究，但必须采用新的有限、机制独立的概念目录并完整记录成功与失败。不得围绕 Campaign288 的会话秩、128 维 RFF、`gamma=6/158`、种子 288、ridge 0.001 或负收益折做事后修补。Alpha360 路线仍仅因已授权可写磁盘容量不足而延期，不是科学否决；只有获得足够的已授权可写容量后才能重新评估。Candidate49 继续作为独立前瞻确认层。
