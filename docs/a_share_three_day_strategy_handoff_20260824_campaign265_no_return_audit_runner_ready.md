# A 股三日短线研究交接：Campaign265 下游零收益审计入口就绪

记录时间：2026-08-24 14:42 Asia/Singapore

工作区：`/Volumes/DIsk/Disk-Coding/qlib`（用户入口 `/Users/niyufei/Coding/qlib` 指向同一仓库）

分支：`faet/local-test`

持续目标：`请持续迭代因子。`，状态 `active`

## 一句话状态

Campaign265 的可转债平价溢价压缩因子已经完成公式、来源验收和下游零收益审计的事前冻结与实现；真实审计计划目前仅因接受来源清单不存在而退出 2。没有读取 Candidate265/比较器/日线价格/收益值，v420 未发布，来源未请求，Candidate49 仍是唯一前瞻候选且账本 0/0。

## 当前策略定义

- 因子：`convertible_bond_equity_parity_premium_compression_3s`
- 方向：higher
- 信号标签：接受的 A 股会话 `t`；因 Tushare `cb_daily` 17:00 发布，值最早只能在下一接受会话开盘使用。
- 单债：同一 exact `CB` 在 `t-3` 与 `t` 两端均活动、存在行、`amount>0` 且 `cb_over_rate` 有限，值为 `cb_over_rate(t-3)-cb_over_rate(t)`。
- 发行人：同一正股多只合格转债取确定性算术中位数；无合格债保持缺失，禁止置零、前向填充、换窗口或替代字段。
- 历史范围：2019-01-02 至 2025-12-31，共 1,699 个接受会话；来源计划为 1 次 `cb_basic` 加 1,699 次 `cb_daily`，共 1,700 次未来调用。

## 新完成的下游审计

权威入口：

- 协议：`docs/a_share_three_day_walkforward_campaign_265_no_return_audit_protocol_20260824.json`
- 实现冻结：`docs/a_share_three_day_walkforward_campaign_265_no_return_audit_implementation_freeze_20260824.json`
- runner：`scripts/a_share_three_day_walkforward_campaign265_no_return_audit.py`
- 真实计划结果：`docs/a_share_three_day_walkforward_campaign_265_no_return_audit_plan_result_20260824.json`
- 最新状态：`docs/a_share_three_day_iteration_status_20260824_campaign265_no_return_audit_runner_ready.json`
- 追加台账：`data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v19.json`

审计顺序不可改变：

1. `plan` 只检查 JSON、真实目录、0600 文件、1,700 个 request/sidecar/schema/字节哈希和输出不存在；不解码 Parquet。
2. `audit` 才能解码已接受的标准化转债快照并构建候选。
3. 先检查六项覆盖/容量门：日覆盖中位数 ≥0.95、P05 ≥0.90、P05 名数 ≥50、非恒定横截面 ≥200、非重叠三信号会话 cohort ≥200、观察年份 ≥5。
4. 覆盖失败时发布聚合终止结果，比较器读取数必须为 0。
5. 覆盖通过后按冻结顺序一次只读一个比较器：Campaign132 的前 140 个、Campaign136、Campaign146、Campaign263，共 143 个。
6. 每个比较器要求每会话至少 50 个精确交集名字、至少 100 个有效会话，`abs(median daily average-tie Spearman)<0.8`。首个失败立即停止，后面的比较值保持关闭。
7. 只有 143/143 全部通过，才能另冻一次 2019–2023 三折开发试验；本 runner 不读任何日线价格或收益。

## 当前实测

- `python scripts/a_share_three_day_walkforward_campaign265_no_return_audit.py plan`
- 实际退出码：2
- `ready=false`
- 唯一 blocker：`source_acceptance_manifest_absent_or_unsafe`
- Parquet 解码、候选、比较器、价格/收益、凭据和 provider 读取：全部 0
- 审计输出：不存在
- 11 项新合成测试通过；连同状态语义、adapter、source workflow 和 v420 publisher 的最终套件共 52 passed；Ruff 通过。
- Campaign265：40 次尝试（15 科学、25 基础设施），完整因子尝试 0，收益读取开发试验 0。第 23 次基础设施失败是 staged diff 发现三处 Markdown 行尾空格；第 24 次是无匹配本应退出 1 的 staged secret scan 被 shell `true` 掩盖；第 25 次是会计补丁使用了不精确的报告尾部上下文并在写入前失败。三次输出均作废并以独立检查恢复。
- 全局累计：2,644 次历史尝试，315 次收益读取开发试验；完整定义/合格数值比较器 `162/143`。

## 严格执行顺序

当前不要执行发布或来源 run。只有用户明确授权 v420 发布和来源获取时，才按以下步骤逐个执行并保留真实退出码：

```bash
python scripts/a_share_three_day_walkforward_campaign265_v420_authorization.py plan
python scripts/a_share_three_day_walkforward_campaign265_v420_authorization.py publish --confirm-v420-publication
python scripts/a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py plan
python scripts/a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py run --confirm-run
```

前一步非零或 `ready!=true` 时不得继续。source workflow 任一 permission/transport/schema/truncation/identity/date/persistence 失败均终止本合同，不得重试、补字段、换端点或为诊断再次请求失败响应。

来源成功并产生不可变 acceptance manifest 后：

```bash
python scripts/a_share_three_day_walkforward_campaign265_no_return_audit.py plan
python scripts/a_share_three_day_walkforward_campaign265_no_return_audit.py audit --confirm-no-return-audit
```

同样只有 `plan` 的退出码 0 且 `ready=true` 才能单独确认 `audit`。不得把两个命令串联为忽略失败码的 shell。

## 不可越界事项

- 不发布 v420、不发 provider 请求，除非用户给出新的明确授权。
- 不绕过任何退出码、缺失清单、哈希、路径、权限、覆盖或唯一性门。
- 不改 Campaign265 公式、方向、三会话 lag、字段、分母、缺失语义、143 顺序或阈值。
- 不读 2024–2025 收益，除非未来完整有限 campaign 先冻结并满足一次性开启条件。
- 不回填 Candidate49 历史收益/信号/执行；不启动第二个前瞻候选。
- 不生成当前评分、选股、仓位或订单；研究结果不构成投资建议。

## 持续迭代含义

目标仍是 active，而不是等待每天新日线。Campaign265 的安全下游路径已经预先完成；来源尚未获准时，可以继续零网络、有限、事前冻结的离线历史研究，但不得用旧终止因子的换统计量、组合、调权或模型救援伪装成独立新因子。Candidate49 未来观察继续作为独立确认层。
