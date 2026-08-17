# Campaign115：一次请求的零网络取证

Campaign115 的验收 runner 新增只读 `inspect-attempt`。它不读取 `.env`、不加载 Token、不创建 provider 客户端，也不授权重试。无 journal 时，它只报告尚未开始；有 journal 时，它以禁止跟随符号链接、0600、唯一 inode 和 64 KiB 上限读取完整 JSONL，严格校验 intent、事件字段、状态转移、provider 调用数、失败码连续性及细节白名单。

取证不再只看终态文件是否存在。success manifest 和 failure record 必须同样是私有唯一文件，并通过固定 schema、协议/数据契约指纹、日期、字段、调用数和 journal 绑定；成功状态还要求 factor frame 路径、4592 行声明和实际 SHA-256 一致。畸形 journal、乱序事件、符号链接、篡改清单、成功/失败冲突或 frame 哈希不符都会退出 2，且仍禁止重试。

31 项适配器与 runner 定向测试、66 项 Campaign113 至 Campaign115 联合回归通过。真实 `inspect-attempt` 返回 `no_attempt_journal`、退出 0、凭据加载与 provider 请求均为 false；真实 plan 的唯一 blocker 仍是用户尚未明确确认当前账户已有 5000 积分。真实 provider 请求、journal、成功/失败清单和 factor frame 均为 0。

本轮一个组合补丁因上下文错位被 `apply_patch` 在任何写入前整体拒绝，随后拆分后成功；追加式台账 v7 将它记为一次基础设施失败。Campaign115 当前为 7 次尝试，其中基础设施失败 5、预值科学尝试 2、完整因子与收益试验均为 0；累计历史尝试为 860，收益读取试验仍为 302。公式、来源、方向、日期、门槛、141 个完整定义、134 个数值比较器以及 Candidate49 两本前瞻台账均未改变。
