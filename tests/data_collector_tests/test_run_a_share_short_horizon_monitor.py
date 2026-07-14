"""Offline checks for the paper-monitor schedule's data-refresh barrier."""

import fcntl
import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_a_share_short_horizon_monitor.py"
SPEC = importlib.util.spec_from_file_location("run_a_share_short_horizon_monitor", SCRIPT_PATH)
MONITOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MONITOR
SPEC.loader.exec_module(MONITOR)


def test_monitor_waits_for_the_pipeline_lock_before_reading_daily_data(tmp_path):
    lock_path = tmp_path / ".a_share_pipeline.lock"
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert MONITOR.pipeline_is_busy(lock_path)
        assert not MONITOR.wait_for_pipeline_idle(lock_path, timeout_seconds=0)
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    assert not MONITOR.pipeline_is_busy(lock_path)
    assert MONITOR.wait_for_pipeline_idle(lock_path, timeout_seconds=0)


def test_monitor_wait_configuration_rejects_invalid_values(tmp_path):
    with pytest.raises(ValueError, match="non-negative"):
        MONITOR.wait_for_pipeline_idle(tmp_path / "lock", timeout_seconds=-1)
    with pytest.raises(ValueError, match="poll_seconds"):
        MONITOR.wait_for_pipeline_idle(tmp_path / "lock", poll_seconds=0)


def test_monitor_uses_the_unseen_start_and_only_enables_registered_prospective_factors(tmp_path):
    prospective_registry = tmp_path / "prospective_registry.json"
    commands = MONITOR.observation_commands(prospective_registry)
    assert commands[0] == ["monitor", "--not-before", "2026-07-14"]
    assert ["prospective-monitor"] not in commands
    prospective_registry.write_text("{}", encoding="utf-8")
    commands = MONITOR.observation_commands(prospective_registry)
    assert commands == [
        ["monitor", "--not-before", "2026-07-14"],
        ["shadow-monitor"],
        ["prospective-monitor"],
        ["report"],
    ]
