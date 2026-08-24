# A 股三日短线因子研究交接（Campaign265 适配器就绪）

## 当前结论

Campaign265 的冻结候选 `convertible_bond_equity_parity_premium_compression_3s` 已完成零网络确定性适配器及纯合成语义验证。公式方向为 higher：同一只 exact `CB` 在信号会话 `t` 与前三个接受的 A 股会话 `t-3` 均活动、均有有限 `cb_over_rate` 且 `amount > 0` 时，单债分数为 `cb_over_rate(t-3) - cb_over_rate(t)`；同一正股多只合格转债取确定性算术中位数。没有活动或合格转债时保持缺失，禁止置零、前向填充、换窗口或反向。

实现位于 `scripts/a_share_three_day_walkforward_campaign265_convertible_premium.py`。它只有纯 Python/pandas 函数，不含 CLI、网络、provider client、凭据读取或真实数据文件加载器。16 项纯合成测试覆盖严格字段顺序、NFKC/大写身份、exact `CB`、A 股映射、日期和活动区间、精确三会话滞后、两端正成交、奇偶中位数、活动转债发行人分母、缺失和失败关闭语义。Black、Ruff 及 Campaign265 三个测试文件共 30 项检查全部通过。

这不是收益有效性结论，也不是可交易策略。本轮没有加载 Token、请求 Tushare、读取来源行、候选/比较值、日线价格或 forward return；2019–2023 开发和 2024–2025 压力试验均未打开。完整定义/数值比较库保持 `162/143`，Campaign265 完整因子尝试和收益试验仍为 0。

Campaign265 当前有效会计为 10 次尝试：7 次值前科学尝试、3 次基础设施失败；累计历史尝试 2,614，累计收益读取开发试验 315。首次 Black 格式失败和一次只读报告路径探测失败均保留在追加式链中，没有被当作科学证据。

持续目标 `请持续迭代因子。` 保持 `active`。Candidate49 仍是唯一前瞻候选，信号/执行账本为 0/0；禁止历史回填、启动第二前瞻候选、生成当前评分/选股/仓位/订单或给出投资建议。

## 权威断点

- 最新状态：`docs/a_share_three_day_iteration_status_20260824_campaign265_adapter_ready.json`，SHA-256 `926cb5336c11225106711964ac5cc566289f9dc467edc52d83edba80ea23ce6e`。
- 数值比较政策 v417：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v417_20260824.json`，SHA-256 `62805389b141904fe6b519bb7ff345410802fb5475f3804615e6f12ff81da39f`。
- 来源合同：`docs/a_share_three_day_walkforward_campaign_265_convertible_premium_source_contract_20260824.json`，SHA-256 `efe7884d3ea0fd7f974e0d3347432e68e9e01ceefe0e6ebdca7fdd3e6349301c`。
- 适配器实现冻结：`docs/a_share_three_day_walkforward_campaign_265_adapter_implementation_freeze_20260824.json`，SHA-256 `2429588261bf35e46c3a68daeab85b23405c247a6fd98195e081c2b43c1f638e`。
- 适配器结果：`docs/a_share_three_day_walkforward_campaign_265_adapter_result_20260824.json`，SHA-256 `4a109a2e7e23091da33246654e391d41af0a57515b23d91dfb28f4718c26da48`。
- 适配器报告：`docs/a_share_three_day_walkforward_campaign_265_adapter_report.md`，SHA-256 `2411e54360d3fa8e7b0a92bf014824c12af3d08afec5a1f2aa200170807b8e2f`。
- 终态验证：`docs/a_share_three_day_walkforward_campaign_265_adapter_validation_20260824.json`，SHA-256 `15cc4b99a5ac1daab270bc7120d6e24e8cd2630ab9b61f25f64d04de358a1ecf`。
- 本地追加链：`data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v3.json`，SHA-256 `7edd5202c77ed575f84efc6e8ecbc51bb2367f631783b1f3810e2378d094bdf0`，链尖 `182be5c5736620bebe17d9128d356cbbb021a084e2bcb52cbc9e5bc2293da00d`。
- 实现：`scripts/a_share_three_day_walkforward_campaign265_convertible_premium.py`，SHA-256 `58b9fddbbeef97955d4961f9f708028aa63d90fc56f2656db68098de7d3543e8`。

`data/` 下的追加链和两份统一研究报告属于 Git 忽略的本地证据，禁止 `git add -f`。`.env` 是权限 `0600`、Git 忽略的凭据容器；不得打印、哈希、提交或把 Token 值写入文档。旧政策、状态、失败和终止记录只可由新文件 supersede，禁止改写。

## 下一步唯一允许路径

1. 仍在 Campaign265 内，先单独冻结并实现一个零网络的一次性来源验收 planner。它必须绑定来源合同、适配器字节、接受日历和因子宇宙指纹。
2. planner 必须在任何 Token 加载前固定：2019-01-02 至 2025-12-31 的完整接受交易日清单、`cb_basic` 一次与每个接受日一次 `cb_daily` 的精确请求数、字段、请求上限/限流、原子 staging 路径、schema/重复/截断/身份/日期检查及失败证据。
3. v417 和当前状态不授权加载凭据或发 provider 请求。只有未来不可变 planner 的零网络 `plan` 为 ready、退出码 0 且另有显式确认时，才可讨论一次执行；任何失败都终止精确定义，禁止重试、切接口或补救。
4. 来源验收完整通过后，先做活动 exact-CB 发行人分母上的冻结覆盖门：中位/P05 至少 95%/90%，P05 至少 50 名，至少 200 个非恒定会话、200 个非重叠三会话 cohort 和五年。任一失败即在 143 项比较值前终止。
5. 覆盖全过后才允许按冻结顺序读取 143 项唯一性比较；每项至少 50 名、100 会话，绝对中位日平均并列 Spearman 必须严格小于 0.8。第一项失败即停。
6. 只有全部无收益门通过，才按三组冻结扩展折与三个信号会话 purge 打开 2019–2023；`t+1/t+3` 必须在同一分区。2024–2025 仅在开发 survivor 产生后整次打开，并标记为历史已暴露的准样本外。

不得加入债券 OHLC/收益、其他溢价字段、评级/赎回/发行字段、amount 权重、其他滞后、阈值、方向、子集、模型、残差、旧因子组合或失败救援。

## 验证命令

在 `/Volumes/DIsk/Disk-Coding/qlib` 运行：

```bash
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m black --check scripts/a_share_three_day_walkforward_campaign265_convertible_premium.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_convertible_premium.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_prevalue_contract.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_adapter_stage.py
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m ruff check scripts/a_share_three_day_walkforward_campaign265_convertible_premium.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_convertible_premium.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_prevalue_contract.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_adapter_stage.py
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_convertible_premium.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_prevalue_contract.py tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_adapter_stage.py -q
```

发布时结果：Black 通过、Ruff 通过、Pytest `30 passed`。

## Candidate49 与发布边界

本轮核查时间为 2026-08-24 12:20:41 Asia/Singapore，早于 16:30，因此没有执行 Candidate49 plan/run。同日流程仍只允许在 16:30 后先 `plan`；仅 `ready=true` 且退出码 0 才可用完全相同参数执行 `run --confirm-run`。source gate 失败则保留绝对日期 staging root 和失败记录，禁止同日重试。

代码发布分支为 `faet/local-test`。交接前基线提交为 `99e81938ffdf8837f5177d4eb4a326b97a2e6b14f`；本文件、适配器、测试和不可变 docs 随本轮新提交发布，实际新提交哈希以 Git 远端分支为准。
