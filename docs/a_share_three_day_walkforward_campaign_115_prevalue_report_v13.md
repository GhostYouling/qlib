# Campaign115：零网络门禁链退出码不再被掩盖

Campaign115 的五段科学门禁现有一个只读统一状态入口：`scripts/a_share_tushare_limit_up_queue_gate_chain.py status`。它按冻结顺序分别启动验收 plan/inspection、开发源 plan、语义验真 plan/inspection、有序无收益 plan/inspection、开发试验 plan/inspection；每个子命令的真实退出码和唯一 JSON 对象都独立校验，不再依赖会掩盖前序退出码的组合 shell 命令。入口没有 run、confirm 或 provider 接口，并对任何凭据泄漏、provider 请求、候选/比较值、日线/forward return、2024–2025、Candidate49 回填或当前评分/选股/仓位/订单声明 fail-closed。

真实状态入口退出 0 表示“门禁链的读取与语义验证成功”，不表示科学门禁已打开。五个 plan 的真实退出码仍依次为 `2/2/2/2/2`：验收只缺用户对当前账号已有 5,000 积分的明确确认；开发源还缺验收成功；语义验真缺最终源根及两份字节一致清单；有序无收益审计缺语义收据和最终源根；开发试验缺单因子审计准入。四个 inspection 均退出 0，状态分别为 `no_attempt_journal`、`no_semantic_verification_receipt`、`no_ordered_no_return_audit`、`no_campaign115_development_trial`。因此没有任何 confirmed scientific command 或 provider action 获得授权。

新增实现与测试的 Black、Ruff 均通过，聚焦回归为 `3 passed in 9.68s`，包含 plan 退出码不一致和 provider 请求声明的 fail-closed 负控。权威复核同时确认 `.env` 是 Git 忽略的 mode-0600 普通文件，恰有一个非空 `TUSHARE_TOKEN` 赋值，但未打印、哈希、记录或持久化其值；Candidate49 信号/执行账本仍为 0 条。首次本地元数据核验误用不存在的裸 `python` 别名并在程序体前退出 127，已追加记录为 `campaign115_infrastructure_025`。

有效会计为 Campaign115 25 次尝试：23 次基础设施失败、2 次值前科学尝试、0 个完整因子尝试、0 次收益读取开发试验；累计历史尝试 878，累计收益读取开发试验 302。141 个完整定义、134 个数值比较器、Campaign115 公式/方向/门槛、Candidate49 唯一前瞻地位、2024–2025 关闭状态及所有当前使用禁令均未改变。只有你明确确认当前 `.env` 对应账号已经具备至少 5,000 积分后，才允许带冻结确认参数重新运行验收 plan；仍须 `ready=true` 且该 plan 自身退出 0 才能执行一次性 confirmed run。本阶段不构成因子通过或投资建议。
