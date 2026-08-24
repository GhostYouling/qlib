# Campaign265 零网络来源验收计划报告

Campaign265 已完成一次性 source-acceptance planner 的值前冻结、实现和零网络执行。`plan` 返回 `ready=true`、实际退出码 0、单个 JSON、无 blocker；它固定了 2019-01-02 至 2025-12-31 共 1,699 个接受交易日，以及 1 次 `cb_basic` 加 1,699 次逐日 `cb_daily`，合计精确 1,700 次未来请求。完整日期清单摘要为 `f9205c3c...bc769`，请求序列摘要为 `3f9cccb3...b4c58`。

字段保持来源合同原样：`cb_basic` 仅 `ts_code,cb_type,stk_code,list_date,delist_date,exchange`，`cb_daily` 仅 `ts_code,trade_date,amount,cb_over_rate`。每次响应必须至少一行且严格少于 2,000 行；禁止分页、代码循环补数、字段扩展或失败响应重请求。未来 provider entry 的最小本地间隔冻结为 1.05 秒。

计划同时冻结了 Git 忽略的私有 staging/final root、逐日原子 checkpoint、来源 manifest、独占 intent、追加式 attempt journal 和终止 failure 路径。任何 permission、transport、schema、空响应、截断、身份、日期、映射或持久化失败都会终止该精确定义。只有“所有已授权请求都有已 fsync 的原子 checkpoint，且不存在 inflight 请求”的精确前缀才允许继续；已授权但未提交 checkpoint 的请求属于不可重试的终止证据。

本阶段没有读取 `.env` 或环境凭据，没有读取或哈希 Token 值，没有导入/创建 provider client，没有发出请求，没有创建 intent、journal、staging 或 final 文件，也没有读取来源行、候选/比较器值、日线价格或 forward return。`ready=true` 只证明离线计划绑定和目标缺失检查有效，绝不授权加载凭据或访问 provider。任何未来执行 workflow、确认参数和来源请求都必须另行冻结并由新政策明确授权。

Black、Ruff 和 Campaign265 四个测试文件共 42 项检查全部通过，其中 planner 专属合成/静态测试 12 项。首次权威核验因猜错两个 Candidate49 台账路径失败，首次 Ruff 因一个未使用导入失败；两者均作为基础设施证据追加，没有被隐藏或当成科学结果。Campaign265 当前有效会计为 13 次尝试：8 次值前科学尝试、5 次基础设施失败、完整因子尝试 0、收益读取开发试验 0；累计历史尝试 2,617，累计收益读取开发试验 315。

完整定义/数值比较器库继续保持 `162/143`。Candidate49 仍是唯一前瞻候选，信号/执行账本为 0/0 且哈希不变；没有历史回填、第二前瞻候选、当前评分、选股、仓位、订单或投资建议。下一步仍属于 Campaign265，只允许另行冻结 credential-safe 的一次性执行 workflow；在那之前不能读取凭据或请求来源。
