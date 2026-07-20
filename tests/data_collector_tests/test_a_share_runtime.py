"""Offline tests for shared A-share runtime configuration."""

import datetime as dt
import importlib.util
import sys
from pathlib import Path

RUNTIME_PATH = Path(__file__).resolve().parents[2] / "scripts" / "_a_share_runtime.py"
SPEC = importlib.util.spec_from_file_location(
    "_a_share_runtime_under_test", RUNTIME_PATH
)
RUNTIME = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


def test_resolve_data_root_defaults_to_repository_data(tmp_path):
    assert RUNTIME.resolve_data_root(tmp_path, {}) == (tmp_path / "data").resolve()


def test_resolve_data_root_supports_absolute_and_repository_relative_paths(tmp_path):
    external = tmp_path / "external data"
    assert (
        RUNTIME.resolve_data_root(tmp_path, {RUNTIME.DATA_ROOT_ENV: str(external)})
        == external.resolve()
    )
    assert (
        RUNTIME.resolve_data_root(tmp_path, {RUNTIME.DATA_ROOT_ENV: "var/a-share"})
        == (tmp_path / "var" / "a-share").resolve()
    )


def test_count_and_latest_path_streams_without_sorting(tmp_path):
    paths = [
        tmp_path / name for name in ("20260101.json", "20260301.json", "20260201.json")
    ]
    consumed = []

    def stream():
        for path in paths:
            consumed.append(path)
            yield path

    count, latest = RUNTIME.count_and_latest_path(stream())
    assert consumed == paths
    assert count == 3
    assert latest == paths[1]


def test_latest_completed_session_date_uses_china_standard_time():
    before_close = dt.datetime(2026, 7, 13, 7, 29, tzinfo=dt.timezone.utc)
    at_close = dt.datetime(2026, 7, 13, 7, 30, tzinfo=dt.timezone.utc)
    assert (
        RUNTIME.latest_completed_session_date(before_close).isoformat() == "2026-07-10"
    )
    assert RUNTIME.latest_completed_session_date(at_close).isoformat() == "2026-07-13"
