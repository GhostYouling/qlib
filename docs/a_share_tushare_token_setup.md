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

经营现金流/归母净利润、业绩预告同比中点、财报披露计划及时性、审计意见和单季度毛利率同比变化分支都已经到达各自的终止门禁。因此，不得再运行这些分支已消费的一次性验收、全量同步或后续审计命令。生产入口会在访问 Token、合同或供应商之前拒绝已终止命令。Token 已配置只代表本机凭据可用，不会恢复已消费的验收，也不会授权重新请求、批量下载、收益诊断、聚合、选股或下单。

对仍处于活动状态且文档明确批准的命令，继续使用第 4 节的包装方式：只替换其中的 Python 子命令，保留空值检查、`TUSHARE_TOKEN="$token"` 的单进程注入、退出码保存和 `unset token`。`--allow-large`（若某个活动合同明确要求）只表示显式确认长任务，不能放宽合同或后续门禁。运行期间不要启动第二份相同同步；若出现锁，先确认现有进程，不要直接删除锁文件。

### 4.2 当前审计意见与毛利率分支状态

`fina_audit` 审计意见分支的一次性来源验收和全量同步已经完成，但固定三日、非重叠队列只有 9 个同时具备两种二值结果的有效截面，未达到 200 个截面的无收益容量门槛。终止记录是 [`a_share_tushare_audit_opinion_research_record.json`](a_share_tushare_audit_opinion_research_record.json)。不要再次运行验收、全量同步或容量审计，也不要降低门槛、改变文本映射、延长事件有效期或继续读取收益。

`fina_indicator` 单季度毛利率同比变化分支的一次性验收已经成功，但唯一一次全量来源同步在 `SH600638` 的第二个固定报告期切片遇到一条必需身份、日期或版本字段不完整的来源行。原子发布逻辑已删除全部临时分区且没有读取价格或收益。终止记录是 [`a_share_tushare_gross_margin_research_record.json`](a_share_tushare_gross_margin_research_record.json)。不要重请求该股票、丢弃或填补异常行、修改字段/切片/公式，或重跑验收和全量同步。

这两项结果说明的是固定研究合同已经消费或失败，不说明 Token 失效。下一项 Tushare 研究必须先完成一份新的、无收益的经济机制重叠审计，并在任何供应商请求之前冻结独立的数据合同；本文的凭据配置步骤本身不构成运行许可。

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
