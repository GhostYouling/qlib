# Campaign115：开发入口验证完成，会计追加至 v14

Campaign115 的科学状态与 v10 报告一致：唯一 higher 单因子开发试验、三组 2019–2023 扩展折、3 个信号会话清除、t+1/t+3 同分区、Top3、固定成本与存活门均已冻结；有序无收益审计尚未准入，所以候选值、比较值、日线价格、forward return 和 2024–2025 仍全部关闭。真实 standalone `plan` 保持 `ready=false`、进程退出码 2，唯一阻塞项为 `ordered_no_return_audit_admitted_one_factor`；inspection 仍为 `no_campaign115_development_trial`。

v10 发布后的组合验证出现一次新的命令环境失败：zsh 小写 `path` 是与 `PATH` 绑定的特殊变量，JSON 校验循环误用它，导致 pytest 子进程无法启动 `git`，得到 `60 passed, 7 failed`。该失败没有修改代码、测试或研究记录，也在凭据和 provider 前停止。改用普通变量 `json_path` 并在新 shell 重跑后，完全相同的 Campaign115 选择范围为 `67 passed in 9.38s`；Black、Ruff、全部选定 JSON 以及 v13 台账哈希链均通过。

因此有效会计追加为 Campaign115 23 次尝试：21 次基础设施失败、2 次预值科学尝试、0 个完整因子尝试、0 次收益读取开发试验；累计历史尝试 876，累计收益读取开发试验仍为 302。141 个完整定义和 134 个数值比较器顺序、Candidate49 唯一前瞻地位与空账本、2024–2025 关闭状态以及所有禁止边界均不变。本阶段不构成因子通过或投资建议。

当前追加绑定：验证 v2 `d19d5fcd...117d`，尝试台账 v14 `46de1e55...b204`。
