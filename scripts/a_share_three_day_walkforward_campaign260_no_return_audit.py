#!/usr/bin/env python3
"""Run Campaign260's frozen coverage-first no-return audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_AUDIT = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign117_no_return_audit.py"
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
    ("Campaign117", "Campaign260"),
    ("campaign117", "campaign260"),
    ("campaign_117", "campaign_260"),
    ("20260813", "20260816"),
    ("all_134", "all_142"),
    ("all-134", "all-142"),
    ("all 134", "all 142"),
    ('numeric_comparator_count") == 134', 'numeric_comparator_count") == 142'),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign260_no_return_audit_generated",
}
exec(compile(_source, str(BASE_AUDIT), "exec"), _generated)  # noqa: S102

Campaign260NoReturnAuditError = _generated["Campaign260NoReturnAuditError"]
FACTOR_NAME = _generated["FACTOR_NAME"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
SNAPSHOT_MANIFEST_PATH = _generated["SNAPSHOT_MANIFEST_PATH"]
ACTIVATION_BINDING_PATH = _generated["ACTIVATION_BINDING_PATH"]
OUTPUT_PATH = _generated["OUTPUT_PATH"]
CANDIDATE49_SIGNAL_LEDGER = _generated["CANDIDATE49_SIGNAL_LEDGER"]
CANDIDATE49_SIGNAL_LEDGER_SHA256 = _generated["CANDIDATE49_SIGNAL_LEDGER_SHA256"]
CANDIDATE49_EXECUTION_LEDGER = _generated["CANDIDATE49_EXECUTION_LEDGER"]
CANDIDATE49_EXECUTION_LEDGER_SHA256 = _generated[
    "CANDIDATE49_EXECUTION_LEDGER_SHA256"
]
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
validate_static_bindings = _generated["validate_static_bindings"]
build_plan = _generated["build_plan"]
coverage_and_variation = _generated["coverage_and_variation"]
run_coverage_audit = _generated["run_coverage_audit"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
