#!/usr/bin/env python3
"""Run Campaign094's frozen coverage-first no-return uniqueness audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign094_features_v4 as definitions

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign093_no_return_audit.py"
)
BASE_RUNNER_SHA256 = "32d39c20f2eb29a699f2ac0018cecd132dddcf7b408541eb66fb3648e54c063f"
FACTOR_NAME = "intraday_range_local_peak_clock_dispersion_236p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign093 no-return runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign093", "Campaign094"),
    ("campaign093", "campaign094"),
    ("campaign_093", "campaign_094"),
    ("intraday_close_transition_range_quadratic_efficiency_238p", FACTOR_NAME),
    (
        "a_share_three_day_walkforward_campaign093_features_v2 as definitions",
        "a_share_three_day_walkforward_campaign094_features_v4 as definitions",
    ),
    (
        "a_share_three_day_walkforward_campaign092_no_return_audit as c88_audit",
        "a_share_three_day_walkforward_campaign093_no_return_audit as c88_audit",
    ),
    (
        "69428173fd9a84f7272b56e253b589cb712355ce0b59a05e2a0b0b9576b82e92",
        "1f1441e59bcef1cb3d18b0030c640453e2ee762668d05157dec9ca1c0f01c340",
    ),
    (
        "bba3e4e71626b0ff2fa3860649da5187ef5c5412879b009f6890e9599ba3cf0b",
        "37865a7d4c5556ee9a79ba9550f0f05229e3c52bb511d8bd1ac3b1f2525a6b63",
    ),
    (
        "8f58573bfc2c1e46bc31da2673d17d70c2aa470b112a898ac3ee1868facab233",
        "dc5778ad0788ed3bd0cc3fc8980110c5f741be29068f3eccad03144eccadf358",
    ),
    ("EXPECTED_ELIGIBLE_ROWS = 1_328_155", "EXPECTED_ELIGIBLE_ROWS = 1_314_834"),
    ("EXPECTED_COMPARISON_COUNT = 122", "EXPECTED_COMPARISON_COUNT = 123"),
    (
        "EXPECTED_COMPLETE_DEFINITION_COUNT = 124",
        "EXPECTED_COMPLETE_DEFINITION_COUNT = 125",
    ),
    ("len(comparisons) != 121", "len(comparisons) != 122"),
    ("first 121 comparison order changed", "first 122 comparison order changed"),
    (
        'receipts["campaign092_compact_snapshot"]',
        'receipts["campaign093_compact_snapshot"]',
    ),
    (
        'receipts.pop("all_121_sources_loaded_in_frozen_order", None)',
        'receipts.pop("all_122_sources_loaded_in_frozen_order", None)',
    ),
    (
        'receipts["all_122_sources_loaded_in_frozen_order"] = True',
        'receipts["all_123_sources_loaded_in_frozen_order"] = True',
    ),
    (
        "c88_audit.c88_audit.c88_audit.c88_audit.c88_audit.c87_audit._compact_snapshot_comparison",
        "c88_audit.c88_audit.c88_audit.c88_audit.c88_audit.c88_audit.c87_audit._compact_snapshot_comparison",
    ),
):
    _source = _source.replace(_old, _new)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign094_no_return_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _namespace)  # noqa: S102

_generated = _namespace["_generated"]
_generated["definitions"] = definitions
_generated["EXPECTED_ELIGIBLE_ROWS"] = 1_314_834

Campaign094NoReturnAuditError = _generated["Campaign094NoReturnAuditError"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _generated["DEFAULT_EXPERIMENT_ROOT"]
SNAPSHOT_MANIFEST_PATH = _generated["SNAPSHOT_MANIFEST_PATH"]
SNAPSHOT_MANIFEST_SHA256 = _generated["SNAPSHOT_MANIFEST_SHA256"]
SNAPSHOT_DATASET_SHA256 = _generated["SNAPSHOT_DATASET_SHA256"]
SNAPSHOT_BINDING = _generated["SNAPSHOT_BINDING"]
SNAPSHOT_BINDING_SHA256 = _generated["SNAPSHOT_BINDING_SHA256"]
AUDIT_IMPLEMENTATION_FREEZE = _generated["AUDIT_IMPLEMENTATION_FREEZE"]
AUDIT_ACTIVATION_BINDING = _generated["AUDIT_ACTIVATION_BINDING"]
TEST_PATH = _generated["TEST_PATH"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _generated["EXPECTED_PARTITIONS"]
EXPECTED_ELIGIBLE_ROWS = _generated["EXPECTED_ELIGIBLE_ROWS"]
EXPECTED_SESSIONS = _generated["EXPECTED_SESSIONS"]
EXPECTED_COMPARISON_COUNT = _generated["EXPECTED_COMPARISON_COUNT"]
EXPECTED_COMPLETE_DEFINITION_COUNT = _generated["EXPECTED_COMPLETE_DEFINITION_COUNT"]
c88_audit = _generated["c88_audit"]


def _install_frozen_ranges(engine: Any) -> None:
    c88_audit._install_frozen_ranges(engine)
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    if FACTOR_NAME in ranges and tuple(ranges[FACTOR_NAME]) != (0.0, 0.25):
        raise Campaign094NoReturnAuditError("conflicting Campaign094 range")
    ranges[FACTOR_NAME] = (0.0, 0.25)
    engine.FACTOR_RANGES = ranges


_generated["_install_frozen_ranges"] = _install_frozen_ranges

load_protocol = _generated["load_protocol"]
verify_candidate_snapshot = _generated["verify_candidate_snapshot"]
verify_static_bindings = _generated["verify_static_bindings"]
load_candidate_arrays = _generated["load_candidate_arrays"]
coverage_and_capacity = _generated["coverage_and_capacity"]
_load_comparisons_after_coverage = _generated["_load_comparisons_after_coverage"]
_run_no_return_audit = _generated["_run_no_return_audit"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
