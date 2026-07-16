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

The accepted 2026-07-13 event probe is also the bound entitlement/schema
evidence for one classified-flow research mechanism.  Its immutable contracts
are `docs/a_share_tushare_moneyflow_data_contract.json` and
`docs/a_share_tushare_moneyflow_capacity_preregistration.json`.  Tushare is the
authorized provider substitute for the still-unobserved JQData version of the
same large-order mechanism; never count or combine the two as independent
factors.  The canonical snapshot requests only the stock/date keys and eight
buy/sell amount fields.  It deliberately excludes Tushare's `net_mf_amount`,
all volume, price, market-cap, and return fields.

Run the fixed full-history request only after reviewing the contracts and the
accepted event manifest.  It makes one sequential call per local trading
session, enforces the frozen throttle/retry policy, writes 2019–2025 annual
partitions below one hidden temporary root, and publishes only after every
partition succeeds:

```bash
TUSHARE_TOKEN="$(launchctl getenv TUSHARE_TOKEN)" \
  python scripts/a_share_rich_data.py sync-tushare-moneyflow --allow-large
```

Do not put the token literal in this command.  The full manifest is usable by
the next gate only when its status is
`full_source_coverage_passed_pending_no_return_capacity`.  Then run exactly:

```bash
python scripts/a_share_short_horizon_factor_research.py \
  tushare-moneyflow-capacity-audit \
  --manifest data/metadata/rich_data/runs/<full-run>.json
```

The capacity audit reads no open, close, price, score, or forward-return
field.  A pass only permits a new fingerprint-bound diagnostic
preregistration; it does not permit aggregation, current scoring, selection,
position sizing, or orders.

Current local research status: the immutable full snapshot
`20260716T085610Z_tushare_moneyflow_daily_6c78e93d` contains 7,723,857
canonical 2019–2025 rows and passed the source gate.  Its one no-return
capacity audit passed with 540/200 cohorts across seven years.  The separately
frozen one-time return diagnostic and both default audits then qualified 0/1
factors: mean Rank IC was negative, six of seven annual mean ICs were
negative, the execution-aware ledger lost 89.23%, and the CNY 200,000 pilot
ledger lost 29.16%.  The terminal record is
`docs/a_share_tushare_moneyflow_research_record.json`.  Do not rerun, invert,
re-window, subset years, combine with the JQData substitute, score, select, or
size this historical factor.  The commands above document the accepted
pipeline and recovery order; they are not authorization to create another
historical trial from the same mechanism.
