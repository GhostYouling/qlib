"""Shared runtime configuration for the repository's A-share scripts."""

from __future__ import annotations

import datetime as dt
import os
from collections.abc import Iterable, Mapping
from pathlib import Path

DATA_ROOT_ENV = "QLIB_A_SHARE_DATA_ROOT"
CHINA_STANDARD_TIME = dt.timezone(dt.timedelta(hours=8), name="Asia/Shanghai")


def resolve_data_root(
    repository_root: Path,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the portable A-share data root.

    An absolute environment value is used as-is. A relative value is anchored
    to the repository rather than the process working directory so scheduled
    jobs behave consistently. The historical ``<repository>/data`` location
    remains the default.
    """

    environment = os.environ if environ is None else environ
    configured = environment.get(DATA_ROOT_ENV, "").strip()
    candidate = Path(configured).expanduser() if configured else Path("data")
    if not candidate.is_absolute():
        candidate = repository_root / candidate
    return candidate.resolve()


def count_and_latest_path(paths: Iterable[Path]) -> tuple[int, Path | None]:
    """Count a path stream and retain its lexically latest entry in one pass."""

    count = 0
    latest: Path | None = None
    latest_key = ""
    for path in paths:
        count += 1
        path_key = path.as_posix()
        if latest is None or path_key > latest_key:
            latest = path
            latest_key = path_key
    return count, latest


def latest_completed_session_date(now: dt.datetime | None = None) -> dt.date:
    """Return a conservative A-share daily-data cutoff in UTC+8.

    A timezone-aware value is converted to China Standard Time; a naive value
    is interpreted as already being in UTC+8 for backward compatibility. The
    helper only knows weekends. Exchange holidays naturally produce no rows
    and remain visible in the caller's run manifest.
    """

    if now is None:
        local_now = dt.datetime.now(CHINA_STANDARD_TIME)
    elif now.tzinfo is None:
        local_now = now
    else:
        local_now = now.astimezone(CHINA_STANDARD_TIME)
    cutoff = local_now.date()
    if local_now.weekday() < 5 and local_now.time() < dt.time(15, 30):
        cutoff -= dt.timedelta(days=1)
    while cutoff.weekday() >= 5:
        cutoff -= dt.timedelta(days=1)
    return cutoff
