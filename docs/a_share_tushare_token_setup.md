# Tushare Token 安全配置

本项目只从环境变量 `TUSHARE_TOKEN` 读取 Tushare 凭据。真实 Token 不得写入 Git、源码、YAML、Notebook、日志、研究清单、聊天或带明文参数的 shell 命令。

本文是仓库的凭据配置规范。下面代码块中的 `token?请粘贴...` 是 zsh 的隐藏输入提示，不是 Token 占位符；请原样运行命令，等提示出现后再粘贴真实 Token，不能把真实值改写进命令本身。

## 1. 安装本项目锁定的 SDK

在仓库根目录运行：

```zsh
python -m pip install -r scripts/data_collector/a_share_rich/requirements.txt
```

## 2. macOS 隐藏输入并注入环境

下面的 `read` 不回显输入；变量名必须是 `token`，这样后两行才能引用同一个临时变量。

如果只需要让**之后启动的 Codex 等图形程序**继承 Token，使用最短配置：

```zsh
read -s "token?请粘贴 Tushare Token，随后按回车："; echo
launchctl setenv TUSHARE_TOKEN "$token"
unset token
```

如果当前终端也要立即运行数据命令，在清除临时变量前多执行一次 `export`：

```zsh
read -s "token?请粘贴 Tushare Token，随后按回车："; echo
export TUSHARE_TOKEN="$token"
launchctl setenv TUSHARE_TOKEN "$token"
unset token
```

- `export` 只让当前终端及其后启动的子进程可用；只使用最短配置时可以省略。
- `launchctl setenv` 让此后启动的 macOS 图形程序可继承。已经打开的 Codex 不会自动获得新值，需要彻底退出后重新打开。
- `unset token` 只清除临时 shell 变量，不会清除已经导出的 `TUSHARE_TOKEN`。
- `launchctl` 设置通常不跨注销或重启持久化；重启后需要重新执行隐藏输入。

不要把 Token 直接写成 `export TUSHARE_TOKEN=真实值` 或 `launchctl setenv TUSHARE_TOKEN 真实值`，否则可能进入命令历史、终端录屏或日志。也不要把它明文写进 `.zshrc`。

如果曾运行 `read -s "xxxxxx"; echo`，zsh 会把 `xxxxxx` 当成接收输入的变量名，并不会自动创建本文后续使用的 `token` 变量；此时再执行 `launchctl setenv TUSHARE_TOKEN "$token"` 可能写入空值。请直接重新运行本节使用 `token?…` 提示的完整命令，再用下一节的“有或无”检查确认，不要打印实际值排查。

## 3. 只验证“有或无”

不要单独运行会把值打印到屏幕的 `launchctl getenv TUSHARE_TOKEN`。使用只输出状态的检查：

```zsh
test -n "${TUSHARE_TOKEN:-}" && echo "当前终端：已配置" || echo "当前终端：未配置"
test -n "$(launchctl getenv TUSHARE_TOKEN)" && echo "launchctl：已配置" || echo "launchctl：未配置"
python scripts/a_share_rich_data.py status
```

`a_share_rich_data.py status` 只报告环境变量和 SDK 是否就绪，不打印 Token，也不登录供应商。

如果 `launchctl` 显示“已配置”，但当前终端或 `a_share_rich_data.py status` 仍显示未配置，说明该进程是在配置之前启动的，不代表 Token 丢失。重新启动程序，或按下一节只向单次子命令透传即可。

## 4. 当前程序尚未继承时运行一次命令

如果 `launchctl` 已配置，但当前终端或当前 Codex 是在配置之前启动的，可以只在该子进程的环境中注入值：

```zsh
token="$(launchctl getenv TUSHARE_TOKEN)"
if [[ -z "$token" ]]; then
  echo "TUSHARE_TOKEN 未配置"
  rc=1
else
  TUSHARE_TOKEN="$token" python scripts/a_share_rich_data.py status
  rc=$?
fi
unset token
exit "$rc"
```

这不会把 Token 作为命令参数传给 Python，也不会输出它。用于实际数据命令时，只替换最后一行中的 Python 子命令；仍须遵守对应数据合同与验收门禁，不能因为凭据可用就跳过单日验收或直接批量下载。

这里用 `rc` 保存命令退出码。不要在 zsh 中写 `status=$?`：`status` 是只读的特殊参数，会让包装脚本在 Python 命令成功后仍额外报错。退出当前交互式终端并非必要时，可以省略最后一行 `exit "$rc"`，改为查看或返回 `rc`。

### 4.1 运行已经冻结并获准的数据命令

