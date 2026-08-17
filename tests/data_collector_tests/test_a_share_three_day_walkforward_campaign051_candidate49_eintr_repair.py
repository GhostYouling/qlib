"""Focused tests for Campaign051's exact Candidate49 EINTR repair."""

from __future__ import annotations

import subprocess
import sys
import textwrap


def _run(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_campaign051_candidate49_eintr_retries_exact_request_once() -> None:
    code = r"""
import errno
import numpy as np
import scripts.a_share_three_day_walkforward_campaign051_features_v6 as repair

calls = []
def fake_loader(manifest, factors, keys):
    calls.append((manifest, factors, keys.copy()))
    if len(calls) == 1:
        raise InterruptedError(errno.EINTR, "interrupted")
    return {repair.EXPECTED_C49_FACTOR: np.array([0.25])}

repair.ORIGINAL_EXPLICIT_LOADER = fake_loader
manifest = {
    "kind": repair.EXPECTED_C49_KIND,
    "dataset_sha256": repair.EXPECTED_C49_DATASET_SHA256,
    "factor_name": repair.EXPECTED_C49_FACTOR,
    "partitions": repair.EXPECTED_C49_PARTITIONS,
    "rows": repair.EXPECTED_C49_ROWS,
    "files": [{}] * repair.EXPECTED_C49_PARTITIONS,
}
result = repair.load_filtered_comparison_values_with_candidate49_eintr_retry(
    manifest, [repair.EXPECTED_C49_FACTOR], np.array([1], dtype=np.int64)
)
assert len(calls) == 2
assert result[repair.EXPECTED_C49_FACTOR].tolist() == [0.25]
assert repair.engine._load_filtered_comparison_values_explicit is repair.load_filtered_comparison_values_with_candidate49_eintr_retry
assert repair.runner.COMPARISON_COUNT == 74
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr


def test_campaign051_candidate49_eintr_does_not_retry_other_request() -> None:
    code = r"""
import errno
import numpy as np
import scripts.a_share_three_day_walkforward_campaign051_features_v6 as repair

calls = []
def fake_loader(manifest, factors, keys):
    calls.append(1)
    raise InterruptedError(errno.EINTR, "interrupted")

repair.ORIGINAL_EXPLICIT_LOADER = fake_loader
manifest = {
    "kind": "another_snapshot",
    "dataset_sha256": repair.EXPECTED_C49_DATASET_SHA256,
    "factor_name": repair.EXPECTED_C49_FACTOR,
    "partitions": repair.EXPECTED_C49_PARTITIONS,
    "rows": repair.EXPECTED_C49_ROWS,
    "files": [{}] * repair.EXPECTED_C49_PARTITIONS,
}
try:
    repair.load_filtered_comparison_values_with_candidate49_eintr_retry(
        manifest, [repair.EXPECTED_C49_FACTOR], np.array([1], dtype=np.int64)
    )
except InterruptedError as exc:
    assert exc.errno == errno.EINTR
else:
    raise AssertionError("non-Candidate49 EINTR must propagate")
assert len(calls) == 1
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr


def test_campaign051_candidate49_second_eintr_propagates() -> None:
    code = r"""
import errno
import numpy as np
import scripts.a_share_three_day_walkforward_campaign051_features_v6 as repair

calls = []
def fake_loader(manifest, factors, keys):
    calls.append(1)
    raise InterruptedError(errno.EINTR, "interrupted")

repair.ORIGINAL_EXPLICIT_LOADER = fake_loader
manifest = {
    "kind": repair.EXPECTED_C49_KIND,
    "dataset_sha256": repair.EXPECTED_C49_DATASET_SHA256,
    "factor_name": repair.EXPECTED_C49_FACTOR,
    "partitions": repair.EXPECTED_C49_PARTITIONS,
    "rows": repair.EXPECTED_C49_ROWS,
    "files": [{}] * repair.EXPECTED_C49_PARTITIONS,
}
try:
    repair.load_filtered_comparison_values_with_candidate49_eintr_retry(
        manifest, [repair.EXPECTED_C49_FACTOR], np.array([1], dtype=np.int64)
    )
except InterruptedError as exc:
    assert exc.errno == errno.EINTR
else:
    raise AssertionError("second EINTR must propagate")
assert len(calls) == 2
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr
