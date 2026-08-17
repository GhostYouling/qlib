#!/usr/bin/env python3
"""Run Campaign260's frozen all-142 ordered no-return uniqueness audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign152_ordered_uniqueness.py"
)
BASE_RUNNER_SHA256 = "3803d4eca42feeed7c9d2e4cf635afdb37145e626b074e04322037594cbd91c9"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign152 ordered uniqueness runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign152", "Campaign260"),
    ("campaign152", "campaign260"),
    ("campaign_152", "campaign_260"),
    ("20260815", "20260816"),
    (
        "8f6c0b1e12d6d88566f8a2eed972f1e198829886dab4c6acc6fba93f499b5fca",
        "36138407f724989f0b644bfcf61fcc84192f7fd6c56c97dde0ce8872d8bae982",
    ),
    (
        "235289d3151eee543282c502fe40ac3d4986663fc00a777f4b3dcbb11c01f01b",
        "ea32c4c63cb52c0db394b315b12ed54ee7c4f74355e063fbc7f38cf077f4b6c8",
    ),
    (
        "36bab509de3b8a012033b4591a5efa942e57b01178f099cd48cbb699267ca267",
        "5e229b9c6d67614ea8104982ec959d55a11d2d388ad86e1c38ece62c42b3b356",
    ),
    (
        "9ea1ebe6aad4867ce76d4fbc52fe46c80f5a3fca3096aa6e74a5e9c8292f4931",
        "9077695bd82a2f4e0f65e4cfd81af346cc1d5e9760c9d8e188a6a8ac78bf591d",
    ),
    ("finite and strictly positive with no upper bound", "finite in [0,1] inclusive"),
    ("or (finite <= 0.0).any()", "or (finite < 0.0).any() or (finite > 1.0).any()"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign260_ordered_uniqueness_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

Campaign260OrderedUniquenessError = _generated[
    "Campaign260OrderedUniquenessError"
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
EXPECTED_COMPARISON_ORDER_SHA256 = _generated[
    "EXPECTED_COMPARISON_ORDER_SHA256"
]
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