只有对应的来源合同、一次性验收和本地上下文指纹都已经通过，而且研究记录没有把该分支标记为终止时，才可以把第 4 节中的 `status` 替换成数据命令。具体允许的命令与阶段必须以 [`a_share_data_pipeline.md`](a_share_data_pipeline.md) 和对应冻结合同为准，不能从旧终端记录、聊天或历史提交复制后直接运行。

经营现金流/归母净利润、业绩预告同比中点、财报披露计划及时性、审计意见、单季度毛利率同比变化、管理层连续性、ST 确认退出恢复速度和自由流通股稀缺度分支都已经到达各自的终止门禁。因此，不得再运行这些分支已消费的一次性验收、全量同步或后续审计命令。生产入口会在访问 Token、合同或供应商之前拒绝已终止命令。Token 已配置只代表本机凭据可用，不会恢复已消费的验收，也不会授权重新请求、批量下载、收益诊断、聚合、选股或下单。

Eastmoney 资产负债表韧性来源是公共接口，完全不读取 `TUSHARE_TOKEN`，也不消耗 Tushare 积分；不要用本节的 Token 包装器运行它。该分支已经完成唯一验收、全量快照、无收益审计和收益/执行诊断，并在稳定性与 Top‑3 门禁终止。终止记录是 [`a_share_eastmoney_balance_sheet_resilience_diagnostic_record.json`](a_share_eastmoney_balance_sheet_resilience_diagnostic_record.json)（SHA‑256 `b7c2888e14fab0dfa4b3f65806ac8dac6e1c46e8390df144c631869ed6da2fcf`）。无论 Token 是否配置，都不得重跑该分支，也不得继续聚合、评分、选股或下单。

对仍处于活动状态且文档明确批准的命令，继续使用第 4 节的包装方式：只替换其中的 Python 子命令，保留空值检查、`TUSHARE_TOKEN="$token"` 的单进程注入、退出码保存和 `unset token`。`--allow-large`（若某个活动合同明确要求）只表示显式确认长任务，不能放宽合同或后续门禁。运行期间不要启动第二份相同同步；若出现锁，先确认现有进程，不要直接删除锁文件。

#### 自由流通股稀缺度分支已终止

`2026-07-13` 单日验收和唯一的 2019–2025 全量请求都已成功消费；全量本地快照共 7,098,264 行，来源记录是 [`a_share_tushare_free_float_scarcity_full_source_record.json`](a_share_tushare_free_float_scarcity_full_source_record.json)。随后唯一的联合无收益审计通过 540/200 容量门，但冻结的 54 字段唯一性规则只得到 46 个具备至少 100 个可比交易日的字段：龙虎榜五项和股东户数三项过于稀疏，因此整体门禁失败。终止记录是 [`a_share_tushare_free_float_scarcity_research_record.json`](a_share_tushare_free_float_scarcity_research_record.json)。

不得再运行 `acceptance-tushare-free-float-scarcity` 或 `sync-tushare-free-float-scarcity --allow-large`。两个入口都会在访问合同、Token 或供应商前拒绝；联合无收益审计入口也会先读取跟踪的终止记录并拒绝。不得复制旧命令、删除本地运行记录后重试、修改日期/字段/公式/方向/阈值、事后删掉稀疏比较字段，或继续收益、聚合、评分、选股、仓位和订单。Token 状态检查仍可运行，但不会恢复任何已消费权限。

#### Eastmoney 资产负债表韧性分支已终止

这个来源不使用 Tushare Token。唯一 2019Q1–2025Q4 快照有 28 个季度分区、113,916 行；无收益容量与 46 个稠密字段唯一性门都通过，但唯一收益诊断的正 IC 比例只有 48.01%，2022、2024、2025 年平均 IC 为负，执行账本最大回撤为 −62.33%。20 万元、100 股整手、双边 0.1% 滑点的可负担席位比例仅 77.12%，且 2021、2022、2024 年收益为负。稳定性和 Top‑3 审计均未留下合格因子。

不得运行 `acceptance-eastmoney-balance-sheet-resilience`、`sync-eastmoney-balance-sheet-resilience --allow-large`、`eastmoney-balance-sheet-resilience-no-return-audit` 或 `eastmoney-balance-sheet-resilience-diagnostic`，也不得把已保存诊断重新交给通用稳定性/Top‑3 审计。CLI 的跟踪终止记录会拒绝这些重跑。`TUSHARE_TOKEN` 的配置、更新或轮换与该分支无关，不会恢复运行许可。

#### Eastmoney 核心利润一致性分支已终止

