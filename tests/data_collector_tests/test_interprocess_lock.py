"""Cross-platform checks for the repository's advisory file lock."""

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _interprocess_lock import (  # noqa: E402
    InterProcessFileLock,
    LockUnavailableError,
    inspect_file_lock,
)


def test_lock_reports_owner_and_rejects_overlap(tmp_path):
    lock_path = tmp_path / "pipeline.lock"

    with InterProcessFileLock(lock_path, owner="test-owner"):
        snapshot = inspect_file_lock(lock_path)
        assert snapshot.exists is True
        assert snapshot.owner == "test-owner"
        assert snapshot.held is True
        with pytest.raises(LockUnavailableError):
            InterProcessFileLock(lock_path).acquire()

    snapshot = inspect_file_lock(lock_path)
    assert snapshot.exists is True
    assert snapshot.owner == "test-owner"
    assert snapshot.held is False


def test_inspection_does_not_create_or_rewrite_markers(tmp_path):
    missing = tmp_path / "missing.lock"
    snapshot = inspect_file_lock(missing)
    assert snapshot.exists is False
    assert not missing.exists()

    marker = tmp_path / "legacy.lock"
    marker.write_text("12345", encoding="utf-8")
    before = marker.read_bytes()
    snapshot = inspect_file_lock(marker)
    assert snapshot.owner == "12345"
    assert snapshot.held is False
    assert marker.read_bytes() == before
