#!/usr/bin/env python3
"""Run the three-day paper monitor and refresh its human-readable report.

This deliberately runs only observation and reporting.  It does not search
new factor combinations, change the approved candidate, or place trades.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _a_share_runtime import resolve_data_root
from _interprocess_lock import InterProcessFileLock, file_lock_is_held

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = resolve_data_root(REPO_ROOT)
RESEARCH = REPO_ROOT / "scripts" / "a_share_short_horizon_factor_research.py"
PIPELINE_LOCK = DATA_ROOT / ".a_share_pipeline.lock"
PROSPECTIVE_FACTOR_REGISTRY = (
    DATA_ROOT / "experiments" / "short_horizon" / "prospective_factor_registry.json"
)
STRATEGY_REGISTRY = (
    DATA_ROOT / "experiments" / "short_horizon" / "strategy_registry.json"
)
SHADOW_OBSERVATION_REGISTRY = (
    DATA_ROOT / "experiments" / "short_horizon" / "shadow_observation_registry.json"
)
FORWARD_NOT_BEFORE = "2026-07-14"
REQUIRED_PRICE_BASIS = "close_known_raw_pct_chg_chain_v1"


def pipeline_is_busy(lock_path: Path = PIPELINE_LOCK) -> bool:
    """Return whether the data pipeline currently holds its advisory lock."""

    return file_lock_is_held(lock_path)


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


def _records(path: Path, key: str) -> list[dict]:
    """Read one append-only registry without treating file existence as validity."""

    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get(key) or []
    return list(records) if isinstance(records, list) else []


def _accepted(record: dict) -> bool:
    return (record.get("data") or {}).get("price_basis") == REQUIRED_PRICE_BASIS


def observation_commands(
    prospective_registry: Path = PROSPECTIVE_FACTOR_REGISTRY,
    strategy_registry: Path = STRATEGY_REGISTRY,
    shadow_registry: Path = SHADOW_OBSERVATION_REGISTRY,
) -> list[list[str]]:
    """Run only observations backed by the accepted point-in-time price basis."""

    iterations = _records(strategy_registry, "iterations")
    valid_iteration_ids = {
        str(item.get("iteration_id")) for item in iterations if _accepted(item)
    }
    commands: list[list[str]] = []
    if any(
        str(item.get("iteration_id")) in valid_iteration_ids
        and (item.get("promotion") or {}).get("status") == "passed_initial_test"
        for item in iterations
    ):
        commands.append(["monitor", "--not-before", FORWARD_NOT_BEFORE])
    observations = _records(shadow_registry, "observations")
    if any(str(item.get("iteration_id")) in valid_iteration_ids for item in observations):
        commands.append(["shadow-monitor"])
    if any(_accepted(item) for item in _records(prospective_registry, "registrations")):
        commands.append(["prospective-monitor"])
    commands.append(["report"])
    return commands


def main() -> int:
    if not wait_for_pipeline_idle():
        raise RuntimeError("A-share data refresh did not finish within 45 minutes; paper observation was skipped")
    for command in observation_commands():
        subprocess.run([sys.executable, str(RESEARCH), *command], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
