# Campaign115：有序无收益审计直接入口修复

Campaign115 的科学状态不变：唯一 higher 因子仍为 `tushare_official_limit_up_queue_persistence`，完整 1,214 会话开发源与语义回执尚不存在，候选值、134 个比较值、日线价格、forward return 和 2024–2025 均未打开。有序无收益审计不存在，开发试验也不存在。

本轮发现冻结协议的直接命令 `python scripts/a_share_tushare_limit_up_queue_no_return_audit.py plan` 在干净进程中无法导入 `scripts` 包。根因是脚本只把自身目录加入 `sys.path`，却没有加入该包的父目录（仓库根）。失败发生在参数解析和任何研究值读取之前，已追加为 `campaign115_infrastructure_024`；旧实现冻结和失败证据均保留。

版本化 v5 修复只在包导入前加入仓库根，并新增干净子进程回归，不改变公式、方向、年份、比较器顺序、覆盖/唯一性门、成本、存活门、路径或数据读取边界。修复后精确协议入口可运行，真实 `plan` 退出码为 2，且只剩 `semantic_verification_receipt_valid`、`source_final_root_present` 两项阻塞；`audit_runtime_binding=true`，134 个比较器元数据绑定全部通过。计划明确报告候选/比较 Parquet、日线/收益、2024–2025、凭据和 provider 均未读取或调用。聚焦回归为 `11 passed in 14.91s`。

有效会计更新为 Campaign115 24 次尝试：22 次基础设施失败、2 次值前科学尝试、0 个完整因子尝试、0 次收益读取开发试验；累计历史尝试 877，累计收益读取开发试验 302。141 个完整定义、134 个数值比较器、Candidate49 唯一前瞻地位及空账本均未改变。本轮不是因子通过，不启动 Campaign116，不生成当前评分、选股、仓位、订单或投资建议。

当前追加绑定：实现冻结 v5 `c964abe5...560d`，验证 v2 `5c348329...3c12`，尝试台账 v15 `592f2674...1e9d`。
