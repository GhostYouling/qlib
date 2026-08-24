# A 股三日短线因子研究交接（2026-08-17）

## 交接结论

当前研究阶段已经完成到 Campaign263。该 Campaign 的研究流程、冻结边界、无收益门禁、唯一性检查、2019–2023 滚动开发试验和终局验证均已完成；结论是 **零开发幸存者，不具备上线条件**。

这不是“策略已经可交易”，而是“当前候选已按预注册规则完成并被终止”。不得从本结果生成当前评分、选股、仓位、订单或投资建议。2024–2025 的历史已暴露准样本外压力区间没有打开，也没有读取其收益。

持续迭代目标 `请持续迭代因子。` 在 Codex 任务层当前为 `paused`。Campaign264 尚未开始。只有在明确恢复研究后，才可按本文末尾的边界启动新的独立、有限、零网络值前机制。

## 固定研究协议

- 目标持有期：三个交易会话；信号在 `t` 收盘后形成，计划于 `t+1` 开盘进入、`t+3` 收盘退出。
- 历史开发：只使用 2019–2023 的三组扩展训练/验证折；分区边界清除三个信号会话，且 `t+1` 与 `t+3` 必须落在同一分区。
- 压力区间：2024–2025 只有在完整候选库、搜索空间、门禁、成本、代码和数据指纹全部冻结，且开发期存在幸存者时，才允许为整个 Campaign 一次性打开。本 Campaign 没有满足条件。
- 组合边界：旧终止因子只可作为预先冻结的完整比较库使用；旧终止结论不得改写，也不得只挑有利因子、年份、方向或参数进行救援。
- 执行口径：Top3；归一化执行账本之外，固定 CNY 200,000、每槽 5%、单信号最多 15%、100 股整手；佣金每边 0.01%、过户费每边 0.002%、卖出印花税 0.05%，主门禁使用每边 10bp 不利滑点，并检查同日成交额参与率。
- 已知限制：历史股票范围源自当前上市快照，存在幸存者偏差；历史研究结果不能直接升级为实盘证据。

## Campaign263 因子

唯一冻结因子为 higher 方向的 `intraday_amount_profile_spectral_entropy_60f`。

在上午和下午各 120 根固定一分钟金额序列中，分别用半场总金额归一化并中心化；对每个半场计算未归一化实数 DFT，合并两个半场所有非零频率 `k=1..60` 的功率，归一化为 60 个频率概率，最终返回 Shannon 熵除以 `ln(60)`。没有搜索频带、窗口、阈值、方向、过滤、拟合、模型或组合。

## 最终结果

| 项目 | 结果 |
| --- | ---: |
| 快照分区 / 行数 / 公式有效行 | 33,015 / 7,724,498 / 7,724,491 |
| 质量与上市基准行 / 候选行 | 1,331,759 / 1,330,170 |
| 日覆盖率中位数 / P05 | 99.9452% / 99.5689% |
| P05 合格名称数 | 138 |
| 非常数横截面会话 | 1,632 |
| 冻结数值比较 | 142/142 通过 |
| 最大绝对中位日秩相关 | 0.721023，对 `intraday_top_decile_amount_event_spacing_entropy_25g` |
| 2021/2022/2023 验证 mean Rank IC | 0.048029 / 0.040426 / 0.055684 |
| 2021/2022/2023 归一化执行收益 | -22.8584% / -21.7485% / -22.7626% |
| 2021/2022/2023 10bp 整手收益 | -2.9949% / -6.0777% / -4.4211% |
| 最差验证归一化回撤 | -38.6977% |
| 开发期聚合 20bp 收益 | -31.5329% |
| 开发幸存者 / 2024–2025 压力试验 | 0 / 0 |

Rank IC 三折均为正，但可执行收益三折均为负，且 10bp 整手收益三折均为负；同时最差回撤和 20bp 成本稳健性门禁失败。因此不能仅凭相关性将其提升为策略。

该定义保留在完整重复控制库中。终局后完整定义库为 162 个，数值比较库为 143 个；把本因子加入未来重复检测不代表它具有投资价值。

## 权威证据

