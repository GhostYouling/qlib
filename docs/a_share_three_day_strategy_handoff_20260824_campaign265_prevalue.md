# A 股三日短线因子研究交接（Campaign265 值前合同阶段）

## 当前结论

Campaign265 已从 Campaign264 的“本地 OHLCV/成交额信息族耗尽”边界取得一项真实进展，但尚未形成可回测或可交易策略。它只重访 Campaign157 明确保留为来源合同缺失、预测价值未测试的 `c157_01`，在完整 162 个定义和 143 个数值比较器前冻结唯一 higher 因子候选：`convertible_bond_equity_parity_premium_compression_3s`。

公式固定为：对接受的 A 股信号会话 `t` 与前三个接受会话 `t-3`，同一只 exact `CB` 必须在两端都有有限 Tushare `cb_over_rate` 和严格正 `amount`；单债分数为 `cb_over_rate(t-3) - cb_over_rate(t)`，同一正股多只合格转债取确定性算术中位数。没有活动或合格转债时为缺失，绝不置零、前向填充、改滞后或换方向。

Tushare 官方 [`cb_basic`](https://tushare.pro/document/2?doc_id=185) 提供转债—正股映射和上市/摘牌日期，[`cb_daily`](https://tushare.pro/document/2?doc_id=187) 提供每日转股溢价率；[权限表](https://tushare.pro/document/1?doc_id=108)显示两者最低都是 2,000 积分。5,000 积分只提高相对调用频次，并非本合同的数据门槛。本轮只读取官方公开文档，没有加载 Token 或请求 provider 行。

当前只完成零行来源合同阶段：没有 adapter、来源验收、候选快照、候选/比较值、日线价格、forward return、2019–2023 开发或 2024–2025 压力试验。完整定义/数值比较库仍为 `162/143`。6 次科学尝试和 1 次写入前补丁失败已经进入追加式哈希链；累计历史尝试为 2,611，累计收益读取开发试验仍为 315。

持续目标 `请持续迭代因子。` 保持 `active`。Candidate49 仍是唯一前瞻候选，两本账保持 0/0，禁止历史回填、启动 Candidate50、当前评分/选股/仓位/订单或投资建议。

## 权威断点

- 最新状态：`docs/a_share_three_day_iteration_status_20260824_campaign265_prevalue_contract.json`，SHA-256 `d54dc99346d9b1698c510f7b8f403e968c8104ede90ba4948d8b6367de483d1d`。
- 数值比较政策 v416：`docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v416_20260824.json`，SHA-256 `1c864ecafbe4d338b5480a34ed9d7f539e51f3afa7f51b261697d166726fe616`。
- 有限概念目录：`docs/a_share_three_day_walkforward_campaign_265_convertible_premium_concept_scouting_20260824.json`，SHA-256 `b6c41973c4d13063804adffacc59d938fdea8a1ee6c9fab2b45b711865386837`。
- 机制审计：`docs/a_share_three_day_walkforward_campaign_265_convertible_premium_mechanism_audit_20260824.json`，SHA-256 `d31c5260f9ba3f28718b44f2a60b772c7a9472ad4c898bcbe4907aff67d48d93`。
- 零行来源合同：`docs/a_share_three_day_walkforward_campaign_265_convertible_premium_source_contract_20260824.json`，SHA-256 `efe7884d3ea0fd7f974e0d3347432e68e9e01ceefe0e6ebdca7fdd3e6349301c`。
- 值前结果：`docs/a_share_three_day_walkforward_campaign_265_prevalue_contract_result_20260824.json`，SHA-256 `0f2e3014c56d1d1ef92506166a2c2a9f38c25cf8078bc801cd5b15937d3cd0c8`。
- 值前报告：`docs/a_share_three_day_walkforward_campaign_265_prevalue_contract_report.md`，SHA-256 `5f3d56bb2da41184e472d41dca74ce3343ec82487c928d6075d8cc853fb81c62`。
- 验证记录：`docs/a_share_three_day_walkforward_campaign_265_prevalue_validation_20260824.json`，SHA-256 `7729f41e4926e0de3aca92c58462929a5034b418d18e6419a0ba2eb6029209e9`。
- 本地追加式台账：`data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v1.json`，SHA-256 `f4be9e7abfe336d5b5eb9c799ebb3acbb54d50a9f1dc73f3677a8743096be8fe`，链尖 `5461f13897fa8caf2384083e20008722a58471104656d2cfb4819320409dbce4`。

`data/` 下的台账和两份统一研究报告是 Git 忽略的本地证据，不得 `git add -f` 强行提交。旧 Campaign264/157 状态、政策、失败和终止记录均不得改写。

## 下一步唯一允许路径

1. 仍在 Campaign265 内实现确定性、零网络 adapter，并只用纯合成 `cb_basic`/`cb_daily` 帧测试身份、日期、精确 `CB`、多债中位数、三会话滞后、正成交、缺失和失败语义。
2. adapter 与测试通过后，另建不可变实现冻结，绑定合同、代码/测试、日历、因子宇宙和输出 schema 指纹。
3. 再另冻一次性来源验收 planner。它必须在 Token 加载前写入完整意图，固定 `cb_basic` 一次及每个 2019-01-02 至 2025-12-31 接受交易日一次 `cb_daily` 的日期清单、请求数、字段、限流、原子路径、截断检查和失败证据；当前 v416 不授权请求。
4. 只有 planner 的零网络 `plan` 为 ready、退出码 0 且显式确认后，才可执行一次 source acceptance。任何权限、schema、超过 2,000 行、日期、身份、映射、重复、持久化或请求失败都终止该精确定义，禁止重试或切换接口。
5. 来源完整通过后，先跑活动 exact-CB 发行人分母上的覆盖门：中位/P05 至少 95%/90%，P05 至少 50 名，至少 200 个非恒定会话、200 个非重叠三会话 cohort 和五年。任一失败即在所有 143 比较值前终止。
6. 覆盖全过后才能按冻结顺序读取 143 项唯一性比较；每项至少 50 名、100 会话，绝对中位日平均并列 Spearman 必须严格小于 0.8。第一项失败即停。
7. 只有全部无收益门通过，才按冻结三折与三个信号会话 purge 打开 2019–2023；`t+1/t+3` 必须位于同一分区。2024–2025 仍须开发 survivor 后一次性打开。

任何阶段不得加入债券 OHLC/收益、`bond_over_rate`、`cb_value`、评级/赎回/发行字段、amount 权重、其他滞后、阈值、反向、子集、模型、残差、旧因子组合或失败救援。

## 验证命令

在 `/Volumes/DIsk/Disk-Coding/qlib` 中运行：

```bash
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m black --check tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_prevalue_contract.py
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m ruff check tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_prevalue_contract.py
PYTHONPATH=. /Volumes/DIsk/Coding/anaconda3/bin/python3.12 -m pytest tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_prevalue_contract.py -q
```

发布时结果为 Black 通过、Ruff 通过、Pytest `7 passed`。测试会校验所有引用哈希、162/143 顺序、七项台账链、公式/门禁、统一报告单一标题、Candidate49 空账本和最新 active 状态。

## Candidate49 独立前瞻边界

本轮记录时为 2026-08-24 11:53:54 Asia/Singapore，早于 16:30，因此没有执行 Candidate49 plan/run。其同日流程仍只允许在目标交易日 16:30 后先 `plan`；仅 `ready=true` 且退出码 0 才可用完全相同参数执行 `run --confirm-run`。source gate 失败则保留绝对日期 staging root 和失败记录，禁止同日重试。

日线根为 `/Volumes/DIsk/Disk-Coding/qlib/data`，分钟根为 `/Volumes/DIsk/qlib-a-share-tushare-1m`。`.env` 只是 Git 忽略的 `0600` 凭据容器；不得打印、哈希、提交或写入文档 Token 值。
