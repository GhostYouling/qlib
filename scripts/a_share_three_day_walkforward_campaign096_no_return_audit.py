#!/usr/bin/env python3
"""Run Campaign096's frozen coverage-first no-return uniqueness audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign096_features_v2 as definitions

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign093_no_return_audit.py"
)
BASE_RUNNER_SHA256 = "32d39c20f2eb29a699f2ac0018cecd132dddcf7b408541eb66fb3648e54c063f"
FACTOR_NAME = "intraday_intrabar_close_location_total_variation_238p"
C95_SEMANTIC_FACTOR = "intraday_own_bar_close_location_entropy_10b_240m"


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
    ("Campaign093", "Campaign096"),
    ("campaign093", "campaign096"),
    ("campaign_093", "campaign_096"),
    ("intraday_close_transition_range_quadratic_efficiency_238p", FACTOR_NAME),
    (
        "a_share_three_day_walkforward_campaign093_features_v2 as definitions",
        "a_share_three_day_walkforward_campaign096_features_v2 as definitions",
    ),
    (
        "a_share_three_day_walkforward_campaign092_no_return_audit as c88_audit",
        "a_share_three_day_walkforward_campaign094_no_return_audit as c88_audit",
    ),
    (
        "69428173fd9a84f7272b56e253b589cb712355ce0b59a05e2a0b0b9576b82e92",
        "1b205f1b6d3b28248b765860b8cf0e4aecee07f960fa535402e316ba13c39a3a",
    ),
    (
        "bba3e4e71626b0ff2fa3860649da5187ef5c5412879b009f6890e9599ba3cf0b",
        "67106bd4f5d4382b770cb79355c27ea4d8ca179296841b7bd9fa2963a46e09f3",
    ),
    (
        "8f58573bfc2c1e46bc31da2673d17d70c2aa470b112a898ac3ee1868facab233",
        "c5a96fbcc3c9c2927aedc0b855c0eddf1633c1ea1cae1a9fd65de87a9389a68c",
    ),
    ("EXPECTED_ELIGIBLE_ROWS = 1_328_155", "EXPECTED_ELIGIBLE_ROWS = 1_193_690"),
    ("EXPECTED_COMPARISON_COUNT = 122", "EXPECTED_COMPARISON_COUNT = 124"),
    (
        "EXPECTED_COMPLETE_DEFINITION_COUNT = 124",
        "EXPECTED_COMPLETE_DEFINITION_COUNT = 127",
    ),
    ("len(comparisons) != 121", "len(comparisons) != 123"),
    ("first 121 comparison order changed", "first 123 comparison order changed"),
    (
        'receipts["campaign092_compact_snapshot"]',
        'receipts["campaign094_compact_snapshot"]',
    ),
    (
        'receipts.pop("all_121_sources_loaded_in_frozen_order", None)',
        'receipts.pop("all_123_sources_loaded_in_frozen_order", None)',
    ),
    (
        'receipts["all_122_sources_loaded_in_frozen_order"] = True',
        'receipts["all_124_sources_loaded_in_frozen_order"] = True',
    ),
    (
        "c88_audit.c88_audit.c88_audit.c88_audit.c88_audit.c87_audit._compact_snapshot_comparison",
        "c88_audit.c88_audit.c88_audit.c88_audit.c88_audit.c88_audit.c88_audit.c87_audit._compact_snapshot_comparison",
    ),
):
    _source = _source.replace(_old, _new)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign096_no_return_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _namespace)  # noqa: S102

_generated = _namespace["_generated"]
_generated["definitions"] = definitions
_generated["EXPECTED_ELIGIBLE_ROWS"] = 1_193_690
Campaign096NoReturnAuditError = _generated["Campaign096NoReturnAuditError"]

_base_load_protocol = _generated["load_protocol"]


def load_protocol() -> dict[str, Any]:
    """Validate v39's semantic-only Campaign095 tail without reading its values."""

    spec = _base_load_protocol()
    complete = definitions.reconstruct_complete_definitions()
    comparisons = definitions.reconstruct_comparisons()
    complete_names = [str(item["name"]) for item in complete]
    comparison_names = [str(item["name"]) for item in comparisons]
    if not (
        complete[-1]
        == {"name": C95_SEMANTIC_FACTOR, "score_direction": "higher"}
        and C95_SEMANTIC_FACTOR in complete_names
        and C95_SEMANTIC_FACTOR not in comparison_names
        and comparisons[-1]
        == {
            "name": "intraday_range_local_peak_clock_dispersion_236p",
            "score_direction": "higher",
        }
    ):
        raise Campaign096NoReturnAuditError("Campaign096 v39 semantic tail changed")
    return spec


_generated["load_protocol"] = load_protocol


def _install_frozen_ranges(engine: Any) -> None:
    c88_audit._install_frozen_ranges(engine)
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    if FACTOR_NAME in ranges and tuple(ranges[FACTOR_NAME]) != (0.0, 1.0):
        raise Campaign096NoReturnAuditError("conflicting Campaign096 range")
    ranges[FACTOR_NAME] = (0.0, 1.0)
    engine.FACTOR_RANGES = ranges


_generated["_install_frozen_ranges"] = _install_frozen_ranges

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
