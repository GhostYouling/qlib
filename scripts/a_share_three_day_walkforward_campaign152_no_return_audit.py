#!/usr/bin/env python3
"""Run Campaign152's frozen coverage-first no-return audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_AUDIT = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign117_no_return_audit.py"
)
BASE_AUDIT_SHA256 = "8ea3a1b2e0cc369ea6a1192304af101b54fecdfebc5334fa199dbe53807331a5"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_AUDIT) != BASE_AUDIT_SHA256:
    raise RuntimeError("frozen Campaign117 coverage-first audit changed")


_source = BASE_AUDIT.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign117", "Campaign152"),
    ("campaign117", "campaign152"),
    ("campaign_117", "campaign_152"),
    ("20260813", "20260815"),
    ("all_134", "all_142"),
    ("all-134", "all-142"),
    ("all 134", "all 142"),
    ('numeric_comparator_count") == 134', 'numeric_comparator_count") == 142'),
):
    _source = _source.replace(_old, _new)
_source = _source.replace("or (finite_values > 1.0).any()", "")
_source = _source.replace("or (finite > 1.0).any()", "")
_source = _source.replace("(finite_values < 0.0).any()", "(finite_values <= 0.0).any()")
_source = _source.replace("(finite < 0.0).any()", "(finite <= 0.0).any()")

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign152_no_return_audit_generated",
}
exec(compile(_source, str(BASE_AUDIT), "exec"), _generated)

Campaign152NoReturnAuditError = _generated["Campaign152NoReturnAuditError"]
_base_validate_static_bindings = _generated["validate_static_bindings"]
_coverage_test_path = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign152_no_return_audit.py"
)


def _validate_static_bindings_with_runner() -> dict[str, Any]:
    static = _base_validate_static_bindings()
    activation_path = _generated["ACTIVATION_BINDING_PATH"]
    activation = _generated["_load_json"](activation_path)
    runner = activation.get("coverage_runner") or {}
    if not (
        runner.get("path")
        == "scripts/a_share_three_day_walkforward_campaign152_no_return_audit.py"
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and runner.get("test_path")
        == "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign152_no_return_audit.py"
        and runner.get("test_sha256") == _sha256(_coverage_test_path)
        and runner.get("synthetic_test_exit_code") == 0
        and runner.get("synthetic_tests_passed") == 5
    ):
        raise Campaign152NoReturnAuditError(
            "Campaign152 coverage runner binding changed"
        )
    static["coverage_runner_sha256"] = runner["sha256"]
    static["coverage_runner_test_sha256"] = runner["test_sha256"]
    return static


_generated["validate_static_bindings"] = _validate_static_bindings_with_runner

FACTOR_NAME = _generated["FACTOR_NAME"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
SNAPSHOT_MANIFEST_PATH = _generated["SNAPSHOT_MANIFEST_PATH"]
ACTIVATION_BINDING_PATH = _generated["ACTIVATION_BINDING_PATH"]
OUTPUT_PATH = _generated["OUTPUT_PATH"]
CANDIDATE49_SIGNAL_LEDGER = _generated["CANDIDATE49_SIGNAL_LEDGER"]
CANDIDATE49_SIGNAL_LEDGER_SHA256 = _generated["CANDIDATE49_SIGNAL_LEDGER_SHA256"]
CANDIDATE49_EXECUTION_LEDGER = _generated["CANDIDATE49_EXECUTION_LEDGER"]
CANDIDATE49_EXECUTION_LEDGER_SHA256 = _generated["CANDIDATE49_EXECUTION_LEDGER_SHA256"]
MINIMUM_MEDIAN_COVERAGE = _generated["MINIMUM_MEDIAN_COVERAGE"]
MINIMUM_P05_COVERAGE = _generated["MINIMUM_P05_COVERAGE"]
MINIMUM_P05_ELIGIBLE_NAMES = _generated["MINIMUM_P05_ELIGIBLE_NAMES"]
MINIMUM_NON_OVERLAPPING_COHORTS = _generated["MINIMUM_NON_OVERLAPPING_COHORTS"]
MINIMUM_OBSERVED_COHORT_YEARS = _generated["MINIMUM_OBSERVED_COHORT_YEARS"]
MINIMUM_NONCONSTANT_CROSS_SECTIONAL_SESSIONS = _generated[
    "MINIMUM_NONCONSTANT_CROSS_SECTIONAL_SESSIONS"
]
HOLDING_PERIOD_SESSIONS = _generated["HOLDING_PERIOD_SESSIONS"]
candidate = _generated["candidate"]
expected_gate = _generated["expected_gate"]
load_protocol = _generated["load_protocol"]
validate_static_bindings = _validate_static_bindings_with_runner
build_plan = _generated["build_plan"]
coverage_and_variation = _generated["coverage_and_variation"]
run_coverage_audit = _generated["run_coverage_audit"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