- 最新状态：`docs/a_share_three_day_iteration_status_20260816_campaign263_terminal.json`，SHA-256 `63b8ce2a195c3c1d2bbc7a5182ae2c886af36602c3e2ddc34286d882476e0f9d`
- 终局结果：`docs/a_share_three_day_walkforward_campaign_263_terminal_result_v6_20260816.json`，SHA-256 `e4b11b5d857d2e1377d174d9b1c9c16c5910d5f6f72b446940a2119df49f2cff`
- 数值比较政策：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v414_20260816.json`，SHA-256 `a41c4a3849d5a14c448e76d9c7f6cc5bf0603da2b8db57cadc85d1534349dac0`
- 终局验证：`docs/a_share_three_day_walkforward_campaign_263_terminal_validation_20260816.json`，SHA-256 `70b193b3664148025e6218cb7dfedd160d7f0aaaeb14862722966fadebf185c3`
- 简明报告：`docs/a_share_three_day_walkforward_campaign_263_terminal_report.md`，SHA-256 `854123a2c09e069637b1231752a2352fac9d03861b53efd22d47a9c37585ceb3`
- 本地追加式尝试台账：`data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v13.json`，SHA-256 `e6075d529195cf87364b8b873d273eea57e23450cfb248f77ceead7782ca2af2`，34 条有效尝试，链尖 `b84d7f5ef4d9c9c0f138612805d52392220f23745ff44fed0e1437132520abb2`

`data/` 按仓库约定保持 Git 忽略；其中的快照、账本和统一报告属于本机研究证据，不应强行提交。Git 中的 `docs/` 终局文件保存了关键哈希、汇总指标和边界。需要迁移完整本地证据时，应单独按哈希传输 `data/experiments/short_horizon/`，不能把原始市场数据加入 Git。

## Candidate49 前瞻轨

Candidate49 仍是唯一前瞻候选，历史回填被禁止，第二个前瞻候选未启动。

- 信号账本：`data/experiments/short_horizon/candidate49_future_signal_ledger.json`，0 条，文件 SHA-256 `5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79`
- 执行账本：`data/experiments/short_horizon/candidate49_future_execution_ledger.json`，0 条，文件 SHA-256 `d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f`

不得用 Campaign263 的历史结果填充 Candidate49，也不得因为本次交接启动 Candidate50。Candidate49 的同日数据工作流仍必须在目标交易日 16:30 Asia/Singapore 后先运行 `plan`；只有 `ready=true` 且退出码为 0，才可用完全相同参数运行确认阶段。任何来源门禁失败都必须保留并禁止同日重试。

## 本机与凭据边界

- 权威 Git 工作树：`/Volumes/DIsk/Disk-Coding/qlib`
- 当前本地日线数据根：`/Volumes/DIsk/Disk-Coding/qlib/data`
- 历史 Tushare 一分钟外置根：`/Volumes/DIsk/qlib-a-share-tushare-1m`
- `.env` 是私有、Git 忽略的本机文件；交接时只确认其为 mode 0600 且存在唯一非空 `TUSHARE_TOKEN`，不得输出、哈希、记录或提交 Token。
- `.DS_Store` 与 `.codex/` 是本机应用产物，不属于研究输入，不提交。

## 验证与复核

Campaign263 最终聚焦验证为 45 passed、1 deselected；被排除的测试只适用于开发激活文件尚不存在的旧阶段。24 个 Campaign263 Python 文件全部通过 Ruff。19 个未冻结文件通过 Black；5 个已被指纹绑定的旧文件即使 Black 会建议改写，也按冻结边界保持字节不变。

额外运行 `test_a_share_runtime.py`、`test_a_share_data_pipeline.py` 与旧版 `test_a_share_short_horizon_factor_research.py` 的组合回归时，结果为 319 passed、7 failed。七个失败都来自旧 2026-07-25 Candidate49/统一报告测试共用的历史加载器：它会扫描全部 `docs/a_share_*record.json`，并要求可发现终止记录仍恰好等于当时冻结的 48 条；完整工作区现在按设计保留了之后数百个版本化终止记录，因此旧断言失败。该结果不涉及 Campaign263 公式、快照、比较、收益或终局链，也不是本次 45 项当前终局测试的回归。不得删除后续记录或改写旧测试来制造全绿；若未来维护通用报告入口，应新增版本化的当前状态加载器和当前状态测试。

聚焦测试命令：

```bash
cd /Volumes/DIsk/Disk-Coding/qlib
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign263_development.py \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign263_features.py \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign263_formula.py \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign263_no_return_audit.py \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign263_ordered_uniqueness.py \
  tests/data_collector_tests/test_a_share_three_day_walkforward_campaign263_terminal.py \
  -k 'not test_development_activation_fails_before_return_loader_when_absent' -q
```

不要重跑已经消费的开发试验来“确认”结果；复核应以只读哈希、终局测试和语义验证为主。

## 若恢复研究

恢复持续迭代目标后，Campaign264 只能从一个经济上独立、有限、零网络的值前机制开始，并在读取候选值前冻结公式、方向、输入字段、缺失/零值/时间语义、覆盖门、完整 143 项比较顺序、开发目录、成本和幸存规则。所有成功、失败和基础设施尝试都必须追加记录，不能只保留最佳结果。

在新候选通过覆盖和全部 143 项唯一性门禁前，不得读取其 2019–2023 开发收益；没有开发幸存者时不得打开 2024–2025。任何历史通过仍只属于研究排序，不自动生成当前交易动作。

## 2026-08-24 Campaign264 续跑补充

持续目标已经恢复为 active。Campaign264 完成了一轮严格值前本地原始通道审查：只读重建 162/143 完整库，并检查分钟与日线 Parquet footer schema；七条候选路线全部因冻结旧族重叠或曝光后 estimator/字段/窗口/模型救援而拒绝。没有候选快照、比较值、价格或收益读取，开发与 2024–2025 仍关闭；累计历史尝试为 2,604，收益读取开发试验仍为 315。

Campaign264 的权威结果为 `docs/a_share_three_day_walkforward_campaign_264_terminal_result_20260824.json`，完整路线说明为 `docs/a_share_three_day_walkforward_campaign_264_local_schema_independent_mechanism_frontier_20260824.json`。下一轮 Campaign265 不能重试这七条路线；必须引入真正新的被接受点时信息通道，或在任何值前证明机制相对完整库独立。Candidate49 的唯一前瞻地位与 0/0 空账本不变。
