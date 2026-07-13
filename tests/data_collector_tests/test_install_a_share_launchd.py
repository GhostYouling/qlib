"""Offline checks for the optional three-day paper-monitor launchd job."""

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "install_a_share_launchd.py"
SPEC = importlib.util.spec_from_file_location("install_a_share_launchd", SCRIPT_PATH)
INSTALLER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = INSTALLER
SPEC.loader.exec_module(INSTALLER)


def test_optional_monitor_job_runs_after_the_close_data_refresh():
    default_jobs = INSTALLER._jobs(with_short_horizon_monitor=False)
    assert INSTALLER.MONITOR_LABEL not in default_jobs

    jobs = INSTALLER._jobs(with_short_horizon_monitor=True)
    monitor = jobs[INSTALLER.MONITOR_LABEL]
    assert monitor["ProgramArguments"][-1] == str(INSTALLER.SHORT_HORIZON_MONITOR)
    assert monitor["StartCalendarInterval"] == [
        {"Weekday": weekday, "Hour": 19, "Minute": 30} for weekday in [2, 3, 4, 5, 6]
    ]
