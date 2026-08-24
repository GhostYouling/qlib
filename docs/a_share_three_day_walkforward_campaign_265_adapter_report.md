# Campaign265 零网络适配器阶段报告

Campaign265 已把值前冻结的可转债溢价压缩合同实现为纯函数适配器，但仍没有打开任何真实来源值或收益。

适配器只接受合约规定的 `cb_basic(ts_code,cb_type,stk_code,list_date,delist_date,exchange)`、单交易日 `cb_daily(ts_code,trade_date,amount,cb_over_rate)`、接受交易日序列和因子股票池。它没有 CLI、网络客户端、Token 接口、真实 Parquet/CSV loader 或 provider transport。

公式保持不变：在信号会话 `t` 和前三个接受会话 `t-3`，同一 exact `CB` 必须两端都在存续期内、都有有限 `cb_over_rate` 和严格正 `amount`；单债分数为 `cb_over_rate(t-3)-cb_over_rate(t)`。同一正股有多只合格转债时取算术中位数，偶数只取中间两值平均。活动转债发行人进入分母；没有合格端点时分数保持缺失，绝不置零或前向填充。

16 个纯合成测试覆盖了投影顺序、NFKC/大写身份、代码与交易所一致性、债券及债券日期唯一性、exact CB/EB 语义、严格日期、A 股股票池、存续期、精确 `t-3`、双端点成交、奇偶中位数、未知债券失败和缺失非零化。Black 与 Ruff 通过。首轮 Black `--check` 只发现两个新文件需机械格式化，因此 Ruff 和 pytest 当次没有执行；该失败与随后通过的适配器实现均已追加到 v2 哈希链。

本阶段没有加载 Token、发出 provider 请求、读取 `cb_basic`/`cb_daily` 真实行、候选/比较器值、日线价格或 forward return。完整定义和数值比较器仍为 `162/143`；Campaign265 有效尝试为 9，其中基础设施失败 2、值前科学尝试 7、完整因子尝试 0、收益读取开发试验 0。累计历史尝试为 2,613，累计收益读取开发试验仍为 315。

下一步仍在 Campaign265 内，只允许另行冻结一次性 source-acceptance planner。planner 必须绑定当前合同、适配器和测试字节、接受日历完整日期清单、`cb_basic` 一次请求、每个接受日一次 `cb_daily`、精确字段、2,000 行截断门、调用数/限流、私有意图、原子目标与终止不重试证据。当前阶段不授权加载凭据或请求来源。

Candidate49 仍是唯一前瞻候选，信号/执行账本保持 0/0，禁止历史回填、启动 Candidate50、当前评分、选股、仓位、订单或把本阶段解释为投资建议。