当前候选 `eastmoney_core_profit_consistency` 使用 Eastmoney 公共利润表接口，不读取 `TUSHARE_TOKEN`，也不消耗 Tushare 积分。唯一来源验收和 2019Q1–2025Q4 全量同步均已永久消费；全量快照有 28 个季度分区、92,764 行。跨克隆来源记录是 [`a_share_eastmoney_core_profit_consistency_full_source_record.json`](a_share_eastmoney_core_profit_consistency_full_source_record.json)（SHA‑256 `be6d43b7fb1e707898b88180c5d5a180bb4e28620fb8d9c646ef1c58cb7604fb`）。不得再次运行 `acceptance-eastmoney-core-profit-consistency` 或 `sync-eastmoney-core-profit-consistency --allow-large`。

唯一联合无收益审计已经通过：保守状态规则得到 304/200 个潜在完整三日非重叠 cohort，覆盖 2020–2025 六年；47 个稠密比较字段均有至少 100 个可比交易日且绝对中位日秩相关低于 0.8。通过记录是 [`a_share_eastmoney_core_profit_consistency_research_record.json`](a_share_eastmoney_core_profit_consistency_research_record.json)（SHA‑256 `753b20b657c5e233dc9948d46f9a29f5cea56b40a7163e757b9018303a4f4c9d`）。无收益审计入口也已消费，不能重跑。

唯一收益与执行诊断已经完成：360 个 cohort 的平均 Rank IC 为 −0.00274，正 IC 比例 48.89%，Top‑3 扣成本累计 −38.22%、最大回撤 −68.64%；执行账本累计 −43.76%。20 万元、100 股整手、双边各 0.1% 滑点的方案累计 −6.14%，整手可负担率 83.24%，2020–2024 每年均为负，且最大成交额参与率 1.344% 超过 1% 上限。默认稳定性和 Top‑3 门禁均为 **0/1**。

跨克隆终止记录为 [`a_share_eastmoney_core_profit_consistency_diagnostic_record.json`](a_share_eastmoney_core_profit_consistency_diagnostic_record.json)（SHA‑256 `970c76e87ee664df2085e305472fc49ea92c5652af8da246f359450ff641907f`）。不得再次运行验收、全量、无收益审计、收益诊断或两道通用门禁，也不得反向、挑选年份、改变公式/状态/持有期/TopK/成本或与已拒绝因子组合。`TUSHARE_TOKEN` 的配置、更新或轮换不会恢复该分支；它不进入聚合、当前评分、选股、仓位或订单。提交仓库不包含本机 Token 或 `launchctl` 环境值。

### 4.2 `stock_st` 分支已终止

ST 恢复速度的唯一全量来源尝试已经消费：完成 58 个历史会话后，2019‑04‑01 返回空表。冻结合同不允许把空表当作“当天没有 ST 股票”，因此程序停止、删除完整临时快照且没有发布年度分区；转换、因子、价格和收益均未读取。终止记录是 [`a_share_tushare_st_recovery_research_record.json`](a_share_tushare_st_recovery_research_record.json)。

不得再运行 `sync-tushare-stock-st-membership`，也不得从旧终端、聊天、shell 历史或 Git 历史复制其命令。入口会在来源链、Token 和供应商访问前拒绝。不要重请求失败日期、跳过/填充空日、把前 58 个会话当作局部历史，或换名称解析/供应商来补合同。Token 状态检查仍可运行，它不会恢复已消费的来源合同。

### 4.3 已终止分支状态

`fina_audit` 审计意见分支的一次性来源验收和全量同步已经完成，但固定三日、非重叠队列只有 9 个同时具备两种二值结果的有效截面，未达到 200 个截面的无收益容量门槛。终止记录是 [`a_share_tushare_audit_opinion_research_record.json`](a_share_tushare_audit_opinion_research_record.json)。不要再次运行验收、全量同步或容量审计，也不要降低门槛、改变文本映射、延长事件有效期或继续读取收益。

`fina_indicator` 单季度毛利率同比变化分支的一次性验收已经成功，但唯一一次全量来源同步在 `SH600638` 的第二个固定报告期切片遇到一条必需身份、日期或版本字段不完整的来源行。原子发布逻辑已删除全部临时分区且没有读取价格或收益。终止记录是 [`a_share_tushare_gross_margin_research_record.json`](a_share_tushare_gross_margin_research_record.json)。不要重请求该股票、丢弃或填补异常行、修改字段/切片/公式，或重跑验收和全量同步。

