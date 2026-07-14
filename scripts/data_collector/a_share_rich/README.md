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

Credentials belong in the local shell environment only:

```bash
export TUSHARE_TOKEN='...'
export JQDATA_USERNAME='...'
export JQDATA_PASSWORD='...'
export RQDATA_USERNAME='...'
export RQDATA_PASSWORD='...'
```

Do not put these values into a `.env` file in the repository, command-line
arguments, notebooks, logs, or git history.

Run `python scripts/a_share_rich_data.py status` before any download.  Start
with the `acceptance` command for one completed trading session; it stores raw
unadjusted bars and a checksum manifest under `data/` (which is Git-ignored).
