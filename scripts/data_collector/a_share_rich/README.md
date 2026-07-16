# A 股分钟线与事件数据接入

This directory contains the optional SDK dependencies for
`scripts/a_share_rich_data.py`.  It is intentionally separate from the core
Qlib dependencies: Tushare, JQData, and RQData require a licensed account and
must not be installed as an implicit side effect of the public daily-data
pipeline.

Install the SDKs after obtaining the providers' permission:

```bash
python -m pip install -r scripts/data_collector/a_share_rich/requirements.txt
```

Credentials belong in the local process environment only.  On macOS with
zsh, enter the Tushare token through a hidden prompt so the value never appears
in shell history:

```zsh
read -s "token?Paste the Tushare token, then press Enter: "; echo
export TUSHARE_TOKEN="$token"
launchctl setenv TUSHARE_TOKEN "$token"
unset token
```

The `export` makes the token available to commands in the current shell;
`launchctl setenv` makes it available to GUI applications started afterward.
Fully quit and reopen Codex after setting it.  Verify without printing the
secret:

```zsh
test -n "$(launchctl getenv TUSHARE_TOKEN)" && echo "configured" || echo "missing"
python scripts/a_share_rich_data.py status
```

`launchctl` does not persist this value across logout or reboot; rerun the
hidden-input commands when needed.  Remove it with `unset TUSHARE_TOKEN` in the
current shell and `launchctl unsetenv TUSHARE_TOKEN` for subsequently launched
applications.  Never paste a real credential into chat or put it in a `.env`
file in the repository, a command literal, notebook, log, or git history.  Use
the same hidden-input/environment pattern for JQData or RQData credentials only
after obtaining those providers' authorization.

Run `python scripts/a_share_rich_data.py status` before any download.  Start
with the `acceptance` command for one completed trading session; it stores raw
unadjusted bars and a checksum manifest under `data/` (which is Git-ignored).

For a 3000-point Tushare account, the event acceptance command defaults to
`moneyflow,limit-price,stock-st,top-list`, mapped to the provider's
`moneyflow`, `stk_limit`, `stock_st`, and `top_list` APIs.  The optional
`limit-list` dataset maps to `limit_list_d` and requires 5000 points, so it is
never requested implicitly.  Event downloads publish atomically only after
every requested table succeeds.  Raw duplicates are preserved and counted in
the manifest; downstream code must freeze a canonicalization rule before
using those rows as factors.