这些结果说明的是固定研究合同已经消费或失败，不说明 Token 失效。候选 `tushare_express_asset_growth_restraint = -growth_assets` 的唯一三股票验收也已经消费：三次固定请求共返回 17 行，但 `growth_assets` 全部缺失或非有限，得到 0 个有效事件，未发布 Parquet、未形成有限因子值，也未读取价格或收益。跨克隆终止记录为 [`a_share_tushare_express_asset_growth_source_acceptance_record.json`](a_share_tushare_express_asset_growth_source_acceptance_record.json)（SHA‑256 `71a61cdfb33359e07f74e101b7958258fce08a70974aee2be0aab16179e48b1e`）。不得再次运行 `acceptance-tushare-express-asset-growth`、换股票/日期/字段、在同一响应里寻找替代因子，或继续全量、收益、聚合、评分、选股和下单；入口会在合同、Token 和供应商访问前拒绝。

合同负债需求积压候选已经按 [`a_share_tushare_contract_liability_backlog_data_contract.json`](a_share_tushare_contract_liability_backlog_data_contract.json)（SHA‑256 `4c6105188ce7246fd9069fdf3e547e612813998b6316ec332e42acdb0aecf611`）完成唯一 12 次来源验收：146 条来源行得到 69 个可用报告期和 55 个有限因子事件，三只股票分别为 19、17、19 个事件；原始响应、合同负债/总资产金额、价格和收益均未保存。跨克隆验收记录为 [`a_share_tushare_contract_liability_backlog_source_acceptance_record.json`](a_share_tushare_contract_liability_backlog_source_acceptance_record.json)（SHA‑256 `5a06db91c904c38bf0415cbff7cec6987e72212d8349a3805ca4a7749911295b`），入口会在合同、Token 和供应商访问前拒绝再次运行 `acceptance-tushare-contract-liability-backlog`。

这个通过只证明固定样本的来源、版本与公式可用，不是因子收益或选股证据。尚未冻结新的全市场来源与无收益协议，因此不得直接运行全量、读取价格或收益、聚合、评分、选股或下单。必须先绑定已验收 manifest/Parquet、点时来源宇宙、日历、精确调用数/切片、原子性、覆盖、容量与稠密唯一性。本文的 Token 配置步骤本身不构成这些运行许可。

`stk_managers` 管理层连续性分支也已在唯一一次来源验收的第一个股票请求上终止：`000001.SZ` 的 184 行中有 53 行完整离任日不等于公告日，不满足预先冻结的历史点时规则。其余两只验收股票未请求，姓名、身份哈希、原始响应、价格和收益均未持久化。终止记录是 [`a_share_tushare_management_continuity_source_acceptance_record.json`](a_share_tushare_management_continuity_source_acceptance_record.json)。不得重跑、请求剩余股票、改写离任日规则或继续全量与收益研究。

## 5. 清除配置

```zsh
unset TUSHARE_TOKEN
launchctl unsetenv TUSHARE_TOKEN
```

清除后重新运行第 3 节的状态检查。仓库内任何文件都不应包含真实 Token；如果曾误写或误提交，应立即在 Tushare 账户侧轮换 Token，再清理泄露位置，不能只删除最新一行提交记录。

## 6. 交给 Codex 使用

完成第 2 节的 `launchctl setenv` 后，彻底退出并重新打开 Codex，再让它在本仓库运行 `python scripts/a_share_rich_data.py status`。你只需确认输出中 Tushare 环境变量和 SDK 已就绪，不需要把 Token 发给 Codex，也不要粘贴任何 `launchctl getenv` 的明文输出。

本项目的后续数据命令必须从进程环境读取 `TUSHARE_TOKEN`，并且仍要遵守对应数据合同的单日验收、不读取收益门禁和原子发布要求。“状态已就绪”只证明本机凭据可用，不代表已授权跳过验收、批量下载、因子诊断或选股。

## 7. 更新或轮换 Token

先在 Tushare 账户侧生成或确认新 Token，再重新执行第 2 节的隐藏输入命令。`launchctl setenv` 会覆盖供**之后启动的程序**继承的旧值，但已经运行的终端、Codex、Notebook 或其他 Python 进程仍可能保留旧环境，需要关闭后重新启动。

如果当前终端也必须立即切换到新 Token，请使用第 2 节包含 `export` 的版本；不要只更新 `launchctl` 后继续从旧终端运行数据命令。更新完成后只执行第 3 节的“已配置/未配置”检查，不要打印新旧 Token 做对比。

一旦怀疑 Token 曾进入命令历史、日志、截图、聊天或 Git，必须立即在 Tushare 账户侧轮换，并检查 Git 历史和相关输出；仅执行 `unset` 或删除工作区文件不能撤销已经发生的泄露。
