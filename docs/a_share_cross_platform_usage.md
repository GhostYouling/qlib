# A 股数据脚本的跨平台使用

`scripts/a_share_data_pipeline.py` 和 `scripts/a_share_rich_data.py` 使用同一份
代码支持 Windows、macOS 与 Linux。不要复制或维护单独的 `*_windows.py`：进程锁、
锁状态检查、路径和中国标准时间截止点都已经由公共实现处理。

## 最小环境

建议在仓库根目录创建虚拟环境。Windows PowerShell：

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install pandas numpy pyarrow requests
```

macOS/Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pandas numpy pyarrow requests
```

只有实际使用某个授权数据源时才安装其 SDK。BaoStock 无需凭据；Tushare、JQData
和 RQData 需要各自的合法账户与授权。可参考
`scripts/data_collector/a_share_rich/requirements.txt`，但不必为了运行日频管线安装全部
供应商 SDK。

## 数据目录

默认数据目录仍是仓库内的 `data`。如果数据盘、容器挂载点或 Windows 任务账户不同，
可通过 `QLIB_A_SHARE_DATA_ROOT` 同时配置日频和富数据脚本，无需复制代码或创建链接。

Windows PowerShell：

```powershell
$env:QLIB_A_SHARE_DATA_ROOT = 'D:\MarketData\qlib-a-share'
python scripts/a_share_data_pipeline.py status
python scripts/a_share_rich_data.py status
```

Windows CMD：

```batch
set QLIB_A_SHARE_DATA_ROOT=D:\MarketData\qlib-a-share
python scripts\a_share_data_pipeline.py status
```

macOS/Linux：

```bash
export QLIB_A_SHARE_DATA_ROOT=/mnt/market-data/qlib-a-share
python scripts/a_share_data_pipeline.py status
```

相对路径会相对于仓库根目录解析，而不是相对于当前工作目录；这能避免 `cron`、
`launchd` 和 Windows 任务计划程序从不同目录启动时写入意外位置。

## 验证

以下命令不会下载行情，可用于确认解释器、依赖、路径和锁实现正常：

```powershell
python scripts/a_share_data_pipeline.py --help
python scripts/a_share_data_pipeline.py status
python scripts/a_share_rich_data.py --help
python scripts/a_share_rich_data.py status
```

日频数据下载和本地物化在各平台使用相同命令：

```powershell
python scripts/a_share_data_pipeline.py sync --symbols 600519,300750 --start 2020-01-01
python scripts/a_share_data_pipeline.py price-basis-audit
python scripts/a_share_data_pipeline.py materialize
```

## Windows 凭据

不要把 token 写进命令、脚本、`.env` 或任务计划参数。可在当前 PowerShell 进程中
通过隐藏输入临时注入：

```powershell
$secret = Read-Host "Tushare token" -AsSecureString
$env:TUSHARE_TOKEN = [PSCredential]::new("token", $secret).GetNetworkCredential().Password
Remove-Variable secret
python scripts/a_share_rich_data.py status
```

用完后清除：

```powershell
Remove-Item Env:TUSHARE_TOKEN
```

JQData 和 RQData 使用相同原则，只设置脚本状态输出中列出的环境变量。

## 定时运行

Windows 任务计划程序应配置为：

- “程序”：虚拟环境中的 `python.exe`；
- “参数”：例如 `scripts\a_share_data_pipeline.py sync`；
- “起始于”：仓库根目录；
- 禁止同一任务并行启动。

脚本本身还会持有跨进程文件锁，因此 Windows 任务计划、macOS `launchd` 和 Linux
`cron` 的重叠运行都会安全失败。锁文件会保留最近一次 PID/启动信息；文件存在不等于
进程仍在运行，应通过 `status` 返回的 `advisory_lock_currently_held` 判断。

## 跨平台一致性

- 默认完成交易日按 UTC+8 中国标准时间计算，不依赖宿主机时区。
- JSON、YAML、Markdown、文本日历等冻结文件在计算 SHA-256 前统一为 LF 换行，
  避免 Git 的 Windows CRLF checkout 造成误报。
- Parquet 等二进制文件仍按原始字节计算 SHA-256，不会放宽数据完整性校验。
- 路径均通过 `pathlib.Path` 解析；manifest 中仍优先保存仓库相对路径，便于跨机器迁移。
