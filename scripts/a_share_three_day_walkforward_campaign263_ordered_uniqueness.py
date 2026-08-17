#!/usr/bin/env python3
"""Run Campaign263's frozen all-142 ordered no-return uniqueness audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign262_ordered_uniqueness.py"
)
BASE_RUNNER_SHA256 = "d3dec35ef59c5e01d653a6d851ebcdfdaafd43013e7c3df7ef9f7beecee9555c"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign262 ordered uniqueness runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign262", "Campaign263"),
    ("campaign262", "campaign263"),
    ("campaign_262", "campaign_263"),
    (
        "ba8393a2728254d414e24a643d2ec8e7ffd044a3c01e189cc1d02dc420c79ffb",
        "e4cd3e6ca0254809050a1779fc433fdbfbbe2afe81f67cb767f464be91dfb20f",
    ),
    (
        "6ef439612d8fef0570393998e5be65de87186b842d952708e330d3ec1ddc9156",
        "4fb82c67252efefdce8466c09e99a9dc526c394b234f2996d8172178e620f0fe",
    ),
    (
        "9bae791bd718231d6341b6f3a7205b3eae25e96aec7c2db0b2b22209e06d9d32",
        "fea163cfc8ec9fd2d389597ea33579b7cb1e0becd60a23be74694c7cddcefdc4",
    ),
    (
        "704da679bba6f247bfaba243df8cc4ecc3b7ac195565fe9ef7e0ff838c7e710b",
        "e9ee03f036cedd5a98badd64533ff9605e0d2bab046392a3ccd2afcbc3a225e7",
    ),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign263_ordered_uniqueness_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102
_generated["EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS"] = 1_330_170
_runtime = _generated["load_protocol"].__globals__
_runtime["EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS"] = 1_330_170
_runtime["IMPLEMENTATION_FREEZE_PATH"] = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_ordered_uniqueness_implementation_freeze_v5_20260816.json"
)
_coverage_module = _runtime["coverage"]
_coverage_runtime = _coverage_module._generated[  # noqa: SLF001
    "run_coverage_audit"
].__globals__
_inner_candidate_loader = _coverage_runtime["_load_candidate_frame"]


def _load_campaign263_candidate_frame(_inherited_expected: int) -> Any:
    return _inner_candidate_loader(7_724_491)


_coverage_module._generated["_load_candidate_frame"] = (  # noqa: SLF001
    _load_campaign263_candidate_frame
)
_coverage_module._generated["_quality_listing_eligible_keys"] = (  # noqa: SLF001
    _coverage_runtime["_quality_listing_eligible_keys"]
)
_generated["IMPLEMENTATION_FREEZE_PATH"] = _runtime["IMPLEMENTATION_FREEZE_PATH"]

Campaign263OrderedUniquenessError = _generated[
    "Campaign263OrderedUniquenessError"
]
PROTOCOL_PATH = _generated["PROTOCOL_PATH"]
PROTOCOL_SHA256 = _generated["PROTOCOL_SHA256"]
COVERAGE_PATH = _generated["COVERAGE_PATH"]
COVERAGE_SHA256 = _generated["COVERAGE_SHA256"]
IMPLEMENTATION_FREEZE_PATH = _generated["IMPLEMENTATION_FREEZE_PATH"]
TEST_PATH = _generated["TEST_PATH"]
OUTPUT_PATH = _generated["OUTPUT_PATH"]
CANDIDATE_MANIFEST_PATH = _generated["CANDIDATE_MANIFEST_PATH"]
CANDIDATE_MANIFEST_SHA256 = _generated["CANDIDATE_MANIFEST_SHA256"]
CANDIDATE_DATASET_SHA256 = _generated["CANDIDATE_DATASET_SHA256"]
EXPECTED_COMPARISON_COUNT = _generated["EXPECTED_COMPARISON_COUNT"]
EXPECTED_COMPARISON_ORDER_SHA256 = _generated["EXPECTED_COMPARISON_ORDER_SHA256"]
EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS = _generated[
    "EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS"
]
MINIMUM_PAIRWISE_NAMES = _generated["MINIMUM_PAIRWISE_NAMES"]
MINIMUM_PAIRWISE_SESSIONS = _generated["MINIMUM_PAIRWISE_SESSIONS"]
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = _generated[
    "MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION"
]
candidate = _generated["candidate"]
coverage = _generated["coverage"]
c146 = _generated["c146"]
base = _generated["base"]
comparison_definitions = _generated["comparison_definitions"]
load_protocol = _generated["load_protocol"]
validate_implementation_freeze = _generated["validate_implementation_freeze"]
validate_static_bindings = _generated["validate_static_bindings"]
build_plan = _generated["build_plan"]
eligible_candidate_panel = _generated["eligible_candidate_panel"]
source_snapshot_comparison = _generated["source_snapshot_comparison"]
summarize_comparisons = _generated["summarize_comparisons"]
run_ordered_uniqueness = _generated["run_ordered_uniqueness"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
