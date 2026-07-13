#!/usr/bin/env python3
"""Run the three-day paper monitor and refresh its human-readable report.

This deliberately runs only observation and reporting.  It does not search
new factor combinations, change the approved candidate, or place trades.
"""

from __future__ import annotations

import fcntl
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESEARCH = REPO_ROOT / "scripts" / "a_share_short_horizon_factor_research.py"
PIPELINE_LOCK = REPO_ROOT / "data" / ".a_share_pipeline.lock"


def pipeline_is_busy(lock_path: Path = PIPELINE_LOCK) -> bool:
    """Return whether the data pipeline currently holds its advisory lock."""

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return False


def wait_for_pipeline_idle(
    lock_path: Path = PIPELINE_LOCK,
    *,
    timeout_seconds: float = 45 * 60,
    poll_seconds: float = 30,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> bool:
    """Wait a bounded time for the preceding scheduled data refresh to finish."""

    if timeout_seconds < 0 or poll_seconds <= 0:
        raise ValueError("timeout_seconds must be non-negative and poll_seconds must be positive")
    deadline = monotonic() + timeout_seconds
    while pipeline_is_busy(lock_path):
        remaining = deadline - monotonic()
        if remaining <= 0:
            return False
        delay = min(poll_seconds, remaining)
        print(f"A-share data refresh still holds {lock_path}; waiting {delay:.0f}s before paper observation")
        sleep(delay)
    return True


def main() -> int:
    if not wait_for_pipeline_idle():
        raise RuntimeError("A-share data refresh did not finish within 45 minutes; paper observation was skipped")
    for command in ("monitor", "shadow-monitor", "report"):
        subprocess.run([sys.executable, str(RESEARCH), command], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
