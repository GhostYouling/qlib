# Tushare Token 安全配置

本项目只从环境变量 `TUSHARE_TOKEN` 读取 Tushare 凭据。真实 Token 不得写入 Git、源码、YAML、Notebook、日志、研究清单、聊天或带明文参数的 shell 命令。

## 1. 安装本项目锁定的 SDK

在仓库根目录运行：

```zsh
python -m pip install -r scripts/data_collector/a_share_rich/requirements.txt
```

## 2. macOS 隐藏输入并注入环境

下面的 `read` 不回显输入；变量名必须是 `token`，这样后两行才能引用同一个临时变量：

```zsh
read -s "token?请粘贴 Tushare Token，随后按回车："; echo
export TUSHARE_TOKEN="$token"
launchctl setenv TUSHARE_TOKEN "$token"
unset token
```

- `export` 让当前终端及其后启动的子进程可用。
- `launchctl setenv` 让此后启动的 macOS 图形程序可继承。已经打开的 Codex 不会自动获得新值，需要彻底退出后重新打开。
- `unset token` 只清除临时 shell 变量，不会清除已经导出的 `TUSHARE_TOKEN`。
- `launchctl` 设置通常不跨注销或重启持久化；重启后需要重新执行隐藏输入。

不要把 Token 直接写成 `export TUSHARE_TOKEN=真实值` 或 `launchctl setenv TUSHARE_TOKEN 真实值`，否则可能进入命令历史、终端录屏或日志。也不要把它明文写进 `.zshrc`。

## 3. 只验证“有或无”

不要单独运行会把值打印到屏幕的 `launchctl getenv TUSHARE_TOKEN`。使用只输出状态的检查：

```zsh
test -n "${TUSHARE_TOKEN:-}" && echo "当前终端：已配置" || echo "当前终端：未配置"
test -n "$(launchctl getenv TUSHARE_TOKEN)" && echo "launchctl：已配置" || echo "launchctl：未配置"
python scripts/a_share_rich_data.py status
```

`a_share_rich_data.py status` 只报告环境变量和 SDK 是否就绪，不打印 Token，也不登录供应商。

## 4. 当前程序尚未继承时运行一次命令

如果 `launchctl` 已配置，但当前终端或当前 Codex 是在配置之前启动的，可以只在该子进程的环境中注入值：

```zsh
token="$(launchctl getenv TUSHARE_TOKEN)"
if [[ -z "$token" ]]; then
  echo "TUSHARE_TOKEN 未配置"
else
  TUSHARE_TOKEN="$token" python scripts/a_share_rich_data.py status
fi
unset token
```

这不会把 Token 作为命令参数传给 Python，也不会输出它。用于实际数据命令时，只替换最后一行中的 Python 子命令；仍须遵守对应数据合同与验收门禁，不能因为凭据可用就跳过单日验收或直接批量下载。

## 5. 清除配置

```zsh
unset TUSHARE_TOKEN
launchctl unsetenv TUSHARE_TOKEN
```

清除后重新运行第 3 节的状态检查。仓库内任何文件都不应包含真实 Token；如果曾误写或误提交，应立即在 Tushare 账户侧轮换 Token，再清理泄露位置，不能只删除最新一行提交记录。
