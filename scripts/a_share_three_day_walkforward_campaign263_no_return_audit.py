#!/usr/bin/env python3
"""Run Campaign263's frozen coverage-first no-return audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_AUDIT = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign262_no_return_audit.py"
)
BASE_AUDIT_SHA256 = "6087212a13b0b77b0583835c38d11f00758efe99c64bca5e7777094d73ce9c60"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_AUDIT) != BASE_AUDIT_SHA256:
    raise RuntimeError("frozen Campaign262 coverage-first audit changed")


_source = BASE_AUDIT.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign262", "Campaign263"),
    ("campaign262", "campaign263"),
    ("campaign_262", "campaign_263"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign263_no_return_audit_generated",
}
exec(compile(_source, str(BASE_AUDIT), "exec"), _generated)  # noqa: S102


def _campaign263_load_protocol() -> dict[str, Any]:
    spec = _generated["candidate"].load_protocol()
    gates = list(spec.get("ordered_no_return_gates") or [])
    if [item.get("gate") for item in gates] != [1, 2, 3]:
        raise _generated["Campaign263NoReturnAuditError"](
            "Campaign263 gate order changed"
        )
    comparison = spec.get("comparison_contract") or {}
    if not (
        comparison.get("numeric_comparator_count") == 142
        and comparison.get("numeric_comparator_order_sha256")
        == _generated["candidate"].NUMERIC_COMPARATOR_ORDER_SHA256
    ):
        raise _generated["Campaign263NoReturnAuditError"](
            "Campaign263 comparison contract changed"
        )
    return spec


_generated["load_protocol"] = _campaign263_load_protocol

Campaign263NoReturnAuditError = _generated["Campaign263NoReturnAuditError"]
FACTOR_NAME = _generated["FACTOR_NAME"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
SNAPSHOT_MANIFEST_PATH = _generated["SNAPSHOT_MANIFEST_PATH"]
ACTIVATION_BINDING_PATH = _generated["ACTIVATION_BINDING_PATH"]
OUTPUT_PATH = _generated["OUTPUT_PATH"]
CANDIDATE49_SIGNAL_LEDGER = _generated["CANDIDATE49_SIGNAL_LEDGER"]
CANDIDATE49_SIGNAL_LEDGER_SHA256 = _generated[
    "CANDIDATE49_SIGNAL_LEDGER_SHA256"
]
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
