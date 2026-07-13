#!/usr/bin/env python3
"""Install or remove macOS launchd schedules for A-share data and paper monitoring.

The local time zone of this workspace (Asia/Singapore) is the same as mainland
China time, so the default 18:30 weekday job runs after the A-share close.
Friday 20:00 performs a full refresh to keep qfq-adjusted history current.
An optional 19:30 weekday job records and settles the approved three-day
paper strategy after the normal close-data refresh has had time to complete.
"""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = REPO_ROOT / "scripts" / "a_share_data_pipeline.py"
SHORT_HORIZON_MONITOR = REPO_ROOT / "scripts" / "run_a_share_short_horizon_monitor.py"
DATA_DIR = REPO_ROOT / "data"
AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
DAILY_LABEL = "com.qlib.a-share-data.daily"
FULL_LABEL = "com.qlib.a-share-data.full"
MONITOR_LABEL = "com.qlib.a-share-short-horizon.monitor"


def _job(label: str, arguments: list[str], calendar: list[dict[str, int]]) -> dict:
    log_dir = DATA_DIR / "logs"
    return {
        "Label": label,
        "ProgramArguments": arguments,
        "WorkingDirectory": str(REPO_ROOT),
        "StartCalendarInterval": calendar,
        "ProcessType": "Background",
        "StandardOutPath": str(log_dir / f"{label}.out.log"),
        "StandardErrorPath": str(log_dir / f"{label}.err.log"),
    }


def _calendar(weekdays: list[int], hour: int, minute: int) -> list[dict[str, int]]:
    # launchd: Sunday=1, Monday=2, ..., Friday=6, Saturday=7.
    return [{"Weekday": weekday, "Hour": hour, "Minute": minute} for weekday in weekdays]


def _paths() -> dict[str, Path]:
    return {
        DAILY_LABEL: AGENTS_DIR / f"{DAILY_LABEL}.plist",
        FULL_LABEL: AGENTS_DIR / f"{FULL_LABEL}.plist",
        MONITOR_LABEL: AGENTS_DIR / f"{MONITOR_LABEL}.plist",
    }


def _jobs(with_short_horizon_monitor: bool) -> dict[str, dict]:
    """Build launchd payloads without mutating a user's LaunchAgents directory."""

    common = [sys.executable, str(PIPELINE), "sync", "--scope", "factor"]
    jobs = {
        DAILY_LABEL: _job(DAILY_LABEL, common, _calendar([2, 3, 4, 5, 6], 18, 30)),
        # The full weekly refresh re-requests qfq history.  This corrects prior
        # adjusted prices after ex-rights/ex-dividend events.
        FULL_LABEL: _job(FULL_LABEL, [*common, "--force-full"], _calendar([6], 20, 0)),
    }
    if with_short_horizon_monitor:
        jobs[MONITOR_LABEL] = _job(
            MONITOR_LABEL,
            [sys.executable, str(SHORT_HORIZON_MONITOR)],
            _calendar([2, 3, 4, 5, 6], 19, 30),
        )
    return jobs


def _bootout(path: Path) -> None:
    subprocess.run(
        ["launchctl", "bootout", f"gui/{os.getuid()}", str(path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def install(args: argparse.Namespace) -> int:
    if sys.platform != "darwin":
        raise RuntimeError("launchd scheduling is only available on macOS")
    (DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = _paths()
    jobs = _jobs(args.with_short_horizon_monitor)
    for label, payload in jobs.items():
        path = paths[label]
        _bootout(path)
        with path.open("wb") as handle:
            plistlib.dump(payload, handle, sort_keys=False)
        subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)], check=True)
        print(f"installed {label}: {path}")
    return 0


def uninstall(_: argparse.Namespace) -> int:
    for label, path in _paths().items():
        _bootout(path)
        if path.exists():
            path.unlink()
        print(f"removed {label}: {path}")
    return 0


def status(_: argparse.Namespace) -> int:
    for label, path in _paths().items():
        result = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{label}"], capture_output=True, text=True, check=False)
        print(f"{label}: {'loaded' if result.returncode == 0 else 'not loaded'} ({path})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, func, help_text in (
        ("install", install, "install weekday + weekly refresh schedules"),
        ("uninstall", uninstall, "remove data and short-horizon monitor schedules"),
        ("status", status, "show whether data and short-horizon monitor schedules are loaded"),
    ):
        command = commands.add_parser(name, help=help_text)
        if name == "install":
            command.add_argument(
                "--with-short-horizon-monitor",
                action="store_true",
                help="also install a weekday 19:30 three-day paper monitor",
            )
        command.set_defaults(func=func)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
