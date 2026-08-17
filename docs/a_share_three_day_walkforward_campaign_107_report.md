# Campaign107 历史滚动研究报告

Campaign107 唯一冻结的 higher 因子是 `intraday_exact_close_level_diversity_240m`。对 09:31–11:30、13:01–15:00 的精确 240 根连续竞价分钟 bar，只读取有限且严格为正的 `close`；按精确数值相等分组，若各价位出现次数为 `n_j`，分数为 `1-sum(n_j*(n_j-1))/57360`。09:30 只参与 241 行源网格校验，不进入公式。公式不做四舍五入、容差、tick 推断、分箱、标准化、阈值或路径顺序使用；常量路径合法且得 0，240 个价位全异得 1。

## 值前冻结与失败保留

有限 5 项机制目录只选中这一项；其余竞价区间占比、十字星占比、成交量熵和收益符号转移熵分别因源占位或旧机制重表达在值前淘汰。raw comparator 适配器先通过 10 个有限值/合法 NaN/无穷/值域/身份合成测试；完整候选与审计冻结套件通过 25 项测试。

首版预注册的 accepted minute-alignment SHA 有一处抄写错误，8 个绑定中 1 个失败；原文件保留，additive overlay 仅修正该 SHA 并重绑 Campaign106 state-v3、policy-v66 和 completion-v2。快照构建后首次 verify 命令误传 `--data-root` 而非必需的 `--manifest`，在 argparse 阶段退出且未读快照值；该失败也追加保留。两次均不改变公式、方向、门槛、折、成本或库顺序。

## 不可变快照与覆盖

快照含 33,015 个分区、7,724,498 行且全部有效。manifest SHA-256 为 `bb41c7f807733709f5e10a12a86177ba18934d496581b172930717787a9f8c3e`，dataset SHA-256 为 `b333c26b770e1e6724ef1e5b474171a866749792e2ea3c43fcf67e15cb62706e`。独立验证通过全部分区字节/数据帧哈希、总数据集指纹与 `1/28680` 离散格点语义；底层读取字段严格为 `datetime,symbol,provider,close`。

质量/当前上市口径有 1,331,759 行，候选有效 1,330,171 行；1,632 个交易会话的覆盖中位/P05 为 `99.945175%/99.568865%`，P05 有效名称 138，可形成 540 个不重叠三会话 cohort，覆盖 2019–2025 七个年份。覆盖门通过后才加载比较器。

## 132 项去重终局

132 项比较全部按冻结顺序完成，raw comparator 合法缺失保持到成对重叠门。共有 5 项违反严格 `<0.8` 门槛：`intraday_price_update_share_238m` 为 `0.931553`，`intraday_unchanged_close_range_absorption_share_238p` 为 `0.894654`，`intraday_terminal_nominal_share_price_affordability_rank_240m` 为 `0.887056`，`intraday_return_weak_order_entropy_234t` 为 `0.816633`，`intraday_price_update_clock_entropy_10b_238m` 为 `0.809491`。

因此候选被明确判定为 `rejected_as_numerically_redundant`，不得反向、改相等规则、加容差/分箱、过滤、残差化、重组或救援。2019–2023 唯一开发试验没有打开；2024–2025 压力收益没有打开或读取，日线价格与 forward return 均未读取。

## 会计与边界

Campaign107 共 3 次历史尝试：1 次完整科学因子尝试和 2 次基础设施失败；追加台账有 4 条，其中终局科学结果是同一尝试的零增量延续。累计历史研究尝试为 794，累计收益读取开发试验保持 300。v67 把本公式追加到完整语义库，库由 136 增至 137；因去重失败，数值比较器仍保持 132 个及原顺序。

Candidate49 仍是唯一前瞻候选，两本账各 0 条；本轮没有 provider 请求、历史回填、第二前瞻候选、当前评分、选股、仓位、订单或投资建议。
