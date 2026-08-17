# Campaign115：单次 2019–2023 开发试验入口已冻结，收益仍关闭

Campaign115 的离线历史迭代引擎继续推进。本轮在任何候选值、比较值、日线价格或 forward return 之前，冻结了 `tushare_official_limit_up_queue_persistence` 的唯一开发试验。完整搜索空间只有一个 higher 单因子、权重 1.0 的 trial：`wf115_tushare_official_limit_up_queue_persistence_single_higher`；没有反向、阈值、过滤、子集、年份、权重、模型或组合搜索。

开发样本固定为 2019–2023 三组扩展折：2019–2020 训练/2021 验证、2019–2021 训练/2022 验证、2019–2022 训练/2023 验证。每个分区边界清除 3 个信号会话，信号为 t 收盘、t+1 开盘进入、t+3 收盘退出，且 t+1 与 t+3 必须完整落在同一训练或验证分区。Top3、CNY 200,000、每槽 5%、单信号 15%、100 股整手、双边佣金/过户费、卖出印花税、双边 10bp 不利滑点和 1% 日成交额参与上限均沿用已冻结政策。存活要求同时通过三折关联、价差、normalized execution、10bp pilot、整手可负担性、容量、回撤及全开发期 20bp 成本门。

新 runner 只暴露 `plan`、显式确认的 `run-development` 和只读 `inspect-trial`，不暴露 2024–2025 stress 命令，也没有凭据或 provider 客户端。`plan` 只读取冻结 JSON 与文件元数据；只有不可变有序无收益审计恰好准入这一个因子、134 项比较全部通过且源语义绑定仍成立时，才会返回 `ready=true` 和退出码 0。运行前会在同一调用中再次验证 admission。2024–2025 仍是历史已暴露的准样本外压力层，只能在唯一开发试验完成且非零 survivor 记录冻结后，为完整 campaign 一次性另行开放；本实现阶段保持关闭。

实现前后合成测试均为 10 项通过；Campaign115 选择性回归为 `67 passed in 10.16s`，Black 检查通过，Ruff `E4,E7,E9,F,I` 通过。真实 standalone `plan` 正确退出 2，唯一阻塞项为 `ordered_no_return_audit_admitted_one_factor`；standalone `inspect-trial` 退出 0 并返回 `no_campaign115_development_trial`。候选值、比较值、价格、收益、2024–2025、凭据及 provider 读取标志均为 false。

本轮追加记录 3 次基础设施失败：应用给出的 `/Users/...` 路径不是权威 Git 工作树；首轮 Ruff 发现一个未使用导入；首次 post-freeze shell 把 plan 与 inspect 连跑，导致后者的 0 掩盖了 plan 的预期退出码 2。三者均在研究值之前发生；独立重跑已经确认 plan 的真实进程退出码为 2，没有执行开发试验。

Campaign115 当前累计 22 次尝试，其中基础设施失败 20、预值科学尝试 2、完整因子尝试 0、收益读取开发试验 0；全部历史研究累计尝试 875，累计收益读取开发试验仍为 302。141 个完整定义和 134 个数值比较器顺序不变。Candidate49 继续是唯一前瞻候选，没有历史回填、第二前瞻候选、当前评分、选股、仓位、订单或投资建议。当前上市快照的存活偏差限制继续保留。

权威绑定：开发协议 `7a6a537c...94ef`，实现冻结 `d7de827b...b67d`，runner `a34c278c...5d85`，验证记录 `5c74e8bc...6d70`，v13 追加台账 `6f8a25c7...6788`。
