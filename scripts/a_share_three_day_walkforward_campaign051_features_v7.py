#!/usr/bin/env python3
"""Fingerprint-bound Campaign051 no-return audit after Candidate49 EINTR repair."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign051_features_v6 as repaired
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign051_features_v6 as repaired


runner = repaired.runner
REPAIR_IMPLEMENTATION_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_051_candidate49_eintr_repair_implementation_freeze_20260803.json"
)
EXPECTED_REPAIRED_ENTRYPOINT_SHA256 = (
    "e839223203cdf6114e4adca00f497c9f74b010cdffe6379a9972ccf2ff46ad2e"
)
EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256 = (
    "225836adf69b63efa53499e2601deb5a1c0125d8ce26b2482834b76ea1358c12"
)

if (
    runner._sha256(runner.Path(repaired.__file__).resolve())
    != EXPECTED_REPAIRED_ENTRYPOINT_SHA256
):
    raise runner.Campaign051FeatureError("Campaign051 frozen v6 EINTR repair changed")
if (
    runner._sha256(REPAIR_IMPLEMENTATION_FREEZE)
    != EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256
):
    raise runner.Campaign051FeatureError(
        "Campaign051 Candidate49 EINTR implementation freeze changed"
    )
if (
    repaired.engine._load_filtered_comparison_values_explicit
    is not repaired.load_filtered_comparison_values_with_candidate49_eintr_retry
):
    raise runner.Campaign051FeatureError(
        "Campaign051 Candidate49 EINTR repair is not installed"
    )


if __name__ == "__main__":
    raise SystemExit(runner.main())
