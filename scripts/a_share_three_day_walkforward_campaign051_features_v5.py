#!/usr/bin/env python3
"""Fingerprint-bound final Campaign051 no-return audit continuation."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign051_features_v4 as repaired
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign051_features_v4 as repaired


runner = repaired.runner
REPAIR_IMPLEMENTATION_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_051_campaign050_verifier_repair_implementation_freeze_20260803.json"
)
EXPECTED_REPAIRED_ENTRYPOINT_SHA256 = (
    "1360d1f35e3543cb6f0ff4e1219cf7ee66fd5797a6b998b62430e7de729d7169"
)
EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256 = (
    "d23e1c78cf07f46ccadacbab4a7b900934550885bc25c17a4662201930035413"
)

if (
    runner._sha256(runner.Path(repaired.__file__).resolve())
    != EXPECTED_REPAIRED_ENTRYPOINT_SHA256
):
    raise runner.Campaign051FeatureError("Campaign051 frozen v4 repair changed")
if (
    runner._sha256(REPAIR_IMPLEMENTATION_FREEZE)
    != EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256
):
    raise runner.Campaign051FeatureError(
        "Campaign051 Campaign050-verifier implementation freeze changed"
    )
if runner.previous.verify_snapshot_files is not repaired.verify_campaign050_snapshot_files:
    raise runner.Campaign051FeatureError(
        "Campaign051 Campaign050-verifier repair is not installed"
    )


if __name__ == "__main__":
    raise SystemExit(runner.main())
